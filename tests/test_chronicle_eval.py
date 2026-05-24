"""Comprehensive tests for chronicle/eval.py.

All tests are heuristic-only (no LLM judge required). The test suite is
designed to run in plain pytest with no extra pip deps beyond the project's
existing requirements.

Run:
    python -m pytest tests/test_chronicle_eval.py -v
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, replace
from typing import Any
from unittest.mock import MagicMock

import pytest

from cfb_rankings.chronicle.eval import (
    AtomicFact,
    BatchEvalReport,
    DriftReport,
    EvalReport,
    FActScoreResult,
    QualityResult,
    VoiceEvalResult,
    decompose_to_atomic_facts,
    detect_drift,
    evaluate_batch,
    evaluate_card,
    score_editorial_quality,
    score_factscore,
    score_voice_g_eval,
    verify_atomic_fact_against_evidence,
    _DEFAULT_SLOP_BANLIST,
    _cosine_distance,
    _split_sentences,
    _tokenize,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@dataclass
class FakeEvidenceRow:
    """Minimal evidence stub — exposes .text and .source_id."""

    text: str
    source_id: str = "ev-001"
    source: str = "cfbi_db"


def _evidence(text: str, source_id: str = "ev-001") -> FakeEvidenceRow:
    return FakeEvidenceRow(text=text, source_id=source_id)


CLEAN_CARD_75W = (
    "Cam Ward completed 28-of-39 passes for 342 yards and three touchdowns "
    "against Florida State, per CFBD play-log data. "
    "His completion rate over the final four games sat at 72 percent, "
    "a stretch that moved Miami from 31st to 14th in SP+ offensive efficiency via the official tracker. "
    "The progression from week eight onward reflects scheme adaptation, not sample-size noise."
)

SLOP_CARD = (
    "This game-changer is truly dominant and elite in every way. "
    "He is an explosive playmaker who is electrifying to watch. "
    "His jaw-dropping, standout performances are unparalleled and second to none. "
    "At the end of the day, when all is said and done, the sky is the limit."
)

LONG_CARD_200W = " ".join(["word"] * 200)


class FakeDb:
    """In-memory DB stub for drift detection tests."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    def query_one(self, sql: str, params: tuple) -> dict | None:
        # Return first row if batch_id matches
        batch_id = params[0] if params else None
        for row in self._rows:
            if row.get("batch_id") == batch_id:
                return row
        return None

    def query_all(self, sql: str, params: tuple) -> list[dict]:
        # Return rows NOT matching current batch_id (simulating historical)
        if len(params) >= 2:
            exclude_batch_id = params[0]
            limit = params[1]
            result = [r for r in self._rows if r.get("batch_id") != exclude_batch_id]
            return result[:limit]
        # Single-param query (e.g., AVG query)
        batch_id = params[0] if params else None
        return [r for r in self._rows if r.get("batch_id") == batch_id]


# ---------------------------------------------------------------------------
# 1. decompose_to_atomic_facts — no-judge fallback
# ---------------------------------------------------------------------------


def test_decompose_no_judge_fallback():
    """Without a judge, decompose_to_atomic_facts uses sentence segmentation."""
    text = (
        "Ward threw for 342 yards. "
        "He had three touchdowns. "
        "Miami won by 14 points."
    )
    facts = decompose_to_atomic_facts(text, judge_backend=None)
    assert len(facts) >= 2, "Should produce at least 2 atomic facts for 3 sentences"
    for fact in facts:
        assert isinstance(fact, AtomicFact)
        assert fact.is_supported is None, "All facts should be unverified initially"
        assert len(fact.text) > 5


def test_decompose_compound_sentence_split():
    """Compound sentences joined by '; ' should be split into sub-facts."""
    text = "Ward rushed for 50 yards; he threw two touchdowns; the team won."
    facts = decompose_to_atomic_facts(text, judge_backend=None)
    assert len(facts) >= 2


def test_decompose_empty_text_returns_empty():
    facts = decompose_to_atomic_facts("", judge_backend=None)
    assert facts == []


# ---------------------------------------------------------------------------
# 2. verify_atomic_fact_against_evidence — heuristic keyword overlap
# ---------------------------------------------------------------------------


def test_verify_atomic_fact_heuristic_supported():
    """A fact whose key terms appear in the evidence pool is marked supported."""
    fact = AtomicFact(
        text="Ward threw 342 yards against Florida State",
        is_supported=None,
    )
    evidence = [
        _evidence("Cam Ward passed for 342 yards in the game against Florida State", "e1"),
        _evidence("Miami offense scored three times", "e2"),
    ]
    result = verify_atomic_fact_against_evidence(fact, evidence, judge_backend=None)
    assert result.is_supported is True
    assert "e1" in result.supporting_evidence_ids


def test_verify_atomic_fact_heuristic_unsupported():
    """A fact with no term overlap in evidence is marked unsupported."""
    fact = AtomicFact(
        text="Ward transferred from Mississippi State",
        is_supported=None,
    )
    evidence = [
        _evidence("Ohio State defeated Michigan 45-10", "e1"),
    ]
    result = verify_atomic_fact_against_evidence(fact, evidence, judge_backend=None)
    assert result.is_supported is False
    assert result.supporting_evidence_ids == []


def test_verify_atomic_fact_empty_key_terms():
    """A fact with only stopwords is assumed supported (cannot falsify)."""
    fact = AtomicFact(text="he is the one", is_supported=None)
    evidence = [_evidence("completely unrelated text xyz")]
    result = verify_atomic_fact_against_evidence(fact, evidence, judge_backend=None)
    assert result.is_supported is True


# ---------------------------------------------------------------------------
# 3. score_factscore — all supported
# ---------------------------------------------------------------------------


def test_score_factscore_passes_when_supported():
    """When all facts are supported by evidence, support_rate == 1.0."""
    card_text = (
        "Ward rushed for yards. "
        "Miami scored three touchdowns. "
        "The victory moved them to second place."
    )
    evidence = [
        _evidence("Ward ran for many yards in the game miami scored touchdowns victory second place"),
    ]
    result = score_factscore(card_text, evidence, judge_backend=None, threshold=0.85)
    assert isinstance(result, FActScoreResult)
    assert result.support_rate == pytest.approx(1.0, abs=0.01)
    assert result.passes is True


# ---------------------------------------------------------------------------
# 4. score_factscore — all unsupported
# ---------------------------------------------------------------------------


def test_score_factscore_fails_when_unsupported():
    """When no facts match evidence, support_rate == 0.0."""
    card_text = (
        "Stetson Bennett threw for 1200 yards in a single quarter. "
        "Georgia defeated Alabama by 90 points. "
        "Bennett won six Heisman trophies consecutively."
    )
    evidence = [
        _evidence("completely unrelated basketball content from nba game"),
    ]
    result = score_factscore(card_text, evidence, judge_backend=None, threshold=0.85)
    assert result.support_rate == pytest.approx(0.0, abs=0.01)
    assert result.passes is False


def test_score_factscore_empty_card():
    """An empty card produces a trivially passing FActScoreResult (no facts to fail)."""
    result = score_factscore("", [], judge_backend=None)
    assert result.support_rate == pytest.approx(1.0, abs=0.01)
    assert result.passes is True


# ---------------------------------------------------------------------------
# 5. score_editorial_quality — word count in target band
# ---------------------------------------------------------------------------


def test_score_editorial_quality_word_count_band():
    """A ~75-word card should have word_count_in_target=True."""
    # Build a card with exactly 75 words
    base = "Ward completed passes for yards and touchdowns against opponents "
    words = (base * 20).split()[:75]
    card = " ".join(words) + " per CFBD data."
    result = score_editorial_quality(card)
    assert result.word_count >= 60
    assert result.word_count <= 90
    assert result.word_count_in_target is True


# ---------------------------------------------------------------------------
# 6. score_editorial_quality — too long
# ---------------------------------------------------------------------------


def test_score_editorial_quality_too_long():
    """A 200-word card should have word_count_in_target=False."""
    result = score_editorial_quality(LONG_CARD_200W)
    assert result.word_count >= 200
    assert result.word_count_in_target is False


# ---------------------------------------------------------------------------
# 7. score_editorial_quality — citation density
# ---------------------------------------------------------------------------


def test_score_editorial_quality_citation_density():
    """A card with 1 citation per ~100 words should pass citation_density_ok."""
    # 80 words + 1 citation = 200 * (1/80) = 2.5 per 200 words > 1.0
    filler = " ".join(["text"] * 79)
    card = filler + " per ESPN data."
    result = score_editorial_quality(card)
    assert result.citation_count >= 1
    assert result.citation_density_per_200w > 1.0
    assert result.citation_density_ok is True


def test_score_editorial_quality_no_citations():
    """A card with zero citations has citation_density_ok=False."""
    card = " ".join(["word"] * 75)  # no citation markers
    result = score_editorial_quality(card)
    assert result.citation_count == 0
    assert result.citation_density_ok is False


# ---------------------------------------------------------------------------
# 8. score_editorial_quality — sentence length variance
# ---------------------------------------------------------------------------


def test_score_editorial_quality_sentence_variance():
    """Mixed short and long sentences should yield variance_ok=True."""
    # Mix a very short sentence with a very long sentence to create high variance
    short = "He won."
    long_sent = (
        "Ward completed twenty-eight of thirty-nine passes for three hundred "
        "forty-two yards and three touchdowns against Florida State last Saturday."
    )
    card = f"{short} {long_sent} {short} {long_sent} He scored."
    result = score_editorial_quality(card)
    # Short=2 words, long ~30 words — variance should be well above 8
    assert result.sentence_length_variance > 8.0
    assert result.sentence_variance_ok is True


def test_score_editorial_quality_uniform_sentences():
    """Sentences of equal length should yield low variance."""
    # 5 sentences of exactly 5 words each
    sent = "He ran very fast today"
    card = ". ".join([sent] * 5) + "."
    result = score_editorial_quality(card)
    assert result.sentence_length_variance == pytest.approx(0.0, abs=1.0)
    assert result.sentence_variance_ok is False


# ---------------------------------------------------------------------------
# 9. score_editorial_quality — em-dash density
# ---------------------------------------------------------------------------


def test_score_editorial_quality_em_dash_density():
    """A card with excessive em-dashes should have em_dash_ok=False."""
    # 10 em-dashes in a ~40-word card => 10/40 * 100 = 25 per 100 words >> 2.0
    em_dashes = " — " * 10
    filler = " ".join(["word"] * 30)
    card = filler + em_dashes
    result = score_editorial_quality(card)
    assert result.em_dash_count == 10
    assert result.em_dash_density > 2.0
    assert result.em_dash_ok is False


def test_score_editorial_quality_em_dash_ok():
    """A card with one em-dash in 80 words should have em_dash_ok=True."""
    card = " ".join(["word"] * 79) + " — great."
    result = score_editorial_quality(card)
    assert result.em_dash_ok is True


# ---------------------------------------------------------------------------
# Confirm QualityResult exposes em_dash_count (via field existence check)
# ---------------------------------------------------------------------------


def test_quality_result_em_dash_count_attribute():
    """QualityResult must expose em_dash_density (used in tests above)."""
    result = score_editorial_quality("Test text — here.")
    assert hasattr(result, "em_dash_density")
    assert result.em_dash_density >= 0.0


# ---------------------------------------------------------------------------
# 10. evaluate_card — ship verdict
# ---------------------------------------------------------------------------


def test_evaluate_card_ship_verdict():
    """A clean, well-sourced, factually-supported card should get verdict=ship."""
    evidence = [
        _evidence(
            "cam ward completed 28 of 39 passes for 342 yards three touchdowns "
            "florida state miami completion rate 72 percent sp offensive efficiency "
            "week eight scheme adaptation final four games"
        ),
    ]
    corpus = [
        "Ward's efficiency numbers tell a story of scheme adaptation, not luck.",
        "The margin closed to near-zero by week eight per CFBD data.",
    ]
    report = evaluate_card(
        card_text=CLEAN_CARD_75W,
        card_cache_key="test-cache-key-001",
        evidence=evidence,
        judge_backend=None,
        voice_corpus_samples=corpus,
    )
    assert isinstance(report, EvalReport)
    assert report.overall_verdict == "ship", (
        f"Expected 'ship', got '{report.overall_verdict}': {report.rationale}"
    )
    assert report.factscore.passes is True
    assert report.quality.slop_ok is True


# ---------------------------------------------------------------------------
# 11. evaluate_card — regenerate verdict (bad factscore)
# ---------------------------------------------------------------------------


def test_evaluate_card_regenerate_verdict():
    """A card with unsupported facts below threshold triggers regenerate."""
    card = (
        "Stetson Bennett threw for 1200 yards single quarter. "
        "Georgia won by 90 points. "
        "Bennett won six consecutive trophies. "
        "No team has ever matched this record in history. "
        "The statistics are unprecedented in modern football analytics."
    )
    # Evidence is completely unrelated — forces near-zero factscore
    evidence = [_evidence("basketball game basketball players basketball court")]
    report = evaluate_card(
        card_text=card,
        card_cache_key="test-cache-key-002",
        evidence=evidence,
        judge_backend=None,
        voice_corpus_samples=[],
        factscore_threshold=0.85,
    )
    assert report.overall_verdict in ("regenerate", "reject"), (
        f"Expected regenerate or reject, got '{report.overall_verdict}': {report.rationale}"
    )


# ---------------------------------------------------------------------------
# 12. evaluate_card — reject verdict (terrible quality + bad factscore)
# ---------------------------------------------------------------------------


def test_evaluate_card_reject_verdict():
    """A card with factscore < 0.5 should be rejected."""
    # Use slop card (multiple slop terms) + unrelated evidence to force low factscore
    evidence = [_evidence("basketball court nba player dunk")]

    # Force factscore to 0.0 by checking a card that factually mentions things
    # completely absent from evidence
    terrible_card = (
        "Ward broke every passing record in SEC history last Tuesday. "
        "He threw 800 yards against undefeated Alabama in overtime per ESPN. "
        "This was the greatest performance in the 150-year history of college football."
    )
    report = evaluate_card(
        card_text=terrible_card,
        card_cache_key="test-cache-key-003",
        evidence=evidence,
        judge_backend=None,
        voice_corpus_samples=[],
        factscore_threshold=0.85,
    )
    # With basketball-only evidence and football-specific claims, factscore ≈ 0.0
    # which should trigger reject (factscore < 0.5)
    assert report.overall_verdict in ("reject", "regenerate"), (
        f"Expected reject or regenerate, got '{report.overall_verdict}': {report.rationale}"
    )
    if report.overall_verdict == "reject":
        assert report.factscore.support_rate < 0.5


# ---------------------------------------------------------------------------
# 13. evaluate_batch — aggregation
# ---------------------------------------------------------------------------


def test_evaluate_batch_aggregates():
    """evaluate_batch should return correct counts and aggregate metrics."""
    evidence_item = _evidence(
        "cam ward passes touchdowns completion miami florida state yards "
        "efficiency ranking scheme week"
    )
    cards = [
        {
            "cache_key": f"card-{i}",
            "text": CLEAN_CARD_75W,
            "evidence": [evidence_item],
        }
        for i in range(3)
    ]

    report = evaluate_batch(
        cards=cards,
        batch_id="test-batch-001",
        voice_corpus_samples=["Ward completed passes for Miami per CFBD."],
    )

    assert isinstance(report, BatchEvalReport)
    assert report.card_count == 3
    assert report.pass_count + report.flag_count + report.regenerate_count + report.reject_count == 3
    assert len(report.individual_reports) == 3
    assert 0.0 <= report.factscore_median <= 1.0
    assert 0.0 <= report.voice_score_median <= 1.0
    assert 0.0 <= report.quality_score_median <= 1.0
    assert 0.0 <= report.slop_fingerprint_median <= 1.0


def test_evaluate_batch_empty():
    """Empty cards list produces a zero-count BatchEvalReport without error."""
    report = evaluate_batch(cards=[], batch_id="empty-batch")
    assert report.card_count == 0
    assert report.individual_reports == []


# ---------------------------------------------------------------------------
# 14. detect_drift — no baseline returns safe
# ---------------------------------------------------------------------------


def test_detect_drift_no_baseline_returns_safe():
    """When there is no prior history in the DB, drift detection returns safe."""
    db = FakeDb(rows=[])  # Empty DB — no historical data
    result = detect_drift(db, batch_id="batch-2026-w21", window_weeks=8)
    assert isinstance(result, DriftReport)
    assert result.flagged_for_human_review is False
    assert result.flagged_metrics == []


def test_detect_drift_within_normal_range():
    """A batch whose metrics are within 1 sigma of baseline should not be flagged."""
    # Build 8 weeks of baseline with stable factscore ~0.90
    history_rows = [
        {
            "batch_id": f"batch-w{i}",
            "factscore": 0.90,
            "voice_score": 0.75,
            "quality_score": 0.80,
            "slop_fingerprint": 0.05,
            "created_at": f"2026-04-{i:02d}T00:00:00",
        }
        for i in range(1, 9)
    ]
    # Current batch has factscore of 0.89 — 1 point drop, well within normal range
    current_row = {
        "batch_id": "batch-current",
        "factscore": 0.89,
        "voice_score": 0.75,
        "quality_score": 0.80,
        "slop_fingerprint": 0.05,
    }
    all_rows = history_rows + [current_row]
    db = FakeDb(rows=all_rows)
    result = detect_drift(db, batch_id="batch-current", window_weeks=8, sigma_threshold=2.0)
    assert result.flagged_for_human_review is False


# ---------------------------------------------------------------------------
# 15. detect_drift — flagged when sigma exceeded
# ---------------------------------------------------------------------------


def test_detect_drift_flagged_when_sigma_exceeded():
    """A 2-sigma drop in factscore should flag the batch for human review."""
    # Stable baseline: factscore mean=0.90, stdev≈0.01
    history_rows = [
        {
            "batch_id": f"batch-w{i}",
            "factscore": 0.90 + (0.01 if i % 2 == 0 else -0.01),
            "voice_score": 0.75,
            "quality_score": 0.80,
            "slop_fingerprint": 0.05,
            "created_at": f"2026-04-{i:02d}T00:00:00",
        }
        for i in range(1, 9)
    ]
    # Current batch has a severe factscore collapse to 0.50
    # Deviation = |0.50 - 0.90| / 0.01 = 40 sigma — clearly flagged
    current_row = {
        "batch_id": "batch-collapsed",
        "factscore": 0.50,
        "voice_score": 0.75,
        "quality_score": 0.80,
        "slop_fingerprint": 0.05,
    }
    all_rows = history_rows + [current_row]
    db = FakeDb(rows=all_rows)
    result = detect_drift(db, batch_id="batch-collapsed", window_weeks=8, sigma_threshold=2.0)
    assert result.flagged_for_human_review is True
    assert "factscore_median" in result.flagged_metrics


# ---------------------------------------------------------------------------
# Internal utility tests (regression locks)
# ---------------------------------------------------------------------------


def test_tokenize_strips_punctuation():
    tokens = _tokenize("Hello, world! It's great.")
    assert "hello" in tokens
    assert "world" in tokens
    # Punctuation stripped
    assert "hello," not in tokens


def test_split_sentences_basic():
    text = "He ran. He scored. The end."
    sents = _split_sentences(text)
    assert len(sents) == 3


def test_cosine_distance_identical():
    """Identical Counter objects should have distance 0.0."""
    from collections import Counter
    c = Counter(["a", "b", "c", "a"])
    assert _cosine_distance(c, c) == pytest.approx(0.0, abs=1e-6)


def test_cosine_distance_orthogonal():
    """Completely disjoint Counter objects should have distance 1.0."""
    from collections import Counter
    a = Counter(["x", "y"])
    b = Counter(["p", "q"])
    assert _cosine_distance(a, b) == pytest.approx(1.0, abs=1e-6)


def test_factscore_result_from_atomic_facts_empty():
    """Empty fact list produces a passing FActScoreResult."""
    result = FActScoreResult.from_atomic_facts([], threshold=0.85)
    assert result.support_rate == 1.0
    assert result.passes is True


def test_factscore_result_from_atomic_facts_mixed():
    """Mixed supported/unsupported facts give correct support_rate."""
    facts = [
        AtomicFact(text="fact 1", is_supported=True),
        AtomicFact(text="fact 2", is_supported=True),
        AtomicFact(text="fact 3", is_supported=False),
        AtomicFact(text="fact 4", is_supported=True),
    ]
    result = FActScoreResult.from_atomic_facts(facts, threshold=0.85)
    assert result.support_rate == pytest.approx(0.75, abs=0.01)
    assert result.contradicted_count == 1
    assert result.passes is False  # 0.75 < 0.85


def test_slop_banlist_default_not_empty():
    """The default slop banlist should contain at least 20 terms."""
    assert len(_DEFAULT_SLOP_BANLIST) >= 20


def test_score_editorial_quality_slop_detected():
    """SLOP_CARD should have a high slop_fingerprint."""
    result = score_editorial_quality(SLOP_CARD)
    assert result.slop_fingerprint > 0.1
    assert result.slop_ok is False


def test_score_voice_g_eval_no_corpus():
    """Voice eval with empty corpus returns a neutral (non-crashing) result."""
    result = score_voice_g_eval("Some card text here.", corpus_samples=[], judge_backend=None)
    assert isinstance(result, VoiceEvalResult)
    assert 0.0 <= result.sounds_like_corpus_score <= 1.0
    assert 0.0 <= result.register_match_score <= 1.0


def test_score_voice_g_eval_matching_corpus():
    """Card very similar to corpus samples should have low lexical_fingerprint_distance."""
    corpus = [
        "Ward completed 28 of 39 passes for 342 yards three touchdowns Florida State.",
        "Miami efficiency ranking improved SP plus data scheme adaptation.",
    ]
    card = "Ward threw 342 yards three touchdowns against Florida State per CFBD data."
    result = score_voice_g_eval(card, corpus_samples=corpus, judge_backend=None)
    # Similar vocabulary — distance should be less than dissimilar corpus
    dissimilar_corpus = ["Basketball player dunked twice in the third quarter of an NBA game."]
    dissimilar_result = score_voice_g_eval(card, corpus_samples=dissimilar_corpus, judge_backend=None)
    assert result.lexical_fingerprint_distance <= dissimilar_result.lexical_fingerprint_distance


def test_evaluate_card_returns_eval_report_type():
    """evaluate_card always returns a typed EvalReport regardless of inputs."""
    report = evaluate_card(
        card_text="Short card.",
        card_cache_key="smoke-test",
        evidence=[],
        judge_backend=None,
    )
    assert isinstance(report, EvalReport)
    assert report.overall_verdict in ("ship", "flag", "regenerate", "reject")


def test_batch_eval_report_verdict_counts_sum_to_card_count():
    """pass + flag + regenerate + reject == card_count."""
    cards = [
        {"cache_key": f"c{i}", "text": CLEAN_CARD_75W, "evidence": []}
        for i in range(5)
    ]
    report = evaluate_batch(cards=cards, batch_id="count-test")
    total = (
        report.pass_count
        + report.flag_count
        + report.regenerate_count
        + report.reject_count
    )
    assert total == report.card_count == 5
