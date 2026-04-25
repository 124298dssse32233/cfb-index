"""Article-page renderer for cover essays + feature pieces.

Each feature renders to ``output/site/editions/<slug>/<feature-slug>/index.html``
as a self-contained HTML document. Body markdown is rendered with a
deliberately-minimal Markdown subset (paragraphs, blockquotes, ``> `` lines,
italic/bold, em-dashes, smart-quotes left to the source).

A full Markdown library is intentionally avoided — the body corpus is
edited prose, not user-supplied content; the tradeoff is readability of
the renderer itself.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from cfb_rankings.db import Database

from .data import (
    Edition, EditionFeature,
    fetch_edition, fetch_edition_features,
)


_ARTICLE_CSS = """
*, *::before, *::after { box-sizing: border-box; }
:root {
  --ink: #1a1a1a; --paper: #f6f1e6; --paper-dim: #ece6d6;
  --rule: #1a1a1a; --rule-soft: rgba(26,26,26,0.18);
  --gold: #c9a24a; --navy: #1f2c4d; --muted: #7a7a7a;
  --serif: 'Source Serif Pro', 'Georgia', 'Times New Roman', serif;
  --sans: 'Inter', 'Helvetica Neue', system-ui, sans-serif;
}
html, body { margin:0; padding:0; background:var(--paper); color:var(--ink);
  font-family:var(--serif); font-size:18px; line-height:1.65; }
.page { max-width: 760px; margin: 0 auto; padding: 64px 32px 96px; }
.eyebrow { font-family:var(--sans); font-size:11px; font-weight:600;
  letter-spacing:0.18em; text-transform:uppercase; color:var(--muted); }
a.up { display:inline-block; margin-bottom:32px; font-family:var(--sans);
  font-size:11px; font-weight:700; letter-spacing:0.16em; text-transform:uppercase;
  color:var(--gold); border-bottom: 2px solid var(--gold); padding-bottom: 2px; }
.kind-pill { display:inline-block; font-family:var(--sans); font-size:10px;
  font-weight:700; letter-spacing:0.18em; text-transform:uppercase;
  background:var(--ink); color:var(--paper); padding:4px 10px; margin-bottom:16px; }
h1.article-title { font-family:var(--serif); font-size:56px; line-height:1.1;
  font-weight:700; margin: 0 0 24px; }
.dek { font-family:var(--serif); font-size:22px; font-style:italic;
  line-height:1.45; margin: 0 0 32px; color:var(--ink); }
.byline-row { display:flex; gap:24px; align-items:baseline;
  border-top:1px solid var(--rule); border-bottom:1px solid var(--rule);
  padding:16px 0; margin-bottom:48px; font-family:var(--sans);
  font-size:11px; font-weight:700; letter-spacing:0.16em;
  text-transform:uppercase; color:var(--ink); }
.body p { margin: 0 0 24px; }
.body p:first-of-type::first-letter { font-family:var(--serif);
  font-size:72px; font-weight:700; float:left; line-height:0.9;
  margin: 4px 12px 0 0; color:var(--gold); }
.body blockquote { border-left: 3px solid var(--gold); padding: 8px 24px;
  margin: 32px 0; font-style: italic; color: var(--ink); background: var(--paper-dim); }
.body em { font-style: italic; }
.body strong { font-weight: 700; }
hr { border:0; height:1px; background:var(--rule); margin:48px 0; }
@media (max-width:768px) {
  .page { padding: 32px 24px 64px; }
  h1.article-title { font-size: 40px; }
  .dek { font-size: 18px; }
}
"""


def render_articles_for_edition(db: Database, edition_slug: str) -> list[Path]:
    edition = fetch_edition(db, edition_slug)
    if edition is None:
        return []
    features = fetch_edition_features(db, edition_slug)
    repo_root = Path(__file__).resolve().parents[3]
    out_dir = repo_root / "output" / "site" / "editions" / edition_slug
    paths: list[Path] = []
    for f in features:
        feature_slug = _slugify(f.title)
        target = out_dir / feature_slug / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_render_article(edition, f), encoding="utf-8")
        paths.append(target)
    return paths


def _render_article(edition: Edition, feature: EditionFeature) -> str:
    body_html = _markdown_to_html(feature.body_markdown)
    kind_label = feature.feature_kind.replace("_", " ").upper()
    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(feature.title)} · CFB Index</title>
<meta name="description" content="{html.escape(feature.dek)}">
<style>{_ARTICLE_CSS}</style>
</head><body>
<div class="page">
  <a class="up" href="/">← {html.escape(edition.theme_title.upper())}</a>
  <span class="kind-pill">{html.escape(kind_label)}</span>
  <h1 class="article-title">{html.escape(feature.title)}</h1>
  <p class="dek">{html.escape(feature.dek)}</p>
  <div class="byline-row">
    <span>{html.escape(feature.byline)}</span>
    <span>{feature.read_time_minutes} MIN READ</span>
    <span style="margin-left:auto;color:var(--muted);">VOL. I · NO. {edition.edition_number}</span>
  </div>
  <article class="body">{body_html}</article>
</div>
</body></html>"""


def _markdown_to_html(md: str) -> str:
    lines = md.split("\n")
    out: list[str] = []
    para_buf: list[str] = []
    blockquote_buf: list[str] = []

    def flush_para() -> None:
        if para_buf:
            text = " ".join(para_buf)
            out.append(f"<p>{_inline(text)}</p>")
            para_buf.clear()

    def flush_quote() -> None:
        if blockquote_buf:
            text = "<br>".join(_inline(s) for s in blockquote_buf)
            out.append(f"<blockquote>{text}</blockquote>")
            blockquote_buf.clear()

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush_para()
            flush_quote()
            continue
        if line.lstrip().startswith("> "):
            flush_para()
            blockquote_buf.append(line.lstrip()[2:])
            continue
        flush_quote()
        para_buf.append(line.strip())
    flush_para()
    flush_quote()
    return "".join(out)


_ITALIC = re.compile(r"\*([^*\n]+)\*")
_BOLD = re.compile(r"\*\*([^*\n]+)\*\*")


def _inline(s: str) -> str:
    s = html.escape(s)
    s = _BOLD.sub(r"<strong>\1</strong>", s)
    s = _ITALIC.sub(r"<em>\1</em>", s)
    return s


def _slugify(text: str) -> str:
    out = "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")
    while "--" in out:
        out = out.replace("--", "-")
    return out
