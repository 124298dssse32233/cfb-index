"""Statement Win Counter — surfaces the most-impressive wins of the most
recent finalized season. Sources from games + official_rankings.

A "statement win" is a win against an opponent who was AP top-25 either at
the time of the game (preferred) or at season's end (fallback). The module
shows the count + the marquee opponent + a one-line story.

Empty when zero top-25 wins. Otherwise renders even with one.

Public API:
    render_statement_wins(db, profile, snapshot) -> str
    STATEMENT_WINS_CSS                            -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot


STATEMENT_WINS_CSS = """
/* Statement Wins counter */
.statement-wins {
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
.statement-wins__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.statement-wins__count {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(36px, 3vw + 12px, 56px);
  font-weight: 400;
  letter-spacing: 0.02em;
  line-height: 1;
  color: var(--accent-primary, #c9a24a);
  margin: 0;
}
.statement-wins__count--zero { color: var(--fg-secondary); }
.statement-wins__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  font-style: italic;
  line-height: 1.4;
  color: var(--fg-secondary);
  margin: 6px 0 0 0;
  max-width: 56ch;
}
.statement-wins__opponents {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 6px;
}
.statement-wins__opponent {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  color: var(--fg-secondary);
}
@media (max-width: 640px) {
  .statement-wins { grid-template-columns: 1fr; }
}
"""


def _fetch_top25_wins(db, team_id: int, season_year: int) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        with my_wins as (
          select
            case when g.home_team_id = :tid then g.away_team_id
                 else g.home_team_id end as opp_id,
            case when g.home_team_id = :tid then g.home_points
                 else g.away_points end as my_pts,
            case when g.home_team_id = :tid then g.away_points
                 else g.home_points end as opp_pts,
            g.week, g.start_time_utc
          from games g
          where (g.home_team_id = :tid or g.away_team_id = :tid)
            and g.season_year = :s
            and g.status = 'Final'
            and g.home_points is not null and g.away_points is not null
        )
        select
          mw.opp_id, t.canonical_name, mw.my_pts, mw.opp_pts,
          (select min(rank_value) from official_rankings
            where team_id = mw.opp_id and season_year = :s
              and ranking_system = 'AP Top 25') as best_ap
        from my_wins mw
        join teams t on t.team_id = mw.opp_id
        where mw.my_pts > mw.opp_pts
        """,
        {"tid": team_id, "s": season_year},
    )
    return rows


def render_statement_wins(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    if db is None or snapshot is None:
        return ""
    rows = _fetch_top25_wins(db, int(snapshot.team_id), int(snapshot.season_year))
    statement_wins: list[dict[str, Any]] = []
    for r in rows:
        ap = r.get("best_ap")
        if ap is None:
            continue
        try:
            ap_int = int(ap)
            if 0 < ap_int <= 25:
                r["ap_rank"] = ap_int
                statement_wins.append(r)
        except (TypeError, ValueError):
            continue

    if not statement_wins:
        return ""

    statement_wins.sort(key=lambda x: x["ap_rank"])
    count = len(statement_wins)
    opp_pills = "".join(
        f'<span class="statement-wins__opponent">#{r["ap_rank"]} {escape(r.get("canonical_name", "?"))}</span>'
        for r in statement_wins[:5]
    )
    if count > 5:
        opp_pills += f'<span class="statement-wins__opponent">+{count - 5} more</span>'

    marquee = statement_wins[0]
    if count == 1:
        story = (
            f"One statement win on the ledger — {marquee.get('canonical_name', '?')} "
            f"({marquee['ap_rank']}) by {abs(marquee.get('my_pts', 0) - marquee.get('opp_pts', 0))}."
        )
    else:
        story = (
            f"{count} wins over AP top-25 opponents. Headlined by "
            f"#{marquee['ap_rank']} {marquee.get('canonical_name', '?')}."
        )

    return f"""
<section class="statement-wins" aria-labelledby="statement-wins-h"
         data-module="statement-wins" data-state="ready" data-count="{count}">
  <div>
    <p class="statement-wins__eyebrow">Statement Wins · {snapshot.season_year}</p>
    <h2 id="statement-wins-h" class="statement-wins__count">{count}</h2>
    <p class="statement-wins__story">{escape(story)}</p>
    <div class="statement-wins__opponents">{opp_pills}</div>
  </div>
</section>"""


__all__ = ["render_statement_wins", "STATEMENT_WINS_CSS"]
