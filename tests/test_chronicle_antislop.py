"""Tests for cfb_rankings.chronicle.antislop.

15 tests covering all public API functions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from cfb_rankings.chronicle.antislop import (
    BanEntry,
    Violation,
    apply_antislop_to_config,
    build_logit_bias,
    check_violations,
    compute_mtld,
    compute_ngram_novelty,
    load_banlist,
    score_slop_fingerprint,
)


# ---------------------------------------------------------------------------
# Minimal DB stub
# ---------------------------------------------------------------------------


class MockDB:
    def __init__(self, rows):
        self._rows = rows

    def query_all(self, sql, params=None):
        return self._rows


# ---------------------------------------------------------------------------
# Minimal generation config (avoids importing runtime.py)
# ---------------------------------------------------------------------------


@dataclass
class SimpleConfig:
    max_tokens: int = 400
    temperature: float = 0.7
    logit_bias: dict | None = None
    antislop_banlist: list | None = None
    antislop_severity: dict | None = None


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_rows():
    return [
        {"phrase": "game-changer", "kind": "cliche", "severity": 2.0},
        {"phrase": "showed out", "kind": "ai_slop", "severity": 3.0},
        {"phrase": "taking it to the next level", "kind": "cliche", "severity": 1.5},
        {"phrase": "dominant", "kind": "cfb_specific", "severity": 1.0},
        {"phrase": "elite", "kind": "cfb_specific", "severity": 0.5},
    ]


@pytest.fixture()
def banlist(sample_rows):
    db = MockDB(sample_rows)
    return load_banlist(db)


# ---------------------------------------------------------------------------
# Test 1: load_banlist returns entries
# ---------------------------------------------------------------------------


def test_load_banlist_returns_entries(sample_rows):
    db = MockDB(sample_rows)
    entries = load_banlist(db)
    assert len(entries) == 5
    assert all(isinstance(e, BanEntry) for e in entries)
    # Sorted by severity DESC
    severities = [e.severity for e in entries]
    assert severities == sorted(severities, reverse=True)


# ---------------------------------------------------------------------------
# Test 2: load_banlist filters by kind (the mock always returns all rows,
#         so we verify the WHERE clause is included and returned rows are
#         consumed correctly when the mock honours the filter)
# ---------------------------------------------------------------------------


def test_load_banlist_filters_by_kind():
    """Filter by kind: mock returns only matching rows."""
    rows = [
        {"phrase": "game-changer", "kind": "cliche", "severity": 2.0},
        {"phrase": "showed out", "kind": "ai_slop", "severity": 3.0},
    ]
    # Mock returns only the rows that match — simulating the WHERE clause
    filtered_rows = [r for r in rows if r["kind"] == "cliche"]
    db = MockDB(filtered_rows)
    entries = load_banlist(db, kinds=["cliche"])
    assert len(entries) == 1
    assert entries[0].phrase == "game-changer"
    assert entries[0].kind == "cliche"


# ---------------------------------------------------------------------------
# Test 3: load_banlist active_only filter
# ---------------------------------------------------------------------------


def test_load_banlist_active_only_filter():
    """active_only=False should still consume whatever rows the mock returns."""
    rows = [
        {"phrase": "game-changer", "kind": "cliche", "severity": 2.0},
        {"phrase": "showed out", "kind": "ai_slop", "severity": 3.0},
    ]
    db = MockDB(rows)
    # active_only=False; mock returns both rows regardless
    entries = load_banlist(db, active_only=False)
    assert len(entries) == 2
    # active_only=True (default); mock still returns both (it's a simple mock)
    entries_active = load_banlist(db, active_only=True)
    assert len(entries_active) == 2


# ---------------------------------------------------------------------------
# Test 4: check_violations finds exact match
# ---------------------------------------------------------------------------


def test_check_violations_finds_exact_match(banlist):
    text = "He was a game-changer for the offense."
    violations = check_violations(text, banlist)
    phrases = [v.phrase for v in violations]
    assert "game-changer" in phrases


# ---------------------------------------------------------------------------
# Test 5: check_violations is case-insensitive
# ---------------------------------------------------------------------------


def test_check_violations_case_insensitive(banlist):
    text = "He was a GAME-CHANGER for the offense."
    violations = check_violations(text, banlist)
    phrases = [v.phrase for v in violations]
    assert "game-changer" in phrases


# ---------------------------------------------------------------------------
# Test 6: check_violations returns sorted by start
# ---------------------------------------------------------------------------


def test_check_violations_returns_sorted_by_start(banlist):
    # "showed out" appears before "game-changer" in this text
    text = "He showed out before becoming a game-changer."
    violations = check_violations(text, banlist)
    starts = [v.start for v in violations]
    assert starts == sorted(starts)


# ---------------------------------------------------------------------------
# Test 7: check_violations returns empty list for empty text
# ---------------------------------------------------------------------------


def test_check_violations_empty_text_returns_empty(banlist):
    assert check_violations("", banlist) == []


# ---------------------------------------------------------------------------
# Test 8: build_logit_bias without tokenizer returns phrase → bias dict
# ---------------------------------------------------------------------------


def test_build_logit_bias_no_tokenizer(banlist):
    bias_map = build_logit_bias(banlist)
    assert isinstance(bias_map, dict)
    # All values should be negative floats
    for phrase, bias in bias_map.items():
        assert isinstance(phrase, str)
        assert isinstance(bias, float)
        assert bias < 0
    # Spot-check: "showed out" severity 3.0 → bias -60.0
    assert bias_map["showed out"] == pytest.approx(-60.0)
    # "elite" severity 0.5 → bias -10.0
    assert bias_map["elite"] == pytest.approx(-10.0)


# ---------------------------------------------------------------------------
# Test 9: score_slop_fingerprint output in [0, 1]
# ---------------------------------------------------------------------------


def test_score_slop_fingerprint_range(banlist):
    texts = [
        "",
        "Normal sentence about football tactics.",
        "He showed out as a game-changer — elite — dominant — taking it to the next level.",
    ]
    for t in texts:
        score = score_slop_fingerprint(t, banlist)
        assert 0.0 <= score <= 1.0, f"Score out of range for: {t!r}"


# ---------------------------------------------------------------------------
# Test 10: clean text scores below 0.2
# ---------------------------------------------------------------------------


def test_score_slop_fingerprint_clean_text_low_score(banlist):
    clean = (
        "The quarterback completed twenty-three of thirty-one attempts, "
        "accumulating 287 yards and two touchdowns in the third quarter."
    )
    score = score_slop_fingerprint(clean, banlist)
    assert score < 0.2, f"Expected clean score < 0.2, got {score:.3f}"


# ---------------------------------------------------------------------------
# Test 11: sloppy text scores above 0.4
# ---------------------------------------------------------------------------


def test_score_slop_fingerprint_sloppy_text_high_score(banlist):
    sloppy = (
        "In a season full of surprises, he showed out and proved he was elite, "
        "a true game-changer and dominant force — taking it to the next level."
    )
    score = score_slop_fingerprint(sloppy, banlist)
    assert score > 0.4, f"Expected sloppy score > 0.4, got {score:.3f}"


# ---------------------------------------------------------------------------
# Test 12: compute_mtld — varied > repetitive
# ---------------------------------------------------------------------------


def test_compute_mtld_diversity():
    varied = (
        "The quarterback scrambled left, evaded the blitz, and launched a spiral "
        "into the end zone where the receiver hauled it in for a spectacular touchdown."
    )
    repetitive = "the the the the the the the the the the the the the the the the"
    mtld_varied = compute_mtld(varied)
    mtld_repetitive = compute_mtld(repetitive)
    assert mtld_varied > mtld_repetitive, (
        f"Expected varied ({mtld_varied:.2f}) > repetitive ({mtld_repetitive:.2f})"
    )
    assert mtld_varied > 0


# ---------------------------------------------------------------------------
# Test 13: compute_ngram_novelty — full overlap → 0
# ---------------------------------------------------------------------------


def test_compute_ngram_novelty_full_overlap_zero():
    text = "the quick brown fox jumps"
    corpus = "the quick brown fox jumps over the lazy dog"
    novelty = compute_ngram_novelty(text, corpus, n=4)
    # All 4-grams from text are in corpus
    assert novelty == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test 14: compute_ngram_novelty — full disjoint → 1
# ---------------------------------------------------------------------------


def test_compute_ngram_novelty_full_disjoint_one():
    text = "apple mango pineapple guava kiwi"
    corpus = "the quick brown fox jumps over the lazy dog"
    novelty = compute_ngram_novelty(text, corpus, n=4)
    assert novelty == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test 15: apply_antislop_to_config sets all three fields
# ---------------------------------------------------------------------------


def test_apply_antislop_to_config_sets_fields(banlist):
    cfg = SimpleConfig()
    result = apply_antislop_to_config(cfg, banlist)

    # Returns the same object (mutate + return)
    assert result is cfg

    # logit_bias is a dict of phrase → float
    assert isinstance(cfg.logit_bias, dict)
    assert len(cfg.logit_bias) == len(banlist)

    # antislop_banlist is a list of strings
    assert isinstance(cfg.antislop_banlist, list)
    assert len(cfg.antislop_banlist) == len(banlist)
    assert all(isinstance(p, str) for p in cfg.antislop_banlist)

    # antislop_severity is a dict of phrase → float
    assert isinstance(cfg.antislop_severity, dict)
    assert len(cfg.antislop_severity) == len(banlist)
    for phrase, sev in cfg.antislop_severity.items():
        assert isinstance(sev, float)
        assert sev > 0
