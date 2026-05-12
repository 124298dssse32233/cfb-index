"""Season-Arc loader — CFPEraView data for the 2014+ per-team-season archive.

Writes one row per (team, season_year) to ``team_season_arc``:

* record + win_pct from ``games`` (season_year ≥ 2014, status = Final)
* ap_rank_final from ``official_rankings`` (max week, system 'AP Top 25')
* sp_plus_final from ``power_ratings_weekly`` (max week)
* mood_score_avg from ``team_week_conversation_features`` (season-mean)
* cfp_flag / title_game_flag / title_won_flag from a hand-annotated canonical
  history map — the DB's postseason flags alone can't reliably distinguish a
  CFP semifinal loss from a standard bowl loss
* brick_state pre-computed so the renderer just reads a CSS class name
* quality_score (0-100) drives the SVG trajectory line when mood data is NULL:
  win% baseline (0-60 pts) + AP boost (0-25 pts) + SP+ centring (0-15 pts)
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any


# --------------------------------------------------------------------------
# Hand-annotated canonical CFP history, 2014-2025.
# Keys: program_slug → { season_year: {flags} }
# Flags: cfp=made CFP, title_game=reached championship, title_won=won it.
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Hand-annotated final AP poll rank per (program, year) for the 11 profiled
# programs, 2014-2019 + 2021. The DB's `official_rankings` table currently
# only covers 2020 + 2022-2025, which left the AP polyline sparse. This map
# fills the gap with the final AP poll (post-bowls) rank for each year so the
# rank trajectory renders honestly. `None` = unranked (outside AP top-25).
#
# Programs outside this map (or years not listed) fall back to the DB query.
# --------------------------------------------------------------------------

FINAL_AP_HISTORY: dict[str, dict[int, int | None]] = {
    "alabama": {
        2014: 4, 2015: 1, 2016: 2, 2017: 1, 2018: 2, 2019: 8,
        2021: 2,
    },
    "ohio-state": {
        2014: 1, 2015: 4, 2016: 6, 2017: 5, 2018: 3, 2019: 3,
        2021: 6,
    },
    "notre-dame": {
        2014: None, 2015: 11, 2016: None, 2017: 11, 2018: 5, 2019: 12,
        2021: 8,
    },
    "georgia": {
        2014: 9, 2015: None, 2016: None, 2017: 2, 2018: 7, 2019: 4,
        2021: 1,
    },
    "michigan": {
        2014: None, 2015: 12, 2016: 10, 2017: None, 2018: 14, 2019: 18,
        2021: 3,
    },
    "oregon": {
        2014: 2, 2015: 19, 2016: None, 2017: None, 2018: None, 2019: 5,
        2021: 22,
    },
    "texas": {
        2014: None, 2015: None, 2016: None, 2017: None, 2018: 9, 2019: None,
        2021: None,
    },
    "penn-state": {
        2014: None, 2015: None, 2016: 7, 2017: 8, 2018: 17, 2019: 9,
        2021: None,
    },
    "usc": {
        2014: 20, 2015: None, 2016: 3, 2017: 12, 2018: None, 2019: None,
        2021: None,
    },
    "vanderbilt": {
        2014: None, 2015: None, 2016: None, 2017: None, 2018: None, 2019: None,
        2021: None,
    },
    "massachusetts": {
        2014: None, 2015: None, 2016: None, 2017: None, 2018: None, 2019: None,
        2021: None,
    },
}


CFP_HISTORY: dict[str, dict[int, dict[str, bool]]] = {
    "notre-dame": {
        2018: {"cfp": True},                                  # Cotton Bowl semi loss
        2020: {"cfp": True},                                  # Rose Bowl semi loss to Alabama
        2024: {"cfp": True, "title_game": True},              # Lost title game to Ohio State
    },
    "alabama": {
        2014: {"cfp": True},                                  # Sugar Bowl semi loss to Ohio State
        2015: {"cfp": True, "title_game": True, "title_won": True},
        2016: {"cfp": True, "title_game": True},              # Lost to Clemson
        2017: {"cfp": True, "title_game": True, "title_won": True},
        2018: {"cfp": True, "title_game": True},              # Lost to Clemson
        2020: {"cfp": True, "title_game": True, "title_won": True},
        2021: {"cfp": True, "title_game": True},              # Lost to Georgia
        2023: {"cfp": True},                                  # Rose Bowl semi loss to Michigan
    },
    "ohio-state": {
        2014: {"cfp": True, "title_game": True, "title_won": True},  # First CFP; won the title
        2016: {"cfp": True},                                  # Fiesta Bowl semi loss to Clemson
        2019: {"cfp": True},                                  # Fiesta Bowl semi loss to Clemson
        2020: {"cfp": True, "title_game": True},              # Lost to Alabama
        2022: {"cfp": True},                                  # Peach Bowl semi loss to Georgia
        2024: {"cfp": True, "title_game": True, "title_won": True},  # Beat Notre Dame for the title
    },
    "georgia": {
        2017: {"cfp": True, "title_game": True},              # Lost OT to Alabama
        2018: {"cfp": True},                                  # Rose Bowl — wait, 2018 was Oklahoma / Alabama semis
        2019: {"cfp": False},                                 # Did not make CFP 2019
        2020: {"cfp": False},
        2021: {"cfp": True, "title_game": True, "title_won": True},
        2022: {"cfp": True, "title_game": True, "title_won": True},
        2024: {"cfp": True},                                  # Sugar Bowl loss to Notre Dame in quarterfinal
    },
    "texas": {
        2023: {"cfp": True},                                  # Sugar Bowl semi loss to Washington
        2024: {"cfp": True},                                  # Cotton Bowl semi loss to Ohio State
    },
    "michigan": {
        2021: {"cfp": True},                                  # Orange Bowl semi loss to Georgia
        2022: {"cfp": True},                                  # Fiesta Bowl semi loss to TCU
        2023: {"cfp": True, "title_game": True, "title_won": True},
    },
    "usc": {},
    "oregon": {
        2014: {"cfp": True, "title_game": True},              # Lost to Ohio State in first CFP title game
        2024: {"cfp": True},                                  # 12-team CFP quarterfinal loss to Ohio State
    },
    "penn-state": {
        2016: {"cfp": False},                                 # No CFP bid, went to Rose Bowl (lost to USC)
        2024: {"cfp": True},                                  # Semifinal loss to Notre Dame
    },
    "vanderbilt": {},
    "massachusetts": {},
}


SEASON_MIN = 2014
# Roll forward automatically: in May-July the upcoming season hasn't
# kicked off yet so cap at the current calendar year. In Aug+ when the
# new season is underway, callers can override via the latest_season
# arg, but the safe default still includes the in-progress year.
# Previously hardcoded `SEASON_MAX = 2025` which silently dropped the
# 2026 season once the calendar rolled over.
from datetime import datetime as _datetime
SEASON_MAX = _datetime.utcnow().year


# Regular-season game counts per CFP-era year, used for partial-data detection.
# A season that ended with <EXPECTED - 1 recorded games in our DB is treated as
# a partial ingest snapshot, not a finished season — the brick displays "(partial)"
# rather than leaking a mid-season record as if it were the final.
# Pre-pandemic years played 12 regular + up to 4 post (conf champ / bowl / CFP
# semi / CFP title). We check against a conservative floor: if a non-current
# season has fewer games recorded than that floor, mark partial.
_EXPECTED_GAMES_FLOOR: dict[int, int] = {
    2014: 12, 2015: 12, 2016: 12, 2017: 12, 2018: 12, 2019: 12,
    2020: 9,   # COVID-truncated SEC 10-game / others varied
    2021: 12, 2022: 12, 2023: 12, 2024: 12, 2025: 12,
}


def _is_partial_record(
    season_year: int,
    total_games: int,
    is_current: bool,
) -> bool:
    """True if (season_year, games_played) looks like an incomplete-ingest snapshot.

    The current season is always allowed to be short — it's legitimately in-progress.
    Everything else: if the DB has fewer than the era's regular-season floor, the
    record on the brick is misleading and we flag it as partial.
    """
    if is_current or total_games == 0:
        return False
    floor = _EXPECTED_GAMES_FLOOR.get(season_year, 12)
    return total_games < floor


def _compute_record(conn: sqlite3.Connection, team_id: int, season_year: int) -> tuple[int, int, int]:
    rows = conn.execute(
        """
        select home_team_id, away_team_id, home_points, away_points
        from games
        where season_year = :s
          and (home_team_id = :tid or away_team_id = :tid)
          and status in ('Final','final','FINAL')
        """,
        {"s": season_year, "tid": team_id},
    ).fetchall()
    w = l = t = 0
    for home_id, away_id, hp, ap in rows:
        if hp is None or ap is None:
            continue
        is_home = int(home_id) == team_id
        mine = int(hp) if is_home else int(ap)
        theirs = int(ap) if is_home else int(hp)
        if mine > theirs:
            w += 1
        elif mine < theirs:
            l += 1
        else:
            t += 1
    return w, l, t


def _fetch_final_ap(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    slug: str | None = None,
) -> int | None:
    """Return final AP rank. Prefers DB; falls back to FINAL_AP_HISTORY map
    for the 11 profiled programs in years the DB ingest doesn't cover
    (pre-2020 + 2021).
    """
    row = conn.execute(
        """
        select rank_value
        from official_rankings
        where team_id = :tid and season_year = :s and ranking_system = 'AP Top 25'
        order by week desc
        limit 1
        """,
        {"tid": team_id, "s": season_year},
    ).fetchone()
    if row and row[0] is not None:
        return int(row[0])
    if slug:
        ap_map = FINAL_AP_HISTORY.get(slug, {})
        if season_year in ap_map:
            return ap_map[season_year]
    return None


def _fetch_final_sp(conn: sqlite3.Connection, team_id: int, season_year: int) -> float | None:
    row = conn.execute(
        """
        select power_rating
        from power_ratings_weekly
        where team_id = :tid and season_year = :s
        order by week desc
        limit 1
        """,
        {"tid": team_id, "s": season_year},
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def _fetch_mood_avg(conn: sqlite3.Connection, team_id: int, season_year: int) -> float | None:
    row = conn.execute(
        """
        select avg(net_sentiment_score) as avg_net
        from team_week_conversation_features
        where team_id = :tid and season_year = :s
          and source_name = 'all' and audience_bucket = 'all'
        """,
        {"tid": team_id, "s": season_year},
    ).fetchone()
    if not row or row[0] is None:
        return None
    # Map [-1, 1] → [0, 100]
    return max(0.0, min(100.0, (float(row[0]) + 1.0) * 50.0))


def _compute_quality_score(
    win_pct: float | None,
    ap_rank: int | None,
    sp_plus: float | None,
) -> float | None:
    """0-100 proxy for season quality. Drives the trajectory line when mood is absent.

    Returns None when no inputs are available (dataset-gap seasons) so the
    renderer can produce a polyline gap instead of drawing through zero.
    """
    if win_pct is None and ap_rank is None and sp_plus is None:
        return None
    score = 0.0
    if win_pct is not None:
        score += min(60.0, win_pct * 60.0)          # up to 60 from record
    if ap_rank is not None:
        ap_contrib = max(0.0, 25.0 - (ap_rank - 1) * (25.0 / 25.0))  # #1 → +25, #25 → +1
        score += ap_contrib
    if sp_plus is not None:
        # SP+ roughly ranges -25..+35 in the DB — centre and cap at ±15 pts
        sp_contrib = max(-15.0, min(15.0, sp_plus * 0.5))
        score += sp_contrib + 15                     # shift to 0..30-ish
        score -= 15                                  # re-centre
    # Clamp
    return max(0.0, min(100.0, score))


def _derive_brick_state(
    wins: int,
    losses: int,
    cfp: bool,
    title_game: bool,
    is_current: bool,
    has_games: bool = True,
    is_partial: bool = False,
) -> str:
    if not has_games and (cfp or title_game):
        # Canonical CFP history exists but games aren't in the DB (ingest gap).
        # Keep the peak/title-era semantics so the brick still shows.
        return "title-era" if title_game else "peak"
    if not has_games:
        return "data-gap"
    if is_current:
        return "current"
    if title_game:
        return "title-era"
    if cfp:
        return "peak"
    if is_partial:
        # Incomplete ingest for a past season — the record is a snapshot, not
        # a finality. Don't classify as winning/crisis when we don't know the
        # finish.
        return "partial-data"
    if losses > wins:
        return "crisis"
    if wins > losses:
        return "winning"
    return "baseline"


def refresh_team_arc(conn: sqlite3.Connection, slug: str, team_id: int, latest_season: int) -> int:
    """Write 12 rows (2014-2025) for the team. Returns count written.

    Writes a row when EITHER games exist for the (team, season) OR the
    CFP_HISTORY map has a flag for that year (so a dataset gap doesn't
    erase a canonical CFP appearance — the brick + chart marker still show,
    with a 0-0 record and a 'data-gap' brick state).
    """
    history = CFP_HISTORY.get(slug, {})
    written = 0
    for year in range(SEASON_MIN, SEASON_MAX + 1):
        w, l, t = _compute_record(conn, team_id, year)
        total = w + l + t
        has_history = year in history
        if total == 0 and not has_history:
            # Skip seasons with no games AND no canonical history
            # (prevents ghost rows for programs that joined FBS mid-range).
            continue
        win_pct = (w / total) if total else None
        ap = _fetch_final_ap(conn, team_id, year, slug=slug)
        sp = _fetch_final_sp(conn, team_id, year)
        mood = _fetch_mood_avg(conn, team_id, year)
        flags = history.get(year, {})
        cfp = bool(flags.get("cfp"))
        title_game = bool(flags.get("title_game"))
        title_won = bool(flags.get("title_won"))
        is_current = (year == latest_season)
        is_crisis = (l > w)

        quality = _compute_quality_score(win_pct, ap, sp)
        is_partial = _is_partial_record(year, total, is_current)
        brick_state = _derive_brick_state(
            w, l, cfp, title_game, is_current,
            has_games=(total > 0),
            is_partial=is_partial,
        )

        conn.execute(
            """
            insert into team_season_arc (
              team_id, season_year, wins, losses, ties, win_pct,
              ap_rank_final, sp_plus_final, cfp_flag, title_game_flag, title_won_flag,
              is_crisis, is_current, mood_score_avg, quality_score, brick_state,
              bowl_game_name, notes_json, generated_at_utc
            ) values (
              :tid, :s, :w, :l, :t, :wp,
              :ap, :sp, :cfp, :tg, :tw,
              :crisis, :cur, :mood, :q, :bs,
              NULL, :notes, current_timestamp
            )
            on conflict(team_id, season_year) do update set
              wins = excluded.wins,
              losses = excluded.losses,
              ties = excluded.ties,
              win_pct = excluded.win_pct,
              ap_rank_final = excluded.ap_rank_final,
              sp_plus_final = excluded.sp_plus_final,
              cfp_flag = excluded.cfp_flag,
              title_game_flag = excluded.title_game_flag,
              title_won_flag = excluded.title_won_flag,
              is_crisis = excluded.is_crisis,
              is_current = excluded.is_current,
              mood_score_avg = excluded.mood_score_avg,
              quality_score = excluded.quality_score,
              brick_state = excluded.brick_state,
              notes_json = excluded.notes_json,
              generated_at_utc = current_timestamp
            """,
            {
                "tid": team_id, "s": year, "w": w, "l": l, "t": t, "wp": win_pct,
                "ap": ap, "sp": sp,
                "cfp": 1 if cfp else 0,
                "tg": 1 if title_game else 0,
                "tw": 1 if title_won else 0,
                "crisis": 1 if is_crisis else 0,
                "cur": 1 if is_current else 0,
                "mood": mood, "q": quality, "bs": brick_state,
                "notes": json.dumps({"is_partial": is_partial}),
            },
        )
        written += 1
    return written


# --------------------------------------------------------------------------
# Read side (used by data.py)
# --------------------------------------------------------------------------

def fetch_arc_rows(db, team_id: int) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select season_year, wins, losses, ties, win_pct,
               ap_rank_final, sp_plus_final,
               cfp_flag, title_game_flag, title_won_flag,
               is_crisis, is_current,
               mood_score_avg, quality_score, brick_state,
               notes_json
        from team_season_arc
        where team_id = :tid
        order by season_year asc
        """,
        {"tid": team_id},
    )
