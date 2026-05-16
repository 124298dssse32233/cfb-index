"""Daily edition take synthesis — Sprint v5-3 Pattern C flag flips.

Two surfaces share this module:

* ``tier1.daily_lead``        — the rank-1 lead take (200w; cohort-divergence
  framing; the overnight headline cohorts moved on).
* ``tier1.daily_supporting``  — supporting takes (rank 2-3; 150w each; the
  "second angle" + "buried lede" beats of The Daily).

Both wrappers are *additive* dispatch helpers. The existing
:func:`cfb_rankings.daily.synthesizer.synthesize_takes` and
:func:`cfb_rankings.daily.synthesizer.synthesize_takes_batch` paths stay
on contract — they remain the offline-stub / Rung-2 fall-back rail. When
the relevant ``QUALITY_LOOP_FLAGS`` entry is set to ``LoopPattern.C_CRITIC_REVISE``,
:func:`synthesize_daily_lead` / :func:`synthesize_daily_supporting` route
the per-take generation through :func:`cfb_rankings.quality_loop.loop_c_critic_revise`
with the surface key + subcommand pinned for telemetry.

Behavior with the flag set::

    1. :func:`cfb_rankings.prompt_context.builders.build_daily_lead_context`
       is called for the edition date.
    2. The context dict is folded into a labeled-section prompt body
       (mood Δ 7d, mood same-week-1yr, cohort transitions, cohort
       divergence, archive threads, yesterday's daily headlines, power Δ).
    3. The prompt + system prompt are handed to ``loop_c_critic_revise``
       with ``surface="tier1.daily_lead"`` (or ``tier1.daily_supporting``)
       and the matching ``subcommand`` string.
    4. The :class:`LoopResult` is returned to the caller wrapped in
       :class:`DailyTakeResult`. On ``fell_back=True`` or
       ``text is None``, the caller falls back to the offline-stub
       hard-coded take via :func:`fallback_to_offline_stub`.

Behavior with the flag absent::

    The offline-stub / batch path is preserved end-to-end —
    :func:`synthesize_daily_lead` / :func:`synthesize_daily_supporting`
    short-circuit to ``fallback_to_offline_stub``.

See ``IMPLEMENTATION_PLAN.md`` Part 5 (Sprint v5-3 deliverable) and
``DESIGN_AUDIT_2026_05_15_v5_3.md`` Part 1 row #2/#3.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Callable, Optional

from cfb_rankings.quality_loop import LoopPattern, loop_c_critic_revise

if TYPE_CHECKING:  # pragma: no cover — type-only imports
    from cfb_rankings.db import Database
    from cfb_rankings.quality_loop import LoopResult


log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Surface identity — referenced by QUALITY_LOOP_FLAGS + WEEKLY_CEILINGS_CENTS
# ---------------------------------------------------------------------------

#: Surface key for the rank-1 lead take.
LEAD_SURFACE_KEY = "tier1.daily_lead"

#: Surface key for the rank-2/3 supporting takes.
SUPPORTING_SURFACE_KEY = "tier1.daily_supporting"

#: Telemetry subcommand label for the lead take.
LEAD_SUBCOMMAND = "quality_loop.C.daily_lead"

#: Telemetry subcommand label for supporting takes.
SUPPORTING_SUBCOMMAND = "quality_loop.C.daily_supporting"

#: Tokens budget for daily takes. The lead take is ~200 words = ~300
#: tokens of output. 1024 leaves headroom for revise-pass guidance.
LEAD_MAX_TOKENS = 1024

#: Supporting takes target ~150 words each. 768 covers headroom.
SUPPORTING_MAX_TOKENS = 768


# ---------------------------------------------------------------------------
# System prompts — voice register + structural requirements per surface
# ---------------------------------------------------------------------------

DAILY_LEAD_SYSTEM_PROMPT = """You are writing the rank-1 LEAD take for The \
Daily, college football's 06:00 ET editorial briefing. The lead is the \
single take that anchors today's homepage and drives the cohort-divergence \
framing the rest of the issue picks up.

VOICE
- Sounds like a literate beat writer who reads The Athletic, lurks on the \
  boards, listens to Solid Verbal — never like AI marketing copy.
- No banned phrases (analytics-cohort, casual-cohort, die-hard-cohort, \
  national-narrative-cohort, n=, effective_n, discourse velocity, signal \
  pipeline, engagement loop, leverage the, delve into, in the realm of, \
  paradigm shift, synergy).
- Acknowledge CFB's absurdity where warranted. No false gravitas.

STRUCTURAL CONSTRAINTS
- 200 words (180-220 acceptable).
- Open with the take, not the setup.
- First line is a headline (no label, just the headline text), then blank \
  line, then body.
- Cite at least two named sources verbatim with attribution (beat writers, \
  outlets, podcasts, real attribution).
- End with a forward look — what to watch today or this week.

COHORT-DIVERGENCE FRAMING
- The lead's editorial product is showing how stat folks, regular fans, \
  and the boards are reading the same overnight story differently. The \
  SOURCE OBSERVATIONS block carries mood Δ, cohort transitions, and \
  divergence — use them.

FACTUALITY
- Every numeric value, every score, every date, every named person, \
  every quoted phrase must trace to the SOURCE OBSERVATIONS block in the \
  user prompt. Paraphrase is fine; invention is not.

CONTINUITY
- Read the YESTERDAY'S DAILY HEADLINES block. Don't restate. Build on. \
  If a previous take already framed a question, advance it.

Output format:
  Line 1: headline (no label, just the headline text)
  Line 2: blank
  Line 3+: body (180-220 words, fan-voice, >=2 named source citations)
No markdown headers, no byline."""


DAILY_SUPPORTING_SYSTEM_PROMPT = """You are writing a SUPPORTING take \
(rank 2 or 3) for The Daily, college football's 06:00 ET editorial \
briefing. The supporting takes are the "second angle" + "buried lede" \
beats — what the casual reader will miss without help.

VOICE
- Sounds like a literate beat writer — knowledgeable, warm, slightly \
  contrarian where warranted. Never AI marketing copy.
- No banned phrases (analytics-cohort, casual-cohort, die-hard-cohort, \
  national-narrative-cohort, n=, effective_n, discourse velocity, signal \
  pipeline, engagement loop, leverage the, delve into, in the realm of, \
  paradigm shift, synergy).
- Acknowledge CFB's absurdity where warranted. No false gravitas.

STRUCTURAL CONSTRAINTS
- 150 words (130-170 acceptable).
- Open with the take, not the setup.
- First line is a headline (no label, just the headline text), then blank \
  line, then body.
- Cite at least two named sources verbatim with attribution.
- End with a forward look.

FOCUS BY RANK (rank specified in user prompt)
- Rank 2: a second angle revealing how stat fans and die-hards are reading \
  the same situation differently.
- Rank 3: a buried lede — something quietly important the casual reader \
  will miss without help.

FACTUALITY
- Every numeric value, every score, every date, every named person, \
  every quoted phrase must trace to the SOURCE OBSERVATIONS block in the \
  user prompt. Paraphrase is fine; invention is not.

Output format:
  Line 1: headline (no label, just the headline text)
  Line 2: blank
  Line 3+: body (130-170 words, fan-voice, >=2 named source citations)
No markdown headers, no byline."""


# ---------------------------------------------------------------------------
# Prompt body assembly
# ---------------------------------------------------------------------------


def _format_section(label: str, value: Any) -> str:
    """Render one labeled section. JSON-encodes lists / dicts for the
    factuality critic to trace claims line-by-line."""
    if value is None or value == [] or value == {}:
        return f"{label}:\n(empty — no signal yet for this section)"
    if isinstance(value, (list, dict)):
        try:
            body = json.dumps(value, indent=2, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            body = str(value)
    else:
        body = str(value)
    return f"{label}:\n{body}"


def compose_lead_prompt_body(context: dict[str, Any]) -> str:
    """Compose the prompt body for the rank-1 lead take.

    Sections (in order):
        1. EDITION DATE
        2. HEADLINE ENTITY (yesterday's #1 anchor for mood-delta lookup)
        3. MOOD DELTA 7D (program-level Δ this week vs trailing 4w)
        4. MOOD SAME-WEEK 1YR AGO (year-over-year mood comp)
        5. COHORT TRANSITIONS (per-conference mood dumbbell)
        6. COHORT DIVERGENCE (stat / casual / die-hard split, 4w)
        7. RECENT DAILY HEADLINES (last 14d — don't restate)
        8. POWER DELTA 7D (Brier shift week-over-week)
        9. ARCHIVE THREADS (in-flight storylines to weave)
    """
    iso = context.get("date", "")
    parts: list[str] = []
    parts.append(
        "SOURCE OBSERVATIONS — every claim in the lead take must trace to "
        "this block."
    )
    parts.append(f"EDITION DATE: {iso}")
    parts.append(_format_section(
        "HEADLINE ENTITY (yesterday's rank-1 anchor)",
        {
            "slug": context.get("headline_entity_slug"),
            "team_id": context.get("headline_entity_team_id"),
        },
    ))
    parts.append(_format_section(
        "MOOD DELTA 7D (program-level Δ this week vs trailing 4w)",
        context.get("mood_delta_7d"),
    ))
    parts.append(_format_section(
        "MOOD SAME-WEEK 1YR AGO (year-over-year mood comp)",
        context.get("mood_same_week_1yr_ago"),
    ))
    parts.append(_format_section(
        "COHORT TRANSITIONS (per-conference mood dumbbell)",
        context.get("cohort_transitions"),
    ))
    parts.append(_format_section(
        "COHORT DIVERGENCE (stat / casual / die-hard split, 4w)",
        context.get("cohort_divergence"),
    ))
    parts.append(_format_section(
        "RECENT DAILY HEADLINES (last 14d — do not restate)",
        context.get("recent_daily_headlines"),
    ))
    parts.append(_format_section(
        "POWER DELTA 7D (Brier shift week-over-week)",
        context.get("power_delta_7d"),
    ))
    parts.append(_format_section(
        "ARCHIVE THREADS (in-flight storylines to weave)",
        context.get("archive_threads"),
    ))
    parts.append(
        "TASK: Write the rank-1 LEAD take for this edition. ~200 words "
        "(180-220 acceptable). Plain prose with a headline on line 1, "
        "blank line, body. Every factual claim must trace to a section above."
    )
    return "\n\n".join(parts)


def compose_supporting_prompt_body(
    context: dict[str, Any], rank: int = 2
) -> str:
    """Compose the prompt body for a rank-2/3 supporting take."""
    iso = context.get("date", "")
    focus_map = {
        2: ("a second angle that reveals how stat fans and die-hards are "
            "reading the same overnight situation differently"),
        3: ("a buried lede — something quietly important the casual reader "
            "will miss without help"),
    }
    focus = focus_map.get(int(rank), focus_map[2])
    parts: list[str] = []
    parts.append(
        "SOURCE OBSERVATIONS — every claim in the supporting take must "
        "trace to this block."
    )
    parts.append(f"EDITION DATE: {iso}\nRANK IN EDITION: {rank} of 3\nFOCUS ANGLE: {focus}")
    parts.append(_format_section(
        "HEADLINE ENTITY (yesterday's rank-1 anchor)",
        {
            "slug": context.get("headline_entity_slug"),
            "team_id": context.get("headline_entity_team_id"),
        },
    ))
    parts.append(_format_section(
        "MOOD DELTA 7D",
        context.get("mood_delta_7d"),
    ))
    parts.append(_format_section(
        "COHORT TRANSITIONS",
        context.get("cohort_transitions"),
    ))
    parts.append(_format_section(
        "COHORT DIVERGENCE (stat / casual / die-hard split, 4w)",
        context.get("cohort_divergence"),
    ))
    parts.append(_format_section(
        "RECENT DAILY HEADLINES (last 14d — do not restate)",
        context.get("recent_daily_headlines"),
    ))
    parts.append(_format_section(
        "ARCHIVE THREADS",
        context.get("archive_threads"),
    ))
    parts.append(
        f"TASK: Write the rank-{rank} SUPPORTING take for this edition. "
        "~150 words (130-170 acceptable). Plain prose with a headline on "
        "line 1, blank line, body. Every factual claim must trace to a "
        "section above."
    )
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Result envelope
# ---------------------------------------------------------------------------


@dataclass
class DailyTakeResult:
    """Outcome of one ``synthesize_daily_*`` call."""
    text: Optional[str]
    source: str  # "llm" | "offline" | "none"
    rank: int
    loop_result: Optional["LoopResult"] = None
    fallback_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def _resolve_flag(surface_key: str) -> Optional[LoopPattern]:
    """Resolve a surface flag from QUALITY_LOOP_FLAGS, coercing strings."""
    try:
        from cfb_rankings.config import QUALITY_LOOP_FLAGS
    except Exception:  # pragma: no cover — config import is bullet-proof
        return None
    configured = QUALITY_LOOP_FLAGS.get(surface_key)
    if isinstance(configured, str):
        try:
            configured = LoopPattern(configured)
        except ValueError:
            return None
    return configured


def synthesize_daily_lead(
    *,
    edition_date: str | date,
    db: "Database",
    sqlite_conn: Optional[sqlite3.Connection] = None,
    context_builder: Optional[Callable[..., dict[str, Any]]] = None,
    fallback: Optional[Callable[[str], Optional[str]]] = None,
    _meter: Any = None,
) -> DailyTakeResult:
    """Generate the rank-1 LEAD take for The Daily on ``edition_date``.

    Dispatch rules:

    * If :data:`cfb_rankings.config.QUALITY_LOOP_FLAGS` maps
      :data:`LEAD_SURFACE_KEY` to :class:`LoopPattern.C_CRITIC_REVISE`,
      build the context via
      :func:`cfb_rankings.prompt_context.builders.build_daily_lead_context`,
      compose the prompt body via :func:`compose_lead_prompt_body`, and
      route through :func:`quality_loop.loop_c_critic_revise`.

    * If the flag is absent, or the loop falls back (offline, timeout,
      Rung-2 critic failures), call ``fallback(edition_date)`` for the
      offline-stub take. The default fallback returns ``None`` — call
      sites then use the existing ``synthesizer.synthesize_takes``
      offline-stub generator at rank 1.
    """
    iso = edition_date.isoformat() if hasattr(edition_date, "isoformat") else str(edition_date)
    configured = _resolve_flag(LEAD_SURFACE_KEY)
    fallback_fn = fallback or fallback_to_offline_stub

    # Path 1: flag absent → offline-stub / sync path.
    if configured != LoopPattern.C_CRITIC_REVISE:
        stub_text = fallback_fn(iso)
        return DailyTakeResult(
            text=stub_text,
            source="offline" if stub_text else "none",
            rank=1,
            loop_result=None,
            fallback_reason="flag_absent" if stub_text else "flag_absent_no_stub",
        )

    # Path 2: flag set → LLM path via Pattern C.
    builder = context_builder
    if builder is None:
        from cfb_rankings.prompt_context.builders import (
            build_daily_lead_context as _default_builder,
        )
        builder = _default_builder

    conn = sqlite_conn
    if conn is None:
        conn = _connection_for_builder(db)

    context: dict[str, Any] = {"date": iso}
    if conn is not None:
        try:
            # Builders expect datetime.date; tolerate both forms.
            d = edition_date if hasattr(edition_date, "isoformat") else datetime.fromisoformat(iso).date()
            context = builder(d, conn)
        except Exception as exc:  # pragma: no cover — builder is defensive
            log.warning(
                "daily_lead: context builder failed (%s: %s); routing through "
                "loop with empty context",
                type(exc).__name__, exc,
            )
            context = {"date": iso}

    prompt_body = compose_lead_prompt_body(context)

    loop_result = loop_c_critic_revise(
        prompt_body,
        system=DAILY_LEAD_SYSTEM_PROMPT,
        max_tokens=LEAD_MAX_TOKENS,
        surface=LEAD_SURFACE_KEY,
        subcommand=LEAD_SUBCOMMAND,
    )

    if loop_result.fell_back or not loop_result.text:
        stub_text = fallback_fn(iso)
        return DailyTakeResult(
            text=stub_text,
            source="offline" if stub_text else "none",
            rank=1,
            loop_result=loop_result,
            fallback_reason=loop_result.fallback_reason or "loop_returned_no_text",
        )

    return DailyTakeResult(
        text=loop_result.text,
        source="llm",
        rank=1,
        loop_result=loop_result,
        fallback_reason=None,
    )


def synthesize_daily_supporting(
    *,
    edition_date: str | date,
    rank: int,
    db: "Database",
    sqlite_conn: Optional[sqlite3.Connection] = None,
    context_builder: Optional[Callable[..., dict[str, Any]]] = None,
    fallback: Optional[Callable[[str, int], Optional[str]]] = None,
    _meter: Any = None,
) -> DailyTakeResult:
    """Generate a rank-2 or rank-3 SUPPORTING take for The Daily.

    Same dispatch contract as :func:`synthesize_daily_lead` but pulls the
    surface key :data:`SUPPORTING_SURFACE_KEY` and threads ``rank`` into
    the prompt body so the surface can flip per-rank later if needed.
    """
    if rank not in (2, 3):
        raise ValueError(f"daily_supporting rank must be 2 or 3, got {rank!r}")
    iso = edition_date.isoformat() if hasattr(edition_date, "isoformat") else str(edition_date)
    configured = _resolve_flag(SUPPORTING_SURFACE_KEY)
    fallback_fn = fallback or (lambda d, r: fallback_to_offline_stub(d, rank=r))

    if configured != LoopPattern.C_CRITIC_REVISE:
        stub_text = fallback_fn(iso, rank)
        return DailyTakeResult(
            text=stub_text,
            source="offline" if stub_text else "none",
            rank=rank,
            loop_result=None,
            fallback_reason="flag_absent" if stub_text else "flag_absent_no_stub",
        )

    builder = context_builder
    if builder is None:
        from cfb_rankings.prompt_context.builders import (
            build_daily_lead_context as _default_builder,
        )
        builder = _default_builder

    conn = sqlite_conn
    if conn is None:
        conn = _connection_for_builder(db)

    context: dict[str, Any] = {"date": iso}
    if conn is not None:
        try:
            d = edition_date if hasattr(edition_date, "isoformat") else datetime.fromisoformat(iso).date()
            context = builder(d, conn)
        except Exception as exc:  # pragma: no cover
            log.warning(
                "daily_supporting: context builder failed (%s: %s); empty",
                type(exc).__name__, exc,
            )
            context = {"date": iso}

    prompt_body = compose_supporting_prompt_body(context, rank=rank)

    loop_result = loop_c_critic_revise(
        prompt_body,
        system=DAILY_SUPPORTING_SYSTEM_PROMPT,
        max_tokens=SUPPORTING_MAX_TOKENS,
        surface=SUPPORTING_SURFACE_KEY,
        subcommand=SUPPORTING_SUBCOMMAND,
    )

    if loop_result.fell_back or not loop_result.text:
        stub_text = fallback_fn(iso, rank)
        return DailyTakeResult(
            text=stub_text,
            source="offline" if stub_text else "none",
            rank=rank,
            loop_result=loop_result,
            fallback_reason=loop_result.fallback_reason or "loop_returned_no_text",
        )

    return DailyTakeResult(
        text=loop_result.text,
        source="llm",
        rank=rank,
        loop_result=loop_result,
        fallback_reason=None,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _connection_for_builder(db: "Database") -> Optional[sqlite3.Connection]:
    """Best-effort extraction of an underlying ``sqlite3.Connection``."""
    for attr in ("_raw_conn", "raw_conn", "conn", "_conn", "connection"):
        candidate = getattr(db, attr, None)
        if isinstance(candidate, sqlite3.Connection):
            return candidate
    url = getattr(db, "url", None) or getattr(db, "database_url", None)
    if isinstance(url, str) and url.startswith("sqlite:///"):
        try:
            conn = sqlite3.connect(url.replace("sqlite:///", "", 1))
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error:
            return None
    return None


def fallback_to_offline_stub(
    edition_date: str, rank: int = 1
) -> Optional[str]:
    """Default fallback: borrow an offline stub from
    :mod:`cfb_rankings.daily.synthesizer`.

    Returns the stub text or ``None`` if the synthesizer can't produce
    one (genuine offline / no-bundle case — callers then drop to their
    own seed path).
    """
    try:
        from cfb_rankings.daily.synthesizer import _offline_take
        from cfb_rankings.daily.data import DailyInputBundle
    except ImportError:  # pragma: no cover — daily package always present
        return None

    bundle = DailyInputBundle(edition_date=edition_date)
    try:
        return _offline_take(rank, bundle)
    except Exception:  # pragma: no cover — defensive
        return None


__all__ = [
    "LEAD_SURFACE_KEY",
    "SUPPORTING_SURFACE_KEY",
    "LEAD_SUBCOMMAND",
    "SUPPORTING_SUBCOMMAND",
    "LEAD_MAX_TOKENS",
    "SUPPORTING_MAX_TOKENS",
    "DAILY_LEAD_SYSTEM_PROMPT",
    "DAILY_SUPPORTING_SYSTEM_PROMPT",
    "DailyTakeResult",
    "compose_lead_prompt_body",
    "compose_supporting_prompt_body",
    "synthesize_daily_lead",
    "synthesize_daily_supporting",
    "fallback_to_offline_stub",
]
