"""Capsule renderer — render sealed Fan-Intelligence capsules from their JSON.

Reads ``data/capsules/<label>.json`` (NOT the live DB) so a capsule reproduces
identically forever. Renders ``/capsule/<label>/`` per capsule + a ``/capsule/``
index. Group Chat Noir, standalone, never crashes the build.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from cfb_rankings.fan_metrics.backometer_render import (
    CHALK,
    GROUND,
    HAIRLINE,
    RECEIPT,
    SURFACE,
    ZONE_COLORS,
    _DISPLAY_STACK,
    _MONO_STACK,
    _SANS_STACK,
)
from cfb_rankings.fan_metrics.capsule import CAPSULE_DIR, load_capsules

AURA_TEXT = "#B794FF"
MARKET = "#3D91FF"

_CSS = f"""
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: {GROUND}; color: {CHALK}; font-family: {_SANS_STACK};
    font-feature-settings: "tnum"; line-height: 1.5; padding: 40px 16px 80px;
  }}
  .wrap {{ max-width: 880px; margin: 0 auto; }}
  .eyebrow {{ font-family: {_MONO_STACK}; font-size: 12px; font-weight: 500; color: {RECEIPT};
    letter-spacing: .14em; text-transform: uppercase; margin-bottom: 10px; }}
  h1 {{ font-family: {_DISPLAY_STACK}; font-weight: 400; text-transform: uppercase;
    font-size: clamp(42px, 8vw, 72px); line-height: 1.02; margin-bottom: 6px; }}
  .sub {{ color: {RECEIPT}; font-size: 15px; margin-bottom: 40px; }}
  .sub b {{ color: {CHALK}; }}
  h2 {{ font-family: {_MONO_STACK}; font-size: 13px; font-weight: 500; letter-spacing: .12em;
    text-transform: uppercase; color: {AURA_TEXT}; margin: 38px 0 14px; }}
  .card {{ background: {SURFACE}; border: 1px solid {HAIRLINE}; border-radius: 12px;
    padding: 16px 18px; margin-bottom: 14px; }}
  .line {{ display: flex; align-items: baseline; justify-content: space-between; gap: 12px;
    padding: 7px 0; border-top: 1px solid {HAIRLINE}; }}
  .line:first-child {{ border-top: none; }}
  .line .who {{ font-weight: 600; }}
  .line .who a {{ color: {CHALK}; text-decoration: none; }}
  .line .who a:hover {{ color: {AURA_TEXT}; }}
  .line .what {{ font-family: {_MONO_STACK}; font-size: 13px; color: {RECEIPT}; text-align: right; }}
  .zone {{ font-family: {_DISPLAY_STACK}; text-transform: uppercase; font-size: 16px; }}
  .tax-pos {{ color: {AURA_TEXT}; }} .tax-neg {{ color: #8FD14F; }}
  .v-delusional {{ color: {AURA_TEXT}; }} .v-sharp {{ color: {MARKET}; }} .v-bullish {{ color: {RECEIPT}; }}
  .slang li {{ list-style: none; display: grid; grid-template-columns: 130px 1fr 56px;
    align-items: center; gap: 10px; padding: 6px 0; }}
  .slang .term {{ font-family: {_MONO_STACK}; font-size: 14px; color: {CHALK}; }}
  .slang .bar {{ background: {GROUND}; border-radius: 5px; height: 14px; overflow: hidden; }}
  .slang .bar > i {{ display: block; height: 100%; background: {AURA_TEXT}; border-radius: 5px; }}
  .slang .n {{ font-family: {_MONO_STACK}; font-size: 13px; color: {RECEIPT}; text-align: right; }}
  .foot {{ margin-top: 44px; padding-top: 16px; border-top: 1px solid {HAIRLINE};
    font-family: {_MONO_STACK}; font-size: 12px; color: {RECEIPT}; }}
  .foot a {{ color: {RECEIPT}; }}
"""


def _zone_color(zone: str) -> str:
    return ZONE_COLORS.get(zone, ZONE_COLORS["uneasy"])


def render_capsule_html(cap: dict[str, Any]) -> str:
    label = escape(str(cap.get("label", "")))
    title = escape(str(cap.get("title", "")))
    sealed = escape(str(cap.get("sealed_on", "")))
    season = escape(str(cap.get("season", "")))

    def lines(items: list[str]) -> str:
        return "".join(items)

    backo = lines([
        f'<div class="line"><span class="who">{escape(b["team"])}</span>'
        f'<span class="what"><span class="zone" style="color:{_zone_color(b["zone"])}">'
        f'{escape(str(b["zone"]).replace("_"," "))}</span> · {b["score"]:.0f}</span></div>'
        for b in cap.get("backometer", [])
    ]) or '<div class="line"><span class="what">no qualifying belief signal</span></div>'

    rent = lines([
        f'<div class="line"><span class="who">{escape(p["rent_free"])} lives rent free in {escape(p["obsessed"])}</span>'
        f'<span class="what">{escape(str(p["ratio"]))} · {p["dominant"]}–{p["minor"]}</span></div>'
        for p in cap.get("rent_free", [])
    ])

    aura = cap.get("aura", {})
    most = lines([
        f'<div class="line"><span class="who">{escape(a["player"])} <span style="color:{RECEIPT};font-family:{_MONO_STACK};font-size:12px">{escape(a["pos"])}</span></span>'
        f'<span class="what">aura {a["perception"]:.0f} · tape {a["production"]:.0f} · '
        f'<span class="{ "tax-pos" if a["aura_tax"]>=0 else "tax-neg" }">{a["aura_tax"]:+.0f}</span></span></div>'
        for a in aura.get("most_aura", [])
    ])

    delu = lines([
        f'<div class="line"><span class="who">{escape(d["team"])}</span>'
        f'<span class="what"><span class="v-{d["verdict"]}">{escape(str(d["verdict"]).upper())}</span> · '
        f'fans {d["belief"]:.0f} vs market {d["market"]:.0f}%</span></div>'
        for d in cap.get("delusion", [])
    ])

    slang_items = cap.get("slang", [])
    smax = max((s["docs"] for s in slang_items), default=1)
    slang = "".join(
        f'<li><span class="term">{escape(str(s["term"]).replace("_"," "))}</span>'
        f'<span class="bar"><i style="width:{(s["docs"]/smax*100):.0f}%"></i></span>'
        f'<span class="n">{s["docs"]}</span></li>'
        for s in slang_items
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The {label} Capsule — {title} · CFB Index</title>
<meta name="description" content="A frozen snapshot of CFB fandom: belief, obsession, aura, and delusion, sealed {sealed}.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">CFB Index · Fan Intelligence · sealed {sealed}</div>
  <h1>The {label}<br>Capsule</h1>
  <p class="sub"><b>{title}.</b> A frozen snapshot of what college-football fandom sounded like —
  belief, obsession, aura, and delusion — preserved exactly as it stood. The {season} conversation,
  bottled.</p>

  <h2>The Backometer — who believed</h2>
  <div class="card">{backo}</div>

  <h2>Rent Free — who lived in whose head</h2>
  <div class="card">{rent}</div>

  <h2>Him Watch — the aura board</h2>
  <div class="card">{most}</div>

  <h2>Delusion Premium — belief vs the market</h2>
  <div class="card">{delu}</div>

  <h2>The words of the moment</h2>
  <div class="card"><ul class="slang">{slang}</ul></div>

  <div class="foot">
    Sealed from live data on {sealed} and frozen — this page reads from a committed
    snapshot, not the live database, so it never changes. ·
    <a href="/capsule/">all capsules →</a> · <a href="/">CFB Index</a>
  </div>
</div>
</body>
</html>"""


def _render_index(capsules: list[dict[str, Any]]) -> str:
    items = "".join(
        f'<div class="line"><span class="who"><a href="/capsule/{escape(str(c["label"]))}/">'
        f'The {escape(str(c["label"]))} Capsule</a></span>'
        f'<span class="what">{escape(str(c.get("title","")))} · sealed {escape(str(c.get("sealed_on","")))}</span></div>'
        for c in capsules
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Capsules · CFB Index</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Anton&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>{_CSS}</style></head>
<body><div class="wrap">
  <div class="eyebrow">CFB Index · Fan Intelligence</div>
  <h1>Capsules</h1>
  <p class="sub">Frozen moments in college-football fandom — each one bottled and preserved.</p>
  <div class="card">{items or '<div class="line"><span class="what">no capsules sealed yet</span></div>'}</div>
</div></body></html>"""


def build_capsules_section(
    output_dir: str | Path = "output/site",
    capsule_dir: Path | str = CAPSULE_DIR,
) -> list[Path]:
    """Render every committed capsule + the /capsule/ index. Never raises."""
    try:
        capsules = load_capsules(capsule_dir)
    except Exception as exc:  # noqa: BLE001
        print(f"[capsule] load failed ({type(exc).__name__}): {exc}")
        return []
    if not capsules:
        return []
    root = Path(output_dir) / "capsule"
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for cap in capsules:
        label = str(cap.get("label") or "").strip()
        if not label:
            continue
        d = root / label
        d.mkdir(parents=True, exist_ok=True)
        p = d / "index.html"
        p.write_text(render_capsule_html(cap), encoding="utf-8")
        written.append(p)
    idx = root / "index.html"
    idx.write_text(_render_index(capsules), encoding="utf-8")
    written.append(idx)
    return written


__all__ = ["build_capsules_section", "render_capsule_html"]
