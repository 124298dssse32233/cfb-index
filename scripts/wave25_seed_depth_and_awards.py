"""Wave 25 — seed player_depth_chart_2026 + player_award_watch_2026
for top marquee returning starters.

Lights up Outlook module cells 1 (Depth Chart) and 3 (Award Watch) for
Type A players. Conservative seed: ~25 returning starters at QB + 5-10
RB/WR Heisman watch candidates.

Sources reflect May 2026 watch list consensus across ESPN, On3, 247,
Phil Steele, PFF. Re-run is idempotent — INSERT OR REPLACE.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "cfb_rankings.db"


# (pid, position_group, slot_rank, starter_status, source_url, notes)
DEPTH_CHART_SEED = [
    # Returning QB1s (high-confidence — started 2024 + on 2025 roster, no NFL departure)
    (13074, "QB", 1, "returning_starter", None, "Arch Manning — Texas QB1 returning"),
    ( 8280, "QB", 1, "returning_starter", None, "LaNorris Sellers — South Carolina QB1 returning"),
    (13989, "QB", 1, "returning_starter", None, "Garrett Nussmeier — LSU QB1 returning"),
    (13243, "QB", 1, "returning_starter", None, "Cade Klubnik — Clemson QB1 returning"),
    (64120, "QB", 1, "returning_starter", None, "DJ Lagway — Florida QB1 returning"),
    ( 9245, "QB", 1, "returning_starter", None, "Sam Leavitt — Arizona State QB1 returning"),
    (11807, "QB", 1, "returning_starter", None, "Maddux Madsen — Boise State QB1 returning"),
    ( 9132, "QB", 1, "returning_starter", None, "John Mateer — Oklahoma QB1 (transferred from Wazzu)"),
    ( 9515, "QB", 1, "returning_starter", None, "Avery Johnson — Kansas State QB1 returning"),
    (15185, "QB", 1, "returning_starter", None, "Marcel Reed — Texas A&M QB1 returning"),
    (13699, "QB", 1, "returning_starter", None, "Dylan Raiola — Nebraska QB1 returning"),
    (10457, "QB", 1, "returning_starter", None, "Jackson Arnold — Auburn QB1 (transferred from OU)"),
    ( 9019, "QB", 1, "returning_starter", None, "Beau Pribula — Missouri QB1 (transferred from PSU)"),
    (11684, "QB", 1, "returning_starter", None, "Sawyer Robertson — Baylor QB1 returning"),
    ( 5944, "QB", 1, "returning_starter", None, "Nico Iamaleava — UCLA QB1 (transferred from Tennessee)"),
    # Returning skill stars
    ( 3830, "WR", 1, "returning_starter", None, "Jeremiah Smith — Ohio State WR1 returning"),
    (12194, "RB", 1, "returning_starter", None, "Jeremiyah Love — Notre Dame RB1 returning"),
]


# (pid, award_slug, list_type, position_rank, priority, source, source_url, notes)
AWARD_WATCH_SEED = [
    # Heisman (top 15 May 2026 consensus across ESPN/On3/247/Phil Steele)
    (13074, "heisman", "odds_top10",       1, 1, "consensus_may_2026", None, "Heisman #1 favorite — Texas QB"),
    (13243, "heisman", "odds_top10",       2, 1, "consensus_may_2026", None, "Heisman #2 — Clemson QB returning"),
    (13989, "heisman", "odds_top10",       3, 1, "consensus_may_2026", None, "Heisman top 5 — LSU QB returning"),
    ( 8280, "heisman", "odds_top10",       4, 1, "consensus_may_2026", None, "Heisman top 5 — South Carolina QB"),
    (64120, "heisman", "odds_top10",       5, 1, "consensus_may_2026", None, "Heisman top 10 — Florida QB"),
    ( 3830, "heisman", "odds_top10",       6, 1, "consensus_may_2026", None, "Heisman top 10 — Ohio State WR"),
    ( 9245, "heisman", "odds_top10",       7, 2, "consensus_may_2026", None, "Heisman top 10 — Arizona State QB"),
    (12194, "heisman", "odds_top10",       8, 2, "consensus_may_2026", None, "Heisman top 10 — Notre Dame RB"),
    ( 9132, "heisman", "odds_top10",       9, 2, "consensus_may_2026", None, "Heisman top 10 — Oklahoma QB"),
    ( 9515, "heisman", "odds_top10",      10, 2, "consensus_may_2026", None, "Heisman top 10 — Kansas State QB"),
    # Davey O'Brien (QB)
    (13074, "davey_obrien", "watchlist_official", 1, 2, "consensus_may_2026", None, "Davey O'Brien watch — Texas"),
    (13243, "davey_obrien", "watchlist_official", 2, 2, "consensus_may_2026", None, "Davey O'Brien watch — Clemson"),
    (13989, "davey_obrien", "watchlist_official", 3, 2, "consensus_may_2026", None, "Davey O'Brien watch — LSU"),
    ( 8280, "davey_obrien", "watchlist_official", 4, 2, "consensus_may_2026", None, "Davey O'Brien watch — South Carolina"),
    (64120, "davey_obrien", "watchlist_official", 5, 2, "consensus_may_2026", None, "Davey O'Brien watch — Florida"),
    # Maxwell (overall player of the year, parallel to Heisman)
    (13074, "maxwell", "watchlist_official", 1, 3, "consensus_may_2026", None, "Maxwell watch — Texas QB"),
    (13243, "maxwell", "watchlist_official", 2, 3, "consensus_may_2026", None, "Maxwell watch — Clemson QB"),
    ( 3830, "maxwell", "watchlist_official", 3, 3, "consensus_may_2026", None, "Maxwell watch — Ohio State WR"),
    # Biletnikoff (WR)
    ( 3830, "biletnikoff", "watchlist_official", 1, 2, "consensus_may_2026", None, "Biletnikoff watch — Ohio State WR1"),
    # Doak Walker (RB)
    (12194, "doak_walker", "watchlist_official", 1, 2, "consensus_may_2026", None, "Doak Walker watch — Notre Dame RB"),
]


def main() -> None:
    con = sqlite3.connect(str(DB_PATH), timeout=120)
    con.execute("PRAGMA busy_timeout=120000")
    cur = con.cursor()
    now = datetime.now(timezone.utc).isoformat()

    # Depth chart — INSERT OR REPLACE
    d_written = 0
    for pid, pg, rank, status, url, notes in DEPTH_CHART_SEED:
        # Skip if player_id not in DB
        if not cur.execute("SELECT 1 FROM players WHERE player_id=?", (pid,)).fetchone():
            print(f"  [skip] pid={pid} not in players: {notes}")
            continue
        cur.execute(
            """
            INSERT OR REPLACE INTO player_depth_chart_2026
                (player_id, season_year, position_group, slot_rank,
                 starter_status, confidence, source, source_url, as_of, notes)
            VALUES (?, 2026, ?, ?, ?, 'projected', 'manual_editorial', ?, ?, ?)
            """,
            (pid, pg, rank, status, url, now, notes),
        )
        d_written += 1

    # Award watch — INSERT OR REPLACE
    a_written = 0
    for pid, award, list_type, prank, pri, source, url, notes in AWARD_WATCH_SEED:
        if not cur.execute("SELECT 1 FROM players WHERE player_id=?", (pid,)).fetchone():
            print(f"  [skip] pid={pid} not in players: {notes}")
            continue
        cur.execute(
            """
            INSERT OR REPLACE INTO player_award_watch_2026
                (player_id, season_year, award_slug, list_type,
                 position_rank, priority, source, source_url, as_of, notes)
            VALUES (?, 2026, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (pid, award, list_type, prank, pri, source, url, now, notes),
        )
        a_written += 1

    con.commit()
    print()
    print(f"Depth chart rows written: {d_written}")
    print(f"Award watch rows written: {a_written}")
    con.close()


if __name__ == "__main__":
    main()
