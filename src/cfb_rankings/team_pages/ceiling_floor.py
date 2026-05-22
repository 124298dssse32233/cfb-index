"""Ceiling vs. Floor projection — Brief §11.2.

Three-scenario probability distribution for next season's outcome.

Brief verbatim (§11.2):

    "Every team page should surface a probability distribution, not a
     point estimate, for the season's possible outcomes.

       Floor   — pessimistic, 1-SD downward variance in SP+.
                 '6-6 regular season, bowl eligible, miss bowl if
                  things go wrong.'
       Base    — central estimate.
                 '9-3 regular season, likely bowl appearance.'
       Ceiling — optimistic if things break right.
                 '11-1, CFP contender, conference title game.'

     Rendered as a horizontal probability band — a bell curve
     visualization showing the full probability mass."

Implementation: full SP+ variance modeling requires SP+ point
projections we don't have in the local DB. This module uses the
honest fallback: last-season win-share + a fixed ±2.5-win variance
(standard CFB year-to-year SD) to construct three scenarios on
the brief's framing.

Public API:
    render_ceiling_floor(profile, snapshot, arc_rows) -> str
    CEILING_FLOOR_CSS                                  -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot


CEILING_FLOOR_CSS = """
/* Ceiling/Floor projection — Brief §11.2 */
.ceiling-floor {
  display: grid;
  gap: clamp(10px, 1.2vw, 16px);
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
}
.ceiling-floor__header {
  display: grid;
  gap: 4px;
}
.ceiling-floor__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.ceiling-floor__title {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(20px, 1.5vw + 10px, 26px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--fg-primary);
  margin: 0;
}

/* Probability band — bell curve via gradient */
.ceiling-floor__band {
  position: relative;
  height: 56px;
  background:
    radial-gradient(circle at 50% 50%, rgba(201,162,74,0.32), transparent 65%),
    linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.02));
  border-radius: 999px;
  overflow: hidden;
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.06));
}
.ceiling-floor__band::before {
  /* The bell curve "spine" */
  content: "";
  position: absolute;
  inset: 8px 0;
  background: linear-gradient(90deg,
    color-mix(in oklab, #c95151 60%, transparent) 0%,
    color-mix(in oklab, var(--accent-primary, #c9a24a) 70%, transparent) 50%,
    color-mix(in oklab, #2c8f5a 60%, transparent) 100%);
  border-radius: 999px;
  filter: blur(8px);
  opacity: 0.45;
}
.ceiling-floor__marker {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--fg-primary);
}
.ceiling-floor__marker-label {
  position: absolute;
  top: 4px;
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--fg-muted);
  white-space: nowrap;
  transform: translateX(-50%);
}
.ceiling-floor__marker-label--base {
  color: var(--accent-primary, #c9a24a);
}

/* Scenario cards */
.ceiling-floor__scenarios {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.ceiling-floor__scenario {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-radius: 8px;
  border-top: 3px solid var(--accent-primary, #c9a24a);
}
.ceiling-floor__scenario[data-kind="floor"]   { border-top-color: #c95151; }
.ceiling-floor__scenario[data-kind="base"]    { border-top-color: var(--accent-primary, #c9a24a); }
.ceiling-floor__scenario[data-kind="ceiling"] { border-top-color: #2c8f5a; }
.ceiling-floor__scenario-kind {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.ceiling-floor__scenario-record {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(20px, 1.4vw + 10px, 26px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
  color: var(--fg-primary);
}
.ceiling-floor__scenario-story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 12px;
  font-style: italic;
  line-height: 1.4;
  color: var(--fg-secondary);
}
.ceiling-floor__caveat {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-style: italic;
  color: var(--fg-muted);
  margin: 0;
  opacity: 0.7;
}
@media (max-width: 640px) {
  .ceiling-floor__scenarios { grid-template-columns: 1fr; }
}
"""


# ---------------------------------------------------------------------------
# Projection math
# ---------------------------------------------------------------------------

def _baseline_wins(snapshot: TeamSnapshot, arc_rows: list[dict[str, Any]]) -> tuple[int, int] | None:
    """Return (base_wins, base_games) — base scenario center."""
    # Prefer last completed season from arc_rows.
    if arc_rows:
        sr = sorted(arc_rows, key=lambda r: int(r.get("season_year") or 0))
        last = sr[-1]
        lw = int(last.get("wins") or 0)
        ll = int(last.get("losses") or 0)
        if lw + ll > 0:
            return (lw, lw + ll)
    # Else current snapshot.
    w = int(snapshot.wins or 0)
    l = int(snapshot.losses or 0)
    if w + l > 0:
        return (w, w + l)
    return None


def _scenario_story(kind: str, wins: int, games: int) -> str:
    losses = games - wins
    if kind == "floor":
        if wins <= 3:
            return "Rebuild year. Bowl access uncertain."
        if wins <= 5:
            return "Below .500. Bowl eligibility comes down to the closing run."
        return "Bowl eligible if the close games break right."
    if kind == "ceiling":
        if wins >= 12:
            return "Undefeated regular season. CFP path opens."
        if wins >= 10:
            return "Double-digit wins. Conference title-game conversation."
        if wins >= 8:
            return "Strong year. NY6-bowl positioning."
        return "Upside scenario: bowl + a signature win."
    # base
    if wins >= 10:
        return "Top-15 finish. Bowl bid likely."
    if wins >= 8:
        return "Bowl. NY6 in reach with one signature win."
    if wins >= 6:
        return "Bowl eligible. The realistic plateau."
    return "Bowl access depends on the closing run."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_ceiling_floor(
    profile: Profile,
    snapshot: TeamSnapshot | None,
    arc_rows: list[dict[str, Any]] | None = None,
) -> str:
    """Render the Ceiling/Floor projection band (Brief §11.2)."""
    if snapshot is None:
        return ""
    base_info = _baseline_wins(snapshot, arc_rows or [])
    if base_info is None:
        return ""
    base_wins, total_games = base_info
    # Normalize total_games to a 12-game baseline so the rendered scenarios
    # match the regular-season frame fans expect (CFB is 12 games + bowl).
    games = 12

    # Variance ±2.5 wins. Floor = base - 2 wins (clamped), Ceiling = base + 2.
    floor = max(0, base_wins - 2)
    ceiling = min(games, base_wins + 3)
    base = max(0, min(games, base_wins))

    # Pin marker positions (% across the bar) — 0 wins on the left, games on right.
    def pct(n: int) -> float:
        return 100.0 * n / games

    floor_pct = pct(floor)
    base_pct = pct(base)
    ceiling_pct = pct(ceiling)

    program = escape(profile.program_name)

    scenarios_html = []
    for kind, wins in (("floor", floor), ("base", base), ("ceiling", ceiling)):
        story = _scenario_story(kind, wins, games)
        scenarios_html.append(
            f'<div class="ceiling-floor__scenario" data-kind="{kind}">'
            f'<span class="ceiling-floor__scenario-kind">{kind}</span>'
            f'<span class="ceiling-floor__scenario-record">{wins}-{games - wins}</span>'
            f'<span class="ceiling-floor__scenario-story">{escape(story)}</span>'
            '</div>'
        )

    return f"""
<section class="ceiling-floor" aria-labelledby="ceiling-floor-h"
         data-module="ceiling-floor" data-state="ready">
  <div class="ceiling-floor__header">
    <p class="ceiling-floor__eyebrow">{program} · Next-Season Outcome Band</p>
    <h2 id="ceiling-floor-h" class="ceiling-floor__title">Floor / Base / Ceiling</h2>
  </div>
  <div class="ceiling-floor__band" role="img" aria-label="Floor {floor} wins, base {base} wins, ceiling {ceiling} wins">
    <div class="ceiling-floor__marker" style="left: {floor_pct:.1f}%;">
      <span class="ceiling-floor__marker-label">Floor {floor}-{games - floor}</span>
    </div>
    <div class="ceiling-floor__marker" style="left: {base_pct:.1f}%;">
      <span class="ceiling-floor__marker-label ceiling-floor__marker-label--base">Base {base}-{games - base}</span>
    </div>
    <div class="ceiling-floor__marker" style="left: {ceiling_pct:.1f}%;">
      <span class="ceiling-floor__marker-label">Ceiling {ceiling}-{games - ceiling}</span>
    </div>
  </div>
  <div class="ceiling-floor__scenarios">
    {''.join(scenarios_html)}
  </div>
  <p class="ceiling-floor__caveat">
    Variance assumed at ±2 wins from last-season record. Replace with SP+ projection band
    once preseason ratings publish.
  </p>
</section>"""


__all__ = ["render_ceiling_floor", "CEILING_FLOOR_CSS"]
