"""Pydantic models for Chronicle Visuals.

VisualSpec   = the Visual Director's contract: what to draw, from where, with which highlights.
VisualReceipt = provenance: source tables, sample size, confidence, as-of timestamp, limitations.
VisualResult = the realized artifact: SVG + receipt + score + cache metadata.

All values displayed in SVG must originate in queries.py outputs, never in LLM prose
(see CHRONICLE_QUALITY_PROPOSAL_v3.md §7 "Visual Director Contract").
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Enums — chart families and visual IDs
# ---------------------------------------------------------------------------


class ChartFamily(str, Enum):
    """Allowed chart families (Tier 0 + Tier 1 from v3 §4)."""

    # Tier 0 — existing locked vocabulary
    PERCENTILE_BAR = "percentile_bar"
    TRAJECTORY_SPARK = "trajectory_spark"
    BUMP = "bump"
    ANNOTATED_LINE = "annotated_line"
    SMALL_MULTIPLES = "small_multiples"
    HEATMAP = "heatmap"

    # Tier 1 — admitted under §4 admission tests
    ANNOTATED_SCATTER = "annotated_scatter"
    DOT_PLOT = "dot_plot"
    RANGE_PLOT = "range_plot"
    ARROW_PLOT = "arrow_plot"
    SLOPEGRAPH = "slopegraph"
    WATERFALL = "waterfall"
    SANKEY = "sankey"
    BRACKET_LATTICE = "bracket_lattice"
    FIELD_MAP = "field_map"
    HEXBIN = "hexbin"
    RIDGELINE = "ridgeline"
    BEESWARM = "beeswarm"
    TILE_MOSAIC = "tile_mosaic"
    TRAVEL_MAP = "travel_map"
    MINIMAL_NETWORK = "minimal_network"
    BRAID = "braid"  # bump + spark composite for Heisman Race Braid


class VisualId(str, Enum):
    """Registered visual modules (v3 §5). v1 ships the bottom 4."""

    STATEMENT_WIN_LADDER = "statement_win_ladder"
    RETURNING_PRODUCTION_XRAY = "returning_production_xray"
    HEISMAN_RACE_BRAID = "heisman_race_braid"
    ROSTER_REPLACEMENT_GRID = "roster_replacement_grid"
    # Deferred to subsequent waves:
    CFP_BUBBLE_WALL = "cfp_bubble_wall"
    MARKET_VS_MODEL_BOARD = "market_vs_model_board"
    PORTAL_FLOW_LEDGER = "portal_flow_ledger"
    TALENT_YIELD_CURVE = "talent_yield_curve"


class ConfidenceBand(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNSET = "unset"


class EntityKind(str, Enum):
    TEAM = "team"
    PLAYER = "player"
    CONFERENCE = "conference"
    RIVALRY = "rivalry"
    LEAGUE = "league"


# ---------------------------------------------------------------------------
# Spec — the Visual Director's output
# ---------------------------------------------------------------------------


class EntityScope(BaseModel):
    model_config = ConfigDict(extra="allow")

    slug: str
    season_year: int | None = None
    week_number: int | None = None
    team_id: int | None = None
    player_id: int | None = None


class Encoding(BaseModel):
    """What variable maps to what visual channel."""

    x: str | None = None
    y: str | None = None
    color: str | None = None
    size: str | None = None
    label: str | None = None
    group: str | None = None


class Annotation(BaseModel):
    """Editorial callout — values must be computed by the renderer, not the LLM."""

    target: str           # entity slug or row identifier
    text: str             # short caption (LLM-allowed)
    reason: str = ""      # why this gets called out (rule-engine output)


class VisualSpec(BaseModel):
    """Visual Director contract — see CHRONICLE_QUALITY_PROPOSAL_v3.md §7."""

    visual_id: VisualId
    chart_family: ChartFamily
    headline_finding: str = Field(..., max_length=200, description="One-sentence chart claim.")
    data_query_id: str
    entity_scope: EntityScope
    encodings: Encoding = Field(default_factory=Encoding)
    annotations: list[Annotation] = Field(default_factory=list)
    required_sources: list[str] = Field(default_factory=list)
    mobile_priority: str = "highlighted_entity_only"
    share_card: bool = True
    alt_text: str = ""


# ---------------------------------------------------------------------------
# Receipt — provenance + sample + confidence
# ---------------------------------------------------------------------------


class VisualReceipt(BaseModel):
    query_id: str
    source_tables: list[str] = Field(default_factory=list)
    as_of_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    sample_n: int = 0
    confidence: ConfidenceBand = ConfidenceBand.UNSET
    limitations: list[str] = Field(default_factory=list)
    citation_urls: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Quality score — weighted blend, see scorer.py
# ---------------------------------------------------------------------------


class VisualQualityScore(BaseModel):
    clarity: float = 0.0           # finding readable in one sentence?
    fan_relevance: float = 0.0     # answers a real fan question?
    data_depth: float = 0.0        # sample size + table depth
    novelty: float = 0.0           # different from neighbouring cards?
    mobile_legibility: float = 0.0 # 360px clean?
    screenshot_value: float = 0.0  # crops to share card?
    evidence_strength: float = 0.0 # provenance + confidence
    voice_fit: float = 0.0         # tone matches Chronicle?
    total: float = 0.0             # blended weighted sum


# ---------------------------------------------------------------------------
# Final result — what gets cached & rendered
# ---------------------------------------------------------------------------


class VisualResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    visual_cache_key: str
    spec: VisualSpec
    receipt: VisualReceipt
    score: VisualQualityScore
    svg_html: str
    share_asset_path: str | None = None
    visual_thesis_hash: str
    visual_data_fingerprint: str
    suppressed: bool = False
    suppression_reason: str = ""
    wall_clock_ms: int = 0
    rows: list[dict[str, Any]] = Field(default_factory=list)  # for table fallback
