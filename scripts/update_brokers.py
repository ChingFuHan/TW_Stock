#!/usr/bin/env python3
r"""
Simplified DB-only single-threaded broker/branch updater.

Loads broker/branch data from lookup JS, validates against DB, and directly upserts 
to PostgreSQL. Single-threaded execution only, with comprehensive progress logging.

Usage:
  .venv/Scripts/python.exe scripts/update_brokers.py --lookup-js data/raw/samples/zbrokerjs.djjs --db tw
  .venv/Scripts/python.exe scripts/update_brokers.py --dry-run --lookup-js data/raw/samples/zbrokerjs.djjs
"""
from __future__ import annotations

import sys
from pathlib import Path
import argparse
import datetime
import logging
from typing import Optional, Any

# Ensure project root is importable
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.tw_broker_flows.broker_lookup import (
    load_lookup_from_path,
    get_broker_names,
    get_broker_branches,
    normalize_branch_code,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_db_connection(dbname: str) -> Any:
    """Get a psycopg2 connection. Prefer db_util if available."""
    # Try db_util first (from pg_sample_code)
    try:
        pg_sample = project_root / "pg_sample_code"
        if pg_sample.exists():
            sys.path.insert(0, str(pg_sample))
            import db_util  # type: ignore
            return db_util.getconn(dbname), db_util
    except Exception:
        pass
    
    # Fall back to direct psycopg2
    try:
        import psycopg2  # type: ignore
    except ImportError:
        raise RuntimeError("psycopg2 is required. Install: pip install psycopg2-binary")
    
    import os
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("DB_DSN")
    if dsn:
        return psycopg2.connect(dsn), None
    
    return psycopg2.connect(
        dbname=dbname,
        host=os.environ.get("PGHOST", "127.0.0.1"),
        port=int(os.environ.get("PGPORT", "5432")),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", ""),
    ), None


def put_db_connection(conn: Any, dbname: str, db_util: Optional[Any]) -> None:
    """Return connection to pool (if db_util) or close it."""
    if db_util is not None:
        try:
            db_util.conn_pools[dbname].putconn(conn)
            return
        except Exception:
            pass
    try:
        conn.close()
    except Exception:
        pass


def upsert_brokers(conn: Any, lookup: dict, now_iso: str, dry_run: bool = False) -> dict[str, int]:
    """
    Upsert brokers from lookup into public.brokers table.
    
    Returns: {'processed': count, 'failed': count}
    """
    broker_names = get_broker_names(lookup)
    stats = {'processed': 0, 'failed': 0}
    
    logger.info(f"Processing {len(broker_names)} brokers...")
    
    if dry_run:
        for broker_code in sorted(broker_names.keys()):
            broker_name = broker_names[broker_code]
            logger.info(f"  [DRY-RUN] INSERT broker {broker_code}: {broker_name}")
            stats['processed'] += 1
        return stats
    
    cur = conn.cursor()
    try:
        for broker_code in sorted(broker_names.keys()):
            broker_name = broker_names[broker_code]
            
            sql = (
                "INSERT INTO public.brokers(broker_code, broker_name, fetched_at) "
                "VALUES (%s, %s, %s) "
                "ON CONFLICT DO NOTHING;"
            )
            
            try:
                cur.execute(sql, (broker_code, broker_name, now_iso))
                stats['processed'] += 1
                if stats['processed'] % 10 == 0:
                    logger.info(f"  Processed {stats['processed']} brokers...")
            except Exception as e:
                logger.error(f"  Failed to insert broker {broker_code}: {e}")
                stats['failed'] += 1
        
        conn.commit()
        logger.info(f"Committed {stats['processed']} broker records")
    finally:
        cur.close()
    
    return stats


def upsert_branches(conn: Any, lookup: dict, now_iso: str, dry_run: bool = False) -> dict[str, int]:
    """
    Upsert branches from lookup into public.branches table.
    
    Returns: {'processed': count, 'failed': count}
    """
    broker_names = get_broker_names(lookup)
    broker_branches = get_broker_branches(lookup)
    stats = {'processed': 0, 'failed': 0}
    
    total_branches = sum(len(b) for b in broker_branches.values())
    logger.info(f"Processing {total_branches} total branches across {len(broker_branches)} brokers...")
    
    if dry_run:
        for broker_code in sorted(broker_branches.keys()):
            branch_map = broker_branches[broker_code]
            logger.info(f"  Broker {broker_code}: {len(branch_map)} branches")
            
            for branch_code_raw in sorted(branch_map.keys()):
                branch_name = branch_map[branch_code_raw]
                branch_code_norm = normalize_branch_code(branch_code_raw)
                is_broker_level = (
                    (branch_code_norm and str(branch_code_norm) == str(broker_code)) or
                    (str(branch_code_raw) == str(broker_code))
                )
                logger.debug(
                    f"    [DRY-RUN] INSERT branch {broker_code}/{branch_code_raw} "
                    f"(normalized: {branch_code_norm}, broker_level: {is_broker_level}): {branch_name}"
                )
                stats['processed'] += 1
        return stats
    
    cur = conn.cursor()
    try:
        for broker_code in sorted(broker_branches.keys()):
            branch_map = broker_branches[broker_code]
            logger.info(f"  Broker {broker_code}: {len(branch_map)} branches")
            
            for branch_code_raw in sorted(branch_map.keys()):
                branch_name = branch_map[branch_code_raw]
                branch_code_norm = normalize_branch_code(branch_code_raw)
                
                # Determine if this is a broker-level branch
                is_broker_level = (
                    (branch_code_norm and str(branch_code_norm) == str(broker_code)) or
                    (str(branch_code_raw) == str(broker_code))
                )
                
                sql = (
                    "INSERT INTO public.branches(broker_code, branch_code_raw, branch_code, "
                    "branch_name, is_broker_level, fetched_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT DO NOTHING;"
                )
                
                try:
                    cur.execute(
                        sql,
                        (broker_code, branch_code_raw, branch_code_norm, branch_name, is_broker_level, now_iso)
                    )
                    stats['processed'] += 1
                    if stats['processed'] % 50 == 0:
                        logger.info(f"    Processed {stats['processed']} branches...")
                except Exception as e:
                    logger.error(f"    Failed to insert branch {broker_code}/{branch_code_raw}: {e}")
                    stats['failed'] += 1
        
        conn.commit()
        logger.info(f"Committed {stats['processed']} branch records")
    finally:
        cur.close()
    
    return stats


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description='Simplified DB-only single-threaded broker/branch updater',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--lookup-js',
        default=str(project_root / 'data' / 'raw' / 'samples' / 'zbrokerjs.djjs'),
        help='Path to broker lookup JavaScript file (default: data/raw/samples/zbrokerjs.djjs)'
    )
    parser.add_argument(
        '--db',
        default='tw',
        help='Database name (default: tw)'
    )
    parser.add_argument(
        '--no-branches',
        action='store_true',
        help='Skip branch updates (only update brokers)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print SQL without executing (safe preview)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args(argv)
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Validate lookup file
    lookup_path = Path(args.lookup_js)
    if not lookup_path.exists():
        logger.error(f"Lookup JS file not found: {lookup_path}")
        return 2
    
    logger.info(f"Loading lookup from: {lookup_path}")
    try:
        lookup = load_lookup_from_path(lookup_path)
    except Exception as e:
        logger.error(f"Failed to load lookup: {e}")
        return 2
    
    broker_names = get_broker_names(lookup)
    broker_branches = get_broker_branches(lookup)
    logger.info(f"Loaded {len(broker_names)} brokers, {sum(len(b) for b in broker_branches.values())} branches total")
    
    if args.dry_run:
        logger.info("Running in DRY-RUN mode (no DB changes)")
        now_iso = datetime.datetime.utcnow().isoformat()
        
        # Dry-run with memory connection
        broker_stats = upsert_brokers(None, lookup, now_iso, dry_run=True)
        logger.info(f"Broker stats (dry-run): {broker_stats}")
        
        if not args.no_branches:
            branch_stats = upsert_branches(None, lookup, now_iso, dry_run=True)
            logger.info(f"Branch stats (dry-run): {branch_stats}")
        
        return 0
    
    # Connect to DB
    logger.info(f"Connecting to database '{args.db}'...")
    try:
        conn, db_util_module = get_db_connection(args.db)
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return 1
    
    try:
        now_iso = datetime.datetime.utcnow().isoformat()
        
        # Upsert brokers
        logger.info("=== BROKERS ===")
        broker_stats = upsert_brokers(conn, lookup, now_iso, dry_run=False)
        logger.info(f"Brokers result: {broker_stats['processed']} processed, {broker_stats['failed']} failed")
        
        # Upsert branches
        if not args.no_branches:
            logger.info("\n=== BRANCHES ===")
            branch_stats = upsert_branches(conn, lookup, now_iso, dry_run=False)
            logger.info(f"Branches result: {branch_stats['processed']} processed, {branch_stats['failed']} failed")
            
            total_processed = broker_stats['processed'] + branch_stats['processed']
            total_failed = broker_stats['failed'] + branch_stats['failed']
        else:
            total_processed = broker_stats['processed']
            total_failed = broker_stats['failed']
        
        logger.info(f"\n=== SUMMARY ===")
        logger.info(f"Total: {total_processed} processed, {total_failed} failed")
        
        return 0 if total_failed == 0 else 1
    
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1
    
    finally:
        put_db_connection(conn, args.db, db_util_module)


if __name__ == '__main__':
    raise SystemExit(main())
