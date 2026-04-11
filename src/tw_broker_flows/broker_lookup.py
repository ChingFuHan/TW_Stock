from __future__ import annotations

from pathlib import Path
import re
import ssl
from typing import Any, cast
import urllib.request
from urllib.parse import urlencode, urljoin
import sys
import os


BROKER_LIST_PATTERN = re.compile(r"var\s+g_BrokerList\s*=\s*'(.*?)';", re.S)
DEFAULT_PAGE_URL = "https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm"
METRIC_QUERY_VALUE = {
    "amount": "B",
    "lots": "E",
}
HEX_CODE_PATTERN = re.compile(r"^[0-9A-Fa-f]+$")
NORMALIZED_CODE_PATTERN = re.compile(r"^[0-9A-Za-z]+$")


LookupData = dict[str, Any]
BranchSourceRow = dict[str, object]


def create_lookup_data() -> LookupData:
    return {
        "broker_names": {},
        "branch_names": {},
        "broker_branches": {},
    }


def get_broker_names(lookup: LookupData) -> dict[str, str]:
    return cast(dict[str, str], lookup["broker_names"])


def get_branch_names(lookup: LookupData) -> dict[str, str]:
    return cast(dict[str, str], lookup["branch_names"])


def get_broker_branches(lookup: LookupData) -> dict[str, dict[str, str]]:
    return cast(dict[str, dict[str, str]], lookup["broker_branches"])


def merge_lookup_data(base_lookup: LookupData | None, extra_lookup: LookupData | None) -> LookupData:
    merged = create_lookup_data()
    merged_broker_names = get_broker_names(merged)
    merged_branch_names = get_branch_names(merged)
    merged_broker_branches = get_broker_branches(merged)

    for source in (base_lookup, extra_lookup):
        if source is None:
            continue

        merged_broker_names.update(get_broker_names(source))
        merged_branch_names.update(get_branch_names(source))

        for broker_code, branch_map in get_broker_branches(source).items():
            target_map = merged_broker_branches.setdefault(broker_code, {})
            target_map.update(branch_map)

    return merged


def build_lookup_from_branch_rows(rows: list[BranchSourceRow]) -> LookupData:
    lookup = create_lookup_data()
    broker_names = get_broker_names(lookup)
    branch_names = get_branch_names(lookup)
    broker_branches = get_broker_branches(lookup)

    for row in rows:
        broker_name = str(row.get("券商中文", "")).strip()
        branch_name = str(row.get("分行中文", "")).strip()
        code1 = str(row.get("code1", "")).strip()
        code2 = str(row.get("code2", "")).strip()

        if not code1 or not code2:
            continue

        if broker_name:
            broker_names[code1] = broker_name

        if branch_name:
            branch_names[code2] = branch_name

        broker_branches.setdefault(code1, {})[code2] = branch_name

    return lookup


def resolve_names(lookup: LookupData, broker_code: str | None, branch_code: str | None) -> tuple[str | None, str | None]:
    broker_names = get_broker_names(lookup)
    branch_names = get_branch_names(lookup)
    broker_branches = get_broker_branches(lookup)

    broker_name = broker_names.get(broker_code or "")
    branch_name = branch_names.get(branch_code or "")

    if branch_name is None and broker_code and branch_code:
        branch_name = broker_branches.get(broker_code, {}).get(branch_code)

    if broker_name is None and branch_name and "-" in branch_name:
        broker_name = branch_name.split("-", 1)[0]

    return broker_name, branch_name


def iter_company_rows(lookup: LookupData) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    broker_names = get_broker_names(lookup)
    broker_branches = get_broker_branches(lookup)

    for broker_code in sorted(broker_names):
        rows.append(
            {
                "券商中文": broker_names[broker_code],
                "code1": broker_code,
                "分行數": len(broker_branches.get(broker_code, {})),
            }
        )

    return rows


def iter_branch_rows(lookup: LookupData) -> list[BranchSourceRow]:
    rows: list[BranchSourceRow] = []
    broker_names = get_broker_names(lookup)
    broker_branches = get_broker_branches(lookup)

    for broker_code in sorted(broker_branches):
        broker_name = broker_names.get(broker_code, "")
        branch_map = broker_branches[broker_code]
        for branch_code in sorted(branch_map):
            rows.append(
                {
                    "券商中文": broker_name,
                    "分行中文": branch_map[branch_code],
                    "code1": broker_code,
                    "code2": branch_code,
                    "is_broker_level": branch_code == broker_code,
                }
            )

    return rows


def build_branch_url(
    start_date: str,
    end_date: str,
    code1: str,
    code2: str,
    base_url: str = DEFAULT_PAGE_URL,
    metric_type: str = "amount",
) -> str:
    metric_value = METRIC_QUERY_VALUE.get(metric_type)
    if metric_value is None:
        raise ValueError(f"Unsupported metric_type: {metric_type}")

    query = urlencode(
        {
            "a": code1,
            "b": code2,
            "c": metric_value,
            "e": start_date,
            "f": end_date,
        }
    )
    return f"{base_url}?{query}"


def build_target_urls(
    branch_rows: list[BranchSourceRow],
    start_date: str,
    end_date: str,
    base_url: str = DEFAULT_PAGE_URL,
    metric_type: str = "amount",
) -> list[str]:
    """
    Generate daily URLs for each branch in the date range.
    Each URL represents a single trading day query.
    Only generates URLs for weekdays (Mon-Fri), excluding weekends.
    """
    from datetime import datetime, timedelta
    
    urls: list[str] = []
    seen: set[str] = set()

    # Parse dates and generate all trading days in range
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Generate URL for each weekday + each branch
    current = start
    while current <= end:
        # Skip weekends (5=Saturday, 6=Sunday)
        if current.weekday() < 5:
            current_date_str = current.strftime("%Y-%m-%d")
            
            for row in branch_rows:
                code1 = str(row.get("code1", "")).strip()
                code2 = str(row.get("code2", "")).strip()
                if not code1 or not code2:
                    continue

                # For daily queries, both start and end should be the same date
                url = build_branch_url(
                    start_date=current_date_str,
                    end_date=current_date_str,
                    code1=code1,
                    code2=code2,
                    base_url=base_url,
                    metric_type=metric_type,
                )
                if url not in seen:
                    urls.append(url)
                    seen.add(url)
        
        current += timedelta(days=1)

    return urls


def parse_lookup_text(text: str) -> LookupData:
    match = BROKER_LIST_PATTERN.search(text)
    if not match:
        raise ValueError("Could not find g_BrokerList in lookup JavaScript.")

    lookup = create_lookup_data()
    broker_names = get_broker_names(lookup)
    branch_names = get_branch_names(lookup)
    broker_branches = get_broker_branches(lookup)
    groups = [group for group in match.group(1).split(";") if group]

    for group in groups:
        entries = [item for item in group.split("!") if item]
        parsed_entries: list[tuple[str, str]] = []
        for entry in entries:
            if "," not in entry:
                continue
            code, name = entry.split(",", 1)
            code = code.strip()
            name = name.strip()
            if code and name:
                parsed_entries.append((code, name))

        if not parsed_entries:
            continue

        broker_code, broker_name = parsed_entries[0]
        broker_names[broker_code] = broker_name
        branch_map = broker_branches.setdefault(broker_code, {})

        for branch_code, branch_name in parsed_entries:
            branch_map[branch_code] = branch_name
            branch_names[branch_code] = branch_name

    return lookup


def load_lookup_from_path(path: str | Path, encoding: str = "big5") -> LookupData:
    return parse_lookup_text(Path(path).read_bytes().decode(encoding, errors="replace"))


def fetch_lookup_text(source_url: str, timeout: int = 30) -> str:
    lookup_url = urljoin(source_url, "/z/js/zbrokerjs.djjs")
    request = urllib.request.Request(
        lookup_url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; tw-broker-flow-scraper/0.1)"},
    )
    with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
        return response.read().decode("big5", errors="replace")


def fetch_lookup(source_url: str, timeout: int = 30) -> LookupData:
    return parse_lookup_text(fetch_lookup_text(source_url, timeout=timeout))


def normalize_branch_code(branch_code: str | None) -> str | None:
    if branch_code is None:
        return None

    value = branch_code.strip()
    if not value:
        return value

    if len(value) < 8 or len(value) % 4 != 0 or not value.startswith("00"):
        return value

    if not HEX_CODE_PATTERN.fullmatch(value):
        return value

    try:
        decoded = "".join(chr(int(value[index : index + 4], 16)) for index in range(0, len(value), 4))
    except ValueError:
        return value

    if NORMALIZED_CODE_PATTERN.fullmatch(decoded):
        return decoded.upper()

    return value


def load_lookup_from_db(dbname: str, include_branches: bool = True, db_schema: str = "public") -> LookupData:
    """
    Load lookup data from Postgres reference tables.

    Returns a LookupData dict compatible with parse_lookup/load_lookup_from_path.
    """
    lookup = create_lookup_data()
    broker_names = get_broker_names(lookup)
    branch_names = get_branch_names(lookup)
    broker_branches = get_broker_branches(lookup)

    db_util = None
    conn = None
    cur = None

    # Try to import db_util from pg_sample_code (same approach as db_writer)
    try:
        project_root = Path(__file__).resolve().parents[2]
        pg_sample = project_root / "pg_sample_code"
        if pg_sample.exists():
            sys.path.insert(0, str(pg_sample))
        import db_util as _db_util  # type: ignore
        db_util = _db_util
    except Exception:
        db_util = None

    try:
        if db_util is not None:
            conn = db_util.getconn(dbname)
        else:
            try:
                import psycopg2  # type: ignore
            except Exception as exc:
                raise RuntimeError("psycopg2 is required to load lookup from DB when db_util is not available") from exc

            dsn = os.environ.get("DATABASE_URL") or os.environ.get("DB_DSN")
            if dsn:
                conn = psycopg2.connect(dsn)
            else:
                conn = psycopg2.connect(
                    dbname=dbname,
                    host=os.environ.get("PGHOST", "127.0.0.1"),
                    port=os.environ.get("PGPORT", "5432"),
                    user=os.environ.get("PGUSER", "postgres"),
                    password=os.environ.get("PGPASSWORD", ""),
                )

        cur = conn.cursor()
        cur.execute(f"SELECT broker_code, broker_name FROM {db_schema}.brokers;")
        for row in cur.fetchall():
            code = row[0]
            name = row[1] if row[1] is not None else ""
            if code:
                broker_names[str(code)] = str(name)

        if include_branches:
            cur.execute(f"SELECT broker_code, branch_code_raw, branch_name FROM {db_schema}.branches;")
            for row in cur.fetchall():
                bcode = row[0]
                branch_raw = row[1]
                branch_name = row[2] if row[2] is not None else ""
                if not bcode or not branch_raw:
                    continue
                bcode = str(bcode)
                branch_raw = str(branch_raw)
                branch_name = str(branch_name)
                broker_branches.setdefault(bcode, {})[branch_raw] = branch_name
                branch_names[branch_raw] = branch_name

    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
        if conn is not None:
            if db_util is not None:
                try:
                    # return to pool if available
                    db_util.conn_pools[dbname].putconn(conn)
                except Exception:
                    try:
                        conn.close()
                    except Exception:
                        pass
            else:
                try:
                    conn.close()
                except Exception:
                    pass

    return lookup
