# Signature Story — Data Inventory (Feasibility Probe)

**Date:** 2026-04-22
**Task:** A.0 in the Player Page Data kickoff.
**DB probed:** `cfb_rankings.db` (SQLite, 80 tables).
**Purpose:** confirm which metrics named in the kickoff exist at player-season granularity, identify gaps, and define the achievable metric pool for TASK A.1's seed file.

---

## 1. Bottom line

**The kickoff's example metric set (EPA/dropback under pressure, CPOE, pressure-to-sack, third-down EPA, red-zone TD%) is NOT achievable with the current database.** None of these require PBP-level data that exists in CFBD's upstream but has never been ingested here — there are zero `pbp_*` / `play_by_play_*` / `situational_*` / `split_*` tables.

**What we DO have is enough to build a defensible Signature Story v1** centered on CFBD weighted-EPA (WEPA) plus traditional counting/rate stats plus usage splits. The story will read "best QB in the ACC by WEPA per dropback, minimum 250 attempts" — not "best QB under pressure." That's honest and shippable.

Recommendation: scope A.1's QB candidate pool to the 10–12 metrics enumerated in §4, stub RB/WR with 2–3 each against available stats, and open a follow-up ticket for "PBP ingestion → situational Signature Story v2."

---

## 2. Candidate tables (what was probed)

| Table | Rows (total) | Player-scoped? | What's in it |
|---|---|---|---|
| `players` | 46,668 | ✓ | id, name, position — identity only, no stats |
| `player_season_stats` | 165,999 | ✓ | traditional counting/rate stats via CFBD, EAV shape (`category` + `stat_type` + `stat_value_num`) |
| `player_game_stats` | 59,871 | ✓ | same shape, per-game |
| `player_usage_season` | 2,672 | ✓ | snap share splits — overall / pass / rush / 1st / 2nd / 3rd down / standard / passing downs |
| `player_value_metrics` | 683 | ✓ | **WEPA passing (191 QBs) + WEPA rushing (492 RBs)**, season-level, with `plays` denominator |
| `player_honors` | 57 | ✓ | Heisman winner flag, AA selections — used by Accolade Lens, not Signature Story |
| `player_recruiting_profiles` | — | ✓ | stars, composite — context, not production |
| `team_game_advanced_stats` | 18,442 | ✗ (team-scoped) | offense/defense PPA, success rate, explosiveness, havoc — can be joined as context |

No PBP, no CPOE, no pressure, no red-zone, no third-down-EPA, no aDOT, no play-action-split tables exist.

---

## 3. Metric-by-metric feasibility (kickoff's named examples)

| Kickoff metric | Table / query | Status |
|---|---|---|
| `epa_per_dropback_under_pressure` | (would need pbp_data + pressure flags) | **MISSING — cannot compute** |
| `cpoe` (completion % over expected) | (would need pbp_data with air-yards and expected-completion model) | **MISSING** |
| `pressure_to_sack_rate` | (would need pbp_data with pressure flags) | **MISSING** (team-level `havoc_off` in `team_game_advanced_stats` is the closest proxy, but it's team-scoped) |
| `third_down_epa` | (would need pbp_data filtered to 3rd down) | **MISSING**. Proxy available: `player_usage_season.usage_third_down` is 3rd-down **snap share** only — usage, not EPA. |
| `red_zone_td_rate` | (would need pbp_data with yardline_100 < 20) | **MISSING** |

---

## 4. Achievable QB metric pool (v1 seed file foundation)

These 10 metrics are queryable today for any 2024/2025 QB and can be ranked cohort-relative.

### WEPA-derived (CFBD aggregate weighted-EPA, season-level)
1. `wepa_passing_total` — `player_value_metrics.metric_value` where `metric_name='wepa_passing'`. Row count: 191 QBs in 2025.
2. `wepa_passing_per_dropback` — `metric_value / plays`. Same table. Denominator (`plays`) is dropback count per CFBD's definition.
3. `wepa_rushing_total` — QBs with rushing WEPA entries (scrambles + designed runs).
4. `wepa_combined_per_play` — `(passing_wepa * passing_plays + rushing_wepa * rushing_plays) / (passing_plays + rushing_plays)`.

### QBR (ESPN, per-game in player_game_stats, category=`passing`, stat_type=`QBR`)
5. `qbr_season_avg` — mean QBR across regular-season games. 311 game-rows in 2025 → ~50+ QBs with multi-game QBR coverage. **Caveat:** not every QB start has a QBR row; coverage is P4-leaning.

### Traditional rate stats (from player_season_stats, category=`passing`)
6. `ypa` — YDS / ATT, filter min-volume.
7. `td_int_ratio` — TD / max(INT, 1).
8. `completion_pct` — PCT (already a rate).
9. `passing_yards_total` — YDS (counting stat, used only as "volume leader" narrative).

### Usage (from player_usage_season)
10. `third_down_usage_share` — `usage_third_down`. **Honest label required:** "3rd-down snap share" not "3rd-down EPA." Narrative weight should be LOW since it's a snap-count story not a performance story.

---

## 5. Achievable RB metric pool (stub, full coverage later per kickoff)

1. `wepa_rushing_total` — `player_value_metrics`, 492 RBs in 2025.
2. `wepa_rushing_per_carry` — `metric_value / plays`.
3. `ypc` — `player_season_stats` rushing YDS / CAR.
4. `rushing_tds` — `player_season_stats` rushing TD.

## 6. Achievable WR metric pool (stub)

1. `receiving_yards` — `player_season_stats` receiving YDS.
2. `receptions` — REC.
3. `ypr` — YDS / REC.

WRs have no advanced metric in the DB. Stub coverage only. Flag for future: YAC, contested-catch %, separation — all PBP-dependent.

---

## 7. Cohort definitions we can actually compute

`player_value_metrics` already carries `conference_name`. `teams.level_code` exists (FBS/FCS). So:

- **P4 QBs** = `conference_name in ('ACC', 'Big 12', 'Big Ten', 'SEC')`. Carr (Notre Dame) falls under `FBS Independents` — Independent QBs at the P4-tier schools (Notre Dame, UConn) must be added to the P4 cohort explicitly via a hard-coded school list, or we use "P4+ND" as the labeled cohort. Recommend the explicit list.
- **G5 QBs** = FBS minus P4+ND.
- **All FBS QBs** = any `conference_name` present in `player_value_metrics`.

Min-volume gates (to hold with for v1):
- QB metrics from `wepa_passing`: min `plays` ≥ 250 (season) or ≥ 20 (single-game).
- QB from QBR: min 8 games with a QBR row.
- Traditional passing: min ATT ≥ 150 (season).
- RB `wepa_rushing`: min `plays` ≥ 80.
- WR receptions: min REC ≥ 20.

---

## 8. Test fixture viability (for TASK A.2)

The kickoff calls for three fixtures: CJ Carr (R15 Heisman finalist), a backup (R03), a walk-on (R00).

| Fixture | player_id | 2025 data found |
|---|---|---|
| C.J. Carr (Notre Dame QB) | 4788 | `wepa_passing=0.41, plays=307`; `wepa_rushing=0.33, plays=32`. Real, rankable. Signature Story must return a real story. |
| Backup QB (R03) | **TBD in A.2** — candidates: any QB with 50 ≤ ATT ≤ 150. Query: `select player_id, player_name from player_season_stats where season_year=2025 and category='passing' and stat_type='ATT' and stat_value_num between 50 and 150`. Should return a real story if it clears gates; otherwise skeleton. | |
| Walk-on (R00) | **TBD in A.2** — pick any QB with 0–10 ATT in `player_season_stats`. Low-volume QBs confirmed in that table (e.g. Luke Watkins, Hollywood Smothers, John White — negative/zero passing YDS). Such players will **not** have a `player_value_metrics.wepa_passing` row (the WEPA table starts at ~50 plays), which is exactly the behavior the skeleton path is designed for: every QB candidate metric fails its min-volume gate → engine returns the shape-accurate skeleton. | |

All three fixtures are supportable from existing data.

---

## 9. Recommended adjustments to TASKS A.1–A.3

1. **A.1 seed file `narrative_weight` tuning:** weight WEPA-per-play HIGHER than raw counting stats so the story favors the efficient-QB narrative over the pure-volume narrative. Weight `third_down_usage_share` LOW (0.2) because it's a snap share, not a performance signal.
2. **A.1 explicit min-volume per metric:** put the §7 numbers in the YAML.
3. **A.2 engine:** the `supporting_chart.data` cohort strip should carry the full qualifying cohort (e.g., all 72 P4+ND QBs with ≥ 250 plays), not just the top 10 — Figma will decide how many to render.
4. **A.3 CLI:** `python manage.py player-signature <slug>` should print the full candidate-metric scoreboard (all 10 QB metrics ranked, with percentile and the final narrative weight × percentile × log(sample) score), not just the winner. That's what makes Signature Story auditable — Kevin can see why a pick won.
5. **Honest naming:** use `wepa_passing_per_dropback` in the seed file, not `epa_per_dropback`. The two are not the same; WEPA is CFBD's weighted aggregate, EPA/play is a PBP-derived rate. Don't mislabel.
6. **Follow-up ticket to open:** "Ingest CFBD pbp_data to enable situational Signature Story v2" — blocks the kickoff's intended pressure/3rd-down/red-zone narratives.

---

## 10. Data sufficient to proceed

Feature A can proceed to TASK A.1 with this v1 pool. The stories it produces will be defensible ("best QB in the ACC by efficiency this season, ranks #1 of N with ≥ 250 dropbacks") but will not match the kickoff's example headline. That is a scope reality, not a blocker.
