# Rankings Redesign — Octopus Design Brief

**Authored 2026-06-08.** Input for `/octo:design-ui-ux` (design + spec only — NO code this run).
Scope chosen by owner: all three rankings surfaces; architecture path left to the Define phase.

> Provider note: Perplexity is unavailable in this environment (no API key). Live-web freshness is
> carried by **Gemini + Qwen** in the multi-provider run, plus the curated **2026 LIVE CONTEXT**
> block at the bottom of this brief (researched 2026-06-08 with sources).

---

## GOAL
Redesign THE CFB INDEX rankings SURFACES into the best-in-class college-football rankings system.
Win on **intelligence density and trust, NOT decoration.** This is a composition / information-
architecture problem, not a new visual identity — our design language is already LOCKED. Deliver a
reviewable SPEC this run. Do NOT modify code; output a concept + module contract + per-surface
wireframes + a phased build recommendation the owner approves before anything is implemented.

## DESIGN DIRECTIVES (owner, 2026-06-08)
- **Mobile-first.** Design the 390px experience FIRST, then enhance up to tablet/desktop. Mobile is
  not a shrunk table — it gets native patterns (swipeable signal cards, card-feed board, compare
  sheet, thumb-zone filters). Every incumbent is a desktop-table clone; we win by being phone-native.
- **Originality mandate.** Do genuinely novel things no competitor does, built on our moat
  (multi-division scale, fan belief, model accountability, sourced claims). Signature originals:
  **Tri-Rank** (Model vs Room vs Nation), **honest ranks with uncertainty bands**, **Cross-Division
  Bridge**, **public Model Report Card**, **"why they moved" explainers**, **season scrubber**.
- **Best-practice craft.** Progressive enhancement (core board readable without JS), no CLS,
  skeleton/lazy-load, ≥44px touch targets, fluid clamp type, reduced-motion + dark mode, WCAG 2.2 AA,
  shareable OG per surface. Excellent typographic formatting throughout.

## SCOPE — one coherent system flexing across three surfaces
1. **Main national board:** `render_rankings_page_html()` in `src/cfb_rankings/reporting.py`
   → `output/site/rankings/index.html`. A 668-team filterable board, FBS→DIII.
2. **Conference pages (73):** `render_conference_page_html()` / `render_conferences_index_html()`
   → `/conferences/<slug>.html`. Already richer (record, ATS, market gap, recent form).
3. **Weekly archive snapshots:** `render_archive_snapshot_html()` → `/archive/<season>-week-<week>.html`.
   These are RETROSPECTIVE / frozen — show mood + claims AS THEY STOOD that week; no live signals.

Design a shared MODULE LIBRARY; vary emphasis per surface, don't fork the system.

## CURRENT STATE (read first; do not re-audit from scratch)
- Built via `python manage.py build-site`. `reporting.py` is ~26.8k lines — grep for symbols, never read whole.
- Today the main board shows only **Rank · Change · Team · Level · Power · Resume**, wrapped in
  hero / movement / selection-room cards / power-vs-resume scatter / strength ladder. It works but
  surfaces almost none of our proprietary data.
- Prior Octopus work to REUSE, not redo: `docs/octopus/discover.md`, `visual_ux_recommendations.md`,
  `chart_vocabulary_audit.md`, `next-roadmap.md`.

## THE MOAT TO SURFACE (our unique, currently-hidden capabilities)
Bring these — today locked to team pages / a sparse hub — onto the rankings surfaces:
1. **Fan Intelligence** (`src/cfb_rankings/fan_intelligence.py`): per-team belief, reality_gap
   (Doomer Ball→Hype Train), respect_gap (fans vs national), swing, cohesion (Civil War→United),
   archetype — from 15+ sources × 14 cohorts.
2. **Vibe Shifts:** biggest weekly mood swings, as a first-class rankings signal.
3. **Model accountability:** we store predictions AND outcomes in `games_predictive_claims` but
   never publish a track record. Surface a "we called it" accuracy/calibration signal.
4. **Already-computed, never-shown columns:** `cross_level_confidence`, `schedule_connectivity`,
   resume percentile + resume rank.
5. **Savant percentile bars** and **Season-Arc trajectories** as drill-downs / hover.
6. **Provenance as credibility:** "15 sources, N cohorts" as a trust signal.

## LOCKED CONSTRAINTS (non-negotiable — propose nothing that breaks these)
- **Archetype = Dashboard.** Obey the contract in `docs/design-system/30-page-archetypes.md`
  (hero finding → primary annotated chart → movers grid → drill-down modules → methodology footer
  → thumb-zone filter strip).
  - Visual mirror per that doc is "Bloomberg + FiveThirtyEight." **NOTE: FiveThirtyEight shut down
    Mar 5, 2025** — emulate its dashboard *craft*, but reference **NYT Upshot + Bloomberg Markets**
    as the *live* exemplars; do not imply 538 still exists.
- **Charts: EXTENSIBLE** (vocabulary unlocked by owner 2026-06-08). The 6 in
  `docs/design-system/31-chart-vocabulary.md` remain the DEFAULT house vocabulary, but NEW chart
  types are now ALLOWED when they buy best-in-class intelligence — e.g. a model
  **calibration/reliability curve** (accountability) and a **playoff-path / scenario projection**
  (forward lens). Discipline preserved by two rules: (a) each new type is added to the locked chart
  doc with a rationale (it stays a system); (b) keep **hand-rolled SVG** to honor the JS<50KB /
  CSS<10KB budget — a charting LIBRARY (D3/Chart.js) requires an explicit perf-budget exception and
  applies to at most ONE interactive module. Still avoid pie / donut / 3D / word-cloud. Use the
  **bump chart** for rank movement.
- **Tokens:** `docs/design-system/00-tokens.md` (Bebas Neue + Source Serif Pro + Inter, 6 ramps,
  tabular numerals on every stat). No new colors or fonts.
- **Receipts + confidence:** every editorial claim carries a receipt citation
  (`docs/design-system/32-receipt-pattern.md`, ≥1 per 200 words). Every stat carries a confidence
  chip AND a table fallback (`docs/design-system/33-confidence-signaling.md`).
- **Must preserve:** the 668-row filter/sort table + its Alpine.js behavior, the flat
  `programs/<slug>.html` link convention, and `/assets/` absolute paths.
- **Perf:** FCP < 1.5s, INP < 200ms, JS < 50KB, critical CSS < 10KB. WCAG 2.2 AA, every chart
  alt-text states the FINDING. Lighthouse CI must stay ≥ 95. Render at 390 / 768 / 1280px.
- **Season state:** support an in-season variant (Saturday Strip) and an off-season variant
  (countdown strip). The 2026 season goes live ~late-Aug (Week 0 = Aug 29, 2026).

## SUCCESS CRITERIA (how we judge "best in class")
- A first-time visitor answers three questions within one viewport: who is #1 and why, who moved
  and why, and what is THIS WEEK's story.
- Every number is sourced (confidence chip); every claim is cited (receipt).
- We visibly beat the named competitors on multi-level breadth (FBS→DIII on one board), fan
  sentiment, and model accountability.

## COMPETITIVE BAR (clear these, then state where we beat each)
- **ESPN FPI** — the table-UX bar: a ~16-column sortable probability table (rating, rank, trend,
  projected W-L, Win Out%, Playoff%, Make NC%, Win NC%), filterable by conference/year. Beat it on
  breadth (FBS→DIII), fan sentiment, and cited provenance.
- **The Athletic (Austin Mock, 100k-sim playoff model)** — the storytelling bar, but delivered as
  *articles*, not a living tool. Our opening: make model storytelling a standing, interactive surface.
- **On3/Rivals (Massey-powered)** — clean projected board (Pwr/Off/Def/HFA/SoS/Score). Match its
  table cleanliness, exceed its depth.
- **SP+ (Bill Connelly, now free at ESPN)** — list-embedded in articles, not interactive. Opportunity.
- **PFF** — grade-derived, gated behind PFF+. Their moat is player-grade provenance; ours is
  multi-signal + fan sentiment + cited claims.
- **Craft references (live):** NYT Upshot, Bloomberg Markets. **538 = iconic but defunct.**

## DELIVERABLES (spec only — no code this run)
1. A one-paragraph redesign THESIS (the through-line idea).
2. A shared MODULE CONTRACT: each module's purpose, data source, which of the 6 charts, token usage,
   confidence + receipt treatment, and mobile behavior.
3. Per-surface markdown WIREFRAMES (main board, conference page, archive snapshot) showing module
   order within the Dashboard spine.
4. A REUSE MAP: which existing renderers/functions each module touches.
5. A PHASED BUILD RECOMMENDATION — weigh SURGICAL (patch `render_rankings_page_html` plus the
   conference/archive renderers) vs ARCHITECTURAL (seed the design system's planned
   `src/cfb_rankings/dashboards/renderer.py` consolidation). Recommend a path with effort estimates.

## PROCESS
Run the Double Diamond. Reuse the prior audits above. Preserve provider disagreements (do not
average them). Write outputs in the `docs/octopus` house style. Put a multi-LLM debate gate at the
Define→Develop boundary before locking scope.

---

## 2026 LIVE CONTEXT (researched 2026-06-08)
_Curated freshness input (Perplexity unavailable). Every factual claim carries a source; synthesis/
white-space claims are flagged as strategic assertions, not facts._

### What top CFB outlets currently show
- **ESPN FPI** — sortable ~16-col table: FPI rating, rank, trend, projected W-L, Win Out%, Win Div%,
  Win Conf%, **Playoff%**, Make NC%, Win NC%; filter by conference and year back to 2005. The most
  feature-rich rankings surface in the market. (espn.com/college-football/fpi)
- **SP+ (Connelly)** — free at ESPN since May 2025, but published as article-embedded *lists*
  (off/def/special-teams ratings, returning production), not an interactive table.
- **ESPN Allstate Playoff Predictor** — pick-your-path scenario simulator layered on FPI.
- **The Athletic / Austin Mock** — 100k-sim CFP model (EPA/play + success rate, adj. for location/
  weather/injuries); round-by-round + title odds, delivered as articles.
- **On3 (now Rivals)** — Massey-powered projected board: Pwr, Off, Def, HFA, SoS, Score + conf filter.
- **PFF** — grade-derived power ratings, gated behind PFF+.
- **247Sports Composite** reduced to 3 feeds (247/ESPN/On3 at 33.3% each) after **On3 acquired Rivals
  (closed ~Jul 2025, Yahoo stake)** — relevant only if we ever blend recruiting "talent."
- **Sports-Reference / Stathead** — owns deep historical query (paid), not modeling or viz.

### Best-in-class data-viz UX patterns (2025–2026)
- **FiveThirtyEight fully shut down Mar 5, 2025** — dead, not dormant; do not cite as a live benchmark.
- No single 538 successor — role fragmented. For *sports*, live torch-bearers are **NYT Upshot** and
  **The Athletic data desk** (both under NYT).
- Current "good" sports-viz leans on **annotated trend lines / chart-as-argument with explicit
  annotation**, not dashboards for their own sake (Sportico 2025 charts-of-the-year).
- Dominant patterns: table-first sortable/filterable dashboards (ESPN FPI is the genre exemplar),
  fan-driven scenario simulators, inline probability/odds columns, **model-vs-poll** framing as a hook.

### 2026-specific CFB facts that reframe a rankings product
- **CFP stays 12 teams for 2026** (expansion left unresolved; decided Jan 23, 2026). Build for 12,
  treat format as visibly contested.
- **Straight seeding (2025→2026):** top 4 *ranked* teams get byes; conf champs no longer auto-seeded
  into the top 4 (5 highest-ranked conf champs still get bids; ND can earn a top-4 bye). → **"Where the
  committee ranks you" is now the load-bearing number** — foreground committee-rank / seed delta.
- **Pac-12 relaunches Jul 1, 2026 as a 9-member league** (Oregon State, Washington State + Boise State,
  Colorado State, Fresno State, San Diego State, Utah State, Texas State; Gonzaga non-football) on a
  CBS/CW/USA package; Mountain West thinned. → Conference filters/logos/standings must reflect 2026
  realignment.
- **2026 calendar:** Week 0 = Sat Aug 29, 2026 (intl games); main kickoff Labor Day weekend (Thu Sep 3→).
  Plan the season-live switchover around late-Aug 2026.

### White space nobody owns (strategic assertions — our moat)
- **One unified multi-division board (FBS→FCS→DII/DIII/NAIA):** every incumbent caps at ~136 FBS teams.
- **Published, audited model-accuracy track record:** with 538 gone, nobody prominently shows their own
  historical hit-rate/calibration — aligns with our confidence-band/calibration system.
- **Fan-sentiment as a first-class ranking signal:** incumbents are performance/recruiting-only.
- **Sourced/cited ranking claims (receipt pattern):** outlets assert ratings; almost none inline-cite
  the evidence behind a team's movement.
