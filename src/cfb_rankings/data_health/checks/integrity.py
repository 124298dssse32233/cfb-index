"""Integrity pillar — cheap anti-join / grain / value checks on the game spine.

This pillar locks the *currently-clean* baseline: every assertion here is verified
to return 0 against the live ``cfb_rankings.db`` (except the one warning baseline,
``games`` completed-but-scoreless = 21). So once wired into the gate, ANY future
regression — a duplicated grain row, an orphaned FK, an impossible score — flips
the check to ``fail`` and the gate refuses GREEN.

Checks (all spine, all count-based; pass iff count == 0):
  * duplicate grain          games.game_id ; player_game_stats.player_game_stat_id
  * orphan FK anti-joins     player_game_stats.{game_id,player_id,team_id} ;
                             roster_entries.{player_id,team_id} ;
                             games.{home_team_id,away_team_id}
  * impossible values        games.home_points / away_points < 0 or > 100
  * completed-but-scoreless  games with a recorded (non-null) home_points but
                             home_points = 0 AND away_points = 0  (warning; =21 baseline)

Read-only: every statement is a SELECT COUNT(*). stdlib + raw sqlite3 only.
"""
from __future__ import annotations

import sqlite3

from .base import CheckResult

name = "integrity"

_PILLAR = "integrity"


def _count(conn: sqlite3.Connection, sql: str) -> int | None:
    """Run a scalar COUNT(*) query; return None if it can't evaluate.

    A missing table / renamed column is exactly the kind of fault this spine
    exists to surface, so we don't swallow it into a passing 0 — we return None
    and the caller emits status='unknown' (which never collapses to GREEN).
    """
    try:
        row = conn.execute(sql).fetchone()
    except sqlite3.Error:
        return None
    if row is None or row[0] is None:
        return None
    return int(row[0])


def _zero_check(
    conn: sqlite3.Connection,
    *,
    check_id: str,
    dataset: str,
    sql: str,
    label: str,
    severity: str = "critical",
) -> CheckResult:
    """Generic 'this count must be 0' assertion -> one CheckResult.

    count == 0  -> pass
    count > 0   -> fail (regression against the locked-clean baseline)
    count None  -> unknown (query could not evaluate; e.g. table/column gone)
    """
    n = _count(conn, sql)
    if n is None:
        return CheckResult(
            check_id=check_id,
            pillar=_PILLAR,
            dataset=dataset,
            season=None,
            status="unknown",
            severity=severity,
            detail=f"{label}: could not evaluate (table/column missing?)",
            evidence_sql=sql,
        )
    if n == 0:
        return CheckResult(
            check_id=check_id,
            pillar=_PILLAR,
            dataset=dataset,
            season=None,
            status="pass",
            severity=severity,
            detail=f"{label}: 0 (baseline clean)",
            evidence_sql=sql,
        )
    return CheckResult(
        check_id=check_id,
        pillar=_PILLAR,
        dataset=dataset,
        season=None,
        status="fail",
        severity=severity,
        detail=f"{label}: {n} (expected 0)",
        evidence_sql=sql,
    )


# --- Duplicate-grain assertions ------------------------------------------
# The grain column is declared unique on the spine; any GROUP BY ... HAVING
# COUNT(*) > 1 group is a broken uniqueness invariant.

def _dup_grain(
    conn: sqlite3.Connection,
    *,
    table: str,
    grain_col: str,
    check_id: str,
) -> CheckResult:
    sql = (
        f"SELECT COUNT(*) FROM "
        f"(SELECT {grain_col} FROM {table} "
        f"GROUP BY {grain_col} HAVING COUNT(*) > 1)"
    )
    return _zero_check(
        conn,
        check_id=check_id,
        dataset=table,
        sql=sql,
        label=f"duplicate grain ({table}.{grain_col})",
        severity="critical",
    )


# --- Orphan-FK anti-joins -------------------------------------------------
# A LEFT JOIN to the parent where the FK is non-null but the parent row is
# absent. NULL FK is not an orphan (that's a null-density concern, owned by the
# validity pillar), so the WHERE guards on the child column being non-null.

def _orphan_fk(
    conn: sqlite3.Connection,
    *,
    child_table: str,
    fk_col: str,
    parent_table: str,
    parent_col: str,
    check_id: str,
    alias_c: str = "c",
    alias_p: str = "p",
) -> CheckResult:
    sql = (
        f"SELECT COUNT(*) FROM {child_table} {alias_c} "
        f"LEFT JOIN {parent_table} {alias_p} "
        f"ON {alias_c}.{fk_col} = {alias_p}.{parent_col} "
        f"WHERE {alias_c}.{fk_col} IS NOT NULL "
        f"AND {alias_p}.{parent_col} IS NULL"
    )
    return _zero_check(
        conn,
        check_id=check_id,
        dataset=child_table,
        sql=sql,
        label=f"orphan FK ({child_table}.{fk_col} -> {parent_table}.{parent_col})",
        severity="critical",
    )


def run(conn: sqlite3.Connection) -> list[CheckResult]:
    """Run every integrity assertion against the spine and return the rows."""
    results: list[CheckResult] = []

    # --- duplicate grain --------------------------------------------------
    results.append(
        _dup_grain(
            conn,
            table="games",
            grain_col="game_id",
            check_id="integrity.dup_grain.games",
        )
    )
    results.append(
        _dup_grain(
            conn,
            table="player_game_stats",
            grain_col="player_game_stat_id",
            check_id="integrity.dup_grain.player_game_stats",
        )
    )

    # --- orphan FKs -------------------------------------------------------
    # player_game_stats -> games / players / teams
    results.append(
        _orphan_fk(
            conn,
            child_table="player_game_stats",
            fk_col="game_id",
            parent_table="games",
            parent_col="game_id",
            check_id="integrity.orphan_fk.player_game_stats.game_id",
        )
    )
    results.append(
        _orphan_fk(
            conn,
            child_table="player_game_stats",
            fk_col="player_id",
            parent_table="players",
            parent_col="player_id",
            check_id="integrity.orphan_fk.player_game_stats.player_id",
        )
    )
    results.append(
        _orphan_fk(
            conn,
            child_table="player_game_stats",
            fk_col="team_id",
            parent_table="teams",
            parent_col="team_id",
            check_id="integrity.orphan_fk.player_game_stats.team_id",
        )
    )
    # roster_entries -> players / teams
    results.append(
        _orphan_fk(
            conn,
            child_table="roster_entries",
            fk_col="player_id",
            parent_table="players",
            parent_col="player_id",
            check_id="integrity.orphan_fk.roster_entries.player_id",
        )
    )
    results.append(
        _orphan_fk(
            conn,
            child_table="roster_entries",
            fk_col="team_id",
            parent_table="teams",
            parent_col="team_id",
            check_id="integrity.orphan_fk.roster_entries.team_id",
        )
    )
    # games -> teams (home + away)
    results.append(
        _orphan_fk(
            conn,
            child_table="games",
            fk_col="home_team_id",
            parent_table="teams",
            parent_col="team_id",
            check_id="integrity.orphan_fk.games.home_team_id",
        )
    )
    results.append(
        _orphan_fk(
            conn,
            child_table="games",
            fk_col="away_team_id",
            parent_table="teams",
            parent_col="team_id",
            check_id="integrity.orphan_fk.games.away_team_id",
        )
    )

    # --- impossible values ------------------------------------------------
    # A CFB final score below 0 or above 100 is physically impossible; either
    # bound is a data-corruption signal. Guarded on non-null so a not-yet-played
    # game (null points) is not counted.
    results.append(
        _zero_check(
            conn,
            check_id="integrity.impossible_score.games",
            dataset="games",
            sql=(
                "SELECT COUNT(*) FROM games WHERE "
                "(home_points IS NOT NULL AND (home_points < 0 OR home_points > 100)) "
                "OR (away_points IS NOT NULL AND (away_points < 0 OR away_points > 100))"
            ),
            label="impossible score (home/away_points < 0 or > 100)",
            severity="critical",
        )
    )

    # --- completed-but-scoreless (warning baseline = 21) ------------------
    # A game with a recorded (non-null) home score but 0-0 final is almost
    # always a completed game whose box score never landed. 21 such rows are the
    # current locked baseline, so this is a WARNING (not critical) and emits the
    # observed count in the detail so the gate can trend it rather than red-line.
    n_scoreless = _count(
        conn,
        "SELECT COUNT(*) FROM games "
        "WHERE home_points IS NOT NULL AND home_points = 0 AND away_points = 0",
    )
    scoreless_sql = (
        "SELECT COUNT(*) FROM games "
        "WHERE home_points IS NOT NULL AND home_points = 0 AND away_points = 0"
    )
    if n_scoreless is None:
        results.append(
            CheckResult(
                check_id="integrity.completed_scoreless.games",
                pillar=_PILLAR,
                dataset="games",
                season=None,
                status="unknown",
                severity="warning",
                detail="completed-but-scoreless (0-0 with non-null home_points): "
                "could not evaluate",
                evidence_sql=scoreless_sql,
            )
        )
    elif n_scoreless == 0:
        results.append(
            CheckResult(
                check_id="integrity.completed_scoreless.games",
                pillar=_PILLAR,
                dataset="games",
                season=None,
                status="pass",
                severity="warning",
                detail="completed-but-scoreless (0-0 with non-null home_points): 0",
                evidence_sql=scoreless_sql,
            )
        )
    else:
        # Non-zero is the known baseline (21). Surface it as a warning fail so
        # the count is visible and any *increase* is noticed, without red-lining
        # the spine on a long-standing, accepted condition.
        results.append(
            CheckResult(
                check_id="integrity.completed_scoreless.games",
                pillar=_PILLAR,
                dataset="games",
                season=None,
                status="fail",
                severity="warning",
                detail=(
                    f"completed-but-scoreless (0-0 with non-null home_points): "
                    f"{n_scoreless} (baseline 21; investigate any increase)"
                ),
                evidence_sql=scoreless_sql,
            )
        )

    return results
