param(
    [Parameter(Mandatory = $true)]
    [int]$StartSeason,
    [Parameter(Mandatory = $true)]
    [int]$EndSeason,
    [switch]$IncludePostseason,
    [switch]$RunModels,
    [switch]$BuildSite,
    [switch]$IncludeHeisman,
    [switch]$IncludePlayLevel
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot
$env:PYTHONUNBUFFERED = "1"
. (Join-Path $repoRoot "scripts\Invoke-LoggedProcess.ps1")

$logDir = Join-Path $repoRoot "output\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $logDir "backfill-$StartSeason-$EndSeason-$timestamp.log"
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

$arguments = @(
    "manage.py",
    "backfill-cfbd-history",
    "--start-season", "$StartSeason",
    "--end-season", "$EndSeason"
)

if ($IncludePostseason) {
    $arguments += "--include-postseason"
}

if ($RunModels) {
    $arguments += "--run-models"
}

if ($BuildSite) {
    $arguments += "--build-site"
}

if (-not $IncludeHeisman) {
    $arguments += "--skip-heisman"
}

if (-not $IncludePlayLevel) {
    $arguments += "--skip-play-level"
}

Write-Host "Running logged CFBD backfill..." -ForegroundColor Cyan
Write-Host "Log file: $logPath" -ForegroundColor DarkGray
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkGray
Write-Host ""

Write-Host "Running CFBD connectivity preflight..." -ForegroundColor Yellow
$exitCode = Invoke-LoggedProcess -Label "CFBD connectivity preflight" -FilePath "python" -ArgumentList @("-u", "manage.py", "check-cfbd-connectivity", "--season", "$StartSeason") -LogPath $logPath
if ($exitCode -ne 0) {
    $stopwatch.Stop()
    Write-Host ""
    Write-Host "Connectivity preflight failed. Skipping the heavy backfill run." -ForegroundColor Red
    Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Yellow
    Write-Host $logPath -ForegroundColor Yellow
    exit $exitCode
}

$exitCode = Invoke-LoggedProcess -Label "CFBD history backfill" -FilePath "python" -ArgumentList (@("-u") + $arguments) -LogPath $logPath
$stopwatch.Stop()

Write-Host ""
if ($exitCode -ne 0) {
    Write-Host "Backfill failed. Review the log file for details:" -ForegroundColor Red
    Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Yellow
    Write-Host $logPath -ForegroundColor Yellow
    exit $exitCode
}

Write-Host "Backfill finished successfully." -ForegroundColor Green
Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Green
Write-Host "Log file: $logPath" -ForegroundColor Green
