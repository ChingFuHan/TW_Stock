r"""
Update brokers and branches tables from a local lookup JS (zbrokerjs.djjs).

Usage:
  .venv/Scripts/python.exe pg_sample_code/update_brokers_from_lookup.py --lookup-js data/raw/samples/zbrokerjs.djjs --db tw
  .venv/Scripts/python.exe pg_sample_code/update_brokers_from_lookup.py --dry-run

By default this updates both brokers and branches. Use --no-branches to skip branches.
"""
from __future__ import annotations

import sys
from pathlib import Path
import argparse
import datetime

# Ensure project root is importable so we can use src.tw_broker_flows.broker_lookup
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# db_util is in the same folder (pg_sample_code) so importing should work when running this script
try:
    import db_util
except Exception as exc:
    print("Warning: db_util import failed; DB execution will not work unless db_util is available.", exc)
    db_util = None

try:
    from src.tw_broker_flows.broker_lookup import (
        load_lookup_from_path,
        get_broker_names,
        get_broker_branches,
        normalize_branch_code,
    )
except Exception as exc:
    raise RuntimeError("Could not import broker_lookup from src.tw_broker_flows. Ensure you run from project root and src is present.") from exc


def q(val: object) -> str:
    if val is None:
        return 'NULL'
    s = str(val)
    s = s.strip()
    if s == '':
        return 'NULL'
    return "'" + s.replace("'", "''") + "'"


def bool_sql(b: bool) -> str:
    return 'true' if b else 'false'


def build_statements(lookup: dict, include_branches: bool = True) -> list:
    stmts: list[str] = []
    now = datetime.datetime.utcnow().isoformat()

    broker_names = get_broker_names(lookup)
    broker_branches = get_broker_branches(lookup)

    # Brokers
    for broker_code in sorted(broker_names.keys()):
        broker_name = broker_names.get(broker_code, '')
        stmts.append(
            f"INSERT INTO public.brokers(broker_code, broker_name, fetched_at) VALUES ({q(broker_code)}, {q(broker_name)}, {q(now)}) "
            f"ON CONFLICT (broker_code) DO UPDATE SET broker_name = EXCLUDED.broker_name, fetched_at = EXCLUDED.fetched_at;"
        )

    if include_branches:
        for broker_code in sorted(broker_branches.keys()):
            branch_map = broker_branches.get(broker_code, {})
            for branch_code_raw in sorted(branch_map.keys()):
                branch_name = branch_map.get(branch_code_raw, '')
                branch_code_norm = normalize_branch_code(branch_code_raw)
                is_broker_level = False
                if branch_code_norm and broker_code and str(branch_code_norm) == str(broker_code):
                    is_broker_level = True
                if str(branch_code_raw) == str(broker_code):
                    is_broker_level = True

                stmts.append(
                    f"INSERT INTO public.branches(broker_code, branch_code_raw, branch_code, branch_name, is_broker_level, fetched_at) VALUES ("
                    f"{q(broker_code)},{q(branch_code_raw)},{q(branch_code_norm)},{q(branch_name)},{bool_sql(is_broker_level)},{q(now)}) "
                    f"ON CONFLICT (broker_code, branch_code_raw) DO UPDATE SET branch_code = EXCLUDED.branch_code, branch_name = EXCLUDED.branch_name, is_broker_level = EXCLUDED.is_broker_level, fetched_at = EXCLUDED.fetched_at;"
                )

    return stmts


def execute_batches(dbname: str, stmts: list[str], batch_size: int = 500) -> None:
    if db_util is None:
        raise RuntimeError('db_util not available; cannot execute SQL against DB.')

    errors = 0
    for i in range(0, len(stmts), batch_size):
        batch = '\n'.join(stmts[i : i + batch_size])
        err = db_util.db99exec(dbname, batch)
        if err is not None:
            print('DB error on batch starting at', i, err)
            errors += 1
    print('Finished. Batches with errors:', errors)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Update brokers and branches from lookup JS')
    parser.add_argument('--lookup-js', default=str(project_root / 'data' / 'raw' / 'samples' / 'zbrokerjs.djjs'))
    parser.add_argument('--db', default='tw', help='Database name (used by db_util.getconn)')
    parser.add_argument('--no-branches', action='store_true', help='Do not update branches table')
    parser.add_argument('--dry-run', action='store_true', help='Only show SQL and counts')
    parser.add_argument('--batch-size', type=int, default=500, help='Statements per DB batch')
    args = parser.parse_args(argv)

    lookup_path = Path(args.lookup_js)
    if not lookup_path.exists():
        print('Lookup JS not found:', lookup_path)
        return 2

    lookup = load_lookup_from_path(lookup_path)
    stmts = build_statements(lookup, include_branches=(not args.no_branches))

    print(f'Prepared {len(stmts)} SQL statements (brokers + branches={not args.no_branches}).')
    if args.dry_run:
        for s in stmts[:50]:
            print(s)
        return 0

    execute_batches(args.db, stmts, batch_size=args.batch_size)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
