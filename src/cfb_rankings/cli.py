from __future__ import annotations

import argparse
import json
import os
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
    compute_story_cards_parser = subparsers.add_parser(
        "compute-story-cards",
        help=("Generate the additive LLM narrator prose for player Story Cards "
              "(tiers S + T1) and write player_story_card_cache. Non-critical, "
              "GPU-budgeted; build-site only READS the cache."),
    )
    compute_story_cards_parser.add_argument("--season", type=int, required=True)
    compute_story_cards_parser.add_argument(
        "--players", nargs="*", type=int, default=None,
        help="Optional player_id list to filter; default = all on-roster players for the season.",
    )
    compute_story_cards_parser.add_argument(
        "--tier", default=None,
        help="Optional comma-separated tier filter (e.g. 'S,T1'); default = S,T1.",
    )
    compute_story_cards_parser.add_argument(
        "--force", action="store_true",
        help="Bypass the content-hash skip and regenerate every candidate "
             "(otherwise unchanged players with cached LLM prose are skipped).",
    )
    compute_story_cards_parser.add_argument(
        "--limit", type=int, default=None,
        help="Cap the number of cards generated this run (the nightly GPU "
             "budget). Content-hash skips already-cached players, so successive "
             "runs fill in the S/T1 cohort over several nights.",
    )
    compute_story_cards_parser.add_argument(
        "--select", default=None, choices=["sweep", "hot-list"],
        help="Cadence cohort mode (doc 59 §11). Default = full cohort (today's "
             "behavior). 'sweep' = the full cohort, explicit (the Sunday/full "
             "beat). 'hot-list' = only the players whose mention_count or packet "
             "evidence fingerprint moved most since the last run (the cheap "
             "mid-week beat). Applied before --limit.",
    )
    eval_cards_parser = subparsers.add_parser(
        "eval-story-cards",
        help=("DEV/EVAL quality tool (doc 59 §10/§14.7): run the Missed-Gold "
              "critic + the deterministic Faithfulness gate over a sample of "
              "player Story Cards and print a quality report. Read-only on prod "
              "data; NOT in the build path; no DB/site writes."),
    )
    eval_cards_parser.add_argument(
        "--season", type=int, default=None,
        help="Stats season (last completed). Default = latest ranked season.",
    )
    eval_cards_parser.add_argument(
        "--players", nargs="*", type=int, default=None,
        help="Explicit player_id list to evaluate; default = the top-N "
             "most-talked-about (the §8 golden set selector).",
    )
    eval_cards_parser.add_argument(
        "--top-n", type=int, default=12,
        help="When --players is omitted, evaluate the top-N most-talked-about "
             "players (default 12).",
    )
    eval_cards_parser.add_argument(
        "--judge", default="mistral", choices=["mistral", "sonnet", "heuristic"],
        help="Missed-Gold judge backend. 'mistral' = local Ollama ($0, default); "
             "'sonnet' = Anthropic API (claude-sonnet-4-6); 'heuristic' = no LLM "
             "(deterministic salience pick). mistral/sonnet fall back to the "
             "heuristic if the backend is unavailable.",
    )
    eval_cards_parser.add_argument(
        "--upcoming-season", type=int, default=2026,
        help="The previewed season for the packet season-clock (default 2026).",
    )
    eval_cards_parser.add_argument(
        "--json", dest="emit_json", action="store_true",
        help="Emit the full machine report as JSON instead of the human report.",
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
    subparsers.add_parser(
        "autopilot-status",
        help="One-screen dashboard of the Autopilot v1 pipeline: source/tier counts, "
             "scrape_health last 7 days, row-count deltas for the headline tables, "
             "build timestamp, sources over the 3-fail threshold.",
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
    data_health_parser = subparsers.add_parser(
        "data-health",
        help="Data Health Spine: gate the factual + offseason data layer "
             "(read-only; RED/YELLOW/GREEN/UNKNOWN).",
    )
    data_health_parser.add_argument(
        "--json", action="store_true", help="emit the JSON report.",
    )
    data_health_parser.add_argument(
        "--strict", action="store_true",
        help="exit 1 when the overall gate is RED (publish-blocking mode).",
    )
    data_health_parser.add_argument(
        "--season", type=int, default=None,
        help="scope the report to a single season (forward-compat).",
    )
    data_health_parser.add_argument(
        "--html", nargs="?", const="", default=None, metavar="PATH",
        help="write a self-contained INTERNAL HTML dashboard (gate banner + "
             "coverage heatmap + flagged assertions). Omit PATH for the default "
             "gitignored data_health_report.html. Read-only side effect; never "
             "writes under output/site, never the DB.",
    )
    data_health_parser.add_argument(
        "--snapshot", action="store_true",
        help="persist this run to data_health_snapshot/_result (trend history).",
    )
    data_health_parser.add_argument(
        "--open-issue", action="store_true",
        help="open one deduped GitHub issue per regression class (requires gh).",
    )
    data_health_parser.add_argument(
        "--dry-run", action="store_true",
        help="with --open-issue, print the issues instead of creating them.",
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

    verify_publish_parser = subparsers.add_parser(
        "verify-publish-readiness",
        help=("Pre-publish data-quality gate: hand-rolled SQL assertions over the "
              "daily tables. Exits 2 on any HARD-FAIL so the publisher aborts the "
              "deploy; WARN-level checks print but never block."),
    )
    verify_publish_parser.add_argument(
        "--freshness-days", type=int, default=2,
        help="Max age (days) of newest conversation_documents.collected_at_utc before HARD-FAIL.")
    verify_publish_parser.add_argument(
        "--min-today-docs", type=int, default=200,
        help="Min conversation_documents rows collected in the last 24h (absolute floor).")
    verify_publish_parser.add_argument(
        "--strict", action="store_true",
        help="Promote the WARN mood/cohort/feature/player checks to HARD-FAIL (also via env VERIFY_STRICT_MOOD=1).")
    verify_publish_parser.add_argument(
        "--json", dest="emit_json", action="store_true", help="Also print a JSON summary.")

    set_conf_parser = subparsers.add_parser(
        "set-conferences",
        help="Update priority_teams.conference from a {slug: conference} seed JSON "
             "(2026 realignment hygiene). Idempotent; only touches listed slugs.",
    )
    set_conf_parser.add_argument("--seed", default="data/seeds/conference_2026.json")

    resolve_week_parser = subparsers.add_parser(
        "resolve-week",
        help=("Print the canonical (season_year, week, week_start, iso_key) for a "
              "date (default today). ONE source of truth so daily_ingest's "
              "producers and consumers can't drift onto different week vocabularies."),
    )
    resolve_week_parser.add_argument(
        "--as-of", default=None,
        help="Date YYYY-MM-DD to resolve (default: today on the box clock).")
    resolve_week_parser.add_argument(
        "--json", dest="emit_json", action="store_true",
        help="Print ONLY a JSON object to stdout (for `ConvertFrom-Json` in PowerShell).")

    import_team_sources_parser = subparsers.add_parser(
        "import-team-sources",
        help=("Upsert per-team source config into priority_teams from a seed CSV "
              "(Build #1: 21->138 teams). New teams inserted fully; existing teams "
              "get tier/reddit_mode/flair updated but hand-tuned reddit_team_sub / "
              "google_news_query are preserved (only filled if empty)."),
    )
    import_team_sources_parser.add_argument(
        "--csv", required=True, help="Seed CSV path (data/seeds/team_sources_seed.csv).")
    import_team_sources_parser.add_argument(
        "--dry-run", action="store_true", help="Report inserts/updates without writing.")

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
    tag_players_parser.add_argument("--no-last-name", action="store_true",
                                    help="Disable last-name-only matching (TASK 5.2 strict mode — "
                                         "full-name match required; higher precision, lower recall).")
    tag_players_parser.add_argument("--player-pool-season", type=int, default=None,
                                    help=("Optional override: build the player-name index from this "
                                          "season's stats instead of --season. Use in offseason mode "
                                          "when docs are tagged to next-season but stats only exist "
                                          "for last-season."))

    tag_teams_parser = subparsers.add_parser(
        "tag-team-mentions",
        help=("Scan untagged conversation_documents (bluesky_curated, substack_*) "
              "for team-alias mentions and emit target_type='team' rows. Reddit is "
              "tagged at collection time and excluded. Dry-run by default; pass "
              "--commit to insert rows."),
    )
    tag_teams_parser.add_argument("--season", type=int, required=True,
                                  help="Season year the emitted targets are stamped with.")
    tag_teams_parser.add_argument("--week", type=int, default=0,
                                  help="Week for the emitted targets (0 = preseason/offseason).")
    tag_teams_parser.add_argument("--limit", type=int, default=None,
                                  help="Optional cap on docs scanned (debug/preview).")
    tag_teams_parser.add_argument("--sources", type=str, default=None,
                                  help="Comma-separated source_name list to scan. Defaults to the "
                                       "curated untagged sources (bluesky_curated + substack_*).")
    tag_teams_parser.add_argument("--commit", action="store_true",
                                  help="Actually insert rows. Default is dry-run.")
    tag_teams_parser.add_argument("--preview", action="store_true",
                                  help="Print each matched (doc, team) pair for eyeball review.")

    compute_player_advanced_parser = subparsers.add_parser(
        "compute-player-advanced",
        help=("Compute player_advanced_metrics for a season (optionally "
              "through-week) and its season rollup with cohort percentiles."),
    )
    compute_player_advanced_parser.add_argument("--season", type=int, required=True)
    compute_player_advanced_parser.add_argument("--week", type=int, default=None,
        help="Optional through-week cutoff. If omitted, writes the full-season "
             "rollup (week=0) + per-position percentiles.")

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
        help="Render /methodology/fan-intelligence.html from source_registry + weights. "
             "Also regenerates /methodology/freshness.html (TASK 8.7).",
    )

    # Wave 25 — refresh 2026 award watch + depth chart from CSV source-of-truth.
    refresh_award_parser = subparsers.add_parser(
        "refresh-award-watch",
        help="Reload data/award_watch_2026.csv into player_award_watch_2026. Idempotent.",
    )
    refresh_award_parser.add_argument("--csv", type=str, default="data/award_watch_2026.csv")
    refresh_award_parser.add_argument("--dry-run", action="store_true")
    refresh_award_parser.add_argument(
        "--prune-source", type=str, default="consensus_may_2026",
        help="Delete rows from this source not present in the CSV (default: consensus_may_2026)",
    )

    refresh_depth_parser = subparsers.add_parser(
        "refresh-depth-chart",
        help="Reload data/depth_chart_2026.csv into player_depth_chart_2026. Idempotent.",
    )
    refresh_depth_parser.add_argument("--csv", type=str, default="data/depth_chart_2026.csv")
    refresh_depth_parser.add_argument("--dry-run", action="store_true")
    refresh_depth_parser.add_argument(
        "--prune-source", type=str, default="manual_editorial",
        help="Delete rows from this source not present in the CSV (default: manual_editorial)",
    )

    subparsers.add_parser(
        "verify-wave25",
        help="Audit Wave 25 modules — every status code, marquee players, override counts.",
    )

    # Sprint v5-11.5 pre-work — Cmd-K search index.
    build_search_parser = subparsers.add_parser(
        "build-search-index",
        help="Emit output/site/search-index.json — the static index the "
             "future Cmd-K overlay fetches. ~9k items / ~900KB minified.",
    )
    build_search_parser.add_argument(
        "--output",
        default="output/site/search-index.json",
        help="Output path (default: output/site/search-index.json).",
    )
    build_search_parser.add_argument(
        "--players-max", type=int, default=15000,
        help="Upper bound on player rows in the index (default: 15000).",
    )
    build_search_parser.add_argument(
        "--season", type=int, default=None,
        help="Season year for player_season_stats filter "
             "(default: latest with rows).",
    )
    build_search_parser.add_argument(
        "--inspect", action="store_true",
        help="Emit indented JSON for human inspection (default: minified).",
    )
    subparsers.add_parser(
        "build-freshness",
        help="Render /methodology/freshness.html only — last-run-per-source summary.",
    )

    # Sprint v5-1 Day 4 — Adapter 3 (archive_threads daily retro pull).
    fetch_archive_retro_parser = subparsers.add_parser(
        "fetch-archive-retro",
        help="Daily Arctic Shift retro pull. Same-MM-DD ± 2 days across prior "
             "years. High-engagement posts → archive_threads; lower-scoring → "
             "conversation_documents tagged 'arctic_shift_retro'. Powers S5 / S7.",
    )
    fetch_archive_retro_parser.add_argument(
        "--today", type=str, default=None,
        help="Anchor date as YYYY-MM-DD. Defaults to today UTC.",
    )
    fetch_archive_retro_parser.add_argument(
        "--years-back", type=int, default=12,
        help="How many prior years to scan (default: 12).",
    )
    fetch_archive_retro_parser.add_argument(
        "--min-score", type=int, default=50,
        help="Engagement threshold for archive_threads promotion (default: 50).",
    )
    fetch_archive_retro_parser.add_argument(
        "--day-window", type=int, default=2,
        help="Inclusive +/- day window around target MM-DD (default: 2).",
    )

    # Stubs for workflow CLIs that haven't been implemented yet (Sprint v5-8
    # follow-ups). The schedule slots fire hourly/weekly and were silently
    # failing → opening one automation-failure issue per cron firing once
    # notify_failure.yml started working (2026-05-22). Until the real
    # implementation lands, log a stub message and exit 0 so the workflow
    # stays green.
    subparsers.add_parser(
        "sync-digest-reactions",
        help="STUB. Sync 👍/👎 reactions on the rolling digest issue into "
             "editorial_overrides. Real implementation lands Sprint v5-8.",
    )
    weekly_digest_parser = subparsers.add_parser(
        "build-weekly-digest",
        help="STUB. Build the weekly digest markdown body. Real "
             "implementation lands Sprint v5-8.",
    )
    weekly_digest_parser.add_argument("--out", type=str, default="digest.md")
    weekly_digest_parser.add_argument("--look-ahead-days", type=int, default=7)

    # Sprint v5-1 Day 4 — S5 Today in CFB History renderer.
    render_today_history_parser = subparsers.add_parser(
        "render-today-in-history",
        help="Render /anniversary/today/ — the offseason safety-net page. "
             "Pulls from archive_threads + team_chronicle_observations + "
             "historical_seasons_summary; always emits a valid page.",
    )
    render_today_history_parser.add_argument(
        "--today", type=str, default=None,
        help="Anchor date as YYYY-MM-DD. Defaults to today UTC.",
    )
    render_today_history_parser.add_argument(
        "--output-dir", type=str, default="output/site/anniversary/today",
        help="Output directory (default: output/site/anniversary/today).",
    )
    render_today_history_parser.add_argument(
        "--max-cards", type=int, default=5,
        help="Maximum anniversary cards on the page (default: 5).",
    )

    # Sprint v5-1 Day 4 — S1 Days to Kickoff countdown.
    kickoff_countdown_parser = subparsers.add_parser(
        "render-kickoff-countdown",
        help="Render /kickoff/ countdown page + sitewide countdown.json. "
             "Daily lightweight refresh — no DB writes; reads kickoff date from "
             "cfb_calendar (KEY_EVENTS_<season> or games table).",
    )
    kickoff_countdown_parser.add_argument(
        "--today", type=str, default=None,
        help="Anchor date YYYY-MM-DD. Defaults to today UTC.",
    )
    kickoff_countdown_parser.add_argument(
        "--output-dir", type=str, default="output/site",
        help="Output directory root (writes /kickoff/index.html + "
             "/assets/countdown.json under this root).",
    )

    # Sprint v5-1 Day 4 — S4 Recruit Watch Board.
    refresh_recruiting_parser = subparsers.add_parser(
        "refresh-recruiting-pulse",
        help="Render /recruit-board/<class_year>/ pages. Reads "
             "player_recruiting_profiles for the target class year, ranks "
             "programs by weighted star sum, surfaces top 25.",
    )
    refresh_recruiting_parser.add_argument(
        "--class-year", type=int, default=None,
        help="Target recruiting class year (default: next class, e.g. 2027 in May 2026).",
    )
    refresh_recruiting_parser.add_argument(
        "--output-dir", type=str, default="output/site",
        help="Output directory root (writes /recruit-board/<class_year>/index.html).",
    )

    # Player-ID anchor — keep /players/<name>-<id>.html URLs stable across a
    # full DB rebuild (player_id is an autoincrement that otherwise reshuffles).
    from cfb_rankings.player_id_anchor import DEFAULT_ANCHOR_PATH as _ANCHOR_PATH
    export_anchor_parser = subparsers.add_parser(
        "export-player-id-anchor",
        help="Write the canonical (cfbd source_player_id -> player_id) mapping to "
             "a committed CSV so player URLs can be re-pinned after a rebuild.",
    )
    export_anchor_parser.add_argument("--path", type=str, default=_ANCHOR_PATH)
    seed_anchor_parser = subparsers.add_parser(
        "seed-player-id-anchor",
        help="Pre-seed canonical player ids from the anchor CSV BEFORE ingestion "
             "so a from-scratch rebuild reuses the same URLs. No-op on a "
             "populated DB.",
    )
    seed_anchor_parser.add_argument("--path", type=str, default=_ANCHOR_PATH)

    # Player dedup — duplicate-human players rows created by name-only ingest
    # paths (honors / recruits). Audit is read-only; merge is dry-run by default.
    subparsers.add_parser(
        "audit-player-duplicates",
        help="Read-only report of duplicate-human players rows and the "
             "conservative merge/delete plan (evidence-gated; see player_dedup.py).",
    )
    merge_dups_parser = subparsers.add_parser(
        "merge-player-duplicates",
        help="Merge duplicate-human players rows into their cfbd-canonical row "
             "(repoints every player_id child table). DRY-RUN unless --commit. "
             "Run export-player-id-anchor afterwards.",
    )
    merge_dups_parser.add_argument(
        "--commit", action="store_true",
        help="Actually write the merge (default is a dry-run plan summary).",
    )

    # R1 — Sunday Vibe Shift Ledger. See docs/octopus/next-roadmap.md.
    vibe_parser = subparsers.add_parser(
        "build-vibe-shifts",
        help="Render /hub/vibe-shifts/<season>/<week>/ ledger pages + per-team SVG share cards.",
    )
    vibe_parser.add_argument(
        "--season",
        type=int,
        default=None,
        help="Season year (omit to use the latest qualifying week's season).",
    )
    vibe_parser.add_argument(
        "--week",
        type=int,
        default=None,
        help="Week number (omit to render the latest few weeks).",
    )
    vibe_parser.add_argument(
        "--output-dir",
        default="output/site",
        help="Site root (default: output/site).",
    )
    vibe_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of teams ranked per week (default 10).",
    )
    vibe_parser.add_argument(
        "--max-weeks",
        type=int,
        default=4,
        help="When --week is omitted, how many recent weeks to render (default 4).",
    )

    # R4 — Dynasty Heatmap.
    dh_parser = subparsers.add_parser(
        "build-dynasty-heatmap",
        help="Render /history/heatmap/ — programs x years grid colored by within-year power percentile.",
    )
    dh_parser.add_argument("--year-start", type=int, default=2014)
    dh_parser.add_argument("--year-end", type=int, default=2025)
    dh_parser.add_argument("--output-dir", default="output/site")

    # R8 — NFL Pipeline.
    np_parser = subparsers.add_parser(
        "build-nfl-pipeline",
        help="Render /nfl-pipeline/ — twelve years of NFL Draft picks ranked by program.",
    )
    np_parser.add_argument("--year-start", type=int, default=2014)
    np_parser.add_argument("--year-end", type=int, default=2025)
    np_parser.add_argument("--output-dir", default="output/site")
    np_parser.add_argument("--top-n", type=int, default=50)

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

    # Signature Bets S2.2 — Hot-Take Engine CLI.
    pht_parser = subparsers.add_parser(
        "player-hot-take",
        help="Print the Hot-Take for one player (math trail + daily pick).",
    )
    pht_parser.add_argument("slug_or_id", help="player slug ('cj-carr-4788') or player_id.")
    pht_parser.add_argument("--season", type=int, default=None)
    pht_parser.add_argument("--as-of", default=None, help="YYYY-MM-DD; defaults to today.")

    cdht_parser = subparsers.add_parser(
        "compute-daily-hot-takes",
        help="Populate player_daily_hot_take for every qualifying player.",
    )
    cdht_parser.add_argument("--season", type=int, default=None)
    cdht_parser.add_argument("--as-of", default=None)

    # Signature Bets S2.5 — Mirror Match CLI.
    pmm_parser = subparsers.add_parser(
        "player-mirror-match",
        help="Print the top Mirror Matches for one player.",
    )
    pmm_parser.add_argument("slug_or_id")
    pmm_parser.add_argument("--season", type=int, default=None)
    pmm_parser.add_argument("-k", type=int, default=10)

    cmm_parser = subparsers.add_parser(
        "compute-mirror-matches",
        help="Populate player_mirror_matches for every player in --season.",
    )
    cmm_parser.add_argument("--season", type=int, default=None)
    cmm_parser.add_argument("-k", type=int, default=10)

    # Wave 10 — CFBD play-by-play ingest + per-player metrics.
    pbp_ingest_parser = subparsers.add_parser(
        "ingest-cfbd-pbp",
        help=("Pull /plays from CFBD for (season, weeks) and upsert into "
              "cfbd_pbp_plays + cfbd_pbp_play_actors."),
    )
    pbp_ingest_parser.add_argument("--season", type=int, required=True)
    pbp_ingest_parser.add_argument("--weeks", type=int, nargs="*", default=None,
                                   help="Specific weeks to pull. Default = 1..16 regular.")
    pbp_ingest_parser.add_argument("--season-type", type=str, default="regular",
                                   choices=["regular", "postseason", "both"])
    pbp_ingest_parser.add_argument("--classification", type=str, default="fbs")
    pbp_ingest_parser.add_argument("--skip-actors", action="store_true",
                                   help="Skip play-text parsing (raw plays only).")

    compute_pbp_parser = subparsers.add_parser(
        "compute-player-pbp-metrics",
        help=("Derive per-player PBP metrics (EPA/db, CPOE, success, "
              "explosive, aDOT, etc.) and write player_pbp_metrics_season."),
    )
    compute_pbp_parser.add_argument("--season", type=int, required=True)

    # Wave 15 — Narrative Arc LLM generator batch CLI.
    garc_parser = subparsers.add_parser(
        "generate-player-narrative-arcs",
        help=("Generate 3-act season narrative arcs for top-N players using "
              "local Ollama. Writes to player_narrative_arc cache."),
    )
    garc_parser.add_argument("--season", type=int, required=True)
    garc_parser.add_argument("--top", type=int, default=100)
    garc_parser.add_argument("--player-ids", type=int, nargs="*", default=None)
    garc_parser.add_argument("--model", type=str, default=None)
    garc_parser.add_argument("--force-refresh", action="store_true")

    # Wave 8 — Signature Story LLM generator batch CLI.
    gpsig_parser = subparsers.add_parser(
        "generate-player-signatures",
        help=("Generate Signature Story prose for top-N players using local "
              "Ollama (mistral-nemo). Writes to player_signature_story cache."),
    )
    gpsig_parser.add_argument("--season", type=int, required=True)
    gpsig_parser.add_argument("--top", type=int, default=100,
                              help="Top N players by Heisman volume / Savant lead.")
    gpsig_parser.add_argument("--player-ids", type=int, nargs="*", default=None,
                              help="Explicit player_id filter.")
    gpsig_parser.add_argument("--model", type=str, default=None)
    gpsig_parser.add_argument("--force-refresh", action="store_true")

    # Signature Bets S2.7 — Achievements CLI.
    cach_parser = subparsers.add_parser(
        "compute-achievements",
        help="Run every achievement detector + recompute rarity for --season.",
    )
    cach_parser.add_argument("--season", type=int, default=None)

    pach_parser = subparsers.add_parser(
        "player-achievements",
        help="Print unlocked achievements for one player.",
    )
    pach_parser.add_argument("slug_or_id")
    pach_parser.add_argument("--season", type=int, default=None)

    # v5-7.5: per-domain sample-size confidence calibration.
    # Locked spec: docs/design-system/33-confidence-signaling.md
    conf_recalc = subparsers.add_parser(
        "recompute-confidence-thresholds",
        help=("Recompute the per-domain confidence-chip thresholds from the "
              "current per-team-week distribution. Idempotent within a "
              "quarter (UPSERT on (domain, quarter))."),
    )
    conf_recalc.add_argument(
        "--domain",
        choices=["fan_intel", "historical", "model", "market", "prediction", "all"],
        default="all",
        help="Which domain to recompute (default: all).",
    )
    conf_recalc.add_argument(
        "--print-only", action="store_true",
        help="Compute and print the thresholds but DO NOT write to DB.",
    )

    conf_status = subparsers.add_parser(
        "confidence-status",
        help="Print the current calibration row per domain.",
    )

    # v5-10e foundation: Monday Mood Map renderer.
    # Locked spec: docs/design-system/30-page-archetypes.md + mockup_07*.
    mm_parser = subparsers.add_parser(
        "generate-mood-map",
        help=("Render the 1200x675 Monday Mood Map PNG. Cron target: every "
              "Monday 6am ET. Outputs light + optional dark variant."),
    )
    mm_parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/site/assets/share/monday_mood_map.png"),
        help="Output PNG path (parent dirs created if missing).",
    )
    mm_parser.add_argument(
        "--dark", action="store_true",
        help="Render the dark-mode variant instead.",
    )
    mm_parser.add_argument(
        "--week-label",
        default=None,
        help="When-label override (e.g. 'WEEK OF 11 MAY 2026 · No. 048'). "
             "Defaults to the current ISO week.",
    )

    # v5-10e: Daily Belief Movers + Pre-game Pack share cards
    dm_parser = subparsers.add_parser(
        "generate-daily-movers",
        help="Render the 1200x630 Daily Belief Movers share card.",
    )
    dm_parser.add_argument(
        "--output", type=Path,
        default=Path("output/site/assets/share/daily_movers.png"),
    )
    dm_parser.add_argument("--dark", action="store_true")

    pp_parser = subparsers.add_parser(
        "generate-pregame-pack",
        help="Render the 1200x630 Pre-game Pack share card for a Saturday game.",
    )
    pp_parser.add_argument(
        "--output", type=Path,
        default=Path("output/site/assets/share/pregame_pack.png"),
    )
    pp_parser.add_argument(
        "--game-id", type=int, default=None,
        help="Specific game_id to render; defaults to next-Saturday's marquee.",
    )
    pp_parser.add_argument("--dark", action="store_true")

    # QA audit — dump every Signature Bets module's output for a player.
    pbets_parser = subparsers.add_parser(
        "player-bets-audit",
        help="Dump all Signature Bets module outputs for one player (QA tool).",
    )
    pbets_parser.add_argument("slug_or_id")
    pbets_parser.add_argument("--season", type=int, default=None)

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
    import_honors_parser.add_argument("--no-stubs", action="store_true",
        help="Skip honors whose player isn't already in the DB (no stub creation).")

    prune_honor_stubs_parser = subparsers.add_parser(
        "prune-honor-stubs",
        help=("Delete garbage honor-import stub players (numeric/RV/NR/team-code "
              "names with no real data) + their honors. Dry-run unless --commit."),
    )
    prune_honor_stubs_parser.add_argument("--commit", action="store_true")

    draft_parser = subparsers.add_parser(
        "ingest-nfl-draft",
        help="Fetch CFBD /draft/picks for one year or a range; upserts into player_nfl_draft.",
    )
    draft_parser.add_argument("--year", type=int, default=None,
        help="Single draft year to ingest.")
    draft_parser.add_argument("--start-year", type=int, default=None,
        help="Start year (inclusive) for range ingest.")
    draft_parser.add_argument("--end-year", type=int, default=None,
        help="End year (inclusive) for range ingest.")

    coaches_parser = subparsers.add_parser(
        "ingest-cfbd-coaches",
        help="Fetch CFBD /coaches; UPDATEs team_seasons.head_coach for matched rows.",
    )
    coaches_parser.add_argument("--year", type=int, default=None,
        help="Single year to ingest.")
    coaches_parser.add_argument("--start-year", type=int, default=None,
        help="Start year (inclusive) for range ingest.")
    coaches_parser.add_argument("--end-year", type=int, default=None,
        help="End year (inclusive) for range ingest.")

    wiki_awards_parser = subparsers.add_parser(
        "scrape-wiki-awards",
        help="Scrape Wikipedia All-America / All-Conference / Position Awards "
             "into CSVs under data/scraped_honors/ (TASKs 4.1/4.2/4.3).",
    )
    wiki_awards_parser.add_argument("--start-year", type=int, default=2022)
    wiki_awards_parser.add_argument("--end-year", type=int, default=2025)
    wiki_awards_parser.add_argument("--out-dir", default="data/scraped_honors")
    wiki_awards_parser.add_argument("--auto-import", action="store_true",
        help="After scraping, auto-import every produced CSV via import-player-honors.")
    wiki_awards_parser.add_argument("--no-stubs", action="store_true",
        help="With --auto-import: skip honors whose player is not already in the DB (safe default).")

    nil_scrape_parser = subparsers.add_parser(
        "scrape-nil-valuations",
        help="Scrape On3 CFB NIL rankings and save to player_nil_valuations table.",
    )
    nil_scrape_parser.add_argument("--limit", type=int, default=200,
        help="Max players to import (default 200).")
    nil_scrape_parser.add_argument("--as-of-date", default=None,
        help="Override snapshot date YYYY-MM-DD (default: today).")
    nil_scrape_parser.add_argument("--dry-run", action="store_true",
        help="Print results without writing to DB.")

    nil_import_parser = subparsers.add_parser(
        "import-nil-valuations",
        help="Import NIL valuations from a CSV file into player_nil_valuations.",
    )
    nil_import_parser.add_argument("--csv", required=True,
        help="Path to CSV with columns: player_name, rank, valuation_usd, [whisper_usd], "
             "[position], [team_name], [as_of_date], [source_name].")
    nil_import_parser.add_argument("--as-of-date", default=None,
        help="Snapshot date YYYY-MM-DD; overrides per-row as_of_date column if set.")
    nil_import_parser.add_argument("--source", default="on3",
        help="Source name to tag rows with (default: on3).")

    seed_team_aliases_parser = subparsers.add_parser("seed-team-aliases")
    seed_team_aliases_parser.add_argument("--season", type=int, required=True)

    ingest_gdelt_news_volume_parser = subparsers.add_parser(
        "ingest-gdelt-news-volume",
        help=(
            "Download today's GDELT GKG bulk files over HTTP (credential-free) "
            "and count daily article mentions per CFB team. Writes to "
            "team_news_volume and source_observations. Use --commit to persist."
        ),
    )
    ingest_gdelt_news_volume_parser.add_argument(
        "--date",
        default=None,
        help="Target date YYYY-MM-DD (default: today UTC).",
    )
    ingest_gdelt_news_volume_parser.add_argument(
        "--lookback-hours",
        type=int,
        default=26,
        help="How far back in masterfilelist.txt to look (default 26 h).",
    )
    ingest_gdelt_news_volume_parser.add_argument(
        "--commit",
        action="store_true",
        help="Persist results to team_news_volume + source_observations.",
    )

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

    collect_reddit_team_rss_parser = subparsers.add_parser(
        "collect-reddit-team-rss",
        help=("Collect each priority team's FOOTBALL subreddit via the .rss path "
              "(Build #2). Dedicated subs -> new.rss; school subs -> flair-filtered "
              "search.rss. Honest UA, no spoof. Replaces the dead text-search "
              "watchlist for per-team Reddit."),
    )
    collect_reddit_team_rss_parser.add_argument("--season", type=int, required=True)
    collect_reddit_team_rss_parser.add_argument("--week", type=int, required=True)
    collect_reddit_team_rss_parser.add_argument("--limit", type=int, default=50,
        help="Max posts per subreddit per run (reddit RSS caps ~100).")
    collect_reddit_team_rss_parser.add_argument("--teams", nargs="*", type=int, default=None,
        help="Optional team_id filter; default = all configured priority teams.")

    collect_boards_parser = subparsers.add_parser(
        "collect-team-boards",
        help=("Collect independent team message boards via public RSS (Build #4). "
              "Each board maps to one team -> direct target. Captures fanbases "
              "that live on boards (TigerDroppings/CougarBoard/etc.), not Reddit."),
    )
    collect_boards_parser.add_argument("--season", type=int, required=True)
    collect_boards_parser.add_argument("--week", type=int, required=True)
    collect_boards_parser.add_argument("--seed", default="data/seeds/board_rss_seed.json",
        help="JSON list of [{team_slug, board_name, board_rss_url}].")

    collect_youtube_comments_parser = subparsers.add_parser(
        "collect-youtube-comments",
        help=("Collect CFB YouTube comments (Build #3): national channels (seed) "
              "+ per-team configured channels. uploads->videos.commentCount triage"
              "->commentThreads. Per-team channels get a direct target; national "
              "ones are tagged by `tag-team-mentions --sources youtube`."),
    )
    collect_youtube_comments_parser.add_argument("--season", type=int, required=True)
    collect_youtube_comments_parser.add_argument("--week", type=int, required=True)
    collect_youtube_comments_parser.add_argument(
        "--national-seed", default="data/seeds/youtube_national_channels.json",
        help="JSON list of national channels [{channel_id,name}].")
    collect_youtube_comments_parser.add_argument("--max-videos-per-channel", type=int, default=8)
    collect_youtube_comments_parser.add_argument("--max-comments-per-video", type=int, default=100)
    collect_youtube_comments_parser.add_argument("--max-units", type=int, default=6000,
        help="Stop once this many API units are spent (free daily quota is 10000).")
    collect_youtube_comments_parser.add_argument("--min-comment-count", type=int, default=3)

    collect_podcast_transcripts_parser = subparsers.add_parser(
        "collect-podcast-transcripts",
        help=("Transcribe recent podcast episodes on the GPU (faster-whisper) and "
              "land each transcript as a conversation_documents row "
              "(source_name='podcast_transcript'); tag-team-mentions --sources "
              "podcast_transcript then attributes them. Ledger-rotated + time-boxed; "
              "self-skips cleanly if faster-whisper isn't installed. Run with the "
              ".venv-ml python so CUDA is available."),
    )
    collect_podcast_transcripts_parser.add_argument("--season", type=int, required=True)
    collect_podcast_transcripts_parser.add_argument("--week", type=int, required=True)
    collect_podcast_transcripts_parser.add_argument("--model-size", default="small.en",
        help="faster-whisper model (tiny.en/base.en/small.en/medium.en/large-v3). small.en is a good speed/quality balance on a 3090.")
    collect_podcast_transcripts_parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    collect_podcast_transcripts_parser.add_argument("--compute-type", default="float16",
        help="float16 for CUDA; int8 for CPU.")
    collect_podcast_transcripts_parser.add_argument("--max-episodes", type=int, default=6,
        help="Rotated batch size per run (collection_ledger picks newest-then-stalest).")
    collect_podcast_transcripts_parser.add_argument("--budget-seconds", type=float, default=900.0,
        help="Hard wall-clock budget; defers the rest to the next run.")
    collect_podcast_transcripts_parser.add_argument("--max-age-days", type=int, default=21,
        help="Only consider episodes published within this many days.")
    collect_podcast_transcripts_parser.add_argument("--beam-size", type=int, default=1)
    collect_podcast_transcripts_parser.add_argument("--show", action="append", default=[],
        help="Optional show_slug filter (repeatable), e.g. --show locked_on_alabama.")

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

    sync_team_locations_parser = subparsers.add_parser("sync-team-locations")
    sync_team_locations_parser.add_argument("--season", type=int, default=2025)
    sync_team_locations_parser.add_argument("--classification", type=str, default=None)

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
    site_parser.add_argument(
        "--use-lkg-only",
        action="store_true",
        default=False,
        help=(
            "Emergency mode: read chronicle cards only from Last-Known-Good cache, "
            "skipping fresh LLM generation entirely. Intended for the "
            "emergency_publish.ps1 failure-handler path."
        ),
    )
    site_parser.add_argument(
        "--no-llm",
        action="store_true",
        default=False,
        help=(
            "Belt-and-suspenders guard: hard-disable every LLM call path in the "
            "chronicle pipeline. --use-lkg-only should already skip LLM calls, "
            "but this flag enforces the constraint at each call site."
        ),
    )

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

    populate_arcs_parser = subparsers.add_parser(
        "populate-arcs",
        help="Open/close the 10 D-010 narrative arc frames into season_narrative_arc.",
    )
    populate_arcs_parser.add_argument("--season", type=int, required=True)
    populate_arcs_parser.add_argument(
        "--week", type=int, default=0,
        help="Week the arcs open at (0 = preseason/offseason).",
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

    track_lexicon_parser = subparsers.add_parser(
        "track-lexicon",
        help=(
            "Count the curated fan-slang watchlist (seeds/lexicon_terms.yaml) into "
            "lexicon_term_daily. Complements mine-lexicon: fixed terms, daily counts, "
            "unbroken history per team. Run in the collection window BEFORE any "
            "raw-text purge."
        ),
    )
    track_lexicon_parser.add_argument("--days", type=int, default=3,
        help="Rolling window of external-created days to (re)count. Default 3.")
    track_lexicon_parser.add_argument("--backfill", action="store_true",
        help="Scan the entire retained corpus and rebuild the whole table.")
    track_lexicon_parser.add_argument("--terms-file", default="seeds/lexicon_terms.yaml")

    discourse_keyness_parser = subparsers.add_parser(
        "compute-discourse-keyness",
        help=(
            "Language Layer wave 1: weighted log-odds keyness of each (team, season) "
            "fan-voice corpus vs the same-season field, written to team_discourse_terms "
            "(week=0 season cuts) for the team-page Lexicon module. Dry run by default; "
            "pass --commit to write."
        ),
    )
    discourse_keyness_parser.add_argument("--season", action="append", required=True,
        help="Season year to compute. Repeatable (--season 2024 --season 2025) "
             "or a comma list (--season 2022,2023,2024,2025).")
    discourse_keyness_parser.add_argument("--teams", default=None,
        help="Optional comma list of team slugs. Explicit teams bypass the "
             "--min-team-docs floor; default is every team above it.")
    discourse_keyness_parser.add_argument("--top-n", type=int, default=30,
        help="Distinctive terms kept per (team, season). Default 30.")
    discourse_keyness_parser.add_argument("--min-team-docs", type=int, default=200,
        help="Doc floor for the all-teams sweep. Default 200.")
    discourse_keyness_parser.add_argument("--weekly", action="store_true",
        help="Also compute the CURRENT week's cut (week>0 rows, 30-doc "
             "team-week floor, top 12) for any requested season containing "
             "today. Past seasons are skipped for the weekly cut.")
    discourse_keyness_parser.add_argument("--commit", action="store_true",
        help="Write rows (default: dry run — compute + print only).")

    discourse_mirror_parser = subparsers.add_parser(
        "compute-discourse-mirror",
        help=(
            "Language Layer wave 2: rivalry-mirror keyness — each fanbase's "
            "distinctive language inside +/-12-token windows around rival "
            "mentions, both directions per rivalry_pairs row, written to "
            "team_discourse_mirror for the team-page Mirror band. Dry run by "
            "default; pass --commit to write."
        ),
    )
    discourse_mirror_parser.add_argument("--season", action="append", required=True,
        help="Season year to compute. Repeatable (--season 2024 --season 2025) "
             "or a comma list (--season 2022,2023,2024,2025).")
    discourse_mirror_parser.add_argument("--pairs", default=None,
        help="Optional comma list of explicit pairs as slugA:slugB "
             "(e.g. michigan:ohio-state,alabama:auburn). Overrides the "
             "rivalry_pairs table read.")
    discourse_mirror_parser.add_argument("--commit", action="store_true",
        help="Write rows (default: dry run — compute + print only).")

    fanbase_voice_parser = subparsers.add_parser(
        "compute-fanbase-voice",
        help=(
            "Language Layer wave 2: fanbase voice personality aggregates "
            "(optimism / joy / anger / doom / sarcasm) with cohort percentile "
            "ranks, written to fanbase_voice_profile for the team-page Voice "
            "module. Cohort = teams above --min-mentions that season. Dry run "
            "by default; pass --commit to write."
        ),
    )
    fanbase_voice_parser.add_argument("--season", action="append", required=True,
        help="Season year to compute. Repeatable (--season 2024 --season 2025) "
             "or a comma list (--season 2024,2025).")
    fanbase_voice_parser.add_argument("--min-mentions", type=int, default=300,
        help="Per-season mention floor for cohort membership. Default 300.")
    fanbase_voice_parser.add_argument("--commit", action="store_true",
        help="Write rows (default: dry run — compute + print only).")

    discourse_eras_parser = subparsers.add_parser(
        "compute-team-eras",
        help=(
            "Language Layer wave 3: within-team cross-season vocabulary contrast, "
            "written to team_discourse_era_terms for the team-page Story Words strip. "
            "Dry run by default; pass --commit to write."
        ),
    )
    discourse_eras_parser.add_argument("--season", action="append", required=True,
        help="Season year(s) to compute. Repeatable or comma-list. "
             "Multiple seasons required for within-team contrast.")
    discourse_eras_parser.add_argument("--teams", default=None,
        help="Optional comma list of team slugs. Default: all teams above floor.")
    discourse_eras_parser.add_argument("--top-n", type=int, default=8,
        help="Era terms kept per (team, season). Default 8.")
    discourse_eras_parser.add_argument("--min-team-docs", type=int, default=150,
        help="Doc floor per team-season. Default 150.")
    discourse_eras_parser.add_argument("--min-seasons", type=int, default=2,
        help="Minimum distinct seasons a team must have data for. Default 2.")
    discourse_eras_parser.add_argument("--commit", action="store_true",
        help="Write rows (default: dry run).")

    player_descriptors_parser = subparsers.add_parser(
        "compute-player-descriptors",
        help=(
            "Language Layer wave 3: fan-voice player descriptor terms from "
            "+-8-token windows around player name mentions, written to "
            "player_discourse_terms for the In Their Words player module. "
            "Dry run by default; pass --commit to write."
        ),
    )
    player_descriptors_parser.add_argument("--season", action="append", required=True,
        help="Season year(s) to compute. Repeatable or comma-list.")
    player_descriptors_parser.add_argument("--players", default=None,
        help="Optional comma list of player IDs (integers). Default: all players above floor.")
    player_descriptors_parser.add_argument("--top-n", type=int, default=10,
        help="Descriptor terms kept per (player, season). Default 10.")
    player_descriptors_parser.add_argument("--min-windows", type=int, default=30,
        help="Minimum window tokens for a player to receive descriptors. Default 30.")
    player_descriptors_parser.add_argument("--commit", action="store_true",
        help="Write rows (default: dry run).")

    fan_voice_board_parser = subparsers.add_parser(
        "build-fan-voice-board",
        help=(
            "Language Layer wave 3: build the standalone /fan-voice/index.html "
            "leaderboard page showing optimism rankings, signature terms, and "
            "Word of the Week across all teams."
        ),
    )
    fan_voice_board_parser.add_argument("--season", type=int, required=True,
        help="Season year to display.")
    fan_voice_board_parser.add_argument("--output-dir", default=None,
        help="Output root dir (default: output/site).")

    kwic_quotes_parser = subparsers.add_parser(
        "compute-kwic-quotes",
        help=(
            "Language Layer wave 4: KWIC (keyword-in-context) quote extraction — "
            "pulls the top-N distinctive terms per team and samples the best "
            "surrounding quote windows, written to team_discourse_kwic_quotes. "
            "Dry run by default; pass --commit to write."
        ),
    )
    kwic_quotes_parser.add_argument("--season", action="append", required=True,
        help="Season year(s) to compute. Repeatable or comma-list.")
    kwic_quotes_parser.add_argument("--commit", action="store_true",
        help="Write rows (default: dry run — compute + print only).")
    kwic_quotes_parser.add_argument("--top-terms", type=int, default=5,
        help="Top distinctive terms to pull quotes for per team. Default 5.")

    discourse_atlas_parser = subparsers.add_parser(
        "compute-discourse-atlas",
        help=(
            "Language Layer wave 4: discourse atlas clustering — groups teams "
            "by semantic fan-voice similarity into N clusters, written to "
            "team_discourse_atlas for the fan-voice leaderboard. "
            "Dry run by default; pass --commit to write."
        ),
    )
    discourse_atlas_parser.add_argument("--season", action="append", required=True,
        help="Season year(s) to compute. Repeatable or comma-list.")
    discourse_atlas_parser.add_argument("--commit", action="store_true",
        help="Write rows (default: dry run — compute + print only).")
    discourse_atlas_parser.add_argument("--n-clusters", type=int, default=8,
        help="Number of clusters for the atlas grouping. Default 8.")

    fan_voice_leaderboard_parser = subparsers.add_parser(
        "build-fan-voice-leaderboard",
        help=(
            "Language Layer wave 4: build the standalone /fan-voice/leaderboard.html "
            "page showing KWIC quotes, atlas clusters, and fanbase voice rankings."
        ),
    )
    fan_voice_leaderboard_parser.add_argument("--season", type=int, required=True,
        help="Season year to display.")

    seed_rivalry_pairs_parser = subparsers.add_parser(
        "seed-rivalry-pairs",
        help=(
            "Load canonical rivalry pairs (seeds/rivalry_pairs.yaml) into rivalry_pairs. "
            "Bootstraps the Rent Free pipeline: _load_rival_pairs unions these with "
            "rivalry_obsession_weekly-derived pairs."
        ),
    )
    seed_rivalry_pairs_parser.add_argument("--pairs-file", default="seeds/rivalry_pairs.yaml")

    seal_capsule_parser = subparsers.add_parser(
        "seal-capsule",
        help=(
            "Freeze the current four-stat suite + slang into a durable git-committed "
            "JSON (data/capsules/<label>.json). The renderer reads the JSON, so the "
            "capsule reproduces forever even after DB rebuilds. Fan suite."
        ),
    )
    seal_capsule_parser.add_argument("--label", required=True, help="e.g. 2026-06")
    seal_capsule_parser.add_argument("--title", default="Talking Season, Frozen")
    seal_capsule_parser.add_argument("--sealed-on", default=None, help="ISO date; default = today")

    rasterize_cards_parser = subparsers.add_parser(
        "rasterize-cards",
        help=(
            "Rasterize the four fan-suite hubs' card SVGs to opaque PNG (og:image "
            "unfurling). Headless Chrome; no-ops if Chrome is absent. Fan suite."
        ),
    )
    rasterize_cards_parser.add_argument("--output-dir", default="output/site")

    compute_delusion_parser = subparsers.add_parser(
        "compute-delusion-premium",
        help=(
            "Compute delusion_premium_weekly (fanbase belief vs market title odds; "
            "delusion_index = belief pctl - market pctl). Polymarket + Backometer. Fan suite."
        ),
    )
    compute_delusion_parser.add_argument("--season", type=int, required=True)

    compute_aura_parser = subparsers.add_parser(
        "compute-aura",
        help=(
            "Compute player_aura_weekly (perception vs production percentile within "
            "position cohort; aura_tax = the gap). QB/RB only — wepa metrics. Fan suite."
        ),
    )
    compute_aura_parser.add_argument("--season", type=int, required=True)

    compute_backometer_parser = subparsers.add_parser(
        "compute-backometer",
        help=(
            "Compute backometer_weekly (0-100 fanbase belief, named zones, hysteresis, "
            "n>=200 floor) from team_week_conversation_features. Fan Intelligence suite."
        ),
    )
    compute_backometer_parser.add_argument("--season", type=int, required=True)
    compute_backometer_parser.add_argument("--weeks", nargs="*", type=int, default=None,
        help="Optional week filter; default = all weeks with feature rows.")

    fix_player_positions_parser = subparsers.add_parser(
        "fix-player-positions",
        help=(
            "Repair players.position from roster_entries / player_season_stats evidence "
            "(game-stat category guesses minted QBs as RBs). Dry-run unless --commit."
        ),
    )
    fix_player_positions_parser.add_argument("--commit", action="store_true")

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

    # ---------------------------------------------------------------- team pages
    load_profiles_parser = subparsers.add_parser(
        "load-team-profiles",
        help="Read profiles/<slug>.md files into team_profiles + team_voice tables.",
    )
    load_profiles_parser.add_argument(
        "--slug", nargs="*", default=None,
        help="Program slug(s) to load. Omit to load every profile in profiles/.",
    )

    gen_narr_parser = subparsers.add_parser(
        "generate-narratives",
        help="Generate state-of-team narratives for each loaded profile, persist to "
             "team_season_narratives. Template mode by default; pass --llm for Claude.",
    )
    gen_narr_parser.add_argument(
        "--slug", nargs="*", default=None,
        help="Program slugs to run. Omit for all loaded profiles.",
    )
    gen_narr_parser.add_argument(
        "--llm", choices=["template", "claude", "claude-code"], default="template",
        help="Generation backend. Default: template (deterministic, offline).",
    )
    gen_narr_parser.add_argument(
        "--model", default="claude-opus-4-7",
        help="Claude model id for --llm claude / claude-code. "
             "Default upgraded to Opus 4.7 per v5.3 row #13 — team narratives "
             "are quarterly cadence, low volume, high visibility.",
    )
    gen_narr_parser.add_argument(
        "--season", type=int, default=None,
        help="Override season context. Default: latest season with games for the team.",
    )

    gen_chron_parser = subparsers.add_parser(
        "generate-chronicle",
        help="Generate Chronicle observation cards (anomaly/moment/flashpoint/echo) "
             "per loaded profile and persist top-K to team_chronicle_observations.",
    )
    gen_chron_parser.add_argument(
        "--slug", nargs="*", default=None,
        help="Program slugs to run. Omit for all loaded profiles.",
    )
    gen_chron_parser.add_argument(
        "--top-k", type=int, default=5,
        help="Max number of cards to publish per team-season (default: 5).",
    )
    gen_chron_parser.add_argument(
        "--season", type=int, default=None,
        help="Season override.",
    )
    gen_chron_parser.add_argument(
        "--model", default="auto",
        choices=["auto", "sonnet", "opus", "template"],
        help="LLM routing. 'auto' = Sonnet standard + Opus for blue-bloods' "
             "top-1 card. 'template' = skip LLM entirely (degraded mode).",
    )
    gen_chron_parser.add_argument(
        "--workers", type=int, default=3,
        help="Parallel LLM subprocess workers per team (default: 3).",
    )
    gen_chron_parser.add_argument(
        "--batch", default="auto",
        choices=["auto", "on", "off"],
        help=(
            "Use Anthropic Message Batches API (50%% off + 1-hour prompt "
            "caching). 'auto' (default): batch ON for multi-team runs "
            "(>=2 slugs), OFF for single-team runs (typically interactive). "
            "'on' / 'off' force either path. The synchronous subprocess "
            "path remains the fallback for single-team interactive iteration."
        ),
    )

    render_team_parser = subparsers.add_parser(
        "render-team",
        help="Render the team page HTML for one or more slugs to "
             "output/site/teams/<slug>.html.",
    )
    render_team_parser.add_argument(
        "slugs", nargs="+",
        help="Program slug(s) to render (e.g. notre-dame alabama vanderbilt massachusetts).",
    )
    render_team_parser.add_argument(
        "--output-dir", default="output/site/teams",
        help="Output directory (default: output/site/teams).",
    )
    render_team_parser.add_argument(
        "--date", default=None,
        help="Override 'today' as YYYY-MM-DD for state resolution (testing).",
    )
    render_team_parser.add_argument(
        "--season", type=int, default=None,
        help="Override season.",
    )

    # ---- sprint 10: storylines (merge-zone marker) ----
    gen_thread_parser = subparsers.add_parser(
        "generate-thread-chapter",
        help="Generate a draft next chapter for a Storyline Thread. Writes "
             "to seeds/_drafts/<slug>_<timestamp>.py for human review before "
             "publishing. --auto runs without interactive prompts (stub for "
             "live LLM call infra in a follow-on sprint).",
    )
    gen_thread_parser.add_argument(
        "--thread", required=True,
        help="Thread slug (e.g. 12-team-playoff-settling).",
    )
    gen_thread_parser.add_argument(
        "--auto", action="store_true",
        help="Cron-mode: no interactive prompts. Calls the shared "
             "llm_runtime; if ANTHROPIC_API_KEY is unset, falls back to "
             "writing a draft scaffold for human review.",
    )
    gen_thread_parser.add_argument(
        "--skip-render", action="store_true",
        help="Skip the post-append render-storylines re-render. Useful "
             "for batch generation; render once after all chapters land.",
    )

    render_storylines_parser = subparsers.add_parser(
        "render-storylines",
        help="Re-seed the storylines DB tables from seeds/, render every "
             "thread page + the index to output/site/storylines/, and emit "
             "the stub_data/threads.json contract Sprint 9 reads.",
    )
    render_storylines_parser.add_argument(
        "--all", action="store_true",
        help="Render every thread (current default behavior — accepted for "
             "explicitness).",
    )
    render_storylines_parser.add_argument(
        "--output-dir", default="output/site/storylines",
        help="Output directory (default: output/site/storylines).",
    )
    render_storylines_parser.add_argument(
        "--contract-path", default="stub_data/threads.json",
        help="Where to write the homepage contract JSON (default: "
             "stub_data/threads.json).",
    )
    render_storylines_parser.add_argument(
        "--no-seed", action="store_true",
        help="Skip the seed-load step and render from existing DB rows only.",
    )

    # WS-12: data-driven storyline candidate queue (editor pull-list, not auto-publish).
    storyline_candidates_parser = subparsers.add_parser(
        "build-storyline-candidates",
        help="Rank live narrative arcs (season_narrative_arc) into the "
             "storyline_candidate queue for editorial review. Dry-run by "
             "default; pass --commit to write.",
    )
    storyline_candidates_parser.add_argument("--season", type=int, required=True)
    storyline_candidates_parser.add_argument(
        "--commit", action="store_true",
        help="Write ranked candidates (preserves editor review_status on re-run).",
    )
    storyline_candidates_parser.add_argument(
        "--digest", nargs="?", const="output/storyline-candidates.md",
        default=None,
        help="Also render an editor-facing Markdown digest (+ JSON sidecar) of "
             "the queue. Optional path; defaults to output/storyline-candidates.md.",
    )

    review_candidate_parser = subparsers.add_parser(
        "review-storyline-candidate",
        help="Record an editor verdict on a storyline candidate "
             "(the sanctioned way to set review_status; survives daily re-rank).",
    )
    review_candidate_parser.add_argument("--id", required=True, dest="candidate_id")
    review_candidate_parser.add_argument(
        "--status", required=True, choices=["proposed", "promoted", "dismissed"],
    )

    # WS-12: editorial cadence dashboard — surfaces "what's overdue" across surfaces.
    cadence_parser = subparsers.add_parser(
        "editorial-cadence",
        help="Write the editorial cadence dashboard (Markdown + JSON): "
             "last-published-per-surface vs staleness thresholds, flags overdue.",
    )
    cadence_parser.add_argument(
        "--output", default="output/editorial-cadence.md",
        help="Output path for the Markdown dashboard (default: "
             "output/editorial-cadence.md). A .json sidecar is written alongside.",
    )
    cadence_parser.add_argument(
        "--strict", action="store_true",
        help="Exit non-zero if any surface is overdue (for CI cadence gating).",
    )
    # ---- end sprint 10: storylines ----

    refresh_savant_parser = subparsers.add_parser(
        "refresh-savant",
        help="Recompute the 13-metric percentile rows in team_savant_weekly for "
             "every profiled program (or a specific slug).",
    )
    refresh_savant_parser.add_argument(
        "--slug", nargs="*", default=None,
        help="Program slug(s) to refresh. Omit for all profiled programs.",
    )
    refresh_savant_parser.add_argument(
        "--season", type=int, default=None,
        help="Season to compute percentiles for. Default: the latest season "
             "that actually has team_game_advanced_stats rows (auto-detected). "
             "The old hardcoded 2024 default wrote 0 rows because the advanced-"
             "stats table is 2025-only as of 2026-06.",
    )

    refresh_arc_parser = subparsers.add_parser(
        "refresh-season-arc",
        help="Populate team_season_arc (2014+ per-team-season rows) for every "
             "profiled program.",
    )
    refresh_arc_parser.add_argument(
        "--slug", nargs="*", default=None,
        help="Program slug(s) to refresh. Omit for all profiled programs.",
    )
    refresh_arc_parser.add_argument(
        "--latest-season", type=int, default=2025,
        help="Season marked is_current. Default: 2025.",
    )

    refresh_rivalry_parser = subparsers.add_parser(
        "refresh-rivalry",
        help="Refresh team_rivalry_meetings head-to-head rows for each profiled "
             "program's Tier-1 rivalry (from profile frontmatter).",
    )
    refresh_rivalry_parser.add_argument(
        "--slug", nargs="*", default=None,
        help="Program slug(s) to refresh. Omit for all profiled programs.",
    )

    render_all_team_parser = subparsers.add_parser(
        "render-team-pages",
        help="Render every real FBS team page without a full "
             "build-site cycle. Convenience for iteration on the team_pages module.",
    )
    render_all_team_parser.add_argument(
        "--output-dir", default="output/site/teams",
        help="Output directory (default: output/site/teams).",
    )
    render_all_team_parser.add_argument(
        "--date", default=None,
        help="Override 'today' as YYYY-MM-DD for state resolution (testing).",
    )
    render_all_team_parser.add_argument(
        "--season", type=int, default=None,
        help="Override season.",
    )
    render_all_team_parser.add_argument(
        "--profiled-only", action="store_true",
        help="Render only hand-authored profiles/*.md pages.",
    )

    render_era_parser = subparsers.add_parser(
        "render-era-page",
        help="Render the CFP-era page (WS-07) for one or more programs to "
             "output/site/programs/<slug>/era/cfp/index.html.",
    )
    render_era_parser.add_argument(
        "slug", nargs="+", help="Program slug(s), e.g. alabama georgia",
    )
    render_era_parser.add_argument(
        "--output-dir", default="output/site/programs",
        help="Base programs directory (default: output/site/programs).",
    )
    render_era_parser.add_argument(
        "--end-season", type=int, default=2025,
        help="Last season to include in the era (default: 2025).",
    )

    simulate_game_parser = subparsers.add_parser(
        "simulate-game",
        help="Simulate a finished game end-to-end against a mock fixture. "
             "Sprint 6 §4 — used for offseason rehearsal of live-gameday mode.",
    )
    simulate_game_parser.add_argument(
        "--home", required=True, help="Home team slug (e.g. alabama)",
    )
    simulate_game_parser.add_argument(
        "--away", required=True, help="Away team slug (e.g. auburn)",
    )
    simulate_game_parser.add_argument(
        "--final-home", type=int, default=None, help="Final home score",
    )
    simulate_game_parser.add_argument(
        "--final-away", type=int, default=None, help="Final away score",
    )
    simulate_game_parser.add_argument(
        "--fixture", default=None,
        help="Path to a mock fixture JSON. When set, scalar args (final-home, "
             "final-away, pre-game-spread-home) may be omitted — fixture wins.",
    )
    simulate_game_parser.add_argument(
        "--wp-curve", default=None, help="Standalone WP timeseries JSON file",
    )
    simulate_game_parser.add_argument(
        "--events-log", default=None, help="Standalone events-log JSON file",
    )
    simulate_game_parser.add_argument(
        "--pre-game-spread-home", type=float, default=None,
        help="Pre-game spread, home perspective. Negative = home favored.",
    )
    simulate_game_parser.add_argument(
        "--persist", action="store_true",
        help="Keep the simulated games_live row after running (default deletes).",
    )
    simulate_game_parser.add_argument(
        "--output-dir", default="output/site/teams",
        help="Where the rendered HTML lands (default: output/site/teams).",
    )
    simulate_game_parser.add_argument(
        "--narrative-mode", default="template",
        choices=("template", "claude", "claude-code"),
        help="State-of-team narrative mode (default: template, no LLM cost).",
    )
    simulate_game_parser.add_argument(
        "--chronicle-mode", default="template",
        choices=("template", "auto", "sonnet", "opus"),
        help="Chronicle game-edition mode (default: template, no LLM cost).",
    )
    simulate_game_parser.add_argument(
        "--season", type=int, default=None, help="Override season year",
    )
    simulate_game_parser.add_argument(
        "--week", type=int, default=None, help="Override week",
    )
    simulate_game_parser.add_argument(
        "--with-cadence", action="store_true",
        help="Also enqueue + drain the post-game render cadence (T+5..T+45). "
             "Exercises games_live_render_queue end-to-end against the fixture.",
    )

    # ----- Sprint 11 — The Canon -----
    canon_seed_parser = subparsers.add_parser(
        "seed-canon-metadata",
        help="Seed the 3 canon_lists rows (idempotent). "
             "Sprint 11 §Phase 1.",
    )

    canon_gen_parser = subparsers.add_parser(
        "generate-canon-list",
        help="Generate one Canon list end-to-end: editorial entries from "
             "seed_authored, cohort splits, rank deltas, voice-validator pass. "
             "Sprint 11.",
    )
    canon_gen_parser.add_argument(
        "--list", required=True,
        help="Canon list slug (the-100-best-players-cfp-era, "
             "the-50-most-defining-games-cfp-era, "
             "the-25-best-coaching-hires-2020s).",
    )
    canon_gen_parser.add_argument(
        "--year", type=int, default=2026,
        help="Edition year (default: 2026).",
    )

    canon_render_parser = subparsers.add_parser(
        "render-canon",
        help="Render one Canon list (per-list page + per-entry pages). "
             "Sprint 11.",
    )
    canon_render_parser.add_argument(
        "--list", required=True, help="Canon list slug.",
    )
    canon_render_parser.add_argument(
        "--output-dir", default="output/site",
        help="Output root (default: output/site).",
    )

    canon_render_all_parser = subparsers.add_parser(
        "render-canon-all",
        help="Render the Canon index + every list + every per-entry page. "
             "Sprint 11.",
    )
    canon_render_all_parser.add_argument(
        "--output-dir", default="output/site",
        help="Output root (default: output/site).",
    )

    process_queue_parser = subparsers.add_parser(
        "process-render-queue",
        help="Drain pending render jobs from games_live_render_queue. "
             "Sprint 6 §1.3 — fires the T+5/15/.../45 post-game cadence.",
    )
    process_queue_parser.add_argument(
        "--output-dir", default="output/site/teams",
        help="Where rendered HTML lands (default: output/site/teams).",
    )
    process_queue_parser.add_argument(
        "--max-jobs", type=int, default=50,
        help="Max jobs to process per tick (default: 50).",
    )
    process_queue_parser.add_argument(
        "--summary", action="store_true",
        help="Print queue counts by status and exit (no work done).",
    )

    gen_hs_parser = subparsers.add_parser(
        "generate-historical-seasons",
        help="Populate team_historical_seasons — flagship authored seasons "
             "overwrite template fallback; subsequent Opus runs overwrite those.",
    )
    gen_hs_parser.add_argument(
        "--slug", nargs="*", default=None,
        help="Program slug(s). Omit for all profiled programs.",
    )
    gen_hs_parser.add_argument(
        "--force-template", action="store_true",
        help="Skip authored content; write template fallback for every season.",
    )

    render_hs_parser = subparsers.add_parser(
        "render-historical-seasons",
        help="Render output/site/teams/<slug>/seasons/<year>.html for every "
             "(slug, year) with a team_season_arc row.",
    )
    render_hs_parser.add_argument(
        "--slug", nargs="*", default=None,
        help="Program slug(s). Omit for all profiled programs.",
    )
    render_hs_parser.add_argument(
        "--output-dir", default="output/site/teams",
        help="Output root (default: output/site/teams).",
    )

    # Sprint 9 — Editions framework registrations.
    from cfb_rankings.editions.cli import register_edition_subcommands
    register_edition_subcommands(subparsers)

    # =========================================================================
    # MERGE ZONE — Sprint 13 Receipts subcommands. Concurrent sprints adding
    # commands should append below this block (not interleave) so merges stay
    # trivial. See CLAUDE_CODE_RECEIPTS_AND_LONG_SHOTS.md.
    # =========================================================================

    extract_pc_parser = subparsers.add_parser(
        "extract-predictive-claims",
        help="Sprint 13: scan conversation_documents for predictive claims, "
             "extract via Haiku → Sonnet pipeline, persist to predictive_claims.",
    )
    extract_pc_parser.add_argument("--days", type=int, default=365)
    extract_pc_parser.add_argument(
        "--sources", default=None,
        help="Comma-separated source_name values to filter (e.g. reddit,bluesky).",
    )
    extract_pc_parser.add_argument("--limit-docs", type=int, default=None)
    extract_pc_parser.add_argument("--haiku-batch", type=int, default=25)
    extract_pc_parser.add_argument(
        "--offline", action="store_true",
        help="Force offline stub mode (no Anthropic API calls).",
    )

    consensus_parser = subparsers.add_parser(
        "load-historical-consensus",
        help="Sprint 13: populate historical_consensus_snapshots from existing "
             "game_lines, official_rankings, power_ratings_weekly, and corpus "
             "aggregate signals.",
    )
    consensus_parser.add_argument(
        "--kind", choices=["all", "vegas", "polls", "sp_plus", "polymarket", "corpus"],
        default="all",
    )

    surprise_parser = subparsers.add_parser(
        "compute-surprise-index",
        help="Sprint 13: compute Surprise Index for predictive_claims.",
    )
    surprise_parser.add_argument(
        "--all-unscored", action="store_true",
        help="Recompute every claim with NULL surprise_index (default).",
    )
    surprise_parser.add_argument(
        "--claim-id", type=int, default=None,
        help="Compute only for a single claim id.",
    )

    resolve_parser = subparsers.add_parser(
        "resolve-outcomes",
        help="Sprint 13: resolve outcomes for predictive claims whose window has closed.",
    )
    resolve_parser.add_argument(
        "--window-end-before", default=None,
        help="ISO date (YYYY-MM-DD). Default: process all unresolved.",
    )

    best_calls_parser = subparsers.add_parser(
        "generate-best-calls",
        help="Sprint 13: generate the annual 'Best Calls of <year>' canonical list.",
    )
    best_calls_parser.add_argument("--year", type=int, required=True)
    best_calls_parser.add_argument("--n", type=int, default=25)
    best_calls_parser.add_argument("--opus-top", type=int, default=3)

    source_profiles_parser = subparsers.add_parser(
        "recompute-source-profiles",
        help="Sprint 13: recompute source_profiles aggregates + bios.",
    )
    source_profiles_parser.add_argument("--min-takes", type=int, default=3)
    source_profiles_parser.add_argument("--top-n", type=int, default=50)

    render_receipts_parser = subparsers.add_parser(
        "render-receipts",
        help="Sprint 13: render output/site/receipts/ — landing, annual lists, source profiles.",
    )

    # END MERGE ZONE — Sprint 13

    # =========================================================================
    # MERGE ZONE — Sprint 14: The Daily subcommands. Concurrent sprints adding
    # commands should append below this block. See CLAUDE_CODE_THE_DAILY.md.
    # =========================================================================
    # ---- sprint 14: daily ----

    generate_daily_parser = subparsers.add_parser(
        "generate-daily",
        help="Sprint 14: run input selector + LLM synthesis for a Daily edition. "
             "Persists to daily_editions + daily_takes.",
    )
    generate_daily_parser.add_argument(
        "--date", default=None,
        help="Edition date YYYY-MM-DD (default: today ET).",
    )

    render_daily_parser = subparsers.add_parser(
        "render-daily",
        help="Sprint 14: render HTML from persisted Daily edition rows.",
    )
    render_daily_parser.add_argument(
        "--date", default=None,
        help="Edition date YYYY-MM-DD (default: today ET).",
    )
    render_daily_parser.add_argument(
        "--output-dir", default=None,
        help="Override output directory (default: output/site/daily/).",
    )

    daily_history_parser = subparsers.add_parser(
        "daily-history",
        help="Sprint 14: print last N Daily editions with status + take count.",
    )
    daily_history_parser.add_argument(
        "--limit", type=int, default=10,
        help="Number of editions to show (default: 10).",
    )

    # END MERGE ZONE — Sprint 14

    # =========================================================================
    # MERGE ZONE — Sprint 15 Reaction Story subcommands. Concurrent sprints
    # should append below this block. See CLAUDE_CODE_THE_REACTION_STORY.md.
    # =========================================================================

    check_triggers_parser = subparsers.add_parser(
        "reactions-check-triggers",
        help="Sprint 15: scan recent Wire entries for Reaction Story triggers.",
    )
    check_triggers_parser.add_argument(
        "--hours", type=int, default=24,
        help="Lookback window in hours (default: 24).",
    )
    check_triggers_parser.add_argument(
        "--force-trigger", type=int, default=None, dest="force_trigger",
        metavar="WIRE_ID",
        help="Force-trigger a specific wire_id regardless of thresholds.",
    )
    check_triggers_parser.add_argument(
        "--auto", action="store_true",
        help="Auto-generate + render reaction stories for all triggered candidates.",
    )
    check_triggers_parser.add_argument(
        "--batch", default="auto",
        choices=["auto", "on", "off"],
        help=(
            "Sprint v5-1.5c: use Anthropic Message Batches API (50%% off + "
            "1h prompt caching) when running --auto across multiple triggered "
            "events. 'auto' (default): batch ON for >=2 events, OFF for 1. "
            "'on'/'off' force either path. Has no effect without --auto."
        ),
    )

    generate_reaction_parser = subparsers.add_parser(
        "generate-reaction",
        help="Sprint 15: run cohort divergence + synthesis for a known trigger.",
    )
    generate_reaction_parser.add_argument("--slug", required=True, help="Story slug.")
    generate_reaction_parser.add_argument(
        "--wire-id", type=int, required=True, dest="wire_id",
        help="Wire entry id to generate from.",
    )

    render_reactions_parser = subparsers.add_parser(
        "render-reactions",
        help="Sprint 15: render reaction story pages to output/site/reactions/.",
    )
    render_reactions_parser.add_argument(
        "--slug", default=None,
        help="Render one specific story slug. Omit to render all published stories.",
    )

    reactions_history_parser = subparsers.add_parser(
        "reactions-history",
        help="Sprint 15: print recent reaction stories.",
    )
    reactions_history_parser.add_argument(
        "--limit", type=int, default=20,
        help="Number of recent stories to show (default: 20).",
    )

    # END MERGE ZONE — Sprint 15

    # ---- Sprint 12: The Wire CLI surface ----
    # The wire-daily GitHub Actions workflow references these three commands,
    # but they were never wired up. Added so the workflow can run as designed.
    wire_ingest_parser = subparsers.add_parser(
        "wire-ingest",
        help="Sprint 12: ingest recent CFBD actions into wire_entries "
             "(transfers, coaching changes, recruiting commits).",
    )
    wire_ingest_parser.add_argument("--days", type=int, default=7,
        help="Lookback window in days (default: 7).")
    wire_ingest_parser.add_argument("--target-count", type=int, default=60,
        help="Approximate target row count after ingest (default: 60).")

    wire_editorial_parser = subparsers.add_parser(
        "wire-generate-editorial",
        help="Sprint 12: backfill why_it_matters / impact_label on wire_entries "
             "rows that don't have them. Existing copy is preserved unless "
             "--overwrite is passed.",
    )
    wire_editorial_parser.add_argument("--days", type=int, default=14,
        help="Lookback window in days (default: 14).")
    wire_editorial_parser.add_argument("--overwrite", action="store_true",
        help="Overwrite existing editorial fields (use with care).")
    wire_editorial_parser.add_argument(
        "--batch", default="off",
        choices=["auto", "on", "off"],
        help=(
            "Sprint v5-1.5c: when 'on' (or 'auto' with >=2 uncovered rows), "
            "run the LLM-backed batch path generate_uncovered_rows_batch on "
            "wire rows without authored captions (50%% off + 1h cache). "
            "Default is 'off' — keep the deterministic templated factual "
            "fallback that ships today; the LLM path activates gated on the "
            "Sprint v5-2 quality-loop validator work."
        ),
    )

    render_wire_parser = subparsers.add_parser(
        "render-wire",
        help="Sprint 12: render /wire/index.html + monthly archive pages "
             "and patch the homepage Wire <tbody>.",
    )
    render_wire_parser.add_argument("--days", type=int, default=30,
        help="Days of entries to show on the wire index (default: 30).")
    render_wire_parser.add_argument("--limit", type=int, default=8,
        help="Number of entries to patch into the homepage Wire panel "
             "(default: 8).")
    render_wire_parser.add_argument("--homepage-path", default=None,
        help="Override homepage path (default: output/site/index.html).")
    render_wire_parser.add_argument("--skip-homepage", action="store_true",
        help="Skip the homepage Wire <tbody> patch — render /wire/ only.")

    # ---- Sprint v5-1 Day 4 follow-up: S3 Portal Heat Index ----
    # DESIGN_AUDIT_2026_05_15_v5_4.md Part 4 §S3.
    # Renders /portal-heat/index.html from `portal_moves` (populated by
    # wire/ingestion.py Adapter 1). DB-tolerant: produces an empty-state
    # page when no rows are in the window.
    refresh_portal_heat_parser = subparsers.add_parser(
        "refresh-portal-heat",
        help="S3 surface: render /portal-heat/ from portal_moves "
             "(Top-25 programs by net delta talent).",
    )
    refresh_portal_heat_parser.add_argument(
        "--days", type=int, default=14,
        help="Lookback window in days (default: 14).",
    )
    refresh_portal_heat_parser.add_argument(
        "--output-dir", default=None,
        help="Override output dir (default: output/site/portal-heat).",
    )

    # ---- Sprint 8.5: Pulse follow-ups ----
    prepare_pulse_parser = subparsers.add_parser(
        "prepare-pulse",
        help="Sprint 8.5: extract themes + generate ledes for top entities. "
             "Writes to team_pulse_cache and conference_themes tables.",
    )
    prepare_pulse_parser.add_argument(
        "--entity", default=None,
        help="Single entity slug to run (e.g. 'alabama'). Omit to run all top-15 entities.",
    )
    prepare_pulse_parser.add_argument(
        "--type", dest="entity_type", default="team",
        choices=["team", "conference", "player"],
        help="Entity type (default: team).",
    )
    prepare_pulse_parser.add_argument(
        "--tier", default=None, choices=["full", "partial"],
        help="Force tier override. Default: auto-detect from top-entity lists.",
    )
    prepare_pulse_parser.add_argument(
        "--batch", default="auto",
        choices=["auto", "on", "off"],
        help=(
            "Sprint v5-1.5c: use Anthropic Message Batches API (50%% off + "
            "1h prompt caching) for Stage-2 themes + lede emission. "
            "'auto' (default): batch ON for >=2 entities, OFF for 1. "
            "'on'/'off' force either path. The sync per-entity path remains "
            "for single-entity --entity invocations."
        ),
    )

    render_conf_pulse_parser = subparsers.add_parser(
        "render-conferences-pulse",
        help="Sprint 8.5: render conference Pulse sections to output/site/conferences/.",
    )
    render_conf_pulse_parser.add_argument(
        "--all", dest="all_conferences", action="store_true",
        help="Render all 11 conferences.",
    )
    render_conf_pulse_parser.add_argument(
        "--slug", default=None,
        help="Single conference slug to render.",
    )
    render_conf_pulse_parser.add_argument(
        "--output-dir", default="output/site/conferences",
        help="Output directory.",
    )

    render_the_room_parser = subparsers.add_parser(
        "render-the-room",
        help="Sprint 8.5: generate Player Pulse v2 (The Room) for top-N players.",
    )
    render_the_room_parser.add_argument(
        "--top", type=int, default=15,
        help="Number of top players by velocity to generate (default: 15).",
    )

    classify_player_sentiment_parser = subparsers.add_parser(
        "classify-player-sentiment",
        help="Sprint 8.5: Haiku-classify unlabelled player conversation targets.",
    )
    classify_player_sentiment_parser.add_argument(
        "--limit", type=int, default=None,
        help="Max rows to classify (omit = all unlabelled).",
    )
    classify_player_sentiment_parser.add_argument(
        "--dry-run", action="store_true",
        help="Count unlabelled rows without classifying.",
    )

    # -------------------------------------------------------------------------
    # Sprint 16: The Mailbag — fan submission editorial
    # -------------------------------------------------------------------------
    mailbag_seed_parser = subparsers.add_parser(
        "mailbag-seed-submissions",
        help="Sprint 16: Seed N representative questions for Mailbag bootstrapping.",
    )
    mailbag_seed_parser.add_argument(
        "--n", type=int, default=5,
        help="Number of seed questions to plant (default: 5, max: 7).",
    )

    mailbag_curate_parser = subparsers.add_parser(
        "mailbag-curate-submissions",
        help="Sprint 16: Select 3–5 queued submissions for a Mailbag edition.",
    )
    mailbag_curate_parser.add_argument(
        "--edition", type=str, default=None,
        help="Edition slug (e.g. 2026-w17). Defaults to current ISO week.",
    )
    mailbag_curate_parser.add_argument(
        "--max", type=int, default=5, dest="max_answers",
        help="Maximum answers per edition (default: 5).",
    )

    mailbag_gen_parser = subparsers.add_parser(
        "mailbag-generate-answers",
        help="Sprint 16: Generate corpus-synthesis answers for a curated Mailbag edition.",
    )
    mailbag_gen_parser.add_argument(
        "--edition", type=str, default=None,
        help="Edition slug. Defaults to current ISO week.",
    )
    mailbag_gen_parser.add_argument(
        "--batch", default="auto",
        choices=["auto", "on", "off"],
        help=(
            "Sprint v5-1.5c: use Anthropic Message Batches API (50%% off + "
            "1h prompt caching). 'auto' (default): batch ON when >=2 curated "
            "questions, OFF for a single-question edition. 'on'/'off' force "
            "either path. The sync path remains available for low-volume "
            "interactive runs."
        ),
    )

    render_mailbag_parser = subparsers.add_parser(
        "render-mailbag",
        help="Sprint 16: Render Mailbag HTML pages (edition + archive + submit form).",
    )
    render_mailbag_parser.add_argument(
        "--edition", type=str, default=None,
        help="Render only this edition slug. Omit to render all.",
    )

    mailbag_history_parser = subparsers.add_parser(
        "mailbag-history",
        help="Sprint 16: Print recent Mailbag editions.",
    )
    mailbag_history_parser.add_argument(
        "--limit", type=int, default=10,
        help="Number of editions to show (default: 10).",
    )

    coaching_fetch_parser = subparsers.add_parser(
        "coaching-fetch-news",
        help="Sprint v5-1 Day 4: pull Footballscoop RSS + 247Sports coaching "
             "tracker into coaching_changes (+ wire_entries).",
    )
    coaching_fetch_parser.add_argument(
        "--days", type=int, default=7,
        help="Only consider entries newer than N days (default: 7).",
    )

    # ----------------------------------------------------------------
    # Sprint v5-3 owner Interrupt 2 — quality-loop guardrail visibility.
    # ----------------------------------------------------------------
    quality_loop_status_parser = subparsers.add_parser(
        "quality-loop-status",
        help="Print per-surface 24h spend + active LoopPattern + auto-disable "
             "status. Inspects surface_spend_events + surface_degrade_state.",
    )
    quality_loop_status_parser.add_argument(
        "--json", action="store_true",
        help="Emit the rows as a JSON array instead of a human-readable table.",
    )

    quality_loop_reenable_parser = subparsers.add_parser(
        "quality-loop-reenable",
        help="Clear the auto-disable degrade marker for a surface after human "
             "review. Re-enables the configured Pattern C flag.",
    )
    quality_loop_reenable_parser.add_argument(
        "surface", type=str,
        help="Surface key, e.g. 'tier1.edition_cover' or 'tier1.reaction_story'.",
    )

    # Chronicle Visuals — v3 visual-first deterministic SVG generation.
    # See CHRONICLE_QUALITY_PROPOSAL_v3.md + migrations/20260526_01_chronicle_visual_cache.sql.
    chronicle_visuals_parser = subparsers.add_parser(
        "generate-chronicle-visuals",
        help="Generate Chronicle Visuals (Statement Win Ladder, Returning Production X-Ray, "
             "Heisman Race Braid, Roster Replacement Grid) into chronicle_visual_cache.",
    )
    chronicle_visuals_parser.add_argument(
        "--season", type=int, required=True,
        help="Season year (e.g. 2024).",
    )
    chronicle_visuals_parser.add_argument(
        "--week", type=int, default=None,
        help="Optional week cutoff. If omitted, uses the most recent week.",
    )
    chronicle_visuals_parser.add_argument(
        "--slug", type=str, default=None,
        help="Limit to a single team slug. If omitted, runs across all active FBS teams.",
    )
    chronicle_visuals_parser.add_argument(
        "--visual", type=str, default=None,
        help="Limit to a single visual id (e.g. statement_win_ladder, "
             "returning_production_xray, heisman_race_braid, roster_replacement_grid).",
    )
    chronicle_visuals_parser.add_argument(
        "--force", action="store_true",
        help="Bypass cache lookup and regenerate.",
    )
    chronicle_visuals_parser.add_argument(
        "--limit-teams", type=int, default=None,
        help="Cap teams processed (useful for smoke tests).",
    )

    # =========================================================================
    # Team Preview — deterministic truth layer (Milestone A).
    # Spec: docs/specs/team-preview-implementation-plan-2026-05-26.md
    # =========================================================================
    def _add_preview_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--season", type=int, required=True,
                       help="Preview season year, e.g. 2026.")
        p.add_argument("--as-of", required=True,
                       help="As-of date YYYY-MM-DD (e.g. 2026-05-25).")
        p.add_argument("--slug", nargs="*", default=None,
                       help="Limit to specific team slugs (default: canonical FBS set).")

    tps_parser = subparsers.add_parser(
        "build-team-preview-snapshots",
        help="Team Preview: build deterministic team_preview_snapshot rows.",
    )
    _add_preview_common(tps_parser)

    spp_parser = subparsers.add_parser(
        "compute-season-path-projections",
        help="Team Preview: compute final-season-aware floor/base/ceiling records.",
    )
    _add_preview_common(spp_parser)

    rrs_parser = subparsers.add_parser(
        "build-roster-reload-snapshots",
        help="Team Preview: build transfer position flow + roster reload summary.",
    )
    _add_preview_common(rrs_parser)

    preview_layer_parser = subparsers.add_parser(
        "build-team-preview-layer",
        help="Team Preview: run all deterministic preview builders for publish.",
    )
    preview_layer_parser.add_argument(
        "--season", type=int, default=None,
        help="Preview season year. Defaults to the current calendar year.",
    )
    preview_layer_parser.add_argument(
        "--as-of", default=None,
        help="As-of date YYYY-MM-DD. Defaults to today's date.",
    )
    preview_layer_parser.add_argument(
        "--slug", nargs="*", default=None,
        help="Limit to specific team slugs (default: canonical FBS set).",
    )
    preview_layer_parser.add_argument(
        "--allow-empty", action="store_true",
        help="Exit successfully even if no preview rows were written.",
    )

    gen_preview_claims_parser = subparsers.add_parser(
        "generate-team-preview-claims",
        help="Team Preview: generate evidence-gated local-LLM preview claim cache rows.",
    )
    gen_preview_claims_parser.add_argument("--season", type=int, required=True)
    gen_preview_claims_parser.add_argument("--as-of", required=True)
    gen_preview_claims_parser.add_argument("--slug", nargs="*", default=None)
    gen_preview_claims_parser.add_argument(
        "--allow-cloud", action="store_true",
        help="Permit Chronicle router cloud fallback. Default is local-only.",
    )
    gen_preview_claims_parser.add_argument(
        "--json", action="store_true",
        help="Emit machine-readable generation report.",
    )

    preview_llm_status_parser = subparsers.add_parser(
        "team-preview-llm-status",
        help="Team Preview: show local LLM backend status via the Chronicle router.",
    )
    preview_llm_status_parser.add_argument(
        "--allow-cloud", action="store_true",
        help="Include cloud fallback routes in status output.",
    )

    bowl_parser = subparsers.add_parser(
        "import-bowl-record-ledger",
        help="Team Preview: import an all-time bowl-record seed (CSV/JSON).",
    )
    bowl_parser.add_argument("--source", required=True,
                             help="Path to a bowl-ledger seed CSV or JSON.")
    bowl_parser.add_argument("--as-of", default=None,
                             help="Retrieval date YYYY-MM-DD (stamped when seed omits it).")

    audit_parser = subparsers.add_parser(
        "audit-team-preview-readiness",
        help="Team Preview: report missing vs low-confidence preview data per team.",
    )
    _add_preview_common(audit_parser)
    audit_parser.add_argument("--json", action="store_true",
                              help="Emit the full per-team report as JSON.")

    # WS-09 — calibration prediction ledger (D-015).
    ledger_parser = subparsers.add_parser(
        "prediction-ledger",
        help="WS-09: record/resolve/summarize the prediction calibration ledger.",
    )
    ledger_parser.add_argument(
        "--action", required=True,
        choices=["record-archetypes", "record-season-wins", "resolve", "summary"],
        help="record-archetypes / record-season-wins: log predictions; "
             "resolve: grade due predictions; summary: print calibration aggregate.",
    )
    ledger_parser.add_argument("--season", type=int, default=None,
                               help="Season the prediction window is for (record actions).")
    ledger_parser.add_argument("--model-id", default=None,
                               help="Filter summary to one model_id.")
    ledger_parser.add_argument("--kind", default=None,
                               help="Filter summary/resolve to one prediction_kind.")
    ledger_parser.add_argument("--last-n", type=int, default=None,
                               help="Summary over the most recent N resolved predictions.")
    ledger_parser.add_argument("--json", action="store_true",
                               help="Emit the summary as JSON.")

    return parser


def main() -> None:
    args = build_parser().parse_args()

    # resolve-week is pure date math (no DB/config needed) — handle it first so
    # it stays fast and usable even before a DB exists. Emits the canonical week
    # identity that daily_ingest.ps1 feeds to every producer + consumer.
    if args.command == "resolve-week":
        from cfb_rankings.common.week import resolve_week
        wk = resolve_week(args.as_of)
        if getattr(args, "emit_json", False):
            import json as _json
            print(_json.dumps(wk.as_dict()))
        else:
            print(f"season_year = {wk.season_year}")
            print(f"week        = {wk.week}")
            print(f"week_start  = {wk.week_start}")
            print(f"iso_key     = {wk.iso_key}")
            print(f"in_season   = {wk.in_season}")
        return

    # data-health opens the DB READ-ONLY through the orchestrator and never
    # mutates — handle it before the read-write Database() setup so it stays a
    # pure read-only gate (mirrors resolve-week's pre-DB short-circuit).
    if args.command == "data-health":
        import sys as _sys
        from pathlib import Path as _Path
        _scripts = _Path(__file__).resolve().parents[2] / "scripts"
        if str(_scripts) not in _sys.path:
            _sys.path.insert(0, str(_scripts))
        import verify_data_health as _dh
        # --html is nargs="?" here too: None = omit; "" = bare flag (use the
        # script's default gitignored path); any other value = explicit PATH.
        _html = getattr(args, "html", None)
        _html_argv = (
            [] if _html is None
            else ["--html"] if _html == ""
            else ["--html", _html]
        )
        rc = _dh.main(
            (["--json"] if getattr(args, "json", False) else [])
            + (["--strict"] if getattr(args, "strict", False) else [])
            + _html_argv
            + (["--snapshot"] if getattr(args, "snapshot", False) else [])
            + (["--open-issue"] if getattr(args, "open_issue", False) else [])
            + (["--dry-run"] if getattr(args, "dry_run", False) else [])
            + (["--season", str(args.season)] if getattr(args, "season", None) is not None else [])
        )
        raise SystemExit(rc)

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

    if args.command == "compute-story-cards":
        from cfb_rankings.player_pages.story_card import compute_story_cards
        tiers = (
            tuple(t.strip() for t in args.tier.split(",") if t.strip())
            if args.tier else ("S", "T1")
        )
        counts = compute_story_cards(
            db, args.season, players=args.players, tiers=tiers,
            limit=getattr(args, "limit", None),
            force=bool(getattr(args, "force", False)),
            select=getattr(args, "select", None),
        )
        # counts is a dict of per-outcome tallies — print a clean summary.
        print(
            f"compute-story-cards {args.season}: "
            f"tiers={','.join(tiers)} force={bool(getattr(args, 'force', False))} "
            f"select={counts.get('select', 'default')} "
            f"candidates={counts.get('candidates', 0)} "
            f"considered={counts.get('considered', 0)} "
            f"generated={counts.get('generated', 0)} "
            f"skipped={counts.get('skipped', 0)} "
            f"fell_back={counts.get('fell_back', 0)} "
            f"deterministic={counts.get('deterministic', 0)} "
            f"errors={counts.get('errors', 0)}"
        )
        return

    if args.command == "eval-story-cards":
        # DEV/EVAL quality tool (doc 59 §10/§14.7). Read-only on prod data; no
        # DB/site writes. Missed-Gold critic + deterministic Faithfulness gate.
        from cfb_rankings.player_pages.card_eval import run_card_eval
        report = run_card_eval(
            db,
            players=getattr(args, "players", None),
            top_n=getattr(args, "top_n", 12),
            judge=getattr(args, "judge", "mistral"),
            season=getattr(args, "season", None),
            upcoming_season=getattr(args, "upcoming_season", 2026),
            print_report=not getattr(args, "emit_json", False),
        )
        if getattr(args, "emit_json", False):
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    if args.command == "seed-source-registry":
        from cfb_rankings.ingest.fanintel_seeds import seed_source_registry
        result = seed_source_registry(db)
        print(f"source_registry: inserted={result['inserted']} updated={result['updated']} total={result['total']}")
        return

    if args.command == "set-conferences":
        import json as _json
        from pathlib import Path as _Path
        p = _Path(args.seed)
        if not p.exists():
            print(f"ABORT: seed not found: {p}")
            return
        doc = _json.loads(p.read_text(encoding="utf-8"))
        conf_map = doc.get("conferences", doc) if isinstance(doc, dict) else {}
        updated = 0
        for slug, conf in conf_map.items():
            if slug.startswith("_") or not conf:
                continue
            row = db.query_one("select team_id from teams where slug = :s", {"s": slug})
            if not row:
                print(f"  (no team for slug {slug!r}; skipped)")
                continue
            db.execute(
                "update priority_teams set conference = :c, updated_at_utc = datetime('now') "
                "where team_id = :t",
                {"c": conf, "t": row["team_id"]},
            )
            updated += 1
        print(f"set-conferences: updated {updated} teams from {p.name}")
        return

    if args.command == "import-team-sources":
        import csv as _csv
        from pathlib import Path as _Path
        seed_path = _Path(args.csv)
        if not seed_path.exists():
            print(f"ABORT: seed CSV not found: {seed_path}")
            return
        seed_rows = list(_csv.DictReader(seed_path.open(encoding="utf-8")))
        inserted = updated = 0
        for r in seed_rows:
            try:
                tid = int(r["team_id"])
            except (KeyError, TypeError, ValueError):
                continue
            existing = db.query_one(
                "select rank_priority from priority_teams where team_id = :t", {"t": tid})
            tier = int(r["collection_tier"]) if (r.get("collection_tier") or "").strip() else None
            params = {
                "team_id": tid,
                # New teams get a tier-grouped rank after the curated 1-21; existing
                # teams keep their hand-set rank_priority.
                "rank": existing["rank_priority"] if existing else (tier or 3) * 100,
                "sub": (r.get("reddit_team_sub") or "").strip() or None,
                "mode": (r.get("reddit_mode") or "").strip() or None,
                "flair": (r.get("reddit_flair_filter") or "").strip() or None,
                "tier": tier,
                "gnews": (r.get("google_news_query") or "").strip() or None,
                "conf": (r.get("conference_2025") or r.get("conference") or "").strip() or None,
            }
            if args.dry_run:
                if existing:
                    updated += 1
                else:
                    inserted += 1
                continue
            db.execute(
                """
                insert into priority_teams (
                    team_id, rank_priority, reddit_team_sub, reddit_mode,
                    reddit_flair_filter, collection_tier, google_news_query,
                    conference, updated_at_utc
                ) values (
                    :team_id, :rank, :sub, :mode, :flair, :tier, :gnews, :conf,
                    datetime('now')
                )
                on conflict(team_id) do update set
                    collection_tier     = excluded.collection_tier,
                    reddit_mode         = excluded.reddit_mode,
                    reddit_flair_filter = excluded.reddit_flair_filter,
                    conference          = coalesce(excluded.conference, priority_teams.conference),
                    -- never clobber a hand-tuned value; only fill when empty
                    reddit_team_sub     = coalesce(nullif(priority_teams.reddit_team_sub, ''), excluded.reddit_team_sub),
                    google_news_query   = coalesce(nullif(priority_teams.google_news_query, ''), excluded.google_news_query),
                    updated_at_utc      = datetime('now')
                """,
                params,
            )
            if existing:
                updated += 1
            else:
                inserted += 1
        mode = "DRY-RUN" if args.dry_run else "APPLIED"
        print(f"import-team-sources [{mode}]: inserted={inserted} updated={updated} "
              f"csv_rows={len(seed_rows)} -> priority_teams now has "
              f"{db.query_one('select count(*) n from priority_teams')['n']} rows")
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

    if args.command == "verify-publish-readiness":
        # Phase-1 data-quality gate. Hand-rolled SQL assertions (db.query_all/query_one
        # rewrite %(x)s->:x and now()->CURRENT_TIMESTAMP; use :named params and
        # datetime('now', ...) -- never literally type now()). Exits 2 on hard-fail so
        # publish_to_vercel.ps1 aborts. WARN-level (the currently-empty Phase-2 tables)
        # only block under --strict / VERIFY_STRICT_MOOD=1.
        import os as _os
        import sys as _sys
        import json as _json
        from datetime import date as _date

        # Use the canonical resolver so the gate checks the EXACT (season, week,
        # iso_key) the daily producers/consumers write. (Before: these derived
        # the old raw season-week / calendar-ISO vocabularies and, mid-week,
        # checked week 42 / "2026-24" while the pipeline wrote 41 / "2025-41" ->
        # false WARNs, and false HARD-FAILs once --strict is on.)
        from cfb_rankings.common.week import resolve_week as _resolve_week
        _wk = _resolve_week()

        def _cur_season() -> int:
            return _wk.season_year

        def _cur_season_week() -> int:
            return _wk.week

        def _cur_iso_key() -> str:
            return _wk.iso_key

        strict = bool(getattr(args, "strict", False)) or _os.environ.get("VERIFY_STRICT_MOOD") == "1"
        hard_fails: list[str] = []
        warns: list[str] = []
        passes: list[str] = []

        def _hard(label: str, ok: bool, detail: str = "") -> None:
            if ok:
                passes.append(f"{label}: PASS")
            else:
                hard_fails.append(f"{label}: FAIL{(' -- ' + detail) if detail else ''}")

        def _soft(label: str, ok: bool, detail: str = "") -> None:
            if ok:
                passes.append(f"{label}: PASS")
            elif strict:
                hard_fails.append(f"{label}: FAIL (strict) -- {detail}")
            else:
                warns.append(f"{label}: WARN -- {detail}")

        def _n(sql: str, params: dict | None = None) -> int:
            row = db.query_one(sql, params or {})
            if not row:
                return 0
            return int(list(row.values())[0] or 0)

        # A. structural integrity (always hard-fail)
        try:
            ic = db.query_all("PRAGMA integrity_check")
            ic_ok = len(ic) == 1 and str(list(ic[0].values())[0]).lower() == "ok"
            _hard("integrity_check", ic_ok, "" if ic_ok else f"{len(ic)} problem row(s): {ic[:3]}")
            fk = db.query_all("PRAGMA foreign_key_check")
            _hard("foreign_key_check", len(fk) == 0, "" if not fk else f"{len(fk)} FK violation(s)")
        except Exception as exc:  # noqa: BLE001
            _hard("integrity pragmas", False, f"error: {exc}")

        # B. conversation_documents freshness + today's ingest (hard-fail)
        fdays = int(getattr(args, "freshness_days", 2))
        newest = db.query_one("select max(collected_at_utc) as ts from conversation_documents")
        newest_ts = newest["ts"] if newest else None
        fresh_n = _n("select count(*) as n from conversation_documents where collected_at_utc >= datetime('now', :w)",
                     {"w": f"-{fdays} day"})
        _hard(f"conversation_documents freshness (<= {fdays}d)", fresh_n > 0,
              f"newest collected_at_utc={newest_ts!r}; 0 rows in window")
        min_docs = int(getattr(args, "min_today_docs", 200))
        today_docs = _n("select count(*) as n from conversation_documents where collected_at_utc >= datetime('now','-1 day')")
        _hard(f"conversation_documents today-insert (>= {min_docs})", today_docs >= min_docs,
              f"only {today_docs} rows in last 24h")

        # C. coverage anomaly vs trailing 7d median (WARN-only; skip if thin baseline)
        per_day = db.query_all(
            "select substr(collected_at_utc,1,10) as d, count(*) as n from conversation_documents "
            "where collected_at_utc >= datetime('now','-8 day') and collected_at_utc < datetime('now','-1 day') "
            "group by d")
        baseline = sorted(int(r["n"]) for r in per_day if int(r["n"] or 0) > 0)
        if len(baseline) >= 3:
            mid = len(baseline) // 2
            median = baseline[mid] if len(baseline) % 2 else (baseline[mid - 1] + baseline[mid]) / 2
            _soft("conversation_documents coverage vs 7d median", median == 0 or today_docs >= 0.25 * median,
                  f"today={today_docs} vs 7d-median={median:.0f} (>75% drop -- a feed may be failing)")
        else:
            warns.append(f"conversation_documents coverage vs 7d median: SKIP (only {len(baseline)} baseline day(s))")

        # D. daily aggregate tables non-empty for the current period (WARN -> HARD under --strict)
        _soft("team_conversation_daily current-period rows",
              _n("select count(*) as n from team_conversation_daily where as_of_date >= date('now', :w)",
                 {"w": f"-{fdays} day"}) > 0, f"0 rows within {fdays}d")
        _soft("fanbase_mood_weekly current-week rows",
              _n("select count(*) as n from fanbase_mood_weekly where week_start_date = date('now','weekday 1','-7 day')") > 0,
              "0 rows for current week_start_date")
        _soft("fanbase_mood_weekly nonzero mood at newest week",
              _n("select count(*) as n from fanbase_mood_weekly where week_start_date = "
                 "(select max(week_start_date) from fanbase_mood_weekly) and mood_score is not null and mood_score <> 0") > 0,
              "all mood_score NULL/0 at newest week")
        _soft("team_week_conversation_features current season/week",
              _n("select count(*) as n from team_week_conversation_features where season_year = :s and week = :w",
                 {"s": _cur_season(), "w": _cur_season_week()}) > 0,
              f"0 rows for season={_cur_season()} week={_cur_season_week()}")
        _soft("team_cohort_week current ISO-week",
              _n("select count(*) as n from team_cohort_week where week = :wk", {"wk": _cur_iso_key()}) > 0,
              f"0 rows for week={_cur_iso_key()}")
        _soft("player_week_conversation_features current season/week",
              _n("select count(*) as n from player_week_conversation_features where season_year = :s and week = :w",
                 {"s": _cur_season(), "w": _cur_season_week()}) > 0,
              f"0 rows for season={_cur_season()} week={_cur_season_week()}")

        print("=" * 64)
        print(f"verify-publish-readiness  (strict={strict})")
        print("=" * 64)
        for line in passes:
            print("  [pass] " + line)
        for line in warns:
            print("  [WARN] " + line)
        for line in hard_fails:
            print("  [FAIL] " + line)
        print("-" * 64)
        print(f"  {len(passes)} pass | {len(warns)} warn | {len(hard_fails)} fail")
        if getattr(args, "emit_json", False):
            print(_json.dumps({"ok": not hard_fails, "strict": strict, "pass": passes,
                               "warn": warns, "fail": hard_fails,
                               "conv_docs_today": today_docs, "newest_collected_at_utc": newest_ts}, indent=2))
        if hard_fails:
            print("\nABORT: data-quality gate failed. Publish must NOT proceed.")
            _sys.exit(2)
        print("\nOK: data-quality gate passed; safe to publish.")
        return

    # --------------------------------------------------------- team pages
    if args.command == "load-team-profiles":
        from cfb_rankings.team_pages.profile_loader import (
            load_profile, upsert_profile_to_db, PROFILES_DIR,
        )
        slugs = args.slug or [p.stem for p in sorted(PROFILES_DIR.glob("*.md"))]
        loaded = 0
        for slug in slugs:
            try:
                profile = load_profile(slug)
            except (FileNotFoundError, ValueError) as exc:
                print(f"  skip {slug}: {exc}")
                continue
            upsert_profile_to_db(db, profile)
            loaded += 1
            print(f"  loaded {slug} (tier {profile.program_tier}, register {profile.voice_register})")
        print(f"load-team-profiles: {loaded}/{len(slugs)} profiles written")
        return

    if args.command == "generate-narratives":
        from cfb_rankings.team_pages.profile_loader import load_profile, PROFILES_DIR
        from cfb_rankings.team_pages.data import fetch_team_snapshot
        from cfb_rankings.team_pages.state_resolver import resolve_state
        from cfb_rankings.team_pages.narrative_generator import generate_state_of_team

        slugs = args.slug or [p.stem for p in sorted(PROFILES_DIR.glob("*.md"))]
        totals = {"prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0}
        for slug in slugs:
            try:
                profile = load_profile(slug)
            except FileNotFoundError:
                print(f"  skip {slug}: profile not found")
                continue
            try:
                snapshot = fetch_team_snapshot(db, slug, season_year=args.season)
            except LookupError as exc:
                print(f"  skip {slug}: {exc}")
                continue
            state = resolve_state(profile, snapshot)
            try:
                result = generate_state_of_team(
                    profile, snapshot, state,
                    mode=args.llm, claude_model=args.model,
                )
            except Exception as exc:
                print(f"  {slug} narrative error: {exc}")
                continue
            result.persist(db, snapshot.team_id, snapshot.season_year, state)
            totals["prompt_tokens"] += result.prompt_tokens
            totals["completion_tokens"] += result.completion_tokens
            totals["cost_usd"] += result.cost_usd
            preview = (result.body_md[:120] + "…") if len(result.body_md) > 120 else result.body_md
            print(f"  {slug} [{result.model_id}] {result.prompt_tokens}p/{result.completion_tokens}c tok ${result.cost_usd:.4f}")
            print(f"    {preview}")
        print(
            f"generate-narratives: programs={len(slugs)} "
            f"prompt_tok={totals['prompt_tokens']} "
            f"completion_tok={totals['completion_tokens']} "
            f"cost=${totals['cost_usd']:.4f}"
        )
        return

    if args.command == "generate-chronicle":
        from cfb_rankings.team_pages.profile_loader import load_profile, PROFILES_DIR
        from cfb_rankings.team_pages.data import fetch_team_snapshot
        from cfb_rankings.team_pages.state_resolver import resolve_state
        from cfb_rankings.team_pages.chronicle_generator import (
            generate_chronicle_for_team,
            generate_chronicle_for_teams_batch,
            BLUE_BLOODS,
        )
        from cfb_rankings.llm_runtime import CostMeter, CostCeilingExceeded

        slugs = args.slug or [p.stem for p in sorted(PROFILES_DIR.glob("*.md"))]
        totals = {"scanned": 0, "published": 0, "dropped": 0}
        NEW_STREAM_TYPES = ("anomaly", "moment", "flashpoint", "echo", "retroactive", "player_arc")

        # Pattern C: one CostMeter per CLI invocation. Across-team ceiling.
        # Sized for a full 17-program weekly profiled run (~$5 from
        # IMPLEMENTATION_PLAN.md Part 6.5 line item tier1.chronicle_profiled).
        # CostCeilingExceeded HALTS the run rather than racing past budget.
        cost_meter = CostMeter(
            ceiling_usd=10.0,
            label="cli.generate-chronicle",
        )

        # Batch-mode dispatcher: auto -> batch when >=2 slugs and model
        # isn't 'template' (template doesn't hit the LLM at all). Single-
        # team runs stay on the sync subprocess path for interactive UX.
        batch_choice = getattr(args, "batch", "auto")
        use_batch = (
            batch_choice == "on"
            or (batch_choice == "auto" and len(slugs) >= 2 and args.model != "template")
        )

        if use_batch:
            print(
                f"generate-chronicle: BATCH mode ({len(slugs)} programs, model={args.model})",
                flush=True,
            )
            # Pre-resolve all profiles + snapshots; collect into one batch plan.
            teams: list = []
            for slug in slugs:
                try:
                    profile = load_profile(slug)
                except FileNotFoundError:
                    print(f"  skip {slug}: profile not found")
                    continue
                try:
                    snapshot = fetch_team_snapshot(db, slug, season_year=args.season)
                except LookupError as exc:
                    print(f"  skip {slug}: {exc}")
                    continue
                teams.append((profile, snapshot))

            try:
                cards_by_slug = generate_chronicle_for_teams_batch(
                    db, teams,
                    model=args.model,
                    max_cards=args.top_k,
                    _meter=cost_meter,
                )
            except CostCeilingExceeded as exc:
                print(f"::error::CostMeter halted run: {exc}", flush=True)
                return 1
            # Persist using the same unpublish-then-publish pattern as the
            # sync path. Loop teams in submission order for stable logs.
            type_placeholders = ",".join(["?"] * len(NEW_STREAM_TYPES))
            for profile, snapshot in teams:
                slug = profile.slug
                cards = cards_by_slug.get(slug, [])
                with db.connection() as _c:
                    _c.execute(
                        f"update team_chronicle_observations set is_published = 0 "
                        f"where team_id = ? and season_year = ? "
                        f"  and card_type in ({type_placeholders})",
                        (snapshot.team_id, snapshot.season_year, *NEW_STREAM_TYPES),
                    )
                    _c.commit()
                state = resolve_state(profile, snapshot)
                for rank, card in enumerate(cards, start=1):
                    card.persist(db, snapshot.team_id, snapshot.season_year, rank, state.as_dict())
                type_summary = ", ".join(c.card_type for c in cards) or "(none survived)"
                print(f"  {slug}: published {len(cards)} cards — {type_summary}")
                totals["published"] += len(cards)
            print(
                f"generate-chronicle: done — programs={len(slugs)} "
                f"cards_published={totals['published']} (batch) "
                f"spent=${cost_meter.spent_usd:.4f} / ${cost_meter.ceiling_usd:.2f}"
            )
            return

        try:
            for slug in slugs:
                try:
                    profile = load_profile(slug)
                except FileNotFoundError:
                    print(f"  skip {slug}: profile not found")
                    continue
                try:
                    snapshot = fetch_team_snapshot(db, slug, season_year=args.season)
                except LookupError as exc:
                    print(f"  skip {slug}: {exc}")
                    continue
                state = resolve_state(profile, snapshot)
                print(f"[{slug}] model={args.model} blueblood={slug in BLUE_BLOODS}")
                cards = generate_chronicle_for_team(
                    db, profile, snapshot,
                    model=args.model,
                    max_cards=args.top_k,
                    parallel_workers=args.workers,
                    _meter=cost_meter,
                )
                # Unpublish prior rows ONLY for the 6 stream-driven types — leave
                # any other card_type (rivalry_posture, rivalry_stakes, savant_echo,
                # etc. from separate scripts) untouched.
                type_placeholders = ",".join(["?"] * len(NEW_STREAM_TYPES))
                db.execute(
                    f"update team_chronicle_observations set is_published = 0 "
                    f"where team_id = :tid and season_year = :s "
                    f"  and card_type in ({type_placeholders})",
                    {"tid": snapshot.team_id, "s": snapshot.season_year, **{}},
                ) if False else None  # placeholder — real exec below with tuple params
                # Use raw params since :placeholder won't bind tuple; fall through
                with db.connection() as _c:
                    _c.execute(
                        f"update team_chronicle_observations set is_published = 0 "
                        f"where team_id = ? and season_year = ? "
                        f"  and card_type in ({type_placeholders})",
                        (snapshot.team_id, snapshot.season_year, *NEW_STREAM_TYPES),
                    )
                    _c.commit()
                for rank, card in enumerate(cards, start=1):
                    card.persist(db, snapshot.team_id, snapshot.season_year, rank, state.as_dict())
                type_summary = ", ".join(c.card_type for c in cards) or "(none survived)"
                print(f"  {slug}: published {len(cards)} cards — {type_summary}")
                totals["published"] += len(cards)
        except CostCeilingExceeded as exc:
            print(f"::error::CostMeter halted run: {exc}", flush=True)
            return 1
        print(
            f"generate-chronicle: done — programs={len(slugs)} "
            f"cards_published={totals['published']} "
            f"spent=${cost_meter.spent_usd:.4f} / ${cost_meter.ceiling_usd:.2f}"
        )
        return

    if args.command == "render-team":
        from cfb_rankings.team_pages.renderer import render_team_page
        override_date = None
        if getattr(args, "date", None):
            override_date = date.fromisoformat(args.date)
        for slug in args.slugs:
            try:
                path = render_team_page(
                    db, slug, args.output_dir,
                    today=override_date, season_year=args.season,
                )
                print(f"  rendered {slug} -> {path}")
            except Exception as exc:
                print(f"  {slug} render failed: {exc}")
        return

    # ---- sprint 10: storylines (merge-zone marker) ----
    if args.command == "generate-thread-chapter":
        from cfb_rankings.storylines.seeds import iter_thread_metadata
        from cfb_rankings.storylines.chapter_authoring import (
            build_context_pack,
            build_prompt,
            parse_llm_chapter_response,
            append_chapter_to_seed,
            write_draft_scaffold,
        )
        from cfb_rankings.llm_runtime import generate_with_voice_check

        slug = args.thread
        meta = next((t for t in iter_thread_metadata() if t["thread_slug"] == slug), None)
        if not meta:
            print(f"unknown thread slug: {slug}")
            return

        next_n_row = db.query_one(
            "select coalesce(max(chapter_number), 0) + 1 as n "
            "from storyline_chapters where thread_slug = :slug",
            {"slug": slug},
        )
        next_n = int(next_n_row["n"]) if next_n_row else 1

        # Build context pack + prompt.
        context = build_context_pack(db, slug, meta, next_n)
        prompt = build_prompt(context)

        print(f"generate-thread-chapter: {slug} chapter {next_n}")
        print(f"  prior chapters in context: {len(context['prior_chapters'])}")
        print(f"  voice register source: {context['voice_register_source']}")

        # v5.3 row #10: storyline thread chapters are 800-1500w with required
        # prior-chapter callbacks + 3+ source citations + verbatim pull quote.
        # Cross-chapter coherence is exactly Opus's strength. Upgraded from
        # Sonnet 4.6 — the biggest single-line quality lift in the codebase.
        # Pattern E (continuity-grounded) wraps land in Sprint v5-4; this is
        # the Day-1 model bump while the loop infra is built.
        result = generate_with_voice_check(
            prompt,
            model="claude-opus-4-7",
            max_tokens=6000,
            max_retries=1,
        )

        print(f"  llm_runtime mode: {result['mode']}")
        print(
            f"  attempts: {result['attempts']}, "
            f"tokens: in={result['tokens_used']['input']} "
            f"out={result['tokens_used']['output']}"
        )
        print(f"  voice_validator_passed: {result['voice_validator_passed']}")

        # Branch: offline-stub fallback.
        if result["mode"] == "offline-stub":
            path = write_draft_scaffold(
                slug, meta, next_n,
                note="ANTHROPIC_API_KEY not set; --auto deferred to next live run.",
            )
            print(f"  draft scaffold written: {path}")
            print("  set ANTHROPIC_API_KEY and re-run for live generation.")
            return

        # Branch: live but voice failed.
        if not result["voice_validator_passed"]:
            path = write_draft_scaffold(
                slug, meta, next_n,
                llm_text=result["text"],
                violations=result["voice_violations"],
                note="Voice validator failed twice. Raw LLM output preserved below for review.",
            )
            print(f"  voice validator failed: {result['voice_violations']}")
            print(f"  draft (with raw response) written: {path}")
            return

        # Branch: live + voice-passed. Parse, append to seed, re-render.
        try:
            chapter_dict = parse_llm_chapter_response(
                result["text"],
                thread_slug=slug,
                chapter_number=next_n,
                meta=meta,
            )
        except Exception as exc:
            path = write_draft_scaffold(
                slug, meta, next_n,
                llm_text=result["text"],
                note=f"Could not parse LLM response: {exc}. Raw output preserved below.",
            )
            print(f"  parse error: {exc}")
            print(f"  draft (with raw response) written: {path}")
            return

        seed_path = append_chapter_to_seed(slug, chapter_dict)
        print(f"  appended chapter {next_n} to {seed_path}")

        if not getattr(args, "skip_render", False):
            from cfb_rankings.storylines.seed_loader import load_all_seeds
            from cfb_rankings.storylines import renderer as _stl_renderer
            seed_summary = load_all_seeds(db)
            _stl_renderer.render_all(db)
            print(f"  re-seeded: {seed_summary['total_chapters']} chapters total")
            print("  storylines re-rendered to output/site/storylines/")
        return

    if args.command == "render-storylines":
        from cfb_rankings.storylines.seed_loader import load_all_seeds
        from cfb_rankings.storylines import renderer as _stl_renderer
        if not args.no_seed:
            seed_result = load_all_seeds(db)
            print(f"seeded: {seed_result['threads_written']} threads, "
                  f"{seed_result['total_chapters']} chapters")
            for slug, n in sorted(seed_result["chapter_counts"].items()):
                print(f"  {slug:40s} {n} chapters")
        result = _stl_renderer.render_all(
            db,
            output_dir=args.output_dir,
            homepage_contract_path=args.contract_path,
        )
        print(f"rendered {result['thread_pages_written']} thread pages + index")
        print(f"  index: {result['index_written']}")
        print(f"  contract: {result['homepage_contract_written']}")
        return

    if args.command == "build-storyline-candidates":
        from cfb_rankings.storylines.candidate_queue import (
            populate_storyline_candidates,
            render_candidate_digest,
        )
        summary = populate_storyline_candidates(
            db, season_year=args.season, commit=args.commit
        )
        mode = "committed" if args.commit else "dry-run"
        print(
            f"storyline candidates ({mode}): {summary['candidates_ranked']} ranked "
            f"from {summary['arcs_scanned']} arcs, {summary['covered_count']} already "
            f"thread-covered, {summary['rows_written']} written"
        )
        for cid, score in summary["top"]:
            print(f"  {score:6.3f}  {cid}")
        if args.digest is not None:
            d = render_candidate_digest(db, season_year=args.season, output_path=args.digest)
            print(
                f"  digest: {d['md_path']} "
                f"({d['proposed']} proposed / {d['net_new']} net-new)"
            )
        return

    if args.command == "review-storyline-candidate":
        from cfb_rankings.storylines.candidate_queue import set_review_status
        found = set_review_status(db, args.candidate_id, args.status)
        if found:
            print(f"{args.candidate_id} -> {args.status}")
        else:
            print(f"no candidate with id {args.candidate_id!r}")
            raise SystemExit(1)
        return

    if args.command == "editorial-cadence":
        from cfb_rankings.storylines.cadence_dashboard import render_cadence_dashboard
        d = render_cadence_dashboard(db, output_path=args.output)
        print(
            f"editorial cadence: {d['overdue_count']} overdue surface(s), "
            f"{d['stale_thread_count']} stale thread(s) -> {d['md_path']}"
        )
        if args.strict and d["overdue_count"]:
            raise SystemExit(1)
        return
    # ---- end sprint 10: storylines ----

    if args.command == "refresh-savant":
        from cfb_rankings.team_pages.savant_data_loader import refresh_team_savant
        from cfb_rankings.team_pages.profile_loader import PROFILES_DIR
        slugs = args.slug or [p.stem for p in sorted(PROFILES_DIR.glob("*.md"))]
        with db.connection() as conn:
            season = args.season
            if season is None:
                row = conn.execute(
                    "select max(g.season_year) "
                    "from team_game_advanced_stats t "
                    "join games g on g.game_id = t.game_id"
                ).fetchone()
                season = int(row[0]) if row and row[0] is not None else None
                if season is None:
                    print("refresh-savant: no team_game_advanced_stats rows found — nothing to compute.")
                    return
                print(f"refresh-savant: auto-selected latest season with data = {season}")
            placeholders = ",".join(["?"] * len(slugs))
            rows = conn.execute(
                f"select slug, team_id from teams where slug in ({placeholders})",
                slugs,
            ).fetchall()
            slug_to_id = {r[0]: r[1] for r in rows}
            total = 0
            for slug in slugs:
                tid = slug_to_id.get(slug)
                if not tid:
                    print(f"  {slug}: team not found")
                    continue
                n = refresh_team_savant(conn, tid, season)
                conn.commit()
                total += n
                print(f"  {slug}: {n} metrics written")
            print(f"refresh-savant: wrote {total} rows across {len(slugs)} programs for season {season}")
        return

    if args.command == "refresh-season-arc":
        from cfb_rankings.team_pages.season_arc_loader import refresh_team_arc
        from cfb_rankings.team_pages.profile_loader import PROFILES_DIR
        slugs = args.slug or [p.stem for p in sorted(PROFILES_DIR.glob("*.md"))]
        with db.connection() as conn:
            placeholders = ",".join(["?"] * len(slugs))
            rows = conn.execute(
                f"select slug, team_id from teams where slug in ({placeholders})",
                slugs,
            ).fetchall()
            slug_to_id = {r[0]: r[1] for r in rows}
            total = 0
            for slug in slugs:
                tid = slug_to_id.get(slug)
                if not tid:
                    continue
                n = refresh_team_arc(conn, slug, tid, args.latest_season)
                conn.commit()
                total += n
                print(f"  {slug}: {n} seasons")
            print(f"refresh-season-arc: {total} rows across {len(slugs)} programs")
        return

    if args.command == "refresh-rivalry":
        from cfb_rankings.team_pages.rivalry_data_loader import refresh_rivalry_meetings
        from cfb_rankings.team_pages.profile_loader import load_profile, PROFILES_DIR
        slugs = args.slug or [p.stem for p in sorted(PROFILES_DIR.glob("*.md"))]
        with db.connection() as conn:
            pairs_seen: set[tuple[str, str]] = set()
            total = 0
            for slug in slugs:
                try:
                    profile = load_profile(slug)
                except FileNotFoundError:
                    continue
                t1 = next((r for r in profile.rivalries if (r.get("tier") or 99) == 1), None)
                if not t1 or not t1.get("opponent_slug"):
                    print(f"  {slug}: no Tier-1 rivalry")
                    continue
                opp = t1["opponent_slug"]
                key = tuple(sorted([slug, opp]))
                if key in pairs_seen:
                    continue
                pairs_seen.add(key)
                n = refresh_rivalry_meetings(conn, slug, opp)
                conn.commit()
                total += n
                print(f"  {slug} vs {opp}: {n} meetings")
            print(f"refresh-rivalry: {total} meetings across {len(pairs_seen)} pairs")
        return

    # ----- Sprint 11 — The Canon -----
    if args.command == "seed-canon-metadata":
        from cfb_rankings.canon import seed_list_metadata
        with db.connection() as conn:
            n = seed_list_metadata(conn)
        print(f"seed-canon-metadata: seeded {n} list metadata rows")
        return

    if args.command == "generate-canon-list":
        from cfb_rankings.canon import generate_canon_list, seed_list_metadata
        with db.connection() as conn:
            # Make sure metadata is seeded first; idempotent.
            seed_list_metadata(conn)
            report = generate_canon_list(conn, args.list, edition_year=args.year)
        print(f"generate-canon-list: {report.list_slug}")
        print(f"  entries           : {report.entry_count}")
        print(f"  paragraphs/oneliners : {report.paragraphs_validated}/{report.oneliners_validated}")
        print(f"  validator         : {report.validator_passed} passed, "
              f"{report.validator_failed} failed "
              f"({report.pass_rate * 100:.1f}% pass rate)")
        if report.validator_failed_labels:
            for lbl in report.validator_failed_labels[:10]:
                print(f"    - {lbl}")
        print(f"  cohort splits     : {report.cohort_splits_computed}")
        print(f"  rank deltas       : {report.rank_deltas_computed}")
        print(f"  effort buckets    : {report.effort_buckets}")
        return

    if args.command == "render-canon":
        from cfb_rankings.canon import render_canon_list, render_canon_index
        with db.connection() as conn:
            list_path = render_canon_list(conn, args.list, args.output_dir)
            index_path = render_canon_index(conn, args.output_dir)
        print(f"render-canon: list  -> {list_path}")
        print(f"             index -> {index_path}")
        return

    if args.command == "render-canon-all":
        from cfb_rankings.canon import render_all_canon
        with db.connection() as conn:
            counts = render_all_canon(conn, args.output_dir)
        print(f"render-canon-all: {counts['lists']} lists, "
              f"{counts['entries']} entries, {counts['index']} index "
              f"-> {args.output_dir}/canon/")
        return

    if args.command == "render-team-pages":
        from cfb_rankings.team_pages import render_all_profiled_pages, PROFILED_SLUGS
        from cfb_rankings.team_pages.profile_loader import list_real_fbs_slugs
        override_date = None
        if getattr(args, "date", None):
            override_date = date.fromisoformat(args.date)
        count = render_all_profiled_pages(
            db, args.output_dir,
            today=override_date, season_year=args.season,
            include_unprofiled_fbs=not args.profiled_only,
        )
        target_count = len(PROFILED_SLUGS)
        if not args.profiled_only:
            target_count = len(set(PROFILED_SLUGS) | set(list_real_fbs_slugs(db)))
        print(
            f"render-team-pages: rendered {count}/{target_count} team pages "
            f"-> {args.output_dir}"
        )
        return

    if args.command == "render-era-page":
        from cfb_rankings.era_pages import render_era_page_for
        rendered = 0
        for slug in args.slug:
            ok = render_era_page_for(db, slug, args.output_dir, end_season=args.end_season)
            if ok:
                rendered += 1
                print(f"render-era-page: {slug} -> "
                      f"{args.output_dir}/{slug}/era/cfp/index.html")
            else:
                print(f"render-era-page: {slug} skipped (insufficient CFP-era data)")
        print(f"render-era-page: rendered {rendered}/{len(args.slug)} era pages")
        return

    if args.command == "simulate-game":
        from cfb_rankings.team_pages.simulate_game import run_simulation
        # When fixture is supplied without scalar args, we still need defaults
        # so argparse doesn't object — the simulator reads from the fixture.
        report = run_simulation(
            db=db,
            home_slug=args.home,
            away_slug=args.away,
            final_home=args.final_home or 0,
            final_away=args.final_away or 0,
            wp_curve_path=args.wp_curve,
            events_log_path=args.events_log,
            persist=args.persist,
            output_dir=args.output_dir,
            pre_game_spread_home=args.pre_game_spread_home,
            fixture_path=args.fixture,
            chronicle_mode=args.chronicle_mode,
            narrative_mode=args.narrative_mode,
            season_year=args.season,
            week=args.week,
            with_cadence=args.with_cadence,
        )
        print(report)
        return

    if args.command == "process-render-queue":
        from cfb_rankings.team_pages.render_queue_worker import (
            process_queue, queue_summary,
        )
        if args.summary:
            counts = queue_summary(db)
            print(
                f"render-queue: pending={counts['pending']} "
                f"running={counts['running']} done={counts['done']} "
                f"failed={counts['failed']}"
            )
            return
        result = process_queue(
            db, output_dir=args.output_dir, max_jobs=args.max_jobs,
        )
        print(
            f"process-render-queue: processed={result['processed']} "
            f"ok={result['ok']} failed={result['failed']} skipped={result['skipped']}"
        )
        return

    if args.command == "generate-historical-seasons":
        from cfb_rankings.team_pages.historical_season_generator import (
            generate_all, generate_for_slug,
        )
        from cfb_rankings.team_pages.profile_loader import PROFILED_SLUGS
        slugs = args.slug
        if slugs:
            totals = {"authored": 0, "template": 0, "skipped": 0}
            for slug in slugs:
                c = generate_for_slug(db, slug, force_template=args.force_template)
                for k, v in c.items():
                    totals[k] += v
                print(f"  {slug}: authored={c['authored']} template={c['template']}")
        else:
            totals = generate_all(db, force_template=args.force_template)
        print(
            f"generate-historical-seasons: "
            f"authored={totals['authored']} template={totals['template']}"
        )
        return

    if args.command == "render-historical-seasons":
        from cfb_rankings.team_pages.historical_season_page import (
            render_all_historical_seasons, render_historical_season_page,
        )
        from cfb_rankings.team_pages.profile_loader import load_profile, PROFILED_SLUGS
        if args.slug:
            count = 0
            for slug in args.slug:
                try:
                    profile = load_profile(slug)
                except FileNotFoundError:
                    print(f"  skip {slug}: profile not found")
                    continue
                if not profile.team_id:
                    continue
                years = [
                    r["season_year"] for r in db.query_all(
                        "select season_year from team_season_arc where team_id = :tid "
                        "order by season_year asc",
                        {"tid": profile.team_id},
                    )
                ]
                for year in years:
                    try:
                        render_historical_season_page(db, slug, year, args.output_dir)
                        count += 1
                    except Exception as exc:
                        print(f"  {slug}/{year} failed: {exc}")
            print(f"render-historical-seasons: wrote {count} pages")
        else:
            count = render_all_historical_seasons(db, args.output_dir)
            print(f"render-historical-seasons: wrote {count} pages")
        return

    if args.command == "tag-player-mentions":
        from cfb_rankings.ingest.player_name_tagger import tag_player_mentions
        result = tag_player_mentions(
            db, season_year=args.season, week=args.week,
            doc_limit=args.limit, commit=args.commit,
            preview=getattr(args, "preview", False),
            include_last_name_matches=not getattr(args, "no_last_name", False),
            player_pool_season=getattr(args, "player_pool_season", None),
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

    if args.command == "tag-team-mentions":
        from cfb_rankings.ingest.team_name_tagger import (
            DEFAULT_UNTAGGED_SOURCES,
            tag_team_mentions,
        )
        sources = (
            [s.strip() for s in args.sources.split(",") if s.strip()]
            if args.sources else list(DEFAULT_UNTAGGED_SOURCES)
        )
        result = tag_team_mentions(
            db, season_year=args.season, week=args.week,
            sources=sources, doc_limit=args.limit,
            commit=args.commit, preview=getattr(args, "preview", False),
        )
        mode = "COMMIT" if args.commit else "DRY-RUN"
        print(
            f"[{mode}] tag-team-mentions season={args.season} week={args.week}"
            + f" sources={','.join(sources)}"
            + f": docs_scanned={result['docs_scanned']}"
            + f" matches={result['matches']}"
            + f" rows_written={result['rows_written']}"
        )
        return

    if args.command == "compute-player-advanced":
        from cfb_rankings.metrics.player_advanced import (
            compute_player_advanced_metrics,
            compute_player_advanced_metrics_season,
        )
        if args.week is None:
            written = compute_player_advanced_metrics_season(db, args.season)
            print(f"compute-player-advanced season={args.season} (rollup+percentiles): rows_written={written}")
        else:
            written = compute_player_advanced_metrics(db, args.season, week=args.week)
            print(f"compute-player-advanced season={args.season} week={args.week}: rows_written={written}")
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
        from cfb_rankings.provenance.freshness_page import write_freshness_page
        from cfb_rankings.provenance.methodology_index_page import write_methodology_index_page
        from cfb_rankings.provenance.calibration_page import write_calibration_page
        out = write_methodology_page(db)
        print(f"methodology page written: {out}")
        fresh = write_freshness_page(db)
        print(f"freshness page written: {fresh}")
        calib = write_calibration_page(db)
        print(f"calibration page written: {calib}")
        idx = write_methodology_index_page()
        print(f"methodology index written: {idx}")
        return

    if args.command == "refresh-award-watch":
        import importlib.util as _ilu
        from pathlib import Path as _P
        _spec = _ilu.spec_from_file_location(
            "load_award_watch", _P(__file__).resolve().parent.parent.parent / "scripts" / "load_award_watch.py"
        )
        _mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod)
        _mod.load(_P(args.csv), _P(getattr(db, "_db_path", None) or "cfb_rankings.db"),
                  args.dry_run, args.prune_source)
        return

    if args.command == "refresh-depth-chart":
        import importlib.util as _ilu
        from pathlib import Path as _P
        _spec = _ilu.spec_from_file_location(
            "load_depth_chart", _P(__file__).resolve().parent.parent.parent / "scripts" / "load_depth_chart.py"
        )
        _mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod)
        _mod.load(_P(args.csv), _P(getattr(db, "_db_path", None) or "cfb_rankings.db"),
                  args.dry_run, args.prune_source)
        return

    if args.command == "verify-wave25":
        import importlib.util as _ilu
        from pathlib import Path as _P
        _spec = _ilu.spec_from_file_location(
            "verify_wave25", _P(__file__).resolve().parent.parent.parent / "scripts" / "verify_wave25.py"
        )
        _mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod)
        import sys as _sys
        _sys.exit(0 if _mod.verify(_P(getattr(db, "_db_path", None) or "cfb_rankings.db")) else 1)

    if args.command == "build-freshness":
        from cfb_rankings.provenance.freshness_page import write_freshness_page
        out = write_freshness_page(db)
        print(f"freshness page written: {out}")
        return

    if args.command == "build-search-index":
        from cfb_rankings.cmdk import write_search_index
        out_path, count = write_search_index(
            db,
            args.output,
            players_max=args.players_max,
            season_year=args.season,
            minify=not args.inspect,
        )
        size_kb = out_path.stat().st_size / 1024
        print(
            f"search-index written: {out_path} "
            f"({count} items, {size_kb:.1f} KB)"
        )
        return

    if args.command == "fetch-archive-retro":
        from cfb_rankings.ingest.sources.archive_retro import fetch_archive_retro
        today_arg = None
        if args.today:
            today_arg = date.fromisoformat(args.today)
        result = fetch_archive_retro(
            db,
            today=today_arg,
            years_back=args.years_back,
            min_score=args.min_score,
            day_window=args.day_window,
        )
        print(
            f"fetch-archive-retro: years_scanned={result['years_scanned']} "
            f"posts_fetched={result['posts_fetched']} "
            f"posts_promoted={result['posts_promoted']} "
            f"posts_archived_low_engagement={result['posts_archived_low_engagement']} "
            f"errors={result['errors']}"
        )
        return

    # Sprint v5-8 stub commands (added 2026-05-22 to silence hourly/weekly
    # cron failure noise once notify_failure.yml started working). Real
    # implementations TBD; until then the workflows exit 0 with a log
    # message and the rolling artifact stays untouched.
    if args.command == "sync-digest-reactions":
        print("sync-digest-reactions: STUB -- no-op until Sprint v5-8.")
        print("  Real implementation will poll the rolling digest issue for")
        print("  thumbs-up/thumbs-down reactions, parse :thumbsdown: into")
        print("  editorial_overrides (override_kind='reject'), idempotent by")
        print("  (item_id, user_id).")
        return

    if args.command == "build-weekly-digest":
        print("build-weekly-digest: STUB -- no-op until Sprint v5-8.")
        print(f"  Args parsed: out={getattr(args, 'out', None)!r} "
              f"look_ahead_days={getattr(args, 'look_ahead_days', None)!r}")
        # Touch the output path so the downstream "Post comment to rolling
        # digest issue" workflow step has a file to read. An empty-ish body
        # is a valid no-op comment that won't pollute the digest thread.
        out_path = getattr(args, "out", None) or "digest.md"
        try:
            Path(out_path).write_text(
                "_(build-weekly-digest is a stub awaiting Sprint v5-8; "
                "this run produced no digest body.)_\n",
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"  warning: failed to write stub body to {out_path}: {exc}")
        return

    if args.command == "render-today-in-history":
        from cfb_rankings.today_in_history import render_today_in_history_page
        today_arg = None
        if args.today:
            today_arg = date.fromisoformat(args.today)
        result = render_today_in_history_page(
            db,
            today=today_arg,
            output_dir=args.output_dir,
            max_cards=args.max_cards,
        )
        print(
            f"render-today-in-history: cards_rendered={result['cards_rendered']} "
            f"files={len(result['output_files'])}"
        )
        for path in result["output_files"]:
            print(f"  wrote {path}")
        return

    if args.command == "render-kickoff-countdown":
        from cfb_rankings.countdown import render_countdown
        today_arg = None
        if args.today:
            today_arg = date.fromisoformat(args.today)
        # Reuse the underlying sqlite3 connection for kickoff_date lookup
        # (cfb_calendar tolerates a None DB; passing it lets the games-table
        # path fire when available).
        result = render_countdown(
            db.connection() if hasattr(db, "connection") else db,
            today=today_arg,
            output_dir=args.output_dir,
        )
        print(
            f"render-kickoff-countdown: days={result['days_to_kickoff']} "
            f"phase={result['phase_label']!r} "
            f"files={result['files_written']}"
        )
        return

    if args.command == "refresh-recruiting-pulse":
        from contextlib import nullcontext
        from cfb_rankings.recruit_board import render_recruit_board
        # render_recruit_board needs a live sqlite3.Connection (it calls
        # .execute()). db.connection() is a @contextmanager — ENTER it instead
        # of passing the unentered manager, which was the #204 crash
        # ("'_GeneratorContextManager' object has no attribute 'execute'").
        cm = db.connection() if hasattr(db, "connection") else nullcontext(db)
        with cm as conn:
            result = render_recruit_board(
                conn,
                class_year=args.class_year,
                output_dir=args.output_dir,
            )
        print(
            f"refresh-recruiting-pulse: class_year={result['class_year']} "
            f"programs={result['program_count']} "
            f"days_to_kickoff={result['days_to_kickoff']} "
            f"-> {result['output_path']}"
        )
        return

    if args.command == "export-player-id-anchor":
        from cfb_rankings.player_id_anchor import export_anchor
        n = export_anchor(db, args.path)
        print(f"export-player-id-anchor: wrote {n:,} rows -> {args.path}")
        return

    if args.command == "seed-player-id-anchor":
        from cfb_rankings.player_id_anchor import seed_anchor
        r = seed_anchor(db, args.path)
        print(
            f"seed-player-id-anchor: anchor_rows={r['anchor_rows']:,} "
            f"players_inserted={r['players_inserted']:,} "
            f"source_ids_inserted={r['source_ids_inserted']:,}"
        )
        return

    if args.command == "audit-player-duplicates":
        from cfb_rankings.player_dedup import audit_duplicates
        audit = audit_duplicates(db)
        print(f"audit-player-duplicates: {audit.summary()}")
        merges = [p for p in audit.plans if p.action == "merge"]
        for p in merges[:15]:
            print(
                f"  merge {p.full_name!r}: {p.dup_id} -> {p.canonical_id} "
                f"({p.dup_child_rows} child rows; {p.reason})"
            )
        if len(merges) > 15:
            print(f"  ... and {len(merges) - 15:,} more merges")
        return

    if args.command == "merge-player-duplicates":
        from cfb_rankings.player_dedup import merge_duplicates
        stats = merge_duplicates(db, commit=args.commit)
        mode = "COMMITTED" if args.commit else "DRY-RUN (use --commit to write)"
        print(f"merge-player-duplicates [{mode}]: {stats}")
        if args.commit:
            print("now run: python manage.py export-player-id-anchor  (and commit the CSV)")
        return

    if args.command == "build-dynasty-heatmap":
        from cfb_rankings.dynasty_heatmap import build_dynasty_heatmap
        written = build_dynasty_heatmap(
            db,
            output_dir=args.output_dir,
            year_start=args.year_start,
            year_end=args.year_end,
        )
        print(f"dynasty-heatmap: wrote {len(written)} files")
        return

    if args.command == "build-nfl-pipeline":
        from cfb_rankings.nfl_pipeline import build_nfl_pipeline
        written = build_nfl_pipeline(
            db,
            output_dir=args.output_dir,
            year_start=args.year_start,
            year_end=args.year_end,
            top_n=args.top_n,
        )
        print(f"nfl-pipeline: wrote {len(written)} files")
        return

    if args.command == "build-vibe-shifts":
        from cfb_rankings.vibe_shifts import (
            build_vibe_shifts_for_week,
            build_vibe_shifts_section,
            latest_vibe_shifts_week,
        )
        if args.week is not None:
            season = args.season
            if season is None:
                latest = latest_vibe_shifts_week(db)
                if latest is None:
                    print("build-vibe-shifts: no qualifying weeks in DB")
                    return
                season, _ = latest
            written = build_vibe_shifts_for_week(
                db, season, args.week, args.output_dir, limit=args.limit,
            )
            print(f"vibe-shifts: wrote {len(written)} files for season {season} week {args.week}")
        else:
            written = build_vibe_shifts_section(
                db,
                output_dir=args.output_dir,
                max_weeks=args.max_weeks,
            )
            print(f"vibe-shifts: wrote {len(written)} files across latest {args.max_weeks} weeks")
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

    if args.command == "player-hot-take":
        import datetime as _dt_ht
        from cfb_rankings.bets.hot_take import (
            fetch_or_generate_take, generate_hot_takes,
        )
        # Resolve slug → player_id.
        target = args.slug_or_id
        if target.isdigit():
            pid = int(target)
        else:
            row = db.query_one(
                "SELECT player_id FROM players "
                "WHERE lower(full_name) = lower(:q) "
                "   OR player_id = CAST(:q AS INTEGER) "
                "LIMIT 1",
                {"q": target},
            )
            if not row:
                digits = "".join(ch for ch in target if ch.isdigit())
                pid = int(digits) if digits else 0
            else:
                pid = int(row["player_id"])
        if not pid:
            print(f"no player resolved for {target!r}")
            return
        season = args.season or int(db.query_one(
            "SELECT MAX(season_year) AS y FROM player_season_stats"
        )["y"] or 2025)
        as_of = (
            _dt_ht.date.fromisoformat(args.as_of) if args.as_of else _dt_ht.date.today()
        )
        take = fetch_or_generate_take(db, pid, season, as_of=as_of)
        if take is None:
            print(f"no defensibly-true take for player_id={pid} on {as_of}.")
            return
        print(f"--- Hot-Take for player_id={pid} ({as_of.isoformat()}) ---")
        print(take.rendered_text)
        print()
        print("math trail:")
        for k, v in take.meta.items():
            print(f"  {k}: {v}")
        # Show runners-up for context.
        all_takes = generate_hot_takes(db, pid, season)
        if len(all_takes) > 1:
            print()
            print(f"runners-up ({len(all_takes)-1}):")
            for other in all_takes[1:4]:
                if other.rendered_text != take.rendered_text:
                    print(f"  - [{other.template_id}] {other.rendered_text}")
        return

    if args.command == "compute-daily-hot-takes":
        import datetime as _dt_ht
        from cfb_rankings.bets.hot_take import compute_daily_hot_takes
        season = args.season or int(db.query_one(
            "SELECT MAX(season_year) AS y FROM player_season_stats"
        )["y"] or 2025)
        as_of = (
            _dt_ht.date.fromisoformat(args.as_of) if args.as_of else _dt_ht.date.today()
        )
        n = compute_daily_hot_takes(db, season, as_of=as_of)
        print(f"computed + cached {n} Hot-Take(s) for season={season} as_of={as_of}")
        return

    if args.command == "player-mirror-match":
        from cfb_rankings.bets.mirror_match import find_mirror_matches
        target = args.slug_or_id
        if target.isdigit():
            pid = int(target)
        else:
            digits = "".join(ch for ch in target if ch.isdigit())
            pid = int(digits) if digits else 0
        season = args.season or int(db.query_one(
            "SELECT MAX(season_year) AS y FROM player_season_stats"
        )["y"] or 2025)
        matches = find_mirror_matches(db, pid, season, k=args.k)
        print(f"--- {len(matches)} Mirror Match(es) for player_id={pid}, season={season} ---")
        for m in matches:
            print(
                f"  {m.match_player_name} ({m.match_team_name or '?'}) "
                f"{m.match_season} — sim={m.similarity_pct}%  cov={m.coverage_pct}%"
            )
        return

    if args.command == "compute-mirror-matches":
        from cfb_rankings.bets.mirror_match import compute_mirror_matches
        season = args.season or int(db.query_one(
            "SELECT MAX(season_year) AS y FROM player_season_stats"
        )["y"] or 2025)
        n = compute_mirror_matches(db, season, k=args.k)
        print(f"computed + cached matches for {n} player(s), season={season}")
        return

    if args.command == "ingest-cfbd-pbp":
        env_path = os.path.join(os.getcwd(), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k, v)
        from cfb_rankings.clients.cfbd import CfbdClient
        from cfb_rankings.ingest.cfbd_pbp import ingest_cfbd_pbp_week
        api_key = os.environ.get("CFBD_PATREON_KEY") or os.environ.get("CFBD_API_KEY")
        base_url = os.environ.get("CFBD_BASE_URL", "https://api.collegefootballdata.com")
        if not api_key:
            raise SystemExit("CFBD_API_KEY (or CFBD_PATREON_KEY) not in env.")
        client = CfbdClient(api_key=api_key, base_url=base_url)
        weeks = args.weeks if args.weeks else list(range(1, 17))
        season_types = (["regular", "postseason"] if args.season_type == "both"
                        else [args.season_type])
        total_plays = 0; total_actors = 0
        for st in season_types:
            for w in weeks:
                result = ingest_cfbd_pbp_week(
                    db, client, args.season, w, st,
                    classification=args.classification,
                    parse_actors=not args.skip_actors,
                )
                total_plays += result["plays"]
                total_actors += result["actors"]
                print(f"  [{st} w{w:02d}] plays={result['plays']} "
                      f"actors={result['actors']}", flush=True)
        print(f"ingest-cfbd-pbp season={args.season}: "
              f"plays={total_plays} actors={total_actors}")
        return

    if args.command == "compute-player-pbp-metrics":
        from cfb_rankings.metrics.player_pbp_metrics import (
            compute_player_pbp_metrics_season,
        )
        r = compute_player_pbp_metrics_season(db, args.season)
        print(f"compute-player-pbp-metrics season={args.season}: {r}")
        return

    if args.command == "generate-player-narrative-arcs":
        from cfb_rankings.player_pages.narrative_arc_generator import (
            generate_narrative_arc,
        )
        season = int(args.season)
        if args.player_ids:
            targets = [(int(pid), None) for pid in args.player_ids]
        else:
            rows = db.query_all(
                """
                with player_latest as (
                    select player_id, max(week) as max_week, position
                      from player_season_stats
                     where season_year = :s
                       and category in ('passing','rushing','receiving','defensive')
                       and stat_type in ('ATT','CAR','REC','TOT')
                     group by player_id, position
                ),
                vol as (
                    select pss.player_id, pss.position, pss.stat_value_num as v
                      from player_season_stats pss
                      join player_latest pl on pl.player_id = pss.player_id
                                           and pl.max_week  = pss.week
                                           and pl.position  = pss.position
                     where pss.season_year = :s
                       and (
                         (pss.position = 'QB' and pss.category='passing' and pss.stat_type='ATT')
                         or (pss.position in ('RB','TB','FB','HB') and pss.category='rushing' and pss.stat_type='CAR')
                         or (pss.position in ('WR','TE') and pss.category='receiving' and pss.stat_type='REC')
                         or (pss.position in ('CB','S','DB','LB','ILB','OLB','MLB','DL','DE','DT','NT','EDGE')
                             and pss.category='defensive' and pss.stat_type='TOT')
                       )
                       and pss.stat_value_num is not null
                )
                select v.player_id, v.position, v.v
                  from vol v order by v.v desc limit :lim
                """,
                {"s": season, "lim": int(args.top)},
            )
            targets = [(int(r["player_id"]), str(r["position"] or "")) for r in rows]
        ok = 0; fail = 0
        for i, (pid, pos) in enumerate(targets, 1):
            r = generate_narrative_arc(
                db, pid, season, pos or "",
                model_id=args.model, force_refresh=args.force_refresh,
            )
            if r:
                ok += 1
                preview = (r.get("opening_text") or "")[:60].replace("\n", " ")
                print(f"  [{i}/{len(targets)}] pid={pid} pos={pos} OK: {preview}...", flush=True)
            else:
                fail += 1
                print(f"  [{i}/{len(targets)}] pid={pid} pos={pos} FAILED", flush=True)
        print(f"generate-player-narrative-arcs season={season}: ok={ok} failed={fail}")
        return

    if args.command == "generate-player-signatures":
        from cfb_rankings.player_pages.signature_story_generator import (
            generate_signature_story,
        )
        season = int(args.season)
        if args.player_ids:
            targets = [(int(pid), None, None) for pid in args.player_ids]
        else:
            # Top-N by gate-metric volume across each position cohort.
            rows = db.query_all(
                """
                with player_latest as (
                    select player_id, max(week) as max_week, position
                      from player_season_stats
                     where season_year = :s
                       and category in ('passing','rushing','receiving','defensive')
                       and stat_type in ('ATT','CAR','REC','TOT')
                     group by player_id, position
                ),
                vol as (
                    select pss.player_id, pss.position, pss.stat_value_num as v
                      from player_season_stats pss
                      join player_latest pl on pl.player_id = pss.player_id
                                           and pl.max_week  = pss.week
                                           and pl.position  = pss.position
                     where pss.season_year = :s
                       and (
                         (pss.position in ('QB') and pss.category='passing' and pss.stat_type='ATT')
                         or (pss.position in ('RB','TB','FB','HB') and pss.category='rushing' and pss.stat_type='CAR')
                         or (pss.position in ('WR','TE') and pss.category='receiving' and pss.stat_type='REC')
                         or (pss.position in ('CB','S','DB','LB','ILB','OLB','MLB','DL','DE','DT','NT','EDGE')
                             and pss.category='defensive' and pss.stat_type='TOT')
                       )
                       and pss.stat_value_num is not null
                )
                select v.player_id, v.position, v.v
                  from vol v
                 order by v.v desc
                 limit :lim
                """,
                {"s": season, "lim": int(args.top)},
            )
            targets = [(int(r["player_id"]), str(r["position"] or ""), float(r["v"])) for r in rows]
        ok = 0; fail = 0
        for i, (pid, pos, _vol) in enumerate(targets, 1):
            r = generate_signature_story(
                db, pid, season, pos or "",
                model_id=args.model, force_refresh=args.force_refresh,
            )
            if r:
                ok += 1
                preview = (r.get("story_text") or "")[:80].replace("\n", " ")
                print(f"  [{i}/{len(targets)}] pid={pid} pos={pos} OK: {preview}...", flush=True)
            else:
                fail += 1
                print(f"  [{i}/{len(targets)}] pid={pid} pos={pos} FAILED", flush=True)
        print(f"generate-player-signatures season={season}: ok={ok} failed={fail}")
        return

    if args.command == "compute-achievements":
        from cfb_rankings.bets.achievements import compute_achievements
        season = args.season or int(db.query_one(
            "SELECT MAX(season_year) AS y FROM player_season_stats"
        )["y"] or 2025)
        n = compute_achievements(db, season)
        print(f"wrote {n} achievement unlock(s) for season={season}")
        return

    if args.command == "player-achievements":
        from cfb_rankings.bets.achievements import fetch_player_achievements
        target = args.slug_or_id
        if target.isdigit():
            pid = int(target)
        else:
            digits = "".join(ch for ch in target if ch.isdigit())
            pid = int(digits) if digits else 0
        season = args.season or int(db.query_one(
            "SELECT MAX(season_year) AS y FROM player_season_stats"
        )["y"] or 2025)
        ach = fetch_player_achievements(db, pid, season)
        print(f"--- {len(ach)} achievement(s) for player_id={pid}, season={season} ---")
        for a in ach:
            rarity = (
                f"{a['rarity_pct']:.1f}%"
                if a.get("rarity_pct") is not None
                else "n/a"
            )
            print(f"  [{rarity}] {a['display_name']} — {a['unlock_context']}")
        return

    if args.command == "recompute-confidence-thresholds":
        from cfb_rankings.confidence import (
            Domain,
            recompute_thresholds,
            _DOMAIN_SAMPLE_SQL,
        )
        domains = (
            [Domain(args.domain)] if args.domain != "all"
            else list(Domain)
        )
        if args.print_only:
            # Dry run — compute but don't write. Bypass the upsert path.
            import statistics
            for d in domains:
                rows = db.query_all(_DOMAIN_SAMPLE_SQL[d])
                samples = sorted(
                    int(r["sample_count"]) for r in rows
                    if r["sample_count"] is not None
                )
                n = len(samples)
                if n == 0:
                    print(f"{d.value:<12} n=0  (no data — would write fallback thresholds)")
                    continue
                p10 = samples[max(0, int(0.10 * (n - 1)))]
                p25 = samples[max(0, int(0.25 * (n - 1)))]
                p75 = samples[max(0, int(0.75 * (n - 1)))]
                print(f"{d.value:<12} n={n:>6}  p10={p10:>6}  p25={p25:>6}  p75={p75:>6}")
            return
        for d in domains:
            result = recompute_thresholds(db, d)
            t = result.thresholds
            print(
                f"{d.value:<12} q={result.quarter}  "
                f"p10={t.p10:>6}  p25={t.p25:>6}  p75={t.p75:>6}  "
                f"n={t.sample_size_at_calibration}"
            )
        return

    if args.command == "confidence-status":
        from cfb_rankings.confidence import Domain, get_calibration
        print(f"{'DOMAIN':<12}  {'P10':>6}  {'P25':>6}  {'P75':>6}  {'N':>8}  CALIBRATED")
        for d in Domain:
            t = get_calibration(d, db=db)
            row = db.query_one(
                "SELECT quarter, computed_at_utc FROM confidence_calibration "
                "WHERE domain = ? ORDER BY computed_at_utc DESC LIMIT 1",
                (d.value,),
            )
            calibrated = f"{row['quarter']} @ {row['computed_at_utc']}" if row else "FALLBACK"
            print(
                f"{d.value:<12}  {t.p10:>6}  {t.p25:>6}  {t.p75:>6}  "
                f"{t.sample_size_at_calibration:>8}  {calibrated}"
            )
        return

    if args.command == "generate-mood-map":
        # v5-10e: DB-backed mood-map render.
        # builders.build_mood_map_input reads from fanbase_mood_weekly +
        # hub_issue_metadata when populated, falls back to the W048 mockup
        # composition otherwise. The renderer is identical either way.
        from cfb_rankings.viral.builders import build_mood_map_input
        from cfb_rankings.viral.mood_map import render
        kwargs = build_mood_map_input(db)
        if args.week_label:
            kwargs["when_label"] = args.week_label
        out = render(args.output, dark=bool(args.dark), **kwargs)
        size_kb = out.stat().st_size / 1024
        print(f"Wrote {out}  ({size_kb:.1f} KB · 1200x675{' · DARK' if args.dark else ''})")
        return

    if args.command == "generate-daily-movers":
        from cfb_rankings.viral.builders import build_daily_movers_input
        from cfb_rankings.viral.daily_movers import render
        kwargs = build_daily_movers_input(db)
        out = render(args.output, dark=bool(args.dark), **kwargs)
        size_kb = out.stat().st_size / 1024
        print(f"Wrote {out}  ({size_kb:.1f} KB · 1200x630{' · DARK' if args.dark else ''})")
        return

    if args.command == "generate-pregame-pack":
        from cfb_rankings.viral.builders import build_pregame_pack_input
        from cfb_rankings.viral.pregame_pack import render
        kwargs = build_pregame_pack_input(db, game_id=args.game_id)
        if kwargs is None:
            print("generate-pregame-pack: no qualifying Saturday game in the next 7 days "
                  "(don't fabricate; pack will run when a game is scheduled).")
            return
        out = render(args.output, dark=bool(args.dark), **kwargs)
        size_kb = out.stat().st_size / 1024
        print(f"Wrote {out}  ({size_kb:.1f} KB · 1200x630{' · DARK' if args.dark else ''})")
        return

    if args.command == "player-bets-audit":
        target = args.slug_or_id
        if target.isdigit():
            pid = int(target)
        else:
            digits = "".join(ch for ch in target if ch.isdigit())
            pid = int(digits) if digits else 0
        if not pid:
            print(f"no player resolved for {target!r}")
            return
        season = args.season or int(db.query_one(
            "SELECT MAX(season_year) AS y FROM player_season_stats"
        )["y"] or 2025)
        prow = db.query_one("SELECT full_name FROM players WHERE player_id = :p", {"p": pid})
        name = (prow or {}).get("full_name") or f"player_id={pid}"
        team_row = db.query_one(
            "SELECT team_id FROM player_season_stats WHERE player_id = :p ORDER BY season_year DESC LIMIT 1",
            {"p": pid},
        )
        team_id = (team_row or {}).get("team_id")
        team_meta = db.query_one("SELECT slug, canonical_name FROM teams WHERE team_id = :t", {"t": team_id}) if team_id else None

        print(f"{'='*72}")
        print(f"  Signature Bets audit: {name} (player_id={pid}) · season {season}")
        print(f"  team: {(team_meta or {}).get('canonical_name') or '(unknown)'} · slug: {(team_meta or {}).get('slug') or '(unknown)'}")
        print(f"{'='*72}\n")

        # Hot-Take / Anti-Take
        print("--- Hot-Take / Anti-Take ------------------------------------")
        from cfb_rankings.bets.hot_take import fetch_or_generate_take
        from cfb_rankings.bets.anti_take import generate_anti_take
        import datetime as _dt_a
        take = fetch_or_generate_take(db, pid, season, as_of=_dt_a.date.today())
        if take:
            ant = generate_anti_take(take)
            if ant:
                print(f"HOT:  {take.rendered_text}")
                print(f"ANTI: [{ant.caveat_tag}] {ant.rendered_text}")
                print(f"meta: rank={take.meta.get('rank')} / cohort_size={take.meta.get('cohort_size')} "
                      f"/ sample={take.meta.get('sample')} / pct={take.meta.get('percentile')}")
            else:
                print("Take present but Anti-Take unpairable — held per S2.3 spec.")
        else:
            print("(no qualifying take today)")

        # Achievements
        print("\n--- Achievements --------------------------------------------")
        from cfb_rankings.bets.achievements import fetch_player_achievements
        for a in fetch_player_achievements(db, pid, season):
            r = f"{a['rarity_pct']:.1f}%" if a.get("rarity_pct") is not None else "n/a"
            print(f"  [{r}] {a['display_name']} — {a['unlock_context']}")

        # Mirror Match
        print("\n--- Mirror Match --------------------------------------------")
        from cfb_rankings.bets.mirror_match import fetch_cached_matches
        matches = fetch_cached_matches(db, pid, season, k=5)
        if matches:
            for m in matches:
                team = m.match_team_name or "?"
                print(f"  #{m.similarity_pct}% sim — {m.match_player_name} ({team}) {m.match_season}")
        else:
            print("  (no cached matches — run `compute-mirror-matches --season N`)")

        # Rival Radar
        print("\n--- Rival Radar ---------------------------------------------")
        from cfb_rankings.bets.rival_radar import compute_rival_radar
        rr = compute_rival_radar(db, pid, season)
        if rr.applicable:
            print(f"  mentions={rr.mention_count_season} / weeks={rr.weeks_with_rival_chatter} "
                  f"/ obsession={rr.obsession_score}")
        else:
            print(f"  empty — {rr.awaiting_reason}")

        # Coaching Lineage
        print("\n--- Coaching Lineage ----------------------------------------")
        from cfb_rankings.bets.coaching_lineage import fetch_coaching_lineage
        lineage = fetch_coaching_lineage((team_meta or {}).get("slug"))
        if lineage:
            hc = (lineage.get("head_coach") or {}).get("name")
            oc = (lineage.get("offensive_coordinator") or {}).get("name")
            dc = (lineage.get("defensive_coordinator") or {}).get("name")
            print(f"  {lineage.get('display_name')}: HC {hc} · OC {oc} · DC {dc}")
        else:
            print("  (no seed for this program)")

        # Narrative Arc
        print("\n--- Narrative Arc -------------------------------------------")
        from cfb_rankings.bets.narrative_arc import fetch_narrative_arc
        arc = fetch_narrative_arc(pid, season)
        if arc:
            for a in arc.get("acts") or []:
                print(f"  {a.get('title')} ({a.get('week_range')})")
        else:
            print("  (no hand-authored arc; auto-draft may fire at render time)")

        # Signature Moment
        print("\n--- Signature Moment ----------------------------------------")
        from cfb_rankings.bets.signature_play import fetch_signature_moment
        sm = fetch_signature_moment(db, pid, season)
        if sm:
            print(f"  Week {sm.week} vs {sm.opponent_name} — {int(sm.stat_value)} {sm.metric_id} ({sm.result_label})")
        else:
            print("  (empty — player_game_stats coverage too thin)")

        # Prediction Markets
        print("\n--- Prediction Markets --------------------------------------")
        from cfb_rankings.bets.prediction_markets import fetch_player_market_signals
        ms = fetch_player_market_signals(db, pid, season)
        if ms.listed:
            print(f"  Heisman implied {ms.heisman_implied_pct}% · {ms.heisman_provider}")
        else:
            print("  (unlisted on major futures markets)")

        # Cohort Divergence
        print("\n--- Cohort Divergence ---------------------------------------")
        from cfb_rankings.bets.cohort_divergence import compute_cohort_divergence
        cd = compute_cohort_divergence(db, pid, season)
        if cd.applicable:
            for d in cd.dots:
                print(f"  {d.label}: belief={d.belief:+.1f}, intensity={d.intensity:.1f}, n={d.mention_count}")
        else:
            print(f"  empty — {cd.awaiting_reason}")

        # This-day chip
        print("\n--- This-day chip -------------------------------------------")
        from cfb_rankings.bets.this_day import fetch_this_day_moment
        td = fetch_this_day_moment(db, pid)
        if td:
            print(f"  {td.headline}")
        else:
            print("  (no historical match for today)")

        print(f"\n{'='*72}\n")
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

    if args.command == "autopilot-status":
        print("=" * 64)
        print("Autopilot v1 — one-screen dashboard")
        print("=" * 64)

        # Source / tier counts
        tier_rows = db.query_all(
            "select tier, count(*) as n from source_registry "
            "where source_id is not null group by tier order by tier"
        )
        total_sources = sum(int(r["n"]) for r in tier_rows)
        active = db.query_one(
            "select count(*) as n from source_registry "
            "where source_id is not null and is_active = 1"
        )["n"]
        print(f"\nSources: {total_sources} total, {active} active")
        for r in tier_rows:
            print(f"  Tier {r['tier']}: {r['n']}")

        # scrape_health last 7 days
        since = (date.today() - timedelta(days=7)).isoformat()
        health = db.query_all(
            "select status, count(*) as n from scrape_health "
            "where run_date >= :since group by status order by status",
            {"since": since},
        )
        total_runs = sum(int(r["n"]) for r in health) or 0
        print(f"\nscrape_health (last 7d): {total_runs} runs")
        for r in health:
            print(f"  {r['status']}: {r['n']}")

        # 3-fail sources
        three_fail = db.query_all(
            """
            select source_id, count(*) as fails
            from (
                select source_id, status,
                    row_number() over (partition by source_id order by run_date desc) rn
                from scrape_health
            )
            where rn <= 3 and status = 'error'
            group by source_id having count(*) = 3
            order by source_id
            """
        )
        if three_fail:
            print(f"\n!! {len(three_fail)} source(s) with 3 consecutive errors:")
            for r in three_fail:
                print(f"  {r['source_id']}")
        else:
            print("\nNo sources at the 3-consecutive-error threshold.")

        # Row-count deltas — headline tables
        print("\nHeadline tables:")
        for table in (
            "conversation_documents",
            "conversation_document_targets",
            "player_week_conversation_features",
            "player_advanced_metrics",
            "player_advanced_metrics_season",
            "player_game_stats",
            "source_observations",
            "team_cohort_week",
            "team_cohort_divergence_week",
        ):
            try:
                n = db.query_one(f"select count(*) as n from {table}")["n"]
                # Rows inserted in last 7 days (where a created_at/ingested_at-ish
                # column exists). Keep the query defensive — fall back silently.
                recent = 0
                for ts_col in ("created_at", "observed_at_utc", "computed_at",
                               "ingested_at", "captured_at", "updated_at"):
                    if db.column_exists(table, ts_col):
                        try:
                            recent_row = db.query_one(
                                f"select count(*) as n from {table} "
                                f"where {ts_col} >= :since",
                                {"since": since},
                            )
                            recent = int(recent_row["n"]) if recent_row else 0
                            break
                        except Exception:
                            continue
                suffix = f" (+{recent:,} last 7d)" if recent else ""
                print(f"  {table}: {n:,}{suffix}")
            except Exception as e:
                print(f"  {table}: n/a ({e})")

        # Latest build timestamp (approx): take site root file mtime.
        from pathlib import Path as _Path
        from datetime import datetime as _dt
        index = _Path("output/site/index.html")
        if index.exists():
            mtime = _dt.fromtimestamp(index.stat().st_mtime)
            print(f"\nSite last built: {mtime.isoformat(timespec='seconds')}")
        else:
            print("\nSite last built: (no output/site/index.html yet)")

        print()
        return

    if args.command == "fanintel-status":
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

    if args.command == "prune-honor-stubs":
        from cfb_rankings.ingest.honors import prune_honor_stub_players

        result = prune_honor_stub_players(db, commit=args.commit)
        mode = "COMMITTED" if result["committed"] else "DRY-RUN (use --commit)"
        print(
            f"prune-honor-stubs [{mode}]: stub_players={result['stub_players']} "
            f"honors_removed={result['honors_removed']} heisman_removed={result['heisman_removed']}",
            flush=True,
        )
        for s in result["sample"]:
            print(f"  {s}", flush=True)
        return

    if args.command == "import-player-honors":
        from cfb_rankings.ingest.honors import import_player_honors_csv

        imported = import_player_honors_csv(
            repository=repository,
            db=db,
            csv_path=args.csv,
            default_source_name=args.source_name,
            create_stubs=not args.no_stubs,
        )
        print(f"Imported {imported} player honor rows from {args.csv}.", flush=True)
        return

    if args.command == "ingest-nfl-draft":
        from cfb_rankings.clients.cfbd import CfbdClient
        from cfb_rankings.ingest.draft import ingest_draft_range, ingest_draft_year

        if not config.cfbd_api_key:
            raise RuntimeError("CFBD_API_KEY not set — cannot fetch draft picks.")
        cfbd = CfbdClient(config.cfbd_api_key, config.cfbd_base_url, config.request_timeout_seconds)

        if args.year:
            summary = ingest_draft_year(db, cfbd, args.year)
            print(f"ingest-nfl-draft year={args.year}: {summary}")
        elif args.start_year and args.end_year:
            summaries = ingest_draft_range(db, cfbd, args.start_year, args.end_year)
            for s in summaries:
                print(f"  year={s['year']}: fetched={s['rows_fetched']} "
                      f"upserted={s['rows_upserted']} "
                      f"player_hits={s['resolved_player_ids']} "
                      f"team_hits={s['resolved_team_ids']}")
        else:
            raise RuntimeError("Provide either --year N or --start-year X --end-year Y.")
        return

    if args.command == "ingest-cfbd-coaches":
        from cfb_rankings.clients.cfbd import CfbdClient
        from cfb_rankings.ingest.coaches import ingest_coaches_range, ingest_coaches_year

        if not config.cfbd_api_key:
            raise RuntimeError("CFBD_API_KEY not set — cannot fetch coaches.")
        cfbd = CfbdClient(config.cfbd_api_key, config.cfbd_base_url, config.request_timeout_seconds)

        if args.year:
            summary = ingest_coaches_year(db, cfbd, args.year)
            print(f"ingest-cfbd-coaches year={args.year}: {summary}")
        elif args.start_year and args.end_year:
            summary = ingest_coaches_range(db, cfbd, args.start_year, args.end_year)
            print(f"ingest-cfbd-coaches {args.start_year}-{args.end_year}: {summary}")
        else:
            raise RuntimeError("Provide either --year N or --start-year X --end-year Y.")
        return

    if args.command == "seed-team-aliases":
        inserted = repository.seed_team_aliases(args.season)
        print(f"Seeded or refreshed {inserted} team alias rows for season {args.season}.", flush=True)
        return

    if args.command == "ingest-gdelt-news-volume":
        from cfb_rankings.ingest.sources.gdelt_gkg import ingest_gdelt_news_volume
        from datetime import datetime, timezone
        date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        result = ingest_gdelt_news_volume(
            db,
            date_str=date_str,
            lookback_hours=args.lookback_hours,
            commit=args.commit,
        )
        print(result)
        return

    if args.command == "scrape-wiki-awards":
        from cfb_rankings.ingest.sources.wiki_awards import emit_honor_csvs
        from cfb_rankings.ingest.honors import import_player_honors_csv
        from pathlib import Path as _Path

        years = range(args.start_year, args.end_year + 1)
        print(f"scrape-wiki-awards: years={list(years)} out_dir={args.out_dir}")
        summary = emit_honor_csvs(years, out_dir=args.out_dir)
        total = sum(summary.values()) if summary else 0
        print(f"  scraped {total} rows across {len(summary)} CSV(s)")
        for name, count in sorted(summary.items()):
            print(f"    {name}: {count} rows")

        if args.auto_import and summary:
            print("  auto-import: running import-player-honors on every CSV...")
            imported_total = 0
            for name in sorted(summary.keys()):
                p = _Path(args.out_dir) / name
                try:
                    imported = import_player_honors_csv(
                        repository=repository, db=db, csv_path=p,
                        default_source_name="wikipedia",
                        create_stubs=not getattr(args, "no_stubs", False),
                    )
                    imported_total += imported
                    print(f"    imported {imported} rows from {name}")
                except Exception as exc:
                    print(f"    FAIL {name}: {exc}")
            print(f"  auto-import total: {imported_total} honor rows imported")
        return

    if args.command == "scrape-nil-valuations":
        import datetime as _dt
        from cfb_rankings.ingest.sources.on3_nil import scrape_on3_nil, save_nil_valuations

        as_of = args.as_of_date or _dt.date.today().isoformat()
        scraped_at = _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        print(f"scrape-nil-valuations: fetching On3 CFB (limit={args.limit}, as_of={as_of})")
        rows = scrape_on3_nil(limit=args.limit)
        if not rows:
            print("  WARNING: no rows returned — page may be JS-rendered.")
            print("  Fallback: python manage.py import-nil-valuations --csv <file.csv>")
            return
        print(f"  scraped {len(rows)} rows")
        for r in rows[:5]:
            print(f"    #{r.get('rank'):>3}  {r.get('player_name'):<25}  "
                  f"{r.get('team_name'):<20}  ${r.get('valuation_usd', 0):,}")
        if len(rows) > 5:
            print(f"    ... ({len(rows) - 5} more)")
        if args.dry_run:
            print("  dry-run: no DB writes.")
            return
        result = save_nil_valuations(db=db, rows=rows, as_of_date=as_of, scraped_at=scraped_at)
        print(f"  inserted={result['inserted']} skipped={result['skipped']}")
        return

    if args.command == "import-nil-valuations":
        import csv as _csv
        import datetime as _dt
        from cfb_rankings.ingest.sources.on3_nil import save_nil_valuations
        from pathlib import Path as _Path

        csv_path = _Path(args.csv)
        if not csv_path.exists():
            print(f"ABORT: file not found: {csv_path}")
            return
        as_of_override = args.as_of_date
        scraped_at = _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        rows: list[dict] = []
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = _csv.DictReader(fh)
            for row in reader:
                as_of = as_of_override or row.get("as_of_date") or _dt.date.today().isoformat()
                val_raw = row.get("valuation_usd") or row.get("nil_value") or ""
                whisper_raw = row.get("whisper_usd") or row.get("whisper") or ""
                try:
                    val = int(float(str(val_raw).replace(",", "").replace("$", "").replace("M", "e6").replace("K", "e3"))) if val_raw else None
                except (ValueError, OverflowError):
                    val = None
                try:
                    whisper = int(float(str(whisper_raw).replace(",", "").replace("$", "").replace("M", "e6").replace("K", "e3"))) if whisper_raw else None
                except (ValueError, OverflowError):
                    whisper = None
                rows.append({
                    "player_name": row.get("player_name") or row.get("name") or "",
                    "rank": int(row["rank"]) if row.get("rank") else None,
                    "valuation_usd": val,
                    "whisper_usd": whisper,
                    "position": row.get("position") or "",
                    "team_name": row.get("team_name") or row.get("school") or "",
                    "source_name": row.get("source_name") or args.source,
                    "source_url": row.get("source_url") or "",
                    "_as_of": as_of,
                })
        if not rows:
            print("ABORT: CSV is empty or has no valid rows.")
            return
        print(f"import-nil-valuations: {len(rows)} rows from {csv_path.name}")
        # Group by as_of_date and save each batch
        from itertools import groupby as _groupby
        rows_sorted = sorted(rows, key=lambda r: r["_as_of"])
        total_inserted = total_skipped = 0
        for as_of, batch in _groupby(rows_sorted, key=lambda r: r["_as_of"]):
            batch_list = list(batch)
            result = save_nil_valuations(db=db, rows=batch_list, as_of_date=as_of, scraped_at=scraped_at)
            print(f"  {as_of}: inserted={result['inserted']} skipped={result['skipped']}")
            total_inserted += result["inserted"]
            total_skipped += result["skipped"]
        print(f"  total: inserted={total_inserted} skipped={total_skipped}")
        return

    if args.command == "collect-team-boards":
        import json as _json
        from pathlib import Path as _Path
        from cfb_rankings.ingest.conversation import collect_team_boards_rss
        repository.seed_levels()
        repository.ensure_season(args.season)
        seed_p = _Path(args.seed)
        if not seed_p.exists():
            print(f"ABORT: board seed not found: {seed_p}")
            return
        board_seed = _json.loads(seed_p.read_text(encoding="utf-8"))
        summary = collect_team_boards_rss(
            db=db, repository=repository, season=args.season, week=args.week,
            board_seed=board_seed,
        )
        print(f"collect-team-boards season={args.season} week={args.week}: "
              f"boards={summary['boards']} documents={summary['documents']} "
              f"targets={summary['targets']} boards_failed={summary['boards_failed']}")
        return

    if args.command == "collect-youtube-comments":
        import json as _json
        import os as _os
        from pathlib import Path as _Path
        from cfb_rankings.ingest.youtube_comments import collect_youtube_comments
        api_key = _os.environ.get("YOUTUBE_API_KEY")
        if not api_key:
            print("ABORT: YOUTUBE_API_KEY not set in env/.env")
            return
        national = []
        seed = _Path(args.national_seed)
        if seed.exists():
            national = _json.loads(seed.read_text(encoding="utf-8"))
        else:
            print(f"WARN: national seed not found ({seed}); national channels skipped")
        summary = collect_youtube_comments(
            db=db, season=args.season, week=args.week, api_key=api_key,
            national_channels=national,
            max_videos_per_channel=args.max_videos_per_channel,
            max_comments_per_video=args.max_comments_per_video,
            max_units=args.max_units, min_comment_count=args.min_comment_count,
        )
        print(f"collect-youtube-comments season={args.season} week={args.week}: "
              f"channels={summary['channels']} videos={summary['videos']} "
              f"documents={summary['documents']} targets={summary['targets']} "
              f"units={summary['units']} quota_hit={summary['quota_hit']}")
        return

    if args.command == "collect-podcast-transcripts":
        from cfb_rankings.ingest.podcast_transcribe import (
            FasterWhisperUnavailable, collect_podcast_transcripts,
        )
        try:
            summary = collect_podcast_transcripts(
                db=db, season=args.season, week=args.week,
                model_size=args.model_size, device=args.device,
                compute_type=args.compute_type, max_episodes=args.max_episodes,
                budget_seconds=args.budget_seconds, max_age_days=args.max_age_days,
                beam_size=args.beam_size, show_filter=list(args.show or []),
            )
        except FasterWhisperUnavailable as exc:
            # Graceful skip (exit 0) so the daily collector isn't marked failed
            # until faster-whisper is installed in .venv-ml.
            print(f"collect-podcast-transcripts SKIPPED: {exc}")
            return
        print(f"collect-podcast-transcripts season={args.season} week={args.week}: "
              f"episodes={summary['episodes']} transcribed={summary['transcribed']} "
              f"failed={summary['failed']} no_audio={summary['skipped_no_audio']} "
              f"chars={summary['chars']}")
        return

    if args.command == "collect-reddit-team-rss":
        from cfb_rankings.ingest.conversation import collect_reddit_team_subs_rss
        repository.seed_levels()
        repository.ensure_season(args.season)
        summary = collect_reddit_team_subs_rss(
            db=db, repository=repository, season=args.season, week=args.week,
            limit=args.limit, only_team_ids=args.teams,
        )
        print(f"collect-reddit-team-rss season={args.season} week={args.week}: "
              f"teams={summary['teams']} documents={summary['documents']} "
              f"targets={summary['targets']} feeds_failed={summary['feeds_failed']}")
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

    if args.command == "sync-team-locations":
        if not config.cfbd_api_key:
            raise RuntimeError("Missing required environment variable for this command: CFBD_API_KEY")
        from cfb_rankings.clients.cfbd import CfbdClient
        from cfb_rankings.ingest.cfbd import sync_cfbd_team_locations

        repository.seed_levels()
        cfbd = CfbdClient(config.cfbd_api_key, config.cfbd_base_url, config.request_timeout_seconds)
        print(f"Backfilling team city/state from CFBD /teams (season {args.season})...", flush=True)
        updated = sync_cfbd_team_locations(
            repository=repository, db=db, client=cfbd,
            season=args.season, classification=args.classification,
        )
        print(f"Updated location for {updated} teams.", flush=True)
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
        from cfb_rankings.chronicle.config import configure as configure_chronicle
        from cfb_rankings.reporting import build_static_site
        from cfb_rankings.retro_render import build_retro_pages

        # Apply LKG / no-LLM runtime flags before any chronicle import runs.
        use_lkg_only = getattr(args, "use_lkg_only", False)
        no_llm = getattr(args, "no_llm", False)
        configure_chronicle(use_lkg_only=use_lkg_only, no_llm=no_llm)
        if use_lkg_only:
            print("[build-site] LKG-only mode: chronicle cards will be served from Last-Known-Good cache.")
        if no_llm:
            print("[build-site] no-LLM mode: all LLM call paths are hard-disabled.")

        # Wave 25 — materialize player_current_status_view into a cache table.
        # The view's nested CTEs cost minutes per WHERE player_id=X. Building
        # it once at start drops 7000 × 4-per-player lookups from "hours" to
        # "sub-second total."
        try:
            import sqlite3 as _sqlite3, time as _time
            _db_path = getattr(db, "_db_path", None) or "cfb_rankings.db"
            _t0 = _time.perf_counter()
            _con = _sqlite3.connect(str(_db_path), timeout=300)
            _con.execute("PRAGMA busy_timeout=300000")
            _con.executescript("""
DROP TABLE IF EXISTS player_current_status_cache;
CREATE TABLE player_current_status_cache AS
SELECT * FROM (
    SELECT v.*,
           ROW_NUMBER() OVER (
               PARTITION BY player_id
               ORDER BY CASE WHEN current_team_id IS NULL THEN 1 ELSE 0 END,
                        CASE WHEN status_code='TRANSFERRED_COLLEGE' THEN 0
                             WHEN status_code='RETURNING_2026' THEN 1
                             ELSE 2 END
           ) AS rn
    FROM player_current_status_view v
) WHERE rn = 1;
ALTER TABLE player_current_status_cache DROP COLUMN rn;
CREATE UNIQUE INDEX idx_player_current_status_cache_pid
    ON player_current_status_cache(player_id);
""")
            _con.commit()
            _n = _con.execute("SELECT COUNT(*) FROM player_current_status_cache").fetchone()[0]
            _con.close()
            print(f"[build-site] Wave 25 status cache: {_n:,} rows in {_time.perf_counter()-_t0:.1f}s")
        except Exception as _exc:
            print(f"[build-site] WARN: status cache build failed — {type(_exc).__name__}: {_exc}")

        # Reuse ONE db connection for the whole build. The per-player render
        # fires ~1M small indexed queries; a fresh connection per query costs
        # ~3ms of connect+PRAGMA+mmap setup (~50 min of pure churn across a
        # build). session() reuses one connection (~0.007ms/query). Pure
        # lifecycle change — identical queries + results.
        with db.session():
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

    if args.command == "populate-arcs":
        from cfb_rankings.chronicle.arc_populator import populate_season_arcs

        report = populate_season_arcs(db, season_year=args.season, week=args.week)
        print(
            f"Opened {report['arcs_total']} narrative arcs for season {args.season} "
            f"across {report['teams_with_state']} teams.",
            flush=True,
        )
        for frame, count in report["per_frame"].items():
            if count:
                print(f"  {frame}: {count}", flush=True)
            else:
                print(f"  {frame}: 0 ({report['empty_reasons'].get(frame, '')})", flush=True)
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

    if args.command == "track-lexicon":
        from cfb_rankings.ingest.lexicon_tracker import track_lexicon_terms

        result = track_lexicon_terms(
            db, days=args.days, backfill=args.backfill, terms_file=args.terms_file,
        )
        print(
            f"track-lexicon: scanned={result['docs_scanned']} "
            f"matched={result['docs_matched']} rows={result['rows_written']} "
            f"days={result['days_touched']} backfill={args.backfill}",
            flush=True,
        )
        return

    if args.command == "compute-discourse-keyness":
        from cfb_rankings.discourse.keyness import compute_team_keyness

        seasons: list[int] = []
        for chunk in args.season:
            seasons.extend(int(s) for s in str(chunk).split(",") if s.strip())
        team_slugs = (
            [t.strip() for t in args.teams.split(",") if t.strip()]
            if args.teams else None
        )
        result = compute_team_keyness(
            db,
            seasons=seasons,
            top_n=args.top_n,
            min_team_docs=args.min_team_docs,
            teams=team_slugs,
            weekly=args.weekly,
            commit=args.commit,
        )
        print(
            f"compute-discourse-keyness: teams={result['teams_written']} "
            f"terms={result['terms_written']} scanned={result['docs_scanned']} "
            f"gated={result['docs_gated']} seasons={result['seasons']} "
            f"weekly={args.weekly} commit={args.commit}",
            flush=True,
        )
        return

    if args.command == "compute-discourse-mirror":
        from cfb_rankings.discourse.mirror import compute_discourse_mirror

        seasons = []
        for chunk in args.season:
            seasons.extend(int(s) for s in str(chunk).split(",") if s.strip())
        pair_slugs: list[tuple[str, str]] | None = None
        if args.pairs:
            pair_slugs = []
            for chunk in args.pairs.split(","):
                chunk = chunk.strip()
                if not chunk:
                    continue
                parts = [p.strip() for p in chunk.split(":") if p.strip()]
                if len(parts) != 2:
                    print(f"compute-discourse-mirror: bad pair {chunk!r} "
                          "(want slugA:slugB) — skipped", flush=True)
                    continue
                pair_slugs.append((parts[0], parts[1]))
        result = compute_discourse_mirror(
            db,
            seasons=seasons,
            pairs=pair_slugs,
            commit=args.commit,
        )
        print(
            f"compute-discourse-mirror: pairs={result['pairs']} "
            f"sides={result['sides_written']} terms={result['terms_written']} "
            f"scanned={result['docs_scanned']} gated={result['docs_gated']} "
            f"seasons={result['seasons']} commit={args.commit}",
            flush=True,
        )
        return

    if args.command == "compute-fanbase-voice":
        from cfb_rankings.discourse.voice_profile import compute_fanbase_voice

        seasons = []
        for chunk in args.season:
            seasons.extend(int(s) for s in str(chunk).split(",") if s.strip())
        result = compute_fanbase_voice(
            db,
            seasons=seasons,
            min_mentions=args.min_mentions,
            commit=args.commit,
        )
        print(
            f"compute-fanbase-voice: rows={result['rows_written']} "
            f"cohorts={result['cohorts']} seasons={result['seasons']} "
            f"commit={args.commit}",
            flush=True,
        )
        return

    if args.command == "compute-team-eras":
        from cfb_rankings.discourse.eras import compute_team_eras
        seasons = []
        for s in (args.season or []):
            for part in s.split(","):
                part = part.strip()
                if part:
                    seasons.append(int(part))
        teams = None
        if args.teams:
            teams = [t.strip() for t in args.teams.split(",") if t.strip()]
        result = compute_team_eras(
            db,
            seasons=seasons,
            top_n=args.top_n,
            min_team_docs=args.min_team_docs,
            min_seasons=args.min_seasons,
            teams=teams,
            commit=args.commit,
        )
        print(
            f"compute-team-eras: teams={result['teams_written']} "
            f"terms={result['terms_written']} docs={result['docs_scanned']} "
            f"seasons={result['seasons']} commit={args.commit}",
            flush=True,
        )
        return

    if args.command == "compute-player-descriptors":
        from cfb_rankings.discourse.descriptors import compute_player_descriptors
        seasons = []
        for s in (args.season or []):
            for part in s.split(","):
                part = part.strip()
                if part:
                    seasons.append(int(part))
        player_ids = None
        if args.players:
            player_ids = [int(p.strip()) for p in args.players.split(",") if p.strip()]
        result = compute_player_descriptors(
            db,
            seasons=seasons,
            top_n=args.top_n,
            min_windows=args.min_windows,
            players=player_ids,
            commit=args.commit,
        )
        print(
            f"compute-player-descriptors: players={result['players_written']} "
            f"terms={result['terms_written']} windows={result['windows_scanned']} "
            f"seasons={result['seasons']} commit={args.commit}",
            flush=True,
        )
        return

    if args.command == "build-fan-voice-board":
        from cfb_rankings.discourse.board_page import build_fan_voice_board
        output_dir = Path(args.output_dir) if args.output_dir else Path("output/site")
        path = build_fan_voice_board(db, output_dir, args.season)
        print(f"build-fan-voice-board: wrote {path}", flush=True)
        return

    if args.command == "compute-kwic-quotes":
        from cfb_rankings.discourse.kwic import compute_kwic_quotes
        seasons = []
        for s in (args.season or []):
            for part in s.split(","):
                part = part.strip()
                if part:
                    seasons.append(int(part))
        result = compute_kwic_quotes(db, seasons=seasons, top_terms=args.top_terms, commit=args.commit)
        print(result)
        return

    if args.command == "compute-discourse-atlas":
        from cfb_rankings.discourse.atlas import compute_discourse_atlas
        seasons = []
        for s in (args.season or []):
            for part in s.split(","):
                part = part.strip()
                if part:
                    seasons.append(int(part))
        result = compute_discourse_atlas(db, seasons=seasons, n_clusters=args.n_clusters, commit=args.commit)
        print(result)
        return

    if args.command == "build-fan-voice-leaderboard":
        from cfb_rankings.discourse.leaderboard_page import build_leaderboard_page
        output_dir = Path("output/site")
        path = build_leaderboard_page(db, output_dir, season=args.season)
        print(f"written: {path}")
        return

    if args.command == "seed-rivalry-pairs":
        from cfb_rankings.ingest.rivalry_seed import seed_rivalry_pairs

        result = seed_rivalry_pairs(db, pairs_file=args.pairs_file)
        print(
            f"seed-rivalry-pairs: loaded={result['loaded']} "
            f"unresolved={len(result['unresolved'])}",
            flush=True,
        )
        for miss in result["unresolved"]:
            print(f"  unresolved: {miss}", flush=True)
        return

    if args.command == "seal-capsule":
        from cfb_rankings.fan_metrics.capsule import seal_capsule

        result = seal_capsule(
            db, label=args.label, title=args.title, sealed_on=args.sealed_on,
        )
        print(f"seal-capsule: wrote {result['path']} ({result['sections']} sections)", flush=True)
        return

    if args.command == "rasterize-cards":
        from cfb_rankings.fan_metrics.rasterize import rasterize_suite_cards

        result = rasterize_suite_cards(output_dir=args.output_dir)
        print(
            f"rasterize-cards: {result['written']}/{result['attempted']} PNGs written",
            flush=True,
        )
        return

    if args.command == "compute-delusion-premium":
        from cfb_rankings.fan_metrics.delusion import compute_delusion_premium

        result = compute_delusion_premium(db, season=args.season)
        print(f"compute-delusion-premium season={args.season}: teams={result['teams']}", flush=True)
        return

    if args.command == "compute-aura":
        from cfb_rankings.fan_metrics.aura import compute_aura

        result = compute_aura(db, season=args.season)
        print(
            f"compute-aura season={args.season}: "
            f"cohorts={result['cohorts']} rows={result['rows']}",
            flush=True,
        )
        return

    if args.command == "compute-backometer":
        from cfb_rankings.fan_metrics.backometer import compute_backometer

        result = compute_backometer(db, season=args.season, weeks=args.weeks)
        print(
            f"compute-backometer season={args.season}: "
            f"team_weeks={result['team_weeks']} low_signal={result['low_signal']}",
            flush=True,
        )
        return

    if args.command == "fix-player-positions":
        from cfb_rankings.ingest.position_fix import fix_player_positions

        result = fix_player_positions(db, commit=args.commit)
        mode = "COMMITTED" if args.commit else "DRY-RUN (use --commit to apply)"
        print(
            f"fix-player-positions [{mode}]: candidates={result['candidates']} "
            f"blank_fills={result['blank_fills']} qb_rescues={result['qb_rescues']} "
            f"review_only={result['review_only']} updated={result['updated']}",
            flush=True,
        )
        for line in result["sample"]:
            print(f"  {line}", flush=True)
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

    # Sprint 9 — Edition framework dispatch.
    if args.command in (
        "publish-edition",
        "render-edition",
        "render-homepage",
        "seed-editions",
        "build-editions-archive",
        # Sprint v5-2 + follow-up wired into dispatch (commands were
        # registered via register_edition_subcommands but never routed
        # here, so calls were falling through. The plural variant is the
        # one world_class_enrich actually invokes after seed-editions to
        # auto-fill draft stubs.)
        "generate-edition-cover",
        "generate-edition-covers",
        # Session 6 (2026-05-22) — wire two new editions subcommands
        # into dispatch. Without these entries, publish-site failed with
        # "Unsupported command: backfill-edition-citations" / "...
        # force-reseed-feature" and the W18/W19 wrong-season fix +
        # citation backfill silently no-op'd through the workflow's
        # `|| true` swallowers. Symptom: live W18 dek + body got the
        # seed fix from the upsert detection (which fires in seed-
        # editions, a different command), but inline [N] markers
        # showed as plain text because the citations were never
        # persisted.
        "backfill-edition-citations",
        "force-reseed-feature",
    ):
        rc = args.func(args)
        raise SystemExit(rc or 0)

    # =========================================================================
    # MERGE ZONE — Sprint 13 Receipts dispatch. See CLI parser merge zone.
    # =========================================================================

    if args.command == "extract-predictive-claims":
        from cfb_rankings.receipts import extract as _ex
        sources = args.sources.split(",") if args.sources else None
        result = _ex.run_extraction(
            days=args.days,
            source_names=sources,
            limit_docs=args.limit_docs,
            haiku_batch=args.haiku_batch,
            offline=True if args.offline else None,
        )
        print(json.dumps(result, indent=2), flush=True)
        return

    if args.command == "load-historical-consensus":
        from cfb_rankings.receipts import consensus as _co
        if args.kind == "all":
            result = _co.load_all()
        elif args.kind == "vegas":
            result = {"vegas_lines": _co.load_vegas_lines()}
        elif args.kind == "polls":
            result = {"polls": _co.load_polls()}
        elif args.kind == "sp_plus":
            result = {"sp_plus": _co.load_sp_plus()}
        elif args.kind == "polymarket":
            result = {"polymarket": _co.load_polymarket()}
        elif args.kind == "corpus":
            result = {"corpus_aggregate": _co.load_corpus_aggregate()}
        print(json.dumps(result, indent=2), flush=True)
        return

    if args.command == "compute-surprise-index":
        from cfb_rankings.receipts import surprise as _su
        if args.claim_id is not None:
            from cfb_rankings.receipts.runtime import db_conn as _conn
            with _conn() as c:
                row = c.execute(
                    "SELECT * FROM predictive_claims WHERE id = ?",
                    (args.claim_id,),
                ).fetchone()
                if not row:
                    print(json.dumps({"error": "claim_not_found"}), flush=True)
                    return
                score, breakdown = _su.compute(row)
                c.execute(
                    "UPDATE predictive_claims SET surprise_index = ?, "
                    "surprise_index_components_json = ? WHERE id = ?",
                    (score, json.dumps(breakdown), args.claim_id),
                )
                c.commit()
                print(json.dumps({"claim_id": args.claim_id, "score": score,
                                  "breakdown": breakdown}, indent=2), flush=True)
            return
        result = _su.compute_batch(only_unscored=True)
        print(json.dumps(result, indent=2), flush=True)
        return

    if args.command == "resolve-outcomes":
        from cfb_rankings.receipts import resolve as _re
        result = _re.resolve_batch(window_end_before=args.window_end_before)
        print(json.dumps(result, indent=2), flush=True)
        return

    if args.command == "generate-best-calls":
        from cfb_rankings.receipts import best_calls as _bc
        result = _bc.generate(args.year, n=args.n, opus_top=args.opus_top)
        print(json.dumps(result, indent=2), flush=True)
        return

    if args.command == "recompute-source-profiles":
        from cfb_rankings.receipts import source_profiles as _sp
        result = _sp.recompute_all(min_takes=args.min_takes, top_n=args.top_n)
        print(json.dumps(result, indent=2), flush=True)
        return

    if args.command == "render-receipts":
        from cfb_rankings.receipts import render as _re
        result = _re.render_all()
        print(json.dumps(result, indent=2), flush=True)
        return

    # END MERGE ZONE — Sprint 13

    # =========================================================================
    # MERGE ZONE — Sprint 14: The Daily dispatch.
    # =========================================================================
    # ---- sprint 14: daily ----

    if args.command == "generate-daily":
        from datetime import date as _date
        from cfb_rankings.daily import select_inputs, synthesize_takes, persist_edition
        from cfb_rankings.llm_runtime import CostMeter, CostCeilingExceeded
        apply_runtime_migrations(db)
        edition_date = args.date or _date.today().isoformat()
        # Pattern C: per-CLI-invocation meter. Per-run ceiling = $0.50
        # (IMPLEMENTATION_PLAN.md Part 6.5 tier1.daily_lead = $5/week ÷ ~7 runs ≈ $0.71;
        # we use a conservative $0.50 against the v5.4 cost-tolerance target).
        cost_meter = CostMeter(
            ceiling_usd=0.5,
            label=f"cli.generate-daily.{edition_date}",
        )
        try:
            with db.connection() as conn:
                bundle = select_inputs(conn, edition_date)
                takes = synthesize_takes(bundle, _meter=cost_meter)
                persist_edition(conn, bundle, takes)
        except CostCeilingExceeded as exc:
            print(f"::error::CostMeter halted run: {exc}", flush=True)
            return 1
        vv_pass = sum(1 for t in takes if t.voice_validator_passed)
        print(f"generate-daily {edition_date}: {len(takes)} takes generated, "
              f"voice_validator passed {vv_pass}/{len(takes)} "
              f"spent=${cost_meter.spent_usd:.4f} / ${cost_meter.ceiling_usd:.2f}")
        for t in takes:
            print(f"  #{t.rank_position}: {t.headline[:80]}")
        return

    if args.command == "render-daily":
        from datetime import date as _date
        from cfb_rankings.daily import render_daily
        edition_date = args.date or _date.today().isoformat()
        with db.connection() as conn:
            paths = render_daily(conn, edition_date, output_dir=args.output_dir)
        for p in paths:
            print(f"  wrote: {p}")
        return

    if args.command == "daily-history":
        from cfb_rankings.daily import fetch_recent_editions
        with db.connection() as conn:
            editions = fetch_recent_editions(conn, limit=args.limit)
        if not editions:
            print("No Daily editions found in DB.")
            return
        print(f"{'Date':<14} {'Status':<12} {'Takes':>6} {'Voice':>6} {'Model'}")
        print("-" * 60)
        for ed in editions:
            vv = "OK" if ed["voice_validator_passed"] else "WARN"
            model = (ed.get("generation_model") or "")[:24]
            print(f"{ed['edition_date']:<14} {ed['status']:<12} {ed['takes_count']:>6} {vv:>6}  {model}")
        return

    # END MERGE ZONE — Sprint 14

    # =========================================================================
    # MERGE ZONE — Sprint 15 Reaction Story dispatch. See CLI parser merge zone.
    # =========================================================================

    if args.command == "reactions-check-triggers":
        from cfb_rankings.reactions.triggers import check_triggers
        from cfb_rankings.reactions.synthesizer import (
            generate_reaction,
            synthesize_reactions_batch,
        )
        from cfb_rankings.reactions.cohort_divergence import extract_cohort_divergence
        from cfb_rankings.reactions.data import fetch_wire_entry
        from cfb_rankings.reactions.renderer import render_story, render_archive
        events = check_triggers(
            hours=args.hours,
            force_wire_id=args.force_trigger,
        )
        print(json.dumps(
            [{"wire_id": e.wire_id, "entity_slug": e.primary_entity_slug,
              "suggested_slug": e.suggested_slug, "velocity": e.velocity,
              "reason": e.trigger_reason}
             for e in events],
            indent=2,
        ), flush=True)
        if args.auto and events:
            # Sprint v5-1.5c: build the (trigger, wire_row, cohort_div, story_slug)
            # tuple list once; routing decides whether to fan out via batch.
            stories_input: list = []
            for evt in events:
                wire_row = fetch_wire_entry(evt.wire_id)
                if wire_row is None:
                    continue
                cohort_div = extract_cohort_divergence(wire_row)
                stories_input.append((evt, wire_row, cohort_div, evt.suggested_slug))

            batch_choice = getattr(args, "batch", "auto")
            use_batch = (
                batch_choice == "on"
                or (batch_choice == "auto" and len(stories_input) >= 2)
            )

            if use_batch and stories_input:
                stories = synthesize_reactions_batch(stories_input)
                for story in stories:
                    render_story(story.slug)
                    print(f"  auto-generated (batch): {story.slug}", flush=True)
                if stories:
                    render_archive()
            else:
                for (evt, wire_row, cohort_div, slug) in stories_input:
                    story = generate_reaction(evt, wire_row, cohort_div, slug)
                    render_story(story.slug)
                    render_archive()
                    print(f"  auto-generated: {story.slug}", flush=True)
        return

    if args.command == "generate-reaction":
        from cfb_rankings.reactions.triggers import TriggerEvent
        from cfb_rankings.reactions.synthesizer import generate_reaction
        from cfb_rankings.reactions.cohort_divergence import extract_cohort_divergence
        from cfb_rankings.reactions.data import fetch_wire_entry
        wire_row = fetch_wire_entry(args.wire_id)
        if wire_row is None:
            print(json.dumps({"error": "wire_entry_not_found", "wire_id": args.wire_id}), flush=True)
            return
        entity_slug = wire_row.get("program_slug") or args.slug.split("-")[0]
        actor_kind = wire_row.get("actor_kind", "program")
        etype_map = {"program": "team", "player": "player", "coach": "coach",
                     "conference": "conference", "committee": "event"}
        evt = TriggerEvent(
            wire_id=args.wire_id,
            primary_entity_slug=entity_slug,
            primary_entity_type=etype_map.get(actor_kind, "team"),
            suggested_slug=args.slug,
            velocity=float(wire_row.get("fan_intel_velocity_spike") or 70),
            trigger_reason="manual",
        )
        cohort_div = extract_cohort_divergence(wire_row)
        story = generate_reaction(evt, wire_row, cohort_div, args.slug)
        print(json.dumps({
            "slug": story.slug,
            "headline": story.headline,
            "surprise_index": story.surprise_index,
            "voice_validator_passed": bool(story.voice_validator_passed),
            "generation_model": story.generation_model,
        }, indent=2), flush=True)
        return

    if args.command == "render-reactions":
        from cfb_rankings.reactions.renderer import render_story, render_all
        if args.slug:
            path = render_story(args.slug)
            print(json.dumps({"rendered": str(path) if path else None}), flush=True)
        else:
            result = render_all()
            print(json.dumps(result, indent=2), flush=True)
        return

    if args.command == "reactions-history":
        from cfb_rankings.reactions.data import list_stories
        stories = list_stories(limit=args.limit)
        print(json.dumps(
            [{"slug": s.slug, "headline": s.headline, "triggered_at": s.triggered_at_utc,
              "surprise_index": s.surprise_index, "status": s.status,
              "voice_ok": bool(s.voice_validator_passed)}
             for s in stories],
            indent=2,
        ), flush=True)
        return

    # END MERGE ZONE — Sprint 15

    # ---- Sprint 12: The Wire dispatch ----
    if args.command == "wire-ingest":
        from cfb_rankings.wire.ingestion import collect_recent_actions, upsert_actions
        # Cleanup pass: remove stale cfbd-recruit wire entries that
        # reference graduated classes. The recruit source used to be
        # unfiltered and seeded with a static rng (see PR #9 / #11), so
        # the table accumulated 2016-2019 commits with fake May-2026
        # timestamps. Now we sweep them before each ingest so the page
        # only shows the actively-recruiting class.
        from datetime import datetime as _dt
        current_year = _dt.utcnow().year
        # Delete recruit entries where the action text references a
        # class year older than current_year. Action text format is
        # f"... commits {season_year}" so we match on " commits 20XX".
        purged = 0
        for stale_year in range(2010, current_year):
            cursor = db.execute(
                """
                delete from wire_entries
                where source_kind = 'cfbd-recruit'
                  and action like :pattern
                """,
                {"pattern": f"% commits {stale_year}"},
            )
            try:
                purged += cursor.rowcount or 0
            except Exception:
                pass
        if purged:
            print(f"wire-ingest: purged {purged} stale recruit entries "
                  f"(class < {current_year})", flush=True)

        actions = collect_recent_actions(
            db, days=args.days, target_count=args.target_count,
        )
        stats = upsert_actions(db, actions)
        print(json.dumps(
            {"collected": len(actions), "purged_stale": purged, **stats},
            indent=2,
        ), flush=True)
        return

    if args.command == "wire-generate-editorial":
        from cfb_rankings.wire.editorial import (
            generate_editorial_for_pending,
            generate_uncovered_rows_batch,
            _lookup_authored,
        )
        batch_choice = getattr(args, "batch", "off")
        # 'auto' counts uncovered rows in window to decide.
        if batch_choice == "auto":
            rows = db.query_all(
                """
                select id, occurred_at, program_slug, program_display, actor_kind,
                       action, fan_intel_velocity_spike, related_thread_slug
                from wire_entries
                where occurred_at >= datetime('now', :since)
                """,
                {"since": f"-{int(args.days)} days"},
            )
            n_uncovered = sum(1 for r in rows if _lookup_authored(r) is None)
            use_batch = n_uncovered >= 2
        else:
            use_batch = batch_choice == "on"

        if use_batch:
            stats = generate_uncovered_rows_batch(db, days=args.days)
            # Run the deterministic pass too so non-uncovered rows still get
            # their why_it_matters / impact_label fields if missing.
            det_stats = generate_editorial_for_pending(
                db, days=args.days, overwrite=args.overwrite,
            )
            stats = {**det_stats, "batch_llm": stats}
        else:
            stats = generate_editorial_for_pending(
                db, days=args.days, overwrite=args.overwrite,
            )
        print(json.dumps(stats, indent=2), flush=True)
        return

    if args.command == "render-wire":
        from cfb_rankings.wire.renderer import render_all as render_wire_all
        from cfb_rankings.wire.homepage_integration import refresh_homepage_wire_block
        result = render_wire_all(db, days=args.days)
        if not args.skip_homepage:
            homepage_path = (
                Path(args.homepage_path) if args.homepage_path else None
            )
            patch_stats = refresh_homepage_wire_block(
                db, homepage_path=homepage_path, limit=args.limit,
            )
            result["homepage_patch"] = patch_stats
        print(json.dumps(result, indent=2, default=str), flush=True)
        return

    # ---- Sprint v5-1 Day 4 follow-up: refresh-portal-heat ----
    if args.command == "refresh-portal-heat":
        from cfb_rankings.portal_heat.renderer import render_all as render_portal_heat
        output_dir = Path(args.output_dir) if args.output_dir else None
        result = render_portal_heat(db, output_dir=output_dir, days=args.days)
        print(json.dumps(result, indent=2, default=str), flush=True)
        return

    # ---- Sprint 8.5: Pulse follow-ups ----
    if args.command == "prepare-pulse":
        from cfb_rankings.team_pages.pulse_state import TOP_ENTITIES_FULL, TOP_ENTITIES_PARTIAL
        from cfb_rankings.team_pages import pulse_themes, pulse_lede

        # Build the run list from the constants — PR #82 (2026-05-17
        # audit2) expanded TOP_ENTITIES_PARTIAL to cover all 17 profiled
        # programs, but this CLI was hardcoding the old 11-entry list
        # in place and ignoring the constants entirely. Read the
        # constants now so a future expansion of TOP_ENTITIES_FULL /
        # TOP_ENTITIES_PARTIAL automatically takes effect.
        #
        # The conference vs team split is encoded in well-known prefixes:
        # conference slugs use "sec" / "fbs-big-ten" / "acc" / "big-12" /
        # "american-athletic" / "mountain-west"; everything else is a team.
        _CONFERENCE_SLUGS = {
            "sec", "fbs-big-ten", "acc", "big-12",
            "american-athletic", "mountain-west",
        }

        def _classify(slug: str) -> tuple[str, str]:
            return (slug, "conference" if slug in _CONFERENCE_SLUGS else "team")

        if args.entity:
            run_list = [(args.entity, args.entity_type)]
        else:
            # FULL tier first (3 themes each), then PARTIAL (1 theme + 1 lede).
            # sorted() gives stable ordering for telemetry; set membership is
            # the source of truth.
            run_list = (
                [_classify(s) for s in sorted(TOP_ENTITIES_FULL)]
                + [_classify(s) for s in sorted(TOP_ENTITIES_PARTIAL)]
            )

        batch_choice = getattr(args, "batch", "auto")
        use_batch = (
            batch_choice == "on"
            or (batch_choice == "auto" and len(run_list) >= 2)
        )

        OPUS_SLUGS = {"alabama", "ohio-state", "georgia"}

        with db.connection() as conn:
            if use_batch:
                # Sprint v5-1.5c: flatten into one (slug, etype, tier, name)
                # list for the Stage-2 themes batch. Stage-1 Haiku candidate
                # scan remains per-entity inside extract_entities_themes_batch.
                batch_themes_input: list[tuple[str, str, str, str | None]] = []
                for slug, etype in run_list:
                    if args.tier:
                        tier = args.tier
                    else:
                        tier = "full" if slug in TOP_ENTITIES_FULL else "partial"
                    batch_themes_input.append((slug, etype, tier, None))
                    print(f"  prepare-pulse: {slug} ({etype}) tier={tier} [batch]", flush=True)

                themes_by_entity = pulse_themes.extract_entities_themes_batch(
                    batch_themes_input, conn,
                )

                # Build lede batch from the themes output, keeping the same
                # opus/sonnet routing as the sync handler.
                batch_lede_input: list[tuple[str, str, list[dict], str, str | None]] = []
                for slug, etype, tier, _name in batch_themes_input:
                    themes = themes_by_entity.get((slug, etype), [])
                    model_tier = "opus" if slug in OPUS_SLUGS else "sonnet"
                    batch_lede_input.append((slug, etype, themes, model_tier, None))

                lede_results = pulse_lede.generate_entity_ledes_batch(
                    batch_lede_input, conn,
                )

                for slug, etype, _tier, _name in batch_themes_input:
                    themes = themes_by_entity.get((slug, etype), [])
                    lede_result = lede_results.get((slug, etype), {})
                    lede_ok = lede_result.get("voice_validator_passed", False)
                    print(
                        f"    {slug} ({etype}): themes={len(themes)} "
                        f"lede_ok={lede_ok} mode={lede_result.get('mode')}",
                        flush=True,
                    )
            else:
                for slug, etype in run_list:
                    if args.tier:
                        tier = args.tier
                    else:
                        tier = "full" if slug in TOP_ENTITIES_FULL else "partial"
                    print(f"  prepare-pulse: {slug} ({etype}) tier={tier}", flush=True)
                    themes = pulse_themes.extract_entity_themes(slug, etype, tier, conn)
                    model_tier = "opus" if slug in OPUS_SLUGS else "sonnet"
                    lede_result = pulse_lede.generate_entity_lede(
                        slug, etype, themes, model_tier, conn
                    )
                    lede_ok = lede_result.get("voice_validator_passed", False)
                    print(
                        f"    themes={len(themes)} lede_ok={lede_ok} "
                        f"mode={lede_result.get('mode')}",
                        flush=True,
                    )
        print("prepare-pulse complete.", flush=True)
        return

    if args.command == "render-conferences-pulse":
        from cfb_rankings.conferences_pulse import renderer as _cpr
        import sqlite3

        output_dir = getattr(args, "output_dir", "output/site/conferences")
        with db.connection() as conn:
            if getattr(args, "all_conferences", False):
                result = _cpr.render_all_conferences(conn, output_dir)
                print(f"render-conferences-pulse: {result['rendered']}/{result['total']} rendered "
                      f"-> {output_dir}/", flush=True)
            elif args.slug:
                html = _cpr.render_conference_pulse_section(args.slug, conn)
                print(f"render-conferences-pulse: {args.slug} -> {len(html)} chars", flush=True)
            else:
                print("render-conferences-pulse: specify --all or --slug", flush=True)
        return

    if args.command == "render-the-room":
        from cfb_rankings.team_pages import the_room_renderer as _trr

        with db.connection() as conn:
            result = _trr.generate_all_player_rooms(conn, top_n=args.top)
        print(
            f"render-the-room: processed {result['processed']} players, "
            f"{result['live']} live, {result['fallback']} fallback",
            flush=True,
        )
        return

    if args.command == "classify-player-sentiment":
        from cfb_rankings.team_pages.sentiment_classifier import classify_player_targets
        import sqlite3

        with db.connection() as conn:
            result = classify_player_targets(
                conn,
                limit=getattr(args, "limit", None),
                dry_run=getattr(args, "dry_run", False),
            )
        print(f"classify-player-sentiment: {result}", flush=True)
        return

    # -------------------------------------------------------------------------
    # Sprint 16: The Mailbag
    # -------------------------------------------------------------------------
    if args.command == "mailbag-seed-submissions":
        from cfb_rankings.mailbag.submissions import seed_representative_submissions
        n = getattr(args, "n", 5)
        ids = seed_representative_submissions(n)
        print(f"mailbag-seed-submissions: planted {len(ids)} seed rows: {ids}", flush=True)
        return

    if args.command == "mailbag-curate-submissions":
        from cfb_rankings.mailbag.curator import curate_for_edition
        from cfb_rankings.mailbag.data import current_edition_slug
        edition = getattr(args, "edition", None) or current_edition_slug()
        max_answers = getattr(args, "max_answers", 5)
        result = curate_for_edition(edition, max_answers=max_answers)
        print(
            f"mailbag-curate-submissions: edition={result['edition_slug']} "
            f"selected={len(result['selected_ids'])} rejected={len(result['rejected_ids'])} "
            f"bootstrap_seeded={result['bootstrap_seeded']} "
            f"publish_date={result['publish_date']}",
            flush=True,
        )
        return

    if args.command == "mailbag-generate-answers":
        from cfb_rankings.mailbag.synthesizer import (
            generate_answers_for_edition,
            generate_answers_for_edition_batch,
        )
        from cfb_rankings.mailbag.data import (
            current_edition_slug,
            db_conn as _mailbag_db_conn,
            list_curated_for_edition,
        )
        from cfb_rankings.llm_runtime import CostMeter, CostCeilingExceeded
        edition = getattr(args, "edition", None) or current_edition_slug()
        # Pattern C: per-CLI-invocation meter. Per-run ceiling = $1.00
        # (IMPLEMENTATION_PLAN.md Part 6.5 tier1.mailbag = $8/week ÷ ~7 runs).
        cost_meter = CostMeter(
            ceiling_usd=1.0,
            label=f"cli.mailbag-generate-answers.{edition}",
        )
        # Sprint v5-1.5c batch-path activation:
        # 'auto' (default) batches when there are >=2 curated questions; that's
        # where the 50%-off batch discount + 1h-cache savings actually fire.
        # 'on' force-batches even N==1 (useful for testing the batch path).
        # 'off' keeps the legacy sync subprocess loop (interactive UX).
        batch_choice = getattr(args, "batch", "auto")
        n_curated = 0
        if batch_choice == "auto":
            with _mailbag_db_conn() as _conn:
                n_curated = len(list_curated_for_edition(_conn, edition))
        use_batch = (
            batch_choice == "on"
            or (batch_choice == "auto" and n_curated >= 2)
        )
        try:
            if use_batch:
                result = generate_answers_for_edition_batch(edition, _meter=cost_meter)
            else:
                result = generate_answers_for_edition(edition, _meter=cost_meter)
        except CostCeilingExceeded as exc:
            print(f"::error::CostMeter halted run: {exc}", flush=True)
            return 1
        print(
            f"mailbag-generate-answers: edition={result['edition_slug']} "
            f"answers={result['answers_generated']} "
            f"voice_passed={result['voice_passed']} voice_failed={result['voice_failed']} "
            f"tokens_in={result['total_input_tokens']} tokens_out={result['total_output_tokens']} "
            f"model_usage={result['model_usage']} "
            f"mode={result.get('mode', 'sync')} "
            f"spent=${cost_meter.spent_usd:.4f} / ${cost_meter.ceiling_usd:.2f}",
            flush=True,
        )
        return

    if args.command == "render-mailbag":
        from cfb_rankings.mailbag.renderer import render_all
        edition = getattr(args, "edition", None)
        result = render_all(edition_slug=edition)
        print(
            f"render-mailbag: output_root={result['output_root']} "
            f"edition_pages={len(result['edition_pages'])} "
            f"index={result['index']} archive={result['archive']} submit={result['submit']}",
            flush=True,
        )
        return

    if args.command == "mailbag-history":
        from cfb_rankings.mailbag.data import db_conn, list_recent_editions, list_answers_for_edition
        limit = getattr(args, "limit", 10)
        with db_conn() as conn:
            editions = list_recent_editions(conn, limit=limit)
        if not editions:
            print("mailbag-history: no editions found", flush=True)
            return
        print(f"{'EDITION':<14} {'DATE':<12} {'STATUS':<12} {'NOTES'}", flush=True)
        print("-" * 60, flush=True)
        for ed in editions:
            slug = ed.get("edition_slug", "")
            date_str = ed.get("publish_date", "")
            status = ed.get("status", "")
            notes = (ed.get("notes") or "")[:40]
            print(f"{slug:<14} {date_str:<12} {status:<12} {notes}", flush=True)
        return

    if args.command == "coaching-fetch-news":
        from cfb_rankings.ingest.sources import coaching_tracker
        counter = coaching_tracker.fetch_coaching_news(db, days=args.days)
        print(
            f"coaching-fetch-news: fetched={counter['fetched']} "
            f"matched_keyword={counter['matched_keyword']} "
            f"persisted={counter['persisted']} errors={counter['errors']}",
            flush=True,
        )
        return

    # ----------------------------------------------------------------
    # Sprint v5-3 owner Interrupt 2 — quality-loop guardrail commands.
    # ----------------------------------------------------------------
    if args.command == "quality-loop-status":
        from cfb_rankings.circuit_state import status_report
        rows = status_report(db)
        if getattr(args, "json", False):
            print(json.dumps(rows, indent=2))
            return
        # Human-readable table.
        if not rows:
            print("quality-loop-status: no surfaces configured.")
            return
        header = (
            f"{'surface':<32} {'active':<18} {'24h_spend':>10} "
            f"{'ceiling':>10} {'frac':>6}  degraded"
        )
        print(header)
        print("-" * len(header))
        for r in rows:
            ceiling = r["ceiling_24h_usd"]
            ceiling_s = f"${ceiling:.2f}" if ceiling is not None else "  --  "
            degraded_s = "YES" if r["degraded"] else " "
            if r["degraded"] and r.get("degrade_reason"):
                degraded_s = f"YES ({r['degrade_reason']})"
            print(
                f"{r['surface']:<32} "
                f"{(r['active_pattern'] or '-'):<18} "
                f"${r['spend_24h_usd']:>9.4f} "
                f"{ceiling_s:>10} "
                f"{r['fraction']:>6.2f}  {degraded_s}"
            )
        return

    if args.command == "quality-loop-reenable":
        from cfb_rankings.circuit_state import reset_surface_degrade
        cleared = reset_surface_degrade(db, args.surface)
        if cleared:
            print(
                f"quality-loop-reenable: cleared degrade marker for "
                f"{args.surface!r}. Configured Pattern C flag is now active again."
            )
        else:
            print(
                f"quality-loop-reenable: no degrade marker found for "
                f"{args.surface!r} (already enabled or never tripped)."
            )
        return

    if args.command == "generate-chronicle-visuals":
        from cfb_rankings.chronicle.visuals import (
            VisualId,
            generate_visuals_for_team,
            generate_all_visuals,
        )
        # Resolve which visuals to run
        visual_ids = None
        if args.visual:
            try:
                visual_ids = [VisualId(args.visual)]
            except ValueError:
                raise RuntimeError(
                    f"unknown visual id {args.visual!r}. Try one of: "
                    f"{[v.value for v in VisualId]}"
                )

        if args.slug:
            results = generate_visuals_for_team(
                db,
                slug=args.slug,
                season_year=args.season,
                week_number=args.week,
                visual_ids=visual_ids,
                force_regenerate=args.force,
            )
            print(f"generate-chronicle-visuals slug={args.slug}: {len(results)} visuals")
            for r in results:
                print(
                    f"  {r.spec.visual_id.value:30s} "
                    f"score={r.score.total:.2f}  n={r.receipt.sample_n}  "
                    f"suppressed={r.suppressed}"
                )
            return

        # Batch across all FBS
        by_slug = generate_all_visuals(
            db,
            season_year=args.season,
            week_number=args.week,
            force_regenerate=args.force,
            limit_teams=args.limit_teams,
        )
        teams_with_visuals = sum(1 for slugs in by_slug.values() if slugs)
        total_visuals = sum(len(v) for v in by_slug.values())
        print(
            f"generate-chronicle-visuals: {teams_with_visuals} teams · "
            f"{total_visuals} visuals generated for season {args.season}"
        )
        return

    # ------------------------------------------------ team preview (Milestone A)
    if args.command == "build-team-preview-snapshots":
        from cfb_rankings.team_preview import build_team_preview_snapshots
        result = build_team_preview_snapshots(db, args.season, args.as_of, slugs=args.slug)
        print(
            f"build-team-preview-snapshots season={args.season} as-of={args.as_of}: "
            f"written={result['written']} skipped={result['skipped']} "
            f"targets={result['targets']}"
        )
        return

    if args.command == "compute-season-path-projections":
        from cfb_rankings.team_preview import compute_season_path_projections
        result = compute_season_path_projections(db, args.season, args.as_of, slugs=args.slug)
        print(
            f"compute-season-path-projections season={args.season} as-of={args.as_of}: "
            f"written={result['written']} skipped={result['skipped']} "
            f"targets={result['targets']}"
        )
        return

    if args.command == "build-roster-reload-snapshots":
        from cfb_rankings.team_preview import build_roster_reload_snapshots
        result = build_roster_reload_snapshots(db, args.season, args.as_of, slugs=args.slug)
        print(
            f"build-roster-reload-snapshots season={args.season} as-of={args.as_of}: "
            f"written={result['written']} skipped={result['skipped']} "
            f"position_rows={result['position_rows']} targets={result['targets']}"
        )
        return

    if args.command == "build-team-preview-layer":
        result = _build_team_preview_layer(
            db,
            season_year=args.season,
            as_of_date=args.as_of,
            slugs=args.slug,
        )
        _print_team_preview_layer_result(result)
        minimum_written = min(
            int(result["snapshots"]["written"]),
            int(result["season_path"]["written"]),
            int(result["roster_reload"]["written"]),
        )
        if minimum_written <= 0 and not args.allow_empty:
            raise RuntimeError(
                "Team-preview layer wrote zero rows for at least one builder. "
                "Re-run with --allow-empty only for empty/dev databases."
            )
        return

    if args.command == "generate-team-preview-claims":
        from cfb_rankings.team_preview.llm_synthesis import generate_team_preview_claims
        report = generate_team_preview_claims(
            db,
            season_year=args.season,
            as_of_date=args.as_of,
            slugs=args.slug,
            allow_cloud=args.allow_cloud,
        )
        if args.json:
            import dataclasses
            print(json.dumps(dataclasses.asdict(report), indent=2, default=str))
        else:
            print(
                f"generate-team-preview-claims season={args.season} as-of={args.as_of}: "
                f"targets={report.targets} approved={report.approved} "
                f"rejected={report.rejected} skipped={report.skipped}"
            )
            for item in report.errors[:12]:
                print(f"  {item}")
            if len(report.errors) > 12:
                print(f"  ... {len(report.errors) - 12} more")
        return

    if args.command == "team-preview-llm-status":
        from cfb_rankings.team_preview.llm_synthesis import preview_llm_status
        rows = preview_llm_status(allow_cloud=args.allow_cloud)
        print("team-preview-llm-status")
        for row in rows:
            health = "ok" if row["healthy"] else "down"
            print(
                f"  {row['role']:<7} {row['tiers']:<8} {health:<4} "
                f"{row['backend']} :: {row['model_id']}"
            )
        return

    if args.command == "import-bowl-record-ledger":
        from cfb_rankings.team_preview.bowl_ledger import import_bowl_ledger
        result = import_bowl_ledger(db, args.source, as_of=args.as_of)
        print(
            f"import-bowl-record-ledger source={args.source}: "
            f"rows={result['rows']} matched_team_id={result['matched_team_id']} "
            f"unmatched={result['unmatched']}"
        )
        return

    if args.command == "audit-team-preview-readiness":
        from cfb_rankings.team_preview.readiness import audit_team_preview_readiness
        report = audit_team_preview_readiness(db, args.season, args.as_of, slugs=args.slug)
        counts = report.counts()
        if getattr(args, "json", False):
            import dataclasses
            print(json.dumps(
                {"counts": counts, "teams": [dataclasses.asdict(t) for t in report.teams]},
                indent=2,
            ))
        else:
            print(
                f"audit-team-preview-readiness season={args.season} as-of={args.as_of}"
            )
            for key, val in counts.items():
                print(f"  {key}: {val}")
        return

    if args.command == "prediction-ledger":
        from cfb_rankings.calibration import (
            calibration_summary,
            record_archetype_predictions,
            record_season_win_predictions,
            resolve_due_predictions,
        )
        if args.action == "record-archetypes":
            if args.season is None:
                raise SystemExit("prediction-ledger --action record-archetypes requires --season")
            result = record_archetype_predictions(db, args.season)
            print(
                f"prediction-ledger record-archetypes season={result['season']}: "
                f"recorded={result['recorded']} (from {result['source_season']})"
            )
            return
        if args.action == "record-season-wins":
            if args.season is None:
                raise SystemExit("prediction-ledger --action record-season-wins requires --season")
            result = record_season_win_predictions(db, args.season)
            print(
                f"prediction-ledger record-season-wins season={result['season']}: "
                f"recorded={result['recorded']}"
            )
            return
        if args.action == "resolve":
            kinds = [args.kind] if args.kind else None
            result = resolve_due_predictions(db, kinds=kinds)
            print(
                f"prediction-ledger resolve: due={result['due']} "
                f"resolved={result['resolved']} skipped={result['skipped']} "
                f"by_kind={result['by_kind']}"
            )
            return
        if args.action == "summary":
            summary = calibration_summary(
                db, model_id=args.model_id, prediction_kind=args.kind, last_n=args.last_n
            )
            if args.json:
                print(json.dumps(summary, indent=2))
            else:
                print(
                    f"prediction-ledger summary model={summary['model_id'] or 'ALL'} "
                    f"kind={summary['prediction_kind'] or 'ALL'}: "
                    f"logged={summary['total_logged']} resolved={summary['resolved']} "
                    f"mean_accuracy={summary['mean_accuracy']}"
                )
                for band, stats in sorted(summary["band_accuracy"].items()):
                    print(f"  {band}: n={stats['n']} accuracy={stats['accuracy']}")
            return
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

    _try_build_team_preview_layer_for_publish(db)
    report_output = write_latest_rankings_report(db=db, output_path=output_path, limit=limit)
    site_output = build_static_site(db=db, output_dir=site_output_dir)
    print(f"Built rankings report: {report_output}", flush=True)
    print(f"Built static site: {site_output}", flush=True)
    if open_report:
        webbrowser.open(Path(report_output).resolve().as_uri())
    return report_output, site_output


def _default_team_preview_context(
    season_year: int | None,
    as_of_date: str | None,
) -> tuple[int, str]:
    today = date.today()
    return season_year or today.year, as_of_date or today.isoformat()


def _build_team_preview_layer(
    db: "Database",
    *,
    season_year: int | None = None,
    as_of_date: str | None = None,
    slugs: list[str] | None = None,
) -> dict[str, object]:
    from cfb_rankings.team_preview import (
        build_roster_reload_snapshots,
        build_team_preview_snapshots,
        compute_season_path_projections,
    )

    season, as_of = _default_team_preview_context(season_year, as_of_date)
    snapshots = build_team_preview_snapshots(db, season, as_of, slugs=slugs)
    season_path = compute_season_path_projections(db, season, as_of, slugs=slugs)
    roster_reload = build_roster_reload_snapshots(db, season, as_of, slugs=slugs)
    return {
        "season": season,
        "as_of": as_of,
        "snapshots": snapshots,
        "season_path": season_path,
        "roster_reload": roster_reload,
    }


def _print_team_preview_layer_result(result: dict[str, object]) -> None:
    snapshots = result["snapshots"]
    season_path = result["season_path"]
    roster_reload = result["roster_reload"]
    print(
        f"build-team-preview-layer season={result['season']} as-of={result['as_of']}: "
        f"snapshots={snapshots['written']}/{snapshots['targets']} "
        f"season_path={season_path['written']}/{season_path['targets']} "
        f"roster_reload={roster_reload['written']}/{roster_reload['targets']} "
        f"position_rows={roster_reload['position_rows']}",
        flush=True,
    )


def _try_build_team_preview_layer_for_publish(db: "Database") -> None:
    try:
        result = _build_team_preview_layer(db)
    except Exception as exc:
        print(
            f"[team-preview] warning: preview layer refresh failed before render: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )
        return
    _print_team_preview_layer_result(result)


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
    """Find a model_runs row for (season, week) with backed-up power_ratings.

    Search order, all gated on `exists (select 1 from power_ratings_weekly
    where model_run_id = mr.model_run_id)` so we never return a model_run
    that has no power data:

      1. Exact week match — original behavior.
      2. Latest model_run for the season with week <= requested. Handles
         late-week postseason data when the caller asked for week 16.
      3. Latest model_run for the season at any week. Handles seasons
         that were only run end-of-season (week 21 final, no week-16
         intermediate). The 2026-05-17 Heisman 2025 failure was exactly
         this case — model_runs for 2025 had only week=21, but the
         Heisman model's `--through-week 16` lookup demanded week=16
         exactly. The model itself caps feature extraction at week 16
         via _heisman_feature_week, so finding the model_run at any
         week is safe.

    Returns None only when the season has zero model_runs entries with
    power data at all.
    """
    # Pass 1: exact (season, week) match
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
    if row is not None:
        return {
            "model_run_id": int(row["model_run_id"]),
            "week": int(row["week"]),
            "model_version": str(row.get("model_version") or ""),
        }
    # Pass 2: nearest run for season with week <= requested
    row = db.query_one(
        """
        select mr.model_run_id, mr.week, mr.model_version
        from model_runs mr
        where mr.season_year = %(season_year)s
          and mr.week <= %(week)s
          and exists (
            select 1
            from power_ratings_weekly p
            where p.model_run_id = mr.model_run_id
          )
        order by mr.week desc, mr.model_run_id desc
        limit 1
        """,
        {"season_year": season, "week": week},
    )
    if row is not None:
        return {
            "model_run_id": int(row["model_run_id"]),
            "week": int(row["week"]),
            "model_version": str(row.get("model_version") or ""),
        }
    # Pass 3: any model_run for the season (e.g. only the final snapshot
    # exists). Heisman model caps at week 16 internally, so even a
    # week-21 model_run will produce week-16-capped feature extraction.
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
