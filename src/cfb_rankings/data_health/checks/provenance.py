"""Provenance pillar — conversation_documents source_id canonical coverage.

What this pillar watches (verified live 2026-06-11):
  1. CANONICAL %  — the fraction of ``conversation_documents`` rows that carry a
     non-empty ``source_id`` (== ``provenance_status='canonical'``). Live
     baseline: 43,479 / 194,972 = **22.30%**, with 151,493 ``legacy_unverified``.
     This is a RATCHET, mirroring ``scripts/verify_data_floors.py``: today's %
     must stay within ``PROVENANCE_TOLERANCE`` of the highest % ever recorded
     (stored in ``data/data_floors_baseline.json`` as ``source_id_pct_high``).
     A silent drop below the high-water mark would quietly undo WP-0.7
     provenance-labeling progress, so it flags as a ``warning`` FAIL. If the
     baseline file is absent we just report the level (pass) — no false alarm.
  2. SOURCE_ID RESOLUTION — a ``source_id`` that is present but does not resolve
     to a real ``source_registry`` source is unverifiable provenance ("not just
     non-null", per the spec). The count of such distinct ids (and the row
     count behind them) is emitted as ``info`` — a watch signal, not a gate.
     Live baseline: 171 / 173 distinct doc source_ids unregistered (27,531 rows)
     because docs carry INSTANCE keys (``athletics_howard``, ``campus_alabama``)
     while ``source_registry.source_id`` holds CLASS keys (``cfbd``, ``polymarket``).

Read-only, stdlib + raw sqlite3 only. Conforms to the locked ``CheckResult`` /
module-level ``run(conn)`` interface in ``checks/base.py``.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .base import CheckResult

name = "provenance"

# Mirror scripts/verify_data_floors.py exactly so the two guards agree.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_BASELINE_PATH = _REPO_ROOT / "data" / "data_floors_baseline.json"
_BASELINE_KEY = "source_id_pct_high"
PROVENANCE_TOLERANCE = 0.5  # percentage points of slack below the high-water mark

_DATASET = "conversation_documents"

# Canonical = a present (non-null, non-blank) source_id. This is identical to the
# write-side definition: provenance_status='canonical' iff source_id is set.
_CANONICAL_PREDICATE = "source_id IS NOT NULL AND TRIM(source_id) <> ''"


def _scalar(conn: sqlite3.Connection, sql: str) -> int | None:
    """Run a single-value query; return None on any sqlite error (-> 'unknown')."""
    try:
        row = conn.execute(sql).fetchone()
    except sqlite3.Error:
        return None
    if not row or row[0] is None:
        return None
    return int(row[0])


def _load_high_water() -> float | None:
    """Read the ratchet high-water % (read-only; never writes the baseline).

    Returns None when the baseline file is missing/unreadable so the canonical-%
    check degrades to a plain level report instead of a false regression alarm.
    """
    if not _BASELINE_PATH.exists():
        return None
    try:
        # utf-8-sig tolerates a BOM from PS 5.1 / Notepad hand-edits.
        data = json.loads(_BASELINE_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    val = data.get(_BASELINE_KEY)
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _check_canonical_pct(conn: sqlite3.Connection) -> CheckResult:
    """conversation_documents canonical source_id % (+ legacy_unverified count)."""
    evidence_sql = (
        "SELECT COUNT(*) AS total, "
        f"SUM(CASE WHEN {_CANONICAL_PREDICATE} THEN 1 ELSE 0 END) AS canonical "
        "FROM conversation_documents"
    )
    total = _scalar(conn, "SELECT COUNT(*) FROM conversation_documents")
    if total is None:
        # Table missing/unreadable — cannot evaluate; must NOT pass.
        return CheckResult(
            check_id="provenance.conversation_documents.canonical_pct",
            pillar=name,
            dataset=_DATASET,
            season=None,
            status="unknown",
            severity="warning",
            detail="conversation_documents is missing or unreadable; "
                   "cannot compute canonical source_id coverage.",
            evidence_sql=evidence_sql,
        )
    if total == 0:
        return CheckResult(
            check_id="provenance.conversation_documents.canonical_pct",
            pillar=name,
            dataset=_DATASET,
            season=None,
            status="unknown",
            severity="warning",
            detail="conversation_documents is empty (0 rows); "
                   "no provenance coverage to evaluate.",
            evidence_sql=evidence_sql,
        )

    canonical = _scalar(
        conn,
        f"SELECT COUNT(*) FROM conversation_documents WHERE {_CANONICAL_PREDICATE}",
    ) or 0
    legacy_unverified = total - canonical
    pct = round(100.0 * canonical / total, 2)

    high_water = _load_high_water()
    if high_water is not None and pct < high_water - PROVENANCE_TOLERANCE:
        status = "fail"
        detail = (
            f"canonical source_id coverage {pct}% "
            f"({canonical:,}/{total:,}; legacy_unverified={legacy_unverified:,}) "
            f"REGRESSED below high-water {high_water}% "
            f"(-{PROVENANCE_TOLERANCE}pp tolerance)."
        )
    else:
        status = "pass"
        hw = f"; high-water {high_water}%" if high_water is not None else ""
        detail = (
            f"canonical source_id coverage {pct}% "
            f"({canonical:,}/{total:,}; legacy_unverified={legacy_unverified:,}){hw}."
        )

    return CheckResult(
        check_id="provenance.conversation_documents.canonical_pct",
        pillar=name,
        dataset=_DATASET,
        season=None,
        status=status,
        severity="warning",
        detail=detail,
        evidence_sql=evidence_sql,
    )


def _check_source_id_resolves(conn: sqlite3.Connection) -> CheckResult:
    """source_id values present must reference a real source_registry source (info)."""
    # Only registry rows that actually carry a source_id form the resolvable set
    # (many legacy registry rows have NULL source_id and are not join targets).
    unresolved_sql = (
        "SELECT COUNT(DISTINCT cd.source_id) AS distinct_unresolved, COUNT(*) AS rows_unresolved "
        "FROM conversation_documents cd "
        f"WHERE {_CANONICAL_PREDICATE.replace('source_id', 'cd.source_id')} "
        "AND cd.source_id NOT IN ("
        "SELECT source_id FROM source_registry "
        "WHERE source_id IS NOT NULL AND TRIM(source_id) <> ''"
        ")"
    )

    # Guard: if either table is unreadable, emit unknown (info) rather than pass.
    try:
        row = conn.execute(unresolved_sql).fetchone()
    except sqlite3.Error as exc:
        return CheckResult(
            check_id="provenance.conversation_documents.source_id_resolves",
            pillar=name,
            dataset=_DATASET,
            season=None,
            status="unknown",
            severity="info",
            detail=f"could not evaluate source_id resolution against "
                   f"source_registry: {type(exc).__name__}.",
            evidence_sql=unresolved_sql,
        )

    distinct_unresolved = int(row[0] or 0)
    rows_unresolved = int(row[1] or 0)

    total_distinct = _scalar(
        conn,
        "SELECT COUNT(DISTINCT source_id) FROM conversation_documents "
        f"WHERE {_CANONICAL_PREDICATE}",
    ) or 0

    if distinct_unresolved == 0:
        status = "pass"
        detail = (
            f"all {total_distinct} distinct present source_id(s) resolve to a "
            f"registered source_registry source."
        )
    else:
        # Unresolved source_ids are a provenance gap but not a hard gate — info.
        status = "fail"
        detail = (
            f"{distinct_unresolved}/{total_distinct} distinct present source_id(s) "
            f"({rows_unresolved:,} rows) do NOT resolve to a registered "
            f"source_registry.source_id (unverifiable provenance)."
        )

    return CheckResult(
        check_id="provenance.conversation_documents.source_id_resolves",
        pillar=name,
        dataset=_DATASET,
        season=None,
        status=status,
        severity="info",
        detail=detail,
        evidence_sql=unresolved_sql,
    )


def run(conn: sqlite3.Connection) -> list[CheckResult]:
    """Run the provenance pillar assertions over an open read-only connection."""
    return [
        _check_canonical_pct(conn),
        _check_source_id_resolves(conn),
    ]
