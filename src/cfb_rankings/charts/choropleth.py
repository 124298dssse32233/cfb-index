"""US-state choropleth as a statebins tile-grid cartogram (WS-08, D-007).

Locked usage (per ``docs/design-system/31-chart-vocabulary.md``): use when
*geography is the point* — recruiting footprint, fan-density, regional
attention. Do NOT use for incidental geography.

Why a tile grid and not true state boundaries: the WS-11 running gate requires
legibility at 320px, where small states (RI, DE, DC) collapse to invisible
slivers on a geographic map. Uniform tiles stay readable at mobile width, keep
the SVG tiny (fits the per-page weight budget), and the single-hue sequential
ramp is colour-blind safe (no red/green encoding). Each state keeps its
approximate geographic position so the shape still reads as the United States.

Public API:
    render_state_choropleth(counts, *, title, caption, accent) -> str
    CHOROPLETH_CSS -> str
"""
from __future__ import annotations

from html import escape
from math import sqrt
from typing import Mapping


# Approximate geographic position of each state on an 8-row x 11-col grid
# (row 0 = north, col 0 = west). Mirrors the widely used "statebins" layout.
_GRID: dict[str, tuple[int, int]] = {
    "ME": (0, 10),
    "VT": (1, 9), "NH": (1, 10),
    "WA": (2, 0), "ID": (2, 1), "MT": (2, 2), "ND": (2, 3), "MN": (2, 4),
    "WI": (2, 5), "MI": (2, 6), "NY": (2, 8), "MA": (2, 9),
    "OR": (3, 0), "NV": (3, 1), "WY": (3, 2), "SD": (3, 3), "IA": (3, 4),
    "IL": (3, 5), "IN": (3, 6), "OH": (3, 7), "PA": (3, 8), "NJ": (3, 9),
    "CT": (3, 10),
    "CA": (4, 0), "UT": (4, 1), "CO": (4, 2), "NE": (4, 3), "MO": (4, 4),
    "KY": (4, 5), "WV": (4, 6), "VA": (4, 7), "MD": (4, 8), "DE": (4, 9),
    "RI": (4, 10),
    "AZ": (5, 1), "NM": (5, 2), "KS": (5, 3), "AR": (5, 4), "TN": (5, 5),
    "NC": (5, 6), "SC": (5, 7), "DC": (5, 8),
    "OK": (6, 3), "LA": (6, 4), "MS": (6, 5), "AL": (6, 6), "GA": (6, 7),
    "AK": (7, 0), "HI": (7, 1), "TX": (7, 3), "FL": (7, 8),
}

_ROWS = 8
_COLS = 11
_CELL = 30          # tile edge in user units
_GAP = 3
_STEP = _CELL + _GAP
_PAD = 4


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lerp(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * t)


def _fill(t: float, lo_rgb: tuple[int, int, int], hi_rgb: tuple[int, int, int]) -> str:
    r = _lerp(lo_rgb[0], hi_rgb[0], t)
    g = _lerp(lo_rgb[1], hi_rgb[1], t)
    b = _lerp(lo_rgb[2], hi_rgb[2], t)
    return f"#{r:02x}{g:02x}{b:02x}"


def render_state_choropleth(
    counts: Mapping[str, int],
    *,
    title: str | None = None,
    caption: str | None = None,
    accent: str = "#c9a24a",
    as_figure: bool = True,
) -> str:
    """Render a US statebins choropleth. ``counts`` maps 2-letter state -> value.

    Returns an empty string when there is nothing to map (no positive counts),
    so callers can treat it like every other optional chip.

    ``as_figure`` (default True) returns the self-contained ``<figure>`` with its
    own title/caption. Pass ``as_figure=False`` to get the bare svg + legend (no
    figure/title/caption) so the map can render through the shared
    ``render_chart_card`` shell without nesting figures — the card then owns the
    headline/lede/source-receipt.
    """
    norm: dict[str, int] = {}
    for code, n in counts.items():
        if not code:
            continue
        try:
            v = int(n)
        except (TypeError, ValueError):
            continue
        if v <= 0:
            continue
        norm[code.strip().upper()] = v

    if not norm:
        return ""

    peak = max(norm.values())
    lo_rgb = _hex_to_rgb("4a3c18")        # dim end of the gold ramp
    hi_rgb = _hex_to_rgb(accent.lstrip("#") if accent.startswith("#") else accent)

    width = _COLS * _STEP - _GAP + _PAD * 2
    height = _ROWS * _STEP - _GAP + _PAD * 2

    tiles: list[str] = []
    for code, (row, col) in _GRID.items():
        x = _PAD + col * _STEP
        y = _PAD + row * _STEP
        n = norm.get(code, 0)
        if n > 0:
            # sqrt spread so the home state doesn't wash everything else out
            t = sqrt(n / peak)
            fill = _fill(t, lo_rgb, hi_rgb)
            stroke = accent
            stroke_op = "0.55"
            label_op = "0.92" if t >= 0.45 else "0.7"
            label_fill = "#1b1b1b" if t >= 0.6 else "#e9e6dc"
            aria = f"{code}: {n}"
        else:
            fill = "rgba(255,255,255,0.03)"
            stroke = "rgba(255,255,255,0.10)"
            stroke_op = "1"
            label_op = "0.35"
            label_fill = "#9a958a"
            aria = f"{code}: 0"
        cx = x + _CELL / 2
        cy = y + _CELL / 2
        tiles.append(
            f'<g role="img" aria-label="{escape(aria)}">'
            f'<rect x="{x}" y="{y}" width="{_CELL}" height="{_CELL}" rx="4" '
            f'fill="{fill}" stroke="{stroke}" stroke-opacity="{stroke_op}" stroke-width="1"/>'
            f'<text x="{cx:.1f}" y="{cy + 3:.1f}" text-anchor="middle" '
            f'fill="{label_fill}" fill-opacity="{label_op}" '
            f'font-family="ui-monospace, monospace" font-size="9" font-weight="700">'
            f'{escape(code)}</text>'
            f'</g>'
        )

    title_html = (
        f'<figcaption class="choropleth__title">{escape(title)}</figcaption>'
        if title else ""
    )
    caption_html = (
        f'<p class="choropleth__caption">{escape(caption)}</p>' if caption else ""
    )
    # Legend: faint -> peak, with the peak value labelled.
    legend = (
        '<div class="choropleth__legend" aria-hidden="true">'
        '<span class="choropleth__legend-label">Fewer</span>'
        '<span class="choropleth__legend-ramp"></span>'
        f'<span class="choropleth__legend-label">More (peak {peak})</span>'
        '</div>'
    )

    svg = (
        f'<svg class="choropleth__svg" data-chart="choropleth" '
        f'viewBox="0 0 {width} {height}" '
        f'role="group" aria-label="Recruit counts by U.S. state" '
        f'preserveAspectRatio="xMidYMid meet">'
        f'{"".join(tiles)}'
        f'</svg>'
    )
    if not as_figure:
        # Bare svg + legend (no figure/title/caption) for the shared chart-card
        # shell — the card owns the headline/lede/source-receipt.
        return f'{svg}{legend}'

    return (
        f'<figure class="choropleth" data-chart="choropleth">'
        f'{title_html}'
        f'{svg}'
        f'{legend}'
        f'{caption_html}'
        f'</figure>'
    )


CHOROPLETH_CSS = """
/* Choropleth (statebins tile grid) — WS-08 */
.choropleth { margin: 0; }
.choropleth__title {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin-bottom: 8px;
}
.choropleth__svg {
  width: 100%;
  height: auto;
  max-width: 420px;
  display: block;
}
.choropleth__legend {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
.choropleth__legend-ramp {
  flex: 1;
  max-width: 160px;
  height: 8px;
  border-radius: 999px;
  background: linear-gradient(90deg, #4a3c18, var(--accent-primary, #c9a24a));
}
.choropleth__legend-label {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 10px;
  color: var(--fg-muted);
  white-space: nowrap;
}
.choropleth__caption {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 12px;
  font-style: italic;
  line-height: 1.4;
  color: var(--fg-secondary);
  margin: 8px 0 0 0;
  max-width: 56ch;
}
"""


__all__ = ["render_state_choropleth", "CHOROPLETH_CSS"]
