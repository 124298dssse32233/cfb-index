This critique focuses on moving the "Data Health Spine" from a passive log-viewer to an active enforcement gate, prioritizing cheap, deterministic SQLite queries over complex observability heuristics.

### 1. Failure modes the design won't catch
*   **The "Placeholder Pandemic":** `rows_inserted > 0` is a false signal if the adapter is writing "TBD" or "N/A" into key fields. The design doesn't check for **NULL/empty string density** in primary keys or vital columns (e.g., `game_id`, `player_id`).
*   **Temporal Corruption (The 2023 Gap):** A global row floor (e.g., `games > 7,000`) is blind to a total wipe of a specific year if subsequent years are over-indexed. You could lose the entire 2023 season and stay "Green" if 2024–2026 is healthy.
*   **Join Decapitation:** High row counts in `players` and `games` are useless if `player_game_stats` has broken FKs. You'll ship 69k pages that are technically "there" but empty of stats.
*   **Unit Drift:** Sudden shifts in value distributions (e.g., yards becoming feet, or betting odds shifting from American to Decimal) won't trigger volume floors but will break the UI logic.

### 2. Completeness done right (Cheap SQLite Checks)
Beyond simple counts, implement these "Gold Standard" integrity checks:
*   **Referential Integrity (The Join Gate):**
    ```sql
    -- Check for "Orphaned" stats that won't show up on any game page
    SELECT count(*) FROM player_game_stats WHERE game_id NOT IN (SELECT id FROM games);
    ```
*   **Cartesian Season×Team Coverage:** Hard-code a `target_teams` count per season in your spec.
    ```sql
    -- Flag seasons where team participation has dropped (indicates scrape failure)
    SELECT season, count(DISTINCT team_id) as team_count 
    FROM roster_entries GROUP BY 1 HAVING team_count < @min_expected;
    ```
*   **Null Density Check:** Track `% NULL` in critical columns (e.g., `roster_entries.position`, `games.start_date`). A jump of >5% NULLs in a new batch is a Red exit.
*   **Schema Drift (Cheap Version):** `PRAGMA table_info(tbl_name)` results compared against a saved JSON signature. If a source adds/removes a column, the build should break until the spec is updated.

### 3. Cadence/SLA model
*   **The Backbone:** Class-level SLA is the right start, but `collection_ledger` must be the **source of truth**, not a secondary log.
*   **Fixing the 433 Orphans:** Do not "map" them by prefix; **re-parent** them. If a `scrape_health` row has a `source_id` starting with `reddit_`, and that prefix exists in `source_registry`, the checker should dynamically treat it as an instance of that class.
*   **"Process when I want":** Add a `target_cadence` column to `source_registry`. 
    *   **Verifiable Logic:** `Red` if `now() > MAX(scrape_health.run_date) + source_registry.target_cadence + grace_hours`. 
    *   This removes the need for Kevin to manually enroll instances in the ledger; the registry drives the expectation.

### 4. Make "perfect" measurable
Propose a **"DHS Score" (Data Health Spine)** 0–100, computed as the weighted average of:
1.  **Spine Coverage (40%):** `%` of (Seasons × Target Teams) present in `roster_entries` and `games`.
2.  **Freshness (30%):** `%` of `is_active` source classes currently within their SLA window.
3.  **FK Integrity (20%):** `1 - (orphaned_stat_rows / total_stat_rows)`.
4.  **Provenance (10%):** Existing provenance % from `verify_data_floors.py`.
*   *Cheap Compute:* These are 4 queries that run in <500ms on a ~200MB SQLite DB.

### 5. Simpler alternative?
**Unified CLI "Gatekeeper":** Instead of a new design-system dashboard and new infrastructure, expand `verify_data_floors.py` into `manage.py check-integrity`.
*   Adopt the **"Data Contract"** pattern: A single YAML/JSON file defining every table's expected columns, null-tolerance, and row-floors *per season*.
*   **Why?** Kevin is an "infra beginner." Managing a dashboard is more work than reading a GitHub Issue with a clear SQL snippet showing exactly which rows failed.

### 6. Sequencing/risk
*   **Risk:** W0.1 (Reconciliation) is a "busywork" trap.
*   **Proposed Pivot:** Move **W0.4 (The Checker)** to W0.1. Use hard-coded "Spine Tables" first. Let the checker identify the orphans by failing them. This turns "Reconciliation" into "Fixing the Red Build," which is a better motivator than a manual audit.

### 7. The 4 open questions: Recommendations
*   **(a) Cadence SLAs at class level?** **YES.** Start there. 84 classes is a configuration task; 443 instances is a data-entry nightmare. Inherit the SLA from the class.
*   **(b) Auto-map orphans by prefix?** **YES, with a "Shame Log".** Map them so they are monitored, but tag them as `legacy_orphan` in the report so Kevin knows to eventually move them into a proper class-instance relationship.
*   **(c) Daily scheduled check?** **NO.** Run it **twice**: once in the `build_publish.ps1` (to prevent shipping broken data) and once as a daily `cron` (to catch stale data that hasn't changed because no build occurred).
*   **(d) Thresholds?** **SKEPTICAL.** "10% short = Yellow" is too loose for "Perfect." **Recommendation:** Missing Season = RED; <2% variance = GREEN; any variance >2% = RED. In a static factual DB, "missing 5% of games" isn't a minor dip; it's a scrape failure.
