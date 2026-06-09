"""Season-path projection math — the load-bearing core of the preview layer.

Spec: docs/specs/team-preview-implementation-plan-2026-05-26.md §2.2, §6, §1.2.

These exercise the pure projection engine with synthetic strength inputs, so the
record arithmetic and the spec's internal-consistency invariants are pinned
independent of any live data.
"""

from __future__ import annotations

import pytest

from cfb_rankings.team_preview.season_path import (
    PathConsistencyError,
    REGULAR_SEASON_GAMES,
    SeasonPathInputs,
    SeasonPathProjection,
    expected_regular_wins,
    project_season_path,
    validate_projection,
)


def _by_scenario(projections):
    return {p.scenario: p for p in projections}


# --- strength -> wins -------------------------------------------------------

def test_expected_regular_wins_is_monotonic() -> None:
    prev = -1.0
    for s in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        w = expected_regular_wins(s)
        assert w > prev, "expected wins must strictly increase with strength"
        prev = w


def test_expected_regular_wins_stays_in_range() -> None:
    assert 0.0 <= expected_regular_wins(0.0) <= REGULAR_SEASON_GAMES
    assert 0.0 <= expected_regular_wins(1.0) <= REGULAR_SEASON_GAMES


# --- elite teams can project beyond 12 games --------------------------------

def test_elite_power_team_projects_beyond_twelve_games() -> None:
    """Alabama-style: P4 conference, elite talent. Ceiling exceeds 12 games."""
    inp = SeasonPathInputs(
        slug="alabama", season_year=2026, strength=0.90,
        is_independent=False, uncertainty=0.2, cfp_eligible=True,
    )
    ceiling = _by_scenario(project_season_path(inp))["ceiling"]
    assert ceiling.final_wins + ceiling.final_losses > REGULAR_SEASON_GAMES
    assert ceiling.bowl_or_cfp_path == "national_champion"
    assert ceiling.conference_title_game is True
    assert ceiling.conference_title_result == "win"


def test_elite_independent_projects_beyond_twelve_without_ccg() -> None:
    """Notre Dame-style: elite but independent — deep CFP run, never a CCG."""
    inp = SeasonPathInputs(
        slug="notre-dame", season_year=2026, strength=0.88,
        is_independent=True, uncertainty=0.2, cfp_eligible=True,
    )
    projections = project_season_path(inp)
    ceiling = _by_scenario(projections)["ceiling"]
    assert ceiling.final_wins + ceiling.final_losses > REGULAR_SEASON_GAMES
    for p in projections:
        assert p.conference_title_game is False
        assert p.conference_title_result == "none"


# --- low-projection teams get no fabricated postseason ----------------------

def test_low_projection_team_gets_no_cfp_or_ccg_path() -> None:
    """Akron-style: low strength. No CFP, no CCG in any scenario; bowl only if
    the regular-season projection actually reaches bowl eligibility."""
    inp = SeasonPathInputs(
        slug="akron", season_year=2026, strength=0.42,
        is_independent=False, uncertainty=0.4, cfp_eligible=True,
    )
    for p in project_season_path(inp):
        assert p.conference_title_game is False
        assert not p.bowl_or_cfp_path.startswith("cfp_")
        assert p.bowl_or_cfp_path != "national_champion"
        assert p.bowl_or_cfp_path in ("none", "bowl")
        if p.bowl_or_cfp_path == "bowl":
            assert p.regular_season_wins >= 6


def test_low_signal_team_floor_has_no_postseason() -> None:
    inp = SeasonPathInputs(slug="umass", season_year=2026, strength=0.30,
                           is_independent=True, uncertainty=0.6, cfp_eligible=True)
    floor = _by_scenario(project_season_path(inp))["floor"]
    assert floor.bowl_or_cfp_path == "none"
    assert floor.postseason_wins == 0 and floor.postseason_losses == 0


# --- independence -----------------------------------------------------------

def test_independent_never_has_conference_title_game() -> None:
    for strength in (0.30, 0.60, 0.88, 0.95):
        inp = SeasonPathInputs(slug="ind", season_year=2026, strength=strength,
                               is_independent=True, cfp_eligible=True)
        for p in project_season_path(inp):
            assert p.conference_title_game is False
            assert p.conference_title_result == "none"


# --- internal consistency of the record math --------------------------------

def test_national_champion_has_zero_postseason_losses() -> None:
    inp = SeasonPathInputs(slug="elite", season_year=2026, strength=0.95,
                           is_independent=False, cfp_eligible=True)
    champ = [p for p in project_season_path(inp)
             if p.bowl_or_cfp_path == "national_champion"]
    assert champ, "an elite team should have a national-champion ceiling"
    for p in champ:
        assert p.postseason_losses == 0


def test_non_champion_cfp_path_has_exactly_one_loss() -> None:
    inp = SeasonPathInputs(slug="strong", season_year=2026, strength=0.85,
                           is_independent=False, cfp_eligible=True)
    cfp = [p for p in project_season_path(inp)
           if p.bowl_or_cfp_path.startswith("cfp_")]
    assert cfp, "a strong team should have at least one CFP-exit scenario"
    for p in cfp:
        assert p.postseason_losses == 1


def test_final_record_equals_components() -> None:
    inp = SeasonPathInputs(slug="x", season_year=2026, strength=0.86,
                           is_independent=False, cfp_eligible=True)
    for p in project_season_path(inp):
        ccg_w = 1 if p.conference_title_result == "win" else 0
        ccg_l = 1 if p.conference_title_result == "loss" else 0
        assert p.final_wins == p.regular_season_wins + ccg_w + p.postseason_wins
        assert p.final_losses == p.regular_season_losses + ccg_l + p.postseason_losses
        assert p.regular_season_wins + p.regular_season_losses == REGULAR_SEASON_GAMES


def test_floor_base_ceiling_final_wins_non_decreasing() -> None:
    for strength in (0.30, 0.55, 0.78, 0.90):
        by = _by_scenario(project_season_path(
            SeasonPathInputs(slug="t", season_year=2026, strength=strength,
                             cfp_eligible=True)))
        assert by["floor"].final_wins <= by["base"].final_wins <= by["ceiling"].final_wins


# --- the cfp-eligibility gate (no talent -> no title run) -------------------

def test_high_strength_without_talent_evidence_is_capped() -> None:
    """A recent FCS->FBS program with an inflated raw strength but no talent
    evidence must not be projected into a national-title path."""
    inp = SeasonPathInputs(slug="sam-houston", season_year=2026, strength=0.90,
                           is_independent=False, cfp_eligible=False)
    for p in project_season_path(inp):
        assert p.bowl_or_cfp_path != "national_champion"


# --- validator rejects fabricated/inconsistent rows -------------------------

def test_validate_rejects_national_champion_with_a_loss() -> None:
    bad = SeasonPathProjection(
        scenario="ceiling", regular_season_wins=12, regular_season_losses=0,
        conference_title_game=True, conference_title_result="win",
        bowl_or_cfp_path="national_champion", postseason_wins=3, postseason_losses=1,
        final_wins=16, final_losses=1,
    )
    with pytest.raises(PathConsistencyError):
        validate_projection(bad, is_independent=False)


def test_validate_rejects_independent_with_conference_title_game() -> None:
    bad = SeasonPathProjection(
        scenario="ceiling", regular_season_wins=12, regular_season_losses=0,
        conference_title_game=True, conference_title_result="win",
        bowl_or_cfp_path="bowl", postseason_wins=1, postseason_losses=0,
        final_wins=14, final_losses=0,
    )
    with pytest.raises(PathConsistencyError):
        validate_projection(bad, is_independent=True)


def test_validate_rejects_bad_final_arithmetic() -> None:
    bad = SeasonPathProjection(
        scenario="base", regular_season_wins=10, regular_season_losses=2,
        conference_title_game=False, conference_title_result="none",
        bowl_or_cfp_path="bowl", postseason_wins=1, postseason_losses=0,
        final_wins=99, final_losses=2,
    )
    with pytest.raises(PathConsistencyError):
        validate_projection(bad, is_independent=False)


def test_project_season_path_always_returns_three_valid_scenarios() -> None:
    for strength in (0.0, 0.25, 0.5, 0.75, 1.0):
        for indep in (True, False):
            for cfp_ok in (True, False):
                projections = project_season_path(SeasonPathInputs(
                    slug="t", season_year=2026, strength=strength,
                    is_independent=indep, cfp_eligible=cfp_ok, uncertainty=0.3))
                assert {p.scenario for p in projections} == {"floor", "base", "ceiling"}
                # project_season_path validates internally; reaching here means
                # every generated scenario passed its consistency checks.
