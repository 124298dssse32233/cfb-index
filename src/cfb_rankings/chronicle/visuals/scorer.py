"""Visual quality scoring.

Weights recalibrated from v3 §13 based on Discover-phase findings:
the v3 proposal weighted novelty=0.15 / evidence=0.05 which is right for
editorial exploration but too loose for a production gate. We bias toward
provenance and mobile legibility, which the rest of the pipeline cannot
recover if they fail at render time.

Suppress below VISUAL_SUPPRESS_THRESHOLD = 0.62
Local-refine 0.62..0.78
Paid review 0.78+
"""
from __future__ import annotations

from .models import VisualQualityScore, VisualReceipt, VisualSpec, ConfidenceBand


# Weights sum to 1.0
WEIGHT_CLARITY = 0.18
WEIGHT_FAN_RELEVANCE = 0.18
WEIGHT_DATA_DEPTH = 0.14
WEIGHT_NOVELTY = 0.08
WEIGHT_MOBILE_LEGIBILITY = 0.12
WEIGHT_SCREENSHOT_VALUE = 0.12
WEIGHT_EVIDENCE_STRENGTH = 0.13
WEIGHT_VOICE_FIT = 0.05

VISUAL_SUPPRESS_THRESHOLD = 0.62
LOCAL_REFINE_THRESHOLD = 0.78


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def score_clarity(headline: str) -> float:
    """Approximation: a clean one-sentence finding is 60-140 chars, no semicolons."""
    n = len(headline.strip())
    if n == 0:
        return 0.0
    base = 0.5
    if 60 <= n <= 140:
        base = 0.95
    elif 40 <= n < 60:
        base = 0.8
    elif 140 < n <= 180:
        base = 0.75
    elif n > 180:
        base = 0.55
    # Penalty for run-on prose
    if headline.count(";") >= 2:
        base -= 0.1
    if "—" in headline or " - " in headline:  # double-clause hint
        base -= 0.05
    return _clamp(base)


def score_fan_relevance(spec: VisualSpec) -> float:
    """Rule-engine proxy: known high-impact modules get a relevance boost."""
    high_impact = {
        "statement_win_ladder",
        "heisman_race_braid",
        "cfp_bubble_wall",
        "market_vs_model_board",
        "portal_flow_ledger",
        "roster_replacement_grid",
        "draft_pipeline_conveyor",
    }
    medium_impact = {
        "returning_production_xray",
        "talent_yield_curve",
        "schedule_stress_map",
    }
    vid = spec.visual_id.value if hasattr(spec.visual_id, "value") else str(spec.visual_id)
    if vid in high_impact:
        return 0.92
    if vid in medium_impact:
        return 0.78
    return 0.62


def score_data_depth(receipt: VisualReceipt) -> float:
    """Sample size + source coverage proxy."""
    n = receipt.sample_n
    src_n = len(receipt.source_tables)
    # Sample component
    if n >= 50:
        sample = 1.0
    elif n >= 20:
        sample = 0.85
    elif n >= 8:
        sample = 0.7
    elif n >= 3:
        sample = 0.55
    else:
        sample = 0.3
    # Source component
    source = 0.6 + min(0.4, 0.1 * src_n)
    return _clamp(0.6 * sample + 0.4 * source)


def score_novelty(spec: VisualSpec, _prior_thesis_hashes: set[str] | None = None) -> float:
    """First-pass: assume new visual is novel; future passes can check anti-dup."""
    if _prior_thesis_hashes is None:
        return 0.75
    return 0.5  # if we know about duplicates, base falls


def score_mobile_legibility(spec: VisualSpec) -> float:
    """Heuristic: simpler families are easier to keep legible at 360px."""
    family = spec.chart_family.value if hasattr(spec.chart_family, "value") else str(spec.chart_family)
    family_legibility = {
        "dot_plot": 0.92,
        "range_plot": 0.9,
        "waterfall": 0.88,
        "tile_mosaic": 0.86,
        "annotated_scatter": 0.74,
        "braid": 0.7,
        "sankey": 0.55,
        "bracket_lattice": 0.6,
        "field_map": 0.5,
        "travel_map": 0.5,
    }
    base = family_legibility.get(family, 0.7)
    # Annotation density penalty
    if len(spec.annotations) > 5:
        base -= 0.1
    return _clamp(base)


def score_screenshot_value(spec: VisualSpec) -> float:
    """Visuals with an explicit share_card flag + concise headline screenshot well."""
    base = 0.7 if spec.share_card else 0.45
    if 60 <= len(spec.headline_finding) <= 140:
        base += 0.15
    return _clamp(base)


def score_evidence_strength(receipt: VisualReceipt) -> float:
    """Provenance + confidence band."""
    src_n = len(receipt.source_tables)
    confidence_weight = {
        ConfidenceBand.HIGH: 1.0,
        ConfidenceBand.MEDIUM: 0.75,
        ConfidenceBand.LOW: 0.45,
        ConfidenceBand.UNSET: 0.3,
    }
    src_component = 0.4 + min(0.5, 0.15 * src_n)
    return _clamp(0.5 * src_component + 0.5 * confidence_weight[receipt.confidence])


def score_voice_fit(headline: str) -> float:
    """Lightweight tone check: penalize obvious AI-isms."""
    lower = headline.lower()
    ai_isms = ("delve into", "in the realm of", "navigate the", "leverage", "synergy")
    penalty = sum(0.15 for phrase in ai_isms if phrase in lower)
    return _clamp(0.85 - penalty)


def score_visual(spec: VisualSpec, receipt: VisualReceipt) -> VisualQualityScore:
    """Compute weighted total quality score."""
    clarity = score_clarity(spec.headline_finding)
    fan_relevance = score_fan_relevance(spec)
    data_depth = score_data_depth(receipt)
    novelty = score_novelty(spec)
    mobile_legibility = score_mobile_legibility(spec)
    screenshot_value = score_screenshot_value(spec)
    evidence_strength = score_evidence_strength(receipt)
    voice_fit = score_voice_fit(spec.headline_finding)

    total = (
        WEIGHT_CLARITY * clarity
        + WEIGHT_FAN_RELEVANCE * fan_relevance
        + WEIGHT_DATA_DEPTH * data_depth
        + WEIGHT_NOVELTY * novelty
        + WEIGHT_MOBILE_LEGIBILITY * mobile_legibility
        + WEIGHT_SCREENSHOT_VALUE * screenshot_value
        + WEIGHT_EVIDENCE_STRENGTH * evidence_strength
        + WEIGHT_VOICE_FIT * voice_fit
    )

    return VisualQualityScore(
        clarity=clarity,
        fan_relevance=fan_relevance,
        data_depth=data_depth,
        novelty=novelty,
        mobile_legibility=mobile_legibility,
        screenshot_value=screenshot_value,
        evidence_strength=evidence_strength,
        voice_fit=voice_fit,
        total=_clamp(total),
    )
