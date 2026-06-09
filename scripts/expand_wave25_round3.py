"""One-shot script: Round 3 expansion of award_watch_2026.csv and depth_chart_2026.csv.

Adds:
  Award Watch:
    - Biletnikoff expanded: 6->10 (adds Wesco, Greathouse, Moore, Bell)
    - Doak Walker expanded: 9->10 (adds Justice Haynes)

  Depth Chart:
    - WR: +4 new entries from major P4 programs (Clemson x2, ND, Georgia)

All player_ids verified RETURNING_2026 / TRANSFERRED_COLLEGE in player_current_status_cache.
Run once from repo root: python scripts/expand_wave25_round3.py
"""
from pathlib import Path
import csv

WATCH_CSV = Path("data/award_watch_2026.csv")
DEPTH_CSV = Path("data/depth_chart_2026.csv")

WATCH_ADDITIONS = """\
# Biletnikoff Award (wide receiver of year) — expanded from 6 to 10 candidates
# Sources: PFF WR rankings 2026, On3 WR watch, Phil Steele 2026 WR grades.
13251,Bryant Wesco Jr.,biletnikoff,watchlist_official,7,2,consensus_may_2026,,2026-05-27,Biletnikoff - Clemson WR; Clemson WR1 top returning target in ACC explosive route runner
12193,Jaden Greathouse,biletnikoff,watchlist_official,8,2,consensus_may_2026,,2026-05-27,Biletnikoff - Notre Dame WR; Irish WR1 big-play threat high NFL draft upside
13246,T.J. Moore,biletnikoff,watchlist_official,9,3,consensus_may_2026,,2026-05-27,Biletnikoff - Clemson WR; veteran receiver brings production and YAC ability
13273,Dillon Bell,biletnikoff,watchlist_official,10,3,consensus_may_2026,,2026-05-27,Biletnikoff - Georgia WR; Bulldogs WR1 returns for sixth season proven possession receiver
# Doak Walker Award (running back of year) — expanded from 9 to 10 candidates
4489,Justice Haynes,doak_walker,watchlist_official,10,3,consensus_may_2026,,2026-05-27,Doak Walker - Transfer RB; explosive pass-catching back high production at prior stop
"""

DEPTH_ADDITIONS = """\
# WR depth chart — major P4 program additions (Round 3 expansion)
13251,Bryant Wesco Jr.,WR,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Clemson WR1 — explosive route runner Biletnikoff candidate leads Tigers offense
12193,Jaden Greathouse,WR,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Notre Dame WR1 — Irish top receiver big-play threat with NFL Draft upside
13246,T.J. Moore,WR,1,returning_starter,projected,manual_editorial,,2026-05-27,Clemson WR — veteran presence in Clemson's talented receiving corps
13273,Dillon Bell,WR,1,returning_starter,confirmed,manual_editorial,,2026-05-27,Georgia WR1 — Bulldogs sixth-year senior veteran possession receiver
"""


def _load_existing_keys(path: Path, id_col: str, key_col: str) -> set:
    """Return set of (id, key) tuples already in the CSV."""
    keys = set()
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row.get(id_col, "")
            if pid and not pid.startswith("#"):
                keys.add((pid, row.get(key_col, "")))
    return keys


def append_csv(path: Path, additions: str, id_col: str, key_col: str) -> int:
    existing = _load_existing_keys(path, id_col, key_col)
    lines_to_add = []
    for line in additions.splitlines(keepends=True):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            lines_to_add.append(line)
            continue
        row = next(csv.reader([stripped]))
        pid = row[0] if row else ""
        key = row[1] if len(row) > 1 else ""
        if id_col == "player_id" and key_col == "award_slug":
            key = row[2] if len(row) > 2 else ""  # award_slug is col index 2
        elif id_col == "player_id" and key_col == "position_group":
            key = row[2] if len(row) > 2 else ""  # position_group is col index 2
        if (pid, key) not in existing:
            lines_to_add.append(line)
    if not lines_to_add:
        return 0
    current = path.read_text(encoding="utf-8")
    separator = "" if current.endswith("\n") else "\n"
    path.write_text(current + separator + "".join(lines_to_add), encoding="utf-8")
    return sum(1 for l in lines_to_add if l.strip() and not l.strip().startswith("#"))


watch_added = append_csv(WATCH_CSV, WATCH_ADDITIONS, "player_id", "award_slug")
depth_added = append_csv(DEPTH_CSV, DEPTH_ADDITIONS, "player_id", "position_group")

print(f"Award watch: added {watch_added} new rows to {WATCH_CSV}")
print(f"Depth chart: added {depth_added} new rows to {DEPTH_CSV}")
