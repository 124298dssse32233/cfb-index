"""CFBD play-by-play ingest — Wave 10.

Pulls /plays endpoint for a (season, week, team) bucket and upserts
into cfbd_pbp_plays. The week+team granularity is the natural rate
limit unit — one HTTP call per (season, week, team) — and CFBD
responses fit comfortably in memory.

Strategy: iterate weeks 1..16 (regular) + 1..3 (postseason). For each
week, fetch all FBS plays once (no team filter — single big payload).
~3-5k plays per week × ~16 weeks = ~60-80k rows for a season.

Public:
    ingest_cfbd_pbp_week(db, client, year, week, season_type) -> dict
    parse_play_text(play) -> list[dict]   # actor rows
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from cfb_rankings.clients.cfbd import CfbdClient
from cfb_rankings.db import Database


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _flatten_clock(clock: Any) -> tuple[int | None, int | None]:
    if not isinstance(clock, dict):
        return (None, None)
    return (_safe_int(clock.get("minutes")), _safe_int(clock.get("seconds")))


# play_text parser patterns. CFBD play text follows a relatively
# stable convention. Patterns are intentionally permissive to handle
# variants like "Player Name Jr." or hyphenated names.
_NAME = r"([A-Z][A-Za-z'\-\.]+(?:\s[A-Z][A-Za-z'\-\.]+){0,3})"
_YDS  = r"(-?\d+)\s*yds?"

_RE_PASS_COMPLETE = re.compile(
    rf"{_NAME} pass complete to {_NAME} for {_YDS}",
)
_RE_PASS_INCOMPLETE = re.compile(
    rf"{_NAME} pass incomplete(?: to {_NAME})?",
)
_RE_PASS_INT = re.compile(
    rf"{_NAME} pass intercepted(?: by {_NAME})?",
)
_RE_RUSH = re.compile(
    rf"{_NAME} (?:run|rush) for {_YDS}",
)
_RE_SACK = re.compile(
    rf"{_NAME} sacked(?: by {_NAME})?(?: for {_YDS})?",
)
_RE_TD_KEYWORD = re.compile(r"\bfor a TD\b|\btouchdown\b", re.IGNORECASE)


def parse_play_text(play: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a list of actor rows for one play, derived from playText.

    Each actor row: {actor_name_raw, role, yards, is_complete,
                     is_touchdown, is_interception, is_sack,
                     air_yards, yac}
    """
    text = (play.get("playText") or "").strip()
    if not text:
        return []
    play_type = (play.get("playType") or "").lower()
    yards_gained = _safe_int(play.get("yardsGained"))
    is_td = 1 if (bool(play.get("scoring")) and (yards_gained or 0) >= 0 and
                  ("touchdown" in play_type or "TD" in (text or ""))) else 0

    actors: list[dict[str, Any]] = []

    # Pass complete
    m = _RE_PASS_COMPLETE.search(text)
    if m:
        passer, receiver, yds = m.group(1), m.group(2), _safe_int(m.group(3))
        td = 1 if _RE_TD_KEYWORD.search(text) else 0
        actors.append({
            "actor_name_raw": passer, "role": "passer",
            "yards": yds, "is_complete": 1, "is_touchdown": td,
            "is_interception": 0, "is_sack": 0,
            "air_yards": None, "yac": None,
        })
        actors.append({
            "actor_name_raw": receiver, "role": "receiver",
            "yards": yds, "is_complete": 1, "is_touchdown": td,
            "is_interception": 0, "is_sack": 0,
            "air_yards": None, "yac": None,
        })
        return actors

    # Pass incomplete
    m = _RE_PASS_INCOMPLETE.search(text)
    if m:
        passer = m.group(1)
        target = m.group(2) if m.lastindex and m.lastindex >= 2 else None
        actors.append({
            "actor_name_raw": passer, "role": "passer",
            "yards": 0, "is_complete": 0, "is_touchdown": 0,
            "is_interception": 0, "is_sack": 0,
            "air_yards": None, "yac": None,
        })
        if target:
            actors.append({
                "actor_name_raw": target, "role": "target",
                "yards": 0, "is_complete": 0, "is_touchdown": 0,
                "is_interception": 0, "is_sack": 0,
                "air_yards": None, "yac": None,
            })
        return actors

    # Interception
    m = _RE_PASS_INT.search(text)
    if m:
        passer = m.group(1)
        interceptor = m.group(2) if m.lastindex and m.lastindex >= 2 else None
        actors.append({
            "actor_name_raw": passer, "role": "passer",
            "yards": 0, "is_complete": 0, "is_touchdown": 0,
            "is_interception": 1, "is_sack": 0,
            "air_yards": None, "yac": None,
        })
        if interceptor:
            actors.append({
                "actor_name_raw": interceptor, "role": "interceptor",
                "yards": 0, "is_complete": 0, "is_touchdown": 0,
                "is_interception": 1, "is_sack": 0,
                "air_yards": None, "yac": None,
            })
        return actors

    # Sack
    m = _RE_SACK.search(text)
    if m:
        qb = m.group(1)
        sacker = m.group(2) if m.lastindex and m.lastindex >= 2 else None
        sack_yds = _safe_int(m.group(3)) if m.lastindex and m.lastindex >= 3 else None
        actors.append({
            "actor_name_raw": qb, "role": "passer",
            "yards": sack_yds or 0, "is_complete": 0, "is_touchdown": 0,
            "is_interception": 0, "is_sack": 1,
            "air_yards": None, "yac": None,
        })
        if sacker:
            actors.append({
                "actor_name_raw": sacker, "role": "sacker",
                "yards": sack_yds or 0, "is_complete": 0, "is_touchdown": 0,
                "is_interception": 0, "is_sack": 1,
                "air_yards": None, "yac": None,
            })
        return actors

    # Rush
    m = _RE_RUSH.search(text)
    if m:
        rusher, yds = m.group(1), _safe_int(m.group(2))
        td = 1 if _RE_TD_KEYWORD.search(text) else 0
        actors.append({
            "actor_name_raw": rusher, "role": "rusher",
            "yards": yds, "is_complete": 0, "is_touchdown": td,
            "is_interception": 0, "is_sack": 0,
            "air_yards": None, "yac": None,
        })
        return actors

    return actors


def _upsert_play(db: Database, play: dict[str, Any], season_year: int,
                  week: int, season_type: str) -> None:
    clock_min, clock_sec = _flatten_clock(play.get("clock"))
    row = {
        "play_id":            str(play.get("id") or ""),
        "game_id":            _safe_int(play.get("gameId")) or 0,
        "drive_id":           str(play.get("driveId") or ""),
        "season_year":        season_year,
        "week":               week,
        "season_type":        season_type,
        "play_number":        _safe_int(play.get("playNumber")),
        "drive_number":       _safe_int(play.get("driveNumber")),
        "offense":            play.get("offense"),
        "defense":            play.get("defense"),
        "offense_conference": play.get("offenseConference"),
        "defense_conference": play.get("defenseConference"),
        "offense_score":      _safe_int(play.get("offenseScore")),
        "defense_score":      _safe_int(play.get("defenseScore")),
        "home_team":          play.get("home"),
        "away_team":          play.get("away"),
        "period":             _safe_int(play.get("period")),
        "clock_minutes":      clock_min,
        "clock_seconds":      clock_sec,
        "yardline":           _safe_int(play.get("yardline")),
        "yards_to_goal":      _safe_int(play.get("yardsToGoal")),
        "down":               _safe_int(play.get("down")),
        "distance":           _safe_int(play.get("distance")),
        "yards_gained":       _safe_int(play.get("yardsGained")),
        "scoring":            1 if play.get("scoring") else 0,
        "play_type":          play.get("playType"),
        "play_text":          play.get("playText"),
        "ppa":                _safe_float(play.get("ppa")),
        "wallclock":          play.get("wallclock"),
        "ingested_at":        _now_iso(),
    }
    if not row["play_id"] or row["game_id"] == 0:
        return
    cols = ", ".join(row.keys())
    placeholders = ", ".join(f":{k}" for k in row.keys())
    db.execute(
        f"insert or replace into cfbd_pbp_plays ({cols}) values ({placeholders})",
        row,
    )


def _upsert_actors(db: Database, play_id: str, actors: list[dict[str, Any]]) -> None:
    if not actors:
        return
    # Drop any existing rows for this play (idempotent re-ingest)
    db.execute(
        "delete from cfbd_pbp_play_actors where play_id = :pid",
        {"pid": play_id},
    )
    now = _now_iso()
    for a in actors:
        a_row = {
            "play_id": play_id,
            "actor_player_id": None,
            "actor_name_raw": a["actor_name_raw"],
            "role": a["role"],
            "yards": a.get("yards"),
            "is_complete": a.get("is_complete", 0),
            "is_touchdown": a.get("is_touchdown", 0),
            "is_interception": a.get("is_interception", 0),
            "is_sack": a.get("is_sack", 0),
            "air_yards": a.get("air_yards"),
            "yac": a.get("yac"),
            "ingested_at": now,
        }
        db.execute(
            """
            insert into cfbd_pbp_play_actors
                (play_id, actor_player_id, actor_name_raw, role, yards,
                 is_complete, is_touchdown, is_interception, is_sack,
                 air_yards, yac, ingested_at)
            values
                (:play_id, :actor_player_id, :actor_name_raw, :role, :yards,
                 :is_complete, :is_touchdown, :is_interception, :is_sack,
                 :air_yards, :yac, :ingested_at)
            """,
            a_row,
        )


def ingest_cfbd_pbp_week(
    db: Database, client: CfbdClient,
    year: int, week: int, season_type: str = "regular",
    classification: str | None = "fbs",
    parse_actors: bool = True,
) -> dict[str, int]:
    """Ingest all plays for a (year, week) bucket. Returns row counts."""
    plays = client.get_plays(
        year=year, week=week, season_type=season_type,
        classification=classification,
    )
    n_plays = 0
    n_actors = 0
    for play in plays:
        _upsert_play(db, play, year, week, season_type)
        n_plays += 1
        if parse_actors:
            actors = parse_play_text(play)
            if actors:
                _upsert_actors(db, str(play.get("id") or ""), actors)
                n_actors += len(actors)
    return {"plays": n_plays, "actors": n_actors}
