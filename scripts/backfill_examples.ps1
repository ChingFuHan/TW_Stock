<#
Backfill 指令範例與快速執行範本

用法範例：
  # 列出範例
  .\scripts\backfill_examples.ps1 -Action list

  # 執行範例（例如 full_history）
  .\scripts\backfill_examples.ps1 -Action run -Example full_history

說明：此檔提供常用範例的快速執行介面，方便排程或手動執行。
#>

param(
    [string]$Action = "list",   # list | run
    [string]$Example = "full_history"  # 範例名稱
)

$PY = ".venv\Scripts\python.exe"
$SCRIPT = "scripts\backfill_daily.py"

$examples = @{ 
    "full_history"    = "$PY $SCRIPT --start-date 2017-01-01 --end-date 2026-04-10"
    "dry_run_preview" = "$PY $SCRIPT --start-date 2017-01-01 --end-date 2026-04-10 --resume --dry-run"
    "resume"          = "$PY $SCRIPT --start-date 2017-01-01 --end-date 2026-04-10 --resume"
    "db_write_week"   = "$PY $SCRIPT --start-date 2026-04-01 --end-date 2026-04-10 --db-name tw"
    "retry_failed"    = "$PY $SCRIPT --start-date 2017-01-01 --end-date 2026-04-10 --resume --retry-failed"
    "daily_schedule"  = "$PY $SCRIPT --start-date $(Get-Date -Format yyyy-MM-dd) --end-date $(Get-Date -Format yyyy-MM-dd) --resume --db-name tw"
    "force_replay"    = "$PY $SCRIPT --start-date 2026-04-01 --end-date 2026-04-10 --no-skip-existing"
    "empty_no_retry"  = "$PY $SCRIPT --start-date 2026-04-01 --end-date 2026-04-10 --resume --empty-retry-days 0"
    "metric_amount"   = "$PY $SCRIPT --start-date 2026-04-01 --end-date 2026-04-10 --metric-type amount --db-name tw"
}

if ($Action -eq "list") {
    Write-Output "可用範例："
    $examples.GetEnumerator() | ForEach-Object { Write-Output ("{0} : {1}" -f $_.Key, $_.Value) }
    exit 0
}

if ($Action -eq "run") {
    if (-not $examples.ContainsKey($Example)) {
        Write-Error "找不到範例: $Example. 使用 -Action list 列出。"
        exit 1
    }
    $cmd = $examples[$Example]
    Write-Output "執行: $cmd"
    # 使用 Invoke-Expression 執行命令（在 PowerShell 中）
    Invoke-Expression $cmd
    exit $LASTEXITCODE
}

Write-Error "未知 Action。用 -Action list 或 -Action run"
exit 1
