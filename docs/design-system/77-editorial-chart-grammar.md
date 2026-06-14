# 77 — The Editorial Chart Grammar (the render backbone)

_Status: BUILDABLE SPEC v1, 2026-06-13. **Not yet implemented.** The locked visual treatment every Chronicle visual renders through — chosen by the owner (2026-06-13) as the direction that "elevates quality the highest and is the most copyable." A reusable NYT-Upshot-class editorial grammar, static-first, applied once in the renderer so all team + player chart families inherit it. Implements Pillar A of [[76-visual-system-master-blueprint.md]] in concrete, buildable terms; the render mechanics live in [[74-world-class-viz-rendering-architecture]]._

---

## 0. Why this grammar (highest quality × most copyable)

Editorial viz reads "expensive" not because of motion but because of **(a) the annotation layer doing the arguing and (b) ruthless emphasis** (one subject saturated, everything else gray). Both are cheap to systematize and deterministic to render. Unlike scrollytelling (bespoke per piece) or broadcast-hero (share-card-specific), this grammar is a **recipe that generalizes to every chart family** — line, scatter, dot/range plot, slopegraph, waterfall, bump. Implement it once; thousands of auto-generated charts inherit a single world-class publication look. It renders fully **without JS** (motion/interaction are enhancement), so it scales to all ~69k pages.

The LLM's only contribution remains the `headline_finding` + which point to annotate; the renderer owns every pixel and value (honesty rule, [[74-world-class-viz-rendering-architecture]] §2).

---

## 1. The eight rules (every chart obeys all eight)

1. **Headline = the finding, not the topic.** Serif, sentence case, states the conclusion: "Fans are priced 14 points above the model." Never "Belief over time." Max ~80 chars; the scorer already rewards 60–140-char clarity.
2. **Direct labels at series termini; no legend.** Each line/series labeled at its end, in its own color. Legends force look-back; kill them.
3. **One emphasis color + grays.** The subject uses the saturated semantic ramp (belief = violet, events = up/down, model/market = blue); peers and context are gray (`--ink-30`). Emphasis is the single biggest quality lever.
4. **The annotation layer is the storyteller.** 1–2 callouts max, anchored to the decisive datapoint via a thin leader line (0.75px, `--ink-40`); the callout text carries the editorial argument and cites its receipt.
5. **A shaded key region names the concept.** The Delusion wedge, a quadrant fill, a confidence band, a median reference — one highlighted area per chart, low-opacity, labeled in place.
6. **Restrained frame.** Hairline gridlines (`--ink-08`) or none; ticks only where read; no chart border, no drop shadows on data; data-ink dominates. Generous margins (see §3) with a right/bottom marginalia gutter for callouts.
7. **Type & numerals.** Serif (Source Serif) headline · sans (Inter) labels · mono (IBM Plex) receipts. `font-variant-numeric: tabular-nums` on **every** number. Sizes in §3.
8. **Mobile reflows, never shrinks.** At ≤400px: drop peer labels, keep the finding + the one hero annotation + the subject; rotate nothing; re-layout the gutter below the plot. (Renderer emits a distinct mobile layout, not a scaled desktop one.)

---

## 2. The anatomy (fixed slots, every card)

```
┌───────────────────────────────────────────────┐
│ EYEBROW  (mono, caps, --ink-50) — subject·metric│   row 1: context
│ HEADLINE (serif, the finding)                   │   row 2: the argument
│                                                 │
│   [ PLOT FIELD ]            [ MARGINALIA ]      │   row 3: data + callouts
│   emphasis subject,          1–2 annotations     │
│   gray context,              on leader lines     │
│   one shaded region          (gutter, right/btm) │
│                                                 │
│ RECEIPT (mono, --ink-50) — n=· source · CONF · ✓│   row 4: provenance + stamp
└───────────────────────────────────────────────┘
```

Slots are constant across families; only the PLOT FIELD geometry changes. This constancy is what makes the output feel like one publication while each chart stays bespoke to its data.

---

## 3. Concrete tokens (first-pass values — tune in the reference build)

- **Canvas:** desktop 640×400 default (4:3) / 16:9 for share; mobile 360-wide reflow. Margins: top 64 (eyebrow+headline), right 96 (gutter), bottom 44 (receipt), left 40 (axis). Gutter ≥ 120px when annotations present.
- **Type:** eyebrow 11px mono caps, letter-spacing .08em · headline 19px/24 serif 600 · axis/labels 12px Inter · direct-label 12px Inter 600 (colored) · annotation 12px serif italic · receipt 10px mono.
- **Color (extends Noir tokens [[62-team-page-master]]):** belief ramp `--violet-700→--violet-300`; context `--ink-30`; gridline `--ink-08`; leader `--ink-40`; up `--up`, down `--down`; model/market `--market` (dashed). Subject saturated; everything else gray.
- **Stroke:** subject line 2px round-join; context lines 1px; gridline 0.5px; leader 0.75px. Markers: subject 3.5px filled, context 2px.
- **Shaded region:** fill at 10–14% opacity of the concept color; label set inside at 11px, same hue darker.
- **Grain/material:** one shared SVG `<filter>` grain at ~3% on the canvas (premium edition feel); off on mobile for perf.

---

## 4. Per-family application (the renderer implements once)

Each family is a PLOT-FIELD geometry that plugs into the §2 anatomy and obeys the §1 rules:

| Family | Plot field | Emphasis | Shaded region | Canonical annotation |
|---|---|---|---|---|
| **annotated line** (`FAN_MOOD_BRAID`) | two series over weeks | subject = belief (violet) | the belief↔model wedge ("Delusion/Paranoia") | the inflection week |
| **annotated scatter** (`PERCEPTION_VS_TAPE`, CFP bubble) | dots in 2 metrics; ≤40 on mobile | subject dot saturated; peers gray | quadrant fill (under/over-priced) | the subject dot |
| **dot / range plot** (rankings, percentiles) | sorted rows, one metric | subject row highlighted | median/percentile reference line | subject's value vs median |
| **slopegraph** (`HOME_AWAY_MIND`, dev arc) | two checkpoints, lines | subject line; peers gray | the gap band | widest-divergence line |
| **waterfall** (`STATEMENT_WIN_LADDER`, returning-prod) | signed bars summing to a delta | the load-bearing bar | the running total line | the bar that moved it most |
| **bump / braid** (`HEISMAN_RACE_BRAID`) | rank lines over weeks | subject braid bold | — (lead-follow draw motion) | the crossover week |

Adding a family = define its PLOT-FIELD renderer; it inherits eyebrow/headline/marginalia/receipt/type/color/mobile for free.

---

## 5. Motion & interaction (enhancement only, layered on the static grammar)

The grammar is complete as static SVG. Then, per [[74-world-class-viz-rendering-architecture]] §4–5 / [[76-visual-system-master-blueprint]] §6:
- **Entrance (native CSS scroll-driven, zero-JS):** the axis draws, then the subject series draws (`enter-draw`), then the shaded region fills, then annotations fade in — the reveal order *is* the reading order (the Pudding principle: transitions do the explaining).
- **Hover/tap (≤3KB shared vanilla):** spotlight a series, reveal the ghost-trace benchmark, tooltip from baked `data-*`.
- **Flagship (Rive/Svelte islands):** the Recomposition-Replay morph when the lead visual changes.
- `prefers-reduced-motion` → static. Always legible with no JS.

---

## 6. Build & acceptance

- Implement the §2 anatomy + §3 tokens + §1 rules as the **shared layout layer** in the new renderer ([[74-world-class-viz-rendering-architecture]]); each family supplies only its PLOT-FIELD geometry.
- **Reference build = `FAN_MOOD_BRAID`** rendered through the full grammar; then port one scatter + one dot-plot to prove the grammar copies before scaling.
- **Acceptance:** three different families, rendered through one grammar, are visually unmistakably the same publication; each obeys all eight rules; each is legible at 360px with no JS; the Vision Critic ([[75-visual-atelier-local-rig-loop]]) passes legibility + headline-matches-chart.

---

## 7. The repeatable system — staying world-class by construction

World-class quality is not a one-time polish; it is a **process with three enforcing layers** so every new visual clears the bar without re-litigating it. (Built and live 2026-06-14.)

### 7a. The authoring recipe (how to add a new visual)
0. **Research best-in-class FIRST (current web, not memory).** Before building any visual type, web-search the state of the art for *that data type / chart form* as of today (e.g. "line-of-identity scatter best practice", "dumbbell chart direction encoding", "beeswarm highlight one entity"). Pull the concrete techniques the best newsrooms/tools use, **copy the best parts, and make ours at least as good** — then cite the sources in the renderer/PR. This step is mandatory and repeats per type; "our learned defaults" are not sufficient. (Worked example: 2026-06-14 research on line-of-identity scatters → added the two-region shading we were missing; dumbbell research confirmed ours already met the bar.)
1. **Query** (`queries.py`): return `{query_id, source_tables, rows, summary_stats, sample_n, confidence, limitations, as_of_utc}`. Every value SQL-sourced. Add an **honesty gate** (suppress on thin/compressed/low-signal data — return `sample_n=0`; see the offseason gate). Include **cohort context** when a "is this a lot?" question exists (a rank or the full field for a scatter).
2. **Renderer** (`families/<name>.py`): build the geometry inside a `draw_plot(px,py,pw,ph)` closure and pass it to `grammar.editorial_card(...)`. Use `cls_text(..., "ed-ax"|"ed-zone"|"ed-ptlabel")` for any small text so it reflows on mobile. **Never** add grain, stamps, or decoration. **Never** print raw table/column/metric names — translate to plain English.
   - **Motion & interactivity are per-type research calls, NEVER mandatory** (owner ruling 2026-06-14). Include them only when best-in-class for *that* data type uses them **and they improve comprehension** — a chart that is clearer static stays static (`editorial_card(animate=False)`, no interactive dots). If it would make the viz worse, leave it out. When you DO include them, they must be **perfect**: motion is scroll-driven + `prefers-reduced-motion`-safe; interactive points use `grammar.dot()` (native `<title>` fallback + keyboard focus + the page tap-tooltip script). The gate (§7b) enforces *correctness-if-present*, not presence.
3. **Register**: add to `_REGISTRY` (team) or `_PLAYER_REGISTRY` (player) + posture + scorer `high_impact` if it answers a real fan argument.
4. **Gate it**: add a synthetic in-season fixture to `ALL_RENDER` in `tests/test_chronicle_visuals_belief.py`. That *automatically* subjects it to the Definition of Done (§7b).

### 7b. The Quality Gate — the codified "Definition of Done" (automated)
`tests/test_chronicle_visuals_belief.py::test_world_class_definition_of_done` runs over **every** grammar visual and FAILS the build unless it passes ALL of:
- **finding-as-headline** (a 24–120-char sentence stating the conclusion, ending in punctuation — not a topic label);
- **shared grammar chrome** (`#f6f1e6` paper + `role="img"` + alt text) — one publication look;
- **human credit line** (`Source: CFB Index …`) with **zero** raw table/column/metric jargon;
- **Upshot restraint** — no `ed-grain`, no `VERIFIED LIVE`, no decoration;
- **typography** — the design serif comes FIRST (the Georgia-ordering regression can never return);
- **mobile** — a responsive `@media (max-width:640px)` type scale is present;
- **determinism** — same data → byte-identical SVG.
The bar is now a test, not a memory. A regression (e.g. re-adding a gimmick, leaking jargon, breaking font order) turns the suite red.

### 7c. The generative quality loop (ongoing improvement)
For raising quality *beyond* the gate, the **Atelier critic loop** ([[75-visual-atelier-local-rig-loop]]): render → a vision model (local `qwen3-vl:8b` for volume, frontier Claude/Opus-vision for flagships) looks at the PNG against a rubric → structured fixes → re-render. Recurring fixes harden the tokens + this checklist + a visual-slop banlist, so the first render gets better over time. Multi-AI design critique (the 2026-06-13/14 Gemini reviews that caught the gimmicks, font bug, and unit mismatch) is the manual version of this loop — run it whenever a family is new or a redesign is proposed.

**The system in one line:** the **grammar** makes a visual consistent, the **gate** makes it correct, the **critic loop** makes it exceptional — and a new visual inherits all three by following §7a.
