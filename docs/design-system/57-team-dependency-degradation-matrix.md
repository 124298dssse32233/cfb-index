# 57 — Team Story Card: Dependency & Degradation Matrix

_Status: RELIABILITY SPEC (critique-hardened v2). Created 2026-06-11. For every crown input: what it reads, what refreshes it, how fresh it must be, and exactly how it degrades. v2 adds the one eligibility matrix that reconciles the competing floors (§1.5), separates `lead_kind` from `render_rung` (§1.5), and adds the negative-trend Rung-3 trigger (§3). The pipeline degrades SILENTLY by design ([[build-failure-philosophy]]), so every input needs a defined fallback — and the crown needs a defined fallback ladder so a quiet 6-6 mid-major gets an honest standings-led card, never a manufactured saga. The team analog of [[48-dependency-degradation-matrix]]._

---

## 0. The two rules

1. **An input never crashes a page.** Missing/empty → the contributing thread is dropped from the resolver's candidate set; the crown returns `""` only as the last rung. Matches the world-class team-page sections.
2. **The crown never shows broken — and never lies.** It degrades down a ladder (§3) into a *different speech act*, never a half-rendered or smoothly-fabricated card. This is the **uncanny-middle** defense: confident prose over thin data is a lie, so below the floor the crown changes what it *does*, not just how loud it is.

---

## 1. The four floors that are already computed (reconcile, don't reinvent)

The live system already materializes the signal floors the crown needs — use them:

| Floor | Source | Meaning |
|---|---|---|
| `backometer_weekly.is_low_signal` | `MIN_SAMPLE = 200` mentions/week | below this, never show a confident belief verdict |
| `backometer_weekly.is_offseason` | calendar | branch to Hope-Economy / Standing-Lead mode |
| pulse `SENTIMENT_FLOOR = 100` docs | `pulse_state.py` | below this, the mood bar is suppressed |
| `team_ledger_scores` `MIN_DOCS = 8` | [[56-team-fan-ledger-detectors]] §4 | below this, no ledger fires |

The rung thresholds (§3) are **reconciled to these** by the matrix below — the crown does not invent a competing floor; it composes the existing ones with an explicit precedence.

## 1.5 The eligibility matrix — `lead_kind` × `render_rung` (the one reconciliation)

The review's core finding: "the floor" was named three incompatible ways (`C≥0.45`, `EffectiveLevel<45 AND D<15`, `MIN_DOCS=8`). They govern **different axes**, and conflating them wrongly demotes a real event to "quiet." Separate them:

- **`lead_kind`** (narrative eligibility, set by the resolver, [[51-team-narrative-engine]] §3e) = *is there a lead, and is it active/standing/quiet?* A **hard structured event is always `active`** regardless of discourse.
- **`render_rung`** (prose richness, set here) = *how richly may it be written, and may it use fanbase-attribution language?*

| Condition | `lead_kind` | max `render_rung` | Fanbase-attribution language? |
|---|---|---|---|
| Hard structured event (firing, result, ranking, official move) | `active` | 1–2 by discourse depth | only if `backometer` not `is_low_signal` |
| Active discourse beat, `V≥30 E≥8 S≥3 C≥0.78` | `active` | 1 (Rich saga) | yes |
| Active beat, `V≥10 E≥5 S≥2 C≥0.62` | `active` | 2 (Constrained) | yes, hedged |
| Continuing state, no fresh movement | `standing` | 2–3 | only the settled belief (`backometer.zone`), never a surge |
| `EffectiveLevel<45 AND D<15`, no active beat | `quiet` | 3 (Standing-led) | **no** — standings only |
| Below `E≥3 / S≥1`, or `is_low_signal` with no event | `quiet` | 3–4 | no |

**Precedence on disagreement:** `lead_kind` wins over `render_rung` for *what the lead is* (an event leads even at Rung 3); the **lower** of the discourse floors wins for *whether fanbase-attribution language is allowed* (a fired-coach fact renders at Rung 2 even with zero discourse, but "the fanbase wanted this" only appears if the discourse floor clears). `MIN_DOCS=8`/`MIN_SAMPLE=200`/`SENTIMENT_FLOOR=100` gate the *attribution language*, never the *factual lead*.

---

## 2. The dependency matrix

| Crown thread | Reads (tables) | Refreshed by | Cadence | If STALE | If EMPTY/MISSING |
|---|---|---|---|---|---|
| Identity / record / mode | `PageState` (`resolve_state`), snapshot, rankings | collect (CFBD) | nightly / on result | last-known | minimal name + record header |
| Fanbase belief + Flip Point | `backometer_weekly` (score/zone/delta_wow) | `compute-backometer` | weekly | last week's zone | drop the mood line; `is_low_signal` → Quiet State |
| Standard-Gap / BAN | rankings + `program_tier` + historical peak | collect + profile | nightly / on result | offseason: label "2025" (fine) | drop BAN; keep record |
| Coach state | `coach_pressure_weekly` (+ `coaching_tenure`) | new detector (enrich) | nightly; tenure hand-seeded | last phase | tenure-only ("Year 3 of the era") |
| Fan ledgers | doc-level `conversation_documents`/`_targets` (evidence, sources) + `team_ledger_scores`; `team_conversation_daily` for the aggregate only ([[51-team-narrative-engine]] §2) | enrich + new detector | nightly | last fired week | below `MIN_DOCS` → no attribution language |
| Rivalry thread | `rivalry_pairs`, `rivalry_obsession_weekly`, games | collect + compute | nightly | last meeting record | drop rivalry thread |
| Hope / recruiting / portal | `recruiting_footprint`, `top_commits`, `transfer_position_snapshots` | collect | on change | last snapshot | drop Hope thread |
| Path object (win-and-in) | standings + CFP/bowl math | collect | weekly in-season | label "as of <date>" | omit path chip |
| Quote | `pulse_themes` / `team_conversation_daily` | build (Opus) | nightly | last good quote | drop quote |
| Tribal Lens slices | `audience_bucket` | collect/enrich | nightly | last slices | single (National) lens only |
| LLM voice (logline/prose) | pulse / chronicle / `program_bible` | build (Opus/Ollama) | top-N nightly + state-hash regen | **serve LKG** (`_cards_lkg/`) | deterministic templated logline (profile voice) |

---

## 3. The card fallback ladder (the four rungs — reconciled with Codex)

The crown always renders something true, picking the **highest rung the data supports**. Speech act changes per rung — not just verbosity.

```
RUNG 1  RICH SAGA           V>=30 docs/7d, E>=8 evidence rows, S>=3 source classes, C>=0.78
        90-140 words, character lead + tension + supporting thread + fanbase attribution
        + confidence meter. Multi-pass LLM (Tier A). The full crown.

RUNG 2  CONSTRAINED         V>=10, E>=5, S>=2, C>=0.62
        55-90 words: state + evidence-backed tension + next calendar test.
        Single-pass LLM, slot-constrained. No metaphor, no "everyone believes," no mind-reading.

RUNG 3  STANDING-LED        E>=3, S>=1, C>=0.45  (or backometer is_low_signal)
        Deterministic prose, NO mood inference:
        "Akron enters November 5-7, fourth in the MAC East, with two one-score losses.
         The next measurable question is the December recruiting window."
        This is the Quiet State ([[51-team-narrative-engine]] §3e) / Standing Lead path.

        NEGATIVE-TREND TRIGGER (review fix — no false calm): if is_low_signal but the
        backometer delta is sharply negative (D_dir = - and |delta| large), the prose must
        pivot from "orderly process" to honest uncertainty — "the program enters a period
        of high uncertainty" — rather than narrating a collapse as a quiet, orderly period.
        Omission-by-calm is its own fabrication.

RUNG 4  BARE STATE          anything below Rung 3
        2026 record / conference / last result / next milestone / "Limited signal".
        No confidence meter implying analytical sophistication.
```

`V` = qualifying discourse items (trailing 7d — distinct from the resolver's belief-displacement `D` in [[51-team-narrative-engine]] §3), `E` = distinct evidence rows behind the lead, `S` = distinct source classes, `C` = calibrated confidence ([[33-confidence-signaling]]). The 1→2 drop is invisible to the reader (a simpler card); 2→3 is the honest mid-major path; 4 is the safety net. **Composition picks the rung; the LLM is never asked to write above the rung its data supports.**

---

## 4. Freshness budget (how stale is too stale)

Per [[51-team-narrative-engine]] §6: **4h** game-day/carousel/signing-day/portal-deadline · **12h** in-season weekday · **24h** offseason · **72h** historical lead. Past budget the crown relabels ("snapshot from this morning"), never rewrites; generated prose avoids present-tense certainty ("today/currently") unless the budget outlasts the next deploy. A stale-but-labeled card beats a fresh-looking lie. Live/in-game is out of scope for v1 (daily-batch) — flag, don't fake.

---

## 5. Coverage-guard registration (so silent death is caught)

The new tables register in `verify_module_coverage.py` (the **team-keyed** path — already exists, [[55-team-rollout-infra-compat]] §0):

- `coach_pressure_weekly` — distinct teams with a computed phase at latest week
- `team_ledger_scores` — distinct teams with a fired ledger at latest week
- `program_bible` — distinct teams with a current bible

Without this, the silent-degradation philosophy hides a dead engine for weeks (the 2026-06-11 incident, [[build-failure-philosophy]]). New tables are "young" and unjudged until they establish a baseline — safe to register from day one.

---

## 6. The single failure that would be invisible

The worst case isn't a crash — it's the resolver **silently leading every team with the Quiet State** because a detector quietly returned empty (sources fine, render fine, but `team_ledger_scores`/`coach_pressure_weekly` empty → every card falls to Rung 3). The defense is the trio ([[55-team-rollout-infra-compat]] §7): non-critical Run (won't block) + `""`/Quiet-State fallback (won't break) + **coverage-guard entry (won't hide)**. The third is the one easy to forget and the only one that surfaces a dead engine. A secondary tell: a **distribution monitor** — if >90% of teams sit at Rung 3–4 on an in-season Monday, something upstream died.

## 7. Provenance

Derived from the live `build_publish.ps1` stage map, the `backometer`/pulse floors (`MIN_SAMPLE=200`, `SENTIMENT_FLOOR=100`), the Codex 4-rung degradation design (2026-06-11), and the graceful-degradation philosophy ([[build-failure-philosophy]]). Mirrors [[48-dependency-degradation-matrix]]. Builds on [[51-team-narrative-engine]], [[55-team-rollout-infra-compat]], [[56-team-fan-ledger-detectors]].
