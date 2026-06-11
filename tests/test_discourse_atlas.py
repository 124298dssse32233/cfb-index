"""Tests for discourse.atlas — Language Layer Wave 4."""
from __future__ import annotations

import json
import math
import sqlite3

import pytest

from cfb_rankings.discourse.atlas import (
    _cosine,
    _dot,
    _norm,
    _centroid,
    _kmeans,
    compute_discourse_atlas,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE teams (
    team_id   INTEGER PRIMARY KEY,
    slug      TEXT NOT NULL
);

CREATE TABLE team_discourse_terms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id     INTEGER NOT NULL,
    season_year INTEGER NOT NULL,
    week        INTEGER NOT NULL DEFAULT 0,
    term        TEXT    NOT NULL,
    z_score     REAL    NOT NULL
);

CREATE TABLE team_discourse_clusters (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id          INTEGER NOT NULL,
    season_year      INTEGER NOT NULL,
    cluster_id       INTEGER NOT NULL,
    cluster_name     TEXT,
    cluster_rank     INTEGER,
    cluster_size     INTEGER,
    shared_terms     TEXT,
    model_version    TEXT,
    computed_at_utc  TEXT
);
"""

# 8 teams with 5+ distinct terms each; z_scores designed so teams cluster
# into two natural groups: teams 1-4 share "offense"-domain terms and
# teams 5-8 share "defense"-domain terms.
SEED_TERMS: dict[int, dict[str, float]] = {
    # Group A — offense-heavy vocabulary
    1: {"touchdown": 2.1, "qb": 1.9, "passing": 1.7, "yards": 1.5, "offense": 1.3,
        "route": 1.1},
    2: {"touchdown": 1.8, "qb": 2.0, "passing": 1.6, "yards": 1.4, "offense": 1.2,
        "scheme": 0.9},
    3: {"touchdown": 1.5, "qb": 1.7, "passing": 2.1, "yards": 1.6, "offense": 1.4,
        "completion": 1.0},
    4: {"touchdown": 1.6, "qb": 1.8, "passing": 1.5, "yards": 1.3, "offense": 1.5,
        "drive": 1.2},
    # Group B — defense-heavy vocabulary
    5: {"sack": 2.3, "blitz": 2.0, "coverage": 1.8, "pressure": 1.6, "tackle": 1.4,
        "stop": 1.2},
    6: {"sack": 2.1, "blitz": 1.9, "coverage": 1.7, "pressure": 1.5, "tackle": 1.3,
        "turnover": 1.0},
    7: {"sack": 1.9, "blitz": 2.2, "coverage": 2.0, "pressure": 1.7, "tackle": 1.5,
        "interception": 1.1},
    8: {"sack": 2.0, "blitz": 1.8, "coverage": 1.9, "pressure": 1.4, "tackle": 1.6,
        "fumble": 0.8},
}

SEASON = 2025


def _make_db(terms: dict[int, dict[str, float]] | None = None,
             season: int = SEASON) -> sqlite3.Connection:
    """Create a fresh in-memory SQLite DB populated with test data."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(DDL)
    terms = terms if terms is not None else SEED_TERMS
    for team_id, vec in terms.items():
        conn.execute(
            "INSERT INTO teams (team_id, slug) VALUES (?, ?)",
            (team_id, f"team-{team_id}"),
        )
        for term, z in vec.items():
            conn.execute(
                "INSERT INTO team_discourse_terms "
                "(team_id, season_year, week, term, z_score) VALUES (?, ?, 0, ?, ?)",
                (team_id, season, term, z),
            )
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Unit tests — pure math helpers
# ---------------------------------------------------------------------------

class TestCosine:
    def test_identical_vectors_returns_one(self):
        v = {"a": 1.0, "b": 2.0, "c": 3.0}
        assert abs(_cosine(v, v) - 1.0) < 1e-9

    def test_orthogonal_vectors_returns_zero(self):
        a = {"x": 1.0}
        b = {"y": 1.0}
        assert _cosine(a, b) == 0.0

    def test_empty_vectors_returns_zero(self):
        assert _cosine({}, {}) == 0.0

    def test_one_empty_vector_returns_zero(self):
        assert _cosine({"a": 1.0}, {}) == 0.0
        assert _cosine({}, {"a": 1.0}) == 0.0

    def test_known_similarity(self):
        # a = (1, 0), b = (1, 1)/sqrt(2) → cosine = 1/sqrt(2)
        a = {"x": 1.0}
        b = {"x": 1.0, "y": 1.0}
        expected = 1.0 / math.sqrt(2)
        assert abs(_cosine(a, b) - expected) < 1e-9


class TestDot:
    def test_overlapping(self):
        a = {"x": 2.0, "y": 3.0}
        b = {"y": 4.0, "z": 5.0}
        assert _dot(a, b) == pytest.approx(12.0)

    def test_no_overlap(self):
        assert _dot({"a": 1.0}, {"b": 1.0}) == 0.0

    def test_empty(self):
        assert _dot({}, {"a": 1.0}) == 0.0


class TestNorm:
    def test_known(self):
        v = {"a": 3.0, "b": 4.0}
        assert _norm(v) == pytest.approx(5.0)

    def test_empty(self):
        assert _norm({}) == 0.0


class TestCentroid:
    def test_mean_values(self):
        vecs = [{"a": 2.0, "b": 4.0}, {"a": 4.0, "b": 0.0}]
        c = _centroid(vecs)
        assert c["a"] == pytest.approx(3.0)
        assert c["b"] == pytest.approx(2.0)

    def test_empty_list(self):
        assert _centroid([]) == {}

    def test_single_vector(self):
        v = {"x": 1.5, "y": 2.5}
        c = _centroid([v])
        assert c == pytest.approx(v)


class TestKmeans:
    def test_returns_one_id_per_vector(self):
        vecs = [{"a": float(i)} for i in range(1, 7)]
        result = _kmeans(vecs, k=3)
        assert len(result) == len(vecs)

    def test_ids_in_range(self):
        vecs = [{"a": float(i), "b": float(i) * 0.5} for i in range(8)]
        k = 3
        result = _kmeans(vecs, k=k)
        assert all(0 <= cid < k for cid in result)

    def test_empty_vectors(self):
        assert _kmeans([], k=3) == []

    def test_k_gt_n_clamps(self):
        # k > len(vectors) should not crash
        vecs = [{"a": 1.0}, {"b": 2.0}]
        result = _kmeans(vecs, k=10)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Integration tests — compute_discourse_atlas
# ---------------------------------------------------------------------------

class TestComputeDiscourseAtlasReturnShape:
    def test_returns_dict_with_correct_keys(self):
        db = _make_db()
        result = compute_discourse_atlas(db, seasons=SEASON)
        assert isinstance(result, dict)
        assert "clusters_computed" in result
        assert "teams_assigned" in result
        assert "seasons" in result

    def test_seasons_is_list(self):
        db = _make_db()
        result = compute_discourse_atlas(db, seasons=SEASON)
        assert isinstance(result["seasons"], list)

    def test_season_recorded_in_result(self):
        db = _make_db()
        result = compute_discourse_atlas(db, seasons=SEASON)
        assert SEASON in result["seasons"]

    def test_teams_assigned_equals_seed_count(self):
        db = _make_db()
        result = compute_discourse_atlas(db, seasons=SEASON)
        assert result["teams_assigned"] == len(SEED_TERMS)

    def test_clusters_computed_at_least_2(self):
        db = _make_db()
        result = compute_discourse_atlas(db, seasons=SEASON)
        assert result["clusters_computed"] >= 2

    def test_accepts_seasons_as_list(self):
        db = _make_db()
        result = compute_discourse_atlas(db, seasons=[SEASON])
        assert result["seasons"] == [SEASON]


class TestInsufficientData:
    def test_fewer_than_4_teams_skips_season(self):
        # Only 3 teams — should skip
        sparse = {k: v for k, v in list(SEED_TERMS.items())[:3]}
        db = _make_db(terms=sparse)
        result = compute_discourse_atlas(db, seasons=SEASON)
        assert result["clusters_computed"] == 0
        assert result["teams_assigned"] == 0
        assert SEASON not in result["seasons"]

    def test_teams_with_fewer_than_5_terms_excluded(self):
        # 6 teams have >= 5 terms; 2 teams have < 5 terms
        thin_terms: dict[int, dict[str, float]] = {
            **{k: v for k, v in list(SEED_TERMS.items())[:6]},
            9:  {"only": 1.0, "three": 0.5, "terms": 0.3},  # 3 terms — excluded
            10: {"four": 1.0, "term": 0.5, "vec": 0.3, "short": 0.2},  # 4 terms — excluded
        }
        db = _make_db(terms=thin_terms)
        result = compute_discourse_atlas(db, seasons=SEASON)
        # 6 qualified teams → clustering proceeds; only 6 assigned
        assert result["teams_assigned"] == 6


class TestCommitFalse:
    def test_no_rows_written_when_commit_false(self):
        db = _make_db()
        compute_discourse_atlas(db, seasons=SEASON, commit=False)
        cur = db.execute("SELECT COUNT(*) FROM team_discourse_clusters")
        assert cur.fetchone()[0] == 0


class TestCommitTrue:
    def test_rows_written_on_commit(self):
        db = _make_db()
        compute_discourse_atlas(db, seasons=SEASON, commit=True)
        cur = db.execute("SELECT COUNT(*) FROM team_discourse_clusters")
        assert cur.fetchone()[0] == len(SEED_TERMS)

    def test_each_team_gets_exactly_one_cluster_row(self):
        db = _make_db()
        compute_discourse_atlas(db, seasons=SEASON, commit=True)
        cur = db.execute(
            "SELECT team_id, COUNT(*) FROM team_discourse_clusters "
            "WHERE season_year = ? GROUP BY team_id",
            (SEASON,),
        )
        for row in cur.fetchall():
            assert row[1] == 1, f"Team {row[0]} has {row[1]} rows, expected 1"

    def test_cluster_sizes_sum_to_total_assigned(self):
        db = _make_db()
        result = compute_discourse_atlas(db, seasons=SEASON, commit=True)
        cur = db.execute(
            "SELECT SUM(cluster_size) FROM ("
            "  SELECT cluster_id, cluster_size "
            "  FROM team_discourse_clusters "
            "  WHERE season_year = ? "
            "  GROUP BY cluster_id"
            ")",
            (SEASON,),
        )
        db_sum = cur.fetchone()[0] or 0
        assert db_sum == result["teams_assigned"]

    def test_shared_terms_is_valid_json_array(self):
        db = _make_db()
        compute_discourse_atlas(db, seasons=SEASON, commit=True)
        cur = db.execute(
            "SELECT shared_terms FROM team_discourse_clusters WHERE season_year = ?",
            (SEASON,),
        )
        for (shared_json,) in cur.fetchall():
            parsed = json.loads(shared_json)
            assert isinstance(parsed, list)

    def test_commit_overwrites_existing_rows(self):
        db = _make_db()
        compute_discourse_atlas(db, seasons=SEASON, commit=True)
        compute_discourse_atlas(db, seasons=SEASON, commit=True)
        cur = db.execute(
            "SELECT COUNT(*) FROM team_discourse_clusters WHERE season_year = ?",
            (SEASON,),
        )
        # Should still equal number of teams (DELETE then re-INSERT)
        assert cur.fetchone()[0] == len(SEED_TERMS)

    def test_cluster_rank_1_is_largest_cluster(self):
        db = _make_db()
        compute_discourse_atlas(db, seasons=SEASON, commit=True)
        # Fetch cluster_id → rank and size
        cur = db.execute(
            "SELECT cluster_id, cluster_rank, cluster_size "
            "FROM team_discourse_clusters "
            "WHERE season_year = ? "
            "GROUP BY cluster_id",
            (SEASON,),
        )
        rows = cur.fetchall()
        rank1_sizes = [r[2] for r in rows if r[1] == 1]
        other_sizes  = [r[2] for r in rows if r[1] != 1]
        assert rank1_sizes, "No cluster with rank=1 found"
        assert all(rank1_sizes[0] >= s for s in other_sizes)

    def test_model_version_set(self):
        db = _make_db()
        compute_discourse_atlas(db, seasons=SEASON, commit=True)
        cur = db.execute(
            "SELECT DISTINCT model_version FROM team_discourse_clusters "
            "WHERE season_year = ?",
            (SEASON,),
        )
        versions = [r[0] for r in cur.fetchall()]
        assert versions == ["atlas_v1"]

    def test_computed_at_utc_is_set(self):
        db = _make_db()
        compute_discourse_atlas(db, seasons=SEASON, commit=True)
        cur = db.execute(
            "SELECT computed_at_utc FROM team_discourse_clusters "
            "WHERE season_year = ? LIMIT 1",
            (SEASON,),
        )
        ts = cur.fetchone()[0]
        assert ts is not None
        # Should be a valid ISO-8601 datetime string
        from datetime import datetime
        datetime.fromisoformat(ts)  # raises if invalid


class TestMultipleSeasons:
    def test_two_seasons_both_processed(self):
        # Duplicate seed data for a second season
        conn = sqlite3.connect(":memory:")
        conn.executescript(DDL)
        for season in (2024, 2025):
            for team_id, vec in SEED_TERMS.items():
                conn.execute(
                    "INSERT INTO teams (team_id, slug) VALUES (?, ?) "
                    "ON CONFLICT(team_id) DO NOTHING",
                    (team_id, f"team-{team_id}"),
                )
                for term, z in vec.items():
                    conn.execute(
                        "INSERT INTO team_discourse_terms "
                        "(team_id, season_year, week, term, z_score) VALUES (?, ?, 0, ?, ?)",
                        (team_id, season, term, z),
                    )
        conn.commit()

        result = compute_discourse_atlas(conn, seasons=[2024, 2025], commit=True)
        assert sorted(result["seasons"]) == [2024, 2025]
        assert result["teams_assigned"] == len(SEED_TERMS) * 2
        # Each season should have its own set of rows
        for season in (2024, 2025):
            cur = conn.execute(
                "SELECT COUNT(*) FROM team_discourse_clusters WHERE season_year = ?",
                (season,),
            )
            assert cur.fetchone()[0] == len(SEED_TERMS)
