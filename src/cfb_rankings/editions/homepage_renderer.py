"""Homepage v4 renderer — Sprint 9.

Renders ``output/site/index.html`` for the active edition per the Figma
node ``73:2`` design-of-record (frame: *Homepage v4 · Tease + Fan-Voice
+ Dumbbell*). Falls back gracefully when the active edition is missing
or when Wave 2 surfaces (Threads, Canon, Wire, Daily) have not shipped:
those sections render from ``stub_data/*.json``.

Per CLAUDE.md, ``reporting.py`` is monolith-protected; the integration
point is a ~5-line delegation hook in ``reporting.py``'s homepage write
path that calls ``render_homepage`` when an active edition exists, and
falls back to the legacy ``render_home_html`` otherwise.

Roman-numeral department layout:
    Masthead              (chrome rows + brand)
    Hero                  (theme + dek)
    I    Cover viz
    II   Cover essay TEASE
    III  Feature TOC (with numbered IV-VIII row entries)
    --   "The Running Departments" divider
    IX   The Daily strip          (stub data until Sprint 14)
    X    The Wire                 (stub data until Sprint 12)
    XI   Active Threads           (stub data until Sprint 10)
    XII  The Canon entry          (stub data until Sprint 11)
    XIII Voices behind this edition
    Footer
"""
from __future__ import annotations

import html
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database

from . import viz_templates
from .data import (
    Edition, EditionFeature, EditionVoice,
    fetch_active_edition, fetch_edition_features, fetch_edition_voices,
)


_ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
          "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]

_STUB_DIR = Path(__file__).resolve().parent / "stub_data"


# ----------------------- Live data fetchers -----------------------

def _fetch_threads_live(db: Database) -> dict[str, Any] | None:
    """Query storyline_threads + storyline_chapters for the Active Threads widget.

    Returns None if the table is empty (caller falls back to stub).
    """
    rows = db.query_all(
        "SELECT thread_slug, title, dek, chapter_count, last_chapter_at, started_at "
        "FROM storyline_threads WHERE status='active' "
        "ORDER BY last_chapter_at DESC"
    )
    if not rows:
        return None
    featured_row = rows[0]
    chaps = db.query_all(
        "SELECT title, dek FROM storyline_chapters "
        "WHERE thread_slug=:slug ORDER BY chapter_number DESC LIMIT 1",
        {"slug": featured_row["thread_slug"]},
    )
    chap = chaps[0] if chaps else {}
    featured: dict[str, Any] = {
        "slug": featured_row["thread_slug"],
        "title": featured_row["title"],
        "chapters": featured_row["chapter_count"],
        "thread_summary": featured_row["dek"],
        "latest_chapter_title": chap.get("title", ""),
        "latest_chapter_dek": chap.get("dek", ""),
        "starting_date": (featured_row["started_at"] or ""),
    }
    active = [
        {
            "slug": r["thread_slug"],
            "title": r["title"],
            "chapters": r["chapter_count"],
            "last_updated": (r["last_chapter_at"] or "")[:10],
        }
        for r in rows[1:]
    ]
    return {"featured": featured, "active": active}


def _fetch_canon_live(db: Database) -> dict[str, Any] | None:
    """Query canon_entries for The Canon widget.

    Rotates the featured entry weekly so the homepage always shows
    something different. Returns None if the table is empty.
    """
    total_rows = db.query_all("SELECT COUNT(*) AS n FROM canon_entries")
    total = (total_rows[0]["n"] if total_rows else 0)
    if not total:
        return None
    week = date.today().isocalendar()[1]
    offset = (week - 1) % total
    rows = db.query_all(
        "SELECT list_slug, rank, entity_kind, entity_slug, entity_display_name, "
        "era_label, summary_short, cohort_split_stat_rank, cohort_split_casual_rank, "
        "cohort_split_label, statline "
        "FROM canon_entries ORDER BY list_slug, rank LIMIT 1 OFFSET :offset",
        {"offset": offset},
    )
    if not rows:
        return None
    e = rows[0]
    kind = e["entity_kind"] or "player"
    category = kind.replace("_", " ").title()
    return {
        "entry": {
            "slug": e["entity_slug"] or "",
            "title": e["entity_display_name"] or "",
            "category": category,
            "era": e["era_label"] or "",
            "summary": e["summary_short"] or "",
            "cohort_divergence": {
                "stat_folks_rank": e["cohort_split_stat_rank"] or "—",
                "regular_fans_rank": e["cohort_split_casual_rank"] or "—",
                "gap_label": e["cohort_split_label"] or "",
                "discussion_starter": e["statline"] or "",
            },
        }
    }


def _fetch_wire_live(db: Database) -> dict[str, Any] | None:
    """Query wire_entries for The Wire widget.

    Returns the 8 most recent entries. Returns None if table is empty.
    """
    rows = db.query_all(
        "SELECT occurred_at, program_display, action, why_it_matters, impact_label "
        "FROM wire_entries ORDER BY occurred_at DESC LIMIT 8"
    )
    if not rows:
        return None

    def _when_label(ts: str) -> str:
        if not ts:
            return ""
        try:
            dt = datetime.strptime(ts[:10], "%Y-%m-%d")
            try:
                return dt.strftime("%b %#d")
            except ValueError:
                return dt.strftime("%b %-d")
        except Exception:
            return ts[:10]

    entries = [
        {
            "when": _when_label(r["occurred_at"]),
            "program": r["program_display"],
            "action": r["action"],
            "why": r["why_it_matters"],
            "impact": r["impact_label"],
        }
        for r in rows
    ]
    return {"entries": entries}


def render_homepage(db: Database, output_path: Path | None = None) -> Path | None:
    """Render the active edition's homepage to ``output_path``.

    Returns the path written, or ``None`` if no active edition exists
    (in which case the caller should fall back to the legacy renderer).
    """
    edition = fetch_active_edition(db)
    if edition is None:
        return None
    features = fetch_edition_features(db, edition.edition_slug)
    voices = fetch_edition_voices(db, edition.edition_slug)
    html_doc = _render_document(edition, features, voices, db=db)
    if output_path is None:
        repo_root = Path(__file__).resolve().parents[3]
        output_path = repo_root / "output" / "site" / "index.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_doc, encoding="utf-8")
    return output_path


def _render_document(edition: Edition, features: list[EditionFeature],
                     voices: list[EditionVoice],
                     db: Database | None = None) -> str:
    cover_essay = next((f for f in features if f.feature_kind == "cover_essay"), None)
    secondary = [f for f in features if f.feature_kind != "cover_essay"]

    if db is not None:
        threads_data = _fetch_threads_live(db) or _load_stub("threads.json")
        canon_data = _fetch_canon_live(db) or _load_stub("canon_featured.json")
        wire_data = _fetch_wire_live(db) or _load_stub("wire_seed.json")
    else:
        threads_data = _load_stub("threads.json")
        canon_data = _load_stub("canon_featured.json")
        wire_data = _load_stub("wire_seed.json")
    daily_data = _load_stub("daily_seed.json")  # Sprint 14 live source not yet available

    publish_dt = datetime.combine(edition.publish_date, datetime.min.time())
    # Windows-safe date formatting (no %-d on win32):
    try:
        publish_label = publish_dt.strftime("%A · %B %#d · %Y").upper()
    except ValueError:
        publish_label = publish_dt.strftime("%A · %B %d · %Y").upper()

    parts: list[str] = []
    parts.append(_render_head(edition))
    parts.append("<body>")
    parts.append(_render_masthead(edition, publish_label))
    parts.append(_render_hero(edition))
    parts.append(_render_cover_viz(edition))
    if cover_essay:
        parts.append(_render_cover_essay_tease(edition, cover_essay))
    parts.append(_render_feature_toc(secondary))
    parts.append(_render_running_departments_divider())
    parts.append(_render_the_daily(daily_data))
    parts.append(_render_the_wire(wire_data))
    parts.append(_render_active_threads(threads_data))
    parts.append(_render_the_canon(canon_data))
    parts.append(_render_voices(voices))
    parts.append(_render_footer(edition))
    parts.append("</body></html>")
    return "".join(parts)


# ----------------------- <head> + CSS -----------------------

_INLINE_CSS = """
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
  --serif: 'Source Serif Pro', 'Georgia', 'Times New Roman', serif;
  --sans: 'Inter', 'Helvetica Neue', -apple-system, system-ui, sans-serif;
}
html, body { margin: 0; padding: 0; background: var(--paper); color: var(--ink);
  font-family: var(--serif); font-size: 17px; line-height: 1.55; }
.page { max-width: 1280px; margin: 0 auto; padding: 0 64px; }
.eyebrow { font-family: var(--sans); font-size: 11px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--ink); }
.eyebrow.muted { color: var(--muted); }
.rule { border: 0; height: 1px; background: var(--rule); margin: 0; }
.rule.soft { background: var(--rule-soft); }
.rule.gold { background: var(--gold); height: 4px; width: 60px; border: 0; }
a { color: inherit; text-decoration: none; }
a.cta { font-family: var(--sans); font-size: 12px; font-weight: 700;
  letter-spacing: 0.16em; text-transform: uppercase; color: var(--gold);
  border-bottom: 2px solid var(--gold); padding-bottom: 2px; }
a.text-link { border-bottom: 1px dotted currentColor; }

/* Masthead */
.chrome { font-family: var(--sans); font-size: 11px; font-weight: 600;
  letter-spacing: 0.16em; text-transform: uppercase;
  display: flex; justify-content: space-between; padding: 12px 0;
  color: var(--ink); }
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
.hero { padding: 96px 0 80px; }
.roman-big { font-family: var(--serif); font-size: 72px; line-height: 1;
  font-weight: 600; color: var(--ink); margin: 0 0 16px; }
.hero .eyebrow { margin-bottom: 24px; }
.theme-title { font-family: var(--serif); font-size: 128px; line-height: 0.95;
  font-weight: 700; letter-spacing: -0.02em; margin: 0 0 32px;
  color: var(--ink); }
.theme-dek { font-family: var(--serif); font-size: 24px; font-style: italic;
  line-height: 1.4; max-width: 720px; margin: 0 0 0 320px; color: var(--ink); }

/* Department block (I, II, III, ...) */
.dept { padding: 64px 0; border-top: 1px solid var(--rule); }
.dept-head { display: flex; align-items: baseline; gap: 24px;
  margin-bottom: 32px; }
.dept .roman { font-family: var(--serif); font-size: 36px; font-weight: 600;
  color: var(--ink); width: 72px; }
.dept .label { font-family: var(--sans); font-size: 11px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--ink); }
.dept .meta { font-family: var(--sans); font-size: 11px; font-weight: 600;
  letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted);
  margin-left: auto; }
.dept .badge-live { background: var(--gold); color: var(--ink);
  padding: 3px 8px; font-size: 10px; letter-spacing: 0.18em;
  font-weight: 700; }

/* Cover essay tease */
.tease-title { font-family: var(--serif); font-size: 64px; line-height: 1.05;
  font-weight: 700; margin: 0 0 24px; max-width: 980px; color: var(--ink); }
.tease-dek { font-family: var(--serif); font-size: 24px; font-style: italic;
  line-height: 1.45; max-width: 820px; margin: 0 0 32px; color: var(--ink); }
.tease-byline { font-family: var(--sans); font-size: 11px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted);
  margin-bottom: 32px; }

/* Feature TOC */
.toc-row { display: grid; grid-template-columns: 80px 1fr 200px;
  align-items: baseline; gap: 24px; padding: 28px 0;
  border-top: 1px solid var(--rule-soft); }
.toc-row:first-of-type { border-top: 0; }
.toc-row .toc-roman { font-family: var(--serif); font-size: 32px;
  font-weight: 600; color: var(--ink); }
.toc-row .toc-title { font-family: var(--serif); font-size: 28px;
  font-weight: 700; line-height: 1.2; margin-bottom: 8px; }
.toc-row .toc-dek { font-family: var(--serif); font-size: 16px;
  font-style: italic; color: var(--ink); line-height: 1.45; max-width: 720px; }
.toc-row .toc-meta { font-family: var(--sans); font-size: 11px;
  font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--muted); text-align: right; line-height: 1.6; }

/* Running departments */
.running-divider { padding: 80px 0 32px; }
.running-divider .label { font-family: var(--sans); font-size: 14px;
  font-weight: 700; letter-spacing: 0.32em; text-transform: uppercase;
  color: var(--ink); margin-bottom: 24px; }

/* The Daily */
.daily-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 64px; }
.daily-takes ol { list-style: none; padding: 0; margin: 0; counter-reset: take; }
.daily-takes li { counter-increment: take; padding: 18px 0;
  border-top: 1px solid var(--rule-soft); display: grid;
  grid-template-columns: 48px 1fr; gap: 16px; }
.daily-takes li::before { content: counter(take); font-family: var(--serif);
  font-size: 32px; font-weight: 600; color: var(--gold); line-height: 1; }
.daily-takes li:first-child { border-top: 0; }
.daily-takes h3 { font-family: var(--serif); font-size: 22px; font-weight: 700;
  margin: 0 0 8px; line-height: 1.25; }
.daily-takes p { font-family: var(--serif); font-size: 16px; margin: 0;
  line-height: 1.5; color: var(--ink); }
.daily-archive .archive-row { display: grid;
  grid-template-columns: 64px 1fr; gap: 12px; padding: 12px 0;
  border-top: 1px solid var(--rule-soft); }
.daily-archive .archive-row:first-of-type { border-top: 0; }
.daily-archive .archive-date { font-family: var(--sans); font-size: 10px;
  font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--muted); }
.daily-archive .archive-title { font-family: var(--serif); font-size: 15px;
  font-weight: 600; line-height: 1.3; }
.daily-archive .archive-summary { font-family: var(--serif); font-size: 13px;
  font-style: italic; color: var(--muted); line-height: 1.45; margin-top: 2px; }

/* The Wire */
.wire-table { width: 100%; border-collapse: collapse; font-family: var(--sans);
  font-size: 13px; }
.wire-table th { font-size: 10px; font-weight: 700; letter-spacing: 0.18em;
  text-transform: uppercase; color: var(--muted); text-align: left;
  padding: 12px 16px 12px 0; border-bottom: 1px solid var(--rule); }
.wire-table td { padding: 14px 16px 14px 0; border-bottom: 1px solid var(--rule-soft);
  vertical-align: top; }
.wire-table .when { font-weight: 700; white-space: nowrap; color: var(--muted); }
.wire-table .program { font-weight: 700; color: var(--ink); }
.wire-table .why { font-family: var(--serif); font-style: italic;
  color: var(--ink); }
.wire-table .impact { font-weight: 700; text-align: right; color: var(--gold); }

/* Active Threads */
.threads-grid { display: grid; grid-template-columns: 740px 1fr; gap: 48px; }
.thread-featured h3 { font-family: var(--serif); font-size: 32px; font-weight: 700;
  margin: 0 0 12px; line-height: 1.2; }
.thread-featured .summary { font-family: var(--serif); font-size: 18px;
  font-style: italic; line-height: 1.5; margin-bottom: 24px; }
.thread-featured .latest-chapter { padding: 16px 20px; background: var(--paper-dim);
  border-left: 4px solid var(--gold); }
.thread-featured .latest-chapter .chapter-eyebrow { font-family: var(--sans);
  font-size: 10px; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--muted); margin-bottom: 4px; }
.thread-featured .latest-chapter .chapter-title { font-family: var(--serif);
  font-size: 18px; font-weight: 700; margin-bottom: 4px; }
.thread-featured .latest-chapter .chapter-dek { font-family: var(--serif);
  font-size: 15px; font-style: italic; color: var(--ink); }
.thread-list .thread-row { padding: 14px 0; border-top: 1px solid var(--rule-soft);
  display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: baseline; }
.thread-list .thread-row:first-of-type { border-top: 0; }
.thread-list .thread-name { font-family: var(--serif); font-size: 16px; font-weight: 600; }
.thread-list .chapters { font-family: var(--sans); font-size: 11px; font-weight: 700;
  letter-spacing: 0.14em; text-transform: uppercase; color: var(--gold); }
.thread-list .last-updated { font-family: var(--sans); font-size: 10px; color: var(--muted);
  letter-spacing: 0.14em; text-transform: uppercase; }

/* The Canon */
.canon-grid { display: grid; grid-template-columns: 1.4fr 1fr; gap: 64px; align-items: start; }
.canon-entry .category-pill { display: inline-block; font-family: var(--sans);
  font-size: 10px; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase;
  background: var(--ink); color: var(--paper); padding: 4px 10px; margin-bottom: 16px; }
.canon-entry .era { font-family: var(--sans); font-size: 11px; color: var(--muted);
  letter-spacing: 0.16em; text-transform: uppercase; margin-bottom: 8px; }
.canon-entry h3 { font-family: var(--serif); font-size: 36px; font-weight: 700;
  margin: 0 0 16px; line-height: 1.15; }
.canon-entry .summary { font-family: var(--serif); font-size: 17px; line-height: 1.6;
  margin-bottom: 20px; }
.canon-divergence .divergence-eyebrow { font-family: var(--sans); font-size: 10px;
  font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--muted); margin-bottom: 12px; }
.canon-divergence .ranks { display: flex; gap: 32px; margin-bottom: 16px; }
.canon-divergence .rank-block { text-align: left; }
.canon-divergence .rank-label { font-family: var(--sans); font-size: 10px;
  letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted); }
.canon-divergence .rank-num { font-family: var(--serif); font-size: 56px;
  font-weight: 700; line-height: 1; }
.canon-divergence .rank-num.fans { color: var(--gold); }
.canon-divergence .rank-num.stats { color: var(--navy); }
.canon-divergence .gap-label { font-family: var(--serif); font-size: 14px;
  font-style: italic; color: var(--ink); margin-bottom: 12px; }
.canon-divergence .starter { font-family: var(--serif); font-size: 16px;
  font-style: italic; color: var(--ink); border-left: 3px solid var(--gold);
  padding-left: 16px; line-height: 1.45; }

/* Voices */
.voices-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 48px; }
.voice-card .voice-name { font-family: var(--serif); font-size: 22px; font-weight: 700;
  margin-bottom: 4px; }
.voice-card .voice-role { font-family: var(--sans); font-size: 10px;
  font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--muted); margin-bottom: 12px; }
.voice-card .voice-pill { display: inline-block; font-family: var(--sans);
  font-size: 11px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;
  background: var(--gold); color: var(--ink); padding: 4px 10px; margin-bottom: 16px; }
.voice-card .voice-bio { font-family: var(--serif); font-size: 15px;
  line-height: 1.5; margin-bottom: 16px; }
.voice-card .takes-tracked { font-family: var(--sans); font-size: 10px;
  letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); }

/* Footer */
.footer { background: var(--ink); color: var(--paper); padding: 64px 0 48px;
  margin-top: 96px; }
.footer .chrome { color: var(--paper); border-bottom: 1px solid var(--paper);
  padding-bottom: 24px; margin-bottom: 32px; }
.footer-cols { display: grid; grid-template-columns: repeat(4, 1fr); gap: 48px; }
.footer-col h4 { font-family: var(--sans); font-size: 11px;
  font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--gold); margin: 0 0 16px; }
.footer-col ul { list-style: none; padding: 0; margin: 0; }
.footer-col li { font-family: var(--serif); font-size: 14px; line-height: 1.8;
  color: var(--paper); }
.footer .bottom-chrome { font-family: var(--sans); font-size: 10px;
  letter-spacing: 0.16em; text-transform: uppercase; color: var(--paper);
  border-top: 1px solid var(--paper); padding-top: 24px; margin-top: 48px;
  display: flex; justify-content: space-between; }

/* Cover viz container */
.viz-container { max-width: 100%; margin: 0 auto; }
.viz-container svg { display: block; max-width: 100%; height: auto; }

@media (max-width: 768px) {
  .page { padding: 0 24px; }
  .theme-title { font-size: 64px; }
  .theme-dek { font-size: 18px; margin-left: 0; }
  .roman-big { font-size: 48px; }
  .tease-title { font-size: 38px; }
  .tease-dek { font-size: 18px; }
  .toc-row { grid-template-columns: 56px 1fr; }
  .toc-row .toc-meta { display: none; }
  .toc-row .toc-roman { font-size: 24px; }
  .toc-row .toc-title { font-size: 22px; }
  .daily-grid { grid-template-columns: 1fr; gap: 32px; }
  .threads-grid { grid-template-columns: 1fr; gap: 32px; }
  .canon-grid { grid-template-columns: 1fr; gap: 32px; }
  .voices-grid { grid-template-columns: 1fr; gap: 32px; }
  .footer-cols { grid-template-columns: repeat(2, 1fr); }
  .wire-table th:nth-child(4), .wire-table td:nth-child(4) { display: none; }
  .nav { display: none; }
  .dept .roman { width: 48px; font-size: 24px; }
  .dept .meta { display: none; }
}
"""


def _render_head(edition: Edition) -> str:
    title = html.escape(f"CFB Index · {edition.theme_title}")
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{html.escape(edition.theme_dek)}">
<style>{_INLINE_CSS}</style>
</head>"""


# ----------------------- Sections -----------------------

def _render_masthead(edition: Edition, publish_label: str) -> str:
    vol = _ROMAN[edition.volume] if edition.volume < len(_ROMAN) else str(edition.volume)
    publish_time = (edition.published_at_utc or "").split(" ")[1][:5] if edition.published_at_utc else "06:00"
    return f"""
<header class="masthead">
  <div class="page">
    <div class="chrome">
      <span>VOL. {vol} · NO. {edition.edition_number}</span>
      <span>{publish_label}</span>
      <span>PUBLISHED {publish_time} ET</span>
    </div>
    <hr class="rule">
    <div class="brand-row">
      <div class="brand">CFB<span class="slash">/</span>INDEX</div>
      <nav class="nav">
        <a href="/rankings/">Rankings</a>
        <a href="/teams/">Teams</a>
        <a href="/editions/">Editions</a>
        <a href="/about-model/">How It Works</a>
      </nav>
    </div>
    <hr class="rule">
  </div>
</header>"""


def _render_hero(edition: Edition) -> str:
    roman = _ROMAN[edition.edition_number] if edition.edition_number < len(_ROMAN) else str(edition.edition_number)
    return f"""
<section class="hero">
  <div class="page">
    <div class="roman-big">{roman}</div>
    <hr class="rule gold">
    <div class="eyebrow" style="margin-top:24px;">THIS WEEK'S COVER · THE OFFSEASON ISSUE</div>
    <h1 class="theme-title">{html.escape(edition.theme_title)}</h1>
    <p class="theme-dek">{html.escape(edition.theme_dek)}</p>
  </div>
</section>"""


def _render_cover_viz(edition: Edition) -> str:
    svg = viz_templates.render(edition.cover_viz_kind, edition.cover_viz_data)
    kind_label = edition.cover_viz_kind.replace("_", " ").upper()
    source = html.escape(edition.cover_viz_data.get("source", ""))
    return f"""
<section class="dept">
  <div class="page">
    <div class="dept-head">
      <span class="roman">I.</span>
      <span class="label">THE COVER · {html.escape(kind_label)}</span>
      <span class="meta">{source}</span>
    </div>
    <div class="viz-container">{svg}</div>
  </div>
</section>"""


def _render_cover_essay_tease(edition: Edition, essay: EditionFeature) -> str:
    return f"""
<section class="dept">
  <div class="page">
    <div class="dept-head">
      <span class="roman">II.</span>
      <span class="label">THE COVER ESSAY · {essay.read_time_minutes} MIN READ</span>
      <span class="meta">{html.escape(essay.byline)}</span>
    </div>
    <h2 class="tease-title">{html.escape(essay.title)}</h2>
    <p class="tease-dek">{html.escape(essay.dek)}</p>
    <a class="cta" href="/editions/{edition.edition_slug}/{_slugify(essay.title)}/">READ THE COVER ESSAY →</a>
  </div>
</section>"""


def _render_feature_toc(secondary: list[EditionFeature]) -> str:
    rows = []
    # Roman numerals start at IV (since I=cover viz, II=essay, III=this section).
    for i, f in enumerate(secondary):
        roman = _ROMAN[i + 4] if (i + 4) < len(_ROMAN) else str(i + 4)
        rows.append(f"""
    <div class="toc-row">
      <div class="toc-roman">{roman}.</div>
      <div>
        <div class="toc-title">{html.escape(f.title)}</div>
        <div class="toc-dek">{html.escape(f.dek)}</div>
      </div>
      <div class="toc-meta">
        {f.read_time_minutes} MIN READ<br>{html.escape(f.byline)}
      </div>
    </div>""")
    return f"""
<section class="dept">
  <div class="page">
    <div class="dept-head">
      <span class="roman">III.</span>
      <span class="label">ALSO IN THIS ISSUE</span>
    </div>
    {''.join(rows)}
  </div>
</section>"""


def _render_running_departments_divider() -> str:
    return """
<section class="running-divider">
  <div class="page">
    <hr class="rule">
    <div class="label" style="margin-top:24px;">THE RUNNING DEPARTMENTS</div>
    <hr class="rule soft">
  </div>
</section>"""


def _render_the_daily(daily: dict[str, Any]) -> str:
    today = daily.get("today") or {}
    archive = daily.get("archive") or []
    takes_html = "".join(
        f"""<li><div></div><div>
          <h3>{html.escape(t.get('headline', ''))}</h3>
          <p>{html.escape(t.get('body', ''))}</p>
        </div></li>"""
        for t in (today.get("takes") or [])
    )
    archive_html = "".join(
        f"""<div class="archive-row">
          <div class="archive-date">{html.escape(a.get('date_label', ''))}</div>
          <div>
            <div class="archive-title">{html.escape(a.get('title', ''))}</div>
            <div class="archive-summary">{html.escape(a.get('summary', ''))}</div>
          </div>
        </div>"""
        for a in archive
    )
    return f"""
<section class="dept">
  <div class="page">
    <div class="dept-head">
      <span class="roman">IX.</span>
      <span class="label">THE DAILY</span>
      <span class="badge-live">LIVE</span>
      <span class="meta">{html.escape(today.get('date_label', ''))}</span>
    </div>
    <div class="daily-grid">
      <div class="daily-takes">
        <h2 style="font-size:36px;margin:0 0 24px;font-weight:700;">{html.escape(today.get('title', ''))}</h2>
        <ol>{takes_html}</ol>
      </div>
      <aside class="daily-archive">
        <div class="eyebrow muted" style="margin-bottom:16px;">LAST FIVE DAYS</div>
        {archive_html}
      </aside>
    </div>
    <p class="eyebrow muted" style="margin-top:32px;">
      Stub data until Sprint 14 ships <em>The Daily</em>'s live pipeline.
    </p>
  </div>
</section>"""


def _render_the_wire(wire: dict[str, Any]) -> str:
    rows = "".join(
        f"""<tr>
          <td class="when">{html.escape(e.get('when', ''))}</td>
          <td class="program">{html.escape(e.get('program', ''))}</td>
          <td>{html.escape(e.get('action', ''))}</td>
          <td class="why">{html.escape(e.get('why', ''))}</td>
          <td class="impact">{html.escape(e.get('impact', ''))}</td>
        </tr>"""
        for e in (wire.get("entries") or [])
    )
    return f"""
<section class="dept">
  <div class="page">
    <div class="dept-head">
      <span class="roman">X.</span>
      <span class="label">THE WIRE</span>
      <span class="meta">UPDATED CONTINUOUSLY · LIVE</span>
    </div>
    <table class="wire-table">
      <thead><tr>
        <th>WHEN</th><th>PROGRAM</th><th>ACTION</th><th>WHY IT MATTERS</th><th>IMPACT</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</section>"""


def _render_active_threads(threads: dict[str, Any]) -> str:
    f = threads.get("featured") or {}
    active = threads.get("active") or []
    total_count = len(active) + (1 if f else 0)
    list_html = "".join(
        f"""<div class="thread-row">
          <div>
            <div class="thread-name">{html.escape(t.get('title', ''))}</div>
            <div class="last-updated">UPDATED {html.escape(t.get('last_updated', ''))}</div>
          </div>
          <div class="chapters">{t.get('chapters', 0)} CH.</div>
        </div>"""
        for t in active
    )
    return f"""
<section class="dept">
  <div class="page">
    <div class="dept-head">
      <span class="roman">XI.</span>
      <span class="label">ACTIVE THREADS</span>
      <span class="meta">LIVE · {total_count} ACTIVE</span>
    </div>
    <div class="threads-grid">
      <article class="thread-featured">
        <div class="eyebrow muted" style="margin-bottom:8px;">FEATURED THREAD · {f.get('chapters', 0)} CHAPTERS</div>
        <h3>{html.escape(f.get('title', ''))}</h3>
        <p class="summary">{html.escape(f.get('thread_summary', ''))}</p>
        <div class="latest-chapter">
          <div class="chapter-eyebrow">LATEST CHAPTER</div>
          <div class="chapter-title">{html.escape(f.get('latest_chapter_title', ''))}</div>
          <div class="chapter-dek">{html.escape(f.get('latest_chapter_dek', ''))}</div>
        </div>
      </article>
      <aside class="thread-list">
        <div class="eyebrow muted" style="margin-bottom:16px;">OTHER ACTIVE THREADS</div>
        {list_html}
      </aside>
    </div>
  </div>
</section>"""


def _render_the_canon(canon: dict[str, Any]) -> str:
    e = canon.get("entry") or {}
    div = e.get("cohort_divergence") or {}
    return f"""
<section class="dept">
  <div class="page">
    <div class="dept-head">
      <span class="roman">XII.</span>
      <span class="label">THE CANON · ENTRY OF THE WEEK</span>
      <span class="meta">LIVE · WEEKLY ROTATION</span>
    </div>
    <div class="canon-grid">
      <article class="canon-entry">
        <span class="category-pill">{html.escape(e.get('category', ''))}</span>
        <div class="era">{html.escape(e.get('era', ''))}</div>
        <h3>{html.escape(e.get('title', ''))}</h3>
        <p class="summary">{html.escape(e.get('summary', ''))}</p>
        <a class="cta" href="/canon/{html.escape(e.get('slug', ''))}/">OPEN CANON ENTRY →</a>
      </article>
      <aside class="canon-divergence">
        <div class="divergence-eyebrow">WHERE THE STAT FOLKS AND REGULAR FANS RANK</div>
        <div class="ranks">
          <div class="rank-block">
            <div class="rank-label">STAT FOLKS</div>
            <div class="rank-num stats">#{div.get('stat_folks_rank', '—')}</div>
          </div>
          <div class="rank-block">
            <div class="rank-label">FANS</div>
            <div class="rank-num fans">#{div.get('regular_fans_rank', '—')}</div>
          </div>
        </div>
        <div class="gap-label">{html.escape(div.get('gap_label', ''))}</div>
        <p class="starter">{html.escape(div.get('discussion_starter', ''))}</p>
      </aside>
    </div>
  </div>
</section>"""


def _render_voices(voices: list[EditionVoice]) -> str:
    cards = "".join(
        f"""<article class="voice-card">
          <div class="voice-name">{html.escape(_humanize_slug(v.source_slug))}</div>
          <div class="voice-role">{html.escape(v.role_label)}</div>
          {f'<span class="voice-pill">{html.escape(v.receipt_score_label or "")}</span>' if v.receipt_score_label else ''}
          <p class="voice-bio">{html.escape(v.bio)}</p>
          <div class="takes-tracked">{v.takes_tracked} TAKES TRACKED</div>
        </article>"""
        for v in voices
    )
    return f"""
<section class="dept">
  <div class="page">
    <div class="dept-head">
      <span class="roman">XIII.</span>
      <span class="label">VOICES BEHIND THIS EDITION</span>
    </div>
    <div class="voices-grid">{cards}</div>
  </div>
</section>"""


def _render_footer(edition: Edition) -> str:
    vol = _ROMAN[edition.volume] if edition.volume < len(_ROMAN) else str(edition.volume)
    year = edition.publish_date.year
    return f"""
<footer class="footer">
  <div class="page">
    <div class="chrome">
      <span>VOL. {vol} · NO. {edition.edition_number}</span>
      <span>CFB / INDEX</span>
      <span>{year}</span>
    </div>
    <div class="footer-cols">
      <div class="footer-col">
        <h4>DEPARTMENTS</h4>
        <ul>
          <li><a href="/editions/">Editions Archive</a></li>
          <li><a href="/the-daily/">The Daily</a></li>
          <li><a href="/wire/">The Wire</a></li>
          <li><a href="/threads/">Storyline Threads</a></li>
          <li><a href="/canon/">The Canon</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>REFERENCE</h4>
        <ul>
          <li><a href="/rankings/">Rankings</a></li>
          <li><a href="/teams/">Team Pages</a></li>
          <li><a href="/conferences/">Conferences</a></li>
          <li><a href="/about-model/">How It Works</a></li>
          <li><a href="/methodology/fan-intelligence.html">Fan Intel</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>SUBSCRIBE</h4>
        <ul>
          <li>Saturday morning · 06:00 ET</li>
          <li>Weekly cover essay</li>
          <li>The Daily — every morning</li>
          <li>The Wire — continuous</li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>MASTHEAD</h4>
        <ul>
          <li>Editor's Desk</li>
          <li>Receipts Desk</li>
          <li>Cohort Desk</li>
          <li>Connections Desk</li>
          <li>Fan-Voice Desk</li>
        </ul>
      </div>
    </div>
    <div class="bottom-chrome">
      <span>© {year} CFB INDEX · BUILT FOR THE OFFSEASON</span>
      <span>VOL. {vol} · NO. {edition.edition_number}</span>
    </div>
  </div>
</footer>"""


# ----------------------- Helpers -----------------------

def _load_stub(filename: str) -> dict[str, Any]:
    path = _STUB_DIR / filename
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _slugify(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def _humanize_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-")[:3])
