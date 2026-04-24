"""JSONL logger for LLM invocations.

Every subprocess call to ``claude`` CLI (Max subscription headless) and
every Anthropic SDK call writes a single line to
``output/_logs/llm_usage_{date}.jsonl`` with subcommand, model, tokens,
duration. Enables post-sprint budget analysis.

Lightweight — ~15 LOC of core logic + path resolution.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _log_dir() -> Path:
    d = Path("output") / "_logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def append_llm_usage(
    *,
    subcommand: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_s: float,
    extra: dict[str, object] | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    path = _log_dir() / f"llm_usage_{now.strftime('%Y-%m-%d')}.jsonl"
    record = {
        "ts": now.isoformat(),
        "subcommand": subcommand,
        "model": model,
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": int(completion_tokens),
        "total_tokens": int(prompt_tokens) + int(completion_tokens),
        "duration_s": round(float(duration_s), 3),
    }
    if extra:
        record.update(extra)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
