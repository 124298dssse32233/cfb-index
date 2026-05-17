"""HTML rendering for the receipt pattern.

Three rendering primitives:

  * ``annotate_body_markdown(body, citations)`` — replaces ``[N]``
    markers in prose with the locked ``<sup class="citation">`` HTML.
    Returns the annotated string; non-matching markers (no Citation
    entry) are left as plain ``[N]`` so the critic catches them in
    rendered output too.

  * ``render_citation_footer(citations)`` — emits the Wikipedia-style
    ordered list of sources to drop below the article body. Skips
    when no citations.

  * ``render_legacy_notice()`` — the spec-locked notice block for
    pre-receipt-pattern content. Mounted by the daily/mailbag/wire
    renderer when published_at < the cutover date.

All output HTML-escapes the dynamic strings. The ``[N]`` ↔ Citation
matching is a pure list scan (cheap; per spec, citations per article
top out at ~30).
"""

from __future__ import annotations

import html as _html
import re
from typing import Iterable

from .types import Citation


_MARKER_RE = re.compile(r"\[(\d+)\]")


def render_inline_marker(citation: Citation) -> str:
    """Emit the locked superscript HTML for one Citation.

    The full label + URL are stamped as ``data-*`` attributes so the
    desktop hover-tooltip + mobile tap-reveal both work without an
    additional fetch.
    """
    url_attr = (
        f' data-cite-url="{_html.escape(citation.source_url)}"'
        if citation.source_url else ""
    )
    date_attr = (
        f' data-cite-date="{_html.escape(citation.source_date)}"'
        if citation.source_date else ""
    )
    return (
        f'<sup class="citation" '
        f'data-cite-id="{citation.marker_id}" '
        f'data-cite-kind="{_html.escape(citation.source_kind)}" '
        f'data-cite-label="{_html.escape(citation.source_label)}"'
        f'{url_attr}{date_attr}>'
        f'<a href="#cite-{citation.marker_id}" '
        f'aria-describedby="cite-{citation.marker_id}">'
        f'[{citation.marker_id}]'
        f'</a>'
        f'</sup>'
    )


def annotate_body_markdown(
    body_markdown: str,
    citations: Iterable[Citation],
) -> str:
    """Replace ``[N]`` markers with the locked inline-marker HTML.

    Markers without a matching Citation are LEFT AS PLAIN ``[N]`` so
    the absent receipt is visible in rendered output (and trivially
    auditable by grep). The CitationCritic should have already blocked
    a passing-with-missing-citation case before reaching this function;
    this is a belt-and-suspenders pass.
    """
    by_id: dict[int, Citation] = {c.marker_id: c for c in citations}

    def _sub(match: re.Match[str]) -> str:
        marker_id = int(match.group(1))
        cit = by_id.get(marker_id)
        if cit is None:
            return match.group(0)  # leave as plain [N]
        return render_inline_marker(cit)

    return _MARKER_RE.sub(_sub, body_markdown)


def render_citation_footer(citations: Iterable[Citation]) -> str:
    """Emit the article-citations footer block (Wikipedia-style)."""
    cit_list = sorted(citations, key=lambda c: c.marker_id)
    if not cit_list:
        return ""
    items_html = "\n".join(_render_footer_item(c) for c in cit_list)
    return f"""\
<footer class="article-citations" aria-labelledby="citations-header">
  <h3 id="citations-header" class="citations-header">Sources</h3>
  <ol class="citations-list">
{items_html}
  </ol>
  <p class="citations-note">
    CFB Index editorial is AI-synthesized and grounded in real sources.
    Every claim above is traceable to at least one cited source.
    <a href="/methodology/citations.html">How we cite &rarr;</a>
  </p>
</footer>"""


def _render_footer_item(citation: Citation) -> str:
    """One <li> in the footer list."""
    link_html = ""
    if citation.source_url:
        date_text = citation.source_date or "source"
        link_html = (
            f'<a href="{_html.escape(citation.source_url)}" '
            f'class="cite-link" rel="noopener noreferrer" target="_blank">'
            f'{_html.escape(date_text)} &rarr;'
            f'</a>'
        )
    elif citation.source_date:
        link_html = (
            f'<span class="cite-date">{_html.escape(citation.source_date)}'
            f'</span>'
        )
    return (
        f'    <li id="cite-{citation.marker_id}" '
        f'class="citation-entry citation-entry--{_html.escape(citation.confidence)}">'
        f'<span class="cite-num">[{citation.marker_id}]</span> '
        f'<span class="cite-kind cite-kind--{_html.escape(citation.source_kind)}">'
        f'{_html.escape(_kind_label(citation.source_kind))}'
        f'</span> '
        f'<span class="cite-label">{_html.escape(citation.source_label)}</span>'
        f' {link_html}'
        f'</li>'
    )


def _kind_label(kind: str) -> str:
    """Human-readable label for a source_kind."""
    return {
        "reddit": "Reddit",
        "beat_writer": "Beat writer",
        "podcast": "Podcast",
        "wikipedia": "Wikipedia",
        "official": "Official",
        "cfbd": "CFBD",
        "wire": "CFB Index Wire",
        "edition": "Prior edition",
    }.get(kind, kind.title())


def render_legacy_notice(cutover_date: str = "2026-05-17") -> str:
    """The locked notice for pre-receipt-pattern editorial."""
    return f"""\
<aside class="legacy-pre-citation-notice" role="note"
       aria-label="Pre-citation editorial notice">
  <p>This piece was published before our citation pattern launched on
  <time datetime="{_html.escape(cutover_date)}">{_html.escape(cutover_date)}</time>.
  New CFB Index editorial includes inline source citations.
  <a href="/methodology/citations.html">Learn more &rarr;</a></p>
</aside>"""


__all__ = [
    "annotate_body_markdown",
    "render_citation_footer",
    "render_inline_marker",
    "render_legacy_notice",
]
