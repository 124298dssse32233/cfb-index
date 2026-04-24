"""Rivalry Card — head-to-head loader from the ``games`` table.

Pulls every final between two programs from ``games``, normalises to a
lex-ordered (program_a, program_b) key, denormalises winner/margin/venue
for hot-path filtering, and writes to ``team_rivalry_meetings``.

No CFBD API call. The ``games`` table already has 23k rows with scores,
venues, and dates — richer than what a one-shot CFBD ``/teams/matchup``
call would return.

Entry point: ``refresh_rivalry_meetings(conn, program_a_slug, program_b_slug)``.
"""
from __future__ import annotations

import sqlite3
from typing import Any


def _canonical_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def refresh_rivalry_meetings(
    conn: sqlite3.Connection,
    program_a_slug: str,
    program_b_slug: str,
    *,
    since_year: int | None = None,
) -> int:
    """Populate team_rivalry_meetings for one program pair. Returns rows written."""
    a_slug, b_slug = _canonical_pair(program_a_slug, program_b_slug)

    where_year = "and g.season_year >= :since" if since_year else ""
    params: dict[str, Any] = {"a": a_slug, "b": b_slug}
    if since_year:
        params["since"] = since_year

    rows = conn.execute(
        f"""
        select g.game_id, g.season_year, g.week, g.status,
               g.home_points, g.away_points,
               coalesce(v.venue_name, '') as venue,
               g.neutral_site,
               substr(g.start_time_utc, 1, 10) as game_date,
               ta.slug as home_slug, tb.slug as away_slug
        from games g
        join teams ta on ta.team_id = g.home_team_id
        join teams tb on tb.team_id = g.away_team_id
        left join venues v on v.venue_id = g.venue_id
        where ((ta.slug = :a and tb.slug = :b) or (ta.slug = :b and tb.slug = :a))
        {where_year}
        order by g.season_year, coalesce(g.week, 0), g.start_time_utc
        """,
        params,
    ).fetchall()

    written = 0
    for r in rows:
        game_id, season_year, week, status, home_pts, away_pts, venue, neutral_site, game_date, home_slug, away_slug = r
        status = (status or "").lower()
        is_complete = 1 if status in ("final", "completed") else 0

        if home_slug == a_slug:
            a_pts, b_pts = home_pts, away_pts
        else:
            a_pts, b_pts = away_pts, home_pts

        winner_slug = None
        margin = None
        if is_complete and a_pts is not None and b_pts is not None:
            margin = int(a_pts) - int(b_pts)
            if margin > 0:
                winner_slug = a_slug
            elif margin < 0:
                winner_slug = b_slug
            else:
                winner_slug = "tie"

        conn.execute(
            """
            insert into team_rivalry_meetings (
              program_a_slug, program_b_slug, game_id, season_year, week, game_date,
              home_slug, a_points, b_points, winner_slug, margin, venue,
              commentary_text, commentary_model_id, is_complete, generated_at_utc
            ) values (
              :a, :b, :gid, :s, :w, :gd,
              :home, :apts, :bpts, :win, :margin, :venue,
              NULL, NULL, :done, current_timestamp
            )
            on conflict(program_a_slug, program_b_slug, game_id) do update set
              season_year = excluded.season_year,
              week = excluded.week,
              game_date = excluded.game_date,
              home_slug = excluded.home_slug,
              a_points = excluded.a_points,
              b_points = excluded.b_points,
              winner_slug = excluded.winner_slug,
              margin = excluded.margin,
              venue = excluded.venue,
              is_complete = excluded.is_complete,
              generated_at_utc = current_timestamp
            """,
            {
                "a": a_slug, "b": b_slug, "gid": int(game_id),
                "s": int(season_year), "w": int(week) if week is not None else None,
                "gd": game_date, "home": home_slug,
                "apts": int(a_pts) if a_pts is not None else None,
                "bpts": int(b_pts) if b_pts is not None else None,
                "win": winner_slug, "margin": margin,
                "venue": venue, "done": is_complete,
            },
        )
        written += 1
    return written


# --------------------------------------------------------------------------
# Read-side helpers (used by the renderer via team_pages.data)
# --------------------------------------------------------------------------

def fetch_meetings(
    db,
    program_a_slug: str,
    program_b_slug: str,
    *,
    limit: int | None = None,
    completed_only: bool = True,
) -> list[dict[str, Any]]:
    """Return meetings for a pair, most-recent first."""
    a_slug, b_slug = _canonical_pair(program_a_slug, program_b_slug)
    where_done = "and is_complete = 1" if completed_only else ""
    lim = f"limit {int(limit)}" if limit else ""
    rows = db.query_all(
        f"""
        select program_a_slug, program_b_slug, game_id, season_year, week, game_date,
               home_slug, a_points, b_points, winner_slug, margin, venue,
               commentary_text, is_complete
        from team_rivalry_meetings
        where program_a_slug = :a and program_b_slug = :b
        {where_done}
        order by season_year desc, coalesce(week, 0) desc, coalesce(game_date, '') desc
        {lim}
        """,
        {"a": a_slug, "b": b_slug},
    )
    return rows


def compute_all_time_record(
    db,
    program_slug: str,
    opponent_slug: str,
) -> dict[str, Any]:
    """All-time W-L-T + current streak for program_slug vs opponent_slug.

    Streak is from program_slug's perspective — positive integer if program
    is currently winning the last N, negative if losing.
    """
    a_slug, b_slug = _canonical_pair(program_slug, opponent_slug)
    rows = db.query_all(
        """
        select season_year, week, game_date, winner_slug, margin,
               a_points, b_points
        from team_rivalry_meetings
        where program_a_slug = :a and program_b_slug = :b
          and is_complete = 1
        order by season_year asc, coalesce(week, 0) asc
        """,
        {"a": a_slug, "b": b_slug},
    )
    w = l = t = 0
    for r in rows:
        win = r["winner_slug"]
        if win == "tie":
            t += 1
        elif win == program_slug:
            w += 1
        elif win is not None:
            l += 1
    # Streak from program's perspective, walking from latest backward.
    streak = 0
    streak_sign = 0
    for r in reversed(rows):
        win = r["winner_slug"]
        if win == "tie" or win is None:
            break
        side = 1 if win == program_slug else -1
        if streak_sign == 0:
            streak_sign = side
            streak = 1
        elif side == streak_sign:
            streak += 1
        else:
            break
    first_year = rows[0]["season_year"] if rows else None
    last_year = rows[-1]["season_year"] if rows else None
    return {
        "wins": w, "losses": l, "ties": t,
        "total_meetings": w + l + t,
        "streak": streak * streak_sign,
        "first_year": first_year,
        "last_year": last_year,
    }


def fetch_next_meeting(
    db,
    program_a_slug: str,
    program_b_slug: str,
) -> dict[str, Any] | None:
    a_slug, b_slug = _canonical_pair(program_a_slug, program_b_slug)
    rows = db.query_all(
        """
        select season_year, week, game_date, home_slug, venue
        from team_rivalry_meetings
        where program_a_slug = :a and program_b_slug = :b
          and is_complete = 0
        order by coalesce(game_date, '9999') asc
        limit 1
        """,
        {"a": a_slug, "b": b_slug},
    )
    return rows[0] if rows else None
