"""NIL + Draft card — Brief §4.12 / Wave 19.

Small, bounded card showing recruiting pedigree (when applicable) and
NFL draft outcome (when applicable). NIL valuation is currently a
"coming soon" — no live On3/247 feed ingested yet.

For a current undergrad: shows star rating + composite + national rank.
For a drafted alumnus: shows draft year + round + pick + NFL team.
Both at once when both apply (e.g. a Senior who has a recruiting
profile and is now eligible for the upcoming draft).

Public API:
    render_nil_draft(db, player_id) -> str
    NIL_DRAFT_CSS                   -> str
"""
from __future__ import annotations

from html import escape
from typing import Any


NIL_DRAFT_CSS = """
/* NIL + Draft card */
.nil-draft {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(12px, 1.6vw, 18px) clamp(14px, 1.8vw, 22px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.nil-draft__head {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 12px; margin-bottom: 8px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 6px;
}
.nil-draft__eyebrow {
  font-size: 0.72rem; letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55)); margin: 0;
}
.nil-draft__title {
  font-size: 1.0rem; font-weight: 600; margin: 0;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.nil-draft__body {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}
.nil-draft__tile {
  background: rgba(255,255,255,0.018);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 9px 12px;
}
.nil-draft__tile-label {
  font-size: 0.66rem; letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  margin: 0 0 2px 0;
}
.nil-draft__tile-value {
  font-size: 1.05rem; font-weight: 600;
  color: var(--text-bright, rgba(255,255,255,0.92));
  margin: 0;
}
.nil-draft__tile-sub {
  font-size: 0.72rem; color: var(--text-quiet, rgba(255,255,255,0.55));
}
.nil-draft__tile--gold {
  border-color: var(--accolade-gold-base, #d1a23a);
  background: rgba(209, 162, 58, 0.06);
}
.nil-draft__tile--gold .nil-draft__tile-value {
  color: var(--accolade-gold-base, #d1a23a);
}
.nil-draft__stars {
  display: inline-flex; gap: 2px; color: var(--accolade-gold-base, #d1a23a);
  font-size: 0.90rem; letter-spacing: 1px;
}
.nil-draft__note {
  margin-top: 8px;
  font-size: 0.66rem; color: var(--text-quiet, rgba(255,255,255,0.50));
  font-style: italic;
}
"""


def _star_chars(n: int) -> str:
    n = max(0, min(5, int(n or 0)))
    return "★" * n + "☆" * (5 - n)


def _fetch_recruit(db, player_id: int) -> dict[str, Any] | None:
    rows = db.query_all(
        """
        select stars, rating, national_rank, season_year, committed_team, position
          from player_recruiting_profiles
         where player_id = :pid
         order by season_year desc
         limit 1
        """,
        {"pid": player_id},
    )
    if not rows:
        return None
    return dict(rows[0])


def _fetch_draft(db, player_id: int) -> dict[str, Any] | None:
    rows = db.query_all(
        """
        select draft_year, round, pick, overall, nfl_team, position
          from player_nfl_draft
         where player_id = :pid
         order by draft_year desc
         limit 1
        """,
        {"pid": player_id},
    )
    if not rows:
        return None
    return dict(rows[0])


def render_nil_draft(db, player_id: int | None) -> str:
    if db is None or player_id is None:
        return ""
    recruit = _fetch_recruit(db, int(player_id))
    draft   = _fetch_draft(db, int(player_id))
    if not recruit and not draft:
        return ""  # Don't render empty card; cleaner than placeholder

    tiles: list[str] = []
    if recruit:
        stars = recruit.get("stars") or 0
        rating = recruit.get("rating")
        natl = recruit.get("national_rank")
        committed = recruit.get("committed_team") or "—"
        tiles.append(
            '<div class="nil-draft__tile nil-draft__tile--gold">'
            '<p class="nil-draft__tile-label">Recruit stars</p>'
            f'<p class="nil-draft__tile-value">'
            f'<span class="nil-draft__stars">{escape(_star_chars(stars))}</span>'
            '</p>'
            f'<p class="nil-draft__tile-sub">to {escape(str(committed))}</p>'
            '</div>'
        )
        if rating is not None:
            tiles.append(
                '<div class="nil-draft__tile">'
                '<p class="nil-draft__tile-label">Composite</p>'
                f'<p class="nil-draft__tile-value">{float(rating):.4f}</p>'
                f'<p class="nil-draft__tile-sub">'
                + (f"#{int(natl)} national" if natl else "")
                + '</p>'
                '</div>'
            )
    if draft:
        rd = draft.get("round")
        pk = draft.get("pick")
        ov = draft.get("overall")
        team = draft.get("nfl_team") or "—"
        year = draft.get("draft_year")
        tiles.append(
            '<div class="nil-draft__tile nil-draft__tile--gold">'
            '<p class="nil-draft__tile-label">NFL Draft</p>'
            f'<p class="nil-draft__tile-value">{year} &middot; Rd {rd}, Pick {pk}</p>'
            f'<p class="nil-draft__tile-sub">#{ov} overall &middot; {escape(str(team))}</p>'
            '</div>'
        )

    if not tiles:
        return ""

    return (
        '<section class="nil-draft" data-module="nil-draft" data-state="ready">'
        '<header class="nil-draft__head">'
        '<div>'
        '<p class="nil-draft__eyebrow">Recruiting &middot; NFL Draft</p>'
        '<p class="nil-draft__title">Pre-college pedigree and pro outcome</p>'
        '</div>'
        '</header>'
        f'<div class="nil-draft__body">{"".join(tiles)}</div>'
        '<p class="nil-draft__note">NIL valuation arrives when On3 / 247 feed is wired.</p>'
        '</section>'
    )
