"""Mailbag renderer — writes static HTML output.

Outputs:
  output/site/mailbag/index.html              — current edition (most recent published)
  output/site/mailbag/{edition_slug}/index.html — archive per edition
  output/site/mailbag/submit/index.html       — submission form (mailto for now)
  output/site/mailbag/archive.html            — last 30 editions list

Uses {{TOKEN}} substitution matching the existing static-site pattern.
No new design tokens — inherits the Wire/Edition typographic system.
"""
from __future__ import annotations

import html
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .data import (
    db_conn,
    list_answers_for_edition,
    list_recent_editions,
    get_edition,
    edition_publish_date,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared CSS — inherits the same palette as the Wire/Edition pages
# ---------------------------------------------------------------------------

_BASE_STYLE = """
*, *::before, *::after { box-sizing: border-box; }
:root {
  --ink: #1a1a1a;
  --paper: #f6f1e6;
  --paper-dim: #ece6d6;
  --rule: #1a1a1a;
  --rule-soft: rgba(26,26,26,0.18);
  --gold: #c9a24a;
  --navy: #1f2c4d;
  --muted: #7a7a7a;
  --amber: #b8842c;
  --green: #2d6f3a;
  --red: #a23232;
  --serif: 'Source Serif Pro', 'Georgia', 'Times New Roman', serif;
  --sans: 'Inter', 'Helvetica Neue', -apple-system, system-ui, sans-serif;
}
html, body { margin: 0; padding: 0; background: var(--paper); color: var(--ink);
  font-family: var(--serif); font-size: 17px; line-height: 1.6; }
.page { max-width: 1280px; margin: 0 auto; padding: 0 64px; }
@media (max-width: 720px) { .page { padding: 0 24px; } }
.eyebrow { font-family: var(--sans); font-size: 11px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--ink); }
.eyebrow.muted { color: var(--muted); }
.rule { border: 0; height: 1px; background: var(--rule); margin: 0; }
.rule.soft { background: var(--rule-soft); }
a { color: inherit; text-decoration: none; }
a.text-link { border-bottom: 1px dotted currentColor; }

.chrome { font-family: var(--sans); font-size: 11px; font-weight: 600;
  letter-spacing: 0.16em; text-transform: uppercase;
  display: flex; justify-content: space-between; padding: 12px 0; }
.brand-row { display: flex; align-items: baseline; justify-content: space-between;
  padding: 24px 0; }
.brand { font-family: var(--serif); font-size: 32px; font-weight: 700;
  letter-spacing: 0.04em; }
.brand .slash { color: var(--gold); margin: 0 6px; }
.nav { font-family: var(--sans); font-size: 12px; font-weight: 600;
  letter-spacing: 0.14em; text-transform: uppercase; }
.nav a { margin-left: 28px; color: var(--ink); }
.nav a:hover { color: var(--gold); }

/* Hero */
.hero { padding: 72px 0 48px; }
.hero .kicker { font-family: var(--sans); font-size: 13px; font-weight: 700;
  letter-spacing: 0.22em; text-transform: uppercase; color: var(--gold);
  margin-bottom: 12px; }
.hero .masthead { font-family: var(--serif); font-size: 52px; font-weight: 700;
  line-height: 1.05; margin: 0 0 12px; }
.hero .deck { font-family: var(--serif); font-size: 20px; font-style: italic;
  line-height: 1.45; max-width: 680px; color: var(--ink); margin: 0 0 24px; }
.hero .meta { font-family: var(--sans); font-size: 12px; font-weight: 600;
  letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); }

/* Layout: two-column on desktop */
.content-grid { display: grid; grid-template-columns: 1fr 260px; gap: 64px;
  padding: 48px 0 64px; align-items: start; }
@media (max-width: 900px) { .content-grid { grid-template-columns: 1fr; gap: 32px; } }

/* Answer cards */
.answer-card { padding: 40px 0; border-top: 1px solid var(--rule); }
.answer-card:first-child { border-top: 2px solid var(--rule); }
.answer-num { font-family: var(--sans); font-size: 11px; font-weight: 700;
  letter-spacing: 0.2em; text-transform: uppercase; color: var(--gold); margin-bottom: 12px; }
.answer-question { font-family: var(--serif); font-size: 24px; font-style: italic;
  font-weight: 600; line-height: 1.3; margin: 0 0 6px; color: var(--ink); }
.answer-byline { font-family: var(--sans); font-size: 12px; font-weight: 600;
  letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted);
  margin: 0 0 24px; }
.answer-body { font-size: 17px; line-height: 1.65; max-width: 720px; }
.answer-body p { margin: 0 0 1em; }
.short-answer { display: inline-block; margin-top: 20px; padding: 10px 16px;
  background: var(--navy); color: #fff; font-family: var(--sans);
  font-size: 13px; font-weight: 700; letter-spacing: 0.08em; border-radius: 3px; }
.short-answer .label { text-transform: uppercase; letter-spacing: 0.18em;
  font-size: 10px; opacity: 0.7; margin-right: 6px; }

/* Source pills */
.source-pills { margin-top: 16px; display: flex; flex-wrap: wrap; gap: 8px; }
.pill { font-family: var(--sans); font-size: 11px; font-weight: 600;
  letter-spacing: 0.1em; text-transform: uppercase; padding: 4px 10px;
  border: 1px solid var(--rule-soft); border-radius: 2px; color: var(--muted); }

/* Sidebar */
.sidebar { font-family: var(--sans); font-size: 13px; }
.sidebar-head { font-size: 11px; font-weight: 700; letter-spacing: 0.2em;
  text-transform: uppercase; color: var(--muted); padding-bottom: 12px;
  border-bottom: 1px solid var(--rule); margin-bottom: 16px; }
.sidebar-edition { padding: 10px 0; border-bottom: 1px solid var(--rule-soft); }
.sidebar-edition a { font-weight: 600; color: var(--ink); }
.sidebar-edition a:hover { color: var(--gold); }
.sidebar-edition .date { display: block; font-size: 11px; color: var(--muted);
  margin-top: 2px; }
.sidebar-cta { margin-top: 24px; padding: 20px; background: var(--paper-dim);
  border-top: 2px solid var(--gold); }
.sidebar-cta p { margin: 0 0 12px; line-height: 1.45; }
.sidebar-cta a { font-weight: 700; border-bottom: 1px solid var(--gold); color: var(--gold); }

/* Archive page */
.archive-list { list-style: none; padding: 0; margin: 0; }
.archive-item { padding: 16px 0; border-bottom: 1px solid var(--rule-soft);
  display: flex; align-items: baseline; gap: 20px; }
.archive-item .slug { font-family: var(--sans); font-size: 13px; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase; width: 100px; flex-shrink: 0; }
.archive-item .date { font-family: var(--sans); font-size: 12px; color: var(--muted);
  width: 100px; flex-shrink: 0; }
.archive-item .status { font-family: var(--sans); font-size: 11px; font-weight: 700;
  letter-spacing: 0.14em; text-transform: uppercase; color: var(--green); }
.archive-item .status.draft { color: var(--amber); }

/* Submit form */
.submit-form { max-width: 560px; }
.form-group { margin-bottom: 28px; }
.form-group label { display: block; font-family: var(--sans); font-size: 12px;
  font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;
  margin-bottom: 8px; }
.form-group input, .form-group textarea {
  width: 100%; padding: 12px 14px; background: #fff; border: 1px solid var(--rule-soft);
  font-family: var(--serif); font-size: 16px; line-height: 1.5; color: var(--ink);
  border-radius: 2px; outline: none; }
.form-group input:focus, .form-group textarea:focus {
  border-color: var(--gold); }
.form-group textarea { height: 160px; resize: vertical; }
.form-note { font-size: 13px; color: var(--muted); margin-top: 6px; font-style: italic; }
.btn-submit { display: inline-block; padding: 12px 28px; background: var(--navy);
  color: #fff; font-family: var(--sans); font-size: 13px; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase; border: none;
  cursor: pointer; border-radius: 2px; }
.btn-submit:hover { background: var(--gold); }
.mailto-note { margin-top: 16px; font-family: var(--sans); font-size: 12px;
  color: var(--muted); font-style: italic; }

.footer { padding: 64px 0 48px; font-family: var(--sans); font-size: 12px;
  color: var(--muted); border-top: 1px solid var(--rule-soft); margin-top: 32px; }
"""


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _nav_html() -> str:
    return (
        '<nav class="nav">'
        '<a href="/">Rankings</a>'
        '<a href="/wire/">Wire</a>'
        '<a href="/editions/">Edition</a>'
        '<a href="/mailbag/">Mailbag</a>'
        '</nav>'
    )


def _chrome_html(edition_slug: str = "") -> str:
    label = f"The Mailbag — {edition_slug}" if edition_slug else "The Mailbag"
    return (
        f'<div class="chrome">'
        f'<span class="eyebrow">CFB Index</span>'
        f'<span class="eyebrow muted">{html.escape(label)}</span>'
        f'</div>'
    )


def _brand_row_html() -> str:
    return (
        '<div class="brand-row">'
        '<div class="brand">CFB<span class="slash">/</span>Index</div>'
        + _nav_html() +
        '</div>'
        '<hr class="rule" />'
    )


def _footer_html() -> str:
    return (
        '<footer class="footer">'
        '<p>CFB Index — college football rankings &amp; intelligence. '
        '<a href="/mailbag/submit/" class="text-link">Submit a question</a> · '
        '<a href="/mailbag/archive.html" class="text-link">Archive</a> · '
        '<a href="/about-model/" class="text-link">About</a></p>'
        '</footer>'
    )


def _answer_card_html(rank: int, answer: dict[str, Any]) -> str:
    handle = html.escape(answer.get("submitter_handle") or "A reader")
    question = html.escape(answer.get("question_text") or "")
    body_raw = answer.get("answer_body") or ""

    # Extract "Short answer:" line and separate from body
    short_answer = ""
    body_lines: list[str] = []
    in_short = False
    for line in body_raw.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("short answer:"):
            short_text = stripped[len("short answer:"):].strip()
            short_answer = html.escape(short_text)
            in_short = True
        elif not in_short:
            body_lines.append(line)

    body_paragraphs = "\n".join(body_lines).strip()
    # Wrap each paragraph in <p>
    paras = [p.strip() for p in body_paragraphs.split("\n\n") if p.strip()]
    body_html = "\n".join(f"<p>{html.escape(p)}</p>" for p in paras) if paras else f"<p>{html.escape(body_raw)}</p>"

    # Source pills
    cited_raw = answer.get("cited_sources_json") or "[]"
    try:
        sources: list[str] = json.loads(cited_raw)
    except Exception:
        sources = []
    pills_html = ""
    if sources:
        pills = "".join(f'<span class="pill">{html.escape(s[:40])}</span>' for s in sources[:5])
        pills_html = f'<div class="source-pills">{pills}</div>'

    short_block = ""
    if short_answer:
        short_block = (
            f'<div class="short-answer">'
            f'<span class="label">Short answer</span>{short_answer}'
            f'</div>'
        )

    return (
        f'<div class="answer-card">'
        f'<div class="answer-num">Question {rank}</div>'
        f'<blockquote class="answer-question">&ldquo;{question}&rdquo;</blockquote>'
        f'<div class="answer-byline">— {handle}</div>'
        f'<div class="answer-body">{body_html}</div>'
        f'{short_block}'
        f'{pills_html}'
        f'</div>'
    )


def _sidebar_html(recent_editions: list[dict[str, Any]], current_slug: str = "") -> str:
    items = ""
    for ed in recent_editions[:5]:
        slug = html.escape(ed["edition_slug"])
        pub_date = html.escape(ed.get("publish_date") or "")
        active = ' style="color:var(--gold);"' if slug == html.escape(current_slug) else ""
        items += (
            f'<div class="sidebar-edition">'
            f'<a href="/mailbag/{slug}/"{active}>{slug}</a>'
            f'<span class="date">{pub_date}</span>'
            f'</div>'
        )

    return (
        f'<aside class="sidebar">'
        f'<div class="sidebar-head">Recent Editions</div>'
        f'{items}'
        f'<div class="sidebar-cta">'
        f'<p>Got a question about CFB? We read everything.</p>'
        f'<a href="/mailbag/submit/">Submit a question &rarr;</a>'
        f'</div>'
        f'</aside>'
    )


def _full_page_html(
    title: str,
    body: str,
    *,
    edition_slug: str = "",
) -> str:
    safe_title = html.escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe_title} — CFB Index</title>
<link rel="stylesheet" href="/assets/cfb-index.93e59647a6bd.css">
<style>{_BASE_STYLE}</style>
</head>
<body class="mailbag__page">
<div class="page">
{_chrome_html(edition_slug)}
{_brand_row_html()}
{body}
{_footer_html()}
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Edition page renderer
# ---------------------------------------------------------------------------

def render_edition_page(
    edition_slug: str,
    *,
    output_dir: Path,
    is_index: bool = False,
) -> Path | None:
    """Render one edition page. Returns output path, or None if no published answers."""
    with db_conn() as conn:
        edition = get_edition(conn, edition_slug)
        if not edition:
            log.warning("mailbag.renderer: edition %s not found", edition_slug)
            return None
        answers = list_answers_for_edition(conn, edition_slug)
        recent = list_recent_editions(conn, limit=6)

    if not answers:
        log.warning("mailbag.renderer: no answers for edition %s", edition_slug)
        return None

    pub_date = html.escape(edition.get("publish_date") or "")
    masthead = f"The Mailbag"
    deck = f"Edition {html.escape(edition_slug)} — published Friday {pub_date}"

    hero_html = (
        f'<header class="hero">'
        f'<div class="kicker">The Mailbag</div>'
        f'<h1 class="masthead">{masthead}</h1>'
        f'<p class="deck">{deck}</p>'
        f'<div class="meta">Your questions. The corpus answers.</div>'
        f'</header>'
        f'<hr class="rule soft" />'
    )

    cards_html = "\n".join(
        _answer_card_html(a["rank_position"], a)
        for a in answers
    )

    sidebar_html = _sidebar_html(recent, current_slug=edition_slug)

    content = (
        f'{hero_html}'
        f'<div class="content-grid">'
        f'<main>{cards_html}</main>'
        f'{sidebar_html}'
        f'</div>'
    )

    page = _full_page_html(f"The Mailbag — {edition_slug}", content, edition_slug=edition_slug)

    if is_index:
        out_path = output_dir / "index.html"
    else:
        edition_dir = output_dir / edition_slug
        edition_dir.mkdir(parents=True, exist_ok=True)
        out_path = edition_dir / "index.html"

    out_path.write_text(page, encoding="utf-8")
    log.info("mailbag.renderer: wrote %s (%d answers)", out_path, len(answers))
    return out_path


# ---------------------------------------------------------------------------
# Archive page
# ---------------------------------------------------------------------------

def render_archive_page(output_dir: Path) -> Path:
    with db_conn() as conn:
        editions = list_recent_editions(conn, limit=30)

    items_html = ""
    for ed in editions:
        slug = html.escape(ed["edition_slug"])
        pub_date = html.escape(ed.get("publish_date") or "")
        status = ed.get("status") or "draft"
        status_class = "status" if status == "published" else "status draft"
        items_html += (
            f'<li class="archive-item">'
            f'<span class="slug"><a href="/mailbag/{slug}/" class="text-link">{slug}</a></span>'
            f'<span class="date">{pub_date}</span>'
            f'<span class="{status_class}">{html.escape(status)}</span>'
            f'</li>'
        )

    if not items_html:
        items_html = '<li class="archive-item"><span class="eyebrow muted">No editions yet.</span></li>'

    body = (
        '<header class="hero">'
        '<div class="kicker">The Mailbag</div>'
        '<h1 class="masthead">Archive</h1>'
        '<p class="deck">Every edition, going back to the beginning.</p>'
        '</header>'
        '<hr class="rule soft" />'
        f'<ul class="archive-list" style="padding:40px 0;">{items_html}</ul>'
    )

    page = _full_page_html("The Mailbag — Archive", body)
    out_path = output_dir / "archive.html"
    out_path.write_text(page, encoding="utf-8")
    log.info("mailbag.renderer: wrote archive %s (%d editions)", out_path, len(editions))
    return out_path


# ---------------------------------------------------------------------------
# Submit form page
# ---------------------------------------------------------------------------

def render_submit_page(output_dir: Path) -> Path:
    body = (
        '<header class="hero">'
        '<div class="kicker">The Mailbag</div>'
        '<h1 class="masthead">Submit a Question</h1>'
        '<p class="deck">Ask us anything about college football. '
        'We pull from the full corpus — Wire, Pulse, Receipts, beat writers — '
        'to give you a sourced answer, not an opinion.</p>'
        '</header>'
        '<hr class="rule soft" />'
        '<div style="padding:48px 0;">'
        '<div class="submit-form">'
        '<form action="mailto:mailbag@cfbindex.local" method="post" enctype="text/plain">'
        '<div class="form-group">'
        '<label for="handle">Your name / handle</label>'
        '<input type="text" id="handle" name="handle" placeholder="e.g. Marcus from Columbus" />'
        '<div class="form-note">This is how we\'ll credit you if we run your question.</div>'
        '</div>'
        '<div class="form-group">'
        '<label for="email">Email (optional)</label>'
        '<input type="email" id="email" name="email" placeholder="you@example.com" />'
        '<div class="form-note">Only used to follow up if we need clarification. Never published.</div>'
        '</div>'
        '<div class="form-group">'
        '<label for="question">Your question</label>'
        '<textarea id="question" name="question" '
        'placeholder="The more specific the better. What do you actually want to know?"></textarea>'
        '<div class="form-note">Best questions are specific and narrative. '
        '"Which teams benefited most from the transfer portal this year?" '
        'beats "Is the transfer portal good?"</div>'
        '</div>'
        '<button type="submit" class="btn-submit">Submit Question</button>'
        '</form>'
        '<p class="mailto-note">'
        '&dagger; This form currently opens your email client (mailto). '
        'A future sprint wires real email ingestion via Resend/Postmark. '
        'In the meantime, you can also email mailbag@cfbindex.local directly.'
        '</p>'
        '</div>'
        '</div>'
    )

    submit_dir = output_dir / "submit"
    submit_dir.mkdir(parents=True, exist_ok=True)
    page = _full_page_html("The Mailbag — Submit a Question", body)
    out_path = submit_dir / "index.html"
    out_path.write_text(page, encoding="utf-8")
    log.info("mailbag.renderer: wrote submit form %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def render_all(
    *,
    edition_slug: str | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    """Render edition(s), submit form, and archive.

    If edition_slug is given, renders only that edition (plus the index if
    it's the most recent published edition). Otherwise renders all published
    editions.
    """
    output_root = output_root or (Path(__file__).resolve().parents[3] / "output" / "site" / "mailbag")
    output_root.mkdir(parents=True, exist_ok=True)

    with db_conn() as conn:
        all_editions = list_recent_editions(conn, limit=30)

    published = [e for e in all_editions if e.get("status") == "published"]
    draft = [e for e in all_editions if e.get("status") != "published"]

    slugs_to_render: list[str]
    if edition_slug:
        slugs_to_render = [edition_slug]
    else:
        slugs_to_render = [e["edition_slug"] for e in all_editions]

    rendered_pages: list[str] = []

    for slug in slugs_to_render:
        path = render_edition_page(slug, output_dir=output_root)
        if path:
            rendered_pages.append(str(path))

    # Render index.html = most recent published edition
    most_recent_published = published[0]["edition_slug"] if published else (
        all_editions[0]["edition_slug"] if all_editions else None
    )
    index_path: Path | None = None
    if most_recent_published and (not edition_slug or edition_slug == most_recent_published):
        index_path = render_edition_page(
            most_recent_published,
            output_dir=output_root,
            is_index=True,
        )

    archive_path = render_archive_page(output_root)
    submit_path = render_submit_page(output_root)

    return {
        "output_root": str(output_root),
        "edition_pages": rendered_pages,
        "index": str(index_path) if index_path else None,
        "archive": str(archive_path),
        "submit": str(submit_path),
        "published_count": len(published),
        "draft_count": len(draft),
    }
