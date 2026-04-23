"""Auto-generate the /methodology/fan-intelligence page — STRATEGY §8 / TASK 8.2.

The page is rendered from:
- ``source_registry`` rows (source_id, name, tier, cadence-via-ingest_method,
  license, cohort_weights, cohort_weights_rationale, max_publication_form)
- ``scrape_health`` (most recent row per source_id → "last_fetch" display)
- the cohort catalog from ``cohorts.aggregate.COHORTS``

Output: ``output/site/methodology/fan-intelligence.html`` — self-contained,
zero external CSS. Not hooked into site navigation yet; hook is a surgical
edit to reporting.py that requires Kevin's sign-off (CLAUDE.md rule).

CLI: ``python manage.py build-methodology``.
"""
from __future__ import annotations

import datetime as _dt
import html
import json
import logging
from pathlib import Path
from typing import Any

from cfb_rankings.cohorts.aggregate import COHORTS
from cfb_rankings.db import Database

logger = logging.getLogger(__name__)

_OUTPUT_DIR = Path("output/site/methodology")
_OUTPUT_FILE = _OUTPUT_DIR / "fan-intelligence.html"

_TIER_EXPLAINERS: dict[str, str] = {
    "A": "Numeric publication OK — raw values like pageviews, get-in price, volume are displayed directly.",
    "B": "Aggregated signal only — sample size and effective-N are always shown; individual posts appear as pseudonymous citations.",
    "C": "Rank or trend only — we publish where a source ranks relative to itself or others, never the raw number.",
    "D": "Editorial citation only — quoted text with a backlink, never included in numeric aggregates.",
}

_FLOOR_EXPLAINER = """
<p>Every (team, cohort, week) cell is assigned an <strong>effective sample size</strong>
(<code>effective_n</code>) — the weighted sum of cohort-weights from every document
contributing to that cell.</p>

<ul>
  <li><strong>effective_n &lt; 30</strong> — the cell shows a rank or "Awaiting Signal."
    We never display a sentiment number at this level, because the sample is too thin
    to support one honestly.</li>
  <li><strong>30 ≤ effective_n &lt; 100</strong> — sentiment is shown with an explicit
    sample-size badge so readers can weight the signal themselves.</li>
  <li><strong>effective_n ≥ 100</strong> — sentiment is shown with standard styling.</li>
</ul>

<p>In addition: if any contributing source carries Tier C confidence, the whole cell is
rendered as a rank rather than a number, regardless of effective_n. Tier D sources
never contribute to numeric aggregates — they appear only as pull-quote citations.</p>
"""


def _utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _fetch_sources(db: Database) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select sr.source_id, sr.source_name, sr.tier, sr.ingest_method,
               sr.license, sr.cohort_weights, sr.cohort_weights_rationale,
               sr.max_publication_form, sr.is_active,
               (select run_date from scrape_health sh
                  where sh.source_id = sr.source_id
                  order by run_date desc limit 1) as last_fetch,
               (select status from scrape_health sh
                  where sh.source_id = sr.source_id
                  order by run_date desc limit 1) as last_status
        from source_registry sr
        where sr.source_id is not null
        order by sr.tier, sr.source_id
        """
    )
    return rows


def _render_tier_section(tier: str, sources: list[dict[str, Any]]) -> str:
    rows = [s for s in sources if s["tier"] == tier]
    if not rows:
        return ""
    body = [f'<section id="tier-{tier.lower()}">']
    body.append(f"<h3>Tier {tier}</h3>")
    body.append(f"<p class='tier-explainer'>{html.escape(_TIER_EXPLAINERS[tier])}</p>")
    body.append("<table class='sources'><thead><tr>")
    body.append("<th>source_id</th><th>name</th><th>cadence / method</th>"
                "<th>license</th><th>publication form</th>"
                "<th>last successful fetch</th>"
                "</tr></thead><tbody>")
    for s in rows:
        active_mark = "" if s["is_active"] else " <span class='inactive'>(inactive)</span>"
        last = html.escape(s["last_fetch"] or "—")
        status = s["last_status"] or "—"
        status_cls = {"ok": "ok", "empty": "warn", "error": "err"}.get(status, "muted")
        body.append(
            f"<tr><td><code>{html.escape(s['source_id'])}</code>{active_mark}</td>"
            f"<td>{html.escape(s['source_name'] or '')}</td>"
            f"<td>{html.escape(s['ingest_method'] or '—')}</td>"
            f"<td>{html.escape(s['license'] or '—')}</td>"
            f"<td>{html.escape(s['max_publication_form'] or '—')}</td>"
            f"<td>{last} <span class='status {status_cls}'>({status})</span></td></tr>"
        )
        rationale = s["cohort_weights_rationale"]
        if rationale:
            body.append(
                f"<tr class='rationale'><td colspan='6'>"
                f"<em>Rationale:</em> {html.escape(rationale)}"
                "</td></tr>"
            )
    body.append("</tbody></table></section>")
    return "\n".join(body)


def _render_cohort_matrix(sources: list[dict[str, Any]]) -> str:
    lines = ["<table class='weights'><thead><tr><th>source_id</th>"]
    for c in COHORTS:
        lines.append(f"<th class='cohort-col'>{html.escape(c)}</th>")
    lines.append("</tr></thead><tbody>")
    for s in sources:
        if s["tier"] == "D":
            continue  # Tier D doesn't participate in cohort aggregation
        try:
            weights: dict[str, Any] = json.loads(s["cohort_weights"] or "{}")
        except json.JSONDecodeError:
            weights = {}
        lines.append(f"<tr><td><code>{html.escape(s['source_id'])}</code></td>")
        for c in COHORTS:
            w = weights.get(c)
            if w is None or w == 0:
                lines.append("<td class='weight zero'>—</td>")
            else:
                cls = "weight high" if w >= 0.5 else ("weight mid" if w >= 0.25 else "weight low")
                lines.append(f"<td class='{cls}'>{float(w):.2f}</td>")
        lines.append("</tr>")
    lines.append("</tbody></table>")
    return "\n".join(lines)


_CSS = """
body { font: 16px/1.5 -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
       color: #1a1a1a; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; }
h1 { font-size: 2rem; margin-bottom: 0; }
.subtitle { color: #555; margin-top: .25rem; }
h2 { margin-top: 2.5rem; border-bottom: 1px solid #ddd; padding-bottom: .25rem; }
h3 { margin-top: 2rem; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 14px; }
th, td { padding: 6px 10px; text-align: left; border-bottom: 1px solid #eee; vertical-align: top; }
th { background: #f7f7f7; font-weight: 600; }
code { background: #f4f4f8; padding: 1px 5px; border-radius: 3px; font-size: 13px; }
.tier-explainer { color: #333; font-style: italic; margin-bottom: .75rem; }
.sources tr.rationale td { color: #444; font-size: 13px; padding: 4px 16px 14px; background: #fbfbfe; border-bottom: 1px solid #eee; }
.inactive { color: #a00; font-weight: 600; font-size: 12px; }
.status { font-size: 12px; padding: 1px 5px; border-radius: 3px; background: #eee; }
.status.ok { background: #d4edda; color: #155724; }
.status.warn { background: #fff3cd; color: #856404; }
.status.err  { background: #f8d7da; color: #721c24; }
.status.muted { background: #eee; color: #555; }
.weights { font-size: 12px; }
.weights .cohort-col { writing-mode: vertical-rl; transform: rotate(180deg); min-height: 90px; }
.weight.zero { color: #bbb; text-align: center; }
.weight.low  { background: #f3f6fb; text-align: right; }
.weight.mid  { background: #dde7f5; text-align: right; font-weight: 600; }
.weight.high { background: #b7c9e6; text-align: right; font-weight: 700; }
.gap-callout { background: #fff7e6; border-left: 4px solid #f2a900; padding: 10px 14px; margin: 1rem 0; }
footer { color: #888; font-size: 12px; margin-top: 3rem; border-top: 1px solid #eee; padding-top: 1rem; }
"""


def render_methodology_html(db: Database) -> str:
    sources = _fetch_sources(db)
    tiers = ["A", "B", "C", "D"]
    active_count = sum(1 for s in sources if s["is_active"])

    parts = ["<!doctype html>", "<html lang='en'><head>",
             "<meta charset='utf-8'>",
             "<title>Fan Intelligence — Methodology | CFB Index</title>",
             f"<style>{_CSS}</style>",
             "</head><body>"]
    parts.append("<h1>Fan Intelligence — Methodology</h1>")
    parts.append(f"<p class='subtitle'>Auto-generated from <code>source_registry</code>. "
                 f"Last build: {_utcnow_iso()}. "
                 f"{active_count} active sources across {len(sources)} registered.</p>")

    parts.append("<h2>1. What we publish, and how we label it</h2>")
    parts.append("<p>Every number on the CFB Index's fan-intelligence pages is tagged with a "
                 "<strong>confidence tier</strong> — A, B, C, or D — determined by its "
                 "<em>worst-tier contributing source</em>. The tier controls how the number "
                 "can be shown.</p>")
    for t in tiers:
        parts.append(f"<p><strong>Tier {t}</strong> — {html.escape(_TIER_EXPLAINERS[t])}</p>")

    parts.append("<h2>2. Effective sample size &amp; the floor rule</h2>")
    parts.append(_FLOOR_EXPLAINER)

    parts.append("<h2>3. Source catalog</h2>")
    parts.append("<p>Every source currently registered, grouped by tier, with cadence, "
                 "license, publication form, and last successful fetch.</p>")
    for t in tiers:
        parts.append(_render_tier_section(t, sources))

    parts.append("<h2>4. Cohort weight matrix</h2>")
    parts.append("<p>Each source contributes to cohort aggregates with weights drawn from the matrix "
                 "below. Weights do not sum to 1 within an axis — a Reddit r/CFB post is "
                 "simultaneously millennial and national-narrative and mildly analytics-tilted, "
                 "and the weights reflect that. Tier D sources are excluded from numeric "
                 "aggregation.</p>")
    parts.append(_render_cohort_matrix(sources))

    parts.append("<h2>5. Known coverage gaps</h2>")
    parts.append(
        "<div class='gap-callout'>"
        "<ul>"
        "<li><strong>Gen Z casual</strong> — programmatic reach is weak; manual TikTok observation "
        "fills. We don't claim parity.</li>"
        "<li><strong>Alumni diaspora</strong> — Facebook alumni groups are largely inaccessible. "
        "We proxy with alumni subreddits and Substacks, which is a narrower signal.</li>"
        "<li><strong>HBCU community</strong> — coverage is narrow (TikTok, HBCU Gameday, "
        "504SportsNation). HBCU program pages carry an honest partial-coverage tag.</li>"
        "<li><strong>Women CFB fans</strong> — a real and growing audience on IG/TikTok. "
        "We don't have a defensible identity signal and do not break it out as a cohort.</li>"
        "<li><strong>International / diaspora fans</strong> — small and unaddressed by our sources.</li>"
        "</ul>"
        "<p>Making these gaps visible is a credibility asset, not a bug to paper over.</p>"
        "</div>"
    )

    parts.append("<h2>6. Weight governance</h2>")
    parts.append("<p>Weights are editorial judgment grounded in public demographic data "
                 "(Pew, GWI, Edison, Kalshi platform disclosures). They are reviewed once per "
                 "year in April, and prior weight versions are snapshotted so historical "
                 "aggregates do not silently shift.</p>")
    parts.append("<p>Corrections: open an issue on the repo or email <a href='mailto:corrections@cfb-index.com'>corrections@cfb-index.com</a>.</p>")

    parts.append("<footer>"
                 "Fan Intelligence methodology page — generated at "
                 f"{_utcnow_iso()} — source of truth: <code>FAN_INTEL_SOURCE_STRATEGY.md</code> + <code>source_registry</code>."
                 "</footer>")
    parts.append("</body></html>")
    return "\n".join(parts)


def write_methodology_page(db: Database, output_path: Path | None = None) -> Path:
    output_path = output_path or _OUTPUT_FILE
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html_text = render_methodology_html(db)
    output_path.write_text(html_text, encoding="utf-8")
    return output_path


__all__ = ["render_methodology_html", "write_methodology_page"]
