param(
    [int]$Season = 0,
    [int]$ThroughWeek = 0,
    [switch]$IncludeHeisman,
    [switch]$SkipHeisman,
    [switch]$IncludePlayLevel,
    [switch]$SkipPlayLevel,
    [switch]$ForceModels,
    [switch]$OpenReport
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot
$env:PYTHONUNBUFFERED = "1"
. (Join-Path $repoRoot "scripts\Invoke-LoggedProcess.ps1")

$logDir = Join-Path $repoRoot "output\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $logDir "safe-sync-$timestamp.log"
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

$arguments = @("manage.py", "sync-site-incremental")

if ($Season -gt 0) {
    $arguments += @("--season", "$Season")
}

if ($ThroughWeek -gt 0) {
    $arguments += @("--through-week", "$ThroughWeek")
}

if ($SkipHeisman -or -not $IncludeHeisman) {
    $arguments += "--skip-heisman"
}

if ($SkipPlayLevel -or -not $IncludePlayLevel) {
    $arguments += "--skip-play-level"
}

if ($ForceModels) {
    $arguments += "--force-models"
}

if ($OpenReport) {
    $arguments += "--open-report"
}

Write-Host "Running safe incremental site refresh..." -ForegroundColor Cyan
Write-Host "Log file: $logPath" -ForegroundColor DarkGray
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkGray
Write-Host ""

$exitCode = Invoke-LoggedProcess -Label "Incremental site refresh" -FilePath "python" -ArgumentList (@("-u") + $arguments) -LogPath $logPath
$stopwatch.Stop()

Write-Host ""
if ($exitCode -ne 0) {
    Write-Host "Refresh failed. Review the log file for details:" -ForegroundColor Red
    Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Yellow
    Write-Host $logPath -ForegroundColor Yellow
    exit $exitCode
}

Write-Host "Refresh finished successfully." -ForegroundColor Green
Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Green
Write-Host "Rankings report: $repoRoot\output\rankings.html" -ForegroundColor Green
Write-Host "Full static site home: $repoRoot\output\site\index.html" -ForegroundColor Green
Write-Host "Log file: $logPath" -ForegroundColor Green
