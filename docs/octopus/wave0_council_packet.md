# Council Evidence Packet — Refine the "Data Health Spine" spec

**Your role (external council):** critique and refine the spec below. Challenge assumptions, find failure
modes, propose simpler/better approaches, and name data-quality best practices we're not applying. You do
NOT have live DB access — treat the "verified facts" as ground truth (Claude verified them in-repo and will
re-verify every suggestion you make before accepting it). Consensus is not evidence; repo verification wins.
Be concrete and actionable, not generic. Prefer reusing existing primitives over new infrastructure.

## The goal (owner: Kevin, a product dev; infra/devops beginner)
"I simply want to be sure my data is **perfect** and being **processed when I want**." Concretely:
(1) data is filled with no silent gaps; (2) it's healthy (not empty/corrupt/erroring); (3) every source
updates at a **cadence Kevin sets**, and he's told when something falls behind; (4) the system reflects
sources being added/removed. This is a static-site CFB analytics product: Python generator → SQLite
(`cfb_rankings.db`, ~192 tables) → ~69k HTML pages → Vercel. Box-first (nightly local build + full-snapshot
deploy). Hard constraints: no new paid APIs / no cost increase; no live-game data; existing locked design
system; never blind-mutate the DB (migrations/scripts only).

**Locked decisions:** the cockpit is **internal-only** (not a public page); alerts are **GitHub issues**.

## Verified repo facts (ground truth, 2026-06-11)
- **Source model is class→instance, not flat.** `source_registry` = 79 source *classes* (e.g. `reddit_city`,
  `polymarket`, `gdelt_tone`), 84 rows with an `is_active` flag. `scrape_health` = **443 instances**
  (per-run log: `source_id, run_date, rows_inserted, status, error_message, timestamps`). 370 instances have
  no registered parent, grouped by prefix: `reddit_*`×159, `google_*`×140, `athletics_*`×21, `campus_*`×15,
  `board_*`×12, `substack_*`×9.
- **`collection_ledger`** (cadence) = `source, entity, last_ok_at, next_due_at, consecutive_failures,
  cooldown_until` — but only **10 instances enrolled**; the other ~433 have no due-date tracking.
- **Live problems nobody is being told about:** ~6 `athletics_*` sources show `status='error'` today;
  `gdelt_volume` is failing (NULL last_ok_at, consecutive_failures≥1); some `podcast_asr` instances aren't
  due to re-collect until 2027.
- **Completeness gaps:** `games`/`player_game_stats` are **missing 2023 entirely**; 2020 & 2022 are partial;
  play-by-play (`plays`/`drives`) = 0; advanced stats (`team_game_advanced_stats`) = 2025-only.
- **Provenance:** 22.3% of conversation docs have a verified `source_id`; the rest are honestly labeled
  `legacy_unverified`; legacy collectors still write NULL source_id (the % drifts down over time).
- **Existing primitives to reuse (don't reinvent):** `source_registry`, `scrape_health`, `collection_ledger`,
  CLI `audit-data-coverage` / `scrape-health` / `refresh-local-health`, and Session-2 guards
  `verify_data_floors.py` (row-floor ratchet + provenance), `verify_module_coverage.py` (has a working
  `--open-issue` → `gh issue create`), `verify_build_manifest.py`. Box pipeline = `scripts/build_publish.ps1`.

## Proposed design (critique this)
**Checker** `verify_data_health.py` (+ `manage.py data-health`), stdlib + raw sqlite3, runs in the box build
(non-Critical) + a daily scheduled run. Evaluates 4 dimensions, each green/yellow/red, writes a
`data_health_snapshot` row (for trends) + report JSON; non-zero exit on red:
1. **Completeness** — per spine dataset, actual vs expected season×team coverage → gap list.
2. **Freshness/Cadence** — per active class+instance, last `scrape_health` success vs a per-source **SLA Kevin
   sets**; `now > last_ok + cadence + grace` or latest `status='error'` → red.
3. **Volume/Integrity** — row floors held + no sudden drop vs last snapshot.
4. **Provenance** — canonical % + trend.

**Config** `data_health/spec.py`: datasets (table, season_range, expected_teams, floor) seeded from
`SPINE_FLOORS`; cadence SLAs per class (daily/weekly/monthly/seasonal/manual + grace_hours).
**New tables:** `data_health_snapshot`, `source_change_log` (logs add/retire/first-seen/orphan events).
**Dashboard:** internal-only, written to a gitignored local path (NOT `output/site/`), reusing design tokens:
source status grid + instance drill-down, season×dataset coverage heatmap, provenance trend, cadence list.
**Alerting:** reuse `--open-issue` → one deduped GitHub issue per regression class; auto-close when green.
**Source-change awareness:** spec derives from `source_registry`, so add→monitored, deactivate→"retired";
new `scrape_health.source_id` → logged.

**7 tasks:** W0.1 source reconciliation (class→instance rollup + prefix-map the 370 orphans) → W0.2 spec
config → W0.3 migrations → W0.4 the checker (first value) → W0.5 change detection → W0.6 dashboard →
W0.7 issue alerts + build wiring.

**Open questions + current defaults:** (a) cadence SLAs at class level only first (per-instance later);
(b) auto-map the 370 orphans by prefix now, fold into registry later; (c) daily scheduled check;
(d) thresholds: missing season=red, ≥10% short=yellow, within 10%=green.

## What we want from you (be specific)
1. **Failure modes the design won't catch** — how could bad/stale/partial data still slip through silently?
2. **Completeness done right** — beyond season×team presence, what integrity checks matter (referential
   integrity, duplicates, nulls in key columns, distribution drift, schema drift)? Cheap ways to do them?
3. **Cadence/SLA model** — is class-level SLA + `collection_ledger` the right backbone? How to handle the
   ~433 instances not in the ledger? How to express "process when I want" precisely + verifiably?
4. **Make "perfect" measurable** — propose a small set of headline health metrics/scores Kevin can trust at
   a glance (and how to compute them cheaply from the existing tables).
5. **Simpler alternative?** — is there a leaner design (or an off-the-shelf pattern: data-contracts,
   freshness SLAs, the "data observability" 5 pillars, Great-Expectations-style assertions) we should adopt
   instead of hand-rolling — given the no-new-cost, internal-only, single-SQLite constraints?
6. **Sequencing/risk** — what should change in the 7-task plan? Biggest risk to call out?
7. **The 4 open questions** — your recommendation on each, with reasoning.
