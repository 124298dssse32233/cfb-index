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
#    GDELT is now ledger-rotated + 8-min wall-clock budgeted (un-capped over a
#    rolling window), so it can't grind even though it's a slow rate-limited API.
# =========================================================================
$freeSources = @("wiki_pv", "wiki_edits", "gdelt_volume", "kalshi", "polymarket",
                 "bluesky_curated", "bluesky_feeds")
foreach ($s in $freeSources) { Run-Adapter $s }

$authSources = @("youtube_meta", "seatgeek", "spotify_charts")
foreach ($s in $authSources) { Run-Adapter $s }

$bulkFamilies = @("google_news_all", "campus_news_all", "athletics_all", "locked_on_all")
foreach ($s in $bulkFamilies) { Run-Adapter $s }

Run "coaching: coaching-fetch-news" { python manage.py coaching-fetch-news --days 7 }

# =========================================================================
# B. Reddit — per-team football subs via .rss (primary) + r/CFB national (best-effort)
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
# B.5 YouTube comments (national + per-team) + tag national/media docs by alias
# =========================================================================
Run "youtube: collect-youtube-comments" {
    python manage.py collect-youtube-comments --season $global:CurSeason --week $global:SeasonWeek --max-units 6000
}
Run "tag: national/media docs by team alias (youtube + bluesky)" {
    python manage.py tag-team-mentions --season $global:CurSeason --week $global:SeasonWeek `
        --sources youtube,bluesky_curated,bluesky_feeds --commit
}

# =========================================================================
# B.6 Independent message boards (12 validated team boards via public RSS)
# =========================================================================
Run "boards: collect-team-boards" {
    python manage.py collect-team-boards --season $global:CurSeason --week $global:SeasonWeek
}

Complete-Pipeline "HEALTHCHECK_URL_COLLECT"
