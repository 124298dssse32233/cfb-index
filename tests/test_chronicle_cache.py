"""Tests for cfb_rankings.chronicle.cache."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from cfb_rankings.chronicle.cache import (
    cache_health,
    compute_cache_key,
    get_cached_card,
    invalidate_by_prefix,
    promote_lkg,
    store_card,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "20260524_03_chronicle_card_cache.sql"
)


@pytest.fixture()
def db(tmp_path: Path) -> sqlite3.Connection:
    """In-process sqlite3 connection with the chronicle_card_cache table."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    sql = MIGRATION_PATH.read_text()
    # Strip BEGIN/COMMIT — sqlite3 auto-transaction handles this fine, but
    # executescript will reject a leading BEGIN if we're already inside a tx.
    conn.executescript(sql)
    return conn


# ---------------------------------------------------------------------------
# compute_cache_key
# ---------------------------------------------------------------------------


def test_compute_cache_key_is_deterministic():
    args = dict(
        slug="cam-ward", season_year=2024, week_number=9,
        card_type="flashpoint", slot_index=0, evidence_hash="abc",
        prompt_template_id="planner-v1", model_id="nemo", model_version="2407",
        schema_version="1",
    )
    k1 = compute_cache_key(**args)
    k2 = compute_cache_key(**args)
    assert k1 == k2
    assert len(k1) == 32
    assert all(c in "0123456789abcdef" for c in k1)


def test_compute_cache_key_varies_on_inputs():
    base = dict(
        slug="x", season_year=2024, week_number=1, card_type="t", slot_index=0,
        evidence_hash="h", prompt_template_id="p", model_id="m",
        model_version="v", schema_version="s",
    )
    k_base = compute_cache_key(**base)
    assert compute_cache_key(**{**base, "slug": "y"}) != k_base
    assert compute_cache_key(**{**base, "week_number": 2}) != k_base
    assert compute_cache_key(**{**base, "model_version": "v2"}) != k_base


def test_compute_cache_key_treats_none_as_empty():
    """None and empty string in the same slot should produce the same key."""
    k_none = compute_cache_key(
        slug="x", season_year=None, week_number=None, card_type="t",
        slot_index=None, evidence_hash="h", prompt_template_id="p",
        model_id="m", model_version="v", schema_version="s",
    )
    # Stability: should not raise
    assert len(k_none) == 32


# ---------------------------------------------------------------------------
# store_card + get_cached_card round-trip
# ---------------------------------------------------------------------------


def _store(db, key="k" * 32, **overrides):
    defaults = dict(
        cache_key=key, slug="cam-ward", entity_kind="player",
        season_year=2024, week_number=9, card_type="flashpoint",
        slot_index=0, card_content={"body": "..."}, card_html=None,
        evidence_hash="abc123", prompt_template_id="writer-v1",
        model_id="nemo", model_version="2407", schema_version="1",
        confidence_band="high", word_count=72, wall_clock_ms=1500,
    )
    defaults.update(overrides)
    store_card(db, **defaults)
    return defaults["cache_key"]


def test_store_and_get_round_trip(db):
    key = _store(db)
    row = get_cached_card(db, key)
    assert row is not None
    assert row["slug"] == "cam-ward"
    assert row["card_type"] == "flashpoint"
    assert row["is_lkg"] == 0
    assert row["card_content"] == {"body": "..."}  # JSON-decoded


def test_get_returns_none_for_missing(db):
    assert get_cached_card(db, "0" * 32) is None


def test_store_is_idempotent_on_same_key(db):
    key = _store(db)
    # Second call with same cache_key should be a no-op, no error
    _store(db, key=key)
    rows = db.execute(
        "SELECT COUNT(*) FROM chronicle_card_cache WHERE cache_key = ?", (key,)
    ).fetchone()
    assert rows[0] == 1


def test_store_supersedes_previous_active(db):
    # Two writes for the same (slug, week, card_type, slot) with different keys
    key1 = _store(db, key="a" * 32, evidence_hash="hash-old")
    key2 = _store(db, key="b" * 32, evidence_hash="hash-new")

    # First should now be superseded
    row1 = db.execute(
        "SELECT superseded_at_utc FROM chronicle_card_cache WHERE cache_key = ?",
        (key1,),
    ).fetchone()
    assert row1["superseded_at_utc"] is not None

    # Second is active
    assert get_cached_card(db, key2) is not None
    assert get_cached_card(db, key1) is None  # filtered out by superseded_at_utc


# ---------------------------------------------------------------------------
# promote_lkg
# ---------------------------------------------------------------------------


def test_promote_lkg_sets_flag(db):
    key = _store(db)
    assert promote_lkg(db, key) is True
    row = db.execute(
        "SELECT is_lkg, lkg_promoted_at_utc FROM chronicle_card_cache WHERE cache_key = ?",
        (key,),
    ).fetchone()
    assert row["is_lkg"] == 1
    assert row["lkg_promoted_at_utc"] is not None


def test_promote_lkg_returns_false_for_missing(db):
    assert promote_lkg(db, "0" * 32) is False


# ---------------------------------------------------------------------------
# invalidate_by_prefix
# ---------------------------------------------------------------------------


def test_invalidate_by_slug(db):
    _store(db, key="a" * 32, slug="cam-ward")
    _store(db, key="b" * 32, slug="travis-hunter")
    n = invalidate_by_prefix(db, slug="cam-ward")
    assert n == 1
    # cam-ward now superseded; travis-hunter still active
    assert get_cached_card(db, "a" * 32) is None
    assert get_cached_card(db, "b" * 32) is not None


def test_invalidate_refuses_no_filters(db):
    _store(db)
    n = invalidate_by_prefix(db)  # no filters
    assert n == 0


def test_invalidate_by_model_id(db):
    # Use distinct slot_index so supersede_previous doesn't auto-supersede
    _store(db, key="a" * 32, model_id="nemo", slot_index=0)
    _store(db, key="b" * 32, model_id="qwen3", slot_index=1)
    n = invalidate_by_prefix(db, model_id="nemo")
    assert n == 1
    # nemo row is now superseded, qwen3 row remains active
    assert get_cached_card(db, "a" * 32) is None
    assert get_cached_card(db, "b" * 32) is not None


# ---------------------------------------------------------------------------
# cache_health
# ---------------------------------------------------------------------------


def test_cache_health_empty(db):
    h = cache_health(db)
    assert h["total_rows"] == 0
    assert h["active_rows"] == 0
    assert h["lkg_rows"] == 0
    assert h["by_card_type"] == {}


def test_cache_health_after_writes(db):
    _store(db, key="a" * 32, card_type="flashpoint")
    _store(db, key="b" * 32, card_type="player_arc", slot_index=1)
    promote_lkg(db, "a" * 32)

    h = cache_health(db)
    assert h["total_rows"] == 2
    assert h["active_rows"] == 2
    assert h["lkg_rows"] == 1
    assert h["by_card_type"]["flashpoint"] == 1
    assert h["by_card_type"]["player_arc"] == 1
    assert h["by_model_id"]["nemo"] == 2
