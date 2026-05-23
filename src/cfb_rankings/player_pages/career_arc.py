"""Career Arc module — Brief §16.4 ("the durable bio layer").

Surfaces the player's college-football career arc in three beats:
  1. Recruit (HS) — stars + national rank if a recruit profile exists
  2. College era (with team + years played)
  3. NFL Draft (if drafted)

Renders even with partial data (e.g., player still in college shows
recruit + college only). Empty when no career data at all.

Public API:
    render_career_arc(db, player_id) -> str
    CAREER_ARC_CSS                   -> str
"""
from __future__ import annotations

from html import escape


CAREER_ARC_CSS = """
/* Career Arc module */
.career-arc {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.career-arc__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted-foreground, var(--fg-muted, #666));
  margin: 0 0 14px 0;
}
.career-arc__rail {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
  position: relative;
}
.career-arc__rail::before {
  content: '';
  position: absolute;
  top: 14px;
  left: 10%;
  right: 10%;
  height: 2px;
  background: var(--stroke-subtle, rgba(255,255,255,0.10));
  z-index: 0;
}
.career-arc__beat {
  display: grid;
  gap: 8px;
  text-align: center;
  position: relative;
  z-index: 1;
  padding: 0 8px;
}
.career-arc__beat-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--stroke-subtle, rgba(255,255,255,0.10));
  margin: 0 auto;
  display: grid;
  place-items: center;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 11px;
  color: var(--muted-foreground, var(--fg-muted, #666));
  font-weight: 700;
}
.career-arc__beat--has-data .career-arc__beat-dot {
  background: var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  color: var(--background, #fff);
}
.career-arc__beat-label {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--muted-foreground, var(--fg-muted, #666));
}
.career-arc__beat-headline {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(15px, 0.9vw + 9px, 19px);
  letter-spacing: 0.02em;
  line-height: 1.1;
  color: var(--foreground, var(--fg-primary, #222));
}
.career-arc__beat-meta {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 11px;
  color: var(--muted-foreground, var(--fg-secondary, #666));
}
.career-arc--empty {
  color: var(--muted-foreground, var(--fg-muted, #666));
  font-style: italic;
  font-size: var(--fs-meta, 0.78rem);
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
}
"""


def render_career_arc(db, player_id: int | None) -> str:
    if db is None or player_id is None:
        return ""

    # Recruit profile
    recruit_rows = db.query_all(
        """
        select stars, national_rank, position, season_year
          from player_recruiting_profiles
         where player_id = :pid
         order by season_year asc
         limit 1
        """,
        {"pid": player_id},
    )
    recruit = recruit_rows[0] if recruit_rows else None

    # College years from player_season_stats
    college_rows = db.query_all(
        """
        select distinct pss.season_year, t.canonical_name as team_name
          from player_season_stats pss
          left join teams t on t.team_id = pss.team_id
         where pss.player_id = :pid
         order by pss.season_year
        """,
        {"pid": player_id},
    )

    # NFL draft
    nfl_rows = db.query_all(
        """
        select draft_year, round, overall, nfl_team
          from player_nfl_draft
         where player_id = :pid
         limit 1
        """,
        {"pid": player_id},
    )
    nfl = nfl_rows[0] if nfl_rows else None

    has_any = bool(recruit or college_rows or nfl)
    if not has_any:
        return ""

    def _beat(label: str, headline: str, meta: str, has_data: bool, dot: str) -> str:
        cls = "career-arc__beat" + (" career-arc__beat--has-data" if has_data else "")
        return (
            f'<div class="{cls}">'
            f'<div class="career-arc__beat-dot">{escape(dot)}</div>'
            f'<div class="career-arc__beat-label">{escape(label)}</div>'
            f'<div class="career-arc__beat-headline">{escape(headline)}</div>'
            f'<div class="career-arc__beat-meta">{escape(meta)}</div>'
            '</div>'
        )

    # Recruit beat
    if recruit:
        stars = recruit.get("stars") or 0
        rank = recruit.get("national_rank")
        yr = recruit.get("season_year")
        star_glyph = "★" * int(stars) if stars else "—"
        recruit_headline = star_glyph
        recruit_meta = f"#{rank} national" if rank else (f"{yr} class" if yr else "Recruit")
    else:
        recruit_headline, recruit_meta = "—", "No recruit profile"

    # College beat
    if college_rows:
        first_year = int(college_rows[0].get("season_year"))
        last_year = int(college_rows[-1].get("season_year"))
        teams = sorted({r.get("team_name") for r in college_rows if r.get("team_name")})
        team_chunk = teams[0] if len(teams) == 1 else f"{len(teams)} teams"
        college_headline = team_chunk
        college_meta = (
            str(first_year)
            if first_year == last_year
            else f"{first_year}–{last_year}"
        )
    else:
        college_headline, college_meta = "—", "No college data"

    # NFL beat
    if nfl:
        overall = nfl.get("overall")
        rnd = nfl.get("round") or 0
        team = nfl.get("nfl_team") or ""
        year = nfl.get("draft_year") or ""
        nfl_headline = f"R{rnd} · #{overall}" if overall else f"R{rnd}"
        nfl_meta = f"{team} · {year}".strip(" ·")
    else:
        nfl_headline, nfl_meta = "—", "Not drafted (yet)"

    return f"""
<section class="career-arc" data-module="career-arc" data-state="ready">
  <p class="career-arc__eyebrow">Career Arc</p>
  <div class="career-arc__rail">
    {_beat("Recruit", recruit_headline, recruit_meta, bool(recruit), "HS")}
    {_beat("College", college_headline, college_meta, bool(college_rows), "CFB")}
    {_beat("NFL Draft", nfl_headline, nfl_meta, bool(nfl), "NFL")}
  </div>
</section>"""


__all__ = ["render_career_arc", "CAREER_ARC_CSS"]
