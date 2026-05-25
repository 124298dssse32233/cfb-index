"""Render Chronicle cards into live-site HTML pages.

Outputs:
  output/site/chronicle/index.html             — landing page, all cards by team
  output/site/chronicle/<slug>.html             — per-team page with that team's cards

Pages use a stripped-down version of the CFB Index design system so they
look on-brand with the rest of the site. Open via Vercel after deploy:
  https://wonderful-margulis-8ec96b.vercel.app/chronicle/
  https://wonderful-margulis-8ec96b.vercel.app/chronicle/alabama.html

Usage:
    python scripts/render_chronicle_site_pages.py
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path


SITE_BASE = Path("output/site/chronicle")

_CITATION_RE = re.compile(r"\[src:[^\]]+\]")


PAGE_CSS = """
  :root {
    --bg: #0a0a0c;
    --fg: #e7e7e9;
    --fg-muted: #888;
    --accent: #d1a23a;
    --card-bg: #14141a;
    --stroke: rgba(255,255,255,0.08);
    --pass: #4a8;
    --flag: #c89744;
  }
  * { box-sizing: border-box; }
  body {
    font-family: 'Inter', system-ui, sans-serif;
    background: var(--bg);
    color: var(--fg);
    margin: 0;
    padding: 0;
    line-height: 1.55;
  }
  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px 32px 80px;
  }
  .nav-strip {
    background: rgba(255,255,255,0.02);
    border-bottom: 1px solid var(--stroke);
    padding: 12px 32px;
    font-size: 12px;
    color: var(--fg-muted);
  }
  .nav-strip a {
    color: var(--accent);
    text-decoration: none;
    margin-right: 16px;
  }
  .nav-strip a:hover { text-decoration: underline; }
  h1 {
    font-family: 'Bebas Neue', sans-serif;
    font-weight: 400;
    font-size: 48px;
    letter-spacing: 0.04em;
    margin: 0 0 8px 0;
  }
  .subtitle {
    color: var(--fg-muted);
    font-size: 14px;
    margin-bottom: 32px;
  }
  .stats {
    display: flex;
    gap: 32px;
    font-size: 13px;
    color: var(--fg-muted);
    margin-bottom: 24px;
    flex-wrap: wrap;
  }
  .stats strong {
    color: var(--accent);
    font-size: 20px;
    display: block;
  }
  .team-section {
    margin: 32px 0;
    padding-top: 16px;
    border-top: 1px solid var(--stroke);
  }
  .team-name {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 28px;
    letter-spacing: 0.06em;
    color: var(--accent);
    margin: 0 0 12px 0;
  }
  .team-name a {
    color: inherit;
    text-decoration: none;
  }
  .team-name a:hover { text-decoration: underline; }
  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px;
  }
  .card {
    background: var(--card-bg);
    border: 1px solid var(--stroke);
    border-left: 3px solid var(--accent);
    border-radius: 8px;
    padding: 16px 20px;
  }
  .card-type {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: var(--fg-muted);
    margin-bottom: 8px;
  }
  .card-headline {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 18px;
    letter-spacing: 0.04em;
    color: var(--fg);
    margin: 0 0 8px 0;
  }
  .card-body {
    font-family: 'Source Serif Pro', Georgia, serif;
    font-size: 15px;
    color: var(--fg);
    margin-bottom: 12px;
  }
  .card-meta {
    font-family: ui-monospace, monospace;
    font-size: 10px;
    color: var(--fg-muted);
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    border-top: 1px solid var(--stroke);
    padding-top: 8px;
  }
  .badge {
    padding: 2px 6px;
    border-radius: 3px;
    background: rgba(255,255,255,0.06);
  }
  .badge--lkg { background: rgba(74,140,90,0.18); color: var(--pass); }
  .badge--v3 { background: rgba(209,162,58,0.18); color: var(--accent); }
  .citation {
    background: rgba(209,162,58,0.10);
    padding: 1px 4px;
    border-radius: 2px;
    font-size: 11px;
    color: var(--accent);
    font-family: ui-monospace, monospace;
  }
  .index-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 8px;
    margin: 24px 0;
  }
  .index-list a {
    display: flex;
    justify-content: space-between;
    padding: 8px 14px;
    background: var(--card-bg);
    border: 1px solid var(--stroke);
    border-radius: 6px;
    color: var(--fg);
    text-decoration: none;
    font-size: 13px;
  }
  .index-list a:hover {
    border-color: var(--accent);
  }
  .index-list .count {
    color: var(--accent);
    font-weight: 700;
  }
  footer {
    border-top: 1px solid var(--stroke);
    margin-top: 64px;
    padding-top: 24px;
    color: var(--fg-muted);
    font-size: 12px;
  }
"""


def _render_card_html(c: sqlite3.Row) -> str:
    try:
        content = json.loads(c["card_content_json"])
        body = content.get("body_text") or ""
        headline = content.get("headline") or ""
    except Exception:
        body = ""
        headline = ""

    body_html = escape(body or "")
    body_html = _CITATION_RE.sub(
        lambda m: f'<span class="citation">{escape(m.group(0))}</span>',
        body_html,
    )

    badges = []
    if c["is_lkg"]:
        badges.append('<span class="badge badge--lkg">LKG</span>')
    tmpl = c["prompt_template_id"] or ""
    if tmpl.startswith("v3"):
        badges.append('<span class="badge badge--v3">v3</span>')
    elif tmpl.startswith("v2"):
        badges.append('<span class="badge">v2</span>')

    headline_html = ""
    if headline:
        headline_html = f'<h3 class="card-headline">{escape(headline)}</h3>'

    fc = c["fact_critic_score"]
    fc_str = f" fc:{fc:.2f}" if fc is not None else ""
    week = c["week_number"]
    season = c["season_year"]
    # Offseason cards (week 0/None) shouldn't show a misleading "wk 12 2024"
    # badge — they cite current offseason evidence. Show a season-only label.
    if week and int(week) > 0:
        when_badge = f"{season or ''} · wk {week}".strip(" ·")
    else:
        when_badge = f"{season or ''} offseason".strip()

    return f"""<article class="card">
  <div class="card-type">{escape(c['card_type'] or '')}</div>
  {headline_html}
  <div class="card-body">{body_html}</div>
  <div class="card-meta">
    {' '.join(badges)}
    <span class="badge">{c['word_count']}w</span>
    <span class="badge">{escape(when_badge)}</span>
    <span class="badge">{fc_str.strip() or 'no critic'}</span>
  </div>
</article>"""


def _page_shell(title: str, content_html: str, breadcrumb: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<div class="nav-strip">
  <a href="/">← CFB Index</a>
  <a href="/chronicle/">The Chronicle</a>
  {breadcrumb}
</div>
<div class="container">
{content_html}
<footer>
  <p>Chronicle cards are LLM-generated narrative content from the CFB Index pipeline.
  Generated locally on Alienware RTX 5070 via Ollama (Mistral Nemo 12B + Qwen3-8B).
  Updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.</p>
</footer>
</div>
</body>
</html>"""


def main() -> int:
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    db_path = Path("cfb_rankings.db")
    if not db_path.exists():
        print(f"DB not found: {db_path}", file=sys.stderr)
        return 1

    SITE_BASE.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    cards = conn.execute("""
        SELECT slug, entity_kind, season_year, week_number, card_type, slot_index,
               card_content_json, model_id, confidence_band, word_count,
               voice_critic_score, fact_critic_score, factscore_atomic,
               prompt_template_id, is_lkg,
               datetime(created_at_utc) as created
        FROM chronicle_card_cache
        WHERE word_count > 0
        ORDER BY slug, card_type, slot_index
    """).fetchall()

    by_team = defaultdict(list)
    for c in cards:
        by_team[c["slug"]].append(c)

    n_total = len(cards)
    n_lkg = sum(1 for c in cards if c["is_lkg"])
    n_teams = len(by_team)

    # --- Landing page ---
    parts = [
        f'<h1>The Chronicle</h1>',
        f'<p class="subtitle">Storylines and narrative intel across college football — '
        f'every card grounded in real evidence and fact-checked before it ships.</p>',
        f'<div class="stats">',
        f'  <div><strong>{n_total}</strong>cards generated</div>',
        f'  <div><strong>{n_teams}</strong>teams covered</div>',
        f'  <div><strong>{n_lkg}</strong>promoted to LKG</div>',
        f'</div>',
        f'<h2 style="font-family: \'Bebas Neue\', sans-serif; letter-spacing: 0.04em; font-size: 24px; color: var(--accent);">Browse by team</h2>',
        f'<div class="index-list">',
    ]
    for team in sorted(by_team.keys()):
        n = len(by_team[team])
        parts.append(
            f'<a href="/chronicle/{escape(team)}.html">'
            f'<span>{escape(team)}</span>'
            f'<span class="count">{n}</span>'
            f'</a>'
        )
    parts.append('</div>')

    parts.append(
        f'<h2 style="font-family: \'Bebas Neue\', sans-serif; letter-spacing: 0.04em; font-size: 24px; color: var(--accent); margin-top: 32px;">All cards</h2>'
    )

    for team in sorted(by_team.keys()):
        parts.append(f'<section class="team-section">')
        parts.append(
            f'  <h2 class="team-name"><a href="/chronicle/{escape(team)}.html">{escape(team)}</a> '
            f'<span style="font-size: 14px; color: var(--fg-muted);">({len(by_team[team])} cards)</span></h2>'
        )
        parts.append(f'  <div class="card-grid">')
        for c in by_team[team]:
            parts.append(_render_card_html(c))
        parts.append(f'  </div>')
        parts.append(f'</section>')

    landing_path = SITE_BASE / "index.html"
    landing_path.write_text(
        _page_shell("The Chronicle · CFB Index", "\n".join(parts)),
        encoding="utf-8",
    )

    # --- Per-team pages ---
    team_paths = []
    for team, team_cards in by_team.items():
        parts = [
            f'<h1>{escape(team)}</h1>',
            f'<p class="subtitle">{len(team_cards)} Chronicle cards generated for this team. '
            f'<a href="/teams/{escape(team)}.html" style="color:var(--accent);text-decoration:none;">'
            f'← Back to {escape(team)} team page</a></p>',
            f'<div class="card-grid">',
        ]
        for c in team_cards:
            parts.append(_render_card_html(c))
        parts.append(f'</div>')

        team_path = SITE_BASE / f"{team}.html"
        team_path.write_text(
            _page_shell(
                f"{team} · The Chronicle · CFB Index",
                "\n".join(parts),
                f'<a href="/chronicle/">All Chronicle storylines</a> · '
                f'<a href="/teams/{escape(team)}.html">{escape(team)} Team Page</a>',
            ),
            encoding="utf-8",
        )
        team_paths.append(team_path)

    print(f"Wrote landing: {landing_path}")
    print(f"Wrote {len(team_paths)} per-team pages")
    print(f"  Live URL after deploy: https://wonderful-margulis-8ec96b.vercel.app/chronicle/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
