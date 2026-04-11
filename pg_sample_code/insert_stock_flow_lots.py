# -*- coding: UTF-8 -*-
"""
Insert / upsert stock flow (lots) records into PostgreSQL using the project's db_util style.
Usage examples:
  python pg_sample_code/insert_stock_flow_lots.py --input-dir data/processed --db tw
  python pg_sample_code/insert_stock_flow_lots.py --file data/processed/20260402/target__a-1030__b-1030.csv --db tw

Notes:
- Depends on pandas, tqdm (optional). The repository already contains db_util.py for DB access.
- The script looks for CSVs produced by the scraper (columns documented in README / storage.py).
- SQL uses ON CONFLICT (...) DO UPDATE to perform upserts.
"""

from __future__ import annotations

import argparse
import os
import glob
import datetime
import pandas as pd
from tqdm import tqdm

from db_util import db99exec


INSERT_CHUNK_ROWS = 1000

FIELDNAMES = [
    "trade_date",
    "broker_code",
    "branch_code",
    "branch_code_raw",
    "broker_name",
    "branch_name",
    "stock_code",
    "stock_name",
    "buy_lots",
    "sell_lots",
    "net_lots",
    "metric_type",
    "source_url",
    "fetched_at",
]


def sql_txt(val: object, quote: bool = True) -> str:
    if val is None:
        return "NULL"
    s = str(val)
    s = s.strip()
    if s == "":
        return "NULL"
    if not quote:
        # numeric
        try:
            return str(int(float(s.replace(',', ''))))
        except Exception:
            return "NULL"
    # quote and escape single quotes
    return "'" + s.replace("'", "''") + "'"


def process_dataframe(df: pd.DataFrame, dbname: str, chunk_rows: int = INSERT_CHUNK_ROWS) -> None:
    """Bulk insert using psycopg2.extras.execute_values with parameterized queries.
    Uses ON CONFLICT ... DO NOTHING as requested.
    """
    import db_util
    try:
        from psycopg2.extras import execute_values
    except Exception:
        raise RuntimeError("psycopg2 is required for DB inserts. Install psycopg2-binary")

    insert_sql = """INSERT INTO public.stock_flow_lots_detailed(
    da, stock_code, stock_name, broker_code, branch_code, branch_code_raw,
    broker_name, branch_name, buy_lots, sell_lots, net_lots, source_url, fetched_at, created_at
) VALUES %s
ON CONFLICT ON CONSTRAINT stock_flow_lots_detailed_pkey DO NOTHING;
"""

    def to_int(v):
        if v is None:
            return None
        s = str(v).strip()
        if s == "" or s in {"--", "N/A"}:
            return None
        try:
            return int(float(s.replace(',', '')))
        except Exception:
            return None

    rows_batch: list[tuple] = []
    total_attempted = 0

    for _, row in df.iterrows():
        def g(key):
            return row.get(key, None) if key in row.index else None

        trade_date = g("trade_date")
        # convert trade_date to datetime if possible
        da_val = None
        if isinstance(trade_date, str) and trade_date:
            try:
                da_val = datetime.datetime.fromisoformat(trade_date)
            except Exception:
                try:
                    da_val = datetime.datetime.strptime(trade_date, "%Y-%m-%d")
                except Exception:
                    da_val = None
        elif isinstance(trade_date, (datetime.date, datetime.datetime)):
            if isinstance(trade_date, datetime.datetime):
                da_val = trade_date
            else:
                da_val = datetime.datetime.combine(trade_date, datetime.time.min)

        broker_code = g("broker_code")
        branch_code = g("branch_code")
        branch_code_raw = g("branch_code_raw")
        broker_name = g("broker_name")
        branch_name = g("branch_name")
        stock_code = g("stock_code")
        stock_name = g("stock_name")
        buy_lots = to_int(g("buy_lots"))
        sell_lots = to_int(g("sell_lots"))
        net_lots = to_int(g("net_lots"))
        source_url = g("source_url")
        fetched_at = g("fetched_at")
        if isinstance(fetched_at, str) and fetched_at:
            try:
                fetched_at_val = datetime.datetime.fromisoformat(fetched_at)
            except Exception:
                fetched_at_val = fetched_at
        else:
            fetched_at_val = fetched_at

        created_at = datetime.datetime.now()

        # ensure code has ' TT Equity' suffix per user request
        code_field = None
        if stock_code is not None:
            s = str(stock_code).strip()
            code_field = f"{s} TT Equity" if not s.endswith("TT Equity") else s

        rows_batch.append((
            da_val, code_field, stock_name, broker_code, branch_code, branch_code_raw,
            broker_name, branch_name, buy_lots, sell_lots, net_lots, source_url, fetched_at_val, created_at
        ))

        if len(rows_batch) >= chunk_rows:
            conn = db_util.getconn(dbname)
            try:
                cur = conn.cursor()
                execute_values(cur, insert_sql, rows_batch, template=None, page_size=chunk_rows)
                conn.commit()
                cur.close()
                total_attempted += len(rows_batch)
            except Exception as e:
                print("DB bulk insert error:", e)
                try:
                    conn.rollback()
                except Exception:
                    pass
            finally:
                # return connection to pool
                db_util.conn_pools[dbname].putconn(conn)
            rows_batch = []

    # flush remainder
    if rows_batch:
        conn = db_util.getconn(dbname)
        try:
            cur = conn.cursor()
            execute_values(cur, insert_sql, rows_batch, template=None, page_size=chunk_rows)
            conn.commit()
            cur.close()
            total_attempted += len(rows_batch)
        except Exception as e:
            print("DB bulk insert error:", e)
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            db_util.conn_pools[dbname].putconn(conn)

    print(f"Attempted to insert {total_attempted} rows (ON CONFLICT DO NOTHING may skip duplicates).")


def find_csvs(input_dir: str, start_date: str | None = None, end_date: str | None = None) -> list:
    files: list[str] = []
    if start_date and end_date:
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        cur = start
        while cur <= end:
            folder = os.path.join(input_dir, cur.strftime('%Y%m%d'))
            if os.path.isdir(folder):
                files.extend(glob.glob(os.path.join(folder, "*.csv")))
            cur = cur + datetime.timedelta(days=1)
    else:
        # recursive find
        files = glob.glob(os.path.join(input_dir, "**", "*.csv"), recursive=True)
    return sorted(files)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Insert stock_flow_lots CSVs into Postgres (upsert).")
    parser.add_argument("--input-dir", default="data/processed", help="Processed CSV root folder")
    parser.add_argument("--file", help="Single CSV file to process")
    parser.add_argument("--db", default="tw", help="Database name configured in db_util.getconn")
    parser.add_argument("--start-date", help="YYYY-MM-DD")
    parser.add_argument("--end-date", help="YYYY-MM-DD")
    parser.add_argument("--chunk-rows", type=int, default=INSERT_CHUNK_ROWS)
    args = parser.parse_args(argv)

    if args.file:
        files = [args.file]
    else:
        files = find_csvs(args.input_dir, args.start_date, args.end_date)

    if not files:
        print("No CSV files found to process.")
        return

    for f in tqdm(files, desc="CSV files"):
        try:
            df = pd.read_csv(f, encoding='utf-8-sig', dtype=str)
        except Exception as e:
            print(f"Failed to read {f}: {e}")
            continue
        process_dataframe(df, args.db, chunk_rows=args.chunk_rows)


if __name__ == '__main__':
    main()
