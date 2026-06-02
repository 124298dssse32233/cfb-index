# Local-LLM Stack for the New 24/7 Box — Research + Plan

_Compiled 2026-06-02 for the CFB Index project. Audience: solo dev, newer to local-LLM / self-hosting._
_Two inputs: (1) an internal audit of how this repo uses LLMs today, (2) a deep web-research pass (110 agents, 27 sources, adversarial fact-check)._

> **Confidence labels used below**
> - ✅ **VERIFIED** — confirmed by the research pass against primary sources (vendor docs / GitHub).
> - 🔶 **WELL-ESTABLISHED** — strong community/expert consensus + my own knowledge, but the research's adversarial pass could *not independently confirm* it (the source blogs were low-quality or verifiers abstained). Treat as solid-but-check-at-install. NOT the same as "false."
> - ⚠️ **CONFIRM HANDS-ON** — genuinely uncertain or fast-moving; only the actual hardware + a live leaderboard at install time can answer.

> **OS CONFIRMED: Windows 11 (2026-06-02).** Good news for a beginner: the easy path (Ollama + LM Studio) is fully native on Windows — one-click installers, automatic NVIDIA GPU detection (your existing GeForce/Studio driver is all that's needed), OpenAI-compatible endpoint on `localhost:11434`. Two Windows-specific notes: (1) **24/7 boot-start** — the Ollama Windows app runs a background server while you're logged in; for true headless start-on-boot-without-login, wrap it with **NSSM** (free) or a **Task Scheduler** task (§6). (2) **The graduate-to vLLM path needs WSL2 or Docker** on Windows (it's Linux-oriented) — but you only touch that if Ollama's batch throughput isn't enough, so it's a later concern, not a day-one one.

---

## 0. The most important finding first: the cost premise

The whole goal was **"cut API cost."** Before anything else, two facts from the repo audit change how to think about that:

1. **A big chunk of editorial today runs through the Claude Code CLI, billed against your flat-rate Claude Max subscription — not metered per-token API.** The local cost log (`output/_logs/llm_usage_2026-04-25.jsonl`) shows calls tagged `claude-opus-4-7+claude-code` / `claude-sonnet-4-6+claude-code` at **$0.00** each, and the `llm_usage_log` SQL table is **empty** locally. Subscription calls don't save money by moving local — you pay the Max fee either way.
2. **The metered (pay-per-token) spend lives in your cloud GitHub Actions runs** (which use `ANTHROPIC_API_KEY`). That number is **not visible from this machine.** The source of truth is **console.anthropic.com → Usage/Billing**.

**Implication (⚠️ confirm with your Console number):** for a solo, modest-volume project, local models likely save **very little actual money**. The economics research backs this up:

> ✅ **Local-vs-API break-even is ~18–24 months only at TEAM scale (3–5M tokens/day).** Below roughly 500K–2M tokens/day, the API stays cheaper for a long time. The real win of going local is the **hybrid split**, not wholesale migration. _(SitePoint cost analysis, 2026 — single secondary source, directional only; its dollar figures assume an RTX 5090 + GPT-4.1, not your 3090 + Claude, so only the conclusion transfers.)_

**So reframe the project:** the honest reasons to stand up local models on this box are
- **Quota relief** — stop spending Max/cloud token budget on grunt work (sentiment labeling, theme tags, rule-checks).
- **Learning** — you wanted a local-LLM playground; this is it.
- **Privacy / independence** — data never leaves the box for the offloaded tasks.

…**not** primarily dollar savings. The box is already going to be on 24/7 for your ingest cadence, so the *marginal* cost of also serving local models is basically the GPU's power draw during scheduled batch jobs — negligible. **Go in for the right reasons and it's a clear win; go in expecting a big API bill to vanish and you'll be disappointed.**

---

## 1. What your code actually does with LLMs today (audit)

Everything is the Anthropic `anthropic` SDK → cloud Claude (Opus 4.7 / Sonnet 4.6 / Haiku 4.5). No provider abstraction, no `base_url` override, nothing local. The workloads split into exactly the two tiers we scoped:

| Tier | Surfaces | Shape | Local candidate? |
|---|---|---|---|
| **A — bulk / structured** | sentiment classification (~19k rows), theme extraction (JSON), critic/rule-check passes | high-volume, JSON-out, scheduled batch (daily/weekly), quality-tolerant, latency-insensitive | **YES — ideal** |
| **B — premium editorial** | cover essays (900–1300 wd), team narratives, mailbag, chronicle cards | voice-sensitive long-form, gated by critic loops + a strict regex voice-validator | **NO — keep on Claude** (see §3) |

The voice-validator and critic loops are **provider-agnostic** (regex + prompts), so they keep working no matter which model generates the text. That's convenient: you can point Tier-A at a local model and the existing quality gates still apply.

---

## 2. The recommended architecture (✅ this is 2026 consensus)

> ✅ **The recommended pattern is a HYBRID split: run predictable, high-volume Tier-A work on the local 3090, keep voice-sensitive Tier-B editorial on a frontier cloud API like Claude.** Corroborated across ~8 independent sources; reported 40–70% cost savings vs all-cloud *at volume*; canonical stack is **LiteLLM + Ollama/vLLM + a frontier provider.** This maps exactly onto Tier-A-local / Tier-B-Claude.

```
                ┌─────────────────────────────────────────────┐
   batch jobs   │  THE NEW 24/7 BOX (Ryzen 9 9900X / 3090 24GB)│
   (daily/      │                                             │
    weekly)     │   Ollama  ──serves──>  small/mid model      │
   ───────────► │   :11434/v1            (Tier-A: classify,   │
                │   (OpenAI-compatible)   theme, critic)       │
                └─────────────────────────────────────────────┘
   editorial
   (cover essays,        ──────────────►  Claude API (Tier-B, unchanged)
    narratives, etc.)
```

---

## 3. The honest Tier-B verdict (⚠️ not benchmark-proven, but well-motivated)

**Keep ALL of your premium editorial on Claude.** The research could not find a verified head-to-head benchmark of the best 24GB-local model vs Claude Sonnet/Opus on voice-sensitive long-form, so I won't pretend there's a number. But two things point the same way:

- ✅ The verified hybrid consensus explicitly reserves frontier cloud models for *"nuanced instruction following and creative tasks where output quality is business-critical."* Your editorial — gated by a strict voice validator and multi-critic loops — is precisely that.
- 🔶 No 24GB-fittable open model (≈24–34B at Q4) matches Claude Sonnet, let alone Opus, on nuanced editorial voice. A good local 32B can produce competent prose, but it will fail a strict voice validator far more often, needing more revise loops — which erases the savings and adds latency.

**Where local *could* help Tier-B without owning the final voice:** generating cheap **first-draft raw material** or **idea/angle candidates** that Claude then refines, and running the **cheaper critic passes** (rule-checking is easier than voice-perfect generation). Optional, later.

**Decision (made — no testing loop):** Tier-B editorial stays on Claude, full stop. You don't want an A/B gate, and the call is clear without one: a 24GB-local model is a real step down on voice-sensitive long-form, and the metered spend it would displace there is small. If you're ever curious you can eyeball a local 32B draft informally, but nothing in the pipeline depends on it and there's no comparison you need to run.

---

## 4. Inference engine — what to install (🔶 well-established; research couldn't independently verify the comparison, but this is settled community knowledge)

> ✅ Updated 2026-06-02: the Ollama-native-Windows path and Qwen3 availability are confirmed by current sources and Ollama's own library. The exact tok/s numbers and the vLLM-needs-WSL2 detail are still worth confirming hands-on, but the headline recommendation (start on Ollama) is solid.

| Engine | Beginner-friendliness | OpenAI-compatible API? | 24/7 service | Windows | Quant formats | Verdict |
|---|---|---|---|---|---|---|
| **Ollama** | ★★★★★ easiest | ✅ yes (`/v1`, port 11434) | runs as background server | ✅ native Windows app | GGUF | **START HERE** |
| **LM Studio** | ★★★★★ GUI | ✅ yes (built-in server) | GUI app (less headless) | native Windows | GGUF (+MLX on Mac) | **GUI companion** for browsing/chatting |
| **llama.cpp** | ★★☆ raw | ✅ yes (`llama-server`) | manual | yes | GGUF | the engine *under* Ollama/LM Studio; skip directly unless tuning |
| **vLLM** | ★★☆ production-grade | ✅ yes | yes (Linux/Docker) | 🔶 via WSL2/Docker | AWQ/GPTQ/GGUF | **graduate-to** for high-throughput batch |
| **TabbyAPI / ExLlamaV2** | ★★☆ enthusiast | ✅ yes (port 5000) | yes | via WSL2/Docker | EXL2 | enthusiast tier; fast on single GPU |
| **KoboldCpp** | ★★★★ single-binary | partial | manual | yes | GGUF | popular for creative; not needed here |

**Primary recommendation: Ollama.** It's the lowest-friction path, exposes the OpenAI-compatible endpoint your pipeline needs, auto-detects the GPU, manages model loading/unloading (good for power — see §6), and pulls models with one command (`ollama pull <model>`).

**Graduate-to-later: vLLM (in WSL2 or Docker)** *only if* the 19k-row batch job is too slow on Ollama. vLLM's continuous batching is dramatically faster for many-prompts-at-once workloads — but it's Linux-oriented and more setup, so don't start there.

---

## 5. Models that fit 24GB VRAM (⚠️ CHECK A LIVE LEADERBOARD AT INSTALL TIME)

> ✅ **Updated 2026-06-02 with verified-live data.** I pulled the actual Ollama
> model library and Qwen's official docs today, so the tags below are **real and
> current**, not guesses. Ignore the "Qwen 3.6 / Gemma 4 / Mistral Small 4 /
> DeepSeek V4" names that float around SEO blogs — those don't match any
> official lineup and look AI-generated. The space still moves monthly, so a
> 60-second glance at **r/LocalLLaMA** or **ollama.com/library** at install time
> is worth it — but you can pull the models below today and they'll be solid.

**Tier-A (bulk / JSON / classification) — small & fast, tons of headroom on 24GB.** These are what the local routing uses by default:
- **`qwen3:8b`** (5.2 GB) — **the default.** Current-gen (Qwen3, Apache 2.0, May 2025 release), excellent instruction-following + JSON. Note: Qwen3 is a *hybrid-reasoning* model — `local_llm.py` disables thinking (`/no_think`) and strips any `<think>` block so you get clean labels.
- **`qwen3:4b`** (2.5 GB) — if you want maximum speed; plenty for 3-class sentiment.
- **`qwen3:14b`** (9.3 GB) — step up if 8B's label quality ever looks shaky.
- **`qwen2.5:7b`** (4.7 GB) — proven, *non*-reasoning fallback if Qwen3's thinking mode ever causes trouble; rock-solid at JSON.
- All of these run **fast** on a 3090 (small models are effectively instant for batch).

**Tier-B-ceiling (best quality that fits 24GB) — the strongest single-3090 models, if you ever experiment beyond Tier-A:**
- **`qwen3:32b`** (20 GB) — ✅ the 2026 consensus "best dense model that fits a 24GB card." Loads fully in VRAM at Q4 with ~3 GB left for context.
- **`qwen3:30b`** (19 GB, MoE, 256K context) — faster per token (only 3B active) and long-context; slightly less depth than the 32B dense. Good when speed/context matter.
- **`gemma3:27b`** (~17 GB) — Gemma 3, often singled out for **prose quality** + 128K context + multimodal; the one to try if you ever want local editorial *drafting*.
- ❌ **Llama 70B-class does NOT fit usefully on 24GB** (needs ~40 GB+ at Q4; partial CPU offload = 2–6 t/s). Skip it on the 3090.

**Quantization:** **Q4_K_M GGUF** remains the 2026 sweet spot for 24GB (~75% smaller than FP16, minimal quality loss; the consensus "gold standard"). Ollama's default tags already ship a sensible Q4 — e.g. `ollama pull qwen3:32b` lands ~20 GB without you specifying a quant.

**tok/s on a 3090 (current data, still verify yourself):** 2026 reports put a dense ~27–32B at Q4 around **~30–35 t/s** on a 3090 (one well-documented Qwen3-32B setup held ~35 t/s even at long context); some report lower (~12–15 t/s) at very long context or on heavier quants. Small Tier-A models (4–8B) hit **50–100+ t/s**. Either way it's fine for *batch* jobs where latency doesn't matter. Confirm on the box with `ollama run --verbose`.

---

## 6. Running it 24/7 (🔶 / ⚠️ — confirm operational details hands-on)

- **Idle behavior:** Ollama **unloads the model from VRAM after ~5 min idle** (`OLLAMA_KEEP_ALIVE`, set to `-1` to keep resident, or e.g. `30m`). So between scheduled jobs, idle VRAM ≈ 0 and the GPU idles low (~15–30W). The model loads on first request, serves the batch, then frees VRAM. **Ideal for your scheduled-batch pattern.**
- **Auto-start headless:** Ollama's Windows app starts a background server, but for **boot-start without logging in**, wrap it with **NSSM** (free, beginner-friendly) or a **Task Scheduler** task set to "run whether logged on or not." (AlwaysUp is a paid alternative — not needed.) ⚠️ Confirm the exact setup on the real machine.
- **3090 thermals / longevity (🔶):** 3090s are a homelab favorite for 24/7 inference. The standard move is to **power-limit** it (`nvidia-smi -pl 280` or so, from 350W) — you lose only a few % speed for a big drop in heat/power. Watch **GDDR6X memory temps** (they run hot); your LANCOOL 217 has fine airflow for it. The ROG Strix is a 3-fan card, well-cooled.
- **Electricity (⚠️ estimate):** the *box being on 24/7 at all* is the dominant cost — roughly **~80–120W idle → ~$10–18/month** at typical US rates, before any LLM work. Inference spikes the GPU to ~300–400W but only during batch jobs (minutes/day), adding pennies. **This idle baseline is the number to weigh against your (likely modest) API savings.**
- **When local actually saves money:** ✅ basically only at team-scale token volume. For you: treat the electricity as the cost of a learning playground + quota relief, not as a cost-saving investment.

---

## 7. Wiring it into your codebase (✅ verified — this is the strong, decision-ready part)

Your code uses the `anthropic` SDK with no provider switch. Two clean, beginner-friendly paths:

**Path 1 (simplest, 1-hop) — point the `openai` client straight at Ollama.**
> ✅ Ollama exposes an OpenAI-compatible endpoint at `http://localhost:11434/v1`. Use the `openai` Python client with that `base_url` and any dummy key.

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
resp = client.chat.completions.create(
    model="qwen3:8b",
    messages=[...],
    temperature=0,                                  # deterministic for classification
    response_format={"type": "json_object"},        # ask for constrained JSON
)
```

**Path 2 (unified gateway) — LiteLLM.**
> ✅ **LiteLLM gives one OpenAI-format interface to 100+ providers** (OpenAI, Anthropic, local Ollama/vLLM) — swap providers by changing a model string / `api_base`. _(Official GitHub + docs, confirmed 3-0.)_
> ✅ It routes to **local models** via `completion(model="ollama/qwen2.5", api_base="http://localhost:11434")`. _(Note: the param is literally `api_base`, not `base_url`.)_
> ✅ Its **Anthropic passthrough** lets you keep the official `anthropic` SDK and native request format by changing only `base_url` to `http://0.0.0.0:4000/anthropic` — so the existing Tier-B code barely changes. _(Confirmed 3-0; caveat: don't confuse the `/anthropic` passthrough with the separate `/v1/messages` unified endpoint, and the virtual-key auth setup is the usual stumbling block.)_

**This is already built — `src/cfb_rankings/local_llm.py` + a shim in `llm_runtime.py`.** The provider switch routes only Tier-A (Haiku-tier) traffic to the local endpoint when `CFB_LOCAL_LLM=1`; Tier-B stays on Anthropic untouched. The voice validator and critic loops sit downstream and don't care which backend produced the text.

**Coverage (verified by tracing every model call site):** the shim sits in `generate_with_voice_check`, so it auto-covers the sentiment classifier, theme-extraction Stage-1, the Haiku critic passes, `pulse_lede`, and the mailbag/daily Haiku paths. One Tier-A surface — the predictive-claims classifier in `receipts/extract.py` — used a *direct* `client.messages.create` call and so got the **same guarded shim added explicitly**. Every other direct-SDK call site (`best_calls`, `reactions`, `source_profiles`, `narrative_generator`, the Stage-2 review in `extract.py`) is Sonnet/Opus and correctly stays on Claude. Net: **all Haiku-tier work routes local; nothing else does.**

**JSON reliability (✅ much better in 2026, but still validate):**
> ✅ Constrained decoding is now standard: Ollama's `format` parameter (and the OpenAI `response_format`) maps a JSON schema to a token-level grammar, so the model is strongly steered to emit valid JSON. `local_llm.py` forwards an optional `response_format` and degrades gracefully if a server rejects it.
> ⚠️ **But Ollama's own docs still call it best-effort** (they recommend also grounding the schema in the prompt), and *reasoning* models can route output into a `<think>` block. So the provider takes belt-and-suspenders measures that need no tuning from you: **temperature 0**, **`/no_think` + `<think>`-stripping**, and the sentiment classifier's existing **regex fallback + skip-bad-rows**. Net: for the 19k-row job you get clean labels without a human in the loop, and any rare unparseable row is safely skipped (and retried next run), not crashed on.

---

## 8. Beginner-friendly extras (optional, "anything that makes sense")

- **Local coding assistant:** **Continue.dev** or **Cline** (VS Code extensions) pointed at a local model via Ollama. Best local coding model that fits 24GB: 🔶 **Qwen2.5-Coder-32B** (or current Qwen3-Coder). **Honest expectation:** great for autocomplete and small edits; it will **not** replace Claude Code for real multi-file work — keep Claude Code as your primary. Treat this as a fun, zero-marginal-cost autocomplete + a fallback when offline.
- **Chat UI:** ✅ **Open WebUI** (Docker, ChatGPT-like, talks to Ollama) for a polished local chat, or just use **LM Studio**'s built-in chat. Good for poking at models and prompt-testing.
- **Embeddings + simple RAG (✅ realistic for a beginner):** ✅ Open WebUI's **built-in RAG supports Ollama as the embedding engine** (Admin → Settings → Documents), so you can run fully-local embeddings with `ollama pull nomic-embed-text` (or `bge-m3`) — no API keys, no data leaving the box. Down the line this could power semantic search over your CFB corpus, but it's clearly optional/future. _(Caveat: changing the embedding model means re-indexing.)_

---

## 9. Bottom line — what I'd install, in order

_The code is already written and off-by-default. This is now an install-and-flip, not a build._

1. **Install Ollama** (native Windows installer). `ollama pull qwen3:8b`, then `ollama run qwen3:8b "say hi"` to confirm the 3090 is doing the work.
2. **Smoke-check the wiring (not an A/B):** `python tools/local_llm_check.py --sample 60`. It runs your real sentiment data through the local model and reports parseable-rate, label spread, and speed. Green → go.
3. **Flip it on:** add `CFB_LOCAL_LLM=1` (and optionally `CFB_LOCAL_LLM_MODEL=qwen3:8b`) to `.env`. Now Tier-A (sentiment + themes + critics — all Haiku-tier) runs local; Opus/Sonnet editorial stays on Claude automatically.
4. **Run the job:** `python manage.py classify-player-sentiment` — same command as always, now served locally.
5. **Harden for 24/7:** power-limit the 3090 (`nvidia-smi -pl 280`), set `OLLAMA_KEEP_ALIVE`, wrap `ollama serve` with NSSM/Task Scheduler for boot-start.
6. **Optional playground:** LM Studio or Open WebUI for chat; Qwen2.5-Coder-32B + Continue.dev for a local coding assistant; `nomic-embed-text` + Open WebUI for local RAG.
7. **Graduate-to (only if batch throughput is too slow):** vLLM in WSL2/Docker — same `CFB_LOCAL_LLM_BASE_URL`, just repoint it. No code change.

**And the one homework item that sizes the payoff:** pull your real metered spend from **console.anthropic.com → Usage**. If it's small, this is a quota-relief + learning project (still worth it — the box is on anyway); if it's surprisingly large, the offload math gets more interesting and we widen what runs local.

---

## 10. The few things only the real hardware can answer

These don't block anything — defaults are chosen and the code runs — they're just where measuring beats guessing:

1. ⚠️ **Real tok/s for `qwen3:32b` Q4 on your 3090** — current data says ~30–35 t/s but it varies with context/quant; `ollama run --verbose` settles it. (Tier-A 8B models will feel instant regardless.)
2. ⚠️ **Ollama as a boot service on Windows** — confirm it auto-starts headless or wrap with NSSM/Task Scheduler; measure idle VRAM/power + sustained-load GDDR6X temps.
3. ⚠️ **Whether a newer small model has landed** by install day — a 60-second look at `ollama.com/library` / r/LocalLLaMA; if so, just change `CFB_LOCAL_LLM_MODEL`.

_Sources of record: Ollama model library + structured-outputs docs and Qwen3 official docs (pulled 2026-06-02, used for the model tags/sizes), LiteLLM (GitHub + docs.litellm.ai), Open WebUI docs, plus 2026 community/benchmark write-ups for tok/s and the 24GB sweet-spot consensus (directional). The "Qwen 3.6 / Gemma 4 / DeepSeek V4 / Mistral Small 4" names seen in SEO blogs could not be matched to official lineups and were deliberately NOT used._
