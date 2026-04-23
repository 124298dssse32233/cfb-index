param(
    [string]$OutputPath = "output\\archive-readiness-audit.md",
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
$logPath = Join-Path $logDir "safe-archive-audit-$timestamp.log"
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

$arguments = @(
    "manage.py",
    "audit-archive-readiness",
    "--output", "$OutputPath"
)

Write-Host "Generating safe archive readiness audit..." -ForegroundColor Cyan
Write-Host "Log file: $logPath" -ForegroundColor DarkGray
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkGray
Write-Host ""

$exitCode = Invoke-LoggedProcess -Label "Archive readiness audit" -FilePath "python" -ArgumentList (@("-u") + $arguments) -LogPath $logPath
$stopwatch.Stop()

Write-Host ""
if ($exitCode -ne 0) {
    Write-Host "Archive readiness audit failed. Review the log file for details:" -ForegroundColor Red
    Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Yellow
    Write-Host $logPath -ForegroundColor Yellow
    exit $exitCode
}

$resolvedOutputPath = Join-Path $repoRoot $OutputPath
Write-Host "Archive readiness audit finished successfully." -ForegroundColor Green
Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Green
Write-Host "Report: $resolvedOutputPath" -ForegroundColor Green
Write-Host "Log file: $logPath" -ForegroundColor Green

if ($OpenReport) {
    Start-Process $resolvedOutputPath | Out-Null
}
