param(
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
$logPath = Join-Path $logDir "safe-publish-$timestamp.log"
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

Write-Host "Publishing college football site outputs from current local data..." -ForegroundColor Cyan
Write-Host "Log file: $logPath" -ForegroundColor DarkGray
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkGray
Write-Host ""

$exitCode = Invoke-LoggedProcess -Label "Build published outputs" -FilePath "python" -ArgumentList @("-u", "manage.py", "build-published") -LogPath $logPath
if ($exitCode -ne 0) {
    $stopwatch.Stop()
    Write-Host ""
    Write-Host "Published build failed. Review the log file for details:" -ForegroundColor Red
    Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Yellow
    Write-Host $logPath -ForegroundColor Yellow
    exit $exitCode
}

Write-Host ""
Write-Host "Auditing internal links..." -ForegroundColor Cyan
$exitCode = Invoke-LoggedProcess -Label "Audit built-site links" -FilePath "python" -ArgumentList @("-u", "manage.py", "audit-links", "--strict") -LogPath $logPath
$stopwatch.Stop()

Write-Host ""
if ($exitCode -ne 0) {
    Write-Host "Link audit failed. Review the log file for details:" -ForegroundColor Red
    Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Yellow
    Write-Host $logPath -ForegroundColor Yellow
    exit $exitCode
}

$reportPath = Join-Path $repoRoot "output\rankings.html"
$sitePath = Join-Path $repoRoot "output\site\index.html"
Write-Host "Published build finished successfully." -ForegroundColor Green
Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Green
Write-Host "Standalone report: $reportPath" -ForegroundColor Green
Write-Host "Full static site home: $sitePath" -ForegroundColor Green
Write-Host "Log file: $logPath" -ForegroundColor Green

if ($OpenReport) {
    Start-Process $sitePath | Out-Null
}
