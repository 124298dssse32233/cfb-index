"""Refuse-to-upload sanity gate for the rolling cfb-rankings-db artifact.

THE BUG THIS PREVENTS (Sprint v5-5 hard-stop investigation, 2026-05-15):
21 workflows upload the cfb-rankings-db artifact. Small workflows
(daily, wire, mailbag, ingest_hourly, etc.) touch a tiny slice of the
DB. Their start-of-workflow init-db creates schema, but they only
populate the tables relevant to their work. When they upload the
result, the DB is FAR smaller than the post-backfill state.

The rolling cycle: backfill produces a 165 MB DB → uploads → next
hour's ingest_hourly downloads it → init-db is idempotent (won't
touch existing data) → ingest runs, populating a few thousand new
rows → uploads the WHOLE cfb_rankings.db → now the rolling artifact
is still ~165 MB, fine.

The poisoning: somewhere along the chain a workflow's init-db ran
against a near-empty download (cause TBD — possibly a workflow that
explicitly drops + recreates tables, or an earlier failure that
uploaded a near-empty DB). After that point, every subsequent
workflow downloads the 14 MB version, runs init-db over it (creates
empty schema), writes its slice (a few KB), and uploads a still-14 MB
version. The cycle perpetuates poison.

THE FIX: before uploading, verify the DB is "healthy" — has at least
the minimum row counts that a real DB should have. Refuse otherwise.

A workflow that's making a small change still gets to publish, but
ONLY if the DB it started from was already healthy. A workflow
working against a poisoned DB will fail the gate and refuse to
upload — preserving the rolling artifact at its last healthy state.

Usage in a workflow:
    - name: Verify DB artifact is healthy before upload
      run: python scripts/verify_db_artifact_healthy.py cfb_rankings.db
    - name: Upload DB artifact
      if: success()
      uses: actions/upload-artifact@v4
      ...

Exit codes:
    0 = healthy, safe to upload
    2 = unhealthy, refuse upload (workflow step fails, ::error:: surfaced)
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────
# Health thresholds
#
# These are the FLOOR row counts for the post-backfill steady state.
# A DB below ANY of these in ALL surveyed tables is treated as poisoned
# (init-db ran over empty input, populated only its tiny slice, about
# to upload partial state).
#
# Sized conservatively against the 2026-05-15 healthy artifact
# (run 25926317548 backfill output, 828 MB on disk, 165 MB compressed):
#   teams: 699 rows
#   team_seasons: ~5,000+ rows
#   games: ~25,000+ rows
#   roster_entries: ~95,000+ rows
#   player_value_metrics: ~4,000+ rows
#   conversation_documents: ~200,000+ rows (varies by ingest cadence)
#
# Set thresholds at ~20% of the steady-state to catch a complete data
# wipe without flagging a normal data-evolution swing.
# ─────────────────────────────────────────────────────────────────────────

CORE_TABLE_FLOORS: dict[str, int] = {
    "teams": 500,
    "team_seasons": 1000,
    "games": 5000,
    "roster_entries": 20000,
    "player_value_metrics": 500,
}

# Minimum file size in bytes. The healthy artifact is ~800 MB on disk.
# A poisoned artifact has been observed at 14 MB. Floor at 50 MB
# catches the 14 MB case without flagging slight schema swings.
MIN_FILE_SIZE_BYTES = 50 * 1024 * 1024


def verify(db_path: str) -> tuple[bool, list[str]]:
    """Return (healthy, reasons). On unhealthy, reasons lists each failure."""
    reasons: list[str] = []

    # File size check
    if not os.path.exists(db_path):
        return False, [f"DB file not found: {db_path}"]
    size = os.path.getsize(db_path)
    if size < MIN_FILE_SIZE_BYTES:
        reasons.append(
            f"file size {size:,} bytes < {MIN_FILE_SIZE_BYTES:,} byte floor "
            f"(50 MB) — likely poisoned artifact, near-empty DB"
        )

    # Table row count checks
    try:
        conn = sqlite3.connect(db_path)
        for table, floor in CORE_TABLE_FLOORS.items():
            try:
                row = conn.execute(
                    f"SELECT count(*) FROM {table}"
                ).fetchone()
                count = row[0] if row else 0
            except sqlite3.OperationalError as exc:
                reasons.append(f"table '{table}' missing or unreadable ({exc})")
                continue
            if count < floor:
                reasons.append(
                    f"table '{table}' has {count:,} rows < {floor:,} floor"
                )
        conn.close()
    except sqlite3.Error as exc:
        return False, [f"DB connection failed: {exc}"]

    return not reasons, reasons


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sanity gate for the rolling cfb-rankings-db artifact."
    )
    parser.add_argument(
        "db_path",
        nargs="?",
        default="cfb_rankings.db",
        help="Path to the DB file to verify (default: cfb_rankings.db)",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="DEBUG ONLY: skip all checks. Never set this in workflows.",
    )
    args = parser.parse_args(argv)

    if args.allow_empty:
        print("::warning::verify_db_artifact_healthy: --allow-empty set, skipping all checks")
        return 0

    healthy, reasons = verify(args.db_path)
    if healthy:
        size_mb = os.path.getsize(args.db_path) / (1024 * 1024)
        print(f"DB artifact healthy: {args.db_path} ({size_mb:.1f} MB)")
        return 0

    print(f"::error::DB artifact at {args.db_path} failed sanity gate.")
    print(f"Reasons ({len(reasons)}):")
    for r in reasons:
        print(f"  - {r}")
    print()
    print("REFUSING TO UPLOAD. The rolling artifact stays at its last healthy state.")
    print("If this is a legitimate near-empty state (e.g. fresh DB init in CI),")
    print("set --allow-empty explicitly. Otherwise, investigate why the DB lost data.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
