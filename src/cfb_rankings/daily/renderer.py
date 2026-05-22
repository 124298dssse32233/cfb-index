"""Phase 4 — HTML renderer for The Daily.

Writes:
  output/site/daily/index.html          — current edition
  output/site/daily/YYYY-MM-DD/index.html — archive per-date
  output/site/daily/archive.html        — last-30 index
"""
from __future__ import annotations

import json
import logging
import os
import re
import string
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cfb_rankings.common.head_chrome import absolute_url

log = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_SITE_DAILY = Path("output/site/daily")

# tentpole "what we're watching" bullets (static calendar)
_WATCHING_BULLETS = [
    "Spring practice reports — portal decisions follow coaching feedback",
    "Transfer portal deadline windows — commitment trackers update daily",
    "Draft advisory declarations — underclassmen decisions shape fall depth",
]

_LONG_MONTHS = {
    "01": "January", "02": "February", "03": "March", "04": "April",
    "05": "May", "06": "June", "07": "July", "08": "August",
    "09": "September", "10": "October", "11": "November", "12": "December",
}

_ORDINALS = {
    1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th", 7: "7th",
    8: "8th", 9: "9th", 10: "10th", 11: "11th", 12: "12th", 13: "13th",
    14: "14th", 15: "15th", 16: "16th", 17: "17th", 18: "18th", 19: "19th",
    20: "20th", 21: "21st", 22: "22nd", 23: "23rd", 24: "24th", 25: "25th",
    26: "26th", 27: "27th", 28: "28th", 29: "29th", 30: "30th", 31: "31st",
}


def _long_date(iso_date: str) -> str:
    """'2026-04-21' → 'Tuesday, April 21st, 2026'"""
    try:
        d = datetime.strptime(iso_date, "%Y-%m-%d")
        day_name = d.strftime("%A")
        month = _LONG_MONTHS[d.strftime("%m")]
        ordinal = _ORDINALS.get(d.day, f"{d.day}th")
        return f"{day_name}, {month} {ordinal}, {d.year}"
    except Exception:
        return iso_date


def _load_template() -> string.Template:
    return string.Template((_TEMPLATES_DIR / "daily.html").read_text(encoding="utf-8"))


def _source_pills_html(cited_json: str) -> str:
    try:
        sources = json.loads(cited_json)
    except Exception:
        sources = []
    if not sources:
        return ""
    pills = "".join(f'<span class="source-pill">{_esc(s)}</span>' for s in sources)
    return f'<div class="source-pills">{pills}</div>'


def _entity_link_html(slug: str, entity_type: str, conn=None) -> str:
    if not slug:
        return ""
    if entity_type == "team":
        href = f"/teams/{slug}.html"
        label = slug.replace("-", " ").title()
    elif entity_type == "player":
        # The daily-take generator has historically written the raw
        # `player_id` (e.g. "2791") into `primary_entity_slug` instead of
        # the canonical page slug ("nico-iamaleava-2791"). When we see a
        # numeric value, resolve to the real page slug via the players
        # table so the link works. If the lookup fails, suppress the link
        # rather than emit a 404.
        resolved = _resolve_player_slug(slug, conn) if slug.isdigit() else slug
        if not resolved:
            return ""
        href = f"/players/{resolved}.html"
        label = resolved.rsplit("-", 1)[0].replace("-", " ").title() if "-" in resolved else resolved
    elif entity_type == "conference":
        # Conference pages live at /conferences/<level-code>-<bare-slug>.html
        # (e.g. /conferences/fbs-sec.html). If the upstream take stored a
        # bare slug like "sec" instead of the canonical "fbs-sec", the link
        # 404s. Normalize: bare slugs get the "fbs-" prefix; already-prefixed
        # ones pass through.
        norm = slug.strip().lower()
        if not norm.startswith(("fbs-", "fcs-", "dii-", "diii-", "naia-")):
            norm = f"fbs-{norm}"
        href = f"/conferences/{norm}.html"
        label = slug.upper()
    else:
        return ""
    return f'<a class="entity-link" href="{href}">→ {_esc(label)} page</a>'


def _resolve_player_slug(player_id_str: str, conn) -> str | None:
    """Map raw player_id ("2791") → canonical page slug ("nico-iamaleava-2791").

    Returns None if the player isn't found or no conn is provided.
    Page slug pattern matches reporting.py: lowercased full_name, dashed,
    suffixed with the numeric id.
    """
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT full_name, player_id FROM players WHERE player_id = ?",
            (int(player_id_str),),
        ).fetchone()
    except Exception:
        return None
    if not row:
        return None
    full_name, player_id = row[0], row[1]
    if not full_name:
        return None
    # Mirror reporting.py's slug rule: lowercase, alnum-with-dashes, dropping
    # consecutive dashes; appended with the player_id.
    cleaned = "".join(c if c.isalnum() else "-" for c in full_name.lower())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    cleaned = cleaned.strip("-")
    return f"{cleaned}-{player_id}" if cleaned else None


def _esc(s: str) -> str:
    return (s
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


# Markdown emphasis runs AFTER _esc so user content stays HTML-safe.
# LLM outputs sometimes use *foo* / **foo** for emphasis; without this
# they leak as literal asterisks into the rendered page (the user saw
# this on /daily/ headlines + bodies — fixed in headlines, this is
# the body-side fix).
import re as _re_md
_DAILY_BOLD_RE = _re_md.compile(r"\*\*(.+?)\*\*")
_DAILY_ITALIC_RE = _re_md.compile(r"(?<![*\w])\*([^*\n]+?)\*(?!\w)")


def _esc_emphasis(s: str) -> str:
    escaped = _esc(s or "")
    escaped = _DAILY_BOLD_RE.sub(r"<strong>\1</strong>", escaped)
    escaped = _DAILY_ITALIC_RE.sub(r"<em>\1</em>", escaped)
    return escaped


def _take_html(rank: int, headline: str, body: str,
               cited_json: str, entity_slug: str, entity_type: str,
               conn=None) -> str:
    rank_labels = {1: "Take #1 — Top Story", 2: "Take #2 — Two Reads", 3: "Take #3 — Buried Lede"}
    rank_label = rank_labels.get(rank, f"Take #{rank}")

    body_paras = "".join(f"<p>{_esc_emphasis(p.strip())}</p>" for p in body.split("\n") if p.strip())
    if not body_paras:
        body_paras = f"<p>{_esc_emphasis(body)}</p>"

    pills = _source_pills_html(cited_json)
    entity = _entity_link_html(entity_slug, entity_type, conn=conn)

    return f"""<article class="take">
  <div class="take__rank">
    <span class="take__numeral">{rank}</span>{_esc(rank_label)}
  </div>
  <h2 class="take__headline">{_esc(headline)}</h2>
  <div class="take__body">{body_paras}</div>
  {pills}
  {entity}
</article>"""


def _watching_html() -> str:
    items = "".join(f'<div class="sidebar__item">{_esc(b)}</div>' for b in _WATCHING_BULLETS)
    return items


def _archive_links_html(recent_editions: list[dict[str, Any]]) -> str:
    links = []
    for ed in recent_editions[:5]:
        date = ed["edition_date"]
        long = _long_date(date)
        links.append(f'<a class="archive-footer__link" href="/daily/{date}/">{_esc(long)}</a>')
    return "\n".join(links) if links else '<span style="opacity:0.4">No prior editions yet</span>'


def _build_auto_summary_html(
    rows: list[tuple],
    edition_date: str,
    conn,
) -> str:
    """Pattern 7 wire-up — emit the 30-second auto-summary block.

    Combines every take's body markdown into a single article-body for
    the auto-summary primitive. Returns "" when:
      - There are 0 takes (rendered as no-takes placeholder elsewhere)
      - The combined body is <200 chars (too short to summarize)
      - The LLM call fails or returns no parseable bullets
      - The Rung-3 weekly ceiling is hit

    Caches per (edition_date, body_hash) so re-running the renderer with
    the same takes is a single SQLite read.
    """
    if not rows:
        return ""
    # Combine all take bodies into one article-shape input. Headlines
    # carry framing; body carries the claim. The 30-second summary
    # should cover claims, so we feed both.
    parts: list[str] = []
    for r in rows:
        headline = (r[1] or "").strip()
        body = (r[2] or "").strip()
        if not body:
            continue
        if headline:
            parts.append(f"{headline}\n\n{body}")
        else:
            parts.append(body)
    combined = "\n\n---\n\n".join(parts)
    if len(combined) < 200:
        return ""
    try:
        # Import lazily — avoid a hot-path import on every site build
        # for editions that don't need the summary (small/empty days).
        from cfb_rankings.auto_summary import (
            CACHE_DDL,
            generate_article_summary,
            render_auto_summary_html,
        )
        from cfb_rankings.db import Database
    except Exception as e:
        log.warning("auto_summary import failed: %s", e)
        return ""
    # The Daily renderer is called with a raw sqlite3 connection (conn);
    # auto_summary wants a cfb_rankings.db.Database wrapper. Build a thin
    # adapter around the connection's path so the cache layer functions.
    db = _adapt_conn_for_auto_summary(conn)
    if db is None:
        # Caching unavailable — still try the LLM path (auto_summary
        # tolerates db=None and just won't cache).
        summary = generate_article_summary(
            body_markdown=combined,
            headline=f"The Daily — {edition_date}",
            dek="",
            cache_key=f"daily:{edition_date}",
            db=None,
        )
    else:
        try:
            db.execute(CACHE_DDL)  # idempotent
        except Exception as e:
            log.warning("auto_summary cache table init failed: %s", e)
        summary = generate_article_summary(
            body_markdown=combined,
            headline=f"The Daily — {edition_date}",
            dek="",
            cache_key=f"daily:{edition_date}",
            db=db,
        )
    if summary is None:
        return ""
    return render_auto_summary_html(summary)


def _adapt_conn_for_auto_summary(conn):
    """Return a Database wrapper around the same sqlite file the
    renderer is using, or None when we can't extract a usable path.

    Daily renderer is one of the few callers that gets a raw sqlite3
    connection rather than a Database handle. We need a Database for
    the auto_summary cache layer's retry-on-locked + DSN semantics.
    """
    try:
        from cfb_rankings.db import Database
        # PRAGMA database_list returns rows of (seq, name, file). The
        # 'main' database's file is the path we want.
        rows = conn.execute("pragma database_list").fetchall()
        for row in rows:
            # sqlite3.Row indexing or tuple
            file_col = row[2] if not isinstance(row, dict) else row["file"]
            name_col = row[1] if not isinstance(row, dict) else row["name"]
            if name_col == "main" and file_col:
                return Database(f"sqlite:///{file_col}")
    except Exception as e:
        log.warning("auto_summary db adapt failed: %s", e)
    return None


def _render_one(
    conn,
    edition_date: str,
    out_path: Path,
    recent_editions: list[dict[str, Any]],
) -> Path:
    """Render a single edition date to out_path/index.html."""
    rows = conn.execute(
        """
        SELECT rank_position, headline, body, cited_sources_json,
               primary_entity_slug, primary_entity_type, generation_model
        FROM daily_takes
        WHERE edition_date = ?
        ORDER BY rank_position
        """,
        (edition_date,),
    ).fetchall()

    if not rows:
        log.warning("render_one(%s): no takes found in DB", edition_date)
        rows = []

    # Surface a transparent banner when this edition was assembled by the
    # offline-fallback synthesizer rather than the LLM pipeline. The
    # editorial audit flagged that fallback days read as templated; rather
    # than hide that, we tell the reader what they're looking at.
    fallback_used = any(
        (r[6] or "").lower() in ("offline-fallback", "stub", "")
        for r in rows
    ) if rows else False
    fallback_banner = (
        '<div class="daily-fallback-banner" style="margin: 16px 0; padding: 12px 16px; '
        'border: 1px solid #d0a050; background: #fff8e6; color: #4a3500; '
        'border-radius: 4px; font-size: 14px;">'
        '<strong>Editorial note:</strong> The Daily for this edition was '
        'assembled by the offline-fallback synthesizer (the LLM pipeline was '
        'unavailable at publish time). Tone and structure may read more '
        'templated than usual — replaced on the next live run.'
        '</div>'
        if fallback_used else ''
    )

    takes_html = "\n".join(
        _take_html(r[0], r[1], r[2], r[3], r[4] or "", r[5] or "event", conn=conn)
        for r in rows
    )
    takes_html = fallback_banner + takes_html

    # Sprint v5-7.6 — 30-second auto-summary above the takes list.
    # Pattern 7 from docs/design-system/34-integration-playbook.md.
    auto_summary_html = _build_auto_summary_html(rows, edition_date, conn)

    tpl = _load_template()
    # Distinguish today's edition (canonical /daily/) from archive entries
    # (/daily/<YYYY-MM-DD>/) so OG share-card canonical URLs are accurate.
    is_archive_entry = out_path.name != "daily" and out_path.parent.name == "daily"
    canonical_path = (
        f"/daily/{edition_date}/" if is_archive_entry else "/daily/"
    )
    html = tpl.substitute(
        title=f"The Daily — {_long_date(edition_date)}",
        long_date=_long_date(edition_date),
        auto_summary_html=auto_summary_html,
        takes_html=takes_html or "<p>No takes available for this edition.</p>",
        watching_html=_watching_html(),
        archive_links=_archive_links_html(recent_editions),
        page_description=(
            f"The Daily for {_long_date(edition_date)} — overnight CFB "
            f"takes, wire-event reactions, and the day's argument theater."
        ),
        page_canonical=absolute_url(canonical_path),
        og_image_url=absolute_url("/og-image.svg"),
    )

    out_path.mkdir(parents=True, exist_ok=True)
    dest = out_path / "index.html"
    dest.write_text(html, encoding="utf-8")
    log.info("rendered %s", dest)
    return dest


def render_daily(conn, edition_date: str, output_dir: str | None = None) -> list[Path]:
    """Render today's edition + archive entry. Returns list of paths written."""
    base = Path(output_dir) if output_dir else _SITE_DAILY
    base.mkdir(parents=True, exist_ok=True)

    recent = fetch_recent_editions(conn, limit=6)

    written: list[Path] = []

    # Archive entry
    archive_path = base / edition_date
    written.append(_render_one(conn, edition_date, archive_path, recent))

    # Current (index)
    written.append(_render_one(conn, edition_date, base, recent))

    # Archive index
    archive_index = _render_archive_index(conn, base, limit=30)
    written.append(archive_index)

    return written


def _render_archive_index(conn, base: Path, limit: int = 30) -> Path:
    """Render archive.html listing last `limit` editions."""
    editions = fetch_recent_editions(conn, limit=limit)

    rows_html = ""
    for ed in editions:
        date = ed["edition_date"]
        status = ed.get("status", "published")
        vv = "✓" if ed.get("voice_validator_passed") else "–"
        takes_count = ed.get("takes_count", 0)
        rows_html += (
            f'<tr>'
            f'<td><a href="/daily/{date}/">{_esc(_long_date(date))}</a></td>'
            f'<td>{_esc(status)}</td>'
            f'<td style="text-align:center">{takes_count}</td>'
            f'<td style="text-align:center">{vv}</td>'
            f'</tr>\n'
        )

    from cfb_rankings.database_archetype import (
        render_database_meta_footer as _db_archetype_footer,
    )
    from datetime import datetime as _dt, timezone as _tz
    _meta_footer = _db_archetype_footer(
        label=("edition tracked" if len(editions) == 1 else "editions tracked"),
        total_rows=len(editions),
        methodology_label="How The Daily ships",
        methodology_href="/methodology/",
        updated_text=f"Updated {_dt.now(_tz.utc).strftime('%Y-%m-%d')}",
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Daily — Archive</title>
<style>
body{{font-family:'Georgia',serif;background:#f8f6f0;color:#1a1a2e;max-width:760px;margin:3rem auto;padding:0 1rem;}}
h1{{font-size:2rem;margin-bottom:0.5rem;color:#0f2044;}}
.sub{{color:#4a5568;font-family:'Inter',sans-serif;font-size:0.8rem;margin-bottom:2rem;}}
table{{width:100%;border-collapse:collapse;font-family:'Inter',sans-serif;font-size:0.85rem;}}
th{{text-align:left;border-bottom:2px solid #c9a84c;padding:0.5rem;color:#0f2044;}}
td{{padding:0.5rem;border-bottom:1px solid #e2ddd5;}}
a{{color:#0f2044;}}
a:hover{{color:#c9a84c;}}
/* Inline Database-archetype meta-footer styles so the archive page
 * doesn't depend on the global stylesheet being loaded. Mirrors the
 * locked treatment in reporting._DATABASE_AND_ARTICLE_ARCHETYPES_CSS_BLOCK. */
.database-archetype__meta-footer{{display:flex;flex-wrap:wrap;align-items:center;gap:12px;padding:16px 0;margin-top:32px;border-top:1px solid rgba(15,32,68,0.12);font-size:12px;color:#4a5568;}}
.database-archetype__meta-link{{font-weight:700;color:#c9a84c;text-decoration:none;letter-spacing:0.04em;text-transform:uppercase;font-size:11px;}}
.database-archetype__meta-link:hover{{text-decoration:underline;}}
.database-archetype__meta-pill{{padding:4px 10px;border-radius:999px;background:rgba(15,32,68,0.04);border:1px solid rgba(15,32,68,0.08);font-size:11px;letter-spacing:0.04em;}}
</style>
</head>
<body class="daily__archive">
<nav style="font-family:'Inter',sans-serif;font-size:0.75rem;margin-bottom:2rem;">
<a href="/">CFB Index</a> · <a href="/daily/">The Daily</a>
</nav>
<h1>The Daily — Archive</h1>
<p class="sub">Last {limit} editions · <a href="/daily/">← Current edition</a></p>
<table>
<thead><tr><th>Edition</th><th>Status</th><th>Takes</th><th>Voice OK</th></tr></thead>
<tbody>{rows_html}</tbody>
</table>
{_meta_footer}
</body>
</html>"""

    dest = base / "archive.html"
    dest.write_text(html, encoding="utf-8")
    log.info("rendered archive index %s", dest)
    return dest


def fetch_recent_editions(conn, limit: int = 6) -> list[dict[str, Any]]:
    """Return last `limit` editions from DB ordered newest first."""
    try:
        rows = conn.execute(
            """
            SELECT e.edition_date, e.status, e.voice_validator_passed, e.generation_model,
                   COUNT(t.rank_position) AS takes_count
            FROM daily_editions e
            LEFT JOIN daily_takes t ON t.edition_date = e.edition_date
            GROUP BY e.edition_date
            ORDER BY e.edition_date DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "edition_date": r[0],
                "status": r[1],
                "voice_validator_passed": bool(r[2]),
                "generation_model": r[3],
                "takes_count": r[4],
            }
            for r in rows
        ]
    except Exception as exc:
        log.warning("fetch_recent_editions failed: %s", exc)
        return []
