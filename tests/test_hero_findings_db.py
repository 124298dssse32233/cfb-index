"""DB-backed tests for the wired-up hero_findings generators.

Generates a tiny in-memory schema, populates 1-2 rows, then verifies the
generator returns a HeroFinding with the right shape. Empty-table tests
verify the contract that generators fall through to None when there's
nothing meaningful to surface.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.hero_findings import (
    FindingKind,
    generate_daily_finding,
    generate_heisman_finding,
    generate_team_finding,
)


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Empty DB with the schema the generators need."""
    d = Database(f"sqlite:///{tmp_path / 'test.db'}")
    d.execute("""
        CREATE TABLE daily_takes (
            edition_date TEXT, rank_position INTEGER, headline TEXT,
            body TEXT, source_count INTEGER, primary_entity_slug TEXT,
            cited_sources_json TEXT
        )
    """)
    d.execute("""
        CREATE TABLE heisman_market_odds_weekly (
            season_year INTEGER, week INTEGER, player_id INTEGER,
            team_id INTEGER, provider TEXT, source_name TEXT,
            source_player_key TEXT, player_name TEXT, team_name TEXT,
            market_name TEXT, american_odds INTEGER, decimal_odds REAL,
            implied_probability REAL, notes TEXT, created_at TEXT
        )
    """)
    d.execute("""
        CREATE TABLE fanbase_mood_weekly (
            mood_weekly_id INTEGER PRIMARY KEY,
            team_id INTEGER, week_start_date TEXT, mood_score INTEGER,
            delta_from_prev_week INTEGER, top_cause_token TEXT,
            top_cause_label TEXT, sample_size INTEGER,
            ingested_at TEXT, source TEXT, sample_authors INTEGER,
            confidence REAL, sample_n INTEGER, sample_window TEXT,
            confidence_floor TEXT, model_version TEXT
        )
    """)
    return d


# ---------------------------------------------------------------------------
# generate_daily_finding
# ---------------------------------------------------------------------------

def test_daily_finding_returns_none_when_table_empty(db: Database) -> None:
    assert generate_daily_finding(db, edition_date="2026-05-13") is None


def test_daily_finding_returns_lead_claim_when_data_present(db: Database) -> None:
    db.execute(
        """INSERT INTO daily_takes
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("2026-05-13", 1, "Dead Air at the Top",
         "Here's the thing about a slow news Tuesday. Movement is happening in DMs.",
         3, "", '["The Athletic","Solid Verbal","Ty Hildenbrandt"]'),
    )
    f = generate_daily_finding(db, edition_date="2026-05-13")
    assert f is not None
    assert f.kind is FindingKind.LEAD_CLAIM
    assert f.number == "3"
    assert "slow news Tuesday" in f.sentence
    # Source count goes on the CHIP label (editorial honesty: 3 sources
    # isn't really HIGH confidence in the fan_intel sense, but the chip
    # carries source-count framing so reader knows the receipts).
    assert f.confidence_override_label == "3 sources cited"
    assert "Lead take" in f.sample_caption


def test_daily_finding_handles_single_source(db: Database) -> None:
    db.execute(
        """INSERT INTO daily_takes
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("2026-05-13", 1, "h", "Single sentence.", 1, "", "[]"),
    )
    f = generate_daily_finding(db, edition_date="2026-05-13")
    assert f is not None
    # Singular: "1 source cited" not "1 sources cited"
    assert f.confidence_override_label == "1 source cited"


def test_daily_finding_ignores_rank_2_takes(db: Database) -> None:
    db.execute("""INSERT INTO daily_takes VALUES
                  ('2026-05-13', 2, 'rank-2', 'Body 2.', 5, '', '[]')""")
    assert generate_daily_finding(db, edition_date="2026-05-13") is None


# ---------------------------------------------------------------------------
# generate_heisman_finding
# ---------------------------------------------------------------------------

def test_heisman_finding_returns_none_when_no_market_data(db: Database) -> None:
    assert generate_heisman_finding(db, season_year=2026) is None


def test_heisman_finding_returns_none_with_only_one_week(db: Database) -> None:
    """Need ≥2 weeks of data to compute a delta."""
    db.execute("""INSERT INTO heisman_market_odds_weekly
        (season_year, week, player_id, player_name, team_name, provider, implied_probability)
        VALUES (2026, 1, 100, 'Allar', 'Penn State', 'BookA', 0.15)""")
    assert generate_heisman_finding(db, season_year=2026) is None


def test_heisman_finding_emits_race_shift_when_data_present(db: Database) -> None:
    """Two weeks × 2 books for the same player → 1 mover identified."""
    for prov in ("BookA", "BookB"):
        # Week 1: Allar at 5% implied
        db.execute("""INSERT INTO heisman_market_odds_weekly
            (season_year, week, player_id, player_name, team_name, provider, implied_probability)
            VALUES (2026, 1, 100, 'Drew Allar', 'Penn State', ?, 0.05)""", (prov,))
        # Week 2: Allar jumps to 23% (the +18 pt mover from the mockup)
        db.execute("""INSERT INTO heisman_market_odds_weekly
            (season_year, week, player_id, player_name, team_name, provider, implied_probability)
            VALUES (2026, 2, 100, 'Drew Allar', 'Penn State', ?, 0.23)""", (prov,))
    f = generate_heisman_finding(db, season_year=2026)
    assert f is not None
    assert f.kind is FindingKind.RACE_SHIFT
    assert f.number.startswith("+") or f.number.startswith("−")
    assert "Drew Allar" in f.sentence
    assert f.confidence_domain == "market"
    assert "sportsbook" in f.sample_caption


def test_heisman_finding_skips_players_with_one_sportsbook(db: Database) -> None:
    """Need ≥2 sportsbooks per player to clear confidence floor."""
    db.execute("""INSERT INTO heisman_market_odds_weekly
        (season_year, week, player_id, player_name, team_name, provider, implied_probability)
        VALUES (2026, 1, 100, 'Allar', 'PSU', 'BookA', 0.05)""")
    db.execute("""INSERT INTO heisman_market_odds_weekly
        (season_year, week, player_id, player_name, team_name, provider, implied_probability)
        VALUES (2026, 2, 100, 'Allar', 'PSU', 'BookA', 0.23)""")
    # Only 1 book for player 100 — should be skipped
    f = generate_heisman_finding(db, season_year=2026)
    assert f is None


# ---------------------------------------------------------------------------
# generate_team_finding
# ---------------------------------------------------------------------------

def test_team_finding_returns_none_when_table_empty(db: Database) -> None:
    assert generate_team_finding(db, team_id=231, season_year=2026) is None


def test_team_finding_returns_none_when_delta_is_small(db: Database) -> None:
    """Small deltas (|d| < 3) don't earn hero-finding real estate."""
    db.execute("""INSERT INTO fanbase_mood_weekly
        (team_id, week_start_date, mood_score, delta_from_prev_week,
         top_cause_label, sample_size)
        VALUES (231, '2026-05-12', 60, 2, 'minor news', 100)""")
    assert generate_team_finding(db, team_id=231, season_year=2026) is None


def test_team_finding_emits_belief_delta_for_real_shift(db: Database) -> None:
    """Michigan's -15 mood drop from the W047 hub_issue example."""
    db.execute("""INSERT INTO fanbase_mood_weekly
        (team_id, week_start_date, mood_score, delta_from_prev_week,
         top_cause_label, sample_size)
        VALUES (130, '2026-04-22', 58, -15, 'Moore presser', 3200)""")
    f = generate_team_finding(db, team_id=130, season_year=2026)
    assert f is not None
    assert f.kind is FindingKind.BELIEF_DELTA
    assert "15" in f.number
    assert "Moore presser" in f.sentence.lower() or "Moore presser" in f.sentence
    assert f.confidence_domain == "fan_intel"
    assert "3200" in f.sample_caption


def test_team_finding_emits_for_positive_delta_too(db: Database) -> None:
    db.execute("""INSERT INTO fanbase_mood_weekly
        (team_id, week_start_date, mood_score, delta_from_prev_week,
         top_cause_label, sample_size)
        VALUES (200, '2026-04-22', 86, 8, '5-star trust me', 1670)""")
    f = generate_team_finding(db, team_id=200, season_year=2026)
    assert f is not None
    assert f.number.startswith("+")


def test_team_finding_handles_missing_cause_label(db: Database) -> None:
    """When top_cause_label is empty, sentence still parses."""
    db.execute("""INSERT INTO fanbase_mood_weekly
        (team_id, week_start_date, mood_score, delta_from_prev_week,
         top_cause_label, sample_size)
        VALUES (300, '2026-04-22', 70, 10, NULL, 500)""")
    f = generate_team_finding(db, team_id=300, season_year=2026)
    assert f is not None
    assert f.number == "+10"
