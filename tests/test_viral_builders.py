"""Tests for the v5-10e DB-backed builders.

The builders take a Database handle and synthesize the kwargs dict
for each share-card renderer. Empty/missing tables → fallback data;
populated tables → real values.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cfb_rankings.viral.builders import (
    _first_sentence,
    build_daily_movers_input,
    build_mood_map_input,
    build_pregame_pack_input,
    build_quote_card_input,
    build_receipt_card_input,
)
from cfb_rankings.viral.daily_movers import MoverCard
from cfb_rankings.viral.mood_map import Cluster, Mover
from cfb_rankings.viral.pregame_pack import TeamSide
from cfb_rankings.db import Database


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Empty DB — no tables. Builders must fall back gracefully."""
    return Database(f"sqlite:///{tmp_path / 'test.db'}")


@pytest.fixture
def db_with_schema(tmp_path: Path) -> Database:
    """DB with the empty tables the builders query, but no rows."""
    d = Database(f"sqlite:///{tmp_path / 'test.db'}")
    d.execute("""
        CREATE TABLE fanbase_mood_weekly (
            team_id INTEGER, week_start_date TEXT, mood_score INTEGER,
            delta_from_prev_week INTEGER, top_cause_label TEXT
        )
    """)
    d.execute("""
        CREATE TABLE teams (
            team_id INTEGER, short_name TEXT, current_conference_id INTEGER
        )
    """)
    d.execute("CREATE TABLE conferences (conference_id INTEGER, short_name TEXT)")
    d.execute("""
        CREATE TABLE hub_issue_metadata (
            cover_headline TEXT, cover_dek TEXT, cover_chart_caption TEXT,
            week_start_date TEXT
        )
    """)
    d.execute("""
        CREATE TABLE daily_editions (edition_date TEXT)
    """)
    d.execute("""
        CREATE TABLE daily_takes (
            edition_date TEXT, rank_position INTEGER, headline TEXT,
            body TEXT, source_count INTEGER, cited_sources_json TEXT
        )
    """)
    d.execute("""
        CREATE TABLE predictive_claims (
            claim_text TEXT, claim_summary_short TEXT, source_slug TEXT,
            source_published_at TEXT, outcome_text TEXT, aged_well_pct REAL,
            outcome_resolved_at TEXT, outcome_verdict TEXT,
            outcome_resolved INTEGER
        )
    """)
    return d


# ---------------------------------------------------------------------------
# _first_sentence
# ---------------------------------------------------------------------------

def test_first_sentence_extracts_to_period() -> None:
    body = "This is the first sentence. This is the second."
    assert _first_sentence(body) == "This is the first sentence."


def test_first_sentence_handles_question_mark() -> None:
    body = "Was this a question? Probably."
    assert _first_sentence(body) == "Was this a question?"


def test_first_sentence_truncates_long_no_punctuation() -> None:
    body = "a" * 200
    out = _first_sentence(body, max_chars=140)
    assert len(out) <= 140
    assert out.endswith("…")


def test_first_sentence_returns_full_short_body() -> None:
    body = "Short."
    assert _first_sentence(body) == "Short."


# ---------------------------------------------------------------------------
# build_mood_map_input — empty DB and populated DB paths
# ---------------------------------------------------------------------------

def test_mood_map_builder_empty_db_returns_fallback(db: Database) -> None:
    """Empty DB (no tables) → builder uses W048 mockup composition."""
    kwargs = build_mood_map_input(db)
    assert "when_label" in kwargs
    assert kwargs["hero_number"] == "47 of 130"
    assert isinstance(kwargs["clusters"], list)
    assert len(kwargs["clusters"]) == 11  # 11 conference clusters
    # Mover fallbacks
    assert len(kwargs["up_movers"]) == 4
    assert len(kwargs["down_movers"]) == 4
    assert kwargs["up_movers"][0].abbr == "OSU"
    assert kwargs["down_movers"][0].abbr == "MICH"


def test_mood_map_builder_schema_only_falls_back(db_with_schema: Database) -> None:
    """Tables exist but are empty → still fallback data."""
    kwargs = build_mood_map_input(db_with_schema)
    assert len(kwargs["clusters"]) == 11
    assert kwargs["up_movers"][0].abbr == "OSU"  # fallback


def test_mood_map_builder_uses_real_data_when_present(db_with_schema: Database) -> None:
    """When fanbase_mood_weekly is populated, builder uses that data."""
    db_with_schema.execute(
        "INSERT INTO teams VALUES (231, 'ALA', 1)"
    )
    db_with_schema.execute(
        "INSERT INTO teams VALUES (232, 'OSU', 2)"
    )
    db_with_schema.execute(
        "INSERT INTO conferences VALUES (1, 'SEC')"
    )
    db_with_schema.execute(
        "INSERT INTO conferences VALUES (2, 'BIG TEN')"
    )
    db_with_schema.execute(
        "INSERT INTO fanbase_mood_weekly VALUES (231, '2026-05-12', 32, -6, 'ordinary contender')"
    )
    db_with_schema.execute(
        "INSERT INTO fanbase_mood_weekly VALUES (232, '2026-05-12', 86, 8, '5-star trust me')"
    )
    db_with_schema.execute(
        "INSERT INTO hub_issue_metadata VALUES ('Real headline.', 'Real dek.', 'cap', '2026-05-12')"
    )
    kwargs = build_mood_map_input(db_with_schema)
    # Real data should drive the hero
    assert kwargs["hero_sentence"] == "Real headline."
    # And the movers should reflect the populated rows
    assert any(m.abbr == "OSU" and m.delta == "+8" for m in kwargs["up_movers"])
    assert any(m.abbr == "ALA" and m.delta == "-6" for m in kwargs["down_movers"])


def test_mood_map_builder_clusters_match_layout() -> None:
    kwargs = build_mood_map_input(Database("sqlite:///:memory:"))
    labels = [c.label for c in kwargs["clusters"]]
    assert labels == [
        "SEC", "BIG TEN", "ACC", "BIG 12", "PAC", "AAC",
        "MWC", "CUSA", "SUN BELT", "MAC", "FBS IND.",
    ]


# ---------------------------------------------------------------------------
# build_quote_card_input
# ---------------------------------------------------------------------------

def test_quote_card_builder_empty_db(db: Database) -> None:
    kwargs = build_quote_card_input(db)
    assert "quote" in kwargs
    assert "attribution" in kwargs
    # Fallback quote
    assert "dead zone" in kwargs["quote"]


def test_quote_card_builder_with_real_take(db_with_schema: Database) -> None:
    db_with_schema.execute(
        "INSERT INTO daily_editions VALUES ('2026-05-13')"
    )
    db_with_schema.execute(
        """
        INSERT INTO daily_takes
        VALUES ('2026-05-13', 1, 'Real headline', 'First sentence here. Second sentence.', 3, '[]')
        """
    )
    kwargs = build_quote_card_input(db_with_schema)
    assert kwargs["quote"] == "First sentence here."
    assert "3 sources" in kwargs["footer_meta"]


# ---------------------------------------------------------------------------
# build_receipt_card_input
# ---------------------------------------------------------------------------

def test_receipt_card_builder_returns_none_when_no_hits(db_with_schema: Database) -> None:
    """No resolved hits → builder returns None (don't fake receipts)."""
    assert build_receipt_card_input(db_with_schema) is None


def test_receipt_card_builder_returns_kwargs_when_hit_present(db_with_schema: Database) -> None:
    db_with_schema.execute(
        """
        INSERT INTO predictive_claims
        VALUES (
            'The full original claim text. Some more.',
            'Short summary',
            'bill-connelly-espn',
            '2026-04-22T00:00:00',
            'Allar leads at +325.',
            92.0,
            '2026-05-13T00:00:00',
            'hit',
            1
        )
        """
    )
    kwargs = build_receipt_card_input(db_with_schema)
    assert kwargs is not None
    assert kwargs["original_claim_date"] == "2026-04-22"
    assert kwargs["original_claim_quote"] == "Short summary"
    assert kwargs["original_attribution"] == "bill-connelly-espn"
    assert kwargs["aged_well_pct"] == 92


# ---------------------------------------------------------------------------
# build_daily_movers_input
# ---------------------------------------------------------------------------

def test_daily_movers_builder_empty_db_fallback(db: Database) -> None:
    kwargs = build_daily_movers_input(db)
    movers = kwargs["movers"]
    assert len(movers) == 6
    # Fallback list starts with OSU + ends with AUB
    assert movers[0].abbr == "OSU"
    assert movers[-1].abbr == "AUB"
    # Mix of up + down
    assert any(m.direction == "up" for m in movers)
    assert any(m.direction == "down" for m in movers)


def test_daily_movers_builder_uses_real_data_when_present(db_with_schema: Database) -> None:
    db_with_schema.execute("INSERT INTO teams VALUES (1, 'OSU', 2)")
    db_with_schema.execute("INSERT INTO teams VALUES (2, 'MICH', 2)")
    db_with_schema.execute("INSERT INTO conferences VALUES (2, 'BIG TEN')")
    db_with_schema.execute(
        "INSERT INTO fanbase_mood_weekly VALUES (1, '2026-05-12', 86, 8, '5-star trust me')"
    )
    db_with_schema.execute(
        "INSERT INTO fanbase_mood_weekly VALUES (2, '2026-05-12', 32, -15, 'Moore presser')"
    )
    kwargs = build_daily_movers_input(db_with_schema)
    movers = kwargs["movers"]
    # Sorted by absolute delta: Michigan -15 first, then OSU +8
    assert movers[0].abbr == "MICH"
    assert movers[0].direction == "down"
    assert movers[0].delta == "-15"
    assert movers[1].abbr == "OSU"
    assert movers[1].direction == "up"
    assert movers[1].delta == "+8"


def test_daily_movers_builder_excludes_zero_deltas(db_with_schema: Database) -> None:
    db_with_schema.execute("INSERT INTO teams VALUES (1, 'X', 2)")
    db_with_schema.execute("INSERT INTO conferences VALUES (2, 'BIG TEN')")
    db_with_schema.execute(
        "INSERT INTO fanbase_mood_weekly VALUES (1, '2026-05-12', 50, 0, 'nothing')"
    )
    kwargs = build_daily_movers_input(db_with_schema)
    # Only row had delta=0 → falls back to mockup
    assert kwargs["movers"][0].abbr == "OSU"  # fallback


def test_daily_movers_builder_truncates_reason(db_with_schema: Database) -> None:
    db_with_schema.execute("INSERT INTO teams VALUES (1, 'TEX', 1)")
    db_with_schema.execute("INSERT INTO conferences VALUES (1, 'SEC')")
    db_with_schema.execute(
        "INSERT INTO fanbase_mood_weekly VALUES (1, '2026-05-12', 75, 5, ?)",
        ("a very long reason that exceeds the 32-character truncation point for sure",),
    )
    kwargs = build_daily_movers_input(db_with_schema)
    assert len(kwargs["movers"][0].reason) <= 32


# ---------------------------------------------------------------------------
# build_pregame_pack_input
# ---------------------------------------------------------------------------

@pytest.fixture
def db_pregame(tmp_path: Path) -> Database:
    """DB with the schema build_pregame_pack_input queries."""
    d = Database(f"sqlite:///{tmp_path / 'pregame.db'}")
    d.execute("""
        CREATE TABLE games (
            game_id INTEGER PRIMARY KEY, season_year INTEGER, week INTEGER,
            start_time_utc TEXT, status TEXT,
            home_team_id INTEGER, away_team_id INTEGER
        )
    """)
    d.execute("""
        CREATE TABLE teams (
            team_id INTEGER, short_name TEXT, school_name TEXT, slug TEXT
        )
    """)
    d.execute("""
        CREATE TABLE power_ratings_weekly (
            team_id INTEGER, season_year INTEGER, week INTEGER,
            power_rating REAL
        )
    """)
    d.execute("""
        CREATE TABLE team_seasons (
            team_id INTEGER, season_year INTEGER,
            wins INTEGER, losses INTEGER
        )
    """)
    d.execute("""
        CREATE TABLE fanbase_mood_weekly (
            team_id INTEGER, week_start_date TEXT, mood_score INTEGER,
            top_cause_label TEXT, delta_from_prev_week INTEGER, sample_size INTEGER
        )
    """)
    return d


def test_pregame_pack_returns_none_when_no_games(db_pregame: Database) -> None:
    assert build_pregame_pack_input(db_pregame) is None


def test_pregame_pack_returns_none_when_no_schema(db: Database) -> None:
    """No tables exist → returns None (don't fake the pregame card)."""
    assert build_pregame_pack_input(db) is None


def test_pregame_pack_with_explicit_game_id(db_pregame: Database) -> None:
    """When game_id is provided, builder reads that specific game."""
    db_pregame.execute("INSERT INTO teams VALUES (1, 'ALA', 'Alabama', 'alabama')")
    db_pregame.execute("INSERT INTO teams VALUES (2, 'LSU', 'LSU', 'lsu')")
    db_pregame.execute(
        "INSERT INTO games VALUES (42, 2026, 11, '2026-11-08T19:30:00', 'scheduled', 1, 2)"
    )
    db_pregame.execute("INSERT INTO team_seasons VALUES (1, 2026, 7, 1)")
    db_pregame.execute("INSERT INTO team_seasons VALUES (2, 2026, 6, 2)")
    db_pregame.execute(
        "INSERT INTO fanbase_mood_weekly VALUES (1, '2026-11-01', 76, 'home favorite', 0, 100)"
    )
    db_pregame.execute(
        "INSERT INTO fanbase_mood_weekly VALUES (2, '2026-11-01', 58, 'underdog', 0, 100)"
    )
    kwargs = build_pregame_pack_input(db_pregame, game_id=42)
    assert kwargs is not None
    # The home team is Alabama (team_id=1) per the games row
    assert kwargs["home"].abbr == "ALA"
    assert kwargs["away"].abbr == "LSU"
    assert kwargs["home"].record == "7-1"
    assert kwargs["away"].record == "6-2"
    assert kwargs["home"].mood == 76
    assert kwargs["away"].mood == 58
    assert "42" in kwargs["url_line"]  # game_id baked into URL
