# Claude Code Kickoff — Full Backfill + Autopilot

**Purpose:** one paste-in prompt that drives Claude Code end-to-end through (a) backfilling every ingestable data source from 2022-09-01 to today, (b) wiring the ingestion + scheduling + monitoring stack so the site updates itself with no manual nudging, and (c) auditing the whole system.

**How to use:** open a fresh Claude Code session in the repo and paste the block below as the first message. Claude Code will read the orientation docs, march through 9 workstreams task-by-task, commit after each, and log to `SESSION_LOG.md`. It will not ask questions — defaults are pre-decided inside the prompt.

**Expected runtime:** multi-session. The prompt is built so `/clear` between workstreams is safe.

---

```
You are shipping "CFB Index Autopilot v1" — a multi-week build that brings every
ingestable data source current from 2022-09-01 to today, turns the GitHub
Actions cron into real persistent ingestion, and self-audits so the site
updates without Kevin manually asking. You work through tasks one at a time,
commit per task, and log every outcome so `/clear` is safe between tasks.

## Read first, in this order (grep/offset — do NOT read any of these whole)

1.  CLAUDE.md                                  (repo rules)
2.  FAN_INTEL_SOURCE_STRATEGY.md               (canonical source + cohort spec)
3.  FAN_INTEL_BUILD_PLAN.md                    (8-week grid, mostly shipped)
4.  PLAYER_PAGE_WORLD_CLASS_BRIEF.md           (player page spine)
5.  PLAYER_PAGE_SEASON_PHASE_DESIGN.md §§ 1, 5, 7  (phase system)
6.  SESSION_LOG.md                             (what's already shipped — the
                                                "Player Page Data — Session Log"
                                                section is key)
7.  src/cfb_rankings/cli.py                    (read lines 1-600 — that's the
                                                full subparser surface; do not
                                                re-read beyond that range)
8.  .github/workflows/*.yml                    (four stubbed workflows; understand
                                                why they currently run as CI-only)
9.  tools/run_adapter.py                       (adapter registry)
10. migrations/*.sql + src/cfb_rankings/migrations.py
                                               (existing schema surface —
                                                skim `create table if not exists`
                                                landmarks, don't tour the file)

Do NOT read reporting.py whole (17.5k lines), fan_intelligence.py whole (811
lines) beyond 1-80 and 820-890, or migrations.py whole — grep first, targeted
reads only.

## Autonomy rules — no questions, pick defaults, move

Kevin is not on call. Do NOT use AskUserQuestion. For every decision point not
already resolved in STRATEGY / BUILD_PLAN / this prompt, apply the default
policy below and proceed, and log the call in SESSION_LOG.md so he can revisit:

- **Historical window:** 2022-09-01 through today. If a source's API only goes
  back to a later date, ingest what it supports and document the gap.
- **Classification scope:** FBS primary. Include FCS for roster / game stats
  backfills because the CFBD endpoints are cheap there, but do not block on
  D-II/D-III coverage.
- **Schema changes:** always additive — new table, new column with NULL default,
  new migration file at `migrations/YYYYMMDD_NN_description.sql`. Never DROP
  or RENAME. Never hand-edit cfb_rankings.db.
- **Adapter failure policy:** exit 0 from adapter runs so cron continues;
  `scrape_health` row carries the error. Three consecutive errors for one
  source → set `source_registry.active=0` automatically and emit a one-line
  note to `docs/audits/autopilot_followups.md`.
- **Retention policy:** Tier A/B raw text = `raw_keep` for 120 days then
  purge-to-aggregate; Tier C = `aggregated_only` from insertion; Tier D =
  `evict_after_90`.
- **Rate-limit discipline:** every adapter respects `min_seconds_between_requests`
  already set on the class. Historical backfill paces at half that speed. If
  rate limits fire anyway, back off exponentially and resume.
- **Secrets:** if a required secret is missing, the adapter short-circuits and
  writes a `scrape_health` row with `status=skipped, error_message='missing env
  FOO_API_KEY'`. Do not raise.
- **Token discipline over completeness:** if a task needs a big read, prefer a
  Haiku subagent with a tight prompt that returns a summary. Never tour a large
  file in-context just to "be thorough."
- **Editorial decisions (cohort weights, narrative voice, archetype labels):**
  do not invent new ones. Use what's in STRATEGY §4 / existing seed files.
- **Skipped sources** (STRATEGY §3 "Deliberately skipped"): do NOT try to
  ingest X/Twitter, paywalled 247/On3/Rivals, closed Discord/FB, TikTok via
  unofficial libs as a daily pipeline. These are non-negotiable.

When in doubt: ship the working version today, flag the tradeoff in the log,
keep moving.

## Model routing — enforce per task

Opus ≈ 10-12 tasks across the whole plan. Sonnet = workhorse (~60 tasks).
Haiku subagents = verification (~80 embedded checks).

- **Opus** for: new schema design, algorithmic decisions (NER tuning, cohort
  weights, PBP-derived metric definitions, draft-aggregation weights), the
  final autopilot-audit synthesis, and any cross-cutting public copy.
- **Sonnet** for: adapter code, backfill orchestration scripts, CLI
  subcommands, tests, seed YAMLs, workflow YAMLs, editorial drafts, and
  every "implement spec X" task.
- **Haiku (via Task tool subagent)** for: grep sweeps, row-count queries,
  schema diffs, format checks, per-file renames, scrape_health canaries,
  build-site diff inspection.

If a task mixes design + implementation, split it: Opus-design commit first,
then Sonnet-implement. Never let Opus do what Sonnet can ship, and never let
Sonnet verify what a Haiku subagent can verify.

## Token discipline

- `reporting.py` is 17.5k lines. Use Grep + offset+limit reads only.
- For multi-file audits, launch a Task (subagent) with a tight prompt and let
  it return a one-paragraph summary — never tour files in the main thread.
- Every task ends with a commit + a 3-line SESSION_LOG entry so `/clear`
  between tasks is safe.
- At ~60% context full: stop at the next task boundary, commit WIP, summarize,
  hand back for `/clear`.

## Repo conventions (reminder)

- New source adapters:  src/cfb_rankings/ingest/sources/{source_id}.py
- Board adapters:       src/cfb_rankings/ingest/sources/boards/{name}.py
- Cohort logic:         src/cfb_rankings/cohorts/
- Provenance helpers:   src/cfb_rankings/provenance/
- Cowork playbooks:     docs/cowork_playbooks/{name}.md
- Schema migrations:    migrations/YYYYMMDD_NN_description.sql
- Seed files:           seeds/{name}.yaml
- Tests colocated:      tests/test_{module}.py
- CLI subcommands:      extend src/cfb_rankings/cli.py
- Secrets:              env vars; .env gitignored; GH Secrets for Actions.
- Never edit output/site/**. Never hand-edit cfb_rankings.db.

## Per-task protocol (every task)

1.  Announce: "Starting TASK X.N — {name}. Model: {Opus|Sonnet}."
2.  Read only what the task needs (grep first).
3.  Implement.
4.  Verification step (Haiku subagent, pytest, row-count, or grep — declared
    in the task's "Verify" line).
5.  git commit -m "autopilot: TASK X.N — {short summary}"
6.  Append to SESSION_LOG.md:
    `YYYY-MM-DD | TASK X.N | {outcome} | {follow-ups}`
7.  Check the task's box in this file (or in the workstream tracker created
    in TASK 0.1).
8.  Move to the next task, or stop if a stop condition triggers.

## Stop conditions

- End of each workstream (W1..W9 boundary). Commit, summarize, hand back.
- Context >60% full → stop at next task boundary, commit, summarize.
- 3 consecutive adapter failures with the same error class → stop, summarize,
  file a follow-up, move on to the next workstream.
- A migration would DROP or RENAME an existing column or table → stop, write
  the analysis to docs/audits/autopilot_followups.md, move on.

## When to escalate to SESSION_LOG (not AskUserQuestion)

- Cohort weights need to change (STRATEGY §4).
- A source not in STRATEGY §3 deserves adding.
- A decision materially changes a published number or methodology page.
- Anything that could break `./publish_site.ps1`.
- Any edit to reporting.py beyond a surgical change at a known line.

Log the decision and the tradeoff, ship the safe default, move on.

========================================================================
WORKSTREAM 0 — Orientation + data inventory
========================================================================

### TASK 0.1 — Read-first + progress tracker (Sonnet)
Read CLAUDE.md, STRATEGY, BUILD_PLAN, PLAYER_PAGE_WORLD_CLASS_BRIEF, last 60
lines of SESSION_LOG.md, cli.py lines 1-600. Open
`docs/audits/autopilot_progress.md` and write a 9-workstream checklist
matching this prompt, one unchecked box per task. Every task-close step
will tick the box.
Verify: Haiku subagent confirms the checklist line-count matches 9
workstreams × N tasks.

### TASK 0.2 — DB inventory (Sonnet + Haiku)
Write `docs/audits/data_inventory_YYYY-MM-DD.md`. For every table in
cfb_rankings.db that touches player / team / conversation / market / honor /
advanced-stat data, print: row_count, min/max of the primary date column (if
any), seasons covered, source_name breakdown. Use one single sqlite
introspection pass (the script should complete in <20s; keep it cheap).
Include a "gap summary" section: which seasons 2022/2023/2024/2025/2026 are
under-covered per table.
Verify: Haiku subagent re-runs the exact queries from the report, confirms
counts, flags any row-count discrepancy.

### TASK 0.3 — Scrape-health baseline (Haiku subagent)
Launch a Haiku subagent that runs `python manage.py scrape-health --since-days 30`,
`python manage.py fanintel-status`, `python manage.py validate-feed-urls`,
captures the output, and returns a 200-word summary. Paste the raw output
into `docs/audits/scrape_health_baseline.md`. This is the "before" snapshot
the final audit compares against.

========================================================================
WORKSTREAM 1 — CFBD deep backfill (the on-field foundation)
========================================================================

Goal: every CFBD-derivable table has rows from 2022-09-01 to today. PBP
data ingested. Advanced metrics derived. Existing CLIs do most of the
heavy lifting — this workstream is largely orchestration.

### TASK 1.1 — Connectivity preflight (Haiku subagent)
Run `python manage.py check-cfbd-connectivity --season 2025`. Confirm API
key present, Patreon tier active, endpoints respond. If it fails, stop this
workstream and move to W2 (do not block the whole plan on CFBD).

### TASK 1.2 — Full CFBD history backfill, 2022-2025 regular + postseason (Sonnet)
Run `python manage.py backfill-cfbd-history --start-season 2022 --end-season 2025
--include-postseason --skip-heisman`. This covers games, lines, drives, plays,
advanced game stats, weather, talent, returning production, recruiting class
data, transfers, roster snapshots. Use `--skip-connectivity-check` if 1.1
already passed. Spread across multiple Actions runs if needed (the CLI is
idempotent — re-run if a week errors).
Verify: Haiku subagent greps row counts per season in `games`, `game_plays`,
`game_drives`, `player_season_stats`, `player_value_metrics`; every season
should have >9,000 games*plays, >10,000 player_season_stats rows.

### TASK 1.3 — 2026 in-season + offseason refresh (Sonnet)
Run `python manage.py ingest-cfbd-preseason --season 2026 --all-season-teams
--classification fbs` and `--classification fcs`. Follow with
`python manage.py backfill-game-player-stats --start-season 2022 --end-season 2026
--include-postseason --missing-only`. Existing rows are preserved via upsert.
Verify: Haiku subagent row-counts `player_game_stats` before/after.

### TASK 1.4 — PBP-derived advanced metrics table (Opus design; Sonnet implement)
**Design (Opus):** the kickoff player-data doc flagged that we lack
EPA/dropback, CPOE, pressure-to-sack, 3rd-down EPA, red-zone TD rate,
aDOT, deep-ball accuracy — all computable from `game_plays` but not yet
persisted. Design migration
`migrations/YYYYMMDD_01_player_advanced_metrics.sql` with a
`player_advanced_metrics` table keyed on
`(player_id, season_year, week, metric_id)` plus `value`, `sample_size`,
`cohort_id`, and a companion `player_advanced_metrics_season` rollup.
Include at minimum these metric_ids: `epa_per_dropback`,
`epa_per_dropback_under_pressure`, `cpoe`, `pressure_to_sack_rate`,
`third_down_epa`, `red_zone_td_rate`, `adot`, `deep_ball_accuracy_20plus`,
`play_action_epa_split`, `scramble_epa`, `turnover_worthy_play_rate`,
`success_rate`, `explosive_play_rate_20plus`. RB/WR variants where the
PBP supports them.
**Implement (Sonnet):** `src/cfb_rankings/metrics/player_advanced.py`
reads `game_plays` + `game_player_stats` and produces rows. CLI
`python manage.py compute-player-advanced --season YYYY [--week N]`.
Idempotent upsert. Tests in `tests/test_player_advanced.py` with synthetic
play fixtures covering each metric's math.
Verify: Haiku runs tests + a 1-week live smoke + confirms CJ Carr
(player_id 4788) has all 13 metric rows for 2025.

### TASK 1.5 — Advanced metrics backfill 2022-2025 (Sonnet)
Loop `compute-player-advanced --season YYYY` for 2022, 2023, 2024, 2025, 2026.
Include postseason where applicable. Write timing summary to
SESSION_LOG.
Verify: Haiku subagent row-counts per season, compares to row counts in
`player_season_stats` (same player-seasons should appear in both).

### TASK 1.6 — Extend Signature Story seed with PBP metrics (Opus seed, Sonnet smoke)
**Design (Opus):** append QB metrics from TASK 1.4 to
`seeds/signature_story_metrics.yaml` with defensible `narrative_weight`
values (pressure/situational beats raw rate, per the v1 ordering). Add a
cohort `p4_qbs_min_80_dropbacks` keyed on the new table.
**Implement (Sonnet):** run `scripts/validate_signature_story_seed.py` +
regenerate the Signature Story index via `compute-signature-story` then
rebuild one player page.
Verify: Haiku opens Carr's page (`output/site/players/cj-carr-4788.html`),
confirms the signature stat updated to a PBP-backed one; opens 3 other
QB pages, spot-checks that the new metrics appear in the scoreboard drawer.

### TASK 1.7 — Weekly CFBD auto-refresh wiring (Sonnet)
Edit `.github/workflows/ingest_hourly.yml`: replace the `init-db` ephemeral
step with a DB-artifact fetch/restore pattern (see W8.1). Add a conditional
step that, during CFB season (Aug-Jan), calls
`python manage.py sync-site-incremental --season $YEAR --through-week $WEEK`
where the week is computed from today's date. Outside season, no-op.
Verify: Haiku dry-runs the workflow file through `actionlint` (pip
install actionlint-py or skip if unavailable and just schema-check manually).

========================================================================
WORKSTREAM 2 — Conversation corpus backfill (2022→today)
========================================================================

Goal: Reddit from 2022-09-01 to today, Bluesky from 2023-11 to today,
message boards 90 days back via their archives, every RSS family
flowing forward and backfilled via site search where possible.

### TASK 2.1 — Reddit historical plan (Opus)
Design `seeds/reddit_historical_plan.yaml`: per priority team, list
(team_subreddit, alumni_subreddit, city_subreddit) and date ranges
2022-09-01 → today partitioned into 7-day windows. Include r/CFB
sitewide as its own row. Specify provider preference — arctic-shift
first (more complete), pullpush fallback (denser for recent). Total
windows should be ~10k (20 teams × 3 subs × ~150 weeks + r/CFB).
Verify: Haiku subagent sanity-checks row count + YAML parses cleanly.

### TASK 2.2 — Reddit backfill runner (Sonnet)
Implement `scripts/backfill_reddit_history.py` that reads the plan and
loops `collect-reddit-plan` per window with `--provider arctic-shift`
then retries failed windows with `--provider pullpush`. Checkpoints
to `data/reddit_backfill_state.json` so resuming after a crash only
replays the unfinished windows. Exponential-backoff on 429. Writes
`scrape_health` row per window. Targets ~500-2000 rows/window.
Verify: Haiku subagent runs the script with `--dry-run` flag, confirms
no DB writes and correct window plan iteration.

### TASK 2.3 — Execute Reddit backfill (Sonnet, long-running)
Run `python scripts/backfill_reddit_history.py --commit`. Expect 8-24h
runtime depending on provider throttling. On any single-window
3-consecutive-fail, skip that window, log, continue. On finish, run
`python manage.py build-conversation-features` for every (season, week)
from 2022-01 through current — loop in the same script.
Verify: row count in `conversation_documents` jumps from ~4,869 to
~500k-2M; Haiku subagent confirms season_year distribution makes
sense (no huge 2024 hole, etc.).

### TASK 2.4 — Bluesky historical backfill (Sonnet)
Bluesky started late 2023. Run the existing `BlueskyCuratedAdapter` +
`BlueskyFeedsAdapter` in a loop with date cursors 2023-11 → today. The
AppView exposes historical via `getAuthorFeed`'s `cursor` param. Add
`scripts/backfill_bluesky_history.py` for the cursor loop. Respect the
1 req/sec soft limit.
Verify: Haiku confirms `conversation_documents.source_name='bluesky'`
rows appear with `ingested_at` timestamps spread across the full window.

### TASK 2.5 — Message board backfill (Sonnet, per-board)
For each existing board adapter (Tigerdroppings, ShaggyBevo, VolNation,
TideFans, Eleven Warriors), add a `.backfill(since_days=...)` method that
paginates the public thread index back 90 days. Run once per board; target
~500 threads each. Do NOT scrape paywalled content or private threads.
Verify: Haiku subagent counts per-source rows in `conversation_documents`;
spot-checks 5 random threads for quote pseudonymization and backlink
correctness.

### TASK 2.6 — RSS-family activation (Sonnet)
The following adapters exist as code but have no seed rows:
`beat_writers`, `substack`, `podcasts_meta`. Seed
`seeds/beat_writer_feeds.yaml`, `seeds/substack_feeds.yaml`,
`seeds/podcast_feeds.yaml` are already on disk — run
`python manage.py seed-feed-instances` to expand them into
`source_registry` rows. Then run each adapter family through
`tools/run_adapter.py` (bulk bulk-families pattern). RSS windows are
limited to recent items, so historical coverage is whatever the feed
exposes — that's acceptable.
Verify: Haiku row-counts `conversation_documents` per source, checks
5 sources have status=ok in `scrape_health`.

### TASK 2.7 — Google News RSS activation (Sonnet)
Run `python tools/run_adapter.py google_news_all` for every priority
team. Each row should produce ~10-40 docs.
Verify: Haiku confirms 20 teams × >10 docs = >200 rows.

### TASK 2.8 — Podcast ASR selective (Sonnet — optional)
Pick 5 flagship shows (Finebaum, Josh Pate, Bruce Feldman, Ari Wasserman,
Cover 3). For each, run `python tools/transcribe_episode.py` on the
3 most-recent episodes. Store transcripts with `source_tier='D'` for
citation-only use. Skip if whisper.cpp/ffmpeg not available — log and
continue.
Verify: Haiku checks stored transcript length > 1k chars, source_tier
label correct.

========================================================================
WORKSTREAM 3 — Tier-A numeric observation backfill
========================================================================

Goal: every Tier-A numeric source either has historical rows back to
2022-09-01 (where the API supports it) or is flagged "live-only start".

### TASK 3.1 — Wikipedia pageviews + edits backfill (Sonnet)
Wikimedia REST supports 2015→ for pageviews. Adapt
`WikipediaPageviewsAdapter` + `WikipediaEditsAdapter` to accept
`start_date` and `end_date` kwargs. Loop back to 2022-09-01 per tracked
entity. Target: 20 teams × 3 pages × ~1300 days ≈ 78k rows.
Verify: Haiku row-counts by entity; confirms ND team page has ~1300
daily rows.

### TASK 3.2 — GDELT volume backfill (Sonnet)
GDELT 2.0 exposes historical via the Doc API (`mode=artlist&timespan=2y`
goes back 2 years hard cap). For pre-2024 coverage, use GDELT's
full-archive BigQuery export mirror if available; otherwise accept the
2-year window and log. Adapt `GdeltVolumeAdapter` for date-range loops.
Verify: Haiku row-counts, confirms one row per (entity, day) for the
last 730 days.

### TASK 3.3 — Prediction markets historical (Sonnet)
Kalshi + Polymarket both expose historical trade/quote data via their
APIs. For each CFB market listed in `seeds/prediction_market_contracts.yaml`
(Heisman futures, CFP winner, conference titles, regular-season props),
pull daily close prices + volume back to contract open.
Verify: Haiku confirms Heisman-favorite contracts have daily series
going back to at least January 2026; CFP 2025 futures go back further
if available.

### TASK 3.4 — SeatGeek live start (Sonnet)
Historical ticket prices are not exposed via the SeatGeek API (no
backfill possible). Start live daily ingestion for upcoming 2026 games.
Confirm SEATGEEK_CLIENT_ID in .env.
Verify: Haiku runs one adapter call, confirms >0 rows for future home
games of top-20 priority teams.

### TASK 3.5 — YouTube metadata live start (Sonnet)
Historical video metadata IS accessible via the Data API but comment
streams are expensive (quota-heavy). Start live daily for team channels
+ top fan channels. No backfill beyond "most recent 50 videos per
channel" at activation.
Verify: Haiku confirms YOUTUBE_API_KEY present, 1-channel smoke run
returns >10 videos.

### TASK 3.6 — Spotify charts weekly start (Sonnet)
Spotify's chart history is thin (~1 year at best). Start weekly
collection. No backfill.
Verify: Haiku runs one adapter call, confirms chart snapshot landed.

### TASK 3.7 — Google Trends weekly (Cowork — playbook only)
STRATEGY §3 says Google Trends is Cowork-manual (no programmatic API
for DMA export). Confirm `docs/cowork_playbooks/trends_weekly.md`
exists and is current. If it doesn't reference 2026 URL paths, update.
Verify: Haiku reads the playbook end-to-end, confirms step-count ≥10.

========================================================================
WORKSTREAM 4 — Honors, awards, draft, NIL backfill
========================================================================

Goal: `player_honors` populated for 2022-2025 with every NCAA-recognized
All-America selector, every All-Conference team, every position award
winner + finalists, every Freshman AA team. Draft results landed.
Mock-draft adapters live. NIL where public.

### TASK 4.1 — All-America scraper (Sonnet)
Wikipedia maintains clean tables at "YYYY College Football All-America
Team" for every year back decades. Build
`src/cfb_rankings/ingest/sources/all_america_wikipedia.py` that parses
those tables for 2022, 2023, 2024, 2025 and emits CSV rows compatible
with `import-player-honors`. Selectors: AP, AFCA, FWAA, Sporting News,
Walter Camp (the 5 NCAA-recognized), plus SI, The Athletic, USA Today,
ESPN, CBS, PFF, CFN, Athlon, Phil Steele (the additional 9 for
Consensus/Unanimous computation). Resolve `player_id` via
`players.canonical_name` + team name; write stub player rows if needed
(STRATEGY allows this — `_ensure_stub_player_id` exists in
`ingest/honors.py`).
Verify: Haiku subagent opens the resulting CSV, confirms 2025 has
~50 unique players × 5-14 selector rows; runs
`python manage.py import-player-honors --csv <output>.csv`, counts
new player_honors rows.

### TASK 4.2 — All-Conference scraper (Sonnet)
For each P4 conference (SEC, B1G, ACC, Big 12) + Group of 5 (AAC,
Mountain West, Sun Belt, MAC, Conference USA), scrape the
conference's "YYYY All-{Conference} Football Team" Wikipedia page
or the league's official media/coaches release for 2022-2025.
Produce CSV, import via existing CLI.
Verify: Haiku confirms ~50 players × conference × year rows.

### TASK 4.3 — Position awards backfill (Sonnet)
The 12 major position awards: Davey O'Brien, Manning, Maxwell, Walter
Camp, Outland, Biletnikoff, Mackey, Thorpe, Groza, Guy, Nagurski,
Bednarik. Wikipedia has winner+finalist lists per award per year.
Scraper emits CSV with `honor_scope='position_award'`,
`honor_name=<award>`, `placement='winner'|'finalist'`.
Verify: Haiku checks 2024 Heisman winner (expected: Travis Hunter)
appears once; 2023 Heisman winner (Jayden Daniels) appears once;
finalists are 3-5 per year per award.

### TASK 4.4 — Freshman AA + Shaun Alexander (Sonnet)
FWAA Freshman All-America + Shaun Alexander FOY + On3 / 247 freshman
teams for 2022-2025. Import via same CSV pipeline with
`honor_scope='freshman_aa'`.
Verify: Haiku row-count.

### TASK 4.5 — NFL Draft backfill (Sonnet)
Wikipedia's "YYYY NFL Draft" articles + sports-reference.com/cfb/draft
give full pick lists. Build `src/cfb_rankings/ingest/draft.py` with a
`player_nfl_draft` landing table (new migration) keyed on
`(player_id, draft_year, round, pick, team_id)`. Back to 2022 draft.
Verify: Haiku runs `select count(*), round from player_nfl_draft
group by round` — 32 picks × 7 rounds × 4 years ≈ 900 rows.

### TASK 4.6 — Mock draft adapter (Sonnet)
Kiper (ESPN), Jeremiah (NFL.com), Walter (WalterFootball), CBS Sports
publish public mock drafts. Build
`src/cfb_rankings/ingest/sources/draft_boards/{source}.py` adapters
per PLAYER_PAGE_SEASON_PHASE_DESIGN.md §11. Landing table
`player_draft_projection` (new migration) with
`(player_id, source_id, snapshot_date, projected_round, projected_pick,
projected_team_id, overall_rank)`. Daily cron during draft week,
weekly otherwise.
Verify: Haiku confirms at least 3 sources × 30 projections for the
current 2026 class; schema present.

### TASK 4.7 — NIL valuations snapshot (Sonnet — best effort)
On3's NIL valuation pages are public. Build
`src/cfb_rankings/ingest/sources/on3_nil.py` that fetches the top-500
NIL valuation list weekly. No historical backfill (only current
snapshots are exposed). Landing table `player_nil_snapshot` keyed on
`(player_id, snapshot_date)`.
Verify: Haiku confirms 500-row snapshot landed; CJ Carr appears.

### TASK 4.8 — Watch lists ingestor (Sonnet)
Heisman Trophy Trust + Davey O'Brien Foundation + Manning Award +
Walter Camp + Maxwell Award publish preseason watch lists and
midseason trim lists. Build
`src/cfb_rankings/ingest/sources/watch_lists.py`. Backfill 2022-2025
rosters from their archives. Treat as Tier A numeric (rank only) +
Tier B citation. Write to `player_honors` with
`honor_scope='watch_list'`.
Verify: Haiku confirms 2025 Heisman watch list has ~50 names.

========================================================================
WORKSTREAM 5 — Player-mention extraction at scale
========================================================================

Goal: `conversation_document_targets.player_id` goes from 0 → tens of
thousands. Every corpus document tagged with every player it references.
`player_week_conversation_features` populated for every week. The Room
on [Player] lights up for players who clear the floor.

### TASK 5.1 — Dry-run the tagger on the full corpus (Sonnet)
Run `python manage.py tag-player-mentions --season 2026 --preview`
against the current ~4,869 docs (offseason only). Capture mention
counts + precision spot-check from the preview snippets.
Verify: Haiku subagent samples 20 random preview lines, flags any
false positives. If precision <0.9, stop and escalate to TASK 5.2.

### TASK 5.2 — Tagger tuning (Opus) — only if 5.1 precision <0.9
Open `src/cfb_rankings/ingest/player_name_tagger.py`. Tighten rules:
strengthen team-name blocklist, add coach-name blocklist (from
`coaching_changes` table), raise last-name-only confidence floor,
add nickname seed file `seeds/player_nicknames.yaml` for the top-100
headline players. Re-dry-run. If still <0.9, switch to full-name-only
matching and accept the recall hit.
Verify: Haiku re-samples 20 preview lines; precision ≥0.95.

### TASK 5.3 — Commit tagger run on full corpus (Sonnet)
Once 5.1/5.2 pass: `python manage.py tag-player-mentions --season 2026 --commit`
+ loop over 2022, 2023, 2024, 2025 as Reddit backfill from W2.3 lands.
Runtime: ~5-15 min per season.
Verify: Haiku runs
`select count(*) from conversation_document_targets where target_type='player'
group by season_year` — should show rows in every season with Reddit coverage.

### TASK 5.4 — Compute player mood weekly + season rollups (Sonnet)
Loop:
  for season in 2022..2026:
    for week in 1..17:
      python manage.py compute-player-week-mood --week={season}-{week:02d}
    python manage.py compute-player-season-mood --season {season}
Write to SESSION_LOG per season: rows_written, players_touched.
Verify: Haiku row-counts `player_week_conversation_features` by season.

### TASK 5.5 — Rebuild player pages + spot-check (Sonnet)
Run `python manage.py build-site`. Verify Carr's page
(`output/site/players/cj-carr-4788.html`) now renders a NON-empty
`.the-room` card (belief dial, cohort pills, top quote).
Verify: Haiku opens 5 pages (high-mention QB, mid-mention RB, rare-mention
OL, walk-on, freshman) and confirms each renders the correct state
(live / partial / empty).

### TASK 5.6 — The Room board + Signature Story board (Sonnet)
Run `python manage.py build-the-room-board --season 2026 --week 16`
and `python manage.py build-signature-story-board --season 2025`.
Also `python manage.py build-players-landing --season 2026 --week 16`.
Verify: Haiku checks `/players/the-room.html`,
`/players/signature-stories.html`, `/players/spotlight.html` exist
with >0 entries each.

========================================================================
WORKSTREAM 6 — Fan Intelligence aggregation backfill
========================================================================

Goal: team-scope + cohort aggregates + divergence + Hub v5 data
backfilled for every week 2022-01 through current.

### TASK 6.1 — Team weekly features (Sonnet)
Loop:
  for (season, week) in every week where conversation_documents has rows:
    python manage.py build-conversation-features --season N --week W
Record timing per season.
Verify: Haiku row-counts `team_week_conversation_features`.

### TASK 6.2 — Cohort aggregation backfill (Sonnet)
Loop `python manage.py compute-cohort-week --week=YYYY-WW` for every
ISO week covered by `conversation_documents.ingested_at` since
2022-09-01.
Verify: Haiku spot-checks 2025-22 divergence > 0 once multi-source
coverage is real (if divergence is still 0, it means one source still
dominates — log follow-up, don't block).

### TASK 6.3 — Divergence backfill (Sonnet)
Loop `python manage.py compute-divergence --week=YYYY-WW` across the
same range.
Verify: Haiku row-counts `team_cohort_divergence_week`.

### TASK 6.4 — Hub v5 weekly data (Sonnet)
`python manage.py classify-fanbases --season 2025 --backfill-history 3`
+ per-week `compute-mood-week`, `compute-rivalry-ratios`, `mine-lexicon`
for the current-season window plus the retro weeks already seeded.
Verify: Haiku opens `/hub/index.html`, confirms the 12 v5 sections
have real data.

### TASK 6.5 — Storylines refresh (Sonnet)
If `conversation_storylines` is a code path that already exists (grep
`conversation_storylines`), run the extraction CLI for every week.
Otherwise log that it's a follow-up and move on.
Verify: Haiku row-counts.

========================================================================
WORKSTREAM 7 — Phase-aware site + offseason modules (player page P.1+)
========================================================================

Goal: the offseason-hotfix P.0 banner becomes dynamic; 2026 Outlook +
Development Trajectory + Draft Day Live + Portal Status + Career-done
states all render. Signature Bets texture layer (Phase S1 voice items)
lands. Methodology page linked from global nav.

### TASK 7.1 — Phase detection (Sonnet)
Build `src/cfb_rankings/season_phase.py` per
PLAYER_PAGE_SEASON_PHASE_DESIGN.md §15 P.1. Function
`current_phase(today: date) -> SeasonPhase`. Unit tests at every phase
boundary (mid-Dec flip, mid-Jan flip, early-April flip, draft-week flip,
May flip, July flip, mid-Aug flip).
Wire into `_assemble_player_page_data` so `phase` is a data-dict field.
Replace hard-coded P.0 banner text in reporting.py with
`_render_phase_banner(phase)`.
Verify: Haiku checks reporting.py diff is single-function scope;
runs `build-site`; opens Carr page on today's date and confirms
banner reads `OFFSEASON · SPRING 2026 · DRAFT WEEK`.

### TASK 7.2 — Offseason Status chip + 2026 Outlook module (Sonnet)
Per §8.1 + §9 of the phase-design doc. Add a `season_phase/offseason_status.py`
resolver that looks at `roster_week`, transfer rows, draft declarations,
honors to produce one of the 15 states. Render into the hero identity
strip.
Build `_render_outlook_card` with 5-7 cells driven by: recruiting
profile + transfer profile + mock-draft consensus (from W4.6) + NIL
(W4.7) + watch-list (W4.8) + team 2026 outlook (from rankings).
Verify: Haiku opens Carr (returning junior), opens a graduating senior,
opens a portal player, opens a freshman signee — 4 distinct states
render correctly.

### TASK 7.3 — Development Trajectory module (Sonnet)
Pre-compute `player_season_summary` aggregating per-season CFB Index
score + milestone markers (recruit, redshirt, first start, All-Conf,
AA, POTY finalist). Render line chart via reporting.py (SVG generation
in-template, no JS required for fallback).
Verify: Haiku checks 3 veteran pages render the chart; freshman page
renders the single-point variant; walk-on renders the empty state.

### TASK 7.4 — Methodology page global-nav link (Opus single-edit, Haiku diff)
**Opus:** open reporting.py at `_site_nav(...)` (grep for it), add a
"Methodology" link. Coordinate with any existing nav tuples at lines
~11717-11723.
**Verify (Haiku):** diff shows a single-function edit; build-site
passes; every page's global nav now includes the link.

### TASK 7.5 — Phase S1 voice layer (Sonnet)
Ship the ambient enhancements from PLAYER_PAGE_SIGNATURE_BETS.md §8
Phase S1: FI Glossary `?` icons (using `seeds/fi_glossary.yaml`
already on disk), inline confidence chips on every metric, era
context strings on record stats, tabular-nums rhythm rule
enforcement (CSS pass only), and the What-Changed client-side diff.
Verify: Haiku loads Carr page, counts `?` icons ≥ 8, confirms
confidence chips render on every stat row.

### TASK 7.6 — Draft Day Live skeleton (Sonnet)
Conditional module — renders only for players in the declared draft
class during the 72-hour window AND when phase == DRAFT. Pre-draft
state only this cycle (countdown + mock consensus + 3 team-fit
scenarios). Live polling is a 2027 stretch; ship the static-render
path now so the module is defined.
Verify: Haiku opens a 2026 declared player's page, confirms card
renders with the countdown + mock band.

========================================================================
WORKSTREAM 8 — Autopilot: real persistence + scheduling + monitoring
========================================================================

Goal: GitHub Actions actually persist data, not reset to fresh schema
every run. Scheduled site rebuilds. Alerts fire. Methodology page
self-updates. This is the workstream that makes all prior work
auto-refresh.

### TASK 8.1 — DB persistence strategy (Opus decision, Sonnet wire)
**Decide (Opus):** the current Actions workflows `init-db` every run.
Three options: (a) upload/download cfb_rankings.db as a Workflow
artifact (retention 90d), (b) push compressed DB to a private GCS/S3
bucket, (c) run ingestion on a small always-on VM (Kevin's PC or a
cheap VPS) via Tailscale + a pull-task runner.
**Default:** (a) — cheapest, already-available, 90-day retention is
fine because the DB is also Kevin's local source of truth; runner
pulls artifact, runs adapters, uploads new artifact.
**Implement (Sonnet):** update every workflow in `.github/workflows/*.yml`
with the download → run → upload pattern. Handle "no prior artifact"
bootstrap.
Verify: Haiku workflow_dispatch-triggers `fanintel-ingest-hourly`;
confirms artifact uploaded; second run reuses it.

### TASK 8.2 — Seed + migrate on every workflow bootstrap (Sonnet)
Replace `init-db` with `apply-migrations` + `seed-source-registry` +
`seed-priority-teams` + `seed-feed-instances` — idempotent and safe
whether the DB is fresh or pre-loaded. Done across all four workflows.
Verify: Haiku checks workflow YAMLs for the init-db → apply-migrations
swap.

### TASK 8.3 — Adapter orchestrator (Sonnet)
Create `scripts/run_all_adapters.py` with tiers:
- hourly: kalshi, polymarket, gdelt_volume, bluesky_curated,
  bluesky_feeds, google_news_all, youtube_meta (if secret), seatgeek
  (if secret), reddit collection during season, CFBD incremental
  sync during season.
- daily: wiki_pv, wiki_edits, campus_news_all, athletics_all,
  locked_on_all, beat_writers_all, substack_all, draft_boards
  (during draft week, weekly otherwise), nil_on3.
- weekly: spotify_charts, all-america scrapers (monthly during
  in-season, weekly Dec-Jan), compute-cohort-week,
  compute-divergence, compute-player-week-mood, build-methodology,
  build-site.
Each tier exits 0 overall; each adapter writes its own
`scrape_health` row. Replace the per-adapter workflow steps with
`python scripts/run_all_adapters.py --tier=hourly|daily|weekly`.
Verify: Haiku dry-runs each tier locally; confirms all called CLIs
exist; confirms weekly tier ends with build-site.

### TASK 8.4 — scrape_health alerting (Sonnet)
Extend `scripts/run_all_adapters.py` to, at the end of each run,
query for sources with 3 consecutive `error` statuses and file a
GitHub Issue via `gh issue create` (or if gh not available, append
to `docs/audits/autopilot_followups.md` under a dated heading).
Also mark `source_registry.active=0` for those sources.
Verify: Haiku injects a synthetic 3-fail history for one source,
runs the orchestrator, confirms the follow-up line lands.

### TASK 8.5 — Weekly site rebuild + publish (Sonnet)
Add `.github/workflows/publish_site.yml` cron: every Monday 11:00 UTC
(~06:00 ET). Steps: download DB artifact, run
`python manage.py sync-site-incremental --season 2026 --through-week $WK`
if in-season, else `python manage.py build-site`. Commit output/site/**
to a `published` branch (or push to the S3/Cloudflare destination
configured in `publish_site.ps1`). Upload new DB artifact.
Verify: Haiku workflow_dispatch-triggers the publish; confirms commits
land on `published` branch.

### TASK 8.6 — Monthly deep-research refresh trigger (Sonnet)
Add `.github/workflows/deep_research_monthly.yml` cron: 1st of the
month. Emits an issue "Deep Research refresh due — see
STRATEGY §7" with the stock prompts from
`research/deep_research_refresh_*.yaml`. No automation of the research
itself — that's Kevin's ChatGPT/Claude Research loop.
Verify: Haiku confirms issue template renders.

### TASK 8.7 — Freshness page (Sonnet)
Add `/methodology/freshness.html` auto-generated from `scrape_health`:
"Last successful run per source, per Tier." Rebuilds in the weekly
publish. Linked from the methodology page + global nav.
Verify: Haiku opens the page, confirms all 37 source_registry rows
listed, timestamps correct.

### TASK 8.8 — Autopilot dashboard CLI (Sonnet)
`python manage.py autopilot-status` prints a one-screen dashboard:
source_registry counts by tier + active/inactive, scrape_health
last-run summary, row-count deltas over the last 7 days for
conversation_documents / player_week_conversation_features /
player_advanced_metrics, site last-built-at, any sources over
the 3-fail threshold. Kevin runs this when he wants a read of
the system.
Verify: Haiku runs the CLI, confirms output < 80 lines, no errors.

========================================================================
WORKSTREAM 9 — End-to-end audit
========================================================================

### TASK 9.1 — Autopilot v1 audit (Opus synthesis + multi-Haiku verification)
Produce `docs/audits/autopilot_v1_audit.md` confirming:

1. Every source in STRATEGY §3 has a `source_registry` row, an adapter,
   and either rows in `scrape_health` (live) or a documented "live-only
   start — no backfill available" line.
2. `conversation_documents.season_year` distribution shows real coverage
   2022, 2023, 2024, 2025, 2026 (each ≥ 50k rows).
3. `conversation_document_targets` has `target_type='player'` rows in
   every season Reddit covers.
4. `player_week_conversation_features` has rows for every (season, week)
   where target rows exist.
5. `player_advanced_metrics` has rows for 2022-2026.
6. `player_honors` has rows for every honor scope from W4 for 2022-2025.
7. `player_nfl_draft` populated for 2022-2025.
8. `player_draft_projection` has ≥ 3 source rows per top-100 2026 prospect.
9. The 4 GitHub Actions workflows upload & re-download the DB artifact
   (confirmed by triggering each via workflow_dispatch).
10. `publish_site.yml` has successfully published a rebuild within the
    last 7 days.
11. At least one team page shows a divergence > 0 (proves multi-source
    FI is working).
12. CJ Carr's page renders live `.the-room`, populated `.algorithmic-signature`,
    non-empty `.outlook`, and the phase banner reflects today's phase.
13. `/methodology/fan-intelligence.html` and `/methodology/freshness.html`
    are both live and linked from global nav.
14. Synthetic 3-fail test triggers the alert path from W8.4.

For each check, a Haiku subagent runs the verification and returns
pass/fail + the one-line evidence. Opus synthesizes the audit doc from
those subagent reports.

Verify: the audit doc ships; follow-up table enumerated for every fail;
kevin gets a one-screen "here's what's live, here's what's on the
follow-up list" summary at the top of the doc.

========================================================================
Begin
========================================================================

Start with TASK 0.1 (orientation + progress tracker — Sonnet).
If SESSION_LOG.md already exists (it does), append; do not overwrite.
After each task: commit, log, tick box, check stop conditions, pick
the next task.

You are authorized to work autonomously through W0 → W9. Do not pause
for Kevin unless a stop condition triggers. If in doubt, pick the
documented default, log the tradeoff, keep moving.
```

---

## Operator notes (not part of the paste-in)

### What this kickoff is
The single largest kickoff Kevin has written. It consolidates three earlier kickoffs (fan intel build, player data, player mentions) plus the offseason hotfix and the autopilot gap identified in SESSION_LOG.md's Week 2 BLOCKED entry. Everything from CFBD PBP backfill to mock-draft aggregators to real GitHub Actions persistence is in one plan.

### Why Claude Code can run it without me on call
Every decision point that used to trigger an AskUserQuestion has a pre-decided default in the "Autonomy rules" section. The prompt tells Claude Code to log the decision and keep moving instead of blocking. Kevin can audit the tradeoffs in `SESSION_LOG.md` + `docs/audits/autopilot_followups.md` after the fact.

### Model routing, in practice
~10-12 Opus tasks: T1.4 design, T1.6 seed, T2.1 plan, T5.2 tagger tuning (conditional), T7.4 single nav edit, T8.1 persistence decision, T9.1 synthesis. Everything else Sonnet or Haiku-subagent. This keeps the Claude Max spend disciplined.

### Realistic timeline
- W0 + W1.1/1.2/1.3: 1 session (orientation + CFBD backfill kickoff).
- W1.4-1.7 (PBP metrics + seed): 1-2 sessions.
- W2 (conversation backfill): Reddit historical run is 8-24h compute time — start it, `/clear`, come back.
- W3 (Tier-A numeric): 1 session.
- W4 (honors/draft/NIL): 2-3 sessions.
- W5 (player mentions): 1 session once W2 has landed.
- W6 (FI aggregation): 1 session.
- W7 (phase + offseason modules): 2-3 sessions.
- W8 (autopilot): 1-2 sessions.
- W9 (audit): 1 session.
Rough total: 12-15 Claude Code sessions spread across 2-3 weeks.

### What to do if it goes off the rails
- Look at the last log line in SESSION_LOG.md. Every task has a 3-line outcome + follow-ups.
- Check `docs/audits/autopilot_followups.md` — every deferred decision lands here.
- If a workstream is blocked on a hard error, skip to the next workstream — they're mostly independent. Come back later.

### One deliberate gap
Twitter/X, paywalled 247/On3/Rivals, private Discord/FB, and TikTok-as-daily are NOT in the plan. STRATEGY §3 excludes them for ToS/price/ethics reasons, and the kickoff enforces that. If Kevin ever changes his mind, those become a new workstream, not a patch to this one.
