"""Contract tests for cmdk overlay assets (CSS + JS).

These are file-shape tests — no JS engine required. They guard against
silent drift between the documented spec (Pattern 9) and what we ship.
Behavioral verification of the overlay happens via the live preview in
docs/mockups/cmdk_demo.html (covered by scripts/_cmdk_demo.py).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


ASSETS_DIR = (
    Path(__file__).resolve().parents[1]
    / "src" / "cfb_rankings" / "cmdk" / "assets"
)


@pytest.fixture(scope="module")
def cmdk_css() -> str:
    return (ASSETS_DIR / "cmdk.css").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def cmdk_js() -> str:
    return (ASSETS_DIR / "cmdk.js").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Existence + non-trivial size
# ---------------------------------------------------------------------------

def test_cmdk_css_exists_and_nonempty() -> None:
    path = ASSETS_DIR / "cmdk.css"
    assert path.exists(), f"missing {path}"
    assert path.stat().st_size > 1000, "cmdk.css is suspiciously small"


def test_cmdk_js_exists_and_nonempty() -> None:
    path = ASSETS_DIR / "cmdk.js"
    assert path.exists(), f"missing {path}"
    assert path.stat().st_size > 1000, "cmdk.js is suspiciously small"


# ---------------------------------------------------------------------------
# CSS contract — every selector the JS injects must have a rule
# ---------------------------------------------------------------------------

# Selectors the JS injects via document.createElement / innerHTML.
# Each must have at least one rule in cmdk.css or the overlay renders
# as unstyled default DOM.
_REQUIRED_CSS_SELECTORS = [
    ".cmdk-backdrop",
    ".cmdk-dialog",
    ".cmdk-input-wrap",
    ".cmdk-input",
    ".cmdk-input-icon",
    ".cmdk-results",
    ".cmdk-group",
    ".cmdk-group__label",
    ".cmdk-item",
    ".cmdk-item__title",
    ".cmdk-item__subtitle",
    ".cmdk-item__kind",
    ".cmdk-empty",
    ".cmdk-footer",
    ".cmdk-footer__key",
    ".cmdk-shortcut",
    ".cmdk-trigger",
    ".cmdk-trigger__shortcut",
]


@pytest.mark.parametrize("selector", _REQUIRED_CSS_SELECTORS)
def test_css_carries_required_selector(cmdk_css: str, selector: str) -> None:
    """Every injected class must have at least one CSS rule."""
    # Use literal substring check — the rule's exact form (with pseudo-
    # classes, attributes, etc.) doesn't matter as long as it exists.
    assert selector in cmdk_css, f"missing rule for {selector}"


def test_css_carries_per_kind_badge_rules(cmdk_css: str) -> None:
    """All 7 SearchItem kinds must have a kind-badge color rule."""
    kinds = ("profile", "team", "player", "edition", "mailbag",
             "conference", "methodology")
    for k in kinds:
        sel = f".cmdk-item__kind--{k}"
        assert sel in cmdk_css, f"missing per-kind badge rule for {sel}"


def test_css_includes_mobile_breakpoint(cmdk_css: str) -> None:
    """The 640px mobile breakpoint must exist (bottom-sheet)."""
    assert re.search(r"@media\s*\(max-width:\s*640px\)", cmdk_css), (
        "missing @media (max-width: 640px) bottom-sheet rule"
    )


def test_css_includes_reduced_motion_block(cmdk_css: str) -> None:
    """Reduced-motion accessibility opt-out must exist."""
    assert "prefers-reduced-motion" in cmdk_css


def test_css_uses_var_fallback_chain(cmdk_css: str) -> None:
    """Tokens must use var() fallback chain so the overlay degrades
    when the host page hasn't defined the team-pages design tokens."""
    # Pick three load-bearing tokens
    for token in ("--bg-card", "--fg-primary", "--accent-primary"):
        # The token should appear with a fallback (anything after a comma)
        assert re.search(
            rf"var\(\s*{re.escape(token)}\s*,",
            cmdk_css,
        ), f"{token} usage missing fallback (var({token}, ...))"


# ---------------------------------------------------------------------------
# JS contract — required public functions + behaviors
# ---------------------------------------------------------------------------

def test_js_uses_strict_mode(cmdk_js: str) -> None:
    assert "'use strict'" in cmdk_js


def test_js_is_iife_wrapped(cmdk_js: str) -> None:
    """The script must run in an IIFE so it doesn't leak helpers."""
    # Tolerant: `(function () {` or `(function() {` at the top
    assert re.search(r"\(function\s*\(\s*\)\s*\{", cmdk_js)


def test_js_exposes_window_cmdk(cmdk_js: str) -> None:
    """Public API: window.cmdk for testing + programmatic open."""
    assert "window.cmdk" in cmdk_js
    assert "open:" in cmdk_js
    assert "close:" in cmdk_js


def test_js_binds_cmd_k(cmdk_js: str) -> None:
    """The script must register the Cmd-K / Ctrl-K keybind."""
    # Detect by looking for both metaKey/ctrlKey AND 'k' key match
    assert "metaKey" in cmdk_js
    assert "ctrlKey" in cmdk_js
    # The 'k' key is the trigger
    assert re.search(r"['\"]k['\"]", cmdk_js)


def test_js_handles_data_trigger_attribute(cmdk_js: str) -> None:
    """[data-cmdk-trigger] click-to-open must be wired."""
    assert "data-cmdk-trigger" in cmdk_js


def test_js_keyboard_navigation_supported(cmdk_js: str) -> None:
    """ArrowUp / ArrowDown / Enter / Escape all handled."""
    for key in ("ArrowDown", "ArrowUp", "Enter", "Escape"):
        assert key in cmdk_js, f"keyboard handler for {key} missing"


def test_js_html_escapes_user_content(cmdk_js: str) -> None:
    """XSS defense: HTML-escape helper must exist + be applied."""
    assert "escapeHtml" in cmdk_js
    assert "&amp;" in cmdk_js
    assert "&lt;" in cmdk_js
    assert "&gt;" in cmdk_js


def test_js_supports_sessionstorage_cache(cmdk_js: str) -> None:
    """Index payload is cached in sessionStorage with TTL."""
    assert "sessionStorage" in cmdk_js
    assert "storageTtlMs" in cmdk_js


def test_js_supports_url_relative_or_external(cmdk_js: str) -> None:
    """Internal /paths use location.href; external open in new tab."""
    assert "window.location.href" in cmdk_js
    assert "window.open" in cmdk_js


def test_js_default_index_url(cmdk_js: str) -> None:
    """Default index URL is /search-index.json — matches what
    cli.py build-search-index writes."""
    assert "/search-index.json" in cmdk_js


def test_js_supports_window_cmdk_config_override(cmdk_js: str) -> None:
    """Hosts can override via window.CMDK_CONFIG."""
    assert "window.CMDK_CONFIG" in cmdk_js


def test_js_role_dialog_set(cmdk_js: str) -> None:
    """Accessibility: the overlay is announced as role=dialog with
    aria-modal=true."""
    assert "'dialog'" in cmdk_js
    assert "aria-modal" in cmdk_js


def test_js_listbox_role_on_results(cmdk_js: str) -> None:
    """Accessibility: results region is role=listbox."""
    assert "'listbox'" in cmdk_js


def test_js_emits_aria_selected_per_item(cmdk_js: str) -> None:
    """Accessibility: selected item gets aria-selected=true."""
    assert "aria-selected" in cmdk_js


def test_js_aware_of_index_schema_version(cmdk_js: str) -> None:
    """Loose schema check: the JS reads items[] from the payload —
    matches what cfb_rankings.cmdk.write_search_index emits."""
    assert "items" in cmdk_js
    # The JS doesn't strictly require schema_version, but should at
    # least handle the payload shape correctly:
    assert ".items" in cmdk_js


# ---------------------------------------------------------------------------
# Cross-asset coherence
# ---------------------------------------------------------------------------

def test_css_and_js_agree_on_class_names(
    cmdk_css: str, cmdk_js: str,
) -> None:
    """Every static class name the JS injects must have a CSS rule.
    Concatenated/templated classes (e.g. `'cmdk-item__kind--' + kind`)
    are excluded since they expand at runtime; per-kind badge rules
    are covered separately by test_css_carries_per_kind_badge_rules."""
    # Pull classes the JS uses via className = "..."
    js_classes = set(re.findall(r"className\s*=\s*['\"]([^'\"]+)['\"]", cmdk_js))
    # Also collect innerHTML class= references
    inner_classes = set()
    for m in re.findall(r"class=\\?\"([^\"\\]+)\\?\"", cmdk_js):
        for c in m.split():
            inner_classes.add(c)
    all_classes = js_classes | inner_classes
    # Valid CSS class identifier: starts with letter/underscore, then
    # word chars / hyphens. Filter out anything with stray quotes or
    # whitespace artifacts from the regex pass.
    valid_class_re = re.compile(r"^[A-Za-z_][\w-]*$")
    cmdk_classes = {
        c for c in all_classes
        if c.startswith("cmdk") and valid_class_re.match(c)
    }
    # Every static cmdk class should be referenced in CSS at least once
    for cls in cmdk_classes:
        assert cls in cmdk_css, (
            f"JS uses class '{cls}' but cmdk.css has no rule for it"
        )


def test_demo_specimen_exists() -> None:
    """The reviewer demo file must be on disk."""
    demo = (
        Path(__file__).resolve().parents[1]
        / "docs" / "mockups" / "cmdk_demo.html"
    )
    assert demo.exists(), (
        "Run scripts/_cmdk_demo.py to regenerate cmdk_demo.html"
    )
    text = demo.read_text(encoding="utf-8")
    # Demo must include the trigger button + the JS + the demo index URL
    assert "cmdk-trigger" in text
    assert "data-cmdk-trigger" in text
    assert "cmdk_demo_index.json" in text


def test_demo_index_json_valid() -> None:
    """The demo index JSON must be parseable + match the SearchItem shape."""
    import json
    p = (
        Path(__file__).resolve().parents[1]
        / "docs" / "mockups" / "cmdk_demo_index.json"
    )
    assert p.exists()
    payload = json.loads(p.read_text(encoding="utf-8"))
    assert payload.get("schema_version") == 1
    items = payload.get("items")
    assert isinstance(items, list)
    assert len(items) > 0
    for i in items:
        assert "kind" in i
        assert "title" in i
        assert "url" in i
