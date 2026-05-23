"""Development Trajectory module — Brief Signature Bet #15.

Multi-season line chart showing year-over-year improvement in a player's
headline metric. For QBs: passing yards. For RBs: rushing yards. For WRs/TEs:
receiving yards.

Sources from player_season_stats.

Only renders when the player has ≥2 seasons of data (single-season players
fall back to empty). Empty when no data.

Public API:
    render_development_trajectory(db, player_id, position) -> str
    DEVELOPMENT_TRAJECTORY_CSS                              -> str
"""
from __future__ import annotations

from html import escape


DEVELOPMENT_TRAJECTORY_CSS = """
/* Development Trajectory chart */
.dev-traj {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.dev-traj__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
  margin-bottom: 12px;
}
.dev-traj__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted-foreground, var(--fg-muted, #666));
  margin: 0;
}
.dev-traj__metric {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  letter-spacing: 0.10em;
  color: var(--muted-foreground, var(--fg-muted, #666));
  text-transform: uppercase;
}
.dev-traj__body {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 14px 20px;
  align-items: stretch;
}
.dev-traj__bars {
  display: flex;
  gap: 8px;
  align-items: end;
  min-width: 140px;
  height: 80px;
}
.dev-traj__bar {
  flex: 1;
  background: linear-gradient(
    to top,
    var(--accent-primary, var(--accolade-gold-base, #d1a23a)) 0%,
    color-mix(in srgb, var(--accent-primary, #d1a23a) 60%, transparent) 100%
  );
  border-radius: 2px 2px 0 0;
  min-height: 4px;
  position: relative;
}
.dev-traj__bar-year {
  position: absolute;
  bottom: -16px;
  left: 0;
  right: 0;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 9px;
  color: var(--muted-foreground, var(--fg-muted, #666));
  text-align: center;
}
.dev-traj__bar-value {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 9px;
  color: var(--foreground, var(--fg-secondary, #999));
  text-align: center;
  margin-bottom: 2px;
}
.dev-traj__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  font-style: italic;
  line-height: 1.4;
  color: var(--muted-foreground, var(--fg-secondary, #666));
  margin: 0;
  max-width: 56ch;
}
.dev-traj__delta {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(22px, 1.4vw + 8px, 28px);
  letter-spacing: 0.02em;
  color: var(--foreground, var(--fg-primary, #222));
  margin: 0 0 4px 0;
  line-height: 1;
}
.dev-traj__delta--positive { color: #4f9d6b; }
.dev-traj__delta--negative { color: #c95151; }
"""


# Position → headline category + stat_type
_POS_STAT_MAP = {
    "QB": ("passing", "YDS", "passing yards"),
    "RB": ("rushing", "YDS", "rushing yards"),
    "FB": ("rushing", "YDS", "rushing yards"),
    "TB": ("rushing", "YDS", "rushing yards"),
    "WR": ("receiving", "YDS", "receiving yards"),
    "TE": ("receiving", "YDS", "receiving yards"),
}


def render_development_trajectory(
    db, player_id: int | None, position: str | None,
) -> str:
    if db is None or player_id is None:
        return ""
    pos = (position or "").upper()
    cfg = _POS_STAT_MAP.get(pos)
    if not cfg:
        return ""
    category, stat_type, metric_label = cfg

    # Sum across weeks for each season (since stats are weekly snapshots
    # we sum the final week's value — actually season_year may aggregate.
    # Use max(week) to get the season-final cumulative value.)
    rows = db.query_all(
        """
        with final_week as (
          select season_year, max(week) as wk
            from player_season_stats
           where player_id = :pid
             and category = :cat and stat_type = :st
           group by season_year
        )
        select pss.season_year, pss.stat_value_num as v
          from player_season_stats pss
          join final_week fw
            on fw.season_year = pss.season_year and fw.wk = pss.week
         where pss.player_id = :pid
           and pss.category = :cat and pss.stat_type = :st
         order by pss.season_year
        """,
        {"pid": player_id, "cat": category, "st": stat_type},
    )
    seasons = [(int(r["season_year"]), float(r["v"] or 0)) for r in rows if r.get("v") is not None]
    if len(seasons) < 2:
        return ""

    max_val = max(v for _, v in seasons) or 1.0

    bars_html: list[str] = []
    for yr, v in seasons:
        h_pct = max(4, int(100 * v / max_val))
        v_label = f"{int(v):,}" if v >= 100 else f"{v:.1f}"
        bars_html.append(
            f'<div class="dev-traj__bar" style="height: {h_pct}%;" title="{yr}: {v_label} {metric_label}">'
            f'<span class="dev-traj__bar-value">{v_label}</span>'
            f'<span class="dev-traj__bar-year">{yr}</span>'
            '</div>'
        )

    first_v = seasons[0][1]
    last_v = seasons[-1][1]
    delta = last_v - first_v
    pct_delta = (delta / first_v * 100) if first_v else 0.0
    if pct_delta >= 25:
        delta_cls = "positive"
        story = f"Up {pct_delta:.0f}% from first season to most-recent."
    elif pct_delta >= 0:
        delta_cls = ""
        story = f"Modest growth ({pct_delta:.0f}%) across the multi-season window."
    elif pct_delta >= -20:
        delta_cls = "negative"
        story = f"Down {abs(pct_delta):.0f}% — context-dependent (injury / role change?)."
    else:
        delta_cls = "negative"
        story = f"Sharp dropoff ({pct_delta:.0f}%) — career inflection point."

    delta_label = f"{pct_delta:+.0f}%"
    span_chunk = f"{seasons[0][0]}–{seasons[-1][0]}"

    return f"""
<section class="dev-traj" data-module="development-trajectory" data-state="ready"
         data-position="{escape(pos)}">
  <div class="dev-traj__head">
    <p class="dev-traj__eyebrow">Development Trajectory · {escape(metric_label)}</p>
    <span class="dev-traj__metric">{escape(span_chunk)}</span>
  </div>
  <div class="dev-traj__body">
    <div class="dev-traj__bars">{''.join(bars_html)}</div>
    <div>
      <h3 class="dev-traj__delta dev-traj__delta--{delta_cls}">{delta_label}</h3>
      <p class="dev-traj__story">{escape(story)}</p>
    </div>
  </div>
</section>"""


__all__ = ["render_development_trajectory", "DEVELOPMENT_TRAJECTORY_CSS"]
