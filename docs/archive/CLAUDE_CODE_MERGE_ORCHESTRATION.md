# Claude Code — Wave 1 + Wave 2 Merge Orchestration

> **Inherits from `CLAUDE_CODE_AUTONOMY_AND_TOKEN_CONTRACT.md`.** Single sequential session. Merges 6 sprint branches into master, resolves known conflicts, validates integration.

**Target budget: ~50k tokens. Runtime: 1.5–2.5 hours.**

**File ownership:** ALL files (this sprint's job is to integrate). But the integrating agent edits ONLY:
- conflict-resolution edits in `cli.py`, `src/cfb_rankings/team_pages/voice_validator.py`, and any `__init__.py` collisions
- merge commit messages
- migration ordering verification
- a final `output/sprint_reports/wave-12-integration.md` report

---

## The 6 branches to integrate (in this order, alphabetical for determinism)

1. `sprint/8-pulse` — Pulse v2 + Conference Pulse foundation. WIP working tree (~85 files staged) needs to be assessed: commit anything that's clearly Sprint 8's territory; stash anything that bleeds into other sprints' modules.
2. `sprint/9-editions` — Edition framework + Homepage v4 + 4 seeded editions
3. `sprint/10-threads` — Storyline Threads + shared `llm_runtime.py`
4. `sprint/11-canon` — The Canon (3 lists, 175 entries). Module currently in `.worktrees/sprint-11-canon/`
5. `sprint/12-wire` — Wire (110 real CFBD portal entries + captions). Module currently lives on `sprint/12-wire` branch
6. `sprint/13-receipts` — Receipts (15.7k claims, 90 in-session editorial entries). Module in `.worktrees/sprint-13-receipts/`

---

## Phase 1 — Pre-merge audit + WIP triage (15 min)

### 1.1 Audit current state

Run `git branch --list` and `git status` on the current checkout. Confirm we're on `sprint/10-threads`.

For each of the 6 sprint branches, run `git log <branch> --oneline -10` and capture the head commit + recent commit messages. Verify each branch is at the expected state per the sprint reports.

For each worktree (`.worktrees/sprint-11-canon`, `.worktrees/sprint-13-receipts`), check whether the worktree is clean or has uncommitted changes. If uncommitted, flag.

### 1.2 Triage the 85 modified files in current working tree

This is Sprint 8's WIP that was never committed. Categorize each modified file:
- (a) Sprint 8's own territory (`team_pages/`, `cohorts/`, `data/`, profile changes, Pulse-related migrations) → commit to `sprint/8-pulse` branch
- (b) Bleeding from another sprint that shouldn't be on this branch → stash with descriptive message
- (c) Genuinely shared infrastructure (e.g., `team_pages/voice_validator.py` if Sprint 8 owns the canonical) → commit to `sprint/8-pulse`

Commit category-(a) files to `sprint/8-pulse` with one consolidated commit message: "sprint 8 final commit: pulse v2 working tree consolidated for integration."

### 1.3 Produce a per-branch readiness report

For each of the 6 branches, output:
- Last commit SHA + message
- Files in scope (module path)
- Migrations on that branch (`migrations/20260425_<NN>_*`)
- Voice validator variant present
- CLI subparser registrations added
- Sprint report file path

This is a one-page report committed to `output/sprint_reports/wave-12-integration.md` Phase 1 section.

---

## Phase 2 — Sequential merge to master (60-90 min)

### 2.1 Create integration branch

From master:
```
git checkout master
git pull origin master  # if remote has changes
git checkout -b integration/wave-1-2
```

### 2.2 Merge each sprint branch in order

For each of the 6 branches in order (8, 9, 10, 11, 12, 13):

1. `git merge sprint/<NN>-<name>` (or for Canon/Receipts, merge from worktree branches)
2. Expect conflicts at:
   - `cli.py` merge zone (~line 750-1020) — multiple subparser registrations
   - `src/cfb_rankings/team_pages/voice_validator.py` — multiple banlist variants
3. Resolve conflicts per Phase 3 rules below
4. Run `python -c "import src.cfb_rankings"` to confirm no import errors
5. `git commit` with message: "integration: merge sprint/<NN>-<name>"

### 2.3 Conflict resolution rules

**`cli.py` merge zone**: collect ALL subparser registrations from ALL sprints, ordered alphabetically by sprint number. Format:

```python
# ---- sprint 8: pulse ----
# (Sprint 8's registrations)
# ---- sprint 9: editions ----
# (Sprint 9's registrations)
# ---- sprint 10: storylines ----
# (Sprint 10's registrations)
# ---- sprint 11: canon ----
# (Sprint 11's registrations)
# ---- sprint 12: wire ----
# (Sprint 12's registrations)
# ---- sprint 13: receipts ----
# (Sprint 13's registrations)
```

If two sprints registered subcommands with the same name, that's a structural bug — flag, don't auto-resolve.

**`team_pages/voice_validator.py`** three-way merge:
- Take Sprint 10's `_build_pattern()` word-boundary regex implementation (the structural fix)
- Take Sprint 10's removal of bare "cohort" + addition of explicit taxonomy variants (`analytics cohort`, `casual cohort`, `die-hard cohort`)
- Take Sprint 10's morphological additions (`methodologies`, `methodological`)
- Take Sprint 13's 15 receipts-specific tone-violation phrases (`hot take`, `L take`, `cope`, `amirite`, etc.)
- Result: ~60 banned phrases total, all using word-boundary regex

Verify result by running `python -m pytest src/cfb_rankings/team_pages/test_voice_validator.py -v` (if tests exist; if not, run sprint 10's `test_chapter_authoring.py` which exercises the validator).

**Migration ordering**: confirm migrations apply in numerical order (08 → 09 → 10 → 11 → 12 → 13). If any migration assumes a table that's created by a later migration, restructure.

**Module collisions**: each sprint's module (`editions/`, `storylines/`, `canon/`, `wire/`, `receipts/`) should be disjoint. If two sprints created files at the same path, that's a structural bug — flag.

**Voice validator imports**: any sprint module that has its own local `voice_validator.py` should be replaced with an import from `team_pages/voice_validator.py`. If a module has its own copy that ADDS phrases not yet in canonical, port those phrases to canonical first, then make the module import from canonical.

### 2.4 Stash handling

If `sprint/8-pulse` had uncommitted WIP that wasn't committed in Phase 1.2, stash it with `git stash push -m "wip-leftover"` before merging. After all 6 merges complete, `git stash list` should be empty (or only contain explicit "wip-leftover" entries that need separate review).

---

## Phase 3 — Post-merge integration validation (30 min)

### 3.1 Apply all migrations

```
python manage.py apply-migrations
```

Expected result: 6 migrations apply cleanly in order. If any duplicates a column or fails, debug:
- The pre-existing `conference_slug` duplicate column bug may surface here. Fix by adding `IF NOT EXISTS` guards to the offending migration or by documenting the schema mismatch.
- If sprint 8's migration (`20260425_08_conferences_schema.sql`) creates a table that an earlier migration also created, reconcile to use ALTER TABLE additions instead of CREATE TABLE.

### 3.2 Build the integrated site

```
python manage.py build-site
```

Verify:
- No errors during render
- All 6 module renderers complete successfully
- Output structure includes:
  - `output/site/index.html` (homepage from Sprint 9)
  - `output/site/editions/` (Sprint 9 editions + article pages)
  - `output/site/storylines/` (8 thread pages from Sprint 10)
  - `output/site/canon/` (3 list pages + entry pages from Sprint 11)
  - `output/site/wire/` (Wire index + monthly archives from Sprint 12)
  - `output/site/receipts/` (1 landing + 1 annual + ≤759 source profiles from Sprint 13)
  - `output/site/teams/<slug>.html` (Pulse-redesigned, with `pulse__*` CSS classes)

### 3.3 Voice validator full sweep

Run the consolidated voice validator across ALL rendered HTML in `output/site/`:

```python
import re, glob
from cfb_rankings.team_pages.voice_validator import validate_fan_voice
violations = []
for path in glob.glob("output/site/**/*.html", recursive=True):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    passed, vs = validate_fan_voice(text, source=path)
    if not passed:
        violations.extend(vs)
print(f"Violations: {len(violations)}")
for v in violations[:20]:
    print(v)
```

Expected: 0 violations. If any, document them in the integration report (some may be acceptable false positives; some may be genuine leakage that needs the next iteration to fix).

### 3.4 Smoke-test integration points

For each sprint's homepage integration widget, verify it now reads from live data instead of stub:

- Sprint 9's homepage Threads section reads from `storyline_threads` table, not `stub_data/threads.json`
- Sprint 9's homepage Canon section reads from `canon_entries` table, not stub
- Sprint 9's homepage Wire section reads from `wire_entries`, not stub
- Sprint 9's homepage Receipts widget reads from receipts data, not placeholder

If any widget is still reading from stub data after integration, update it to query the live table. This is expected post-merge cleanup.

### 3.5 Commit final integration

After all phases land, commit the final state:

```
git commit -m "integration: wave 1+2 merged · all 6 sprints reconciled · voice validator unified"
git push origin integration/wave-1-2
```

Open a PR from `integration/wave-1-2` → `master`. After Kevin's review, fast-forward merge to master.

---

## Phase 4 — Integration report (15 min)

Update `output/sprint_reports/wave-12-integration.md` with the post-merge state:

- Per-sprint merge status (clean / had conflicts / required schema fix)
- Final voice validator banlist count and any deltas
- Final cli.py subparser registrations (full list)
- Migrations applied in order
- All output directories rendered cleanly
- Voice validator sweep result (violations count)
- Stash list (should be empty or only explicit wip)
- Pre-existing bugs hit during integration + how resolved
- Quality concerns observed
- Natural next: Sprint 8.5 (Pulse follow-ups for deferred LLM work) → Wave 3 (Daily / Reaction / Mailbag)

---

## Decision authority

Autonomous on: all conflict resolution choices that follow the rules above; commit message wording; minor refactors during merge (e.g., extracting a duplicated function into a shared module); migration restructure when a duplicate column / table situation surfaces.

Stop and flag only if:
- Two sprints registered the same CLI subcommand name (structural bug requiring Kevin's call)
- Two sprints created identical filenames at the same path (structural bug)
- A migration assumes a schema state that no other migration produces (data-integrity issue)
- The integration build fails with an unrecoverable error after 3 attempts

Anything else: decide, document, proceed.

---

## Report back with

1. Per-branch readiness pre-merge (Phase 1.3 report)
2. Conflicts encountered + resolutions per branch
3. Migration application result + any schema fixes
4. Voice validator unified count + sweep violations
5. CLI subparser final list
6. Build-site output structure verification
7. Stash list (post-integration)
8. Pre-existing bugs encountered
9. Quality concerns
10. Natural next: 8.5 Pulse follow-ups, then Wave 3

Token usage by model. Files touched. Time elapsed.

When the integration branch is pushed and the PR is open, session complete.
