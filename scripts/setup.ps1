# TW_Stock 一鍵環境設定（Windows PowerShell）
#
# 用法（在專案根目錄執行）：
#   .\scripts\setup.ps1
#
# 會自動完成 fresh clone 後必要的三步：
#   1) 建立 .venv 虛擬環境（若尚未存在）
#   2) 安裝相依套件（psycopg2-binary, python-dotenv 等）★最常被遺漏★
#   3) 由 .env.example 建立 .env（若尚未存在）
# 最後驗證套件是否就緒。

$ErrorActionPreference = "Stop"

# 切換到專案根目錄（此腳本位於 scripts/ 之下）
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
Write-Host "==> 專案根目錄: $root" -ForegroundColor Cyan

# 1) 建立 venv
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "==> 建立虛擬環境 .venv (Python 3.11)..." -ForegroundColor Cyan
    py -3.11 -m venv .venv
} else {
    Write-Host "==> .venv 已存在，略過建立" -ForegroundColor DarkGray
}

# 2) 安裝相依套件（關鍵步驟）
Write-Host "==> 安裝相依套件 (requirements.txt)..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3) 建立 .env
if (-not (Test-Path ".\.env")) {
    Copy-Item ".\.env.example" ".\.env"
    Write-Host "==> 已由 .env.example 建立 .env（請編輯填入 PostgreSQL 連線資訊）" -ForegroundColor Yellow
} else {
    Write-Host "==> .env 已存在，略過" -ForegroundColor DarkGray
}

# 4) 驗證
Write-Host "==> 驗證相依套件..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe -c "import psycopg2, dotenv; print('  deps OK: psycopg2', psycopg2.__version__)"

Write-Host ""
Write-Host "[OK] 環境設定完成。下一步：" -ForegroundColor Green
Write-Host "  1) 編輯 .env 填入 PGHOST / PGPORT / PGUSER / PGPASSWORD"
Write-Host "  2) 跑單日 DB 回補測試："
Write-Host "     .\.venv\Scripts\python.exe scripts\backfill_daily.py --start-date 2026-06-22 --end-date 2026-06-22 --db-name tw"
