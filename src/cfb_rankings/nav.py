"""
Global navigation component for CFB Index.

Provides consistent navigation across all pages. This is the single source
of truth for site-wide navigation to ensure UX consistency.

Navigation Structure:
    - Home (logo)
    - Power Rankings
    - Teams
    - Players
    - Daily
    - Wire
    - Editions
    - Storylines
    - Methodology

Mobile Navigation:
    - Hamburger menu for screens < 860px
    - Full-width dropdown with proper touch targets
    - ARIA labels for accessibility

Usage:
    from cfb_rankings.nav import render_global_nav

    nav_html = render_global_nav(current_page="/rankings/")
"""

from __future__ import annotations

from typing import Literal


# Valid navigation paths
NavPath = Literal[
    "/",
    "/rankings/",
    "/teams/",
    "/players/",
    "/daily/",
    "/wire/",
    "/editions/",
    "/storylines/",
    "/methodology/",
]


# Global navigation items - ordered by importance
# Labels should be concise and descriptive
NAV_ITEMS = [
    {"path": "/rankings/", "label": "Rankings"},
    {"path": "/teams/", "label": "Teams"},
    {"path": "/players/spotlight.html", "label": "Players"},
    {"path": "/heisman/", "label": "Heisman"},
    {"path": "/programs/", "label": "Programs"},
    {"path": "/history/", "label": "History"},
    {"path": "/editions/", "label": "Editions"},
    {"path": "/wire/", "label": "Wire"},
    {"path": "/about-model/", "label": "How It Works"},
]


def render_global_nav(
    current_page: str = "/",
    variant: Literal["desktop", "mobile", "both"] = "both",
    brand_link: str = "/",
    show_mobile_toggle: bool = True,
) -> str:
    """Render the global navigation component.

    Args:
        current_page: Current page path for active state highlighting
        variant: Which variant(s) to render ("desktop", "mobile", "both")
        brand_link: Where the logo/brand links to (default: homepage)
        show_mobile_toggle: Whether to include hamburger toggle button

    Returns:
        HTML string containing the navigation markup
    """
    nav_links = "\n".join(
        _render_nav_link(item["path"], item["label"], current_page)
        for item in NAV_ITEMS
    )

    mobile_toggle = ""
    if show_mobile_toggle and variant in ("desktop", "both"):
        mobile_toggle = """
        <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="nav-links" aria-label="Toggle navigation menu">
          <span class="hamburger"></span>
          <span class="hamburger"></span>
          <span class="hamburger"></span>
        </button>"""

    if variant == "mobile":
        # Mobile-only nav (for inside responsive menu)
        return f"""
    <nav class="nav" id="nav-links" role="navigation">
      <a class="nav-link{_is_active('/', current_page)}" href="{brand_link}">Home</a>
      {nav_links}
    </nav>"""
    elif variant == "desktop":
        # Desktop-only nav
        return f"""
      <nav class="nav" role="navigation">
        {nav_links}
      </nav>"""
    else:
        # Full nav with mobile toggle
        return f"""
      <nav class="nav-container" role="navigation">
        {mobile_toggle}
        <div class="nav-links" id="nav-links">
          {nav_links}
        </div>
      </nav>"""


def _render_nav_link(path: str, label: str, current_page: str) -> str:
    """Render a single navigation link with active state."""
    active_class = _is_active(path, current_page)
    return f'        <a class="nav-link{active_class}" href="{path}">{label}</a>'


def _is_active(path: str, current_page: str) -> str:
    """Check if a path should be marked as active."""
    # Exact match
    if path == current_page:
        return " is-current"

    # Homepage special case
    if path == "/" and current_page == "/":
        return " is-current"

    # Parent path match (e.g., /teams/ matches /teams/alabama.html)
    if path != "/" and current_page.startswith(path.rstrip("/")):
        return " is-current"

    return ""


def render_breadcrumb(
    current_page: str,
    page_title: str,
    parent_pages: list[tuple[str, str]] | None = None,
) -> str:
    """Render a breadcrumb navigation component.

    Args:
        current_page: Current page path
        page_title: Title of the current page
        parent_pages: List of (path, label) tuples for parent pages

    Returns:
        HTML string containing breadcrumb markup
    """
    crumbs = [('<a href="/">Home</a>', "/")]

    if parent_pages:
        for path, label in parent_pages:
            crumbs.append((f'<a href="{path}">{label}</a>', path))

    crumbs.append((page_title, current_page))

    crumb_html = "\n".join(
        f'      <span class="breadcrumb-item">{crumb[0]}</span>'
        for i, crumb in enumerate(crumbs)
    )
    separators = "\n".join(
        '      <span class="breadcrumb-sep">/</span>' for _ in range(len(crumbs) - 1)
    )

    return f"""
    <nav class="breadcrumb" aria-label="Breadcrumb">
      {crumb_html}
      {separators}
    </nav>"""
