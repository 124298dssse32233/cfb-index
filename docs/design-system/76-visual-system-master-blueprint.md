# 76 — The CFB Index Visual System: Master Blueprint

_Status: MASTER BLUEPRINT v1, 2026-06-13. **Not yet implemented.** The single converged program for world-class, self-renewing data visualization across **all** team and player pages (thousands of pages), authored under the owner mandate: "the absolute best setup for June 2026 — world-class viz that stays relevant as the pages change through the offseason and seasons; carte blanche; make it look like a billion-dollar company." Unifies and supersedes-as-entry-point [[73-belief-visual-family]] (what to chart), [[74-world-class-viz-rendering-architecture]] (how to render), [[75-visual-atelier-local-rig-loop]] (the self-critiquing loop). Grounded in June-2026 state of the art (Observable Framework, Svelte, D3, Rive; evaluator-optimizer agentic loops; VIS-Shepherd-class critics)._

---

## 0. What "billion-dollar" actually means here

It is not fancier charts. It is **systemic coherence + living relevance + provable honesty**, at scale:

1. **One locked visual language** applied to every chart on every page — the Stripe/Linear/Apple lesson: brand is consistency, not decoration. A fan should recognize a CFB Index chart from across the room.
2. **It re-edits itself on the calendar.** The chart on a page in June is a different chart than the one in November, because the *story* changed — and the system did that automatically.
3. **Self-critiquing quality.** Nothing ships that an art director (here, a frontier vision model) wouldn't pass.
4. **Provable honesty.** Every value traces to a query; the picture can't imply what the data doesn't.
5. **Uncopyable.** Conditioned on proprietary belief/narrative data nobody else has, refined by a loop nobody else runs.

The four pillars below deliver these.

```
            ┌──────────────────────────────────────────────────────────────┐
            │  PILLAR A — THE LANGUAGE      (locked design system §6)        │
            │  one type/color/texture/motion/annotation grammar, everywhere  │
            └───────────────┬──────────────────────────────────────────────┘
PILLAR D ──▶ │              ▼                                                  │ ◀── PILLAR C
LIVING       │  PILLAR B — THE RENDER STACK  (Observable Framework+D3+Rive §7) │   THE ATELIER
RECOMPOSITION│  data(SQL)→Director→render→SVG/Canvas→PNG, deterministic        │   frontier+local
(calendar §3)│              ▲                                                  │   evaluator-optimizer
            │              └──── PILLAR C critiques & refines ────────────────┘   loop (§5)
            └──────────────────────────────────────────────────────────────┘
                 one engine, entity-agnostic: TEAMS + PLAYERS + rivalry/conf (§2)
                 tiered across thousands of pages, regenerating on cadence (§4)
```

---

## 1. The non-negotiable spine (carried from the existing engine)

The built `chronicle/visuals/` engine stays the spine; everything here extends it. Preserved, always: **values come from `queries.py` (SQL) only**; receipts + confidence on every card; suppression<0.62; anti-dup thesis hash; LKG fallback; static SVG works with **no JS**; alt-text + table fallback; the `VisualResult`→cache→team/player render slot. Per [[preserve-modules-no-delete-without-signoff]], all new rendering lands as a **parallel renderer behind a flag**, per-family cutover, legacy stays as fallback.

---

## 2. One engine, both subjects — teams AND players (entity-agnostic)

The engine already carries `EntityKind {team, player, conference, rivalry, league}` and a player visual ships today (`HEISMAN_RACE_BRAID`). The Visual Director, family registry, scorer, and Atelier loop are **entity-agnostic**; only the query + the family set differ by subject.

**Team belief/narrative families** (from [[73-belief-visual-family]]): `FAN_MOOD_BRAID` (Phantom Delta), `HOME_AWAY_MIND` (fan-vs-national), `MOOD_SPECTRUM` (emotion shares) — plus the structural set already built.

**Player families** (net-new, mirroring the player narrative engine [[42-player-narrative-engine]] / packet [[59-player-evidence-packet-contract]] / the live Noir route [[noir-player-route-live]]):
- **`PERCEPTION_VS_TAPE`** — the player Phantom Delta: discourse/hype vs production/value metrics. This is the Noir moat ([[noir-rollout-readiness-2026-06-12]]) made visual. Annotated line/scatter; the gap is the story.
- **`DEVELOPMENT_ARC`** — recruit rating → usage → production → draft signal, year over year (slopegraph/braid).
- **`ROLE_FINGERPRINT`** — the constrained radar/percentile hybrid (the one sanctioned radial use) for "what kind of player is he becoming."
- **`HEISMAN_TRAJECTORY`** (exists as braid) and **`LOAD_BEARER`** (narrative-weight: how much of the team's belief rides on this player).
- **Ledger-driven**: player ledgers are **already built** (`player_pages/ledgers.py`) — surface them as a belief visual (Hope/Grievance/Judgment/Grudge/Belonging) the way [[73-belief-visual-family]] does for teams.

One registry, two family namespaces; the Director picks within the subject's set. The cache key already namespaces by `entity_kind`, so team/player can't collide.

---

## 3. The Living Recomposition Engine (why the viz "stays relevant")

This is the heart of the mandate. The visual on a page is a **function of that subject's current narrative state**, and it **changes when the state changes** — automatically, on the calendar.

### 3.1 Calendar acts drive the lead visual
- **Teams** — the Director's-Playbook acts ([[69-living-team-page-directors-playbook]]): Long Wait → Permission Slip → Hope-Doping → Verdict Begins → Weekly Grind → Rivalry Week → Reckoning → Carnage → Reload → Spring. Each act has a **preferred lead visual** (e.g. Carnage → portal `Defection Echo`; Hope-Doping → `FAN_MOOD_BRAID` + returning-production; Rivalry Week → the Grudge/obsession visual; Weekly Grind → the result-delta `Statement Win Ladder`).
- **Players** — the player calendar: Recruiting/Signing → Spring → Camp → In-season (week-to-week) → Bowl/Award → Draft → Portal. Each maps to a preferred player family (e.g. Draft season → `DEVELOPMENT_ARC`/draft conveyor; In-season → `PERCEPTION_VS_TAPE`).

An **Act Resolver** (date → current_act → preferred-family weighting) feeds the Director so the *whole site* recomposes on schedule.

### 3.2 Regeneration triggers (the dual trigger, from [[51-team-narrative-engine]] §7 / [[61-team-evidence-packet-contract]])
A subject's visuals re-render when **either**: the **narrative spine hash** changes (the story moved) **or** the **evidence fingerprint** changes (`sha1` of selected source rows + structured fact keys). Same signature → cache hit → skip. This is already the engine's `data_fingerprint` + `RENDERER_VERSION` mechanism — extend it to include the narrative-state hash.

### 3.3 Freshness + event-triggered rebuild
Freshness budgets by calendar state ([[51-team-narrative-engine]] §6): 4h on game day / carousel / signing day / portal deadline; 12h in-season weekday; 24h offseason; 72h for historical leads. A **hard event** (result, firing, hire, big portal move, draft pick) triggers an **out-of-cycle rebuild of just that subject's visuals**, not a wait for the nightly batch. Stale-but-known-superseded visuals are **suppressed**, not shown with a timestamp.

### 3.4 Make the change legible (the signature "living" moment)
When the lead visual changes between builds, surface it: an **Overthrow Spark / Recomposition Replay** ([[73-belief-visual-family]] lineage) that animates the transition from last build's lead to this one ("last week this page led with recruiting momentum; a portal exodus overrode it"). Rive (§7) makes this morph premium. **No competitor can show this because no one else diffs their own narrative state.**

---

## 4. Scale across thousands of pages — tiering & cadence

Billion-dollar quality on ~69k pages ≠ a frontier loop on every page. Tier the *effort*, never the *language* (the locked design system makes even the cheapest tier beautiful). Mirrors the Chronicle tier policy + [[58-team-build-philosophy]].

| Tier | Subjects | Pipeline | Motion | Critic | Cadence |
|---|---|---|---|---|---|
| **S — Flagship** | top-25 teams, top players, marquee moments | full Director + Atelier loop, **Rive** hero piece | Rive + scroll-driven | **frontier VLM** (Claude Opus vision), 3× self-consistent | event-driven + ~daily |
| **Mid** | rest of FBS, ranked/relevant players | Director + **local** Atelier loop, Observable Framework SVG | CSS scroll-driven + WAAPI | **local** `qwen3-vl:8b` | nightly / weekly |
| **Long-tail** | deep roster, low-signal programs | deterministic render from tokens + Plot geometry (no loop) | CSS entrance only | none (scorer gate only) | on evidence change |
| **Quiet/Awaiting** | genuinely no signal | honest "Awaiting Signal" state, **no fabricated chart** | none | none | — |

Everything falls back to **LKG** if its tier's pipeline fails or overruns the nightly window — the pipeline never blocks deploy ([[build-failure-philosophy]]). Promotion is event-driven (a hard event jumps a subject to S for that cycle).

---

## 5. The Atelier loop — frontier-primary, local-volume (cost is not a constraint)

The evaluator-optimizer loop (now standard SOTA — VIS-Shepherd, A2P-Vis) is the spine. With Claude Max + subscriptions, **frontier models are the primary taste-makers; the local rig is the throughput tier.**

```
DATA(SQL) → DIRECTOR → RENDER → VISION CRITIC → refine(≤N) → ESCALATE(flagship) → score→cache→LKG
            │          │         │
   frontier (Opus)   Node       frontier VLM on S/flagship;
   for S; local       Observable local qwen3-vl:8b for Mid;
   qwen3.6:27b        Framework  rubric-constrained structured
   for Mid+volume     +D3+Rive   output, 3× self-consistency on S
```

- **Director** = narrative-state → `VisualSpec` (chart, angle, headline, `motion_intent`, `palette_treatment`). Frontier (Opus) authors flagship specs; local `qwen3.6:27b` handles volume. Never emits a data value (honesty rule).
- **Vision Critic** = *looks at the rendered PNG* against a fixed rubric (legibility@360, label-overlap, hierarchy, contrast, hero-present, **headline_matches_chart** = visual honesty, share-crop-survives) → structured JSON `{scores, fixes[], verdict}`. Frontier on flagship; local on Mid. Constrain VLM failure modes with: fixed schema, 3× self-consistency on S, fixes must name a `target`, and the critic **never asserts data values** (only judges pixels/depiction).
- **Refine** routes fixes back to render (geometry/token) or Director (angle); keep best-scoring; cap iters.
- **Learning layer (the compounding moat)**: accumulate critic judgments → harden tokens, grow Director few-shot exemplars, build a **visual-slop banlist** (analog to the 56-phrase prose banlist), and eventually a **design-critic LoRA** (you have the LoRA path) so the local critic matches the CFB Index bar. Refine-iters-to-ship falls month over month.

---

## 6. Pillar A — the locked "billion-dollar" design language

The single highest-leverage investment; lock it first, apply everywhere. Source of truth = CSS custom properties + a mirrored JSON the renderer imports (SVG and CSS never drift). Extends Noir tokens ([[62-team-page-master]]).

- **Type system:** display (Anton — hero numbers, all-caps tight) · editorial serif (Source Serif — headline/annotation prose) · Inter (UI/labels) · IBM Plex Mono (receipts). `tabular-nums` on **every** number. Defined min sizes for 360px.
- **Color = data, tonal not categorical:** belief/perception = violet ✦ **ramp** (momentum→stagnation); events = up/down by sign; model/market = blue (dashed/labeled, never asserted); team color = identity only (≤12% tint). Ramps, never flat single hues.
- **Material:** SVG `<filter>` grain + paper tint (premium edition feel, not browser-default); `mix-blend-mode: multiply` where braid/bump paths cross.
- **Layout grammar:** **one hero element** per chart (the 0.5-second landing point); **marginalia** annotation (clean data field; heavy text in gutters on thin leader lines); receipt drawer in mono; the rotated low-opacity **"VERIFIED · LIVE · <date>" stamp** as a brand signature.
- **Motion vocabulary** (named, systemic — feels designed, not ad-hoc): `enter-draw` (staggered `stroke-dasharray`, lead-follow), `settle-elastic` (waterfall gravity), `enter-cluster` (scatter shows variance), `morph` (ridgeline/recomposition). Native CSS scroll-driven by default (zero-JS, universal in 2026); Rive for hero data-bound pieces; `prefers-reduced-motion` honored; static is the baseline.

This language *is* the brand. Applied across thousands of pages by the pipeline, it is what reads as "billion-dollar."

---

## 7. Pillar B — the render stack (June-2026 SOTA)

| Concern | Choice | Why (what top teams use) |
|---|---|---|
| Viz build system | **Observable Framework** | build-time static + interactive islands + large data; by D3's creator; purpose-built for exactly this |
| Bespoke geometry | **D3 v7** (via Plot for standard marks) | the foundational newsroom layer; braid/field-map/sankey need it |
| Interactive components | **Svelte 5** islands, hydrate-on-intersection | the dominant newsroom data-viz framework (Rich Harris, ex-NYT); smallest runtime |
| Hero / data-bound motion | **Rive** (state machines + data binding, WASM/Canvas) | 2026 premium for "animation is logic"; the recomposition morph, belief braid |
| Entrance / micro-motion | **native CSS scroll-driven + WAAPI** | universal 2026, zero main-thread JS, free on all pages |
| Tooltips / ghost-trace site-wide | **~3KB vanilla**, event-delegated on `data-*` | no framework tax across 69k pages |
| Render runtime | **Node v24** (installed) as pure subprocess | honesty stays in Python; geometry in JS |
| Share-PNG / OG | **resvg-py** (unchanged) | consumes any SVG; Rive frames via headless capture for flagship |

Determinism contract: the Node renderer is pure (no db/network/clock/RNG; seed any jitter from the spec). Same state → byte-identical output → stable cache.

---

## 8. Build & ops integration

- Slots into the nightly box build ([[deploy-clobber-root-cause]] full-snapshot discipline): generate visuals for all tiers within the window; LKG covers overruns; event-triggered out-of-cycle rebuilds for hard events.
- Parallel renderer flag `VISUAL_RENDERER ∈ {legacy, framework}` (the Noir-migration playbook); per-family cutover; legacy is the always-working fallback.
- Eval gate before any family flips default: scorer + **Playwright visual-regression** screenshots at 360/768/1200 + the Vision-Critic honesty pass.
- All guardrails from §1 preserved end to end.

---

## 9. The program (phased — "no matter how long," sequenced for compounding value)

1. **Lock Pillar A** (the design language) and apply it to the *existing* Python SVG. Immediate billion-dollar lift, zero engine risk, validates the brand. **Do this first.**
2. **Render harness** — Observable Framework + D3 + Node subprocess + determinism test; port **`FAN_MOOD_BRAID`** as the reference card (team belief flagship).
3. **Vision-Critic harness** — rubric schema; validate it catches a broken chart and passes a clean one (local `qwen3-vl:8b`, frontier on flagship).
4. **Refine loop** — wire fixes→re-render; measure score lift on a 20-card benchmark.
5. **Director** — narrative-state → `VisualSpec`; condition election on act + `delta_wow` + `emotional_core` (the live→`ProgramNarrativeState` seam). This is the narrative-conditioning that started this whole thread.
6. **Player families** — port `PERCEPTION_VS_TAPE` + ledger-driven player visuals; same loop, player namespace.
7. **Living recomposition** — Act Resolver + dual-trigger regen + event rebuild + the Recomposition-Replay (Rive).
8. **Tiering at scale** — S/Mid/Long-tail routing; frontier on S, local on Mid, deterministic long-tail; LKG everywhere.
9. **Learning layer** — token hardening + Director few-shot + visual-slop banlist; later the design-critic LoRA.
10. **Rive hero pieces + flagship polish** — the marquee, screenshot-worthy, group-chat-able cards.

---

## 10. North-star acceptance

- A neutral viewer, shown any page in any month, says "this looks like a billion-dollar product" — and a competitor cannot reproduce it without the belief data and the loop.
- The same team/player page in June, October, and January shows **different, correct lead visuals** because the story changed — automatically.
- Every chart traces every value to a query; the Vision Critic blocks any chart whose picture overstates its data.
- Thousands of pages render world-class within the nightly window, degrading gracefully (LKG / honest Awaiting-Signal), never blocking deploy.
- Refine-iterations-to-ship fall month over month as the learning layer compounds — the system gets better while you sleep.
