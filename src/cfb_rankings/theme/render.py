"""Python-side helpers for the theme toggle (Sprint v5-11.5).

Renderers call these to inject the right assets + button markup into
their pages. The actual logic lives in the assets/ JS + CSS files.
"""

from __future__ import annotations

import html as _html
from pathlib import Path


_ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def _read_asset(name: str) -> str:
    return (_ASSETS_DIR / name).read_text(encoding="utf-8")


# Read the FOUC-prevention script once at import time. Tiny enough to
# inline in every <head>; doing so avoids a render-blocking network
# request that would defeat the FOUC purpose.
THEME_INIT_SCRIPT = _read_asset("theme_init.js")


def render_theme_assets_head(
    *,
    css_url: str = "/assets/theme_toggle.css",
    js_url: str = "/assets/theme_toggle.js",
    inline_init: bool = True,
) -> str:
    """Emit the <head> stanza for the theme toggle.

    The init script MUST run before first paint to prevent FOUC, so
    it's inlined (default). The toggle UI script can be deferred.
    The CSS uses var() fallback chains so the page renders correctly
    even before tokens-bridge.css loads.

    Window A wires this into the global head template. Output shape::

        <script>{theme_init.js inlined}</script>
        <link rel="stylesheet" href="/assets/theme_toggle.css">
        <script defer src="/assets/theme_toggle.js"></script>
    """
    parts: list[str] = []
    if inline_init:
        # Defensive escape: if THEME_INIT_SCRIPT ever contains the
        # literal `</script>`, the HTML parser would close the inline
        # tag prematurely. The current script doesn't, but future edits
        # to theme_init.js shouldn't require remembering this constraint.
        script_safe = THEME_INIT_SCRIPT.replace("</script>", "<\\/script>")
        parts.append(f'<script>{script_safe}</script>')
    parts.append(
        f'<link rel="stylesheet" href="{_html.escape(css_url)}">'
    )
    parts.append(
        f'<script defer src="{_html.escape(js_url)}"></script>'
    )
    return "\n".join(parts)


def render_theme_toggle_button(*, css_class: str = "theme-toggle") -> str:
    """Emit the toggle button markup.

    The button starts as a plain element; the JS injects the SVG icons
    + sets data-state on first activation. This is intentional — we
    don't want to commit 800 bytes of inline SVG to every page.
    """
    safe_class = _html.escape(css_class)
    return (
        f'<button class="{safe_class}" data-theme-toggle '
        f'aria-label="Toggle theme" type="button"></button>'
    )


__all__ = [
    "THEME_INIT_SCRIPT",
    "render_theme_assets_head",
    "render_theme_toggle_button",
]
