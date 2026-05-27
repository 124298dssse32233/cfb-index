"""Stat-ribbon sparklines — Brief P0 #5 / Wave 12.

Generates 8-week trajectory sparklines for the top stat tiles on a
player page. Each sparkline is an inline SVG using the player-page
percentile color tokens.

The helper returns a dict mapping common stat-tile labels to their
SVG sparkline HTML. The legacy stat-ribbon renderer in reporting.py
looks up by label and injects when present.

Public API:
    build_stat_sparklines(db, player_id, season_year, position)
        -> dict[str, str]  # label_or_key -> svg_html
    SPARKLINE_CSS
"""
from __future__ import annotations

from html import escape
from typing import Any


SPARKLINE_CSS = """
/* Stat-ribbon sparklines */
.stat-spark {
  display: block;
  width: 100%;
  height: 24px;
  margin-top: 6px;
  overflow: visible;
}
.stat-spark__line {
  fill: none;
  stroke: var(--accolade-gold-base, #d1a23a);
  stroke-width: 1.5;
  vector-effect: non-scaling-stroke;
}
.stat-spark__fill {
  fill: var(--accolade-gold-base, #d1a23a);
  opacity: 0.12;
}
.stat-spark__dot {
  fill: var(--accolade-gold-base, #d1a23a);
  stroke: #15161a;
  stroke-width: 1.0;
}
.stat-spark__baseline {
  stroke: rgba(255,255,255,0.18);
  stroke-width: 1;
  stroke-dasharray: 2 2;
}
"""


# Map "headline_card label" → (category, stat_type)
# Matches the labels used by the legacy stat-profile cards.
_LABEL_TO_METRIC = {
    "Pass yards":     ("passing",   "YDS"),
    "Passing yards":  ("passing",   "YDS"),
    "Pass TDs":       ("passing",   "TD"),
    "Completion rate":("passing",   "PCT_CALC"),
    "Completion %":   ("passing",   "PCT_CALC"),
    "Yards/attempt":  ("passing",   "AVG"),
    "QBR":            ("passing",   "QBR"),
    "Rush yards":     ("rushing",   "YDS"),
    "Rush TDs":       ("rushing",   "TD"),
    "Yards/carry":    ("rushing",   "AVG"),
    "Carries":        ("rushing",   "CAR"),
    "Rec yards":      ("receiving", "YDS"),
    "Receiving yards":("receiving", "YDS"),
    "Receptions":     ("receiving", "REC"),
    "Yards/catch":    ("receiving", "AVG"),
    "Rec TDs":        ("receiving", "TD"),
    "Tackles":        ("defensive", "TOT"),
    "Sacks":          ("defensive", "SACKS"),
    "TFL":            ("defensive", "TFL"),
    "Passes defended":("defensive", "PD"),
}


def _fetch_weekly_series(
    db, player_id: int, season_year: int, category: str, stat_type: str,
) -> list[tuple[int, float]]:
    """Return [(week, value), ...] sorted by week ASC."""
    rows = db.query_all(
        """
        select week, stat_value_num, stat_value_text
          from player_game_stats
         where player_id = :pid
           and season_year = :s
           and category = :cat
           and stat_type = :stype
           and (stat_value_num is not null or stat_value_text is not null)
         order by week asc
        """,
        {"pid": player_id, "s": season_year, "cat": category, "stype": stat_type},
    )
    out: list[tuple[int, float]] = []
    for r in rows:
        wk = r.get("week")
        v = r.get("stat_value_num")
        if v is None:
            try:
                v = float(r.get("stat_value_text"))
            except (TypeError, ValueError):
                continue
        if wk is not None and v is not None:
            out.append((int(wk), float(v)))
    return out


def _fetch_completion_rate_series(
    db, player_id: int, season_year: int,
) -> list[tuple[int, float]]:
    """Completion percentage per game from C/ATT text."""
    rows = db.query_all(
        """
        select week, stat_value_text
          from player_game_stats
         where player_id = :pid
           and season_year = :s
           and category = 'passing'
           and stat_type = 'C/ATT'
         order by week asc
        """,
        {"pid": player_id, "s": season_year},
    )
    out: list[tuple[int, float]] = []
    for r in rows:
        wk = r.get("week")
        txt = (r.get("stat_value_text") or "").strip()
        if wk is None or "/" not in txt:
            continue
        try:
            c, a = txt.split("/")
            c, a = int(c), int(a)
            if a > 0:
                out.append((int(wk), 100.0 * c / a))
        except (TypeError, ValueError):
            continue
    return out


def _build_sparkline_svg(
    series: list[tuple[int, float]],
    width: int = 140, height: int = 24, baseline: float | None = None,
) -> str:
    """Return inline SVG for a sparkline. Empty string if too few points."""
    if len(series) < 3:
        return ""
    values = [v for _, v in series]
    vmin = min(values)
    vmax = max(values)
    if vmax == vmin:
        # Flat line — still show
        vrange = 1.0
    else:
        vrange = vmax - vmin
    n = len(values)
    pad_x = 3
    pad_y = 3
    plot_w = width - 2 * pad_x
    plot_h = height - 2 * pad_y

    pts: list[tuple[float, float]] = []
    for i, v in enumerate(values):
        x = pad_x + (i / max(1, n - 1)) * plot_w
        y = pad_y + plot_h - ((v - vmin) / vrange) * plot_h
        pts.append((x, y))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    fill_poly = poly + f" {pts[-1][0]:.1f},{height} {pts[0][0]:.1f},{height}"

    baseline_line = ""
    if baseline is not None and vmin <= baseline <= vmax:
        by = pad_y + plot_h - ((baseline - vmin) / vrange) * plot_h
        baseline_line = (
            f'<line class="stat-spark__baseline" x1="0" y1="{by:.1f}" '
            f'x2="{width}" y2="{by:.1f}" />'
        )

    return (
        f'<svg class="stat-spark" viewBox="0 0 {width} {height}" '
        'preserveAspectRatio="none" aria-hidden="true">'
        f'{baseline_line}'
        f'<polygon class="stat-spark__fill" points="{fill_poly}" />'
        f'<polyline class="stat-spark__line" points="{poly}" />'
        f'<circle class="stat-spark__dot" cx="{pts[-1][0]:.1f}" '
        f'cy="{pts[-1][1]:.1f}" r="2.5" />'
        '</svg>'
    )


def build_stat_sparklines(
    db, player_id: int | None, season_year: int | None,
    position: str | None = None,
) -> dict[str, str]:
    """Return {label: svg_html} for every metric we can plot."""
    if db is None or player_id is None or season_year is None:
        return {}
    out: dict[str, str] = {}
    for label, (cat, stype) in _LABEL_TO_METRIC.items():
        if stype == "PCT_CALC":
            series = _fetch_completion_rate_series(
                db, int(player_id), int(season_year),
            )
        else:
            series = _fetch_weekly_series(
                db, int(player_id), int(season_year), cat, stype,
            )
        svg = _build_sparkline_svg(series)
        if svg:
            out[label] = svg
            # Also key by metric for fallback lookups
            out[f"{cat}.{stype}"] = svg
    return out
