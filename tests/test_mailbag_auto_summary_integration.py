"""End-to-end: Mailbag renderer wires the auto-summary block above answers.

Pattern 7 (Mailbag) from docs/design-system/34-integration-playbook.md.
Mirrors test_daily_auto_summary_integration.py — same primitive, different
surface, different token system (Mailbag uses --gold/--ink/--navy/--sans
print-feel palette).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cfb_rankings.mailbag.renderer import (
    _adapt_conn_for_auto_summary,
    _build_auto_summary_html,
)


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    c = sqlite3.connect(str(tmp_path / "mailbag.db"))
    c.row_factory = sqlite3.Row
    return c


def test_empty_answers_returns_empty(conn: sqlite3.Connection) -> None:
    assert _build_auto_summary_html([], "2026-w19", conn) == ""


def test_short_combined_body_returns_empty(conn: sqlite3.Connection) -> None:
    """Combined question + body < 200 chars → too short."""
    answers = [{
        "question_text": "Q?",
        "answer_body": "Short answer.",
        "rank_position": 1,
    }]
    assert _build_auto_summary_html(answers, "2026-w19", conn) == ""


def test_llm_failure_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
) -> None:
    import cfb_rankings.auto_summary as auto_summary
    monkeypatch.setattr(
        auto_summary,
        "generate_article_summary",
        lambda **kwargs: None,
    )
    body = "Substantial answer prose. " * 30
    answers = [{
        "question_text": "Question here?",
        "answer_body": body,
        "rank_position": 1,
    }]
    assert _build_auto_summary_html(answers, "2026-w19", conn) == ""


def test_successful_summary_renders_aside(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
) -> None:
    from cfb_rankings.auto_summary import AutoSummary
    import cfb_rankings.auto_summary as auto_summary
    fake = AutoSummary(
        bullets=(
            "Texas A&M's portal class signals a defensive shift.",
            "Reader question about UT/A&M rivalry distribution.",
            "Beat-writer consensus is converging on the spring narrative.",
        ),
        body_hash="abc1234567890def",
    )
    monkeypatch.setattr(
        auto_summary,
        "generate_article_summary",
        lambda **kwargs: fake,
    )
    body = "Substantive answer prose with multiple paragraphs of content. " * 20
    answers = [{
        "question_text": "Will A&M flip the SEC West?",
        "answer_body": body,
        "rank_position": 1,
    }]
    out = _build_auto_summary_html(answers, "2026-w19", conn)
    assert 'class="auto-summary"' in out
    # & in "A&M" must be HTML-escaped to &amp;
    assert "Texas A&amp;M" in out
    assert "portal class signals" in out
    assert "30-second summary" in out


def test_combines_multiple_answers(
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
    body_a = "First answer paragraph. " * 20
    body_b = "Second answer paragraph. " * 20
    answers = [
        {"question_text": "Q1?", "answer_body": body_a, "rank_position": 1},
        {"question_text": "Q2?", "answer_body": body_b, "rank_position": 2},
    ]
    _build_auto_summary_html(answers, "2026-w19", conn)
    combined = captured["body_markdown"]
    assert "Q: Q1?" in combined
    assert "Q: Q2?" in combined
    assert "First answer paragraph" in combined
    assert "Second answer paragraph" in combined
    assert "---" in combined


def test_cache_key_includes_edition_slug(
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
    body = "Substantial answer prose. " * 30
    answers = [{"question_text": "Q?", "answer_body": body, "rank_position": 1}]
    _build_auto_summary_html(answers, "2026-w22", conn)
    assert captured["cache_key"] == "mailbag:2026-w22"


def test_strips_draft_marker_before_summarizing(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
) -> None:
    """[DRAFT — edition X] trailing marker should be stripped before
    feeding the summarizer. Uses the exact marker format
    `_DRAFT_MARKER_RE` matches (trailing, single-instance)."""
    captured: dict = {}
    import cfb_rankings.auto_summary as auto_summary
    monkeypatch.setattr(
        auto_summary,
        "generate_article_summary",
        lambda **kwargs: captured.update(kwargs) or None,
    )
    body = (
        "The actual answer prose with substantive content here. " * 10
        + " [DRAFT — edition 2026-w19; API key required]"
    )
    answers = [{
        "question_text": "Q?",
        "answer_body": body,
        "rank_position": 1,
    }]
    _build_auto_summary_html(answers, "2026-w19", conn)
    assert "body_markdown" in captured
    assert "[DRAFT" not in captured["body_markdown"]
    assert "actual answer prose" in captured["body_markdown"]


def test_adapt_conn_returns_database(conn: sqlite3.Connection) -> None:
    db = _adapt_conn_for_auto_summary(conn)
    assert db is not None
    db.execute("CREATE TABLE IF NOT EXISTS smoke (x INTEGER)")
    db.execute("INSERT INTO smoke (x) VALUES (?)", (7,))
    row = db.query_one("SELECT x FROM smoke")
    assert row is not None and row["x"] == 7
