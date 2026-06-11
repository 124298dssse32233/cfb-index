"""Label conversation_documents provenance honestly (WP-0.7).

WHY (CP-4, Discover §1 #4 / §8)
-------------------------------
Only ~22% of conversation_documents carry a canonical `source_id`; the other
~78% are legacy reddit/youtube/board rows whose collectors set `source_name`
but never the canonical id. The adversarial council was unanimous: **LABEL the
legacy rows, do NOT infer a source_id** — inferring an id from `source_name`
risks silent mis-attribution and would permanently corrupt the audit trail.

This script writes a `provenance_status` column:
    'canonical'         — row has a real source_id (modern collectors)
    'legacy_unverified' — source_id is NULL (legacy reddit/youtube/board): the
                          origin is recorded (source_name/channel/url) but not
                          tied to a registry source_id and not reconstructed.

It is IDEMPOTENT (re-running yields the same state), DEFENSIVE (adds the column
if missing), and REVERSIBLE (`--revert` nulls the column; a DB .bak is the
belt-and-suspenders rollback). `--dry-run` reports the split WITHOUT writing,
so it can be validated against the live DB read-only.

Wired non-critical into build_publish.ps1 so the box keeps provenance honest on
every build. Stdlib + sqlite3 only.

Usage:
    python scripts/backfill_provenance_status.py [--db cfb_rankings.db] [--dry-run] [--revert]
Exit codes: 0 ok · 2 DB missing/unreadable.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB = str(_REPO_ROOT / "cfb_rankings.db")
_TABLE = "conversation_documents"
_COL = "provenance_status"


def _has_column(conn: sqlite3.Connection, table: str, col: str) -> bool:
    return any(r[1] == col for r in conn.execute(f'PRAGMA table_info("{table}")'))


def _counts(conn: sqlite3.Connection) -> dict:
    total = conn.execute(f'SELECT COUNT(*) FROM "{_TABLE}"').fetchone()[0]
    canonical = conn.execute(
        f'SELECT COUNT(*) FROM "{_TABLE}" WHERE source_id IS NOT NULL').fetchone()[0]
    legacy = total - canonical
    return {"total": total, "canonical": canonical, "legacy_unverified": legacy}


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="Label conversation_documents provenance (canonical vs legacy_unverified).")
    ap.add_argument("--db", default=_DEFAULT_DB)
    ap.add_argument("--dry-run", action="store_true", help="report the split, write nothing")
    ap.add_argument("--revert", action="store_true", help="null out provenance_status (rollback)")
    args = ap.parse_args(argv)

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"::error::DB not found: {db_path}")
        return 2

    pre = _counts_ro(db_path)
    if pre is None:
        return 2
    pct = round(100.0 * pre["canonical"] / pre["total"], 2) if pre["total"] else 0.0
    print(f"{_TABLE}: total={pre['total']:,} canonical(source_id)={pre['canonical']:,} ({pct}%) "
          f"legacy_unverified={pre['legacy_unverified']:,}")

    if args.dry_run:
        print("dry-run: no rows written. Would set "
              f"{pre['canonical']:,} -> 'canonical', {pre['legacy_unverified']:,} -> 'legacy_unverified'.")
        return 0

    try:
        conn = sqlite3.connect(str(db_path), timeout=30)
        conn.execute("PRAGMA busy_timeout=20000")
    except sqlite3.Error as exc:
        print(f"::error::cannot open DB: {exc}")
        return 2
    try:
        # Defensive, idempotent column add.
        if not _has_column(conn, _TABLE, _COL):
            conn.execute(f'ALTER TABLE "{_TABLE}" ADD COLUMN {_COL} TEXT')
            print(f"  added column {_TABLE}.{_COL}")

        if args.revert:
            conn.execute(f'UPDATE "{_TABLE}" SET {_COL} = NULL')
            conn.commit()
            print("reverted: provenance_status set to NULL for all rows.")
            return 0

        # Idempotent labeling: re-running is a no-op once values match.
        c1 = conn.execute(
            f'UPDATE "{_TABLE}" SET {_COL} = \'canonical\' '
            f'WHERE source_id IS NOT NULL AND ({_COL} IS NULL OR {_COL} <> \'canonical\')').rowcount
        c2 = conn.execute(
            f'UPDATE "{_TABLE}" SET {_COL} = \'legacy_unverified\' '
            f'WHERE source_id IS NULL AND ({_COL} IS NULL OR {_COL} <> \'legacy_unverified\')').rowcount
        conn.commit()
        # Report resulting distribution.
        dist = dict(conn.execute(
            f'SELECT COALESCE({_COL},\'(null)\'), COUNT(*) FROM "{_TABLE}" GROUP BY 1').fetchall())
        print(f"labeled: canonical+={c1:,} legacy_unverified+={c2:,} "
              f"(re-run idempotent). distribution={dist}")
    finally:
        conn.close()
    return 0


def _counts_ro(db_path: Path) -> "dict | None":
    try:
        ro = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True, timeout=15)
    except sqlite3.Error as exc:
        print(f"::error::cannot open DB read-only: {exc}")
        return None
    try:
        return _counts(ro)
    finally:
        ro.close()


if __name__ == "__main__":
    raise SystemExit(main())
