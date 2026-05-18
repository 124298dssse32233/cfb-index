# CFB Index — Triple Audit, v2 (Deep)

**Date:** 2026-05-15
**Auditor:** Claude (autonomous, orchestrated 6-investigator parallel deep-dive)
**Live site:** https://wonderful-margulis-8ec96b.vercel.app (build 25925571518, deployed 15:15 UTC)
**Branch:** claude/romantic-euclid-fd39e3
**Supersedes:** [DESIGN_AUDIT_2026_05_15.md](DESIGN_AUDIT_2026_05_15.md) (v1, written same day)

### Backfill-aware caveat (read first)

A historical-data backfill (`backfill-full-history` run 25926317548, `start_season=2020`, `end_season=2025`, `skip_reddit=true`, `skip_models=true`) is in-flight at audit time, ~1 hour into a ~4-hour run. Phase 3 (player season context) is currently executing; phases 4–7 (game-level player stats, Reddit-skipped, fan-intel rebuild, DB inventory + publish-site auto-trigger) have not yet completed. The live site reflects the **prior** deploy and is missing the data that will exist post-backfill.

**Findings in this audit are partitioned:**

- **STRUCTURAL** (most findings) — design, layout, code organization, navigation, asset hygiene, accessibility, performance. These are real today and persist after the backfill.
- **DATA-FLOW** (a minority of findings) — content emptiness or thin coverage that resolves automatically when phases 3–6 complete and `publish-site` fires. Marked `[BACKFILL-RECOVERS]` throughout.
- **MIXED** — surfaces with both a rendering pathology *and* a data pathology. Each is split into the two layers.

This audit critiques structure with full force and defers content-emptiness judgment where the backfill will resolve it.

---

## What's New in v2 (Delta from v1)

v2 was produced by dispatching six parallel specialized investigators against orthogonal dimensions, plus integrating two clarifying inputs from the owner (backfill state + extended moat list). The deltas:

1. **DB-side moat-to-renderer matrix** — `team_savant_weekly`, `team_chronicle_observations`, `team_season_arc`, `player_week_conversation_features`, `predictive_claims` are read by 5+ render paths each but the local DB has 0 rows (backfill-recovering for some; flag for others).
2. **Per-renderer quality matrix** — 15 renderer files surveyed, each labelled `PRODUCTION` / `PARTIAL` / `STUB` with line counts, CSS strategy, and concrete data-table reads.
3. **Token-drift quantification** — five hardcoded "gold" hex values (`#c9a24a`, `#E0A300`, `#f4c95d`, `#c5b358`, `#FFB800`) across four renderers. No shared token source.
4. **Concrete competitive references with URLs** — 15 named treatments from ESPN, On3, 247Sports, Stathead, Basketball-Reference, Winsipedia, PFR, The Athletic, NYT Mag, Bloomberg Businessweek, FT Big Read, FiveThirtyEight, Polymarket, Reuters, AP.
5. **Icon family recommendation (Phosphor)** + 12-glyph bespoke commission plan + source-platform licensing matrix (which logos you can ship, which require text-only fallback).
6. **Complete `@font-face` recipe for Vercel static** — Fontsource WOFF2s + size-adjust fallback metrics for zero CLS + preload + `vercel.json` cache headers — drop-in code.
7. **Typography psychology critique** — Source Serif Pro → Charter migration argument. Type-scale midpoint compression. Six concrete directives.
8. **College-football-specific color palette** — field green, concrete gray, band brass, deep crimson, burnt orange — replacing the current fintech-borrowed semantic ramp.
9. **Density-per-surface targets** — explicit row heights, column counts, inter-module gap reductions.
10. **Editorial-voice atoms** — pull-quote, drop cap, marginalia, decorative dividers — none currently shipping.
11. **Motion patterns** — chart-on-scroll reveal, hover-lift specifics, sticky read-progress, page-turn for editions, sortable column highlights.
12. **WCAG 2.1 AA failures** — `#c9a24a` on `#f6f1e6` = 3.2:1 (fails 4.5:1). Touch target sizing. `prefers-reduced-motion` coverage gap (15 declarations).
13. **Quantified perf measurements** — 77 MB image directory, 5,842-line CSS bundle, ~300 KB inline-CSS duplication across 150 team+history pages, zero `@font-face` in three edition renderers.
14. **Sprint-sized roadmap** — concrete sequencing of fixes into 5 sprints, with effort estimates.
15. **Three identity-defining moves** — masthead typographic identity, persistent source-trust layer, cohort-divergence universal atom.

---

## Part 1 · Strategic

### Executive Summary

**TL;DR (three bullets, sharpened):**

- **There are two world-class surfaces (`/hub/` and profiled team pages) and seventeen generic ones; closing the gap is the entire product opportunity.** Hub renders 28 inline charts and reads from 7 fetch-paths; profiled team pages ship Hero + Savant + Rivalry + Chronicle + Era arc. Every other shipping renderer (`wire/`, `reactions/`, `mailbag/`, `daily/`, `storylines/`, `canon/`-list, `editions/`-article, `conferences_pulse/`, `provenance/methodology`, `the_room`) is text-prose with inline CSS that re-invents the token dictionary.
- **The proprietary moat is genuine, large, and invisible outside two pages.** Owner-confirmed moats: CFBD Tier 2 (30k calls/month), Arctic Shift Reddit (back to 2013), Wikipedia pageviews + edits, Locked On podcasts, campus newspaper RSS, Spotify charts, school athletics feeds, plus Bluesky, GDELT, SeatGeek, prediction markets, beat-writer Substack, YouTube. The pipeline ingests ALL of these; only Hub and (degraded) team-page Pulse visualize any of it. Every other page is moat-blind to the user.
- **There are five token vocabularies, four "gold" hex values, three pages with no font loaded, two competing navs (9 vs 5), one cohort-divergence atom waiting to be lifted from the homepage Canon callout to every page on the site.** Each of these is a 1–3 day fix. Together they're the difference between "blog with charts" and "Athletic-tier product."

**Site aggregate, hero-weighted: ~5.6/10** (vs ESPN/Athletic/538 benchmark). Ceiling is shipped (8.5 on Hub, 7.5 on Alabama). Floor is broken (2 on Players/Heatmap stubs). Six surfaces (Wire, Mailbag, Daily, Reactions, Canon-list, Conferences) cluster around 4 — competent text presentation, zero proprietary visualization. **The median is dragging the brand below where its best work warrants.**

**Top 5 highest-leverage fixes (v2 — sharpened with new findings):**

| # | Fix | Effort | Impact |
|---|---|---|---|
| 1 | **Lift cohort-divergence bar to a universal atom** and use on Reactions, Wire callouts, Canon list rows, Mailbag answers, Homepage Voices. Atom exists once (text-only) on the Canon callout. | 3 days | The single highest-impact brand move available. Defines product identity in one visual element. |
| 2 | **Ship the persistent Source-Trust ribbon** below every team-page hero and on the homepage cover. Eight chips, freshness timestamps per source, color-by-Tier. Pulls from `source_observations` (120 rows live). | 3 days | The proprietary moat made literally visible. No other CFB site can copy this without first building the pipeline. |
| 3 | **Consolidate to one paper bg, one ink, one gold via shared `design_tokens.py`** — then rewrite Wire, Reactions, Mailbag, Daily, Storylines, Editions renderers to import from it. Eliminates the four-hex gold drift and the five-vocabulary token sprawl. | 5 days | Foundational. Every subsequent design fix is easier and stays consistent. |
| 4 | **Replace bottom-nav emojis with Phosphor SVG glyphs + expose full taxonomy via hamburger.** Currently emoji glyphs + only 5 destinations on mobile vs 9 on desktop. | 1 day | Removes the single loudest "hobby project" signal. |
| 5 | **Fix the three broken low-effort pages** (`/players/spotlight.html`, `/players/the-room.html`, `/history/heatmap/`) — all 769px tall, two with Times New Roman fallback. Either ship the renderer brief or stub them honestly. | 1–2 days | Removes the three lowest-quality entry points from the navigable surface. |

**Top 5 second tier (effort 1–2 weeks each):**

| # | Fix | Why |
|---|---|---|
| 6 | Rebuild `/reactions/` from text-link headings to magazine cards with cohort-divergence as cover art | The single most-tragic moat-vs-surface mismatch on the site |
| 7 | Wire as triage console — filter chips, IMPACT left-stripe, source chips per row, mobile card transform | 110 rows × 0 filters × 0 source attribution today |
| 8 | Real `@font-face` loading + size-adjust fallback metrics across all renderers | Three pages currently fall back to Times New Roman |
| 9 | Team-art expansion — helmets + wordmarks for 17 profiled programs (Phase 1), top-50 P4 (Phase 2) | 664 slugs × 0 helmets × 0 wordmarks today |
| 10 | Player-page world-class brief execution per `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` | Two of the top-nav destinations are 769px stubs |

---

### The Three Identity-Defining Moves

These are higher-tier than the Top 5 fixes. Each is identity work — single visual moves that change what kind of product this is.

#### Move A: Give the Masthead a Typographic Identity

Every outlet in the ESPN/538/Athletic tier is instantly recognizable by its wordmark. CFB Index's "CFBINDEX" wordmark in the homepage banner inherits from the body sans stack — different rendering on every device. Every other premium outlet has a *fixed* wordmark — The Athletic in GT America Compressed, FiveThirtyEight in Decima Mono Pro, Bloomberg Businessweek in Druk Wide.

Ship a single SVG wordmark. Compressed condensed display face (Barlow Condensed SemiBold 900 or a custom variable-font weight). Used in nav, in masthead, on share cards, in the favicon. One file. Identity work. **Effort: 1 day (commission or curate) + 30 min wire-up.**

#### Move B: Persistent Source-Trust Ribbon on Every Page

This is the single most distinctive design move available to this product. Bottom-of-content (or below-hero on team pages) chip strip: `reddit ●2h  ·  bluesky ●14m  ·  espn ●4h  ·  campus ●1d  ·  wikipedia ●12h  ·  seatgeek ●9h  ·  gdelt ●live  ·  locked-on ●3h`. Dot color = Tier (green Tier A / amber B / gray D). Hover = "last Reddit ingest: 14 min ago — 1,243 mentions today across r/CFB, r/Alabamafootball, r/RollTide."

This is Bloomberg-terminal-tier UX applied to a free-tier sports site. No other CFB analytics property does this. The data is already in `source_observations` (120 rows live, plus the table populates per build). **Effort: 3 days (atom + data plumb + per-page render).**

#### Move C: Cohort Divergence as the Universal Brand Atom

The product's core thesis is "stat-folks and regular fans disagree, and we measure both." The visual that expresses this thesis exists today *exactly once* — as a text-only label on the homepage Canon callout ("STAT FOLKS / FANS / consensus"). Rendered as a 200px horizontal SVG bar with two filled segments in `--color-navy-400` and `--color-coral-400` and numeric end-labels, this atom becomes the FiveThirtyEight probability-needle of CFB Index. It appears on:

- Every Reaction card (as cover art)
- Every Wire row when the divergence threshold is crossed
- Every Canon entry as the argument
- Every team-page Pulse module next to mood number
- Every Mailbag answer where cohort data is relevant
- The homepage Voices module
- The Hub (it's already there in chart form — promote it to atom)

**Effort: 3 days (atom build) + 5 days (eight surface placements).** This is the single highest-leverage brand-identity move available.

---

## Part 2 · The Moats

### Moat Visibility Scorecard v2 (expanded + backfill-aware)

For each owner-named moat: rating, current surface, target surface, reference treatment, backfill effect.

#### Moat 1: CFBD Tier 2 — 30,000 calls/month of advanced metrics

**Capabilities:** EPA, PPA, success rate, explosiveness, opponent-adjusted, win-probability time series, weather, recruiting talent composites, returning production, transfer-portal data.

- **Rating:** Underexposed structurally · `[BACKFILL-RECOVERS]` for `team_savant_weekly` data
- **Where it appears today:** `SavantCard` on 17 profiled team pages — peer-set toggle, 13 metrics, narrative header (where data exists)
- **Where it should appear:** Every team page (664), every player page, Compare page, Wire (as inline anomaly callouts mid-table), Editions cover essay (inline anchors), Heisman board (calibration / receipts)
- **Reference treatment:** ESPN's matchup-predictor arc gauge (https://www.espn.com/college-football/team/_/id/333); The Athletic's Bill Connelly weekly column SP+ ribbon graphs; 538's "vs replacement" sparklines (archive: https://fivethirtyeight.com/features/how-we-designed-the-look-of-our-2020-forecast/).
- **Backfill effect:** Phase 2 (CFBD game history) repopulates `team_savant_weekly`. Phase 3 (player season context) repopulates per-player advanced metrics. Both currently writing. After Phase 4 (game-level player stats), the Savant card data flow recovers fully.
- **Concrete next step:** Lift `render_savant_card` from `src/cfb_rankings/team_pages/savant_card.py` into `src/cfb_rankings/common/atoms.py` and parametrize for unprofiled programs with a degraded-data variant (n=last-3-games when full season unavailable).

#### Moat 2: Arctic Shift Reddit Archive — Historical depth back to 2013

**Capabilities:** Reddit comments + posts archive covering 13+ years of conversation. The pre-existing Reddit ingest already ran (skipped in current backfill); Arctic Shift covers weeks 21–31 (late May through early August — peak offseason fan anticipation).

- **Rating:** Hidden
- **Where it appears today:** Implicitly inside `/hub/` cohort divergence calculations (the data feeds belief / reality_gap / respect_gap features in `fan_intelligence.py`); explicitly visible nowhere
- **Where it should appear:** As a *historical-context* lens on every editorial surface. A Pulse module should be able to say "this is the third-highest June-conversation volume in the Arctic Shift archive for this program." Editions cover essays should embed historical-similarity callouts. Storyline threads should reference the historical archive as evidence.
- **Reference treatment:** Substack's "year-over-year readership" chart; Polymarket's volume-relative-to-base; Wayback Machine's slider control.
- **Concrete next step:** Add a `historical_velocity_callout(team_id, current_week, current_volume)` partial that computes percentile of current volume vs. 13-year history at the same calendar week, returns a one-line "3rd-highest June for this fanbase since 2014" string. Surface in Pulse footer and Daily.

#### Moat 3: Wikipedia pageview + edit signals

**Capabilities:** Programs and players generate edit deltas and pageview spikes that correlate with off-cycle interest events (commitment, scandal, depth-chart shift).

- **Rating:** Hidden
- **Where it appears today:** Inside the `ingest/sources/wikipedia.py` adapter, computed into per-team and per-player interest features; visible nowhere
- **Where it should appear:** As a `Wikipedia mentions ↑ 312% this week` chip on Wire rows for newly-signed players. As a "fan interest spike" sparkline on the Pulse module. As a player-page "national awareness curve" 12-month sparkline.
- **Reference treatment:** Google Trends graph; Wikipedia's own "pageviews" tool.
- **Concrete next step:** Build a single `WikipediaSpike` atom — short sparkline + arrow + percentage — and use on Wire (commitments + portal entries) and Player pages.

#### Moat 4: Locked On Podcast Metadata — Team-Pod Coverage Lane

**Capabilities:** Locked On runs a team-pod for nearly every P5 program plus many G5 / FCS. Episode metadata (titles, descriptions, publish times) yields a per-team conversation lane that complements Reddit + beat-writer signals.

- **Rating:** Hidden
- **Where it appears today:** Inside `ingest/sources/podcasts_meta.py`; visible nowhere on the site
- **Where it should appear:** As a "the team-pod is talking about ___" callout on team pages and Daily. As a podcast-source chip in the Source-Trust Ribbon. As source attribution on Mailbag answers that reference podcast takes.
- **Reference treatment:** Spotify podcast charts integration in The Athletic; Apple Podcasts' "From the same network" rail.
- **Concrete next step:** Add `LockedOnCallout` partial — "Locked On Crimson Tide · this week: 'Why Vandy's spring should worry the SEC' · 2d ago" — with link and freshness. Use on team-page Pulse footer.

#### Moat 5: Campus Newspaper RSS — Local Press Lane

**Capabilities:** School papers (The Crimson White at Alabama, The Daily Iowan at Iowa, The Stanford Daily, etc.) ingested via RSS. Often catch coaching-staff signals and locker-room sentiment 24–72 hours before national press.

- **Rating:** Hidden
- **Where it appears today:** Inside `ingest/sources/campus_news.py`; visible nowhere
- **Where it should appear:** As a "Local press is saying" callout on Pulse modules; as a credibility-tier in the Source-Trust ribbon; as an Editions cover-essay attribution.
- **Reference treatment:** The Athletic's "Local Beat" sidebar; ESPN's reporter network.

#### Moat 6: Spotify Charts — Cultural Signal

**Capabilities:** Per-region Spotify chart movements correlate with regional cultural attention. A specific song trending in Tuscaloosa around game week is a fanbase-energy proxy.

- **Rating:** Hidden
- **Where it appears today:** Inside `ingest/sources/spotify_charts.py`; visible nowhere
- **Where it should appear:** As a *cultural-color* atom on rivalry-week countdowns. "Top regional song this week: ___ · streams ↑ 12%." A small, weird, distinctive surface that ESPN literally can't match.
- **Reference treatment:** Pitchfork's regional charts; the FT's "Soundtrack" feature.
- **Note:** This is a *delight* surface — small, atmospheric, signature-y. Should be visible but not central.

#### Moat 7: School Athletics RSS — Official-Release Lane

**Capabilities:** Athletic-department RSS feeds (rolltide.com, fightingirish.com, etc.) — the official-statement source for every program.

- **Rating:** Hidden
- **Where it appears today:** Inside the campus / RSS ingest family; visible nowhere as a source-tier
- **Where it should appear:** As a green-dot Tier-A source in the Source-Trust Ribbon. As a primary-source attribution on Wire entries derived from official releases.
- **Concrete next step:** Add `OfficialReleaseChip` as a Source-Trust ribbon variant.

#### Moat 8: Bluesky firehose, GDELT, SeatGeek, prediction markets, beat-writer Substack, YouTube metadata

**Bluesky:** Real-time fan-conversation lane post-Twitter migration. Currently feeding `fan_intelligence.py` but visible nowhere.

**GDELT:** Real-time news volume signal. Visible nowhere.

**SeatGeek:** Ticket pricing as fan-demand proxy. Visible nowhere. This is one of the strongest *contrarian-signal* moats — when a fanbase is loud on Reddit but tickets aren't moving, the divergence itself is the story.

**Prediction markets:** Polymarket + Kalshi probability data per game. Currently in `ingest/sources/prediction_markets.py`. Visible nowhere.

**Beat-writer Substack:** Per-program Substack feeds tracked. Visible on the homepage Voices module (with "Aged Well %" treatment), but not surfaced on the team pages or wire rows where the beat-writer take is directly relevant.

**YouTube metadata:** Per-program YouTube channel signals — views, comments, sentiment on game-recap videos.

**Aggregate recommendation:** All six of these belong in the Source-Trust Ribbon (Move B). Adding them takes the strip from 4 chips to 12 — closer to a Bloomberg-terminal data-feed status row than a small attribution lineup. This is appropriate. Trust scales with source count.

#### Moat 9: Fanbase classification + Weekly mood + Cohort divergence (computed)

- **Rating:** Hidden outside `/hub/`
- **Backfill effect:** Phase 6 rebuilds `fanbase_mood_weekly` and `team_fanbase_cohort_week`. After phase 6, the data exists; the surfacing is still a structural problem.
- **Concrete next step:** Cohort-divergence atom (Move C). Below-hero fanbase-cohort chip strip per team. National mood ribbon on homepage.

#### Moat 10: Storyline threads (Active/Dormant editorial arcs)

- **Rating:** Underexposed
- **Where it appears today:** 8 thread titles on `/storylines/` index (no pills); right-rail on homepage (no pills); Live in `_fetch_storylines` in `fan_intelligence.py` line 1063 and on `storyline_threads` table (8 rows live)
- **Concrete next step:** ThreadPill atom with `--active|--dormant` variants. Chapter-density EKG per thread row on index. Active threads as cross-cuts on team pages.

#### Moat 11: Reaction stories (auto-triggered on cohort divergence)

- **Rating:** Hidden (the most-tragic surface/moat mismatch)
- **Where it appears today:** Three text-link headlines on `/reactions/`, dark page, no images
- **Concrete next step:** Magazine-card rebuild per Big Swing B3. The trigger logic in `reactions/triggers.py` produces auto-generated stories when cohorts diverge; the renderer emits prose. Rebuild against `docs/design-system/12-modules-intel.md` ChronicleCard pattern with cohort-divergence bar as cover art.

#### Moat 12: Signature stories per player

- **Rating:** Hidden · `[BACKFILL-RECOVERS]` partially for player season context data
- **Where it appears today:** `canon-entry__paragraph-wrap` section on individual Canon entries
- **Concrete next step:** Execute `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` — Accolade Lens, signature stories with cohort divergence on rankings.

#### Moat 13: Chronicle observation cards (anomaly / moment / flashpoint / echo / retroactive / player_arc)

- **Rating:** Adequate on profiled team pages · Hidden elsewhere
- **Concrete next step:** Lift Chronicle module into `common/atoms.py` and call from `editions/article_renderer.py`, `daily/renderer.py`, `_render_home_meta_row` in `reporting.py:13927`.
- **Backfill note:** `team_chronicle_observations` is currently 0 rows in the local DB. Whether this populates from the current backfill depends on whether the LLM Chronicle-generation step runs in the post-publish enrichment phase. **Flag for owner confirmation:** is the world-class-enrich workflow (referenced in CLAUDE.md "world-class enrichment workflow") in the auto-trigger sequence after `publish-site`?

#### Moat 14: Power ratings + Heisman model + Receipts

- **Rating:** Hidden (`/heisman/` shows 1 row; `games_predictive_claims` and `claim_outcomes` are referenced 0 times in `reporting.py`)
- **`[BACKFILL-RECOVERS]`** for the 2020–2025 model-run data populating predictive_claims; **STRUCTURAL** for the receipts UI itself
- **Concrete next step:** Build `ReceiptStrip` atom — claim, prediction, outcome, age. Wire into team-page hero, rankings movement column, Heisman row.

#### Moat 15: Canon lists with cohort splits

- **Rating:** Underexposed (cohort bar exists once as text)
- **Concrete next step:** Lift cohort-divergence atom (Move C); render at list-index level for every Canon list.

#### Moat 16: Hub computed evidence

- **Rating:** Adequate — `/hub/` is the strongest page on the site
- **Concrete next step:** Use `/hub/` as the visual reference and lift its module composition (28 charts, sentence-led headlines, magazine numbering) to Daily, Editions cover, and Reactions.

### Data Pipeline State (backfill-aware moat-table matrix)

From Investigator 1's DB-side audit; reframed against the in-flight backfill.

| Table | Rows (local DB) | Reader render paths | Backfill phase that populates | Structural verdict |
|---|---|---|---|---|
| `source_observations` | 120 | canon/cohorts.py:146, daily | (not in current backfill; live) | OK — surface as ribbon |
| `storyline_threads` | 8 | editions/homepage_renderer.py:91, storylines/renderer.py | (live; ingest separate) | OK — surface with pills |
| `conversation_documents` | 110 | fan_intelligence.py:1193 | (live) | OK |
| `team_pulse_cache` | 0 | daily/selector.py:164, mailbag/data.py:353 | Phase 6 (mood compute) | BACKFILL-RECOVERS |
| `team_savant_weekly` | 0 | team_pages/data.py:525 + 4 others | Phase 2 (CFBD history) | BACKFILL-RECOVERS |
| `team_chronicle_observations` | 0 | team_pages/data.py:496 + 4 others | **NOT IN BACKFILL** — needs world-class-enrich | STRUCTURAL — confirm with owner |
| `team_season_arc` | 0 | team_pages/data.py:584, historical_season_generator.py | **NOT IN BACKFILL** — needs LLM enrich | STRUCTURAL — confirm with owner |
| `player_week_conversation_features` | 0 | the_room_renderer.py:53 + 5 others | Phase 6 (fan intel) | BACKFILL-RECOVERS |
| `predictive_claims` | 0 | daily/selector.py:196 | Models skipped this run (`skip_models=true`) | STRUCTURAL until next model run |
| `fanbase_mood_weekly` | 0 | (ingest-only, NO render reads) | Phase 6 (mood compute) | DATA + STRUCTURAL (renderers not wired to read this) |
| `player_honors` | 0 | (audit.py only) | (not in current backfill) | DATA gap + STRUCTURAL (no render path) |
| `heisman_market_odds_weekly` | 0 | (models only) | (skipped this run) | DATA gap + STRUCTURAL |
| `team_brand_assets` | 0 | visual_assets.py:101, reporting.py:5187 | (not in current backfill — needs separate ingest) | STRUCTURAL — table is empty locally; team accent colors are coming from profile front-matter for the 17 profiled programs; remaining 647 unprofiled programs have no per-team accent today |

**Two structural confirmations needed from owner:**

1. Does the `publish-site` auto-trigger at end of run 25926317548 include the world-class-enrich LLM phase that writes `team_chronicle_observations` and `team_season_arc`? If yes, those flip to `BACKFILL-RECOVERS`. If no, structural ingest work is needed.
2. Is `team_brand_assets` intentionally empty (with the design relying on profile front-matter accent hex), or is there an ingest path that should be populating it for all 664 programs?

---

## Part 3 · The Pages

(Per-page verdicts from v1 retained; corrections/additions from v2 investigators folded in. Differences from v1 marked `[NEW]`.)

### Per-Page Verdicts (v2 updates)

| Page | Status | Rating | Key v2 update |
|---|---|---|---|
| `/` (Homepage) | Pass with reservations | 7/10 | `[NEW]` Add drop-cap on cover essay first ¶; replace generic Source Serif Pro body face with Charter; ship the cohort-divergence atom (Move C) on the Canon callout |
| `/rankings/` | Needs Work | 6/10 | `[NEW]` Filter chips have no `<label>` — WCAG 1.3.1 failure (Investigator 6). Add explicit labels. Replace movement arrow with signed integer ("+3" / "-2") per Wikipedia AP poll pattern. Pin top-5 with expanded treatment |
| `/teams/alabama.html` (profiled) | Pass | 7.5/10 | Pulse "Awaiting Signal" is **legitimate graceful degradation** per CLAUDE.md, not a bug. Drop from "broken" list in v1. Keep rivalry-trajectory `<img>` placeholder as a real concrete fix. Add `--bg-tint: rgba(var(--accent-rgb), 0.04)` to body for program-level emotional differentiation (Investigator 5) |
| `/teams/memphis.html` (legacy) | Needs Work | 4/10 | `[NEW]` CSS bundle hash drift (`89cc354d9863` vs deployed `f3924a06eced`) — investigate. Plumb `team_brand_assets.primary_color` into legacy template (when populated) |
| `/wire/` | Needs Work | 4/10 | `[NEW]` Wire `fetch_recent()` returns `source` metadata; renderer drops it (Investigator 2). Add source-chip column. Add IMPACT left-stripe color encoding. Filter chips above table. Mobile card transform via `data-wcfb-card-mobile` |
| `/daily/` | Needs Work | 3.5/10 | `[NEW]` Three text paragraphs in 2,507px — wrong font (Georgia not Source Serif), zero visual anchors. Enforce 4-section minimum in renderer: 1 chart, 1 featured-game callout, 1 mood-mover, 3 prose ¶ |
| `/mailbag/` | Needs Work | 4/10 | `[NEW]` Add pull-quote atom every 2nd answer; left-margin question-number treatment (NYT Spelling Bee pattern); topic-tag chip per question |
| `/reactions/` | Broken | 3/10 | `[NEW]` `reactions/renderer.py:264` `render_archive()` returns story cards with zero cohort visual — the `_sentiment_bar()` helper at line 126 is defined but never called. Lift to atom + use as cover art per Big Swing B3 |
| `/canon/` (list index) | Needs Work | 5/10 | `[NEW]` Lift the homepage-callout cohort-divergence bar to list-index level. Per-list cover treatment (headshot grid for the 100; coach portraits for the 25; goalpost for the 50). "How the lists work" should hero, not coda |
| `/canon/.../cj-stroud.html` (entry) | Pass with reservations | 5.5/10 | `[NEW]` `canon-entry__statline` should be 4-tile MetricTile cluster. Headshot. Add cohort-divergence bar (already shipped here as text — make it a bar). Drop-cap on opening paragraph |
| `/storylines/` | Needs Work | 5/10 | `[NEW]` `storylines/renderer.py` literally contains the string `"placeholder · Sprint 13"` for receipts (Investigator 2) — finish or remove. ThreadPill atom with active/dormant. Chapter-density EKG. Thread-anatomy timeline on detail pages |
| `/players/spotlight.html` | Broken | 2/10 | `[NEW]` `font-family: "Times New Roman"` — renderer never emits `<link>` for the CSS bundle. 769px stub. Critical fix |
| `/players/the-room.html` | Broken | 2/10 | `the_room_renderer.py` 255 LOC, stub. `[NEW]` Reads `player_week_conversation_features` (0 rows; `[BACKFILL-RECOVERS]` Phase 6). Even after data lands, the rendering structure is a stub — needs the world-class brief executed |
| `/heisman/` | Needs Work | 3/10 | `[NEW]` `[BACKFILL-RECOVERS]` for content (skipped `--skip-models`). Structural fix is still needed: off-season fallback = "How the model called 2025" calibration retrospective; `ReceiptStrip` atom |
| `/hub/` | Pass | 8.5/10 | `[NEW]` Font is "Source Serif 4" (not "Source Serif Pro" used elsewhere) — drift. Background `#f3eee4` doesn't match Wire/Mailbag/Editions `#f6f1e6` — drift. Both fixable in one PR by reading from `design_tokens.py` |
| `/compare/` | Needs Work | 4/10 | `[NEW]` The 80+ CSS classes (`wcfb-compare__pickers`, `__panes`, etc.) ship but data isn't wired in. Build invocation missing. Side-by-side mirrored percentile bars (Basketball-Reference Comparison Finder pattern: bold-the-winner) |
| `/conferences/` | Needs Work | 5/10 | `[NEW]` 61 flat cards, zero hierarchy. Power 4 cards should be larger, G5 smaller, FCS collapsed by default. League glyphs (custom SVG sprite). Comparative metric per league (SP+ aggregate, EPA-per-play, mood index) |
| `/editions/` | Needs Work | 4.5/10 | `[NEW]` Cover art generator: each issue gets a generated cover (Pillow renderer + `viz_templates/` directory wire-up). Page-turn metaphor on click (CSS perspective + rotateY at `--motion-delight`) |
| `/methodology/fan-intelligence.html` | Needs Work | 6/10 | `[NEW]` Highest-leverage moat-comms page; ships at 15,061px tall with zero charts and falls back to system-ui. Force-directed source-graph visualization. Live per-source freshness counters. Tier matrix as color-coded grid not text headings |
| `/history/heatmap/` | Broken | 2/10 | Times New Roman fallback, 769px stub, 1 SVG total for a page promising "twelve seasons. Every program. One image." Critical fix — render the actual heatmap from `team_season_arc` (currently 0 rows, see structural confirmation question above) |

### Per-Renderer Quality Matrix (NEW in v2)

From Investigator 2's code-level survey. PRODUCTION = shipping at high quality, ready to lift atoms from; PARTIAL = structure exists but key pieces missing; STUB = wireframe-level only.

| Renderer | LOC | CSS strategy | Components rendered | Inline SVG | Data tables read | Verdict |
|---|---|---|---|---|---|---|
| `team_pages/renderer.py` | 1,089 | Inlined (6 CSS files, 1,317 LOC) | Savant, Rivalry, Chronicle, Pulse, Era cards | No | 9 fetch_* | **PRODUCTION** |
| `hub_page.py` | 1,923 | Inlined palette tokens | Mood Index, Ticker, Hype/Reality, Taxonomy, Rivalry Matrix, Lexicon, Index cards | Yes (16 SVG) | 7 fetch_* | **PRODUCTION** |
| `editions/homepage_renderer.py` | 1,106 | Inlined paper palette | Hero, roman numerals, cover essay, sidebar threads, Voices module | No | 8+ fetch_* | **PRODUCTION** |
| `wire/renderer.py` | 453 | Inlined `_BASE_STYLE` 133 LOC | Table rows, impact chips (color-coded text only) | No | 2 fetch_* | **STUB** (110-row flat table, source metadata loaded and dropped) |
| `reactions/renderer.py` | 263 | Inlined `_CSS` 65 LOC | Card, sidebar cohort panels, sentiment bars (atom defined but unused in archive) | No | 3 fetch_* | **STUB** |
| `canon/renderer.py` | 448 | External `canon.css` 639 LOC | Top/mid entries, chips, mini-viz divergence bar (on entry pages only) | No | 2 fetch_* | **PARTIAL** |
| `mailbag/renderer.py` | 594 | Inlined `_BASE_STYLE` 159 LOC | Answer cards, Q&A pairs, source pills | No | 3 fetch_* | **STUB** |
| `daily/renderer.py` | 362 | External `cfb-index.*.css` | 3 paragraphs stacked | No | 1 fetch_* | **STUB** |
| `editions/article_renderer.py` | 237 | Inlined `_ARTICLE_CSS` 100+ LOC | Body prose, blockquotes, byline | No | 2 fetch_* | **PARTIAL** |
| `editions/archive_renderer.py` | 369 | Inlined shared palette | Article cards (4/index) | No | 2 fetch_* | **PARTIAL** |
| `storylines/renderer.py` | 607 | Inlined dark palette | Thread headings, receipts (placeholder Sprint 13), follower-count stub | No | 2 fetch_* | **STUB** |
| `conferences_pulse/renderer.py` | 217 | Inlined paper palette | 61 flat conference cards | No | 1 fetch_* | **STUB** |
| `provenance/methodology_page.py` | 418 | Inlined | Tier A/B/C/D text headings | No | N/A | **STUB** (promised diagram, ships text) |
| `team_pages/the_room_renderer.py` | 255 | Inlined dark palette | Player directory table, Heisman year rows | No | 2 fetch_* | **STUB** (font fallback) |

**Distribution:** 3 PRODUCTION / 3 PARTIAL / 8 STUB. Eight stub renderers represent the bulk of the site's surface area. Each is 200–600 LOC — the rebuilds aren't massive, they're scoped.

**Five code-level findings from Investigator 2 (folded into recommendations below):**

1. **Reactions and Wire load source/sentiment data and discard it.** `reactions/renderer.py:264` calls `fetch_cohort_splits()` but never invokes the `_sentiment_bar()` helper at line 126. Wire's `fetch_recent()` returns full `source` column metadata but the template emits only date/program/action/why/impact.
2. **CSS inlining is inconsistent across "production" pages.** team_pages inlines (3 files, 1,317 LOC duplicated × ~150 pages). Hub inlines a palette. Editions homepage inlines paper palette but Editions article inlines a *different* paper palette with a different hex.
3. **18 dead `_render_history_*` and `_render_player_*` functions in `reporting.py`** (lines 17367–18532) are never invoked. Either there's a missing orchestrator that bridges `reporting.py` to `team_pages/`, or the code is genuinely dead. Confirm.
4. **`hub_page.py` exports `render_team_archetype_module()` (per docstring) for reuse, but `team_pages/` re-implements an archetype pill instead of importing.** Same module, two implementations.
5. **Every renderer that inlines CSS re-invents the token dictionary.** Wire (`#c9a24a` gold), Mailbag (same), Hub (`#E0A300` gold), Reactions (`#f4c95d` gold), team_pages (`#c5b358` gold), wcfb-enhancements (`#c9a24a`). **Five different golds.** No shared source. The design-system spec at `docs/design-system/00-tokens.md` is never imported by any renderer.

---

## Part 4 · The Systems

### Typography (NEW)

The site has five font families running simultaneously with no governing theory. The deeper problem (Investigator 5) isn't drift — it's that two incompatible editorial registers (Source Serif Pro for editorial, Inter for data) are being mixed page-to-page with no rule for when to use each.

**Current state:**

| Section | Computed font | Note |
|---|---|---|
| Homepage, Wire, Mailbag, Editions | Source Serif Pro → Georgia fallback | Editorial register |
| `/hub/` | Source Serif 4 → Georgia | **Different typeface from Source Serif Pro** despite identical name root. Different spacing metrics, different weight |
| Profiled team pages | Inter Display + Inter | Data register |
| Canon, Storylines, the_room | Inter | Data register but missing Inter Display |
| Reactions | system-ui | No font loaded |
| Daily | Georgia | No Source Serif loaded |
| `/players/spotlight.html`, `/history/heatmap/` | **Times New Roman** | Browser default — no font loaded at all |

**Investigator 5's recommendation: Migrate the editorial serif from Source Serif Pro to Charter.**

Source Serif Pro is a clean editorial workhorse but it was originally designed for long-form government and academic documents — it reads *scholarly*, not *athletic*. Charter (designed by Matthew Carter for low-resolution screens) is metrically denser, sharper, with more authority. Free under SIL OFL. It's what The Atlantic and many editorial outlets actually use.

**Alternative**: Libre Baskerville is the next-best option (free, OFL, metrically close to Times New Roman but optically corrected for screens).

**Type scale critique:** The clamp scale in `team_pages/assets/tokens.css` is well-built but midpoint-compressed. `--fs-headline-sm: 22px` and `--fs-headline: 30px` are too close; body sizes `--fs-body: 16px` and `--fs-body-lg: 18px` collapse to the same visual band. Add one step at 26px between headline-sm and headline; widen body-lg to 20px for pull-quote usage.

**Caps treatment:** The uppercase-tracked-caps eyebrow pattern (`letter-spacing: 0.08em; text-transform: uppercase`) is correct and widely used by 538 and Athletic. The problem is inconsistent application — some module heads are uppercase Inter, others are `<h2>` at default casing. Lock: uppercase tracked caps for *all* eyebrows and section labels; title case for *all* narrative headlines; never mixed-case within a single module.

**Directives:**

1. Replace Source Serif Pro globally with Charter (or Libre Baskerville). Update `--font-serif` token. Replace "Source Serif 4" on Hub with the same Charter binary — eliminates drift.
2. Set `--font-body-editorial: Charter, "Source Serif", Georgia, serif` and use for *all* sustained prose (Mailbag answers, Daily paragraphs, Canon entry text, Wire "why it matters" cells).
3. Reserve Inter for UI labels, metric tiles, eyebrow text, and nav only — never as the body face for prose.
4. Expand the clamp scale to 9 stops with a 26px headline-sm step. Add 20px body-lg.
5. Lock uppercase-tracked-caps to all eyebrows. Run a sweep to find `text-transform: uppercase` mismatches across renderers.
6. Audit headings hierarchy globally (Investigator 6 found h1 → h2 → h3 → h2 → h3 chaos on team+program pages).

### Color Psychology + College-Football-Specific Palette (NEW)

The `team_pages/assets/tokens.css` semantic mapping — navy=analytical, coral=emotional, amber=heritage, gray=structural, green=positive, red=crisis — is competent fintech product-design thinking. It's the *wrong* emotional vocabulary for college football.

College football's emotional palette is **iron-gray stadium concrete, oversaturated grass green, band brass, late-afternoon amber light cutting through stadium shadows, the muted burgundy of laundered scarlet, the stark white of number plates.** The emotional arc runs from pregame anxiety (charcoal + muted yellow) to the white-hot of a go-ahead score (full saturated team color) to the Sunday-morning postmortem (depleted grays and quiet blues).

What the current palette gets wrong:

- `--tone-coral: #d95e7c` is fashion-forward pink. At home on a lifestyle app. Appears nowhere in stadium culture.
- `--tone-navy: #3570b5` is generically "finance app blue," not CFB-specific.
- No brown, no deep crimson, no field-green, no concrete — the actual colors of the physical experience are absent.

**Proposed replacements:**

| Current | Issue | Replacement | Why |
|---|---|---|---|
| `--tone-coral: #d95e7c` | Fashion pink | `--tone-burntorange: #c4622d` | Tennessee-vs-Bama emotional weight; culturally loaded |
| `--belief-bullish: #3ea073` (teal-green) | Too clinical | `--tone-grass: #3a7d35` | Saturday field green |
| `--tone-amber: #d9a55e` | Too muted | `--tone-brass: #c98a1a` | True trophy-and-tradition brass |
| `--tone-red: #c04a4a` | UI standard | `--tone-crimson: #9e1b32` (deep) + `--tone-alert: #d93025` (bright, reserved for MAJOR-impact only) | Crimson is for narrative weight; alert is for IMPACT chip |
| `--fg-muted: #8a90a1` (cool gray) | Digital | `--fg-concrete: #8a8c88` (warm gray with slight green undertone) | Stadium concrete |
| Paper backgrounds `#f6f1e6` | Strongest decision on the site | Protect; converge Hub `#f3eee4` → `#f6f1e6` | Aged-parchment archival |

**Directives:**

1. Replace `--tone-coral` with `--tone-burntorange`. Retain coral as a legacy alias for one release; remove after migration.
2. Add `--tone-grass` as the ambient-positive token; retire `--belief-bullish`.
3. Deepen `--tone-red` → `--tone-crimson` for crisis narrative; introduce `--tone-alert` for MAJOR-impact-only chip use.
4. Converge all paper backgrounds to `--paper: #f6f1e6` (canonical). Daily's `#f8f6f0` and Hub's `#f3eee4` are drift.
5. Add `--bg-tint: rgba(var(--accent-rgb), 0.04)` to profiled team page body element — sourced from program primary color, decomposed to RGB. Single CSS property; dramatic emotional differentiation between Alabama (crimson tint) and UConn (navy tint).

### Information Density Targets (NEW)

The site oscillates between text-wall (Mailbag at 6,601px Q&A, Wire at 9,533px / 110 rows) and empty shell (Reactions at 937px, Players at 769px, Heisman at 1 row). Per-surface targets:

| Surface | Current density | Target | Action |
|---|---|---|---|
| Wire | 110 rows at ~86px each, no filter | Dense triage: 3-col, 36px rows, sticky filter rail, 25-row pagination | Big Swing — see Top 5 #7 |
| Hub | 28 charts over 9,671px — correct | Maintain; do not compress. Lift modules to other pages | Reference only |
| Daily | 2,507px / 3 prose paragraphs / 0 anchors | Min 4 sections: 1 chart + 1 featured game + 1 mood-mover + 3 prose ¶ | Enforce in renderer |
| Mailbag | 6,601px Q&A — prose density correct, visual density wrong | Q-number left margin, pull-quote every 2nd answer, topic chip per question | Atom adds |
| Team pages (profiled) | Desktop correct; mobile stacks awkwardly | Reduce inter-module gap from `--sp-10: 80px` → `--sp-7: 32px` desktop, 24px mobile | One CSS change |
| Conferences | 61 uniform cards | Hierarchical: P4 large, G5 medium, FCS collapsed | Card-variant rework |
| Rankings | Flat table | Pinned top-5 with expanded treatment, standard rows below | Tier-row variant |

**Directive: Cut all inter-module spacing from `--sp-9 / --sp-10` (56px / 80px) to `--sp-7` (32px) on desktop, 24px on mobile.** The Athletic's team pages use 32–40px section gaps. At 80px CFB Index reads as disconnected modules rather than a unified team narrative.

### Editorial Voice via Design (NEW)

This is where the gap to The Athletic is most visible and most fixable. The site's editorial *copy* is strong ("Michigan's belief is at a decade low" is an Athletic-tier sentence). The *typographic apparatus* supporting that voice is absent.

**Missing atoms (all <10 lines of CSS each):**

- **Pull-quote.** Zero exist on any surface. Mailbag has multiple pull-worthy answers. Daily has opinion prose. Spec:

  ```css
  .pull-quote {
    font-family: var(--font-serif);
    font-size: 1.5em;
    font-style: italic;
    color: var(--fg-primary);
    border-left: 4px solid var(--accent-primary);
    padding-left: 1.5rem;
    margin: var(--sp-6) 0;
  }
  ```

- **Drop cap.** Homepage cover essay opens body prose with no drop cap. Every premium outlet (Atlantic, Athletic, NYT Mag) uses one. Spec:

  ```css
  .body-lead::first-letter {
    float: left;
    font-family: var(--font-serif);
    font-size: 3.5em;
    line-height: 0.9;
    padding-right: 0.1em;
    color: var(--accent-primary);
  }
  ```

- **Sidebar callouts / marginalia.** Mailbag and Canon entries have supporting data buried in prose. Lift to `<aside class="marginalia">` at `margin-right: -240px; width: 220px` on wide screens, collapsing inline at tablet. This is **the single move** that makes the product *feel* like The Athletic vs a blog.

- **Body-copy width cap.** Currently uncontrolled — paragraph text reflows to 120ch on wide monitors. Add `max-width: 65ch` to all `.body-copy`, `.mailbag-answer`, `.daily-prose`, `.canon-entry__paragraph-wrap`.

- **Truncation hygiene.** Reactions truncates mid-word ("And the Fanbase Didn't React the W"). Use 2-line clamp with `text-overflow: ellipsis`; never truncate within a word.

- **Decorative dividers.** The roman-numeral homepage section numbering is the best editorial design decision on the site. Lift to a global section-break atom (thin 1px rule with roman numeral centered inline, New Yorker pattern).

### Program-Level Differentiation (NEW)

Alabama, Notre Dame, and Ohio State team pages currently differ from Akron only via `--accent-primary` injected at body. Necessary but emotionally thin. Four mechanisms (from Olympic.com team landing pages, NBA team pages, Premier League clubs) for program-level emotional differentiation:

1. **Texture / overlay.** Add `--bg-tint: rgba(var(--accent-rgb), 0.04)` to the `<body>` of profiled programs. For Alabama, a barely-visible crimson tint at `rgba(158, 27, 50, 0.04)` changes the entire emotional read of the dark surface without affecting readability.
2. **Hero photography treatment.** Currently no images. ESPN's team landing uses a saturated stadium photograph with team-color gradient overlay. Even one licensed `--hero-bg: url(...)` per profiled program separates blue-bloods from directionals at first glance.
3. **Program personality typographic classes.** Map 4 personality variants:
   - `.program--blue-blood` — Alabama, Ohio State, Notre Dame, Michigan, Georgia, USC, Texas → `font-weight: 900; letter-spacing: -0.04em` (compressed, powerful, confident)
   - `.program--contender` — Penn State, Oregon, Tennessee, Oklahoma → `font-weight: 800; letter-spacing: -0.02em`
   - `.program--regional` — Vanderbilt, UConn, Iowa State, etc. → `font-weight: 700; letter-spacing: 0`
   - `.program--rebuild` — programs in tier 6+ → `font-weight: 500; letter-spacing: 0` (still proving)
4. **Heritage trophy shelf.** Alabama's current heritage strip is a flat text line: "Founded 1892 · Titles · Conf titles · Heismans · CFP · Bowls · Stadium · Legacy." For a school with 18 national titles, this should be a scrolling trophy shelf — small gold icons per title, each clickable to the relevant era. For Vandy or UConn, the strip's relative emptiness conveys the program's actual status without explicit ranking.

### Motion & Interaction Design (NEW)

`tokens.css` defines four motion durations (`--motion-reveal: 240ms`, `--motion-state: 180ms`, `--motion-data: 420ms`, `--motion-delight: 800ms`) with `prefers-reduced-motion` override. Grep shows `--motion-reveal` is referenced only in `tier-toggle:hover` and `filter-chip:hover` — the two least-interesting interactions on the site. `--motion-data` and `--motion-delight` appear to be unused.

**What should ship:**

1. **Chart-on-scroll reveal.** Every inline SVG chart (28 on Hub, every Savant percentile bar, every sparkline) animates from zero when entering the viewport. `IntersectionObserver` + `@keyframes barGrow` triggered by toggling `.is-visible`. Staggered delay (50ms × index). 30 lines JS + 10 lines CSS. **Single most emotionally-impactful interaction available.**
2. **Hover lifts** on team cards, reaction cards, Wire rows. Replace `transition: all` (performance anti-pattern, forces layout) with explicit `transform, box-shadow, border-color`. `transform: translateY(-2px); box-shadow: var(--elev-raised)` at `--motion-state: 180ms`.
3. **Sticky read-progress indicator** on Wire (9,533px) and Methodology (15,061px). 3px progress bar at top of viewport, `position: fixed; width: calc(scrollY / documentHeight * 100%)`. Minimum-viable positional cue.
4. **Page-turn metaphor for Editions.** CSS `perspective + rotateY` transition on clicking an Editions archive card — 800ms at `--motion-delight`. Front face: cover. Back face: article preview. Directly references the print-newspaper metaphor the editorial system is building toward.
5. **Sortable column highlights.** Wire and Rankings tables show no feedback on active sort column. Active column header gets `background: var(--bg-card-raised); box-shadow: inset 0 -2px 0 var(--accent-primary)` — Bloomberg terminal pattern.

**Critical a11y note (Investigator 6):** `prefers-reduced-motion` reduces only 1 transition block. **15 other declarations fire even with reduced-motion on** (lines 2886, 3273, 3338, etc. of main bundle). Move all `--motion-*` durations into the reduced-motion override block.

### Icon Strategy (NEW)

**Recommendation: Phosphor Icons** as the primary family. ~9,000 icons, six weights (Thin → Duotone), MIT-licensed, ships as `@phosphor-icons/web` (SSR-friendly raw SVG — what `reporting.py` needs since no React runtime).

Why Phosphor over Lucide / Tabler / Material Symbols:

- **Lucide** is more popular but precisely *because* it's everywhere — every AI-scaffolded site uses it, so it costs differentiation.
- **Tabler** is sharper for pure dashboards but reads sterile / SaaS-like.
- **Phosphor's** slightly humanist curves match a newsroom register (closer to Source Serif than to fintech dashboard).
- Phosphor's chart/data set rivals Tabler: `ChartLineUp`, `TrendUp`, `Pulse`, `Waveform`, `ChartScatter`, `ChartDonut`, `Funnel`, `Sigma`. Use Regular for nav, Bold for KPIs, Duotone for Chronicle-card glyphs, Fill for active states.

**Bespoke glyph commission — 12 glyphs, 1 illustrator-week, $1.5–3k:**

1. Accolade tier (4): `accolade.heisman` (laurel + W), `accolade.all-american` (shield + star burst), `accolade.cfp` (bracket-bar), `accolade.nfl-pipeline` (arrow exiting laurel). Filled gold/duotone, slightly heavier than Phosphor Regular.
2. Aspiration rungs (4): `rung.achievable` (single rising bar), `rung.stretch` (two bars + chevron), `rung.dream` (mountain peak + star), `rung.locked` (padlock atop dim mountain). Monotonically increasing visual mass.
3. Chronicle card types (6): `chronicle.anomaly` (sparkline with outlier dot), `chronicle.moment` (timestamped pin), `chronicle.flashpoint` (radiating star), `chronicle.echo` (concentric arcs), `chronicle.retroactive` (clock with reverse arrow), `chronicle.player-arc` (rising curve with portrait silhouette). Duotone, two-tone token-driven.
4. Impact tiers (2): `impact.major` (filled triangle, larger), `impact.minor` (outlined triangle). `impact.moves-conference` = Phosphor `ArrowsLeftRight` recolored — don't commission.

**Do NOT commission** (use existing solutions):

- Cohort marks: Phosphor `ChartBar` (stat-folks), `Smiley` (casuals), `Fire` (die-hards), `Moon` (dormant).
- Position glyphs: letterforms in a circle (`<span class="pos pos-qb">QB</span>`). Custom position icons are a trap — they all become helmet silhouettes. Letter chips are how ESPN, PFF, Pro Football Reference do it.

**Source-platform mark licensing:**

| Platform | Mark allowed? | Recommendation |
|---|---|---|
| Reddit | Yes (Simple Icons CC0) | Simple Icons `reddit`. No recoloring of snoo. |
| Bluesky | Yes | Simple Icons `bluesky`. Safe. |
| Wikipedia | Yes (CC-BY-SA wordmark) | Simple Icons `wikipedia`. Safe. |
| SeatGeek | Yes (public brand kit) | Simple Icons `seatgeek`. Safe. |
| ESPN | **No** (trademark + ad-standards restrict third-party use) | Text label only: `<span class="source-chip source-chip--text">ESPN</span>` |
| 247Sports | **No** (CBS Sports trademark, no public kit) | Text label only |
| On3 | **No** (no public kit) | Text label only |
| SB Nation | **No** (Vox Media trademark) | Text label only, or Phosphor `Megaphone` + label |
| Locked On | Confirm with owner | Default to text label until confirmed |
| Spotify | Yes for podcasts (with attribution) | Simple Icons `spotify` |

**Ship pattern:** `<SourceChip variant="reddit" />` emits *either* the Simple Icons SVG (allowlist: reddit, bluesky, wikipedia, seatgeek, spotify) *or* a typographic chip for trademark-restricted set. Single API surface; never puts you in a position where ESPN's legal team has a complaint.

### Font-Loading Recipe (NEW — drop-in code)

Three pages currently fall back to Times New Roman or system-ui because no `@font-face` is loaded. Investigator 4's recipe for a Vercel static site with no React runtime:

**Directory layout:**

```
output/site/assets/fonts/
  charter-var.woff2            # Charter (or Libre Baskerville) variable, latin subset
  inter-var.woff2              # Inter variable
  jetbrains-mono-var.woff2     # JetBrains Mono
output/site/assets/fonts.css   # @font-face + size-adjust fallback metrics
vercel.json                    # immutable cache headers for /assets/fonts/*
```

**`fonts.css`:**

```css
@font-face {
  font-family: "Charter";
  font-style: normal;
  font-weight: 400 800;
  font-display: optional;
  src: url("/assets/fonts/charter-var.woff2") format("woff2-variations");
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+2000-206F, U+2122, U+2212;
}
@font-face {
  font-family: "Charter Fallback";
  src: local("Georgia");
  size-adjust: 102%;
  ascent-override: 92%;
  descent-override: 24%;
  line-gap-override: 0%;
}
/* repeat blocks for Inter (Arial fallback) and JetBrains Mono (Menlo fallback) */

:root {
  --font-serif: "Charter", "Charter Fallback", Georgia, serif;
  --font-sans: "Inter", "Inter Fallback", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", "JetBrains Fallback", ui-monospace, monospace;
}
```

**In every HTML `<head>` (three pages currently missing this):**

```html
<link rel="preload" href="/assets/fonts/charter-var.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/inter-var.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/fonts.css">
```

**`vercel.json`:**

```json
{ "headers": [ { "source": "/assets/fonts/(.*)",
  "headers": [ { "key": "Cache-Control",
                 "value": "public, max-age=31536000, immutable" } ] } ] }
```

**Pipeline:** `npm i @fontsource-variable/charter @fontsource-variable/inter @fontsource-variable/jetbrains-mono`, then copy `latin.woff2` from each package into `output/site/assets/fonts/` in the build script. Don't preload JetBrains Mono — it's only used in code blocks.

**Audit fix:** Grep `reporting.py` and every renderer for `<head>` emit sites. Ensure every page goes through a single `_render_head_chrome()` helper that emits the preload + stylesheet trio. The three Times New Roman pages bypassed this — fix the bypass.

### Accessibility (WCAG 2.1 AA) (NEW)

Investigator 6's audit. Site is compliant on landmarks, nav, skip-links. Fails on contrast, form labeling, touch targets, and reduced-motion coverage.

**Critical findings:**

| Page type | Issue | WCAG | File | Line |
|---|---|---|---|---|
| All editions (`/`, Wire, Mailbag, Editions, Daily) | **Contrast failure**: `#c9a24a` (gold) on `#f6f1e6` (paper) = **3.2:1** (needs 4.5:1) | 2.1 AA | `editions/{archive,article,homepage}_renderer.py` | 50, 29, 394 |
| Rankings | Filter/toggle chips missing `<label>` (use aria-label) | 1.3.1 | `output/site/rankings/index.html` | 474, 484, 491 |
| Team pages | Savant card uses `aria-pressed` on `role=tablist` (should be `role=tab` + `aria-selected`) | 1.3.1 | `output/site/teams/alabama.html` | 1940 |
| All interactive | `.nav-toggle` = 8px padding (26–30px hit area, fails 44×44 target) | 2.5.5 | `output/site/assets/cfb-index.f3924a06eced.css` | 343–351 |
| All pages | `prefers-reduced-motion` honored but **incomplete** (15 motion declarations still fire) | 2.3.3 | `output/site/assets/cfb-index.f3924a06eced.css` | 2581 |
| Team pages | Inline journey SVG missing `role="img"` + complete `aria-labelledby` | 1.1.1 | `output/site/teams/abilene-christian.html` | 188 |
| Rankings | Power-Resume chart missing detailed text description | 1.1.1 | rankings | 282 |
| Rankings | Aria-label overused on pure-CSS divs (15+ instances should be `<fieldset>` with `<legend>`) | 1.3.1 | rankings | 264, 271, 282 |

**Top 10 a11y fixes by impact:**

1. **Replace `#c9a24a` on `#f6f1e6`.** Options: shift accent to `#996c00` (5.8:1 on paper) OR shift bg to `#fafafa` with `#c9a24a` (4.9:1). Affects 3 editions renderers and the entire shipping bundle's gold use.
2. **Move all `--motion-*` declarations into `prefers-reduced-motion: reduce` block.** Currently 15 transitions fire even with reduce on.
3. **Expand touch targets:** `.nav-toggle` padding 8px → 10px 12px (gets 44×44). `.savant-card__chip` explicit `min-height: 44px`. Bottom-nav chips already at `min-height: 44px` — verify.
4. **Replace `role=tablist + aria-pressed`** on Savant peer toggle with `role=tablist + role=tab + aria-selected`.
5. **Add explicit `<label>` to board-control inputs** on Rankings (currently using placeholder/title).
6. **Add `<desc>` to inline SVG charts** (journey chart, Savant bars, Pulse trajectory). Title + aria-labelledby alone is insufficient for complex graphics.
7. **Audit heading hierarchy** across all pages. Team archetype module (line 146) uses `<h3>` inside section with `<h2>` ancestor and no `<h1>` context inside `.team-shell` — observed h1→h2→h3→h2→h3 chaos on team+program pages.
8. **Consolidate redundant skip-links** on team pages (line 23 second skip-link is duplicate).
9. **Test `:focus-visible` ring at 2px solid `#FFB800`** on dark hero sections — may be sub-3:1 against `#0b0d12`. Consider 3px width.
10. **Replace overused aria-label divs with semantic `<fieldset>` + `<legend>`** on Rankings filter groups.

### Performance (NEW)

Investigator 6's measurements:

| Metric | Value | Note |
|---|---|---|
| Main CSS bundle | 5,842 lines / ~180 KB | Single shared bundle |
| Inline CSS per team page | **2,164 lines** (6 stylesheets inlined) | Duplicated across ~150 team + history pages |
| Total inline duplication | **~300 KB across 150 pages** | Wasted transfer; no cache reuse |
| Remote CSS @import | 1 (fonts.googleapis.com) | Render-blocking, ~18 KB |
| Total team-art assets | **77 MB** | 1,306 PNG files (664 teams × 2 PNGs), ~59 KB/team |
| `@font-face` declarations | 3 families in main bundle, **0 in editions renderers** | Silent fallback risk |
| Dead-CSS risk | <15% (sample of 20 random classes = 20/20 used) | Acceptable |

**Top 5 perf wins:**

1. **Externalize team-page inline CSS.** Currently `team_pages/renderer.py:294-298` inlines `tokens.css + styles.css + savant_card.css + rivalry_card.css + season_arc_card.css + historical_season.css` (2,164 lines) into every page. For 150 profiled team + historical pages, ~300 KB of duplicated CSS shipped on every request. Move to a shared `/assets/team-page.css` bundle. **Win: ~300 KB total transfer reduction + cache reuse + faster builds.**
2. **Optimize team-art PNGs to WebP.** 77 MB PNG → ~25 MB WebP at equivalent quality. Use `<picture>` for PNG fallback. **Win: ~150–200 KB per team-page hero load.**
3. **Replace Google Fonts `@import`** with self-hosted WOFF2 (recipe above). **Win: eliminate 18 KB render-blocking request + ~100 ms FCP improvement on 4G.**
4. **Merge `savant_card.css + rivalry_card.css + season_arc_card.css + historical_season.css`** into single `card-modules.css`. **Win: ~15 KB + 1 less parse compile cost.**
5. **Lazy-load** team OG-card images on archive/index pages (`loading="lazy"`). **Win: ~50 KB per archive page.**

---

## Part 5 · The References

Concrete competitive references with URLs. From Investigator 3. For each category, 2–3 references with: URL · component name · visual description · "what we steal."

### Team Page Hero

- **ESPN College Football — Alabama** · https://www.espn.com/college-football/team/_/id/333/alabama-crimson-tide · *Crimson identity band, "1st in SEC" standing pill, horizontal tab nav (Home/Schedule/Stats/Roster/Tickets), opponent-logo chip rail with vs/@ glyphs and network badges. Color saturates only the top band; rest is white-on-light for scannability.* **Steal:** identity band + standing chip + opponent-chip rail as one continuous unit, not three stacked cards.
- **ESPN 2025 College Football Rebrand** · https://www.behance.net/gallery/233649937/2025-ESPN-COLLEGE-FOOTBALL-REBRAND · *Two-year, 60-person Creative Studio rebuild centered on helmet/glove macro photography. Hero treatments crop helmet at high contrast, drop the team mark as a foil-style monogram, chrome score/clock in fixed condensed-numeral lockup.* **Steal:** helmet-as-hero crop + monogram foil treatment instead of generic team-color washes.
- **On3 team hub** · https://www.on3.com/teams/alabama-crimson-tide/ · *Hero stacks team mark + record + AP rank + recruiting class rank chips in single row, then surfaces "Latest Buzz" ticker as first content block — recruiting/portal news takes priority over schedule.* **Steal:** rank-pill cluster (national / conf / recruiting / portal) as compact identity-band suffix.

### Rankings Table

- **CBS Sports AP Top 25** · https://www.cbssports.com/college-football/rankings/ap/ · *Flat, generously padded rows; large left-edge rank numeral, 40px team mark, team name bold, trend arrow adjacent to name, vote-points column, "next game" cell with opponent logo + date. Row separation by hairline only.* **Steal:** trend-arrow adjacency to name (not in separate column) + "next game" as rightmost preview cell.
- **Yahoo Sports CFB Rankings** · https://sports.yahoo.com/college-football/rankings/ · *Poll-Type selector pill row above the table (CFP / AP / Coaches) toggles in place. Previous-week rank shown as caption beneath current rank.* **Steal:** in-place poll-type toggle + prev-rank as "subscript" not its own column.
- **Sports-Reference + Wikipedia AP poll** · https://www.sports-reference.com/cfb/ ; https://en.wikipedia.org/wiki/AP_poll · *Reference-grade density: first-place votes in parens, total points, change vs. previous week as a signed integer (+3 / -2) rather than just arrow. Monospace digits, footnotes for "others receiving votes."* **Steal:** signed-integer movement + first-place vote count in parens — more honest than just an arrow glyph.

### The Wire (Transfer Portal)

- **On3 Football Transfer Portal Wire** · https://www.on3.com/transfer-portal/wire/football/ · *Top-of-page summary banner shows aggregate counts ("3,656 Entered / 2,752 Committed (75%) / 62 Withdrawn (1.70%)") as live metrics. Filter row stacks: year dropdown → sport pills → status pills (Status/Withdrawn/Committed/Signed/Enrolled) → position pills (QB/RB/WR/…). Each player row: thumbnail, position badge, name link, ht/wt/class, HS, On3 rating, NIL valuation (lock-icon on gated rows), status badge, prev-team and dest-team logos with arrow between.* **Steal:** aggregate-counter banner + prev→dest team logo pair with arrow as the single most-scannable row element.
- **247Sports Transfer Portal** · https://247sports.com/season/2025-football/transferportal/ · *Card grid (not row table) with star-rating badge top-left of each card, school color stripe as identity, "Last updated" timestamp on every card.* **Steal:** per-card freshness timestamp — every wire item gets "X hours ago," not just page header.
- **247Sports/Rivals news ticker** · https://247sports.com/college/transfer-portal/ · *Right-rail "Latest News" with bylined posts, each with tag chip (Commit / Visit / Decommit / Enters Portal). Source attribution is byline + outlet (e.g., "Steve Wiltfong, On3") — credibility = named beat reporter, not "sources say."* **Steal:** typed tag chips + named-reporter byline as the credibility unit.

### Comparison Page (Head-to-Head)

- **Stathead Versus Finder** · https://stathead.com/football/versus-finder.cgi · *Two stacked selector blocks over a single combined results table — not two parallel tables. H2H summary card at top, then game-by-game ledger.* **Steal:** combined ledger underneath all-time summary card — one source of truth.
- **Basketball-Reference Player Comparison Finder** · https://www.basketball-reference.com/tools/share.fcgi?id=tIYaY · *Side-by-side columns share center stat-name spine; better-of-pair cells get bold weight (no color — bold only). Toggle for Per-Game / Per-100 / Advanced.* **Steal:** bold-the-winner-per-row instead of color-coding; toggleable normalization (per game / per drive / per play).
- **Winsipedia** · https://www.winsipedia.com/compare · *Diverging horizontal bar treatment — each metric is one bar with midline as parity; team-color fills extend left/right from center.* **Steal:** diverging center-anchored bars for "which side is better" metrics.

### Player Canonical Entries

- **Pro Football Reference (Feb 2026 redesign)** · https://www.pro-football-reference.com/ · *In-page nav moved from horizontal hover-bar to click-driven vertical sidebar (Career Stats / Game Logs / Splits / Advanced / Combine / HOF Monitor). Player News module from approved-domain RSS allowlist.* **Steal:** vertical sticky anchor sidebar + curated outbound-news module (allowlisted RSS, not scrape).
- **The Athletic editorial-design portfolio** · https://www.behance.net/gallery/217631571/The-Athletic-Editorial-Design-Chapter-One · *Player feature heroes use cutout silhouettes against flat duotone backgrounds; display type wraps around the figure.* **Steal:** cutout-on-duotone hero per profiled player.
- **Sports Reference player pages** · *Every stat table gets share/embed link — pages become atomic citation units.* **Steal:** atomic embeddable tables.

### Editorial Cover Pages

- **NYT Magazine covers (Matt Willey era)** · https://mattwilley.co.uk/NYT-Covers · *Custom Cheltenham revival at extreme scale; hero is either single arresting photograph OR pure typographic treatment (no photo).* **Steal:** half your covers should be pure-typographic when story is conceptual — don't default to photo every time.
- **Bloomberg Businessweek** · https://commercialtype.com/custom/bloomberg_businessweek · *Type system: Neue Haas Grotesk + Druk (display, extreme widths/condensations) + Publico (longform body). Heroes chop and manipulate Neue Haas Grotesk as typographic illustration; rigid grid supports "layer of chaos on top."* **Steal:** two-typeface lockup with Druk-style wide/narrow display foil.
- **FT Big Read** · https://www.ft.com/big-read · *Single hero photo with hairline FT-pink rule above kicker, oversized serif headline, dek in sans below, "X min read" pill.* **Steal:** kicker rule + read-time pill as consistent editorial watermark.

### Fan-Sentiment Visualizations

- **FiveThirtyEight 2020 "ball swarm"** · https://fivethirtyeight.com/features/how-we-designed-the-look-of-our-2020-forecast/ (live site shut down March 2025 — archive only) · *100 dots = 100 simulated outcomes huddled on x-axis of margin; hover reveals the map for that simulation. Built to communicate uncertainty, not a single point estimate.* **Steal:** bee-swarm dot field instead of single probability line — every dot = one sim.
- **Polymarket** · https://polymarket.com/ · *Big percentage numerals; complementary outcomes shown as paired pills ([Yes 52% / No 48%]); volume in dollars ("$169M Vol") as confidence proxy.* **Steal:** pair-pill for binary sentiment + volume-as-confidence indicator.
- **NYT Upshot fan-chart treatments** · *Forecasts use central median line with translucent percentile bands (5/25/50/75/95) — band is the message, not centerline.* **Steal:** median + percentile-band ribbon for any "what happens next" chart.

### Source-Credibility / Freshness

- **Reuters article header** · any article on https://www.reuters.com/ · *Kicker tag → headline → byline with reporter location ("By X in Y") → "Updated X hours ago" adjacent to publish timestamp.* **Steal:** dual timestamp (published / updated) shown only when they differ — implicit honesty.
- **AP News** · https://apnews.com/ · *"AP" wordmark badge top of article (wire-service provenance), category tag, headline, byline with author photo thumbnails, explicit "Updated X:XX p.m. EDT" stamp. Corrections inline as editorial notes, not buried.* **Steal:** byline with author thumbnail + explicit timezone-stamped Updated line.
- **FT / Bloomberg freshness rails** · https://www.ft.com/ ; https://www.bloomberg.com/ · *FT uses pink hairline above any "Live" item; Bloomberg flashes yellow "Live" dot and relative-time "4m ago" auto-updating. Both keep absolute time on hover.* **Steal:** relative-time pill with absolute on hover; reserve a single accent color exclusively for liveness, never for branding.

---

## Part 6 · The Plan

### Global Quick Wins (v2 — sharpened)

| # | Fix | File / location | Effort |
|---|---|---|---|
| 1 | **Consolidate to one paper bg.** Today: `#f6f1e6` / `#f8f6f0` / `#fafafa` / `#f3eee4`. Pick `#f6f1e6` canonical paper, `#fafafa` data-surface light, retire others | All renderers — best done as part of `design_tokens.py` consolidation | 4h |
| 2 | **Consolidate to one dark bg.** Today: `#0b0d12` / `#0c0e10`. Pick `#0b0d12` | All renderers | 1h |
| 3 | **Replace "Source Serif Pro" with Charter globally** via `@font-face` recipe (Part 4) | New `assets/fonts.css`, every renderer's `<head>` emit | 1d |
| 4 | **Move every motion declaration into `prefers-reduced-motion: reduce` block.** Currently 15 fire with reduce on | Main bundle | 2h |
| 5 | **Replace emoji bottom-nav glyphs with Phosphor SVG sprite** | `tools/wcfb_enhancements/wcfb-enhancements.css` + new sprite | 1d |
| 6 | **Build hash audit script** that fails CI if a generated page references a CSS hash that doesn't match latest bundle. Memphis loads `89cc354d9863` but on-disk is `f3924a06eced` | New script in `tools/` | 4h |
| 7 | **Plumb `team_brand_assets.primary_color` to legacy renderers** so unprofiled teams have accent color | reporting.py legacy team renderer | 3h (after table populated) |
| 8 | **Add `data-wcfb-card-mobile` attribute to every shipping table.** Mobile transform CSS is built; opt-in is missing | wire/renderer.py, rankings template, conferences | 2h |
| 9 | **Audit headings hierarchy globally** — confirm no h1→h3 jumps; fix h2→h3→h2→h3 chaos on team pages | every renderer | 4h |
| 10 | **Replace `#c9a24a` accent everywhere** with `#996c00` (or shift paper to `#fafafa`) for WCAG AA contrast | Main bundle + all editions renderers | 4h |
| 11 | **Lift the cohort-divergence text label to an SVG bar atom** in `common/atoms.py` | new file | 1d |
| 12 | **Wire source-attribution chip column** into `wire/renderer.py` — `source` data already loaded, just not rendered | wire/renderer.py | 2h |
| 13 | **Call `_sentiment_bar()`** in `reactions/renderer.py:render_archive()` — helper defined at line 126, never invoked | reactions/renderer.py | 1h |
| 14 | **Remove "placeholder · Sprint 13"** receipts stub from `storylines/renderer.py` or implement | storylines/renderer.py | 2h–1d |
| 15 | **Externalize team-page inline CSS** to shared bundle — saves ~300KB across 150 pages | team_pages/renderer.py | 4h |

### Big Swings (v2)

(v1's 10 swings retained; v2 sharpens with references.)

| # | Name | Effort | Reference |
|---|---|---|---|
| B1 | **Persistent Source-Trust Ribbon** below every team-page hero + homepage cover | 3d | Reuters article header + Bloomberg data-feed status |
| B2 | **The Receipts Strip** — "model said X, here's what happened" on team-page hero + Wire rows + Heisman | 1wk | FiveThirtyEight calibration plots |
| B3 | **Reactions as Magazine Cards** — cohort-divergence bar as cover art per card | 1sp | The Athletic Series cards |
| B4 | **Storyline Anatomy View** — vertical timeline of chapters with weight + active/dormant | 1sp | NYT investigation timelines |
| B5 | **Compare Slam** — Savant percentile bars head-to-head, bold-the-winner | 1wk | Basketball-Reference Comparison Finder |
| B6 | **Heatmap of Heritage** — render `/history/heatmap/` against `team_season_arc` (subject to data confirmation) | 1wk | NYT 100 Years of Presidents |
| B7 | **Player Pages, world-class brief execution** per `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` | 1sp | Pro Football Reference Feb 2026 redesign |
| B8 | **Conference Pages with Identity** — per-league tonal palette + glyph + comparative metric chart | 1wk | — |
| B9 | **Editions Cover Generator** — generated cover image per issue via Pillow + viz_templates | 1sp | NYT Magazine covers, Bloomberg Businessweek |
| B10 | **Daily as a Dashboard** — top-3 mood movers, latest wire, storyline updates, Chronicle hero, freshness footer | 1wk | Bloomberg terminal home |

### Sprint-Sized Roadmap (NEW)

The full body of recommendations across v1 + v2 sequences into 5 sprints. Estimates assume one-developer-week per sprint sub-task; many tasks are parallelizable.

**Sprint 9.5 — Foundation (1 week)**

- Create `src/cfb_rankings/common/design_tokens.py` — single source for paper/ink/gold/accents/fonts/spacing
- Migrate every renderer to import from it (Wire, Mailbag, Reactions, Daily, Storylines, Editions article, Hub, team_pages)
- Add `@font-face` recipe (Charter + Inter + JetBrains Mono) via `output/site/assets/fonts.css`
- Externalize team-page inline CSS to `/assets/team-page.css`
- Build CSS-hash CI audit script
- Replace `#c9a24a` accent or shift paper bg (WCAG AA fix)
- Move all `--motion-*` declarations into `prefers-reduced-motion` block

**Sprint 10 — Atom Library + Quick Wins (1 week)**

- Create `src/cfb_rankings/common/atoms.py` — extract reusable components from team_pages/savant_card.py, rivalry_card.py, etc.
- Add `CohortDivergenceBar` atom (Move C)
- Add `SourceTrustRibbon` atom (Move B)
- Add `ReceiptStrip` atom
- Add pull-quote, drop-cap, marginalia, body-width-cap as global utility styles
- Wire source-attribution chip column into Wire
- Fix Reactions to actually call `_sentiment_bar()` in archive render
- Remove storylines "Sprint 13 placeholder" stub
- Replace bottom-nav emoji with Phosphor SVG sprite
- Build hamburger menu exposing full taxonomy on mobile

**Sprint 11 — Renderer Rebuilds (2 weeks)**

- Rebuild `reactions/renderer.py` to magazine-card pattern (Big Swing B3) using `CohortDivergenceBar` atom
- Rebuild `wire/renderer.py` to triage console (filters, IMPACT left-stripe, source chips, mobile card transform)
- Rebuild `daily/renderer.py` to dashboard pattern (Big Swing B10)
- Add `ThreadPill` + chapter-density EKG to `storylines/renderer.py`
- Fix `/players/spotlight.html`, `/players/the-room.html`, `/history/heatmap/` rendering pathologies
- Wire `Compare` to data + ship Savant mirror bars

**Sprint 12 — Per-Program Identity + Methodology (2 weeks)**

- Add `--bg-tint` per program to profiled team pages
- Add 4 program personality classes (`.program--blue-blood` etc.)
- Build heritage trophy shelf SVG icon row
- Replace rivalry-trajectory `<img>` placeholder with real SVG sparkline
- Broaden Pulse `mood_lookback_60d` to render sparkline during low-floor weeks
- Add freshness ribbon below team-page hero (Move B, full surface)
- Rewrite `/methodology/fan-intelligence.html` with force-directed source-graph viz + Tier matrix grid + live per-source freshness counters

**Sprint 13 — Editorial Polish + Visual Library (2 weeks)**

- Bespoke 12-glyph commission (accolade tier × 4, aspiration rungs × 4, chronicle card types × 6 — minus impact tier × 2)
- Editions cover generator with viz_templates
- Page-turn metaphor for Editions archive
- Chart-on-scroll reveal across every inline SVG
- Sticky read-progress indicator on Wire + Methodology + long Editions
- Sortable-column highlights on Wire + Rankings
- Convert team-art PNGs → WebP, ship `<picture>` fallback

**Total effort:** ~8 developer-weeks. **Bundled effect:** site moves from heterogeneous-quality (2/10 floor, 8.5/10 ceiling) to consistent 7+/10 across all surfaces. Identity moves (Source-Trust Ribbon, Cohort-Divergence Bar, Masthead typography) ship in the first three sprints.

---

## Part 7 · Appendices

### Token Drift Inventory (NEW)

**Five vocabularies, four shipping renderer files, one canonical spec doc, one in-flight reconciliation:**

| File | Status | Vocabulary |
|---|---|---|
| `docs/design-system/00-tokens.md` | Canonical spec (light-mode-first, 6 ramps × 7 stops) | `--color-navy-400`, `--color-text`, `--color-surface`, `--fs-body`, `--sp-4` |
| `docs/design-system/unified-design-tokens.md` | 2 days old, reconciliation attempt | `--bg-primary`, `--fg-primary`, `--accent-primary`, `--fs-base`, `--space-4` |
| `output/site/assets/cfb-index.f3924a06eced.css` | 5,842-line shipped main bundle | mixed; uses both `--color-*` and `--bg-*` |
| `src/cfb_rankings/team_pages/assets/tokens.css` | Shipped team-page tokens (dark-default, 429 lines) | `--bg-0`, `--fg-primary`, `--accent-primary`, `--fs-body`, `--sp-4`, `--pct-low/high` |
| `tools/wcfb_enhancements/wcfb-enhancements.css` | Site-wide enhancement layer, 556 lines | `--wcfb-accent`, `--wcfb-bg-card`, `--wcfb-fg-primary` (own prefix) |

**Hardcoded "gold" hex values found in shipping renderers:**

| Hex | Used in | Notes |
|---|---|---|
| `#c9a24a` | Wire `_BASE_STYLE`, Mailbag `_BASE_STYLE`, wcfb-enhancements `--wcfb-accent` | Most common, but **fails WCAG AA contrast on paper** |
| `#E0A300` | Hub palette | Different value, same role |
| `#f4c95d` | Reactions `_CSS` | Lightest, fails AA |
| `#c5b358` | team_pages/tokens.css `--accent-primary` | Default before per-team override |
| `#FFB800` | Main bundle focus-visible ring | Different value, different role |

**Recommendation (sharpened from v1):** Promote `team_pages/assets/tokens.css` to `output/site/assets/tokens.css` as canonical. Build `src/cfb_rankings/common/design_tokens.py` as the Python-side single source for all renderer-inlined CSS. Add CI test that fails if any module CSS file declares a non-token color hex.

### Font Fragmentation Inventory (NEW)

Five families observed:

| Family | Surfaces | Note |
|---|---|---|
| Source Serif Pro | Homepage, Wire, Mailbag, Editions | Editorial register |
| Source Serif 4 | Hub | **Different typeface** despite name root |
| Georgia | Daily | Drift (should be Source Serif) |
| Inter Display | Alabama team page | Display only |
| Inter | Memphis, Rankings, Canon, Storylines, Conferences, Heisman, the-room, Compare | UI register |
| system-ui | Reactions, Methodology | No font loaded |
| Times New Roman | `/players/spotlight.html`, `/history/heatmap/` | No font loaded, browser default |

### Navigation Fragmentation Inventory

| Surface | Links exposed | Glyphs |
|---|---|---|
| Homepage topbar (desktop) | Rankings, Teams, Players, Heisman, Programs, History, Editions, Wire, How It Works (9) | Text only |
| Memphis topbar (legacy) | Power Rankings, Teams, Players, Heisman, Vibe Shifts, Programs, History, NFL Pipeline, The Model, Analysis, Weekly Archive, Matchup Simulator, Compare Teams (13) | Text only |
| Mobile bottom nav | Home, Rank, Hub, Compare, About (5) | **Emoji**: 🏠📊💡⚖️📚 |

**Three different navigation taxonomies on one site.** Pick one canonical top-nav (8 items max), one canonical bottom-nav (5 most-used), align legacy renderer to canonical, replace emoji.

### Audit Evidence Table

| URL | Live h1 | Computed bg | Computed font | Charts | Imgs | Scroll px | Verdict |
|---|---|---|---|---|---|---|---|
| `/` | After the Bracket | #f6f1e6 | Source Serif Pro | 1+ SVG | 0 | 10597 | Pass |
| `/rankings/` | (filter UI) | #fafafa | Inter | 0 | 0 | n/a | Needs Work |
| `/teams/alabama.html` | Alabama | `#0b0d12` | Inter Display | 1 img placeholder + arc SVG | 1 logo | n/a | Pass |
| `/teams/memphis.html` | Memphis | #fafafa | Inter | 0 | 0 | n/a | Needs Work |
| `/wire/` | Every move. Every read. | #f6f1e6 | Source Serif Pro | 0 | 0 | 9533 | Needs Work |
| `/daily/` | (story h2s) | #f8f6f0 | Georgia | 0 | 0 | 2507 | Needs Work |
| `/mailbag/` | The Mailbag | #f6f1e6 | Source Serif Pro | 0 | 0 | 6601 | Needs Work |
| `/reactions/` | Reaction Stories | #0c0e10 | system-ui | 0 | 0 | 937 | Broken |
| `/canon/` | The lists that settle… | #0b0d12 | Inter | 0 | 0 | 1224 | Needs Work |
| `/canon/.../cj-stroud.html` | C.J. Stroud | dark | Inter | 0 | 0 | 1569 | Pass w/res |
| `/storylines/` | Storyline Threads | #0b0d12 | Inter | 0 | 0 | 1397 | Needs Work |
| `/players/spotlight.html` | Players — 2025 | transparent | **Times New Roman** | 0 | 0 | **769** | Broken |
| `/players/the-room.html` | (no h1) | #fafafa | Inter | 0 | 0 | **769** | Broken |
| `/heisman/` | (off-season) | #fafafa | Inter | 0 | 0 | 1569 | Needs Work |
| `/hub/` | Michigan's belief is at a decade low. | #f3eee4 | **Source Serif 4** | **28** | 0 | 9671 | **Pass — site standard-bearer** |
| `/compare/` | Compare two programs. | #f6f1e6 | Inter | 0 | 0 | 1030 | Needs Work |
| `/conferences/` | The sport gets more interesting… | #fafafa | Inter | 0 | 0 | 6806 | Needs Work |
| `/editions/` | Every issue. | #f6f1e6 | Source Serif Pro | 0 | 0 | 3395 | Needs Work |
| `/methodology/fan-intelligence.html` | Fan Intelligence — Methodology | transparent | **system-ui** | 0 | 0 | 15061 | Needs Work |
| `/history/heatmap/` | Twelve seasons. Every program. One image. | transparent | **Times New Roman** | 1 | 0 | **769** | Broken |

---

## Closing

The product has a 7-out-of-10 ceiling already shipped on two surfaces (Hub and profiled team pages). The data pipeline is genuinely unique — confirmed CFBD Tier 2 + Arctic Shift Reddit + Wikipedia signals + Locked On podcasts + campus newspapers + Spotify charts + school athletics RSS + Bluesky + GDELT + SeatGeek + prediction markets + beat-writer Substack + YouTube. The design-system specs are sophisticated and well-considered. The gap between what the codebase can produce and what the live site shows is the single biggest opportunity on the board.

Closing that gap doesn't require new data architecture — it requires:

1. One shared `design_tokens.py`
2. One shared `common/atoms.py`
3. The three identity moves: Masthead, Source-Trust Ribbon, Cohort-Divergence Bar
4. Eight stub renderers lifted to use the atoms

Estimated total effort to move the entire site to a uniform 7+/10: **5 sprints (~8 developer-weeks)**. The Top 5 fixes alone — most of which are atom-lifts from existing code — ship in Sprint 9.5 + Sprint 10 (2 weeks).

**The single highest-leverage move on the entire roadmap:** Move C — Cohort-Divergence Bar as the universal brand atom. It exists *as text* on the homepage Canon callout today. Rendered as a 200px horizontal SVG bar and placed on every Reaction card, every Wire row with divergence, every Canon entry, every team-page Pulse module, every Mailbag answer with cohort relevance, every Editions cover — it becomes the 538-probability-needle-of-college-football. It is the thesis of the product made into one piece of visual currency. **It does not exist as a rendered visual anywhere on the live site.**

Ship that one atom — and the product becomes recognizably itself.
