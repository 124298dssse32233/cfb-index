"""Cohort Divergence Map — 2D scatter for The Room (S3.1 / §4 Bet #10).

Aggregates ``player_week_conversation_features`` per audience bucket
into (belief, intensity, mention_count) 3-tuples suitable for an SVG
scatter. Belief = net sentiment (-100..100). Intensity = normalized
mention count (0..100) relative to the player's own max bucket.

Sub-cohort breakdowns (own-team alumni vs students, per-rival, etc.)
need mention-author metadata we don't carry today; the fetcher falls
back cleanly to the 4-top-level cohort view per kickoff spec.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cfb_rankings.db import Database


# Display labels + colour hooks keyed on audience_bucket.
_BUCKET_LABELS: dict[str, str] = {
    "fan":      "Own fans",
    "rival":    "Rivals",
    "national": "National",
    "media":    "Media",
}
_BUCKET_ORDER: tuple[str, ...] = ("fan", "rival", "national", "media")


@dataclass(frozen=True)
class CohortDot:
    bucket: str
    label: str
    belief: float          # -100..100
    intensity: float       # 0..100
    mention_count: int
    top_quote: str | None
    sarcasm_risk: str | None


@dataclass(frozen=True)
class CohortDivergenceMap:
    applicable: bool
    awaiting_reason: str
    dots: list[CohortDot]
    max_mentions: int


def _safe_json_first_string(value: Any) -> str | None:
    if not value:
        return None
    try:
        import json
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError):
        return None
    if isinstance(parsed, dict):
        for k in ("text", "quote", "headline", "excerpt"):
            v = parsed.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    if isinstance(parsed, list) and parsed:
        first = parsed[0]
        if isinstance(first, dict):
            for k in ("text", "quote", "headline", "excerpt"):
                v = first.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
        if isinstance(first, str) and first.strip():
            return first.strip()
    return None


def compute_cohort_divergence(
    db: Database, player_id: int, season: int
) -> CohortDivergenceMap:
    """Aggregate per-bucket belief/intensity/mentions for the map."""
    rows = db.query_all(
        "SELECT audience_bucket, "
        "       SUM(mention_count)          AS mentions, "
        "       AVG(net_sentiment_score)    AS net, "
        "       AVG(attention_score)        AS att, "
        "       MAX(top_quote_json)         AS top_q, "
        "       MAX(sarcasm_risk)           AS sarcasm "
        "FROM player_week_conversation_features "
        "WHERE player_id = :pid AND season_year = :s "
        "GROUP BY audience_bucket",
        {"pid": player_id, "s": season},
    )
    if not rows:
        return CohortDivergenceMap(
            applicable=False,
            awaiting_reason=(
                "Cohort divergence reads how different fanbases talk about this "
                "player. Returns once weekly mentions clear the publish floor."
            ),
            dots=[],
            max_mentions=0,
        )
    by_bucket = {str(r["audience_bucket"] or "").strip().lower(): r for r in rows}
    # Hard cap at a max mention count to compute intensity against.
    max_mentions = max(
        (int(r.get("mentions") or 0) for r in rows), default=0
    )
    dots: list[CohortDot] = []
    for bucket in _BUCKET_ORDER:
        r = by_bucket.get(bucket)
        if r is None:
            continue
        mentions = int(r.get("mentions") or 0)
        if mentions == 0:
            continue
        net = r.get("net") or 0
        try:
            belief = max(-100.0, min(100.0, float(net) * 100.0))
        except (TypeError, ValueError):
            belief = 0.0
        intensity = (mentions / max_mentions * 100.0) if max_mentions > 0 else 0.0
        dots.append(
            CohortDot(
                bucket=bucket,
                label=_BUCKET_LABELS.get(bucket, bucket.title()),
                belief=round(belief, 1),
                intensity=round(intensity, 1),
                mention_count=mentions,
                top_quote=_safe_json_first_string(r.get("top_q")),
                sarcasm_risk=r.get("sarcasm") and str(r["sarcasm"]),
            )
        )
    if not dots:
        return CohortDivergenceMap(
            applicable=False,
            awaiting_reason=(
                "No qualifying bucket cleared the mention floor this season."
            ),
            dots=[],
            max_mentions=0,
        )
    return CohortDivergenceMap(
        applicable=True,
        awaiting_reason="",
        dots=dots,
        max_mentions=max_mentions,
    )
