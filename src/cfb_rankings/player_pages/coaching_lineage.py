"""Coaching Lineage module — Brief Signature Bet #10.

Shows the player's head-coach lineage during their college career.
Sources from team_seasons.head_coach (CFBD coaches ingest, 2018+).

For each year the player was on the roster, we show:
  - Year + team
  - Head coach
  - Whether the coach changed mid-career (era marker)

Falls back to "Awaiting Signal" when no head_coach rows are available
for the player's seasons.

Public API:
    render_coaching_lineage(db, player_id, primary_team_id, seasons) -> str
    COACHING_LINEAGE_CSS                                              -> str
"""
from __future__ import annotations

from html import escape
from typing import Any, Iterable


COACHING_LINEAGE_CSS = """
/* Coaching Lineage module */
.coaching-lineage {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.coaching-lineage__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
  margin-bottom: 12px;
}
.coaching-lineage__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted-foreground, var(--fg-muted, #666));
  margin: 0;
}
.coaching-lineage__total {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--muted-foreground, var(--fg-muted, #666));
}
.coaching-lineage__rows {
  display: grid;
  gap: 8px;
}
.coaching-lineage__row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 14px;
  align-items: baseline;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.06));
  border-radius: 6px;
}
.coaching-lineage__row--era-change {
  border-left: 3px solid var(--accent-primary, var(--accolade-gold-base, #d1a23a));
}
.coaching-lineage__year {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 12px;
  color: var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  font-weight: 600;
  min-width: 50px;
}
.coaching-lineage__coach {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 13px;
  font-weight: 600;
  color: var(--foreground, var(--fg-primary, #222));
}
.coaching-lineage__team {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  color: var(--muted-foreground, var(--fg-muted, #666));
}
.coaching-lineage__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  font-style: italic;
  line-height: 1.4;
  color: var(--muted-foreground, var(--fg-secondary, #666));
  margin: 8px 0 0 0;
  max-width: 56ch;
}
.coaching-lineage--empty {
  color: var(--muted-foreground, var(--fg-muted, #666));
  font-style: italic;
  font-size: var(--fs-meta, 0.78rem);
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
}
"""


def render_coaching_lineage(
    db, player_id: int | None, primary_team_id: int | None,
    seasons: Iterable[int] | None = None,
) -> str:
    """Render the coaching lineage panel for a player.

    Args:
        db: Database handle
        player_id: Player ID (used for roster_history lookup if seasons not given)
        primary_team_id: Team to query head_coach for
        seasons: Optional explicit list of seasons; otherwise inferred from
                 player_season_stats or roster_history.
    """
    if db is None or primary_team_id is None:
        return ""

    # If seasons not given, infer from player's actual playing seasons
    if seasons is None and player_id is not None:
        rows = db.query_all(
            """
            select distinct season_year
              from player_season_stats
             where player_id = :pid
             order by season_year
            """,
            {"pid": player_id},
        )
        seasons = [int(r["season_year"]) for r in rows]
    else:
        seasons = sorted(set(int(s) for s in (seasons or [])))

    if not seasons:
        return (
            '<section class="coaching-lineage coaching-lineage--empty" '
            'data-module="coaching-lineage" data-state="empty">'
            'Coaching lineage fills in once we have multi-season roster data for this player.'
            '</section>'
        )

    # Fetch head_coach for each season
    rows = db.query_all(
        """
        select ts.season_year, ts.head_coach, t.canonical_name as team_name
          from team_seasons ts
          join teams t on t.team_id = ts.team_id
         where ts.team_id = :tid
           and ts.season_year in ({placeholders})
         order by ts.season_year
        """.format(
            placeholders=",".join(str(int(s)) for s in seasons)
        ),
        {"tid": primary_team_id},
    )
    if not rows or all(not r.get("head_coach") for r in rows):
        return (
            '<section class="coaching-lineage coaching-lineage--empty" '
            'data-module="coaching-lineage" data-state="empty">'
            'Coaching lineage fills in once the head-coach data is ingested for this team.'
            '</section>'
        )

    # Build rows
    row_html: list[str] = []
    coaches_seen: list[str] = []
    previous_coach: str | None = None
    for r in rows:
        year = int(r.get("season_year"))
        coach = r.get("head_coach") or "—"
        team = r.get("team_name") or "—"
        era_change_class = ""
        if previous_coach is not None and coach != previous_coach:
            era_change_class = " coaching-lineage__row--era-change"
        if coach and coach not in coaches_seen and coach != "—":
            coaches_seen.append(coach)
        previous_coach = coach
        row_html.append(
            f'<div class="coaching-lineage__row{era_change_class}">'
            f'<span class="coaching-lineage__year">{year}</span>'
            f'<div>'
            f'<div class="coaching-lineage__coach">{escape(coach)}</div>'
            f'<div class="coaching-lineage__team">{escape(team)}</div>'
            f'</div>'
            f'<span class="coaching-lineage__team">'
            f'{"era →" if era_change_class else ""}</span>'
            f'</div>'
        )

    # Story line
    if len(coaches_seen) == 1:
        story = f"Played his entire career under {coaches_seen[0]}."
    elif len(coaches_seen) == 2:
        story = (
            f"Coaching transition mid-career: {coaches_seen[0]} → "
            f"{coaches_seen[1]}. Worth noting in scheme + development context."
        )
    else:
        names = ", ".join(coaches_seen[:-1]) + f", and {coaches_seen[-1]}"
        story = (
            f"Played under {len(coaches_seen)} different head coaches: {names}. "
            "Multi-era developmental context."
        )

    span_chunk = f"{seasons[0]}–{seasons[-1]}" if len(seasons) > 1 else str(seasons[0])

    return f"""
<section class="coaching-lineage" data-module="coaching-lineage" data-state="ready">
  <div class="coaching-lineage__head">
    <p class="coaching-lineage__eyebrow">Coaching Lineage · {escape(span_chunk)}</p>
    <span class="coaching-lineage__total">{len(coaches_seen)} coach{'es' if len(coaches_seen) != 1 else ''}</span>
  </div>
  <div class="coaching-lineage__rows">{''.join(row_html)}</div>
  <p class="coaching-lineage__story">{escape(story)}</p>
</section>"""


__all__ = ["render_coaching_lineage", "COACHING_LINEAGE_CSS"]
