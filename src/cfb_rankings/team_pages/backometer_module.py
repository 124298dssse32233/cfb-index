"""Backometer team-page module — a Group Chat Noir "night band".

Embeds the team's fanbase-belief reading as a self-contained dark band
inside the otherwise-light team page (spec docs/design-system/40-noir-subbrand.md
§2: vibe modules render as full-bleed night bands). Reuses the chart geometry
and tokens from ``fan_metrics.backometer_render`` so the team-page monitor and
the hub/share-card monitor are one source of truth.

Graceful degradation: renders only when the team has a current PUBLISHABLE
verdict (latest week clears the n>=MIN_SAMPLE floor). A team with no qualifying
week yet (most programs in the deep offseason) renders nothing, matching the
"render only with signal" contract every other team-page module follows. The
hub carries the LOW SIGNAL transparency; the team page shows the band only when
there's a real verdict to show.

Public API:
    render_backometer_module(db, profile, snapshot) -> str
    BACKOMETER_MODULE_CSS                            -> str
"""

from __future__ import annotations

from html import escape
from typing import Any

from cfb_rankings.fan_metrics.backometer import MIN_SAMPLE, load_zone_labels
from cfb_rankings.fan_metrics.backometer_render import (
    CHALK,
    GROUND,
    HAIRLINE,
    RECEIPT,
    SURFACE,
    ZONE_COLORS,
    _monitor_svg_fragment,
)

from .data import TeamSnapshot
from .profile_loader import Profile

# Display stack: Anton if present, else Bebas Neue (already loaded site-wide
# per the design system), else a condensed system fallback. No new font dep.
_DISPLAY_STACK = "'Anton', 'Bebas Neue', 'Arial Narrow', sans-serif"
_MONO_STACK = "'IBM Plex Mono', ui-monospace, 'Courier New', monospace"


def _fetch_team_backometer(db, team_id: int) -> dict[str, Any] | None:
    """Return ``{latest, trail}`` for the team's most recent season, or None.

    Robust to the offseason season-key convention (data is keyed to the prior
    season_year): picks the max season_year present for this team, then the
    full week trail within it.
    """
    if not team_id:
        return None
    latest = db.query_one(
        """
        select *
        from backometer_weekly
        where team_id = :tid
        order by season_year desc, week desc
        limit 1
        """,
        {"tid": team_id},
    )
    if not latest:
        return None
    trail = db.query_all(
        """
        select week, score, zone, sample_size, is_low_signal, week_start_date
        from backometer_weekly
        where team_id = :tid and season_year = :season
        order by week
        """,
        {"tid": team_id, "season": int(latest["season_year"])},
    )
    return {"latest": latest, "trail": trail}


def render_backometer_module(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    if db is None or snapshot is None or not getattr(snapshot, "team_id", None):
        return ""
    try:
        bundle = _fetch_team_backometer(db, int(snapshot.team_id))
    except Exception:
        return ""
    if not bundle:
        return ""
    latest = bundle["latest"]
    # Only show the band when there is a current, publishable verdict.
    if int(latest.get("is_low_signal") or 0):
        return ""

    zone_labels = load_zone_labels()
    zone_id = str(latest.get("zone") or "uneasy")
    zone_color = ZONE_COLORS.get(zone_id, ZONE_COLORS["uneasy"])
    zone_word = zone_labels.get(zone_id, zone_id.upper())
    score = float(latest.get("score") or 0.0)
    n = int(latest.get("sample_size") or 0)
    sources = int(latest.get("source_count") or 0)
    delta = latest.get("delta_wow")

    # SVG monitor in a 1040x300 viewBox (matches the share-card geometry band).
    monitor = _monitor_svg_fragment(
        bundle["trail"], x0=70, x1=970, y_top=40, y_bottom=250,
        zone_color=zone_color, clip_prefix="bm-team",
    )
    svg = (
        f'<svg viewBox="0 0 1040 300" role="img" '
        f'aria-label="The Backometer: this fanbase is {escape(zone_word)} at {score:.0f}">'
        f'<text x="70" y="28" fill="#2EE07C" font-size="13" '
        f'font-family="{_MONO_STACK}">SO BACK ↑</text>'
        f'<text x="70" y="282" fill="#FF4E42" font-size="13" '
        f'font-family="{_MONO_STACK}">IT\'S SO OVER ↓</text>'
        f'{monitor}</svg>'
    )

    delta_html = ""
    if delta is not None:
        arrow = "▲" if float(delta) >= 0 else "▼"
        d_color = "#2EE07C" if float(delta) >= 0 else "#FF4E42"
        delta_html = (
            f'<span class="bm-delta" style="color:{d_color}">'
            f'{arrow} {abs(float(delta)):.1f} <span class="bm-delta-unit">wk/wk</span></span>'
        )

    source_word = "source" if sources == 1 else "sources"
    receipt = (
        f"n={n:,} fan conversations · {sources} {source_word} · "
        f"sarcasm-adjusted · floor n≥{MIN_SAMPLE}"
    )

    return f"""
<section class="bm-band" style="--bm-zone:{zone_color}" aria-label="The Backometer">
  <div class="bm-band__inner">
    <div class="bm-band__head">
      <span class="bm-eyebrow">The Backometer™</span>
      <a class="bm-link" href="/hub/backometer/">how every fanbase reads →</a>
    </div>
    <div class="bm-verdict">
      <span class="bm-zone">{escape(zone_word)}</span>
      <span class="bm-score">{score:.0f}{delta_html}</span>
    </div>
    <div class="bm-chart">{svg}</div>
    <div class="bm-receipt">{escape(receipt)}</div>
  </div>
</section>"""


BACKOMETER_MODULE_CSS = f"""
/* Backometer night band (Group Chat Noir, embedded in the light team page) */
.bm-band {{
  margin: clamp(20px, 3vw, 32px) 0;
  border-radius: 16px;
  background: {GROUND};
  border: 1px solid {HAIRLINE};
  overflow: hidden;
}}
.bm-band__inner {{ padding: clamp(18px, 2.6vw, 30px) clamp(18px, 2.8vw, 32px); }}
.bm-band__head {{
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 12px; flex-wrap: wrap; margin-bottom: 14px;
}}
.bm-eyebrow {{
  font-family: {_MONO_STACK}; font-size: 12px; font-weight: 500;
  letter-spacing: .14em; text-transform: uppercase; color: {RECEIPT};
}}
.bm-link {{
  font-family: {_MONO_STACK}; font-size: 11px; color: {RECEIPT};
  text-decoration: none; border-bottom: 1px solid {HAIRLINE};
}}
.bm-link:hover {{ color: {CHALK}; }}
.bm-verdict {{
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 16px; flex-wrap: wrap; margin-bottom: 10px;
}}
.bm-zone {{
  font-family: {_DISPLAY_STACK}; text-transform: uppercase; line-height: 1;
  font-size: clamp(30px, 6vw, 52px); letter-spacing: .02em; color: var(--bm-zone);
}}
.bm-score {{
  font-family: {_DISPLAY_STACK}; line-height: 1; color: var(--bm-zone);
  font-size: clamp(40px, 8vw, 68px); font-variant-numeric: tabular-nums;
  display: inline-flex; align-items: baseline; gap: 14px;
}}
.bm-delta {{
  font-family: {_MONO_STACK}; font-size: 15px; font-weight: 500;
}}
.bm-delta-unit {{ color: {RECEIPT}; font-size: 12px; }}
.bm-chart {{
  background: {SURFACE}; border: 1px solid {HAIRLINE}; border-radius: 10px;
  padding: 8px 10px; margin: 4px 0 14px;
}}
.bm-chart svg {{ display: block; width: 100%; height: auto; }}
.bm-receipt {{
  font-family: {_MONO_STACK}; font-size: 12px; font-weight: 500; color: {RECEIPT};
}}
@media (max-width: 520px) {{
  .bm-chart {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
  .bm-chart svg {{ min-width: 520px; }}
}}
"""


__all__ = ["render_backometer_module", "BACKOMETER_MODULE_CSS"]
