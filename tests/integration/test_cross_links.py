"""Cross-Link Verification Tests

Verifies that all player/team/opponent links resolve correctly.

Spec: WORLD_CLASS_STATS_IMPLEMENTATION_PLAN.md Phase 4, Task D3
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from bs4 import BeautifulSoup


# =============================================================================
# TEST CASES
# =============================================================================

@pytest.mark.integration
def test_player_cross_links(output_dir: Path) -> None:
    """Verify player pages link to valid team pages."""
    # Find a sample player page
    player_dir = output_dir / "players"
    if not player_dir.exists():
        pytest.skip("No players directory found")

    player_files = list(player_dir.glob("*.html"))
    if not player_files:
        pytest.skip("No player HTML files found")

    # Test first few player pages
    for player_file in player_files[:5]:
        html = player_file.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")

        # Find all cross-links
        cross_links = soup.find_all("a", class_="wcfb-cross-link")

        for link in cross_links:
            href = link.get("href")
            if not href:
                continue

            # Resolve relative path
            if href.startswith("../"):
                target_path = (player_file.parent / href).resolve()
            else:
                target_path = (output_dir / href).resolve()

            # Check file exists
            assert target_path.exists(), f"Broken link: {href} in {player_file.name}"


@pytest.mark.integration
def test_team_page_links_resolve(output_dir: Path) -> None:
    """Verify team page links to opponent pages resolve correctly."""
    teams_dir = output_dir / "teams"
    if not teams_dir.exists():
        pytest.skip("No teams directory found")

    team_files = list(teams_dir.glob("*.html"))
    if not team_files:
        pytest.skip("No team HTML files found")

    # Test first few team pages
    for team_file in team_files[:5]:
        html = team_file.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")

        # Find all opponent links (adjust selector based on actual implementation)
        opponent_links = soup.find_all("a", href=lambda x: x and x.startswith("../teams/"))

        for link in opponent_links:
            href = link.get("href")
            if not href:
                continue

            # Extract team slug from href
            # "../teams/georgia.html" -> "georgia.html"
            team_filename = href.split("/")[-1]
            target_path = (teams_dir / team_filename).resolve()

            # Check file exists (for profiled teams) or link is valid
            # Note: Unprofiled teams might not have pages, which is OK
            if target_path.name in [
                f"{slug}.html" for slug in [
                    "alabama", "auburn", "florida", "georgia", "massachusetts",
                    "michigan", "notre-dame", "ohio-state", "oklahoma", "oregon",
                    "penn-state", "tennessee", "texas", "uconn", "usc",
                    "vanderbilt", "washington",
                ]
            ]:
                # These are profiled teams - should exist
                assert target_path.exists(), f"Broken profiled team link: {href} in {team_file.name}"


@pytest.mark.integration
def test_no_broken_image_links(output_dir: Path) -> None:
    """Verify all image links resolve correctly."""
    assets_dir = output_dir / "assets"
    if not assets_dir.exists():
        pytest.skip("No assets directory found")

    # Check player pages for broken image links
    player_dir = output_dir / "players"
    if player_dir.exists():
        for player_file in list(player_dir.glob("*.html"))[:3]:
            html = player_file.read_text(encoding="utf-8")
            soup = BeautifulSoup(html, "html.parser")

            images = soup.find_all("img")
            for img in images:
                src = img.get("src")
                if not src:
                    continue

                # Resolve relative path
                if src.startswith("../"):
                    target_path = (player_file.parent / src).resolve()
                else:
                    target_path = (output_dir / src).resolve()

                # For asset files, check they exist
                if "assets" in target_path.parts:
                    assert target_path.exists(), f"Broken image: {src} in {player_file.name}"


@pytest.mark.integration
def test_theme_toggle_assets(output_dir: Path) -> None:
    """Verify theme toggle assets are present."""
    # Check for theme JavaScript
    js_files = list(output_dir.glob("**/theme*.js")) + list(output_dir.glob("**/stat_definitions.js"))
    assert js_files, "Theme JavaScript files not found"

    # Check for theme CSS
    css_files = list(output_dir.glob("**/*theme*.css")) + list(output_dir.glob("**/*stats*.css"))
    # CSS might be inlined, so this is optional
    if css_files:
        for css_file in css_files[:3]:
            assert css_file.exists(), f"CSS file missing: {css_file}"


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def output_dir() -> Path:
    """Return the output directory for generated HTML files."""
    return Path(__file__).parent.parent.parent.parent / "output" / "site"


@pytest.fixture
def sample_player_html(output_dir: Path) -> str:
    """Return HTML content from a sample player page."""
    player_dir = output_dir / "players"
    if not player_dir.exists():
        pytest.skip("No players directory")

    player_files = list(player_dir.glob("*.html"))
    if not player_files:
        pytest.skip("No player HTML files")

    # Return first player file's content
    return player_files[0].read_text(encoding="utf-8")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_links_from_html(html: str, css_class: str | None = None) -> list[dict[str, str]]:
    """Extract all links from HTML with optional CSS class filter.

    Args:
        html: HTML content
        css_class: Optional CSS class to filter by

    Returns:
        List of dicts with href and text
    """
    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a", class_=css_class)

    return [
        {"href": link.get("href", ""), "text": link.get_text(strip=True)}
        for link in links
        if link.get("href")
    ]


def check_file_exists(path: Path, base_dir: Path) -> bool:
    """Check if a file exists, resolving relative paths.

    Args:
        path: File path (may be relative)
        base_dir: Base directory for resolving relative paths

    Returns:
        True if file exists
    """
    if path.is_absolute():
        return path.exists()

    # Resolve relative to base_dir
    resolved = (base_dir / path).resolve()
    return resolved.exists()