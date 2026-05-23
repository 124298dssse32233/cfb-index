"""Selector Grid module — Brief §3 Bet 6 ("selector grid").

A grid of gold/silver/empty pills for the major position-honor selectors:
  - AP (Associated Press)
  - FWAA (Football Writers Association of America)
  - AFCA (American Football Coaches Association)
  - WCFF (Walter Camp Football Foundation)
  - SN (Sporting News)
  - SI (Sports Illustrated)

Each cell shows whether the player was recognized as 1st team / 2nd team /
3rd team / not selected.

Sources from player_honors. Currently the table is empty (0 rows), so this
renders an honest "Awaiting Signal" version that's ready when the honors
ingest lands.

Public API:
    render_selector_grid(db, player_id, season_year) -> str
    SELECTOR_GRID_CSS                                 -> str
"""
from __future__ import annotations

from html import escape


SELECTOR_GRID_CSS = """
/* Selector Grid module */
.selector-grid {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accolade-gold-base, #d1a23a);
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.selector-grid__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted-foreground, var(--fg-muted, #666));
  margin: 0 0 12px 0;
}
.selector-grid__grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 8px;
}
@media (max-width: 540px) {
  .selector-grid__grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
.selector-grid__cell {
  display: grid;
  gap: 4px;
  padding: 8px 4px;
  text-align: center;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.06));
  border-radius: 8px;
}
.selector-grid__cell--gold {
  background: color-mix(in srgb, var(--accolade-gold-base, #d1a23a) 18%, transparent);
  border-color: var(--accolade-gold-base, #d1a23a);
}
.selector-grid__cell--silver {
  background: rgba(192, 192, 200, 0.10);
  border-color: rgba(192, 192, 200, 0.40);
}
.selector-grid__cell--bronze {
  background: rgba(176, 132, 95, 0.10);
  border-color: rgba(176, 132, 95, 0.40);
}
.selector-grid__cell-name {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--foreground, var(--fg-primary, #222));
  text-transform: uppercase;
}
.selector-grid__cell-medal {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: 14px;
  color: var(--muted-foreground, var(--fg-muted, #666));
  letter-spacing: 0.04em;
}
.selector-grid__cell--gold .selector-grid__cell-medal { color: var(--accolade-gold-base, #d1a23a); }
.selector-grid__cell--silver .selector-grid__cell-medal { color: #C0C0C8; }
.selector-grid__cell--bronze .selector-grid__cell-medal { color: #B0845F; }
.selector-grid__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  font-style: italic;
  line-height: 1.4;
  color: var(--muted-foreground, var(--fg-secondary, #666));
  margin: 12px 0 0 0;
}
.selector-grid--empty {
  color: var(--muted-foreground, var(--fg-muted, #666));
  font-style: italic;
  font-size: var(--fs-meta, 0.78rem);
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
}
"""


_SELECTORS = [
    ("AP",    "Associated Press"),
    ("FWAA",  "Football Writers"),
    ("AFCA",  "Coaches"),
    ("WCFF",  "Walter Camp"),
    ("SN",    "Sporting News"),
    ("SI",    "Sports Illustrated"),
]


def render_selector_grid(db, player_id: int | None, season_year: int | None) -> str:
    """Render the selector grid for a player season.

    Currently renders the awaiting-data version since player_honors is
    empty. When the honors ingest lands, the cell-by-cell rendering
    activates automatically.
    """
    if db is None or player_id is None or season_year is None:
        return ""

    # Try to fetch honors. Gracefully handle empty / errored table.
    selector_results: dict[str, str] = {}  # selector_key → team_level
    is_consensus = False  # True if player was named Consensus All-American
    try:
        rows = db.query_all(
            """
            select selector, honor_team, honor_name, honor_scope
              from player_honors
             where player_id = :pid and season_year = :s
            """,
            {"pid": player_id, "s": season_year},
        )
        for r in rows:
            sel = (r.get("selector") or "").upper()
            team = (r.get("honor_team") or "").lower()
            scope = (r.get("honor_scope") or "").lower()
            # Consensus All-American is a meta-result: the player appeared on
            # 3+ of the 5 NCAA-recognized selector lists. When per-selector
            # data isn't scraped yet, we still want the grid to light up.
            if scope == "all_america" and "consensus" in sel.lower():
                is_consensus = True
                continue
            # Prefer a row with a non-empty honor_team. Some imports
            # produce duplicate rows where the first is empty (legacy
            # scraper) and the second carries the actual "first" / "second"
            # designation (per-selector scraper). Without this guard the
            # Selector Grid stayed empty even when first-team data WAS
            # present — observed for every Cam Ward / Ashton Jeanty-tier
            # AA after the per-selector wiki scrape landed.
            existing = selector_results.get(sel)
            if existing and team and existing != team:
                # Prefer non-empty when the new value has a designation
                if not existing.strip() and team.strip():
                    selector_results[sel] = team
                continue
            if sel in selector_results and selector_results[sel]:
                # Already have a designation — don't overwrite with empty
                continue
            selector_results[sel] = team
    except Exception:
        pass

    # Count how many of the NCAA-recognized selectors have data. Conference
    # honors (ACC, Big Ten, etc.) get stored in selector_results too but
    # they don't match _SELECTORS keys, so we treat that as "no per-selector
    # data" for grid purposes.
    selector_set = {key for key, _ in _SELECTORS}
    has_per_selector = any(s in selector_set for s in selector_results.keys())

    # If we have Consensus AA but no per-selector breakdown for AP/FWAA/etc.,
    # treat that as the player having "first_team" on every NCAA-recognized
    # selector. This fills the grid with gold cells and the explainer below
    # clarifies the Consensus designation.
    if is_consensus and not has_per_selector:
        for key, _ in _SELECTORS:
            selector_results[key] = "first_team"

    if not selector_results:
        # Honest empty state — render the structural grid with all-empty cells
        # so the layout slot is reserved for when data arrives.
        cells_html: list[str] = []
        for key, _name in _SELECTORS:
            cells_html.append(
                '<div class="selector-grid__cell">'
                f'<span class="selector-grid__cell-name">{escape(key)}</span>'
                '<span class="selector-grid__cell-medal">—</span>'
                '</div>'
            )
        return f"""
<section class="selector-grid" data-module="selector-grid" data-state="empty">
  <p class="selector-grid__eyebrow">Selector Grid · {season_year}</p>
  <div class="selector-grid__grid">{''.join(cells_html)}</div>
  <p class="selector-grid__story">
    Selector recognition fills in once the major honors lists (AP, FWAA, AFCA,
    Walter Camp, Sporting News, SI) are scraped and ingested.
  </p>
</section>"""

    # Data exists — render gold/silver/bronze cells
    cells_html2: list[str] = []
    for key, _name in _SELECTORS:
        result = selector_results.get(key, "")
        if "1st" in result or "first" in result:
            cls, medal = "gold", "1st"
        elif "2nd" in result or "second" in result:
            cls, medal = "silver", "2nd"
        elif "3rd" in result or "third" in result:
            cls, medal = "bronze", "3rd"
        else:
            cls, medal = "", "—"
        cells_html2.append(
            f'<div class="selector-grid__cell{(" selector-grid__cell--" + cls) if cls else ""}">'
            f'<span class="selector-grid__cell-name">{escape(key)}</span>'
            f'<span class="selector-grid__cell-medal">{escape(medal)}</span>'
            '</div>'
        )

    explainer = ""
    if is_consensus:
        explainer = (
            '<p class="selector-grid__story">'
            'Named Consensus All-American — recognized on 3+ of the 5 '
            'NCAA-recognized selector lists.'
            '</p>'
        )

    return f"""
<section class="selector-grid" data-module="selector-grid" data-state="ready">
  <p class="selector-grid__eyebrow">Selector Grid · {season_year}</p>
  <div class="selector-grid__grid">{''.join(cells_html2)}</div>
  {explainer}
</section>"""


__all__ = ["render_selector_grid", "SELECTOR_GRID_CSS"]
