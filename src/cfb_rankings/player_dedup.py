"""Player dedup — find and merge duplicate-human ``players`` rows.

WHY THIS EXISTS
---------------
Different ingest paths created multiple ``players`` rows for the same human.
Example found 2026-06-10: Dillon Gabriel exists three times — pid 120 (honors
name-only insert, no source ids), pid 4344 (``cfbd-recruit`` row), pid 11737
(``cfbd`` athlete row, carries the Heisman data). The split scatters one
player's stats/mentions/honors across ghost ids, and every ghost gets anchored
by the player-ID anchor, freezing the split. Root cause is the honors ingest's
name-only entry point (see docs/research/player-id-stability-scoping-2026-05-21.md,
"drift mode #2").

SAFETY MODEL (conservative by construction)
-------------------------------------------
Same name does NOT mean same human — CFB is full of distinct players sharing a
name. A duplicate is auto-mergeable only when ALL of these hold:

* its name group (``lower(trim(full_name))``) contains EXACTLY ONE row with a
  ``cfbd`` athlete source id — that row is canonical. Groups with two or more
  cfbd rows are distinct humans and are never touched.
* the duplicate itself has NO ``cfbd`` athlete id (it may carry
  ``cfbd-recruit`` or nothing).
* year gate: if both sides have season evidence (honors / season stats /
  heisman / recruiting / transfer / roster years, draft year), the year ranges
  must overlap within ±1. A duplicate with NO year evidence is only removed
  when it also has no meaningful child rows (a dead row — deleted, not merged).
  Year evidence on the dup but none on the canonical -> skipped as ambiguous.

MERGE MECHANICS
---------------
Tables holding a ``player_id`` column are discovered from ``sqlite_master`` at
run time (36 as of 2026-06). For each: ``UPDATE OR IGNORE ... SET player_id =
canonical`` then ``DELETE`` whatever still points at the dup — rows that lost
the update collided with a unique constraint, i.e. the canonical already has
that exact row, so the dup's copy is redundant by definition. The dup's
``players`` row is deleted last. Everything runs in one transaction;
``merge_duplicates`` is dry-run unless ``commit=True``.

After a committed merge, refresh the player-ID anchor (``export-player-id-anchor``)
so external ids (e.g. the recruit id) re-anchor to the canonical player_id.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from cfb_rankings.db import Database

log = logging.getLogger(__name__)

# Tables with (player_id, season-ish year) used as identity evidence.
_YEAR_EVIDENCE = [
    ("player_honors", "season_year"),
    ("player_season_stats", "season_year"),
    ("heisman_rankings_weekly", "season_year"),
    ("recruiting_entries", "season_year"),
    ("player_recruiting_profiles", "season_year"),
    ("transfer_entries", "season_year"),
    ("roster_entries", "season_year"),
    ("player_nfl_draft", "draft_year"),
]

# Per-player caches/identity rows: their existence is not "meaningful data"
# when deciding whether a no-year duplicate is a dead row.
_NON_MEANINGFUL_TABLES = {"player_current_status_cache", "player_source_ids", "player_aliases"}


@dataclass
class MergePlan:
    canonical_id: int
    dup_id: int
    full_name: str
    action: str  # "merge" | "delete"
    dup_child_rows: int
    dup_years: tuple[int, int] | None
    canon_years: tuple[int, int] | None
    reason: str = ""


@dataclass
class AuditResult:
    plans: list[MergePlan] = field(default_factory=list)
    skipped_multi_cfbd: int = 0      # >=2 cfbd rows in group -> distinct humans
    skipped_no_cfbd: int = 0         # no canonical to merge into
    skipped_year_mismatch: int = 0   # year ranges don't touch -> likely distinct
    skipped_ambiguous: int = 0       # not enough evidence either way

    def summary(self) -> dict[str, int]:
        return {
            "merge": sum(1 for p in self.plans if p.action == "merge"),
            "delete_dead": sum(1 for p in self.plans if p.action == "delete"),
            "skipped_multi_cfbd_groups": self.skipped_multi_cfbd,
            "skipped_no_cfbd_groups": self.skipped_no_cfbd,
            "skipped_year_mismatch": self.skipped_year_mismatch,
            "skipped_ambiguous": self.skipped_ambiguous,
        }


def _player_id_tables(db: Database) -> list[str]:
    """Every real table (not ``players`` itself) carrying a player_id column."""
    tables = [
        r["name"]
        for r in db.query_all(
            "select name from sqlite_master where type = 'table' and name not like 'sqlite_%'"
        )
    ]
    out: list[str] = []
    for t in tables:
        if t == "players":
            continue
        cols = {r["name"] for r in db.query_all(f"pragma table_info({t})")}
        if "player_id" in cols:
            out.append(t)
    return out


def _years_by_pid(db: Database) -> dict[int, tuple[int, int]]:
    """player_id -> (min_year, max_year) across all year-evidence tables."""
    existing = {
        r["name"]
        for r in db.query_all("select name from sqlite_master where type = 'table'")
    }
    lo: dict[int, int] = {}
    hi: dict[int, int] = {}
    for table, col in _YEAR_EVIDENCE:
        if table not in existing:
            continue
        rows = db.query_all(
            f"select player_id, min({col}) as lo, max({col}) as hi"
            f"  from {table} where player_id is not null and {col} is not null"
            f"  group by player_id"
        )
        for r in rows:
            pid = int(r["player_id"])
            lo[pid] = min(lo.get(pid, 9999), int(r["lo"]))
            hi[pid] = max(hi.get(pid, 0), int(r["hi"]))
    return {pid: (lo[pid], hi[pid]) for pid in lo}


def _meaningful_child_counts(db: Database, tables: list[str]) -> dict[int, int]:
    """player_id -> total rows across all non-cache player_id tables."""
    counts: dict[int, int] = defaultdict(int)
    for t in tables:
        if t in _NON_MEANINGFUL_TABLES:
            continue
        for r in db.query_all(
            f"select player_id, count(*) as n from {t}"
            f" where player_id is not null group by player_id"
        ):
            counts[int(r["player_id"])] += int(r["n"])
    return dict(counts)


def _ranges_touch(a: tuple[int, int], b: tuple[int, int], slack: int = 1) -> bool:
    return a[0] - slack <= b[1] and b[0] - slack <= a[1]


def audit_duplicates(db: Database) -> AuditResult:
    """Build the conservative merge/delete plan. Read-only."""
    tables = _player_id_tables(db)
    years = _years_by_pid(db)
    child_counts = _meaningful_child_counts(db, tables)

    cfbd_pids = {
        int(r["player_id"])
        for r in db.query_all(
            "select distinct player_id from player_source_ids where source_name = 'cfbd'"
        )
    }

    groups: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for r in db.query_all("select player_id, full_name from players"):
        nm = (r["full_name"] or "").strip().lower()
        if nm:
            groups[nm].append((int(r["player_id"]), r["full_name"]))

    result = AuditResult()
    for nm, members in groups.items():
        if len(members) < 2:
            continue
        canon = [m for m in members if m[0] in cfbd_pids]
        if len(canon) > 1:
            result.skipped_multi_cfbd += 1
            continue
        if not canon:
            result.skipped_no_cfbd += 1
            continue
        canonical_id, _ = canon[0]
        canon_years = years.get(canonical_id)

        for dup_id, full_name in members:
            if dup_id == canonical_id:
                continue
            dup_years = years.get(dup_id)
            dup_children = child_counts.get(dup_id, 0)

            if dup_years and canon_years:
                if _ranges_touch(dup_years, canon_years):
                    result.plans.append(MergePlan(
                        canonical_id, dup_id, full_name, "merge",
                        dup_children, dup_years, canon_years,
                        reason=f"year overlap {dup_years}~{canon_years}",
                    ))
                else:
                    result.skipped_year_mismatch += 1
            elif dup_years and not canon_years:
                result.skipped_ambiguous += 1
            elif dup_children == 0:
                result.plans.append(MergePlan(
                    canonical_id, dup_id, full_name, "delete",
                    0, None, canon_years, reason="dead row: no years, no child data",
                ))
            else:
                # Child data but no year signal anywhere -> not enough evidence.
                result.skipped_ambiguous += 1
    return result


def merge_duplicates(db: Database, commit: bool = False) -> dict[str, int]:
    """Execute the audit plan. Dry-run (plan only) unless ``commit=True``.

    Returns the audit summary plus, when committed, rows_repointed and
    players_deleted counts.
    """
    audit = audit_duplicates(db)
    stats = audit.summary()
    if not commit:
        log.info("player-dedup DRY RUN: %s", stats)
        return stats

    tables = _player_id_tables(db)
    rows_repointed = 0
    players_deleted = 0
    with db.connection() as conn:
        for plan in audit.plans:
            if plan.action == "merge":
                for t in tables:
                    cur = conn.execute(
                        f"update or ignore {t} set player_id = ? where player_id = ?",
                        (plan.canonical_id, plan.dup_id),
                    )
                    rows_repointed += cur.rowcount if cur.rowcount > 0 else 0
                    # Whatever still points at the dup lost a unique-constraint
                    # race with a row the canonical already has -> redundant.
                    conn.execute(f"delete from {t} where player_id = ?", (plan.dup_id,))
            else:  # delete: dead row — still clear cache/source rows pointing at it
                for t in tables:
                    conn.execute(f"delete from {t} where player_id = ?", (plan.dup_id,))
            conn.execute("delete from players where player_id = ?", (plan.dup_id,))
            players_deleted += 1
        conn.commit()

    stats["rows_repointed"] = rows_repointed
    stats["players_deleted"] = players_deleted
    log.info("player-dedup COMMITTED: %s", stats)
    return stats


__all__ = ["audit_duplicates", "merge_duplicates", "AuditResult", "MergePlan"]
