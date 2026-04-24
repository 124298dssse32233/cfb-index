from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
import webbrowser

from cfb_rankings.config import AppConfig
from cfb_rankings.migrations import apply_runtime_migrations

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cfb-rankings")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db")
    subparsers.add_parser(
        "apply-migrations",
        help="Apply all SQL files in migrations/ plus runtime column migrations. Idempotent.",
    )
    subparsers.add_parser(
        "seed-source-registry",
        help="Load seeds/source_registry.yaml into source_registry (upsert on source_id).",
    )
    subparsers.add_parser(
        "seed-priority-teams",
        help="Load seeds/priority_teams.yaml into priority_teams (upsert on team_id).",
    )
    subparsers.add_parser(
        "seed-source-instances",
        help="Expand *_template source_registry rows into per-team concrete rows "
             "(one per priority_teams row × family with a populated handle).",
    )
    subparsers.add_parser(
        "seed-feed-instances",
        help="Expand per-feed YAML seeds (beat_writer, substack, podcast, radio) "
             "into concrete source_registry rows.",
    )
    subparsers.add_parser(
        "fanintel-status",
        help="One-shot operational summary: source_registry counts, scrape_health, "
             "priority_teams coverage, team_cohort_week coverage.",
    )
    validate_parser = subparsers.add_parser(
        "validate-feed-urls",
        help="HEAD-check every source_registry.terms_url (+ priority_teams wiki pages). "
             "Writes scrape_health rows and prints a summary of broken URLs.",
    )
    validate_parser.add_argument(
        "--include-templates", action="store_true",
        help="Also validate *_template ToS URLs (usually skipped).",
    )
    validate_parser.add_argument(
        "--include-wiki-pages", action="store_true",
        help="Also HEAD-check priority_teams.wiki_{team,coach,qb}_page articles.",
    )
    scrape_health_parser = subparsers.add_parser(
        "scrape-health",
        help="Print per-source run status from scrape_health (sorted error > empty > ok).",
    )
    scrape_health_parser.add_argument(
        "--since-days", type=int, default=7,
        help="Limit to runs within the last N days (default: 7).",
    )
    compute_cohort_parser = subparsers.add_parser(
        "compute-cohort-week",
        help="Aggregate conversation_documents into team_cohort_week for a YYYY-WW.",
    )
    compute_cohort_parser.add_argument("--week", required=True, help="Week key in YYYY-WW format.")
    compute_cohort_parser.add_argument(
        "--teams", nargs="*", type=int, default=None,
        help="Optional team_id list to filter; default = all teams present in docs.",
    )
    compute_divergence_parser = subparsers.add_parser(
        "compute-divergence",
        help="Compute cohort divergence per team for one week (reads team_cohort_week).",
    )
    compute_divergence_parser.add_argument("--week", required=True, help="Week key in YYYY-WW format.")

    tag_players_parser = subparsers.add_parser(
        "tag-player-mentions",
        help=("Scan conversation_documents for player-name mentions and emit "
              "conversation_document_targets rows with target_type='player'. "
              "Dry-run by default; pass --commit to actually insert rows."),
    )
    tag_players_parser.add_argument("--season", type=int, required=True,
                                    help="Season year — restricts both doc scope and candidate players.")
    tag_players_parser.add_argument("--week", type=int, default=None,
                                    help="Optional week filter.")
    tag_players_parser.add_argument("--limit", type=int, default=None,
                                    help="Optional cap on docs scanned (debug/preview).")
    tag_players_parser.add_argument("--commit", action="store_true",
                                    help="Actually insert rows. Default is dry-run.")
    tag_players_parser.add_argument("--preview", action="store_true",
                                    help="Print each match with a context snippet for eyeball review.")

    compute_player_mood_parser = subparsers.add_parser(
        "compute-player-week-mood",
        help=("Aggregate conversation_document_targets (target_type='player') into "
              "player_week_conversation_features for a YYYY-WW."),
    )
    compute_player_mood_parser.add_argument("--week", required=True, help="Week key in YYYY-WW.")
    compute_player_mood_parser.add_argument(
        "--players", nargs="*", type=int, default=None,
        help="Optional player_id list to filter; default = all players with mentions.",
    )

    the_room_board_parser = subparsers.add_parser(
        "build-the-room-board",
        help=("Build the /players/the-room.html discovery page that lists "
              "every player whose mood card renders ready-state today."),
    )
    the_room_board_parser.add_argument("--season", type=int, required=True)
    the_room_board_parser.add_argument("--week", type=int, default=1)

    players_landing_parser = subparsers.add_parser(
        "build-players-landing",
        help=("Build /players/spotlight.html — curated landing that previews "
              "The Room + Signature Stories boards in one page."),
    )
    players_landing_parser.add_argument("--season", type=int, required=True)
    players_landing_parser.add_argument("--week", type=int, default=1)

    signature_board_parser = subparsers.add_parser(
        "build-signature-story-board",
        help=("Build /players/signature-stories.html — Top 25 per position "
              "by engine percentile, each clickable to the player page."),
    )
    signature_board_parser.add_argument("--season", type=int, required=True)

    compute_player_season_mood_parser = subparsers.add_parser(
        "compute-player-season-mood",
        help=("Season rollup: aggregate ALL player-scope target rows for one "
              "season into week=0 rows. Lets offseason player pages surface "
              "a non-empty Room when no single week clears the floor."),
    )
    compute_player_season_mood_parser.add_argument("--season", type=int, required=True)
    compute_player_season_mood_parser.add_argument(
        "--players", nargs="*", type=int, default=None,
        help="Optional player_id filter.",
    )
    subparsers.add_parser(
        "build-methodology",
        help="Render /methodology/fan-intelligence.html from source_registry + weights.",
    )

    # Signature Bets S1.6 — Live Signal Flow event lifecycle.
    signal_emit_parser = subparsers.add_parser(
        "signal-emit",
        help="Emit one Live Signal Flow event (Signature Bets S1.6).",
    )
    signal_emit_parser.add_argument("--player-id", type=int, required=True)
    signal_emit_parser.add_argument(
        "--event-type", required=True,
        choices=[
            "portal_entry", "commit", "injury", "draft_declare", "draft_pick",
            "watch_list", "all_american", "program_record",
            "heisman_odds_swing", "major_news",
        ],
    )
    signal_emit_parser.add_argument("--headline", required=True)
    signal_emit_parser.add_argument("--sub-line", default=None)
    signal_emit_parser.add_argument("--source-url", default=None)
    signal_emit_parser.add_argument("--source-name", default=None)
    signal_emit_parser.add_argument("--decay-hours", type=float, default=72.0)
    signal_emit_parser.add_argument("--dedup-key", default=None)

    signal_list_parser = subparsers.add_parser(
        "signal-list",
        help="List active (non-decayed) signals for a player.",
    )
    signal_list_parser.add_argument("--player-id", type=int, required=True)

    signal_prune_parser = subparsers.add_parser(
        "signal-prune",
        help="Delete signals that decayed more than --older-than-hours ago.",
    )
    signal_prune_parser.add_argument(
        "--older-than-hours", type=float, default=24.0,
    )

    player_mood_parser = subparsers.add_parser(
        "player-mood",
        help=("Print The Room on [Player] — the player-scope mood profile. "
              "Takes a slug ('cj-carr-4788') or numeric player_id."),
    )
    player_mood_parser.add_argument(
        "player", help="Player slug (any-prefix-<id>) or numeric player_id.",
    )
    player_mood_parser.add_argument("--season", type=int, default=None)
    player_mood_parser.add_argument("--week", type=int, default=1,
                                    help="Week number (default 1; aggregate is weekly).")
    player_mood_parser.add_argument("--json", action="store_true",
                                    help="Emit the profile as JSON.")

    player_signature_parser = subparsers.add_parser(
        "player-signature",
        help=("Print the Signature Story for a single player. "
              "Takes a player slug (e.g. 'cj-carr-4788') or a raw player_id."),
    )
    player_signature_parser.add_argument(
        "player",
        help="Player slug (any-prefix-<id>) or numeric player_id.",
    )
    player_signature_parser.add_argument(
        "--season", type=int, default=None,
        help="Season year (default: latest season with player data).",
    )
    player_signature_parser.add_argument(
        "--week", type=int, default=None,
        help="Optional through-week cutoff. If omitted, full-season snapshot.",
    )
    player_signature_parser.add_argument(
        "--json", action="store_true",
        help="Emit the story payload as JSON instead of the pretty scoreboard.",
    )

    list_sportsdb_parser = subparsers.add_parser("list-sportsdb-leagues")
    list_sportsdb_parser.add_argument("--country", default="United States")
    list_sportsdb_parser.add_argument("--sport", default="American Football")

    ingest_sportsdb_parser = subparsers.add_parser("ingest-sportsdb")
    ingest_sportsdb_parser.add_argument("--league-id", type=int, required=True)
    ingest_sportsdb_parser.add_argument("--season", type=int, required=True)
    ingest_sportsdb_parser.add_argument("--level-code", required=True, choices=["FBS", "FCS", "DII", "DIII"])
    ingest_sportsdb_parser.add_argument("--conference", required=True)

    ingest_cfbd_week_parser = subparsers.add_parser("ingest-cfbd-week")
    ingest_cfbd_week_parser.add_argument("--season", type=int, required=True)
    ingest_cfbd_week_parser.add_argument("--week", type=int, required=True)
    ingest_cfbd_week_parser.add_argument("--season-type", default="regular")
    ingest_cfbd_week_parser.add_argument("--skip-play-level", action="store_true", help="Skip both drives and plays for a lighter refresh.")
    ingest_cfbd_week_parser.add_argument("--skip-lines", action="store_true")
    ingest_cfbd_week_parser.add_argument("--skip-weather", action="store_true")
    ingest_cfbd_week_parser.add_argument("--skip-advanced-stats", action="store_true")
    ingest_cfbd_week_parser.add_argument("--skip-drives", action="store_true")
    ingest_cfbd_week_parser.add_argument("--skip-plays", action="store_true")
    ingest_cfbd_week_parser.add_argument("--include-game-player-stats", action="store_true")

    ingest_cfbd_preseason_parser = subparsers.add_parser("ingest-cfbd-preseason")
    ingest_cfbd_preseason_parser.add_argument("--season", type=int, required=True)
    ingest_cfbd_preseason_parser.add_argument("--team", action="append", default=[], help="Repeat for each team to load a roster.")
    ingest_cfbd_preseason_parser.add_argument("--all-season-teams", action="store_true", help="Load rosters for every team already present in the selected season.")
    ingest_cfbd_preseason_parser.add_argument(
        "--classification",
        choices=["fbs", "fcs"],
        help="Load a full classification-wide roster snapshot in one CFBD call when no explicit teams are provided.",
    )

    import_honors_parser = subparsers.add_parser("import-player-honors")
    import_honors_parser.add_argument("--csv", required=True)
    import_honors_parser.add_argument("--source-name", default="manual")

    seed_team_aliases_parser = subparsers.add_parser("seed-team-aliases")
    seed_team_aliases_parser.add_argument("--season", type=int, required=True)

    collect_reddit_parser = subparsers.add_parser("collect-reddit-watchlist")
    collect_reddit_parser.add_argument("--season", type=int, required=True)
    collect_reddit_parser.add_argument("--week", type=int, required=True)
    collect_reddit_parser.add_argument("--team", action="append", default=[], help="Optional explicit watchlist team names.")
    collect_reddit_parser.add_argument("--limit-teams", type=int, default=25)
    collect_reddit_parser.add_argument("--subreddit", default="CFB", help="Target subreddit for search. Use an empty string for sitewide search.")
    collect_reddit_parser.add_argument("--audience-bucket", default="national", choices=["fan", "rival", "national", "media", "unknown"])
    collect_reddit_parser.add_argument("--search-limit", type=int, default=15)
    collect_reddit_parser.add_argument("--provider", default="reddit", choices=["reddit", "arctic-shift", "pullpush"])
    collect_reddit_parser.add_argument("--after", help="Optional lower bound as Unix seconds or YYYY-MM-DD ET.")
    collect_reddit_parser.add_argument("--before", help="Optional upper bound as Unix seconds or YYYY-MM-DD ET.")
    collect_reddit_parser.add_argument("--no-replace-existing", action="store_true")

    collect_reddit_plan_parser = subparsers.add_parser("collect-reddit-plan")
    collect_reddit_plan_parser.add_argument("--season", type=int, required=True)
    collect_reddit_plan_parser.add_argument("--week", type=int, required=True)
    collect_reddit_plan_parser.add_argument("--plan", required=True, help="Path to a JSON collection plan.")
    collect_reddit_plan_parser.add_argument("--provider", default="reddit", choices=["reddit", "arctic-shift", "pullpush"])
    collect_reddit_plan_parser.add_argument("--after", help="Optional default lower bound as Unix seconds or YYYY-MM-DD ET.")
    collect_reddit_plan_parser.add_argument("--before", help="Optional default upper bound as Unix seconds or YYYY-MM-DD ET.")
    collect_reddit_plan_parser.add_argument("--no-replace-existing", action="store_true")

    collect_reddit_comments_parser = subparsers.add_parser(
        "collect-reddit-comments",
        help="Collect comments beneath already-targeted Reddit posts for a season/week.",
    )
    collect_reddit_comments_parser.add_argument("--season", type=int, required=True)
    collect_reddit_comments_parser.add_argument("--week", type=int, required=True)
    collect_reddit_comments_parser.add_argument("--provider", default="arctic-shift", choices=["arctic-shift", "pullpush"])
    collect_reddit_comments_parser.add_argument("--subreddit", action="append", default=[], help="Optional subreddit filter; repeatable.")
    collect_reddit_comments_parser.add_argument("--limit-posts", type=int, default=100)
    collect_reddit_comments_parser.add_argument("--comments-per-post", type=int, default=100)
    collect_reddit_comments_parser.add_argument("--min-post-comments", type=int, default=5)
    collect_reddit_comments_parser.add_argument("--min-post-score", type=int, default=0)
    collect_reddit_comments_parser.add_argument("--no-replace-existing", action="store_true")
    collect_reddit_comments_parser.add_argument("--skip-build-features", action="store_true")

    backfill_offseason_parser = subparsers.add_parser(
        "backfill-offseason-conversation",
        help="Date-bounded historical Reddit backfill for retro offseason weeks.",
    )
    backfill_offseason_parser.add_argument("--season", type=int, default=2025)
    backfill_offseason_parser.add_argument("--window", default="21..31")
    backfill_offseason_parser.add_argument("--provider", default="arctic-shift", choices=["arctic-shift", "pullpush"])
    backfill_offseason_parser.add_argument("--plan", help="Optional JSON collection plan to reuse for each requested week.")
    backfill_offseason_parser.add_argument("--subreddit", action="append", default=None, help="National/team-search subreddit; repeatable. Defaults to CFB.")
    backfill_offseason_parser.add_argument("--limit-per-query", type=int, default=100)
    backfill_offseason_parser.add_argument("--days-per-window", type=int, default=1)
    backfill_offseason_parser.add_argument("--through-date", default="2026-04-22", help="Last ET calendar date to include for open-ended final week.")
    backfill_offseason_parser.add_argument("--replace-existing", action="store_true", help="Delete matching existing targets before the first window for each plan entry.")
    backfill_offseason_parser.add_argument("--collect-comments", action="store_true", help="After post collection, collect comments beneath high-signal targeted posts.")
    backfill_offseason_parser.add_argument("--comment-post-limit", type=int, default=100)
    backfill_offseason_parser.add_argument("--comments-per-post", type=int, default=100)
    backfill_offseason_parser.add_argument("--min-comment-post-replies", type=int, default=5)
    backfill_offseason_parser.add_argument("--skip-build-features", action="store_true")
    backfill_offseason_parser.add_argument("--continue-on-error", action="store_true")
    backfill_offseason_parser.add_argument("--dry-run", action="store_true")

    purge_reddit_raw_parser = subparsers.add_parser(
        "purge-reddit-raw-content",
        help="Purge stored Reddit raw text/payload after aggregate features exist.",
    )
    purge_reddit_raw_parser.add_argument("--source-name", default="reddit")
    purge_reddit_raw_parser.add_argument("--provider", help="Optional provider filter, e.g. arctic_shift.")
    purge_reddit_raw_parser.add_argument("--older-than-days", type=int, default=2)
    purge_reddit_raw_parser.add_argument("--cutoff-utc", help="Explicit UTC cutoff, e.g. 2026-04-22 00:00:00.")
    purge_reddit_raw_parser.add_argument("--dry-run", action="store_true")
    purge_reddit_raw_parser.add_argument("--no-require-weekly-features", action="store_true")

    build_conversation_parser = subparsers.add_parser("build-conversation-features")
    build_conversation_parser.add_argument("--season", type=int, required=True)
    build_conversation_parser.add_argument("--week", type=int, required=True)
    build_conversation_parser.add_argument("--source-name", default="reddit")
    build_conversation_parser.add_argument("--pregame-days", type=int, default=7)
    build_conversation_parser.add_argument("--postgame-hours", type=int, default=48)

    hub_evidence_parser = subparsers.add_parser(
        "hub-computed-evidence",
        help="Write a full JSON evidence report for computed Hub v5 rows.",
    )
    hub_evidence_parser.add_argument("--output", default="output/hub-computed-evidence.json")
    hub_evidence_parser.add_argument("--week-start-from", default="2026-01-19")
    hub_evidence_parser.add_argument("--week-start-to", default="2026-04-22")
    hub_evidence_parser.add_argument(
        "--max-posts",
        type=int,
        default=0,
        help="0 includes every contributing source thread; positive values mark entries as truncated.",
    )

    sync_team_seasons_parser = subparsers.add_parser("sync-team-seasons")
    sync_team_seasons_parser.add_argument("--start-season", type=int)
    sync_team_seasons_parser.add_argument("--end-season", type=int)
    sync_team_seasons_parser.add_argument("--season", action="append", type=int, default=[])

    run_models_parser = subparsers.add_parser("run-models")
    run_models_parser.add_argument("--season", type=int, required=True)
    run_models_parser.add_argument("--through-week", type=int, required=True)
    run_models_parser.add_argument("--skip-heisman", action="store_true", help="Skip the Heisman model for a lighter team-model run.")

    run_heisman_parser = subparsers.add_parser("run-heisman-model")
    run_heisman_parser.add_argument("--season", type=int, required=True)
    run_heisman_parser.add_argument("--through-week", type=int, required=True)

    backfill_player_parser = subparsers.add_parser("backfill-player-context")
    backfill_player_parser.add_argument("--start-season", type=int, required=True)
    backfill_player_parser.add_argument("--end-season", type=int, required=True)
    backfill_player_parser.add_argument(
        "--classification",
        default="fbs",
        choices=["fbs"],
        help="Historical player-context ingest currently targets FBS because CFBD player stat endpoints map cleanly there.",
    )
    backfill_player_parser.add_argument("--through-week", type=int, help="Optional fixed week override for every season.")
    backfill_player_parser.add_argument("--skip-preseason", action="store_true", help="Skip roster/recruiting/transfer refreshes before loading player stats.")
    backfill_player_parser.add_argument("--skip-rankings", action="store_true", help="Skip official poll refreshes.")
    backfill_player_parser.add_argument("--skip-usage", action="store_true", help="Skip player usage refreshes.")
    backfill_player_parser.add_argument("--skip-value-metrics", action="store_true", help="Skip WEPA/value-metric refreshes.")
    backfill_player_parser.add_argument("--force", action="store_true", help="Reload seasons even when the destination tables already have rows.")
    backfill_player_parser.add_argument(
        "--skip-connectivity-check",
        action="store_true",
        help="Skip the upfront CFBD connectivity preflight. Use only if you intentionally want to rely on per-call failures.",
    )

    backfill_game_player_parser = subparsers.add_parser("backfill-game-player-stats")
    backfill_game_player_parser.add_argument("--start-season", type=int, required=True)
    backfill_game_player_parser.add_argument("--end-season", type=int, required=True)
    backfill_game_player_parser.add_argument("--include-postseason", action="store_true")
    backfill_game_player_parser.add_argument(
        "--missing-only",
        action="store_true",
        help="Only ingest source weeks whose completed FBS games still lack game-level player stats.",
    )
    backfill_game_player_parser.add_argument(
        "--classification",
        action="append",
        choices=["fbs", "fcs", "ii", "iii"],
        help=(
            "Repeat to target specific CFBD classifications for game-level player stats. "
            "Defaults to FBS-only so the historical archive pass stays aligned with the current public site."
        ),
    )
    backfill_game_player_parser.add_argument(
        "--max-weeks",
        type=int,
        help="Optional cap on the total number of source weeks processed across the full run. Useful for small, predictable recovery batches.",
    )
    backfill_game_player_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the source weeks that would be targeted without making any CFBD requests.",
    )
    backfill_game_player_parser.add_argument(
        "--skip-connectivity-check",
        action="store_true",
        help="Skip the upfront CFBD connectivity preflight. Use only if you intentionally want to rely on per-call failures.",
    )

    audit_parser = subparsers.add_parser("audit-data-coverage")
    audit_parser.add_argument("--output", default="output/data-coverage-audit.md")

    player_audit_parser = subparsers.add_parser("audit-player-archive")
    player_audit_parser.add_argument("--output", default="output/player-archive-audit.md")

    awards_audit_parser = subparsers.add_parser("audit-awards-archive")
    awards_audit_parser.add_argument("--output", default="output/awards-archive-audit.md")

    archive_readiness_parser = subparsers.add_parser("audit-archive-readiness")
    archive_readiness_parser.add_argument("--output", default="output/archive-readiness-audit.md")

    connectivity_parser = subparsers.add_parser("check-cfbd-connectivity")
    connectivity_parser.add_argument("--season", type=int, default=2025)

    history_status_parser = subparsers.add_parser("history-load-status")
    history_status_parser.add_argument("--start-season", type=int)
    history_status_parser.add_argument("--end-season", type=int)
    history_status_parser.add_argument("--output", default="output/history-load-status.md")

    refresh_local_health_parser = subparsers.add_parser("refresh-local-health")
    refresh_local_health_parser.add_argument("--start-season", type=int, default=2014)
    refresh_local_health_parser.add_argument("--end-season", type=int)
    refresh_local_health_parser.add_argument("--site-dir", default="output/site")
    refresh_local_health_parser.add_argument("--output", default="output/local-health-refresh.md")
    refresh_local_health_parser.add_argument("--skip-link-audit", action="store_true")

    validate_maintenance_parser = subparsers.add_parser("validate-maintenance")
    validate_maintenance_parser.add_argument("--output", default="output/maintenance-validation.md")
    validate_maintenance_parser.add_argument("--local-health", default="output/local-health-refresh.json")
    validate_maintenance_parser.add_argument("--bundle", default="output/maintenance-bundle.json")
    validate_maintenance_parser.add_argument("--queue", default="output/maintenance-action-queue.json")
    validate_maintenance_parser.add_argument(
        "--allow-p0",
        action="store_true",
        help="Report P0 maintenance actions as warnings instead of failing validation.",
    )

    integrity_parser = subparsers.add_parser("audit-competition-integrity")
    integrity_parser.add_argument("--output", default="output/competition-integrity-audit.md")

    program_history_integrity_parser = subparsers.add_parser("audit-program-history")
    program_history_integrity_parser.add_argument("--output", default="output/program-history-integrity-audit.md")

    subparsers.add_parser("repair-team-current-identity")

    sync_parser = subparsers.add_parser("sync-site")
    sync_parser.add_argument("--season", type=int)
    sync_parser.add_argument("--through-week", type=int)
    sync_parser.add_argument("--season-type", default="regular")
    sync_parser.add_argument("--output", default="output/rankings.html")
    sync_parser.add_argument("--site-output-dir", default="output/site")
    sync_parser.add_argument("--limit", type=int, default=100)
    sync_parser.add_argument("--open-report", action="store_true")
    sync_parser.add_argument("--skip-play-level", action="store_true", help="Skip drives and plays during weekly ingest for a faster sync.")
    sync_parser.add_argument("--skip-heisman", action="store_true", help="Skip the Heisman model during the combined site sync.")
    sync_parser.add_argument(
        "--skip-connectivity-check",
        action="store_true",
        help="Skip the upfront CFBD connectivity preflight. Use only if you intentionally want to rely on per-call failures.",
    )

    sync_incremental_parser = subparsers.add_parser("sync-site-incremental")
    sync_incremental_parser.add_argument("--season", type=int)
    sync_incremental_parser.add_argument("--through-week", type=int)
    sync_incremental_parser.add_argument("--season-type", default="regular")
    sync_incremental_parser.add_argument("--output", default="output/rankings.html")
    sync_incremental_parser.add_argument("--site-output-dir", default="output/site")
    sync_incremental_parser.add_argument("--limit", type=int, default=100)
    sync_incremental_parser.add_argument("--open-report", action="store_true")
    sync_incremental_parser.add_argument("--force-models", action="store_true")
    sync_incremental_parser.add_argument("--skip-play-level", action="store_true", help="Skip drives and plays during incremental ingest for a faster sync.")
    sync_incremental_parser.add_argument("--skip-heisman", action="store_true", help="Skip the Heisman model during the incremental site sync.")
    sync_incremental_parser.add_argument(
        "--skip-connectivity-check",
        action="store_true",
        help="Skip the upfront CFBD connectivity preflight. Use only if you intentionally want to rely on per-call failures.",
    )

    backfill_parser = subparsers.add_parser("backfill-cfbd-history")
    backfill_parser.add_argument("--start-season", type=int, required=True)
    backfill_parser.add_argument("--end-season", type=int, required=True)
    backfill_parser.add_argument("--include-postseason", action="store_true")
    backfill_parser.add_argument("--run-models", action="store_true")
    backfill_parser.add_argument("--build-site", action="store_true")
    backfill_parser.add_argument("--skip-play-level", action="store_true", help="Skip drives and plays to make large historical backfills safer.")
    backfill_parser.add_argument("--skip-heisman", action="store_true", help="Skip the Heisman model during historical backfills.")
    backfill_parser.add_argument(
        "--skip-connectivity-check",
        action="store_true",
        help="Skip the upfront CFBD connectivity preflight. Use only if you intentionally want to rely on per-call failures.",
    )

    site_parser = subparsers.add_parser("build-site")
    site_parser.add_argument("--output-dir", default="output/site")

    audit_links_parser = subparsers.add_parser("audit-links")
    audit_links_parser.add_argument("--site-dir", default="output/site")
    audit_links_parser.add_argument("--strict", action="store_true", help="Exit non-zero on any broken link.")

    report_parser = subparsers.add_parser("build-rankings-report")
    report_parser.add_argument("--output", default="output/rankings.html")
    report_parser.add_argument("--limit", type=int, default=100)

    publish_parser = subparsers.add_parser("build-published")
    publish_parser.add_argument("--output", default="output/rankings.html")
    publish_parser.add_argument("--site-output-dir", default="output/site")
    publish_parser.add_argument("--limit", type=int, default=100)
    publish_parser.add_argument("--open-report", action="store_true")

    # Fan Intelligence Hub v5 — data-model CLIs
    seed_archetypes_parser = subparsers.add_parser(
        "seed-archetypes",
        help="Load the 18 primary + 8 modifier archetypes into fanbase_archetype_taxonomy.",
    )
    seed_archetypes_parser.add_argument(
        "--seed-issue", action="store_true",
        help="Also load Issue N° 047 cover/editor/commiseration metadata.",
    )

    classify_fanbases_parser = subparsers.add_parser(
        "classify-fanbases",
        help="Run the v1 rules-based classifier over every active FBS team for a season.",
    )
    classify_fanbases_parser.add_argument("--season", type=int, required=True)
    classify_fanbases_parser.add_argument(
        "--classifier-version", default="v1.0",
        help="Stamp this classifier version onto every emitted row.",
    )
    classify_fanbases_parser.add_argument(
        "--backfill-history", type=int, default=0,
        help="Also write N prior seasons into fanbase_classification_history using the same classifier.",
    )

    compute_mood_week_parser = subparsers.add_parser(
        "compute-mood-week",
        help="Compute weekly mood scores for every FBS team (or load the Issue N° 047 seed).",
    )
    compute_mood_week_parser.add_argument("--week", default="2026-04-22", help="Week start date (YYYY-MM-DD).")
    compute_mood_week_parser.add_argument(
        "--from-seed", action="store_true",
        help="Skip conversation-pipeline compute and load the Issue N° 047 exemplar snapshot.",
    )
    compute_mood_week_parser.add_argument("--from-features", action="store_true")
    compute_mood_week_parser.add_argument("--no-from-seed", action="store_true")

    compute_rivalry_parser = subparsers.add_parser(
        "compute-rivalry-ratios",
        help="Compute the 12 canonical rivalry obsession ratios for the week.",
    )
    compute_rivalry_parser.add_argument("--week", default="2026-04-22")
    compute_rivalry_parser.add_argument("--from-seed", action="store_true")
    compute_rivalry_parser.add_argument("--from-features", action="store_true")
    compute_rivalry_parser.add_argument("--no-from-seed", action="store_true")

    mine_lexicon_parser = subparsers.add_parser(
        "mine-lexicon",
        help="Mine weekly phrase spikes and pick the featured Lexicon of the Week entry.",
    )
    mine_lexicon_parser.add_argument("--week", default="2026-04-22")
    mine_lexicon_parser.add_argument("--from-seed", action="store_true")
    mine_lexicon_parser.add_argument("--from-features", action="store_true")
    mine_lexicon_parser.add_argument("--no-from-seed", action="store_true")

    seed_hub_issue_parser = subparsers.add_parser(
        "seed-hub-issue",
        help="One-shot: run all five Hub v5 seeders for Issue N° 047.",
    )
    seed_hub_issue_parser.add_argument("--season", type=int, default=2025)
    seed_hub_issue_parser.add_argument("--week", default="2026-04-22")

    seed_retro_issue_parser = subparsers.add_parser(
        "seed-retro-issue",
        help="Seed one retro offseason issue (038..047) with editorial provenance.",
    )
    seed_retro_issue_parser.add_argument("--issue", required=True)

    subparsers.add_parser(
        "seed-retro-all",
        help="Seed all retro offseason issues (038..047) with editorial provenance.",
    )

    build_retro_parser = subparsers.add_parser(
        "build-retro-pages",
        help="Render the retro offseason issue pages under hub/retro.",
    )
    build_retro_parser.add_argument("--output-dir", default="output/site")
    build_retro_parser.add_argument("--bust-cache", action="store_true")

    retro_calibrate_parser = subparsers.add_parser(
        "retro-calibrate",
        help="Run retro offseason directional calibration checks.",
    )
    retro_calibrate_parser.add_argument("--window", default="21..30")

    sync_team_brand_parser = subparsers.add_parser(
        "sync-team-brand-assets",
        help="Sync team brand colors, mascots, and logo assets from CFBD.",
    )
    sync_team_brand_parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Season year to request from CFBD. Defaults to current UTC year.",
    )
    sync_team_brand_parser.add_argument(
        "--refresh-assets",
        action="store_true",
        help="Force re-download even if content hash matches.",
    )
    sync_team_brand_parser.add_argument(
        "--classification",
        choices=["fbs", "fcs", "ii", "iii"],
        default="fbs",
        help="NCAA classification to sync (default: fbs).",
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = AppConfig.from_env()
    from cfb_rankings.db import Database
    from cfb_rankings.storage import Repository

    db = Database(config.database_url)
    repository = Repository(db)
    schema_path = Path(__file__).resolve().parents[2] / "research" / "cfb-data-schema-sqlite.sql"

    if args.command == "init-db":
        db.apply_sql_file(schema_path)
        apply_runtime_migrations(db)
        repository.seed_levels()
        return

    apply_runtime_migrations(db)

    if args.command == "apply-migrations":
        print("Runtime migrations + SQL migrations applied.")
        rows = db.query_all(
            "select migration_id, applied_at_utc from schema_migrations order by migration_id"
        )
        for row in rows:
            print(f"  {row['migration_id']} @ {row['applied_at_utc']}")
        return

    if args.command == "seed-source-registry":
        from cfb_rankings.ingest.fanintel_seeds import seed_source_registry
        result = seed_source_registry(db)
        print(f"source_registry: inserted={result['inserted']} updated={result['updated']} total={result['total']}")
        return

    if args.command == "compute-cohort-week":
        from cfb_rankings.cohorts.aggregate import compute_cohort_week
        result = compute_cohort_week(db, args.week, teams=args.teams)
        print(f"compute-cohort-week {args.week}: "
              f"docs_considered={result['docs_considered']} "
              f"docs_skipped={result['docs_skipped']} "
              f"cells_written={result['cells_written']}")
        return

    if args.command == "compute-divergence":
        from cfb_rankings.cohorts.divergence import compute_divergence_week
        result = compute_divergence_week(db, args.week)
        print(f"compute-divergence {args.week}: teams_written={result['teams_written']}")
        return

    if args.command == "tag-player-mentions":
        from cfb_rankings.ingest.player_name_tagger import tag_player_mentions
        result = tag_player_mentions(
            db, season_year=args.season, week=args.week,
            doc_limit=args.limit, commit=args.commit,
            preview=getattr(args, "preview", False),
        )
        mode = "COMMIT" if args.commit else "DRY-RUN"
        print(
            f"[{mode}] tag-player-mentions season={args.season}"
            + (f" week={args.week}" if args.week is not None else "")
            + f": docs_scanned={result['docs_scanned']}"
            + f" matches={result['matches']}"
            + f" skipped_ambiguous={result['skipped_ambiguous']}"
            + f" rows_written={result['rows_written']}"
        )
        return

    if args.command == "compute-player-week-mood":
        from cfb_rankings.cohorts.player_aggregate import compute_player_week_mood
        result = compute_player_week_mood(db, args.week, players=args.players)
        print(f"compute-player-week-mood {args.week}: "
              f"rows_read={result['rows_read']} "
              f"players_touched={result['players_touched']} "
              f"cells_written={result['cells_written']}")
        return

    if args.command == "build-the-room-board":
        from cfb_rankings.the_room_board import build_the_room_board
        out = build_the_room_board(db, season_year=args.season, week=args.week)
        print(f"the-room board written: {out}")
        return

    if args.command == "build-players-landing":
        from cfb_rankings.players_landing import build_players_landing
        out = build_players_landing(db, season_year=args.season, week=args.week)
        print(f"players landing written: {out}")
        return

    if args.command == "build-signature-story-board":
        from cfb_rankings.signature_story_board import build_signature_story_board
        out = build_signature_story_board(db, season_year=args.season)
        print(f"signature-stories board written: {out}")
        return

    if args.command == "compute-player-season-mood":
        from cfb_rankings.cohorts.player_aggregate import compute_player_season_mood
        result = compute_player_season_mood(db, args.season, players=args.players)
        print(f"compute-player-season-mood {args.season}: "
              f"rows_read={result['rows_read']} "
              f"players_touched={result['players_touched']} "
              f"cells_written={result['cells_written']}")
        return

    if args.command == "build-methodology":
        from cfb_rankings.provenance.methodology_page import write_methodology_page
        out = write_methodology_page(db)
        print(f"methodology page written: {out}")
        return

    if args.command == "signal-emit":
        from cfb_rankings.bets.signal_flow import emit_signal_event
        eid = emit_signal_event(
            db,
            player_id=args.player_id,
            event_type=args.event_type,
            headline=args.headline,
            sub_line=args.sub_line,
            source_url=args.source_url,
            source_name=args.source_name,
            decay_hours=args.decay_hours,
            dedup_key=args.dedup_key,
        )
        print(f"emitted signal event id={eid} for player_id={args.player_id}")
        return

    if args.command == "signal-list":
        from cfb_rankings.bets.signal_flow import fetch_active_signals
        sigs = fetch_active_signals(db, args.player_id)
        print(f"{len(sigs)} active signal(s) for player_id={args.player_id}:")
        for s in sigs:
            print(
                f"  #{s.player_signal_event_id} [{s.event_type}] {s.headline!r} "
                f"— remaining {s.remaining_fraction():.2f} — "
                f"expires {s.expires_at.isoformat()}"
            )
        return

    if args.command == "signal-prune":
        from cfb_rankings.bets.signal_flow import prune_expired_signals
        n = prune_expired_signals(db, older_than_hours=args.older_than_hours)
        print(f"pruned {n} expired signal(s)")
        return

    if args.command == "player-mood":
        from cfb_rankings.fan_intelligence import fetch_player_mood_profile
        player_id = _resolve_player_identifier(db, args.player)
        if player_id is None:
            print(f"error: could not resolve player '{args.player}'.")
            return
        season = args.season or _default_player_season(db, player_id)
        profile = fetch_player_mood_profile(db, player_id, season, args.week)
        if args.json:
            print(json.dumps(profile, indent=2, default=str))
            return
        _print_player_mood(db, profile, player_id, season, args.week)
        return

    if args.command == "player-signature":
        from cfb_rankings.signature_story import (
            build_candidate_scoreboard,
            fetch_player_signature_story,
        )
        player_id = _resolve_player_identifier(db, args.player)
        if player_id is None:
            print(f"error: could not resolve player '{args.player}' — "
                  f"pass a numeric id or a slug ending in '-<id>'.")
            return
        season = args.season or _default_player_season(db, player_id)
        story = fetch_player_signature_story(db, player_id, season, args.week)
        if args.json:
            print(json.dumps(story, indent=2, default=str))
            return
        _print_signature_story(db, story, player_id, season, args.week,
                               build_candidate_scoreboard)
        return

    if args.command == "scrape-health":
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=args.since_days)).isoformat()
        rows = db.query_all(
            """
            select source_id,
                   max(run_date) as last_run,
                   (select rows_inserted from scrape_health sh2
                    where sh2.source_id = sh.source_id order by run_date desc limit 1) as rows_inserted,
                   (select status from scrape_health sh2
                    where sh2.source_id = sh.source_id order by run_date desc limit 1) as status
            from scrape_health sh
            where run_date >= :cutoff
            group by source_id
            """,
            {"cutoff": cutoff},
        )
        priority = {"error": 0, "empty": 1, "skipped": 2, "ok": 3}
        rows.sort(key=lambda r: (priority.get(r["status"], 9), r["source_id"]))
        header = f"{'source_id':<28} {'last_run':<12} {'rows':>7} {'status':<8}"
        print(header)
        print("-" * len(header))
        if not rows:
            print("(no scrape_health rows in the last"
                  f" {args.since_days} days — adapters not yet wired)")
            return
        for row in rows:
            print(f"{(row['source_id'] or '')[:28]:<28} "
                  f"{(row['last_run'] or '')[:12]:<12} "
                  f"{row['rows_inserted'] or 0:>7} "
                  f"{row['status'] or '':<8}")
        return

    if args.command == "fanintel-status":
        from datetime import date, timedelta
        print("=" * 64)
        print("Fan Intelligence — operational status")
        print("=" * 64)

        n_fanintel = db.query_one(
            "select count(*) as n from source_registry where source_id is not null"
        )["n"]
        n_active = db.query_one(
            "select count(*) as n from source_registry where source_id is not null and is_active = 1"
        )["n"]
        print(f"\nsource_registry: {n_fanintel} fanintel rows ({n_active} active)")
        tier_rows = db.query_all(
            "select tier, count(*) as n from source_registry "
            "where source_id is not null group by tier order by tier"
        )
        for r in tier_rows:
            print(f"  tier {r['tier']}: {r['n']}")

        n_pt = db.query_one("select count(*) as n from priority_teams")["n"]
        n_pt_needs = db.query_one(
            "select count(*) as n from priority_teams where needs_research = 1"
        )["n"]
        print(f"\npriority_teams: {n_pt} teams ({n_pt_needs} flagged needs_research)")

        cutoff = (date.today() - timedelta(days=7)).isoformat()
        health_rows = db.query_all(
            "select status, count(*) as n from scrape_health "
            "where run_date >= :cutoff group by status order by status",
            {"cutoff": cutoff},
        )
        if health_rows:
            print(f"\nscrape_health (last 7 days):")
            for r in health_rows:
                print(f"  {r['status']}: {r['n']}")
        else:
            print("\nscrape_health: no runs in the last 7 days")

        cohort_rows = db.query_one(
            "select count(*) as n, count(distinct team_id) as teams, "
            "count(distinct week) as weeks from team_cohort_week"
        )
        print(f"\nteam_cohort_week: {cohort_rows['n']} cells across "
              f"{cohort_rows['teams']} teams × {cohort_rows['weeks']} weeks")

        obs_rows = db.query_one(
            "select count(*) as n, count(distinct source_id) as srcs "
            "from source_observations"
        ) if db.query_one(
            "select 1 as x from sqlite_master where type='table' and name='source_observations'"
        ) else None
        if obs_rows:
            print(f"\nsource_observations: {obs_rows['n']} rows from "
                  f"{obs_rows['srcs']} distinct source_id's")

        docs = db.query_one(
            "select count(*) as n from conversation_documents"
        )["n"]
        docs_w_src = db.query_one(
            "select count(*) as n from conversation_documents where source_id is not null"
        )["n"]
        print(f"\nconversation_documents: {docs} rows "
              f"({docs_w_src} with new-schema source_id populated)")

        div_rows = db.query_one(
            "select count(*) as n, count(case when divergence_score is not null then 1 end) as qual "
            "from team_cohort_divergence_week"
        )
        print(f"\nteam_cohort_divergence_week: {div_rows['n']} rows "
              f"({div_rows['qual']} with qualifying divergence_score)")

        print("\n" + "=" * 64)
        return

    if args.command == "validate-feed-urls":
        from cfb_rankings.ingest.feed_validator import (
            validate_registry_feeds, validate_priority_team_wiki_pages,
        )
        print("Validating source_registry terms_url entries...")
        result = validate_registry_feeds(
            db, include_templates=args.include_templates,
        )
        print(f"  ok={result['ok']} error={result['error']} "
              f"skipped={result['skipped']} total={result['total']}")
        if result["error"] > 0:
            print("  See `python manage.py scrape-health` for error details.")
        if args.include_wiki_pages:
            print("Validating priority_teams wiki_* pages...")
            wiki = validate_priority_team_wiki_pages(db)
            issue_count = 0
            for team in wiki["teams"]:
                if team["issues"]:
                    issue_count += 1
                    print(f"  {team['team_name']}:")
                    for issue in team["issues"]:
                        print(f"    - {issue}")
            if issue_count == 0:
                print("  all wiki pages resolve OK")
        return

    if args.command == "seed-feed-instances":
        from cfb_rankings.ingest.fanintel_seeds import (
            seed_beat_writer_feeds, seed_substack_feeds,
            seed_podcast_feeds, seed_radio_feeds,
        )
        totals = {"inserted": 0, "updated": 0, "skipped": 0}
        for family_name, fn in [
            ("beat_writer", seed_beat_writer_feeds),
            ("substack", seed_substack_feeds),
            ("podcast", seed_podcast_feeds),
            ("radio", seed_radio_feeds),
        ]:
            result = fn(db)
            totals["inserted"] += result["inserted"]
            totals["updated"] += result["updated"]
            totals["skipped"] += result["skipped"]
            print(f"  {family_name}: inserted={result['inserted']} "
                  f"updated={result['updated']} skipped={result['skipped']}")
        print(f"seed-feed-instances totals: inserted={totals['inserted']} "
              f"updated={totals['updated']} skipped={totals['skipped']}")
        return

    if args.command == "seed-source-instances":
        from cfb_rankings.ingest.fanintel_seeds import seed_source_instances
        result = seed_source_instances(db)
        print(f"source-instances: inserted={result['inserted']} "
              f"updated={result['updated']} total={result['total']} "
              f"skipped_no_template={result['skipped_no_template']}")
        return

    if args.command == "seed-priority-teams":
        from cfb_rankings.ingest.fanintel_seeds import seed_priority_teams
        result = seed_priority_teams(db)
        print(
            f"priority_teams: inserted={result['inserted']} updated={result['updated']} "
            f"total={result['total']} missing={len(result['missing_team_names'])}"
        )
        for name in result["missing_team_names"]:
            print(f"  MISSING team_name: {name}")
        return

    if args.command == "ingest-sportsdb":
        if not config.sportsdb_api_key:
            raise RuntimeError("Missing required environment variable for this command: SPORTSDB_API_KEY")
        from cfb_rankings.clients.sportsdb import SportsDbClient
        from cfb_rankings.ingest.sportsdb import ingest_sportsdb_league

        repository.seed_levels()
        sportsdb = SportsDbClient(config.sportsdb_api_key, config.sportsdb_base_url, config.request_timeout_seconds)
        ingest_sportsdb_league(
            repository=repository,
            client=sportsdb,
            league_id=args.league_id,
            season=args.season,
            level_code=args.level_code,
            conference_name=args.conference,
        )
        return

    if args.command == "list-sportsdb-leagues":
        if not config.sportsdb_api_key:
            raise RuntimeError("Missing required environment variable for this command: SPORTSDB_API_KEY")
        from cfb_rankings.clients.sportsdb import SportsDbClient

        sportsdb = SportsDbClient(config.sportsdb_api_key, config.sportsdb_base_url, config.request_timeout_seconds)
        leagues = sportsdb.search_all_leagues(country=args.country, sport=args.sport)
        for league in leagues:
            league_id = league.get("idLeague") or league.get("id")
            league_name = league.get("strLeague") or "Unknown League"
            league_alt = league.get("strLeagueAlternate") or ""
            print(f"{league_id}\t{league_name}\t{league_alt}")
        return

    if args.command == "ingest-cfbd-week":
        if not config.cfbd_api_key:
            raise RuntimeError("Missing required environment variable for this command: CFBD_API_KEY")
        from cfb_rankings.clients.cfbd import CfbdClient
        from cfb_rankings.ingest.cfbd import ingest_cfbd_week

        repository.seed_levels()
        cfbd = CfbdClient(config.cfbd_api_key, config.cfbd_base_url, config.request_timeout_seconds)
        include_drives = not (args.skip_play_level or args.skip_drives)
        include_plays = not (args.skip_play_level or args.skip_plays)
        ingest_cfbd_week(
            repository=repository,
            db=db,
            client=cfbd,
            season=args.season,
            week=args.week,
            season_type=args.season_type,
            include_lines=not args.skip_lines,
            include_weather=not args.skip_weather,
            include_advanced_game_stats=not args.skip_advanced_stats,
            include_drives=include_drives,
            include_plays=include_plays,
            include_game_player_stats=args.include_game_player_stats,
        )
        return

    if args.command == "ingest-cfbd-preseason":
        if not config.cfbd_api_key:
            raise RuntimeError("Missing required environment variable for this command: CFBD_API_KEY")
        from cfb_rankings.clients.cfbd import CfbdClient
        from cfb_rankings.ingest.cfbd import ingest_cfbd_preseason

        repository.seed_levels()
        cfbd = CfbdClient(config.cfbd_api_key, config.cfbd_base_url, config.request_timeout_seconds)
        teams = list(args.team or [])
        if args.all_season_teams:
            teams = _season_team_names(db, args.season)
            print(f"Loading preseason context for {len(teams)} season teams...", flush=True)
        elif teams:
            print(f"Loading preseason context for {len(teams)} explicitly requested teams...", flush=True)
        elif args.classification:
            print(f"Loading preseason context tables plus the full {args.classification.upper()} roster snapshot...", flush=True)
        else:
            print("Loading preseason context tables without team roster pulls.", flush=True)
        ingest_cfbd_preseason(
            repository=repository,
            db=db,
            client=cfbd,
            season=args.season,
            teams=teams,
            classification=args.classification,
        )
        return

    if args.command == "import-player-honors":
        from cfb_rankings.ingest.honors import import_player_honors_csv

        imported = import_player_honors_csv(
            repository=repository,
            db=db,
            csv_path=args.csv,
            default_source_name=args.source_name,
        )
        print(f"Imported {imported} player honor rows from {args.csv}.", flush=True)
        return

    if args.command == "seed-team-aliases":
        inserted = repository.seed_team_aliases(args.season)
        print(f"Seeded or refreshed {inserted} team alias rows for season {args.season}.", flush=True)
        return

    if args.command == "collect-reddit-watchlist":
        from cfb_rankings.clients.historical_reddit import create_historical_reddit_client, normalize_historical_provider
        from cfb_rankings.ingest.conversation import collect_reddit_watchlist

        repository.seed_levels()
        repository.ensure_season(args.season)
        provider_name = normalize_historical_provider(args.provider)
        reddit = create_historical_reddit_client(provider_name, timeout_seconds=config.request_timeout_seconds)
        summary = collect_reddit_watchlist(
            repository=repository,
            db=db,
            client=reddit,
            season=args.season,
            week=args.week,
            team_names=list(args.team or []),
            limit_teams=args.limit_teams,
            subreddit=(args.subreddit or "").strip() or None,
            audience_bucket=args.audience_bucket,
            search_limit=args.search_limit,
            after=_coerce_epoch_bound(args.after),
            before=_coerce_epoch_bound(args.before),
            provider_name=provider_name,
            replace_existing=not args.no_replace_existing,
        )
        print(
            f"Collected Reddit watchlist data: {summary['document_count']} documents across {summary['watchlist_team_count']} teams and {summary['target_count']} team targets.",
            flush=True,
        )
        return

    if args.command == "collect-reddit-plan":
        from cfb_rankings.clients.historical_reddit import create_historical_reddit_client, normalize_historical_provider
        from cfb_rankings.ingest.conversation import collect_reddit_subreddit_listing, collect_reddit_watchlist

        repository.seed_levels()
        repository.ensure_season(args.season)
        default_provider = normalize_historical_provider(args.provider)
        plan_entries = _load_reddit_collection_plan(args.plan)
        total_documents = 0
        total_targets = 0

        for index, entry in enumerate(plan_entries, start=1):
            mode = str(entry.get("mode") or "team_search").strip().lower()
            audience_bucket = str(entry.get("audience_bucket") or "national").strip().lower()
            subreddit = str(entry.get("subreddit") or "").strip()
            provider_name = normalize_historical_provider(str(entry.get("provider") or default_provider))
            reddit = create_historical_reddit_client(provider_name, timeout_seconds=config.request_timeout_seconds)
            after = _coerce_epoch_bound(entry.get("after") or args.after)
            before = _coerce_epoch_bound(entry.get("before") or args.before)
            replace_existing = _coerce_plan_bool(entry.get("replace_existing"), default=not args.no_replace_existing)
            if mode == "team_search":
                team_names = _coerce_plan_string_list(entry.get("teams") if "teams" in entry else entry.get("team"))
                summary = collect_reddit_watchlist(
                    repository=repository,
                    db=db,
                    client=reddit,
                    season=args.season,
                    week=args.week,
                    team_names=team_names,
                    limit_teams=int(entry.get("limit_teams") or 25),
                    subreddit=subreddit or None,
                    audience_bucket=audience_bucket,
                    search_limit=int(entry.get("search_limit") or 15),
                    after=after,
                    before=before,
                    provider_name=provider_name,
                    replace_existing=replace_existing,
                )
                total_documents += int(summary["document_count"])
                total_targets += int(summary["target_count"])
                print(
                    f"[{index}/{len(plan_entries)}] team_search r/{subreddit or 'sitewide'} "
                    f"bucket={audience_bucket}: {summary['document_count']} docs, {summary['target_count']} targets.",
                    flush=True,
                )
                continue

            if mode == "subreddit_listing":
                team_name = str(entry.get("team") or "").strip()
                if not team_name:
                    raise RuntimeError(f"Plan entry {index} is missing required field 'team' for mode=subreddit_listing.")
                summary = collect_reddit_subreddit_listing(
                    repository=repository,
                    db=db,
                    client=reddit,
                    season=args.season,
                    week=args.week,
                    target_team_name=team_name,
                    subreddit=subreddit,
                    audience_bucket=audience_bucket,
                    listing=str(entry.get("listing") or "new").strip().lower(),
                    limit=int(entry.get("limit") or 25),
                    require_cfb_context=_coerce_plan_bool(entry.get("require_cfb_context"), default=True),
                    after=after,
                    before=before,
                    provider_name=provider_name,
                    replace_existing=replace_existing,
                )
                total_documents += int(summary["document_count"])
                total_targets += int(summary["target_count"])
                print(
                    f"[{index}/{len(plan_entries)}] subreddit_listing {summary['team_name']} from r/{summary['subreddit']} "
                    f"bucket={audience_bucket}: {summary['document_count']} docs, {summary['target_count']} targets, "
                    f"skipped_non_cfb={summary['skipped_non_cfb']}.",
                    flush=True,
                )
                continue

            raise RuntimeError(f"Unsupported Reddit collection plan mode '{mode}' in entry {index}.")

        print(
            f"Collected Reddit plan data: {total_documents} total documents and {total_targets} total team targets.",
            flush=True,
        )
        return

    if args.command == "collect-reddit-comments":
        from cfb_rankings.clients.historical_reddit import create_historical_reddit_client, normalize_historical_provider
        from cfb_rankings.ingest.conversation import (
            build_conversation_features,
            build_phrase_mentions_weekly,
            collect_reddit_comments_for_posts,
        )

        repository.seed_levels()
        repository.ensure_season(args.season)
        provider_name = normalize_historical_provider(args.provider)
        reddit = create_historical_reddit_client(provider_name, timeout_seconds=config.request_timeout_seconds)
        summary = collect_reddit_comments_for_posts(
            db=db,
            client=reddit,
            season=args.season,
            week=args.week,
            provider_name=provider_name,
            subreddits=list(args.subreddit or []),
            limit_posts=args.limit_posts,
            comments_per_post=args.comments_per_post,
            min_post_comments=args.min_post_comments,
            min_post_score=args.min_post_score,
            replace_existing=not args.no_replace_existing,
        )
        print(
            f"Collected Reddit comments: {summary['document_count']} comments from {summary['post_count']} posts "
            f"and {summary['target_count']} attributed team targets "
            f"(skipped_no_target={summary.get('skipped_no_target', 0)}).",
            flush=True,
        )
        if not args.skip_build_features:
            feature_summary = build_conversation_features(db=db, season=args.season, week=args.week, source_name="reddit")
            phrase_summary = build_phrase_mentions_weekly(db=db, season=args.season, week=args.week, source_name="reddit")
            print(
                f"Rebuilt features after comments: weekly={feature_summary['weekly_rows']} daily={feature_summary['daily_rows']} "
                f"rivals={feature_summary['rival_mention_rows']} phrases={phrase_summary['phrase_rows']}.",
                flush=True,
            )
        return

    if args.command == "purge-reddit-raw-content":
        from cfb_rankings.ingest.conversation import purge_reddit_raw_content

        summary = purge_reddit_raw_content(
            db=db,
            source_name=args.source_name,
            provider_name=args.provider,
            older_than_days=args.older_than_days,
            cutoff_utc=args.cutoff_utc,
            dry_run=args.dry_run,
            require_weekly_features=not args.no_require_weekly_features,
        )
        action = "Would purge" if summary["dry_run"] else "Purged"
        display_count = summary["documents_examined"] if summary["dry_run"] else summary["documents_purged"]
        print(
            f"{action} {display_count} Reddit raw documents "
            f"(examined={summary['documents_examined']}, cutoff={summary['cutoff_utc']}).",
            flush=True,
        )
        return

    if args.command == "backfill-offseason-conversation":
        from cfb_rankings.clients.historical_reddit import create_historical_reddit_client, normalize_historical_provider
        from cfb_rankings.ingest.conversation import (
            build_conversation_features,
            build_phrase_mentions_weekly,
            collect_reddit_comments_for_posts,
            collect_reddit_subreddit_listing,
            collect_reddit_watchlist,
        )
        from cfb_rankings.ingest.hub_data_retro import seed_offseason_week_map

        repository.seed_levels()
        repository.ensure_season(args.season)
        seed_offseason_week_map(db)
        provider_name = normalize_historical_provider(args.provider)
        client = create_historical_reddit_client(provider_name, timeout_seconds=config.request_timeout_seconds)
        week_records = _offseason_week_records(db, season=args.season, window=args.window)
        all_week_records = _offseason_week_records(db, season=args.season, window="21..31")
        if not week_records:
            raise RuntimeError(f"No offseason weeks found for {args.season} window {args.window}.")
        base_plan = _load_reddit_collection_plan(args.plan) if args.plan else None
        total_documents = 0
        total_targets = 0
        total_errors = 0
        for record in week_records:
            week = int(record["offseason_week"])
            week_start = str(record["week_start_date"])
            week_end = _offseason_week_end(record, all_week_records, args.through_date)
            plan_entries = base_plan or _default_offseason_backfill_plan(
                db,
                week_start=week_start,
                fallback_week_start=_next_issue_week_start(week_start, all_week_records),
                subreddits=list(args.subreddit or ["CFB"]),
                limit_per_query=args.limit_per_query,
            )
            if args.dry_run:
                print(f"[dry-run] week={week} {week_start}..{week_end.isoformat()} entries={len(plan_entries)} provider={provider_name}", flush=True)
                continue
            for entry_index, entry in enumerate(plan_entries, start=1):
                first_window = True
                for window_start, window_end in _iter_date_windows(_parse_iso_date(week_start), week_end, args.days_per_window):
                    after = _date_bound_to_epoch(window_start)
                    before = _date_bound_to_epoch(window_end)
                    try:
                        summary = _run_reddit_plan_entry(
                            repository=repository,
                            db=db,
                            client=client,
                            entry=entry,
                            season=args.season,
                            week=week,
                            provider_name=provider_name,
                            after=after,
                            before=before,
                            replace_existing=args.replace_existing and first_window,
                            collect_reddit_watchlist=collect_reddit_watchlist,
                            collect_reddit_subreddit_listing=collect_reddit_subreddit_listing,
                        )
                    except Exception as exc:
                        total_errors += 1
                        print(
                            f"[week {week}] ERROR entry={entry_index} window={window_start.isoformat()}..{window_end.isoformat()} provider={provider_name}: {exc}",
                            flush=True,
                        )
                        if not args.continue_on_error:
                            raise
                        continue
                    finally:
                        first_window = False
                    total_documents += int(summary.get("document_count") or 0)
                    total_targets += int(summary.get("target_count") or 0)
                    print(
                        f"[week {week}] entry={entry_index}/{len(plan_entries)} {window_start.isoformat()}..{window_end.isoformat()} "
                        f"docs={summary.get('document_count', 0)} targets={summary.get('target_count', 0)}",
                        flush=True,
                    )
            if args.collect_comments:
                try:
                    comment_summary = collect_reddit_comments_for_posts(
                        db=db,
                        client=client,
                        season=args.season,
                        week=week,
                        provider_name=provider_name,
                        subreddits=list(args.subreddit or []),
                        limit_posts=args.comment_post_limit,
                        comments_per_post=args.comments_per_post,
                        min_post_comments=args.min_comment_post_replies,
                        replace_existing=args.replace_existing,
                    )
                    total_documents += int(comment_summary.get("document_count") or 0)
                    total_targets += int(comment_summary.get("target_count") or 0)
                    print(
                        f"[week {week}] comments={comment_summary['document_count']} "
                        f"from_posts={comment_summary['post_count']} targets={comment_summary['target_count']} "
                        f"skipped_no_target={comment_summary.get('skipped_no_target', 0)}",
                        flush=True,
                    )
                except Exception as exc:
                    total_errors += 1
                    print(f"[week {week}] ERROR comments provider={provider_name}: {exc}", flush=True)
                    if not args.continue_on_error:
                        raise
            if not args.skip_build_features:
                feature_summary = build_conversation_features(db=db, season=args.season, week=week, source_name="reddit")
                phrase_summary = build_phrase_mentions_weekly(db=db, season=args.season, week=week, source_name="reddit")
                print(
                    f"[week {week}] features={feature_summary['weekly_rows']} daily={feature_summary['daily_rows']} "
                    f"rivals={feature_summary['rival_mention_rows']} phrases={phrase_summary['phrase_rows']}",
                    flush=True,
                )
        print(
            f"Backfilled offseason conversation: {total_documents} documents, {total_targets} targets, errors={total_errors}.",
            flush=True,
        )
        if total_errors:
            raise SystemExit(1)
        return

    if args.command == "build-conversation-features":
        from cfb_rankings.ingest.conversation import build_conversation_features

        summary = build_conversation_features(
            db=db,
            season=args.season,
            week=args.week,
            source_name=args.source_name,
            pregame_days=args.pregame_days,
            postgame_hours=args.postgame_hours,
        )
        print(
            "Built conversation features: "
            f"{summary['daily_rows']} daily rows, "
            f"{summary['weekly_rows']} weekly rows, "
            f"{summary['game_rows']} game rows, "
            f"{summary['storyline_rows']} storyline rows.",
            flush=True,
        )
        return

    if args.command == "hub-computed-evidence":
        from cfb_rankings.ingest.hub_evidence import write_hub_computed_evidence_report

        summary = write_hub_computed_evidence_report(
            db=db,
            output_path=args.output,
            week_start_from=args.week_start_from,
            week_start_to=args.week_start_to,
            max_posts=args.max_posts,
        )
        no_truncation = "yes" if args.max_posts == 0 else "no"
        print(
            f"Wrote Hub computed evidence to {summary['output']} "
            f"(mood={summary['mood_rows']}, rivalry={summary['rivalry_rows']}, "
            f"lexicon={summary['lexicon_rows']}, no_hidden_truncation={no_truncation}).",
            flush=True,
        )
        return

    if args.command == "sync-team-seasons":
        if not config.cfbd_api_key:
            raise RuntimeError("Missing required environment variable for this command: CFBD_API_KEY")
        from cfb_rankings.clients.cfbd import CfbdClient
        from cfb_rankings.ingest.cfbd import sync_cfbd_team_seasons

        repository.seed_levels()
        cfbd = CfbdClient(config.cfbd_api_key, config.cfbd_base_url, config.request_timeout_seconds)
        seasons = sorted(set(args.season or []))
        if args.start_season is not None and args.end_season is not None:
            seasons.extend(range(args.start_season, args.end_season + 1))
        if not seasons:
            seasons = [int(row["season_year"]) for row in db.query_all("select season_year from seasons order by season_year")]
        seasons = sorted(set(seasons))
        print(f"Refreshing season-aware conference memberships for: {', '.join(str(season) for season in seasons)}", flush=True)
        sync_cfbd_team_seasons(repository=repository, db=db, client=cfbd, seasons=seasons)
        return

    if args.command == "run-models":
        cfbd = None
        if config.cfbd_api_key:
            from cfb_rankings.clients.cfbd import CfbdClient

            cfbd = CfbdClient(config.cfbd_api_key, config.cfbd_base_url, config.request_timeout_seconds)
        from cfb_rankings.pipeline import run_weekly_models

        run_weekly_models(
            db=db,
            model_version=config.model_version,
            season=args.season,
            through_week=args.through_week,
            cfbd_client=cfbd,
            include_heisman=not args.skip_heisman,
        )
        return

    if args.command == "run-heisman-model":
        cfbd = None
        if config.cfbd_api_key:
            from cfb_rankings.clients.cfbd import CfbdClient

            cfbd = CfbdClient(config.cfbd_api_key, config.cfbd_base_url, config.request_timeout_seconds)
        from cfb_rankings.models.heisman import HeismanModelRunner

        summary = _model_summary_for_week(db, args.season, args.through_week)
        if summary is None:
            raise RuntimeError(
                f"No team model snapshot found for season {args.season} week {args.through_week}. "
                "Run `python manage.py run-models --season <season> --through-week <week>` first."
            )

        print(
            f"Running Heisman model against existing model run {summary['model_run_id']} for season {args.season} week {args.through_week}...",
            flush=True,
        )
        runner = HeismanModelRunner(db, config.model_version)
        runner.run(
            model_run_id=int(summary["model_run_id"]),
            season=args.season,
            through_week=args.through_week,
            cfbd_client=cfbd,
        )
        return

    if args.command == "backfill-player-context":
        if not config.cfbd_api_key:
            raise RuntimeError("Missing required environment variable for this command: CFBD_API_KEY")
        if args.end_season < args.start_season:
            raise RuntimeError("--end-season must be greater than or equal to --start-season")
        _ensure_cfbd_connectivity_or_exit(
            config=config,
            season=args.start_season,
            label="player-context backfill",
            skip_check=args.skip_connectivity_check,
        )

        from cfb_rankings.clients.cfbd import CfbdClient
        from cfb_rankings.ingest.cfbd import ingest_cfbd_preseason
        from cfb_rankings.models.heisman import HeismanModelRunner

        db.apply_sql_file(schema_path)
        apply_runtime_migrations(db)
        repository.seed_levels()

        cfbd = CfbdClient(config.cfbd_api_key, config.cfbd_base_url, config.request_timeout_seconds)
        runner = HeismanModelRunner(db, config.model_version)

        total_summary = {
            "seasons": 0,
            "rankings": 0,
            "season_stats": 0,
            "usage": 0,
            "value_metrics": 0,
        }
        for season in range(args.start_season, args.end_season + 1):
            target_week = args.through_week or _max_competition_week(db, season)
            if target_week <= 0:
                regular_source_weeks = _season_source_weeks(db, cfbd, season, season_type="regular")
                postseason_source_weeks = _postseason_source_weeks(db, cfbd, season)
                source_weeks = regular_source_weeks + postseason_source_weeks
                target_week = max(source_weeks) if source_weeks else 0
            if target_week <= 0:
                print(f"Skipping season {season}: no local or CFBD competition week could be determined yet.", flush=True)
                continue

            print(f"[player-context] season {season}: target week {target_week}", flush=True)
            if not args.skip_preseason:
                existing_roster_rows = db.query_one(
                    """
                    select count(*) as row_count
                    from roster_entries
                    where season_year = %(season)s
                    """,
                    {"season": season},
                ) or {}
                if not args.force and int(existing_roster_rows.get("row_count") or 0) > 0:
                    print(
                        f"[player-context] season {season}: roster context already exists; skipping preseason refresh",
                        flush=True,
                    )
                else:
                    season_team_level = args.classification.upper()
                    season_teams = _season_team_names_for_level(db, season, season_team_level)
                    print(
                        (
                            f"[player-context] season {season}: refreshing preseason roster/recruiting/transfer "
                            f"context for {len(season_teams)} {season_team_level} teams..."
                        ),
                        flush=True,
                    )
                    ingest_cfbd_preseason(
                        repository=repository,
                        db=db,
                        client=cfbd,
                        season=season,
                        teams=season_teams,
                        classification=None,
                    )

            season_summary = runner.backfill_player_context(
                season=season,
                through_week=target_week,
                cfbd_client=cfbd,
                include_rankings=not args.skip_rankings,
                include_usage=not args.skip_usage,
                include_value_metrics=not args.skip_value_metrics,
                skip_if_present=not args.force,
            )
            total_summary["seasons"] += 1
            total_summary["rankings"] += int(season_summary["rankings"])
            total_summary["season_stats"] += int(season_summary["season_stats"])
            total_summary["usage"] += int(season_summary["usage"])
            total_summary["value_metrics"] += int(season_summary["value_metrics"])

        print(
            (
                "[player-context] historical refresh complete: "
                f"{total_summary['seasons']} seasons, "
                f"+{total_summary['rankings']} official ranking rows, "
                f"+{total_summary['season_stats']} player season stat rows, "
                f"+{total_summary['usage']} usage rows, "
                f"+{total_summary['value_metrics']} value metric rows."
            ),
            flush=True,
        )
        return

    if args.command == "backfill-game-player-stats":
        if not config.cfbd_api_key:
            raise RuntimeError("Missing required environment variable for this command: CFBD_API_KEY")
        if args.end_season < args.start_season:
            raise RuntimeError("--end-season must be greater than or equal to --start-season")
        if args.max_weeks is not None and args.max_weeks <= 0:
            raise RuntimeError("--max-weeks must be greater than 0 when provided")
        _ensure_cfbd_connectivity_or_exit(
            config=config,
            season=args.start_season,
            label="game-player-stat backfill",
            skip_check=args.skip_connectivity_check or args.dry_run,
        )

        from cfb_rankings.clients.cfbd import CfbdClient
        from cfb_rankings.ingest.cfbd import ingest_cfbd_week

        db.apply_sql_file(schema_path)
        apply_runtime_migrations(db)
        repository.seed_levels()
        cfbd = CfbdClient(config.cfbd_api_key, config.cfbd_base_url, config.request_timeout_seconds)
        game_player_stat_classifications = list(args.classification or ["fbs"])
        print(
            "[game-player-stats] "
            f"target classifications: {', '.join(classification.upper() for classification in game_player_stat_classifications)}",
            flush=True,
        )
        if args.dry_run:
            print("[game-player-stats] dry run enabled: no CFBD requests will be made.", flush=True)
        remaining_weeks = args.max_weeks

        for season in range(args.start_season, args.end_season + 1):
            if args.missing_only:
                regular_weeks = _missing_player_game_stat_source_weeks(db, season, season_type="regular")
                if regular_weeks:
                    print(
                        f"[game-player-stats] season {season}: targeting {len(regular_weeks)} regular source weeks with missing FBS player stats.",
                        flush=True,
                    )
                else:
                    print(
                        f"[game-player-stats] season {season}: no regular weeks with missing FBS player stats detected locally.",
                        flush=True,
                    )
            else:
                regular_weeks = _season_source_weeks(db, cfbd, season, season_type="regular")
            regular_weeks = _apply_week_cap(regular_weeks, remaining_weeks)
            if not regular_weeks and not args.include_postseason:
                print(f"[game-player-stats] season {season}: no regular weeks available; skipping", flush=True)
                continue
            for week in regular_weeks:
                if args.missing_only and not _has_local_games_for_source_week(
                    db,
                    season=season,
                    season_type="regular",
                    source_week=week,
                ):
                    print(
                        f"[game-player-stats] season {season}: skipping regular source week {week} because no local game shell exists yet.",
                        flush=True,
                    )
                    continue
                if args.dry_run:
                    print(f"[game-player-stats] season {season}: would ingest regular source week {week}.", flush=True)
                    remaining_weeks = _decrement_remaining_week_budget(remaining_weeks)
                    if _week_budget_exhausted(remaining_weeks):
                        print("[game-player-stats] week cap reached during dry run.", flush=True)
                        return
                    continue
                print(f"[game-player-stats] season {season}: ingesting regular source week {week}...", flush=True)
                ingest_cfbd_week(
                    repository=repository,
                    db=db,
                    client=cfbd,
                    season=season,
                    week=week,
                    season_type="regular",
                    include_lines=False,
                    include_weather=False,
                    include_advanced_game_stats=False,
                    include_drives=False,
                    include_plays=False,
                    include_game_player_stats=True,
                    game_player_stat_classifications=game_player_stat_classifications,
                )
                remaining_weeks = _decrement_remaining_week_budget(remaining_weeks)
                if _week_budget_exhausted(remaining_weeks):
                    print("[game-player-stats] week cap reached; stopping after the current batch.", flush=True)
                    return
            if args.include_postseason:
                if args.missing_only:
                    postseason_weeks = _missing_player_game_stat_source_weeks(db, season, season_type="postseason")
                    if postseason_weeks:
                        print(
                            f"[game-player-stats] season {season}: targeting {len(postseason_weeks)} postseason source weeks with missing FBS player stats.",
                            flush=True,
                        )
                    else:
                        print(
                            f"[game-player-stats] season {season}: no postseason weeks with missing FBS player stats detected locally.",
                            flush=True,
                        )
                else:
                    postseason_weeks = _postseason_source_weeks(db, cfbd, season)
                postseason_weeks = _apply_week_cap(postseason_weeks, remaining_weeks)
                for week in postseason_weeks:
                    if args.missing_only and not _has_local_games_for_source_week(
                        db,
                        season=season,
                        season_type="postseason",
                        source_week=week,
                    ):
                        print(
                            f"[game-player-stats] season {season}: skipping postseason source week {week} because no local game shell exists yet.",
                            flush=True,
                        )
                        continue
                    if args.dry_run:
                        print(f"[game-player-stats] season {season}: would ingest postseason source week {week}.", flush=True)
                        remaining_weeks = _decrement_remaining_week_budget(remaining_weeks)
                        if _week_budget_exhausted(remaining_weeks):
                            print("[game-player-stats] week cap reached during dry run.", flush=True)
                            return
                        continue
                    print(f"[game-player-stats] season {season}: ingesting postseason source week {week}...", flush=True)
                    ingest_cfbd_week(
                        repository=repository,
                        db=db,
                        client=cfbd,
                        season=season,
                        week=week,
                        season_type="postseason",
                        include_lines=False,
                        include_weather=False,
                        include_advanced_game_stats=False,
                        include_drives=False,
                        include_plays=False,
                        include_game_player_stats=True,
                        game_player_stat_classifications=game_player_stat_classifications,
                    )
                    remaining_weeks = _decrement_remaining_week_budget(remaining_weeks)
                    if _week_budget_exhausted(remaining_weeks):
                        print("[game-player-stats] week cap reached; stopping after the current batch.", flush=True)
                        return
        if args.dry_run:
            print("[game-player-stats] dry run complete.", flush=True)
        return

    if args.command == "audit-data-coverage":
        from cfb_rankings.audit import write_data_coverage_audit

        output_path = write_data_coverage_audit(db=db, output_path=args.output)
        print(output_path, flush=True)
        return

    if args.command == "audit-player-archive":
        from cfb_rankings.audit import write_player_archive_audit

        output_path = write_player_archive_audit(db=db, output_path=args.output)
        print(output_path, flush=True)
        return

    if args.command == "audit-awards-archive":
        from cfb_rankings.audit import write_awards_archive_audit

        output_path = write_awards_archive_audit(db=db, output_path=args.output)
        print(output_path, flush=True)
        return

    if args.command == "audit-archive-readiness":
        from cfb_rankings.audit import write_archive_readiness_audit

        output_path = write_archive_readiness_audit(db=db, output_path=args.output)
        print(output_path, flush=True)
        return

    if args.command == "check-cfbd-connectivity":
        from cfb_rankings.operations import check_cfbd_connectivity

        result = check_cfbd_connectivity(config=config, season=args.season)
        status = "OK" if result["ok"] else "FAILED"
        print(f"CFBD connectivity: {status}", flush=True)
        print(result["message"], flush=True)
        if "payload_count" in result:
            print(f"Payload count: {int(result['payload_count'])}", flush=True)
        if not result["ok"]:
            raise SystemExit(2)
        return

    if args.command == "history-load-status":
        from cfb_rankings.operations import write_history_load_status

        output_path = write_history_load_status(
            db=db,
            output_path=args.output,
            start_season=args.start_season,
            end_season=args.end_season,
        )
        print(output_path, flush=True)
        return

    if args.command == "refresh-local-health":
        from cfb_rankings.operations import refresh_local_health_artifacts

        output_path = refresh_local_health_artifacts(
            db=db,
            start_season=args.start_season,
            end_season=args.end_season,
            site_dir=args.site_dir,
            output_path=args.output,
            skip_link_audit=args.skip_link_audit,
            verbose=True,
        )
        print(output_path, flush=True)
        return

    if args.command == "validate-maintenance":
        from cfb_rankings.operations import validate_maintenance_outputs

        result = validate_maintenance_outputs(
            output_path=args.output,
            local_health_path=args.local_health,
            bundle_path=args.bundle,
            queue_path=args.queue,
            allow_p0=args.allow_p0,
        )
        print(result["markdownPath"], flush=True)
        print(f"Maintenance validation: {result['status']}", flush=True)
        if not result["ok"]:
            raise SystemExit(2)
        return

    if args.command == "audit-competition-integrity":
        from cfb_rankings.integrity import write_competition_integrity_audit

        output_path = write_competition_integrity_audit(db=db, output_path=args.output)
        print(output_path, flush=True)
        return

    if args.command == "audit-program-history":
        from cfb_rankings.integrity import write_program_history_integrity_audit

        output_path = write_program_history_integrity_audit(db=db, output_path=args.output)
        print(output_path, flush=True)
        return

    if args.command == "repair-team-current-identity":
        repaired = repository.repair_team_current_identity_from_latest_season()
        print(f"Repaired {repaired} team current identity rows.", flush=True)
        return

    if args.command == "sync-site":
        if not config.cfbd_api_key:
            raise RuntimeError("Missing required environment variable for this command: CFBD_API_KEY")
        season_for_check = args.season or _default_season(db)
        _ensure_cfbd_connectivity_or_exit(
            config=config,
            season=season_for_check,
            label="site sync",
            skip_check=args.skip_connectivity_check,
        )

        from cfb_rankings.clients.cfbd import CfbdClient
        from cfb_rankings.ingest.cfbd import ingest_cfbd_week
        from cfb_rankings.pipeline import run_weekly_models

        db.apply_sql_file(schema_path)
        apply_runtime_migrations(db)
        repository.seed_levels()

        cfbd = CfbdClient(config.cfbd_api_key, config.cfbd_base_url, config.request_timeout_seconds)
        season = season_for_check
        through_week = args.through_week or _default_through_week(db, cfbd, season, args.season_type)
        source_weeks = [week for week in _season_source_weeks(db, cfbd, season, args.season_type) if week <= through_week]

        if through_week < 1:
            raise RuntimeError(f"Could not determine a valid week for season {season}.")
        if args.season_type == "regular" and source_weeks:
            max_source_week = max(source_weeks)
            if through_week > max_source_week:
                print(
                    f"Requested regular through-week {through_week}, but CFBD only reports regular source weeks through {max_source_week}. "
                    "Postseason weeks will still be synced separately.",
                    flush=True,
                )

        print(f"Syncing season {season} through week {through_week}...", flush=True)
        for week in source_weeks:
            print(f"Ingesting CFBD week {week}...", flush=True)
            ingest_cfbd_week(
                repository=repository,
                db=db,
                client=cfbd,
                season=season,
                week=week,
                season_type=args.season_type,
                include_drives=not args.skip_play_level,
                include_plays=not args.skip_play_level,
            )
        _sync_postseason_weeks(
            repository=repository,
            db=db,
            cfbd=cfbd,
            season=season,
            include_drives=not args.skip_play_level,
            include_plays=not args.skip_play_level,
        )

        print(f"Running {_model_run_label(include_heisman=not args.skip_heisman)}...", flush=True)
        run_weekly_models(
            db=db,
            model_version=config.model_version,
            season=season,
            through_week=_max_competition_week(db, season),
            cfbd_client=cfbd,
            include_heisman=not args.skip_heisman,
        )

        _publish_outputs(
            db=db,
            output_path=args.output,
            site_output_dir=args.site_output_dir,
            limit=args.limit,
            open_report=args.open_report,
        )
        return

    if args.command == "sync-site-incremental":
        if not config.cfbd_api_key:
            raise RuntimeError("Missing required environment variable for this command: CFBD_API_KEY")
        season_for_check = args.season or _default_season(db)
        _ensure_cfbd_connectivity_or_exit(
            config=config,
            season=season_for_check,
            label="incremental site sync",
            skip_check=args.skip_connectivity_check,
        )

        from cfb_rankings.clients.cfbd import CfbdClient
        from cfb_rankings.ingest.cfbd import ingest_cfbd_week
        from cfb_rankings.pipeline import run_weekly_models

        db.apply_sql_file(schema_path)
        apply_runtime_migrations(db)
        repository.seed_levels()

        cfbd = CfbdClient(config.cfbd_api_key, config.cfbd_base_url, config.request_timeout_seconds)
        season = season_for_check
        through_week = args.through_week or _default_through_week(db, cfbd, season, args.season_type)
        latest_local_week = _latest_local_week(db, season, args.season_type)
        source_weeks = [week for week in _season_source_weeks(db, cfbd, season, args.season_type) if week <= through_week]

        if through_week < 1:
            raise RuntimeError(f"Could not determine a valid week for season {season}.")
        if args.season_type == "regular" and source_weeks:
            max_source_week = max(source_weeks)
            if through_week > max_source_week:
                print(
                    f"Requested regular through-week {through_week}, but CFBD only reports regular source weeks through {max_source_week}. "
                    "Postseason weeks will still be synced separately.",
                    flush=True,
                )

        missing_weeks = [week for week in source_weeks if week > latest_local_week]
        if not missing_weeks:
            print(
                f"No missing weeks to ingest for season {season}. Local data is already through week {latest_local_week}.",
                flush=True,
            )
        else:
            print(
                f"Incremental sync for season {season}: local week {latest_local_week}, target week {through_week}.",
                flush=True,
            )
            for week in missing_weeks:
                print(f"Ingesting CFBD week {week}...", flush=True)
                ingest_cfbd_week(
                    repository=repository,
                    db=db,
                    client=cfbd,
                    season=season,
                    week=week,
                    season_type=args.season_type,
                    include_drives=not args.skip_play_level,
                    include_plays=not args.skip_play_level,
                )

        _sync_postseason_weeks(
            repository=repository,
            db=db,
            cfbd=cfbd,
            season=season,
            include_drives=not args.skip_play_level,
            include_plays=not args.skip_play_level,
        )
        model_week = max(_max_competition_week(db, season), through_week)
        latest_model_summary = _latest_model_summary(db, season)
        can_reuse_existing_model = (
            not args.force_models
            and not missing_weeks
            and latest_model_summary is not None
            and int(latest_model_summary["week"]) >= model_week
            and str(latest_model_summary.get("model_version") or "") == config.model_version
        )

        if can_reuse_existing_model:
            print(
                f"Skipping model rerun: existing {config.model_version} snapshot already covers season {season} through week {int(latest_model_summary['week'])}.",
                flush=True,
            )
        else:
            print(
                f"Running {_model_run_label(include_heisman=not args.skip_heisman)} through week {model_week}...",
                flush=True,
            )
            run_weekly_models(
                db=db,
                model_version=config.model_version,
                season=season,
                through_week=model_week,
                cfbd_client=cfbd,
                include_heisman=not args.skip_heisman,
            )

        _publish_outputs(
            db=db,
            output_path=args.output,
            site_output_dir=args.site_output_dir,
            limit=args.limit,
            open_report=args.open_report,
        )
        return

    if args.command == "backfill-cfbd-history":
        if not config.cfbd_api_key:
            raise RuntimeError("Missing required environment variable for this command: CFBD_API_KEY")
        if args.end_season < args.start_season:
            raise RuntimeError("--end-season must be greater than or equal to --start-season")
        _ensure_cfbd_connectivity_or_exit(
            config=config,
            season=args.start_season,
            label="historical CFBD backfill",
            skip_check=args.skip_connectivity_check,
        )

        from cfb_rankings.clients.cfbd import CfbdClient
        from cfb_rankings.ingest.cfbd import ingest_cfbd_week
        from cfb_rankings.pipeline import run_weekly_models
        from cfb_rankings.reporting import build_static_site, write_latest_rankings_report

        db.apply_sql_file(schema_path)
        apply_runtime_migrations(db)
        repository.seed_levels()

        cfbd = CfbdClient(config.cfbd_api_key, config.cfbd_base_url, config.request_timeout_seconds)

        for season in range(args.start_season, args.end_season + 1):
            regular_weeks = _season_source_weeks(db, cfbd, season, season_type="regular")
            if not regular_weeks:
                print(f"No regular-season weeks available for season {season}.", flush=True)
                continue

            print(
                f"Backfilling season {season}: {len(regular_weeks)} regular-season source weeks detected.",
                flush=True,
            )
            for week in regular_weeks:
                print(f"Ingesting {season} regular source week {week}...", flush=True)
                ingest_cfbd_week(
                    repository=repository,
                    db=db,
                    client=cfbd,
                    season=season,
                    week=week,
                    season_type="regular",
                    include_drives=not args.skip_play_level,
                    include_plays=not args.skip_play_level,
                )

            if args.include_postseason:
                _sync_postseason_weeks(
                    repository=repository,
                    db=db,
                    cfbd=cfbd,
                    season=season,
                    include_drives=not args.skip_play_level,
                    include_plays=not args.skip_play_level,
                )

            if args.run_models:
                through_week = _max_competition_week(db, season)
                print(
                    f"Running {_model_run_label(include_heisman=not args.skip_heisman)} for season {season} through week {through_week}...",
                    flush=True,
                )
                run_weekly_models(
                    db=db,
                    model_version=config.model_version,
                    season=season,
                    through_week=through_week,
                    cfbd_client=cfbd,
                    include_heisman=not args.skip_heisman,
                )

        if args.build_site:
            _publish_outputs(
                db=db,
                output_path="output/rankings.html",
                site_output_dir="output/site",
                limit=100,
            )
        return

    if args.command == "build-rankings-report":
        from cfb_rankings.reporting import write_latest_rankings_report

        output_path = write_latest_rankings_report(db=db, output_path=args.output, limit=args.limit)
        print(output_path)
        return

    if args.command == "build-site":
        from cfb_rankings.reporting import build_static_site
        from cfb_rankings.retro_render import build_retro_pages

        output_path = build_static_site(db=db, output_dir=args.output_dir)
        build_retro_pages(db, output_dir=args.output_dir)
        print(output_path)
        return

    if args.command == "audit-links":
        import sys
        from cfb_rankings.reporting import audit_site_links

        broken = audit_site_links(site_dir=args.site_dir)
        if broken:
            print(f"Found {len(broken)} broken internal link(s):")
            for item in broken[:50]:
                print(f"  {item['file']} -> {item['href']}  ({item['reason']})")
            if len(broken) > 50:
                print(f"  ... and {len(broken) - 50} more")
            if args.strict:
                sys.exit(1)
        else:
            print("No broken internal links found.")
        return

    if args.command == "build-published":
        _publish_outputs(
            db=db,
            output_path=args.output,
            site_output_dir=args.site_output_dir,
            limit=args.limit,
            open_report=args.open_report,
        )
        return

    if args.command == "seed-archetypes":
        from cfb_rankings.ingest.archetypes import seed_taxonomy
        from cfb_rankings.ingest.hub_data import seed_issue_metadata

        primary_count, modifier_count = seed_taxonomy(db)
        print(f"Seeded {primary_count} primary archetypes and {modifier_count} modifiers.", flush=True)
        if args.seed_issue:
            seed_issue_metadata(db)
            print("Seeded Issue N\u00b0 047 metadata into hub_issue_metadata.", flush=True)
        return

    if args.command == "classify-fanbases":
        from cfb_rankings.ingest.archetypes import classify_all_fanbases

        total = classify_all_fanbases(db, season_year=args.season, classifier_version=args.classifier_version)
        print(f"Classified {total} fanbases for season {args.season}.", flush=True)
        if args.backfill_history > 0:
            for offset in range(1, args.backfill_history + 1):
                backfill_season = args.season - offset
                backfill_total = classify_all_fanbases(
                    db,
                    season_year=backfill_season,
                    classifier_version=f"{args.classifier_version}-hist",
                )
                print(f"  Backfilled {backfill_total} history rows for season {backfill_season}.", flush=True)
        return

    if args.command == "compute-mood-week":
        from cfb_rankings.ingest.hub_data import seed_mood_week

        if args.from_features or args.no_from_seed:
            from cfb_rankings.ingest.hub_data_compute import compute_mood_week_from_features

            count = compute_mood_week_from_features(db, week_start=args.week)
            print(f"Computed {count} mood rows for week {args.week} from conversation features.", flush=True)
        elif args.from_seed:
            count = seed_mood_week(db, week_start=args.week)
            print(f"Loaded {count} mood rows for week {args.week} from seed.", flush=True)
        else:
            count = seed_mood_week(db, week_start=args.week)
            print(f"Loaded {count} mood rows for week {args.week} (offseason: seed).", flush=True)
        return

    if args.command == "compute-rivalry-ratios":
        from cfb_rankings.ingest.hub_data import seed_rivalry_week

        if args.from_features or args.no_from_seed:
            from cfb_rankings.ingest.hub_data_compute import compute_rivalry_ratios_from_features

            count = compute_rivalry_ratios_from_features(db, week_start=args.week)
            print(f"Computed {count} rivalry rows for week {args.week} from pair mentions.", flush=True)
        else:
            count = seed_rivalry_week(db, week_start=args.week)
            print(f"Loaded {count} rivalry rows for week {args.week}.", flush=True)
        return

    if args.command == "mine-lexicon":
        from cfb_rankings.ingest.hub_data import seed_lexicon_week

        if args.from_features or args.no_from_seed:
            from cfb_rankings.ingest.hub_data_compute import compute_lexicon_spikes_from_features

            count = compute_lexicon_spikes_from_features(db, week_start=args.week)
            print(f"Computed {count} lexicon rows for week {args.week} from phrase features.", flush=True)
        else:
            count = seed_lexicon_week(db, week_start=args.week)
            print(f"Loaded {count} lexicon rows for week {args.week}.", flush=True)
        return

    if args.command == "seed-retro-issue":
        from cfb_rankings.ingest.hub_data_retro import seed_retro_issue

        result = seed_retro_issue(db, args.issue)
        print(
            f"Seeded retro issue {args.issue}: "
            f"{result.get('reverted', 0)} reverted, "
            f"{result['metadata']} metadata, {result['mood']} mood, "
            f"{result['rivalry']} rivalry, {result['lexicon']} lexicon rows.",
            flush=True,
        )
        return

    if args.command == "seed-retro-all":
        from cfb_rankings.ingest.hub_data_retro import seed_retro_all

        result = seed_retro_all(db)
        total_mood = sum(row["mood"] for row in result.values())
        total_rivalry = sum(row["rivalry"] for row in result.values())
        total_lexicon = sum(row["lexicon"] for row in result.values())
        print(
            f"Seeded {len(result)} retro issues: "
            f"{total_mood} mood, {total_rivalry} rivalry, {total_lexicon} lexicon rows.",
            flush=True,
        )
        return

    if args.command == "build-retro-pages":
        from cfb_rankings.retro_render import build_retro_pages

        paths = build_retro_pages(db, output_dir=args.output_dir, bust_cache=args.bust_cache)
        print(f"Rendered {len(paths)} retro artifacts under {args.output_dir}.", flush=True)
        return

    if args.command == "retro-calibrate":
        from cfb_rankings.ingest.hub_data_compute import retro_calibrate

        results = retro_calibrate(db, window=args.window)
        failed = False
        for row in results:
            status = row["status"]
            print(
                f"{status}: {row['check']} observed={row['observed']} expected={row['expected']}",
                flush=True,
            )
            failed = failed or status == "FAIL"
        if failed:
            raise SystemExit(1)
        return

    if args.command == "seed-hub-issue":
        from cfb_rankings.ingest.archetypes import seed_taxonomy, classify_all_fanbases
        from cfb_rankings.ingest.hub_data import (
            seed_issue_metadata, seed_mood_week, seed_rivalry_week, seed_lexicon_week,
        )

        p, m = seed_taxonomy(db)
        print(f"Taxonomy: {p} primary, {m} modifiers.", flush=True)
        seed_issue_metadata(db)
        print("Hub issue metadata loaded.", flush=True)
        total = classify_all_fanbases(db, season_year=args.season)
        print(f"Classified {total} fanbases for season {args.season}.", flush=True)
        # Also backfill 5 prior season history rows so the migration sparkline has data
        for offset in range(1, 6):
            backfill_season = args.season - offset
            backfill_total = classify_all_fanbases(
                db, season_year=backfill_season, classifier_version=f"v1.0-hist-{backfill_season}",
            )
            print(f"  History {backfill_season}: {backfill_total} rows.", flush=True)
        mood = seed_mood_week(db, week_start=args.week)
        rivalry = seed_rivalry_week(db, week_start=args.week)
        lexicon = seed_lexicon_week(db, week_start=args.week)
        print(f"Weekly: {mood} mood, {rivalry} rivalry, {lexicon} lexicon rows.", flush=True)
        return

    if args.command == "sync-team-brand-assets":
        if not config.cfbd_api_key:
            raise RuntimeError("Missing required environment variable for this command: CFBD_API_KEY")
        from cfb_rankings.clients.cfbd import CfbdClient
        from cfb_rankings.ingest.team_brand import sync_team_brand_assets

        cfbd = CfbdClient(config.cfbd_api_key, config.cfbd_base_url, config.request_timeout_seconds)
        sync_team_brand_assets(
            repository=repository,
            db=db,
            client=cfbd,
            year=args.year,
            classification=args.classification,
            refresh_assets=args.refresh_assets,
            site_root=Path("output/site"),
        )
        return

    raise RuntimeError(f"Unsupported command: {args.command}")


def _ensure_cfbd_connectivity_or_exit(
    *,
    config: "AppConfig",
    season: int,
    label: str,
    skip_check: bool = False,
) -> None:
    if skip_check:
        print(f"Skipping CFBD connectivity preflight for {label}.", flush=True)
        return

    from cfb_rankings.operations import check_cfbd_connectivity

    print(f"Running CFBD connectivity preflight for {label}...", flush=True)
    result = check_cfbd_connectivity(config=config, season=season)
    if result.get("ok"):
        print(result.get("message") or "CFBD connectivity check succeeded.", flush=True)
        return

    print(result.get("message") or "CFBD connectivity check failed.", flush=True)
    raise SystemExit(2)


def _apply_week_cap(weeks: list[int], remaining_weeks: int | None) -> list[int]:
    if remaining_weeks is None:
        return weeks
    if remaining_weeks <= 0:
        return []
    return weeks[:remaining_weeks]


def _load_reddit_collection_plan(path: str) -> list[dict[str, object]]:
    plan_path = Path(path)
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    entries = payload.get("sources") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        raise RuntimeError(f"Reddit collection plan must be a JSON list or an object with a 'sources' list: {plan_path}")
    normalized_entries: list[dict[str, object]] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise RuntimeError(f"Reddit collection plan entry {index} must be an object.")
        normalized_entries.append(entry)
    if not normalized_entries:
        raise RuntimeError(f"Reddit collection plan is empty: {plan_path}")
    return normalized_entries


def _coerce_plan_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, list):
        results: list[str] = []
        for item in value:
            cleaned = str(item or "").strip()
            if cleaned:
                results.append(cleaned)
        return results
    raise RuntimeError(f"Expected a string or list of strings in Reddit collection plan, got: {type(value).__name__}")


def _coerce_plan_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise RuntimeError(f"Could not interpret Reddit collection plan boolean value: {value}")


def _coerce_epoch_bound(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    return _date_bound_to_epoch(_parse_iso_date(text))


def _parse_iso_date(value: str) -> date:
    return date.fromisoformat(value.strip()[:10])


def _date_bound_to_epoch(value: date) -> int:
    eastern = ZoneInfo("America/New_York")
    localized = datetime.combine(value, time.min, tzinfo=eastern)
    return int(localized.astimezone(timezone.utc).timestamp())


def _iter_date_windows(start: date, end_exclusive: date, days_per_window: int) -> list[tuple[date, date]]:
    step = max(int(days_per_window), 1)
    windows: list[tuple[date, date]] = []
    cursor = start
    while cursor < end_exclusive:
        next_cursor = min(cursor + timedelta(days=step), end_exclusive)
        windows.append((cursor, next_cursor))
        cursor = next_cursor
    return windows


def _parse_week_window(window: str) -> tuple[int, int]:
    text = (window or "").strip()
    if ".." in text:
        left, right = text.split("..", 1)
        return int(left), int(right)
    value = int(text)
    return value, value


def _offseason_week_records(db: "Database", season: int, window: str) -> list[dict[str, object]]:
    start_week, end_week = _parse_week_window(window)
    return db.query_all(
        """
        select season_year, offseason_week, week_start_date, issue_number, issue_title, slug
        from offseason_week_map
        where season_year = %(season)s
          and offseason_week between %(start_week)s and %(end_week)s
        order by offseason_week
        """,
        {"season": season, "start_week": start_week, "end_week": end_week},
    )


def _offseason_week_end(record: dict[str, object], records: list[dict[str, object]], through_date: str) -> date:
    current_week = int(record["offseason_week"])
    next_record = next((row for row in records if int(row["offseason_week"]) > current_week), None)
    start = _parse_iso_date(str(record["week_start_date"]))
    if next_record:
        return _parse_iso_date(str(next_record["week_start_date"]))
    through = _parse_iso_date(through_date) + timedelta(days=1)
    return max(start + timedelta(days=1), min(start + timedelta(days=7), through))


def _next_issue_week_start(week_start: str, records: list[dict[str, object]]) -> str | None:
    sorted_starts = [str(row["week_start_date"]) for row in records]
    if week_start not in sorted_starts:
        return None
    index = sorted_starts.index(week_start)
    if index + 1 >= len(sorted_starts):
        return None
    return sorted_starts[index + 1]


def _default_offseason_backfill_plan(
    db: "Database",
    *,
    week_start: str,
    fallback_week_start: str | None,
    subreddits: list[str],
    limit_per_query: int,
) -> list[dict[str, object]]:
    team_names = _mood_team_names_for_week(db, week_start)
    if not team_names and fallback_week_start:
        team_names = _mood_team_names_for_week(db, fallback_week_start)
    if not team_names:
        team_names = ["Indiana", "Miami", "Michigan", "Ohio State", "Oregon", "Nebraska", "USC", "Texas"]
    entries: list[dict[str, object]] = []
    for subreddit in subreddits:
        entries.append(
            {
                "mode": "team_search",
                "teams": team_names,
                "subreddit": subreddit,
                "audience_bucket": "national",
                "search_limit": limit_per_query,
                "replace_existing": False,
            }
        )
    return entries


def _resolve_player_identifier(db, raw: str) -> int | None:
    """Accept either a numeric player_id or a slug with trailing '-<id>'."""
    raw = (raw or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return int(raw)
    if "-" in raw:
        tail = raw.rsplit("-", 1)[-1]
        if tail.isdigit():
            return int(tail)
    rows = db.query_all(
        "select player_id from players where lower(full_name) = lower(:n)",
        {"n": raw.replace("-", " ")},
    )
    if len(rows) == 1:
        return int(rows[0]["player_id"])
    return None


def _default_player_season(db, player_id: int) -> int:
    rows = db.query_all(
        """
        select max(season_year) as y from (
          select season_year from player_value_metrics where player_id = :pid
          union all
          select season_year from player_season_stats where player_id = :pid
          union all
          select season_year from player_game_stats where player_id = :pid
        )
        """,
        {"pid": player_id},
    )
    year = rows[0].get("y") if rows else None
    return int(year or 2025)


def _print_player_mood(db, profile, player_id, season, week):
    rows = db.query_all(
        "select full_name, position from players where player_id = :pid",
        {"pid": player_id},
    )
    if rows:
        header = f"{rows[0]['full_name']} ({rows[0]['position']})  player_id={player_id}  season={season}  week={week}"
    else:
        header = f"player_id={player_id}  season={season}  week={week}"
    print(header)
    print("-" * len(header))
    if not profile["has_data"]:
        print("[no signal yet]")
        print(f"  sample: {profile['sample']['mentions']} mentions / {profile['sample']['authors']} authors")
        print(f"  confidence: {profile['confidence']['label']}")
        narrative = (profile.get("belief") or {}).get("narrative") or ""
        if narrative:
            print(f"  narrative: {narrative}")
        return
    s = profile["sample"]
    b = profile["belief"] or {}
    c = profile["confidence"]
    print(f"Archetype: {profile.get('archetype') or '--'}")
    print(f"Belief:    score={b.get('score')}  label={b.get('label') or '--'}")
    print(f"Narrative: {b.get('narrative') or ''}")
    print(f"Confidence: {c.get('label')} (score={c.get('score')}, sarcasm={c.get('sarcasm_risk')})")
    print(f"Sample:")
    print(f"  own fans   : {s.get('mentions')}")
    print(f"  rivals     : {s.get('rival_mentions')}")
    print(f"  national   : {s.get('national_mentions')}")
    print(f"  media      : {s.get('media_mentions')}")
    for axis in ("respect_gap", "swing", "cohesion"):
        ax = profile.get(axis) or {}
        print(f"  {axis:12s}: {ax.get('label') or '--'}")
    tq = profile.get("top_quote")
    if tq:
        print()
        print(f'Top quote ({tq.get("bucket") or "?"}): "{tq.get("text")}"  — {tq.get("author_pseudonym") or "fan"}')


def _print_signature_story(db, story, player_id, season, week, build_scoreboard_fn):
    rows = db.query_all(
        "select full_name, position from players where player_id = :pid",
        {"pid": player_id},
    )
    if rows:
        name = rows[0]["full_name"]
        position = rows[0]["position"]
        header = f"{name} ({position})  player_id={player_id}  season={season}"
    else:
        header = f"player_id={player_id}  season={season}"
    if week is not None:
        header += f"  through week {week}"
    print(header)
    print("-" * len(header))
    if not story["has_story"]:
        print(f"[no story] {story['narrative']}")
        print(f"confidence: {story['confidence']['label']}")
        return
    hs = story["headline_stat"]
    print(f"Winner: {hs['metric_id']}")
    print(f"  label         : {hs['label']}")
    print(f"  value         : {hs['value']}  ({hs['unit']})")
    print(f"  rank          : {hs['rank']} of {hs['cohort_size']} — {hs['rank_cohort']}")
    print(f"  percentile    : {hs['percentile']}")
    print(f"  sample_size   : {hs['sample_size']}")
    print(f"  confidence    : {story['confidence']['label']}  (score={story['confidence']['score']})")
    print()
    print("Narrative:")
    print(f"  {story['narrative']}")
    print()
    print("Scoreboard (every qualifying metric, ordered by score):")
    scoreboard = build_scoreboard_fn(db, player_id, season, week)
    print(f"  {'metric':<32} {'rank':>8} {'pct':>6} {'n':>6} {'wt':>5} {'score':>8}")
    for e in scoreboard:
        rank_str = f"{e.rank}/{e.cohort_size}"
        print(f"  {e.metric.id:<32} {rank_str:>8} {e.percentile:>6.1f} "
              f"{int(e.sample_size):>6} {e.metric.narrative_weight:>5.2f} {e.score:>8.3f}")


def _mood_team_names_for_week(db: "Database", week_start: str) -> list[str]:
    rows = db.query_all(
        """
        select distinct t.canonical_name
        from fanbase_mood_weekly fmw
        join teams t on t.team_id = fmw.team_id
        where fmw.week_start_date = %(week_start)s
        order by t.canonical_name
        """,
        {"week_start": week_start},
    )
    return [str(row["canonical_name"]) for row in rows]


def _run_reddit_plan_entry(
    *,
    repository: object,
    db: "Database",
    client: object,
    entry: dict[str, object],
    season: int,
    week: int,
    provider_name: str,
    after: int,
    before: int,
    replace_existing: bool,
    collect_reddit_watchlist: object,
    collect_reddit_subreddit_listing: object,
) -> dict[str, object]:
    mode = str(entry.get("mode") or "team_search").strip().lower()
    audience_bucket = str(entry.get("audience_bucket") or "national").strip().lower()
    subreddit = str(entry.get("subreddit") or "").strip()
    if mode == "team_search":
        team_names = _coerce_plan_string_list(entry.get("teams") if "teams" in entry else entry.get("team"))
        return collect_reddit_watchlist(
            repository=repository,
            db=db,
            client=client,
            season=season,
            week=week,
            team_names=team_names,
            limit_teams=int(entry.get("limit_teams") or 25),
            subreddit=subreddit or None,
            audience_bucket=audience_bucket,
            search_limit=int(entry.get("search_limit") or entry.get("limit") or 100),
            require_cfb_context=_coerce_plan_bool(entry.get("require_cfb_context"), default=True),
            after=after,
            before=before,
            provider_name=provider_name,
            replace_existing=replace_existing,
        )
    if mode == "subreddit_listing":
        team_name = str(entry.get("team") or "").strip()
        if not team_name:
            raise RuntimeError("subreddit_listing plan entry is missing required field 'team'.")
        return collect_reddit_subreddit_listing(
            repository=repository,
            db=db,
            client=client,
            season=season,
            week=week,
            target_team_name=team_name,
            subreddit=subreddit,
            audience_bucket=audience_bucket,
            listing=str(entry.get("listing") or "new").strip().lower(),
            limit=int(entry.get("limit") or 100),
            require_cfb_context=_coerce_plan_bool(entry.get("require_cfb_context"), default=True),
            after=after,
            before=before,
            provider_name=provider_name,
            replace_existing=replace_existing,
        )
    raise RuntimeError(f"Unsupported Reddit collection plan mode '{mode}'.")


def _decrement_remaining_week_budget(remaining_weeks: int | None) -> int | None:
    if remaining_weeks is None:
        return None
    return max(remaining_weeks - 1, 0)


def _week_budget_exhausted(remaining_weeks: int | None) -> bool:
    return remaining_weeks is not None and remaining_weeks <= 0


def _default_season(db: "Database") -> int:
    row = db.query_one("select max(season_year) as season_year from seasons")
    if row and row.get("season_year"):
        return int(row["season_year"])

    today = datetime.now()
    return today.year if today.month >= 8 else today.year - 1


def _default_through_week(db: "Database", cfbd: object, season: int, season_type: str) -> int:
    completed_week = _latest_completed_cfbd_week(cfbd, season, season_type)
    if completed_week:
        return completed_week

    row = db.query_one(
        """
        select max(week) as week
        from games
        where season_year = %(season_year)s
          and season_type = %(season_type)s
        """,
        {"season_year": season, "season_type": season_type},
    )
    if row and row.get("week"):
        return int(row["week"])
    return 1


def _latest_completed_cfbd_week(cfbd: object, season: int, season_type: str) -> int | None:
    try:
        games = cfbd.get_games(year=season, season_type=season_type)
    except Exception as exc:
        print(f"Could not auto-detect latest CFBD week: {exc}")
        return None

    completed_weeks: list[int] = []
    for game in games:
        if game.get("completed") and game.get("week") is not None:
            try:
                completed_weeks.append(int(game["week"]))
            except (TypeError, ValueError):
                continue
    return max(completed_weeks) if completed_weeks else None


def _latest_local_week(db: "Database", season: int, season_type: str) -> int:
    row = db.query_one(
        """
        select max(week) as week
        from games
        where season_year = %(season_year)s
          and season_type = %(season_type)s
        """,
        {"season_year": season, "season_type": season_type},
    )
    if row and row.get("week") is not None:
        return int(row["week"])
    return 0


def _publish_outputs(
    db: "Database",
    output_path: str,
    site_output_dir: str,
    limit: int,
    open_report: bool = False,
) -> tuple[Path, Path]:
    from cfb_rankings.reporting import build_static_site, write_latest_rankings_report

    report_output = write_latest_rankings_report(db=db, output_path=output_path, limit=limit)
    site_output = build_static_site(db=db, output_dir=site_output_dir)
    print(f"Built rankings report: {report_output}", flush=True)
    print(f"Built static site: {site_output}", flush=True)
    if open_report:
        webbrowser.open(Path(report_output).resolve().as_uri())
    return report_output, site_output


def _latest_model_summary(db: "Database", season: int) -> dict[str, int | str] | None:
    row = db.query_one(
        """
        select mr.model_run_id, mr.week, mr.model_version
        from model_runs mr
        where mr.season_year = %(season_year)s
          and exists (
            select 1
            from power_ratings_weekly p
            where p.model_run_id = mr.model_run_id
          )
        order by mr.week desc, mr.model_run_id desc
        limit 1
        """,
        {"season_year": season},
    )
    if row is None:
        return None
    return {
        "model_run_id": int(row["model_run_id"]),
        "week": int(row["week"]),
        "model_version": str(row.get("model_version") or ""),
    }


def _model_run_label(include_heisman: bool) -> str:
    return "Power, Resume, and Heisman models" if include_heisman else "Power and Resume models"


def _model_summary_for_week(db: "Database", season: int, week: int) -> dict[str, int | str] | None:
    row = db.query_one(
        """
        select mr.model_run_id, mr.week, mr.model_version
        from model_runs mr
        where mr.season_year = %(season_year)s
          and mr.week = %(week)s
          and exists (
            select 1
            from power_ratings_weekly p
            where p.model_run_id = mr.model_run_id
          )
        order by mr.model_run_id desc
        limit 1
        """,
        {"season_year": season, "week": week},
    )
    if row is None:
        return None
    return {
        "model_run_id": int(row["model_run_id"]),
        "week": int(row["week"]),
        "model_version": str(row.get("model_version") or ""),
    }


def _season_source_weeks(db: "Database", cfbd: object, season: int, season_type: str) -> list[int]:
    try:
        games = cfbd.get_games(year=season, season_type=season_type)
        weeks = sorted({int(game["week"]) for game in games if game.get("week") is not None})
        if weeks:
            return weeks
    except Exception as exc:
        print(f"Could not auto-detect {season_type} weeks for season {season}: {exc}", flush=True)

    rows = db.query_all(
        """
        select distinct coalesce(source_week, week) as source_week
        from games
        where season_year = %(season_year)s
          and season_type = %(season_type)s
          and coalesce(source_week, week) is not null
        order by source_week
        """,
        {"season_year": season, "season_type": season_type},
    )
    return [int(row["source_week"]) for row in rows]


def _postseason_source_weeks(db: "Database", cfbd: object, season: int) -> list[int]:
    try:
        games = cfbd.get_games(year=season, season_type="postseason")
        weeks = sorted({int(game["week"]) for game in games if game.get("week") is not None})
        if weeks:
            return weeks
    except Exception as exc:
        print(f"Could not auto-detect postseason weeks: {exc}", flush=True)

    rows = db.query_all(
        """
        select distinct coalesce(source_week, week) as source_week
        from games
        where season_year = %(season_year)s
          and season_type = 'postseason'
          and coalesce(source_week, week) is not null
        order by source_week
        """,
        {"season_year": season},
    )
    return [int(row["source_week"]) for row in rows]


def _missing_player_game_stat_source_weeks(db: "Database", season: int, season_type: str) -> list[int]:
    rows = db.query_all(
        """
        with completed_fbs_games as (
          select
            g.game_id,
            coalesce(g.source_week, g.week) as source_week
          from games g
          join teams ht on ht.team_id = g.home_team_id
          join teams at on at.team_id = g.away_team_id
          left join team_seasons hts
            on hts.team_id = g.home_team_id
           and hts.season_year = g.season_year
          left join team_seasons ats
            on ats.team_id = g.away_team_id
           and ats.season_year = g.season_year
          where g.season_year = %(season_year)s
            and g.season_type = %(season_type)s
            and g.home_points is not null
            and g.away_points is not null
            and coalesce(g.source_week, g.week) is not null
            and coalesce(hts.level_code, ht.level_code) = 'FBS'
            and coalesce(ats.level_code, at.level_code) = 'FBS'
        )
        select distinct cfg.source_week
        from completed_fbs_games cfg
        left join (
          select distinct game_id
          from player_game_stats
          where season_year = %(season_year)s
        ) pgs on pgs.game_id = cfg.game_id
        where pgs.game_id is null
        order by cfg.source_week
        """,
        {"season_year": season, "season_type": season_type},
    )
    return [int(row["source_week"]) for row in rows if row.get("source_week") is not None]


def _has_local_games_for_source_week(db: "Database", season: int, season_type: str, source_week: int) -> bool:
    row = db.query_one(
        """
        select 1 as found
        from games
        where season_year = %(season_year)s
          and season_type = %(season_type)s
          and coalesce(source_week, week) = %(source_week)s
        limit 1
        """,
        {"season_year": season, "season_type": season_type, "source_week": source_week},
    )
    return row is not None


def _sync_postseason_weeks(
    repository: "Repository",
    db: "Database",
    cfbd: object,
    season: int,
    include_drives: bool = True,
    include_plays: bool = True,
) -> None:
    from cfb_rankings.ingest.cfbd import ingest_cfbd_week

    postseason_weeks = _postseason_source_weeks(db, cfbd, season)
    if not postseason_weeks:
        print(f"No postseason weeks available to ingest for season {season}.", flush=True)
        return

    for source_week in postseason_weeks:
        print(f"Ingesting CFBD postseason source week {source_week}...", flush=True)
        ingest_cfbd_week(
            repository=repository,
            db=db,
            client=cfbd,
            season=season,
            week=source_week,
            season_type="postseason",
            include_drives=include_drives,
            include_plays=include_plays,
        )


def _max_competition_week(db: "Database", season: int) -> int:
    row = db.query_one(
        """
        select max(week) as week
        from games
        where season_year = %(season_year)s
        """,
        {"season_year": season},
    )
    if row and row.get("week") is not None:
        return int(row["week"])
    return 0


def _season_team_names(db: "Database", season: int) -> list[str]:
    rows = db.query_all(
        """
        select distinct t.canonical_name
        from teams t
        join games g on g.home_team_id = t.team_id or g.away_team_id = t.team_id
        where g.season_year = %(season_year)s
        order by t.canonical_name
        """,
        {"season_year": season},
    )
    return [str(row["canonical_name"]) for row in rows if row.get("canonical_name")]


def _season_team_names_for_level(db: "Database", season: int, level_code: str) -> list[str]:
    rows = db.query_all(
        """
        select distinct t.canonical_name
        from teams t
        join games g on g.home_team_id = t.team_id or g.away_team_id = t.team_id
        left join team_seasons ts
          on ts.team_id = t.team_id
         and ts.season_year = g.season_year
        where g.season_year = %(season_year)s
          and coalesce(ts.level_code, t.level_code) = %(level_code)s
        order by t.canonical_name
        """,
        {"season_year": season, "level_code": level_code},
    )
    return [str(row["canonical_name"]) for row in rows if row.get("canonical_name")]
