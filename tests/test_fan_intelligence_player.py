"""Tests for player-scope fan intelligence (Feature B).

Covers:
  - High-mention player (Carr) → real belief profile with cohort buckets.
  - Low-mention player → _empty_player_profile skeleton.
  - Freshman with zero rows → skeleton.
  - Bucket isolation: a rival row must NOT leak into the fan-bucket belief.

In-memory SQLite fixture mirrors the production schema (just the columns we
exercise, not every field).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.fan_intelligence import (
    MIN_AUTHORS_FOR_SIGNAL,
    MIN_MENTIONS_FOR_SIGNAL,
    fetch_player_mood_profile,
)


CARR = 4788
LOW_MENTION = 50001
FRESHMAN = 50002


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    db_path = tmp_path / "pwcf.db"
    conn = sqlite3.connect(db_path)
    _schema(conn)
    _seed(conn)
    conn.commit()
    conn.close()
    return Database(str(db_path))


def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE player_week_conversation_features (
            player_week_conversation_feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_year INTEGER, week INTEGER, player_id INTEGER,
            team_id INTEGER, source_name TEXT, audience_bucket TEXT,
            mention_count INTEGER DEFAULT 0, unique_author_count INTEGER DEFAULT 0,
            positive_doc_count INTEGER DEFAULT 0,
            neutral_doc_count INTEGER DEFAULT 0,
            negative_doc_count INTEGER DEFAULT 0,
            mean_sentiment_score REAL, net_sentiment_score REAL,
            joy_share REAL, anger_share REAL, fear_share REAL,
            trust_share REAL, sadness_share REAL, surprise_share REAL,
            attention_score REAL, sample_quality_score REAL,
            sarcasm_risk TEXT, top_storyline_json TEXT, top_quote_json TEXT,
            sample_n INTEGER, sample_window TEXT, confidence_floor TEXT,
            model_version TEXT, created_at TEXT
        );
        """
    )


def _ins(conn, *, player_id, bucket, mentions, authors, net_sent, source="all",
         season=2025, week=12, top_quote_json=None, sarcasm_risk="low"):
    conn.execute(
        """INSERT INTO player_week_conversation_features(
            season_year, week, player_id, team_id, source_name, audience_bucket,
            mention_count, unique_author_count, net_sentiment_score,
            mean_sentiment_score, top_quote_json, sarcasm_risk, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
        (season, week, player_id, 1, source, bucket, mentions, authors,
         net_sent, net_sent, top_quote_json, sarcasm_risk),
    )


def _seed(conn: sqlite3.Connection) -> None:
    # Carr: healthy fan + national + rival + media rows.
    _ins(conn, player_id=CARR, bucket="fan", mentions=142, authors=38, net_sent=0.65,
         top_quote_json='{"text": "Carr is the real deal — ND pick-six aside, he\'s top-10 at worst.", '
                        '"author_pseudonym": "NDFaithful", "source_url": "https://reddit.com/r/notredamefootball/x", '
                        '"sentiment_score": 0.72}')
    _ins(conn, player_id=CARR, bucket="national", mentions=88, authors=42, net_sent=0.31)
    _ins(conn, player_id=CARR, bucket="rival", mentions=36, authors=24, net_sent=-0.42,
         top_quote_json='{"text": "Carr looked average against us", "author_pseudonym": "uscfan"}')
    _ins(conn, player_id=CARR, bucket="media", mentions=22, authors=18, net_sent=0.4)
    # History rows in earlier weeks (fan bucket) so swing populates.
    for wk, sent in [(8, 0.55), (9, 0.5), (10, 0.6), (11, 0.62)]:
        _ins(conn, player_id=CARR, bucket="fan", mentions=120, authors=30,
             net_sent=sent, week=wk)

    # Low-mention backup QB: 6 mentions — below gate.
    _ins(conn, player_id=LOW_MENTION, bucket="fan", mentions=6, authors=3, net_sent=0.1)

    # Freshman: no rows at all.


def test_high_mention_player_has_real_profile(db: Database) -> None:
    profile = fetch_player_mood_profile(db, CARR, 2025, 12)
    assert profile["has_data"] is True
    assert profile["player_id"] == CARR
    assert profile["sample"]["mentions"] == 142
    assert profile["sample"]["authors"] == 38
    assert profile["sample"]["rival_mentions"] == 36
    assert profile["sample"]["national_mentions"] == 88
    assert profile["sample"]["media_mentions"] == 22

    # Confidence is populated with a label.
    assert profile["confidence"]["label"]
    # Belief is driven by the fan bucket — rival's negative sentiment MUST NOT leak in.
    belief_score = profile["belief"]["score"]
    assert belief_score is not None
    # Fan net_sent = 0.65 → belief score should be clearly positive.
    assert belief_score > 0.0
    # Rival negative sentiment is not the fan belief.
    assert belief_score > -0.42


def test_top_quote_present_when_supplied(db: Database) -> None:
    profile = fetch_player_mood_profile(db, CARR, 2025, 12)
    tq = profile.get("top_quote")
    assert tq is not None
    assert "real deal" in tq["text"]
    assert tq["author_pseudonym"] == "NDFaithful"
    # Quote must come from the fan bucket (not the rival one).
    assert tq["bucket"] == "fan"


def test_low_mention_player_returns_empty(db: Database) -> None:
    profile = fetch_player_mood_profile(db, LOW_MENTION, 2025, 12)
    assert profile["has_data"] is False
    # Shape is identical to the team-scope empty — no branching needed upstream.
    for key in ("confidence", "sample", "belief", "reality_gap", "respect_gap",
                "swing", "cohesion", "rival_heat", "archetype", "storylines",
                "top_quote", "updated_label"):
        assert key in profile, f"missing empty-profile key: {key}"
    assert profile["belief"]["score"] is None


def test_freshman_with_no_rows_returns_empty(db: Database) -> None:
    profile = fetch_player_mood_profile(db, FRESHMAN, 2025, 12)
    assert profile["has_data"] is False
    assert profile["sample"]["mentions"] == 0
    assert profile["top_quote"] is None


def test_bucket_isolation_no_leak(db: Database) -> None:
    """Rival rows contribute to `rival_mentions` but NOT to belief."""
    profile = fetch_player_mood_profile(db, CARR, 2025, 12)
    # Belief score reflects fan net_sent (0.65), NOT a weighted blend with rival (-0.42).
    # A leak would push belief toward the mean of fan/rival ~ 0.115.
    assert profile["belief"]["score"] > 0.3, (
        f"rival-to-fan leak suspected: belief={profile['belief']['score']}"
    )


def test_gate_constants_are_honored(db: Database) -> None:
    # Sanity: if MIN_MENTIONS_FOR_SIGNAL gate is > 12, the test fixtures might need
    # tuning. This guards against a gate-config drift breaking the tests silently.
    assert MIN_MENTIONS_FOR_SIGNAL <= 20
    assert MIN_AUTHORS_FOR_SIGNAL <= 10
