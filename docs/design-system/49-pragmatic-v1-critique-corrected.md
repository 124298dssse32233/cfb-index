# 49 — Build Philosophy: Full Vision, Rig-Bounded

_Status: PLAN (v2). Created 2026-06-11; **revised after owner correction** — do NOT scope down out of product-uncertainty. Build the full vision (docs 41–48). The ONLY legitimate reason to dial back is when the single RTX 3090 physically cannot complete the work nightly. This doc separates the (rejected) "cut because unproven" critique from the (accepted) "tier because the GPU can't" reality, and folds in the pure quality fixes._

---

## 0. The principle (owner ruling, 2026-06-11)

> "I don't want a simpler first build just because we don't know if people will like it. I do want to dial back when it's not achievable to complete everything on my rig."

So the 3-way review ([[41-player-story-card]]…[[48-dependency-degradation-matrix]] critique) gets re-sorted:

| Reviewer said | Why they said it | Ruling |
|---|---|---|
| ship a simpler validation build / bake-off gate first | unproven product-market fit | **REJECTED** — build the real thing |
| cut bible/snapshots/changelog, musical-chains | "editorial platform before PMF" | **REJECTED** — keep (cheap + wanted) |
| cut 5-axis salience → 1 score; defer features | solo-dev complexity | **OPTIONAL** — build full; simplify only if it doesn't earn its keep |
| **tier LLM generation; can't do 69k nightly** | **physical GPU limit** | **ACCEPTED** — the real dial-back |
| **solve the Tribal-Lens static delivery** | SSG can't toggle 3 POVs cheaply | **ACCEPTED** — a delivery problem, not a feature cut |
| confident narrator + confidence meter (not neutral hedge) | quality / honesty | **DECIDED 2026-06-11 (owner): confident narrator** |
| don't strip sarcasm; handle it | accuracy | **KEEP** (quality fix) |
| do-not-amplify list for criminal/legal/medical/pile-ons | safety/liability | **KEEP** (narrow safety floor) |
| differentiate by content within a coherent frame | craft / "diff shapes read as buggy" | **OWNER'S CALL** (you wanted bespoke shapes) |

The vision stands. What follows is only (1) what the rig forces, and (2) what makes it *better*, not smaller.

---

## 1. What the rig actually forces (the one real constraint)

A single 3090 + Ollama (~13s/card warm) cannot run a multipass writer+eval over ~tens of thousands of pages nightly. This is physics, not timidity. The dial-backs:

- **Reuse the existing Chronicle tier policy** (it already exists, and the live `signature_story`/`narrative_arc` generators already do top-N, not all). LLM *voice* is generated for the tiers the GPU can finish nightly:
  - **S (top ~25–100):** full multipass (best-of-3, eval, the rich engine).
  - **T1 (next few hundred):** single-pass voice.
  - **T2/T3 (the long tail):** **deterministic only** — the ambitious *structured* engine (succession, ledgers-from-the-daily-encoder-pass, stat BAN) still runs for everyone; only the *LLM prose* is withheld where the GPU can't reach.
- **Content-hash regen** (already the pattern) — unchanged players don't re-generate, so nightly load ≈ "who changed today," not the whole roster.
- **Spread heavy generation** if needed — the chronicle-weekly runner already exists for batch LLM work; S-tier best-of-3 can run weekly while T1 refreshes nightly.
- **Ledger stance detection piggybacks** on the **daily encoder pass** you already run (CardiffNLP) for the cheap volume/emotion signal; reserve Qwen3 zero-shot stance for the S/T1 cohort where nuance matters ([[47-fan-ledger-detectors]] §1).

Net: **every player still gets a card; the engine still runs ambitiously; only LLM-prose richness is tiered by GPU budget.** Nothing in the vision is cut — it's scheduled to the hardware.

---

## 2. Tribal Lens — a delivery problem to solve, not a feature to drop

The feature stays (Home/Rival/National POV is one of the most distinctive ideas, [[43-cfb-native-content-model]] §4). The static-site constraint is solved by **delivery**, not deletion:
- ship all (1–3) POV texts as a small **inline JSON payload per page** + a client-side toggle (no extra pages, no server) — the payload is a few hundred words, negligible weight; or
- if a POV's discourse is thin, render only the ones that meet the floor (often just National) — graceful, not 3× always.
No tripling of the 69k page count; no build-window blowup.

---

## 3. The quality fixes (these make it better, not smaller)

- **C1 — Confident narrator + confidence meter.** The neutral observer voice reads as a hedging robot and is a hidden cop-out (choosing "representative" *is* editorializing). The fix: a consistent house-narrator voice that **states the dominant fan take plainly (attributed to the fanbase)** with a confidence meter, dissent as a labeled minority. Preserves "compile the room, don't invent our own take" while killing the mush. **Decided 2026-06-11 (owner): the confident narrator** — compile the room without sounding like a robot.
- **C6 — Sarcasm handled, not stripped** ([[47-fan-ledger-detectors]]) — CFB discourse *is* sarcasm; the context model + `sarcasm_score` + the confidence meter carry it.
- **C7 — Narrow do-not-amplify floor** — unverified criminal/legal/medical allegations, identity pile-ons, doxxing, deleted-then-quoted content are excluded from auto-narration regardless of volume. (You're fine amplifying *real* narratives, including ugly ones — this is just the thin liability/decency floor.)
- **The card data contract** ([§5]) — the missing output schema; pure engineering hygiene, build it first.

---

## 4. Content integrity (NOT a product-uncertainty cut)

Gating the narrative on discourse volume is **not** "scope down because unproven" — it's the same anti-fabrication rule you already endorsed (don't manufacture drama for a backup long-snapper, [[42-player-narrative-engine]] §10). Below the discourse floor, the card shows the **honest stats-only state**, because there is genuinely no narrative to compile — not because we're being cautious. (The rig tiering reinforces it, but integrity is the reason.) The "uncanny middle" — smooth confident prose over thin/sarcastic data — is the real quality risk this prevents.

---

## 5. The card data contract (build this before code)

```
card = {
  player_external_id, season, as_of_date,
  tier: "narrative" | "stats-strip",
  logline, why_now, body, kicker,            # null unless narrative
  ban: { number, label, receipt } | null,
  dominant_take: { text, confidence, source_count, minority_take? } | null,
  ledger_lead, succession, citations[], composition[], fallback_reason?
}
```

---

## 6. On the "bake-off"

Not a go/no-go gate (rejected). But looking at sample outputs early while building is just **good craft** — you tune the narrator prompts and the confidence thresholds by reading real cards, the same way the existing `signature_story` generator was tuned. It's a development habit inside the committed build, not a permission slip.

---

## 7. First build (the real thing, rig-tiered)

1. **Card data contract (§5)** + the do-not-amplify floor (C7).
2. **The deterministic engine for everyone** — succession (QB-first, confidence-gated), ledger detection on the daily encoder pass, BAN selection, one-frame composition. This already gives every player a real, bespoke-by-content card with no GPU bottleneck.
3. **The LLM narrator for the S/T1 tiers** — confident voice + confidence meter, reusing the existing generator + eval/LKG/banlist, content-hash regen.
4. **The rich layers** (bible/snapshots changelog, tribal lens via inline payload, succession beyond QB) — built as the vision intends, scheduled to the GPU budget (S/T1 nightly, deeper passes weekly).

Build order is "deterministic-first → LLM voice on top," but that's for **dependency + degradation** reasons ([[48-dependency-degradation-matrix]]), not to scope down. The whole vision ships; the GPU just meters the prose.

---

## 8. Provenance
3-way adversarial review (2026-06-11) re-sorted under the owner's ruling: full vision, dial back only for the rig. Supersedes the v1 "cut for PMF" framing. North star = [[41-player-story-card]]…[[48-dependency-degradation-matrix]]; quality fixes folded in.
