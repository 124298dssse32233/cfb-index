# Chronicle Quality Proposal v2

Current as of May 24, 2026. This v2 keeps the editorial diagnosis and card-quality system from `CHRONICLE_QUALITY_PROPOSAL_v1.md`, then refines the operating model around your actual goal: use the strongest practical local LLM workflow on the Dell A1250 CU7265KF/32/1/5070H desktop, and spend paid API dollars only where they create visible Chronicle quality lift.

## 1. Executive Update

The v1 proposal was right about Chronicle's product problem: the pipeline must stop generating multiple paraphrases of the same evidence pool and start filling distinct editorial jobs. The May 24 refinement is about how to run that system economically and reliably.

The best workflow for this machine is not "all local" and not "all API." It is a tiered local-first production loop:

1. Deterministic DB retrieval, eligibility, evidence locking, and chart assembly stay in Python/SQLite.
2. Local small/mid LLMs handle planning, angle selection, JSON frame construction, first drafts, and most critique.
3. Paid APIs are reserved for high-leverage judgment: S-tier final critique, headline/body refinement on near-miss cards, and occasional adversarial QA for cards the system wants to feature.
4. Every model call, local or paid, must be metered in `llm_usage_log`, even if local cost is zero, so the system learns latency, failure rate, schema validity, and quality-per-token by model.

For your desktop, the default production lane should be Ollama because the repo already has an `OllamaBackend`, the backend supports structured JSON schemas, and it is the lowest-friction local daemon on Windows/consumer GPU setups. A llama.cpp `llama-server` lane should remain available for controlled batch runs and prompt-cache experiments, but it should not be a required health gate when Ollama is healthy.

## 2. Hardware Assumption

User-provided machine string:

```text
DELL A1250 CU7265KF/32/1/5070H
```

Operational interpretation:

| Component | Working assumption | Workflow implication |
|---|---|---|
| System RAM | 32 GB | Enough for Python build pipeline plus one local model server; not enough to treat CPU offload as free. |
| Storage | 1 TB class | Fine for several GGUF/Ollama model variants, logs, and cache. Keep model zoo disciplined. |
| GPU | RTX 5070-class / 5070H-class | Exact VRAM must be detected with `nvidia-smi`; do not hard-code desktop 5070 assumptions. |
| Best local model size | 7B to 14B quantized; occasional larger MoE only if benchmarked | Prefer models that fit cleanly in VRAM over larger models with heavy CPU offload. |
| Concurrency | 1 writer call at a time | Avoid model swapping and KV-cache pressure during weekly Chronicle runs. |

The workflow should probe live hardware at run time:

```bash
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader,nounits
```

Then set model policy from detected VRAM bands:

| Free VRAM at run start | Writer policy | Planner/critic policy |
|---:|---|---|
| < 10 GB | Use LKG/template or paid fallback only for required S cards | Local 4B-8B only |
| 10-14 GB | 7B-12B Q4 writer | 7B-8B Q4 planner |
| 14-18 GB | 12B-14B Q4/Q5 writer | 8B-14B Q4 planner, sequential |
| > 18 GB | Test 20B/27B quantized writer, but require measured quality lift | Planner can stay smaller |

## 3. May 24 Local LLM Research Synthesis

The community pattern across r/LocalLLaMA, r/ollama, and practical local-LLM tooling discussions is stable:

| Signal | What it means for Chronicle |
|---|---|
| Fit-in-VRAM beats maximum parameter count | A 12B/14B quantized model that stays on GPU will usually produce a better production workflow than a larger model that swaps or crawls. |
| Ollama is the ergonomic default | Use it for the normal Windows desktop workflow, model pulls, health checks, and structured JSON responses. |
| llama.cpp/llama-server is the control lane | Use it when prompt cache, grammar constraints, predictable ports, or low-level tuning matter more than convenience. |
| vLLM is a server-throughput lane | It is excellent for multi-request serving and guided decoding, but it is probably overkill for one desktop Chronicle batch unless the box is moved to a stable Linux/WSL production setup. |
| LM Studio is a manual evaluation lane | Useful for side-by-side model testing and prompt debugging, not the weekly automated path. |
| EXL2/tabbyAPI can be fast | Worth testing only after the Ollama/llama.cpp baseline is measured; operational simplicity matters more than peak tokens/sec for Chronicle. |
| Huge context windows are not free | KV cache consumes VRAM. Chronicle should pass tighter evidence bundles, not dump a 50-row page pool into every writer call. |
| Structured output still needs validation | Ollama, vLLM, OpenAI, and llama.cpp all support constrained/structured output patterns, but Chronicle should keep Pydantic validation and repair/retry as the real contract. |

Primary references checked on May 24, 2026:

- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs) and [Ollama generate API](https://docs.ollama.com/api/generate): `format` accepts JSON or a JSON schema; `keep_alive` controls model residency.
- [vLLM structured outputs](https://docs.vllm.ai/en/v0.9.2/features/structured_outputs.html): guided decoding supports JSON schema, regex, choices, and grammar through serving APIs.
- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs?api-mode=chat) and [OpenAI API pricing](https://platform.openai.com/docs/pricing/): useful for paid escalation, but prices and model names should remain config-driven.
- Recent community threads: [r/LocalLLaMA 2026 local setup thread](https://www.reddit.com/r/LocalLLaMA/comments/1th7f24/whats_your_current_local_llm_setup_in_2026/), [r/LocalLLaMA RTX 5070 thread](https://www.reddit.com/r/LocalLLaMA/comments/1qt3vbc/what_ai_to_run_on_rtx_5070/), [r/ollama 2026 setup guide thread](https://www.reddit.com/r/ollama/comments/1sibjph/my_2026_ollama_setup_guide_what_actually_works/), [r/ollama reliability thread](https://www.reddit.com/r/ollama/comments/1sjef91/has_anyone_actually_gotten_a_reliable_local_ai/).

Community evidence is not authoritative. It is useful for workflow heuristics, then Chronicle should validate those heuristics with its own benchmark harness on this exact desktop.

## 4. Recommended Local Stack

### Production Default: Ollama

Use Ollama as the normal Chronicle local backend.

Current repo alignment:

- `src/cfb_rankings/chronicle/runtime.py` already checks Ollama first in `build_default_router()`.
- Defaults are already sensible:
  - Writer: `mistral-nemo:12b-instruct-2407-q4_K_M`
  - Planner/critic: `qwen3:8b`
- `OllamaBackend.generate()` already passes a JSON schema through `format` when `GenerationConfig.json_schema` is set.
- `OllamaBackend` strips Qwen-style `<think>...</think>` blocks before JSON parsing.
- Local calls estimate cost as `$0.00`, which is correct for spend accounting, but they still need latency and token telemetry.

Recommended local model pulls:

```bash
ollama pull mistral-nemo:12b-instruct-2407-q4_K_M
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

Optional benchmark candidates, not defaults:

| Role | Candidate | Why test it | Caveat |
|---|---|---|---|
| Writer | Qwen 14B-class instruct quant | Often stronger instruction following than older 7B models | May pressure VRAM depending quant/context |
| Writer | Gemma 12B/27B-class quant | Strong prose in some local setups | 27B-class may be slow/offloaded on this machine |
| Planner | Qwen 8B/14B-class reasoning/instruct | Good JSON/planning behavior | Reasoning tags must be stripped or disabled |
| Embeddings | BGE-M3 or `nomic-embed-text` | Needed for duplicate/thesis detection | Verify local package/runtime path |
| Reranker | BGE reranker/base-class | Improves evidence selection before writing | Adds CPU/GPU time; keep optional |

### Control Lane: llama.cpp / llama-server

Keep llama.cpp as a second production-capable lane, especially for:

- GBNF/grammar experiments.
- Prompt-cache measurements.
- Stable per-role ports.
- Offline runs where you want fewer Ollama abstractions.

Suggested role ports:

| Port | Role | Model shape |
|---:|---|---|
| 8001 | Writer | Mistral Nemo / Qwen 14B-class GGUF Q4_K_M or Q5_K_M |
| 8002 | Planner/Critic | Qwen 8B-class GGUF Q4_K_M |

But it should be an alternative backend, not a hard dependency. Right now `.github/workflows/chronicle-weekly.yml` still fails preflight if `localhost:8001` and `localhost:8002` are not healthy, even though `runtime.py` prefers Ollama. That should be fixed.

### Manual Evaluation Lane: LM Studio

Use LM Studio for fast human model comparison, prompt trials, and "does this model feel better?" checks. Do not make it the Chronicle automation dependency unless it exposes a stable local API contract in your environment.

### Defer: vLLM/SGLang as Main Production

vLLM and SGLang are worth knowing, but the default for this project should not be a full serving stack. Chronicle is a batch editorial system on one desktop. The bottleneck is evidence assignment, duplicate avoidance, and quality gating more than multi-tenant serving throughput.

Revisit vLLM only if all are true:

1. The runner is stable under WSL/Linux CUDA.
2. The same model beats Ollama/llama.cpp on throughput without lowering schema-valid rate.
3. Weekly runs need concurrent request serving instead of sequential high-quality generation.

## 5. Chronicle Model Roles

Do not ask one model to do everything. Route by job.

| Role | Default model | Local or paid | Temperature | Output |
|---|---|---|---:|---|
| Evidence slotter | Python rules plus local embeddings | Local | n/a | Distinct evidence bundles |
| Planner | `qwen3:8b` | Local | 0.1-0.3 | JSON frame plan |
| Writer | `mistral-nemo:12b-instruct-2407-q4_K_M` | Local | 0.4-0.7 | 2-3 bounded variants |
| Fact critic | Python verifier plus local Qwen | Local | 0.0 | Pass/fail and cited claims |
| Voice critic | Local Qwen | Local | 0.1 | Slop flags, specificity score |
| Collision critic | Embeddings plus local critic | Local | 0.0 | Twin/reuse rejection |
| Refiner | Local writer first | Local | 0.3 | Tightened final copy |
| Premium critic | Frontier paid API | Paid, gated | 0.0-0.2 | Final judgment on S/T1 near-miss cards |
| Premium refiner | Frontier paid API | Paid, gated | 0.2-0.4 | One final pass for share-candidate cards |

The quality system should view paid APIs as editors and judges, not as the default drafting engine.

## 6. Paid API Policy

The right paid-API posture is "small, explicit, measured."

### Default budget

| Budget | Recommendation |
|---|---:|
| Soft weekly cap | `$5` |
| Hard weekly cap | `$20` |
| Hard daily cap | `$5` |
| Emergency run cap | manual override only |

### Allowed paid roles

Paid models should be allowed for:

- `premium_insight_critic`
- `premium_final_refiner`
- `adversarial_fact_review`
- `headline_body_polish` for homepage/featured cards

Paid models should not be used for:

- Bulk first drafts.
- T2/T3 routine recaps.
- Filling missing deterministic data.
- Rewriting every failed local draft.

### Escalation gate

Escalate a card to paid review only when all are true:

1. Card tier is S or T1, or the card is selected for homepage/social promotion.
2. Deterministic fact checks pass.
3. Duplicate/thesis collision checks pass.
4. Local insight quality score is in the salvage band, for example `0.62 <= IQS < 0.82`.
5. Weekly paid spend is below the soft cap, or the run has explicit override.

Do not pay to rescue a bad frame. If evidence is generic or duplicated, regenerate the frame locally instead.

### Provider routing

Keep provider/model names in config, not code. As of May 24, 2026, price and model catalogs are moving fast enough that Chronicle should not bake exact frontier model choices into source. The config should support:

```yaml
paid:
  enabled: true
  weekly_soft_cap_usd: 5.00
  weekly_hard_cap_usd: 20.00
  daily_hard_cap_usd: 5.00
  roles:
    premium_insight_critic:
      provider: openai
      model: ${CHRONICLE_PAID_CRITIC_MODEL}
      max_cards_per_run: 40
    premium_final_refiner:
      provider: openai
      model: ${CHRONICLE_PAID_REFINER_MODEL}
      max_cards_per_run: 20
```

The existing `DeepInfraBackend` remains useful as a continuity fallback because it is already wired in `runtime.py`. But for the quality plan, the important spend is not cheap bulk generation. It is targeted high-judgment review.

## 7. Required Repo Refinements

### 7.1 Fix workflow/backend mismatch

Current mismatch:

- `src/cfb_rankings/chronicle/runtime.py` prefers Ollama first.
- `.github/workflows/chronicle-weekly.yml` preflight hard-fails unless both `llama-server` ports are healthy.

Change preflight to accept one healthy backend per role:

| Role | Valid health paths |
|---|---|
| Writer | Ollama has writer model, or llama-server `:8001` healthy, or paid fallback explicitly allowed |
| Planner/Critic | Ollama has planner model, or llama-server `:8002` healthy |

Recommended check order:

```bash
curl -sf http://localhost:11434/api/tags
curl -sf http://localhost:8001/health
curl -sf http://localhost:8002/health
```

The workflow should fail only when no acceptable route exists for the requested tier.

### 7.2 Add router policy config

Add `config/chronicle_models.yml` or equivalent:

```yaml
hardware:
  detect_vram_with: nvidia-smi
  writer_concurrency: 1
  planner_concurrency: 1
  min_free_vram_mib:
    normal: 10000
    local_writer: 12000

local:
  backend_preference:
    - ollama
    - llama_server
    - deepinfra
    - null
  ollama:
    base_url: http://localhost:11434
    keep_alive: 20m
    writer:
      model: mistral-nemo:12b-instruct-2407-q4_K_M
      max_ctx: 8192
      max_tokens: 420
    planner:
      model: qwen3:8b
      max_ctx: 8192
      max_tokens: 650
  llama_server:
    writer_url: http://localhost:8001
    planner_url: http://localhost:8002

quality:
  local_variants_per_s_card: 3
  local_variants_per_t1_card: 2
  require_schema_valid: true
  require_fact_pass: true
  require_thesis_unique: true

paid:
  enabled: true
  weekly_soft_cap_usd: 5.00
  weekly_hard_cap_usd: 20.00
  allowed_roles:
    - premium_insight_critic
    - premium_final_refiner
```

Then make `build_default_router()` read a backend preference list instead of using only the current hard-coded order.

### 7.3 Make local runtime tunable

Expose these environment/config knobs:

| Setting | Purpose |
|---|---|
| `CHRONICLE_BACKEND_PREFERENCE` | Explicitly choose `ollama,llama_server,deepinfra,null`. |
| `CHRONICLE_OLLAMA_KEEP_ALIVE` | Avoid repeated model unload/reload during batch runs. |
| `CHRONICLE_OLLAMA_NUM_CTX` | Keep context bounded by evidence assignment. |
| `CHRONICLE_OLLAMA_NUM_GPU` | Optional GPU layer control if needed. |
| `CHRONICLE_WRITER_CONCURRENCY` | Keep writer at 1 on this desktop by default. |
| `CHRONICLE_PAID_WEEKLY_CAP_USD` | Hard guardrail for API spend. |
| `CHRONICLE_PAID_ALLOWED_ROLES` | Prevent accidental paid bulk drafting. |

### 7.4 Log local calls as first-class telemetry

Even local calls should write:

- `surface`
- `model_id`
- `backend`
- `input_tokens`
- `output_tokens`
- `latency_ms`
- `finish_reason`
- `json_valid`
- `retry_count`
- `loop_pattern`
- `critic_role`
- `cost_usd = 0.0`

This lets Chronicle answer the only question that matters: which local model actually produces the best valid card per minute on this machine?

### 7.5 Add benchmark harness

Add a benchmark subcommand:

```bash
python -m cfb_rankings.chronicle.run benchmark-models `
  --fixture-set chronicle_quality_50 `
  --models mistral-nemo:12b-instruct-2407-q4_K_M qwen3:8b `
  --roles writer planner critic `
  --variants 3
```

Measure:

| Metric | Why |
|---|---|
| JSON valid rate | Required for Planner/critic contracts |
| Fact pass rate | Prevents fluent wrong cards |
| Thesis uniqueness | Directly attacks v1 duplicate issue |
| Slop phrase rate | Measures voice drift |
| Latency/card | Determines weekly feasibility |
| Tokens/sec | Useful but secondary |
| Paid escalation rate | Shows whether local models are improving |
| Final keep rate | Best single measure |

The benchmark should use frozen fixtures from real bad cards: Alabama market-volume duplicates, Auburn generic recap, Kansas/Kansas State bleed, Arizona/Ty Simpson bleed, and 25-50 representative S/T1 teams.

## 8. Revised Chronicle Generation Loop

The proposed v2 loop:

```text
DB evidence retrieval
  -> deterministic evidence eligibility
  -> local embeddings / duplicate memory
  -> frame slot assignment
  -> local planner JSON
  -> schema validation
  -> local writer variants
  -> deterministic fact check
  -> local voice critic
  -> local collision critic
  -> local refiner
  -> paid critic/refiner only if gated
  -> final deterministic render
  -> telemetry + cache + LKG
```

Important change from v1: paid API does not replace the anti-dup architecture. Paid API sits after that architecture and reviews the few cards worth spending on.

## 9. Local Model Workflow for Your Desktop

### Daily/manual workflow

Use this when iterating prompts and cards:

1. Start Ollama.
2. Confirm models:

```bash
ollama list
curl http://localhost:11434/api/tags
```

3. Run a small Chronicle batch:

```bash
python -m cfb_rankings.chronicle.run generate --tier S --max-cards 5 --allow-cloud false
```

4. Review telemetry:

```sql
SELECT model_id, backend, COUNT(*) calls, AVG(latency_ms) avg_ms
FROM llm_usage_log
WHERE surface LIKE '%chronicle%'
GROUP BY model_id, backend
ORDER BY calls DESC;
```

5. Only after local outputs are schema-valid and non-duplicative, enable paid critique for a small S-tier sample.

### Weekly automated workflow

Use:

- Ollama as default.
- Writer concurrency 1.
- Planner/critic sequential unless benchmark proves safe.
- Paid critique capped and gated.
- LKG fallback for local outage.

The weekly workflow should never fail just because the optional llama.cpp lane is down while Ollama is healthy.

## 10. What Not To Do

Do not chase 70B-class local models on this machine for Chronicle production. CPU offload and swapping will turn the workflow into a latency problem without solving duplicate evidence framing.

Do not pay for all drafting. It creates spend without fixing the mechanical cause of repetitive cards.

Do not set maximum context by default. Chronicle should shrink the evidence bundle per card until each card has a specific evidence spine.

Do not treat Reddit/community model preferences as proof. Treat them as a candidate list, then run the repo benchmark on your actual workload.

Do not make vLLM the main path until it beats Ollama/llama.cpp on this machine with the same schema-valid rate and less operational friction.

## 11. Two-Week Implementation Plan

| Day | Work | Output |
|---:|---|---|
| 1 | Add hardware probe and backend-health matrix | Workflow knows Ollama vs llama-server vs paid availability |
| 2 | Fix `chronicle-weekly.yml` preflight mismatch | Ollama-first runs stop failing on missing llama-server |
| 3 | Add router policy config and env overrides | Backend/model choices move out of hard-coded defaults |
| 4 | Add local-call telemetry fields and dashboard query | Local models become measurable |
| 5 | Add benchmark fixture set from known bad cards | Repeatable local bakeoff |
| 6 | Run Ollama baseline: Mistral Nemo writer, Qwen planner | Baseline quality/latency report |
| 7 | Test one alternate writer and one alternate planner | Evidence-based model choice |
| 8 | Add paid escalation gate | API spend limited to high-value cards |
| 9 | Run S-tier paid critic pilot under `$5` cap | Measure lift vs local-only |
| 10 | Lock defaults and write operator runbook | Stable weekly workflow |

## 12. Final Recommendation

Adopt an Ollama-first, schema-validated, local telemetry-heavy Chronicle workflow immediately. Keep llama.cpp/llama-server as the controlled performance lane, but remove it as a mandatory preflight dependency. Use paid APIs as a scarce editorial layer for S/T1 cards after local evidence framing, fact checks, and duplicate checks already pass.

The practical target for this desktop is not to imitate a frontier-model newsroom. It is to build a disciplined local editorial machine that generates most cards for free, knows exactly when local quality is insufficient, and spends API dollars only on the few moments where better judgment is visible to readers.
