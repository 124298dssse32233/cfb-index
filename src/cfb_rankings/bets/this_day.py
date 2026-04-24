"""Historical "this day" chip — Signature Bets S4.3 / §5 item 19.

Finds the player's most recent game whose calendar date matches
today's month + day. If none, returns None; renderer omits the chip.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Any

from cfb_rankings.db import Database


@dataclass(frozen=True)
class ThisDayMoment:
    game_id: int
    season: int
    week: int | None
    date_iso: str
    years_ago: int
    opponent_short: str | None
    result_label: str
    headline: str


def fetch_this_day_moment(
    db: Database, player_id: int, today: _dt.date | None = None
) -> ThisDayMoment | None:
    today = today or _dt.date.today()
    month = today.month
    day = today.day
    # Fetch any game for this player where month-day of game date
    # matches today. games.start_time_utc is ISO text.
    try:
        rows = db.query_all(
            "SELECT pgs.game_id, pgs.season_year, pgs.week, pgs.team_id, "
            "       g.start_time_utc, g.home_team_id, g.away_team_id, "
            "       g.home_points, g.away_points, "
            "       ht.short_name AS home_short, at.short_name AS away_short "
            "FROM player_game_stats pgs "
            "LEFT JOIN games g ON g.game_id = pgs.game_id "
            "LEFT JOIN teams ht ON ht.team_id = g.home_team_id "
            "LEFT JOIN teams at ON at.team_id = g.away_team_id "
            "WHERE pgs.player_id = :pid "
            "  AND g.start_time_utc IS NOT NULL "
            "  AND strftime('%m', g.start_time_utc) = :m "
            "  AND strftime('%d', g.start_time_utc) = :d",
            {"pid": player_id, "m": f"{month:02d}", "d": f"{day:02d}"},
        )
    except Exception:
        return None
    if not rows:
        return None
    # Deduplicate by game_id; pick the most recent season (not today).
    seen: dict[int, dict[str, Any]] = {}
    for r in rows:
        gid = int(r["game_id"])
        if gid not in seen:
            seen[gid] = r
    best = sorted(
        seen.values(),
        key=lambda r: int(r.get("season_year") or 0),
        reverse=True,
    )
    # Skip same-year game; a "this day" chip wants a historical anchor.
    today_year = today.year
    best_row = next((r for r in best if int(r.get("season_year") or 0) != today_year), None)
    if not best_row:
        return None

    is_home = best_row.get("team_id") == best_row.get("home_team_id")
    opp_short = (
        best_row.get("away_short") if is_home else best_row.get("home_short")
    )
    hp = best_row.get("home_points")
    ap = best_row.get("away_points")
    if hp is None or ap is None:
        result_label = "—"
    else:
        own = hp if is_home else ap
        opp = ap if is_home else hp
        sym = "W" if own > opp else "L" if own < opp else "T"
        result_label = f"{sym} {int(own)}-{int(opp)}"

    season = int(best_row.get("season_year") or 0)
    years_ago = max(0, today.year - season)
    dt_iso = str(best_row.get("start_time_utc") or "")[:10]
    year_phrase = (
        "One year ago today" if years_ago == 1
        else f"{years_ago} years ago today"
    )
    headline = (
        f"{year_phrase}: Week {int(best_row.get('week') or 0)} "
        f"{'at ' if not is_home else 'vs '}{opp_short or 'opponent'} "
        f"({result_label})."
    )
    return ThisDayMoment(
        game_id=int(best_row["game_id"]),
        season=season,
        week=(int(best_row["week"]) if best_row.get("week") is not None else None),
        date_iso=dt_iso,
        years_ago=years_ago,
        opponent_short=opp_short,
        result_label=result_label,
        headline=headline,
    )
