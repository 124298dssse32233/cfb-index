$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot
$env:PYTHONUNBUFFERED = "1"

Write-Host "Publishing college football site outputs from current local data..." -ForegroundColor Cyan
python -u manage.py build-team-preview-layer
python -u manage.py build-published

Write-Host ""
Write-Host "Auditing internal links..." -ForegroundColor Cyan
python -u manage.py audit-links --strict
if ($LASTEXITCODE -ne 0) {
    Write-Host "Link audit failed. Fix broken links before publishing." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Standalone report:" -ForegroundColor Green
Write-Host "$repoRoot\output\rankings.html"
Write-Host ""
Write-Host "Full static site home:" -ForegroundColor Green
Write-Host "$repoRoot\output\site\index.html"
