"""Tests for the shared LLM runtime."""
from __future__ import annotations

import json
import logging
import os
from unittest import mock

import pytest

from cfb_rankings.llm_runtime import (
    DEFAULT_MODEL,
    generate_with_voice_check,
)


class TestOfflineFallback:
    """When no API key is set, the runtime returns mode='offline-stub'
    without raising. This is the contract every cron-driven caller relies on."""

    def test_no_api_key_returns_offline_stub(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # Patch AppConfig too so .env doesn't leak a key.
        with mock.patch("cfb_rankings.llm_runtime._resolve_api_key", return_value=None):
            result = generate_with_voice_check("write me something")
        assert result["mode"] == "offline-stub"
        assert result["text"] is None
        assert result["voice_validator_passed"] is False
        assert result["attempts"] == 0
        assert result["tokens_used"] == {"input": 0, "output": 0}
        assert result["model_used"] == DEFAULT_MODEL

    def test_no_api_key_strict_mode_raises(self):
        with mock.patch("cfb_rankings.llm_runtime._resolve_api_key", return_value=None):
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY not set"):
                generate_with_voice_check("write me something", fallback_to_offline=False)

    def test_sdk_init_failure_falls_back_when_allowed(self):
        """If the Anthropic SDK fails to construct (e.g. pydantic version
        mismatch), we still return offline-stub rather than raising."""
        with mock.patch("cfb_rankings.llm_runtime._resolve_api_key", return_value="sk-fake"):
            # Simulate the SDK raising something non-ImportError on init.
            fake_anthropic = mock.MagicMock()
            fake_anthropic.Anthropic.side_effect = RuntimeError("pydantic ConfigError")
            with mock.patch.dict("sys.modules", {"anthropic": fake_anthropic}):
                result = generate_with_voice_check("write me something")
        assert result["mode"] == "offline-stub"
        assert result["text"] is None


class TestVoiceRetryLoop:
    """When the LLM produces banned-phrase copy, the runtime retries once
    with rewrite guidance before giving up."""

    def _fake_message(self, text: str, in_toks: int = 100, out_toks: int = 200):
        """Construct a mock Anthropic Message-like object."""
        msg = mock.MagicMock()
        msg.content = [mock.MagicMock(text=text)]
        msg.usage = mock.MagicMock(input_tokens=in_toks, output_tokens=out_toks)
        return msg

    def test_voice_pass_first_try_returns_success(self):
        with mock.patch("cfb_rankings.llm_runtime._resolve_api_key", return_value="sk-fake"):
            fake_client = mock.MagicMock()
            fake_client.messages.create.return_value = self._fake_message(
                "Notre Dame is quietly high in the offseason."
            )
            fake_anthropic = mock.MagicMock()
            fake_anthropic.Anthropic.return_value = fake_client
            with mock.patch.dict("sys.modules", {"anthropic": fake_anthropic}):
                result = generate_with_voice_check("write a Pulse lede")
        assert result["mode"] == "live"
        assert result["voice_validator_passed"] is True
        assert result["attempts"] == 1
        assert result["tokens_used"] == {"input": 100, "output": 200}

    def test_voice_fail_then_pass_retries_once(self):
        """First response leaks a banned phrase; second response is clean."""
        bad = "The analytics-cohort and the casual-cohort disagree this week."
        good = "The stat crowd and regular fans disagree this week."
        with mock.patch("cfb_rankings.llm_runtime._resolve_api_key", return_value="sk-fake"):
            fake_client = mock.MagicMock()
            fake_client.messages.create.side_effect = [
                self._fake_message(bad),
                self._fake_message(good),
            ]
            fake_anthropic = mock.MagicMock()
            fake_anthropic.Anthropic.return_value = fake_client
            with mock.patch.dict("sys.modules", {"anthropic": fake_anthropic}):
                result = generate_with_voice_check("write something", max_retries=1)
        assert result["mode"] == "live"
        assert result["voice_validator_passed"] is True
        assert result["attempts"] == 2
        # Both calls happened.
        assert fake_client.messages.create.call_count == 2
        # The retry prompt should have included the rewrite guidance.
        retry_call = fake_client.messages.create.call_args_list[1]
        retry_prompt = retry_call.kwargs["messages"][0]["content"]
        assert "REJECT REASON" in retry_prompt

    def test_voice_fail_twice_returns_failure(self):
        bad = "The analytics-cohort dominates the discourse this week."
        with mock.patch("cfb_rankings.llm_runtime._resolve_api_key", return_value="sk-fake"):
            fake_client = mock.MagicMock()
            fake_client.messages.create.side_effect = [
                self._fake_message(bad),
                self._fake_message(bad),
            ]
            fake_anthropic = mock.MagicMock()
            fake_anthropic.Anthropic.return_value = fake_client
            with mock.patch.dict("sys.modules", {"anthropic": fake_anthropic}):
                result = generate_with_voice_check("write something", max_retries=1)
        assert result["voice_validator_passed"] is False
        assert "analytics-cohort" in result["voice_violations"]
        assert result["attempts"] == 2
        assert result["text"] == bad

    def test_empty_response_triggers_retry(self):
        with mock.patch("cfb_rankings.llm_runtime._resolve_api_key", return_value="sk-fake"):
            fake_client = mock.MagicMock()
            fake_client.messages.create.side_effect = [
                self._fake_message(""),
                self._fake_message("Notre Dame's offseason mood is steady."),
            ]
            fake_anthropic = mock.MagicMock()
            fake_anthropic.Anthropic.return_value = fake_client
            with mock.patch.dict("sys.modules", {"anthropic": fake_anthropic}):
                result = generate_with_voice_check("write something", max_retries=1)
        assert result["voice_validator_passed"] is True
        assert result["attempts"] == 2


class TestTelemetry:
    """A structured log line lands on every call so cost-sweep tooling can grep."""

    def test_offline_stub_emits_skip_event(self, caplog):
        caplog.set_level(logging.INFO, logger="cfb_rankings.llm_runtime.telemetry")
        with mock.patch("cfb_rankings.llm_runtime._resolve_api_key", return_value=None):
            generate_with_voice_check("hello")
        records = [r for r in caplog.records if "llm_runtime.event" in r.message]
        assert len(records) >= 1
        # Extract the JSON portion.
        msg = records[0].message
        payload = json.loads(msg.split("llm_runtime.event ", 1)[1])
        assert payload["event"] == "skip"
        assert payload["mode"] == "offline-stub"
        assert payload["reason"] == "no_api_key"
