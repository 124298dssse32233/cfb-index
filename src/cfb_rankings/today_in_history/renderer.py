"""S5 — Today in CFB History renderer.

Writes ``output/site/anniversary/today/index.html`` (the canonical page)
+ a sibling ``data.json`` payload usable by the homepage strip widget.

Stylistically mirrors the editions archive renderer (serif on beige
"paper" background, gold rules) so the surface feels part of the same
CFB Index visual system.

The page is the offseason safety net — it must never 404 and must
always produce at least one file (the HTML page) even when the DB has
nothing. The empty state is a deliberate "Quiet day in CFB history"
moment, not an error.
"""
from __future__ import annotations

import html
import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from cfb_rankings.common.cfb_calendar import (
    cfb_week_label,
    days_to_kickoff,
    human_date_phrase,
    human_phase_label,
)

from .data import AnniversaryCard, gather_today_in_history_cards

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = "output/site/anniversary/today"


# ---------------------------------------------------------------------------
# CSS — concentrated; mirrors editions/archive_renderer.py palette so the
# anniversary page sits in the same visual family.
# ---------------------------------------------------------------------------

_CSS = """
*, *::before, *::after { box-sizing: border-box; }
:root {
  --ink: #1a1a1a;
  --paper: #f6f1e6;
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
.page { max-width: 980px; margin: 0 auto; padding: 0 32px; }
hr.rule { border: 0; height: 1px; background: var(--rule); margin: 0; }
hr.rule.gold { background: var(--gold); height: 3px; }
hr.rule.soft { background: var(--rule-soft); }

/* Masthead */
.masthead { padding: 28px 0 14px; }
.masthead .chrome { display: flex; justify-content: space-between;
  font-family: var(--sans); font-size: 10px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--ink);
  padding-bottom: 12px; }
.masthead .brand-row { display: flex; align-items: baseline;
  padding: 22px 0; gap: 36px; }
.masthead .brand { font-family: var(--serif); font-size: 44px; font-weight: 700;
  letter-spacing: -0.02em; }
.masthead .brand .slash { color: var(--gold); margin: 0 2px; }
.masthead .nav { margin-left: auto; display: flex; gap: 24px;
  font-family: var(--sans); font-size: 12px; font-weight: 600;
  letter-spacing: 0.16em; text-transform: uppercase; }
.masthead .nav a { color: var(--ink); text-decoration: none;
  border-bottom: 1px solid transparent; padding-bottom: 2px; }
.masthead .nav a:hover { border-bottom-color: var(--gold); }

/* Hero */
.hero { padding: 48px 0 24px; }
.hero .eyebrow { font-family: var(--sans); font-size: 11px; font-weight: 700;
  letter-spacing: 0.24em; text-transform: uppercase; color: var(--muted);
  margin-bottom: 12px; }
.hero h1 { font-family: var(--serif); font-size: 72px; line-height: 1.02;
  font-weight: 700; margin: 0; letter-spacing: -0.01em; }
.hero .dateline { font-family: var(--sans); font-size: 12px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--ink);
  margin-top: 20px; }
.hero .phase { font-family: var(--sans); font-size: 12px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted);
  margin-top: 4px; }

/* Cards */
.cards { padding: 36px 0 96px; display: grid; gap: 36px; }
.card { border-top: 1px solid var(--rule); padding-top: 24px;
  display: grid; grid-template-columns: 160px 1fr; gap: 28px; align-items: start; }
.card:first-of-type { border-top: 3px solid var(--gold); padding-top: 24px; }
.card .stamp { font-family: var(--serif); font-size: 48px; line-height: 1;
  font-weight: 600; color: var(--ink); }
.card .stamp .ago { display: block; font-family: var(--sans); font-size: 11px;
  font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--muted); margin-top: 8px; }
.card h2 { font-family: var(--serif); font-size: 30px; line-height: 1.18;
  font-weight: 700; margin: 0 0 10px; }
.card h2 a { color: var(--ink); text-decoration: none; border-bottom: 1px solid var(--rule-soft); }
.card h2 a:hover { border-bottom-color: var(--gold); color: var(--navy); }
.card p.body { font-family: var(--serif); font-size: 17px; line-height: 1.55;
  margin: 0 0 12px; color: var(--ink); }
.card .attribution { font-family: var(--sans); font-size: 11px; font-weight: 600;
  letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted); }
.card .source-tag { display: inline-block; margin-left: 8px; padding: 2px 8px;
  background: var(--paper); border: 1px solid var(--rule-soft);
  color: var(--ink); font-size: 9px; letter-spacing: 0.2em; }

/* Empty state */
.empty { padding: 56px 0 96px; text-align: center; }
.empty h2 { font-family: var(--serif); font-size: 36px; font-weight: 600;
  margin: 0 0 16px; }
.empty p { font-family: var(--serif); font-size: 18px; max-width: 560px;
  margin: 0 auto; color: var(--ink); }

/* Footer */
.footer { border-top: 1px solid var(--rule); padding: 24px 0 40px;
  font-family: var(--sans); font-size: 11px; color: var(--muted);
  letter-spacing: 0.14em; text-transform: uppercase; }
.footer a { color: var(--muted); text-decoration: none; }
.footer a:hover { color: var(--ink); }

@media (max-width: 720px) {
  .hero h1 { font-size: 48px; }
  .card { grid-template-columns: 1fr; gap: 12px; }
  .card .stamp { font-size: 36px; }
  .card h2 { font-size: 24px; }
}
"""


# ---------------------------------------------------------------------------
# Entry — orchestrator
# ---------------------------------------------------------------------------

def render_today_in_history_page(
    db: Any,
    *,
    today: date | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    max_cards: int = 5,
) -> dict[str, int | list[str]]:
    """Render the S5 anniversary surface.

    Writes:
      * ``<output_dir>/index.html`` — the canonical page
      * ``<output_dir>/data.json`` — payload for the homepage strip widget

    Returns stats: ``{'cards_rendered', 'output_files'}``.
    """
    today = today or _utc_today()
    cards = gather_today_in_history_cards(db, today=today, max_cards=max_cards)

    week_label = _safe_label(today, db, cfb_week_label, default="")
    phase_label = _safe_label(today, db, human_phase_label, default="")
    try:
        dtk = days_to_kickoff(today, db=db)
    except Exception as exc:  # noqa: BLE001 — graceful
        logger.debug("today_in_history: days_to_kickoff failed: %s", exc)
        dtk = None

    html_text = render_today_in_history_html(
        cards=cards,
        today=today,
        week_label=week_label,
        phase_label=phase_label,
        days_to_kickoff_value=dtk,
    )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    index_path = out_dir / "index.html"
    index_path.write_text(html_text, encoding="utf-8")

    data_path = out_dir / "data.json"
    payload = {
        "generated_at_utc": _utcnow_iso(),
        "today": today.isoformat(),
        "week_label": week_label,
        "phase_label": phase_label,
        "days_to_kickoff": dtk,
        "cards": [c.to_dict() for c in cards],
    }
    data_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "cards_rendered": len(cards),
        "output_files": [str(index_path), str(data_path)],
    }


# ---------------------------------------------------------------------------
# HTML construction
# ---------------------------------------------------------------------------

def render_today_in_history_html(
    *,
    cards: list[AnniversaryCard],
    today: date,
    week_label: str = "",
    phase_label: str = "",
    days_to_kickoff_value: int | None = None,
) -> str:
    """Build the standalone HTML page. Side-effect-free."""
    date_phrase = human_date_phrase(today)
    dateline_bits: list[str] = [date_phrase]
    if week_label:
        dateline_bits.append(week_label)

    if cards:
        body_html = _cards_html(cards)
    else:
        body_html = _empty_state_html(week_label=week_label, phase_label=phase_label)

    dateline = " · ".join(html.escape(bit) for bit in dateline_bits if bit)
    phase_meta = ""
    if phase_label and days_to_kickoff_value is not None and days_to_kickoff_value > 0:
        phase_meta = (
            f'<div class="phase">{html.escape(phase_label)} · '
            f'{days_to_kickoff_value} day{"s" if days_to_kickoff_value != 1 else ""} to kickoff</div>'
        )
    elif phase_label:
        phase_meta = f'<div class="phase">{html.escape(phase_label)}</div>'

    generated_at = _utcnow_iso()

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Today in CFB History · CFB Index</title>
  <meta name="description" content="On this date in college football — anniversary cards anchored on real history, refreshed daily.">
  <style>{_CSS}</style>
</head>
<body>
  <header class="masthead">
    <div class="page">
      <div class="chrome">
        <span>TODAY IN CFB HISTORY</span>
        <span>CFB · INDEX</span>
        <span>{len(cards)} {'CARD' if len(cards) == 1 else 'CARDS'}</span>
      </div>
      <hr class="rule">
      <div class="brand-row">
        <div class="brand">CFB<span class="slash">/</span>INDEX</div>
        <nav class="nav">
          <a href="/">Home</a>
          <a href="/rankings/">Rankings</a>
          <a href="/daily/">Daily</a>
          <a href="/wire/">Wire</a>
          <a href="/editions/">Editions</a>
          <a href="/methodology/">Methodology</a>
        </nav>
      </div>
      <hr class="rule">
    </div>
  </header>

  <section class="hero">
    <div class="page">
      <div class="eyebrow">ON THIS DATE</div>
      <h1>On This Date in College Football</h1>
      <div class="dateline">{dateline}</div>
      {phase_meta}
    </div>
  </section>

  <section class="cards">
    <div class="page">
      {body_html}
    </div>
  </section>

  <footer class="footer">
    <div class="page">
      <span>CFB · INDEX</span> &nbsp;·&nbsp;
      <span>Today in CFB History</span> &nbsp;·&nbsp;
      <span>Generated {html.escape(generated_at)}</span> &nbsp;·&nbsp;
      <a href="/">Home</a> &nbsp;·&nbsp;
      <a href="/methodology/">Methodology</a>
    </div>
  </footer>
</body>
</html>
"""


def _cards_html(cards: list[AnniversaryCard]) -> str:
    pieces: list[str] = []
    for card in cards:
        headline = html.escape(card.headline or "(untitled)")
        if card.url:
            headline_html = f'<a href="{html.escape(card.url)}" rel="noopener external">{headline}</a>'
        else:
            headline_html = headline
        years_ago_label = (
            "1 year ago today" if card.years_ago == 1 else f"{card.years_ago} years ago today"
        )
        source_label = _source_label(card.source)
        body_html = html.escape(card.body or "") if card.body else ""
        body_block = f'<p class="body">{body_html}</p>' if body_html else ""
        attribution_html = html.escape(card.attribution or "")
        pieces.append(f"""
        <article class="card">
          <div class="stamp">
            {card.year}
            <span class="ago">{html.escape(years_ago_label)}</span>
          </div>
          <div class="body-col">
            <h2>{headline_html}</h2>
            {body_block}
            <div class="attribution">{attribution_html}<span class="source-tag">{html.escape(source_label)}</span></div>
          </div>
        </article>
        """)
    return "\n".join(pieces)


def _empty_state_html(*, week_label: str, phase_label: str) -> str:
    sub = ""
    if week_label or phase_label:
        chosen = week_label or phase_label
        sub = f'<p>We&rsquo;re in {html.escape(chosen)} and nothing notable matches this date in the archive. Check back tomorrow.</p>'
    else:
        sub = "<p>Nothing notable matches this date in the archive. Check back tomorrow.</p>"

    return f"""
    <div class="empty">
      <h2>Quiet day in CFB history.</h2>
      {sub}
    </div>
    """


def _source_label(source: str) -> str:
    return {
        "archive_threads": "Reddit archive",
        "team_chronicle": "Chronicle",
        "historical_season": "Season recap",
    }.get(source, source)


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------

def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_label(today: date, db: Any, fn: Any, *, default: str = "") -> str:
    """Call cfb_calendar helper that may raise on Database-vs-Connection
    mismatch. Returns ``default`` on any error."""
    try:
        return fn(today, db) or default
    except Exception as exc:  # noqa: BLE001 — graceful
        logger.debug("today_in_history: %s failed: %s", getattr(fn, "__name__", fn), exc)
        return default


__all__ = [
    "render_today_in_history_html",
    "render_today_in_history_page",
]
