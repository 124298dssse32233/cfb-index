"""Delusion Premium team-page module — a Group Chat Noir "night band".

Fan belief (violet) vs betting-market title odds (blue) for one contender,
with the delusion verdict + rank. Renders only for teams that have a live
championship market AND a belief score (the ~10 contenders); everyone else
skips it. Reads delusion_premium_weekly.

Public API:
    render_delusion_module(db, profile, snapshot) -> str
    DELUSION_MODULE_CSS                            -> str
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

from .data import TeamSnapshot
from .profile_loader import Profile

BELIEF = "#9D6BFF"
BELIEF_TEXT = "#B794FF"
MARKET = "#3D91FF"

_VERDICT = {
    "delusional": ("DELUSIONAL", BELIEF_TEXT),
    "sharp": ("SHARP", MARKET),
    "bullish": ("BULLISH", CHALK),
}


def render_delusion_module(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    if db is None or snapshot is None or not getattr(snapshot, "team_id", None):
        return ""
    try:
        row: dict[str, Any] | None = db.query_one(
            """
            select * from delusion_premium_weekly
            where team_id = :tid order by season_year desc, week desc limit 1
            """,
            {"tid": int(snapshot.team_id)},
        )
    except Exception:
        return ""
    if not row:
        return ""

    vk = str(row.get("verdict") or "bullish")
    word, color = _VERDICT.get(vk, _VERDICT["bullish"])
    belief = float(row["belief_score"])
    market = float(row["market_pct"])
    index = float(row["delusion_index"])
    rank = int(row.get("rank") or 0)
    cohort = int(row.get("cohort_size") or 0)
    low = " · belief low-signal" if int(row.get("belief_low_signal") or 0) else ""

    return f"""
<section class="dp-band" style="--dp-accent:{color}" aria-label="Delusion Premium">
  <div class="dp-band__inner">
    <div class="dp-band__head">
      <span class="dp-eyebrow">Delusion Premium™</span>
      <a class="dp-link" href="/hub/delusion/">most delusional fanbases →</a>
    </div>
    <div class="dp-verdict">
      <span class="dp-word">{escape(word)}</span>
      <span class="dp-rank">#{rank}<span class="dp-rank-unit"> of {cohort}</span></span>
    </div>
    <div class="dp-rows">
      <div class="dp-row">
        <span class="dp-label" style="color:{BELIEF_TEXT}">✦ Fans believe</span>
        <span class="dp-track"><i style="width:{max(2.0, belief):.0f}%;background:{BELIEF}"></i></span>
        <span class="dp-val">{belief:.0f}</span>
      </div>
      <div class="dp-row">
        <span class="dp-label" style="color:{MARKET}">▪ Market gives</span>
        <span class="dp-track"><i style="width:{max(2.0, market):.0f}%;background:{MARKET}"></i></span>
        <span class="dp-val">{market:.0f}%</span>
      </div>
    </div>
    <div class="dp-receipt">belief = Backometer{escape(low)} · market = Polymarket implied 2027 title odds · index {index:+.0f}</div>
  </div>
</section>"""


DELUSION_MODULE_CSS = f"""
/* Delusion Premium night band (Group Chat Noir) */
.dp-band {{ margin: clamp(20px,3vw,32px) 0; border-radius: 16px; background: {GROUND};
  border: 1px solid {HAIRLINE}; overflow: hidden; }}
.dp-band__inner {{ padding: clamp(18px,2.6vw,30px) clamp(18px,2.8vw,32px); }}
.dp-band__head {{ display: flex; align-items: baseline; justify-content: space-between;
  gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }}
.dp-eyebrow {{ font-family: {_MONO_STACK}; font-size: 12px; font-weight: 500;
  letter-spacing: .14em; text-transform: uppercase; color: {RECEIPT}; }}
.dp-link {{ font-family: {_MONO_STACK}; font-size: 11px; color: {RECEIPT};
  text-decoration: none; border-bottom: 1px solid {HAIRLINE}; }}
.dp-link:hover {{ color: {CHALK}; }}
.dp-verdict {{ display: flex; align-items: baseline; justify-content: space-between;
  gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }}
.dp-word {{ font-family: {_DISPLAY_STACK}; text-transform: uppercase; line-height: 1;
  font-size: clamp(28px,5vw,46px); letter-spacing: .02em; color: var(--dp-accent); }}
.dp-rank {{ font-family: {_DISPLAY_STACK}; font-size: clamp(30px,5vw,46px); line-height: 1;
  color: var(--dp-accent); font-variant-numeric: tabular-nums; }}
.dp-rank-unit {{ font-family: {_MONO_STACK}; font-size: 13px; color: {RECEIPT}; }}
.dp-rows {{ display: flex; flex-direction: column; gap: 10px; }}
.dp-row {{ display: grid; grid-template-columns: 130px 1fr 52px; align-items: center; gap: 12px; }}
.dp-label {{ font-family: {_MONO_STACK}; font-size: 12px; }}
.dp-track {{ background: {SURFACE}; border-radius: 5px; height: 16px; overflow: hidden; }}
.dp-track > i {{ display: block; height: 100%; border-radius: 5px; }}
.dp-val {{ font-family: {_MONO_STACK}; font-size: 15px; color: {CHALK}; text-align: right;
  font-variant-numeric: tabular-nums; }}
.dp-receipt {{ font-family: {_MONO_STACK}; font-size: 12px; color: {RECEIPT}; margin-top: 14px; }}
@media (max-width: 520px) {{ .dp-row {{ grid-template-columns: 110px 1fr 46px; }} }}
"""


__all__ = ["render_delusion_module", "DELUSION_MODULE_CSS"]
