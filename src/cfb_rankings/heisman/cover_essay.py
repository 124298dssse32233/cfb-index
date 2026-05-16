"""Heisman weekly narrative synthesis — Sprint v5-3 Pattern C scaffold.

The Heisman surface had **no live LLM narrative path** before Sprint v5-3.
The existing :mod:`cfb_rankings.models.heisman` runner emits structured
ranking data (top-10, market odds, win/finalist/ballot probabilities) but
the weekly narrative that anchors the Heisman section pages has, to date,
been hand-authored or rendered from templates.

This module lands the LLM scaffold + the Pattern C flag-flip dispatch
along the same pattern as :mod:`cfb_rankings.editions.cover_essay` did
for the v5-2 edition cover. The sync fall-back path returns ``None`` so
the caller can render its existing template — this preserves current
behavior.

Behavior with ``QUALITY_LOOP_FLAGS["tier1.heisman_weekly"] = LoopPattern.C_CRITIC_REVISE``:

    1. :func:`cfb_rankings.prompt_context.builders.build_heisman_weekly_context`
       is called for ``(season, week)``.
    2. The context dict is folded into a labeled-section prompt body
       (top-10 board, market odds, vote-history archetype comps,
       last-4-games for top 5, conversation volume).
    3. The prompt + system prompt are handed to ``loop_c_critic_revise``
       with ``surface="tier1.heisman_weekly"`` and
       ``subcommand="quality_loop.C.heisman_weekly"``.
    4. The :class:`LoopResult` is returned wrapped in a
       :class:`HeismanNarrativeResult`. On ``fell_back=True`` or
       ``text is None``, the wrapper returns ``source="none"`` and the
       caller falls through to its existing template / hand-authored
       rendering.

Behavior with the flag absent:

    :func:`synthesize_heisman_weekly` short-circuits to ``source="none"``
    without making any LLM call. The caller renders the existing
    template rail as before.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Optional

from cfb_rankings.quality_loop import LoopPattern, loop_c_critic_revise

if TYPE_CHECKING:  # pragma: no cover — type-only
    from cfb_rankings.db import Database
    from cfb_rankings.quality_loop import LoopResult


log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Surface identity — referenced by QUALITY_LOOP_FLAGS + WEEKLY_CEILINGS_CENTS
# ---------------------------------------------------------------------------

SURFACE_KEY = "tier1.heisman_weekly"
SUBCOMMAND = "quality_loop.C.heisman_weekly"

#: Heisman weekly narrative target = 600-900 words = ~900-1300 tokens of
#: output. 3072 leaves headroom for revise-pass guidance.
MAX_TOKENS = 3072


# ---------------------------------------------------------------------------
# System prompt — voice register, structural requirements, ballot-archetype comps
# ---------------------------------------------------------------------------

HEISMAN_WEEKLY_SYSTEM_PROMPT = """You are the lead essayist for CFB Index's \
weekly Heisman narrative. Your output is the longform piece that anchors \
the Heisman section page every week. It runs 600-900 words. It opens with \
a specific stat or scene from the top candidate's last game, then traces \
the week's Heisman state through ballot-archetype comparables.

VOICE
- Sounds like a literate beat writer who has watched Heisman ballots for \
  20 years, never like AI marketing copy.
- No banned phrases (analytics-cohort, casual-cohort, die-hard-cohort, \
  national-narrative-cohort, n=, effective_n, discourse velocity, signal \
  pipeline, engagement loop, leverage the, delve into, in the realm of, \
  paradigm shift, synergy).
- Concrete stats over abstractions. "His third-down conversion rate jumped \
  to 58% over the last three weeks" beats "his efficiency metrics improved".

STRUCTURAL CONSTRAINTS
- 600-900 words.
- Open with one specific stat, snap, or play from the top candidate's \
  last game (drawn verbatim from the LAST 4 GAMES TOP 5 block).
- Cover the top 5 candidates by ballot/finalist probability — order by \
  the BOARD's overall rank, not by market odds.
- Include at least one BALLOT-ARCHETYPE comparable from the VOTE HISTORY \
  block (e.g. "this run mirrors Burrow 2019" with the comparable's place \
  + first-place votes from the block).
- Cite the market on at least one candidate — actual numeric odds and \
  the provider (e.g. "DraftKings has Manning -130, implying 56% to win").
- Close with one forward-look paragraph: who would move if X happens on \
  the upcoming Saturday slate.

FACTUALITY
- Every numeric value, every player name, every team name, every odds \
  line must trace to the SOURCE OBSERVATIONS block in the user prompt. \
  Paraphrase prose; never invent stats or odds.
- If a candidate appears in the BOARD but not in MARKET ODDS, say so \
  ("the books haven't priced him yet").

Output is the narrative BODY ONLY — no headline, no dek, no byline, no \
markdown headers. Plain prose paragraphs separated by blank lines."""


# ---------------------------------------------------------------------------
# Prompt body assembly
# ---------------------------------------------------------------------------


def _format_section(label: str, value: Any) -> str:
    """Render one labeled section."""
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


def compose_prompt_body(context: dict[str, Any]) -> str:
    """Compose the user-side prompt for the Heisman weekly narrative.

    Sections (in order):
        1. SEASON / WEEK
        2. BOARD TOP 10 (overall rank, latent score, win/finalist/ballot probs)
        3. MARKET ODDS (provider, american/decimal, implied probability)
        4. VOTE HISTORY ARCHETYPE COMPS (place, winner_flag, finalist_flag)
        5. LAST 4 GAMES — TOP 5 (per-candidate game-by-game line)
        6. CONVERSATION VOLUME TOP 5 (per-candidate quotes 7d)
        7. ARCHIVE THREADS (in-flight storyline arcs)
    """
    season = context.get("season", "")
    week = context.get("week", "")
    parts: list[str] = []
    parts.append(
        "SOURCE OBSERVATIONS — every claim in the Heisman narrative must "
        "trace to this block."
    )
    parts.append(f"SEASON: {season}\nWEEK: {week}")
    parts.append(_format_section(
        "BOARD TOP 10 (overall rank, latent score, probabilities)",
        context.get("top_10"),
    ))
    parts.append(_format_section(
        "MARKET ODDS (provider, american/decimal, implied probability)",
        context.get("market_odds"),
    ))
    parts.append(_format_section(
        "VOTE HISTORY ARCHETYPE COMPS (place, winner_flag, finalist_flag)",
        context.get("vote_history_archetype_comps"),
    ))
    parts.append(_format_section(
        "LAST 4 GAMES — TOP 5 (per-candidate game-by-game)",
        context.get("last_4_games_top_5"),
    ))
    parts.append(_format_section(
        "CONVERSATION VOLUME TOP 5 (per-candidate quotes 7d)",
        context.get("conversation_volume_top_5"),
    ))
    parts.append(_format_section(
        "ARCHIVE THREADS (in-flight storyline arcs)",
        context.get("archive_threads"),
    ))
    parts.append(
        "TASK: Write the Heisman weekly narrative body for this week. "
        "600-900 words. Plain prose. No headline / dek / byline / markdown "
        "headers. Cover the top 5 by board rank; cite the market; "
        "include at least one ballot-archetype comparable from the VOTE "
        "HISTORY block; close with a forward look. Every factual claim "
        "must trace to a section above."
    )
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Result envelope
# ---------------------------------------------------------------------------


@dataclass
class HeismanNarrativeResult:
    """Outcome of one :func:`synthesize_heisman_weekly` call.

    ``text`` is the generated narrative body when ``source == "llm"``;
    ``None`` when ``source in ("template", "none")``. The caller renders
    its existing template rail when ``text is None``.
    """
    text: Optional[str]
    source: str  # "llm" | "template" | "none"
    loop_result: Optional["LoopResult"] = None
    fallback_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def synthesize_heisman_weekly(
    *,
    season: int,
    week: int,
    db: "Database",
    sqlite_conn: Optional[sqlite3.Connection] = None,
    context_builder: Optional[Callable[..., dict[str, Any]]] = None,
    fallback: Optional[Callable[[int, int], Optional[str]]] = None,
) -> HeismanNarrativeResult:
    """Generate the Heisman weekly narrative body for ``(season, week)``.

    Dispatch rules:

    * Flag set → build context via
      :func:`prompt_context.builders.build_heisman_weekly_context`,
      compose prompt body, route through
      :func:`quality_loop.loop_c_critic_revise`.

    * Flag absent → return ``source="none"`` so the caller renders the
      existing template rail.
    """
    try:
        from cfb_rankings.config import QUALITY_LOOP_FLAGS
    except Exception:  # pragma: no cover — config import is bullet-proof
        QUALITY_LOOP_FLAGS = {}

    configured = QUALITY_LOOP_FLAGS.get(SURFACE_KEY)
    if isinstance(configured, str):
        try:
            configured = LoopPattern(configured)
        except ValueError:
            configured = None

    fallback_fn = fallback or fallback_to_template

    # Path 1: flag absent → template rail.
    if configured != LoopPattern.C_CRITIC_REVISE:
        template_text = fallback_fn(season, week)
        return HeismanNarrativeResult(
            text=template_text,
            source="template" if template_text else "none",
            loop_result=None,
            fallback_reason="flag_absent" if template_text else "flag_absent_no_template",
        )

    # Path 2: flag set → LLM path via Pattern C.
    builder = context_builder
    if builder is None:
        from cfb_rankings.prompt_context.builders import (
            build_heisman_weekly_context as _default_builder,
        )
        builder = _default_builder

    conn = sqlite_conn
    if conn is None:
        conn = _connection_for_builder(db)

    context: dict[str, Any] = {"season": season, "week": week}
    if conn is not None:
        try:
            context = builder(season, week, conn)
        except Exception as exc:  # pragma: no cover
            log.warning(
                "heisman_weekly: context builder failed (%s: %s); routing "
                "through loop with empty context",
                type(exc).__name__, exc,
            )
            context = {"season": season, "week": week}

    prompt_body = compose_prompt_body(context)

    loop_result = loop_c_critic_revise(
        prompt_body,
        system=HEISMAN_WEEKLY_SYSTEM_PROMPT,
        max_tokens=MAX_TOKENS,
        surface=SURFACE_KEY,
        subcommand=SUBCOMMAND,
    )

    if loop_result.fell_back or not loop_result.text:
        template_text = fallback_fn(season, week)
        return HeismanNarrativeResult(
            text=template_text,
            source="template" if template_text else "none",
            loop_result=loop_result,
            fallback_reason=loop_result.fallback_reason or "loop_returned_no_text",
        )

    return HeismanNarrativeResult(
        text=loop_result.text,
        source="llm",
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


def fallback_to_template(season: int, week: int) -> Optional[str]:
    """Default fallback: there is no committed seed narrative for the
    Heisman weekly surface yet. The renderer's existing template rail
    handles the no-LLM case. Returns ``None`` so the caller knows to
    fall through to its template.
    """
    return None


__all__ = [
    "SURFACE_KEY",
    "SUBCOMMAND",
    "MAX_TOKENS",
    "HEISMAN_WEEKLY_SYSTEM_PROMPT",
    "HeismanNarrativeResult",
    "compose_prompt_body",
    "synthesize_heisman_weekly",
    "fallback_to_template",
]
