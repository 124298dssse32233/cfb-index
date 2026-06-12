"""Pillar registry + fan-out.

The 5 observability pillars (completeness, volume, schema/validity, integrity,
freshness/provenance) each land as a module exposing ``name`` + ``run(conn)``
and get appended to ``PILLARS``. ``run_all`` iterates them and flattens the
``CheckResult`` rows.

Scaffold state: ``PILLARS`` is empty. ``run_all`` therefore returns ``[]`` and
the report/gate render a clean empty (UNKNOWN) result — it must NOT crash with
zero pillars. Downstream agents register pillars by appending to ``PILLARS``
(or importing their module and adding it here).
"""
from __future__ import annotations

import sqlite3

from .base import CheckResult, Pillar  # re-export for convenience
from . import integrity
from . import completeness
from . import provenance
from . import freshness
from . import validity

# Each entry must satisfy the Pillar protocol (a ``name`` attr + ``run(conn)``).
# A pillar module satisfies it at module level; append the imported module here.
PILLARS: list = []
PILLARS.append(integrity)
PILLARS.append(completeness)
PILLARS.append(provenance)
PILLARS.append(freshness)
PILLARS.append(validity)

__all__ = ["CheckResult", "Pillar", "PILLARS", "run_all"]


def run_all(conn: sqlite3.Connection) -> list[CheckResult]:
    """Run every registered pillar and flatten the results.

    A pillar that raises is isolated: its failure is converted into a single
    UNKNOWN/critical CheckResult so one broken pillar can never silently drop
    the others or crash the whole run (the gate then refuses to go GREEN).
    """
    results: list[CheckResult] = []
    for pillar in PILLARS:
        name = getattr(pillar, "name", getattr(pillar, "__name__", "unknown"))
        try:
            pillar_results = pillar.run(conn)
        except Exception as exc:  # noqa: BLE001 - isolate a broken pillar
            results.append(
                CheckResult(
                    check_id=f"{name}.pillar_error",
                    pillar=str(name),
                    dataset="-",
                    season=None,
                    status="unknown",
                    severity="critical",
                    detail=f"pillar {name} raised {type(exc).__name__}: {exc}",
                    evidence_sql="",
                )
            )
            continue
        results.extend(pillar_results)
    return results
