# World-Class Visual & UX — Implementation Plan

_Dated 2026-05-18. Synthesizes three strategic docs (`CFB_INDEX_VISUAL_SYSTEM_CONCEPT.md`, `CFB_INDEX_IDENTITY_PRODUCTION_PLAYBOOK.md`, `CHATGPT_VISUAL_SYSTEM_RUNBOOK.md`), the 250+ rule catalog in `docs/octopus/visual_ux_recommendations.md`, the 15 `docs/design-system/*.md` specs, and the two world-class briefs (`PLAYER_PAGE_WORLD_CLASS_BRIEF.md`, `TEAM_PAGE_WORLD_CLASS_BRIEF.md`) into a sequenced delivery plan with explicit dependencies and success criteria._

## The North Star

> "If you covered the logo and the masthead, would this still look like us?" — from `CFB_INDEX_VISUAL_SYSTEM_CONCEPT.md` §9

The visual concept doc proposes a 90-day production plan oriented around **producing** 500+ bespoke illustrations. The world-class briefs and design-system specs propose the **structural** components that frame those illustrations. This plan combines both tracks into 6 phases over ~14 weeks.

## Where we are (2026-05-18)

**Already shipped (✅ live or queued in publish):**
- PR #131 — Tier-1 art (36 PNGs) wired to hub: 18 totems on archetype cards, 8 modifier glyphs on chips, 8 rubrics on section eyebrows
- PR #133 — Team logos on team-page heroes (664 teams, deterministic URL emit)
- PR #134 — Tabular numerals + reduced-motion enforced globally
- PR #132 — Recommendations doc (250+ rules synthesized into 4 tiers)

**Production status of the asset library:**
- Tier 1 (foundation, ~34 images): **100% produced** — wired this session
- Tier 2 (depth, ~150 images: helmets + rivalry coins + migration diagrams): **0% produced**
- Tier 3 (atmosphere, ~80 images: stadium silhouettes + fan-type portraits + field-notes): **0% produced**
- Tier 4 (covers + commiseration + lexicon, ~140 images/year): **0% produced** (1 author portrait done)

**Specs status (from `docs/design-system/`):**
- All 15 specs are LOCKED (tokens, atoms, modules-hero, modules-season, modules-intel, modules-archive, modules-game-recap, page-compositions, page-archetypes, chart-vocabulary, receipt-pattern, confidence-signaling, integration-playbook, unified-design-tokens)
- Implementation coverage of the locked specs is partial — see Phase 2 audit.

---

## Phase 1 — Foundation (DONE)

**Goal:** Lock the tokens + cardinal typography rules + Tier-1 art so every subsequent phase has rails.

| Deliverable | Status | Verification |
|---|---|---|
| Tabular numerals on stat-class elements | ✅ PR #134 | Live in publish 26011857294 |
| Reduced-motion guard | ✅ PR #134 | Same |
| Team logos on team pages | ✅ PR #133 | Same |
| Tier-1 art wired to hub | ✅ PR #131 | Live in publish 26011469761 |
| Design recommendations doc | ✅ PR #132 | On master |
| URL helper module (`illustrations.py`) | ✅ PR #131 | On master |
| Confidence chip prototype (Heisman Lens + hero) | ✅ PR #137, PR #140 | Live in publish 26015396877 (in flight) |
| Chart vocabulary audit | ✅ PR #139 | `docs/octopus/chart_vocabulary_audit.md` |
| OG/twitter meta sweep (~14 surfaces) | ✅ PRs #141, #142, #146, #148, #149, #150, #151 | Live in publishes |
| SEO foundations (robots.txt + sitemap.xml with team URLs) | ✅ PR #145, PR #153 | Live after next publish |
| Workflow stability (fanintel-gameday module, publish-site 404 copy) | ✅ PR #143, PR #147 | Active on next workflow runs |

**Done — close Phase 1. Cumulative: 19 PRs (#131-#154).** Plus Phase 1.5 SEO + workflow bonus items added during the 2026-05-18 sleep-session.

---

## Phase 2 — Design-token migration + chart vocabulary enforcement (~2 weeks)

**Goal:** Migrate the global stylesheet from legacy hex tokens to the locked v5 OKLCH ramp, then audit existing SVG charts against the locked 6-type chart vocabulary.

### 2A — Token migration (1 week, ~3 PRs)

**Risk:** medium. Touches the global stylesheet. Visual regression possible. Mitigation: ship in 3 PRs (semantic aliases → component overrides → legacy cleanup) so each step is reversible.

**Deliverables:**
1. **Add v5 token block** to `cfb_rankings/reporting.py:_compose_global_css()` as a new `_V5_TOKENS_CSS_BLOCK` that lays alongside the existing `_FIGMA_V5_TOKENS_CSS_BLOCK` (which exists). Confirm the v5 block defines the 6 color ramps × 7 stops from `docs/design-system/00-tokens.md` (navy / coral / amber / gray / green / red).
2. **Wire semantic aliases** — `--color-text`, `--color-text-muted`, `--color-surface`, `--color-surface-card`, `--color-line`. Add dark-mode override block.
3. **Migrate top 10 high-traffic components** to use the new aliases instead of legacy hex literals. Audit `reporting.py` grep for `#1a1a1a`, `#FAFAFA`, `#DC2626`, `#E0A300`, replace with `var(--color-*)`.

**Acceptance:** view sources of `/`, `/rankings/`, `/teams/alabama.html`, `/hub/`, `/players/quinn-ewers-39300.html` — no hex literals remain in `<style>` blocks; all CSS uses tokens.

### 2B — Chart vocabulary enforcement audit (1 week, ~2 PRs)

**Goal:** Per `docs/design-system/31-chart-vocabulary.md`, exactly 6 chart types are permitted (percentile bar, trajectory spark, bump chart, annotated line, small multiples, heatmap). Vertical bar / pie / radar / 3D charts are FORBIDDEN.

**Deliverables:**
1. **Audit script** — grep all SVG-emitting code in `reporting.py` + `team_pages/` + `editions/`. List every chart type produced.
2. **Refactor PR** — replace any unauthorized chart types with their canonical equivalent. Common candidates: vertical bar charts → percentile bar; pie/donut → small multiples or annotated line; radar → only Player Fingerprint hero context.
3. **Annotated chart linter** — assert that every chart in player + team pages has its caption (identity) + on-chart annotations (story), per the chart-vocabulary spec.

**Acceptance:** rendered sample of 10 chart-containing pages, all charts conform to one of the 6 types.

**Risk if skipped:** the visual system can't lock until charts conform; otherwise the brand identity drifts every time a new chart ships.

---

## Phase 3 — Component refactors per locked specs (~3 weeks)

**Goal:** Activate the locked v5 component specs (`docs/design-system/10-modules-*.md`) where the renderer currently ships old patterns.

### 3A — Player Hero Fingerprint (1 week, 1 PR)

**Spec:** `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` §Hero, locked.

**Current state:** legacy player hero has team_name + position + jersey + class as text; no fingerprint structure.

**Target:** 3-column vibe-cells hero with name + one signature number + trajectory spark + accolade pill.

**Risk:** medium — player pages are the highest-volume surface (~44k pages). One bad layout regression is visible site-wide. Mitigation: ship behind a feature flag (default off), preview 5-10 sample players, flip flag once verified.

### 3B — Player Standing 17-rung ladder (1 week, 1 PR)

**Spec:** `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` §Player Standing, locked at 17 rungs.

**Current state:** no standing visualization; player rank is shown as a number.

**Target:** SVG ladder rail with 17 ticks (Walk-on → POTY Winner), gold marker at current rung, three-read drill-down (rail / tier-pills / rung-drawer).

**Effort estimate:** SVG rail at 200 LOC + Python helper that maps accolades to rung index at 150 LOC. Manageable.

**Risk:** low. Additive (existing player rank text stays). New module slots in below the hero.

### 3C — Game-log table (1 week, 1 PR)

**Spec:** `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` §Game Log, locked.

**Current state:** missing. The site has season-summary stats but no game-by-game breakdown — significant data-parity gap vs ESPN/247Sports.

**Target:** table per the spec — date / opponent / result / key stats / longest play / advanced micro-metric.

**Dependency:** confirm `player_game_stats` table coverage. Spec assumes weekly data. If only partial coverage, ship the table with honest "Awaiting Signal" rows for missing weeks.

**Risk:** medium. Data-coverage gaps may surface mid-build. Mitigation: prototype against Quinn Ewers (full coverage) first, then expand.

---

## Phase 4 — Tier-2 art production sprint (~2 weeks)

**Goal:** Produce the next ~150 bespoke images per the Tier-2 spec.

This is a CONTENT production sprint, not a code sprint. Each batch follows the `CHATGPT_VISUAL_SYSTEM_RUNBOOK.md` workflow (Art Director GPT + master plate + 4-6 candidates per asset + curation).

### 4A — Team helmet silhouettes (1 week, ~133 PNGs)

**Spec:** `CFB_INDEX_VISUAL_SYSTEM_CONCEPT.md` §2.1, ligne-claire helmet profile per FBS school in team primary color.

**Production approach:** batch generation via OpenAI API per the runbook §6. ~6 candidates per school × 133 = ~800 generations. ~$15-20 in API cost per the runbook. Then 4-6 hours of curation.

**Wire-up:** once produced, drop into `assets/team-art/<slug>/helmet.png`, extend `illustrations.py` with `helmet_url(slug)`, wire into:
- 20-28px team chips wherever a team is referenced
- 80px on team-page hero (alongside the logo)
- 200px on the Heisman board (next to player team)

### 4B — Rivalry coin marks (3 days, 12 PNGs)

**Spec:** §2.2, ligne-claire coin/seal format per flagship rivalry.

**Production:** 6 candidates × 12 = 72 generations. ~$2 API cost. 1 hour curation.

**Wire-up:** drop into `assets/illustrations/rivalry-coins/`, extend `illustrations.py` with `rivalry_coin_url(rivalry_slug)`, wire into:
- Hub N° 05 Rivalry section (each rivalry cell shows its coin)
- Team page rivalry-card module
- New: `/rivalries/<slug>/` landing page per coin

### 4C — Archetype migration diagrams (3 days, 5 PNGs)

**Spec:** §2.3, halftone engraving on bone paper.

**Production:** 6 candidates × 5 = 30 generations. ~$1 API cost.

**Wire-up:** marginal illustrations in the N° 04 Taxonomy section closer paragraph.

**Acceptance for Phase 4:** ~150 new bespoke assets shipped to live site. Team chips across the entire site now show helmet silhouettes. Rivalry pages now have coin marks. Migration diagrams visible in the taxonomy section.

---

## Phase 5 — Editorial weekly cadence (ongoing from launch week 1)

**Goal:** Establish the recurring per-issue art commitment that compounds into the archive moat.

Per `CHATGPT_VISUAL_SYSTEM_RUNBOOK.md` §7, weekly art commitment = 3 images per issue:

1. **One cover** (risograph, 1200×800) — Monday brief, Tuesday generation, Wednesday commit
2. **One commiseration cartoon** (halftone, 400×300) — same day as cover
3. **One lexicon panel** (risograph, 400×400, optional) — Wednesday if the week's featured phrase warrants

**Total weekly cost:** ~4 hrs/week of art-director time (per the runbook).

**Wire-up:** the issue renderer needs to look up each issue's `cover_art_path`, `commiseration_art_path`, `lexicon_panel_art_path`. Schema migration: add these to `hub_issues` table.

**Backfill option:** retroactively cover Vol V N° 040 → N° 047 (8 issues) to populate the archive visually before going live. Per the runbook this is a one-time 1-day sprint.

**Acceptance:** every issue page from this week forward has cover + commiseration + (optional) lexicon panel. Archive page becomes a visual history of the season.

---

## Phase 6 — Moat layer (~6-8 weeks, can run in parallel after Phase 4)

These are the high-leverage long-term investments per the visual system / playbook. Each is its own self-contained project.

### 6A — Editorial Receipt Pattern (2-3 weeks)

**Spec:** `docs/design-system/32-receipt-pattern.md`, locked.

**Scope:** inline `[N]` citation markers on every AI-generated factual/interpretive claim, hover/tap source detail, footer citation list, citation_critic validation gate.

**Schema migration:** new `editorial_citations` table.

**Wire-up:** Pattern C/D prompt revision + citation extraction + per-piece footer renderer + the validation gate.

**Why it matters:** trust + uncopyable provenance moat. Without this, the AI editorial reads as opaque assertion; with it, it reads as defensible journalism.

### 6B — Confidence Signaling expansion (1-2 weeks)

**Spec:** `docs/design-system/33-confidence-signaling.md`, locked.

**Current state:** zero confidence signaling visible. Every metric reads as equally trustworthy.

**Target:** three-band chips (✓ high / • medium / ? low / suppress) on top-traffic stat surfaces (player Heisman lens, team Mood Card, signature story, season arc).

**Schema migration:** `confidence_calibration` table per quarter.

**Wire-up:** new `confidence_pill.py` helper + thread `confidence_band` through 3-4 surfaces. Don't try to retrofit every stat in one PR; pick the highest-traffic + highest-data-variance surfaces.

### 6C — Container queries refactor (2-3 weeks)

**Spec:** `docs/design-system/01-atoms.md` + `34-integration-playbook.md`.

**Current state:** responsive layout is viewport-based.

**Target:** every module adapts to its container, not viewport. Same `.fi-mood-card` works at 100% phone width and 50% desktop width.

**Risk:** medium. Refactor touches every module's CSS.

**Why now:** unblocks proper module portability (the same card used in hub, team page, embed all behave correctly).

### 6D — Alpine.js progressive enhancement (1 week)

**Spec:** `FRONTEND_ARCHITECTURE_DECISION.md`, locked.

**Current state:** existing JS is vanilla; no progressive-enhancement framework.

**Target:** add Alpine.js 3.x (~14KB gzipped) for filter toggles, drawers, tabs, URL-sync. Migrate ad-hoc inline JS to Alpine `x-data` / `x-show` / `x-on:click`.

**Why now:** Cmd-K (Window B's #122) + future interactive modules benefit from a consistent framework. Vanilla is acceptable; Alpine is much faster to author against.

---

## Phase 7 — Tier-3 + Tier-4 production (multi-month, batch)

Per the runbook §7, ongoing library work + per-issue commitments. Items:

- Stadium silhouettes (40-60 generic profiles)
- Editorial-generic fan portraits (10-15 anonymous types: "The Dad at the Tailgate", "The Alumni Returner", "The First Game", "The Sign Holder")
- Field-notes marginal pencil diagrams (X's & O's, blackboard sketches)
- Tradition illustrations (Dotting the I, Enter Sandman, The Grove tailgate, The 12th Man sign — 30-40 total)
- Historical moment illustrations (Flutie Hail Mary, Bush Push, Kick Six, Music City Miracle)
- Decade markers for archive navigation (10s, 20s, 30s)

**Cadence:** 8-12 new library assets per month via batch sprints during quieter weeks. Per the runbook this is the "library work that happens in batches" pattern.

---

## Phase 8 — Moat-tier strategic investments (multi-quarter)

These are mentioned in the playbook but require executive decisions, not implementation:

- **Custom display face licensing** — the playbook flags this as a strategic moat investment (alongside The New Yorker's Irvin, The Economist's Ecotype). Long-term brand identity.
- **Long-term illustrator relationship** — Barry Blitt 30+ years at The New Yorker. Find one human illustrator to commission ~6-12 covers a year alongside the AI cadence; the human covers become the moat.
- **Per-player generated OG images** — replace the site-default `og-image.svg` with per-player generated cards (uses player headshot + key stat + team accent). Requires the OG image pipeline + ~50k generated SVGs.

---

## Cross-cutting concerns (apply to every phase)

### Accessibility budget — never compromised
Every phase must:
- Meet WCAG 2.1 AA contrast (3:1 graphical, 4.5:1 text). Use design-system OKLCH ramps which pass at every step
- Include skip-link + landmark structure
- Respect `prefers-reduced-motion` (Phase 1 enforced this globally)
- Include alt text on every meaningful image; empty alt on decorative
- 44×44px touch targets
- Keyboard nav for every interactive element

### Performance budget — never compromised
- FCP < 0.8s on 4G
- LCP < 1.2s
- CLS < 0.02
- JS payload < 35KB gzipped per page
- Images: webp + avif with srcset; zero layout shift
- Fonts: `font-display: swap` with metric-matched fallback

### Verification protocol (per `CFB_INDEX_IDENTITY_PRODUCTION_PLAYBOOK.md`)
Every PR:
1. Smoke-test syntax (Python ast.parse + smoke-test renders)
2. Diff against `origin/published` after publish
3. Quote the actual change on a live URL in the PR description
4. Roll forward, never roll back without a HARD-NO documented in `define.md`

---

## Total effort + sequence

| Phase | Effort | Dependencies | Risk |
|---|---|---|---|
| 1 Foundation | DONE (5 PRs) | — | — |
| 2 Tokens + chart vocab | 2 weeks (5 PRs) | Phase 1 | medium |
| 3 Component refactors | 3 weeks (3-4 PRs) | Phase 2 (uses new tokens) | medium |
| 4 Tier-2 art production | 2 weeks (content sprint) | Phase 1 helpers | low |
| 5 Editorial weekly cadence | ongoing from week 1 | — | low |
| 6A Receipt Pattern | 2-3 weeks (3-4 PRs) | parallel to others | medium |
| 6B Confidence signaling | 1-2 weeks (2-3 PRs) | parallel to others | low |
| 6C Container queries | 2-3 weeks (refactor) | parallel to others | medium |
| 6D Alpine.js | 1 week (1-2 PRs) | parallel to others | low |
| 7 Tier-3/4 art | rolling, 8-12/month | — | low |
| 8 Moat investments | multi-quarter | executive decision | n/a |

**Total: ~14 weeks of focused work** for Phases 2-6. Phase 7 (rolling library) and Phase 8 (moat) are unbounded.

## Critical dependencies

The dependency graph is mostly linear-ish:

```
Phase 1 (DONE)
  │
  ├──► Phase 2A (tokens) ──► Phase 2B (chart vocab) ──► Phase 3 (components)
  │                                                          │
  ├──► Phase 4 (Tier-2 art)  ────────────────────────────────┤
  │                                                          │
  ├──► Phase 5 (editorial cadence — starts week 1) ──────────┤
  │                                                          │
  └──► Phase 6 (parallel tracks, no inter-deps) ─────────────┘
                                                             │
                                          Phases 7-8 (rolling, ongoing)
```

The ONE hard dependency: Phase 3 (component refactors) requires Phase 2A (tokens) because the components are spec'd against the v5 OKLCH ramps. Don't refactor before tokens land.

Everything else can run in parallel, including the Tier-2 art production (Phase 4) which is content work disjoint from code.

## What to do FIRST when this plan is approved

Phase 2A token migration is the highest leverage next move. Three reasons:
1. **Unblocks Phase 3** — every component refactor needs the new tokens to be in place.
2. **Visible immediately** — once tokens migrate, dark mode lights up, color consistency tightens across the site.
3. **Lowest risk in the dependency chain** — token migration is purely CSS; reversible with a one-PR revert.

After Phase 2A, the next decision: do Phase 4 (art production sprint) and Phase 3 (component refactors) in parallel, or sequence them? **Recommendation: parallel.** Art production is content work that doesn't touch code; component refactors don't touch art assets. Two independent tracks.

## When this plan succeeds

Every CFB fan who lands on the site recognizes it as **The CFB Index** — not a sports analytics dashboard, not a generic data site. They:
- See bespoke illustrations (totems, helmets, rivalry coins) on every team-page hero
- Read editorial copy with inline source citations
- Watch confidence chips on every stat so they know which numbers to trust
- Get instant search via Cmd-K from any page
- Find the same module looking right at 100% phone width AND 50% desktop width
- See the same paper-cream bone substrate and amber accent on every image and chart
- Pull an old archive page in 2030 and the visual voice still reads

The screenshot test from `CFB_INDEX_VISUAL_SYSTEM_CONCEPT.md` §9 — "if you covered the logo and the masthead, would this still look like us?" — passes for every page.
