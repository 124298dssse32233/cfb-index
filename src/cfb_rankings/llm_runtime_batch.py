"""Batched LLM runtime — peer to ``llm_runtime.py``.

Wraps Anthropic's Message Batches API (50% input+output discount) and
stacks it with 1-hour prompt caching (~90% off cached input tokens, GA
Jan 2026) to drive the effective per-token rate down to ~5% of standard
on shared-context workloads.

Cost math at a glance (per Anthropic published pricing as of 2026-05):

    standard      = 1.00x  input
    + batch       = 0.50x  input + output
    + cache_read  = 0.10x  per cached token (after one-time 1.25x write)
    => combined   ≈ 0.05x  on the cached prefix tokens

For the Chronicle workload (17 profiled teams × shared editorial voice
contract + shared evidence block per week), the cached prefix dominates
input cost. Combined savings are roughly:
    - 50% on output (Batch API discount alone)
    - 95% on shared input (Batch × cache_read)
    - 50% on per-job tail (team-specific prompt segment)

This module is ADDITIVE — it does NOT replace ``llm_runtime.py``. The
synchronous path stays in place for:
  - Interactive single-team runs (CLI ergonomics)
  - Critique-loop iterations inside ``quality_loop.py`` (need per-call
    feedback to converge)
  - Any low-N call that's faster than batch poll overhead

Public API:

    BatchJob       - dataclass: one unit of work in a batch
    BatchResult    - dataclass: parsed result for one job
    submit_batch(jobs, ...) -> list[BatchResult]
    submit_batch_offline_safe(jobs, fallback_per_job, ...) -> list[BatchResult]

Contracts:

1. **Never throws on missing SDK / API key when offline-safe.** Returns
   offline-stub-shaped results, same pattern as ``llm_runtime``.
2. **Voice-validator runs on every result before return.** Same gate as
   the synchronous path. Caller never has to validate manually.
3. **Telemetry per job.** Emits a JSON line to
   ``cfb_rankings.llm_runtime.telemetry`` for each successful job with
   the same field shape as the sync path, plus the ``mode='batch'``
   marker and ``custom_id`` for correlation.
4. **Polls with backoff.** Hard timeout configurable (default 4h). Most
   batches return in minutes per Anthropic SLA, well within weekly
   cron windows.
5. **Per-job partial failure tolerated.** The SDK returns per-job
   results — some can succeed and some fail. Failed jobs come back
   with ``succeeded=False, error=<message>``; the rest of the batch is
   still returned.
"""
from __future__ import annotations

import importlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional

log = logging.getLogger(__name__)
_telemetry_log = logging.getLogger("cfb_rankings.llm_runtime.telemetry")


# Lazy validator load — mirrors llm_runtime._load_validator. Kept local so
# this module is importable independently when only batch path is needed.
_VALIDATOR_CACHE: Optional[Callable[..., tuple[bool, list[str]]]] = None


def _load_validator() -> Callable[..., tuple[bool, list[str]]]:
    """Lazy-import the voice validator (mirrors ``llm_runtime._load_validator``).

    First tries the normal package import; on failure (e.g. team_pages
    package init mid-edit), falls back to a direct-file import bypass.
    """
    global _VALIDATOR_CACHE
    if _VALIDATOR_CACHE is not None:
        return _VALIDATOR_CACHE
    try:
        module = importlib.import_module("cfb_rankings.team_pages.voice_validator")
        _VALIDATOR_CACHE = module.validate_fan_voice
        return _VALIDATOR_CACHE
    except Exception:
        import importlib.util
        import sys
        from pathlib import Path
        validator_path = (
            Path(__file__).parent / "team_pages" / "voice_validator.py"
        )
        module_name = "_voice_validator_batch_isolated"
        spec = importlib.util.spec_from_file_location(module_name, validator_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(
                f"could not load voice_validator from {validator_path}"
            )
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        _VALIDATOR_CACHE = module.validate_fan_voice
        return _VALIDATOR_CACHE


# ---------------------------------------------------------------------------
# Dataclasses (public contract surface)
# ---------------------------------------------------------------------------

@dataclass
class BatchJob:
    """One unit of work in a batch — the params + a custom_id for tracking.

    ``custom_id`` must be globally unique within the batch. The SDK keys
    per-job results on this id so callers can correlate back to source
    rows (e.g. ``f"chronicle-{team_slug}"``).

    ``system_blocks`` is a list of content blocks — each a dict with
    ``type='text'`` and optionally ``cache_control`` to mark the block
    for 1-hour ephemeral caching. Put the shared, stable, high-token
    text here.

    ``messages`` is the standard Anthropic messages array; put the
    per-job user-turn payload here.
    """
    custom_id: str
    system_blocks: list[dict[str, Any]]
    messages: list[dict[str, Any]]
    model: str
    max_tokens: int
    # Optional extra metadata the caller wants threaded back via the
    # BatchResult. Not sent to the API. Useful for re-attaching original
    # row context after results return out of order.
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult:
    """Parsed per-job result returned by ``submit_batch``."""
    custom_id: str
    text: str | None
    voice_validator_passed: bool
    voice_violations: list[str]
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    model_used: str
    succeeded: bool
    mode: str = "batch"  # 'batch' | 'offline-stub'
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_api_key() -> str | None:
    """Same fallback chain as ``llm_runtime._resolve_api_key``."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        from cfb_rankings.config import AppConfig
        cfg = AppConfig.from_env()
        return cfg.anthropic_api_key
    except Exception:
        return None


def _emit_telemetry(payload: dict[str, Any]) -> None:
    _telemetry_log.info(
        "llm_runtime_batch.event %s",
        json.dumps(payload, separators=(",", ":")),
    )


def _offline_stub_result(job: BatchJob, reason: str) -> BatchResult:
    return BatchResult(
        custom_id=job.custom_id,
        text=None,
        voice_validator_passed=False,
        voice_violations=[],
        input_tokens=0,
        output_tokens=0,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
        model_used=job.model,
        succeeded=False,
        mode="offline-stub",
        error=reason,
        metadata=dict(job.metadata),
    )


def _extract_text(result_message: Any) -> str:
    """Extract concatenated text from a Message-shaped object/dict."""
    # The SDK returns a Message object whose .content is a list of blocks.
    # In our test harness it can also be a plain dict.
    content = (
        getattr(result_message, "content", None)
        if not isinstance(result_message, dict)
        else result_message.get("content")
    )
    if not content:
        return ""
    parts: list[str] = []
    for block in content:
        # Both attr-style and dict-style blocks supported.
        text = (
            getattr(block, "text", None)
            if not isinstance(block, dict)
            else block.get("text")
        )
        if text:
            parts.append(text)
    return "".join(parts).strip()


def _extract_usage(result_message: Any) -> dict[str, int]:
    """Pull token counts from a Message-shaped object/dict, defaulting to 0."""
    usage = (
        getattr(result_message, "usage", None)
        if not isinstance(result_message, dict)
        else result_message.get("usage")
    )
    if usage is None:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
    def _read(name: str) -> int:
        if isinstance(usage, dict):
            return int(usage.get(name, 0) or 0)
        return int(getattr(usage, name, 0) or 0)
    return {
        "input_tokens": _read("input_tokens"),
        "output_tokens": _read("output_tokens"),
        "cache_creation_input_tokens": _read("cache_creation_input_tokens"),
        "cache_read_input_tokens": _read("cache_read_input_tokens"),
    }


def _build_request(job: BatchJob) -> dict[str, Any]:
    """Translate a BatchJob into the SDK request dict for batch submission."""
    params: dict[str, Any] = {
        "model": job.model,
        "max_tokens": job.max_tokens,
        "messages": list(job.messages),
    }
    if job.system_blocks:
        # Pass system content blocks as-is — caller is responsible for
        # cache_control placement on the shared/stable blocks.
        params["system"] = list(job.system_blocks)
    return {
        "custom_id": job.custom_id,
        "params": params,
    }


# ---------------------------------------------------------------------------
# Public API — submit_batch
# ---------------------------------------------------------------------------

def submit_batch(
    jobs: list[BatchJob],
    *,
    poll_interval_seconds: int = 30,
    timeout_seconds: int = 14400,
    on_progress: Callable[[int, int], None] | None = None,
    run_voice_validator: bool = True,
) -> list[BatchResult]:
    """Submit a batch, poll until done, run voice_validator on each result.

    Args:
        jobs: list of BatchJob — each must have a unique custom_id.
        poll_interval_seconds: how often to check batch status (default 30s).
        timeout_seconds: hard cap on total poll time (default 4h).
            Anthropic SLA is 24h but typical completion is minutes.
        on_progress: optional callback ``(completed, total)`` per poll.
        run_voice_validator: if True (default), every result text is
            passed through the validator and the per-job
            ``voice_validator_passed`` + ``voice_violations`` fields are
            populated. Set to False only when running structured-output
            jobs where the validator's editorial gate is inappropriate.

    Returns:
        list[BatchResult] in the same order as ``jobs``. Failed jobs
        come back with ``succeeded=False`` and ``error`` populated.

    Raises:
        ImportError if the anthropic SDK is missing.
        RuntimeError if no API key is set.
        TimeoutError if the batch doesn't complete within
            ``timeout_seconds``.

    Use ``submit_batch_offline_safe`` to suppress those errors and fall
    back to offline-stub results for the whole batch.
    """
    if not jobs:
        return []

    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    # Lazy import — same widened-exception pattern as llm_runtime so older
    # pydantic on Python 3.14 doesn't take the whole batch path down.
    import anthropic  # type: ignore

    client = anthropic.Anthropic(api_key=api_key)
    requests = [_build_request(j) for j in jobs]

    _emit_telemetry({
        "event": "batch_submit",
        "job_count": len(jobs),
        "models": sorted({j.model for j in jobs}),
    })

    batch = client.messages.batches.create(requests=requests)
    batch_id = getattr(batch, "id", None) or (
        batch.get("id") if isinstance(batch, dict) else None
    )
    if not batch_id:
        raise RuntimeError(
            f"batch submit returned no id; got {type(batch).__name__}"
        )

    log.info(
        "llm_runtime_batch: submitted batch=%s jobs=%d",
        batch_id, len(jobs),
    )

    start = time.monotonic()
    completed_batch = None
    while True:
        elapsed = time.monotonic() - start
        if elapsed > timeout_seconds:
            raise TimeoutError(
                f"batch {batch_id} did not complete within "
                f"{timeout_seconds}s (poll interval {poll_interval_seconds}s)"
            )
        status_obj = client.messages.batches.retrieve(batch_id)
        status = (
            getattr(status_obj, "processing_status", None)
            or (status_obj.get("processing_status") if isinstance(status_obj, dict) else None)
        )
        counts = (
            getattr(status_obj, "request_counts", None)
            or (status_obj.get("request_counts") if isinstance(status_obj, dict) else None)
        )
        if on_progress and counts is not None:
            try:
                done = sum([
                    int(getattr(counts, "succeeded", 0) or 0)
                    if not isinstance(counts, dict)
                    else int(counts.get("succeeded", 0) or 0),
                    int(getattr(counts, "errored", 0) or 0)
                    if not isinstance(counts, dict)
                    else int(counts.get("errored", 0) or 0),
                    int(getattr(counts, "canceled", 0) or 0)
                    if not isinstance(counts, dict)
                    else int(counts.get("canceled", 0) or 0),
                    int(getattr(counts, "expired", 0) or 0)
                    if not isinstance(counts, dict)
                    else int(counts.get("expired", 0) or 0),
                ])
                on_progress(done, len(jobs))
            except Exception:
                pass

        if status == "ended":
            completed_batch = status_obj
            break

        time.sleep(poll_interval_seconds)

    # Stream per-job results.
    try:
        results_iter = client.messages.batches.results(batch_id)
    except Exception as exc:
        raise RuntimeError(f"failed to stream batch results: {exc}") from exc

    validate_fan_voice = _load_validator() if run_voice_validator else None
    by_id: dict[str, BatchResult] = {}
    jobs_by_id = {j.custom_id: j for j in jobs}

    for entry in results_iter:
        custom_id = (
            getattr(entry, "custom_id", None)
            or (entry.get("custom_id") if isinstance(entry, dict) else None)
        )
        if not custom_id:
            log.warning("llm_runtime_batch: result entry missing custom_id; skipping")
            continue
        job = jobs_by_id.get(custom_id)
        if job is None:
            log.warning(
                "llm_runtime_batch: result for unknown custom_id=%s; skipping",
                custom_id,
            )
            continue

        result = (
            getattr(entry, "result", None)
            or (entry.get("result") if isinstance(entry, dict) else None)
        )
        result_type = (
            getattr(result, "type", None)
            or (result.get("type") if isinstance(result, dict) else None)
        ) if result is not None else None

        if result_type == "succeeded":
            message = (
                getattr(result, "message", None)
                or (result.get("message") if isinstance(result, dict) else None)
            )
            text = _extract_text(message)
            usage = _extract_usage(message)
            passed = True
            violations: list[str] = []
            if run_voice_validator and validate_fan_voice is not None and text:
                passed, violations = validate_fan_voice(
                    text, source=f"llm_runtime_batch:{job.model}"
                )
            elif run_voice_validator and not text:
                passed = False
                violations = ["__empty_response__"]
            model_used = (
                getattr(message, "model", job.model)
                if not isinstance(message, dict)
                else message.get("model", job.model)
            )
            br = BatchResult(
                custom_id=custom_id,
                text=text or None,
                voice_validator_passed=passed,
                voice_violations=violations,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                cache_creation_input_tokens=usage["cache_creation_input_tokens"],
                cache_read_input_tokens=usage["cache_read_input_tokens"],
                model_used=model_used,
                succeeded=True,
                mode="batch",
                metadata=dict(job.metadata),
            )
            _emit_telemetry({
                "event": "batch_job",
                "custom_id": custom_id,
                "model": model_used,
                "mode": "batch",
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "cache_creation_input_tokens": usage["cache_creation_input_tokens"],
                "cache_read_input_tokens": usage["cache_read_input_tokens"],
                "voice_passed": passed,
            })
            by_id[custom_id] = br
        else:
            # errored / canceled / expired — surface the message.
            error_obj = (
                getattr(result, "error", None)
                or (result.get("error") if isinstance(result, dict) else None)
            ) if result is not None else None
            error_msg: str
            if error_obj is None:
                error_msg = f"batch job ended with type={result_type!r}"
            elif isinstance(error_obj, dict):
                error_msg = error_obj.get("message") or str(error_obj)
            else:
                error_msg = (
                    getattr(error_obj, "message", None) or str(error_obj)
                )
            br = BatchResult(
                custom_id=custom_id,
                text=None,
                voice_validator_passed=False,
                voice_violations=[],
                input_tokens=0,
                output_tokens=0,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
                model_used=job.model,
                succeeded=False,
                mode="batch",
                error=error_msg,
                metadata=dict(job.metadata),
            )
            _emit_telemetry({
                "event": "batch_job_failed",
                "custom_id": custom_id,
                "model": job.model,
                "error": error_msg,
                "result_type": result_type,
            })
            by_id[custom_id] = br

    # Preserve the input order; fill missing slots with an explicit failure
    # marker (e.g. the SDK dropped a result line).
    out: list[BatchResult] = []
    for j in jobs:
        if j.custom_id in by_id:
            out.append(by_id[j.custom_id])
        else:
            out.append(BatchResult(
                custom_id=j.custom_id,
                text=None,
                voice_validator_passed=False,
                voice_violations=[],
                input_tokens=0,
                output_tokens=0,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
                model_used=j.model,
                succeeded=False,
                mode="batch",
                error="result missing from batch output stream",
                metadata=dict(j.metadata),
            ))

    succeeded = sum(1 for r in out if r.succeeded)
    _emit_telemetry({
        "event": "batch_complete",
        "batch_id": batch_id,
        "job_count": len(jobs),
        "succeeded": succeeded,
        "failed": len(jobs) - succeeded,
        "elapsed_seconds": round(time.monotonic() - start, 1),
    })
    return out


# ---------------------------------------------------------------------------
# Public API — submit_batch_offline_safe
# ---------------------------------------------------------------------------

def submit_batch_offline_safe(
    jobs: list[BatchJob],
    fallback_per_job: Callable[[BatchJob], str | None] | None = None,
    **kwargs: Any,
) -> list[BatchResult]:
    """Wrapper that returns offline-stub-shaped results when:
      - anthropic SDK is missing
      - ANTHROPIC_API_KEY is not set
      - batch submission fails before any job runs

    Matches ``llm_runtime``'s graceful-degrade pattern. Callers can pass
    a ``fallback_per_job`` to fill in deterministic offline text on a
    per-job basis (e.g. a template card); when provided, the resulting
    BatchResult will have ``text=<fallback>``, ``mode='offline-stub'``,
    ``succeeded=False`` so callers can still distinguish degraded output.

    Errors that occur AFTER submission (e.g. timeout while polling) are
    re-raised — at that point we've already committed real spend and
    silent fallback would mask a partial-failure scenario the caller
    needs to know about.
    """
    def _all_offline(reason: str) -> list[BatchResult]:
        out: list[BatchResult] = []
        for j in jobs:
            stub = _offline_stub_result(j, reason)
            if fallback_per_job is not None:
                try:
                    text = fallback_per_job(j)
                    if text:
                        stub.text = text
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "fallback_per_job raised for %s (%s: %s); leaving text=None",
                        j.custom_id, type(exc).__name__, exc,
                    )
            out.append(stub)
        _emit_telemetry({
            "event": "batch_offline",
            "reason": reason,
            "job_count": len(jobs),
        })
        return out

    if not jobs:
        return []

    api_key = _resolve_api_key()
    if not api_key:
        return _all_offline("no_api_key")

    try:
        import anthropic  # noqa: F401
    except ImportError:
        return _all_offline("anthropic_sdk_not_installed")
    except Exception as exc:  # noqa: BLE001
        return _all_offline(f"sdk_import_failed:{type(exc).__name__}")

    try:
        return submit_batch(jobs, **kwargs)
    except TimeoutError:
        # Caller needs to know — partial spend already committed.
        raise
    except Exception as exc:  # noqa: BLE001
        # If submission fails BEFORE any job ran (e.g. auth error,
        # network down, malformed request), degrade gracefully.
        log.warning(
            "submit_batch_offline_safe: batch submission failed "
            "(%s: %s); falling back to offline-stub for %d jobs",
            type(exc).__name__, exc, len(jobs),
        )
        return _all_offline(f"submit_failed:{type(exc).__name__}")
