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

Today this module re-exports two existing primitives so any Dashboard
page can call them without re-importing across modules:
  - ``render_hero_finding`` — eyebrow + big number + sentence + caption
  - ``render_methodology_footer`` — link + sample + updated timestamp

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


__all__ = ["render_hero_finding", "render_methodology_footer"]
