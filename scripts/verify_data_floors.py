"""Data-floor gate: provenance coverage + factual-spine row floors (WP-0.4).

THE GAP THIS FILLS (2026-06-11)
-------------------------------
Two sibling guards already exist:
  * verify_source_health_floors.py — watches RAW source ingestion (scrape_health).
  * verify_module_coverage.py      — watches COMPUTED MODULE tables (discourse,
                                     atlas, mood, chronicle, ...) vs a baseline.
Neither watches:
  1. PROVENANCE — what fraction of conversation_documents carry a canonical
     source_id. This is a RATCHET: it must never regress, and as the WP-0.7
     labeling/reconstruction lands it should climb. A silent regression would
     undo provenance progress with no alarm.
  2. The FACTUAL SPINE — games / players / ratings / player_game_stats. These
     aren't "modules" or "sources", so neither guard sees them; yet if a broken
     build leaves them near-empty, the entire site (rankings, profiles) ships
     hollow. Absolute conservative floors (~half of healthy) catch that.

Read-only, stdlib + sqlite3. Wired NON-critical into build_publish.ps1 so a
regression is logged + exits 1 (visible) but never blocks the must-publish
deploy. The provenance baseline lives in a JSON state file and ratchets UP only.

Usage:
    python scripts/verify_data_floors.py [db_path] [--baseline <json>] [--json]
Exit codes (mirror the sibling guards):
    0 = all floors satisfied
    1 = one or more floors breached (regression)
    2 = DB missing / unreadable
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB = str(_REPO_ROOT / "cfb_rankings.db")
_DEFAULT_BASELINE = _REPO_ROOT / "data" / "data_floors_baseline.json"

# Provenance ratchet: today's source_id coverage must stay within TOL of the
# best (highest) coverage ever recorded. The baseline ratchets up as coverage
# improves, so WP-0.7 progress becomes the new floor.
PROVENANCE_TOLERANCE = 0.5  # percentage points of slack below the high-water mark

# Absolute floors for the factual spine. Set conservatively (~half of the
# healthy 2026-06-11 counts) so they fire ONLY on catastrophic emptiness, never
# on normal week-to-week variance. {table: (min_rows, what it powers)}.
SPINE_FLOORS: dict[str, tuple[int, str]] = {
    "games":               (7_000,   "schedules, results, rankings inputs"),
    "players":             (40_000,  "every player page + roster"),
    "player_game_stats":   (1_000_000, "player stat lines, game logs"),
    "power_ratings_weekly":(30_000,  "Power rankings (the core product)"),
    "resume_ratings_weekly":(25_000, "Resume rankings (Power-vs-Resume)"),
    "team_rating_deltas":  (8_000,   "movement / offseason + film-room hubs"),
    "roster_entries":      (20_000,  "rosters, recruiting footprint"),
}


def _scalar(conn: sqlite3.Connection, sql: str) -> "int | None":
    try:
        row = conn.execute(sql).fetchone()
    except sqlite3.Error as exc:
        print(f"::warning::query failed ({exc}): {sql[:70]}")
        return None
    return None if not row or row[0] is None else int(row[0])


def _load_baseline(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def evaluate(conn: sqlite3.Connection, baseline: dict) -> tuple[list[dict], dict]:
    findings: list[dict] = []

    # --- provenance ratchet ---
    total = _scalar(conn, "SELECT COUNT(*) FROM conversation_documents") or 0
    with_sid = _scalar(conn, "SELECT COUNT(*) FROM conversation_documents WHERE source_id IS NOT NULL") or 0
    pct = round(100.0 * with_sid / total, 2) if total else 0.0
    prev_high = float(baseline.get("source_id_pct_high", 0.0))
    if total and pct < prev_high - PROVENANCE_TOLERANCE:
        findings.append({
            "floor": "provenance:source_id_pct",
            "today": pct, "baseline": prev_high,
            "detail": f"conversation_documents source_id coverage {pct}% < high-water {prev_high}% "
                      f"(- {PROVENANCE_TOLERANCE}pp tolerance)",
        })
    new_high = max(prev_high, pct)  # ratchet up only

    # --- spine floors ---
    spine_status = {}
    for tbl, (floor, powers) in SPINE_FLOORS.items():
        n = _scalar(conn, f'SELECT COUNT(*) FROM "{tbl}"')
        spine_status[tbl] = n
        if n is None:
            findings.append({"floor": f"spine:{tbl}", "today": None, "baseline": floor,
                             "detail": f"{tbl} unreadable (missing table?) — powers {powers}"})
        elif n < floor:
            findings.append({"floor": f"spine:{tbl}", "today": n, "baseline": floor,
                             "detail": f"{tbl} has {n} rows < floor {floor} — powers {powers}"})

    stats = {"source_id_pct": pct, "source_id_pct_high": new_high,
             "conversation_documents": total, "spine": spine_status}
    new_baseline = dict(baseline)
    new_baseline["source_id_pct_high"] = new_high
    return findings, {"stats": stats, "new_baseline": new_baseline}


def main(argv: "list[str] | None" = None) -> int:
    p = argparse.ArgumentParser(description="Provenance + factual-spine data-floor gate.")
    p.add_argument("db_path", nargs="?", default=_DEFAULT_DB)
    p.add_argument("--baseline", default=str(_DEFAULT_BASELINE))
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-write", action="store_true", help="don't update the ratchet baseline (testing)")
    args = p.parse_args(argv)

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"::error::DB not found: {db_path}")
        return 2
    try:
        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True, timeout=10)
        conn.execute("PRAGMA busy_timeout=8000")
    except sqlite3.Error as exc:
        print(f"::error::cannot open DB read-only: {exc}")
        return 2

    baseline_path = Path(args.baseline)
    baseline = _load_baseline(baseline_path)
    try:
        findings, out = evaluate(conn, baseline)
    finally:
        conn.close()

    # Persist the ratcheted baseline (only ever raises the provenance floor).
    if not args.no_write:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(out["new_baseline"], indent=2, sort_keys=True), encoding="utf-8")

    if args.json:
        print(json.dumps({"findings": findings, **out["stats"]}, indent=2, default=str))

    s = out["stats"]
    print(f"data floors: source_id {s['source_id_pct']}% (high-water {s['source_id_pct_high']}%), "
          f"spine={ {k: v for k, v in s['spine'].items()} }")
    if not findings:
        print("data floors OK: provenance ratchet held; all spine tables above floor.")
        return 0
    print(f"::warning::{len(findings)} data floor(s) breached:")
    for f in findings:
        print(f"  - {f['floor']}: {f['detail']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
