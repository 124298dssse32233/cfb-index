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
