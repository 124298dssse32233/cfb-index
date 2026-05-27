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
.ceiling-floor__marker:first-child .ceiling-floor__marker-label {
  transform: translateX(0);
}
.ceiling-floor__marker:last-child .ceiling-floor__marker-label {
  transform: translateX(-100%);
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
  .ceiling-floor {
    border-radius: 8px;
  }
  .ceiling-floor__marker-label {
    font-size: 8px;
    letter-spacing: 0.04em;
  }
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


_PATH_DESCRIPTOR = {
    "national_champion": "National champion.",
    "cfp_title": "CFP title game.",
    "cfp_semifinal": "CFP semifinal.",
    "cfp_quarterfinal": "CFP quarterfinal.",
    "cfp_first_round": "CFP first round.",
    "bowl": "Bowl game.",
    "none": "No postseason.",
}


def _projection_story(kind: str, row: dict[str, Any]) -> str:
    """Story line for a projection-backed scenario.

    Prefers the deterministic path_label/rationale from the truth layer so the
    prose tracks the actual projected postseason path (which can extend past 12
    games), rather than the win-count heuristic.
    """
    path = row.get("bowl_or_cfp_path") or "none"
    ccg_win = row.get("conference_title_result") == "win"
    desc = _PATH_DESCRIPTOR.get(path, "")
    if ccg_win and path not in ("none", "bowl"):
        return f"Conference title + {desc[:1].lower()}{desc[1:]}" if desc else "Conference title."
    if ccg_win:
        return "Conference title game appearance."
    return desc or _scenario_story(kind, int(row.get("final_wins") or 0), 12)


def _scenarios_from_projection(
    season_path: dict[str, dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Build floor/base/ceiling render rows from a projection set.

    Returns None unless all three scenarios are present, so a partial set never
    renders a misleading band.
    """
    out: list[dict[str, Any]] = []
    for kind in ("floor", "base", "ceiling"):
        row = season_path.get(kind)
        if not row:
            return None
        fw = int(row.get("final_wins") or 0)
        fl = int(row.get("final_losses") or 0)
        ft = int(row.get("final_ties") or 0)
        out.append({
            "kind": kind,
            "wins": fw,
            "losses": fl,
            "ties": ft,
            "games": fw + fl + ft,
            "story": _projection_story(kind, row),
        })
    return out


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
    season_path: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Render the Ceiling/Floor projection band (Brief §11.2).

    When a deterministic season-path projection set is supplied (the
    team-preview truth layer, Milestone A/B), the band uses final-season-aware
    records that can exceed 12 games — a ceiling can show e.g. 15-1 for a
    projected national-title run (regular season + conference title + CFP).
    Otherwise it falls back to the ±2-win heuristic off last season's record.
    """
    if snapshot is None:
        return ""

    scenarios = _scenarios_from_projection(season_path) if season_path else None
    projection_backed = scenarios is not None

    if scenarios is None:
        base_info = _baseline_wins(snapshot, arc_rows or [])
        if base_info is None:
            return ""
        base_wins, _ = base_info
        # Heuristic fallback: normalise to a 12-game regular-season frame.
        games = 12
        floor = max(0, base_wins - 2)
        ceiling = min(games, base_wins + 3)
        base = max(0, min(games, base_wins))
        scenarios = [
            {"kind": "floor", "wins": floor, "losses": games - floor, "ties": 0,
             "games": games, "story": _scenario_story("floor", floor, games)},
            {"kind": "base", "wins": base, "losses": games - base, "ties": 0,
             "games": games, "story": _scenario_story("base", base, games)},
            {"kind": "ceiling", "wins": ceiling, "losses": games - ceiling, "ties": 0,
             "games": games, "story": _scenario_story("ceiling", ceiling, games)},
        ]

    # Band scale: widest projected game total (>=12) so a deep-CFP ceiling has
    # room past the regular-season frame. Markers position by wins on that scale.
    scale = max(12, max(s["games"] for s in scenarios))

    def pct(n: int) -> float:
        return 100.0 * n / scale if scale else 0.0

    by_kind = {s["kind"]: s for s in scenarios}
    floor_s, base_s, ceiling_s = by_kind["floor"], by_kind["base"], by_kind["ceiling"]

    def record(s: dict[str, Any]) -> str:
        return f'{s["wins"]}-{s["losses"]}-{s["ties"]}' if s["ties"] else f'{s["wins"]}-{s["losses"]}'

    program = escape(profile.program_name)

    scenarios_html = []
    for s in scenarios:
        scenarios_html.append(
            f'<div class="ceiling-floor__scenario" data-kind="{s["kind"]}">'
            f'<span class="ceiling-floor__scenario-kind">{s["kind"]}</span>'
            f'<span class="ceiling-floor__scenario-record">{record(s)}</span>'
            f'<span class="ceiling-floor__scenario-story">{escape(s["story"])}</span>'
            '</div>'
        )

    if projection_backed:
        caveat = (
            "Final-season-aware projection: floor / base / ceiling include "
            "conference title and CFP games where the model supports them, so "
            "a ceiling can exceed a 12-game regular season."
        )
    else:
        caveat = (
            "Variance assumed at ±2 wins from last-season record. Replace "
            "with the season-path projection once preview data is built."
        )

    return f"""
<section class="ceiling-floor" aria-labelledby="ceiling-floor-h"
         data-module="ceiling-floor" data-state="ready"
         data-source="{'projection' if projection_backed else 'heuristic'}">
  <div class="ceiling-floor__header">
    <p class="ceiling-floor__eyebrow">{program} · Next-Season Outcome Band</p>
    <h2 id="ceiling-floor-h" class="ceiling-floor__title">Floor / Base / Ceiling</h2>
  </div>
  <div class="ceiling-floor__band" role="img" aria-label="Floor {record(floor_s)}, base {record(base_s)}, ceiling {record(ceiling_s)}">
    <div class="ceiling-floor__marker" style="left: {pct(floor_s['wins']):.1f}%;">
      <span class="ceiling-floor__marker-label">Floor {record(floor_s)}</span>
    </div>
    <div class="ceiling-floor__marker" style="left: {pct(base_s['wins']):.1f}%;">
      <span class="ceiling-floor__marker-label ceiling-floor__marker-label--base">Base {record(base_s)}</span>
    </div>
    <div class="ceiling-floor__marker" style="left: {pct(ceiling_s['wins']):.1f}%;">
      <span class="ceiling-floor__marker-label">Ceiling {record(ceiling_s)}</span>
    </div>
  </div>
  <div class="ceiling-floor__scenarios">
    {''.join(scenarios_html)}
  </div>
  <p class="ceiling-floor__caveat">
    {escape(caveat)}
  </p>
</section>"""


__all__ = ["render_ceiling_floor", "CEILING_FLOOR_CSS"]
