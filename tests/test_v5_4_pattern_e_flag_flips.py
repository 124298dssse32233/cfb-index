"""Sprint v5-4 — Pattern E flag flips (storyline chapters + chronicle profiled).

Tests that the two Pattern E surfaces honor the
``config.QUALITY_LOOP_FLAGS`` flags and route correctly:

    * ``tier1.storyline_chapter``  → loop_e_continuity
    * ``tier1.chronicle_profiled`` → loop_e_continuity (profiled slugs only)

For each surface:

    1. Flag absent → sync path; no loop call.
    2. Flag set with no prior chapters/observations → loop_e_continuity is
       called with empty-history sentinels in the thread_history /
       entity_ledger kwargs.
    3. Flag set with prior history → loop_e_continuity is called with the
       formatted history + named-entity ledger.
    4. Loop falls back (``fell_back=True``, e.g. continuity critic
       rejection or wall-clock timeout) → sync fallback engaged.
    5. Empty thread / no observations → sync fallback when loop returns
       no text.

For chronicle specifically, an additional gate: a non-profiled slug
short-circuits to the sync path with ``fallback_reason="unprofiled_slug"``.

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
        pattern=LoopPattern.E_CONTINUITY.value,
        final_score=8.4,
        verdicts=[],
        revise_count=0,
        total_tokens={"input": 1200, "output": 800},
    )


def _fell_back_loop_result(
    reason: str = "consecutive_critic_failures_after_escalation",
) -> LoopResult:
    return LoopResult(
        text=None,
        pattern=LoopPattern.E_CONTINUITY.value,
        final_score=0.0,
        verdicts=[],
        revise_count=0,
        total_tokens={"input": 0, "output": 0},
        fell_back=True,
        fallback_reason=reason,
    )


# ===========================================================================
# 1) tier1.storyline_chapter
# ===========================================================================

from cfb_rankings.storylines.chapter_pattern_e import (
    MAX_TOKENS as STORYLINE_MAX_TOKENS,
    STORYLINE_CHAPTER_SYSTEM_PROMPT,
    SUBCOMMAND as STORYLINE_SUBCOMMAND,
    SURFACE_KEY as STORYLINE_SURFACE_KEY,
    StorylineChapterResult,
    compose_prompt_body as compose_storyline_prompt_body,
    extract_named_entity_ledger as storyline_extract_ledger,
    format_thread_history as storyline_format_history,
    synthesize_storyline_chapter,
)


def _stub_storyline_context_with_history() -> dict[str, Any]:
    """A representative context matching the v5.3 Part 4 manifest, with
    three prior chapters that look real enough for the ledger to grip on."""
    return {
        "thread_slug": "vandy-renaissance",
        "thread": {
            "thread_slug": "vandy-renaissance",
            "title": "The Vandy Renaissance",
            "dek": "Lea's rebuild becomes a national story.",
            "status": "active",
            "voice_register_source": "profile:vanderbilt",
            "chapter_count": 3,
            "last_chapter_at": "2026-05-08 09:00:00",
        },
        "last_3_chapters": [
            {
                "chapter_number": 3,
                "title": "Pavia's Run Becomes The Standard",
                "dek": "Sam Hartman called it.",
                "body_markdown": (
                    "Diego Pavia ran the option three times in the second "
                    "quarter against Alabama and produced 47 yards. The "
                    "Athletic's Stewart Mandel called it 'the standard "
                    "for Vandy's offense' on the Monday podcast. Lea has "
                    "now beaten Alabama and Auburn in the same season."
                ),
                "byline": "From The Vandy Renaissance Department",
                "published_at": "2026-05-08 09:00:00",
                "referenced_chapter_ids": [1, 2],
                "referenced_sources_json": '[{"name": "Stewart Mandel"}]',
                "pull_quote": "The standard for Vandy's offense.",
            },
            {
                "chapter_number": 2,
                "title": "Lea's Tempo Lift",
                "dek": "Practice reps tell the story.",
                "body_markdown": (
                    "Clark Lea added two-minute tempo periods to spring "
                    "practice. Beat writer Joey Knight from the "
                    "Tennessean filed three observations from one "
                    "session. Pavia hit eight straight on a hurry-up "
                    "drill."
                ),
                "byline": "From The Vandy Renaissance Department",
                "published_at": "2026-05-01 09:00:00",
                "referenced_chapter_ids": [1],
                "referenced_sources_json": '[{"name": "Joey Knight"}]',
                "pull_quote": "Eight straight on a hurry-up drill.",
            },
            {
                "chapter_number": 1,
                "title": "From The Vandy Renaissance Department",
                "dek": "The thread opens.",
                "body_markdown": (
                    "Clark Lea takes over Vanderbilt football in 2021. "
                    "By 2025 he has wins over Alabama and Auburn. The "
                    "Athletic's Andy Staples filed a 4,000-word feature."
                ),
                "byline": "From The Vandy Renaissance Department",
                "published_at": "2026-04-24 09:00:00",
                "referenced_chapter_ids": [],
                "referenced_sources_json": '[{"name": "Andy Staples"}]',
                "pull_quote": None,
            },
        ],
        "wire_per_primary_program": [
            {
                "program_slug": "vanderbilt",
                "wire_14d": [
                    {"action": "spring_practice", "actor": "Lea"},
                ],
            },
        ],
        "conversation_quotes": [
            {"source": "Solid Verbal", "ep": 247, "quote": "Vandy is real."},
        ],
        "source_observations": [
            {"entity": "vanderbilt", "kind": "team", "evidence": "spring tempo lift"},
        ],
        "prior_referenced_sources": [],
        "archive_threads": [],
    }


def _stub_storyline_context_empty() -> dict[str, Any]:
    """First chapter — no prior chapters in the manifest."""
    return {
        "thread_slug": "new-thread",
        "thread": {
            "thread_slug": "new-thread",
            "title": "A New Thread",
            "dek": "Chapter 1.",
            "status": "active",
            "voice_register_source": "editor-desk",
        },
        "last_3_chapters": [],
        "wire_per_primary_program": [],
        "conversation_quotes": [],
        "source_observations": [],
        "prior_referenced_sources": [],
        "archive_threads": [],
    }


# ---------------------------------------------------------------------------
# Storyline: flag absent
# ---------------------------------------------------------------------------


class TestStorylineFlagAbsent:

    def test_flag_absent_uses_sync_path(self, fake_db):
        """No flag → no LLM call; result.source == 'sync' (or 'none'
        if the fallback returns None as the default does)."""
        fb = mock.MagicMock(return_value="SYNC SCAFFOLD BODY.")
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS", {}, clear=True,
        ), mock.patch.object(_ql_module, "loop_e_continuity") as mock_loop:
            result = synthesize_storyline_chapter(
                thread_slug="vandy-renaissance",
                chapter_number=4,
                db=fake_db,
                fallback=fb,
            )
        assert isinstance(result, StorylineChapterResult)
        assert result.text == "SYNC SCAFFOLD BODY."
        assert result.source == "sync"
        assert result.thread_slug == "vandy-renaissance"
        assert result.chapter_number == 4
        assert result.fallback_reason == "flag_absent"
        mock_loop.assert_not_called()
        fb.assert_called_once_with("vandy-renaissance", 4)

    def test_flag_absent_no_sync_returns_none(self, fake_db):
        """No flag + fallback returns None → source='none', text=None."""
        fb = mock.MagicMock(return_value=None)
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS", {}, clear=True,
        ):
            result = synthesize_storyline_chapter(
                thread_slug="vandy-renaissance",
                chapter_number=4,
                db=fake_db,
                fallback=fb,
            )
        assert result.text is None
        assert result.source == "none"
        assert result.fallback_reason == "flag_absent_no_sync"


# ---------------------------------------------------------------------------
# Storyline: flag set with prior chapters
# ---------------------------------------------------------------------------


class TestStorylineFlagSetWithHistory:

    def test_loop_e_called_with_history_and_ledger(self, fake_db):
        """Flag set + prior chapters → loop_e_continuity gets the right
        surface, subcommand, system, max_tokens, thread_history, and
        entity_ledger kwargs."""
        ctx_builder = mock.MagicMock(
            return_value=_stub_storyline_context_with_history()
        )

        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {STORYLINE_SURFACE_KEY: LoopPattern.E_CONTINUITY},
            clear=True,
        ), mock.patch(
            "cfb_rankings.storylines.chapter_pattern_e.loop_e_continuity",
            return_value=_ok_loop_result("Chapter 4 body."),
        ) as mock_loop:
            result = synthesize_storyline_chapter(
                thread_slug="vandy-renaissance",
                chapter_number=4,
                db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=ctx_builder,
            )

        assert mock_loop.call_count == 1
        _args, kwargs = mock_loop.call_args
        # Surface + subcommand are pinned.
        assert kwargs["surface"] == STORYLINE_SURFACE_KEY == "tier1.storyline_chapter"
        assert kwargs["subcommand"] == STORYLINE_SUBCOMMAND == "quality_loop.E.storyline_chapter"
        assert kwargs["system"] == STORYLINE_CHAPTER_SYSTEM_PROMPT
        assert kwargs["max_tokens"] == STORYLINE_MAX_TOKENS == 4096

        # The thread_history block carries the prior chapter teasers,
        # newest first.
        history = kwargs["thread_history"]
        assert isinstance(history, str)
        assert "Chapter 3: Pavia's Run Becomes The Standard" in history
        assert "Chapter 2: Lea's Tempo Lift" in history
        assert "Chapter 1: From The Vandy Renaissance Department" in history
        # Newest first — chapter 3 appears before chapter 1.
        assert history.find("Chapter 3:") < history.find("Chapter 1:")

        # The entity ledger picks up proper nouns that recurred.
        ledger = kwargs["entity_ledger"]
        assert isinstance(ledger, str)
        assert "Vandy" in ledger or "Vanderbilt" in ledger
        assert "Lea" in ledger
        # Common stopword tokens should NOT show up.
        assert "The (appears" not in ledger

        # critic_context surfaces source observations for the
        # factuality critic.
        cc = kwargs["critic_context"]
        assert isinstance(cc, dict)
        assert cc["surface"] == STORYLINE_SURFACE_KEY
        assert "source_observations" in cc

        # The positional prompt argument folds in manifest sections.
        prompt_arg = _args[0] if _args else kwargs.get("prompt")
        assert isinstance(prompt_arg, str)
        assert "SOURCE OBSERVATIONS" in prompt_arg
        assert "THREAD" in prompt_arg
        assert "NEXT CHAPTER NUMBER: 4" in prompt_arg

        # Result envelope correct.
        assert result.text == "Chapter 4 body."
        assert result.source == "llm"
        assert result.loop_result is not None
        assert result.chapter_number == 4


# ---------------------------------------------------------------------------
# Storyline: flag set, no prior chapters
# ---------------------------------------------------------------------------


class TestStorylineFlagSetEmpty:

    def test_loop_e_called_with_empty_history_sentinels(self, fake_db):
        """Flag set + no prior chapters → loop_e_continuity receives the
        'no prior chapters' sentinel in thread_history and a similar
        sentinel for the entity_ledger."""
        ctx_builder = mock.MagicMock(
            return_value=_stub_storyline_context_empty()
        )

        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {STORYLINE_SURFACE_KEY: LoopPattern.E_CONTINUITY},
            clear=True,
        ), mock.patch(
            "cfb_rankings.storylines.chapter_pattern_e.loop_e_continuity",
            return_value=_ok_loop_result("Chapter 1 body."),
        ) as mock_loop:
            result = synthesize_storyline_chapter(
                thread_slug="new-thread",
                chapter_number=1,
                db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=ctx_builder,
            )

        assert mock_loop.call_count == 1
        _args, kwargs = mock_loop.call_args
        history = kwargs["thread_history"]
        ledger = kwargs["entity_ledger"]
        assert "no prior chapters" in history.lower()
        assert "ledger is empty" in ledger.lower() or "no proper-noun" in ledger.lower()
        assert result.text == "Chapter 1 body."
        assert result.source == "llm"


# ---------------------------------------------------------------------------
# Storyline: loop fell back (continuity critic rejection)
# ---------------------------------------------------------------------------


class TestStorylineLoopFellBack:

    def test_continuity_rejection_falls_through_to_sync(self, fake_db):
        """Loop returns fell_back=True (continuity critic caught a
        contradiction, or wall-clock timeout, or Rung-2 fall-back) →
        sync fallback engaged."""
        fb = mock.MagicMock(return_value="SYNC FALLBACK BODY")
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {STORYLINE_SURFACE_KEY: LoopPattern.E_CONTINUITY},
            clear=True,
        ), mock.patch(
            "cfb_rankings.storylines.chapter_pattern_e.loop_e_continuity",
            return_value=_fell_back_loop_result(
                reason="consecutive_critic_failures_after_escalation"
            ),
        ):
            result = synthesize_storyline_chapter(
                thread_slug="vandy-renaissance",
                chapter_number=4,
                db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=mock.MagicMock(
                    return_value=_stub_storyline_context_with_history()
                ),
                fallback=fb,
            )

        assert result.text == "SYNC FALLBACK BODY"
        assert result.source == "sync"
        assert result.loop_result is not None
        assert result.loop_result.fell_back is True
        assert (
            result.fallback_reason
            == "consecutive_critic_failures_after_escalation"
        )
        fb.assert_called_once_with("vandy-renaissance", 4)

    def test_empty_thread_falls_back_when_loop_returns_no_text(self, fake_db):
        """Loop returns text=None (offline-stub or empty SDK response)
        for a brand-new thread → sync fallback engaged."""
        fb = mock.MagicMock(return_value=None)
        no_text_result = LoopResult(
            text=None,
            pattern=LoopPattern.E_CONTINUITY.value,
            final_score=0.0,
            verdicts=[],
            revise_count=0,
            total_tokens={"input": 0, "output": 0},
            fell_back=False,
            fallback_reason=None,
        )
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {STORYLINE_SURFACE_KEY: LoopPattern.E_CONTINUITY},
            clear=True,
        ), mock.patch(
            "cfb_rankings.storylines.chapter_pattern_e.loop_e_continuity",
            return_value=no_text_result,
        ):
            result = synthesize_storyline_chapter(
                thread_slug="new-thread",
                chapter_number=1,
                db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=mock.MagicMock(
                    return_value=_stub_storyline_context_empty()
                ),
                fallback=fb,
            )
        assert result.text is None
        assert result.source == "none"
        assert result.fallback_reason == "loop_returned_no_text"


# ---------------------------------------------------------------------------
# Storyline: helpers (format_thread_history + extract_named_entity_ledger)
# ---------------------------------------------------------------------------


class TestStorylineHelpers:

    def test_format_thread_history_handles_empty(self):
        out = storyline_format_history([])
        assert "no prior chapters" in out.lower()

    def test_format_thread_history_newest_first(self):
        out = storyline_format_history(
            _stub_storyline_context_with_history()["last_3_chapters"]
        )
        # Chapter 3 (newest) before chapter 1.
        assert out.find("Chapter 3:") < out.find("Chapter 1:")
        # Pull quotes surface when present.
        assert "PULL QUOTE:" in out

    def test_extract_named_entity_ledger_ranks_by_frequency(self):
        out = storyline_extract_ledger(
            _stub_storyline_context_with_history()["last_3_chapters"]
        )
        # Lea / Vandy / Vanderbilt show up multiple times — should be in
        # the ledger.
        assert "Lea" in out
        # Stopwords like "The" or "From" should not appear.
        assert "The (appears" not in out


# ===========================================================================
# 2) tier1.chronicle_profiled
# ===========================================================================

from cfb_rankings.team_pages.chronicle_pattern_e import (
    CHRONICLE_PROFILED_SYSTEM_PROMPT,
    MAX_TOKENS as CHRONICLE_MAX_TOKENS,
    SUBCOMMAND as CHRONICLE_SUBCOMMAND,
    SURFACE_KEY as CHRONICLE_SURFACE_KEY,
    ChronicleCardResult,
    compose_prompt_body as compose_chronicle_prompt_body,
    extract_named_entity_ledger as chronicle_extract_ledger,
    format_thread_history as chronicle_format_history,
    is_profiled,
    synthesize_chronicle_card,
)


def _stub_chronicle_context_with_history() -> dict[str, Any]:
    """Profiled program with recent chronicle observations."""
    return {
        "program_slug": "alabama",
        "week": 12,
        "team_id": 333,
        "candidate_observations_evidence": {
            "rivalry": "Auburn week — Pavia revenge angle",
            "player_arc": "Manning sophomore leap",
        },
        "recent_chronicle_headlines": [
            {
                "card_type": "season_arc",
                "headline": "Alabama's red-zone dropoff is a Saban echo",
                "week": 11,
                "season_year": 2025,
                "source_attribution": "Aaron Suttles · The Athletic · Mon",
                "surprise_score": 0.72,
            },
            {
                "card_type": "rivalry",
                "headline": "The Auburn special-teams gap, again",
                "week": 10,
                "season_year": 2025,
                "source_attribution": "Solid Verbal pod ep 247",
                "surprise_score": 0.58,
            },
            {
                "card_type": "archive",
                "headline": "Manning's snap-share matches 2020 Mac Jones",
                "week": 9,
                "season_year": 2025,
                "source_attribution": "Andy Staples · On3 · Fri",
                "surprise_score": 0.64,
            },
        ],
        "fanbase_classification_history": [
            {
                "season_year": 2025,
                "primary_archetype_slug": "national-narrative",
                "primary_confidence": 0.82,
                "modifier_slugs_json": "[\"blueblood\"]",
            },
        ],
        "power_ratings_sparkline_6y": [
            {"season_year": 2020, "rank": 1},
            {"season_year": 2021, "rank": 1},
            {"season_year": 2022, "rank": 6},
            {"season_year": 2023, "rank": 4},
            {"season_year": 2024, "rank": 7},
            {"season_year": 2025, "rank": 5},
        ],
        "player_archetype_peers": [
            {"player": "Mac Jones", "season": 2020, "stat_line": "11-1, 4500 yds"},
        ],
    }


def _stub_chronicle_context_empty() -> dict[str, Any]:
    """Profiled program with no prior observations."""
    return {
        "program_slug": "alabama",
        "week": 1,
        "team_id": 333,
        "candidate_observations_evidence": None,
        "recent_chronicle_headlines": [],
        "fanbase_classification_history": [],
        "power_ratings_sparkline_6y": [],
        "player_archetype_peers": [],
    }


# ---------------------------------------------------------------------------
# Chronicle: flag absent
# ---------------------------------------------------------------------------


class TestChronicleFlagAbsent:

    def test_profiled_flag_absent_uses_sync_path(self, fake_db):
        """Profiled slug + flag absent → sync path."""
        fb = mock.MagicMock(return_value="SYNC TEMPLATE CARD.")
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS", {}, clear=True,
        ), mock.patch.object(_ql_module, "loop_e_continuity") as mock_loop, \
             mock.patch(
                "cfb_rankings.team_pages.chronicle_pattern_e.is_profiled",
                return_value=True,
            ):
            result = synthesize_chronicle_card(
                program_slug="alabama",
                week=12,
                db=fake_db,
                fallback=fb,
            )
        assert isinstance(result, ChronicleCardResult)
        assert result.source == "sync"
        assert result.text == "SYNC TEMPLATE CARD."
        assert result.fallback_reason == "flag_absent"
        assert result.program_slug == "alabama"
        assert result.week == 12
        mock_loop.assert_not_called()
        fb.assert_called_once_with("alabama", 12)


# ---------------------------------------------------------------------------
# Chronicle: unprofiled slug (flag treated as unset)
# ---------------------------------------------------------------------------


class TestChronicleUnprofiled:

    def test_unprofiled_slug_short_circuits_to_sync(self, fake_db):
        """Unprofiled slug → Pattern E never fires even with flag set."""
        fb = mock.MagicMock(return_value="UNPROFILED SYNC CARD.")
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {CHRONICLE_SURFACE_KEY: LoopPattern.E_CONTINUITY},
            clear=True,
        ), mock.patch.object(_ql_module, "loop_e_continuity") as mock_loop, \
             mock.patch(
                "cfb_rankings.team_pages.chronicle_pattern_e.is_profiled",
                return_value=False,
            ):
            result = synthesize_chronicle_card(
                program_slug="east-carolina",
                week=12,
                db=fake_db,
                fallback=fb,
            )
        assert result.source == "sync"
        assert result.text == "UNPROFILED SYNC CARD."
        assert result.fallback_reason == "unprofiled_slug"
        mock_loop.assert_not_called()
        fb.assert_called_once_with("east-carolina", 12)

    def test_unprofiled_slug_no_sync_returns_none(self, fake_db):
        """Unprofiled + no fallback body → text=None."""
        fb = mock.MagicMock(return_value=None)
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {CHRONICLE_SURFACE_KEY: LoopPattern.E_CONTINUITY},
            clear=True,
        ), mock.patch(
            "cfb_rankings.team_pages.chronicle_pattern_e.is_profiled",
            return_value=False,
        ):
            result = synthesize_chronicle_card(
                program_slug="east-carolina",
                week=12,
                db=fake_db,
                fallback=fb,
            )
        assert result.source == "none"
        assert result.text is None
        assert result.fallback_reason == "unprofiled_slug_no_sync"


# ---------------------------------------------------------------------------
# Chronicle: flag set + profiled + observations
# ---------------------------------------------------------------------------


class TestChronicleFlagSetWithHistory:

    def test_loop_e_called_with_history_and_ledger(self, fake_db):
        """Flag set + profiled + observations → loop_e_continuity gets
        the formatted thread_history + entity_ledger."""
        ctx_builder = mock.MagicMock(
            return_value=_stub_chronicle_context_with_history()
        )

        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {CHRONICLE_SURFACE_KEY: LoopPattern.E_CONTINUITY},
            clear=True,
        ), mock.patch(
            "cfb_rankings.team_pages.chronicle_pattern_e.is_profiled",
            return_value=True,
        ), mock.patch(
            "cfb_rankings.team_pages.chronicle_pattern_e.loop_e_continuity",
            return_value=_ok_loop_result("Card body for alabama W12."),
        ) as mock_loop:
            result = synthesize_chronicle_card(
                program_slug="alabama",
                week=12,
                db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=ctx_builder,
            )

        assert mock_loop.call_count == 1
        _args, kwargs = mock_loop.call_args
        assert kwargs["surface"] == CHRONICLE_SURFACE_KEY == "tier1.chronicle_profiled"
        assert kwargs["subcommand"] == CHRONICLE_SUBCOMMAND == "quality_loop.E.chronicle_profiled"
        assert kwargs["system"] == CHRONICLE_PROFILED_SYSTEM_PROMPT
        assert kwargs["max_tokens"] == CHRONICLE_MAX_TOKENS == 2048

        history = kwargs["thread_history"]
        assert isinstance(history, str)
        assert "Alabama's red-zone dropoff" in history
        assert "Auburn special-teams gap" in history

        ledger = kwargs["entity_ledger"]
        assert isinstance(ledger, str)
        # Proper-noun entities from prior headlines and the candidate
        # evidence both show up.
        assert "Alabama" in ledger or "Manning" in ledger or "Auburn" in ledger

        cc = kwargs["critic_context"]
        assert isinstance(cc, dict)
        assert cc["surface"] == CHRONICLE_SURFACE_KEY
        assert "source_observations" in cc

        prompt_arg = _args[0] if _args else kwargs.get("prompt")
        assert isinstance(prompt_arg, str)
        assert "PROGRAM SLUG: alabama" in prompt_arg
        assert "WEEK: 12" in prompt_arg
        assert "POWER RATINGS SPARKLINE" in prompt_arg
        assert "PLAYER ARCHETYPE PEERS" in prompt_arg

        assert result.text == "Card body for alabama W12."
        assert result.source == "llm"
        assert result.program_slug == "alabama"
        assert result.week == 12


# ---------------------------------------------------------------------------
# Chronicle: flag set + profiled + no observations
# ---------------------------------------------------------------------------


class TestChronicleFlagSetEmpty:

    def test_empty_observations_uses_sentinel_history(self, fake_db):
        """No prior observations → empty-history sentinel in
        thread_history; ledger is the empty sentinel too."""
        ctx_builder = mock.MagicMock(
            return_value=_stub_chronicle_context_empty()
        )

        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {CHRONICLE_SURFACE_KEY: LoopPattern.E_CONTINUITY},
            clear=True,
        ), mock.patch(
            "cfb_rankings.team_pages.chronicle_pattern_e.is_profiled",
            return_value=True,
        ), mock.patch(
            "cfb_rankings.team_pages.chronicle_pattern_e.loop_e_continuity",
            return_value=_ok_loop_result("W1 card body."),
        ) as mock_loop:
            result = synthesize_chronicle_card(
                program_slug="alabama",
                week=1,
                db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=ctx_builder,
            )

        _args, kwargs = mock_loop.call_args
        history = kwargs["thread_history"]
        ledger = kwargs["entity_ledger"]
        assert "no prior chronicle cards" in history.lower() or \
               "first observation" in history.lower()
        # Empty observations + no candidate evidence in the empty stub
        # → ledger is the empty sentinel.
        assert "no proper-noun entities" in ledger.lower() or \
               "no prior" in ledger.lower()
        assert result.text == "W1 card body."
        assert result.source == "llm"


# ---------------------------------------------------------------------------
# Chronicle: loop fell back
# ---------------------------------------------------------------------------


class TestChronicleLoopFellBack:

    def test_continuity_rejection_falls_through_to_sync(self, fake_db):
        fb = mock.MagicMock(return_value="SYNC TEMPLATE CARD")
        with mock.patch.dict(
            "cfb_rankings.config.QUALITY_LOOP_FLAGS",
            {CHRONICLE_SURFACE_KEY: LoopPattern.E_CONTINUITY},
            clear=True,
        ), mock.patch(
            "cfb_rankings.team_pages.chronicle_pattern_e.is_profiled",
            return_value=True,
        ), mock.patch(
            "cfb_rankings.team_pages.chronicle_pattern_e.loop_e_continuity",
            return_value=_fell_back_loop_result("wall_clock_timeout_90s"),
        ):
            result = synthesize_chronicle_card(
                program_slug="alabama",
                week=12,
                db=fake_db,
                sqlite_conn=mock.MagicMock(),
                context_builder=mock.MagicMock(
                    return_value=_stub_chronicle_context_with_history()
                ),
                fallback=fb,
            )

        assert result.text == "SYNC TEMPLATE CARD"
        assert result.source == "sync"
        assert result.loop_result is not None
        assert result.loop_result.fell_back is True
        assert result.fallback_reason == "wall_clock_timeout_90s"
        fb.assert_called_once_with("alabama", 12)


# ---------------------------------------------------------------------------
# Chronicle: helpers
# ---------------------------------------------------------------------------


class TestChronicleHelpers:

    def test_format_thread_history_handles_empty(self):
        out = chronicle_format_history([])
        assert (
            "no prior" in out.lower() or "first observation" in out.lower()
        )

    def test_format_thread_history_includes_card_type_and_week(self):
        out = chronicle_format_history(
            _stub_chronicle_context_with_history()["recent_chronicle_headlines"]
        )
        assert "season_arc" in out
        assert "rivalry" in out
        assert "Auburn special-teams gap" in out

    def test_extract_named_entity_ledger_ingests_candidate_evidence(self):
        recent = _stub_chronicle_context_with_history()[
            "recent_chronicle_headlines"
        ]
        candidate = {
            "rivalry": "Auburn week — Pavia revenge angle",
            "player_arc": "Manning sophomore leap",
        }
        out = chronicle_extract_ledger(recent, candidate_evidence=candidate)
        # Manning shows up in both prior headlines AND the candidate
        # blob — top of the ledger.
        assert "Manning" in out
        assert "Auburn" in out
        assert "Pavia" in out
        # Stopwords filtered.
        assert "The (appears" not in out

    def test_is_profiled_returns_true_for_known_slug(self):
        # alabama is one of the 17 profiled slugs per CLAUDE.md.
        assert is_profiled("alabama") is True

    def test_is_profiled_returns_false_for_unknown_slug(self):
        assert is_profiled("not-a-real-slug-zzz") is False


# ===========================================================================
# 3) Config defaults — v5-4 flips landed
# ===========================================================================


class TestConfigDefaults:

    def test_storyline_flag_set_in_default_config(self):
        from cfb_rankings import config
        assert STORYLINE_SURFACE_KEY in config.QUALITY_LOOP_FLAGS
        pattern = config.QUALITY_LOOP_FLAGS[STORYLINE_SURFACE_KEY]
        assert pattern == LoopPattern.E_CONTINUITY or pattern == "E_continuity"

    def test_chronicle_flag_set_in_default_config(self):
        from cfb_rankings import config
        assert CHRONICLE_SURFACE_KEY in config.QUALITY_LOOP_FLAGS
        pattern = config.QUALITY_LOOP_FLAGS[CHRONICLE_SURFACE_KEY]
        assert pattern == LoopPattern.E_CONTINUITY or pattern == "E_continuity"

    def test_storyline_weekly_ceiling_present(self):
        from cfb_rankings import config
        assert STORYLINE_SURFACE_KEY in config.WEEKLY_CEILINGS_CENTS

    def test_chronicle_weekly_ceiling_present(self):
        from cfb_rankings import config
        assert CHRONICLE_SURFACE_KEY in config.WEEKLY_CEILINGS_CENTS

    def test_storyline_surface_constants_unchanged(self):
        assert STORYLINE_SURFACE_KEY == "tier1.storyline_chapter"
        assert STORYLINE_SUBCOMMAND == "quality_loop.E.storyline_chapter"
        assert STORYLINE_MAX_TOKENS == 4096

    def test_chronicle_surface_constants_unchanged(self):
        assert CHRONICLE_SURFACE_KEY == "tier1.chronicle_profiled"
        assert CHRONICLE_SUBCOMMAND == "quality_loop.E.chronicle_profiled"
        assert CHRONICLE_MAX_TOKENS == 2048
