"""Tests for the WS-07 CFP-era page (data assembly + renderer).

Seeds a synthetic 12-season program (alpha) inside a 9-team within-year cohort
so the percentile math is meaningful, plus a couple of postseason games (one
title win, one title loss), a coach change, and a handful of NFL draftees.
Asserts the three-act bucketing, the stat sheet, defining-game ranking, and
that the renderer emits the expected structural sections. A second short
program exercises the MIN_SEASONS guard (returns None).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.era_pages import build_era_summary, render_era_page
from cfb_rankings.era_pages.data import ACTS
from cfb_rankings.migrations import apply_runtime_migrations

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCHEMA = REPO_ROOT / "research" / "cfb-data-schema-sqlite.sql"

_SEASONS = tuple(range(2014, 2026))  # 12 CFP-era seasons
_FILLERS = list(range(11, 19))       # 8 filler teams -> 9-team cohort/year


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(f"sqlite:///{tmp_path / 'era.db'}")
    database.apply_sql_file(BASE_SCHEMA)
    apply_runtime_migrations(database)
    _seed(database)
    return database


def _power(pid: int, run_id: int, team_id: int, season: int, rating: float) -> dict:
    return {
        "power_rating_weekly_id": pid, "model_run_id": run_id, "team_id": team_id,
        "season_year": season, "week": 15, "power_rating": rating,
        "offense_rating": 0.0, "defense_rating": 0.0,
        "special_teams_rating": 0.0, "tempo_rating": 0.0,
    }


def _seed(db: Database) -> None:
    db.upsert_many("levels", [{"level_code": "FBS", "level_name": "FBS", "sort_order": 1}],
                   conflict_columns=["level_code"])
    db.upsert_many("conferences",
                   [{"conference_id": 1, "conference_name": "Test Conf", "level_code": "FBS"}],
                   conflict_columns=["conference_id"])
    db.upsert_many("seasons", [{"season_year": y} for y in _SEASONS],
                   conflict_columns=["season_year"])
    db.upsert_many("model_runs",
                   [{"model_run_id": y, "model_name": "t", "model_version": "v1",
                     "season_year": y, "data_cutoff_utc": f"{y}-12-01T00:00:00Z"}
                    for y in _SEASONS],
                   conflict_columns=["model_run_id"])

    teams = [{"team_id": 1, "canonical_name": "Alpha", "slug": "alpha",
              "level_code": "FBS", "current_conference_id": 1},
             {"team_id": 2, "canonical_name": "Bravo", "slug": "bravo",
              "level_code": "FBS", "current_conference_id": 1}]
    for tid in _FILLERS:
        teams.append({"team_id": tid, "canonical_name": f"Filler{tid}",
                      "slug": f"f{tid}", "level_code": "FBS", "current_conference_id": 1})
    db.upsert_many("teams", teams, conflict_columns=["team_id"])

    # alpha sits at the top of the cohort every year -> ~100th percentile.
    powers, pid = [], 0
    for yr in _SEASONS:
        pid += 1
        powers.append(_power(pid, yr, 1, yr, 100.0))
        for j, tid in enumerate(_FILLERS):
            pid += 1
            powers.append(_power(pid, yr, tid, yr, 10.0 + j))
    db.upsert_many("power_ratings_weekly", powers,
                   conflict_columns=["power_rating_weekly_id"])

    # Uniform game-row shape so upsert_many (which derives columns from row[0])
    # never drops the postseason notes field.
    def _game(gid: int, yr: int, stype: str, wk: int, h: int, a: int,
              hp: int, ap: int, notes: str | None = None) -> dict:
        return {"game_id": gid, "season_year": yr, "season_type": stype,
                "week": wk, "status": "Final", "home_team_id": h, "away_team_id": a,
                "home_points": hp, "away_points": ap, "notes": notes}

    # 12 regular-season wins + 1 loss each year (a clean 12-1 baseline).
    games, gid = [], 0
    for yr in _SEASONS:
        for k in range(12):
            gid += 1
            games.append(_game(gid, yr, "regular", k + 1, 1, 11, 30, 10))
        gid += 1
        games.append(_game(gid, yr, "regular", 13, 12, 1, 24, 21))

    # Two postseason title games: 2017 win, 2021 loss (both vs Bravo).
    gid += 1
    games.append(_game(gid, 2017, "postseason", 16, 1, 2, 35, 28,
                       "CFP National Championship Presented By AT&T"))
    gid += 1
    games.append(_game(gid, 2021, "postseason", 16, 2, 1, 33, 18,
                       "CFP National Championship"))
    db.upsert_many("games", games, conflict_columns=["game_id"])

    # Coach change: Coach A 2014-2020, Coach B 2021-2025.
    ts = []
    for yr in _SEASONS:
        ts.append({"team_id": 1, "season_year": yr, "level_code": "FBS",
                   "head_coach": "Coach A" if yr <= 2020 else "Coach B"})
    db.upsert_many("team_seasons", ts, conflict_columns=["team_id", "season_year"])

    # NFL draftees: spring after 2018 (2 from the 2018 roster) and after 2022 (3).
    def _d(did: int, yr: int, name: str, rnd: int, pick: int, overall: int) -> dict:
        return {"player_nfl_draft_id": did, "draft_year": yr, "college_team_id": 1,
                "player_name": name, "round": rnd, "pick": pick, "overall": overall,
                "nfl_team": "Test NFL"}

    draft = [
        _d(1, 2019, "A", 1, 1, 1), _d(2, 2019, "B", 1, 2, 2),
        _d(3, 2023, "C", 1, 1, 1), _d(4, 2023, "D", 2, 1, 33),
        _d(5, 2023, "E", 3, 1, 65),
    ]
    db.upsert_many("player_nfl_draft", draft, conflict_columns=["player_nfl_draft_id"])


def test_summary_assembles_full_era(db: Database) -> None:
    s = build_era_summary(db, "alpha", end_season=2025)
    assert s is not None
    assert s.program_name == "Alpha"
    assert s.conference == "Test Conf"
    assert s.year_start == 2014 and s.year_end == 2025
    assert len(s.seasons) == 12
    # 3 acts: founding / transition / expansion all populated.
    assert [a.key for a in s.acts] == [a.key for a in ACTS]


def test_stat_sheet_values(db: Database) -> None:
    ss = build_era_summary(db, "alpha").stat_sheet
    assert ss["seasons"] == 12
    # 12-1 regular each year (144-12) + 2017 title win + 2021 title loss.
    assert ss["record"] == (145, 13)
    assert ss["titles"] == 1                  # one title win (2017)
    assert ss["title_games"] == 2             # plus one title loss (2021)
    assert ss["nfl_draftees"] == 5
    # Top of a 9-team cohort under the midrank definition: 100*(8+0.5)/9.
    top_pct = 100.0 * 8.5 / 9.0
    assert ss["best_season_pct"] == pytest.approx(top_pct)
    assert ss["avg_percentile"] == pytest.approx(top_pct)


def test_act_bucketing_and_records(db: Database) -> None:
    acts = {a.key: a for a in build_era_summary(db, "alpha").acts}
    # Founding 2014-2020 (7 seasons): 84-7 regular + 2017 title win -> 85-7.
    assert acts["founding"].record == (85, 7)
    # Transition 2021-2023 (3 seasons): 36-3 regular + 2021 title loss -> 36-4.
    assert acts["transition"].record == (36, 4)
    # Expansion 2024-2025 (2 seasons) -> 24-2.
    assert acts["expansion"].record == (24, 2)


def test_defining_games_rank_title_first(db: Database) -> None:
    s = build_era_summary(db, "alpha")
    titles = [g for g in s.defining_games if g.is_title]
    assert len(titles) == 2
    # The 2017 win must outrank the 2021 loss in the renderer's top-5 ordering.
    won = next(g for g in titles if g.won)
    lost = next(g for g in titles if not g.won)
    assert won.year == 2017 and won.opponent == "Bravo"
    assert lost.year == 2021


def test_coach_spans_collapse(db: Database) -> None:
    coaches = build_era_summary(db, "alpha").coaches
    assert [(c.name, c.year_start, c.year_end) for c in coaches] == [
        ("Coach A", 2014, 2020),
        ("Coach B", 2021, 2025),
    ]


def test_draftees_mapped_to_season(db: Database) -> None:
    seasons = {s.year: s for s in build_era_summary(db, "alpha").seasons}
    # 2019 draft -> 2018 roster (2); 2023 draft -> 2022 roster (3).
    assert seasons[2018].draftees == 2
    assert seasons[2022].draftees == 3


def test_renderer_emits_sections(db: Database) -> None:
    html = render_era_page(build_era_summary(db, "alpha"))
    assert "<!doctype html>" in html
    for marker in ("The three-act trajectory", "Defining games",
                   "Coaches of the era", "Roster of the era",
                   "<svg", "Coach B"):
        assert marker in html


def test_short_history_returns_none(db: Database) -> None:
    # Bravo only has power data via the cohort fillers? No — bravo has no
    # power_ratings rows of its own, so it has 0 era seasons -> None.
    assert build_era_summary(db, "bravo") is None


def test_unknown_slug_returns_none(db: Database) -> None:
    assert build_era_summary(db, "does-not-exist") is None


def test_render_all_isolates_a_poison_slug(db: Database, tmp_path: Path, monkeypatch) -> None:
    # A single broken program must not fail the whole publish: render_all_era_pages
    # swallows per-slug exceptions and still writes the healthy pages.
    from cfb_rankings.era_pages import build as era_build

    real = era_build.render_era_page_for

    def flaky(db_, slug, programs_dir, **kw):
        if slug == "boom":
            raise RuntimeError("synthetic malformed-row failure")
        return real(db_, slug, programs_dir, **kw)

    monkeypatch.setattr(era_build, "render_era_page_for", flaky)
    out = tmp_path / "programs"
    count = era_build.render_all_era_pages(db, out, slugs=["boom", "alpha"])

    assert count == 1
    assert (out / "alpha" / "era" / "cfp" / "index.html").exists()
    assert not (out / "boom" / "era" / "cfp" / "index.html").exists()
