"""Edition cover essay synthesis — Sprint v5-2 first quality_loop flag flip.

Production prior to Sprint v5-2 ran exclusively off seed-authored cover
essay bodies in :mod:`cfb_rankings.editions.seeds`. There was no live
LLM-driven cover essay generator. Sprint v5-2 lands the scaffold for the
LLM path, gated on the new :data:`cfb_rankings.config.QUALITY_LOOP_FLAGS`
feature-flag dictionary.

The current flag mapping (set in ``config.py``) is::

    QUALITY_LOOP_FLAGS = {
        "tier1.edition_cover": LoopPattern.C_CRITIC_REVISE,
    }

Behavior with the flag set::

    1. :func:`build_edition_cover_context` is called for ``(season, week)``.
    2. The context dict is folded into a labeled-section prompt body
       (prior 4 covers, cohort dumbbell, rank disagreements, active
       storylines, MAJOR wire 7d, resolved receipts, top chronicle
       moments, season phase).
    3. The prompt + system prompt are handed to
       :func:`cfb_rankings.quality_loop.loop_c_critic_revise` with
       ``surface="tier1.edition_cover"`` and
       ``subcommand="quality_loop.C.edition_cover"``.
    4. The :class:`LoopResult` is returned to the caller. On
       ``fell_back=True`` or ``text is None`` (offline-stub, wall-clock
       timeout, Rung-2 fall-back), the caller falls back to the
       seed-authored cover essay via :func:`fallback_to_seed`.

Behavior with the flag absent (default for surfaces that haven't been
flipped yet)::

    The seed-authored path is used as before. :func:`synthesize_cover_essay`
    short-circuits to :func:`fallback_to_seed`.

Safety nets inherited from Sprint v5-1.5b::

    * $100/mo console.anthropic.com cap with 50/80/95 alerts.
    * CostMeter with $1/call ceiling (commit 0bef7921).
    * Wall-clock timeout 90s in ``_run_critic_loop`` (commit 7970f8dd).
    * Hard iteration cap ``_MAX_REVISES[C] = 1``.
    * Rung-3 weekly ceiling of $10/wk (``WEEKLY_CEILINGS_CENTS``).

The caller (currently :func:`cfb_rankings.editions.cli._cmd_generate_cover`)
is responsible for persisting the generated body to ``edition_features``
via :func:`cfb_rankings.editions.data.upsert_feature` and for stamping
the ``editions.cover_essay_id`` pointer.

Sprint v5-2 is the FIRST surface to flip — see ``IMPLEMENTATION_PLAN.md``
Part 5 and ``DESIGN_AUDIT_2026_05_15_v5_3.md`` Part 1 row #1 + Part 3 +
Part 4. Edition cover is on Pattern C this sprint; v5-8 upgrades it to
Pattern D adversarial after a 4-week A/B against the Pattern C baseline.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Optional

# Import the loop entry point at module load so tests can monkey-patch
# ``cover_essay.loop_c_critic_revise``. The import is cheap and lives
# in the same package — no circularity risk.
from cfb_rankings.quality_loop import LoopPattern, loop_c_critic_revise

if TYPE_CHECKING:  # pragma: no cover — type-only imports
    from cfb_rankings.db import Database
    from cfb_rankings.quality_loop import LoopResult

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Surface identity — referenced by quality_loop + WEEKLY_CEILINGS_CENTS
# ---------------------------------------------------------------------------

#: Surface key used by ``QUALITY_LOOP_FLAGS`` and ``WEEKLY_CEILINGS_CENTS``.
#: Matches the canonical naming convention ``tier{N}.{surface_slug}``.
SURFACE_KEY = "tier1.edition_cover"

#: Telemetry subcommand label written into ``llm_usage_log``.
SUBCOMMAND = "quality_loop.C.edition_cover"

#: Tokens budget for the cover essay body. Cover essays in seeds.py are
#: ~1200-1400 words = ~1800-2100 tokens of output. 4096 leaves headroom
#: for revise-pass guidance and the JSON envelope from the critic panel.
MAX_TOKENS = 4096


# ---------------------------------------------------------------------------
# System prompt — voice register, structural constraints, citation rules
# ---------------------------------------------------------------------------

EDITION_COVER_SYSTEM_PROMPT = """You are the lead essayist for CFB Index's \
weekly Edition cover. Your output is the single longform piece that anchors \
every Saturday morning's homepage. It runs ~900-1300 words. It opens with a \
specific scene or observation, then frames a question the rest of the issue \
answers.

VOICE
- Sounds like a literate beat writer who has watched the sport for 20 \
  years, never like AI marketing copy.
- No banned phrases (analytics-cohort, casual-cohort, die-hard-cohort, \
  national-narrative-cohort, n=, effective_n, discourse velocity, signal \
  pipeline, engagement loop, leverage the, delve into, in the realm of, \
  paradigm shift, synergy).
- Concrete nouns over abstract category words. Verbs of consequence over \
  hedging.

STRUCTURAL CONSTRAINTS
- 900-1300 words.
- One specific scene or detail in the first 100 words.
- At least three concrete facts (named program, score, date, or \
  attribution) drawn verbatim from the SOURCE OBSERVATIONS block in the \
  user prompt.
- One pull-quote-worthy sentence in the middle third.
- Closing paragraph poses or restates the question the issue will answer.

FACTUALITY
- Every numeric value, every score, every date, every named person, \
  every quoted phrase must trace to the SOURCE OBSERVATIONS block in the \
  user prompt. Paraphrase is fine; invention is not.
- If a fact would require information that isn't in the source block, \
  write around it.

CALENDAR AWARENESS (read this carefully — wrong-season drift breaks the \
issue)
- A CALENDAR CONTEXT block in the user prompt tells you the actual publish \
  date and whether the sport is in-season or offseason. RESPECT IT.
- The "WEEK" number is the ISO calendar week of the publish date — not a \
  football week. ISO week 18 is the first Monday of May. Football week 18 \
  is championship/CFP week. They are NOT the same.
- If CALENDAR CONTEXT says OFFSEASON: no games are being played this \
  week, no press boxes are full, no current quotes from coaches exist, no \
  Saturday slate is happening. Do not write a regular-season recap or a \
  championship-week scene-setter. The offseason has its own subjects: \
  portal closures, recruiting cycles, coaching changes, the absence of \
  forced news cycles, what fanbases choose to talk about when there is \
  nothing to talk about. The SOURCE OBSERVATIONS block is your factual \
  ground; if it is sparse, write about the offseason rhythm itself, not \
  about invented mid-season scenes.
- If CALENDAR CONTEXT says IN-SEASON: write the regular-season piece. The \
  ISO week and football week roughly align in fall; the distinction \
  matters most in spring.

CONTINUITY
- Read the PRIOR 4 COVERS block. Don't restate. Build on. If a previous \
  cover already framed a question, advance it.

Output is the cover essay BODY ONLY — no headline, no dek, no byline, \
no markdown headers. Plain prose paragraphs separated by blank lines."""


# ---------------------------------------------------------------------------
# Prompt body assembly — folds the context dict into labeled sections
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


def compose_prompt_body(context: dict[str, Any]) -> str:
    """Compose the user-side prompt from the context dict.

    The labeled-section format is what the FACTUALITY critic traces
    against. Each section becomes a paragraph the essayist can lean on
    and the critic can audit.

    Sections (in order):
        1. SEASON / WEEK
        2. SEASON PHASE
        3. PRIOR 4 COVERS (continuity — don't restate)
        4. COHORT MOOD DUMBBELL (per-conference Δ this week vs trailing 4w)
        5. RANK DISAGREEMENTS (BT vs SP+ vs FPI top-25 gaps)
        6. ACTIVE STORYLINES (in-flight threads to weave)
        7. MAJOR WIRE 7D (top transactions/news + pre-authored why-it-matters)
        8. RESOLVED RECEIPTS (this week's high-surprise calls to re-cite)
        9. TOP CHRONICLE MOMENTS (verbatim observations from the 17 profiled)

    Any missing/empty section renders as "(empty — no signal yet…)" so
    the essayist knows to skip the corresponding paragraph rather than
    invent one.
    """
    season = context.get("season", "")
    week = context.get("week", "")
    parts: list[str] = []
    parts.append("SOURCE OBSERVATIONS — every claim in the cover essay must trace to this block.")
    parts.append(f"SEASON: {season}\nWEEK (ISO calendar week of publish date): {week}")

    # CALENDAR CONTEXT — Session 6 fix for wrong-season Pattern C drift.
    # Before this block existed, the LLM saw only "WEEK: 18" and
    # interpreted it as football week 18 (mid-November championship
    # week) rather than ISO calendar week 18 (first Monday of May).
    # The live W18 cover essay shipped 1,100 words set in mid-November
    # on a May 4 publish date. This block tells the LLM the actual
    # calendar position so it can ground its scene-setting correctly.
    publish_date = context.get("publish_date")
    is_offseason = context.get("is_offseason")
    days_to_kickoff = context.get("days_to_kickoff")
    if publish_date is not None:
        phase = "OFFSEASON" if is_offseason else "IN-SEASON"
        kickoff_line = (
            f"DAYS TO NEXT KICKOFF: {days_to_kickoff}"
            if days_to_kickoff is not None else ""
        )
        offseason_note = (
            "This is an OFFSEASON edition. No games are being played this week. "
            "No press boxes are full. No current coach quotes exist. "
            "Do NOT write a regular-season recap or a championship-week "
            "scene-setter. Offseason subjects: portal closures, recruiting, "
            "coaching changes, the absence of forced news cycles. If "
            "SOURCE OBSERVATIONS is sparse, write about the offseason "
            "rhythm itself."
        ) if is_offseason else (
            "This is an IN-SEASON edition. Games are happening. Write the "
            "regular-season piece."
        )
        parts.append(
            "CALENDAR CONTEXT:\n"
            f"PUBLISH DATE: {publish_date}\n"
            f"SEASON PHASE: {phase}\n"
            f"{kickoff_line}\n"
            f"{offseason_note}".rstrip()
        )

    parts.append(_format_section("SEASON PHASE", context.get("season_phase")))
    parts.append(_format_section(
        "PRIOR 4 COVERS (continuity context — do not restate)",
        context.get("prior_4_covers"),
    ))
    parts.append(_format_section(
        "COHORT MOOD DUMBBELL (per-conference Δ this week vs trailing 4w)",
        context.get("cohort_mood_dumbbell"),
    ))
    parts.append(_format_section(
        "RANK DISAGREEMENTS (BT vs SP+ vs FPI top-25 gaps)",
        context.get("rank_disagreements"),
    ))
    parts.append(_format_section(
        "ACTIVE STORYLINES (in-flight threads to weave)",
        context.get("active_storylines"),
    ))
    parts.append(_format_section(
        "MAJOR WIRE 7D (transactions/news + why-it-matters)",
        context.get("major_wire_7d"),
    ))
    parts.append(_format_section(
        "RESOLVED RECEIPTS (this week's high-surprise calls to re-cite)",
        context.get("resolved_receipts"),
    ))
    parts.append(_format_section(
        "TOP CHRONICLE MOMENTS (verbatim observations from profiled programs)",
        context.get("top_chronicle_moments"),
    ))
    parts.append(
        "TASK: Write the cover essay body for this edition. 900-1300 words. "
        "Plain prose. No headline / dek / byline / markdown headers. Every "
        "factual claim must trace to a section above."
    )
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Result envelope
# ---------------------------------------------------------------------------


@dataclass
class CoverEssayResult:
    """Outcome of one :func:`synthesize_cover_essay` call.

    ``text`` is the generated essay body when ``source == "llm"``; the
    seed body when ``source == "seed"``; ``None`` only when both paths
    fail (offline + no seed for the slug).
    """
    text: Optional[str]
    source: str  # "llm" | "seed" | "none"
    loop_result: Optional["LoopResult"] = None
    fallback_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def synthesize_cover_essay(
    *,
    season: int,
    week: int,
    edition_slug: str,
    db: "Database",
    sqlite_conn: Optional[sqlite3.Connection] = None,
    context_builder: Optional[Callable[..., dict[str, Any]]] = None,
    fallback: Optional[Callable[[str], Optional[str]]] = None,
) -> CoverEssayResult:
    """Generate the Edition cover essay body for ``(season, week)``.

    Dispatch rules:

    * If :data:`cfb_rankings.config.QUALITY_LOOP_FLAGS` maps
      ``SURFACE_KEY`` to :class:`LoopPattern.C_CRITIC_REVISE`, build the
      context dict via :func:`prompt_context.builders.build_edition_cover_context`,
      compose the prompt body via :func:`compose_prompt_body`, and route
      through :func:`quality_loop.loop_c_critic_revise`.

    * If the flag is absent, or the loop falls back (offline, wall-clock
      timeout, Rung-2 critic failures), call ``fallback(edition_slug)``
      to retrieve the seed-authored body.

    Parameters
    ----------
    season, week:
        Identify the edition for context lookups. Forwarded to
        :func:`prompt_context.builders.build_edition_cover_context`.
    edition_slug:
        Edition slug (e.g. ``"2026-w17"``). Passed to ``fallback`` for
        the seed-path lookup. Not used by the LLM path.
    db:
        :class:`cfb_rankings.db.Database` instance. Used to obtain the
        underlying ``sqlite3.Connection`` for the context builder when
        ``sqlite_conn`` is not provided.
    sqlite_conn:
        Optional explicit ``sqlite3.Connection`` for the context
        builder. If not provided, derived from ``db``.
    context_builder:
        Override the context-builder function. Defaults to
        :func:`prompt_context.builders.build_edition_cover_context`.
        Mainly for testing.
    fallback:
        Override the seed-lookup function. Defaults to
        :func:`fallback_to_seed`. Mainly for testing.
    """
    # Resolve the flag.
    try:
        from cfb_rankings.config import QUALITY_LOOP_FLAGS
    except Exception:  # pragma: no cover — config import is bullet-proof
        QUALITY_LOOP_FLAGS = {}

    configured = QUALITY_LOOP_FLAGS.get(SURFACE_KEY)
    if isinstance(configured, str):  # tolerate raw-string flag values
        try:
            configured = LoopPattern(configured)
        except ValueError:
            configured = None

    fallback_fn = fallback or fallback_to_seed

    # Path 1: flag absent → seed-authored body.
    if configured != LoopPattern.C_CRITIC_REVISE:
        seed_text = fallback_fn(edition_slug)
        return CoverEssayResult(
            text=seed_text,
            source="seed" if seed_text else "none",
            loop_result=None,
            fallback_reason="flag_absent" if seed_text else "flag_absent_no_seed",
        )

    # Path 2: flag set → LLM path via Pattern C.
    builder = context_builder
    if builder is None:
        from cfb_rankings.prompt_context.builders import (
            build_edition_cover_context as _default_builder,
        )
        builder = _default_builder

    # Acquire a sqlite3.Connection for the builder. ``Database`` wraps
    # SQLAlchemy / sqlite3 depending on URL — surface the raw connection
    # if available, otherwise leave the builder to no-op on the empty
    # path (it catches sqlite3.Error and returns []).
    conn = sqlite_conn
    if conn is None:
        conn = _connection_for_builder(db)

    context: dict[str, Any] = {}
    if conn is not None:
        try:
            context = builder(season, week, conn)
        except Exception as exc:  # pragma: no cover — builder is defensive
            log.warning(
                "edition_cover: context builder failed (%s: %s); routing through "
                "loop with empty context",
                type(exc).__name__, exc,
            )
            context = {"season": season, "week": week}
    else:
        context = {"season": season, "week": week}

    prompt_body = compose_prompt_body(context)

    loop_result = loop_c_critic_revise(
        prompt_body,
        system=EDITION_COVER_SYSTEM_PROMPT,
        max_tokens=MAX_TOKENS,
        surface=SURFACE_KEY,
        subcommand=SUBCOMMAND,
    )

    # Graceful degradation: any fall-back from the loop means we fall
    # through to the seed path. The caller never sees a None body unless
    # both the loop AND the seed lookup fail.
    if loop_result.fell_back or not loop_result.text:
        seed_text = fallback_fn(edition_slug)
        return CoverEssayResult(
            text=seed_text,
            source="seed" if seed_text else "none",
            loop_result=loop_result,
            fallback_reason=loop_result.fallback_reason or "loop_returned_no_text",
        )

    return CoverEssayResult(
        text=loop_result.text,
        source="llm",
        loop_result=loop_result,
        fallback_reason=None,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _connection_for_builder(db: "Database") -> Optional[sqlite3.Connection]:
    """Best-effort extraction of an underlying ``sqlite3.Connection`` from
    the :class:`Database` wrapper. Returns ``None`` if the wrapper is
    not SQLite-backed (the context builders run only on SQLite)."""
    for attr in ("_raw_conn", "raw_conn", "conn", "_conn", "connection"):
        candidate = getattr(db, attr, None)
        if isinstance(candidate, sqlite3.Connection):
            return candidate
    # Fall back to a fresh connection on the database file when the URL
    # is a sqlite:// path. The builders only need read access.
    url = getattr(db, "url", None) or getattr(db, "database_url", None)
    if isinstance(url, str) and url.startswith("sqlite:///"):
        try:
            conn = sqlite3.connect(url.replace("sqlite:///", "", 1))
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error:
            return None
    return None


def fallback_to_seed(edition_slug: str) -> Optional[str]:
    """Default fallback: pull the cover essay body from
    :mod:`cfb_rankings.editions.seeds` if a seed payload exists.

    Returns the seed body or ``None`` if no seed exists for the slug
    (genuine offseason / not-yet-authored editions).
    """
    try:
        from cfb_rankings.editions.seeds import (
            _archive_edition_payload,
            _w17_payload,
        )
    except ImportError:  # pragma: no cover — seeds module always present
        return None

    try:
        if edition_slug == "2026-w17":
            _, features, _ = _w17_payload()
        else:
            _, features, _ = _archive_edition_payload(edition_slug)
    except KeyError:
        return None

    for f in features:
        if f.feature_order == 1 and f.feature_kind == "cover_essay":
            return f.body_markdown
    return None


__all__ = [
    "SURFACE_KEY",
    "SUBCOMMAND",
    "MAX_TOKENS",
    "EDITION_COVER_SYSTEM_PROMPT",
    "CoverEssayResult",
    "compose_prompt_body",
    "synthesize_cover_essay",
    "fallback_to_seed",
]
