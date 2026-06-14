# 74 — World-Class Viz Rendering Architecture (the Chronicle Visuals rebuild)

_Status: ARCHITECTURE SPEC v1, 2026-06-13. **Not yet implemented.** Target-state rebuild of the Chronicle Visuals render layer for world-class design quality, motion, and interactivity. Companion to [CHRONICLE_QUALITY_PROPOSAL_v3.md](../../CHRONICLE_QUALITY_PROPOSAL_v3.md) (the engine) and [[73-belief-visual-family]] (new visuals). Decided under the owner mandate "best final end product no matter how long — no active users yet," so this optimizes for the highest ceiling, not the lowest-risk patch._

---

## 0. Diagnosis — why the current output is "far below standard"

The engine (pipeline, scorer, cache, LKG, share-PNG, anti-dup) is good. **The renderer is the ceiling.** Concretely:

- Geometry is hand-written inline `<svg>` via Python f-strings over a primitive helper (`svg_helpers`: `svg_open/text/line/circle/rect/path`) and a **flat 5-color palette** (gold/navy/ink/muted/cream). No scales library, no layout engine, no typographic system, no texture, no motion, no interaction.
- **This is not fixable by prompting the LLM.** Per v3 §7, the LLM never emits pixels — it picks the angle and writes the one-sentence `headline_finding`; a deterministic renderer owns the visual. **World-class lives in the renderer + the design system, full stop.** The LLM's only quality levers are a sharp headline and (new) a motion-intent enum.

Multi-AI brainstorm verdict (Gemini craft + Perplexity stack + native-feature research, 2026-06-13): move core geometry to a real grammar-of-graphics layer (**Observable Plot / D3**, by the D3 team, deterministic, server-side SVG), build a true **design-token system**, and add motion via **native 2026 CSS** (scroll-driven animations are universal; View Transitions + WAAPI production-ready) with interactivity as **progressive-enhancement islands**, never a per-page bundle.

---

## 1. Confirmed environment facts (these make the rebuild cheap)

- **Node v24.16.0 is already installed** on the box → a Node render step adds no new runtime.
- **Share-PNG is `resvg-py`** (`svg_to_bytes`: SVG string → PNG) → any SVG, including Plot/D3-rendered, flows through the existing PNG + LKG + cache path **unchanged**.
- The build is Python-orchestrated (`build_publish.ps1` → `manage.py`), nightly, deterministic, 69k static pages on Vercel.
- Owner rule [[preserve-modules-no-delete-without-signoff]]: **parallel renderer, legacy stays as fallback, per-family cutover** (the Noir player-migration playbook), no module deletion without sign-off.

---

## 2. The target architecture — a clean two-language split

The honesty/determinism contract is preserved by making **Python the only thing that touches data** and **Node a pure, stateless geometry function**.

```
PYTHON (owns truth)                          NODE (owns geometry)            BROWSER (owns life)
─────────────────────                        ────────────────────            ──────────────────
queries.py  → rows + summary_stats           render.mjs:                     static SVG (no-JS OK)
   (SQL only; values never invented)           (VisualSpec JSON + rows)         + design tokens (CSS)
        │                                         → world-class SVG string      + native motion (CSS
        ▼                                       Observable Plot / D3             scroll-driven, WAAPI)
VisualSpec + VisualReceipt (Pydantic)          NO db, NO network, NO clock      + islands (hydrate-on-
        │                                       pure: same input→same SVG         intersection, flagship
        ├──spawn subprocess─────────────────────────▶  stdin JSON                  surfaces only)
        │                                       stdout SVG  ◀────────────────────
        ▼
score_visual → suppress<0.62 → anti-dup thesis
        │
        ├─▶ resvg-py: SVG string → share PNG (1200×675 / 1080×1350)   [UNCHANGED]
        ▼
chronicle_visual_cache + LKG  →  team_pages render slot
```

**Determinism contract (the migration's safety rule):** `render.mjs` is a pure function — it receives the spec + rows on stdin, returns SVG on stdout, and must not read the DB, the network, the filesystem, or the clock (mirror the existing `Date.now()`/`Math.random()` ban; seed any jitter from a value in the spec). Same rows → byte-identical SVG → cache key stable. The existing `RENDERER_VERSION` hash extends to include `render.mjs` + the token files so the cache busts when geometry changes.

**Why not pure-Python (e.g. better matplotlib)?** Matplotlib/Plotly output reads as "scientific," not "editorial," and fights the share-card/mobile/typographic control we need. Observable Plot is purpose-built for editorial SVG and is the D3 team's own grammar. With Node already present, the only cost is a subprocess boundary — worth it for the ceiling.

**Why a subprocess, not a JS rewrite of the pipeline?** Keeps every honesty/scoring/cache/LKG guarantee in the audited Python and quarantines all "new" risk to a pure rendering function that can't lie (it never sees the DB).

### 2.1 Batch the subprocess (performance)

Spawning Node per visual across 119 teams × N visuals is slow. Pattern: a **long-lived Node worker** (one process for the whole build) reading newline-delimited JSON jobs on stdin and emitting `{cache_key, svg}` on stdout, OR a single batched call per team. Python `subprocess` with a persistent pipe; fall back to per-call spawn if the worker dies. Target: full-fleet render inside the nightly window.

---

## 3. The design-token system (the craft layer — the biggest single quality jump)

A real token system, not a 5-constant palette. Lives as the source of truth in one place (CSS custom properties for the live site + a mirrored JSON the Node renderer imports, so SVG and CSS never drift).

- **Type:** a deliberate stack — display (Anton/Bebas for hero numbers, all-caps tight tracking), editorial serif (Source Serif) for headline/annotation prose, Inter for UI/labels, IBM Plex Mono for receipts. **`font-variant-numeric: tabular-nums` everywhere a number appears** (Gemini: wobbling numbers = "cheap"). Min sizes for 360px.
- **Color as data, tonal not categorical:** per the Noir semantics ([[62-team-page-master]]) — perception/belief = violet ✦ *ramp* (vibrant→muted = momentum→stagnation), events = up/down by sign, market/model = blue (dashed/labeled), team color = identity only (≤12% tint). Ramps, not single hues.
- **Texture / "material":** an SVG `<filter>` grain layer + optional paper tint so cards read as a premium daily edition, not browser default; `mix-blend-mode: multiply` where bump/braid paths cross (ink-overprint secondaries).
- **Layout / annotation:** **marginalia** annotation pattern — clean data field, heavy text in the gutters joined by thin leader lines (Gemini); one **hero element** per chart (the number/finding the eye lands on in 0.5s); receipt drawer in mono, never in the headline zone.
- **The receipt stamp:** a rotated, low-opacity "VERIFIED · LIVE DATA · <date>" mark — turns build-time generation into a felt "edition" and reinforces the honesty moat.

This layer alone closes most of the "flat → premium" gap and is independent of the render-engine choice — author it first.

---

## 4. The motion system — native-first, earned-not-decorative

2026 reality (verified): **CSS scroll-driven animations are universal, View Transitions + WAAPI production-ready** → most premium motion is native CSS with **zero main-thread JS**. So motion ships on all 69k pages for free, as progressive enhancement (respects `prefers-reduced-motion`; static is the baseline).

**A reusable motion vocabulary** (a small set of named easings + stagger rules in the tokens, so motion feels systemic not ad-hoc): `enter-draw`, `enter-rise`, `enter-cluster`, `settle-elastic`, `morph`.

**Earned motion, per chart family (Gemini, mapped to your registry):**
- **bump / braid** → `enter-draw` with **staggered `stroke-dasharray`**: rank #1 draws before #2 (lead-follow hierarchy is the *meaning*).
- **waterfall / ladder** → `settle-elastic` **gravity drop**: bars fall and settle, reinforcing accumulation/weight.
- **scatter** → `enter-cluster`: dots start at the mean and fly to position, **visualizing variance** from the norm.
- **ridgeline** → `morph` between states (preseason→now): migration of probability, not two snapshots.
- **annotated line (FAN_MOOD_BRAID)** → axis + series **draw on scroll into view** ("kinetic signature" — the chart drafts itself for the reader); the divergence wedge fills after both lines land.
- **tile mosaic** → staggered tile reveal, **SVG pattern fills** (dots=5★, stripes=4★) for tactile density.

Mechanism: emit the geometry static; attach `view-timeline`/`@keyframes` via a class on the SVG + a `<style>` block from tokens. No JS needed for entrance/draw. WAAPI only where CSS can't express it.

---

## 5. The interactivity layer — islands, flagship surfaces only

Interactivity is the one thing that genuinely needs JS, so it's scoped hardest: **progressive-enhancement islands**, **hydrate-on-intersection**, and only on high-value surfaces (Chronicle hub, team marquee) — never blanket across 69k pages.

- **Tier A (all pages, ~3KB shared):** one tiny vanilla helper, event-delegated on `data-*` attributes the SVG already carries → hover/tap **tooltips**, the **ghost-trace** benchmark reveal, highlight-on-hover. No framework. Works because the SVG is server-rendered with the data baked into attributes.
- **Tier B (flagship only):** **Svelte 5** islands (smallest runtime of the modern options) for scrubbers, before/after toggles, "show my team," week-scrubbing the mood arc. Mounted via `IntersectionObserver` only when the island scrolls near view; the static SVG is the no-JS fallback underneath.

Decision: **Svelte 5 over D3-on-client / React** — D3 for build-time geometry, Svelte for the few interactive islands, keeps client bundles tiny. (Perplexity + Gemini both land here.)

---

## 6. Tooling decisions (locked recommendations)

| Concern | Choice | Why |
|---|---|---|
| Build-time geometry | **Observable Plot** (drop to **D3** for bespoke: braid, field-map, sankey) | D3-team grammar, deterministic, editorial SVG, faceting/scales/annotation far past f-strings |
| Render runtime | **Node v24** (already installed) as a **pure subprocess** | no new runtime; honesty stays in Python |
| Share-PNG | **resvg-py** (unchanged) | already SVG→PNG; consumes Plot SVG as-is |
| Entrance/draw motion | **native CSS scroll-driven + WAAPI** | universal 2026, zero JS, free on all pages |
| Interactivity | **Svelte 5 islands**, hydrate-on-intersection | smallest runtime; flagship-scoped |
| Tooltips/ghost-trace | **~3KB vanilla, event-delegated on `data-*`** | no framework tax site-wide |
| Tokens | **CSS custom properties + mirrored JSON** | single source of truth; SVG & CSS can't drift |

---

## 7. Migration — parallel renderer, per-family cutover (preserve rule)

Per [[preserve-modules-no-delete-without-signoff]], nothing is deleted; the new path runs **beside** the old behind a flag, cutover one chart family at a time.

1. **Token system first** (§3) — author the design tokens + apply to the *existing* Python SVG. Immediate visible lift, validates the design language, zero engine risk.
2. **Node render harness** — `render.mjs` pure-function worker + Python subprocess bridge + determinism test (same rows → identical SVG twice). Wire `RENDERER_VERSION` to include it.
3. **Parallel renderer flag** — `VISUAL_RENDERER ∈ {legacy, plot}` (env, like `NOIR_ROLLOUT_TIER`). `legacy` = current f-string path (default/fallback). `plot` = Node path. Per-visual override so families cut over individually.
4. **Port one family** end-to-end (recommend **FAN_MOOD_BRAID** from [[73-belief-visual-family]] — new, flagship, no legacy to preserve) → render via Plot/D3, native draw motion, Tier-A tooltips, resvg PNG. This is the reference implementation + the quality bar.
5. **Motion + island layer** (§4–5) shipped with that family.
6. **Cut over remaining families** one per cycle; keep legacy renderer as the fallback the flag can revert to. Retire legacy only after every family is ported **and signed off**.
7. **Eval gate:** the existing scorer + a new **visual-regression screenshot** check (Playwright at 360/768/1200) before any family flips default — no family ships that regresses mobile legibility or share-card cropping (v3 §12).

---

## 8. Guardrails preserved (non-negotiable through the rebuild)

- **Honesty:** every displayed value still originates in `queries.py` (SQL); Node receives rows, never queries. Receipts + confidence band on every card. Reality axis labeled (model/résumé/poll), never "market/$."
- **No-JS baseline:** static SVG renders and is fully legible with JS disabled; motion + interaction are enhancements; `prefers-reduced-motion` honored.
- **Determinism:** pure renderer, no clock/RNG/network; cache key + `RENDERER_VERSION` stable per data fingerprint.
- **Accessibility:** alt text + table fallback per visual (v3 §12); tab/focus on interactive islands; contrast tokens.
- **Suppression/anti-dup/LKG:** unchanged — the new renderer plugs into the same `VisualResult` flow.

---

## 9. Plain-language note on cost (for the infra-light owner)

The scary-sounding part — "add a Node render step" — is small because Node is already installed and the boundary is one subprocess that takes JSON in and gives SVG out. You are **not** rewriting the site in JavaScript; Python still runs everything and owns all the data. If the Node step ever breaks, the `legacy` flag renders the old SVG and the site still ships. The biggest *time* cost is design craft (tokens, motion choreography, porting each family well), which is exactly where "best end product no matter how long" should be spent.

---

## 10. Acceptance (target state)

- A flagship visual (FAN_MOOD_BRAID) renders via Plot/D3 with: tokenized type/color/texture, one hero element, marginalia annotation, native scroll-draw entrance, Tier-A hover tooltip + ghost trace, resvg share-PNG, alt+table fallback — and screenshots clean at 360/768/1200.
- `VISUAL_RENDERER` flag flips a family between legacy and plot with no data/honesty change; determinism test passes.
- A neutral viewer would call the result "world-class / screenshot-worthy," not "competent but flat."
- Legacy renderer remains a working fallback until full sign-off.
