#!/usr/bin/env python3
r"""
歷史資料回補 / 每日更新腳本

逐日呼叫 tw_broker_flows 抓取券商分點交易資料。
支援斷點續傳：已完成的日期自動跳過。

用法範例：
  # 歷史回補（2017 年至今）
  .venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2017-01-01 --end-date 2026-04-10

  # 指定 metric-type
  .venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2025-01-01 --end-date 2025-12-31 --metric-type lots

  # 直接寫入資料庫
  .venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2026-04-01 --end-date 2026-04-10 --db-name tw

  # 每日更新（只抓今天）
  .venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2026-04-10 --end-date 2026-04-10

  # 從斷點繼續（讀取 progress 檔案，自動跳過已完成的日期）
  .venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2017-01-01 --end-date 2026-04-10 --resume

  # Dry-run 模式（只列出要抓的日期，不實際執行）
  .venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2024-01-01 --end-date 2024-01-31 --dry-run
"""
from __future__ import annotations

import sys
import os
import argparse
import json
import logging
import subprocess
import time
from datetime import datetime, date, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# 常數
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXE = sys.executable  # 使用當前 Python 直譯器
PROGRESS_FILE = PROJECT_ROOT / "data" / "logs" / "backfill_progress.json"
DEFAULT_METRIC = "lots"
DEFAULT_MAX_WORKERS = 15
DEFAULT_DELAY_BETWEEN_DAYS = 1.0  # 秒，避免被封鎖
DEFAULT_EMPTY_RETRY_DAYS = 30  # 空資料在此天數內仍會重試

# ---------------------------------------------------------------------------
# 日誌設定
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 進度管理（斷點續傳）
# ---------------------------------------------------------------------------
def load_progress(progress_path: Path) -> dict:
    """載入已完成日期的進度檔案。"""
    if not progress_path.exists():
        return {"completed_dates": {}, "failed_dates": {}}
    try:
        data = json.loads(progress_path.read_text(encoding="utf-8"))
        if "completed_dates" not in data:
            data["completed_dates"] = {}
        if "failed_dates" not in data:
            data["failed_dates"] = {}
        return data
    except Exception as e:
        logger.warning(f"無法讀取進度檔案 {progress_path}: {e}，將從頭開始")
        return {"completed_dates": {}, "failed_dates": {}}


def save_progress(progress_path: Path, progress: dict) -> None:
    """儲存進度到 JSON 檔案。"""
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(
        json.dumps(progress, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def mark_date_completed(progress: dict, date_str: str, stats: dict) -> None:
    """標記某日為完成。"""
    progress["completed_dates"][date_str] = {
        "completed_at": datetime.now().isoformat(),
        **stats,
    }
    # 從失敗清單中移除（如果重試成功）
    progress["failed_dates"].pop(date_str, None)


def mark_date_failed(progress: dict, date_str: str, error: str) -> None:
    """標記某日為失敗。"""
    progress["failed_dates"][date_str] = {
        "failed_at": datetime.now().isoformat(),
        "error": error,
    }


# ---------------------------------------------------------------------------
# 日期工具
# ---------------------------------------------------------------------------
def generate_weekdays(start_date: str, end_date: str) -> list[str]:
    """產生日期範圍內的所有工作日（週一至週五）。"""
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    dates: list[str] = []
    current = start
    while current <= end:
        if current.weekday() < 5:  # 0=Mon, 4=Fri
            dates.append(current.isoformat())
        current += timedelta(days=1)

    return dates


def is_empty_and_recent(progress: dict, date_str: str, retry_days: int) -> bool:
    """
    判斷某日是否為「近期空資料」——應該重試而非永久跳過。

    規則：
    - 該日已完成但 csv_count == 0（空資料，CSV 模式）
    - 該日已完成但 db_successes == 0（空資料，DB 模式，無任何 branch 成功）
    - 距離今天不超過 retry_days 天
    - 超過 retry_days 天的空資料視為永久完成（假日/非交易日）
    """
    entry = progress["completed_dates"].get(date_str)
    if not entry:
        return False
    
    # CSV 模式：有資料就不重試
    if entry.get("csv_count", 0) > 0:
        return False
    
    # DB 模式：有任何成功就不重試
    if entry.get("db_successes", 0) > 0:
        return False
    
    # 確認確實是空資料（沒有 CSV，也沒有 DB 寫入成功）
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return (date.today() - d).days <= retry_days


# ---------------------------------------------------------------------------
# 單日抓取
# ---------------------------------------------------------------------------
def parse_scraper_stats(output: str) -> dict:
    """
    從 scraper output 擷取統計數據（successes/failures）。
    
    範例：
      2026-04-13 01:22:59,979 INFO Finished. successes=899 failures=1 log=...
    """
    stats = {}
    lines = output.strip().splitlines()
    for line in lines:
        if "successes=" in line:
            import re
            match_s = re.search(r"successes=(\d+)", line)
            match_f = re.search(r"failures=(\d+)", line)
            if match_s:
                stats["successes"] = int(match_s.group(1))
            if match_f:
                stats["failures"] = int(match_f.group(1))
            break
    return stats


def scrape_one_day(
    date_str: str,
    metric_type: str,
    max_workers: int,
    db_name: str | None,
    extra_args: list[str],
) -> tuple[int, str, dict]:
    """
    對單一日期執行抓取。

    回傳 (exit_code, output_summary, stats_dict)
    stats_dict 包含 {'successes': int, 'failures': int} 若 scraper 有輸出
    """
    cmd = [
        PYTHON_EXE, "-m", "src.tw_broker_flows",
        "--all-branches",
        "--metric-type", metric_type,
        "--start-date", date_str,
        "--end-date", date_str,
        "--max-workers", str(max_workers),
    ]

    if db_name:
        cmd.extend(["--db-name", db_name])

    cmd.extend(extra_args)

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=600,  # 10 分鐘超時
    )

    # 從 stdout/stderr 中擷取最後幾行作為摘要
    output = (result.stdout or "") + (result.stderr or "")
    lines = [l for l in output.strip().splitlines() if l.strip()]
    summary = lines[-1] if lines else "(no output)"
    
    # 解析統計數據
    stats = parse_scraper_stats(output)

    return result.returncode, summary, stats


# ---------------------------------------------------------------------------
# 結果檢查
# ---------------------------------------------------------------------------
def count_processed_csvs(date_str: str) -> int:
    """計算某日已產生的 CSV 檔案數量。"""
    date_folder = date_str.replace("-", "")
    processed_dir = PROJECT_ROOT / "data" / "processed" / date_folder
    if not processed_dir.exists():
        return 0
    return len(list(processed_dir.glob("*.csv")))


# ---------------------------------------------------------------------------
# 主程式
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="歷史資料回補 / 每日更新腳本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--start-date", required=True,
        help="開始日期 (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date", required=True,
        help="結束日期 (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--metric-type", default=DEFAULT_METRIC,
        choices=["amount", "lots", "both"],
        help=f"指標類型 (預設: {DEFAULT_METRIC})",
    )
    parser.add_argument(
        "--max-workers", type=int, default=DEFAULT_MAX_WORKERS,
        help=f"每日抓取的並行數 (預設: {DEFAULT_MAX_WORKERS})",
    )
    parser.add_argument(
        "--db-name",
        help="直接寫入指定的 PostgreSQL 資料庫",
    )
    parser.add_argument(
        "--delay", type=float, default=DEFAULT_DELAY_BETWEEN_DAYS,
        help=f"每日之間的延遲秒數 (預設: {DEFAULT_DELAY_BETWEEN_DAYS})",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="從上次進度繼續，自動跳過已完成的日期",
    )
    parser.add_argument(
        "--retry-failed", action="store_true",
        help="重新嘗試之前失敗的日期",
    )
    parser.add_argument(
        "--progress-file",
        default=str(PROGRESS_FILE),
        help=f"進度檔案路徑 (預設: {PROGRESS_FILE})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="只列出要抓的日期，不實際執行",
    )
    parser.add_argument(
        "--skip-existing", action="store_true", default=True,
        help="跳過已有 CSV 輸出的日期 (預設: 開啟)",
    )
    parser.add_argument(
        "--no-skip-existing", action="store_true",
        help="不跳過已有 CSV 的日期（強制重抓）",
    )
    parser.add_argument(
        "--empty-retry-days", type=int, default=DEFAULT_EMPTY_RETRY_DAYS,
        help=f"空資料日期的重試天數窗口 (預設: {DEFAULT_EMPTY_RETRY_DAYS})。"
             f"距離今天 N 天內的空資料仍會重新抓取，超過則視為永久完成（假日）。"
             f"設為 0 則不重試空資料。",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args, extra = parser.parse_known_args(argv)

    progress_path = Path(args.progress_file)
    progress = load_progress(progress_path) if args.resume else {
        "completed_dates": {},
        "failed_dates": {},
    }

    skip_existing = not args.no_skip_existing

    # 產生工作日清單
    all_dates = generate_weekdays(args.start_date, args.end_date)
    logger.info(
        f"日期範圍: {args.start_date} ~ {args.end_date}, "
        f"共 {len(all_dates)} 個工作日"
    )

    # 過濾要執行的日期
    dates_to_scrape: list[str] = []
    skipped_progress = 0
    skipped_existing = 0
    retry_empty = 0

    for d in all_dates:
        # 跳過已完成（進度檔案記錄的）
        if args.resume and d in progress["completed_dates"]:
            # 空資料在重試窗口內 → 仍需重新抓取
            if is_empty_and_recent(progress, d, args.empty_retry_days):
                retry_empty += 1
                dates_to_scrape.append(d)
                continue
            skipped_progress += 1
            continue

        # 跳過已失敗的（除非指定 --retry-failed）
        if args.resume and d in progress["failed_dates"] and not args.retry_failed:
            skipped_progress += 1
            continue

        # 跳過已有 CSV 輸出的日期
        if skip_existing and count_processed_csvs(d) > 0:
            skipped_existing += 1
            # 同步到進度檔案
            if d not in progress["completed_dates"]:
                mark_date_completed(progress, d, {
                    "csv_count": count_processed_csvs(d),
                    "source": "existing_files",
                })
            continue

        dates_to_scrape.append(d)

    logger.info(
        f"待抓取: {len(dates_to_scrape)} 天, "
        f"已跳過(進度): {skipped_progress}, "
        f"已跳過(既有CSV): {skipped_existing}"
        + (f", 空資料重試: {retry_empty}" if retry_empty > 0 else "")
    )

    if args.dry_run:
        logger.info("=== DRY-RUN 模式 ===")
        for i, d in enumerate(dates_to_scrape, 1):
            weekday_name = datetime.strptime(d, "%Y-%m-%d").strftime("%A")
            logger.info(f"  [{i}/{len(dates_to_scrape)}] {d} ({weekday_name})")
        logger.info(f"共 {len(dates_to_scrape)} 天需要抓取")
        # 儲存進度（含 skip_existing 的同步結果）
        if args.resume:
            save_progress(progress_path, progress)
        return 0

    # 統計
    total = len(dates_to_scrape)
    success_count = 0
    fail_count = 0
    empty_count = 0
    start_time = time.time()

    for idx, date_str in enumerate(dates_to_scrape, 1):
        elapsed = time.time() - start_time
        if idx > 1:
            avg_per_day = elapsed / (idx - 1)
            remaining = avg_per_day * (total - idx + 1)
            eta_str = f", 預計剩餘: {remaining / 60:.1f} 分鐘"
        else:
            eta_str = ""

        logger.info(
            f"[{idx}/{total}] 抓取 {date_str} "
            f"(成功:{success_count} 失敗:{fail_count} 空:{empty_count}{eta_str})"
        )

        try:
            exit_code, summary, stats = scrape_one_day(
                date_str=date_str,
                metric_type=args.metric_type,
                max_workers=args.max_workers,
                db_name=args.db_name,
                extra_args=extra,
            )

            csv_count = count_processed_csvs(date_str)

            # 判定成功條件（優先順序）：
            # 1. 有 CSV 產出（--db-name 無此項）
            # 2. --db-name 模式 + stats 中 successes > 0
            # 3. exit_code == 0（空資料或全部失敗但成功完成）
            
            if csv_count > 0:
                # CSV 模式：有輸出即完成
                success_count += 1
                if exit_code != 0:
                    logger.info(f"  ✓ 完成 (部分失敗): {csv_count} 個 CSV, exit_code={exit_code}")
                else:
                    logger.info(f"  ✓ 完成: {csv_count} 個 CSV")
                mark_date_completed(progress, date_str, {
                    "csv_count": csv_count,
                    "exit_code": exit_code,
                })
            elif args.db_name and stats.get("successes", 0) > 0:
                # DB 模式：有成功的 branch 寫入
                success_count += 1
                successes = stats.get("successes", 0)
                failures = stats.get("failures", 0)
                logger.info(
                    f"  ✓ 完成 (DB 寫入): {successes} 成功 {failures} 失敗"
                )
                mark_date_completed(progress, date_str, {
                    "csv_count": 0,
                    "exit_code": exit_code,
                    "db_successes": successes,
                    "db_failures": failures,
                    "source": "db_insert",
                })
            elif exit_code == 0:
                # 成功執行但無資料或無 CSV（非交易日或假日）
                empty_count += 1
                logger.info(f"  ○ 完成但無資料 (可能為非交易日或假日)")
                mark_date_completed(progress, date_str, {
                    "csv_count": 0,
                    "exit_code": exit_code,
                })
            else:
                # 真正的失敗：exit_code != 0 且沒有產出
                fail_count += 1
                logger.warning(f"  ✗ 失敗 (exit_code={exit_code}): {summary}")
                mark_date_failed(progress, date_str, summary)

        except subprocess.TimeoutExpired:
            fail_count += 1
            logger.error(f"  ✗ 逾時 (超過 600 秒)")
            mark_date_failed(progress, date_str, "timeout")

        except Exception as e:
            fail_count += 1
            logger.error(f"  ✗ 異常: {e}")
            mark_date_failed(progress, date_str, str(e))

        # 定期儲存進度（每 10 天）
        if idx % 10 == 0:
            save_progress(progress_path, progress)

        # 日期間延遲
        if idx < total and args.delay > 0:
            time.sleep(args.delay)

    # 最終儲存進度
    save_progress(progress_path, progress)

    # 最終統計
    total_elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info("回補完成！")
    logger.info(f"  日期範圍: {args.start_date} ~ {args.end_date}")
    logger.info(f"  工作日數: {len(all_dates)}")
    logger.info(f"  實際抓取: {total}")
    logger.info(f"  成功: {success_count}")
    logger.info(f"  失敗: {fail_count}")
    logger.info(f"  無資料: {empty_count}")
    logger.info(f"  跳過: {skipped_progress + skipped_existing}")
    logger.info(f"  總耗時: {total_elapsed / 60:.1f} 分鐘")
    if total > 0:
        logger.info(f"  平均每日: {total_elapsed / total:.1f} 秒")
    logger.info(f"  進度檔案: {progress_path}")
    logger.info("=" * 60)

    return 1 if fail_count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
