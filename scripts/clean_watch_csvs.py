"""Wave 25 — strip rows for drafted/exhausted players from watch CSVs.

Reads cfb_rankings.db's player_current_status_cache, finds ineligible
pids (status code = NFL_DRAFTED_*, EXHAUSTED, MEDICAL, HISTORICAL),
and rewrites the CSV with those rows removed. Comments and headers
preserved.

This is a one-shot cleanup. The weekly refresh workflow runs the
loaders, which already skip ineligible pids — this just keeps the
CSV honest.

Run: python scripts/clean_watch_csvs.py [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import io
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "cfb_rankings.db"
AWARD_CSV = ROOT / "data" / "award_watch_2026.csv"
DEPTH_CSV = ROOT / "data" / "depth_chart_2026.csv"


def _ineligible_pids() -> set[int]:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro&immutable=1", uri=True)
    rows = con.execute(
        "SELECT player_id FROM player_current_status_cache "
        "WHERE status_code IN ('NFL_DRAFTED_2026','NFL_DRAFTED_PRIOR','NFL_UDFA',"
        "                      'EXHAUSTED_ELIGIBILITY','MEDICAL_RETIREMENT','HISTORICAL_ALUM')"
    ).fetchall()
    con.close()
    return {r[0] for r in rows}


def _clean_csv(path: Path, ineligible: set[int], dry_run: bool) -> tuple[int, int]:
    """Returns (rows_kept, rows_dropped)."""
    text = path.read_text(encoding="utf-8")
    kept_lines: list[str] = []
    dropped = 0
    kept = 0
    # Pass through comment lines + header + data rows we keep
    header_seen = False
    for line in text.splitlines(keepends=False):
        if line.strip().startswith("#") or not line.strip():
            kept_lines.append(line)
            continue
        if not header_seen:
            kept_lines.append(line)
            header_seen = True
            header_cols = next(csv.reader([line]))
            continue
        # Parse data row to extract player_id
        try:
            parsed = next(csv.reader([line]))
            row = dict(zip(header_cols, parsed))
            pid = int(row.get("player_id", "0").strip())
        except (ValueError, StopIteration):
            kept_lines.append(line)
            continue
        if pid in ineligible:
            dropped += 1
            continue
        kept_lines.append(line)
        kept += 1

    if not dry_run:
        # Preserve trailing newline if original had one
        ending = "\n" if text.endswith("\n") else ""
        path.write_text("\n".join(kept_lines) + ending, encoding="utf-8")
    return kept, dropped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    ineligible = _ineligible_pids()
    print(f"Ineligible pids in DB: {len(ineligible):,}")

    for csv_path in (AWARD_CSV, DEPTH_CSV):
        if not csv_path.exists():
            print(f"  SKIP (missing): {csv_path.name}")
            continue
        kept, dropped = _clean_csv(csv_path, ineligible, args.dry_run)
        verb = "would drop" if args.dry_run else "dropped"
        print(f"  {csv_path.name}: kept {kept} rows, {verb} {dropped} ineligible rows")


if __name__ == "__main__":
    main()
