"""Tests for CostMeter wiring across the 14 LLM call sites in Sprint v5-1.5b.

Coverage targets one test per pattern (A, B, C), one for ceiling-breach
propagation, one for meter-shared-across-N-calls, and one regression test
verifying the wired call sites preserve their public API (kwarg-only
``_meter`` parameter; default ``None``).

All Anthropic SDK calls are mocked. No network traffic.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

import pytest

from cfb_rankings.llm_runtime import (
    CostCeilingExceeded,
    CostMeter,
    MODEL_RATES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_usage(input_tokens: int = 1000, output_tokens: int = 500):
    """Build an SDK-shaped usage object (attribute-bearing)."""
    return SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )


def _fake_sdk_response(text: str = "hello", input_tokens: int = 1000,
                       output_tokens: int = 500):
    """Build a fake anthropic SDK response with `.content[0].text` and `.usage`."""
    return SimpleNamespace(
        content=[SimpleNamespace(text=text, type="text")],
        usage=_fake_usage(input_tokens, output_tokens),
    )


def _fake_gwvc_result(text: str = "draft",
                     in_toks: int = 1000, out_toks: int = 500,
                     model: str = "claude-sonnet-4-6",
                     mode: str = "live"):
    """Build the dict-shape result that ``generate_with_voice_check`` returns."""
    return {
        "text": text,
        "voice_validator_passed": True,
        "voice_violations": [],
        "attempts": 1,
        "tokens_used": {"input": in_toks, "output": out_toks},
        "model_used": model,
        "mode": mode,
    }


# ---------------------------------------------------------------------------
# Pattern A — meter wraps a single SDK call
# ---------------------------------------------------------------------------


class TestPatternA:
    """Pattern A: caller passes ``_meter``; module calls
    ``meter.record(model, response.usage)`` after each SDK call.
    Verified through the receipts/extract surface."""

    def test_classify_batch_haiku_records_meter(self, monkeypatch):
        """receipts.extract.classify_batch_haiku records cost when given a meter."""
        from cfb_rankings.receipts import extract as receipts_extract

        # Ensure we stay on the Anthropic SDK path even if LOCAL_LLM_URL was
        # injected into os.environ by _load_dotenv() in a prior test.
        monkeypatch.delenv("LOCAL_LLM_URL", raising=False)

        # Mock the anthropic client + response.
        fake_resp = _fake_sdk_response(text='{"i":0,"is_prediction":false}',
                                       input_tokens=2000, output_tokens=400)
        mock_client = mock.MagicMock()
        mock_client.messages.create.return_value = fake_resp
        monkeypatch.setattr(receipts_extract, "_anthropic_client",
                            lambda: mock_client)
        monkeypatch.setattr(receipts_extract, "_have_anthropic", lambda: True)

        batch = [SimpleNamespace(
            sentence="Texas wins SEC", external_created_at_utc="2026-05-15T00:00:00Z",
        )]

        meter = CostMeter(ceiling_usd=5.0, label="test_pattern_a")
        _, tokens = receipts_extract.classify_batch_haiku(batch, _meter=meter)

        # The meter recorded one call (Haiku rates: 1 + 5 per Mtok).
        assert len(meter.records) == 1
        assert meter.records[0]["model"] == receipts_extract.HAIKU_MODEL
        # Expected cost = (2000 * 1e-6 * 1) + (400 * 1e-6 * 5) = $0.002 + $0.002 = $0.004
        assert 0.003 < meter.spent_usd < 0.005

    def test_classify_batch_haiku_uses_default_meter_when_omitted(
        self, monkeypatch,
    ):
        """When ``_meter`` is omitted the module creates its own per-call meter,
        so standalone calls still hard-fail on runaway spend."""
        from cfb_rankings.receipts import extract as receipts_extract

        # Ensure we stay on the Anthropic SDK path even if LOCAL_LLM_URL was
        # injected into os.environ by _load_dotenv() in a prior test.
        monkeypatch.delenv("LOCAL_LLM_URL", raising=False)

        fake_resp = _fake_sdk_response(text='{"i":0,"is_prediction":false}',
                                       input_tokens=100, output_tokens=10)
        mock_client = mock.MagicMock()
        mock_client.messages.create.return_value = fake_resp
        monkeypatch.setattr(receipts_extract, "_anthropic_client",
                            lambda: mock_client)
        monkeypatch.setattr(receipts_extract, "_have_anthropic", lambda: True)

        batch = [SimpleNamespace(
            sentence="x", external_created_at_utc="2026-05-15T00:00:00Z",
        )]
        # No meter passed — default created internally; should not raise.
        _claims, tokens = receipts_extract.classify_batch_haiku(batch)
        # Sanity check: token reporting still works.
        assert tokens["input_tokens"] == 100


# ---------------------------------------------------------------------------
# Pattern B — meter wraps a generate_with_voice_check call
# ---------------------------------------------------------------------------


class TestPatternB:
    """Pattern B: synthesizer wraps gwvc; meter.record reads tokens_used dict.
    Verified through daily/synthesizer + mailbag/synthesizer."""

    def test_daily_synthesize_takes_records_per_take(self, monkeypatch):
        """Pattern B records one entry per LIVE generate_with_voice_check call."""
        from cfb_rankings.daily import synthesizer as daily_synth

        # Stub bundle that's harmless for the synth loop.
        bundle = SimpleNamespace(
            edition_date="2026-05-15",
            wire_candidates=[],
            thread_candidates=[],
            pulse_spikes=[],
            resolved_receipts=[],
        )

        # Mock is_tentpole + generate_with_voice_check used by synth.
        monkeypatch.setattr(daily_synth, "is_tentpole", lambda _: False)
        called = {"n": 0}

        def fake_gwvc(*args, **kwargs):
            called["n"] += 1
            return _fake_gwvc_result(
                text=f"Headline {called['n']}\n\nbody text mentions The Athletic and ESPN.",
                in_toks=500, out_toks=200,
            )

        # Patch the lazy import inside synthesize_takes.
        from cfb_rankings import llm_runtime
        monkeypatch.setattr(llm_runtime, "generate_with_voice_check", fake_gwvc)

        meter = CostMeter(ceiling_usd=5.0, label="test_pattern_b")
        results = daily_synth.synthesize_takes(bundle, _meter=meter)

        # 3 takes generated, 3 records on meter (Pattern B fires per take).
        assert called["n"] == 3
        assert len(meter.records) == 3
        assert len(results) == 3
        # All recorded against Sonnet at the standard input/output rates.
        # Each call: 500 * $3/M + 200 * $15/M = $0.0015 + $0.003 = $0.0045
        per_call = (500 * 3.0 + 200 * 15.0) / 1_000_000
        assert abs(meter.spent_usd - 3 * per_call) < 1e-6

    def test_daily_synthesize_takes_skips_offline_stub(self, monkeypatch):
        """offline-stub results should NOT register against the meter
        — there's no real spend to count."""
        from cfb_rankings.daily import synthesizer as daily_synth
        from cfb_rankings import llm_runtime

        bundle = SimpleNamespace(
            edition_date="2026-05-15",
            wire_candidates=[],
            thread_candidates=[],
            pulse_spikes=[],
            resolved_receipts=[],
        )
        monkeypatch.setattr(daily_synth, "is_tentpole", lambda _: False)

        def fake_gwvc(*args, **kwargs):
            return _fake_gwvc_result(text="", in_toks=0, out_toks=0,
                                    model="offline-stub", mode="offline-stub")

        monkeypatch.setattr(llm_runtime, "generate_with_voice_check", fake_gwvc)

        meter = CostMeter(ceiling_usd=1.0, label="test_pattern_b_offline")
        daily_synth.synthesize_takes(bundle, _meter=meter)
        assert meter.records == []
        assert meter.spent_usd == 0.0


# ---------------------------------------------------------------------------
# Pattern C — workflow entry point: one meter shared across N calls
# ---------------------------------------------------------------------------


class TestPatternC:
    """Pattern C: a single workflow-level meter is shared across many LLM
    calls; total spend rolls up into one bucket. Verified directly against
    CostMeter (since CLI dispatch construction is heavy to fake)."""

    def test_one_meter_records_N_calls_into_single_total(self):
        """Pattern C invariant: 5 calls → meter.records has length 5
        and ``spent_usd`` equals the sum of each call's compute_cost."""
        meter = CostMeter(ceiling_usd=10.0, label="test_pattern_c")
        per_call_cost = (1000 * 3.0 + 200 * 15.0) / 1_000_000  # Sonnet rates
        for i in range(5):
            cost = meter.record("claude-sonnet-4-6",
                               _fake_usage(input_tokens=1000, output_tokens=200),
                               note=f"call_{i}")
            assert abs(cost - per_call_cost) < 1e-9

        assert len(meter.records) == 5
        assert abs(meter.spent_usd - 5 * per_call_cost) < 1e-9
        summary = meter.summary()
        assert summary["call_count"] == 5
        assert summary["by_model"]["claude-sonnet-4-6"]["calls"] == 5


# ---------------------------------------------------------------------------
# Ceiling-breach propagation
# ---------------------------------------------------------------------------


class TestCeilingBreachPropagation:
    """Ensure ``CostCeilingExceeded`` raised inside any wired surface
    propagates out instead of being swallowed at the inner call site.
    GitHub #37686 is the horror story this prevents."""

    def test_daily_synthesizer_propagates_ceiling_exceeded(self, monkeypatch):
        """Daily's per-take loop must re-raise CostCeilingExceeded
        (it only swallows non-ceiling exceptions like Overloaded)."""
        from cfb_rankings.daily import synthesizer as daily_synth
        from cfb_rankings import llm_runtime

        bundle = SimpleNamespace(
            edition_date="2026-05-15",
            wire_candidates=[],
            thread_candidates=[],
            pulse_spikes=[],
            resolved_receipts=[],
        )
        monkeypatch.setattr(daily_synth, "is_tentpole", lambda _: False)

        def fake_gwvc(*args, **kwargs):
            # Returns enough tokens that the FIRST call eats more than ceiling.
            return _fake_gwvc_result(in_toks=100_000_000,
                                    out_toks=100_000_000)
        monkeypatch.setattr(llm_runtime, "generate_with_voice_check", fake_gwvc)

        # Ceiling intentionally below per-call cost.
        meter = CostMeter(ceiling_usd=0.01, label="test_ceiling_breach")
        with pytest.raises(CostCeilingExceeded):
            daily_synth.synthesize_takes(bundle, _meter=meter)

    def test_pattern_a_propagates_ceiling_exceeded(self, monkeypatch):
        """Pattern A modules: meter.record raises CostCeilingExceeded
        which must NOT be swallowed."""
        from cfb_rankings.receipts import extract as receipts_extract

        # Ensure we stay on the Anthropic SDK path even if LOCAL_LLM_URL was
        # injected into os.environ by _load_dotenv() in a prior test.
        monkeypatch.delenv("LOCAL_LLM_URL", raising=False)

        fake_resp = _fake_sdk_response(input_tokens=100_000_000,
                                       output_tokens=100_000_000)
        mock_client = mock.MagicMock()
        mock_client.messages.create.return_value = fake_resp
        monkeypatch.setattr(receipts_extract, "_anthropic_client",
                            lambda: mock_client)
        monkeypatch.setattr(receipts_extract, "_have_anthropic", lambda: True)

        batch = [SimpleNamespace(
            sentence="x", external_created_at_utc="2026-05-15T00:00:00Z",
        )]
        meter = CostMeter(ceiling_usd=0.001, label="test_ceiling_a")
        with pytest.raises(CostCeilingExceeded):
            receipts_extract.classify_batch_haiku(batch, _meter=meter)


# ---------------------------------------------------------------------------
# Meter shared across batch of N calls
# ---------------------------------------------------------------------------


class TestMeterSharedAcrossBatch:
    """The same meter instance can be passed through multiple synthesizer
    calls — total spend accumulates across them. This is the foundation
    for Pattern C workflow-level cost ceilings."""

    def test_meter_accumulates_across_separate_calls(self):
        """Sequence of meter.record() calls grows ``spent_usd`` monotonically."""
        meter = CostMeter(ceiling_usd=10.0, label="test_batch_share")
        # 3 Haiku calls + 2 Sonnet calls.
        for _ in range(3):
            meter.record("claude-haiku-4-5",
                        _fake_usage(input_tokens=100, output_tokens=50))
        for _ in range(2):
            meter.record("claude-sonnet-4-6",
                        _fake_usage(input_tokens=1000, output_tokens=200))

        haiku_cost = 3 * (100 * 1.0 + 50 * 5.0) / 1_000_000
        sonnet_cost = 2 * (1000 * 3.0 + 200 * 15.0) / 1_000_000
        expected = haiku_cost + sonnet_cost
        assert abs(meter.spent_usd - expected) < 1e-9
        assert len(meter.records) == 5

    def test_batch_discount_applied(self):
        """is_batch=True applies the 50% input/output discount per Anthropic
        pricing. Cache fields don't get the additional batch discount."""
        meter = CostMeter(ceiling_usd=10.0, label="test_batch_discount")
        usage = _fake_usage(input_tokens=1000, output_tokens=500)
        sync_cost = meter.compute_cost("claude-sonnet-4-6", usage, is_batch=False)
        batch_cost = meter.compute_cost("claude-sonnet-4-6", usage, is_batch=True)
        assert abs(batch_cost - 0.5 * sync_cost) < 1e-9


# ---------------------------------------------------------------------------
# Public API regression — _meter kwarg-only with None default
# ---------------------------------------------------------------------------


class TestPublicApiRegression:
    """Verify every wired surface keeps the same public API: ``_meter`` is
    a keyword-only argument that defaults to None. Standalone callers
    that don't know about CostMeter must still work."""

    @pytest.mark.parametrize("module_path,fn_name", [
        ("cfb_rankings.daily.synthesizer", "synthesize_takes"),
        ("cfb_rankings.mailbag.synthesizer", "generate_answers_for_edition"),
        ("cfb_rankings.mailbag.synthesizer", "generate_answers_for_edition_batch"),
        ("cfb_rankings.reactions.synthesizer", "generate_reaction"),
        ("cfb_rankings.reactions.synthesizer", "synthesize_reactions_batch"),
        ("cfb_rankings.team_pages.pulse_lede", "generate_entity_lede"),
        ("cfb_rankings.team_pages.pulse_lede", "generate_entity_ledes_batch"),
        ("cfb_rankings.team_pages.pulse_themes", "extract_entity_themes"),
        ("cfb_rankings.team_pages.pulse_themes", "extract_entities_themes_batch"),
        ("cfb_rankings.team_pages.sentiment_classifier", "classify_player_targets"),
        ("cfb_rankings.team_pages.chronicle_generator", "write_cards_batch"),
        ("cfb_rankings.team_pages.chronicle_generator", "generate_chronicle_for_team"),
        ("cfb_rankings.team_pages.chronicle_generator", "generate_chronicle_for_teams_batch"),
        ("cfb_rankings.team_pages.narrative_generator", "generate_state_of_team"),
        ("cfb_rankings.team_pages.narrative_generator", "generate_state_of_team_post_game"),
        ("cfb_rankings.team_pages.narrative_generator", "_call_anthropic_sdk"),
        ("cfb_rankings.receipts.extract", "classify_batch_haiku"),
        ("cfb_rankings.receipts.extract", "review_batch_sonnet"),
        ("cfb_rankings.receipts.best_calls", "_llm_write"),
        ("cfb_rankings.receipts.source_profiles", "_voice_summary"),
        ("cfb_rankings.receipts.source_profiles", "recompute_all"),
        ("cfb_rankings.wire.editorial", "generate_uncovered_rows_batch"),
        ("cfb_rankings.canon.generator", "regenerate_entries_batch"),
    ])
    def test_wired_function_accepts_meter_kwarg(self, module_path, fn_name):
        """Every wired callable advertises a kwarg-only ``_meter``
        parameter defaulting to None."""
        import importlib
        import inspect

        mod = importlib.import_module(module_path)
        fn = getattr(mod, fn_name)
        sig = inspect.signature(fn)
        assert "_meter" in sig.parameters, (
            f"{module_path}.{fn_name} is missing `_meter` kwarg"
        )
        param = sig.parameters["_meter"]
        # Must be keyword-only and default to None.
        assert param.kind == inspect.Parameter.KEYWORD_ONLY, (
            f"{module_path}.{fn_name}._meter must be keyword-only "
            f"(found kind={param.kind})"
        )
        assert param.default is None, (
            f"{module_path}.{fn_name}._meter must default to None "
            f"(found {param.default!r})"
        )
