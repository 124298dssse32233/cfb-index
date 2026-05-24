"""Tests for cfb_rankings.chronicle.runtime."""
from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from cfb_rankings.chronicle.runtime import (
    BackendRoute,
    CardTier,
    GenerationConfig,
    GenerationError,
    GenerationResult,
    LLMBackend,
    NullBackend,
    Router,
    build_default_router,
    json_schema_to_grammar,
    parse_structured_response,
)


# ---------------------------------------------------------------------------
# GenerationConfig
# ---------------------------------------------------------------------------


def test_generation_config_defaults():
    c = GenerationConfig()
    assert c.max_tokens == 800
    assert 0 < c.temperature <= 1.0
    assert c.n_samples == 1
    assert c.json_schema is None
    assert c.stop == []


def test_generation_config_overrides():
    c = GenerationConfig(max_tokens=42, temperature=0.1, seed=7, stop=["</end>"])
    assert c.max_tokens == 42
    assert c.temperature == 0.1
    assert c.seed == 7
    assert c.stop == ["</end>"]


# ---------------------------------------------------------------------------
# NullBackend
# ---------------------------------------------------------------------------


class _Schema(BaseModel):
    name: str = "default"
    n: int = 0


def test_null_backend_generate():
    be = NullBackend(canned_response="hello world")
    out = be.generate("ignored", GenerationConfig())
    assert out.text == "hello world"
    assert out.backend == "null"
    assert out.finish_reason == "stop"


def test_null_backend_structured_with_defaults():
    be = NullBackend()
    instance, res = be.generate_structured("x", _Schema, GenerationConfig())
    assert isinstance(instance, _Schema)
    assert res.json_parsed == {"name": "default", "n": 0}


def test_null_backend_structured_required_fields():
    """Schemas with required fields should still work via model_construct."""

    class StrictSchema(BaseModel):
        required_field: str

    be = NullBackend()
    instance, res = be.generate_structured("x", StrictSchema, GenerationConfig())
    # No exception is the success condition
    assert isinstance(instance, StrictSchema)


def test_null_backend_health_and_cost():
    be = NullBackend()
    assert be.health_check() is True
    assert be.estimate_cost_usd(1000, 1000) == 0.0


# ---------------------------------------------------------------------------
# parse_structured_response
# ---------------------------------------------------------------------------


def test_parse_structured_clean_json():
    inst = parse_structured_response('{"name": "Cam", "n": 12}', _Schema)
    assert inst.name == "Cam"
    assert inst.n == 12


def test_parse_structured_code_fence():
    text = "Sure thing!\n```json\n{\"name\": \"Cam\", \"n\": 12}\n```\nLet me know."
    inst = parse_structured_response(text, _Schema)
    assert inst.name == "Cam"


def test_parse_structured_trailing_prose():
    text = '{"name": "Cam", "n": 12}\n\nNotes: lorem ipsum.'
    inst = parse_structured_response(text, _Schema)
    assert inst.n == 12


def test_parse_structured_leading_whitespace():
    text = "\n\n  {\"name\": \"a\", \"n\": 1}  "
    inst = parse_structured_response(text, _Schema)
    assert inst.name == "a"


def test_parse_structured_empty_raises():
    with pytest.raises(GenerationError):
        parse_structured_response("", _Schema)


def test_parse_structured_invalid_raises():
    with pytest.raises(GenerationError):
        parse_structured_response("this is not json at all", _Schema)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


def test_router_select_picks_role_and_tier():
    a = NullBackend(model_id="a")
    b = NullBackend(model_id="b")
    routes = [
        BackendRoute(backend=a, role="writer", tier_eligible=[CardTier.S, CardTier.T1]),
        BackendRoute(backend=b, role="writer", tier_eligible=[CardTier.T2, CardTier.T3]),
        BackendRoute(backend=a, role="planner", tier_eligible=list(CardTier)),
    ]
    r = Router(routes)
    assert r.select(CardTier.S, "writer").model_id == "a"
    assert r.select(CardTier.T3, "writer").model_id == "b"
    assert r.select(CardTier.T2, "planner").model_id == "a"


def test_router_no_match_raises():
    r = Router([])
    with pytest.raises(GenerationError):
        r.select(CardTier.S, "writer")


def test_build_default_router_no_cloud_no_localserver():
    """When llama-server isn't running and cloud is disabled, every role is
    serviceable (falls back to NullBackend)."""
    router = build_default_router(allow_cloud=False)
    for tier in CardTier:
        for role in ("writer", "planner", "critic"):
            be = router.select(tier, role)
            assert isinstance(be, LLMBackend)


# ---------------------------------------------------------------------------
# GBNF grammar
# ---------------------------------------------------------------------------


def test_json_schema_to_grammar_primitives():
    schema = {"type": "object", "properties": {"x": {"type": "string"}}}
    g = json_schema_to_grammar(schema)
    assert "root" in g
    assert "string" in g  # canonical primitive defined
    assert "::=" in g


def test_json_schema_to_grammar_enum():
    schema = {"type": "object", "properties": {"verdict": {"enum": ["pass", "fail"]}}}
    g = json_schema_to_grammar(schema)
    assert '"pass"' in g
    assert '"fail"' in g


def test_json_schema_to_grammar_array():
    schema = {
        "type": "object",
        "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
    }
    g = json_schema_to_grammar(schema)
    assert "[" in g and "]" in g


def test_json_schema_to_grammar_nullable():
    schema = {
        "type": "object",
        "properties": {"opt": {"type": ["string", "null"]}},
    }
    g = json_schema_to_grammar(schema)
    assert "null" in g


# ---------------------------------------------------------------------------
# GenerationResult helpers
# ---------------------------------------------------------------------------


def test_generation_result_is_truncated():
    r = GenerationResult(
        text="...", tokens_in=10, tokens_out=10, wall_clock_ms=1,
        finish_reason="length", model_id="m", model_version="1", backend="b",
    )
    assert r.is_truncated is True

    r2 = GenerationResult(
        text="...", tokens_in=10, tokens_out=10, wall_clock_ms=1,
        finish_reason="stop", model_id="m", model_version="1", backend="b",
    )
    assert r2.is_truncated is False
