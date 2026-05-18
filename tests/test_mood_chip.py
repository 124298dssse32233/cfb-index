"""Tests for cfb_rankings.provenance.mood_chip (M-4).

The chip primitive is renderer-agnostic; tests cover:
  - fetch_source_count: counts distinct sources, excludes 'all' aggregate,
    degrades gracefully on missing tables
  - render_provenance_chip: locked HTML shape, pluralization, compact
    variant, XSS escape on the URL
  - PROVENANCE_CHIP_CSS: present + uses var() fallback chains
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.provenance.mood_chip import (
    PROVENANCE_CHIP_CSS,
    ProvenanceData,
    fetch_player_source_count,
    fetch_source_count,
    render_provenance_chip,
)


# ---------------------------------------------------------------------------
# DB fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path: Path) -> Database:
    """In-memory-ish DB with the conversation-features schema."""
    d = Database(f"sqlite:///{tmp_path / 'mood.db'}")
    d.execute("""
        CREATE TABLE team_week_conversation_features (
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            source_name TEXT NOT NULL DEFAULT 'all',
            audience_bucket TEXT NOT NULL DEFAULT 'all',
            mention_count INTEGER NOT NULL DEFAULT 0,
            unique_author_count INTEGER,
            UNIQUE (season_year, week, team_id, source_name, audience_bucket)
        )
    """)
    d.execute("""
        CREATE TABLE player_week_conversation_features (
            player_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            source_name TEXT NOT NULL DEFAULT 'all',
            audience_bucket TEXT NOT NULL DEFAULT 'all',
            mention_count INTEGER NOT NULL DEFAULT 0,
            UNIQUE (season_year, week, player_id, source_name, audience_bucket)
        )
    """)
    return d


@pytest.fixture
def empty_db(tmp_path: Path) -> Database:
    """DB with no schema — every fetch must degrade to 0."""
    return Database(f"sqlite:///{tmp_path / 'empty.db'}")


# ---------------------------------------------------------------------------
# ProvenanceData dataclass
# ---------------------------------------------------------------------------

def test_provenance_data_is_frozen() -> None:
    pd = ProvenanceData(mentions=247, sources=5)
    with pytest.raises(Exception):
        pd.mentions = 999


def test_provenance_data_default_methodology_url() -> None:
    pd = ProvenanceData(mentions=10, sources=2)
    assert pd.methodology_url == "/methodology/fan-intelligence.html"


# ---------------------------------------------------------------------------
# fetch_source_count
# ---------------------------------------------------------------------------

def test_fetch_source_count_counts_distinct_sources(db: Database) -> None:
    # Insert mentions across 3 different subreddits + the 'all' aggregate
    rows = [
        (333, 2025, 12, "r/CFB", "fan", 50),
        (333, 2025, 12, "r/AlabamaFootball", "fan", 100),
        (333, 2025, 12, "r/SEC", "fan", 75),
        (333, 2025, 12, "all", "fan", 225),   # synthetic aggregate — excluded
    ]
    for r in rows:
        db.execute(
            "INSERT INTO team_week_conversation_features "
            "(team_id, season_year, week, source_name, audience_bucket, mention_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            r,
        )
    n = fetch_source_count(db, team_id=333, season_year=2025, week=12)
    assert n == 3  # 'all' excluded


def test_fetch_source_count_returns_zero_for_unknown_team(db: Database) -> None:
    assert fetch_source_count(db, team_id=999, season_year=2025, week=12) == 0


def test_fetch_source_count_respects_bucket_filter(db: Database) -> None:
    """A team's national-bucket sources don't bleed into the fan-bucket count."""
    db.execute(
        "INSERT INTO team_week_conversation_features "
        "(team_id, season_year, week, source_name, audience_bucket, mention_count) "
        "VALUES (333, 2025, 12, 'r/CFB', 'fan', 50)",
    )
    db.execute(
        "INSERT INTO team_week_conversation_features "
        "(team_id, season_year, week, source_name, audience_bucket, mention_count) "
        "VALUES (333, 2025, 12, 'r/CFB', 'national', 20)",
    )
    db.execute(
        "INSERT INTO team_week_conversation_features "
        "(team_id, season_year, week, source_name, audience_bucket, mention_count) "
        "VALUES (333, 2025, 12, 'r/SECNation', 'national', 30)",
    )
    fan_n = fetch_source_count(db, team_id=333, season_year=2025, week=12, bucket="fan")
    nat_n = fetch_source_count(db, team_id=333, season_year=2025, week=12, bucket="national")
    assert fan_n == 1
    assert nat_n == 2


def test_fetch_source_count_empty_db_returns_zero(empty_db: Database) -> None:
    """Missing table → 0, no raise."""
    assert fetch_source_count(empty_db, team_id=333, season_year=2025, week=12) == 0


def test_fetch_player_source_count(db: Database) -> None:
    db.execute(
        "INSERT INTO player_week_conversation_features "
        "(player_id, season_year, week, source_name, audience_bucket, mention_count) "
        "VALUES (100, 2025, 12, 'r/CFB', 'fan', 50)",
    )
    db.execute(
        "INSERT INTO player_week_conversation_features "
        "(player_id, season_year, week, source_name, audience_bucket, mention_count) "
        "VALUES (100, 2025, 12, 'r/QBs', 'fan', 30)",
    )
    db.execute(
        "INSERT INTO player_week_conversation_features "
        "(player_id, season_year, week, source_name, audience_bucket, mention_count) "
        "VALUES (100, 2025, 12, 'all', 'fan', 80)",  # excluded
    )
    n = fetch_player_source_count(db, player_id=100, season_year=2025, week=12)
    assert n == 2


def test_fetch_player_source_count_empty_db(empty_db: Database) -> None:
    assert fetch_player_source_count(empty_db, player_id=100, season_year=2025, week=12) == 0


# ---------------------------------------------------------------------------
# render_provenance_chip
# ---------------------------------------------------------------------------

def test_render_chip_basic_shape() -> None:
    html = render_provenance_chip(247, 5)
    assert 'class="provenance-chip"' in html
    assert "247 posts" in html
    assert "5 sources" in html
    assert 'href="/methodology/fan-intelligence.html"' in html
    assert "methodology" in html
    # The aria-label exposes the raw count for screen readers
    assert 'aria-label="Provenance: 247 posts from 5 sources"' in html


def test_render_chip_pluralizes_one_post() -> None:
    html = render_provenance_chip(1, 1)
    assert "1 post " in html or "1 post<" in html  # singular
    assert "1 source " in html or "1 source<" in html


def test_render_chip_thousand_separator() -> None:
    html = render_provenance_chip(12345, 47)
    assert "12,345" in html


def test_render_chip_returns_empty_for_zero_zero() -> None:
    """No provenance signal → render nothing (caller shows empty-state)."""
    assert render_provenance_chip(0, 0) == ""


def test_render_chip_shows_when_one_nonzero() -> None:
    """Even (mentions=0, sources=N) is worth showing — it's an honest 'no
    posts yet but we are reading N feeds' signal."""
    html = render_provenance_chip(0, 3)
    assert html != ""
    assert "0 posts" in html
    assert "3 sources" in html


def test_render_chip_compact_variant() -> None:
    html = render_provenance_chip(247, 5, compact=True)
    assert "provenance-chip--compact" in html
    assert "based on" not in html  # compact drops the prefix copy
    assert "247" in html
    assert "&middot;" in html
    assert "5" in html


def test_render_chip_xss_escapes_methodology_url() -> None:
    """A malicious caller passing a URL with quotes can't break out of attrs."""
    html = render_provenance_chip(
        10, 2,
        methodology_url='" onmouseover="alert(1)"',
    )
    assert "onmouseover" not in html or "&quot;" in html
    # The literal injected attribute MUST be escaped
    assert 'href="' in html  # the legitimate href attribute opens
    assert "alert(1)" not in html or "&quot;" in html


def test_render_chip_custom_methodology_url() -> None:
    html = render_provenance_chip(
        50, 4,
        methodology_url="/methodology/custom.html",
    )
    assert 'href="/methodology/custom.html"' in html


# ---------------------------------------------------------------------------
# CSS contract
# ---------------------------------------------------------------------------

def test_css_has_required_selectors() -> None:
    for selector in (
        ".provenance-chip",
        ".provenance-chip strong",
        ".provenance-chip__link",
        ".provenance-chip__link:hover",
        ".provenance-chip--compact",
    ):
        assert selector in PROVENANCE_CHIP_CSS, f"missing rule for {selector}"


def test_css_uses_var_fallback_chains() -> None:
    """Tokens must var() through fallback chains so the chip degrades
    on hosts that haven't loaded team-pages tokens."""
    # Pick three load-bearing token usages
    for token in ("--fg-muted", "--fg-primary", "--accent-primary"):
        assert re.search(
            rf"var\(\s*{re.escape(token)}\s*,",
            PROVENANCE_CHIP_CSS,
        ), f"{token} usage missing fallback"


def test_css_is_nonempty() -> None:
    assert len(PROVENANCE_CHIP_CSS) > 500


# ---------------------------------------------------------------------------
# End-to-end happy path (fetch + render)
# ---------------------------------------------------------------------------

def test_end_to_end_fetch_then_render(db: Database) -> None:
    """Real-world flow: count distinct sources, render the chip."""
    sources = [
        ("r/CFB", 50),
        ("r/AlabamaFootball", 100),
        ("r/SEC", 75),
        ("r/CollegeFootball", 30),
    ]
    for src, n in sources:
        db.execute(
            "INSERT INTO team_week_conversation_features "
            "(team_id, season_year, week, source_name, audience_bucket, mention_count) "
            "VALUES (333, 2025, 12, ?, 'fan', ?)",
            (src, n),
        )
    db.execute(
        "INSERT INTO team_week_conversation_features "
        "(team_id, season_year, week, source_name, audience_bucket, mention_count) "
        "VALUES (333, 2025, 12, 'all', 'fan', 255)",
    )
    n_sources = fetch_source_count(db, team_id=333, season_year=2025, week=12)
    html = render_provenance_chip(mentions=255, sources=n_sources)
    assert n_sources == 4
    assert "255 posts" in html
    assert "4 sources" in html
