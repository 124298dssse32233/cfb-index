"""Season Standing Rail — Brief §3.1 (TEAM_PAGE_WORLD_CLASS_BRIEF).

Team-page analog to the Player Standing 17-rung rail. Answers the
one question every fan walks in with at the program level: *Where is
this team in the national picture this season?*

Brief verbatim (§3.1):

    RUNG 0 — Not in FBS (FCS / D-II / D-III)
    RUNG 1 — FBS, sub-.500 / winless
    RUNG 2 — FBS, bowl-ineligible but competitive
    RUNG 3 — Bowl eligible (6+ wins, no ranking)
    RUNG 4 — Ranked (AP/Coaches, 25-16)
    RUNG 5 — Ranked (Top 15, 15-6)
    RUNG 6 — Ranked Top 5 / CFP contender
    RUNG 7 — CFP Quarterfinal / Semifinal
    RUNG 8 — CFP Championship game
    RUNG 9 — CFP National Champion

Placement cascade: AP rank → CFP committee ranking → SP+ top-25 →
win count + bowl eligibility. Updated Mondays in the production
pipeline.

UI: full-width horizontal rail with 10 ticks, filled marker at the
current rung, ghost marker at the start-of-season projection (when
available), accolade gold for the championship rung. One-line
narrative below the rail. Compatible visual grammar with the player
Standing Rail so they read as the same product surface.

Public API:
    render_season_standing_rail(...) -> str
    SEASON_STANDING_RAIL_CSS    -> str
    SEASON_RUNG_NAMES           -> tuple[str, ...]   (10 entries)
    SEASON_RUNG_NARRATIVE       -> tuple[str, ...]
    compute_season_rung(snapshot) -> int | None
"""
from __future__ import annotations

from html import escape
from typing import Any

from .data import TeamSnapshot
from .profile_loader import Profile


# ---------------------------------------------------------------------------
# Taxonomy (Brief §3.1)
# ---------------------------------------------------------------------------

SEASON_RUNG_NAMES: tuple[str, ...] = (
    "Sub-FBS",                          # R0
    "FBS sub-.500",                     # R1
    "FBS competitive",                  # R2
    "Bowl eligible",                    # R3
    "Ranked (25-16)",                   # R4
    "Top 15",                           # R5
    "CFP contender",                    # R6
    "CFP quarterfinal/semi",            # R7
    "CFP title game",                   # R8
    "National champion",                # R9
)

SEASON_RUNG_NARRATIVE: tuple[str, ...] = (
    "Outside FBS — non-Division-I football this season.",
    "Below .500 in FBS play. The rebuild bar.",
    "Competitive in FBS but not bowl-eligible — the close-loss tier.",
    "6+ wins, bowl access secured. The baseline of a successful FBS year.",
    "Ranked in the AP/Coaches polls, 16-25. National relevance achieved.",
    "Top 15 nationally. NY6-bowl conversation.",
    "Top 5 / CFP-contender. A real championship case is on the table.",
    "Made the CFP quarterfinal or semifinal — among the country's final 4-8.",
    "Reached the CFP National Championship game.",
    "National Champion. The peak.",
)

# Group rungs into tiers for the pill row below the rail.
# (lo, hi inclusive, label)
SEASON_TIER_BOUNDARIES: tuple[tuple[int, int, str], ...] = (
    (0, 0,  "Sub-FBS"),
    (1, 2,  "Building"),
    (3, 3,  "Bowl"),
    (4, 5,  "Ranked"),
    (6, 6,  "Contender"),
    (7, 9,  "Playoff"),
)


# ---------------------------------------------------------------------------
# Placement logic — Brief §3.1 cascade
# ---------------------------------------------------------------------------

def _rank_to_rung(rank: int | None) -> int | None:
    """Convert AP/CFP rank to a rung value. Returns None if no rank."""
    if rank is None:
        return None
    try:
        r = int(rank)
    except (TypeError, ValueError):
        return None
    if r <= 0:
        return None
    if r <= 5:
        return 6     # Top-5 → CFP contender
    if r <= 15:
        return 5     # 6-15 → Top 15
    if r <= 25:
        return 4     # 16-25 → Ranked
    return None      # outside top-25, fall through


def compute_season_rung(snapshot: TeamSnapshot | None) -> int | None:
    """Compute the season standing rung 0-9 from a TeamSnapshot.

    Cascade (Brief §3.1):
        1) CFP committee rank → maps to rung 4/5/6.
        2) AP rank → maps to rung 4/5/6.
        3) Coaches rank → maps to rung 4/5/6.
        4) Bowl eligibility (6+ wins) → rung 3.
        5) Wins ≥ losses → rung 2 (competitive).
        6) Wins < losses → rung 1 (sub-.500).
        7) Non-FBS level_code → rung 0.

    Returns None for empty / unknown snapshots. The renderer treats
    None as an empty state (don't draw).
    """
    if snapshot is None:
        return None

    # Level: non-FBS → R0. Anything else falls through to the cascade.
    level = (snapshot.level_code or "").upper()
    if level and level not in ("FBS",):
        return 0

    # 1) CFP committee rank (most authoritative late-season).
    rung = _rank_to_rung(snapshot.cfp_rank)
    if rung is not None:
        return rung

    # 2) AP rank
    rung = _rank_to_rung(snapshot.ap_rank)
    if rung is not None:
        return rung

    # 3) Coaches Poll
    rung = _rank_to_rung(snapshot.coaches_rank)
    if rung is not None:
        return rung

    # 4) Record-based fallback.
    wins = int(snapshot.wins or 0)
    losses = int(snapshot.losses or 0)
    if wins >= 6:
        return 3              # Bowl eligible, unranked
    if wins >= losses and (wins + losses) > 0:
        return 2              # Competitive
    if wins + losses == 0:
        return None           # No data yet — empty state, not "winless"
    return 1                  # Sub-.500


# ---------------------------------------------------------------------------
# CSS — adapted from the player Standing Rail for visual consistency
# ---------------------------------------------------------------------------

SEASON_STANDING_RAIL_CSS = """
/* Season Standing Rail — Brief §3.1
 *
 * Visual sibling of the player Standing Rail. Reads --accent-primary /
 * --accent-secondary from the enclosing body so each team page's rail
 * takes on the program brand pair.
 */

.season-standing-rail {
  --rail-track:        rgba(255, 255, 255, 0.08);
  --rail-tick:         rgba(255, 255, 255, 0.18);
  --rail-marker:       var(--accent-primary, #c9a24a);
  --rail-marker-soft:  var(--accent-secondary, var(--accent-primary, #c9a24a));
  --rail-ghost:        rgba(255, 255, 255, 0.22);
  --rail-tier-bg:      rgba(255, 255, 255, 0.03);
  --rail-champion:     #d4af37;

  display: grid;
  gap: clamp(12px, 1.5vw, 18px);
  padding: clamp(18px, 2.4vw, 28px) clamp(18px, 2.6vw, 32px);
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--stroke-default, var(--rail-tick));
  border-radius: 16px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
}

.season-standing-rail__header {
  display: grid;
  gap: 6px;
}
.season-standing-rail__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.season-standing-rail__rung-name {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(28px, 2.6vw + 12px, 40px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--fg-primary);
  margin: 0;
}
.season-standing-rail__rung-narrative {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: clamp(14px, 0.4vw + 13px, 17px);
  font-style: italic;
  line-height: 1.45;
  color: var(--fg-secondary);
  margin: 0;
  max-width: 64ch;
}

/* === The rail itself: 10 ticks === */

.season-standing-rail__rail {
  position: relative;
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  align-items: center;
  height: 56px;
  padding: 0 6px;
}
.season-standing-rail__rail::before {
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
.season-standing-rail__tick {
  position: relative;
  height: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.season-standing-rail__tick::before {
  content: "";
  width: 2px;
  height: 12px;
  background: var(--rail-tick);
  border-radius: 1px;
}
.season-standing-rail__tick[data-current="true"]::before {
  width: 18px;
  height: 28px;
  background: var(--rail-marker);
  border-radius: 4px;
  box-shadow:
    0 0 0 4px color-mix(in oklab, var(--rail-marker) 24%, transparent),
    0 0 0 10px color-mix(in oklab, var(--rail-marker) 8%, transparent);
}
.season-standing-rail__tick[data-ghost="true"]::before {
  width: 8px;
  height: 18px;
  background: var(--rail-ghost);
  border-radius: 3px;
}
/* Championship rung (R9) — accolade gold even when not current. */
.season-standing-rail__tick[data-rung="9"]::before {
  background: var(--rail-champion);
  width: 4px;
  height: 16px;
}
.season-standing-rail__tick[data-rung="9"][data-current="true"]::before {
  background: var(--rail-champion);
  box-shadow:
    0 0 0 4px color-mix(in oklab, var(--rail-champion) 32%, transparent),
    0 0 0 10px color-mix(in oklab, var(--rail-champion) 10%, transparent);
}
.season-standing-rail__rung-num {
  position: absolute;
  bottom: -22px;
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--fg-muted);
}
.season-standing-rail__tick[data-current="true"] .season-standing-rail__rung-num {
  color: var(--rail-marker);
}

/* === Tier pill row === */

.season-standing-rail__tiers {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 4px;
  padding: 4px;
  background: var(--rail-tier-bg);
  border-radius: 10px;
}
.season-standing-rail__tier {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  text-align: center;
  padding: 8px 6px;
  color: var(--fg-muted);
  background: transparent;
  border-radius: 8px;
  border: 1px solid transparent;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.season-standing-rail__tier[data-current="true"] {
  background: var(--rail-marker);
  color: #ffffff;
  border-color: var(--rail-marker);
}

@media (max-width: 640px) {
  .season-standing-rail__tiers {
    grid-template-columns: repeat(3, 1fr);
  }
  .season-standing-rail__rung-name { font-size: 26px; }
}

/* Empty state — drawn when compute_season_rung returns None */
.season-standing-rail--empty {
  display: grid;
  gap: 4px;
  padding: 16px 18px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px dashed var(--rail-tick);
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
}
.season-standing-rail--empty p {
  margin: 0;
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-style: italic;
  color: var(--fg-muted);
  font-size: 14px;
}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tier_for_rung(rung: int) -> int:
    """Return the tier-pill index containing the given rung."""
    for idx, (lo, hi, _) in enumerate(SEASON_TIER_BOUNDARIES):
        if lo <= rung <= hi:
            return idx
    return 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_season_standing_rail(
    profile: Profile,
    snapshot: TeamSnapshot | None,
    *,
    last_season_rung: int | None = None,
    projected_rung: int | None = None,
) -> str:
    """Render the team Season Standing 9-rung rail (Brief §3.1).

    Args:
        profile: Profile object for program-name escape and slug.
        snapshot: TeamSnapshot — drives the cascade. None → empty state.
        last_season_rung: Optional ghost marker at last year's rung.
        projected_rung: Optional ghost marker at start-of-season SP+ projection.
            Takes precedence over last_season_rung when both provided
            (start-of-season projection is the brief-specified ghost).

    Returns empty-state HTML when the rung can't be computed.
    """
    rung = compute_season_rung(snapshot)
    season_label = (
        str(snapshot.season_year) if snapshot and snapshot.season_year else ""
    )

    if rung is None:
        eyebrow = (
            f"Season Standing · {escape(season_label)}"
            if season_label else "Season Standing"
        )
        return (
            '<section class="season-standing-rail--empty" '
            'aria-labelledby="season-standing-rail-empty-h" '
            'data-module="season-standing-rail" data-state="empty">'
            f'<p class="season-standing-rail__eyebrow" id="season-standing-rail-empty-h">{eyebrow}</p>'
            '<p>Season standing settles in once games are played and rankings publish.</p>'
            '</section>'
        )

    ghost_rung: int | None = projected_rung if projected_rung is not None else last_season_rung
    if ghost_rung is not None:
        try:
            ghost_rung = max(0, min(9, int(ghost_rung)))
        except (TypeError, ValueError):
            ghost_rung = None
        if ghost_rung == rung:
            ghost_rung = None  # don't double-render on the same tick

    rung_name = SEASON_RUNG_NAMES[rung]
    rung_narrative = SEASON_RUNG_NARRATIVE[rung]

    eyebrow_bits: list[str] = ["Season Standing"]
    if season_label:
        eyebrow_bits.append(escape(season_label))
    if snapshot is not None:
        w, l = int(snapshot.wins or 0), int(snapshot.losses or 0)
        if (w + l) > 0:
            eyebrow_bits.append(f"{w}-{l}")
        rank_chips: list[str] = []
        if snapshot.cfp_rank:
            rank_chips.append(f"CFP #{int(snapshot.cfp_rank)}")
        if snapshot.ap_rank:
            rank_chips.append(f"AP #{int(snapshot.ap_rank)}")
        if rank_chips:
            eyebrow_bits.append(" / ".join(rank_chips))
    if ghost_rung is not None and projected_rung is not None:
        delta = rung - ghost_rung
        if delta > 0:
            eyebrow_bits.append(
                f"up {delta} {'rung' if delta == 1 else 'rungs'} from preseason"
            )
        elif delta < 0:
            eyebrow_bits.append(
                f"down {-delta} {'rung' if -delta == 1 else 'rungs'} from preseason"
            )
        else:
            eyebrow_bits.append("matched preseason projection")
    elif ghost_rung is not None and last_season_rung is not None:
        delta = rung - ghost_rung
        if delta > 0:
            eyebrow_bits.append(
                f"up {delta} {'rung' if delta == 1 else 'rungs'} year-over-year"
            )
        elif delta < 0:
            eyebrow_bits.append(
                f"down {-delta} {'rung' if -delta == 1 else 'rungs'} year-over-year"
            )

    eyebrow = " · ".join(eyebrow_bits)

    tier_idx_current = _tier_for_rung(rung)

    ticks_html: list[str] = []
    for i in range(10):
        attrs: list[str] = [f'data-rung="{i}"']
        if i == rung:
            attrs.append('data-current="true"')
        if ghost_rung is not None and i == ghost_rung:
            attrs.append('data-ghost="true"')
        attrs.append(f'aria-label="Rung {i} — {escape(SEASON_RUNG_NAMES[i])}"')
        attrs.append(f'title="R{i} · {escape(SEASON_RUNG_NAMES[i])}"')
        # Label every rung number — only 10 of them, no crowding.
        rung_num_html = f'<span class="season-standing-rail__rung-num">R{i}</span>'
        ticks_html.append(
            f'<span class="season-standing-rail__tick" {" ".join(attrs)}>{rung_num_html}</span>'
        )

    tier_pills_html: list[str] = []
    for idx, (_, _, label) in enumerate(SEASON_TIER_BOUNDARIES):
        cur = ' data-current="true"' if idx == tier_idx_current else ""
        tier_pills_html.append(
            f'<span class="season-standing-rail__tier"{cur}>{escape(label)}</span>'
        )

    program = escape(profile.program_name)

    return f"""
<section class="season-standing-rail" aria-labelledby="season-standing-rail-h"
         data-module="season-standing-rail" data-state="ready">
  <div class="season-standing-rail__header">
    <p class="season-standing-rail__eyebrow">{eyebrow}</p>
    <h2 id="season-standing-rail-h" class="season-standing-rail__rung-name">{escape(rung_name)}</h2>
    <p class="season-standing-rail__rung-narrative">{program}: {escape(rung_narrative)}</p>
  </div>
  <div class="season-standing-rail__rail" role="img"
       aria-label="Season standing rail — {program} at rung {rung}, {escape(rung_name)}">
    {''.join(ticks_html)}
  </div>
  <div class="season-standing-rail__tiers" role="list" aria-label="Season standing tiers">
    {''.join(tier_pills_html)}
  </div>
</section>"""


__all__ = [
    "render_season_standing_rail",
    "compute_season_rung",
    "SEASON_STANDING_RAIL_CSS",
    "SEASON_RUNG_NAMES",
    "SEASON_RUNG_NARRATIVE",
    "SEASON_TIER_BOUNDARIES",
]
