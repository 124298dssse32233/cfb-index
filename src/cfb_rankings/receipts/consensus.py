"""Historical consensus snapshots (Sprint 13 Phase 2).

Loads consensus markers used by the Surprise Index:
  * vegas_line              — game spread + total (existing `game_lines` table)
  * ap_poll / coaches_poll  — preseason + weekly rank (existing `official_rankings`)
  * sp_plus_projection      — power_rating analog (existing `power_ratings_weekly`)
  * corpus_aggregate        — % of corpus takes that aligned with claim
  * polymarket_market       — implied probabilities (existing `source_observations`
                              source_id='polymarket' rows)

Most adapters are read-from-existing-table → write-to-snapshot transformers.
We don't re-fetch from CFBD; the data is already locally ingested. New CFBD
calls are gated to filling gaps not already covered.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Iterable

from .runtime import db_conn, slugify


# ---------------------------------------------------------------------------
# Helper: idempotent upsert into historical_consensus_snapshots
# ---------------------------------------------------------------------------

_UPSERT_SQL = """
INSERT INTO historical_consensus_snapshots (
    snapshot_date, consensus_kind, entity_kind, entity_slug,
    metric, metric_value, metric_implied_probability, sample_size,
    season_year, week, source_provider, raw_payload_json
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (snapshot_date, consensus_kind, entity_kind, entity_slug, metric)
DO UPDATE SET
    metric_value = excluded.metric_value,
    metric_implied_probability = excluded.metric_implied_probability,
    sample_size = excluded.sample_size,
    season_year = excluded.season_year,
    week = excluded.week,
    source_provider = excluded.source_provider,
    raw_payload_json = excluded.raw_payload_json
"""


def _upsert(conn: sqlite3.Connection, rows: Iterable[tuple]) -> int:
    n = 0
    for row in rows:
        conn.execute(_UPSERT_SQL, row)
        n += 1
    return n


# ---------------------------------------------------------------------------
# Vegas-line snapshots from existing `game_lines`
# ---------------------------------------------------------------------------

def load_vegas_lines(season_year_min: int = 2014) -> int:
    """Project closing-line spreads + implied win-prob into snapshots."""
    inserted = 0
    with db_conn() as conn:
        cur = conn.execute("""
            SELECT gl.game_id, gl.spread_home_close, gl.total_close,
                   gl.moneyline_home_close, gl.moneyline_away_close,
                   gl.line_timestamp_utc, gl.provider,
                   g.season_year, g.week, g.start_time_utc,
                   g.home_team_id, g.away_team_id,
                   ht.slug AS home_slug, at.slug AS away_slug
              FROM game_lines gl
              JOIN games g ON g.game_id = gl.game_id
              LEFT JOIN teams ht ON ht.team_id = g.home_team_id
              LEFT JOIN teams at ON at.team_id = g.away_team_id
             WHERE g.season_year >= ?
               AND gl.spread_home_close IS NOT NULL
        """, (season_year_min,))
        rows = cur.fetchall()
        upserts: list[tuple] = []
        for r in rows:
            snap_date = (r["start_time_utc"] or "")[:10]
            if not snap_date:
                continue
            home_slug = r["home_slug"] or f"team-{r['home_team_id']}"
            away_slug = r["away_slug"] or f"team-{r['away_team_id']}"
            entity_slug = f"{away_slug}_at_{home_slug}"
            implied = _moneyline_to_prob(r["moneyline_home_close"]) if r["moneyline_home_close"] else None
            payload = {
                "spread_home_close": r["spread_home_close"],
                "total_close": r["total_close"],
                "moneyline_home_close": r["moneyline_home_close"],
                "moneyline_away_close": r["moneyline_away_close"],
                "provider": r["provider"],
                "game_id": r["game_id"],
            }
            upserts.append((
                snap_date, "vegas_line", "game", entity_slug,
                "game_spread", float(r["spread_home_close"]), implied, None,
                r["season_year"], r["week"], r["provider"] or "cfbd",
                json.dumps(payload),
            ))
            if r["total_close"] is not None:
                upserts.append((
                    snap_date, "vegas_line", "game", entity_slug,
                    "game_total", float(r["total_close"]), None, None,
                    r["season_year"], r["week"], r["provider"] or "cfbd",
                    json.dumps(payload),
                ))
        inserted = _upsert(conn, upserts)
        conn.commit()
    return inserted


def _moneyline_to_prob(ml: int | None) -> float | None:
    if ml is None:
        return None
    if ml < 0:
        return -ml / (-ml + 100)
    return 100 / (ml + 100)


# ---------------------------------------------------------------------------
# Poll snapshots from existing `official_rankings`
# ---------------------------------------------------------------------------

_POLL_KIND_MAP = {
    "AP Top 25": "ap_poll",
    "ap": "ap_poll",
    "Coaches Poll": "coaches_poll",
    "coaches": "coaches_poll",
}


def load_polls(season_year_min: int = 2015) -> int:
    """Snapshot AP + Coaches preseason and weekly ranks."""
    inserted = 0
    with db_conn() as conn:
        cur = conn.execute("""
            SELECT orw.team_id, orw.season_year, orw.week,
                   orw.ranking_system, orw.region, orw.rank_value, orw.rating_value,
                   t.slug AS team_slug
              FROM official_rankings orw
              LEFT JOIN teams t ON t.team_id = orw.team_id
             WHERE orw.season_year >= ?
               AND orw.rank_value IS NOT NULL
        """, (season_year_min,))
        rows = cur.fetchall()
        upserts: list[tuple] = []
        for r in rows:
            consensus_kind = _POLL_KIND_MAP.get(
                r["ranking_system"] or "",
                _POLL_KIND_MAP.get((r["ranking_system"] or "").lower(), None),
            )
            if not consensus_kind:
                continue
            snap_date = _week_to_date(r["season_year"], r["week"])
            slug = r["team_slug"] or f"team-{r['team_id']}"
            metric = "preseason_rank" if r["week"] in (0, None) else "weekly_rank"
            upserts.append((
                snap_date, consensus_kind, "team", slug,
                metric, float(r["rank_value"]), None, None,
                r["season_year"], r["week"], "cfbd",
                json.dumps({"rating_value": r["rating_value"]}),
            ))
        inserted = _upsert(conn, upserts)
        conn.commit()
    return inserted


def _week_to_date(season_year: int, week: int | None) -> str:
    """Convert season-year + week to a representative date.

    Week 0 / None → ~Aug 25 (preseason). Week N → Aug 25 + (N-1)*7 days.
    Good enough for snapshot date keys.
    """
    base = date(season_year, 8, 25)
    if week is None or week == 0:
        return base.isoformat()
    return (base + timedelta(days=(week - 1) * 7)).isoformat()


# ---------------------------------------------------------------------------
# SP+ projection snapshots from existing `power_ratings_weekly`
# ---------------------------------------------------------------------------

def load_sp_plus(season_year_min: int = 2015) -> int:
    inserted = 0
    with db_conn() as conn:
        cur = conn.execute("""
            SELECT prw.team_id, prw.season_year, prw.week, prw.power_rating,
                   prw.offense_rating, prw.defense_rating, t.slug AS team_slug
              FROM power_ratings_weekly prw
              LEFT JOIN teams t ON t.team_id = prw.team_id
             WHERE prw.season_year >= ?
               AND prw.power_rating IS NOT NULL
        """, (season_year_min,))
        rows = cur.fetchall()
        upserts: list[tuple] = []
        for r in rows:
            slug = r["team_slug"] or f"team-{r['team_id']}"
            snap_date = _week_to_date(r["season_year"], r["week"])
            upserts.append((
                snap_date, "sp_plus_projection", "team", slug,
                "power_rating", float(r["power_rating"]), None, None,
                r["season_year"], r["week"], "internal",
                json.dumps({
                    "offense_rating": r["offense_rating"],
                    "defense_rating": r["defense_rating"],
                }),
            ))
        inserted = _upsert(conn, upserts)
        conn.commit()
    return inserted


# ---------------------------------------------------------------------------
# Polymarket snapshots from existing source_observations
# ---------------------------------------------------------------------------

def load_polymarket() -> int:
    inserted = 0
    with db_conn() as conn:
        cur = conn.execute("""
            SELECT entity_id, entity_label, observed_at_utc, metric, value_numeric,
                   raw_payload_json
              FROM source_observations
             WHERE source_id = 'polymarket'
               AND value_numeric IS NOT NULL
        """)
        rows = cur.fetchall()
        upserts: list[tuple] = []
        for r in rows:
            snap_date = (r["observed_at_utc"] or "")[:10]
            if not snap_date:
                continue
            slug = slugify(r["entity_label"] or r["entity_id"] or "unknown")
            upserts.append((
                snap_date, "polymarket_market", "team", slug,
                r["metric"] or "implied_prob",
                float(r["value_numeric"]),
                None, None, None, None, "polymarket", r["raw_payload_json"],
            ))
        inserted = _upsert(conn, upserts)
        conn.commit()
    return inserted


# ---------------------------------------------------------------------------
# Corpus aggregate: for each (season, week, team), what % of takes were
# bullish vs bearish? Approximated from team_conversation_daily aggregates
# (mean_sentiment_score) which the fan-intel pipeline already maintains.
# ---------------------------------------------------------------------------

def load_corpus_aggregate(season_year_min: int = 2024) -> int:
    """Snapshot corpus sentiment per team-week as an aggregate marker."""
    inserted = 0
    with db_conn() as conn:
        cur = conn.execute("""
            SELECT tcd.team_id, tcd.as_of_date, tcd.season_year, tcd.week,
                   tcd.mean_sentiment_score, tcd.net_sentiment_score,
                   tcd.mention_count, t.slug AS team_slug
              FROM team_conversation_daily tcd
              LEFT JOIN teams t ON t.team_id = tcd.team_id
             WHERE tcd.season_year >= ?
        """, (season_year_min,))
        rows = cur.fetchall()
        upserts: list[tuple] = []
        for r in rows:
            slug = r["team_slug"] or f"team-{r['team_id']}"
            snap_date = (r["as_of_date"] or "")[:10] or _week_to_date(
                r["season_year"], r["week"]
            )
            implied = _sentiment_to_implied(r["mean_sentiment_score"])
            upserts.append((
                snap_date, "corpus_aggregate", "team", slug,
                "sentiment_alignment_pct",
                float(r["mean_sentiment_score"] or 0.0),
                implied, int(r["mention_count"] or 0),
                r["season_year"], r["week"], "internal",
                json.dumps({"net_sentiment": r["net_sentiment_score"]}),
            ))
        inserted = _upsert(conn, upserts)
        conn.commit()
    return inserted


def _sentiment_to_implied(score: float | None) -> float | None:
    """Map [-1, +1] sentiment to [0, 1] alignment probability proxy."""
    if score is None:
        return None
    return max(0.0, min(1.0, (score + 1) / 2))


# ---------------------------------------------------------------------------
# Lookup helpers (used by surprise.py)
# ---------------------------------------------------------------------------

def lookup_consensus(
    *,
    entity_slug: str,
    metric: str,
    on_or_before: str,
    consensus_kinds: tuple[str, ...] = (),
) -> dict[str, Any] | None:
    """Find the most recent snapshot at or before `on_or_before`."""
    with db_conn(read_only=True) as conn:
        if consensus_kinds:
            placeholders = ",".join("?" for _ in consensus_kinds)
            sql = f"""
                SELECT * FROM historical_consensus_snapshots
                 WHERE entity_slug = ? AND metric = ?
                   AND snapshot_date <= ?
                   AND consensus_kind IN ({placeholders})
                 ORDER BY snapshot_date DESC LIMIT 1
            """
            params: list[Any] = [entity_slug, metric, on_or_before, *consensus_kinds]
        else:
            sql = """
                SELECT * FROM historical_consensus_snapshots
                 WHERE entity_slug = ? AND metric = ?
                   AND snapshot_date <= ?
                 ORDER BY snapshot_date DESC LIMIT 1
            """
            params = [entity_slug, metric, on_or_before]
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def load_all() -> dict[str, int]:
    """Run every loader. Returns counts."""
    return {
        "vegas_lines": load_vegas_lines(),
        "polls": load_polls(),
        "sp_plus": load_sp_plus(),
        "polymarket": load_polymarket(),
        "corpus_aggregate": load_corpus_aggregate(),
    }
