"""Article archetype renderer module.

Per ``docs/design-system/30-page-archetypes.md``, the Article archetype
covers ``/daily/``, ``/mailbag/``, ``/reactions/``, and the per-feature
edition essays at ``/editions/<n>/<slug>/``. The spec lists the
renderer as **partial** — :mod:`cfb_rankings.editions.article_renderer`
already implements most of the pattern for edition essays; daily,
mailbag, and reactions each ship their own wrapper today.

This module is the **starter scaffold** for the consolidation work
the v2 audit calls out as Tier 2 (~3-5 days). Mirrors the Profile /
Dashboard / Database scaffold approach.

What lives here today (callable from any article-style renderer):

  - :func:`render_article_chrome` — eyebrow + kind pill + h1 + dek +
    byline row, the consistent top-of-article header treatment
  - :func:`render_article_footer` — closing meta block (next article
    link + share row + methodology pointer)
  - :func:`render_article_aside_callout` — pull-quote / aside block
    used for the spec's "one pull-quote-worthy sentence in the middle
    third" rule
  - :func:`render_continue_reading_row` — next/previous article nav
    consolidating ad-hoc CTAs across the surfaces

Citation pipeline lives in :mod:`cfb_rankings.citations`; article-
archetype renderers should call its ``annotate_body_markdown`` +
``render_citation_footer`` before/after the body in the same pattern
as :mod:`cfb_rankings.editions.article_renderer`.

What's still TO BUILD (sized for focused future sessions):

  - Full Article page wrapper consolidating editions.article_renderer
    with daily / mailbag / reactions renderers
  - Pull-quote autodetection from body markdown (currently manual)
  - Shared markdown→HTML primitive (each surface today rolls its own
    paragraph + blockquote + bold/italic regex pass)
"""
from __future__ import annotations

from html import escape as _escape


def render_article_chrome(
    *,
    eyebrow: str,
    kind_label: str,
    headline: str,
    dek: str = "",
    byline: str = "",
    read_time_minutes: int | None = None,
    edition_label: str = "",
) -> str:
    """Consistent article-top chrome.

    Args
    ----
    eyebrow
        Short uppercase eyebrow line (e.g. ``"THE DAILY · May 22"``).
    kind_label
        Article-kind pill text (e.g. ``"COVER ESSAY"``, ``"MAILBAG"``,
        ``"REACTION"``).
    headline
        Article ``<h1>`` text.
    dek
        Optional italic deck. Empty hides it.
    byline
        Optional byline (e.g. ``"By The Editor's Desk"``). Empty hides
        the whole byline row.
    read_time_minutes
        Optional read-time integer; rendered as ``"N MIN READ"``.
    edition_label
        Optional right-aligned label (e.g. ``"VOL. I · NO. 18"``).
    """
    dek_html = (
        f'<p class="article-archetype__dek">{_escape(dek)}</p>'
        if dek else ""
    )
    byline_row = ""
    if byline:
        read_html = (
            f'<span>{int(read_time_minutes)} MIN READ</span>'
            if read_time_minutes else ""
        )
        edition_html = (
            f'<span class="article-archetype__byline-edition">{_escape(edition_label)}</span>'
            if edition_label else ""
        )
        byline_row = (
            '<div class="article-archetype__byline-row">'
            f'<span>{_escape(byline)}</span>'
            f'{read_html}'
            f'{edition_html}'
            '</div>'
        )
    return f"""<header class="article-archetype__chrome">
  <p class="article-archetype__eyebrow">{_escape(eyebrow)}</p>
  <span class="article-archetype__kind-pill">{_escape(kind_label)}</span>
  <h1 class="article-archetype__headline">{_escape(headline)}</h1>
  {dek_html}
  {byline_row}
</header>"""


def render_article_aside_callout(*, quote: str, attribution: str = "") -> str:
    """Pull-quote / aside callout for the spec's mid-third moment.

    Plain text inputs. Renders as a ``<aside>`` with the locked
    typography treatment.
    """
    attr_html = (
        f'<cite class="article-archetype__aside-attribution">&mdash; {_escape(attribution)}</cite>'
        if attribution else ""
    )
    return (
        '<aside class="article-archetype__aside-callout" aria-label="Pull quote">'
        f'<blockquote class="article-archetype__aside-quote">{_escape(quote)}</blockquote>'
        f'{attr_html}'
        '</aside>'
    )


def render_continue_reading_row(
    *,
    next_label: str = "",
    next_href: str = "",
    prev_label: str = "",
    prev_href: str = "",
) -> str:
    """Render the previous/next nav at the end of an article.

    Either or both may be empty (suppressed). When both are empty the
    function returns an empty string (no nav row at all).
    """
    next_html = ""
    if next_label and next_href:
        next_html = (
            f'<a class="article-archetype__nav-link article-archetype__nav-link--next" '
            f'href="{_escape(next_href)}">'
            f'<span class="article-archetype__nav-eyebrow">Next</span>'
            f'<span class="article-archetype__nav-label">{_escape(next_label)} &rsaquo;</span>'
            f'</a>'
        )
    prev_html = ""
    if prev_label and prev_href:
        prev_html = (
            f'<a class="article-archetype__nav-link article-archetype__nav-link--prev" '
            f'href="{_escape(prev_href)}">'
            f'<span class="article-archetype__nav-eyebrow">Previous</span>'
            f'<span class="article-archetype__nav-label">&lsaquo; {_escape(prev_label)}</span>'
            f'</a>'
        )
    if not (next_html or prev_html):
        return ""
    return f'<nav class="article-archetype__continue-row" aria-label="Article navigation">{prev_html}{next_html}</nav>'


def render_article_footer(
    *,
    share_url: str = "",
    methodology_label: str = "How we report this",
    methodology_href: str = "/methodology/",
) -> str:
    """Closing meta block on an article-archetype page.

    Methodology pointer is mandatory; share URL is optional and renders
    a small copy-link affordance.
    """
    share_html = ""
    if share_url:
        share_html = (
            f'<a class="article-archetype__footer-share" href="{_escape(share_url)}" '
            f'data-share-url="{_escape(share_url)}">Share this page &rsaquo;</a>'
        )
    return f"""<footer class="article-archetype__footer" aria-label="Article footer">
  <a class="article-archetype__footer-methodology" href="{_escape(methodology_href)}">{_escape(methodology_label)} &rsaquo;</a>
  {share_html}
</footer>"""


__all__ = [
    "render_article_chrome",
    "render_article_aside_callout",
    "render_continue_reading_row",
    "render_article_footer",
]
