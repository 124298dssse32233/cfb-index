"""Editions archive page renderer.

Writes ``output/site/editions/index.html`` — the landing page for the
``/editions/`` directory, listing every published edition with its
theme, dek, publish date, and links to each feature.

Multiple surfaces link to ``/editions/`` (the active homepage's nav and
footer, the mailbag and wire templates). Until this renderer landed,
those links 404'd.

Stylistically mirrors ``homepage_renderer.py`` — serif headlines on the
beige "paper" background, gold rules, Roman numerals for masthead
chrome — so the archive feels like a coherent issue catalog, not a
bare-bones index.

CLI: ``python manage.py build-editions-archive``. Also called from
``daily_ingest.ps1`` after ``build-site``.
"""
from __future__ import annotations

import html
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from cfb_rankings.db import Database

from .data import (
    Edition,
    EditionFeature,
    fetch_edition_features,
    list_editions,
)


_OUTPUT_PATH = (
    Path(__file__).resolve().parents[3]
    / "output" / "site" / "editions" / "index.html"
)

_ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
          "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]


_ARCHIVE_CSS = """
*, *::before, *::after { box-sizing: border-box; }
:root {
  --ink: #1a1a1a;
  --paper: #f6f1e6;
  --paper-dim: #ece6d6;
  --rule: #1a1a1a;
  --rule-soft: rgba(26, 26, 26, 0.18);
  --gold: #c9a24a;
  --navy: #1f2c4d;
  --muted: #7a7a7a;
  --serif: 'Source Serif Pro', 'Georgia', 'Times New Roman', serif;
  --sans: 'Inter', 'Helvetica Neue', system-ui, sans-serif;
}
html, body { margin: 0; padding: 0; background: var(--paper); color: var(--ink);
  font-family: var(--serif); font-size: 17px; line-height: 1.65; }
.page { max-width: 1140px; margin: 0 auto; padding: 0 32px; }
hr.rule { border: 0; height: 1px; background: var(--rule); margin: 0; }
hr.rule.gold { background: var(--gold); height: 3px; }
hr.rule.soft { background: var(--rule-soft); }

/* Masthead */
.masthead { padding: 32px 0 16px; }
.masthead .chrome { display: flex; justify-content: space-between;
  font-family: var(--sans); font-size: 10px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--ink);
  padding-bottom: 16px; }
.masthead .brand-row { display: flex; align-items: baseline;
  padding: 28px 0; gap: 48px; }
.masthead .brand { font-family: var(--serif); font-size: 56px; font-weight: 700;
  letter-spacing: -0.02em; }
.masthead .brand .slash { color: var(--gold); margin: 0 2px; }
.masthead .nav { margin-left: auto; display: flex; gap: 28px;
  font-family: var(--sans); font-size: 12px; font-weight: 600;
  letter-spacing: 0.16em; text-transform: uppercase; }
.masthead .nav a { color: var(--ink); text-decoration: none;
  border-bottom: 1px solid transparent; padding-bottom: 2px; }
.masthead .nav a:hover { border-bottom-color: var(--gold); }
.masthead .nav a.current { border-bottom-color: var(--gold); color: var(--ink); }

/* Hero */
.hero { padding: 56px 0 32px; }
.hero .eyebrow { font-family: var(--sans); font-size: 11px; font-weight: 700;
  letter-spacing: 0.24em; text-transform: uppercase; color: var(--muted);
  margin-bottom: 12px; }
.hero h1 { font-family: var(--serif); font-size: 88px; line-height: 1;
  font-weight: 700; margin: 0; letter-spacing: -0.01em; }
.hero p.lede { font-family: var(--serif); font-size: 22px; font-style: italic;
  line-height: 1.45; max-width: 720px; margin: 24px 0 0; color: var(--ink); }

/* Issue grid */
.issues { padding: 48px 0 96px; display: grid; gap: 64px; }
.issue { display: grid; grid-template-columns: 220px 1fr; gap: 48px;
  align-items: start; border-top: 1px solid var(--rule);
  padding-top: 40px; }
.issue:first-of-type { border-top: 3px solid var(--gold); padding-top: 32px; }
.issue .roman-col { text-align: center; }
.issue .roman-col .roman { font-family: var(--serif); font-size: 96px;
  font-weight: 600; line-height: 1; color: var(--ink); }
.issue .roman-col .vol { font-family: var(--sans); font-size: 11px;
  font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--muted); margin-top: 12px; display: block; }
.issue .roman-col .date { font-family: var(--sans); font-size: 11px;
  font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--ink); margin-top: 6px; display: block; }
.issue .roman-col .status-draft { display: inline-block; margin-top: 12px;
  font-family: var(--sans); font-size: 10px; font-weight: 700;
  letter-spacing: 0.16em; text-transform: uppercase; color: var(--paper);
  background: var(--muted); padding: 3px 8px; }

.issue .body-col h2 { font-family: var(--serif); font-size: 44px;
  font-weight: 700; line-height: 1.1; margin: 0 0 16px; }
.issue .body-col h2 a { color: var(--ink); text-decoration: none; }
.issue .body-col h2 a:hover { color: var(--navy); }
.issue .body-col .dek { font-family: var(--serif); font-size: 20px;
  font-style: italic; line-height: 1.5; margin: 0 0 24px; color: var(--ink); }
.issue .body-col .cta { display: inline-block; font-family: var(--sans);
  font-size: 11px; font-weight: 700; letter-spacing: 0.18em;
  text-transform: uppercase; color: var(--gold);
  border-bottom: 2px solid var(--gold); padding-bottom: 4px;
  margin-bottom: 28px; text-decoration: none; }
.issue .body-col .also-label { font-family: var(--sans); font-size: 10px;
  font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--muted); margin: 24px 0 12px; }
.issue .body-col ul.features { list-style: none; padding: 0; margin: 0;
  display: grid; gap: 8px; }
.issue .body-col ul.features li { display: grid;
  grid-template-columns: 32px 1fr; gap: 12px; align-items: baseline;
  padding: 10px 0; border-top: 1px solid var(--rule-soft); }
.issue .body-col ul.features li:first-of-type { border-top: 0; }
.issue .body-col ul.features .num { font-family: var(--serif); font-size: 16px;
  font-weight: 600; color: var(--gold); }
.issue .body-col ul.features .title { font-family: var(--serif); font-size: 16px;
  font-weight: 600; line-height: 1.35; }
.issue .body-col ul.features .title a { color: var(--ink); text-decoration: none; }
.issue .body-col ul.features .title a:hover { text-decoration: underline; }
.issue .body-col ul.features .kind { font-family: var(--sans); font-size: 10px;
  font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--muted); margin-left: 8px; }

/* Empty state */
.empty { padding: 96px 0; text-align: center; color: var(--muted); }
.empty h2 { font-family: var(--serif); font-size: 32px; color: var(--ink);
  margin-bottom: 16px; }

/* Footer */
.footer { background: var(--ink); color: var(--paper); padding: 64px 0 48px;
  margin-top: 32px; }
.footer .chrome { display: flex; justify-content: space-between;
  font-family: var(--sans); font-size: 10px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--paper);
  border-bottom: 1px solid var(--paper); padding-bottom: 24px;
  margin-bottom: 32px; }
.footer a { color: var(--paper); }
.footer .bottom { font-family: var(--sans); font-size: 10px;
  font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--paper); margin-top: 24px; }

@media (max-width: 768px) {
  .hero h1 { font-size: 56px; }
  .issue { grid-template-columns: 1fr; gap: 16px; }
  .issue .roman-col { display: flex; align-items: baseline; gap: 16px;
    text-align: left; }
  .issue .roman-col .roman { font-size: 48px; }
  .issue .body-col h2 { font-size: 32px; }
  .masthead .brand-row { flex-wrap: wrap; gap: 16px; }
  .masthead .nav { width: 100%; flex-wrap: wrap; gap: 16px; margin-left: 0; }
}
"""


def _slugify(text: str) -> str:
    cleaned = "".join(c if c.isalnum() else "-" for c in text.lower())
    return re.sub(r"-+", "-", cleaned).strip("-")


def _format_publish_date(d: date) -> str:
    # %-d is POSIX-only and breaks on Windows; format the day manually.
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def _entry_link_for(
    edition: Edition,
    features: list[EditionFeature],
) -> tuple[str, Optional[EditionFeature]]:
    """Pick the canonical entry-point feature for an edition.

    Preference order:
    1. The feature whose id matches edition.cover_essay_id (if set).
    2. The first feature with feature_kind == 'cover_essay'.
    3. The lowest-feature_order feature.
    """
    if edition.cover_essay_id is not None:
        for f in features:
            if f.id == edition.cover_essay_id:
                return _feature_url(edition, f), f
    for f in features:
        if (f.feature_kind or "").lower() == "cover_essay":
            return _feature_url(edition, f), f
    if features:
        ordered = sorted(features, key=lambda f: f.feature_order)
        return _feature_url(edition, ordered[0]), ordered[0]
    return f"/editions/{edition.edition_slug}/", None


def _feature_url(edition: Edition, feature: EditionFeature) -> str:
    return f"/editions/{edition.edition_slug}/{_slugify(feature.title)}/"


def _render_issue_block(
    edition: Edition,
    features: list[EditionFeature],
    cover_feature: Optional[EditionFeature],
    entry_url: str,
) -> str:
    vol = _ROMAN[edition.volume] if edition.volume < len(_ROMAN) else str(edition.volume)
    roman_num = (
        _ROMAN[edition.edition_number]
        if edition.edition_number < len(_ROMAN)
        else str(edition.edition_number)
    )
    secondary = [
        f for f in sorted(features, key=lambda f: f.feature_order)
        if cover_feature is None or f.id != cover_feature.id
    ]
    feature_rows = []
    for i, f in enumerate(secondary, start=1):
        kind_label = (f.feature_kind or "").replace("_", " ").upper()
        feature_rows.append(
            f"""
        <li>
          <span class="num">{i}.</span>
          <span class="title">
            <a href="{html.escape(_feature_url(edition, f))}">{html.escape(f.title)}</a>
            <span class="kind">{html.escape(kind_label)}</span>
          </span>
        </li>"""
        )
    also_block = (
        f"""
      <div class="also-label">Also in this issue</div>
      <ul class="features">{''.join(feature_rows)}</ul>"""
        if feature_rows
        else ""
    )
    cover_cta = (
        f"""<a class="cta" href="{html.escape(entry_url)}">Read the cover essay →</a>"""
        if cover_feature is not None
        else ""
    )
    status_pill = (
        ""
        if edition.status == "published"
        else f"""<span class="status-draft">{html.escape(edition.status.upper())}</span>"""
    )
    return f"""
  <article class="issue">
    <div class="roman-col">
      <div class="roman">{roman_num}</div>
      <span class="vol">Vol. {vol} · No. {edition.edition_number}</span>
      <span class="date">{html.escape(_format_publish_date(edition.publish_date))}</span>
      {status_pill}
    </div>
    <div class="body-col">
      <h2><a href="{html.escape(entry_url)}">{html.escape(edition.theme_title)}</a></h2>
      <p class="dek">{html.escape(edition.theme_dek)}</p>
      {cover_cta}
      {also_block}
    </div>
  </article>"""


def render_editions_archive_html(db: Database) -> str:
    editions = list_editions(db)  # already ordered publish_date desc
    issues_html: list[str] = []
    for edition in editions:
        features = fetch_edition_features(db, edition.edition_slug)
        entry_url, cover_feature = _entry_link_for(edition, features)
        issues_html.append(_render_issue_block(edition, features, cover_feature, entry_url))

    if not editions:
        body = """
      <section class="empty">
        <h2>No editions published yet.</h2>
        <p>Check back soon — the first issue ships Monday morning.</p>
      </section>"""
    else:
        body = f"""
    <section class="issues">{''.join(issues_html)}</section>"""

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Editions Archive · CFB Index</title>
  <meta name="description" content="Every weekly issue of the CFB Index — cover essays, features, and voices, archived in one place.">
  <style>{_ARCHIVE_CSS}</style>
</head>
<body>
  <header class="masthead">
    <div class="page">
      <div class="chrome">
        <span>THE EDITIONS ARCHIVE</span>
        <span>CFB · INDEX</span>
        <span>{len(editions)} {'ISSUE' if len(editions) == 1 else 'ISSUES'}</span>
      </div>
      <hr class="rule">
      <div class="brand-row">
        <div class="brand">CFB<span class="slash">/</span>INDEX</div>
        <nav class="nav">
          <a href="/rankings/">Rankings</a>
          <a href="/teams/">Teams</a>
          <a class="current" href="/editions/">Editions</a>
          <a href="/about-model/">How It Works</a>
        </nav>
      </div>
      <hr class="rule">
    </div>
  </header>

  <section class="hero">
    <div class="page">
      <div class="eyebrow">THE ARCHIVE</div>
      <h1>Every issue.</h1>
      <p class="lede">The CFB Index publishes a new edition every Monday — a
        cover essay, a cover viz, and five secondary features built around a
        single theme. Past issues live here in full.</p>
    </div>
  </section>

  <div class="page">{body}</div>

  <footer class="footer">
    <div class="page">
      <div class="chrome">
        <span>CFB · INDEX</span>
        <span>Editions Archive</span>
        <span>Generated {html.escape(generated_at)}</span>
      </div>
      <div class="bottom">
        <a href="/">Home</a> &nbsp;·&nbsp;
        <a href="/methodology/">Methodology</a> &nbsp;·&nbsp;
        <a href="/about-model/">How it works</a>
      </div>
    </div>
  </footer>
</body>
</html>
"""


def write_editions_archive(db: Database, output_path: Path | None = None) -> Path:
    target = output_path or _OUTPUT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_editions_archive_html(db), encoding="utf-8")
    return target


__all__ = ["render_editions_archive_html", "write_editions_archive"]
