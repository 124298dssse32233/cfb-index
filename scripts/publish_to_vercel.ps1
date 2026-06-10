# publish_to_vercel.ps1
# Recurring local->live publish for the 24/7 box (Option A: box is source of truth).
# Deploys output/site DIRECTLY (not repo root) so the 1.3GB DB + .venv + repo
# junk are never uploaded -- only the ~2GB site. After the first full publish,
# Vercel has every file cached, so each run only uploads what the build changed
# (dedup) -> small + fast + well under the per-deploy cap.
#
# If a future FULL rebuild changes so many files that the diff exceeds the cap,
# run scripts/chunked_vercel_publish.ps1 once to re-prime, then this resumes.
#
# Safe by design: deploys are atomic and the public URL only switches on the
# alias step AFTER a healthy upload, so a failed/empty build never goes live.
$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$env:FORCE_COLOR = "0"
$SCOPE = "team_gR4aMSXbAnKOXs49An6tIStd"
$ALIAS = "wonderful-margulis-8ec96b.vercel.app"
$SITE  = Join-Path $RepoRoot "output\site"
$LogDir = Join-Path $RepoRoot "logs"; if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory $LogDir | Out-Null }
$LogPath = Join-Path $LogDir ("publish_vercel_{0:yyyy-MM-dd_HHmmss}.log" -f (Get-Date))
function Log([string]$m){ $s = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"; "$s  $m" | Tee-Object -FilePath $LogPath -Append }
function Clean([string]$x){ ($x -replace '(?<=\S) (?=\S)','') }

Log "==== publish_to_vercel START ===="

# 1. Sanity gate: refuse to deploy a missing/empty/poisoned build.
if (-not (Test-Path $SITE)) { Log "ABORT: output/site missing -- run build-site first."; exit 1 }
$fileCount = (Get-ChildItem -LiteralPath $SITE -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
Log "output/site file count: $fileCount"
if ($fileCount -lt 3500) { Log "ABORT: only $fileCount files (<3500) -- refusing to publish a broken/empty build."; exit 1 }

# 1b. DATA-QUALITY GATE + build-manifest freshness (Phase-1 reliability). Runs
#     BEFORE any Vercel interaction. Independent of the caller, so a manual publish
#     is gated too. A bad/stale/empty dataset can no longer reach the live site.
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$PyExe = if (Test-Path $VenvPython) { $VenvPython } else { "python" }
$env:PYTHONUTF8 = "1"
Log "gate: manage.py verify-publish-readiness ..."
(& $PyExe manage.py verify-publish-readiness 2>&1) | Tee-Object -FilePath $LogPath -Append
if ($LASTEXITCODE -ne 0) { Log "ABORT: verify-publish-readiness failed (exit $LASTEXITCODE) -- live site UNCHANGED."; exit 3 }
$Manifest = Join-Path $SITE "_build_manifest.json"
if (-not (Test-Path $Manifest)) { Log "ABORT: _build_manifest.json missing -- build did not complete cleanly. Live site UNCHANGED."; exit 4 }
$ageHours = ((Get-Date) - (Get-Item -LiteralPath $Manifest).LastWriteTime).TotalHours
if ($ageHours -gt 26) { Log ("ABORT: _build_manifest.json is {0:N1}h old (>26h) -- stale build. Live site UNCHANGED." -f $ageHours); exit 4 }
Log ("gate PASSED; manifest age {0:N1}h. Proceeding to deploy." -f $ageHours)

# 2. Ensure the project link + a complete vercel.json live INSIDE output/site
#    (build-site may wipe them). outputDirectory '.' so it serves the site root.
Copy-Item -LiteralPath (Join-Path $RepoRoot ".vercel") -Destination (Join-Path $SITE ".vercel") -Recurse -Force -ErrorAction SilentlyContinue
$vj = '{"$schema":"https://openapi.vercel.sh/vercel.json","outputDirectory":".","framework":null,"cleanUrls":false,"trailingSlash":true,"rewrites":[{"source":"/:slug([a-z][a-z0-9-]+).html","destination":"/teams/:slug.html"},{"source":"/today-in-history","destination":"/anniversary/today/index.html"},{"source":"/today-in-history/","destination":"/anniversary/today/index.html"}],"headers":[{"source":"/(.*)","headers":[{"key":"X-Robots-Tag","value":"index, follow"}]}]}'
[System.IO.File]::WriteAllText((Join-Path $SITE "vercel.json"), $vj)

# 2b. Authenticate non-interactively via VERCEL_TOKEN. Load it from .env if the
#     caller (e.g. daily_ingest) didn't already export it. A scheduled-task shell
#     has NO stored `vercel login` creds, so the token is the reliable path.
if ([string]::IsNullOrWhiteSpace($env:VERCEL_TOKEN)) {
    $envFile = Join-Path $RepoRoot ".env"
    if (Test-Path $envFile) {
        foreach ($line in Get-Content $envFile) {
            if ($line -match '^\s*VERCEL_TOKEN\s*=\s*(.+?)\s*$') {
                $env:VERCEL_TOKEN = ($matches[1].Trim('"').Trim("'"))
            }
        }
    }
}
$TokenArg = @()
if (-not [string]::IsNullOrWhiteSpace($env:VERCEL_TOKEN)) {
    $TokenArg = @("--token", $env:VERCEL_TOKEN)
    Log "auth: using VERCEL_TOKEN (non-interactive)."
} else {
    Log "auth: NO VERCEL_TOKEN found in env or .env -- deploy will FAIL on this box. Add VERCEL_TOKEN to .env (see https://vercel.com/account/tokens)."
}

# 3. Deploy output/site to production (archive=tgz handles the >15k file count).
#    Auto-retry on transient Vercel API errors: the /v2/files endpoint
#    intermittently returns a 500 "Internal Server error" (non-JSON) mid-upload
#    -> FetchError -> no URL captured. Observed ~3 of 4 attempts on 2026-06-09;
#    each cleared on retry, and the CLI itself advises "retry deploy". An
#    unattended daily publish must ride through this rather than skip the deploy.
Set-Location -LiteralPath $SITE
$url = $null
$MaxDeploy = 4
for ($i = 1; $i -le $MaxDeploy; $i++) {
    Log "deploying output/site to production (attempt $i/$MaxDeploy)..."
    $out = (& vercel deploy --prod --yes --archive=tgz --scope $SCOPE @TokenArg 2>&1 | ForEach-Object { Clean $_ })
    $out | Tee-Object -FilePath $LogPath -Append | Out-Null
    $url = ($out | Select-String -Pattern 'https://wonderful-margulis-8ec96b-[a-z0-9]+-[a-z0-9-]+\.vercel\.app' -AllMatches | ForEach-Object { $_.Matches.Value } | Select-Object -First 1)
    if ($url) { break }
    if ($i -lt $MaxDeploy) {
        $backoff = 10 * $i
        Log "   attempt $i captured no URL (transient Vercel API error?) -- retrying in ${backoff}s..."
        Start-Sleep -Seconds $backoff
    }
}
Set-Location -LiteralPath $RepoRoot
if (-not $url) { Log "FAIL: no production URL after $MaxDeploy attempts -- live site UNCHANGED. (cap exceeded? run chunked_vercel_publish.ps1)."; exit 2 }
Log "deploy URL: $url"

# 3b. Smoke-check the new deployment at its per-deploy URL BEFORE flipping the
#     public alias. The deploy is live at its per-deploy URL immediately while the
#     alias still points at the PREVIOUS (good) deploy, so if the new build is
#     broken (renders an error / empty / non-HTML despite passing the file-count
#     and data gates) we abort WITHOUT aliasing and the live site stays good.
#     Retry for cold-start warmup. Checks the homepage + one rewrite-routed team
#     page so a routing regression is caught too.
$smokeOk = $false
$smokePaths = @("/", "/teams/alabama.html")
for ($s = 1; $s -le 4; $s++) {
    $allPass = $true
    foreach ($p in $smokePaths) {
        try {
            $sr = Invoke-WebRequest -Uri ($url.TrimEnd('/') + $p) -Method Get -TimeoutSec 30 -UseBasicParsing
            $htmlOk = ($sr.StatusCode -eq 200) -and ($sr.Content -match '(?i)<html')
            if (-not $htmlOk) { $allPass = $false; Log "smoke attempt ${s}: $p -> HTTP $($sr.StatusCode) htmlOk=$htmlOk" }
        } catch { $allPass = $false; Log "smoke attempt ${s}: $p error: $($_.Exception.Message)" }
    }
    if ($allPass) { $smokeOk = $true; Log "smoke: new deploy healthy (homepage + team page, attempt $s)"; break }
    Start-Sleep -Seconds (5 * $s)
}
if (-not $smokeOk) {
    Log "ABORT: new deploy failed smoke check ($url) -- NOT flipping the alias. Live site stays on the previous good deploy."
    exit 5
}

# 4. Re-point the public alias to the new deployment (it does NOT auto-rotate).
Log "aliasing $ALIAS -> new deployment..."
(& vercel alias set $url $ALIAS --scope $SCOPE @TokenArg 2>&1 | ForEach-Object { Clean $_ }) | Tee-Object -FilePath $LogPath -Append | Out-Null

# 5. Health check.
Start-Sleep -Seconds 4
try { $r = Invoke-WebRequest -Uri "https://$ALIAS" -Method Head -TimeoutSec 30 -UseBasicParsing; Log "HEALTH https://$ALIAS -> HTTP $($r.StatusCode)" }
catch { Log "HEALTH check error: $($_.Exception.Message)" }
Log "==== publish_to_vercel DONE -- site is live ===="
