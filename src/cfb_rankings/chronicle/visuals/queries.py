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

    # Team-relevance gate: on a TEAM page this visual is only worth showing if
    # that team actually has a Heisman contender. Otherwise it renders the
    # NATIONAL race (e.g. Oregon's QB on North Texas's page) — irrelevant and
    # confusing. Suppress when the anchor team has no top-40 player.
    # Gate to top_n (the braid only DISPLAYS the top N). A team with a #22
    # player isn't in the rendered race, so showing the national top-8 on its
    # page is still irrelevant — require a player within the displayed band.
    anchor_team_id = _team_id_for_slug(db, slug) if slug else None
    if anchor_team_id is not None:
        rel = _query_one(
            db,
            "SELECT 1 AS x FROM heisman_rankings_weekly "
            "WHERE season_year = :s AND team_id = :tid AND rank_overall <= :tn LIMIT 1",
            {"s": season_year, "tid": anchor_team_id, "tn": top_n},
        )
        if not rel:
            return _empty_result(query_id, source_tables, "no Heisman contender on this team")

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

    # Use the latest portal cycle that actually has data for this team (>= the
    # requested preview season), so the freshest portal class surfaces even
    # when it's newer than the global preview season. e.g. with 2026 transfer
    # data ingested, a preview-season=2025 request still shows the 2026 portal.
    latest = _query_one(
        db,
        "SELECT MAX(season_year) AS sy FROM transfer_entries "
        "WHERE (to_team_id = :tid OR from_team_id = :tid) AND season_year >= :sy",
        {"tid": team_id, "sy": season_year},
    )
    if latest and latest.get("sy"):
        season_year = int(latest["sy"])

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
        in_n = int(in_row["n"]) if in_row else 0
        out_n = int(out_row["n"]) if out_row else 0
        # Per-position talent value = avg transfer_points * headcount. This is
        # the QUALITY dimension (not just bodies): a position can be net-negative
        # on count but net-positive on talent if the incoming pieces are rated
        # higher than the departures. Serves the "who actually improved / where
        # are the hidden holes" fan question (research 2026-05-25).
        in_pts = (float(in_row["avg_points"] or 0) * in_n) if in_row else 0.0
        out_pts = (float(out_row["avg_points"] or 0) * out_n) if out_row else 0.0
        net_talent = in_pts - out_pts
        rows.append({
            "position": pos,
            "incoming_n": in_n,
            "incoming_avg_rating": float(in_row["avg_rating"] or 0) if in_row else 0.0,
            "incoming_avg_points": float(in_row["avg_points"] or 0) if in_row else 0.0,
            "outgoing_n": out_n,
            "outgoing_avg_rating": float(out_row["avg_rating"] or 0) if out_row else 0.0,
            "outgoing_avg_points": float(out_row["avg_points"] or 0) if out_row else 0.0,
            "net_n": in_n - out_n,
            "net_talent": net_talent,
        })

    total_in = sum(r["incoming_n"] for r in rows)
    total_out = sum(r["outgoing_n"] for r in rows)
    sample_n = total_in + total_out
    confidence = "high" if sample_n >= 12 else ("medium" if sample_n >= 4 else "low")

    # Identify the biggest position upgrade + biggest hole by talent value.
    rows_with_talent = [r for r in rows if abs(r["net_talent"]) > 0.001]
    biggest_upgrade = max(rows_with_talent, key=lambda r: r["net_talent"], default=None)
    biggest_hole = min(rows_with_talent, key=lambda r: r["net_talent"], default=None)

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
            "net_talent_total": sum(r["net_talent"] for r in rows),
            "biggest_upgrade_pos": biggest_upgrade["position"] if biggest_upgrade and biggest_upgrade["net_talent"] > 0 else None,
            "biggest_upgrade_val": biggest_upgrade["net_talent"] if biggest_upgrade and biggest_upgrade["net_talent"] > 0 else 0.0,
            "biggest_hole_pos": biggest_hole["position"] if biggest_hole and biggest_hole["net_talent"] < 0 else None,
            "biggest_hole_val": biggest_hole["net_talent"] if biggest_hole and biggest_hole["net_talent"] < 0 else 0.0,
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

    # Team-relevance gate: only show the bubble wall on a team page if that
    # team is actually in the at-large field (top-25 resume). For a 6-7 G5
    # team it would otherwise render a dead "not in the field" card.
    if anchor_team_id is not None and not any(r["team_id"] == anchor_team_id for r in raw):
        return _empty_result(query_id, source_tables, "team not in the CFP at-large field")

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
# Query: Draft Pipeline Conveyor
# ---------------------------------------------------------------------------
#
# "Who did the draft take, and who's left to replace them?" — pairs the most
# recent NFL-draft departures by position (draft capital lost) with the
# portal + returning replacements at those positions. Serves the #10 fan
# interest (draft aftermath -> replacement pipeline) from the 2026-05-25
# research. Forward-looking: it frames last cycle's losses against the
# 2026 roster answer.
#
# Draft capital weight: round-weighted (R1=7 ... R7=1) so losing a 1st-rounder
# at a position counts far more than a 7th-rounder.


def query_draft_pipeline_conveyor(
    db: Any,
    *,
    slug: str,
    season_year: int,
    week_number: int | None = None,  # ignored
) -> dict[str, Any]:
    query_id = "draft_pipeline_conveyor_v1"
    source_tables = ["player_nfl_draft", "transfer_entries", "teams"]

    team_id = _team_id_for_slug(db, slug)
    if team_id is None:
        return _empty_result(query_id, source_tables, "team slug not found")

    # Use the most recent draft year available for this team — but only if it's
    # RECENT (this or last cycle). A page viewed in 2026 shouldn't headline a
    # team's lone 2021 pick as "2026 reload" content; suppress stale/old draft
    # classes so the card stays relevant to the current offseason.
    dy_row = _query_one(
        db,
        "SELECT MAX(draft_year) AS dy FROM player_nfl_draft WHERE college_team_id = ?",
        (team_id,),
    )
    draft_year = (dy_row or {}).get("dy")
    if not draft_year:
        return _empty_result(query_id, source_tables, "no NFL draft picks for this program")
    # Latest draft in the DB overall = the current cycle; require this team's
    # most recent class to be within 1 year of it.
    latest_overall = (_query_one(db, "SELECT MAX(draft_year) AS dy FROM player_nfl_draft", ()) or {}).get("dy") or draft_year
    if draft_year < latest_overall - 1:
        return _empty_result(query_id, source_tables, "no recent NFL draft departures")

    picks = _query_all(
        db,
        """
        SELECT position, round, pick, overall, player_name
        FROM player_nfl_draft
        WHERE college_team_id = :tid AND draft_year = :dy
        ORDER BY overall ASC
        """,
        {"tid": team_id, "dy": draft_year},
    )
    if not picks:
        return _empty_result(query_id, source_tables, "no draft picks for latest cycle")

    def _pos_bucket(p: str | None) -> str:
        # Handles both short codes (LB, OT) and CFBD full names (LINEBACKER,
        # OFFENSIVE TACKLE) — draft rows carry full names, transfer rows carry
        # codes, so both must normalize to the same bucket or the
        # replacement-match logic silently fails.
        s = (p or "").strip().upper()
        if s in ("QB", "QUARTERBACK"): return "QB"
        if s in ("RB", "HB", "FB", "RUNNING BACK", "TAILBACK", "FULLBACK"): return "RB"
        if s in ("WR", "FL", "WIDE RECEIVER", "RECEIVER", "FLANKER"): return "WR"
        if s in ("TE", "TIGHT END"): return "TE"
        if s in ("OT", "OG", "C", "OL", "G", "T", "IOL", "OFFENSIVE TACKLE",
                 "OFFENSIVE GUARD", "OFFENSIVE LINE", "OFFENSIVE LINEMAN",
                 "CENTER", "GUARD", "TACKLE"): return "OL"
        if s in ("DT", "DE", "DL", "NT", "EDGE", "DEFENSIVE TACKLE",
                 "DEFENSIVE END", "DEFENSIVE LINE", "DEFENSIVE LINEMAN",
                 "NOSE TACKLE", "EDGE RUSHER"): return "DL"
        if s in ("LB", "ILB", "OLB", "MLB", "LINEBACKER"): return "LB"
        if s in ("CB", "S", "DB", "FS", "SS", "CORNERBACK", "SAFETY",
                 "DEFENSIVE BACK", "CORNER"): return "DB"
        if s in ("K", "P", "LS", "KICKER", "PUNTER", "PLACEKICKER",
                 "LONG SNAPPER"): return "ST"
        return s or "ATH"

    def _round_weight(rd: int | None) -> int:
        try:
            return max(1, 8 - int(rd))
        except (TypeError, ValueError):
            return 1

    # Draft capital lost by position bucket.
    by_pos: dict[str, dict] = {}
    for pk in picks:
        bucket = _pos_bucket(pk.get("position"))
        d = by_pos.setdefault(bucket, {"position": bucket, "picks": 0, "capital": 0, "top_pick": None, "names": []})
        d["picks"] += 1
        d["capital"] += _round_weight(pk.get("round"))
        if d["top_pick"] is None or (pk.get("overall") or 999) < d["top_pick"]:
            d["top_pick"] = pk.get("overall")
        if len(d["names"]) < 3:
            d["names"].append(pk.get("player_name") or "")

    # Portal replacements at those positions (incoming transfers, latest cycle).
    portal_year = _query_one(
        db,
        "SELECT MAX(season_year) AS sy FROM transfer_entries WHERE to_team_id = ?",
        (team_id,),
    )
    psy = (portal_year or {}).get("sy")
    incoming: dict[str, int] = {}
    if psy:
        for r in _query_all(
            db,
            """
            SELECT position, COUNT(*) AS n FROM transfer_entries
            WHERE to_team_id = :tid AND season_year = :sy AND position IS NOT NULL
            GROUP BY position
            """,
            {"tid": team_id, "sy": psy},
        ):
            incoming[_pos_bucket(r.get("position"))] = incoming.get(_pos_bucket(r.get("position")), 0) + int(r["n"])

    rows = sorted(by_pos.values(), key=lambda d: d["capital"], reverse=True)
    for d in rows:
        d["incoming_replacements"] = incoming.get(d["position"], 0)
        d["first_rounder"] = bool(d["top_pick"] and d["top_pick"] <= 32)

    total_picks = sum(d["picks"] for d in rows)
    total_capital = sum(d["capital"] for d in rows)
    # Position with most capital lost AND no portal replacement = the exposed hole.
    exposed = next(
        (d for d in rows if d["incoming_replacements"] == 0 and d["capital"] >= 4),
        None,
    )

    return {
        "query_id": query_id,
        "source_tables": source_tables,
        "rows": rows,
        "summary_stats": {
            "team_id": team_id,
            "draft_year": draft_year,
            "portal_year": psy,
            "total_picks": total_picks,
            "total_capital": total_capital,
            "top_position": rows[0]["position"] if rows else None,
            "top_position_picks": rows[0]["picks"] if rows else 0,
            "top_position_first_rounder": rows[0]["first_rounder"] if rows else False,
            "exposed_position": exposed["position"] if exposed else None,
        },
        "sample_n": total_picks,
        "confidence": "high" if total_picks >= 5 else ("medium" if total_picks >= 2 else "low"),
        "limitations": [] if total_picks >= 2 else ["small draft class"],
        "as_of_utc": _now_utc(),
    }


# ---------------------------------------------------------------------------
# Query: Delta DNA (team swing signature)
# ---------------------------------------------------------------------------
#
# Per-game power_delta series for a team's most recent completed season — the
# program's "swing signature." High volatility = boom/bust; low volatility +
# positive mean = steadily-built; low volatility + negative mean = fake-stable.
# Exploits the proprietary team_rating_deltas (per-game power change) that
# ESPN/On3 don't expose. Retrospective data (2024) but framed as a
# built-to-leap-vs-fake-stable read into 2026.


def query_delta_dna(
    db: Any,
    *,
    slug: str,
    season_year: int,
    week_number: int | None = None,
) -> dict[str, Any]:
    query_id = "delta_dna_v1"
    source_tables = ["team_rating_deltas", "games", "teams"]

    team_id = _team_id_for_slug(db, slug)
    if team_id is None:
        return _empty_result(query_id, source_tables, "team slug not found")

    rows_raw = _query_all(
        db,
        """
        SELECT d.power_delta, d.offense_delta, d.defense_delta, d.resume_delta,
               g.week
        FROM team_rating_deltas d
        JOIN games g ON g.game_id = d.game_id
        WHERE d.team_id = :tid AND g.season_year = :sy
          AND d.power_delta IS NOT NULL
        ORDER BY g.week ASC
        """,
        {"tid": team_id, "sy": season_year},
    )
    if len(rows_raw) < 3:
        return _empty_result(query_id, source_tables, "not enough game deltas for a signature")

    deltas = [float(r["power_delta"] or 0) for r in rows_raw]
    n = len(deltas)
    mean = sum(deltas) / n
    var = sum((d - mean) ** 2 for d in deltas) / n
    std = var ** 0.5
    biggest_up = max(deltas)
    biggest_down = min(deltas)

    rows = [
        {
            "week": r["week"],
            "power_delta": float(r["power_delta"] or 0),
            "offense_delta": float(r["offense_delta"] or 0),
            "defense_delta": float(r["defense_delta"] or 0),
        }
        for r in rows_raw
    ]

    # Archetype from mean + volatility.
    if std >= 1.2 and mean > 0.2:
        archetype = "boom-built"
    elif std >= 1.2:
        archetype = "boom-bust"
    elif mean > 0.2:
        archetype = "steadily-built"
    elif mean < -0.2:
        archetype = "fake-stable"
    else:
        archetype = "flat-line"

    return {
        "query_id": query_id,
        "source_tables": source_tables,
        "rows": rows,
        "summary_stats": {
            "team_id": team_id,
            "season_year": season_year,
            "games": n,
            "mean_delta": mean,
            "volatility": std,
            "biggest_up": biggest_up,
            "biggest_down": biggest_down,
            "archetype": archetype,
        },
        "sample_n": n,
        "confidence": "high" if n >= 10 else "medium",
        "limitations": [],
        "as_of_utc": _now_utc(),
    }


# ---------------------------------------------------------------------------
# Query: Continuity Stress Test
# ---------------------------------------------------------------------------
#
# Returning-production stress bars weighting QB / OL / offense / defense, from
# returning_production. Richer than ESPN's single returning-production number:
# shows WHERE the continuity is and where the stress (turnover) sits. Forward
# preview data (2025 = the upcoming-season returning production).


def query_continuity_stress_test(
    db: Any,
    *,
    slug: str,
    season_year: int,
    week_number: int | None = None,  # ignored
) -> dict[str, Any]:
    query_id = "continuity_stress_test_v1"
    source_tables = ["returning_production", "teams"]

    team_id = _team_id_for_slug(db, slug)
    if team_id is None:
        return _empty_result(query_id, source_tables, "team slug not found")

    row = _query_one(
        db,
        """
        SELECT returning_total, returning_offense, returning_defense,
               returning_qb, returning_ol
        FROM returning_production
        WHERE team_id = :tid AND season_year = :sy
        LIMIT 1
        """,
        {"tid": team_id, "sy": season_year},
    )
    if not row:
        return _empty_result(query_id, source_tables, "no returning-production snapshot")

    def _pct(v):
        # Return None for missing data so the renderer can show "n/a" rather
        # than a misleading 0% bar (audit: North Texas O-line/Defense were NULL
        # and rendered as 0%, which reads as broken).
        if v is None:
            return None
        x = float(v)
        return x if 0 <= x <= 1 else (x / 100.0 if x > 1 else 0.0)

    # League averages for context.
    avg = _query_one(
        db,
        """
        SELECT AVG(returning_total) t, AVG(returning_offense) o,
               AVG(returning_defense) d, AVG(returning_qb) q, AVG(returning_ol) l
        FROM returning_production WHERE season_year = :sy
        """,
        {"sy": season_year},
    ) or {}

    bars = [
        {"key": "QB", "label": "QB room", "value": _pct(row.get("returning_qb")), "league_avg": _pct(avg.get("q"))},
        {"key": "OL", "label": "O-line", "value": _pct(row.get("returning_ol")), "league_avg": _pct(avg.get("l"))},
        {"key": "OFF", "label": "Offense", "value": _pct(row.get("returning_offense")), "league_avg": _pct(avg.get("o"))},
        {"key": "DEF", "label": "Defense", "value": _pct(row.get("returning_defense")), "league_avg": _pct(avg.get("d"))},
        {"key": "TOT", "label": "Overall", "value": _pct(row.get("returning_total")), "league_avg": _pct(avg.get("t"))},
    ]
    # Weakest link (biggest stress) = lowest returning vs league avg. Only
    # consider units that actually have data (value not None); a NULL unit is
    # "n/a", not a 0% stress point.
    scored = [b for b in bars if b["value"] is not None and b["league_avg"] is not None]
    stressed = min(scored, key=lambda b: b["value"] - b["league_avg"]) if scored else None
    anchored = max(scored, key=lambda b: b["value"] - b["league_avg"]) if scored else None

    if not scored:
        return _empty_result(query_id, source_tables, "no returning-production unit data")
    overall = _pct(row.get("returning_total"))
    return {
        "query_id": query_id,
        "source_tables": source_tables,
        "rows": bars,
        "summary_stats": {
            "team_id": team_id,
            "season_year": season_year,
            "stressed_key": stressed["key"] if stressed else None,
            "stressed_label": stressed["label"] if stressed else "",
            "stressed_value": stressed["value"] if stressed else None,
            "anchored_key": anchored["key"] if anchored else None,
            "anchored_label": anchored["label"] if anchored else "",
            "overall_value": overall if overall is not None else 0.0,
            "overall_avg": _pct(avg.get("t")) or 0.0,
        },
        "sample_n": 1,
        "confidence": "high",
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


# ---------------------------------------------------------------------------
# Query: Fan Mood Braid — the Phantom Delta (belief vs the model)
# ---------------------------------------------------------------------------
#
# The honest single-snapshot form (design-system 73 §2.4 / 77): where dense
# weekly belief history does not yet exist, render the latest full-cohort
# snapshot as a dumbbell. Belief = backometer_weekly.score; reality =
# power_ratings_weekly.power_rating. BOTH percentile-ranked within the SAME
# cohort (teams carrying both signals) so the gap is apples-to-apples. Every
# value is SQL-sourced; the renderer invents nothing.
# ---------------------------------------------------------------------------


def query_fan_mood_braid(
    db: Any,
    *,
    slug: str,
    season_year: int,
    week_number: int | None = None,
) -> dict[str, Any]:
    query_id = "fan_mood_braid_v1"
    source_tables = ["backometer_weekly", "power_ratings_weekly", "teams"]

    team_id = _team_id_for_slug(db, slug)
    if team_id is None:
        return _empty_result(query_id, source_tables, "team slug not found")

    # Latest broad belief snapshot week for the season.
    bw = _query_one(
        db,
        "SELECT MAX(week) AS w FROM backometer_weekly WHERE season_year = :sy",
        {"sy": season_year},
    )
    belief_week = (bw or {}).get("w")
    if belief_week is None:
        return _empty_result(query_id, source_tables, "no backometer snapshot for season")

    belief_rows = _query_all(
        db,
        """
        SELECT team_id, score, zone, delta_wow, sample_size, is_low_signal, is_offseason
        FROM backometer_weekly
        WHERE season_year = :sy AND week = :w AND score IS NOT NULL
        """,
        {"sy": season_year, "w": belief_week},
    )
    me_belief = next((r for r in belief_rows if r["team_id"] == team_id), None)
    if me_belief is None:
        return _empty_result(query_id, source_tables, "team has no belief snapshot this week")

    # Latest model snapshot week.
    pw = _query_one(
        db,
        "SELECT MAX(week) AS w FROM power_ratings_weekly WHERE season_year = :sy",
        {"sy": season_year},
    )
    power_week = (pw or {}).get("w")
    if power_week is None:
        return _empty_result(query_id, source_tables, "no power ratings for season")

    power_rows = _query_all(
        db,
        """
        SELECT team_id, power_rating
        FROM power_ratings_weekly
        WHERE season_year = :sy AND week = :w AND power_rating IS NOT NULL
        """,
        {"sy": season_year, "w": power_week},
    )
    power_by_team = {r["team_id"]: r["power_rating"] for r in power_rows}

    # Cohort = teams present in BOTH signals (fair, apples-to-apples ranking).
    belief_by_team = {
        r["team_id"]: r["score"] for r in belief_rows if r["team_id"] in power_by_team
    }
    if team_id not in belief_by_team:
        return _empty_result(query_id, source_tables, "team missing a model rating this week")
    n = len(belief_by_team)
    if n < 8:
        return _empty_result(query_id, source_tables, "cohort too small for a fair percentile")

    belief_scores = sorted(belief_by_team.values())
    power_scores = sorted(power_by_team[t] for t in belief_by_team)

    def pctile(sorted_vals: list[float], v: float) -> int:
        i = sum(1 for x in sorted_vals if x <= v)
        return int(round(100.0 * (i - 0.5) / len(sorted_vals)))

    my_belief = belief_by_team[team_id]
    my_power = power_by_team[team_id]
    belief_pctile = pctile(belief_scores, my_belief)
    model_pctile = pctile(power_scores, my_power)

    # Ranks within the cohort (1 = highest).
    belief_rank = 1 + sum(1 for v in belief_by_team.values() if v > my_belief)
    model_rank = 1 + sum(1 for t, v in power_by_team.items() if t in belief_by_team and v > my_power)
    spots = model_rank - belief_rank  # + => fans rank the team higher than the model does
    phantom_delta = belief_pctile - model_pctile  # signed percentile-point gap
    # Cohort context (answers "is this gap big?"): rank the subject's
    # belief-minus-model gap against every team's. 1 = widest fans-over-model.
    all_gaps = [pctile(belief_scores, belief_by_team[t]) - pctile(power_scores, power_by_team[t])
                for t in belief_by_team]
    gap_rank = 1 + sum(1 for g in all_gaps if g > phantom_delta)

    is_low = bool(me_belief.get("is_low_signal")) or (me_belief.get("sample_size") or 0) < 200
    # Belief honesty floor (design-system 73 §3): a thin or low-signal belief
    # reading cannot anchor a confident belief-vs-model claim. Suppress rather
    # than amplify offseason noise into a manufactured saga.
    if is_low:
        return _empty_result(
            query_id, source_tables,
            "belief below honesty floor (low-signal or thin sample) — suppressed",
        )
    # Offseason gate (owner decision 2026-06-13): the offseason belief snapshot
    # is compressed (mood regresses toward the mean), so cross-team percentile
    # amplifies small gaps into false drama. Suppress the belief family until
    # in-season, where belief diverges meaningfully and volume rises. The gate
    # is self-clearing: when is_offseason flips to 0, the family activates.
    is_offseason = bool(me_belief.get("is_offseason"))
    if is_offseason:
        return _empty_result(
            query_id, source_tables,
            "offseason belief distribution too compressed for a fair percentile — activates in-season",
        )
    confidence = "high" if (me_belief.get("sample_size") or 0) >= 300 else "medium"

    name = _team_name_for_id(db, team_id)
    zone = (me_belief.get("zone") or "").replace("_", " ")

    # Full cohort points for the diagonal scatter (belief x, model y). Each
    # team is a faint field dot; the subject + the two extremes (most delusion =
    # widest fans-over-model, most paranoia = widest model-over-fans) get labels.
    points = []
    for t in belief_by_team:
        bpt = pctile(belief_scores, belief_by_team[t])
        mpt = pctile(power_scores, power_by_team[t])
        points.append({"team_id": t, "belief": bpt, "model": mpt, "gap": bpt - mpt})
    delusion_x = max(points, key=lambda p: p["gap"])["team_id"]
    paranoia_x = min(points, key=lambda p: p["gap"])["team_id"]
    label_ids = {team_id, delusion_x, paranoia_x}
    name_rows = _query_all(
        db,
        f"SELECT team_id, canonical_name FROM teams WHERE team_id IN ({','.join(str(int(i)) for i in label_ids)})",
    )
    names = {r["team_id"]: r["canonical_name"] for r in name_rows}
    rows = []
    for p in points:
        rows.append({
            "belief": p["belief"], "model": p["model"], "gap": p["gap"],
            "subject": p["team_id"] == team_id,
            "label": names.get(p["team_id"]) if p["team_id"] in label_ids else None,
        })
    return {
        "query_id": query_id,
        "source_tables": source_tables,
        "rows": rows,
        "summary_stats": {
            "team_id": team_id,
            "team_name": name,
            "season_year": season_year,
            "belief_week": belief_week,
            "power_week": power_week,
            "n_cohort": n,
            "is_offseason": is_offseason,
            "belief_pctile": belief_pctile,
            "model_pctile": model_pctile,
            "phantom_delta": phantom_delta,
            "net_movement": phantom_delta,
            "gap_rank": gap_rank,
            "spots": spots,
            "zone": zone,
            "delta_wow": me_belief.get("delta_wow"),
            "sample_size": me_belief.get("sample_size"),
        },
        "sample_n": int(me_belief.get("sample_size") or 0),
        "confidence": confidence,
        "limitations": (["offseason snapshot — low fan-discourse volume"] if is_low else []),
        "as_of_utc": _now_utc(),
    }


def _season_is_offseason(db: Any, season_year: int) -> bool:
    """True when the latest belief snapshot for the season is offseason-flagged.
    Shared offseason gate for the belief family (owner decision 2026-06-13)."""
    r = _query_one(
        db,
        "SELECT is_offseason FROM backometer_weekly WHERE season_year = :sy ORDER BY week DESC LIMIT 1",
        {"sy": season_year},
    )
    return bool(r and r.get("is_offseason"))


# ---------------------------------------------------------------------------
# Query: Home/Away Mind — the Belonging Gap (fan vs national net sentiment)
# ---------------------------------------------------------------------------
#
# The proprietary audience-tagged moat: how a fanbase feels vs how the nation
# talks. belonging_gap = fan_net - national_net (positive = grievance fuel,
# "the world doubts us, we don't"; negative = "even we've cooled"). Suppressed
# in the offseason (thin national discourse) — activates in-season.
# ---------------------------------------------------------------------------


def query_home_away_mind(
    db: Any,
    *,
    slug: str,
    season_year: int,
    week_number: int | None = None,
) -> dict[str, Any]:
    query_id = "home_away_mind_v1"
    source_tables = ["team_week_conversation_features", "teams"]

    team_id = _team_id_for_slug(db, slug)
    if team_id is None:
        return _empty_result(query_id, source_tables, "team slug not found")
    if _season_is_offseason(db, season_year):
        return _empty_result(query_id, source_tables,
                             "offseason fan-vs-national discourse too thin — activates in-season")

    rows = _query_all(
        db,
        """
        SELECT week, audience_bucket, mention_count, unique_author_count, net_sentiment_score
        FROM team_week_conversation_features
        WHERE season_year = :sy AND team_id = :tid
        ORDER BY week DESC
        """,
        {"sy": season_year, "tid": team_id},
    )
    by_week: dict[int, dict[str, dict]] = {}
    for r in rows:
        by_week.setdefault(r["week"], {})[r["audience_bucket"]] = r

    target = None
    for wk in sorted(by_week, reverse=True):
        d = by_week[wk]
        if "fan" in d and "national" in d:
            target = (wk, d)
            break
    if target is None:
        return _empty_result(query_id, source_tables, "no week with both fan and national discourse")

    wk, d = target
    fan, nat = d["fan"], d["national"]
    MIN_MENTIONS = 40
    if (fan.get("mention_count") or 0) < MIN_MENTIONS or (nat.get("mention_count") or 0) < MIN_MENTIONS:
        return _empty_result(query_id, source_tables, "fan/national volume below floor")

    fan_net = float(fan.get("net_sentiment_score") or 0.0)
    nat_net = float(nat.get("net_sentiment_score") or 0.0)
    gap = fan_net - nat_net
    nf = int(fan.get("mention_count") or 0)
    nn = int(nat.get("mention_count") or 0)
    confidence = "high" if min(nf, nn) >= 150 else "medium"
    name = _team_name_for_id(db, team_id)

    return {
        "query_id": query_id,
        "source_tables": source_tables,
        "rows": [
            {"key": "fan", "label": "Your fanbase", "net": fan_net, "n": nf},
            {"key": "national", "label": "The nation", "net": nat_net, "n": nn},
        ],
        "summary_stats": {
            "team_id": team_id,
            "team_name": name,
            "season_year": season_year,
            "week": wk,
            "fan_net": fan_net,
            "national_net": nat_net,
            "belonging_gap": gap,
            "net_movement": gap,
            "n_fan": nf,
            "n_national": nn,
        },
        "sample_n": nf,
        "confidence": confidence,
        "limitations": [],
        "as_of_utc": _now_utc(),
    }


# ---------------------------------------------------------------------------
# Query: Perception vs the Tape — player hype vs production (quadrant scatter)
# ---------------------------------------------------------------------------
#
# The player Phantom Delta and the Noir perception-vs-tape moat. X = hype
# (2025 mention volume) percentile; Y = production (prior-season wEPA)
# percentile — both ranked within the player's POSITION cohort so the axes are
# fair. The quadrant (median crosshairs) is the finding: producing-but-unhyped
# (underrated) vs hyped-but-unproven (overhyped). All values SQL-sourced.
# ---------------------------------------------------------------------------


def _resolve_player_id(db: Any, slug: str | None, player_id: int | None) -> int | None:
    if player_id is not None:
        return player_id
    if not slug:
        return None
    tail = slug.rsplit("-", 1)[-1]
    if tail.isdigit():
        return int(tail)
    r = _query_one(db, "SELECT player_id FROM players WHERE LOWER(full_name) = LOWER(:n)",
                   {"n": slug.replace("-", " ")})
    return r["player_id"] if r else None


def query_perception_vs_tape(
    db: Any,
    *,
    slug: str | None = None,
    player_id: int | None = None,
    season_year: int,
    week_number: int | None = None,
) -> dict[str, Any]:
    query_id = "perception_vs_tape_v1"
    source_tables = ["player_week_conversation_features", "player_value_metrics", "players"]

    pid = _resolve_player_id(db, slug, player_id)
    if pid is None:
        return _empty_result(query_id, source_tables, "player not resolved")
    prow = _query_one(db, "SELECT full_name, position FROM players WHERE player_id = :p", {"p": pid})
    if not prow:
        return _empty_result(query_id, source_tables, "player not found")
    position = (prow.get("position") or "").strip()
    metric = "wepa_passing" if position.upper() == "QB" else "wepa_rushing"
    prod_season = season_year - 1  # the completed-season "tape"

    rows = _query_all(
        db,
        """
        WITH hype AS (
            SELECT player_id, SUM(mention_count) AS m
            FROM player_week_conversation_features
            WHERE season_year = :sy GROUP BY player_id
        ),
        prod AS (
            SELECT player_id, metric_value AS v
            FROM player_value_metrics
            WHERE season_year = :psy AND metric_name = :mn
        )
        SELECT pl.player_id, pl.full_name, h.m AS hype, pr.v AS prod
        FROM hype h
        JOIN prod pr ON pr.player_id = h.player_id
        JOIN players pl ON pl.player_id = h.player_id
        WHERE pl.position = :pos AND h.m > 0
        """,
        {"sy": season_year, "psy": prod_season, "mn": metric, "pos": position},
    )
    if len(rows) < 12:
        return _empty_result(query_id, source_tables, "position cohort too small for a fair scatter")
    me = next((r for r in rows if r["player_id"] == pid), None)
    if me is None:
        return _empty_result(query_id, source_tables, "player missing hype or production")

    hype_sorted = sorted(r["hype"] for r in rows)
    prod_sorted = sorted(r["prod"] for r in rows)
    n = len(rows)

    def pct(sorted_vals: list[float], v: float) -> int:
        i = sum(1 for x in sorted_vals if x <= v)
        return int(round(100.0 * (i - 0.5) / len(sorted_vals)))

    # Peer labels: the most-hyped and the most-productive (besides the subject).
    peer_ids = {max(rows, key=lambda r: r["hype"])["player_id"],
                max(rows, key=lambda r: r["prod"])["player_id"]} - {pid}

    points = [{
        "x": pct(hype_sorted, r["hype"]),
        "y": pct(prod_sorted, r["prod"]),
        "name": r["full_name"],
        "subject": r["player_id"] == pid,
        "peer": r["player_id"] in peer_ids,
    } for r in rows]

    hx, py_ = pct(hype_sorted, me["hype"]), pct(prod_sorted, me["prod"])
    quadrant = ("PROVEN" if hx >= 50 and py_ >= 50 else
                "UNDERRATED" if hx < 50 and py_ >= 50 else
                "OVERHYPED" if hx >= 50 and py_ < 50 else "OFF THE RADAR")

    return {
        "query_id": query_id,
        "source_tables": source_tables,
        "rows": points,
        "summary_stats": {
            "player_id": pid,
            "player_name": prow["full_name"],
            "position": position,
            "metric": metric,
            "season_year": season_year,
            "prod_season": prod_season,
            "n_cohort": n,
            "hype_pctile": hx,
            "prod_pctile": py_,
            "quadrant": quadrant,
            "net_movement": py_ - hx,  # +production over hype = underrated
            "hype_mentions": int(me["hype"]),
        },
        "sample_n": int(me["hype"]),
        "confidence": "high" if n >= 25 else "medium",
        "limitations": [],
        "as_of_utc": _now_utc(),
    }
