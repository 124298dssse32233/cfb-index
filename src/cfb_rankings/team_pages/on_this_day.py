"""On This Day — Brief §25.3.

Daily-rotated historical artifact surfaced on every team page.

Brief verbatim (§25.3):

    "Daily-rotated historical artifact surfaced on every team page.
     Sources: honors.py, team_annotations (new table, §20), game archives.
     Displayed in the mascot voice. 'On this day in 1979, Bear Bryant
     coached his 315th win, becoming college football's winningest coach.
     The Elephant remembers.'"

    "Zero maintenance after the data is seeded. High emotional resonance.
     This is the kind of module that gets screenshotted and texted to a
     dad-group-chat."

Implementation: query games table for past games on today's MM-DD for
this team. Rank by notability (postseason > ranked opponent > regular
season). Fall back to "Anniversary Nearby" mode that surfaces the
closest-on-the-calendar past game when nothing fell on today exactly.

When no historical data is available at all, render the mascot voice's
'awaiting_signal' line as honest empty state.

Public API:
    render_on_this_day(db, profile, today) -> str
    ON_THIS_DAY_CSS                          -> str
"""
from __future__ import annotations

from datetime import date, datetime
from html import escape
from typing import Any

from .profile_loader import Profile


ON_THIS_DAY_CSS = """
/* On This Day — Brief §25.3
 * A compact retrospective card. Reads --accent-primary from the body.
 */
.on-this-day {
  display: grid;
  gap: clamp(8px, 1.2vw, 14px);
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.2vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-secondary, var(--accent-primary, #c9a24a));
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
}
.on-this-day__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.on-this-day__headline {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(20px, 1.6vw + 8px, 26px);
  font-weight: 400;
  line-height: 1.05;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--fg-primary);
  margin: 0;
}
.on-this-day__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: clamp(14px, 0.4vw + 13px, 16px);
  line-height: 1.5;
  color: var(--fg-secondary);
  margin: 0;
  max-width: 60ch;
}
.on-this-day__voice {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  font-style: italic;
  color: var(--fg-secondary);
  margin: 0;
  padding-top: 4px;
  border-top: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.08));
}
.on-this-day--awaiting .on-this-day__headline {
  font-size: clamp(18px, 1.2vw + 8px, 22px);
  color: var(--fg-muted);
}
"""


# ---------------------------------------------------------------------------
# Data fetch
# ---------------------------------------------------------------------------

def _team_id_from_profile(profile: Profile, db) -> int | None:
    if profile.team_id is not None:
        return int(profile.team_id)
    row = db.query_one(
        "select team_id from teams where slug = :slug",
        {"slug": profile.slug},
    )
    return int(row["team_id"]) if row else None


def _games_on_calendar_date(db, team_id: int, month: int, day: int) -> list[dict[str, Any]]:
    """Past finalized games for this team on this MM-DD across all years."""
    return db.query_all(
        """
        select g.season_year, g.start_time_utc, g.status,
               g.home_team_id, g.away_team_id,
               g.home_points, g.away_points,
               ht.canonical_name as home_name, at.canonical_name as away_name,
               ht.slug as home_slug, at.slug as away_slug,
               g.week, g.season_type
        from games g
        join teams ht on ht.team_id = g.home_team_id
        join teams at on at.team_id = g.away_team_id
        where (g.home_team_id = :tid or g.away_team_id = :tid)
          and g.status = 'Final'
          and g.home_points is not null
          and g.away_points is not null
          and cast(substr(g.start_time_utc, 6, 2) as integer) = :mm
          and cast(substr(g.start_time_utc, 9, 2) as integer) = :dd
        order by g.season_year desc
        """,
        {"tid": team_id, "mm": month, "dd": day},
    )


def _any_past_games(db, team_id: int, limit: int = 200) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select g.season_year, g.start_time_utc,
               g.home_team_id, g.away_team_id,
               g.home_points, g.away_points,
               ht.canonical_name as home_name, at.canonical_name as away_name,
               ht.slug as home_slug, at.slug as away_slug,
               g.week, g.season_type
        from games g
        join teams ht on ht.team_id = g.home_team_id
        join teams at on at.team_id = g.away_team_id
        where (g.home_team_id = :tid or g.away_team_id = :tid)
          and g.status = 'Final'
          and g.home_points is not null
          and g.away_points is not null
        order by g.season_year desc, g.week desc
        limit :lim
        """,
        {"tid": team_id, "lim": limit},
    )


def _game_to_story(team_id: int, row: dict[str, Any]) -> tuple[str, str, int]:
    """Convert a game row into (headline, story, notability_score)."""
    is_home = int(row["home_team_id"]) == team_id
    team_pts = int(row["home_points"] if is_home else row["away_points"])
    opp_pts = int(row["away_points"] if is_home else row["home_points"])
    opp_name = row["away_name"] if is_home else row["home_name"]
    season = int(row["season_year"])
    is_post = (row.get("season_type") or "").lower() in ("postseason", "post")
    margin = team_pts - opp_pts
    abs_margin = abs(margin)
    outcome = "won" if margin > 0 else ("lost" if margin < 0 else "tied")
    loc = "home" if is_home else "road"
    headline = (
        f"{season}: {outcome.title()} {team_pts}-{opp_pts} {('vs' if is_home else 'at')} {opp_name}"
    )
    if is_post:
        headline = f"Postseason {headline}"
    bowl_clue = " in the postseason" if is_post else ""
    if margin > 0:
        descriptor = (
            "blowout" if abs_margin >= 28
            else ("comfortable" if abs_margin >= 14 else "tight")
        )
        story = (
            f"In {season}, the program {outcome} {team_pts}-{opp_pts} "
            f"{('vs' if is_home else 'at')} {opp_name}{bowl_clue} — a "
            f"{descriptor} {loc} result that left the {abs_margin}-point "
            "margin on the books."
        )
    else:
        descriptor = (
            "stinging" if abs_margin >= 21
            else ("close" if abs_margin <= 7 else "one-score")
            if abs_margin <= 8 else "one to file away"
        )
        story = (
            f"In {season}, the program {outcome} {team_pts}-{opp_pts} "
            f"{('vs' if is_home else 'at')} {opp_name}{bowl_clue} — a "
            f"{descriptor} {loc} result, {abs_margin} points either way."
        )

    # Notability: postseason +5, blowout-win +3, ranked opp +2 (not modeled
    # without rank lookup), recency-near +1.
    score = 0
    if is_post:
        score += 5
    if margin > 0 and abs_margin >= 21:
        score += 3
    if margin > 0:
        score += 1
    return (headline, story, score)


def _voice_line(profile: Profile) -> str:
    """Mascot voice tail line for the card."""
    vocab = profile.mascot_voice or {}
    line = (
        vocab.get("win_celebrated")
        or vocab.get("loss_acknowledged")
        or vocab.get("awaiting_signal")
        or ""
    )
    return str(line).strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_on_this_day(db, profile: Profile, today: date | None = None) -> str:
    """Render the On This Day card (Brief §25.3)."""
    today = today or date.today()
    team_id = _team_id_from_profile(profile, db)
    if team_id is None:
        return ""

    program = escape(profile.program_name)

    rows = _games_on_calendar_date(db, team_id, today.month, today.day)
    rank_mode: str
    chosen: dict[str, Any] | None
    if rows:
        # Pick the most notable game by score, breaking ties by recency.
        scored = [(_game_to_story(team_id, r)[2], r) for r in rows]
        scored.sort(key=lambda t: (-t[0], -int(t[1]["season_year"])))
        chosen = scored[0][1]
        rank_mode = "exact"
    else:
        # Fall back to the most-recent significant game in program history,
        # rotated deterministically by today's day-of-year so the surface
        # changes daily without needing exact-date data.
        all_games = _any_past_games(db, team_id, limit=200)
        if not all_games:
            voice = _voice_line(profile)
            voice_html = (
                f'<p class="on-this-day__voice">{escape(voice)}</p>'
                if voice else ""
            )
            return (
                '<section class="on-this-day on-this-day--awaiting" '
                'aria-labelledby="on-this-day-h" data-module="on-this-day" data-state="empty">'
                '<p class="on-this-day__eyebrow">On This Program</p>'
                '<h2 id="on-this-day-h" class="on-this-day__headline">'
                f'{program} · Awaiting season archive</h2>'
                '<p class="on-this-day__story">No finalized game rows have been '
                'ingested for this program yet — the calendar history fills in '
                'once the season archive lands.</p>'
                f'{voice_html}'
                '</section>'
            )
        # Rotate by day-of-year.
        idx = today.timetuple().tm_yday % len(all_games)
        chosen = all_games[idx]
        rank_mode = "rotated"

    headline, story, _score = _game_to_story(team_id, chosen)
    voice = _voice_line(profile)
    voice_html = (
        f'<p class="on-this-day__voice">{escape(voice)}</p>'
        if voice else ""
    )
    eyebrow = (
        f"On This Day — {today.strftime('%B %-d').replace('-', '')}"
        if False else  # %-d not portable on Windows
        f"On This Day — {today.strftime('%B')} {today.day}"
    )
    if rank_mode == "rotated":
        eyebrow = f"From the Archive — {program}"

    return f"""
<section class="on-this-day" aria-labelledby="on-this-day-h"
         data-module="on-this-day" data-state="{rank_mode}">
  <p class="on-this-day__eyebrow">{eyebrow}</p>
  <h2 id="on-this-day-h" class="on-this-day__headline">{escape(headline)}</h2>
  <p class="on-this-day__story">{escape(story)}</p>
  {voice_html}
</section>"""


__all__ = ["render_on_this_day", "ON_THIS_DAY_CSS"]
