"""Aspiration Ladder — Brief Part III §33.4.

Brief verbatim:
    "Every team page gets an aspiration ladder. 3-5 rungs. Each rung:
     outcome name, realistic odds, one-sentence program-historic
     context. Rungs that are meaningfully out of reach render dimmed
     with 'locked' annotation — dreams acknowledged, not promised."

Brief §33.2 also specifies tier-aware adaptation:

    Contender (T1-T2)     Mid (T3-T5)             Non-contender (T6-T10)
    Semifinal → champion  8 wins → conf title     6 wins → exceed last
                          → CFP buzz              year → statement year

This module renders the ladder chrome with tier-defaulted rung
labels. Per-program overrides can come from
profile.frontmatter.aspiration_ladder (a list of rung dicts) when
authored; otherwise the tier-default applies.

Public API:
    render_aspiration_ladder(profile, snapshot=None) -> str
    ASPIRATION_LADDER_CSS                              -> str
"""
from __future__ import annotations

import html
from typing import Any

from .profile_loader import Profile


ASPIRATION_LADDER_CSS = """
/* Aspiration Ladder — Brief Part III §33.4 */
.aspiration-ladder {
  display: grid;
  gap: var(--sp-3, 12px);
  padding: var(--sp-4, 18px) var(--sp-5, 22px);
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--stroke-default);
  border-radius: var(--radius-md);
  margin-bottom: clamp(20px, 3vw, 32px);
}
.aspiration-ladder__header {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px 18px;
}
.aspiration-ladder__title {
  font-family: var(--font-display);
  font-size: clamp(20px, 1.5vw + 10px, 26px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--fg-primary);
  margin: 0;
}
.aspiration-ladder__eyebrow {
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.aspiration-ladder__rungs {
  display: grid;
  gap: 8px;
}
.aspiration-ladder__rung {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px 16px;
  align-items: baseline;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--stroke-subtle);
  border-left: 4px solid var(--accent-primary, #c9a24a);
  border-radius: 8px;
}
.aspiration-ladder__rung--locked {
  opacity: 0.55;
  border-left-style: dashed;
}
.aspiration-ladder__rung-name {
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  font-weight: 700;
  color: var(--fg-primary);
}
.aspiration-ladder__rung-odds {
  font-family: var(--font-mono);
  font-size: var(--fs-label);
  font-weight: 600;
  color: var(--accent-primary, #c9a24a);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.aspiration-ladder__rung--locked .aspiration-ladder__rung-odds {
  color: var(--fg-muted);
}
.aspiration-ladder__rung-context {
  grid-column: 1 / -1;
  font-family: var(--font-serif);
  font-size: var(--fs-label);
  font-style: italic;
  color: var(--fg-secondary);
  line-height: 1.45;
}
.aspiration-ladder__locked-chip {
  display: inline-block;
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--fg-muted);
  font-family: var(--font-sans);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  border-radius: 999px;
  margin-left: 6px;
}
"""


# Tier-default ladders per brief §33.2. (name, odds_default, context, locked_for_tier_above)
TIER_DEFAULT_LADDERS: dict[int, list[tuple[str, str, str, bool]]] = {
    # Tier 1 — Blue Blood
    1: [
        ("CFP appearance",  "—",  "The floor for the program's modern identity.",          False),
        ("CFP semifinal",   "—",  "Reaching the semi is the era-relevant peak.",            False),
        ("Title game",      "—",  "The trip to the title game frames every recruiting cycle.", False),
        ("National champion","—", "Won twice in the last decade. The bar is the bar.",      False),
    ],
    # Tier 2 — Heritage Power
    2: [
        ("9-win season",    "—",  "The benchmark recent successors are graded against.",   False),
        ("Conference title","—",  "The structural peak the modern era is built for.",      False),
        ("NY6 bowl",        "—",  "Above the bowl tier — the validation bowl.",            False),
        ("CFP appearance",  "—",  "Plausible in a strong year; the dream rung.",           True),
    ],
    # Tier 3 — Modern Power
    3: [
        ("8 wins",          "—",  "Above the program's recent baseline.",                  False),
        ("Beat a top-10 opponent", "—", "Statement win that reshapes recruiting.",          False),
        ("Conference championship game appearance", "—", "Plausible breakthrough.",        False),
        ("NY6 bowl",        "—",  "Beyond modern reach without a transformative year.",    True),
    ],
    # Tier 4 — Power-5 Aspirer
    4: [
        ("Bowl eligibility (6 wins)", "—", "The realistic floor for a successful season.",  False),
        ("Beat the cross-state rival","—", "Calendar-defining outcome for the fanbase.",    False),
        ("8 wins",          "—",  "Has happened in the last decade; would feel like a leap.", False),
        ("Conference title","—",  "Generational stretch goal.",                            True),
    ],
    # Tier 5 — Mid-major Standard
    5: [
        ("Bowl eligibility (6 wins)", "—", "Baseline for a successful season.",              False),
        ("Beat an in-state rival",    "—", "The headline result for the fanbase.",          False),
        ("Conference division title", "—", "Realistic stretch goal.",                      False),
        ("9-win season",    "—",  "Possible; would compound recruiting next cycle.",       True),
    ],
}
# Default for tiers >= 6
DEFAULT_LADDER_LOW_TIER: list[tuple[str, str, str, bool]] = [
    ("First bowl since program-stated year", "—", "The baseline goal — bowl access matters.", False),
    ("Beat a rival",     "—", "The narrative win the season is graded by.",                False),
    ("Statement year",   "—", "Exceed last season by 2+ wins.",                            False),
    ("Conference championship", "—", "Out of reach without a transformative year.",        True),
]


def _ladder_for_profile(profile: Profile) -> list[tuple[str, str, str, bool]]:
    """Resolve the ladder list — profile override if present, else tier default."""
    fm = profile.frontmatter or {}
    custom = fm.get("aspiration_ladder")
    if isinstance(custom, list) and custom:
        out: list[tuple[str, str, str, bool]] = []
        for entry in custom:
            if isinstance(entry, dict):
                name = str(entry.get("name") or entry.get("outcome") or "")
                odds = str(entry.get("odds") or entry.get("probability") or "—")
                ctx = str(entry.get("context") or "")
                locked = bool(entry.get("locked", False))
                if name:
                    out.append((name, odds, ctx, locked))
        if out:
            return out
    tier = profile.program_tier or 5
    return TIER_DEFAULT_LADDERS.get(tier, DEFAULT_LADDER_LOW_TIER)


def render_aspiration_ladder(profile: Profile, snapshot: Any = None) -> str:
    """Render the aspiration ladder for a profile. Brief Part III §33.4."""
    rungs = _ladder_for_profile(profile)
    if not rungs:
        return ""
    rungs_html: list[str] = []
    for name, odds, ctx, locked in rungs:
        cls = "aspiration-ladder__rung"
        if locked:
            cls += " aspiration-ladder__rung--locked"
        locked_chip = (
            '<span class="aspiration-ladder__locked-chip">Locked</span>'
            if locked else ""
        )
        ctx_html = (
            f'<p class="aspiration-ladder__rung-context">{html.escape(ctx)}</p>'
            if ctx else ""
        )
        rungs_html.append(
            f'<div class="{cls}">'
            f'<span class="aspiration-ladder__rung-name">{html.escape(name)}{locked_chip}</span>'
            f'<span class="aspiration-ladder__rung-odds">{html.escape(odds)}</span>'
            f'{ctx_html}'
            f'</div>'
        )
    program = html.escape(profile.program_name)
    return f"""<section class="aspiration-ladder" aria-labelledby="aspiration-ladder-h">
  <div class="aspiration-ladder__header">
    <h2 id="aspiration-ladder-h" class="aspiration-ladder__title">Aspiration Ladder</h2>
    <p class="aspiration-ladder__eyebrow">Brief Part III §33.4 · {program}</p>
  </div>
  <div class="aspiration-ladder__rungs">
    {''.join(rungs_html)}
  </div>
</section>"""


__all__ = [
    "render_aspiration_ladder",
    "ASPIRATION_LADDER_CSS",
    "TIER_DEFAULT_LADDERS",
]
