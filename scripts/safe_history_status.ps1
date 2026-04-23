param(
    [int]$StartSeason = 2014,
    [int]$EndSeason = 2025,
    [string]$OutputPath = "output\\history-load-status.md",
    [switch]$OpenReport
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $repoRoot
Set-Location $repoRoot
$env:PYTHONUNBUFFERED = "1"
. (Join-Path $repoRoot "scripts\\Invoke-LoggedProcess.ps1")

$logDir = Join-Path $repoRoot "output\\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $logDir "safe-history-status-$timestamp.log"
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

$arguments = @(
    "manage.py",
    "history-load-status",
    "--start-season", "$StartSeason",
    "--end-season", "$EndSeason",
    "--output", "$OutputPath"
)

Write-Host "Generating safe history status report..." -ForegroundColor Cyan
Write-Host "Log file: $logPath" -ForegroundColor DarkGray
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkGray
Write-Host ""

$exitCode = Invoke-LoggedProcess -Label "History load status" -FilePath "python" -ArgumentList (@("-u") + $arguments) -LogPath $logPath
$stopwatch.Stop()

Write-Host ""
if ($exitCode -ne 0) {
    Write-Host "History status generation failed. Review the log file for details:" -ForegroundColor Red
    Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Yellow
    Write-Host $logPath -ForegroundColor Yellow
    exit $exitCode
}

$resolvedOutputPath = Join-Path $repoRoot $OutputPath
Write-Host "History status report finished successfully." -ForegroundColor Green
Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Green
Write-Host "Report: $resolvedOutputPath" -ForegroundColor Green
Write-Host "Log file: $logPath" -ForegroundColor Green

if ($OpenReport) {
    Start-Process $resolvedOutputPath | Out-Null
}
