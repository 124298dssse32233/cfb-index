"""Chronicle LLM runtime.

Two-backend model:
  - LocalLlamaBackend: talks to llama-server over HTTP. Used for Tier S/T1
    where Voice LoRA + Antislop sampler must be applied.
  - DeepInfraBackend: hosted Mistral Nemo for Tier 2/3. Cheaper at scale, no
    Voice LoRA, but adequate for tail-end cards.
  - NullBackend: returns canned responses, for tests + --no-llm mode.

The Router picks backend based on (tier, role).

Prompt structure standardized:
  - System prompt: voice cues, card_type rubric, ban-list reminder
  - Evidence: <evidence source="..." trust="..."> blocks from wrap_evidence()
  - Narrative state: frame_stack + open_arcs + calendar_pressure (compressed)
  - Task: 1-shot instruction for the specific agent role (Planner / Writer / Critic)
  - Schema: Pydantic JSON schema for structured output

Caching strategy:
  - Stable prefix (system + voice cues) cached via llama-server's prompt cache
    (cache_prompt=true, n_keep spans the system block).
  - SHA-256 result cache via chronicle_card_cache table (per architecture v3).
  - Prefix cache target: 30-50% TTFT reduction on cache hits.
"""
from __future__ import annotations

import abc
import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ValidationError

log = logging.getLogger("cfb_rankings.chronicle.runtime")

T = TypeVar("T", bound=BaseModel)


# ---------------------------------------------------------------------------
# Tier enum
# ---------------------------------------------------------------------------


class CardTier(Enum):
    """Card-quality tier. Drives backend + agent-count selection."""

    S = "S"    # Top 25 players + top 10 teams. Full 5-agent + Best-of-3. Local + LoRA.
    T1 = "T1"  # Top 50 teams + top 100 players. Full single-pass. Local + LoRA.
    T2 = "T2"  # Rank 51-100. 3-agent. Cloud or local.
    T3 = "T3"  # Long tail. Template-fill. Qwen3-4B or cloud.


# ---------------------------------------------------------------------------
# Config / result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class GenerationConfig:
    """Per-call sampling + safety knobs."""

    max_tokens: int = 800
    temperature: float = 0.7
    top_p: float = 0.92
    top_k: int = 40
    min_p: float = 0.05
    repetition_penalty: float = 1.05
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    seed: int | None = None

    # Constrained decoding
    json_schema: dict | None = None
    grammar: str | None = None

    # Antislop integration (P2)
    antislop_banlist: list[str] | None = None
    antislop_severity: dict[str, float] | None = None
    logit_bias: dict[int, float] | None = None

    # Best-of-N
    n_samples: int = 1

    # Timeouts
    wall_clock_budget_s: float = 60.0

    # Stop sequences
    stop: list[str] = field(default_factory=list)


@dataclass
class GenerationResult:
    """Result of a single generation call."""

    text: str
    tokens_in: int
    tokens_out: int
    wall_clock_ms: int
    finish_reason: Literal["stop", "length", "error", "timeout"]
    model_id: str
    model_version: str
    backend: str
    cached_prefix: bool = False
    json_parsed: dict | None = None
    raw_response: dict = field(default_factory=dict)
    n_samples_used: int = 1

    @property
    def is_truncated(self) -> bool:
        return self.finish_reason == "length"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GenerationError(RuntimeError):
    """Raised on unrecoverable generation failures (after retries exhausted)."""


class GenerationTimeout(GenerationError):
    """Specific subclass for budget exceedance."""


# ---------------------------------------------------------------------------
# Structured-output helpers
# ---------------------------------------------------------------------------

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_FIRST_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_structured_response(text: str, schema_model: type[T]) -> T:
    """Extract first valid JSON object from text and validate against schema_model.

    Tolerates:
    - Leading/trailing whitespace
    - Code-fence wrapping (```json ... ```)
    - Trailing prose after the JSON object

    Raises GenerationError if no valid JSON can be extracted.
    """
    if not text or not text.strip():
        raise GenerationError("Empty response — cannot parse structured output")

    candidates: list[str] = []
    stripped = text.strip()

    # 1. Try fenced code blocks first
    for m in _JSON_FENCE_RE.finditer(stripped):
        candidates.append(m.group(1).strip())

    # 2. Try the full text as JSON
    candidates.append(stripped)

    # 3. Try the first {...} substring (greedy)
    m = _FIRST_OBJECT_RE.search(stripped)
    if m:
        candidates.append(m.group(0))

    last_err: Exception | None = None
    for candidate in candidates:
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_err = exc
            continue
        try:
            return schema_model.model_validate(data)
        except ValidationError as exc:
            last_err = exc
            continue

    raise GenerationError(
        f"Could not parse structured response against {schema_model.__name__}: {last_err}"
    )


# ---------------------------------------------------------------------------
# GBNF grammar generation from JSON schema
# ---------------------------------------------------------------------------


def json_schema_to_grammar(schema: dict) -> str:
    """Generate a llama.cpp GBNF grammar that constrains output to the JSON schema.

    Supports a useful subset:
    - object with required properties
    - string, integer, number, boolean, null
    - arrays of primitives
    - enums (string literals)
    - nullable types (anyOf/oneOf with null)

    Returns a GBNF string ready to pass to llama-server's `grammar` field.

    The grammar always defines the canonical primitives (ws, string, number, ...)
    and a `root` production matching the supplied schema.
    """
    rules: dict[str, str] = {}
    counter = [0]

    def fresh(prefix: str) -> str:
        counter[0] += 1
        return f"{prefix}-{counter[0]}"

    def emit(name: str, body: str) -> None:
        rules[name] = body

    def compile_node(node: dict, name_hint: str = "node") -> str:
        # Handle enum
        if "enum" in node:
            opts = " | ".join(json.dumps(v) for v in node["enum"] if isinstance(v, str))
            rule_name = fresh(name_hint)
            emit(rule_name, opts if opts else '"\\"\\"" ')
            return rule_name

        # Handle anyOf / oneOf — pick first non-null branch + allow null
        for key in ("anyOf", "oneOf"):
            if key in node:
                branches = node[key]
                rule_name = fresh(name_hint)
                branch_rules = []
                for b in branches:
                    if b.get("type") == "null":
                        branch_rules.append('"null"')
                    else:
                        branch_rules.append(compile_node(b, name_hint))
                emit(rule_name, " | ".join(branch_rules))
                return rule_name

        t = node.get("type")
        if isinstance(t, list):
            # ["string", "null"] etc.
            non_null = [x for x in t if x != "null"]
            allow_null = "null" in t
            if non_null:
                inner = compile_node({**node, "type": non_null[0]}, name_hint)
                if allow_null:
                    rule_name = fresh(name_hint)
                    emit(rule_name, f'{inner} | "null"')
                    return rule_name
                return inner
            return "null-lit"

        if t == "string":
            return "string"
        if t == "integer":
            return "integer"
        if t == "number":
            return "number"
        if t == "boolean":
            return "boolean"
        if t == "null":
            return "null-lit"

        if t == "array":
            items = node.get("items", {"type": "string"})
            item_rule = compile_node(items, name_hint + "-item")
            rule_name = fresh(name_hint + "-arr")
            emit(
                rule_name,
                f'"[" ws ( {item_rule} ( ws "," ws {item_rule} )* )? ws "]"',
            )
            return rule_name

        if t == "object" or "properties" in node:
            props = node.get("properties", {})
            required = node.get("required", [])
            rule_name = fresh(name_hint + "-obj")

            if not props:
                emit(rule_name, '"{" ws "}"')
                return rule_name

            pieces: list[str] = []
            for pname, pschema in props.items():
                prule = compile_node(pschema, pname)
                key_lit = json.dumps(pname)
                # In strict mode every property is emitted; required-aware would
                # explode rule count combinatorially. Keep simple.
                pieces.append(f'{key_lit} ws ":" ws {prule}')

            body = '"{" ws ' + ' ws "," ws '.join(pieces) + ' ws "}"'
            emit(rule_name, body)
            return rule_name

        # Fallback: accept any value
        return "value"

    # Canonical primitives
    emit("ws", "[ \\t\\n]*")
    emit("string", r'"\"" ( [^"\\] | "\\" ["\\/bfnrt] | "\\u" [0-9a-fA-F]{4} )* "\""')
    emit("integer", r'"-"? ( "0" | [1-9] [0-9]* )')
    emit("number", r'"-"? ( "0" | [1-9] [0-9]* ) ( "." [0-9]+ )? ( [eE] [-+]? [0-9]+ )?')
    emit("boolean", '"true" | "false"')
    emit("null-lit", '"null"')
    emit("value", "string | number | boolean | null-lit")

    root_rule = compile_node(schema, "root")
    emit("root", root_rule)

    # Render: sort so primitives come last for readability
    lines = [f"{name} ::= {body}" for name, body in rules.items()]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Backend abstract base
# ---------------------------------------------------------------------------


class LLMBackend(abc.ABC):
    """Abstract base for any inference backend."""

    name: str
    model_id: str
    model_version: str

    @abc.abstractmethod
    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult:
        ...

    @abc.abstractmethod
    def generate_structured(
        self, prompt: str, schema_model: type[T], config: GenerationConfig
    ) -> tuple[T, GenerationResult]:
        ...

    @abc.abstractmethod
    def health_check(self) -> bool:
        ...

    @abc.abstractmethod
    def estimate_cost_usd(self, tokens_in: int, tokens_out: int) -> float:
        ...


# ---------------------------------------------------------------------------
# LocalLlamaBackend — llama-server HTTP client
# ---------------------------------------------------------------------------


class LocalLlamaBackend(LLMBackend):
    """Connects to llama-server over HTTP.

    Defaults assume llama-server running at http://localhost:8001 for Writer
    (Mistral Nemo) and http://localhost:8002 for Planner/Critic (Qwen3-8B).
    Pass `port` to override.

    Implementation:
    - Uses httpx (sync). Lazy-imported inside __init__ so module-load is cheap.
    - POSTs /completion endpoint with the llama-server JSON shape:
      {prompt, n_predict, temperature, top_p, top_k, min_p, repeat_penalty,
       grammar, logit_bias, n_keep, cache_prompt: true, ...}
    - On JSON-mode (config.json_schema set), generates a GBNF grammar from
      the schema if config.grammar is not already set.
    - On Best-of-N (n_samples > 1), fires N requests with different seeds and
      returns the first non-error result (caller can pick a ranker if needed).
    - Retry: 3 attempts with exponential backoff + jitter. Honors
      wall_clock_budget_s as hard cap across all attempts.
    - health_check returns False (does not raise) on connection failure.
    - Cost is always 0.0 (local inference).
    """

    def __init__(
        self,
        model_id: str,
        port: int = 8001,
        host: str = "localhost",
        model_version: str = "unknown",
        voice_lora_path: str | None = None,
        timeout_s: float = 60.0,
    ):
        # Lazy import — avoids hard dep at module load time
        try:
            import httpx  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise GenerationError(
                "httpx is required for LocalLlamaBackend; install with `pip install httpx`"
            ) from exc

        self.model_id = model_id
        self.model_version = model_version
        self.port = port
        self.host = host
        self.voice_lora_path = voice_lora_path
        self.timeout_s = timeout_s
        self.name = f"llama-server@{host}:{port}"
        self._base_url = f"http://{host}:{port}"

    # ---- request building --------------------------------------------------

    def _build_payload(self, prompt: str, config: GenerationConfig) -> dict:
        payload: dict[str, Any] = {
            "prompt": prompt,
            "n_predict": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "top_k": config.top_k,
            "min_p": config.min_p,
            "repeat_penalty": config.repetition_penalty,
            "presence_penalty": config.presence_penalty,
            "frequency_penalty": config.frequency_penalty,
            "cache_prompt": True,
            "stream": False,
        }
        if config.seed is not None:
            payload["seed"] = config.seed
        if config.stop:
            payload["stop"] = list(config.stop)
        if config.grammar:
            payload["grammar"] = config.grammar
        elif config.json_schema:
            payload["grammar"] = json_schema_to_grammar(config.json_schema)
        if config.logit_bias:
            # llama-server expects [[token_id, bias], ...]
            payload["logit_bias"] = [[int(k), float(v)] for k, v in config.logit_bias.items()]
        return payload

    # ---- core generate -----------------------------------------------------

    def _single_request(
        self,
        prompt: str,
        config: GenerationConfig,
        deadline: float,
    ) -> GenerationResult:
        import httpx

        payload = self._build_payload(prompt, config)
        remaining = max(0.1, deadline - time.monotonic())
        t0 = time.monotonic()

        try:
            with httpx.Client(timeout=remaining) as client:
                resp = client.post(f"{self._base_url}/completion", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException as exc:
            raise GenerationTimeout(f"llama-server request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise GenerationError(f"llama-server HTTP error: {exc}") from exc

        wall_ms = int((time.monotonic() - t0) * 1000)
        text = data.get("content", "")
        # llama-server reports "stopped_eos" / "stopped_limit" / "stopped_word"
        stopped_limit = bool(data.get("stopped_limit"))
        finish: Literal["stop", "length", "error", "timeout"] = "length" if stopped_limit else "stop"

        # Token counts: llama-server returns tokens_evaluated + tokens_predicted
        tokens_in = int(data.get("tokens_evaluated", 0))
        tokens_out = int(data.get("tokens_predicted", 0))
        cached_prefix = bool(data.get("tokens_cached", 0)) and int(data.get("tokens_cached", 0)) > 0

        return GenerationResult(
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            wall_clock_ms=wall_ms,
            finish_reason=finish,
            model_id=self.model_id,
            model_version=self.model_version,
            backend=self.name,
            cached_prefix=cached_prefix,
            raw_response=data,
        )

    def _with_retries(
        self, prompt: str, config: GenerationConfig
    ) -> GenerationResult:
        deadline = time.monotonic() + config.wall_clock_budget_s
        last_err: Exception | None = None
        for attempt in range(3):
            if time.monotonic() >= deadline:
                raise GenerationTimeout(
                    f"Wall-clock budget {config.wall_clock_budget_s}s exhausted"
                )
            try:
                return self._single_request(prompt, config, deadline)
            except GenerationTimeout:
                raise
            except GenerationError as exc:
                last_err = exc
                backoff = min(2.0 ** attempt + random.random() * 0.5, 5.0)
                log.warning(
                    "LocalLlamaBackend attempt %d failed (%s); sleeping %.1fs",
                    attempt + 1, exc, backoff,
                )
                time.sleep(backoff)
        raise GenerationError(f"LocalLlamaBackend exhausted retries: {last_err}")

    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult:
        if config.n_samples <= 1:
            return self._with_retries(prompt, config)

        # Best-of-N: vary the seed; return the first successful one
        results: list[GenerationResult] = []
        base_seed = config.seed if config.seed is not None else 0
        last_err: Exception | None = None
        for i in range(config.n_samples):
            sub = GenerationConfig(**{**config.__dict__, "n_samples": 1, "seed": base_seed + i})
            try:
                results.append(self._with_retries(prompt, sub))
            except GenerationError as exc:
                last_err = exc
                continue
        if not results:
            raise GenerationError(f"Best-of-N produced zero results: {last_err}")
        best = results[0]
        best.n_samples_used = len(results)
        return best

    def generate_structured(
        self,
        prompt: str,
        schema_model: type[T],
        config: GenerationConfig,
    ) -> tuple[T, GenerationResult]:
        # Inject schema -> grammar
        schema = schema_model.model_json_schema()
        cfg = GenerationConfig(**{**config.__dict__, "json_schema": schema})
        result = self.generate(prompt, cfg)
        parsed = parse_structured_response(result.text, schema_model)
        result.json_parsed = parsed.model_dump()
        return parsed, result

    def health_check(self) -> bool:
        try:
            import httpx
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"{self._base_url}/health")
                return resp.status_code == 200
        except Exception as exc:
            log.debug("LocalLlamaBackend health_check failed: %s", exc)
            return False

    def estimate_cost_usd(self, tokens_in: int, tokens_out: int) -> float:
        return 0.0


# ---------------------------------------------------------------------------
# DeepInfraBackend — hosted Mistral Nemo
# ---------------------------------------------------------------------------


class DeepInfraBackend(LLMBackend):
    """Hosted Mistral Nemo via DeepInfra OpenAI-compatible API.

    Pricing as of May 2026: $0.02 / 1M input tokens, $0.04 / 1M output tokens.
    API key from env DEEPINFRA_API_KEY.
    """

    PRICE_IN_PER_1M = 0.02
    PRICE_OUT_PER_1M = 0.04
    BASE_URL = "https://api.deepinfra.com/v1/openai"

    def __init__(
        self,
        model_id: str = "mistralai/Mistral-Nemo-Instruct-2407",
        model_version: str = "2407",
        api_key: str | None = None,
        timeout_s: float = 60.0,
    ):
        try:
            import httpx  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise GenerationError(
                "httpx is required for DeepInfraBackend; install with `pip install httpx`"
            ) from exc
        self.model_id = model_id
        self.model_version = model_version
        self.api_key = api_key or os.environ.get("DEEPINFRA_API_KEY", "")
        self.timeout_s = timeout_s
        self.name = f"deepinfra:{model_id}"

    def _build_messages(self, prompt: str) -> list[dict]:
        # We pass the entire prompt as a single user message — system prompt
        # is prepended in the caller via prompts.py.
        return [{"role": "user", "content": prompt}]

    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult:
        import httpx

        if not self.api_key:
            raise GenerationError("DEEPINFRA_API_KEY not set")

        body: dict[str, Any] = {
            "model": self.model_id,
            "messages": self._build_messages(prompt),
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "presence_penalty": config.presence_penalty,
            "frequency_penalty": config.frequency_penalty,
            "stream": False,
        }
        if config.seed is not None:
            body["seed"] = config.seed
        if config.stop:
            body["stop"] = list(config.stop)
        if config.json_schema:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "card", "schema": config.json_schema, "strict": True},
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        t0 = time.monotonic()
        try:
            with httpx.Client(timeout=config.wall_clock_budget_s) as client:
                resp = client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=headers,
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException as exc:
            raise GenerationTimeout(f"DeepInfra request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise GenerationError(f"DeepInfra HTTP error: {exc}") from exc

        wall_ms = int((time.monotonic() - t0) * 1000)
        choices = data.get("choices") or []
        if not choices:
            raise GenerationError(f"DeepInfra returned no choices: {data}")
        msg = choices[0].get("message", {}) or {}
        text = msg.get("content", "")
        finish_reason_raw = choices[0].get("finish_reason", "stop")
        finish: Literal["stop", "length", "error", "timeout"] = (
            "length" if finish_reason_raw == "length" else "stop"
        )
        usage = data.get("usage", {}) or {}
        return GenerationResult(
            text=text,
            tokens_in=int(usage.get("prompt_tokens", 0)),
            tokens_out=int(usage.get("completion_tokens", 0)),
            wall_clock_ms=wall_ms,
            finish_reason=finish,
            model_id=self.model_id,
            model_version=self.model_version,
            backend=self.name,
            raw_response=data,
        )

    def generate_structured(
        self,
        prompt: str,
        schema_model: type[T],
        config: GenerationConfig,
    ) -> tuple[T, GenerationResult]:
        schema = schema_model.model_json_schema()
        cfg = GenerationConfig(**{**config.__dict__, "json_schema": schema})
        result = self.generate(prompt, cfg)
        parsed = parse_structured_response(result.text, schema_model)
        result.json_parsed = parsed.model_dump()
        return parsed, result

    def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            import httpx
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return resp.status_code == 200
        except Exception as exc:
            log.debug("DeepInfraBackend health_check failed: %s", exc)
            return False

    def estimate_cost_usd(self, tokens_in: int, tokens_out: int) -> float:
        return (
            tokens_in * self.PRICE_IN_PER_1M + tokens_out * self.PRICE_OUT_PER_1M
        ) / 1_000_000


# ---------------------------------------------------------------------------
# OllamaBackend — local Ollama server (OpenAI-compatible API at :11434/v1)
# ---------------------------------------------------------------------------


class OllamaBackend(LLMBackend):
    """Ollama backend — talks to local Ollama daemon at http://localhost:11434.

    Uses Ollama's OpenAI-compatible API at /v1/chat/completions. No auth needed.
    Most ergonomic local-LLM path on Windows; Ollama auto-manages model loading,
    GPU offload, and inter-model swap.

    Model IDs should match the Ollama registry name, e.g. "mistral-nemo:12b-instruct-2407-q4_K_M"
    or "qwen3:8b". List available via `ollama list`.

    Set `keep_alive` (str like "10m", "-1" for infinite, "0" for unload-after-call)
    to control how long Ollama keeps the model resident in VRAM.
    """

    BASE_URL = "http://localhost:11434"

    def __init__(
        self,
        model_id: str,
        model_version: str = "ollama",
        base_url: str | None = None,
        timeout_s: float = 120.0,
        keep_alive: str = "10m",
    ):
        try:
            import httpx  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise GenerationError(
                "httpx is required for OllamaBackend; install with `pip install httpx`"
            ) from exc
        self.model_id = model_id
        self.model_version = model_version
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.timeout_s = timeout_s
        self.keep_alive = keep_alive
        self.name = f"ollama:{model_id}"

    def _build_messages(self, prompt: str) -> list[dict]:
        return [{"role": "user", "content": prompt}]

    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult:
        import httpx

        # Use Ollama's native /api/generate which:
        # 1. Has more reliable `format: "json"` support than OpenAI-shim response_format
        # 2. Honors all Ollama options (keep_alive, num_predict, etc.)
        # 3. Returns full prompt_eval_count / eval_count for accurate token accounting
        options: dict[str, Any] = {
            "temperature": config.temperature,
            "top_p": config.top_p,
            "top_k": config.top_k,
            "min_p": config.min_p,
            "repeat_penalty": config.repetition_penalty,
            "num_predict": config.max_tokens,
        }
        if config.seed is not None:
            options["seed"] = config.seed
        if config.stop:
            options["stop"] = list(config.stop)

        body: dict[str, Any] = {
            "model": self.model_id,
            "prompt": prompt,
            "stream": False,
            "options": options,
            "keep_alive": self.keep_alive,
        }
        # When constrained-decoding requested: use Ollama's native `format`
        # parameter — accepts "json" (free-form) or a full JSON schema dict.
        if config.json_schema:
            body["format"] = config.json_schema

        headers = {"Content-Type": "application/json"}

        t0 = time.monotonic()
        try:
            with httpx.Client(timeout=config.wall_clock_budget_s) as client:
                resp = client.post(
                    f"{self.base_url}/api/generate",
                    headers=headers,
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException as exc:
            raise GenerationTimeout(f"Ollama request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise GenerationError(f"Ollama HTTP error: {exc}") from exc

        wall_ms = int((time.monotonic() - t0) * 1000)
        text = data.get("response", "")
        # Strip Qwen3-style <think>...</think> reasoning blocks (they precede
        # the actual answer; for JSON output we need the bare JSON).
        if "<think>" in text and "</think>" in text:
            text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)
        done_reason = data.get("done_reason", "stop")
        finish: Literal["stop", "length", "error", "timeout"] = (
            "length" if done_reason == "length" else "stop"
        )
        return GenerationResult(
            text=text,
            tokens_in=int(data.get("prompt_eval_count", 0)),
            tokens_out=int(data.get("eval_count", 0)),
            wall_clock_ms=wall_ms,
            finish_reason=finish,
            model_id=self.model_id,
            model_version=self.model_version,
            backend=self.name,
            raw_response=data,
        )

    def generate_structured(
        self,
        prompt: str,
        schema_model: type[T],
        config: GenerationConfig,
    ) -> tuple[T, GenerationResult]:
        schema = schema_model.model_json_schema()
        cfg = GenerationConfig(**{**config.__dict__, "json_schema": schema})
        result = self.generate(prompt, cfg)
        parsed = parse_structured_response(result.text, schema_model)
        result.json_parsed = parsed.model_dump()
        return parsed, result

    def health_check(self) -> bool:
        try:
            import httpx
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                if resp.status_code != 200:
                    return False
                # Also verify the requested model is actually pulled
                data = resp.json()
                pulled_models = {m.get("name", "") for m in data.get("models", [])}
                # Accept exact match or prefix match (mistral-nemo:latest vs mistral-nemo:12b-...)
                base = self.model_id.split(":")[0]
                for m in pulled_models:
                    if m == self.model_id or m.startswith(f"{base}:"):
                        return True
                log.warning(
                    "Ollama is up but model %r not in pulled list. Pulled: %s",
                    self.model_id, sorted(pulled_models),
                )
                return False
        except Exception as exc:
            log.debug("OllamaBackend health_check failed: %s", exc)
            return False

    def estimate_cost_usd(self, tokens_in: int, tokens_out: int) -> float:
        return 0.0  # local inference, no API cost


# ---------------------------------------------------------------------------
# NullBackend — for tests + --no-llm mode
# ---------------------------------------------------------------------------


class NullBackend(LLMBackend):
    """Returns canned responses. For tests + --no-llm mode."""

    def __init__(
        self,
        canned_response: str = "[NULL BACKEND]",
        model_id: str = "null",
        model_version: str = "0.0.0",
    ):
        self.canned_response = canned_response
        self.model_id = model_id
        self.model_version = model_version
        self.name = "null"

    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult:
        return GenerationResult(
            text=self.canned_response,
            tokens_in=max(1, len(prompt) // 4),
            tokens_out=max(1, len(self.canned_response) // 4),
            wall_clock_ms=0,
            finish_reason="stop",
            model_id=self.model_id,
            model_version=self.model_version,
            backend="null",
        )

    def generate_structured(
        self,
        prompt: str,
        schema_model: type[T],
        config: GenerationConfig,
    ) -> tuple[T, GenerationResult]:
        # Try to build a zero-value instance; fall back to model_construct
        # which bypasses validation for schemas with required fields.
        try:
            instance = schema_model()
        except Exception:
            instance = schema_model.model_construct()
        result = self.generate(prompt, config)
        try:
            result.json_parsed = instance.model_dump()
        except Exception:
            result.json_parsed = {}
        return instance, result

    def health_check(self) -> bool:
        return True

    def estimate_cost_usd(self, tokens_in: int, tokens_out: int) -> float:
        return 0.0


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


@dataclass
class BackendRoute:
    """One row in the backend routing table."""

    backend: LLMBackend
    role: Literal["writer", "planner", "critic"]
    tier_eligible: list[CardTier]


class Router:
    """Selects backend by (tier, role).

    First matching route wins. If no route matches, raises GenerationError —
    callers should always ensure a NullBackend catch-all exists or call
    build_default_router which provides one.
    """

    def __init__(self, routes: list[BackendRoute]):
        self.routes = list(routes)

    def select(self, tier: CardTier, role: str) -> LLMBackend:
        for route in self.routes:
            if route.role == role and tier in route.tier_eligible:
                return route.backend
        raise GenerationError(
            f"No backend route for tier={tier.value} role={role!r}"
        )

    def add_route(self, route: BackendRoute) -> None:
        self.routes.append(route)


def build_default_router(allow_cloud: bool = True) -> Router:
    """Construct the canonical router for CFB Index.

    Backend preference order (per role):
      1. OllamaBackend (if Ollama daemon is running AND the model is pulled)
      2. LocalLlamaBackend (if llama-server is reachable on the expected port)
      3. DeepInfraBackend (cloud fallback, requires DEEPINFRA_API_KEY)
      4. NullBackend (graceful degradation, returns empty drafts)

    Ollama is checked first because it's the lowest-friction local path on
    Windows / consumer GPUs. If Ollama is present with the right models pulled,
    we don't even try llama-server.
    """
    # Preferred Ollama model IDs (override via env if user has different names)
    OLLAMA_WRITER_MODEL = os.environ.get(
        "CHRONICLE_OLLAMA_WRITER", "mistral-nemo:12b-instruct-2407-q4_K_M"
    )
    OLLAMA_PLANNER_MODEL = os.environ.get(
        "CHRONICLE_OLLAMA_PLANNER", "qwen3:8b"
    )

    def _maybe_ollama(model_id: str, mv: str) -> LLMBackend | None:
        try:
            be = OllamaBackend(model_id=model_id, model_version=mv)
        except GenerationError:
            return None
        if be.health_check():
            log.info("Using OllamaBackend for %s", model_id)
            return be
        return None

    def _maybe_llama_server(model_id: str, port: int, mv: str) -> LLMBackend | None:
        try:
            be = LocalLlamaBackend(model_id=model_id, port=port, model_version=mv)
        except GenerationError as exc:
            log.debug("LocalLlamaBackend(%s:%d) init failed: %s", model_id, port, exc)
            return None
        if be.health_check():
            log.info("Using LocalLlamaBackend (llama-server) for %s @ :%d", model_id, port)
            return be
        return None

    def _resolve_writer() -> LLMBackend:
        be = _maybe_ollama(OLLAMA_WRITER_MODEL, "2407")
        if be: return be
        be = _maybe_llama_server("mistral-nemo-12b-q5km", 8001, "2407")
        if be: return be
        log.warning("No local Writer backend — using NullBackend (install Ollama + pull %s)", OLLAMA_WRITER_MODEL)
        return NullBackend(model_id="writer-unavailable")

    def _resolve_planner() -> LLMBackend:
        be = _maybe_ollama(OLLAMA_PLANNER_MODEL, "3.0")
        if be: return be
        be = _maybe_llama_server("qwen3-8b-thinking-q4km", 8002, "3.0")
        if be: return be
        log.warning("No local Planner backend — using NullBackend (install Ollama + pull %s)", OLLAMA_PLANNER_MODEL)
        return NullBackend(model_id="planner-unavailable")

    writer_local = _resolve_writer()
    planner_local = _resolve_planner()

    routes: list[BackendRoute] = [
        BackendRoute(
            backend=writer_local, role="writer",
            tier_eligible=[CardTier.S, CardTier.T1],
        ),
        BackendRoute(
            backend=planner_local, role="planner",
            tier_eligible=[CardTier.S, CardTier.T1, CardTier.T2],
        ),
        BackendRoute(
            backend=planner_local, role="critic",
            tier_eligible=[CardTier.S, CardTier.T1, CardTier.T2],
        ),
    ]

    if allow_cloud and os.environ.get("DEEPINFRA_API_KEY"):
        try:
            cloud = DeepInfraBackend()
            routes.append(BackendRoute(
                backend=cloud, role="writer",
                tier_eligible=[CardTier.T2, CardTier.T3],
            ))
        except GenerationError as exc:
            log.warning("DeepInfra init failed: %s — falling back to local for T2/T3", exc)
            routes.append(BackendRoute(
                backend=writer_local, role="writer",
                tier_eligible=[CardTier.T2, CardTier.T3],
            ))
    else:
        # No cloud — local handles everything for writer
        routes.append(BackendRoute(
            backend=writer_local, role="writer",
            tier_eligible=[CardTier.T2, CardTier.T3],
        ))

    # T3 planner/critic = NullBackend (template-fill skips them)
    null_be = NullBackend()
    routes.append(BackendRoute(
        backend=null_be, role="planner",
        tier_eligible=[CardTier.T3],
    ))
    routes.append(BackendRoute(
        backend=null_be, role="critic",
        tier_eligible=[CardTier.T3],
    ))

    return Router(routes)


__all__ = [
    "CardTier",
    "GenerationConfig",
    "GenerationResult",
    "GenerationError",
    "GenerationTimeout",
    "LLMBackend",
    "LocalLlamaBackend",
    "OllamaBackend",
    "DeepInfraBackend",
    "NullBackend",
    "BackendRoute",
    "Router",
    "build_default_router",
    "parse_structured_response",
    "json_schema_to_grammar",
]
