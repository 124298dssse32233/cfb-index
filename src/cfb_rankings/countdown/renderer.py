"""Days-to-Kickoff countdown — S1 surface.

Writes two artifacts under output_root:
  - /kickoff/index.html — standalone landing page
  - /assets/countdown.json — small JSON for sitewide strip consumption

Both reference cfb_calendar for the canonical date/phase/kickoff logic.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import date
from html import escape
from pathlib import Path

from cfb_rankings.common.cfb_calendar import (
    cfb_week_label,
    days_to_kickoff,
    human_phase_label,
    is_in_season,
    is_offseason,
    kickoff_date,
)

log = logging.getLogger(__name__)


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
{head_chrome}
<link rel="stylesheet" href="/assets/css/site.css">
<style>
  .countdown-hero {{ text-align: center; padding: 64px 24px; }}
  .countdown-number {{ font-size: clamp(96px, 18vw, 240px); font-weight: 900;
                        font-variant-numeric: tabular-nums; line-height: 1;
                        color: var(--accent, #c9a24a); margin: 0; }}
  .countdown-unit {{ font-size: 24px; font-weight: 700; letter-spacing: 2px;
                      text-transform: uppercase; color: var(--muted-foreground, #555);
                      margin-top: 8px; }}
  .countdown-phase {{ font-size: 18px; margin-top: 16px;
                       color: var(--muted-foreground, #666); }}
  .countdown-detail {{ font-size: 16px; margin-top: 32px; max-width: 56ch;
                        margin-left: auto; margin-right: auto;
                        color: var(--foreground, #222); }}
</style>
</head>
<body class="countdown-page">
<main class="site-shell" id="main-content">
  <section class="countdown-hero">
    <p class="countdown-number">{days}</p>
    <p class="countdown-unit">{unit}</p>
    <p class="countdown-phase">{phase_label}</p>
    <p class="countdown-detail">{detail}</p>
  </section>
</main>
</body>
</html>
"""


def render_countdown(
    db: sqlite3.Connection | None = None,
    *,
    today: date | None = None,
    output_dir: str = "output/site",
) -> dict[str, int | str]:
    """Render /kickoff/index.html + /assets/countdown.json.

    Args:
        db: Optional DB connection (for games-table kickoff lookup; falls
            back to KEY_EVENTS_<season> constants if missing).
        today: Override anchor date (for tests / pinned runs).
        output_dir: Root output directory.

    Returns:
        Dict with counters + paths written:
          {'days_to_kickoff', 'phase_label', 'files_written', 'json_path', 'html_path'}
    """
    today = today or date.today()
    output_root = Path(output_dir)

    if is_in_season(today, db):
        days = 0
        unit = "GAMES IN PROGRESS"
        phase = human_phase_label(today, db)
        detail = f"It's {phase}. Watch the games."
        title = f"{phase} — CFB Index"
        season_year_for_desc = today.year
    else:
        days = days_to_kickoff(today, db=db)
        unit = "DAY" if days == 1 else "DAYS"
        phase = human_phase_label(today, db)
        ko_date = kickoff_date(today.year if today.month >= 1 else today.year - 1, db)
        if ko_date <= today:
            # already past this season's kickoff — roll forward
            ko_date = kickoff_date(today.year + 1, db)
        detail = (
            f"It's {phase}. Kickoff Saturday is "
            f"{ko_date.strftime('%B')} {ko_date.day}, {ko_date.year}."
        )
        title = f"{days} {unit} to Kickoff — CFB Index"
        season_year_for_desc = ko_date.year

    description = (
        f"{days} days until the {season_year_for_desc} college football season kicks off. "
        "Phase, countdown, and what's happening in the meantime."
    )

    from cfb_rankings.common.head_chrome import render_head_chrome
    head_chrome = render_head_chrome(
        page_path="/kickoff/",
        title=title,
        description=description,
        og_type="article",
    )
    html = _HTML_TEMPLATE.format(
        title=escape(title),
        description=escape(description),
        days=days,
        unit=escape(unit),
        phase_label=escape(phase),
        detail=escape(detail),
        head_chrome=head_chrome,
    )

    kickoff_dir = output_root / "kickoff"
    kickoff_dir.mkdir(parents=True, exist_ok=True)
    html_path = kickoff_dir / "index.html"
    html_path.write_text(html, encoding="utf-8")

    assets_dir = output_root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    json_path = assets_dir / "countdown.json"
    json_payload = {
        "today_iso": today.isoformat(),
        "days_to_kickoff": days,
        "in_season": not is_offseason(today, db),
        "phase_label": phase,
        "week_label": cfb_week_label(today, db),
    }
    json_path.write_text(
        json.dumps(json_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    log.info(
        "render_countdown: days=%d phase=%r files=2 root=%s",
        days, phase, str(output_root),
    )
    return {
        "days_to_kickoff": days,
        "phase_label": phase,
        "files_written": 2,
        "json_path": str(json_path),
        "html_path": str(html_path),
    }
