"""Player Standing 17-rung Rail — Brief §7.

The single biggest UX move in the Player Brief — replaces the original
Accolade Lens. Six tiers, seventeen rungs from R00 walk-on to R16
Heisman winner. One module answers the question every fan walks in
with: "how good is this guy, actually, right now?"

Tier structure — CANONICAL, mirrors standing_aggregator.RUNG_TABLE
(the labels/tiers are imported from there; do not re-list a divergent
ladder here):
  Tier 0: Not on team   R00 — Walk-on
                        R01 — Scout team / redshirt
  Tier 1: 2-deep        R02 — Deep reserve
                        R03 — Backup
                        R04 — Rotational
  Tier 2: Starter       R05 — Part-time starter
                        R06 — Starter
                        R07 — Impact starter
  Tier 3: Recognized    R08 — Watch-list name
                        R09 — All-Conference HM / 2nd team
                        R10 — All-Conference 1st team
                        R11 — National watch / fringe AA
  Tier 4: Elite         R12 — All-American
                        R13 — Consensus All-American
                        R14 — Unanimous All-American
  Tier 5: Apex          R15 — POTY finalist
                        R16 — POTY / Heisman winner

The rung_id is computed by standing_aggregator.classify_rung (surfaced in
player_data['standing']['current_rung_id']). This module renders the
visualization and MUST label by the same canonical table.

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


# Rung catalog — (rung_id, label, tier, tier_label).
# SINGLE SOURCE OF TRUTH: the canonical ladder lives in
# standing_aggregator.RUNG_TABLE — the SAME table classify_rung() scores
# against. This renderer indexes its label table by the rung NUMBER the
# aggregator computed, so the two must never diverge. This table previously
# encoded a different ladder (R11 = "All-American 1st team"); the aggregator
# computes R11 = "National watch / fringe AA", which is why Arch Manning's rail
# read "All-American 1st team" next to an empty selector grid (2026-06-13).
from .standing_aggregator import RUNG_TABLE as _RUNG_CATALOG  # (rung, label, tier_id, tier_label)

# Per-rung story copy, aligned to the canonical RUNG_TABLE labels above.
_RUNG_STORIES = {
    0:  "Walk-on. Earning a roster spot is the starting line.",
    1:  "Scout team / redshirt. Developing behind the depth chart.",
    2:  "Deep reserve. In the program, working up the two-deep.",
    3:  "Backup. On the two-deep, pushing for snaps.",
    4:  "Rotational. Earning real snaps in the rotation.",
    5:  "Part-time starter. Splitting first-team reps.",
    6:  "Starter. A locked-in starting role.",
    7:  "Impact starter. Producing measurable value above replacement.",
    8:  "Watch-list name. On the national radar at the position.",
    9:  "All-Conference HM / 2nd team. Conference recognition has started.",
    10: "All-Conference 1st team. Among the conference's best at the position.",
    11: "National watch / fringe All-America. Knocking on the All-America door.",
    12: "All-American. Named to an NCAA-recognized All-America team.",
    13: "Consensus All-American. Recognized by a majority of the selectors.",
    14: "Unanimous All-American. First-team on every major selector list.",
    15: "Position-of-the-Year finalist. Among the nation's elite at the position.",
    16: "Position-of-the-Year / Heisman winner. The trophy is in the case.",
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
    last_tier = None  # NOT 0 — canonical tier ids start at 0 ("Not on team"),
    # so a 0-seed would skip the first tier marker.
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
    <p class="player-standing__eyebrow">Player Standing &middot; {len(_RUNG_CATALOG)} rungs</p>
    <span class="player-standing__tier-label">Tier {tier} &middot; {escape(tier_label)}</span>
  </div>
  <h3 class="player-standing__rung-label">R{rung_id:02d} &middot; {escape(label)}</h3>
  <p class="player-standing__story">{escape(story)}</p>
  <div class="player-standing__rail" role="img" aria-label="Standing rung {rung} of 16">
    {''.join(rail_html)}
  </div>
  <div class="player-standing__tier-row">
    {''.join(tier_markers)}
  </div>
</section>"""


__all__ = ["render_standing_rail", "STANDING_RAIL_CSS"]
