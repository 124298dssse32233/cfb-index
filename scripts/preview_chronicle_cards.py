"""Render all generated Chronicle cards to a single HTML preview page.

Outputs `output/chronicle_preview.html` — open in browser to scan all generated
content. Includes quality scores, sources, and per-team grouping.

Usage:
    python scripts/preview_chronicle_cards.py [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from html import escape
from pathlib import Path
from collections import defaultdict


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("output/chronicle_preview.html"))
    p.add_argument("--db", type=Path, default=Path("cfb_rankings.db"))
    args = p.parse_args()

    if not args.db.exists():
        print(f"DB not found: {args.db}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row

    cards = conn.execute(
        """
        SELECT slug, entity_kind, season_year, week_number, card_type, slot_index,
               card_content_json, model_id, confidence_band, word_count,
               voice_critic_score, fact_critic_score, factscore_atomic,
               datetime(created_at_utc) as created, is_lkg
        FROM chronicle_card_cache
        WHERE word_count > 0
        ORDER BY slug, card_type
        """
    ).fetchall()

    # Group by team
    by_team = defaultdict(list)
    for c in cards:
        by_team[c["slug"]].append(c)

    # Summary stats
    n_total = len(cards)
    n_lkg = sum(1 for c in cards if c["is_lkg"])
    avg_words = sum(c["word_count"] or 0 for c in cards) / max(1, n_total)
    by_type = defaultdict(int)
    for c in cards:
        by_type[c["card_type"]] += 1

    args.out.parent.mkdir(parents=True, exist_ok=True)

    html_parts = ["""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Chronicle Cards Preview — CFB Index</title>
<style>
  :root {
    --bg: #0a0a0c;
    --fg: #e7e7e9;
    --fg-muted: #888;
    --accent: #d1a23a;
    --card-bg: #14141a;
    --stroke: rgba(255,255,255,0.08);
    --flag: #c89744;
    --pass: #4a8;
    --fail: #c64;
  }
  * { box-sizing: border-box; }
  body {
    font-family: 'Inter', system-ui, sans-serif;
    background: var(--bg);
    color: var(--fg);
    margin: 0;
    padding: 24px 32px 80px;
    line-height: 1.55;
  }
  h1 {
    font-family: 'Bebas Neue', sans-serif;
    font-weight: 400;
    font-size: 48px;
    letter-spacing: 0.04em;
    margin: 0 0 8px 0;
  }
  .stats {
    display: flex;
    gap: 32px;
    font-size: 13px;
    color: var(--fg-muted);
    margin-bottom: 32px;
    border-bottom: 1px solid var(--stroke);
    padding-bottom: 16px;
  }
  .stats strong { color: var(--accent); font-size: 20px; display: block; }
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
    position: relative;
  }
  .card-type {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: var(--fg-muted);
    margin-bottom: 8px;
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
  .badge { padding: 2px 6px; border-radius: 3px; background: rgba(255,255,255,0.06); }
  .badge--lkg { background: rgba(74,140,90,0.18); color: var(--pass); }
  .badge--high { background: rgba(209,162,58,0.18); color: var(--accent); }
  .badge--medium { background: rgba(200,151,68,0.18); color: var(--flag); }
  .citation { background: rgba(209,162,58,0.10); padding: 1px 4px; border-radius: 2px; font-size: 11px; color: var(--accent); font-family: ui-monospace, monospace; }
</style>
</head>
<body>"""]

    html_parts.append(f"""
<h1>Chronicle Cards Preview</h1>
<div class="stats">
  <div><strong>{n_total}</strong>cards generated</div>
  <div><strong>{len(by_team)}</strong>teams covered</div>
  <div><strong>{n_lkg}</strong>promoted to LKG</div>
  <div><strong>{int(avg_words)}</strong>avg word count</div>
</div>
""")

    # By-type breakdown
    html_parts.append('<div class="stats">')
    for ctype, n in sorted(by_type.items(), key=lambda x: -x[1]):
        html_parts.append(f'  <div><strong>{n}</strong>{ctype}</div>')
    html_parts.append('</div>')

    # Citation marker pattern: [src:xxx]
    import re
    cit_re = re.compile(r"\[src:[^\]]+\]")

    for team in sorted(by_team.keys()):
        team_cards = by_team[team]
        html_parts.append(f'<section class="team-section">')
        html_parts.append(f'  <h2 class="team-name">{escape(team)}</h2>')
        html_parts.append(f'  <div class="card-grid">')
        for c in team_cards:
            try:
                content = json.loads(c["card_content_json"])
                body = content.get("body_text") or content.get("headline") or ""
            except Exception:
                body = "(unparseable)"
            # Highlight citations
            body_html = escape(body or "")
            body_html = cit_re.sub(lambda m: f'<span class="citation">{escape(m.group(0))}</span>', body_html)

            badges = []
            if c["is_lkg"]:
                badges.append('<span class="badge badge--lkg">LKG</span>')
            cb = c["confidence_band"] or "unset"
            badges.append(f'<span class="badge badge--{cb}">{cb}</span>')

            wall = ""
            if c["fact_critic_score"] is not None:
                wall += f' fc:{c["fact_critic_score"]:.2f}'
            if c["factscore_atomic"] is not None:
                wall += f' as:{c["factscore_atomic"]:.2f}'

            html_parts.append(f"""    <article class="card">
      <div class="card-type">{escape(c['card_type'])} · slot {c['slot_index'] or 0}</div>
      <div class="card-body">{body_html}</div>
      <div class="card-meta">
        {' '.join(badges)}
        <span class="badge">{c['word_count']}w</span>
        <span class="badge">{escape((c['model_id'] or '').split(':')[0])}</span>
        <span class="badge">wk {c['week_number'] or '?'} · {c['season_year'] or '?'}</span>
        <span class="badge">{wall.strip() or '—'}</span>
      </div>
    </article>""")
        html_parts.append('  </div>')
        html_parts.append('</section>')

    html_parts.append('</body></html>')

    args.out.write_text("\n".join(html_parts), encoding="utf-8")
    print(f"Wrote {n_total} cards x {len(by_team)} teams to {args.out}")
    print(f"  Open in browser: file:///{args.out.absolute()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
