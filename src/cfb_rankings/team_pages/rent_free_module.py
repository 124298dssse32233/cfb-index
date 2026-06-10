"""Rent Free team-page module — a Group Chat Noir "night band".

Two-sided obsession readout for one program: which rival fanbases bring this
team up most (this team lives rent free in their heads), and which rivals this
team's own fans can't stop talking about. Perception data -> Aura Violet.

Reads team_week_rival_mentions via fetch_rent_free_for_team. Renders only when
there's signal on at least one side (the team-page graceful-degradation
contract); the /hub/rent-free/ board carries the cross-program leaderboard.

Public API:
    render_rent_free_module(db, profile, snapshot) -> str
    RENT_FREE_MODULE_CSS                            -> str
"""

from __future__ import annotations

from html import escape
from typing import Any

from cfb_rankings.fan_metrics.backometer_render import (
    CHALK,
    GROUND,
    HAIRLINE,
    RECEIPT,
    SURFACE,
    _DISPLAY_STACK,
    _MONO_STACK,
)
from cfb_rankings.fan_metrics.rent_free import fetch_rent_free_for_team

from .data import TeamSnapshot
from .profile_loader import Profile

AURA_TEXT = "#B794FF"


def _row(item: dict[str, Any]) -> str:
    return (
        f'<li><a href="/teams/{escape(str(item["slug"]))}.html">{escape(str(item["name"]))}</a>'
        f'<span class="rf-count">{int(item["count"])}</span></li>'
    )


def render_rent_free_module(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    if db is None or snapshot is None or not getattr(snapshot, "team_id", None):
        return ""
    try:
        data = fetch_rent_free_for_team(db, int(snapshot.team_id))
    except Exception:
        return ""
    if not data:
        return ""

    living = data["living_rent_free"][:4]   # fanbases obsessed with this team
    in_head = data["in_their_head"][:4]     # rivals this team obsesses over
    if not living and not in_head:
        return ""

    team_name = escape(getattr(snapshot, "canonical_name", None) or "This team")

    living_col = ""
    if living:
        living_col = (
            f'<div class="rf-col">'
            f'<div class="rf-col-head">{team_name} lives rent free in</div>'
            f'<ol class="rf-list">{"".join(_row(x) for x in living)}</ol></div>'
        )
    in_head_col = ""
    if in_head:
        in_head_col = (
            f'<div class="rf-col">'
            f'<div class="rf-col-head">In {team_name}’s head</div>'
            f'<ol class="rf-list">{"".join(_row(x) for x in in_head)}</ol></div>'
        )

    return f"""
<section class="rf-band" aria-label="Rent Free">
  <div class="rf-band__inner">
    <div class="rf-band__head">
      <span class="rf-eyebrow">Rent Free™</span>
      <a class="rf-link" href="/hub/rent-free/">the full obsession board →</a>
    </div>
    <div class="rf-cols">{living_col}{in_head_col}</div>
    <div class="rf-receipt">rival cross-mentions, this season · counts reflect collected conversation</div>
  </div>
</section>"""


RENT_FREE_MODULE_CSS = f"""
/* Rent Free night band (Group Chat Noir, perception/violet) */
.rf-band {{
  margin: clamp(20px, 3vw, 32px) 0; border-radius: 16px;
  background: {GROUND}; border: 1px solid {HAIRLINE}; overflow: hidden;
}}
.rf-band__inner {{ padding: clamp(18px, 2.6vw, 30px) clamp(18px, 2.8vw, 32px); }}
.rf-band__head {{
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 12px; flex-wrap: wrap; margin-bottom: 16px;
}}
.rf-eyebrow {{
  font-family: {_MONO_STACK}; font-size: 12px; font-weight: 500;
  letter-spacing: .14em; text-transform: uppercase; color: {RECEIPT};
}}
.rf-link {{
  font-family: {_MONO_STACK}; font-size: 11px; color: {RECEIPT};
  text-decoration: none; border-bottom: 1px solid {HAIRLINE};
}}
.rf-link:hover {{ color: {CHALK}; }}
.rf-cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
@media (max-width: 540px) {{ .rf-cols {{ grid-template-columns: 1fr; }} }}
.rf-col {{ background: {SURFACE}; border: 1px solid {HAIRLINE}; border-radius: 10px; padding: 14px 16px; }}
.rf-col-head {{
  font-family: {_DISPLAY_STACK}; text-transform: uppercase; color: {AURA_TEXT};
  font-size: clamp(15px, 2.4vw, 20px); letter-spacing: .02em; margin-bottom: 10px; line-height: 1.1;
}}
.rf-list {{ list-style: none; margin: 0; padding: 0; }}
.rf-list li {{
  display: flex; align-items: baseline; justify-content: space-between; gap: 10px;
  padding: 6px 0; border-top: 1px solid {HAIRLINE};
}}
.rf-list li:first-child {{ border-top: none; }}
.rf-list a {{ color: {CHALK}; text-decoration: none; font-weight: 600; font-size: 15px; }}
.rf-list a:hover {{ color: {AURA_TEXT}; }}
.rf-count {{
  font-family: {_MONO_STACK}; font-size: 14px; color: {RECEIPT};
  font-variant-numeric: tabular-nums;
}}
.rf-receipt {{
  font-family: {_MONO_STACK}; font-size: 12px; font-weight: 500; color: {RECEIPT}; margin-top: 14px;
}}
"""


__all__ = ["render_rent_free_module", "RENT_FREE_MODULE_CSS"]
