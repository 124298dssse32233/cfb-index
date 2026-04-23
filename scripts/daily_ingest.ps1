# scripts/daily_ingest.ps1
#
# Daily Fan Intelligence ingestion runner — driven by Windows Task Scheduler.
# Runs all Tier A + Tier B adapters that don't need aggressive rate-limiting,
# then recomputes the prior ISO week's cohort aggregates and rebuilds the
# methodology page.
#
# Exits 0 if at least one adapter succeeded; exits 1 if every adapter failed
# (so Task Scheduler flags a failure state you'd actually care about).
#
# Logs per-run to logs/fanintel_ingest_YYYY-MM-DD.log.

$ErrorActionPreference = "Continue"  # keep going when one adapter fails
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

# Load .env into the current process (so adapters see API keys)
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$') {
            $name  = $matches[1]
            $value = $matches[2] -replace '^"(.*)"$', '$1' -replace "^'(.*)'$", '$1'
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

# Per-day log
$LogDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$LogPath = Join-Path $LogDir ("fanintel_ingest_{0:yyyy-MM-dd}.log" -f (Get-Date))

function Log([string]$msg) {
    $stamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"
    "$stamp  $msg" | Tee-Object -FilePath $LogPath -Append
}

function Run-Adapter([string]$id) {
    Log "== $id =="
    python tools/run_adapter.py $id *>&1 | Tee-Object -FilePath $LogPath -Append
    return $LASTEXITCODE
}

Log "==== daily_ingest start ===="

# Always-run free sources (no auth required)
$free = @(
    "wiki_pv", "wiki_edits", "gdelt_volume",
    "kalshi", "polymarket",
    "bluesky_curated", "bluesky_feeds"
)
foreach ($a in $free) { Run-Adapter $a | Out-Null }

# Auth-required (env var presence will let them run; otherwise they exit 0)
$auth = @("youtube_meta", "seatgeek", "spotify_charts")
foreach ($a in $auth) { Run-Adapter $a | Out-Null }

# Per-team bulk families (RSS)
$bulk = @("google_news_all", "campus_news_all", "athletics_all", "locked_on_all")
foreach ($a in $bulk) { Run-Adapter $a | Out-Null }

# Aggregation + methodology refresh for the ISO week that just ended
$week = (Get-Date).AddDays(-7).ToString("yyyy")
$wkNum = [int]((Get-Culture).Calendar.GetWeekOfYear((Get-Date).AddDays(-7), [System.Globalization.CalendarWeekRule]::FirstFourDayWeek, [System.DayOfWeek]::Monday))
$WeekKey = "{0}-{1}" -f $week, $wkNum

Log "== compute-cohort-week --week=$WeekKey =="
python manage.py compute-cohort-week --week=$WeekKey *>&1 | Tee-Object -FilePath $LogPath -Append

Log "== compute-divergence --week=$WeekKey =="
python manage.py compute-divergence --week=$WeekKey *>&1 | Tee-Object -FilePath $LogPath -Append

Log "== build-methodology =="
python manage.py build-methodology *>&1 | Tee-Object -FilePath $LogPath -Append

Log "== fanintel-status =="
python manage.py fanintel-status *>&1 | Tee-Object -FilePath $LogPath -Append

Log "==== daily_ingest end ===="
