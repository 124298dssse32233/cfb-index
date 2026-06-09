# scripts/daily_ingest.ps1
#
# Full daily Fan Intelligence + CFBD + site pipeline. Driven by Windows Task
# Scheduler; runs under the logged-in user at 09:00. Expected wall-clock: ~15 min.
#
# In-season (Aug 15 - Jan 20), this also runs CFBD week ingest + model runs.
# Offseason, those are skipped cleanly.
#
# Exits 0 even if individual adapters fail; scrape_health captures the detail.
# Logs per-run to logs/fanintel_ingest_YYYY-MM-DD.log.

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

# --- Self-contained scheduled-task runtime: project venv + UTF-8 --------------
# Task Scheduler launches a bare shell with no venv active, so bare `python`
# would resolve to the system interpreter, which lacks this project's deps (they
# live in .venv from `pip install -e .`). Prepend the venv so every `python`
# below is the project interpreter. Also force UTF-8 so non-ASCII log output
# can't crash Python on a fresh Windows box (cp1252 default). No-op if .venv is
# absent, so this stays portable to a system-Python setup.
$env:PYTHONUTF8 = "1"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $env:Path = (Split-Path -Parent $VenvPython) + ";" + $env:Path
}

# --- Load .env into process so API keys are visible to python -----------------
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$') {
            $name  = $matches[1]
            $value = $matches[2] -replace '^"(.*)"$', '$1' -replace "^'(.*)'$", '$1'
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

$LogDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$LogPath = Join-Path $LogDir ("fanintel_ingest_{0:yyyy-MM-dd}.log" -f (Get-Date))

function Log([string]$msg) {
    $stamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"
    "$stamp  $msg" | Tee-Object -FilePath $LogPath -Append
}

function Run([string]$label, [scriptblock]$block) {
    Log "== $label =="
    & $block *>&1 | Tee-Object -FilePath $LogPath -Append
    if ($LASTEXITCODE -ne 0) { Log "   $label exited with code $LASTEXITCODE (continuing)" }
}

function Run-Adapter([string]$id) {
    Run "adapter: $id" { python tools/run_adapter.py $id }
}

# --- Derived dates -----------------------------------------------------------
$Now        = Get-Date
$IsInSeason = ($Now.Month -ge 8) -or ($Now.Month -eq 1 -and $Now.Day -le 20)
$CurSeason  = if ($Now.Month -ge 7) { $Now.Year } else { $Now.Year - 1 }

# Previous Monday date (YYYY-MM-DD) — what compute-mood-week expects
$PrevMonday = $Now.AddDays(-(([int]$Now.DayOfWeek + 6) % 7)).ToString("yyyy-MM-dd")

# Current ISO week key (YYYY-WW) — what cohort aggregator expects
$WeekNum  = [int]((Get-Culture).Calendar.GetWeekOfYear(
    $Now, [System.Globalization.CalendarWeekRule]::FirstFourDayWeek,
    [System.DayOfWeek]::Monday))
$IsoWeekKey = "{0}-{1:D2}" -f $Now.Year, $WeekNum

# Current season week (integer) — for CFBD. Rough: weeks since Aug 26.
$SeasonStart = Get-Date -Year $CurSeason -Month 8 -Day 26
$SeasonWeek  = [math]::Max(1, [math]::Floor(($Now - $SeasonStart).TotalDays / 7) + 1)

Log "==== daily_ingest start ===="
Log "   today=$($Now.ToString('yyyy-MM-dd'))  iso_week=$IsoWeekKey  prev_monday=$PrevMonday"
Log "   in_season=$IsInSeason  cur_season=$CurSeason  season_week=$SeasonWeek"

# =========================================================================
# A. Fan-intelligence ingestion (year-round, free / auth-gated)
# =========================================================================
$freeSources = @(
    "wiki_pv", "wiki_edits", "gdelt_volume",
    "kalshi", "polymarket",
    "bluesky_curated", "bluesky_feeds"
)
foreach ($s in $freeSources) { Run-Adapter $s }

$authSources = @("youtube_meta", "seatgeek", "spotify_charts")
foreach ($s in $authSources) { Run-Adapter $s }

$bulkFamilies = @("google_news_all", "campus_news_all", "athletics_all", "locked_on_all")
foreach ($s in $bulkFamilies) { Run-Adapter $s }

# Coaching carousel (FootballScoop RSS — feed moved /feed/ -> /rss/, fixed 2026-06).
# Captures hires/fires going forward; the offseason carousel itself can't be
# backfilled (247Sports tracker is bot-blocked, RSS is recent-only).
Run "coaching: coaching-fetch-news" { python manage.py coaching-fetch-news --days 7 }

# =========================================================================
# B. Reddit (PullPush provider = free; Arctic Shift text-search returns HTTP 422 as of 2026-06)
# =========================================================================
Run "reddit: collect-reddit-watchlist" {
    python manage.py collect-reddit-watchlist `
        --season $CurSeason --week $SeasonWeek `
        --subreddit CFB `
        --audience-bucket national `
        --provider pullpush `
        --search-limit 15
}

# =========================================================================
# C. CFBD weekly refresh - in-season only
# =========================================================================
if ($IsInSeason) {
    Run "cfbd: ingest-cfbd-week --season=$CurSeason --week=$SeasonWeek" {
        python manage.py ingest-cfbd-week --season $CurSeason --week $SeasonWeek
    }
    # NOTE: import-player-honors is CSV-driven, not daily cadence. The wiki-awards
    # scraper auto-imports each CSV it produces. Honors mostly land in December —
    # use weekly_deep.ps1 / load_history scripts to refresh, not the daily loop.
} else {
    Log "   (offseason: skipping ingest-cfbd-week)"
}

# =========================================================================
# D. Aggregators - current week
# =========================================================================
Run "aggregate: compute-cohort-week --week=$IsoWeekKey" {
    python manage.py compute-cohort-week --week $IsoWeekKey
}
Run "aggregate: compute-divergence --week=$IsoWeekKey" {
    python manage.py compute-divergence --week $IsoWeekKey
}
Run "aggregate: compute-mood-week --week=$PrevMonday" {
    python manage.py compute-mood-week --week $PrevMonday --no-from-seed
}
Run "aggregate: compute-rivalry-ratios --week=$PrevMonday" {
    python manage.py compute-rivalry-ratios --week $PrevMonday --no-from-seed
}
Run "aggregate: mine-lexicon --week=$PrevMonday" {
    python manage.py mine-lexicon --week $PrevMonday --no-from-seed
}

# =========================================================================
# E. Player pipeline
# =========================================================================
Run "player: tag-player-mentions --season=$CurSeason --commit" {
    python manage.py tag-player-mentions --season $CurSeason --commit
}
Run "player: compute-player-week-mood --week=$IsoWeekKey" {
    python manage.py compute-player-week-mood --week $IsoWeekKey
}

# =========================================================================
# F. Team feature rebuild (recomputes team_week_conversation_features)
# =========================================================================
Run "features: build-conversation-features --season=$CurSeason --week=$SeasonWeek" {
    python manage.py build-conversation-features --season $CurSeason --week $SeasonWeek
}

# =========================================================================
# G. Models (in-season only - require fresh game data)
# =========================================================================
if ($IsInSeason) {
    Run "models: run-models --season=$CurSeason --through-week=$SeasonWeek" {
        python manage.py run-models --season $CurSeason --through-week $SeasonWeek
    }
    Run "models: run-heisman-model --season=$CurSeason --through-week=$SeasonWeek" {
        python manage.py run-heisman-model --season $CurSeason --through-week $SeasonWeek
    }
} else {
    Log "   (offseason: skipping run-models + run-heisman-model)"
}

# =========================================================================
# H. Board builders (fast, stateless reads)
# =========================================================================
Run "board: build-the-room-board --season=$CurSeason" {
    python manage.py build-the-room-board --season $CurSeason --week $SeasonWeek
}
Run "board: build-players-landing --season=$CurSeason" {
    python manage.py build-players-landing --season $CurSeason --week $SeasonWeek
}
Run "board: build-signature-story-board --season=$CurSeason" {
    python manage.py build-signature-story-board --season $CurSeason
}
Run "board: build-methodology" { python manage.py build-methodology }

# =========================================================================
# I. Full static site rebuild - the main product output
# =========================================================================
Run "team-preview: build-team-preview-layer" { python manage.py build-team-preview-layer }
Run "team-preview: generate-team-preview-claims" {
    python manage.py generate-team-preview-claims --season (Get-Date -Format yyyy) --as-of (Get-Date -Format yyyy-MM-dd)
}
Run "site: build-site" { python manage.py build-site }
Run "site: build-editions-archive" { python manage.py build-editions-archive }

# =========================================================================
# J. Status dump for the log trailer
# =========================================================================
Run "status: fanintel-status" { python manage.py fanintel-status }

Log "==== daily_ingest end ===="
