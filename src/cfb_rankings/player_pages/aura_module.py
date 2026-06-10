"""Aura player-page module — a Group Chat Noir "night band".

Self-contained, fully inline-styled (no stylesheet plumbing into the
reporting.py monolith) dark band showing this player's perception-vs-production
gap and aura tax. Injected via ``page_data["new_aura_html"]``.

Reads player_aura_weekly (written by `manage.py compute-aura`). Renders only
for QB/RB players above the mention floor with a real verdict; returns "" for
everyone else (the page simply skips the band).

Public API:
    render_player_aura(db, player_id) -> str
"""

from __future__ import annotations

from html import escape
from typing import Any

GROUND = "#101418"
SURFACE = "#1B2128"
CHALK = "#EDE6D6"
RECEIPT = "#B8B2A4"
HAIRLINE = "rgba(237,230,214,0.12)"
AURA = "#9D6BFF"
AURA_TEXT = "#B794FF"
PROD = "rgba(237,230,214,0.82)"
DISPLAY = "'Anton','Bebas Neue','Arial Narrow',sans-serif"
MONO = "'IBM Plex Mono',ui-monospace,'Courier New',monospace"
SANS = "Inter,system-ui,-apple-system,sans-serif"

_VERDICT = {
    "aura_tax": ("AURA TAX", AURA_TEXT, "more hype than the tape"),
    "underrated": ("UNDERRATED", "#8FD14F", "the tape outruns the hype"),
    "matched": ("HYPE = TAPE", CHALK, "the discourse is fair"),
}


def _bar(label: str, pctl: float, fill: str) -> str:
    return (
        f'<div style="margin:10px 0">'
        f'<div style="display:flex;justify-content:space-between;font-family:{MONO};'
        f'font-size:12px;color:{RECEIPT};margin-bottom:5px">'
        f'<span>{escape(label)}</span><span style="color:{CHALK}">{pctl:.0f}th pctl</span></div>'
        f'<div style="background:{SURFACE};border-radius:5px;height:16px;overflow:hidden">'
        f'<div style="height:100%;border-radius:5px;width:{max(2.0, pctl):.0f}%;background:{fill}"></div>'
        f'</div></div>'
    )


def render_player_aura(db, player_id: int) -> str:
    if db is None or not player_id:
        return ""
    try:
        row: dict[str, Any] | None = db.query_one(
            """
            select * from player_aura_weekly
            where player_id = :pid
            order by season_year desc, week desc
            limit 1
            """,
            {"pid": int(player_id)},
        )
    except Exception:
        return ""
    if not row or int(row.get("is_low_signal") or 0):
        return ""
    verdict_key = str(row.get("verdict") or "matched")
    if verdict_key not in _VERDICT:
        return ""

    word, color, gloss = _VERDICT[verdict_key]
    tax = float(row.get("aura_tax") or 0.0)
    perc = float(row.get("perception_pctl") or 0.0)
    prod = float(row.get("production_pctl") or 0.0)
    n = int(row.get("mention_count") or 0)
    cohort = escape(str(row.get("cohort_label") or ""))
    metric = escape(str(row.get("production_metric") or ""))

    return f"""
<div style="margin:24px 0;border-radius:16px;background:{GROUND};border:1px solid {HAIRLINE};overflow:hidden">
  <div style="padding:22px 24px">
    <div style="display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:12px">
      <span style="font-family:{MONO};font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:{RECEIPT}">Aura&#8482; · Him Watch</span>
      <a href="/hub/him-watch/" style="font-family:{MONO};font-size:11px;color:{RECEIPT};text-decoration:none;border-bottom:1px solid {HAIRLINE}">the full board &#8594;</a>
    </div>
    <div style="display:flex;align-items:baseline;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:6px">
      <span style="font-family:{DISPLAY};text-transform:uppercase;font-size:clamp(28px,5vw,46px);line-height:1;color:{color}">{escape(word)}</span>
      <span style="font-family:{DISPLAY};font-size:clamp(40px,7vw,60px);line-height:1;color:{color};font-variant-numeric:tabular-nums">{tax:+.0f}<span style="font-family:{MONO};font-size:13px;color:{RECEIPT};margin-left:8px">aura tax</span></span>
    </div>
    <div style="font-family:{SANS};font-size:14px;color:{CHALK};margin-bottom:14px">Fans rank this player in the <b style="color:{AURA_TEXT}">{perc:.0f}th</b> percentile of {escape(str(row.get('position') or ''))}s; the tape says <b>{prod:.0f}th</b> — {escape(gloss)}.</div>
    {_bar("✦ AURA — FAN PERCEPTION", perc, AURA)}
    {_bar("PRODUCTION — ON-FIELD", prod, PROD)}
    <div style="font-family:{MONO};font-size:12px;color:{RECEIPT};margin-top:12px">n={n:,} mentions · cohort: {cohort} · perception=conversation volume, production={metric}</div>
  </div>
</div>"""


__all__ = ["render_player_aura"]
