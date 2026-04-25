"""Render helpers for Storyline Threads.

Pure-Python helpers (no external deps). Markdown-light to HTML, drop-cap
wrapping, citation formatting, datetime humanization.

The markdown subset we support is intentionally small — paragraphs,
blockquotes, links, *em*, **strong**, smart-quote preservation. This
matches what we ask Sonnet to produce in the seed-author prompts.
"""
from __future__ import annotations

import html
import json
import re
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Datetime humanization
# ---------------------------------------------------------------------------

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    s = str(value).strip()
    if not s:
        return None
    # Try common SQLite formats.
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def humanize_date(value: Any) -> str:
    dt = parse_dt(value)
    if dt is None:
        return "—"
    return f"{_MONTHS[dt.month - 1]} {dt.day}, {dt.year}"


def humanize_date_short(value: Any) -> str:
    dt = parse_dt(value)
    if dt is None:
        return "—"
    return f"{_MONTHS[dt.month - 1]} {dt.day}"


# ---------------------------------------------------------------------------
# Markdown-light renderer
# ---------------------------------------------------------------------------

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_STRONG_RE = re.compile(r"\*\*([^*\n]+?)\*\*")
_EM_RE = re.compile(r"(?<!\*)\*([^*\n]+?)\*(?!\*)")


def _inline(text: str) -> str:
    """Apply inline markdown (link, strong, em) to an already HTML-escaped string.

    Order matters: links → strong → em. We escape first, then unescape
    the markdown delimiters before applying.
    """
    # Escape HTML, then convert markdown markers (which are now safe
    # because the underlying chars are already escaped, but `*` and
    # `[` are not escaped by html.escape — only `<`, `>`, `&`, `"`, `'`).
    escaped = html.escape(text, quote=False)

    def _link_sub(match: re.Match) -> str:
        label = match.group(1)
        href = match.group(2)
        if href.lower() in ("none", "null", ""):
            return label  # no real URL — render as plain text
        # href is escaped via html.escape on the wrapping text already;
        # additionally guard quotes here.
        href_safe = href.replace('"', '&quot;')
        return f'<a href="{href_safe}">{label}</a>'

    escaped = _LINK_RE.sub(_link_sub, escaped)
    escaped = _STRONG_RE.sub(r"<strong>\1</strong>", escaped)
    escaped = _EM_RE.sub(r"<em>\1</em>", escaped)
    return escaped


def markdown_light_to_html(md: str) -> str:
    """Convert the supported markdown subset to HTML.

    Subset: blank-line-separated paragraphs, blockquotes (lines starting
    with `> `), links `[text](url)` (treats `url=None`/`null`/empty as
    plain text), em `*x*`, strong `**x**`. Smart quotes pass through
    unchanged.
    """
    if not md:
        return ""

    # Normalize line endings.
    md = md.replace("\r\n", "\n").replace("\r", "\n").strip()

    # Split into blocks on blank lines.
    blocks = re.split(r"\n\s*\n", md)
    out: list[str] = []
    for block in blocks:
        block = block.strip("\n")
        if not block.strip():
            continue
        lines = block.split("\n")
        if all(line.lstrip().startswith(">") for line in lines):
            # Blockquote — strip the leading >, join with <br> if multi-line
            quoted_lines = [re.sub(r"^\s*>\s?", "", line) for line in lines]
            inner = " ".join(_inline(line) for line in quoted_lines)
            out.append(f"<blockquote><p>{inner}</p></blockquote>")
        else:
            # Paragraph — collapse internal newlines into spaces
            joined = " ".join(line.strip() for line in lines if line.strip())
            out.append(f"<p>{_inline(joined)}</p>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Source citation rendering
# ---------------------------------------------------------------------------

def render_sources(sources_json: str | None) -> str:
    """Render a JSON-array of source dicts as a list of <li> cards."""
    if not sources_json:
        return ""
    try:
        sources = json.loads(sources_json)
    except (json.JSONDecodeError, TypeError):
        return ""
    items: list[str] = []
    for src in sources:
        kind = html.escape(str(src.get("kind", "")), quote=True).upper()
        name = html.escape(str(src.get("name", "")), quote=True)
        label = html.escape(str(src.get("label", "")), quote=True)
        date_s = src.get("date") or ""
        date_disp = humanize_date_short(date_s) if date_s else ""
        url = src.get("url")
        name_html = f'<span class="src-name">{name}</span>'
        if url and isinstance(url, str) and url not in ("None", "null"):
            url_safe = html.escape(url, quote=True)
            name_html = f'<a href="{url_safe}"><span class="src-name">{name}</span></a>'
        bits = []
        if kind:
            bits.append(f'<span class="kind">{kind}</span>')
        bits.append(name_html)
        if label:
            bits.append(f'· {label}')
        if date_disp:
            bits.append(f'· {date_disp}')
        items.append(f'<li>{" ".join(bits)}</li>')
    return "\n".join(items)


# ---------------------------------------------------------------------------
# Pull quote
# ---------------------------------------------------------------------------

def render_pull_quote(quote: str | None) -> str:
    if not quote or not quote.strip():
        return ""
    return (
        f'<aside class="pull-quote">\u201c{html.escape(quote.strip(), quote=False)}\u201d</aside>'
    )


# ---------------------------------------------------------------------------
# Referenced chapters callout
# ---------------------------------------------------------------------------

def render_referenced_callout(
    referenced_ids_json: str | None,
    chapters_by_number: dict[int, dict],
    thread_slug: str,
) -> str:
    if not referenced_ids_json:
        return ""
    try:
        ids = json.loads(referenced_ids_json)
    except (json.JSONDecodeError, TypeError):
        return ""
    if not ids:
        return ""
    rows: list[str] = []
    for n in ids:
        ch = chapters_by_number.get(int(n))
        if not ch:
            continue
        title = html.escape(ch["title"], quote=False)
        href = f"#chapter-{int(n)}"
        rows.append(
            f'<div class="ref-row"><span class="ref-num">CH {int(n):02d}</span>'
            f'<a href="{href}">{title}</a></div>'
        )
    if not rows:
        return ""
    return (
        '<div class="referenced-chapters">'
        '<div class="label">Builds on prior chapters</div>'
        + "".join(rows) +
        '</div>'
    )


# ---------------------------------------------------------------------------
# Word-count display
# ---------------------------------------------------------------------------

def humanize_word_count(n: int | None) -> str:
    if n is None or n <= 0:
        return "0"
    if n < 1000:
        return str(n)
    return f"{n / 1000:.1f}k".replace(".0k", "k")


# ---------------------------------------------------------------------------
# Status label
# ---------------------------------------------------------------------------

def status_label(status: str | None) -> str:
    if not status:
        return "Unknown"
    return {"active": "Active", "resolved": "Resolved", "archived": "Archived"}.get(
        status.lower(), status.capitalize()
    )
