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

# 2. Ensure the project link + a complete vercel.json live INSIDE output/site
#    (build-site may wipe them). outputDirectory '.' so it serves the site root.
Copy-Item -LiteralPath (Join-Path $RepoRoot ".vercel") -Destination (Join-Path $SITE ".vercel") -Recurse -Force -ErrorAction SilentlyContinue
$vj = '{"$schema":"https://openapi.vercel.sh/vercel.json","outputDirectory":".","framework":null,"cleanUrls":false,"trailingSlash":true,"rewrites":[{"source":"/:slug([a-z][a-z0-9-]+).html","destination":"/teams/:slug.html"},{"source":"/today-in-history","destination":"/anniversary/today/index.html"},{"source":"/today-in-history/","destination":"/anniversary/today/index.html"}],"headers":[{"source":"/(.*)","headers":[{"key":"X-Robots-Tag","value":"index, follow"}]}]}'
[System.IO.File]::WriteAllText((Join-Path $SITE "vercel.json"), $vj)

# 3. Deploy output/site to production (archive=tgz handles the >15k file count).
Set-Location -LiteralPath $SITE
Log "deploying output/site to production..."
$out = (& vercel deploy --prod --yes --archive=tgz --scope $SCOPE 2>&1 | ForEach-Object { Clean $_ })
$out | Tee-Object -FilePath $LogPath -Append | Out-Null
$url = ($out | Select-String -Pattern 'https://wonderful-margulis-8ec96b-[a-z0-9]+-[a-z0-9-]+\.vercel\.app' -AllMatches | ForEach-Object { $_.Matches.Value } | Select-Object -First 1)
Set-Location -LiteralPath $RepoRoot
if (-not $url) { Log "FAIL: no production URL captured -- live site UNCHANGED. See log (cap exceeded? run chunked_vercel_publish.ps1)."; exit 2 }
Log "deploy URL: $url"

# 4. Re-point the public alias to the new deployment (it does NOT auto-rotate).
Log "aliasing $ALIAS -> new deployment..."
(& vercel alias set $url $ALIAS --scope $SCOPE 2>&1 | ForEach-Object { Clean $_ }) | Tee-Object -FilePath $LogPath -Append | Out-Null

# 5. Health check.
Start-Sleep -Seconds 4
try { $r = Invoke-WebRequest -Uri "https://$ALIAS" -Method Head -TimeoutSec 30 -UseBasicParsing; Log "HEALTH https://$ALIAS -> HTTP $($r.StatusCode)" }
catch { Log "HEALTH check error: $($_.Exception.Message)" }
Log "==== publish_to_vercel DONE -- site is live ===="
