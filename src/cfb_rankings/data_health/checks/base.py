"""Shared interface for the Data Health pillars (LOCKED).

Every pillar module under ``data_health/checks/`` MUST conform to this exactly:
  * it produces ``CheckResult`` rows (the normalized result grain), and
  * it exposes a module-level ``def run(conn) -> list[CheckResult]``.

Downstream agents implement pillars against these two contracts and nothing
else. Keep this module dependency-free (stdlib + typing only).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import sqlite3

# Allowed enum-like string sets (validated by callers; kept as plain str on the
# dataclass for cheap JSON serialization).
STATUSES = ("pass", "fail", "unknown")
SEVERITIES = ("critical", "warning", "info")


@dataclass(frozen=True)
class CheckResult:
    """One assertion outcome — the normalized result row.

    Fields (LOCKED — do not reorder/rename; report.py + gate.py key off these):
      check_id      stable id for the assertion, e.g. "completeness.games.2023".
      pillar        owning pillar, e.g. "completeness" | "volume" | "schema" | ...
      dataset       dataset/table the assertion is about (or a logical group).
      season        season the assertion is scoped to, or None if season-agnostic.
      status        'pass' | 'fail' | 'unknown'.
      severity      'critical' | 'warning' | 'info'.
      detail        human-readable one-liner (what was asserted + observed).
      evidence_sql  the SQL that produced the evidence (for reproducibility); ''.
    """
    check_id: str
    pillar: str
    dataset: str
    season: int | None
    status: str
    severity: str
    detail: str
    evidence_sql: str = ""

    def __post_init__(self) -> None:
        # Fail loud on a malformed status/severity rather than silently letting a
        # typo'd 'faii' slip past the gate as a non-fail.
        if self.status not in STATUSES:
            raise ValueError(
                f"CheckResult.status must be one of {STATUSES}, got {self.status!r}"
            )
        if self.severity not in SEVERITIES:
            raise ValueError(
                f"CheckResult.severity must be one of {SEVERITIES}, got {self.severity!r}"
            )


@runtime_checkable
class Pillar(Protocol):
    """Structural type a pillar module/object satisfies.

    A pillar has a ``name`` and a ``run(conn)`` that returns CheckResults. The
    pillar modules in this package satisfy this at module level (module ``name``
    attribute + module-level ``run``); ``checks.run_all`` treats each entry of
    ``checks.PILLARS`` as a Pillar.
    """

    name: str

    def run(self, conn: sqlite3.Connection) -> list[CheckResult]:
        ...
