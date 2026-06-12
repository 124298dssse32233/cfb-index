"""Pillar results -> one overall gate state (RED/YELLOW/GREEN/UNKNOWN).

Gates, not a blended score (codex correcting gemini): a single averaged 0-100
number hides critical failures. We present per-pillar pass-rates + a hard
overall gate.

Rules (from the blueprint + spec):
  RED      any critical FAIL.
  YELLOW   any warning/info FAIL (non-critical), or any UNKNOWN that is NOT on a
           critical assertion (a degraded-but-not-broken signal).
  UNKNOWN  a *required* (critical) assertion could not be evaluated. UNKNOWN
           NEVER collapses to GREEN.
  GREEN    everything required passed.

Key nuance the pillars own, NOT the gate: a season at its OWN regime expectation
(covid / in_progress / known_missing) must already be emitted as ``status='pass'``
by the completeness pillar — so it never reaches the gate as a fail. The gate
only aggregates the statuses it is given.

Empty input (zero pillars / zero results — the scaffold state) -> UNKNOWN, with a
clear summary, never GREEN (we cannot assert health we never measured).
"""
from __future__ import annotations

from collections import defaultdict


def _passrate(passes: int, total: int) -> float:
    """Pass fraction in [0,1]; total of 0 -> 0.0 (no evidence, not 'all good')."""
    return round(passes / total, 4) if total else 0.0


def compute_gate(results) -> dict:
    """Aggregate CheckResult rows into the overall gate dict.

    Returns:
      {
        "overall": "RED" | "YELLOW" | "GREEN" | "UNKNOWN",
        "passrates": {pillar: float in [0,1]},
        "counts": {"total","pass","fail","unknown",
                   "critical_fail","warning_fail","critical_unknown","by_pillar":{...}},
        "summary": str,
      }
    """
    results = list(results)

    # Per-pillar tallies.
    by_pillar: dict[str, dict[str, int]] = defaultdict(
        lambda: {"pass": 0, "fail": 0, "unknown": 0, "total": 0}
    )
    n_pass = n_fail = n_unknown = 0
    critical_fail = warning_fail = critical_unknown = 0

    for r in results:
        bucket = by_pillar[r.pillar]
        bucket["total"] += 1
        if r.status == "pass":
            bucket["pass"] += 1
            n_pass += 1
        elif r.status == "fail":
            bucket["fail"] += 1
            n_fail += 1
            if r.severity == "critical":
                critical_fail += 1
            else:
                warning_fail += 1
        else:  # unknown
            bucket["unknown"] += 1
            n_unknown += 1
            if r.severity == "critical":
                critical_unknown += 1

    passrates = {
        pillar: _passrate(b["pass"], b["total"]) for pillar, b in by_pillar.items()
    }

    total = len(results)

    # --- decide the overall gate ---
    if total == 0:
        overall = "UNKNOWN"
        summary = (
            "UNKNOWN: no health assertions were evaluated (no pillars registered). "
            "Absence of measurement is never GREEN."
        )
    elif critical_fail > 0:
        overall = "RED"
        summary = (
            f"RED: {critical_fail} critical failure(s). "
            f"({n_fail} fail / {n_unknown} unknown / {n_pass} pass of {total})"
        )
    elif critical_unknown > 0:
        # A required assertion could not be evaluated -> UNKNOWN, never GREEN.
        overall = "UNKNOWN"
        summary = (
            f"UNKNOWN: {critical_unknown} required assertion(s) could not be "
            f"evaluated (unknown denominator). Never collapses to GREEN. "
            f"({n_fail} fail / {n_unknown} unknown / {n_pass} pass of {total})"
        )
    elif warning_fail > 0 or n_unknown > 0:
        overall = "YELLOW"
        summary = (
            f"YELLOW: {warning_fail} non-critical failure(s), {n_unknown} "
            f"unevaluated. No critical breakage. "
            f"({n_pass} pass of {total})"
        )
    else:
        overall = "GREEN"
        summary = f"GREEN: all {total} required assertion(s) passed."

    counts = {
        "total": total,
        "pass": n_pass,
        "fail": n_fail,
        "unknown": n_unknown,
        "critical_fail": critical_fail,
        "warning_fail": warning_fail,
        "critical_unknown": critical_unknown,
        "by_pillar": dict(by_pillar),
    }

    return {
        "overall": overall,
        "passrates": passrates,
        "counts": counts,
        "summary": summary,
    }
