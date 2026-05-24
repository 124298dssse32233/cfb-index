"""Chronicle observability — Langfuse + DCGM + ntfy.sh integration.

All telemetry is OPTIONAL — system runs without observability stack installed.
Every function is wrapped in try/except so a missing dep or unreachable host
never crashes the generation pipeline.

Configuration via env vars:
    LANGFUSE_HOST          e.g. http://localhost:3000
    LANGFUSE_PUBLIC_KEY    pk-lf-...
    LANGFUSE_SECRET_KEY    sk-lf-...
    NTFY_TOPIC             e.g. cfb-chronicle-alerts
    NTFY_HOST              default https://ntfy.sh
    DCGM_PROMETHEUS_URL    for GPU metrics polling
    CHRONICLE_OBS_ENABLED  set to "1" to enable (default: disabled)
"""
from __future__ import annotations

import contextlib
import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator, Literal

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_langfuse_client: Any = None  # set by init_langfuse()
_obs_enabled: bool = False     # set by init_langfuse()


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _langfuse_configured() -> bool:
    return bool(_get_env("LANGFUSE_PUBLIC_KEY") and _get_env("LANGFUSE_SECRET_KEY"))


def _ntfy_configured() -> bool:
    return bool(_get_env("NTFY_TOPIC"))


def _obs_globally_enabled() -> bool:
    return _get_env("CHRONICLE_OBS_ENABLED", "0") == "1"


# ---------------------------------------------------------------------------
# Langfuse init
# ---------------------------------------------------------------------------


def init_langfuse(
    host: str | None = None,
    public_key: str | None = None,
    secret_key: str | None = None,
    enabled: bool | None = None,
) -> bool:
    """Initialize the Langfuse client. Call once at pipeline startup.

    Parameters override env vars when provided. Returns True if successfully
    initialized, False if disabled or package unavailable.

    Thread safety: this function modifies module-level state; call it from
    the main thread before spawning workers.
    """
    global _langfuse_client, _obs_enabled

    should_enable = enabled if enabled is not None else _obs_globally_enabled()
    if not should_enable:
        log.debug("init_langfuse: observability disabled (CHRONICLE_OBS_ENABLED != 1)")
        _obs_enabled = False
        return False

    pk = public_key or _get_env("LANGFUSE_PUBLIC_KEY")
    sk = secret_key or _get_env("LANGFUSE_SECRET_KEY")
    h = host or _get_env("LANGFUSE_HOST", "http://localhost:3000")

    if not pk or not sk:
        log.warning("init_langfuse: LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set")
        _obs_enabled = False
        return False

    try:
        from langfuse import Langfuse  # type: ignore[import-not-found]

        _langfuse_client = Langfuse(
            public_key=pk,
            secret_key=sk,
            host=h,
        )
        _obs_enabled = True
        log.info("init_langfuse: Langfuse client initialized (host=%s)", h)
        return True
    except ImportError:
        log.debug("init_langfuse: langfuse package not installed — no-op")
        _obs_enabled = False
        return False
    except Exception as exc:
        log.warning("init_langfuse: initialization failed (%s) — obs disabled", exc)
        _obs_enabled = False
        return False


# ---------------------------------------------------------------------------
# Generation span context manager
# ---------------------------------------------------------------------------


@dataclass
class GenerationSpan:
    """Holds references to an active Langfuse generation span.

    Do not instantiate directly — use trace_generation() context manager.
    """

    name: str
    trace_id: str | None
    start_time: float = field(default_factory=time.monotonic)
    _span: Any = field(default=None, repr=False)


@contextmanager
def trace_generation(
    name: str,
    trace_id: str | None = None,
    **attrs: Any,
) -> Generator[GenerationSpan, None, None]:
    """Context manager for a generation span.

    Usage::

        with trace_generation("chronicle_card_gen", trace_id=cache_key,
                              entity_slug="cam-ward") as span:
            card = generate_card(...)

    When Langfuse is unavailable or disabled, the context manager is a no-op
    but still yields a GenerationSpan for uniform calling code.
    """
    span = GenerationSpan(name=name, trace_id=trace_id)
    lf_generation = None

    if _obs_enabled and _langfuse_client is not None:
        try:
            lf_trace = _langfuse_client.trace(
                id=trace_id or f"{name}-{int(time.time())}",
                name=name,
                metadata=attrs,
            )
            lf_generation = lf_trace.generation(
                name=name,
                metadata=attrs,
            )
            span._span = lf_generation
        except Exception as exc:
            log.debug("trace_generation: span creation failed (%s)", exc)

    try:
        yield span
    except Exception:
        if lf_generation is not None:
            with contextlib.suppress(Exception):
                lf_generation.end(level="ERROR")
        raise

    if lf_generation is not None:
        with contextlib.suppress(Exception):
            elapsed_ms = int((time.monotonic() - span.start_time) * 1000)
            lf_generation.end(
                metadata={"elapsed_ms": elapsed_ms},
            )


# ---------------------------------------------------------------------------
# Metric logging
# ---------------------------------------------------------------------------


def log_metric(
    metric_name: str,
    value: float,
    trace_id: str | None = None,
    tags: dict[str, str] | None = None,
) -> None:
    """Write a gauge metric to Langfuse (as a score) and/or structured log.

    Always writes to the Python logger at DEBUG level so metrics are
    captured by any log aggregator even without the Langfuse stack.
    """
    log.debug(
        "chronicle_metric name=%s value=%s trace_id=%s tags=%s",
        metric_name,
        value,
        trace_id,
        tags,
    )

    if not _obs_enabled or _langfuse_client is None:
        return

    if trace_id is None:
        return

    try:
        _langfuse_client.score(
            trace_id=trace_id,
            name=metric_name,
            value=value,
            comment=str(tags) if tags else None,
        )
    except Exception as exc:
        log.debug("log_metric: Langfuse score write failed (%s)", exc)


# ---------------------------------------------------------------------------
# ntfy.sh alerts
# ---------------------------------------------------------------------------


AlertLevel = Literal["info", "warning", "error", "critical"]

# ntfy.sh priority mapping
_NTFY_PRIORITY: dict[str, str] = {
    "info": "low",
    "warning": "default",
    "error": "high",
    "critical": "urgent",
}


def alert(
    level: AlertLevel,
    title: str,
    message: str,
    tags: list[str] | None = None,
) -> bool:
    """Push an alert to ntfy.sh.

    Returns True if the push succeeded, False otherwise (including when ntfy
    is not configured). Never raises.
    """
    if not _ntfy_configured():
        log.debug("alert: NTFY_TOPIC not set — alert suppressed (level=%s title=%r)", level, title)
        return False

    topic = _get_env("NTFY_TOPIC")
    host = _get_env("NTFY_HOST", "https://ntfy.sh").rstrip("/")
    url = f"{host}/{topic}"
    priority = _NTFY_PRIORITY.get(level, "default")

    headers = {
        "Title": title,
        "Priority": priority,
        "Tags": ",".join(tags) if tags else level,
    }

    try:
        import urllib.request

        data = message.encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            success = 200 <= resp.status < 300
        if not success:
            log.warning("alert: ntfy.sh returned status %d", resp.status)
        return success
    except Exception as exc:
        log.warning("alert: ntfy.sh push failed (%s)", exc)
        return False


# ---------------------------------------------------------------------------
# GPU metrics (DCGM via Prometheus)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GpuMetrics:
    """GPU utilization snapshot from DCGM-Exporter Prometheus endpoint."""

    gpu_utilization_pct: float | None
    memory_used_mb: float | None
    memory_total_mb: float | None
    temperature_c: float | None
    power_draw_w: float | None
    source_url: str


def poll_gpu_metrics() -> GpuMetrics | None:
    """Poll DCGM-Exporter Prometheus endpoint for GPU metrics.

    Returns None if DCGM_PROMETHEUS_URL is not set or the endpoint is
    unreachable. Never raises.
    """
    url = _get_env("DCGM_PROMETHEUS_URL")
    if not url:
        return None

    try:
        import urllib.request

        with urllib.request.urlopen(url, timeout=3) as resp:
            body = resp.read().decode("utf-8")

        metrics = _parse_prometheus_text(body)
        return GpuMetrics(
            gpu_utilization_pct=metrics.get("DCGM_FI_DEV_GPU_UTIL"),
            memory_used_mb=metrics.get("DCGM_FI_DEV_FB_USED"),
            memory_total_mb=metrics.get("DCGM_FI_DEV_FB_FREE"),
            temperature_c=metrics.get("DCGM_FI_DEV_GPU_TEMP"),
            power_draw_w=metrics.get("DCGM_FI_DEV_POWER_USAGE"),
            source_url=url,
        )
    except Exception as exc:
        log.debug("poll_gpu_metrics: failed to fetch DCGM metrics (%s)", exc)
        return None


def _parse_prometheus_text(body: str) -> dict[str, float]:
    """Parse Prometheus text format into a {metric_name: value} dict.

    Handles the simple "metric_name{labels} value timestamp" format.
    """
    result: dict[str, float] = {}
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            # Split off labels block and value
            if "{" in line:
                name = line[: line.index("{")]
                rest = line[line.rindex("}") + 1 :].strip()
            else:
                parts = line.split()
                name = parts[0]
                rest = parts[1] if len(parts) > 1 else ""
            value_str = rest.split()[0] if rest else ""
            if value_str:
                result[name] = float(value_str)
        except (ValueError, IndexError):
            continue
    return result


# ---------------------------------------------------------------------------
# Convenience: record one complete card generation event
# ---------------------------------------------------------------------------


def record_card_generation(
    *,
    entity_slug: str,
    card_type: str,
    cache_key: str,
    card_text: str,
    factscore: float | None = None,
    voice_score: float | None = None,
    quality_score: float | None = None,
    slop_fingerprint: float | None = None,
    verdict: str | None = None,
    model_id: str | None = None,
    latency_ms: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> bool:
    """Convenience wrapper: log one complete card-generation event to Langfuse.

    Records a trace + optional scores. Returns True if anything was written.
    No-ops gracefully when Langfuse is unavailable.
    """
    if not _obs_enabled or _langfuse_client is None:
        return False

    try:
        trace = _langfuse_client.trace(
            id=cache_key,
            name="chronicle_card_generation",
            metadata={
                "entity_slug": entity_slug,
                "card_type": card_type,
                "verdict": verdict,
                "model_id": model_id,
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "char_count": len(card_text),
            },
        )

        # Log generation span
        trace.generation(
            name="card_text",
            model=model_id or "unknown",
            input=f"entity_slug={entity_slug} card_type={card_type}",
            output=card_text[:500],  # truncate for storage
            usage={
                "input": input_tokens or 0,
                "output": output_tokens or 0,
            },
        )

        # Log eval scores
        if factscore is not None:
            _langfuse_client.score(trace_id=cache_key, name="factscore", value=factscore)
        if voice_score is not None:
            _langfuse_client.score(trace_id=cache_key, name="voice_fidelity", value=voice_score)
        if quality_score is not None:
            _langfuse_client.score(trace_id=cache_key, name="editorial_quality", value=quality_score)
        if slop_fingerprint is not None:
            _langfuse_client.score(trace_id=cache_key, name="slop_fingerprint", value=slop_fingerprint)

        _langfuse_client.flush()
        return True

    except Exception as exc:
        log.warning("record_card_generation: Langfuse write failed (%s)", exc)
        return False


# ---------------------------------------------------------------------------
# Flush / shutdown
# ---------------------------------------------------------------------------


def flush() -> None:
    """Flush all pending Langfuse events. Call before process exit."""
    if _langfuse_client is None:
        return
    with contextlib.suppress(Exception):
        _langfuse_client.flush()
