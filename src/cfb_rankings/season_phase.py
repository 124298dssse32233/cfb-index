"""Season-phase detection — Autopilot v1 TASK 7.1.

Returns the current CFB calendar phase from today's date. Every player
page, team page, and hub page reads this to decide which modules to
render, what banner copy to show, and how to label retrospective vs
forward-looking content.

Spec: PLAYER_PAGE_SEASON_PHASE_DESIGN.md §2 + §6.

Public API:
    current_phase(today: date = None) -> SeasonPhase
    phase_banner(phase: SeasonPhase) -> str

Phase boundaries are approximate — CFB dates vary year to year, but the
day-of-year boundaries are stable within a few days, which is the right
granularity for this system.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class Phase(str, Enum):
    IN_SEASON = "IN_SEASON"
    POSTSEASON = "POSTSEASON"
    OFFSEASON_EARLY = "OFFSEASON_EARLY"
    OFFSEASON_DRAFT = "OFFSEASON_DRAFT"
    OFFSEASON_SUMMER = "OFFSEASON_SUMMER"
    OFFSEASON_PRESEASON = "OFFSEASON_PRESEASON"
    PRESEASON_CAMP = "PRESEASON_CAMP"


@dataclass(frozen=True)
class SeasonPhase:
    phase: Phase
    sub_phase: str                 # e.g. "bowl_week", "pre_draft", "draft_week"
    season_year: int               # the CFB season this phase BELONGS to
                                   # (the 2025 season covers Aug 2025 → mid-Jan 2026)
    forward_season_year: int       # the next season we're building toward (e.g. 2026 in offseason)
    today: date
    banner_text: str


def _cfb_season_year(today: date) -> int:
    """Return the CFB "season of record" for a given date.

    Aug-onward belongs to that calendar year's season.
    Jan/Feb/etc. of the next year still belong to the PRIOR season
    (bowl games + CFP for the 2025 season are played in Jan 2026).
    """
    if today.month >= 8:
        return today.year
    return today.year - 1


def _week_of_season(today: date, season_year: int) -> int:
    """Approximate week-of-CFB-season. Week 1 ≈ last Sat of Aug."""
    anchor = date(season_year, 8, 20)
    if today < anchor:
        return 0
    delta = (today - anchor).days
    return max(1, min(17, delta // 7 + 1))


def _in_draft_week(today: date) -> bool:
    """NFL Draft runs the last Thursday-Saturday of April (approx).

    Treat Apr 22 → Apr 28 as "draft week" regardless of exact Thursday.
    """
    if today.month != 4:
        return False
    return 22 <= today.day <= 28


def _month_name(today: date) -> str:
    return today.strftime("%B").upper()


def current_phase(today: date | None = None) -> SeasonPhase:
    """Resolve today's SeasonPhase.

    Phase boundaries (approximate, in day-of-year space):
        Aug 20 → Dec 7  : IN_SEASON
        Dec 8 → Jan 13  : POSTSEASON   (bowl week early; CFP late)
        Jan 14 → Apr 14 : OFFSEASON_EARLY (portal + spring practice)
        Apr 15 → Apr 21 : OFFSEASON_EARLY sub_phase='pre_draft'
        Apr 22 → Apr 28 : OFFSEASON_DRAFT (NFL draft)
        Apr 29 → Apr 30 : OFFSEASON_EARLY sub_phase='post_draft'
        May  1 → Jul 9  : OFFSEASON_SUMMER
        Jul 10 → Aug 14 : OFFSEASON_PRESEASON
        Aug 15 → Aug 19 : PRESEASON_CAMP
    """
    if today is None:
        today = date.today()

    season_year = _cfb_season_year(today)
    # Forward season_year: the one fans are building toward.
    # In Jan-Jul the forward year is the calendar year.
    # In Aug-Dec the forward year is the current calendar year (in-season).
    if today.month >= 8:
        forward = today.year
    else:
        forward = today.year

    phase: Phase
    sub_phase: str
    banner: str
    m, d = today.month, today.day

    if (m == 8 and d >= 20) or (m in (9, 10, 11)) or (m == 12 and d <= 7):
        # IN-SEASON
        week = _week_of_season(today, season_year)
        phase = Phase.IN_SEASON
        sub_phase = f"week_{week}"
        banner = f"WK {week} · {season_year} SEASON"

    elif (m == 12 and d >= 8) or (m == 1 and d <= 13):
        phase = Phase.POSTSEASON
        if m == 12 and d <= 20:
            sub_phase = "bowl_week"
            banner = f"POSTSEASON · {season_year} · BOWL WEEK"
        elif (m == 12 and d >= 21) or (m == 1 and d <= 6):
            sub_phase = "cfp_quarterfinal"
            banner = f"POSTSEASON · {season_year} · CFP QUARTERFINAL"
        else:
            sub_phase = "cfp_semifinal_championship"
            banner = f"POSTSEASON · {season_year} · CFP SEMIFINAL/CHAMPIONSHIP"

    elif (m == 1 and d >= 14) or (m == 2) or (m == 3):
        phase = Phase.OFFSEASON_EARLY
        if m == 1 or m == 2:
            sub_phase = "portal_window"
            banner = f"OFFSEASON · {_month_name(today)} {today.year} · PORTAL WINDOW OPEN"
        else:
            sub_phase = "spring_practice"
            banner = f"OFFSEASON · SPRING {today.year} · PRACTICE ACTIVE"

    elif m == 4 and d <= 14:
        phase = Phase.OFFSEASON_EARLY
        sub_phase = "spring_practice"
        banner = f"OFFSEASON · SPRING {today.year} · PRACTICE ACTIVE"

    elif m == 4 and 15 <= d <= 21:
        phase = Phase.OFFSEASON_EARLY
        sub_phase = "pre_draft"
        banner = f"OFFSEASON · SPRING {today.year} · PRE-DRAFT"

    elif m == 4 and _in_draft_week(today):
        phase = Phase.OFFSEASON_DRAFT
        sub_phase = "draft_week"
        # Task spec verification expects this exact banner shape on Apr 23:
        # "OFFSEASON · SPRING 2026 · DRAFT WEEK".
        banner = f"OFFSEASON · SPRING {today.year} · DRAFT WEEK"

    elif m == 4 and d >= 29:
        phase = Phase.OFFSEASON_EARLY
        sub_phase = "post_draft"
        banner = f"OFFSEASON · {today.year} NFL DRAFT · COMPLETE"

    elif m == 5 or m == 6 or (m == 7 and d <= 9):
        phase = Phase.OFFSEASON_SUMMER
        sub_phase = "commitment_season"
        banner = f"OFFSEASON · SUMMER {today.year} · COMMITMENT SEASON"

    elif (m == 7 and d >= 10) or (m == 8 and d <= 14):
        phase = Phase.OFFSEASON_PRESEASON
        sub_phase = "outlook_window"
        banner = f"PRESEASON · {today.year} · OUTLOOK WINDOW"

    elif m == 8 and 15 <= d <= 19:
        phase = Phase.PRESEASON_CAMP
        sub_phase = "fall_camp"
        banner = f"PRESEASON · {today.year} · FALL CAMP OPEN"

    else:
        # Fallback — should not fire. Safe generic banner.
        phase = Phase.OFFSEASON_EARLY
        sub_phase = "unclassified"
        banner = f"OFFSEASON · {today.year}"

    return SeasonPhase(
        phase=phase,
        sub_phase=sub_phase,
        season_year=season_year,
        forward_season_year=forward,
        today=today,
        banner_text=banner,
    )


def phase_banner(phase: SeasonPhase) -> str:
    """Convenience accessor — callers can read phase.banner_text directly."""
    return phase.banner_text
