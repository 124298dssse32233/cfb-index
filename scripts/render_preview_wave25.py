"""Wave 25 preview: render Status Strip + Where-Ended-Up + 2026 Outlook
for 8 marquee players covering every archetype.

Opens via file:// at output/site/players/_preview-wave25.html
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from cfb_rankings.db import Database
from cfb_rankings.player_pages import (
    render_status_strip, STATUS_STRIP_CSS,
    render_where_ended_up, WHERE_ENDED_UP_CSS,
    render_outlook_2026, OUTLOOK_2026_CSS,
    PLAYER_PAGE_TOKENS_CSS,
    season_context_label, page_title_suffix,
    fetch_status_row,
)
from datetime import date

PLAYERS = [
    (13074, "Arch Manning",         "Type A — Returning starter (inferred from 2025 roster)"),
    (3830,  "Jeremiah Smith",       "Type A — Returning WR + Heisman watch potential"),
    (11807, "Maddux Madsen",        "Type A — Returning starter, Group of 5"),
    (12763, "Fernando Mendoza",     "Type B — #1 overall pick, 2026 Draft"),
    (9020,  "Drew Allar",           "Type B — 2026 Draft, Steelers Rd 3"),
    (13272, "Carson Beck",          "Type B — 2026 Draft after Miami transfer"),
    (1015,  "Cam Ward",             "Type B — 2025 Draft (entering 2nd NFL season)"),
    (120,   "Dillon Gabriel",       "Type B — 2025 Draft (entering 2nd NFL season)"),
    (11804, "Ashton Jeanty",        "Type B — 2025 Draft (entering 2nd NFL season)"),
    (6623,  "Tre Stewart",          "Type D — Career complete (no 2025 roster)"),
]


def render_player_card(db, pid: int, name: str, archetype: str) -> str:
    status_row = fetch_status_row(db, pid)
    if not status_row:
        return f"<section><h3>{name}</h3><p>(no status row)</p></section>"

    status_code = status_row.get("status_code") or "—"

    strip_html = render_status_strip(db, pid)
    where_html = render_where_ended_up(db, pid)
    outlook_html = render_outlook_2026(db, pid)

    label = season_context_label(
        status_code,
        last_team_name=status_row.get("last_college_team_name"),
        last_season_year=status_row.get("last_college_year"),
        current_date=date(2026, 5, 27),
    )
    title_suffix = page_title_suffix(
        status_code,
        current_team_name=status_row.get("last_college_team_name"),
        position=status_row.get("position_2026") or status_row.get("master_position"),
        nfl_team=status_row.get("nfl_team"),
        last_team_name=status_row.get("last_college_team_name"),
        current_date=date(2026, 5, 27),
    )

    return f"""
    <article class="player-card">
        <header class="player-card__head">
            <h2 class="player-card__name">{name}</h2>
            <p class="player-card__archetype">{archetype}</p>
            <p class="player-card__meta">
                Status: <code>{status_code}</code> ·
                Page title: <em>{name} | {title_suffix}</em> ·
                Section label: <em>{label}</em>
            </p>
        </header>
        {strip_html}
        {where_html}
        {outlook_html}
    </article>
    """


def main() -> None:
    db = Database(str(ROOT / "cfb_rankings.db"))
    cards = []
    for pid, name, archetype in PLAYERS:
        cards.append(render_player_card(db, pid, name, archetype))

    css_bundle = (
        PLAYER_PAGE_TOKENS_CSS + STATUS_STRIP_CSS + WHERE_ENDED_UP_CSS + OUTLOOK_2026_CSS
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Wave 25 Preview · Player Page Offseason Posture</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{
  --bg: #0f1014;
  --fg: #f4f4f5;
  --accent: #d1a23a;
  --stroke-subtle: rgba(255,255,255,0.08);
  --text-bright: rgba(255,255,255,0.94);
  --text-soft: rgba(255,255,255,0.80);
  --text-quiet: rgba(255,255,255,0.55);
  --accolade-gold-base: #d1a23a;
  --accolade-gold-highlight: #e4c76b;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
}}
* {{ box-sizing: border-box; }}
body {{
  background: var(--bg);
  color: var(--fg);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  margin: 0; padding: 24px 20px;
  line-height: 1.5;
}}
.container {{ max-width: 1100px; margin: 0 auto; }}
.preview-banner {{
  background: linear-gradient(135deg,#1a1d24 0%,#0f1014 100%);
  border: 1px solid #2a2d34;
  border-radius: 12px;
  padding: 18px 22px;
  margin-bottom: 24px;
}}
.preview-banner h1 {{ margin: 0 0 6px 0; font-size: 1.4rem; }}
.preview-banner p {{ margin: 0; color: var(--text-soft); font-size: 0.88rem; }}
.player-card {{
  margin-bottom: 36px;
  padding: 18px 20px;
  background: rgba(255,255,255,0.012);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 14px;
}}
.player-card__name {{
  margin: 0;
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--text-bright);
}}
.player-card__archetype {{
  margin: 4px 0 8px 0;
  font-size: 0.84rem;
  color: var(--accolade-gold-base);
  font-weight: 500;
}}
.player-card__meta {{
  margin: 0 0 14px 0;
  font-size: 0.76rem;
  color: var(--text-quiet);
}}
.player-card__meta code {{
  background: rgba(255,255,255,0.06);
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 0.74rem;
}}
.player-card__meta em {{
  font-style: italic;
  color: var(--text-soft);
}}
{css_bundle}
</style>
</head>
<body>
<div class="container">
    <div class="preview-banner">
        <h1>Wave 25 Preview · Player Page 2026 Offseason Posture</h1>
        <p>10 marquee players covering all 11 status codes. Status Strip + Where-Ended-Up + 2026 Outlook all rendered with real DB data. As of 2026-05-27.</p>
    </div>
    {"".join(cards)}
</div>
</body>
</html>"""

    out = ROOT / "output" / "site" / "players" / "_preview-wave25.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Wrote: {out}")
    print(f"Size:  {out.stat().st_size:,} bytes")
    print(f"Open:  file:///{out.as_posix()}")


if __name__ == "__main__":
    main()
