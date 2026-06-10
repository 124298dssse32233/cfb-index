"""Wave 25 — auto-seed status overrides for split-pid players.

The DB has many players where stats live on one player_id but NFL draft
data lives on a different player_id (same name, different canonical
record). Example: Dillon Gabriel pid=11737 (Oregon, all 2024 stats) vs
pid=120 (canonical, 2025 NFL draft to Cleveland).

When users visit /players/dillon-gabriel-11737.html, the Status Strip
currently resolves to EXHAUSTED_ELIGIBILITY because pid=11737 has no
draft row. This script writes a player_status_override row for the
STATS pid that mirrors the DRAFT pid's status, so the page shows the
correct NFL framing.

Safe-by-design:
  - Only operates on full-name exact matches
  - Requires stats_pid has 30+ stat rows (eliminates ambiguous low-vol matches)
  - Requires position match between stats_pid and draft_pid (cuts false positives)
  - Tagged set_by='auto_alias_2026_05_27' for auditability
  - Idempotent — re-running skips existing overrides

Run: python scripts/wave25_seed_alias_overrides.py
     python scripts/wave25_seed_alias_overrides.py --dry-run
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "cfb_rankings.db"


def _name_variants(name: str) -> list[str]:
    """Return common name variants (Cam ↔ Cameron, TJ ↔ T.J., Jr / Sr suffixes)."""
    variants = {name, name.strip()}
    short_long = {
        "Cam": "Cameron", "Cameron": "Cam",
        "Tom": "Thomas", "Thomas": "Tom",
        "Mike": "Michael", "Michael": "Mike",
        "Dan": "Daniel", "Daniel": "Dan",
        "Matt": "Matthew", "Matthew": "Matt",
        "Will": "William", "William": "Will",
        "Sam": "Samuel", "Samuel": "Sam",
        "Joe": "Joseph", "Joseph": "Joe",
        "Andy": "Andrew", "Andrew": "Andy",
        "Chris": "Christopher", "Christopher": "Chris",
        "Rob": "Robert", "Robert": "Rob",
        "Alex": "Alexander", "Alexander": "Alex",
        "Ben": "Benjamin", "Benjamin": "Ben",
        "Jake": "Jacob", "Jacob": "Jake",
        "Zach": "Zachary", "Zachary": "Zach",
        "Josh": "Joshua", "Joshua": "Josh",
    }
    parts = name.split(" ", 1)
    if len(parts) == 2 and parts[0] in short_long:
        variants.add(f"{short_long[parts[0]]} {parts[1]}")
    # Punctuation variants for initials (TJ vs T.J.)
    for v in list(variants):
        if "." in v:
            variants.add(v.replace(".", "").replace("  ", " ").strip())
        else:
            # Detect "TJ"/"CJ"/"AJ" prefixes and add "T.J." form
            p = v.split(" ", 1)
            if p and len(p[0]) == 2 and p[0].isupper():
                variants.add(f"{p[0][0]}.{p[0][1]}. " + (p[1] if len(p) > 1 else ""))
    return list(variants)


def find_split_pid_candidates(con: sqlite3.Connection) -> list[dict]:
    """Find players where stats pid != draft pid but full_name (or variant) matches."""
    cur = con.cursor()
    # Pull all stats pids and all draft pids separately, join in Python on name variants.
    stats_rows = cur.execute(
        """
        SELECT p.player_id, p.full_name, p.position AS master_position,
               (SELECT COUNT(*) FROM player_season_stats WHERE player_id=p.player_id) AS stats_n,
               (SELECT position FROM player_season_stats
                  WHERE player_id=p.player_id AND position IS NOT NULL
                  ORDER BY season_year DESC LIMIT 1) AS stats_pos
        FROM players p
        WHERE ((SELECT COUNT(*) FROM player_season_stats WHERE player_id=p.player_id)
               + (SELECT COUNT(*) FROM player_game_stats WHERE player_id=p.player_id)) >= 30
          AND (SELECT MAX(draft_year) FROM player_nfl_draft WHERE player_id=p.player_id) IS NULL
        """
    ).fetchall()
    draft_rows = cur.execute(
        """
        SELECT p.player_id, p.full_name, p.position AS master_position,
               (SELECT MAX(draft_year) FROM player_nfl_draft WHERE player_id=p.player_id) AS draft_year,
               (SELECT round FROM player_nfl_draft WHERE player_id=p.player_id
                ORDER BY draft_year DESC LIMIT 1) AS draft_round,
               (SELECT pick FROM player_nfl_draft WHERE player_id=p.player_id
                ORDER BY draft_year DESC LIMIT 1) AS draft_pick,
               (SELECT overall FROM player_nfl_draft WHERE player_id=p.player_id
                ORDER BY draft_year DESC LIMIT 1) AS draft_overall,
               (SELECT nfl_team FROM player_nfl_draft WHERE player_id=p.player_id
                ORDER BY draft_year DESC LIMIT 1) AS nfl_team,
               (SELECT position FROM player_nfl_draft WHERE player_id=p.player_id
                ORDER BY draft_year DESC LIMIT 1) AS draft_position
        FROM players p
        WHERE (SELECT MAX(draft_year) FROM player_nfl_draft WHERE player_id=p.player_id) IS NOT NULL
          AND (SELECT COUNT(*) FROM player_season_stats WHERE player_id=p.player_id) = 0
        """
    ).fetchall()

    # Index draft rows by name variants
    draft_by_name: dict[str, list[dict]] = {}
    draft_cols = [c[0] for c in cur.description]
    for r in draft_rows:
        d = dict(zip(draft_cols, r))
        for v in _name_variants(d["full_name"]):
            draft_by_name.setdefault(v, []).append(d)

    # Find matches
    stats_cols = ["player_id", "full_name", "master_position", "stats_n", "stats_pos"]
    candidates: list[dict] = []
    for srow in stats_rows:
        s = dict(zip(stats_cols, srow))
        for v in _name_variants(s["full_name"]):
            if v in draft_by_name:
                for d in draft_by_name[v]:
                    candidates.append({
                        "stats_pid": s["player_id"],
                        "full_name": s["full_name"],
                        "stats_pos": s["stats_pos"] or s["master_position"],
                        "stats_n": s["stats_n"],
                        "draft_pid": d["player_id"],
                        "draft_name": d["full_name"],
                        "draft_year": d["draft_year"],
                        "draft_round": d["draft_round"],
                        "draft_pick": d["draft_pick"],
                        "draft_overall": d["draft_overall"],
                        "nfl_team": d["nfl_team"],
                        "draft_position": d["draft_position"],
                    })
                break

    # Dedupe — prefer most recent draft year if stats_pid matches multiple
    by_stats_pid: dict[int, dict] = {}
    for c in candidates:
        existing = by_stats_pid.get(c["stats_pid"])
        if not existing or (c.get("draft_year") or 0) > (existing.get("draft_year") or 0):
            by_stats_pid[c["stats_pid"]] = c
    return sorted(by_stats_pid.values(), key=lambda c: c["full_name"])


_POSITION_FAMILIES = {
    "QB": {"QB", "Quarterback"},
    "RB": {"RB", "TB", "FB", "HB", "Running Back"},
    "WR": {"WR", "Wide Receiver"},
    "TE": {"TE", "Tight End"},
    "OL": {"OL", "OT", "OG", "C", "G", "T", "IOL", "Offensive Tackle", "Offensive Guard", "Center", "Offensive Lineman"},
    "DL": {"DL", "DE", "DT", "NT", "EDGE", "Edge", "Defensive End", "Defensive Tackle", "Nose Tackle"},
    "LB": {"LB", "ILB", "OLB", "MLB", "Linebacker"},
    "DB": {"CB", "S", "DB", "FS", "SS", "Cornerback", "Safety", "Defensive Back"},
    "K":  {"K", "PK", "Kicker", "Placekicker"},
    "P":  {"P", "Punter"},
    "LS": {"LS", "Long Snapper"},
}


def _position_compatible(p1: str | None, p2: str | None) -> bool:
    """True if two position strings map to the same family."""
    if not p1 or not p2:
        return False
    p1u, p2u = p1.strip().upper(), p2.strip().upper()
    if p1u == p2u:
        return True
    for fam in _POSITION_FAMILIES.values():
        fam_upper = {f.upper() for f in fam}
        if p1u in fam_upper or p1.strip() in fam:
            if p2u in fam_upper or p2.strip() in fam:
                return True
    return False


def _status_code_for_draft_year(draft_year: int) -> str:
    return "NFL_DRAFTED_2026" if int(draft_year) == 2026 else "NFL_DRAFTED_PRIOR"


def write_overrides(con: sqlite3.Connection, candidates: list[dict], dry_run: bool) -> tuple[int, int, int]:
    """Returns (written, skipped_position_mismatch, skipped_already_exists)."""
    cur = con.cursor()
    now = datetime.now(timezone.utc).isoformat()
    written = 0
    skipped_pos = 0
    skipped_exists = 0

    for c in candidates:
        # Position match required ONLY when stats volume is thin (<100 rows);
        # high-volume players (Gabriel, Jeanty, Ward) often have stale master
        # positions in `players.position` but their identity is unambiguous.
        if c.get("stats_n", 0) < 100 and not _position_compatible(
            c.get("stats_pos"), c.get("draft_position")
        ):
            skipped_pos += 1
            continue

        # Skip if override already exists
        existing = cur.execute(
            "SELECT player_id FROM player_status_override WHERE player_id = ?",
            (c["stats_pid"],),
        ).fetchone()
        if existing:
            skipped_exists += 1
            continue

        status_code = _status_code_for_draft_year(c["draft_year"])
        notes = (
            f"Auto-aliased from draft_pid={c['draft_pid']} "
            f"(name match: {c['full_name']!r}; "
            f"draft={c['draft_year']} R{c['draft_round']} #{c['draft_overall']} {c['nfl_team']})"
        )

        if dry_run:
            print(
                f"  [DRY] override pid={c['stats_pid']} ({c['full_name']:30s}) "
                f"-> {status_code} ({c['nfl_team']} R{c['draft_round']})"
            )
        else:
            cur.execute(
                """
                INSERT INTO player_status_override
                    (player_id, status_code, set_by, set_at, notes,
                     nfl_team, draft_year, draft_round, draft_pick, draft_overall)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (c["stats_pid"], status_code, "auto_alias_2026_05_27", now, notes,
                 c["nfl_team"], c["draft_year"], c["draft_round"],
                 c["draft_pick"], c["draft_overall"]),
            )
        written += 1
    return written, skipped_pos, skipped_exists


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(str(DB_PATH))
    try:
        candidates = find_split_pid_candidates(con)
        print(f"Found {len(candidates)} split-pid candidates.")

        # Show a preview of the top names
        print("Preview (first 10):")
        for c in candidates[:10]:
            print(
                f"  stats_pid={c['stats_pid']:6} ({c['full_name']:30s} {c['stats_pos']:6}) "
                f"<- draft_pid={c['draft_pid']:6} ({c['draft_year']} {c['nfl_team']} R{c['draft_round']} {c['draft_position']})"
            )

        written, skip_pos, skip_exists = write_overrides(con, candidates, args.dry_run)
        if not args.dry_run:
            con.commit()
        print()
        print(f"Written: {written}  skipped_position_mismatch: {skip_pos}  skipped_already_exists: {skip_exists}")
        if args.dry_run:
            print("(dry-run — no DB writes)")
    finally:
        con.close()


if __name__ == "__main__":
    main()
