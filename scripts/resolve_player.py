"""Read-only canonical-player resolver + orphan audit (linkrot mitigation).

The `players` table has ~43k orphan duplicate rows (no roster_entries, no
player_source_ids) that collide by name with the real, attributed players.
Naive name->id lookups land on orphans (the bug that returned "Bailey Carraway"
for "CJ Carr"). This module resolves a name (+ optional team) to the CANONICAL
player_id — the row backed by real data (cfbd source id, PBP metrics, season
stats) — so the blurb scale-up can pull each player's proprietary percentiles
cleanly without first running the destructive orphan merge.

READ-ONLY: opens the DB with mode=ro. Safe to run during a build.

    python scripts/resolve_player.py            # audit + self-test on the 10
    python scripts/resolve_player.py "Jeremiah Smith" "Ohio State"
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "cfb_rankings.db"


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def resolve(conn: sqlite3.Connection, name: str, team: str | None = None):
    """Return (player_id, full_name, team_name, score) for the best canonical
    match, or None. Ranks candidates by data-evidence: cfbd source id, PBP
    metric rows, season-stat rows, roster rows — orphans score ~0."""
    cur = conn.cursor()

    def _score(pid, full):
        src = cur.execute(
            "SELECT count(*) FROM player_source_ids WHERE player_id=? AND source_name='cfbd'",
            (pid,),
        ).fetchone()[0]
        pbp = cur.execute(
            "SELECT count(*) FROM player_pbp_metrics_season WHERE player_id=?", (pid,)
        ).fetchone()[0]
        stats = cur.execute(
            "SELECT count(*) FROM player_season_stats WHERE player_id=?", (pid,)
        ).fetchone()[0]
        tm = cur.execute(
            "SELECT t.school_name FROM roster_entries r JOIN teams t ON t.team_id=r.team_id "
            "WHERE r.player_id=? ORDER BY r.season_year DESC LIMIT 1",
            (pid,),
        ).fetchone()
        tm = tm[0] if tm else None
        score = (src * 50) + (pbp * 10) + min(stats, 50) + (5 if tm else 0)
        if team and tm and _norm(team) in _norm(tm):
            score += 100  # strong team confirmation
        has_evidence = (src > 0) or (pbp > 0) or (stats > 0)
        return (pid, full, tm, score, has_evidence)

    def _best(rows):
        best = None
        for pid, full in rows:
            cand = _score(pid, full)
            if best is None or cand[3] > best[3]:
                best = cand
        return best

    # Prefer the best EXACT-name match when it has real data evidence — keeps
    # name-collisions resolving to the right player via the team filter (e.g.
    # Bo Jackson the OSU RB, not the Auburn legend). Only fall to a surname-LIKE
    # search when the exact match is an empty orphan — the punctuation-variant
    # case ("DJ Lagway" the orphan vs the canonical "D.J. Lagway").
    exact_rows = cur.execute(
        "SELECT player_id, full_name FROM players WHERE lower(full_name)=?",
        (_norm(name),),
    ).fetchall()
    best = _best(exact_rows)
    if best is not None and best[4]:
        return best[:4]
    last = _norm(name).split()[-1] if name else ""
    if last:
        like_best = _best(cur.execute(
            "SELECT player_id, full_name FROM players WHERE lower(full_name) LIKE ?",
            (f"%{last}%",),
        ).fetchall())
        if like_best is not None and (best is None or like_best[3] > best[3]):
            best = like_best
    return best[:4] if best else None


def audit(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    tot = cur.execute("SELECT count(*) FROM players").fetchone()[0]
    orphans = cur.execute(
        "SELECT count(*) FROM players p WHERE NOT EXISTS"
        "(SELECT 1 FROM roster_entries r WHERE r.player_id=p.player_id) AND NOT EXISTS"
        "(SELECT 1 FROM player_source_ids s WHERE s.player_id=p.player_id)"
    ).fetchone()[0]
    print(f"players: {tot:,} | orphans (no roster + no source): {orphans:,} ({100*orphans/tot:.1f}%)")


_TEST = [
    ("CJ Carr", "Notre Dame", 32522), ("Arch Manning", "Texas", 13074),
    ("Jeremiah Smith", "Ohio State", 3830), ("Julian Sayin", "Ohio State", 15151),
    ("Dante Moore", "Oregon", 16494), ("Dylan Raiola", "Nebraska", 13699),
    ("Sam Leavitt", "Arizona State", 9245), ("Colin Simmons", "Texas", 13102),
    ("Bo Jackson", "Ohio State", 52911), ("Trinidad Chambliss", "Ole Miss", 51590),
]


def main() -> None:
    conn = _conn()
    if len(sys.argv) >= 2:
        r = resolve(conn, sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
        print(r)
        return
    audit(conn)
    print("--- self-test vs the 10 known canonical ids ---")
    ok = 0
    for name, team, expect in _TEST:
        r = resolve(conn, name, team)
        got = r[0] if r else None
        hit = got == expect
        ok += hit
        print(f"  {name:20s} -> {got} (expect {expect}) {'OK' if hit else 'MISMATCH'}  {r[2] if r else ''}")
    print(f"resolver accuracy: {ok}/10")


if __name__ == "__main__":
    main()
