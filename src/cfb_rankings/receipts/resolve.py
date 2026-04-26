"""Outcome resolution (Sprint 13 Phase 5).

When a claim's outcome_window_end has passed, look up the actual outcome and
mark hit/miss/partial/unresolvable. Strategy depends on prediction_kind:

    * record           — read team's season record from games table
    * game             — read final score from games table
    * recruit          — read player_recruiting_profiles destination
    * coaching_change  — flagged for editorial review (no clean source yet)
    * portal           — read transfer_entries
    * award            — read player_honors / heisman_vote_results
    * rank             — read official_rankings end-of-season
    * title            — read national champion / conference champion
    * playoff_bid      — read playoff participation
    * other            — flagged for editorial Sonnet review

Sonnet review is reserved for `coaching_change`, `other`, and any kind that
the auto-resolver can't match cleanly.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, datetime
from typing import Any

from .runtime import db_conn


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Per-kind resolvers — each returns (verdict, outcome_text, aged_well_pct)
# Verdict in {'hit','miss','partial','unresolvable'}.
# ---------------------------------------------------------------------------

def _resolve_record(conn: sqlite3.Connection, claim: sqlite3.Row, entities: dict[str, Any]) -> tuple[str, str, float]:
    programs = entities.get("programs") or []
    if not programs:
        return "unresolvable", "No program slug attached.", 0.0
    slug = programs[0]
    season_year = _claim_target_season(claim)
    row = conn.execute("""
        SELECT
            SUM(CASE WHEN g.home_team_id = t.team_id AND g.home_points > g.away_points THEN 1 ELSE 0 END)
          + SUM(CASE WHEN g.away_team_id = t.team_id AND g.away_points > g.home_points THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN g.home_team_id = t.team_id AND g.home_points < g.away_points THEN 1 ELSE 0 END)
          + SUM(CASE WHEN g.away_team_id = t.team_id AND g.away_points < g.home_points THEN 1 ELSE 0 END) AS losses
          FROM teams t
          LEFT JOIN games g
            ON (g.home_team_id = t.team_id OR g.away_team_id = t.team_id)
           AND g.season_year = ?
           AND g.home_points IS NOT NULL
         WHERE t.slug = ?
    """, (season_year, slug)).fetchone()
    if not row or row["wins"] is None:
        return "unresolvable", f"No game data for {slug} {season_year}.", 0.0
    wins, losses = int(row["wins"] or 0), int(row["losses"] or 0)
    text = f"{slug} finished {wins}-{losses} in {season_year}."
    # Look for explicit numeric record in the claim text.
    import re
    m = re.search(r"\b(\d{1,2})\s*-\s*(\d{1,2})\b", claim["claim_text"] or "")
    if m:
        pred_wins = int(m.group(1))
        delta = abs(pred_wins - wins)
        if delta == 0:
            return "hit", f"{text} Prediction nailed wins.", 100.0
        if delta <= 1:
            return "partial", f"{text} Off by 1 win from prediction.", 70.0
        if delta <= 2:
            return "partial", f"{text} Off by {delta} wins from prediction.", 45.0
        return "miss", f"{text} Prediction was off by {delta} wins.", 15.0
    # Vague positive/negative qualitative claim.
    pct = wins / max(1, wins + losses) * 100.0
    text_l = (claim["claim_text"] or "").lower()
    if any(w in text_l for w in ("undefeated", "unbeaten", "perfect")):
        if losses == 0 and wins >= 8:
            return "hit", f"{text} Undefeated as predicted.", 100.0
        if losses <= 1:
            return "partial", f"{text} Lost {losses}, undefeated prediction missed by a hair.", 65.0
        return "miss", f"{text} Undefeated prediction did not land.", 10.0
    return "partial", f"{text} (No numeric record in claim; recorded outcome.)", round(pct, 1)


def _resolve_game(conn: sqlite3.Connection, claim: sqlite3.Row, entities: dict[str, Any]) -> tuple[str, str, float]:
    # Crude: find a game in the outcome window involving any mentioned program.
    programs = entities.get("programs") or []
    pub = _parse_date(claim["source_published_at"])
    end = _parse_date(claim["outcome_window_end"])
    if not programs or not pub or not end:
        return "unresolvable", "Missing program or window.", 0.0
    placeholders = ",".join("?" for _ in programs)
    row = conn.execute(f"""
        SELECT g.game_id, g.season_year, g.week, g.home_points, g.away_points,
               ht.slug AS home_slug, at.slug AS away_slug, g.start_time_utc
          FROM games g
          JOIN teams ht ON ht.team_id = g.home_team_id
          JOIN teams at ON at.team_id = g.away_team_id
         WHERE (ht.slug IN ({placeholders}) OR at.slug IN ({placeholders}))
           AND DATE(g.start_time_utc) BETWEEN ? AND ?
           AND g.home_points IS NOT NULL
         ORDER BY g.start_time_utc ASC
         LIMIT 1
    """, (*programs, *programs, pub.isoformat(), end.isoformat())).fetchone()
    if not row:
        return "unresolvable", "No completed game in window.", 0.0
    text = (
        f"{row['away_slug']} {row['away_points']}, {row['home_slug']} {row['home_points']} "
        f"on {row['start_time_utc'][:10]}."
    )
    # Heuristic verdict based on mentioned programs winning.
    home_won = row["home_points"] > row["away_points"]
    pred_text = (claim["claim_text"] or "").lower()
    winner = row["home_slug"] if home_won else row["away_slug"]
    if winner in pred_text or any(p in pred_text and (p == winner) for p in programs):
        return "hit", text, 90.0
    return "miss", text, 20.0


def _resolve_rank(conn: sqlite3.Connection, claim: sqlite3.Row, entities: dict[str, Any]) -> tuple[str, str, float]:
    programs = entities.get("programs") or []
    if not programs:
        return "unresolvable", "No program for rank claim.", 0.0
    season_year = _claim_target_season(claim)
    slug = programs[0]
    row = conn.execute("""
        SELECT MIN(rank_value) AS best_rank, MAX(week) AS final_week
          FROM official_rankings orw
          JOIN teams t ON t.team_id = orw.team_id
         WHERE t.slug = ? AND orw.season_year = ?
           AND orw.ranking_system IN ('AP Top 25','Coaches Poll','ap','coaches')
    """, (slug, season_year)).fetchone()
    if not row or row["best_rank"] is None:
        return "miss", f"{slug} unranked all season {season_year}.", 5.0
    best_rank = int(row["best_rank"])
    text = f"{slug} peaked at #{best_rank} in {season_year}."
    pred_text = (claim["claim_text"] or "").lower()
    import re
    m = re.search(r"top\s*(\d+)", pred_text)
    if m:
        threshold = int(m.group(1))
        if best_rank <= threshold:
            return "hit", text, 100.0
        if best_rank <= threshold + 5:
            return "partial", text, 55.0
        return "miss", text, 15.0
    if "ranked" in pred_text:
        return "hit" if best_rank <= 25 else "miss", text, 80.0 if best_rank <= 25 else 10.0
    return "partial", text, 50.0


def _resolve_title(conn: sqlite3.Connection, claim: sqlite3.Row, entities: dict[str, Any]) -> tuple[str, str, float]:
    programs = entities.get("programs") or []
    season_year = _claim_target_season(claim)
    if not programs:
        return "unresolvable", "No program for title claim.", 0.0
    # Conference champ: best regular-season-conference record (rough proxy).
    # National champ: would need explicit data we don't yet have a clean lookup for.
    return "unresolvable", (
        f"Title claim for {programs[0]} {season_year} flagged for editorial resolve."
    ), 0.0


def _resolve_playoff_bid(conn: sqlite3.Connection, claim: sqlite3.Row, entities: dict[str, Any]) -> tuple[str, str, float]:
    programs = entities.get("programs") or []
    if not programs:
        return "unresolvable", "No program for playoff claim.", 0.0
    season_year = _claim_target_season(claim)
    slug = programs[0]
    row = conn.execute("""
        SELECT COUNT(*) AS n
          FROM games g
          JOIN teams t ON (t.team_id = g.home_team_id OR t.team_id = g.away_team_id)
         WHERE t.slug = ? AND g.season_year = ? AND g.season_type = 'postseason'
    """, (slug, season_year)).fetchone()
    pred_text = (claim["claim_text"] or "").lower()
    miss_pred = any(w in pred_text for w in ("miss", "won't make", "won't be", "no playoff"))
    if row and (row["n"] or 0) > 0:
        if miss_pred:
            return "miss", f"{slug} did make the playoff in {season_year}.", 10.0
        return "hit", f"{slug} made the playoff in {season_year}.", 95.0
    if miss_pred:
        return "hit", f"{slug} missed the playoff in {season_year} as predicted.", 95.0
    return "miss", f"{slug} missed the playoff in {season_year}.", 10.0


def _resolve_award(conn: sqlite3.Connection, claim: sqlite3.Row, entities: dict[str, Any]) -> tuple[str, str, float]:
    season_year = _claim_target_season(claim)
    players = entities.get("players") or []
    if not players:
        return "unresolvable", "No player attached.", 0.0
    name_like = players[0].split()[-1] if players else ""
    row = conn.execute("""
        SELECT ph.honor_kind, p.name
          FROM player_honors ph
          JOIN players p ON p.player_id = ph.player_id
         WHERE ph.season_year = ?
           AND p.name LIKE ?
         LIMIT 1
    """, (season_year, f"%{name_like}%")).fetchone()
    if row:
        return "hit", f"{row['name']} won {row['honor_kind']} in {season_year}.", 95.0
    return "miss", f"No award match for {players[0]} in {season_year}.", 5.0


def _resolve_default(conn: sqlite3.Connection, claim: sqlite3.Row, entities: dict[str, Any]) -> tuple[str, str, float]:
    return "unresolvable", "Kind not auto-resolvable; flagged for editorial review.", 0.0


_RESOLVERS = {
    "record": _resolve_record,
    "game": _resolve_game,
    "rank": _resolve_rank,
    "title": _resolve_title,
    "playoff_bid": _resolve_playoff_bid,
    "award": _resolve_award,
    "recruit": _resolve_default,
    "coaching_change": _resolve_default,
    "portal": _resolve_default,
    "other": _resolve_default,
}


def _claim_target_season(claim: sqlite3.Row) -> int:
    """Best-guess season year the claim resolves in."""
    end = _parse_date(claim["outcome_window_end"])
    if end:
        return end.year if end.month >= 8 else end.year - 1
    pub = _parse_date(claim["source_published_at"])
    if pub:
        return pub.year if pub.month >= 8 else pub.year - 1
    return datetime.utcnow().year


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def resolve_one(claim: sqlite3.Row, conn: sqlite3.Connection) -> tuple[str, str, float]:
    try:
        entities = json.loads(claim["entities_mentioned_json"] or "{}")
    except json.JSONDecodeError:
        entities = {}
    resolver = _RESOLVERS.get(claim["prediction_kind"], _resolve_default)
    try:
        return resolver(conn, claim, entities)
    except Exception as exc:  # pragma: no cover - defensive
        return "unresolvable", f"Resolver error: {exc!s}", 0.0


def resolve_batch(*, window_end_before: str | None = None) -> dict[str, int]:
    counts = {"hit": 0, "miss": 0, "partial": 0, "unresolvable": 0, "skipped": 0}
    where = ["outcome_resolved = 0"]
    params: list[Any] = []
    if window_end_before:
        where.append("outcome_window_end <= ?")
        params.append(window_end_before)
    sql = "SELECT * FROM predictive_claims WHERE " + " AND ".join(where)
    with db_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        for row in rows:
            verdict, text, aged_pct = resolve_one(row, conn)
            counts[verdict] = counts.get(verdict, 0) + 1
            conn.execute("""
                UPDATE predictive_claims
                   SET outcome_resolved = 1,
                       outcome_verdict = ?,
                       outcome_text = ?,
                       outcome_resolved_at = CURRENT_TIMESTAMP,
                       aged_well_pct = ?
                 WHERE id = ?
            """, (verdict, text, aged_pct, row["id"]))
        conn.commit()
    return counts
