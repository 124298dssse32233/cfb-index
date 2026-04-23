# Operations Runbook

Last updated: April 22, 2026

## Purpose

This file explains how to safely operate the project without rediscovering everything from scratch.

Use this when:

- the thread context is gone
- commands are running longer than expected
- you only need to rebuild the site
- you are unsure whether to re-ingest, rerun models, or just regenerate HTML

Related operational memory:

- `docs/cfbd-tier2-and-safe-operations.md` covers the current CFBD Tier 2 scope, why some long Python jobs feel frozen, and the default timeout recommendation
- `docs/anthropic-second-brain-workflow.md` explains how Anthropic is meant to plug into the repo without becoming the default heavy processor

## Environment assumptions

- local OS: Windows
- shell: PowerShell
- database: SQLite
- local DB file: `cfb_rankings.db`
- entrypoint: `manage.py`

You do not need PostgreSQL or pgAdmin for this repo.

Timeout guidance:

- keep `REQUEST_TIMEOUT_SECONDS=60` as the default for now
- prefer background or logged runs for heavy ingest instead of lowering the timeout globally
- if a job is expected to be large, operator strategy matters more than forcing a shorter timeout
- if the environment blocks outbound HTTP entirely, the CFBD client now fails fast on permission-denied socket errors instead of retrying for several minutes

## First commands to know

Show command list:

```powershell
python manage.py --help
```

Current commands:

- `init-db`
- `list-sportsdb-leagues`
- `ingest-sportsdb`
- `ingest-cfbd-week`
- `ingest-cfbd-preseason`
- `import-player-honors`
- `seed-team-aliases`
- `collect-reddit-watchlist`
- `build-conversation-features`
- `sync-team-seasons`
- `run-models`
- `run-heisman-model`
- `backfill-player-context`
- `backfill-game-player-stats`
- `audit-data-coverage`
- `audit-player-archive`
- `audit-awards-archive`
- `audit-competition-integrity`
- `audit-program-history`
- `check-cfbd-connectivity`
- `history-load-status`
- `repair-team-current-identity`
- `sync-site`
- `sync-site-incremental`
- `backfill-cfbd-history`
- `build-published`
- `build-site`
- `build-rankings-report`

## Safe default workflow

If you only changed templates, reporting, CSS, or front-end layout:

```powershell
python manage.py build-published
```

This is the safest default for UI / reporting work because it refreshes both published outputs:

- `output/rankings.html`
- `output/site`

If you only care about the static site and want the absolute fastest HTML-only pass, `python manage.py build-site` is still available.

Windows publish shortcuts:

- `publish_site.bat`
- `publish_site.ps1`

If the database already has recent weeks loaded and you want to catch up carefully:

```powershell
python manage.py sync-site-incremental --season 2025 --through-week 21
```

Prefer `sync-site-incremental` over `sync-site` when possible.
It now rebuilds both `output/rankings.html` and the full static site in `output/site`.
It can also skip a redundant model rerun when the latest saved snapshot already covers the needed week with the current model version.

If you want the safest logged everyday refresh from Windows, use:

- `safe_refresh_site.bat`
- `safe_refresh_site.ps1`

That helper:

- writes a timestamped log to `output/logs`
- uses `sync-site-incremental`
- skips play-level ingest and the Heisman pass by default
- runs Python in unbuffered mode so progress messages flush immediately
- lets you opt back into heavier work when you explicitly want it

If you specifically want a safer logged wrapper around the heavy team-model command, use:

- `safe_run_models.bat`
- `safe_run_models.ps1`

Example:

```powershell
powershell -ExecutionPolicy Bypass -File .\safe_run_models.ps1 -Season 2025 -ThroughWeek 21
```

Optional published-output rebuild after the model run:

```powershell
powershell -ExecutionPolicy Bypass -File .\safe_run_models.ps1 -Season 2025 -ThroughWeek 21 -BuildPublished
```

That helper:

- writes a timestamped log to `output/logs`
- runs `python -u` so status lines appear immediately
- emits periodic terminal heartbeats during quiet stretches so operators can tell the job is still alive
- skips the Heisman pass by default unless you explicitly opt in
- can rebuild `output/rankings.html` and `output/site` after a successful model run

If historical pages have missing or stale conference-era labels, refresh season-aware team memberships without rerunning models:

```powershell
python manage.py sync-team-seasons
python manage.py sync-team-seasons --season 2025
python manage.py sync-team-seasons --start-season 2021 --end-season 2025
```

If you want a focused sanity check for program-history pages and suspicious season records:

```powershell
python manage.py audit-program-history --output output\program-history-integrity-audit.md
```

Use this when:

- a program page shows a suspicious record total
- you suspect one school may be split across multiple internal team IDs
- you want a quick offline check before trusting long-arc historical storytelling

If you want a focused check on how complete the FBS player archive is by season:

```powershell
python manage.py audit-player-archive --output output\player-archive-audit.md
```

Use this when:

- you want a faster answer than reading raw table counts
- you need to know which seasons still lack game-level player stats
- you want to verify whether postseason player-game coverage is actually present
- you want the machine-readable sidecar at `output/player-archive-audit.json` for automation or scripted triage

If you need a full ingest + model + site run from scratch for a season:

```powershell
python manage.py sync-site --season 2025 --through-week 21
```

That path also rebuilds both published outputs at the end:

- `output/rankings.html`
- `output/site`

If you specifically want the incremental path to rerun models even when a reusable snapshot exists, use:

```powershell
python manage.py sync-site-incremental --season 2025 --through-week 21 --force-models
```

If you want a lighter one-off manual run from the terminal, use:

```powershell
python manage.py sync-site-incremental --season 2025 --through-week 21 --skip-play-level --skip-heisman
```

## When commands may take a long time

### `build-published`

Usually reasonable. This regenerates both public HTML outputs from existing database state.

Use this first whenever the issue looks front-end, reporting, layout, or publish related.

It is also the right command after changing the historical similarity cards, since those are rendered into both the home board dropdowns and the full team pages.

### `build-site`

Usually reasonable. This regenerates static HTML from existing database state.

Use this when you only need the static site tree and do not care about refreshing `output/rankings.html`.

### `run-models`

Potentially expensive, especially for deeper seasons or when many snapshots need recalculation.

Use this when:

- new underlying game data was ingested
- model logic changed
- model output tables are stale

Do not use this just because HTML needs to change.

If you only need team models and want to avoid the Heisman data pull, use:

```powershell
python manage.py run-models --season 2025 --through-week 21 --skip-heisman
```

### `sync-site`

Potentially the heaviest common command because it can:

- initialize schema
- ingest many weeks
- sync postseason
- rerun models
- build outputs

Prefer `sync-site-incremental` unless you specifically need a fuller rerun.

This command is not the best choice to babysit inside an active chat session when large historical or first-time player-data refreshes are involved.

### `sync-site-incremental`

This is usually the best operational command for normal refreshes.

It can:

- ingest only missing weeks
- sync postseason weeks
- reuse an already-current model snapshot when safe
- rebuild both the standalone report and the full static site

This should remain the default choice for normal in-season maintenance.

## Machine-readable maintenance outputs

The main offline maintenance commands now write markdown plus matching JSON sidecars.

Current structured outputs:

- `output/data-coverage-audit.md` plus `output/data-coverage-audit.json`
- `output/player-archive-audit.md` plus `output/player-archive-audit.json`
- `output/awards-archive-audit.md` plus `output/awards-archive-audit.json`
- `output/competition-integrity-audit.md` plus `output/competition-integrity-audit.json`
- `output/program-history-integrity-audit.md` plus `output/program-history-integrity-audit.json`
- `output/history-load-status.md` plus `output/history-load-status.json`
- `output/archive-readiness-audit.md` plus `output/archive-readiness-audit.json`
- `output/local-health-refresh.md` plus `output/local-health-refresh.json`
- `output/maintenance-bundle.json`, which rolls the local-health result and parsed audit sidecars into one automation-friendly file
- `output/maintenance-action-queue.md` plus `output/maintenance-action-queue.json`, which distills the sidecars into prioritized operator actions and labels generated commands by mode, network requirement, expected weight, and safety read
- `output/maintenance-validation.md` plus `output/maintenance-validation.json`, which validates the generated maintenance JSON layer and fails if it finds broken links, stale artifacts, malformed sidecars, missing command metadata, or open P0 actions

Use the markdown files for the human operator read.
Use the JSON sidecars for automation, dashboards, or any script that should avoid scraping markdown tables and prose bullets.
`scripts/safe_refresh_local_health.ps1` now also prints the action-queue count and the top three actions after a successful run, so a beginner can see the next backend priorities without opening JSON.

Validation command:

```powershell
python manage.py validate-maintenance
```

## Heavy jobs

If you need to run a larger historical load or anything that may touch:

- many seasons
- player season stats
- player usage
- player WEPA
- full postseason refreshes

prefer running it with a log outside the active chat session.

Example:

```powershell
New-Item -ItemType Directory -Force logs
python manage.py backfill-cfbd-history --start-season 2022 --end-season 2022 --include-postseason 2>&1 | Tee-Object logs\backfill-2022.log
```

There is now a reusable helper for this pattern:

- `scripts/backfill_cfbd_logged.ps1`

Example:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\backfill_cfbd_logged.ps1 -StartSeason 2022 -EndSeason 2022 -IncludePostseason
```

The logged wrappers now share a small helper at `scripts/Invoke-LoggedProcess.ps1`.
That helper:

- writes the command line into the log first
- mirrors stdout and stderr into the console and log file
- prints periodic `[heartbeat] ... still running` messages during quiet stretches
- makes it much easier to distinguish "alive but slow" from "actually stuck"

For game-level player stats specifically, the logged wrapper now defaults to a missing-first strategy:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\backfill_game_player_stats_logged.ps1 -StartSeason 2025 -EndSeason 2025 -IncludePostseason
```

That wrapper now passes `--missing-only` by default, which means it only targets source weeks whose completed FBS games still lack `player_game_stats`.
It also defaults to `--classification fbs`, so the historical recovery path does not burn CFBD calls on FCS, DII, and DIII player-game endpoints unless we explicitly ask for them.
It now also supports two safer operator modes:

- `--dry-run` / `-DryRun` to preview targeted weeks without any CFBD calls
- `--max-weeks <N>` / `-MaxWeeks <N>` to stop after a bounded number of source weeks

If you really want to brute-force every week again, add:

```powershell
-ForceFullSeason
```

That helper now also uses unbuffered Python output so long historical loads show progress sooner in the terminal and in the log.

Model-runtime note:

- `python manage.py run-models --season 2025 --through-week 21 --skip-heisman` now completes successfully again in this workspace.
- `safe_run_models.ps1` also now accepts the more natural `-SkipHeisman` switch in addition to the older include-style toggle.

Safer pattern:

1. ingest data for one season
2. inspect counts / logs
3. run models
4. rebuild outputs

Less safe pattern:

1. run one giant all-in-one backfill across many seasons while also expecting an interactive chat workflow to stay pleasant

## Recommended decision tree

### Case 1: "The page layout is wrong"

Run:

```powershell
python manage.py build-published
```

### Case 2: "I changed reporting code and the generated page is outdated"

Run:

```powershell
python manage.py build-published
```

### Case 3: "I ingested a new week and rankings need to reflect it"

Run:

```powershell
python manage.py run-models --season 2025 --through-week 21 --skip-heisman
python manage.py build-published
```

### Case 4: "I want the project to catch up to the latest locally missing week"

Run:

```powershell
python manage.py sync-site-incremental --season 2025 --through-week 21 --skip-play-level --skip-heisman
```

### Case 5: "I want a major historical refresh"

Run:

```powershell
python manage.py backfill-cfbd-history --start-season 2019 --end-season 2025 --include-postseason --run-models --build-site
```

### Historical player context

Use this when the team/game history is already present and you want the player-side archive filled out for prior seasons:

```powershell
python manage.py backfill-player-context --start-season 2014 --end-season 2025
```

What it loads:

- season-end official rankings snapshot coverage
- FBS roster context
- player season stats
- player usage
- player WEPA / value metrics

For long runs, prefer the logged wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\backfill_player_context_logged.ps1 -StartSeason 2014 -EndSeason 2025 -ChunkSize 1
```

### Historical game-level player stats

Use this when you want the `/games/players` archive persisted for team pages, player pages, signature-performance cards, and matchup explainers:

```powershell
python manage.py backfill-game-player-stats --start-season 2014 --end-season 2025 --include-postseason
```

By default that command now targets `FBS` only. If we ever want to expand the archive deliberately, add one or more explicit classifications such as:

```powershell
python manage.py backfill-game-player-stats --start-season 2025 --end-season 2025 --include-postseason --classification fbs --classification fcs
```

If you want a pure preview without touching the network, use:

```powershell
python manage.py backfill-game-player-stats --start-season 2024 --end-season 2025 --include-postseason --dry-run --max-weeks 12
```

Logged wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\backfill_game_player_stats_logged.ps1 -StartSeason 2014 -EndSeason 2025 -IncludePostseason
```

Example bounded batch:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\backfill_game_player_stats_logged.ps1 -StartSeason 2024 -EndSeason 2025 -IncludePostseason -MaxWeeks 8
```

### Coverage audit

Generate a quick archive health report:

```powershell
python manage.py audit-data-coverage --output output\data-coverage-audit.md
```

This report is useful for spotting seasons that have game data but are still missing rosters, player stats, usage, value metrics, honors, or rankings.

For a more player-specific backlog board, use:

```powershell
python manage.py audit-player-archive --output output\player-archive-audit.md
```

That report now does three extra things beyond raw counts:

- surfaces completely missing seasons instead of silently skipping them
- assigns each season a readiness status such as `Game shell only` or `Player context partial`
- ranks the top recovery priorities so the next historical backfill target is obvious

For structured honors and Heisman coverage specifically, use:

```powershell
python manage.py audit-awards-archive --output output\awards-archive-audit.md
```

That report is useful because it separates two very different states:

- `Heisman only`
- genuinely broader awards coverage

Right now the local archive has Heisman winners/finalists across `2014-2025`, but it does **not** yet have broad position-award, All-America, or conference-honors coverage.

### Competition integrity audit

Generate a second report aimed at correctness rather than coverage:

```powershell
python manage.py audit-competition-integrity --output output\competition-integrity-audit.md
```

This report checks:

- postseason games that spill into the next calendar year
- regular-season rows with suspicious year drift
- duplicate game signatures
- teams appearing twice on the same UTC date
- generic placeholder conference rows like `FBS`
- explicit level transitions across seasons
- latest-board placeholder contamination and cross-level peer sanity

### Repair current team identity

If `teams.level_code` or `teams.current_conference_id` drift away from the latest season-aware identity in `team_seasons`, you can repair that fallback layer with:

```powershell
python manage.py repair-team-current-identity
```

This is useful because some rendering paths still use current team identity as a fallback when a season-specific join is missing.

### CFBD connectivity preflight

Before starting a heavy CFBD-dependent job, you can now explicitly test whether the current environment can reach the API:

```powershell
python manage.py check-cfbd-connectivity --season 2025
```

The logged PowerShell wrappers now run this preflight automatically and abort before the expensive stage if connectivity or auth is broken.
The heaviest raw Python commands now do the same by default:

- `python manage.py sync-site`
- `python manage.py sync-site-incremental`
- `python manage.py backfill-cfbd-history`
- `python manage.py backfill-player-context`
- `python manage.py backfill-game-player-stats`

If you intentionally want to skip that safeguard and let the command rely on per-call failures instead, add:

```powershell
--skip-connectivity-check
```

### Full 2014-forward history load

There is now a higher-level orchestration script that chains:

1. CFBD historical game/postseason backfill
2. season-aware team/conference sync
3. historical player-context backfill
4. historical game-player-stat backfill
5. honors import if `docs\heisman_honors_2014_2025.csv` exists
6. published rebuild
7. coverage audit

Run it detached when you want the archive to keep moving without babysitting:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\load_history_2014_forward.ps1 -StartSeason 2014 -EndSeason 2025
```

This loader is now resumable. It writes a checkpoint file in `output/logs`:

- `history-load-state-<start>-<end>.json`

That state file tracks whether each season has completed:

- team/game/postseason backfill
- season-aware conference sync
- player-context backfill
- game-level player-stat backfill

and whether the global finish steps have completed:

- honors import
- published rebuild
- coverage audit

If the process stops halfway through, rerunning the same command should resume instead of starting from scratch.

You can also generate a readable progress report from the checkpoint file:

```powershell
python manage.py history-load-status --start-season 2014 --end-season 2025 --output output\history-load-status.md
```

Or use the logged wrapper if you want a stable command with a log file and optional auto-open behavior:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\safe_history_status.ps1 -StartSeason 2014 -EndSeason 2025
```

If you want one operator-facing report that merges publish health, audit artifact presence, and season-by-season archive readiness into a single markdown file, use:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\safe_archive_audit.ps1
```

That readiness report now includes copy-pasteable recovery commands for the exact current gaps, including:

- foundational season-shell recovery
- player-context backfills
- safe dry-run previews for game-level player-stat recovery
- the follow-up full game-player-stat backfill command

If you want the full local maintenance pass that regenerates every local audit, reruns the site link checker, and writes a compact summary file, use:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\safe_refresh_local_health.ps1 -StartSeason 2014 -EndSeason 2025
```

If you only want the audit suite and summary refresh without the slower built-site link crawl, add `-SkipLinkAudit`.

That report summarizes:

- which seasonal stages are complete
- which global finish steps are still pending
- how far the local archive has progressed by season
- whether the published outputs and archive audits actually exist on disk

If no resumable checkpoint exists yet, the report now falls back to inferred progress from the local archive tables and local output artifacts instead of showing an empty shell.

`safe_refresh_local_health.ps1` writes:

- `output/local-health-refresh.md`
- refreshed archive/audit markdown files in `output/`
- a logged run in `output/logs`

If the local health report says the published site is behind the newest local model snapshot, the fastest corrective action is now:

```powershell
powershell -ExecutionPolicy Bypass -File safe_publish_site.ps1
```

That wrapper:

- rebuilds `output/rankings.html`
- rebuilds `output/site`
- runs a strict internal-link audit
- leaves a timestamped log in `output/logs`

## Most important generated files

The main site outputs are:

- `output/site/index.html`
- `output/site/rankings/index.html`
- `output/site/archive/index.html`
- `output/site/conferences/index.html`
- `output/site/programs/index.html`
- `output/site/matchups/index.html`
- `output/site/compare/index.html`
- `output/site/teams/<team>.html`

If these pages regenerate successfully, the static site build is generally healthy.

## Quick verification commands

Syntax check:

```powershell
python -m py_compile src\cfb_rankings\reporting.py src\cfb_rankings\utils.py manage.py
```

Rebuild published outputs:

```powershell
python manage.py build-published
```

Check that important generated pages exist:

```powershell
Test-Path output\site\index.html
Test-Path output\site\compare\index.html
Test-Path output\site\teams\indiana.html
```

## Data source guidance

### CFBD

Use `CollegeFootballData` as the real football backbone.

Best for:

- schedules
- results
- advanced metrics
- recruiting
- returning production
- play-by-play

### SportsDB

Use `TheSportsDB` as optional enrichment.

Best for:

- badges
- logos
- artwork
- metadata polish

Do not assume it is the main source for full all-level NCAA competitive coverage.

### Conversation sources

Current validated conversation source path:

- Reddit public endpoints with browser-like headers
- RSS / Atom fallback for subreddit listing and search feeds

Practical meaning:

- the Reddit path is good enough for a constrained v1
- it should still be treated as a public-web ingestion path, not a guaranteed enterprise feed
- weekly/editorial outputs are much safer than hard real-time promises

Current follow-on sources worth adding later:

- YouTube comments and video metadata
- Apify-managed collection jobs for heavier or scheduled scraping

Known limitation:

- game-window conversation features require collection to happen near the actual game dates for the target week
- live tests against old historical weeks are still useful for weekly aggregation, but pregame/postgame windows may correctly come back empty

## Season identity reminder

Never forget this rule:

- postseason games played in January or February still belong to the season that started the previous fall

Example:

- January 2026 postseason games that decide the `2025` competitive cycle belong to `season_year = 2025`

This matters for:

- rankings
- archive pages
- team pages
- playoff pages
- historical summaries

## Important local reference files

- `README.md`
- `docs/internal-project-context.md`
- `research/feature-gap-memo-2026-04-21.md`
- `research/competitor-audit-2026-04-20.md`
- `research/model-math-spec.md`
- `research/power-model-refined-spec.md`

## Troubleshooting notes

### "Do I need PostgreSQL?"

No. Local development is using SQLite.

### "The long model command seems stuck"

Before rerunning it:

1. Ask whether new data was actually ingested.
2. If not, try `python manage.py build-published` first.
3. If the issue is just HTML / layout / generated copy, `build-published` is the right command.
4. Prefer `sync-site-incremental` over `sync-site` when catching up on weeks.
5. If you truly need to rerun models, prefer `safe_run_models.ps1` so the run is logged and flushes progress immediately.

### "The front page changed but the compare page did not"

Run:

```powershell
python manage.py build-published
```

The site is statically generated. Generated pages do not update themselves until the site build runs again.

## Practical recovery sequence

If you are starting cold and want the fastest sanity check:

```powershell
python -m py_compile src\cfb_rankings\reporting.py src\cfb_rankings\utils.py manage.py
python manage.py build-published
```

Then open:

- `output/site/index.html`
- `output/site/compare/index.html`
- `output/site/teams/indiana.html`

That gives a good quick check of:

- home page
- compare workflow
- team page workflow

## One-sentence summary

When in doubt, rebuild the static site first, rerun heavy model or ingest commands only when the underlying football data or model logic actually changed.
