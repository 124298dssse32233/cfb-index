# Team Preview Data Source Maximization

As of: 2026-05-25  
Companion specs:

- `docs/specs/team-preview-system-blueprint-2026.md`
- `docs/specs/team-page-may-2026-user-journey.md`

This is not an implementation plan. It is the pre-plan source audit: what data should power each concept, what the repo already has, what is missing, and which free sources are worth adding.

## 1. Product Rule

Every team-page preview module should use the richest source stack it can support without faking precision.

The source order is:

1. Official / structured football fact source.
2. CFB Index model or derived metric.
3. Market / attention / fan-intel signal.
4. Editorial synthesis with visible receipts.

Do not let a single source type dominate:

- Recruiting rank alone is not roster reload.
- Net portal count alone is not transfer impact.
- Last year's record alone is not a projection.
- Fan mood alone is not reality.
- A model number alone is not a story.

## 2. Current Local Data Inventory

Local snapshot checked 2026-05-26. Production may differ.

Strong local coverage:

| Table | Rows | Coverage | Product use |
| --- | ---: | --- | --- |
| `games` | 8,594 | 2018-2024 | schedules, results, recent form, rivalry, home/away |
| `power_ratings_weekly` | 32,618 | 2020-2024 | season path, leverage, model priors |
| `resume_ratings_weekly` | 26,367 | 2020-2024 | committee-style resume context |
| `official_rankings` | 2,701 | 2020-2024 | AP/Coaches/CFP labels |
| `returning_production` | 525 | 2020-2025 | roster continuity |
| `team_talent_snapshots` | 530 | 2020-2025 | blue-chip / talent floor |
| `recruiting_entries` | 533 | 2020-2025 | team class rank and rating |
| `player_recruiting_profiles` | 20,392 | 2020-2026 | top recruits, position/class shape |
| `transfer_entries` | 14,800 | 2023-2026 | transfer additions/losses |
| `player_nfl_draft` | 2,316 | 2018-2026 | draft losses and pipeline |
| `player_game_stats` | 1,304,322 | 2020-2024 | role/production loss, returning usage |
| `player_season_stats` | 426,725 | 2020-2024 | production by player/position |
| `chronicle_card_cache` | 672 | 2024 | narrative cards |
| `chronicle_visual_cache` | 2,404 | 2024-2025 | visual story candidates |

Weak or empty local coverage:

| Table | State | Consequence |
| --- | --- | --- |
| `priority_teams` | empty | fan-intel adapters cannot know which feeds/handles/pages to pull |
| `fanbase_mood_weekly` | empty | no reliable Fan Reality Gap until aggregation is active |
| `team_cohort_week` / `team_cohort_divergence_week` | empty | no cohort split or civil-war module yet |
| `source_observations` | only Polymarket volume rows locally | attention sources exist in code but are not producing broad data |
| `game_lines` / `game_line_snapshots` | empty | market-vs-model modules need CFBD line ingest or a fallback |
| `game_weather` | empty | weather should be suppressed until loaded or forecast window opens |
| `team_savant_weekly` | empty | Savant module needs either rebuilt inputs or a confidence-labeled fallback |
| `editorial_citations` | empty | receipt pattern is designed but not populated for preview claims |

Main conclusion:

- Football-structure data is the current strength.
- Fan-intel source infrastructure exists but is not yet activated at scale locally.
- Team pages should first maximize CFBD/model/roster/portal/draft/recruiting data, then layer fan-intel where confidence supports it.

## 3. Source Tiers for Team Previews

### Tier A: publish numeric

Use directly with confidence/freshness labels.

| Source | Existing? | Team-page use |
| --- | --- | --- |
| CFBD API | yes | games, schedules, rosters, returning production, talent, recruiting, portal, draft, ratings, lines, weather |
| CFB Index power/resume models | yes | path projection, schedule leverage, model baseline |
| NCAA / CFP official docs | partly manual | CFP path rules, recruiting calendar, transfer windows |
| Wikimedia Pageviews API | adapter exists | attention spikes for team/coach/QB pages |
| GDELT DOC 2.0 | adapter exists | media volume, national attention |
| SeatGeek API | adapter exists | ticket demand / event heat |
| Polymarket / Kalshi public APIs | adapter exists | futures and national expectation where liquid |
| NWS weather.gov API | not yet in repo as adapter | game-week weather for schedule leverage |

### Tier B: aggregate only

Use with sample size and confidence. Do not publish raw quotes as representative fact.

| Source | Existing? | Team-page use |
| --- | --- | --- |
| Reddit | client exists; collection runs exist | team mood, rival heat, panic/calm |
| Bluesky AppView / Jetstream | adapter exists | media/fan discourse, beat-writer chatter |
| YouTube Data API metadata | adapter exists | views/comments volume on team/fan videos |
| YouTube comments | source strategy says yes; verify adapter state before use | fan mood with quota gating |
| Google News RSS | adapter exists | news volume and topic changes |
| Campus newspapers RSS | adapter exists | student/local campus perspective |
| Beat-writer RSS | adapter exists | local media posture |
| School athletics RSS | adapter exists | official roster/news claims |
| Podcast RSS / Locked On | adapter exists | local audio discourse metadata |
| Team message boards | adapter/playbooks exist | diehard mood, transfer/recruiting anxiety |

### Tier C: rank/trend only

Use only as relative movement, not precise numeric truth.

| Source | Existing? | Team-page use |
| --- | --- | --- |
| Google Trends DMA export | registry entry | regional attention rank |
| GDELT tone | registry entry | press tone trend, not raw sentiment |
| thin prediction markets | registry entry | "market exists but thin" flag |

### Tier D: citation only

Use as receipts for claims, not as generalized data.

| Source | Existing? | Team-page use |
| --- | --- | --- |
| Official school media guides / record books | new/free source | all-time bowl ledgers, stadium, program records |
| NCAA record PDFs | new/free source | bowl records and official definitions |
| Beat articles | registry entry | sourced quote/context |
| School press releases | registry entry | roster/coach/schedule confirmations |
| Free 247/On3 pages | partial/manual | cross-check portal/recruit status, not silent scrape truth |
| College Football Reference / Winsipedia | new/manual QA | all-time history cross-checks, not sole canonical source |

## 4. Module Source Contracts

### PreviewThesis

Maximum source blend:

- final 2025 record and postseason endpoint from `games`
- final AP/Coaches/CFP labels from `official_rankings`
- schedule opener from CFBD/future schedule plus official school schedule fallback
- roster continuity from `returning_production`
- talent floor from `team_talent_snapshots`
- portal balance from `transfer_entries`
- draft losses from `player_nfl_draft`
- high-school class shape from `player_recruiting_profiles`
- fan/attention context from `source_observations` and `conversation_documents` if confidence supports it

Rule:

- thesis must name one roster hinge, one path hinge, or one belief hinge. It should not summarize every dataset.

### SeasonPathBand

Maximum source blend:

- 2026 schedule: CFBD first, official school/conference schedule fallback
- opponent strength: CFB Index power ratings, CFBD SP/FPI/Elo/SRS if loaded
- roster priors: returning production, talent, portal, recruiting, draft losses
- market priors: CFBD lines when in season; liquid Polymarket/Kalshi futures only where applicable
- CFP rules: official CFP format and seeding docs
- conference title path: conference schedule/model

Free-source additions worth considering:

- official team/conference schedule pages for kickoff time and TV truth
- FBSchedules as a human QA source only, not canonical
- ESPN public scoreboard/schedule endpoint only as a fallback QA source, because it is not an official documented contract

Confidence:

- high: full schedule + model ratings + roster priors
- medium: schedule + model ratings, incomplete roster priors
- low: schedule missing or relying on calendar fallback

### RosterReplacementXray

Maximum source blend:

- `returning_production`: team-level continuity
- CFBD roster snapshots: returning players and class/year
- `player_game_stats` / `player_season_stats`: actual production lost/retained
- `transfer_entries`: inbound/outbound transfer movement
- `player_nfl_draft`: draft exits and draft capital
- `player_recruiting_profiles`: recruit pedigree by position
- team official roster pages: free fallback for class/position confirmation
- school signing-day releases: free source for early-enrollee and status language

Do not flatten:

- transfer loss != graduation loss
- transfer addition != high-school addition
- production loss != body-count loss
- draft pick != undrafted eligibility exit

Needed derived tables:

- `team_position_continuity`
- `team_transfer_snapshot`
- `team_draft_loss_snapshot`
- `team_recruiting_shape`

### TransferPortalBalance

Maximum source blend:

- CFBD `/player/portal` via `transfer_entries` as primary
- ratings, stars, transfer points from the same table
- prior production joined from player stats when player_id matches
- destination/source school for loss context
- On3 transfer portal team pages/rankings as free public cross-check where manual QA is acceptable
- official team announcements for high-profile additions/losses

Required display:

- additions count
- losses count
- incoming quality
- outgoing quality
- top addition
- costliest loss
- unreplaced position need
- position-level net and quality swing

Rule:

- never show only `net +N` or `net -N`. Net is a footer, not the module.

### HighSchoolRecruitingReload

Maximum source blend:

- `recruiting_entries`: team class rank/rating
- `player_recruiting_profiles`: player rank, state, position, stars, rating
- CFBD recruit geography fields
- 247/On3 free pages as status/cross-check where legally and operationally safe
- school signing-day pages for signed/enrolled wording

Required distinction:

- high-school recruiting can solve future depth.
- portal additions solve immediate roster holes more often.
- freshman class should not be described as replacing transfer losses unless the player is likely to play immediately.

### ScheduleLeverageMap

Maximum source blend:

- 2026 schedule
- power rating gap
- home/away/neutral and travel
- rivalry flags
- rest / bye weeks / short weeks
- CFBD lines when available
- NWS forecast once within forecast range
- SeatGeek event prices/listing counts as fan-demand proxy
- fan mood volatility if active

Derived metrics:

- `game_win_probability`
- `playoff_or_bowl_odds_delta`
- `conference_title_delta`
- `rivalry_weight`
- `fan_combustibility`

Free-source additions:

- NWS `api.weather.gov` for U.S. venue forecasts
- Open-Meteo for international games where NWS does not apply

### FanRealityGap

Maximum source blend:

- Reddit team/national/city/alumni sources
- Bluesky curated handles and feeds
- YouTube metadata and comments
- Google News RSS
- GDELT volume/tone
- Wikipedia pageviews/edits
- podcast RSS metadata
- message-board observations
- SeatGeek demand
- model baseline
- market baseline

Output must separate:

- fan mood
- national mood
- rival heat
- media attention
- market belief
- model reality

Low-signal fallback:

- use attention and source activity ("quiet, but schedule/portal movement is the last real signal")
- do not invent a mood number

Current blocker:

- `priority_teams` is empty locally, so most fan-intel adapters have no targets.

### AllTimeBowlLedger

Maximum source blend:

- NCAA official record book/PDF for definitions
- official school media guide/record book for program claim
- College Football Reference / Sports-Reference as structured cross-check
- Winsipedia as public cross-check
- local `games` postseason rows only for recent detail, never for all-time total

Required fields:

- source scope: all-time bowl record / major bowls / all postseason / CFP included or excluded
- wins, losses, ties
- appearances
- verified_as_of
- source_url
- confidence

Rule:

- if sources disagree, render the scope distinction instead of choosing silently.

### WhatChangedSinceSpring

Maximum source blend:

- snapshot hashes across:
  - path projection
  - transfer snapshot
  - recruiting snapshot
  - schedule truth
  - fan/attention sources
  - model/market data

Good output:

- "Portal balance moved from patched to thin at WR."
- "Schedule opener time confirmed."
- "Fan attention quiet; media volume increased."
- "Recruiting class added a position-need match."

## 5. Free Sources Worth Adding or Activating

### Highest value

| Source | Why it matters | Use |
| --- | --- | --- |
| Official team/conference schedule pages | fixes kickoff/date/TV truth | CalendarRail, ScheduleLeverageMap |
| Official school media guides / record books | all-time ledgers and program records | AllTimeBowlLedger, ProgramStandard |
| NCAA record PDFs | official definitions for records | Bowl scope, record definitions |
| NWS weather.gov | free official U.S. forecast API | game-week schedule leverage |
| Wikimedia Pageviews/Edits | free attention proxy | FanRealityGap, WhatChanged |
| GDELT DOC 2.0 | free media volume | national attention |
| Bluesky AppView/Jetstream | free public social graph | fan/media mood |
| YouTube Data API | free quota | video attention, comments if added |
| SeatGeek | free key | ticket demand and event heat |
| Polymarket public Gamma API | no auth for market discovery | market belief where liquid |

### Useful but lower trust / fallback

| Source | Caveat | Use |
| --- | --- | --- |
| Google News RSS | not a formal stable API contract | topic discovery, not canonical facts |
| FBSchedules | useful schedule QA, not official | cross-check schedule gaps |
| ESPN public endpoints | undocumented | schedule/scoreboard QA only |
| College Football Reference | excellent structure, respect site limits | all-time cross-check/manual seed |
| Winsipedia | excellent public historical context | all-time cross-check/manual seed |
| Free On3/247 pages | page structure and access can change | portal/recruit status QA |

### Avoid as core sources

- paywalled On3/247/Rivals content
- X/Twitter scraping
- Instagram/Facebook bulk collection
- Discord/private communities
- unofficial TikTok scraping as a cron dependency
- injury/depth-chart claims without official/beat receipts

## 6. Source Activation Gaps Before Any Build Plan

These are not implementation steps yet. They are source readiness checks that should shape the later plan.

1. `priority_teams` must be populated for the teams we care about first. Without it, fan-intel adapters cannot target pages, feeds, handles, podcasts, or ticket slugs.
2. `source_observations` should be broadened beyond Polymarket volume rows. Wikimedia, GDELT, YouTube, SeatGeek, and Google News are already coded or nearly coded paths.
3. `conversation_document_targets` needs rows so collected documents are tied to teams and can aggregate into mood/cohort outputs.
4. `game_lines` or `game_line_snapshots` should be loaded before any market-vs-model claim renders.
5. All-time bowl ledger should be a seeded, source-scoped table rather than a dynamic scrape.
6. Future 2026 schedule truth should have at least two layers: CFBD plus official school/conference confirmation for kickoff time/TV.
7. Transfer portal rows need quality and prior-production joins so portal losses read correctly.
8. High-school recruiting needs status handling: committed, signed, enrolled, unknown.
9. Every module must have a confidence fallback path before it ships.

## 7. Best Data Moats

The strongest CFB Index differentiators are the combinations, not any one dataset:

1. Portal losses plus prior production plus roster need.
2. High-school recruiting shape plus portal unreplaced holes.
3. Schedule leverage plus CFP/bowl path deltas.
4. Fan mood plus model baseline plus market baseline.
5. Program standard plus current projection.
6. Media/fan attention shifts plus "what changed" snapshots.
7. All-time ledgers with source-scope honesty.

These are the places to spend design and engineering effort. They are harder to copy than a top-25 rank, a recruiting class rank, or a generic preview paragraph.

## 8. Sources Checked

- CollegeFootballData API / Swagger: https://api.collegefootballdata.com/
- CollegeFootballData site/API access: https://collegefootballdata.com/
- CFP 2025-26 seeding policy: https://collegefootballplayoff.com/news/2025/5/22/2526-seeding-rev.aspx
- NCAA FBS recruiting calendar: https://ncaaorg.s3.amazonaws.com/compliance/recruiting/calendar/2025-26/2025-26D1Rec_FBSMFBRecruitingCalendar.pdf
- NCAA Division I transfer windows: https://fs.ncaa.org.s3.amazonaws.com/Docs/eligibility_center/Transfer/DIUG_Windows.pdf
- Wikimedia Pageviews API: https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html
- GDELT DOC 2.0 API: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- Bluesky Jetstream: https://docs.bsky.app/blog/jetstream
- YouTube Data API quota/docs: https://developers.google.com/youtube/v3/getting-started
- SeatGeek Platform API: https://seatgeek.github.io/
- Polymarket API docs: https://docs.polymarket.com/api-reference
- Kalshi API help: https://help.kalshi.com/account-and-login/kalshi-api
- NWS API docs: https://www.weather.gov/documentation/services-web-api
- NCAA football records/statistics page: https://ncaaorg.sidearmsports.com/sports/2013/11/19/ncaa-football-statistics.aspx
- College Football Reference Alabama bowl page example: https://www.football-reference.com/cfb/schools/alabama/bowls.html
- Winsipedia Alabama page example: https://www.winsipedia.com/alabama
