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
    IX   The Daily strip          (live: daily_editions; fallback: daily_seed.json)
    X    The Wire                 (live: wire_entries; fallback: wire_seed.json)
    XI   Active Threads           (live: storyline_threads; fallback: threads.json)
    XII  The Canon entry          (live: canon_entries; fallback: canon_featured.json)
    XIII Voices behind this edition
    Footer

Each running department uses a `_fetch_*_live(db)` function that returns
None when the source table is empty; the caller then falls back to a
stub JSON in `stub_data/`. The is_live flag is passed to the render
function so badges ("LIVE" / "ARCHIVE VIEW") stay honest about which
mode is active.
"""
from __future__ import annotations

import html
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.nav import render_global_nav

from . import viz_templates
from .data import (
    Edition, EditionFeature, EditionVoice,
    fetch_active_edition, fetch_edition_features, fetch_edition_voices,
)


_ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
          "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]

_STUB_DIR = Path(__file__).resolve().parent / "stub_data"


# Matches *foo* (italic) and **foo** (bold) in escaped HTML text. We render
# inline emphasis on dek / summary / tease fields so seed copy that uses
# markdown convention ("the conversation is about *tempo*") doesn't bleed
# literal asterisks into the page. Order matters: bold first so its inner
# `*foo*` doesn't get re-matched as italic.
import re as _re

_BOLD_RE = _re.compile(r"\*\*([^*]+)\*\*")
_ITALIC_RE = _re.compile(r"\*([^*\s][^*]*?[^*\s]|[^*\s])\*")


def _inline_emphasis(text: str) -> str:
    """Apply *foo*→<em> and **foo**→<strong> AFTER html.escape().

    Use only on plain-text fields where consistent markdown emphasis has
    been authored into seed copy. For full markdown processing on body
    content, use article_renderer._markdown_to_html.
    """
    escaped = html.escape(text or "")
    escaped = _BOLD_RE.sub(r"<strong>\1</strong>", escaped)
    escaped = _ITALIC_RE.sub(r"<em>\1</em>", escaped)
    return escaped


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
    # Surface whether the corpus is actually fresh. _render_active_threads
    # uses this to decide "LIVE · N ACTIVE" vs "ARCHIVE · N THREADS".
    # Without it, populating the DB with threads whose last chapter is
    # April-old falsely flipped the homepage from "ARCHIVE" to "LIVE".
    latest = ""
    for r in rows:
        when = (r["last_chapter_at"] or "")[:10]
        if when and when > latest:
            latest = when
    is_fresh = False
    if latest:
        try:
            d = datetime.strptime(latest, "%Y-%m-%d").date()
            is_fresh = (date.today() - d).days <= 14
        except ValueError:
            is_fresh = False
    return {"featured": featured, "active": active, "is_fresh": is_fresh}


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
    # The CTA template renders /canon/{slug}.html — canon entries on
    # disk live at /canon/<list_slug>/<entity_slug>.html, so we compose
    # the full relative slug here. Previously this returned just
    # entity_slug, which produced a 404 link on the homepage CTA.
    list_slug = e["list_slug"] or ""
    entity_slug = e["entity_slug"] or ""
    if list_slug and entity_slug:
        href_slug = f"{list_slug}/{entity_slug}"
    else:
        href_slug = entity_slug or list_slug
    return {
        "entry": {
            "slug": href_slug,
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
    # Surface the freshest occurred_at so the homepage badge can be honest
    # about how recent the wire actually is.
    latest = max((r.get("occurred_at") for r in rows if r.get("occurred_at")), default="")
    return {"entries": entries, "latest_occurred_at": latest}


def _fetch_daily_live(db: Database) -> dict[str, Any] | None:
    """Query daily_editions + daily_takes for The Daily homepage strip.

    Returns the freshest 'published' edition plus the last few archive
    leads. Returns None if no published edition exists (caller falls
    back to the seed stub). Offline-stub editions are excluded so the
    homepage never advertises hardcoded fallback prose as today's take.
    """
    # Filter out offline-stub editions even if they were historically
    # written with status='published' before the synthesizer fix landed.
    # The Alabama / Georgia / OL fallback prose is hardcoded and would
    # otherwise look like today's "real" three takes on the homepage.
    editions = db.query_all(
        "SELECT edition_date, generated_at_utc FROM daily_editions "
        "WHERE status = 'published' "
        "  AND coalesce(generation_model, '') NOT LIKE '%offline%' "
        "ORDER BY edition_date DESC LIMIT 6"
    )
    if not editions:
        return None
    today_row = editions[0]
    today_takes = db.query_all(
        "SELECT rank_position, headline, body FROM daily_takes "
        "WHERE edition_date = :date ORDER BY rank_position",
        {"date": today_row["edition_date"]},
    )
    if not today_takes:
        return None

    def _summarize(body: str, max_len: int) -> str:
        body = (body or "").strip()
        if len(body) <= max_len:
            return body
        return body[:max_len].rsplit(" ", 1)[0] + "…"

    try:
        d = datetime.strptime(today_row["edition_date"][:10], "%Y-%m-%d").date()
        try:
            today_label = d.strftime("%A, %B %#d, %Y")
        except ValueError:
            today_label = d.strftime("%A, %B %-d, %Y")
    except Exception:
        today_label = today_row["edition_date"]

    today_block = {
        "date_label": today_label,
        "title": "Three Things This Morning",
        "takes": [
            {"n": t["rank_position"], "headline": t["headline"],
             "body": _summarize(t["body"], max_len=240)}
            for t in today_takes
        ],
    }

    archive: list[dict[str, str]] = []
    for ed in editions[1:6]:
        leads = db.query_all(
            "SELECT headline, body FROM daily_takes "
            "WHERE edition_date = :date ORDER BY rank_position LIMIT 1",
            {"date": ed["edition_date"]},
        )
        if not leads:
            continue
        try:
            ad = datetime.strptime(ed["edition_date"][:10], "%Y-%m-%d").date()
            try:
                arc_label = ad.strftime("%b %#d")
            except ValueError:
                arc_label = ad.strftime("%b %-d")
        except Exception:
            arc_label = ed["edition_date"][:10]
        lead = leads[0]
        archive.append({
            "date_label": arc_label,
            "title": lead["headline"],
            "summary": _summarize(lead["body"], max_len=140),
        })

    return {
        "today": today_block,
        "archive": archive,
        "latest_edition_date": today_row["edition_date"][:10],
    }


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

    # Track whether each surface is using live or stub data so badges
    # can stop lying about freshness when the homepage was assembled
    # from cached seed JSON instead of the DB.
    if db is not None:
        threads_live = _fetch_threads_live(db)
        canon_live = _fetch_canon_live(db)
        wire_live = _fetch_wire_live(db)
        daily_live = _fetch_daily_live(db)
    else:
        threads_live = canon_live = wire_live = daily_live = None
    threads_data = threads_live or _load_stub("threads.json")
    canon_data = canon_live or _load_stub("canon_featured.json")
    wire_data = wire_live or _load_stub("wire_seed.json")
    daily_data = daily_live or _load_stub("daily_seed.json")
    threads_is_live = threads_live is not None
    canon_is_live = canon_live is not None
    wire_is_live = wire_live is not None
    daily_is_live = daily_live is not None

    publish_dt = datetime.combine(edition.publish_date, datetime.min.time())
    # Windows-safe date formatting (no %-d on win32):
    try:
        publish_label = publish_dt.strftime("%A · %B %#d · %Y").upper()
    except ValueError:
        publish_label = publish_dt.strftime("%A · %B %d · %Y").upper()

    parts: list[str] = []
    parts.append(_render_head(edition))
    parts.append(f'<main id="main-content">')
    parts.append(_render_masthead(edition, publish_label))
    parts.append(_render_hero(edition))
    parts.append(_render_cover_viz(edition))
    if cover_essay:
        parts.append(_render_cover_essay_tease(edition, cover_essay))
    parts.append(_render_feature_toc(secondary))
    parts.append(_render_running_departments_divider())
    parts.append(_render_the_daily(daily_data, is_live=daily_is_live))
    parts.append(_render_the_wire(wire_data, is_live=wire_is_live))
    parts.append(_render_active_threads(threads_data, is_live=threads_is_live))
    parts.append(_render_the_canon(canon_data, is_live=canon_is_live))
    parts.append(_render_voices(voices))
    parts.append(_render_footer(edition))
    parts.append("</main></body></html>")
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
.page { max-width: 1280px; margin: 0 auto; padding: 0 clamp(24px, 5vw, 64px); }
.eyebrow { font-family: var(--sans); font-size: 11px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--ink); }
.eyebrow.muted { color: var(--muted); }
.rule { border: 0; height: 1px; background: var(--rule); margin: 0; }
.rule.soft { background: var(--rule-soft); }
.rule.gold { background: var(--gold); height: 4px; width: 60px; border: 0; }
a { color: inherit; text-decoration: none; }
a:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }
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
  .nav { font-size: 10px; flex-wrap: wrap; gap: 8px; justify-content: center; }
  .nav a { margin-left: 0; margin-right: 8px; margin-bottom: 8px; }
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
</head><body>
<a href="#main-content" style="position:absolute;left:-9999px;top:auto;width:1px;height:1px;overflow:hidden;">Skip to main content</a>"""


# ----------------------- Sections -----------------------

def _render_masthead(edition: Edition, publish_label: str) -> str:
    from cfb_rankings.nav import render_global_nav

    vol = _ROMAN[edition.volume] if edition.volume < len(_ROMAN) else str(edition.volume)
    publish_time = (edition.published_at_utc or "").split(" ")[1][:5] if edition.published_at_utc else "06:00"

    # Use shared navigation component for consistency across all pages
    nav_html = render_global_nav(current_page="/", variant="desktop")

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
      {nav_html}
    </div>
    <hr class="rule">
  </div>
</header>

<script>
// Mobile navigation toggle - ensures accessibility and proper ARIA states
(function() {{
  const toggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (toggle && navLinks) {{
    toggle.addEventListener('click', function() {{
      const isOpen = navLinks.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    }});
    // Close menu when clicking outside
    document.addEventListener('click', function(e) {{
      if (!toggle.contains(e.target) && !navLinks.contains(e.target)) {{
        navLinks.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      }}
    }});
    // Close menu on window resize to desktop
    window.addEventListener('resize', function() {{
      if (window.innerWidth >= 860) {{
        navLinks.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      }}
    }});
  }}
}})();
</script>"""


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
    <p class="tease-dek">{_inline_emphasis(essay.dek)}</p>
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
        <div class="toc-dek">{_inline_emphasis(f.dek)}</div>
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


def _render_the_daily(daily: dict[str, Any], is_live: bool = False) -> str:
    today = daily.get("today") or {}
    archive = daily.get("archive") or []
    takes_html = "".join(
        f"""<li><div></div><div>
          <h3>{html.escape(t.get('headline', ''))}</h3>
          <p>{_inline_emphasis(t.get('body', ''))}</p>
        </div></li>"""
        for t in (today.get("takes") or [])
    )
    archive_html = "".join(
        f"""<div class="archive-row">
          <div class="archive-date">{html.escape(a.get('date_label', ''))}</div>
          <div>
            <div class="archive-title">{html.escape(a.get('title', ''))}</div>
            <div class="archive-summary">{_inline_emphasis(a.get('summary', ''))}</div>
          </div>
        </div>"""
        for a in archive
    )
    badge_html = '<span class="badge-live">LIVE</span>' if is_live else ''
    footer_html = (
        ''
        if is_live
        else '<p class="eyebrow muted" style="margin-top:32px;">Today\'s edition will be published later. Check back for fresh takes.</p>'
    )
    return f"""
<section class="dept">
  <div class="page">
    <div class="dept-head">
      <span class="roman">IX.</span>
      <span class="label">THE DAILY</span>
      {badge_html}
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
    {footer_html}
  </div>
</section>"""


def _render_the_wire(wire: dict[str, Any], is_live: bool = False) -> str:
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
    # Honest freshness label: derive from the freshest occurred_at in the
    # rows actually rendered. Falls back to a static label only when no
    # data is available (stub mode).
    meta = "ARCHIVE VIEW"
    if is_live:
        latest = (wire.get("latest_occurred_at") or "")[:10]
        if latest:
            try:
                d = datetime.strptime(latest, "%Y-%m-%d").date()
                age_days = (date.today() - d).days
                if age_days <= 1:
                    meta = f"UPDATED {latest} · LIVE"
                elif age_days <= 7:
                    meta = f"LATEST ENTRY {latest} · {age_days}d AGO"
                else:
                    meta = f"LATEST ENTRY {latest} · ARCHIVE VIEW"
            except Exception:
                meta = f"UPDATED {latest}"
    return f"""
<section class="dept">
  <div class="page">
    <div class="dept-head">
      <span class="roman">X.</span>
      <span class="label">THE WIRE</span>
      <span class="meta">{html.escape(meta)}</span>
    </div>
    <table class="wire-table">
      <thead><tr>
        <th>WHEN</th><th>PROGRAM</th><th>ACTION</th><th>WHY IT MATTERS</th><th>IMPACT</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</section>"""


def _render_active_threads(threads: dict[str, Any], is_live: bool = False) -> str:
    f = threads.get("featured") or {}
    active = threads.get("active") or []
    total_count = len(active) + (1 if f else 0)
    # "is_fresh" comes from _fetch_threads_live: at least one chapter
    # within the last 14 days. The DB being populated with stale data
    # (all chapters from April) was flipping the badge from "ARCHIVE"
    # back to "LIVE" — fresh-corpus check fixes that.
    is_fresh = bool(threads.get("is_fresh"))
    # Drop the per-row "UPDATED <date>" line when the corpus is stale
    # or stubbed — preserves real dates only when they actually mean
    # "recently updated."
    def _row_html(t: dict[str, Any]) -> str:
        last = (t.get("last_updated") or "").strip()
        if is_live and is_fresh and last:
            updated_html = f'<div class="last-updated">UPDATED {html.escape(last)}</div>'
        else:
            updated_html = '<div class="last-updated muted">ARCHIVE</div>'
        return (
            f'<div class="thread-row">'
            f'<div>'
            f'<div class="thread-name">{html.escape(t.get("title", ""))}</div>'
            f'{updated_html}'
            f'</div>'
            f'<div class="chapters">{t.get("chapters", 0)} CH.</div>'
            f'</div>'
        )
    list_html = "".join(_row_html(t) for t in active)
    if is_live and is_fresh:
        meta_label = f"LIVE · {total_count} ACTIVE"
    else:
        meta_label = f"ARCHIVE · {total_count} THREADS"
    return f"""
<section class="dept">
  <div class="page">
    <div class="dept-head">
      <span class="roman">XI.</span>
      <span class="label">ACTIVE THREADS</span>
      <span class="meta">{meta_label}</span>
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


def _render_the_canon(canon: dict[str, Any], is_live: bool = False) -> str:
    e = canon.get("entry") or {}
    div = e.get("cohort_divergence") or {}
    # "WEEKLY ROTATION" is accurate when canon_entries is populated (the
    # _fetch_canon_live function rotates by ISO week). When falling back
    # to stub_data/canon_featured.json, there's no rotation.
    meta_label = "WEEKLY ROTATION" if is_live else "FEATURED ENTRY"
    return f"""
<section class="dept">
  <div class="page">
    <div class="dept-head">
      <span class="roman">XII.</span>
      <span class="label">THE CANON · ENTRY OF THE WEEK</span>
      <span class="meta">{meta_label}</span>
    </div>
    <div class="canon-grid">
      <article class="canon-entry">
        <span class="category-pill">{html.escape(e.get('category', ''))}</span>
        <div class="era">{html.escape(e.get('era', ''))}</div>
        <h3>{html.escape(e.get('title', ''))}</h3>
        <p class="summary">{html.escape(e.get('summary', ''))}</p>
        <a class="cta" href="/canon/{html.escape(e.get('slug', ''))}.html">OPEN CANON ENTRY →</a>
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
          <li><a href="/daily/">The Daily</a></li>
          <li><a href="/wire/">The Wire</a></li>
          <li><a href="/mailbag/">The Mailbag</a></li>
          <li><a href="/storylines/">Storyline Threads</a></li>
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
    # Must collapse consecutive dashes to match article_renderer._slugify so
    # the homepage cover-essay link resolves to the filesystem path that
    # article_renderer actually wrote. Without the collapse, titles with
    # consecutive non-alnum chars (em-dash + space, "It's — Just a Show",
    # double hyphens, etc.) produced a homepage link with "--" pointing at a
    # path that was written with single "-".
    out = "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")
    while "--" in out:
        out = out.replace("--", "-")
    return out


def _humanize_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-")[:3])
