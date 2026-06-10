"""Pin the canonical week resolution against the live DB's ground truth.

The whole Phase-2 fix hinges on resolve_week() reproducing the (season_year,
week) pair that producers ALREADY wrote: the live DB's newest
conversation_document_targets / team_week_conversation_features key is
(2025, 41) with week_start 2026-06-08. If this drifts, the daily run orphans
the existing backlog.
"""

from __future__ import annotations

from datetime import date

from cfb_rankings.common.week import resolve_week


def test_current_offseason_week_matches_db_ground_truth() -> None:
    # Any day in the Mon 2026-06-08 .. Sun 2026-06-14 week -> (2025, 41).
    for d in ("2026-06-08", "2026-06-09", "2026-06-11", "2026-06-14"):
        wk = resolve_week(d)
        assert wk.season_year == 2025, (d, wk)
        assert wk.week == 41, (d, wk)
        assert wk.week_start == "2026-06-08", (d, wk)
        assert wk.iso_key == "2025-41", (d, wk)
        assert wk.in_season is False, (d, wk)


def test_monday_determined_no_midweek_flip() -> None:
    # Every weekday of one week resolves identically (the property that lets the
    # mood path, handed the Monday, line up with same-run features).
    keys = {resolve_week(d).iso_key
            for d in ("2025-09-01", "2025-09-02", "2025-09-05", "2025-09-07")}
    assert len(keys) == 1, keys


def test_in_season_gate_matches_legacy() -> None:
    assert resolve_week("2025-09-15").in_season is True   # Sep -> in season
    assert resolve_week("2026-01-10").in_season is True   # early Jan -> in season
    assert resolve_week("2026-01-25").in_season is False  # late Jan -> offseason
    assert resolve_week("2026-06-09").in_season is False  # Jun -> offseason


def test_season_rollover_is_monotonic_text() -> None:
    # Late-offseason key < next-season opener key, lexically (cohort MAX(week)).
    june = resolve_week("2026-06-29").iso_key      # 2025 season tail
    july = resolve_week("2026-07-06").iso_key      # 2026 season, week 1
    assert july > june, (june, july)
    assert resolve_week("2026-07-06").season_year == 2026
    assert resolve_week("2026-07-06").week == 1


def test_iso_key_round_trips_through_parse() -> None:
    from cfb_rankings.cohorts.aggregate import parse_week_key

    wk = resolve_week("2026-06-09")
    assert parse_week_key(wk.iso_key) == (wk.season_year, wk.week)
