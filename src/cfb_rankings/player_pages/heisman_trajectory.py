"""Heisman Trajectory chart — Brief Signature Bet #14.

Surfaces the player's Heisman rank week-by-week across the season using
heisman_rankings_weekly. Shows a sparkline (SVG) of rank-over-time + the
peak rank + the final rank + the season average.

Only renders for players who appeared in at least 3 weekly rankings —
typically the top-25 Heisman contenders. Falls back gracefully empty
for everyone else.

Public API:
    render_heisman_trajectory(db, player_id, season_year) -> str
    HEISMAN_TRAJECTORY_CSS                                 -> str
"""
from __future__ import annotations

from html import escape


HEISMAN_TRAJECTORY_CSS = """
/* Heisman Trajectory sparkline */
.heisman-traj {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accolade-gold-base, #d1a23a);
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.heisman-traj__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
  margin-bottom: 12px;
}
.heisman-traj__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted-foreground, var(--fg-muted, #666));
  margin: 0;
}
.heisman-traj__peak {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(22px, 1.6vw + 8px, 30px);
  font-weight: 400;
  letter-spacing: 0.02em;
  color: var(--accolade-gold-base, #d1a23a);
  margin: 0;
  line-height: 1;
}
.heisman-traj__body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px 22px;
  align-items: center;
}
.heisman-traj__chart {
  width: 100%;
  height: 90px;
}
.heisman-traj__chart .traj-line {
  stroke: var(--accolade-gold-base, #d1a23a);
  stroke-width: 2;
  fill: none;
}
.heisman-traj__chart .traj-fill {
  fill: color-mix(in srgb, var(--accolade-gold-base, #d1a23a) 22%, transparent);
}
.heisman-traj__chart .traj-axis-line {
  stroke: var(--stroke-subtle, rgba(255,255,255,0.10));
  stroke-width: 1;
  stroke-dasharray: 3 3;
}
.heisman-traj__chart .traj-end-dot {
  fill: var(--accolade-gold-highlight, #f2c866);
  stroke: var(--accolade-gold-base, #d1a23a);
  stroke-width: 2;
}
.heisman-traj__meta {
  display: grid;
  gap: 4px;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 11px;
  color: var(--muted-foreground, var(--fg-secondary, #666));
  text-align: right;
}
.heisman-traj__meta-value {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: 18px;
  color: var(--foreground, var(--fg-primary, #222));
  letter-spacing: 0.04em;
}
.heisman-traj__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  font-style: italic;
  line-height: 1.4;
  color: var(--muted-foreground, var(--fg-secondary, #666));
  margin: 8px 0 0 0;
  max-width: 56ch;
}
.heisman-traj--empty {
  color: var(--muted-foreground, var(--fg-muted, #666));
  font-style: italic;
  font-size: var(--fs-meta, 0.78rem);
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
}
"""


def render_heisman_trajectory(
    db, player_id: int | None, season_year: int | None,
) -> str:
    if db is None or player_id is None or season_year is None:
        return ""
    rows = db.query_all(
        """
        select week, rank_overall, finalist_probability
          from heisman_rankings_weekly
         where player_id = :pid and season_year = :s
           and rank_overall is not null
         order by week
        """,
        {"pid": player_id, "s": season_year},
    )
    if not rows:
        return ""
    # Single-week mode: render a static "Final Heisman Position" badge instead
    # of the full sparkline. The 2024 data currently only has week 16 snapshots
    # so most players land here.
    if len(rows) < 3:
        r = rows[-1]
        rank = int(r.get("rank_overall") or 0)
        finalist = float(r.get("finalist_probability") or 0)
        if rank == 0 or rank > 25:
            return ""
        if rank == 1:
            label = "Heisman favorite"
        elif rank <= 3:
            label = f"Heisman finalist tier (#{rank})"
        elif rank <= 5:
            label = f"Heisman top-5 (#{rank})"
        elif rank <= 10:
            label = f"Heisman top-10 (#{rank})"
        else:
            label = f"Heisman top-25 (#{rank})"
        return f"""
<section class="heisman-traj" data-module="heisman-trajectory" data-state="snapshot"
         data-final="{rank}">
  <div class="heisman-traj__head">
    <p class="heisman-traj__eyebrow">Final Heisman Position &middot; {season_year}</p>
    <h3 class="heisman-traj__peak">#{rank}</h3>
  </div>
  <p class="heisman-traj__story">{escape(label)} &middot; finalist probability {finalist*100:.0f}%.</p>
</section>"""

    weeks = [int(r.get("week") or 0) for r in rows]
    ranks = [int(r.get("rank_overall") or 99) for r in rows]
    finalist_probs = [float(r.get("finalist_probability") or 0) for r in rows]

    peak_rank = min(ranks)
    final_rank = ranks[-1]
    avg_rank = sum(ranks) / len(ranks)
    peak_finalist = max(finalist_probs)

    # SVG sparkline (lower rank = HIGHER on chart). Map rank 1-25 to y=0-1 inverted.
    chart_w, chart_h = 360, 80
    rank_cap = 25  # render ranks 1-25; anything beyond clamps
    points: list[tuple[float, float]] = []
    for idx, r in enumerate(ranks):
        x = (idx / max(1, len(ranks) - 1)) * chart_w
        y_normalized = min(1.0, (r - 1) / (rank_cap - 1))  # rank 1 → 0; rank 25 → 1
        y = y_normalized * chart_h
        points.append((x, y))

    polyline_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    # Fill area: under the line
    fill_pts = polyline_pts + f" {chart_w:.1f},{chart_h:.1f} 0,{chart_h:.1f}"
    end_x, end_y = points[-1]

    # Axis line at rank 5
    axis_y_5 = ((5 - 1) / (rank_cap - 1)) * chart_h

    if peak_rank == 1:
        story = "Reached #1 in the Heisman model at some point during the season."
    elif peak_rank <= 3:
        story = f"Peaked at #{peak_rank} — top-tier Heisman contention all season."
    elif peak_rank <= 5:
        story = f"Peaked at #{peak_rank} — sustained finalist conversation."
    elif peak_rank <= 10:
        story = f"Peaked at #{peak_rank} — top-10 conversation."
    else:
        story = f"Peaked at #{peak_rank} this season."

    return f"""
<section class="heisman-traj" data-module="heisman-trajectory" data-state="ready"
         data-peak="{peak_rank}" data-final="{final_rank}">
  <div class="heisman-traj__head">
    <p class="heisman-traj__eyebrow">Heisman Trajectory &middot; {season_year}</p>
    <h3 class="heisman-traj__peak">Peak #{peak_rank}</h3>
  </div>
  <div class="heisman-traj__body">
    <svg class="heisman-traj__chart" viewBox="0 0 {chart_w} {chart_h}" preserveAspectRatio="none" aria-hidden="true">
      <line class="traj-axis-line" x1="0" y1="{axis_y_5:.1f}" x2="{chart_w}" y2="{axis_y_5:.1f}" />
      <polygon class="traj-fill" points="{fill_pts}" />
      <polyline class="traj-line" points="{polyline_pts}" />
      <circle class="traj-end-dot" cx="{end_x:.1f}" cy="{end_y:.1f}" r="4" />
    </svg>
    <div class="heisman-traj__meta">
      <div>Final rank</div>
      <div class="heisman-traj__meta-value">#{final_rank}</div>
      <div>Avg #{avg_rank:.1f}</div>
      <div>Finalist prob {peak_finalist*100:.0f}%</div>
    </div>
  </div>
  <p class="heisman-traj__story">{escape(story)}</p>
</section>"""


__all__ = ["render_heisman_trajectory", "HEISMAN_TRAJECTORY_CSS"]
