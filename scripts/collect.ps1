# scripts/collect.ps1
#
# COLLECTION half of the decoupled pipeline (cadence architecture, 2026-06).
# Pulls every source into SQLite, then exits. Does NOT build or publish — the
# build_publish.ps1 job reads SQLite as-of-now, so a slow/failed collector here
# can never block the site from shipping. Schedule on its own cadence (e.g. 05:00,
# or more frequently in-season). See docs/pipeline_cadence_architecture_2026-06.md.
#
# Activate the decoupled cadence via register_split_tasks.ps1. Until then the
# monolith daily_ingest.ps1 stays the active path.

$PipelineName = "collect"
. "$PSScriptRoot\_pipeline_common.ps1"

# --- Pre-mutation DB snapshot (VACUUM INTO) + 7-day rotation -----------------
$BackupDir = Join-Path $global:RepoRoot "backups"
if (-not (Test-Path $BackupDir)) { New-Item -ItemType Directory -Path $BackupDir | Out-Null }
$DbPath   = Join-Path $global:RepoRoot "cfb_rankings.db"
$SnapPath = Join-Path $BackupDir ("cfb_rankings_{0:yyyy-MM-dd}.db" -f $global:Now)
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
#    gdelt_volume auto-routes: BQ (if GOOGLE_APPLICATION_CREDENTIALS set) →
#    HTTP GKG bulk (credential-free, ~3-4 min) → DOC 2.0 rotation (legacy,
#    explicit adapter_id 'gdelt_volume_doc'). The gdelt-news-volume CLI step
#    below runs alongside to also materialise counts into team_news_volume.
# =========================================================================
$freeSources = @("wiki_pv", "wiki_edits", "gdelt_volume", "kalshi", "polymarket",
                 "bluesky_curated", "bluesky_feeds")
foreach ($s in $freeSources) { Run-Adapter $s }

# GDELT GKG bulk -> team_news_volume: DISABLED 2026-06-11.
# This crashed every run (gdelt_gkg.py queried a column that no longer exists) and
# is redundant: the live GDELT signal comes from the `gdelt_volume` adapter above
# (BigQuery -> source_observations), which IS consumed by features. team_news_volume
# is read by NOTHING in the codebase, and the GKG path's 11k-alias substring matcher
# is slow and lower-quality. If per-team news volume is ever wanted, read it from
# source_observations rather than re-materialising via the bulk GKG path.
Log "   (gdelt: ingest-gdelt-news-volume intentionally disabled -- redundant with the gdelt_volume BQ adapter; team_news_volume is unread)"

$authSources = @("youtube_meta", "seatgeek", "spotify_charts")
foreach ($s in $authSources) { Run-Adapter $s }

$bulkFamilies = @("google_news_all", "campus_news_all", "athletics_all", "locked_on_all")
foreach ($s in $bulkFamilies) { Run-Adapter $s }

Run "coaching: coaching-fetch-news" { python manage.py coaching-fetch-news --days 7 }

# =========================================================================
# B. Reddit — per-team football subs via .rss (primary) + r/CFB national (best-effort)
#
# 429 NOTE (freshness triage 2026-06-12): the live .rss path below is the single
# biggest source of HTTP 429 in scrape_health (Reddit throttles unauth .rss). The
# RESOLUTION is the archive path, NOT live-RSS backoff: Arctic Shift by-subreddit
# listing endpoints (alive, unauth, fresh, and carry score + num_comments that RSS
# lacks) via src/cfb_rankings/clients/reddit_arctic_shift.py + `--provider
# arctic-shift` (already the default for collect-reddit-comments below) and pullpush
# (collect-reddit-watchlist below). Architecture + rebuild plan: Build #2 in
# docs/source_expansion_MASTER_PLAN_2026-06.md. The .rss 429s are therefore
# largely EXPECTED degradation of a superseded path — route per-team pulls through
# the Arctic Shift listing adapter rather than fighting the rate limit.
# =========================================================================
Run "reddit: collect-reddit-team-rss (per-team football subs)" {
    python manage.py collect-reddit-team-rss --season $global:CurSeason --week $global:SeasonWeek --limit 50
}
Run "reddit: collect-reddit-watchlist (r/CFB national, best-effort)" {
    python manage.py collect-reddit-watchlist `
        --season $global:CurSeason --week $global:SeasonWeek `
        --subreddit CFB --audience-bucket national --provider pullpush --search-limit 15
}

# =========================================================================
# B.5 YouTube comments + Podcast transcripts (GPU), THEN tag national/media
#     docs by team alias. The tag step must run AFTER both collectors and must
#     include their source_names, because build_publish does NOT run
#     tag-team-mentions (only tag-player-mentions) — team attribution happens
#     here or not at all.
# =========================================================================
Run "youtube: collect-youtube-comments" {
    python manage.py collect-youtube-comments --season $global:CurSeason --week $global:SeasonWeek --max-units 6000
}
# Podcast transcription needs CUDA -> use .venv-ml python (like the encoder step).
# Self-skips cleanly (exit 0) if .venv-ml or faster-whisper is absent.
$MlPython = Join-Path $global:RepoRoot ".venv-ml\Scripts\python.exe"
if (Test-Path $MlPython) {
    Run "podcast: collect-podcast-transcripts (.venv-ml, GPU, time-boxed)" {
        & $MlPython manage.py collect-podcast-transcripts `
            --season $global:CurSeason --week $global:SeasonWeek `
            --max-episodes 6 --budget-seconds 900 --model-size small.en
    }
} else {
    Log "   (.venv-ml absent -- skipping podcast transcription)"
}
Run "tag: national/media docs by team alias (youtube + bluesky + podcasts)" {
    python manage.py tag-team-mentions --season $global:CurSeason --week $global:SeasonWeek `
        --sources youtube,bluesky_curated,bluesky_feeds,podcast_transcript --commit
}

# =========================================================================
# B.6 Independent message boards (12 validated team boards via public RSS)
# =========================================================================
Run "boards: collect-team-boards" {
    python manage.py collect-team-boards --season $global:CurSeason --week $global:SeasonWeek
}

# =========================================================================
# B.7 Reddit COMMENT trees under already-targeted posts (Arctic Shift).
#     --min-post-comments 0 so the .rss-sourced team-sub posts (which carry
#     reply_count=0 because RSS omits comment counts) are eligible parents;
#     the candidate selector now also accepts mention_role='team-sub'. Bounded
#     (limit-posts) + best-effort: this lives in COLLECT, so a slow/flaky Arctic
#     Shift run can never block the build. --skip-build-features because
#     build_publish.ps1 owns the feature rebuild (comments fold into it there).
# =========================================================================
Run "reddit: collect-reddit-comments (comment trees, best-effort)" {
    python manage.py collect-reddit-comments `
        --season $global:CurSeason --week $global:SeasonWeek `
        --provider arctic-shift --limit-posts 150 --comments-per-post 60 `
        --min-post-comments 0 --skip-build-features
}

# =========================================================================
# B.8 Curated fan-slang lexicon counts (lexicon_term_daily). Runs in COLLECT
#     because it needs raw body_text: the aggregates are the only thing that
#     survives if purge-reddit-raw-content is ever scheduled — this step must
#     always run before any purge step is added. 3-day rolling window is
#     idempotent (delete+reinsert per day) and covers late-arriving comments.
# =========================================================================
Run "lexicon: track-lexicon (curated watchlist, 3-day window)" {
    python manage.py track-lexicon --days 3
}

# =========================================================================
# C. Silent-degradation gate. Baseline-aware: alerts (gh issue) only when an
#    ESTABLISHED source goes dark — the failure mode that hid the May .json
#    shutoff for ~10 days. NOT -Critical: a quiet source must not fail the whole
#    collect (the gh issue is the alert); only a clean collect pings success.
# =========================================================================
Run "verify: per-source health floors" {
    python scripts/verify_source_health_floors.py --open-issue
}

# =========================================================================
# D. CRITICAL volume floor. The per-source health check above judges on a 21-day
#    window, so it CANNOT see a single-day wholesale collapse (e.g. a cli.py bug
#    that kills every Reddit/board subcommand at once -- as happened 2026-06-11,
#    where the day fell from ~31.9k docs to ~2.8k yet everything reported "clean").
#    This is the one -Critical step in collect: a >75% drop vs the 7d median
#    flips FailedSteps -> fail-ping + non-zero exit so the nightly actually alerts.
#    Standalone raw-sqlite3 (NOT manage.py) so it survives a broken main().
# =========================================================================
Run "verify: collect volume floor (today vs 7d median)" -Critical {
    python scripts/verify_collect_volume.py
}

Complete-Pipeline "HEALTHCHECK_URL_COLLECT"
