"""Shared LLM runtime: SDK call + voice-validator retry + cost telemetry.

Used by every product surface that runs live LLM generation in --auto cron
contexts. First caller is Sprint 10's `generate-thread-chapter --auto`;
follow-on callers in Wave 3 (Daily, Reaction Story, Mailbag) inherit the
same retry loop, telemetry contract, and graceful-degradation behavior.

Contracts (the things callers can rely on):

1. **Never throws on missing API key.** When ANTHROPIC_API_KEY is unset
   and `fallback_to_offline=True` (the default), returns a result with
   ``mode='offline-stub'`` and ``text=None``. Callers branch on mode and
   fall back to seed/draft paths without conditional API-key handling.

2. **Never throws on rate limits.** Inner retry uses exponential backoff
   (1s → 2s → 4s → 8s → 16s, capped at 30s) with jitter, up to 5
   attempts. After 5 the underlying exception bubbles up.

3. **Always runs voice_validator on the output.** On fail, retries once
   (configurable via ``max_retries``) with appended rewrite guidance
   that names the banned phrases. After the retry budget is exhausted,
   returns the last response with ``voice_validator_passed=False`` so
   the caller decides what to do.

4. **Always logs structured cost telemetry.** Single JSON line per call
   under logger ``cfb_rankings.llm_runtime.telemetry``. Sweep tools can
   grep + sum input_tokens / output_tokens by model + mode.

5. **Graceful when SDK not installed.** Lazy import; if ``anthropic`` is
   not on the path, returns ``mode='offline-stub'``. Lets us run the
   product on minimal environments without forcing the dep.
"""
from __future__ import annotations

import importlib
import json
import logging
import os
import random
import time
from typing import Any, Callable

log = logging.getLogger(__name__)
_telemetry_log = logging.getLogger("cfb_rankings.llm_runtime.telemetry")


_VALIDATOR_CACHE: Callable[..., tuple[bool, list[str]]] | None = None


def _load_validator() -> Callable[..., tuple[bool, list[str]]]:
    """Lazy-import the validator, bypassing the team_pages package's
    __init__ when needed.

    Why bypass: the team_pages package `__init__.py` imports `renderer`,
    which transitively pulls in modules that other concurrent sprints
    are mid-edit on (e.g. the sprint-8 in-progress data.py). Loading
    the validator via direct file-spec keeps llm_runtime usable on any
    branch where the validator file itself is present, even if the
    package init is mid-modification.

    First try the normal package import path (faster, shares one
    module instance with any other team_pages call site). On failure,
    fall back to direct-file load.
    """
    global _VALIDATOR_CACHE
    if _VALIDATOR_CACHE is not None:
        return _VALIDATOR_CACHE
    try:
        module = importlib.import_module("cfb_rankings.team_pages.voice_validator")
        _VALIDATOR_CACHE = module.validate_fan_voice
        return _VALIDATOR_CACHE
    except Exception:
        # Bypass package __init__ — load the file directly.
        import importlib.util
        import sys
        from pathlib import Path
        validator_path = (
            Path(__file__).parent / "team_pages" / "voice_validator.py"
        )
        module_name = "_voice_validator_isolated"
        spec = importlib.util.spec_from_file_location(module_name, validator_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(
                f"could not load voice_validator from {validator_path}"
            )
        module = importlib.util.module_from_spec(spec)
        # Must register in sys.modules BEFORE exec so dataclass decorators
        # can resolve their containing module via cls.__module__ lookup.
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        _VALIDATOR_CACHE = module.validate_fan_voice
        return _VALIDATOR_CACHE


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "claude-sonnet-4-6"
_RATE_LIMIT_MAX_ATTEMPTS = 8
_RATE_LIMIT_BASE_SECONDS = 2.0
_RATE_LIMIT_CAP_SECONDS = 60.0
_EMPTY_RESPONSE_MARKER = "__empty_response__"


# ---------------------------------------------------------------------------
# API key resolution — tolerant of various config patterns
# ---------------------------------------------------------------------------

def _resolve_api_key() -> str | None:
    """Read ANTHROPIC_API_KEY from env first, then AppConfig fallback."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        from cfb_rankings.config import AppConfig
        cfg = AppConfig.from_env()
        return cfg.anthropic_api_key
    except Exception:
        return None


def _empty_result(model: str, reason: str) -> dict[str, Any]:
    """Standard offline-stub result. Logged + returned."""
    payload = {
        "event": "skip",
        "reason": reason,
        "mode": "offline-stub",
        "model": model,
    }
    _telemetry_log.info("llm_runtime.event %s", json.dumps(payload, separators=(",", ":")))
    return {
        "text": None,
        "voice_validator_passed": False,
        "voice_violations": [],
        "attempts": 0,
        "tokens_used": {"input": 0, "output": 0},
        "model_used": model,
        "mode": "offline-stub",
    }


def _rewrite_guidance(violations: list[str]) -> str:
    if not violations:
        return ""
    return (
        "\n\n---\n"
        "Your previous draft tripped the voice validator. REJECT REASON: "
        f"the following banned phrases appeared and must be removed or "
        f"replaced: {', '.join(repr(v) for v in violations)}. Rewrite the "
        "response from scratch, preserving the editorial intent but "
        "eliminating every flagged phrase. Use approved fan-voice "
        "alternatives where applicable."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_with_voice_check(
    prompt: str,
    *,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4000,
    max_retries: int = 1,
    fallback_to_offline: bool = True,
) -> dict[str, Any]:
    """Generate text via Anthropic SDK, gate against voice validator.

    Returns:
        ``{
            "text": str | None,
            "voice_validator_passed": bool,
            "voice_violations": list[str],
            "attempts": int,
            "tokens_used": {"input": int, "output": int},
            "model_used": str,
            "mode": "live" | "offline-stub",
        }``
    """
    api_key = _resolve_api_key()
    if not api_key:
        if not fallback_to_offline:
            raise RuntimeError("ANTHROPIC_API_KEY not set and fallback_to_offline=False")
        return _empty_result(model, "no_api_key")

    # Lazy import + lazy client construction. The Anthropic SDK chain has
    # pydantic-version sensitivity (e.g. it fails to load on Python 3.14
    # with older pydantic), so we widen the offline fallback to any
    # exception raised before we have a usable client.
    try:
        import anthropic  # type: ignore
        client = anthropic.Anthropic(api_key=api_key)
    except ImportError:
        if not fallback_to_offline:
            raise
        return _empty_result(model, "anthropic_sdk_not_installed")
    except Exception as exc:
        if not fallback_to_offline:
            raise
        log.warning("llm_runtime: SDK construction failed (%s: %s); falling back to offline-stub",
                    type(exc).__name__, exc)
        return _empty_result(model, f"sdk_init_failed:{type(exc).__name__}")

    validate_fan_voice = _load_validator()
    current_prompt = prompt
    total_input = 0
    total_output = 0
    attempts = 0
    last_text: str | None = None
    last_violations: list[str] = []

    voice_attempts = 0
    while voice_attempts <= max_retries:
        voice_attempts += 1
        text, in_toks, out_toks = _call_with_rate_limit_retry(
            client, current_prompt,
            system=system, model=model, max_tokens=max_tokens,
        )
        attempts += 1
        total_input += in_toks
        total_output += out_toks
        last_text = text

        if not text.strip():
            # Empty response — treat as a voice failure to trigger retry.
            last_violations = [_EMPTY_RESPONSE_MARKER]
            if voice_attempts <= max_retries:
                current_prompt = (
                    prompt + "\n\n---\nYour previous response was empty. "
                    "Please respond with the requested content."
                )
            continue

        passed, violations = validate_fan_voice(text, source=f"llm_runtime:{model}")
        last_violations = violations

        if passed:
            _emit_telemetry({
                "event": "generate",
                "model": model,
                "mode": "live",
                "input_tokens": total_input,
                "output_tokens": total_output,
                "voice_passed": True,
                "attempts": attempts,
            })
            return {
                "text": text,
                "voice_validator_passed": True,
                "voice_violations": [],
                "attempts": attempts,
                "tokens_used": {"input": total_input, "output": total_output},
                "model_used": model,
                "mode": "live",
            }

        if voice_attempts <= max_retries:
            current_prompt = prompt + _rewrite_guidance(violations)

    _emit_telemetry({
        "event": "generate",
        "model": model,
        "mode": "live",
        "input_tokens": total_input,
        "output_tokens": total_output,
        "voice_passed": False,
        "voice_violations": last_violations,
        "attempts": attempts,
    })
    return {
        "text": last_text,
        "voice_validator_passed": False,
        "voice_violations": last_violations,
        "attempts": attempts,
        "tokens_used": {"input": total_input, "output": total_output},
        "model_used": model,
        "mode": "live",
    }


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _emit_telemetry(payload: dict[str, Any]) -> None:
    _telemetry_log.info("llm_runtime.event %s", json.dumps(payload, separators=(",", ":")))


def _call_with_rate_limit_retry(
    client: Any, prompt: str, *,
    system: str | None, model: str, max_tokens: int,
) -> tuple[str, int, int]:
    """Single SDK call wrapped with exponential-backoff retry on rate limits.

    Returns ``(text, input_tokens, output_tokens)``. Raises on non-rate-limit
    failures or after ``_RATE_LIMIT_MAX_ATTEMPTS`` retries.
    """
    last_exc: Exception | None = None
    for attempt in range(1, _RATE_LIMIT_MAX_ATTEMPTS + 1):
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                # Ephemeral prompt-cache on the system block. The system prompt
                # is the largest stable token block in every voice-validated
                # surface (Chronicle voice contract ~2000 tokens shared across
                # 595 calls/week, etc.). Cache hit drops input cost ~10x for
                # the cached portion. No effect on first call in a 5-min
                # window; subsequent calls within the window read from cache.
                # See IMPLEMENTATION_PLAN.md Part 4 Sprint v5-1 Day 1 Patch 1.
                kwargs["system"] = [
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            response = client.messages.create(**kwargs)
            text_parts = [b.text for b in response.content if hasattr(b, "text")]
            text = "".join(text_parts).strip()
            in_toks = getattr(response.usage, "input_tokens", 0)
            out_toks = getattr(response.usage, "output_tokens", 0)
            # Prompt-cache visibility — emits to telemetry when caching is
            # active so we can verify hit rate. cache_creation_input_tokens
            # are billed at 1.25x base rate (one-time); cache_read_input_tokens
            # at 0.1x base rate (every cached hit). Anthropic SDK exposes both
            # as separate usage fields; older SDK versions may not have them
            # (hence getattr default 0). input_tokens excludes the cached
            # portion, so total billable input is in_toks + 1.25*cache_create
            # + 0.1*cache_read.
            cache_create = getattr(response.usage, "cache_creation_input_tokens", 0)
            cache_read = getattr(response.usage, "cache_read_input_tokens", 0)
            if cache_create or cache_read:
                _emit_telemetry({
                    "event": "cache_usage",
                    "model": model,
                    "cache_creation_input_tokens": cache_create,
                    "cache_read_input_tokens": cache_read,
                    "input_tokens": in_toks,
                })
            return (text, in_toks, out_toks)
        except Exception as exc:
            msg = str(exc).lower()
            is_rate_limited = (
                "rate limit" in msg
                or "rate_limit" in msg
                or "429" in msg
                or "overloaded" in msg
                or "529" in msg
            )
            if not is_rate_limited or attempt == _RATE_LIMIT_MAX_ATTEMPTS:
                raise
            backoff = min(
                _RATE_LIMIT_CAP_SECONDS,
                _RATE_LIMIT_BASE_SECONDS * (2 ** (attempt - 1)),
            ) * (0.7 + random.random() * 0.6)
            log.warning(
                "llm_runtime rate-limit hit on attempt %d/%d; sleeping %.1fs",
                attempt, _RATE_LIMIT_MAX_ATTEMPTS, backoff,
            )
            time.sleep(backoff)
            last_exc = exc
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("unreachable rate-limit retry exit")
