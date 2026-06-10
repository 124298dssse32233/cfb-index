"""Render JUST the redesigned rankings board (standalone, fast) to a preview path,
so we can screenshot the fixed board without waiting for the full 80-min build.
Writes output/site/_preview_rankings/index.html (same ../assets/ depth as /rankings/).
"""
import os
from pathlib import Path

# load .env into the environment so AppConfig.from_env() has what it needs
for _line in open(".env", encoding="utf-8"):
    _line = _line.strip()
    if _line and not _line.startswith("#") and "=" in _line:
        k, v = _line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from cfb_rankings.config import AppConfig
from cfb_rankings.db import Database
from cfb_rankings.reporting import (
    fetch_latest_rankings,
    _latest_local_week,
    _build_team_mood_index,
    render_rankings_page_html,
)

config = AppConfig.from_env()
db = Database(config.database_url)

summary, rankings = fetch_latest_rankings(db, limit=1000)
llw = _latest_local_week(db, int(summary["season_year"]))
mood = _build_team_mood_index(db)
html = render_rankings_page_html(summary, rankings, llw, None, None, mood)

out = Path("output/site/_preview_rankings/index.html")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html, encoding="utf-8")
print(f"wrote {out}  ({len(html)} bytes)  mood_teams={len(mood)}  rankings={len(rankings)}")

# Lightweight version (top 30 only) so the screenshot tool can render it for a
# remote user. Same chips/logos/layout, just far fewer DOM nodes.
html_lite = render_rankings_page_html(summary, rankings[:30], llw, None, None, mood)
out_lite = Path("output/site/_preview_lite/index.html")
out_lite.parent.mkdir(parents=True, exist_ok=True)
out_lite.write_text(html_lite, encoding="utf-8")
print(f"wrote {out_lite}  ({len(html_lite)} bytes)  rows=30")
