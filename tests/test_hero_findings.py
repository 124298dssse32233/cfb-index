"""Tests for the cfb_rankings.hero_findings scaffold package.

v5-7.5 foundation. The generators are now wired:
  * generate_hub_finding — reads team_cohort_divergence_week
  * generate_daily_finding — reads daily_takes
  * generate_heisman_finding — reads heisman_market_odds_weekly
  * generate_team_finding — reads fanbase_mood_weekly
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.hero_findings import (
    FindingKind,
    HeroFinding,
    generate_daily_finding,
    generate_heisman_finding,
    generate_hub_finding,
    generate_team_finding,
    render_hero_finding_html,
)


def test_finding_kind_enum_values_match_spec() -> None:
    expected = {
        "cohort_divergence",
        "belief_delta",
        "race_shift",
        "anniversary_anchor",
        "lead_claim",
        "edition_lead",
        "fallback_avg_mood",
    }
    assert {k.value for k in FindingKind} == expected


def _sample_finding(**kwargs) -> HeroFinding:
    defaults = dict(
        kind=FindingKind.COHORT_DIVERGENCE,
        number="47 of 130",
        sentence="Fanbases diverged from the model by <em>more than 15 spots</em> this week.",
        sample_caption="Sample: 202,341 mentions · 47 sources · last 7 days",
        sample_size=47,
        confidence_domain="fan_intel",
        confidence_rank=80,
        sort_priority=10,
    )
    defaults.update(kwargs)
    return HeroFinding(**defaults)


def test_render_emits_locked_class_structure() -> None:
    f = _sample_finding()
    html = render_hero_finding_html(f)
    assert 'class="hero-finding"' in html
    assert 'class="hero-finding__number"' in html
    assert 'class="hero-finding__sentence"' in html
    assert 'class="hero-finding__caption"' in html
    assert 'class="sample-chip"' in html
    assert 'class="confidence confidence--high"' in html


def test_render_escapes_eyebrow_and_number_but_preserves_em_in_sentence() -> None:
    f = _sample_finding(
        number="<X>",
        sentence="The <em>em</em> here is intentional",
    )
    html = render_hero_finding_html(f, eyebrow_text="<bad>")
    assert "&lt;X&gt;" in html
    assert "&lt;bad&gt;" in html
    # The <em> in sentence is passed through (caller's responsibility to sanitize)
    assert "<em>em</em>" in html


def test_render_custom_eyebrow() -> None:
    f = _sample_finding()
    html = render_hero_finding_html(f, eyebrow_text="TODAY")
    assert "TODAY" in html


def test_unset_band_no_n_in_render() -> None:
    """Spec: unset chips suppress the n= suffix."""
    f = _sample_finding(sample_size=1)  # below fallback p10=4
    html = render_hero_finding_html(f)
    assert "confidence--unset" in html
    assert "Awaiting signal" in html
    assert "n=" not in html


def test_confidence_override_label_in_render() -> None:
    f = _sample_finding(sample_size=12, confidence_override_label="Moderate")
    html = render_hero_finding_html(f)
    # Sample 12 → MEDIUM band (color), label override "Moderate"
    assert "Moderate" in html
    assert "confidence--medium" in html
    # Editorial-honesty: band NOT softened
    assert "confidence--low" not in html


def test_generators_handle_none_db_defensively() -> None:
    """Contract: passing db=None should NOT crash — return None instead.

    Generators may be called from contexts where the DB isn't yet wired;
    they must not raise AttributeError on the .query_one / .query_all calls.
    """
    assert generate_hub_finding(None) is None
    assert generate_daily_finding(None, edition_date="2026-05-13") is None
    assert generate_heisman_finding(None, season_year=2026) is None
    assert generate_team_finding(None, team_id=231, season_year=2026) is None


def test_hero_finding_is_frozen() -> None:
    """The dataclass is frozen — downstream code can't mutate it post-create."""
    f = _sample_finding()
    with pytest.raises(Exception):  # FrozenInstanceError subclass varies
        f.number = "changed"


# ---------------------------------------------------------------------------
# generate_hub_finding — cohort divergence aggregator (2026-05-17)
# ---------------------------------------------------------------------------

@pytest.fixture
def divergence_db(tmp_path: Path) -> Database:
    """Empty DB with team_cohort_divergence_week + teams tables."""
    d = Database(f"sqlite:///{tmp_path / 'div.db'}")
    d.execute("""
        CREATE TABLE teams (
            team_id INTEGER PRIMARY KEY,
            canonical_name TEXT,
            school_name TEXT,
            short_name TEXT,
            slug TEXT
        )
    """)
    d.execute("""
        CREATE TABLE team_cohort_divergence_week (
            team_id INTEGER,
            week TEXT,
            divergence_score REAL,
            num_cohorts_qualifying INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (team_id, week)
        )
    """)
    return d


def test_hub_finding_returns_none_for_empty_table(divergence_db: Database) -> None:
    assert generate_hub_finding(divergence_db) is None


def test_hub_finding_returns_none_when_table_missing(tmp_path: Path) -> None:
    """OperationalError → None, never raises."""
    d = Database(f"sqlite:///{tmp_path / 'bare.db'}")
    assert generate_hub_finding(d) is None


def test_hub_finding_picks_highest_divergence(divergence_db: Database) -> None:
    """Among qualifying teams in latest week, top score wins."""
    divergence_db.execute(
        "INSERT INTO teams (team_id, short_name, slug) VALUES (?, ?, ?)",
        (333, "Alabama", "alabama"),
    )
    divergence_db.execute(
        "INSERT INTO teams (team_id, short_name, slug) VALUES (?, ?, ?)",
        (334, "Auburn", "auburn"),
    )
    divergence_db.execute(
        "INSERT INTO team_cohort_divergence_week "
        "(team_id, week, divergence_score, num_cohorts_qualifying) "
        "VALUES (?, ?, ?, ?)",
        (333, "2026-W19", 1.25, 5),
    )
    divergence_db.execute(
        "INSERT INTO team_cohort_divergence_week "
        "(team_id, week, divergence_score, num_cohorts_qualifying) "
        "VALUES (?, ?, ?, ?)",
        (334, "2026-W19", 0.40, 4),
    )
    f = generate_hub_finding(divergence_db, season_year=2026)
    assert f is not None
    assert f.kind == FindingKind.COHORT_DIVERGENCE
    assert "Alabama" in f.sentence
    assert "fractured" in f.sentence  # score ≥ 1.0
    assert f.number == "5"
    assert f.sample_size == 5
    assert f.confidence_domain == "fan_intel"
    assert f.confidence_rank == 75  # num_cohorts >= 4 → strong
    assert f.extras["team_id"] == 333
    assert f.extras["team_slug"] == "alabama"
    assert f.extras["week_iso"] == "2026-W19"


def test_hub_finding_filters_below_min_cohorts(divergence_db: Database) -> None:
    """A team with only 2 cohorts qualifying must NOT win — too thin a story."""
    divergence_db.execute(
        "INSERT INTO teams (team_id, short_name, slug) VALUES (?, ?, ?)",
        (333, "Alabama", "alabama"),
    )
    divergence_db.execute(
        "INSERT INTO team_cohort_divergence_week "
        "(team_id, week, divergence_score, num_cohorts_qualifying) "
        "VALUES (?, ?, ?, ?)",
        (333, "2026-W19", 2.0, 2),  # high score but only 2 cohorts
    )
    assert generate_hub_finding(divergence_db) is None


def test_hub_finding_uses_latest_week_when_unspecified(
    divergence_db: Database,
) -> None:
    """Without week_iso, the latest week with non-null scores is chosen."""
    divergence_db.execute(
        "INSERT INTO teams (team_id, short_name, slug) VALUES (?, ?, ?)",
        (333, "Alabama", "alabama"),
    )
    divergence_db.execute(
        "INSERT INTO teams (team_id, short_name, slug) VALUES (?, ?, ?)",
        (334, "Auburn", "auburn"),
    )
    # Older week: Auburn wins big
    divergence_db.execute(
        "INSERT INTO team_cohort_divergence_week "
        "(team_id, week, divergence_score, num_cohorts_qualifying) "
        "VALUES (?, ?, ?, ?)",
        (334, "2026-W18", 3.0, 6),
    )
    # Latest week: Alabama wins (more modest score)
    divergence_db.execute(
        "INSERT INTO team_cohort_divergence_week "
        "(team_id, week, divergence_score, num_cohorts_qualifying) "
        "VALUES (?, ?, ?, ?)",
        (333, "2026-W19", 0.6, 3),
    )
    f = generate_hub_finding(divergence_db)
    assert f is not None
    assert "Alabama" in f.sentence
    assert f.extras["week_iso"] == "2026-W19"


def test_hub_finding_honors_explicit_week(divergence_db: Database) -> None:
    """Explicit week_iso overrides the auto-pick."""
    divergence_db.execute(
        "INSERT INTO teams (team_id, short_name, slug) VALUES (?, ?, ?)",
        (334, "Auburn", "auburn"),
    )
    divergence_db.execute(
        "INSERT INTO team_cohort_divergence_week "
        "(team_id, week, divergence_score, num_cohorts_qualifying) "
        "VALUES (?, ?, ?, ?)",
        (334, "2026-W18", 1.5, 4),
    )
    divergence_db.execute(
        "INSERT INTO team_cohort_divergence_week "
        "(team_id, week, divergence_score, num_cohorts_qualifying) "
        "VALUES (?, ?, ?, ?)",
        (334, "2026-W19", 0.2, 3),
    )
    # Latest is W19 (low score), but we ask for W18
    f = generate_hub_finding(divergence_db, week_iso="2026-W18")
    assert f is not None
    assert f.extras["week_iso"] == "2026-W18"
    assert "fractured" in f.sentence  # 1.5 score → fractured


def test_hub_finding_picks_intensity_word_by_score(
    divergence_db: Database,
) -> None:
    """Score ≥1.0 → fractured; ≥0.5 → split; else → diverged."""
    divergence_db.execute(
        "INSERT INTO teams (team_id, short_name, slug) VALUES (?, ?, ?)",
        (340, "TestTeam", "testteam"),
    )
    divergence_db.execute(
        "INSERT INTO team_cohort_divergence_week "
        "(team_id, week, divergence_score, num_cohorts_qualifying) "
        "VALUES (?, ?, ?, ?)",
        (340, "2026-W19", 0.30, 4),
    )
    f = generate_hub_finding(divergence_db)
    assert f is not None
    assert "diverged" in f.sentence


def test_hub_finding_returns_none_for_zero_score(
    divergence_db: Database,
) -> None:
    """Zero/negative score → no story."""
    divergence_db.execute(
        "INSERT INTO teams (team_id, short_name, slug) VALUES (?, ?, ?)",
        (340, "TestTeam", "testteam"),
    )
    divergence_db.execute(
        "INSERT INTO team_cohort_divergence_week "
        "(team_id, week, divergence_score, num_cohorts_qualifying) "
        "VALUES (?, ?, ?, ?)",
        (340, "2026-W19", 0.0, 5),
    )
    assert generate_hub_finding(divergence_db) is None


def test_hub_finding_lower_rank_when_only_three_cohorts(
    divergence_db: Database,
) -> None:
    """3 cohorts = passable (rank 55); 4+ = strong (rank 75)."""
    divergence_db.execute(
        "INSERT INTO teams (team_id, short_name, slug) VALUES (?, ?, ?)",
        (340, "TestTeam", "testteam"),
    )
    divergence_db.execute(
        "INSERT INTO team_cohort_divergence_week "
        "(team_id, week, divergence_score, num_cohorts_qualifying) "
        "VALUES (?, ?, ?, ?)",
        (340, "2026-W19", 0.8, 3),
    )
    f = generate_hub_finding(divergence_db)
    assert f is not None
    assert f.confidence_rank == 55
