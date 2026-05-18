"""Tests for cfb_rankings.citations (Sprint v5-6a.5 receipt pattern).

Coverage:
  - Citation dataclass + citation_from_row builders
  - persistence: round-trip + missing-table degradation + re-run idempotent
  - render: inline markers + footer list + legacy notice + HTML escape
  - critic: missing/orphan citations, hallucinated sources, density bands
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cfb_rankings.citations import (
    CITATION_DDL,
    Citation,
    CitationCritic,
    SOURCE_KIND_VALUES,
    annotate_body_markdown,
    citation_from_row,
    load_citations,
    persist_citations,
    render_citation_footer,
    render_inline_marker,
    render_legacy_notice,
)
from cfb_rankings.db import Database


# ---------------------------------------------------------------------------
# types
# ---------------------------------------------------------------------------

def test_source_kind_enum_values_match_spec() -> None:
    assert SOURCE_KIND_VALUES == (
        "reddit", "beat_writer", "podcast", "wikipedia",
        "official", "cfbd", "wire", "edition",
    )


def test_citation_from_row_minimal() -> None:
    row = {
        "marker_id": 1,
        "source_kind": "reddit",
        "source_label": "r/CFB · 248 replies",
    }
    c = citation_from_row(row)
    assert c.marker_id == 1
    assert c.source_kind == "reddit"
    assert c.source_label == "r/CFB · 248 replies"
    assert c.source_url is None
    assert c.confidence == "supporting"  # default


def test_citation_is_frozen() -> None:
    c = Citation(marker_id=1, source_kind="reddit", source_label="x")
    with pytest.raises(Exception):
        c.marker_id = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path: Path) -> Database:
    d = Database(f"sqlite:///{tmp_path / 'citations.db'}")
    d.execute(CITATION_DDL)
    return d


@pytest.fixture
def db_no_table(tmp_path: Path) -> Database:
    return Database(f"sqlite:///{tmp_path / 'empty.db'}")


def test_persist_then_load(db: Database) -> None:
    cits = [
        Citation(
            marker_id=1, source_kind="reddit",
            source_label="r/CFB · 248 replies",
            source_url="https://reddit.com/r/CFB/comments/x",
            confidence="primary",
        ),
        Citation(
            marker_id=2, source_kind="beat_writer",
            source_label="Stewart Mandel · The Athletic · May 12, 2026",
            source_url="https://theathletic.com/x",
            source_date="2026-05-12",
            confidence="supporting",
        ),
    ]
    written = persist_citations(db, generation_id=42, citations=cits)
    assert written == 2

    loaded = load_citations(db, generation_id=42)
    assert len(loaded) == 2
    assert loaded[0].marker_id == 1
    assert loaded[0].source_kind == "reddit"
    assert loaded[1].marker_id == 2
    assert loaded[1].source_date == "2026-05-12"


def test_persist_is_idempotent_on_rerun(db: Database) -> None:
    """Second persist with same generation_id replaces, not duplicates."""
    cits_v1 = [Citation(marker_id=1, source_kind="reddit", source_label="v1")]
    cits_v2 = [
        Citation(marker_id=1, source_kind="reddit", source_label="v2"),
        Citation(marker_id=2, source_kind="podcast", source_label="podcast x"),
    ]
    persist_citations(db, 100, cits_v1)
    persist_citations(db, 100, cits_v2)

    loaded = load_citations(db, 100)
    assert len(loaded) == 2
    assert loaded[0].source_label == "v2"  # not "v1"
    assert loaded[1].source_kind == "podcast"


def test_persist_handles_empty_list(db: Database) -> None:
    assert persist_citations(db, 5, []) == 0


def test_persist_missing_table_returns_zero(db_no_table: Database) -> None:
    """OperationalError → log + return 0, never raises."""
    cits = [Citation(marker_id=1, source_kind="reddit", source_label="x")]
    assert persist_citations(db_no_table, 1, cits) == 0


def test_load_missing_table_returns_empty(db_no_table: Database) -> None:
    assert load_citations(db_no_table, 1) == []


def test_load_unknown_generation_returns_empty(db: Database) -> None:
    assert load_citations(db, 999) == []


def test_check_constraint_blocks_bad_source_kind(db: Database) -> None:
    """The CHECK constraint should reject 'invalid_kind' at the DB level."""
    cits = [Citation(
        marker_id=1, source_kind="invalid_kind",  # type: ignore[arg-type]
        source_label="x",
    )]
    # persist_citations swallows OperationalError but the CHECK fires as
    # IntegrityError — should propagate so tests catch this.
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        persist_citations(db, 1, cits)


def test_check_constraint_blocks_bad_confidence(db: Database) -> None:
    cits = [Citation(
        marker_id=1, source_kind="reddit",
        source_label="x",
        confidence="totally_made_up",  # type: ignore[arg-type]
    )]
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        persist_citations(db, 1, cits)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def test_render_inline_marker_emits_locked_attrs() -> None:
    c = Citation(
        marker_id=3, source_kind="beat_writer",
        source_label="Stewart Mandel · The Athletic · May 12, 2026",
        source_url="https://theathletic.com/x",
        source_date="2026-05-12",
    )
    html = render_inline_marker(c)
    assert 'class="citation"' in html
    assert 'data-cite-id="3"' in html
    assert 'data-cite-kind="beat_writer"' in html
    assert "Stewart Mandel" in html
    assert 'href="#cite-3"' in html
    assert "https://theathletic.com/x" in html


def test_render_inline_marker_omits_url_when_absent() -> None:
    c = Citation(marker_id=1, source_kind="cfbd", source_label="CFBD API")
    html = render_inline_marker(c)
    assert "data-cite-url" not in html


def test_render_inline_marker_escapes_label() -> None:
    c = Citation(
        marker_id=1, source_kind="reddit",
        source_label="<script>alert(1)</script>",
    )
    html = render_inline_marker(c)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_annotate_body_markdown_replaces_markers() -> None:
    body = "Alabama won big[1] and Mandel agreed[2]. The data backs it[3]."
    cits = [
        Citation(marker_id=1, source_kind="reddit", source_label="r/CFB"),
        Citation(marker_id=2, source_kind="beat_writer", source_label="Mandel"),
        Citation(marker_id=3, source_kind="cfbd", source_label="CFBD"),
    ]
    out = annotate_body_markdown(body, cits)
    assert out.count('class="citation"') == 3
    assert "[1]" not in out.split('aria-describedby="cite-1"')[1][:50] \
        or 'data-cite-id="1"' in out  # marker survived in the sup label


def test_annotate_body_leaves_unmatched_markers_as_plain() -> None:
    """A [N] without a matching Citation entry must remain visible."""
    body = "Solid claim here[1]. Suspicious claim[99] over here."
    cits = [Citation(marker_id=1, source_kind="reddit", source_label="r/CFB")]
    out = annotate_body_markdown(body, cits)
    assert 'data-cite-id="1"' in out
    # [99] left as plain text (catches missed citation in visible output)
    assert "[99]" in out


def test_render_citation_footer_empty_returns_empty() -> None:
    assert render_citation_footer([]) == ""


def test_render_citation_footer_emits_locked_structure() -> None:
    cits = [
        Citation(
            marker_id=1, source_kind="reddit",
            source_label="r/CFB · Sark vs Kirby · 318 replies",
            source_url="https://reddit.com/r/CFB/comments/x",
            source_date="2026-05-14",
            confidence="primary",
        ),
        Citation(
            marker_id=2, source_kind="beat_writer",
            source_label="Stewart Mandel · The Athletic",
            source_url="https://theathletic.com/x",
            source_date="2026-05-12",
            confidence="supporting",
        ),
    ]
    html = render_citation_footer(cits)
    assert 'class="article-citations"' in html
    assert 'aria-labelledby="citations-header"' in html
    assert '<ol class="citations-list">' in html
    assert 'id="cite-1"' in html
    assert 'id="cite-2"' in html
    assert "citation-entry--primary" in html
    assert "citation-entry--supporting" in html
    assert 'href="https://reddit.com/r/CFB/comments/x"' in html
    assert "Stewart Mandel" in html
    # methodology cross-link
    assert "/methodology/citations.html" in html


def test_render_citation_footer_sorts_by_marker_id() -> None:
    cits = [
        Citation(marker_id=3, source_kind="cfbd", source_label="Z"),
        Citation(marker_id=1, source_kind="reddit", source_label="A"),
        Citation(marker_id=2, source_kind="podcast", source_label="M"),
    ]
    html = render_citation_footer(cits)
    pos_1 = html.find('id="cite-1"')
    pos_2 = html.find('id="cite-2"')
    pos_3 = html.find('id="cite-3"')
    assert 0 < pos_1 < pos_2 < pos_3


def test_render_legacy_notice_includes_cutover_date() -> None:
    html = render_legacy_notice("2026-05-17")
    assert 'class="legacy-pre-citation-notice"' in html
    assert '<time datetime="2026-05-17">' in html
    assert "/methodology/citations.html" in html


# ---------------------------------------------------------------------------
# critic
# ---------------------------------------------------------------------------

def _long_body(words: int) -> str:
    """Generate a body of N words for density testing."""
    return " ".join(f"word{i}" for i in range(words))


def test_critic_passes_when_density_and_match_are_good() -> None:
    body = _long_body(400) + " A claim[1]. Another claim[2]."
    cits = [
        Citation(marker_id=1, source_kind="reddit", source_label="r/CFB"),
        Citation(marker_id=2, source_kind="beat_writer", source_label="Mandel"),
    ]
    avail = [
        {"id": "r1", "label": "r/CFB recent thread"},
        {"id": "b1", "label": "Stewart Mandel column"},
    ]
    result = CitationCritic().critique(body, cits, avail)
    assert result.passed
    assert result.citation_count == 2


def test_critic_blocks_missing_citation() -> None:
    body = "Solid claim[1]. Suspicious[99]."
    cits = [Citation(marker_id=1, source_kind="reddit", source_label="r/CFB")]
    result = CitationCritic().critique(body, cits)
    assert not result.passed
    blockers = [i for i in result.issues if i.severity == "blocker"]
    assert any(i.kind == "missing_citation" for i in blockers)


def test_critic_warns_on_orphan_citation() -> None:
    """Citation entry with no [N] marker in body is a warning, not a block."""
    body = "No markers here."
    cits = [Citation(marker_id=1, source_kind="reddit", source_label="r/CFB")]
    result = CitationCritic().critique(body, cits)
    warnings = [i for i in result.issues if i.severity == "warning"]
    assert any(i.kind == "orphan_citation" for i in warnings)


def test_critic_blocks_empty_source_label() -> None:
    body = "Claim[1]."
    cits = [Citation(marker_id=1, source_kind="reddit", source_label="   ")]
    result = CitationCritic().critique(body, cits)
    assert not result.passed
    assert any(i.kind == "empty_source_label" for i in result.issues)


def test_critic_blocks_hallucinated_source() -> None:
    """Citation label not fuzzy-matching any available source → blocker."""
    body = "Claim[1]."
    cits = [Citation(
        marker_id=1, source_kind="beat_writer",
        source_label="Pete Thamel · Yahoo · May 12, 2026",
    )]
    # Available_sources only mentions Mandel
    avail = [{"id": "b1", "label": "Stewart Mandel column"}]
    result = CitationCritic().critique(body, cits, avail)
    assert not result.passed
    assert any(i.kind == "hallucinated_source" for i in result.issues)


def test_critic_no_hallucination_check_without_available_sources() -> None:
    """If caller didn't pass available_sources, skip the check (pre-wiring)."""
    body = "Claim[1]."
    cits = [Citation(marker_id=1, source_kind="reddit", source_label="X")]
    result = CitationCritic().critique(body, cits, None)
    # No hallucinated_source issue
    assert not any(i.kind == "hallucinated_source" for i in result.issues)


def test_critic_warns_on_low_density() -> None:
    """800-word body with 1 citation → warn (1 per 800 falls below the
    1-per-400 warn threshold but still above the 1-per-800 block floor)."""
    body = _long_body(800) + " Claim[1]."
    cits = [Citation(marker_id=1, source_kind="reddit", source_label="X")]
    result = CitationCritic().critique(body, cits)
    warnings = [i for i in result.issues if i.severity == "warning"]
    assert any(i.kind == "low_citation_density" for i in warnings)


def test_critic_blocks_on_critical_low_density() -> None:
    """1600-word body with 1 citation → block (1 per 1600 below 1 per 800)."""
    body = _long_body(1600) + " Claim[1]."
    cits = [Citation(marker_id=1, source_kind="reddit", source_label="X")]
    result = CitationCritic().critique(body, cits)
    assert not result.passed
    assert any(i.kind == "critical_low_density" for i in result.issues)


def test_critic_skips_density_for_tiny_bodies() -> None:
    """Bodies under 100 words don't trigger density checks (auto-summaries
    and one-liners are legitimately uncited prose)."""
    body = "Tiny claim with no marker."  # 5 words
    result = CitationCritic().critique(body, [])
    assert result.passed
    assert not any("density" in i.kind for i in result.issues)


def test_critic_result_exposes_helper_properties() -> None:
    body = "Claim[1]. Missing[2]."
    cits = [Citation(marker_id=1, source_kind="reddit", source_label="X")]
    result = CitationCritic().critique(body, cits)
    assert len(result.blockers) >= 1
    # warnings property is iterable
    list(result.warnings)
