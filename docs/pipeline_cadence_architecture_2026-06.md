I have full ground truth now. Everything checks out against the actual code, and importantly several research recommendations are already shipped (`--archive=tgz`, deploy retry-with-backoff, alias rotation, file-count + data-quality + manifest gates, `min_seconds_between_requests`, honest UA, `consecutive_fail_abort`). My synthesis accounts for that. Here is the architecture.

---

# Daily Pipeline Cadence Architecture (June 2026)

This is the single, opinionated target design for your stack: solo dev, one always-on Windows box (Ryzen 9 9900X + RTX 3090), Python/.venv → SQLite (1.46 GB) → ~27k static pages → Vercel, orchestrated only by PowerShell + Task Scheduler. It synthesizes all four research passes against your *actual* code in `scripts/daily_ingest.ps1`, `scripts/publish_to_vercel.ps1`, `src/cfb_rankings/ingest/sources/gdelt_volume.py`, and `numeric_base.py`.

**What's already done (do not rebuild):** your publish path (`publish_to_vercel.ps1`) already ships `vercel deploy --prod --yes --archive=tgz`, a 4-attempt deploy retry with backoff, explicit `vercel alias set` rotation, and three pre-deploy gates (≥3500-file count, `verify-publish-readiness`, `_build_manifest.json` <26h). The base adapter already has `min_seconds_between_requests`, an honest User-Agent, and a retry policy; GDELT already has a `consecutive_fail_abort=6` circuit breaker. So the Vercel-resilience research is ~80% implemented — the remaining gap is purely **the collect↔build coupling and GDELT's per-team-loop architecture.**

---

## 1. Verdict: the 3-4 changes that matter most (ranked, with why)

**#1 — Replace GDELT's 138-call per-team loop with ONE bulk pull. (Highest value, fixes the root cause permanently.)**
The DOC 2.0 API enforces "one request every 5 seconds" ([h-toss.com, Jan 2026](https://h-toss.com/gdelt-api-request-failed-please-limit-requests-to-one-every-5-seconds/)), so 138 teams is an ~11.5-minute floor *before any 429*, and your `min_seconds_between_requests=5.0` makes that floor literal. No looping/pacing/rotation fix beats deleting the loop. Pull GDELT's pre-computed bulk data **once** and aggregate all 138 team counts locally. This retires `max_collection_tier=2` (the 76-team cap), `consecutive_fail_abort`, and the entire grind class. ([GDELT BigQuery still free 2026](https://www.gdeltproject.org/data.html); [bulk GKG / NGrams as the rate-limit-free replacement](https://blog.gdeltproject.org/ukraine-api-rate-limiting-web-ngrams-3-0/))

**#2 — Decouple collect from build+publish into two Task Scheduler jobs sharing only SQLite. (Structural; makes the build un-blockable forever.)**
Today `daily_ingest.ps1` runs collect → aggregate → encoder → build → publish in one synchronous script (lines 117–320), so any slow section A holds the publish hostage — exactly your incident. Split into `collect.ps1` (writes SQLite on its own cadence) and `build_publish.ps1` (reads SQLite as-of-now, builds, deploys). The build then ships *whatever is in SQLite*, degrading gracefully (which your "Awaiting Signal" fallback already embraces). This is the producer/consumer-over-a-shared-store pattern; SQLite *is* the buffer, no broker needed. ([outbox/worker decoupling](https://www.milanjovanovic.tech/blog/implementing-the-outbox-pattern); [pipelines that don't break](https://www.kdnuggets.com/the-complete-guide-to-building-data-pipelines-that-dont-break))

**#3 — Add a `collection_ledger` table + stale-first rotation + per-source wall-clock budget. (The keystone; makes "all 138, bounded" possible for every slow source, not just GDELT.)**
One table records `(source, entity, last_ok_at, next_due_at, cooldown_until, cursor)`. Each run picks the N oldest-due entities within a hard time box; on success pushes `next_due_at` forward. This is a crawl budget: full coverage over a rolling window, bounded per-run work, partial runs resume cleanly. A time box makes "hours-long grind" *structurally impossible*. ([Google crawl budget](https://developers.google.com/crawling/docs/crawl-budget); [staleness-driven recrawl](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8452733))

**#4 (lower priority, do later) — Output-side content-hash manifest for cheap frequent publishes.**
Only matters *once you publish multiple times a day*. Your 5-min build is fine for a nightly cadence; a `manifest.json` of `{path: sha256}` (always-rebuild aggregates, hash the long tail) shrinks uploads when you go intraday. Defer until #1–#3 land. ([Eleventy incremental model](https://www.11ty.dev/docs/usage/incremental/); [sqlite-chronicle](https://github.com/simonw/sqlite-chronicle))

> Changes #1–#3 would each independently have prevented your incident; together they make the system fast, comprehensive, and self-healing. #4 is a freshness upgrade, not a fix.

---

## 2. Source-by-source cadence table

Velocity is the deciding axis: high-velocity fan signals stay daily; slow/rate-limited volume signals rotate; structural data is event-driven. "Critical path" = the build *reads* it; **no source is ever fetched on the critical path** after the decouple (#2) — the build only reads SQLite.

| Source (your live adapters) | Cadence | Coverage model | Path | Rate-limit posture |
|---|---|---|---|---|
| **GDELT volume** (`gdelt_volume`) | Daily, **1 bulk call total** | All 138 at once via BigQuery/GKG bulk | Decoupled (`collect-slow`) | No per-team API; no limiter. Honest UA + HTTP (not HTTPS) for bulk files. |
| **Reddit per-team RSS** (`collect-reddit-team-rss`) | **Daily, all ~118 teams** | High velocity (game-day spikes) → daily | Decoupled (`collect-fast`) | `.rss` is generous; keep honest UA + existing spacing. |
| **Reddit r/CFB national** (`collect-reddit-watchlist`) | Daily, best-effort | National layer | `collect-fast` | PullPush/Arctic Shift already 429/422-degraded — keep best-effort, never critical. |
| **YouTube comments** (`collect-youtube-comments`) | **Daily, quota-budgeted** | `--max-units 6000` already bounds it | `collect-slow` | Hard 10k units/day; your 6000 cap is the budget. Keep. |
| **Independent boards** (`collect-team-boards`) | **Daily, all 12** | Direct 1 board→1 team RSS | `collect-fast` | Tiny; no issue. |
| **Bluesky** (`bluesky_curated`, `bluesky_feeds`) | Daily | Public AppView + custom feed | `collect-fast` | Generous public API. |
| **Wikipedia** (`wiki_pv`, `wiki_edits`) | Daily, all 138 | Bulk-ish endpoints | `collect-fast` | Polite; fine. |
| **Google News / campus / athletics / Locked On RSS** (`*_all`) | Daily | Bulk RSS families | `collect-fast` | RSS, no per-entity API loop. |
| **Kalshi / Polymarket** | Daily | Market snapshots | `collect-fast` | Light. |
| **SeatGeek / Spotify** (`seatgeek`, `spotify_charts`) | Daily | Auth-gated | `collect-slow` | Respect each key's quota. |
| **Coaching carousel** (`coaching-fetch-news`) | Daily, `--days 7` overlap | RSS | `collect-fast` | Overlap window catches late edits. |
| **CFBD week ingest** (`ingest-cfbd-week`) | **Event-driven** (in-season only) | Already gated `if ($IsInSeason)` | `build_publish` pre-step | Keep as-is. |
| **Models / Heisman** (`run-models`, etc.) | Event-driven (in-season) | Needs fresh game data | `build_publish` pre-step | Keep as-is. |
| **Encoder sentiment** (`sentiment_classify_daily.py`, `.venv-ml`) | Daily, GPU | New docs only | `collect-slow` (or a 3rd GPU job) | Local, no network limiter. Already non-critical. |

**Media Cloud** (a research suggestion): wire in *only later* as a rolling weekly cross-check (cycle teams over 2–3 days to stay under 4,000 req/week and the 2 req/min cap) — **not** the daily driver, and never on the critical path. ([Media Cloud FAQs](https://www.mediacloud.org/documentation/faqs)) GNews/NewsAPI.org/NewsAPI.ai are all non-viable at 138/day — do not adopt. ([gnews pricing](https://gnews.io/pricing); [newsapi pricing](https://newsapi.org/pricing))

---

## 3. GDELT decision

**Primary: one daily BigQuery query against the partitioned GKG table. Fallback: nightly bulk GKG file download parsed locally. Retire the per-team DOC API entirely.**

**Why BigQuery primary.** One scheduled query returns all 138 rows in a single round trip with zero rate limiter:

```sql
SELECT DATE, V2Organizations
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME >= TIMESTAMP(DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY))
```

then `UNNEST(SPLIT(V2Organizations, ';'))`, strip the char-offset after the comma, `GROUP BY` your 138-team alias map. Selecting only two columns from the **partitioned** table scans well under 1 GB/day (~30 GB/month ≈ 3% of the free 1 TiB) = **$0/month**. ([partitioned tables: 15 GB vs 423 GB](https://blog.gdeltproject.org/announcing-partitioned-gdelt-bigquery-tables/); [free tier 1 TiB then $6.25/TiB](https://cloud.google.com/bigquery/pricing)) Hard-guard it: set `maximum_bytes_billed` on the job and `--dry_run` first so an accidental `SELECT *`/unpartitioned scan can never bill. ([cost best-practices](https://docs.cloud.google.com/bigquery/docs/best-practices-costs))

**Why a bulk-file fallback (no Google account needed).** If BigQuery auth/quota ever hiccups, nightly download the trailing-24h GKG 15-min files via `http://data.gdeltproject.org/gdeltv2/lastupdate.txt` (~365 MB/day English compressed), parse the `V2Organizations` column on the 9900X, aggregate the *same* metric. Two gotchas the research verified live: send a non-empty **User-Agent** (UA-less = 429), and fetch over **plain HTTP** — `data.gdeltproject.org`'s HTTPS cert is altname-mismatched, so HTTPS fails TLS while HTTP works. ([UA requirement](https://github.com/alex9smith/gdelt-doc-api/issues/22); [GKG codebook V2Organizations](http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf))

**Why not the other options.** Rotated-API (the §4 fallback) still pays the 5s-per-call tax and only ever covers a slice per night — strictly worse than one bulk pull that covers all 138 daily. Paid GDELT Cloud is unnecessary. No commercial news API sustains 138 entities/day at $0.

**The one real work item this creates:** a curated 138-team → org-alias map (full name, nickname, abbreviations) with homonym guards for **Miami / Washington / Buffalo / Oregon-vs-Oregon State**. This map is the *only* thing between bulk data and clean per-team counts — your `priority_teams.google_news_query` column is the natural place to extend with alias arrays.

**Net:** `gdelt_volume.py` stops being a `fetch()`-loops-over-teams adapter and becomes a `fetch()`-runs-one-query-then-`parse()`-buckets-locally adapter. Delete `max_collection_tier`, `consecutive_fail_abort`, `min_seconds_between_requests`, and the 76-team cap.

---

## 4. The rotation + decoupling mechanism

Concrete enough to implement in your stack today.

### 4a. The ledger (one migration in `migrations.py`)

```sql
CREATE TABLE IF NOT EXISTS collection_ledger (
  source        TEXT NOT NULL,        -- 'gdelt','reddit_rss','youtube','seatgeek',...
  entity        TEXT NOT NULL,        -- team_id (or '*' for whole-source bulk runs)
  last_ok_at    TEXT,
  last_attempt_at TEXT,
  next_due_at   TEXT,                  -- eligible-again time; NULL = never collected
  cursor        TEXT,                  -- high-water mark / continuation token
  consecutive_failures INTEGER DEFAULT 0,
  cooldown_until TEXT,                 -- per-entity deferral after repeated failure
  PRIMARY KEY (source, entity)
);
CREATE INDEX IF NOT EXISTS idx_ledger_due ON collection_ledger(source, next_due_at);
```

This one table replaces the ad-hoc state you already carry: GDELT's tier cap, `reddit_backfill_state.json`, etc. It is simultaneously your rotation queue, your checkpoint store, and your deferral list — `next_due_at <= now` *is* the pending set (no SKIP LOCKED, single writer). ([ledger-as-queue](https://dev.to/damikaanupama/designing-asynchronous-apis-with-a-pending-processing-and-done-workflow-4gpd))

### 4b. Per-run slice selection (Python, called from each rotating adapter)

```python
def select_batch(db, source, budget, now_iso):
    rows = db.query_all("""
      SELECT entity FROM collection_ledger
      WHERE source = :s
        AND (cooldown_until IS NULL OR cooldown_until <= :now)
      ORDER BY (next_due_at IS NULL) DESC,   -- never-collected first
               next_due_at ASC               -- then stalest-due first
      LIMIT :budget""",
      {"s": source, "now": now_iso, "budget": budget})
    return [r["entity"] for r in rows]
```

Set budget so `budget × period ≥ 138`. For any *non-bulk* rotated source: 46/run × 72h interval covers all 138 every 3 days. **Note: with the GDELT bulk fix (#1, #3), GDELT no longer needs rotation** — it's `entity='*'`, one row, daily. Rotation is the pattern for the *next* slow per-entity source you add (e.g. Media Cloud), and the safety net if any source must stay per-entity.

### 4c. The collect loop (idempotent + time-boxed + checkpointed)

```python
deadline = time.monotonic() + budget_seconds          # hard wall-clock box (#3)
for entity in select_batch(db, source, budget, now):
    if time.monotonic() > deadline:
        break                                          # defer rest to next run
    try:
        data = fetch(source, entity, since=cursor[entity])
        upsert(db, data)                               # idempotent (below)
        commit_ledger(db, source, entity,              # checkpoint AFTER write
                      last_ok_at=now, next_due_at=now+interval,
                      cursor=new_cursor, consecutive_failures=0)
    except RateLimited as e:
        defer(db, source, entity, cooldown_until=now + (e.retry_after or backoff))
    except Exception:
        bump_failures(db, source, entity)              # cooldown after K fails
```

Idempotency is *free* in your stack — `numeric_base.write_rows()` already dedups on `dedup_key` (`source|entity|metric|day`), so re-running a partial batch overwrites rather than duplicates. Keep an overlap window (re-read last 1–2 days on time-bounded sources) so late/edited upstream rows are caught. ([idempotent pipelines](https://medium.com/towards-data-engineering/building-idempotent-data-pipelines-a-practical-guide-to-reliability-at-scale-2afc1dcb7251); [overlap window](https://unstructured.io/insights/incremental-data-ingestion-strategies-for-continuous-pipelines))

### 4d. The decoupling (split `daily_ingest.ps1` → two Task Scheduler jobs)

| Job | Cadence (Task Scheduler) | Lines from today's monolith | Touches network? |
|---|---|---|---|
| **`collect.ps1`** | every 60 min (or 2–3×/day) | sections **A, B, B.5, B.6** (all adapters) + **E.5** encoder | Yes — time-boxed per source |
| **`build_publish.ps1`** | fixed daily slot (e.g. 09:00) | sections **C, D, E, F, G, H, I, J, K** (aggregate → models → build → publish) | **No source fetching** — reads SQLite only |

The build reads whatever SQLite holds *now*. If `collect.ps1` is mid-run or GDELT failed, the site ships yesterday's values. Section K (`publish_to_vercel.ps1`) is already gated and resilient — it stays as-is. Per-source time budgets in `collect.ps1` mean no adapter can run away with the clock. Keep your existing `$script:FailedSteps` + Healthchecks dead-man's-switch in **both** jobs.

### 4e. SQLite concurrency (only if you make `collect.ps1` fetch concurrently)

If you parallelize fetches (optional optimization, not required): fan out fetches with `ThreadPoolExecutor(max_workers=5–10)` **per source**, funnel **all writes through one dedicated writer thread** fed by a `queue.Queue`, one `BEGIN IMMEDIATE` transaction per drained batch. SQLite WAL gives unlimited readers + exactly one writer — never write from multiple threads. Set on the writer: `journal_mode=WAL`, `busy_timeout=5000`, `synchronous=NORMAL`, `wal_autocheckpoint=4000`; keep your existing `mmap` + `temp_store=memory` (commit 6322620). The build opens **read-only** connections and reads concurrently without blocking. ([SQLite WAL](https://sqlite.org/wal.html); [single-writer queue](https://oldmoe.blog/2024/07/08/the-write-stuff-concurrent-write-transactions-in-sqlite/)) **For your volume, sequential collection is fine — treat concurrency as a later nicety, not part of the core fix.**

---

## 5. Build/publish resilience

**Incremental rebuild: NO, not now.** Your 5-min full build for ~27k pages is genuinely fine for a daily (or few-times-daily) cadence. Incrementalizing it now is premature optimization. The honest trigger to build it is *freshness*: once collect runs hourly and you want to publish 6–24×/day, a full rebuild + full re-upload each time wastes effort. At that point add **output-side content hashing first** (a `manifest.json` of `{path: sha256}`, always-rebuild the few aggregate pages — homepage/rankings/conference/board — hash the long tail; ~1 day, near-zero risk), and only later input-side `sqlite-chronicle` dirty-tracking if render time itself becomes the bottleneck. Do **not** adopt Next/Astro/Gatsby ISR — bolting your Python generator onto a JS build graph is pure lock-in; use their dependency-graph idea only as a mental model. ([11ty incremental](https://www.11ty.dev/docs/usage/incremental/); [sqlite-chronicle](https://github.com/simonw/sqlite-chronicle))

**How the site ships even if a collector is slow/failed — this is the whole point of #2:**
1. **Build reads SQLite, never the network.** A dead/slow collector cannot block it. Worst case the site is one day stale on that one signal — graceful degradation your "Awaiting Signal" fallback already handles.
2. **Per-source time box** (#3) caps any collector; the rolling window absorbs the remainder next run.
3. **Publish is already hardened** in `publish_to_vercel.ps1`: file-count gate (≥3500), `verify-publish-readiness` data-quality gate, `_build_manifest.json` <26h freshness gate, 4-attempt deploy retry with backoff, explicit alias rotation, post-deploy HEAD health check. Keep all of it. The only addition worth making: **smoke-check the per-deploy URL before `vercel alias set`** so a bad deploy never becomes live (your CLAUDE.md already notes the per-deploy URL is the source of truth). ([Vercel 15k-file limit → archive](https://vercel.com/docs/limits); [alias rotation pattern](https://vercel.com/docs/cli/deploy))
4. **Vercel Hobby headroom:** at a daily/few-times-daily cadence you're nowhere near 100 deploys/day; `--archive=tgz` keeps you under the 15k-file wall. Only consider Pro ($20, in budget) if you move to publish-every-15-min. ([Vercel limits](https://vercel.com/docs/limits))

---

## 6. Implementation plan, sequenced for a solo vibecoder

Ordered lowest-risk → highest-value-per-effort. Steps 1–3 alone fully prevent a repeat of the incident.

| # | Step | What to build | Effort | Risk |
|---|---|---|---|---|
| **1** | **Decouple the monolith.** | Copy `daily_ingest.ps1` → `collect.ps1` (keep sections A,B,B.5,B.6,E.5) and `build_publish.ps1` (sections C–K). Register two Task Scheduler jobs (reuse `register_daily_task.ps1` pattern). `build_publish` does zero adapter calls. | ~3–4 h | **Low.** Pure reorg; both still exit 0 on adapter failure. Test by running each by hand once. |
| **2** | **Bulk GDELT (BigQuery primary).** | One GCP project + service-account JSON; `pip install google-cloud-bigquery`; rewrite `gdelt_volume.py` `fetch()` to one parameterized query (partition-filtered, `maximum_bytes_billed` cap, `--dry_run` self-check). `parse()` buckets `V2Organizations` via the alias map. Delete `max_collection_tier`/`consecutive_fail_abort`/76-cap. | ~1 day | **Med.** Mostly the alias map + GCP auth. De-risk with the dry-run cap; keep old adapter behind an env flag for one cycle. |
| **3** | **Alias map + homonym guards.** | Extend `priority_teams` with an alias array per team; hand-curate 138 entries; explicit guards for Miami/Washington/Buffalo/Oregon. | ~half day | **Low** but tedious; this is the accuracy bottleneck — spot-check counts vs known busy weeks. |
| **4** | **GDELT bulk-file fallback.** | `scripts/gdelt_bulk_fallback.py`: download trailing-24h GKG via `lastupdate.txt` (plain HTTP, honest UA), parse locally, same alias map → same SQLite rows. Wire as failover if the BigQuery step errors. | ~half day | **Low.** Reuses the alias map + parse path. |
| **5** | **Ledger + time-box for remaining/future slow sources.** | Add `collection_ledger` migration + `select_batch()`/`commit_ledger()` helpers + a per-source `budget_seconds` deadline in `collect.ps1` adapters. Apply to YouTube/SeatGeek/any future per-entity source. | ~1 day | **Med.** New shared code path; ship behind a feature flag, validate one source first. |
| **6** | **(Defer) Output-side content-hash manifest.** | `manifest.json` of `{path: sha256}`; always-rebuild aggregates, hash the long tail; only emit changed files. Do *only* when you start publishing intraday. | ~1 day | **Low**, but **don't do it yet** — no payoff at daily cadence. |

---

## 7. What to explicitly NOT do (over-engineering traps)

- **Do NOT keep tuning the per-team GDELT loop** — better backoff, AIMD, token buckets, rotation. The loop itself is the bug; bulk pull deletes it. (Rotation/AIMD belong only to sources that *must* stay per-entity, of which you'll have none after #2.)
- **Do NOT add Prefect / Dagster / Airflow / Redis / Kafka.** A prior pass already rejected these; SQLite is your durable buffer and Task Scheduler is your scheduler. Two `.ps1` files + one ledger table is the entire orchestrator.
- **Do NOT build incremental rendering now.** The 5-min build is not a problem at daily cadence. It's premature until you publish many times a day.
- **Do NOT adopt a JS SSG (Next/Astro/Gatsby) for incrementality.** Massive lock-in to retrofit a custom Python generator; use their dependency-graph *idea*, not their build.
- **Do NOT pay for GDELT Cloud or any commercial news API.** Free BigQuery + bulk covers all 138 daily at $0; paid tiers are priced for a handful of queries, not 138 entities/night.
- **Do NOT re-implement the Vercel publish path.** `--archive=tgz`, deploy retry, alias rotation, and the three gates already exist and work — the only delta worth adding is a per-deploy-URL smoke check before the alias flip.
- **Do NOT permanently overcut coverage** (the `max_collection_tier=2` band-aid). Bulk restores all 138 at zero time cost; delete the cap rather than living with it.
- **Do NOT parallelize SQLite writes across threads.** WAL allows exactly one writer; if you ever add concurrent fetching, funnel writes through a single writer thread. For your volume, sequential is fine — don't add concurrency machinery you don't need.

**Files this touches:** `src/cfb_rankings/ingest/sources/gdelt_volume.py` (rewrite to bulk), `src/cfb_rankings/migrations.py` (ledger + alias columns), `scripts/daily_ingest.ps1` (split into `scripts/collect.ps1` + `scripts/build_publish.ps1`), `scripts/register_daily_task.ps1` (register both jobs), new `scripts/gdelt_bulk_fallback.py`. `scripts/publish_to_vercel.ps1` stays essentially as-is.

---

## Appendix: key facts by angle

### gdelt
- GDELT DOC 2.0 API's current client-facing limit is one request per 5 seconds (literal error: 'Please limit requests to one every 5 seconds'), reproduced Jan 2026 — so 138 teams = ~11.5 min floor before any 429 backoff. (high) https://h-toss.com/gdelt-api-request-failed-please-limit-requests-to-one-every-5-seconds/
- GDELT does not publish an exact QPS/req-per-day number; it tunes the limiter dynamically to protect its ElasticSearch clusters, noting a 0.001 QPS change moves its 429 rate ~5%. (high) https://blog.gdeltproject.org/behind-the-scenes-api-quotas-the-impact-of-a-fraction-of-a-qps/
- A second 429 cause is a missing User-Agent header — GDELT now blocks UA-less requests; setting an honest UA removes that class of 429s but not the 5s ceiling. (high) https://github.com/alex9smith/gdelt-doc-api/issues/22
- GDELT 2.0 publishes a new file set every 15 minutes; the live English GKG file is ~3.8 MB compressed per 15 min (~365 MB/day English), each row carrying a V2Organizations NER field — verified live via lastupdate.txt during this research. (high) http://data.gdeltproject.org/gdeltv2/lastupdate.txt
- The GKG V2 V2Organizations field lists every organization NER-extracted per article (semicolon-delimited with char offsets), so one bulk GKG download can yield all 138 per-team counts via local aggregation. (high) http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf
- GDELT's public BigQuery dataset is still live and free-tier-queryable in 2026, updated every 15 minutes. (high) https://www.gdeltproject.org/data.html
- BigQuery free tier is the first 1 TiB scanned/month, then $6.25/TiB on-demand. (high) https://cloud.google.com/bigquery/pricing
- Using the partitioned table gdelt-bq.gdeltv2.gkg_partitioned, a 15-day query scans 15 GB (vs 423 GB unpartitioned) — ~1 GB/day full-row, far less for a 2-column DATE+V2Organizations scan. (high) https://blog.gdeltproject.org/announcing-partitioned-gdelt-bigquery-tables/
- A daily per-entity GKG rollup therefore scans roughly 30 GB/month (~3% of the free tier) = $0/month for a solo dev. (high) https://blog.gdeltproject.org/using-bigquery-table-decorators-to-lower-query-cost/
- GDELT explicitly recommends the Web NGrams 3.0 bulk dataset (downloaded per minute, no API calls) as the rate-limit-free replacement for the DOC API for high-volume querying. (high) https://blog.gdeltproject.org/ukraine-api-rate-limiting-web-ngrams-3-0/
- Media Cloud is free, nonprofit, 200M+ stories, exposes an 'attention over time' volume metric, but defaults to 4,000 API requests/week with some endpoints capped at 2 req/min. (high) https://www.mediacloud.org/documentation/faqs
- GNews free tier is 100 requests/day, 1 req/sec, non-commercial only — exceeded on day one at 138 entities. (high) https://gnews.io/pricing
- NewsAPI.org free tier is 100 req/day development-only; paid starts at $449/month. (high) https://newsapi.org/pricing
- NewsAPI.ai / Event Registry free plan is 2,000 searches one-time with no historical data — burns out in ~2 weeks at 138/day. (high) https://newsapi.ai/plans
- A separate paid GDELT Cloud (gdeltcloud.com) appeared by 2026 with API keys, Query Units, per-minute caps and monthly quotas — distinct from the free api.gdeltproject.org DOC API and not needed for this use case. (med) https://docs.gdeltcloud.com/developers/api-keys
- Academic literature rates Media Cloud's open-web coverage and documentation above GDELT's, while GDELT's NER entity extraction is designed for noisy news but still has duplicate-entity and coverage caveats. (med) https://arxiv.org/pdf/2104.03702

### orchestration
- The root cause is architectural coupling, not source slowness: a rate-limited low-velocity source (GDELT) sits inline/synchronous on the same path as the must-publish-on-time build, so its grind blocks publish — fix by decoupling, not by tuning the source. (high) https://codelit.io/blog/async-processing-patterns
- Moving slow work off the critical path via a producer-writes/worker-drains decoupling (outbox-style) keeps the deadline-bearing path from being blocked by any one slow stage; the durable log can just be a database table, no broker needed. (high) https://www.milanjovanovic.tech/blog/implementing-the-outbox-pattern
- Crawlers solved the 'too many entities, finite budget' problem with crawl-budget + stale-first scheduling: assign each entity a next-crawl time and rotate, recrawling frequently-changing/important entities more often. (high) https://developers.google.com/crawling/docs/crawl-budget
- A staleness/decay engine should drive re-collection from metadata (time since last update + degree of staleness jointly), not a fixed 'everything every night' schedule. (high) https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8452733
- Fixed N-retries amplify load on a failing service ('1+N times the work at 100% failure'); a retry token budget (deposit ~0.1 token on success, consume 1 per retry) makes retries self-regulate as failure rate climbs. (high) https://brooker.co.za/blog/2022/02/28/retries.html
- Always honor the server's Retry-After header on 429 — computing your own backoff means waiting too long or too short; Retry-After overrides your schedule. (high) https://easyparser.com/blog/api-error-handling-retry-strategies-python-guide
- Token bucket is the canonical client-side pacing primitive (used by AWS API Gateway, NGINX, Stripe): refill at a steady rate, consume a token per request, wait when empty. (high) https://oneuptime.com/blog/post/2026-01-22-token-bucket-rate-limiting-python/view
- AIMD adaptive concurrency auto-discovers an undocumented rate limit: +1 to concurrency on sustained success, multiply by ~0.5-0.9 on a 429/latency spike — settling at the safe rate instead of hand-guessing a team cap. (high) https://www.michal-drozd.com/en/blog/adaptive-concurrency-limits/
- Exponential backoff must use jitter (full or decorrelated) and a cap (~30s rule of thumb) to avoid synchronized retry spikes; sane defaults: base 0.5-1s, <=5 attempts, retry only {429,500,502,503,504}, never retry 4xx except 429. (high) https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
- A circuit breaker (CLOSED->OPEN->HALF_OPEN) stops hammering a dead/limited service; for a build-with-a-deadline, opening the breaker and deferring the remaining batch to the next rotation run is the right call. (high) https://dev.to/caraxesthebloodwyrm02/your-python-api-calls-will-fail-heres-how-to-handle-it-1pk9
- Idempotent loads (stable keys + upsert/merge) plus per-entity watermark checkpoints let a partial/failed run resume cleanly with no duplicates; commit the checkpoint only after the data write succeeds. (high) https://medium.com/towards-data-engineering/building-idempotent-data-pipelines-a-practical-guide-to-reliability-at-scale-2afc1dcb7251
- An overlap window (re-read a small slice before the high-water mark, dedupe via idempotent upsert) catches late/edited upstream writes that strict incremental cursors would miss. (med) https://unstructured.io/insights/incremental-data-ingestion-strategies-for-continuous-pipelines
- SQLite WAL gives unlimited concurrent readers alongside one writer, but does NOT allow concurrent writers — SQLite always serializes writes (exactly one write lock at a time). (high) https://sqlite.org/wal.html
- The robust pattern for write-heavy SQLite is to serialize all writes through one dedicated writer thread fed by an in-process queue, while fetching in parallel; batch many writes per transaction for throughput. (high) https://oldmoe.blog/2024/07/08/the-write-stuff-concurrent-write-transactions-in-sqlite/
- Set busy_timeout on every SQLite connection (costs nothing, eliminates most SQLITE_BUSY), use synchronous=NORMAL with WAL, BEGIN IMMEDIATE for writes, and raise wal_autocheckpoint (e.g. ~4000 pages) under write-heavy bursts. (med) https://www.dev.to/software_mvp-factory/sqlite-wal-mode-and-connection-strategies-for-high-throughput-mobile-apps-beyond-the-basics-eh0
- Bound I/O-bound fetch concurrency with asyncio.Semaphore (new code) or ThreadPoolExecutor max_workers (legacy), ~5-10 concurrent per source as a polite start; the concurrency cap and the rate cap should be the same AIMD-driven dial. (high) https://medium.com/@mr.sourav.raj/mastering-asyncio-semaphores-in-python-a-complete-guide-to-concurrency-control-6b4dd940e10e
- A database-as-queue (status pending->processing->done, claim oldest) is enough for single-box async work; for one writer you don't even need SKIP LOCKED — 'next_due_at <= now' on the ledger is your pending set. (med) https://dev.to/damikaanupama/designing-asynchronous-apis-with-a-pending-processing-and-done-workflow-4gpd

### currency

### build_publish
- Vercel enforces a HARD limit of 15,000 source files per CLI deployment; deployments over this fail at the build step — your ~27k-page site is ~1.8x over and must use --archive (high) https://vercel.com/docs/limits
- `vercel deploy --archive=tgz` compresses the deploy into a few tarball parts, is the documented fix for 'thousands of files,' and as of 2025-02-11 split-tgz is the default tgz behavior (~30% faster uploads) (high) https://vercel.com/changelog/split-tgz-is-now-the-default-cli-archive-deployment-behavior
- Raw multi-thousand-file uploads can trip Vercel's upload-rate limit and lock the account out of deploying for 24 hours; --archive avoids it (high) https://github.com/vercel/vercel/issues/14472
- Vercel static source-upload size cap is 100 MB on Hobby vs 1 GB on Pro; your 1.46 GB SQLite is a build input and must never be deployed (high) https://vercel.com/docs/limits
- Hobby plan rate limits: 100 deployments/day, 100 builds/hour, 5,000 uploads/day; hitting them locks you out ~24h (api-deployments-free-per-day). Pro raises these to 6,000/day, 450/hr, 40,000 uploads/day (high) https://vercel.com/docs/limits
- Serving static HTML is NOT counted as a 'build' for the builds-per-hour limit; only functions/framework builds count (high) https://vercel.com/docs/limits
- `vercel deploy --prebuilt` fully decouples deploy from build so Vercel never rebuilds your custom-generated pages; prebuilt static files never expire (atomic/immutable) (high) https://vercel.com/docs/cli/deploy
- The documented alias-rotation pattern is: capture deploy URL from stdout, then explicitly `vercel alias set <url> <alias>` (or `vercel promote`) — aliasing does not always auto-rotate (high) https://vercel.com/docs/cli/deploy
- --archive's downside: it negates Vercel's per-file upload caching, so unchanged files re-upload each time — making output-side content-hashing valuable to shrink what changes (high) https://vercel.com/docs/cli/deploy
- Decoupling producers (collectors) from consumers (build) via a shared store is the 2025-26 standard for resilient pipelines; SQLite itself is your buffer — no Kafka/queue needed (high) https://www.kdnuggets.com/the-complete-guide-to-building-data-pipelines-that-dont-break
- simonw/sqlite-chronicle adds a triggered _chronicle table with an indexed monotonic __version per row, letting a builder query exactly 'what changed since version N' for incremental rendering (high) https://github.com/simonw/sqlite-chronicle
- GDELT publishes no hard QPS number; their own data shows a 0.001 QPS fleet change flipped 429 rate from ~0% to 5% — you must stay well under ~1 QPS and space requests with jitter (high) https://blog.gdeltproject.org/behind-the-scenes-api-quotas-the-impact-of-a-fraction-of-a-qps/
- GDELT DOC API now rejects requests lacking a browser-like User-Agent header with what looks like a rate-limit error even at low volume; adding a real UA is a free fix (med) https://github.com/alex9smith/gdelt-doc-api/issues/22
- Exponential backoff WITH JITTER (not fixed 30s) is required so concurrent retries don't synchronize into fresh 429 bursts (high) https://www.ayrshare.com/complete-guide-to-handling-rate-limits-prevent-429-errors/
- Eleventy/Gatsby incremental builds work by tracking a template→layout→data dependency graph and rebuilding all dependents of a changed input — the mental model to copy for shared/aggregate pages (high) https://www.11ty.dev/docs/usage/incremental/
- Vercel max build step duration is 45 min and there is no upper limit on OUTPUT files (only the 15k SOURCE-file upload limit matters for a prebuilt static site) (med) https://vercel.com/docs/limits
