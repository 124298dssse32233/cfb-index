# Player Page World-Class Brainstorm — Research Trail

**Date:** 2026-04-22
**Canonical doc:** `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` (root). This file is the research trail / archive version; the brief is what downstream sessions should read first.

---

## Task framing

Kevin: "Do deep research on how to make our player pages world class. Start with quarterbacks specifically. Fully tap the Fan Intelligence framework. Present traditional stats like the best legacy mega-sites, but better. Best-in-class advanced stats via CFBD tier-2 + any other free APIs. Design/UX/frontend critical — must be readable for casuals AND analytical fans, with the "5s vibe → explore more" ladder. Figma will design from the guidance. Extend Heisman concept to All-American, All-Conference, All-Freshman, other awards."

Clarification answers:
- Deliverable format: **brainstorm in chat** (this archive is the written version).
- Fan Intel depth: **heavy — FI is the spine**.
- Data scope: **whatever it takes — propose the full stack**.

---

## Research inputs consulted

### Codebase
- `output/site/players/cj-carr-4788.html` — the actual rendered QB page (audit target).
- `src/cfb_rankings/fan_intelligence.py` — FI framework (team-scoped today).
- `src/cfb_rankings/reporting.py` — render paths for player pages (`_assemble_player_page_data` at line 2280, `render_player_page_html` at 732, `build_player_page_data_map` at 1630).
- `CLAUDE.md` — repo rules.
- Grepped for `player_mentions` / `player_conversation` / `entity_id` — confirmed FI has no player scoping today.

### Web research (full list in §12 of the canonical brief)
- CFBD API v2, tier 2/3, v2 GA, 2025 WP overhaul.
- cfbfastR function reference + `cfbd_pbp_data`.
- ESPN Total QBR methodology (Wikipedia + ESPN explainer).
- PFF QB grading (big-time throws, turnover-worthy plays).
- PFR advanced stats (aDOT, IAY, CAY, YAC).
- NFL Next Gen Stats data dictionary.
- Baseball Savant percentile card UX + red-blue gradient.
- nfelo QB rankings + era-adjusted design.
- NN/Group + IxDF on progressive disclosure.
- Figma web design trends 2026.
- CFB awards landscape: NCAA-recognized All-America selectors (AP/FWAA/AFCA/WCFF/SN), full 2025 selector pool (14 bodies), consensus vs. unanimous criteria, Shaun Alexander Freshman of the Year, FWAA Freshman All-America, position awards (Davey O'Brien, Manning, Unitas, Archie Griffin, Bednarik, Nagurski, Outland, Biletnikoff, Mackey, Thorpe, Groza, Guy).

---

## Iteration 1 — module list, data plan, roadmap

### Current CJ Carr page audit
Has: hero with rank chips, sticky subnav, Current Heisman Lens (6 stat-tiles), Signature Story (templated prose + 3 quirky cards), Current Season Production (summary ribbon + player-identity drawer + traditional season tables + advanced drawer with Passing WEPA/role share/usage splits + filterable stat explorer), Identity & Role bio, Recruiting Pedigree, Transfer Arc (empty), Trophy Case (placeholder), Honors Timeline (empty), Heisman By Year (one row), Roster Timeline.

### Missing vs. world-class
1. Zero FI tie-in (greenfield — biggest opportunity).
2. No game log.
3. No splits.
4. No charts (everything is tiles + tables).
5. No percentile card.
6. Thin advanced layer (no EPA/dropback, CPOE, aDOT, pressure, PA splits, deep ball).
7. No supporting-cast context (OL pressure, WR drops, scheme).
8. Generic Signature Story copy.
9. No peer comparator.
10. No Heisman trajectory chart.
11. Empty trophy case + honors for a Heisman-probable QB in Wk 21.
12. No NIL / market / hype valuation.

### Proposed module list (original v1)
Hero · QB Card · Fan Intel ("The Room on [Player]") · Heisman Trajectory · Current Season Production (traditional) · Advanced Metrics Savant card · Splits · Pass Chart · Supporting Cast · Peer Comparator · Heisman Lens rework · Signature Story (generative) · Trophy Case · Honors Timeline · NIL/Market · Bio/Recruiting/Transfer/Roster.

### Data-source inventory
Captured in §6 of the canonical brief. Key insight: one new ingestion dependency — player-entity tagging in the conversation pipeline — unlocks all player-FI modules.

### Roadmap v1
P0: Game log · Trajectory spark · QB Card · Percentile chips + sparks on every stat row.
P1: Savant card · Splits · Signature Story rewrite · Watch list + weekly awards ingest.
P2: Player-entity FI pipeline · Peer Comparator · Pass chart · Supporting Cast.
P3: "What needs to happen" scenarios · NIL+draft card · Live game mode.

---

## Iteration 2 — UX + Accolade Lens generalization

### UX reading ladder (the core unlock)
Four tiers. Every module declares which tier it serves.
- **5s** — Hero + QB Fingerprint.
- **30s** — FI card, top 3 stats, accolade probabilities. Casual-fan ceiling.
- **5m** — Game log, splits, full Accolade Lens, peer comparator, Signature Story.
- **Deep-dive** — Advanced Savant, pass chart, explorer, scheme context.

### UX primitives (9 atoms)
Percentile Bar · Belief Dial · Trajectory Spark · Eyebrow/Number/Narrative · Drawer · Tab Bar · Chip · Pill Comparator · Selector Grid.

### Color system (3 semantic ramps)
- Percentile: red → grey → blue (Savant convention).
- Belief: red → grey → green.
- Accolade: gold, reserved exclusively.

### Hero Fingerprint redesign
3-column desktop / vertical mobile. Middle column is five vibe cells:
1. CFB Index QB Score (0-100 composite).
2. Heisman Heat (rank + spark + probability).
3. Fan Belief (Dial + archetype).
4. Respect Gap (fan − national).
5. Reality Gap (fan vs. structural).
Right column: accolade ribbon (3 live awards + trajectory sparks).

### Fan Intel card — "The Room on [Player]"
Reuse `.mood-card` CSS. Four panels: Belief header · 3-axis strip · Storylines · Rival Heat pills. Empty-state falls back to team mood.

### Accolade Lens — the generalization
One module replaces today's "Heisman Lens." Tab per award stream (Heisman, Davey O'Brien, Manning, Unitas, Maxwell, Walter Camp, All-America, All-Conference, Shaun Alexander, etc.). Default tab auto-picked by player salience.

Unified grammar per tab:
1. Where he stands now (model rank / published projection).
2. What it would take (generated scenario tied to remaining schedule).
3. Trajectory (weekly probability line).
4. Official result (announced or "not yet awarded" + selector-sub-results ticker).

Three zones inside a tab:
- **Left — Ladder** (Watch list → All-conf → All-Am → POTY).
- **Middle — 3 probability tiles** (Win · Finalist · Ballot).
- **Right — "What needs to happen"** generated narrative.

**Below — Selector Grid.** Pill grid of AP/FWAA/AFCA/WCFF/SN/SI/Athletic/PFF/CFN/Athlon/Steele. Gold=1st, silver=2nd, grey=HM, empty=not yet. Best design idea in the doc.

**Polymorphism.** Swap tab set per position. DB → Nagurski/Bednarik/Thorpe. WR → Biletnikoff. TE → Mackey. OL → Outland. Ship polymorphic from day one.

### Mobile (65%+ of traffic)
Non-negotiable patterns captured in §5 of the canonical brief.

### Figma handoff brief
Captured in §8 of the canonical brief. 8-step commission order, 5-page file structure.

---

## Decisions locked in this session

- FI is the spine. Traditional stats are the foundation. Advanced stats are the exhibit.
- Four reading tiers, declared per module.
- Three color ramps (percentile / belief / accolade gold). No more.
- Accolade Lens polymorphic from day one.
- Hero Fingerprint non-negotiable.
- Signature Story generated, not templated.
- Selector Grid is required.
- Page is a weekly product (all hero numbers move Monday).
- Mobile-first, with 65% traffic share driving the design.

---

## Open questions (carried to canonical brief §11)

- CFBD tier-3 subscription for P3?
- Player-entity conversation pipeline — P1.5 or inside P2?
- All-Freshman team scraping — self-host or wait?
- Hero photo policy — licensed / monogram-only / AI-silhouette?
- Signature Story generator — hosted LLM or API-at-build?

---

## Next-step candidates (after iteration 2)

1. Spec doc for Figma — primitive-by-primitive + module-by-module with states + props.
2. Static HTML prototype of reimagined CJ Carr page with placeholder data.
3. Data-layer + `reporting.py` plan for the P0 slice.

---

## Iteration 3 — Player Standing + Design Craft

### Kevin's direction
*"i like the accolade lens module, but it should go further than that. it should have more rungs including like starter, benchwarmer, etc. then focus on doing deep research to make the design, UX and frontend absolutely perfect for everything."*

Key insight: the Accolade Lens only worked for the top 1%. A QB3 at Vanderbilt got a dead module. Need a universal status framework that works for every player on every roster.

### Research inputs consulted (iteration 3)

- Baseball Savant player page redesign (new slider-bar percentile rankings, red↔blue gradient).
- The Athletic / Shorthand player profile storytelling templates.
- F1 driver dashboards (OpenF1, TracingInsights, telemetry UX — "show what matters now, not everything").
- Strava athlete profile / Trophy Case / Best Efforts progression.
- Apple Fitness achievement rings + retroactive badge calculation + badge categories.
- NFL Next Gen Stats visualization patterns (XY tracking, gold-number interactive links).
- Progressive disclosure — NN/g, IxDF, LogRocket, Smashing Magazine 2025 writeups; the "5-7 chunks of working memory" calibration.
- Accessible diverging palettes — ColorBrewer, Carbon, OKLCH interpolation rationale, WCAG 3:1 graphical / 4.5:1 text targets.
- Fluid typography + container queries — `clamp()` usage, component-centric responsive design in 2026.
- Mobile bottom-sheet patterns — Mobbin glossary, NN/g bottom-sheet guidelines, Material Design 1 archive, 75% one-handed phone use stat.
- Linear / Raycast microinteraction standards — 100-300ms feedback, 200-500ms reveals, organic easing, never linear.
- Data-table design for large sports datasets — sticky headers, virtualization, row hover, frozen first column.

### Reframing decisions

- **Accolade Lens deprecated** as a standalone module. Awards now live as tabs *inside* the new Player Standing ladder.
- **17 rungs across 6 tiers.** Not 50 (too granular), not 7 (too coarse). 17 gives perceptually distinct tiers aligned to working memory (4-7 chunks) plus enough internal resolution for in-season movement.
- **Short-circuit placement cascade.** First rule wins: POTY outcomes → selector AA outcomes → All-Conference outcomes → watch lists → snap%/production gates → roster-only signals.
- **"Canonized"** (HOF / retired numbers / all-time teams) is a hero ribbon, not a rung. Historical status ≠ current season standing.
- **Three-read progressive disclosure** on the same module: rail (5s) → tier pills (30s) → rung drawer (5m) → accolade tabs (deep).
- **Polymorphism** by position (tab set changes) and by career stage (active vs. retrospective rail variant).

### Design craft decisions locked

- **Typography:** single family (Inter + Inter Display), fluid `clamp()` scale across five steps, "bright number / quiet label" rhythm rule.
- **Color:** three OKLCH ramps (percentile red-grey-blue, belief red-grey-green, accolade gold). Dark-mode-first. WCAG 2.1 AA at every step.
- **Motion:** four roles with exact durations/easings (Reveal 240ms, State 180ms, Data entry 420ms stagger, Delight 800ms overshoot). Linear easing forbidden. `prefers-reduced-motion` honored.
- **Interaction:** distinct hover/active/focus, no hover-only affordances, copy-on-tap, URL-persisted tab/drawer state, keyboard nav with arrow-key rung inspection.
- **Data viz:** 44/32px sparklines with terminal dot labeled, 88×22 percentile pills, field-oriented pass charts, one virtualized `<StatTable>` primitive for game log + stat explorer, trajectory lines with rung-threshold bands.
- **Mobile:** bottom sheets for every drawer, thumb-zone CTAs, scroll-snap tabs, 44×44 targets, container queries for every module.
- **States:** four mandatory per module (empty / loading / partial / error), honest copy never generic spinners.
- **A11y:** ARIA sibling text on every data point, `prefers-contrast` support, gold focus ring 2px/4px offset never suppressed.
- **Performance budget:** FCP < 0.8s, LCP < 1.2s, CLS < 0.02, JS < 35KB gzipped, rail/FI/tables all work without JS.

### Page IA (iteration 3 final)

1. Hero Fingerprint (5s).
2. **Player Standing** — rail + tier pills + rung drawer + nested accolade tabs (30s → deep).
3. The Room on [Player] — FI card (30s).
4. Signature Story — generated (30s).
5. Current Season Production — traditional (5m).
6. Advanced Exhibit — Savant card, pass chart, stat explorer (deep).
7. Peer Comparator (5m).
8. Supporting Cast (5m).
9. Bio / Recruiting / Transfer / Roster (reference).
10. NIL / Market / Draft (P3).

### Roadmap reshuffle

- **P0:** Standing rail (rules 2-5 of cascade) · Hero Fingerprint · design tokens (fluid type + three OKLCH ramps + motion) · game log · percentile chips + sparklines on every stat row.
- **P1:** Accolade tabs nested in Standing · Signature Story build-time LLM · Savant card · Splits · Watch-list + weekly awards ingest (feeds cascade rule #4).
- **P2:** Player-entity FI pipeline → "Room on [Player]" scoped · Peer Comparator · Pass chart · Supporting Cast · Accolade tab polymorphism (every position) · career-retrospective Standing variant.
- **P3:** Extended scenarios · NIL/draft · Live game mode.

### Open questions (iteration 3)

- Snap% ingest: scrape PFF, derive from CFBD drives/plays participation, or wait for a cleaner source? (Blocks accuracy of cascade rules #5.)
- All-Conference timing: conferences release Monday after championship — fine, but HM teams sometimes not released at all for certain conferences. How do we represent R09 for those?
- Signature Story LLM: API during weekly build (simpler) vs. self-hosted (cheaper at scale, more infra). Current lean: Anthropic API during build, cache aggressively.
- Career-retrospective view: do we backfill the rail for historical seasons (requires old snap% data we don't have), or start the retrospective from 2026 onward?
- Walk-on vs. preferred walk-on vs. roster invitee distinction at R00 — matters or overkill?

### Decisions locked (iteration 3)

- Standing is universal. Every rostered player gets a rung, every page renders the rail.
- Accolade Lens is no longer a standalone module — it lives as nested tabs inside Standing.
- Dark-mode-first, OKLCH ramps, WCAG 2.1 AA, 44×44 touch targets — hard constraints on every component.
- Mobile-first is enforced via container queries on every module, not viewport breakpoints.
- Shareable URL state is a P0 requirement, not a nice-to-have.
- Signature Story ships as build-time-generated in P1; templated version gets deprecated when it does.
