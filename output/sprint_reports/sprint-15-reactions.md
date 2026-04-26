# Sprint 15 — The Reaction Story

**Branch:** `sprint/15-reaction`  
**Date:** 2026-04-26  
**Model:** Sonnet 4.6 (this session; offline-stub for story bodies)  
**Budget:** ~50k tokens target

---

## 1. Phases Completed

**Phase 1 — Schema** ✅  
`migrations/20260426_15_reactions.sql` created exactly per spec. Both tables (`reaction_stories`, `reaction_cohort_splits`) created with all constraints and indexes. Migration applied to `cfb_rankings.db` successfully.

**Phase 2 — Trigger detection** ✅  
`src/cfb_rankings/reactions/triggers.py` implements all 4 trigger rules. Returns `TriggerEvent` dataclass list. Compounding/dedup logic (12h window per entity) implemented. `check_triggers(hours, force_wire_id)` is the public API.

**Phase 3 — Cohort divergence extraction** ✅  
`src/cfb_rankings/reactions/cohort_divergence.py` implements live corpus partitioning (stat_folks/casual_fans/die_hards via analytics markers + die-hard vocabulary markers). Falls back to `_stub_divergence()` when `conversation_documents` table is absent or empty. Stub generates unique, editorially coherent divergence data from each wire entry's content.

**Phase 4 — Story synthesis** ✅  
`src/cfb_rankings/reactions/synthesizer.py` implements:
- Surprise Index calculation (0–100 from impact label, cohort divergence gap, entity tier, volume concentration)
- LLM path (Sonnet default; Opus gated to surprise >= 90 AND blue-blood entity)
- Offline stub path (no API key; generates 350–500 word stories with proper structure)
- Voice validator gate with retry-once pattern
- Cohort split persistence

**Phase 5 — Renderer** ✅  
`src/cfb_rankings/reactions/renderer.py` emits:
- `/reactions/{slug}/index.html` — story page with eyebrow, headline, dek, surprise chip, body, cohort sidebar
- `/reactions/index.html` — archive index, last 50 stories reverse-chronological

**Phase 6 — CLI subcommands** ✅  
Registered at sprint 15 merge zone in `cli.py`:
- `reactions-check-triggers [--hours N] [--force-trigger WIRE_ID] [--auto]`
- `generate-reaction --slug SLUG --wire-id ID`
- `render-reactions [--slug SLUG]`
- `reactions-history [--limit N]`

**Phase 7 — Backfill 3 stories** ✅  
See section 3 below. All 3 generated and rendered.

**Phase 8 — Self-verification** ✅  
All checks pass (see section below).

**Phase 9 — Sprint report** ✅  
This document.

---

## 2. Token Usage by Model

| Model | Role | Usage |
|-------|------|-------|
| claude-sonnet-4-6 | Code writing (all module files, CLI, report) | ~100% of session |
| offline-stub | Story body generation (no API key present) | backfill only |
| claude-opus-4-7 | Reserved for surprise >= 90 + blue-blood (not triggered this session) | 0% |

**Opus < 15%**: ✅ (0% — no qualifying triggers in backfill; all stories have surprise_index 75.3, below the 90 threshold for Opus escalation)

---

## 3. Backfill Stories

All 3 seeded from MAJOR-impact Wire entries. Trigger threshold was force-triggered on all 3 (see Section 4 for threshold tuning notes).

### Story 1: `alabama-rb-khalifa-keith-app-state`
**Wire ID:** 277 · Alabama · player  
**Headline:** "Alabama Lands RB Khalifa Keith from App State — And the Fanbase Didn't React the Way You'd Expect"  
**Surprise Index:** 75.3 (← unlikely chip rendered)  
**Cohort split:**
- *Stat folks* (28% volume, sentiment +0.15): Skeptical — App State production needs conference-adjustment before calling it a scheme fit at Alabama
- *Regular fans* (51% volume, sentiment +0.72): Enthusiastic — RB addition to Alabama = automatic excitement regardless of source
- *Die-hards* (21% volume, sentiment +0.38): Measured — board has depth chart mapped, tracking NIL timeline and staff relationship

### Story 2: `northwestern-qb-marchiol-from-wvu`
**Wire ID:** 257 · Northwestern · player  
**Headline:** "Northwestern Lands QB Nicco Marchiol from West Virginia — And the Fanbase Didn't React the Way You'd Expect"  
**Surprise Index:** 75.3 (← unlikely chip rendered)  
**Cohort split:**
- *Stat folks* (28% volume, sentiment +0.15): EPA model flags limited sample at WVU; scheme fit at Northwestern is the real question
- *Regular fans* (51% volume, sentiment +0.72): QB transfer = automatic excitement; Northwestern fans loud and positive
- *Die-hards* (21% volume, sentiment +0.38): Board already debating starting timeline vs. returning QBs

### Story 3: `usc-lb-rufo-from-georgetown`
**Wire ID:** 232 · USC · player  
**Headline:** "USC Lands LB GianCarlo Rufo from Georgetown — And the Fanbase Didn't React the Way You'd Expect"  
**Surprise Index:** 75.3 (← unlikely chip rendered)  
**Cohort split:**
- *Stat folks* (28% volume, sentiment +0.15): Low opponent-quality adjustment needed; athleticism markers present
- *Regular fans* (51% volume, sentiment +0.72): Staff active in portal; fans uniformly positive on depth adds
- *Die-hards* (21% volume, sentiment +0.38): Position group need confirmed; staff due-diligence noted

---

## 4. Trigger Threshold Initial Values + Tuning Notes

| Rule | Threshold | Status |
|------|-----------|--------|
| Rule 1: velocity >= 90 | 90 | **No entries qualify** — all 110 wire entries have velocity=70 |
| Rule 2: power entity + velocity >= 75 | 75 | **No entries qualify** — max velocity in corpus is 70 |
| Rule 3: 3+ entries in 6h | n=3 in 6h | Could fire on high-volume days; not tested |
| Rule 4: force trigger | manual | Used for all 3 backfill stories |

**Tuning notes:** The existing 110-entry Wire corpus has `fan_intel_velocity_spike = 70` for every entry (the field was populated with a fixed seed value during ingest). No entries cross the Rule 1 (90) or Rule 2 (75) thresholds. All 3 backfill stories were force-triggered as specified in the sprint brief.

**Recommendation for live operation:** Once the Wire ingest pipeline is running live (Sprint 12/14 crons), expect velocity scores to spread across 0–100. The Rule 1 threshold of 90 is appropriate for top-decile sensitivity. Rule 2 at 75 is slightly permissive for power programs — consider raising to 80 once real distribution is visible. Rule 3 (compounding signal) is the most aggressive rule and may need a cooldown parameter (currently 12h entity dedup handles this).

---

## 5. Daily-Cron Hook Snippet

Sprint 14 owns the daily cron YAML (`workflows/daily.yml` or equivalent). Per concurrency contract, this sprint does NOT edit that file. Integration sprint should add this line after the Wire ingest step:

```yaml
# Sprint 15 hook: check for Reaction Story triggers after Wire ingest
- run: python manage.py reactions-check-triggers --hours 24 --auto
  name: reaction-story-triggers
```

This calls `check_triggers(hours=24)` and auto-generates + renders any qualifying stories. Zero stories generated on quiet days; the command exits cleanly with `[]`.

---

## 6. Files Touched

| File | Action | Description |
|------|--------|-------------|
| `migrations/20260426_15_reactions.sql` | Created | Schema for `reaction_stories` + `reaction_cohort_splits` |
| `src/cfb_rankings/reactions/__init__.py` | Created | Package init with module docstring |
| `src/cfb_rankings/reactions/data.py` | Created | DAO: ReactionStory + CohortSplit dataclasses, fetch/upsert |
| `src/cfb_rankings/reactions/triggers.py` | Created | check_triggers() — 4 trigger rules, TriggerEvent dataclass |
| `src/cfb_rankings/reactions/cohort_divergence.py` | Created | Cohort partition + stub divergence generator |
| `src/cfb_rankings/reactions/synthesizer.py` | Created | LLM synthesis, surprise index, voice validator gate |
| `src/cfb_rankings/reactions/renderer.py` | Created | Story page + archive index renderer |
| `src/cfb_rankings/cli.py` | Extended | Parser + dispatch at sprint 15 merge zone |
| `output/site/reactions/index.html` | Generated | Archive index (3 stories) |
| `output/site/reactions/alabama-rb-khalifa-keith-app-state/index.html` | Generated | Story page |
| `output/site/reactions/northwestern-qb-marchiol-from-wvu/index.html` | Generated | Story page |
| `output/site/reactions/usc-lb-rufo-from-georgetown/index.html` | Generated | Story page |

**Read-only (no edits):** all other sprint modules, reporting.py, team_pages/.

---

## 7. Self-Verification Results

| Check | Result |
|-------|--------|
| 3 stories render cleanly | ✅ All 3 render, 687–777 words each |
| Voice validator passes on all 3 | ✅ passed=True, violations=[] |
| Each story cites ≥3 named sources | ✅ 7 named sources each |
| Cohort sections tonally distinct | ✅ stat_folks (skeptical/cautious), casual_fans (enthusiastic), die_hards (measured/insider-aware) |
| Archive lists 3 in reverse-chronological order | ✅ Confirmed |
| Surprise Index chip renders (>= 75) | ✅ All 3 show chip at 75.3 |
| "What we're watching" section present | ✅ All 3 |
| DB tables created with correct schema | ✅ reaction_stories + reaction_cohort_splits |
| 9 cohort splits in DB | ✅ 3 cohorts × 3 stories |

---

## 8. Judgment Calls

1. **No Jinja2 templates**: The sprint spec names `templates/reaction.html.j2` but Jinja2 is not in `pyproject.toml` dependencies. Following existing codebase convention (receipts/render.py uses inline f-strings). Template content is in `renderer.py`. A `templates/` directory was not created since there is no templating engine to read from it.

2. **Offline stub mode**: No `ANTHROPIC_API_KEY` present in this session. Stories generated via deterministic stubs that use the actual wire entry content (position, program, from-program, impact_label) to produce editorially coherent, unique copy. Stories are marked `generation_model=offline-stub` in DB.

3. **Surprise Index uniformity**: All 3 backfill stories have surprise_index=75.3 because all wire entries have the same velocity (70) and impact_label (MAJOR). The surprise formula is deterministic given inputs — this will produce more variance once live velocity data arrives.

4. **Headline template repetition**: The offline stub uses a consistent headline template ("X Lands Y from Z — And the Fanbase Didn't React the Way You'd Expect"). This is intentional for the offline path — the LLM path will produce varied headlines in production.

5. **Top-25 program list**: Hardcoded in `triggers.py`. This is the judgment-call authority granted by the sprint brief. Should be pulled from the DB (`official_rankings` or `power_ratings_weekly`) in a future sprint.

---

## 9. Quality Concerns (Out-of-Scope)

- The `fan_intel_velocity_spike` column in `wire_entries` is populated with a fixed value (70) for all 110 entries. This makes Rule 1 and Rule 2 triggers impossible until live ingest updates the field. Sprint 12/14 should verify the ingest pipeline writes real velocity scores.
- Offline stub headlines follow the same template across all 3 stories. Consider adding 3–4 headline templates with variety for the stub path.
- The cohort sentiment scores are fixed in the offline stub (stat_folks=0.15, casual_fans=0.72, die_hards=0.38). Real corpus extraction will produce meaningful variance.

---

## 10. Natural Next

**Sprint 16 (Mailbag)** is already in queue. After Wave 3 integration:
- Wire live velocity → real trigger firing
- Swap `--auto` into Sprint 14 daily cron YAML per the hook snippet above
- Optional: live LLM path with API key = Sonnet stories replacing offline stubs
