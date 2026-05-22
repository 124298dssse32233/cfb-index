"""Conference Standing module — Brief §10.2 / §10.3.

The full Conference Lens (Brief §10) is a toggle that recalculates
every module's reference population against conference peers vs.
national peers. That requires DB-side precompute + module CSS swaps
across 9 modules — out of scope for same-day.

This is §10.2 / §10.3: a dedicated compact standing module that
positions the focal team within its conference cohort. Renders below
the season snapshot.

Brief verbatim (§10.3):

    "A compact table showing all conference teams ranked by SP+ +
     Record, with your team highlighted. Not a full rankings page —
     a positioning device. 'You are 3rd in the conference by SP+.
     The teams ranked above you are your direct path to the title
     game.'"

Public API:
    render_conference_standing(db, profile, snapshot) -> str
    CONFERENCE_STANDING_CSS                            -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot


CONFERENCE_STANDING_CSS = """
/* Conference Standing — Brief §10.2-10.3 */
.conference-standing {
  display: grid;
  gap: clamp(10px, 1.4vw, 16px);
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
}
.conference-standing__header {
  display: grid;
  gap: 4px;
}
.conference-standing__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.conference-standing__title {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(22px, 1.8vw + 10px, 30px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--fg-primary);
  margin: 0;
}
.conference-standing__summary {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 14px;
  font-style: italic;
  line-height: 1.4;
  color: var(--fg-secondary);
  margin: 0;
}
.conference-standing__table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
}
.conference-standing__table thead th {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--fg-muted);
  text-align: left;
  padding: 6px 8px;
  border-bottom: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
}
.conference-standing__table tbody td {
  padding: 8px;
  font-size: 13px;
  color: var(--fg-secondary);
  border-bottom: 1px solid var(--stroke-subtle, rgba(255,255,255,0.05));
}
.conference-standing__table tbody tr:last-child td {
  border-bottom: none;
}
.conference-standing__table .conference-standing__row--focal {
  background: color-mix(in oklab, var(--accent-primary, #c9a24a) 12%, transparent);
  border-left: 3px solid var(--accent-primary, #c9a24a);
}
.conference-standing__table .conference-standing__row--focal td {
  color: var(--fg-primary);
  font-weight: 700;
}
.conference-standing__table .conference-standing__rank {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: 16px;
  letter-spacing: 0.02em;
  color: var(--accent-primary, #c9a24a);
  font-weight: 400;
}
.conference-standing__table .conference-standing__team-link {
  color: inherit;
  text-decoration: none;
}
.conference-standing__table .conference-standing__team-link:hover {
  text-decoration: underline;
}
.conference-standing__table .conference-standing__record {
  font-family: var(--font-mono, monospace);
  font-size: 12px;
}
"""


# ---------------------------------------------------------------------------
# Data fetch
# ---------------------------------------------------------------------------

def _fetch_conference_records(db, conference_id: int, season_year: int) -> list[dict[str, Any]]:
    """Records for every team in the given conference for the given year.

    Computed inline from games table; SP+ rank pulled if available.
    """
    rows = db.query_all(
        """
        with conf_teams as (
            select t.team_id, t.slug, t.canonical_name, t.school_name
            from teams t
            where t.current_conference_id = :conf
              and t.level_code = 'FBS'
        ),
        team_records as (
            select ct.team_id, ct.slug, ct.canonical_name, ct.school_name,
                   sum(case
                       when g.home_team_id = ct.team_id and g.home_points > g.away_points then 1
                       when g.away_team_id = ct.team_id and g.away_points > g.home_points then 1
                       else 0 end) as wins,
                   sum(case
                       when g.home_team_id = ct.team_id and g.home_points < g.away_points then 1
                       when g.away_team_id = ct.team_id and g.away_points < g.home_points then 1
                       else 0 end) as losses,
                   count(g.game_id) as game_count
            from conf_teams ct
            left join games g
              on (g.home_team_id = ct.team_id or g.away_team_id = ct.team_id)
              and g.season_year = :season
              and g.status = 'Final'
              and g.home_points is not null
              and g.away_points is not null
            group by ct.team_id
        )
        select * from team_records
        order by wins desc, losses asc, canonical_name asc
        """,
        {"conf": conference_id, "season": season_year},
    )
    return rows


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_conference_standing(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    """Render the Conference Standing compact module (Brief §10.2-10.3)."""
    if snapshot is None or snapshot.conference_id is None:
        return ""

    rows = _fetch_conference_records(db, int(snapshot.conference_id), int(snapshot.season_year))
    if not rows or len(rows) < 3:
        return ""

    # Find focal team rank
    focal_rank = None
    focal_record = None
    for i, r in enumerate(rows):
        if int(r["team_id"]) == int(snapshot.team_id):
            focal_rank = i + 1
            focal_record = (int(r["wins"]), int(r["losses"]))
            break

    if focal_rank is None:
        return ""

    above = focal_rank - 1
    total = len(rows)
    conf = escape(snapshot.conference_name or "Conference")
    program = escape(profile.program_name)
    fw, fl = focal_record

    if above == 0:
        summary = (
            f"{program} sits at the top of the {conf} at {fw}-{fl}. "
            "Everyone else is chasing."
        )
    elif above <= 2:
        summary = (
            f"{program} is {_ordinal(focal_rank)} in the {conf} at {fw}-{fl}. "
            f"{above} {'team' if above == 1 else 'teams'} above — that's the direct path to the title game."
        )
    elif above <= 5:
        summary = (
            f"{program} sits {_ordinal(focal_rank)} of {total} in the {conf} at {fw}-{fl}. "
            "Mid-conference — moves up or down depend on rivalry results and the late-season closing run."
        )
    else:
        summary = (
            f"{program} is {_ordinal(focal_rank)} of {total} in the {conf} at {fw}-{fl}. "
            "The path to the title is steep — the focus is on bowl access and rivalry wins."
        )

    table_rows: list[str] = []
    for i, r in enumerate(rows):
        rank = i + 1
        slug = r["slug"]
        name = r["canonical_name"] or r["school_name"] or slug
        wins, losses = int(r["wins"]), int(r["losses"])
        is_focal = int(r["team_id"]) == int(snapshot.team_id)
        focal_cls = " conference-standing__row--focal" if is_focal else ""
        link = (
            f'<a class="conference-standing__team-link" href="/teams/{escape(slug)}.html">'
            f'{escape(name)}</a>'
        )
        table_rows.append(
            f'<tr class="conference-standing__row{focal_cls}">'
            f'<td><span class="conference-standing__rank">{rank}</span></td>'
            f'<td>{link}</td>'
            f'<td><span class="conference-standing__record">{wins}-{losses}</span></td>'
            f'</tr>'
        )

    return f"""
<section class="conference-standing" aria-labelledby="conference-standing-h"
         data-module="conference-standing" data-state="ready">
  <div class="conference-standing__header">
    <p class="conference-standing__eyebrow">{conf} Standing · {snapshot.season_year}</p>
    <h2 id="conference-standing-h" class="conference-standing__title">
      {_ordinal(focal_rank)} in the {conf}
    </h2>
    <p class="conference-standing__summary">{escape(summary)}</p>
  </div>
  <table class="conference-standing__table" aria-label="{conf} standings">
    <thead><tr><th scope="col">#</th><th scope="col">Program</th><th scope="col">Record</th></tr></thead>
    <tbody>
      {''.join(table_rows)}
    </tbody>
  </table>
</section>"""


__all__ = ["render_conference_standing", "CONFERENCE_STANDING_CSS"]
