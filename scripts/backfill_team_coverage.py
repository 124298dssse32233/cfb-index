"""Backfill / refresh team_coverage from the 6 cohort authoring sources.

Per DECISIONS.md#D-016 + specs/01-foundation-unblock.md. Thin CLI wrapper
over ``cfb_rankings.coverage.sync_team_coverage`` — all gather + sync logic
lives there so the build (reporting.build_static_site) and this script share
one implementation.

``sync_team_coverage`` does an atomic truncate-and-reinsert, so this script
is always a full refresh: rerunning is idempotent AND a slug removed from an
authoring constant is removed from the table. (The old INSERT OR IGNORE only
ever added rows.)

Usage:

    python scripts/backfill_team_coverage.py            # refresh
    python scripts/backfill_team_coverage.py --dry-run  # show counts, no write
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cfb_rankings.config import AppConfig
from cfb_rankings.coverage import gather_rows, sync_team_coverage
from cfb_rankings.db import Database
from cfb_rankings.migrations import apply_runtime_migrations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Show row counts per tier without writing.")
    args = parser.parse_args()

    if args.dry_run:
        rows = gather_rows()
        by_tier: dict[str, int] = {}
        for r in rows:
            by_tier[r["tier"]] = by_tier.get(r["tier"], 0) + 1
        print(f"Gathered {len(rows)} rows across {len(by_tier)} tiers:")
        for tier, n in sorted(by_tier.items()):
            print(f"  {tier:24s} {n:>4d}")
        print("--dry-run set; no writes performed")
        return 0

    config = AppConfig.from_env()
    db = Database(config.database_url)
    apply_runtime_migrations(db)

    if not db.query_one(
        "select name from sqlite_master where type='table' and name='team_coverage'"
    ):
        print("ERROR: team_coverage table missing — migration not applied", file=sys.stderr)
        return 2

    by_tier = sync_team_coverage(db)
    total = sum(by_tier.values())
    print(f"Refreshed team_coverage: {total} rows across {len(by_tier)} tiers:")
    for tier, n in sorted(by_tier.items()):
        print(f"  {tier:24s} {n:>4d}")
    distinct_slugs = db.query_one(
        "select count(distinct team_slug) as n from team_coverage"
    )["n"]
    print(f"covering {distinct_slugs} distinct team_slug values")
    return 0


if __name__ == "__main__":
    sys.exit(main())
