"""HTML renderer for HeroFinding. Locked treatment from the mockup set."""

from __future__ import annotations

import html as _html

from ..confidence import render_confidence_chip
from .types import HeroFinding


def render_hero_finding_html(
    finding: HeroFinding,
    *,
    eyebrow_text: str = "WHAT THIS WEEK SHOWS",
) -> str:
    """Emit the hero-finding section HTML.

    The output matches ``docs/mockups/_mockup_shared.css :: .hero-finding``
    structure exactly so the v5-7.5 wiring is a drop-in.

    The ``sentence`` field is passed through unescaped to allow a single
    ``<em>`` span — callers MUST sanitize any other HTML they put in.
    The ``number`` and captions are escaped.
    """
    number = _html.escape(finding.number)
    eyebrow = _html.escape(eyebrow_text)
    sample = _html.escape(finding.sample_caption)
    # When the caller provides a chip label that already states a count
    # (e.g. "3 sources cited"), suppress the auto-appended "· n=N" suffix
    # to avoid redundant numbers in the chip.
    label = finding.confidence_override_label
    show_sample = label is None or not any(
        kw in label.lower() for kw in ("source", "book", "ballot", "mention", "n=")
    )
    chip = render_confidence_chip(
        finding.sample_size,
        finding.confidence_domain,
        override_label=label,
        show_sample=show_sample,
    )
    return f'''\
<section class="hero-finding" aria-label="Hero finding">
  <p class="eyebrow">{eyebrow}</p>
  <div class="hero-finding__number">{number}</div>
  <p class="hero-finding__sentence">
    {finding.sentence}
  </p>
  <div class="hero-finding__caption">
    <span class="sample-chip">{sample}</span>
    {chip}
  </div>
</section>'''


__all__ = ["render_hero_finding_html"]
