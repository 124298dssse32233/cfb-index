"""Backfill priority_teams.wiki_team_page for all teams (task #20).

Only 21/140 priority teams had wiki_team_page populated (the original seed);
the 138-team expansion never backfilled it, so the Wikipedia pageviews/edits
adapters silently produced 0 rows for the other 119.

Strategy: candidate title "{canonical_name}_football" → Wikipedia REST
summary API (free, no auth, follows redirects) → store the RESOLVED canonical
title (e.g. Florida_State_football redirects to
Florida_State_Seminoles_football). Disambiguation pages and 404s are reported
for manual mapping, never written.

Run: .venv\\Scripts\\python.exe scripts\\backfill_wiki_team_pages.py [--commit]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "cfb_rankings.db"
SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}?redirect=true"
UA = "cfb-index-wiki-backfill/1.0 (kevinsherrin@gmail.com) python-urllib"


def resolve(candidate: str) -> tuple[str | None, str]:
    url = SUMMARY.format(title=urllib.parse.quote(candidate))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return None, f"http {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)
    if data.get("type") == "disambiguation":
        return None, "disambiguation"
    resolved = (data.get("titles") or {}).get("canonical") or ""
    if "football" not in resolved.lower():
        return None, f"resolved to non-football page: {resolved}"
    return resolved, "ok"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(DB, timeout=120)
    rows = con.execute(
        """
        select pt.team_id, t.canonical_name
          from priority_teams pt
          join teams t on t.team_id = pt.team_id
         where pt.wiki_team_page is null or pt.wiki_team_page = ''
         order by t.canonical_name
        """
    ).fetchall()
    print(f"backfilling {len(rows)} teams (commit={args.commit})")

    ok, misses = [], []
    for team_id, name in rows:
        candidate = f"{name.replace(' ', '_')}_football"
        resolved, status = resolve(candidate)
        if resolved:
            ok.append((resolved, team_id))
            print(f"  OK   {name:25s} -> {resolved}")
        else:
            misses.append((name, candidate, status))
            print(f"  MISS {name:25s} ({candidate}: {status})")
        time.sleep(0.15)  # polite pacing for the free API

    if args.commit and ok:
        con.executemany(
            "update priority_teams set wiki_team_page = ? where team_id = ?", ok
        )
        con.commit()
    print(f"\nresolved {len(ok)}, misses {len(misses)}")
    if misses:
        print("manual mapping needed for:")
        for name, cand, status in misses:
            print(f"  {name} ({status})")


if __name__ == "__main__":
    main()
