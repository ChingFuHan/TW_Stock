<#
Backfill script: fetch daily "lots" (張數) for all broker branches, starting from StartDate (default today) and going backwards.
Stops when MaxConsecutiveNoData consecutive days produced no processed CSVs (default 30).

Usage examples:
  # Run with defaults (start today, stop after 30 consecutive no-data days)
  .\scripts\backfill_lots.ps1

  # Start from a specific date and override N
  .\scripts\backfill_lots.ps1 -StartDate '2026-04-11' -MaxConsecutiveNoData 30

Notes:
- Requires Python installed (preferably py launcher with -3.11).
- Uses local lookup JS at data\raw\samples\zbrokerjs.djjs by default.
- Output will be written under data\processed and logs to data\logs.
#>

param(
    [DateTime]$StartDate = ([DateTime]::UtcNow).Date,
    [int]$MaxConsecutiveNoData = 30,
    [string]$PythonCmd = "py",
    [string]$PythonVersionArg = "-3.11",
    [string]$RepoRoot = "C:\Users\User\Documents\TW_Stock",
    [int]$DelayBetweenDaysSec = 0
)

$lookupJs = Join-Path $RepoRoot "data\raw\samples\zbrokerjs.djjs"
$logsDir = Join-Path $RepoRoot "data\logs"
$processedRoot = Join-Path $RepoRoot "data\processed"

if (-not (Test-Path $lookupJs)) {
    Write-Error "Lookup JS not found: $lookupJs. Aborting."
    exit 2
}

if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir | Out-Null }
if (-not (Test-Path $processedRoot)) { New-Item -ItemType Directory -Path $processedRoot | Out-Null }

$consecutiveNoData = 0
$currentDate = $StartDate

Write-Output "Starting backfill from $($StartDate.ToString('yyyy-MM-dd')) backward. Stop after $MaxConsecutiveNoData consecutive no-data days."

while ($consecutiveNoData -lt $MaxConsecutiveNoData) {
    $dateStr = $currentDate.ToString('yyyy-MM-dd')
    $dateFolder = $dateStr -replace '-',''
    $processedFolder = Join-Path $processedRoot $dateFolder

    if (Test-Path $processedFolder) {
        try {
            $csvs = Get-ChildItem -Path $processedFolder -Filter *.csv -File -ErrorAction Stop
        } catch {
            $csvs = $null
        }
        if ($csvs -and $csvs.Count -gt 0) {
            Write-Output "[$dateStr] already processed: found $($csvs.Count) CSV(s). Resetting consecutive counter."
            $consecutiveNoData = 0
            $currentDate = $currentDate.AddDays(-1)
            Start-Sleep -Seconds $DelayBetweenDaysSec
            continue
        }
    }

    Write-Output "[$dateStr] running scraper..."
    $logFile = Join-Path $logsDir "backfill_$($dateFolder).log"
    $pythonArgs = @($PythonVersionArg, "-m", "src.tw_broker_flows",
                    "--all-branches", "--metric-type", "lots",
                    "--start-date", $dateStr, "--end-date", $dateStr,
                    "--lookup-js", $lookupJs,
                    "--output-dir", (Join-Path $RepoRoot "data"),
                    "--delay-seconds", "0.1"
                   )

    try {
        & $PythonCmd @pythonArgs 2>&1 | Tee-Object -FilePath $logFile
    } catch {
        Write-Warning "Python process failed to start: $_"
    }

    $exitCode = $LASTEXITCODE

    # After running, check processed folder again
    try {
        $csvs = Get-ChildItem -Path $processedFolder -Filter *.csv -File -ErrorAction Stop
    } catch {
        $csvs = $null
    }

    if ($csvs -and $csvs.Count -gt 0 -and $exitCode -eq 0) {
        Write-Output "[$dateStr] Success: $($csvs.Count) CSV(s) created. Resetting consecutive counter."
        $consecutiveNoData = 0
    } else {
        Write-Warning "[$dateStr] No CSVs created or non-zero exit code ($exitCode). Incrementing consecutive counter."
        $consecutiveNoData++
    }

    $currentDate = $currentDate.AddDays(-1)
    Start-Sleep -Seconds $DelayBetweenDaysSec
}

Write-Output "Stopping: reached $consecutiveNoData consecutive no-data days. Backfill complete."

exit 0
