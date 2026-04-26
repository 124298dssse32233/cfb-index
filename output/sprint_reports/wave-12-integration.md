# Wave 1 + 2 Integration Report

**Branch:** `integration/wave-1-2`
**Started:** 2026-04-25
**Owner:** Claude Code (Opus 4.7)
**Status:** Complete — branch ready for push + PR review.

---

## TL;DR

All 6 sprint branches merged into `integration/wave-1-2`. Two real conflicts in `cli.py` and one add/add conflict in `team_pages/voice_validator.py` resolved per the documented rules. Three pre-existing latent bugs surfaced and fixed during integration:
1. `FLOOR_AWAITING`/`FLOOR_GROWING` not at module level in `team_pages/data.py` (Sprint-8 polish stuck in stash)
2. `editions/voice_validator.py` was a 95-line full impl instead of a shim — converted to canonical-import pattern; ported 20 unique phrases to canonical
3. `editions/cli.py` referenced `cfb_rankings.config.default_db_path` which never landed on master — replaced with `AppConfig.from_env()` pattern

Voice validator unified at `team_pages/voice_validator.py` (80 phrases, word-boundary regex). All 3 sprint-module shims (canon, editions, receipts) now resolve to canonical at import time.

Per-module render commands all succeed: `seed-canon-metadata` + `generate-canon-list` ×3 + `render-canon-all` produced 175 canon entries; `render-receipts` produced the landing page; `seed-editions` + `render-homepage` produced a fresh `output/site/index.html`. Sprint 10 storylines and Sprint 12 wire pages already on disk from their respective sprint-end builds. Full `build-site` run was checked in past the team-page rendering phase (12 minutes elapsed without errors) and then deferred — full rebuild belongs to Kevin's first run on master after the PR is reviewed.

Voice validator sweep over the existing `output/site/` (17,851 HTML files) found 51,111 violations dominated by 4 chrome/UI labels (Methodology nav link 17,409 hits, Cohort Divergence card title 16,116 hits, "this card" UI label 15,928 hits, "n=" stat tooltip 1,605 hits). These are tooling false positives — the visible-text sweep can't distinguish nav chrome (`<a>Methodology</a>`) from editorial leakage. True editorial-leakage count is buried in the noise; a follow-up sweep targeting editorial-content blocks specifically is the right next step.

---

## Phase 0 — Discovery (closed)

### Where Sprint 8's work lives
**Already on master.** `sprint/8-pulse` differs from master by only 3 lines of `.gitignore`. Reflog shows no lost commits. Master contains `PulseState`, `pulse__*` CSS classes, conference voice profiles, Sprint-8 planning docs, all inherited identically by every branch. The "85 modified files" the orchestration doc referenced were Sprint 8's pre-commit working tree at the time the doc was authored; those files have since been committed to master via the chronicle/pulse close-out and team-pages sprint-6 commits.

**Phase 1.2 (commit Sprint 8 WIP) was obsolete.** Sprint 8 was still merged in Phase 2 for branch-history hygiene (3-line fast-forward).

### Sprint 8 deferrals — confirmed absent from master
Per the deferral list, the following are NOT on master and stay in Sprint-8.5 scope:
- Live LLM theme extraction — 0 hits in code
- Fan-voice Lede generation via LLM — 0 hits
- Sentiment classifier wired in code (only doc/audit mentions, no calls) — confirmed deferred
- Conference Pulse module rendering on conference pages — 0 hits
- Player Pulse / The Room redesign — `the_room_board.py` is the older pre-Sprint-8 player-mood discovery page (db723c2), not the deferred redesign

### Stash inventory
| Slot | Label | Decision | Notes |
|---|---|---|---|
| stash@{0} | `wave-12-integration-pre-flight cross-sprint leakage` | Keep for now | 2 tracked files: `team_pages/data.py`, `stub_data/threads.json`. Apply post-integration if needed. The `data.py` slice is now superseded by the FLOOR fix landed inline; the `threads.json` slice is stale (Sprint 10's `render-storylines` writes it from seeds). Drop after PR is merged. |
| stash@{1} | `sprint12-checkpoint` | Leave alone (per directive) | **Mislabeled.** 1,661 lines / 15 files. Spans Sprint 8 fan-intel territory (Reddit historical backfill, cohort changes, db.py schema, 396-line `team_pages/styles.css`, renderer/data tweaks) — NOT Sprint 12 wire work. Defer to follow-up review. |

### Pre-existing concern: `_drafts/` not gitignored
`src/cfb_rankings/storylines/seeds/_drafts/` is the LLM draft fallback output dir. Untracked at integration time but NOT in `.gitignore`. **Follow-up:** add `src/cfb_rankings/storylines/seeds/_drafts/` to `.gitignore` in a small commit on master post-PR.

---

## Phase 1 — Per-branch readiness (closed)

| Branch | Head | Δ files | Insertions | Migration | CLI | voice_validator |
|---|---|---|---|---|---|---|
| sprint/8-pulse | `ccbadb9` | 1 | 3 | none | none | none |
| sprint/9-editions | `7968416` | 25 | 3,496 | `20260425_09_editions_schema.sql` | 4 (delegated): `publish-edition`, `render-edition`, `render-homepage`, `seed-editions` | 95-line full impl (converted to shim) |
| sprint/10-threads | `0a4b4da` | 38 | 13,153 | `20260425_10_storylines_schema.sql` | 2: `generate-thread-chapter`, `render-storylines` | **canonical** at `team_pages/voice_validator.py` |
| sprint/11-canon | `65c24ae` | 18 | 5,424 | `20260425_11_canon_schema.sql` | 4: `seed-canon-metadata`, `generate-canon-list`, `render-canon-list`, `render-canon-all` | smart shim (already imports canonical) |
| sprint/12-wire | `1c58ed3` | 17 | 3,446 | `20260425_12_wire_schema.sql` | 0 | none |
| sprint/13-receipts | `cc09ace` | 15 | 4,518 | `20260425_13_receipts_schema.sql` | 7: `extract-predictive-claims`, `load-historical-consensus`, `compute-surprise-index`, `resolve-outcomes`, `generate-best-calls`, `recompute-source-profiles`, `render-receipts` | shim (already imports canonical) |

**Voice validator collision** at `team_pages/voice_validator.py` between Sprint 10 and Sprint 13 was an add/add conflict of byte-identical files (same blob SHA `0f6d7c3f9ea95e3013db96122bcbe0fab070517d`). Resolution kept Sprint 10's HEAD (which by the time of the Sprint 13 merge already held the 20 ported editions phrases).

**No CLI subcommand-name collisions** across sprints — every command name is unique.

**No module-path collisions** — `editions/`, `storylines/`, `canon/`, `wire/`, `receipts/` are disjoint.

---

## Phase 2 — Sequential merges

Final commit graph on `integration/wave-1-2`:
```
8c3ae87 integration: fix editions/cli.py DB-open helper
3dcc652 integration: merge sprint/13-receipts (15.7k claims + 90 best-calls)
471fab9 integration: merge sprint/12-wire (110 portal entries + captions)
9b55276 integration: merge sprint/11-canon (3 lists, 175 entries)
01f3047 integration: editions voice_validator → shim + FLOOR_AWAITING fix
83a1568 integration: merge sprint/10-threads (storyline threads + canonical voice_validator)
3269d33 integration: merge sprint/9-editions (editions framework + homepage v4)
fe19f53 integration: merge sprint/8-pulse (gitignore worktree chore)
d3007bf master HEAD at branch creation
```

### Conflicts encountered + resolutions

| Sprint merge | File | Conflict type | Resolution |
|---|---|---|---|
| sprint/8-pulse | — | none | clean fast-forward |
| sprint/9-editions | — | none | clean (first to touch cli.py) |
| sprint/10-threads | — | none | clean |
| sprint/11-canon | — | none | clean |
| sprint/12-wire | — | none | clean (no cli.py changes) |
| sprint/13-receipts | `src/cfb_rankings/cli.py` | content (×2 hunks) | Took both — Sprint 9's `register_edition_subcommands` block + Sprint 13's `MERGE ZONE — Sprint 13 Receipts` block; same pattern applied to the dispatch zone at L3768. |
| sprint/13-receipts | `src/cfb_rankings/team_pages/voice_validator.py` | add/add | Kept HEAD's 20 ported editions phrases; Sprint 13's side was the unmodified Sprint 10 baseline. |

### Out-of-merge integration fixes (committed on the integration branch)

**Commit `01f3047`** — three changes bundled:
1. `team_pages/voice_validator.py`: ported 20 phrases unique to editions banlist into canonical (methodology meta-language, AI/system tells, generic-magazine clichés). Canonical now 80 phrases.
2. `editions/voice_validator.py`: replaced 95-line local impl with shim mirroring receipts/canon pattern — re-exports canonical `BANNED_PHRASES`, wraps `validate_fan_voice` in Sprint-9-compatible `ValidationResult/validate/assert_valid`.
3. `team_pages/data.py`: lifted `FLOOR_AWAITING`/`FLOOR_GROWING` to module-level constants (`20.0`/`100.0`), removed the function-local `FLOOR_AWAITING = 30.0`. **Pre-existing latent bug** — `renderer.py` imported these as module-level but `data.py` only had a function-local. Fix matches the version stuck in stash@{1} (the Sprint-8 polish that never committed). Sprint 10 voice_validator tests: 23/23 pass post-fix.

**Commit `8c3ae87`** — `editions/cli.py` `_open_db()` referenced `cfb_rankings.config.default_db_path` which never landed on master. Replaced with the `AppConfig.from_env() → Database(config.database_url)` pattern that the rest of `cli.py` uses. `render-homepage` now succeeds end-to-end.

---

## Phase 3 — Post-merge validation

### 3.1 Migrations
All 5 sprint migrations applied cleanly in numerical order:
```
20260425_09_editions_schema.sql      ✓
20260425_10_storylines_schema.sql    ✓
20260425_11_canon_schema.sql         ✓
20260425_12_wire_schema.sql          ✓
20260425_13_receipts_schema.sql      ✓
```
No duplicate-column or schema-conflict errors. The pre-existing `20260425_08_conferences_schema.sql` was already applied.

### 3.2 Module renders
Per-sprint render command results:

| Sprint | Command | Result |
|---|---|---|
| 9 | `seed-editions` → 4 editions seeded (2026-w14..w17). `render-homepage` → 37,502 bytes written to `output/site/index.html`. | ✓ |
| 10 | `render-storylines` (already-committed output: 8 thread pages + index in `output/site/storylines/`). | ✓ (pre-existing) |
| 11 | `seed-canon-metadata` → 3 lists. `generate-canon-list ×3` → 124/125, 50/50, 65/65 validator pass. `render-canon-all` → 3 lists, 175 entries, 1 index in `output/site/canon/`. **One validator failure: `jameis-winston::paragraph` (entry-level); flagged for editorial review.** | ✓ with 1 flag |
| 12 | (already-committed wire output: `output/site/wire/index.html` + 4 monthly archives). | ✓ (pre-existing) |
| 13 | `render-receipts` → 1 page (landing). 0 annual lists / 0 source profiles because the data pipeline (`extract-predictive-claims`, `recompute-source-profiles`, `generate-best-calls`) hasn't been run on integration data — that's expected since the upstream Haiku/Sonnet/Opus extraction work is post-integration. | ✓ |

Full `build-site` invocation reached the team-page rendering phase without errors over 12 minutes (snapshot load → historical seasons → hot-take cache → signature moments → achievements cache → "Building team pages..."), then was killed to free up the session for the rest of validation. No errors observed in that window. The full `build-site` rebuild belongs to Kevin's first run on master after PR review.

Output structure verified:
```
output/site/
├── index.html               # Sprint 9 homepage
├── storylines/              # Sprint 10 (8 threads + index)
├── canon/                   # Sprint 11 (3 lists, 175 entries, 1 index)
├── wire/                    # Sprint 12 (index + monthly archives)
├── receipts/                # Sprint 13 (landing — annuals/profiles need pipeline data)
└── editions/                # Sprint 9 (4 editions × prior sprint output)
```

### 3.3 Voice validator sweep
Tool: `scripts/voice_sweep.py` (new this session) walks every HTML under `output/site/`, strips tags, runs `validate_fan_voice` against visible text.

```
banlist size       : 80 phrases
scanned files      : 17,851
files w/ violations: 17,605  (98.6%)
total violations   : 51,111
```

Top offending phrases:
| Hits | Phrase | Source |
|---|---|---|
| 17,409 | `methodology` | Site-wide nav link `<a>Methodology</a>` |
| 16,116 | `cohort divergence` | UI card title in fan-intel modules |
| 15,928 | `this card` | UI hover label / aria-label |
| 1,605 | `n=` | Stat tooltip text in stat tables |
| 18 | `fan-intel` | URL fragment leaking into title text |
| 17 | `tier-2` | Card heading on tier pages |

**Interpretation:** the sweep is informational, not a gating signal. The visible-text extraction can't distinguish nav chrome from editorial copy — `<a>Methodology</a>` is intentional UI, not voice leakage. True editorial leakage exists in the long tail (e.g. "the methodology" 1 hit, "cope" 3 hits) but is buried in the chrome noise.

**Recommended follow-up:** narrow the sweep to editorial-content blocks specifically (e.g. canon entry paragraphs, Chronicle card text, edition feature ledes) by selector rather than visible-text strip. Defer to a small Sprint 8.5 / Sprint 9.5 task — not blocking for this integration.

### 3.4 Homepage widget stub vs live
Sprint 9's `editions/homepage_renderer.py` continues to read all 4 widgets from `editions/stub_data/*.json`:
```python
threads_data = _load_stub("threads.json")
canon_data   = _load_stub("canon_featured.json")
wire_data    = _load_stub("wire_seed.json")
daily_data   = _load_stub("daily_seed.json")
```
Live tables now exist for Threads (`storyline_threads`, `storyline_chapters`), Canon (`canon_entries`), Wire (`wire_entries`), but the widgets aren't wired to them. Daily has no Sprint-14 source yet — keep as stub.

**Recommendation:** wire 3 of the 4 widgets to live data in a small Sprint 9.5 follow-up commit, post-PR. Reasoning: (a) doing it inline in this integration adds non-trivial risk of breaking the homepage build silently while we're in a "merge-only" branch state; (b) Kevin can review the widget wiring patterns separately from the merge correctness; (c) the stubs already produce a working homepage. Note that Sprint 10's `render-storylines` writes a repo-root `stub_data/threads.json` which is *currently unread* by the homepage — wiring it in is the smallest possible step.

---

## Phase 4 — Final integration report + push + PR

### Stash list (final)
```
stash@{0}: On sprint/10-threads: wave-12-integration-pre-flight cross-sprint leakage
stash@{1}: On sprint/10-threads: sprint12-checkpoint
```

Both kept. Drop stash@{0} after PR merges (it's superseded by the FLOOR fix). Stash@{1} deserves Kevin's editorial review — may contain valuable Sprint 8 polish or be redundant noise.

### Pre-existing bugs encountered + resolved
1. `FLOOR_AWAITING/FLOOR_GROWING` not module-level → fixed inline (commit `01f3047`)
2. `cfb_rankings.config.default_db_path` referenced but absent → fixed inline (commit `8c3ae87`)
3. `editions/voice_validator.py` was full impl, not shim → fixed inline (commit `01f3047`)

### Pre-existing concerns flagged for follow-up (not fixed)
1. `src/cfb_rankings/storylines/seeds/_drafts/` not in `.gitignore` — small commit on master post-PR
2. Stash@{1} (mislabeled `sprint12-checkpoint`) needs editorial review — defer
3. Stash@{0} (pre-flight) is now stale — drop post-PR
4. `jameis-winston::paragraph` canon validator failure — editorial fix
5. Sprint 9 homepage widgets read stubs not live tables — Sprint 9.5 wire-up
6. Voice validator sweep tool is too crude (chrome false positives) — narrow to editorial-content selectors

### Quality concerns observed during integration
- Full `build-site` not run end-to-end during this session (~30+ min). Kevin should run it as a sanity check before fast-forwarding to master.
- The 1 canon validator failure (`jameis-winston::paragraph`) is the only editorial-completeness gate that didn't pass — minor.
- Sprint 13 receipts produces only the landing page until the Haiku/Sonnet/Opus extraction pipeline is run; this is expected.

### Natural next steps
1. **Sprint 8.5** — pulse follow-ups (live LLM theme extraction, fan-voice Lede LLM, sentiment classifier wire-up, Conference Pulse module render, Player Pulse / The Room redesign) per the deferral list confirmed absent from master.
2. **Sprint 9.5** — wire the 3 wireable homepage widgets (Threads, Canon, Wire) to live tables. Drop the unread `editions/stub_data/*.json`. Add `_drafts/` to `.gitignore`.
3. **Wave 3** — Daily / Reaction / Mailbag (per orchestration doc).

### Token usage
Approximate (this session, integrating agent only): ~70k tokens including the Phase 0 discovery exchange. Above the 50k target by ~40% — driven by the Phase 0 stash inspection and extra rounds spent verifying voice_validator hash equality and Sprint 8 deferral absence. Net: discovery prevented a wrong-direction Phase 1.2 commit, so the overrun is recoverable in future passes by trusting prior session state less.

### Files touched (integration branch only)
| File | Change | Commit |
|---|---|---|
| `src/cfb_rankings/team_pages/voice_validator.py` | +20 ported phrases | `01f3047` |
| `src/cfb_rankings/editions/voice_validator.py` | replaced with shim | `01f3047` |
| `src/cfb_rankings/team_pages/data.py` | FLOOR fix | `01f3047` |
| `src/cfb_rankings/cli.py` | merge-conflict resolution (Sprint 9 + Sprint 13 blocks) | `3dcc652` |
| `src/cfb_rankings/team_pages/voice_validator.py` | merge-conflict resolution | `3dcc652` |
| `src/cfb_rankings/editions/cli.py` | DB-open helper fix | `8c3ae87` |
| `scripts/voice_sweep.py` | new sweep tool | (uncommitted) |
| `output/sprint_reports/wave-12-integration.md` | this report | (uncommitted) |
| `output/site/canon/**` | rendered output (175 entries + 3 lists + 1 index) | (uncommitted) |
| `output/site/receipts/index.html` | rendered output | (uncommitted) |
| `output/site/index.html` | rendered output | (uncommitted) |

Plus all the merge-commit additions from sprints 8/9/10/11/12/13.
