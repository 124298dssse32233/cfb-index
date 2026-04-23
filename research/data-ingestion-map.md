# Data Ingestion Map

Research date: 2026-04-20

This document explains how `TheSportsDB` and `CollegeFootballData Tier 2` should feed the database and models.

It exists to answer four practical questions:

1. Which source should own which data?
2. How do we join everything together?
3. How often should each dataset refresh?
4. How do we stay efficient with API usage?

## Source ownership

### TheSportsDB should own

- team discovery across all levels
- league and season discovery
- team identity metadata
- venue metadata
- schedule and final-score coverage across all levels
- public-facing imagery and artwork

Use TheSportsDB as the universal front-end backbone because it covers the whole site experience better.

### CFBD Tier 2 should own

- FBS/FCS games and game metadata
- rosters
- recruiting data
- team talent
- returning production
- betting lines
- weather
- team and player stats
- advanced box scores
- opponent-adjusted metrics
- drives
- play-by-play

Use CFBD as the analytics truth source for FBS and FCS.

### NCAA and manual layers should own

- DII official ranking priors
- DIII NPI priors
- lower-division coaching changes
- lower-division continuity notes
- major lower-division roster shocks not represented cleanly elsewhere

## Canonical join strategy

Never join raw source feeds directly in the app.

Always join through canonical IDs:

- `teams.team_id`
- `games.game_id`
- `players.player_id`

The bridge tables are:

- `team_source_ids`
- `game_source_ids`
- `player_source_ids`

That lets us:

- keep SportsDB and CFBD names from drifting independently
- support school renames and aliases
- merge level changes or conference changes cleanly

## Table ownership map

### SportsDB -> core tables

Use SportsDB to populate:

- `levels`
- `conferences`
- `venues`
- `teams`
- `team_source_ids`
- `seasons`
- `games`
- `game_source_ids`

Preferred SportsDB surfaces:

- team lookup and team search
- league/season listing
- schedule/event lookup
- venue lookup

Use it for:

- badge and logo assets
- fanart
- broad team metadata
- all-level schedule coverage

### CFBD -> core and analytics tables

Use CFBD to populate:

- `games`
- `game_lines`
- `game_weather`
- `players`
- `player_source_ids`
- `roster_entries`
- `recruiting_entries`
- `team_talent_snapshots`
- `returning_production`
- `transfer_entries` when stable data exists
- `drives`
- `plays`
- `team_game_advanced_stats`

Preferred CFBD surfaces:

- games
- team stats
- advanced box scores
- betting lines
- weather
- roster
- recruiting
- talent
- drives
- plays

Use CFBD as the richer source whenever both feeds cover the same FBS/FCS game.

### NCAA/public/manual -> prior and explainability tables

Use NCAA and manual input to populate:

- `official_rankings`
- `team_seasons`
- `manual_team_adjustments`

These are especially important for DII and DIII.

## Conflict resolution rules

### Team identity

If SportsDB and CFBD disagree on spelling:

- keep the canonical school name in `teams`
- store both raw forms in source-id tables
- prefer the school's official athletic branding in the public UI

### Game results

For FBS/FCS:

- prefer CFBD for analytics fields
- accept SportsDB for presentation fields when needed
- final scores should reconcile nightly

For DII/DIII:

- SportsDB will often be the only structured source
- if public manual verification is needed, store a note in `games.notes`

### Venue and neutral-site flags

Prefer CFBD for FBS/FCS neutral-site truth.
Prefer SportsDB for venue artwork and public venue details.

## Refresh cadence

### Preseason full sync

Run once in late spring and once again in August.

Load:

- teams
- conferences
- venues
- seasons
- rosters
- recruiting
- talent
- returning production
- official lower-level rankings
- manual offseason adjustments

### In-season nightly sync

Run every night during the season.

Load:

- upcoming schedules
- game status updates
- final scores
- lines
- weather
- updated team metadata if changed

### Game-day live or near-live sync

Run more frequently on Saturdays.

Load:

- live scoreboard
- live play-by-play for FBS/FCS if needed
- in-progress weather

This is optional for version one if the site is not trying to be a live-game dashboard.

### Postgame enrichment sync

Run after final results settle.

Load:

- advanced box scores
- drives
- play-by-play
- game lines close
- final weather snapshot

Then trigger:

- opponent-adjusted weekly feature refresh
- Power model recompute
- Resume recompute
- team-page delta generation

## API budget strategy

### CFBD Tier 2 budget

As of April 20, 2026, CFBD Tier 2 allows `30,000 calls/month`.

That is enough if we cache correctly.

Rules:

- never refetch immutable historical seasons unless repairing data
- load weekly slices instead of team-by-team slices whenever possible
- store raw payloads for replay/debugging
- compute opponent-adjusted features from stored plays, not repeated API calls

### SportsDB budget

SportsDB documentation currently shows:

- premium rate limit `100 requests per minute`

That is plenty for scheduled syncs as long as we batch responsibly and cache IDs.

## Recommended load order

### Initial historical backfill

1. Load all levels, conferences, seasons, and teams from SportsDB.
2. Build canonical team mapping in `team_source_ids`.
3. Load historical games from SportsDB for all levels.
4. Load CFBD historical FBS/FCS games and match to canonical `games`.
5. Backfill CFBD lines, weather, advanced box scores, drives, and plays for FBS/FCS.
6. Backfill recruiting, talent, roster, and returning production for recent seasons.
7. Backfill NCAA DII/DIII ranking priors for recent seasons where available.

### Weekly operating load

1. Refresh schedules and scores.
2. Refresh CFBD weekly analytics surfaces.
3. Recompute opponent-adjusted features.
4. Run the model.
5. Publish weekly outputs.

## Matching logic

### Team matching

Match teams using:

- source ID when already known
- normalized school name
- state
- level
- conference

Never rely on name-only matching once a canonical mapping exists.

### Game matching

Match games using:

- home team
- away team
- start date
- season year
- week

Allow fuzzy date windows for kickoff-time mismatches.

Store every successful source-game mapping in `game_source_ids`.

## Raw payload retention

For debugging and reprocessing, keep a raw-ingestion store outside the core relational schema.

Recommended folders or object storage pattern:

```text
raw/
  sportsdb/
    teams/YYYY-MM-DD/
    events/YYYY-MM-DD/
  cfbd/
    games/YYYY/week-N/
    lines/YYYY/week-N/
    advanced-box/YYYY/week-N/
    drives/YYYY/week-N/
    plays/YYYY/week-N/
```

Why this matters:

- source fields can change
- mappings occasionally fail
- model logic evolves
- replaying raw snapshots saves a lot of pain

## Model-ready feature snapshots

Do not query raw plays directly from the app for every page render.

Materialize weekly feature snapshots:

- `opponent_adjusted_team_week`
- `power_ratings_weekly`
- `resume_ratings_weekly`
- `game_predictions`
- `team_rating_deltas`
- `strength_of_record_benchmarks`

This makes the site fast and lets the UI tell rich stories without rerunning heavy model logic.

## Data quality rules

### Required to publish Power

- canonical teams mapped
- final score available
- venue or neutral-site status known well enough

### Required to publish advanced FBS/FCS Power

- advanced box or play/drive data available
- betting line available for calibration if historical

### Required to publish Resume

- final result available
- pregame Power snapshot frozen

### Required to publish cross-level confidence

- posterior uncertainty available
- bridge-game connectivity computed

## Versioning rule

Every publish should write one `model_runs` row.

All derived outputs should reference that run.

This gives us:

- reproducibility
- rollback
- clean historical snapshots
- easy debugging when a team page looks wrong

## Recommended first implementation

If we want the fastest serious build:

1. Build canonical `teams`, `games`, and source-id mappings first.
2. Backfill SportsDB schedules/results across all levels.
3. Backfill CFBD analytics for FBS/FCS.
4. Materialize weekly derived tables.
5. Build the app only on derived tables plus core metadata.

That sequence gives us a stable foundation before we start polishing the front end.
