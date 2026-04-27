# Wave 3 Land + Polish + Verify — Sprint Report

**Date:** 2026-04-26  
**Branch:** master  
**Model:** claude-sonnet-4-6 (100% Sonnet, 0% Opus)  
**Final master SHA:** 79015a9

---

## 1. Phase 1 Audit — Wave 3 Branch State

| Sprint | Branch | Status | Notes |
|--------|--------|--------|-------|
| 14 | sprint/14-daily | **DONE** | Completion commit `93c86bf`. 8 files. No sprint report file, but commit message is comprehensive completion summary. |
| 15 | sprint/15-reaction | **DONE** | Completion commit `0c76020`. Sprint report at `output/sprint_reports/sprint-15-reactions.md`. All phases ✅, voice validator passed. |
| 16 | sprint/16-mailbag | **DONE** | Completion commit `880b069`. 11 files. No sprint report file, but commit message documents all phases including voice-validator fixes. |

**IN PROGRESS branches:** None.  
**MISSING branches:** None.  
**Hard-blockers in any sprint report:** None.

*Note on sprint report files:* Sprints 14 and 16 did not write a separate `output/sprint_reports/sprint-N-*.md` file. Their commit messages serve as the completion record. Sprint 15 was exemplary — report was thorough with hard-blocker check, tuning notes, and judgment calls.

---

## 2. Phase 2 — Per-Branch Merge Results

### Sprint 14 — `sprint/14-daily`
- Rebase onto master: clean (1 commit, no conflicts)
- Merge: `git merge --ff-only` → `fdaa66c`
- Import check: ✅ `from cfb_rankings.daily import renderer`
- CLI check: `generate-daily`, `render-daily` registered at sprint-14 merge zone
- Pushed: `a63ff79..fdaa66c`

### Sprint 15 — `sprint/15-reaction`
- Rebase onto master: clean (1 commit, no conflicts)
- Merge: `git merge --ff-only` → `f02800b`
- Import check: ✅ `from cfb_rankings.reactions import renderer`
- CLI check: `reactions-check-triggers`, `generate-reaction`, `render-reactions`, `reactions-history` registered
- Migrations applied: `20260426_15_reactions.sql` ✅
- Pushed: `fdaa66c..f02800b`

### Sprint 16 — `sprint/16-mailbag`
- Rebase onto master: **CONFLICT in `src/cfb_rankings/cli.py`**
- **Conflict resolution:** Sprint 15 and 16 both modified cli.py (different merge zones). Conflicts were cosmetic — f-strings (HEAD/sprint-15 rebase) vs `.format()` strings (sprint-16 original). Took HEAD version (f-strings) throughout. One additional import (`list_answers_for_edition`) preserved from HEAD. No subcommand name collisions.
- Merge: `git merge --ff-only` → `79015a9`
- Import check: ✅ `from cfb_rankings.mailbag import renderer`
- CLI check: `mailbag-seed-submissions`, `mailbag-curate-submissions`, `mailbag-generate-answers`, `render-mailbag`, `mailbag-history` registered
- Pushed: `f02800b..79015a9`

### Migrations applied (all 3)
```
20260426_14_daily.sql    @ 2026-04-26 19:59:58  ✅
20260426_15_reactions.sql @ 2026-04-26 19:59:58  ✅
20260426_16_mailbag.sql   @ 2026-04-26 19:59:58  ✅
```

---

## 3. Phase 3 — Render Results

| Surface | Command | Result |
|---------|---------|--------|
| Daily (today) | `render-daily` | ✅ 2026-04-26 index + archive rendered |
| Daily (backfill) | `render-daily --date YYYY-MM-DD` × 5 | ✅ 2026-04-21 through 2026-04-25 re-rendered |
| Reactions | `render-reactions` | ✅ 3 stories + archive index |
| Mailbag seed | `mailbag-seed-submissions --n 5` | ✅ 5 seed rows planted (IDs 6–10) |
| Mailbag curate | `mailbag-curate-submissions --max 3` | ✅ edition=2026-w17 selected=3 rejected=2 |
| Mailbag generate | `mailbag-generate-answers` | ✅ answers=3 voice_passed=3 voice_failed=0 (offline-stub mode) |
| Mailbag render | `render-mailbag` | ✅ 1 edition page + index + archive + submit form |

**Output directories confirmed:**
- `output/site/daily/` — 6 edition dirs + index.html + archive.html
- `output/site/reactions/` — 3 story dirs + index.html
- `output/site/mailbag/` — 1 edition dir + index.html + archive.html + submit/

---

## 4. Phase 4 — Visual Audit (Pre-Fix)

All Wave 3 pages were **STUB** — no `<link rel="stylesheet">`, no design-token classes.

| Page | Status | css | token | bytes |
|------|--------|-----|-------|-------|
| daily/index.html | STUB | ✗ | ✗ | 6,889 |
| daily/archive.html | STUB | ✗ | ✗ | 1,809 |
| reactions/index.html | STUB | ✗ | ✗ | 4,715 |
| mailbag/index.html | STUB | ✗ | ✗ | 13,507 |
| mailbag/submit/index.html | STUB | ✗ | ✗ | 9,496 |
| daily/2026-04-21/index.html | STUB | ✗ | ✗ | 10,157 |
| reactions/*/index.html (×2) | STUB | ✗ | ✗ | 7,880–8,202 |

All pages used elaborate inline `<style>` blocks (not unstyled) but lacked the shared CSS link and module-namespaced classes.

---

## 5. Phase 5 — Polish Fixes Applied

Same pattern as The Room (visual-audit-001): each surface shipped without the shared CSS link.

### Fix 1: Daily (`src/cfb_rankings/daily/templates/daily.html`)
- Added `<link rel="stylesheet" href="/assets/cfb-index.93e59647a6bd.css">` to `<head>`
- Added `class="daily__page"` to `<body>`
- Added `class="daily__nav"` to `<nav class="site-nav">`

### Fix 2: Daily archive (`src/cfb_rankings/daily/renderer.py`)
- Added CSS link to `_render_archive_index()` inline template
- Added `class="daily__archive"` to `<body>`
- Added minimal breadcrumb nav

### Fix 3: Reactions (`src/cfb_rankings/reactions/renderer.py`)
- Added CSS link to `_page_head()`
- Added `class="reaction__page"` to `<body>`
- Added `reaction__nav` inline nav with links to CFB Index, Reaction Stories, Wire, Storylines
- Fixed voice-validator violation in archive dek (see Phase 6)

### Fix 4: Mailbag (`src/cfb_rankings/mailbag/renderer.py`)
- Added CSS link to `_full_page_html()`
- Added `class="mailbag__page"` to `<body>`
- (Mailbag already had `_nav_html()`, `_chrome_html()`, `_brand_row_html()` implemented)

### Visual Audit (Post-Fix)

| Page | Status | css | token | bytes |
|------|--------|-----|-------|-------|
| daily/index.html | ✅ OK | ✓ | ✓ | 10,102 |
| daily/archive.html | ✅ OK | ✓ | ✓ | 2,048 (short table — expected) |
| daily/2026-04-21–25/index.html | ✅ OK | ✓ | ✓ | 10,098–10,258 |
| daily/2026-04-26/index.html | ✅ OK | ✓ | ✓ | 6,986 (no takes yet) |
| reactions/index.html | ✅ OK | ✓ | ✓ | 5,315 |
| reactions/*/index.html (×3) | ✅ OK | ✓ | ✓ | 8,480–8,802 |
| mailbag/index.html | ✅ OK | ✓ | ✓ | 13,595 |
| mailbag/2026-w17/index.html | ✅ OK | ✓ | ✓ | 13,595 |
| mailbag/submit/index.html | ✅ OK | ✓ | ✓ | 9,584 |
| mailbag/archive.html | ✅ OK | ✓ | ✓ | 8,391 |

**0 stub-styled pages remaining.**

---

## 6. Phase 6 — Voice Validator Sweep

**Wave 3 pages: 0 violations.**

All 8 Wave 3 sampled pages passed:
- `output/site/daily/index.html` ✅
- `output/site/daily/2026-04-21/index.html` ✅
- `output/site/daily/2026-04-22/index.html` ✅
- `output/site/reactions/index.html` ✅
- `output/site/reactions/alabama-rb-khalifa-keith-app-state/index.html` ✅
- `output/site/reactions/northwestern-qb-marchiol-from-wvu/index.html` ✅
- `output/site/mailbag/index.html` ✅
- `output/site/mailbag/2026-w17/index.html` ✅

**One Wave 3 fix required:** `reactions/index.html` archive dek used "cohort divergence" (banned technical term). Fixed in `renderer.py` to "how the three fan cohorts split / diverged."

**Pre-existing violations (out of Wave 3 scope):**

| File | Phrases | Source |
|------|---------|--------|
| teams/notre-dame.html | `fan-intel`, `tier-2`, `n=`, `sample growing` | Team-page module, pre-existing |
| teams/alabama.html | `fan-intel`, `tier-2` | Team-page module, pre-existing |
| index.html, conferences/fbs-sec.html, players/the-room.html | `methodology` | Shared nav link text — chrome false positive |

The "methodology" violations are in the shared topbar nav (`<a href="../methodology/fan-intelligence.html">Methodology</a>`). This is a nav label, not editorial content — chrome false positive per the plan's exclusion.

---

## 7. Token Usage by Model

| Model | Role | Approx. usage |
|-------|------|---------------|
| claude-sonnet-4-6 | All code, conflict resolution, polish, report | ~100% |
| claude-opus-4-7 | None | 0% |
| claude-haiku-4-5 | None | 0% |

**Opus <15%**: ✅ (0%)

---

## 8. Files Touched

**Merge additions (Sprint 14):**
- `.github/workflows/the-daily-06am-et.yml` (created, if:false guarded)
- `migrations/20260426_14_daily.sql`
- `src/cfb_rankings/daily/__init__.py`
- `src/cfb_rankings/daily/data.py`
- `src/cfb_rankings/daily/renderer.py`
- `src/cfb_rankings/daily/selector.py`
- `src/cfb_rankings/daily/synthesizer.py`
- `src/cfb_rankings/daily/templates/daily.html`

**Merge additions (Sprint 15):**
- `migrations/20260426_15_reactions.sql`
- `output/site/reactions/index.html` (pre-rendered by sprint 15)
- `output/site/reactions/*/index.html` (3 stories, pre-rendered)
- `output/sprint_reports/sprint-15-reactions.md`
- `src/cfb_rankings/cli.py` (+352 lines — reactions CLI zone)
- `src/cfb_rankings/reactions/__init__.py`
- `src/cfb_rankings/reactions/cohort_divergence.py`
- `src/cfb_rankings/reactions/data.py`
- `src/cfb_rankings/reactions/renderer.py`
- `src/cfb_rankings/reactions/synthesizer.py`
- `src/cfb_rankings/reactions/triggers.py`

**Merge additions (Sprint 16):**
- `.github/workflows/mailbag-friday-09am-et.yml` (created, if:false guarded)
- `migrations/20260426_16_mailbag.sql`
- `src/cfb_rankings/cli.py` (+125 lines conflict-resolved — mailbag CLI zone)
- `src/cfb_rankings/mailbag/__init__.py`
- `src/cfb_rankings/mailbag/curator.py`
- `src/cfb_rankings/mailbag/data.py`
- `src/cfb_rankings/mailbag/renderer.py`
- `src/cfb_rankings/mailbag/submissions.py`
- `src/cfb_rankings/mailbag/synthesizer.py`
- `src/cfb_rankings/mailbag/templates/mailbag.html.j2` (Jinja2 reference stub)
- `src/cfb_rankings/mailbag/templates/submit.html.j2` (Jinja2 reference stub)

**Polish edits (this session):**
- `src/cfb_rankings/daily/templates/daily.html` — CSS link, `daily__page` class
- `src/cfb_rankings/daily/renderer.py` — archive CSS link, `daily__archive` class
- `src/cfb_rankings/reactions/renderer.py` — CSS link, `reaction__page` class, nav, dek voice fix
- `src/cfb_rankings/mailbag/renderer.py` — CSS link, `mailbag__page` class

**Generated outputs (rendered this session):**
- `output/site/daily/` (6 edition dirs, index, archive)
- `output/site/reactions/` (3 story dirs, index)
- `output/site/mailbag/` (1 edition dir, index, archive, submit)
- `output/site/teams/` (17 profiled + 203 historical season pages)
- `output/site/conferences/` (11 conference pulse pages)
- `output/site/storylines/` (8 thread pages + index)
- `output/site/canon/` (3 lists, 175 entries, 1 index)
- `output/site/players/the-room.html`
- `output/site/index.html`

---

## 9. Quality Concerns

**Sprint 14 (Daily):**
- No sprint report file written — commit message serves as record
- Daily CLI has no `cli.py` merge zone comment (the zone marker is present but no `# sprint-14` header-style comment). Works correctly.
- `render-daily` always re-renders the current date AND writes `index.html` and `archive.html`. Re-rendering old dates updates index.html to that date as "current" — may confuse index.html purpose.
- The 2026-04-26 edition has no takes in DB (`generate-daily` was not run for today, only for backfill). `render-daily` renders an empty "No takes available for this edition." page.

**Sprint 15 (Reactions):**
- Trigger thresholds cannot fire organically — all 110 wire entries have `fan_intel_velocity_spike = 70`, below Rule 1 (90) and Rule 2 (75) thresholds. All content is force-triggered / offline stub.
- Offline stub headlines use the same template across all 3 stories.

**Sprint 16 (Mailbag):**
- Jinja2 `.j2` template files are reference stubs only — the renderer uses inline Python strings. The `.j2` files are not executed.
- `mailbag-history` imports `list_answers_for_edition` but the command body doesn't use it (it only lists editions). The import is harmless but unused.

**Pre-existing (out of scope):**
- Team-page voice-validator violations: `fan-intel`, `tier-2`, `n=`, `sample growing` in team pages
- Shared nav has `methodology` link text that triggers the validator — needs to be renamed to "The Model" across all nav-generating code

---

## 10. IN PROGRESS Branches

None. All three Wave 3 sprints were DONE and merged.

---

## 11. Natural Next

**Fire `CLAUDE_CODE_FIRST_LIVE_CYCLE_AND_GO_LIVE.md`** to:
- Flip the `if: false` guards on `.github/workflows/the-daily-06am-et.yml` and `mailbag-friday-09am-et.yml`
- Wire the Sprint 15 reactions cron hook into Sprint 14's daily workflow YAML
- Fix the pre-existing nav "Methodology" label → "The Model" across reporting.py nav tuples
- Address team-page voice-validator violations (`fan-intel`, `tier-2`, `n=`)
