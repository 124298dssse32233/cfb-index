"""Tests for cfb_rankings.cmdk.index_builder (Sprint v5-11.5 foundation).

Builds an in-memory DB with the schema each indexer reads, verifies:
  * Each indexer returns the right SearchItem shape
  * Missing tables degrade gracefully (return empty list, no raise)
  * Profiled-vs-unprofiled team partitioning works
  * Player indexer is bounded by ``players_max``
  * Stable JSON output via write_search_index
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cfb_rankings.cmdk import (
    KIND_VALUES,
    SearchItem,
    build_search_index,
    index_conferences,
    index_editions,
    index_methodology,
    index_players,
    index_profiles,
    index_teams,
    write_search_index,
)
from cfb_rankings.cmdk.index_builder import index_mailbag
from cfb_rankings.db import Database


# ---------------------------------------------------------------------------
# Type contract
# ---------------------------------------------------------------------------

def test_item_kind_values_match_spec() -> None:
    assert KIND_VALUES == (
        "team", "profile", "player", "edition", "mailbag",
        "conference", "methodology",
    )


def test_search_item_is_frozen() -> None:
    item = SearchItem(kind="team", title="Alabama", url="/teams/alabama.html")
    with pytest.raises(Exception):
        item.title = "changed"


def test_search_item_as_dict_omits_defaults() -> None:
    """A bare SearchItem produces a minimal JSON dict."""
    item = SearchItem(kind="team", title="X", url="/x")
    d = item.as_dict()
    assert d == {"kind": "team", "title": "X", "url": "/x"}
    # Tier 5 (default) is omitted; subtitle/aliases empty → omitted
    assert "tier" not in d
    assert "subtitle" not in d
    assert "aliases" not in d


def test_search_item_as_dict_includes_non_defaults() -> None:
    item = SearchItem(
        kind="profile", title="Alabama", url="/teams/alabama.html",
        subtitle="Profiled program", tier=1, aliases=("rolltide", "tide"),
    )
    d = item.as_dict()
    assert d["subtitle"] == "Profiled program"
    assert d["tier"] == 1
    assert d["aliases"] == ["rolltide", "tide"]


# ---------------------------------------------------------------------------
# DB fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Empty DB with the schemas each indexer reads."""
    d = Database(f"sqlite:///{tmp_path / 'cmdk.db'}")
    d.execute("""
        CREATE TABLE teams (
            team_id INTEGER PRIMARY KEY,
            slug TEXT,
            school_name TEXT,
            short_name TEXT,
            level_code TEXT,
            current_conference_id INTEGER,
            is_active INTEGER
        )
    """)
    d.execute("""
        CREATE TABLE conferences (
            conference_id INTEGER PRIMARY KEY,
            conference_name TEXT,
            conference_short_name TEXT,
            conference_slug TEXT,
            level_code TEXT,
            display_name TEXT,
            member_count INTEGER,
            is_active INTEGER
        )
    """)
    d.execute("""
        CREATE TABLE editions (
            edition_slug TEXT PRIMARY KEY,
            edition_number INTEGER,
            volume INTEGER,
            publish_date TEXT,
            theme_title TEXT,
            status TEXT
        )
    """)
    d.execute("""
        CREATE TABLE mailbag_editions (
            edition_slug TEXT PRIMARY KEY,
            publish_date TEXT,
            status TEXT,
            generated_at_utc TEXT,
            notes TEXT
        )
    """)
    d.execute("""
        CREATE TABLE players (
            player_id INTEGER PRIMARY KEY,
            full_name TEXT,
            first_name TEXT,
            last_name TEXT,
            position TEXT,
            home_state TEXT
        )
    """)
    d.execute("""
        CREATE TABLE player_season_stats (
            player_id INTEGER,
            team_id INTEGER,
            season_year INTEGER,
            PRIMARY KEY (player_id, team_id, season_year)
        )
    """)
    return d


@pytest.fixture
def empty_db(tmp_path: Path) -> Database:
    """DB with no tables at all — every indexer must degrade to []."""
    return Database(f"sqlite:///{tmp_path / 'empty.db'}")


# ---------------------------------------------------------------------------
# Teams + profiles
# ---------------------------------------------------------------------------

def test_index_teams_basic(db: Database) -> None:
    db.execute(
        "INSERT INTO teams (team_id, slug, school_name, level_code, is_active) "
        "VALUES (1, 'alabama', 'Alabama', 'FBS', 1)",
    )
    db.execute(
        "INSERT INTO teams (team_id, slug, school_name, level_code, is_active) "
        "VALUES (2, 'eastern-kentucky', 'Eastern Kentucky', 'FCS', 1)",
    )
    items = index_teams(db, profiled_slugs=frozenset())
    assert len(items) == 2
    by_slug = {i.url: i for i in items}
    bama = by_slug["/teams/alabama.html"]
    assert bama.title == "Alabama"
    assert bama.tier == 2  # FBS
    assert "FBS" in bama.subtitle
    eku = by_slug["/teams/eastern-kentucky.html"]
    assert eku.tier == 3  # FCS


def test_index_teams_skips_profiled_slugs(db: Database) -> None:
    """Profiled teams skip team indexing (they're indexed as profiles)."""
    db.execute(
        "INSERT INTO teams (team_id, slug, school_name, level_code, is_active) "
        "VALUES (1, 'alabama', 'Alabama', 'FBS', 1)",
    )
    db.execute(
        "INSERT INTO teams (team_id, slug, school_name, level_code, is_active) "
        "VALUES (2, 'tulsa', 'Tulsa', 'FBS', 1)",
    )
    items = index_teams(db, profiled_slugs=frozenset({"alabama"}))
    assert len(items) == 1
    assert items[0].title == "Tulsa"


def test_index_teams_skips_inactive(db: Database) -> None:
    db.execute(
        "INSERT INTO teams (team_id, slug, school_name, is_active) "
        "VALUES (1, 'defunct', 'Defunct College', 0)",
    )
    assert index_teams(db) == []


def test_index_teams_empty_db_returns_empty(empty_db: Database) -> None:
    """Missing teams table → graceful empty."""
    assert index_teams(empty_db) == []


def test_index_profiles_basic(db: Database) -> None:
    db.execute(
        "INSERT INTO teams (team_id, slug, school_name) "
        "VALUES (1, 'alabama', 'Alabama')",
    )
    db.execute(
        "INSERT INTO teams (team_id, slug, school_name) "
        "VALUES (2, 'georgia', 'Georgia')",
    )
    items = index_profiles(db, profiled_slugs=frozenset({"alabama", "georgia"}))
    assert len(items) == 2
    assert all(i.kind == "profile" for i in items)
    assert all(i.tier == 1 for i in items)


def test_index_profiles_empty_slugs(db: Database) -> None:
    assert index_profiles(db, profiled_slugs=frozenset()) == []


# ---------------------------------------------------------------------------
# Players (bounded)
# ---------------------------------------------------------------------------

def test_index_players_basic(db: Database) -> None:
    db.execute(
        "INSERT INTO teams (team_id, slug, school_name, short_name) "
        "VALUES (1, 'alabama', 'Alabama', 'Bama')",
    )
    db.execute(
        "INSERT INTO players (player_id, full_name, position) "
        "VALUES (100, 'Bryce Underwood', 'QB')",
    )
    db.execute(
        "INSERT INTO player_season_stats (player_id, team_id, season_year) "
        "VALUES (100, 1, 2026)",
    )
    items = index_players(db, season_year=2026)
    assert len(items) == 1
    underwood = items[0]
    assert underwood.title == "Bryce Underwood"
    assert "QB" in underwood.subtitle
    assert "Bama" in underwood.subtitle
    assert underwood.url == "/players/100.html"


def test_index_players_respects_max(db: Database) -> None:
    """players_max caps the SELECT."""
    db.execute(
        "INSERT INTO teams (team_id, slug, school_name) "
        "VALUES (1, 'alabama', 'Alabama')",
    )
    for i in range(50):
        db.execute(
            "INSERT INTO players (player_id, full_name) VALUES (?, ?)",
            (1000 + i, f"Player {i}"),
        )
        db.execute(
            "INSERT INTO player_season_stats (player_id, team_id, season_year) "
            "VALUES (?, 1, 2026)",
            (1000 + i,),
        )
    items = index_players(db, season_year=2026, players_max=10)
    assert len(items) == 10


def test_index_players_no_stats_table_returns_empty(empty_db: Database) -> None:
    assert index_players(empty_db, season_year=2026) == []


def test_index_players_no_season_returns_empty(db: Database) -> None:
    """No player_season_stats rows → no season → empty result."""
    assert index_players(db) == []


# ---------------------------------------------------------------------------
# Editions, mailbag, conferences
# ---------------------------------------------------------------------------

def test_index_editions_basic(db: Database) -> None:
    db.execute(
        "INSERT INTO editions (edition_slug, edition_number, publish_date, "
        "theme_title, status) VALUES ('2026-w19', 19, '2026-05-09', "
        "'The Spring Wire', 'published')",
    )
    items = index_editions(db)
    assert len(items) == 1
    assert items[0].title == "The Spring Wire"
    assert items[0].url == "/editions/2026-w19/"
    assert "2026-05-09" in items[0].subtitle


def test_index_editions_skips_drafts(db: Database) -> None:
    db.execute(
        "INSERT INTO editions (edition_slug, status) VALUES ('draft-x', 'draft')",
    )
    assert index_editions(db) == []


def test_index_mailbag_basic(db: Database) -> None:
    db.execute(
        "INSERT INTO mailbag_editions (edition_slug, publish_date, status) "
        "VALUES ('2026-w19-mailbag', '2026-05-10', 'published')",
    )
    items = index_mailbag(db)
    assert len(items) == 1
    assert items[0].title == "Mailbag — 2026-w19-mailbag"
    assert items[0].url == "/mailbag/2026-w19-mailbag/"


def test_index_conferences_basic(db: Database) -> None:
    db.execute(
        "INSERT INTO conferences (conference_id, conference_name, "
        "conference_short_name, conference_slug, level_code, member_count, "
        "is_active) VALUES (1, 'Southeastern Conference', 'SEC', 'sec', "
        "'FBS', 16, 1)",
    )
    items = index_conferences(db)
    assert len(items) == 1
    sec = items[0]
    assert sec.url == "/conferences/sec.html"
    assert "FBS" in sec.subtitle
    assert "16 teams" in sec.subtitle


def test_index_conferences_skips_no_slug(db: Database) -> None:
    """Conferences without a slug AND without short_name → skipped."""
    db.execute(
        "INSERT INTO conferences (conference_id, conference_name) "
        "VALUES (1, 'Mystery League')",
    )
    assert index_conferences(db) == []


# ---------------------------------------------------------------------------
# Methodology (static)
# ---------------------------------------------------------------------------

def test_index_methodology_returns_fixed_list() -> None:
    items = index_methodology()
    assert len(items) >= 4
    # Every methodology item is tier 4
    assert all(i.tier == 4 for i in items)
    # The methodology index page is included
    assert any(i.url == "/methodology/" for i in items)


# ---------------------------------------------------------------------------
# Aggregate + writer
# ---------------------------------------------------------------------------

def test_build_search_index_combines_all_categories(db: Database) -> None:
    db.execute(
        "INSERT INTO teams (team_id, slug, school_name, level_code, is_active) "
        "VALUES (1, 'alabama', 'Alabama', 'FBS', 1)",
    )
    db.execute(
        "INSERT INTO conferences (conference_id, conference_name, "
        "conference_slug, is_active) VALUES (1, 'SEC', 'sec', 1)",
    )
    items = build_search_index(db, profiled_slugs=frozenset({"alabama"}))
    kinds = {i.kind for i in items}
    # methodology always present (static) + profile + conference from db
    assert "methodology" in kinds
    assert "profile" in kinds
    assert "conference" in kinds


def test_write_search_index_emits_valid_json(
    db: Database,
    tmp_path: Path,
) -> None:
    db.execute(
        "INSERT INTO teams (team_id, slug, school_name, level_code, is_active) "
        "VALUES (1, 'alabama', 'Alabama', 'FBS', 1)",
    )
    out_path = tmp_path / "search-index.json"
    path, count = write_search_index(
        db, out_path, profiled_slugs=frozenset({"alabama"}),
    )
    assert path == out_path
    assert count >= 1
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert isinstance(payload["items"], list)
    assert len(payload["items"]) == count


def test_write_search_index_minify_default(
    db: Database,
    tmp_path: Path,
) -> None:
    """Default minify=True → single-line JSON."""
    out_path = tmp_path / "search-index.json"
    write_search_index(db, out_path)
    content = out_path.read_text(encoding="utf-8")
    # Minified: no newlines in the body
    assert "\n" not in content


def test_write_search_index_inspectable_when_not_minified(
    db: Database,
    tmp_path: Path,
) -> None:
    out_path = tmp_path / "search-index.json"
    write_search_index(db, out_path, minify=False)
    content = out_path.read_text(encoding="utf-8")
    # Indented form has newlines
    assert "\n" in content


def test_no_pii_leakage_in_player_records(db: Database) -> None:
    """Player records must NOT include home_state in subtitle (PII-adjacent)."""
    db.execute(
        "INSERT INTO teams (team_id, slug, school_name) "
        "VALUES (1, 'alabama', 'Alabama')",
    )
    db.execute(
        "INSERT INTO players (player_id, full_name, position, home_state) "
        "VALUES (100, 'John Doe', 'QB', 'TX')",
    )
    db.execute(
        "INSERT INTO player_season_stats (player_id, team_id, season_year) "
        "VALUES (100, 1, 2026)",
    )
    items = index_players(db, season_year=2026)
    for i in items:
        assert "TX" not in i.subtitle
        assert "TX" not in i.title


# ---------------------------------------------------------------------------
# Defensive: every indexer survives a totally empty DB
# ---------------------------------------------------------------------------

def test_every_indexer_handles_empty_db(empty_db: Database) -> None:
    assert index_teams(empty_db) == []
    assert index_profiles(empty_db, profiled_slugs=frozenset({"alabama"})) == []
    assert index_players(empty_db) == []
    assert index_editions(empty_db) == []
    assert index_mailbag(empty_db) == []
    assert index_conferences(empty_db) == []
    # methodology is static — always non-empty
    assert len(index_methodology()) > 0


def test_build_search_index_on_empty_db(empty_db: Database) -> None:
    """Even a bare DB produces a valid (mostly-methodology-only) index."""
    items = build_search_index(empty_db, profiled_slugs=frozenset())
    assert len(items) >= 1  # methodology always present
    assert all(isinstance(i, SearchItem) for i in items)
