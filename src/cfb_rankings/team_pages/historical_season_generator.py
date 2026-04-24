"""Populate ``team_historical_seasons`` with editorial content for every
profiled (slug, season_year) pair.

Order of precedence (highest first):

1. Hand-authored row from ``AUTHORED_SEASONS`` — the flagship corpus.
2. LLM-generated content (Opus for editorial, Sonnet for moments) —
   scaffold in place; actual call-out stub at the bottom of the module.
3. Deterministic template fallback via ``build_template_season``.

Idempotent: rows are upserted on (team_slug, season_year). The CLI
``generate-historical-seasons`` drives this module.
"""
from __future__ import annotations

import json
from typing import Any

from .profile_loader import load_profile, PROFILED_SLUGS
from .historical_season_authored import AUTHORED_SEASONS
from .historical_season_content import build_template_season


def generate_for_slug(db, slug: str, *, force_template: bool = False) -> dict[str, int]:
    """Write rows for every (slug, year) that has a team_season_arc row.

    Returns a counter dict {'authored': n, 'template': n, 'skipped': n}.
    """
    profile = load_profile(slug)
    if not profile.team_id:
        return {"authored": 0, "template": 0, "skipped": 0}
    arc_rows = db.query_all(
        """
        select season_year, wins, losses, ties, win_pct,
               ap_rank_final, sp_plus_final,
               cfp_flag, title_game_flag, title_won_flag,
               brick_state, quality_score, notes_json
        from team_season_arc
        where team_id = :tid
        order by season_year asc
        """,
        {"tid": profile.team_id},
    )

    counts = {"authored": 0, "template": 0, "skipped": 0}
    for arc in arc_rows:
        year = arc["season_year"]
        # Authored content overrides
        authored_body = None if force_template else AUTHORED_SEASONS.get((slug, year))
        if authored_body:
            row = _authored_to_row(slug, year, arc, authored_body)
        else:
            games = db.query_all(
                """
                select week, season_type, start_time_utc,
                       home_team_id, away_team_id,
                       home_points, away_points,
                       (select school_name from teams where team_id = g.home_team_id) as home_name,
                       (select school_name from teams where team_id = g.away_team_id) as away_name,
                       neutral_site
                from games g
                where season_year = :y
                  and status in ('Final','final','FINAL')
                  and (home_team_id = :tid or away_team_id = :tid)
                order by start_time_utc
                """,
                {"tid": profile.team_id, "y": year},
            )
            row = build_template_season(profile, arc, games)
            counts["template"] += 1
        if authored_body:
            counts["authored"] += 1

        db.execute(
            """
            insert into team_historical_seasons (
              team_slug, season_year, season_title, season_thesis,
              defining_moments_json, pull_quote_json, legacy_paragraph,
              gap_year_flag, model_id, generated_at_utc
            ) values (
              :slug, :year, :title, :thesis,
              :moments, :quote, :legacy,
              :gap, :model, current_timestamp
            )
            on conflict(team_slug, season_year) do update set
              season_title = excluded.season_title,
              season_thesis = excluded.season_thesis,
              defining_moments_json = excluded.defining_moments_json,
              pull_quote_json = excluded.pull_quote_json,
              legacy_paragraph = excluded.legacy_paragraph,
              gap_year_flag = excluded.gap_year_flag,
              model_id = excluded.model_id,
              generated_at_utc = current_timestamp
            """,
            {
                "slug": slug, "year": year,
                "title": row["season_title"],
                "thesis": row["season_thesis"],
                "moments": row["defining_moments_json"],
                "quote": row["pull_quote_json"],
                "legacy": row["legacy_paragraph"],
                "gap": row["gap_year_flag"],
                "model": row["model_id"],
            },
        )
    return counts


def generate_all(db, *, force_template: bool = False) -> dict[str, int]:
    totals = {"authored": 0, "template": 0, "skipped": 0}
    for slug in sorted(PROFILED_SLUGS):
        c = generate_for_slug(db, slug, force_template=force_template)
        for k, v in c.items():
            totals[k] += v
        print(
            f"  {slug}: authored={c['authored']} template={c['template']}"
            + (f" skipped={c['skipped']}" if c['skipped'] else "")
        )
    return totals


def _authored_to_row(
    slug: str, year: int,
    arc: dict[str, Any],
    authored: dict[str, Any],
) -> dict[str, Any]:
    """Normalize a hand-authored dict into the DB row shape."""
    moments = authored.get("defining_moments") or []
    pull = authored.get("pull_quote")
    is_gap = (arc.get("wins") or 0) + (arc.get("losses") or 0) + (arc.get("ties") or 0) == 0
    return {
        "season_title": authored["season_title"],
        "season_thesis": authored["season_thesis"],
        "defining_moments_json": json.dumps(moments, ensure_ascii=False),
        "pull_quote_json": json.dumps(pull, ensure_ascii=False) if pull else None,
        "legacy_paragraph": authored["legacy_paragraph"],
        "gap_year_flag": 1 if is_gap else 0,
        "model_id": "authored-inline",
    }
