"""Batch builder for CFP-era pages (WS-07).

Renders ``/programs/<slug>/era/cfp/index.html`` for every real FBS program
with enough CFP-era history (``build_era_summary`` returns ``None`` below
``MIN_SEASONS``, so sparse/non-FBS programs are silently skipped). Used by
``build-site`` and the ``render-era-page`` CLI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..db import Database
from .data import build_era_summary
from .renderer import render_era_page


def era_page_relpath(slug: str) -> str:
    """Site-root-relative URL for a program's era page (no leading slash)."""
    return f"programs/{slug}/era/cfp/"


def era_page_available(db: Database, team_id: int, *, end_season: int = 2025) -> bool:
    """Cheap eligibility check matching ``build_era_summary``'s MIN_SEASONS guard.

    Lets a caller (e.g. the team-page crosslink) avoid pointing at an era page
    that won't be rendered, without paying the full assembly cost.
    """
    from .data import CFP_ERA_START, MIN_SEASONS
    row = db.query_one(
        """
        select count(distinct season_year) as n
          from power_ratings_weekly
         where team_id = :t and season_year between :ys and :ye
        """,
        {"t": int(team_id), "ys": CFP_ERA_START, "ye": end_season},
    )
    return bool(row) and int(row["n"] or 0) >= MIN_SEASONS


def render_era_page_for(
    db: Database, slug: str, programs_dir: Path | str, *, end_season: int = 2025
) -> bool:
    """Render one program's era page. Returns False if it had no era to tell."""
    summary = build_era_summary(db, slug, end_season=end_season)
    if summary is None:
        return False
    dest = Path(programs_dir) / slug / "era" / "cfp"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "index.html").write_text(render_era_page(summary), encoding="utf-8")
    return True


def render_all_era_pages(
    db: Database,
    programs_dir: Path | str,
    *,
    end_season: int = 2025,
    slugs: Iterable[str] | None = None,
) -> int:
    """Render era pages for all qualifying FBS programs. Returns the count written."""
    if slugs is None:
        from ..team_pages.profile_loader import list_real_fbs_slugs
        slugs = list_real_fbs_slugs(db)
    count = 0
    for slug in slugs:
        if render_era_page_for(db, slug, programs_dir, end_season=end_season):
            count += 1
    return count
