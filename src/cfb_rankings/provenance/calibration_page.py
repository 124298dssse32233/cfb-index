"""Auto-generate /methodology/calibration.html — the public calibration
track record (WS-09, spec 09-calibration-ledger §7).

This is the rendered surface of the prediction ledger: "we publish our
confusion matrix." Every published prediction is logged to
``prediction_ledger`` *before* the outcome is known; the weekly resolver
grades each one once its outcome exists. This page renders the live
``calibration_summary`` aggregate so a fan can see how often our calls
were right, broken down by model, prediction kind, and confidence band.

Output: ``output/site/methodology/calibration.html`` — self-contained,
zero external CSS, same style family as ``methodology/index.html``.

CLI hook: rendered by ``python manage.py build-methodology``.
"""
from __future__ import annotations

import datetime as _dt
import html
from pathlib import Path
from typing import Any

from cfb_rankings.calibration import calibration_summary
from cfb_rankings.common.head_chrome import absolute_url
from cfb_rankings.db import Database

_OUTPUT_DIR = Path("output/site/methodology")
_OUTPUT_FILE = _OUTPUT_DIR / "calibration.html"

# Human-readable labels for the model/kind identifiers stored in the ledger.
_KIND_LABELS = {
    "archetype_assignment": "Fanbase archetype assignments",
    "season_wins": "Preseason season-win projections",
}
_MODEL_LABELS = {
    "fanbase-classifier": "Fanbase classifier",
    "season-path": "Season-path projector",
}
_BAND_ORDER = ["high", "medium", "low", "unset"]


def _utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{round(value * 100)}%"


def _kind_label(kind: str) -> str:
    return _KIND_LABELS.get(kind, kind.replace("_", " ").title())


def _model_label(model_id: str) -> str:
    return _MODEL_LABELS.get(model_id, model_id)


def _surface_rows(db: Database) -> list[dict[str, Any]]:
    """One row per (model_id, prediction_kind) with logged + pending counts."""
    return db.query_all(
        """
        select model_id,
               prediction_kind,
               count(*) as logged,
               sum(case when resolved_at_utc is not null then 1 else 0 end) as resolved
        from prediction_ledger
        group by model_id, prediction_kind
        order by model_id, prediction_kind
        """
    )


def _render_band_table(band_accuracy: dict[str, dict[str, Any]]) -> str:
    if not band_accuracy:
        return ""
    bands = [b for b in _BAND_ORDER if b in band_accuracy]
    bands += [b for b in band_accuracy if b not in _BAND_ORDER]
    rows = "".join(
        f"<tr><td class=\"band band-{html.escape(b)}\">{html.escape(b.title())}</td>"
        f"<td class=\"num\">{int(band_accuracy[b]['n'])}</td>"
        f"<td class=\"num\">{_pct(band_accuracy[b]['accuracy'])}</td></tr>"
        for b in bands
    )
    return (
        "<table class=\"bands\"><thead><tr>"
        "<th scope=\"col\">Confidence band</th>"
        "<th scope=\"col\">Resolved calls</th>"
        "<th scope=\"col\">Correct</th>"
        "</tr></thead><tbody>"
        f"{rows}</tbody></table>"
    )


def _render_surface(db: Database, model_id: str, kind: str, logged: int, resolved: int) -> str:
    summary = calibration_summary(db, model_id=model_id, prediction_kind=kind)
    pending = max(0, logged - resolved)
    title = f"{_kind_label(kind)}"
    sub = _model_label(model_id)
    mean_line = (
        f"<strong>{_pct(summary['mean_accuracy'])}</strong> of resolved calls were correct "
        f"({resolved} graded)"
        if resolved
        else "No calls graded yet — these predictions are on record, awaiting their outcome."
    )
    pending_line = (
        f"<p class=\"meta\">{pending} prediction{'s' if pending != 1 else ''} still pending "
        f"(logged before the outcome; the weekly resolver grades them once the result exists).</p>"
        if pending
        else ""
    )
    band_table = _render_band_table(summary.get("band_accuracy") or {})
    return f"""
    <div class="surface">
      <h2>{html.escape(title)}</h2>
      <p class="model">Model: {html.escape(sub)} &middot; {logged} logged &middot; {resolved} resolved</p>
      <p class="headline">{mean_line}</p>
      {band_table}
      {pending_line}
    </div>"""


def render_calibration_html(db: Database) -> str:
    overall = calibration_summary(db)
    surfaces = _surface_rows(db)
    generated_at = _utcnow_iso()
    page_canonical = absolute_url("/methodology/calibration.html")
    og_image_url = absolute_url("/og-image.svg")
    page_description = (
        "CFB Index publishes its own confusion matrix. Every prediction we "
        "publish is logged before the outcome is known, then graded weekly. "
        "This page shows how often our calls were right, by model and "
        "confidence band."
    )
    total_logged = overall["total_logged"]
    total_resolved = overall["resolved"]
    overall_headline = (
        f"Across every tracked model, <strong>{_pct(overall['mean_accuracy'])}</strong> of "
        f"our {total_resolved} graded predictions were correct."
        if total_resolved
        else f"{total_logged} predictions are on record; none have reached their outcome yet."
    )
    surface_html = "".join(
        _render_surface(
            db,
            str(r["model_id"]),
            str(r["prediction_kind"]),
            int(r["logged"]),
            int(r["resolved"] or 0),
        )
        for r in surfaces
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Calibration track record | CFB Index</title>
  <meta name="description" content="{html.escape(page_description, quote=True)}">
  <link rel="canonical" href="{html.escape(page_canonical, quote=True)}">
  <meta property="og:site_name" content="THE CFB INDEX">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{html.escape(page_canonical, quote=True)}">
  <meta property="og:title" content="Calibration track record | CFB Index">
  <meta property="og:description" content="{html.escape(page_description, quote=True)}">
  <meta property="og:image" content="{html.escape(og_image_url, quote=True)}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:url" content="{html.escape(page_canonical, quote=True)}">
  <meta name="twitter:title" content="Calibration track record | CFB Index">
  <meta name="twitter:description" content="{html.escape(page_description, quote=True)}">
  <meta name="twitter:image" content="{html.escape(og_image_url, quote=True)}">
  <style>
    body {{ font: 16px/1.5 -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
           color: #1a1a1a; max-width: 880px; margin: 2rem auto; padding: 0 1rem; }}
    .skip-link {{ position: absolute; left: -9999px; top: auto; width: 1px;
                  height: 1px; overflow: hidden; }}
    .skip-link:focus {{ position: static; width: auto; height: auto;
                        display: inline-block; padding: 0.5rem 1rem;
                        background: #1a1a1a; color: #fff; }}
    nav a {{ color: #0969da; text-decoration: none; }}
    nav a:hover, nav a:focus-visible {{ text-decoration: underline; }}
    h1 {{ font-size: 2rem; margin-bottom: 0.25rem; }}
    .subtitle {{ color: #555; margin-top: 0.25rem; margin-bottom: 1.5rem; }}
    .overall {{ border: 1px solid #d0d7de; border-radius: 10px; padding: 1.25rem 1.5rem;
               margin: 1.25rem 0 2rem; background: #f6f8fa; }}
    .overall .headline {{ font-size: 1.15rem; margin: 0; }}
    .surface {{ border: 1px solid #e6e6e6; border-radius: 10px; padding: 1.25rem 1.5rem;
               margin: 1.25rem 0; background: #fafafa; }}
    .surface h2 {{ margin: 0 0 0.25rem 0; font-size: 1.2rem; }}
    .surface .model {{ color: #5a5a5a; font-size: 13px; margin: 0 0 0.75rem; }}
    .surface .headline {{ margin: 0.25rem 0 0.75rem; }}
    table.bands {{ border-collapse: collapse; width: 100%; margin: 0.5rem 0; font-size: 14px; }}
    table.bands th, table.bands td {{ border: 1px solid #e6e6e6; padding: 0.4rem 0.6rem; text-align: left; }}
    table.bands th {{ background: #f0f0f0; }}
    table.bands td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .band {{ font-weight: 600; }}
    .band-high {{ color: #1a7f37; }}
    .band-medium {{ color: #9a6700; }}
    .band-low {{ color: #6e7781; }}
    .band-unset {{ color: #8c959f; }}
    .meta {{ color: #5a5a5a; font-size: 13px; }}
    footer {{ color: #595959; font-size: 12px; margin-top: 3rem; border-top: 1px solid #eee;
             padding-top: 1rem; }}
    footer a {{ color: #0969da; }}
    a:focus-visible {{ outline: 2px solid #0969da; outline-offset: 2px; }}
  </style>
</head>
<body>
  <a href="#main-content" class="skip-link">Skip to main content</a>
  <nav aria-label="Breadcrumb"><a href="./">&larr; Methodology</a></nav>
  <main id="main-content">
    <h1>Our calibration track record</h1>
    <p class="subtitle">We log every prediction we publish <em>before</em> the outcome is
       known, then grade ourselves weekly. This is the confusion matrix most outlets
       never show you.</p>

    <div class="overall">
      <p class="headline">{overall_headline}</p>
    </div>
    {surface_html}
  </main>

  <footer>
    Calibration ledger &middot; {total_logged} predictions logged &middot;
    {total_resolved} resolved &middot; updated {html.escape(generated_at)}
    &middot; <a href="./">Methodology</a>
  </footer>
</body>
</html>
"""


def write_calibration_page(db: Database, output_path: Path | None = None) -> Path:
    output_path = output_path or _OUTPUT_FILE
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_calibration_html(db), encoding="utf-8")
    return output_path


__all__ = ["render_calibration_html", "write_calibration_page"]
