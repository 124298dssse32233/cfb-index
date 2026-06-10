"""Delusion Premium — fanbase belief vs betting-market title odds.

Two axes for the contender cohort (teams with a live championship market):
- BELIEF: the Backometer (fan optimism, 0-100).
- MARKET: implied 2027-title probability from Polymarket, parsed out of the
  source_observations raw_payload (outcomePrices[0] = the "Yes" price).

Both are percentile-ranked within the cohort; ``delusion_index = belief_pctl -
market_pctl`` (signed: positive = fans believe more than the smart money does
= delusion premium; negative = the market is higher on you than your own fans =
"sharp"/quietly backed). The raw belief score and market % are the evocative
display numbers; the index is the honest, scale-free ranking.

This is the offseason form. The December "Sharpest Fanbase" payoff layers
resolved outcomes on top of this weekly history — a separate future step.

CLI:
    python manage.py compute-delusion-premium --season YYYY
"""

from __future__ import annotations

import bisect
import json
import logging
import re
from typing import Any

from cfb_rankings.db import Database

logger = logging.getLogger(__name__)

DELUSION_BAND = 25.0   # |delusion_index| past this earns a verdict


def _implied_pct(payload: str | None) -> float | None:
    """Extract the market-implied 'Yes' probability (%) from a Polymarket row."""
    if not payload:
        return None
    try:
        j = json.loads(payload)
    except Exception:  # noqa: BLE001
        return None
    op = j.get("outcomePrices")
    if isinstance(op, str):
        try:
            op = json.loads(op)
        except Exception:  # noqa: BLE001
            return None
    if isinstance(op, list) and op:
        try:
            return float(op[0]) * 100.0
        except (TypeError, ValueError):
            return None
    return None


def _percentiles(values: dict[int, float]) -> dict[int, float]:
    n = len(values)
    if n == 0:
        return {}
    if n == 1:
        return {next(iter(values)): 100.0}
    ordered = sorted(values.values())
    return {k: round(100.0 * bisect.bisect_right(ordered, v) / n, 1) for k, v in values.items()}


def _verdict(index: float) -> str:
    if index >= DELUSION_BAND:
        return "delusional"
    if index <= -DELUSION_BAND:
        return "sharp"
    return "bullish"


def _fetch_market_odds(db: Database) -> list[dict[str, Any]]:
    """Latest Polymarket title-odds observation per team, mapped to team_id."""
    rows = db.query_all(
        """
        select entity_id, entity_label, observed_at_utc, raw_payload_json
        from source_observations
        where source_id = 'polymarket' and entity_type = 'polymarket_market'
        """
    )
    latest: dict[str, dict[str, Any]] = {}
    for r in rows:
        eid = str(r["entity_id"])
        if eid not in latest or str(r["observed_at_utc"]) > str(latest[eid]["observed_at_utc"]):
            latest[eid] = r

    out: list[dict[str, Any]] = []
    for r in latest.values():
        pct = _implied_pct(r.get("raw_payload_json"))
        if pct is None:
            continue
        # "Texas win 2027 CFP National Championship" -> "Texas"
        name = re.sub(r"\s+win\s+.*$", "", str(r.get("entity_label") or "")).strip()
        if not name:
            continue
        team = db.query_one(
            "select team_id, slug from teams where canonical_name = :n or short_name = :n limit 1",
            {"n": name},
        )
        if team is None:
            team = db.query_one(
                "select team_id, slug from teams where canonical_name like :p limit 1",
                {"p": name.split()[0] + "%"},
            )
        if team is None:
            logger.warning("delusion: unmapped market team %r", name)
            continue
        out.append(
            {
                "team_id": int(team["team_id"]),
                "slug": team["slug"],
                "name": name,
                "market_pct": round(pct, 1),
                "observed_at": r.get("observed_at_utc"),
            }
        )
    return out


def compute_delusion_premium(db: Database, *, season: int) -> dict[str, int]:
    """Compute delusion_premium_weekly for the contender cohort."""
    market = _fetch_market_odds(db)
    if len(market) < 3:
        logger.info("compute-delusion-premium: only %d market teams; skipped", len(market))
        return {"teams": 0}

    # Belief = latest Backometer score per team (used even if low-signal here,
    # flagged so the receipt can say so).
    belief: dict[int, dict[str, Any]] = {}
    for m in market:
        b = db.query_one(
            """
            select score, is_low_signal, week, week_start_date
            from backometer_weekly
            where team_id = :tid
            order by season_year desc, week desc limit 1
            """,
            {"tid": m["team_id"]},
        )
        if b is not None:
            belief[m["team_id"]] = b
    cohort = [m for m in market if m["team_id"] in belief]
    if len(cohort) < 3:
        logger.info("compute-delusion-premium: only %d teams with belief; skipped", len(cohort))
        return {"teams": 0}

    belief_vals = {m["team_id"]: float(belief[m["team_id"]]["score"]) for m in cohort}
    market_vals = {m["team_id"]: float(m["market_pct"]) for m in cohort}
    belief_pctl = _percentiles(belief_vals)
    market_pctl = _percentiles(market_vals)

    week_no = max((int(belief[m["team_id"]]["week"] or 0) for m in cohort), default=0)
    rows: list[dict[str, Any]] = []
    for m in cohort:
        tid = m["team_id"]
        b_score = float(belief[tid]["score"])
        index = round(belief_pctl[tid] - market_pctl[tid], 1)
        rows.append(
            {
                "team_id": tid,
                "season_year": season,
                "week": week_no,
                "week_start_date": belief[tid].get("week_start_date"),
                "belief_score": round(b_score, 1),
                "belief_low_signal": int(belief[tid].get("is_low_signal") or 0),
                "belief_pctl": belief_pctl[tid],
                "market_pct": m["market_pct"],
                "market_pctl": market_pctl[tid],
                "market_source": "polymarket",
                "market_observed_at": m.get("observed_at"),
                "delusion_index": index,
                "raw_gap": round(b_score - m["market_pct"], 1),
                "cohort_size": len(cohort),
                "verdict": _verdict(index),
            }
        )

    rows.sort(key=lambda r: -r["delusion_index"])
    for i, r in enumerate(rows, start=1):
        r["rank"] = i

    db.upsert_many(
        "delusion_premium_weekly",
        rows,
        conflict_columns=["team_id", "season_year", "week"],
        update_columns=[
            "week_start_date", "belief_score", "belief_low_signal", "belief_pctl",
            "market_pct", "market_pctl", "market_source", "market_observed_at",
            "delusion_index", "raw_gap", "cohort_size", "rank", "verdict",
        ],
    )
    logger.info("compute-delusion-premium: season=%d teams=%d", season, len(rows))
    return {"teams": len(rows)}


__all__ = ["compute_delusion_premium", "DELUSION_BAND"]
