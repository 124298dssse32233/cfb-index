# Stash@{1} Inventory — Sprint 9.5

**Stash label:** `sprint12-checkpoint` (mislabeled)
**Actual contents:** Sprint 8 fan-intel WIP + cohort logic fixes + team-pages pulse polish
**Created on:** `sprint/10-threads` branch
**Total:** 1,661 lines across 15 files (+1,237 / -37)
**Diff file:** `output/sprint_reports/stash-1-inventory.diff`

---

## File-by-File Breakdown

| File | +/- | Sprint Territory | Recommendation |
|------|-----|-----------------|----------------|
| `data/reddit_backfill_state.json` | +220/-0 | Sprint 8 fan-intel (Reddit backfill) | DEFER |
| `docs/CHRONICLE_EDITORIAL_BRIEF.md` | +2/-0 | Sprint 8 editorial | APPLY |
| `logs/reddit_history_backfill_2500.log` | +230/-0 | Sprint 8 fan-intel (log file) | DROP |
| `scripts/backfill_reddit_history.py` | +7/-1 | Sprint 8 fan-intel (bug fix) | APPLY |
| `seeds/priority_teams.yaml` | +103/-0 | Sprint 5/8 fan-intel | DEFER |
| `seeds/reddit_historical_plan.yaml` | +100/-21 | Sprint 8 fan-intel | DEFER |
| `src/cfb_rankings/cli.py` | +72/-0 | Sprint 12 wire (superseded) | DROP |
| `src/cfb_rankings/cohorts/aggregate.py` | +6/-2 | Sprint 8 cohort logic | APPLY |
| `src/cfb_rankings/cohorts/divergence.py` | +11/-5 | Sprint 8 cohort logic | DEFER |
| `src/cfb_rankings/cohorts/test_aggregate.py` | +7/-4 | Sprint 8 tests | APPLY |
| `src/cfb_rankings/db.py` | +30/-1 | Sprint 8 infrastructure | APPLY |
| `src/cfb_rankings/team_pages/assets/styles.css` | +396/-0 | Sprint 8 pulse CSS | DEFER |
| `src/cfb_rankings/team_pages/data.py` | +11/-1 | Sprint 8 pulse (FLOOR fix) | DROP |
| `src/cfb_rankings/team_pages/renderer.py` | +41/-1 | Sprint 8 pulse (deferred) | DEFER |
| `src/cfb_rankings/team_pages/rivalry_card.py` | +1/-1 | Sprint 8 editorial copy | APPLY |

---

## Assessment by Category

### APPLY — Port to a new commit on integration/wave-1-2

**`docs/CHRONICLE_EDITORIAL_BRIEF.md` (+2):** Adds 2 lines reinforcing the voice register
("warm-and-fan-positioned, not aloof-magazine"). Small editorial doc improvement with no
code dependencies. Safe to apply.

**`scripts/backfill_reddit_history.py` (+7/-1):** Fixes a false-positive bug where city
subreddits (r/Knoxville, r/Athens, r/Austin) were tagging non-football posts as team
content. The fix requires football context even for city subreddit scrapes. Targeted and
well-scoped — this is the kind of fix that prevents data quality issues downstream.

**`src/cfb_rankings/cohorts/aggregate.py` (+6/-2):** Preserves computed sentiment even
when effective_n is below the publication floor. The FLOOR constants fix was already
applied in integration commit `01f3047`, but this is the upstream cohort logic that
goes with it — ensures the aggregator writes sentiment to the DB regardless of floor
threshold (floor filtering happens downstream in renderer). Part of the Sprint 8 cohort
polish that was split across stash and that commit.

**`src/cfb_rankings/cohorts/test_aggregate.py` (+7/-4):** Adds
`test_below_floor_still_writes_sentiment` — a targeted unit test for the above fix.
Test additions are safe to apply; they don't affect production behavior.

**`src/cfb_rankings/db.py` (+30/-1):** Adds idempotent migration application — allows
`ALTER TABLE ... ADD COLUMN` migrations to be re-run without errors by checking if the
column already exists. This is infrastructure-quality work with zero downside risk.
Currently absent from the integration branch.

**`src/cfb_rankings/team_pages/rivalry_card.py` (+1/-1):** One-line editorial copy
change ("Signal accumulating · per-rivalry weekly fan signal feeding in as the 2025-26
season..."). Trivial copy improvement.

### DROP — Already superseded or should never be committed

**`logs/reddit_history_backfill_2500.log` (+230):** A runtime log file that captures
one backfill run's output. Log files don't belong in git; they're ephemeral runtime
artifacts. This should never have been staged. Drop without concern.

**`src/cfb_rankings/cli.py` (+72):** Adds `wire-ingest` command with `sprint 12: wire`
merge-zone marker. Sprint 12 has since been merged to `integration/wave-1-2` via a
proper merge commit. The integration merge brought the canonical Sprint 12 CLI work.
This stash version appears to be a forward-port that was staged on sprint/10-threads
before the integration merged Sprint 12 — it's now obsolete. **Verify:** `wire-ingest`
is NOT present in the current `cli.py` on integration (checked: grep returns 0 hits,
meaning Sprint 12's wire CLI didn't actually include `wire-ingest` in its merge — this
stash addition is Sprint 8.5 fan-intel WIP that happens to reference sprint 12). Likely
a pre-staged staging of future work. Needs Kevin's review before applying.
→ Reclassify as DEFER if wire-ingest is needed.

**`src/cfb_rankings/team_pages/data.py` (+11/-1):** Adds FLOOR constants as module-level
and a comment block. This is precisely the fix that was already applied in integration
commit `01f3047` ("lifted FLOOR_AWAITING/FLOOR_GROWING to module-level"). The stash
version and the integration fix appear to be independently authored but equivalent.
**Fully superseded — drop.**

### DEFER — Needs Kevin's review before applying

**`data/reddit_backfill_state.json` (+220):** Adds completed backfill records for
Michigan (`michigan_team`) and Ohio State City (`ohiostate_city`) subreddits from
2022–2023. This is valid backfill state — but the current state file on disk may have
moved further along (or this batch may have already been run via a separate session).
Compare against current `data/reddit_backfill_state.json` before applying; no harm if
duplicate "ok" entries are merged, but needs inspection.

**`seeds/priority_teams.yaml` (+103):** Adds Sprint 5 profiled programs (11 teams) to
the priority_teams tracking list, with a comment that they were added to `profiles/`
but missed the priority_teams update. Fixes a cron bug where these programs weren't
getting team-tagged. Check against current priority_teams.yaml; if these teams are
already present, drop. If absent, this is a real gap that affects data quality.

**`seeds/reddit_historical_plan.yaml` (+100/-21):** Restructures reddit historical
backfill plan with `audience_bucket: local` classification for city subreddits. Pairs
with the backfill_reddit_history.py fix. May be superseded by further planning work,
or it may be the canonical current state. Needs diff against current file.

**`src/cfb_rankings/cohorts/divergence.py` (+11/-5):** Updates divergence qualification
logic — cohorts must have non-null sentiment AND `effective_n >= FLOOR_MIN`. Connected
to the aggregate.py fix. Worth applying as a pair with aggregate.py, but needs a test
run first to confirm no regressions in the divergence calculation.

**`src/cfb_rankings/team_pages/assets/styles.css` (+396):** Adds pulse CSS classes
(`pulse__badge--full`, `pulse__badge--low`, etc.). This is the Sprint 8.5 deferred
Pulse v2 styling work. The renderer.py changes in this stash reference `render_pulse_v2`
which is NOT present in the current integration branch (confirmed: `renderer.py` has
`_render_pulse` internal function but not `pulse_renderer.render_pulse_v2`). The CSS
is forward-staged for work that hasn't shipped yet. Apply when Sprint 8.5 ships.

**`src/cfb_rankings/team_pages/renderer.py` (+41/-1):** Imports `pulse_state` and
`render_pulse_v2` from not-yet-shipped modules. Per the Wave 1+2 integration report,
"live LLM theme extraction / fan-voice Lede LLM / sentiment classifier wire-up /
Conference Pulse module render / Player Pulse / The Room redesign" were all confirmed
absent from master and deferred to Sprint 8.5. This renderer change is part of that
deferred scope. **Do not apply until Sprint 8.5 ships the pulse_state/pulse_renderer
modules.**

---

## Summary Recommendation

Apply in a small clean-up commit (no code risk):
- `docs/CHRONICLE_EDITORIAL_BRIEF.md`
- `scripts/backfill_reddit_history.py`
- `src/cfb_rankings/cohorts/aggregate.py`
- `src/cfb_rankings/cohorts/test_aggregate.py`
- `src/cfb_rankings/db.py`
- `src/cfb_rankings/team_pages/rivalry_card.py`

Drop immediately (no value, fully superseded):
- `logs/reddit_history_backfill_2500.log`
- `src/cfb_rankings/team_pages/data.py`

Defer to Kevin review (check against current state before applying):
- `data/reddit_backfill_state.json`
- `seeds/priority_teams.yaml`
- `seeds/reddit_historical_plan.yaml`
- `src/cfb_rankings/cohorts/divergence.py`
- `src/cfb_rankings/cli.py` (reclassify as DROP if wire-ingest is redundant)

Defer to Sprint 8.5 (requires pulse_state/pulse_renderer modules):
- `src/cfb_rankings/team_pages/assets/styles.css`
- `src/cfb_rankings/team_pages/renderer.py`

**Do not apply or drop the stash itself** — preserve stash@{1} until Kevin has reviewed
the DEFER files and approved the APPLY list. After applying the 6 safe files and
confirming the DEFERs, drop the stash.
