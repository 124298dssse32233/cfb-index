"""Selector Grid — PLAYER_PAGE_WORLD_CLASS_BRIEF.md §7.5.

The brief verbatim:

    "The Selector Grid — pill grid, one chip per selector, gold/
     silver/HM/empty. Still the single best 'how real is this honor'
     visualization in sports."
    "Don't ship without the Selector Grid."

This is the §3 #9 design primitive — *"the Accolade Lens's signature
component"*. Renders an 11-pill grid covering the canonical
All-America selectors (the 5 NCAA-recognized + the 6 most-cited
extras) with the player's status on each pill: gold for 1st team,
silver for 2nd team, bronze for HM, grey/empty when not named.

§7.5 selector list verbatim:

    "NCAA-recognized official All-America selectors (since 2002):
     AP, AFCA, FWAA, Sporting News, Walter Camp.
     ≥3 of 5 = Consensus; all 5 = Unanimous.
     Full 2025 selector pool (14 bodies): add SI, The Athletic,
     USA Today, ESPN, CBS Sports, PFF, CFN, Athlon, Phil Steele."

v1 ships 11 selectors (5 NCAA-recognized + SI, The Athletic, USA
Today, ESPN, PFF, Athlon). v2 can expand to all 14.

Public API:
    render_selector_grid(honors_history, season) -> str
    SELECTOR_GRID_CSS_BLOCK                       -> str
"""
from __future__ import annotations

from html import escape
from typing import Any


# ---------------------------------------------------------------------------
# Selector taxonomy
# ---------------------------------------------------------------------------

# (slug, short label, full label, is_ncaa_recognized)
SELECTORS: tuple[tuple[str, str, str, bool], ...] = (
    ("ap",       "AP",     "Associated Press",         True),
    ("afca",     "AFCA",   "American Football Coaches Association", True),
    ("fwaa",     "FWAA",   "Football Writers Association of America", True),
    ("sn",       "SN",     "The Sporting News",        True),
    ("wc",       "WC",     "Walter Camp Foundation",   True),
    ("si",       "SI",     "Sports Illustrated",       False),
    ("athletic", "TA",     "The Athletic",             False),
    ("usat",     "USAT",   "USA Today",                False),
    ("espn",     "ESPN",   "ESPN",                     False),
    ("pff",      "PFF",    "Pro Football Focus",       False),
    ("athlon",   "Athlon", "Athlon Sports",            False),
)

# Patterns we match against honor row `selector` field (case-insensitive,
# substring). Loose because data sources spell selectors many ways.
SELECTOR_PATTERNS: dict[str, tuple[str, ...]] = {
    "ap":       ("associated press", "ap "),
    "afca":     ("afca", "coaches"),
    "fwaa":     ("fwaa", "football writers"),
    "sn":       ("sporting news",),
    "wc":       ("walter camp",),
    "si":       ("sports illustrated", " si ", "si "),
    "athletic": ("the athletic", "athletic "),
    "usat":     ("usa today", "usat"),
    "espn":     ("espn",),
    "pff":      ("pff", "pro football focus"),
    "athlon":   ("athlon",),
}


# ---------------------------------------------------------------------------
# CSS block
# ---------------------------------------------------------------------------

SELECTOR_GRID_CSS_BLOCK = """
/* Selector Grid — Sprint C (PLAYER_PAGE_WORLD_CLASS_BRIEF §7.5)
 *
 * 11-pill grid. Each pill = one All-America selector. Pill state:
 *   1st team → gold (--selector-gold)
 *   2nd team → silver
 *   HM       → bronze
 *   empty    → grey-on-grey
 *
 * Pills use display font for the selector short label so the grid
 * reads as a single block of branding rather than a list of strings.
 */

.selector-grid {
  --selector-gold:    #c9a24a;
  --selector-silver:  #c5c8d0;
  --selector-bronze:  #b56a3c;
  --selector-empty-fg:rgba(255, 255, 255, 0.35);
  --selector-empty-bg:rgba(255, 255, 255, 0.04);
  --selector-stroke:  rgba(255, 255, 255, 0.10);

  display: grid;
  gap: 10px;
  padding: clamp(16px, 2vw, 24px) clamp(16px, 2.2vw, 28px);
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--selector-stroke);
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
}

.selector-grid__header {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px 14px;
  margin-bottom: 4px;
}
.selector-grid__title {
  font-family: 'Bebas Neue', 'Inter Display', 'Inter', system-ui, sans-serif;
  font-size: clamp(22px, 1.6vw + 12px, 30px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--fg-primary, #1a1a1a);
  margin: 0;
}
.selector-grid__sub {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted, #8a90a1);
  margin: 0;
}
.selector-grid__summary {
  font-family: 'Source Serif Pro', Georgia, serif;
  font-size: 14px;
  color: var(--fg-secondary, #4a4a4a);
  margin: 0;
}

.selector-grid__pills {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(74px, 1fr));
  gap: 8px;
}

@media (max-width: 720px) {
  .selector-grid__pills {
    grid-template-columns: repeat(3, 1fr);
  }
}

.selector-pill {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 12px 6px;
  background: var(--selector-empty-bg);
  border: 1px solid var(--selector-stroke);
  border-radius: 8px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  min-height: 64px;
}
.selector-pill__short {
  font-family: 'Bebas Neue', 'Inter Display', 'Inter', system-ui, sans-serif;
  font-size: 19px;
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
  color: var(--selector-empty-fg);
}
.selector-pill__state {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--selector-empty-fg);
}
.selector-pill__ncaa-dot {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--fg-muted, #8a90a1);
  opacity: 0.35;
}
.selector-pill[data-rank="1"] {
  background: color-mix(in oklab, var(--selector-gold) 18%, transparent);
  border-color: var(--selector-gold);
}
.selector-pill[data-rank="1"] .selector-pill__short,
.selector-pill[data-rank="1"] .selector-pill__state {
  color: var(--selector-gold);
}
.selector-pill[data-rank="2"] {
  background: color-mix(in oklab, var(--selector-silver) 14%, transparent);
  border-color: var(--selector-silver);
}
.selector-pill[data-rank="2"] .selector-pill__short,
.selector-pill[data-rank="2"] .selector-pill__state {
  color: var(--selector-silver);
}
.selector-pill[data-rank="HM"] {
  background: color-mix(in oklab, var(--selector-bronze) 14%, transparent);
  border-color: var(--selector-bronze);
}
.selector-pill[data-rank="HM"] .selector-pill__short,
.selector-pill[data-rank="HM"] .selector-pill__state {
  color: var(--selector-bronze);
}

.selector-grid__legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted, #8a90a1);
}
.selector-grid__legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}
.selector-grid__legend-dot--gold   { background: var(--selector-gold); }
.selector-grid__legend-dot--silver { background: var(--selector-silver); }
.selector-grid__legend-dot--bronze { background: var(--selector-bronze); }
.selector-grid__legend-dot--ncaa   { background: var(--fg-muted, #8a90a1); }
"""


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def _rank_for_team_label(team_label: str) -> str | None:
    """Map an honor row's team_label ('1st', '2nd', 'HM') to a pill rank."""
    if not team_label:
        return None
    t = team_label.strip().lower()
    if any(x in t for x in ("1st", "first", "consensus", "unanimous")):
        return "1"
    if any(x in t for x in ("2nd", "second")):
        return "2"
    if any(x in t for x in ("3rd", "third", "honorable", "hm")):
        return "HM"
    return None


def _match_selector(selector_text: str, honor_name: str) -> str | None:
    """Return the selector slug if this honor matches one of our selectors."""
    blob = f"{selector_text} {honor_name}".lower()
    for slug, patterns in SELECTOR_PATTERNS.items():
        for p in patterns:
            if p in blob:
                return slug
    return None


def _is_all_america_honor(scope: str, name: str) -> bool:
    """Is this honor an All-America selection?"""
    blob = f"{scope} {name}".lower()
    return any(x in blob for x in ("all-america", "all america", "aa team"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_selector_grid(
    honors_history: list[dict[str, Any]] | None,
    season: int | str | None = None,
) -> str:
    """Render the 11-pill All-America Selector Grid.

    Always renders the full grid — the empty state IS the visualisation.
    For a player with no AA honors, the grid reads as eleven greyed pills,
    which is the brief's design intent (the grid answers "how widely was
    he named?" — including "not at all" is the answer for most players).
    """
    honors_history = honors_history or []

    # season filter — if season provided, only count that year's AA honors
    relevant: list[dict[str, Any]] = []
    for h in honors_history:
        if not _is_all_america_honor(
            str(h.get("honor_scope") or ""),
            str(h.get("honor_name") or ""),
        ):
            continue
        if season is not None:
            try:
                hy = int(h.get("season_year") or 0)
                sy = int(str(season))
                if hy != sy:
                    continue
            except (TypeError, ValueError):
                pass
        relevant.append(h)

    # For each selector slug, find the best-ranked honor (1st > 2nd > HM).
    rank_priority = {"1": 3, "2": 2, "HM": 1}
    best_by_selector: dict[str, str] = {}
    for h in relevant:
        slug = _match_selector(
            str(h.get("selector") or ""),
            str(h.get("honor_name") or ""),
        )
        if not slug:
            continue
        rank = _rank_for_team_label(str(h.get("honor_team") or ""))
        if not rank:
            # No explicit team label — assume 1st if it's an AA selection at all
            rank = "1"
        cur = best_by_selector.get(slug)
        if cur is None or rank_priority.get(rank, 0) > rank_priority.get(cur, 0):
            best_by_selector[slug] = rank

    # Headline: count NCAA-recognized 1st teams for the Consensus/Unanimous status.
    ncaa_first_team_count = sum(
        1 for (slug, _short, _full, is_ncaa) in SELECTORS
        if is_ncaa and best_by_selector.get(slug) == "1"
    )
    aa_status = ""
    if ncaa_first_team_count >= 5:
        aa_status = "Unanimous All-American"
    elif ncaa_first_team_count >= 3:
        aa_status = "Consensus All-American"
    elif ncaa_first_team_count >= 1:
        aa_status = "All-American"

    season_text = (
        f"All-America Selector Grid · {escape(str(season))}"
        if season else "All-America Selector Grid"
    )
    summary = (
        f"<p class='selector-grid__summary'><strong>{escape(aa_status)}.</strong> "
        f"Named on {ncaa_first_team_count} of 5 NCAA-recognized selectors (AP, AFCA, FWAA, SN, WC).</p>"
        if aa_status else
        ("<p class='selector-grid__summary'>"
         "No All-America selections on the ledger. "
         "Pills light up gold (1st), silver (2nd), or bronze (HM) when "
         "selectors name him."
         "</p>")
    )

    pills_html: list[str] = []
    for slug, short, full, is_ncaa in SELECTORS:
        rank = best_by_selector.get(slug)
        if rank == "1":
            state_label = "1st"
        elif rank == "2":
            state_label = "2nd"
        elif rank == "HM":
            state_label = "HM"
        else:
            state_label = "—"
        attrs = ""
        if rank:
            attrs = f' data-rank="{rank}"'
        ncaa_dot = (
            '<span class="selector-pill__ncaa-dot" aria-hidden="true" '
            'title="NCAA-recognized selector"></span>'
            if is_ncaa else ""
        )
        pills_html.append(
            f'<article class="selector-pill"{attrs} title="{escape(full)} · {escape(state_label)}">'
            f'{ncaa_dot}'
            f'<span class="selector-pill__short">{escape(short)}</span>'
            f'<span class="selector-pill__state">{escape(state_label)}</span>'
            f'</article>'
        )

    return f"""
<section class="selector-grid" aria-labelledby="selector-grid-h" data-module="selector-grid" data-state="ready">
  <header class="selector-grid__header">
    <h2 id="selector-grid-h" class="selector-grid__title">Selector Grid</h2>
    <p class="selector-grid__sub">{season_text}</p>
  </header>
  {summary}
  <div class="selector-grid__pills" role="list" aria-label="All-America selector pills">
    {''.join(pills_html)}
  </div>
  <p class="selector-grid__legend">
    <span><span class="selector-grid__legend-dot selector-grid__legend-dot--gold"></span>1st team</span>
    <span><span class="selector-grid__legend-dot selector-grid__legend-dot--silver"></span>2nd team</span>
    <span><span class="selector-grid__legend-dot selector-grid__legend-dot--bronze"></span>HM</span>
    <span><span class="selector-grid__legend-dot selector-grid__legend-dot--ncaa"></span>NCAA-recognized</span>
  </p>
</section>
"""


__all__ = [
    "render_selector_grid",
    "SELECTOR_GRID_CSS_BLOCK",
    "SELECTORS",
]
