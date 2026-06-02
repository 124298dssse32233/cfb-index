# Local-LLM Quickstart — day-one steps for the new box

_Companion to `local-llm-stack-2026-06.md`. The literal click-by-click for when the machine arrives._
_Everything here is OFF until you turn it on — installing it changes nothing about your current cloud jobs._
_Model tags verified against ollama.com on 2026-06-02. No A/B testing — just install, smoke-check, flip._

## What got pre-built (already in the repo)

| File | What it is |
|---|---|
| `src/cfb_rankings/local_llm.py` | Local-model provider. Talks to any OpenAI-compatible server (Ollama/LM Studio/vLLM). Returns the **exact** same result shape as the cloud path, so nothing downstream changes. Temperature 0, disables/strips reasoning `<think>` blocks, optional schema-constrained JSON, graceful offline-stub if the server's down. Uses `requests` (no new dependency). |
| `src/cfb_rankings/llm_runtime.py` (`_maybe_local_model` + a small shim) | The hybrid switch. **Off by default.** When enabled, routes only **Haiku-tier** calls (sentiment, themes, critics) to the local box. Opus/Sonnet editorial **always** stays on Claude. |
| `tools/local_llm_check.py` | Smoke check (NOT an A/B): runs your real sentiment data through the local model and reports parseable-rate, label spread, and speed, so you can confirm the setup works. Read-only. |

The switch is controlled entirely by environment variables — no code edits to turn it on/off:

| Env var | Default | Meaning |
|---|---|---|
| `CFB_LOCAL_LLM` | _(unset = OFF)_ | `1` to route Tier-A calls local |
| `CFB_LOCAL_LLM_MODEL` | `qwen3:8b` | the local model tag to serve |
| `CFB_LOCAL_LLM_BASE_URL` | `http://localhost:11434/v1` | Ollama's OpenAI endpoint |
| `CFB_LOCAL_LLM_TEMPERATURE` | `0` | deterministic — best for classification |
| `CFB_LOCAL_LLM_NO_THINK` | `1` | appends `/no_think` so Qwen3 skips its reasoning block |
| `CFB_LOCAL_LLM_ANTHROPIC_MODELS` | _(Haiku only)_ | comma-list to override which models route local |

---

## Step 1 — install Ollama (5 min)

Download the Windows installer from **ollama.com/download** and run it. It installs a background server on `http://localhost:11434` and auto-detects the RTX 3090 (your normal GeForce/Studio driver is all it needs). Confirm in a terminal:

```bash
ollama --version
```

## Step 2 — pull the Tier-A model (a few min, ~5 GB)

```bash
ollama pull qwen3:8b
ollama run qwen3:8b "Reply with one word: hello"   # sanity check, then /bye to exit
```

> Verified-current tags (2026-06-02): `qwen3:4b` (2.5 GB, fastest), `qwen3:8b` (5.2 GB, **default**), `qwen3:14b` (9.3 GB, more headroom), `qwen3:32b` (20 GB, top quality that fits 24 GB). A 60-sec glance at `ollama.com/library` / r/LocalLLaMA at install time is worth it in case something newer landed — if so, just change `CFB_LOCAL_LLM_MODEL`.

## Step 3 — smoke-check the wiring (not an A/B, ~1 min)

With Ollama running (no `ANTHROPIC_API_KEY` needed for this):

```bash
python tools/local_llm_check.py --sample 60
```

You'll get something like:

```
OK   server up at http://localhost:11434/v1  (1 model(s) loaded)
     classifying 60 real docs with local=qwen3:8b (temp 0, /no_think, <think> stripped)
  ...
  parseable labels ........ 60/60  (100%)
  label distribution ...... positive=22, neutral=27, negative=11
  avg latency ............. 1.8s per 30-doc batch
  VERDICT:
    ✅ Local Tier-A path is healthy — safe to enable (CFB_LOCAL_LLM=1).
```

This only confirms the **plumbing** (reachable, clean JSON labels, sane spread, decent speed) — it's not judging quality against Claude. If it's green, you're done deciding.

## Step 4 — turn it on

Add to your `.env` (loads automatically when any `manage.py` command runs):

```
CFB_LOCAL_LLM=1
CFB_LOCAL_LLM_MODEL=qwen3:8b
```

Then run the real job — same command as always, now served locally:

```bash
python manage.py classify-player-sentiment --limit 500
```

Because routing keys on the Haiku model id, this is the **only** kind of work that goes local. Your daily/weekly editorial (cover essays, narratives, mailbag — all Opus/Sonnet) keeps hitting Claude untouched. **To turn it all back off:** delete the two `.env` lines (or set `CFB_LOCAL_LLM=0`).

## Step 5 — keep it running 24/7

Ollama's Windows app runs in the background while you're logged in. For start-on-boot without logging in, wrap `ollama serve` with **NSSM** (free) or a Task Scheduler task set to "run whether logged on or not." Recommended on a 24/7 box: power-limit the 3090 (`nvidia-smi -pl 280`) for cooler, quieter operation. (Details in `local-llm-stack-2026-06.md` §6.)

---

## Expanding later (optional)

- **It already covers all Tier-A surfaces.** Once `CFB_LOCAL_LLM=1`, every Haiku-tier call routes local automatically — sentiment classification, theme-extraction Stage-1, the Haiku critic passes, **and** the predictive-claims classifier (`receipts/extract.py`). Opus/Sonnet editorial stays on Claude. No per-surface wiring needed.
- **Bigger/better local model:** point `CFB_LOCAL_LLM_MODEL` at `qwen3:14b` or `qwen3:32b` — the 3090's 24 GB fits up to the 32B at Q4. Bigger = slower but higher quality; fine for nightly batch.
- **Faster batch throughput:** if the 19k-row job is slow on Ollama, graduate to **vLLM** (in WSL2/Docker) — same `CFB_LOCAL_LLM_BASE_URL`, just repoint it. No code change.
- **Playground:** LM Studio or Open WebUI for chat; Qwen2.5-Coder-32B + Continue.dev for a local coding assistant. All optional.

## Watch-outs

- **JSON is much more reliable in 2026 but not guaranteed** — the provider already runs temperature 0, strips `<think>` blocks, and the sentiment classifier skips any unparseable row (and retries it next run), so you don't need to babysit it. Glance at the "parseable" number in the smoke check once.
- **First call after idle is slow** — Ollama loads the model into VRAM on first request (a few seconds), then it's fast until it unloads after ~5 min idle. One-time cost per batch. Set `OLLAMA_KEEP_ALIVE=-1` to keep it resident if you prefer.
- **The switch reads env vars, not a config object** — so they must be in `.env` (auto-loaded by `manage.py` commands) or set as real environment variables in whatever runs the job.
