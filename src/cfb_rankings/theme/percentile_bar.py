"""Percentile Bar Component (World-Class CFB Stats Display)

Renders percentile bars with red→grey→blue diverging scale.
Communicates rank/percentile context alongside raw values.

Spec: docs/research/cfb-stats-conformance-spec.md §3.2
Chart Vocabulary: docs/design-system/31-chart-vocabulary.md
"""

from __future__ import annotations

import html as _html
from dataclasses import dataclass
from enum import Enum


# =============================================================================
# COLOR SCALE DEFINITIONS
# =============================================================================

class PercentileBand(Enum):
    """Confidence bands for percentile display."""
    HIGH = "high"      # 75th-100th percentile → elite (blue)
    MEDIUM = "medium"  # 25th-75th percentile → good (green)
    LOW = "low"        # 0th-25th percentile → low (red)


def percentile_band(value: int) -> PercentileBand:
    """Get the percentile band for a given value (0-100)."""
    if value >= 75:
        return PercentileBand.HIGH
    if value >= 25:
        return PercentileBand.MEDIUM
    return PercentileBand.LOW


def percentile_tier_class(value: int) -> str:
    """Get the CSS tier class for card-based layout.

    Returns:
        'elite' for 75th+, 'good' for 25-74th, 'low' for <25th.
    """
    if value >= 75:
        return "elite"
    if value >= 25:
        return "good"
    return "low"


def percentile_fill_color(value: int) -> str:
    """Get the CSS fill color for a percentile value."""
    band = percentile_band(value)
    colors = {
        PercentileBand.HIGH: "#3b82f6",   # blue
        PercentileBand.MEDIUM: "#9ca3af",  # grey
        PercentileBand.LOW: "#ef4444",     # red
    }
    return colors[band]


def percentile_data_attr(value: int) -> str:
    """Get the data-pct-* attribute for CSS styling."""
    band = percentile_band(value)
    return f"data-pct-{band.value}=\"true\""


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SampleSize:
    """Sample size information for confidence signaling."""
    value: int
    label: str = ""  # e.g., "snaps", "games", "attempts"

    def confidence_level(self) -> PercentileBand:
        """Determine confidence level based on sample size."""
        # These thresholds are per-domain calibrated via confidence_calibration table
        if self.value >= 100:
            return PercentileBand.HIGH
        if self.value >= 30:
            return PercentileBand.MEDIUM
        return PercentileBand.LOW

    def __str__(self) -> str:
        """Format for display (e.g., '142 snaps', '8 games')."""
        if self.label:
            return f"{self.value} {self.label}"
        return str(self.value)


@dataclass
class PercentileBar:
    """A percentile bar displaying a player/team's relative standing."""
    label: str           # Stat label (e.g., "PASS YARDS/GAME")
    value: int           # Percentile value (0-100)
    raw_value: str       # Raw stat value for display (e.g., "287.3")
    peer_group: str      # Peer group label (e.g., "vs FBS QBs", "vs P4 teams")
    sample_size: SampleSize | None = None
    width: int = 200     # Bar width in pixels (max-width for responsive)
    rank: str | None = None  # Rank display (e.g., "92nd")


# =============================================================================
# RENDERER
# =============================================================================

class PercentileBarRenderer:
    """Renders percentile bars with proper color encoding and accessibility."""

    def __init__(self, bar: PercentileBar):
        self.bar = bar

    def render(self) -> str:
        """Render the complete percentile bar component."""
        safe_label = _html.escape(self.bar.label)
        safe_value = _html.escape(str(self.bar.value))
        safe_raw = _html.escape(self.bar.raw_value)
        safe_peer = _html.escape(self.bar.peer_group)

        # Calculate bar fill and position
        fill_pct = min(max(self.bar.value, 0), 100)
        band = percentile_band(self.bar.value)
        fill_color = percentile_fill_color(self.bar.value)
        band_attr = percentile_data_attr(self.bar.value)

        # Sample size chip (if provided)
        sample_chip = ""
        if self.bar.sample_size:
            sample_chip = self._render_sample_chip(self.bar.sample_size)

        return f"""<div class="wcfb-percentile-bar">
  <span class="wcfb-percentile-bar__label">{safe_label}</span>
  <div class="wcfb-percentile-bar__track">
    <div class="wcfb-percentile-bar__fill" style="width: {fill_pct}%;" {band_attr}></div>
    <span class="wcfb-percentile-bar__dot" style="left: {fill_pct}%;"></span>
  </div>
  <span class="wcfb-percentile-bar__value">{safe_raw}</span>
  <span class="wcfb-percentile-bar__peer">{safe_peer}</span>
  {sample_chip}
</div>"""

    def _render_sample_chip(self, sample: SampleSize) -> str:
        """Render the sample size confidence chip."""
        safe_text = _html.escape(str(sample))
        band = sample.confidence_level()
        return f'<span class="wcfb-confidence-chip wcfb-confidence-chip--{band.value}">{safe_text}</span>'


class PercentileCardRenderer:
    """Renders percentile cards with the refined card-based layout.

    Card design features:
    - Larger values (24px) for prominence
    - Tier-based rank badges (elite/good/low)
    - Gradient bars instead of tiny dots
    - Sample size shown once at header level, not per-row
    """

    def __init__(self, bar: PercentileBar):
        self.bar = bar

    def render(self) -> str:
        """Render the complete percentile card component."""
        safe_label = _html.escape(self.bar.label)
        safe_value = _html.escape(self.bar.raw_value)
        safe_rank = _html.escape(self.bar.rank or f"{self.bar.value}th")

        # Calculate tier class
        tier_class = percentile_tier_class(self.bar.value)
        fill_pct = min(max(self.bar.value, 0), 100)

        return f"""<div class="wcfb-percentile-card wcfb-percentile-card--{tier_class}">
  <div class="wcfb-percentile-card__main">
    <div class="wcfb-percentile-card__label">{safe_label}</div>
    <div class="wcfb-percentile-card__value">{safe_value}</div>
    <div class="wcfb-percentile-card__rank">{safe_rank}</div>
  </div>
  <div class="wcfb-percentile-card__bar">
    <div class="wcfb-percentile-card__track">
      <div class="wcfb-percentile-card__fill" style="width: {fill_pct}%;"></div>
    </div>
    <div class="wcfb-percentile-card__markers">
      <span>0</span><span>50</span><span>100</span>
    </div>
  </div>
</div>"""


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def render_percentile_bar(
    label: str,
    value: int,
    raw_value: str,
    peer_group: str = "vs FBS",
    sample_size: int | None = None,
    sample_label: str = "snaps",
) -> str:
    """Quick render of a percentile bar.

    Args:
        label: Stat label (e.g., "PASS YARDS/GAME")
        value: Percentile value (0-100)
        raw_value: Raw stat value for display (e.g., "287.3")
        peer_group: Peer group label (default: "vs FBS")
        sample_size: Sample size for confidence signaling
        sample_label: Sample size label (default: "snaps")

    Returns:
        HTML string for the percentile bar component.
    """
    bar = PercentileBar(
        label=label,
        value=value,
        raw_value=raw_value,
        peer_group=peer_group,
        sample_size=SampleSize(sample_size, sample_label) if sample_size else None,
    )
    renderer = PercentileBarRenderer(bar)
    return renderer.render()


def render_percentile_bars_grid(
    bars: list[PercentileBar],
    grid_id: str = "percentile-grid",
    use_cards: bool = True,
) -> str:
    """Render multiple percentile bars in a grid layout.

    Args:
        bars: List of PercentileBar objects
        grid_id: CSS ID for the grid container
        use_cards: If True, use card-based layout; if False, use legacy bars

    Useful for player fingerprint cards or team profiles.
    """
    rows = []
    renderer_cls = PercentileCardRenderer if use_cards else PercentileBarRenderer

    for bar in bars:
        renderer = renderer_cls(bar)
        rows.append(f"  {renderer.render()}")

    safe_id = _html.escape(grid_id)
    bars_html = "\n".join(rows)

    return f"""<div class="wcfb-percentile-grid" id="{safe_id}">
{bars_html}
</div>"""


def render_percentile_card(
    label: str,
    value: int,
    raw_value: str,
    rank: str | None = None,
) -> str:
    """Quick render of a single percentile card.

    Args:
        label: Stat label (e.g., "PASS YARDS/GAME")
        value: Percentile value (0-100)
        raw_value: Raw stat value for display (e.g., "287.3")
        rank: Rank display (e.g., "92nd", defaults to "{value}th")

    Returns:
        HTML string for the percentile card component.
    """
    bar = PercentileBar(
        label=label,
        value=value,
        raw_value=raw_value,
        peer_group="",  # Not shown in card layout
        rank=rank,
    )
    renderer = PercentileCardRenderer(bar)
    return renderer.render()


def render_sample_badge(
    sample_size: int,
    label: str = "attempts",
    confidence: str = "high",
) -> str:
    """Render a single sample size badge (shown once at header level).

    Args:
        sample_size: Sample size value (e.g., 401)
        label: Sample type label (e.g., "attempts", "snaps", "games")
        confidence: Confidence level ("high", "medium", "low")

    Returns:
        HTML string for the sample badge component.
    """
    safe_size = _html.escape(str(sample_size))
    safe_label = _html.escape(label)
    safe_conf = _html.escape(confidence)

    return f"""<div class="wcfb-sample-badge">
  <span class="wcfb-sample-badge__icon">●</span>
  <span class="wcfb-sample-badge__text">{safe_size} {safe_label} • {safe_conf.capitalize()} confidence</span>
</div>"""


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def calculate_percentile(
    value: float,
    min_value: float,
    max_value: float,
) -> int:
    """Calculate percentile (0-100) for a value within a range.

    Uses linear interpolation. Clamps to 0-100.
    """
    if max_value == min_value:
        return 50  # All values are the same

    pct = ((value - min_value) / (max_value - min_value)) * 100
    return int(round(max(0, min(100, pct))))


def format_raw_value(value: float, decimals: int = 1) -> str:
    """Format a raw value for display.

    Removes trailing zeros from decimal values.
    """
    formatted = f"{value:.{decimals}f}"
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted


__all__ = [
    # Enums
    "PercentileBand",
    # Functions
    "percentile_band",
    "percentile_fill_color",
    "percentile_data_attr",
    "percentile_tier_class",
    # Data structures
    "SampleSize",
    "PercentileBar",
    # Renderer
    "PercentileBarRenderer",
    "PercentileCardRenderer",
    # Factory functions
    "render_percentile_bar",
    "render_percentile_card",
    "render_percentile_bars_grid",
    "render_sample_badge",
    # Utilities
    "calculate_percentile",
    "format_raw_value",
]
