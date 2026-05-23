"""Player Standing 17-rung Rail — Brief §7.

The single biggest UX move in the Player Brief — replaces the original
Accolade Lens. Six tiers, seventeen rungs from R00 walk-on to R16
Heisman winner. One module answers the question every fan walks in
with: "how good is this guy, actually, right now?"

Tier structure (per brief):
  Tier 1: Floor                R00 — Walk-on
                               R01 — Backup
                               R02 — Rotation
  Tier 2: Established          R03 — Starter
                               R04 — Regular contributor
  Tier 3: Quality starter      R05 — Solid starter
                               R06 — Quality starter
  Tier 4: All-Conference       R07 — All-Conference 2nd team
                               R08 — All-Conference 1st team
  Tier 5: National recognition R09 — All-American 3rd team
                               R10 — All-American 2nd team
                               R11 — All-American 1st team
  Tier 6: National honors      R12 — Position-of-the-Year
                               R13 — Watch-list honoree
                               R14 — POTY finalist
                               R15 — Heisman finalist
                               R16 — Heisman winner

The rung_id is computed elsewhere (often present in player_data as
"standing_rung"). This module renders the visualization.

Public API:
    render_standing_rail(standing_rung, player_name) -> str
    STANDING_RAIL_CSS                                -> str
"""
from __future__ import annotations

from html import escape


STANDING_RAIL_CSS = """
/* Player Standing 17-rung Rail */
.player-standing {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.player-standing__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 12px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
}
.player-standing__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted-foreground, var(--fg-muted, #666));
  margin: 0;
}
.player-standing__tier-label {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  padding: 3px 9px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--accent-primary, #d1a23a) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent-primary, #d1a23a) 30%, transparent);
}
.player-standing__rung-label {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(22px, 1.6vw + 8px, 30px);
  letter-spacing: 0.02em;
  color: var(--foreground, var(--fg-primary, #222));
  margin: 0 0 4px 0;
  line-height: 1;
}
.player-standing__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  font-style: italic;
  line-height: 1.4;
  color: var(--muted-foreground, var(--fg-secondary, #666));
  margin: 0 0 12px 0;
  max-width: 56ch;
}
.player-standing__rail {
  display: flex;
  gap: 3px;
  align-items: stretch;
  margin-top: 8px;
}
.player-standing__rung {
  flex: 1;
  min-width: 0;
  height: 14px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.08);
  position: relative;
}
.player-standing__rung--filled {
  background: var(--accent-primary, var(--accolade-gold-base, #d1a23a));
}
.player-standing__rung--current {
  background: linear-gradient(
    to bottom,
    var(--accolade-gold-highlight, #f2c866) 0%,
    var(--accolade-gold-base, #d1a23a) 100%
  );
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--accolade-gold-base) 60%, transparent);
}
.player-standing__rung-id {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 9px;
  color: var(--muted-foreground, var(--fg-muted, #666));
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
}
.player-standing__tier-row {
  display: flex;
  justify-content: space-between;
  margin-top: 18px;
  gap: 4px;
}
.player-standing__tier-marker {
  flex: 1;
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 9px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  text-align: center;
  color: var(--muted-foreground, var(--fg-muted, #666));
}
.player-standing--empty {
  color: var(--muted-foreground, var(--fg-muted, #666));
  font-style: italic;
  font-size: var(--fs-meta, 0.78rem);
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
}
"""


# Rung catalog — (rung_id, label, tier, tier_label)
_RUNG_CATALOG = [
    (0,  "Walk-on",                    1, "Floor"),
    (1,  "Backup",                     1, "Floor"),
    (2,  "Rotation",                   1, "Floor"),
    (3,  "Starter",                    2, "Established"),
    (4,  "Regular contributor",        2, "Established"),
    (5,  "Solid starter",              3, "Quality starter"),
    (6,  "Quality starter",            3, "Quality starter"),
    (7,  "All-Conference 2nd team",    4, "All-Conference"),
    (8,  "All-Conference 1st team",    4, "All-Conference"),
    (9,  "All-American 3rd team",      5, "National recognition"),
    (10, "All-American 2nd team",      5, "National recognition"),
    (11, "All-American 1st team",      5, "National recognition"),
    (12, "Position-of-the-Year",       6, "National honors"),
    (13, "Watch-list honoree",         6, "National honors"),
    (14, "POTY finalist",              6, "National honors"),
    (15, "Heisman finalist",           6, "National honors"),
    (16, "Heisman winner",             6, "National honors"),
]

_RUNG_STORIES = {
    0:  "Roster reality. The starting block is honest.",
    1:  "Snap-by-snap rotation player. Working on the next step.",
    2:  "Earned snaps in the rotation. Pushing for the starting nod.",
    3:  "Starting role secured. Year-over-year improvement is the next bet.",
    4:  "Regular contributor on a competitive roster. Quietly productive.",
    5:  "Solid starter — the kind of player every program builds around.",
    6:  "Quality starter producing measurable value above replacement.",
    7:  "All-Conference 2nd team. The recognition has started.",
    8:  "All-Conference 1st team. Among the conference's best at the position.",
    9:  "All-American 3rd team. National recognition has arrived.",
    10: "All-American 2nd team. Among the country's best at the position.",
    11: "All-American 1st team. Elite-tier national recognition.",
    12: "Position-of-the-Year — the country's best at the position.",
    13: "Watch-list honoree across major position awards.",
    14: "POTY finalist — one of three nationally for the position award.",
    15: "Heisman finalist — among the country's best players, period.",
    16: "Heisman winner. The trophy is in the case.",
}


def render_standing_rail(standing_rung: int | None, player_name: str = "") -> str:
    """Render the 17-rung Standing Rail.

    Args:
        standing_rung: int 0-16 inclusive, or None for empty
        player_name: optional, used in story when prominent
    """
    if standing_rung is None:
        return (
            '<section class="player-standing player-standing--empty" '
            'data-module="player-standing" data-state="empty">'
            'Player Standing rail computes once enough usage data is available.'
            '</section>'
        )
    try:
        rung = max(0, min(16, int(standing_rung)))
    except (TypeError, ValueError):
        return ""

    rung_id, label, tier, tier_label = _RUNG_CATALOG[rung]
    story = _RUNG_STORIES.get(rung, "")

    rail_html: list[str] = []
    for r_idx in range(17):
        if r_idx == rung:
            cls = "player-standing__rung player-standing__rung--current"
        elif r_idx < rung:
            cls = "player-standing__rung player-standing__rung--filled"
        else:
            cls = "player-standing__rung"
        rail_html.append(
            f'<div class="{cls}" data-rung-id="R{r_idx:02d}" '
            f'title="R{r_idx:02d} — {escape(_RUNG_CATALOG[r_idx][1])}"></div>'
        )

    tier_markers: list[str] = []
    last_tier = 0
    for r_idx in range(17):
        _, _, t, t_label = _RUNG_CATALOG[r_idx]
        if t != last_tier:
            tier_markers.append(
                f'<span class="player-standing__tier-marker">{escape(t_label)}</span>'
            )
            last_tier = t

    return f"""
<section class="player-standing" data-module="player-standing" data-state="ready"
         data-rung="{rung}" data-tier="{tier}">
  <div class="player-standing__head">
    <p class="player-standing__eyebrow">Player Standing · {len(_RUNG_CATALOG)} rungs</p>
    <span class="player-standing__tier-label">Tier {tier} · {escape(tier_label)}</span>
  </div>
  <h3 class="player-standing__rung-label">R{rung_id:02d} · {escape(label)}</h3>
  <p class="player-standing__story">{escape(story)}</p>
  <div class="player-standing__rail" role="img" aria-label="Standing rung {rung} of 16">
    {''.join(rail_html)}
  </div>
  <div class="player-standing__tier-row">
    {''.join(tier_markers)}
  </div>
</section>"""


__all__ = ["render_standing_rail", "STANDING_RAIL_CSS"]
