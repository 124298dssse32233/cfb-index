"""Receipts surface renderer (Sprint 13 Phase 5).

Pages emitted under output/site/receipts/:
    /receipts/index.html                       — landing page
    /receipts/long-shots/<year>.html           — annual canonical list
    /receipts/source/<source-slug>.html        — per-source profile
    /receipts/aged-poorly/<year>.html          — companion list (gentle)

Templates live in receipts/templates/. The renderer is intentionally Jinja-
free — straight str.format / f-string composition — to avoid adding a
templating dep when reporting.py uses none.
"""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Any, Sequence

from .runtime import db_conn, receipts_output_root, slugify


# ---------------------------------------------------------------------------
# Tiny composer — no external deps, no Jinja.
# ---------------------------------------------------------------------------

_BASE_HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{title} · CFB Index Receipts</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
:root {{
  --bg: #0c0e10;
  --card: #14171b;
  --ink: #e8eaed;
  --ink-dim: #95a0ad;
  --accent: #f4c95d;
  --hit: #5dd39e;
  --miss: #d96c6c;
  --partial: #f4c95d;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; }}
a {{ color: var(--ink); text-decoration: none; border-bottom: 1px dotted var(--ink-dim); }}
a:hover {{ color: var(--accent); border-bottom-color: var(--accent); }}
.wrap {{ max-width: 880px; margin: 0 auto; padding: 48px 24px 96px; }}
.kicker {{ font: 600 11px/1 ui-sans-serif, system-ui; letter-spacing: 0.18em; text-transform: uppercase; color: var(--accent); }}
h1 {{ font: 700 38px/1.1 "Crimson Pro", Georgia, serif; margin: 12px 0 8px; letter-spacing: -0.01em; }}
h2 {{ font: 600 22px/1.25 "Crimson Pro", Georgia, serif; margin: 32px 0 8px; }}
h3 {{ font: 600 18px/1.2 ui-sans-serif, system-ui; margin: 24px 0 4px; }}
.lede {{ color: var(--ink-dim); margin-bottom: 32px; max-width: 60ch; }}
.card {{ background: var(--card); border-radius: 10px; padding: 20px 24px; margin-bottom: 16px; border-left: 3px solid var(--accent); }}
.card .meta {{ color: var(--ink-dim); font-size: 13px; margin-bottom: 8px; display: flex; gap: 12px; flex-wrap: wrap; }}
.card .quote {{ font: italic 17px/1.4 "Crimson Pro", Georgia, serif; margin: 8px 0; padding: 6px 0 6px 14px; border-left: 2px solid var(--ink-dim); color: var(--ink); }}
.card .body {{ color: var(--ink); margin: 8px 0 0; }}
.card .verdict {{ display: inline-block; font-weight: 700; font-size: 12px; padding: 2px 10px; border-radius: 4px; letter-spacing: 0.06em; }}
.verdict.hit {{ background: rgba(93,211,158,0.15); color: var(--hit); }}
.verdict.miss {{ background: rgba(217,108,108,0.15); color: var(--miss); }}
.verdict.partial {{ background: rgba(244,201,93,0.15); color: var(--partial); }}
.verdict.unresolvable {{ background: rgba(149,160,173,0.15); color: var(--ink-dim); }}
.surprise {{ font-variant-numeric: tabular-nums; font-weight: 600; color: var(--accent); }}
.rank {{ font: 700 28px/1 "Crimson Pro", Georgia, serif; color: var(--accent); margin-right: 12px; }}
ul.plain {{ list-style: none; padding: 0; margin: 0; }}
ul.plain li {{ padding: 12px 0; border-bottom: 1px solid #20242a; }}
table.scoreboard {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
table.scoreboard th, table.scoreboard td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #20242a; font-size: 14px; }}
table.scoreboard th {{ color: var(--ink-dim); font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; font-size: 11px; }}
.footer {{ margin-top: 64px; color: var(--ink-dim); font-size: 13px; }}
</style>
</head>
<body><div class="wrap">
"""

_BASE_FOOT = """
<div class="footer">CFB Index · Receipts · regenerated {now} UTC</div>
</div></body></html>
"""


def _escape(s: Any) -> str:
    if s is None:
        return ""
    return html.escape(str(s))


def _safe_slug_for_filename(slug: str) -> str:
    """Cap pathological slugs at 80 chars + short hash for Windows MAX_PATH safety."""
    if len(slug) <= 80:
        return slug
    import hashlib
    h = hashlib.sha1(slug.encode("utf-8")).hexdigest()[:8]
    return slug[:72] + "-" + h


def _verdict_pill(verdict: str | None) -> str:
    v = (verdict or "unresolvable").lower()
    label = {"hit": "AGED WELL", "miss": "AGED POORLY", "partial": "MIXED",
             "unresolvable": "PENDING"}.get(v, v.upper())
    return f'<span class="verdict {v}">{label}</span>'


# ---------------------------------------------------------------------------
# Page renderers
# ---------------------------------------------------------------------------

def render_landing() -> Path:
    out_root = receipts_output_root()
    out_root.mkdir(parents=True, exist_ok=True)

    with db_conn(read_only=True) as conn:
        recent = conn.execute("""
            SELECT pc.*, sp.display_name AS source_display
              FROM predictive_claims pc
              LEFT JOIN source_profiles sp ON sp.source_slug = pc.source_slug
             WHERE pc.outcome_resolved = 1
             ORDER BY pc.outcome_resolved_at DESC
             LIMIT 12
        """).fetchall()
        long_shots = conn.execute("""
            SELECT pc.*, sp.display_name AS source_display
              FROM predictive_claims pc
              LEFT JOIN source_profiles sp ON sp.source_slug = pc.source_slug
             WHERE pc.outcome_verdict = 'hit'
               AND pc.surprise_index IS NOT NULL
             ORDER BY pc.surprise_index DESC LIMIT 6
        """).fetchall()
        annual_years = [r[0] for r in conn.execute("""
            SELECT DISTINCT season_year FROM receipts_annual_lists
             WHERE list_kind = 'best_calls'
             ORDER BY season_year DESC
        """).fetchall()]

    parts: list[str] = [_BASE_HEAD.format(title="Receipts")]
    parts.append('<div class="kicker">CFB Index · Receipts</div>')
    parts.append("<h1>The takes that aged well — and the ones that didn't.</h1>")
    parts.append(
        '<p class="lede">We track predictive takes from beat writers, podcasts, '
        'message boards, and our own archive. When the outcome lands, we surface '
        'who saw it coming — quantified by the Surprise Index, with the original '
        'words intact.</p>'
    )

    if annual_years:
        parts.append("<h2>The 25 Best Calls</h2><ul class='plain'>")
        for y in annual_years:
            parts.append(
                f'<li><a href="long-shots/{y}.html">The 25 Best Calls of {y}</a></li>'
            )
        parts.append("</ul>")

    parts.append("<h2>Featured long-shots that hit</h2>")
    for r in long_shots:
        parts.append(_render_claim_card(r))

    parts.append("<h2>Recent resolutions</h2>")
    for r in recent:
        parts.append(_render_claim_card(r, compact=True))

    parts.append(_BASE_FOOT.format(now=datetime.utcnow().strftime("%Y-%m-%d %H:%M")))
    out = out_root / "index.html"
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


def _render_claim_card(claim, *, compact: bool = False) -> str:
    surp = claim["surprise_index"] if claim["surprise_index"] is not None else 0
    src_name = claim["source_display"] if "source_display" in claim.keys() and claim["source_display"] else claim["source_slug"].replace("-", " ").title()
    pub = (claim["source_published_at"] or "")[:10]
    parts = ['<div class="card">']
    parts.append('<div class="meta">')
    parts.append(_verdict_pill(claim["outcome_verdict"]))
    parts.append(f'<span class="surprise">Surprise Index {surp:.0f}</span>')
    parts.append(f'<span><a href="source/{_escape(_safe_slug_for_filename(claim["source_slug"]))}.html">{_escape(src_name)}</a></span>')
    parts.append(f'<span>{_escape(pub)}</span>')
    parts.append("</div>")
    parts.append(f'<div class="quote">"{_escape(claim["claim_text"])}"</div>')
    if claim["outcome_text"]:
        parts.append(f'<div class="body">{_escape(claim["outcome_text"])}</div>')
    parts.append("</div>")
    return "\n".join(parts)


def render_annual(season_year: int) -> Path:
    out_root = receipts_output_root() / "long-shots"
    out_root.mkdir(parents=True, exist_ok=True)

    with db_conn(read_only=True) as conn:
        entries = conn.execute("""
            SELECT ral.*, pc.claim_text, pc.source_slug, pc.source_url,
                   pc.source_published_at, pc.surprise_index, pc.outcome_text,
                   pc.outcome_verdict, sp.display_name AS source_display
              FROM receipts_annual_lists ral
              JOIN predictive_claims pc ON pc.id = ral.claim_id
              LEFT JOIN source_profiles sp ON sp.source_slug = pc.source_slug
             WHERE ral.season_year = ?
               AND ral.list_kind = 'best_calls'
             ORDER BY ral.rank ASC
        """, (season_year,)).fetchall()

    parts: list[str] = [_BASE_HEAD.format(title=f"The 25 Best Calls of {season_year}")]
    parts.append('<div class="kicker">CFB Index · Receipts</div>')
    parts.append(f"<h1>The 25 Best Calls of {season_year}</h1>")
    parts.append(
        '<p class="lede">Twenty-five takes that landed when consensus said they wouldn\'t. '
        'Ranked by Surprise Index — the composite of how unlikely each call was at the time '
        'it was made.</p>'
    )
    if not entries:
        parts.append("<p>No entries yet. Check back after the season's resolutions are processed.</p>")
    for e in entries:
        parts.append('<div class="card">')
        parts.append('<div class="meta">')
        parts.append(f'<span class="rank">#{e["rank"]}</span>')
        parts.append(_verdict_pill(e["outcome_verdict"]))
        surp = e["surprise_index"] or 0
        parts.append(f'<span class="surprise">Surprise Index {surp:.0f}</span>')
        src_name = e["source_display"] or e["source_slug"].replace("-", " ").title()
        parts.append(f'<span><a href="../source/{_escape(_safe_slug_for_filename(e["source_slug"]))}.html">{_escape(src_name)}</a></span>')
        parts.append(f'<span>{_escape((e["source_published_at"] or "")[:10])}</span>')
        parts.append("</div>")
        parts.append(f"<h3>{_escape(e['editorial_title'])}</h3>")
        parts.append(f'<div class="quote">"{_escape(e["claim_text"])}"</div>')
        parts.append(f"<div class='body'>{_escape(e['editorial_paragraph'])}</div>")
        if e["editorial_pull_quote"]:
            parts.append(f"<div class='body' style='color:var(--accent);font-style:italic;'>— "
                         f"\"{_escape(e['editorial_pull_quote'])}\"</div>")
        parts.append("</div>")

    parts.append(_BASE_FOOT.format(now=datetime.utcnow().strftime("%Y-%m-%d %H:%M")))
    out = out_root / f"{season_year}.html"
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


def render_source(source_slug: str) -> Path | None:
    out_root = receipts_output_root() / "source"
    out_root.mkdir(parents=True, exist_ok=True)
    safe_slug = _safe_slug_for_filename(source_slug)

    with db_conn(read_only=True) as conn:
        prof = conn.execute(
            "SELECT * FROM source_profiles WHERE source_slug = ?", (source_slug,)
        ).fetchone()
        if not prof:
            return None
        claims = conn.execute("""
            SELECT * FROM predictive_claims
             WHERE source_slug = ?
             ORDER BY source_published_at DESC
             LIMIT 50
        """, (source_slug,)).fetchall()

    parts: list[str] = [_BASE_HEAD.format(title=prof["display_name"])]
    parts.append('<div class="kicker">CFB Index · Receipts · Source Profile</div>')
    parts.append(f"<h1>{_escape(prof['display_name'])}</h1>")
    if prof["role_label"]:
        parts.append(f"<div class='lede'>{_escape(prof['role_label'])}</div>")
    if prof["voice_summary"]:
        parts.append(f"<p class='lede'>{_escape(prof['voice_summary'])}</p>")

    score = prof["receipt_score_pct"] or 0
    label = prof["receipt_score_label"] or ""
    parts.append("<table class='scoreboard'>")
    parts.append("<tr><th>Receipt Score</th><th>Tracked</th><th>Resolved</th><th>Hit</th><th>Miss</th><th>Partial</th></tr>")
    parts.append(
        f"<tr><td><strong>{score:.0f}%</strong> {_escape(label)}</td>"
        f"<td>{prof['takes_tracked']}</td><td>{prof['takes_resolved']}</td>"
        f"<td>{prof['takes_hit']}</td><td>{prof['takes_miss']}</td>"
        f"<td>{prof['takes_partial']}</td></tr>"
    )
    parts.append("</table>")

    parts.append("<h2>Take history</h2>")
    for c in claims:
        parts.append(_render_claim_card(c, compact=True))

    parts.append(_BASE_FOOT.format(now=datetime.utcnow().strftime("%Y-%m-%d %H:%M")))
    out = out_root / f"{safe_slug}.html"
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def render_all() -> dict[str, Any]:
    out_root = receipts_output_root()
    out_root.mkdir(parents=True, exist_ok=True)
    pages: list[str] = []

    pages.append(str(render_landing()))

    with db_conn(read_only=True) as conn:
        years = [r[0] for r in conn.execute("""
            SELECT DISTINCT season_year FROM receipts_annual_lists
             WHERE list_kind = 'best_calls'
        """).fetchall()]
        slugs = [r[0] for r in conn.execute(
            "SELECT source_slug FROM source_profiles WHERE profile_published = 1"
        ).fetchall()]

    for y in years:
        pages.append(str(render_annual(y)))
    for s in slugs:
        path = render_source(s)
        if path:
            pages.append(str(path))

    return {"pages_written": len(pages), "annual_lists": len(years),
            "source_profiles": len(slugs), "root": str(out_root)}
