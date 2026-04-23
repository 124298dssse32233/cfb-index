"""Unit tests for cohort aggregator + divergence. Uses ephemeral SQLite DBs."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from cfb_rankings.db import Database
from cfb_rankings.cohorts.aggregate import compute_cohort_week, FLOOR_MIN
from cfb_rankings.cohorts.divergence import compute_divergence_week


def _fresh_db() -> Database:
    tmp = Path(tempfile.mkdtemp()) / "cohorts_test.db"
    db = Database(f"sqlite:///{tmp.as_posix()}")
    db.execute("""
        create table source_registry (
            source_registry_id integer primary key autoincrement,
            source_id text unique, source_name text, tier text,
            cohort_weights text, max_publication_form text, ingest_method text
        )
    """)
    db.execute("""
        create table conversation_documents (
            conversation_document_id integer primary key autoincrement,
            source_name text, source_id text
        )
    """)
    db.execute("""
        create table conversation_document_targets (
            id integer primary key autoincrement,
            conversation_document_id integer,
            season_year integer, week integer, team_id integer, sentiment_score real
        )
    """)
    db.execute("""
        create table team_cohort_week (
            team_id integer, cohort text, week text,
            effective_n real, sentiment_score real, volume integer,
            top_source_ids text, confidence_tier text,
            created_at_utc text, updated_at_utc text,
            primary key (team_id, cohort, week)
        )
    """)
    db.execute("""
        create table team_cohort_divergence_week (
            team_id integer, week text, divergence_score real,
            num_cohorts_qualifying integer,
            created_at_utc text, updated_at_utc text,
            primary key (team_id, week)
        )
    """)
    return db


def _seed_source(db: Database, source_id: str, tier: str, **weights: float) -> None:
    db.execute(
        "insert into source_registry (source_id, source_name, tier, cohort_weights, max_publication_form) "
        "values (:sid, :sn, :t, :w, 'aggregate')",
        {"sid": source_id, "sn": source_id, "t": tier, "w": json.dumps(weights)},
    )


def _seed_doc(db: Database, source_id: str, team_id: int, sentiment: float | None,
              season: int = 2025, week: int = 1) -> None:
    db.execute(
        "insert into conversation_documents (source_name, source_id) values (:sn, :sid)",
        {"sn": source_id, "sid": source_id},
    )
    # Same-row fetch from a fresh connection: query max id.
    doc_row = db.query_one("select max(conversation_document_id) as id from conversation_documents")
    db.execute(
        """
        insert into conversation_document_targets
        (conversation_document_id, season_year, week, team_id, sentiment_score)
        values (:doc, :s, :w, :t, :sent)
        """,
        {"doc": doc_row["id"], "s": season, "w": week, "t": team_id, "sent": sentiment},
    )


def test_floor_rule_suppresses_small_n() -> None:
    db = _fresh_db()
    # tiny weight, only a handful of docs → effective_n << 30
    _seed_source(db, "source_a", "B", millennial=0.5, die_hard=0.2)
    for _ in range(5):
        _seed_doc(db, "source_a", team_id=10, sentiment=0.4)
    result = compute_cohort_week(db, "2025-01")
    assert result["cells_written"] == 2  # millennial + die_hard
    row = db.query_one(
        "select * from team_cohort_week where team_id=10 and cohort='millennial' and week='2025-01'"
    )
    # 5 * 0.5 = 2.5 effective_n; below FLOOR_MIN
    assert row["effective_n"] == 2.5
    assert row["effective_n"] < FLOOR_MIN
    assert row["sentiment_score"] is None  # floor rule
    assert row["volume"] == 5
    assert row["confidence_tier"] == "B"


def test_above_floor_publishes_sentiment() -> None:
    db = _fresh_db()
    _seed_source(db, "source_a", "A", millennial=1.0)
    for _ in range(40):
        _seed_doc(db, "source_a", team_id=10, sentiment=0.5)
    compute_cohort_week(db, "2025-01")
    row = db.query_one(
        "select * from team_cohort_week where team_id=10 and cohort='millennial' and week='2025-01'"
    )
    assert row["effective_n"] == 40.0
    assert abs(row["sentiment_score"] - 0.5) < 1e-9
    assert row["volume"] == 40
    assert row["confidence_tier"] == "A"


def test_worst_tier_ratchet() -> None:
    db = _fresh_db()
    _seed_source(db, "tier_a_src", "A", analytics=0.9)
    _seed_source(db, "tier_c_src", "C", analytics=0.3)
    # both contribute → confidence_tier = C
    for _ in range(30):
        _seed_doc(db, "tier_a_src", team_id=7, sentiment=0.8, week=2)
    for _ in range(10):
        _seed_doc(db, "tier_c_src", team_id=7, sentiment=-0.1, week=2)
    compute_cohort_week(db, "2025-02")
    row = db.query_one(
        "select * from team_cohort_week where team_id=7 and cohort='analytics' and week='2025-02'"
    )
    assert row["confidence_tier"] == "C"


def test_tier_d_excluded_from_aggregation() -> None:
    db = _fresh_db()
    _seed_source(db, "tier_d_src", "D", analytics=1.0)
    for _ in range(200):
        _seed_doc(db, "tier_d_src", team_id=7, sentiment=0.1)
    result = compute_cohort_week(db, "2025-03")
    assert result["cells_written"] == 0  # Tier D skipped entirely


def test_null_sentiment_still_contributes_volume() -> None:
    db = _fresh_db()
    _seed_source(db, "source_a", "B", die_hard=1.0)
    # 50 docs, half with null sentiment
    for i in range(50):
        _seed_doc(db, "source_a", team_id=10, sentiment=None if i % 2 else 0.6)
    compute_cohort_week(db, "2025-01")
    row = db.query_one(
        "select * from team_cohort_week where team_id=10 and cohort='die_hard' and week='2025-01'"
    )
    assert row["effective_n"] == 50.0
    assert row["volume"] == 50
    # only 25 contributed to sentiment sum; weighted mean = 0.6
    assert abs(row["sentiment_score"] - 0.6) < 1e-9


def test_divergence_requires_two_qualifying_cohorts() -> None:
    db = _fresh_db()
    _seed_source(db, "src", "B", millennial=1.0, die_hard=1.0, casual_vibes=1.0)
    for _ in range(30):
        _seed_doc(db, "src", team_id=10, sentiment=0.8, week=5)
    compute_cohort_week(db, "2025-05")
    # manually override one cohort's sentiment_score to create divergence
    db.execute(
        "update team_cohort_week set sentiment_score=0.2 "
        "where team_id=10 and cohort='casual_vibes' and week='2025-05'"
    )
    result = compute_divergence_week(db, "2025-05")
    row = db.query_one(
        "select * from team_cohort_divergence_week where team_id=10 and week='2025-05'"
    )
    assert row["num_cohorts_qualifying"] == 3
    # stdev of [0.8, 0.8, 0.2] ≈ 0.346
    assert row["divergence_score"] is not None
    assert 0.3 < row["divergence_score"] < 0.4


def test_divergence_single_cohort_null_score() -> None:
    db = _fresh_db()
    _seed_source(db, "src", "A", millennial=1.0)
    for _ in range(30):
        _seed_doc(db, "src", team_id=10, sentiment=0.5, week=6)
    compute_cohort_week(db, "2025-06")
    compute_divergence_week(db, "2025-06")
    row = db.query_one(
        "select * from team_cohort_divergence_week where team_id=10 and week='2025-06'"
    )
    assert row["num_cohorts_qualifying"] == 1
    assert row["divergence_score"] is None
