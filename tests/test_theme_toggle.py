"""Contract tests for the theme toggle (Sprint v5-11.5).

These are file-shape + render-helper tests — no JS engine required.
The behavioral verification of the toggle (cycle, persistence,
data-theme attribute flips) happens via the live preview demo at
docs/mockups/theme_toggle_demo.html.

Key invariants enforced here:
  * theme_init.js MUST be tiny + synchronous (FOUC prevention)
  * theme_toggle.js exposes window.cfbTheme.{set,cycle,current,...}
  * theme_toggle.css uses var() fallback chains (host-agnostic)
  * tokens-bridge.css uses :where() to neutralize OS-pref specificity
    so [data-theme] overrides win (the bug I caught + fixed during
    demo verification)
  * render_theme_assets_head includes init inline (FOUC) + CSS link +
    deferred toggle script
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
THEME_ASSETS = ROOT / "src" / "cfb_rankings" / "theme" / "assets"
BRIDGE_CSS = ROOT / "docs" / "design-system" / "assets" / "tokens-bridge.css"


@pytest.fixture(scope="module")
def init_js() -> str:
    return (THEME_ASSETS / "theme_init.js").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def toggle_js() -> str:
    return (THEME_ASSETS / "theme_toggle.js").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def toggle_css() -> str:
    return (THEME_ASSETS / "theme_toggle.css").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def bridge_css() -> str:
    return BRIDGE_CSS.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# theme_init.js — FOUC prevention contract
# ---------------------------------------------------------------------------

def test_init_script_exists() -> None:
    p = THEME_ASSETS / "theme_init.js"
    assert p.exists()
    assert p.stat().st_size > 100


def test_init_script_is_tiny(init_js: str) -> None:
    """The FOUC-prevention script inlines in every page <head>. Keep it
    under 1KB so the budget impact is negligible."""
    assert len(init_js) < 1024, (
        f"theme_init.js is {len(init_js)} bytes; spec requires <1024 "
        "to keep <head> inline budget small"
    )


def test_init_script_reads_storage_key(init_js: str) -> None:
    assert "cfb-theme-pref" in init_js


def test_init_script_sets_data_theme_attribute(init_js: str) -> None:
    """Must set data-theme on <html> for 'light'/'dark' prefs; remove
    for 'system'. That's what the bridge CSS keys on."""
    assert "setAttribute" in init_js
    assert "removeAttribute" in init_js
    assert "data-theme" in init_js


def test_init_script_handles_storage_unavailable(init_js: str) -> None:
    """Privacy-mode browsers throw on localStorage access — must catch."""
    assert "try" in init_js
    assert "catch" in init_js


def test_init_script_is_iife(init_js: str) -> None:
    """Must run immediately + not leak globals."""
    assert re.search(r"\(function\s*\(\s*\)\s*\{", init_js)


# ---------------------------------------------------------------------------
# theme_toggle.js — public API + behavior
# ---------------------------------------------------------------------------

def test_toggle_js_exists(toggle_js: str) -> None:
    assert len(toggle_js) > 1000


def test_toggle_js_use_strict(toggle_js: str) -> None:
    assert "'use strict'" in toggle_js


def test_toggle_js_exposes_public_api(toggle_js: str) -> None:
    assert "window.cfbTheme" in toggle_js
    for method in ("current", "effective", "cycle", "set", "system"):
        # Each method appears as a property in the API export
        assert re.search(
            rf"\b{method}\b\s*:", toggle_js,
        ), f"window.cfbTheme.{method} missing from public API"


def test_toggle_js_uses_same_storage_key(
    init_js: str, toggle_js: str,
) -> None:
    """init + toggle must agree on the storage key."""
    assert "cfb-theme-pref" in init_js
    assert "cfb-theme-pref" in toggle_js


def test_toggle_js_state_machine_order(toggle_js: str) -> None:
    """Cycle: system → light → dark → system. Order matters for UX
    consistency (light comes before dark)."""
    m = re.search(r"ORDER\s*=\s*\[([^\]]+)\]", toggle_js)
    assert m, "expected ORDER constant"
    order = m.group(1).replace(" ", "").replace("'", "").replace('"', "")
    assert order == "system,light,dark"


def test_toggle_js_listens_to_prefers_color_scheme(toggle_js: str) -> None:
    """When in system mode, OS-level pref changes should refire the
    cfb-theme-changed event so charts re-render."""
    assert "matchMedia" in toggle_js
    assert "prefers-color-scheme" in toggle_js


def test_toggle_js_emits_cfb_theme_changed_event(toggle_js: str) -> None:
    """Other components subscribe to this to re-render."""
    assert "cfb-theme-changed" in toggle_js
    assert "CustomEvent" in toggle_js


def test_toggle_js_click_delegation(toggle_js: str) -> None:
    """[data-theme-toggle] click handler must use delegation so dynam-
    ically inserted buttons work too."""
    assert "data-theme-toggle" in toggle_js
    assert "closest" in toggle_js


def test_toggle_js_handles_storage_errors(toggle_js: str) -> None:
    assert "try" in toggle_js
    assert "catch" in toggle_js


def test_toggle_js_initializes_after_dom_ready(toggle_js: str) -> None:
    """Buttons might not be in the DOM when script loads — wait for
    DOMContentLoaded if loading is in progress."""
    assert "DOMContentLoaded" in toggle_js or "readyState" in toggle_js


def test_toggle_js_aria_labels(toggle_js: str) -> None:
    """Accessibility: aria-label + aria-pressed on toggle buttons."""
    assert "aria-label" in toggle_js
    assert "aria-pressed" in toggle_js


# ---------------------------------------------------------------------------
# theme_toggle.css — styling contract
# ---------------------------------------------------------------------------

def test_toggle_css_required_selectors(toggle_css: str) -> None:
    for selector in (
        ".theme-toggle",
        ".theme-toggle__icon",
        ".theme-toggle__icon--system",
        ".theme-toggle__icon--light",
        ".theme-toggle__icon--dark",
        '.theme-toggle[data-state="system"]',
        '.theme-toggle[data-state="light"]',
        '.theme-toggle[data-state="dark"]',
        ".theme-toggle:hover",
        ".theme-toggle:focus-visible",
    ):
        assert selector in toggle_css, f"missing rule: {selector}"


def test_toggle_css_var_fallback_chains(toggle_css: str) -> None:
    """The toggle should render correctly on hosts that haven't loaded
    tokens-bridge.css yet — relies on var() chains all the way down to
    a hardcoded literal."""
    # Pick three load-bearing tokens
    for token in ("--stroke-default", "--fg-secondary", "--accent-primary"):
        assert re.search(
            rf"var\(\s*{re.escape(token)}\s*,",
            toggle_css,
        ), f"{token} usage missing fallback"


def test_toggle_css_reduced_motion(toggle_css: str) -> None:
    """Animations must be killed under prefers-reduced-motion."""
    assert "prefers-reduced-motion" in toggle_css


def test_toggle_css_mobile_breakpoint(toggle_css: str) -> None:
    """Tooltip is hidden on touch devices (no hover) at <640px."""
    assert re.search(r"@media\s*\(max-width:\s*640px\)", toggle_css)


# ---------------------------------------------------------------------------
# tokens-bridge.css — specificity contract (the bug I caught + fixed)
# ---------------------------------------------------------------------------

def test_bridge_uses_where_for_os_preference(bridge_css: str) -> None:
    """The @media (prefers-color-scheme: light) block MUST be wrapped
    in :where() so its specificity is 0. Otherwise [data-theme="dark"]
    overrides can't beat it — the bug I caught when the demo flipped
    data-theme but the body bg didn't change."""
    media_block = re.search(
        r"@media\s*\(prefers-color-scheme:\s*light\)\s*\{[^}]+\}",
        bridge_css,
    )
    assert media_block, "missing @media (prefers-color-scheme: light) block"
    # The selector inside must use :where()
    assert ":where(" in media_block.group(0), (
        "@media block must use :where() to neutralize specificity — "
        "otherwise the [data-theme] overrides won't win"
    )


def test_bridge_data_theme_dark_override(bridge_css: str) -> None:
    """User-explicit dark mode override exists + sets the inverted ramp."""
    dark_block = re.search(
        r':root\[data-theme="dark"\]\s*\{([^}]+)\}',
        bridge_css,
    )
    assert dark_block, "missing :root[data-theme=\"dark\"] block"
    body = dark_block.group(1)
    assert "--semantic-bg-base" in body
    assert "#0b0d12" in body  # dark base color


def test_bridge_data_theme_light_override(bridge_css: str) -> None:
    light_block = re.search(
        r':root\[data-theme="light"\]\s*\{([^}]+)\}',
        bridge_css,
    )
    assert light_block, "missing :root[data-theme=\"light\"] block"
    body = light_block.group(1)
    assert "--semantic-bg-base" in body
    assert "#faf8f3" in body  # bone paper


def test_bridge_excludes_daily_mailbag_wire(bridge_css: str) -> None:
    """Daily/Mailbag/Wire keep their bespoke palettes regardless of OS
    preference — per v5_11_5_sprint_brief.md §Part 5 risk."""
    media_block = re.search(
        r"@media\s*\(prefers-color-scheme:\s*light\)\s*\{[^}]+\}",
        bridge_css,
    )
    assert media_block
    selectors = media_block.group(0)
    for cls in ("daily-page", "mailbag-page", "wire-page"):
        assert cls in selectors, (
            f"@media block must exclude .{cls} so its bespoke palette "
            "isn't auto-flipped"
        )


# ---------------------------------------------------------------------------
# render.py helpers
# ---------------------------------------------------------------------------

def test_render_helpers_importable() -> None:
    from cfb_rankings.theme import (
        THEME_INIT_SCRIPT,
        render_theme_assets_head,
        render_theme_toggle_button,
    )
    assert THEME_INIT_SCRIPT
    assert callable(render_theme_assets_head)
    assert callable(render_theme_toggle_button)


def test_render_button_emits_data_theme_toggle() -> None:
    from cfb_rankings.theme import render_theme_toggle_button
    html = render_theme_toggle_button()
    assert "data-theme-toggle" in html
    assert 'aria-label="Toggle theme"' in html
    assert 'type="button"' in html


def test_render_assets_head_includes_fouc_init() -> None:
    from cfb_rankings.theme import render_theme_assets_head
    head = render_theme_assets_head()
    # FOUC init script is inlined (NOT deferred)
    assert "<script>" in head
    assert "cfb-theme-pref" in head
    # CSS link present
    assert 'rel="stylesheet"' in head
    assert "theme_toggle.css" in head
    # Toggle script is deferred
    assert 'defer src="' in head
    assert "theme_toggle.js" in head


def test_render_assets_head_escapes_custom_urls() -> None:
    from cfb_rankings.theme import render_theme_assets_head
    head = render_theme_assets_head(
        css_url='" onload="alert(1)"',
    )
    assert "alert(1)" not in head or "&quot;" in head


# ---------------------------------------------------------------------------
# Demo specimen
# ---------------------------------------------------------------------------

def test_demo_specimen_exists() -> None:
    demo = ROOT / "docs" / "mockups" / "theme_toggle_demo.html"
    assert demo.exists(), (
        "Run scripts/_theme_toggle_demo.py to regenerate theme_toggle_demo.html"
    )
    text = demo.read_text(encoding="utf-8")
    # Demo must include the trigger button + the assets
    assert "data-theme-toggle" in text
    assert "cfb-theme-pref" in text  # FOUC init script inlined
    assert "tokens-bridge.css" in text or ":root[data-theme=" in text
