"""Tests for ``cfb_rankings.llm_runtime_batch`` and ``CostMeter``.

All Anthropic SDK calls are mocked — none of these tests should touch the
network. Cross-platform safe (no Linux-only assumptions).
"""
from __future__ import annotations

import sys
import types
from typing import Any
from unittest import mock

import pytest

from cfb_rankings import llm_runtime, llm_runtime_batch
from cfb_rankings.llm_runtime import CostMeter, CostCeilingExceeded, MODEL_RATES
from cfb_rankings.llm_runtime_batch import (
    BatchJob,
    BatchResult,
    submit_batch,
    submit_batch_offline_safe,
)


# ---------------------------------------------------------------------------
# Fake SDK shapes (attr-style) so the production code path exercises both
# attr-and-dict-style result handling.
# ---------------------------------------------------------------------------

class _FakeUsage:
    def __init__(self, input_tokens=0, output_tokens=0,
                 cache_creation_input_tokens=0, cache_read_input_tokens=0):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_creation_input_tokens = cache_creation_input_tokens
        self.cache_read_input_tokens = cache_read_input_tokens


class _FakeContentBlock:
    def __init__(self, text):
        self.text = text


class _FakeMessage:
    def __init__(self, text, model="claude-sonnet-4-6", usage=None):
        self.content = [_FakeContentBlock(text)]
        self.model = model
        self.usage = usage or _FakeUsage(
            input_tokens=100,
            output_tokens=200,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )


class _FakeBatchResultEntry:
    def __init__(self, custom_id, result_type, message=None, error=None):
        self.custom_id = custom_id
        self.result = types.SimpleNamespace(
            type=result_type,
            message=message,
            error=error,
        )


class _FakeBatchStatus:
    def __init__(self, batch_id="batch_test_001", processing_status="ended",
                 succeeded=0, errored=0, canceled=0, expired=0):
        self.id = batch_id
        self.processing_status = processing_status
        self.request_counts = types.SimpleNamespace(
            succeeded=succeeded,
            errored=errored,
            canceled=canceled,
            expired=expired,
        )


def _make_fake_anthropic(
    *,
    submit_status: _FakeBatchStatus | None = None,
    retrieve_sequence: list[_FakeBatchStatus] | None = None,
    results: list[_FakeBatchResultEntry] | None = None,
    submit_raises: Exception | None = None,
):
    """Build a fake `anthropic` module with messages.batches API."""
    submit_status = submit_status or _FakeBatchStatus()
    retrieve_sequence = retrieve_sequence or [submit_status]
    results = results or []

    create_calls: list[Any] = []

    class _FakeBatches:
        def __init__(self):
            self._retrieve_idx = 0

        def create(self, requests):
            create_calls.append(requests)
            if submit_raises is not None:
                raise submit_raises
            return submit_status

        def retrieve(self, batch_id):
            assert batch_id == submit_status.id
            idx = min(self._retrieve_idx, len(retrieve_sequence) - 1)
            self._retrieve_idx += 1
            return retrieve_sequence[idx]

        def results(self, batch_id):
            assert batch_id == submit_status.id
            return iter(results)

    class _FakeMessagesAPI:
        def __init__(self):
            self.batches = _FakeBatches()

    class _FakeClient:
        def __init__(self, api_key=None):
            self.messages = _FakeMessagesAPI()

    fake_anthropic = types.SimpleNamespace(Anthropic=_FakeClient)
    return fake_anthropic, create_calls


def _stub_validator_passes(monkeypatch):
    """Force the voice validator to pass on any input — keeps tests focused
    on the batch plumbing rather than the editorial gate."""
    monkeypatch.setattr(
        llm_runtime_batch,
        "_load_validator",
        lambda: (lambda text, source="": (True, [])),
    )
    monkeypatch.setattr(
        llm_runtime_batch,
        "_VALIDATOR_CACHE",
        lambda text, source="": (True, []),
        raising=False,
    )


def _stub_validator_fails_on(monkeypatch, banned: str):
    """Validator fails on any text containing ``banned`` substring."""
    def _v(text, source=""):
        if banned and banned in text:
            return False, [banned]
        return True, []
    monkeypatch.setattr(llm_runtime_batch, "_load_validator", lambda: _v)
    monkeypatch.setattr(llm_runtime_batch, "_VALIDATOR_CACHE", _v, raising=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_submit_batch_happy_path(monkeypatch):
    """One batch with two jobs, both succeed; results returned in input order."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    _stub_validator_passes(monkeypatch)

    msg_a = _FakeMessage("hello from job A", usage=_FakeUsage(
        input_tokens=10, output_tokens=20,
        cache_creation_input_tokens=500, cache_read_input_tokens=0,
    ))
    msg_b = _FakeMessage("hello from job B", usage=_FakeUsage(
        input_tokens=10, output_tokens=22,
        cache_creation_input_tokens=0, cache_read_input_tokens=500,
    ))
    results = [
        _FakeBatchResultEntry("job-b", "succeeded", message=msg_b),
        _FakeBatchResultEntry("job-a", "succeeded", message=msg_a),
    ]
    fake_anthropic, create_calls = _make_fake_anthropic(results=results)
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    jobs = [
        BatchJob(
            custom_id="job-a",
            system_blocks=[{"type": "text", "text": "system prefix",
                            "cache_control": {"type": "ephemeral", "ttl": "1h"}}],
            messages=[{"role": "user", "content": "hi a"}],
            model="claude-sonnet-4-6",
            max_tokens=200,
        ),
        BatchJob(
            custom_id="job-b",
            system_blocks=[{"type": "text", "text": "system prefix",
                            "cache_control": {"type": "ephemeral", "ttl": "1h"}}],
            messages=[{"role": "user", "content": "hi b"}],
            model="claude-sonnet-4-6",
            max_tokens=200,
        ),
    ]
    out = submit_batch(jobs, poll_interval_seconds=0)

    assert [r.custom_id for r in out] == ["job-a", "job-b"]
    assert out[0].text == "hello from job A"
    assert out[1].text == "hello from job B"
    assert out[0].cache_creation_input_tokens == 500
    assert out[1].cache_read_input_tokens == 500
    assert all(r.succeeded for r in out)
    assert all(r.voice_validator_passed for r in out)

    # Verify the create() call included our system_blocks (with cache_control)
    assert len(create_calls) == 1
    req_a = next(r for r in create_calls[0] if r["custom_id"] == "job-a")
    assert req_a["params"]["system"][0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}


def test_submit_batch_offline_safe_no_sdk(monkeypatch):
    """Missing anthropic SDK → returns offline-stub results, never raises."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    # Remove anthropic from sys.modules and ensure import fails.
    monkeypatch.setitem(sys.modules, "anthropic", None)

    jobs = [
        BatchJob(
            custom_id=f"job-{i}",
            system_blocks=[{"type": "text", "text": "sys"}],
            messages=[{"role": "user", "content": f"u{i}"}],
            model="claude-haiku-4-5",
            max_tokens=100,
        )
        for i in range(3)
    ]
    out = submit_batch_offline_safe(jobs)
    assert len(out) == 3
    for r in out:
        assert r.succeeded is False
        assert r.mode == "offline-stub"
        assert r.text is None


def test_submit_batch_offline_safe_no_api_key(monkeypatch):
    """No API key → offline-stub for every job. Fallback text is applied."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # Also stub AppConfig to ensure no key surfaces.
    monkeypatch.setattr(
        llm_runtime_batch, "_resolve_api_key", lambda: None,
    )

    jobs = [
        BatchJob(
            custom_id="job-1",
            system_blocks=[],
            messages=[{"role": "user", "content": "u"}],
            model="claude-sonnet-4-6",
            max_tokens=100,
        ),
        BatchJob(
            custom_id="job-2",
            system_blocks=[],
            messages=[{"role": "user", "content": "u"}],
            model="claude-sonnet-4-6",
            max_tokens=100,
        ),
    ]
    out = submit_batch_offline_safe(jobs, fallback_per_job=lambda j: f"stub-for-{j.custom_id}")
    assert [r.text for r in out] == ["stub-for-job-1", "stub-for-job-2"]
    assert all(r.mode == "offline-stub" for r in out)
    assert all(not r.succeeded for r in out)


def test_submit_batch_partial_failure(monkeypatch):
    """SDK returns mixed succeeded/errored results; partial failure surfaces per-job."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    _stub_validator_passes(monkeypatch)

    msg_ok = _FakeMessage("ok response")
    err_obj = types.SimpleNamespace(
        type="invalid_request_error",
        message="bad input for job 2",
    )
    results = [
        _FakeBatchResultEntry("job-1", "succeeded", message=msg_ok),
        _FakeBatchResultEntry("job-2", "errored", error=err_obj),
    ]
    fake_anthropic, _ = _make_fake_anthropic(results=results)
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    jobs = [
        BatchJob(custom_id="job-1", system_blocks=[],
                 messages=[{"role": "user", "content": "u1"}],
                 model="claude-sonnet-4-6", max_tokens=100),
        BatchJob(custom_id="job-2", system_blocks=[],
                 messages=[{"role": "user", "content": "u2"}],
                 model="claude-sonnet-4-6", max_tokens=100),
    ]
    out = submit_batch(jobs, poll_interval_seconds=0)
    assert out[0].succeeded and out[0].text == "ok response"
    assert not out[1].succeeded
    assert out[1].error is not None
    assert "bad input for job 2" in out[1].error


def test_submit_batch_voice_validator_runs_per_result(monkeypatch):
    """Voice validator runs on each successful result before return."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    _stub_validator_fails_on(monkeypatch, banned="forbidden")

    msg_clean = _FakeMessage("clean editorial copy")
    msg_dirty = _FakeMessage("contains the forbidden phrase")
    results = [
        _FakeBatchResultEntry("clean-job", "succeeded", message=msg_clean),
        _FakeBatchResultEntry("dirty-job", "succeeded", message=msg_dirty),
    ]
    fake_anthropic, _ = _make_fake_anthropic(results=results)
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    jobs = [
        BatchJob(custom_id="clean-job", system_blocks=[],
                 messages=[{"role": "user", "content": "u"}],
                 model="claude-sonnet-4-6", max_tokens=100),
        BatchJob(custom_id="dirty-job", system_blocks=[],
                 messages=[{"role": "user", "content": "u"}],
                 model="claude-sonnet-4-6", max_tokens=100),
    ]
    out = submit_batch(jobs, poll_interval_seconds=0)
    assert out[0].voice_validator_passed is True
    assert out[0].voice_violations == []
    assert out[1].voice_validator_passed is False
    assert "forbidden" in out[1].voice_violations


def test_submit_batch_cache_control_passes_through(monkeypatch):
    """The cache_control field on system blocks reaches the batch request payload."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    _stub_validator_passes(monkeypatch)

    results = [_FakeBatchResultEntry("only-job", "succeeded", message=_FakeMessage("x"))]
    fake_anthropic, create_calls = _make_fake_anthropic(results=results)
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    job = BatchJob(
        custom_id="only-job",
        system_blocks=[
            {"type": "text", "text": "static voice contract"},
            {
                "type": "text",
                "text": "huge shared evidence block",
                "cache_control": {"type": "ephemeral", "ttl": "1h"},
            },
        ],
        messages=[{"role": "user", "content": "per-job"}],
        model="claude-opus-4-7",
        max_tokens=512,
    )
    submit_batch([job], poll_interval_seconds=0)

    req = create_calls[0][0]
    assert req["custom_id"] == "only-job"
    system = req["params"]["system"]
    assert len(system) == 2
    # First block is uncached static voice contract.
    assert "cache_control" not in system[0]
    # Second block carries the 1h cache control.
    assert system[1]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert system[1]["text"] == "huge shared evidence block"


def test_submit_batch_offline_safe_submit_failure_falls_back(monkeypatch):
    """If batch submission itself raises, offline_safe returns stub results."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    fake_anthropic, _ = _make_fake_anthropic(
        submit_raises=RuntimeError("connection reset"),
    )
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
    _stub_validator_passes(monkeypatch)

    jobs = [
        BatchJob(custom_id="j", system_blocks=[],
                 messages=[{"role": "user", "content": "u"}],
                 model="claude-sonnet-4-6", max_tokens=10),
    ]
    out = submit_batch_offline_safe(jobs)
    assert len(out) == 1
    assert out[0].mode == "offline-stub"
    assert out[0].error is not None
    assert "submit_failed" in out[0].error


# ---------------------------------------------------------------------------
# CostMeter tests
# ---------------------------------------------------------------------------

def test_cost_meter_records_and_warns(caplog):
    meter = CostMeter(ceiling_usd=1.0, label="test_meter", warn_at_fraction=0.5)
    usage = _FakeUsage(input_tokens=10_000, output_tokens=2_000)
    # Sonnet sync: 10K input × $3/M = $0.03, 2K output × $15/M = $0.03 → $0.06
    cost = meter.record("claude-sonnet-4-6", usage, is_batch=False)
    assert cost == pytest.approx(0.06, rel=1e-3)
    assert meter.spent_usd == pytest.approx(0.06, rel=1e-3)
    assert len(meter.records) == 1


def test_cost_meter_batch_discount_applied():
    meter = CostMeter(ceiling_usd=100.0, label="test_batch")
    usage = _FakeUsage(input_tokens=10_000, output_tokens=2_000)
    sync_cost = meter.compute_cost("claude-sonnet-4-6", usage, is_batch=False)
    batch_cost = meter.compute_cost("claude-sonnet-4-6", usage, is_batch=True)
    # Batch should be exactly 50% of sync for input + output (no cache here).
    assert batch_cost == pytest.approx(sync_cost * 0.5, rel=1e-6)


def test_cost_meter_cache_rates():
    """Cache reads + writes use the cache-specific rates; not discounted by batch."""
    meter_5m = CostMeter(ceiling_usd=100.0, label="cache_5m", cache_ttl="5m")
    meter_1h = CostMeter(ceiling_usd=100.0, label="cache_1h", cache_ttl="1h")
    usage = _FakeUsage(
        input_tokens=0, output_tokens=0,
        cache_creation_input_tokens=1_000_000,
        cache_read_input_tokens=0,
    )
    cost_5m = meter_5m.compute_cost("claude-sonnet-4-6", usage)
    cost_1h = meter_1h.compute_cost("claude-sonnet-4-6", usage)
    # 5m write: 3.75/M × 1M = $3.75; 1h write: 6.00/M × 1M = $6.00
    assert cost_5m == pytest.approx(3.75, rel=1e-3)
    assert cost_1h == pytest.approx(6.00, rel=1e-3)


def test_cost_meter_ceiling_raises():
    meter = CostMeter(ceiling_usd=0.05, label="tight_meter")
    # Opus rates: 10K input × $15/M + 2K output × $75/M = $0.15 + $0.15 = $0.30
    usage = _FakeUsage(input_tokens=10_000, output_tokens=2_000)
    with pytest.raises(CostCeilingExceeded):
        meter.record("claude-opus-4-7", usage)


def test_cost_meter_summary_aggregates_by_model():
    meter = CostMeter(ceiling_usd=100.0, label="agg")
    meter.record("claude-sonnet-4-6", _FakeUsage(input_tokens=1000, output_tokens=500))
    meter.record("claude-sonnet-4-6", _FakeUsage(input_tokens=2000, output_tokens=1000))
    meter.record("claude-opus-4-7", _FakeUsage(input_tokens=1000, output_tokens=500))
    summary = meter.summary()
    assert summary["call_count"] == 3
    assert set(summary["by_model"].keys()) == {"claude-sonnet-4-6", "claude-opus-4-7"}
    assert summary["by_model"]["claude-sonnet-4-6"]["calls"] == 2
    assert summary["by_model"]["claude-opus-4-7"]["calls"] == 1


def test_cost_meter_haiku_suffix_resolves():
    """The -20251001 suffixed Haiku model id should resolve to Haiku rates."""
    meter = CostMeter(ceiling_usd=100.0, label="haiku")
    usage = _FakeUsage(input_tokens=10_000, output_tokens=2_000)
    # Haiku: 10K × $1/M + 2K × $5/M = $0.01 + $0.01 = $0.02
    cost = meter.compute_cost("claude-haiku-4-5-20251001", usage)
    assert cost == pytest.approx(0.02, rel=1e-3)


def test_model_rates_table_complete():
    """All three model tiers + suffixed haiku are in the rates table."""
    for model in ("claude-opus-4-7", "claude-sonnet-4-6",
                  "claude-haiku-4-5", "claude-haiku-4-5-20251001"):
        assert model in MODEL_RATES
        rates = MODEL_RATES[model]
        for key in ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h"):
            assert key in rates
            assert rates[key] > 0
