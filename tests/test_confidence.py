"""Tests for cfb_rankings.confidence (v5-7.5 foundation slice).

Locked spec: docs/design-system/33-confidence-signaling.md
Module:      src/cfb_rankings/confidence.py
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path

import pytest

from cfb_rankings.confidence import (
    Band,
    CalibrationThresholds,
    Domain,
    band_for,
    current_quarter,
    get_calibration,
    recompute_thresholds,
    render_confidence_chip,
)
from cfb_rankings.db import Database


# ---------------------------------------------------------------------------
# Pure unit tests
# ---------------------------------------------------------------------------

def test_band_enum_values_match_css_modifiers() -> None:
    """Locked CSS: confidence--high / confidence--medium / etc."""
    assert Band.HIGH.value == "high"
    assert Band.MEDIUM.value == "medium"
    assert Band.LOW.value == "low"
    assert Band.UNSET.value == "unset"


def test_domain_enum_matches_spec_doc() -> None:
    """33-confidence-signaling.md Per-domain thresholds table."""
    assert {d.value for d in Domain} == {
        "fan_intel", "historical", "model", "market", "prediction",
    }


@pytest.mark.parametrize("sample, expected", [
    (0,   Band.UNSET),
    (3,   Band.UNSET),    # below p10=4
    (4,   Band.LOW),      # at p10
    (7,   Band.LOW),      # below p25=8
    (8,   Band.MEDIUM),   # at p25
    (20,  Band.MEDIUM),   # below p75=35
    (35,  Band.HIGH),     # at p75
    (100, Band.HIGH),     # above p75
])
def test_band_for_fan_intel_fallback_thresholds(sample, expected) -> None:
    """Locked fallback: fan_intel p10=4, p25=8, p75=35."""
    assert band_for(sample, "fan_intel") is expected


def test_band_for_accepts_enum_and_string() -> None:
    assert band_for(20, Domain.FAN_INTEL) is band_for(20, "fan_intel")


def test_band_for_rejects_unknown_domain() -> None:
    with pytest.raises(ValueError, match="unknown confidence domain"):
        band_for(10, "made_up_domain")


def test_band_for_rejects_negative_sample() -> None:
    with pytest.raises(ValueError, match="sample_size must be >= 0"):
        band_for(-1, "fan_intel")


def test_calibration_thresholds_pure_band_calculation() -> None:
    """The thresholds dataclass is pure — no DB needed."""
    t = CalibrationThresholds(p10=4, p25=8, p75=35, sample_size_at_calibration=100)
    assert t.band(0) is Band.UNSET
    assert t.band(3) is Band.UNSET
    assert t.band(4) is Band.LOW
    assert t.band(7) is Band.LOW
    assert t.band(8) is Band.MEDIUM
    assert t.band(34) is Band.MEDIUM
    assert t.band(35) is Band.HIGH
    assert t.band(9999) is Band.HIGH


# ---------------------------------------------------------------------------
# render_confidence_chip
# ---------------------------------------------------------------------------

def test_chip_renders_band_css_modifier() -> None:
    html = render_confidence_chip(42, "fan_intel")
    assert 'class="confidence confidence--high"' in html
    assert "n=42" in html


def test_chip_default_label_per_band() -> None:
    assert "High confidence" in render_confidence_chip(50, "fan_intel")
    assert "Medium confidence" in render_confidence_chip(20, "fan_intel")
    assert "Low confidence" in render_confidence_chip(6, "fan_intel")
    assert "Awaiting signal" in render_confidence_chip(1, "fan_intel")


def test_chip_override_label_softens_text_only_not_band() -> None:
    """Editorial-honesty lock: override changes label, NEVER changes band."""
    # sample 12 falls in MEDIUM band (p25=8 .. p75=35)
    html = render_confidence_chip(12, "fan_intel", override_label="Moderate")
    assert "Moderate" in html
    # Band class is STILL medium — colour is sample-derived
    assert 'confidence--medium' in html
    # And it should NOT have downgraded to a softer band
    assert 'confidence--low' not in html
    assert 'confidence--high' not in html


def test_chip_unset_does_not_render_sample_count() -> None:
    """Unset chips suppress the n= suffix per the spec."""
    html = render_confidence_chip(1, "fan_intel")
    assert "Awaiting signal" in html
    assert "n=" not in html


def test_chip_show_sample_false_suppresses_n() -> None:
    html = render_confidence_chip(42, "fan_intel", show_sample=False)
    assert "n=" not in html


def test_chip_escapes_override_label() -> None:
    """Defense against label injection."""
    html = render_confidence_chip(42, "fan_intel", override_label="<script>x</script>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


# ---------------------------------------------------------------------------
# current_quarter
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("month, expected_q", [
    (1, "Q1"), (2, "Q1"), (3, "Q1"),
    (4, "Q2"), (5, "Q2"), (6, "Q2"),
    (7, "Q3"), (8, "Q3"), (9, "Q3"),
    (10, "Q4"), (11, "Q4"), (12, "Q4"),
])
def test_current_quarter_per_month(month, expected_q) -> None:
    now = dt.datetime(2026, month, 15, tzinfo=dt.timezone.utc)
    assert current_quarter(now) == f"2026{expected_q}"


# ---------------------------------------------------------------------------
# DB-backed integration tests — use a real on-disk SQLite via a temp file
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Apply the migration to a fresh DB so tests have the calibration table."""
    db_path = tmp_path / "test.db"
    # cfb_rankings.db.Database expects sqlite:/// URL
    database_url = f"sqlite:///{db_path}"
    d = Database(database_url)

    # Apply just the confidence_calibration migration directly
    migration = Path(__file__).resolve().parent.parent / "migrations" / "20260531_03_confidence_calibration.sql"
    d.apply_sql_file(migration)
    return d


def test_get_calibration_returns_fallback_when_no_row(db: Database) -> None:
    """No calibration row → fallback thresholds."""
    t = get_calibration(Domain.FAN_INTEL, db=db)
    assert t.p10 == 4
    assert t.p25 == 8
    assert t.p75 == 35
    assert t.sample_size_at_calibration == 0


def test_recompute_with_zero_rows_writes_fallback(db: Database) -> None:
    """Empty source tables → recompute writes the fallback row anyway."""
    # The source tables don't exist in our test DB so the SQL will fail — to
    # test the zero-row branch we need to create empty source tables first.
    db.execute("CREATE TABLE conversation_documents (conversation_document_id INTEGER, external_created_at_utc TEXT, collected_at_utc TEXT)")
    db.execute("CREATE TABLE conversation_document_targets (conversation_document_id INTEGER, team_id INTEGER)")
    result = recompute_thresholds(db, Domain.FAN_INTEL)
    assert result.thresholds.p10 == 4
    assert result.thresholds.p25 == 8
    assert result.thresholds.p75 == 35
    assert result.thresholds.sample_size_at_calibration == 0
    # The row should be queryable afterwards
    t = get_calibration(Domain.FAN_INTEL, db=db)
    assert t.p10 == 4
    assert t.sample_size_at_calibration == 0


def test_recompute_idempotent_within_quarter(db: Database) -> None:
    """Two recomputes within the same quarter UPDATE the row, not append."""
    db.execute("CREATE TABLE conversation_documents (conversation_document_id INTEGER, external_created_at_utc TEXT, collected_at_utc TEXT)")
    db.execute("CREATE TABLE conversation_document_targets (conversation_document_id INTEGER, team_id INTEGER)")
    recompute_thresholds(db, Domain.FAN_INTEL)
    recompute_thresholds(db, Domain.FAN_INTEL)
    rows = db.query_all(
        "SELECT COUNT(*) AS n FROM confidence_calibration WHERE domain = 'fan_intel'"
    )
    assert rows[0]["n"] == 1


def test_recompute_computes_real_percentiles(db: Database) -> None:
    """When there IS sample data, compute the percentiles, don't fall back."""
    # Build a small distribution: 1, 2, 3, ..., 100 docs across 100 team-weeks
    db.execute("CREATE TABLE conversation_documents (conversation_document_id INTEGER, external_created_at_utc TEXT, collected_at_utc TEXT)")
    db.execute("CREATE TABLE conversation_document_targets (conversation_document_id INTEGER, team_id INTEGER)")
    # Seed: team=1 has 10 docs in week A, team=2 has 20 docs in week B, etc.
    for team in range(1, 11):
        wk = f"2026-W{team:02d}"
        for doc_idx in range(team * 10):
            cid = team * 1000 + doc_idx
            db.execute(
                "INSERT INTO conversation_documents (conversation_document_id, external_created_at_utc) VALUES (?, ?)",
                (cid, f"2026-{wk[5:7]}-01T00:00:00Z"),
            )
            db.execute(
                "INSERT INTO conversation_document_targets (conversation_document_id, team_id) VALUES (?, ?)",
                (cid, team),
            )
    result = recompute_thresholds(db, Domain.FAN_INTEL)
    # 10 team-weeks with sample counts 10, 20, ..., 100
    # p10 ≈ 10, p25 ≈ 25-ish, p75 ≈ 75-ish
    assert result.thresholds.sample_size_at_calibration == 10
    assert result.thresholds.p10 < result.thresholds.p25 < result.thresholds.p75


def test_band_for_uses_recomputed_thresholds(db: Database) -> None:
    """After recompute, band_for() should pick up the new row, not the fallback."""
    # Create a distribution where the thresholds are clearly different from fallback
    db.execute("CREATE TABLE conversation_documents (conversation_document_id INTEGER, external_created_at_utc TEXT, collected_at_utc TEXT)")
    db.execute("CREATE TABLE conversation_document_targets (conversation_document_id INTEGER, team_id INTEGER)")
    # Insert one giant team-week of 1000 docs so p75 ends up at 1000 not 35
    for i in range(1000):
        db.execute(
            "INSERT INTO conversation_documents (conversation_document_id, external_created_at_utc) VALUES (?, ?)",
            (i, "2026-05-01T00:00:00Z"),
        )
        db.execute(
            "INSERT INTO conversation_document_targets (conversation_document_id, team_id) VALUES (?, ?)",
            (i, 1),
        )
    recompute_thresholds(db, Domain.FAN_INTEL)
    # Now band_for(50, ...) — with fallback that's HIGH (50 > 35), but with the
    # new threshold p75=1000 it's MEDIUM (50 is well below 1000)
    assert band_for(50, "fan_intel", db=db) is Band.UNSET  # below p10=1000
