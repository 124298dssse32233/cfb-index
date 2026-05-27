"""CFB Index Composite Score — Brief §4.1 hero cell #1.

The headline 0-100 score that anchors the QB Fingerprint hero. Brief
specifies an opponent-adjusted EPA+CPOE+VOR composite, but with no PBP
ingested we compute a box-rate composite: weighted mean of the Savant
percentiles produced by `compute_savant_bars`.

For QBs the weighting leans on per-play efficiency (YPA, CMP%) and
production (YDS, TD) more than counting stats. For other positions the
weighting is uniform across the same metric set — these are v1 scores
that get refined when PBP lands.

Returns a dict the hero renderer can drop straight into cell #1:
    {
      "score": 0-100 int,
      "tier": "elite" | "strong" | "solid" | "mid" | "below",
      "narrative": str,
      "n_metrics": int,
      "cohort_size": int (largest cohort observed),
    }
"""
from __future__ import annotations

from typing import Any

from .box_savant import compute_savant_bars


_QB_WEIGHTS = {
    "Yards / att":   1.4,
    "Completion %":  1.3,
    "Pass TDs":      1.2,
    "Pass yards":    1.1,
    "Interceptions": 1.0,
    "Rush yards":    0.6,
    "Rush TDs":      0.5,
    "Fumbles lost":  0.4,
}
_RB_WEIGHTS = {
    "Yards / carry": 1.4,
    "Rush yards":    1.3,
    "Rush TDs":      1.2,
    "Long run":      0.9,
    "Carries":       0.8,
    "Rec yards":     0.7,
    "Receptions":    0.6,
    "Fumbles lost":  0.4,
}
_WR_WEIGHTS = {
    "Rec yards":     1.4,
    "Rec TDs":       1.3,
    "Yards / catch": 1.1,
    "Receptions":    1.0,
    "Long catch":    0.8,
    "Rush yards":    0.5,
    "Rush TDs":      0.5,
    "Fumbles lost":  0.4,
}
_DEF_WEIGHTS = {
    "Sacks":            1.5,
    "Tackles for loss": 1.3,
    "Interceptions":    1.3,
    "Passes defended":  1.1,
    "Forced fumbles":   1.0,
    "QB hurries":       1.0,
    "Tackles":          0.8,
    "Solo tackles":     0.8,
}


def _weights_for_position(position: str) -> dict[str, float]:
    pos = (position or "").upper().strip()
    if pos in {"QB", "QUARTERBACK"}:
        return _QB_WEIGHTS
    if pos in {"RB", "TB", "FB", "HB"}:
        return _RB_WEIGHTS
    if pos in {"WR", "TE"}:
        return _WR_WEIGHTS
    if pos in {"CB", "S", "DB", "LB", "ILB", "OLB", "MLB",
               "DL", "DE", "DT", "NT", "EDGE"}:
        return _DEF_WEIGHTS
    return {}


def _ordinal(n: int) -> str:
    """1 → '1st', 22 → '22nd', 113 → '113th'."""
    if 10 <= (n % 100) <= 20:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _tier(score: float) -> tuple[str, str]:
    """Return (tier_key, label) for the composite score."""
    if score >= 90:
        return "elite", "Elite"
    if score >= 75:
        return "strong", "All-Conference"
    if score >= 55:
        return "solid", "Solid starter"
    if score >= 35:
        return "mid", "Mid-pack"
    return "below", "Below cohort"


def compute_cfb_index_score(
    db, player_id: int | None, season_year: int | None,
    position: str | None = None,
) -> dict[str, Any] | None:
    """Return composite score payload, or None if insufficient metrics."""
    if db is None or player_id is None or season_year is None:
        return None
    bars = compute_savant_bars(db, int(player_id), int(season_year), position or "")
    if len(bars) < 3:
        return None

    weights = _weights_for_position(position or "")
    total_w = 0.0
    weighted_sum = 0.0
    max_cohort = 0
    top_bars: list[tuple[str, float, float]] = []  # (label, pct, weight)
    for b in bars:
        w = weights.get(b["label"], 1.0)
        weighted_sum += b["percentile"] * w
        total_w += w
        max_cohort = max(max_cohort, int(b.get("cohort_size") or 0))
        top_bars.append((b["label"], b["percentile"], w))

    if total_w == 0:
        return None
    score = weighted_sum / total_w
    tier_key, tier_label = _tier(score)

    # Narrative: cite the top weighted contributor
    top_bars.sort(key=lambda t: t[1] * t[2], reverse=True)
    if top_bars:
        lead = top_bars[0]
        narrative = (
            f"{tier_label} in the position cohort. "
            f"Carried by {lead[0].lower()} at the {_ordinal(int(round(lead[1])))} percentile."
        )
    else:
        narrative = f"{tier_label} in the position cohort."

    return {
        "score": int(round(score)),
        "score_raw": score,
        "tier": tier_key,
        "tier_label": tier_label,
        "narrative": narrative,
        "n_metrics": len(bars),
        "cohort_size": max_cohort,
    }
