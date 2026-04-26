"""Wire renderer — writes the public-facing Wire pages.

Outputs:
    output/site/wire/index.html              — last `days` days
    output/site/wire/archive/<YYYY-MM>.html  — one page per month with entries

Pattern: load templates from `wire/templates/*.html`, substitute the
`{{TOKEN}}` placeholders, and write straight to disk. Matches the
existing static-site model.
"""
from __future__ import annotations

import html
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from cfb_rankings.db import Database

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared CSS — pulled inline into every Wire page. Mirrors the homepage
# palette tokens so the Wire feels native to the rest of the product.
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
  font-family: var(--serif); font-size: 17px; line-height: 1.55; }
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

.hero { padding: 72px 0 48px; }
.hero-wire .roman-big { font-family: var(--serif); font-size: 64px; line-height: 1;
  font-weight: 600; color: var(--ink); margin: 12px 0 16px; }
.hero-wire .lede { font-family: var(--serif); font-size: 22px; font-style: italic;
  line-height: 1.4; max-width: 720px; color: var(--ink); margin: 16px 0 0; }
.archive-nav { font-family: var(--sans); font-size: 12px; font-weight: 600;
  letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted);
  margin-top: 24px; }
.archive-nav a { color: var(--ink); border-bottom: 1px dotted currentColor; }

.dept { padding: 32px 0; }
.dept-head { display: flex; gap: 24px; align-items: baseline; padding-bottom: 16px; }
.dept-head .roman { font-family: var(--serif); font-size: 32px; color: var(--gold); }
.dept-head .label { font-family: var(--sans); font-size: 13px; font-weight: 700;
  letter-spacing: 0.2em; text-transform: uppercase; }
.dept-head .meta { font-family: var(--sans); font-size: 11px; color: var(--muted);
  letter-spacing: 0.16em; text-transform: uppercase; }

.wire-table { width: 100%; border-collapse: collapse; font-family: var(--sans);
  font-size: 14px; }
.wire-table th { text-align: left; padding: 12px 16px 12px 0; font-weight: 700;
  letter-spacing: 0.14em; text-transform: uppercase; font-size: 11px;
  color: var(--muted); border-bottom: 1px solid var(--rule); }
.wire-table td { padding: 14px 16px 14px 0; border-bottom: 1px solid var(--rule-soft);
  vertical-align: top; }
.wire-table td.when { color: var(--muted); font-variant-numeric: tabular-nums;
  white-space: nowrap; width: 92px; }
.wire-table td.program { font-weight: 700; width: 168px; }
.wire-table td.program a { border-bottom: 1px dotted currentColor; }
.wire-table td.action { width: 240px; }
.wire-table td.why { font-family: var(--serif); font-size: 16px; line-height: 1.4;
  color: var(--ink); }
.wire-table td.why .hist-comp { display: block; margin-top: 4px;
  color: var(--muted); font-size: 14px; font-style: italic; }
.wire-table td.impact { width: 132px; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; font-size: 11px; }
.wire-table td.impact.amber { color: var(--amber); }
.wire-table td.impact.muted { color: var(--muted); }
.wire-table td.impact.green { color: var(--green); }
.wire-table td.impact.red   { color: var(--red); }

.archive-list { list-style: none; padding: 0; margin: 0; columns: 2;
  font-family: var(--sans); font-size: 14px; }
.archive-list li { padding: 8px 0; }
.archive-list a { border-bottom: 1px dotted currentColor; }

.footer { padding: 64px 0 48px; }

@media (max-width: 720px) {
  .hero { padding: 48px 0 24px; }
  .hero-wire .roman-big { font-size: 44px; }
  .hero-wire .lede { font-size: 18px; }
  .wire-table { font-size: 13px; }
  .wire-table td.action { width: auto; }
  .wire-table td.program { width: 110px; }
  .wire-table td.when { width: 64px; }
  .wire-table td.why { font-size: 15px; }
}
"""


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------

def _templates_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def _load_template(name: str) -> str:
    return (_templates_dir() / name).read_text(encoding="utf-8")


def _format_when(occurred_at_str: str, *, now: datetime | None = None) -> str:
    """Friendly ticker timestamp.

    Today               -> "HH:MM ET"
    Yesterday           -> "Yesterday"
    Within last 7 days  -> "<N>d"
    Else                -> "Mar 14"
    """
    now = now or datetime.utcnow()
    try:
        occurred = datetime.fromisoformat(occurred_at_str)
    except ValueError:
        return occurred_at_str
    diff_days = (now.date() - occurred.date()).days
    if diff_days <= 0:
        return f"{occurred.strftime('%H:%M')} ET"
    if diff_days == 1:
        return "Yesterday"
    if diff_days < 7:
        return f"{diff_days}d"
    return _safe_strftime(occurred, "%b %-d")


def _safe_strftime(d: datetime, fmt: str) -> str:
    """%-d on Windows requires a fallback to %#d."""
    try:
        return d.strftime(fmt)
    except (ValueError, OSError):
        return d.strftime(fmt.replace("%-d", "%#d"))


def _program_link(slug: str | None, display: str) -> str:
    """Render program cell — link to /teams/<slug>/ when we have a slug."""
    safe_display = html.escape(display or "")
    if slug:
        safe_slug = html.escape(slug, quote=True)
        return f'<a href="/teams/{safe_slug}/">{safe_display}</a>'
    return safe_display


def _row_html(row: dict[str, Any], *, now: datetime | None = None) -> str:
    when = html.escape(_format_when(str(row.get("occurred_at", "")), now=now))
    program = _program_link(row.get("program_slug"), row.get("program_display") or "")
    action = html.escape(row.get("action") or "")
    why = html.escape(row.get("why_it_matters") or "")
    historical = row.get("historical_comp")
    if historical:
        why += f'<span class="hist-comp">{html.escape(historical)}</span>'
    impact_label = html.escape(row.get("impact_label") or "MINOR")
    impact_color = (row.get("impact_color") or "muted").lower()
    if impact_color not in ("amber", "muted", "green", "red"):
        impact_color = "muted"

    return (
        "<tr>"
        f'<td class="when">{when}</td>'
        f'<td class="program">{program}</td>'
        f'<td class="action">{action}</td>'
        f'<td class="why">{why}</td>'
        f'<td class="impact {impact_color}">{impact_label}</td>'
        "</tr>"
    )


def _entries_tbody(rows: Iterable[dict[str, Any]], *, now: datetime | None = None) -> str:
    return "\n".join(_row_html(r, now=now) for r in rows)


def _substitute(template: str, tokens: dict[str, str]) -> str:
    out = template
    for key, value in tokens.items():
        out = out.replace("{{" + key + "}}", value)
    return out


# ---------------------------------------------------------------------------
# Data access.
# ---------------------------------------------------------------------------

def fetch_recent(db: Database, *, days: int) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select id, occurred_at, program_slug, program_display, actor_kind,
               action, why_it_matters, impact_label, impact_color,
               historical_comp, source_kind, source_url, source_name,
               related_thread_slug, fan_intel_velocity_spike
        from wire_entries
        where occurred_at >= datetime('now', :since)
          and trim(why_it_matters) <> ''
        order by occurred_at desc
        """,
        {"since": f"-{int(days)} days"},
    )


def fetch_for_month(db: Database, *, year: int, month: int) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select id, occurred_at, program_slug, program_display, actor_kind,
               action, why_it_matters, impact_label, impact_color,
               historical_comp
        from wire_entries
        where strftime('%Y', occurred_at) = :y
          and strftime('%m', occurred_at) = :m
          and trim(why_it_matters) <> ''
        order by occurred_at desc
        """,
        {"y": f"{year:04d}", "m": f"{month:02d}"},
    )


def list_archive_months(db: Database) -> list[tuple[int, int, int]]:
    """Returns a list of (year, month, count) tuples covering every month
    that has at least one Wire entry."""
    rows = db.query_all(
        """
        select cast(strftime('%Y', occurred_at) as integer) as y,
               cast(strftime('%m', occurred_at) as integer) as m,
               count(*) as n
        from wire_entries
        where trim(why_it_matters) <> ''
        group by y, m
        order by y desc, m desc
        """
    )
    return [(int(r["y"]), int(r["m"]), int(r["n"])) for r in rows]


# ---------------------------------------------------------------------------
# Render functions.
# ---------------------------------------------------------------------------

def render_wire_index(
    db: Database,
    *,
    output_dir: Path,
    days: int = 30,
    now: datetime | None = None,
) -> Path:
    """Render the Wire index page (last `days` days)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = fetch_recent(db, days=days)
    archive_months = list_archive_months(db)

    archive_links = "\n".join(
        f'<li><a href="/wire/archive/{year:04d}-{month:02d}.html">'
        f'{datetime(year, month, 1).strftime("%B %Y")}</a> '
        f'<span class="eyebrow muted" style="margin-left:8px;">{count} entries</span></li>'
        for year, month, count in archive_months
    )
    if not archive_links:
        archive_links = "<li class=\"eyebrow muted\">No archive months yet.</li>"

    template = _load_template("wire.html")
    rendered = _substitute(template, {
        "TITLE": "The Wire",
        "UPDATED_AT": (now or datetime.utcnow()).strftime("%Y-%m-%d %H:%M UTC"),
        "HEAD_STYLE": _BASE_STYLE,
        "ENTRIES_TBODY": _entries_tbody(rows, now=now),
        "ARCHIVE_LINKS": archive_links,
        "ENTRY_COUNT": str(len(rows)),
        "WINDOW_DAYS": str(days),
    })

    out_path = output_dir / "index.html"
    out_path.write_text(rendered, encoding="utf-8")
    log.info("wire.renderer: wrote %s (%d entries)", out_path, len(rows))
    return out_path


def render_archive_month(
    db: Database,
    *,
    output_dir: Path,
    year: int,
    month: int,
    prev_link: str = "",
    next_link: str = "",
    now: datetime | None = None,
) -> Path:
    archive_dir = output_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    rows = fetch_for_month(db, year=year, month=month)
    label = datetime(year, month, 1).strftime("%B %Y")

    template = _load_template("wire_archive.html")
    rendered = _substitute(template, {
        "TITLE": f"The Wire — {label}",
        "HEAD_STYLE": _BASE_STYLE,
        "MONTH_LABEL": label,
        "ENTRY_COUNT": str(len(rows)),
        "ENTRIES_TBODY": _entries_tbody(rows, now=now),
        "PREV_LINK": prev_link,
        "NEXT_LINK": next_link,
        "UPDATED_AT": (now or datetime.utcnow()).strftime("%Y-%m-%d %H:%M UTC"),
    })

    out_path = archive_dir / f"{year:04d}-{month:02d}.html"
    out_path.write_text(rendered, encoding="utf-8")
    log.info("wire.renderer: wrote %s (%d entries)", out_path, len(rows))
    return out_path


def render_all(
    db: Database,
    *,
    output_dir: Path | None = None,
    days: int = 30,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Top-level entry point. Renders the index + every archive month."""
    output_dir = output_dir or Path("output/site/wire")
    output_dir.mkdir(parents=True, exist_ok=True)

    index_path = render_wire_index(db, output_dir=output_dir, days=days, now=now)

    months = list_archive_months(db)
    archive_paths: list[Path] = []
    for i, (year, month, _count) in enumerate(months):
        prev = months[i + 1] if i + 1 < len(months) else None
        nxt = months[i - 1] if i > 0 else None
        prev_link = (
            f'<a href="/wire/archive/{prev[0]:04d}-{prev[1]:02d}.html">'
            f'← {datetime(prev[0], prev[1], 1).strftime("%B %Y")}</a>'
            if prev else ""
        )
        next_link = (
            f'<a href="/wire/archive/{nxt[0]:04d}-{nxt[1]:02d}.html">'
            f'{datetime(nxt[0], nxt[1], 1).strftime("%B %Y")} →</a>'
            if nxt else ""
        )
        path = render_archive_month(
            db, output_dir=output_dir, year=year, month=month,
            prev_link=prev_link, next_link=next_link, now=now,
        )
        archive_paths.append(path)

    return {
        "index": str(index_path),
        "archive_pages": [str(p) for p in archive_paths],
        "archive_months": [(y, m) for y, m, _ in months],
    }


# Re-export the row builder for the homepage integration.
def render_row_html(row: dict[str, Any], *, now: datetime | None = None) -> str:
    return _row_html(row, now=now)
