"""Tests for cfb_rankings.season_phase."""

from __future__ import annotations

from datetime import date

import pytest

from cfb_rankings.season_phase import Phase, current_phase, phase_banner


@pytest.mark.parametrize(
    "today,expected_phase,banner_must_contain",
    [
        # IN-SEASON
        (date(2025, 8, 30), Phase.IN_SEASON, "WK"),
        (date(2025, 10, 5), Phase.IN_SEASON, "2025 SEASON"),
        (date(2025, 12, 6), Phase.IN_SEASON, "WK"),

        # POSTSEASON
        (date(2025, 12, 20), Phase.POSTSEASON, "BOWL WEEK"),
        (date(2025, 12, 30), Phase.POSTSEASON, "CFP"),
        (date(2026, 1, 10), Phase.POSTSEASON, "CFP"),

        # OFFSEASON EARLY — portal
        (date(2026, 1, 20), Phase.OFFSEASON_EARLY, "PORTAL"),
        (date(2026, 2, 10), Phase.OFFSEASON_EARLY, "PORTAL"),

        # OFFSEASON EARLY — spring practice
        (date(2026, 3, 15), Phase.OFFSEASON_EARLY, "PRACTICE"),
        (date(2026, 4, 10), Phase.OFFSEASON_EARLY, "PRACTICE"),

        # OFFSEASON EARLY — pre-draft
        (date(2026, 4, 17), Phase.OFFSEASON_EARLY, "PRE-DRAFT"),
        (date(2026, 4, 20), Phase.OFFSEASON_EARLY, "PRE-DRAFT"),

        # OFFSEASON DRAFT — exact kickoff verification target
        (date(2026, 4, 23), Phase.OFFSEASON_DRAFT, "DRAFT WEEK"),
        (date(2026, 4, 24), Phase.OFFSEASON_DRAFT, "DRAFT WEEK"),
        (date(2026, 4, 25), Phase.OFFSEASON_DRAFT, "DRAFT WEEK"),

        # Post-draft
        (date(2026, 4, 29), Phase.OFFSEASON_EARLY, "COMPLETE"),
        (date(2026, 4, 30), Phase.OFFSEASON_EARLY, "COMPLETE"),

        # OFFSEASON SUMMER
        (date(2026, 5, 1), Phase.OFFSEASON_SUMMER, "SUMMER"),
        (date(2026, 6, 15), Phase.OFFSEASON_SUMMER, "COMMITMENT"),
        (date(2026, 7, 1), Phase.OFFSEASON_SUMMER, "COMMITMENT"),

        # OFFSEASON PRESEASON
        (date(2026, 7, 10), Phase.OFFSEASON_PRESEASON, "OUTLOOK"),
        (date(2026, 8, 1), Phase.OFFSEASON_PRESEASON, "OUTLOOK"),
        (date(2026, 8, 14), Phase.OFFSEASON_PRESEASON, "OUTLOOK"),

        # PRESEASON CAMP
        (date(2026, 8, 15), Phase.PRESEASON_CAMP, "FALL CAMP"),
        (date(2026, 8, 19), Phase.PRESEASON_CAMP, "FALL CAMP"),

        # Back to IN-SEASON for the next year
        (date(2026, 8, 30), Phase.IN_SEASON, "WK"),
    ],
)
def test_phase_boundaries(today: date, expected_phase: Phase, banner_must_contain: str) -> None:
    result = current_phase(today)
    assert result.phase == expected_phase, f"{today} expected {expected_phase}, got {result.phase} (banner={result.banner_text!r})"
    assert banner_must_contain in result.banner_text, (
        f"{today}: banner {result.banner_text!r} missing {banner_must_contain!r}"
    )


def test_task_spec_verification_banner() -> None:
    """Kickoff TASK 7.1 spec: banner on 2026-04-23 should read
    'OFFSEASON · SPRING 2026 · DRAFT WEEK'."""
    p = current_phase(date(2026, 4, 23))
    assert p.banner_text == "OFFSEASON · SPRING 2026 · DRAFT WEEK"


def test_season_year_rollover() -> None:
    # Aug-Dec of 2025 → season 2025.
    assert current_phase(date(2025, 8, 25)).season_year == 2025
    assert current_phase(date(2025, 12, 5)).season_year == 2025
    # Bowl/CFP of the 2025 season play in Jan 2026, still "season 2025".
    assert current_phase(date(2026, 1, 5)).season_year == 2025
    # From Aug 2026 onward → season 2026.
    assert current_phase(date(2026, 8, 25)).season_year == 2026


def test_week_increments_in_season() -> None:
    w1 = current_phase(date(2025, 8, 30)).sub_phase
    w6 = current_phase(date(2025, 10, 5)).sub_phase
    assert w1.startswith("week_")
    assert w6.startswith("week_")
    # week_1 vs week_6 — later date => higher week.
    assert int(w1.split("_")[1]) < int(w6.split("_")[1])


def test_phase_banner_accessor() -> None:
    p = current_phase(date(2026, 4, 23))
    assert phase_banner(p) == p.banner_text
