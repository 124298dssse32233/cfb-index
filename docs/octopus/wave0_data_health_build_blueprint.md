# Wave 0 — Data Health Spine: Build Blueprint (concrete how-to)

_Authored 2026-06-11. The executable companion to `wave0_data_health_spec.md` (design + 7 rounds of live
verification). Every example uses VERIFIED real column names / contracts. Stdlib + raw sqlite3 only; reuse
existing primitives. Internal-only surface; GitHub-issue alerts._

## Module layout (`src/cfb_rankings/data_health/`)
```
data_health/
  __init__.py
  contracts.py     # declarative dataset + schedule contracts (the spec; checked-in, reviewable)
  inventory.py     # desired source-instance inventory + reconciliation (class→instance→state)
  calendar.py      # CFB per-year regimes + real-FBS-conference universe (verified facts)
  checks.py        # the cheap-SQL assertion catalog, grouped by pillar
  gate.py          # pillar results → RED/YELLOW/GREEN/UNKNOWN gate logic
  report.py        # snapshot persistence + JSON/console rendering
  identity.py      # pipeline-boundary DB fingerprint (path/size/mtime/schema-hash/rowcounts)
scripts/verify_data_health.py   # thin orchestrator → manage.py data-health (calls the above)
migrations/2026XXXX_data_health.sql  # data_health_snapshot, data_health_result
```
The orchestrator IMPORTS, never duplicates: `verify_data_floors.SPINE_FLOORS`,
`cfb_rankings.audit._season_coverage_rows`, `verify_build_manifest`, and the `--open-issue` helper.

## 1. `calendar.py` — verified CFB ground truth (hard-coded, it's history)
```python
FBS_CONFERENCES = frozenset({  # the 11 real FBS conferences — defines the entity universe
  "SEC","Big Ten","Big 12","ACC","American","Mountain West","Sun Belt",
  "Conference USA","Mid-American","Pac-12","FBS Independents"})

# verified exact per-year FBS counts (real-FBS-conference members from team_seasons)
EXPECTED_FBS = {2020:127, 2021:130, 2022:131, 2023:133, 2024:134, 2025:136}  # 2023 = real, currently missing

# per-(dataset, season) regime. Game-spine example; offseason datasets have the INVERSE 2021-2022 holes.
REGIME = {  # 'normal'|'covid'|'in_progress'|'known_missing'|'pre_data'
  ("game_spine", 2020):"covid", ("game_spine",2021):"normal", ("game_spine",2022):"normal",
  ("game_spine",2023):"known_missing", ("game_spine",2024):"normal", ("game_spine",2025):"in_progress"}

CFP_FORMAT = {**{y:"4team" for y in range(2014,2024)}, **{y:"12team" for y in range(2024,2027)}}
NORMAL_GAMES_PER_TEAM = 12   # +1 conf championship; Hawaii rule +1
COVID_GAMES_PER_TEAM_FLOOR = 6   # 2020 verified median 9 (range 3-12) → floor 6, never expect 12
```
`fbs_team_ids(db, season)` → `team_seasons` rows where `conference_id` resolves into `FBS_CONFERENCES`
(NOT `level_code='FBS'`, which over-counts via the generic "FBS" bucket — verified 134 vs 175 in 2024).

## 2. `contracts.py` — declarative, one per dataset
```python
@dataclass(frozen=True)
class DatasetContract:
    name: str; table: str; grain: tuple[str,...]           # unique key
    required_non_null: tuple[str,...]
    parents: tuple[tuple[str,str,str],...]                  # (fk_col, parent_table, parent_col)
    expected_seasons: frozenset[int]                        # THIS dataset's own season set
    season_phase: str                                       # which REGIME family
    density: dict | None = None                             # e.g. {"per":"home_team_id","min":5.5}
    allowed_values: dict | None = None
    zero_row_policy: str = "required"                       # required|deferred|out_of_scope

GAMES = DatasetContract(
    name="games", table="games", grain=("game_id",),
    required_non_null=("game_id","season_year","home_team_id","away_team_id"),
    parents=(("home_team_id","teams","team_id"),("away_team_id","teams","team_id")),
    expected_seasons=frozenset(range(2020,2026)),  # 2014+ is the stretch goal
    season_phase="game_spine",
    density={"per":"home_team_id","min_normal":5.5,"min_covid":3.0})
# plates for player_game_stats, roster_entries, ratings, recruiting_*, transfers, draft, honors, heisman …
```
A **schedule contract** per source class (`inventory.py`): `cadence ∈ {daily,weekly,monthly,seasonal,manual}`,
`grace_hours`, `max_horizon_days` (so a 2027 due-date flags), `zero_rows_ok_if="no_change"`.

## 3. `checks.py` — the cheap-SQL assertion catalog (verified queries)
Each returns `CheckResult(id, pillar, status: pass|fail|unknown, severity, detail, evidence_sql)`.
```
COMPLETENESS  reuse audit._season_coverage_rows; per (dataset,season) actual vs expected_seasons + regime.
              DENSITY (verified essential): games home-per-team ≥ contract.min  ← catches 2022 (max 6).
VOLUME        per-season floor + drop-vs-last-snapshot (NOT global — a 2023 wipe hides behind a global count).
SCHEMA        PRAGMA table_info(tbl) hash vs checked-in signature (catches the Savant display_name class).
VALIDITY      null-density in required cols (players.position 15.9% baseline); impossible values
              (home_points<0/>100=0 ✓; completed_and_scoreless=21 ⚠); future start_time_utc=0 ✓.
INTEGRITY     dup-grain (=0 ✓); orphan FK anti-joins (=0 ✓); cross-table reconciliation.
UNIQUENESS    duplicate full_name density (4,850 baseline — trend, not absolute); prefer player_source_ids.
FRESHNESS     per active instance: last ok run + schedule contract → overdue/error/anomaly/never_established.
PROVENANCE    canonical% + 7/30-day trend; source_id must resolve to a known source (not just non-null).
LINEAGE/ID    DB fingerprint match (identity.py) across check↔build↔deploy.
```
Verified-clean baselines to LOCK (so future regressions fire): all FK/grain/temporal checks = 0.

## 4. `gate.py` — pillar results → one state (codex model)
```
RED   if any: critical contract fail · missing required season for a 'normal' dataset ·
              overdue CRITICAL source · DB-identity mismatch · schema-hash drift on a spine table
YELLOW if any: non-critical SLA miss · provenance dropping · unclassified instances · warn-threshold
GREEN  if all required gates pass (a 'covid'/'in_progress'/'known_missing' season at its OWN expectation = GREEN)
UNKNOWN if a required assertion could not evaluate  →  NEVER collapses to GREEN
```
Headline = the gate + the 5 pillar pass-rates + counts (active/never-seen/overdue/failing/unclassified) +
last good build + deploy DB fingerprint. (Optional 0-100 score sits BESIDE the gate, never as it.)

## 5. Snapshot schema (`migrations`)
```sql
CREATE TABLE data_health_snapshot (snapshot_id INTEGER PRIMARY KEY, run_utc TEXT, overall TEXT,
  db_fingerprint TEXT, pillar_passrates_json TEXT, summary_json TEXT);
CREATE TABLE data_health_result (snapshot_id INT, check_id TEXT, pillar TEXT, dataset TEXT, season INT,
  status TEXT, severity TEXT, detail TEXT);   -- normalized rows, not one wide blob (codex)
```
Source add/retire is DERIVED by diffing the current reconciled inventory vs the previous snapshot — no
separate mutable `source_change_log` initially.

## 6. CLI + wiring
`manage.py data-health [--json] [--strict] [--open-issue] [--shadow] [--season N]`. Exit non-zero on RED
(unless `--shadow`). Wire into `build_publish.ps1` at **pipeline start, pre-build, post-build** (+ the
DB-identity check) and a **daily** standalone run — non-Critical during calibration; once trusted, a RED
spine subset BLOCKS publish. Alerts (`--open-issue`) enabled only AFTER several shadow runs baseline.

## 7. Reconciliation algorithm (`inventory.py`)
```
expected = checked-in desired inventory (per instance: class, key, active, expected_dataset, first/retired)
single-class prefixes auto-map (athletics_*→athletics_template, campus_*, locked_*, google_*); multi-class
  prefixes (reddit×4, substack×10, beat×13, youtube×3, board×3) require REVIEWED config; rest = 'unclassified'.
state = expected ⟕ collection_ledger ⟕ latest(scrape_health) → {healthy, never_enrolled, never_observed,
  observed_not_expected, retired, disabled, overdue, failed, stale_upstream}
```
First run MUST reproduce the verified live picture: **136/443 unhealthy** (80 error, 56 empty),
athletics 19/21 error.

## 8. Test plan (W0.4 acceptance)
Run against (a) the live DB — must reproduce every verified finding (2023 hole, 2022 half-season, 136
unhealthy sources, players.position 15.9% null, 21 scoreless-completed); (b) a **deliberately-damaged copy**
(drop a season, null a key column, rename a column, insert a dup) — every injected fault must turn RED/UNKNOWN.
A check that can't catch its own injected fault doesn't ship.

## Build order (maps to spec tasks W0.1–0.9)
calendar+contracts → inventory/reconciliation → migrations → **checks+gate (first value, console/JSON)** →
snapshots → identity + pre/post-build wiring → shadow runs → issue alerts → (optional) dashboard.
