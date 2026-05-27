"""Supporting Cast & Scheme Context — Brief §4.10.

Mid-page module that explains the system around the player:
  - Head coach, OC, DC (from team_seasons)
  - Pass-run split (from aggregated player_game_stats) — scheme tag
  - OL pressure rate (from cfbd_pbp_plays once PBP ingest lands)
  - Pace estimate (plays per game)

Public API:
    render_supporting_cast(db, player_id, season_year, team_id) -> str
    SUPPORTING_CAST_CSS                                         -> str
"""
from __future__ import annotations

from html import escape
from typing import Any


SUPPORTING_CAST_CSS = """
/* Supporting Cast module */
.supporting-cast {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.supporting-cast__head {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 12px; margin-bottom: 10px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
}
.supporting-cast__eyebrow {
  font-size: 0.72rem; letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55)); margin: 0;
}
.supporting-cast__title {
  font-size: 1.05rem; font-weight: 600; margin: 0;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.supporting-cast__staff-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px; margin-bottom: 14px;
}
.supporting-cast__staff-card {
  background: rgba(255,255,255,0.020);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 10px 12px;
}
.supporting-cast__staff-role {
  font-size: 0.66rem; letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55)); margin: 0 0 4px 0;
}
.supporting-cast__staff-name {
  font-size: 0.92rem; font-weight: 600;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.supporting-cast__scheme {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}
.supporting-cast__scheme-tile {
  background: rgba(255,255,255,0.018);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 9px 12px;
}
.supporting-cast__scheme-label {
  font-size: 0.66rem; letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55));
}
.supporting-cast__scheme-value {
  font-size: 1.05rem; font-weight: 600;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.supporting-cast__scheme-note {
  font-size: 0.72rem; color: var(--text-quiet, rgba(255,255,255,0.55));
}
.supporting-cast__tagline {
  margin-top: 12px;
  padding: 10px 14px;
  background: rgba(255,255,255,0.018);
  border-radius: 8px;
  font-size: 0.86rem;
  color: var(--text-soft, rgba(255,255,255,0.82));
  font-style: italic;
}
.supporting-cast--empty {
  color: var(--text-quiet, rgba(255,255,255,0.55));
  font-style: italic;
  padding: 14px;
}
"""


def _scheme_tag(pass_share: float | None, plays_per_game: float | None) -> str:
    if pass_share is None:
        return ""
    bits: list[str] = []
    if pass_share >= 0.62:
        bits.append("pass-heavy")
    elif pass_share >= 0.55:
        bits.append("pass-leaning")
    elif pass_share <= 0.40:
        bits.append("run-heavy")
    elif pass_share <= 0.47:
        bits.append("run-leaning")
    else:
        bits.append("balanced")
    if plays_per_game is not None:
        if plays_per_game >= 75:
            bits.append("fast tempo")
        elif plays_per_game <= 62:
            bits.append("slow tempo")
    return ", ".join(bits).capitalize()


def _team_year_aggregates(
    db, team_id: int, season_year: int,
) -> dict[str, Any]:
    """Return aggregated team passing/rushing volume from player_season_stats.

    Uses each player's max-week cumulative snapshot to avoid double-counting
    weekly partial sums. player_game_stats does NOT carry a numeric ATT
    column for passing (it uses the text C/ATT format), so season_stats
    is the correct source for team-level volume here.
    """
    rows = db.query_all(
        """
        with player_latest as (
            select player_id, max(week) as max_week
              from player_season_stats
             where team_id = :tid and season_year = :s
             group by player_id
        )
        select
          sum(case when pss.category='passing' and pss.stat_type='ATT'
                   then pss.stat_value_num else 0 end) as pass_att,
          sum(case when pss.category='rushing' and pss.stat_type='CAR'
                   then pss.stat_value_num else 0 end) as rush_att,
          sum(case when pss.category='passing' and pss.stat_type='YDS'
                   then pss.stat_value_num else 0 end) as pass_yds,
          sum(case when pss.category='rushing' and pss.stat_type='YDS'
                   then pss.stat_value_num else 0 end) as rush_yds
          from player_season_stats pss
          join player_latest pl on pl.player_id = pss.player_id
                               and pl.max_week  = pss.week
         where pss.team_id = :tid and pss.season_year = :s
        """,
        {"tid": team_id, "s": season_year},
    )
    games_row = db.query_all(
        """
        select count(distinct game_id) as g
          from player_game_stats
         where team_id = :tid and season_year = :s
        """,
        {"tid": team_id, "s": season_year},
    )
    games = int((games_row[0] or {}).get("g") or 0) if games_row else 0
    if not rows:
        return {"games_played": games}
    r = rows[0]
    pa = float(r.get("pass_att") or 0)
    ra = float(r.get("rush_att") or 0)
    total = pa + ra
    return {
        "pass_attempts": pa,
        "rush_attempts": ra,
        "pass_share": (pa / total) if total > 0 else None,
        "plays_per_game": (total / games) if games > 0 else None,
        "pass_yards": float(r.get("pass_yds") or 0),
        "rush_yards": float(r.get("rush_yds") or 0),
        "games_played": games,
    }


def _team_year_staff(db, team_id: int, season_year: int) -> dict[str, str]:
    rows = db.query_all(
        """
        select head_coach, offensive_coordinator, defensive_coordinator
          from team_seasons
         where team_id = :tid and season_year = :s
         limit 1
        """,
        {"tid": team_id, "s": season_year},
    )
    if not rows:
        return {}
    r = rows[0]
    return {
        "head_coach": (r.get("head_coach") or "").strip() or "",
        "oc": (r.get("offensive_coordinator") or "").strip() or "",
        "dc": (r.get("defensive_coordinator") or "").strip() or "",
    }


def _pressure_rate(
    db, team_id: int, season_year: int,
) -> tuple[float | None, int]:
    """OL pressure-allowed rate from PBP sack data. Returns (rate, dropback_count)."""
    rows = db.query_all(
        """
        select
          count(*) as dropbacks,
          sum(case when a.is_sack = 1 then 1 else 0 end) as sacks
        from cfbd_pbp_play_actors a
        join cfbd_pbp_plays p on p.play_id = a.play_id
        join teams t on t.canonical_name = p.offense
        where p.season_year = :s
          and t.team_id = :tid
          and a.role = 'passer'
        """,
        {"tid": team_id, "s": season_year},
    )
    if not rows:
        return (None, 0)
    r = rows[0]
    db_ct = int(r.get("dropbacks") or 0)
    sacks = int(r.get("sacks") or 0)
    if db_ct < 20:
        return (None, db_ct)
    return (sacks / db_ct, db_ct)


def render_supporting_cast(
    db, player_id: int | None, season_year: int | None,
    team_id: int | None = None,
) -> str:
    if db is None or player_id is None or season_year is None or team_id is None:
        return ""

    staff = _team_year_staff(db, int(team_id), int(season_year))
    agg = _team_year_aggregates(db, int(team_id), int(season_year))
    pressure_rate, db_ct = _pressure_rate(db, int(team_id), int(season_year))

    if not staff and not agg:
        return (
            '<section class="supporting-cast supporting-cast--empty" '
            'data-module="supporting-cast-v2" data-state="empty">'
            'Supporting Cast returns once team-season staff + game volume land.'
            '</section>'
        )

    # Staff cards
    staff_cards: list[str] = []
    if staff.get("head_coach"):
        staff_cards.append(
            f'<div class="supporting-cast__staff-card">'
            f'<p class="supporting-cast__staff-role">Head Coach</p>'
            f'<p class="supporting-cast__staff-name">{escape(staff["head_coach"])}</p>'
            f'</div>'
        )
    if staff.get("oc"):
        staff_cards.append(
            f'<div class="supporting-cast__staff-card">'
            f'<p class="supporting-cast__staff-role">Offensive Coord.</p>'
            f'<p class="supporting-cast__staff-name">{escape(staff["oc"])}</p>'
            f'</div>'
        )
    if staff.get("dc"):
        staff_cards.append(
            f'<div class="supporting-cast__staff-card">'
            f'<p class="supporting-cast__staff-role">Defensive Coord.</p>'
            f'<p class="supporting-cast__staff-name">{escape(staff["dc"])}</p>'
            f'</div>'
        )

    # Scheme tiles
    scheme_tiles: list[str] = []
    if agg.get("pass_share") is not None:
        scheme_tiles.append(
            f'<div class="supporting-cast__scheme-tile">'
            f'<p class="supporting-cast__scheme-label">Pass share</p>'
            f'<p class="supporting-cast__scheme-value">{agg["pass_share"]*100:.1f}%</p>'
            f'<p class="supporting-cast__scheme-note">'
            f'{int(agg["pass_attempts"])} pass / {int(agg["rush_attempts"])} run</p>'
            f'</div>'
        )
    if agg.get("plays_per_game") is not None:
        scheme_tiles.append(
            f'<div class="supporting-cast__scheme-tile">'
            f'<p class="supporting-cast__scheme-label">Plays / game</p>'
            f'<p class="supporting-cast__scheme-value">{agg["plays_per_game"]:.1f}</p>'
            f'<p class="supporting-cast__scheme-note">'
            f'{int(agg.get("games_played") or 0)} games</p>'
            f'</div>'
        )
    if pressure_rate is not None:
        scheme_tiles.append(
            f'<div class="supporting-cast__scheme-tile">'
            f'<p class="supporting-cast__scheme-label">OL sack rate (allowed)</p>'
            f'<p class="supporting-cast__scheme-value">{pressure_rate*100:.1f}%</p>'
            f'<p class="supporting-cast__scheme-note">{db_ct} dropbacks &middot; PBP</p>'
            f'</div>'
        )

    scheme_tag = _scheme_tag(agg.get("pass_share"), agg.get("plays_per_game"))
    tagline = (
        f'<p class="supporting-cast__tagline">Scheme: {escape(scheme_tag)}.</p>'
        if scheme_tag else ""
    )

    return (
        '<section class="supporting-cast" '
        f'data-module="supporting-cast-v2" data-state="ready">'
        '<header class="supporting-cast__head">'
        '<div>'
        '<p class="supporting-cast__eyebrow">Supporting Cast &middot; Scheme</p>'
        '<p class="supporting-cast__title">Staff and system around the player</p>'
        '</div>'
        '<span class="supporting-cast__meta">'
        f'{season_year} season</span>'
        '</header>'
        f'<div class="supporting-cast__staff-grid">{"".join(staff_cards)}</div>'
        f'<div class="supporting-cast__scheme">{"".join(scheme_tiles)}</div>'
        f'{tagline}'
        '</section>'
    )
