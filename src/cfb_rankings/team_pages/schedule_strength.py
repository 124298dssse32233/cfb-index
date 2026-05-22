"""Schedule Strength chip.

Surfaces opponent quality on every team page. Brief §5.1 lists
"Opponent-Adjusted SOS" as one of the Team Savant Card's 15 metrics
("the strength of schedule chip, because everything else is
meaningless without it"). This module renders it as its own visible
chip rather than burying it in the Savant percentile-bar set.

Components computed from the games table:
  - avg_opp_win_pct  — average opponent win percentage across season
  - top25_count      — number of AP top-25 opponents played
  - top10_count      — number of AP top-10 opponents played

Score combines win-pct band + ranked-count weight. 4 bands:
  Brutal     — avg ≥ 0.65 OR 4+ top-25 opps
  Hard       — avg ≥ 0.55 OR 2+ top-25
  Balanced   — avg ≥ 0.45
  Soft       — below

Public API:
    render_schedule_strength(db, profile, snapshot) -> str
    SCHEDULE_STRENGTH_CSS                              -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot


SCHEDULE_STRENGTH_CSS = """
/* Schedule Strength chip */
.schedule-strength {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px 18px;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-secondary, var(--accent-primary, #c9a24a));
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
}
.schedule-strength__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.schedule-strength__band {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(22px, 1.6vw + 10px, 30px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--fg-primary);
  margin: 0;
}
.schedule-strength__band--brutal   { color: #c95151; }
.schedule-strength__band--hard     { color: #c98c1a; }
.schedule-strength__band--balanced { color: var(--accent-primary, #c9a24a); }
.schedule-strength__band--soft     { color: var(--fg-secondary); }

.schedule-strength__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  font-style: italic;
  line-height: 1.4;
  color: var(--fg-secondary);
  margin: 0;
  max-width: 56ch;
}

.schedule-strength__stats {
  display: grid;
  gap: 4px;
  text-align: right;
  min-width: 120px;
}
.schedule-strength__stat-row {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  align-items: baseline;
}
.schedule-strength__stat-label {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.schedule-strength__stat-value {
  font-family: var(--font-mono, monospace);
  font-size: 14px;
  font-weight: 600;
  color: var(--fg-primary);
}
@media (max-width: 640px) {
  .schedule-strength { grid-template-columns: 1fr; }
  .schedule-strength__stats { text-align: left; }
  .schedule-strength__stat-row { justify-content: flex-start; }
}
"""


# ---------------------------------------------------------------------------
# Data fetch
# ---------------------------------------------------------------------------

def _fetch_opponent_records(db, team_id: int, season_year: int) -> list[dict[str, Any]]:
    """For each opponent the focal team played this season, return their
    season record (wins/losses + final AP rank if any)."""
    rows = db.query_all(
        """
        with opps as (
            select distinct
                case when g.home_team_id = :tid then g.away_team_id
                     else g.home_team_id end as opp_id
            from games g
            where (g.home_team_id = :tid or g.away_team_id = :tid)
              and g.season_year = :s
              and g.status = 'Final'
              and g.home_points is not null and g.away_points is not null
        )
        select o.opp_id, t.canonical_name,
            sum(case
                when g.home_team_id = o.opp_id and g.home_points > g.away_points then 1
                when g.away_team_id = o.opp_id and g.away_points > g.home_points then 1
                else 0 end) as wins,
            sum(case
                when g.home_team_id = o.opp_id and g.home_points < g.away_points then 1
                when g.away_team_id = o.opp_id and g.away_points < g.home_points then 1
                else 0 end) as losses,
            (select min(rank_value) from official_rankings
              where team_id = o.opp_id and season_year = :s
                and ranking_system = 'AP Top 25') as best_ap
        from opps o
        join teams t on t.team_id = o.opp_id
        left join games g
          on (g.home_team_id = o.opp_id or g.away_team_id = o.opp_id)
          and g.season_year = :s
          and g.status = 'Final'
          and g.home_points is not null and g.away_points is not null
        group by o.opp_id
        """,
        {"tid": team_id, "s": season_year},
    )
    return rows


def _band(avg_pct: float, top25: int, top10: int) -> tuple[str, str]:
    if avg_pct >= 0.65 or top25 >= 4 or top10 >= 2:
        return ("Brutal", "brutal")
    if avg_pct >= 0.55 or top25 >= 2:
        return ("Hard", "hard")
    if avg_pct >= 0.45:
        return ("Balanced", "balanced")
    return ("Soft", "soft")


def render_schedule_strength(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    if db is None or snapshot is None:
        return ""
    opps = _fetch_opponent_records(db, int(snapshot.team_id), int(snapshot.season_year))
    if not opps or len(opps) < 6:
        return ""

    pcts: list[float] = []
    top25_count = 0
    top10_count = 0
    ranked_names: list[str] = []
    for r in opps:
        w = int(r.get("wins") or 0)
        l = int(r.get("losses") or 0)
        if w + l == 0:
            continue
        pct = w / (w + l)
        pcts.append(pct)
        ap = r.get("best_ap")
        if ap is not None:
            try:
                r_int = int(ap)
                if 0 < r_int <= 25:
                    top25_count += 1
                    ranked_names.append(r.get("canonical_name", "?"))
                if 0 < r_int <= 10:
                    top10_count += 1
            except (TypeError, ValueError):
                pass
    if not pcts:
        return ""
    avg_pct = sum(pcts) / len(pcts)
    band_label, band_suffix = _band(avg_pct, top25_count, top10_count)

    program = escape(profile.program_name)
    story_parts: list[str] = [
        f"Average opponent win rate {int(avg_pct * 100)}% across {len(pcts)} finalized games."
    ]
    if top25_count > 0:
        ranked_chunk = ", ".join(escape(n) for n in ranked_names[:3])
        more = "" if top25_count <= 3 else f" +{top25_count-3} more"
        story_parts.append(
            f"{top25_count} AP top-25 opponent{'s' if top25_count != 1 else ''} played ({ranked_chunk}{more})."
        )
    elif avg_pct >= 0.45:
        story_parts.append("No top-25 opponents, but mid-tier slate kept the schedule honest.")
    else:
        story_parts.append("Few national contenders on the slate — recruit-board talk discounts the wins accordingly.")

    story = " ".join(story_parts)

    stats_html = (
        '<div class="schedule-strength__stats">'
        '<div class="schedule-strength__stat-row">'
        f'<span class="schedule-strength__stat-label">Opp Win %</span>'
        f'<span class="schedule-strength__stat-value">{avg_pct:.3f}</span>'
        '</div>'
        '<div class="schedule-strength__stat-row">'
        f'<span class="schedule-strength__stat-label">Top-25</span>'
        f'<span class="schedule-strength__stat-value">{top25_count}</span>'
        '</div>'
        '<div class="schedule-strength__stat-row">'
        f'<span class="schedule-strength__stat-label">Top-10</span>'
        f'<span class="schedule-strength__stat-value">{top10_count}</span>'
        '</div>'
        '</div>'
    )

    return f"""
<section class="schedule-strength" aria-labelledby="schedule-strength-h"
         data-module="schedule-strength" data-state="ready" data-band="{band_suffix}">
  <div>
    <p class="schedule-strength__eyebrow">Schedule Strength · {program} · {snapshot.season_year}</p>
    <h2 id="schedule-strength-h" class="schedule-strength__band schedule-strength__band--{band_suffix}">{escape(band_label)}</h2>
    <p class="schedule-strength__story">{story}</p>
  </div>
  {stats_html}
</section>"""


__all__ = ["render_schedule_strength", "SCHEDULE_STRENGTH_CSS"]
