"""Canonical week resolution for the daily pipeline.

ONE source of truth for "what (season_year, week) is right now?" so producers
(reddit collector, team/player taggers, feature builder) and consumers (cohort,
mood, player-mood aggregators) can never disagree again.

Background — the silent-zero bug this kills
-------------------------------------------
Before this helper, ``daily_ingest.ps1`` derived three *different* week
vocabularies from the same clock:

* ``$SeasonWeek``  = season-week integer (e.g. 41) -> producers + features
* ``$IsoWeekKey``  = ISO week  "2026-24"            -> cohort + player-mood
* ``$PrevMonday``  = Monday date "2026-06-08"        -> mood / rivalry / lexicon

Producers stamped ``conversation_document_targets`` with ``(season_year=2025,
week=41)`` while cohort/player aggregators queried ``(2026, 24)`` -> 0 rows, and
mood mapped the Monday through a frozen ``offseason_week_map`` -> ``ValueError``.
Everything below makes all three derive from the *same* pair.

Canonical key
-------------
The **season-week integer** -- the value the ``games`` table and the reddit
collector already use. ``resolve_week`` is fully *Monday-determined*: every day
in a Mon-Sun week resolves to the SAME ``(season_year, week)``, so the
mood path (which is handed the week's Monday) and the feature path (handed the
run's "today") can't drift by a day across the Aug-26 anchor boundary.

``iso_key`` is ``f"{season_year}-{week:02d}"`` (e.g. ``"2025-41"``) -- note the
components are the season pair, NOT the calendar-ISO pair. ``parse_week_key``
splits it straight back to ``(2025, 41)``. The zero-padded, season-prefixed form
also keeps ``MAX(week)`` (the cohort reader) monotonic across the new-season
rollover ("2026-01" > "2025-52").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

# College-football season anchor. Season N's clock starts the Tue of week 0
# (Aug 26 is the conventional "week 0" Tuesday the legacy PS derivation used);
# weeks count forward from there and keep counting through the offseason until
# the next season's anchor, so e.g. June 2026 is week ~41 of the 2025 season.
SEASON_START_MONTH = 8
SEASON_START_DAY = 26


@dataclass(frozen=True)
class WeekKey:
    """Resolved week identity. All fields describe the SAME week."""

    season_year: int   # CFB season year (2025 for any date Jul 2025 - Jun 2026)
    week: int          # season-week integer, Monday-aligned, >= 1
    week_start: str    # Monday of the week, "YYYY-MM-DD"
    iso_key: str       # "f{season_year}-{week:02d}" -> "2025-41"
    in_season: bool    # Aug 1 - Jan 20 window (matches legacy $IsInSeason)

    def as_dict(self) -> dict[str, object]:
        return {
            "season_year": self.season_year,
            "week": self.week,
            "week_start": self.week_start,
            "iso_key": self.iso_key,
            "in_season": self.in_season,
        }


def _coerce_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    # Accept "YYYY-MM-DD" or a full ISO timestamp; take the date head.
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def resolve_week(as_of: date | datetime | str | None = None) -> WeekKey:
    """Resolve the canonical week for ``as_of`` (defaults to today).

    Monday-determined: ``resolve_week(any_day)`` and
    ``resolve_week(that_week's_monday)`` return identical season_year/week/
    iso_key, which is what lets the mood path (handed the Monday) line up with
    the feature path (handed the run date).
    """
    today = _coerce_date(as_of) if as_of is not None else date.today()
    monday = today - timedelta(days=today.weekday())  # Mon=0 .. Sun=6

    # Season year + week are derived from the *Monday* so the whole calendar
    # week carries one label (no mid-week flip across the Aug-26 anchor). A
    # Monday in Jul-Dec belongs to that calendar year's season; Jan-Jun belongs
    # to the prior year's season -- matching the legacy $CurSeason rule.
    season_year = monday.year if monday.month >= 7 else monday.year - 1

    season_start = date(season_year, SEASON_START_MONTH, SEASON_START_DAY)
    week = max(1, (monday - season_start).days // 7 + 1)

    # in_season tracks the raw date (not the Monday) to exactly match the legacy
    # $IsInSeason gate that toggles CFBD ingest / model runs.
    in_season = (today.month >= 8) or (today.month == 1 and today.day <= 20)

    return WeekKey(
        season_year=season_year,
        week=week,
        week_start=monday.isoformat(),
        iso_key=f"{season_year}-{week:02d}",
        in_season=in_season,
    )


__all__ = ["WeekKey", "resolve_week", "SEASON_START_MONTH", "SEASON_START_DAY"]
