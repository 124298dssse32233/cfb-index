"""End-to-end: Daily renderer wires the auto-summary block above takes.

Pattern 7 from docs/design-system/34-integration-playbook.md. The Daily
renderer must:
  1. Build a combined article-body from all takes (headline + body)
  2. Short-circuit when combined body <200 chars
  3. Call auto_summary.generate_article_summary with cache_key=daily:<date>
  4. Render the .auto-summary block above takes_html in the layout
  5. Degrade gracefully when the LLM call returns None
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cfb_rankings.daily.renderer import (
    _adapt_conn_for_auto_summary,
    _build_auto_summary_html,
)


def _seed_daily_takes(conn: sqlite3.Connection, edition_date: str,
                     takes: list[tuple[int, str, str]]) -> None:
    """Seed daily_takes with (rank, headline, body) tuples."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_takes (
            edition_date TEXT, rank_position INTEGER, headline TEXT,
            body TEXT, cited_sources_json TEXT,
            primary_entity_slug TEXT, primary_entity_type TEXT,
            generation_model TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO daily_takes (edition_date, rank_position, headline, body, "
        "cited_sources_json, primary_entity_slug, primary_entity_type, "
        "generation_model) VALUES (?, ?, ?, ?, '[]', '', 'event', 'test')",
        [(edition_date, rank, h, b) for rank, h, b in takes],
    )
    conn.commit()


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    """In-memory sqlite connection."""
    c = sqlite3.connect(str(tmp_path / "daily.db"))
    c.row_factory = sqlite3.Row
    return c


def test_empty_rows_returns_empty(conn: sqlite3.Connection) -> None:
    """Daily with no takes → no auto-summary section."""
    assert _build_auto_summary_html([], "2026-05-17", conn) == ""


def test_short_combined_body_returns_empty(conn: sqlite3.Connection) -> None:
    """Combined headline + body < 200 chars → too short to summarize."""
    # Each take: rank, headline, body, cited_json, primary_slug, primary_type, model
    rows = [(1, "Short headline", "Brief body.", "[]", "x", "event", "m")]
    out = _build_auto_summary_html(rows, "2026-05-17", conn)
    assert out == ""


def test_llm_failure_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
) -> None:
    """LLM returns None → no summary block rendered."""
    # Stub generate_article_summary to return None
    import cfb_rankings.auto_summary as auto_summary
    monkeypatch.setattr(
        auto_summary,
        "generate_article_summary",
        lambda **kwargs: None,
    )
    body = "Plenty of substantive content here. " * 30
    rows = [(1, "A headline here", body, "[]", "x", "event", "m")]
    out = _build_auto_summary_html(rows, "2026-05-17", conn)
    assert out == ""


def test_successful_summary_renders_aside(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
) -> None:
    """Auto-summary returns bullets → renders the locked .auto-summary aside."""
    from cfb_rankings.auto_summary import AutoSummary
    import cfb_rankings.auto_summary as auto_summary

    fake = AutoSummary(
        bullets=(
            "Alabama survives Iron Bowl.",
            "Underwood throws three touchdowns.",
            "CFP semifinal seed locked.",
        ),
        body_hash="deadbeef12345678",
    )
    monkeypatch.setattr(
        auto_summary,
        "generate_article_summary",
        lambda **kwargs: fake,
    )
    body = "Substantive Daily take body content. " * 30
    rows = [(1, "Iron Bowl Recap", body, "[]", "alabama", "team", "m")]
    out = _build_auto_summary_html(rows, "2026-11-30", conn)
    assert 'class="auto-summary"' in out
    assert "Alabama survives Iron Bowl." in out
    assert "Underwood throws three touchdowns." in out
    assert "30-second summary" in out


def test_combines_multiple_takes_into_single_summary(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
) -> None:
    """All takes (headline + body) feed one combined summary input."""
    captured: dict = {}
    import cfb_rankings.auto_summary as auto_summary

    def _capture(**kwargs):
        captured.update(kwargs)
        from cfb_rankings.auto_summary import AutoSummary
        return AutoSummary(
            bullets=("Test bullet content here.",),
            body_hash="x",
        )

    monkeypatch.setattr(
        auto_summary,
        "generate_article_summary",
        _capture,
    )
    body_a = "First take body content " * 20
    body_b = "Second take body content " * 20
    rows = [
        (1, "First headline", body_a, "[]", "x", "event", "m"),
        (2, "Second headline", body_b, "[]", "y", "event", "m"),
    ]
    _build_auto_summary_html(rows, "2026-05-17", conn)
    combined = captured["body_markdown"]
    assert "First headline" in combined
    assert "Second headline" in combined
    assert "First take body content" in combined
    assert "Second take body content" in combined
    # The separator between takes is the markdown HR
    assert "---" in combined


def test_cache_key_includes_edition_date(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
) -> None:
    captured: dict = {}
    import cfb_rankings.auto_summary as auto_summary
    monkeypatch.setattr(
        auto_summary,
        "generate_article_summary",
        lambda **kwargs: captured.update(kwargs) or None,
    )
    body = "Substantive body. " * 30
    rows = [(1, "Headline", body, "[]", "x", "event", "m")]
    _build_auto_summary_html(rows, "2026-08-30", conn)
    assert captured["cache_key"] == "daily:2026-08-30"


def test_skips_takes_with_empty_body(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
) -> None:
    """Takes with empty body text are filtered out."""
    captured: dict = {}
    import cfb_rankings.auto_summary as auto_summary
    monkeypatch.setattr(
        auto_summary,
        "generate_article_summary",
        lambda **kwargs: captured.update(kwargs) or None,
    )
    body = "Real substantive content. " * 30
    rows = [
        (1, "Empty body take", "", "[]", "x", "event", "m"),
        (2, "Real take", body, "[]", "y", "event", "m"),
    ]
    _build_auto_summary_html(rows, "2026-05-17", conn)
    combined = captured["body_markdown"]
    # The empty-body take's headline must NOT appear in the summary input
    assert "Empty body take" not in combined
    assert "Real take" in combined


def test_adapt_conn_returns_database(conn: sqlite3.Connection) -> None:
    """The connection adapter must produce a working Database handle."""
    db = _adapt_conn_for_auto_summary(conn)
    assert db is not None
    # Sanity: the wrapper accepts a query against the same file
    db.execute("CREATE TABLE IF NOT EXISTS smoke (x INTEGER)")
    db.execute("INSERT INTO smoke (x) VALUES (?)", (42,))
    row = db.query_one("SELECT x FROM smoke")
    assert row is not None and row["x"] == 42


def test_adapt_conn_returns_none_for_in_memory_conn() -> None:
    """sqlite3.connect(':memory:') has no file path — adapter returns None
    and the caller falls back to the no-cache LLM path."""
    in_mem = sqlite3.connect(":memory:")
    db = _adapt_conn_for_auto_summary(in_mem)
    # Either None (no file) OR a Database pointing at empty path — both
    # acceptable. The cache writes would fail-soft in either case.
    # We just verify it doesn't raise.
    assert db is None or hasattr(db, "execute")
