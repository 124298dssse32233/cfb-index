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
