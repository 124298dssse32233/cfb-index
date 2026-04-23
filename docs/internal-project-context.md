# Internal Project Context

Last updated: April 22, 2026

## What this project is

This repo is the working codebase for a college football analytics site that aims to be the most interesting and best-looking all-level CFB site on the internet.

The product idea is not just "a rankings page." The site is meant to feel like a full selection-room / argument-room / research-room for college football:

- one unified football universe across `FBS`, `FCS`, `Division II`, and `Division III`
- a predictive model for "how strong is this team right now and what happens next?"
- a separate resume model for "what has this team actually earned so far?"
- team pages that explain rating movement week by week
- rich comparisons, matchup projections, conference views, archive views, and eventually playoff / map / roster / portal tools

Working brand concepts already used in the site:

- `CFB Atlas`
- `The CFB Index`

## Product north star

The site should combine what fans love about:

- ranking arguments
- playoff debates
- team identity and "who are we really?" discussions
- cross-level curiosity
- offseason roster and portal obsession
- historical context
- visually memorable dashboards and story-driven browsing

The goal is not just accuracy. The site should be:

- analytically serious
- visually distinctive
- fun to revisit
- useful for argument and exploration
- strong in both in-season and offseason modes

## Core product thesis

Most public college football analytics products stop at `FBS`, or at best at `DI`.

This site's biggest differentiator is that it treats NCAA football as one connected ecosystem, while still being honest about uncertainty. That means:

- no fake hard ceilings or floors by subdivision
- no pretending a top `DIII` team is automatically comparable to a playoff `FBS` team with the same confidence as two SEC teams
- cross-level comparisons should be published with connectivity / uncertainty awareness
- bridge games, opponent chains, and schedule graph structure matter

## Season identity rules

This project defines a football season by the year in which that competitive cycle begins.

Examples:

- the `2025 season` starts with preseason buildup and opening games in `2025`
- regular-season games in fall `2025` belong to `season_year = 2025`
- bowls, playoffs, and title games played in January or February `2026` still belong to `season_year = 2025`
- offseason changes in early `2026` belong to the `2026 season` buildup, not the final `2025` ranking set

Implementation rules:

- `season_year` is the canonical season key
- `game_date` still keeps the real calendar date
- `season_phase` distinguishes `preseason`, `regular season`, `conference championship`, `playoff`, `bowl`, and `final`
- front-end labels should usually say `2025 Season`, with optional helper text like `2025-26`

This rule is important and should not be casually changed.

## Data stack

### Primary football source

`CollegeFootballData Tier 2` is the primary analytics backbone.

Why:

- schedules
- game results
- team and player stats
- recruiting data
- advanced metrics
- opponent-adjusted metrics
- live scoreboard
- live play-by-play

This is the main source that should drive the actual football model.

### Secondary enrichment source

`TheSportsDB` is used as optional metadata / presentation enrichment.

Good use cases:

- logos and artwork
- alternate team metadata
- venue / badge / fanart polish

Bad use case:

- relying on it as the main all-level competition backbone

Observed limitation:

- in local exploration, SportsDB football coverage appeared much stronger for Division I than for the full all-level NCAA universe

### Local storage

Local development uses `SQLite`, not PostgreSQL.

Current local database file:

- `cfb_rankings.db`

This is intentional because it keeps the project beginner-friendly and easy to move.

## Current architecture

At a high level:

1. API data is ingested into the local SQLite database.
2. Weekly model runs create predictive and resume outputs.
3. A static site generator builds HTML pages into `output/site`.

For day-to-day publish work from already-loaded data, the simplest operator command is:

- `python manage.py build-published`
- `publish_site.ps1`
- `publish_site.bat`

That rebuilds both:

- `output/rankings.html`
- `output/site`

Important code locations:

- `manage.py`
- `src/cfb_rankings/cli.py`
- `src/cfb_rankings/reporting.py`
- `src/cfb_rankings/pipeline.py`
- `src/cfb_rankings/db.py`
- `src/cfb_rankings/config.py`
- `src/cfb_rankings/clients/`
- `src/cfb_rankings/ingest/`

Important supporting files:

- `README.md`
- `docs/cfbd-tier2-and-safe-operations.md`
- `docs/anthropic-second-brain-workflow.md`
- `research/cfb-data-schema-sqlite.sql`
- `research/model-math-spec.md`
- `research/power-resume-presentation-research-2026-04-21.md`
- `research/power-model-refined-spec.md`
- `research/competitor-audit-2026-04-20.md`
- `research/feature-gap-memo-2026-04-21.md`
- `research/sentiment-market-study-design-2026-04-21.md`
- `research/cfb-fan-delight-viz-brief-2026-04-21.md`
- `research/anthropic-second-brain-synthesis-2026-04-21.md`
- `research/conversation-intelligence-v1-data-plan-2026-04-21.md`
- `research/proprietary-fan-intelligence-ideation-2026-04-21.md`
- `research/fan-intelligence-flagship-roadmap-2026-04-21.md`
- `research/fanbase-mood-system-design-2026-04-21.md`
- `research/affection-hostility-leaderboards-2026-04-21.md`
- `research/frontend-design-benchmark-2026-04-21.md`
- `research/cfb-language-understanding-2026-04-21.md`
- `research/unique-concepts-hardening-2026-04-22.md`
- `research/unique-concepts-market-honesty-2026-04-22.md`
- `research/offseason-homepage-execution-2026-04-22.md`
- `research/offseason-fan-delight-deep-research-2026-04-22.md`
- `research/offseason-publishing-queue-and-build-order-2026-04-22.md`
- `output/anthropic-unique-concepts-hardening-review.md`
- `output/anthropic-offseason-fan-delight-review.md`
- `output/anthropic-offseason-viz-review.md`
- `output/anthropic-offseason-build-order-review.md`

Operational note:

- the current CFBD Tier 2 coverage, safe backfill guidance, and timeout recommendation now live in `docs/cfbd-tier2-and-safe-operations.md`
- current recommendation is to keep `REQUEST_TIMEOUT_SECONDS=60` as the default and to prefer background/logged runs for heavy ingest work instead of giant in-chat foreground jobs
- the safest everyday refresh shortcut is now `safe_refresh_site.ps1`, which logs runs and defaults to skipping the heaviest play-level ingest and Heisman pass unless explicitly re-enabled
- the historical game-level player-stat recovery path is intentionally `FBS-first` right now; `backfill-game-player-stats` and `scripts/backfill_game_player_stats_logged.ps1` default to `--classification fbs` so archive repair stays aligned with the current public site and does not silently spend calls on other subdivisions
- the main local integrity reports now live in:
  - `output/player-archive-audit.md`
  - `output/awards-archive-audit.md`
  - `output/data-coverage-audit.md`
  - `output/competition-integrity-audit.md`
  - `output/program-history-integrity-audit.md`
  - `output/history-load-status.md`
- `output/player-archive-audit.md` is now the clearest single backlog view for historical player completeness because it exposes missing seasons, assigns each year an archive-readiness status, and ranks recovery priorities instead of only listing raw table counts
- the ridge-solver path used by the weekly power/features model no longer depends on a working local NumPy install to function; it now has a sparse pure-Python fallback that restored `run-models` and `safe_run_models.ps1` to healthy runtimes on this machine after the vendored NumPy import path proved broken
- `scripts/safe_history_status.ps1` is now the safest quick health check for the historical archive because it regenerates `output/history-load-status.md` with a log file and surfaces both inferred season progress and whether the final audits / published artifacts actually exist on disk even when no resumable checkpoint file exists yet
- `scripts/safe_archive_audit.ps1` now generates `output/archive-readiness-audit.md`, which is the best single-file operator summary of local archive health because it rolls together publish footprint, audit artifact presence, season readiness, postseason player-stat continuity, and next recommended recovery actions
- `output/archive-readiness-audit.md` now also emits concrete recovery commands for the current archive state, including the safe dry-run path for `backfill_game_player_stats_logged.ps1`, so the report can be treated as an actionable runbook rather than only a diagnosis
- `write_archive_readiness_audit` now also writes `output/archive-readiness-audit.json`, giving automations a structured view of publish footprint, audit artifact status, season readiness, critical gaps, recommended next actions, and exact recovery commands without scraping markdown
- `scripts/safe_refresh_local_health.ps1` now runs the complete offline maintenance pass: it regenerates the local audit suite, refreshes `output/history-load-status.md` and `output/archive-readiness-audit.md`, checks built-site links, and writes `output/local-health-refresh.md` as the quickest human-readable summary of the current backend state
- `output/local-health-refresh.md` now includes a freshness section that compares the latest modeled weekly snapshot against the current published site and audit artifact timestamps, so it will explicitly call out when the site is lagging behind the database state
- the freshness comparison in `output/local-health-refresh.md` is now timezone-normalized, so it no longer produces false stale warnings when database timestamps are UTC and local file mtimes are rendered in local desktop time
- `refresh-local-health` now also writes `output/local-health-refresh.json`, a machine-readable sidecar with artifact timestamps, latest model snapshot metadata, freshness status, suggested publish actions, and site-link audit results so future automations do not need to scrape markdown
- `write_history_load_status` now also writes `output/history-load-status.json`, giving unattended checks structured access to inferred-vs-checkpoint mode, per-season stage flags, finish-step health, and local archive snapshot counts
- `write_data_coverage_audit` now also writes `output/data-coverage-audit.json`, so table-level historical coverage can be consumed by scripts without scraping markdown
- `write_player_archive_audit` now also writes `output/player-archive-audit.json`, exposing season coverage, readiness buckets, recovery priorities, gaps, and sampled missing games in a structured form
- `write_awards_archive_audit` now also writes `output/awards-archive-audit.json`, exposing per-season honors coverage and loaded award labels in a structured form
- `write_competition_integrity_audit` now also writes `output/competition-integrity-audit.json`, exposing season-continuity, duplicate/collision, identity-drift, placeholder-conference, level-transition, and latest-board integrity counts
- `write_program_history_integrity_audit` now also writes `output/program-history-integrity-audit.json`, exposing suspicious records, overlapping program identities, scoring anomalies, and per-level completed-game thresholds
- `refresh-local-health` now also writes `output/maintenance-bundle.json`, a single structured rollup that includes the local-health result and the parsed audit sidecars for automation-friendly backend triage
- `refresh-local-health` now also writes `output/maintenance-action-queue.md` and `output/maintenance-action-queue.json`, a prioritized operator queue derived from the structured audits so the next recovery task is explicit even if thread context is lost; command rows now include mode, network requirement, expected weight, and a safety read so heavy CFBD recovery jobs are not confused with light offline audits
- `scripts/safe_refresh_local_health.ps1` now prints the action-queue count and the top three maintenance actions after a successful run, keeping the beginner-friendly PowerShell path aligned with the machine-readable backend triage layer
- `python manage.py validate-maintenance` now writes `output/maintenance-validation.md` and `output/maintenance-validation.json`, validating the maintenance JSON layer itself and failing on broken-link reports, stale artifacts, malformed sidecars, missing command metadata, or open P0 actions
- `safe_publish_site.ps1` now provides the logged offline publish path for rebuilding `output/rankings.html` and `output/site` from current local database state and then immediately running a strict internal-link audit

Product strategy note:

- the most promising sentiment/market feature is not "can vibes beat Vegas"
- it is a `market + conversation intelligence` layer built around `Fan Pulse`, `National Mood`, `Rival Heat`, `Market Drift`, and `Model vs Market`
- the current study-design and fan-delight memos above should be treated as the default framing for that work
- the newest implementation plan says the first public launch should be `FBS-only`, `team-level`, and mostly weekly/editorial rather than trying to be a real-time social-listening product
- the current strongest product direction is even narrower and more opinionated: the site should lean into `fan intelligence`, `belief tracking`, `respect gap`, and `rival heat`, with a `Team Mood Card` as the clearest flagship surface
- `research/fan-intelligence-flagship-roadmap-2026-04-21.md` should be treated as the current default strategy memo for April-through-August product ideation
- `research/fanbase-mood-system-design-2026-04-21.md` now defines the clearest metric shape for the fan-intelligence layer: four core axes (`Belief Level`, `Reality Gap`, `Swing Factor`, `Cohesion`) plus comparison modules like `Respect Gap` and `Rival Heat`
- `research/affection-hostility-leaderboards-2026-04-21.md` now defines how to handle `most loved`, `most criticized`, `rival heat`, `national darlings / villains`, and later player/coach boards without collapsing everything into a misleading `most hated` label
- `research/frontend-design-benchmark-2026-04-21.md` is now the main internal memo for what currently makes the front-end feel less premium than ESPN / On3 / Sports Reference and what visual / interaction changes matter most next
- `research/cfb-language-understanding-2026-04-21.md` is now the main internal memo for handling memes, sarcasm, doomposting, rivalry bait, and confidence gating in the conversation-intelligence layer
- `research/unique-concepts-hardening-2026-04-22.md` adds outside-research support for `Shock Index`, `Loyalty Temperature`, `In-Group / Out-Group Split`, `Spillover Risk`, and the broader idea that surprise and intergroup language are stronger organizing principles than generic sentiment averages
- `research/unique-concepts-market-honesty-2026-04-22.md` now locks the sharper public concept stack: `Team Mood Card`, `Shock Index`, `Respect Gap`, `Fanbase Civil War Watch`, and `What Changed This Week`, while also making the product stance explicit that the market angle should stay descriptive and comparative rather than claim fragile `beat Vegas` alpha
- `research/offseason-homepage-execution-2026-04-22.md` now captures the live homepage stance for the current calendar window: month-aware offseason hero framing, a visible `Road To Kickoff` runway from `April` through `August`, an `Offseason Mood Board` empty-state that explains what should publish in the current month, and a surfaced `Fanbase Civil War Watch` card on the homepage
- `research/offseason-fan-delight-deep-research-2026-04-22.md` is now the strongest single memo for the `April 22 -> August kickoff` question because it combines current offseason dates, outside fan-engagement evidence, the spring-game / offseason-access shift, mainstream content patterns, Anthropic critique, and the actual repo/runtime limits into one prioritized module stack and visual strategy
- `research/offseason-publishing-queue-and-build-order-2026-04-22.md` is now the main execution memo for this offseason because it ties the current codebase to an exact weekly publishing queue from `April 22` to kickoff, identifies the honest first five modules, and makes the real prerequisite explicit: audience-source hardening before stronger public fan-intelligence claims
- `output/anthropic-unique-concepts-hardening-review.md` is the latest second-brain critique and should be treated as the current high-level prioritization pass for what becomes public signature product versus later-phase/internal tooling
- `output/anthropic-offseason-fan-delight-review.md` is the latest second-brain pass on which offseason modules fans would actually revisit and which directions are commodity traps
- `output/anthropic-offseason-viz-review.md` is the latest second-brain pass on which visual forms should package the offseason modules so they feel premium, mobile-friendly, and socially shareable rather than like generic dashboard widgets
- `output/anthropic-offseason-build-order-review.md` is the latest second-brain pass on module sequencing and publish cadence for the current repo state; use it as a pressure test, but note that one of its recommendations (`fix the static site builder first`) was already overtaken later in the session once a newer valid model snapshot was available and `build-site` completed successfully
- implementation reality check: `src/cfb_rankings/fan_intelligence.py` already computes the core `Team Mood Card` pieces such as `belief`, `reality_gap`, `respect_gap`, `swing`, `cohesion`, and `rival_heat`, but `Shock Index` and a stronger `What Changed This Week` explanation layer are still the clearest next product additions rather than already-finished live features
- implementation reality check for the collector: `src/cfb_rankings/storage.py` now correctly returns season aliases again, and `src/cfb_rankings/ingest/conversation.py` now deduplicates watchlist teams by using the latest available power row per team instead of accidentally joining across every saved week in a model run; these fixes materially improve the honesty of the next conversation-ingest iteration
- implementation reality check for verification: the new offseason helpers in `src/cfb_rankings/reporting.py` now also survive a full `python manage.py build-site` pass against the latest valid snapshot; a transient earlier mismatch came from a stale `model_runs.week` / `power_ratings_weekly.week` mismatch on an older latest snapshot, but the current latest build completed successfully and wrote the full static site
- the older `research/offseason-modules-recommendation-2026-04-21.md` is still useful background, but it is more analyst-style and should not override the newer proprietary-first fan-intelligence direction unless explicitly chosen

### Historical membership layer

Season-specific conference and level membership now belongs in `team_seasons`, not in `teams.current_conference_id`.

Why this matters:

- historical conference storytelling is wrong if it follows a school's current league backward in time
- conference pages can stay current-season oriented, but program-history pages need season-aware membership
- realignment eras, archived conference labels, and multi-season narrative cards should read from `team_seasons`

Practical rule:

- `teams.current_conference_id` is still useful as a current-identity fallback
- anything tied to a specific season should prefer `team_seasons`

Lightweight repair / refresh command:

- `python manage.py sync-team-seasons`
- `python manage.py sync-team-seasons --start-season 2021 --end-season 2025`

That command refreshes season-aware conference membership from CFBD game schedule payloads that match the locally loaded seasons, without rerunning the full model pipeline.

### Program-history integrity watchlist

### Historical archive watchlist

As of `April 22, 2026`, the player-archive audit shows two foundational historical gaps:

- `2017` currently exists only as an awards shell
- `2018` currently exists only as an awards shell

That means future history loading should not just chase missing player-game stats. The first missing-year recovery target is still:

- create baseline game/archive rows for `2017`
- then do the same for `2018`

Important related change:

- the manual honors importer in `src/cfb_rankings/ingest/honors.py` now auto-creates missing season shells and stub player rows when needed, so historical Heisman imports for older seasons do not silently disappear just because the player archive is still thin
- as a result, the structured Heisman winner/finalist layer now covers `2014-2025`
- the awards archive is still narrow, though: `output/awards-archive-audit.md` currently shows a `Heisman only` state for every season until broader award families are imported

The archive now has a dedicated historical sanity check:

- `python manage.py audit-program-history --output output/program-history-integrity-audit.md`

Current notable finding from that report:

- `Charlotte` has one overlapping duplicate internal team identity in `2014`
  - primary team id `132` with the expected multi-season history
  - duplicate team id `750` with a generic placeholder `FBS` conference row and one completed game

That class of issue is the main structural risk for doubled or otherwise misleading program-history records.

### Historical similarity engine

The team-page and front-page "reminiscence" cards are no longer supposed to be decorative placeholders.

Current implementation lives in:

- `src/cfb_rankings/reporting.py`

What it does:

- builds a cached archive of end-of-season team profiles from the latest loaded snapshot for each season
- uses real `power_ratings_weekly`, `resume_ratings_weekly`, and `opponent_adjusted_team_week` data
- compares the current team against prior loaded seasons only
- creates three separate nearest-neighbor comps:
  - `Offensive Reminiscence`
  - `Defensive Reminiscence`
  - `Overall Team Profile`

Important behavioral rules:

- the comp cards should never fall back to fake hard-coded seasons or seeded percentages
- the archive comparison should prefer real feature overlap and reject candidates that only share one usable field
- front-page expandable rows and full team pages should both read from the same computed similarity payload
- the comparison pool is intentionally cross-level, so a real `FCS`, `DII`, or `DIII` comp can surface if the profile actually matches

## What the two models mean

### Predictive model

Purpose:

- estimate current team strength
- support matchup projections
- answer "what would happen next?"

The predictive model should eventually lean heavily on:

- opponent-adjusted performance
- offense / defense / special teams components
- preseason priors
- roster strength
- recruiting / transfer / returning-production context
- recency without becoming overly noisy

### Resume model

Purpose:

- evaluate the quality of what a team has actually accomplished
- support ranking / committee-style debate
- answer "what has this team earned?"

The resume model should care more about:

- wins and losses
- opponent quality
- best wins
- absence / presence of bad losses
- schedule strength
- phase-aware context

### Relationship between them

The site intentionally keeps `Power` and `Resume` separate. That separation is a core product feature, not an accident.

Fans want to know:

- who is stronger?
- who is more deserving?
- where do those answers disagree?

That tension is one of the most important things on the site.

## Historical context rules

History is now a core product layer, not just an archive.

That means:

- previous seasons should be visible on the homepage, rankings surfaces, and team pages

### Current loaded archive span

As of the latest local refresh on `April 21, 2026`, the local game archive spans:

- `2020` through `2025`
- `6` distinct seasons loaded in `games`

That matters for:

- program-history pages
- similarity comps
- greatest / roughest season explorer modules
- conference-era and realignment storytelling

## Betting-data layer

The site now has a real CFBD betting-data layer instead of just product notes.

Current implementation status:

- game lines are stored in `game_lines`
- team pages compute market-aware summaries from closing lines
- team pages now show:
  - `ATS`
  - totals profile
  - wins versus market expectation
  - favorite / underdog ATS splits
  - a market game log
- conference pages now surface:
  - average ATS performance
  - average wins versus market
  - ATS leader
  - team board ATS context
- homepage now includes a `Market Reality Check` module

Important constraint:

- this is based on CFBD game-line history, not a live sportsbook trading system
- Tier 2 is excellent for historical and refreshable market context, but not for high-frequency real-time market movement products

Recommended next betting-data expansions:

- matchup-level `market vs model` disagreement cards
- expected wins by phase and by home / away split
- program-history `wins above market` timelines
- conference ATS pages that separate league-wide numbers from intra-conference double counting
- team pages should explain a program arc, not just one isolated year
- full `Programs` pages should exist as a separate explorer layer, not just as a side panel on season pages
- the predictive model should use prior seasons as preseason context, then let in-season evidence gradually take over
- prior-season carryover should be informed by roster continuity and talent inputs where our data stack supports it

Current product direction for history UX:

- `Programs` index page acts like a finder / explorer for all loaded programs
- each program page shows the long arc of the program, not just the current season
- conference-era cards and year-by-year tables use season-aware memberships
- current season pages should link back up to the full program page

Current source-of-truth memo for this area:

- `research/historical-context-and-preseason-priors-2026-04-21.md`

Current product stance:

- history should be first-class on the homepage, rankings page, team pages, and the dedicated history hub
- fans should be able to answer `best since`, `gap to peak`, `current vs program baseline`, `greatest seasons`, `roughest seasons`, and `best multi-year runs` quickly
- year-by-year tables should not just be raw stats; they should carry editorial context like `peak power`, `best resume`, `best finish`, `above standard`, or `down year`

Important caveat:

- do not present authoritative historical conference-era arcs until the data model includes season-specific conference membership
- the current historical team ledger is strong enough for program history, but conference realignment makes retro conference storytelling risky if it is inferred from current affiliations

## Conference ranking model

Conference strength should not be treated as a plain average of team ratings.

Current intended model:

- the primary conference sort should use a KenPom-style `RR50` measure
- `RR50` means the neutral-field rating a hypothetical team would need to go `.500` against a full round robin of the conference
- this is more robust than a simple average because one extreme bottom team does not distort the whole league as much
- the site should also expose a second metric for top-end quality, currently called `Upper Strength`
- very small affiliation groups should be lightly regressed toward their subdivision baseline so one-team or two-team groups do not hijack conference cards
- `Upper Strength` should weight the best teams in the league more heavily so we can distinguish:
  - the deepest conference
  - the hardest conference to navigate
  - the conference with the strongest title-caliber ceiling

The idea is:

- `RR50` answers the KenPom-like question
- `Upper Strength` answers the "how dangerous is the top of this league nationally?" question
- `Median Power` and similar middle-tier context help us avoid confusing a top-heavy conference with a deep one

## Current implemented site features

As of this update, the generated site includes:

- home page (now leads with a Fan Intelligence `Mood Board` block)
- full rankings page
- team pages (now lead with a flagship `Team Mood Card`)
- conference index and conference pages
- matchup studio (now framed as `Argument Theater` with Market vs Model vs Mood cards)
- dedicated history hub
- weekly archive index
- weekly snapshot pages
- compare page

## Fan intelligence data contract

As of the current build, the reporting layer ships a proper fan-intelligence data contract instead of just raw sentiment numbers.

Key pieces:

- `src/cfb_rankings/fan_intelligence.py` holds the axis computation: `Belief Level`, `Reality Gap`, `Swing Factor`, `Cohesion`, `Respect Gap`, `Rival Heat`, plus an archetype and confidence band.
- `fetch_team_mood_profile(db, team_id, season_year, week, context)` returns a stable-shape profile that always renders, even when no signal exists yet.
- `fetch_fan_intel_board(db, season_year, week, team_index)` returns homepage leaderboards: `vibe_shifts`, `respect_gap_leaders`, `respect_gap_doubters`, `rival_heat_leaders`, `main_characters`, `panicked_fanbases`, `polarized`.
- Reality Gap compares fan belief to the current `power_percentile`, never to text alone.
- Audience buckets (`fan`, `national`, `rival`) are kept strictly separate. Rival mockery never bleeds into Fan Pulse.
- Sarcasm-risky samples get their confidence downgraded via `_sarcasm_risk_from_row`; the worst readers get suppressed from headline surfaces entirely.
- `conversation_utils.CFB_MEME_PHRASES` is a hand-built CFB-specific lexicon for victory-lap, doompost, explicit-irony, rival-bait, and sarcastic-praise patterns.
- Public outputs prefer labeled bands (`Bullish`, `Hype Train`, `Civil War`, etc.) over precise decimals.
- As of April 22, 2026, the live conversation collector also supports a config-driven Reddit source plan via `python manage.py collect-reddit-plan --season <season> --week <week> --plan research/reddit-community-plan-v1.json`.
- That path now supports:
  - `national` collection from `r/CFB`
  - direct team-subreddit listing pulls for `fan` buckets
  - targeted in-community search for `rival` buckets
- `src/cfb_rankings/fan_intelligence.py` now falls back to the strongest available source row when `source_name='all'` has not been materialized yet, so real `reddit` rows can still render on team pages.

Publish gates:

- minimum `12` fan mentions before a team's Fan Pulse is published
- minimum `4` distinct authors before confidence is allowed to hit Medium
- minimum `40` mentions + `12` authors before confidence can hit High
- when rival share ≈ fan share *and* net sentiment is strongly positive, the sarcasm risk is raised and confidence is automatically downgraded

History-specific layers now implemented:

- homepage / rankings history cards for greatest seasons, strongest teams, rises, sustained programs, and two-year runs
- team-page historical snapshot cards with `best since`, `gap to peak`, percentile context, and baseline-vs-current framing
- year-by-year team tables with a `lens` column so users can immediately tell whether a season was a peak, best finish, best resume, or a down year
- history hub tables for closest-to-peak programs and best two-year runs
- history hub `History Explorer` table with search, level filter, conference filter, and sort modes across every loaded team-season

Current generated output lives in:

- `output/site/index.html`
- `output/site/history/index.html` now includes the searchable cross-season explorer, not just summary cards

## Current local archive snapshot

As of this update, the local modeled archive covers:

- `2021`
- `2022`
- `2023`
- `2024`
- `2025`

That five-season window is now strong enough to support real `best since`, `program baseline`, and `two-year run` storytelling on the live site.
- `output/site/history/index.html`
- `output/site/rankings/index.html`
- `output/site/archive/index.html`
- `output/site/conferences/index.html`
- `output/site/matchups/index.html`
- `output/site/compare/index.html`
- `output/site/teams/<team>.html`

### Current front-end product ideas already implemented

- home page "selection board" feel
- rankings board controls with search, level filter, conference filter, sort, and range jumps
- rankings page summary strip, debate starters, and visual context modules above the board
- expandable ranking rows
- side-by-side `Power` and `Resume`
- team identity visuals
- team-page placement context and nearest-neighbor compare shortcuts
- matchup projections
- history hub with:
  - best-by-level peaks
  - greatest / roughest loaded seasons
  - turnarounds, collapses, and dynasty tracking
  - season almanac cards
  - fan-facing preseason-prior explanation
- compare workflow with:
  - selector-based team-vs-team comparison
  - verdict cards
  - component battle bars
  - phase splits
  - shared opponents
  - quick-load debate presets
- weekly replay / archive experience

## Product themes that should stay true

- The site should feel editorial and intentional, not generic SaaS.
- The front end should feel like college football, not just "analytics software."
- The product should reward curiosity.
- Every major page should help the user answer a real question.
- The site should be as strong in arguments and exploration as it is in raw metrics.

## Current community-source research references

- `research/community-language-and-source-taxonomy-2026-04-22.md` is now the main memo for how CFB fans actually talk across Reddit and message boards, what source tiers we should trust for `fan` vs `national` vs `rival`, and what that means for offseason product design.
- `research/reddit-community-plan-v1.json` is the starter collection plan for the live Reddit source map.
- `research/cfb-only-reddit-filtering-2026-04-22.md` is the main memo for the latest `CFB only` filtering audit, including the remaining mixed-sport failure modes and the current v1 choices.
- `research/reddit-community-plan-cfb-safe-v2.json` is the safer current launch plan when we want a narrower but cleaner `CFB-only` Reddit slice without waiting on a full Anthropic ambiguity pass.
- `output/anthropic-community-source-taxonomy-review.md` is the latest Anthropic pressure test of the Reddit-first v1 scope and its honest limits.
- `output/anthropic-cfb-only-filtering-review.md` is the latest Anthropic recommendation on the `CFB-only` Reddit filtering problem; its bottom line is `Option B` long-term, but it also supports a narrower safe-source plan for v1 simplicity.

## Current known gaps

These are the biggest missing areas relative to the best public CFB products and fan habits:

- no true playoff room / simulator yet
- no imperialism / territory / map layer yet
- no full live game page with play-by-play, leverage swings, and win probability storytelling yet
- no rich offseason roster-strength / transfer portal / recruiting prior layer yet
- no historical query explorer yet
- no user personalization like favorites / watchlists / saved comparisons yet

## Recommended next roadmap

The current best next build order is:

1. `Playoff room`
   - bracket / simulator / path analysis
   - merit debate
   - postseason-aware season framing
2. `Imperialism / territory layer`
   - highly shareable
   - visually memorable
   - very native to college football fandom
3. `Roster / portal / recruiting priors`
   - offseason engagement
   - stronger preseason power model
4. `Live and postgame game pages`
   - play-by-play
   - win probability
   - drive summaries
   - turning-point storytelling
5. `Historical explorer`
   - program arcs
   - season comparisons
   - opponent / era / conference queries
6. `Personalization`
   - favorites
   - saved teams
   - saved compares
   - watchlists

## Research docs worth reading first

If someone inherits this repo and needs to recover context quickly, read these in order:

1. `README.md`
2. `docs/internal-project-context.md`
3. `docs/operations-runbook.md`
4. `research/feature-gap-memo-2026-04-21.md`
5. `research/competitor-audit-2026-04-20.md`
6. `research/model-math-spec.md`
7. `research/power-model-refined-spec.md`

## Recovery checklist if context is lost

If a future session starts cold, do this:

1. Read `README.md`.
2. Read this file.
3. Read `docs/operations-runbook.md`.
4. Open the current generated home page in `output/site/index.html`.
5. Review the latest research memo in `research/feature-gap-memo-2026-04-21.md`.
6. Rebuild the site with `python manage.py build-site` to confirm the generator still works.
7. Only rerun heavy ingestion or model commands if the underlying data actually changed.
8. Preserve the season identity rule that postseason games in January / February still belong to the season that started the previous fall.

## Current local archive snapshot

At the time of this update, the local modeled archive covers:

- `2022`
- `2023`
- `2024`
- `2025`

That four-season sample materially improves both the history UX and the preseason carryover logic.

Historical archive tooling added after that snapshot:

- `python manage.py backfill-player-context --start-season <start> --end-season <end>`
- `python manage.py backfill-game-player-stats --start-season <start> --end-season <end> --include-postseason`
- `python manage.py audit-data-coverage --output output/data-coverage-audit.md`
- `python manage.py audit-competition-integrity --output output/competition-integrity-audit.md`
- `python manage.py check-cfbd-connectivity --season <season>`
- `python manage.py history-load-status --start-season <start> --end-season <end> --output output/history-load-status.md`
- `powershell -ExecutionPolicy Bypass -File scripts\safe_history_status.ps1 -StartSeason <start> -EndSeason <end>`
- `python manage.py audit-archive-readiness --output output/archive-readiness-audit.md`
- `powershell -ExecutionPolicy Bypass -File scripts\safe_archive_audit.ps1`
- `python manage.py refresh-local-health --start-season <start> --end-season <end> --site-dir output/site --output output/local-health-refresh.md`
- `powershell -ExecutionPolicy Bypass -File scripts\safe_refresh_local_health.ps1 -StartSeason <start> -EndSeason <end>`
- `python manage.py repair-team-current-identity`
- `scripts/backfill_player_context_logged.ps1`
- `scripts/backfill_game_player_stats_logged.ps1`
- `scripts/load_history_2014_forward.ps1`
- `docs/heisman_honors_2014_2025.csv`

Those are the main recovery handles if a future session needs to resume the 2014-forward backfill without re-deriving the workflow.

## One-sentence summary

This repo is building a visually distinctive, analytically serious, all-level college football universe where `Power`, `Resume`, matchup projection, weekly replay, and team identity all live inside one coherent product.
