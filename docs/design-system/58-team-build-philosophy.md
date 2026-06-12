# 58 — Build Philosophy: Full Vision, Rig-Bounded (Team Edition)

_Status: PLAN (critique-hardened v2). Created 2026-06-11. The team analog of [[49-pragmatic-v1-critique-corrected]]. Same owner ruling — build the full vision (docs 50–57); the ONLY legitimate dial-back is when the single RTX 3090 physically can't finish nightly. For teams that constraint is **barely binding**: ~119 FBS pages vs the ~69k player pages, so the GPU budget is loose enough to afford richer per-page generation than the player card. v2 wires tier promotion to the evaluation gate ([[51-team-narrative-engine]] §12). Not yet implemented._

---

## 0. The principle (owner ruling, carried from [[49-pragmatic-v1-critique-corrected]])

> "I don't want a simpler first build just because we don't know if people will like it. I do want to dial back when it's not achievable to complete everything on my rig."

Build the whole crown. Tier the LLM **prose** only where the GPU can't reach — never cut a feature for product-uncertainty. For teams, the math makes this almost a non-issue.

---

## 1. The scale reality — the GPU is not the constraint here

The player engine is rig-bound because ~69k pages can't all get fresh multipass LLM voice nightly on one 3090. **The team engine has ~119 FBS pages.** At the Chronicle-measured ~13s/card warm, even a generous best-of-3 multipass over *every* FBS team is well within a nightly window — and state-signature regen (already the pattern) drops it to "who changed today," usually a handful. So:

- **Every profiled FBS team can afford rich LLM prose.** The tiering below is about *quality calibration* (don't burn best-of-3 on a team with no story), not a hard GPU ceiling.
- **The dial-back that bites the player card does not bite here.** The honest constraint for teams is the **data floor** (the uncanny middle, [[57-team-dependency-degradation-matrix]]), not the GPU.

---

## 2. The tier plan (quality calibration, not a GPU ceiling)

Reuse the Chronicle tier policy ([[CLAUDE.md]]), keyed on the resolver's lead score + the degradation rung ([[57-team-dependency-degradation-matrix]] §3), recomputed nightly:

- **Tier A (~25 teams):** lead score ≥75, Rung-1 thresholds met, or a hard event active (firing, hire, rivalry result, conference move, playoff selection, top-5 recruiting change). **Two-model generation + critic** (best-of-3 on the marquee). Local Ollama (mistral-small3.2 writer + qwen3 planner) or cloud Opus for the pulse-lede lane.
- **Tier B (~45 teams):** Rung-2 eligible. **One constrained single-pass.**
- **Tier C (~49 teams):** **Deterministic template-fill** (the profile-voice templated logline) — Rung 3–4. No model in the loop.
- **Promotion is event-driven:** any team with a hard event jumps to Tier A regardless of its baseline.
- **Shadow→live promotion is eval-gated:** a tier ships LLM prose to production only after it clears the evaluation benchmark ([[51-team-narrative-engine]] §12 — lead-accuracy, lens-invariance, false-hot-seat rate, Quiet-State calibration, contradiction rate). Until then the tier runs in shadow (generated, logged, not rendered) over the deterministic card.

Two LLM lanes exist and the crown routes per tier ([[54-integration-with-live-team-system]] §6): **pulse = cloud Opus** (already powers `pulse_lede`), **chronicle = local Ollama**. The crown is not local-only.

---

## 3. The non-negotiable: deterministic-first, GPU off the critical path

**The resolver and the typed claims are the product; the LLM prose is a replaceable presentation layer.** ([[51-team-narrative-engine]] §9.) The nightly order:

```
facts → resolver → DETERMINISTIC card (all 119, no GPU)
                 → optional LLM enhancement (Tier A/B)
                 → claim validator
                 → Last-Known-Good selection (_cards_lkg/)
                 → site build
```

The deterministic card is produced first **for every team**, so GPU work is **never on the deploy's critical path** — a Sunday-night pipeline or GPU failure degrades a team to its deterministic render (Rung 2–4), never a broken or missing card. Selection order on render: valid fresh LLM candidate matching the current state hash → valid LKG matching the same lead event → deterministic template → bare state. **Never reuse old fluent prose after the lead character changes** (a cached recruiting story cannot survive a coach firing because it reads well).

Hard limits: Tier A ≤2 drafts + 1 critic; a global GPU deadline (generous given 119 pages); per-team failure isolation; deploy proceeds when the deadline expires.

---

## 4. The quality fixes (these make it better, not smaller)

- **Confident-compiler narrator + confidence meter** — the dominant fan take stated plainly, attributed to the fanbase, dissent as a labeled minority; the meter is the honesty mechanism ([[51-team-narrative-engine]] §1). Not the neutral-observer hedge.
- **The Self-Narration half-life** — Settled Belief vs Reactive Surge ([[51-team-narrative-engine]] §1); the team-specific honesty fix the player card didn't need.
- **Sarcasm handled, not stripped** ([[56-team-fan-ledger-detectors]] §6).
- **Narrow do-not-amplify floor** — unverified criminal/legal/medical, pile-ons, doxxing; plus the coach defamation discipline ([[53-program-succession-coaching-carousel]] §5).
- **The Quiet State as a legitimate output** — not a failure mode ([[57-team-dependency-degradation-matrix]] §3).

---

## 5. The crown data contract (build this before code)

```
crown = {
  program_slug, season, as_of_date, freshness_class,
  render_tier: "rich" | "constrained" | "standing" | "bare",
  page_mode,                                  # from state_resolver
  lead: { character, timescale, event_id, score, confidence },
  logline, logline_locked_event_id,
  ban: { number, label, receipt } | null,
  standard_gap,
  dominant_take: { text, confidence, source_count, half_life, minority_take? } | null,
  supporting_threads[], claims[], citations[],
  lenses: { home, national, rival } | { national },   # Tribal Lens payload
  fallback_reason?
}
```

This is `ProgramNarrativeState` ([[51-team-narrative-engine]] §9) projected to the renderer — the missing output schema; pure engineering hygiene, build it first.

---

## 6. First build (the real thing)

1. **The crown data contract (§5)** + the do-not-amplify floor.
2. **The deterministic crown for every team** — resolver over existing signals (`PageState` + `backometer` + standings) + `coach_pressure_weekly` (Level 1–2) + templated profile-voice logline. Every FBS team gets a real, bespoke-by-composition card with no GPU bottleneck ([[54-integration-with-live-team-system]] §4 v0).
3. **The confident-compiler voice for Tier A/B** — reuse pulse (Opus) / chronicle (Ollama) + eval/LKG/banlist, state-hash regen.
4. **The rich layers** — full ledgers, Tribal Lens payload, Level-3 hot seat, `program_bible` snapshots/changelog — built as the vision intends; the GPU comfortably affords it at 119 pages.

Build order is "deterministic-first → LLM voice on top," for dependency + degradation reasons ([[57-team-dependency-degradation-matrix]]), not to scope down. The whole vision ships; the GPU is barely a meter at this scale.

## 7. Provenance

Carries the owner ruling from [[49-pragmatic-v1-critique-corrected]] (full vision, dial back only for the rig). Codex Tier A/B/C + deterministic-first-off-critical-path design (2026-06-11). Grounded in the ~119-page scale, the Chronicle tier policy + `_cards_lkg/`, and the two LLM lanes (pulse Opus / chronicle Ollama). Mirrors [[49-pragmatic-v1-critique-corrected]]. North star = [[50-team-story-card]]…[[57-team-dependency-degradation-matrix]].
