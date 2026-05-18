"""Render the Transfer Portal Heat Index landing page.

Writes `output/site/portal-heat/index.html`. Style mirrors the wire
renderer (same palette, same chrome) so the page lands as a peer of /wire/.

Public surface:
    render_index(db, output_dir=..., days=14, now=None) -> Path
    render_all(db, output_dir=None, days=14, now=None)  -> dict
"""
from __future__ import annotations

import html
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

from cfb_rankings.common.cfb_calendar import cfb_week_label, days_to_kickoff
from cfb_rankings.portal_heat.data import (
    PortalMover,
    ProgramChurn,
    fetch_program_churn,
    last_entry_age_days,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared CSS — kept in this module (mirrors wire/renderer's pattern).
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
.page { max-width: 1280px; margin: 0 auto; padding: 0 clamp(24px, 5vw, 64px); }
.chrome { font-family: var(--sans); font-size: 11px; font-weight: 600;
  letter-spacing: 0.16em; text-transform: uppercase;
  display: flex; justify-content: space-between; padding: 12px 0; }
.brand-row { display: flex; align-items: baseline; justify-content: space-between;
  padding: 24px 0; }
.brand { font-family: var(--serif); font-size: 32px; font-weight: 700;
  letter-spacing: 0.04em; }
.brand .slash { color: var(--gold); margin: 0 6px; }
.rule { border: 0; height: 1px; background: var(--rule); margin: 0; }
.rule.soft { background: var(--rule-soft); }
a { color: inherit; text-decoration: none; }
a:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }
.eyebrow { font-family: var(--sans); font-size: 11px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--ink); }
.eyebrow.muted { color: var(--muted); }

.hero { padding: 72px 0 24px; }
.hero h1 { font-family: var(--serif); font-size: 56px; line-height: 1;
  font-weight: 600; color: var(--ink); margin: 12px 0 16px; }
.hero .lede { font-family: var(--serif); font-size: 20px; font-style: italic;
  line-height: 1.4; max-width: 760px; color: var(--ink); margin: 0; }
.hero .window-meta { font-family: var(--sans); font-size: 12px; font-weight: 600;
  letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted);
  margin: 24px 0 0; }

.empty-state { padding: 96px 0; text-align: center; }
.empty-state .roman { font-family: var(--serif); font-size: 48px; color: var(--muted);
  margin: 0 0 12px; }
.empty-state p { font-family: var(--serif); font-style: italic; font-size: 20px;
  color: var(--ink); margin: 8px 0 0; }

.board { padding: 32px 0; display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
.card { background: #fff; border: 1px solid var(--rule-soft); border-top: 4px solid var(--ink);
  padding: 20px 22px; position: relative; }
.card .rank { position: absolute; top: 18px; right: 22px; font-family: var(--serif);
  font-size: 28px; color: var(--muted); font-weight: 700; }
.card .program { font-family: var(--sans); font-size: 11px; font-weight: 700;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted);
  margin-bottom: 6px; }
.card h2 { font-family: var(--serif); font-size: 24px; line-height: 1.15;
  margin: 0 0 16px; padding-right: 48px; }
.card h2 a { border-bottom: 1px dotted currentColor; }

.delta-row { display: flex; gap: 16px; align-items: baseline; margin-bottom: 12px;
  font-family: var(--sans); font-size: 12px; font-weight: 700;
  letter-spacing: 0.12em; text-transform: uppercase; }
.delta-row .net { font-size: 26px; font-family: var(--serif); letter-spacing: 0; }
.delta-row .net.pos { color: var(--green); }
.delta-row .net.neg { color: var(--red); }
.delta-row .net.zero { color: var(--muted); }
.delta-row .ins-outs { color: var(--muted); }
.delta-row .ins-outs strong.in { color: var(--green); }
.delta-row .ins-outs strong.out { color: var(--red); }

.movers { list-style: none; padding: 0; margin: 8px 0 0; font-family: var(--sans);
  font-size: 13px; }
.movers li { padding: 6px 0; border-top: 1px dotted var(--rule-soft); }
.movers li:first-child { border-top: 0; }
.movers .arrow { font-weight: 700; margin-right: 6px; }
.movers .arrow.in { color: var(--green); }
.movers .arrow.out { color: var(--red); }
.movers .pos { color: var(--muted); margin-left: 4px; font-size: 11px;
  letter-spacing: 0.1em; text-transform: uppercase; }
.movers .stars { color: var(--gold); margin-left: 4px; }

.footer { padding: 64px 0 48px; }

@media (max-width: 720px) {
  .hero { padding: 48px 0 16px; }
  .hero h1 { font-size: 38px; }
  .hero .lede { font-size: 17px; }
  .card h2 { font-size: 20px; }
}
"""


# ---------------------------------------------------------------------------
# Template + render helpers.
# ---------------------------------------------------------------------------

def _templates_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def _load_template(name: str) -> str:
    return (_templates_dir() / name).read_text(encoding="utf-8")


def _substitute(template: str, tokens: dict[str, str]) -> str:
    out = template
    for key, value in tokens.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def _global_nav() -> str:
    """Render the global nav, but degrade gracefully when nav module errors.

    The nav module pulls a lot of imports at first call; if anything in
    the dependency chain isn't importable (e.g. minimal test DBs), we
    fall back to a tiny inline strip so the page still renders.
    """
    try:
        from cfb_rankings.nav import render_global_nav
        return render_global_nav(current_page="/portal-heat/", variant="desktop")
    except Exception as exc:  # pragma: no cover - nav is best-effort
        log.debug("portal_heat.renderer: nav unavailable (%s)", exc)
        return (
            '<nav class="nav"><a href="/">Home</a> '
            '<a href="/wire/">Wire</a></nav>'
        )


def _fmt_net(value: float) -> str:
    """Render a signed net Δ with a single decimal when fractional."""
    rounded = round(value, 1)
    if abs(rounded - round(rounded)) < 1e-9:
        rounded_int = int(round(rounded))
        return f"+{rounded_int}" if rounded_int > 0 else (str(rounded_int) if rounded_int < 0 else "0")
    return f"{rounded:+.1f}"


def _net_class(value: float) -> str:
    if value > 0:
        return "pos"
    if value < 0:
        return "neg"
    return "zero"


def _star_glyph(stars: int | None) -> str:
    if not stars or stars <= 0:
        return ""
    return "★" * min(int(stars), 5)


def _mover_li(m: PortalMover) -> str:
    direction = "in" if m.direction == "in" else "out"
    arrow = "↘" if direction == "in" else "↗"
    cp = m.counterpart_display or (m.counterpart_slug or "")
    if direction == "in":
        cp_label = f"from {cp}" if cp else "portal entry"
    else:
        cp_label = f"to {cp}" if cp else "portal exit"
    pos = f'<span class="pos">{html.escape(m.position)}</span>' if m.position else ""
    star = f' <span class="stars">{_star_glyph(m.stars)}</span>' if m.stars else ""
    return (
        f'<li><span class="arrow {direction}">{arrow}</span>'
        f'{html.escape(m.player_name)}{pos}{star} '
        f'<span class="pos">{html.escape(cp_label)}</span></li>'
    )


def _program_card(rank: int, churn: ProgramChurn) -> str:
    name_html = html.escape(churn.program_display)
    if churn.program_slug:
        program_link = (
            f'<a href="/teams/{html.escape(churn.program_slug, quote=True)}.html">'
            f'{name_html}</a>'
        )
    else:
        program_link = name_html

    net_class = _net_class(churn.net_delta)
    net_str = _fmt_net(churn.net_delta)

    movers_html = "\n".join(_mover_li(m) for m in churn.top_movers) or (
        '<li class="eyebrow muted">No headline movers in this window.</li>'
    )

    # Inline color accent — use primary color from team_brand_assets when known.
    accent = (churn.primary_color or "").strip()
    if accent and not accent.startswith("#"):
        # Tolerate raw 6-char hex.
        accent = "#" + accent if len(accent) in (3, 6) else ""
    border_style = (
        f' style="border-top-color: {html.escape(accent, quote=True)};"'
        if accent else ""
    )

    return (
        f'<article class="card"{border_style}>'
        f'<div class="rank">{rank:02d}</div>'
        f'<div class="program">{html.escape(churn.program_slug or "")}</div>'
        f'<h2>{program_link}</h2>'
        f'<div class="delta-row">'
        f'<span class="net {net_class}">{html.escape(net_str)}</span>'
        f'<span class="ins-outs">'
        f'<strong class="in">+{churn.entries} in</strong> · '
        f'<strong class="out">-{churn.exits} out</strong>'
        f'</span>'
        f'</div>'
        f'<ul class="movers">{movers_html}</ul>'
        f'</article>'
    )


def _board_html(rows: list[ProgramChurn]) -> str:
    return "\n".join(_program_card(i + 1, r) for i, r in enumerate(rows))


def _empty_state_html(db: Any, *, now: datetime) -> str:
    age = last_entry_age_days(db, now=now)
    if age is None:
        msg = "Portal cool — no moves on record yet. We'll fill this in as data lands."
    elif age == 0:
        msg = "Portal cool — last entry was today, but nothing inside the heat window."
    else:
        msg = f"Portal cool — last entry {age} days ago."
    return (
        '<section class="empty-state">'
        '<div class="roman">—</div>'
        f'<p>{html.escape(msg)}</p>'
        '</section>'
    )


# ---------------------------------------------------------------------------
# Public render functions.
# ---------------------------------------------------------------------------

def render_index(
    db: Any,
    *,
    output_dir: Path | None = None,
    days: int = 14,
    now: datetime | None = None,
) -> Path:
    """Render `<output_dir>/index.html`. Returns the written path.

    The renderer NEVER crashes on empty data — empty-state branch covers
    "no portal_moves rows", "table missing", "all rows outside window".
    """
    now = now or datetime.utcnow()
    today: date = now.date()
    output_dir = output_dir or Path("output/site/portal-heat")
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = fetch_program_churn(db, days=days, limit=25, now=now)

    week_label = _safe_label(today, db, fn=cfb_week_label)
    dtk = _safe_dtk(today, db)
    dtk_paren = f"({dtk} days to kickoff)" if dtk is not None else ""

    if rows:
        body = _board_html(rows)
        total_entries = sum(r.entries for r in rows)
        total_exits = sum(r.exits for r in rows)
        lede = (
            f"Top {len(rows)} programs by net Δ talent over the last "
            f"{days} days. {total_entries} entries, {total_exits} exits, "
            f"weighted by star rating where known."
        )
    else:
        body = _empty_state_html(db, now=now)
        lede = (
            "The Heat Index lights up when entries and exits start moving. "
            "We'll fill it in the moment CFBD shows fresh portal activity."
        )

    from cfb_rankings.nav import render_global_head_chrome, render_global_nav_actions
    template = _load_template("portal_heat.html")
    rendered = _substitute(template, {
        "TITLE": "Transfer Portal Heat Index",
        "UPDATED_AT": now.strftime("%Y-%m-%d %H:%M UTC"),
        "HEAD_CHROME": render_global_head_chrome(),
        "HEAD_STYLE": _BASE_STYLE,
        "GLOBAL_NAV": _global_nav(),
        "NAV_ACTIONS": render_global_nav_actions(),
        "WEEK_LABEL": html.escape(week_label),
        "DAYS_TO_KICKOFF_PAREN": html.escape(dtk_paren),
        "WINDOW_DAYS": str(days),
        "LEDE": html.escape(lede),
        "BOARD_OR_EMPTY": body,
    })

    out_path = output_dir / "index.html"
    out_path.write_text(rendered, encoding="utf-8")
    log.info(
        "portal_heat.renderer: wrote %s (%d programs, %d-day window)",
        out_path, len(rows), days,
    )
    return out_path


def render_all(
    db: Any,
    *,
    output_dir: Path | None = None,
    days: int = 14,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Top-level entry — renders the index page.

    Returns metadata dict for the CLI/workflow caller (paths + counts).
    """
    output_dir = output_dir or Path("output/site/portal-heat")
    index_path = render_index(db, output_dir=output_dir, days=days, now=now)
    # Re-read for counts so the CLI can log a coherent summary without
    # re-implementing the data fetch.
    churn = fetch_program_churn(db, days=days, limit=25, now=now or datetime.utcnow())
    return {
        "index": str(index_path),
        "programs": len(churn),
        "days_window": int(days),
    }


# ---------------------------------------------------------------------------
# cfb_calendar tolerance — DB-tolerant fallbacks.
# ---------------------------------------------------------------------------

def _safe_label(today: date, db: Any, *, fn) -> str:
    """Call cfb_week_label with the best DB handle we can produce.

    Project's Database wrapper isn't a sqlite3.Connection — cfb_week_label
    expects one. We pass None (which the calendar module handles via the
    KEY_EVENTS_BY_YEAR constants) when we can't get a raw connection.
    """
    conn = _raw_connection(db)
    try:
        return fn(today, conn)
    except Exception as exc:  # pragma: no cover - calendar is best-effort
        log.debug("portal_heat.renderer: week_label failed (%s)", exc)
        return "Offseason"


def _safe_dtk(today: date, db: Any) -> int | None:
    conn = _raw_connection(db)
    try:
        return int(days_to_kickoff(today, db=conn))
    except Exception as exc:  # pragma: no cover
        log.debug("portal_heat.renderer: days_to_kickoff failed (%s)", exc)
        return None


def _raw_connection(db: Any):
    """Return a sqlite3 connection if available, else None."""
    import sqlite3 as _sql
    if isinstance(db, _sql.Connection):
        return db
    # Project's Database wrapper opens-per-call; cfb_calendar reads cheaply
    # from constants when DB is None, which is fine for label rendering.
    return None


__all__ = ["render_all", "render_index"]
