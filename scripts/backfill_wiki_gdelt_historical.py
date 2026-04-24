"""One-shot historical Wikipedia + GDELT backfill 2022-01-01 to today.

WikipediaPageviewsAdapter + GdeltVolumeAdapter default to 7-day lookback.
This script constructs them with a huge lookback_days (~1575 = 4.3 years)
and runs them once. Wikipedia REST API supports arbitrary date ranges
and returns daily points for every page in priority_teams.wiki_*.
GDELT API returns daily article counts per entity-query within timespan.

Runs in foreground. Prints progress. ~5-10 min wall clock.
"""
from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from cfb_rankings.config import AppConfig
from cfb_rankings.db import Database
from cfb_rankings.migrations import apply_runtime_migrations
from cfb_rankings.ingest.sources.wikipedia import WikipediaPageviewsAdapter, WikipediaEditsAdapter
from cfb_rankings.ingest.sources.gdelt_volume import GdeltVolumeAdapter


def load_env() -> None:
    env_path = REPO / ".env"
    if not env_path.exists():
        return
    import os
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k.strip(), v)


def main() -> None:
    load_env()
    config = AppConfig.from_env()
    db = Database(config.database_url)
    apply_runtime_migrations(db)

    today = _dt.date.today()
    start = _dt.date(2022, 1, 1)
    days = (today - start).days
    print(f"backfilling Wikipedia + GDELT from {start} to {today}  ({days} days)")

    # Wikipedia pageviews — ask for the full 4-year window per priority page
    print("\n[1/3] WikipediaPageviewsAdapter (lookback_days={})".format(days))
    a = WikipediaPageviewsAdapter(db, lookback_days=days)
    res = a.run()
    print(f"  -> status={res.status} rows_inserted={res.rows_inserted}")

    # Wikipedia edits — edits API is paginated and slow; cap at 2 years
    print("\n[2/3] WikipediaEditsAdapter (lookback_days=730)")
    e = WikipediaEditsAdapter(db, lookback_days=730)
    res = e.run()
    print(f"  -> status={res.status} rows_inserted={res.rows_inserted}")

    # GDELT — their API supports timespan up to ~5 years; try full window
    # but fall back gracefully if they rate-limit
    print("\n[3/3] GdeltVolumeAdapter (historical)")
    import cfb_rankings.ingest.sources.gdelt_volume as gv
    gv._DOC_URL = (
        "https://api.gdeltproject.org/api/v2/doc/doc?"
        "query={query}&mode=TimelineVol"
        f"&STARTDATETIME={start.strftime('%Y%m%d')}000000"
        f"&ENDDATETIME={today.strftime('%Y%m%d')}235959"
        "&FORMAT=JSON"
    )
    g = GdeltVolumeAdapter(db)
    res = g.run()
    print(f"  -> status={res.status} rows_inserted={res.rows_inserted}")

    print("\nDone. New source_observations rows:")
    for r in db.query_all("select source_id, count(*) as n from source_observations group by source_id order by n desc"):
        print(f"  {r['source_id']:20s} {r['n']}")


if __name__ == "__main__":
    main()
