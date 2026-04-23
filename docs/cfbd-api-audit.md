# CFBD API Audit

Last reviewed: April 21, 2026

Primary sources:
- https://api.collegefootballdata.com/api-docs.json
- https://blog.collegefootballdata.com/api-v2-is-now-in-general-availability/

## Scope

This audit compares our local CFBD integration against the official v2 OpenAPI spec and notes the concrete implementation work completed during the review.

Reviewed endpoints:
- `/games`
- `/lines`
- `/games/weather`
- `/stats/game/advanced`
- `/drives`
- `/plays`
- `/roster`
- `/player/returning`
- `/talent`
- `/recruiting/teams`
- `/games/players`
- `/stats/player/season`
- `/player/usage`
- `/wepa/players/passing`
- `/wepa/players/rushing`
- `/recruiting/players`
- `/player/portal`

## Changes made

### 1. CFBD client parameter parity

Updated `src/cfb_rankings/clients/cfbd.py` so the wrapper now exposes the documented optional filters instead of only a narrow subset.

Examples:
- `get_games()` now supports `team`, `home`, `away`, `conference`, and `game_id`.
- `get_lines()` now supports `game_id`, `team`, `home`, `away`, `conference`, and `provider`.
- `get_weather()` now supports `team`, `conference`, `classification`, and `game_id`.
- `get_advanced_game_stats()` now supports `team`, `opponent`, and `exclude_garbage_time`.
- `get_drives()` and `get_plays()` now support the full documented offense/defense/conference/classification filters.
- `get_returning_production()` now supports `team` and `conference`.
- `get_recruiting_teams()` now supports `team`.
- `get_game_player_stats()` now supports `classification`, `category`, and `game_id`.

This keeps our integration layer aligned with the official contract and makes future ingest work much easier.

### 2. Transfer portal ingest is now live

We already had a `transfer_entries` table and the preseason power-prior model was already reading transfer balance from it, but the CFBD `/player/portal` feed was not being ingested.

That gap is now closed in `src/cfb_rankings/ingest/cfbd.py`:
- `ingest_cfbd_preseason()` now ingests CFBD transfer portal data.
- Portal rows are written into `transfer_entries`.
- `from_team_id`, `to_team_id`, `from_level_code`, and `to_level_code` are resolved where possible.
- `transfer_points` is populated from CFBD `rating` when available, otherwise falls back to `stars`, then `1.0`.
- raw transfer context like origin, destination, transfer date, stars, and eligibility is preserved in `notes` as JSON.

This materially improves offseason priors, especially for the predictive and cross-season power model.

### 3. SQLite reliability hardening

Updated `src/cfb_rankings/db.py` to use:
- a SQLite connection timeout of 30 seconds
- `pragma busy_timeout = 30000`

This reduces failures from short-lived write contention during long multi-command refreshes.

## Validation completed

After the audit changes:
- preseason CFBD context was refreshed for seasons 2021-2025
- transfer portal data was loaded for seasons 2021-2025
- power/resume models were rerun for seasons 2021-2025
- the published site was rebuilt

Observed transfer row counts after the refresh:
- 2021: 1,770
- 2022: 2,273
- 2023: 2,502
- 2024: 3,378
- 2025: 4,499

Observed 2025 preseason context counts:
- `returning_production`: 134
- `team_talent_snapshots`: 134
- `transfer_entries`: 4,499

## Important behavioral notes from the official spec

### Division classification enum

The official `DivisionClassification` values in CFBD v2 are:
- `fbs`
- `fcs`
- `ii`
- `iii`

Our CLI/classification usage should continue to pass lowercase values to CFBD.

### Season type enum

The official `SeasonType` values include:
- `regular`
- `postseason`
- `both`
- `allstar`
- `spring_regular`
- `spring_postseason`

Our current site pipeline mainly uses `regular`, `postseason`, and `both`, which matches present needs.

## Remaining follow-up opportunities

These are not blocker issues for the main rankings site, but they are worth tackling next:

### 1. Heisman season-stat normalization for historical seasons

During reruns, the player season-stat endpoints returned large CFBD payloads for 2021-2024, but our FBS normalization path did not produce usable candidate rows for those seasons. That suggests a roster/player identity coverage issue in the Heisman pipeline rather than an API contract problem.

### 2. Player-level recruiting ingest

We now use:
- team recruiting summaries
- roster snapshots
- transfer portal

We are still not ingesting the player-level `/recruiting/players` endpoint into a dedicated workflow. That could later improve player pages, recruiting-history storytelling, and roster-quality explanations.

### 3. Game-player stat ingest for team/player pages

The wrapper now supports the full `/games/players` parameter set, but the main site still does not surface game-level player stat detail. That is a strong future enhancement for matchup pages, player pages, and “why the model moved” explainers.
