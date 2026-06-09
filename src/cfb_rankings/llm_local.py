"""Local LLM routing for Anthropic-backed product surfaces.

Provides a drop-in alternative to ``generate_with_voice_check()`` that routes
to a locally running llama-server (or any OpenAI-compatible endpoint) instead
of the Anthropic API.  Callers that already branch on ``result["mode"]`` get
local acceleration with zero structural changes.

Activation
----------
Set ``LOCAL_LLM_URL`` to your local endpoint base URL (no trailing slash):

    export LOCAL_LLM_URL=http://localhost:8001/v1    # llama-server (recommended)
    export LOCAL_LLM_URL=http://localhost:11434/v1   # Ollama OpenAI-compat layer

Optional env vars:

    LOCAL_LLM_MODEL    Override the model name sent in the request.
                       Defaults to the model_id passed by the caller, or
                       "local" if the endpoint ignores the field.
    LOCAL_LLM_TIMEOUT  HTTP timeout in seconds. Default: 120.

Return contract
---------------
Every function returns a dict compatible with ``generate_with_voice_check()``::

    {
        "text":         str | None,     # generated text; None on failure
        "mode":         "local"         # or "offline-stub" on failure
                      | "offline-stub",
        "model_used":   str,            # model name echoed from response
        "tokens_used":  {               # from usage field in response
            "input":  int,
            "output": int,
        },
        "call_id":      str,            # random hex for log correlation
        "voice_validator_passed": True, # always True — no voice check locally
        "voice_violations": [],
        "attempts": 1,
    }

Thread safety
-------------
All functions are stateless — safe to call from multiple threads concurrently.
The ``requests.Session`` is created per call (no shared state).

Usage example
-------------
::

    from cfb_rankings.llm_local import is_local_enabled, local_generate

    if is_local_enabled():
        result = local_generate(prompt, system=system_prompt, max_tokens=256)
    else:
        result = generate_with_voice_check(prompt, system=system_prompt,
                                           model=MODEL, max_tokens=256,
                                           fallback_to_offline=True)
    if result["text"]:
        labels = _parse_labels(result["text"], batch_size)
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import time
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment-variable config
# ---------------------------------------------------------------------------
_ENV_URL = "LOCAL_LLM_URL"
_ENV_MODEL = "LOCAL_LLM_MODEL"
_ENV_TIMEOUT = "LOCAL_LLM_TIMEOUT"

_DEFAULT_TIMEOUT = 120  # seconds — local inference can be slow on first token


def is_local_enabled() -> bool:
    """True when LOCAL_LLM_URL is set to a non-empty value."""
    return bool(os.environ.get(_ENV_URL, "").strip())


def _base_url() -> str:
    url = os.environ.get(_ENV_URL, "").rstrip("/")
    if not url:
        raise RuntimeError(
            "LOCAL_LLM_URL is not set — call is_local_enabled() before local_generate()"
        )
    return url


def _is_ollama() -> bool:
    """True when LOCAL_LLM_URL points at an Ollama daemon.

    Ollama detection: URL contains port 11434 OR the /v1 suffix has a
    sibling /api route reachable at the same host.  The simpler heuristic
    — port 11434 — covers 99% of installs and avoids an extra HTTP round-trip.
    Users on a non-standard port can set LOCAL_LLM_OLLAMA=1 to force it.
    """
    if os.environ.get("LOCAL_LLM_OLLAMA", "").strip() == "1":
        return True
    url = os.environ.get(_ENV_URL, "")
    return ":11434" in url


def _ollama_host() -> str:
    """Return the bare Ollama host URL (strips /v1 suffix if present)."""
    url = _base_url()
    # Strip the OpenAI-compat /v1 suffix so we can reach /api/chat
    if url.endswith("/v1"):
        url = url[:-3]
    return url


def _timeout() -> int:
    return int(os.environ.get(_ENV_TIMEOUT, str(_DEFAULT_TIMEOUT)))


def _model_name(requested: str | None) -> str:
    """Resolve the model name to send. Env var wins, then caller's value, then 'local'."""
    env_model = os.environ.get(_ENV_MODEL, "").strip()
    return env_model or requested or "local"


def _stub_result(call_id: str) -> dict[str, Any]:
    return {
        "text": None,
        "mode": "offline-stub",
        "model_used": "local-unavailable",
        "tokens_used": {"input": 0, "output": 0},
        "call_id": call_id,
        "voice_validator_passed": True,
        "voice_violations": [],
        "attempts": 1,
    }


# ---------------------------------------------------------------------------
# Core HTTP helper
# ---------------------------------------------------------------------------

def _strip_think_blocks(text: str) -> str:
    """Remove <think>...</think> reasoning blocks from model output.

    Qwen3 and similar thinking-mode models emit these before the actual
    response. They're invisible to users but consume output tokens. Strip
    them so callers receive only the usable response text.
    """
    import re
    # Remove complete think blocks (greedy to handle nested content)
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
    return text.strip()


def _chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str | None,
    max_tokens: int,
    temperature: float = 0.7,
    response_format: dict[str, Any] | None = None,
    call_id: str,
) -> dict[str, Any]:
    """POST to the appropriate local endpoint and return the normalised result.

    Routing:
    - Ollama (port 11434 or LOCAL_LLM_OLLAMA=1): uses ``/api/chat`` with
      ``think: false``.  This is Ollama's native endpoint — it properly
      suppresses Qwen3 chain-of-thought generation so thinking tokens don't
      consume the ``max_tokens`` budget.  The ``/v1/chat/completions`` compat
      layer doesn't honour ``think: false`` and routes thinking tokens to a
      separate ``reasoning`` field while still counting them toward the cap,
      which causes empty ``content`` at small token budgets.
    - llama-server / other OpenAI-compat: uses ``/v1/chat/completions``.
      Strips residual ``<think>...</think>`` blocks post-hoc.

    Raises ``RuntimeError`` on HTTP or JSON errors — caller wraps in try/except.
    """
    try:
        import requests as _requests
    except ImportError as exc:
        raise RuntimeError("requests library not installed") from exc

    model_name = _model_name(model)
    t0 = time.monotonic()

    if _is_ollama():
        # -----------------------------------------------------------------
        # Ollama native /api/chat — supports think:false properly
        # -----------------------------------------------------------------
        url = _ollama_host() + "/api/chat"
        payload: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "think": False,   # suppresses Qwen3 reasoning tokens entirely
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        # Ollama /api/chat doesn't support response_format — inject schema
        # instruction into system message when JSON is requested.
        if response_format:
            schema_hint = (
                "\n\nYou MUST respond with valid JSON only. No explanation. "
                "No markdown. No preamble."
            )
            if response_format.get("type") == "json_schema":
                import json as _json
                schema = response_format["json_schema"].get("schema", {})
                schema_hint += f" Schema: {_json.dumps(schema)}"
            # Append to last system message or prepend a new one
            if messages and messages[0]["role"] == "system":
                payload["messages"] = [
                    {**messages[0], "content": messages[0]["content"] + schema_hint},
                    *messages[1:],
                ]
            else:
                payload["messages"] = [
                    {"role": "system", "content": schema_hint.strip()},
                    *messages,
                ]

        resp = _requests.post(url, json=payload, timeout=_timeout(),
                              headers={"Content-Type": "application/json"})
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        if resp.status_code != 200:
            raise RuntimeError(f"Ollama /api/chat HTTP {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        raw_text = (data.get("message") or {}).get("content") or ""
        text = _strip_think_blocks(raw_text)
        in_toks = int(data.get("prompt_eval_count") or 0)
        out_toks = int(data.get("eval_count") or 0)
        finish_reason = "stop" if data.get("done") else "length"

    else:
        # -----------------------------------------------------------------
        # OpenAI-compat /v1/chat/completions — llama-server et al.
        # -----------------------------------------------------------------
        url = _base_url() + "/chat/completions"
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        if response_format:
            payload["response_format"] = response_format

        resp = _requests.post(url, json=payload, timeout=_timeout(),
                              headers={"Content-Type": "application/json"})
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        if resp.status_code != 200:
            raise RuntimeError(f"llama-server HTTP {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        choice = data["choices"][0]
        raw_text = choice["message"]["content"] or ""
        text = _strip_think_blocks(raw_text)
        finish_reason = choice.get("finish_reason", "")
        usage = data.get("usage") or {}
        in_toks = int(usage.get("prompt_tokens", 0))
        out_toks = int(usage.get("completion_tokens", 0))

    model_used = model_name  # Ollama /api/chat echoes it in data["model"]

    log.debug(
        "local_generate call_id=%s model=%s in=%d out=%d ms=%d finish=%s ollama=%s",
        call_id, model_used, in_toks, out_toks, elapsed_ms, finish_reason, _is_ollama(),
    )

    return {
        "text": text if text else None,
        "mode": "local",
        "model_used": model_used,
        "tokens_used": {"input": in_toks, "output": out_toks},
        "call_id": call_id,
        "voice_validator_passed": True,
        "voice_violations": [],
        "attempts": 1,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def local_generate(
    prompt: str,
    *,
    system: str = "",
    model: str | None = None,
    max_tokens: int = 512,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Generate free-form text via the local endpoint.

    Drop-in for ``generate_with_voice_check()`` on text-output tasks
    (sentiment labels, theme extraction, source summaries, etc.).

    Returns the standard result dict — mode is "local" on success or
    "offline-stub" if the server is unreachable / returns an error.
    """
    call_id = secrets.token_hex(4)
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        return _chat_completion(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            call_id=call_id,
        )
    except Exception as exc:
        log.warning("local_generate call_id=%s failed: %s", call_id, exc)
        return _stub_result(call_id)


def local_generate_json(
    prompt: str,
    *,
    system: str = "",
    model: str | None = None,
    max_tokens: int = 512,
    json_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a JSON-constrained response via the local endpoint.

    Uses ``response_format`` for structured decoding when the server supports
    it (llama-server ≥ b3447 with grammar support, Ollama ≥ 0.3.0).

    ``json_schema``: a JSON Schema dict.  When provided, requests strict schema
    adherence via::

        response_format = {
            "type": "json_schema",
            "json_schema": {"name": "output", "strict": True, "schema": json_schema}
        }

    When ``json_schema`` is None, uses ``response_format = {"type": "json_object"}``
    (free-form JSON, server ensures valid JSON but not schema adherence).

    Returns the standard result dict — ``result["text"]`` is the raw JSON string.
    Callers parse it with ``json.loads(result["text"])``.
    """
    call_id = secrets.token_hex(4)
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    if json_schema is not None:
        response_format: dict[str, Any] = {
            "type": "json_schema",
            "json_schema": {
                "name": "output",
                "strict": True,
                "schema": json_schema,
            },
        }
    else:
        response_format = {"type": "json_object"}

    try:
        return _chat_completion(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=0.0,  # JSON tasks: deterministic
            response_format=response_format,
            call_id=call_id,
        )
    except Exception as exc:
        log.warning("local_generate_json call_id=%s failed: %s", call_id, exc)
        return _stub_result(call_id)


__all__ = ["is_local_enabled", "local_generate", "local_generate_json"]
