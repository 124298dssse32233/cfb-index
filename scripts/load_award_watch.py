"""Wave 25 — load player_award_watch_2026 from data/award_watch_2026.csv.

The CSV is the canonical source-of-truth — easy to edit, audit, diff.
This loader UPSERTs idempotently and prunes rows whose source set was
"replaced" (rows present in DB but absent from CSV for the same as_of
date are kept; rows past their expiration cycle are cleared if --prune
specified).

CSV format (header row required):
    player_id,full_name_for_audit,award_slug,list_type,
    position_rank,priority,source,source_url,as_of,notes

Lines starting with `#` (after stripping whitespace) are comments.

Run:
    python scripts/load_award_watch.py
    python scripts/load_award_watch.py --csv data/award_watch_2026.csv
    python scripts/load_award_watch.py --dry-run
    python scripts/load_award_watch.py --prune-source consensus_may_2026
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "cfb_rankings.db"
DEFAULT_CSV = ROOT / "data" / "award_watch_2026.csv"


def load(csv_path: Path, db_path: Path, dry_run: bool, prune_source: str | None) -> int:
    con = sqlite3.connect(str(db_path), timeout=120)
    con.execute("PRAGMA busy_timeout=120000")
    cur = con.cursor()

    # Build pid validation cache
    valid_pids: set[int] = {r[0] for r in cur.execute("SELECT player_id FROM players").fetchall()}

    # Build name→pid resolution map for self-healing across DB rebuilds.
    # The artifact DB (used by CI) and local DB can have diverged player_id
    # assignments (e.g. Arch Manning = 48391 in artifact, 13074 in local).
    # full_name_for_audit in the CSV is the authoritative identifier; we use
    # it to resolve to the DB's actual player_id rather than the CSV's stale
    # hint.  Ambiguous names (multiple players share the same full_name) are
    # excluded — those fall back to the CSV pid.
    _name_pid_raw: dict[str, list[int]] = {}
    for _pid_r, _name_r in cur.execute("SELECT player_id, full_name FROM players"):
        if not _name_r:
            continue
        _key = _name_r.strip().lower()
        _name_pid_raw.setdefault(_key, []).append(_pid_r)
    name_to_pid: dict[str, int] = {
        k: v[0] for k, v in _name_pid_raw.items() if len(v) == 1
    }

    # Skip players whose current status indicates they're not on a 2026 college roster.
    # The cache table is the canonical source. Falls back to view if cache missing.
    try:
        ineligible_pids = {
            r[0] for r in cur.execute(
                "SELECT player_id FROM player_current_status_cache "
                "WHERE status_code IN ('NFL_DRAFTED_2026','NFL_DRAFTED_PRIOR','NFL_UDFA',"
                "                      'EXHAUSTED_ELIGIBILITY','MEDICAL_RETIREMENT','HISTORICAL_ALUM')"
            ).fetchall()
        }
    except sqlite3.OperationalError:
        ineligible_pids = set()
        print("  WARN: player_current_status_cache missing — drafted-player guard disabled")

    rows_written = 0
    rows_skipped_missing_pid = 0
    rows_skipped_audit_mismatch = 0
    rows_skipped_ineligible = 0
    rows_resolved_by_name = 0
    ineligible_examples: list[str] = []
    seen_keys: set[tuple] = set()
    name_warnings: list[str] = []

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        # Skip leading comment lines, then read header
        lines = []
        for raw in f:
            if raw.strip().startswith("#"):
                continue
            lines.append(raw)
        reader = csv.DictReader(lines)
        for row in reader:
            try:
                pid = int(row["player_id"].strip())
            except (ValueError, KeyError):
                continue

            audit_name = (row.get("full_name_for_audit") or "").strip()

            # Name-based resolution: use the DB's actual player_id for this
            # name when the CSV pid either doesn't exist in this DB or maps to
            # a different player.  This makes the seeder self-healing across
            # DB rebuilds where player_id assignments diverge.
            if audit_name:
                db_name_for_pid = (cur.execute(
                    "SELECT full_name FROM players WHERE player_id=?", (pid,)
                ).fetchone() or (None,))[0]
                if db_name_for_pid is None or db_name_for_pid.strip().lower() != audit_name.lower():
                    # CSV pid doesn't exist or maps to someone else — try name lookup
                    resolved = name_to_pid.get(audit_name.lower())
                    if resolved:
                        if resolved != pid:
                            print(f"  pid resolved by name: {audit_name!r} "
                                  f"csv_pid={pid} -> db_pid={resolved}")
                            rows_resolved_by_name += 1
                        pid = resolved
                    elif pid not in valid_pids:
                        rows_skipped_missing_pid += 1
                        continue
                    else:
                        # pid is valid but name mismatches and name is ambiguous/missing
                        name_warnings.append(
                            f"  audit-mismatch (no resolution): pid={pid} "
                            f"csv={audit_name!r} db={db_name_for_pid!r}"
                        )
                        rows_skipped_audit_mismatch += 1
                        continue

            if pid not in valid_pids:
                rows_skipped_missing_pid += 1
                continue
            if pid in ineligible_pids:
                rows_skipped_ineligible += 1
                if len(ineligible_examples) < 10:
                    ineligible_examples.append(f"pid={pid} {audit_name}")
                continue

            award_slug = row["award_slug"].strip()
            list_type = row["list_type"].strip()
            key = (pid, 2026, award_slug, list_type)
            if key in seen_keys:
                print(f"  WARN: duplicate key in CSV pid={pid} {award_slug}/{list_type}")
                continue
            seen_keys.add(key)

            pos_rank = int(row["position_rank"]) if row.get("position_rank", "").strip() else None
            priority = int(row.get("priority") or 5)
            source = (row.get("source") or "csv_load").strip()
            source_url = (row.get("source_url") or "").strip() or None
            as_of = (row.get("as_of") or "").strip()
            notes = (row.get("notes") or "").strip() or None

            if dry_run:
                rows_written += 1
                continue

            cur.execute(
                """
                INSERT OR REPLACE INTO player_award_watch_2026
                    (player_id, season_year, award_slug, list_type,
                     position_rank, priority, source, source_url, as_of, notes)
                VALUES (?, 2026, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (pid, award_slug, list_type, pos_rank, priority, source, source_url, as_of, notes),
            )
            rows_written += 1

    pruned = 0
    if prune_source and not dry_run:
        # Delete rows from this source whose key is not in seen_keys
        existing = cur.execute(
            "SELECT player_id, season_year, award_slug, list_type FROM player_award_watch_2026 WHERE source=?",
            (prune_source,),
        ).fetchall()
        for ex in existing:
            if tuple(ex) not in seen_keys:
                cur.execute(
                    "DELETE FROM player_award_watch_2026 WHERE player_id=? AND season_year=? AND award_slug=? AND list_type=?",
                    ex,
                )
                pruned += 1

    if not dry_run:
        con.commit()

    print(f"Award watch load: wrote {rows_written}, "
          f"resolved_by_name={rows_resolved_by_name}, "
          f"skipped_missing_pid={rows_skipped_missing_pid}, "
          f"skipped_audit_mismatch={rows_skipped_audit_mismatch}, "
          f"skipped_ineligible(drafted/exhausted)={rows_skipped_ineligible}, "
          f"pruned={pruned}")
    if ineligible_examples:
        print("Ineligible (player drafted/exhausted — remove from CSV):")
        for ex in ineligible_examples:
            print(f"  {ex}")
    if name_warnings:
        print("Audit mismatches (first 10):")
        for w in name_warnings[:10]:
            print(w)
    if dry_run:
        print("(dry-run — no DB writes)")

    # Summary by award
    if not dry_run:
        for award, n in cur.execute(
            "SELECT award_slug, COUNT(*) FROM player_award_watch_2026 GROUP BY award_slug ORDER BY award_slug"
        ).fetchall():
            print(f"    {award:20} {n:3} rows")

    con.close()
    return rows_written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--db",  type=Path, default=DEFAULT_DB)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--prune-source", type=str, default="consensus_may_2026",
                    help="Delete rows from this source whose key isn't in the CSV (default: consensus_may_2026)")
    args = ap.parse_args()
    if not args.csv.exists():
        sys.exit(f"CSV not found: {args.csv}")
    load(args.csv, args.db, args.dry_run, args.prune_source)


if __name__ == "__main__":
    main()
