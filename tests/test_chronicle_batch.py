"""Smoke test for ``chronicle_generator.write_cards_batch``.

Verifies the Chronicle batch migration produces the same persistence-ready
payload shape as the sync path for a 3-team test set. Uses a mocked
``submit_batch_offline_safe`` so no live API call happens.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from cfb_rankings.team_pages.chronicle_streams import CandidateObservation
from cfb_rankings.team_pages import chronicle_generator
from cfb_rankings.team_pages.chronicle_generator import (
    build_chronicle_batch_jobs,
    write_cards_batch,
)
from cfb_rankings.llm_runtime_batch import BatchResult


def _make_candidate(stream: str = "archive", suggested_type: str = "moment") -> CandidateObservation:
    return CandidateObservation(
        suggested_type=suggested_type,
        evidence={"week": 7, "season": 2026, "summary": "test evidence"},
        source_citation="from the 2026 season archive",
        oddity_score=0.82,
        date_window=("2026-09-01", "2026-09-30"),
        stream=stream,
        notes="A moment worth noting from the archive.",
    )


def _make_profile_stub(slug: str):
    """Minimal Profile-shaped stub — Chronicle's batch builder only reads a
    small subset of fields (program_name, voice_register, identity_phrase,
    mantra, stock_phrases, era_name_overrides, mascot_voice, never_use).
    """
    class _P:
        def __init__(self, s):
            self.slug = s
            self.program_name = s.replace("-", " ").title()
            self.program_tier = 2
            self.voice_register = "warm-fan"
            self.identity_phrase = "test identity"
            self.mantra = "test mantra"
            self.stock_phrases = ["test phrase"]
            self.never_use = ["banned-test-phrase"]
            self.rivalries = []
        @property
        def era_name_overrides(self):
            return {}
        @property
        def mascot_voice(self):
            return {}
    return _P(slug)


def _make_snapshot_stub(slug: str):
    class _S:
        team_id = 1
        season_year = 2026
    s = _S()
    s.slug = slug
    return s


def test_build_chronicle_batch_jobs_shape():
    """Builder emits one BatchJob per (candidate, profile) pair with a
    1h-TTL cache_control on the system preamble."""
    plan = []
    for slug in ("alabama", "georgia", "michigan"):
        profile = _make_profile_stub(slug)
        snapshot = _make_snapshot_stub(slug)
        plan.append((_make_candidate(), profile, snapshot, "claude-sonnet-4-6"))

    jobs = build_chronicle_batch_jobs(plan)
    assert len(jobs) == 3
    for i, job in enumerate(jobs):
        # custom_id format: chronicle-<slug>-<rank>
        assert job.custom_id.startswith("chronicle-")
        assert job.custom_id.endswith(f"-{i+1}")
        # System block carries cache_control with 1h TTL
        assert len(job.system_blocks) == 1
        sb = job.system_blocks[0]
        assert sb["type"] == "text"
        assert sb["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
        # Messages carry user-turn payload with the program name
        assert len(job.messages) == 1
        assert job.messages[0]["role"] == "user"
        # Metadata threaded for routing back to the candidate
        assert "slug" in job.metadata
        assert "rank" in job.metadata


def test_write_cards_batch_three_team_mock(monkeypatch):
    """3 teams × 1 card each → submit_batch_offline_safe is called once,
    payloads come back as parsed JSON dicts in input order."""
    plan = []
    for slug in ("alabama", "georgia", "michigan"):
        profile = _make_profile_stub(slug)
        snapshot = _make_snapshot_stub(slug)
        plan.append((_make_candidate(), profile, snapshot, "claude-sonnet-4-6"))

    # Build per-job fake BatchResult JSON payloads — these mirror what the
    # SDK would return after the model wrote the card.
    fake_results = []
    for i, slug in enumerate(("alabama", "georgia", "michigan"), start=1):
        body = json.dumps({
            "headline": f"{slug.title()} headline since 2014 with Coach Smith",
            "body": (
                f"{slug.title()}'s archive shows this is the longest such run "
                "since 2014. The numbers thread a line through the program memory "
                "no other class has matched."
            ),
            "attribution": "from the 2026 season archive",
        })
        fake_results.append(BatchResult(
            custom_id=f"chronicle-{slug}-{i}",
            text=body,
            voice_validator_passed=True,
            voice_violations=[],
            input_tokens=500,
            output_tokens=200,
            cache_creation_input_tokens=2000 if i == 1 else 0,
            cache_read_input_tokens=0 if i == 1 else 2000,
            model_used="claude-sonnet-4-6",
            succeeded=True,
            mode="batch",
            metadata={"slug": slug, "rank": i},
        ))

    submit_mock = mock.Mock(return_value=fake_results)
    monkeypatch.setattr(
        "cfb_rankings.team_pages.chronicle_generator.submit_batch_offline_safe",
        submit_mock,
        raising=False,
    )
    # The import inside write_cards_batch is `from cfb_rankings.llm_runtime_batch
    # import submit_batch_offline_safe` — patch via that path too.
    import cfb_rankings.llm_runtime_batch as _lrb
    monkeypatch.setattr(_lrb, "submit_batch_offline_safe", submit_mock)

    results = write_cards_batch(plan)

    assert len(results) == 3
    assert submit_mock.call_count == 1
    for i, (cand, profile, snapshot, mdl, payload, meta) in enumerate(results):
        assert payload is not None, f"row {i}: payload should parse cleanly"
        assert "headline" in payload
        assert "body" in payload
        assert "attribution" in payload
        assert meta["error"] is None
        assert meta["model"] == "claude-sonnet-4-6"
        # First row paid cache write; subsequent rows show cache reads.
        if i == 0:
            assert meta["cache_creation_input_tokens"] == 2000
            assert meta["cache_read_input_tokens"] == 0
        else:
            assert meta["cache_creation_input_tokens"] == 0
            assert meta["cache_read_input_tokens"] == 2000


def test_write_cards_batch_partial_failure_per_card(monkeypatch):
    """One card succeeds, one fails — both come back with the expected
    success/error markers."""
    plan = []
    for slug in ("alabama", "georgia"):
        profile = _make_profile_stub(slug)
        snapshot = _make_snapshot_stub(slug)
        plan.append((_make_candidate(), profile, snapshot, "claude-sonnet-4-6"))

    good_body = json.dumps({
        "headline": "Alabama defining moment since 2014",
        "body": "Alabama's archive shows this is the longest such run since 2014. "
                "The numbers thread a line through the program memory no other class has matched.",
        "attribution": "from the 2026 season archive",
    })
    fake_results = [
        BatchResult(
            custom_id="chronicle-alabama-1",
            text=good_body,
            voice_validator_passed=True,
            voice_violations=[],
            input_tokens=500,
            output_tokens=200,
            cache_creation_input_tokens=2000,
            cache_read_input_tokens=0,
            model_used="claude-sonnet-4-6",
            succeeded=True,
            mode="batch",
        ),
        BatchResult(
            custom_id="chronicle-georgia-2",
            text=None,
            voice_validator_passed=False,
            voice_violations=[],
            input_tokens=0,
            output_tokens=0,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
            model_used="claude-sonnet-4-6",
            succeeded=False,
            mode="batch",
            error="invalid_request_error: malformed system block",
        ),
    ]
    submit_mock = mock.Mock(return_value=fake_results)
    monkeypatch.setattr(
        "cfb_rankings.team_pages.chronicle_generator.submit_batch_offline_safe",
        submit_mock,
        raising=False,
    )
    import cfb_rankings.llm_runtime_batch as _lrb
    monkeypatch.setattr(_lrb, "submit_batch_offline_safe", submit_mock)

    results = write_cards_batch(plan)
    # row 0: clean success
    _c0, _p0, _s0, _m0, payload0, meta0 = results[0]
    assert payload0 is not None
    assert meta0["error"] is None
    # row 1: batch reported failure
    _c1, _p1, _s1, _m1, payload1, meta1 = results[1]
    assert payload1 is None
    assert meta1["error"] is not None
    assert "malformed" in meta1["error"]
