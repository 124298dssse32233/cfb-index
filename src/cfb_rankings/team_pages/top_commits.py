"""Top Commits module — surfaces the 3 highest-rated incoming recruits for
the most recent recruiting class. Sources from `player_recruiting_profiles`
populated by the CFBD preseason ingest.

Brief §11.5 ("recruiting roster, top 3"). Audit T9 fragment now resolvable.

Renders even if only one ranked recruit exists. Skips entirely when no
ranked recruits.

Public API:
    render_top_commits(db, profile, snapshot) -> str
    TOP_COMMITS_CSS                            -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot


TOP_COMMITS_CSS = """
/* Top Commits module */
.top-commits {
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-secondary, var(--accent-primary, #c9a24a));
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
}
.top-commits__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 10px;
}
.top-commits__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.top-commits__class-tag {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--fg-muted);
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
}
.top-commits__list {
  display: grid;
  gap: 10px;
}
.top-commits__row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px 14px;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.06));
}
.top-commits__stars {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 14px;
  letter-spacing: 0.04em;
  color: var(--accent-primary, #c9a24a);
  font-weight: 600;
  min-width: 56px;
}
.top-commits__name {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(15px, 0.9vw + 9px, 19px);
  letter-spacing: 0.02em;
  color: var(--fg-primary);
  line-height: 1.1;
}
.top-commits__meta {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  color: var(--fg-secondary);
  margin-top: 2px;
}
.top-commits__rank {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 11px;
  color: var(--fg-muted);
  text-align: right;
}
.top-commits__rank strong {
  color: var(--fg-primary);
  font-weight: 600;
}
@media (max-width: 540px) {
  .top-commits__row { grid-template-columns: auto minmax(0, 1fr); }
  .top-commits__rank { grid-column: 2 / 3; text-align: left; }
}
"""


def _fetch_top_commits(db, team_id: int, season_year: int, limit: int = 3) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select
            prp.season_year,
            p.full_name,
            prp.stars,
            prp.rating,
            prp.national_rank,
            prp.position,
            prp.city,
            prp.state_province
        from player_recruiting_profiles prp
        left join players p on p.player_id = prp.player_id
        where prp.team_id = :tid
          and prp.season_year = :s
          and prp.rating is not null
        order by prp.rating desc
        limit :limit
        """,
        {"tid": team_id, "s": season_year, "limit": limit},
    )
    return rows


def _latest_recruiting_year(db, team_id: int) -> int | None:
    rows = db.query_all(
        """
        select max(season_year) as y
          from player_recruiting_profiles
         where team_id = :tid
        """,
        {"tid": team_id},
    )
    if not rows:
        return None
    y = rows[0].get("y")
    return int(y) if y else None


def _star_glyphs(stars: int | None) -> str:
    n = int(stars or 0)
    return "★" * n + "☆" * (5 - n) if 0 < n <= 5 else "—"


def render_top_commits(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    if db is None or snapshot is None:
        return ""
    team_id = int(snapshot.team_id)
    yr = _latest_recruiting_year(db, team_id)
    if yr is None:
        return ""
    rows = _fetch_top_commits(db, team_id, yr, limit=3)
    if not rows:
        return ""

    list_html: list[str] = []
    for r in rows:
        name = r.get("full_name") or "Unnamed recruit"
        stars = r.get("stars")
        pos = r.get("position") or "—"
        city = r.get("city") or ""
        state = r.get("state_province") or ""
        loc = ", ".join(p for p in [city, state] if p)
        nat = r.get("national_rank")
        rating = r.get("rating") or 0
        try:
            rating_f = float(rating)
        except (TypeError, ValueError):
            rating_f = 0.0

        rank_chunk = (
            f"<strong>#{int(nat)}</strong> national" if nat is not None
            else f"rating <strong>{rating_f:.3f}</strong>"
        )

        list_html.append(
            f"""<div class="top-commits__row">
  <span class="top-commits__stars" aria-label="{escape(str(stars or 0))} star">{_star_glyphs(stars)}</span>
  <div>
    <div class="top-commits__name">{escape(name)}</div>
    <div class="top-commits__meta">{escape(pos)} · {escape(loc) if loc else 'No location'}</div>
  </div>
  <div class="top-commits__rank">{rank_chunk}</div>
</div>"""
        )

    return f"""
<section class="top-commits" aria-labelledby="top-commits-h"
         data-module="top-commits" data-state="ready" data-class-year="{yr}">
  <div class="top-commits__head">
    <p class="top-commits__eyebrow" id="top-commits-h">Recruiting Reload - Top {len(rows)} commits</p>
    <span class="top-commits__class-tag">{yr} class</span>
  </div>
  <div class="top-commits__list">
    {''.join(list_html)}
  </div>
</section>"""


__all__ = ["render_top_commits", "TOP_COMMITS_CSS"]
