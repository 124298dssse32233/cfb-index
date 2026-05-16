"""Sprint v5-3 — batch Pattern C flag flips (Tier-1 surfaces).

Tests the next four Tier-1 surfaces wired to ``loop_c_critic_revise``:

    * ``tier1.daily_lead``
    * ``tier1.daily_supporting``
    * ``tier1.heisman_weekly``
    * ``tier1.mailbag``
    * ``tier1.reaction_story``

For each surface, four behavior tests:

    1. Flag absent → sync / offline-stub path used; no loop call.
    2. Flag set → ``loop_c_critic_revise`` called with the expected
       surface key + subcommand + system prompt + max_tokens.
    3. Loop falls back (``fell_back=True``) → fallback path used; the
       loop_result is still threaded back so telemetry stays observable.
    4. Prompt body folds the v5.3 Part 4 manifest sections correctly.

Plus a small ConfigDefaults block validating that the config-level flag
flips landed and the surface key strings haven't drifted.

All Anthropic SDK calls are mocked. Nothing should touch the network.
"""
from __future__ import annotations

from typing import Any
from unittest import mock

import pytest

from cfb_rankings import quality_loop as _ql_module
from cfb_rankings.quality_loop import LoopPattern, LoopResult


# ---------------------------------------------------------------------------
# Shared fixtures + helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_quality_loop_state():
    _ql_module.reset_circuit_state()
    yield
    _ql_module.reset_circuit_state()


@pytest.fixture
def fake_db():
    return mock.MagicMock(name="Database")


def _ok_loop_result(text: str = "GENERATED BODY.") -> LoopResult:
    return LoopResult(
        text=text,
        pattern=LoopPattern.C_CRITIC_REVISE.value,
        final_score=8.4,
        verdicts=[],
        revise_count=0,
        total_tokens={"input": 1200, "output": 800},
    )


def _fell_back_loop_result(reason: str = "offline_stub") -> LoopResult:
    return LoopResult(
        text=None,
        pattern=LoopPattern.C_CRITIC_REVISE.value,
        final_score=0.0,
        verdicts=[],
        revise_count=0,
        total_tokens={"input": 0, "output": 0},
        fell_back=True,
        fallback_reason=reason,
    )


# ===========================================================================
# 1) tier1.daily_lead
# ===========================================================================

from cfb_rankings.daily.cover_essay import (
    DAILY_LEAD_SYSTEM_PROMPT,
    LEAD_MAX_TOKENS,
    LEAD_SUBCOMMAND,
    LEAD_SURFACE_KEY,
    DailyTakeResult,
    compose_lead_prompt_body,
    synthesize_daily_lead,
)


def _stub_daily_context() -> dict[str, Any]:
    return {
        "date": "2026-10-15",
        "week_iso": "2026-W42",
        "headline_entity_slug": "alabama",
        "headline_entity_team_id": 333,
        "mood_delta_7d": {"week_start_date": "2026-10-12", "delta": 0.22},
        "mood_same_week_1yr_ago": {"week_start_date": "2025-10-13", "score": 0.41},
        "cohort_transitions": [{"conference": "SEC", "left": 0.5, "right": 0.8}],
        "cohort_divergence": [{"cohort": "stat_folks", "score": 0.31}],
        "archive_threads": [{"thread": "saban-legacy"}],
        "recent_daily_headlines": [
            {"edition_date": "2026-10-14", "headline": "Manning's Snap-Share Cliff"}
        ],
        "power_delta_7d": {"brier_shift": 0.012},
    }


class TestDailyLeadFlagAbsent:

    def test_flag_absent_uses_offline_stub(self, fake_db):
        fb = mock.MagicMock(return_value="OFFLINE STUB BODY.")
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS", {}, clear=True,
        ), mock.patch.object(_ql_module, "loop_c_critic_revise") as mock_loop:
            result = synthesize_daily_lead(
                edition_date="2026-10-15",
                db=fake_db,
                fallback=fb,
            )
        assert isinstance(result, DailyTakeResult)
        assert result.text == "OFFLINE STUB BODY."
        assert result.source == "offline"
        assert result.rank == 1
        assert result.fallback_reason == "flag_absent"
        mock_loop.assert_not_called()
        fb.assert_called_once_with("2026-10-15")


class TestDailyLeadFlagSet:

    def test_loop_c_called_with_expected_args(self, fake_db):
        ctx_builder = mock.MagicMock(return_value=_stub_daily_context())
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {LEAD_SURFACE_KEY: LoopPattern.C_CRITIC_REVISE},
            clear=True,
        ), mock.patch(
            "cfb_rankings.daily.cover_essay.loop_c_critic_revise",
            return_value=_ok_loop_result("LEAD BODY."),
        ) as mock_loop:
            result = synthesize_daily_lead(
                edition_date="2026-10-15",
                db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=ctx_builder,
            )
        assert mock_loop.call_count == 1
        _args, kwargs = mock_loop.call_args
        assert kwargs["surface"] == LEAD_SURFACE_KEY == "tier1.daily_lead"
        assert kwargs["subcommand"] == LEAD_SUBCOMMAND == "quality_loop.C.daily_lead"
        assert kwargs["system"] == DAILY_LEAD_SYSTEM_PROMPT
        assert kwargs["max_tokens"] == LEAD_MAX_TOKENS
        prompt_arg = _args[0]
        assert "SOURCE OBSERVATIONS" in prompt_arg
        assert "EDITION DATE: 2026-10-15" in prompt_arg
        assert result.text == "LEAD BODY."
        assert result.source == "llm"
        assert result.rank == 1


class TestDailyLeadLoopFellBack:

    def test_falls_back_when_loop_fell_back(self, fake_db):
        fb = mock.MagicMock(return_value="OFFLINE STUB BODY.")
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {LEAD_SURFACE_KEY: LoopPattern.C_CRITIC_REVISE},
            clear=True,
        ), mock.patch(
            "cfb_rankings.daily.cover_essay.loop_c_critic_revise",
            return_value=_fell_back_loop_result("offline_stub"),
        ):
            result = synthesize_daily_lead(
                edition_date="2026-10-15",
                db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=mock.MagicMock(return_value=_stub_daily_context()),
                fallback=fb,
            )
        assert result.source == "offline"
        assert result.text == "OFFLINE STUB BODY."
        assert result.fallback_reason == "offline_stub"
        fb.assert_called_once_with("2026-10-15")


class TestDailyLeadPromptManifest:

    def test_compose_lead_prompt_body_includes_every_manifest_section(self):
        body = compose_lead_prompt_body(_stub_daily_context())
        for label in [
            "HEADLINE ENTITY",
            "MOOD DELTA 7D",
            "MOOD SAME-WEEK 1YR AGO",
            "COHORT TRANSITIONS",
            "COHORT DIVERGENCE",
            "RECENT DAILY HEADLINES",
            "POWER DELTA 7D",
            "ARCHIVE THREADS",
        ]:
            assert label in body, f"section {label!r} missing"
        assert "SOURCE OBSERVATIONS" in body
        assert "alabama" in body
        assert "Manning" in body

    def test_empty_context_renders_gracefully(self):
        body = compose_lead_prompt_body({"date": "2026-10-15"})
        assert "MOOD DELTA 7D" in body
        assert "(empty" in body


# ===========================================================================
# 2) tier1.daily_supporting
# ===========================================================================

from cfb_rankings.daily.cover_essay import (
    DAILY_SUPPORTING_SYSTEM_PROMPT,
    SUPPORTING_MAX_TOKENS,
    SUPPORTING_SUBCOMMAND,
    SUPPORTING_SURFACE_KEY,
    compose_supporting_prompt_body,
    synthesize_daily_supporting,
)


class TestDailySupportingFlagAbsent:

    def test_flag_absent_uses_offline_stub(self, fake_db):
        fb = mock.MagicMock(return_value="STUB SUPPORTING TAKE.")
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS", {}, clear=True,
        ), mock.patch.object(_ql_module, "loop_c_critic_revise") as mock_loop:
            result = synthesize_daily_supporting(
                edition_date="2026-10-15",
                rank=2,
                db=fake_db,
                fallback=fb,
            )
        assert result.source == "offline"
        assert result.text == "STUB SUPPORTING TAKE."
        assert result.rank == 2
        mock_loop.assert_not_called()
        fb.assert_called_once_with("2026-10-15", 2)


class TestDailySupportingFlagSet:

    @pytest.mark.parametrize("rank", [2, 3])
    def test_loop_c_called_with_expected_args(self, fake_db, rank):
        ctx_builder = mock.MagicMock(return_value=_stub_daily_context())
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {SUPPORTING_SURFACE_KEY: LoopPattern.C_CRITIC_REVISE},
            clear=True,
        ), mock.patch(
            "cfb_rankings.daily.cover_essay.loop_c_critic_revise",
            return_value=_ok_loop_result(f"SUPPORTING BODY {rank}."),
        ) as mock_loop:
            result = synthesize_daily_supporting(
                edition_date="2026-10-15",
                rank=rank,
                db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=ctx_builder,
            )
        assert mock_loop.call_count == 1
        _args, kwargs = mock_loop.call_args
        assert kwargs["surface"] == SUPPORTING_SURFACE_KEY == "tier1.daily_supporting"
        assert kwargs["subcommand"] == SUPPORTING_SUBCOMMAND == "quality_loop.C.daily_supporting"
        assert kwargs["system"] == DAILY_SUPPORTING_SYSTEM_PROMPT
        assert kwargs["max_tokens"] == SUPPORTING_MAX_TOKENS
        prompt_arg = _args[0]
        assert f"RANK IN EDITION: {rank} of 3" in prompt_arg
        assert result.text == f"SUPPORTING BODY {rank}."
        assert result.source == "llm"
        assert result.rank == rank

    def test_invalid_rank_raises(self, fake_db):
        with pytest.raises(ValueError, match="rank must be 2 or 3"):
            synthesize_daily_supporting(
                edition_date="2026-10-15", rank=1, db=fake_db,
            )


class TestDailySupportingLoopFellBack:

    def test_falls_back_when_loop_returns_no_text(self, fake_db):
        fb = mock.MagicMock(return_value="STUB FOR RANK 3.")
        no_text = LoopResult(
            text=None, pattern=LoopPattern.C_CRITIC_REVISE.value,
            final_score=0.0, verdicts=[], revise_count=0,
            total_tokens={"input": 0, "output": 0},
            fell_back=False, fallback_reason=None,
        )
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {SUPPORTING_SURFACE_KEY: LoopPattern.C_CRITIC_REVISE},
            clear=True,
        ), mock.patch(
            "cfb_rankings.daily.cover_essay.loop_c_critic_revise",
            return_value=no_text,
        ):
            result = synthesize_daily_supporting(
                edition_date="2026-10-15",
                rank=3,
                db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=mock.MagicMock(return_value=_stub_daily_context()),
                fallback=fb,
            )
        assert result.text == "STUB FOR RANK 3."
        assert result.source == "offline"
        assert result.fallback_reason == "loop_returned_no_text"
        assert result.rank == 3


class TestDailySupportingPromptManifest:

    def test_focus_angle_threads_into_prompt(self):
        body_rank2 = compose_supporting_prompt_body(_stub_daily_context(), rank=2)
        body_rank3 = compose_supporting_prompt_body(_stub_daily_context(), rank=3)
        assert "second angle" in body_rank2
        assert "buried lede" in body_rank3
        assert "RANK IN EDITION: 2 of 3" in body_rank2
        assert "RANK IN EDITION: 3 of 3" in body_rank3
        for body in (body_rank2, body_rank3):
            assert "COHORT DIVERGENCE" in body
            assert "COHORT TRANSITIONS" in body
            assert "MOOD DELTA 7D" in body


# ===========================================================================
# 3) tier1.heisman_weekly
# ===========================================================================

from cfb_rankings.heisman.cover_essay import (
    HEISMAN_WEEKLY_SYSTEM_PROMPT,
    MAX_TOKENS as HEISMAN_MAX_TOKENS,
    SUBCOMMAND as HEISMAN_SUBCOMMAND,
    SURFACE_KEY as HEISMAN_SURFACE_KEY,
    HeismanNarrativeResult,
    compose_prompt_body as heisman_compose_prompt_body,
    synthesize_heisman_weekly,
)


def _stub_heisman_context() -> dict[str, Any]:
    return {
        "season": 2026,
        "week": 12,
        "top_10": [
            {"player_id": 7, "team_id": 333, "rank_overall": 1,
             "latent_score": 0.92, "win_probability": 0.58,
             "finalist_probability": 0.81},
            {"player_id": 11, "team_id": 401, "rank_overall": 2,
             "latent_score": 0.84, "win_probability": 0.19,
             "finalist_probability": 0.71},
        ],
        "market_odds": [
            {"player_id": 7, "player_name": "Arch Manning",
             "provider": "DraftKings",
             "american_odds": -130, "implied_probability": 0.565},
        ],
        "vote_history_archetype_comps": [
            {"season_year": 2019, "player_id": 99, "place": 1,
             "winner_flag": 1, "first_place_votes": 841,
             "total_points": 2608},
        ],
        "last_4_games_top_5": [
            {"player_id": 7, "games": [{"week": 11, "ypc": 6.4}],
             "honors": []},
        ],
        "conversation_volume_top_5": [
            {"player_id": 7, "quotes": [{"text": "Manning is locked in.",
                                         "attribution": "Beat Reporter X"}]},
        ],
        "archive_threads": [],
    }


class TestHeismanWeeklyFlagAbsent:

    def test_flag_absent_returns_none_source(self, fake_db):
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS", {}, clear=True,
        ), mock.patch.object(_ql_module, "loop_c_critic_revise") as mock_loop:
            result = synthesize_heisman_weekly(
                season=2026, week=12, db=fake_db,
            )
        assert isinstance(result, HeismanNarrativeResult)
        assert result.text is None
        assert result.source == "none"
        assert result.fallback_reason == "flag_absent_no_template"
        mock_loop.assert_not_called()


class TestHeismanWeeklyFlagSet:

    def test_loop_c_called_with_expected_args(self, fake_db):
        ctx_builder = mock.MagicMock(return_value=_stub_heisman_context())
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {HEISMAN_SURFACE_KEY: LoopPattern.C_CRITIC_REVISE},
            clear=True,
        ), mock.patch(
            "cfb_rankings.heisman.cover_essay.loop_c_critic_revise",
            return_value=_ok_loop_result("HEISMAN NARRATIVE BODY."),
        ) as mock_loop:
            result = synthesize_heisman_weekly(
                season=2026, week=12, db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=ctx_builder,
            )
        assert mock_loop.call_count == 1
        _args, kwargs = mock_loop.call_args
        assert kwargs["surface"] == HEISMAN_SURFACE_KEY == "tier1.heisman_weekly"
        assert kwargs["subcommand"] == HEISMAN_SUBCOMMAND == "quality_loop.C.heisman_weekly"
        assert kwargs["system"] == HEISMAN_WEEKLY_SYSTEM_PROMPT
        assert kwargs["max_tokens"] == HEISMAN_MAX_TOKENS == 3072
        prompt_arg = _args[0]
        assert "SOURCE OBSERVATIONS" in prompt_arg
        assert "SEASON: 2026" in prompt_arg
        assert "WEEK: 12" in prompt_arg
        assert "BOARD TOP 10" in prompt_arg
        assert result.text == "HEISMAN NARRATIVE BODY."
        assert result.source == "llm"


class TestHeismanWeeklyLoopFellBack:

    def test_falls_back_to_template_returns_none(self, fake_db):
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {HEISMAN_SURFACE_KEY: LoopPattern.C_CRITIC_REVISE},
            clear=True,
        ), mock.patch(
            "cfb_rankings.heisman.cover_essay.loop_c_critic_revise",
            return_value=_fell_back_loop_result("weekly_ceiling"),
        ):
            result = synthesize_heisman_weekly(
                season=2026, week=12, db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=mock.MagicMock(return_value=_stub_heisman_context()),
            )
        assert result.text is None
        assert result.source == "none"
        assert result.fallback_reason == "weekly_ceiling"


class TestHeismanWeeklyPromptManifest:

    def test_compose_prompt_body_includes_every_manifest_section(self):
        body = heisman_compose_prompt_body(_stub_heisman_context())
        for label in [
            "BOARD TOP 10",
            "MARKET ODDS",
            "VOTE HISTORY ARCHETYPE COMPS",
            "LAST 4 GAMES",
            "CONVERSATION VOLUME TOP 5",
            "ARCHIVE THREADS",
        ]:
            assert label in body, f"section {label!r} missing"
        assert "SOURCE OBSERVATIONS" in body
        assert "Arch Manning" in body
        assert "DraftKings" in body


# ===========================================================================
# 4) tier1.mailbag
# ===========================================================================

from cfb_rankings.mailbag.synthesizer import (
    MAILBAG_MAX_TOKENS,
    MAILBAG_SUBCOMMAND,
    MAILBAG_SURFACE_KEY,
    MAILBAG_SYSTEM_PROMPT,
    MailbagAnswerResult,
    compose_mailbag_prompt_body,
    synthesize_mailbag_answer,
)


def _stub_mailbag_context() -> dict[str, Any]:
    return {
        "question_id": 42,
        "question": {
            "id": 42,
            "submitter_handle": "tide-fan-77",
            "question_text": "How real is Alabama's portal reload?",
            "topic_tags_json": '["alabama","portal"]',
            "status": "curated",
            "submitted_at_utc": "2026-10-14T18:32:00Z",
        },
        "topic_tags": ["alabama", "portal"],
        "conversation_quotes": [
            {"text": "Saban's hand on the recruiting wheel is unmistakable.",
             "attribution": "Marcus Spears, ESPN"},
            {"text": "Reload, not rebuild — that's the read.",
             "attribution": "Stewart Mandel, The Athletic"},
            {"text": "Watch the depth chart, not the headlines.",
             "attribution": "Saturday Down South"},
        ],
        "fanbase_classification_history": [
            {"program_slug": "alabama",
             "history": [
                 {"season_year": 2025, "primary_archetype_slug": "blue_blood",
                  "primary_confidence": 0.93}
             ]},
        ],
        "archive_threads": [],
        "past_mailbag_answers": [],
        "active_storylines_matching": [
            {"thread_slug": "saban-transition", "title": "Saban transition watch",
             "status": "active"},
        ],
    }


class TestMailbagFlagAbsent:

    def test_flag_absent_uses_offline_stub(self, fake_db):
        fb = mock.MagicMock(return_value="OFFLINE STUB ANSWER.")
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS", {}, clear=True,
        ), mock.patch.object(_ql_module, "loop_c_critic_revise") as mock_loop:
            result = synthesize_mailbag_answer(
                question_id=42, edition_slug="2026-w42", db=fake_db,
                fallback=fb,
            )
        assert isinstance(result, MailbagAnswerResult)
        assert result.text == "OFFLINE STUB ANSWER."
        assert result.source == "offline"
        assert result.fallback_reason == "flag_absent"
        mock_loop.assert_not_called()
        fb.assert_called_once()


class TestMailbagFlagSet:

    def test_loop_c_called_with_expected_args(self, fake_db):
        ctx_builder = mock.MagicMock(return_value=_stub_mailbag_context())
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {MAILBAG_SURFACE_KEY: LoopPattern.C_CRITIC_REVISE},
            clear=True,
        ), mock.patch(
            "cfb_rankings.mailbag.synthesizer._loop_c_critic_revise",
            return_value=_ok_loop_result("MAILBAG ANSWER BODY."),
        ) as mock_loop:
            result = synthesize_mailbag_answer(
                question_id=42, edition_slug="2026-w42", db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=ctx_builder,
            )
        assert mock_loop.call_count == 1
        _args, kwargs = mock_loop.call_args
        assert kwargs["surface"] == MAILBAG_SURFACE_KEY == "tier1.mailbag"
        assert kwargs["subcommand"] == MAILBAG_SUBCOMMAND == "quality_loop.C.mailbag"
        assert kwargs["system"] == MAILBAG_SYSTEM_PROMPT
        assert kwargs["max_tokens"] == MAILBAG_MAX_TOKENS == 1536
        prompt_arg = _args[0]
        assert "SOURCE OBSERVATIONS" in prompt_arg
        assert "alabama" in prompt_arg
        assert "VERBATIM SOURCE QUOTES" in prompt_arg
        assert result.text == "MAILBAG ANSWER BODY."
        assert result.source == "llm"


class TestMailbagLoopFellBack:

    def test_falls_back_when_loop_fell_back(self, fake_db):
        fb = mock.MagicMock(return_value="STUB AFTER FALLBACK.")
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {MAILBAG_SURFACE_KEY: LoopPattern.C_CRITIC_REVISE},
            clear=True,
        ), mock.patch(
            "cfb_rankings.mailbag.synthesizer._loop_c_critic_revise",
            return_value=_fell_back_loop_result("offline_stub"),
        ):
            result = synthesize_mailbag_answer(
                question_id=42, edition_slug="2026-w42", db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=mock.MagicMock(return_value=_stub_mailbag_context()),
                fallback=fb,
            )
        assert result.source == "offline"
        assert result.text == "STUB AFTER FALLBACK."
        assert result.fallback_reason == "offline_stub"


class TestMailbagPromptManifest:

    def test_compose_mailbag_prompt_body_includes_every_manifest_section(self):
        body = compose_mailbag_prompt_body(_stub_mailbag_context())
        for label in [
            "QUESTION",
            "TOPIC TAGS",
            "VERBATIM SOURCE QUOTES",
            "FANBASE CLASSIFICATION HISTORY",
            "ACTIVE STORYLINES MATCHING",
            "PAST MAILBAG ANSWERS",
            "ARCHIVE THREADS",
        ]:
            assert label in body, f"section {label!r} missing"
        assert "tide-fan-77" in body
        assert "Marcus Spears" in body
        assert "How real is Alabama" in body


# ===========================================================================
# 5) tier1.reaction_story
# ===========================================================================

from cfb_rankings.reactions.synthesizer import (
    REACTION_STORY_MAX_TOKENS,
    REACTION_STORY_SUBCOMMAND,
    REACTION_STORY_SURFACE_KEY,
    REACTION_STORY_SYSTEM_PROMPT,
    ReactionStoryResult,
    compose_reaction_prompt_body,
    synthesize_reaction_story,
)


def _stub_reaction_context() -> dict[str, Any]:
    return {
        "wire_id": 1234,
        "wire": {
            "id": 1234,
            "occurred_at": "2026-10-14T22:14:00Z",
            "program_slug": "alabama",
            "program_display": "Alabama",
            "actor_kind": "player",
            "action": "QB Arch Manning transfer from Texas",
            "why_it_matters": "Headline-grade portal move",
            "impact_label": "MAJOR",
            "historical_comp": "Cam Newton 2010 transfer",
            "source_name": "On3",
        },
        "historical_comp": "Cam Newton 2010 transfer",
        "cohort_divergence": [
            {"cohort": "stat_folks", "score": 0.5},
            {"cohort": "casual_fans", "score": 0.78},
            {"cohort": "die_hards", "score": 0.42},
        ],
        "cohort_quotes": [
            {"cohort": "stat_folks",
             "quotes": [{"text": "QBR projects 78 next season.",
                         "attribution": "PFF analyst"}]},
        ],
        "archive_threads": [],
        "mood_delta_7d": {"delta": 0.31},
        "surprise_index": 88.5,
    }


class TestReactionStoryFlagAbsent:

    def test_flag_absent_uses_caller_fallback(self, fake_db):
        fb = mock.MagicMock(return_value="STUB REACTION BODY.")
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS", {}, clear=True,
        ), mock.patch.object(_ql_module, "loop_c_critic_revise") as mock_loop:
            result = synthesize_reaction_story(
                wire_id=1234, db=fake_db, fallback=fb,
            )
        assert isinstance(result, ReactionStoryResult)
        assert result.text == "STUB REACTION BODY."
        assert result.source == "offline"
        assert result.fallback_reason == "flag_absent"
        mock_loop.assert_not_called()
        fb.assert_called_once_with(1234)

    def test_flag_absent_no_fallback_returns_none(self, fake_db):
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS", {}, clear=True,
        ):
            result = synthesize_reaction_story(wire_id=1234, db=fake_db)
        assert result.text is None
        assert result.source == "none"
        assert result.fallback_reason == "flag_absent_no_stub"


class TestReactionStoryFlagSet:

    def test_loop_c_called_with_expected_args(self, fake_db):
        ctx_builder = mock.MagicMock(return_value=_stub_reaction_context())
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {REACTION_STORY_SURFACE_KEY: LoopPattern.C_CRITIC_REVISE},
            clear=True,
        ), mock.patch(
            "cfb_rankings.reactions.synthesizer._rxn_loop_c_critic_revise",
            return_value=_ok_loop_result("REACTION STORY BODY."),
        ) as mock_loop:
            result = synthesize_reaction_story(
                wire_id=1234, db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=ctx_builder,
            )
        assert mock_loop.call_count == 1
        _args, kwargs = mock_loop.call_args
        assert kwargs["surface"] == REACTION_STORY_SURFACE_KEY == "tier1.reaction_story"
        assert kwargs["subcommand"] == REACTION_STORY_SUBCOMMAND == "quality_loop.C.reaction_story"
        assert kwargs["system"] == REACTION_STORY_SYSTEM_PROMPT
        assert kwargs["max_tokens"] == REACTION_STORY_MAX_TOKENS == 2048
        prompt_arg = _args[0]
        assert "SOURCE OBSERVATIONS" in prompt_arg
        assert "WIRE EVENT" in prompt_arg
        assert "COHORT QUOTES" in prompt_arg
        assert result.text == "REACTION STORY BODY."
        assert result.source == "llm"


class TestReactionStoryLoopFellBack:

    def test_falls_back_when_loop_fell_back(self, fake_db):
        fb = mock.MagicMock(return_value="STUB FALLBACK BODY.")
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {REACTION_STORY_SURFACE_KEY: LoopPattern.C_CRITIC_REVISE},
            clear=True,
        ), mock.patch(
            "cfb_rankings.reactions.synthesizer._rxn_loop_c_critic_revise",
            return_value=_fell_back_loop_result("weekly_ceiling"),
        ):
            result = synthesize_reaction_story(
                wire_id=1234, db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=mock.MagicMock(return_value=_stub_reaction_context()),
                fallback=fb,
            )
        assert result.source == "offline"
        assert result.text == "STUB FALLBACK BODY."
        assert result.fallback_reason == "weekly_ceiling"


class TestReactionStoryPromptManifest:

    def test_compose_reaction_prompt_body_includes_every_manifest_section(self):
        body = compose_reaction_prompt_body(_stub_reaction_context())
        for label in [
            "WIRE EVENT",
            "HISTORICAL COMP",
            "SURPRISE INDEX",
            "COHORT DIVERGENCE",
            "COHORT QUOTES",
            "MOOD DELTA 7D",
            "ARCHIVE THREADS",
        ]:
            assert label in body, f"section {label!r} missing"
        assert "SOURCE OBSERVATIONS" in body
        assert "WIRE ID: 1234" in body
        assert "Cam Newton" in body
        assert "Arch Manning" in body


# ===========================================================================
# 6) Config defaults — sanity that the v5-3 flag flips landed
# ===========================================================================


class TestConfigDefaults:

    def test_all_v5_3_flags_set_in_default_config(self):
        from cfb_rankings import config
        for surface in (
            "tier1.edition_cover",
            "tier1.daily_lead",
            "tier1.daily_supporting",
            "tier1.heisman_weekly",
            "tier1.mailbag",
            "tier1.reaction_story",
        ):
            assert surface in config.QUALITY_LOOP_FLAGS
            pattern = config.QUALITY_LOOP_FLAGS[surface]
            assert pattern == LoopPattern.C_CRITIC_REVISE or pattern == "C_critic_revise"

    def test_weekly_ceilings_present_for_all_v5_3_surfaces(self):
        from cfb_rankings import config
        for surface in (
            "tier1.edition_cover",
            "tier1.daily_lead",
            "tier1.daily_supporting",
            "tier1.heisman_weekly",
            "tier1.mailbag",
            "tier1.reaction_story",
        ):
            assert surface in config.WEEKLY_CEILINGS_CENTS
            assert config.WEEKLY_CEILINGS_CENTS[surface] > 0

    def test_surface_keys_match_module_constants(self):
        assert LEAD_SURFACE_KEY == "tier1.daily_lead"
        assert SUPPORTING_SURFACE_KEY == "tier1.daily_supporting"
        assert HEISMAN_SURFACE_KEY == "tier1.heisman_weekly"
        assert MAILBAG_SURFACE_KEY == "tier1.mailbag"
        assert REACTION_STORY_SURFACE_KEY == "tier1.reaction_story"

    def test_subcommands_match_module_constants(self):
        assert LEAD_SUBCOMMAND == "quality_loop.C.daily_lead"
        assert SUPPORTING_SUBCOMMAND == "quality_loop.C.daily_supporting"
        assert HEISMAN_SUBCOMMAND == "quality_loop.C.heisman_weekly"
        assert MAILBAG_SUBCOMMAND == "quality_loop.C.mailbag"
        assert REACTION_STORY_SUBCOMMAND == "quality_loop.C.reaction_story"
