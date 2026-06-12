"""Validity pillar — schema-drift + null-density + impossible values.

Three assertion families, all cheap read-only SQL/PRAGMA against the live DB:

  1. SCHEMA DRIFT.  For each contract table, ``PRAGMA table_info`` yields a stable
     signature (sorted ``name:type`` pairs). On the FIRST run, the per-table
     signatures are written to ``data_health/schema_signatures.json`` as the
     checked-in baseline and every table passes ("baseline established"). On
     subsequent runs each table's live signature is diffed against the baseline:
     an exact match passes; ANY drift (column added / removed / renamed / retyped)
     fails CRITICAL — this is the class that silently broke the Savant
     ``display_name`` render. A table missing from the live DB but present in the
     baseline fails CRITICAL; a table present live but absent from the baseline is
     emitted as INFO (a new table, not a regression).

  2. NULL DENSITY.  For each contract's ``required_non_null`` columns, the % of
     rows that are NULL (and, for text-ish key columns, the empty string — which
     is how ``players.position`` reads 15.9% rather than 0.1%). A required column
     that is entirely absent from the table is a schema-drift signal and fails
     CRITICAL. Otherwise: 0% null passes; up to the warn threshold is INFO; above
     it is a WARNING (never critical — a 15.9% null ``players.position`` is a
     known, tolerated "placeholder pandemic", not a build-breaker). The blueprint
     calls out ``players.position`` explicitly, so it gets its own dedicated
     check in addition to any contract coverage.

  3. IMPOSSIBLE / FUTURE VALUES on the game spine (verified-clean baselines that
     should only ever fire on FUTURE corruption):
       * ``games.start_time_utc`` in the future (> now) — 0 baseline -> pass.
       * negative or >100 game scores — 0 baseline -> pass.
       * games marked Final yet 0-0 (regulation ties impossible post-1996 OT) —
         21 baseline -> WARNING (mislabeled cancelled/forfeited games).

Read-only: this module never mutates the DB. The ONLY file it writes is the
baseline ``schema_signatures.json`` (and only when it does not yet exist).
stdlib + raw sqlite3 only.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone

from .. import contracts
from .base import CheckResult

name = "validity"

# Where the checked-in schema baseline lives (sibling of the ``checks`` package,
# i.e. ``data_health/schema_signatures.json``).
_SIGNATURE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "schema_signatures.json",
)

# A required column that is NULL/empty above this share is surfaced as a WARNING
# (below it, as INFO). 12% sits under the 15.9% ``players.position`` baseline so
# that genuine placeholder-density fires, while a near-clean column stays quiet.
_NULL_WARN_THRESHOLD = 0.12

# Text-ish key columns where the empty string is semantically null (so the
# ``players.position`` 9,754 empties count, matching the verified 15.9%). Numeric
# id/season columns use strict ``IS NULL`` only.
_EMPTY_AS_NULL = ("position", "category", "stat_type")


# --- helpers --------------------------------------------------------------

def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table,),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, table: str) -> dict[str, str]:
    """{column_name: declared_type} via PRAGMA, or {} if the table is absent."""
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    except sqlite3.Error:
        return {}
    # PRAGMA table_info columns: (cid, name, type, notnull, dflt_value, pk)
    return {str(r[1]): str(r[2] or "") for r in rows}


def _signature(cols: dict[str, str]) -> list[str]:
    """Stable, order-independent signature: sorted ``name:type`` tokens."""
    return sorted(f"{n}:{t}" for n, t in cols.items())


def _row_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except sqlite3.Error:
        return 0


# --- 1. schema drift ------------------------------------------------------

def _load_baseline() -> dict | None:
    if not os.path.exists(_SIGNATURE_PATH):
        return None
    try:
        with open(_SIGNATURE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _build_baseline(conn: sqlite3.Connection, tables: list[str]) -> dict:
    return {
        t: _signature(_table_columns(conn, t))
        for t in tables
        if _table_exists(conn, t)
    }


def _write_baseline(baseline: dict) -> bool:
    try:
        with open(_SIGNATURE_PATH, "w", encoding="utf-8") as fh:
            json.dump(baseline, fh, indent=2, sort_keys=True)
            fh.write("\n")
        return True
    except OSError:
        return False


def _check_schema(conn: sqlite3.Connection) -> list[CheckResult]:
    results: list[CheckResult] = []
    tables = sorted({c.table for c in contracts.ALL_CONTRACTS})
    baseline = _load_baseline()

    if baseline is None:
        # First run: snapshot the live schema as the checked-in baseline. Pass
        # (we have nothing to drift against yet) but record that we just minted it.
        baseline = _build_baseline(conn, tables)
        wrote = _write_baseline(baseline)
        detail = (
            f"schema baseline established for {len(baseline)} table(s) "
            f"-> {os.path.basename(_SIGNATURE_PATH)}"
            if wrote
            else (
                f"schema baseline computed for {len(baseline)} table(s) but could "
                f"NOT be written to {_SIGNATURE_PATH}"
            )
        )
        results.append(
            CheckResult(
                check_id="validity.schema.baseline",
                pillar=name,
                dataset="-",
                season=None,
                status="pass" if wrote else "unknown",
                severity="info" if wrote else "critical",
                detail=detail,
                evidence_sql="PRAGMA table_info(<table>)  -- per contract table",
            )
        )
        return results

    # Subsequent runs: diff each contract table against the baseline.
    for table in tables:
        base_sig = baseline.get(table)
        live_cols = _table_columns(conn, table)
        live_sig = _signature(live_cols)

        if base_sig is None:
            # New contract table not yet in the baseline -> info, not a regression.
            results.append(
                CheckResult(
                    check_id=f"validity.schema.{table}",
                    pillar=name,
                    dataset=table,
                    season=None,
                    status="pass",
                    severity="info",
                    detail=(
                        f"{table}: no baseline signature on file "
                        f"(new table; will baseline on next regen)"
                    ),
                    evidence_sql=f"PRAGMA table_info({table})",
                )
            )
            continue

        if not live_cols:
            # Baseline expects it but the live DB has no such table -> critical.
            results.append(
                CheckResult(
                    check_id=f"validity.schema.{table}",
                    pillar=name,
                    dataset=table,
                    season=None,
                    status="fail",
                    severity="critical",
                    detail=f"{table}: table present in baseline but MISSING from live DB",
                    evidence_sql=f"PRAGMA table_info({table})",
                )
            )
            continue

        if live_sig == base_sig:
            results.append(
                CheckResult(
                    check_id=f"validity.schema.{table}",
                    pillar=name,
                    dataset=table,
                    season=None,
                    status="pass",
                    severity="critical",
                    detail=f"{table}: schema signature matches baseline ({len(live_sig)} cols)",
                    evidence_sql=f"PRAGMA table_info({table})",
                )
            )
        else:
            base_set, live_set = set(base_sig), set(live_sig)
            added = sorted(live_set - base_set)
            removed = sorted(base_set - live_set)
            results.append(
                CheckResult(
                    check_id=f"validity.schema.{table}",
                    pillar=name,
                    dataset=table,
                    season=None,
                    status="fail",
                    severity="critical",
                    detail=(
                        f"{table}: SCHEMA DRIFT vs baseline -- "
                        f"added={added or '[]'} removed={removed or '[]'}"
                    ),
                    evidence_sql=f"PRAGMA table_info({table})",
                )
            )
    return results


# --- 2. null density ------------------------------------------------------

def _null_density(
    conn: sqlite3.Connection, table: str, col: str, count_empty: bool
) -> tuple[int, int]:
    """(null_or_empty_rows, total_rows) for ``table.col``."""
    total = _row_count(conn, table)
    if total == 0:
        return 0, 0
    if count_empty:
        pred = f"{col} IS NULL OR TRIM({col}) = ''"
    else:
        pred = f"{col} IS NULL"
    try:
        n = int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {pred}").fetchone()[0])
    except sqlite3.Error:
        return -1, total
    return n, total


def _emit_null_density(
    conn: sqlite3.Connection,
    *,
    dataset: str,
    table: str,
    col: str,
    severity_floor: str,
    check_id: str,
) -> CheckResult:
    """One null-density CheckResult for ``table.col``.

    A required column entirely absent from the table is itself schema drift ->
    fail CRITICAL. Otherwise null% drives the status: 0% pass; <= threshold info;
    > threshold a WARNING (capped at the contract's severity, never escalating a
    warning-tier dataset to critical).
    """
    cols = _table_columns(conn, table)
    count_empty = col in _EMPTY_AS_NULL
    if col not in cols:
        return CheckResult(
            check_id=check_id,
            pillar=name,
            dataset=dataset,
            season=None,
            status="fail",
            severity="critical",
            detail=(
                f"{table}.{col}: required column ABSENT from live schema "
                f"(contract/DB drift)"
            ),
            evidence_sql=f"PRAGMA table_info({table})",
        )

    n_null, total = _null_density(conn, table, col, count_empty)
    pred = f"{col} IS NULL OR TRIM({col})=''" if count_empty else f"{col} IS NULL"
    sql = f"SELECT COUNT(*) FROM {table} WHERE {pred}"

    if total == 0:
        # No rows to measure -> can't assert density. Not a fail (emptiness is the
        # completeness/volume pillars' concern), but not a clean pass either.
        return CheckResult(
            check_id=check_id,
            pillar=name,
            dataset=dataset,
            season=None,
            status="unknown",
            severity="info",
            detail=f"{table}.{col}: 0 rows -- null density not measurable",
            evidence_sql=sql,
        )
    if n_null < 0:
        return CheckResult(
            check_id=check_id,
            pillar=name,
            dataset=dataset,
            season=None,
            status="unknown",
            severity="info",
            detail=f"{table}.{col}: null-density query failed to evaluate",
            evidence_sql=sql,
        )

    pct = n_null / total
    label = "null/empty" if count_empty else "null"
    detail = f"{table}.{col}: {n_null}/{total} {label} ({pct * 100:.1f}%)"
    if n_null == 0:
        return CheckResult(check_id, name, dataset, None, "pass", "info", detail, sql)
    if pct <= _NULL_WARN_THRESHOLD:
        return CheckResult(check_id, name, dataset, None, "pass", "info", detail, sql)
    # Over threshold -> warning, but never exceed the contract's own severity.
    sev = "warning" if severity_floor != "info" else "info"
    return CheckResult(
        check_id, name, dataset, None, "fail", sev,
        f"{detail} -- exceeds {_NULL_WARN_THRESHOLD * 100:.0f}% null threshold", sql,
    )


def _check_null_density(conn: sqlite3.Connection) -> list[CheckResult]:
    results: list[CheckResult] = []

    # Contract-declared required_non_null columns.
    for ct in contracts.ALL_CONTRACTS:
        if not _table_exists(conn, ct.table):
            # Table absence is owned by completeness/schema; skip here so we don't
            # double-flag.
            continue
        for col in ct.required_non_null:
            results.append(
                _emit_null_density(
                    conn,
                    dataset=ct.name,
                    table=ct.table,
                    col=col,
                    # Warning-tier contracts cap at warning; critical-tier still
                    # caps at warning for null density (a populated-but-null key is
                    # a quality warning, not a build-breaker -- the blueprint marks
                    # players.position 15.9% as YELLOW, not RED).
                    severity_floor="warning",
                    check_id=f"validity.null.{ct.name}.{col}",
                )
            )

    # Dedicated players.position check (called out explicitly in the blueprint;
    # 15.9% baseline). players is not itself a contract table.
    if _table_exists(conn, "players"):
        results.append(
            _emit_null_density(
                conn,
                dataset="players",
                table="players",
                col="position",
                severity_floor="warning",
                check_id="validity.null.players.position",
            )
        )

    return results


# --- 3. impossible / future spine values ----------------------------------

def _scalar(conn: sqlite3.Connection, sql: str) -> int | None:
    try:
        row = conn.execute(sql).fetchone()
    except sqlite3.Error:
        return None
    return int(row[0]) if row and row[0] is not None else None


def _check_impossible_values(conn: sqlite3.Connection) -> list[CheckResult]:
    results: list[CheckResult] = []
    if not _table_exists(conn, "games"):
        return results
    gcols = _table_columns(conn, "games")

    # 3a. Future kickoff times (verified-clean 0 baseline).
    if "start_time_utc" in gcols:
        now = datetime.now(timezone.utc).isoformat(sep=" ", timespec="seconds")
        sql = (
            "SELECT COUNT(*) FROM games "
            "WHERE start_time_utc IS NOT NULL AND start_time_utc > ?"
        )
        try:
            n = int(conn.execute(sql, (now,)).fetchone()[0])
        except sqlite3.Error:
            n = None
        evidence = f"SELECT COUNT(*) FROM games WHERE start_time_utc > '{now}'"
        if n is None:
            results.append(CheckResult(
                "validity.future.games.start_time_utc", name, "games", None,
                "unknown", "info", "games.start_time_utc future-date query failed",
                evidence))
        elif n == 0:
            results.append(CheckResult(
                "validity.future.games.start_time_utc", name, "games", None,
                "pass", "warning",
                "games.start_time_utc: 0 games scheduled in the future (clean)",
                evidence))
        else:
            results.append(CheckResult(
                "validity.future.games.start_time_utc", name, "games", None,
                "fail", "warning",
                f"games.start_time_utc: {n} game(s) dated in the FUTURE (> now)",
                evidence))

    # 3b. Impossible scores (negative / > 100). Verified-clean 0 baseline.
    if "home_points" in gcols and "away_points" in gcols:
        sql = (
            "SELECT COUNT(*) FROM games WHERE "
            "home_points < 0 OR away_points < 0 OR "
            "home_points > 100 OR away_points > 100"
        )
        n = _scalar(conn, sql)
        if n is None:
            results.append(CheckResult(
                "validity.score.range.games", name, "games", None,
                "unknown", "info", "games score-range query failed", sql))
        elif n == 0:
            results.append(CheckResult(
                "validity.score.range.games", name, "games", None,
                "pass", "warning",
                "games scores: 0 negative / 0 over-100 (clean)", sql))
        else:
            results.append(CheckResult(
                "validity.score.range.games", name, "games", None,
                "fail", "warning",
                f"games scores: {n} row(s) with negative or >100 points", sql))

        # 3c. Completed-yet-scoreless (regulation ties impossible post-1996 OT).
        # Verified 21 baseline -> warning (mislabeled cancelled/forfeited games).
        if "status" in gcols:
            sql = (
                "SELECT COUNT(*) FROM games "
                "WHERE status='Final' AND home_points=0 AND away_points=0"
            )
            n = _scalar(conn, sql)
            if n is None:
                results.append(CheckResult(
                    "validity.score.scoreless_final.games", name, "games", None,
                    "unknown", "info", "games scoreless-Final query failed", sql))
            elif n == 0:
                results.append(CheckResult(
                    "validity.score.scoreless_final.games", name, "games", None,
                    "pass", "warning",
                    "games: 0 Final games scored 0-0 (clean)", sql))
            else:
                results.append(CheckResult(
                    "validity.score.scoreless_final.games", name, "games", None,
                    "fail", "warning",
                    (f"games: {n} Final game(s) scored 0-0 -- regulation ties are "
                     f"impossible post-1996 OT (likely cancelled/forfeited "
                     f"mislabeled Final)"),
                    sql))

    return results


# --- pillar entrypoint ----------------------------------------------------

def run(conn: sqlite3.Connection) -> list[CheckResult]:
    """Run the validity pillar: schema-drift + null-density + impossible values."""
    results: list[CheckResult] = []
    results.extend(_check_schema(conn))
    results.extend(_check_null_density(conn))
    results.extend(_check_impossible_values(conn))
    return results
