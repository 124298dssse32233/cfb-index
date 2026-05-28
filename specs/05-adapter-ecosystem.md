# WS-05 — Adapter Ecosystem Live

**Phase:** 1–2 (Jun–Sep 2026)
**Owner:** Claude execution
**Status:** Blocked on WS-01 (`numeric_observations` table)

## Goal

Get all 84 configured sources actually emitting rows. Today: 2 of 84 work. The schema and adapters mostly exist; the work is debugging, target-table creation, and loud-fail enforcement.

## Definition of perfect

- All 7 numeric adapters writing to `numeric_observations`: Wikipedia pageviews, Wikipedia edits, GDELT article counts, Kalshi, Polymarket (migrated from `source_observations`), SeatGeek, YouTube view-velocity, Spotify chart positions, Bluesky post counts.
- Per-team-subreddit conversation ingestion active for all 119 FBS via the deep offseason workflow on weekly cron (post bucket-label fix).
- Beat-writer RSS + Locked On podcast RSS + Substack RSS all writing to `conversation_documents`.
- 6 message-board scrapers (TideFans, ShaggyBevo, Volnation, EleverWarriors, TigerDroppings, ShakingTheSouthland) running on daily cadence.
- All 6 audience buckets actually used: fan / rival / national / media / recruit / insider.
- `freshness_page.py` exposes every adapter's last-success timestamp.
- CI alerts when any adapter is >48h stale.

## Current state

- 84 sources in `source_registry`. 2 emit data (Reddit r/CFB collector + Polymarket).
- 7 numeric adapters silently fail because their target tables don't exist (`wiki_pageviews`, `seatgeek_listings`, etc. all MISSING).
- All 8,005 target rows are `audience_bucket='national'` (single bucket).
- `freshness_page.py` exists but doesn't reflect adapter health.

## Dependencies

- **Blocks:** WS-02 (classifier needs Layer 1 + 2 + 3 data), WS-09 (calibration ledger reads markets), Chronicle pipeline diversification (D-004)
- **Blocked by:** WS-01 (numeric_observations table)

## Implementation approach

1. Wait for WS-01 to create `numeric_observations`.
2. Triage 7 silent adapters in parallel — `/octo:parallel` is appropriate here (independent debugging):
   - Wikipedia: confirm pageview API endpoint
   - GDELT: confirm doc.api query format
   - SeatGeek: verify `SEATGEEK_CLIENT_ID` secret
   - YouTube: verify `YOUTUBE_API_KEY` + quota
   - Spotify: confirm public-charts URL
   - Kalshi: confirm CFB markets exist
   - Bluesky Jetstream: likely needs real handler debugging
3. Apply 6-bucket migration (per D-006) to backfill existing 8,005 rows from `'national'` to correct bucket keyed on `source_name + source_channel`.
4. Schedule deep offseason workflow on weekly cron (Saturday on self-hosted runner).
5. Define adapter contract: every `run()` returns `AdapterResult(rows_written, errors, skipped_reason)`. Workflow reads result.
6. Update `freshness_page.py` to surface per-adapter health.

## Running gate

- `numeric_observations` has ≥500 rows from ≥4 distinct adapters within 7 days of deploy.
- `conversation_document_targets` has rows in ≥3 distinct buckets within 30 days.
- Freshness page renders every adapter; CI alerts on >48h staleness.

## Decisions

- D-006 — 6-bucket taxonomy — LOCKED
- D-017 — Octopus invocation policy — OPEN (affects whether adapter triage uses `/octo:parallel`)

## Pointers

- `src/cfb_rankings/ingest/sources/*.py` (12 adapters)
- `tools/run_adapter.py` (workflow runner)
- `.github/workflows/ingest_hourly.yml` + `ingest_daily.yml`
- VISION § 6 (5-layer signal model)
