"""Sprint v5-2 — first quality_loop flag flip.

Tests that ``cfb_rankings.editions.cover_essay.synthesize_cover_essay``
honors the ``config.QUALITY_LOOP_FLAGS["tier1.edition_cover"]`` flag:

1. With flag absent → seed path is used; no LLM call made.
2. With flag set to ``LoopPattern.C_CRITIC_REVISE`` →
   ``quality_loop.loop_c_critic_revise`` is invoked with the expected
   surface key, subcommand, system prompt, and prompt body.
3. Surface key passed to the loop is ``"tier1.edition_cover"``.
4. ``prompt_context.build_edition_cover_context`` is invoked and its
   dict is folded into the prompt body (labeled sections).
5. Graceful degradation: when the loop returns ``fell_back=True``
   (offline-stub, wall-clock timeout, Rung-2 fall-back), the synthesizer
   falls through to the seed body.

All Anthropic SDK calls are mocked. Nothing should touch the network.
"""
from __future__ import annotations

from typing import Any
from unittest import mock

import pytest

from cfb_rankings import quality_loop as _ql_module
from cfb_rankings.editions import cover_essay
from cfb_rankings.editions.cover_essay import (
    EDITION_COVER_SYSTEM_PROMPT,
    MAX_TOKENS,
    SUBCOMMAND,
    SURFACE_KEY,
    CoverEssayResult,
    compose_prompt_body,
    synthesize_cover_essay,
)
from cfb_rankings.quality_loop import LoopPattern, LoopResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stub_context() -> dict[str, Any]:
    """A representative context dict matching the v5.3 Part 4 manifest."""
    return {
        "season": 2026,
        "week": 17,
        "season_phase": {"phase": "postseason", "sub_phase": "post_bracket"},
        "prior_4_covers": [
            {"edition_slug": "2026-w16", "title": "Draft Reset",
             "dek": "Twenty-three first-rounders left.",
             "theme_tag": "post_draft"},
        ],
        "cohort_mood_dumbbell": [
            {"conference": "SEC", "left": 0.42, "right": 0.86,
             "annotation": "Texas high; Auburn processing"},
        ],
        "rank_disagreements": [
            {"team": "Notre Dame", "bt_rank": 4, "sp_plus_rank": 7,
             "fpi_rank": 6, "spread": 3},
        ],
        "active_storylines": [
            {"thread_slug": "iowa-tempo-2026",
             "title": "Iowa's Spring Doesn't Feel Like Iowa"},
        ],
        "major_wire_7d": [
            {"action": "portal_commit", "actor": "Texas",
             "why_it_matters": "Adds a Day-1 starting OT."},
        ],
        "resolved_receipts": [
            {"caller": "Bill Connelly", "claim": "G5 wins first-round",
             "surprise_index": 89, "outcome_verdict": "verified"},
        ],
        "top_chronicle_moments": [
            {"team_slug": "alabama", "observation": "Spring practice tempo lift",
             "evidence_strength": 0.81, "resonance_score": 0.74},
        ],
    }


def _gen_response(text: str, voice_passed: bool = True) -> dict[str, Any]:
    """Shape that ``llm_runtime.generate_with_voice_check`` returns."""
    return {
        "text": text,
        "voice_validator_passed": voice_passed,
        "voice_violations": [],
        "attempts": 1,
        "tokens_used": {"input": 1200, "output": 800},
        "model_used": "claude-mock",
        "mode": "live",
    }


def _critic_payload(passed: bool, score: float) -> dict[str, Any]:
    """Mock critic verdict envelope."""
    import json
    return _gen_response(
        json.dumps({
            "pass": passed,
            "score": score,
            "issues": [],
            "suggested_revisions": "",
        }),
    )


@pytest.fixture(autouse=True)
def _reset_quality_loop_state():
    _ql_module.reset_circuit_state()
    yield
    _ql_module.reset_circuit_state()


@pytest.fixture
def fake_db():
    """A minimal DB-like sentinel — `synthesize_cover_essay` only
    consults ``db`` to extract a sqlite3.Connection, and in these tests
    we always pass ``sqlite_conn=None`` + a stub ``context_builder``."""
    return mock.MagicMock(name="Database")


# ---------------------------------------------------------------------------
# 1. Flag absent → seed path used
# ---------------------------------------------------------------------------


class TestFlagAbsent:

    def test_seed_path_used_when_flag_absent(self, fake_db):
        """No flag → no LLM call; result.source == 'seed'."""
        seed_body = "Seed-authored cover essay body."
        fb = mock.MagicMock(return_value=seed_body)

        # Patch the flags dict to empty (flag explicitly absent).
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {},
            clear=True,
        ), mock.patch.object(_ql_module, "loop_c_critic_revise") as mock_loop:
            result = synthesize_cover_essay(
                season=2026, week=17, edition_slug="2026-w17",
                db=fake_db, fallback=fb,
            )

        assert isinstance(result, CoverEssayResult)
        assert result.text == seed_body
        assert result.source == "seed"
        assert result.loop_result is None
        assert result.fallback_reason == "flag_absent"
        # The whole point: no loop call when the flag is unset.
        mock_loop.assert_not_called()
        fb.assert_called_once_with("2026-w17")

    def test_seed_path_falls_through_with_no_seed(self, fake_db):
        """No flag, no seed → source='none', text=None."""
        fb = mock.MagicMock(return_value=None)

        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {},
            clear=True,
        ):
            result = synthesize_cover_essay(
                season=2026, week=99, edition_slug="2026-w99",
                db=fake_db, fallback=fb,
            )

        assert result.text is None
        assert result.source == "none"
        assert result.fallback_reason == "flag_absent_no_seed"


# ---------------------------------------------------------------------------
# 2. Flag set → loop_c_critic_revise routed with expected args
# ---------------------------------------------------------------------------


class TestFlagSet:

    def test_loop_c_called_with_expected_args(self, fake_db):
        """Flag set to Pattern C → loop_c_critic_revise gets the right
        surface, subcommand, system prompt, max_tokens, and prompt body."""
        ctx_builder = mock.MagicMock(return_value=_stub_context())
        fake_loop_result = LoopResult(
            text="GENERATED COVER ESSAY BODY.",
            pattern=LoopPattern.C_CRITIC_REVISE.value,
            final_score=8.4,
            verdicts=[],
            revise_count=0,
            total_tokens={"input": 1200, "output": 800},
        )

        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {SURFACE_KEY: LoopPattern.C_CRITIC_REVISE},
            clear=True,
        ), mock.patch(
            "cfb_rankings.editions.cover_essay.loop_c_critic_revise",
            return_value=fake_loop_result,
        ) as mock_loop:
            result = synthesize_cover_essay(
                season=2026, week=17, edition_slug="2026-w17",
                db=fake_db, sqlite_conn=mock.MagicMock(),
                context_builder=ctx_builder,
            )

        # The loop was called with the right surface + subcommand + system.
        assert mock_loop.call_count == 1
        _args, kwargs = mock_loop.call_args
        assert kwargs["surface"] == SURFACE_KEY == "tier1.edition_cover"
        assert kwargs["subcommand"] == SUBCOMMAND == "quality_loop.C.edition_cover"
        assert kwargs["system"] == EDITION_COVER_SYSTEM_PROMPT
        assert kwargs["max_tokens"] == MAX_TOKENS == 4096

        # The prompt body folded in the context dict.
        prompt_arg = _args[0] if _args else kwargs.get("prompt")
        # The positional prompt argument:
        if not _args:
            # loop_c_critic_revise is keyword-only? It accepts positional
            # `prompt` per the source. Either way, find it.
            pass
        assert isinstance(prompt_arg, str)
        assert "SOURCE OBSERVATIONS" in prompt_arg
        assert "SEASON: 2026" in prompt_arg
        assert "WEEK (ISO calendar week of publish date): 17" in prompt_arg
        # Sections from the context manifest land in the prompt body:
        assert "PRIOR 4 COVERS" in prompt_arg
        assert "COHORT MOOD DUMBBELL" in prompt_arg
        assert "RANK DISAGREEMENTS" in prompt_arg
        assert "ACTIVE STORYLINES" in prompt_arg
        assert "MAJOR WIRE 7D" in prompt_arg
        assert "RESOLVED RECEIPTS" in prompt_arg
        assert "TOP CHRONICLE MOMENTS" in prompt_arg
        assert "SEASON PHASE" in prompt_arg

        # The result carries the LLM body.
        assert result.text == "GENERATED COVER ESSAY BODY."
        assert result.source == "llm"
        assert result.loop_result is fake_loop_result
        assert result.fallback_reason is None

        # Context builder was called with (season, week, conn).
        ctx_builder.assert_called_once()
        cb_args, _cb_kwargs = ctx_builder.call_args
        assert cb_args[0] == 2026
        assert cb_args[1] == 17


# ---------------------------------------------------------------------------
# 3. Context builder integration — build_edition_cover_context default
# ---------------------------------------------------------------------------


class TestContextBuilderWiring:

    def test_default_builder_is_build_edition_cover_context(self, fake_db):
        """When no explicit context_builder is provided,
        prompt_context.builders.build_edition_cover_context is the
        default. We patch it at its real location and verify it's the
        function the synthesizer reaches for."""
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {SURFACE_KEY: LoopPattern.C_CRITIC_REVISE},
            clear=True,
        ), mock.patch(
            "cfb_rankings.prompt_context.builders.build_edition_cover_context",
            return_value=_stub_context(),
        ) as default_builder, mock.patch(
            "cfb_rankings.editions.cover_essay.loop_c_critic_revise",
            return_value=LoopResult(
                text="ok", pattern=LoopPattern.C_CRITIC_REVISE.value,
                final_score=8.0, verdicts=[], revise_count=0,
                total_tokens={"input": 1, "output": 1},
            ),
        ):
            result = synthesize_cover_essay(
                season=2026, week=17, edition_slug="2026-w17",
                db=fake_db, sqlite_conn=mock.MagicMock(),
            )

        default_builder.assert_called_once()
        cb_args, _ = default_builder.call_args
        assert cb_args[0] == 2026
        assert cb_args[1] == 17
        assert result.source == "llm"
        assert result.text == "ok"

    def test_compose_prompt_body_includes_every_manifest_section(self):
        """The Part 4 manifest sections all show up labeled."""
        body = compose_prompt_body(_stub_context())
        for label in [
            "SEASON PHASE",
            "PRIOR 4 COVERS",
            "COHORT MOOD DUMBBELL",
            "RANK DISAGREEMENTS",
            "ACTIVE STORYLINES",
            "MAJOR WIRE 7D",
            "RESOLVED RECEIPTS",
            "TOP CHRONICLE MOMENTS",
        ]:
            assert label in body, f"section {label!r} missing from prompt body"
        # And the verbatim source-of-truth marker is present so the
        # FACTUALITY critic can pin claims to it.
        assert "SOURCE OBSERVATIONS" in body
        # Concrete values from the stub context flow through.
        assert "2026-w16" in body
        assert "Iowa" in body
        assert "Bill Connelly" in body

    def test_compose_prompt_body_renders_empty_sections_gracefully(self):
        """Sections that the builder couldn't fill (graceful degradation
        in Sprint v5-1 prompt_context) render as '(empty — no signal …)'
        rather than as 'null' or being silently omitted."""
        ctx = {"season": 2026, "week": 17}
        body = compose_prompt_body(ctx)
        # All eight manifest sections still appear, marked empty.
        assert "PRIOR 4 COVERS" in body
        assert "(empty" in body


# ---------------------------------------------------------------------------
# 4. Graceful degradation on loop fall-back
# ---------------------------------------------------------------------------


class TestGracefulDegradation:

    def test_falls_back_to_seed_when_loop_fell_back(self, fake_db):
        """Loop returns fell_back=True (offline-stub, wall-clock timeout,
        Rung-2 fall-back) → seed body is returned, source='seed',
        fallback_reason mirrors the loop's reason."""
        seed_body = "SEED FALLBACK BODY"
        fb = mock.MagicMock(return_value=seed_body)
        fell_back_result = LoopResult(
            text=None,
            pattern=LoopPattern.C_CRITIC_REVISE.value,
            final_score=0.0,
            verdicts=[],
            revise_count=0,
            total_tokens={"input": 0, "output": 0},
            fell_back=True,
            fallback_reason="offline_stub",
        )

        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {SURFACE_KEY: LoopPattern.C_CRITIC_REVISE},
            clear=True,
        ), mock.patch(
            "cfb_rankings.editions.cover_essay.loop_c_critic_revise",
            return_value=fell_back_result,
        ):
            result = synthesize_cover_essay(
                season=2026, week=17, edition_slug="2026-w17",
                db=fake_db, sqlite_conn=mock.MagicMock(),
                context_builder=mock.MagicMock(return_value=_stub_context()),
                fallback=fb,
            )

        assert result.text == seed_body
        assert result.source == "seed"
        assert result.loop_result is fell_back_result
        assert result.fallback_reason == "offline_stub"
        fb.assert_called_once_with("2026-w17")

    def test_falls_back_to_seed_when_loop_returns_no_text(self, fake_db):
        """Loop didn't formally fall back but text is None (edge case
        — e.g. an SDK that returned an empty string after retries).
        The synthesizer still falls back."""
        seed_body = "FALLBACK SEED BODY"
        fb = mock.MagicMock(return_value=seed_body)
        no_text_result = LoopResult(
            text=None,
            pattern=LoopPattern.C_CRITIC_REVISE.value,
            final_score=0.0,
            verdicts=[],
            revise_count=0,
            total_tokens={"input": 0, "output": 0},
            fell_back=False,
            fallback_reason=None,
        )

        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {SURFACE_KEY: LoopPattern.C_CRITIC_REVISE},
            clear=True,
        ), mock.patch(
            "cfb_rankings.editions.cover_essay.loop_c_critic_revise",
            return_value=no_text_result,
        ):
            result = synthesize_cover_essay(
                season=2026, week=17, edition_slug="2026-w17",
                db=fake_db, sqlite_conn=mock.MagicMock(),
                context_builder=mock.MagicMock(return_value=_stub_context()),
                fallback=fb,
            )

        assert result.text == seed_body
        assert result.source == "seed"
        assert result.fallback_reason == "loop_returned_no_text"


# ---------------------------------------------------------------------------
# 5. End-to-end with quality_loop driving real generate_with_voice_check
#    (still mocked at the runtime layer)
# ---------------------------------------------------------------------------


class TestEndToEndWithLoopDriving:

    def test_end_to_end_flag_set_runs_real_loop_c(self, fake_db):
        """Don't mock loop_c_critic_revise; mock the runtime layer
        underneath it. Confirms the dispatch wires all the way through
        to quality_loop.generate_with_voice_check with the same surface
        + subcommand we configured at the synthesizer level."""
        gen = _gen_response("ESSAY BODY.")
        c1 = _critic_payload(True, 8.5)
        c2 = _critic_payload(True, 9.0)
        c3 = _critic_payload(True, 8.2)
        mock_runtime = mock.MagicMock(side_effect=[gen, c1, c2, c3])

        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {SURFACE_KEY: LoopPattern.C_CRITIC_REVISE},
            clear=True,
        ), mock.patch(
            "cfb_rankings.quality_loop.llm_runtime.generate_with_voice_check",
            mock_runtime,
        ):
            result = synthesize_cover_essay(
                season=2026, week=17, edition_slug="2026-w17",
                db=fake_db, sqlite_conn=mock.MagicMock(),
                context_builder=mock.MagicMock(return_value=_stub_context()),
            )

        assert result.source == "llm"
        assert result.text == "ESSAY BODY."
        assert result.loop_result is not None
        assert result.loop_result.pattern == LoopPattern.C_CRITIC_REVISE.value
        # 1 gen + 3 critics = 4 runtime calls (no revise needed).
        assert mock_runtime.call_count == 4

        # And the very first call (the gen call) used Pattern C's default
        # gen model (Opus 4.7) per quality_loop._LOOP_GEN_MODEL_DEFAULTS.
        gen_call_kwargs = mock_runtime.call_args_list[0].kwargs
        assert gen_call_kwargs.get("model") == "claude-opus-4-7"
        assert gen_call_kwargs.get("max_tokens") == MAX_TOKENS
        assert gen_call_kwargs.get("system") == EDITION_COVER_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# 6. Surface keys + config defaults — sanity
# ---------------------------------------------------------------------------


class TestConfigDefaults:

    def test_flag_is_set_in_default_config(self):
        """The Sprint v5-2 flip lives in config.py and is on by default."""
        from cfb_rankings import config
        assert SURFACE_KEY in config.QUALITY_LOOP_FLAGS
        pattern = config.QUALITY_LOOP_FLAGS[SURFACE_KEY]
        # Accept either the enum or the string sentinel that the
        # circular-import fallback emits.
        assert pattern == LoopPattern.C_CRITIC_REVISE or pattern == "C_critic_revise"

    def test_weekly_ceiling_present_for_surface(self):
        """Rung-3 weekly ceiling is wired for the new flag's surface."""
        from cfb_rankings import config
        assert SURFACE_KEY in config.WEEKLY_CEILINGS_CENTS
        assert config.WEEKLY_CEILINGS_CENTS[SURFACE_KEY] == 1000  # $10/wk

    def test_surface_constants_unchanged(self):
        """Catch accidental rename of the public surface key /
        subcommand. Downstream telemetry depends on these strings."""
        assert SURFACE_KEY == "tier1.edition_cover"
        assert SUBCOMMAND == "quality_loop.C.edition_cover"
        assert MAX_TOKENS == 4096
