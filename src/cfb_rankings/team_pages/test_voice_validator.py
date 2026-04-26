"""Tests for the fan-voice copy validator."""
from __future__ import annotations

import pytest

from cfb_rankings.team_pages.voice_validator import (
    BANNED_PHRASES,
    FAN_VOICE_REPLACEMENTS,
    first_violation,
    has_banned_phrase,
    validate,
    validate_fan_voice,
)


class TestBannedPhraseDetection:
    """Phrases on the banlist must fail the gate, every form."""

    def test_no_hyphen_cohort_taxonomy_fails(self):
        # Sprint 10 audit: bare "cohort" was removed from BANNED_PHRASES
        # because it false-positived on legitimate non-taxonomy uses
        # ("portal cohort", "freshman cohort"). The taxonomy variants
        # without hyphens are listed explicitly so the LLM-generated
        # leakage path stays caught.
        ok, violations = validate_fan_voice("the analytics cohort is bullish on ND")
        assert not ok
        assert "analytics cohort" in violations

    def test_hyphenated_cohort_compound_fails(self):
        ok, _ = validate_fan_voice("the analytics-cohort and the casual-cohort disagree")
        assert not ok

    def test_legitimate_non_taxonomy_cohort_passes(self):
        # Sprint 10 audit: "portal cohort" / "freshman cohort" / "JMU
        # cohort" are standard English usages of the word "cohort" (a
        # group of people moving together). They are NOT the analytics-
        # cohort / casual-cohort taxonomy and should not be banned.
        for text in (
            "Cignetti brought a portal cohort of 13 from JMU.",
            "The freshman cohort showed up to camp Monday.",
            "We watched the cohort move from one program to another.",
        ):
            ok, violations = validate_fan_voice(text)
            assert ok, f"unexpectedly failed: {text!r} (violations={violations})"

    def test_n_equals_notation_fails(self):
        ok, _ = validate_fan_voice("n=48 mentions this week")
        assert not ok

    def test_sample_growing_idiom_fails(self):
        ok, _ = validate_fan_voice("sample growing across the offseason")
        assert not ok

    def test_pipeline_leakage_fails(self):
        ok, _ = validate_fan_voice("our fan-intel pipeline ingested 184k posts")
        assert not ok

    def test_engine_leakage_fails(self):
        ok, _ = validate_fan_voice("the stat engine flagged this anomaly")
        assert not ok

    def test_discourse_velocity_fails(self):
        ok, _ = validate_fan_voice("discourse velocity spiked Monday morning")
        assert not ok

    def test_methodology_in_body_copy_fails(self):
        # methodology PAGE may be technical; copy outside it must not be.
        ok, _ = validate_fan_voice(
            "Our methodology surfaces real fan voices over stock phrases."
        )
        assert not ok

    def test_self_referential_scaffolding_fails(self):
        ok, _ = validate_fan_voice("This card argues that Notre Dame is quietly high.")
        assert not ok

    def test_every_season_produces_fails(self):
        ok, _ = validate_fan_voice(
            "Every season produces one of these moments — this is ND's."
        )
        assert not ok


class TestPassingCopy:
    """Copy that talks like a beat writer should pass."""

    def test_clean_lede_passes(self):
        text = (
            "Notre Dame is quietly high. Texas is louder, but ND has more "
            "upside left in this offseason."
        )
        ok, violations = validate_fan_voice(text)
        assert ok
        assert violations == []

    def test_alabama_voice_passes(self):
        text = (
            "Alabama's mood is hovering at last-year's October baseline — "
            "early, but no ceiling yet."
        )
        ok, _ = validate_fan_voice(text)
        assert ok

    def test_fan_voice_replacement_passes(self):
        # The replacement vocabulary itself must pass.
        text = "The stat folks see efficiency. The regular fans see the SEC getting screwed."
        ok, _ = validate_fan_voice(text)
        assert ok

    def test_empty_input_passes(self):
        # Empty content is the caller's concern, not the validator's.
        ok, _ = validate_fan_voice("")
        assert ok
        ok, _ = validate_fan_voice("   \n  ")
        assert ok

    def test_bare_sample_passes(self):
        # We block "sample growing" but allow bare "sample" / "early sample".
        ok, _ = validate_fan_voice("23 fans heard from · early sample")
        assert ok


class TestValidationResultStructured:
    """The structured-result variant supports source tagging + boolean coercion."""

    def test_passed_result_truthy(self):
        result = validate("Notre Dame is quietly high.", source="ND lede")
        assert bool(result) is True
        assert result.source == "ND lede"

    def test_failed_result_falsy(self):
        result = validate("the analytics cohort is bullish", source="ND lede")
        assert bool(result) is False
        assert "analytics cohort" in result.violations
        assert result.source == "ND lede"


class TestHelpers:
    def test_has_banned_phrase(self):
        assert has_banned_phrase("the analytics cohort agrees")
        assert not has_banned_phrase("Notre Dame is quietly high.")

    def test_first_violation_returns_first_match(self):
        assert first_violation("n=48 mentions") == "n="
        assert first_violation("Notre Dame plays Saturday.") is None

    def test_replacement_table_has_all_known_internals(self):
        # Spot-check that our replacement table covers the cohort terms
        # the prompts will most often reach for.
        assert "analytics-cohort" in FAN_VOICE_REPLACEMENTS
        assert "casual-cohort" in FAN_VOICE_REPLACEMENTS
        assert "cohort divergence" in FAN_VOICE_REPLACEMENTS

    def test_banned_phrases_nonempty(self):
        # Sanity — the gate is only useful if the banlist is real.
        assert len(BANNED_PHRASES) >= 25
        assert "analytics cohort" in BANNED_PHRASES
        assert "analytics-cohort" in BANNED_PHRASES
        assert "n=" in BANNED_PHRASES

    def test_word_boundary_avoids_substring_false_positive(self):
        # Sprint 10 regression: "the engine" used to match inside "the
        # engineering team" via substring; word-boundary regex fixes it.
        ok, _ = validate_fan_voice("the engineering team filed the report")
        assert ok
        # Same for "this table" inside "this tablecloth".
        ok, _ = validate_fan_voice("this tablecloth is the program's identity")
        assert ok
        # And the standalone-cohort case the audit was about.
        ok, _ = validate_fan_voice("Cignetti's portal cohort arrived in March")
        assert ok
