"""Bowl History chip — most-recent postseason result + 5-year postseason
win-loss row. Sources from the games table where season_type='postseason'.
Audit T28 fragment ("bowl game continuity story").

Renders even with single-game history. Goes empty when zero postseason
games on the ledger.

Public API:
    render_bowl_history(db, profile, snapshot) -> str
    BOWL_HISTORY_CSS                            -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot, fetch_bowl_ledger_row
from cfb_rankings.team_preview.bowl_ledger import resolve_bowl_record_display


BOWL_HISTORY_CSS = """
/* Bowl History chip */
.bowl-history {
  display: grid;
  gap: 8px;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-secondary, var(--accent-primary, #c9a24a));
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
}
.bowl-history__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.bowl-history__verdict {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(22px, 1.4vw + 10px, 30px);
  font-weight: 400;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  line-height: 1;
  color: var(--fg-primary);
  margin: 0;
}
.bowl-history__recent {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  line-height: 1.4;
  color: var(--fg-secondary);
  margin: 0;
}
.bowl-history__row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.bowl-history__year {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 11px;
  padding: 3px 9px;
  border-radius: 999px;
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  background: rgba(255, 255, 255, 0.025);
}
.bowl-history__year--win  { color: #4f9d6b; border-color: rgba(79, 157, 107, 0.35); }
.bowl-history__year--loss { color: #c95151; border-color: rgba(201, 81, 81, 0.35); }
"""


def _fetch_postseason(db, team_id: int) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select g.season_year, g.start_time_utc,
               g.home_team_id, g.away_team_id,
               g.home_points, g.away_points,
               g.notes
          from games g
         where g.season_type = 'postseason'
           and (g.home_team_id = :tid or g.away_team_id = :tid)
           and g.status = 'Final'
           and g.home_points is not null
           and g.away_points is not null
         order by g.season_year desc, g.start_time_utc desc
        """,
        {"tid": team_id},
    )
    return rows


def render_bowl_history(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    if db is None or snapshot is None:
        return ""
    rows = _fetch_postseason(db, int(snapshot.team_id))
    if not rows:
        return ""

    # Compute most-recent + last-5 record
    most_recent = rows[0]
    recent_year = int(most_recent.get("season_year"))
    hp = most_recent.get("home_points")
    ap = most_recent.get("away_points")
    is_home = most_recent.get("home_team_id") == snapshot.team_id
    won = (hp > ap) if is_home else (ap > hp)

    # Last 5 postseason
    last5 = rows[:5]
    wins = 0
    losses = 0
    year_pills: list[str] = []
    for r in last5:
        rh = r.get("home_team_id") == snapshot.team_id
        rhp, rap = r.get("home_points"), r.get("away_points")
        rwon = (rhp > rap) if rh else (rap > rhp)
        wins += 1 if rwon else 0
        losses += 0 if rwon else 1
        cls = "win" if rwon else "loss"
        year_pills.append(
            f'<span class="bowl-history__year bowl-history__year--{cls}">{int(r.get("season_year"))}</span>'
        )

    total_games = len(rows)
    total_wins = sum(
        1 for r in rows
        if (r.get("home_team_id") == snapshot.team_id) == (r.get("home_points") > r.get("away_points"))
    )
    total_losses = total_games - total_wins

    # Honest scope resolution (spec §1.5): the games table only holds CFBD-era
    # (~2018+) postseason results, so it must NEVER be labelled "all-time". Hand
    # the recent-era tally + any verified ledger row to resolve_bowl_record_display,
    # which decides whether an all-time, recent-era, or unavailable label is honest.
    era_years = sorted({int(r.get("season_year")) for r in rows})
    recent_era_label = (
        f"{era_years[0]}-{era_years[-1]}" if len(era_years) > 1
        else (str(era_years[0]) if era_years else "recent")
    )
    ledger_row = fetch_bowl_ledger_row(db, snapshot.slug)
    display = resolve_bowl_record_display(
        ledger_row,
        recent_postseason_wins=total_wins,
        recent_postseason_losses=total_losses,
        recent_era_label=recent_era_label,
    )
    if display.suppress:
        return ""
    verdict = display.label
    recent_line = (
        f"Most recent: {recent_year} — {'win' if won else 'loss'} {hp}-{ap} "
        f"({'home' if is_home else 'away'})."
    )
    if last5:
        recent_line += f" Last 5 postseason: {wins}-{losses}."

    return f"""
<section class="bowl-history" aria-labelledby="bowl-history-h"
         data-module="bowl-history" data-state="ready">
  <p class="bowl-history__eyebrow">Bowl / Postseason Ledger</p>
  <h2 id="bowl-history-h" class="bowl-history__verdict">{escape(verdict)}</h2>
  <p class="bowl-history__recent">{escape(recent_line)}</p>
  <div class="bowl-history__row" aria-label="Recent postseason appearances">
    {''.join(year_pills)}
  </div>
</section>"""


__all__ = ["render_bowl_history", "BOWL_HISTORY_CSS"]
