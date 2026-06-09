"""Moment of the Year — Brief §11.7 adaptation.

The full brief's "Moment Signal" requires FI swing detection on the
week-over-week conversation pipeline. That data isn't available to
the team-page renderer today.

This is the games-table approximation: surface the single most-
impactful game from the team's recent season, with scoring based on:
  + Postseason (CFP / NY6 bowl)               +6
  + Win                                        +2 (else loss is base)
  + Margin > 14                                +2
  + Top-25 opponent (ranking lookup)           +5
  + Top-10 opponent                            +8

The result is a single-card "the moment" — the screenshot fans
re-share in March about why the season mattered.

Public API:
    render_moment_of_year(db, profile, snapshot) -> str
    MOMENT_OF_YEAR_CSS                            -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot


MOMENT_OF_YEAR_CSS = """
/* Moment of the Year — Brief §11.7 adaptation */
.moment-of-year {
  display: grid;
  gap: clamp(10px, 1.2vw, 14px);
  padding: clamp(16px, 2.0vw, 22px) clamp(18px, 2.2vw, 26px);
  background: linear-gradient(180deg,
    color-mix(in oklab, var(--accent-primary, #c9a24a) 6%, transparent),
    rgba(255,255,255,0.02));
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 4px solid var(--accent-primary, #c9a24a);
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
}
.moment-of-year__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.moment-of-year__headline {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(24px, 1.8vw + 12px, 34px);
  font-weight: 400;
  line-height: 1.05;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--fg-primary);
  margin: 0;
}
.moment-of-year__headline--win  { color: #2c8f5a; }
.moment-of-year__headline--loss { color: #c95151; }
.moment-of-year__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: clamp(14px, 0.4vw + 13px, 17px);
  line-height: 1.45;
  color: var(--fg-secondary);
  margin: 0;
  max-width: 64ch;
}
.moment-of-year__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.moment-of-year__chip {
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 999px;
  color: var(--accent-primary, #c9a24a);
}
"""


# ---------------------------------------------------------------------------
# Data fetch + scoring
# ---------------------------------------------------------------------------

def _fetch_season_games(db, team_id: int, season_year: int) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select g.season_year, g.week, g.season_type,
               g.home_team_id, g.away_team_id,
               g.home_points, g.away_points,
               ht.canonical_name as home_name, at.canonical_name as away_name
        from games g
        join teams ht on ht.team_id = g.home_team_id
        join teams at on at.team_id = g.away_team_id
        where (g.home_team_id = :tid or g.away_team_id = :tid)
          and g.season_year = :season
          and g.status = 'Final'
          and g.home_points is not null and g.away_points is not null
        order by g.week
        """,
        {"tid": team_id, "season": season_year},
    )


def _opp_rank_for_game(db, opp_team_id: int, season_year: int, week: int | None) -> int | None:
    """Look up the AP rank of the opponent at the time of the game.

    Best-effort: pulls the most recent rank entry for the opponent in
    that season at week ≤ game week. Returns None if no ranking row.
    """
    if week is None:
        return None
    row = db.query_one(
        """
        select rank_value
        from official_rankings
        where team_id = :tid
          and season_year = :s
          and ranking_system = 'AP Top 25'
          and week <= :wk
        order by week desc
        limit 1
        """,
        {"tid": opp_team_id, "s": season_year, "wk": week},
    )
    return int(row["rank_value"]) if row and row["rank_value"] else None


def _score_moment(team_id: int, game: dict[str, Any], opp_rank: int | None) -> tuple[int, dict[str, Any]]:
    """Score a game's moment-impact and build the headline/story."""
    is_home = int(game["home_team_id"]) == team_id
    team_pts = int(game["home_points"] if is_home else game["away_points"])
    opp_pts = int(game["away_points"] if is_home else game["home_points"])
    opp_name = game["away_name"] if is_home else game["home_name"]
    margin = team_pts - opp_pts
    is_win = margin > 0
    is_post = (game.get("season_type") or "").lower() in ("postseason", "post")
    abs_margin = abs(margin)

    score = 0
    chips: list[str] = []
    if is_win:
        score += 2
    if abs_margin >= 14:
        score += 2
        chips.append("Decisive Margin")
    if is_post:
        score += 6
        chips.append("Postseason")
    if opp_rank is not None:
        if opp_rank <= 5:
            score += 8
            chips.append(f"vs Top-5 (#{opp_rank})")
        elif opp_rank <= 10:
            score += 6
            chips.append(f"vs Top-10 (#{opp_rank})")
        elif opp_rank <= 25:
            score += 4
            chips.append(f"vs AP #{opp_rank}")
    loc = "vs" if is_home else "at"
    outcome = "Won" if is_win else ("Tied" if margin == 0 else "Lost")
    headline = f"{outcome} {team_pts}-{opp_pts} {loc} {opp_name}"
    if is_post:
        headline = "Postseason · " + headline

    parts: list[str] = []
    parts.append(
        f"Week {int(game.get('week') or 0)} of {int(game['season_year'])}."
    )
    if opp_rank is not None and is_win and opp_rank <= 15:
        parts.append(f"Beat a top-{opp_rank} opponent on the {('road' if not is_home else 'field')}.")
    elif is_post and is_win:
        parts.append(f"Postseason win — the season-defining moment.")
    elif is_win and abs_margin >= 21:
        parts.append("A statement margin. Recruiting boards re-rendered overnight.")
    elif not is_win and abs_margin >= 28:
        parts.append("A reckoning loss — the data point the next season must answer.")
    else:
        parts.append("The single game that defined the season's arc.")

    return score, {
        "headline": headline,
        "story": " ".join(parts),
        "chips": chips,
        "is_win": is_win,
        "is_post": is_post,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_moment_of_year(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    """Render the Moment of the Year card (Brief §11.7 games-table proxy)."""
    if db is None or snapshot is None:
        return ""
    if snapshot.team_id is None or snapshot.season_year is None:
        return ""

    games = _fetch_season_games(db, int(snapshot.team_id), int(snapshot.season_year))
    if not games:
        return ""

    scored: list[tuple[int, dict[str, Any]]] = []
    for g in games:
        opp_id = int(g["away_team_id"] if int(g["home_team_id"]) == int(snapshot.team_id) else g["home_team_id"])
        opp_rank = _opp_rank_for_game(db, opp_id, int(g["season_year"]), g.get("week"))
        score, packed = _score_moment(int(snapshot.team_id), g, opp_rank)
        scored.append((score, packed))

    # Need a meaningfully-impactful moment to render — at least score 4.
    scored.sort(key=lambda t: -t[0])
    top_score, packed = scored[0]
    if top_score < 4:
        return ""

    headline_cls = (
        "moment-of-year__headline--win" if packed["is_win"]
        else "moment-of-year__headline--loss"
    )
    chip_html = "".join(
        f'<span class="moment-of-year__chip">{escape(c)}</span>'
        for c in packed["chips"]
    )
    program = escape(profile.program_name)

    return f"""
<section class="moment-of-year" aria-labelledby="moment-of-year-h"
         data-module="moment-of-year" data-state="ready"
         data-score="{top_score}">
  <p class="moment-of-year__eyebrow">Moment of the Year · {program} · {int(snapshot.season_year)}</p>
  <h2 id="moment-of-year-h" class="moment-of-year__headline {headline_cls}">{escape(packed['headline'])}</h2>
  <p class="moment-of-year__story">{escape(packed['story'])}</p>
  <div class="moment-of-year__meta">{chip_html}</div>
</section>"""


__all__ = ["render_moment_of_year", "MOMENT_OF_YEAR_CSS"]
