# World-Class Gap Audit — 2026-05-22

Auditor: Claude. Scope: player + team pages, comparing the design briefs in this repo against what is shipping at `https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app`.

Anchor briefs read for this audit:

- `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` (572 lines, 3 iterations; QB Fingerprint, Standing Rail, Savant card, Selector Grid, four-tier reading ladder).
- `PLAYER_PAGE_SEASON_PHASE_DESIGN.md` (432 lines; phase banner, 2026 Outlook, Development Trajectory, Draft Day Live).
- `PLAYER_PAGE_SIGNATURE_BETS.md` (~660 lines; 14 named bets — Rival Radar, Hot-Take Engine, Anti-Take, Mirror Match, FI Glossary, Achievements, Signature Play, Prediction Markets woven, Cohort Divergence Map, Coaching Lineage, Scenario Explorer, Live Signal Flow, Narrative Arc Board, plus 20 "smaller details that compound").
- `TEAM_PAGE_WORLD_CLASS_BRIEF.md` Parts I + II + III (1,746 lines; reading ladder, two prestige rails, "The Room on [Team]" five-panel FI card, 15-metric Team Savant, Season/Era/Dynasty Arc time navigator, four-zone Rivalry Card, Recruiting Pipeline, Scheme Fingerprint, Conference Lens, Fanbase Health Index, Ceiling/Floor projections, Quiet Years Detector, Fanbase Fracture Detector, The Moment Signal, Tab-as-Room IA, Tribal Voice System, Hero Arc viz, Wrapped drop, Kickoff Check-In, Program Similarity Engine, Community Annotation Layer, Program-tier sentience 10-tier taxonomy, Seasonal sentience ~10 anchor variants, Chronicle module 6 card types, Profile-driven editorial infrastructure).
- `TEAM_PAGE_ENGAGEMENT_BRIEF.md` (941 lines; "The Story Right Now" headline, four emotional contracts, narrative engine, 18-archetype fanbase taxonomy).
- `TEAM_PAGE_ITERATION_LOG.md` (811 lines; 16 mockups produced before any code shipped — every major module designed at full fidelity).
- Design system: `docs/design-system/00-tokens.md` (locked OKLCH-style ramps + Bebas Neue display font), `30-page-archetypes.md` (6 IA archetypes locked 2026-05-17), `31-chart-vocabulary.md`, `32-receipt-pattern.md`, `33-confidence-signaling.md`.

Live evidence pulled by the Vercel MCP into the persisted-output cache for:

- `/players/fernando-mendoza-38276.html` (#1 Heisman nowcast QB — the showcase player page)
- `/players/spotlight.html` (players landing)
- `/programs/notre-dame.html` (legacy program history renderer)
- `/programs/alabama.html` (same legacy renderer)
- `/teams/notre-dame.html` (the world-class `team_pages/` renderer — Profile slug)
- `/teams/florida-international.html` (the legacy `reporting.py` team renderer — unprofiled slug)

Code surveyed (not edited): `src/cfb_rankings/team_pages/` (1,204-line renderer.py + 18 sibling modules + 6 stylesheets, total ~3,300 LOC of world-class scaffolding), `src/cfb_rankings/profile/__init__.py` (397-line archetype primitives), and the `reporting.py` player-page paths (`_assemble_player_page_data`, `Signature Story`, `Player Standing`, `Narrative Arc`).

---

## TL;DR

The site is in an unusually awkward state: two design ambitions, two rendering pipelines, and one URL surface that confuses both. The world-class `team_pages/` module exists, is wired into the build for the 17 profiled slugs, and ships a recognizably ambitious Profile page — Notre Dame's `/teams/notre-dame.html` includes the Pulse, Chronicle (4 cards on the live render), Savant Card (with a real percentile bar set + peer toggle), Rivalry Card scaffold, and a CFP-Era Season Arc. That page is not embarrassing. It is also clearly partial — the Pulse is in "QUIET · dead period heritage" mode showing zero mentions and one boilerplate quote, the Chronicle has no Echo/Moment/Retroactive card-type variety the brief specifies, the rivalry side-by-side thermometer is missing, and per-team voice ("Subway Alumnus · Mystic-Persecuted") shows up but the mascot voice fallback ("The Leprechaun is keeping his own counsel") reads more cute than ritualized.

The player pages have the opposite problem: they have NONE of the design language in the brief. Mendoza's page — the #1 QB in the country on this product's own model — opens with `profile-identity-v2` chrome (4 generic stat tiles, the breadcrumb of `Heisman / Players / Fernando Mendoza`, and the same identity strip every program page uses). There is no QB Fingerprint hero, no 17-rung Standing Rail visualization (the data is encoded in a JSON `data-player-slug` block as `"standing_rung": 15` but never drawn), no Belief Dial, no Savant card with the 12 percentile bars, no Selector Grid, no Hot-Take / Anti-Take, no Rival Radar, no Mirror Match. What's there: Signature Story (with cohort bar + confidence chip — good), an AI-drafted Narrative Arc in 3 acts (Discovery / Ascent / Coronation — good), a Scenario Explorer slider, achievements encoded but only printed as a debug-looking `{'achievement_id': ...}` Python-repr string inside the JSON state block. The Phase Banner ("OFFSEASON · SUMMER 2026 · COMMITMENT SEASON") is implemented. Most of the rest is generic `.stat-card` / `.panel` chrome that looks like every other directory page on the site.

Unprofiled team pages (`/teams/florida-international.html`) are still on the legacy `reporting.py` pipeline — `team-shell` wrapper, `profile-identity-v2`, `mood-card-empty`, `Cohort Signal — awaiting data`, the 18-archetype "Fanbase Archetype" panel — and look like a 2018 SaaS dashboard. The shocking comparison the user named ("FIU has more visible design content than ND") is half true: FIU's legacy page has the 4-tile resume / power / net-points strip + an empty mood card + an archetype panel + a season journey chart, totalling about six visible modules above the fold; ND's `/teams/` page has 8+ richer modules, but most look semi-empty in May because the Pulse correctly reports zero offseason signal. The legacy FIU page LOOKS busier; the new ND page IS deeper. Both feel ugly in different ways.

Sixteen mockups were produced in Figma per `TEAM_PAGE_ITERATION_LOG.md`. Of those sixteen, the live site partially ships approximately five (Pulse, Chronicle, Savant Card, Rivalry Card scaffold, CFP-Era Arc) and entirely misses eleven (Hero Arc 131-season stripe / 13-brick variant, Historical Season Deep-Dive, the dual-trajectory rivalry heat chart, Mobile-first 390pt full-fidelity translation, Seasonal Sentience 4-state grid, Game Recap Mode hero, Program-tier sentience visual differentiation, Four-program payoff render comparison, Full desktop composition, the live signal Hype Meter, Wrapped stack). Nothing was Figma-designed for player pages at this fidelity — the Player Brief's "Figma handoff" §9 was scoped but never commissioned, and it shows.

So the honest, top-of-doc answer to "why does it look ugly": the player pages were never given the renderer the brief asked for, and the team pages got 30% of theirs. The polish work that has shipped (a11y hardening, contrast, scope=col on tables, tabular numerals, profile-identity-v2 chrome extraction, meta footers across 17,836 surfaces, sitemap and robots) is real engineering — but none of it touches what a fan SEES. A page with WCAG-AA contrast and tabular-nums still looks generic if the actual hierarchy is "four stat tiles, then ten more stat tiles, then a chart."

---

## Part 1 — Player page audit

### 1.1 What the brief intends

The Player Brief is the most articulated design doc in this repo, written across three iterations on 2026-04-22 and supplemented by the Season-Phase doc and the Signature Bets doc on 2026-04-23. The core moves:

**Thesis** (§1): "The QB page should feel like three experiences stacked on one URL: the vibe read at the top (FI), the traditional box-score foundation (cleaner than ESPN/SR), the analytical exhibit (Savant-style percentile card)." Verbatim: *"FI is the spine. Traditional stats are the foundation. Advanced stats are the exhibit."*

**Reading ladder** (§2): four explicit tiers — 5-second / 30-second / 5-minute / deep-dive — with the design rule *"No module mixes tiers."* The five-second zone is Hero + QB Fingerprint Card; the 30-second zone is FI card + top 3 stats with percentile chips + live accolade probabilities.

**Nine UX primitives** (§3) Figma was supposed to build first: Percentile Bar (Savant red→grey→blue), Belief Dial, Trajectory Spark, Eyebrow→Number→Narrative grammar, Drawer, Tab Bar, Chip, Pill Comparator, Selector Grid. Each in desktop + mobile + loading + empty + error states.

**Hero "QB Fingerprint"** (§4.1): three-column desktop, single-column mobile. Five vibe cells in the middle (QB Score / Heisman Heat / Fan Belief / Respect Gap / Reality Gap). Stacked mini-cards for top 3 accolades on the right.

**Player Standing 17-rung rail** (§7): the single biggest UX move in the doc — replacing the original Accolade Lens. Six tiers, seventeen rungs from R00 walk-on to R16 Heisman winner, with a placement cascade, a tier-pill row, a rung drawer with "Why he's here / What moves him up / What moves him down," and accolade tabs nested INSIDE Standing rather than as a parallel module. The brief states: *"Player Standing replaces the Accolade Lens as the page's primary status hub. It answers the one question every fan walks in with: how good is this guy, actually, right now? One module, 17 rungs, same component for a walk-on and for the Heisman frontrunner."*

**Design Craft** (§8): Inter Display / Inter typography, fluid `clamp()` scale, OKLCH three-ramp color system (percentile / belief / accolade-gold), four-role motion grammar (Reveal 240ms / State 180ms / Data-entry 420ms / Delight 800ms), 44×44 touch targets, dark-mode-default, four mandatory states per module, FCP < 0.8s budget.

**14 Signature Bets** (Signature Bets brief): Rival Radar (new 5m-tier module), Hot-Take Engine + Anti-Take Engine (paired ambient card), Statistical Mirror Match (5m, "Closest historical match: Bo Nix, Oregon 2023 · 94% similar"), FI Glossary `?` icons throughout, Weekly "What Changed" diff, Achievements (12+ named badges including Money Down / Clutch Gene / Rival-Slayer / Cold-Weather Stud), Signature Play (per-game card), Prediction Markets woven into Hero cells, Cohort Divergence Map (2D scatter), Coaching Lineage, Scenario Explorer, Live Signal Flow (top-of-page bar), Narrative Arc Board (3-act per season).

**Season-phase doc**: explicit Phase Banner ("OFFSEASON · SUMMER 2026 · COMMITMENT SEASON"), Hero cells swap per phase (5 in-season cells become 2025 retrospective + 2026 forward-looking cells), 2026 Outlook module (7 cells: Projected Role / Heisman Futures / Draft Grade / Watch Lists / Returning Value / Team 2026 Outlook / Coaching Continuity), Development Trajectory line chart, Draft Day Live conditional module, 15-state Offseason Status chip.

### 1.2 What's actually live (Mendoza page audit)

Body classes and chrome of the live `/players/fernando-mendoza-38276.html`:

- `<main class="site-shell">`, then `<div class="phase-banner">OFFSEASON · SUMMER 2026 · COMMITMENT SEASON</div>` — **phase banner is implemented and correct.**
- A `<script type="application/json" id="page-state">` block carries `"standing_rung":15, "achievements": ["{'achievement_id': 'achievement_money_efficiency', ...}", ...]` — **the data exists. The data is JSON-encoded Python-repr strings (unusable until JS parses them). Nothing draws this on screen.** The visible page never renders the rung number, the rung name, or the rail.
- `<section class="team-shell" style="--team-accent:#990000; --team-accent-soft:#b98343;">` — **note the leaking `--team-accent-soft:#b98343`. That hex is the same warm-tan on Indiana, Notre Dame, and Florida International — it is the default Profile fallback color, not Indiana's actual #FFFFFF/#990000 brand pair. The accent system half-works.**
- Breadcrumbs: `Heisman / Players / Fernando Mendoza`.
- `<section class="profile-identity-v2">` — the SAME chrome used on `/programs/notre-dame.html`, `/programs/alabama.html`, and `/teams/florida-international.html`. Four `.profile-identity-v2__stat-tile`s with `Current nowcast #1`, `Season forecast #1`, `Win probability 14.3%`, `Best official finish --`. **This is not a QB Fingerprint. It is the generic directory-card hero pattern.**
- `<div class="player-hero-facts">` with three pieces of meta (`3 · #15 · 6-5 | 225 lb · Miami, FL`).
- Sticky `<nav class="player-subnav">` with 10 anchors (Room / Story / Stats / Standing / Splits / Savant / Peers / Cast / Bio / Trophy) — **the anchors imply the brief modules, but most of the destinations are generic `.panel`s with `.stat-card`s, not the modules described.**
- `<section id="current-heisman-lens">` — 5 stat tiles (nowcast / forecast / win prob / finalist prob / ballot prob). Has a `<span class="fi-confidence fi-confidence--high">HIGH CONFIDENCE</span>` chip — **confidence signaling spec from `33-confidence-signaling.md` IS hitting.**
- `<article class="signature-story">` — implemented. Hero stat (`+0.560 EPA`), rank chip (`#4 of 55`), 94th percentile, cohort bar with `style="width: 94.4%; background: var(--percentile-100);"`, "Also strong" runner list of 3 metrics. **This is the closest thing on the page to the brief's grammar.**
- `<article class="signature-play signature-play--empty">` — module exists, currently empty-state. "No signature moment on the ledger yet."
- `<article class="narrative-arc narrative-arc--auto">` — three acts (Discovery / Ascent / Coronation) with a meta range / inflection / synthesis structure. **Implemented per Signature Bets §14 spec, and reads cleanly.** Carries an "AI-drafted · under editorial review" badge — honest.
- `<article class="scenario-explorer">` — Alpine.js powered slider (remaining games × per-game projection). **Implemented per Signature Bet #12.**
- The rest of the page is `<article class="panel">` blocks wrapping `<div class="feature-grid history-snapshot-grid">` of generic `<article class="stat-card">` tiles for Identity & Role, Recruiting Pedigree, etc.

What is conspicuously not present on the live page:

- **No QB Fingerprint hero.** The five-vibe-cell grammar (Eyebrow → big tabular display number → one-sentence narrative) is replaced by four small uniform stat tiles.
- **No 17-rung Standing Rail.** The data is present (`standing_rung: 15` = "POTY finalist" per the brief's R15 spec). The rail is not drawn.
- **No Belief Dial.** There's a `data-belief` data-attribute system elsewhere but no visible dial on this page. The "Room" anchor renders to an "Awaiting Signal" panel (because Mendoza-specific FI hasn't been built per the brief — confirmed in the brief: *"The one new ingestion dependency: player-entity tagging in the conversation pipeline"*).
- **No Savant card.** Mendoza's page has no 12-percentile-bar Savant block. There IS one for teams; players never got one wired up.
- **No Selector Grid.** Zero gold/silver/empty pills for AP / FWAA / AFCA / WCFF / SN / SI / etc. — the brief called this *"the single best design idea in this doc"* and *"don't ship without the Selector Grid."*
- **No Hot-Take card + Anti-Take card.** Not present.
- **No Rival Radar.** Not present.
- **No Mirror Match.** Not present.
- **No Achievements ribbon.** The data is generated (3 achievements: Money Efficiency, Volume King, Program Benchmark, with rarity_pct values). They're JSON-encoded as Python repr strings inside the page-state script and never rendered as gold-medallion badges anywhere.
- **No Coaching Lineage module.** Not present.
- **No Live Signal Flow bar.** Not present.
- **Prediction Markets** are not woven into hero cells.
- **What Changed diff** for return visitors: there's a `<div data-what-changed aria-live="polite"></div>` placeholder, currently empty.
- **2026 Outlook** is not a discrete module with the 7-cell pattern. The Heisman Lens block has 5 cells that approximate part of it.
- **Development Trajectory** multi-season line chart: not present.

Sampled other player pages (`/players/spotlight.html`): the landing has three QBs (Pavia, Iamaleava, Maiava), three RBs, three WRs — and an "Awaiting Signal" Room panel as the only other content. **For the brand's #1-billed product surface (players), the landing page has six modules total and one of them is an empty state.** This page should be electric in May; instead it's a list.

### 1.3 Gap matrix (player pages)

| # | Module / spec | Brief intent (verbatim where pointed) | Live state | Severity | Effort |
|---|---|---|---|---|---|
| 1 | QB Fingerprint hero (5 vibe cells) | "Eyebrow → big display number → 14px sentence of plain-English read" × 5 cells | Generic `profile-identity-v2` 4-tile strip | P0 | 3 days |
| 2 | 17-rung Standing Rail | "Full-width horizontal rail. 17 tick marks. Filled gold marker at the current rung; faint ghost marker at last season's rung." | Data present (`standing_rung:15`), not rendered | P0 | 2 days |
| 3 | Standing tier pills + rung drawer | "Six tier labels below the rail … tap current-rung marker → bottom sheet" | Not present | P1 | 2 days |
| 4 | Accolade tabs nested inside Standing | "Heisman tab fully designed … then grammar applied to Davey O'Brien · All-American · All-Conference to prove polymorphism" | Not present | P1 | 3 days |
| 5 | Selector Grid | *"Don't ship without the Selector Grid"* | Not present | P0 | 1 day |
| 6 | Belief Dial (player-scoped) | Belief Dial inline + archetype label | Not present; FI is team-scoped only | P1 (data-blocked) | 1 week + pipeline work |
| 7 | Savant card (12 percentile bars, red→grey→blue) | "Vertical stack of ~12 percentile bars, red→grey→blue gradient … ordered best → most interesting → concerns" | Not present on player pages (exists on teams) | P0 | 3 days |
| 8 | Pass chart | "Field-oriented SVG … hex-bin on large samples" | Not present | P2 | 1 week |
| 9 | Splits tabs | "Situational · Defense quality · Home/Road · Pocket" | Not present | P1 | 2 days |
| 10 | Peer Comparator + Mirror Match | 3-pill default + radar + respect-gap grid | Not present | P1 | 3 days |
| 11 | Hot-Take + Anti-Take | "Always paired … intellectual honesty move that 247 and ESPN can't pull off" | Not present | P1 | 4 days |
| 12 | Achievements ribbon | "Small gold badges … rarity discipline: many achievements must be held by <10% of cohort" | Generated as JSON Python-repr strings, never rendered | P0 (fix the render only — data is there) | 1 day |
| 13 | Signature Play sub-module | Per-game card surfacing THE play | Empty-state stub present | P2 | 4 days |
| 14 | Narrative Arc 3-act | "Per-act inflection play" | Implemented & reading well | shipped | — |
| 15 | Signature Story | hero stat + rank chip + percentile + cohort bar + confidence + runners | Implemented & reading well | shipped | — |
| 16 | Scenario Explorer | Slider widget for remaining-game projections | Implemented | shipped | — |
| 17 | Phase Banner | "OFFSEASON · SUMMER 2026 · COMMITMENT SEASON" | Implemented & correct | shipped | — |
| 18 | 2026 Outlook (7 cells) | Projected Role / Heisman Futures / Draft Grade / Watch Lists / Returning Value / Team 2026 Outlook / Coaching Continuity | Partial — only Heisman Lens 5-cell block, no Watch Lists / Returning Value | P1 | 2 days |
| 19 | Development Trajectory line | "Season on x, CFB Index score on y … milestone markers" | Not present | P1 | 2 days |
| 20 | Live Signal Flow bar | "Thin bar under the Hero. Accolade-gold left border" | Not present | P2 | 2 days |
| 21 | Rival Radar | "Rival fanbases mention Carr 4.2× more than any opposing QB" | Not present (data-blocked on player-FI pipeline) | P2 | data + 4 days |
| 22 | Coaching Lineage chip + module | "Year 2 OC: Mike Denbrock · 82 plays/gm prior stop" | Not present | P2 | 3 days |
| 23 | Prediction Markets in Hero | "Kalshi +450 · 18.2% implied · up 160 bps" | Not present | P2 | 2 days + data |
| 24 | What Changed diff | "Updated Mon Apr 21 — Mood shifted: +0.4 SD this week" | Placeholder `<div data-what-changed>` only | P2 | 2 days |
| 25 | FI Glossary `?` icons | "Tap opens a 60-word explainer" | Implemented elsewhere (Fanbase Archetype on team pages); not on player pages | P2 | 1 day |
| 26 | Three OKLCH color ramps | Percentile / Belief / Accolade-gold strict separation | Not visible on player pages — pages read as a generic light-on-light card grid | P0 | 1 day token work |
| 27 | Bebas Neue display font usage | "big display-font number (Bebas Neue)" — declared in tokens 2026-05-16 | Visible only on Hero Findings; not on player hero numbers | P1 | 0.5 day |
| 28 | Dark-mode default | "Dark mode is the default" | Page is light-mode default; theme toggle exists | P1 (decision) | 0.5 day |
| 29 | 4 mandatory module states (empty / loading / partial / error) | "Every primitive needs: desktop + mobile + loading + empty + error states" | Empty states present, no skeleton-loading state visible | P2 | 2 days |
| 30 | Mobile-first layout (390pt thumb-native) | "Hero fingerprint: vertical stack; five vibe cells horizontal snap-scroll" | Generic responsive grid; nothing thumb-native designed | P1 | 3 days |

Bands: P0 = visible hero/identity gaps a casual fan notices in 5 seconds; P1 = brief-mandated modules wholly missing from the canonical product; P2 = polish or data-blocked items where shipping requires upstream pipeline work.

### 1.4 "Awaiting Signal" empty-state audit

CLAUDE.md is explicit: *"'Awaiting Signal' fan-intel fallback fires for genuinely-no-signal programs (small DII/DIII/NAIA without measurable Reddit/news/betting volume). It's a graceful-degradation path, not a bug — fix the upstream signal collection, not the fallback string."* That's correct in spirit, but the implementation is undisciplined on player pages.

- Mendoza (the #1 nowcast QB) has The Room rendering to *"Awaiting Signal — publishing starts once corpus density clears the floor."* — this is correct in that player-FI pipeline does not exist yet (the brief is explicit: *"To light up the 'The Room on [Player]' module, we need a parallel `player_week_conversation_features` table"*). The fallback should be the team's Mood Card per `PLAYER_PAGE_WORLD_CLASS_BRIEF.md §4.2`: *"Low-conversation players fall back to team mood with honest copy: 'Not enough player-specific chatter yet. Belief below reflects Notre Dame's team Mood Card.'"* Live fallback says nothing about the team and never shows the team Belief Dial. **Spec violation, not a graceful fallback.**
- Spotlight landing's "The Room" panel: a single line `Awaiting Signal — publishing starts once corpus density clears the floor.` for the WHOLE landing page. Doesn't degrade to anything; just an empty box.
- The Signature Play is correctly empty-state ("No signature moment on the ledger yet … Returns once this player puts together a multi-game body of work").
- The Heisman Lens shows "Best official finish --" rather than "no official finish yet (eligible 2026)" — falls short of the brief's *"Specific, honest copy. Never 'No data available.'"*

Five out of the seven empty states on the Mendoza page are mute placeholders that violate the brief's "specific, honest copy" rule (§8.8). This is fixable in an afternoon.

---

## Part 2 — Team / program page audit

### 2.1 What the brief intends

The Team Brief is the heaviest single document in the repo. Read in three layers:

**Part I** locks the philosophy and the reading ladder. Thesis: *"FI is the spine. Results are the foundation. Context is the exhibit. Time is the axis."* Two-rail prestige system (9-rung Season Standing + 7-tier Program Prestige). Five-panel "The Room on [Team]" FI card (Fanbase Archetype + Headline / Five-Axis Strip with Reality Gap & Respect Gap & Cohort Divergence & Rival Heat & Volatility / Home vs Away Mood Split / Top Storylines / Confidence Badge). 15-metric Team Savant Card. Three-altitude Arc time navigator (This Season → [Coach] Era → All-Time). Four-zone Rivalry Card (Identity Header / Four-Axis Rivalry Matrix / Timeline / Game-Week Context with dual-thermometer Fan Heat Index). Recruiting Pipeline (three panels including pipeline-vs-performance gap chart). Coaching Staff Scheme Fingerprint. Conference Lens toggle. Seven bespoke team-only concepts (Fanbase Health Index, Ceiling/Floor projections, Home-Field Advantage Quantification, Program Trajectory Arc, Quiet Years Detector, Fanbase Fracture Detector, The Moment Signal).

**Part II** adds the new-gen fan lens. Hero Arc viz with 131 bars at the very top of the page (Climate-Stripes-style season-strength stripe — *"The retained §6 Arc is the interactive explorer. The proposed §20 Arc-as-Hero is a glance-readable identity strip."*). Screenshot-Native design ("every card on the page must satisfy: team mark + card title + one headline number visible in the first 60% of vertical space"). Synchronized Communal Moments (Wrapped drop day, Kickoff Check-In, Hype Meter, Weekly Fanbase Leaderboard). Tab-as-Room IA alternative (`PULSE | FILM | RECRUITING | HISTORY | MEMES`). Tribal Voice System per-team. Year-round content rotations. Program Similarity Engine ("2025 Alabama is most similar to 2017 Clemson"). Community Annotation Layer.

**Part III** is the integration pass after 16 mockups (per the Iteration Log). Five macro principles: program-tier sentience (10-tier taxonomy, every module reshapes), seasonal sentience (10 named anchor variants × 6 accents = ~25-30 meaningful states), deep program profiles (~45-50 fields per team driving every rendering decision), Chronicle module at three altitudes with six card types, Claude Code + Max content generation pipeline.

**Engagement brief** layers on top: the four emotional contracts (Casual / Die-Hard / Data Nerd / Rival), "The Story Right Now" 14-18-word headline, 18-archetype taxonomy, narrative engine with six signal layers.

### 2.2 What's actually live (ND / Alabama / FIU)

Two pipelines coexist:

**Pipeline A — `team_pages/` (Profile renderer, 17 profiled slugs).** Fires for the slugs in `profiles/*.md` (alabama, auburn, florida, georgia, massachusetts, michigan, notre-dame, ohio-state, oklahoma, oregon, penn-state, tennessee, texas, uconn, usc, vanderbilt, washington — per CLAUDE.md, 17 unchanged since 2026-05-12). What ND ships, from the live HTML:

- Hero block with eyebrow `MAY 22, 2026 · DEAD PERIOD · HERITAGE WINDOW · 2025 SEASON`, logo PNG (Notre Dame primary), wordmark `Notre Dame`, record `10-2`, three rank chips (`AP #9 / COACHES #9 / CFP #11`), heritage strip (`Founded 1887 · Titles 13 · Heismans 7 · CFP 2 · Bowls 38 · Conference FBS Independent · Stadium Notre Dame Stadium (77,622) · Legacy Knute Rockne`), and a `hero__state` paragraph in Source Serif Pro that reads as the brief's "Story Right Now" — *"Notre Dame is a program that knows what it is, and still asks the question. Ten and two, ninth in both polls, eleventh on the committee's board, a 49-20 closeout at Stanford … Play like a champion today."* This is **the strongest single piece of content on any team page in the product.** It's per-team voiced, present-tense, season-aware, ends on the mantra. The brief's Engagement spec for the headline is met here.
- A 4-tile `hero__metrics` row (Record / AP / SP+ / CFP Standing). Cleaner than ESPN's. Not a Hero Arc stripe.
- `<section class="pulse">`: `pulse__live-dot--quiet`, "The Pulse on Notre Dame," meta `QUIET · dead period heritage · signal ramps back in camp`, mood number `—`, one quote (`"Every season here is measured against the ones people name after coaches." — Notre Dame fanbase · recurring line`), one event ("Dead-period quiet — official-visit + heritage window"), one "Fall camp ~71 days out" event, and badge `0 mentions · awaiting signal`. **Pulse architecture exists. Pulse content is one quote + two stub events because nothing has happened. This is honest, but reads thin.** The brief's Pulse spec (Mood number + weekly delta + velocity vs baseline + 72-hour event log + 3-4 conversation topics with sentiment bars + reality/respect/divergence gap compact cards + 3 curated quotes + footer linking to venues) is roughly 30% rendered.
- `<section class="rituals">` with 5 ritual cards (Play Like a Champion Today / Victory March / Trumpet Quartet at the Grotto / Touchdown Jesus / The Shillelagh and the Leprechaun) — **excellent. This is exactly the editorial infrastructure the brief Part III promised. Notre Dame's profile YAML is doing real work.**
- `<aside class="cultural-anchors">` with "Notre Dame is the program that converted Catholic mass immigration into a national fanbase that has nothing to do with proximity to South Bend." Two archetype labels (`From inside: Subway Alumnus / From outside: Mystic-Persecuted`). **Excellent.** Voice is the strongest signal on the page.
- `<section class="chronicle">`: four cards (one MOMENT — "Notre Dame Drops 70 on Syracuse"; two ANOMALY — pass defense at 94th pct + rushing at 94th pct; one FLASHPOINT — "Irish Hold the Shillelagh for a Third Straight Year"). **Four cards. Brief specifies six card types (Anomaly / Moment / Flashpoint / Echo / Retroactive / Player arc); only three of the six types appear.** No Echo card despite the brief explicitly describing the cross-era cosine-similarity finding ("0.94 similarity to a 2012 ND defense") as a hallmark moment.
- `<section class="savant-card">`: header eyebrow `THE SAVANT CARD · Notre Dame · 2025`, peer toggle (FBS / Power-4 / Conference / Program 2014+), narrative line *"Notre Dame reads strongest in explosive plays (top 1%) and epa / play (top 5%); the crux lives in explosive plays allowed, where Notre Dame sits at the 48th percentile,"* and percentile bars labeled "offense · strengths lead" with EPA/play (96th), Success Rate (81st), etc. **Implemented to spec.** This is the second-strongest module after Hero.
- Rivalry card scaffold present (rendered via `render_rivalry_card` for the tier-1 ND/USC matchup per profile.rivalries) — I didn't render-snapshot the full rivalry card in this audit but the renderer paths exist.
- CFP-Era Season Arc (per `season_arc_card.py`).

What ND's `/teams/` page **does not** ship:

- **No Hero Arc stripe (Part II §20).** The 131-season climate-stripe / 13-brick CFP-era hero is the very first module the new-gen lens demanded. Not present.
- **No Rivalry Thermometer** dual-fanbase heat reading. The brief's screenshot-bait module per §7 — not visible.
- **No five-axis strip** (Reality Gap / Respect Gap / Cohort Divergence / Rival Heat / Volatility) in The Pulse. Cohort divergence is computed but not visualized as a stacked-segment bar.
- **No Home vs Away Mood Split panel.**
- **No Aspiration Ladder module.** Part III §33.4 mandates it for every team page.
- **No Program Prestige 7-tier rail.**
- **No Season Standing 9-rung rail.**
- **No Recruiting Pipeline module.**
- **No Coaching Staff Scheme Fingerprint.**
- **No Conference Lens toggle.**
- **No Ceiling vs Floor probability band.**
- **No Fanbase Health Index gauge.**
- **No Quiet Years / Fanbase Fracture / The Moment chips.**
- **No Wrapped stack, no Kickoff Check-In, no Hype Meter, no Weekly Leaderboard, no Program Similarity card, no Community Annotation Layer.**
- **No Tab-as-Room IA. No Seasonal Sentience visible accent flip** (the page hasn't shifted to a post-loss-red or rivalry-week-amber treatment despite the resolver existing in `state_resolver.py`).

Alabama's `/programs/alabama.html` is the **LEGACY reporting.py renderer** — title is `Alabama Program History`, body is the same `profile-identity-v2` chrome plus the program-arc SVG chart. This URL is what most users will land on from external links because `/programs/<slug>.html` is the historical canonical. Alabama's `/teams/alabama.html` would hit the world-class renderer (alabama is a profiled slug), but the audit's brief deliberately also fetched the program URL to evidence the parallel-stack problem.

**Pipeline B — `reporting.py` legacy renderer (~662 unprofiled slugs).** FIU is the test case. What FIU's `/teams/florida-international.html` ships:

- Same `<main class="site-shell">` / `<header class="topbar">` site shell.
- `<section class="team-shell" style="--team-accent:#19423f; --team-accent-soft:#b98343;">` — note again the **`--team-accent-soft:#b98343` leak across every team**.
- `<section class="profile-identity-v2">` — same chrome as program pages and player pages. Stat tiles (Record 7-6 / Power +14.1 / Resume 79 / Net Points -19).
- `<section class="mood-card is-waiting mood-card-empty">` — "Florida International fan conversation is quiet right now. The Mood Card lights up during the season … Re-opens with the 2026 season."
- `<section class="cohort-panel cohort-panel--empty">` — Cohort Signal awaiting data.
- `<section class="team-archetype-section">` — Fanbase Archetype with FI glossary `?` button.
- ... and continuing: the legacy page is a long flat scroll of `.panel` blocks for Season Rating Journey, Best Wins / Bad Losses, Recruiting Snapshot, etc.

**Comparison:** ND's `/teams/notre-dame.html` is roughly 5× longer in HTML byte count than FIU's `/teams/florida-international.html` and 2× richer in visible-module count. The user's premise that *FIU has more visible design content than ND* is not literally accurate — FIU has FEWER, GENERIC modules; ND has MORE, BESPOKE modules. But the perception is real: FIU's page is denser per scroll because the legacy renderer crams more flat stat panels in a tighter rhythm, while ND's bespoke modules each take a full viewport and many appear half-empty in the offseason (Pulse mood = `—`, mention count 0, Chronicle has only 4 cards). **ND looks ugly because its world-class scaffolding is half-empty in May, and FIU looks ugly because its legacy chrome is fully populated with generic content.** Two different ugly.

### 2.3 Gap matrix (team pages)

| # | Module / spec | Brief intent | Live state (ND `/teams/`) | Severity | Effort |
|---|---|---|---|---|---|
| T1 | Hero Arc stripe (131-bar climate / 13-brick CFP) | Part II §20 — top-of-page identity strip | Not present | P0 | 4 days |
| T2 | "The Story Right Now" 14-18-word headline | Engagement Brief §B | Implemented — ND hero state paragraph reads strongly | shipped | — |
| T3 | Season Standing 9-rung rail | Part I §3.1 | Not present | P1 | 2 days |
| T4 | Program Prestige 7-tier rail | Part I §3.2 | Not present | P1 | 1 day |
| T5 | "The Room on [Team]" 5-panel FI card | Part I §4 | Pulse covers Panels 1+4; missing Panels 2 (5-axis strip), 3 (Home/Away), 5 (confidence badge present elsewhere) | P0 | 3 days |
| T6 | Team Savant Card (15 metrics, 3 tabs) | Part I §5 | Implemented; ~12 bars; offense/defense/overall tabs unclear in scroll evidence | shipped (refine) | 1 day |
| T7 | Season Arc 3-altitude time navigator | Part I §6 | CFP-Era view shipped; This-Season weekly view + All-Time decade view not present | P1 | 3 days |
| T8 | Rivalry Card 4 zones with dual-thermometer | Part I §7 | Scaffold present; thermometer + four-axis matrix not visible in the rendered evidence | P0 | 3 days |
| T9 | Recruiting Pipeline (3 panels) | Part I §8 | Not present | P1 | 3 days |
| T10 | Coaching Staff Scheme Fingerprint | Part I §9 | Not present | P1 | 4 days |
| T11 | Conference Lens toggle | Part I §10 | Not present | P1 | 3 days |
| T12 | Ceiling vs Floor probability band | Part I §11.2 | Not present | P2 | 3 days |
| T13 | Fanbase Health Index gauge | Part I §11.1 | Not present | P2 | 2 days |
| T14 | Home-field advantage quantification chip | Part I §11.3 | Not present | P2 | 2 days |
| T15 | Quiet Years / Fracture / Moment chips | Part I §11.4-7 | Not present | P2 | 2 days |
| T16 | Aspiration Ladder | Part III §33.4 | Not present | P1 | 2 days |
| T17 | Seasonal Sentience accent flip | Part III §32 (10 anchor variants × 6 accents) | Resolver exists in `state_resolver.py`; visible accent change in the rendered page absent | P1 | 2 days |
| T18 | Program-tier sentience (UMass-vs-Alabama divergence) | Part III §33 | Implicit via profile fields; not visually differentiated | P1 | 3 days |
| T19 | Chronicle 6 card-type variety | Part III §36 | 3 of 6 types live (Moment / Anomaly / Flashpoint); Echo / Retroactive / Player Arc absent | P1 | 3 days |
| T20 | Rituals strip | Part III + locked design system | Implemented for ND beautifully | shipped | — |
| T21 | Cultural anchors aside | Part III §34 | Implemented | shipped | — |
| T22 | Mascot voice fallback | Part II §24 | Implemented ("The Leprechaun is keeping his own counsel") | shipped (extend to 130 programs) | 1 wk |
| T23 | Wrapped stack | Part II §21.3 | Not present | P2 | 4 days |
| T24 | Kickoff Check-In counter | Part II §22.1 | Not present | P2 | 2 days |
| T25 | Hype Meter | Part II §22.2 | Not present | P3 | data + 1 wk |
| T26 | Weekly Fanbase Leaderboard | Part II §22.3 | Not present | P3 | 2 days |
| T27 | Program Similarity Engine | Part II §26 | Not present | P2 | 3 days |
| T28 | Tab-as-Room IA prototype | Part II §23 | Not prototyped | P2 (decision, not effort) | 1 wk |
| T29 | Community Annotation Layer | Part II §27 | Not present | P3 | 2 wks + moderation |
| T30 | Share-Card renderer | Part II §21.2 | Not present | P2 | 1 wk |
| T31 | Legacy renderer parity (662 unprofiled slugs) | Part III §39 brand position: "every team's page with equal editorial care" | Two-tier reality: 17 profiled slugs get the world-class renderer, 662 slugs get the legacy renderer | P0 | 6-week sprint |
| T32 | `/programs/<slug>.html` vs `/teams/<slug>.html` IA split | Part I §14.1 open question: "Should `programs/<slug>` be deprecated and folded into `teams/<slug>`?" | Two URLs, two renderers, two purposes (history vs current season). Nav confusion documented by the audit. | P0 | 2 days (decision) + 5 days (consolidation) |

### 2.4 Why ND vs FIU feels jarring

Three reasons, in priority:

1. **The legacy renderer (FIU) has visual rhythm; the world-class renderer (ND) has visual real-estate.** FIU's `.panel` + `.stat-card` density is fast to scan even when generic. ND's modules each claim a viewport. When the underlying data is sparse (May, offseason, Pulse at zero mentions), the world-class page feels like a designed magazine spread with most pages blank.
2. **Accent leakage.** `--team-accent-soft:#b98343` is hardcoded into every `team-shell`-class wrapper across all of `/programs/`, `/teams/` (legacy slugs), and `/players/` — meaning Notre Dame, Alabama, Florida, and FIU all share the same warm-tan secondary. Only `/teams/notre-dame.html` (and the other 16 profiled slugs) successfully sets ND's gold #C99700 secondary via the new renderer's `--accent-secondary` token. So the user clicking through ND → Alabama → FIU sees the same warm tan three times despite three completely different brand systems.
3. **Bebas Neue is declared but not used at hero scale on team pages.** The token system locked `--font-display: 'Bebas Neue'` on 2026-05-16 (see `00-tokens.md:106`). The ND team hero wordmark is in `var(--font-display)` per the team-pages CSS, but the `hero__record 10-2` and `hero__metrics .metric-tile__value` are in `var(--font-serif)` (Source Serif Pro). The brief calls for *"big display-font number"* on the page's loudest stat — ND's 10-2 record is rendered at the size and weight of the heritage strip beneath it, not at hero-display scale. Visual hierarchy collapses.

---

## Part 3 — Cross-cutting issues

These affect both player AND team pages.

**Per-team accent system is half-wired.** The `team_pages/` Profile renderer correctly threads `--accent-primary` + `--accent-secondary` from `profile.accent_hex` and `profile.accent_hex_secondary` into the team-shell wrapper for the 17 profiled slugs. For every other slug — and every player page, every program-history page, and every conference page — the legacy `reporting.py` writes the team-shell wrapper with `style="--team-accent:#XXXXXX; --team-accent-soft:#b98343;"` where the `--team-accent-soft` value is the same b98343 fallback. **Audit-confirmed across 4 sampled pages: Mendoza (Indiana), ND program, Alabama program, FIU.** The accent token system was built; the rollout never finished. This is a 4-hour fix in reporting.py if a per-team `accent_hex_secondary` lookup is wired into the same place the primary lookup lives.

**Bebas Neue is declared but invisible.** Locked in tokens.css 2026-05-16. Hero finding pages and the Saturday Strip use it. Player hero wordmarks (Mendoza's name renders in `--font-display`), team hero wordmarks (ND's name renders in `--font-display`), and big-number stats on those heroes do not. The visual signature of the design system is missing from the visible page-tops where it should land hardest. Probably one CSS rule per renderer.

**Receipt-pattern citation density is hitting on editions and not on the rest of the product.** The Pattern C/D citation infrastructure was built (per completed task #24). It's visible on `/editions/<n>/<slug>` per the design-system doc spec. Player pages have ONE inline confidence chip (HIGH CONFIDENCE · through week 16) and no inline receipt markers. Team pages have source attribution on Chronicle cards (`gamelog · 2025 season · wk 13` / `Savant card · 2025 season through postseason`) — which IS receipt-pattern compliant. Player pages need the same treatment for every stat citation: at minimum on the Heisman Lens probabilities, the Signature Story percentile, and the Achievement criteria.

**Chart vocabulary compliance.** `31-chart-vocabulary.md` allows six chart types and explicitly forbids pie / vertical bar / radar (except player fingerprint). The Mendoza Scenario Explorer renders a slider widget (not a chart). The Notre Dame Pulse renders a number `—` placeholder. The Notre Dame Savant card renders horizontal percentile bars (allowed). The CFP-Era Arc card renders an annotated line + bricks (allowed). The legacy program-history page renders a hybrid `historyGradient`-filled vertical bar + line overlay — **this is the kind of bar chart the chart vocab explicitly forbids except where it's the percentile primitive.** Either re-classify it as an allowed "percentile bar" (in spirit it is one), or rebuild it as an annotated line per the locked vocabulary.

**Confidence signaling is partially implemented.** `33-confidence-signaling.md` mandates 3 bands (high/medium/low) + unset, with `confidence_calibration` table, per-domain calibration. Player page has `fi-confidence--high` chips visible. Team page Chronicle cards have source-line attribution but no confidence band chip. The receipts on the Signature Story have a HIGH/n=389 chip. **Inconsistent application — not absent.**

**Reading-ladder discipline broken on player pages.** Brief §2 design rule: *"No module mixes tiers."* The Mendoza page interleaves a 30-second module (Heisman Lens 5-cell snapshot) with a 5-minute module (Signature Story full grid) with a deep-dive module (Scenario Explorer slider) all above the fold. The 5-second read is absent; the 30-second / 5-minute / deep are mashed together. This is the most fundamental brief violation on player pages.

**Mobile-first is aspirational.** The site renders responsively, but no module on either the Mendoza page or the ND team page is mobile-FIRST. The Mendoza Signature Story has a 2-column desktop grid that stacks vertically on mobile; that's responsive-down, not thumb-native. The brief's "five vibe cells horizontal snap-scroll" pattern is not implemented anywhere.

---

## Part 4 — The "why does it look ugly" answer

In plain English, distilled to seven root causes:

1. **The player page never got the renderer the brief asked for.** Mendoza's page is the legacy directory-card chrome wrapped around a few real modules (Signature Story, Narrative Arc, Scenario Explorer). The hero isn't a QB Fingerprint; it's four generic stat tiles. The standing isn't a rail; it's a JSON datum that never renders. The Savant card doesn't exist for players. The Selector Grid — the brief's single most-named asset — was never built. A page can be polished and still look generic when its hero says nothing specific.

2. **Bebas Neue is invisible on the loudest surfaces.** The display font that gives the brand its stadium-scoreboard energy was locked into tokens but never wired into the hero numbers. Source Serif Pro is doing the work that Bebas Neue should do, and serifs at hero scale read as 2014 startup blog rather than 2026 sports data terminal.

3. **`--team-accent-soft:#b98343` leaks across every legacy page.** The accent token system half-shipped. Click through three programs and you see the same warm-tan three times. The visual identity that should differentiate ND-navy-gold from Alabama-crimson-white from FIU-teal-gold collapses to one chrome color.

4. **The world-class team pages are scaffolds with empty rooms.** ND's `/teams/` page has the Pulse, Chronicle, Savant, Rivalry scaffold, Season Arc — but in late May, the Pulse shows zero mentions and one boilerplate quote, the Chronicle has 4 cards instead of 5-6 cards across 3 of 6 types, the Rivalry thermometer is missing, the five-axis strip isn't drawn. A designed empty state is honest; a half-designed empty state looks unfinished.

5. **Two URL families, two renderers, one user mental model.** `/programs/notre-dame.html` is the legacy history-explorer (generic chrome + bar chart). `/teams/notre-dame.html` is the world-class current-season Profile. The "2025 Season Page" button on the program page bounces to the team page; nothing tells the user the experiences differ. The CLAUDE.md note about flat program URLs being intentional is true at the URL level, but no UX clarifies why two pages exist for the same entity.

6. **The reading ladder collapses on player pages.** The 5-second / 30-second / 5-minute tiering is the brief's whole architecture. Mendoza's page mixes all tiers above the fold and never delivers a 5-second hero. The eye doesn't know where to land.

7. **Sixteen mockups produced in Figma. Five (roughly) shipped.** The Iteration Log enumerates: Hero Arc (131-bar), CFP-Era 13-brick, current-season theater, the Pulse, Rivalry Card with dual-trajectory, Chronicle 4 card-types, Historical Season Deep-Dive (ND 2018 "The Proof"), CFP-Era multi-metric, Mobile 390pt, Seasonal sentience 4-state grid, Game Recap Mode (post-loss), Program-tier sentience UMass study, Deep program profile Vanderbilt, 4-program payoff render, Savant card, Full desktop composition. Of those: Pulse + Chronicle + Savant + Rivalry Card scaffold + CFP-Era Arc are partially live. The other eleven exist as concepts and HTML mockups in `docs/mockups/` (mockup_02_team_alabama_v2.html, mockup_03_team_vanderbilt_v2.html, team_page_surface2_specimen.html, team_page_rituals_specimen.html, etc.) but were never moved into the renderer. That's a 30% conversion rate from designed to shipped, with the brand's most differentiating concepts (Hero Arc, dual-thermometer rivalry, seasonal sentience accent flip, game recap mode, program-tier divergence) on the cutting-room floor.

---

## Part 5 — World-class implementation plan

Sprints are sized for solo + AI-assisted dev per the iteration log's stated constraints. Days are realistic — not aspirational. Ordering is by visible impact × dependency unlock.

### 5.1 Sprint structure

- **Sprint A — Player Hero Rebuild (3 days).** Highest-leverage 3 days on the site. Replaces the generic player identity strip with a real QB Fingerprint + Standing Rail. Player pages stop looking like directory cards.
- **Sprint B — Token Cleanup (1 day).** Bebas Neue wire-up on hero numbers, accent_secondary rollout across the legacy renderer. One-day visual lift.
- **Sprint C — Player Page Module Backfill (5 days).** Selector Grid, Savant card for players, Achievements ribbon renderer (data already exists), Hot-Take + Anti-Take pair.
- **Sprint D — Team Pulse Completion (3 days).** Five-axis strip, Home/Away mood split, Chronicle Echo + Retroactive cards. Closes the brief's Panel 2/3 gaps in The Room.
- **Sprint E — Team Hero Arc + Rivalry Thermometer (4 days).** Part II §20 hero stripe, dual-thermometer Fan Heat Index. The two screenshot-virality moves the brief explicitly named.
- **Sprint F — `/programs/` ↔ `/teams/` IA decision + consolidation (5 days).** Either deprecate `/programs/<slug>.html` or fold it under a single Profile renderer. End the parallel-stack problem.
- **Sprint G — Long-tail team page coverage (6 weeks, parallel).** Roll the world-class renderer to the remaining 113 FBS programs that don't yet have profile YAMLs. Each profile = ~4hr Claude-assisted research + 30 min human review per Part III §34.4.

### 5.2 Sprint detail

**Sprint A — Player Hero Rebuild (3 days)**

- *Goal:* The Mendoza page opens with a 5-second readable identity (name + team + 1 vibe number + 1 trajectory + 1 rung). Visual ladder is unambiguous.
- *Surfaces touched:* `src/cfb_rankings/reporting.py` player-page render path (`_assemble_player_page_data` and the hero block per `PLAYER_PAGE_WORLD_CLASS_BRIEF.md §1.13` — entry point); new CSS in a new `src/cfb_rankings/player_pages/assets/styles.css` to avoid bloating reporting.py CSS; new partial `_render_qb_fingerprint(player, season)`.
- *Definition of done:* (a) the 5 vibe cells render Eyebrow → big tabular number → 14px sentence with one Trajectory Spark per cell; (b) Bebas Neue on the hero number; (c) gold ribbon with 3 live accolade chips (Heisman Heat / Davey O'Brien / Consensus AA); (d) 17-rung Standing Rail with filled gold marker at current rung + tier-pill row underneath; (e) mobile renders at 390pt with vibe cells in horizontal snap-scroll.
- *Risk:* `reporting.py` is 26.8k lines and any new hero block is doing surgery on the busiest file in the codebase. Mitigate by writing the new renderer as a standalone `src/cfb_rankings/player_pages/` module like `team_pages/` and short-circuiting reporting.py the same way (per CLAUDE.md's `PROFILED_SLUGS` pattern).
- *Days:* 3.

**Sprint B — Token Cleanup (1 day)**

- *Goal:* Bebas Neue on hero numbers across player + team + program pages; per-team `--accent-secondary` propagation across the legacy renderer.
- *Surfaces:* `src/cfb_rankings/reporting.py` accent-strip emitter (grep for `--team-accent-soft:#b98343`); team-pages tokens.css `--fs-hero` weight selector; player_pages/styles.css (created in Sprint A).
- *Definition of done:* (a) ND program page shows ND gold #C99700 as `--team-accent-soft`, not #b98343; (b) Alabama shows white as secondary; (c) Mendoza's hero record `10-2` renders in Bebas Neue at the size token's max; (d) Browser-MCP screenshot diff against 3 programs shows three different gradient envelopes.
- *Risk:* `--team-accent-soft` is referenced in ~20+ places across CSS rules — pure search-and-replace plus per-team lookup. Low risk.
- *Days:* 1.

**Sprint C — Player Page Module Backfill (5 days)**

- *Goal:* Bring the player page to module parity with the team page. Selector Grid + Savant card + Achievements ribbon + Hot-Take/Anti-Take pair.
- *Surfaces:* new `src/cfb_rankings/player_pages/savant_card.py` (lift the team-pages Savant template, swap metrics to the QB 12); new `src/cfb_rankings/player_pages/selector_grid.py` (renders 11-pill grid from `player_honors` table); new `src/cfb_rankings/player_pages/achievements_ribbon.py` (parse the existing JSON-encoded achievement Python-repr strings — already in the page-state — into gold medallions); new `src/cfb_rankings/player_pages/hot_take.py` (rules engine reading from `player_savant_weekly` candidate stats).
- *Definition of done:* Mendoza page shows 12-bar percentile Savant card with peer toggle; 11-pill Selector Grid for All-America bodies even when all empty; 3 gold Achievement medallions hover-revealing rarity %; one Hot-Take + Anti-Take card pair.
- *Risk:* Hot-Take generation is non-trivial — start with a deterministic rules engine, not LLM. Validate against the brief's "no clickbait" / "must be defensible" rule.
- *Days:* 5.

**Sprint D — Team Pulse Completion (3 days)**

- *Goal:* Finish "The Room on [Team]" Panels 2 and 3.
- *Surfaces:* `src/cfb_rankings/team_pages/the_room_renderer.py` (already exists per ls output); `src/cfb_rankings/team_pages/styles.css`.
- *Definition of done:* Pulse module renders five-axis strip (Reality Gap / Respect Gap / Cohort Divergence segmented bar / Rival Heat 3-pill / Volatility) with real numbers when data ≥ floor and honest empty-states when below floor; Home/Away mood split panel with the two-thermometer treatment.
- *Risk:* Data availability for some axes (especially Home/Away mood split — requires geographic source filtering). Ship the panel with "Local market signal not yet ingested" honest empty-state if needed.
- *Days:* 3.

**Sprint E — Team Hero Arc + Rivalry Thermometer (4 days)**

- *Goal:* Two highest-virality team-page modules.
- *Surfaces:* new `src/cfb_rankings/team_pages/hero_arc_stripe.py` (lift logic from `docs/mockups/mockup_02_team_alabama_v2.html` which already has the 13-brick CFP-era stripe HTML); modify `src/cfb_rankings/team_pages/rivalry_card.py` to add the dual-trajectory Heat chart + thermometer pair (the brief gives full SVG specs).
- *Definition of done:* Notre Dame `/teams/` page opens with the 13-brick CFP-era hero (each brick = 2014-2026 season, accent-gold for CFP appearance), and the ND/USC rivalry card includes the side-by-side fanbase-heat thermometer.
- *Risk:* The brief allows two registers (131-season climate stripe + CFP-era 13-brick). Iteration Log §4 locked v1.0 = CFP era (2014–present). Ship the 13-brick version; defer the 131-bar version to v2.
- *Days:* 4.

**Sprint F — `/programs/` ↔ `/teams/` IA consolidation (5 days)**

- *Goal:* End the parallel-stack problem the audit identified.
- *Surfaces:* `src/cfb_rankings/cli.py` build-site dispatcher; `vercel.json` rewrites if needed.
- *Decision needed first (1 day):* per `TEAM_PAGE_WORLD_CLASS_BRIEF.md §14.1`, do we (a) deprecate `/programs/<slug>.html` and 301-redirect to `/teams/<slug>.html` after folding history INTO the team page's Arc module, or (b) keep both but explicitly link them with a "View 2025 Season" / "View Full History" toggle that's visible on both?
- *Definition of done:* one of the two architectures shipped; nav confusion removed; the "Programs" top-nav link goes to the same page family as the "Teams" link; the brief's open question §14.1 is answered.
- *Risk:* High — this URL change touches existing SEO and the entire crosslink graph in reporting.py. Strong mitigation: option (a) keeps URLs but moves rendering responsibility, no link rewriting needed.
- *Days:* 5.

**Sprint G — Long-tail team page coverage (6 weeks, parallel)**

- *Goal:* Brand position per Part III §39 — "every team's page with equal editorial care at that team's own level of stakes."
- *Surfaces:* new `profiles/*.md` files for the ~113 unprofiled FBS programs.
- *Definition of done:* every FBS team renders via the world-class `team_pages/` renderer; the legacy reporting.py team-card path is deletable; UMass and Alabama both look bespoke at their tier's stakes.
- *Risk:* Editorial-review bandwidth (Part III §34.4 estimates ~600 hours for 130 programs). Mitigate by tiered priority: T1-T2 (top 20) hand-reviewed; T3-T5 Sonnet draft + light review; T6-T10 Sonnet/Haiku batch + spot review.
- *Days:* 6 weeks parallel to A-F.

### 5.3 What I would ship first

**Sprint B (token cleanup, 1 day).** Defended choice. Three reasons:

1. It changes the visible top-of-page on every team and player page simultaneously. The user sees a different site in 5 seconds without any new architecture.
2. The brief's *single most-cited typography call* — *"the rhythm rule: every number that is a data point is tabular-nums + slightly heavier than its label … bright number, quiet label … violating this is the cardinal sin"* — is half-violated everywhere right now. Bebas Neue on hero numbers solves this in one CSS rule per renderer.
3. The accent leakage is one of the named root causes of the "ugly" feedback. Per-team accent_secondary in reporting.py is half-a-day of work.

If Sprint B doesn't change the perception, Sprint A is wrong about Sprint A. If it does, you've earned the right to spend three days on Sprint A.

---

## Part 6 — What to NOT do

These are in the briefs and should be deprioritized or actively rejected right now:

1. **Don't build the 131-season climate stripe (Part II §20 v2).** The Iteration Log §4 locked v1.0 = CFP era. The 13-brick CFP-era variant is the right scope for now. Deferring the 131-season version is correct.

2. **Don't build the Community Annotation Layer (Part II §27) before the Hero Rebuild ships.** The brief says *"shipping the read path is easy. Shipping the write path without moderation is reckless."* True — but more importantly, an annotated page that still looks generic is a worse spend than fixing the hero.

3. **Don't build the Wrapped stack generator (Part II §21.3) in 2026.** Wrapped requires synchronized cross-team simultaneity — its value comes from every fanbase posting the same artifact the same day. That's a January 2027 ship at earliest. Build the share-card renderer FIRST as the underlying primitive (it pays back across every module), then layer Wrapped on it.

4. **Don't build the Tab-as-Room IA prototype (Part II §23) until the scroll-anchor model is fully shipped.** The brief itself says *"both designs valid … prototype both on Alabama … recommend prototype, not a bet made in the brief."* Right now there's no production scroll-anchor model finished — prototyping its replacement is premature.

5. **Don't build the Draft Day Live module (Season-Phase §8.3) in 2026.** The brief is explicit: *"Draft Day Live would have been ideal to ship THIS week for the 2026 draft (April 23-25). That's not realistic — we're hours from Round 1. Ship it after draft week completes and stage it for 2027."* That window has already closed for 2026.

6. **Don't ship the Hype Meter without a live-game data pipeline.** It depends on per-minute aggregated reactions; without infrastructure for that, it's a fake-energy module. Build the pipeline before the UI.

7. **Don't keep iterating new Figma mockups before existing mockups ship.** The Iteration Log shows 16 designed and ~5 partially shipped. Every additional mockup widens the design-to-ship gap. Freeze new mockup work until the conversion rate is above 70%.

---

## Appendix A — Module-level checklist

Long table. One row per designed module. "Live state" reflects what the persisted Vercel fetches showed; "Evidence" is a class-name or other concrete proof for live shipped modules.

| Module | Source brief | Renderer/file (if exists) | Live state | Evidence |
|---|---|---|---|---|
| Player hero — generic identity strip | (legacy) | `reporting.py` player render | shipped (legacy) | `class="profile-identity-v2"` |
| Player hero — QB Fingerprint (5 vibe cells) | Player Brief §4.1 | — | missing | — |
| Player hero — accolade ribbon 3 cards | Player Brief §4.1 right column | — | missing | — |
| Standing — 17-rung rail | Player Brief §7 | — | data-only | `"standing_rung":15` in JSON |
| Standing — 6 tier pills | Player Brief §7.4 | — | missing | — |
| Standing — rung drawer | Player Brief §7.4 | — | missing | — |
| Standing — accolade tabs nested | Player Brief §7.4 | — | missing | — |
| Selector Grid (11 pills) | Player Brief §7.5 | — | missing | — |
| The Room on [Player] | Player Brief §4.2 | (data-blocked) | empty-state | `mood-waiting-banner` text |
| Player Savant card (12 bars red→grey→blue) | Player Brief §4.5 | — | missing | — |
| Splits tabs (4) | Player Brief §4.6 | — | missing | — |
| Signature Story | Player Brief §4.7 | `reporting.py` | shipped | `<article class="signature-story">` |
| Signature Play | Sig Bets #8 | `reporting.py` | empty-state stub | `signature-play--empty` |
| Narrative Arc 3-act | Sig Bets #14 | `reporting.py` | shipped | `<article class="narrative-arc">` |
| Scenario Explorer | Sig Bets #12 | `reporting.py` | shipped | `<article class="scenario-explorer">` Alpine |
| Hot-Take + Anti-Take | Sig Bets #2, #3 | — | missing | — |
| Mirror Match | Sig Bets #4 | — | missing | — |
| Achievements ribbon | Sig Bets #7 | (data only) | data-only | JSON Python-repr in page-state |
| FI Glossary `?` icons | Sig Bets #5 | `reporting.py` | partial (team archetype only) | `<button class="fi-glossary">` |
| What Changed diff | Sig Bets #6 | `reporting.py` | placeholder | `<div data-what-changed>` |
| Live Signal Flow bar | Sig Bets #13 | — | missing | — |
| Rival Radar | Sig Bets #1 | — | missing | — |
| Coaching Lineage | Sig Bets #11 | — | missing | — |
| Cohort Divergence Map (2D scatter) | Sig Bets #10 | — | missing | — |
| Prediction Markets in Hero | Sig Bets #9 | — | missing | — |
| Phase banner | Season-Phase Doc §6 | `reporting.py` | shipped | `<div class="phase-banner">` |
| 2026 Outlook (7 cells) | Season-Phase Doc §8.1 | partial via Heisman Lens | partial | `<section id="current-heisman-lens">` |
| Development Trajectory | Season-Phase Doc §8.2 | — | missing | — |
| Draft Day Live | Season-Phase Doc §8.3 | — | missing (correctly deferred) | — |
| Offseason Status chip | Season-Phase Doc §9 | — | missing | — |
| **Team page** | | | | |
| Team hero — wordmark + heritage strip + Story | Engagement Brief §B | `team_pages/renderer.py` | shipped | `<section class="hero">`, `hero__heritage`, `hero__state` |
| Team hero — Story Right Now sentence | Engagement Brief §B | `narrative_generator.py` | shipped (excellent) | `<p class="hero__state">` |
| Team hero — Arc stripe (13-brick CFP-era) | Team Brief Part II §20 | — | missing | — |
| Season Standing 9-rung rail | Team Brief §3.1 | — | missing | — |
| Program Prestige 7-tier rail | Team Brief §3.2 | — | missing | — |
| The Room — Panel 1 archetype + headline | Team Brief §4.2 | `pulse_*.py` | shipped (offseason-quiet) | `<section class="pulse">` |
| The Room — Panel 2 five-axis strip | Team Brief §4.2 | — | missing | — |
| The Room — Panel 3 Home/Away mood | Team Brief §4.2 | — | missing | — |
| The Room — Panel 4 storylines | Team Brief §4.2 | `pulse_*.py` | partial | `pulse__event-log` |
| The Room — Panel 5 confidence badge | Team Brief §4.2 | partial | partial | `pulse__badge--awaiting` |
| Team Savant Card (15 metrics, 3 tabs) | Team Brief §5 | `savant_card.py` + `.css` | shipped | `<section class="savant-card">` |
| Season Arc — This Season weekly | Team Brief §6.2 | — | missing | — |
| Season Arc — Era view | Team Brief §6.3 | — | missing | — |
| Season Arc — All-Time decade | Team Brief §6.4 | — | missing | — |
| Season Arc — CFP-Era (v1 scope) | Iteration Log §4 | `season_arc_card.py` | shipped | `<section class="season-arc">` evidence |
| Rivalry Card — Zone 1 mythic header | Team Brief §7.2 | `rivalry_card.py` | shipped | `render_rivalry_card` invoked |
| Rivalry Card — Zone 2 four-axis matrix | Team Brief §7.2 | — | missing | — |
| Rivalry Card — Zone 3 timeline | Team Brief §7.2 | `rivalry_card.py` | partial | meetings list rendered |
| Rivalry Card — Zone 4 game-week + thermometer | Team Brief §7.2 | — | missing | — |
| Recruiting Pipeline 3 panels | Team Brief §8 | — | missing | — |
| Coaching Staff Scheme Fingerprint | Team Brief §9 | — | missing | — |
| Conference Lens toggle | Team Brief §10 | — | missing | — |
| Fanbase Health Index | Team Brief §11.1 | — | missing | — |
| Ceiling vs Floor projections | Team Brief §11.2 | — | missing | — |
| Home-field advantage chip | Team Brief §11.3 | — | missing | — |
| Quiet Years Detector | Team Brief §11.5 | — | missing | — |
| Fanbase Fracture Detector | Team Brief §11.6 | — | missing | — |
| The Moment Signal banner | Team Brief §11.7 | — | missing | — |
| Aspiration Ladder | Team Brief Part III §33.4 | — | missing | — |
| Chronicle — Moment card | Team Brief Part III §36 | `chronicle_generator.py` | shipped | `chronicle-card--moment` |
| Chronicle — Anomaly card | §36 | `chronicle_generator.py` | shipped | `chronicle-card--anomaly` |
| Chronicle — Flashpoint card | §36 | `chronicle_generator.py` | shipped | `chronicle-card--flashpoint` |
| Chronicle — Echo card | §36 | `chronicle_streams.py` | not seen live | — |
| Chronicle — Retroactive card | §36 | `chronicle_generator.py` | not seen live | — |
| Chronicle — Player Arc card | §36 | `chronicle_streams.py` | not seen live | — |
| Rituals strip | Part III locked design system | `rituals_module.py` | shipped beautifully | `<section class="rituals">` 5 cards |
| Cultural anchors aside | Part III §34 | `renderer.py:_render_cultural_anchors` | shipped | `<aside class="cultural-anchors">` |
| Mascot voice fallback | Part II §24 | `profile_loader.py` | shipped for 17 slugs | "The Leprechaun is keeping his own counsel" |
| Seasonal sentience accent flip | Part III §32 | `state_resolver.py` | resolver exists, accent invisible | — |
| Program-tier sentience differentiation | Part III §33 | `profile_loader.py` | implicit via profile | — |
| Wrapped stack | Part II §21.3 | — | missing | — |
| Kickoff Check-In counter | Part II §22.1 | — | missing | — |
| Hype Meter | Part II §22.2 | — | missing | — |
| Weekly Fanbase Leaderboard | Part II §22.3 | — | missing | — |
| Program Similarity Engine | Part II §26 | — | missing | — |
| Tab-as-Room IA | Part II §23 | — | not prototyped | — |
| Community Annotation Layer | Part II §27 | — | missing | — |
| Share-Card renderer | Part II §21.2 | — | missing | — |

Tally: of approximately 70 designed modules across both briefs, the live site ships roughly 18 cleanly, 8 partially, and 44 not at all. That's a ~25% ship rate against the design vision.

---

## Appendix B — Tokens + typography spot check (Notre Dame)

Notre Dame's profile YAML drives the team_pages renderer at `/teams/notre-dame.html`. Expected colors per `00-tokens.md` "Program-variable tokens" examples and per the brief's per-team accent system:

```
[data-program="notre-dame"] {
  --color-accent-primary:   #0C2340; /* navy */
  --color-accent-secondary: #C99700; /* gold */
}
```

What the live page emits in inline `<style>` and inside the team-shell wrapper:

- ND `/teams/notre-dame.html` (world-class renderer): emits `--accent-primary: #0C2340; --accent-secondary: #c5b358;` in `:root`. Wait — `#c5b358` is the default `--accolade-gold` from `team_pages/assets/tokens.css:23`, not ND's brand gold `#C99700`. Inspection of `team_pages/profile_loader.py` and ND's profile YAML would confirm whether ND's profile sets accent_hex_secondary; if it does, the renderer should override the default. The rendered output `--accent-secondary: #c5b358;` suggests ND's profile YAML is NOT setting accent_hex_secondary, so the default fires. **Bug or unfinished profile — fix is to add `accent_hex_secondary: "#C99700"` to `profiles/notre-dame.md`.**
- ND `/programs/notre-dame.html` (legacy renderer): emits `<section class="team-shell" style="--team-accent:#0C2340; --team-accent-soft:#b98343;">`. **`--team-accent-soft:#b98343` is the warm-tan fallback discussed above. Should be ND gold.**
- Mendoza `/players/fernando-mendoza-38276.html` (legacy renderer, Indiana team-shell): emits `--team-accent:#990000; --team-accent-soft:#b98343;`. **Indiana primary is correct (#990000); secondary leaks to b98343.**

Where the mismatch lives in code:

- For the team_pages renderer: `src/cfb_rankings/team_pages/renderer.py:334-335`:
  ```
  accent_primary = profile.accent_hex
  accent_secondary = profile.accent_hex_secondary or _darken_color(accent_primary)
  ```
  ND's profile should set `accent_hex_secondary`. If it's blank, `_darken_color(#0C2340)` runs — which would not produce `#c5b358`. So either the file produces an unexpected hex, or `profile.accent_hex_secondary` resolves to `None` and the renderer is falling through to a `--accolade-gold` default elsewhere. **Trace by reading `profile_loader.py` and the ND profile YAML.**
- For the legacy renderer: search reporting.py for the literal string `b98343` — likely in a `team-shell` emit. Replace with a per-team lookup: e.g. `team.accent_secondary or '#b98343'`, then add a 130-team CSV/YAML mapping for the secondary.

Typography spot check on the ND hero:

- `hero__wordmark` ("Notre Dame") — `font-family: var(--font-display)`, size `--fs-hero` (clamped 32-56px). **Bebas Neue if loaded; system fallback if not.** The `<link rel="preload">` for Bebas Neue should be in `<head>`; if it's not, FOUT during the first paint. Worth verifying via Network panel.
- `hero__record` ("10-2") — `font-family: var(--font-serif)`. Source Serif Pro. **Should be `var(--font-display)` per the brief's "big display number" rule for the loudest stat on the page.** One CSS rule.
- `metric-tile__value` (4-tile row: 10-2 / #9 / +7.8 / #11) — `font-family: var(--font-serif)`. Same call: should be `var(--font-display)`.
- `pulse__mood-number` (currently `—`) — `font-family: var(--font-display)`. **Correct** when there's a number to display.
- `chronicle-card__headline` (h3) — `font-family: var(--font-serif)`. **Correct per brief; headlines stay editorial-serif.**

So the typography spec is right; the hero numbers just don't use the right family. Fix is two lines in `team_pages/assets/styles.css`.

---

End of audit.
