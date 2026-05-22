"""Player Standing Rail — Sprint C from WORLD_CLASS_GAP_AUDIT_2026_05_22.

The single biggest UX move in `PLAYER_PAGE_WORLD_CLASS_BRIEF.md §7`.
Brief verbatim:

    "Player Standing replaces the Accolade Lens as the page's primary
     status hub. It answers the one question every fan walks in with:
     how good is this guy, actually, right now? One module, 17 rungs,
     same component for a walk-on and for the Heisman frontrunner."

Six perceptually distinct tiers, 17 rungs total:

    TIER 0 — Not on team       (R00-R01)
    TIER 1 — On the 2-deep     (R02-R04)
    TIER 2 — Starter           (R05-R07)
    TIER 3 — Recognized        (R08-R11)
    TIER 4 — Elite             (R12-R14)
    TIER 5 — Apex              (R15-R16)

The 5-second read (this module's MVP): full-width horizontal rail,
17 tick marks, filled gold marker at the current rung, faint ghost
marker at last season's rung, current rung's name in large type
above, tier-pill row below.

The 30-second read (tap a tier to zoom) and 5-minute read (rung
drawer with "Why he's here / What moves him up / down") are
deferred to Sprint C+1.

Data contract: the renderer accepts a `standing_rung` int (0-16)
plus optional `last_season_rung` int. Returns empty string when
`standing_rung` is None (the brief's honest empty-state for
players whose snap% / accolade data hasn't been ingested).

Public API:
    render_standing_rail(...) -> str
    STANDING_RAIL_CSS_BLOCK    -> str
    RUNG_NAMES                 -> tuple[str, ...]  (17 entries)
    TIER_BOUNDARIES            -> tuple[tuple[int, int, str], ...]
"""
from __future__ import annotations

from html import escape
from typing import Any


# ---------------------------------------------------------------------------
# Taxonomy (per brief §7.2)
# ---------------------------------------------------------------------------

RUNG_NAMES: tuple[str, ...] = (
    "Walk-on",                          # R00
    "Scout team",                       # R01
    "Deep reserve",                     # R02
    "Backup",                           # R03
    "Rotational",                       # R04
    "Part-time starter",                # R05
    "Starter",                          # R06
    "Impact starter",                   # R07
    "Watch-list name",                  # R08
    "All-Conference HM",                # R09
    "All-Conference 1st",               # R10
    "National watch",                   # R11
    "All-American",                     # R12
    "Consensus All-American",           # R13
    "Unanimous All-American",           # R14
    "POTY finalist",                    # R15
    "POTY winner",                      # R16
)

# (rung_lo, rung_hi inclusive, label, short_label)
TIER_BOUNDARIES: tuple[tuple[int, int, str, str], ...] = (
    (0,  1,  "Not on team",  "On-team"),
    (2,  4,  "On the 2-deep", "2-deep"),
    (5,  7,  "Starter",       "Starter"),
    (8,  11, "Recognized",    "Recognized"),
    (12, 14, "Elite",         "Elite"),
    (15, 16, "Apex",          "Apex"),
)

# Brief-mandated 5-second narrative per rung. Spelled out so the
# module always carries copy at every position.
RUNG_NARRATIVE: tuple[str, ...] = (
    "Signed but not on the depth chart.",
    "On the roster, building the body.",
    "On the roster, no meaningful snaps yet.",
    "Situational reps in specific packages.",
    "Rotational; 15-40% snap share.",
    "Part-time starter; injury fill or split room.",
    "Starter; >60% snap share, role unlocked.",
    "Impact starter; above-average for the conference.",
    "Named to a national award watch list.",
    "All-Conference second team or honorable mention.",
    "All-Conference first team.",
    "National watch — fringe All-America case.",
    "All-American on at least one NCAA-recognized selector.",
    "Consensus All-American (3+ of 5 selectors).",
    "Unanimous All-American (all 5 selectors).",
    "National Player-of-the-Year finalist.",
    "National Player-of-the-Year winner.",
)


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

STANDING_RAIL_CSS_BLOCK = """
/* Player Standing Rail — Sprint C (PLAYER_PAGE_WORLD_CLASS_BRIEF §7)
 *
 * Reads --team-accent / --team-accent-soft from the enclosing
 * .team-shell so the marker takes on the player's program brand pair.
 *
 * 5-second read only in v1: rail + tier pills + current-rung name +
 * 1-line narrative. Drawer / accolade tabs deferred.
 */

.standing-rail {
  --rail-track:       rgba(255, 255, 255, 0.08);
  --rail-tick:        rgba(255, 255, 255, 0.18);
  --rail-marker:      var(--team-accent, #c9a24a);
  --rail-marker-ring: var(--team-accent-soft, var(--team-accent, #c9a24a));
  --rail-ghost:       rgba(255, 255, 255, 0.22);
  --rail-tier-bg:     rgba(255, 255, 255, 0.03);

  display: grid;
  gap: clamp(12px, 1.5vw, 18px);
  padding: clamp(18px, 2.4vw, 28px) clamp(18px, 2.6vw, 32px);
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--rail-tick);
  border-radius: 16px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
}

.standing-rail__header {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.standing-rail__eyebrow {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted, #8a90a1);
  margin: 0;
}
.standing-rail__rung-name {
  font-family: 'Bebas Neue', 'Inter Display', 'Inter', system-ui, sans-serif;
  font-size: clamp(28px, 2.6vw + 12px, 40px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--fg-primary, #1a1a1a);
  margin: 0;
}
.standing-rail__rung-narrative {
  font-family: 'Source Serif Pro', Georgia, serif;
  font-size: clamp(14px, 0.4vw + 13px, 17px);
  line-height: 1.45;
  color: var(--fg-secondary, #4a4a4a);
  margin: 0;
  max-width: 64ch;
}

/* === The rail itself: 17 ticks === */

.standing-rail__rail {
  position: relative;
  display: grid;
  grid-template-columns: repeat(17, 1fr);
  align-items: center;
  height: 56px;
  padding: 0 6px;
}
.standing-rail__rail::before {
  content: "";
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--rail-track);
  border-radius: 2px;
  transform: translateY(-50%);
}
.standing-rail__tick {
  position: relative;
  height: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.standing-rail__tick::before {
  content: "";
  width: 2px;
  height: 12px;
  background: var(--rail-tick);
  border-radius: 1px;
}
.standing-rail__tick[data-current="true"]::before {
  width: 18px;
  height: 28px;
  background: var(--rail-marker);
  border-radius: 4px;
  box-shadow:
    0 0 0 4px color-mix(in oklab, var(--rail-marker) 24%, transparent),
    0 0 0 10px color-mix(in oklab, var(--rail-marker) 8%, transparent);
}
.standing-rail__tick[data-ghost="true"]::before {
  width: 8px;
  height: 18px;
  background: var(--rail-ghost);
  border-radius: 3px;
}
/* Make the tick at each tier boundary slightly taller to chunk the rail */
.standing-rail__tick[data-tier-end="true"]::after {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  right: -1px;
  width: 1px;
  background: var(--rail-tick);
}

.standing-rail__rung-num {
  position: absolute;
  bottom: -22px;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--fg-muted, #8a90a1);
}
.standing-rail__tick[data-current="true"] .standing-rail__rung-num {
  color: var(--rail-marker);
}

/* === Tier pill row === */

.standing-rail__tiers {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 4px;
  padding: 4px;
  background: var(--rail-tier-bg);
  border-radius: 10px;
}

.standing-rail__tier {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  text-align: center;
  padding: 8px 6px;
  color: var(--fg-muted, #8a90a1);
  background: transparent;
  border-radius: 8px;
  cursor: default;
  border: 1px solid transparent;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.standing-rail__tier[data-current="true"] {
  background: var(--rail-marker);
  color: #ffffff;
  border-color: var(--rail-marker);
}

@media (max-width: 540px) {
  .standing-rail__tiers {
    grid-template-columns: repeat(3, 1fr);
  }
  .standing-rail__rung-name { font-size: 26px; }
}

/* Empty state */
.standing-rail--empty {
  display: grid;
  gap: 4px;
  padding: 16px 18px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px dashed var(--rail-tick);
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
}
.standing-rail--empty p {
  margin: 0;
  font-family: 'Source Serif Pro', Georgia, serif;
  font-style: italic;
  color: var(--fg-muted, #8a90a1);
  font-size: 14px;
}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tier_for_rung(rung: int) -> int:
    """Return the tier index (0-5) containing the given rung."""
    for idx, (lo, hi, _, _) in enumerate(TIER_BOUNDARIES):
        if lo <= rung <= hi:
            return idx
    return 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_standing_rail(
    *,
    standing_rung: int | None,
    last_season_rung: int | None = None,
    season_label: str = "",
) -> str:
    """Render the Player Standing 17-rung rail.

    Returns empty-state HTML when ``standing_rung`` is None.
    """
    if standing_rung is None:
        return (
            '<section class="standing-rail--empty" aria-labelledby="standing-rail-empty-h" data-module="standing-rail" data-state="empty">'
            '<p id="standing-rail-empty-h">Standing settles in once snap-rate, depth-chart, or accolade data lands for this player.</p>'
            '</section>'
        )

    try:
        rung = max(0, min(16, int(standing_rung)))
    except (TypeError, ValueError):
        return (
            '<section class="standing-rail--empty" data-module="standing-rail" data-state="invalid">'
            '<p>Standing pending — non-integer rung in the state blob.</p>'
            '</section>'
        )

    ghost_rung: int | None = None
    if last_season_rung is not None:
        try:
            ghost_rung = max(0, min(16, int(last_season_rung)))
        except (TypeError, ValueError):
            ghost_rung = None
        if ghost_rung == rung:
            ghost_rung = None  # don't double-render at the same spot

    rung_name = RUNG_NAMES[rung]
    rung_narrative = RUNG_NARRATIVE[rung]
    season_eyebrow = (
        f"Player Standing · {escape(season_label)}"
        if season_label else "Player Standing"
    )
    if ghost_rung is not None and ghost_rung != rung:
        delta = rung - ghost_rung
        if delta > 0:
            season_eyebrow += f" · up {delta} {'rung' if delta == 1 else 'rungs'} from last season"
        else:
            season_eyebrow += f" · down {-delta} {'rung' if -delta == 1 else 'rungs'} from last season"

    tier_idx_current = _tier_for_rung(rung)
    tier_end_rungs = {hi for (_, hi, _, _) in TIER_BOUNDARIES[:-1]}

    ticks_html: list[str] = []
    for i in range(17):
        attrs: list[str] = []
        if i == rung:
            attrs.append('data-current="true"')
        if ghost_rung is not None and i == ghost_rung:
            attrs.append('data-ghost="true"')
        if i in tier_end_rungs:
            attrs.append('data-tier-end="true"')
        attrs.append(f'aria-label="R{i:02d} {escape(RUNG_NAMES[i])}"')
        attrs.append(f'title="R{i:02d} · {escape(RUNG_NAMES[i])}"')
        rung_num_html = (
            f'<span class="standing-rail__rung-num">R{i:02d}</span>'
            if i in (0, rung, 8, 16) else ""
        )
        ticks_html.append(
            f'<span class="standing-rail__tick" {" ".join(attrs)}>{rung_num_html}</span>'
        )

    tier_pills_html: list[str] = []
    for idx, (_, _, label, _short) in enumerate(TIER_BOUNDARIES):
        cur = ' data-current="true"' if idx == tier_idx_current else ""
        tier_pills_html.append(
            f'<span class="standing-rail__tier"{cur}>{escape(label)}</span>'
        )

    return f"""
<section class="standing-rail" aria-labelledby="standing-rail-h" data-module="standing-rail" data-state="ready">
  <div class="standing-rail__header">
    <p class="standing-rail__eyebrow">{season_eyebrow}</p>
    <h2 id="standing-rail-h" class="standing-rail__rung-name">{escape(rung_name)}</h2>
    <p class="standing-rail__rung-narrative">{escape(rung_narrative)}</p>
  </div>
  <div class="standing-rail__rail" role="img" aria-label="Player standing rail — currently at rung {rung}, {escape(rung_name)}">
    {''.join(ticks_html)}
  </div>
  <div class="standing-rail__tiers" role="list" aria-label="Standing tiers">
    {''.join(tier_pills_html)}
  </div>
</section>
"""


__all__ = [
    "render_standing_rail",
    "STANDING_RAIL_CSS_BLOCK",
    "RUNG_NAMES",
    "RUNG_NARRATIVE",
    "TIER_BOUNDARIES",
]
