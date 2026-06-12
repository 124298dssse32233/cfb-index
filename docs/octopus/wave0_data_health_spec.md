# Wave 0 — Data Health Spine: Implementation Spec (v2, council-refined)

_v1 authored 2026-06-11; **v2 refined 2026-06-11** via Octopus council (gemini + codex + qwen) + Claude
repo-verification. Raw critiques: `docs/octopus/wave0_council_raw/{gemini,codex,qwen}.md`. Spec only — not
built. Parent: `site_quality_next_phases_plan_2026-06-11.md`. Locked: **internal-only** · **GitHub-issue alerts**._

## Goal
One authoritative "is my data filled, healthy, and processed when I want?" capability that **unifies**
existing signal, runs deterministically, alerts via GitHub issues, and auto-adapts to source add/remove.

## The core refinement (codex): stop conflating four questions
The v1 design treated `scrape_health` as the source inventory. It isn't. Four distinct questions need four
distinct answers:
1. **What should exist** (datasets × season × entity) — no primitive owns this today.
2. **What should run** (the *desired source-instance inventory*) — **missing primitive; build this first.**
3. **What actually ran** — `scrape_health` (an observation log; 443 instances, includes dead/historical).
4. **Whether the data is usable** — no integrity layer today.

`source_registry` (79 classes), `collection_ledger` (10 enrolled), and `scrape_health` (443 observed) each
answer *subsets*. Treating historical `scrape_health` rows as the active inventory produces **false alarms +
blind spots**. So the foundation is a **declarative desired inventory**; everything else reconciles against it.

## Verified repo facts (Claude-checked 2026-06-11 — corrects the repo-blind council SQL)
- **Real schema (council guessed several wrong):** `games` PK = **`game_id`** (not `id`); date col =
  **`start_time_utc`** (not `start_date`). `roster_entries` uses **`season_year`** (not `season`).
  `player_game_stats` FK = `game_id` + `player_id`; `players` PK = **`player_id`** (not `players.id`).
- **FK integrity currently clean:** `player_game_stats` orphan `game_id` = **0** → a good guard to lock in.
- **Severe silent gap found while verifying:** `roster_entries` coverage = **2020: 14 teams, 2021–2023:
  MISSING, 2024: 134, 2025: 146**. Worse than the games gap — rosters effectively exist only for 2024–2025.
- **Null-density signal:** `players.position` = **15.9% null** (9,754/61,381); `full_name`/`player_id`/
  `home_points` ~0%. Confirms gemini's "placeholder pandemic" check is worth running.
- **Schema-drift signature** via `PRAGMA table_info` → hash is trivial + catches the renamed/dropped-column
  bug class (which hid today's Savant `display_name` + `index_conferences` bugs).
- **Source model** (unchanged): 79 classes / 443 instances / 370 prefix-grouped orphans
  (`reddit_*`×159, `google_*`×140, `athletics_*`×21…); `collection_ledger` enrolls only 10.
- **Live failures to repair, not just monitor:** ~6 `athletics_*` erroring today; `gdelt_volume` failing;
  `podcast_asr` due-dates in **2027** (schedule anomaly). `audit-data-coverage` CLI exists (reuse).

## Architecture

### 1. Desired source-instance inventory (the new foundation — codex)
Checked-in, reviewed config (not derived from `scrape_health`). Per instance:
`source_class · instance_key · active · cadence_override? · expected_output_dataset · first_expected_date ·
retired_date`. Reconcile **expected LEFT JOIN collection_ledger LEFT JOIN latest scrape_health** → classify
every instance into one explicit state: *expected+healthy · expected-never-enrolled · expected-never-observed
· observed-not-expected · retired · disabled · overdue · failed · successful-but-stale-upstream*. The 370
orphans get **proposed** prefix mappings, but only **reviewed** mappings enter config; unmapped stay visible
as `unclassified` (never guessed into a parent). `scrape_health` stays an observation log.

### 2. Data contracts (declarative; the heart — all 3 + Claude)
Per **dataset** contract (checked-in Python/YAML; reuse `verify_data_floors.SPINE_FLOORS`):
`grain (e.g. one row per game_id,team_id) · key cols · required-non-null cols · parent refs · valid
season_range · entity universe · min rows per entity-season · allowed categoricals · invariants · freshness
semantics · zero-row policy`.
Per **source** = a **schedule contract** (renamed from "SLA" — codex): `timezone · interval/rule · allowed
start window · completion deadline · max upstream lag · grace · zero-rows-allowed-only-if no_change · max
scheduling horizon` (so a 2027 due-date flags as anomaly).

### 3. The checker `verify_data_health.py` (+ `manage.py data-health`) — an ORCHESTRATOR
Stdlib + raw sqlite3; **calls reusable checks** from `verify_data_floors.py`, `audit-data-coverage`,
`verify_build_manifest.py` (don't duplicate). Evaluates the **5 observability pillars** as cheap SQL, each
producing pass/fail assertions:
- **Completeness/Coverage** — required season×entity cells present (catches missing 2023, the roster gap).
- **Freshness/Schedule** — per the 4 timestamps `due_at / completed_at / data_through / processed_at`
  ("ran" ≠ "current"); overdue, erroring, or schedule-anomaly → flag.
- **Volume** — per-dataset, per-season floors + drop-vs-last-snapshot (NOT a global floor — a 2023 wipe
  hides behind a global count).
- **Schema/Validity** — `PRAGMA` signature vs checked-in hash; null-density in key cols; impossible values
  (negative attempts, future dates, season/date mismatch); allowed-categoricals.
- **Integrity/Uniqueness/Lineage** — duplicate-grain; orphan FKs (anti-join); cross-table reconciliation
  (team game totals vs games); provenance-validity (`source_id` references a *known* source, not just non-null).
Writes a snapshot (**run header + normalized result rows / versioned JSON**, not one wide row) + report JSON;
exit non-zero on red.

### 4. Pipeline-boundary identity check (codex — high value, this project's history)
The checker, the build, and the deployed snapshot must prove they used the **same DB**: compare DB
path/size/mtime/**schema-hash**/key row-counts (+ optional content fingerprint) between `data-health`,
`verify_build_manifest.py`, and the deploy. Directly defends the **box-DB vs cloud-artifact divergence**
class that has bitten this project (`player_id` space drift, stale artifact content).

### 5. Headline result: gates, not a blended score (codex corrects gemini)
A single averaged 0–100 score hides critical failures. Present **5 pillar pass-rates** + a hard overall
**gate state**:
- **RED** — any critical contract failure, missing mandatory dataset/season, overdue critical source,
  corrupt DB, or failed identity check.
- **YELLOW** — non-critical SLA misses, degrading provenance, unclassified sources, warning thresholds.
- **GREEN** — all required gates pass.
- **UNKNOWN** — a required assertion couldn't be evaluated. **UNKNOWN must never collapse into GREEN.**
Plus a one-glance header: active/never-seen/overdue/failing instance counts, last successful end-to-end
build, and the DB fingerprint of the last deploy. (A glanceable composite *score* may sit **beside** the gate
as secondary, never as the gate.)

### 6. Surface + alerting (gemini + codex + the internal-only decision)
Lead with **deterministic JSON + console** (`manage.py data-health`) and **GitHub issues** — for an
infra-beginner owner, a clear issue with the failing SQL beats a dashboard. Reuse the existing `--open-issue`
→ `gh issue create` helper; **one deduped issue per regression class** (not per instance — avoids 370 issues),
auto-close on green. **Dashboard is built LAST and optional** (internal, gitignored local path, never in
`output/site/`). **Drop `source_change_log` initially** — derive add/retire/first-seen by diffing the current
reconciled inventory vs the previous snapshot (add a durable event log only if proven necessary).

## Revised task sequence (codex-refined; checker before dashboard)
1. **W0.1** Define terminology + write dataset/schedule **contracts** (games, player_game_stats, roster_entries,
   provenance first). Seed from `SPINE_FLOORS`.
2. **W0.2** Build the **desired source-instance inventory**; reconcile 443 observations; classify 370 orphans
   (proposed→reviewed). *Do not auto-accept prefix maps.*
3. **W0.3** Repair the **known live failures** surfaced (athletics errors, gdelt, 2027 schedules, NULL-provenance writes) — so the first run isn't all-red noise.
4. **W0.4** ⭐ **Checker, no persistence/dashboard** — JSON + console; validate against a known-good copy AND a
   deliberately-damaged copy (must catch the injected gap). *First real value.*
5. **W0.5** Dataset integrity contracts wired (FK/null/dupe/distribution/schema).
6. **W0.6** Snapshots + trend comparison (+ inventory-diff for source changes).
7. **W0.7** Pre- **and** post-build verification + the **DB identity check**; wire into `build_publish.ps1`.
8. **W0.8** GitHub-issue alerting — enabled only **after several shadow runs** establish baselines (anti-noise).
9. **W0.9** (optional) Internal dashboard, last.
Checker is **non-Critical during calibration**; once trusted, **critical spine failures BLOCK publish**
(else "red" means knowingly shipping bad data — contradicts the goal).

## Resolved open questions (council consensus + verification)
- **(a) Cadence granularity** — class-level **defaults** with **instance overrides supported in the model from
  day one** (so no migration when one podcast/subreddit needs a different schedule). Compute freshness from
  `scrape_health` + contract, NOT from mass-seeding 433 ledger rows.
- **(b) The 370 orphans** — auto-**propose** prefix maps; require **reviewed** checked-in config; unmapped =
  `unclassified` and visible (never silently re-parented).
- **(c) Check frequency** — **not** daily-only. Run at pipeline start, **pre-build, post-build**, AND once
  daily independently (a single daily run can't tell scheduler-failure from collector-failure).
- **(d) Thresholds** — reject the universal 10%. **Per-dataset severity, season-aware:** missing required
  season = RED; any missing game in a *completed* historical season = RED; spine volume deviation strict
  (~2%); conversation volume looser; **current in-progress season has separate expectations**; unknown
  denominator = UNKNOWN (never green).

## Biggest risks (codex)
1. A polished monitor over an **undefined source universe** → *systematic* false confidence. (Mitigated by
   W0.2-first + the inventory being the source of truth.)
2. **Alert noise** → shadow-run baselines before enabling issues (W0.8 after W0.4–0.7).
3. **False confidence from wrong expectations** → meta-check: every spine table must have a contract;
   every active instance must map to the inventory; else flagged, not silently passed.

## Still-open for Kevin
- **Zero-row tables** (`plays`/`drives`): classify as *required-red*, *deferred-with-target-date*, or
  *out-of-scope*? (They must not sit ambiguously green.)
- **Publish-blocking**: once calibrated, should a RED spine check **hard-block** the nightly deploy (safest)
  or only warn? (Recommend hard-block on the critical spine subset.)
- **Roster gap** (2021–2023 missing): backfill as part of Wave A, or accept rosters as 2024+ only?

---

## Appendix — Live-code verification (round 3, 2026-06-11): from design to build-ready
_Every check below was run read-only against the production `cfb_rankings.db`. Real numbers; corrects the
council's repo-blind guesses; sets concrete contracts + reuse points._

### Reuse map (build by composing, not rebuilding)
- **Completeness pillar ≈ 80% already built.** `cfb_rankings/audit.py::write_data_coverage_audit` +
  `_season_coverage_rows(db)` already compute a **13-dataset × season matrix from 2014→latest** (Games,
  Postseason, Team Seasons, Rosters, Player Season Stats, Player Usage, Player Value, Player Game Stats,
  Honors, Heisman Votes, Official Rankings, Transfers, Recruiting) **with a gaps section + sidecar.** The
  checker should call `_season_coverage_rows()` and add density + thresholds + gating on top. → **Expected
  season range is 2014+** (so our 2020–2025-with-holes data has a *large* known gap surface already computed).
- **Volume/provenance:** import `verify_data_floors.SPINE_FLOORS` (dict at line 50) + its ratchet.
- **Schema/manifest/identity:** `verify_build_manifest.py`. **Alerts:** the working `--open-issue` →
  `gh issue create` in `verify_module_coverage.py`.

### Inventory reconciliation — prototyped, works, and prefix-ambiguity is real
- 443 instances; **latest-run status: ok=304, error=80, empty=56, skipped=3 → 136 (31%) UNHEALTHY now**,
  invisible today. `athletics_*`=19/21 error; `reddit_*`=65/159 unhealthy; `substack_*`=5/9; `campus_*`=12/15.
- **Auto-prefix-mapping is unsafe for multi-class prefixes** (confirms codex): `reddit`→4 classes,
  `substack`→10, `beat`→13, `youtube`→3, `board`→3. Only single-class prefixes auto-map cleanly:
  `athletics_*`→`athletics_template`, `campus_*`→`campus_template`, `locked_*`→`locked_on_template`,
  `google_*`→`google_trends_dma`. ⇒ ship single-class auto-maps; **reviewed config** for reddit/substack/
  beat/youtube/board; everything else `unclassified` + visible.

### Spine integrity — currently SPOTLESS (lock this baseline; guards catch regressions)
Verified 0 for ALL of: games dup `game_id`; `player_game_stats` dup PK + dup grain
(game_id,team_id,player_id,category,stat_type); orphan `player_id`/`team_id` in player_game_stats & rosters;
games orphan `home_team_id`; games future `start_time_utc`; games season/start-year mismatch. ⇒ the FK / grain
/ temporal-validity assertions establish a clean green baseline and only fire on *future* corruption.

### Completeness reality — DENSITY matters, not just presence (concrete)
games per season (`distinct home_team_id` / total / completed):
`2020: 137/563`, `2021: 429/2408`, **`2022: 671/1563` (≈2.3 home-games/team — HALF-EMPTY despite all teams
present)**, **`2023: MISSING`**, `2024: 680/3747`, `2025: 675/3830`. A presence check passes 2022; a
**games-per-team density** check (contract: ≥ ~5.5 home-games/team for a completed FBS season) catches it.
- `power_ratings_weekly` / `resume_ratings_weekly` seasons = `2020,2021,2024,2025` → **missing 2022 + 2023**.
- `roster_entries` = `2020:14 teams, 2021/2022/2023 MISSING, 2024:134, 2025:146`.
- `players.position` = **15.9% null** (9,754/61,381) → null-density contract, yellow.

### Concrete contract seeds (real columns — use these verbatim)
```
games:        grain=game_id (unique ✓) · parents=home_team_id,away_team_id→teams · date=start_time_utc
              · season_range=2014.. · density: home_games_per_team ≥ 5.5 for completed seasons
player_game_stats: grain=player_game_stat_id (unique ✓) · key(game_id,team_id,player_id,category,stat_type)
              · parents game_id→games, player_id→players, team_id→teams · numeric col=stat_value_num
roster_entries: grain=roster_entry_id · season_year · parents player_id,team_id · required(position ≤? null%)
entity_universe: current FBS = teams WHERE level_code='FBS' AND is_active=1   (NOT raw level_code → 198 rows
              includes historical schools; real current FBS ≈ 134)
```

### Freshness — cadence must be DECLARED, not inferred (prototyped)
Inferring cadence from successful-run history is **insufficient**: only **43/337 instances (13%) have ≥3 ok
runs** to infer from (the other 294 barely ran — themselves a signal of never-established sources). ⇒ the
schedule contract uses **declared** per-class cadence defaults (the "cadence Kevin sets"); history-inference
is a **config-assist** ("this class historically ran ~every 7d") + a sanity check ("declared weekly but ran
daily"), never the source of truth. The prototype already catches the obvious case
(`reddit_backfill_fsu_city`: 175 days since last ok vs a ~7-day historical cadence). Instances with <3 ok
runs are reported as `never-established`, not silently "fresh".

### Net effect on the plan
Completeness reuses an existing audit; integrity is a clean-baseline lock; the genuinely-new build is the
**desired inventory + reconciliation**, **schedule contracts + 4-timestamp freshness**, **gates**, the
**DB-identity check**, and **alerting** — materially smaller than v1 implied. The first checker run will
immediately surface: 136 unhealthy source instances, the 2022 half-season + 2023 hole, ratings 2022–2023,
the roster 2021–2023 gap, and `players.position` nulls.

---

## Appendix B — CFB historical reality: per-year expectation *regimes* (round 4)
_Verified read-only against the DB and cross-checked against real CFB history. THIS is what stops the health
system from crying wolf on legitimately-weird seasons while still catching real gaps. Completeness/density
contracts MUST be per-season with a regime tag — never a single uniform rule._

### The data source for per-year truth
- **Entity universe + conference = `team_seasons`** (2,703 rows: `team_id, season_year, level_code,
  conference_id` per year) — NOT `teams.current_conference_id` (static; ignores realignment) and NOT the
  current FBS set (ignores FCS→FBS moves). **Caveat:** `team_seasons` FBS counts look inflated post-2020
  (2020=127 ✓ real, but 2021=152/2022=161/2024=175/2025=167 vs real ≈130–136) → `team_seasons` membership is
  itself a contract to validate, not blindly trusted.
- Normal-season reference: **12 regular-season games/team** (13 with a conference-championship; +1 Hawaii
  rule). FBS ≈ 130 (2020) → ~136 (2025), **growing** via realignment + FCS→FBS transitions. CFP = **4-team
  (≤2023) → 12-team (2024+)**.

### Per-season regimes (verified medians; the contract keys off these)
| Season | Regime | Verified shape | Contract expectation |
|---|---|---|---|
| **2020** | **COVID — reduced** | 127 FBS, **median 9 g/team (range 3–12)**, 78 teams at 8–11 | Expect reduced+variable; **exempt from the ≥12 density rule**; floor ~ median≥7, no team>13. Flagging 2020 "incomplete" = FALSE ALARM. |
| 2021 | normal | 152 listed, median **12**, 133 at 12+ | Full-season density (≥~11 median); investigate the inflated membership count |
| **2022** | **DATA GAP** | 161 listed, **median 5, MAX 6 g/team** | Normal year → expect ≥12; **max 6 = ~half the season missing → RED/backfill** (not an anomaly) |
| **2023** | **BLACK HOLE** | **0 rows in games, player_game_stats, roster_entries, team_seasons, ratings** | Entire normal season missing → **RED, top backfill priority** |
| 2024 | normal (12-CFP) | 175 listed, median **12**, 133 at 12+ | Full-season density; investigate inflated count |
| 2025 | normal/current | 167 listed, median **12** (max 16 = deep CFP) | Current-season rules: in-progress weeks exempt; postseason expected Dec–Jan |

### Other CFB-specific gaps found
- **Historical postseason is largely missing:** `postseason_games` table doesn't exist; `games.season_type
  ='postseason'` rows exist **only for 2025**. Bowls + the 4-team CFP (2020–2023) and 2024's 12-team bracket
  aren't represented → a real coverage gap. Postseason expectation is **per-year by CFP format**.
- **Pre-2020 absent:** the audit's expected range is **2014+**; the DB starts at 2020 → 2014–2019 entirely
  missing (decide: in-scope historical depth, or accept 2020+ as the floor).

### Design consequence (folded into the contracts)
Each spine dataset's completeness contract carries a **per-season row** with: `regime ∈ {pre-data, covid,
normal, in-progress, known-missing}`, expected entity count (from `team_seasons`, validated), expected
density band (games/team), and postseason format. The gate logic:
- `covid` season below *normal* density → **GREEN** (expected). Below *covid* floor → yellow.
- `normal` historical season below density → **RED** (2022, 2023).
- `in-progress` current season → judged only on weeks that should exist to date.
- `pre-data`/`known-missing` → explicit state, never silently green, never false-red.
This is the difference between a monitor that's trusted and one that's muted after week one.

### Round 5 — domain dimensions verified (realignment, membership, rankings, stats, postseason)
**Realignment + level history is ACCURATE** (spot-checked vs known truth): the 2024 Pac-12 collapse
(USC/UCLA/Oregon/Washington→Big Ten; Colorado/Utah→Big 12; Cal/Stanford/SMU→ACC; Oregon State stays
"Pac-2"), Texas/Oklahoma→SEC, BYU Independent→Big 12, and FCS→FBS moves with correct years (James Madison
2022, Kennesaw State 2024, Jacksonville State/Sam Houston) — all correct in `team_seasons`. Transitions are
bracketed correctly even across the 2023 hole (2022 before / 2024 after).

**The precise entity-universe definition (use this in contracts):** FBS = a `team_seasons` row whose
`conference_id` resolves to one of the 11 real FBS conferences (SEC, Big Ten, Big 12, ACC, American, Mountain
West, Sun Belt, C-USA, MAC, Pac-12, FBS Independents). This yields the **exactly-correct** per-year counts —
**2020=127 · 2021=130 · 2022=131 · 2024=134 · 2025=136** — whereas raw `level_code='FBS'` over-counts (175 in
2024) because **41 teams are parked in a generic "FBS" conference bucket** (non-FBS opponents / unresolved →
a level-hygiene backlog item, NOT used for the universe).

**Verified per dimension:**
- `official_rankings`: 2020 (15 wk/850), 2021 (15 wk/900), 2024 (16 wk/951), 2025 (16 wk/950); **2022 + 2023
  MISSING**. Contract: AP/Coaches/CFP per week, season-aware (CFP poll only from week ~10).
- `player_game_stats` categories: all 9 present every season (defensive/receiving/rushing/passing/punting/
  kicking/kickReturns/puntReturns/fumbles); **2022 volume ≈ half** (tracks the games gap), others full.
- Postseason (`games.season_type='postseason'`): **only 2025** (86 rows; verify against bowls+12-team CFP).
  2020–2024 bowls/CFP absent → per-year postseason contract by CFP format (4-team ≤2023 / 12-team 2024+).

**Bottom line:** the data is domain-*correct* where present (realignment, membership, stat categories,
rankings structure all verified accurate); the work is closing structural gaps (2022 partial, 2023 black
hole, historical postseason, pre-2020) — and the health contracts must encode the per-year regimes above so
those gaps flag RED while real anomalies (2020 COVID) stay GREEN.

### Round 6 — secondary dimensions: gap patterns DIFFER BY DOMAIN (so contracts are per-dataset-per-year)
The single most important finding: **there is no one "missing 2023" rule.** Each data domain has its own
expected-season set. A naive global expectation would be wrong for half the tables.

| Dataset | Years present | Expected (per CLAUDE.md / reality) | Gap |
|---|---|---|---|
| **Game spine** (games/pgs/rosters/ratings/rankings/team_seasons) | 2020,2021,2022*,2024,2025 | 2020–2025 | **2023 missing**, 2022 partial |
| recruiting_entries (team class) | 2020,2023,2024,2025 | 2018–2025 | **2021,2022 missing** + pre-2020 |
| returning_production | 2020,2023,2024,2025 | 2018–2025 | **2021,2022 missing** |
| team_talent_snapshots | 2020,2023,2024,2025 | 2018–2025 | **2021,2022 missing** |
| player_recruiting_profiles | 2020–2026 ✓ | 2018–2025 | pre-2020 only |
| transfer_entries | 2023–2026 | portal era ~2021+ | **pre-2023 missing** |
| player_nfl_draft | **2024,2025,2026 only** | CLAUDE.md says 2018–2025 (STALE) | **2018–2023 missing** |
| player_honors | 2024,2025 only | multi-year | **pre-2024 missing** |
| heisman_rankings_weekly | **2020,2024 only** | per-season | **2021,2022,2023,2025 missing** (feeds `/film-room/`) |

**Empty / near-empty derived tables (classify each: required-red / deferred / out-of-scope):**
`coaching_changes`=0, `portal_moves`=0, `player_draft_projection`=0, `heisman_market_odds_weekly`=0,
`heisman_vote_results`=2 (should be ~10 finalists/yr). **Coaching:** `team_seasons.head_coach` is **75.7%
NULL** (and `coaching_changes` is empty) → coaching history is effectively absent and must be marked as such,
not silently passed.

**Doc-vs-reality drift the health system would catch:** CLAUDE.md claims "NFL Draft 2018–2025" but the DB has
only 2024–2026 — exactly the stale-doc/real-data divergence the spine should surface (and a reminder to fix
CLAUDE.md).

**Contract design consequence:** every dataset declares its OWN `expected_seasons` set + regime per season;
the gate diffs actual vs that dataset's expectation. Wave A backfill priority, re-ranked by this round:
**(1) 2023 game spine** (black hole, feeds everything) → **(2) 2021–2022 offseason** (recruiting/talent/
returning) → **(3) historical NFL draft + honors + heisman** (feed player pages + film-room) →
**(4) historical postseason** → **(5) pre-2020 depth** (optional).

### Round 7 — data soundness / integrity edges (validity pillar)
- **Heisman semantics + freshness:** `heisman_rankings_weekly` is a **single snapshot** (week=1 only — the
  name lies), present **only 2020 + 2024**, with a 9× methodology drift (2020 ranks a 1,778-player shortlist;
  2024 ranks ~all 16,218 players), and **2025 (current) missing** — so `/film-room/`'s Heisman read is stale.
  Contract: flag name-vs-shape mismatch + missing current season + the 9× volume drift.
- **Player-identity duplication (quantified for WP-1.6):** 61,381 players, **4,850 duplicate full-names**
  (Isaiah Johnson ×19, Jayden Williams ×17). A mix of real same-names + re-ingestion drift. Integrity check:
  duplicate-name density trend + (durable fix) identity via `player_source_ids` (75,588 rows) rather than
  name. Reuse `audit-player-duplicates`.
- **Score validity:** 0 negative, 0 >100 (clean) — but **21 games marked completed yet 0–0** (regulation
  ties are impossible post-1996 OT → almost certainly cancelled/forfeited games mislabeled `completed`).
  Contract: `completed_and_scoreless` count = warning; investigate/relabel.

## Verification status (rounds 3–7 complete)
The data layer is now comprehensively verified against live code AND real CFB history. **What exists is
domain-accurate** (realignment, level moves, per-year FBS membership, stat categories, scores — all checked
sound); **integrity is clean** (0 dup-grain / orphan-FK / impossible-value on the spine). The work is
**closing structural gaps** (2023 black hole, 2022 partial, 2021–2022 offseason, recent-only draft/honors/
heisman, historical postseason, pre-2020) and **per-dataset-per-year contracts** so each is judged by its
own real expectation. The spec is build-ready; remaining input needed is the handful of "still-open"
classification calls below + whether to start the build or the Wave A backfills this verification prioritized.
