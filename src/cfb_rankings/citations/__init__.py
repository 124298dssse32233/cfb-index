"""Receipt pattern foundation (Sprint v5-6a.5).

Citation system for Pattern C/D AI editorial. Each generation persists
its citations to ``editorial_citations`` and renders them as:

* Inline ``<sup class="citation">`` superscript markers in body prose
* Footer citation list (Wikipedia-style) at the bottom of articles

Locked spec: ``docs/design-system/32-receipt-pattern.md``

Public API::

    from cfb_rankings.citations import (
        Citation,
        SourceKind,
        ConfidenceTier,
        CitationCritic,
        persist_citations,
        load_citations,
        render_inline_marker,
        render_citation_footer,
        annotate_body_markdown,
    )

Package name note: the parallel ``cfb_rankings.receipts`` package
(Sprint 13) holds the *predictive-claim* receipts infrastructure
("the receipts we have on bold predictions"), which is unrelated to
the editorial-citation receipt pattern this package implements.
"""

from .types import (
    Citation,
    ConfidenceTier,
    SourceKind,
    SOURCE_KIND_VALUES,
    citation_from_row,
)
from .persistence import (
    CITATION_DDL,
    load_citations,
    persist_citations,
)
from .critic import (
    CitationCritic,
    CritiqueIssue,
    CritiqueResult,
)
from .render import (
    annotate_body_markdown,
    render_citation_footer,
    render_inline_marker,
    render_legacy_notice,
)

__all__ = [
    "Citation",
    "ConfidenceTier",
    "SourceKind",
    "SOURCE_KIND_VALUES",
    "citation_from_row",
    "CITATION_DDL",
    "load_citations",
    "persist_citations",
    "CitationCritic",
    "CritiqueIssue",
    "CritiqueResult",
    "annotate_body_markdown",
    "render_citation_footer",
    "render_inline_marker",
    "render_legacy_notice",
]
