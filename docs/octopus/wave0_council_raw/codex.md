## Executive Verdict

The proposal is directionally sound, but it conflates four separate concepts:

1. What should exist.
2. What should run.
3. What actually ran.
4. Whether the resulting data is usable.

`source_registry`, `collection_ledger`, and `scrape_health` currently answer different subsets of those questions. Treating historical `scrape_health` rows as the active instance inventory will produce both false alarms and blind spots.

The missing primitive is a **desired source-instance inventory**. Add that before building the dashboard or alert automation.

## 1. Uncaught Failure Modes

The proposed checker could remain green when:

- A collector reports `status='success'` but inserts zero rows.
- Rows were inserted but all belong to the wrong season, entity, or run.
- A partial run overwrites complete historical data.
- A collector succeeds using cached or unchanged upstream data.
- `rows_inserted` is positive but duplicates existing rows.
- Data is collected on time but not processed into downstream tables.
- Collection succeeds after the static-site build, so production remains stale.
- A source disappears without emitting another `scrape_health` row.
- A class remains registered while an expected instance is never created.
- A stale historical instance is mistaken for an active expected instance.
- The latest attempt is an error even though an immediate retry succeeds, or vice versa.
- A collector writes NULL/invalid timestamps, future dates, or malformed identifiers.
- Coverage exists for every team but is severely incomplete within each team.
- Team identity drift creates duplicate aliases or orphan foreign keys.
- Schema changes silently alter column meaning or type affinity.
- Snapshot comparisons hide gradual degradation because only sudden drops trigger.
- A build uses a different DB file than the checker inspected.
- Health checks pass, then later pipeline stages mutate the DB.

Add an explicit **pipeline-boundary identity check**: DB path, file size, modification time, schema hash, selected row counts, and ideally a cheap content fingerprint must match between health verification and `verify_build_manifest.py`.

## 2. Completeness and Integrity

Season×team presence is necessary but too weak. Define dataset contracts with cheap SQL assertions.

### Recommended contract fields

Each spine dataset should declare:

- Expected grain, such as one row per `game_id, team_id`.
- Primary or natural key columns.
- Required non-null columns.
- Parent references.
- Valid season range.
- Expected entity universe.
- Minimum records per entity-season.
- Allowed categorical values.
- Dataset-specific invariants.
- Freshness timestamp semantics.

### Cheap checks

Run these using indexed `COUNT`, `GROUP BY`, and anti-joins:

- **Duplicate grain:** grouped key count greater than one.
- **Required nulls:** NULL counts for identifiers, season, team, and measured value columns.
- **Orphans:** child rows with no matching game, player, team, source, or season parent.
- **Impossible values:** negative attempts, wins exceeding games, invalid dates, season/date mismatch.
- **Cross-table reconciliation:** team game totals versus games; player stats reference scheduled games.
- **Symmetry:** each FBS-vs-FBS game has the expected team-side records.
- **Density:** rows per team-season and rows per game, not merely presence.
- **Distribution drift:** median and selected percentiles versus recent complete seasons.
- **Schema drift:** compare `PRAGMA table_info`, indexes, and foreign keys against a checked-in signature.
- **Temporal holes:** missing weeks or long date gaps inside otherwise populated seasons.
- **Provenance validity:** non-NULL `source_id` must reference a known source, not just be populated.

Do not use one universal “within 10%” rule. A 9% deficit in `games` is severe; a 15% change in conversation volume may be normal. Thresholds belong to each dataset contract.

Also classify intentionally unavailable data explicitly. The empty `plays` and `drives` tables should be either:

- Required and red.
- Deferred with an owner and target date.
- Out of scope and excluded.

Never let zero-row tables sit ambiguously in the health score.

## 3. Cadence and SLA Model

Class-level cadence is a useful default, but it is not a sufficient operational backbone.

### Separate four timestamps

For every expected instance, track:

- `due_at`: when collection should start.
- `completed_at`: when the collector successfully finished.
- `data_through`: newest upstream event/date represented in its output.
- `processed_at`: when downstream processing consumed that output.

“Ran successfully” is not equivalent to “contains current data.”

### Define “process when I want”

Use a verifiable schedule contract:

```text
schedule timezone
schedule rule or interval
allowed start window
completion deadline
maximum upstream lag
grace period
expected output behavior
```

Example:

```text
Run daily at 04:00 America/New_York
May start from 03:45–04:15
Must complete by 05:00
Data must be current through previous calendar day
Zero rows allowed only when explicitly marked no_change
```

### Handling the 433 unenrolled instances

Do not manually seed 433 ledger rows from historical health logs. First establish the expected inventory.

Recommended model:

```text
source class
instance key
active state
cadence override, optional
expected output dataset
first expected date
retired date
```

Then reconcile:

```text
expected instances
LEFT JOIN collection_ledger
LEFT JOIN latest scrape_health
```

This produces clear states:

- Expected and healthy.
- Expected but never enrolled.
- Expected but never observed.
- Observed but not expected.
- Retired.
- Temporarily disabled.
- Overdue.
- Failed.
- Successful but stale upstream data.

Populate missing ledger rows deterministically from that inventory. `scrape_health` should remain an observation log, not define what should exist.

A `podcast_asr` due date in 2027 should be reported as a **schedule anomaly**, even if it is technically not overdue. Add maximum permitted scheduling horizon by cadence class.

## 4. Measurable Headline Metrics

Avoid a blended 0–100 score as the primary result. Averages hide critical failures. Present five pass rates plus a hard overall state.

1. **Coverage**
   - Passing required entity-period cells / expected required cells.
   - Show exact missing cells.

2. **Schedule Compliance**
   - Instances completed within their deadline / instances due during the measurement window.

3. **Data Currency**
   - Instances whose `data_through` meets maximum upstream lag / active expected instances.

4. **Contract Integrity**
   - Passing required assertions / required assertions evaluated.
   - Any critical key, orphan, or reconciliation failure forces red.

5. **Provenance**
   - Canonical records with valid verified provenance / eligible canonical records.
   - Show both level and seven-/30-day change.

Also show:

- Active expected instances.
- Never-seen instances.
- Overdue instances.
- Current failures.
- Unclassified observed instances.
- Last successful end-to-end build.
- DB fingerprint used by the last deployed build.

Overall status should use gates:

- **Red:** any critical contract failure, missed mandatory dataset/season, overdue critical source, corrupt DB, or failed build identity check.
- **Yellow:** non-critical SLA misses, degrading provenance, unclassified sources, or warning thresholds.
- **Green:** all required gates pass.
- **Unknown:** checker could not evaluate a required assertion.

“Unknown” must not collapse into green.

## 5. Leaner Design

Do not introduce Great Expectations or another framework here. For one SQLite database, it adds dependencies and abstraction without removing the need to define project-specific contracts.

Adopt the **data-contract pattern**, implemented with existing primitives:

- Checked-in Python contract definitions.
- Raw SQLite assertions.
- JSON report artifact.
- Existing GitHub issue helper.
- Existing build-manifest verification.
- Existing row-floor checks invoked or imported rather than duplicated.

Keep `verify_data_health.py` as an orchestrator. It should call reusable checks from `verify_data_floors.py`, coverage auditing, manifest verification, and cadence reconciliation.

I would avoid `source_change_log` initially. Source changes can be derived by comparing the current reconciled inventory with the previous snapshot. A separate mutable event log creates synchronization and duplicate-event problems. Add it only if durable event history proves necessary.

Snapshots should store one run header plus normalized result rows or a versioned JSON payload. One wide aggregate row will be difficult to query and migrate.

## 6. Sequencing and Risk

Recommended sequence:

1. **Define terminology and contracts**
   - Expected, observed, enrolled, successful, current, processed, retired.

2. **Create desired instance inventory**
   - Reconcile the 443 observations and classify all 370 orphans.
   - Do not silently auto-accept prefix mappings.

3. **Repair immediate known failures**
   - Athletics errors, `gdelt_volume`, 2027 schedules, missing provenance writes.

4. **Build checker without persistence or dashboard**
   - Produce deterministic JSON and console output.
   - Run against known-good and deliberately damaged DB copies.

5. **Add dataset integrity contracts**
   - Start with `games`, `player_game_stats`, and provenance.

6. **Add snapshots and trend comparisons**

7. **Wire pre-build and post-build verification**
   - Confirm the same DB artifact was checked and built.

8. **Add issue alerting**

9. **Build the dashboard last**

The biggest risk is creating a polished monitor over an undefined source universe. That would make false confidence systematic.

A secondary risk is alert noise. Start alerts only after at least several shadow runs establish baselines and expose misclassification.

The checker should be non-critical during calibration, but critical spine failures should eventually block publish. Otherwise “red” means production knowingly ships unhealthy data, which conflicts with the goal.

## 7. Recommendations on Open Questions

### A. Class-level SLA first

Use class-level values as defaults, with instance overrides supported from day one. The data model should not require migration when one podcast, subreddit, or athletics source needs a different schedule.

### B. Prefix-map the 370 orphans

Generate proposed mappings automatically, but require reviewed mappings in checked-in configuration. Prefixes can collide, drift, or encode entities incorrectly. Unmapped observations should remain visible as `unclassified`, not disappear into a guessed parent.

### C. Daily scheduled check

Run:

- At the start of the box pipeline.
- After collection/processing and before build.
- After build/manifests.
- Once daily independently of the build.

A single daily check cannot distinguish scheduler failure from collector failure and may inspect data before it was due.

### D. Missing season / 10% thresholds

Reject the universal defaults.

Use contract-specific severity:

- Missing required season: red.
- Missing any expected game for a completed historical season: red.
- Missing teams or weeks: red or yellow according to dataset criticality.
- Volume deviation: dataset-specific absolute and relative thresholds.
- Current/in-progress seasons: separate expectations from completed seasons.
- Unknown expected denominator: unknown, never green.

Finally, rename “SLA” to **schedule contract** internally unless Kevin is promising service to external customers. It is more precise: the system is verifying desired timing, completion, currency, and processing, not merely elapsed freshness.
