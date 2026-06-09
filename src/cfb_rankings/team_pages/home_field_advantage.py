"""Home-Field Advantage chip — Brief §11.3.

Brief verbatim (§11.3):

    "Home-field advantage varies enormously by program and venue.
     Jordan-Hare Stadium plays differently than Kinnick. The Swamp
     on a night game is not the same as a Tuesday noon kickoff in
     Ames.

     Metrics:
       - Home EPA differential — home vs away beyond opponent quality
       - Night game effect — separate day/night EPA splits
       - Venue rating — capacity vs attendance, noise metric

     Rendered as one composite tile: 'Home-field advantage: Elite
     (94th percentile). Night games at Bryant-Denny have cost
     opponents an average of 0.06 EPA/play beyond the opponent
     quality model predicts.'"

Implementation: full EPA differential needs play-by-play we don't have
in the local DB. This module surfaces the cheapest honest proxy:
home/away win-share delta from the games table, optionally enriched
with venue.capacity when populated.

Public API:
    render_home_field_advantage(db, profile, snapshot) -> str
    HOME_FIELD_ADVANTAGE_CSS                            -> str
"""
from __future__ import annotations

from html import escape
from typing import Any

from .profile_loader import Profile
from .data import TeamSnapshot


HOME_FIELD_ADVANTAGE_CSS = """
/* Home-Field Advantage — Brief §11.3 */
.home-field {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px 18px;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, #c9a24a);
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
}
.home-field__main {
  display: grid;
  gap: 4px;
}
.home-field__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin: 0;
}
.home-field__band {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(22px, 1.6vw + 10px, 30px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--fg-primary);
  margin: 0;
}
.home-field__band--elite     { color: #2c8f5a; }
.home-field__band--strong    { color: var(--accent-primary, #c9a24a); }
.home-field__band--average   { color: var(--fg-secondary); }
.home-field__band--soft      { color: #c98c1a; }
.home-field__band--reversed  { color: #c95151; }

.home-field__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  font-style: italic;
  line-height: 1.4;
  color: var(--fg-secondary);
  margin: 0;
  max-width: 56ch;
}

.home-field__stats {
  display: grid;
  gap: 4px;
  align-self: center;
  text-align: right;
  min-width: 130px;
}
.home-field__stat-label {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.home-field__stat-value {
  font-family: var(--font-mono, monospace);
  font-size: 14px;
  font-weight: 600;
  color: var(--fg-primary);
}
@media (max-width: 640px) {
  .home-field { grid-template-columns: 1fr; }
  .home-field__stats { text-align: left; }
}
"""


# ---------------------------------------------------------------------------
# Data fetch
# ---------------------------------------------------------------------------

def _fetch_home_away_splits(db, team_id: int, since_year: int = 2018) -> dict[str, Any]:
    row = db.query_one(
        """
        select
          sum(case when g.home_team_id = :tid and g.home_points > g.away_points then 1 else 0 end) as home_wins,
          sum(case when g.home_team_id = :tid and g.home_points < g.away_points then 1 else 0 end) as home_losses,
          sum(case when g.away_team_id = :tid and g.away_points > g.home_points then 1 else 0 end) as away_wins,
          sum(case when g.away_team_id = :tid and g.away_points < g.home_points then 1 else 0 end) as away_losses,
          avg(case when g.home_team_id = :tid then g.home_points - g.away_points end) as home_margin_avg,
          avg(case when g.away_team_id = :tid then g.away_points - g.home_points end) as away_margin_avg
        from games g
        where (g.home_team_id = :tid or g.away_team_id = :tid)
          and g.status = 'Final'
          and g.home_points is not null and g.away_points is not null
          and g.season_year >= :yr
          and g.neutral_site = 0
        """,
        {"tid": team_id, "yr": since_year},
    )
    return dict(row) if row else {}


def _fetch_venue(db, team_id: int) -> dict[str, Any] | None:
    row = db.query_one(
        """
        select v.venue_name, v.capacity, v.city, v.state
        from teams t
        left join venues v on v.venue_id = t.venue_id
        where t.team_id = :tid and v.venue_id is not null
        """,
        {"tid": team_id},
    )
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Band classification
# ---------------------------------------------------------------------------

def _band(delta_pct: float, margin_delta: float | None) -> tuple[str, str]:
    """delta_pct = (home_winpct - away_winpct) * 100.
    margin_delta = home_margin_avg - away_margin_avg."""
    # Use margin delta when present to override pct in edge cases.
    if delta_pct >= 30 or (margin_delta is not None and margin_delta >= 14):
        return ("Elite", "elite")
    if delta_pct >= 18 or (margin_delta is not None and margin_delta >= 8):
        return ("Strong", "strong")
    if delta_pct >= 6 or (margin_delta is not None and margin_delta >= 3):
        return ("Above-Average", "strong")
    if delta_pct >= -3:
        return ("Average", "average")
    if delta_pct >= -15:
        return ("Soft", "soft")
    return ("Reversed (worse at home)", "reversed")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_home_field_advantage(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    """Render the Home-Field Advantage chip (Brief §11.3)."""
    if db is None or snapshot is None:
        return ""

    splits = _fetch_home_away_splits(db, int(snapshot.team_id))
    if not splits:
        return ""

    hw = int(splits.get("home_wins") or 0)
    hl = int(splits.get("home_losses") or 0)
    aw = int(splits.get("away_wins") or 0)
    al = int(splits.get("away_losses") or 0)
    total_games = hw + hl + aw + al
    if total_games < 6:
        # Not enough sample
        return ""

    home_n = max(1, hw + hl)
    away_n = max(1, aw + al)
    home_pct = hw / home_n
    away_pct = aw / away_n
    delta_pct = (home_pct - away_pct) * 100
    home_margin = splits.get("home_margin_avg")
    away_margin = splits.get("away_margin_avg")
    try:
        home_margin = float(home_margin) if home_margin is not None else None
        away_margin = float(away_margin) if away_margin is not None else None
    except (TypeError, ValueError):
        home_margin = away_margin = None
    margin_delta = (
        home_margin - away_margin
        if (home_margin is not None and away_margin is not None)
        else None
    )

    band_label, band_suffix = _band(delta_pct, margin_delta)
    venue = _fetch_venue(db, int(snapshot.team_id))

    # Story copy
    parts: list[str] = []
    parts.append(
        f"{int(home_pct * 100)}% home win rate vs {int(away_pct * 100)}% on the road"
    )
    if margin_delta is not None:
        if margin_delta > 0:
            parts.append(f"margin runs +{margin_delta:.1f} better at home")
        elif margin_delta < 0:
            parts.append(f"margin runs {margin_delta:.1f} weaker at home")
    if venue and venue.get("venue_name"):
        cap = venue.get("capacity")
        if cap:
            parts.append(f"{escape(venue['venue_name'])} seats {int(cap):,}")
        else:
            parts.append(f"{escape(venue['venue_name'])}")
    story = ". ".join(parts) + "."

    program = escape(profile.program_name)

    # Right-aligned compact stats
    stats_html = (
        '<div class="home-field__stats">'
        f'<span class="home-field__stat-label">Home</span>'
        f'<span class="home-field__stat-value">{hw}-{hl}</span>'
        f'<span class="home-field__stat-label">Away</span>'
        f'<span class="home-field__stat-value">{aw}-{al}</span>'
        '</div>'
    )

    return f"""
<section class="home-field" aria-labelledby="home-field-h"
         data-module="home-field-advantage" data-state="ready"
         data-band="{band_suffix}">
  <div class="home-field__main">
    <p class="home-field__eyebrow">Home-Field Advantage · {program} · 2018-present</p>
    <h2 id="home-field-h" class="home-field__band home-field__band--{band_suffix}">{escape(band_label)}</h2>
    <p class="home-field__story">{story}</p>
  </div>
  {stats_html}
</section>"""


__all__ = ["render_home_field_advantage", "HOME_FIELD_ADVANTAGE_CSS"]
