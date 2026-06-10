"""Team x source coverage report — find the dead cells in fan-intel collection.

We built a four-pillar source portfolio (Reddit / YouTube / podcasts / boards +
GDELT + betting), but "we have the pipes" is not "every team has signal". A team
with no recent docs from any source falls back to the "Awaiting Signal" mood card.
This read-only report surfaces, for the last N days:

  * per SOURCE   — total docs and how many distinct teams it reaches
  * per TEAM     — total docs and how many sources reach it (worst teams first)
  * the universe of priority_teams that are dark or nearly dark (Awaiting-Signal risk)

It pairs with verify_source_health_floors.py: that watches a source's day-over-day
trend; this watches the team x source surface. Neither writes to the DB.

Usage:
    python scripts/report_source_coverage.py                 # 7-day text report
    python scripts/report_source_coverage.py --days 14 --csv out/coverage.csv
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import sqlite3
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB = str(_REPO_ROOT / "cfb_rankings.db")
_LABEL_CANDIDATES = ("slug", "school", "name", "display_name", "team_name", "location")


def _ro_connect(db_path: str) -> sqlite3.Connection:
    uri = f"file:{Path(db_path).as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10)
    conn.execute("PRAGMA busy_timeout=8000")
    return conn


def _pick_label_column(conn: sqlite3.Connection) -> str:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(teams)").fetchall()}
    for c in _LABEL_CANDIDATES:
        if c in cols:
            return c
    return "team_id"  # last resort


def _family(source_name: str) -> str:
    """Collapse per-team source ids to a family so the summary stays readable.
    google_news_penn-state -> google_news ; locked_on_byu -> locked_on.
    Single-name sources (reddit, youtube, board) pass through unchanged."""
    import re
    fam = re.sub(r"_[a-z0-9][a-z0-9-]*$", "", source_name)
    return fam or source_name


def build_report(db_path: str, days: int, today: _dt.date) -> dict:
    conn = _ro_connect(db_path)
    label = _pick_label_column(conn)
    cutoff = (today - _dt.timedelta(days=days)).isoformat()

    # Team universe we care about = priority_teams, labelled via teams.
    universe = {
        int(r[0]): (r[1] if r[1] is not None else str(r[0]))
        for r in conn.execute(
            f"""
            select pt.team_id, t.{label}
              from priority_teams pt
              left join teams t on t.team_id = pt.team_id
            """
        ).fetchall()
    }

    # Per (team_id, source) doc counts in the window (team-scope targets only).
    cell_rows = conn.execute(
        """
        select cdt.team_id, cd.source_name, count(distinct cd.conversation_document_id)
          from conversation_documents cd
          join conversation_document_targets cdt
            on cdt.conversation_document_id = cd.conversation_document_id
         where substr(cd.collected_at_utc, 1, 10) >= ?
           and cdt.target_type = 'team'
           and cdt.team_id is not null
         group by cdt.team_id, cd.source_name
        """,
        (cutoff,),
    ).fetchall()
    conn.close()

    cells: dict[tuple[int, str], int] = {}
    sources: dict[str, dict] = {}
    team_totals: dict[int, dict] = {tid: {"docs": 0, "sources": set()} for tid in universe}
    for team_id, source_name, n in cell_rows:
        n = int(n)
        cells[(int(team_id), source_name)] = n
        s = sources.setdefault(source_name, {"docs": 0, "teams": set()})
        s["docs"] += n
        if team_id in universe:
            s["teams"].add(int(team_id))
            team_totals[int(team_id)]["docs"] += n
            team_totals[int(team_id)]["sources"].add(source_name)

    return {
        "label": label, "days": days, "cutoff": cutoff,
        "universe": universe, "cells": cells, "sources": sources,
        "team_totals": team_totals,
    }


def print_report(rep: dict, low_threshold: int, worst_n: int, detail: bool = False) -> None:
    universe, sources, team_totals = rep["universe"], rep["sources"], rep["team_totals"]
    print(f"=== Source coverage, last {rep['days']}d (since {rep['cutoff']}) ===")
    print(f"priority teams: {len(universe)}   source feeds: {len(sources)}\n")

    # Roll per-team feeds up into families so this stays scannable.
    fams: dict[str, dict] = {}
    for name, s in sources.items():
        f = fams.setdefault(_family(name), {"docs": 0, "teams": set(), "feeds": 0})
        f["docs"] += s["docs"]
        f["teams"] |= s["teams"]
        f["feeds"] += 1
    print("-- per source family (docs / distinct teams reached / # feeds) --")
    for fam, f in sorted(fams.items(), key=lambda kv: -kv[1]["docs"]):
        print(f"  {fam:<20} {f['docs']:>8} docs   {len(f['teams']):>3}/{len(universe)} teams   "
              f"{f['feeds']:>3} feed(s)")

    if detail:
        print("\n-- per feed (full, docs / teams) --")
        for name, s in sorted(sources.items(), key=lambda kv: -kv[1]["docs"]):
            print(f"  {name:<32} {s['docs']:>7} docs   {len(s['teams']):>3} teams")

    dark = sorted(
        ((tid, lbl) for tid, lbl in universe.items()
         if team_totals[tid]["docs"] < low_threshold),
        key=lambda x: team_totals[x[0]]["docs"],
    )
    print(f"\n-- teams below {low_threshold} docs/{rep['days']}d "
          f"(Awaiting-Signal risk): {len(dark)} of {len(universe)} --")
    for tid, lbl in dark[:worst_n]:
        tt = team_totals[tid]
        srcs = ", ".join(sorted(tt["sources"])) or "(none)"
        print(f"  {str(lbl):<24} {tt['docs']:>4} docs  [{len(tt['sources'])} src: {srcs}]")
    if len(dark) > worst_n:
        print(f"  …and {len(dark) - worst_n} more")


def write_csv(rep: dict, path: str) -> None:
    universe, cells, sources = rep["universe"], rep["cells"], rep["sources"]
    src_names = sorted(sources.keys())
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["team", "team_id", "total_docs"] + src_names)
        for tid, lbl in sorted(universe.items(), key=lambda kv: str(kv[1])):
            row = [lbl, tid, rep["team_totals"][tid]["docs"]]
            row += [cells.get((tid, s), 0) for s in src_names]
            w.writerow(row)
    print(f"\nwrote full matrix -> {path} ({len(universe)} teams x {len(src_names)} sources)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Team x source coverage report (read-only).")
    p.add_argument("db_path", nargs="?", default=_DEFAULT_DB)
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--low-threshold", type=int, default=5,
                   help="teams below this many docs in the window are flagged")
    p.add_argument("--worst", type=int, default=30, help="how many worst teams to list")
    p.add_argument("--detail", action="store_true", help="also print every individual feed")
    p.add_argument("--csv", default=None, help="also write the full matrix to this CSV")
    p.add_argument("--today", default=None, help="override 'today' (YYYY-MM-DD)")
    args = p.parse_args(argv)

    today = _dt.date.fromisoformat(args.today) if args.today else _dt.date.today()
    try:
        rep = build_report(args.db_path, args.days, today)
    except sqlite3.OperationalError as exc:
        print(f"ERROR: could not read coverage tables: {exc}")
        return 2
    print_report(rep, args.low_threshold, args.worst, detail=args.detail)
    if args.csv:
        write_csv(rep, args.csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
