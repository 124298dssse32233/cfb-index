"""Regression test for the fanbase-archetype percentile fix (2026-05-28).

Bug: ``classify_all_fanbases`` ranked every team against the full multi-level
power-ratings pool (FBS + FCS + DII + DIII, ~707 teams). FBS teams cluster at
the top of that pool, so nearly every FBS team landed at percentile >=0.80 and
the classifier collapsed onto the ``quiet-professional`` fallback. The fix ranks
each team only against peers at its own ``level_code``.
"""
from __future__ import annotations

from cfb_rankings.ingest.archetypes import _percentiles_within_level


def test_percentiles_ranked_within_level_not_cross_level() -> None:
    # 4 FBS teams + 6 FCS teams. FCS power ratings are all *higher* numerically
    # here to make the cross-level bug obvious: under the old cross-level rank,
    # the FBS teams would sit at the bottom; under per-level rank each cohort
    # spans the full 0..1 range independently.
    rows = [
        {"team_id": 1, "power_rating": 10.0, "level_code": "FBS"},
        {"team_id": 2, "power_rating": 20.0, "level_code": "FBS"},
        {"team_id": 3, "power_rating": 30.0, "level_code": "FBS"},
        {"team_id": 4, "power_rating": 40.0, "level_code": "FBS"},
        {"team_id": 11, "power_rating": 100.0, "level_code": "FCS"},
        {"team_id": 12, "power_rating": 110.0, "level_code": "FCS"},
        {"team_id": 13, "power_rating": 120.0, "level_code": "FCS"},
        {"team_id": 14, "power_rating": 130.0, "level_code": "FCS"},
        {"team_id": 15, "power_rating": 140.0, "level_code": "FCS"},
        {"team_id": 16, "power_rating": 150.0, "level_code": "FCS"},
    ]
    pct = _percentiles_within_level(rows, "power_rating")

    # Each level spans the full 0..1 range — top of its own cohort is 1.0,
    # bottom is 0.0 — regardless of the other level's absolute numbers.
    assert pct[1] == 0.0          # weakest FBS
    assert pct[4] == 1.0          # strongest FBS
    assert pct[11] == 0.0         # weakest FCS
    assert pct[16] == 1.0         # strongest FCS

    # The strongest FBS team must NOT be dragged down just because every FCS
    # rating is numerically larger (the old cross-level bug).
    assert pct[4] > pct[1]

    # A mid FBS team sits in the middle of its OWN cohort, not the bottom of
    # the pooled 10-team list (which would have been ~0.33).
    assert abs(pct[3] - (2 / 3)) < 1e-9


def test_single_team_level_does_not_divide_by_zero() -> None:
    # A lone team in its level must not divide-by-zero. rank 0 / max(1, 0) = 0.0
    # — deterministic and crash-free (the exact value is moot for a 1-team cohort).
    rows = [{"team_id": 99, "power_rating": 5.0, "level_code": "DIII"}]
    pct = _percentiles_within_level(rows, "power_rating")
    assert pct[99] == 0.0
