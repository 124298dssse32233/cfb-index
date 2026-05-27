"""Season-by-season Context strip — Brief §4.4 / Wave 23.

For each season this player played, show a small context card with:
  • Team record (W-L)
  • Head coach + OC
  • Scheme tag (pass-heavy / balanced / run-heavy + tempo)

Renders as a horizontal strip above the season-by-season tables so a
reader can quickly see "what kind of season was this in" before
reading the box stats. Mirrors the "Team 13-1 · OC: Will Stein ·
Pass-balanced" pattern from the Brief.

Public API:
    render_season_context(db, player_id) -> str
    SEASON_CONTEXT_CSS                   -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .supporting_cast import _team_year_aggregates, _scheme_tag


SEASON_CONTEXT_CSS = """
/* Season Context strip */
.season-context {
  margin: var(--space-3, 0.75rem) 0 var(--space-4, 1rem) 0;
  padding: clamp(10px, 1.4vw, 14px) clamp(12px, 1.6vw, 18px);
  background: rgba(255, 255, 255, 0.015);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 10px;
  font-variant-numeric: tabular-nums;
}
.season-context__head {
  font-size: 0.66rem;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  margin: 0 0 6px 0;
}
.season-context__rows {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}
.season-context__row {
  background: rgba(255,255,255,0.025);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 0.82rem;
}
.season-context__year {
  display: inline-block;
  font-weight: 700;
  color: var(--accolade-gold-base, #d1a23a);
  margin-right: 6px;
}
.season-context__team {
  color: var(--text-bright, rgba(255,255,255,0.92));
  font-weight: 600;
}
.season-context__record {
  display: inline-block;
  padding: 1px 6px;
  margin-left: 6px;
  font-size: 0.70rem;
  background: rgba(255,255,255,0.06);
  border-radius: 4px;
  color: var(--text-soft, rgba(255,255,255,0.78));
}
.season-context__detail {
  display: block;
  margin-top: 3px;
  font-size: 0.74rem;
  color: var(--text-quiet, rgba(255,255,255,0.62));
  line-height: 1.4;
}
"""


def _team_record(db, team_id: int, season_year: int) -> tuple[int, int]:
    """Compute (wins, losses) for a team-season from games table."""
    rows = db.query_all(
        """
        select home_team_id, away_team_id, home_points, away_points
          from games
         where season_year = :s
           and (home_team_id = :tid or away_team_id = :tid)
           and home_points is not null
           and away_points is not null
        """,
        {"tid": team_id, "s": season_year},
    )
    w = 0; l = 0
    for r in rows:
        hp = r.get("home_points"); ap = r.get("away_points")
        if hp is None or ap is None: continue
        is_home = int(r["home_team_id"]) == int(team_id)
        mine = hp if is_home else ap
        theirs = ap if is_home else hp
        if mine > theirs: w += 1
        elif mine < theirs: l += 1
    return (w, l)


def _staff_for(db, team_id: int, season_year: int) -> dict[str, str]:
    rows = db.query_all(
        """
        select head_coach, offensive_coordinator
          from team_seasons
         where team_id = :tid and season_year = :s limit 1
        """,
        {"tid": team_id, "s": season_year},
    )
    if not rows:
        return {}
    return {
        "hc": (rows[0].get("head_coach") or "").strip(),
        "oc": (rows[0].get("offensive_coordinator") or "").strip(),
    }


def render_season_context(db, player_id: int | None) -> str:
    if db is None or player_id is None:
        return ""

    # Find seasons + teams the player played for
    rows = db.query_all(
        """
        with player_latest as (
            select season_year, team_id, max(week) as mw
              from player_season_stats
             where player_id = :pid and team_id is not null
             group by season_year, team_id
        )
        select pss.season_year, pss.team_id, pss.team_name
          from player_season_stats pss
          join player_latest pl
            on pl.season_year = pss.season_year
           and pl.team_id     = pss.team_id
           and pl.mw          = pss.week
         where pss.player_id = :pid
         order by pss.season_year asc
        """,
        {"pid": int(player_id)},
    )
    if not rows:
        return ""

    # Dedup by (year, team)
    seen: set[tuple[int, int]] = set()
    cards: list[str] = []
    for r in rows:
        year = int(r["season_year"])
        tid = int(r["team_id"]) if r.get("team_id") else 0
        team = (r.get("team_name") or "").strip() or "—"
        key = (year, tid)
        if key in seen:
            continue
        seen.add(key)

        w, l = _team_record(db, tid, year) if tid else (0, 0)
        staff = _staff_for(db, tid, year) if tid else {}
        agg = _team_year_aggregates(db, tid, year) if tid else {}
        scheme = _scheme_tag(agg.get("pass_share"), agg.get("plays_per_game"))

        rec_html = (
            f'<span class="season-context__record">{w}-{l}</span>'
            if (w + l) > 0 else ""
        )
        detail_bits: list[str] = []
        if staff.get("hc"):
            detail_bits.append(f"HC: {staff['hc']}")
        if staff.get("oc") and staff["oc"] != staff.get("hc"):
            detail_bits.append(f"OC: {staff['oc']}")
        if scheme:
            detail_bits.append(scheme)
        detail = " · ".join(detail_bits)

        cards.append(
            '<div class="season-context__row">'
            f'<span class="season-context__year">{year}</span>'
            f'<span class="season-context__team">{escape(team)}</span>'
            f'{rec_html}'
            + (f'<span class="season-context__detail">{escape(detail)}</span>'
               if detail else "")
            + '</div>'
        )

    if not cards:
        return ""
    return (
        '<section class="season-context" data-module="season-context" data-state="ready">'
        '<p class="season-context__head">Season context · Team result + system</p>'
        f'<div class="season-context__rows">{"".join(cards)}</div>'
        '</section>'
    )
