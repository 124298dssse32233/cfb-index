"""Shared chart-card shell (WS-08, D-007).

The chart-vocabulary spec names a single component "all charts render through"
so the surrounding chrome stops drifting (today some charts carry a
source-receipt footer, some don't; some embed the source inside the SVG, some
omit it). This is that shell.

``render_chart_card`` wraps any chart SVG in a consistent ``<figure>``:
eyebrow → headline → lede, then the chart (with optional x/y axis labels and an
optional annotation-overlay layer), then a source-receipt ``<figcaption>``. It
is pure string composition — deterministic, data-free, unit-testable — and emits
no JS, so a carded chart still satisfies the WS-11 static-SVG-fallback bar.

The card does NOT draw the chart; callers pass a finished SVG string from one of
the renderers in this package (or an inline renderer pending centralisation).
The annotation overlay is an optional stacked layer for the simple case; pixel-
aligned callouts inside a chart's own viewBox stay the chart's job (see
``charts.render_annotation_overlay`` and its era-trajectory consumer).
"""
from __future__ import annotations

from html import escape

__all__ = ["render_chart_card", "CHART_CARD_CSS"]


def render_chart_card(
    chart_svg: str,
    *,
    headline: str | None = None,
    eyebrow: str | None = None,
    lede: str | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    source: str | None = None,
    annotation_svg: str | None = None,
    anchor: str | None = None,
    heading_level: int = 2,
) -> str:
    """Wrap ``chart_svg`` in the shared chart-card figure.

    Args:
        chart_svg: A finished, self-contained SVG string (the chart itself).
        headline: Card title (rendered as an ``<hN>``; ``heading_level`` sets N).
        eyebrow: Small uppercase kicker above the headline (e.g. chart type).
        lede: One-line dek under the headline.
        x_label / y_label: Axis labels. ``y_label`` reads bottom-to-top.
        source: Data attribution for the source-receipt footer (e.g.
            ``"CFB Index · transfer_entries"``). Rendered as ``Source: …``.
        annotation_svg: Optional overlay SVG stacked over the plot (simple case).
        anchor: Optional ``id`` for in-page nav links.
        heading_level: Heading tag level for the headline (clamped to 2..6).

    Returns:
        A ``<figure class="chart-card">`` HTML string, or ``""`` if no chart.
    """
    if not chart_svg or not chart_svg.strip():
        return ""

    level = max(2, min(6, int(heading_level)))

    head_bits: list[str] = []
    if eyebrow:
        head_bits.append(f'<p class="chart-card__eyebrow">{escape(eyebrow)}</p>')
    if headline:
        head_bits.append(
            f'<h{level} class="chart-card__headline">{escape(headline)}</h{level}>'
        )
    if lede:
        head_bits.append(f'<p class="chart-card__lede">{escape(lede)}</p>')
    header = (
        f'<header class="chart-card__head">{"".join(head_bits)}</header>'
        if head_bits
        else ""
    )

    overlay = (
        f'<div class="chart-card__overlay" aria-hidden="true">{annotation_svg}</div>'
        if annotation_svg and annotation_svg.strip()
        else ""
    )
    y_axis = (
        f'<span class="chart-card__ylabel">{escape(y_label)}</span>' if y_label else ""
    )
    x_axis = (
        f'<span class="chart-card__xlabel">{escape(x_label)}</span>' if x_label else ""
    )
    body = (
        '<div class="chart-card__body">'
        f"{y_axis}"
        f'<div class="chart-card__plot">{chart_svg}{overlay}</div>'
        f"{x_axis}"
        "</div>"
    )

    footer = (
        f'<figcaption class="chart-card__source">'
        f'<span class="chart-card__source-label">Source</span> {escape(source)}'
        f"</figcaption>"
        if source
        else ""
    )

    id_attr = f' id="{escape(anchor)}"' if anchor else ""
    return (
        f'<figure class="chart-card"{id_attr}>'
        f"{header}{body}{footer}"
        f"</figure>"
    )


# Light-page-portable defaults; host pages may override the CSS variables.
CHART_CARD_CSS = """
.chart-card { margin: 0 0 1.5rem; padding: 0; border: 0; }
.chart-card__head { margin-bottom: .6rem; }
.chart-card__eyebrow {
  margin: 0 0 .2rem; font-size: .68rem; letter-spacing: .14em;
  text-transform: uppercase; font-weight: 700;
  color: var(--chart-card-eyebrow, var(--fg-muted, #7a7a7a));
}
.chart-card__headline {
  margin: 0; font-size: 1.18rem; line-height: 1.2; font-weight: 700;
  color: var(--chart-card-fg, var(--fg, #1a1a1a));
}
.chart-card__lede {
  margin: .25rem 0 0; font-size: .9rem; line-height: 1.45;
  color: var(--chart-card-muted, var(--fg-secondary, #555));
}
.chart-card__body {
  display: grid; grid-template-columns: auto 1fr;
  grid-template-areas: "ylabel plot" ".  xlabel";
  align-items: center; gap: .35rem .5rem;
}
.chart-card__plot { grid-area: plot; position: relative; min-width: 0; }
.chart-card__plot > svg { max-width: 100%; height: auto; display: block; }
.chart-card__overlay { position: absolute; inset: 0; pointer-events: none; }
.chart-card__overlay > svg { width: 100%; height: 100%; display: block; }
.chart-card__ylabel {
  grid-area: ylabel; writing-mode: vertical-rl; transform: rotate(180deg);
  font-size: .68rem; letter-spacing: .1em; text-transform: uppercase;
  color: var(--chart-card-muted, var(--fg-muted, #7a7a7a)); white-space: nowrap;
}
.chart-card__xlabel {
  grid-area: xlabel; text-align: center;
  font-size: .68rem; letter-spacing: .1em; text-transform: uppercase;
  color: var(--chart-card-muted, var(--fg-muted, #7a7a7a));
}
.chart-card__source {
  margin-top: .5rem; font-size: .72rem; line-height: 1.4;
  color: var(--chart-card-muted, var(--fg-muted, #7a7a7a));
}
.chart-card__source-label {
  text-transform: uppercase; letter-spacing: .1em; font-weight: 700;
  margin-right: .35rem;
}
@media (max-width: 360px) {
  .chart-card__body { grid-template-columns: 1fr; grid-template-areas: "plot" "xlabel"; }
  .chart-card__ylabel { display: none; }
}
""".strip()
