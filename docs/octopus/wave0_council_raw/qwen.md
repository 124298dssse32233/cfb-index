## Answers to the 7 Questions in "What We Want from You"

---

### **1. Failure Modes the Design Won't Catch**  
The proposed design relies on **presence checks** (season×team coverage, row floors) and **cadence SLAs**, but it will miss:  
- **Semantic drift**: Data may exist but be **invalid** (e.g., `games` table has 2023 rows but with incorrect team IDs or invalid game outcomes).  
- **Schema drift**: Columns like `team_id` or `season` may be present but **not typed correctly** (e.g., `season` as strings instead of integers).  
- **Overlapping data**: Redundant entries in `plays`/`drives` (e.g., duplicate play IDs) could go undetected.  
- **False positives in "healthy" sources**: A source may have `status='success'` but **insufficient rows** (e.g., `reddit_city` fails to crawl a critical article).  
- **No tracking of "orphaned" instances**: The 370 unregistered `scrape_health` instances (e.g., `board_*`, `campus_*`) are not in `collection_ledger`, so their cadence is **unenforced**.  

**Recommendation**: Add **schema validation** via `audit_data_coverage.py` (already exists) and **duplicate detection** via `SELECT COUNT(*) FROM plays WHERE play_id IN (SELECT play_id FROM plays GROUP BY play_id HAVING COUNT(*) > 1)`.

---

### **2. Completeness Done Right**  
Beyond season×team coverage, the following checks are critical:  
- **Referential integrity**: Ensure foreign keys (e.g., `player_id` in `player_game_stats` references `players.id`) exist and are not NULL.  
- **Schema consistency**: Use `pragma table_info` to check column types and ensure they match `source_registry` metadata.  
- **Nulls in key columns**: Query `SELECT * FROM games WHERE season IS NULL OR team_id IS NULL`.  
- **Distribution drift**: For `player_game_stats`, check if `avg(points)` for a team drops by >50% compared to prior seasons.  

**Cheap Implementation**:  
- Use existing `verify_data_floors.py` to validate row counts.  
- Add a `--schema-check` flag to `audit-data-coverage` to enforce schema.  

---

### **3. Cadence/SLA Model**  
The current **class-level SLA** model is flawed:  
- **433 unregistered instances** (e.g., `athletics_*`) are not in `collection_ledger`, so their cadence is **unenforced**.  
- **"Process when I want"** requires **manual overrides** (e.g., `source_id=gdelt_volume` should be manually paused if it’s failing).  

**Recommendation**:  
- **Migrate all 430+ unregistered instances** into `source_registry` and `collection_ledger` ASAP.  
- Use `--cadence=manual` in `spec.py` to allow Kevin to define **exact run times** (e.g., `scrape_health` for `gdelt_volume` must run on Mondays only).  
- **Per-instance SLAs** (not class-level) would be ideal but are not feasible without rewriting `collection_ledger`.

---

### **4. Make "Perfect" Measurable**  
**Headline metrics** for Kevin:  
1. **SLA Compliance Rate** = (Number of sources meeting cadence SLAs) / (Total active sources)  
2. **Completeness Score** = (Expected rows – missing rows) / Expected rows  
3. **Volume Floor Adherence** = (Current row count – floor) / Floor  
4. **Provenance Coverage** = (Sources with verified `source_id`) / (Total sources)  

**Example Calculation**:  
```sql
-- SLA Compliance Rate
SELECT 
  (COUNT(CASE WHEN last_ok_at > (now - cadence_seconds) THEN 1 ELSE NULL END) / COUNT(*)) * 100 AS compliance_rate 
FROM collection_ledger;
```

---

### **5. Simpler Alternative?**  
Adopt **data observability 5 pillars** (completeness, freshness, validity, consistency, uniqueness) **without new cost**:  
- **Freshness**: Use `collection_ledger` + `scrape_health` (already exists).  
- **Validity**: Use `verify_data_floors.py` for row counts and `verify_build_manifest.py` for schema.  
- **Uniqueness**: Use `SELECT COUNT(*) FROM plays GROUP BY play_id HAVING COUNT(*) > 1` (as above).  

**Avoid**: Great Expectations (requires new dependencies). Use **existing CLI tools** like `audit-data-coverage`.

---

### **6. Sequencing/Risk**  
**Sequencing**: Prioritize **W0.1 source reconciliation** (map 370 orphans + update `source_registry`) **before** W0.3 migrations. Otherwise, the ledger will remain incomplete.  

**Biggest Risk**:  
- **Orphaned sources** (370 instances) not mapped into `collection_ledger` will **bypass cadence enforcement**.  
- **SLA misalignment**: Class-level cadences (e.g., `reddit_*` daily) may not match Kevin’s **intent** (e.g., only run `reddit_newswire` on Mondays).  

---

### **7. Open Questions**  
**(a)** **Cadence SLAs at class level only first**  
- **Recommendation**: Start with **class-level SLAs** (e.g., `reddit_*` daily) but **design for instance-level granularity** in W0.2. Use `--cadence=manual` in `spec.py` for sources like `gdelt_volume`.  

**(b)** **Auto-map 370 orphans by prefix now, fold into registry later**  
- **Recommendation**: Map `board_*` → `board_news`, `campus_*` → `campus_calendar`, etc., into `source_registry` **today**. Fold into `collection_ledger` during W0.3.  

**(c)** **Daily scheduled check**  
- **Recommendation**: Keep daily checks **but allow manual runs** via `manage.py data-health --force`.  

**(d)** **Thresholds: missing season=red, ≥10% short=yellow, within 10%=green**  
- **Recommendation**:  
  - **Red**: Missing **any season** (e.g., `games` missing 2023).  
  - **Yellow**: ≥10% missing in 2021–2025 (e.g., `player_game_stats` missing 10% of 2022 data).  
  - **Green**: 100% of 2021–2025 data present, with no unregistered sources.  

--- 

This addresses all 7 questions with repo-specific, actionable refinements.
