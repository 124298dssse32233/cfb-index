"""LLM usage telemetry — dual writer (JSONL + SQL).

Every Anthropic SDK call and quality_loop iteration flows through here.
Two destinations, both best-effort:

1. ``output/_logs/llm_usage_{date}.jsonl`` — durable append-only file
   for post-sprint budget analysis. Survives DB resets.

2. ``llm_usage_log`` SQL table — fast-query mirror used by:
   - circuit_state.get_24h_spend() for per-surface auto-disable
   - the /admin queue page for spend-by-surface display
   - the end-of-session cost-telemetry SQL the user runs to dial
     Pattern E → C or C → B if a surface is hot

The SQL mirror was specified by migration 20260525_15 but the writer
was never extended — fixed in hotfix-10 (PR #65). The JSONL writer
predates the SQL table and remains the primary durable record;
the SQL write is wrapped in a try/except and a failure here never
blocks the LLM call (telemetry must never crash a workflow).

Lightweight — the SQL connection is opened fresh per call (one round
trip, ~1 ms on local SQLite) so callers don't have to thread a
Database handle through every code path. For high-frequency batch
loops where this overhead matters, callers can pass an explicit
``sqlite_conn`` to reuse a connection.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


log = logging.getLogger(__name__)


def _log_dir() -> Path:
    d = Path("output") / "_logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


# Standard Anthropic pricing in USD per million tokens. Mirrors the
# table in llm_runtime.MODEL_RATES but expressed per-MTok so the math
# is easier to read here. Used when callers don't pass an explicit
# ``cost_usd`` argument.
_COST_PER_MTOK_USD: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0,
                          "cache_read": 0.30, "cache_write_5m": 3.75},
    "claude-opus-4-7": {"input": 15.0, "output": 75.0,
                        "cache_read": 1.50, "cache_write_5m": 18.75},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0,
                                  "cache_read": 0.08, "cache_write_5m": 1.0},
    "template-v1": {"input": 0.0, "output": 0.0,
                    "cache_read": 0.0, "cache_write_5m": 0.0},
}


def _estimate_cost_usd(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> float:
    """Best-effort cost in USD when the caller didn't pre-compute it.

    Conservative: unknown models bill at Sonnet rates (the budget
    ceiling should still fire correctly).
    """
    rates = _COST_PER_MTOK_USD.get(
        model, _COST_PER_MTOK_USD["claude-sonnet-4-6"]
    )
    return (
        prompt_tokens * rates["input"]
        + completion_tokens * rates["output"]
        + cache_read_tokens * rates["cache_read"]
        + cache_creation_tokens * rates["cache_write_5m"]
    ) / 1_000_000


def _db_path_from_env() -> Optional[str]:
    """Resolve the SQLite file path from DATABASE_URL.

    Supports the project's standard form ``sqlite:///./cfb_rankings.db``
    and the absolute form ``sqlite:////abs/path.db``. Returns None when
    the URL is not a sqlite:// form (Postgres etc.) so the caller skips
    the SQL mirror gracefully.
    """
    url = os.getenv("DATABASE_URL", "sqlite:///./cfb_rankings.db")
    if not url.startswith("sqlite:///"):
        return None
    return url[len("sqlite:///") :]


def _iso_week(now: datetime) -> str:
    iso = now.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def append_llm_usage(
    *,
    subcommand: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_s: float,
    extra: dict[str, object] | None = None,
    cost_usd: float | None = None,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
    sqlite_conn: Optional[sqlite3.Connection] = None,
) -> None:
    """Append one LLM-call telemetry row to JSONL + SQL table.

    Backwards-compatible signature — every existing call site keeps
    working; the new keyword args (``cost_usd``, ``cache_*_tokens``,
    ``sqlite_conn``) all default. When ``cost_usd`` is None, the
    function estimates it from ``model`` and the token counts via
    the Anthropic public per-MTok rates.

    Parameters in ``extra`` that this function recognizes and maps to
    SQL columns:
        - ``surface``        → llm_usage_log.surface
        - ``loop_pattern``   → loop_pattern
        - ``critic_roles_used`` (list[str]) → critic_role (first entry)
        - ``critic_scores`` (list[float]) → critic_score (first entry)
        - ``revise_count``   → revise_count
        - ``fell_back`` (bool) → fell_back (cast to 0/1)
        - ``fallback_reason``/``final_score`` (informational only,
                              kept in JSONL only)
        - ``prompt_version`` → prompt_version
    """
    now = datetime.now(timezone.utc)
    extra_dict: dict[str, Any] = dict(extra or {})

    # ── JSONL write (primary durable record; pre-existing behavior) ──
    record = {
        "ts": now.isoformat(),
        "subcommand": subcommand,
        "model": model,
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": int(completion_tokens),
        "total_tokens": int(prompt_tokens) + int(completion_tokens),
        "duration_s": round(float(duration_s), 3),
    }
    record.update(extra_dict)

    if cost_usd is None:
        cost_usd = _estimate_cost_usd(
            model,
            int(prompt_tokens),
            int(completion_tokens),
            int(cache_read_tokens),
            int(cache_creation_tokens),
        )
    record["cost_usd"] = round(float(cost_usd), 6)

    try:
        path = _log_dir() / f"llm_usage_{now.strftime('%Y-%m-%d')}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception as exc:  # disk full, perm denied, etc. Don't crash.
        log.warning("append_llm_usage: JSONL write failed: %s", exc)

    # ── SQL mirror (hotfix-10) ──
    #
    # llm_usage_log was created by migration 20260525_15 specifically
    # for fast SUM() aggregates per surface. The writer was specified
    # in the migration's docstring but never landed — this is that fix.
    try:
        conn = sqlite_conn
        own_conn = False
        if conn is None:
            db_path = _db_path_from_env()
            if not db_path:
                # Non-sqlite DB or unparseable URL: skip SQL mirror.
                return
            if not Path(db_path).exists():
                # CLI invoked before init-db — JSONL still wrote, fine.
                return
            conn = sqlite3.connect(db_path)
            own_conn = True

        # Pick surface from extra.surface first; fall back to extracting
        # the leading dotted prefix of subcommand (e.g.
        # "quality_loop.C.edition_cover" → "edition_cover"). If the
        # subcommand isn't dotted, use it verbatim.
        surface_val = extra_dict.get("surface")
        if not surface_val:
            parts = subcommand.split(".")
            surface_val = parts[-1] if len(parts) > 1 else subcommand
        surface_val = str(surface_val)

        critic_role_val: Optional[str] = None
        critic_score_val: Optional[float] = None
        roles = extra_dict.get("critic_roles_used")
        if isinstance(roles, (list, tuple)) and roles:
            critic_role_val = str(roles[0])
        scores = extra_dict.get("critic_scores")
        if isinstance(scores, (list, tuple)) and scores:
            try:
                critic_score_val = float(scores[0])
            except (TypeError, ValueError):
                critic_score_val = None

        fell_back_raw = extra_dict.get("fell_back", False)
        try:
            fell_back_val = 1 if fell_back_raw else 0
        except Exception:
            fell_back_val = 0

        conn.execute(
            """
            INSERT INTO llm_usage_log (
                call_id, invoked_at_utc, iso_week,
                surface, model_id, prompt_version,
                input_tokens, output_tokens,
                cache_read_input_tokens, cache_creation_input_tokens,
                cost_usd, latency_ms, success, error_kind,
                loop_pattern, critic_role, critic_score,
                revise_count, fell_back, notes
            ) VALUES (
                :call_id, :invoked_at_utc, :iso_week,
                :surface, :model_id, :prompt_version,
                :input_tokens, :output_tokens,
                :cache_read_input_tokens, :cache_creation_input_tokens,
                :cost_usd, :latency_ms, :success, :error_kind,
                :loop_pattern, :critic_role, :critic_score,
                :revise_count, :fell_back, :notes
            )
            """,
            {
                "call_id": str(extra_dict.get("call_id") or uuid.uuid4()),
                "invoked_at_utc": now.isoformat(sep=" ", timespec="seconds"),
                "iso_week": _iso_week(now),
                "surface": surface_val,
                "model_id": str(model),
                "prompt_version": (
                    str(extra_dict["prompt_version"])
                    if extra_dict.get("prompt_version") is not None else None
                ),
                "input_tokens": int(prompt_tokens),
                "output_tokens": int(completion_tokens),
                "cache_read_input_tokens": int(cache_read_tokens),
                "cache_creation_input_tokens": int(cache_creation_tokens),
                "cost_usd": float(cost_usd),
                "latency_ms": int(round(float(duration_s) * 1000.0)),
                "success": 0 if fell_back_val and not extra_dict.get("text") else 1,
                "error_kind": (
                    str(extra_dict["error_kind"])
                    if extra_dict.get("error_kind") else None
                ),
                "loop_pattern": (
                    str(extra_dict["loop_pattern"])
                    if extra_dict.get("loop_pattern") else None
                ),
                "critic_role": critic_role_val,
                "critic_score": critic_score_val,
                "revise_count": int(extra_dict.get("revise_count") or 0),
                "fell_back": fell_back_val,
                "notes": (
                    str(extra_dict["fallback_reason"])
                    if extra_dict.get("fallback_reason") else None
                ),
            },
        )
        if own_conn:
            conn.commit()
            conn.close()
    except Exception as exc:
        # Telemetry must never crash a loop. Log dir/file edge cases,
        # SQLite locks, missing table (migration not yet applied) — all
        # swallowed. The JSONL write above is the durable record.
        log.warning("append_llm_usage: SQL mirror failed: %s", exc)
