param(
    [int]$StartSeason = 2014,
    [int]$EndSeason = 0,
    [string]$SiteDir = "output\\site",
    [string]$OutputPath = "output\\local-health-refresh.md",
    [switch]$SkipLinkAudit,
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
$logPath = Join-Path $logDir "safe-local-health-$timestamp.log"
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

$arguments = @(
    "manage.py",
    "refresh-local-health",
    "--start-season", "$StartSeason",
    "--site-dir", "$SiteDir",
    "--output", "$OutputPath"
)
if ($EndSeason -gt 0) {
    $arguments += @("--end-season", "$EndSeason")
}
if ($SkipLinkAudit) {
    $arguments += "--skip-link-audit"
}

Write-Host "Refreshing local health artifacts..." -ForegroundColor Cyan
Write-Host "Log file: $logPath" -ForegroundColor DarkGray
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkGray
Write-Host ""

$exitCode = Invoke-LoggedProcess -Label "Local health refresh" -FilePath "python" -ArgumentList (@("-u") + $arguments) -LogPath $logPath
$stopwatch.Stop()

Write-Host ""
if ($exitCode -ne 0) {
    Write-Host "Local health refresh failed. Review the log file for details:" -ForegroundColor Red
    Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Yellow
    Write-Host $logPath -ForegroundColor Yellow
    exit $exitCode
}

$resolvedOutputPath = Join-Path $repoRoot $OutputPath
Write-Host "Local health refresh finished successfully." -ForegroundColor Green
Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Green
Write-Host "Summary: $resolvedOutputPath" -ForegroundColor Green
Write-Host "Log file: $logPath" -ForegroundColor Green

$queuePath = Join-Path $repoRoot "output\maintenance-action-queue.json"
if (Test-Path $queuePath) {
    try {
        $queue = Get-Content $queuePath -Raw | ConvertFrom-Json
        $summary = $queue.summary
        Write-Host "Action queue: $($summary.actionCount) open actions (P0: $($summary.p0), P1: $($summary.p1), P2: $($summary.p2))" -ForegroundColor Green
        $topActions = @($queue.actions | Select-Object -First 3)
        foreach ($action in $topActions) {
            Write-Host " - [$($action.priority)] $($action.area): $($action.title)" -ForegroundColor DarkGray
        }
        Write-Host "Queue file: $(Join-Path $repoRoot 'output\maintenance-action-queue.md')" -ForegroundColor Green
    }
    catch {
        Write-Host "Action queue exists but could not be parsed: $queuePath" -ForegroundColor Yellow
        Write-Host $_.Exception.Message -ForegroundColor Yellow
    }
}

if ($OpenReport) {
    Start-Process $resolvedOutputPath | Out-Null
}
