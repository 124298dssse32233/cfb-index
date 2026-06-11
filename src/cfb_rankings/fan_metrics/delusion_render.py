"""Delusion Premium hub + share cards (Group Chat Noir).

/hub/delusion/ — the "most delusional fanbase" board: fan belief (violet,
perception) vs betting-market title odds (blue, market — spec quarantine),
ranked by the signed delusion index. Per-team 1200x675 head-to-head cards.
Clones the backometer_render module shape (standalone, never crashes the build).

Data: delusion_premium_weekly (written by `manage.py compute-delusion-premium`).
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.fan_metrics.backometer_render import (
    CHALK,
    GROUND,
    HAIRLINE,
    RECEIPT,
    SURFACE,
    _DISPLAY_STACK,
    _MONO_STACK,
    _SANS_STACK,
    og_card_meta,
)

BELIEF = "#9D6BFF"
BELIEF_TEXT = "#B794FF"
MARKET = "#3D91FF"

VERDICT = {
    "delusional": ("DELUSIONAL", BELIEF_TEXT, "fans believe; the market doesn’t"),
    "sharp": ("SHARP", MARKET, "the market’s higher on you than your own fans"),
    "bullish": ("BULLISH", CHALK, "fans run ahead of the market"),
}


def latest_delusion(db: Database) -> tuple[int, int] | None:
    row = db.query_one(
        """
        select season_year, max(week) as week from delusion_premium_weekly
        where season_year = (select max(season_year) from delusion_premium_weekly)
        group by season_year
        """
    )
    if not row or row.get("week") is None:
        return None
    return int(row["season_year"]), int(row["week"])


def fetch_delusion_board(db: Database, season: int, week: int) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select d.*, t.canonical_name as team_name, t.slug as team_slug
        from delusion_premium_weekly d
        join teams t on t.team_id = d.team_id
        where d.season_year = :season and d.week = :week
        order by d.rank
        """,
        {"season": season, "week": week},
    )


# ---------------------------------------------------------------------------
# Share card (1200x675) — FANS vs MARKET head-to-head
# ---------------------------------------------------------------------------

def render_delusion_card_svg(row: dict[str, Any], *, season: int) -> str:
    name = str(row["team_name"])
    verdict_key = str(row.get("verdict") or "bullish")
    word, color, gloss = VERDICT.get(verdict_key, VERDICT["bullish"])
    belief = float(row["belief_score"])
    market = float(row["market_pct"])
    index = float(row["delusion_index"])
    rank = int(row.get("rank") or 0)
    cohort = int(row.get("cohort_size") or 0)
    low = int(row.get("belief_low_signal") or 0)

    # Two stat blocks share a center divider; belief bar (violet) and market
    # bar (blue) are scaled to a common 0-100 so the gap is visible.
    track = 420.0
    belief_w = max(2.0, belief / 100.0 * track)
    market_w = max(2.0, market / 100.0 * track)
    low_note = " (low-signal)" if low else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675" role="img" aria-label="Delusion Premium: {escape(name)} fans {belief:.0f} vs market {market:.0f}%">
  <rect x="0" y="0" width="1200" height="675" rx="24" fill="{GROUND}"/>
  <rect x="1.5" y="1.5" width="1197" height="672" rx="23" fill="none" stroke="{HAIRLINE}" stroke-width="2"/>
  <text x="80" y="78" fill="{RECEIPT}" font-size="22" letter-spacing="4"
        font-family="{_MONO_STACK}">DELUSION PREMIUM™ · {season} · #{rank} OF {cohort}</text>
  <text x="80" y="150" fill="{CHALK}" font-size="52" font-weight="800"
        font-family="{_SANS_STACK}">{escape(name)}</text>
  <text x="80" y="250" fill="{color}" font-size="84"
        font-family="{_DISPLAY_STACK}" letter-spacing="1">{escape(word)}</text>
  <text x="1120" y="170" fill="{color}" text-anchor="end" font-size="96"
        font-family="{_DISPLAY_STACK}" font-variant-numeric="tabular-nums">{index:+.0f}</text>
  <text x="1120" y="214" fill="{RECEIPT}" text-anchor="end" font-size="20"
        font-family="{_MONO_STACK}">DELUSION INDEX</text>

  <text x="80" y="346" fill="{BELIEF_TEXT}" font-size="22" font-family="{_MONO_STACK}">✦ FANS — BACKOMETER BELIEF</text>
  <rect x="80" y="362" width="{track:.0f}" height="58" rx="8" fill="{SURFACE}"/>
  <rect x="80" y="362" width="{belief_w:.1f}" height="58" rx="8" fill="{BELIEF}"/>
  <text x="{80 + track + 24:.0f}" y="404" fill="{CHALK}" font-size="44" font-weight="800"
        font-family="{_SANS_STACK}" font-variant-numeric="tabular-nums">{belief:.0f}</text>

  <text x="80" y="486" fill="{MARKET}" font-size="22" font-family="{_MONO_STACK}">▪ MARKET — IMPLIED 2027 TITLE ODDS</text>
  <rect x="80" y="502" width="{track:.0f}" height="58" rx="8" fill="{SURFACE}"/>
  <rect x="80" y="502" width="{market_w:.1f}" height="58" rx="8" fill="{MARKET}"/>
  <text x="{80 + track + 24:.0f}" y="544" fill="{CHALK}" font-size="44" font-weight="800"
        font-family="{_SANS_STACK}" font-variant-numeric="tabular-nums">{market:.0f}%</text>

  <line x1="80" y1="608" x2="1120" y2="608" stroke="{HAIRLINE}" stroke-width="2"/>
  <text x="80" y="644" fill="{RECEIPT}" font-size="18"
        font-family="{_MONO_STACK}">belief=Backometer{escape(low_note)} · market=Polymarket title odds</text>
  <text x="1120" y="644" fill="{RECEIPT}" text-anchor="end" font-size="18"
        font-family="{_MONO_STACK}">cfbindex.com</text>
</svg>"""


# ---------------------------------------------------------------------------
# Hub
# ---------------------------------------------------------------------------

_HUB_CSS = f"""
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: {GROUND}; color: {CHALK}; font-family: {_SANS_STACK};
    font-feature-settings: "tnum"; line-height: 1.5; padding: 40px 16px 80px;
  }}
  .wrap {{ max-width: 880px; margin: 0 auto; }}
  .eyebrow {{
    font-family: {_MONO_STACK}; font-size: 12px; font-weight: 500; color: {RECEIPT};
    letter-spacing: .12em; text-transform: uppercase; margin-bottom: 10px;
  }}
  h1 {{
    font-family: {_DISPLAY_STACK}; font-weight: 400; text-transform: uppercase;
    font-size: clamp(40px, 7vw, 62px); line-height: 1.05; margin-bottom: 8px;
  }}
  .lede {{ color: {RECEIPT}; font-size: 15px; max-width: 64ch; margin-bottom: 36px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th {{
    font-family: {_MONO_STACK}; font-size: 10.5px; font-weight: 500; letter-spacing: .1em;
    text-transform: uppercase; color: {RECEIPT}; text-align: left;
    padding: 8px; border-bottom: 1px solid {HAIRLINE};
  }}
  th.num, td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td {{ padding: 11px 8px; border-bottom: 1px solid {HAIRLINE}; }}
  td a {{ color: {CHALK}; text-decoration: none; font-weight: 600; }}
  td a:hover {{ color: {BELIEF_TEXT}; }}
  .belief {{ color: {BELIEF_TEXT}; font-weight: 700; }}
  .market {{ color: {MARKET}; font-weight: 700; }}
  .v-delusional {{ color: {BELIEF_TEXT}; }}
  .v-sharp {{ color: {MARKET}; }}
  .v-bullish {{ color: {RECEIPT}; }}
  .verdict {{ font-family: {_MONO_STACK}; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; }}
  .foot {{
    margin-top: 40px; padding-top: 16px; border-top: 1px solid {HAIRLINE};
    font-family: {_MONO_STACK}; font-size: 12px; color: {RECEIPT};
  }}
  .foot a {{ color: {RECEIPT}; }}
"""


def render_delusion_index_html(season: int, board: list[dict[str, Any]]) -> str:
    body = ""
    for r in board:
        vk = str(r.get("verdict") or "bullish")
        word = VERDICT.get(vk, VERDICT["bullish"])[0]
        body += (
            f"<tr><td class='num'>{int(r['rank'])}</td>"
            f"<td><a href=\"/teams/{escape(str(r['team_slug']))}.html\">{escape(str(r['team_name']))}</a></td>"
            f"<td class='num belief'>{float(r['belief_score']):.0f}</td>"
            f"<td class='num market'>{float(r['market_pct']):.0f}%</td>"
            f"<td class='num'>{float(r['delusion_index']):+.0f}</td>"
            f"<td class='verdict v-{vk}'>{escape(word)}</td></tr>"
        )
    _dp_desc = "Which fanbases believe more than the betting market does. Fan belief vs implied title odds."
    _dp_img = f"/hub/delusion/{season}/{board[0]['team_slug']}.png" if board else None
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Delusion Premium — {season} · CFB Index</title>
<meta name="description" content="{escape(_dp_desc)}">
{og_card_meta(f'Delusion Premium — {season}', _dp_desc, _dp_img)}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>{_HUB_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">CFB Index · Fan Intelligence · {season}</div>
  <h1>Delusion Premium™</h1>
  <p class="lede">Which fanbases believe in a title more than the betting market does. We rank
  <span class="belief">fan belief</span> (the Backometer) against the <span class="market">market's
  implied 2027 title odds</span> — both as percentiles within the contender field — and the gap is
  the delusion index. Top = most delusional; bottom = the market's higher on you than your own fans
  ("sharp"). The honest calibration payoff — who was actually right — settles in December.</p>
  <table>
    <tr><th class="num">#</th><th>Fanbase</th><th class="num">Belief</th>
        <th class="num">Market</th><th class="num">Index</th><th>Verdict</th></tr>
    {body}
  </table>
  <div class="foot">
    Belief = Backometer (fan optimism, 0-100; some offseason scores are low-signal) ·
    market = Polymarket implied 2027 CFP title odds ·
    <a href="/methodology/fan-intelligence.html">full methodology →</a>
  </div>
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Build entry point
# ---------------------------------------------------------------------------

def build_delusion_section(db: Database, output_dir: str | Path = "output/site") -> list[Path]:
    try:
        latest = latest_delusion(db)
        if latest is None:
            print("[delusion] no delusion_premium_weekly rows; section skipped")
            return []
        season, week = latest
        board = fetch_delusion_board(db, season, week)
    except Exception as exc:  # noqa: BLE001
        print(f"[delusion] fetch failed ({type(exc).__name__}): {exc}")
        return []
    if not board:
        return []

    out_dir = Path(output_dir) / "hub" / "delusion" / str(season)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for row in board:
        svg = render_delusion_card_svg(row, season=season)
        svg_path = out_dir / f"{row['team_slug']}.svg"
        svg_path.write_text(svg, encoding="utf-8")
        written.append(svg_path)
    index_path = out_dir / "index.html"
    index_path.write_text(render_delusion_index_html(season, board), encoding="utf-8")
    written.append(index_path)

    root = Path(output_dir) / "hub" / "delusion"
    root.mkdir(parents=True, exist_ok=True)
    redirect = (
        '<!doctype html><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0; url=/hub/delusion/{season}/">'
        "<title>Delusion Premium</title>"
        f'<p>Redirecting to <a href="/hub/delusion/{season}/">the latest board</a>.</p>'
    )
    (root / "index.html").write_text(redirect, encoding="utf-8")
    written.append(root / "index.html")
    return written


__all__ = ["build_delusion_section", "render_delusion_card_svg", "render_delusion_index_html"]
