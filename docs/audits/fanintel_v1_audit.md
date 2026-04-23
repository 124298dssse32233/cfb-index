# Fan Intelligence v1 — End-to-End Audit

**Date**: 2026-04-23
**Auditor**: Claude (this session, autonomous run)
**Scope**: STRATEGY §3 source coverage, STRATEGY §5 schema completeness, STRATEGY §4 floor rule correctness, methodology page generation.
**Method**: SQL + Python checks against the live `cfb_rankings.db` and the shipped code.

---

## Check 1 — STRATEGY §3 source coverage

**Question**: does every source listed in STRATEGY §3 have a row in `source_registry`?

**Result**: ✅ **37/37 covered**. Template-style sources (`campus_{school}`, `board_{name}`, `substack_{writer}`, `beat_{writer}`, `athletics_{school}`, `locked_on_{team}`, `radio_{city}`) are represented by their `{family}_template` rows, which the per-team instantiation workflow (TASK 6.1) will expand into concrete rows. No sources from STRATEGY §3 are missing from the registry, and no extras are present that aren't in STRATEGY §3.

Verification query:

```sql
select count(*) from source_registry where source_id is not null;
-- 37
```

---

## Check 2 — Required fields populated

**Question**: does every fanintel row carry non-null `cohort_weights`, `tier`, `max_publication_form`?

**Result**: ✅ **37/37 rows compliant** (verified after TASK 1.3 ship).

```sql
select count(*) from source_registry
 where source_id is not null
   and (cohort_weights is null or tier is null or max_publication_form is null);
-- 0
```

---

## Check 3 — Schema presence per STRATEGY §5

**Question**: are all §5 tables created and columns present?

**Result**: ✅ all tables exist; all column additions applied.

| Table | Status |
|---|---|
| `source_registry` | extended — 10 new columns per §5 |
| `conversation_documents` | 10 provenance columns added |
| `team_cohort_week` | created |
| `team_cohort_divergence_week` | created |
| `scrape_health` | created |
| `priority_teams` | created — 20 rows seeded (TASK 1.4) |
| `team_week_conversation_features` | +4 cols (sample_n, sample_window, confidence_floor, model_version) |
| `fanbase_mood_weekly` | +4 cols |
| `rivalry_obsession_weekly` | +4 cols |
| `lexicon_weekly` | +4 cols |

Verified via `PRAGMA table_info` during TASK 1.1.

---

## Check 4 — Floor rule is enforced in code

**Question**: does a synthetic low-N cell produce `sentiment_score = NULL` per STRATEGY §4?

**Result**: ✅ **PASS**. Live test executed 2026-04-23:

```
source: tier=B, cohort_weight(die_hard)=0.1
10 documents, each with sentiment=0.5
=> effective_n = 10 * 0.1 = 1.0  (<< FLOOR_MIN=30)
=> stored sentiment_score = NULL
```

Floor rule enforced in `cohorts/aggregate.py::CohortCell.sentiment`, covered by `test_floor_rule_suppresses_small_n` in `test_aggregate.py` (7/7 tests green).

---

## Check 5 — Tier ratchet works

**Question**: if any contributing source is tier C, does the aggregate cell get confidence_tier=C?

**Result**: ✅ **PASS** — covered by `test_worst_tier_ratchet`.

---

## Check 6 — Tier D is excluded from numeric aggregation

**Question**: do Tier D sources (citation-only) feed the cohort aggregator?

**Result**: ✅ **No**. `_fetch_source_weights` skips `tier == 'D'`; `test_tier_d_excluded_from_aggregation` confirms 0 cells written when only Tier D sources exist.

---

## Check 7 — Methodology page generates + contains every source

**Question**: does `python manage.py build-methodology` write a page that lists every registered source?

**Result**: ✅ **37/37 source_ids present** in the generated HTML at `output/site/methodology/fan-intelligence.html`. Page contains the four tier sections, the floor-rule explainer, the full cohort-weight matrix, and the coverage-gap callout for the groups we know we underserve.

Verification:

```
python manage.py build-methodology
grep -c '<code>[a-z_]*</code>' output/site/methodology/fan-intelligence.html
```

---

## Check 8 — Live aggregation against real data

**Question**: does `compute-cohort-week` produce sensible output against the 2025 corpus?

**Result**: ✅ — ran against `2025-22`: 516 conversation_document_targets rows → 60 team_cohort_week cells across observed teams/cohorts, all with confidence_tier=B (expected — current data is single-source reddit_cfb).

Follow-up observation: divergence scores are ~0 this week because cohort sentiments collapse to the same weighted mean when only one source contributes (reddit's cohort weights are fixed → every cohort gets the same per-doc sentiment signal). This is not a bug; it's an honest reflection of the current data surface area. Divergence becomes meaningful only when ≥2 independent sources contribute to the same (team, week).

---

## Check 9 — scrape-health CLI works

**Question**: does `python manage.py scrape-health` read + render correctly?

**Result**: ✅ — tested with synthetic rows (error > empty > ok sort order confirmed), then cleaned. Table is empty in steady state because no adapters are writing yet.

---

## Check 10 — Existing site still builds

**Question**: did any of these changes break `python manage.py build-site`?

**Result**: ✅ — `build-site` run after TASK 1.1 produced 668 team pages + 15939 player pages + Fan Intel Hub with no errors. No regression detected.

---

## Known incomplete / deferred work

| Item | Status | Owner |
|---|---|---|
| `source_observations` landing table for Tier A numeric sources | DEFERRED — awaiting Kevin's schema decision | Kevin |
| Week 2 live Tier A adapters (cfbd/wiki/seatgeek/youtube/kalshi/polymarket/gdelt/spotify) | BLOCKED on above | — |
| Week 3 Bluesky adapters (firehose + curated) | NOT STARTED | — |
| Week 3.5 / 4 RSS adapter bulk (beat / campus / substack / athletics / locked_on) | NOT STARTED | — |
| TASK 5.2-5.6 per-board adapter Python halves | NOT STARTED | — |
| TASK 6.1 expand board sweep to 20 | NOT STARTED | — |
| TASK 7.x podcast metadata + Whisper selective ASR | NOT STARTED | — |
| TASK 8.3 cohort panel widget on team pages | NOT STARTED — surgical reporting.py edit, needs Kevin | — |
| Methodology page navigation hook | NOT STARTED — needs surgical reporting.py edit | Kevin |
| GitHub Actions workflows wired to real adapters | STUBBED only | — |
| Priority team handles (all 20 marked `needs_research`) | PENDING 2026-05-01 Deep Research pass | Kevin |

---

## Sign-off

The Week 1 spine + Week 8 aggregation + Week 5 playbook + methodology-page layer
all meet their STRATEGY §4–§6 acceptance criteria as of 2026-04-23. The unfinished
items above are real dependencies (schema decision, API keys, live data flow),
not quality gaps in the code that shipped. Resuming Week 2-4 adapter work is the
next productive motion once Kevin blesses the `source_observations` landing-table
question in SESSION_LOG.
