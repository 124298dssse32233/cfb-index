"""Deterministic data queries for Chronicle visuals.

Every visual must trace back to a query function registered here. The renderer
never reaches into arbitrary tables — it consumes the typed dict returned by
one of these `query_*` functions.

Each query returns a uniform shape:
    {
        "query_id": str,
        "source_tables": list[str],
        "rows": list[dict],
        "summary_stats": dict,
        "sample_n": int,
        "confidence": "high" | "medium" | "low" | "unset",
        "limitations": list[str],
        "as_of_utc": str,
    }

Db wrapper compatibility: works with both raw sqlite3.Connection and the
project's Database wrapper (matches the pattern in cache.py).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("cfb_rankings.chronicle.visuals.queries")


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _query_all(db: Any, sql: str, params: tuple | dict = ()) -> list[dict]:
    """Run a query and return list[dict] regardless of db wrapper."""
    if hasattr(db, "query_all"):
        return db.query_all(sql, params)
    cur = db.execute(sql, params)
    cols = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _query_one(db: Any, sql: str, params: tuple | dict = ()) -> dict | None:
    rows = _query_all(db, sql, params)
    return rows[0] if rows else None


def _team_id_for_slug(db: Any, slug: str) -> int | None:
    row = _query_one(db, "SELECT team_id FROM teams WHERE slug = ?", (slug,))
    return row["team_id"] if row else None


def _team_name_for_id(db: Any, team_id: int) -> str:
    row = _query_one(db, "SELECT canonical_name FROM teams WHERE team_id = ?", (team_id,))
    return row["canonical_name"] if row else f"team-{team_id}"


# ---------------------------------------------------------------------------
# Query: Statement Win Ladder
# ---------------------------------------------------------------------------
#
# Source: team_rating_deltas joined to games + teams.
# For a team in a season, rank wins by power_delta + resume_delta. Show the
# top 5 results plus the magnitude that separates them.
#
# Rows shape:
#   game_id, week, opponent_slug, opponent_name, opponent_power_rating,
#   result_text (W/L score), power_delta, resume_delta, total_delta,
#   is_win, is_top_result
# ---------------------------------------------------------------------------


def query_statement_win_ladder(
    db: Any,
    *,
    slug: str,
    season_year: int,
    week_number: int | None = None,
    top_n: int = 5,
) -> dict[str, Any]:
    query_id = "statement_win_ladder_v1"
    source_tables = ["team_rating_deltas", "games", "teams", "power_ratings_weekly"]

    team_id = _team_id_for_slug(db, slug)
    if team_id is None:
        return _empty_result(query_id, source_tables, "team slug not found")

    week_clause = "AND g.week <= :week_number" if week_number else ""
    params: dict[str, Any] = {"team_id": team_id, "season_year": season_year}
    if week_number:
        params["week_number"] = week_number

    sql = f"""
    SELECT
        d.game_id,
        d.team_id,
        d.power_delta,
        d.resume_delta,
        d.offense_delta,
        d.defense_delta,
        g.week,
        g.home_team_id,
        g.away_team_id,
        g.home_points,
        g.away_points,
        g.start_time_utc,
        CASE WHEN d.team_id = g.home_team_id THEN g.away_team_id ELSE g.home_team_id END AS opponent_team_id,
        CASE WHEN d.team_id = g.home_team_id THEN g.home_points - g.away_points ELSE g.away_points - g.home_points END AS margin
    FROM team_rating_deltas d
    JOIN games g ON g.game_id = d.game_id
    WHERE d.team_id = :team_id
      AND g.season_year = :season_year
      {week_clause}
      AND g.home_points IS NOT NULL
      AND g.away_points IS NOT NULL
    ORDER BY (d.power_delta + d.resume_delta) DESC
    """

    raw = _query_all(db, sql, params)
    if not raw:
        return _empty_result(query_id, source_tables, "no completed games found")

    rows: list[dict] = []
    for r in raw:
        opp_id = r["opponent_team_id"]
        opp_name = _team_name_for_id(db, opp_id) if opp_id else "TBD"
        opp_slug_row = _query_one(db, "SELECT slug FROM teams WHERE team_id = ?", (opp_id,)) if opp_id else None
        margin = r["margin"] or 0
        is_win = margin > 0
        team_pts = r["home_points"] if r["team_id"] == r["home_team_id"] else r["away_points"]
        opp_pts = r["away_points"] if r["team_id"] == r["home_team_id"] else r["home_points"]
        result_text = f"{'W' if is_win else 'L'} {int(team_pts or 0)}-{int(opp_pts or 0)}"
        rows.append({
            "game_id": r["game_id"],
            "week": r["week"],
            "opponent_slug": opp_slug_row["slug"] if opp_slug_row else None,
            "opponent_name": opp_name,
            "result_text": result_text,
            "power_delta": float(r["power_delta"] or 0),
            "resume_delta": float(r["resume_delta"] or 0),
            "offense_delta": float(r["offense_delta"] or 0),
            "defense_delta": float(r["defense_delta"] or 0),
            "total_delta": float((r["power_delta"] or 0) + (r["resume_delta"] or 0)),
            "is_win": is_win,
        })

    top_rows = rows[:top_n]
    if top_rows:
        top_rows[0]["is_top_result"] = True

    delta_spread = (rows[0]["total_delta"] - rows[-1]["total_delta"]) if len(rows) > 1 else 0.0
    sample_n = len(rows)
    confidence = "high" if sample_n >= 8 else ("medium" if sample_n >= 4 else "low")

    return {
        "query_id": query_id,
        "source_tables": source_tables,
        "rows": top_rows,
        "summary_stats": {
            "delta_spread": delta_spread,
            "total_games": sample_n,
            "team_id": team_id,
        },
        "sample_n": sample_n,
        "confidence": confidence,
        "limitations": [] if sample_n >= 4 else ["small sample (<4 games)"],
        "as_of_utc": _now_utc(),
    }


# ---------------------------------------------------------------------------
# Query: Returning Production X-Ray
# ---------------------------------------------------------------------------


def query_returning_production_xray(
    db: Any,
    *,
    slug: str,
    season_year: int,
    week_number: int | None = None,  # ignored — annual snapshot
) -> dict[str, Any]:
    query_id = "returning_production_xray_v1"
    source_tables = ["returning_production", "teams"]

    team_id = _team_id_for_slug(db, slug)
    if team_id is None:
        return _empty_result(query_id, source_tables, "team slug not found")

    sql = """
    SELECT season_year, returning_total, returning_offense, returning_defense,
           returning_qb, returning_ol, total_ppa, percent_ppa,
           percent_passing_ppa, percent_receiving_ppa, percent_rushing_ppa,
           usage_rate, passing_usage_rate, receiving_usage_rate, rushing_usage_rate,
           source_name
    FROM returning_production
    WHERE team_id = :team_id AND season_year = :season_year
    LIMIT 1
    """
    row = _query_one(db, sql, {"team_id": team_id, "season_year": season_year})
    if not row:
        return _empty_result(query_id, source_tables, "no returning production for season")

    # Peer comparison — pull league average for same season
    peer_avg_sql = """
    SELECT AVG(returning_total) AS league_avg_total,
           AVG(returning_offense) AS league_avg_offense,
           AVG(returning_defense) AS league_avg_defense
    FROM returning_production
    WHERE season_year = :season_year
    """
    peer = _query_one(db, peer_avg_sql, {"season_year": season_year}) or {}

    # Build a waterfall: total split by side, qb, oline
    bars = [
        {"label": "Offense", "value": float(row.get("returning_offense") or 0), "kind": "category"},
        {"label": "Defense", "value": float(row.get("returning_defense") or 0), "kind": "category"},
    ]
    # QB returning and OL returning are subcomponents — surfaced as annotations
    return {
        "query_id": query_id,
        "source_tables": source_tables,
        "rows": bars,
        "summary_stats": {
            "season_year": season_year,
            "team_id": team_id,
            "returning_total": float(row.get("returning_total") or 0),
            "returning_qb": float(row.get("returning_qb") or 0),
            "returning_ol": float(row.get("returning_ol") or 0),
            "league_avg_total": float(peer.get("league_avg_total") or 0),
            "league_avg_offense": float(peer.get("league_avg_offense") or 0),
            "league_avg_defense": float(peer.get("league_avg_defense") or 0),
            "source_name": row.get("source_name") or "cfbd",
        },
        "sample_n": 1,
        "confidence": "high",
        "limitations": [],
        "as_of_utc": _now_utc(),
    }


# ---------------------------------------------------------------------------
# Query: Heisman Race Braid
# ---------------------------------------------------------------------------


def query_heisman_race_braid(
    db: Any,
    *,
    slug: str | None = None,         # player slug (optional anchor)
    season_year: int,
    week_number: int | None = None,
    top_n: int = 8,
) -> dict[str, Any]:
    """Multi-week rank trajectory for the top N Heisman contenders."""
    query_id = "heisman_race_braid_v1"
    source_tables = ["heisman_rankings_weekly", "players", "teams"]

    # Most recent week available for season
    if week_number is None:
        recent = _query_one(
            db,
            "SELECT MAX(week) AS w FROM heisman_rankings_weekly WHERE season_year = ?",
            (season_year,),
        )
        week_number = (recent or {}).get("w") or 0

    if week_number == 0:
        return _empty_result(query_id, source_tables, "no Heisman rankings for season")

    # Top N at the snapshot week
    top_sql = """
    SELECT h.player_id, h.team_id, h.rank_overall, h.latent_score,
           h.finalist_probability, h.win_probability
    FROM heisman_rankings_weekly h
    WHERE h.season_year = :season_year AND h.week = :week
      AND h.rank_overall IS NOT NULL
    ORDER BY h.rank_overall ASC
    LIMIT :top_n
    """
    top_at_week = _query_all(
        db,
        top_sql,
        {"season_year": season_year, "week": week_number, "top_n": top_n},
    )
    if not top_at_week:
        return _empty_result(query_id, source_tables, "no rankings at snapshot week")

    player_ids = [r["player_id"] for r in top_at_week]
    placeholders = ",".join("?" for _ in player_ids)

    history_sql = f"""
    SELECT h.player_id, h.team_id, h.week, h.rank_overall, h.latent_score,
           h.finalist_probability, p.full_name AS player_name, t.slug AS team_slug
    FROM heisman_rankings_weekly h
    LEFT JOIN players p ON p.player_id = h.player_id
    LEFT JOIN teams t ON t.team_id = h.team_id
    WHERE h.season_year = ?
      AND h.player_id IN ({placeholders})
      AND h.rank_overall IS NOT NULL
    ORDER BY h.player_id, h.week
    """
    history = _query_all(db, history_sql, tuple([season_year, *player_ids]))

    # Group by player
    by_player: dict[int, dict] = {}
    for row in history:
        pid = row["player_id"]
        if pid not in by_player:
            by_player[pid] = {
                "player_id": pid,
                "player_name": row.get("player_name") or f"player-{pid}",
                "team_slug": row.get("team_slug"),
                "current_rank": next(
                    (t["rank_overall"] for t in top_at_week if t["player_id"] == pid),
                    None,
                ),
                "history": [],
            }
        by_player[pid]["history"].append({
            "week": row["week"],
            "rank": row["rank_overall"],
            "latent_score": float(row["latent_score"] or 0),
            "finalist_probability": float(row.get("finalist_probability") or 0),
        })

    rows = sorted(by_player.values(), key=lambda p: p["current_rank"] or 999)

    return {
        "query_id": query_id,
        "source_tables": source_tables,
        "rows": rows,
        "summary_stats": {
            "season_year": season_year,
            "snapshot_week": week_number,
            "anchor_slug": slug,
        },
        "sample_n": len(rows),
        "confidence": "high" if len(rows) >= 6 else "medium",
        "limitations": [],
        "as_of_utc": _now_utc(),
    }


# ---------------------------------------------------------------------------
# Query: Roster Replacement Grid
# ---------------------------------------------------------------------------


def query_roster_replacement_grid(
    db: Any,
    *,
    slug: str,
    season_year: int,
    week_number: int | None = None,  # ignored
) -> dict[str, Any]:
    query_id = "roster_replacement_grid_v1"
    source_tables = ["transfer_entries", "teams"]

    team_id = _team_id_for_slug(db, slug)
    if team_id is None:
        return _empty_result(query_id, source_tables, "team slug not found")

    # Incoming transfers (gains)
    in_sql = """
    SELECT position, COUNT(*) AS n, AVG(transfer_points) AS avg_points,
           AVG(rating) AS avg_rating
    FROM transfer_entries
    WHERE to_team_id = :team_id AND season_year = :season_year
      AND position IS NOT NULL
    GROUP BY position
    ORDER BY n DESC
    """
    incoming = _query_all(db, in_sql, {"team_id": team_id, "season_year": season_year})

    # Outgoing transfers (losses)
    out_sql = """
    SELECT position, COUNT(*) AS n, AVG(transfer_points) AS avg_points,
           AVG(rating) AS avg_rating
    FROM transfer_entries
    WHERE from_team_id = :team_id AND season_year = :season_year
      AND position IS NOT NULL
    GROUP BY position
    ORDER BY n DESC
    """
    outgoing = _query_all(db, out_sql, {"team_id": team_id, "season_year": season_year})

    # Normalize positions and merge into grid
    positions = sorted(set(
        [r["position"] for r in incoming] + [r["position"] for r in outgoing]
    ))
    rows = []
    for pos in positions:
        in_row = next((r for r in incoming if r["position"] == pos), None)
        out_row = next((r for r in outgoing if r["position"] == pos), None)
        rows.append({
            "position": pos,
            "incoming_n": int(in_row["n"]) if in_row else 0,
            "incoming_avg_rating": float(in_row["avg_rating"] or 0) if in_row else 0.0,
            "outgoing_n": int(out_row["n"]) if out_row else 0,
            "outgoing_avg_rating": float(out_row["avg_rating"] or 0) if out_row else 0.0,
            "net_n": (int(in_row["n"]) if in_row else 0) - (int(out_row["n"]) if out_row else 0),
        })

    total_in = sum(r["incoming_n"] for r in rows)
    total_out = sum(r["outgoing_n"] for r in rows)
    sample_n = total_in + total_out
    confidence = "high" if sample_n >= 12 else ("medium" if sample_n >= 4 else "low")

    return {
        "query_id": query_id,
        "source_tables": source_tables,
        "rows": rows,
        "summary_stats": {
            "team_id": team_id,
            "season_year": season_year,
            "total_incoming": total_in,
            "total_outgoing": total_out,
            "net_movement": total_in - total_out,
        },
        "sample_n": sample_n,
        "confidence": confidence,
        "limitations": [] if sample_n >= 4 else ["small portal sample"],
        "as_of_utc": _now_utc(),
    }


# ---------------------------------------------------------------------------
# Query: CFP Bubble Wall
# ---------------------------------------------------------------------------


def query_cfp_bubble_wall(
    db: Any,
    *,
    slug: str,
    season_year: int,
    week_number: int | None = None,
) -> dict[str, Any]:
    query_id = "cfp_bubble_wall_v1"
    source_tables = ["official_rankings", "power_ratings_weekly", "resume_ratings_weekly", "teams"]

    anchor_team_id = _team_id_for_slug(db, slug)

    # Pick the most-recent week that has all three sources (or week_number override)
    if week_number is None:
        wk_row = _query_one(
            db,
            """
            SELECT MAX(week) AS w FROM power_ratings_weekly WHERE season_year = ?
            """,
            (season_year,),
        )
        week_number = (wk_row or {}).get("w") or 0
    if week_number == 0:
        return _empty_result(query_id, source_tables, "no power ratings for season")

    # Pull top-25 candidates by resume_ratings for the snapshot week
    sql = """
    SELECT r.team_id, r.resume_score, r.season_year, r.week,
           p.power_rating,
           t.canonical_name AS team_name, t.slug
    FROM resume_ratings_weekly r
    JOIN power_ratings_weekly p
      ON p.team_id = r.team_id AND p.season_year = r.season_year AND p.week = r.week
    JOIN teams t ON t.team_id = r.team_id
    WHERE r.season_year = :season_year AND r.week = :week
      AND t.level_code = 'FBS' AND t.is_active = 1
    ORDER BY r.resume_score DESC
    LIMIT 25
    """
    raw = _query_all(db, sql, {"season_year": season_year, "week": week_number})
    if not raw:
        return _empty_result(query_id, source_tables, "no resume+power rows for week")

    # Percentile rank within the snapshot set
    res_sorted = sorted([r["resume_score"] or 0 for r in raw])
    pow_sorted = sorted([r["power_rating"] or 0 for r in raw])
    n = len(raw)

    def pctile(values: list[float], v: float) -> float:
        # Linear pctile in [0,1]
        i = sum(1 for x in values if x <= v)
        return (i - 0.5) / max(1, n)

    rows: list[dict] = []
    for r in raw:
        x = pctile(res_sorted, r["resume_score"] or 0)
        y = pctile(pow_sorted, r["power_rating"] or 0)
        is_anchor = r["team_id"] == anchor_team_id
        # Top-5 of either axis = peer-label
        peer = (r["resume_score"] in res_sorted[-5:]) or (r["power_rating"] in pow_sorted[-5:])
        rows.append({
            "slug": r["slug"],
            "label": r["team_name"],
            "x": x,
            "y": y,
            "peer_label": peer,
            "anchor": is_anchor,
        })

    return {
        "query_id": query_id,
        "source_tables": source_tables,
        "rows": rows,
        "summary_stats": {
            "season_year": season_year,
            "snapshot_week": week_number,
            "anchor_slug": slug,
            "n_teams": n,
        },
        "sample_n": n,
        "confidence": "high" if n >= 15 else "medium",
        "limitations": [],
        "as_of_utc": _now_utc(),
    }


# ---------------------------------------------------------------------------
# Query: Talent Yield Curve
# ---------------------------------------------------------------------------


def query_talent_yield_curve(
    db: Any,
    *,
    slug: str,
    season_year: int,
    week_number: int | None = None,  # ignored
) -> dict[str, Any]:
    query_id = "talent_yield_curve_v1"
    source_tables = ["team_talent_snapshots", "player_nfl_draft", "teams"]

    anchor_team_id = _team_id_for_slug(db, slug)

    # x-axis: talent rank percentile (1.0 = top talent class) at season
    # y-axis: 3-year rolling NFL draft yield percentile

    # Pull all FBS team talent for season
    talent_sql = """
    SELECT t.team_id, t.slug, t.canonical_name AS team_name,
           tt.talent_score, tt.talent_rank
    FROM teams t
    JOIN team_talent_snapshots tt
      ON tt.team_id = t.team_id AND tt.season_year = :season_year
    WHERE t.level_code = 'FBS' AND t.is_active = 1
    """
    talent_rows = _query_all(db, talent_sql, {"season_year": season_year})
    if not talent_rows:
        return _empty_result(query_id, source_tables, "no talent snapshot for season")

    # Pull 3-year rolling draft picks per team (draft_year in [season-2, season])
    draft_sql = """
    SELECT college_team_id, COUNT(*) AS picks
    FROM player_nfl_draft
    WHERE college_team_id IS NOT NULL
      AND draft_year BETWEEN :y_start AND :y_end
    GROUP BY college_team_id
    """
    draft_rows = _query_all(
        db, draft_sql,
        {"y_start": season_year - 2, "y_end": season_year},
    )
    draft_by_team: dict[int, int] = {int(r["college_team_id"]): int(r["picks"]) for r in draft_rows}

    # Compute percentiles within the talent universe
    talent_scores = sorted([r["talent_score"] or 0 for r in talent_rows])
    draft_counts = sorted([draft_by_team.get(r["team_id"], 0) for r in talent_rows])
    n = len(talent_rows)

    def pctile(values: list[float], v: float) -> float:
        i = sum(1 for x in values if x <= v)
        return (i - 0.5) / max(1, n)

    rows: list[dict] = []
    for r in talent_rows:
        team_id = r["team_id"]
        x = pctile(talent_scores, r["talent_score"] or 0)
        picks = draft_by_team.get(team_id, 0)
        y = pctile(draft_counts, picks)
        is_anchor = team_id == anchor_team_id
        # Top 8 either axis -> peer label
        peer = (r["talent_score"] in talent_scores[-8:]) or (picks in draft_counts[-8:])
        rows.append({
            "slug": r["slug"],
            "label": r["team_name"],
            "x": x,
            "y": y,
            "peer_label": peer,
            "anchor": is_anchor,
        })

    return {
        "query_id": query_id,
        "source_tables": source_tables,
        "rows": rows,
        "summary_stats": {
            "season_year": season_year,
            "anchor_slug": slug,
            "n_teams": n,
        },
        "sample_n": n,
        "confidence": "high" if n >= 50 else "medium",
        "limitations": [],
        "as_of_utc": _now_utc(),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_result(query_id: str, source_tables: list[str], reason: str) -> dict[str, Any]:
    return {
        "query_id": query_id,
        "source_tables": source_tables,
        "rows": [],
        "summary_stats": {},
        "sample_n": 0,
        "confidence": "unset",
        "limitations": [reason],
        "as_of_utc": _now_utc(),
    }
