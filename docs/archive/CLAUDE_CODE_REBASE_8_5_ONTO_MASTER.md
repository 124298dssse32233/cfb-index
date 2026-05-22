# Claude Code — Rebase sprint/8.5-pulse-followups onto Master

> **Inherits from `CLAUDE_CODE_AUTONOMY_AND_TOKEN_CONTRACT.md`.** Single sequential session. Surgical conflict resolution + rebase + push + PR.

**Recommended model: Sonnet 4.6.**

**Target budget: ~10k tokens. Runtime: 20–40 min.**

---

## What this sprint does

Sprint 8.5 was branched from master BEFORE the Wave 1+2 integration was merged. Now master has Wave 1+2's commits, and sprint/8.5-pulse-followups needs to rebase onto the new master to integrate cleanly.

Conflicts are expected in 4 files (voice_validator.py, renderer.py, reporting.py, cli.py). This sprint resolves them per pre-defined rules, force-pushes the rebased branch, and opens the PR.

**File ownership:** rebase-resolution edits to `team_pages/voice_validator.py`, `team_pages/renderer.py`, `reporting.py`, `cli.py`. No other files should need editing — the rest of Sprint 8.5's work is in net-new files (`pulse_state.py`, `pulse_themes.py`, `pulse_lede.py`, `sentiment_classifier.py`, `the_room_renderer.py`, `profiles/_conferences/*.md`) which won't conflict because they didn't exist on master prior.

---

## Phase 1 — Pre-rebase audit (5 min)

### 1.1 Confirm state

```
git fetch origin
git checkout master
git pull origin master
git log --oneline -5  # confirm Wave 1+2 integration commits are present
git checkout sprint/8.5-pulse-followups
git log --oneline -5  # confirm Sprint 8.5 commit fabf0fc is HEAD
git log master..HEAD  # commits unique to 8.5
```

If anything looks unexpected (e.g., master doesn't have integration commits yet, or 8.5 has commits other than the ones from the sprint report), stop and flag.

### 1.2 Save the current 8.5 HEAD as a safety reference

```
git tag sprint/8.5-pre-rebase-backup
```

So if the rebase goes sideways, we can return to this point.

---

## Phase 2 — Rebase + conflict resolution (15-30 min)

### 2.1 Start the rebase

```
git rebase master
```

Expect conflicts on 1-4 files across the rebased commits. Resolve per rules below, then `git rebase --continue` after each conflict.

### 2.2 Conflict resolution rules

#### `team_pages/voice_validator.py`

- **Take union of all BANNED_PHRASES from both branches.** Master's version (post-integration) has Sprint 10's word-boundary regex + Sprint 13's expanded list. Sprint 8.5 may have added more phrases as it surfaced banned-phrase leakage during Lede + theme generation.
- Final version: master's `_build_pattern()` regex implementation + the union of all banned phrases (~60-70 entries expected).
- Re-run any voice_validator tests after resolution to confirm the unified version still passes (`23/23` from Sprint 10 + any 8.5 tests).

#### `team_pages/renderer.py`

- **8.5 wins on PulseState integration** — the parts of renderer.py that call `build_pulse_state()` and route to the new modules.
- **Master (post-integration) wins on the rest** — anything Sprint 9 or earlier polished.
- If both branches add functions with similar names but different signatures, keep both and rename the 8.5 version to be specific (e.g., `_render_pulse_v2_module` if there's a conflict with `_render_pulse_module`).

#### `reporting.py`

- **Keep ALL delegation hooks** — Sprint 9 added the homepage hook, Sprint 8.5 added Conference Pulse + Player Pulse hooks. They're disjoint code blocks operating on different page types.
- The hooks are simple guarded if-statements that delegate when active content exists for the entity. Stack them; don't merge.
- Per CLAUDE.md, no other reporting.py edits are allowed. If conflict surfaces something outside the documented hooks, flag and stop.

#### `cli.py`

- **Keep all subparser registrations** at the documented merge zone (line ~750-1020), alphabetically ordered. Sprint 8.5 added registrations for `compute-conference-pulse`, `render-conferences-pulse`, `render-the-room`, possibly others.
- Final order at merge zone:
  ```
  # ---- sprint 8: pulse ----
  # ---- sprint 8.5: pulse follow-ups ----
  # ---- sprint 9: editions ----
  # ---- sprint 10: storylines ----
  # ---- sprint 11: canon ----
  # ---- sprint 12: wire ----
  # ---- sprint 13: receipts ----
  ```
- Each marker block contains its sprint's subparser registrations. If two sprints registered the same subcommand name, that's a structural bug — flag.

### 2.3 Confirm clean state after rebase

```
git status  # should be clean
git log --oneline -10  # confirm Sprint 8.5's commits sit on top of master's commits
```

---

## Phase 3 — Validation (5-10 min)

### 3.1 Import + render smoke test

```
python -c "from cfb_rankings.team_pages.pulse_state import build_pulse_state; print('OK')"
python -c "from cfb_rankings.team_pages.pulse_themes import extract_theme_candidates; print('OK')"
python -c "from cfb_rankings.team_pages.pulse_lede import generate_lede; print('OK')"
python -c "from cfb_rankings.team_pages.sentiment_classifier import classify_sentiment_batch; print('OK')"
python -c "from cfb_rankings.team_pages.the_room_renderer import render_the_room; print('OK')"
```

If any imports fail post-rebase, fix the import paths (likely a shared module that moved).

### 3.2 Voice validator test

Run any test files that exist for voice_validator:
```
python -m pytest src/cfb_rankings/team_pages/test_voice_validator.py -v
python -m pytest src/cfb_rankings/storylines/test_chapter_authoring.py -v
```

Expected: all pass post-rebase.

### 3.3 Render one team page + one conference page

```
python manage.py render-team-pages --slug notre-dame
python manage.py render-conferences-pulse --slug fbs-sec
```

Verify both render without errors. Quick visual check on the rendered HTML:
- Notre Dame Pulse module shows live theme cards + Lede (8.5's work)
- SEC conference page shows Pulse module section (8.5's work)
- No regression on Sprint 9 / 10 / 11 / 12 / 13 surfaces (homepage still renders, storylines pages still render, etc.)

If render errors, debug them inline. Keep going.

---

## Phase 4 — Force-push + PR (5 min)

### 4.1 Force-push the rebased branch

```
git push --force-with-lease origin sprint/8.5-pulse-followups
```

`--force-with-lease` (not bare `--force`) ensures we don't overwrite any concurrent push from elsewhere.

### 4.2 Open the PR

PR creation URL printed by the push. Or visit:
`https://github.com/124298dssse32233/cfb-index/pull/new/sprint/8.5-pulse-followups`

PR body — write to `output/sprint_reports/sprint-8-5-rebase-PR-BODY.md`:

```markdown
# Sprint 8.5 — Pulse Follow-Ups (Rebased onto master after Wave 1+2 integration)

## What landed
- Live LLM theme extraction for top 10 programs + top 5 conferences
- Fan-voice Lede generation via llm_runtime (3 Opus blue-blood, 12 Sonnet rest)
- Player target sentiment classification (19,063 / 19,109 = 99.8%)
- 8 missing conference voice profiles authored
- Conference Pulse module rendering on /conferences/* pages
- The Room v2 (Player Pulse) on top-15 high-traffic players
- 5 net-new modules in team_pages/

## Rebase notes
Branch was rebased onto master post-Wave-1+2-integration.
Conflicts resolved in: voice_validator.py (union of phrases), renderer.py (8.5 wins on PulseState), reporting.py (additive hooks), cli.py (alphabetically ordered merge zone).

## Voice validator final state
~60-70 banned phrases. Word-boundary regex from Sprint 10. Tests passing.

## Spot-check
- Notre Dame, Alabama, Ohio State team pages render Pulse v2 with live themes + ledes
- SEC, Big Ten, ACC, Big 12, AAC conference pages render Pulse module
- Top 15 player pages render The Room v2

## Token usage
Sprint 8.5 main: ~50-55k tokens (rebase: ~10k additional)

Ready for fast-forward merge to master.
```

Open the PR via UI, paste body. Don't auto-merge — Kevin reviews + merges.

---

## Decision authority

Autonomous on: conflict resolution choices that follow the rules above; rebase commit message wording; minor refactors needed to make imports work post-rebase; small test fixes that surface during validation.

Stop and flag only on:
- Two sprints registered the same CLI subcommand name (structural bug)
- A code block in reporting.py outside the documented hook locations is conflicting (CLAUDE.md violation)
- A test that was passing on either branch fails post-rebase and the fix isn't obvious within 5 minutes

---

## Report back with

1. Pre-rebase state confirmed (master HEAD + 8.5 HEAD)
2. Conflicts encountered + resolution per file (one paragraph per conflicted file)
3. Validation results (imports + tests + sample renders)
4. Force-push confirmation + final HEAD SHA on remote
5. PR URL opened
6. Quality concerns (if any banned-phrase leakage emerged during the unified validator pass)
7. Token usage

Session complete after PR opens. Kevin merges via UI to master.
