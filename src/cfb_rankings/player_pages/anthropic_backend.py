"""AnthropicBackend — the SONNET API writer for the live top-50 Story Cards.

Doc 59 §14.6 (D-1, LOCKED 2026-06-12): the live top-50 (most-talked-about ∪
importance, post eligibility.filter_active) are written by **Sonnet via the
Anthropic API**, run automatically by the box at each editorial beat. This module
is the writer-agnostic backend the narrator routes that cohort to. Everything
below the top-50 keeps the local Ollama ``mistral`` path
(``story_card_narrator._writer_generate``); the long tail stays deterministic.

CONTRACT (mirrors ``_writer_generate`` so the narrator's backend seam is clean):
  - ``generate(prompt) -> str | None`` — takes the SAME ``system\\n\\nuser`` prompt
    the narrator already builds, splits it back into system + user for the
    Messages API, and returns the raw JSON string the writer schema constrains.
    Returns ``None`` on ANY failure (API down / rate-limited / over-budget /
    auth / parse) so the narrator falls through its ladder (Sonnet → mistral →
    deterministic → LKG, doc 59 §12). NEVER raises into the render path.
  - The five card fields are constrained via ``output_config.format`` json_schema
    (the same five keys the Ollama ``format`` param enforces) so the narrator's
    existing ``_parse_prose_json`` parses the result unchanged.

MODEL: ``claude-sonnet-4-6`` (doc 59 D-1 — Kevin chose Sonnet, NOT Opus: the
confident-compiler quality is more than enough at ~1/5 the cost). Sonnet 4.6
still accepts ``temperature`` (unlike Opus 4.7/4.8), so editorial prose gets the
narrator's warm 0.4. ``max_tokens`` is bounded to the card budget.

KEY HANDLING (doc 59 D-1 (b), §15 side-find): ``ANTHROPIC_API_KEY`` is read from
``config.AppConfig.anthropic_api_key`` / the ``ANTHROPIC_API_KEY`` env var. It is
NEVER printed, echoed, or logged. The pipeline loads ``.env`` via
``_pipeline_common.ps1``; this module also tolerates a key present only in the
ambient env.

BUDGET CAP (doc 59 §14.6 step 4 / D-1 cost): a configurable monthly token-or-
dollar cap. Spend is tracked in a small JSON ledger
(``data/sonnet_writer_budget.json``) keyed by ``YYYY-MM``; once the month's
estimated dollar spend exceeds the cap, ``generate`` returns ``None`` WITHOUT
calling the API (so the narrator routes the card to ``mistral``). Default cap
``$30/mo`` (well above the ~$6-12/mo D-1 estimate — a guardrail, not a throttle).
Override via ``CFB_INDEX_SONNET_MONTHLY_CAP_USD``.

LOUD-ON-FALLBACK (doc 59 §12): this module does not itself alert; it records
per-card ``prose_source`` through the narrator's return dict and exposes
:func:`summarize_prose_sources` so the beat job can fail loudly when the Sonnet
share of the top-50 falls below a floor for a non-thin reason.

NO NEW HARD DEP: prefers the installed ``anthropic`` SDK; if it is somehow
absent, falls back to a raw ``httpx`` POST to ``/v1/messages`` (httpx is already
a dependency of the local writer path). Adds nothing to requirements.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import threading
from pathlib import Path
from typing import Any, Optional

# Doc 59 D-1: Sonnet, not Opus. Sonnet 4.6 keeps temperature + output_config.format.
SONNET_MODEL_ID = os.environ.get("CFB_INDEX_SONNET_MODEL") or "claude-sonnet-4-6"

# Card-writer generation budget — match the narrator's editorial ergonomics.
_SONNET_MAX_TOKENS = int(os.environ.get("CFB_INDEX_SONNET_MAX_TOKENS", "700"))
_SONNET_TEMPERATURE = float(os.environ.get("CFB_INDEX_SONNET_TEMPERATURE", "0.4"))
_SONNET_TIMEOUT_S = float(os.environ.get("CFB_INDEX_SONNET_TIMEOUT", "60"))

# Sonnet 4.6 list price (doc: claude-api skill, 2026): $3/M in, $15/M out.
_PRICE_IN_PER_TOKEN = 3.0 / 1_000_000
_PRICE_OUT_PER_TOKEN = 15.0 / 1_000_000

# Monthly hard budget cap (USD). Default a generous $30/mo guardrail; the D-1
# realistic spend is ~$6-12/mo. Over cap ⇒ route to mistral (doc 59 §14.6 step 4).
_DEFAULT_MONTHLY_CAP_USD = float(os.environ.get("CFB_INDEX_SONNET_MONTHLY_CAP_USD", "30"))

# Budget ledger location (small JSON, per-YYYY-MM token + dollar totals).
_BUDGET_LEDGER_PATH = Path(
    os.environ.get(
        "CFB_INDEX_SONNET_BUDGET_LEDGER",
        str(Path(__file__).resolve().parents[3] / "data" / "sonnet_writer_budget.json"),
    )
)

# The five card fields — the SAME schema the Ollama writer constrains, expressed
# as a json_schema for output_config.format. additionalProperties:false is
# required by the structured-outputs contract.
_SONNET_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "logline": {"type": "string"},
        "dominant_take": {"type": "string"},
        "minority_take": {"type": ["string", "null"]},
        "body": {"type": "string"},
        "kicker": {"type": ["string", "null"]},
    },
    "required": ["logline", "dominant_take", "body"],
    "additionalProperties": False,
}

_LEDGER_LOCK = threading.Lock()


# ===========================================================================
# Prompt split — the narrator hands us "<system>\n\nuser..." (one blob, the same
# string it feeds Ollama). The Messages API wants system + user separated. The
# system half is everything up to the first blank-line gap that precedes the
# per-player <player> block; we split on the FIRST "\n\n" that is followed by the
# user payload. The narrator joins exactly as `f"{system}\n\n{user}"`, so a split
# on the first double-newline reconstructs the two halves faithfully. NEVER
# raises (degrades to whole-prompt-as-user).
# ===========================================================================
def _split_system_user(prompt: str) -> tuple[str, str]:
    try:
        idx = prompt.find("\n\n")
        if idx <= 0:
            return "", prompt
        system = prompt[:idx].strip()
        user = prompt[idx + 2 :].strip()
        if not user:
            return "", prompt
        return system, user
    except Exception:
        return "", prompt


# ===========================================================================
# Budget ledger — per-month token + dollar tally. Read/modify/write under a lock.
# Best-effort: any IO failure degrades to "assume spendable" (the cap is a
# guardrail, not a correctness gate — a missing ledger must not block the writer).
# ===========================================================================
def _month_key(now: _dt.datetime | None = None) -> str:
    d = now or _dt.datetime.utcnow()
    return f"{d.year:04d}-{d.month:02d}"


def _load_ledger() -> dict[str, Any]:
    try:
        if _BUDGET_LEDGER_PATH.exists():
            with _BUDGET_LEDGER_PATH.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def _month_spend_usd(ledger: dict[str, Any], month: str) -> float:
    try:
        row = ledger.get(month) or {}
        return float(row.get("usd") or 0.0)
    except Exception:
        return 0.0


def _record_spend(month: str, tokens_in: int, tokens_out: int, usd: float) -> None:
    """Add one call's usage to the month's ledger row. Best-effort, never raises."""
    try:
        with _LEDGER_LOCK:
            ledger = _load_ledger()
            row = ledger.get(month) or {"calls": 0, "tokens_in": 0, "tokens_out": 0, "usd": 0.0}
            row["calls"] = int(row.get("calls", 0)) + 1
            row["tokens_in"] = int(row.get("tokens_in", 0)) + int(tokens_in)
            row["tokens_out"] = int(row.get("tokens_out", 0)) + int(tokens_out)
            row["usd"] = round(float(row.get("usd", 0.0)) + float(usd), 6)
            ledger[month] = row
            try:
                _BUDGET_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            tmp = _BUDGET_LEDGER_PATH.with_suffix(".json.tmp")
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(ledger, fh, indent=2, sort_keys=True)
            tmp.replace(_BUDGET_LEDGER_PATH)
    except Exception:
        pass


def _estimate_cost_usd(tokens_in: int, tokens_out: int) -> float:
    return (tokens_in * _PRICE_IN_PER_TOKEN) + (tokens_out * _PRICE_OUT_PER_TOKEN)


# ===========================================================================
# Key resolution — config.AppConfig.anthropic_api_key first (it loads .env), then
# the ambient env. NEVER returns/logs the value anywhere but the request header.
# ===========================================================================
def _resolve_api_key() -> str | None:
    try:
        from cfb_rankings.config import AppConfig

        cfg = AppConfig.from_env()
        key = getattr(cfg, "anthropic_api_key", None)
        if key:
            return str(key)
    except Exception:
        pass
    key = os.environ.get("ANTHROPIC_API_KEY")
    return str(key) if key else None


class AnthropicBackend:
    """Sonnet-via-API writer. ``generate(prompt) -> str | None`` (raw JSON or None).

    Construct once per batch (cheap; lazy-imports the SDK on first call). The
    instance caches the resolved key + monthly cap and exposes ``last_error`` /
    ``last_skip_reason`` for the narrator/beat job to record a fallback reason
    WITHOUT ever surfacing the key.
    """

    def __init__(
        self,
        *,
        model_id: str = SONNET_MODEL_ID,
        max_tokens: int = _SONNET_MAX_TOKENS,
        temperature: float = _SONNET_TEMPERATURE,
        timeout_s: float = _SONNET_TIMEOUT_S,
        monthly_cap_usd: float = _DEFAULT_MONTHLY_CAP_USD,
        api_key: Optional[str] = None,
    ) -> None:
        self.model_id = model_id
        self.max_tokens = int(max_tokens)
        self.temperature = float(temperature)
        self.timeout_s = float(timeout_s)
        self.monthly_cap_usd = float(monthly_cap_usd)
        self._api_key = api_key or _resolve_api_key()
        self.last_error: str | None = None
        self.last_skip_reason: str | None = None

    # ---- availability + budget gates ------------------------------------
    def available(self) -> bool:
        """True iff a key is present AND the month is under the budget cap.

        Used by the narrator to decide whether to even attempt Sonnet (so a
        no-key or over-budget batch routes straight to mistral with a recorded
        reason — never a silent crash). NEVER raises."""
        if not self._api_key:
            self.last_skip_reason = "no-api-key"
            return False
        try:
            month = _month_key()
            spent = _month_spend_usd(_load_ledger(), month)
            if spent >= self.monthly_cap_usd:
                self.last_skip_reason = "over-budget"
                return False
        except Exception:
            # Ledger trouble must not block the writer (cap is a guardrail).
            pass
        self.last_skip_reason = None
        return True

    # ---- the writer call -------------------------------------------------
    def generate(self, prompt: str) -> str | None:
        """Run ONE Sonnet card-writer call. Returns the raw JSON string or None.

        Mirrors ``_writer_generate``'s contract exactly so the narrator's seam is
        a drop-in: any failure (no key / over-budget / API down / rate-limited /
        timeout / auth / parse) returns ``None`` and records ``last_error`` or
        ``last_skip_reason``; NEVER raises. On success records spend in the
        monthly ledger and returns the model's JSON text for the narrator's
        existing ``_parse_prose_json``."""
        self.last_error = None
        if not self.available():
            return None

        system, user = _split_system_user(prompt)
        try:
            text, tokens_in, tokens_out = self._call_messages(system, user)
        except Exception as exc:  # never raise into the render path
            # Record the CLASS of error, never the key or full payload.
            self.last_error = type(exc).__name__
            return None

        if not text:
            self.last_error = "empty-response"
            return None

        # Record spend (best-effort) so the monthly cap holds across the batch.
        try:
            usd = _estimate_cost_usd(tokens_in, tokens_out)
            _record_spend(_month_key(), tokens_in, tokens_out, usd)
        except Exception:
            pass
        return text

    # ---- SDK / raw-HTTP transport ---------------------------------------
    def _call_messages(self, system: str, user: str) -> tuple[str, int, int]:
        """Return (json_text, tokens_in, tokens_out). Raises on transport error.

        Prefers the installed ``anthropic`` SDK; falls back to raw ``httpx`` only
        if the SDK is unavailable (adds no new hard dep). Both paths constrain the
        five card fields via ``output_config.format`` json_schema so the response
        text is the JSON the narrator parses."""
        try:
            import anthropic  # type: ignore
        except Exception:
            return self._call_messages_httpx(system, user)

        client = anthropic.Anthropic(api_key=self._api_key, timeout=self.timeout_s)
        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": user}],
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": _SONNET_JSON_SCHEMA,
                }
            },
        }
        if system:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)

        # output_config.format guarantees the first text block is the JSON object.
        text = ""
        for block in getattr(resp, "content", []) or []:
            if getattr(block, "type", None) == "text":
                text = getattr(block, "text", "") or ""
                if text:
                    break
        usage = getattr(resp, "usage", None)
        tokens_in = int(getattr(usage, "input_tokens", 0) or 0)
        tokens_out = int(getattr(usage, "output_tokens", 0) or 0)
        return text, tokens_in, tokens_out

    def _call_messages_httpx(self, system: str, user: str) -> tuple[str, int, int]:
        """Raw /v1/messages POST (SDK-absent fallback). Raises on transport error."""
        import httpx

        body: dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": user}],
            "output_config": {
                "format": {"type": "json_schema", "schema": _SONNET_JSON_SCHEMA}
            },
        }
        if system:
            body["system"] = system
        headers = {
            "x-api-key": self._api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        with httpx.Client(timeout=self.timeout_s) as client:
            resp = client.post(
                "https://api.anthropic.com/v1/messages", json=body, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
        text = ""
        for block in data.get("content") or []:
            if block.get("type") == "text":
                text = block.get("text") or ""
                if text:
                    break
        usage = data.get("usage") or {}
        tokens_in = int(usage.get("input_tokens") or 0)
        tokens_out = int(usage.get("output_tokens") or 0)
        return text, tokens_in, tokens_out


# ===========================================================================
# LOUD-ON-FALLBACK summary (doc 59 §12). Given the per-card prose_source values
# the narrator recorded for a batch, return counts + the Sonnet share so a beat
# job can alert when the Sonnet share of the top-50 falls below a floor for a
# non-thin reason. Wiring the actual alert is the caller's job (stubbed here);
# this just computes the signal.
# ===========================================================================
def summarize_prose_sources(
    prose_sources: list[str | None],
    *,
    sonnet_floor: float = 0.60,
) -> dict[str, Any]:
    """Counts by prose_source + the Sonnet share, with a below-floor flag.

    ``prose_sources`` is the list of per-card ``prose_source`` strings
    ('sonnet'|'mistral'|'deterministic'|'lkg'|None). ``alert`` is True when the
    Sonnet share of the COHORT falls below ``sonnet_floor`` (default 0.60, doc 59
    §12) — the caller decides whether the shortfall is a legitimate thin-packet
    case or a silent full-batch degrade worth an issue. NEVER raises."""
    counts: dict[str, int] = {}
    total = 0
    for src in prose_sources or []:
        key = str(src or "none")
        counts[key] = counts.get(key, 0) + 1
        total += 1
    sonnet = counts.get("sonnet", 0)
    share = (sonnet / total) if total else 0.0
    return {
        "counts": counts,
        "total": total,
        "sonnet": sonnet,
        "sonnet_share": round(share, 4),
        "sonnet_floor": sonnet_floor,
        "alert": bool(total) and share < sonnet_floor,
    }


__all__ = [
    "AnthropicBackend",
    "SONNET_MODEL_ID",
    "summarize_prose_sources",
]
