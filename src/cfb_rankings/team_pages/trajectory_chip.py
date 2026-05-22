"""Program Trajectory Chip — Brief §11.4.

A compact, single-tile callout that names the program's direction.

Brief verbatim (§11.4):

    "A 10-year rolling Prestige Rung chart — the team's own prestige
     history, plotted as a line. This is the all-time Arc view from §6,
     compressed into a compact visual for the hero zone."

    "Trajectory label: Generated automatically from the slope:
     'Rising' / 'Steady' / 'Declining' / 'Volatile' (high standard
     deviation of rung over 10 years)."

Why it matters (brief continued):

    "Trajectory direction matters more than absolute position for story.
     A program moving from Tier 3 to Tier 5 in five years (Georgia
     2016–2022) is a more interesting story than a program holding at
     Tier 5 (static Alabama). The chart shows the slope."

Implementation: ingests the `arc_rows` payload already fetched by the
renderer (no extra query). Computes a per-season pseudo-rung from
win_pct + AP final + cfp_flag, then slopes the last 10 entries.

Public API:
    render_trajectory_chip(profile, arc_rows) -> str
    TRAJECTORY_CHIP_CSS                        -> str
    classify_trajectory(rungs) -> tuple[label, narrative]
"""
from __future__ import annotations

import statistics
from html import escape
from typing import Any

from .profile_loader import Profile


TRAJECTORY_CHIP_CSS = """
/* Program Trajectory Chip — Brief §11.4 */
.trajectory-chip {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px 18px;
  padding: 12px clamp(14px, 1.8vw, 20px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
}
.trajectory-chip__direction {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(22px, 1.8vw + 10px, 30px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--accent-primary, #c9a24a);
  white-space: nowrap;
}
.trajectory-chip__direction--rising    { color: #2c8f5a; }
.trajectory-chip__direction--declining { color: #c95151; }
.trajectory-chip__direction--volatile  { color: #c98c1a; }
.trajectory-chip__direction--steady    { color: var(--accent-primary, #c9a24a); }

.trajectory-chip__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 14px;
  font-style: italic;
  line-height: 1.45;
  color: var(--fg-secondary);
  margin: 0;
  max-width: 64ch;
}

.trajectory-chip__spark {
  display: block;
  height: 36px;
  width: clamp(80px, 12vw, 160px);
  font-variant-numeric: tabular-nums;
}
.trajectory-chip__spark path {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
  stroke-linejoin: round;
  stroke-linecap: round;
}
.trajectory-chip__spark circle {
  fill: var(--accent-primary, #c9a24a);
}
.trajectory-chip__spark line.baseline {
  stroke: var(--fg-muted);
  stroke-dasharray: 2 3;
  stroke-width: 0.5;
  opacity: 0.5;
}

@media (max-width: 540px) {
  .trajectory-chip { grid-template-columns: 1fr; }
  .trajectory-chip__spark { width: 100%; }
}
"""


# ---------------------------------------------------------------------------
# Rung computation from arc_rows
# ---------------------------------------------------------------------------

def _row_to_rung(row: dict[str, Any]) -> float | None:
    """Convert a season_arc row to a pseudo-rung (0-9 float).

    Cascade mirrors season_standing_rail but uses end-of-season data:
        - title_won_flag → 9
        - title_game_flag → 8
        - cfp_flag → 7
        - ap_rank_final ≤ 5 → 6
        - ap_rank_final ≤ 15 → 5
        - ap_rank_final ≤ 25 → 4
        - 6+ wins → 3
        - record .500+ → 2
        - sub-.500 → 1
    """
    if row.get("title_won_flag"):
        return 9.0
    if row.get("title_game_flag"):
        return 8.0
    if row.get("cfp_flag"):
        return 7.0
    ap = row.get("ap_rank_final")
    if ap is not None:
        try:
            r = int(ap)
            if 0 < r <= 5:  return 6.0
            if r <= 15:     return 5.0
            if r <= 25:     return 4.0
        except (TypeError, ValueError):
            pass
    wins = int(row.get("wins") or 0)
    losses = int(row.get("losses") or 0)
    if wins + losses == 0:
        return None
    if wins >= 6:
        return 3.0
    if wins >= losses:
        return 2.0
    return 1.0


def classify_trajectory(rungs: list[float]) -> tuple[str, str]:
    """Classify a list of per-season rungs as Rising / Steady / Declining / Volatile.

    Heuristic:
        - Need 4+ years of data.
        - If stdev > 2.0 → Volatile.
        - Linear slope of last-N rungs:
            slope > +0.18/yr → Rising
            slope < -0.18/yr → Declining
            else → Steady.

    Returns (label, narrative).
    """
    if not rungs or len(rungs) < 4:
        return ("Insufficient history", "Need at least four seasons of data to read direction.")

    try:
        sd = statistics.pstdev(rungs)
    except statistics.StatisticsError:
        sd = 0.0

    n = len(rungs)
    mean_x = (n - 1) / 2
    mean_y = sum(rungs) / n
    num = sum((i - mean_x) * (rungs[i] - mean_y) for i in range(n))
    denom = sum((i - mean_x) ** 2 for i in range(n))
    slope = num / denom if denom else 0.0

    first_avg = sum(rungs[: max(1, n // 2)]) / max(1, n // 2)
    last_avg = sum(rungs[-max(1, n // 2):]) / max(1, n // 2)
    delta = last_avg - first_avg

    # Volatile takes precedence — when the variance dominates the slope signal.
    if sd >= 2.2 and abs(slope) < 0.30:
        return (
            "Volatile",
            f"Wide swings — {len(rungs)} seasons covering a {min(rungs):.0f}-{max(rungs):.0f} prestige range. "
            f"The slope flattens but the standard deviation ({sd:.1f}) tells the real story.",
        )
    if slope >= 0.18 or delta >= 1.5:
        return (
            "Rising",
            f"Climbing {delta:+.1f} rungs across the last {len(rungs)} seasons. "
            f"Slope {slope:+.2f} rungs / year — moving up the prestige scale.",
        )
    if slope <= -0.18 or delta <= -1.5:
        return (
            "Declining",
            f"Slipping {delta:+.1f} rungs across the last {len(rungs)} seasons. "
            f"Slope {slope:+.2f} rungs / year — moving down the prestige scale.",
        )
    return (
        "Steady",
        f"Holding the line. The {len(rungs)}-year slope ({slope:+.2f} rungs / yr) doesn't tilt either way — "
        f"the program lives at roughly Tier {mean_y:.0f}.",
    )


def _sparkline_svg(rungs: list[float]) -> str:
    """Tiny sparkline of the rungs over time."""
    if not rungs:
        return ""
    w, h = 160, 36
    margin = 2
    n = len(rungs)
    if n < 2:
        return ""
    # Y axis is 0-9 rungs; invert (higher rung = higher on chart, but SVG y grows downward).
    lo, hi = 0.0, 9.0
    span = hi - lo
    def y(v: float) -> float:
        return margin + (h - 2 * margin) * (1.0 - (v - lo) / span)
    def x(i: int) -> float:
        return margin + (w - 2 * margin) * (i / (n - 1))
    pts = " ".join(f"{x(i):.1f},{y(rungs[i]):.1f}" for i in range(n))
    path_d = "M " + " L ".join(p for p in pts.split())
    last_cx = x(n - 1)
    last_cy = y(rungs[-1])
    baseline_y = y(rungs[0])
    return (
        f'<svg class="trajectory-chip__spark" viewBox="0 0 {w} {h}" '
        f'preserveAspectRatio="none" role="img" aria-label="10-season prestige sparkline">'
        f'<line class="baseline" x1="0" y1="{baseline_y:.1f}" x2="{w}" y2="{baseline_y:.1f}"></line>'
        f'<path d="{path_d}"></path>'
        f'<circle cx="{last_cx:.1f}" cy="{last_cy:.1f}" r="3"></circle>'
        f'</svg>'
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_trajectory_chip(profile: Profile, arc_rows: list[dict[str, Any]]) -> str:
    """Render the Program Trajectory chip from arc_rows (Brief §11.4)."""
    if not arc_rows:
        return ""

    sorted_rows = sorted(arc_rows, key=lambda r: int(r.get("season_year") or 0))
    rungs_with_year: list[tuple[int, float]] = []
    for row in sorted_rows:
        v = _row_to_rung(row)
        if v is not None:
            try:
                yr = int(row.get("season_year"))
            except (TypeError, ValueError):
                continue
            rungs_with_year.append((yr, v))

    if len(rungs_with_year) < 4:
        return ""

    # Use last 10 seasons.
    last_ten = rungs_with_year[-10:]
    rungs = [v for _, v in last_ten]
    start_year = last_ten[0][0]
    end_year = last_ten[-1][0]

    label, narrative = classify_trajectory(rungs)
    cls_suffix = label.lower()
    program = escape(profile.program_name)
    span = f"{start_year}–{end_year}"

    return (
        '<section class="trajectory-chip" aria-labelledby="trajectory-chip-h" '
        'data-module="trajectory-chip" data-state="ready">'
        f'<h2 id="trajectory-chip-h" class="trajectory-chip__direction trajectory-chip__direction--{cls_suffix}">'
        f'{escape(label)}</h2>'
        f'<p class="trajectory-chip__story">'
        f'<strong>{program} {span}.</strong> {escape(narrative)}'
        f'</p>'
        f'{_sparkline_svg(rungs)}'
        '</section>'
    )


__all__ = [
    "render_trajectory_chip",
    "TRAJECTORY_CHIP_CSS",
    "classify_trajectory",
]
