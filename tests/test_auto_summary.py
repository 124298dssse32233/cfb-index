"""Tests for cfb_rankings.auto_summary (Sprint v5-7.6).

Pattern A 30-second auto-summary primitive. Tests cover:
  - body-hash stability (cache key invariant)
  - bullet parser tolerance (-, *, •, –)
  - empty/short body short-circuit
  - cache round-trip
  - HTML escape on bullet content
  - end-to-end with mocked loop_a_single_shot
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from cfb_rankings.auto_summary import (
    AutoSummary,
    CACHE_DDL,
    _body_hash,
    _parse_bullets,
    generate_article_summary,
    render_auto_summary_html,
)
from cfb_rankings.db import Database


# ---------------------------------------------------------------------------
# _body_hash
# ---------------------------------------------------------------------------

def test_body_hash_is_stable_for_identical_input() -> None:
    """Same body → same hash. Cache key invariant."""
    body = "A reasonably long body that holds for hash comparison " * 5
    assert _body_hash(body) == _body_hash(body)


def test_body_hash_changes_when_body_changes_by_one_char() -> None:
    """Byte-for-byte invalidation — single-char delta → different hash."""
    body = "alabama beat auburn 27-24 in the iron bowl."
    assert _body_hash(body) != _body_hash(body + ".")


def test_body_hash_is_16_chars_hex() -> None:
    """Truncated SHA-256 — 16 hex chars (64 bits, plenty for cache key)."""
    h = _body_hash("anything")
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# _parse_bullets
# ---------------------------------------------------------------------------

def test_parse_bullets_accepts_dash_prefix() -> None:
    raw = """- First bullet sentence here.
- Second bullet sentence here.
- Third bullet sentence here."""
    bullets = _parse_bullets(raw)
    assert len(bullets) == 3
    assert bullets[0] == "First bullet sentence here."


def test_parse_bullets_accepts_star_prefix() -> None:
    raw = "* Star prefix bullet one.\n* Star prefix bullet two."
    bullets = _parse_bullets(raw)
    assert len(bullets) == 2
    assert bullets[1] == "Star prefix bullet two."


def test_parse_bullets_accepts_unicode_bullet_prefix() -> None:
    raw = "• Unicode bullet one matters.\n• Unicode bullet two matters."
    bullets = _parse_bullets(raw)
    assert len(bullets) == 2


def test_parse_bullets_accepts_en_dash_prefix() -> None:
    raw = "– En-dash bullet number one.\n– En-dash bullet number two."
    bullets = _parse_bullets(raw)
    assert len(bullets) == 2


def test_parse_bullets_caps_at_max_bullets() -> None:
    """LLM may overflow — we cap at the requested ceiling."""
    raw = "\n".join(f"- Bullet number {i} content here." for i in range(10))
    bullets = _parse_bullets(raw, max_bullets=3)
    assert len(bullets) == 3


def test_parse_bullets_drops_too_short_lines() -> None:
    """Bullets under 10 chars are rejected as junk."""
    raw = "- ok\n- This one is long enough to keep."
    bullets = _parse_bullets(raw)
    assert len(bullets) == 1
    assert bullets[0] == "This one is long enough to keep."


def test_parse_bullets_skips_non_bullet_lines() -> None:
    """Throat-clearing prose between bullets is ignored."""
    raw = """Here is the summary you requested:

- The first true bullet sentence here.
And here is some commentary.
- The second true bullet sentence here."""
    bullets = _parse_bullets(raw)
    assert len(bullets) == 2


def test_parse_bullets_empty_input_returns_empty() -> None:
    assert _parse_bullets("") == ()
    assert _parse_bullets("\n\n\n") == ()


# ---------------------------------------------------------------------------
# generate_article_summary — short-circuit paths
# ---------------------------------------------------------------------------

def test_generate_returns_none_for_empty_body() -> None:
    assert generate_article_summary("", cache_key="x") is None


def test_generate_returns_none_for_short_body() -> None:
    """<200 chars is too short to summarize meaningfully."""
    assert generate_article_summary("a" * 50, cache_key="x") is None


def test_generate_returns_none_for_whitespace_body() -> None:
    assert generate_article_summary("   \n\n   ", cache_key="x") is None


# ---------------------------------------------------------------------------
# Cache layer — fixtures + round-trip
# ---------------------------------------------------------------------------

@pytest.fixture
def db_with_cache_table(tmp_path: Path) -> Database:
    """Empty DB with just the auto_summary_cache table created."""
    d = Database(f"sqlite:///{tmp_path / 'cache.db'}")
    d.execute(CACHE_DDL)
    return d


@pytest.fixture
def db_no_table(tmp_path: Path) -> Database:
    """DB with no cache table — _read_cache must gracefully return None."""
    return Database(f"sqlite:///{tmp_path / 'empty.db'}")


def test_cache_read_returns_none_when_table_missing(db_no_table: Database) -> None:
    """OperationalError (no such table) → None, never raises."""
    from cfb_rankings.auto_summary import _read_cache
    assert _read_cache(db_no_table, "k", "hash") is None


def test_cache_write_silent_when_table_missing(db_no_table: Database) -> None:
    """Missing table → warning, no exception."""
    from cfb_rankings.auto_summary import _write_cache
    summary = AutoSummary(
        bullets=("a bullet that is long enough.",),
        body_hash="abc123",
    )
    # Should not raise
    _write_cache(db_no_table, "k", summary)


def test_cache_round_trip(db_with_cache_table: Database) -> None:
    """Write then read returns the same bullets."""
    from cfb_rankings.auto_summary import _read_cache, _write_cache
    summary = AutoSummary(
        bullets=("bullet one is here.", "bullet two follows naturally."),
        body_hash="deadbeefcafe1234",
    )
    _write_cache(db_with_cache_table, "daily:2026-05-17", summary)
    got = _read_cache(db_with_cache_table, "daily:2026-05-17", "deadbeefcafe1234")
    assert got is not None
    assert got.bullets == summary.bullets
    assert got.body_hash == "deadbeefcafe1234"


def test_cache_miss_on_wrong_body_hash(db_with_cache_table: Database) -> None:
    """Different body_hash → cache miss, even if key matches."""
    from cfb_rankings.auto_summary import _read_cache, _write_cache
    summary = AutoSummary(
        bullets=("bullet one is here.",),
        body_hash="originalhash1234",
    )
    _write_cache(db_with_cache_table, "k", summary)
    assert _read_cache(db_with_cache_table, "k", "differenthash99") is None


# ---------------------------------------------------------------------------
# generate_article_summary — end-to-end with mocked loop_a_single_shot
# ---------------------------------------------------------------------------

@dataclass
class _FakeLoopResult:
    text: str | None


def _install_fake_loop(
    monkeypatch: pytest.MonkeyPatch,
    text: str | None,
    *,
    call_log: list[dict[str, Any]] | None = None,
) -> None:
    """Patch loop_a_single_shot inside cfb_rankings.quality_loop."""
    import cfb_rankings.quality_loop as ql

    def _fake(prompt: str, **kwargs: Any) -> _FakeLoopResult:
        if call_log is not None:
            call_log.append({"prompt": prompt, **kwargs})
        return _FakeLoopResult(text=text)

    monkeypatch.setattr(ql, "loop_a_single_shot", _fake)


def test_generate_full_round_trip_with_mock(
    monkeypatch: pytest.MonkeyPatch,
    db_with_cache_table: Database,
) -> None:
    """End-to-end: generate → LLM mock → parse → cache write → return."""
    _install_fake_loop(
        monkeypatch,
        text=(
            "- Alabama survived a fourth-quarter comeback attempt against Auburn.\n"
            "- Quarterback Jalen Milroe threw for three touchdowns.\n"
            "- The Iron Bowl win clinches a top-four CFP seed for Alabama."
        ),
    )
    body = "Alabama beat Auburn 27-24. " * 30  # >200 chars
    result = generate_article_summary(
        body_markdown=body,
        headline="Iron Bowl Recap",
        dek="Tide survive a late push.",
        cache_key="daily:2026-11-30",
        db=db_with_cache_table,
    )
    assert result is not None
    assert len(result.bullets) == 3
    assert result.bullets[0].startswith("Alabama survived")
    assert result.model_version == "auto-summary.v1"


def test_generate_caches_result_for_next_call(
    monkeypatch: pytest.MonkeyPatch,
    db_with_cache_table: Database,
) -> None:
    """Second call with same key+body skips the LLM (cache hit)."""
    calls: list[dict[str, Any]] = []
    _install_fake_loop(
        monkeypatch,
        text="- Bullet content that is long enough to keep.\n- Second bullet content here.",
        call_log=calls,
    )
    body = "Substantive article body. " * 30
    r1 = generate_article_summary(
        body_markdown=body, cache_key="k1", db=db_with_cache_table,
    )
    r2 = generate_article_summary(
        body_markdown=body, cache_key="k1", db=db_with_cache_table,
    )
    assert r1 is not None and r2 is not None
    assert r1.bullets == r2.bullets
    # Only one LLM call should have happened — second hit cache
    assert len(calls) == 1


def test_generate_force_regenerate_bypasses_cache(
    monkeypatch: pytest.MonkeyPatch,
    db_with_cache_table: Database,
) -> None:
    calls: list[dict[str, Any]] = []
    _install_fake_loop(
        monkeypatch,
        text="- Bullet content that is long enough to keep.\n- Second bullet content here.",
        call_log=calls,
    )
    body = "Substantive article body. " * 30
    generate_article_summary(
        body_markdown=body, cache_key="k1", db=db_with_cache_table,
    )
    generate_article_summary(
        body_markdown=body, cache_key="k1",
        db=db_with_cache_table, force_regenerate=True,
    )
    assert len(calls) == 2


def test_generate_returns_none_when_llm_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_loop(monkeypatch, text=None)
    body = "Substantive article body. " * 30
    assert generate_article_summary(body, cache_key="k") is None


def test_generate_returns_none_when_bullets_unparseable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM responded with prose, no bullet markers — parser yields 0 bullets."""
    _install_fake_loop(
        monkeypatch,
        text="This article was about Alabama winning a football game.",
    )
    body = "Substantive article body. " * 30
    assert generate_article_summary(body, cache_key="k") is None


def test_generate_works_without_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """db=None path: always calls LLM, never caches, returns result."""
    _install_fake_loop(
        monkeypatch,
        text="- A complete-enough bullet number one.\n- A complete-enough bullet number two.",
    )
    body = "Substantive article body. " * 30
    result = generate_article_summary(body, cache_key="k")  # db omitted
    assert result is not None
    assert len(result.bullets) == 2


def test_generate_truncates_long_body_in_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bodies over 3000 chars are excerpted (start + tail) to bound tokens."""
    calls: list[dict[str, Any]] = []
    _install_fake_loop(
        monkeypatch,
        text="- A first bullet that is long enough.\n- A second bullet that is long enough.",
        call_log=calls,
    )
    body = "A" * 2500 + " MIDDLE_MARKER " + "B" * 2500
    generate_article_summary(body, cache_key="k", headline="H", dek="D")
    assert len(calls) == 1
    prompt = calls[0]["prompt"]
    # The middle should be elided; markers from start and tail should both
    # exist; the elision marker should be present.
    assert "MIDDLE_MARKER" not in prompt
    assert "[...middle truncated...]" in prompt


def test_generate_propagates_loop_exception_as_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If loop_a_single_shot raises, we log + return None (graceful)."""
    import cfb_rankings.quality_loop as ql

    def _boom(prompt: str, **kwargs: Any) -> None:
        raise RuntimeError("simulated API outage")

    monkeypatch.setattr(ql, "loop_a_single_shot", _boom)
    body = "Substantive article body. " * 30
    assert generate_article_summary(body, cache_key="k") is None


# ---------------------------------------------------------------------------
# render_auto_summary_html
# ---------------------------------------------------------------------------

def test_render_empty_string_for_none_summary() -> None:
    # type: ignore[arg-type]
    assert render_auto_summary_html(None) == ""  # type: ignore[arg-type]


def test_render_empty_string_for_empty_bullets() -> None:
    summary = AutoSummary(bullets=(), body_hash="x")
    assert render_auto_summary_html(summary) == ""


def test_render_emits_aside_with_aria_label() -> None:
    summary = AutoSummary(
        bullets=("First sentence here.", "Second sentence here."),
        body_hash="x",
    )
    html = render_auto_summary_html(summary)
    assert 'class="auto-summary"' in html
    assert 'aria-label="30-second summary"' in html
    assert "30-second summary" in html
    assert "First sentence here." in html
    assert "Second sentence here." in html


def test_render_escapes_bullet_html() -> None:
    """XSS defense — bullets are HTML-escaped."""
    summary = AutoSummary(
        bullets=("<script>alert(1)</script>",),
        body_hash="x",
    )
    html = render_auto_summary_html(summary)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_render_escapes_model_version() -> None:
    # model_version is stored on the AutoSummary object but is NOT rendered
    # into the visible HTML (removed from the meta footer for cleanliness).
    # The key safety invariant is that raw HTML tags from model_version do
    # NOT leak into the output — a passive XSS check.
    summary = AutoSummary(
        bullets=("Bullet content here.",),
        body_hash="x",
        model_version="<weird>v2</weird>",
    )
    html = render_auto_summary_html(summary)
    assert "<weird>" not in html
    # model_version is intentionally not rendered (no &lt;weird&gt; expected)
