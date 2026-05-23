"""CFBD coaches ingest — populates team_seasons.head_coach from CFBD's
/coaches endpoint. Idempotent UPDATE-only (no INSERT — relies on team_seasons
rows already existing for the team/year pair).

CFBD /coaches returns:
  [
    {
      "first_name": "Nick",
      "last_name": "Saban",
      "hire_date": "...",
      "seasons": [
        {"school": "Alabama", "year": 2024, ...},
        ...
      ]
    },
    ...
  ]

We iterate seasons[] and UPDATE team_seasons.head_coach matched on
(team_slug → team_id, year → season_year).

CLI: `python manage.py ingest-cfbd-coaches --start-year 2014 --end-year 2025`
"""
from __future__ import annotations

import logging
from typing import Any

from cfb_rankings.clients.cfbd import CfbdClient
from cfb_rankings.db import Database


log = logging.getLogger(__name__)


def _resolve_team_id(db: Database, school_name: str) -> int | None:
    """Map a CFBD school name to our team_id via canonical_name + alt_name."""
    if not school_name:
        return None
    rows = db.query_all(
        """
        select team_id from teams
         where canonical_name = :name
            or slug = :slug
         limit 1
        """,
        {"name": school_name, "slug": school_name.lower().replace(" ", "-")},
    )
    if rows:
        return int(rows[0]["team_id"])
    return None


def ingest_coaches_year(db: Database, client: CfbdClient, year: int) -> dict[str, int]:
    """Pull coaches for a single year + UPDATE team_seasons.head_coach."""
    try:
        coaches = client.get_coaches(year=year)
    except Exception as exc:
        log.warning(f"CFBD /coaches failed for year={year}: {exc}")
        return {"fetched": 0, "updated": 0, "skipped": 0}

    updated = 0
    skipped = 0
    fetched = 0

    for coach in coaches:
        # CFBD response uses camelCase (firstName/lastName), but accept both.
        first = (coach.get("first_name") or coach.get("firstName") or "").strip()
        last = (coach.get("last_name") or coach.get("lastName") or "").strip()
        full_name = f"{first} {last}".strip()
        if not full_name:
            continue
        for season in coach.get("seasons", []) or []:
            fetched += 1
            sy = season.get("year")
            school = season.get("school")
            if sy != year or not school:
                continue
            team_id = _resolve_team_id(db, school)
            if not team_id:
                skipped += 1
                continue
            # UPDATE only — relies on team_seasons row existing.
            result = db.execute(
                """
                update team_seasons
                   set head_coach = :name
                 where team_id = :tid and season_year = :sy
                """,
                {"name": full_name, "tid": team_id, "sy": year},
            )
            updated += 1

    print(
        f"[CFBD coaches] {year}: fetched={fetched} updated={updated} skipped={skipped}",
        flush=True,
    )
    return {"fetched": fetched, "updated": updated, "skipped": skipped}


def ingest_coaches_range(
    db: Database, client: CfbdClient, start_year: int, end_year: int
) -> dict[str, int]:
    totals = {"fetched": 0, "updated": 0, "skipped": 0}
    for year in range(start_year, end_year + 1):
        s = ingest_coaches_year(db, client, year)
        for k in totals:
            totals[k] += s[k]
    return totals
