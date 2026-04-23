# Offseason Publishing Queue And Build Order

Research date: 2026-04-22

Companion files:

- `docs/internal-project-context.md`
- `research/offseason-fan-delight-deep-research-2026-04-22.md`
- `research/offseason-homepage-execution-2026-04-22.md`
- `research/unique-concepts-market-honesty-2026-04-22.md`
- `output/anthropic-offseason-build-order-review.md`

## Purpose

This memo turns the offseason research into:

- a concrete `April 22 -> kickoff` publishing queue
- a practical build order for the first public fan-intelligence modules
- an honest read of what the current codebase already does versus what still needs work

This is the execution memo to use if context is lost.

## Current code understanding

The key repo truth as of `April 22, 2026`:

## 1. The homepage is now offseason-aware

`src/cfb_rankings/reporting.py` now already supports:

- month-aware hero framing for `April` through `August`
- a `Road To Kickoff` runway
- an `Offseason Mood Board` warm-up state
- a surfaced `Fanbase Civil War Watch` homepage slot

Current verified output:

- `output/site/index.html` now renders:
  - `What fanbases are talking themselves into after spring`
  - `April Through August, On Purpose`
  - offseason module cards like `Spring Exit Survey` and `Hope Inventory`

## 2. Team Mood Card is real, but still mostly waiting on data

`src/cfb_rankings/fan_intelligence.py` already computes:

- `belief`
- `reality_gap`
- `respect_gap`
- `swing`
- `cohesion`
- `rival_heat`
- `storylines`
- homepage boards for:
  - `vibe_shifts`
  - `respect_gap_leaders`
  - `respect_gap_doubters`
  - `rival_heat_leaders`
  - `main_characters`
  - `panicked_fanbases`
  - `polarized`

`src/cfb_rankings/reporting.py` already renders:

- `Team Mood Card` on team pages
- `Top Storylines`
- homepage `Fanbase Civil War Watch`
- matchup-page `Argument Theater`

Current verified output:

- team pages such as `output/site/teams/indiana.html` render the full mood-card shell, but currently show `Awaiting Signal` because the live conversation sample is still too thin and still only national-bucket

## 3. The Reddit collector is still v1, but it is now slightly healthier

The conversation pipeline is:

- `seed-team-aliases`
- `collect-reddit-watchlist`
- `build-conversation-features`

Two important live-code fixes were made in this session:

- `src/cfb_rankings/storage.py`
  - fixed `team_aliases_for_season()` so it actually returns aliases instead of silently returning an empty list
- `src/cfb_rankings/ingest/conversation.py`
  - fixed `_build_watchlist()` so it no longer duplicates teams by joining against every power week in the latest model run

Why those fixes matter:

- aliases are foundational for collection quality
- duplicated watchlist rows waste scarce collection passes and muddy source coverage

## 4. The live conversation dataset is still thin

After the post-fix validation pass:

- `12` conversation documents
- `14` conversation targets
- `3` weekly feature rows
- `9` storyline rows
- current weekly aggregate coverage is still:
  - `2025`, `week 1`, `national` bucket only

Important implication:

- the current UI is good enough to ship honest shells and empty states
- it is **not** yet strong enough to present the full public fan/rival/national story at scale

## 5. The static site builder currently works again

`python manage.py build-site` now completes successfully against the latest snapshot and built:

- `668` team pages
- `685` program pages
- `15939` player pages

That means the public rendering path is usable for the next iteration.

## First principle for the build order

The public module order should follow this rule:

- harden what already exists before inventing new metrics

That means:

- do not start with `Shock Index`
- start with the existing mood system and the collection quality it depends on

## Required prerequisite before public fan-intelligence claims

Before the first strong public push, the pipeline needs better audience coverage.

Current limitation:

- the collector can tag an `audience_bucket`
- but the live data is still only `national`
- there is no current per-team subreddit manifest or per-team source routing layer for clean `fan` and `rival` collection

So the real prerequisite is:

## Stage 0. Audience-source hardening

Goal:

- get repeatable `fan`, `national`, and later `rival` collection for a constrained FBS set

Recommended first scope:

- `25-30` FBS teams
- biggest fanbases
- contenders
- volatile brands
- rivalry-rich programs

This is the true first step even though it is not a public module.

## Concrete build order for the first 5 modules

## 1. Team Mood Card

Status:

- already implemented in code
- already rendered on team pages

What still needs work:

- stronger collection coverage for `fan` and `national`
- visual polish and screenshot-quality presentation
- maybe lighter copy tuning for empty states

Why this is first:

- it is the flagship
- it is the clearest shareable product object
- it reuses the most existing code

Code already involved:

- `src/cfb_rankings/fan_intelligence.py`
- `src/cfb_rankings/reporting.py`

Build target:

- top `25-30` FBS teams first

Ship condition:

- enough sample to publish at least a meaningful subset of teams
- confidence gating intact

## 2. Fanbase Civil War Watch

Status:

- already computed as `polarized`
- already surfaced in the homepage layout

What still needs work:

- real `fan` bucket coverage
- stronger labeling and ordering polish
- editorial copy that explains split camps cleanly

Why this is second:

- it is already one of the strongest proprietary differentiators
- fans immediately understand it
- it does not require new math, only better inputs and packaging

Code already involved:

- `src/cfb_rankings/fan_intelligence.py`
- `src/cfb_rankings/reporting.py`

Ship condition:

- enough teams with real `fan` rows to make the board feel alive

## 3. Respect Gap Census

Status:

- already computed
- already partially surfaced in homepage boards

What still needs work:

- better `fan` plus `national` coverage
- a stronger visual form than list rows
- dumbbell-chart or split-bar rendering

Why this is third:

- it is already mathematically present
- it is one of the most arguable fan-facing outputs
- it is perfect for May and July

Code already involved:

- `src/cfb_rankings/fan_intelligence.py`
- `src/cfb_rankings/reporting.py`

New work:

- add a more premium visual renderer for the homepage / section page

## 4. What Changed Right Now

Status:

- concept present
- data partial
- not yet properly surfaced on the homepage

What still needs work:

- aggregate homepage explanation layer from `conversation_storylines`
- better storyline quality
- small editorial summary rail

Why this is fourth:

- it is the best revisitation loop
- it turns data into readable football stories
- it keeps the site from feeling robotic

Code already involved:

- `conversation_storylines` table
- `src/cfb_rankings/ingest/conversation.py`
- `src/cfb_rankings/fan_intelligence.py`
- `src/cfb_rankings/reporting.py`

New work:

- homepage / team-page explainer rail
- storyline aggregation and ranking logic

## 5. Shock Index

Status:

- research-validated
- not implemented yet

What still needs work:

- event-level surprise framing
- delta logic grounded in real football events
- annotation layer so the board is explainable

Why this is fifth instead of first:

- it is the best next new metric
- but it needs more new backend logic than the first four
- the product gets more value by first hardening the existing belief system

Best offseason use cases:

- portal shocks
- coach / coordinator news
- QB battle movement
- media-day quote spikes
- preseason ranking jumps

## What should wait until later

- `Living Rent Free`
  - wait until `rival` sourcing is cleaner
- `Rival Heat Matrix`
  - same reason
- player-level mood tracking
  - too fragile for now
- real-time game-window products
  - wrong cadence and timing risk

## Exact publishing queue: April 22 through kickoff

The right cadence is:

- one marquee homepage package each week
- one recurring board refresh
- one or two lighter team-level updates when the data supports them

Do not try to publish too many separate product objects every week.

## Week Of April 22

Primary package:

- `Spring Exit Survey`

Supporting modules:

- `Who Gained Belief After Spring`
- `QB Panic Meter`
- `Hope Inventory`

Execution note:

- homepage framing is already done
- this week should focus on collection hardening and first honest shells

## Week Of April 29

Primary package:

- first public `Team Mood Card` push for a constrained FBS set

Supporting modules:

- `Fanbase Civil War Watch`
- `Respect Gap` preview rows

Execution note:

- only ship teams that clear the publish gate
- let everyone else stay in `Awaiting Signal`

## Week Of May 6

Primary package:

- `Respect Gap Census`

Supporting modules:

- `Programs Outsiders Keep Getting Wrong`
- `Most Fragile Contenders`

## Week Of May 13

Primary package:

- `Fanbase Civil War Watch`

Supporting modules:

- team-level `Mood Card` refresh
- first `What Changed Right Now` experiments

## Week Of May 20

Primary package:

- `Hope Inventory`

Supporting modules:

- `Who Gained Belief`
- `Who Got More Nervous`

## Week Of May 27

Primary package:

- `What Changed Right Now`

Supporting modules:

- refreshed `Respect Gap`
- refreshed `Civil War Watch`

## Week Of June 3

Primary package:

- first public `Shock Index`

Supporting modules:

- `Summer Vibe Stalls`
- `Storyline Gravity`

## Week Of June 10

Primary package:

- `Storyline Gravity`

Supporting modules:

- `What Fans Are Lying To Themselves About`

## Week Of June 17

Primary package:

- `Recruiting Euphoria / Paranoia`

Important rule:

- cover recruiting as fan reaction and identity narrative
- not as recruitnik service content

## Week Of June 24

Primary package:

- `Summer Vibe Stalls`

Supporting modules:

- `Hope Inventory` refresh
- `Shock Index` refresh

## Week Of July 1

Primary package:

- `Pre-Media-Days Belief Check`

Supporting modules:

- `Respect Gap Census`
- `Civil War Watch`

## Week Of July 8

Primary package:

- `Big 12 Media Days Reality Check`

Supporting modules:

- `Quote Energy vs Fan Mood`

## Week Of July 15

Primary package:

- `ACC Media Days Reality Check`

## Week Of July 22

Primary package:

- `SEC Media Days Reality Check`

## Week Of July 29

Primary package:

- `Big Ten Media Days Reality Check`

Supporting modules for July overall:

- `Who Is Selling Hope Best`
- `Conference Respect Gap Boards`
- `Main Character Right Now`

## Week Of August 5

Primary package:

- `Camp Panic Meter`

Supporting modules:

- `Team Mood Card` refresh
- `Shock Index` refresh

## Week Of August 12

Primary package:

- `Preseason Truth Detector`

Supporting modules:

- `Delusion Meter`
- `Model vs Mood vs Market` quadrant

## Week Of August 19

Primary package:

- `AP Poll vs Fan Pulse`

Supporting modules:

- `Respect Gap` refresh
- `What Changed Right Now`

## Week Of August 26

Primary package:

- `Week 0 Vibe Board`

Supporting modules:

- `Camp Panic Meter` final refresh
- `Shock Index` final pre-kickoff board

## Weekly operating loop

For the current stack, the weekly working loop should look like:

1. refresh aliases
2. run constrained conversation collection
3. build conversation features
4. inspect counts and storyline quality
5. rebuild the static site
6. only publish the modules that cleared the gate

Current operator commands:

```bash
python manage.py seed-team-aliases --season 2025
python manage.py collect-reddit-watchlist --season 2025 --week 1 --limit-teams 25 --search-limit 10
python manage.py build-conversation-features --season 2025 --week 1
python manage.py build-site
```

Recommended near-term improvement:

- add a manifest-driven collection command or workflow for:
  - `fan`
  - `national`
  - later `rival`

because the current collector still uses:

- one subreddit per run
- one audience bucket tag per run

That is workable for v1 experiments, but not yet ideal for repeatable public publication.

## Practical next coding priorities

1. keep the alias and watchlist fixes
2. add repeatable `fan` and `national` collection for top FBS teams
3. harden `Team Mood Card`
4. harden `Fanbase Civil War Watch`
5. add a stronger `Respect Gap` visual form
6. add a `What Changed Right Now` storyline rail
7. add `Shock Index`

## Strategic takeaway

The honest first public build order is:

1. audience-source hardening
2. `Team Mood Card`
3. `Fanbase Civil War Watch`
4. `Respect Gap Census`
5. `What Changed Right Now`
6. `Shock Index`

The honest first public publishing rhythm is:

- weekly
- editorial
- FBS-first
- fan-intelligence-first

That is the best match between:

- what fans will actually revisit
- what the repo already supports
- what a solo operator can realistically maintain from `April 22, 2026` to kickoff
