"""Auto-generate /methodology/index.html — the landing page for the
``/methodology/`` directory.

Several pages on the site link to ``/methodology/`` (storyline threads,
glossary cross-refs). The two real pages — ``fan-intelligence.html`` and
``freshness.html`` — are both auto-generated, but until now there was no
index page and those links 404'd.

This page lists both child pages with short descriptions and the most
recent build timestamp pulled from the file mtimes (best-effort — falls
back to the page's own generation time if the files aren't present).

Output: ``output/site/methodology/index.html`` — self-contained, zero
external CSS, same style family as ``fan-intelligence.html`` /
``freshness.html``.

CLI hook: rendered by ``python manage.py build-methodology``.
"""
from __future__ import annotations

import datetime as _dt
import html
from pathlib import Path

from cfb_rankings.common.head_chrome import absolute_url


_OUTPUT_DIR = Path("output/site/methodology")
_OUTPUT_FILE = _OUTPUT_DIR / "index.html"


def _utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _last_modified(path: Path) -> str:
    try:
        ts = _dt.datetime.fromtimestamp(path.stat().st_mtime, tz=_dt.timezone.utc)
        return ts.strftime("%Y-%m-%d %H:%M UTC")
    except OSError:
        return "—"


def render_methodology_index_html(output_dir: Path | None = None) -> str:
    output_dir = output_dir or _OUTPUT_DIR
    fan_intel_path = output_dir / "fan-intelligence.html"
    freshness_path = output_dir / "freshness.html"
    fan_intel_mtime = _last_modified(fan_intel_path)
    freshness_mtime = _last_modified(freshness_path)
    generated_at = _utcnow_iso()
    page_canonical = absolute_url("/methodology/")
    og_image_url = absolute_url("/og-image.svg")
    page_description = (
        "How CFB Index models work: the Power + Resume ratings, the "
        "Heisman tracker, the fan-intelligence layer, and how each "
        "page's data gets refreshed. Methodology pages explain the "
        "model behind the rankings."
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Methodology | CFB Index</title>
  <meta name="description" content="{html.escape(page_description, quote=True)}">
  <link rel="canonical" href="{html.escape(page_canonical, quote=True)}">
  <meta property="og:site_name" content="THE CFB INDEX">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{html.escape(page_canonical, quote=True)}">
  <meta property="og:title" content="Methodology | CFB Index">
  <meta property="og:description" content="{html.escape(page_description, quote=True)}">
  <meta property="og:image" content="{html.escape(og_image_url, quote=True)}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:url" content="{html.escape(page_canonical, quote=True)}">
  <meta name="twitter:title" content="Methodology | CFB Index">
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
    .subtitle {{ color: #555; margin-top: 0.25rem; margin-bottom: 2rem; }}
    .page {{ border: 1px solid #e6e6e6; border-radius: 10px; padding: 1.25rem 1.5rem;
            margin: 1.25rem 0; background: #fafafa; }}
    .page h2 {{ margin: 0 0 0.5rem 0; font-size: 1.25rem; }}
    .page h2 a {{ color: #1a1a1a; text-decoration: none; }}
    .page h2 a:hover, .page h2 a:focus-visible {{ text-decoration: underline; }}
    .page p {{ margin: 0.5rem 0; }}
    /* Phase 9 a11y: WCAG AA 4.5:1 contrast — was #777 (4.21:1 fail on #fafafa) */
    .page .meta {{ color: #5a5a5a; font-size: 13px; }}
    /* Phase 9 a11y: WCAG AA 4.5:1 contrast — was #888 (3.55:1 fail on #fff) */
    footer {{ color: #595959; font-size: 12px; margin-top: 3rem; border-top: 1px solid #eee;
             padding-top: 1rem; }}
    footer a {{ color: #0969da; }}
    a:focus-visible {{ outline: 2px solid #0969da; outline-offset: 2px; }}
  </style>
</head>
<body>
  <a href="#main-content" class="skip-link">Skip to main content</a>
  <nav aria-label="Breadcrumb"><a href="../">&larr; CFB Index</a></nav>
  <main id="main-content">
    <h1>Methodology</h1>
    <p class="subtitle">How the CFB Index actually works — sources, tiers, sample-size
       rules, and which pipelines ran most recently.</p>

    <div class="page">
      <h2><a href="fan-intelligence.html">Fan Intelligence methodology</a></h2>
      <p>The full doctrine behind every number on a player or team page: the
         four-tier confidence model (A / B / C / D), the effective-sample-size
         floor, the cohort weight matrix, known coverage gaps, the glossary
         backing every <code>?</code> popover, and the source catalog grouped
         by tier.</p>
      <p class="meta">Sourced from the live signal registry &middot;
         last updated {html.escape(fan_intel_mtime)}</p>
    </div>

    <div class="page">
      <h2><a href="calibration.html">Calibration track record</a></h2>
      <p>Our public confusion matrix. Every prediction we publish is logged
         <em>before</em> the outcome is known, then graded weekly. See how often
         our calls were right &mdash; broken down by model, prediction kind, and
         confidence band &mdash; including where our high-confidence calls missed.</p>
      <p class="meta">Sourced from the live prediction ledger</p>
    </div>

    <div class="page">
      <h2><a href="freshness.html">Data source freshness</a></h2>
      <p>Last successful run per registered source, with status and rows
         inserted. Refreshed automatically each week. Useful for diagnosing why a
         cohort cell is showing &ldquo;Awaiting Signal&rdquo; — usually it&rsquo;s
         an ingest that hasn&rsquo;t run, not a real data gap.</p>
      <p class="meta">Last updated {html.escape(freshness_mtime)}</p>
    </div>
  </main>

  <footer>
    Methodology index &middot; updated {html.escape(generated_at)}
  </footer>
</body>
</html>
"""


def write_methodology_index_page(output_path: Path | None = None) -> Path:
    output_path = output_path or _OUTPUT_FILE
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html_text = render_methodology_index_html(output_path.parent)
    output_path.write_text(html_text, encoding="utf-8")
    return output_path


__all__ = ["render_methodology_index_html", "write_methodology_index_page"]
