"""Tests for cfb_rankings.cohorts.player_aggregate.compute_player_week_mood.

Build a minimal schema with conversation_documents +
conversation_document_targets + player_week_conversation_features, seed a
few player-scoped target rows, aggregate, and assert the output row shape
and math.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.cohorts.player_aggregate import (
    SAMPLE_SIGNAL_FLOOR,
    SAMPLE_STANDARD_FLOOR,
    compute_player_week_mood,
)


CARR = 4788
OTHER = 999

SEASON = 2025
WEEK = 12


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    db_path = tmp_path / "pagg.db"
    conn = sqlite3.connect(db_path)
    _schema(conn)
    _seed(conn)
    conn.commit()
    conn.close()
    return Database(str(db_path))


def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE conversation_documents (
            conversation_document_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT,
            source_author_id TEXT,
            source_author_name TEXT,
            source_url TEXT,
            capture_url TEXT,
            body_text TEXT,
            title_text TEXT,
            like_count INTEGER DEFAULT 0,
            reply_count INTEGER DEFAULT 0,
            view_count INTEGER DEFAULT 0
        );
        CREATE TABLE conversation_document_targets (
            conversation_document_target_id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_document_id INTEGER NOT NULL,
            season_year INTEGER,
            week INTEGER,
            game_id INTEGER,
            team_id INTEGER,
            player_id INTEGER,
            target_type TEXT,
            target_key TEXT,
            target_label TEXT,
            affiliation_team_id INTEGER,
            audience_bucket TEXT,
            mention_role TEXT,
            sentiment_label TEXT,
            sentiment_score REAL,
            emotion_primary TEXT,
            emotion_secondary TEXT,
            sarcasm_score REAL,
            toxicity_score REAL,
            confidence_score REAL,
            model_provider TEXT,
            model_name TEXT,
            model_version TEXT,
            is_primary_target INTEGER DEFAULT 0,
            notes TEXT
        );
        CREATE TABLE player_week_conversation_features (
            player_week_conversation_feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER,
            source_name TEXT,
            audience_bucket TEXT NOT NULL,
            mention_count INTEGER DEFAULT 0,
            unique_author_count INTEGER DEFAULT 0,
            positive_doc_count INTEGER DEFAULT 0,
            neutral_doc_count INTEGER DEFAULT 0,
            negative_doc_count INTEGER DEFAULT 0,
            mean_sentiment_score REAL,
            net_sentiment_score REAL,
            joy_share REAL, anger_share REAL, fear_share REAL,
            trust_share REAL, sadness_share REAL, surprise_share REAL,
            attention_score REAL,
            sample_quality_score REAL,
            sarcasm_risk TEXT,
            top_storyline_json TEXT,
            top_quote_json TEXT,
            sample_n INTEGER,
            sample_window TEXT,
            confidence_floor TEXT,
            model_version TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX ux_pwcf_keys ON player_week_conversation_features (
            player_id, season_year, week, COALESCE(source_name, ''), audience_bucket
        );
        """
    )


def _doc(conn, *, body, author, author_name="fan", source="reddit_cfb",
         likes=0, replies=0, url="https://example.test/x"):
    cur = conn.execute(
        """INSERT INTO conversation_documents
           (source_name, source_author_id, source_author_name, source_url,
            body_text, like_count, reply_count, view_count)
           VALUES (?,?,?,?,?,?,?,0)""",
        (source, author, author_name, url, body, likes, replies),
    )
    return cur.lastrowid


def _target(conn, doc_id, *, player_id, bucket, sentiment, emotion=None,
            sarcasm=0.0, confidence=0.8, team_id=1):
    conn.execute(
        """INSERT INTO conversation_document_targets
           (conversation_document_id, season_year, week, player_id,
            target_type, audience_bucket, sentiment_score, emotion_primary,
            sarcasm_score, confidence_score, affiliation_team_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (doc_id, SEASON, WEEK, player_id, "player", bucket, sentiment,
         emotion, sarcasm, confidence, team_id),
    )


def _seed(conn: sqlite3.Connection) -> None:
    # Carr: 15 fan mentions, mostly positive; 3 rivals (negative); 2 media (positive).
    for i in range(15):
        doc = _doc(conn, body=f"Carr looked sharp in week {WEEK}" if i % 2 == 0
                   else f"Notre Dame's QB play is carrying them, Carr MVP",
                   author=f"nd_fan_{i}", likes=10 + i, replies=1)
        _target(conn, doc, player_id=CARR, bucket="fan", sentiment=0.5 + 0.01 * i,
                emotion="joy" if i % 3 else "trust", confidence=0.9)

    for i in range(3):
        doc = _doc(conn, body=f"Carr is overrated vs real competition",
                   author=f"usc_fan_{i}", likes=5, replies=0)
        _target(conn, doc, player_id=CARR, bucket="rival", sentiment=-0.5,
                emotion="anger", confidence=0.8)

    for i in range(2):
        doc = _doc(conn, body=f"Top-10 QB watch: Carr in the mix",
                   author=f"beat_{i}", author_name="ESPN analyst",
                   source="beat_espn", likes=50, replies=20)
        _target(conn, doc, player_id=CARR, bucket="media", sentiment=0.4,
                emotion="trust", confidence=0.95)

    # OTHER player: only 2 fan mentions (below signal floor).
    for i in range(2):
        doc = _doc(conn, body="barely made the depth chart",
                   author=f"other_fan_{i}")
        _target(conn, doc, player_id=OTHER, bucket="fan", sentiment=0.0,
                confidence=0.6)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _fetch_rows(db: Database, **filters):
    where = " and ".join(f"{k}=:{k}" for k in filters)
    return db.query_all(
        f"select * from player_week_conversation_features where {where}",
        filters,
    )


def test_aggregate_writes_one_row_per_bucket_per_source(db: Database) -> None:
    result = compute_player_week_mood(db, f"{SEASON}-{WEEK:02d}")
    assert result["rows_read"] == 22  # 15 + 3 + 2 + 2
    assert result["players_touched"] == 2
    # Carr has fan/rival/media (3 buckets), plus OTHER has fan (1 bucket) = 4 cells.
    assert result["cells_written"] == 4


def test_carr_fan_row_math(db: Database) -> None:
    compute_player_week_mood(db, f"{SEASON}-{WEEK:02d}")
    rows = _fetch_rows(db, player_id=CARR, audience_bucket="fan")
    assert len(rows) == 1
    r = rows[0]
    assert r["mention_count"] == 15
    # Every fan row has a distinct author_id, so unique_author_count == 15.
    assert r["unique_author_count"] == 15
    # All sentiments > POS_CUTOFF (0.5..0.64).
    assert r["positive_doc_count"] == 15
    assert r["neutral_doc_count"] == 0
    assert r["negative_doc_count"] == 0
    # mean_sentiment ≈ (0.5 + ... + 0.64) / 15 ≈ 0.57.
    assert 0.55 < r["mean_sentiment_score"] < 0.60
    # net_sentiment == (pos - neg) / total == 1.0
    assert r["net_sentiment_score"] == 1.0
    # Confidence floor: mention_count (15) is >=12 but <40 → 'sample'.
    assert r["confidence_floor"] == "sample"
    assert r["sarcasm_risk"] == "low"


def test_carr_rival_does_not_pollute_fan(db: Database) -> None:
    compute_player_week_mood(db, f"{SEASON}-{WEEK:02d}")
    fan = _fetch_rows(db, player_id=CARR, audience_bucket="fan")[0]
    rival = _fetch_rows(db, player_id=CARR, audience_bucket="rival")[0]
    assert fan["mean_sentiment_score"] > 0
    assert rival["mean_sentiment_score"] == pytest.approx(-0.5, abs=0.01)


def test_top_quote_pulled_from_bucket(db: Database) -> None:
    compute_player_week_mood(db, f"{SEASON}-{WEEK:02d}")
    fan = _fetch_rows(db, player_id=CARR, audience_bucket="fan")[0]
    assert fan["top_quote_json"] is not None
    payload = json.loads(fan["top_quote_json"])
    assert "Carr" in payload["text"]
    # Fan bucket quote must be a positive-sentiment one, not a rival's negative.
    assert float(payload.get("sentiment_score") or 0) > 0


def test_below_floor_still_writes_row_with_thin_confidence(db: Database) -> None:
    compute_player_week_mood(db, f"{SEASON}-{WEEK:02d}")
    # OTHER has 2 fan mentions — below SAMPLE_SIGNAL_FLOOR (12). Row still written;
    # the aggregate is responsible only for math. Gating lives in the reader
    # (fetch_player_mood_profile / compute_player_mood_index).
    rows = _fetch_rows(db, player_id=OTHER, audience_bucket="fan")
    assert len(rows) == 1
    assert rows[0]["mention_count"] == 2
    assert rows[0]["confidence_floor"] == "thin"
    assert SAMPLE_SIGNAL_FLOOR > rows[0]["mention_count"]


def test_upsert_is_idempotent(db: Database) -> None:
    compute_player_week_mood(db, f"{SEASON}-{WEEK:02d}")
    compute_player_week_mood(db, f"{SEASON}-{WEEK:02d}")
    # Re-running must not duplicate cells.
    rows = _fetch_rows(db, player_id=CARR)
    bucket_keys = sorted((r["audience_bucket"], r["source_name"]) for r in rows)
    assert len(bucket_keys) == len(set(bucket_keys))


def test_player_filter_narrows_work(db: Database) -> None:
    result = compute_player_week_mood(db, f"{SEASON}-{WEEK:02d}", players=[OTHER])
    assert result["players_touched"] == 1
    assert result["cells_written"] == 1


def test_sample_standard_floor_constant() -> None:
    assert SAMPLE_STANDARD_FLOOR > SAMPLE_SIGNAL_FLOOR


def test_round_trip_aggregate_then_mood_profile(db: Database) -> None:
    """Aggregate the fixture rows, then read via fetch_player_mood_profile.

    This is the end-to-end contract: raw targets → aggregate → reader sees
    has_data=True with the expected belief direction.
    """
    from cfb_rankings.fan_intelligence import fetch_player_mood_profile

    compute_player_week_mood(db, f"{SEASON}-{WEEK:02d}")

    profile = fetch_player_mood_profile(db, CARR, SEASON, WEEK)
    assert profile["has_data"] is True, "aggregate → reader contract broken"
    assert profile["sample"]["mentions"] == 15
    assert profile["sample"]["rival_mentions"] == 3
    assert profile["sample"]["media_mentions"] == 2
    assert profile["belief"]["score"] is not None
    # Fan chatter is overwhelmingly positive; belief must trend positive.
    assert profile["belief"]["score"] > 0.0
    # Top quote should be from the fan bucket (positive sentiment).
    assert profile["top_quote"] is not None
    assert profile["top_quote"]["bucket"] == "fan"
