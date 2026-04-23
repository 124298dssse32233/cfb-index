param(
    [Parameter(Mandatory = $true)]
    [int]$StartSeason,
    [Parameter(Mandatory = $true)]
    [int]$EndSeason,
    [switch]$IncludePostseason,
    [switch]$ForceFullSeason,
    [string[]]$Classification = @("fbs"),
    [int]$MaxWeeks,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot
$env:PYTHONUNBUFFERED = "1"
. (Join-Path $repoRoot "scripts\Invoke-LoggedProcess.ps1")

$logDir = Join-Path $repoRoot "output\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $logDir "game-player-stats-$StartSeason-$EndSeason-$timestamp.log"
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

$arguments = @(
    "manage.py",
    "backfill-game-player-stats",
    "--start-season", "$StartSeason",
    "--end-season", "$EndSeason"
)

if (-not $ForceFullSeason) {
    $arguments += "--missing-only"
}

if ($IncludePostseason) {
    $arguments += "--include-postseason"
}

foreach ($value in $Classification) {
    if (-not [string]::IsNullOrWhiteSpace($value)) {
        $arguments += @("--classification", $value.Trim().ToLowerInvariant())
    }
}

if ($PSBoundParameters.ContainsKey('MaxWeeks')) {
    $arguments += @("--max-weeks", "$MaxWeeks")
}

if ($DryRun) {
    $arguments += "--dry-run"
}

Write-Host "Running logged game-player-stat backfill..." -ForegroundColor Cyan
Write-Host "Log file: $logPath" -ForegroundColor DarkGray
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkGray
Write-Host "Classifications: $($Classification -join ', ')" -ForegroundColor DarkGray
if ($PSBoundParameters.ContainsKey('MaxWeeks')) {
    Write-Host "Week cap: $MaxWeeks" -ForegroundColor DarkGray
}
if ($DryRun) {
    Write-Host "Mode: dry run" -ForegroundColor DarkGray
}
Write-Host ""

if (-not $DryRun) {
    Write-Host "Running CFBD connectivity preflight..." -ForegroundColor Yellow
    $exitCode = Invoke-LoggedProcess -Label "CFBD connectivity preflight" -FilePath "python" -ArgumentList @("-u", "manage.py", "check-cfbd-connectivity", "--season", "$StartSeason") -LogPath $logPath
    if ($exitCode -ne 0) {
        $stopwatch.Stop()
        Write-Host ""
        Write-Host "Connectivity preflight failed. Skipping the game-player-stat backfill." -ForegroundColor Red
        Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Yellow
        Write-Host $logPath -ForegroundColor Yellow
        exit $exitCode
    }
}

$exitCode = Invoke-LoggedProcess -Label "Game player stats backfill" -FilePath "python" -ArgumentList (@("-u") + $arguments) -LogPath $logPath
$stopwatch.Stop()

Write-Host ""
if ($exitCode -ne 0) {
    Write-Host "Game-player-stat backfill failed. Review the log file for details:" -ForegroundColor Red
    Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Yellow
    Write-Host $logPath -ForegroundColor Yellow
    exit $exitCode
}

Write-Host "Game-player-stat backfill finished successfully." -ForegroundColor Green
Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Green
Write-Host "Log file: $logPath" -ForegroundColor Green
