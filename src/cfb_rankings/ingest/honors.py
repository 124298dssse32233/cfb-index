from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.ingest.common import maybe_int
from cfb_rankings.storage import Repository


def import_player_honors_csv(
    repository: Repository,
    db: Database,
    csv_path: str | Path,
    default_source_name: str = "manual",
) -> int:
    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    honor_rows = [_normalize_honor_row(repository, db, row, default_source_name) for row in rows]
    honor_rows = [row for row in honor_rows if row is not None]
    db.upsert_many(
        "player_honors",
        honor_rows,
        conflict_columns=[
            "player_id",
            "season_year",
            "week",
            "honor_scope",
            "honor_name",
            "selector",
            "honor_team",
            "position",
            "source_name",
        ],
        update_columns=[
            "team_id",
            "conference_name",
            "placement",
            "consensus_flag",
            "unanimous_flag",
            "source_url",
            "notes",
        ],
    )
    heisman_rows = [_honor_to_heisman_vote_result(row) for row in honor_rows]
    heisman_rows = [row for row in heisman_rows if row is not None]
    db.upsert_many(
        "heisman_vote_results",
        heisman_rows,
        conflict_columns=["season_year", "player_id", "source_name"],
        update_columns=[
            "team_id",
            "place",
            "winner_flag",
            "finalist_flag",
            "notes",
        ],
    )
    return len(honor_rows)


def _normalize_honor_row(
    repository: Repository,
    db: Database,
    row: dict[str, Any],
    default_source_name: str,
) -> dict[str, Any] | None:
    season_year = maybe_int(row.get("season_year") or row.get("season") or row.get("year"))
    if season_year is None:
        return None
    repository.ensure_season(season_year)
    player_id = _resolve_player_id(db, row)
    if player_id is None:
        player_id = _ensure_stub_player_id(db, row)
    if player_id is None:
        return None
    week_value = maybe_int(row.get("week"))
    team_id = _resolve_team_id(repository, row)
    return {
        "player_id": player_id,
        "season_year": season_year,
        "week": week_value or 0,
        "team_id": team_id,
        "conference_name": _clean_text(row.get("conference_name") or row.get("conference")),
        "honor_scope": _clean_text(row.get("honor_scope")) or "honor",
        "honor_name": _clean_text(row.get("honor_name")) or _clean_text(row.get("award")) or "Honor",
        "selector": _clean_text(row.get("selector")) or "",
        "honor_team": _clean_text(row.get("honor_team") or row.get("team_designation")) or "",
        "position": _clean_text(row.get("position")) or "",
        "placement": maybe_int(row.get("placement") or row.get("place")),
        "consensus_flag": 1 if _truthy(row.get("consensus_flag") or row.get("consensus")) else 0,
        "unanimous_flag": 1 if _truthy(row.get("unanimous_flag") or row.get("unanimous")) else 0,
        "source_name": _clean_text(row.get("source_name")) or default_source_name,
        "source_url": _clean_text(row.get("source_url")),
        "notes": _clean_text(row.get("notes")),
    }


def _resolve_player_id(db: Database, row: dict[str, Any]) -> int | None:
    direct_id = maybe_int(row.get("player_id"))
    if direct_id is not None:
        return direct_id
    for source_name, source_column in (("cfbd", "cfbd_player_id"), ("cfbd-recruit", "cfbd_recruit_id")):
        source_value = _clean_text(row.get(source_column))
        if not source_value:
            continue
        matched = db.query_one(
            """
            select player_id
            from player_source_ids
            where source_name = %(source_name)s
              and source_player_id = %(source_player_id)s
            """,
            {"source_name": source_name, "source_player_id": source_value},
        )
        if matched is not None:
            return int(matched["player_id"])
    full_name = _clean_text(row.get("full_name") or row.get("player_name") or row.get("name"))
    if not full_name:
        return None
    matched = db.query_one(
        """
        select player_id
        from players
        where lower(full_name) = lower(%(full_name)s)
        order by player_id asc
        limit 1
        """,
        {"full_name": full_name},
    )
    return None if matched is None else int(matched["player_id"])


def _resolve_team_id(repository: Repository, row: dict[str, Any]) -> int | None:
    direct_id = maybe_int(row.get("team_id"))
    if direct_id is not None:
        return direct_id
    team_name = _clean_text(row.get("team_name") or row.get("team"))
    if not team_name:
        return None
    return repository.match_team_by_name(team_name)


def _ensure_stub_player_id(db: Database, row: dict[str, Any]) -> int | None:
    full_name = _clean_text(row.get("full_name") or row.get("player_name") or row.get("name"))
    if not full_name:
        return None

    matched = db.query_one(
        """
        select player_id
        from players
        where lower(full_name) = lower(%(full_name)s)
        order by player_id asc
        limit 1
        """,
        {"full_name": full_name},
    )
    if matched is not None:
        return int(matched["player_id"])

    first_name, last_name = _split_name(full_name)
    position = _clean_text(row.get("position"))
    db.execute(
        """
        insert into players (
          full_name,
          first_name,
          last_name,
          position
        ) values (
          %(full_name)s,
          %(first_name)s,
          %(last_name)s,
          %(position)s
        )
        """,
        {
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "position": position,
        },
    )
    created = db.query_one(
        """
        select player_id
        from players
        where lower(full_name) = lower(%(full_name)s)
        order by player_id desc
        limit 1
        """,
        {"full_name": full_name},
    )
    if created is None:
        return None

    player_id = int(created["player_id"])
    for source_name, source_column in (("cfbd", "cfbd_player_id"), ("cfbd-recruit", "cfbd_recruit_id")):
        source_value = _clean_text(row.get(source_column))
        if not source_value:
            continue
        db.upsert_many(
            "player_source_ids",
            [
                {
                    "player_id": player_id,
                    "source_name": source_name,
                    "source_player_id": source_value,
                }
            ],
            conflict_columns=["source_name", "source_player_id"],
            update_columns=["player_id"],
        )
    return player_id


def _clean_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _truthy(value: Any) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized in {"1", "true", "yes", "y"}


def _split_name(full_name: str) -> tuple[str | None, str | None]:
    parts = [part for part in full_name.strip().split() if part]
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[-1]


def _honor_to_heisman_vote_result(row: dict[str, Any]) -> dict[str, Any] | None:
    honor_name = str(row.get("honor_name") or "").strip().lower()
    selector = str(row.get("selector") or "").strip().lower()
    if "heisman" not in honor_name or "heisman" not in selector:
        return None
    winner_flag = 1 if "winner" in honor_name or str(row.get("honor_team") or "").strip().lower() == "winner" else 0
    finalist_flag = 1 if winner_flag or "finalist" in honor_name or str(row.get("honor_team") or "").strip().lower() == "finalist" else 0
    return {
        "season_year": int(row["season_year"]),
        "player_id": int(row["player_id"]),
        "team_id": row.get("team_id"),
        "source_name": str(row.get("source_name") or "official-heisman"),
        "place": row.get("placement"),
        "winner_flag": winner_flag,
        "finalist_flag": finalist_flag,
        "first_place_votes": None,
        "second_place_votes": None,
        "third_place_votes": None,
        "total_points": None,
        "ballot_count": None,
        "notes": str(row.get("notes") or ""),
    }
