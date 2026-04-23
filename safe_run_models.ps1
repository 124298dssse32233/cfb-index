param(
    [Parameter(Mandatory = $true)]
    [int]$Season,
    [Parameter(Mandatory = $true)]
    [int]$ThroughWeek,
    [switch]$IncludeHeisman,
    [switch]$SkipHeisman,
    [switch]$BuildPublished
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot
$env:PYTHONUNBUFFERED = "1"
. (Join-Path $repoRoot "scripts\Invoke-LoggedProcess.ps1")

$logDir = Join-Path $repoRoot "output\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $logDir "safe-models-$Season-w$ThroughWeek-$timestamp.log"
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

$arguments = @(
    "manage.py",
    "run-models",
    "--season", "$Season",
    "--through-week", "$ThroughWeek"
)

if ($SkipHeisman -or -not $IncludeHeisman) {
    $arguments += "--skip-heisman"
}

Write-Host "Running safe model refresh..." -ForegroundColor Cyan
Write-Host "Log file: $logPath" -ForegroundColor DarkGray
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkGray
Write-Host ""

$exitCode = Invoke-LoggedProcess -Label "Model refresh" -FilePath "python" -ArgumentList (@("-u") + $arguments) -LogPath $logPath

if ($exitCode -eq 0 -and $BuildPublished) {
    Write-Host ""
    Write-Host "Model run succeeded. Rebuilding published outputs..." -ForegroundColor Cyan
    $exitCode = Invoke-LoggedProcess -Label "Published rebuild" -FilePath "python" -ArgumentList @("-u", "manage.py", "build-published") -LogPath $logPath
}

$stopwatch.Stop()

Write-Host ""
if ($exitCode -ne 0) {
    Write-Host "Model run failed. Review the log file for details:" -ForegroundColor Red
    Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Yellow
    Write-Host $logPath -ForegroundColor Yellow
    exit $exitCode
}

Write-Host "Model run finished successfully." -ForegroundColor Green
Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Green
Write-Host "Log file: $logPath" -ForegroundColor Green
if ($BuildPublished) {
    Write-Host "Rankings report: $repoRoot\output\rankings.html" -ForegroundColor Green
    Write-Host "Full static site home: $repoRoot\output\site\index.html" -ForegroundColor Green
}
