@echo off
REM BACKFILL 指令範例範本 (Windows cmd)
REM 編輯後取消 REM 執行或直接複製到命令列

REM Full history:
REM .venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2017-01-01 --end-date 2026-04-10

REM Dry-run preview:
REM .venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2017-01-01 --end-date 2026-04-10 --resume --dry-run

REM Resume (從進度續抓):
REM .venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2017-01-01 --end-date 2026-04-10 --resume

REM DB write sample:
REM .venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2026-04-01 --end-date 2026-04-10 --db-name tw

REM Daily schedule (使用 %DATE% 或替換為固定日期):
REM .venv\Scripts\python.exe scripts\backfill_daily.py --start-date %DATE% --end-date %DATE% --resume --db-name tw

ECHO 範例已寫入此檔案。請編輯後取消 REM 並執行。