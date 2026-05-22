"""Dashboard archetype renderer module.

Per docs/design-system/30-page-archetypes.md, the Dashboard archetype
covers ``/``, ``/heisman/``, ``/rankings/``, and ``/hub/vibe-shifts/``.
The spec lists the renderer as "TO BUILD (consolidate hub/heisman/
rankings renderers)". This module is the starter scaffold for that
consolidation work — currently exposes the shared structural
components so legacy renderers can adopt them incrementally before a
full rewrite.

Shared components (from the archetype spec, top-to-bottom):
  - Top zone (44px sticky): brand + "what this is" eyebrow
  - Saturday Strip (in-season) OR countdown strip (off-season)
  - Hero finding (1 big number + sentence + caption + sample chip)
  - Primary visualization (annotated chart)
  - Movers grid (2-col mobile, 3-4-col desktop)
  - Drill-down modules
  - Methodology footer
  - Bottom filter strip (mobile thumb-zone)

Today this module re-exports three primitives so any Dashboard page
can call them without re-importing across modules:
  - ``render_hero_finding`` — eyebrow + big number + sentence + caption
  - ``render_methodology_footer`` — link + sample + updated timestamp
  - ``render_mobile_filter_strip`` — bottom thumb-zone filter shortcut
    (mobile-only; closes the last Dashboard archetype zone gap)

Full consolidation (Sprint v5-9+) will move the page-level structure
in here and make the page renderers in reporting.py / hub_page.py be
adapters that supply the data shape this module expects.
"""
from __future__ import annotations

from html import escape as _escape

from cfb_rankings.nav import render_methodology_footer


def render_hero_finding(
    *,
    eyebrow: str,
    number: str,
    sentence: str,
    caption: str = "",
    aria_label: str = "Top of the board",
) -> str:
    """Render the Dashboard archetype hero finding zone.

    Single big number + 1-sentence finding + caption. Suppress with an
    empty string by passing ``number=""`` (callers control whether
    they have the data to surface a hero).

    Args
    ----
    eyebrow
        Short uppercase eyebrow line. E.g. "Final 2025 Heisman" or
        "2025 Power Rankings".
    number
        The single big number. Pre-formatted string (e.g. "14.3%",
        "+12.8", "692"). Use ``font-variant-numeric: tabular-nums``
        styling is on the .hero-finding__number rule.
    sentence
        One-line finding. E.g. "Mendoza leads the final-2025 ballot."
    caption
        Optional small caption. Sample-size chip, footnote, or empty.
    aria_label
        Section's aria-label for screen readers.

    Returns
    -------
    HTML string that callers inject before their primary hero section.
    Empty string if ``number`` is falsy.
    """
    if not number:
        return ""
    caption_html = f'<p class="hero-finding__caption">{caption}</p>' if caption else ""
    return f"""<section class="hero-finding" aria-label="{_escape(aria_label)}">
  <p class="hero-finding__eyebrow">{_escape(eyebrow)}</p>
  <p class="hero-finding__number">{number}</p>
  <p class="hero-finding__sentence">{sentence}</p>
  {caption_html}
</section>"""


def render_mobile_filter_strip(
    *,
    filter_anchor: str = "#filter",
    filter_label: str = "Filter",
    sort_anchor: str | None = None,
    sort_label: str = "Sort",
    summary_text: str = "",
    aria_label: str = "Filter and sort shortcuts",
) -> str:
    """Render the Dashboard archetype's mobile thumb-zone filter strip.

    Per ``docs/design-system/30-page-archetypes.md`` §"Dashboard archetype",
    the bottom of every Dashboard page should expose a sticky thumb-zone
    strip with filter chips that the user can reach without stretching.
    This was the only Dashboard archetype zone session 4 didn't ship.

    The strip is rendered as a ``<nav>`` of in-page anchor links
    (filter, optional sort, plus a passive summary). On desktop it's
    visually hidden via the ``@media (min-width: 768px)`` rule in the
    accompanying CSS block — the existing filter UI sits inline on
    desktop, so the strip would be redundant there. On mobile, it
    sticks to the bottom of the viewport with ``position: fixed`` and
    ``bottom: 0``, sized at 56px tall (above the 44px touch-target
    minimum, below the typical iOS bottom-gesture zone).

    No JavaScript dependency. The anchor links scroll the existing
    filter controls into view — they already exist on Heisman and
    Rankings as the ``board-utility`` block from session 4's filter-h3
    pass.

    Args
    ----
    filter_anchor
        In-page anchor (e.g. ``#filter``, ``#board-controls``) that
        scrolls the existing filter UI into the viewport when tapped.
    filter_label
        Label shown on the filter chip. Keep short (≤8 chars).
    sort_anchor
        Optional second anchor (e.g. ``#sort``). When provided, a sort
        chip is added.
    sort_label
        Label shown on the sort chip.
    summary_text
        Optional passive text rendered on the right of the strip. E.g.
        ``"15,599 players"`` for the Heisman page or ``"#1 Alabama"``
        for the rankings page. Empty hides this segment.
    aria_label
        Section's aria-label for screen readers.

    Returns
    -------
    HTML string for a ``<nav class="dashboard-mobile-filter-strip">``
    block.
    """
    sort_chip = ""
    if sort_anchor:
        sort_chip = (
            f'<a class="dashboard-mobile-filter-strip__chip" '
            f'href="{_escape(sort_anchor)}">{_escape(sort_label)}</a>'
        )
    summary_html = (
        f'<span class="dashboard-mobile-filter-strip__summary">'
        f'{_escape(summary_text)}</span>'
        if summary_text else ""
    )
    return f"""<nav class="dashboard-mobile-filter-strip" aria-label="{_escape(aria_label)}">
  <a class="dashboard-mobile-filter-strip__chip" href="{_escape(filter_anchor)}">{_escape(filter_label)}</a>
  {sort_chip}
  {summary_html}
</nav>"""


__all__ = [
    "render_hero_finding",
    "render_methodology_footer",
    "render_mobile_filter_strip",
]
