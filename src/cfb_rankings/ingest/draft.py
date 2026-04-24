"""NFL Draft results ingest — Autopilot v1 TASK 4.5.

Pulls CFBD's /draft/picks endpoint for a given year, resolves
player_id / team_id when possible, and upserts into
player_nfl_draft.

CLI: `python manage.py ingest-nfl-draft --year 2022` (one year) or
`--start-year 2022 --end-year 2025` (loop).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from cfb_rankings.clients.cfbd import CfbdClient
from cfb_rankings.db import Database

log = logging.getLogger(__name__)


def _resolve_player_id(db: Database, college_id: Any, player_name: str | None) -> int | None:
    """Resolve CFBD college_id → players.player_id, falling back to name.

    CFBD's draft endpoint returns the college_id that matches rows in
    `player_source_ids` with source_name='cfbd'.
    """
    if college_id is not None:
        row = db.query_one(
            "select player_id from player_source_ids "
            "where source_name = 'cfbd' and source_player_id = :sid",
            {"sid": str(college_id)},
        )
        if row and row.get("player_id"):
            return int(row["player_id"])
    if player_name:
        # Fallback: exact full_name match.
        row = db.query_one(
            "select player_id from players "
            "where lower(full_name) = lower(:n) limit 1",
            {"n": player_name.strip()},
        )
        if row and row.get("player_id"):
            return int(row["player_id"])
    return None


def _resolve_team_id(db: Database, team_name: str | None) -> int | None:
    if not team_name:
        return None
    # Try canonical_name, school_name, short_name, slug, then aliases.
    row = db.query_one(
        """
        select team_id from teams
        where lower(canonical_name) = lower(:n)
           or lower(school_name)    = lower(:n)
           or lower(short_name)     = lower(:n)
           or lower(slug)           = lower(:n)
        limit 1
        """,
        {"n": team_name},
    )
    if row:
        return int(row["team_id"])
    row = db.query_one(
        "select team_id from team_aliases "
        "where lower(alias_text) = lower(:n) or lower(alias_normalized) = lower(:n) "
        "limit 1",
        {"n": team_name},
    )
    if row:
        return int(row["team_id"])
    return None


def ingest_draft_year(db: Database, client: CfbdClient, year: int) -> dict[str, int]:
    """Fetch + upsert every draft pick for the given year.

    Returns {rows_fetched, rows_upserted, resolved_player_ids,
    resolved_team_ids}.
    """
    picks = client.get_nfl_draft_picks(year)
    fetched = len(picks)
    rows: list[dict[str, Any]] = []
    player_hits = 0
    team_hits = 0
    for p in picks:
        overall = p.get("overall") or p.get("pick")
        round_num = p.get("round")
        pick_in_round = p.get("pick") or overall
        if round_num is None or pick_in_round is None:
            continue
        player_name = p.get("name") or p.get("player") or p.get("playerName")
        college_id = p.get("collegeId") or p.get("college_id") or p.get("college_athlete_id")
        college_team = p.get("collegeTeam") or p.get("college_team")
        college_conf = p.get("collegeConference") or p.get("college_conference")
        nfl_team = p.get("nflTeam") or p.get("nfl_team") or ""
        nfl_abbr = p.get("nflTeamAbbreviation") or p.get("nfl_team_abbreviation") or None
        position = p.get("position") or p.get("collegePosition")
        player_id = _resolve_player_id(db, college_id, player_name)
        team_id = _resolve_team_id(db, college_team)
        if player_id is not None:
            player_hits += 1
        if team_id is not None:
            team_hits += 1
        rows.append(
            {
                "draft_year": int(year),
                "round": int(round_num),
                "pick": int(pick_in_round),
                "overall": int(overall) if overall is not None else None,
                "player_id": player_id,
                "player_name": player_name,
                "position": position,
                "height_inches": p.get("height") or p.get("heightInches"),
                "weight_lbs": p.get("weight") or p.get("weightLbs"),
                "college_team_id": team_id,
                "college_team_name": college_team,
                "college_conference": college_conf,
                "nfl_team": nfl_team,
                "nfl_team_abbr": nfl_abbr,
                "source_name": "cfbd",
                "source_player_id": str(college_id) if college_id is not None else None,
                "raw_payload_json": json.dumps(p),
            }
        )

    if rows:
        db.upsert_many(
            "player_nfl_draft",
            rows,
            conflict_columns=["draft_year", "round", "pick"],
        )

    log.info(
        "ingest-nfl-draft year=%d fetched=%d upserted=%d player_resolved=%d team_resolved=%d",
        year, fetched, len(rows), player_hits, team_hits,
    )
    return {
        "rows_fetched": fetched,
        "rows_upserted": len(rows),
        "resolved_player_ids": player_hits,
        "resolved_team_ids": team_hits,
    }


def ingest_draft_range(
    db: Database, client: CfbdClient, start_year: int, end_year: int
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for year in range(start_year, end_year + 1):
        s = ingest_draft_year(db, client, year)
        s["year"] = year
        summaries.append(s)
    return summaries
