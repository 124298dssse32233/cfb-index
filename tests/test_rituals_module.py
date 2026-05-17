"""Tests for cfb_rankings.team_pages.rituals_module (Sprint v5-8.5).

Locked spec: docs/mockups/mockup_02_team_alabama_v2.html (rituals strip).
Profile data shipped in master commit 95e7d5dd52 for all 17 profiled teams.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from cfb_rankings.team_pages.profile_loader import Profile, load_profile
from cfb_rankings.team_pages.rituals_module import (
    _make_monogram,
    _shorten_when,
    render_cultural_anchors,
    render_rituals_strip,
    render_visual_identity_chip,
)


# ---------------------------------------------------------------------------
# Pure unit tests — monogram + when helpers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name, expected", [
    ("Rammer Jammer", "RJ"),
    ("Yea Alabama (Fight Song)", "YA"),
    ("Elephant Walk", "EW"),
    ("Pregame Flyover", "PF"),
    ("Million Dollar Band Halftime", "MD"),
    ("The Walk of Champions", "WC"),  # "The" + "of" dropped
    ("Anchor Down Call-and-Response", "AD"),
    ("Vol Navy", "VN"),
    ("Howard's Rock", "HR"),
])
def test_monogram_extracts_two_letters(name: str, expected: str) -> None:
    assert _make_monogram(name) == expected


@pytest.mark.parametrize("when, expected", [
    ("kickoff + after every score", "kickoff"),
    ("After victory; last possession of opponent", "victory"),
    ("Team entrance", "entrance"),
    ("Halftime, all home games", "halftime"),
    ("End of national anthem, major games", "anthem"),
    ("Pregame Flyover", "pregame"),
])
def test_shorten_when_extracts_keyword(when: str, expected: str) -> None:
    assert _shorten_when(when.lower()) == expected


def test_shorten_when_caps_arbitrary_at_18_chars() -> None:
    long = "some very long descriptive when string that exceeds the limit"
    out = _shorten_when(long)
    assert len(out) <= 18


# ---------------------------------------------------------------------------
# render_rituals_strip — uses real profile YAML from disk
# ---------------------------------------------------------------------------

def _fake_profile(slug: str, frontmatter: dict[str, Any]) -> Profile:
    from pathlib import Path
    return Profile(
        slug=slug,
        team_id=frontmatter.get("team_id"),
        program_tier=int(frontmatter.get("program_tier", 5) or 5),
        voice_register=frontmatter.get("voice_register", ""),
        tonal_template=frontmatter.get("tonal_template", ""),
        identity_phrase=frontmatter.get("identity_phrase", ""),
        mantra=frontmatter.get("mantra", ""),
        frontmatter=frontmatter,
        sections={},
        source_path=Path(f"profiles/{slug}.md"),
    )


def test_alabama_rituals_strip_renders_5_cards() -> None:
    """Alabama profile ships with 5 real rituals (proof-of-concept)."""
    profile = load_profile("alabama")
    html = render_rituals_strip(profile)
    assert 'class="rituals program-section"' in html
    assert 'class="rituals-track"' in html
    # Exactly 5 ritual cards
    assert html.count('class="ritual-card"') == 5
    # Each of the 5 ritual names must appear (verbatim, escaped if needed)
    for expected in ("Rammer Jammer", "Yea Alabama", "Elephant Walk",
                     "Pregame Flyover", "Million Dollar Band"):
        assert expected in html, f"missing ritual: {expected}"


def test_alabama_rituals_strip_includes_since_years() -> None:
    profile = load_profile("alabama")
    html = render_rituals_strip(profile)
    for year in (1970, 1926, 1981, 2003, 1929):
        assert f"since {year}" in html


def test_alabama_rituals_strip_carries_monograms() -> None:
    profile = load_profile("alabama")
    html = render_rituals_strip(profile)
    # The mockup-locked monograms
    for mono in ("RJ", "YA", "EW", "PF", "MD"):
        assert f">{mono}<" in html


def test_empty_rituals_returns_empty_string() -> None:
    """Profile without rituals → empty string. Caller decides empty-state."""
    p = _fake_profile("test", {"team_id": 1, "program_tier": 5})
    assert render_rituals_strip(p) == ""


def test_rituals_with_no_name_field_dropped() -> None:
    """Defensive: ritual entries missing 'name' are filtered out."""
    p = _fake_profile("test", {
        "team_id": 1,
        "program_tier": 1,
        "rituals": [
            {"started_year": 2000},  # missing name → dropped
            {"name": "Real Ritual", "started_year": 2010},
        ],
    })
    html = render_rituals_strip(p)
    assert html.count('class="ritual-card"') == 1
    assert "Real Ritual" in html


def test_rituals_capped_at_5_cards() -> None:
    """If a profile has 7 rituals, only the first 5 render."""
    p = _fake_profile("test", {
        "team_id": 1,
        "program_tier": 1,
        "rituals": [{"name": f"Ritual {i}", "started_year": 1900 + i}
                    for i in range(7)],
    })
    html = render_rituals_strip(p)
    assert html.count('class="ritual-card"') == 5


def test_rituals_html_escapes_user_content() -> None:
    """XSS defense — ritual name/description are escaped."""
    p = _fake_profile("test", {
        "team_id": 1,
        "program_tier": 1,
        "rituals": [{
            "name": "<script>x</script>",
            "started_year": 2000,
            "description": "<img onerror=x>",
        }],
    })
    html = render_rituals_strip(p)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<img" not in html or "&lt;img" in html


def test_rituals_tier_intro_varies() -> None:
    """Different tiers get different intro copy."""
    base_ritual = {"name": "X", "started_year": 2000}
    p1 = _fake_profile("a", {"team_id": 1, "program_tier": 1,
                              "rituals": [base_ritual]})
    p5 = _fake_profile("b", {"team_id": 2, "program_tier": 5,
                              "rituals": [base_ritual]})
    html1 = render_rituals_strip(p1)
    html5 = render_rituals_strip(p5)
    assert html1 != html5


# ---------------------------------------------------------------------------
# render_cultural_anchors
# ---------------------------------------------------------------------------

def test_alabama_cultural_anchors_render() -> None:
    profile = load_profile("alabama")
    html = render_cultural_anchors(profile)
    assert 'class="cultural-anchors"' in html
    assert "Alabama is what college football looks like" in html
    assert "Process-Believer" in html


def test_cultural_anchors_empty_when_absent() -> None:
    p = _fake_profile("test", {"team_id": 1, "program_tier": 5})
    assert render_cultural_anchors(p) == ""


def test_cultural_anchors_empty_when_one_sentence_missing() -> None:
    p = _fake_profile("test", {
        "team_id": 1,
        "program_tier": 5,
        "cultural_anchors": {
            # No one_sentence — block is meaningless without the lede
            "fan_archetype_dominant": "X",
        },
    })
    assert render_cultural_anchors(p) == ""


# ---------------------------------------------------------------------------
# render_visual_identity_chip
# ---------------------------------------------------------------------------

def test_alabama_visual_identity_chip_renders() -> None:
    profile = load_profile("alabama")
    html = render_visual_identity_chip(profile)
    assert "alternating-3-stripe-crimson-white" in html
    assert "crimson-cream-houndstooth-grey" in html


def test_visual_identity_chip_empty_when_absent() -> None:
    p = _fake_profile("test", {"team_id": 1, "program_tier": 5})
    assert render_visual_identity_chip(p) == ""


# ---------------------------------------------------------------------------
# Coverage across all 17 profiled teams (smoke test the YAML data shape)
# ---------------------------------------------------------------------------

ALL_PROFILED = [
    "alabama", "auburn", "florida", "georgia", "massachusetts", "michigan",
    "notre-dame", "ohio-state", "oklahoma", "oregon", "penn-state",
    "tennessee", "texas", "uconn", "usc", "vanderbilt", "washington",
]


@pytest.mark.parametrize("slug", ALL_PROFILED)
def test_every_profile_loads_without_crashing(slug: str) -> None:
    """Defensive: every profiled team's YAML parses + the renderer
    handles whatever shape it produces (empty or populated)."""
    profile = load_profile(slug)
    # Both calls must NOT raise — empty string is the worst case
    rituals_html = render_rituals_strip(profile)
    anchors_html = render_cultural_anchors(profile)
    vi_html = render_visual_identity_chip(profile)
    assert isinstance(rituals_html, str)
    assert isinstance(anchors_html, str)
    assert isinstance(vi_html, str)


@pytest.mark.parametrize("slug", ALL_PROFILED)
def test_every_profile_has_rituals_after_master_commit_95e7d5dd52(slug: str) -> None:
    """Master commit 95e7d5dd52 added rituals YAML for all 17 teams."""
    profile = load_profile(slug)
    rituals = profile.frontmatter.get("rituals")
    assert rituals, f"{slug}: rituals key missing or empty"
    assert isinstance(rituals, list)
    assert len(rituals) >= 3, f"{slug}: needs ≥3 rituals (got {len(rituals)})"
    # Each ritual must have a name
    for i, r in enumerate(rituals):
        assert isinstance(r, dict), f"{slug}: rituals[{i}] not a dict"
        assert r.get("name"), f"{slug}: rituals[{i}] missing name"
