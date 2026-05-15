"""Conference Pulse section renderer.

Renders the Pulse v2 HTML fragment for a conference page. Reads pre-generated
themes + ledes from conference_themes table. Falls back to stock-phrase copy
for conferences without generated content (6 mid-tier leagues by design).

Standalone render: render_conference_pulse_section(slug, conn) → HTML str
Full render:       render_all_conferences(conn, output_dir) → summary dict

The HTML fragment is structured to match the Pulse v2 section spec:
  <section class="pulse conf-pulse"> ... </section>
Suitable for injection into an existing conference page or standalone file.
"""
from __future__ import annotations

import html as _html
import logging
import os
from typing import Any

log = logging.getLogger(__name__)

_TOP_5 = {"sec", "big-ten", "acc", "big-12", "american-athletic"}

_STOCK_LEDE: dict[str, str] = {
    "mountain-west": "The Mountain West keeps producing draft-ready talent while the room stays quiet.",
    "conference-usa": "C-USA programs are grinding. The signal is thin but the work isn't.",
    "sun-belt": "Sun Belt football punches above its weight — the fans know it.",
    "fbs-mac": "The MAC plays on Tuesday nights while everyone else is asleep. The outcomes still matter.",
    "swac": "SWAC football carries a tradition that national media keeps underselling.",
    "american-athletic": "The AAC is moving. Conversation is picking up across the board.",
    "fbs-independents": "No conference. No schedule protection. No excuses.",
    "pac-12": "Whatever the Pac-12 becomes next, the football was real.",
}

_CONF_DISPLAY: dict[str, str] = {
    "sec": "SEC",
    "fbs-big-ten": "Big Ten",
    "acc": "ACC",
    "big-12": "Big 12",
    "american-athletic": "American Athletic",
    "mountain-west": "Mountain West",
    "conference-usa": "Conference USA",
    "sun-belt": "Sun Belt",
    "fbs-mac": "MAC",
    "swac": "SWAC",
    "fbs-independents": "FBS Independents",
}


def _load_conference_data(conference_slug: str, db_conn: Any) -> dict[str, Any]:
    """Load themes + lede from conference_themes table.

    Defensive: conference_themes table is created by the prepare-pulse
    pipeline. If it doesn't exist yet (fresh DB, pipeline never ran),
    return empty themes rather than crashing the renderer.
    """
    import sqlite3
    cur = db_conn.cursor()
    try:
        cur.execute(
            """
            SELECT label, summary, representative_quote, delta_label, surfaced_rank
            FROM conference_themes
            WHERE conference_slug = ?
            ORDER BY surfaced_rank
            """,
            (conference_slug,),
        )
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        rows = []
    if not rows:
        return {"themes": [], "lede": None}

    themes = []
    lede = None
    for row in rows:
        if row[4] == 1 and row[3]:  # delta_label on rank-1 row = lede
            lede = row[3]
        if row[0] and row[0] != "Pulse Lede":  # skip placeholder rows
            themes.append({
                "label": row[0],
                "summary": row[1] or "",
                "quote": row[2] or "",
            })
    return {"themes": themes, "lede": lede}


def _sentiment_bars(positive: int, neutral: int, negative: int) -> str:
    total = positive + neutral + negative
    if total == 0:
        return ""
    p_pct = round(100 * positive / total)
    n_pct = round(100 * neutral / total)
    neg_pct = 100 - p_pct - n_pct
    return (
        f'<div class="conf-pulse__sentiment">'
        f'<div class="conf-pulse__sentiment-bar conf-pulse__sentiment-bar--pos" '
        f'style="width:{p_pct}%" title="positive {p_pct}%"></div>'
        f'<div class="conf-pulse__sentiment-bar conf-pulse__sentiment-bar--neu" '
        f'style="width:{n_pct}%" title="neutral {n_pct}%"></div>'
        f'<div class="conf-pulse__sentiment-bar conf-pulse__sentiment-bar--neg" '
        f'style="width:{neg_pct}%" title="negative {neg_pct}%"></div>'
        f'</div>'
    )


def _load_conf_sentiment(conference_slug: str, db_conn: Any) -> dict[str, Any]:
    """Aggregate team_conversation_daily for all teams in this conference.

    Defensive against missing conferences.conference_slug column — added
    via migration 20260525_18 (2026-05-15). On DBs where the migration
    hasn't run, returns empty so the renderer falls back to its empty-
    state UI rather than crashing.
    """
    import sqlite3
    cur = db_conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                SUM(tcd.positive_doc_count),
                SUM(tcd.negative_doc_count),
                SUM(tcd.mention_count),
                AVG(tcd.mean_sentiment_score)
            FROM team_conversation_daily tcd
            JOIN teams t ON t.team_id = tcd.team_id
            JOIN conferences c ON c.conference_id = t.current_conference_id
            WHERE c.conference_slug = ?
              AND tcd.as_of_date >= date('now', '-30 days')
            """,
            (conference_slug,),
        )
    except sqlite3.OperationalError:
        return {}
    row = cur.fetchone()
    if not row or not row[2]:
        return {}
    pos = int(row[0] or 0)
    neg = int(row[1] or 0)
    total = int(row[2] or 0)
    neutral = max(0, total - pos - neg)
    mean = round(float(row[3] or 0), 3)
    return {"positive": pos, "neutral": neutral, "negative": neg, "total": total, "mean": mean}


def render_conference_pulse_section(conference_slug: str, db_conn: Any) -> str:
    """Return the Pulse v2 HTML fragment for a conference.

    Full content (themes + lede) for top-5 conferences.
    Stock-phrase fallback for the rest (still a clean render, no blank states).
    """
    display_name = _CONF_DISPLAY.get(conference_slug, conference_slug.replace("-", " ").upper())
    data = _load_conference_data(conference_slug, db_conn)
    sentiment = _load_conf_sentiment(conference_slug, db_conn)

    themes = data.get("themes", [])
    lede = data.get("lede")
    is_live = bool(themes or lede)

    # Stock-phrase fallback for conferences without LLM content
    if not lede:
        lede = _STOCK_LEDE.get(conference_slug, f"{display_name} — conversation is building.")

    # Lede block
    lede_html = f'<p class="conf-pulse__lede">{_html.escape(lede)}</p>'

    # Themes block
    theme_items = []
    for t in themes[:3]:
        label = _html.escape(t.get("label", ""))
        summary = _html.escape(t.get("summary", ""))
        quote = t.get("quote", "").strip()
        quote_html = (
            f'<blockquote class="conf-pulse__theme-quote">'
            f'"{_html.escape(quote)}"</blockquote>'
        ) if quote else ""
        theme_items.append(
            f'<div class="conf-pulse__theme">'
            f'<strong class="conf-pulse__theme-label">{label}</strong>'
            f'<span class="conf-pulse__theme-summary">{summary}</span>'
            f'{quote_html}</div>'
        )
    themes_html = ("\n".join(theme_items)) if theme_items else ""

    # Sentiment bar
    sent_html = ""
    if sentiment and sentiment.get("total", 0) >= 100:
        sent_html = _sentiment_bars(
            sentiment["positive"], sentiment["neutral"], sentiment["negative"]
        )
        mean = sentiment.get("mean", 0)
        mean_sign = "+" if mean >= 0 else ""
        sent_html += (
            f'<div class="conf-pulse__sentiment-meta">'
            f'{sentiment["total"]:,} mentions · {mean_sign}{mean:.2f} net sentiment</div>'
        )

    live_cls = "conf-pulse--live" if is_live else "conf-pulse--fallback"

    return f"""<section class="pulse conf-pulse {live_cls}" aria-labelledby="conf-pulse-{conference_slug}">
  <div class="conf-pulse__header">
    <h3 id="conf-pulse-{conference_slug}" class="conf-pulse__title">
      {_html.escape(display_name)} — Fan Pulse
    </h3>
  </div>
  {lede_html}
  {themes_html}
  {sent_html}
</section>"""


def render_all_conferences(db_conn: Any, output_dir: str) -> dict[str, Any]:
    """Render Pulse fragments for all known FBS conferences.

    Writes <output_dir>/<slug>_pulse.html for each conference.
    Returns summary: {rendered, total, errors}.
    """
    slugs = list(_CONF_DISPLAY.keys())
    os.makedirs(output_dir, exist_ok=True)

    rendered = 0
    errors = 0
    for slug in slugs:
        try:
            fragment = render_conference_pulse_section(slug, db_conn)
            out_path = os.path.join(output_dir, f"{slug}_pulse.html")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(fragment)
            rendered += 1
        except Exception as exc:
            log.error("render_all_conferences: error on %s: %s", slug, exc)
            errors += 1

    return {"rendered": rendered, "total": len(slugs), "errors": errors}
