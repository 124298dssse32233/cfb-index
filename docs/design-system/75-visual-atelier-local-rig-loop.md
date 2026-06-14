# 75 — The Visual Atelier: a local-rig, closed-loop design engine

_Status: SYSTEM ARCHITECTURE v1, 2026-06-13. **Not yet implemented.** The capstone that ties together [[73-belief-visual-family]] (what to chart), [[74-world-class-viz-rendering-architecture]] (how to render world-class), [[51-team-narrative-engine]] (the narrative state), and the local LLM rig into one self-improving visual factory. Authored under the owner mandate "the absolute best world-class system I can use given my rig + my data." Optimizes for the highest possible ceiling._

---

## 0. The thesis — stop hand-tuning charts; build a factory that critiques itself

World-class studios don't ship the first render. A designer makes it, an **art director looks at it and says what's wrong**, it gets fixed, repeat. That feedback loop is the quality. CFB Index can now run that loop **automatically, nightly, on owned hardware** because two things are true in June 2026:

1. **Vision-language models can see and judge a rendered chart.** Qwen3-VL (installed: `qwen3-vl:8b`) reads chart images, detects label overlap/legibility/hierarchy problems, and can even emit corrected HTML/CSS — and the agentic "generate → render → VLM-critique → refine" pattern is established research (ChartDiff, EvoChart, "Navigating the Mirage" misleading-chart detection).
2. **Your rig already runs it for free.** RTX 3090 24GB + Ollama with `qwen3.6:27b`, `mistral-small3.2`, `qwen3:14b`, **`qwen3-vl:8b`**, `qwen2.5vl:3b`.

The result is a system no competitor can copy: it is conditioned on **proprietary belief data** they don't have, and improved by a **closed critique loop** they aren't running. v3 §11 already imagined this ("render → screenshot QA → paid critic") but assumed the critic must be a gated paid call; in 2026 the critic is a **local VLM that runs on every iteration, not just the final gate.**

---

## 1. The rig (verified 2026-06-13)

| Model | Size | Role in the Atelier |
|---|---|---|
| `qwen3.6:27b` | 17.4 GB | **Visual Director** (planner/critic) — narrative→spec, prose critique |
| `mistral-small3.2` | 15.2 GB | **Writer** — `headline_finding`, annotation copy |
| `qwen3-vl:8b` | 6.1 GB | **Vision Critic** — *looks at the rendered PNG*, scores design, names fixes |
| `qwen2.5vl:3b` | 3.2 GB | fast Vision Critic (triage / share-card crop check) |
| `qwen3:14b` | 9.3 GB | fallback planner |

24GB means models **hot-swap per call** (the existing Chronicle pattern — fine for a nightly batch). The Vision Critic (6.1GB) is small enough to stay resident alongside a writer for fast loops.

---

## 2. The loop — six stages, all local

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ 1. DATA & HONESTY  (Python — unchanged)                                   │
  │    queries.py → rows + summary_stats + VisualReceipt   (SQL only)         │
  └───────────────┬─────────────────────────────────────────────────────────┘
                  ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ 2. VISUAL DIRECTOR  (qwen3.6:27b, structured output)                      │
  │    in:  ProgramNarrativeState (lead char, delta_wow, act, emotional_core) │
  │         + available data manifest                                        │
  │    out: VisualSpec {chart_family, encodings, annotations, motion_intent,  │
  │         palette_treatment, headline_finding}   ← narrative-CONDITIONED    │
  │    (never emits data values — only the angle + words + design intent)     │
  └───────────────┬─────────────────────────────────────────────────────────┘
                  ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ 3. RENDER  (Node + Observable Plot/D3 + design tokens — doc 74)           │
  │    pure(spec, rows) → world-class SVG  →  resvg-py → PNG                   │
  └───────────────┬─────────────────────────────────────────────────────────┘
                  ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ 4. VISION CRITIC  (qwen3-vl:8b LOOKS AT THE PNG, rubric-constrained)      │
  │    out: {scores{legibility,hierarchy,overlap,contrast,hero,              │
  │          headline_matches_chart, screenshot_value}, fixes[], verdict}     │
  └───────────────┬─────────────────────────────────────────────────────────┘
                  ▼
  ┌─────────────── REFINE (≤N iters) ──────────────────────────────────────── ┐
  │  verdict=ship → done.   verdict=fix → route each fix:                      │
  │   • geometry/label fix → adjust SPEC, re-render (stage 3)                  │
  │   • wrong angle/headline → back to DIRECTOR (stage 2)                      │
  │   • token-level (color/space/type) → tweak treatment, re-render            │
  │  stop at score≥BAR or max_iters; keep best-scoring render.                 │
  └───────────────┬─────────────────────────────────────────────────────────┘
                  ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ 5. ESCALATION GATE (tiered)                                               │
  │    flagship S/T1 only: one paid frontier-VLM critique (Claude/GPT vision) │
  │    for the final 1% — keep/revise/suppress + one sharper headline (v3§11) │
  └───────────────┬─────────────────────────────────────────────────────────┘
                  ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ 6. SCORE → SUPPRESS<0.62 → ANTI-DUP → CACHE → LKG → team-page slot        │
  │    (existing engine flow, unchanged)                                      │
  └─────────────────────────────────────────────────────────────────────────┘
```

Everything in stages 1–4 + 6 is **local and free**. Stage 5 is the only paid call, gated to flagship cards.

---

## 3. Stage 2 — the Visual Director (this closes the narrative-conditioning gap)

The earlier-identified gap was: the engine elects visuals by **data availability**, not by **this team's current story**. The Director fixes that. Given `ProgramNarrativeState` ([[51-team-narrative-engine]] §9) — lead character, signed `delta_wow`, Director's-Playbook act ([[69-living-team-page-directors-playbook]]), `emotional_core` ([[63-per-program-emotional-identity]]) — it emits a structured `VisualSpec` choosing:

- **which chart leads** (the one that *proves the current lead*, e.g. `FAN_MOOD_BRAID` when `lead.character=='fanbase'` and `|delta_wow|` is large);
- the **angle + `headline_finding`** (Writer model phrases it);
- **annotations** (which datapoint to call out — values injected by the renderer, never the LLM);
- a **`motion_intent`** enum (doc 74 §4: `enter-draw / settle-elastic / enter-cluster / morph`) — the LLM picks the *intent*, the renderer owns the pixels;
- a **`palette_treatment`** keyed off `emotional_core` (a grief program renders cooler/quieter; a delusion program leans the violet belief ramp) — bespoke *within* the token system.

Hard rule (unchanged from v3 §7): **the Director never emits a number.** It chooses story, words, and design intent; Python+Node own every value and pixel. This is what lets the system be both creative and incapable of lying.

---

## 4. Stage 4 — the Vision Critic (the part that makes it world-class)

The Critic is the art director. It receives the rendered **PNG** (+ the headline + the data table for honesty cross-check) and returns **structured JSON against a fixed rubric** — never free-form vibes:

```json
{
  "legibility_360": 0.0-1.0,   "label_overlap": 0.0-1.0,
  "visual_hierarchy": 0.0-1.0, "contrast": 0.0-1.0,
  "hero_element_present": true/false,
  "headline_matches_chart": true/false,   // honesty: does the picture show what the words claim?
  "share_crop_survives": true/false,
  "fixes": [ {"issue":"y-axis labels collide at 360px","target":"spec.encodings.y","severity":"high"} ],
  "verdict": "ship | fix | suppress"
}
```

**Why this is safe (constraining VLM failure modes):** open VLMs hallucinate issues and judge inconsistently. Constraints: (1) a **fixed rubric with numeric fields + structured output** (Ollama `format` schema), never open critique; (2) **self-consistency** — sample the Critic 3× on flagship cards, take majority verdict; (3) the Critic **only judges pixels/legibility/honesty-of-depiction** — it is *forbidden to assert data values* (those come from the receipt); (4) a **fix must name a `target`** in the spec/tokens or it's discarded (no actionable target = noise). The misleading-chart-detection capability (ChartDiff / "Navigating the Mirage") doubles as a **visual honesty gate**: if `headline_matches_chart=false`, suppress — the picture must not imply something the data doesn't.

---

## 5. The system gets smarter over time (the compounding moat)

Every critique is a labeled judgment. Accumulate them ([[honors-comprehensive]]-style, mirroring the existing prose antislop/banlist):

- **Token feedback:** recurring fixes ("contrast fails on the violet ramp at 360px") harden the **design tokens** — fixed once, never recur.
- **Director few-shot:** specs that shipped at high score become **few-shot exemplars**, so the Director proposes better first drafts (fewer refine iters over time).
- **Design banlist:** recurring anti-patterns become hard renderer lint (a "visual slop" list, analog to the 56-phrase prose banlist).
- **Optional Design-Critique LoRA:** you already have a LoRA training path (`train_voice_lora.py`). Once enough Critic judgments accumulate, fine-tune a small **design-critic LoRA** on (image → rubric-score) pairs so the local Critic matches your taste specifically. This is the endgame: a critic that knows *the CFB Index bar*.

The loop converges: month 1 it refines 3–4× per card; month 6 the first render usually ships, because the tokens, few-shot, and banlist absorbed the lessons.

---

## 6. Other ways the rig + data earn their keep

- **Share-card QA:** `qwen2.5vl:3b` (fast) verifies the 1200×675 crop still reads without article prose (v3 §12 editorial gate) — automatically.
- **Per-team bespoke treatment:** the Director maps `emotional_core` → palette/texture/annotation emphasis, so 119 pages feel authored, not templated — but always within the token system, so never off-brand.
- **Accessibility generation:** the Writer drafts alt text; the Critic confirms the alt text matches what's visually shown.
- **Cohort design calibration:** run the Critic across a team's whole visual set to enforce variety (no two flagship cards with the same silhouette) — the visual analog of the prose anti-duplication.

---

## 7. Performance & scheduling (24GB reality)

- Render (Node) is CPU-cheap. Critic (`qwen3-vl:8b`, 6GB) is fast and can stay resident. Director (`qwen3.6:27b`, 17GB) hot-swaps with the Writer per card (existing pattern).
- Budget per card: render (ms) + 1–3 Critic passes (~seconds each) + occasional Director re-plan. For ~119 teams × a few visuals with LKG fallback, this fits a **nightly batch window**; flagship paid-VLM escalation is a handful of calls.
- **Never blocks deploy** (v3 §8 / [[build-failure-philosophy]]): if the loop fails or runs long, the card falls back to last-known-good. The loop is quality enrichment off the critical path.

---

## 8. How it composes with the existing plan

- **Doc 73** supplies the belief visuals the Director can choose from.
- **Doc 74** is stages 1, 3, 6 — the Python/Node split, tokens, native motion, islands. The Atelier adds stages **2 (Director)**, **4 (Vision Critic)**, **5 (escalation)** on top.
- **Doc 51** (narrative engine) supplies the Director's input (`ProgramNarrativeState`). Until that lands, the Director conditions on the **live seam** (`PageState` + `backometer.delta_wow`) — same as doc 73 §5.
- All existing guardrails (honesty/SQL-sourced values, suppression, anti-dup, LKG, no-JS fallback, accessibility) are **preserved** — the Atelier only adds judgment and refinement around them.

---

## 9. Build sequence (capstone on top of 74's migration)

1. **74 first** — tokens, Node render harness, parallel-renderer flag, port `FAN_MOOD_BRAID`. (No Atelier yet; just a world-class static renderer.)
2. **Vision Critic harness** — `qwen3-vl:8b` via Ollama, rubric schema (Ollama `format`), feed it the rendered PNG, get structured JSON. Validate it catches a deliberately-broken chart (overlapping labels) and passes a clean one.
3. **Refine loop** — wire Critic `fixes[]` → re-render; cap iters; keep best. Measure score lift across a 20-card benchmark.
4. **Visual Director** — `qwen3.6:27b` narrative→`VisualSpec` structured output; condition election on `delta_wow`/act/`emotional_core`. This is the narrative-conditioning the owner originally asked for, now with a critic enforcing quality.
5. **Escalation gate** — one paid frontier-VLM critique for flagship S/T1 only.
6. **Learning layer** — accumulate judgments → token hardening + Director few-shot + design banlist; later, the design-critic LoRA.

---

## 10. Acceptance (target state)

- A card flows data → Director → render → Vision-Critic → refine → ship, fully local, nightly, with LKG fallback.
- The Vision Critic reliably (3× self-consistent) catches label-overlap / low-contrast / headline-mismatch and the refine loop measurably raises the score.
- The Director picks the *narratively correct* lead visual (validated on a labeled program-week set, like [[51-team-narrative-engine]] §12).
- Flagship cards clear a paid-VLM final gate; the system's average refine-iterations-to-ship *falls* month over month as the learning layer compounds.
- A neutral viewer calls the output world-class; a competitor cannot reproduce it without the belief data and the loop.
