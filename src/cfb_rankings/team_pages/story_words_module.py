"""Season Vocabulary strip — Language Layer Wave 3 (A6).

Shows the most distinctive vocabulary terms for each season in a team's history,
as a stacked era band strip. No LLM chapter naming — just the statistically
strongest terms + multipliers, newest season first.

Reads team_discourse_era_terms (written by compute-team-eras). The within-team
cross-season contrast means Michigan 2023's top terms are harbaugh/rose/bama
(what that season's vocabulary had vs their OWN other seasons) and 2024's are
orji/warren/mullings — pure corpus statistics revealing the era narrative.

Confidence floor: >=3 era terms for the most recent season AND >= 2 distinct
seasons with data (the within-team contrast requires at least 2 seasons).
Below floor -> returns "" (graceful degradation, no layout hole).

Public API:
    render_story_words(db, profile, snapshot) -> str
    STORY_WORDS_CSS                           -> str
"""

from __future__ import annotations
from html import escape
from typing import Any
from .data import TeamSnapshot
from .profile_loader import Profile

_MIN_TERMS_FOR_SHOW = 3
_MIN_SEASONS = 2
_TERMS_PER_ERA = 5   # terms shown per season band


def _field(row: Any, key: str) -> Any:
    try:
        return row[key]
    except (TypeError, KeyError, IndexError):
        return None


def render_story_words(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    # team_id lives on profile; snapshot is used for context only
    team_id_raw = getattr(profile, "team_id", None) or getattr(snapshot, "team_id", None)
    if db is None or not team_id_raw:
        return ""
    team_id = int(team_id_raw)
    try:
        rows = db.query_all(
            "SELECT season_year, term, term_rank, rate_ratio, log2_ratio, z_score, magnitude_band "
            "FROM team_discourse_era_terms "
            "WHERE team_id = :team_id "
            "ORDER BY season_year DESC, term_rank ASC",
            {"team_id": team_id},
        )
    except Exception:
        return ""

    if not rows:
        return ""

    # Group by season
    from collections import defaultdict
    by_season: dict[int, list] = defaultdict(list)
    for r in rows:
        s = _field(r, "season_year")
        if s is not None:
            by_season[int(s)].append(r)

    if len(by_season) < _MIN_SEASONS:
        return ""

    # Most recent season must have enough terms
    most_recent = max(by_season)
    if len(by_season[most_recent]) < _MIN_TERMS_FOR_SHOW:
        return ""

    # Build era band rows, newest season first
    bands_html = ""
    for season in sorted(by_season, reverse=True):
        terms = by_season[season][:_TERMS_PER_ERA]
        if not terms:
            continue
        # Map log2_ratio to font weight 300-900
        ratios = [float(_field(t, "log2_ratio") or 0.0) for t in terms]
        lo, hi = min(ratios), max(ratios)
        span = (hi - lo) or 1.0

        chips = ""
        for term, l2 in zip(terms, ratios):
            frac = (l2 - lo) / span
            weight = int(round(300 + frac * 600))
            word = escape(str(_field(term, "term") or ""))
            ratio = float(_field(term, "rate_ratio") or 0.0)
            band = str(_field(term, "magnitude_band") or "mild")
            cls = f"story-words__chip story-words__chip--{band}"
            chips += (
                f'<span class="{cls}" style="font-weight:{weight}">'
                f'{word}<span class="story-words__chip-ratio">×{ratio:.1f}</span>'
                f'</span>'
            )
        bands_html += (
            f'<div class="story-words__era">'
            f'<span class="story-words__year">{season}</span>'
            f'<div class="story-words__chips">{chips}</div>'
            f'</div>'
        )

    if not bands_html:
        return ""

    return f"""
<section class="story-words" aria-label="Season Vocabulary">
  <div class="story-words__head">
    <span class="story-words__eyebrow">Season Vocabulary</span>
    <span class="story-words__subhead">how the conversation changed, year to year</span>
  </div>
  {bands_html}
</section>"""


STORY_WORDS_CSS = """
/* Season Vocabulary strip — Language Layer Wave 3 */
.story-words {
  display: grid;
  gap: clamp(8px, 1.2vw, 12px);
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255,255,255,0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
}
.story-words__head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}
.story-words__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--accent-primary, #c9a24a);
}
.story-words__subhead {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.story-words__era {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
  padding: 6px 0;
  border-bottom: 1px solid var(--stroke-subtle, rgba(255,255,255,0.06));
}
.story-words__era:last-child { border-bottom: none; }
.story-words__year {
  font-family: var(--font-display, 'Bebas Neue', Impact, sans-serif);
  font-size: clamp(22px, 3.5vw, 32px);
  line-height: 1;
  color: var(--fg-muted);
  min-width: 60px;
  flex-shrink: 0;
}
.story-words__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding-top: 4px;
}
.story-words__chip {
  font-family: 'Hepta Slab', var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: clamp(13px, 1.8vw, 16px);
  line-height: 1;
  color: var(--fg-primary);
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  overflow-wrap: anywhere;
}
.story-words__chip--signature {
  border-color: color-mix(in srgb, var(--accent-primary, #c9a24a) 40%, transparent);
  background: color-mix(in srgb, var(--accent-primary, #c9a24a) 8%, transparent);
}
.story-words__chip-ratio {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 10px;
  font-weight: 500;
  color: var(--accent-primary, #c9a24a);
  letter-spacing: 0.06em;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
"""

__all__ = ["render_story_words", "STORY_WORDS_CSS"]
