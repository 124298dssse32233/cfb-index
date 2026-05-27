"""Wave 25 — load player_depth_chart_2026 from data/depth_chart_2026.csv.

CSV-driven, idempotent UPSERT. Same audit/prune pattern as load_award_watch.py.

CSV format (header row required, lines starting with `#` ignored):
    player_id,full_name_for_audit,position_group,slot_rank,
    starter_status,confidence,source,source_url,as_of,notes

Run:
    python scripts/load_depth_chart.py
    python scripts/load_depth_chart.py --dry-run
    python scripts/load_depth_chart.py --prune-source manual_editorial
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "cfb_rankings.db"
DEFAULT_CSV = ROOT / "data" / "depth_chart_2026.csv"


def load(csv_path: Path, db_path: Path, dry_run: bool, prune_source: str | None) -> int:
    con = sqlite3.connect(str(db_path), timeout=120)
    con.execute("PRAGMA busy_timeout=120000")
    cur = con.cursor()

    valid_pids: set[int] = {r[0] for r in cur.execute("SELECT player_id FROM players").fetchall()}

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
    rows_skipped_audit = 0
    rows_skipped_ineligible = 0
    ineligible_examples: list[str] = []
    seen_keys: set[tuple] = set()
    name_warnings: list[str] = []

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        lines = [ln for ln in f if not ln.strip().startswith("#")]
        reader = csv.DictReader(lines)
        for row in reader:
            try:
                pid = int(row["player_id"].strip())
            except (ValueError, KeyError):
                continue
            if pid not in valid_pids:
                rows_skipped_missing_pid += 1
                continue
            if pid in ineligible_pids:
                rows_skipped_ineligible += 1
                audit_name = (row.get("full_name_for_audit") or "").strip()
                if len(ineligible_examples) < 10:
                    ineligible_examples.append(f"pid={pid} {audit_name}")
                continue

            audit_name = (row.get("full_name_for_audit") or "").strip()
            if audit_name:
                actual = cur.execute("SELECT full_name FROM players WHERE player_id=?", (pid,)).fetchone()
                if actual and actual[0].strip().lower() != audit_name.lower():
                    name_warnings.append(
                        f"  audit-mismatch pid={pid} csv={audit_name!r} db={actual[0]!r}"
                    )
                    rows_skipped_audit += 1
                    continue

            pg = row["position_group"].strip()
            key = (pid, 2026, pg)
            if key in seen_keys:
                print(f"  WARN: duplicate key pid={pid} {pg}")
                continue
            seen_keys.add(key)

            slot_rank = int(row.get("slot_rank") or 1)
            starter_status = row["starter_status"].strip()
            confidence = (row.get("confidence") or "projected").strip()
            source = (row.get("source") or "csv_load").strip()
            source_url = (row.get("source_url") or "").strip() or None
            as_of = (row.get("as_of") or "").strip()
            notes = (row.get("notes") or "").strip() or None

            if dry_run:
                rows_written += 1
                continue

            cur.execute(
                """
                INSERT OR REPLACE INTO player_depth_chart_2026
                    (player_id, season_year, position_group, slot_rank,
                     starter_status, confidence, source, source_url, as_of, notes)
                VALUES (?, 2026, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (pid, pg, slot_rank, starter_status, confidence, source, source_url, as_of, notes),
            )
            rows_written += 1

    pruned = 0
    if prune_source and not dry_run:
        existing = cur.execute(
            "SELECT player_id, season_year, position_group FROM player_depth_chart_2026 WHERE source=?",
            (prune_source,),
        ).fetchall()
        for ex in existing:
            if tuple(ex) not in seen_keys:
                cur.execute(
                    "DELETE FROM player_depth_chart_2026 WHERE player_id=? AND season_year=? AND position_group=?",
                    ex,
                )
                pruned += 1

    if not dry_run:
        con.commit()

    print(f"Depth chart load: wrote {rows_written}, skipped_missing_pid={rows_skipped_missing_pid}, "
          f"skipped_audit={rows_skipped_audit}, "
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

    if not dry_run:
        for pg, n in cur.execute(
            "SELECT position_group, COUNT(*) FROM player_depth_chart_2026 GROUP BY position_group ORDER BY position_group"
        ).fetchall():
            print(f"    {pg:6} {n:3} rows")
    con.close()
    return rows_written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--db",  type=Path, default=DEFAULT_DB)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--prune-source", type=str, default="manual_editorial")
    args = ap.parse_args()
    if not args.csv.exists():
        sys.exit(f"CSV not found: {args.csv}")
    load(args.csv, args.db, args.dry_run, args.prune_source)


if __name__ == "__main__":
    main()
