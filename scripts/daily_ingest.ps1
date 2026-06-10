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

# Steps marked -Critical accumulate here; a non-empty list -> non-zero script exit
# + a Healthchecks /fail ping at the end, so a silently-broken data day is surfaced.
# Adapters stay NON-critical (one dead feed must not fail the whole run).
$script:FailedSteps = @()
function Run([string]$label, [scriptblock]$block, [switch]$Critical) {
    Log "== $label =="
    & $block *>&1 | Tee-Object -FilePath $LogPath -Append
    if ($LASTEXITCODE -ne 0) {
        Log "   $label exited with code $LASTEXITCODE (continuing)"
        if ($Critical) { $script:FailedSteps += $label }
    }
}

function Run-Adapter([string]$id) {
    Run "adapter: $id" { python tools/run_adapter.py $id }
}

# --- Canonical week: ONE source of truth -------------------------------------
# Every producer (reddit collector, taggers, feature builder) and consumer
# (cohort, mood, player-mood aggregators) MUST share the same week identity.
# Before this, three vocabularies were derived here independently -- season-week
# integer, ISO week "YYYY-WW", and the Monday date -- and silently disagreed:
# producers stamped (2025, 41) while cohort/player read ISO (2026, 24) -> 0 rows
# and mood mapped the Monday through a frozen calendar -> ValueError. resolve-week
# (src/cfb_rankings/common/week.py) emits all four keys from one computation so
# they can never drift again. Hard-abort if it doesn't return JSON -- proceeding
# with empty week vars would silently zero every aggregator.
$Now = Get-Date
$WkLines = (python manage.py resolve-week --json)
$WkLine  = ($WkLines -split "`n" | Where-Object { $_ -match '^\s*\{.*\}\s*$' } | Select-Object -Last 1)
try {
    $Wk = $WkLine | ConvertFrom-Json
    if (-not $Wk.iso_key) { throw "no iso_key" }
} catch {
    Log "FATAL: resolve-week did not return parseable JSON (got: '$WkLine'). Aborting before any data mutation."
    exit 1
}
$CurSeason  = [int]$Wk.season_year      # 2025 in offseason (CFB season just played)
$SeasonWeek = [int]$Wk.week             # season-week integer (producers + features + CFBD)
$PrevMonday = [string]$Wk.week_start    # Monday YYYY-MM-DD (mood / rivalry / lexicon)
$IsoWeekKey = [string]$Wk.iso_key       # "2025-41" (cohort + player-week-mood)
$IsInSeason = [bool]$Wk.in_season

Log "==== daily_ingest start ===="
Log "   today=$($Now.ToString('yyyy-MM-dd'))  iso_week=$IsoWeekKey  prev_monday=$PrevMonday"
Log "   in_season=$IsInSeason  cur_season=$CurSeason  season_week=$SeasonWeek"

# --- Pre-mutation DB snapshot (VACUUM INTO) + 7-day rotation -----------------
# Recoverability: a bad ingest day becomes "restore = copy a file". VACUUM INTO
# writes a consistent, defragmented copy without locking out the live DB. Uses the
# project interpreter (no sqlite3.exe dependency). Non-critical: a failed backup
# logs but never blocks the day's run.
$BackupDir = Join-Path $RepoRoot "backups"
if (-not (Test-Path $BackupDir)) { New-Item -ItemType Directory -Path $BackupDir | Out-Null }
$DbPath   = Join-Path $RepoRoot "cfb_rankings.db"
$SnapPath = Join-Path $BackupDir ("cfb_rankings_{0:yyyy-MM-dd}.db" -f $Now)
if (Test-Path $DbPath) {
    Run "backup: VACUUM INTO $($SnapPath | Split-Path -Leaf)" {
        if (Test-Path $SnapPath) { Remove-Item -LiteralPath $SnapPath -Force }
        python -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('VACUUM INTO ?',(sys.argv[2],)); c.close()" $DbPath $SnapPath
    }
    Get-ChildItem -LiteralPath $BackupDir -Filter "cfb_rankings_*.db" |
        Sort-Object LastWriteTime -Descending | Select-Object -Skip 7 |
        ForEach-Object { Log "   rotating out old snapshot $($_.Name)"; Remove-Item -LiteralPath $_.FullName -Force }
} else {
    Log "   (no cfb_rankings.db yet -- skipping snapshot)"
}

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
# B. Reddit
#    PRIMARY per-team source (Build #2): each team's FOOTBALL subreddit via the
#    .rss path (dedicated -> new.rss; school subs -> flair-filtered search.rss),
#    honest UA. Covers ~118 of 138 teams from the priority_teams seed. This
#    replaced the city/university-sub noise that dominated the old listing pull.
# =========================================================================
Run "reddit: collect-reddit-team-rss (per-team football subs)" {
    python manage.py collect-reddit-team-rss --season $CurSeason --week $SeasonWeek --limit 50
}
# Secondary: r/CFB national-layer text search. The free archive text-search is
# rate-limited/degraded (Arctic Shift 422 / PullPush 429 as of 2026-06), so this
# is best-effort national coverage on top of the per-team RSS above.
Run "reddit: collect-reddit-watchlist (r/CFB national, best-effort)" {
    python manage.py collect-reddit-watchlist `
        --season $CurSeason --week $SeasonWeek `
        --subreddit CFB `
        --audience-bucket national `
        --provider pullpush `
        --search-limit 15
}

# =========================================================================
# B.5 YouTube comments (Build #3) — the biggest unexploited fan-opinion pool.
#     National channels (seed) + per-team configured channels -> recent-upload
#     comments. uploads->videos.commentCount triage->commentThreads (1 unit each;
#     ~660/day offseason vs 10k free). Per-team channels tag directly; national
#     comments are alias-tagged afterward. Needs YOUTUBE_API_KEY (loaded from .env).
# =========================================================================
Run "youtube: collect-youtube-comments" {
    python manage.py collect-youtube-comments --season $CurSeason --week $SeasonWeek --max-units 6000
}
Run "youtube: tag national comments by alias" {
    python manage.py tag-team-mentions --season $CurSeason --week $SeasonWeek --sources youtube --commit
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
} -Critical
Run "aggregate: compute-divergence --week=$IsoWeekKey" {
    python manage.py compute-divergence --week $IsoWeekKey
}
Run "aggregate: compute-mood-week --week=$PrevMonday" {
    python manage.py compute-mood-week --week $PrevMonday --no-from-seed
} -Critical
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
# Season rollup (week=0): collapses ALL weeks of player chatter into one row per
# (player, bucket). This is what lights up Room cards in the offseason -- a player
# mentioned a few times across many weeks clears the floor on the season total
# even when no single week does. compute_player_mood_index falls back to this
# rollup (and cross-season to the prior year) when the weekly row is below gates.
Run "player: compute-player-season-mood --season=$CurSeason" {
    python manage.py compute-player-season-mood --season $CurSeason
}

# =========================================================================
# E.5 Encoder sentiment classify (the moat-quality consistency fix).
#     Runs the CardiffNLP stack on the 3090 over today's new (VADER-labeled)
#     docs and rewrites their target sentiment to the encoder labels BEFORE the
#     feature rebuild below aggregates them -- so the live mood numbers stay on
#     the same method as the one-time backfill instead of drifting back to VADER.
#     Cross-env: this needs torch/transformers, which live in .venv-ml, NOT the
#     production .venv. No-op + log if .venv-ml is absent (degrades to VADER for
#     the day; build still proceeds). Non-critical: an encoder hiccup must not
#     block the daily publish.
# =========================================================================
$MlPython = Join-Path $RepoRoot ".venv-ml\Scripts\python.exe"
if (Test-Path $MlPython) {
    Run "sentiment: encoder classify (.venv-ml, pinned heads)" {
        & $MlPython scripts/sentiment_classify_daily.py --commit
    }
} else {
    Log "   (.venv-ml absent -- skipping encoder classify; today's new docs keep VADER labels)"
}

# =========================================================================
# F. Team feature rebuild (recomputes team_week_conversation_features)
# =========================================================================
Run "features: build-conversation-features --season=$CurSeason --week=$SeasonWeek" {
    python manage.py build-conversation-features --season $CurSeason --week $SeasonWeek
} -Critical

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
Run "site: build-site" { python manage.py build-site } -Critical
Run "site: build-editions-archive" { python manage.py build-editions-archive }

# =========================================================================
# J. Status dump for the log trailer
# =========================================================================
Run "status: fanintel-status" { python manage.py fanintel-status }

# =========================================================================
# K. Publish the freshly-built site to Vercel (Option A: the box is the
#    source of truth; the cloud deploy crons are disabled). Deploys
#    output/site directly, atomic + alias-gated, with a >=3500-file sanity
#    gate so a broken/empty build can never reach the live URL. Logs to its
#    own publish_vercel_*.log.
# =========================================================================
if ($script:FailedSteps -contains "site: build-site") {
    Log "== publish: SKIPPED (build-site failed; refusing to deploy a broken build) =="
} else {
    Log "== publish: scripts\publish_to_vercel.ps1 =="
    & (Join-Path $RepoRoot "scripts\publish_to_vercel.ps1") *>&1 | Tee-Object -FilePath $LogPath -Append
    Log "   publish_to_vercel returned $LASTEXITCODE"
    if ($LASTEXITCODE -ne 0) { $script:FailedSteps += "publish_to_vercel" }
}

# --- Healthchecks.io dead-man's-switch + final exit status -------------------
# Set HEALTHCHECK_URL in .env. Success ping on a clean run; /fail ping otherwise
# so the monitor distinguishes "ran but failed" from "never ran". PS-safe.
$HcUrl = $env:HEALTHCHECK_URL
if ([string]::IsNullOrWhiteSpace($HcUrl)) {
    Log "   (HEALTHCHECK_URL not set -- skipping dead-man's-switch ping)"
} elseif ($script:FailedSteps.Count -eq 0) {
    try { Invoke-WebRequest -Uri $HcUrl -Method Get -TimeoutSec 15 -UseBasicParsing | Out-Null; Log "   healthcheck: success ping sent" }
    catch { Log "   healthcheck ping error: $($_.Exception.Message)" }
} else {
    try { Invoke-WebRequest -Uri ($HcUrl.TrimEnd('/') + '/fail') -Method Get -TimeoutSec 15 -UseBasicParsing | Out-Null; Log "   healthcheck: FAIL ping sent" }
    catch { Log "   healthcheck fail-ping error: $($_.Exception.Message)" }
}

if ($script:FailedSteps.Count -gt 0) {
    Log "==== daily_ingest end (FAILED: $($script:FailedSteps -join ', ')) ===="
    exit 1
}
Log "==== daily_ingest end (clean) ===="
exit 0
