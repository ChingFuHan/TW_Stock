#!/usr/bin/env python3
r"""
從 0 建立 PostgreSQL 資料表（執行 pg_sample_code/create_*.sql）。

連線資訊讀自專案根目錄的 .env（PGHOST/PGPORT/PGUSER/PGPASSWORD，或單一 DATABASE_URL）。
所有建表 SQL 皆為 CREATE ... IF NOT EXISTS，可重複執行（idempotent）。

用法：
  # 建立回補所需的兩張表（預設：brokers/branches + stock_flow_lots_detailed）
  .venv\Scripts\python.exe scripts\init_db.py --db tw

  # 自訂要執行的 SQL 檔
  .venv\Scripts\python.exe scripts\init_db.py --db tw --sql create_brokers_branches.sql

注意：create_stock_flow_lots.sql 與 create_stock_flow_lots_detailed.sql 使用同名索引
（stock_flow_stock_date_idx），同一個資料庫不要兩張都建。回補實際只寫 stock_flow_lots_detailed。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# 載入 .env（若有）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ModuleNotFoundError:
    print(
        "[warn] python-dotenv 未安裝，.env 不會被載入；"
        r" 請先執行： .\.venv\Scripts\python.exe -m pip install -r requirements.txt",
        file=sys.stderr,
    )

try:
    import psycopg2
except ModuleNotFoundError:
    print(
        "[error] 缺少 psycopg2，無法連線資料庫；"
        r" 請先執行： .\.venv\Scripts\python.exe -m pip install -r requirements.txt",
        file=sys.stderr,
    )
    raise

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = PROJECT_ROOT / "pg_sample_code"

# 預設只建回補實際需要的表（避開 stock_flow_lots 與 detailed 的同名索引衝突）
DEFAULT_SQL_FILES = [
    "create_brokers_branches.sql",
    "create_stock_flow_lots_detailed.sql",
]


def split_statements(sql_text: str) -> list[str]:
    """把 SQL 檔切成單句（這些 DDL 無 function/dollar-quote，可安全以 ; 切分）。"""
    statements = []
    for raw in sql_text.split(";"):
        # 去掉純註解行後若還有實際 SQL 才保留
        code = "\n".join(
            line for line in raw.splitlines() if not line.strip().startswith("--")
        ).strip()
        if code:
            statements.append(raw.strip())
    return statements


def connect(dbname: str):
    """以 .env / 環境變數連線（比照 db_writer 的 env 連線路徑）。"""
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="從 0 建立 PostgreSQL 資料表")
    parser.add_argument("--db", default="tw", help="資料庫名稱 (預設: tw)")
    parser.add_argument(
        "--sql",
        nargs="*",
        default=DEFAULT_SQL_FILES,
        help="要執行的 SQL 檔名（位於 pg_sample_code/，預設為 brokers/branches + stock_flow_lots_detailed）",
    )
    args = parser.parse_args(argv)

    # 先檢查檔案都存在
    sql_paths = []
    for name in args.sql:
        path = SQL_DIR / name
        if not path.exists():
            print(f"[error] 找不到 SQL 檔: {path}", file=sys.stderr)
            return 2
        sql_paths.append(path)

    conn = connect(args.db)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        # 避免在已有資料/有人連線的線上 DB 上，CREATE INDEX 卡在鎖等待而無限等待；
        # 逾時會丟錯被下面的 try/except 接住印 [skip]。空 DB 從 0 建表時不受影響。
        cur.execute("SET lock_timeout = '15s'")
        for path in sql_paths:
            print(f"==> 執行 {path.name} ...")
            for stmt in split_statements(path.read_text(encoding="utf-8")):
                try:
                    cur.execute(stmt)
                except psycopg2.Error as exc:
                    # 既有資料庫的表/索引可能與此 DDL 不同（例如 legacy 欄名），
                    # 屬非致命，警告後繼續下一句。autocommit 下單句失敗不影響其他句。
                    first_line = str(exc).strip().splitlines()[0]
                    print(f"   [skip] {first_line}", file=sys.stderr)
        cur.close()
    finally:
        conn.close()

    print(f"[OK] 資料表建立完成（db={args.db}）")
    print("下一步：")
    print("  - （選用）灌參考表： .\\.venv\\Scripts\\python.exe scripts\\update_brokers.py --db " + args.db)
    print("  - 回補 flow 資料：   .\\.venv\\Scripts\\python.exe scripts\\backfill_daily.py "
          "--start-date 2026-06-18 --end-date 2026-06-22 --db-name " + args.db + " --resume")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
