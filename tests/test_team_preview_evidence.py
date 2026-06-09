"""Regression coverage for the Milestone A preview evidence contract."""

from __future__ import annotations

from cfb_rankings.team_preview.evidence import (
    SeasonNormContext,
    TeamEvidence,
    _fingerprint,
    build_team_evidence,
)


class _EvidenceDB:
    def query_one(self, sql: str, params: dict | None = None) -> dict | None:
        flat = " ".join(sql.lower().split())

        if "from teams t left join conferences c" in flat:
            return {
                "team_id": 1,
                "slug": "alabama",
                "current_conference_id": 8,
                "conference_name": "SEC",
            }
        if "from games where season_type = 'regular'" in flat:
            return {"season_year": 2024}
        if "sum(case when (home_team_id = :t and home_points > away_points)" in flat:
            return {"w": 12, "l": 2, "t": 0}
        if "from official_rankings" in flat:
            return None
        if "from games g join teams ht on ht.team_id = g.home_team_id" in flat:
            return None
        if "select max(season_year) from team_talent_snapshots" in flat:
            return None
        if "select max(season_year) from recruiting_entries" in flat:
            return None
        if "select max(season_year) from returning_production" in flat:
            return None
        if "sum(case when to_team_id = :t then 1 else 0 end) tin" in flat:
            return {"tin": 0, "tout": 0}
        if "from player_nfl_draft" in flat:
            return {"c": 0, "cap": 0}
        if "select max(week) from power_ratings_weekly" in flat:
            return {"value": 17}
        if "select power_rating from power_ratings_weekly" in flat:
            return {"power_rating": 22.5}
        if "select max(week) from resume_ratings_weekly" in flat:
            return {"value": 17}
        if "select resume_score as resume_rating from resume_ratings_weekly" in flat:
            return {"resume_rating": 18.75}
        raise AssertionError(f"Unhandled SQL in test stub: {sql}")


def test_build_team_evidence_populates_resume_prior_rating() -> None:
    norm = SeasonNormContext(
        season_year=2026,
        power_season=2025,
        resume_season=2025,
    )
    ev = build_team_evidence(_EvidenceDB(), "alabama", 2026, "2026-05-25", norm)
    assert ev is not None
    assert ev.resume_prior_rating == 18.75
    assert "resume_prior_lag(2025)" in ev.missing_sources


def test_fingerprint_changes_when_resume_prior_rating_changes() -> None:
    common = dict(
        slug="alabama",
        team_id=1,
        season_year=2026,
        as_of_date="2026-05-25",
        conference_id=8,
        conference_name="SEC",
        is_independent=False,
        power_prior_rating=22.5,
    )
    a = TeamEvidence(**common, resume_prior_rating=12.0)
    b = TeamEvidence(**common, resume_prior_rating=19.0)
    assert _fingerprint(a) != _fingerprint(b)
