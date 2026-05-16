"""Chronicle card synthesis for profiled programs — Sprint v5-4 Pattern E.

The 17 profiled programs (``PROFILED_SLUGS`` from
:mod:`cfb_rankings.team_pages.profile_loader`) get the world-class
chronicle treatment: their cards form a multi-week running record where
"since/first time since" comparative markers, voice-register continuity
with prior weeks, and player-archetype peer comparisons all matter.

Pattern E adds, over Pattern C's three-critic loop:

    * Pre-pass loads recent chronicle observations (the last ~5
      headlines for the same program) → THREAD HISTORY block.
    * A named-entity ledger extracted from those prior observations →
      preserved verbatim across cards.
    * The CONTINUITY critic catches contradictions and rename drift.

Unprofiled programs (~662 slugs) stay on the existing template path —
the Pattern E machinery never fires for them.

Behavior with ``QUALITY_LOOP_FLAGS["tier1.chronicle_profiled"] = LoopPattern.E_CONTINUITY``:

    1. The caller checks ``program_slug in PROFILED_SLUGS``. If not
       profiled, this module's :func:`synthesize_chronicle_card`
       short-circuits to ``source="sync"`` (flag treated as unset).
    2. :func:`cfb_rankings.prompt_context.builders.build_chronicle_context`
       is called for the ``(program_slug, week)`` pair.
    3. The context's ``recent_chronicle_headlines`` becomes the THREAD
       HISTORY block.
    4. An entity ledger is extracted from the recent headlines and the
       caller-supplied ``candidate_observations_evidence`` blob (the
       Stage-1 multi-stream scan output the chronicle_generator builds).
    5. The prompt + system prompt + thread_history + entity_ledger are
       handed to :func:`loop_e_continuity` with the surface key + the
       telemetry subcommand pinned.
    6. On ``fell_back=True`` or ``text is None``, the synthesizer falls
       through to the legacy
       :func:`cfb_rankings.team_pages.chronicle_generator.generate_chronicle_for_team`
       sync path.

Behavior with the flag absent OR with an unprofiled slug::

    The legacy ``chronicle_generator.generate_chronicle_for_team`` path
    runs end-to-end.
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
SURFACE_KEY = "tier1.chronicle_profiled"

#: Telemetry subcommand label written into ``llm_usage_log``.
SUBCOMMAND = "quality_loop.E.chronicle_profiled"

#: Tokens budget. Chronicle cards target 120-220 words of body markdown ≈
#: 200-400 tokens of output. 2048 leaves headroom for revise-pass
#: guidance and the JSON envelope from the critic panel.
MAX_TOKENS = 2048


# ---------------------------------------------------------------------------
# System prompt — voice register, comparative-marker discipline, archetype peer comp
# ---------------------------------------------------------------------------

CHRONICLE_PROFILED_SYSTEM_PROMPT = """You are writing one CHRONICLE CARD \
for a profiled program on the CFB Index. The card is a 120-220 word \
observation about something specific that happened this week — a tempo \
shift, a coaching tendency, a quiet recruiting move, an archive echo. \
The reader has been following this program's chronicle for weeks; every \
card stands on its own but reads as the next entry in a running record.

VOICE REGISTER (v4 §2.7 — non-negotiable)
- Beat-Writer Test: would a sharp independent CFB blogger write this?
- Name names every paragraph: coaches, players, dates, plays, board \
  users, podcasters.
- Editorial prose: short sentences, concrete nouns, active voice.
- Warm, fan-positioned, smart-but-knows-the-in-jokes. The Athletic \
  columnist + Defector mid-range + Solid Verbal in textual form.
- No banned phrases (analytics-cohort, casual-cohort, die-hard-cohort, \
  cohort divergence, cohort split, n=, effective_n, discourse velocity, \
  signal pipeline, engagement loop, leverage the, delve into, in the \
  realm of, paradigm shift, synergy, methodology, hot take).

COMPARATIVE-MARKER REQUIREMENT
- Every card includes at least one "since/first time since/last time \
  X happened was Y" comparative marker. The POWER RATINGS SPARKLINE 6Y \
  block carries the rank history; pick the most recent year that \
  matches the current observation and cite it.

PLAYER-ARCHETYPE PEER COMPARISON
- If the card's stat or scene involves a single player, include one \
  archetype-peer comparison from the PLAYER ARCHETYPE PEERS block when \
  it is non-empty. ("This run mirrors X's 2021 over the same stretch.")
- If the PEERS block is empty, skip the comparison — do not invent.

STRUCTURAL CONSTRAINTS
- 120-220 words of body markdown.
- Open with a concrete noun + verb of consequence. No setup paragraphs.
- One named source citation with real attribution (beat writer + \
  outlet + date, or podcast + episode + date, or board username + \
  thread description).
- Close with a sentence that links forward — what to watch this week \
  or next.

CONTINUITY (the Pattern E discipline)
- The THREAD HISTORY block carries the last ~5 chronicle cards for this \
  program. Build on them, do not restate. If a prior card already \
  flagged "the offensive line shuffle", do not flag it again — name \
  what's new this week.
- The NAMED-ENTITY LEDGER preserves verbatim phrasings. If prior cards \
  call something "the bench surge", do not silently rename it "the \
  rotation surge". Match the ledger.

FACTUALITY
- Every stat, every date, every score, every named person, every quoted \
  phrase must trace to the SOURCE OBSERVATIONS block in the user prompt.
- Mild paraphrase of source language is OK; invention is not.

Output is the card BODY ONLY — no headline (callers supply it), no \
markdown headers, no byline. Plain prose paragraphs separated by blank \
lines."""


# ---------------------------------------------------------------------------
# Prompt body assembly
# ---------------------------------------------------------------------------


def _format_section(label: str, value: Any) -> str:
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


def compose_prompt_body(
    context: dict[str, Any], *, program_slug: str, week: int | None = None,
) -> str:
    """Compose the user-side prompt for one chronicle card.

    Sections (in order):
        1. PROGRAM + WEEK identity
        2. CANDIDATE OBSERVATIONS EVIDENCE (the Stage-1 multi-stream scan)
        3. FANBASE CLASSIFICATION HISTORY (6-year archetype lineage)
        4. POWER RATINGS SPARKLINE 6Y (for "since X" comparative markers)
        5. PLAYER ARCHETYPE PEERS (peer-archetype comparisons)
    """
    parts: list[str] = []
    parts.append(
        "SOURCE OBSERVATIONS — every claim in the card must trace to "
        "this block."
    )
    parts.append(
        f"PROGRAM SLUG: {program_slug}\n"
        f"WEEK: {week if week is not None else context.get('week', '?')}"
    )
    parts.append(_format_section(
        "CANDIDATE OBSERVATIONS EVIDENCE (Stage-1 multi-stream scan)",
        context.get("candidate_observations_evidence"),
    ))
    parts.append(_format_section(
        "FANBASE CLASSIFICATION HISTORY (6-year archetype lineage)",
        context.get("fanbase_classification_history"),
    ))
    parts.append(_format_section(
        "POWER RATINGS SPARKLINE 6Y (for 'since X' comparative markers)",
        context.get("power_ratings_sparkline_6y"),
    ))
    parts.append(_format_section(
        "PLAYER ARCHETYPE PEERS (peer-archetype comparisons)",
        context.get("player_archetype_peers"),
    ))
    parts.append(
        "TASK: Write one chronicle card body for this program/week. "
        "120-220 words. Plain prose paragraphs separated by blank lines. "
        "Include at least one 'since/first time since' comparative marker "
        "anchored in the SPARKLINE block. One named source citation. "
        "Every factual claim must trace to a section above or to the "
        "THREAD HISTORY."
    )
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Thread history + named-entity ledger formatting
# ---------------------------------------------------------------------------


def format_thread_history(recent_observations: list[dict[str, Any]]) -> str:
    """Format the last-N recent chronicle observations for this program.

    Newest first (matches the builder's ORDER BY season_year DESC, week
    DESC). Each entry surfaces the card_type + headline + week +
    source_attribution + surprise_score so the critic can detect when a
    candidate restates a prior beat instead of advancing.
    """
    if not recent_observations:
        return "(no prior chronicle cards — this is the first observation)"
    blocks: list[str] = []
    # Cap at 5 — the prompt size shouldn't explode if the builder
    # returns 40 rows.
    for obs in recent_observations[:5]:
        ct = obs.get("card_type") or "?"
        wk = obs.get("week")
        sy = obs.get("season_year")
        headline = (obs.get("headline") or "").strip()
        src = (obs.get("source_attribution") or "").strip()
        surprise = obs.get("surprise_score")
        bits = [f"[{ct}]"]
        if sy is not None or wk is not None:
            bits.append(f"S{sy} W{wk}")
        if surprise is not None:
            try:
                bits.append(f"surprise={float(surprise):.2f}")
            except (TypeError, ValueError):
                pass
        meta = " ".join(bits)
        attribution = f"\nSOURCE: {src}" if src else ""
        blocks.append(
            f"{meta}\n"
            f"HEADLINE: {headline}{attribution}"
        )
    return "\n\n".join(blocks)


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
    recent_observations: list[dict[str, Any]],
    *,
    candidate_evidence: Any = None,
    max_entries: int = 30,
) -> str:
    """Build a frequency-ranked named-entity ledger from recent cards.

    Uses the headline + source_attribution of each prior observation
    plus an optional candidate-evidence blob (the Stage-1 multi-stream
    scan output that often carries player + coach names verbatim).
    """
    counts: dict[str, int] = {}

    def _ingest(s: Any) -> None:
        if not s:
            return
        text = s if isinstance(s, str) else str(s)
        for tok in _PROPER_NOUN_RE.findall(text):
            if tok in _LEDGER_STOPLIST:
                continue
            counts[tok] = counts.get(tok, 0) + 1

    for obs in (recent_observations or []):
        _ingest(obs.get("headline"))
        _ingest(obs.get("source_attribution"))

    # The Stage-1 candidate evidence often carries the freshest entity
    # names (player who just transferred, coach who just hired). Ingest
    # whatever shape it arrives in.
    if candidate_evidence is not None:
        if isinstance(candidate_evidence, (list, tuple, set)):
            for item in candidate_evidence:
                _ingest(item)
        elif isinstance(candidate_evidence, dict):
            for v in candidate_evidence.values():
                _ingest(v)
        else:
            _ingest(candidate_evidence)

    if not counts:
        return "(no proper-noun entities found in prior cards)"
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ranked = ranked[:max_entries]
    lines = [f"  - {name} (appears {n}× in prior cards)" for name, n in ranked]
    return "Verbatim phrasings to preserve across cards:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Profiled-program gating
# ---------------------------------------------------------------------------


def is_profiled(program_slug: str) -> bool:
    """Return True iff ``program_slug`` is one of the 17 profiled slugs.

    Pattern E only fires for profiled programs — unprofiled slugs stay
    on the legacy template path even when the flag is set.
    """
    try:
        from cfb_rankings.team_pages.profile_loader import PROFILED_SLUGS
    except Exception:  # pragma: no cover — profile_loader import is bullet-proof
        return False
    return program_slug in PROFILED_SLUGS


# ---------------------------------------------------------------------------
# Result envelope
# ---------------------------------------------------------------------------


@dataclass
class ChronicleCardResult:
    """Outcome of one :func:`synthesize_chronicle_card` call."""
    text: Optional[str]
    source: str  # "llm" | "sync" | "none"
    program_slug: str
    week: Optional[int]
    loop_result: Optional["LoopResult"] = None
    fallback_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _resolve_flag(surface_key: str) -> Optional[LoopPattern]:
    try:
        from cfb_rankings.config import QUALITY_LOOP_FLAGS
    except Exception:  # pragma: no cover
        return None
    configured = QUALITY_LOOP_FLAGS.get(surface_key)
    if isinstance(configured, str):
        try:
            configured = LoopPattern(configured)
        except ValueError:
            return None
    return configured


def synthesize_chronicle_card(
    *,
    program_slug: str,
    week: int,
    db: "Database",
    candidate_evidence: Any = None,
    sqlite_conn: Optional[sqlite3.Connection] = None,
    context_builder: Optional[Callable[..., dict[str, Any]]] = None,
    fallback: Optional[Callable[[str, int], Optional[str]]] = None,
    _meter: Any = None,
) -> ChronicleCardResult:
    """Generate one chronicle card body for ``(program_slug, week)``.

    Dispatch rules:

    * If ``program_slug`` is NOT in :data:`PROFILED_SLUGS`, the flag is
      treated as unset — short-circuits to the sync path. Only the 17
      profiled programs get the Pattern E treatment.

    * If ``QUALITY_LOOP_FLAGS["tier1.chronicle_profiled"]`` is
      :class:`LoopPattern.E_CONTINUITY` AND the slug is profiled, build
      context, format thread history + ledger, and route through
      :func:`loop_e_continuity`.

    * On loop fall-back or empty text, drop to the sync path.

    Parameters
    ----------
    program_slug:
        Program slug (kebab case, e.g. ``"alabama"``).
    week:
        Target week number. Stamped into the prompt.
    db:
        Database wrapper. Used to extract the underlying
        ``sqlite3.Connection``.
    candidate_evidence:
        Optional Stage-1 multi-stream scan output (the dict-of-streams
        the legacy chronicle_generator produces). Fed into both the
        prompt body and the entity-ledger extractor.
    sqlite_conn:
        Optional explicit connection for the context builder.
    context_builder:
        Override the context builder. Mainly for tests.
    fallback:
        Override the sync-path fallback. Mainly for tests.
    """
    # Pre-flight: only profiled slugs use Pattern E.
    if not is_profiled(program_slug):
        fallback_fn = fallback or fallback_to_sync_path
        sync_text = fallback_fn(program_slug, week)
        return ChronicleCardResult(
            text=sync_text,
            source="sync" if sync_text else "none",
            program_slug=program_slug,
            week=week,
            loop_result=None,
            fallback_reason=(
                "unprofiled_slug" if sync_text else "unprofiled_slug_no_sync"
            ),
        )

    configured = _resolve_flag(SURFACE_KEY)
    fallback_fn = fallback or fallback_to_sync_path

    # Path 1: flag absent → sync path.
    if configured != LoopPattern.E_CONTINUITY:
        sync_text = fallback_fn(program_slug, week)
        return ChronicleCardResult(
            text=sync_text,
            source="sync" if sync_text else "none",
            program_slug=program_slug,
            week=week,
            loop_result=None,
            fallback_reason="flag_absent" if sync_text else "flag_absent_no_sync",
        )

    # Path 2: flag set + profiled → LLM path via Pattern E.
    builder = context_builder
    if builder is None:
        from cfb_rankings.prompt_context.builders import (
            build_chronicle_context as _default_builder,
        )
        builder = _default_builder

    conn = sqlite_conn
    if conn is None:
        conn = _connection_for_builder(db)

    context: dict[str, Any] = {"program_slug": program_slug, "week": week}
    if conn is not None:
        try:
            context = builder(program_slug, week, conn)
        except Exception as exc:  # pragma: no cover — builder is defensive
            log.warning(
                "chronicle_profiled: context builder failed (%s: %s); "
                "routing through loop with empty context",
                type(exc).__name__, exc,
            )
            context = {"program_slug": program_slug, "week": week}

    # Stamp the caller-supplied candidate evidence into the context so
    # both the prompt body and the entity ledger see it.
    if candidate_evidence is not None:
        context["candidate_observations_evidence"] = candidate_evidence

    recent_obs = context.get("recent_chronicle_headlines") or []
    thread_history = format_thread_history(recent_obs)
    entity_ledger = extract_named_entity_ledger(
        recent_obs, candidate_evidence=context.get("candidate_observations_evidence")
    )

    prompt_body = compose_prompt_body(context, program_slug=program_slug, week=week)

    # Provide the source observations for the factuality critic. The
    # chronicle context's candidate_observations_evidence + recent
    # headlines + sparkline are the traceable claim sources.
    factuality_source_block = {
        "candidate_observations_evidence": context.get("candidate_observations_evidence"),
        "recent_chronicle_headlines": recent_obs,
        "power_ratings_sparkline_6y": context.get("power_ratings_sparkline_6y"),
        "fanbase_classification_history": context.get("fanbase_classification_history"),
    }

    loop_result = loop_e_continuity(
        prompt_body,
        thread_history=thread_history,
        entity_ledger=entity_ledger,
        system=CHRONICLE_PROFILED_SYSTEM_PROMPT,
        critic_context={
            "surface": SURFACE_KEY,
            "source_observations": factuality_source_block,
        },
        max_tokens=MAX_TOKENS,
        surface=SURFACE_KEY,
        subcommand=SUBCOMMAND,
    )

    if loop_result.fell_back or not loop_result.text:
        sync_text = fallback_fn(program_slug, week)
        return ChronicleCardResult(
            text=sync_text,
            source="sync" if sync_text else "none",
            program_slug=program_slug,
            week=week,
            loop_result=loop_result,
            fallback_reason=loop_result.fallback_reason or "loop_returned_no_text",
        )

    return ChronicleCardResult(
        text=loop_result.text,
        source="llm",
        program_slug=program_slug,
        week=week,
        loop_result=loop_result,
        fallback_reason=None,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _connection_for_builder(db: "Database") -> Optional[sqlite3.Connection]:
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


def fallback_to_sync_path(program_slug: str, week: int) -> Optional[str]:
    """Default fallback: the legacy
    :func:`cfb_rankings.team_pages.chronicle_generator.generate_chronicle_for_team`
    pipeline runs in its existing call sites.

    Returns ``None`` — callers' existing sync rail handles the no-LLM
    case (template-only chronicle cards).
    """
    return None


__all__ = [
    "SURFACE_KEY",
    "SUBCOMMAND",
    "MAX_TOKENS",
    "CHRONICLE_PROFILED_SYSTEM_PROMPT",
    "ChronicleCardResult",
    "compose_prompt_body",
    "format_thread_history",
    "extract_named_entity_ledger",
    "is_profiled",
    "synthesize_chronicle_card",
    "fallback_to_sync_path",
]
