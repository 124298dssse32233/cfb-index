"""Program Prestige Bar — Brief §3.2 (TEAM_PAGE_WORLD_CLASS_BRIEF).

The slower-moving, era-weighted sibling of the Season Standing rail.
Where Season Standing answers "where are you this year," Prestige
answers "what kind of program is this, historically?"

Brief verbatim (§3.2):

    PRESTIGE TIER 1 — Regional Program (limited national profile)
    PRESTIGE TIER 2 — Mid-Major Contender (G5 force, occasional national attention)
    PRESTIGE TIER 3 — Power Program (consistent P4 presence, regional brand)
    PRESTIGE TIER 4 — National Program (sustained top-25 expectations)
    PRESTIGE TIER 5 — Blue Blood (generational elite — Alabama, Ohio State, etc.)
    PRESTIGE TIER 6 — Dynasty Active (currently executing a multi-year elite run)
    PRESTIGE TIER 7 — All-Time Great Era (historical peak, may be past)

UI brief: compact horizontal tier bar (not a 17-rung rail). Tier name
in large display type ("BLUE BLOOD"). Sub-line acknowledges historical
peak — "Historical peak: Tier 6 / Dynasty Active (2015–2021 Saban run).
Current tier: Tier 5." Honest nuance: a Blue Blood can sit at T5
without currently being in a dynasty.

Data sources (precedence):
    1) profile.frontmatter.prestige_tier  — explicit override
    2) profile.frontmatter.prestige_historical_peak — peak ghost
    3) Translation from profile.program_tier (1-10 internal scale).

Public API:
    render_program_prestige_bar(profile) -> str
    PROGRAM_PRESTIGE_BAR_CSS              -> str
    PRESTIGE_TIER_NAMES                   -> tuple[str, ...] (8 entries; idx 0 unused)
    PRESTIGE_TIER_NARRATIVE               -> tuple[str, ...]
"""
from __future__ import annotations

from html import escape
from typing import Any

from .profile_loader import Profile


# ---------------------------------------------------------------------------
# Taxonomy (Brief §3.2)
# ---------------------------------------------------------------------------

# Index 0 is unused so tier 1..7 reads naturally as index 1..7.
PRESTIGE_TIER_NAMES: tuple[str, ...] = (
    "",                          # 0 unused
    "Regional",                  # 1
    "Mid-Major Contender",       # 2
    "Power Program",             # 3
    "National Program",          # 4
    "Blue Blood",                # 5
    "Dynasty Active",            # 6
    "All-Time Great Era",        # 7
)

PRESTIGE_TIER_SHORT: tuple[str, ...] = (
    "", "Regional", "Mid-Major", "Power", "National",
    "Blue Blood", "Dynasty", "All-Time",
)

PRESTIGE_TIER_NARRATIVE: tuple[str, ...] = (
    "",
    "Regional program — limited national profile.",
    "Mid-Major Contender — G5 force with occasional national attention.",
    "Power Program — consistent P4 presence and regional brand strength.",
    "National Program — sustained top-25 expectations across cycles.",
    "Blue Blood — generational elite. The standard the sport measures itself against.",
    "Dynasty Active — currently executing a multi-year elite run.",
    "All-Time Great Era — historical peak. May be past, never displaced.",
)


# Translation from profile.program_tier (internal 1-10) to Brief prestige tier (1-7).
# The internal scale runs Blue Blood (1) → Heritage Power (2) → Modern Power (3)
# → P5 Aspirer (4) → Mid-major Standard (5) → Mid-major (6-7) → Group of 5 (8-10).
# The brief's 7-tier prestige scale runs the *opposite* direction (Regional → Blue Blood).
PROGRAM_TIER_TO_PRESTIGE: dict[int, int] = {
    1:  5,    # Blue Blood internal → Blue Blood brief
    2:  4,    # Heritage Power      → National Program
    3:  3,    # Modern Power        → Power Program
    4:  3,    # P5 Aspirer          → Power Program
    5:  2,    # Mid-major Standard  → Mid-Major Contender
    6:  2,
    7:  2,
    8:  1,    # Group of 5 low     → Regional
    9:  1,
    10: 1,
}


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

PROGRAM_PRESTIGE_BAR_CSS = """
/* Program Prestige Bar — Brief §3.2
 *
 * Sibling of the Season Standing rail. Reads accent tokens from the
 * enclosing body so each program brand colors the active tier pill.
 */

.program-prestige-bar {
  --pp-track:        rgba(255, 255, 255, 0.08);
  --pp-tier-bg:      rgba(255, 255, 255, 0.02);
  --pp-marker:       var(--accent-primary, #c9a24a);
  --pp-marker-soft:  var(--accent-secondary, var(--accent-primary, #c9a24a));
  --pp-ghost:        rgba(255, 255, 255, 0.22);

  display: grid;
  gap: clamp(12px, 1.5vw, 18px);
  padding: clamp(18px, 2.4vw, 28px) clamp(18px, 2.6vw, 32px);
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--stroke-default, var(--pp-track));
  border-radius: 16px;
  margin-bottom: clamp(20px, 3vw, 32px);
}

.program-prestige-bar__header {
  display: grid;
  gap: 6px;
}
.program-prestige-bar__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.program-prestige-bar__tier-name {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(32px, 3vw + 14px, 56px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--fg-primary);
  margin: 0;
}
.program-prestige-bar__narrative {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: clamp(14px, 0.4vw + 13px, 17px);
  font-style: italic;
  line-height: 1.45;
  color: var(--fg-secondary);
  margin: 0;
  max-width: 64ch;
}
.program-prestige-bar__peak {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 13px;
  color: var(--fg-secondary);
  margin: 0;
}
.program-prestige-bar__peak strong {
  color: var(--fg-primary);
  font-weight: 700;
}

/* === Tier-bar: 7 segments === */

.program-prestige-bar__bar {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
  padding: 5px;
  background: var(--pp-tier-bg);
  border-radius: 12px;
  border: 1px solid var(--pp-track);
}
.program-prestige-bar__segment {
  position: relative;
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  text-align: center;
  padding: 12px 6px 26px 6px;
  color: var(--fg-muted);
  background: transparent;
  border-radius: 8px;
  border: 1px solid transparent;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-height: 56px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: center;
  gap: 4px;
}
.program-prestige-bar__segment-num {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--fg-muted);
  opacity: 0.6;
}
.program-prestige-bar__segment[data-current="true"] {
  background: var(--pp-marker);
  color: #ffffff;
  border-color: var(--pp-marker);
}
.program-prestige-bar__segment[data-current="true"] .program-prestige-bar__segment-num {
  color: rgba(255,255,255,0.85);
  opacity: 1;
}
.program-prestige-bar__segment[data-peak="true"]:not([data-current="true"]) {
  background: color-mix(in oklab, var(--pp-marker) 14%, transparent);
  border-color: color-mix(in oklab, var(--pp-marker) 50%, transparent);
  color: var(--fg-primary);
}
.program-prestige-bar__segment[data-peak="true"]:not([data-current="true"])::after {
  content: "PEAK";
  position: absolute;
  bottom: 4px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 8px;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: var(--pp-marker);
}

@media (max-width: 640px) {
  .program-prestige-bar__tier-name { font-size: 32px; }
  .program-prestige-bar__bar {
    grid-template-columns: repeat(4, 1fr);
    grid-auto-rows: auto;
  }
}

.program-prestige-bar--empty {
  display: none; /* every team renders the bar; only override fully missing */
}
"""


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

def _resolve_prestige_tier(profile: Profile) -> int:
    """Resolve the prestige tier (1-7) for a profile.

    Order:
        1) frontmatter.prestige_tier        — explicit override
        2) PROGRAM_TIER_TO_PRESTIGE[profile.program_tier]
        3) Fallback: Tier 2 (Mid-Major Contender) for unknown.
    """
    fm = profile.frontmatter or {}
    custom = fm.get("prestige_tier")
    if custom is not None:
        try:
            v = int(custom)
            if 1 <= v <= 7:
                return v
        except (TypeError, ValueError):
            pass
    pt = profile.program_tier
    if pt is not None:
        try:
            return PROGRAM_TIER_TO_PRESTIGE.get(int(pt), 2)
        except (TypeError, ValueError):
            pass
    return 2


def _resolve_peak(profile: Profile, current_tier: int) -> tuple[int | None, str]:
    """Resolve the historical peak tier + label.

    Frontmatter shape:
        prestige_historical_peak:
          tier: 6
          label: "2015-2021 Saban dynasty"

    Returns (peak_tier_or_None, label_string). Peak only renders if it
    differs from the current tier — otherwise it's noise.
    """
    fm = profile.frontmatter or {}
    peak = fm.get("prestige_historical_peak")
    if isinstance(peak, dict):
        try:
            tier = int(peak.get("tier")) if peak.get("tier") is not None else None
        except (TypeError, ValueError):
            tier = None
        label = str(peak.get("label") or "")
        if tier is not None and 1 <= tier <= 7 and tier != current_tier:
            return tier, label
    return None, ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_program_prestige_bar(profile: Profile) -> str:
    """Render the 7-tier Program Prestige bar (Brief §3.2)."""
    tier = _resolve_prestige_tier(profile)
    peak_tier, peak_label = _resolve_peak(profile, tier)
    tier_name = PRESTIGE_TIER_NAMES[tier]
    tier_narrative = PRESTIGE_TIER_NARRATIVE[tier]

    segments_html: list[str] = []
    for i in range(1, 8):
        attrs: list[str] = [f'data-tier="{i}"']
        if i == tier:
            attrs.append('data-current="true"')
        if peak_tier is not None and i == peak_tier:
            attrs.append('data-peak="true"')
        attrs.append(
            f'title="Tier {i} · {escape(PRESTIGE_TIER_NAMES[i])}"'
        )
        segments_html.append(
            f'<div class="program-prestige-bar__segment" {" ".join(attrs)}>'
            f'<span class="program-prestige-bar__segment-num">T{i}</span>'
            f'<span>{escape(PRESTIGE_TIER_SHORT[i])}</span>'
            f'</div>'
        )

    program = escape(profile.program_name)
    peak_line = ""
    if peak_tier is not None:
        peak_name = escape(PRESTIGE_TIER_NAMES[peak_tier])
        peak_suffix = f" ({escape(peak_label)})" if peak_label else ""
        peak_line = (
            f'<p class="program-prestige-bar__peak">'
            f'Historical peak: <strong>Tier {peak_tier} · {peak_name}</strong>{peak_suffix}. '
            f'Current tier: Tier {tier}.'
            f'</p>'
        )

    return f"""
<section class="program-prestige-bar" aria-labelledby="program-prestige-bar-h"
         data-module="program-prestige-bar" data-state="ready">
  <div class="program-prestige-bar__header">
    <p class="program-prestige-bar__eyebrow">Program Prestige · {program}</p>
    <h2 id="program-prestige-bar-h" class="program-prestige-bar__tier-name">{escape(tier_name)}</h2>
    <p class="program-prestige-bar__narrative">{escape(tier_narrative)}</p>
    {peak_line}
  </div>
  <div class="program-prestige-bar__bar" role="list" aria-label="Program prestige tiers">
    {''.join(segments_html)}
  </div>
</section>"""


__all__ = [
    "render_program_prestige_bar",
    "PROGRAM_PRESTIGE_BAR_CSS",
    "PRESTIGE_TIER_NAMES",
    "PRESTIGE_TIER_SHORT",
    "PRESTIGE_TIER_NARRATIVE",
    "PROGRAM_TIER_TO_PRESTIGE",
]
