"""Tests for ``cfb_rankings.quality_loop`` — five patterns, five critics,
three-rung circuit breakers, dispatch helper.

All Anthropic SDK calls are mocked via patching
``cfb_rankings.llm_runtime.generate_with_voice_check``. None of these tests
should ever touch the network.
"""
from __future__ import annotations

import json
from unittest import mock

import pytest

from cfb_rankings import quality_loop
from cfb_rankings.quality_loop import (
    CriticRole,
    CriticVerdict,
    LoopPattern,
    LoopResult,
    loop_a_single_shot,
    loop_b_single_critic,
    loop_c_critic_revise,
    loop_d_adversarial,
    loop_e_continuity,
    loop_for_surface,
    reset_circuit_state,
    run_critic,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gen_response(text: str, *, voice_passed: bool = True,
                  in_toks: int = 100, out_toks: int = 200) -> dict:
    """Build the dict shape that ``generate_with_voice_check`` returns."""
    return {
        "text": text,
        "voice_validator_passed": voice_passed,
        "voice_violations": [] if voice_passed else ["banned"],
        "attempts": 1,
        "tokens_used": {"input": in_toks, "output": out_toks},
        "model_used": "claude-mock",
        "mode": "live",
    }


def _critic_payload(passed: bool, score: float, issues=None,
                    suggested: str = "") -> str:
    """Serialize the JSON envelope a critic is expected to return."""
    return json.dumps({
        "pass": passed,
        "score": score,
        "issues": list(issues or []),
        "suggested_revisions": suggested,
    })


@pytest.fixture(autouse=True)
def _reset_state():
    """Each test starts with fresh circuit-breaker state."""
    reset_circuit_state()
    yield
    reset_circuit_state()


def _patch_runtime(responses):
    """Patch ``llm_runtime.generate_with_voice_check`` to return the
    provided sequence of response dicts (one per call).

    Returns the mock so tests can assert call counts."""
    if not isinstance(responses, list):
        responses = [responses]
    mock_fn = mock.MagicMock(side_effect=responses)
    return mock.patch(
        "cfb_rankings.quality_loop.llm_runtime.generate_with_voice_check",
        mock_fn,
    ), mock_fn


# ---------------------------------------------------------------------------
# 1 — one test per loop pattern
# ---------------------------------------------------------------------------

class TestLoopPatterns:

    def test_pattern_a_single_shot_passes_through(self):
        """Pattern A makes exactly one gen call, no critics."""
        patcher, mock_fn = _patch_runtime([_gen_response("Clean factual restatement.")])
        with patcher:
            result = loop_a_single_shot(
                "summarize this wire row",
                system="wire factual restatement",
                model="claude-sonnet-4-6",
            )
        assert isinstance(result, LoopResult)
        assert result.pattern == LoopPattern.A_SINGLE_SHOT.value
        assert result.text == "Clean factual restatement."
        assert result.revise_count == 0
        assert result.verdicts == []
        assert result.fell_back is False
        assert result.voice_validator_passed is True
        # Final score is 10 on voice pass, 0 on voice fail.
        assert result.final_score == 10.0
        assert mock_fn.call_count == 1

    def test_pattern_b_single_critic_passes_first_try(self):
        """Pattern B: generate → one critic. Pass first try → no revise."""
        gen_resp = _gen_response("Sonnet draft text.")
        critic_resp = _gen_response(_critic_payload(True, 8.5))
        patcher, mock_fn = _patch_runtime([gen_resp, critic_resp])
        with patcher:
            result = loop_b_single_critic(
                "draft this team narrative",
                critic_role=CriticRole.VOICE,
            )
        assert result.pattern == LoopPattern.B_SINGLE_CRITIC.value
        assert result.text == "Sonnet draft text."
        assert result.revise_count == 0
        assert len(result.verdicts) == 1
        assert result.verdicts[0].critic_role == CriticRole.VOICE.value
        assert result.verdicts[0].passed is True
        assert mock_fn.call_count == 2  # 1 gen + 1 critic

    def test_pattern_b_revises_once_on_critic_fail(self):
        """Pattern B: fail critic on first draft → revise → pass."""
        responses = [
            _gen_response("Weak first draft."),
            _gen_response(_critic_payload(False, 5.0, ["too generic"], "be specific")),
            _gen_response("Stronger revised draft."),
            _gen_response(_critic_payload(True, 8.0)),
        ]
        patcher, mock_fn = _patch_runtime(responses)
        with patcher:
            result = loop_b_single_critic("draft", critic_role=CriticRole.VOICE)
        assert result.text == "Stronger revised draft."
        assert result.revise_count == 1
        assert len(result.verdicts) == 2
        assert mock_fn.call_count == 4

    def test_pattern_c_critic_revise_default_tier1(self):
        """Pattern C runs 3 critics (voice + headline + factuality).
        Pass first try → 1 gen + 3 critic calls = 4 total."""
        gen_resp = _gen_response("Opus tier-1 draft.")
        responses = [gen_resp] + [
            _gen_response(_critic_payload(True, 8.0)),
            _gen_response(_critic_payload(True, 9.0)),
            _gen_response(_critic_payload(True, 8.5)),
        ]
        patcher, mock_fn = _patch_runtime(responses)
        with patcher:
            result = loop_c_critic_revise("write the daily lead")
        assert result.pattern == LoopPattern.C_CRITIC_REVISE.value
        assert result.text == "Opus tier-1 draft."
        assert result.revise_count == 0
        assert len(result.verdicts) == 3
        roles = {v.critic_role for v in result.verdicts}
        assert roles == {"voice", "headline", "factuality"}
        # Final score = mean of last critique round.
        assert result.final_score == pytest.approx((8.0 + 9.0 + 8.5) / 3)
        assert mock_fn.call_count == 4

    def test_pattern_d_adversarial_runs_engagement_critic(self):
        """Pattern D runs 4 critics including ENGAGEMENT (Edition cover only)."""
        gen_resp = _gen_response("Edition cover essay draft.")
        responses = [gen_resp] + [
            _gen_response(_critic_payload(True, 9.0)),  # voice
            _gen_response(_critic_payload(True, 9.0)),  # headline
            _gen_response(_critic_payload(True, 8.5)),  # factuality
            _gen_response(_critic_payload(True, 8.0)),  # engagement
        ]
        patcher, mock_fn = _patch_runtime(responses)
        with patcher:
            result = loop_d_adversarial("write the edition cover")
        assert result.pattern == LoopPattern.D_ADVERSARIAL.value
        assert len(result.verdicts) == 4
        roles = {v.critic_role for v in result.verdicts}
        assert "engagement" in roles
        assert roles == {"voice", "headline", "factuality", "engagement"}

    def test_pattern_e_continuity_injects_thread_history(self):
        """Pattern E runs 4 critics including CONTINUITY and injects
        thread history + entity ledger into the gen system prompt."""
        gen_resp = _gen_response("Chapter 4 of the Vandy ascendance arc.")
        responses = [gen_resp] + [
            _gen_response(_critic_payload(True, 8.0)),  # voice
            _gen_response(_critic_payload(True, 8.5)),  # headline
            _gen_response(_critic_payload(True, 9.0)),  # factuality
            _gen_response(_critic_payload(True, 8.5)),  # continuity
        ]
        patcher, mock_fn = _patch_runtime(responses)
        with patcher:
            result = loop_e_continuity(
                "write chapter 4",
                thread_history="Chapter 1: ... Chapter 2: ... Chapter 3: ...",
                entity_ledger="'the standard' = the Diego Pavia bar",
                system="storyline chapter system prompt",
            )
        assert result.pattern == LoopPattern.E_CONTINUITY.value
        roles = {v.critic_role for v in result.verdicts}
        assert "continuity" in roles
        assert roles == {"voice", "headline", "factuality", "continuity"}
        # The first call's system prompt must contain the injected blocks.
        first_call = mock_fn.call_args_list[0]
        injected_system = first_call.kwargs["system"]
        assert "THREAD HISTORY" in injected_system
        assert "NAMED-ENTITY LEDGER" in injected_system
        assert "Diego Pavia bar" in injected_system


# ---------------------------------------------------------------------------
# 2 — one test per critic role prompt structure
# ---------------------------------------------------------------------------

class TestCriticPrompts:

    def _capture_call(self, payload: str):
        """Return (patcher, mock_fn) for a single critic call."""
        return _patch_runtime([_gen_response(payload)])

    def test_voice_critic_prompt_mentions_banned_phrases(self):
        patcher, mock_fn = self._capture_call(_critic_payload(True, 8.0))
        with patcher:
            verdict = run_critic(CriticRole.VOICE, "Notre Dame is quietly high.")
        system = mock_fn.call_args.kwargs["system"]
        assert "VOICE critic" in system
        # The voice critic must enforce banned-phrase taxonomy.
        assert "banned" in system.lower()
        assert "cohort" in system.lower()
        # Returns a verdict with the parsed score.
        assert verdict.score == 8.0
        assert verdict.critic_role == "voice"

    def test_headline_critic_prompt_lists_five_questions(self):
        patcher, mock_fn = self._capture_call(_critic_payload(True, 8.0))
        with patcher:
            verdict = run_critic(CriticRole.HEADLINE, "Vandy Holds, Bama Folds")
        system = mock_fn.call_args.kwargs["system"]
        assert "HEADLINE critic" in system
        # 5-question rubric.
        assert "§2.9" in system or "5-question" in system or "rubric" in system.lower()
        # Headline pass threshold is 8.0; 8.0 with pass=true → passes.
        assert verdict.passed is True

    def test_factuality_critic_prompt_requires_source_traceable(self):
        patcher, mock_fn = self._capture_call(_critic_payload(False, 4.0, ["invented yardage"]))
        with patcher:
            verdict = run_critic(
                CriticRole.FACTUALITY,
                "Beck threw for 412 yards.",
                context={"source_observations": "Beck: 287 passing yards"},
            )
        system = mock_fn.call_args.kwargs["system"]
        user_prompt = mock_fn.call_args.kwargs.get("model") and \
            mock_fn.call_args.args[0]
        assert "FACTUALITY critic" in system
        assert "traceable" in system.lower() or "trace" in system.lower()
        # The source observations block must be in the user prompt.
        assert "SOURCE OBSERVATIONS" in user_prompt
        assert "287 passing yards" in user_prompt
        assert verdict.passed is False
        assert "invented yardage" in verdict.issues

    def test_engagement_critic_prompt_pattern_d_only(self):
        patcher, mock_fn = self._capture_call(_critic_payload(True, 8.0))
        with patcher:
            verdict = run_critic(CriticRole.ENGAGEMENT, "Edition cover essay draft.")
        system = mock_fn.call_args.kwargs["system"]
        assert "ENGAGEMENT critic" in system
        # Engagement critic asks the "sophisticated reader" question.
        assert "sophisticated" in system.lower()
        assert "scrolling" in system.lower() or "linger" in system.lower()
        # Threshold is 7.5; score 8.0 + pass=true → passes.
        assert verdict.passed is True

    def test_continuity_critic_prompt_pattern_e_only(self):
        patcher, mock_fn = self._capture_call(_critic_payload(True, 8.5))
        with patcher:
            verdict = run_critic(
                CriticRole.CONTINUITY,
                "Chapter 4 draft text.",
                context={
                    "thread_history": "Chapter 1: ... Chapter 2: ...",
                    "entity_ledger": "'the standard' = the Pavia bar",
                },
            )
        system = mock_fn.call_args.kwargs["system"]
        user_prompt = mock_fn.call_args.args[0]
        assert "CONTINUITY critic" in system
        assert "thread" in system.lower()
        assert "THREAD HISTORY" in user_prompt
        assert "NAMED-ENTITY LEDGER" in user_prompt
        assert verdict.passed is True


class TestCriticParsing:

    def test_critic_parses_markdown_fenced_json(self):
        """Opus sometimes wraps JSON in ```json fences. The parser must
        unwrap them."""
        fenced = "```json\n" + _critic_payload(True, 8.0) + "\n```"
        patcher, mock_fn = _patch_runtime([_gen_response(fenced)])
        with patcher:
            verdict = run_critic(CriticRole.VOICE, "candidate text")
        assert verdict.score == 8.0
        assert verdict.passed is True

    def test_critic_unparseable_response_defaults_to_failure(self):
        """If the critic returns garbage, the verdict is a parse-failure
        with pass=False so the loop can fall back / revise."""
        patcher, _ = _patch_runtime([_gen_response("not json at all")])
        with patcher:
            verdict = run_critic(CriticRole.VOICE, "candidate text")
        assert verdict.passed is False
        assert verdict.score == 0.0
        assert any("parse_failed" in i for i in verdict.issues)


# ---------------------------------------------------------------------------
# 3 — circuit breakers: Rung 1 (escalation) + Rung 2 (fall-back)
# ---------------------------------------------------------------------------

class TestCircuitBreakers:

    def test_rung_1_escalates_gen_model_on_consecutive_critic_failures(self):
        """Rung 1: after 2 consecutive critic failures, the gen-model
        escalates Sonnet → Opus on the revise pass."""
        # First gen + 1 failing critic; revise pass + 1 passing critic.
        # Pattern B has 1 critic, but its single-fail on first round is
        # only 1 failure. To trip Rung 1 we need ≥ 2 failed critics across
        # one panel; Pattern C's 3-critic panel can produce that on round 1.
        gen1 = _gen_response("Sonnet first draft.")
        fail = _critic_payload(False, 4.0, ["weak"], "tighten")
        pass_ = _critic_payload(True, 8.0)
        gen2 = _gen_response("Revised draft (now from Opus).")
        responses = [
            gen1,
            _gen_response(fail),    # voice fail (1st consec failure)
            _gen_response(fail),    # headline fail (2nd consec failure → Rung 1)
            _gen_response(pass_),   # factuality pass
            gen2,
            _gen_response(pass_),   # voice pass on revise
            _gen_response(pass_),   # headline pass on revise
            _gen_response(pass_),   # factuality pass on revise
        ]
        patcher, mock_fn = _patch_runtime(responses)
        with patcher:
            result = loop_c_critic_revise(
                "draft",
                model="claude-sonnet-4-6",
            )
        assert result.revise_count == 1
        # The revise call should have used the escalated model.
        revise_call = mock_fn.call_args_list[4]  # 0=gen, 1-3=critics, 4=revise gen
        assert revise_call.kwargs["model"] == "claude-opus-4-7"
        # Final result passes after revision.
        assert result.text == "Revised draft (now from Opus)."

    def test_rung_2_falls_back_after_three_consecutive_failures(self):
        """Rung 2: 3 consecutive critic failures (initial round + escalated
        revise both failing) → fall back to seeds.py path. Result has
        text=None and fell_back=True."""
        gen1 = _gen_response("First weak draft.")
        gen2 = _gen_response("Still-weak revised draft.")
        fail = _critic_payload(False, 3.0, ["bad"], "fix it")
        responses = [
            gen1,
            _gen_response(fail),  # voice fail
            _gen_response(fail),  # headline fail (2 failures → Rung 1 escalates)
            _gen_response(fail),  # factuality fail (3 failures → Rung 2 trips)
            gen2,
            _gen_response(fail),  # voice still fails
            _gen_response(fail),  # headline still fails
            _gen_response(fail),  # factuality still fails
        ]
        patcher, _ = _patch_runtime(responses)
        with patcher:
            result = loop_c_critic_revise("draft")
        assert result.fell_back is True
        assert result.text is None
        assert result.fallback_reason is not None
        assert "consecutive_critic_failures" in result.fallback_reason

    def test_rung_3_weekly_ceiling_halts_loop(self):
        """Rung 3: per-surface weekly spend > ceiling → loop returns
        immediately with fell_back=True / reason='weekly_ceiling'."""
        # Pre-populate the counter past the ceiling for tier1.edition_cover.
        from cfb_rankings.config import WEEKLY_CEILINGS_CENTS
        ceiling = WEEKLY_CEILINGS_CENTS["tier1.edition_cover"]
        quality_loop._CIRCUIT_STATE.weekly_spend_cents["tier1.edition_cover"] = ceiling + 100

        patcher, mock_fn = _patch_runtime([])
        with patcher:
            result = loop_c_critic_revise(
                "draft the cover",
                surface="tier1.edition_cover",
            )
        assert result.fell_back is True
        assert result.fallback_reason == "weekly_ceiling"
        assert mock_fn.call_count == 0  # no SDK calls happened


# ---------------------------------------------------------------------------
# 4 — loop_for_surface() dispatch with empty + populated flags
# ---------------------------------------------------------------------------

class TestDispatch:

    def test_loop_for_surface_returns_none_when_flag_unset(self):
        """With QUALITY_LOOP_FLAGS empty (Sprint v5-1 default), every
        surface returns None — call sites stay on the legacy path."""
        # Force empty.
        with mock.patch("cfb_rankings.config.QUALITY_LOOP_FLAGS", {}):
            assert loop_for_surface("tier1.edition_cover") is None
            assert loop_for_surface("tier3.wire") is None
            assert loop_for_surface("nonexistent.surface") is None

    def test_loop_for_surface_returns_configured_function(self):
        """When a flag is set, dispatch returns the matching loop fn."""
        flags = {
            "tier1.edition_cover": LoopPattern.D_ADVERSARIAL,
            "tier1.daily_lead": LoopPattern.C_CRITIC_REVISE,
            "tier1.storyline_chapter": LoopPattern.E_CONTINUITY,
            "tier3.wire": LoopPattern.A_SINGLE_SHOT,
        }
        with mock.patch("cfb_rankings.config.QUALITY_LOOP_FLAGS", flags):
            assert loop_for_surface("tier1.edition_cover") is loop_d_adversarial
            assert loop_for_surface("tier1.daily_lead") is loop_c_critic_revise
            assert loop_for_surface("tier1.storyline_chapter") is loop_e_continuity
            assert loop_for_surface("tier3.wire") is loop_a_single_shot
            # Unmapped surface still returns None.
            assert loop_for_surface("tier1.heisman_weekly") is None

    def test_loop_for_surface_tolerates_string_pattern_values(self):
        """If a flag value is the string form (e.g. loaded from JSON),
        dispatch still works."""
        flags = {"tier3.wire": "A_single_shot"}
        with mock.patch("cfb_rankings.config.QUALITY_LOOP_FLAGS", flags):
            assert loop_for_surface("tier3.wire") is loop_a_single_shot
