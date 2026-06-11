"""Discourse leaderboard page builder — Language Layer Wave 4.

Builds the standalone /fan-voice/leaderboard.html page.
Pattern: "Pudding Hip-Hop Vocabulary" / NBA My Season framing.

Each fanbase gets ranked across four sentiment axes (optimism, anger, joy,
sarcasm). The page shows a full optimism table plus per-metric extremes (top-3
and bottom-1 for each metric).
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any

from .keyness import _row_get


# ---------------------------------------------------------------------------
# Ordinal helper
# ---------------------------------------------------------------------------

def _ordinal(n: int) -> str:
    """Return English ordinal string for integer n (e.g. 1 -> '1st').

    Handles the special cases: 11th, 12th, 13th, and the recurring x11/x12/x13
    patterns in hundreds (111th, 112th, 113th, etc.).
    """
    if not isinstance(n, int):
        n = int(n)
    # The teen exceptions apply to the last two digits.
    remainder_100 = n % 100
    if 11 <= remainder_100 <= 13:
        suffix = "th"
    else:
        remainder_10 = n % 10
        if remainder_10 == 1:
            suffix = "st"
        elif remainder_10 == 2:
            suffix = "nd"
        elif remainder_10 == 3:
            suffix = "rd"
        else:
            suffix = "th"
    return f"{n}{suffix}"


# ---------------------------------------------------------------------------
# CSS / HTML helpers
# ---------------------------------------------------------------------------

_PAGE_CSS = """
:root {
  --color-bg: #0a0c10;
  --color-surface: #12151c;
  --color-surface-2: #1a1e28;
  --color-border: #2a2f3e;
  --color-accent: #e8a838;
  --color-accent-dim: #c48a20;
  --color-text: #e2e6f0;
  --color-text-dim: #8892a4;
  --color-pos: #4caf7d;
  --color-neg: #e05050;
  --font-display: 'Bebas Neue', Impact, sans-serif;
  --font-body: 'Inter', system-ui, sans-serif;
  --font-serif: 'Source Serif Pro', Georgia, serif;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-body);
  font-size: 15px;
  line-height: 1.5;
  min-height: 100vh;
  padding: 0 0 4rem;
}
a { color: var(--color-accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Nav */
.top-nav {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  padding: 0.75rem 1.5rem;
  display: flex;
  align-items: center;
  gap: 1.5rem;
  font-size: 13px;
  color: var(--color-text-dim);
}
.top-nav a { color: var(--color-text-dim); }
.top-nav a:hover { color: var(--color-accent); text-decoration: none; }
.top-nav .sep { opacity: 0.4; }

/* Hero */
.hero {
  background: linear-gradient(160deg, #0e1220 0%, #0a0c10 60%);
  border-bottom: 2px solid var(--color-accent);
  padding: 3rem 1.5rem 2.5rem;
  text-align: center;
}
.hero-title {
  font-family: var(--font-display);
  font-size: clamp(2.5rem, 6vw, 4.5rem);
  letter-spacing: 0.04em;
  color: var(--color-accent);
  line-height: 1;
  margin-bottom: 0.4rem;
}
.hero-season {
  font-family: var(--font-display);
  font-size: clamp(1.2rem, 3vw, 1.8rem);
  letter-spacing: 0.08em;
  color: var(--color-text-dim);
  margin-bottom: 1.2rem;
}
.hero-stat {
  display: inline-block;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 0.6rem 1.6rem;
  font-size: 1.1rem;
  color: var(--color-text);
}
.hero-stat strong {
  color: var(--color-accent);
  font-size: 1.4rem;
  font-family: var(--font-display);
  letter-spacing: 0.05em;
}

/* Content container */
.content {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

/* Section headers */
.section-header {
  font-family: var(--font-display);
  font-size: 1.6rem;
  letter-spacing: 0.06em;
  color: var(--color-accent);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.4rem;
  margin: 2.5rem 0 1rem;
}

/* Full-ranking table */
.rank-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.rank-table th {
  background: var(--color-surface-2);
  color: var(--color-text-dim);
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.55rem 0.75rem;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}
.rank-table th.num { text-align: right; }
.rank-table td {
  padding: 0.55rem 0.75rem;
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}
.rank-table td.num { text-align: right; font-variant-numeric: tabular-nums; }
.rank-table tr:hover td { background: var(--color-surface-2); }
.rank-num {
  color: var(--color-text-dim);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  min-width: 2.2rem;
  display: inline-block;
}
.team-name { font-weight: 600; color: var(--color-text); }
.nba-framing { font-size: 12px; color: var(--color-text-dim); margin-top: 1px; }
.score-pos { color: var(--color-pos); font-variant-numeric: tabular-nums; }
.score-neg { color: var(--color-neg); font-variant-numeric: tabular-nums; }
.score-neu { color: var(--color-text-dim); font-variant-numeric: tabular-nums; }

/* Extremes grid */
.extremes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}
.extreme-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}
.extreme-card-header {
  background: var(--color-surface-2);
  border-bottom: 1px solid var(--color-border);
  padding: 0.5rem 0.75rem;
  font-family: var(--font-display);
  font-size: 1rem;
  letter-spacing: 0.06em;
  color: var(--color-accent);
}
.extreme-card-header .badge {
  font-size: 10px;
  font-family: var(--font-body);
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-text-dim);
  float: right;
  margin-top: 3px;
}
.extreme-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.45rem 0.75rem;
  border-bottom: 1px solid var(--color-border);
  font-size: 13px;
}
.extreme-row:last-child { border-bottom: none; }
.extreme-row.bottom-row { background: rgba(224,80,80,0.06); }
.extreme-team { color: var(--color-text); font-weight: 500; }
.extreme-rank { font-size: 11px; color: var(--color-text-dim); margin-top: 1px; }

/* Stub */
.stub-msg {
  text-align: center;
  padding: 5rem 2rem;
  color: var(--color-text-dim);
  font-size: 1.1rem;
}

/* Footer */
.page-footer {
  text-align: center;
  padding: 2rem 1rem 0;
  font-size: 12px;
  color: var(--color-text-dim);
  border-top: 1px solid var(--color-border);
  margin-top: 3rem;
}
"""

_METRIC_LABELS = {
    "optimism": "Optimism",
    "anger": "Anger",
    "joy": "Joy",
    "sarcasm": "Sarcasm",
}

_METRIC_SCORE_KEYS = {
    "optimism": "optimism_score",
    "anger": "anger_score",
    "joy": "joy_score",
    "sarcasm": "sarcasm_score",
}


def _fmt_score(val: float | None) -> str:
    """Format a score as '+X.XXX' or '-X.XXX', or '—' if missing."""
    if val is None:
        return "—"
    if val >= 0:
        return f"+{val:.3f}"
    return f"{val:.3f}"


def _score_class(val: float | None) -> str:
    if val is None:
        return "score-neu"
    if val > 0:
        return "score-pos"
    if val < 0:
        return "score-neg"
    return "score-neu"


def _esc(text: str) -> str:
    """Minimal HTML-escape for user-supplied text."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_leaderboard_page(db, output_dir, season: int) -> str:
    """Build /fan-voice/leaderboard.html and return its absolute path.

    Parameters
    ----------
    db:
        An open sqlite3 connection (row_factory should be sqlite3.Row or dict).
    output_dir:
        Root output directory (Path or str).  The file lands at
        ``<output_dir>/fan-voice/leaderboard.html``.
    season:
        The season year to display (e.g. 2025).

    Returns
    -------
    str
        Absolute path to the written HTML file.
    """
    output_dir = Path(output_dir)
    fan_voice_dir = output_dir / "fan-voice"
    os.makedirs(fan_voice_dir, exist_ok=True)
    out_path = fan_voice_dir / "leaderboard.html"

    # ------------------------------------------------------------------
    # 1. Query DB
    # ------------------------------------------------------------------
    try:
        cur = db.execute(
            """
            SELECT team_id,
                   COALESCE(display_name, slug) AS display_name,
                   slug,
                   optimism_score,
                   anger_score,
                   joy_score,
                   sarcasm_score,
                   anxiety_score,
                   cohort_size
            FROM   fanbase_voice_profile
            WHERE  season_year = ?
            ORDER  BY optimism_score DESC
            """,
            (season,),
        )
        rows = cur.fetchall()
    except Exception:
        rows = []

    # ------------------------------------------------------------------
    # 2. Stub page if no data
    # ------------------------------------------------------------------
    if not rows:
        html_out = _build_stub_page(season)
        out_path.write_text(html_out, encoding="utf-8")
        return str(out_path)

    n_fanbases = len(rows)

    # ------------------------------------------------------------------
    # 3. Build Section 1 — hero bar
    # ------------------------------------------------------------------
    hero_html = f"""
    <div class="hero">
      <div class="hero-title">Fan-Voice Leaderboard</div>
      <div class="hero-season">{season} Season</div>
      <div class="hero-stat">
        <strong>{n_fanbases}</strong> fanbases analyzed
      </div>
    </div>"""

    # ------------------------------------------------------------------
    # 4. Build Section 2 — full optimism table
    # ------------------------------------------------------------------
    table_rows_html = []
    for rank_0, row in enumerate(rows):
        rank = rank_0 + 1
        name = _esc(_row_get(row, "display_name") or _row_get(row, "slug") or "Unknown")
        opt_val = _row_get(row, "optimism_score")
        score_str = _fmt_score(opt_val)
        sc = _score_class(opt_val)
        ord_rank = _ordinal(rank)
        nba_framing = f"{ord_rank} of {n_fanbases} fanbases in optimism"
        table_rows_html.append(
            f"""<tr>
              <td class="num"><span class="rank-num">{rank}</span></td>
              <td>
                <div class="team-name">{name}</div>
                <div class="nba-framing">{nba_framing}</div>
              </td>
              <td class="num"><span class="{sc}">{score_str}</span></td>
            </tr>"""
        )

    section2_html = f"""
    <h2 class="section-header">Full Optimism Rankings</h2>
    <table class="rank-table">
      <thead>
        <tr>
          <th class="num" style="width:3rem">#</th>
          <th>Fanbase</th>
          <th class="num">Optimism Score</th>
        </tr>
      </thead>
      <tbody>
        {''.join(table_rows_html)}
      </tbody>
    </table>"""

    # ------------------------------------------------------------------
    # 5. Build Section 3 — per-metric extremes
    # ------------------------------------------------------------------
    # For each metric, sort rows by that metric score and show top-3 + bottom-1.
    extreme_cards_html = []
    for metric_key, score_col in _METRIC_SCORE_KEYS.items():
        label = _METRIC_LABELS[metric_key]

        # Sort by this metric, filtering out rows where score is None
        metric_rows = [r for r in rows if _row_get(r, score_col) is not None]
        if not metric_rows:
            continue
        sorted_desc = sorted(
            metric_rows,
            key=lambda r: (_row_get(r, score_col) or 0),
            reverse=True,
        )

        top3 = sorted_desc[:3]
        bottom1 = sorted_desc[-1:]

        rows_html = []
        for i, r in enumerate(top3):
            name = _esc(_row_get(r, "display_name") or _row_get(r, "slug") or "Unknown")
            val = _row_get(r, score_col)
            sc = _score_class(val)
            rows_html.append(
                f"""<div class="extreme-row">
                  <div>
                    <div class="extreme-team">{name}</div>
                    <div class="extreme-rank">{_ordinal(i+1)} highest</div>
                  </div>
                  <span class="{sc}">{_fmt_score(val)}</span>
                </div>"""
            )

        # Separator row
        rows_html.append(
            '<div class="extreme-row" style="justify-content:center;'
            'color:var(--color-text-dim);font-size:11px;padding:0.25rem 0.75rem;">'
            "&#8942; lowest &#8942;</div>"
        )

        for r in bottom1:
            name = _esc(_row_get(r, "display_name") or _row_get(r, "slug") or "Unknown")
            val = _row_get(r, score_col)
            sc = _score_class(val)
            rows_html.append(
                f"""<div class="extreme-row bottom-row">
                  <div>
                    <div class="extreme-team">{name}</div>
                    <div class="extreme-rank">lowest</div>
                  </div>
                  <span class="{sc}">{_fmt_score(val)}</span>
                </div>"""
            )

        extreme_cards_html.append(
            f"""<div class="extreme-card">
              <div class="extreme-card-header">
                {label}
                <span class="badge">Top 3 + Bottom</span>
              </div>
              {''.join(rows_html)}
            </div>"""
        )

    section3_html = f"""
    <h2 class="section-header">Metric Extremes</h2>
    <div class="extremes-grid">
      {''.join(extreme_cards_html)}
    </div>"""

    # ------------------------------------------------------------------
    # 6. Assemble full page
    # ------------------------------------------------------------------
    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fan-Voice Leaderboard — {season} Season | CFB Index</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600&family=Source+Serif+Pro:wght@400;600&display=swap" rel="stylesheet">
  <style>{_PAGE_CSS}</style>
</head>
<body>
  <nav class="top-nav">
    <a href="/index.html">CFB Index</a>
    <span class="sep">/</span>
    <a href="/fan-voice/index.html">Fan Voice</a>
    <span class="sep">/</span>
    <span>Leaderboard</span>
  </nav>
  {hero_html}
  <div class="content">
    {section2_html}
    {section3_html}
    <div class="page-footer">
      CFB Index &mdash; Fan-Voice Leaderboard &mdash; {season} Season &mdash;
      <a href="/fan-voice/index.html">Back to Fan Voice</a>
    </div>
  </div>
</body>
</html>"""

    out_path.write_text(page_html, encoding="utf-8")
    return str(out_path)


# ---------------------------------------------------------------------------
# Stub page (no data)
# ---------------------------------------------------------------------------

def _build_stub_page(season: int) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fan-Voice Leaderboard — {season} Season | CFB Index</title>
  <style>{_PAGE_CSS}</style>
</head>
<body>
  <nav class="top-nav">
    <a href="/index.html">CFB Index</a>
    <span class="sep">/</span>
    <a href="/fan-voice/index.html">Fan Voice</a>
    <span class="sep">/</span>
    <span>Leaderboard</span>
  </nav>
  <div class="hero">
    <div class="hero-title">Fan-Voice Leaderboard</div>
    <div class="hero-season">{season} Season</div>
  </div>
  <div class="content">
    <div class="stub-msg">
      No data for season {season}. Check back after fanbase voice profiles
      have been computed for this season.
    </div>
    <div class="page-footer">
      <a href="/fan-voice/index.html">Back to Fan Voice</a>
    </div>
  </div>
</body>
</html>"""
