"""One-pass data inventory generator for cfb_rankings.db.

Runs against every table that touches player / team / conversation / market /
honor / advanced-stat data, emits a markdown report:
- row_count
- min/max of the primary date-ish column (if any)
- season-year distribution
- source_name / source_id distribution (where applicable)

Designed to finish in <20s; uses indexed aggregate queries only.

Usage:
    python scripts/data_inventory.py --db cfb_rankings.db --output docs/audits/data_inventory_YYYY-MM-DD.md
"""

from __future__ import annotations

import argparse
import sqlite3
import time
from collections import defaultdict
from datetime import date
from pathlib import Path


TABLES_OF_INTEREST = [
    # Player scope
    ("players",                         None,                  None),
    ("player_aliases",                  None,                  None),
    ("player_game_stats",               "season_year",         None),
    ("player_honors",                   "season_year",         "source_name"),
    ("player_recruiting_profiles",      "season_year",         None),
    ("player_season_stats",             "season_year",         None),
    ("player_signal_events",            "occurred_at",         "source_name"),
    ("player_source_ids",               None,                  "source_name"),
    ("player_usage_season",             "season_year",         None),
    ("player_value_metrics",            "season_year",         None),
    ("player_week_conversation_features", "season_year",       "source_name"),
    ("roster_entries",                  "season_year",         None),
    ("roster_source_snapshots",         "season_year",         "source_name"),
    ("transfer_entries",                "season_year",         None),
    ("portal_moves",                    "season_year",         None),

    # Team scope
    ("teams",                           None,                  None),
    ("team_aliases",                    None,                  None),
    ("team_brand",                      None,                  None),
    ("team_brand_assets",               None,                  "source_name"),
    ("team_cohort_divergence_week",     None,                  None),       # uses YYYY-WW
    ("team_cohort_week",                None,                  None),       # uses YYYY-WW
    ("team_conversation_daily",         "observed_date",       "source_name"),
    ("team_game_advanced_stats",        "season_year",         None),
    ("team_game_conversation_features", "season_year",         "source_name"),
    ("team_rating_deltas",              "season_year",         None),
    ("team_seasons",                    "season_year",         None),
    ("team_talent_snapshots",           "season_year",         None),
    ("team_week_conversation_features", "season_year",         "source_name"),
    ("team_week_rival_mentions",        "season_year",         None),

    # Conversation scope
    ("conversation_collection_runs",    "started_at",          "source_name"),
    ("conversation_document_targets",   "season_year",         None),
    ("conversation_documents",          "published_at_utc",    "source_name"),
    ("conversation_raw_retention_audit", "checked_at",         "source_name"),
    ("conversation_storylines",         "season_year",         None),

    # Markets / predictions
    ("game_line_snapshots",             "snapshot_captured_at", None),
    ("game_lines",                      "season_year",         None),
    ("game_predictions",                "season_year",         None),
    ("heisman_market_odds_weekly",      None,                  None),       # uses week_start
    ("prediction_market_snapshots",     "captured_at",         "source"),

    # Honors / awards
    ("heisman_rankings_weekly",         None,                  None),
    ("heisman_vote_results",            "season_year",         None),

    # Advanced stats
    ("preseason_prior_components",      "season_year",         None),
    ("opponent_adjusted_team_week",     "season_year",         None),
    ("power_ratings_weekly",            "season_year",         None),
    ("resume_ratings_weekly",           "season_year",         None),
    ("strength_of_record_benchmarks",   "season_year",         None),
    ("level_strength_weekly",           "season_year",         None),
    ("conference_strength_weekly",      "season_year",         None),
    ("returning_production",            "season_year",         None),

    # Source registry / observations
    ("source_observations",             "observed_at_utc",     "source_id"),
    ("source_registry",                 None,                  None),
    ("scrape_health",                   "run_date",            "source_id"),

    # Hub v5 / FI
    ("fanbase_classification",          "season_year",         None),
    ("fanbase_classification_history",  "season_year",         None),
    ("fanbase_mood_weekly",             None,                  None),
    ("hub_issue_metadata",              None,                  None),
    ("hub_provenance_audit",            None,                  None),
    ("lexicon_weekly",                  None,                  None),
    ("phrase_mentions_weekly",          None,                  None),
    ("rivalry_obsession_weekly",        None,                  None),
    ("spring_events",                   "season_year",         None),

    # Games / drives / plays
    ("games",                           "season_year",         None),
    ("drives",                          "season_year",         None),
    ("plays",                           "season_year",         None),
    ("game_source_ids",                 None,                  "source_name"),
    ("game_weather",                    "season_year",         None),

    # Coaching
    ("coaching_changes",                "announced_date",      None),
]

SEASONS_OF_INTEREST = [2022, 2023, 2024, 2025, 2026]


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "select 1 from sqlite_master where type='table' and name=?",
        (name,),
    )
    return cur.fetchone() is not None


def _columns(conn: sqlite3.Connection, name: str) -> set[str]:
    cur = conn.execute(f"pragma table_info({name})")
    return {row[1] for row in cur.fetchall()}


def _row_count(conn: sqlite3.Connection, name: str) -> int:
    cur = conn.execute(f"select count(*) from {name}")
    return cur.fetchone()[0]


def _range(conn: sqlite3.Connection, name: str, column: str) -> tuple[str | None, str | None]:
    cur = conn.execute(f"select min({column}), max({column}) from {name}")
    row = cur.fetchone()
    return row[0], row[1]


def _season_distribution(conn: sqlite3.Connection, name: str, season_column: str) -> dict[int, int]:
    out: dict[int, int] = {}
    cur = conn.execute(
        f"select {season_column}, count(*) from {name} group by {season_column}"
    )
    for season, count in cur.fetchall():
        try:
            out[int(season) if season is not None else 0] = count
        except (TypeError, ValueError):
            out[season] = count  # type: ignore[index]
    return out


def _source_distribution(conn: sqlite3.Connection, name: str, source_column: str) -> list[tuple[str, int]]:
    cur = conn.execute(
        f"select {source_column}, count(*) from {name} "
        f"group by {source_column} order by 2 desc limit 15"
    )
    return [(str(row[0]) if row[0] is not None else "NULL", row[1]) for row in cur.fetchall()]


def _format_seasons(dist: dict[int, int]) -> str:
    if not dist:
        return "—"
    parts: list[str] = []
    for s in SEASONS_OF_INTEREST:
        parts.append(f"{s}:{dist.get(s, 0):,}")
    other = {k: v for k, v in dist.items() if k not in SEASONS_OF_INTEREST}
    if other:
        other_total = sum(other.values())
        parts.append(f"other:{other_total:,}")
    return " · ".join(parts)


def _format_sources(items: list[tuple[str, int]]) -> str:
    if not items:
        return "—"
    return ", ".join(f"{n}={c:,}" for n, c in items)


def _gap_summary(inventory: list[dict]) -> list[str]:
    lines: list[str] = []
    for entry in inventory:
        if not entry["season_dist"]:
            continue
        coverage = entry["season_dist"]
        missing = [s for s in SEASONS_OF_INTEREST if coverage.get(s, 0) == 0]
        if missing:
            lines.append(
                f"- `{entry['table']}`: no rows for {', '.join(str(s) for s in missing)}"
            )
    return lines


def build_inventory(db_path: str) -> list[dict]:
    inventory: list[dict] = []
    conn = sqlite3.connect(db_path)
    try:
        for table, date_col, source_col in TABLES_OF_INTEREST:
            if not _table_exists(conn, table):
                inventory.append({"table": table, "missing": True})
                continue
            cols = _columns(conn, table)
            count = _row_count(conn, table)
            entry = {
                "table": table,
                "count": count,
                "date_column": date_col,
                "date_min": None,
                "date_max": None,
                "season_dist": {},
                "source_dist": [],
            }
            if date_col and date_col in cols and count > 0:
                entry["date_min"], entry["date_max"] = _range(conn, table, date_col)
            if "season_year" in cols and count > 0:
                entry["season_dist"] = _season_distribution(conn, table, "season_year")
            if source_col and source_col in cols and count > 0:
                entry["source_dist"] = _source_distribution(conn, table, source_col)
            inventory.append(entry)
    finally:
        conn.close()
    return inventory


def render_report(inventory: list[dict], db_path: str, elapsed: float) -> str:
    today = date.today().isoformat()
    lines: list[str] = []
    lines.append(f"# Data Inventory — {today}\n")
    lines.append(f"**DB:** `{db_path}` · **Generated in:** {elapsed:.2f}s\n")
    lines.append(
        "This is the baseline snapshot taken at the start of the Autopilot v1 build. "
        "Every subsequent workstream should change these numbers. The \"gap summary\" "
        "at the bottom is the target list for the backfill work in W1 / W2 / W3 / W4.\n"
    )

    lines.append("## Per-table inventory\n")
    lines.append(
        "| Table | Rows | Date column | Min | Max | Season coverage | Top sources |"
    )
    lines.append("|---|---:|---|---|---|---|---|")
    for entry in inventory:
        if entry.get("missing"):
            lines.append(f"| `{entry['table']}` | MISSING | — | — | — | — | — |")
            continue
        date_col = entry.get("date_column") or "—"
        date_min = entry.get("date_min") or "—"
        date_max = entry.get("date_max") or "—"
        seasons = _format_seasons(entry.get("season_dist") or {})
        sources = _format_sources(entry.get("source_dist") or [])
        lines.append(
            f"| `{entry['table']}` | {entry['count']:,} | {date_col} | {date_min} | {date_max} | {seasons} | {sources} |"
        )

    lines.append("\n## Gap summary — seasons missing per table\n")
    gaps = _gap_summary(inventory)
    if gaps:
        lines.extend(gaps)
    else:
        lines.append("_No season gaps detected in tables that carry a `season_year` column._")

    lines.append("\n## Autopilot backfill targets (derived from gaps)\n")
    lines.append(
        "- **W1 (CFBD deep backfill)** must fill: `player_game_stats`, "
        "`player_season_stats`, `player_value_metrics`, `player_usage_season`, "
        "`games`, `drives`, `plays`, `game_lines`, `game_predictions`, "
        "`opponent_adjusted_team_week`, `power_ratings_weekly`, "
        "`resume_ratings_weekly`, `returning_production`, "
        "`team_game_advanced_stats`, `team_talent_snapshots` for seasons "
        "missing rows above."
    )
    lines.append(
        "- **W2 (conversation corpus)** must fill `conversation_documents` "
        "and downstream `conversation_document_targets` + weekly features "
        "for 2022 / 2023 / 2024 / 2025 (offseason + in-season)."
    )
    lines.append(
        "- **W3 (Tier-A numeric)** must fill `source_observations` with "
        "historical pageviews / market prices / article volumes for 2022-2025 "
        "where the API allows."
    )
    lines.append(
        "- **W4 (honors / awards / draft / NIL)** must fill `player_honors` "
        "for every honor scope 2022-2025, plus new tables `player_nfl_draft`, "
        "`player_draft_projection`, `player_nil_snapshot`."
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="cfb_rankings.db")
    parser.add_argument("--output", required=True, help="Markdown report output path.")
    args = parser.parse_args()

    start = time.perf_counter()
    inventory = build_inventory(args.db)
    elapsed = time.perf_counter() - start
    report = render_report(inventory, args.db, elapsed)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"Wrote {out_path} ({len(inventory)} tables, {elapsed:.2f}s)")


if __name__ == "__main__":
    main()
