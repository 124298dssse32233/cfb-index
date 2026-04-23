param(
    [Parameter(Mandatory = $true)]
    [int]$StartSeason,
    [Parameter(Mandatory = $true)]
    [int]$EndSeason,
    [string]$Classification = "fbs",
    [int]$ChunkSize = 2,
    [switch]$SkipPreseason,
    [switch]$SkipRankings,
    [switch]$SkipUsage,
    [switch]$SkipValueMetrics,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot
$env:PYTHONUNBUFFERED = "1"
. (Join-Path $repoRoot "scripts\Invoke-LoggedProcess.ps1")

$logDir = Join-Path $repoRoot "output\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $logDir "player-context-$StartSeason-$EndSeason-$timestamp.log"
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

Write-Host "Running logged historical player-context backfill..." -ForegroundColor Cyan
Write-Host "Log file: $logPath" -ForegroundColor DarkGray
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkGray
Write-Host ""

Write-Host "Running CFBD connectivity preflight..." -ForegroundColor Yellow
$exitCode = Invoke-LoggedProcess -Label "CFBD connectivity preflight" -FilePath "python" -ArgumentList @("-u", "manage.py", "check-cfbd-connectivity", "--season", "$StartSeason") -LogPath $logPath
if ($exitCode -ne 0) {
    $stopwatch.Stop()
    Write-Host ""
    Write-Host "Connectivity preflight failed. Skipping the player-context backfill." -ForegroundColor Red
    Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Yellow
    Write-Host $logPath -ForegroundColor Yellow
    exit $exitCode
}

for ($chunkStart = $StartSeason; $chunkStart -le $EndSeason; $chunkStart += $ChunkSize) {
    $chunkEnd = [Math]::Min($chunkStart + $ChunkSize - 1, $EndSeason)
    $arguments = @(
        "manage.py",
        "backfill-player-context",
        "--start-season", "$chunkStart",
        "--end-season", "$chunkEnd",
        "--classification", $Classification
    )

    if ($SkipPreseason) {
        $arguments += "--skip-preseason"
    }
    if ($SkipRankings) {
        $arguments += "--skip-rankings"
    }
    if ($SkipUsage) {
        $arguments += "--skip-usage"
    }
    if ($SkipValueMetrics) {
        $arguments += "--skip-value-metrics"
    }
    if ($Force) {
        $arguments += "--force"
    }

    Write-Host "Chunk $chunkStart-$chunkEnd..." -ForegroundColor Yellow
    $exitCode = Invoke-LoggedProcess -Label "Player context chunk $chunkStart-$chunkEnd" -FilePath "python" -ArgumentList (@("-u") + $arguments) -LogPath $logPath
    if ($exitCode -ne 0) {
        $stopwatch.Stop()
        Write-Host ""
        Write-Host "Player-context backfill failed. Review the log file for details:" -ForegroundColor Red
        Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Yellow
        Write-Host $logPath -ForegroundColor Yellow
        exit $exitCode
    }
}

$stopwatch.Stop()
Write-Host ""
Write-Host "Historical player-context backfill finished successfully." -ForegroundColor Green
Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Green
Write-Host "Log file: $logPath" -ForegroundColor Green
