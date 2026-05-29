"""Recruiting Footprint chip — Brief §11.5.

Shows the geographic distribution of a team's most-recent recruiting
class as a list of state codes with counts. Surfaces:
  - Home state count (how much in-state recruiting)
  - Top 3 states with counts
  - Total recruits (cross-references Top Commits' national rank)

Sources from player_recruiting_profiles (CFBD HighSchool/JUCO/Prep).

Empty when no recruits in the latest class.

Public API:
    render_recruiting_footprint(db, profile, snapshot) -> str
    RECRUITING_FOOTPRINT_CSS                            -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from ..charts import CHOROPLETH_CSS, render_state_choropleth
from .profile_loader import Profile
from .data import TeamSnapshot


# Number of recent recruiting cycles aggregated into the footprint map. A
# single class is too sparse in the offseason to read as geography; a few
# cycles shows where the program actually pulls from.
_FOOTPRINT_WINDOW = 4


_RECRUITING_FOOTPRINT_CSS = """
/* Recruiting Footprint chip */
.recruit-footprint {
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-secondary, var(--accent-primary, #c9a24a));
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
}
.recruit-footprint__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 10px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
}
.recruit-footprint__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.recruit-footprint__total {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(22px, 1.4vw + 8px, 28px);
  color: var(--accent-primary, #c9a24a);
  line-height: 1;
}
.recruit-footprint__states {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 6px;
}
.recruit-footprint__state {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 11px;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  color: var(--fg-secondary);
}
.recruit-footprint__state--home {
  border-color: var(--accent-primary, #c9a24a);
  color: var(--accent-primary, #c9a24a);
  font-weight: 600;
}
.recruit-footprint__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  font-style: italic;
  line-height: 1.4;
  color: var(--fg-secondary);
  margin: 8px 0 0 0;
  max-width: 56ch;
}
.recruit-footprint__map {
  margin: 12px 0 4px 0;
}
"""

# Ship the shared choropleth styles alongside the footprint chip so the map
# renders wherever this module does (the renderer injects this one constant).
RECRUITING_FOOTPRINT_CSS = _RECRUITING_FOOTPRINT_CSS + CHOROPLETH_CSS


# State of the team for "home state" detection. Lazy lookup.
_TEAM_HOME_STATE: dict[int, str] = {}


def _fetch_state_distribution(db, team_id: int, season_year: int) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select state_province, count(*) as n
          from player_recruiting_profiles
         where team_id = :tid and season_year = :s
           and state_province is not null
         group by state_province
         order by count(*) desc, state_province asc
        """,
        {"tid": team_id, "s": season_year},
    )
    return rows


def _fetch_state_footprint(
    db, team_id: int, latest_year: int, window: int = _FOOTPRINT_WINDOW
) -> dict[str, int]:
    """Recruit counts by state aggregated over the last ``window`` cycles."""
    rows = db.query_all(
        """
        select upper(state_province) as st, count(*) as n
          from player_recruiting_profiles
         where team_id = :tid
           and season_year between :ys and :ye
           and state_province is not null and state_province != ''
         group by upper(state_province)
        """,
        {"tid": team_id, "ys": latest_year - (window - 1), "ye": latest_year},
    )
    out: dict[str, int] = {}
    for r in rows:
        code = (r.get("st") or "").strip()
        n = int(r.get("n") or 0)
        if code and n > 0:
            out[code] = n
    return out


def _team_home_state(db, team_id: int) -> str | None:
    if team_id in _TEAM_HOME_STATE:
        return _TEAM_HOME_STATE[team_id] or None
    rows = db.query_all(
        """
        select state, country
          from teams
         where team_id = :tid limit 1
        """,
        {"tid": team_id},
    )
    state = None
    if rows:
        state = (rows[0].get("state") or "").upper() or None
    _TEAM_HOME_STATE[team_id] = state or ""
    return state


def _latest_recruit_year(db, team_id: int) -> int | None:
    rows = db.query_all(
        """
        select max(season_year) as y from player_recruiting_profiles
         where team_id = :tid
        """,
        {"tid": team_id},
    )
    if not rows:
        return None
    y = rows[0].get("y")
    return int(y) if y else None


def render_recruiting_footprint(
    db, profile: Profile, snapshot: TeamSnapshot | None,
) -> str:
    if db is None or snapshot is None:
        return ""
    team_id = int(snapshot.team_id)
    year = _latest_recruit_year(db, team_id)
    if year is None:
        return ""
    states = _fetch_state_distribution(db, team_id, year)
    if not states:
        return ""

    home_state = _team_home_state(db, team_id)
    total = sum(int(s.get("n") or 0) for s in states)

    in_state_n = next(
        (int(s.get("n") or 0) for s in states
         if (s.get("state_province") or "").upper() == (home_state or "")),
        0,
    )

    # Build state chips
    chips: list[str] = []
    for s in states[:8]:
        code = (s.get("state_province") or "").upper()
        n = int(s.get("n") or 0)
        cls = "recruit-footprint__state"
        if home_state and code == home_state:
            cls += " recruit-footprint__state--home"
        chips.append(
            f'<span class="{cls}">{escape(code)} · {n}</span>'
        )
    if len(states) > 8:
        chips.append(
            f'<span class="recruit-footprint__state">+{len(states)-8} more</span>'
        )

    # Story
    top_state = states[0]
    top_code = (top_state.get("state_province") or "").upper()
    top_n = int(top_state.get("n") or 0)
    if home_state and top_code == home_state and total > 0:
        in_state_pct = int(100 * in_state_n / total)
        story = (
            f"In-state focus — {in_state_pct}% of the {year} class is from {home_state}."
            if in_state_pct >= 30 else
            f"Mixed in-state + national footprint. {in_state_pct}% from {home_state}."
        )
    else:
        story = (
            f"{top_code} leads the {year} class with {top_n} commits. "
            f"National footprint reaching {len(states)} states."
        )

    # Geography map: aggregate a few cycles so the footprint reads as a region,
    # not a single (offseason-sparse) class. The text chips above stay as the
    # accessible, no-SVG fallback.
    footprint = _fetch_state_footprint(db, team_id, year)
    map_html = ""
    if footprint:
        start_year = year - (_FOOTPRINT_WINDOW - 1)
        lead_code = max(footprint, key=lambda k: footprint[k])
        map_caption = (
            f"{sum(footprint.values())} signees across {len(footprint)} states, "
            f"{start_year}-{year}. {lead_code} leads the pull."
        )
        map_html = (
            '<div class="recruit-footprint__map">'
            + render_state_choropleth(
                footprint,
                title=f"Where they recruit · {start_year}-{year}",
                caption=map_caption,
            )
            + '</div>'
        )

    return f"""
<section class="recruit-footprint" aria-labelledby="recruit-footprint-h"
         data-module="recruiting-footprint" data-state="ready" data-class-year="{year}">
  <div class="recruit-footprint__head">
    <p class="recruit-footprint__eyebrow" id="recruit-footprint-h">Recruiting Footprint · {year}</p>
    <span class="recruit-footprint__total">{total}</span>
  </div>
  <div class="recruit-footprint__states">{''.join(chips)}</div>
  <p class="recruit-footprint__story">{escape(story)}</p>
  {map_html}
</section>"""


__all__ = ["render_recruiting_footprint", "RECRUITING_FOOTPRINT_CSS"]
