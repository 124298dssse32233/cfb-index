"""Share-card PNG renderer for Chronicle Visuals.

v3 §15 P0 deliverable: "share-card renderer 1200x675 and 1080x1350 image exports."

Implementation uses resvg-py (pure-Python Rust binding). Output goes to
output/site/_visuals/{slug}_{visual_id}.png. The renderer wraps the
existing SVG in a sized canvas with the visual's headline as bottom caption
so the cropped image still makes sense without surrounding article prose
(v3 §12 "Editorial Gates: share value").
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

log = logging.getLogger("cfb_rankings.chronicle.visuals.share_renderer")

# Default landscape share card — Twitter/Facebook OG sizing.
SHARE_W = 1200
SHARE_H = 675

# Output directory under output/site/ so Vercel serves it directly.
_OUTPUT_REL = "_visuals"


def _resvg_render(svg_str: str, output_width: int) -> bytes:
    """Render an SVG string to PNG bytes using resvg-py."""
    try:
        from resvg_py import svg_to_bytes
    except ImportError as exc:
        raise RuntimeError(
            "resvg-py not installed — run `pip install resvg-py` to enable "
            "share-card PNG export."
        ) from exc
    return bytes(svg_to_bytes(svg_string=svg_str))


def build_share_svg(
    *,
    headline: str,
    inner_svg: str,
    accent_hex: str = "#c9a24a",
    site_label: str = "CFB INDEX",
    sample_n: int | None = None,
    confidence: str | None = None,
) -> str:
    """Wrap the inner-card SVG in a 1200x675 share card frame.

    Layout:
        - top 56px: brand strip (CFB INDEX, accent rule)
        - middle: scaled inner_svg
        - bottom 120px: headline (serif, large) + meta strip
    """
    # Pull the inner viewBox so we can preserve aspect ratio
    m = re.search(r'viewBox="([\d\.\s-]+)"', inner_svg)
    if m:
        parts = m.group(1).split()
        if len(parts) == 4:
            inner_vb_w = float(parts[2])
            inner_vb_h = float(parts[3])
        else:
            inner_vb_w, inner_vb_h = 600.0, 400.0
    else:
        inner_vb_w, inner_vb_h = 600.0, 400.0

    # Compute drawable area (margins for chrome)
    pad_x = 48
    chrome_top = 64
    chrome_bottom = 140
    draw_w = SHARE_W - 2 * pad_x
    draw_h = SHARE_H - chrome_top - chrome_bottom
    scale = min(draw_w / inner_vb_w, draw_h / inner_vb_h)
    scaled_w = inner_vb_w * scale
    scaled_h = inner_vb_h * scale
    inner_x = pad_x + (draw_w - scaled_w) / 2
    inner_y = chrome_top + (draw_h - scaled_h) / 2

    # Strip inner <svg ...> wrapper attrs and replace with <g transform> for nesting
    stripped = re.sub(r'<svg\b[^>]*>', '', inner_svg, count=1)
    stripped = re.sub(r'</svg>\s*$', '', stripped, count=1)

    # Escape headline for SVG (XML text node)
    headline_esc = (
        headline.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    meta_bits = []
    if sample_n is not None:
        meta_bits.append(f"n={sample_n}")
    if confidence and confidence != "unset":
        meta_bits.append(confidence)
    meta_bits.append("cfbindex")
    meta_text = " · ".join(meta_bits)

    # Headline can be long — split into two lines if > 64 chars
    if len(headline_esc) > 64:
        words = headline_esc.split()
        mid = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])
    else:
        line1 = headline_esc
        line2 = ""

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{SHARE_W}" height="{SHARE_H}" viewBox="0 0 {SHARE_W} {SHARE_H}">
  <rect width="{SHARE_W}" height="{SHARE_H}" fill="#f6f1e6"/>
  <rect x="0" y="0" width="{SHARE_W}" height="6" fill="{accent_hex}"/>
  <text x="{pad_x}" y="40" font-family="Georgia,serif" font-size="14"
        font-weight="700" letter-spacing="3" fill="#1a1a1a">{site_label}</text>
  <g transform="translate({inner_x:.1f},{inner_y:.1f}) scale({scale:.4f})">{stripped}</g>
  <text x="{pad_x}" y="{SHARE_H - 80}" font-family="Georgia,serif" font-size="28"
        font-weight="700" fill="#1a1a1a">{line1}</text>
  <text x="{pad_x}" y="{SHARE_H - 46}" font-family="Georgia,serif" font-size="28"
        font-weight="700" fill="#1a1a1a">{line2}</text>
  <text x="{pad_x}" y="{SHARE_H - 18}" font-family="Inter,Helvetica,Arial,sans-serif"
        font-size="13" fill="#7a7a7a">{meta_text}</text>
</svg>'''


def write_share_png(
    *,
    slug: str,
    visual_id: str,
    inner_svg: str,
    headline: str,
    accent_hex: str = "#c9a24a",
    sample_n: int | None = None,
    confidence: str | None = None,
    output_root: Path | None = None,
) -> str | None:
    """Render the share card to PNG and return the relative asset path.

    Returns None if resvg-py is unavailable so the pipeline degrades gracefully.
    """
    try:
        share_svg = build_share_svg(
            headline=headline,
            inner_svg=inner_svg,
            accent_hex=accent_hex,
            sample_n=sample_n,
            confidence=confidence,
        )
        png_bytes = _resvg_render(share_svg, SHARE_W)
    except RuntimeError as exc:
        log.warning("share-card render skipped (%s)", exc)
        return None
    except Exception as exc:
        log.exception("share-card render failed for %s/%s: %s", slug, visual_id, exc)
        return None

    output_root = output_root or Path("output/site")
    asset_dir = output_root / _OUTPUT_REL
    asset_dir.mkdir(parents=True, exist_ok=True)
    rel_path = f"{_OUTPUT_REL}/{slug}_{visual_id}.png"
    full_path = output_root / rel_path
    full_path.write_bytes(png_bytes)
    return rel_path
