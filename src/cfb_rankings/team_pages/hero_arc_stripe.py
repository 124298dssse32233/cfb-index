"""Hero Arc Stripe — 13-brick CFP-era identity strip.

`TEAM_PAGE_WORLD_CLASS_BRIEF.md §20` and Iteration Log §4 locked
v1.0 = CFP era (2014-2026 = 13 seasons), one brick per season. Lives
ABOVE the fold as a 1.5-second glance-readable identity anchor —
the screenshot-virality module the brief named explicitly.

Brief verbatim (§20.1):
    "HERO STRIPE — 130 bars, one per season
     era-adjusted strength, diverging color ramp
     [Bryant red][slump blue][Saban red][current...]"

v1.0 scope cut to 13-brick CFP-era per Iteration Log §4:
    "The two model visualizations — does the CFP-era 13-brick Arc
     *fully* replace the 131-bar climate stripe for v1.0? Probably:
     compact stripe in heritage strip, brick strip as primary."

Each brick:
- Height: scales with season-strength composite (0..1) — taller =
  stronger season. Floor = 16px so even a 0-12 season is visible.
- Color: red→navy diverging via the design-system percentile ramp.
- Border: gold (--accolade-gold) when the season included a CFP
  appearance.
- Tooltip: `2024 · 11-2 · #5 AP · CFP Quarterfinal`.

Reads from the same `arc_rows` payload the deeper season_arc_card
consumes — no new data fetch.

Public API:
    render_hero_arc_stripe(profile, arc_rows, *, accent_primary,
                            accent_secondary) -> str
    HERO_ARC_STRIPE_CSS  (CSS string, inlined into renderer.py page)
"""
from __future__ import annotations

import html
from typing import Any

from .profile_loader import Profile


HERO_ARC_STRIPE_CSS = """
/* Hero Arc Stripe — TEAM_PAGE_WORLD_CLASS_BRIEF §20, v1.0 CFP era */

.hero-arc-stripe {
  --has-cfp:        var(--accolade-gold);
  --brick-empty:    color-mix(in oklab, var(--bg-card-raised) 80%, var(--bg-card));
  --label-fg:       var(--fg-secondary);

  display: grid;
  gap: var(--sp-3, 12px);
  padding: clamp(16px, 2.2vw, 28px) clamp(16px, 2.6vw, 32px);
  background:
    linear-gradient(
      135deg,
      color-mix(in oklab, var(--accent-primary) 6%, transparent) 0%,
      color-mix(in oklab, var(--accent-secondary) 4%, transparent) 60%,
      transparent 100%
    );
  border: 1px solid var(--stroke-default);
  border-radius: var(--radius-lg, 16px);
  margin-bottom: clamp(20px, 3vw, 32px);
}

.hero-arc-stripe__header {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px 24px;
}
.hero-arc-stripe__title {
  font-family: var(--font-display);
  font-size: clamp(20px, 1.5vw + 10px, 28px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--fg-primary);
  margin: 0;
}
.hero-arc-stripe__sub {
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}

.hero-arc-stripe__bricks {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(0, 1fr);
  align-items: end;
  gap: 6px;
  height: 96px;
  padding: 4px 0;
}

.hero-arc-stripe__brick {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: stretch;
  min-width: 0;
  height: 100%;
  cursor: default;
}
.hero-arc-stripe__bar {
  display: block;
  width: 100%;
  border-radius: 4px 4px 2px 2px;
  background: var(--brick-color, var(--brick-empty));
  border: 1px solid color-mix(in oklab, var(--brick-color, var(--brick-empty)) 60%, transparent);
  min-height: 16px;
  transition: filter 120ms ease;
}
.hero-arc-stripe__brick--cfp .hero-arc-stripe__bar {
  border: 2px solid var(--has-cfp);
  box-shadow: 0 0 0 2px color-mix(in oklab, var(--has-cfp) 22%, transparent);
}
.hero-arc-stripe__brick--current .hero-arc-stripe__bar {
  outline: 2px solid var(--accent-primary);
  outline-offset: 2px;
}
.hero-arc-stripe__brick:hover .hero-arc-stripe__bar {
  filter: brightness(1.18);
}

.hero-arc-stripe__brick-label {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--fg-muted);
  text-align: center;
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.hero-arc-stripe__brick--cfp .hero-arc-stripe__brick-label {
  color: var(--has-cfp);
}

.hero-arc-stripe__legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 18px;
  font-family: var(--font-sans);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.hero-arc-stripe__legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  margin-right: 6px;
  vertical-align: middle;
}
.hero-arc-stripe__legend-dot--high { background: var(--pct-high); }
.hero-arc-stripe__legend-dot--mid  { background: var(--pct-mid); }
.hero-arc-stripe__legend-dot--low  { background: var(--pct-low); }
.hero-arc-stripe__legend-dot--cfp  {
  background: transparent;
  border: 2px solid var(--has-cfp);
  width: 10px; height: 10px;
}

@media (max-width: 540px) {
  .hero-arc-stripe__bricks { height: 72px; gap: 4px; }
  .hero-arc-stripe__brick-label { font-size: 8px; }
  .hero-arc-stripe__title { font-size: 20px; }
}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _composite_strength(row: dict[str, Any]) -> float:
    """Composite season-strength score in [0.0, 1.0]. Read from the
    pre-computed `quality_score` on each arc row if available; else
    derive from win% + AP rank.

    Brief §20.2's exact formula uses SRS percentile within a 15-year
    window + AP-rank contribution + SOS-adjusted win residual. For
    v1.0 we use whatever the season_arc_loader stuffed in `quality_score`
    and fall back to derived values when it's missing.
    """
    qs = row.get("quality_score")
    if qs is not None:
        try:
            return max(0.0, min(1.0, float(qs)))
        except (TypeError, ValueError):
            pass
    # Derive from wins/losses + AP rank
    w = row.get("wins") or 0
    l = row.get("losses") or 0
    try:
        win_pct = float(w) / max(1, float(w) + float(l))
    except (TypeError, ValueError):
        win_pct = 0.5
    ap = row.get("final_ap_rank")
    ap_bonus = 0.0
    if ap:
        try:
            ap_i = int(ap)
            if 1 <= ap_i <= 25:
                ap_bonus = (26 - ap_i) / 25 * 0.4
        except (TypeError, ValueError):
            pass
    return max(0.0, min(1.0, win_pct * 0.6 + ap_bonus))


def _brick_color(strength: float) -> str:
    """Map a 0..1 strength to an OKLCH-ish percentile color. Uses the
    design-system token names (--pct-high / --pct-mid / --pct-low) via
    color-mix so the dark/light theme tokens cascade correctly.
    """
    if strength >= 0.75:
        return "var(--pct-high)"
    if strength >= 0.55:
        return "color-mix(in oklab, var(--pct-high) 60%, var(--pct-mid) 40%)"
    if strength >= 0.40:
        return "var(--pct-mid)"
    if strength >= 0.22:
        return "color-mix(in oklab, var(--pct-low) 60%, var(--pct-mid) 40%)"
    return "var(--pct-low)"


def _had_cfp_appearance(row: dict[str, Any]) -> bool:
    """Did this season include a CFP appearance? Loose detection
    against fields the season_arc_loader populates."""
    for k in ("had_cfp", "cfp_appearance", "made_cfp"):
        v = row.get(k)
        if v in (True, 1, "1", "true", "True"):
            return True
    notes = row.get("notes_json")
    if notes:
        try:
            import json as _json
            data = _json.loads(notes) if isinstance(notes, str) else dict(notes)
            if data.get("cfp_appearance") or data.get("made_cfp"):
                return True
        except (TypeError, ValueError):
            pass
    return False


def _row_record_text(row: dict[str, Any]) -> str:
    w = row.get("wins")
    l = row.get("losses")
    if w is None and l is None:
        return ""
    return f"{int(w or 0)}-{int(l or 0)}"


def _row_ap_text(row: dict[str, Any]) -> str:
    ap = row.get("final_ap_rank")
    if ap in (None, 0, "0", ""):
        return "UR"
    try:
        return f"#{int(ap)}"
    except (TypeError, ValueError):
        return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# CFP era window. Brief locked v1.0 = 2014-2026 = 13 seasons.
CFP_ERA_START = 2014
CFP_ERA_END = 2026


def render_hero_arc_stripe(
    profile: Profile,
    arc_rows: list[dict[str, Any]],
    *,
    current_season: int | None = None,
) -> str:
    """Render the 13-brick CFP-era Hero Arc stripe.

    Returns "" when no arc data is available (graceful degradation for
    thin-history programs per brief §20.5).
    """
    # Index arc_rows by season for fast lookup
    by_year: dict[int, dict[str, Any]] = {}
    for r in arc_rows or []:
        try:
            y = int(r.get("season_year") or 0)
        except (TypeError, ValueError):
            continue
        if y:
            by_year[y] = r

    if not by_year:
        return ""

    # Stat aggregates for the header
    seasons_in_window = [
        by_year[y] for y in range(CFP_ERA_START, CFP_ERA_END + 1)
        if y in by_year
    ]
    cfp_count = sum(1 for r in seasons_in_window if _had_cfp_appearance(r))

    bricks_html: list[str] = []
    for year in range(CFP_ERA_START, CFP_ERA_END + 1):
        row = by_year.get(year)
        is_current = (current_season is not None and year == int(current_season))
        if row is None:
            # No data — render an empty placeholder at min height
            bricks_html.append(
                '<div class="hero-arc-stripe__brick" '
                f'title="{year} · no data on file" aria-label="{year} no data">'
                '<span class="hero-arc-stripe__bar" '
                'style="--brick-color: var(--brick-empty); height: 16px;"></span>'
                f'<span class="hero-arc-stripe__brick-label">{html.escape(str(year)[-2:])}</span>'
                '</div>'
            )
            continue
        strength = _composite_strength(row)
        # Bar height range: 18% to 100% of bricks container height
        height_pct = max(18, int(round(strength * 100)))
        color = _brick_color(strength)
        had_cfp = _had_cfp_appearance(row)
        record_text = _row_record_text(row)
        ap_text = _row_ap_text(row)
        title_parts = [str(year)]
        if record_text:
            title_parts.append(record_text)
        if ap_text:
            title_parts.append(ap_text + " AP")
        if had_cfp:
            title_parts.append("CFP")
        title = " · ".join(title_parts)
        classes = ["hero-arc-stripe__brick"]
        if had_cfp:
            classes.append("hero-arc-stripe__brick--cfp")
        if is_current:
            classes.append("hero-arc-stripe__brick--current")
        bricks_html.append(
            f'<div class="{" ".join(classes)}" '
            f'title="{html.escape(title)}" aria-label="{html.escape(title)}">'
            '<span class="hero-arc-stripe__bar" '
            f'style="--brick-color: {color}; height: {height_pct}%;"></span>'
            f'<span class="hero-arc-stripe__brick-label">'
            f'{html.escape(str(year)[-2:])}'
            '</span>'
            '</div>'
        )

    program = html.escape(profile.program_name)
    title_text = f"CFP Era · {program}"
    sub_parts = [f"{len(seasons_in_window)} seasons on file"]
    if cfp_count > 0:
        sub_parts.append(
            f"{cfp_count} CFP appearance" + ("s" if cfp_count != 1 else "")
        )

    return f"""
<section class="hero-arc-stripe" aria-labelledby="hero-arc-stripe-h" data-module="hero-arc-stripe">
  <div class="hero-arc-stripe__header">
    <h2 id="hero-arc-stripe-h" class="hero-arc-stripe__title">{html.escape(title_text)}</h2>
    <p class="hero-arc-stripe__sub">{html.escape(" · ".join(sub_parts))}</p>
  </div>
  <div class="hero-arc-stripe__bricks" role="img"
       aria-label="13-brick season-strength arc, 2014 through 2026">
    {''.join(bricks_html)}
  </div>
  <p class="hero-arc-stripe__legend">
    <span><span class="hero-arc-stripe__legend-dot hero-arc-stripe__legend-dot--low"></span>down</span>
    <span><span class="hero-arc-stripe__legend-dot hero-arc-stripe__legend-dot--mid"></span>middle</span>
    <span><span class="hero-arc-stripe__legend-dot hero-arc-stripe__legend-dot--high"></span>peak</span>
    <span><span class="hero-arc-stripe__legend-dot hero-arc-stripe__legend-dot--cfp"></span>CFP year</span>
  </p>
</section>
"""


__all__ = [
    "render_hero_arc_stripe",
    "HERO_ARC_STRIPE_CSS",
    "CFP_ERA_START",
    "CFP_ERA_END",
]
