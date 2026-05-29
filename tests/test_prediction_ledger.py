"""Tests for the WS-09 prediction ledger (the calibration trust spine).

Coverage:
  - record_prediction is idempotent on its deterministic id and preserves
    observed_at (first-seen) + any prior resolution across re-records.
  - confidence band derives from confidence_value when not supplied; bad band raises.
  - resolve_due_predictions only touches rows past expires_at, calls the kind's
    resolver, and leaves not-yet-knowable outcomes unresolved.
  - calibration_summary aggregates resolved rows by band.
  - record_archetype_predictions instruments the classifier end-to-end and the
    archetype resolver grades a held vs revised assignment against real data.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cfb_rankings.calibration import (
    calibration_summary,
    prediction_id_for,
    record_archetype_predictions,
    record_prediction,
    record_season_win_predictions,
    resolve_due_predictions,
)
from cfb_rankings.db import Database
from cfb_rankings.migrations import apply_runtime_migrations

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCHEMA = REPO_ROOT / "research" / "cfb-data-schema-sqlite.sql"


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(f"sqlite:///{tmp_path / 'ledger.db'}")
    database.apply_sql_file(BASE_SCHEMA)
    apply_runtime_migrations(database)
    _seed(database)
    return database


def _seed(db: Database) -> None:
    db.upsert_many(
        "levels",
        [{"level_code": "FBS", "level_name": "FBS", "sort_order": 1},
         {"level_code": "FCS", "level_name": "FCS", "sort_order": 2}],
        conflict_columns=["level_code"],
    )
    db.upsert_many(
        "seasons",
        [{"season_year": y} for y in (2024, 2025, 2026)],
        conflict_columns=["season_year"],
    )
    db.upsert_many(
        "teams",
        [{"team_id": 1, "canonical_name": "Alpha", "slug": "alpha", "level_code": "FBS"},
         {"team_id": 2, "canonical_name": "Bravo", "slug": "bravo", "level_code": "FBS"},
         {"team_id": 3, "canonical_name": "Delta FCS", "slug": "delta", "level_code": "FCS"}],
        conflict_columns=["team_id"],
    )


def _classify(db: Database, team_id: int, season: int, archetype: str, conf: float = 0.7) -> None:
    db.upsert_many(
        "fanbase_classification",
        [{"team_id": team_id, "season_year": season, "primary_archetype_slug": archetype,
          "primary_confidence": conf, "modifier_slugs_json": "[]", "signature_phrase": "",
          "classifier_version": "v1.0", "notes": "test"}],
        conflict_columns=["team_id", "season_year"],
    )


def test_record_is_idempotent_and_preserves_first_seen(db: Database) -> None:
    pid1 = record_prediction(
        db, model_id="m", entity_type="team", entity_id="alpha",
        prediction_kind="archetype_assignment", period_key="2026",
        predicted_value="quiet-professional", confidence_value=0.8,
        observed_at="2026-01-01 00:00:00",
    )
    pid2 = record_prediction(
        db, model_id="m", entity_type="team", entity_id="alpha",
        prediction_kind="archetype_assignment", period_key="2026",
        predicted_value="content-mid-major", confidence_value=0.5,
        observed_at="2026-05-01 00:00:00",
    )
    assert pid1 == pid2 == prediction_id_for("m", "team", "alpha", "archetype_assignment", "2026")
    rows = db.query_all("select * from prediction_ledger", {})
    assert len(rows) == 1  # upsert, not append
    row = rows[0]
    assert row["predicted_value"] == "content-mid-major"   # value refreshed
    assert row["confidence_band"] == "medium"              # 0.5 -> medium
    assert row["observed_at_utc"] == "2026-01-01 00:00:00"  # first-seen preserved


def test_band_derivation_and_validation(db: Database) -> None:
    record_prediction(db, model_id="m", entity_type="team", entity_id="a",
                      prediction_kind="k", period_key="p", predicted_value="x",
                      confidence_value=0.9)
    record_prediction(db, model_id="m", entity_type="team", entity_id="b",
                      prediction_kind="k", period_key="p", predicted_value="x",
                      confidence_value=None)
    bands = {r["entity_id"]: r["confidence_band"]
             for r in db.query_all("select entity_id, confidence_band from prediction_ledger", {})}
    assert bands["a"] == "high"
    assert bands["b"] == "unset"
    with pytest.raises(ValueError):
        record_prediction(db, model_id="m", entity_type="team", entity_id="c",
                          prediction_kind="k", period_key="p", predicted_value="x",
                          confidence_band="bogus")


def test_resolve_only_touches_due_rows(db: Database) -> None:
    # alpha predicted (for 2025) to stay quiet-professional; actually does (held).
    _classify(db, 1, 2025, "quiet-professional")
    record_prediction(
        db, model_id="fanbase-classifier", entity_type="team", entity_id="alpha",
        prediction_kind="archetype_assignment", period_key="2025",
        predicted_value="quiet-professional", confidence_value=0.7,
        expires_at="2026-02-01 00:00:00",
    )
    # bravo's window has NOT expired yet -> must be skipped by the resolver.
    record_prediction(
        db, model_id="fanbase-classifier", entity_type="team", entity_id="bravo",
        prediction_kind="archetype_assignment", period_key="2099",
        predicted_value="whatever", confidence_value=0.7,
        expires_at="2099-02-01 00:00:00",
    )
    result = resolve_due_predictions(db, now="2026-05-28 00:00:00")
    assert result["due"] == 1            # only alpha's window has passed
    assert result["resolved"] == 1
    assert result["by_kind"] == {"archetype_assignment": 1}

    alpha = db.query_one(
        "select actual_value, accuracy_score, resolution_note from prediction_ledger "
        "where entity_id = 'alpha'", {})
    assert alpha["actual_value"] == "quiet-professional"
    assert alpha["accuracy_score"] == 1.0
    assert alpha["resolution_note"] == "held"


def test_resolve_skips_unknowable_outcome(db: Database) -> None:
    # Due by date, but season 2025 has no classification yet -> stays unresolved.
    record_prediction(
        db, model_id="fanbase-classifier", entity_type="team", entity_id="alpha",
        prediction_kind="archetype_assignment", period_key="2025",
        predicted_value="quiet-professional", confidence_value=0.7,
        expires_at="2026-02-01 00:00:00",
    )
    result = resolve_due_predictions(db, now="2026-05-28 00:00:00")
    assert result["due"] == 1
    assert result["resolved"] == 0
    assert result["skipped"] == 1
    row = db.query_one("select resolved_at_utc from prediction_ledger where entity_id='alpha'", {})
    assert row["resolved_at_utc"] is None


def test_resolve_grades_a_revised_assignment_as_miss(db: Database) -> None:
    _classify(db, 1, 2025, "content-mid-major")  # actual differs from prediction
    record_prediction(
        db, model_id="fanbase-classifier", entity_type="team", entity_id="alpha",
        prediction_kind="archetype_assignment", period_key="2025",
        predicted_value="quiet-professional", confidence_value=0.7,
        expires_at="2026-02-01 00:00:00",
    )
    resolve_due_predictions(db, now="2026-05-28 00:00:00")
    alpha = db.query_one(
        "select actual_value, accuracy_score, resolution_note from prediction_ledger "
        "where entity_id='alpha'", {})
    assert alpha["actual_value"] == "content-mid-major"
    assert alpha["accuracy_score"] == 0.0
    assert alpha["resolution_note"] == "revised"


def test_record_archetypes_instruments_fbs_only_and_resolves(db: Database) -> None:
    # Source season 2024 archetypes (the predicted carry-forward).
    _classify(db, 1, 2024, "quiet-professional", conf=0.8)
    _classify(db, 2, 2024, "stockholm-syndrome", conf=0.5)
    _classify(db, 3, 2024, "delusional", conf=0.9)  # FCS — must be excluded
    # Actual 2025 outcomes: alpha holds, bravo revises.
    _classify(db, 1, 2025, "quiet-professional")
    _classify(db, 2, 2025, "rising-believer")

    # Explicit allowlist (seeded teams aren't in profiles/); delta is FCS anyway.
    out = record_archetype_predictions(db, 2025, fbs_slugs=frozenset({"alpha", "bravo"}))
    assert out["recorded"] == 2          # alpha + bravo, NOT delta (FCS)
    assert out["source_season"] == 2024
    slugs = {r["entity_id"] for r in db.query_all("select entity_id from prediction_ledger", {})}
    assert slugs == {"alpha", "bravo"}
    # Bands carried from the source confidence.
    bama = db.query_one("select confidence_band from prediction_ledger where entity_id='alpha'", {})
    assert bama["confidence_band"] == "high"  # 0.8

    resolve_due_predictions(db, now="2026-05-28 00:00:00")
    summary = calibration_summary(db, model_id="fanbase-classifier")
    assert summary["resolved"] == 2
    assert summary["mean_accuracy"] == 0.5   # 1 held + 1 revised
    # Per-band: alpha (high, held=1.0), bravo (medium, revised=0.0).
    assert summary["band_accuracy"]["high"] == {"n": 1, "accuracy": 1.0}
    assert summary["band_accuracy"]["medium"] == {"n": 1, "accuracy": 0.0}


def test_allowlist_drops_mislabeled_non_fbs_team(db: Database) -> None:
    """charlie is level_code='FBS' in the dirty seed but not in the real-FBS
    allowlist — it must NOT get a prediction logged (mirrors the arc-populator gate)."""
    db.upsert_many(
        "teams",
        [{"team_id": 9, "canonical_name": "Charlie NAIA", "slug": "charlie", "level_code": "FBS"}],
        conflict_columns=["team_id"],
    )
    _classify(db, 1, 2024, "quiet-professional", conf=0.8)
    _classify(db, 9, 2024, "delusional", conf=0.9)
    out = record_archetype_predictions(db, 2025, fbs_slugs=frozenset({"alpha"}))
    assert out["recorded"] == 1
    slugs = {r["entity_id"] for r in db.query_all("select entity_id from prediction_ledger", {})}
    assert slugs == {"alpha"}            # charlie dropped despite level_code='FBS'


def _project(db: Database, slug: str, season: int, wins: int, band: str = "high") -> None:
    tid = db.query_one("select team_id from teams where slug = :s", {"s": slug})["team_id"]
    db.execute(
        """insert into team_season_path_projection
           (team_id, slug, season_year, as_of_date, scenario, regular_season_wins,
            regular_season_losses, final_wins, final_losses, confidence_band, model_version)
           values (:tid, :slug, :season, '2026-05-25', 'base', :wins, :losses,
                   :wins, :losses, :band, 'season_path_v1')""",
        {"tid": tid, "slug": slug, "season": season, "wins": wins,
         "losses": 12 - wins, "band": band},
    )


def _game(db: Database, season: int, home: int, away: int, hp: int, ap: int) -> None:
    db.execute(
        """insert into games
           (season_year, season_type, status, home_team_id, away_team_id, home_points, away_points)
           values (:season, 'regular', 'Final', :home, :away, :hp, :ap)""",
        {"season": season, "home": home, "away": away, "hp": hp, "ap": ap},
    )


def test_record_season_wins_locks_preseason_projection(db: Database) -> None:
    _project(db, "alpha", 2026, wins=10, band="high")
    _project(db, "bravo", 2026, wins=4, band="medium")
    out = record_season_win_predictions(db, 2026, fbs_slugs=frozenset({"alpha", "bravo"}))
    assert out["recorded"] == 2
    alpha = db.query_one(
        "select predicted_value, confidence_band, model_id, expires_at_utc "
        "from prediction_ledger where entity_id='alpha' and prediction_kind='season_wins'", {})
    assert alpha["predicted_value"] == "10"
    assert alpha["confidence_band"] == "high"
    assert alpha["model_id"] == "season-path"
    assert alpha["expires_at_utc"] == "2027-01-15 00:00:00"


def test_season_wins_resolver_grades_against_games(db: Database) -> None:
    _project(db, "alpha", 2025, wins=10)   # predicts 10
    record_season_win_predictions(db, 2025, fbs_slugs=frozenset({"alpha"}))
    # Force expiry into the past so the resolver picks it up.
    db.execute("update prediction_ledger set expires_at_utc='2026-01-15 00:00:00' "
               "where entity_id='alpha' and prediction_kind='season_wins'", {})
    # alpha actually goes 8-1 in completed regular-season games -> |10-8|/4 = 0.5 score.
    aid = db.query_one("select team_id from teams where slug='alpha'")["team_id"]
    bid = db.query_one("select team_id from teams where slug='bravo'")["team_id"]
    for _ in range(8):
        _game(db, 2025, home=aid, away=bid, hp=21, ap=7)   # alpha wins
    _game(db, 2025, home=aid, away=bid, hp=3, ap=24)        # alpha loses
    result = resolve_due_predictions(db, now="2026-05-28 00:00:00", kinds=["season_wins"])
    assert result["resolved"] == 1
    row = db.query_one(
        "select actual_value, accuracy_score, resolution_note from prediction_ledger "
        "where entity_id='alpha' and prediction_kind='season_wins'", {})
    assert row["actual_value"] == "8"
    assert row["accuracy_score"] == 0.5
    assert "predicted 10, actual 8" in row["resolution_note"]


def test_season_wins_resolver_skips_unplayed_season(db: Database) -> None:
    _project(db, "alpha", 2026, wins=10)
    record_season_win_predictions(db, 2026, fbs_slugs=frozenset({"alpha"}))
    db.execute("update prediction_ledger set expires_at_utc='2025-01-01 00:00:00' "
               "where prediction_kind='season_wins'", {})  # due, but no 2026 games exist
    result = resolve_due_predictions(db, now="2026-05-28 00:00:00", kinds=["season_wins"])
    assert result["resolved"] == 0
    assert result["skipped"] == 1


def _game_id(db: Database, season: int, home: int, away: int, hp, ap) -> int:
    db.execute(
        """insert into games
           (season_year, season_type, status, home_team_id, away_team_id, home_points, away_points)
           values (:season, 'regular', :status, :home, :away, :hp, :ap)""",
        {"season": season, "home": home, "away": away, "hp": hp, "ap": ap,
         "status": "Final" if hp is not None else "Scheduled"},
    )
    return int(db.query_one("select max(game_id) as g from games")["g"])


def test_game_pick_resolver_grades_both_sides(db: Database) -> None:
    aid = db.query_one("select team_id from teams where slug='alpha'")["team_id"]
    bid = db.query_one("select team_id from teams where slug='bravo'")["team_id"]
    g = _game_id(db, 2025, home=aid, away=bid, hp=28, ap=10)  # alpha (home) wins
    # one correct pick (alpha), one wrong pick (bravo).
    record_prediction(db, model_id="picks", entity_type="game", entity_id=str(g),
                      prediction_kind="game_pick", period_key="2025",
                      predicted_value="alpha", confidence_value=0.7,
                      expires_at="2025-12-01 00:00:00")
    record_prediction(db, model_id="picks", entity_type="game", entity_id=str(g),
                      prediction_kind="game_pick", period_key="2025-wrong",
                      predicted_value="bravo", confidence_value=0.7,
                      expires_at="2025-12-01 00:00:00")
    out = resolve_due_predictions(db, now="2026-01-01 00:00:00", kinds=["game_pick"])
    assert out["resolved"] == 2
    rows = {r["period_key"]: r for r in db.query_all(
        "select period_key, actual_value, accuracy_score, resolution_note "
        "from prediction_ledger where prediction_kind='game_pick'", {})}
    assert rows["2025"]["actual_value"] == "alpha"
    assert rows["2025"]["accuracy_score"] == 1.0
    assert rows["2025"]["resolution_note"] == "called it"
    assert rows["2025-wrong"]["accuracy_score"] == 0.0
    assert rows["2025-wrong"]["resolution_note"] == "wrong side"


def test_game_pick_resolver_handles_tie(db: Database) -> None:
    aid = db.query_one("select team_id from teams where slug='alpha'")["team_id"]
    bid = db.query_one("select team_id from teams where slug='bravo'")["team_id"]
    g = _game_id(db, 2025, home=aid, away=bid, hp=17, ap=17)
    record_prediction(db, model_id="picks", entity_type="game", entity_id=str(g),
                      prediction_kind="game_pick", period_key="2025",
                      predicted_value="alpha", confidence_value=0.7,
                      expires_at="2025-12-01 00:00:00")
    resolve_due_predictions(db, now="2026-01-01 00:00:00", kinds=["game_pick"])
    row = db.query_one("select actual_value, accuracy_score from prediction_ledger "
                       "where prediction_kind='game_pick'", {})
    assert row["actual_value"] == "tie"
    assert row["accuracy_score"] == 0.5


def test_game_pick_resolver_skips_unplayed_game(db: Database) -> None:
    aid = db.query_one("select team_id from teams where slug='alpha'")["team_id"]
    bid = db.query_one("select team_id from teams where slug='bravo'")["team_id"]
    g = _game_id(db, 2025, home=aid, away=bid, hp=None, ap=None)  # not final
    record_prediction(db, model_id="picks", entity_type="game", entity_id=str(g),
                      prediction_kind="game_pick", period_key="2025",
                      predicted_value="alpha", confidence_value=0.7,
                      expires_at="2025-12-01 00:00:00")
    out = resolve_due_predictions(db, now="2026-01-01 00:00:00", kinds=["game_pick"])
    assert out["resolved"] == 0
    assert out["skipped"] == 1


def _player(db: Database, player_id: int, name: str) -> None:
    db.upsert_many("players", [{"player_id": player_id, "full_name": name}],
                   conflict_columns=["player_id"])


def test_award_resolver_heisman(db: Database) -> None:
    _player(db, 100, "Real Winner")
    _player(db, 200, "Our Pick")
    db.execute(
        """insert into heisman_vote_results (season_year, player_id, team_id, winner_flag)
           values (2025, 100, 1, 1)""", {})
    # We picked player 200 (missed) and, separately, player 100 (called it).
    record_prediction(db, model_id="heisman-model", entity_type="award", entity_id="heisman",
                      prediction_kind="award_winner", period_key="2025",
                      predicted_value="200", confidence_value=0.6,
                      expires_at="2025-12-15 00:00:00")
    resolve_due_predictions(db, now="2026-01-01 00:00:00", kinds=["award_winner"])
    row = db.query_one("select actual_value, accuracy_score, resolution_note "
                       "from prediction_ledger where prediction_kind='award_winner'", {})
    assert row["actual_value"] == "100"
    assert row["accuracy_score"] == 0.0
    assert row["resolution_note"] == "missed"


def test_award_resolver_generic_honor_and_correct_call(db: Database) -> None:
    _player(db, 300, "Biletnikoff Winner")
    db.execute(
        """insert into player_honors
           (player_id, season_year, team_id, honor_scope, honor_name, placement)
           values (300, 2025, 1, 'national', 'Biletnikoff Award', 1)""", {})
    record_prediction(db, model_id="awards", entity_type="award", entity_id="Biletnikoff Award",
                      prediction_kind="award_winner", period_key="2025",
                      predicted_value="300", confidence_value=0.8,
                      expires_at="2025-12-15 00:00:00")
    resolve_due_predictions(db, now="2026-01-01 00:00:00", kinds=["award_winner"])
    row = db.query_one("select actual_value, accuracy_score, resolution_note "
                       "from prediction_ledger where prediction_kind='award_winner'", {})
    assert row["actual_value"] == "300"
    assert row["accuracy_score"] == 1.0
    assert row["resolution_note"] == "called the winner"


def test_award_resolver_skips_when_no_winner_recorded(db: Database) -> None:
    record_prediction(db, model_id="heisman-model", entity_type="award", entity_id="heisman",
                      prediction_kind="award_winner", period_key="2025",
                      predicted_value="200", confidence_value=0.6,
                      expires_at="2025-12-15 00:00:00")
    out = resolve_due_predictions(db, now="2026-01-01 00:00:00", kinds=["award_winner"])
    assert out["resolved"] == 0
    assert out["skipped"] == 1
    row = db.query_one("select resolved_at_utc from prediction_ledger "
                       "where prediction_kind='award_winner'", {})
    assert row["resolved_at_utc"] is None


def test_summary_empty_is_safe(db: Database) -> None:
    summary = calibration_summary(db)
    assert summary["resolved"] == 0
    assert summary["mean_accuracy"] is None
    assert summary["band_accuracy"] == {}


def test_calibration_page_renders_resolved_and_pending(db: Database) -> None:
    from cfb_rankings.provenance.calibration_page import render_calibration_html

    # One resolved archetype call (held -> correct) ...
    _classify(db, 1, 2025, "quiet-professional")
    record_prediction(
        db, model_id="fanbase-classifier", entity_type="team", entity_id="alpha",
        prediction_kind="archetype_assignment", period_key="2025",
        predicted_value="quiet-professional", confidence_value=0.8,
        expires_at="2026-02-01 00:00:00",
    )
    resolve_due_predictions(db, now="2026-05-28 00:00:00", kinds=["archetype_assignment"])
    # ... and one still-pending preseason season-win projection.
    _project(db, "alpha", 2026, wins=10)
    record_season_win_predictions(db, 2026, fbs_slugs=frozenset({"alpha"}))

    html = render_calibration_html(db)
    assert "Fanbase archetype assignments" in html
    assert "Preseason season-win projections" in html
    assert "100%" in html  # the resolved held call graded correct
    assert "awaiting their outcome" in html  # the pending season-win surface
    assert "confusion matrix" in html  # the editorial framing renders
    # The pending surface renders a concrete "we said X" receipt: the standing
    # call, its resolution date, and a team link — not just a generic count.
    assert "On the record now" in html
    assert "10 wins" in html
    assert "/teams/alpha.html" in html
    assert "January 2027" in html  # season-win projections expire mid-January
