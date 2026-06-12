"""Completeness pillar — actual presence + DENSITY vs each contract's own
``expected_seasons`` and the per-year REGIME.

The central rule (round-6 refinement): there is NO global "missing 2023" rule.
Each dataset declares its OWN ``expected_seasons`` in ``contracts.py``; this
pillar diffs *actual rows per season* against that set, then judges the verdict
through the per-season REGIME from ``calendar``:

  * 'normal'        — the season SHOULD be fully present. Absent => FAIL at the
                      contract severity (critical for the game spine). For a
                      dataset with a density contract (``games``), present-but-
                      sparse also FAILs (this is what catches 2022 ~2.9
                      home-games/FBS-team, well under the 5.5 normal floor).
  * 'covid'         — 2020. Judged against the COVID density floor (3.0), never
                      12. A reduced-but-real 2020 => PASS, not a gap.
  * 'in_progress'   — the current season (2025). Judged only on weeks-to-date:
                      any rows present => PASS; a still-incomplete current season
                      is not a fault.
  * 'known_missing' — a genuinely-acknowledged / out-of-scope hole. Emitted as an
                      explicit UNKNOWN (info-severity) — NEVER a silent pass and
                      NEVER a critical red, because it is a recorded, accepted gap.
                      NOTE: game-spine 2023 is deliberately NOT tagged this way —
                      it is a real season missing from the DB and is judged 'normal'
                      so it fires a CRITICAL FAIL (spec Appendix B: #1 backfill).
  * 'pre_data'      — before the DB floor / a future season. Explicit INFO, never
                      a silent pass.

Stdlib + raw ``sqlite3`` only; read-only (this pillar never mutates the DB).
"""
from __future__ import annotations

import sqlite3

from ..calendar import (
    COVID_GAMES_PER_TEAM_FLOOR,
    fbs_team_ids,
    regime_for,
)
from ..contracts import ALL_CONTRACTS, DatasetContract
from .base import CheckResult

name = "completeness"

# Candidate season-column spellings, in priority order. Most spine + offseason
# tables use ``season_year``; ``player_nfl_draft`` uniquely uses ``draft_year``
# (verified live). Resolving at runtime keeps this working across the schema
# variation the health spine exists to surface elsewhere.
_SEASON_COL_CANDIDATES = ("season_year", "draft_year", "year", "season")


def run(conn: sqlite3.Connection) -> list[CheckResult]:
    results: list[CheckResult] = []
    for contract in ALL_CONTRACTS:
        results.extend(_check_contract(conn, contract))
    return results


def _check_contract(
    conn: sqlite3.Connection, contract: DatasetContract
) -> list[CheckResult]:
    out: list[CheckResult] = []

    season_col = _resolve_season_column(conn, contract.table)
    if season_col is None:
        # We cannot even find the season grain — never silently pass. This is a
        # structural problem (missing table / no season column); UNKNOWN so the
        # gate refuses GREEN.
        out.append(
            CheckResult(
                check_id=f"completeness.{contract.name}.season_column",
                pillar=name,
                dataset=contract.name,
                season=None,
                status="unknown",
                severity=contract.severity,
                detail=(
                    f"{contract.name}: could not resolve a season column on table "
                    f"'{contract.table}' (tried {', '.join(_SEASON_COL_CANDIDATES)}) "
                    f"— cannot evaluate completeness."
                ),
                evidence_sql=f"PRAGMA table_info({contract.table});",
            )
        )
        return out

    counts = _season_counts(conn, contract.table, season_col)
    if counts is None:
        out.append(
            CheckResult(
                check_id=f"completeness.{contract.name}.query",
                pillar=name,
                dataset=contract.name,
                season=None,
                status="unknown",
                severity=contract.severity,
                detail=(
                    f"{contract.name}: failed to query per-season counts from "
                    f"'{contract.table}.{season_col}' — cannot evaluate completeness."
                ),
                evidence_sql=(
                    f"SELECT {season_col}, COUNT(*) FROM {contract.table} "
                    f"GROUP BY {season_col};"
                ),
            )
        )
        return out

    for season in sorted(contract.expected_seasons):
        out.append(
            _check_season(conn, contract, season, season_col, counts.get(season, 0))
        )
    return out


def _check_season(
    conn: sqlite3.Connection,
    contract: DatasetContract,
    season: int,
    season_col: str,
    row_count: int,
) -> CheckResult:
    regime = regime_for(contract.season_phase, season)
    check_id = f"completeness.{contract.name}.{season}"
    count_sql = (
        f"SELECT COUNT(*) FROM {contract.table} WHERE {season_col} = {season};"
    )

    # --- Acknowledged gaps: explicit, never a silent pass, never critical-red.
    if regime == "known_missing":
        return CheckResult(
            check_id=check_id,
            pillar=name,
            dataset=contract.name,
            season=season,
            status="unknown",
            severity="info",
            detail=(
                f"{contract.name} {season}: regime=known_missing "
                f"(acknowledged hole) — {row_count} rows present; not judged as a "
                f"fail, but flagged so it never silently reads as complete."
            ),
            evidence_sql=count_sql,
        )

    if regime == "pre_data":
        return CheckResult(
            check_id=check_id,
            pillar=name,
            dataset=contract.name,
            season=season,
            status="unknown" if row_count == 0 else "pass",
            severity="info",
            detail=(
                f"{contract.name} {season}: regime=pre_data (before DB floor / "
                f"future) — {row_count} rows; outside the evaluable window."
            ),
            evidence_sql=count_sql,
        )

    # --- Absent under a regime that should have data => a real gap.
    if row_count == 0:
        return CheckResult(
            check_id=check_id,
            pillar=name,
            dataset=contract.name,
            season=season,
            status="fail",
            severity=contract.severity,
            detail=(
                f"{contract.name} {season}: MISSING — 0 rows, but regime="
                f"{regime} expects this season present."
            ),
            evidence_sql=count_sql,
        )

    # --- Present. For datasets with a density contract, presence is not enough:
    # judge home-games-per-FBS-team vs the regime-appropriate floor.
    if contract.density and regime in ("normal", "covid"):
        return _check_density(conn, contract, season, regime, row_count, count_sql)

    # in_progress: judged only on weeks-to-date — any rows => not a fault.
    if regime == "in_progress":
        return CheckResult(
            check_id=check_id,
            pillar=name,
            dataset=contract.name,
            season=season,
            status="pass",
            severity=contract.severity,
            detail=(
                f"{contract.name} {season}: regime=in_progress — {row_count} rows "
                f"to date (current season, not penalized for being incomplete)."
            ),
            evidence_sql=count_sql,
        )

    # Present + normal/covid with no density contract => pass on presence.
    return CheckResult(
        check_id=check_id,
        pillar=name,
        dataset=contract.name,
        season=season,
        status="pass",
        severity=contract.severity,
        detail=(
            f"{contract.name} {season}: present ({row_count} rows), regime={regime}."
        ),
        evidence_sql=count_sql,
    )


def _check_density(
    conn: sqlite3.Connection,
    contract: DatasetContract,
    season: int,
    regime: str,
    row_count: int,
    count_sql: str,
) -> CheckResult:
    """Density gate for the game spine: home-games per real-FBS team.

    Catches the 2022 half-season (≈2.9/team) that a naive presence check passes.
    Judged against ``min_covid`` for a covid season (2020), ``min_normal`` otherwise.
    """
    check_id = f"completeness.{contract.name}.{season}"
    per_col = contract.density.get("per", "home_team_id")
    min_normal = float(contract.density.get("min_normal", 0.0))
    min_covid = float(contract.density.get("min_covid", min_normal))
    floor = min_covid if regime == "covid" else min_normal

    fbs = fbs_team_ids(conn, season)
    if not fbs:
        # The entity universe for a season that should exist could not resolve
        # (e.g. team_seasons absent for that year). Never silently pass.
        return CheckResult(
            check_id=check_id,
            pillar=name,
            dataset=contract.name,
            season=season,
            status="unknown",
            severity=contract.severity,
            detail=(
                f"{contract.name} {season}: {row_count} rows present but the FBS "
                f"entity universe is empty (team_seasons unresolved) — cannot "
                f"verify density; not assertable as complete."
            ),
            evidence_sql=count_sql,
        )

    placeholders = ",".join("?" for _ in fbs)
    density_sql = (
        f"SELECT COUNT(*) FROM {contract.table} "
        f"WHERE season_year = {season} AND {per_col} IN ({len(fbs)} FBS team ids)"
    )
    try:
        home_in_fbs = conn.execute(
            f"SELECT COUNT(*) FROM {contract.table} "
            f"WHERE season_year = ? AND {per_col} IN ({placeholders})",
            (season, *fbs),
        ).fetchone()[0]
    except sqlite3.Error as exc:
        return CheckResult(
            check_id=check_id,
            pillar=name,
            dataset=contract.name,
            season=season,
            status="unknown",
            severity=contract.severity,
            detail=(
                f"{contract.name} {season}: density query failed ({exc}); "
                f"cannot verify density."
            ),
            evidence_sql=density_sql,
        )

    per_team = home_in_fbs / len(fbs) if fbs else 0.0
    floor_label = "covid floor" if regime == "covid" else "normal floor"

    if per_team < floor:
        return CheckResult(
            check_id=check_id,
            pillar=name,
            dataset=contract.name,
            season=season,
            status="fail",
            severity=contract.severity,
            detail=(
                f"{contract.name} {season}: SPARSE — {per_team:.2f} "
                f"{per_col.replace('_id','')}-games/FBS-team "
                f"({home_in_fbs} over {len(fbs)} teams) < {floor:.2f} "
                f"({floor_label}, regime={regime}). Half-season / partial gap."
            ),
            evidence_sql=density_sql,
        )

    return CheckResult(
        check_id=check_id,
        pillar=name,
        dataset=contract.name,
        season=season,
        status="pass",
        severity=contract.severity,
        detail=(
            f"{contract.name} {season}: density OK — {per_team:.2f} "
            f"{per_col.replace('_id','')}-games/FBS-team over {len(fbs)} teams "
            f">= {floor:.2f} ({floor_label}, regime={regime})."
        ),
        evidence_sql=density_sql,
    )


# --- helpers -------------------------------------------------------------


def _resolve_season_column(conn: sqlite3.Connection, table: str) -> str | None:
    """Find the season column on ``table`` at runtime (handles ``draft_year``)."""
    try:
        cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except sqlite3.Error:
        return None
    if not cols:
        return None
    for cand in _SEASON_COL_CANDIDATES:
        if cand in cols:
            return cand
    return None


def _season_counts(
    conn: sqlite3.Connection, table: str, season_col: str
) -> dict[int, int] | None:
    """Map ``{season: row_count}`` for a table, or None if the query fails."""
    try:
        rows = conn.execute(
            f"SELECT {season_col}, COUNT(*) FROM {table} "
            f"WHERE {season_col} IS NOT NULL GROUP BY {season_col}"
        ).fetchall()
    except sqlite3.Error:
        return None
    out: dict[int, int] = {}
    for season, cnt in rows:
        try:
            out[int(season)] = int(cnt)
        except (TypeError, ValueError):
            continue
    return out
