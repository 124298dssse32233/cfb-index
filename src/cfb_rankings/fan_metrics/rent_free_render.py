"""Rent Free hub + share cards (Group Chat Noir, perception/violet).

Renders ``/hub/rent-free/<season>/`` as a leaderboard of the most lopsided
fanbase obsessions, each with a two-bar head-to-head comparison and a
1200x675 standalone SVG share card. Rent Free is fan-PERCEPTION data, so it
uses Aura Violet (spec quarantine rule), never the green/ember production
accents. Clones the backometer_render module shape (standalone, never crashes
the build, per-season dir, root redirect).
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
from cfb_rankings.fan_metrics.rent_free import fetch_rent_free_pairs, latest_rent_free_season

AURA = "#9D6BFF"        # perception fill
AURA_DIM = "#7E5BD6"    # the quieter side
AURA_TEXT = "#B794FF"   # violet at text sizes (graphic tier too dark for type)


# ---------------------------------------------------------------------------
# Two-bar head-to-head fragment (shared by card + hub + team module)
# ---------------------------------------------------------------------------

def _obsession_bars_svg(
    pair: dict[str, Any],
    *,
    x0: float, x1: float, y0: float, bar_h: float, gap: float,
) -> str:
    """Two stacked horizontal bars: A->B and B->A, scaled to the dominant side.

    The longer bar is the obsessed fanbase. Counts sit at each bar's end;
    the quiet side still draws a hairline stub when its count is 0 so the
    asymmetry is unmistakable.
    """
    a_to_b = int(pair["a_to_b"])
    b_to_a = int(pair["b_to_a"])
    scale_max = max(1, a_to_b, b_to_a)
    track = x1 - x0

    label_fs = max(13.0, bar_h * 0.46)
    count_fs = max(18.0, bar_h * 0.46)

    def bar(y: float, label: str, count: int, fill: str) -> str:
        w = (count / scale_max) * track
        w_draw = max(w, 2.0)  # hairline stub for zero
        baseline = y + bar_h * 0.72
        # When the bar nearly fills the track there's no room for the count to
        # the right of it — set it INSIDE the bar, right-aligned, in near-black
        # (chalk-on-violet fails AA; near-black on the accent fill passes).
        if w_draw > track - 64:
            count_svg = (
                f'<text x="{x0 + w_draw - 14:.1f}" y="{baseline:.0f}" fill="#101418" '
                f'text-anchor="end" font-size="{count_fs:.0f}" font-weight="800" '
                f'font-family="{_SANS_STACK}" font-variant-numeric="tabular-nums">{count}</text>'
            )
        else:
            count_svg = (
                f'<text x="{x0 + w_draw + 14:.1f}" y="{baseline:.0f}" fill="{CHALK}" '
                f'font-size="{count_fs:.0f}" font-weight="700" font-family="{_SANS_STACK}" '
                f'font-variant-numeric="tabular-nums">{count}</text>'
            )
        return (
            f'<text x="{x0:.0f}" y="{y - 8:.0f}" fill="{RECEIPT}" font-size="{label_fs:.0f}" '
            f'font-family="{_MONO_STACK}">{escape(label)}</text>'
            f'<rect x="{x0:.0f}" y="{y:.0f}" width="{track:.0f}" height="{bar_h:.0f}" rx="6" '
            f'fill="{SURFACE}"/>'
            f'<rect x="{x0:.0f}" y="{y:.0f}" width="{w_draw:.1f}" height="{bar_h:.0f}" rx="6" '
            f'fill="{fill}"/>'
            f'{count_svg}'
        )

    obsessed_is_a = a_to_b >= b_to_a
    y1, y2 = y0, y0 + bar_h + gap + 26
    a_label = f"{_short(pair['a_name'])} fans → {_short(pair['b_name'])}"
    b_label = f"{_short(pair['b_name'])} fans → {_short(pair['a_name'])}"
    return (
        bar(y1 + 26, a_label, a_to_b, AURA if obsessed_is_a else AURA_DIM)
        + bar(y2, b_label, b_to_a, AURA if not obsessed_is_a else AURA_DIM)
    )


def _short(name: str, limit: int = 18) -> str:
    return name if len(name) <= limit else name[: limit - 1] + "…"


# ---------------------------------------------------------------------------
# Share card (1200x675)
# ---------------------------------------------------------------------------

def render_rent_free_card_svg(pair: dict[str, Any], *, season: int) -> str:
    rent_free = pair["rent_free"]["name"]
    obsessed = pair["obsessed"]["name"]
    verdict = f"{_short(rent_free, 22)} lives rent free"
    sub = f"in {_short(obsessed, 24)}'s head"
    ratio_label = pair["ratio_label"]
    bars = _obsession_bars_svg(pair, x0=80, x1=1120, y0=300, bar_h=56, gap=34)
    receipt = f"n={pair['total']:,} cross-mentions · {season} · rival-bucket tagged"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675" role="img" aria-label="Rent Free: {escape(rent_free)} lives rent free in {escape(obsessed)}'s head">
  <rect x="0" y="0" width="1200" height="675" rx="24" fill="{GROUND}"/>
  <rect x="1.5" y="1.5" width="1197" height="672" rx="23" fill="none" stroke="{HAIRLINE}" stroke-width="2"/>
  <text x="80" y="78" fill="{RECEIPT}" font-size="22" letter-spacing="4"
        font-family="{_MONO_STACK}">RENT FREE™ · {escape(pair['rivalry_name'])} · {season}</text>
  <text x="80" y="178" fill="{AURA_TEXT}" font-size="74"
        font-family="{_DISPLAY_STACK}" letter-spacing="1">{escape(verdict)}</text>
  <text x="80" y="244" fill="{CHALK}" font-size="40" font-weight="700"
        font-family="{_SANS_STACK}">{escape(sub)}</text>
  <text x="1120" y="150" fill="{AURA_TEXT}" text-anchor="end" font-size="92"
        font-family="{_DISPLAY_STACK}" font-variant-numeric="tabular-nums">{escape(ratio_label)}</text>
  {bars}
  <line x1="80" y1="608" x2="1120" y2="608" stroke="{HAIRLINE}" stroke-width="2"/>
  <text x="80" y="644" fill="{RECEIPT}" font-size="20"
        font-family="{_MONO_STACK}">{escape(receipt)}</text>
  <text x="1120" y="644" fill="{RECEIPT}" text-anchor="end" font-size="20"
        font-family="{_MONO_STACK}">cfbindex.com</text>
</svg>"""


# ---------------------------------------------------------------------------
# Hub page
# ---------------------------------------------------------------------------

_HUB_CSS = f"""
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: {GROUND}; color: {CHALK};
    font-family: {_SANS_STACK}; font-feature-settings: "tnum";
    line-height: 1.5; padding: 40px 16px 80px;
  }}
  .wrap {{ max-width: 880px; margin: 0 auto; }}
  .eyebrow {{
    font-family: {_MONO_STACK}; font-size: 12px; font-weight: 500;
    color: {RECEIPT}; letter-spacing: .12em; text-transform: uppercase; margin-bottom: 10px;
  }}
  h1 {{
    font-family: {_DISPLAY_STACK}; font-weight: 400; text-transform: uppercase;
    font-size: clamp(40px, 7vw, 62px); line-height: 1.05; margin-bottom: 8px;
  }}
  .lede {{ color: {RECEIPT}; font-size: 15px; max-width: 62ch; margin-bottom: 40px; }}
  .card {{
    background: {SURFACE}; border: 1px solid {HAIRLINE}; border-radius: 12px;
    margin-bottom: 22px; overflow: hidden;
  }}
  .card-top {{
    display: flex; align-items: baseline; justify-content: space-between;
    gap: 12px; padding: 16px 20px 4px;
  }}
  .card-rivalry {{
    font-family: {_MONO_STACK}; font-size: 11px; letter-spacing: .12em;
    text-transform: uppercase; color: {RECEIPT};
  }}
  .card-ratio {{
    font-family: {_DISPLAY_STACK}; font-size: 30px; color: {AURA_TEXT};
    font-variant-numeric: tabular-nums;
  }}
  .card-verdict {{
    padding: 0 20px; font-family: {_DISPLAY_STACK}; text-transform: uppercase;
    font-size: clamp(22px, 4vw, 32px); color: {AURA_TEXT}; line-height: 1.08;
  }}
  .card-verdict small {{
    display: block; font-family: {_SANS_STACK}; text-transform: none;
    font-size: 14px; color: {CHALK}; font-weight: 600; margin-top: 2px;
  }}
  .card svg {{ display: block; width: 100%; height: auto; padding: 6px 8px 0; }}
  .card-foot {{
    display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap;
    padding: 10px 20px; border-top: 1px solid {HAIRLINE};
    font-family: {_MONO_STACK}; font-size: 12px; color: {RECEIPT};
  }}
  .card-foot a {{ color: {RECEIPT}; }}
  .foot {{
    margin-top: 44px; padding-top: 16px; border-top: 1px solid {HAIRLINE};
    font-family: {_MONO_STACK}; font-size: 12px; color: {RECEIPT};
  }}
  .foot a {{ color: {RECEIPT}; }}
"""


def _card_bars_inline_svg(pair: dict[str, Any]) -> str:
    bars = _obsession_bars_svg(pair, x0=20, x1=860, y0=10, bar_h=34, gap=22)
    return (
        f'<svg viewBox="0 0 880 150" role="img" '
        f'aria-label="{escape(pair["a_name"])} vs {escape(pair["b_name"])} cross-mentions">'
        f"{bars}</svg>"
    )


def render_rent_free_index_html(season: int, pairs: list[dict[str, Any]]) -> str:
    cards = ""
    for pair in pairs:
        pslug = f"{pair['a_slug']}-vs-{pair['b_slug']}"
        cards += (
            f'<div class="card">'
            f'<div class="card-top">'
            f'<span class="card-rivalry">{escape(pair["rivalry_name"])}</span>'
            f'<span class="card-ratio">{escape(pair["ratio_label"])}</span>'
            f"</div>"
            f'<div class="card-verdict">{escape(_short(pair["rent_free"]["name"], 24))} lives rent free'
            f'<small>in {escape(pair["obsessed"]["name"])}’s head</small></div>'
            f'{_card_bars_inline_svg(pair)}'
            f'<div class="card-foot">'
            f'<span><a href="/teams/{escape(pair["rent_free"]["slug"])}.html">'
            f'{escape(pair["rent_free"]["name"])} →</a> · '
            f'<a href="/teams/{escape(pair["obsessed"]["slug"])}.html">'
            f'{escape(pair["obsessed"]["name"])} →</a></span>'
            f'<span><a href="{escape(pslug)}.png" download>download card</a></span>'
            f"</div></div>\n"
        )

    title = f"Rent Free — {season}"
    og_desc = "Which rival fanbase talks about you most. Pairwise obsession asymmetry from real fan conversations."
    og_img = (
        f"/hub/rent-free/{season}/{pairs[0]['a_slug']}-vs-{pairs[0]['b_slug']}.png"
        if pairs else None
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · CFB Index</title>
<meta name="description" content="{escape(og_desc)}">
{og_card_meta(title, og_desc, og_img)}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>{_HUB_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">CFB Index · Fan Intelligence · {season}</div>
  <h1>Rent Free™</h1>
  <p class="lede">Which rival fanbase talks about you most — ranked by how lopsided the
  obsession runs. Counts are real cross-mentions from collected fan conversation; the
  receipt shows both directions so every multiple is auditable. "One-sided" means we have
  little collected conversation from the quiet fanbase, not that they never bring you up.</p>
  {cards}
  <div class="foot">
    Method: directional rival mentions summed over the season, floored at a clear
    dominant side · perception data (violet), never mixed with on-field accents ·
    <a href="/methodology/fan-intelligence.html">full methodology →</a>
  </div>
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Build entry points (never crash the build)
# ---------------------------------------------------------------------------

def build_rent_free_section(
    db: Database,
    output_dir: str | Path = "output/site",
    *,
    limit: int = 24,
) -> list[Path]:
    """Render the latest season's Rent Free board + per-pair cards + redirect."""
    try:
        season = latest_rent_free_season(db)
        if season is None:
            print("[rent-free] no rival-mention rows; section skipped")
            return []
        pairs = fetch_rent_free_pairs(db, season=season, limit=limit)
    except Exception as exc:  # noqa: BLE001
        print(f"[rent-free] fetch failed ({type(exc).__name__}): {exc}")
        return []
    if not pairs:
        print("[rent-free] no pairs cleared the floor; section skipped")
        return []

    out_dir = Path(output_dir) / "hub" / "rent-free" / str(season)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for pair in pairs:
        pslug = f"{pair['a_slug']}-vs-{pair['b_slug']}"
        svg = render_rent_free_card_svg(pair, season=season)
        svg_path = out_dir / f"{pslug}.svg"
        svg_path.write_text(svg, encoding="utf-8")
        written.append(svg_path)
    index_path = out_dir / "index.html"
    index_path.write_text(render_rent_free_index_html(season, pairs), encoding="utf-8")
    written.append(index_path)

    root = Path(output_dir) / "hub" / "rent-free"
    root.mkdir(parents=True, exist_ok=True)
    redirect = (
        '<!doctype html><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0; url=/hub/rent-free/{season}/">'
        "<title>Rent Free</title>"
        f'<p>Redirecting to <a href="/hub/rent-free/{season}/">the latest board</a>.</p>'
    )
    redirect_path = root / "index.html"
    redirect_path.write_text(redirect, encoding="utf-8")
    written.append(redirect_path)
    return written


__all__ = [
    "build_rent_free_section",
    "render_rent_free_card_svg",
    "render_rent_free_index_html",
]
