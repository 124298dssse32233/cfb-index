"""Rasterize Fan-Intelligence share-card SVGs to PNG (for og:image unfurling).

Chat apps (iMessage/Discord/X/Slack) unfurl raster og:images, not SVG. This
turns every generated suite card SVG into a sibling PNG at build time, using
**headless Chrome** — already installed on the box, zero new Python/native
dependencies (no Cairo). The SVG is inlined into a zero-margin HTML page (so it
picks up real Anton/Plex from Google Fonts when the build host is online; falls
back to the cards' baked-in condensed/mono system stacks offline), screenshotted
at exact card dimensions, then flattened onto the Noir ground so the PNG is
opaque and safe against white chat bubbles.

Never raises into the build: missing Chrome or a failed render logs and skips.

CLI:
    python manage.py rasterize-cards [--output-dir output/site]
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Noir ground (spec §3) — cards flatten onto this for an opaque shareable PNG.
_GROUND_RGB = (16, 20, 24)

# Suite card directories (each holds per-entity <slug>.svg cards + index.html).
_CARD_HUB_DIRS = ("backometer", "rent-free", "him-watch", "delusion")

_CHROME_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)

_FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Anton&'
    'family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">'
)


def find_chrome() -> str | None:
    for exe in ("chrome", "chromium", "msedge"):
        p = shutil.which(exe)
        if p:
            return p
    for cand in _CHROME_CANDIDATES:
        if os.path.exists(cand):
            return cand
    return None


def _flatten_to_opaque(raw_png: Path, out_png: Path) -> bool:
    """Composite the RGBA screenshot onto the Noir ground -> opaque RGB PNG."""
    try:
        from PIL import Image
    except Exception:  # noqa: BLE001 — Pillow always present, but never crash the build
        # No Pillow: keep the raw (possibly-transparent) PNG rather than nothing.
        shutil.copyfile(raw_png, out_png)
        return True
    im = Image.open(raw_png).convert("RGBA")
    bg = Image.new("RGB", im.size, _GROUND_RGB)
    bg.paste(im, mask=im.split()[3])
    bg.save(out_png, "PNG")
    return True


def rasterize_svg(
    svg_path: Path,
    png_path: Path,
    *,
    width: int = 1200,
    height: int = 675,
    chrome: str | None = None,
    online_fonts: bool = True,
) -> bool:
    chrome = chrome or find_chrome()
    if not chrome:
        return False
    try:
        svg_markup = Path(svg_path).read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return False
    # Drop any XML prolog so the SVG inlines cleanly into HTML.
    if svg_markup.lstrip().startswith("<?xml"):
        svg_markup = svg_markup.split("?>", 1)[-1]

    head_fonts = _FONT_LINK if online_fonts else ""
    html = (
        f"<!doctype html><html><head><meta charset='utf-8'>{head_fonts}"
        f"<style>html,body{{margin:0;padding:0;width:{width}px;height:{height}px;overflow:hidden}}"
        f"svg{{display:block;width:{width}px;height:{height}px}}</style></head>"
        f"<body>{svg_markup}</body></html>"
    )
    with tempfile.TemporaryDirectory() as td:
        html_path = Path(td) / "card.html"
        html_path.write_text(html, encoding="utf-8")
        raw_png = Path(td) / "raw.png"
        cmd = [
            chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--force-device-scale-factor=1", f"--window-size={width},{height}",
            f"--user-data-dir={Path(td) / 'profile'}",
            "--no-first-run", "--no-default-browser-check",
            f"--screenshot={raw_png}", "--default-background-color=00000000",
            f"file:///{html_path.as_posix()}",
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        except Exception as exc:  # noqa: BLE001
            logger.warning("rasterize: chrome failed for %s — %s", svg_path.name, exc)
            return False
        if not raw_png.exists():
            return False
        png_path.parent.mkdir(parents=True, exist_ok=True)
        return _flatten_to_opaque(raw_png, png_path)


def rasterize_suite_cards(output_dir: str | Path = "output/site") -> dict[str, int]:
    """Rasterize every per-entity card SVG under the four suite hub dirs.

    Returns {'attempted', 'written'}; never raises. If Chrome is absent the
    whole step no-ops (cards still ship as SVG + remain downloadable).
    """
    chrome = find_chrome()
    if not chrome:
        logger.info("rasterize: no Chrome/Edge found; PNG og:images skipped")
        return {"attempted": 0, "written": 0}

    hub_root = Path(output_dir) / "hub"
    attempted = written = 0
    for name in _CARD_HUB_DIRS:
        base = hub_root / name
        if not base.exists():
            continue
        for svg in base.rglob("*.svg"):
            attempted += 1
            png = svg.with_suffix(".png")
            if rasterize_svg(svg, png, chrome=chrome):
                written += 1
    logger.info("rasterize: %d/%d card PNGs written", written, attempted)
    return {"attempted": attempted, "written": written}


__all__ = ["rasterize_suite_cards", "rasterize_svg", "find_chrome"]
