# Fan Intelligence — 8-Week Build Plan

**Status**: execution. Reference: `FAN_INTEL_SOURCE_STRATEGY.md`. Check off tasks as they ship. Append results to `SESSION_LOG.md`.

---

## Model routing (enforce per task)

| Task shape | Model | Why |
|---|---|---|
| Schema design, cohort-weight decisions, architectural choices | **Opus** | High-consequence, hard-to-change, judgment-heavy |
| Implementing a specified feature, one adapter, tests, editorial copy | **Sonnet** | Well-scoped implementation work — the workhorse |
| Grep sweep, file listing, rename, format check, diff review, canary | **Haiku** (via subagent) | Save main-thread tokens; Haiku is accurate enough for verification |

Rule of thumb: Opus designs, Sonnet implements, Haiku verifies. Never let Opus do what Sonnet can, never let Sonnet do what Haiku can verify.

---

## Token-budget discipline

- `src/cfb_rankings/reporting.py` is 17.5k lines. **Never Read whole.** Use `offset`+`limit` reads, or Grep.
- Prefer Grep over Read when searching for a known string.
- Use the Task (subagent) tool for multi-file audits — the subagent returns a summary, keeping main context clean.
- Every task ends with a fresh commit + 3-line entry in `SESSION_LOG.md` so `/clear` between tasks is safe.
- When a task requires reading a large file: target the relevant line range, don't tour.
- If the context is getting full mid-task: stop, commit work-in-progress, clear, and resume.

---

## Repo conventions

- New source adapters: `src/cfb_rankings/ingest/sources/{source_id}.py`.
- Board adapters: `src/cfb_rankings/ingest/sources/boards/{board_name}.py`.
- Cohort logic: `src/cfb_rankings/cohorts/`.
- Provenance helpers: `src/cfb_rankings/provenance/`.
- Cowork playbooks: `docs/cowork_playbooks/{name}.md`.
- Schema migrations: `migrations/YYYYMMDD_NN_description.sql`.
- Seeds: `seeds/{name}.yaml`.
- Tests colocated: `test_{module}.py` next to the module.
- Secrets: environment variables only, `.env` gitignored, GitHub Secrets for Actions.
- CLI subcommands: added to `src/cfb_rankings/cli.py`, one function per command.
- No edits to `output/site/**`. No hand-edits to `cfb_rankings.db` — write a CLI subcommand.

---

## Task template

Every task announced and logged uses this shape:

```
### TASK N.M — {short name}
Model: Opus | Sonnet | Haiku-subagent
Depends on: [task IDs]
Inputs: [files/data read]
Output: [files/diffs produced]
Acceptance: [bullet list — each verifiable]
Token tips: [specific reads to avoid, grep patterns to prefer]
Verification: [how to confirm done — test cmd, grep, row-count query]
```

---

## Week 1 — Spine

Goal: schema, adapter base, source_registry seeded, priority_teams seeded, Actions cron scaffolded. No external data flowing yet.

### TASK 1.1 — Schema additions ✅ (2026-04-22)
**Model**: Opus. **Output**: `migrations/20260422_01_fanintel_schema.sql` adding everything in STRATEGY §5. NULL-able defaults, backward-compatible. Applier CLI: `python manage.py apply-migrations`.
**Acceptance**: `sqlite3 cfb_rankings.db ".schema"` shows new tables/columns; existing `build-site` still runs without errors.
**Verification**: Haiku subagent: run `build-site`, diff site output — only additive changes allowed.

### TASK 1.2 — `SourceAdapter` base class
**Model**: Opus. **Output**: `src/cfb_rankings/ingest/sources/base.py` with abstract methods `fetch()`, `parse()`, `write_rows()`, `health_check()`. Constants for `adapter_version`, retry policy, rate-limit. Concrete helper `BaseRssAdapter(SourceAdapter)` for the 40+ RSS sources to reuse.
**Acceptance**: unit test instantiates a dummy adapter, runs full lifecycle, writes one row to `scrape_health`.
**Verification**: pytest.

### TASK 1.3 — `source_registry` seed
**Model**: Opus (weights are editorial judgment). **Output**: `seeds/source_registry.yaml` with one entry per source in STRATEGY §3, cohort_weights copied from §4. Loader CLI: `python manage.py seed-source-registry`.
**Acceptance**: `SELECT COUNT(*) FROM source_registry` matches expected count; every row has non-null `cohort_weights`, `tier`, `max_publication_form`.
**Verification**: Haiku subagent: grep YAML for any missing required field.

### TASK 1.4 — `priority_teams` seed (20 teams)
**Model**: Sonnet. **Output**: `seeds/priority_teams.yaml` with 20 teams: 5 SEC, 4 B1G, 3 ACC, 3 B12, 3 G5, 2 HBCU. Fill in known handles; mark uncertain rows `needs_research: true`. Loader CLI: `python manage.py seed-priority-teams`.
**Acceptance**: 20 rows in `priority_teams`. The 20 selected programs cover the geographic + cohort diversity STRATEGY §9 requires.
**Verification**: Haiku subagent: count, diversity check.

### TASK 1.5 — GitHub Actions workflows (stubbed)
**Model**: Sonnet. **Output**: `.github/workflows/ingest_hourly.yml`, `ingest_daily.yml`, `ingest_weekly.yml`, `scrape_health.yml`. No adapters enabled yet — jobs just echo and exit 0. Secrets block included but empty (commented).
**Acceptance**: push → jobs appear in Actions tab on schedule.
**Verification**: manual check of Actions tab after push.

### TASK 1.6 — `scrape-health` CLI
**Model**: Haiku-subagent. **Output**: `python manage.py scrape-health` prints a table: `source_id | last_run | rows | status`. Sorted by status (error > empty > ok).
**Acceptance**: runs in <1s; output matches DB rows.
**Verification**: sqlite query cross-check.

---

## Week 2 — Free Tier-A sources

Goal: every Tier-A numeric source flowing into SQLite with provenance.

### TASK 2.1 — CFBD Patreon extension
**Model**: Sonnet. **Output**: `sources/cfbd.py` extended to pull `/lines`, `/lines/providers`, `/stats/season/advanced`, `/recruiting/players`. Store with `source_id=cfbd`.
**Acceptance**: daily row counts > 0 for each endpoint during in-season period.

### TASK 2.2 — Wikipedia pageviews
**Model**: Sonnet. **Output**: `sources/wikipedia_pageviews.py`. For each entity referenced in `priority_teams.wiki_*_page`, pull daily pageviews via Wikimedia REST API.
**Acceptance**: ≥60 rows/day (20 teams × 3 entities minimum).

### TASK 2.3 — Wikipedia edits
**Model**: Sonnet. **Output**: `sources/wikipedia_edits.py`. Daily edit counts + bytes changed per tracked page.

### TASK 2.4 — SeatGeek
**Model**: Sonnet. **Output**: `sources/seatgeek.py`. For each tracked team, pull upcoming events + cheapest-listing price + listing count.
**Acceptance**: rows for every future home game + top 3 away games per team.

### TASK 2.5 — YouTube metadata
**Model**: Sonnet. **Output**: `sources/youtube_meta.py`. Track team channels + 3 fan channels per team. Pull video uploads, views, comment counts daily.
**Acceptance**: <5% of daily quota burned.

### TASK 2.6 — Kalshi + Polymarket
**Model**: Sonnet. **Output**: `sources/kalshi.py`, `sources/polymarket.py`. Pull contract prices + volume for CFP, Heisman, conference titles, select game markets.
**Acceptance**: rows include `volume_usd` — floor rule enforced downstream.

### TASK 2.7 — GDELT volume
**Model**: Sonnet. **Output**: `sources/gdelt_volume.py`. Daily article counts per entity; *volume only*, no tone.

### TASK 2.8 — Spotify charts
**Model**: Sonnet. **Output**: `sources/spotify_charts.py`. Weekly CFB-category chart snapshot.

**Week 2 closing**: Haiku subagent runs full `scrape-health`; all 8 sources report `ok`.

---

## Week 3 — Conversation expansion

### TASK 3.1 — Bluesky firehose (Jetstream)
**Model**: Opus (architecture). **Output**: `sources/bluesky_firehose.py`. WebSocket client with keyword + handle filter; batched hourly writes to SQLite.
**Acceptance**: continuous process stays alive for 24h under supervisor; <100MB/day disk growth.

### TASK 3.2 — Bluesky curated handles + custom feeds
**Model**: Sonnet. **Output**: `sources/bluesky_curated.py`, `sources/bluesky_feeds.py`. Pull `getAuthorFeed` for curated list; pull `getFeed` for subscribed public feeds.

### TASK 3.3 — Bluesky starter-pack harvester
**Model**: Sonnet. **Output**: CLI `python manage.py bluesky-harvest-starterpacks` that takes a list of pack URIs and appends handles to `bluesky_curated` JSON in `priority_teams`.

### TASK 3.4 — Bluesky social graph sampler
**Model**: Opus. **Output**: `sources/bluesky_graph.py`. For each team's 3 top beat-writer handles, sample follower intersection; emit candidate fan handles.

### TASK 3.5 — Reddit expansion
**Model**: Sonnet. **Output**: `sources/reddit_team.py`, `sources/reddit_alumni.py`, `sources/reddit_city.py` (or unify into `sources/reddit.py` with sub-type config). Include comment-tree depth up to 3 for top 20 submissions/day per sub.
**Acceptance**: `community_type` correctly tagged per row.

### TASK 3.6 — Google News RSS per team
**Model**: Sonnet. **Output**: `sources/google_news.py`. Per-team query RSS polled every 4h.

---

## Week 4 — Media pulse

### TASK 4.1 — Beat-writer RSS (bulk)
**Model**: Sonnet. **Output**: `sources/beat_writers.py` (extends `BaseRssAdapter`). Seed file `seeds/beat_writer_feeds.yaml` with ~60 feeds across the 20 priority teams.

### TASK 4.2 — Campus newspapers (bulk)
**Model**: Sonnet. **Output**: `sources/campus_news.py`. Seed file with 20 campus paper feeds.

### TASK 4.3 — Substack (bulk)
**Model**: Sonnet. **Output**: `sources/substack.py`. Seed file with ~15 CFB Substack feeds.

### TASK 4.4 — School athletic sites (bulk)
**Model**: Sonnet. **Output**: `sources/athletics_sites.py`. Seed file with 20 school athletic RSS.

### TASK 4.5 — Locked On team-pod RSS metadata
**Model**: Sonnet. **Output**: `sources/locked_on.py`. One feed per team; capture title, description, duration, chapters. No transcription yet.

---

## Week 5 — Cowork playbook v1

### TASK 5.1 — Monday board-sweep playbook (design)
**Model**: Opus. **Output**: `docs/cowork_playbooks/monday_board_sweep.md`. Step-by-step navigation + extraction schema for the first 5 boards (Tigerdroppings, Shaggy Bevo, VolNation, TideFans, OSU indep).
**Acceptance**: a fresh Cowork session following the playbook produces rows identical in shape to a separate test run.

### TASK 5.2–5.6 — Five board adapters (Python-side complement)
**Model**: Sonnet, one task per board. **Output**: `sources/boards/{board}.py`. Each adapter handles the automated parts (RSS where available, structured thread indexes); the playbook handles the rest.
**Acceptance**: adapter + playbook combined produces ≥20 posts/week/board.

### TASK 5.7 — `team_cohort_week` aggregator (draft)
**Model**: Opus. **Output**: `cohorts/aggregate.py`. Computes `effective_n`, `sentiment_score`, `volume`, `confidence_tier` per `(team, cohort, week)` per STRATEGY §4 rules. CLI: `python manage.py compute-cohort-week --week=YYYY-WW`.
**Acceptance**: produces rows respecting floor rule; Tier C sources force aggregate to Tier C.

---

## Week 6 — Cowork playbook v2

### TASK 6.1 — Expand board sweep to 20 boards
**Model**: Sonnet. **Output**: 15 more board adapters + playbook extension.

### TASK 6.2 — TikTok observation playbook
**Model**: Sonnet. **Output**: `docs/cowork_playbooks/tiktok_weekly.md`. 30 creators, weekly. Schema: `(creator_handle, observed_at, followers, top_video_views_7d, top_video_url)`.

### TASK 6.3 — Google Trends export playbook
**Model**: Sonnet. **Output**: `docs/cowork_playbooks/trends_weekly.md`. DMA-level exports per priority team, CSV import CLI.

### TASK 6.4 — Facebook alumni glance playbook
**Model**: Sonnet. **Output**: `docs/cowork_playbooks/fb_alumni_glance.md`. 10 public Pages, observe + summarize, store under `source_id=facebook_alumni_glance` as Tier D citations.

### TASK 6.5 — Thursday game-week pulse + Sunday recap playbooks
**Model**: Sonnet. **Output**: two more playbook markdown files; shared extraction schema.

---

## Week 7 — Podcast + radio

### TASK 7.1 — Podcast RSS metadata (bulk)
**Model**: Sonnet. **Output**: `sources/podcasts_meta.py`. Tracks ~40 shows; captures episode metadata only.

### TASK 7.2 — Whisper.cpp selective ASR
**Model**: Sonnet. **Output**: `tools/transcribe_episode.py` — CLI that downloads one episode, transcribes locally, stores segment table. Not run on cron; triggered manually for episodes flagged for editorial use.
**Acceptance**: runs on Kevin's PC; transcript stored with `source_tier=D`.

### TASK 7.3 — Finebaum daily metadata
**Model**: Sonnet. **Output**: `sources/finebaum.py`. Daily ESPN feed metadata capture; no transcription by default.

### TASK 7.4 — Local sports radio podcast RSS
**Model**: Sonnet. **Output**: seed file with 8–12 regional sports radio podcast feeds (Atlanta, Birmingham, Columbus, Knoxville, Baton Rouge, Dallas, LA, Columbus OH, Ann Arbor region). Reuse `BaseRssAdapter`.

---

## Week 8 — Cohort aggregation + editorial

### TASK 8.1 — Cohort divergence metric
**Model**: Opus. **Output**: `cohorts/divergence.py`. Computes per-team-week `divergence_score`. CLI: `python manage.py compute-divergence --week=YYYY-WW`.

### TASK 8.2 — Methodology page auto-generation
**Model**: Opus (copy is high-consequence). **Output**: template + generator in `reporting.py` (surgical edit) that renders `/methodology/fan-intelligence` from `source_registry` + current weight matrix.
**Acceptance**: page lists every active source with tier, cadence, license, last-fetch, cohort weight rationale. Passes a11y spot-check.

### TASK 8.3 — Cohort panel widget on team pages
**Model**: Opus design, Sonnet implement. **Output**: small-multiples panel rendering cohort sentiment bars per team-week, respecting effective-N floor rule; "Awaiting Signal" fallback wired. Enable on 3 flagship team pages initially.
**Acceptance**: no cell shows a number if `effective_n < 30`.

### TASK 8.4 — Monday Brief template
**Model**: Sonnet. **Output**: `docs/editorial/monday_brief_template.md`. Prompts Claude or ChatGPT with current week's divergence data and produces a draft brief. Kevin edits for voice.

### TASK 8.5 — End-to-end audit
**Model**: Opus (cross-cutting), with multiple Haiku subagents for verification.
**Output**: a document `docs/audits/fanintel_v1_audit.md` confirming: every source in §3 has a row in `source_registry`; every source produces rows or is flagged inactive; methodology page is up; floor rule is tested with a synthetic low-N case.
**Acceptance**: audit doc ships; no failing checks.

---

## After Week 8

- Monitor `scrape_health` weekly (5 min).
- Fix broken adapters as they surface (1–2 hrs/month expected).
- Run monthly Deep Research config refresh.
- Run quarterly starter-pack + beat-writer refresh.
- First annual cohort weight review: **April 2027**. Snapshot 2026 weights before editing.

---

## How to pick the next task

1. Open this file.
2. Find the first unchecked task in the earliest unfinished week.
3. Announce `TASK N.M` and chosen model.
4. Read only what the Token Tips allow.
5. Implement. Test. Commit.
6. Spawn Haiku subagent for verification if the task's Verification line calls for it.
7. Append to `SESSION_LOG.md`:
   `YYYY-MM-DD | TASK N.M | {outcome} | {follow-ups}`
8. Check the box here. Push.
9. If at a week boundary or context is >60% full: stop, summarize, hand back.
