"""Mobile Responsiveness Tests for World-Class Stats Display

Tests that the stat cards and tables work correctly on various mobile viewports.

Spec: WORLD_CLASS_STATS_IMPLEMENTATION_PLAN.md Phase 4, Task D2
"""
from __future__ import annotations

import pytest

playwright_sync_api = pytest.importorskip(
    "playwright.sync_api",
    reason="playwright not installed (install + `playwright install` to enable visual tests)",
)
Page = playwright_sync_api.Page
expect = playwright_sync_api.expect


# =============================================================================
# VIEWPORT CONFIGURATIONS
# =============================================================================

VIEWPORTS = {
    "iphone_se": {"width": 375, "height": 667},
    "iphone_12": {"width": 390, "height": 844},
    "ipad": {"width": 768, "height": 1024},
}


# =============================================================================
# TEST CASES
# =============================================================================

@pytest.mark.mobile
@pytest.mark.parametrize("viewport_name", VIEWPORTS.keys())
def test_stat_cards_visible_without_horizontal_scroll(
    page: Page,
    viewport_name: str,
) -> None:
    """Test that all stat cards are fully visible without horizontal scroll."""
    viewport = VIEWPORTS[viewport_name]
    page.set_viewport_size(viewport["width"], viewport["height"])

    # Navigate to a player page (replace with actual URL)
    page.goto("file:///path/to/output/site/players/example.html")

    # Check for horizontal scroll
    scroll_width = page.evaluate("document.documentElement.scrollWidth")
    client_width = page.evaluate("document.documentElement.clientWidth")

    assert scroll_width == client_width, (
        f"Page has horizontal scroll on {viewport_name} "
        f"(scroll_width={scroll_width}, client_width={client_width})"
    )


@pytest.mark.mobile
@pytest.mark.parametrize("viewport_name", VIEWPORTS.keys())
def test_tap_targets_are_minimum_size(
    page: Page,
    viewport_name: str,
) -> None:
    """Test that all interactive elements meet minimum tap target size (44x44px)."""
    viewport = VIEWPORTS[viewport_name]
    page.set_viewport_size(viewport["width"], viewport["height"])

    page.goto("file:///path/to/output/site/players/example.html")

    # Check all tappable elements
    tappable_selectors = [
        ".wcfb-percentile-card",  # Stat cards for definitions
        ".wcfb-sort-btn",          # Sort buttons
        "button[data-def]",        # Stat definition triggers
    ]

    for selector in tappable_selectors:
        elements = page.query_selector_all(selector)
        for i, element in enumerate(elements):
            box = element.bounding_box()
            assert box is not None, f"Element {selector}[{i}] has no bounding box"

            # Check minimum tap target size (44x44px per WCAG)
            width_ok = box["width"] >= 44
            height_ok = box["height"] >= 44

            assert width_ok and height_ok, (
                f"Element {selector}[{i}] on {viewport_name} is too small: "
                f"{box['width']}x{box['height']} (minimum: 44x44)"
            )


@pytest.mark.mobile
def test_sticky_column_does_not_overlap_content(page: Page) -> None:
    """Test that sticky first column doesn't overlap content on mobile."""
    # Set mobile viewport
    page.set_viewport_size(375, 667)
    page.goto("file:///path/to/output/site/players/example.html")

    # Check if sticky column exists
    sticky_col = page.query_selector(".wcfb-sticky-column")
    if not sticky_col:
        pytest.skip("No sticky column found on page")

    # Scroll to the right
    page.evaluate("document.documentElement.scrollLeft = 100")

    # Check that sticky column doesn't overlap the content
    sticky_box = sticky_col.bounding_box()
    assert sticky_box is not None

    # The sticky column should stay on the left
    assert sticky_box["x"] == 0, "Sticky column should stay at x=0"


@pytest.mark.mobile
def test_bottom_sheet_slides_up_smoothly(page: Page) -> None:
    """Test that stat definition bottom sheet slides up smoothly on mobile."""
    page.set_viewport_size(375, 667)
    page.goto("file:///path/to/output/site/players/example.html")

    # Find a stat definition trigger
    trigger = page.query_selector("button[data-def]")
    if not trigger:
        pytest.skip("No stat definition triggers found")

    # Click to open bottom sheet
    trigger.click()

    # Wait for bottom sheet to appear
    page.wait_for_selector(".wcfb-stats-bottom-sheet--open", state="visible", timeout=2000)

    # Check that bottom sheet is visible
    bottom_sheet = page.query_selector(".wcfb-stats-bottom-sheet--open")
    assert bottom_sheet is not None

    # Check that bottom sheet covers most of the screen
    sheet_box = bottom_sheet.bounding_box()
    assert sheet_box is not None
    assert sheet_box["height"] > page.viewport_size["height"] * 0.7

    # Test close button
    close_btn = page.query_selector(".wcfb-stats-bottom-sheet__close")
    assert close_btn is not None

    close_btn.click()
    page.wait_for_selector(".wcfb-stats-bottom-sheet--open", state="hidden", timeout=2000)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def check_horizontal_scroll(page: Page) -> tuple[bool, int, int]:
    """Check if page has horizontal scroll.

    Returns:
        Tuple of (has_scroll, scroll_width, client_width)
    """
    scroll_width = page.evaluate("document.documentElement.scrollWidth")
    client_width = page.evaluate("document.documentElement.clientWidth")
    has_scroll = scroll_width > client_width

    return has_scroll, scroll_width, client_width


def get_all_tappable_elements(page: Page) -> list[dict[str, Any]]:
    """Get all tappable elements with their sizes.

    Returns:
        List of dicts with element info
    """
    selectors = [
        "button",
        "a",
        "[onclick]",
        "[data-def]",
        ".wcfb-percentile-card",
    ]

    elements = []
    for selector in selectors:
        found = page.query_selector_all(selector)
        for el in found:
            box = el.bounding_box()
            if box:
                elements.append({
                    "selector": selector,
                    "width": box["width"],
                    "height": box["height"],
                    "x": box["x"],
                    "y": box["y"],
                })

    return elements
