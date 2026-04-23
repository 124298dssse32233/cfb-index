# Conversation Intelligence V1 Data Plan

Research date: 2026-04-21

## Purpose

This memo turns the sentiment / market strategy work into an actual build plan for this repo.

It answers:

- what we should collect
- how often we should collect it
- what tables should exist
- what the first publishable features should be
- what is realistic under the current stack and budget

## Bottom line

The right v1 is:

- `FBS-only` for the first public launch
- mostly `batch`, not real-time
- built around `team-level` conversation intelligence
- joined to `CFBD` open/close lines and existing model outputs

The right product is:

- `Fan Pulse`
- `National Mood`
- `Rival Heat`
- `Market vs Mood`
- `Biggest Vibe Shifts`

The right technical shape is:

1. store normalized raw conversation documents
2. resolve them to teams / players / games
3. score them at the target level
4. aggregate to daily, weekly, and game-window features
5. keep raw snapshots for future event studies and debugging

## What v1 should cover

### Coverage by level

Always on:

- `FBS` teams

Selective:

- `FCS` top 25, playoff field, rivalry spikes, and page-demand teams

Later:

- `FCS` top 25 and playoff field
- `DII`
- `DIII`

### Coverage by entity

V1:

- teams
- games

V1.5:

- featured players
- awards watchlists

Not v1:

- full sport-wide player coverage

## Source ownership

## 1. Reddit

Primary use:

- team fan sentiment
- rival sentiment
- long-form frustration / optimism
- weekly storyline extraction

Collection method:

- `Apify` actor runs with normalized dataset output

Why:

- best budget-adjusted fan discourse source
- richest rivalry and postgame text
- avoids direct Reddit API dependence

## 2. YouTube comments

Primary use:

- emotional postgame reaction
- highlight and press-conference reaction
- nationally visible player discourse

Collection method:

- official `YouTube Data API` first

Why:

- official
- cheap
- stable

Important implementation note:

- `commentThreads.list` does not always include all replies, so deeper reply pulls should use `comments.list` when needed

## 3. Bluesky

Primary use:

- open-public chatter
- analyst and media reaction
- national conversation outside Reddit

Collection method:

- direct `requests` to public Bluesky endpoints

Why:

- official public endpoint exists
- no scraper required for the basic use case

## 4. Search / headlines

Primary use:

- national narrative detection
- story discovery
- finding candidate articles and videos

Collection method:

- `Apify` Google Search actor

Why:

- headline discovery is more useful than full article scraping in v1

## 5. Betting context

Primary use:

- open / close market context for game studies

Collection method:

- current `CFBD Tier 2` line data
- future `game_line_snapshots` table for richer intraday studies

## 6. Prediction markets

Primary use:

- awards
- playoff futures
- headline event probabilities

Collection method:

- `Kalshi` public market endpoints
- `Polymarket` public Gamma / Data / CLOB reads

Why:

- these are realistic future-facing sources for probabilities
- they are more useful for futures and event markets than for pretending we own sportsbook-level pregame microstructure on day one

## Collection cadence

The budget does not break because of model inference.

The budget breaks because of collection scope and frequency.

### Recommended v1 cadence

Daily:

- one `morning` sweep for always-on watchlist teams
- one `evening` sweep for always-on watchlist teams

Game-week boosts:

- `72h pregame`
- `24h pregame`
- `12h pregame`
- `24h postgame`
- `72h postgame`

Event-driven:

- injury rumor spikes
- coaching changes
- poll-release reactions
- upset alerts
- playoff-committee reveals

### Source-specific cadence

Reddit:

- twice daily for always-on team watchlist
- boosted around featured games and event triggers

YouTube:

- no blanket crawl
- only pull comments for candidate videos tied to featured teams, featured games, or awards watchlists

Bluesky:

- once or twice daily for always-on watchlist
- boosted for featured games and story spikes

Prediction markets:

- every `4` hours for awards / futures watchlists
- more frequent only after the site proves the feature is worth it

## Watchlist strategy

The project should not collect the whole universe equally.

Use a `watchlist` mindset.

### Always-on watchlist

- all `FBS` teams
- Top 25 / playoff teams
- current week featured matchups

### Featured watchlist

- rivalry games
- ranked matchups
- teams with major movement in Power or Resume
- teams with unusual site or social interest

### Event-driven watchlist

- player injury chatter
- coach turmoil
- Heisman momentum
- transfer-portal spikes

## Audience bucketing rules

The product gets interesting when we separate viewpoints instead of averaging them.

### Buckets to support from day one

- `fan`
- `rival`
- `national`
- `media`
- `unknown`

### Practical heuristics

Fan:

- team subreddit
- official team channels
- explicitly team-affiliated communities

Rival:

- rival subreddit mentioning the team
- known rivalry keyword combinations

National:

- `r/CFB`
- broad search / headline results
- general Bluesky public search

Media:

- known beat-writer and analyst lists
- official network / publication accounts

Unknown:

- anything we cannot confidently place

## Entity resolution rules

### Team resolution

Use:

- canonical `teams`
- `team_source_ids`
- new `team_aliases`

Important examples:

- `Bama`
- `UGA`
- `tOSU`
- `Ole Miss`
- `State`

### Player resolution

Use:

- canonical `players`
- `player_source_ids`
- `roster_entries`
- new `player_aliases`

Practical rule:

- player-level features should only publish when the roster / team context is strong enough to disambiguate the name

## Core tables to add

The v1 schema should support four layers.

### Layer 1: Control and raw ingestion

- `conversation_collection_runs`
- `conversation_documents`

### Layer 2: Canonical mapping and scoring

- `team_aliases`
- `player_aliases`
- `conversation_document_targets`

### Layer 3: Aggregates for product and analysis

- `team_conversation_daily`
- `team_week_conversation_features`
- `team_game_conversation_features`
- `conversation_storylines`

### Layer 4: Future market microstructure

- `game_line_snapshots`
- `prediction_market_snapshots`

## Ruthless trim for launch

The schema can support more than the first public launch should try to ship.

### Essential for the first public launch

- `conversation_collection_runs`
- `conversation_documents`
- `team_aliases`
- `conversation_document_targets`
- `team_week_conversation_features`
- `team_game_conversation_features`
- `conversation_storylines`

### Helpful but not required on day one

- `player_aliases`
- `team_conversation_daily`

### Deliberately future-facing

- `game_line_snapshots`
- `prediction_market_snapshots`

Those future-facing tables are worth keeping in the schema now so later work does not require another redesign, but they should not block launch.

## What the first study dataset should look like

Primary study grain:

- `one row per game-team`

Built by joining:

- `games`
- `game_lines`
- `power_ratings_weekly`
- `resume_ratings_weekly`
- `team_game_conversation_features`
- `team_week_conversation_features`
- weather and advanced-game context where needed

### Key dependent variables

- `spread_move_home = spread_home_close - spread_home_open`
- `total_move = total_close - total_open`
- implied-probability changes when moneylines are available

### Key independent variables

- fan net sentiment
- rival net sentiment
- national net sentiment
- mention volume
- anger / fear / trust mix
- attention spikes
- sentiment disagreement between buckets

### Key controls

- current power gap
- resume gap
- home field
- weather
- ranking visibility
- rivalry indicator
- week / season effects

## Publishability rules

Do not publish a flashy number when the underlying sample is thin.

### Minimum quality rules

For team-level publishable outputs:

- at least `20` target-resolved documents in the window
- at least `5` distinct authors / accounts when available
- no more than `80%` of the sample from one single document thread or video

### Low-confidence warning rules

Flag low confidence when:

- sarcasm score is unusually high
- one source dominates the sample
- all data comes from one event spike
- the audience bucket is mostly `unknown`

## Best v1 product outputs

Homepage:

- `Biggest Vibe Shifts`
- `Market vs Mood Disagreements`
- `Most Panicked Fanbases`
- `Rival Heat Leaders`

Team page:

- `Fan Pulse`
- `National Mood`
- `Rival Heat`
- `What Changed This Week`
- `Key Storylines`

Matchup page:

- `Which fanbase is calmer`
- `What both sides are worried about`
- `Where the model, market, and mood disagree`

## Best v1 technical rollout

### Phase 1

- add schema and runtime migrations
- add alias tables
- add raw conversation and target-score tables
- add weekly / game-window aggregate tables

### Phase 2

- ingest Reddit + Bluesky + headline discovery
- compute team-level aggregates
- build weekly homepage modules
- keep scope `FBS` and `team-level` only

### Phase 3

- add YouTube comments for featured teams / games only
- add storyline labeling
- ship team-page `Fan Pulse` and `National Mood`

### Phase 4

- add `team_conversation_daily`
- add `player_aliases` for award-watch and featured-player work
- add `game_line_snapshots`
- add `prediction_market_snapshots`
- build deeper event studies

## Cost discipline

Practical monthly target under the broader site budget:

- use `Apify` carefully for Reddit and search discovery
- keep `YouTube` official
- use `Bluesky` public endpoints directly
- use `Anthropic` only for critique, storyline labeling, or editorial polish

The leanest rule is:

- use LLMs for the `last mile`
- not for every raw document

## Recommended next implementation steps

1. land the schema and migrations
2. add source credentials to `.env`
3. create a watchlist-driven ingestion layer for Reddit, Bluesky, and headlines
4. compute `team_week_conversation_features`
5. join those features to `game_lines` for the first analysis notebook / report

## Sources checked

Official or primary sources reviewed for this plan:

- `Bluesky app.bsky.feed.searchPosts`
  - https://docs.bsky.app/docs/api/app-bsky-feed-search-posts
- `Apify schedules`
  - https://docs.apify.com/platform/schedules
- `Apify Python client`
  - https://docs.apify.com/api/client/python/reference/class/ApifyClient
- `YouTube Data API overview`
  - https://developers.google.com/youtube/v3/getting-started
- `YouTube comments implementation guide`
  - https://developers.google.com/youtube/v3/guides/implementation/comments
- `Kalshi public market data quick start`
  - https://docs.kalshi.com/getting_started/quick_start_market_data
- `Polymarket API introduction`
  - https://docs.polymarket.com/api-reference/introduction
- `Polymarket rate limits`
  - https://docs.polymarket.com/api-reference/rate-limits
