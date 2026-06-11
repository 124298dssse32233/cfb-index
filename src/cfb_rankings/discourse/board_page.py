"""Fan-Voice Board page builder — Language Layer Wave 3.

Builds /fan-voice/index.html — a standalone leaderboard page showing:
  1. Optimism Leaderboard — all teams in fanbase_voice_profile cohort,
     sorted by optimism_mean desc. Team name, optimism score, percentile rank.
  2. Signature Terms Mosaic — top "signature" term per team from
     team_discourse_terms (magnitude_band='signature', term_rank=1),
     shown as a grid of team+term+multiplier cards.
  3. Word of the Week Spotlight — teams with a word-of-week (weekly cut,
     week > 0, z_score >= 4) in the current week, top 5 by z_score.

CLI: python manage.py build-fan-voice-board --season YEAR

Public API:
    build_fan_voice_board(db, output_dir, season) -> str
    (returns the path written as a string)
"""

from __future__ import annotations
import math
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any


def _field(row: Any, key: str) -> Any:
    try:
        return row[key]
    except (TypeError, KeyError, IndexError):
        return None


def build_fan_voice_board(db, output_dir, season: int) -> str:
    output_dir = Path(output_dir)
    fan_voice_dir = output_dir / "fan-voice"
    fan_voice_dir.mkdir(parents=True, exist_ok=True)
    out_path = fan_voice_dir / "index.html"

    from cfb_rankings.common.week import resolve_week
    current_week = int(resolve_week().week)

    # ── 1. Optimism leaderboard ──────────────────────────────────────────
    try:
        opt_rows = db.query_all(
            "SELECT fvp.optimism_rank, fvp.optimism_mean, fvp.cohort_size, "
            "tm.school_name "
            "FROM fanbase_voice_profile fvp "
            "JOIN teams tm ON tm.team_id = fvp.team_id "
            "WHERE fvp.season_year = :season "
            "ORDER BY fvp.optimism_rank ASC",
            {"season": season},
        )
    except Exception:
        opt_rows = []

    opt_html = ""
    if opt_rows:
        total = int(_field(opt_rows[0], "cohort_size") or len(opt_rows))
        rows_html = ""
        for row in opt_rows:
            rank = int(_field(row, "optimism_rank") or 0)
            score = float(_field(row, "optimism_mean") or 0.0)
            name = escape(str(_field(row, "school_name") or ""))
            sign = "+" if score >= 0 else ""
            bar_pct = min(100, max(0, int((score + 0.3) / 0.6 * 100)))
            rows_html += (
                f'<tr class="board__row">'
                f'<td class="board__rank">{rank}</td>'
                f'<td class="board__name">{name}</td>'
                f'<td class="board__score">{sign}{score:.3f}</td>'
                f'<td class="board__bar-cell">'
                f'<div class="board__bar" style="width:{bar_pct}%"></div>'
                f'</td>'
                f'</tr>'
            )
        opt_html = f"""
<section class="board-section">
  <h2 class="board-section__title">Optimism Leaderboard</h2>
  <p class="board-section__meta">
    Average sentiment score across fan posts · {total} fanbases · {season} season
  </p>
  <table class="board__table">
    <thead>
      <tr>
        <th>Rank</th><th>Fanbase</th><th>Score</th><th>Bar</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>
</section>"""

    # ── 2. Signature terms mosaic ─────────────────────────────────────────
    try:
        sig_rows = db.query_all(
            "SELECT tdt.term, tdt.rate_ratio, tm.school_name "
            "FROM team_discourse_terms tdt "
            "JOIN teams tm ON tm.team_id = tdt.team_id "
            "WHERE tdt.season_year = :season AND tdt.week = 0 "
            "AND tdt.term_rank = 1 "
            "ORDER BY tdt.rate_ratio DESC",
            {"season": season},
        )
    except Exception:
        sig_rows = []

    sig_html = ""
    if sig_rows:
        cards_html = ""
        for row in sig_rows:
            name = escape(str(_field(row, "school_name") or ""))
            term = escape(str(_field(row, "term") or ""))
            ratio = float(_field(row, "rate_ratio") or 0.0)
            cards_html += (
                f'<div class="mosaic__card">'
                f'<div class="mosaic__team">{name}</div>'
                f'<div class="mosaic__term">{term}</div>'
                f'<div class="mosaic__ratio">×{ratio:.1f}</div>'
                f'</div>'
            )
        sig_html = f"""
<section class="board-section">
  <h2 class="board-section__title">Signature Terms — {season}</h2>
  <p class="board-section__meta">
    Each fanbase's most statistically distinctive word · ×N vs rest of college football
  </p>
  <div class="mosaic">{cards_html}</div>
</section>"""

    # ── 3. Word of the Week spotlight ────────────────────────────────────
    try:
        wow_rows = db.query_all(
            "SELECT tdt.term, tdt.rate_ratio, tdt.z_score, tdt.week, tm.school_name "
            "FROM team_discourse_terms tdt "
            "JOIN teams tm ON tm.team_id = tdt.team_id "
            "WHERE tdt.season_year = :season AND tdt.week = :week "
            "AND tdt.term_rank = 1 AND tdt.z_score >= 4.0 "
            "ORDER BY tdt.z_score DESC LIMIT 6",
            {"season": season, "week": current_week},
        )
    except Exception:
        wow_rows = []

    wow_html = ""
    if wow_rows:
        items_html = ""
        for row in wow_rows:
            name = escape(str(_field(row, "school_name") or ""))
            term = escape(str(_field(row, "term") or ""))
            ratio = float(_field(row, "rate_ratio") or 0.0)
            z = float(_field(row, "z_score") or 0.0)
            items_html += (
                f'<div class="wow-spot__item">'
                f'<span class="wow-spot__team">{name}</span>'
                f'<span class="wow-spot__term">{term}</span>'
                f'<span class="wow-spot__meta">×{ratio:.1f} · z={z:.1f}</span>'
                f'</div>'
            )
        wow_html = f"""
<section class="board-section">
  <h2 class="board-section__title">Word of the Week — Wk {current_week}</h2>
  <div class="wow-spot">{items_html}</div>
</section>"""

    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Fan Voice Board — {season} CFB Season</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{
  --bg: #0d0d0d;
  --fg: #e8e0d4;
  --fg-muted: rgba(232,224,212,0.5);
  --accent: #c9a24a;
  --stroke: rgba(255,255,255,0.08);
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: ui-monospace, monospace;
  --font-serif: 'Source Serif Pro', Georgia, serif;
  --font-display: 'Bebas Neue', Impact, sans-serif;
}}
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Hepta+Slab:wght@100..900&display=swap');
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: var(--bg); color: var(--fg); font-family: var(--font-sans); padding: clamp(16px, 4vw, 48px); }}
.page-title {{ font-family: var(--font-display); font-size: clamp(36px, 8vw, 72px); color: var(--accent); margin-bottom: 6px; line-height: 1; }}
.page-meta {{ font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--fg-muted); margin-bottom: 48px; }}
.board-section {{ margin-bottom: 56px; }}
.board-section__title {{ font-family: var(--font-display); font-size: clamp(22px, 4vw, 36px); color: var(--fg); margin-bottom: 6px; }}
.board-section__meta {{ font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-muted); margin-bottom: 20px; }}
.board__table {{ width: 100%; border-collapse: collapse; }}
.board__table th {{ font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--fg-muted); text-align: left; padding: 6px 12px 6px 0; border-bottom: 1px solid var(--stroke); }}
.board__row td {{ padding: 8px 12px 8px 0; border-bottom: 1px solid var(--stroke); vertical-align: middle; }}
.board__rank {{ font-family: var(--font-mono); font-size: 11px; color: var(--fg-muted); width: 32px; font-variant-numeric: tabular-nums; }}
.board__name {{ font-size: 14px; font-weight: 600; }}
.board__score {{ font-family: var(--font-mono); font-size: 12px; font-variant-numeric: tabular-nums; color: var(--accent); width: 70px; }}
.board__bar-cell {{ width: 200px; }}
.board__bar {{ height: 4px; background: var(--accent); border-radius: 2px; min-width: 2px; }}
.mosaic {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }}
.mosaic__card {{ padding: 14px; background: rgba(255,255,255,0.025); border: 1px solid var(--stroke); border-radius: 10px; }}
.mosaic__team {{ font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--fg-muted); margin-bottom: 6px; }}
.mosaic__term {{ font-family: 'Hepta Slab', var(--font-serif); font-size: 20px; font-weight: 700; color: var(--fg); line-height: 1; overflow-wrap: anywhere; }}
.mosaic__ratio {{ font-family: var(--font-mono); font-size: 11px; color: var(--accent); margin-top: 4px; font-variant-numeric: tabular-nums; }}
.wow-spot {{ display: grid; gap: 10px; }}
.wow-spot__item {{ display: flex; align-items: center; gap: 16px; padding: 10px 16px; background: rgba(255,255,255,0.025); border: 1px solid var(--stroke); border-radius: 8px; }}
.wow-spot__team {{ font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--fg-muted); min-width: 120px; }}
.wow-spot__term {{ font-family: 'Hepta Slab', var(--font-serif); font-size: 22px; font-weight: 800; color: var(--accent); overflow-wrap: anywhere; }}
.wow-spot__meta {{ font-family: var(--font-mono); font-size: 10px; color: var(--fg-muted); margin-left: auto; white-space: nowrap; font-variant-numeric: tabular-nums; }}
</style>
</head>
<body>
<h1 class="page-title">Fan Voice Board</h1>
<p class="page-meta">{season} CFB season · built {built_at}</p>
{opt_html}
{sig_html}
{wow_html}
</body>
</html>"""

    out_path.write_text(html, encoding="utf-8")
    return str(out_path)


__all__ = ["build_fan_voice_board"]
