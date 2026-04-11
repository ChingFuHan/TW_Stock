from __future__ import annotations

from pathlib import Path
import sys
import os
import datetime
from typing import Any, Dict, List, Optional

try:
    import psycopg2
    from psycopg2.extras import execute_values
except Exception as exc:  # pragma: no cover - runtime requirement
    raise RuntimeError("psycopg2 is required for DB writes: install psycopg2-binary") from exc


# Try to reuse existing pg_sample_code/db_util connection pool if available
def _import_db_util() -> Optional[Any]:
    try:
        project_root = Path(__file__).resolve().parents[2]
        pg_sample = project_root / "pg_sample_code"
        if pg_sample.exists():
            # Ensure the folder with db_util.py is on sys.path so `import db_util` works
            sys.path.insert(0, str(pg_sample))
        import db_util  # type: ignore

        return db_util
    except Exception:
        return None


_db_util = _import_db_util()


INSERT_SQL = """INSERT INTO public.stock_flow_lots_detailed(
    da, stock_code, stock_name, broker_code, branch_code, branch_code_raw,
    broker_name, branch_name, buy_lots, sell_lots, net_lots, source_url, fetched_at, created_at
) VALUES %s
ON CONFLICT ON CONSTRAINT stock_flow_lots_detailed_pkey DO NOTHING;
"""


def _normalize_code(stock_code: Optional[str]) -> Optional[str]:
    if stock_code is None:
        return None
    s = str(stock_code).strip()
    if not s:
        return None
    if s.endswith("TT Equity"):
        return s
    return f"{s} TT Equity"


def _parse_datetime(value: object) -> Optional[datetime.datetime]:
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time.min)
    s = str(value).strip()
    if not s:
        return None
    try:
        # ISO formats
        return datetime.datetime.fromisoformat(s)
    except Exception:
        pass
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d")
    except Exception:
        return None


def _to_int(value: object) -> Optional[int]:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s in {"--", "N/A"}:
        return None
    try:
        return int(str(s).replace(",", ""))
    except Exception:
        return None


def _get_connection(dbname: str):
    """Return a psycopg2 connection. Prefer db_util.getconn(dbname) if available, otherwise
    connect using environment variables (DATABASE_URL or PGHOST/PGUSER/PGPASSWORD/PGPORT).
    """
    if _db_util is not None:
        # db_util.getconn returns a connection from a ThreadedConnectionPool
        return _db_util.getconn(dbname)

    dsn = os.environ.get("DATABASE_URL") or os.environ.get("DB_DSN")
    if dsn:
        return psycopg2.connect(dsn)

    return psycopg2.connect(
        dbname=dbname,
        host=os.environ.get("PGHOST", "127.0.0.1"),
        port=os.environ.get("PGPORT", "5432"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", ""),
    )


def _put_connection(dbname: str, conn) -> None:
    if _db_util is not None:
        try:
            # return to pool
            _db_util.conn_pools[dbname].putconn(conn)
            return
        except Exception:
            pass

    try:
        conn.close()
    except Exception:
        pass


def insert_records(records: List[Dict[str, object]], dbname: str, chunk_size: int = 200, schema: str = "public", table: str = "stock_flow_lots_detailed") -> int:
    """
    Insert parsed records into a stock flow table using the actual table columns present in the DB.

    This function discovers the table columns at runtime and maps parsed record keys
    heuristically to those columns. It uses ON CONFLICT DO NOTHING so repeated runs are safe.
    
    Optimized for concurrent access with better connection handling.
    """
    if not records:
        return 0

    # simple module-level cache for discovered table columns
    _table_columns_cache = globals().get("_table_columns_cache")
    if _table_columns_cache is None:
        _table_columns_cache = {}
        globals()["_table_columns_cache"] = _table_columns_cache

    def _get_table_columns(dbname_: str, schema_: str, table_: str) -> List[str]:
        key = (dbname_, schema_, table_)
        if key in _table_columns_cache:
            return _table_columns_cache[key]

        conn = _get_connection(dbname_)
        cols: List[str] = []
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position",
                (schema_, table_),
            )
            cols = [row[0] for row in cur.fetchall()]
            cur.close()
        finally:
            _put_connection(dbname_, conn)

        _table_columns_cache[key] = cols
        return cols

    def _map_record_to_row(r: Dict[str, object], cols: List[str]) -> tuple:
        values: List[object | None] = []
        for col in cols:
            lname = col.lower()
            val = None

            # date/time
            if lname in ("da", "trade_date", "date"):
                val = _parse_datetime(r.get("trade_date") or r.get("da") or r.get("date"))

            # stock code / name
            # Accept both 'stock_code'/'stock_name' *and* short names like 'code'/'cname' used in legacy schemas.
            if lname == "code" or ("stock" in lname and "code" in lname):
                code = r.get("stock_code") or r.get("stock") or r.get("code") or r.get("stock_no")
                if code is None:
                    val = None
                else:
                    s = str(code).strip()
                    val = s if s.endswith("TT Equity") or s == "" else f"{s} TT Equity"

            elif lname == "cname" or lname == "name" or ("stock" in lname and "name" in lname):
                val = r.get("stock_name") or r.get("stock") or r.get("name") or r.get("cname")


            # broker/branch ids and names
            elif "broker" in lname and "code" in lname:
                val = r.get("broker_code") or r.get("code1") or r.get("broker")

            elif "branch" in lname and "code" in lname:
                if "raw" in lname:
                    val = r.get("branch_code_raw") or r.get("code2")
                else:
                    val = r.get("branch_code") or r.get("branch_code_raw") or r.get("code2")

            elif "broker" in lname and "name" in lname:
                val = r.get("broker_name") or r.get("券商中文") or r.get("broker")

            elif "branch" in lname and "name" in lname:
                val = r.get("branch_name") or r.get("分行中文") or r.get("branch")

            # numeric lots
            elif "buy" in lname and "lot" in lname:
                val = _to_int(r.get("buy_lots") or r.get("buy"))

            elif "sell" in lname and "lot" in lname:
                val = _to_int(r.get("sell_lots") or r.get("sell"))

            elif "net" in lname and "lot" in lname:
                val = _to_int(r.get("net_lots") or r.get("net"))

            # urls / timestamps
            elif "source" in lname or "url" in lname:
                val = r.get("source_url") or r.get("source") or r.get("url")

            elif "fetched" in lname:
                val = _parse_datetime(r.get("fetched_at") or r.get("fetched"))

            elif "created" in lname:
                val = _parse_datetime(r.get("created_at")) or datetime.datetime.now()

            else:
                # fallback: try exact key matches (case-sensitive and lowercased)
                # Only override earlier-determined values if val is None —
                # preserve mappings like the parsed trade_date that were set above.
                if val is None:
                    if col in r:
                        val = r.get(col)
                    elif col.lower() in r:
                        val = r.get(col.lower())
                    elif col.upper() in r:
                        val = r.get(col.upper())
                    else:
                        val = None

            values.append(val)

        return tuple(values)

    cols = _get_table_columns(dbname, schema, table)
    if not cols:
        raise RuntimeError(f"Could not find columns for table {schema}.{table}")

    # build value rows aligned to discovered columns
    rows: List[tuple] = []
    for r in records:
        row = _map_record_to_row(r, cols)
        
        # Check if required NOT NULL columns have values
        code_idx = cols.index('code') if 'code' in cols else -1
        cname_idx = cols.index('cname') if 'cname' in cols else -1
        
        if code_idx >= 0 and row[code_idx] is None:
            import logging
            logging.warning(f"Skipping record with NULL code: {r.get('source_url')}")
            continue
        if cname_idx >= 0 and row[cname_idx] is None:
            import logging
            logging.warning(f"Skipping record with NULL cname: {r.get('source_url')}")
            continue
        
        rows.append(row)


    total_attempted = 0
    insert_sql = f"INSERT INTO {schema}.{table} ({', '.join(cols)}) VALUES %s ON CONFLICT DO NOTHING;"

    # Process in chunks with better error handling
    for i in range(0, len(rows), chunk_size):
        batch = rows[i : i + chunk_size]
        conn = _get_connection(dbname)
        try:
            cur = conn.cursor()
            execute_values(cur, insert_sql, batch, fetch=False)
            conn.commit()
            cur.close()
            total_attempted += len(batch)
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            # Log but continue with next batch
            import logging
            logging.warning(f"Failed to insert batch at offset {i}: {e}")
            raise
        finally:
            _put_connection(dbname, conn)

    return total_attempted
