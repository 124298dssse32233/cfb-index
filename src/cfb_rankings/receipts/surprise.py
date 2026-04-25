"""Surprise Index quantification (Sprint 13 Phase 4).

Composite 0..100 score per claim. Higher = more surprising at the time the
claim was made. Components per the sprint spec:

    1. vegas_implied_pct   — 100 - implied_probability_pct (35%)
    2. consensus_alignment — 100 - corpus_aggregate_alignment_pct (35%)
    3. magnitude_factor    — game-spread magnitude or rank-delta (20%)
    4. recency_adjustment  — claims further from outcome score higher (10%)

Computed once per claim; re-runnable when historical consensus refreshes.
"""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import date, datetime
from typing import Any

from .consensus import lookup_consensus
from .runtime import db_conn


WEIGHTS = {
    "vegas": 0.35,
    "consensus": 0.35,
    "magnitude": 0.20,
    "recency": 0.10,
}


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _component_vegas(claim: sqlite3.Row, entities: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """Look up the relevant Vegas marker on or before the claim's publish date."""
    pub_date = (claim["source_published_at"] or "")[:10]
    programs = entities.get("programs") or []
    if not programs or not pub_date:
        return 50.0, {"reason": "no_program_or_date", "score": 50.0}
    # We don't have season-win-total snapshots yet (Vegas only stores game lines).
    # Use SP+ rank-percentile as a proxy: a claim about a low-rated team doing
    # something extreme is surprising.
    snap = lookup_consensus(
        entity_slug=programs[0],
        metric="power_rating",
        on_or_before=pub_date,
        consensus_kinds=("sp_plus_projection",),
    )
    if not snap:
        return 50.0, {"reason": "no_snapshot", "score": 50.0}
    rating = snap["metric_value"]
    # Normalize: power_ratings on this site cluster ~ -25..+30. Map to 0..100
    # where 100 = lowest-rated. A pred. about a -20 team doing X = high surprise.
    score = max(0.0, min(100.0, (30.0 - rating) * (100.0 / 55.0)))
    return score, {
        "reason": "sp_plus_proxy",
        "rating": rating,
        "snapshot_date": snap["snapshot_date"],
        "score": round(score, 2),
    }


def _component_consensus(claim: sqlite3.Row, entities: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    pub_date = (claim["source_published_at"] or "")[:10]
    programs = entities.get("programs") or []
    if not programs or not pub_date:
        return 50.0, {"reason": "no_program_or_date", "score": 50.0}
    snap = lookup_consensus(
        entity_slug=programs[0],
        metric="sentiment_alignment_pct",
        on_or_before=pub_date,
        consensus_kinds=("corpus_aggregate",),
    )
    if not snap:
        return 50.0, {"reason": "no_corpus_snapshot", "score": 50.0}
    # If sentiment was very positive (alignment near 1.0) and the take was a
    # negative/down prediction, the take diverged → high surprise.
    # If sentiment was very negative and the take was bullish → high surprise.
    # Without claim-stance classification we use absolute deviation from neutral
    # as the divergence proxy.
    align = snap["metric_implied_probability"] or 0.5
    divergence_pct = abs(align - 0.5) * 200.0  # 0..100
    return divergence_pct, {
        "reason": "corpus_divergence_proxy",
        "alignment": align,
        "snapshot_date": snap["snapshot_date"],
        "score": round(divergence_pct, 2),
    }


def _component_magnitude(claim: sqlite3.Row, entities: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    text = (claim["claim_text"] or "").lower()
    score = 30.0  # default modest magnitude
    notes: dict[str, Any] = {"reason": "default", "score": score}
    # Keyword heuristics for magnitude language.
    if any(w in text for w in ("undefeated", "unbeaten", "perfect season", "shock", "stun", "stuns")):
        score = 90.0
        notes = {"reason": "magnitude_words", "kind": "extreme", "score": score}
    elif any(w in text for w in ("upset", "long shot", "long-shot", "dark horse", "sleeper")):
        score = 75.0
        notes = {"reason": "magnitude_words", "kind": "upset", "score": score}
    elif any(w in text for w in ("playoff", "natty", "title")):
        score = 60.0
        notes = {"reason": "magnitude_words", "kind": "title_bid", "score": score}
    return score, notes


def _component_recency(claim: sqlite3.Row) -> tuple[float, dict[str, Any]]:
    pub = _parse_date(claim["source_published_at"])
    end = _parse_date(claim["outcome_window_end"])
    if not pub or not end:
        return 50.0, {"reason": "missing_dates", "score": 50.0}
    days = max(0, (end - pub).days)
    # 0 days → 0; 365 days → 100 (saturating).
    score = min(100.0, days * (100.0 / 365.0))
    return score, {"reason": "days_ahead", "days": days, "score": round(score, 2)}


def compute(claim: sqlite3.Row) -> tuple[float, dict[str, Any]]:
    try:
        entities = json.loads(claim["entities_mentioned_json"] or "{}")
    except json.JSONDecodeError:
        entities = {}

    v, vd = _component_vegas(claim, entities)
    c, cd = _component_consensus(claim, entities)
    m, md = _component_magnitude(claim, entities)
    r, rd = _component_recency(claim)

    composite = (
        v * WEIGHTS["vegas"]
        + c * WEIGHTS["consensus"]
        + m * WEIGHTS["magnitude"]
        + r * WEIGHTS["recency"]
    )
    breakdown = {
        "weights": WEIGHTS,
        "vegas": vd,
        "consensus": cd,
        "magnitude": md,
        "recency": rd,
        "composite": round(composite, 2),
    }
    return round(composite, 2), breakdown


def compute_batch(*, only_unresolved: bool = False, only_unscored: bool = True) -> dict[str, int]:
    """Compute Surprise Index for matching claims."""
    where = []
    if only_unresolved:
        where.append("outcome_resolved = 0")
    if only_unscored:
        where.append("surprise_index IS NULL")
    sql = "SELECT * FROM predictive_claims"
    if where:
        sql += " WHERE " + " AND ".join(where)
    n_processed = 0
    n_updated = 0
    with db_conn() as conn:
        rows = conn.execute(sql).fetchall()
        for row in rows:
            n_processed += 1
            score, breakdown = compute(row)
            conn.execute(
                "UPDATE predictive_claims SET surprise_index = ?, "
                "surprise_index_components_json = ? WHERE id = ?",
                (score, json.dumps(breakdown, sort_keys=True), row["id"]),
            )
            n_updated += 1
        conn.commit()
    return {"processed": n_processed, "updated": n_updated}
