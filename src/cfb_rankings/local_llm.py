"""Local-LLM provider — OpenAI-compatible endpoint (Ollama / LM Studio / vLLM / LiteLLM).

Drop-in shim for the **Tier-A** (bulk / structured) half of the hybrid plan in
``docs/research/local-llm-stack-2026-06.md``. It mirrors the return contract of
``llm_runtime.generate_with_voice_check`` EXACTLY, so existing callers
(sentiment classifier, theme extraction, critic passes) need *zero* changes —
they simply get routed here when local routing is enabled.

Routing is **OFF by default.** ``llm_runtime.generate_with_voice_check``
delegates here only when ``CFB_LOCAL_LLM=1`` AND the requested Anthropic model
is in the local-eligible allowlist (default: the Haiku tier). Tier-B editorial
(Opus / Sonnet) is never routed local. See ``_maybe_local_model`` in
``llm_runtime.py``.

Built for "runs reliably without a human in the loop" (no A/B gate):
  - **temperature 0 by default** — deterministic classification/extraction.
  - **<think>…</think> stripping** — Qwen3 / DeepSeek-R1 and friends are hybrid
    reasoning models that emit a thinking block by default; we drop it so the
    payload is clean JSON. A ``/no_think`` hint is also appended to the system
    prompt by default (honored by Qwen3, ignored by others).
  - **optional schema-constrained output** — pass ``response_format`` and it is
    forwarded to the server's ``response_format`` (Ollama maps this to its
    grammar-constrained ``format``). If a server rejects it, we transparently
    retry without it, so the call never hard-fails on an unsupported field.
  - **graceful degradation** — if the local server is unreachable the call
    returns an offline-stub (same shape as a missing API key), so a down server
    never crashes a batch job.

Transport: a plain ``requests`` POST to ``{base}/chat/completions`` (the
OpenAI-compatible Chat Completions API that every local server exposes). No new
dependency — ``requests`` is already in ``pyproject.toml``.

Environment variables:
    CFB_LOCAL_LLM            "1"/"true"/"yes"/"on" to enable routing (read in llm_runtime).
    CFB_LOCAL_LLM_MODEL      local model tag (default "qwen3:8b").
    CFB_LOCAL_LLM_BASE_URL   default "http://localhost:11434/v1" (Ollama's OpenAI endpoint).
    CFB_LOCAL_LLM_API_KEY    default "ollama" (dummy; local servers ignore it).
    CFB_LOCAL_LLM_TIMEOUT    per-request seconds (default 120).
    CFB_LOCAL_LLM_TEMPERATURE  sampling temperature (default 0 — deterministic).
    CFB_LOCAL_LLM_NO_THINK   "1" (default) appends "/no_think" to the system prompt.
    CFB_LOCAL_LLM_ANTHROPIC_MODELS  comma list of Anthropic model ids eligible
                             for local routing (default: any id containing "haiku").
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

log = logging.getLogger(__name__)

_THINK_BLOCK = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


def _resolve_local_config() -> dict[str, Any]:
    """Read the local-endpoint settings from env. Re-read each call so a batch
    job / smoke check can override CFB_LOCAL_LLM_BASE_URL at runtime."""
    return {
        "base_url": os.environ.get("CFB_LOCAL_LLM_BASE_URL", "http://localhost:11434/v1"),
        "api_key": os.environ.get("CFB_LOCAL_LLM_API_KEY", "ollama"),
        "timeout": float(os.environ.get("CFB_LOCAL_LLM_TIMEOUT", "120")),
        "temperature": float(os.environ.get("CFB_LOCAL_LLM_TEMPERATURE", "0")),
        "no_think": _truthy(os.environ.get("CFB_LOCAL_LLM_NO_THINK", "1")),
    }


def _offline_stub(model: str, reason: str) -> dict[str, Any]:
    """Same shape llm_runtime uses when there's no API key. Callers already
    branch on ``mode == "offline-stub"`` and skip — so a down local server is
    handled identically to a missing cloud key (safe, resumable)."""
    return {
        "text": None,
        "voice_validator_passed": False,
        "voice_violations": [],
        "attempts": 0,
        "tokens_used": {"input": 0, "output": 0},
        "model_used": model,
        "mode": "offline-stub",
    }


def _strip_reasoning(text: str) -> str:
    """Drop <think>…</think> blocks emitted by hybrid reasoning models."""
    cleaned = _THINK_BLOCK.sub("", text)
    # Defensive: an unclosed <think> with no closing tag — drop everything up
    # to the first '{' or '[' if present (JSON payloads), else the raw tail.
    if "<think>" in cleaned.lower() and "</think>" not in cleaned.lower():
        for ch in ("{", "["):
            idx = cleaned.find(ch)
            if idx != -1:
                cleaned = cleaned[idx:]
                break
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------

def _chat_completion(
    cfg: dict[str, Any],
    model: str,
    prompt: str,
    system: str | None,
    max_tokens: int,
    response_format: dict[str, Any] | None,
) -> tuple[str, int, int]:
    """One OpenAI-compatible /chat/completions call. Returns (text, in_tok, out_tok).

    ``response_format`` (if given) is forwarded so the server can grammar-
    constrain JSON. If the server rejects that field (HTTP 400/422), we retry
    once without it. Raises on transport / other HTTP error so the caller can
    fall back to offline-stub.
    """
    import requests  # already a project dependency

    if cfg["no_think"] and system:
        system = system + "\n/no_think"
    elif cfg["no_think"]:
        system = "/no_think"

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    base_payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": cfg["temperature"],
        "stream": False,
    }
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }

    for attempt_payload in ([{**base_payload, "response_format": response_format}]
                            if response_format else []) + [base_payload]:
        resp = requests.post(url, headers=headers, json=attempt_payload, timeout=cfg["timeout"])
        if resp.status_code in (400, 422) and "response_format" in attempt_payload:
            log.warning("local_llm: server rejected response_format (%s); retrying without it",
                        resp.status_code)
            continue
        resp.raise_for_status()
        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content") or ""
        usage = data.get("usage") or {}
        return (
            _strip_reasoning(text),
            int(usage.get("prompt_tokens") or 0),
            int(usage.get("completion_tokens") or 0),
        )

    # Unreachable in practice (the no-response_format payload always runs), but
    # keeps type-checkers happy.
    raise RuntimeError("local_llm: no payload variant succeeded")


# ---------------------------------------------------------------------------
# Public API — mirrors llm_runtime.generate_with_voice_check's contract
# ---------------------------------------------------------------------------

def generate_local(
    prompt: str,
    *,
    system: str | None = None,
    model: str = "qwen3:8b",
    max_tokens: int = 4000,
    max_retries: int = 1,
    fallback_to_offline: bool = True,
    response_format: dict[str, Any] | None = None,
    anthropic_model: str | None = None,
) -> dict[str, Any]:
    """Generate text from a local OpenAI-compatible model, gated by the same
    voice validator as the cloud path, returning the identical result dict.

    ``response_format`` (optional) — an OpenAI-style structured-output spec,
    e.g. ``{"type": "json_object"}`` or a full ``{"type": "json_schema", ...}``;
    forwarded to the server for grammar-constrained JSON when supported.
    ``anthropic_model`` is the original Anthropic model id this call would have
    used (telemetry only). ``model`` is the LOCAL tag actually served.
    """
    import uuid

    call_id = uuid.uuid4().hex
    cfg = _resolve_local_config()
    model_used = f"local/{model}"

    # Lazy imports from llm_runtime to avoid an import cycle at module load.
    from cfb_rankings.llm_runtime import (
        _EMPTY_RESPONSE_MARKER,
        _emit_telemetry,
        _load_validator,
        _rewrite_guidance,
    )

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
        try:
            text, in_toks, out_toks = _chat_completion(
                cfg, model, current_prompt, system, max_tokens, response_format,
            )
        except Exception as exc:  # transport / HTTP / JSON — degrade gracefully
            if not fallback_to_offline:
                raise
            log.warning(
                "local_llm: request to %s failed (%s: %s); returning offline-stub",
                cfg["base_url"], type(exc).__name__, exc,
            )
            stub = _offline_stub(model_used, f"local_unreachable:{type(exc).__name__}")
            stub["call_id"] = call_id
            return stub

        attempts += 1
        total_input += in_toks
        total_output += out_toks
        last_text = text

        if not text.strip():
            last_violations = [_EMPTY_RESPONSE_MARKER]
            if voice_attempts <= max_retries:
                current_prompt = (
                    prompt + "\n\n---\nYour previous response was empty. "
                    "Please respond with the requested content."
                )
            continue

        passed, violations = validate_fan_voice(text, source=f"local_llm:{model}")
        last_violations = violations

        if passed:
            _emit_telemetry({
                "event": "generate",
                "model": model_used,
                "anthropic_model": anthropic_model,
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
                "model_used": model_used,
                "mode": "live",
                "call_id": call_id,
            }

        if voice_attempts <= max_retries:
            current_prompt = prompt + _rewrite_guidance(violations)

    _emit_telemetry({
        "event": "generate",
        "model": model_used,
        "anthropic_model": anthropic_model,
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
        "model_used": model_used,
        "mode": "live",
        "call_id": call_id,
    }


def health_check() -> dict[str, Any]:
    """Quick reachability probe for the local endpoint. Returns
    ``{"ok": bool, "base_url": str, "models": [...] | None, "error": str | None}``.

    Hits the OpenAI-compatible ``/models`` listing. Handy for the smoke check
    and for a startup sanity check on the box."""
    import requests

    cfg = _resolve_local_config()
    url = cfg["base_url"].rstrip("/") + "/models"
    try:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {cfg['api_key']}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        models = [m.get("id") for m in (data.get("data") or []) if isinstance(m, dict)]
        return {"ok": True, "base_url": cfg["base_url"], "models": models, "error": None}
    except Exception as exc:
        return {
            "ok": False,
            "base_url": cfg["base_url"],
            "models": None,
            "error": f"{type(exc).__name__}: {exc}",
        }
