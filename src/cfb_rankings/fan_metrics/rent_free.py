"""Rent Free — pairwise fanbase obsession asymmetry.

"Which rival fanbase talks about you most." Reads directional cross-mention
counts (team_week_rival_mentions, written by build-conversation-features +
the rivalry_pairs bootstrap) aggregated over the latest season, joins the
canonical pair list, and surfaces the ASYMMETRY: who is disproportionately
obsessed with whom.

Metric: raw directional mention counts per pair, summed over the season.
``a_to_b`` = how often team A's fans bring up team B. The story is the gap.
The receipt always carries both raw counts, so a lopsided ratio is never a
black box — and when one side has near-zero collected conversation we mark
the pair "one-sided" rather than printing a misleading precise multiple.

No persistence: the aggregate is a trivial GROUP BY over a few hundred rows,
recomputed at render time. (Backometer persists because of cross-week
hysteresis + history; Rent Free's display is current-standings only.)
"""

from __future__ import annotations

from typing import Any

from cfb_rankings.db import Database

# Publication floor: a pair needs a clear dominant side AND enough total
# signal before we'll print a verdict. Tuned against the live offseason
# corpus so the marquee asymmetries qualify and 1-vs-0 noise does not.
MIN_DOMINANT = 15
MIN_TOTAL = 20
# Below this on the quiet side, the ratio is "directional, not precise" — we
# have little/no collected conversation from that fanbase, so we say so.
ONE_SIDED_BELOW = 3


def latest_rent_free_season(db: Database) -> int | None:
    row = db.query_one("select max(season_year) as y from team_week_rival_mentions")
    if not row or row.get("y") is None:
        return None
    return int(row["y"])


def fetch_rent_free_pairs(
    db: Database,
    *,
    season: int | None = None,
    min_dominant: int = MIN_DOMINANT,
    min_total: int = MIN_TOTAL,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Return floored pairs sorted most-lopsided first.

    Each dict carries the obsessed side (does more talking), the rent-free
    side (gets talked about more), raw counts both ways, a sort-stable
    ``ratio_value``, a display ``ratio_label`` ("4.5x" or "one-sided"), and
    team identity (name/slug/color) for both sides.
    """
    if season is None:
        season = latest_rent_free_season(db)
    if season is None:
        return []

    rows = db.query_all(
        """
        with agg as (
          select team_id, rival_team_id, sum(mention_count) as m
          from team_week_rival_mentions
          where season_year = :season
          group by team_id, rival_team_id
        )
        select
          p.rivalry_name,
          p.team_a_id, p.team_b_id,
          ta.canonical_name as a_name, ta.slug as a_slug,
          tb.canonical_name as b_name, tb.slug as b_slug,
          coalesce(ba_brand.primary_color, '#9D6BFF') as a_color,
          coalesce(bb_brand.primary_color, '#9D6BFF') as b_color,
          coalesce(ab.m, 0) as a_to_b,
          coalesce(ba.m, 0) as b_to_a
        from rivalry_pairs p
        join teams ta on ta.team_id = p.team_a_id
        join teams tb on tb.team_id = p.team_b_id
        left join team_brand ba_brand on ba_brand.team_id = p.team_a_id
        left join team_brand bb_brand on bb_brand.team_id = p.team_b_id
        left join agg ab on ab.team_id = p.team_a_id and ab.rival_team_id = p.team_b_id
        left join agg ba on ba.team_id = p.team_b_id and ba.rival_team_id = p.team_a_id
        where p.is_active = 1
        """,
        {"season": season},
    )

    pairs: list[dict[str, Any]] = []
    for r in rows:
        a_to_b = int(r["a_to_b"])  # A's fans talking about B
        b_to_a = int(r["b_to_a"])
        total = a_to_b + b_to_a
        dominant = max(a_to_b, b_to_a)
        minor = min(a_to_b, b_to_a)
        if dominant < min_dominant or total < min_total:
            continue

        # The obsessed side does more talking; the rent-free side gets talked about.
        if a_to_b >= b_to_a:
            obsessed = {"name": r["a_name"], "slug": r["a_slug"], "color": r["a_color"]}
            rent_free = {"name": r["b_name"], "slug": r["b_slug"], "color": r["b_color"]}
            obsessed_count, rentfree_count = a_to_b, b_to_a
        else:
            obsessed = {"name": r["b_name"], "slug": r["b_slug"], "color": r["b_color"]}
            rent_free = {"name": r["a_name"], "slug": r["a_slug"], "color": r["a_color"]}
            obsessed_count, rentfree_count = b_to_a, a_to_b

        one_sided = minor < ONE_SIDED_BELOW
        ratio_value = dominant / max(1, minor)
        ratio_label = "one-sided" if one_sided else f"{dominant / minor:.1f}×"

        pairs.append(
            {
                "rivalry_name": r["rivalry_name"],
                "season": season,
                "obsessed": obsessed,
                "rent_free": rent_free,
                "obsessed_count": obsessed_count,
                "rentfree_count": rentfree_count,
                "a_name": r["a_name"], "a_slug": r["a_slug"], "a_color": r["a_color"], "a_to_b": a_to_b,
                "b_name": r["b_name"], "b_slug": r["b_slug"], "b_color": r["b_color"], "b_to_a": b_to_a,
                "total": total,
                "ratio_value": round(ratio_value, 2),
                "ratio_label": ratio_label,
                "one_sided": one_sided,
            }
        )

    pairs.sort(key=lambda p: p["ratio_value"], reverse=True)
    if limit is not None:
        pairs = pairs[:limit]
    return pairs


def fetch_rent_free_for_team(
    db: Database,
    team_id: int,
    *,
    season: int | None = None,
    min_mentions: int = 6,
) -> dict[str, Any] | None:
    """Team-page view: who is rent-free in this team, and who this team is
    rent-free in. Returns ``{in_their_head, living_rent_free}`` lists or None.

    - ``in_their_head``: rivals THIS team's fans bring up most (this team is
      obsessed -> those rivals live rent free in this fanbase).
    - ``living_rent_free``: rivals whose fans bring up THIS team most (this
      team lives rent free in those fanbases).
    Looser floor than the hub (this is a focused team readout, not a leaderboard).
    """
    if season is None:
        season = latest_rent_free_season(db)
    if season is None or not team_id:
        return None

    out_rows = db.query_all(
        """
        select m.rival_team_id as other_id, t.canonical_name as other_name,
               t.slug as other_slug, sum(m.mention_count) as m
        from team_week_rival_mentions m
        join teams t on t.team_id = m.rival_team_id
        where m.season_year = :season and m.team_id = :tid
        group by m.rival_team_id
        having sum(m.mention_count) >= :floor
        order by m desc
        """,
        {"season": season, "tid": team_id, "floor": min_mentions},
    )
    in_rows = db.query_all(
        """
        select m.team_id as other_id, t.canonical_name as other_name,
               t.slug as other_slug, sum(m.mention_count) as m
        from team_week_rival_mentions m
        join teams t on t.team_id = m.team_id
        where m.season_year = :season and m.rival_team_id = :tid
        group by m.team_id
        having sum(m.mention_count) >= :floor
        order by m desc
        """,
        {"season": season, "tid": team_id, "floor": min_mentions},
    )
    if not out_rows and not in_rows:
        return None
    return {
        "season": season,
        "in_their_head": [  # rivals this team obsesses over
            {"name": r["other_name"], "slug": r["other_slug"], "count": int(r["m"])}
            for r in out_rows
        ],
        "living_rent_free": [  # fanbases obsessed with this team
            {"name": r["other_name"], "slug": r["other_slug"], "count": int(r["m"])}
            for r in in_rows
        ],
    }


__all__ = [
    "fetch_rent_free_pairs",
    "fetch_rent_free_for_team",
    "latest_rent_free_season",
    "MIN_DOMINANT",
    "MIN_TOTAL",
]
