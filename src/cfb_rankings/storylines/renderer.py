"""Renderer for Storyline Threads.

DB → standalone HTML at output/site/storylines/<slug>.html plus
output/site/storylines/index.html, plus the homepage contract file
stub_data/threads.json.

Pure Python — no Jinja2 dep. Uses string.Template-style ${slot}
substitution into the HTML skeletons in templates/.

Visual design-of-record: Figma node 62:2 in file eGIVOKDIFSmo1yM1LShLQx.
Single-column flow, sans typography (Inter / system-ui), inline chapter
index, related threads, and receipts panels (no left-or-right sidebars).
"""
from __future__ import annotations

import html
import json
import re
import string
from datetime import date, datetime
from pathlib import Path
from typing import Any

from . import render_helpers as rh
from cfb_rankings.common.head_chrome import absolute_url


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _load_template(name: str) -> string.Template:
    text = (_TEMPLATES_DIR / name).read_text(encoding="utf-8")
    return string.Template(text)


def _load_css() -> str:
    return (_TEMPLATES_DIR / "_styles.css").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# DB queries
# ---------------------------------------------------------------------------

def _fetch_thread(db, slug: str) -> dict | None:
    return db.query_one(
        "select * from storyline_threads where thread_slug = :slug",
        {"slug": slug},
    )


def _fetch_chapters(db, slug: str) -> list[dict]:
    return db.query_all(
        """
        select * from storyline_chapters
        where thread_slug = :slug
        order by chapter_number desc
        """,
        {"slug": slug},
    )


def _fetch_all_threads(db) -> list[dict]:
    return db.query_all(
        """
        select * from storyline_threads
        order by status = 'active' desc, last_chapter_at desc nulls last, started_at desc
        """
    )


def _fetch_related_threads(db, current_slug: str, limit: int = 3) -> list[dict]:
    return db.query_all(
        """
        select * from storyline_threads
        where thread_slug != :slug and status = 'active'
        order by last_chapter_at desc nulls last
        limit :lim
        """,
        {"slug": current_slug, "lim": limit},
    )


# ---------------------------------------------------------------------------
# Helpers — date display, relative time, accent color
# ---------------------------------------------------------------------------

def _accent_soft(hex_color: str | None) -> str:
    """Return rgba(r,g,b,0.18) for an accent hex. Used for inline accent-soft slot."""
    if not hex_color or not hex_color.startswith("#") or len(hex_color) not in (4, 7):
        return "rgba(197, 179, 88, 0.18)"
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return "rgba(197, 179, 88, 0.18)"
    return f"rgba({r}, {g}, {b}, 0.18)"


def _relative(dt_value: Any, today: datetime | None = None) -> str:
    dt = rh.parse_dt(dt_value)
    if dt is None:
        return "—"
    now = today or datetime.now()
    delta = now - dt
    days = delta.days
    if days < 0:
        return rh.humanize_date_short(dt)
    if days == 0:
        return "today"
    if days == 1:
        return "1 day ago"
    if days < 7:
        return f"{days} days ago"
    if days < 30:
        weeks = days // 7
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    if days < 365:
        months = days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = days // 365
    return f"{years} year{'s' if years != 1 else ''} ago"


def _short_year_month(dt_value: Any) -> str:
    dt = rh.parse_dt(dt_value)
    if dt is None:
        return "—"
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    return f"{months[dt.month - 1]} {dt.year}"


def _humanize_followers(n: int | None) -> str:
    """Format a follower count — placeholder until follow infra ships."""
    if n is None or n <= 0:
        return "—"
    if n < 1000:
        return str(n)
    return f"{n / 1000:.1f}k".replace(".0k", "k")


# ---------------------------------------------------------------------------
# Body rendering with inline pull-quote (matches Figma layout where the
# pull quote sits BETWEEN body paragraphs, not at the end as a sidebar)
# ---------------------------------------------------------------------------

def _render_body_with_pull_quote(body_md: str, pull_quote: str | None,
                                  attribution: str | None = None) -> str:
    """Render markdown body, splicing the pull quote in after paragraph #2.

    If no pull quote, render body unchanged. Matches Figma node 62:73
    where the pull quote and attribution sit inline within the body
    flow rather than as a floated aside.
    """
    if not pull_quote or not pull_quote.strip():
        return rh.markdown_light_to_html(body_md)

    # Split on blank-line paragraph boundaries.
    blocks = re.split(r"\n\s*\n", body_md.strip())
    if len(blocks) < 3:
        # Body too short to splice — render quote at end.
        body_html = rh.markdown_light_to_html(body_md)
        quote_html = (
            f'<p class="pull-quote">\u201c{html.escape(pull_quote.strip(), quote=False)}\u201d</p>'
        )
        if attribution:
            quote_html += (
                f'<p class="pull-quote-attribution">— {html.escape(attribution, quote=False)}</p>'
            )
        return body_html + "\n" + quote_html

    before = "\n\n".join(blocks[:2])
    after = "\n\n".join(blocks[2:])
    before_html = rh.markdown_light_to_html(before)
    after_html = rh.markdown_light_to_html(after)
    quote_html = (
        f'<p class="pull-quote">\u201c{html.escape(pull_quote.strip(), quote=False)}\u201d</p>'
    )
    if attribution:
        quote_html += (
            f'<p class="pull-quote-attribution">— {html.escape(attribution, quote=False)}</p>'
        )
    return before_html + "\n" + quote_html + "\n" + after_html


# ---------------------------------------------------------------------------
# Source-row rendering (Figma 62:81 sources panel)
# ---------------------------------------------------------------------------

def _render_source_rows(sources_json: str | None) -> str:
    """Render the sources panel as one .source-row per cited source.

    Each row shows source name (in accent), publisher, date, and the
    verbatim quote underneath. Matches Figma node 62:83-114 layout.
    """
    if not sources_json:
        return ""
    try:
        sources = json.loads(sources_json)
    except (json.JSONDecodeError, TypeError):
        return ""
    rows: list[str] = []
    for src in sources:
        name = html.escape(str(src.get("name", "")), quote=False)
        publisher = html.escape(str(src.get("label", "")), quote=False)
        date_s = src.get("date") or ""
        date_disp = rh.humanize_date_short(date_s) if date_s else ""
        # The verbatim quote — if not present, show source-info row only.
        quote = src.get("quote") or ""
        url = src.get("url")
        url_safe = html.escape(url, quote=True) if url and url not in ("None", "null") else None

        name_node = f'<span class="src-name">{name}</span>'
        if url_safe:
            name_node = f'<a href="{url_safe}">{name_node}</a>'

        top_left = name_node
        if publisher:
            top_left += f'<span class="src-dot">·</span><span class="src-publisher">{publisher}</span>'

        date_node = f'<span class="src-date">{date_disp}</span>' if date_disp else ""

        quote_node = ""
        if quote:
            quote_node = f'<p class="src-quote">\u201c{html.escape(quote, quote=False)}\u201d</p>'

        rows.append(
            '<div class="source-row">'
            f'<div class="source-row-top"><div class="left">{top_left}</div>{date_node}</div>'
            f'{quote_node}'
            '</div>'
        )
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Pull-quote attribution finder — looks at sources for whichever was used
# ---------------------------------------------------------------------------

def _attribution_for_pull_quote(pull_quote: str | None,
                                  sources_json: str | None) -> str | None:
    """If the pull quote is verbatim from one of the cited sources, find it."""
    if not pull_quote or not sources_json:
        return None
    try:
        sources = json.loads(sources_json)
    except (json.JSONDecodeError, TypeError):
        return None
    pq_norm = pull_quote.strip().lower()[:60]
    for src in sources:
        quote = (src.get("quote") or "").lower()
        if quote and quote[:60] == pq_norm:
            name = src.get("name", "")
            label = src.get("label", "")
            date_s = src.get("date") or ""
            date_disp = rh.humanize_date_short(date_s) if date_s else ""
            parts = [name]
            if label:
                parts.append(label)
            if date_disp:
                parts.append(date_disp)
            return ", ".join(p for p in parts if p)
    # Fallback — first source's name.
    if sources:
        first = sources[0]
        name = first.get("name", "")
        label = first.get("label", "")
        if name:
            return f"{name}, {label}" if label else name
    return None


# ---------------------------------------------------------------------------
# Receipts placeholder — Figma shows populated receipts; Sprint 13 owns the
# real data path, so we render a 2-row stub with a "stub" tag in the header.
# ---------------------------------------------------------------------------

_RECEIPT_STUBS: dict[str, list[dict]] = {
    # Per-thread illustrative stub receipts. These are intentionally
    # generic-but-plausible placeholders to demonstrate the panel
    # structure (matches Figma 62:139-156). Sprint 13 (Receipts) will
    # replace these with real DB-backed receipts indexed against this
    # thread's chapters.
    "_default": [
        {
            "quote": "Receipts on this thread's prior takes return when the editorial ledger reaches enough resolved chapters to grade them honestly.",
            "verdict": "premature",
            "attribution": "&mdash; The Receipts Desk",
        },
    ],
}


def _render_receipts_stub(slug: str) -> str:
    receipts = _RECEIPT_STUBS.get(slug, _RECEIPT_STUBS["_default"])
    rows: list[str] = []
    verdict_class = {
        "aged-poorly": "aged-poorly",
        "vindicated": "vindicated",
        "premature": "premature",
    }
    verdict_label = {
        "aged-poorly": "AGED POORLY",
        "vindicated": "VINDICATED",
        "premature": "AWAITING",
    }
    for r in receipts:
        v = r.get("verdict", "premature")
        rows.append(
            '<div class="receipt-row">'
            '<div class="receipt-row-top">'
            f'<p class="receipt-quote">\u201c{html.escape(r["quote"], quote=False)}\u201d</p>'
            f'<span class="verdict-pill {verdict_class.get(v, "premature")}">{verdict_label.get(v, "AWAITING")}</span>'
            '</div>'
            f'<p class="receipt-attribution">{html.escape(r["attribution"], quote=False)}</p>'
            '</div>'
        )
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Single-thread rendering
# ---------------------------------------------------------------------------

def render_thread(db, slug: str, output_dir: Path | str) -> Path:
    thread = _fetch_thread(db, slug)
    if not thread:
        raise ValueError(f"thread not found: {slug}")

    chapters = _fetch_chapters(db, slug)  # newest first
    chapters_by_number: dict[int, dict] = {int(c["chapter_number"]): c for c in chapters}

    current = chapters[0] if chapters else None
    current_number = int(current["chapter_number"]) if current else 0

    # Inline chapter index — show top 5 newest, then a "+ N earlier" note.
    visible_count = 5
    visible = chapters[:visible_count]
    remaining = max(0, len(chapters) - visible_count)
    rows: list[str] = []
    for ch in visible:
        n = int(ch["chapter_number"])
        title = html.escape(ch["title"], quote=False)
        date_disp = rh.humanize_date_short(ch["published_at"])
        cls = "chapter-row current" if n == current_number else "chapter-row"
        rows.append(
            f'<div class="{cls}">'
            f'<span class="chapter-num">{n:02d}</span>'
            f'<a class="ct" href="#chapter-{n}">{title}</a>'
            f'<span class="cd">{date_disp}</span>'
            f'</div>'
        )
    chapter_index_html = "\n".join(rows) or '<div class="chapter-row"><span class="ct">No chapters yet.</span></div>'

    if remaining > 0:
        earliest_year = rh.parse_dt(chapters[-1]["published_at"])
        year = earliest_year.year if earliest_year else ""
        chapter_index_more_html = (
            f'<div class="nav-rail-more">+ {remaining} earlier chapter'
            f'{"s" if remaining != 1 else ""}{f" from {year}" if year else ""}</div>'
        )
    else:
        chapter_index_more_html = ""

    # Current chapter content.
    if current:
        current_chapter_number = f"{int(current['chapter_number']):02d}"
        current_chapter_title = html.escape(current["title"], quote=False)
        current_chapter_dek = html.escape(current["dek"], quote=False)
        current_chapter_published_display = rh.humanize_date(current["published_at"])
        current_chapter_read_time = current.get("read_time_minutes", 1)
        sources_json = current.get("referenced_sources_json")
        attribution = _attribution_for_pull_quote(current.get("pull_quote"), sources_json)
        current_chapter_body_html = _render_body_with_pull_quote(
            current["body_markdown"], current.get("pull_quote"), attribution,
        )
        current_chapter_sources_html = _render_source_rows(sources_json)
        current_chapter_referenced_html = rh.render_referenced_callout(
            current.get("referenced_chapter_ids"), chapters_by_number, slug
        )
        # The render_referenced_callout uses old class names; rewrite if needed.
        current_chapter_referenced_html = current_chapter_referenced_html.replace(
            "referenced-chapters", "ref-callout"
        )
    else:
        current_chapter_number = "00"
        current_chapter_title = "No chapters published yet"
        current_chapter_dek = "Chapter content will appear here once authored."
        current_chapter_published_display = "—"
        current_chapter_read_time = 1
        current_chapter_body_html = '<p><em>This thread is open. The first chapter is being written.</em></p>'
        current_chapter_sources_html = ""
        current_chapter_referenced_html = ""

    # Right rail moved inline — related threads as 3-up cards.
    related = _fetch_related_threads(db, slug, limit=3)
    related_html_parts: list[str] = []
    for r in related:
        r_title = html.escape(r["title"], quote=False)
        r_chapters = r.get("chapter_count", 0)
        r_date = rh.humanize_date_short(r["last_chapter_at"]) if r.get("last_chapter_at") else "—"
        r_accent = r.get("accent_hex") or "#c5b358"
        related_html_parts.append(
            f'<a class="related-card" href="/storylines/{r["thread_slug"]}.html">'
            f'<span class="accent-bar" style="background: {r_accent};"></span>'
            f'<span class="rel-title">{r_title}</span>'
            f'<span class="rel-meta">'
            f'<span class="rel-chapters">{r_chapters} chapters</span>'
            f'<span class="rel-date">{r_date}</span>'
            f'</span>'
            f'</a>'
        )
    related_threads_html = (
        "\n".join(related_html_parts)
        or '<div class="related-card"><span class="rel-title">No related threads.</span></div>'
    )

    # Status + meta values.
    chapter_count = thread.get("chapter_count") or len(chapters)
    word_count_total = thread.get("word_count") or sum(int(c.get("word_count") or 0) for c in chapters)
    follower_count = thread.get("follower_count") or 0
    status = thread.get("status") or "active"

    template = _load_template("thread.html")
    embedded_css = _load_css()
    accent_hex = thread.get("accent_hex") or "#c5b358"
    # Distribution-leak fix: storyline pages were shipping without
    # og:image / twitter:card / canonical until 2026-05-17 (parallel to
    # the player-page fix in PR #99). Threads are share-bait surfaces
    # — a Tweet/Bluesky/SMS link to /storylines/<slug>.html previously
    # rendered as a bare URL with no preview image, title, or
    # description.
    page_canonical = absolute_url(f"/storylines/{slug}.html")
    og_image_url = absolute_url("/og-image.svg")
    page_html = template.safe_substitute(
        page_title=f"{thread['title']} · CFB Index Storyline Threads",
        page_description=thread["dek"],
        page_canonical=page_canonical,
        og_image_url=og_image_url,
        embedded_css=embedded_css,
        accent_hex=accent_hex,
        accent_hex_soft=_accent_soft(accent_hex),
        thread_slug=thread["thread_slug"],
        thread_title=html.escape(thread["title"], quote=False),
        thread_title_upper=html.escape(thread["title"].upper(), quote=False),
        thread_dek=html.escape(thread["dek"], quote=False),
        status_class=status,
        status_label=rh.status_label(status),
        chapter_count=chapter_count,
        word_count_display=rh.humanize_word_count(word_count_total),
        started_at_short=_short_year_month(thread.get("started_at")),
        started_at_long=rh.humanize_date(thread.get("started_at")),
        last_chapter_relative=_relative(thread.get("last_chapter_at")),
        follower_count_display=_humanize_followers(follower_count),
        chapter_index_html=chapter_index_html,
        chapter_index_more_html=chapter_index_more_html,
        current_chapter_number=current_chapter_number,
        current_chapter_title=current_chapter_title,
        current_chapter_dek=current_chapter_dek,
        current_chapter_published_display=current_chapter_published_display,
        current_chapter_read_time=current_chapter_read_time,
        current_chapter_referenced_html=current_chapter_referenced_html,
        current_chapter_body_html=current_chapter_body_html,
        current_chapter_sources_html=current_chapter_sources_html,
        related_threads_html=related_threads_html,
        receipts_html=_render_receipts_stub(slug),
        receipts_stub_label="receipts pending — see methodology",
        footer_year=datetime.now().year,
    )
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.html"
    out_path.write_text(page_html, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Index rendering
# ---------------------------------------------------------------------------

def render_index(db, output_dir: Path | str) -> Path:
    threads = _fetch_all_threads(db)
    cards: list[str] = []
    # Threads that haven't gotten a new chapter in 21+ days get a
    # "Dormant" status badge instead of "Active". The seed deks say
    # things like "mapped chapter by chapter as it happens" which read
    # as a contradiction when paired with an April last-chapter date in
    # mid-May. Downgrade the badge so the page is honest about cadence.
    from datetime import date as _date, datetime as _dt
    today = _dt.utcnow().date()
    for t in threads:
        title = html.escape(t["title"], quote=False)
        dek = html.escape(t["dek"], quote=False)
        accent = t.get("accent_hex") or "#c5b358"
        slug = t["thread_slug"]
        ch_count = t.get("chapter_count") or 0
        last_raw = t.get("last_chapter_at")
        last = rh.humanize_date_short(last_raw) if last_raw else "—"
        started = _short_year_month(t["started_at"])
        status = rh.status_label(t.get("status"))
        # Downgrade the status pill when the last chapter is stale.
        if last_raw and status.lower() == "active":
            try:
                last_date = _dt.strptime(str(last_raw)[:10], "%Y-%m-%d").date()
                age_days = (today - last_date).days
                if age_days >= 14:
                    status = "Dormant"
            except (ValueError, TypeError):
                pass
        cards.append(
            f'<a class="index-card" href="/storylines/{slug}.html">'
            f'<span class="ic-bar" style="background: {accent};"></span>'
            f'<div class="ic-eyebrow">{status} · started {started}</div>'
            f'<h2 class="ic-title">{title}</h2>'
            f'<p class="ic-dek">{dek}</p>'
            f'<div class="ic-foot">'
            f'<span><strong>{ch_count}</strong> chapters</span>'
            f'<span>last <strong>{last}</strong></span>'
            f'</div>'
            f'</a>'
        )
    template = _load_template("thread_index.html")
    # Database-archetype meta-footer (Session 6 Track 6 adopter #4)
    from cfb_rankings.database_archetype import (
        render_database_meta_footer as _db_archetype_footer,
    )
    _db_meta = _db_archetype_footer(
        label=(
            "active thread" if len(threads) == 1
            else "active threads"
        ),
        total_rows=len(threads),
        methodology_label="How storyline threads work",
        methodology_href="/methodology/",
        updated_text=f"Updated {today.isoformat()}",
    )
    page_html = template.safe_substitute(
        embedded_css=_load_css(),
        thread_cards_html="\n".join(cards) or '<p>No threads yet.</p>',
        database_meta_footer=_db_meta,
        footer_year=datetime.now().year,
        page_canonical=absolute_url("/storylines/"),
        og_image_url=absolute_url("/og-image.svg"),
    )
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"
    out_path.write_text(page_html, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Homepage contract — stub_data/threads.json (Sprint 9 reads this)
# ---------------------------------------------------------------------------

def emit_homepage_threads_json(db, output_path: Path | str) -> Path:
    threads = _fetch_all_threads(db)
    payload: list[dict] = []
    for t in threads:
        slug = t["thread_slug"]
        latest = db.query_one(
            """
            select chapter_number, title, dek, published_at, byline
            from storyline_chapters
            where thread_slug = :slug
            order by chapter_number desc
            limit 1
            """,
            {"slug": slug},
        )
        payload.append({
            "slug": slug,
            "title": t["title"],
            "dek": t["dek"],
            "accent_hex": t.get("accent_hex"),
            "status": t.get("status"),
            "started_at": str(t.get("started_at")) if t.get("started_at") else None,
            "last_chapter_at": str(t.get("last_chapter_at")) if t.get("last_chapter_at") else None,
            "chapter_count": t.get("chapter_count") or 0,
            "word_count": t.get("word_count") or 0,
            "href": f"/storylines/{slug}.html",
            "latest_chapter": (
                {
                    "number": int(latest["chapter_number"]),
                    "title": latest["title"],
                    "dek": latest["dek"],
                    "published_at": str(latest["published_at"]),
                    "byline": latest["byline"],
                }
                if latest else None
            ),
        })

    contract = {
        "_emitted_by_sprint_10": True,
        "_emitted_at": datetime.utcnow().isoformat() + "Z",
        "_contract_version": 1,
        "_consumers": ["sprint-9-homepage", "sprint-9-edition-toc"],
        "threads": payload,
    }
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(contract, indent=2), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------

def render_all(
    db,
    output_dir: Path | str = "output/site/storylines",
    homepage_contract_path: Path | str = "stub_data/threads.json",
) -> dict[str, Any]:
    threads = _fetch_all_threads(db)
    written: list[str] = []
    for t in threads:
        path = render_thread(db, t["thread_slug"], output_dir)
        written.append(str(path))
    index_path = render_index(db, output_dir)
    written.append(str(index_path))
    contract_path = emit_homepage_threads_json(db, homepage_contract_path)
    return {
        "thread_pages_written": len(threads),
        "index_written": str(index_path),
        "homepage_contract_written": str(contract_path),
        "all_paths": written,
    }
