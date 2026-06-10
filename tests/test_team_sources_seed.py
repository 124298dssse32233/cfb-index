"""Guard the priority_teams source seed (Build #1, 21->138 coverage).

Protects the committed seed CSV against a bad census refresh: every FBS team must
map to a unique team_id with a valid tier, a reddit sub, and a Google News query.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

SEED = Path(__file__).resolve().parents[1] / "data" / "seeds" / "team_sources_seed.csv"

TIER1_EXPECTED = {
    "miami", "indiana", "georgia", "notre-dame", "texas", "oregon", "ohio-state",
    "lsu", "michigan", "penn-state", "alabama", "usc", "ole-miss", "auburn",
    "texas-tech", "florida-state", "nebraska", "north-carolina", "tennessee",
    "texas-a-m", "wisconsin", "duke",
}


@pytest.fixture(scope="module")
def rows():
    assert SEED.exists(), f"seed missing: {SEED}"
    return list(csv.DictReader(SEED.open(encoding="utf-8")))


def test_covers_full_fbs(rows):
    assert len(rows) == 138, f"expected 138 FBS teams, got {len(rows)}"


def test_team_ids_unique_and_int(rows):
    ids = [r["team_id"] for r in rows]
    assert all(i.strip().isdigit() for i in ids), "non-integer team_id present"
    assert len(set(ids)) == len(ids), "duplicate team_id in seed"


def test_every_team_has_reddit_sub_and_gnews(rows):
    missing_sub = [r["slug"] for r in rows if not (r.get("reddit_team_sub") or "").strip()]
    missing_g = [r["slug"] for r in rows if not (r.get("google_news_query") or "").strip()]
    assert not missing_sub, f"teams missing reddit sub: {missing_sub}"
    assert not missing_g, f"teams missing google_news_query: {missing_g}"


def test_tiers_valid_and_tier1_present(rows):
    for r in rows:
        assert r["collection_tier"] in {"1", "2", "3"}, (r["slug"], r["collection_tier"])
    tier1 = {r["slug"] for r in rows if r["collection_tier"] == "1"}
    assert tier1 == TIER1_EXPECTED, f"tier-1 drift: {tier1 ^ TIER1_EXPECTED}"


def test_reddit_mode_valid(rows):
    for r in rows:
        assert r["reddit_mode"] in {"dedicated", "school_flair", "skip"}, (r["slug"], r["reddit_mode"])


def test_school_subs_have_flair_filter(rows):
    """A school sub without a flair filter would re-import the noise we just removed."""
    bad = [r["slug"] for r in rows
           if r["reddit_mode"] == "school_flair" and not (r.get("reddit_flair_filter") or "").strip()]
    assert not bad, f"school_flair subs missing flair filter: {bad}"
