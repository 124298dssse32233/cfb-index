# Fan Intelligence — Source & Cohort Strategy

**Status**: canonical reference. Last updated 2026-04-22. Update weights, sources, and tiers *here*; downstream docs and code should cite this file, not restate it.

---

## 1. Mission & principles

The CFB Index publishes fan-intelligence data (mood, attention, divergence, obsession) alongside on-field rankings. The product differentiator is **cohort-aware sentiment with row-level provenance** — no competitor does it and nobody can fake it without an equivalent source + weight system.

Three non-negotiable principles, enforced in code, not policy:

1. **No fake precision.** If effective sample size for a cell falls below the floor, the UI renders a rank or the "Awaiting Signal" fallback. Never a faked percentage.
2. **Every row carries provenance.** `platform`, `source_id`, `source_tier`, `ingestion_adapter_version`, `capture_url`, `sample_n`. Everything traces back.
3. **Editorial is visibly editorial.** When we curate, annotate, or human-transcribe, the UI marks it.

---

## 2. Architecture — four tiers

Every source lives in exactly one tier. Tier assignment controls how it runs and who touches it.

### Tier 1 — Always-on Python pipelines (GitHub Actions cron, free)
Pure API + RSS sources. No human intervention. Runs 24/7.
CFBD (+Patreon $10/mo), Wikipedia pageviews + edits, SeatGeek, YouTube Data API, Bluesky (firehose + AppView), GDELT, Google News RSS, Substack RSS, campus newspapers, beat writer RSS, school athletics RSS, Kalshi + Polymarket, Reddit (team/alumni/city subs + comment trees), Locked On podcast RSS metadata.

### Tier 2 — Cowork-Chrome weekly sweeps (~90 min/week in-season)
Kevin opens Cowork, Claude follows a pre-built playbook and writes rows to SQLite.
Independent team message boards (Tigerdroppings, Shaggy Bevo, VolNation, TideFans, OSU/UM independents), 247/On3/Rivals free-tier threads, TikTok creator observations (30 curated), Facebook public alumni Pages (glance), Google Trends regional exports, Spotify/Apple podcast chart positions, Finebaum daily episode metadata, Barstool college IG accounts.

### Tier 3 — Monthly deep-research refreshes (2–3 hrs/month)
Kevin launches ChatGPT Deep Research or Claude Research with stock prompts.
Refreshes: beat-writer handles per team, active boards per team, podcast chart entrants, coach social accounts, NIL/portal writer cohort.

### Tier 4 — Editorial synthesis on demand
Claude Max / ChatGPT Pro assists Kevin writing narratives when cross-source divergences emerge. Not a pipeline — a practice.

---

## 3. Source catalog

Each source is identified by `source_id`, assigned a publication tier (A/B/C/D), a cost, a cadence, and a provenance label.

### Tier A — numeric publication OK

| source_id | description | cost | cadence | provenance label |
|---|---|---|---|---|
| `cfbd` | CFBD core facts + lines + advanced stats (Patreon tier) | $10/mo | hourly in-season, daily off | `CFBD, YYYY-WW` |
| `wiki_pv` | Wikipedia pageviews per tracked entity (en) | free | daily | `Wikipedia pageviews (en), {page}, {window}, N={count}` |
| `wiki_edits` | Wikipedia edit activity per tracked entity | free | daily | `Wikipedia edits (en), {page}, {window}` |
| `seatgeek` | Event get-in price + listing counts | free tier | daily; hourly game week | `SeatGeek get-in, {event}, {timestamp}, N listings={N}` |
| `youtube_meta` | Video views + metadata for tracked channels | free (quota) | daily | `YouTube video {id}, channel {title}, fetched {timestamp}` |
| `kalshi` | Kalshi contract prices + volume | free | daily | `Kalshi contract {id}, last trade {date}, volume ${N}` |
| `polymarket` | Polymarket contract prices + volume | free | daily | `Polymarket {market_id}, {date}, volume ${N}` |
| `gdelt_volume` | Article count per entity per day | free | daily | `GDELT 2.0, N={count}, window {range}` |
| `spotify_charts` | CFB-category podcast chart ranks | free | weekly | `Spotify Podcast Charts, {category}, {week}` |

### Tier B — aggregated signal, publish with sample size

| source_id | description | cost | cadence |
|---|---|---|---|
| `reddit_cfb` | r/CFB submissions + comment trees | free | hourly |
| `reddit_team` | per-team subreddit | free | hourly |
| `reddit_alumni` | alumni subreddit (e.g. r/UofM) | free | hourly |
| `reddit_city` | city subreddit (e.g. r/BatonRouge) | free | daily |
| `bluesky_firehose` | Jetstream keyword-filtered | free | continuous |
| `bluesky_curated` | ~600 hand-picked handles per team graph | free | 10 min |
| `bluesky_feeds` | public CFB custom feeds via AppView | free | 15 min |
| `bluesky_starterpack` | seeded from public starter packs, harvested quarterly | free | quarterly harvest |
| `youtube_comments_team` | team-channel comment streams | free (quota) | daily |
| `youtube_comments_nat` | national CFB pod channel comments | free (quota) | daily |
| `twitch_chat` | game-day chat on 5–10 CFB channels | free | live during games |
| `board_{name}` | independent team boards (one row per board) | free or $10/mo proxies | daily adapter or weekly Cowork |
| `locked_on_{team}` | Locked On team-daily pod RSS | free | daily (metadata); weekly selective ASR |
| `campus_{school}` | campus newspaper RSS | free | daily |
| `substack_{writer}` | CFB Substack RSS | free | hourly |
| `beat_{writer}` | beat-writer RSS | free | hourly |
| `athletics_{school}` | school athletic site press RSS | free | daily |

### Tier C — rank/trend only, never a raw number

| source_id | description | cost | cadence |
|---|---|---|---|
| `gdelt_tone` | GDELT tone score, weekly aggregate only | free | weekly |
| `google_trends_dma` | DMA-level regional rank via Cowork export | free | weekly |
| `tiktok_observed` | 30 CFB creator follower + top-video counts | free | weekly (Cowork manual) |
| `predict_thin` | Kalshi/Polymarket contracts with volume <$1k | free | daily |

### Tier D — editorial citation only (human quotes)

| source_id | description |
|---|---|
| `finebaum_rss` | Paul Finebaum Show episode metadata + selective quote-ASR |
| `radio_{city}` | local sports radio podcast RSS + selective quotes |
| `beat_articles` | beat-writer article quotes via RSS |
| `press_releases` | school athletic press release quotes |
| `board_quotes` | message-board pull-quotes, pseudonym-only + backlink |
| `facebook_alumni_glance` | Cowork-manual observation of public alumni Pages |

### Deliberately skipped — do not build for these

- X/Twitter in any form (price + ToS).
- Instagram / Facebook bulk programmatic collection (ToS).
- Discord non-public servers (ToS + ethics).
- Rivals/247/On3 **paywalled** content (ToS; free tiers only).
- TikTok via unofficial libraries as a daily pipeline (fragility + ToS).
- Threads API (revisit 2026 Q3).
- Racial / gender / political cohort splits (indefensible from platform data).
- "Podcast sentiment index" from ASR (ASR error + sarcasm + negation loss).
- Google Trends raw 0–100 values as published numbers (silently rebaselined).
- Player social accounts as "fan sentiment" (they're the subject, not the fan; and minors).

---

## 4. Cohort system

Three orthogonal axes. Each source carries a weight vector per axis. Documents inherit source weights. Aggregates are weighted sums. One document can contribute to multiple cohorts simultaneously.

**Generation axis**: `boomer_gen_x` (55+), `millennial` (28–44), `gen_z` (18–27), `college_age` (17–22, overlaps Gen Z but distinct on-campus flavor).

**Lens axis**: `analytics`, `recruiting`, `gambling`, `casual_vibes`, `die_hard`, `media_class`.

**Geography axis**: `local_market`, `national_narrative`, `alumni_diaspora`, `hbcu_community`.

### Starting weight matrix

Weights do not need to sum to 1 within an axis. A Reddit r/CFB post is simultaneously millennial and national-narrative and mildly analytics-tilted — that's realistic.

| source | boom/gx | mill | gen_z | coll | anal | rec | gamb | casl | die | media | local | nat |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `reddit_cfb` | .05 | .55 | .25 | .10 | .30 | .10 | .15 | .15 | .20 | .05 | .05 | .60 |
| `reddit_team` | .10 | .55 | .25 | .15 | .15 | .10 | .10 | .15 | .55 | .05 | .30 | .25 |
| `reddit_alumni` | .15 | .55 | .20 | .10 | .10 | .05 | .05 | .15 | .30 | .05 | .15 | .30 |
| `reddit_city` | .15 | .50 | .25 | .15 | .05 | .05 | .05 | .20 | .20 | .05 | .70 | .10 |
| `board_indep` | .40 | .40 | .10 | .05 | .10 | .15 | .10 | .05 | .70 | .05 | .55 | .15 |
| `board_247_free` | .30 | .45 | .15 | .05 | .15 | .35 | .10 | .05 | .65 | .05 | .50 | .20 |
| `finebaum_rss` | .75 | .15 | .02 | .02 | .05 | .10 | .10 | .15 | .60 | .10 | .60 | .30 |
| `radio_local` | .65 | .25 | .05 | .03 | .05 | .10 | .10 | .15 | .55 | .10 | .80 | .10 |
| `bluesky_curated` | .15 | .55 | .15 | .05 | .30 | .15 | .10 | .05 | .25 | .55 | .20 | .60 |
| `bluesky_firehose` | .05 | .50 | .25 | .15 | .15 | .10 | .10 | .20 | .15 | .10 | .10 | .55 |
| `youtube_comments_team` | .35 | .40 | .20 | .10 | .10 | .10 | .05 | .25 | .55 | .05 | .40 | .30 |
| `youtube_comments_nat` | .20 | .45 | .25 | .10 | .25 | .10 | .10 | .30 | .30 | .10 | .10 | .70 |
| `tiktok_observed` | .02 | .20 | .65 | .35 | .05 | .15 | .05 | .60 | .10 | .05 | .20 | .50 |
| `twitch_chat` | .02 | .30 | .55 | .30 | .10 | .05 | .10 | .40 | .30 | .05 | .25 | .40 |
| `campus_news` | .05 | .15 | .55 | .70 | .10 | .10 | .05 | .15 | .30 | .15 | .70 | .10 |
| `facebook_alumni_glance` | .55 | .30 | .05 | .03 | .05 | .05 | .05 | .20 | .40 | .05 | .35 | .20 |
| `substack_cfb` | .20 | .55 | .15 | .05 | .40 | .15 | .10 | .05 | .30 | .70 | .15 | .65 |
| `locked_on_team` | .20 | .50 | .20 | .10 | .25 | .15 | .10 | .10 | .55 | .40 | .40 | .30 |
| `seatgeek` | — | — | — | — | — | — | — | .30 | .60 | — | .80 | .20 |
| `kalshi` / `polymarket` | .05 | .50 | .20 | .10 | .55 | .05 | .75 | .05 | .15 | .05 | .05 | .75 |
| `cfbd` (lines) | — | — | — | — | .60 | .20 | .70 | — | .30 | .10 | .10 | .70 |
| `wiki_pv` | .20 | .40 | .25 | .15 | .15 | .15 | .05 | .40 | .15 | .05 | .20 | .65 |

Column abbreviations: boom/gx = boomer_gen_x, mill = millennial, coll = college_age, anal = analytics, rec = recruiting, gamb = gambling, casl = casual_vibes, die = die_hard, nat = national_narrative. Geography axis columns `alumni_diaspora` and `hbcu_community` omitted for width; stored in full in `source_registry.cohort_weights` JSON.

### Effective sample size rule

For each `(team, cohort, week)` cell:

```
effective_n = sum(doc.source.cohort_weight[cohort] for doc in docs)
```

- `effective_n < 30` → UI shows rank or "Awaiting Signal". Never a number.
- `30 ≤ effective_n < 100` → publish number with explicit sample-size badge.
- `effective_n ≥ 100` → publish number with standard styling.

Enforced in the aggregator, not in UI. UI reads `confidence_tier` and renders accordingly.

### Cohort divergence metric (first-class product feature)

For each `(team, week)`:

```
divergence_score = stdev(cohort_sentiment for each cohort where effective_n ≥ 30)
```

High divergence = fragmented fanbase = story. Low divergence = real consensus. Ship as a core widget on team pages.

### Weight governance

- Weights are editorial judgment grounded in Pew/GWI platform demographic data. Cite the basis in `cohort_weights_rationale`.
- Reviewed once per year (April, ahead of the following season). Prior weight versions are snapshotted immutably so historical aggregates don't shift.
- Public at `/methodology/cohorts` — weight table, rationale, changelog.

---

## 5. Schema additions (apply before collecting from new sources)

Migration file: `migrations/20260422_01_fanintel_schema.sql`. Backward-compatible defaults (NULL-able or with sensible defaults).

### New table: `source_registry`
```
source_id            TEXT PRIMARY KEY
name                 TEXT NOT NULL
platform             TEXT NOT NULL         -- reddit|bluesky|youtube|…
tier                 TEXT NOT NULL         -- A|B|C|D
ingest_method        TEXT NOT NULL         -- api_official|api_unofficial|rss|firehose|cowork_manual
terms_url            TEXT
license              TEXT
retention_days       INTEGER               -- for privacy/ToS compliance
cohort_weights       TEXT NOT NULL         -- JSON per §4
cohort_weights_rationale TEXT
cohort_weights_updated_at DATE
max_publication_form TEXT NOT NULL         -- numeric|aggregate|rank|citation
active               INTEGER NOT NULL DEFAULT 1
```

### New columns on `conversation_documents`
```
source_id                    TEXT REFERENCES source_registry(source_id)
source_tier                  TEXT             -- denormalized for fast filter
demographic_slice            TEXT             -- hardcore_board|reddit|media_adjacent|…
geographic_origin            TEXT             -- nullable; IP-geo|self-declared|domain|post-geo
author_identity_class        TEXT             -- pseudonymous|real_name_social|verified_media|official|anonymous
capture_url                  TEXT
canonical_url                TEXT
retention_policy             TEXT             -- raw_keep|aggregated_only|evict_after_N
ingestion_adapter_version    TEXT
dedup_key                    TEXT             -- hash(platform,author,timestamp,text[:16])
```

### New table: `team_cohort_week`
```
team_id              INTEGER NOT NULL
cohort               TEXT NOT NULL           -- e.g. gen_z, analytics, local_market
week                 TEXT NOT NULL           -- YYYY-WW
effective_n          REAL NOT NULL
sentiment_score      REAL                    -- NULL if below floor
volume               INTEGER NOT NULL
top_source_ids       TEXT                    -- JSON array
confidence_tier      TEXT NOT NULL           -- A|B|C (worst tier that contributed)
PRIMARY KEY (team_id, cohort, week)
```

### New table: `team_cohort_divergence_week`
```
team_id              INTEGER NOT NULL
week                 TEXT NOT NULL
divergence_score     REAL
num_cohorts_qualifying INTEGER
PRIMARY KEY (team_id, week)
```

### New table: `scrape_health`
```
source_id            TEXT NOT NULL
run_date             DATE NOT NULL
rows_inserted        INTEGER
status               TEXT NOT NULL           -- ok|empty|error|skipped
error_message        TEXT
PRIMARY KEY (source_id, run_date)
```

### New table: `priority_teams`
Per-team configuration consumed by all adapters.
```
team_id              INTEGER PRIMARY KEY REFERENCES teams(team_id)
rank_priority        INTEGER NOT NULL        -- 1..20 for top tier; 0 = standard
reddit_team_sub      TEXT
reddit_alumni_sub    TEXT
reddit_city_sub      TEXT
wiki_team_page       TEXT
wiki_coach_page      TEXT
wiki_qb_page         TEXT
google_news_query    TEXT
youtube_team_channel_id TEXT
youtube_fan_channels TEXT                    -- JSON array
bluesky_team_handle  TEXT
bluesky_beat_handles TEXT                    -- JSON array
message_board_primary TEXT                   -- domain
message_board_secondary TEXT
campus_newspaper_feed TEXT
substack_feeds       TEXT                    -- JSON array
beat_writer_rss      TEXT                    -- JSON array
athletic_dept_feed   TEXT
seatgeek_team_slug   TEXT
twitch_channels      TEXT                    -- JSON array
sports_radio_shows   TEXT                    -- JSON array of podcast RSS
head_coach_bsky      TEXT
head_coach_ig        TEXT
tiktok_creators      TEXT                    -- JSON array
locked_on_rss        TEXT
needs_research       INTEGER NOT NULL DEFAULT 0
last_config_refresh  DATE
```

### Modifications to existing aggregates

`team_week_conversation_features`, `fanbase_mood_weekly`, `rivalry_obsession_weekly`, `lexicon_weekly`: add `sample_n INTEGER`, `sample_window TEXT`, `confidence_floor TEXT`, `model_version TEXT`. Backfill via migration where possible.

---

## 6. Publication & provenance rules (enforced in code)

- Every aggregate row must have `sample_n` and `source_ids` populated. Rows missing either are never shown in UI.
- Tier C contributions to an aggregate → aggregate inherits Tier C confidence → renders rank/trend only.
- Effective-N floor enforced in aggregator, before write to `team_cohort_week`.
- Methodology page (`/methodology/fan-intelligence`) auto-generated from `source_registry` + weight tables. Adding a source updates the page.
- Quoted text from Tier B/D sources: backlink + pseudonym required. Full-text storage governed by `retention_policy`.
- For YouTube comments specifically: if a comment is deleted upstream (detected via quarterly sweep), purge from storage per `retention_policy=raw_keep` + deletion-check.

---

## 7. Operational cadence

### In-season weekly rhythm
- **Monday 9 AM, 45 min.** Cowork board-sweep playbook (20 boards). ~400 new rows.
- **Monday 10 AM, 30 min.** Weekly brief written, divergences narrated with source citations.
- **Thursday 3 PM game week, 20 min.** Game-week pulse — ticket snapshot, line review, board flare-ups.
- **Sunday 10 AM game week, 30 min.** Post-game recap sweep — emotional pulse across platforms.

### Monthly
- **First of month, 30 min.** Deep Research config refresh run. Review JSON patch, apply.

### Quarterly (1 hr)
- Review `scrape_health` trends, fix chronic broken adapters, harvest any new Bluesky starter packs.

### Annually (2 hrs)
- Cohort weight review. Snapshot old weights with date tag. Publish changelog.

### Ad-hoc
- **CFP Tuesdays (Nov–Dec)**: reveal reaction window — dedicated collector fires ±90 min of reveal time.
- **Breaking coaching news**: trigger deep pull on affected team + rival teams within 24h.

---

## 8. Public methodology page spec

At `/methodology/fan-intelligence`, auto-generated from code + `source_registry`:

- Full source list: tier, cadence, license, last successful fetch.
- Cohort weight matrix with per-source rationale strings.
- Effective-N thresholds and confidence-tier definitions.
- Example cells rendered at each confidence tier.
- Changelog of weight updates and source additions.
- Contact for corrections.

This page is the single highest-credibility asset in the product. Never soften it, never hide it, and never publish a metric that can't defend itself on this page.

---

## 9. Known coverage gaps (document honestly)

- **Gen Z casual** — programmatic reach is weak; manual TikTok observation fills. Don't claim parity.
- **Alumni diaspora** — FB alumni groups largely inaccessible. Best we can do is alumni-sub + Substack proxies.
- **HBCU community** — coverage is narrow (TikTok, HBCU Gameday, 504SportsNation). Publish honest "partial coverage" tag on HBCU program pages.
- **Women CFB fans** — real and growing on IG/TikTok, no defensible identity signal. Not broken out as a cohort.
- **International/diaspora fans** — small, unaddressed. Acknowledge in methodology.

These gaps aren't bugs to paper over. Making them visible is a credibility asset.
