import json
import sqlite3

import pytest

from cfb_rankings.team_pages.atlas_chip_module import ATLAS_CHIP_CSS, render_atlas_chip


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeProfile:
    def __init__(self, team_id=0):
        self.team_id = team_id


class FakeSnapshot:
    def __init__(self, team_id=0):
        self.team_id = team_id


def _make_db(rows=None):
    """Return an in-memory SQLite connection pre-seeded with optional rows."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE team_discourse_clusters (
            cluster_row_id INTEGER PRIMARY KEY,
            team_id        INTEGER,
            season_year    INTEGER,
            cluster_id     INTEGER,
            cluster_name   TEXT,
            cluster_rank   INTEGER,
            cluster_size   INTEGER,
            shared_terms   TEXT,
            model_version  TEXT,
            computed_at_utc TEXT
        )
        """
    )
    if rows:
        conn.executemany(
            """
            INSERT INTO team_discourse_clusters
                (cluster_row_id, team_id, season_year, cluster_id,
                 cluster_name, cluster_rank, cluster_size, shared_terms,
                 model_version, computed_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    conn.commit()
    return conn


def _basic_row(team_id=1, cluster_size=5, shared_terms=None, season_year=2025):
    if shared_terms is None:
        shared_terms = json.dumps(["dynasty", "rebuild", "NIL", "transfer"])
    return (
        1,            # cluster_row_id
        team_id,      # team_id
        season_year,  # season_year
        42,           # cluster_id
        "Blue Bloods",# cluster_name
        1,            # cluster_rank
        cluster_size, # cluster_size
        shared_terms, # shared_terms
        "v1",         # model_version
        "2025-01-01", # computed_at_utc
    )


# ---------------------------------------------------------------------------
# Floor / guard tests
# ---------------------------------------------------------------------------

def test_returns_empty_for_db_none():
    profile = FakeProfile(team_id=1)
    snapshot = FakeSnapshot(team_id=1)
    result = render_atlas_chip(None, profile, snapshot)
    assert result == ""


def test_returns_empty_for_profile_none():
    db = _make_db()
    snapshot = FakeSnapshot(team_id=1)
    result = render_atlas_chip(db, None, snapshot)
    assert result == ""


def test_returns_empty_when_no_cluster_row():
    db = _make_db()  # empty table
    profile = FakeProfile(team_id=99)
    snapshot = FakeSnapshot(team_id=99)
    result = render_atlas_chip(db, profile, snapshot)
    assert result == ""


def test_returns_empty_when_cluster_size_is_1():
    db = _make_db([_basic_row(cluster_size=1)])
    profile = FakeProfile(team_id=1)
    snapshot = FakeSnapshot(team_id=1)
    result = render_atlas_chip(db, profile, snapshot)
    assert result == ""


def test_returns_empty_when_cluster_size_is_0():
    db = _make_db([_basic_row(cluster_size=0)])
    profile = FakeProfile(team_id=1)
    snapshot = FakeSnapshot(team_id=1)
    result = render_atlas_chip(db, profile, snapshot)
    assert result == ""


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

def test_returns_nonempty_html_when_cluster_size_ge_2():
    db = _make_db([_basic_row(cluster_size=2)])
    profile = FakeProfile(team_id=1)
    snapshot = FakeSnapshot(team_id=1)
    result = render_atlas_chip(db, profile, snapshot)
    assert result != ""


def test_html_contains_cluster_name():
    db = _make_db([_basic_row(cluster_size=3)])
    profile = FakeProfile(team_id=1)
    snapshot = FakeSnapshot(team_id=1)
    result = render_atlas_chip(db, profile, snapshot)
    assert "Blue Bloods" in result


def test_html_contains_atlas_chip_css_class():
    db = _make_db([_basic_row(cluster_size=3)])
    profile = FakeProfile(team_id=1)
    snapshot = FakeSnapshot(team_id=1)
    result = render_atlas_chip(db, profile, snapshot)
    assert "atlas-chip" in result


def test_html_contains_companion_count():
    # cluster_size=5 -> companion_count=4
    db = _make_db([_basic_row(cluster_size=5)])
    profile = FakeProfile(team_id=1)
    snapshot = FakeSnapshot(team_id=1)
    result = render_atlas_chip(db, profile, snapshot)
    assert "4 other fanbases" in result


def test_html_contains_shared_terms_as_pills():
    terms = ["dynasty", "rebuild", "NIL", "transfer"]
    db = _make_db([_basic_row(cluster_size=4, shared_terms=json.dumps(terms))])
    profile = FakeProfile(team_id=1)
    snapshot = FakeSnapshot(team_id=1)
    result = render_atlas_chip(db, profile, snapshot)
    for term in terms:
        assert term in result


def test_shared_terms_capped_at_four():
    terms = ["a", "b", "c", "d", "e", "f"]
    db = _make_db([_basic_row(cluster_size=4, shared_terms=json.dumps(terms))])
    profile = FakeProfile(team_id=1)
    snapshot = FakeSnapshot(team_id=1)
    result = render_atlas_chip(db, profile, snapshot)
    # First 4 present, 5th and 6th not rendered as pills
    assert result.count("atlas-chip__term-pill") == 4


def test_html_label_text_present():
    db = _make_db([_basic_row(cluster_size=3)])
    profile = FakeProfile(team_id=1)
    snapshot = FakeSnapshot(team_id=1)
    result = render_atlas_chip(db, profile, snapshot)
    assert "Your Vocabulary Cluster" in result


# ---------------------------------------------------------------------------
# Graceful-degradation tests
# ---------------------------------------------------------------------------

def test_handles_shared_terms_none_gracefully():
    db = _make_db([_basic_row(cluster_size=3, shared_terms=None)])
    profile = FakeProfile(team_id=1)
    snapshot = FakeSnapshot(team_id=1)
    # Must not raise; should return non-empty (cluster_size=3 >= 2)
    result = render_atlas_chip(db, profile, snapshot)
    assert result != ""
    assert "atlas-chip" in result


def test_handles_malformed_json_in_shared_terms_gracefully():
    db = _make_db([_basic_row(cluster_size=3, shared_terms="NOT_VALID_JSON{{{")])
    profile = FakeProfile(team_id=1)
    snapshot = FakeSnapshot(team_id=1)
    result = render_atlas_chip(db, profile, snapshot)
    assert result != ""
    assert "atlas-chip" in result


def test_handles_shared_terms_empty_list():
    db = _make_db([_basic_row(cluster_size=3, shared_terms=json.dumps([]))])
    profile = FakeProfile(team_id=1)
    snapshot = FakeSnapshot(team_id=1)
    result = render_atlas_chip(db, profile, snapshot)
    assert result != ""
    assert "atlas-chip__terms" in result


# ---------------------------------------------------------------------------
# Team-ID fallback chain tests
# ---------------------------------------------------------------------------

def test_falls_back_to_snapshot_team_id_when_profile_team_id_is_zero():
    db = _make_db([_basic_row(team_id=7, cluster_size=3)])
    profile = FakeProfile(team_id=0)
    snapshot = FakeSnapshot(team_id=7)
    result = render_atlas_chip(db, profile, snapshot)
    assert "Blue Bloods" in result


def test_returns_empty_when_both_team_ids_are_zero():
    db = _make_db([_basic_row(team_id=1, cluster_size=3)])
    profile = FakeProfile(team_id=0)
    snapshot = FakeSnapshot(team_id=0)
    result = render_atlas_chip(db, profile, snapshot)
    assert result == ""


def test_snapshot_team_id_takes_priority_over_profile():
    # The snapshot id is canonical (resolved by slug in the renderer); the profile
    # YAML team_id can be stale after a team_id re-ingest. The cluster exists only
    # for the snapshot id, so the chip must use it.
    db = _make_db([_basic_row(team_id=99, cluster_size=3)])
    profile = FakeProfile(team_id=1)     # stale -> no cluster
    snapshot = FakeSnapshot(team_id=99)  # canonical -> has the cluster
    result = render_atlas_chip(db, profile, snapshot)
    assert "Blue Bloods" in result


def test_falls_back_to_profile_team_id_when_snapshot_missing():
    # When the snapshot has no usable id, fall back to the profile's.
    db = _make_db([_basic_row(team_id=1, cluster_size=3)])
    profile = FakeProfile(team_id=1)
    snapshot = FakeSnapshot(team_id=0)
    result = render_atlas_chip(db, profile, snapshot)
    assert "Blue Bloods" in result


# ---------------------------------------------------------------------------
# CSS constant sanity check
# ---------------------------------------------------------------------------

def test_atlas_chip_css_constant_is_nonempty_string():
    assert isinstance(ATLAS_CHIP_CSS, str)
    assert len(ATLAS_CHIP_CSS) > 0


def test_atlas_chip_css_contains_key_selectors():
    assert ".atlas-chip" in ATLAS_CHIP_CSS
    assert ".atlas-chip__name" in ATLAS_CHIP_CSS
    assert ".atlas-chip__label" in ATLAS_CHIP_CSS
    assert ".atlas-chip__terms" in ATLAS_CHIP_CSS


def test_atlas_chip_css_contains_mobile_breakpoint():
    assert "max-width" in ATLAS_CHIP_CSS
