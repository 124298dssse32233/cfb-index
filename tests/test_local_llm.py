"""Regression tests for the off-by-default local-LLM routing + provider.

These lock in the safety guarantees that matter most:
  - routing is OFF unless CFB_LOCAL_LLM is explicitly enabled (cloud unchanged);
  - only Haiku-tier models route local; Opus/Sonnet never do;
  - a down local server degrades to an offline-stub of the correct shape,
    never an exception, so a batch job can't be crashed by a dead endpoint.

No network and no API key required (the one transport test points at a dead
port and asserts graceful failure).
"""
from __future__ import annotations

import pytest

from cfb_rankings import local_llm
from cfb_rankings.llm_runtime import _maybe_local_model

_HAIKU = "claude-haiku-4-5-20251001"
_OPUS = "claude-opus-4-7"
_SONNET = "claude-sonnet-4-6"

_LOCAL_ENV = (
    "CFB_LOCAL_LLM", "CFB_LOCAL_LLM_MODEL", "CFB_LOCAL_LLM_ANTHROPIC_MODELS",
    "CFB_LOCAL_LLM_BASE_URL", "CFB_LOCAL_LLM_TEMPERATURE", "CFB_LOCAL_LLM_NO_THINK",
    "CFB_LOCAL_LLM_API_KEY", "CFB_LOCAL_LLM_TIMEOUT",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Every test starts from a pristine, routing-OFF environment."""
    for var in _LOCAL_ENV:
        monkeypatch.delenv(var, raising=False)
    yield


class TestRouting:
    def test_off_by_default(self):
        # No CFB_LOCAL_LLM → every model stays on the cloud path.
        assert _maybe_local_model(_HAIKU) is None
        assert _maybe_local_model(_OPUS) is None
        assert _maybe_local_model(_SONNET) is None

    def test_enabled_routes_only_haiku(self, monkeypatch):
        monkeypatch.setenv("CFB_LOCAL_LLM", "1")
        assert _maybe_local_model(_HAIKU) == "qwen3:8b"  # current-gen default
        assert _maybe_local_model(_OPUS) is None
        assert _maybe_local_model(_SONNET) is None

    @pytest.mark.parametrize("flag", ["1", "true", "yes", "on", "TRUE", "On"])
    def test_truthy_flag_values(self, monkeypatch, flag):
        monkeypatch.setenv("CFB_LOCAL_LLM", flag)
        assert _maybe_local_model(_HAIKU) == "qwen3:8b"

    @pytest.mark.parametrize("flag", ["0", "false", "no", "off", ""])
    def test_falsey_flag_values(self, monkeypatch, flag):
        monkeypatch.setenv("CFB_LOCAL_LLM", flag)
        assert _maybe_local_model(_HAIKU) is None

    def test_custom_model_tag(self, monkeypatch):
        monkeypatch.setenv("CFB_LOCAL_LLM", "1")
        monkeypatch.setenv("CFB_LOCAL_LLM_MODEL", "qwen3:14b")
        assert _maybe_local_model(_HAIKU) == "qwen3:14b"

    def test_allowlist_override(self, monkeypatch):
        monkeypatch.setenv("CFB_LOCAL_LLM", "1")
        monkeypatch.setenv("CFB_LOCAL_LLM_ANTHROPIC_MODELS", _SONNET)
        # Now only Sonnet routes local; Haiku falls back to cloud.
        assert _maybe_local_model(_SONNET) == "qwen3:8b"
        assert _maybe_local_model(_HAIKU) is None


class TestReasoningStrip:
    def test_strips_closed_think_block(self):
        assert local_llm._strip_reasoning('<think>reasoning</think>["positive"]') == '["positive"]'

    def test_case_insensitive_and_trims(self):
        assert local_llm._strip_reasoning("  <THINK>x\ny</THINK>\n  hi ") == "hi"

    def test_unclosed_think_falls_back_to_json(self):
        assert local_llm._strip_reasoning('<think>unclosed {"a":1}') == '{"a":1}'

    def test_plain_text_untouched(self):
        assert local_llm._strip_reasoning("plain text") == "plain text"


class TestConfigDefaults:
    def test_deterministic_and_no_think(self):
        cfg = local_llm._resolve_local_config()
        assert cfg["temperature"] == 0.0
        assert cfg["no_think"] is True
        assert cfg["base_url"] == "http://localhost:11434/v1"


class TestGracefulDegradation:
    def test_down_server_returns_offline_stub(self, monkeypatch):
        # Nothing is listening on this port → must NOT raise.
        monkeypatch.setenv("CFB_LOCAL_LLM_BASE_URL", "http://127.0.0.1:59999/v1")
        result = local_llm.generate_local("hello", model="qwen3:8b", max_retries=0)
        assert result["mode"] == "offline-stub"
        assert result["text"] is None
        # Shape parity with the cloud generate_with_voice_check contract.
        for key in ("text", "voice_validator_passed", "voice_violations",
                    "attempts", "tokens_used", "model_used", "mode"):
            assert key in result
        assert result["model_used"] == "local/qwen3:8b"

    def test_down_server_with_response_format_still_safe(self, monkeypatch):
        monkeypatch.setenv("CFB_LOCAL_LLM_BASE_URL", "http://127.0.0.1:59999/v1")
        result = local_llm.generate_local(
            "hi", model="qwen3:8b", max_retries=0,
            response_format={"type": "json_object"},
        )
        assert result["mode"] == "offline-stub"

    def test_health_check_graceful(self, monkeypatch):
        monkeypatch.setenv("CFB_LOCAL_LLM_BASE_URL", "http://127.0.0.1:59999/v1")
        health = local_llm.health_check()
        assert health["ok"] is False
        assert health["models"] is None
        assert health["error"]


class TestMaxTokensFloor:
    """A Haiku-tuned caller cap (e.g. 256) must be raised so local reasoning
    models have room for their stripped <think> pass plus the answer. Otherwise
    a 50-doc batch truncates to empty and every row silently skips."""

    @staticmethod
    def _capture_post(monkeypatch):
        captured: dict = {}

        class _Resp:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [{"message": {"content": '["positive"]'}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                }

        def _fake_post(url, headers=None, json=None, timeout=None):
            captured.update(json or {})
            return _Resp()

        import requests
        monkeypatch.setattr(requests, "post", _fake_post)
        # Keep the unit hermetic: no telemetry side effects, validator passes.
        monkeypatch.setattr("cfb_rankings.llm_runtime._emit_telemetry", lambda *a, **k: None)
        monkeypatch.setattr(
            "cfb_rankings.llm_runtime._load_validator",
            lambda: (lambda text, source=None: (True, [])),
        )
        return captured

    def test_small_cap_raised_to_default_floor(self, monkeypatch):
        captured = self._capture_post(monkeypatch)
        local_llm.generate_local("p", model="qwen3:8b", max_tokens=256, max_retries=0)
        assert captured["max_tokens"] >= 1024

    def test_floor_is_env_tunable(self, monkeypatch):
        monkeypatch.setenv("CFB_LOCAL_LLM_MIN_TOKENS", "2000")
        captured = self._capture_post(monkeypatch)
        local_llm.generate_local("p", model="qwen3:8b", max_tokens=256, max_retries=0)
        assert captured["max_tokens"] == 2000

    def test_large_cap_is_preserved(self, monkeypatch):
        captured = self._capture_post(monkeypatch)
        local_llm.generate_local("p", model="qwen3:8b", max_tokens=4000, max_retries=0)
        assert captured["max_tokens"] == 4000

    def test_reasoning_effort_default_none(self, monkeypatch):
        # The real off-switch for Qwen3-class thinking; defaults to disabling it.
        captured = self._capture_post(monkeypatch)
        local_llm.generate_local("p", model="qwen3:8b", max_retries=0)
        assert captured.get("reasoning_effort") == "none"

    def test_reasoning_effort_env_override(self, monkeypatch):
        monkeypatch.setenv("CFB_LOCAL_LLM_REASONING_EFFORT", "low")
        captured = self._capture_post(monkeypatch)
        local_llm.generate_local("p", model="qwen3:8b", max_retries=0)
        assert captured.get("reasoning_effort") == "low"

    def test_reasoning_effort_omitted_when_blank(self, monkeypatch):
        monkeypatch.setenv("CFB_LOCAL_LLM_REASONING_EFFORT", "")
        captured = self._capture_post(monkeypatch)
        local_llm.generate_local("p", model="qwen3:8b", max_retries=0)
        assert "reasoning_effort" not in captured

    def test_unsupported_field_falls_back_gracefully(self, monkeypatch):
        # A server that 400s on reasoning_effort must still succeed via the bare
        # payload — never hard-fail on an unsupported optional field.
        calls = {"payloads": []}

        class _Resp:
            def __init__(self, status):
                self.status_code = status

            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [{"message": {"content": '["positive"]'}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                }

        def _fake_post(url, headers=None, json=None, timeout=None):
            calls["payloads"].append(json or {})
            status = 400 if "reasoning_effort" in (json or {}) else 200
            return _Resp(status)

        import requests
        monkeypatch.setattr(requests, "post", _fake_post)
        monkeypatch.setattr("cfb_rankings.llm_runtime._emit_telemetry", lambda *a, **k: None)
        monkeypatch.setattr(
            "cfb_rankings.llm_runtime._load_validator",
            lambda: (lambda text, source=None: (True, [])),
        )
        result = local_llm.generate_local("p", model="qwen3:8b", max_retries=0)
        assert result["mode"] == "live"
        assert len(calls["payloads"]) == 2  # featured (400) then bare (200)
        assert "reasoning_effort" not in calls["payloads"][-1]
