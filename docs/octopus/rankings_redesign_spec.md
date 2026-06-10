# Rankings Redesign — Design Spec **v4** (board-first · identity-tight)

**Authored 2026-06-08 via `/octo:design-ui-ux`.** v4 supersedes v3. Inputs:
[`rankings_redesign_brief.md`](rankings_redesign_brief.md) · research dossier
[`rankings_redesign_research.md`](rankings_redesign_research.md).
**Integrated:** Gemini critique (v1) · 4-stream deep research · **two independent v3 critiques**
(Gemini = feasibility, principal-product-designer = strategy) · owner directives. **Codex:** abandoned
(hung; never emitted) — superseded by the two v3 critiques. Design + spec only — no code this run.

---

## 0. What changed from v3 (two-critique integration log)
- **🔴 BOARD-FIRST IA (both reviewers converged):** the ranked Top 25 is now the **instant, no-JS,
  crawlable hero**. Hero Finding → a one-line banner; Signal Stack → a strip *below the top 5* / a
  "Stories" tab. Answer "who's #1" in **zero taps**, then earn the right to tell stories.
- **🔴 NEW pillar — Casual default + SEO (§4):** a skimmable, no-interaction, server-rendered,
  schema.org-marked Top 25 for the searcher who just wants the list. This was missing entirely.
- **🔴 NEW — What-If / Path simulator (M-WhatIf):** the thing FPI wins on; fans want to *simulate*, not
  just read. First-class forward module.
- **Bettor lens (M-Bet):** surface ATS / market-gap on the MAIN board (highest-intent cohort), not just
  conference pages.
- **Identity tightened to 3 pillars** (+ growth assets + research backlog); the 14-item slate was "a
  backlog wearing a strategy costume."
- **Perf honesty (§11):** explicit fallbacks for `<details name>`, anchor-positioning, content-
  visibility; **focus management is budgeted JS, not free.**
- **Accountability rigor (§12):** multi-season samples + confidence intervals; poll-Brier demoted to
  research; cherry-picked "we called it" replaced by aggregate hit-rate.
- **Scope realism (§10):** Phase 1 = **12–18 dev-days**; **Tri-Rank implied-rank derivation is a
  modeling spike**, pre-built before Phase 1.

---

## 1. THESIS
**The first rankings board built for a phone, for every division, that shows its work — and answers
"who's #1?" in zero taps.** Power (how good) · résumé (what they earned) · fan belief (who the room
believes) · a public calibration record (whether we've been right). Incumbents are desktop tables that
cap at FBS, hide fan belief, and never publish their accuracy. We win on **board-first speed,
phone-native craft, honest uncertainty, and a tight original identity.**

**Identity in one line:** *the rankings that show their work.* Safe identity core = **Tri-Rank** +
**Model Report Card**; contested-but-uncopyable third = **Cross-Division Bridge** (see §13).

---

## 2. ORIGINALITY — tightened (3 pillars · growth · supporting · backlog)

**IDENTITY PILLARS (these ARE the product; both reviewers back the first two):**
- **P1 Tri-Rank — Model · Room · Nation** ⭐ model rank vs fan-belief-implied rank vs national-implied
  rank; the *gap* is the story. The only way to make fan-belief legible as a number. *(Derivation is a
  modeling task — see §10.)*
- **P2 Model Report Card** ⭐ public calibration curve + season Brier + plain verdict. "We publish when
  we're wrong" — the trust moat nobody owns since 538 died.
- **P3 Cross-Division Bridge** ⭐ "this DII #1 would slot ~#90 in FBS." Uncopyable by anyone capping at
  136 FBS. **CONTESTED** (§13): identity signal vs. low-stakes novelty — validate with users.

**GROWTH / DISTRIBUTION ASSETS (not identity; Phase 3 bet):**
- **G1 Program Stripes** — one stripe/season, color = final rank vs program baseline; shareable, merch-ready.
- **G2 Rankings Wrapped** — season-end swipeable share-card stack; organic distribution loop.

**SUPPORTING MECHANICS (earn their place inside modules):**
- **S1 Quantile dotplots** (load-bearing per Gemini) — odds as "14 of 20 outcomes"; kills the
  containment misread. **S2 "Why they moved"** explainers with receipts. **S3 Overtake-bump
  scrollyteller** — the weekly narrative asset. **S4 Connected-scatterplot** season portrait (desktop /
  drawer only — too dense for the one-thumb default).

**RESEARCH BACKLOG (toys gated on data + user-testing; do NOT ship in identity frame):**
HOPs, "You Draw It," skewed fan chart, **poll-Brier leaderboard** (ordinal→prob is arbitrary), Marey
gauntlet.

---

## 3. MOBILE-FIRST EXPERIENCE (390px) — **board-first**
```
┌─────────────────────────────┐
│ Sticky top 44px: brand · ⌘K  │
├─────────────────────────────┤
│ My-Teams chips ▶ (swipe)     │  followed teams filter; off by default for first-time visitors
├─────────────────────────────┤
│ 1-LINE FINDING BANNER        │  "Ohio St #1 — power & résumé agree" (dismissible; NOT a full screen)
├─────────────────────────────┤
│ ★ THE BOARD = HERO ★         │  the ranked Top 25, server-rendered, readable with ZERO interaction.
│   card-feed: rank · Δspark ·  │  One dominant number (power, +inline rank). Tri-Rank triplet.
│   team · power(+rk) · belief │  Playoff-odds dotplot. Tap → <details> drawer.
│   [Compare] · [Lenses ▾]      │  Lenses: Résumé · Bettor (ATS/market) · Belief.
│   … Top 25 …                 │  "Load deep board (668)" → content-visibility lazy.
├─────────────────────────────┤
│ STORIES strip (below top 5   │  ← demoted Signal Stack: swipeable story cards (Riser · Vibe Shift ·
│   or a "Stories" tab)        │  Called-It-aggregate · Bridge). Optional, never blocks the list.
├─────────────────────────────┤
│ DRILL-DOWN (lazy): Report     │  Model Report Card · The Room · Strength-by-level · What-If sim
│   Card · Room · What-If       │
├─────────────────────────────┤
│ METHODOLOGY FOOTER · "Updated 2h ago" (pulses) · provenance        │
├─────────────────────────────┤
│ BOTTOM TAB BAR: Rankings · Scores · Teams · Search                 │
└─────────────────────────────┘
```
**Rule (both reviewers):** the list is the hero. The finding is one line, the Stories strip lives
*below the top 5* (or behind a tab) — two editorial gates in front of the data was the v3 mistake.
**Micro-interactions:** roll numbers 200–300ms; haptic on follow/compare; scrubbable Δ-spark; skeletons.

---

## 4. CASUAL DEFAULT + SEO (new pillar — existential for a static site)
- **Zero-interaction Top 25:** server-rendered, fully readable and ranked **without any JS**; the default
  view requires no taps. This is the casual fan's entire need — serve it first-class.
- **Crawlable + structured:** semantic `<ol>`/`<table>` Top 25 in the initial HTML; **schema.org
  `ItemList`/`SportsEvent`** markup; descriptive `<title>`/meta targeting "college football rankings",
  "[team] ranking", "[conference] rankings"; per-surface OG images.
- **Fast static path:** the board's above-fold HTML + critical CSS render before any enhancement; the
  product must win the Google snippet, not just the engaged fan.
- **Entry intents served:** national Top 25 · "[team] rank + why" (deep-link to row drawer) ·
  "[conference] rankings" (conference surface). Rival-watching via My-Teams + a "rivals" chip.

---

## 5. ENHANCE UP (768→1280): the KenPom board
Signal/Stories → full-width **overtake-bump** (desktop). Card feed → **dense KenPom table** (value +
inline rank, sticky team spine, snap-scroll numeric columns, sort any column with `aria-sort` + live
region). Modules → 3–4-col grid; Compare → side panel; bump → hover-scrub scrollyteller.

---

## 6. MODULE CONTRACT (v4)
**NEW since v3 in bold.** Load column = perf contract.

| # | Module | Form | Load |
|---|---|---|---|
| M1 | Finding banner | 1-line typographic (dismissible) | eager |
| M2 | **The Board (HERO)** — KenPom card-feed→table | value+inline-rank · Δ scrubbable spark · **quantile-dotplot** cell · **Lenses (Résumé/Bettor/Belief)** | **Top 25 eager (no-JS); deep board content-visibility lazy** |
| M3 | Tri-Rank cell (P1) | 3-dot scale + divergence arrow | eager |
| M4 | Stories strip (demoted Signal Stack) | swipe cards | lazy, below top 5 |
| M5 | Row Drawer (`<details name>`) | Savant sliders (pool stated) + season-arc spark + connected scatter (S4) + the-room | **lazy on expand** |
| M6 | **Model Report Card (P2)** | calibration curve + Brier **+ CIs** + verdict | lazy |
| M7 | **What-If / Path simulator** | pick results → live playoff/seed odds (FPI-killer); the 1 JS-lib exception | lazy |
| M8 | The Room board | mood heatmap small-multiples | lazy |
| M9 | Cross-Division Bridge (P3) | dot-on-scale across levels | lazy |
| M10 | Strength-by-level / Power-vs-Résumé | percentile h-bars / annotated scatter | lazy |
| M11 | **Bettor lens** (on M2) | ATS cover% · wins-vs-market · line value | lens toggle |
| M12 | Share layer | Program Stripes (G1) · Rankings Wrapped (G2) · OG | on-demand |
| M13 | Methodology footer | provenance + liveness pulse | eager |

**Universal rules:** one dominant number per card; rank beside every number; state the comparison pool;
color is functional; every chart has a data-table fallback + finding-stating alt-text; sub-floor fan
signals → "Awaiting Signal."

---

## 7. PER-SURFACE
- **Main `/rankings/`:** board-first; Top 25 → FBS → All (668). All lenses; full modules.
- **Conference `/conferences/<slug>.html`:** board-first scoped to conference; richer columns native;
  Bettor lens especially relevant. **Reflect rebuilt 9-team 2026 Pac-12 + thinned Mountain West.**
- **Archive `/archive/<season>-week-<week>.html` (RETROSPECTIVE):** frozen; **overtake-bump scrollyteller
  + Model Report Card are the stars** ("said vs happened"); season scrubber.

---

## 8. CHART VOCABULARY additions (unlocked; documented in `31-chart-vocabulary.md`)
Quantile dotplot (preferred over bands) · calibration curve · connected scatterplot · Program Stripes ·
overtake-bump · (backlog: skewed fan chart, HOPs — reduced-motion fallback = dotplot). Forbidden still:
pie/donut/3D/word-cloud. What-If sim (M7) is the only JS-charting-lib candidate (explicit perf exception).

---

## 9. REUSE MAP (v4 deltas)
| Module | Reuse | New wiring |
|---|---|---|
| M2 Board | `_render_rankings_row`, `_rankings_board_script` | inline-rank cols; surface `schedule_connectivity`,`cross_level_confidence`; **lens toggles** |
| M3 Tri-Rank | — | **NET-NEW modeling: belief/respect percentile → implied rank (pre-spike, §10)** |
| M6 Report Card | — | `games_predictive_claims`+`claim_outcomes`+`confidence_calibration` (multi-season) |
| M7 What-If | — | season-sim engine (net-new or reuse model forecast) |
| M11 Bettor | conference betting summaries | port ATS/market to main board lens |
| M5 drawer | `savant_data_loader`,`season_arc_loader`,`fetch_team_mood_profile` | lazy `<details>` |

---

## 10. PHASED BUILD (scope corrected)
**Phase 0 — SPIKE (~2–3 days):** prove **Tri-Rank implied-rank derivation** (belief/respect → rank) is
sound and stable; without it P1 is a modeling task masquerading as a render tweak.

**Phase 1 — SURGICAL board-first (`reporting.py`), ~12–18 dev-days, low–med risk.** Board-first IA;
**no-JS crawlable Top 25 + SEO/schema (§4)**; KenPom inline-rank + surfaced SoS/confidence; **Tri-Rank
chip (P1)**; **quantile-dotplot** cell (S1); Bettor lens; Stories strip demoted; content-visibility +
`<details name>` + `:has()` board with **fallbacks + focus-management JS budgeted**; provenance/liveness
footer; roll/haptic micro-interactions.

**Phase 2 — MODULE, ~3 weeks.** Savant drawer + connected scatter (S4); **Model Report Card (P2)** with
CIs; The Room; **What-If sim (M7)**; Cross-Division Bridge (P3); "why they moved" (S2); Compare.

**Phase 3 — ARCHITECTURAL + GROWTH.** Seed `dashboards/renderer.py` (migrate `/rankings/` first);
**Program Stripes (G1) + Rankings Wrapped (G2)**; overtake-bump scrollyteller (S3); season scrubber;
research-backlog experiments behind flags. **Rule:** Report Card (P2) ships before any calibrated cone
or poll-Brier (backlog).

**Recommendation: hybrid** — Phase 0 spike → Phase 1 board-first ship → Phase 2 → Phase 3. Don't lead
with the rewrite; don't ship originals before the list is fast and crawlable.

---

## 11. CRAFT · A11Y · PERF (honest about fallbacks)
- **Board stack + REQUIRED fallbacks:** semantic `<table>` in a `role=region` scroll wrapper (never
  `display:block`); sticky first column + scroll-snap; `content-visibility:auto` with **carefully mapped
  `contain-intrinsic-size`** (CLS risk on filter/sort — test, reserve space per card state);
  **`<details name>`** drawers **+ a tiny JS shim** to enforce exclusivity on pre-Sept-2025 Safari/
  Android (else "all-open" bloat); `:has()` filtering behind `@supports`; **Popover API** filter panel;
  anchor-positioned tooltips **with a static fallback position** (Chromium-heavy).
- **Focus management is BUDGETED JS, not free:** drawers/Popovers/compare-tray need focus trap + return
  + `aria-live`. "Zero-JS" applies to rendering, not a11y.
- **PE:** core ranking renders + is sortable-by-link server-side; JS only enhances.
- **Budget:** FCP<1.5s, INP<200ms, **JS<50KB** (sort + filter-counts + focus-mgmt + 1 sim lib — still
  fits), critical CSS<10KB, Lighthouse≥95, 390/768/1280 via container queries.
- **Enhancement-only:** View Transitions, Speculation-Rules prerender. Reduced-motion disables roll/
  scrub/HOPs.

---

## 12. ACCOUNTABILITY RIGOR (Report Card, fixed)
- **Multi-season sample required** before publishing a calibration verdict; show **confidence intervals**
  on the curve (one Chaos Saturday must not swing the headline).
- **Aggregate hit-rate, not cherry-picks:** kill "Model Called-It" survivorship cards; show season
  hit-rate + Brier vs a coin-flip baseline + accuracy-vs-weeks-out.
- **Poll-Brier leaderboard (backlog):** scoring ordinal AP/Coaches/Committee requires a defensible
  ordinal→probability mapping; flagged as research, not a launch feature.

---

## 13. RISKS / PRESERVED DISAGREEMENTS
- **Cross-Division Bridge (P3) — UNRESOLVED:** product-designer = "the headline, uncopyable";
  Gemini = "gimmick, no competitive stakes." **Synthesis:** keep as an *identity/credibility* signal
  ("one honest scale for everyone"), not a daily-use tool; **user-test before marketing it as THE
  signature.** Owner decides.
- **Containment effect:** lead with quantile dotplots/HOPs; label any band "1 in 3 finish outside."
- **Originality vs noise:** research-backlog items stay flagged until user-tested.
- **Owner decision still open:** is the marketed signature **Tri-Rank** or the **Model Report Card**?
  (Both reviewers rate these the two safest pillars.)

## 14. Codex critique — ABANDONED (hung; never emitted). Superseded by the two v3 critiques above.
