# Claude Code — Wave 3 Land + Polish + Verify

> **Inherits from `CLAUDE_CODE_AUTONOMY_AND_TOKEN_CONTRACT.md`.** Single sequential session. Audits Wave 3 sprint state, merges what's ready, renders everything, audits + polishes new surfaces, verifies. Does NOT enable GitHub Actions crons — that's a separate sprint (`CLAUDE_CODE_FIRST_LIVE_CYCLE_AND_GO_LIVE.md`).

**Recommended model: Sonnet 4.6.**

**Target budget: ~50k tokens. Runtime: 1.5–2.5 hours.**

**Branch:** work directly on `master`. Each Wave 3 sprint branch gets rebased + fast-forward-merged into master sequentially. No new feature branch.

**File ownership:**
- Edit: any conflict-resolution edits during sprint merges (cli.py merge zones, voice_validator.py if it conflicts)
- Edit: any module's renderer template / Jinja file / inline-template Python if visual polish is needed for Wave 3 surfaces
- Edit: shared CSS in `output/site/assets/` only if a token/utility is missing
- Read-only: data layers, reporting.py outside documented hooks

---

## Why this sprint

Three Wave 3 sprints (`sprint/14-daily`, `sprint/15-reaction`, `sprint/16-mailbag`) ran in parallel. Their state is unknown — some may be done, some may not. The Visual Polish sprint already shipped to master (commit `a63ff79` per Kevin's note); Wave 3 surfaces may have the same stub-template bug (The Room shipped totally unstyled).

This sprint:
1. Audits Wave 3 state — which branches exist, which are complete
2. Sequentially merges each completed sprint to master with conflict resolution per documented rules
3. Renders all new surfaces
4. Audits new Wave 3 surfaces for the same visual-polish gap that hit The Room
5. Fixes any stub-styled new surfaces
6. Final build-site verification
7. Reports state + readiness for go-live

---

## Phase 1 — Wave 3 state audit (5 min, ~2k tokens)

### 1.1 Confirm master state

```
git fetch origin
git checkout master
git pull origin master
git log --oneline -5  # confirm visual-polish + sprint 8.5 are landed
```

Expected on master: visual-polish-001 commit, sprint/8.5-pulse-followups merged commit, integration/wave-1-2 merged commit.

### 1.2 Inventory Wave 3 branches

```
git branch -a | grep -E "sprint/(14-daily|15-reaction|16-mailbag)"
git log origin/sprint/14-daily --oneline -5 2>/dev/null || echo "14-daily: no remote branch"
git log origin/sprint/15-reaction --oneline -5 2>/dev/null || echo "15-reaction: no remote branch"
git log origin/sprint/16-mailbag --oneline -5 2>/dev/null || echo "16-mailbag: no remote branch"
```

For each branch, classify:
- **DONE** — recent commits with sprint-completion-style messages, sprint report file present at `output/sprint_reports/sprint-N-*.md`
- **IN PROGRESS** — branch exists but no completion commit; the corresponding Claude Code window is still running
- **MISSING** — no remote branch at all

If any are IN PROGRESS, **do not interfere** with that branch. Work only on DONE branches in this session.

### 1.3 Read the sprint report for each DONE branch

For each DONE sprint, read `output/sprint_reports/sprint-N-*.md` from that branch. Verify:
- Sprint reports completion of all phases
- Voice validator passed
- Files-touched list matches what the prompt scoped
- No "stop and flag" hard-blocker conditions documented

If a DONE branch has a sprint report flagging a hard-blocker, **leave it for Kevin's review** — don't merge.

---

## Phase 2 — Sequential merge to master (30-60 min, ~15k tokens)

### 2.1 Merge order

For each DONE branch, in this order: 14 → 15 → 16. (Order matters because Sprint 15's report should contain a daily-cron-hook snippet that Sprint 14's workflow YAML needs.)

If 14 is IN PROGRESS but 15 or 16 is DONE, merge what's done; the cron-hook integration becomes a follow-up.

### 2.2 Per-branch merge procedure

For each DONE branch:

```
git checkout master
git pull origin master  # ensure we have the latest before each merge
git checkout sprint/<NN>-<name>
git rebase master  # rebase branch onto current master
# resolve conflicts per Phase 2.3 if any
git checkout master
git merge --ff-only sprint/<NN>-<name>
git push origin master
```

If `git merge --ff-only` fails, the rebase didn't actually update the branch tip — investigate and retry.

### 2.3 Conflict resolution rules

**`cli.py` merge zone** (the `# ---- sprint NN: <name> ----` marker blocks):
- Each Wave 3 sprint adds its own marker block alphabetically by sprint number
- If two Wave 3 sprints registered the same subcommand name, that's a structural bug — flag, stop, leave for Kevin
- Otherwise: just stack the marker blocks in sprint-number order

**`team_pages/voice_validator.py`**:
- Wave 3 sprints should NOT have edited this file — it's owned by the Pulse / team-pages module
- If a Wave 3 branch did edit it: take master's version, document the conflict in the sprint report

**`migrations/`**:
- Each Wave 3 sprint adds files with sprint-prefixed numeric prefixes (`20260426_14_*`, `_15_*`, `_16_*`) — no conflicts expected
- If a numbered prefix collision exists, flag

**Module directories** (`daily/`, `reactions/`, `mailbag/`):
- Disjoint by design — no conflicts expected
- If somehow a file appears in two modules, flag

**GitHub Actions YAMLs**:
- Sprint 14 creates `.github/workflows/the-daily-06am-et.yml`
- Sprint 16 creates `.github/workflows/mailbag-friday-09am-et.yml`
- Sprint 15 doesn't create one but may reference Sprint 14's file in its sprint report (don't edit Sprint 14's YAML directly — that's the post-merge integration)

### 2.4 Post-merge sanity per sprint

After each merge:

```
python -c "import cfb_rankings"  # confirm imports clean
python manage.py --help | head -50  # confirm new subcommands registered
```

If imports fail, debug inline.

### 2.5 Apply migrations

After all merges:

```
python manage.py apply-migrations
```

Expected: 14, 15, 16 migrations apply cleanly. If any fails (column duplicate, table conflict), debug per the merge-orchestration sprint's pattern (add IF NOT EXISTS guards, reorder, etc.).

---

## Phase 3 — Render all new surfaces (15-30 min, ~5k tokens)

### 3.1 Render each Wave 3 surface

```
python manage.py generate-daily        # if exists; otherwise the Daily's actual generation subcommand
python manage.py render-daily

python manage.py reactions-check-triggers --hours 168 --auto  # backfill any obvious triggers from last week
python manage.py render-reactions

python manage.py mailbag-seed-submissions --n 5  # only if no real submissions yet
python manage.py mailbag-curate-submissions --max 3
python manage.py mailbag-generate-answers
python manage.py render-mailbag
```

The actual subcommand names should match what each sprint's report documents. If a name differs, check `cli.py` for the registered name.

If any command errors with "no such subcommand", check the sprint's `cli.py` registration in the merge zone — the merge may have dropped it.

### 3.2 Verify outputs

```
ls output/site/daily/
ls output/site/reactions/
ls output/site/mailbag/
```

Each should have at least an `index.html` plus per-edition / per-story subdirectories.

---

## Phase 4 — Visual polish audit on Wave 3 surfaces (15 min, ~5k tokens)

Use the same audit pattern as `CLAUDE_CODE_VISUAL_POLISH_AUDIT.md`:

```python
import re
from pathlib import Path

def style_audit(path: str) -> dict:
    text = Path(path).read_text(encoding='utf-8')
    return {
        "path": path,
        "has_doctype": text.startswith("<!DOCTYPE"),
        "has_head_link_css": bool(re.search(r'<link[^>]+rel="stylesheet"', text, re.I)),
        "has_design_token_class": bool(re.search(r'class="[^"]*(?:pulse__|edition__|chronicle__|nav__|module__|daily__|reaction__|mailbag__)', text)),
        "byte_count": len(text),
    }

paths = [
    "output/site/daily/index.html",
    "output/site/reactions/index.html",
    "output/site/mailbag/index.html",
    "output/site/mailbag/submit/index.html",
]
# also one of each archive entry
import glob
for p in glob.glob("output/site/daily/*/index.html")[:1]: paths.append(p)
for p in glob.glob("output/site/reactions/*/index.html")[:1]: paths.append(p)
for p in glob.glob("output/site/mailbag/*/index.html")[:1]: paths.append(p)

for p in paths:
    print(style_audit(p))
```

A page is **stub-styled** if:
- Missing `<link rel="stylesheet">` AND no Tailwind / design-token classes
- byte_count < 5KB on a content page

---

## Phase 5 — Fix stub-styled Wave 3 surfaces if any (~15k tokens)

For each stub-styled Wave 3 page identified in Phase 4:

1. Locate the renderer + template (`src/cfb_rankings/{daily,reactions,mailbag}/templates/`)
2. Diff against the closest reference template:
   - Daily / Mailbag → use Edition page chrome (`editions/templates/edition.html.j2`)
   - Reactions → use Storylines / Edition chrome blend
3. Apply the standard `<head>` + nav + main + footer
4. Use surface-appropriate module classes (`daily__*`, `reaction__*`, `mailbag__*` — define namespace in shared CSS if not present)
5. Re-render via the surface's CLI subcommand
6. Re-run Phase 4 audit on the fixed pages

If a surface ALREADY uses the design system properly, skip it. Don't over-edit.

If the polish work for a surface exceeds 30 minutes of edits, flag in the report and leave a TODO — don't try to over-rewrite in this session.

---

## Phase 6 — Final build-site + voice validator sweep (10 min, ~3k tokens)

### 6.1 Targeted renders (avoid the build-site player-page hang)

Skip the full `build-site` (the player+Heisman cache step has a known hang per Kevin's earlier session). Instead, run targeted renders to refresh the surfaces that matter:

```
python manage.py render-team-pages
python manage.py render-conferences-pulse --all
python manage.py render-the-room --top 15
python manage.py render-storylines
python manage.py render-canon-all
python manage.py render-receipts  # or whatever the receipts subcommand is
python manage.py render-homepage
python manage.py render-daily
python manage.py render-reactions
python manage.py render-mailbag
```

Skip any subcommand that doesn't exist (no error — just keep going).

### 6.2 Voice validator sweep

Run the consolidated voice validator across the live-rendered HTML:

```python
import glob
from cfb_rankings.team_pages.voice_validator import validate_fan_voice

violations = []
sample_paths = [
    "output/site/index.html",
    "output/site/daily/index.html",
    "output/site/reactions/index.html",
    "output/site/mailbag/index.html",
    "output/site/teams/notre-dame.html",
    "output/site/teams/alabama.html",
    "output/site/conferences/fbs-sec.html",
    "output/site/storylines/the-12-team-playoff-settling.html",
    "output/site/players/the-room.html",
]
# add 1 of each archive
import glob
for p in glob.glob("output/site/daily/*/index.html")[:1]: sample_paths.append(p)
for p in glob.glob("output/site/reactions/*/index.html")[:1]: sample_paths.append(p)
for p in glob.glob("output/site/mailbag/*/index.html")[:1]: sample_paths.append(p)

for p in sample_paths:
    try:
        with open(p, encoding='utf-8') as f:
            text = f.read()
        passed, vs = validate_fan_voice(text, source=p)
        if not passed:
            violations.extend(vs)
    except FileNotFoundError:
        violations.append(f"file missing: {p}")

print(f"Violations: {len(violations)}")
for v in violations[:30]:
    print(v)
```

Expected: 0 substantive violations on editorial-content samples (chrome false positives don't count). Document any real banned-phrase leakage.

---

## Phase 7 — Sprint report (15 min, ~2k tokens)

Write `output/sprint_reports/wave-3-land-and-polish.md`:

1. **Phase 1 audit** — per-branch state (DONE / IN PROGRESS / MISSING)
2. **Phase 2 merges** — per-branch merge result, conflict resolution if any, final master SHA
3. **Phase 3 renders** — per-surface success / errors
4. **Phase 4 visual audit** — per-surface pass / stub
5. **Phase 5 polish fixes** — what was fixed, before/after
6. **Phase 6 voice validator sweep** — count + any real violations
7. **Token usage** by model (target: Sonnet >85%, Opus near 0%)
8. **Files touched** — every file modified
9. **Quality concerns** — anything noted
10. **IN PROGRESS branches** (if any) — what's still pending
11. **Natural next:** fire `CLAUDE_CODE_FIRST_LIVE_CYCLE_AND_GO_LIVE.md` to flip the cron guards

Commit the report:
```
git add output/sprint_reports/wave-3-land-and-polish.md
git commit -m "wave 3: land + polish + verify report"
git push origin master
```

---

## Decision authority

Autonomous on:
- All conflict resolution choices that follow the rules in §2.3
- Whether a surface needs polish (apply Phase 4 audit threshold)
- Polish-fix scope (head/nav chrome, module class application, byte-count threshold)
- Subcommand name fallbacks if the documented name differs from the registered name
- Skipping IN PROGRESS branches and noting them

Stop and flag only on:
- Two Wave 3 sprints registered the same CLI subcommand name (structural bug)
- A migration assumes schema state another migration produces with conflict (data-integrity issue)
- A Wave 3 sprint report flags one of the four canonical hard-blocker conditions
- Polish work for a single surface exceeds 30 minutes of edits (leave as TODO)
- The four canonical hard-blocker conditions

---

## Report back with

1. Phase 1 audit table — which sprints DONE / IN PROGRESS / MISSING
2. Phase 2 merge results per sprint — conflicts encountered + resolutions
3. Phase 3 render results per surface — success/error
4. Phase 4 visual audit table per Wave 3 page
5. Phase 5 polish fixes applied — before/after
6. Phase 6 voice validator sweep result
7. Token usage by model
8. Files touched
9. Final master SHA pushed
10. IN PROGRESS branches list (if any) — what to do with them
11. Quality concerns
12. Confirmation that `CLAUDE_CODE_FIRST_LIVE_CYCLE_AND_GO_LIVE.md` is the next sprint to fire

Session complete after the report pushes to master.
