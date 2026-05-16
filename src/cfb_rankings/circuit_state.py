"""Per-surface 24-hour rolling cost ceiling + auto-disable state.

Sprint v5-3 owner Interrupt 2 deliverable. This module is the persistent
counterpart to ``quality_loop._CIRCUIT_STATE`` (which holds only the
weekly Rung-3 in-memory counter). Where the in-memory counter resets at
process exit, this module's state lives in two SQLite tables:

* ``surface_spend_events`` — append-only log of ``(surface, ts_utc,
  cost_usd, note)`` rows. The 24-hour rolling aggregate is computed by
  summing rows with ``ts_utc >= now - 24h``.
* ``surface_degrade_state`` — one row per surface that has been
  auto-disabled. ``get_active_pattern()`` consults this before reading
  ``config.QUALITY_LOOP_FLAGS``.

Contracts:

1. ``record_surface_spend(db, surface, cost_usd)`` — append an event.
   Idempotent on repeat calls with different timestamps. Negative cost
   is rejected (table constraint).

2. ``get_24h_spend(db, surface)`` — sum events in the last 24 hours.
   O(N) on rows in the window; in practice <1k rows/day per surface so
   no index dance needed.

3. ``should_auto_disable(db, surface)`` — True iff last-24h spend
   exceeds ``DAILY_AGGREGATE_CEILINGS_USD[surface]``. Returns False if
   the surface is not configured (graceful degradation).

4. ``get_active_pattern(db, surface)`` — returns the EFFECTIVE pattern
   the surface should use. Decision tree:
       a. if surface NOT in ``QUALITY_LOOP_FLAGS`` → None.
       b. else if surface in ``surface_degrade_state`` (human hasn't
          re-enabled yet) → that row's degrade pattern.
       c. else if ``should_auto_disable`` (24h aggregate breached) →
          ``SURFACE_DEGRADE_PATTERN[surface]`` and ALSO upserts the
          degrade row so subsequent calls short-circuit. Logs loudly.
       d. otherwise → the configured ``QUALITY_LOOP_FLAGS`` pattern.

5. ``reset_surface_degrade(db, surface)`` — delete the degrade row.
   Used by ``manage.py quality-loop-reenable``. Does NOT touch the
   spend-events log — owner may want to inspect that.

6. ``prune_old_events(db, max_age_hours)`` — housekeeping to keep the
   events table small. Not called automatically; tests + cron exercise it.

All DB writes go through ``Database.execute`` / ``upsert_many`` so retry
logic and busy-timeout protection are inherited.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cfb_rankings.db import Database
    from cfb_rankings.quality_loop import LoopPattern

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Time helpers — keep timestamps timezone-aware UTC.
# ---------------------------------------------------------------------------

_TS_FORMAT = "%Y-%m-%d %H:%M:%S"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _to_iso(ts: datetime) -> str:
    """Format a datetime in the SQLite-comparable UTC string format the
    table's DEFAULT CURRENT_TIMESTAMP produces (``YYYY-MM-DD HH:MM:SS``).
    Strips tzinfo so string comparison stays consistent with the column."""
    if ts.tzinfo is not None:
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    return ts.strftime(_TS_FORMAT)


# ---------------------------------------------------------------------------
# Spend-events recording + rollup
# ---------------------------------------------------------------------------

def record_surface_spend(
    db: "Database",
    surface: str,
    cost_usd: float,
    *,
    timestamp: datetime | None = None,
    note: str | None = None,
) -> None:
    """Append a single spend event for a surface.

    No-op if ``cost_usd <= 0`` — saves a write and matches CostMeter
    semantics (zero-cost calls don't burn budget).
    """
    if cost_usd <= 0:
        return
    ts = _to_iso(timestamp or _now_utc())
    db.execute(
        "INSERT INTO surface_spend_events (surface, ts_utc, cost_usd, note) "
        "VALUES (:surface, :ts_utc, :cost_usd, :note)",
        {
            "surface": surface,
            "ts_utc": ts,
            "cost_usd": float(cost_usd),
            "note": note,
        },
    )


def get_24h_spend(
    db: "Database",
    surface: str,
    *,
    now: datetime | None = None,
) -> float:
    """Sum cost_usd for ``surface`` events in the last 24 hours."""
    cutoff_dt = (now or _now_utc()) - timedelta(hours=24)
    cutoff = _to_iso(cutoff_dt)
    row = db.query_one(
        "SELECT COALESCE(SUM(cost_usd), 0.0) AS total "
        "FROM surface_spend_events "
        "WHERE surface = :surface AND ts_utc >= :cutoff",
        {"surface": surface, "cutoff": cutoff},
    )
    if not row:
        return 0.0
    return float(row.get("total") or 0.0)


def should_auto_disable(
    db: "Database",
    surface: str,
    *,
    now: datetime | None = None,
) -> bool:
    """True iff last-24h spend > ``DAILY_AGGREGATE_CEILINGS_USD[surface]``.

    Returns False when the surface is not in the ceiling map (no ceiling
    configured = no auto-disable).
    """
    try:
        from cfb_rankings.config import DAILY_AGGREGATE_CEILINGS_USD
    except Exception:
        return False
    ceiling = DAILY_AGGREGATE_CEILINGS_USD.get(surface)
    if ceiling is None:
        return False
    spent = get_24h_spend(db, surface, now=now)
    return spent > float(ceiling)


# ---------------------------------------------------------------------------
# Degrade-state management
# ---------------------------------------------------------------------------

def _read_degrade_row(db: "Database", surface: str) -> dict[str, Any] | None:
    return db.query_one(
        "SELECT surface, degrade_pattern, breached_at_utc, breached_spend_usd, "
        "       ceiling_usd, reason "
        "FROM surface_degrade_state WHERE surface = :surface",
        {"surface": surface},
    )


def _upsert_degrade_row(
    db: "Database",
    surface: str,
    *,
    pattern_value: str,
    spent_usd: float,
    ceiling_usd: float,
    reason: str,
    breached_at: datetime | None = None,
) -> None:
    ts = _to_iso(breached_at or _now_utc())
    db.execute(
        "INSERT INTO surface_degrade_state "
        "  (surface, degrade_pattern, breached_at_utc, breached_spend_usd, "
        "   ceiling_usd, reason) "
        "VALUES (:surface, :pattern, :ts, :spent, :ceiling, :reason) "
        "ON CONFLICT(surface) DO UPDATE SET "
        "  degrade_pattern = excluded.degrade_pattern, "
        "  breached_at_utc = excluded.breached_at_utc, "
        "  breached_spend_usd = excluded.breached_spend_usd, "
        "  ceiling_usd = excluded.ceiling_usd, "
        "  reason = excluded.reason",
        {
            "surface": surface,
            "pattern": pattern_value,
            "ts": ts,
            "spent": float(spent_usd),
            "ceiling": float(ceiling_usd),
            "reason": reason,
        },
    )


def get_active_pattern(
    db: "Database",
    surface: str,
    *,
    now: datetime | None = None,
) -> "LoopPattern | None":
    """Return the effective LoopPattern for ``surface``.

    See module-docstring step 4 for the decision tree. Returns None when
    the surface has no configured flag (caller should fall through to the
    legacy ``generate_with_voice_check`` path).

    Side effect: if the 24h aggregate is breached AND no degrade row
    exists yet, this function writes one (so subsequent calls in the same
    process short-circuit on the existing row rather than re-querying the
    spend rollup). A ``::warning::`` is logged so the owner sees it in
    workflow output.
    """
    try:
        from cfb_rankings.config import (
            DAILY_AGGREGATE_CEILINGS_USD,
            QUALITY_LOOP_FLAGS,
            SURFACE_DEGRADE_PATTERN,
        )
        from cfb_rankings.quality_loop import LoopPattern
    except Exception:
        return None

    configured = QUALITY_LOOP_FLAGS.get(surface)
    if configured is None:
        return None
    # Normalize string → enum.
    if isinstance(configured, str):
        try:
            configured = LoopPattern(configured)
        except ValueError:
            return None

    # 4b) Existing degrade marker wins. Human must explicitly re-enable.
    existing = _read_degrade_row(db, surface)
    if existing is not None:
        try:
            return LoopPattern(existing["degrade_pattern"])
        except (ValueError, KeyError):
            return configured  # corrupt row — log + fall through to configured

    # 4c) Live check on the 24h aggregate. If breached, write the marker
    # and degrade now.
    if should_auto_disable(db, surface, now=now):
        degrade = SURFACE_DEGRADE_PATTERN.get(surface)
        if degrade is None:
            # No degrade target configured — fall back to Pattern A by default.
            degrade = LoopPattern.A_SINGLE_SHOT
        elif isinstance(degrade, str):
            try:
                degrade = LoopPattern(degrade)
            except ValueError:
                degrade = LoopPattern.A_SINGLE_SHOT
        spent = get_24h_spend(db, surface, now=now)
        ceiling = float(DAILY_AGGREGATE_CEILINGS_USD.get(surface, 0.0))
        _upsert_degrade_row(
            db, surface,
            pattern_value=degrade.value,
            spent_usd=spent,
            ceiling_usd=ceiling,
            reason="daily_aggregate_ceiling",
        )
        # Loud log: GitHub Actions surfaces `::warning::` in workflow run summaries.
        msg = (
            f"::warning::circuit_state auto-disabled Pattern C for {surface!r}: "
            f"24h spend ${spent:.4f} > ceiling ${ceiling:.2f}; "
            f"degraded to {degrade.value}. "
            f"Run `manage.py quality-loop-reenable {surface}` after review."
        )
        log.warning(msg)
        print(msg, flush=True)
        return degrade

    # 4d) Not breached — return the configured pattern.
    return configured


def reset_surface_degrade(db: "Database", surface: str) -> bool:
    """Clear the degrade marker for a surface. Returns True if a row was
    deleted, False if no marker existed.

    Used by ``manage.py quality-loop-reenable <surface>``. Spend events
    are intentionally NOT pruned — owner may want to inspect them.
    """
    existing = _read_degrade_row(db, surface)
    if existing is None:
        return False
    db.execute(
        "DELETE FROM surface_degrade_state WHERE surface = :surface",
        {"surface": surface},
    )
    return True


# ---------------------------------------------------------------------------
# Per-run cost-meter helper
# ---------------------------------------------------------------------------

def make_cost_meter_for_surface(
    surface: str,
    *,
    label: str | None = None,
    default_usd: float = 5.00,
    db: "Database | None" = None,
):
    """Construct a ``CostMeter`` whose ceiling comes from
    ``PER_RUN_CEILINGS_USD[surface]``, falling back to ``default_usd``
    when the surface isn't configured.

    This is the canonical way for Pattern C surfaces to build their
    per-run meter so the per-surface ceiling is enforced uniformly.

    When ``db`` is provided, the returned meter ALSO forwards every
    ``record()`` call to ``record_surface_spend(db, surface, cost)`` so
    the 24h rolling aggregate stays accurate. The forwarding wrap is
    transparent: callers see the same return value (cost in USD) and
    the same ``CostCeilingExceeded`` propagation. See
    ``attach_meter_to_surface`` for an in-place wiring against a
    pre-existing meter.
    """
    # Lazy import to avoid pulling llm_runtime at module import time
    # (keeps `from cfb_rankings.circuit_state import ...` light).
    from cfb_rankings.llm_runtime import CostMeter
    try:
        from cfb_rankings.config import PER_RUN_CEILINGS_USD
        ceiling = float(PER_RUN_CEILINGS_USD.get(surface, default_usd))
    except Exception:
        ceiling = float(default_usd)
    meter = CostMeter(
        ceiling_usd=ceiling,
        label=label or surface,
    )
    if db is not None:
        attach_meter_to_surface(db, meter, surface)
    return meter


def attach_meter_to_surface(db: "Database", meter: Any, surface: str) -> None:
    """Wrap ``meter.record()`` so every recorded cost ALSO flows into
    ``surface_spend_events`` for the 24h aggregate guardrail.

    Idempotent: calling twice on the same meter does NOT double-count
    (a ``_surface_tracked`` sentinel attribute is checked first).

    Failure isolation: if writing to ``surface_spend_events`` raises
    (transient SQLite lock, missing table on a partially-migrated DB,
    etc.) the error is swallowed with a log line. Per-run ceiling
    enforcement via ``CostMeter`` is the primary guardrail; the 24h
    aggregate is a secondary safety net that must not crash a live run.
    """
    if getattr(meter, "_surface_tracked", False):
        return
    original_record = meter.record

    def _tracked_record(model_id: str, usage: Any, **kwargs: Any) -> float:
        cost = original_record(model_id, usage, **kwargs)
        try:
            record_surface_spend(db, surface, float(cost or 0.0))
        except Exception as exc:  # pragma: no cover — defensive
            log.warning(
                "attach_meter_to_surface: record_surface_spend failed for "
                "surface=%r cost=$%.4f: %s",
                surface, float(cost or 0.0), exc,
            )
        return cost

    meter.record = _tracked_record  # type: ignore[assignment]
    meter._surface_tracked = True  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Housekeeping
# ---------------------------------------------------------------------------

def prune_old_events(
    db: "Database",
    *,
    max_age_hours: int = 168,
    now: datetime | None = None,
) -> int:
    """Delete spend events older than ``max_age_hours``. Returns the
    number of rows pruned. Default keeps a week of history (24h is the
    enforcement window, 168h gives a comfortable cushion for forensics).
    """
    cutoff_dt = (now or _now_utc()) - timedelta(hours=max_age_hours)
    cutoff = _to_iso(cutoff_dt)
    before = db.query_one(
        "SELECT COUNT(*) AS n FROM surface_spend_events WHERE ts_utc < :cutoff",
        {"cutoff": cutoff},
    )
    n_before = int((before or {}).get("n") or 0)
    if n_before == 0:
        return 0
    db.execute(
        "DELETE FROM surface_spend_events WHERE ts_utc < :cutoff",
        {"cutoff": cutoff},
    )
    return n_before


# ---------------------------------------------------------------------------
# Status reporting (for manage.py quality-loop-status)
# ---------------------------------------------------------------------------

def status_report(
    db: "Database",
    *,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Build a per-surface status row for every surface in
    ``QUALITY_LOOP_FLAGS`` ∪ ``DAILY_AGGREGATE_CEILINGS_USD``.

    Each row::

        {
            "surface": str,
            "configured_pattern": str | None,
            "active_pattern":     str | None,
            "spend_24h_usd":      float,
            "ceiling_24h_usd":    float | None,
            "fraction":           float,         # 0.0 when ceiling None
            "degraded":           bool,
            "degrade_reason":     str | None,
            "breached_at_utc":    str | None,
        }
    """
    try:
        from cfb_rankings.config import (
            DAILY_AGGREGATE_CEILINGS_USD,
            QUALITY_LOOP_FLAGS,
        )
    except Exception:
        return []
    surfaces = sorted(set(QUALITY_LOOP_FLAGS.keys()) | set(DAILY_AGGREGATE_CEILINGS_USD.keys()))
    rows: list[dict[str, Any]] = []
    for surface in surfaces:
        configured = QUALITY_LOOP_FLAGS.get(surface)
        configured_value: str | None
        if configured is None:
            configured_value = None
        elif hasattr(configured, "value"):
            configured_value = configured.value
        else:
            configured_value = str(configured)
        ceiling = DAILY_AGGREGATE_CEILINGS_USD.get(surface)
        spend = get_24h_spend(db, surface, now=now)
        degrade_row = _read_degrade_row(db, surface)
        if degrade_row is not None:
            active = degrade_row["degrade_pattern"]
            degraded = True
            reason = degrade_row.get("reason")
            breached_at = degrade_row.get("breached_at_utc")
        else:
            active = configured_value
            degraded = False
            reason = None
            breached_at = None
        rows.append({
            "surface": surface,
            "configured_pattern": configured_value,
            "active_pattern": active,
            "spend_24h_usd": round(spend, 6),
            "ceiling_24h_usd": float(ceiling) if ceiling is not None else None,
            "fraction": round(spend / float(ceiling), 4) if ceiling else 0.0,
            "degraded": degraded,
            "degrade_reason": reason,
            "breached_at_utc": breached_at,
        })
    return rows


__all__ = [
    "record_surface_spend",
    "get_24h_spend",
    "should_auto_disable",
    "get_active_pattern",
    "reset_surface_degrade",
    "make_cost_meter_for_surface",
    "attach_meter_to_surface",
    "prune_old_events",
    "status_report",
]
