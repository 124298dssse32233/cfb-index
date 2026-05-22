"""Database archetype renderer module.

Per ``docs/design-system/30-page-archetypes.md``, the Database archetype
covers ``/wire/``, ``/editions/``, ``/canon/``, ``/players/`` (directory),
``/portal-heat/``, ``/recruit-board/``, and ``/storylines/``. The spec
lists the renderer as **partial** — each surface today has its own
custom listing UI; the visual rhythm doesn't carry across them.

This module is the **starter scaffold** for that consolidation work
the v2 audit calls out as Tier 2 (~1 week). Strategy mirrors
:mod:`cfb_rankings.profile` and :mod:`cfb_rankings.dashboards`: extract
a small set of HTML emitters that the legacy renderers can adopt
incrementally before any one of them gets fully rewritten.

What lives here today (callable from any database-list renderer):

  - :func:`render_filter_strip` — uniform filter chip row (the archetype
    spec calls for a sticky filter bar above the table; this is the
    no-JS chip-anchor version)
  - :func:`render_table_grid_open` / :func:`render_table_grid_close` —
    consistent wrapper around tabular listings (sets the table
    typography + responsive overflow rule)
  - :func:`render_database_meta_footer` — methodology + total-rows
    footer pattern matching the Profile/Dashboard archetypes
  - :func:`render_empty_listing` — the "no matches / no rows yet"
    state, consolidating ad-hoc text across the seven surfaces

CSS support is contributed inline by the legacy renderers' page-level
styles; once a critical mass of adopters land, the rules consolidate
into a ``.database-archetype__*`` block in the global stylesheet (TBD).

What's still TO BUILD (sized for focused future sessions):

  - The full Database page wrapper (analogous to the Profile / Dashboard
    page-template work). For now, callers build their own ``<html>``
    document and just splice these primitives in.
  - Sortable-column emitter — every Database surface has its own
    sort logic today; consolidating saves ~150 LOC per renderer.
  - Pagination shell — Heisman + Players already paginated inline,
    but the rest don't. Consolidate when E1/E2/E3 perf passes finish.
"""
from __future__ import annotations

from html import escape as _escape


def render_filter_strip(
    *,
    filters: list[tuple[str, str, str]],
    aria_label: str = "Database filters",
) -> str:
    """Uniform filter strip for database-archetype pages.

    ``filters`` is a list of ``(label, href, count_or_state)`` tuples.
    ``count_or_state`` is rendered as a small chip on the right of each
    filter (e.g. ``"23 active"``, ``"All"``, ``"7 dormant"``); empty
    string suppresses the chip. ``href`` typically points at an in-page
    anchor (``#filter-active``) or a separate listing URL.
    """
    if not filters:
        return ""
    items_html = "".join(
        f'<li class="database-archetype__filter-item">'
        f'<a class="database-archetype__filter-link" href="{_escape(href)}">'
        f'<span class="database-archetype__filter-label">{_escape(label)}</span>'
        + (
            f'<span class="database-archetype__filter-state">{_escape(state)}</span>'
            if state else ""
        )
        + '</a></li>'
        for (label, href, state) in filters
    )
    return (
        f'<nav class="database-archetype__filter-strip" aria-label="{_escape(aria_label)}">'
        f'<ul class="database-archetype__filter-list">'
        f'{items_html}'
        f'</ul></nav>'
    )


def render_table_grid_open(
    *,
    table_class: str = "",
    aria_label: str = "Listing",
) -> str:
    """Open a responsive wrapper around a Database-archetype listing.

    Always sets overflow-x: auto via the CSS class so wide tables scroll
    horizontally on mobile rather than blow out the viewport. Callers
    emit their own ``<table>`` (and headers) inside the wrapper.

    Pair with :func:`render_table_grid_close`.
    """
    cls = "database-archetype__table-wrap"
    if table_class:
        cls = f"{cls} {table_class}"
    return (
        f'<div class="{cls}" role="region" aria-label="{_escape(aria_label)}" tabindex="0">'
    )


def render_table_grid_close() -> str:
    """Close tag for :func:`render_table_grid_open`."""
    return "</div>"


def render_database_meta_footer(
    *,
    label: str,
    total_rows: int,
    methodology_label: str = "How we collect this",
    methodology_href: str = "/methodology/",
    updated_text: str = "",
) -> str:
    """Methodology footer + row-count pill for Database-archetype pages.

    Mirrors :func:`cfb_rankings.profile.render_profile_meta_footer` but
    surfaces total row count as the headline metric. Used as a closer
    on listing pages so visitors get a "this is the universe" anchor.

    Args
    ----
    label
        What's being counted (e.g. ``"Editions in the archive"``).
    total_rows
        Row count to display.
    methodology_label, methodology_href
        Methodology link target + label.
    updated_text
        Optional "Updated YYYY-MM-DD" pill text. Empty hides it.
    """
    updated_html = (
        f'<span class="database-archetype__meta-pill">{_escape(updated_text)}</span>'
        if updated_text else ""
    )
    return f"""<footer class="database-archetype__meta-footer" aria-label="Database methodology + freshness">
  <a class="database-archetype__meta-link" href="{_escape(methodology_href)}">{_escape(methodology_label)} &rsaquo;</a>
  <span class="database-archetype__meta-pill"><strong>{total_rows:,}</strong> {_escape(label)}</span>
  {updated_html}
</footer>"""


def render_empty_listing(
    *,
    headline: str,
    body: str,
    action_label: str | None = None,
    action_href: str | None = None,
) -> str:
    """Consolidated empty-state shell for Database-archetype listings.

    Use anywhere a listing page would currently show ad-hoc "No matches"
    or stack of blank rows. Plain text inputs; HTML entity references
    (e.g. ``&ge;``) pass through unchanged.
    """
    cta = ""
    if action_label and action_href:
        cta = (
            f' <a class="database-archetype__empty-cta" href="{_escape(action_href)}">'
            f'{_escape(action_label)} &rsaquo;</a>'
        )
    return (
        '<section class="database-archetype__empty" aria-label="Listing — no matches">'
        f'<h3 class="database-archetype__empty-headline">{_escape(headline)}</h3>'
        f'<p class="database-archetype__empty-body">{body}{cta}</p>'
        '</section>'
    )


__all__ = [
    "render_filter_strip",
    "render_table_grid_open",
    "render_table_grid_close",
    "render_database_meta_footer",
    "render_empty_listing",
]
