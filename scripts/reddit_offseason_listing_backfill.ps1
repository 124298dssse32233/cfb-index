# scripts/reddit_offseason_listing_backfill.ps1
#
# Autonomous, NO-CREDENTIALS Reddit collection via the WORKING Arctic Shift
# subreddit_listing endpoint (the query= text-search is 422-broken; listing works).
# Collects r/CFB + 43 team/city subs across the plan's date range, then runs the
# full downstream pipeline so the fan-intel surfaces reflect it.
#
# Restart-safe: backfill_reddit_history.py checkpoints every 20 windows in
# data/reddit_backfill_state.json, so re-running resumes. Continue-on-error.
# Heavy: the full plan is thousands of windows (arctic-shift soft-limits ~1 req/3s),
# so expect several hours. Logs to logs/.

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$env:PYTHONUTF8 = "1"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) { $env:Path = (Split-Path -Parent $VenvPython) + ";" + $env:Path }

if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$') {
            $n = $matches[1]; $v = $matches[2] -replace '^"(.*)"$', '$1' -replace "^'(.*)'$", '$1'
            [Environment]::SetEnvironmentVariable($n, $v, "Process")
        }
    }
}

$LogDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory $LogDir | Out-Null }
$LogPath = Join-Path $LogDir ("reddit_listing_backfill_{0:yyyy-MM-dd_HHmmss}.log" -f (Get-Date))

function Log([string]$m) { $s = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"; "$s  $m" | Tee-Object -FilePath $LogPath -Append }
function Run([string]$label, [string[]]$a) {
    Log "== $label =="
    & python -u manage.py @a *>&1 | Tee-Object -FilePath $LogPath -Append
    if ($LASTEXITCODE -ne 0) { Log "   $label exited $LASTEXITCODE (continuing)" } else { Log "   $label OK" }
}

$sw = [System.Diagnostics.Stopwatch]::StartNew()
Log "==== reddit_listing_backfill START ===="

# STEP 1 - the content: full Reddit backfill via the WORKING subreddit_listing endpoint
Log "== STEP 1: backfill_reddit_history.py --commit (subreddit_listing; arctic-shift -> pullpush) =="
& python scripts\backfill_reddit_history.py --commit *>&1 | Tee-Object -FilePath $LogPath -Append
Log "   STEP 1 backfill returned $LASTEXITCODE"

# STEP 2 - downstream pipeline on the new docs (tag + aggregate + features + boards + build)
Log "== STEP 2: daily_ingest.ps1 (tag-player-mentions + aggregation + features + boards + build) =="
& (Join-Path $RepoRoot "scripts\daily_ingest.ps1")
Log "   STEP 2 daily_ingest returned $LASTEXITCODE"

# STEP 3 - player sentiment on the newly-tagged targets, via LOCAL Ollama (cost-meter now $0)
Run "classify-player-sentiment (local Ollama)" @("classify-player-sentiment")

# STEP 4 - final rebuild so sentiment/mood show up
Run "build-site (final)" @("build-site")

$sw.Stop()
Log ("==== reddit_listing_backfill END (elapsed {0:N1} min) ====" -f $sw.Elapsed.TotalMinutes)
