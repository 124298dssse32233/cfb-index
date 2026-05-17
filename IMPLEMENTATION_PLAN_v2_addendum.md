# IMPLEMENTATION_PLAN — v2 Addendum
# Net-new sprints that integrate with the original IMPLEMENTATION_PLAN.md
# See IMPLEMENTATION_PLAN_v3_iteration.md for refinements + acceptance criteria + tier strategy

**Status:** Authoritative net-new work to insert into the existing 17-week plan.
**Owner:** Window B (per COORDINATION.md)
**Last updated:** 2026-05-16

---

## Part 0 — Synthesis Approach

This addendum identifies the **genuinely new work** that the existing `IMPLEMENTATION_PLAN.md` doesn't cover. It deliberately avoids duplicating:
- Already-shipped infrastructure (v5-1 foundation, Pattern C/E flag flips, hotfixes 1-15, pre-2020 backfill, DB sanity gate, CostMeter, Batch API)
- Already-specified work (team page state-resolver, player page reading-ladder, three illustration families, six-ramp color, dark-mode share-card tokens, profile vocab/mascot_voice/stock_phrases system)
- Already-scheduled sprints (v5-2 through v5-12 in the main plan)

What survives that filter is the **net-new work this addendum adds**. Window B owns execution of these inserted sprints.

---

## Part 1 — What's Already Done or Specified

### Already shipped to production (don't rebuild)
- Pattern C/E AI critique loops on Edition cover, Daily, Heisman, Mailbag, Reactions (v5-2/v5-3/v5-4)
- 16 SQL migrations including `llm_usage_log`, `circuit_state`, `quality_gates` (v5-1 Day 3)
- CostMeter + per-surface ceilings + telemetry (PR #51, #65)
- Batch API path on 6 surfaces (v5-1.5 commit 1cd48ce9)
- 8 new offseason workflows (v5-1 Day 4)
- `cfb_calendar.py` + 33 tests (v5-1 Day 2)
- DB sanity gate / artifact poison terminator (PR #57)
- Pre-2020 historical backfill (12 seasons; run 25957715382)
- Pattern C cover essays for W18, W19 + auto-essay workflow wiring (hotfix-9, #69, #75)
- Per-team voice palette in `profiles/*.md`: `vocab`, `mascot_voice`, `stock_phrases`, `never_use`, `always_surface`, `voice_register`, `tonal_template`, `rivalries`, `aspiration_ladder`, `heritage`, `coaching_regimes`, `era_annotations`
- Six-ramp color system + 3 semantic ramps (`docs/design-system/00-tokens.md`)
- Three illustration families (`CFB_INDEX_VISUAL_SYSTEM_CONCEPT.md`)
- Reading-ladder pattern (`PLAYER_PAGE_WORLD_CLASS_BRIEF.md`)
- State-aware page compositions (`docs/design-system/20-page-compositions.md`)
- All major team_pages modules: `the_room_renderer`, `pulse_lede`, `pulse_themes`, `chronicle_*`, `season_arc_card`, `rivalry_card`, `savant_card`, `game_recap_hero`, `narrative_generator`, `historical_season_*`

### Already scheduled in existing IMPLEMENTATION_PLAN (Window A owns)
- 17 bespoke per-program renderer modules (v5-9)
- 19 player position + archetype surfaces (v5-10a)
- 8 Tier-1 rivalry pages with Claude SVG trophies (v5-10b)
- 25 trophy SVGs (v5-0; status unknown — Window A should verify)
- 11 prompt templates (v5-0; status unknown)
- 17 profile-schema extensions for `signature_metrics_ladder`, `archetype_tags`, `lexicon_anchors`, `cohort_register` (v5-0; status unknown)
- Visual asset system + helmet stripes (v5-6b)
- Pillow OG card templates (10 of them) (v5-6a)
- `/admin/queue/` + `/admin/panic` (v5-8)
- Edition cover → Pattern D adversarial (v5-8)
- 12 Arctic Shift archive surfaces (v5-10d)
- 10 phase landings + 11 conference + 5 cross-program (v5-10c)
- 16 named data-source surfaces (v5-9)
- S1-S12 offseason content surfaces (spread across v5-1 through v5-10d)
- 9 tentpole editions with manual covers (spread across v5-6b through v5-11)
- Voice-validator regression suite (v5-11)
- Post-publish HTML audit (v5-11)
- Observability dashboard (v5-12)

---

## Part 2 — The Net-New Work (8 Initiatives)

After subtracting Part 1 from prior research, here are the 8 genuinely new initiatives. Ranked by impact-per-effort.

### NEW-1: Hero Finding pattern across Hub, Daily, Heisman, Editions ⭐⭐⭐⭐⭐
Bloomberg/538 pattern — every page leads with a *finding* (number + sentence + sample-size caption) before any chart or prose. Not in any existing brief. Single biggest moat-visibility lever.

### NEW-2: Receipt Pattern for AI editorial ⭐⭐⭐⭐⭐
Inline source citations on every Pattern C/D claim, hover-revealable to show the Reddit thread, beat writer column, podcast quote that fed it. Not in any existing brief or sprint. Single biggest credibility lever for AI content in the 2026 post-AI-flood era.

### NEW-3: Sample-size signaling system ⭐⭐⭐⭐
Every named metric on every page gets a `[n=247 · medium confidence]` chip. Plus methodology links. Not in any existing brief.

### NEW-4: Mobile-forward Saturday Strip UI primitive ⭐⭐⭐⭐⭐
Sticky-at-top mobile element: in-season shows live games scrolling, off-season shows countdown + portal news. Not in any existing brief. Single biggest mobile daily-return habit driver.

### NEW-5: Per-team Rituals & Cultural Identity surfacing ⭐⭐⭐⭐
Profile data system exists; what's missing is an *explicit traditions/rituals module* on each team page. Hawkeye Wave on Iowa page. White Out on Penn State. Howard's Rock on Clemson. Hero-rotation element, not buried metadata.

### NEW-6: Monday Mood Map weekly viral artifact ⭐⭐⭐⭐⭐
Auto-generated 1200×675 image showing all 130 FBS team moods, posted to X every Monday 9am ET. Not in any existing brief. Single highest-leverage viral artifact your moat enables.

### NEW-7: Full-page dark mode ⭐⭐⭐
Share-card dark tokens exist; full-page doesn't. Late-night CFB reading is a real use case.

### NEW-8: Command-K power-user navigation ⭐⭐⭐
Universal search-and-jump across 663 team pages + 40k+ player pages + editions + methodology. Not in existing brief. Power-user habit driver.

---

## Part 3 — Sprint Integration with existing IMPLEMENTATION_PLAN

The existing plan runs v5-0 through v5-12 (May 18 – Sept 18). This addendum inserts new sprints between existing ones rather than replacing. Net add: ~5 weeks across the 17-week plan when run serially; ~2-3 weeks when run in parallel with Window A.

### Sprint v5-5.4 (insert FIRST) — "Mockup Sprint" — 1 week
**Goal:** Produce 7 high-fidelity HTML mockups using real data and locked tokens. No functionality, no AI generation, no data binding. Just pixels.

**Deliverables (each in `docs/mockups/`):**
1. `mockup_01_hub_v2.html` — Hub with hero finding + movers board + cohort divergence + methodology footer (mobile + desktop)
2. `mockup_02_team_alabama_v2.html` — Alabama team page with hero, rituals strip, Chronicle cards, season arc, pulse module
3. `mockup_03_team_vanderbilt_v2.html` — Vandy using same archetype but different voice/emphasis
4. `mockup_04_daily_v2.html` — Daily article with auto-summary, hero finding, receipt-pattern citations, pull quotes
5. `mockup_05_heisman_v2.html` — Heisman page with horse-race chart, bubble watch, historical comparison
6. `mockup_06_saturday_strip.html` — Mobile-only mockup, both in-season and off-season states
7. `mockup_07_monday_mood_map.png` — Static image render of the viral artifact

**Process:**
- HTML+CSS in `docs/mockups/` directory (NOT Figma — already decided)
- Use the live site's CSS as foundation
- Pull real data from the live DB so the mockup uses real names, real numbers, real recent events
- Mobile-first: design 390px wide, then expand to desktop

**Why this matters:** Catches IA problems before coding. Gives every subsequent sprint a *visual target*. Becomes the test artifact.

**Acceptance criteria:**
- 7 mockup files in `docs/mockups/` (named per spec)
- Each renders correctly at 390px, 768px, and 1280px
- Uses real data (no Lorem Ipsum)
- Uses locked typography stack
- Saturday Strip mockup uses both in-season and off-season variants
- Hub mockup leads with hero finding pattern from real DB data

**Kill criteria:** If mockups reveal a fundamental IA flaw, stop and re-plan before continuing to v5-5.5.

### Sprint v5-5.5 (insert after v5-5.4) — "Foundational Decisions Sprint" — 1 week

**Goal:** Lock 5 foundational design decisions. No production code shipping; specification work.

**Deliverables:**
- Updated `docs/design-system/00-tokens.md` with locked typography stack + tabular-nums CSS rule (the existing Inter + Source Serif Pro stays; ADD display font Bebas Neue and tabular numerals enforcement)
- New `docs/design-system/30-page-archetypes.md` documenting the 6 IA archetypes:
  1. Article (Daily, Mailbag, Reactions, Edition essays)
  2. Dashboard (Hub, Heisman, Power Rankings)
  3. Profile (Team, Player, Coach, Conference)
  4. Database (Wire, Editions archive, Canon lists)
  5. Tentpole (9 marquee editions)
  6. Anniversary/Retro (Today in CFB History, Saturdays Past)
- New `docs/design-system/31-chart-vocabulary.md` documenting the 6 allowed chart types + forbidden list:
  - Allowed: percentile bar, trajectory spark, bump chart, annotated line, small-multiples grid, heatmap
  - Forbidden: pie charts (always), bar charts (use percentile bars instead), radar charts (except player fingerprint)
- New `docs/design-system/32-receipt-pattern.md` documenting:
  - Citation wire format (JSON schema for Pattern C/D output)
  - Render treatment (superscript markers, tooltip on hover, full citation list at footer)
  - `editorial_citations` table migration
  - Citation critic role addition
- New `docs/design-system/33-confidence-signaling.md` documenting:
  - 3 confidence levels (high/medium/low)
  - Thresholds calibrated per data domain (fan_intel, historical, model)
  - Visual treatment (colored chips)
  - When to suppress vs show "(insufficient data)"

**Why first:** Every subsequent sprint references these. Without locking, designers and AI prompts drift.

**Acceptance criteria:** 5 design-system docs updated/created with specific values, locked decisions.

### Sprint v5-6a.5 (insert after Window A ships v5-6a) — "Receipt Pattern + Visual Layer" — 1 week

**Goal:** Ship the receipt pattern so every Pattern C/D claim is sourced.

**Deliverables:**
- Extend `quality_loop.py` Pattern C output to include `citations[]` array
- Modify Pattern C system prompt to require source attribution
- Update factuality critic role (or add new `citation_critic`) to verify every claim has a source ID
- Extend `prompt_context/builders.py` 12 builders to pass *available_sources* into the prompt with stable IDs
- New `src/cfb_rankings/receipts/render.py` module: superscript renderer + tooltip + footer-list HTML
- New CSS partial: `receipts.css` for citation marker styling
- Migration: `editorial_citations` table (citation_id, generation_id, source_kind, source_url, source_label, source_date, created_at_utc)

**Verify after:** check live `/daily/` page — every claim that came from a Reddit thread or beat writer column now has a superscript citation.

**Acceptance criteria:**
- 100% of new Pattern C/D output has citations
- citation_critic catches missing citations 95%+ of time
- Live site shows citation superscripts in editorial content
- Hover/tap reveals source info

**Kill criteria:** If citation quality is <80% accurate after 2 weeks, demote to Pattern B and revisit.

### Sprint v5-7.5 (insert after Window A ships v5-7) — "Hero Finding + Sample-Size System" — 1 week

**Goal:** Every page leads with a hero finding. Every metric carries confidence signaling.

**Deliverables:**
- New `src/cfb_rankings/hero_findings/generator.py` module producing daily/weekly findings per archetype:
  - Hub finding (cohort divergence, mover anomalies)
  - Daily finding (lead claim from cover essay)
  - Heisman finding (race shift, comparable historical context)
  - Editions finding (cover essay lead, pulled forward)
- New CSS partial: `hero_finding.css` — 36-48px display number + 14-16px body sentence + 12px caption
- Every page archetype renderer now expects a `hero_finding` field at the top
- Sample-size signaling shipped site-wide: every chart, every metric chip, footer-data-depth line
- New `src/cfb_rankings/confidence.py` module with calibrated thresholds + render helpers

**Acceptance criteria:**
- Hero finding generated daily for 5+ archetypes
- Findings vary across days (no robotic repetition)
- Sample-size chip on every named metric
- Generator runs in <30 seconds

**Kill criteria:** If hero findings sound robotic for 3 consecutive days, pause and reformulate.

### Sprint v5-7.6 (insert after v5-7.5) — "Saturday Strip + Mobile Foundation" — 1 week

**Goal:** Mobile-forward UX primitives that turn the site into a daily-return habit.

**Deliverables:**
- `src/cfb_rankings/mobile/saturday_strip.py` module — generates the strip data
- `src/cfb_rankings/mobile/saturday_strip.css` + small JS for auto-refresh
- Bottom navigation per existing world-class plan Phase 6 (5 items: Rankings, Teams, Players, Wire, Methodology)
- Add 30-second auto-summary at top of every article-archetype page (Pattern A LLM call, cached)
- Performance budget enforcement: Lighthouse CI on build, fail below 95
- Critical CSS extraction per existing plan

**Acceptance criteria:**
- Saturday Strip live on mobile, performs <500ms load
- Bottom nav shipped
- Auto-summary on articles
- Mobile FCP <1.5s on 4G; LCP <2.5s; CLS=0; INP<200ms

**Kill criteria:** If Saturday Strip has >5% error rate during gamedays, defer live ticker and ship countdown-only variant.

### Sprint v5-8.5 (insert after Window A ships v5-8) — "Rituals + Cultural Identity" — 1 week + ~10hr editorial

**Goal:** Distinctly-CFB cultural identity on every team page.

**Deliverables:**
- Add `rituals: []` field to all 17 profile YAMLs (3-5 per team)
- Add `cultural_anchors`, `visual_identity_anchors`, `data_emphasis` fields per spec
- New `src/cfb_rankings/team_pages/rituals_module.py` — renders rituals as part of profile-archetype page IA
- Update profile-archetype IA spec to include rituals module placement
- Editorial curation: ritual entries for all 17 teams (~30-60 min per team × 17 = ~10-17 hours)

**Acceptance criteria:**
- All 17 profiles have rituals data
- Rituals module renders on team pages
- Each ritual has: name, started_year, when_it_happens, description, image_asset slug, cultural_significance

### Sprint v5-10e (insert after Window A ships v5-10d) — "Viral Content Engine" — 2 weeks

**Goal:** Auto-generating viral artifacts that travel on X and CFB Twitter.

**Deliverables (5 viral formats):**
1. **Monday Mood Map** generator + Pillow image render + GitHub Action that posts to X
2. **Daily Belief Movers** card generator
3. **Pre-game packs** generator (Friday nights for Saturday games)
4. **Receipt cards** (when predictions resolve — leverages `predictive_claims` table)
5. **Quote cards** (Pitchfork-style shareable AI editorial quotes)

Each is a Pillow template + data pipeline + cron.

**Defer to post-launch:** AI-voice video format (too risky for first cycle).

**Acceptance criteria:**
- Mood Map auto-posts Monday
- 5 artifact types generating
- X engagement >100 likes/share within 4 weeks

**Kill criteria:** If viral artifacts get dunked persistently, pause and audit data accuracy.

### Sprint v5-11.5 (insert after Window A ships v5-11) — "Polish + Dark Mode + Command-K" — 2 weeks

**Goal:** Modern table-stakes features that signal "we ship complete products."

**Deliverables:**
- Full-page dark mode — invert bone paper to warm-ink-dark, keep accent palette (slight desat), test every chart/illustration in both modes
- Command-K interface — search bar overlay (Cmd-K on desktop, dedicated icon on mobile), indexes teams + players + editions + methodology, jump-to-result
- "What we got wrong" recurring Daily section — once a week, pull from `predictive_claims` resolved-wrong rows

**Acceptance criteria:**
- Dark mode on all archetypes
- Cmd-K indexed across teams/players/editions
- Both pass accessibility (WCAG 2.2 AA minimum)

**Kill criteria:** If dark mode introduces 10+ regressions, ship feature-flagged off and fix incrementally.

---

## Part 4 — Sprint Sequencing

```
Week 1: v5-5.4 (mockups)
Week 2: v5-5.5 (decisions) [Window B] || Window A continues current cleanup
Week 3-4: Window A ships v5-6a + v5-6b || Window B ships v5-6a.5 receipts
Week 5: Window A ships v5-7 || Window B ships v5-7.5 hero+samples
Week 6: Window B ships v5-7.6 mobile Saturday Strip
Week 7-8: Window A ships v5-8 || Window B ships v5-8.5 rituals
Week 9-13: Window A ships v5-9, v5-10a/b/c/d || Window B ships v5-10e viral
Week 14-15: Window A ships v5-11 || Window B ships v5-11.5 dark+CmdK
Week 16-17: Window A ships v5-12 launch retro || Window B supports
```

Net effect when running in parallel: full v5.x program completes ~4 weeks earlier than serial execution while including all addendum features.

---

## Part 5 — Cross-Sprint Concerns

### Visual mirror references
Specific patterns to mirror, by surface:
- **Hub:** Bloomberg Markets dashboard layout (hero finding + movers + restrained color)
- **Daily:** The Athletic columnist + NYT Upshot data essay hybrid
- **Heisman page:** FiveThirtyEight election dashboard horse-race + bubble watch
- **Team pages:** The Athletic columnist-per-writer pattern (shared design, per-author variation)
- **Wire:** Bloomberg terminal feed (variable-row weight, expandable detail)
- **Editions archive:** NY Magazine print archive (magazine cover wall)
- **Rivalry pages:** Pitchfork album review structure (hero art + score + dek + body)
- **Tentpole edition covers:** New Yorker covers (illustration-led, no chrome)
- **Confidence chips:** Anthropic model confidence + Stripe data confidence patterns
- **Command-K:** Linear's keyboard navigation
- **Saturday Strip:** Polymarket's top-ticker + ESPN's score bar (mobile pattern)
- **Receipt-pattern citations:** Wikipedia citation pattern (don't reinvent)
- **"What we got wrong":** 538's election post-mortems + Athletic beat-writer "changed my mind"

### Performance budgets (mobile-first)
- FCP < 1.5s on 4G
- LCP < 2.5s on 4G
- CLS = 0
- INP < 200ms
- Total JS < 50KB (compressed)
- Critical CSS inlined < 10KB
- Total fonts < 100KB (variable woff2)
- Enforced by Lighthouse CI; fails build below 95

### Accessibility commitments
- WCAG 2.2 AA across all archetypes
- WCAG AAA on Article archetype
- Color contrast 4.5:1 minimum (7:1 for AAA Article)
- Focus indicators on every interactive element
- Touch targets 44×44 minimum, 48×48 for primary actions
- Chart alt-text + `<table>` fallback
- `prefers-reduced-motion` honored (all transitions ≤100ms or instant)
- Full keyboard navigation with visible focus
- Axe DevTools automated scan must pass

---

## Part 6 — What This Addendum Deliberately Doesn't Cover

For honesty:
- AI-voice video format (too risky for solo dev cycle)
- Personalization / per-user experiences (premature at current scale)
- Native mobile apps (PWA only is correct)
- Community features (not the moat)
- Live gameday hub (ESPN owns this; Saturday Strip is enough)
- Bento grids (trend has peaked)
- Premium subscription path (Year 2 question)
- Custom domain swap (defer; Vercel URL is fine)
- Conference visual tints (risk of stereotyping outweighs differentiation)

---

## Part 7 — Single Most Important Discipline

**Sprint v5-5.4 (mockups) is a HARD GATE before any other addendum sprint.** Mockups force the design problem to be solved before engineering commits to it. Skip this and downstream sprints will refactor.

The other discipline that matters most: live-site verification after every deploy. Use `curl + grep` against `wonderful-margulis-8ec96b.vercel.app` (or `git show origin/published:<path>`) to inspect the actually-deployed HTML. Don't trust "the PR merged" as evidence the site changed.

See `IMPLEMENTATION_PLAN_v3_iteration.md` for tier strategy, acceptance criteria detail, technical-debt sequencing, and execution coordination.
