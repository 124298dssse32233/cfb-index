$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot
$env:PYTHONUNBUFFERED = "1"

Write-Host "Refreshing college football site data and rankings..." -ForegroundColor Cyan
python -u manage.py sync-site-incremental --open-report

Write-Host ""
Write-Host "If the page did not open automatically, use this file:" -ForegroundColor Green
Write-Host "$repoRoot\output\rankings.html"
Write-Host ""
Write-Host "Full static site home:" -ForegroundColor Green
Write-Host "$repoRoot\output\site\index.html"
