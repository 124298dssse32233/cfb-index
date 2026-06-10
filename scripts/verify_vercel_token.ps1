# verify_vercel_token.ps1 -- confirms VERCEL_TOKEN authenticates, WITHOUT deploying.
# Read-only: runs `vercel whoami` + lists the team's projects. Never publishes.
$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$env:FORCE_COLOR = "0"
$SCOPE = "team_gR4aMSXbAnKOXs49An6tIStd"

# Load VERCEL_TOKEN from .env if not already in env.
if ([string]::IsNullOrWhiteSpace($env:VERCEL_TOKEN)) {
    if (Test-Path ".env") {
        foreach ($line in Get-Content ".env") {
            if ($line -match '^\s*VERCEL_TOKEN\s*=\s*(.+?)\s*$') {
                $env:VERCEL_TOKEN = ($matches[1].Trim('"').Trim("'"))
            }
        }
    }
}

if ([string]::IsNullOrWhiteSpace($env:VERCEL_TOKEN)) {
    Write-Output "RESULT: NO TOKEN -- .env has an empty VERCEL_TOKEN=. Paste your token after the = and re-run."
    exit 1
}

Write-Output "Token found (len $($env:VERCEL_TOKEN.Length)). Checking auth (no deploy)..."
Write-Output "--- vercel whoami ---"
& vercel whoami --token $env:VERCEL_TOKEN
$who = $LASTEXITCODE
Write-Output "--- vercel project ls (scope $SCOPE) ---"
& vercel project ls --scope $SCOPE --token $env:VERCEL_TOKEN
$ls = $LASTEXITCODE

if ($who -eq 0 -and $ls -eq 0) {
    Write-Output "RESULT: OK -- token authenticates and can see the team projects. Safe to publish on your go-ahead."
} else {
    Write-Output "RESULT: FAILED -- whoami=$who project-ls=$ls. Token may be wrong, expired, or scoped to the wrong team. Re-create at https://vercel.com/account/tokens"
}
