# CFBD Tier 2 And Safe Operations

Last updated: April 22, 2026

## Purpose

This document is the operational memory for two recurring questions:

1. Is `CollegeFootballData Tier 2` enough for this project and for the planned market/sentiment work?
2. How should we run heavy Python jobs without making the local chat workflow feel frozen or fragile?

If thread context is lost, this file should be treated as a practical source of truth alongside:

- `docs/internal-project-context.md`
- `docs/operations-runbook.md`
- `docs/cfbd-api-audit.md`
- `output/program-history-integrity-audit.md`

## Short answer

- `CFBD Tier 2` is enough for the current site and for the next research layer we care about.
- We do **not** need to move off Python to launch a real site.
- We do **not** need to move off SQLite for v1 static-site publishing.
- We **do** need to run heavy ingestion and backfills more carefully, preferably outside the live chat session and with logs.
- Keeping `REQUEST_TIMEOUT_SECONDS=60` as the default is reasonable. That is not a dumb preference.

## Current architecture truth

The project is currently designed as:

- Python ingestion and model jobs
- SQLite as the local build database
- precomputed outputs in `output/site`
- a static-site publishing flow

That means the public site does **not** need live SQLite reads on every request.

The most important operational distinction is:

- `Python + SQLite` here is primarily a content pipeline
- not the public serving layer

This is why the project can launch as a real site without first becoming a heavy always-on web app.

## What CFBD Tier 2 gives us

Per the official CFBD tier page as checked on `April 21, 2026`, `Tier 2` currently includes:

- `30k API calls/month`
- basic API endpoints
- historical data
- team statistics
- player statistics
- recruiting data
- betting lines
- advanced metrics
- opponent-adjusted metrics
- weather data
- live scoreboard
- live play-by-play

Important exclusion:

- `GraphQL API` and subscription-style access begin at `Tier 3`, not `Tier 2`

Source:

- https://collegefootballdata.com/api-tiers

## What the repo already uses from Tier 2

The current CFBD client in `src/cfb_rankings/clients/cfbd.py` already supports a strong Tier 2 slice.

### Core weekly ingest

The weekly ingest pipeline uses:

- `/games`
- `/lines`
- `/games/weather`
- `/stats/game/advanced`
- `/drives`
- `/plays`

These feed:

- schedules and results
- betting context
- weather context
- advanced team/game metrics
- possession-level context
- play-level context

### Preseason and roster context

The preseason ingest uses:

- `/roster`
- `/player/returning`
- `/talent`
- `/recruiting/teams`
- `/recruiting/players`
- `/player/portal`

These feed:

- roster snapshots
- returning production
- team talent
- recruiting priors
- transfer portal context

### Heisman and player-context layer

The Heisman pipeline uses:

- `/rankings`
- `/stats/player/season`
- `/player/usage`
- `/wepa/players/passing`
- `/wepa/players/rushing`
- `/stats/season/advanced`

This is enough for:

- official-poll visibility
- player season stat normalization
- usage share
- value metrics
- team-defense context

## Practical conclusion on Tier 2

Tier 2 is enough for:

- the current rankings site
- matchup and betting-context features
- open/close line storytelling
- weather and market context
- player and Heisman modeling
- the first version of a market/sentiment study

Tier 2 is **not** enough for:

- true subscription-based live market dashboards via CFBD GraphQL
- pretending the site is a live trading terminal with push subscriptions

But that is fine because the current product should stay mostly batch-generated anyway.

## Important product caveat for betting research

CFBD lines are useful, but the current local table design is still better for:

- open-to-close studies
- retrospective market-context features

than for:

- deep intraday lead/lag studies
- provider-by-provider time-series analysis

Why:

- the current `game_lines` table effectively stores one merged row per game
- the ingest currently takes the last available provider row in a game payload
- we do **not** yet store a full snapshot history of every line change over time

So for a richer future study, we should later add:

- `game_line_snapshots`
- `prediction_market_snapshots`

That is a data-model improvement, not a Tier 2 blocker.

## Why long Python runs feel frozen

The local app is not usually crashing because Python is inherently the wrong tool.

The more likely causes are:

### 1. Large blocking API calls

The CFBD client currently makes blocking HTTP requests through `urllib`.

Some endpoints are naturally heavy:

- `plays`
- `drives`
- `stats/player/season`
- `player/usage`
- player WEPA endpoints

### 2. Retries can make a slow endpoint feel hung

`src/cfb_rankings/clients/base.py` retries transient failures up to `5` attempts with exponential backoff.

That is good for reliability, but it means one bad endpoint can take several minutes before finally failing.

Important exception:

- permission-denied outbound socket failures such as Windows `WinError 10013` now fail fast instead of retrying

Why:

- that class of error usually means the environment itself is blocking network access
- retrying does not improve the outcome
- failing fast makes long-running jobs much easier to reason about

### 3. `sync-site` is a bundle command

The `sync-site` path can do all of this in one foreground run:

- initialize schema
- ingest multiple weeks
- sync postseason
- run Power/Resume/Heisman models
- rebuild published outputs

That is convenient, but it is not the safest command to babysit inside an interactive chat.

### 4. The Heisman layer quietly adds work

If required cached player inputs are missing, model runs may trigger:

- `10` player stat category pulls
- player usage pulls
- two WEPA pulls
- rankings pulls
- advanced season-stat pulls

That makes a seemingly normal site refresh feel much heavier than expected.

### 5. The local database is already real-sized

As of `April 21, 2026`, the local SQLite file is roughly:

- `~410 MB`

And includes on the order of:

- `18k+` games
- `157k+` drives
- `1.14M+` plays

SQLite is still fine for this use case, but this is large enough that brute-force foreground refreshes can feel sluggish.

## What we changed to make long runs feel safer

The Windows logged wrappers now route Python commands through `scripts/Invoke-LoggedProcess.ps1`.

That helper:

- records the exact command in the log before the run starts
- mirrors stdout and stderr back into the console instead of buffering everything until exit
- prints periodic heartbeat lines during quiet periods with elapsed and idle time

This does not make a slow CFBD endpoint faster, but it does make operator trust much better:

- if the job is making progress, you will keep seeing output
- if the job is quiet but healthy, you will see heartbeat lines
- if outbound HTTP is blocked, the CFBD preflight still fails fast before the heavy stage begins

We also now treat the game-level player-stat backfill as a resumable / missing-first job:

- `scripts/backfill_game_player_stats_logged.ps1` defaults to `--missing-only`
- the CLI only targets source weeks whose completed FBS games still lack `player_game_stats`
- the archive pass now defaults to `--classification fbs`, so it does not waste CFBD calls on other subdivisions unless we ask for them on purpose
- the command now supports `--dry-run` and `--max-weeks`, so we can preview or bound a historical recovery batch before spending CFBD calls

That matters because the player-game archive is currently the largest historical gap, and brute-forcing every week would waste both time and CFBD calls once network access is available again.

## Timeout guidance

The default `REQUEST_TIMEOUT_SECONDS=60` is acceptable and should remain the default for now.

Reasons:

- several CFBD endpoints can legitimately be slow
- a `20-30` second global timeout is more likely to create false failures than to improve the actual operator experience
- the bigger problem is running heavy jobs in the wrong place, not the timeout being too generous

Current recommendation:

- keep `60` as the default
- optionally use `90` for overnight/background jobs if CFBD is having a rough day
- do **not** globally lower the timeout just to make interactive runs feel snappier

If we want different behavior later, the better design is:

- one timeout for normal/background ingest
- one shorter timeout for explicitly interactive/debug commands

But we do not need that split yet.

## Safe operating rules

### Use these commands for everyday work

Preferred daily commands:

- `python manage.py sync-site-incremental`
- `python manage.py build-published`
- `python manage.py build-site`
- `safe_refresh_site.ps1`

Why:

- they reuse already-loaded data when possible
- they avoid unnecessary brute-force reruns

If the run should stay light, prefer:

- `python manage.py sync-site-incremental --skip-play-level --skip-heisman`

Those two flags now exist specifically so normal maintenance does not silently turn into a huge job.

### Do not do giant multi-season jobs in chat

Avoid using the live chat session for:

- multi-season historical backfills
- first-time full player-data refreshes
- combined ingest + models + site builds over many seasons

Those should run:

- in PowerShell with logs
- in GitHub Actions
- in another detached runner

Helpful logged helpers now available:

- `safe_refresh_site.ps1`
- `scripts/backfill_cfbd_logged.ps1`
- `scripts/backfill_player_context_logged.ps1`
- `scripts/backfill_game_player_stats_logged.ps1`
- `scripts/load_history_2014_forward.ps1`

Those wrappers now run a lightweight CFBD connectivity preflight before the heavy work starts, so a blocked network or bad token fails immediately instead of looking frozen for a long time.
The raw heavyweight Python commands now also run that preflight by default, so the safer behavior is no longer limited to the PowerShell wrappers.
If we ever intentionally want the old behavior for debugging, the long-running commands accept `--skip-connectivity-check`.

### For heavy jobs, split the work into phases

Safer sequence:

1. backfill raw data
2. run models
3. build outputs

Less safe sequence:

1. one giant command that does all three across many seasons

### Prefer one season at a time

For history work:

- run one season first
- verify counts and outputs
- then move to the next season

Do not jump immediately to a long `2021-2025` or similar all-in-one run unless it is intentionally an overnight job.

### Prefer classification-wide roster pulls when possible

If we need a full FBS or FCS roster snapshot:

- prefer the classification-wide roster path
- avoid many small per-team roster calls unless the classification path is unavailable

### Keep the public site static

The public site should continue to read from generated outputs.

Do **not** tie user-facing page loads to:

- long model recomputes
- live SQLite mutations
- fresh CFBD calls

Heavy Python work belongs in scheduled or manual refresh jobs.

## Safe job patterns

### Normal refresh

Use:

```powershell
python manage.py sync-site-incremental --season 2025 --through-week 21
```

### Publish from already-loaded data

Use:

```powershell
python manage.py build-published
```

### Heavy backfill with logging

Use:

```powershell
New-Item -ItemType Directory -Force logs
python manage.py backfill-cfbd-history --start-season 2022 --end-season 2022 --include-postseason 2>&1 | Tee-Object logs\backfill-2022.log
```

### Recommended heavy backfill sequence

Example:

1. load one season's raw history
2. inspect counts
3. run models for that season
4. rebuild outputs

This is much safer than asking one foreground chat run to do everything.

## What we should improve later

These are worthwhile improvements, but they are not required to launch:

- checkpointed backfill commands
- `--skip-plays`, `--skip-heisman`, or similar narrow ingest flags
- clearer per-stage logging and elapsed-time reporting
- scheduled builds outside the interactive chat session
- a remote database only when we truly need shared live writes or dynamic APIs

Recent reliability upgrades already landed:

- resumable `load_history_2014_forward.ps1` checkpoint state in `output/logs/history-load-state-<start>-<end>.json`
- `python manage.py history-load-status` to turn that checkpoint into a readable progress report
- `scripts/safe_history_status.ps1` to regenerate that report with logging and inferred local artifact checks even before a checkpoint exists
- `scripts/safe_archive_audit.ps1` to produce a single operator report that merges publish health, audit coverage, season readiness, and next recovery actions
- `scripts/safe_refresh_local_health.ps1` to refresh the entire offline health-report stack and audit the built site links in one logged pass
- `python manage.py check-cfbd-connectivity` to fail fast before long archival jobs begin
- audit coverage now also tracks `heisman_vote_results`, not just broad honors rows
- `python manage.py audit-competition-integrity` to catch postseason continuity drift, duplicate-risk schedules, placeholder conference rows, and cross-level labeling issues

## Migration guidance

Do **not** migrate off Python just because heavy local jobs sometimes feel slow.

The first fixes should be operational:

- better job scheduling
- better logging
- safer command choices
- more incremental refresh behavior

Move from SQLite to Postgres only when one of these becomes true:

- multiple remote jobs need to write concurrently
- we add real live API endpoints backed by the DB
- we add user accounts, watchlists, polling, or admin tooling
- we need shared cloud-hosted writes rather than local build-time storage

## Bottom line

The current recommended stance is:

- keep `CFBD Tier 2`
- keep Python
- keep SQLite for the current static-site publishing flow
- keep `REQUEST_TIMEOUT_SECONDS=60` as the default
- avoid giant in-chat foreground jobs
- use incremental refreshes for normal work
- run heavy backfills with logs outside the active chat session

That is the best mix of reliability, cost control, and launch speed for the project right now.
