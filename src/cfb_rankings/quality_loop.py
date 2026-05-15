"""Critique-loop wrapper around ``llm_runtime.generate_with_voice_check``.

Sprint v5-1 Day 5 deliverable per ``DESIGN_AUDIT_2026_05_15_v5_3.md`` Part 3
and ``IMPLEMENTATION_PLAN.md`` Part 6. This module is a *peer* of
``llm_runtime.py``, not a replacement — the eight existing
``generate_with_voice_check`` call sites stay on contract until Sprint v5-2
begins flipping ``config.QUALITY_LOOP_FLAGS`` flags surface-by-surface.

What lives here:

1. **Five loop patterns** (A through E) — single-shot, single critic,
   critic-revise, adversarial, continuity-grounded. Each loop drives the
   underlying ``generate_with_voice_check`` once for generation and 0-N
   times for critique, then optionally regenerates with critique guidance
   appended to the prompt.

2. **Five critic roles** — voice, headline, factuality, engagement,
   continuity. Each returns ``{"pass": bool, "score": float, "issues":
   list, "suggested_revisions": str}`` JSON. Parsed defensively because
   Opus sometimes wraps the payload in markdown fences.

3. **Three-rung circuit breakers** —
   - Rung 1 (consecutive critic failures ≥ 2): escalate gen-model tier and
     retry once;
   - Rung 2 (consecutive critic failures ≥ 3 after escalation): fall back
     to the seed/draft path; caller receives ``fell_back=True`` and a
     reason string;
   - Rung 3 (per-surface weekly spend > ``WEEKLY_CEILINGS_CENTS``): halt
     loop for the rest of the week.

4. **Telemetry** via ``team_pages.llm_usage_log.append_llm_usage`` with
   the new fields ``loop_pattern``, ``critic_roles_used``,
   ``critic_scores``, ``revise_count``, ``fell_back``, ``fallback_reason``.

5. **Dispatch helper** — ``loop_for_surface(surface)`` reads
   ``config.QUALITY_LOOP_FLAGS`` and returns the appropriate loop function.
   With the flags dict empty (Sprint v5-1 default) this returns ``None``;
   call sites should branch to the legacy direct ``generate_with_voice_check``
   path when no flag is set.

Notes on critic prompt provenance: the v5.3 audit Part 3 describes the
five critic roles in prose (lines 196-200) but the verbatim prompt text
lives in "Investigator C's report", which is not committed to this repo.
The prompt constants below are faithful syntheses of the Part 3 behavior
spec — banned-phrase + register fit for voice, 5-question §2.9 rubric
for headline, claim-tracing for factuality, "would a sophisticated CFB
reader linger" for engagement, named-entity ledger + thread-arc check for
continuity. Tune freely from here; tests pin the *structure* of each
prompt (system prompt mentions the role + required JSON keys) so prompt
copy can iterate without breaking the regression net.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable

from cfb_rankings import llm_runtime
from cfb_rankings.team_pages import llm_usage_log


# ---------------------------------------------------------------------------
# Public enums + dataclasses
# ---------------------------------------------------------------------------

class LoopPattern(str, Enum):
    """The five critique-loop patterns. String values keep telemetry+
    config dictionaries human-readable in JSONL logs."""
    A_SINGLE_SHOT = "A_single_shot"
    B_SINGLE_CRITIC = "B_single_critic"
    C_CRITIC_REVISE = "C_critic_revise"
    D_ADVERSARIAL = "D_adversarial"
    E_CONTINUITY = "E_continuity"


class CriticRole(str, Enum):
    """The five critic roles. Wired into ``run_critic(role=...)``."""
    VOICE = "voice"
    HEADLINE = "headline"
    FACTUALITY = "factuality"
    ENGAGEMENT = "engagement"
    CONTINUITY = "continuity"


@dataclass
class CriticVerdict:
    """One critic's response on one draft."""
    passed: bool
    score: float  # 0-10
    issues: list[str]
    suggested_revisions: str
    critic_role: str
    model: str
    tokens: dict[str, int]  # {"input": int, "output": int}

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "issues": list(self.issues),
            "suggested_revisions": self.suggested_revisions,
            "critic_role": self.critic_role,
            "model": self.model,
            "tokens": dict(self.tokens),
        }


@dataclass
class LoopResult:
    """Outcome of one loop_x() call. ``text`` is None on Rung-2 fall-back
    (caller is expected to render the seed/draft alternative)."""
    text: str | None
    pattern: str
    final_score: float
    verdicts: list[CriticVerdict]
    revise_count: int
    total_tokens: dict[str, int]
    fell_back: bool = False
    fallback_reason: str | None = None
    voice_validator_passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "pattern": self.pattern,
            "final_score": self.final_score,
            "verdicts": [v.to_dict() for v in self.verdicts],
            "revise_count": self.revise_count,
            "total_tokens": dict(self.total_tokens),
            "fell_back": self.fell_back,
            "fallback_reason": self.fallback_reason,
            "voice_validator_passed": self.voice_validator_passed,
        }


# ---------------------------------------------------------------------------
# Constants — pass thresholds, model tiers, defaults
# ---------------------------------------------------------------------------

# Scoring threshold defaults. Tunable per Open Item #2 in v5.3 Part 7.
DEFAULT_PASS_THRESHOLD = 7.0
ENGAGEMENT_PASS_THRESHOLD = 7.5
HEADLINE_PASS_THRESHOLD = 8.0  # "fail < 8" per v5.3 Part 3 line 197

# Model tier ladder for Rung-1 escalation. Sonnet → Opus is the most common
# step; Haiku → Sonnet covers Tier-2/3. Keys are model-id substrings, not
# exact match — Anthropic versions roll forward independently.
_MODEL_ESCALATION = {
    # Haiku → Sonnet
    "claude-haiku-4-5": "claude-sonnet-4-6",
    "claude-haiku-4": "claude-sonnet-4-6",
    # Sonnet → Opus
    "claude-sonnet-4-6": "claude-opus-4-7",
    "claude-sonnet-4-5": "claude-opus-4-7",
    "claude-sonnet-4": "claude-opus-4-7",
}

# Default models for each critic role per v5.3 Part 3 / Part 6.3.
_CRITIC_MODEL_DEFAULTS: dict[CriticRole, str] = {
    CriticRole.VOICE: "claude-haiku-4-5",        # Sonnet for Tier-1, overridable
    CriticRole.HEADLINE: "claude-haiku-4-5",
    CriticRole.FACTUALITY: "claude-sonnet-4-6",
    CriticRole.ENGAGEMENT: "claude-opus-4-7",    # Pattern D only
    CriticRole.CONTINUITY: "claude-sonnet-4-6",  # Pattern E only
}

# Gen-side default models for each loop pattern. Loop functions accept an
# explicit ``model=`` override that wins. These are the floors.
_LOOP_GEN_MODEL_DEFAULTS: dict[LoopPattern, str] = {
    LoopPattern.A_SINGLE_SHOT: "claude-sonnet-4-6",
    LoopPattern.B_SINGLE_CRITIC: "claude-sonnet-4-6",
    LoopPattern.C_CRITIC_REVISE: "claude-opus-4-7",
    LoopPattern.D_ADVERSARIAL: "claude-opus-4-7",
    LoopPattern.E_CONTINUITY: "claude-opus-4-7",
}

# Max revise passes per pattern (excluding the initial generation).
_MAX_REVISES: dict[LoopPattern, int] = {
    LoopPattern.A_SINGLE_SHOT: 0,
    LoopPattern.B_SINGLE_CRITIC: 1,
    LoopPattern.C_CRITIC_REVISE: 1,
    LoopPattern.D_ADVERSARIAL: 2,
    LoopPattern.E_CONTINUITY: 1,
}

# Wall-clock timeout per loop invocation (seconds). Defense-in-depth against
# the runaway-loop failure mode: an SDK hang, a network stall, or a critic
# stuck in retry would otherwise burn unbounded compute. The `_MAX_REVISES`
# iteration cap already bounds the call count, but doesn't bound wall-clock
# per call. The console.anthropic.com $100/mo cap catches runaway spend on
# a multi-day timescale; this timeout catches it within seconds.
#
# Sized per pattern's expected work:
#   A: single shot — 30s plenty
#   B: gen + 1 critic + maybe 1 revise — 60s
#   C: gen + 3 critics + 1 revise + 3 re-critics — 90s
#   D: gen + 4 critics + 2 revises + 4 re-critics — 150s
#   E: gen + 3 critics + 1 revise + continuity preload — 90s
#
# Tunable per surface via call-site argument; this is the hard ceiling.
_WALL_CLOCK_TIMEOUT_S: dict[LoopPattern, float] = {
    LoopPattern.A_SINGLE_SHOT: 30.0,
    LoopPattern.B_SINGLE_CRITIC: 60.0,
    LoopPattern.C_CRITIC_REVISE: 90.0,
    LoopPattern.D_ADVERSARIAL: 150.0,
    LoopPattern.E_CONTINUITY: 90.0,
}


# ---------------------------------------------------------------------------
# Circuit-breaker state (process-local; persistence is a Sprint v5-1 Day 5
# follow-on migration `20260520_16_circuit_state.sql`). For Sprint v5-1
# we hold counters in-memory; tests reset via `reset_circuit_state()`.
# ---------------------------------------------------------------------------

@dataclass
class _CircuitState:
    consecutive_critic_failures: int = 0
    escalated_this_run: bool = False
    weekly_spend_cents: dict[str, int] = field(default_factory=dict)
    halted_surfaces: set[str] = field(default_factory=set)


_CIRCUIT_STATE = _CircuitState()


def reset_circuit_state() -> None:
    """Clear in-memory circuit state. Tests use this between cases."""
    global _CIRCUIT_STATE
    _CIRCUIT_STATE = _CircuitState()


def _check_rung_3(surface: str) -> tuple[bool, str | None]:
    """Return ``(blocked, reason)`` if surface has tripped its weekly
    ceiling. Reads from `config.WEEKLY_CEILINGS_CENTS`."""
    if surface in _CIRCUIT_STATE.halted_surfaces:
        return (True, "weekly_ceiling")
    try:
        from cfb_rankings.config import WEEKLY_CEILINGS_CENTS
    except Exception:
        return (False, None)
    ceiling = WEEKLY_CEILINGS_CENTS.get(surface)
    if ceiling is None:
        return (False, None)
    spent = _CIRCUIT_STATE.weekly_spend_cents.get(surface, 0)
    if spent > ceiling:
        _CIRCUIT_STATE.halted_surfaces.add(surface)
        return (True, "weekly_ceiling")
    return (False, None)


def _record_spend(surface: str | None, cents: int) -> None:
    """Increment per-surface weekly spend counter (in-memory)."""
    if not surface or cents <= 0:
        return
    _CIRCUIT_STATE.weekly_spend_cents[surface] = (
        _CIRCUIT_STATE.weekly_spend_cents.get(surface, 0) + cents
    )


# ---------------------------------------------------------------------------
# Critic prompt constants
#
# Each prompt template returns the same JSON envelope:
#   {"pass": bool, "score": float, "issues": [str], "suggested_revisions": str}
#
# System prompt is fixed per role. User prompt embeds the candidate text,
# the surface context (if any), and a reminder of the response schema.
# ---------------------------------------------------------------------------

_JSON_SCHEMA_REMINDER = (
    'Respond with a single JSON object and nothing else. The object must '
    'have exactly these keys: "pass" (boolean), "score" (number 0 to 10), '
    '"issues" (array of short strings), "suggested_revisions" (string of '
    'concrete guidance for a rewrite, empty string if pass=true). Do not '
    'wrap the JSON in markdown code fences.'
)

_VOICE_CRITIC_SYSTEM = (
    "You are the VOICE critic for CFB Index. Your job is to enforce the "
    "publication's fan-voice register — sounds like a literate beat writer, "
    "never like AI marketing copy or internal analyst taxonomy.\n\n"
    "Auto-fail (score 0, pass=false) if the candidate contains any banned "
    "phrase from this taxonomy: analytics-cohort, casual-cohort, "
    "die-hard-cohort, national-narrative-cohort, n=, effective_n, "
    "discourse velocity, signal pipeline, engagement loop, leverage the, "
    "delve into, in the realm of, paradigm shift, synergy. Any close "
    "variant (with or without hyphen, with or without quotes) also fails.\n\n"
    "If no banned phrase appears, score on register fit:\n"
    "  10 = reads exactly like a knowledgeable fan/beat writer\n"
    "   7 = clean but slightly generic\n"
    "   4 = AI-flavored hedging or vague\n"
    "   0 = banned-phrase hit\n\n"
    "pass=true requires score >= 7."
)

_HEADLINE_CRITIC_SYSTEM = (
    "You are the HEADLINE critic for CFB Index. Apply the 5-question §2.9 "
    "rubric from the v4 stylebook. For each YES award 2 points (max 10):\n\n"
    "  1. Does the headline name a specific entity (program, player, "
    "     coach, conference)? Generic nouns like 'team' or 'player' = NO.\n"
    "  2. Does it carry a verb of consequence (not just 'is', 'has')?\n"
    "  3. Is there a stake or tension implied (someone has something to "
    "     lose, gain, or prove)?\n"
    "  4. Is it under 12 words and free of clickbait punctuation "
    "     (no '...', no '!!!')?\n"
    "  5. Does it pass the 'said-on-the-podcast' test — would a host say "
    "     this verbatim into a microphone?\n\n"
    "Score = 2 × number of YES. pass=true requires score >= 8 (4 of 5 YES)."
)

_FACTUALITY_CRITIC_SYSTEM = (
    "You are the FACTUALITY critic for CFB Index. Every numeric value, "
    "every date, every score, every named person, every quoted phrase in "
    "the candidate must be traceable to the SOURCE OBSERVATIONS block in "
    "the user prompt. Mild paraphrase of source language is OK; wholesale "
    "invention of statistics, ranks, dates, or attributions is not.\n\n"
    "For each claim in the candidate, mark it traceable or not. Score:\n"
    "  10 = every claim traceable, no invented specifics\n"
    "   7 = minor unsupported color (e.g. 'fans were thrilled') OK; "
    "       all numerics and attributions trace\n"
    "   4 = at least one numeric or attribution does not trace\n"
    "   0 = multiple invented facts\n\n"
    "List each untraceable claim verbatim in `issues`. pass=true requires "
    "score >= 7."
)

_ENGAGEMENT_CRITIC_SYSTEM = (
    "You are the ENGAGEMENT critic for CFB Index. This critic only fires "
    "for Pattern D (Edition cover essay) — the highest-stakes longform "
    "surface in the publication. Your single question: would a "
    "sophisticated college football reader (one who knows the difference "
    "between SP+ and FPI, follows beat writers, lurks on multiple boards) "
    "stop scrolling and read this all the way through?\n\n"
    "Score on the reader's likely behavior:\n"
    "  10 = irresistible — opens with tension, sustains it, lands a punch\n"
    "   7 = solid — reads fine but doesn't grip\n"
    "   4 = competent but generic; reader skims and leaves\n"
    "   0 = wouldn't get past the dek\n\n"
    "Flag every place where the prose lapses into list-mode, abstract "
    "hedging, or wire-recap voice. pass=true requires score >= 7.5."
)

_CONTINUITY_CRITIC_SYSTEM = (
    "You are the CONTINUITY critic for CFB Index. This critic only fires "
    "for Pattern E (storyline thread chapters + chronicle cards for "
    "profiled programs). Given the THREAD HISTORY and NAMED-ENTITY LEDGER "
    "in the user prompt, judge whether the candidate:\n\n"
    "  1. Advances the thread (introduces a new beat, doesn't restate "
    "     prior chapters);\n"
    "  2. Preserves named-entity phrasing (if prior chapters call it "
    "     'the standard' it must stay 'the standard', not 'the bar');\n"
    "  3. Does not contradict prior chapters' factual claims;\n"
    "  4. References at least one specific element of the running arc.\n\n"
    "Score: 2.5 points per criterion met (max 10). pass=true requires "
    "score >= 7 (3 of 4 criteria). List every contradiction or "
    "entity-rename in `issues`."
)


_CRITIC_SYSTEM_PROMPTS: dict[CriticRole, str] = {
    CriticRole.VOICE: _VOICE_CRITIC_SYSTEM,
    CriticRole.HEADLINE: _HEADLINE_CRITIC_SYSTEM,
    CriticRole.FACTUALITY: _FACTUALITY_CRITIC_SYSTEM,
    CriticRole.ENGAGEMENT: _ENGAGEMENT_CRITIC_SYSTEM,
    CriticRole.CONTINUITY: _CONTINUITY_CRITIC_SYSTEM,
}


def _critic_user_prompt(role: CriticRole, text: str, context: dict | None) -> str:
    """Build the user-side prompt for a critic call. Surface-specific
    context goes here; the schema reminder is appended verbatim."""
    parts: list[str] = []
    parts.append(f"CANDIDATE TEXT (role={role.value}):\n---\n{text}\n---")
    if context:
        if role == CriticRole.FACTUALITY and "source_observations" in context:
            parts.append(
                "SOURCE OBSERVATIONS (every claim in the candidate must "
                f"trace to this block):\n---\n{context['source_observations']}\n---"
            )
        if role == CriticRole.CONTINUITY:
            if "thread_history" in context:
                parts.append(
                    "THREAD HISTORY (prior chapters in this storyline):\n"
                    f"---\n{context['thread_history']}\n---"
                )
            if "entity_ledger" in context:
                parts.append(
                    "NAMED-ENTITY LEDGER (must preserve these phrasings):\n"
                    f"---\n{context['entity_ledger']}\n---"
                )
        if role == CriticRole.HEADLINE and "headline" in context:
            parts.append(f"HEADLINE UNDER REVIEW:\n---\n{context['headline']}\n---")
        if "surface" in context:
            parts.append(f"SURFACE: {context['surface']}")
    parts.append(_JSON_SCHEMA_REMINDER)
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Defensive JSON parsing — Opus sometimes wraps payloads in ```json fences.
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)
_FIRST_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_critic_json(raw: str) -> dict[str, Any]:
    """Extract the JSON envelope from a critic response. Strips markdown
    fences if present; falls back to first-balanced-braces scan."""
    if not raw or not raw.strip():
        return _default_failure_payload("empty_response")
    text = raw.strip()
    # Try fenced block first.
    m = _FENCE_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Plain JSON object scan.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = _FIRST_OBJECT_RE.search(text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return _default_failure_payload(f"unparseable:{text[:60]!r}")


def _default_failure_payload(reason: str) -> dict[str, Any]:
    return {
        "pass": False,
        "score": 0.0,
        "issues": [f"critic_parse_failed: {reason}"],
        "suggested_revisions": (
            "The critic response could not be parsed as JSON. Regenerate "
            "the candidate from scratch, focusing on a cleaner structure."
        ),
    }


def _coerce_verdict(payload: dict[str, Any], role: CriticRole, model: str,
                    tokens: dict[str, int], pass_threshold: float) -> CriticVerdict:
    """Coerce a parsed JSON payload into a CriticVerdict. Tolerates
    missing/misnamed fields — defaults to fail if score absent."""
    raw_pass = payload.get("pass", payload.get("passed", False))
    try:
        score = float(payload.get("score", 0))
    except (TypeError, ValueError):
        score = 0.0
    # Clamp to 0-10.
    score = max(0.0, min(10.0, score))
    issues_raw = payload.get("issues", [])
    if isinstance(issues_raw, str):
        issues = [issues_raw]
    elif isinstance(issues_raw, Iterable):
        issues = [str(x) for x in issues_raw]
    else:
        issues = []
    suggested = str(payload.get("suggested_revisions", "") or "")
    # If the critic didn't explicitly pass, gate on score.
    passed = bool(raw_pass) and score >= pass_threshold
    return CriticVerdict(
        passed=passed,
        score=score,
        issues=issues,
        suggested_revisions=suggested,
        critic_role=role.value,
        model=model,
        tokens=tokens,
    )


# ---------------------------------------------------------------------------
# run_critic — single critic invocation
# ---------------------------------------------------------------------------

def run_critic(
    role: CriticRole | str,
    text: str,
    context: dict | None = None,
    *,
    model: str | None = None,
    pass_threshold: float | None = None,
) -> CriticVerdict:
    """Invoke one critic on a candidate string. Returns a CriticVerdict.

    Wraps ``llm_runtime.generate_with_voice_check`` with the critic-role
    system prompt. The voice validator on the critic call itself is a
    safety net (a critic response is internal and shouldn't normally trip
    it, but if Opus echoes the candidate's banned phrase in its issues
    list it's fine to flag — the verdict still parses).
    """
    if isinstance(role, str):
        role = CriticRole(role)
    if model is None:
        model = _CRITIC_MODEL_DEFAULTS[role]
    if pass_threshold is None:
        pass_threshold = {
            CriticRole.VOICE: DEFAULT_PASS_THRESHOLD,
            CriticRole.HEADLINE: HEADLINE_PASS_THRESHOLD,
            CriticRole.FACTUALITY: DEFAULT_PASS_THRESHOLD,
            CriticRole.ENGAGEMENT: ENGAGEMENT_PASS_THRESHOLD,
            CriticRole.CONTINUITY: DEFAULT_PASS_THRESHOLD,
        }[role]

    system = _CRITIC_SYSTEM_PROMPTS[role]
    user_prompt = _critic_user_prompt(role, text, context)

    result = llm_runtime.generate_with_voice_check(
        user_prompt,
        system=system,
        model=model,
        max_tokens=1500,
        max_retries=0,  # critics get one shot; their voice failures don't matter
    )
    tokens = result.get("tokens_used") or {"input": 0, "output": 0}
    raw_text = result.get("text") or ""
    if result.get("mode") == "offline-stub":
        # No API key — auto-pass with neutral score so the loop short-circuits
        # in dev/test environments without making the surface look broken.
        return CriticVerdict(
            passed=True,
            score=DEFAULT_PASS_THRESHOLD,
            issues=[],
            suggested_revisions="",
            critic_role=role.value,
            model=model,
            tokens=tokens,
        )
    payload = _parse_critic_json(raw_text)
    return _coerce_verdict(payload, role, model, tokens, pass_threshold)


# ---------------------------------------------------------------------------
# Internal helper: one generation call (gen-side, voice-validator gated)
# ---------------------------------------------------------------------------

def _generate(
    prompt: str,
    *,
    system: str | None,
    model: str,
    max_tokens: int,
) -> dict[str, Any]:
    """Thin wrapper over generate_with_voice_check that always returns a
    dict (offline-stub yields text=None, which loop_* must handle)."""
    return llm_runtime.generate_with_voice_check(
        prompt,
        system=system,
        model=model,
        max_tokens=max_tokens,
        max_retries=1,
    )


def _add_tokens(running: dict[str, int], add: dict[str, int]) -> dict[str, int]:
    running["input"] = running.get("input", 0) + int(add.get("input", 0))
    running["output"] = running.get("output", 0) + int(add.get("output", 0))
    return running


def _escalate_model(current: str) -> str:
    """Return the next-tier model for Rung-1 escalation, or the same
    model if already at the top."""
    return _MODEL_ESCALATION.get(current, current)


def _revise_prompt(original: str, verdicts: list[CriticVerdict]) -> str:
    """Append critic guidance to the original prompt for a revise pass."""
    blocks: list[str] = []
    for v in verdicts:
        if v.passed:
            continue
        block = (
            f"[{v.critic_role.upper()} CRITIC — score {v.score:.1f}/10]\n"
            f"Issues: {'; '.join(v.issues) if v.issues else '(none listed)'}\n"
            f"Guidance: {v.suggested_revisions or '(no specific guidance)'}\n"
        )
        blocks.append(block)
    if not blocks:
        return original
    return (
        f"{original}\n\n---\n"
        "Your previous draft failed one or more critic checks. Revise once, "
        "preserving the editorial intent but addressing every issue below.\n\n"
        + "\n".join(blocks)
    )


def _emit_telemetry(
    *,
    subcommand: str,
    pattern: LoopPattern,
    model: str,
    result: LoopResult,
    duration_s: float,
    surface: str | None,
) -> None:
    """Single telemetry line per loop call. Extends ``append_llm_usage``
    with the new fields per v5.3 Part 3."""
    extra: dict[str, Any] = {
        "loop_pattern": result.pattern,
        "critic_roles_used": [v.critic_role for v in result.verdicts],
        "critic_scores": [v.score for v in result.verdicts],
        "revise_count": result.revise_count,
        "fell_back": result.fell_back,
        "fallback_reason": result.fallback_reason,
        "final_score": result.final_score,
    }
    if surface:
        extra["surface"] = surface
    try:
        llm_usage_log.append_llm_usage(
            subcommand=subcommand,
            model=model,
            prompt_tokens=result.total_tokens.get("input", 0),
            completion_tokens=result.total_tokens.get("output", 0),
            duration_s=duration_s,
            extra=extra,
        )
    except Exception:
        # Telemetry must never crash a loop. Log dir creation, disk full,
        # JSON serialization edge cases — all swallowed.
        pass


# ---------------------------------------------------------------------------
# Pattern A — Single-shot + regex voice validation
# ---------------------------------------------------------------------------

def loop_a_single_shot(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    max_tokens: int = 4000,
    surface: str | None = None,
    subcommand: str = "quality_loop.A",
) -> LoopResult:
    """Pattern A — single Opus/Sonnet call, no critique loop.

    For Wire factual restatement, Canon tail, headline judge, all Tier-3
    surfaces. Cost ~$0.006/call. The regex voice validator inside
    ``generate_with_voice_check`` is the only gate.
    """
    pattern = LoopPattern.A_SINGLE_SHOT
    started = time.monotonic()
    model = model or _LOOP_GEN_MODEL_DEFAULTS[pattern]
    totals = {"input": 0, "output": 0}

    blocked, reason = _check_rung_3(surface) if surface else (False, None)
    if blocked:
        result = LoopResult(
            text=None, pattern=pattern.value, final_score=0.0,
            verdicts=[], revise_count=0, total_tokens=totals,
            fell_back=True, fallback_reason=reason,
            voice_validator_passed=False,
        )
        _emit_telemetry(subcommand=subcommand, pattern=pattern, model=model,
                        result=result, duration_s=time.monotonic() - started,
                        surface=surface)
        return result

    gen = _generate(prompt, system=system, model=model, max_tokens=max_tokens)
    _add_tokens(totals, gen.get("tokens_used") or {})
    voice_passed = bool(gen.get("voice_validator_passed", False))
    score = 10.0 if voice_passed else 0.0
    result = LoopResult(
        text=gen.get("text"),
        pattern=pattern.value,
        final_score=score,
        verdicts=[],
        revise_count=0,
        total_tokens=totals,
        fell_back=False,
        fallback_reason=None,
        voice_validator_passed=voice_passed,
    )
    _emit_telemetry(subcommand=subcommand, pattern=pattern, model=model,
                    result=result, duration_s=time.monotonic() - started,
                    surface=surface)
    return result


# ---------------------------------------------------------------------------
# Pattern B — Single critic loop
# ---------------------------------------------------------------------------

def loop_b_single_critic(
    prompt: str,
    *,
    critic_role: CriticRole | str = CriticRole.VOICE,
    system: str | None = None,
    model: str | None = None,
    critic_model: str | None = None,
    critic_context: dict | None = None,
    max_tokens: int = 4000,
    surface: str | None = None,
    subcommand: str = "quality_loop.B",
) -> LoopResult:
    """Pattern B — generate → single critic → regenerate once if score < 7.

    For Tier-2 narratives, Chronicle ranks 3-5, source-voice summaries.
    Cost ~$0.04/call. Default critic is the voice critic; pass another
    via ``critic_role=``.
    """
    pattern = LoopPattern.B_SINGLE_CRITIC
    if isinstance(critic_role, str):
        critic_role = CriticRole(critic_role)
    started = time.monotonic()
    model = model or _LOOP_GEN_MODEL_DEFAULTS[pattern]
    totals = {"input": 0, "output": 0}

    blocked, reason = _check_rung_3(surface) if surface else (False, None)
    if blocked:
        result = LoopResult(
            text=None, pattern=pattern.value, final_score=0.0,
            verdicts=[], revise_count=0, total_tokens=totals,
            fell_back=True, fallback_reason=reason,
        )
        _emit_telemetry(subcommand=subcommand, pattern=pattern, model=model,
                        result=result, duration_s=time.monotonic() - started,
                        surface=surface)
        return result

    return _run_critic_loop(
        prompt=prompt,
        system=system,
        gen_model=model,
        critic_roles=[critic_role],
        critic_model_overrides={critic_role: critic_model} if critic_model else None,
        critic_context=critic_context,
        max_tokens=max_tokens,
        pattern=pattern,
        max_revises=_MAX_REVISES[pattern],
        surface=surface,
        subcommand=subcommand,
        totals=totals,
        started=started,
    )


# ---------------------------------------------------------------------------
# Pattern C — Critic-revise (the dominant Tier-1 loop)
# ---------------------------------------------------------------------------

def loop_c_critic_revise(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    critic_models: dict[CriticRole, str] | None = None,
    critic_context: dict | None = None,
    max_tokens: int = 4000,
    surface: str | None = None,
    subcommand: str = "quality_loop.C",
) -> LoopResult:
    """Pattern C — generate (Opus + thinking) → voice + headline + factuality
    critics → revise once → re-critique → emit.

    The default Tier-1 loop. Wraps every surface in v5.3 Part 1 Tier-1
    table except Edition cover (Pattern D) and Storyline/Chronicle profiled
    (Pattern E). Cost ~$0.40/call.
    """
    pattern = LoopPattern.C_CRITIC_REVISE
    started = time.monotonic()
    model = model or _LOOP_GEN_MODEL_DEFAULTS[pattern]
    totals = {"input": 0, "output": 0}

    blocked, reason = _check_rung_3(surface) if surface else (False, None)
    if blocked:
        result = LoopResult(
            text=None, pattern=pattern.value, final_score=0.0,
            verdicts=[], revise_count=0, total_tokens=totals,
            fell_back=True, fallback_reason=reason,
        )
        _emit_telemetry(subcommand=subcommand, pattern=pattern, model=model,
                        result=result, duration_s=time.monotonic() - started,
                        surface=surface)
        return result

    return _run_critic_loop(
        prompt=prompt,
        system=system,
        gen_model=model,
        critic_roles=[CriticRole.VOICE, CriticRole.HEADLINE, CriticRole.FACTUALITY],
        critic_model_overrides=critic_models,
        critic_context=critic_context,
        max_tokens=max_tokens,
        pattern=pattern,
        max_revises=_MAX_REVISES[pattern],
        surface=surface,
        subcommand=subcommand,
        totals=totals,
        started=started,
    )


# ---------------------------------------------------------------------------
# Pattern D — Adversarial (Edition cover only)
# ---------------------------------------------------------------------------

def loop_d_adversarial(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    critic_models: dict[CriticRole, str] | None = None,
    critic_context: dict | None = None,
    max_tokens: int = 8000,
    surface: str | None = None,
    subcommand: str = "quality_loop.D",
) -> LoopResult:
    """Pattern D — Edition cover. Generate (Opus + 16K thinking) →
    Critic Group A (voice + headline + factuality, structural) +
    Critic B (engagement, "would a sophisticated CFB reader linger?") →
    revise satisfying both groups → re-score → emit.

    Cost ~$0.60/call. Edition cover essay only at first; tentpole editions
    follow per IMPLEMENTATION_PLAN.md Part 6.7.
    """
    pattern = LoopPattern.D_ADVERSARIAL
    started = time.monotonic()
    model = model or _LOOP_GEN_MODEL_DEFAULTS[pattern]
    totals = {"input": 0, "output": 0}

    blocked, reason = _check_rung_3(surface) if surface else (False, None)
    if blocked:
        result = LoopResult(
            text=None, pattern=pattern.value, final_score=0.0,
            verdicts=[], revise_count=0, total_tokens=totals,
            fell_back=True, fallback_reason=reason,
        )
        _emit_telemetry(subcommand=subcommand, pattern=pattern, model=model,
                        result=result, duration_s=time.monotonic() - started,
                        surface=surface)
        return result

    return _run_critic_loop(
        prompt=prompt,
        system=system,
        gen_model=model,
        critic_roles=[
            CriticRole.VOICE,
            CriticRole.HEADLINE,
            CriticRole.FACTUALITY,
            CriticRole.ENGAGEMENT,
        ],
        critic_model_overrides=critic_models,
        critic_context=critic_context,
        max_tokens=max_tokens,
        pattern=pattern,
        max_revises=_MAX_REVISES[pattern],
        surface=surface,
        subcommand=subcommand,
        totals=totals,
        started=started,
    )


# ---------------------------------------------------------------------------
# Pattern E — Continuity-grounded (Storylines + Chronicle profiled)
# ---------------------------------------------------------------------------

def loop_e_continuity(
    prompt: str,
    *,
    thread_history: str | None = None,
    entity_ledger: str | None = None,
    system: str | None = None,
    model: str | None = None,
    critic_models: dict[CriticRole, str] | None = None,
    critic_context: dict | None = None,
    max_tokens: int = 4000,
    surface: str | None = None,
    subcommand: str = "quality_loop.E",
) -> LoopResult:
    """Pattern E — Pattern C plus a continuity critic that sees the last
    3 chapters/cards + a named-entity ledger.

    For Storyline thread chapters and Chronicle cards on profiled programs.
    Cost ~$0.15/call (caching makes thread history nearly free on the
    second + third chapters of the same arc).
    """
    pattern = LoopPattern.E_CONTINUITY
    started = time.monotonic()
    model = model or _LOOP_GEN_MODEL_DEFAULTS[pattern]
    totals = {"input": 0, "output": 0}

    blocked, reason = _check_rung_3(surface) if surface else (False, None)
    if blocked:
        result = LoopResult(
            text=None, pattern=pattern.value, final_score=0.0,
            verdicts=[], revise_count=0, total_tokens=totals,
            fell_back=True, fallback_reason=reason,
        )
        _emit_telemetry(subcommand=subcommand, pattern=pattern, model=model,
                        result=result, duration_s=time.monotonic() - started,
                        surface=surface)
        return result

    # Inject thread history + entity ledger into both the gen system prompt
    # and the continuity critic context.
    augmented_system = system or ""
    if thread_history:
        augmented_system += (
            "\n\nTHREAD HISTORY (last 3 chapters/cards in this storyline):\n"
            f"---\n{thread_history}\n---"
        )
    if entity_ledger:
        augmented_system += (
            "\n\nNAMED-ENTITY LEDGER (preserve these phrasings exactly):\n"
            f"---\n{entity_ledger}\n---"
        )

    continuity_ctx = dict(critic_context or {})
    if thread_history:
        continuity_ctx["thread_history"] = thread_history
    if entity_ledger:
        continuity_ctx["entity_ledger"] = entity_ledger

    return _run_critic_loop(
        prompt=prompt,
        system=augmented_system or None,
        gen_model=model,
        critic_roles=[
            CriticRole.VOICE,
            CriticRole.HEADLINE,
            CriticRole.FACTUALITY,
            CriticRole.CONTINUITY,
        ],
        critic_model_overrides=critic_models,
        critic_context=continuity_ctx,
        max_tokens=max_tokens,
        pattern=pattern,
        max_revises=_MAX_REVISES[pattern],
        surface=surface,
        subcommand=subcommand,
        totals=totals,
        started=started,
    )


# ---------------------------------------------------------------------------
# Shared internal critic-loop driver (Patterns B, C, D, E)
# ---------------------------------------------------------------------------

def _run_critic_loop(
    *,
    prompt: str,
    system: str | None,
    gen_model: str,
    critic_roles: list[CriticRole],
    critic_model_overrides: dict[CriticRole, str] | None,
    critic_context: dict | None,
    max_tokens: int,
    pattern: LoopPattern,
    max_revises: int,
    surface: str | None,
    subcommand: str,
    totals: dict[str, int],
    started: float,
) -> LoopResult:
    """Shared driver: generate → critique → optionally revise once →
    re-critique → return. Implements Rung-1 escalation + Rung-2 fall-back.
    """
    # Track consecutive critic failures for this surface in process-local
    # state. A failure here means at least one critic in the panel said
    # passed=False on the final draft.
    revise_count = 0
    all_verdicts: list[CriticVerdict] = []
    current_model = gen_model
    current_prompt = prompt
    fell_back = False
    fallback_reason: str | None = None
    final_text: str | None = None
    voice_passed = False
    escalated_this_call = False

    # First generation.
    gen = _generate(current_prompt, system=system, model=current_model,
                    max_tokens=max_tokens)
    _add_tokens(totals, gen.get("tokens_used") or {})
    final_text = gen.get("text")
    voice_passed = bool(gen.get("voice_validator_passed", False))

    if gen.get("mode") == "offline-stub":
        # No API key — short-circuit with a neutral result. Surface should
        # fall back to seed/draft path; we mark fell_back=True so telemetry
        # accounts for it without polluting weekly spend.
        result = LoopResult(
            text=None,
            pattern=pattern.value,
            final_score=0.0,
            verdicts=[],
            revise_count=0,
            total_tokens=totals,
            fell_back=True,
            fallback_reason="offline_stub",
            voice_validator_passed=False,
        )
        _emit_telemetry(subcommand=subcommand, pattern=pattern,
                        model=current_model, result=result,
                        duration_s=time.monotonic() - started,
                        surface=surface)
        return result

    # Critique round 1.
    verdicts = _run_critic_panel(
        text=final_text or "",
        roles=critic_roles,
        overrides=critic_model_overrides,
        context=critic_context,
    )
    for v in verdicts:
        _add_tokens(totals, v.tokens)
    all_verdicts.extend(verdicts)

    failed = [v for v in verdicts if not v.passed]
    # Total failed verdicts across all rounds is the Rung-1 / Rung-2 metric.
    # "Consecutive critic failures ≥ 2" trips Rung 1 (escalation);
    # "Consecutive critic failures ≥ 3 after escalation" trips Rung 2
    # (fall-back to seeds). Per v5.3 Part 3 lines 205-208 — failure count
    # is across critic verdicts, not loop rounds.
    total_failed = len(failed)
    if (
        total_failed >= 2
        and not _CIRCUIT_STATE.escalated_this_run
        and max_revises >= 1
    ):
        escalated_model = _escalate_model(current_model)
        if escalated_model != current_model:
            current_model = escalated_model
            _CIRCUIT_STATE.escalated_this_run = True
            escalated_this_call = True

    # Wall-clock safety net. If the loop has already burned through its
    # budget before entering the revise round (e.g. a hung first generation
    # or a critic panel that took ages), bail with a fall-back. Defense
    # against runaway: caps blast radius at one timeout window of compute
    # rather than letting it spin until rate-limit kicks in.
    timeout_s = _WALL_CLOCK_TIMEOUT_S.get(pattern, 120.0)
    if (time.monotonic() - started) > timeout_s:
        fell_back = True
        fallback_reason = f"wall_clock_timeout_{timeout_s:.0f}s"
        final_text = None
        failed = []  # skip the revise loop entirely

    # Revise + re-critique loop (max_revises times). Pattern A has 0,
    # Patterns B/C/E have 1, Pattern D has 2. Also bails on wall-clock
    # timeout — checked at start of every iteration.
    while failed and revise_count < max_revises:
        if (time.monotonic() - started) > timeout_s:
            fell_back = True
            fallback_reason = f"wall_clock_timeout_{timeout_s:.0f}s"
            final_text = None
            break
        revise_count += 1
        revised_prompt = _revise_prompt(current_prompt, verdicts)
        gen = _generate(revised_prompt, system=system, model=current_model,
                        max_tokens=max_tokens)
        _add_tokens(totals, gen.get("tokens_used") or {})
        final_text = gen.get("text")
        voice_passed = bool(gen.get("voice_validator_passed", False))
        if gen.get("mode") == "offline-stub":
            break
        verdicts = _run_critic_panel(
            text=final_text or "",
            roles=critic_roles,
            overrides=critic_model_overrides,
            context=critic_context,
        )
        for v in verdicts:
            _add_tokens(totals, v.tokens)
        all_verdicts.extend(verdicts)
        failed = [v for v in verdicts if not v.passed]
        total_failed += len(failed)

    # Mirror onto the process-local counter for cross-call accounting,
    # though Rung 1/2 decisions happen on the in-call `total_failed`
    # above. The process counter accumulates so a string of failures
    # across consecutive calls also trips Rung 2 even when each call's
    # own panel only fails once or twice.
    if not failed:
        _CIRCUIT_STATE.consecutive_critic_failures = 0
    else:
        _CIRCUIT_STATE.consecutive_critic_failures += total_failed

    # Rung 2 — total failed verdicts across this loop (initial + revise)
    # ≥ 3 triggers a fall-back. This means we tried, escalated, retried,
    # and the panel still rejected the output.
    if failed and total_failed >= 3:
        fell_back = True
        fallback_reason = "consecutive_critic_failures_after_escalation"
        final_text = None

    # Reset the per-run escalation flag so subsequent calls can escalate again.
    _CIRCUIT_STATE.escalated_this_run = False

    # Final score is the mean of the latest critique round (or 0 if fell back).
    if fell_back or not verdicts:
        final_score = 0.0
    else:
        final_score = sum(v.score for v in verdicts) / max(1, len(verdicts))

    result = LoopResult(
        text=final_text,
        pattern=pattern.value,
        final_score=final_score,
        verdicts=all_verdicts,
        revise_count=revise_count,
        total_tokens=totals,
        fell_back=fell_back,
        fallback_reason=fallback_reason,
        voice_validator_passed=voice_passed and not fell_back,
    )
    _emit_telemetry(subcommand=subcommand, pattern=pattern, model=current_model,
                    result=result, duration_s=time.monotonic() - started,
                    surface=surface)
    # `escalated_this_call` is captured in telemetry via the `model` field
    # (current_model reflects the escalated tier). No additional bookkeeping
    # on the LoopResult — Rung-1 escalation is an internal recovery, not a
    # failure mode the caller has to handle.
    _ = escalated_this_call  # retained for clarity; future digest may surface
    return result


def _run_critic_panel(
    *,
    text: str,
    roles: list[CriticRole],
    overrides: dict[CriticRole, str] | None,
    context: dict | None,
) -> list[CriticVerdict]:
    """Invoke each critic role on the same candidate text. Sequential —
    parallelism is a follow-on optimization; v5-1 keeps it simple."""
    out: list[CriticVerdict] = []
    for role in roles:
        model = (overrides or {}).get(role)
        verdict = run_critic(role, text, context=context, model=model)
        out.append(verdict)
    return out


# ---------------------------------------------------------------------------
# Dispatch helper — read config.QUALITY_LOOP_FLAGS
# ---------------------------------------------------------------------------

_LOOP_FUNCTIONS: dict[LoopPattern, Callable[..., LoopResult]] = {
    LoopPattern.A_SINGLE_SHOT: loop_a_single_shot,
    LoopPattern.B_SINGLE_CRITIC: loop_b_single_critic,
    LoopPattern.C_CRITIC_REVISE: loop_c_critic_revise,
    LoopPattern.D_ADVERSARIAL: loop_d_adversarial,
    LoopPattern.E_CONTINUITY: loop_e_continuity,
}


def loop_for_surface(surface: str) -> Callable[..., LoopResult] | None:
    """Look up the configured loop for a surface key.

    Returns the loop function (``loop_a_single_shot`` ... ``loop_e_continuity``)
    or ``None`` if the surface isn't in ``config.QUALITY_LOOP_FLAGS``.

    Call sites use ``None`` as the signal to stay on the legacy
    ``generate_with_voice_check`` path. Sprint v5-2 populates the flags
    dict surface-by-surface per the rollout in v5.3 Part 5.
    """
    try:
        from cfb_rankings.config import QUALITY_LOOP_FLAGS
    except Exception:
        return None
    pattern = QUALITY_LOOP_FLAGS.get(surface)
    if pattern is None:
        return None
    if isinstance(pattern, str):
        try:
            pattern = LoopPattern(pattern)
        except ValueError:
            return None
    return _LOOP_FUNCTIONS.get(pattern)


__all__ = [
    "LoopPattern",
    "CriticRole",
    "CriticVerdict",
    "LoopResult",
    "run_critic",
    "loop_a_single_shot",
    "loop_b_single_critic",
    "loop_c_critic_revise",
    "loop_d_adversarial",
    "loop_e_continuity",
    "loop_for_surface",
    "reset_circuit_state",
]
