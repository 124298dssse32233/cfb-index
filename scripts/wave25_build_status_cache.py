"""Wave 25 — Materialize player_current_status_view into a cache table.

The view does 4 deeply-nested CTEs with per-player subqueries. With WHERE
player_id=X, SQLite re-materializes the CTEs every call. Build was doing
4 view queries × 7000 players = catastrophic.

This script materializes ONCE then indexes on player_id, dropping the
per-player query from minutes to microseconds.

Run automatically by manage.py build-site (added to publish pipeline).
"""
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "cfb_rankings.db"


def build_cache(db_path: str = str(DB_PATH)) -> int:
    """Rebuild player_current_status_cache from the view. Returns row count."""
    con = sqlite3.connect(db_path, timeout=120)
    con.execute("PRAGMA busy_timeout=120000")
    cur = con.cursor()

    t0 = time.perf_counter()
    cur.executescript(
        """
        DROP TABLE IF EXISTS player_current_status_cache;
        CREATE TABLE player_current_status_cache AS
            SELECT * FROM player_current_status_view;
        CREATE UNIQUE INDEX idx_player_current_status_cache_pid
            ON player_current_status_cache(player_id);
        """
    )
    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM player_current_status_cache").fetchone()[0]
    t1 = time.perf_counter()
    print(f"player_current_status_cache: {n:,} rows in {t1-t0:.1f}s")
    con.close()
    return n


if __name__ == "__main__":
    sys.exit(0 if build_cache() else 1)
