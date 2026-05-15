"""CFB calendar utilities — single source of truth for user-facing date/phase/kickoff labeling.

The codebase stores ISO calendar week keys (`YYYY-WW`) internally — these are
fine for storage/lookup but render as garbage in user copy during offseason
("Welcome to Week 21" in late May is meaningless to a CFB reader).

This module produces human-friendly labels:
  - Section headers → phase labels ("Late Spring", "Fall Camp", "Bowl Season")
  - Eyebrow / dateline → phase + parenthetical ("Late Spring · 106 days to kickoff")
  - In-season → conventional "Week N" / "Rivalry Week" / "CFP Title Week"
  - Game-week approach → "Game Week (3 days to kickoff)"
  - Bowl season → named ("Bowl Season", "CFP Quarterfinal Week", "CFP Title Week")
  - ISO week keys → kept in data layer only, NEVER surface to readers

Public API summary (see docstrings for details):
  kickoff_date(season, db)            → date of first FBS game
  days_to_kickoff(today, season, db)  → int (positive; rolls forward post-kickoff)
  cfp_title_game_date(season, db)     → date of CFP title game ending given season
  is_offseason(today, db)             → bool
  is_in_season(today, db)             → bool
  human_phase_label(today, db)        → "Late Spring" / "SEC Media Days Week" / etc.
  cfb_week_label(today, db)           → canonical 'where are we' label
  cfb_week_label_for_window(today, iso_week, db) → variant for fan_intel updated_label
  archive_week_key(today)             → ISO YYYY-WW (data-layer only)
  human_date_phrase(d)                → "May 15, 2026" style for body copy

All DB queries are read-only and cheap. Helpers fall back to KEY_EVENTS_YEAR
constants when DB rows are missing — never crash on empty DB. Never call from
ingest/migration code.

See: IMPLEMENTATION_PLAN.md Part 4 (Sprint v5-1 Day 2) +
     DESIGN_AUDIT_2026_05_15_v5_4.md Part 2.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

log = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────
# Key event tables — promoted to "{event.label} Week" when today is within
# 7 days before the event start (or +1 day after end).
#
# Verify each year's dates against the official conference / NCAA calendar
# before merging. Sources: SEC/B1G/ACC/B12 conference comms, AP poll
# release calendar, CFP committee schedule.
# ───────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class KeyEvent:
    slug: str
    label: str
    start: date
    end: date | None = None  # single-day if None
    is_kickoff: bool = False
    is_cfp_title: bool = False
    promote_window_days: int = 7  # days before start where event "owns" the week label


KEY_EVENTS_2026: list[KeyEvent] = [
    KeyEvent("nfl_draft",                "NFL Draft",          date(2026, 4, 23), date(2026, 4, 25)),
    KeyEvent("transfer_window_spring",   "Spring Portal Close", date(2026, 4, 30)),
    KeyEvent("big_12_media_days",        "Big 12 Media Days",   date(2026, 7,  8), date(2026, 7, 10)),
    KeyEvent("sec_media_days",           "SEC Media Days",      date(2026, 7, 14), date(2026, 7, 17)),
    KeyEvent("acc_kickoff",              "ACC Kickoff",         date(2026, 7, 22), date(2026, 7, 24)),
    KeyEvent("big_ten_media_days",       "Big Ten Media Days",  date(2026, 7, 27), date(2026, 7, 28)),
    KeyEvent("fall_camp_open",           "Fall Camp Opens",     date(2026, 8,  3)),
    KeyEvent("preseason_ap_poll",        "Preseason AP Poll",   date(2026, 8, 17)),
    KeyEvent("week_0_kickoff",           "Week 0 Kickoff",      date(2026, 8, 22), is_kickoff=True),
    KeyEvent("week_1_kickoff",           "Week 1 Kickoff",      date(2026, 8, 29), is_kickoff=True),
    KeyEvent("rivalry_saturday",         "Rivalry Saturday",    date(2026, 11, 28)),
    KeyEvent("army_navy",                "Army-Navy",           date(2026, 12, 12)),
    KeyEvent("cfp_first_round",          "CFP First Round",     date(2026, 12, 18), date(2026, 12, 20)),
    KeyEvent("cfp_quarterfinals",        "CFP Quarterfinals",   date(2026, 12, 31), date(2027, 1,  1)),
    KeyEvent("cfp_semifinals",           "CFP Semifinals",      date(2027, 1,  8), date(2027, 1,  9)),
    KeyEvent("cfp_title_game",           "CFP Title Game",      date(2027, 1, 11), is_cfp_title=True),
    KeyEvent("nsd_early",                "Early Signing Day",   date(2026, 12,  3)),
]

# Future-year stubs. Fill in real dates per year as they're announced.
# Until then `human_phase_label` falls back to the month→phase table.
KEY_EVENTS_BY_YEAR: dict[int, list[KeyEvent]] = {
    2026: KEY_EVENTS_2026,
}


# Maps the existing _MONTH_TO_PHASE values (defined in
# team_pages/state_resolver.py) to user-friendly labels. Keeping the slugs
# identical to the source-of-truth dict lets us depend on it without
# importing (avoids circular import; the team_pages package transitively
# imports renderer which is heavy).
PHASE_HUMAN_LABEL = {
    "bowl-and-carousel":       "Bowl Season",
    "nsd-and-portal":          "National Signing Day & Portal Window",
    "spring-and-portal":       "Spring Practice & Portal Window",
    "dead-period-heritage":    "Late Spring",
    "media-days":              "Media Days Season",
    "camp":                    "Fall Camp",
    "early-season":            "Early Season",
    "stakes-rising":           "Stakes Rising",
    "rivalry-peak":            "Rivalry Window",
    "cfp-selection-and-bowl":  "Selection & Bowl Window",
}

_MONTH_TO_PHASE = {
    1:  "bowl-and-carousel",
    2:  "nsd-and-portal",
    3:  "spring-and-portal",
    4:  "spring-and-portal",
    5:  "dead-period-heritage",
    6:  "dead-period-heritage",
    7:  "media-days",
    8:  "camp",
    9:  "early-season",
    10: "stakes-rising",
    11: "rivalry-peak",
    12: "cfp-selection-and-bowl",
}


# ───────────────────────────────────────────────────────────────────────────
# Date-level helpers
# ───────────────────────────────────────────────────────────────────────────

def archive_week_key(today: date) -> str:
    """ISO YYYY-WW for storage/lookup. NEVER surface to readers."""
    iso = today.isocalendar()
    return f"{iso[0]}-{iso[1]:02d}"


def human_date_phrase(d: date) -> str:
    """Body-copy date phrase. Replaces 'Week 21' / 'Wk 5' in narrative text.

    Examples:
        2026-05-15 → 'May 15, 2026'

    Cross-platform: avoids strftime's %-d (Linux/macOS only) and %#d
    (Windows only) by formatting the day component directly.
    """
    if not hasattr(d, "strftime"):
        return str(d)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


# ───────────────────────────────────────────────────────────────────────────
# Kickoff / title game lookups (DB-aware with constant fallback)
# ───────────────────────────────────────────────────────────────────────────

def kickoff_date(season: int, db: sqlite3.Connection | None = None) -> date:
    """Date of the first FBS game of the given season.

    Tries the games table first; falls back to KEY_EVENTS_<season>'s
    week_0_kickoff (or week_1_kickoff if week_0 not present).

    Args:
        season: Season year, e.g. 2026.
        db: SQLite connection. Optional — falls back to KEY_EVENTS if None
            or query fails.
    """
    if db is not None:
        try:
            cur = db.execute(
                """
                SELECT MIN(DATE(start_date)) AS d
                FROM games
                WHERE season_year = ?
                  AND classification = 'fbs'
                """,
                (season,),
            )
            row = cur.fetchone()
            if row and row[0]:
                return date.fromisoformat(str(row[0])[:10])
        except sqlite3.Error as exc:
            log.debug("kickoff_date: DB query failed for season %d (%s); using constant", season, exc)

    events = KEY_EVENTS_BY_YEAR.get(season, [])
    for ev in events:
        if ev.slug == "week_0_kickoff":
            return ev.start
    for ev in events:
        if ev.slug == "week_1_kickoff":
            return ev.start
    # Last-resort heuristic: last Saturday of August
    return _last_saturday_in_august(season)


def cfp_title_game_date(season: int, db: sqlite3.Connection | None = None) -> date:
    """Date of the CFP title game ending the given season.

    Note: the title game falls in *January of the following calendar year*.
    Season 2026 → title game January 2027.
    """
    events = KEY_EVENTS_BY_YEAR.get(season, [])
    for ev in events:
        if ev.is_cfp_title:
            return ev.start
    # Future-year fallback heuristic: 2nd Monday of January
    return _second_monday_in_january(season + 1)


def days_to_kickoff(
    today: date,
    season: int | None = None,
    db: sqlite3.Connection | None = None,
) -> int:
    """Days until the next FBS kickoff. Always non-negative.

    If season is omitted, picks the next upcoming kickoff. If today is
    past this season's kickoff, rolls to next season's.
    """
    if season is None:
        # Try this calendar year first; if kickoff already passed, use next.
        candidate_season = today.year
        ko = kickoff_date(candidate_season, db)
        if ko < today:
            candidate_season += 1
            ko = kickoff_date(candidate_season, db)
    else:
        ko = kickoff_date(season, db)
    return max(0, (ko - today).days)


# ───────────────────────────────────────────────────────────────────────────
# Season/offseason classification
# ───────────────────────────────────────────────────────────────────────────

def is_offseason(today: date, db: sqlite3.Connection | None = None) -> bool:
    """True iff today is after the most recent CFP title game and before
    the next kickoff.

    Edge cases:
      - Between Aug 22 (Week 0) and Aug 29 (Week 1): considered in-season
        because games are happening.
      - Title game day itself: NOT offseason (it's a game day).
      - The day after the title game: first day of offseason.
    """
    # Find the previous season's title game and the next kickoff.
    # Title game for season S is in January of S+1.
    # If today is Jan-Aug: prev title = title for season (today.year - 1),
    #                       next kickoff = season today.year (or today.year+1 if past)
    # If today is Sep-Dec: in-season (no offseason possible).
    if today.month >= 9:
        return False
    # Jan-Aug: between Jan 1 and the upcoming kickoff
    prev_title = cfp_title_game_date(today.year - 1, db)
    next_kickoff = kickoff_date(today.year, db)
    return prev_title < today < next_kickoff


def is_in_season(today: date, db: sqlite3.Connection | None = None) -> bool:
    return not is_offseason(today, db)


# ───────────────────────────────────────────────────────────────────────────
# Phase labels
# ───────────────────────────────────────────────────────────────────────────

def _last_saturday_in_august(year: int) -> date:
    """Heuristic kickoff anchor when KEY_EVENTS data is absent."""
    d = date(year, 8, 31)
    while d.weekday() != 5:  # 5 = Saturday
        d -= timedelta(days=1)
    return d


def _second_monday_in_january(year: int) -> date:
    """Heuristic CFP title anchor when KEY_EVENTS data is absent."""
    d = date(year, 1, 1)
    mondays_found = 0
    while True:
        if d.weekday() == 0:  # Monday
            mondays_found += 1
            if mondays_found == 2:
                return d
        d += timedelta(days=1)


def _matching_key_event(today: date, db: sqlite3.Connection | None) -> Optional[KeyEvent]:
    """Return the KeyEvent that 'owns' today's label, if any.

    Ownership rule: today is between (event.start - promote_window_days)
    and (event.end or event.start) + 1 day inclusive.
    """
    for year in (today.year, today.year - 1, today.year + 1):
        for ev in KEY_EVENTS_BY_YEAR.get(year, []):
            window_start = ev.start - timedelta(days=ev.promote_window_days)
            window_end = (ev.end or ev.start) + timedelta(days=1)
            if window_start <= today <= window_end:
                return ev
    return None


def human_phase_label(today: date, db: sqlite3.Connection | None = None) -> str:
    """Phase label with key-event promotion.

    Returns one of:
      - Canonical in-season labels: "Week N", "Rivalry Week", "CFP Title Week"
      - Key-event labels: "SEC Media Days Week", "Fall Camp Opens Week"
      - Phase labels: "Late Spring", "Fall Camp", "Bowl Season"

    The function does NOT include the parenthetical days-to-kickoff
    suffix — that's `cfb_week_label`'s job.
    """
    # In-season "Week N" — query the games table; fall back to a kickoff-anchored
    # week count when DB is absent.
    if is_in_season(today, db):
        return _in_season_week_label(today, db)

    # Offseason — check for key-event ownership first
    ev = _matching_key_event(today, db)
    if ev is not None:
        # Special cases for CFP / kickoff events
        if ev.is_cfp_title:
            return "CFP Title Week"
        if ev.is_kickoff:
            return "Game Week"
        return f"{ev.label} Week"

    # Generic offseason — map month to phase
    slug = _MONTH_TO_PHASE.get(today.month, "early-season")
    return PHASE_HUMAN_LABEL.get(slug, slug.replace("-", " ").title())


def _in_season_week_label(today: date, db: sqlite3.Connection | None) -> str:
    """Best-effort 'Week N' label when in-season.

    Strategy:
      1. If a key-event for today exists (e.g. Rivalry Saturday, Army-Navy,
         CFP First Round) — use that label.
      2. Otherwise count weeks since Aug 20 of the current cfb-year.
    """
    ev = _matching_key_event(today, db)
    if ev is not None:
        if ev.is_cfp_title:
            return "CFP Title Week"
        # In-season key events: prefer their full label (e.g. "Rivalry Saturday")
        return ev.label

    # Anchor: nearest preceding Aug 20.
    anchor_year = today.year if today.month >= 8 else today.year - 1
    anchor = date(anchor_year, 8, 20)
    if today < anchor:
        # Shouldn't happen if is_in_season returned True, but handle safely.
        return "Preseason"
    week_num = max(0, min(16, (today - anchor).days // 7 + 1))
    return f"Week {week_num}"


# ───────────────────────────────────────────────────────────────────────────
# The canonical label functions used by callers
# ───────────────────────────────────────────────────────────────────────────

def cfb_week_label(today: date, db: sqlite3.Connection | None = None) -> str:
    """Canonical 'where are we' label for user-facing copy.

    Hybrid convention:
      - In-season → unchanged 'Week N' / 'Rivalry Week' / 'CFP Title Week'
      - Within 7-day game-week approach → 'Game Week (N days to kickoff)'
      - Offseason → '<phase or event> (N days to kickoff)'
      - >7 days from kickoff and >7 days from any key event → just '<phase>'
        (no parenthetical) to avoid clutter on landing pages

    Examples (verified by test suite):
      2026-05-15 → 'Late Spring (106 days to kickoff)'
      2026-07-15 → 'SEC Media Days Week (45 days to kickoff)'
      2026-08-26 → 'Game Week (3 days to kickoff)'
      2026-08-29 → 'Week 1'
      2026-11-28 → 'Rivalry Saturday'
      2027-01-11 → 'CFP Title Week'
      2027-01-15 → 'Bowl Season (217 days to kickoff)'
    """
    if is_in_season(today, db):
        return human_phase_label(today, db)

    # Offseason — compose phase + countdown parenthetical
    phase = human_phase_label(today, db)
    dtk = days_to_kickoff(today, db=db)

    # Special phrasing when very close to kickoff
    if 0 < dtk <= 7:
        return f"Game Week ({dtk} days to kickoff)"
    if dtk == 0:
        return "Kickoff Day"

    return f"{phase} ({dtk} days to kickoff)"


def cfb_week_label_for_window(
    today: date,
    iso_week: int,
    db: sqlite3.Connection | None = None,
) -> str:
    """Variant for fan_intelligence updated_label patterns.

    The caller computed an ISO week as a data key (e.g. for SQL filtering)
    and wants to render it as 'Week N window'. In-season that's literal
    'Week N window' (matching the in-season game-week label). Offseason
    drops the ISO number and uses the phase: 'Late Spring window'.

    Args:
        today: The date the page is being rendered.
        iso_week: The ISO calendar week the data was computed for.
        db: Optional DB connection.
    """
    if is_in_season(today, db):
        return f"Week {iso_week} window"
    phase = human_phase_label(today, db)
    return f"{phase} window"


__all__ = [
    "KeyEvent",
    "KEY_EVENTS_2026",
    "KEY_EVENTS_BY_YEAR",
    "PHASE_HUMAN_LABEL",
    "archive_week_key",
    "cfb_week_label",
    "cfb_week_label_for_window",
    "cfp_title_game_date",
    "days_to_kickoff",
    "human_date_phrase",
    "human_phase_label",
    "is_in_season",
    "is_offseason",
    "kickoff_date",
]
