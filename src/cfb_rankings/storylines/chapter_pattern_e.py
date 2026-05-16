"""Storyline thread chapter synthesis — Sprint v5-4 Pattern E flag flip.

Storyline threads carry chapter-to-chapter continuity (named entities,
running arcs, referenced prior beats). Pattern C's three-critic loop is
not enough — a fourth critic (CONTINUITY) needs to see the last three
chapters and a named-entity ledger to catch contradictions and
entity-rename drift across chapters.

This module wraps :func:`cfb_rankings.quality_loop.loop_e_continuity`
behind the surface flag ``QUALITY_LOOP_FLAGS["tier1.storyline_chapter"]``.

Behavior with the flag set to :class:`LoopPattern.E_CONTINUITY`::

    1. :func:`cfb_rankings.prompt_context.builders.build_storyline_chapter_context`
       is called for ``thread_slug`` against the SQLite connection.
    2. The last 3 chapters in the manifest become the THREAD HISTORY
       block fed to both the gen system prompt and the continuity critic.
    3. A named-entity ledger is extracted from the prior chapters' bodies
       — pull-quote sources, byline phrasings, and the chapter titles
       themselves — and fed to the critic so entity-name drift is caught.
    4. The prompt + system prompt + thread_history + entity_ledger are
       handed to :func:`loop_e_continuity` with ``surface="tier1.storyline_chapter"``
       and ``subcommand="quality_loop.E.storyline_chapter"``.
    5. On ``fell_back=True`` or ``text is None``, the synthesizer falls
       through to the existing
       :func:`cfb_rankings.storylines.chapter_authoring.build_prompt` +
       :func:`write_draft_scaffold` sync path.

Behavior with the flag absent::

    The legacy sync authoring path is used end-to-end.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Optional

from cfb_rankings.quality_loop import LoopPattern, loop_e_continuity

if TYPE_CHECKING:  # pragma: no cover — type-only imports
    from cfb_rankings.db import Database
    from cfb_rankings.quality_loop import LoopResult


log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Surface identity — referenced by QUALITY_LOOP_FLAGS + WEEKLY_CEILINGS_CENTS
# ---------------------------------------------------------------------------

#: Surface key used by ``QUALITY_LOOP_FLAGS`` and ``WEEKLY_CEILINGS_CENTS``.
SURFACE_KEY = "tier1.storyline_chapter"

#: Telemetry subcommand label written into ``llm_usage_log``.
SUBCOMMAND = "quality_loop.E.storyline_chapter"

#: Tokens budget. Storyline chapter bodies target 800-1500 words ≈
#: 1200-2200 tokens of output. 4096 leaves headroom for revise-pass
#: guidance and the JSON envelope from the critic panel.
MAX_TOKENS = 4096


# ---------------------------------------------------------------------------
# System prompt — voice register, structural constraints, continuity rules
# ---------------------------------------------------------------------------

STORYLINE_CHAPTER_SYSTEM_PROMPT = """You are the lead essayist for one \
running Storyline Thread on the CFB Index. Each thread is a sequence of \
chapters (800-1500 words each) that tracks one running arc — a coaching \
story, a conference-realignment beat, a rivalry recalibration. The reader \
arrives expecting continuity: every chapter is the next beat in the same \
running argument, not a standalone post.

VOICE
- Sounds like a literate beat writer who has watched the sport for 20 \
  years, never like AI marketing copy.
- The Athletic columnist + Defector mid-range + Solid Verbal in textual \
  form. Warm, fan-positioned, smart-but-knows-the-in-jokes.
- No banned phrases (analytics-cohort, casual-cohort, die-hard-cohort, \
  national-narrative-cohort, n=, effective_n, discourse velocity, signal \
  pipeline, engagement loop, leverage the, delve into, in the realm of, \
  paradigm shift, synergy).

STRUCTURAL CONSTRAINTS
- 800-1500 words of body prose.
- Reference at least one prior chapter explicitly (e.g. "as Chapter 2 \
  noted that …"). The referenced_chapter_ids list must be non-empty if \
  prior chapters exist.
- Cite at least 3 named sources verbatim (beat writers, podcasts, board \
  posts) with real attribution (name, outlet, date).
- One pull-quote-worthy sentence in the middle third.
- Paragraphs separated by blank lines.

CONTINUITY (the Pattern E discipline)
- The THREAD HISTORY block in the system prompt contains the last 3 \
  chapters. Build on them, do not restate.
- The NAMED-ENTITY LEDGER block preserves verbatim phrasings — if a \
  prior chapter calls something "the standard", do not silently \
  rename it "the bar". Match the ledger.
- Advance the running arc: introduce a new beat, do not summarize prior \
  beats. One surprise per chapter.
- Do not contradict factual claims established in prior chapters.

FACTUALITY
- Every numeric value, every date, every score, every named person, \
  every quoted phrase must trace to the SOURCE OBSERVATIONS block in the \
  user prompt (recent wire entries, conversation quotes, observations).
- Mild paraphrase of source language is OK; invention is not.

Output is the chapter BODY ONLY — no headline, no dek, no byline, no \
markdown headers. Plain prose paragraphs separated by blank lines."""


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


def compose_prompt_body(context: dict[str, Any]) -> str:
    """Compose the user-side prompt for a storyline chapter.

    Sections (in order):
        1. THREAD identity (slug, title, dek, status)
        2. NEXT CHAPTER NUMBER
        3. WIRE PER PRIMARY PROGRAM (recent transactions / news 14d)
        4. CONVERSATION QUOTES (beat-writer / podcast / board signal)
        5. SOURCE OBSERVATIONS (broad pool the factuality critic traces)
        6. ARCHIVE THREADS (cross-thread references)
    """
    thread = context.get("thread") or {}
    parts: list[str] = []
    parts.append(
        "SOURCE OBSERVATIONS — every claim in the chapter must trace to "
        "this block."
    )
    parts.append(
        f"THREAD: {thread.get('thread_slug', context.get('thread_slug', '?'))}\n"
        f"TITLE: {thread.get('title', '')}\n"
        f"DEK: {thread.get('dek', '')}\n"
        f"STATUS: {thread.get('status', '')}\n"
        f"VOICE REGISTER SOURCE: {thread.get('voice_register_source', '')}"
    )
    next_n = context.get("next_chapter_number")
    if next_n is None:
        # Derive from prior chapters if not supplied — caller-friendly.
        prior_chs = context.get("last_3_chapters") or []
        if prior_chs:
            try:
                next_n = max(int(c.get("chapter_number") or 0) for c in prior_chs) + 1
            except (TypeError, ValueError):
                next_n = 1
        else:
            next_n = 1
    parts.append(f"NEXT CHAPTER NUMBER: {next_n}")
    parts.append(_format_section(
        "WIRE PER PRIMARY PROGRAM (last 14 days)",
        context.get("wire_per_primary_program"),
    ))
    parts.append(_format_section(
        "CONVERSATION QUOTES (beat / podcast / board, last 14 days)",
        context.get("conversation_quotes"),
    ))
    parts.append(_format_section(
        "SOURCE OBSERVATIONS POOL (broad evidence pool)",
        context.get("source_observations"),
    ))
    parts.append(_format_section(
        "ARCHIVE THREADS (cross-thread references)",
        context.get("archive_threads"),
    ))
    parts.append(
        "TASK: Write the body of the next chapter for this Storyline "
        "Thread. 800-1500 words. Plain prose paragraphs separated by "
        "blank lines. Reference at least one prior chapter from the "
        "THREAD HISTORY block. Cite at least three named sources with "
        "real attribution. Every factual claim must trace to a section "
        "above or to the THREAD HISTORY."
    )
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Thread history + named-entity ledger formatting
# ---------------------------------------------------------------------------


def format_thread_history(prior_chapters: list[dict[str, Any]]) -> str:
    """Format the last-3-chapters list for the THREAD HISTORY block.

    Newest chapter first (matches the builder's ORDER BY DESC). Bodies
    are trimmed to ~200 words each so the block stays cache-friendly
    across thread arcs.
    """
    if not prior_chapters:
        return "(no prior chapters — this is chapter 1)"
    blocks: list[str] = []
    for ch in prior_chapters:
        try:
            n = int(ch.get("chapter_number") or 0)
        except (TypeError, ValueError):
            n = 0
        title = (ch.get("title") or "").strip()
        dek = (ch.get("dek") or "").strip()
        body = (ch.get("body_markdown") or "").strip()
        words = body.split()
        teaser = " ".join(words[:200])
        if len(words) > 200:
            teaser += " […]"
        pq = (ch.get("pull_quote") or "").strip()
        pq_line = f"\nPULL QUOTE: {pq}" if pq else ""
        blocks.append(
            f"--- Chapter {n}: {title} ---\n"
            f"DEK: {dek}\n"
            f"TEASER (first 200 words): {teaser}{pq_line}"
        )
    return "\n\n".join(blocks)


# Cheap proper-noun extractor: any token that starts with an uppercase
# letter and is at least 3 chars. Filters out sentence-initial common
# words via a tiny stoplist. This isn't NLP-grade — it's a signal-grade
# ledger for the continuity critic to anchor entity-name consistency.
_PROPER_NOUN_RE = re.compile(r"\b[A-Z][A-Za-z][A-Za-z0-9'\-]+\b")
_LEDGER_STOPLIST = frozenset({
    "The", "This", "That", "These", "Those", "Their", "There", "They",
    "Then", "Than", "Thus", "When", "Where", "What", "Which", "Who",
    "Why", "How", "After", "Before", "Since", "While", "During", "And",
    "But", "Yet", "For", "Nor", "So", "Because", "If", "Although",
    "However", "Meanwhile", "Today", "Yesterday", "Tomorrow",
    "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
    "Saturday", "Sunday",
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
})


def extract_named_entity_ledger(
    prior_chapters: list[dict[str, Any]], *, max_entries: int = 40,
) -> str:
    """Build a frequency-ranked named-entity ledger from prior chapters.

    Includes the chapter titles + dek + pull quotes + the byline phrasing
    (so chapter renames are caught). The ledger is rendered as a plain-text
    list so the continuity critic can scan for verbatim mismatches.
    """
    if not prior_chapters:
        return "(no prior chapters — ledger is empty)"

    counts: dict[str, int] = {}

    def _ingest(s: str) -> None:
        if not s:
            return
        for tok in _PROPER_NOUN_RE.findall(s):
            if tok in _LEDGER_STOPLIST:
                continue
            counts[tok] = counts.get(tok, 0) + 1

    for ch in prior_chapters:
        _ingest(ch.get("title"))
        _ingest(ch.get("dek"))
        _ingest(ch.get("pull_quote"))
        # Sample the first 600 chars of the body — the highest-density
        # area for named entities. Going deeper is rarely worth the
        # cache pressure on multi-chapter threads.
        body = (ch.get("body_markdown") or "")[:600]
        _ingest(body)
        # Also surface byline phrasings so renames are caught.
        byline = (ch.get("byline") or "")
        _ingest(byline)

    if not counts:
        return "(no proper-noun entities found in prior chapters)"

    # Stable sort: count desc, then alphabetical.
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ranked = ranked[:max_entries]
    lines = [f"  - {name} (appears {n}× in prior chapters)" for name, n in ranked]
    return "Verbatim phrasings to preserve across chapters:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Result envelope
# ---------------------------------------------------------------------------


@dataclass
class StorylineChapterResult:
    """Outcome of one :func:`synthesize_storyline_chapter` call.

    ``text`` is the generated chapter body when ``source == "llm"``; the
    sync-path scaffold (when the legacy authoring code path is used);
    ``None`` only when both paths fail (offline + no scaffold writable).
    """
    text: Optional[str]
    source: str  # "llm" | "sync" | "none"
    thread_slug: str
    chapter_number: int
    loop_result: Optional["LoopResult"] = None
    fallback_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Public entry point
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


def synthesize_storyline_chapter(
    *,
    thread_slug: str,
    chapter_number: int,
    db: "Database",
    sqlite_conn: Optional[sqlite3.Connection] = None,
    context_builder: Optional[Callable[..., dict[str, Any]]] = None,
    fallback: Optional[Callable[[str, int], Optional[str]]] = None,
    _meter: Any = None,
) -> StorylineChapterResult:
    """Generate the next chapter body for ``thread_slug``.

    Dispatch rules:

    * If ``QUALITY_LOOP_FLAGS["tier1.storyline_chapter"]`` is
      :class:`LoopPattern.E_CONTINUITY`, build the context via
      :func:`prompt_context.builders.build_storyline_chapter_context`,
      compose the prompt, format the thread history + entity ledger from
      the last 3 chapters, and route through
      :func:`quality_loop.loop_e_continuity`.

    * If the flag is absent, or the loop falls back (offline-stub,
      wall-clock timeout, Rung-2 critic failures, continuity-rejected),
      call ``fallback(thread_slug, chapter_number)`` for the sync path.

    Parameters
    ----------
    thread_slug:
        Kebab-case thread slug (e.g. ``"vandy-renaissance"``).
    chapter_number:
        Target chapter number. Surfaced into the prompt so the LLM knows
        which arc beat it's writing.
    db:
        :class:`cfb_rankings.db.Database` wrapper. Used to extract the
        underlying ``sqlite3.Connection`` when ``sqlite_conn`` is None.
    sqlite_conn:
        Optional explicit connection for the context builder.
    context_builder:
        Override the context-builder function. Mainly for tests.
    fallback:
        Override the sync-path fallback. Mainly for tests.
    """
    configured = _resolve_flag(SURFACE_KEY)
    fallback_fn = fallback or fallback_to_sync_path

    # Path 1: flag absent → legacy sync path.
    if configured != LoopPattern.E_CONTINUITY:
        sync_text = fallback_fn(thread_slug, chapter_number)
        return StorylineChapterResult(
            text=sync_text,
            source="sync" if sync_text else "none",
            thread_slug=thread_slug,
            chapter_number=chapter_number,
            loop_result=None,
            fallback_reason="flag_absent" if sync_text else "flag_absent_no_sync",
        )

    # Path 2: flag set → LLM path via Pattern E.
    builder = context_builder
    if builder is None:
        from cfb_rankings.prompt_context.builders import (
            build_storyline_chapter_context as _default_builder,
        )
        builder = _default_builder

    conn = sqlite_conn
    if conn is None:
        conn = _connection_for_builder(db)

    context: dict[str, Any] = {"thread_slug": thread_slug}
    if conn is not None:
        try:
            context = builder(thread_slug, conn)
        except Exception as exc:  # pragma: no cover — builder is defensive
            log.warning(
                "storyline_chapter: context builder failed (%s: %s); "
                "routing through loop with empty context",
                type(exc).__name__, exc,
            )
            context = {"thread_slug": thread_slug}

    # Stamp the target chapter number for the prompt body.
    context.setdefault("next_chapter_number", chapter_number)

    prior_chapters = context.get("last_3_chapters") or []
    thread_history = format_thread_history(prior_chapters)
    entity_ledger = extract_named_entity_ledger(prior_chapters)

    prompt_body = compose_prompt_body(context)

    loop_result = loop_e_continuity(
        prompt_body,
        thread_history=thread_history,
        entity_ledger=entity_ledger,
        system=STORYLINE_CHAPTER_SYSTEM_PROMPT,
        critic_context={
            "surface": SURFACE_KEY,
            "source_observations": context.get("source_observations") or [],
        },
        max_tokens=MAX_TOKENS,
        surface=SURFACE_KEY,
        subcommand=SUBCOMMAND,
    )

    if loop_result.fell_back or not loop_result.text:
        sync_text = fallback_fn(thread_slug, chapter_number)
        return StorylineChapterResult(
            text=sync_text,
            source="sync" if sync_text else "none",
            thread_slug=thread_slug,
            chapter_number=chapter_number,
            loop_result=loop_result,
            fallback_reason=loop_result.fallback_reason or "loop_returned_no_text",
        )

    return StorylineChapterResult(
        text=loop_result.text,
        source="llm",
        thread_slug=thread_slug,
        chapter_number=chapter_number,
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


def fallback_to_sync_path(
    thread_slug: str, chapter_number: int
) -> Optional[str]:
    """Default fallback: the legacy chapter authoring path lives in
    :mod:`cfb_rankings.storylines.chapter_authoring`. That module writes
    a draft scaffold to ``seeds/_drafts/`` when no API key is present
    rather than returning a body — so this fallback returns ``None`` and
    the caller drops to its own legacy authoring code path.

    Returns ``None`` so the caller's existing sync rail handles the
    no-LLM case.
    """
    return None


__all__ = [
    "SURFACE_KEY",
    "SUBCOMMAND",
    "MAX_TOKENS",
    "STORYLINE_CHAPTER_SYSTEM_PROMPT",
    "StorylineChapterResult",
    "compose_prompt_body",
    "format_thread_history",
    "extract_named_entity_ledger",
    "synthesize_storyline_chapter",
    "fallback_to_sync_path",
]
