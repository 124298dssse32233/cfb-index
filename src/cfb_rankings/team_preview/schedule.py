"""Schedule truth for the preview layer.

Spec: docs/specs/team-preview-implementation-plan-2026-05-26.md §2.1, §3.6, §10.

The cardinal rule: never render a generic kickoff date as if it were official.
If no future-season schedule is loaded, say so plainly. This module returns a
small, explicit status object the renderer (a later milestone) can trust.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScheduleStatus:
    season_year: int
    schedule_known: bool
    games_loaded: int
    first_game_id: int | None = None
    first_game_start_utc: str | None = None
    first_game_opponent_id: int | None = None
    first_game_opponent_name: str | None = None
    note: str = ""

    @property
    def display_state(self) -> str:
        """Stable token a renderer can switch on."""
        return "known" if self.schedule_known else "not_loaded"


def resolve_schedule_status(db: Any, team_id: int, season_year: int) -> ScheduleStatus:
    count = db.query_one(
        "select count(*) c from games where season_year = :s "
        "and (home_team_id = :t or away_team_id = :t)",
        {"s": season_year, "t": team_id},
    )
    games_loaded = int((count or {}).get("c") or 0)

    first = db.query_one(
        """
        select g.game_id, g.start_time_utc, g.home_team_id, g.away_team_id,
               ht.canonical_name home_name, at.canonical_name away_name
        from games g
        join teams ht on ht.team_id = g.home_team_id
        join teams at on at.team_id = g.away_team_id
        where g.season_year = :s and (g.home_team_id = :t or g.away_team_id = :t)
          and g.start_time_utc is not null
        order by g.start_time_utc asc
        limit 1
        """,
        {"s": season_year, "t": team_id},
    )
    if not first:
        return ScheduleStatus(
            season_year=season_year,
            schedule_known=False,
            games_loaded=games_loaded,
            note=f"{season_year} schedule not loaded",
        )

    if int(first["home_team_id"]) == team_id:
        opp_id, opp_name = int(first["away_team_id"]), first["away_name"]
    else:
        opp_id, opp_name = int(first["home_team_id"]), first["home_name"]

    return ScheduleStatus(
        season_year=season_year,
        schedule_known=True,
        games_loaded=games_loaded,
        first_game_id=int(first["game_id"]),
        first_game_start_utc=first["start_time_utc"],
        first_game_opponent_id=opp_id,
        first_game_opponent_name=opp_name,
        note="",
    )
