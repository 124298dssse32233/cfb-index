# Claude Code — Sprint 9.5: Homepage Widget Wire-Up + Integration Cleanup

> **Inherits from `CLAUDE_CODE_AUTONOMY_AND_TOKEN_CONTRACT.md`.** Single sequential session. Closes follow-ups documented in `output/sprint_reports/wave-12-integration.md` so the integration branch is ready to fast-forward to master.

**Target budget: ~40k tokens. Runtime: 45-90 min.**

**Branch:** work on `integration/wave-1-2` (the Wave 1+2 integration branch). Don't create a new sprint branch — these are integration cleanups, not a new feature surface.

**File ownership:** anything in `editions/`, `editions/templates/`, `output/site/`, `.gitignore`, plus a small canon editorial fix. Don't touch other sprints' modules.

---

## What this sprint closes

Five known follow-ups from the Wave 1+2 integration report:

1. **Homepage widgets still read from stub JSON files instead of live tables** — the foundation issue. Sprint 9 shipped with stub_data/*.json placeholders pending Wave 2 surfaces; Wave 2 surfaces are now live.
2. **Canon validator failure on `jameis-winston::paragraph`** — one editorial entry didn't pass the consolidated voice validator post-merge.
3. **`.gitignore` missing `src/cfb_rankings/storylines/seeds/_drafts/`** — Sprint 10's `--auto` fallback writes draft scaffolds here that should never be committed.
4. **Full `build-site` end-to-end run** — the integration only got ~12 minutes in. Need a clean full-run to confirm no rendering regressions across the merged state.
5. **Stash@{1} editorial inventory** — the 1,661-line "sprint12-checkpoint" stash that's actually mislabeled Sprint 8 fan-intel WIP. Inventory it cleanly so we can decide whether to apply, drop, or defer.

---

## Phase 1 — Homepage widget wire-up (the main work, ~25k tokens)

The homepage was rendered by Sprint 9 using stub data files. Now that Wave 2 surfaces are live (Threads, Canon, Wire, Receipts have real DB tables populated), wire each homepage widget to query the live table.

### 1.1 Locate the four widgets in `editions/homepage_renderer.py`

Each widget currently reads from `stub_data/*.json`:

- **Active Threads section** (Roman XI in homepage v4) — currently reads `stub_data/threads.json`. Should query `storyline_threads` + `storyline_chapters` tables (Sprint 10 schema).
- **From The Canon section** (Roman XII) — currently reads `stub_data/canon_featured.json`. Should query `canon_lists` + `canon_entries` (Sprint 11 schema).
- **The Wire section** (Roman X) — currently reads `stub_data/wire_seed.json`. Should query `wire_entries` (Sprint 12 schema).
- **Receipts callouts** in cover-essay or sidebar — should query `predictive_claims` + `receipts_annual_lists` (Sprint 13 schema) for resolved/aged-well entries.

### 1.2 Replace stub reads with live queries

For each widget:

```python
# Before (stub):
with open("stub_data/threads.json") as f:
    threads = json.load(f)["threads"][:6]

# After (live):
from cfb_rankings.storylines.data import fetch_active_threads
threads = fetch_active_threads(limit=6, order_by="last_chapter_at DESC")
```

If the data-fetcher functions don't exist on the corresponding sprint module, build minimal ones inside `editions/homepage_renderer.py` that query the SQLite DB directly. Don't touch other sprint modules — keep the integration boundary clean.

### 1.3 Graceful fallback

If a sprint table is empty (e.g., no Wire entries this week, no resolved Receipts), the widget falls back to its stub_data JSON. Document this so the homepage never renders empty — it always has SOMETHING, even if the live data is thin.

### 1.4 Re-render homepage

```
python manage.py render-homepage
```

Verify `output/site/index.html` now reflects live data. Specifically:
- Active Threads section shows the 8 real threads with current chapter teasers from `storyline_chapters` (not the 6 from threads.json)
- From The Canon section shows a real Caleb Williams entry (or whichever entry is rotated in by editorial logic) from `canon_entries`
- The Wire section shows the most recent 8 entries from `wire_entries` (the 110-entry CFBD-backed dataset)
- Receipts callout shows a real aged-well take from `predictive_claims` where `outcome_verdict='hit'` and `surprise_index >= 75`

---

## Phase 2 — Canon validator failure fix (~3k tokens)

Locate `jameis-winston::paragraph` in the Canon module's authored editorial. Run it through the consolidated voice_validator. Identify which banned phrase trips it. Rewrite the offending sentence in fan voice. Re-validate. Re-render the entry page.

If the failure is on a phrase that's a false positive (legitimate non-taxonomy use of a banned word), document it as a banlist refinement candidate but DO NOT add a new exception unless clearly warranted — the rule is no banned phrases in fan-voice copy. Better to rewrite than to weaken the validator.

Re-run the canon validator sweep across all 175 entries to confirm 175/175 pass post-fix.

---

## Phase 3 — `.gitignore` + small hygiene (~2k tokens)

Add to `.gitignore`:

```
# Storyline draft scaffolds (LLM-generated drafts written by --auto fallback path)
src/cfb_rankings/storylines/seeds/_drafts/
```

Verify with `git status` that any existing files in `_drafts/` are now ignored. If files were accidentally committed in earlier sprints, leave them committed but ensure new ones are ignored going forward.

Also: check `git status` for any other artifact directories that should be gitignored (LLM cache files, temp build outputs, etc.) — apply judgment.

---

## Phase 4 — Stash@{1} editorial inventory (~5k tokens)

The mislabeled "sprint12-checkpoint" stash contains 1,661 lines of Sprint 8 fan-intel + team-pages-polish work. Don't apply it. Don't drop it. Inventory it.

```
git stash show -p stash@{1} > output/sprint_reports/stash-1-inventory.diff
```

Then write `output/sprint_reports/stash-1-inventory.md` summarizing:
- File-by-file breakdown of the 15 modified files
- Which sprint's territory each file belongs to (Sprint 8 fan-intel, Sprint 8 team-pages polish, mixed, etc.)
- Editorial assessment: which changes look valuable vs which look outdated/superseded
- Recommendation per file: APPLY (port to a new commit), DROP (already-superseded), or DEFER (needs human review)

This is documentation only — no actual changes to files. Future session uses this inventory to make the apply/drop/defer call.

---

## Phase 5 — Full `build-site` end-to-end + voice validator sweep (~5k tokens)

```
python manage.py build-site 2>&1 | tee output/sprint_reports/build-site-integration-run.log
```

Run to completion, even if it takes 30+ minutes. Capture full log.

Verify the final state:
- All 6 module surfaces render: homepage + editions/ + storylines/ + canon/ + wire/ + receipts/ + teams/
- No render errors in the log
- Output structure matches the integration report's expected directory tree
- Total file count ~ matches expectation (homepage + edition pages + 8 storylines + 175 canon entries + 110 wire entries + 761 receipts pages + 17 team pages + 11 conference pages + ...)

Then run a focused voice-validator sweep on a SAMPLE of pages (not the 51k-violation full sweep that's dominated by chrome false positives — that's a separate tooling sprint). Specifically:
- 5 randomly-selected storyline reader pages
- 5 randomly-selected canon entry pages  
- 5 randomly-selected wire entries' caption fields (queried directly from `wire_entries`)
- 5 randomly-selected receipts long-shot entries
- The homepage cover essay tease + 2 features

Expected: 0 violations on these editorial-content samples. If any violations surface, document them — they're real editorial leakage that should be fixed.

---

## Phase 6 — Update integration report + commit (~2k tokens)

Update `output/sprint_reports/wave-12-integration.md` with a new section "Sprint 9.5 Cleanup":
- Homepage widget wire-up status (live or partial fallback)
- Canon validator post-fix sweep result
- .gitignore additions
- Stash inventory document path
- Full build-site result + log path
- Voice validator sample sweep result

Commit all Sprint 9.5 changes to `integration/wave-1-2` with message:

```
sprint 9.5: homepage widget wire-up + integration cleanup

- Wire 4 homepage widgets to live tables (Threads, Canon, Wire, Receipts)
- Fix canon validator failure on jameis-winston::paragraph
- Add storylines/_drafts/ to .gitignore
- Inventory stash@{1} (1,661-line mislabeled fan-intel WIP)
- Full build-site verified
- Voice validator sample sweep clean
```

Push to remote.

---

## Decision authority

Autonomous on: which fields to read from live tables, fallback logic when tables are empty, jameis-winston rewrite phrasing, stash inventory recommendations, additional gitignore entries.

Stop and flag only on the four canonical hard-blocker conditions.

---

## Report back with

1. Phase 1 — 4 widgets wired; before/after of one homepage section showing live vs stub data
2. Phase 2 — jameis-winston rewrite (original + new)
3. Phase 3 — .gitignore additions list
4. Phase 4 — stash inventory document path + summary
5. Phase 5 — build-site full-run completion status + voice sample sweep result
6. Phase 6 — final integration commit SHA pushed to remote

Token usage. Files touched. Time elapsed. After the commit pushes to `integration/wave-1-2`, session complete. Kevin then merges integration → master manually.
