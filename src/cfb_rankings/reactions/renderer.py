"""Reaction Story renderer (Sprint 15 Phase 5).

Writes:
  output/site/reactions/{slug}/index.html  — story page
  output/site/reactions/index.html         — archive index (last 50)

Inline string templates; no Jinja2 (not in project deps). Matches the
receipts/render.py pattern. CSS braces are NOT passed through str.format()
— the page is assembled via concatenation to avoid KeyError on CSS custom
properties like var(--bg).
"""
from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .data import CohortSplit, ReactionStory, fetch_cohort_splits, fetch_story, list_stories

SITE_ROOT = Path(__file__).resolve().parents[3] / "output" / "site"

_CSS = """\
:root{--bg:#0c0e10;--card:#14171b;--ink:#e8eaed;--ink-dim:#95a0ad;
--accent:#f4c95d;--pos:#5dd39e;--neg:#d96c6c;--surprise:#e8904a;}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;}
a{color:var(--ink);text-decoration:none;border-bottom:1px dotted var(--ink-dim);}
a:hover{color:var(--accent);border-bottom-color:var(--accent);}
.wrap{max-width:900px;margin:0 auto;padding:48px 24px 96px;}
.eyebrow{font:600 11px/1 system-ui;letter-spacing:.18em;text-transform:uppercase;
  color:var(--accent);margin-bottom:10px;}
h1{font:700 40px/1.1 "Crimson Pro",Georgia,serif;margin:10px 0 8px;letter-spacing:-.015em;}
.dek{color:var(--ink-dim);font-size:18px;line-height:1.5;max-width:62ch;margin-bottom:28px;}
.surprise-chip{display:inline-flex;align-items:center;gap:6px;
  background:rgba(232,144,74,.15);color:var(--surprise);
  font:700 12px/1 system-ui;letter-spacing:.06em;padding:4px 12px;
  border-radius:20px;margin-bottom:20px;}
.layout{display:grid;grid-template-columns:1fr 260px;gap:40px;}
@media(max-width:720px){.layout{grid-template-columns:1fr;}}
.body h2{font:600 20px/1.25 "Crimson Pro",Georgia,serif;
  margin:36px 0 8px;color:var(--accent);}
.body p{margin:0 0 18px;max-width:68ch;}
.quote-pill{background:var(--card);border-left:3px solid var(--ink-dim);
  border-radius:0 8px 8px 0;padding:12px 16px;margin:10px 0;}
.quote-pill em{color:var(--ink-dim);font-size:13px;}
.sidebar{}
.cohort-card{background:var(--card);border-radius:10px;padding:16px;margin-bottom:16px;}
.cohort-label{font:700 10px/1 system-ui;letter-spacing:.14em;text-transform:uppercase;
  color:var(--accent);margin-bottom:6px;}
.cohort-stance{font-size:13px;color:var(--ink-dim);margin-bottom:8px;}
.sentiment-bar{height:6px;background:#20242a;border-radius:3px;overflow:hidden;margin:6px 0;}
.sentiment-fill{height:100%;border-radius:3px;}
.vol-share{font:600 11px/1 system-ui;color:var(--ink-dim);}
h2.section{font:600 18px/1.25 system-ui;margin:4px 0 16px;}
.story-card{background:var(--card);border-radius:10px;padding:18px 22px;
  margin-bottom:14px;border-left:3px solid var(--accent);}
.story-card .meta{color:var(--ink-dim);font-size:12px;margin-bottom:6px;
  display:flex;gap:12px;flex-wrap:wrap;}
.story-card h3{margin:0 0 4px;font:600 18px/1.2 "Crimson Pro",Georgia,serif;}
.story-card .sub{color:var(--ink-dim);font-size:13px;}
.footer{margin-top:64px;color:var(--ink-dim);font-size:13px;}
"""


def _page_head(title: str) -> str:
    escaped = html.escape(title)
    return (
        f'<!doctype html>\n<html lang="en">\n<head>\n'
        f'<meta charset="utf-8"/>\n'
        f'<title>{escaped}</title>\n'
        f'<meta name="viewport" content="width=device-width,initial-scale=1"/>\n'
        f'<style>\n{_CSS}</style>\n'
        f'</head>\n<body><div class="wrap">\n'
    )


def _page_foot() -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    return f'<div class="footer">CFB Index · Reaction Stories · regenerated {now} UTC</div>\n</div></body></html>\n'


# ── Markdown → HTML (minimal inline converter) ──────────────────────────────

def _md_to_html(md: str) -> str:
    lines = md.split("\n")
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            out.append(f'<h2>{html.escape(stripped[3:])}</h2>')
        elif stripped.startswith("> "):
            content = stripped[2:]
            content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)
            content = re.sub(r"\*(.+?)\*", r"<em>\1</em>", content)
            out.append(f'<div class="quote-pill">{content}</div>')
        elif stripped == "":
            out.append("")
        else:
            content = html.escape(stripped)
            content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)
            content = re.sub(r"\*(.+?)\*", r"<em>\1</em>", content)
            out.append(f"<p>{content}</p>")
    return "\n".join(out)


# ── Cohort sidebar ──────────────────────────────────────────────────────────

def _cohort_label(cohort: str) -> str:
    return {"stat_folks": "Stat Folks", "casual_fans": "Regular Fans",
            "die_hards": "Die-Hards"}.get(cohort, cohort)


def _sentiment_bar(score: Optional[float]) -> str:
    if score is None:
        return ""
    pct = int((score + 1) / 2 * 100)
    if score > 0.1:
        color = "var(--pos)"
    elif score < -0.1:
        color = "var(--neg)"
    else:
        color = "var(--ink-dim)"
    return (
        f'<div class="sentiment-bar">'
        f'<div class="sentiment-fill" style="width:{pct}%;background:{color}"></div></div>'
        f'<div class="vol-share">Sentiment {score:+.2f}</div>'
    )


def _sidebar_html(splits: list[CohortSplit]) -> str:
    total_vol = sum((s.volume_share or 0) for s in splits) or 1.0
    parts = ['<div class="sidebar">']
    for split in splits:
        label = _cohort_label(split.cohort)
        stance = html.escape(split.stance[:120])
        vol_pct = int((split.volume_share or 0) / total_vol * 100)
        bar = _sentiment_bar(split.sentiment_score)
        parts.append(
            f'<div class="cohort-card">'
            f'<div class="cohort-label">{label}</div>'
            f'<div class="cohort-stance">{stance}</div>'
            f'{bar}'
            f'<div class="vol-share">{vol_pct}% of mentions</div>'
            f'</div>'
        )
    parts.append("</div>")
    return "\n".join(parts)


# ── Story page renderer ─────────────────────────────────────────────────────

def render_story(slug: str) -> Optional[Path]:
    story = fetch_story(slug)
    if story is None:
        print(f"  [render] story not found: {slug}", flush=True)
        return None
    splits = fetch_cohort_splits(slug)

    out_dir = SITE_ROOT / "reactions" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"

    triggered_dt = story.triggered_at_utc[:10]
    wire_link = "/wire/index.html"
    eyebrow = (
        f'Reaction Story · triggered {triggered_dt} · '
        f'<a href="{wire_link}">wire entry #{story.triggered_by_wire_id}</a>'
    )

    surprise_chip = ""
    if story.surprise_index is not None and story.surprise_index >= 75:
        surprise_chip = (
            f'<div class="surprise-chip">'
            f'Surprise Index {story.surprise_index:.0f} ← unlikely</div>\n'
        )

    body_html = _md_to_html(story.body)
    sidebar = _sidebar_html(splits)

    page = _page_head(f"{story.headline} · CFB Index Reaction")
    page += f'<div class="eyebrow">{eyebrow}</div>\n'
    page += f'<h1>{html.escape(story.headline)}</h1>\n'
    page += f'<p class="dek">{html.escape(story.dek)}</p>\n'
    page += surprise_chip
    page += '<div class="layout">\n'
    page += f'<div class="body">{body_html}</div>\n'
    page += sidebar + "\n"
    page += "</div>\n"
    page += _page_foot()

    out_path.write_text(page, encoding="utf-8")
    print(f"  [render] wrote {out_path}", flush=True)
    return out_path


# ── Archive index renderer ──────────────────────────────────────────────────

def render_archive(limit: int = 50) -> Path:
    stories = list_stories(status="published", limit=limit)
    out_dir = SITE_ROOT / "reactions"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"

    page = _page_head("Reaction Stories · CFB Index")
    page += '<div class="eyebrow">CFB Index</div>\n'
    page += '<h1>Reaction Stories</h1>\n'
    page += (
        '<p class="dek">On-demand pieces that fire when a wire event crosses a velocity '
        'threshold — the proprietary spin is cohort divergence: what stat folks, '
        'regular fans, and the boards each said, and why the split matters.</p>\n'
    )
    page += f'<h2 class="section">Latest {len(stories)} Stories</h2>\n'

    for s in stories:
        dt = s.triggered_at_utc[:10]
        surprise_note = ""
        if s.surprise_index is not None and s.surprise_index >= 75:
            surprise_note = f' · Surprise Index {s.surprise_index:.0f} ← unlikely'
        entity_badge = html.escape(s.primary_entity_slug.replace("-", " ").title())
        hl = html.escape(s.headline)
        dk = html.escape(s.dek[:160]) + ("…" if len(s.dek) > 160 else "")
        page += (
            f'<div class="story-card">'
            f'<div class="meta"><span>{dt}</span><span>{entity_badge}</span>'
            f'<span>velocity {s.triggered_by_velocity:.0f}{surprise_note}</span></div>'
            f'<h3><a href="/reactions/{s.slug}/">{hl}</a></h3>'
            f'<div class="sub">{dk}</div>'
            f'</div>\n'
        )

    if not stories:
        page += '<p style="color:var(--ink-dim)">No published reaction stories yet.</p>\n'

    page += _page_foot()
    out_path.write_text(page, encoding="utf-8")
    print(f"  [render-archive] wrote {out_path}", flush=True)
    return out_path


# ── Public entrypoints ──────────────────────────────────────────────────────

def render_all() -> dict:
    stories = list_stories(status="published")
    rendered = []
    for s in stories:
        path = render_story(s.slug)
        if path:
            rendered.append(str(path))
    archive_path = render_archive()
    return {"stories_rendered": len(rendered), "archive": str(archive_path), "paths": rendered}
