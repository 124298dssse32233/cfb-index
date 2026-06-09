"""Recent Form chip — last 10 finalized games as a W/L glyph row with
streak and momentum read. Brief §6.2 ("recent form"). The chip answers the
fan's gut question instantly: *"how are they playing lately?"*

Visual: ten 18×24 colored blocks, leftmost = oldest, rightmost = most recent.
W = team-accent. L = muted grey. T = amber.
Below glyph row: "W2" or "L3" streak chip + "4-1 last 5" + "7-3 last 10" + an
adjective ("Hot", "Cooling", "Cold", "Mixed", "Hibernating").

Falls back gracefully when fewer than 5 finalized games available.

Public API:
    render_recent_form(db, profile, snapshot) -> str
    RECENT_FORM_CSS                            -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot


RECENT_FORM_CSS = """
/* Recent Form chip */
.recent-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px 22px;
  align-items: center;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, #c9a24a);
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
}
.recent-form__head {
  display: grid;
  gap: 4px;
}
.recent-form__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.recent-form__verdict {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(22px, 1.4vw + 10px, 28px);
  font-weight: 400;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  line-height: 1;
  margin: 0;
}
.recent-form__verdict--hot         { color: #4f9d6b; }
.recent-form__verdict--warming     { color: var(--accent-primary, #c9a24a); }
.recent-form__verdict--mixed       { color: var(--fg-primary); }
.recent-form__verdict--cooling     { color: #c98c1a; }
.recent-form__verdict--cold        { color: #c95151; }
.recent-form__verdict--hibernating { color: var(--fg-secondary); }
.recent-form__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  font-style: italic;
  line-height: 1.4;
  color: var(--fg-secondary);
  margin: 0;
  max-width: 56ch;
}

.recent-form__glyphs {
  display: flex;
  gap: 5px;
  align-items: end;
}
.recent-form__glyph {
  width: 14px;
  height: 28px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.08);
}
.recent-form__glyph--w { background: var(--accent-primary, #c9a24a); }
.recent-form__glyph--l { background: rgba(255, 255, 255, 0.14); }
.recent-form__glyph--t { background: #c98c1a; }
.recent-form__glyph-row { display: flex; gap: 5px; align-items: end; }

.recent-form__meta {
  display: grid;
  gap: 4px;
  margin-top: 6px;
}
.recent-form__chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  color: var(--fg-secondary);
}
.recent-form__chip {
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.06));
  font-weight: 600;
  letter-spacing: 0.04em;
}
.recent-form__chip--win  { color: #4f9d6b; border-color: rgba(79, 157, 107, 0.35); }
.recent-form__chip--loss { color: #c95151; border-color: rgba(201, 81, 81, 0.35); }

@media (max-width: 640px) {
  .recent-form { grid-template-columns: 1fr; }
}
"""


def _fetch_last_n(db, team_id: int, n: int = 10) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select
            g.start_time_utc,
            g.season_year,
            g.home_team_id, g.away_team_id,
            g.home_points, g.away_points
        from games g
        where (g.home_team_id = :tid or g.away_team_id = :tid)
          and g.status = 'Final'
          and g.home_points is not null and g.away_points is not null
        order by g.start_time_utc desc, g.game_id desc
        limit :n
        """,
        {"tid": team_id, "n": n},
    )
    return rows


def _result(row: dict[str, Any], team_id: int) -> str:
    hp = row.get("home_points")
    ap = row.get("away_points")
    if hp == ap:
        return "t"
    if row.get("home_team_id") == team_id:
        return "w" if hp > ap else "l"
    return "w" if ap > hp else "l"


def _streak(results: list[str]) -> str:
    """results is newest-first."""
    if not results:
        return ""
    first = results[0]
    n = 1
    for r in results[1:]:
        if r == first:
            n += 1
        else:
            break
    return f"{first.upper()}{n}"


def _verdict(results: list[str]) -> tuple[str, str, str]:
    """Return (label, css_suffix, story)."""
    if not results:
        return ("Awaiting", "hibernating", "No recent games on the ledger.")
    last5 = results[:5]
    w5 = last5.count("w")
    if w5 == 5:
        return ("Hot", "hot", "Five straight. The momentum tier on every blog right now.")
    if w5 == 4:
        return ("Warming", "warming", "Four of five. The board favors this trend.")
    if w5 == 3:
        return ("Mixed", "mixed", "Three of five. Trending up, not yet hot.")
    if w5 == 2:
        return ("Cooling", "cooling", "Two of five. Schedule has caught up.")
    if w5 == 1:
        return ("Cold", "cold", "One of five. The film room is busy this week.")
    return ("Hibernating", "hibernating", "Zero of five. Reset territory.")


def render_recent_form(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    if db is None or snapshot is None:
        return ""
    games = _fetch_last_n(db, int(snapshot.team_id), n=10)
    if len(games) < 5:
        return ""

    # results newest-first
    results = [_result(g, int(snapshot.team_id)) for g in games]
    # glyph row should display oldest-first (left to right reads as time)
    glyphs_oldest_first = list(reversed(results))

    last5_w = results[:5].count("w")
    last5_l = results[:5].count("l")
    last10_w = results.count("w")
    last10_l = results.count("l")

    streak = _streak(results)
    streak_class = "win" if streak and streak.startswith("W") else "loss" if streak.startswith("L") else ""
    verdict_label, verdict_suffix, story = _verdict(results)

    glyph_html = "".join(
        f'<span class="recent-form__glyph recent-form__glyph--{r}" aria-hidden="true"></span>'
        for r in glyphs_oldest_first
    )
    sr_text = "".join(r.upper() for r in glyphs_oldest_first)

    chips_html = (
        f'<span class="recent-form__chip recent-form__chip--{streak_class}">Streak {escape(streak)}</span>'
        if streak else ""
    )
    chips_html += (
        f'<span class="recent-form__chip">Last 5 · {last5_w}-{last5_l}</span>'
        f'<span class="recent-form__chip">Last 10 · {last10_w}-{last10_l}</span>'
    )

    return f"""
<section class="recent-form" aria-labelledby="recent-form-h"
         data-module="recent-form" data-state="ready" data-verdict="{verdict_suffix}">
  <div class="recent-form__head">
    <p class="recent-form__eyebrow">Recent Form · last {len(games)} games</p>
    <h2 id="recent-form-h" class="recent-form__verdict recent-form__verdict--{verdict_suffix}">{escape(verdict_label)}</h2>
    <p class="recent-form__story">{escape(story)}</p>
    <div class="recent-form__chips">{chips_html}</div>
  </div>
  <div class="recent-form__meta">
    <div class="recent-form__glyph-row" role="img" aria-label="Game results oldest to newest: {escape(sr_text)}">
      {glyph_html}
    </div>
  </div>
</section>"""


__all__ = ["render_recent_form", "RECENT_FORM_CSS"]
