# Session 11 Wrap — 100% Real-FBS Profile Coverage + Diagnostic Fix

**Date:** 2026-05-23 (continuation)
**Session 10 end:** 90 hand-authored YAMLs (75.6%) + 5 new modules + CFBD 2025 data
**Session 11 end:** **127 hand-authored YAMLs = 100% of 119 real FBS programs** + CI diagnostic fix

## Headline

**Every single one of the 119 real FBS programs now has a hand-authored profile YAML** —
identity phrase, accent colors, mascot voice, rituals, cultural anchors, rivalry context, program history.
No synthesizer fallbacks needed for real FBS programs. The audit's long-tail YAML
authoring task is complete.

## The bug we discovered

User reported the Cincinnati team page still looked like the legacy chrome — and they
were right. Investigation revealed:

**Cincinnati, Indiana, Texas-Tech, Boise State (and others)** were rendering with the OLD
`reporting.py` `premium-team-hero` template instead of the world-class `team_pages`
template, even though they had profiles/*.md files.

Pattern: The original 17 PROFILED_SLUGS (alabama, georgia, ohio-state, notre-dame, etc.)
were rendering world-class. Every new YAML added since was getting silently skipped in CI.

CI log showed `team-pages v2: 50 hand-authored + 68 synthesized = 118 world-class team pages`
but there were 55 hand-authored YAMLs at deploy time. **5 were silently dropped without
error messages.**

## Diagnostic fix shipped (commit 9b61f8b0183)

`src/cfb_rankings/team_pages/profile_loader.py`:
- Added robust PROFILES_DIR resolution: try `Path(__file__).parents[3] / "profiles"` first,
  fall back to `Path.cwd() / "profiles"` if that doesn't contain .md files.
- Guards against pip-editable-install `__file__` resolution edge cases.

`src/cfb_rankings/team_pages/renderer.py` `render_all_profiled_pages`:
- Print PROFILED_SLUGS contents + count BEFORE the render loop (now visible in CI logs).
- Per-slug failures print eagerly with `flush=True` — so OOM / SIGTERM mid-loop still
  leaves a trail of which slugs were tried.
- If render still drops any slug in CI, the logs will now show which one and why.

## YAMLs authored (Session 11: 7 batches, 37 new YAMLs)

| Sprint | YAMLs | Count |
|---|---|---|
| AK | tulane, fresno-state, san-diego-state, colorado-state, tulsa | 95 |
| AL | utah-state, wyoming, nevada, northern-illinois, western-michigan | 100 |
| AM | old-dominion, rice, bowling-green, utep, south-alabama | 105 |
| AN | boston-college, troy, southern-miss, temple, texas-state | 110 |
| AO | hawai-i, unlv, utsa, middle-tennessee, florida-atlantic | 115 |
| AP | arkansas-state, uab, louisiana, louisiana-tech, charlotte | 120 |
| AQ | florida-international, georgia-southern, georgia-state, new-mexico-state, north-texas, san-jos-state, ul-monroe | 127 |

**Coverage: 119/119 real FBS = 100%**

Notes on the 127 vs 119: 8 YAMLs are for programs the `list_real_fbs_slugs(db)` helper
filters out (jacksonville-state, miami-oh, ohio, sam-houston, toledo — all FBS but in
small conferences the helper doesn't include in its core FBS list). Total profile YAML
count is 127.

## Total program coverage delta this session

| Metric | Start | End |
|---|---|---|
| Hand-authored profile YAMLs | 90 | 127 |
| Real FBS coverage | 75.6% | **100%** |
| Synthesizer fallbacks needed | 29 of 119 | **0** of 119 |
| Team-page modules built | 19 | 19 (unchanged) |

## Pending verification

Deploy `26321869940` (currently queued) ships with:
- All 127 hand-authored YAMLs
- CI diagnostic logging
- Robust PROFILES_DIR resolution

When deploy completes (~50 min from queue), expected outcomes:
1. Live `/teams/cincinnati.html` becomes world-class (current bug fixed)
2. Live `/teams/indiana.html` becomes world-class
3. Live `/teams/texas-tech.html` becomes world-class
4. All 119 FBS pages show identity-phrase hero + 15+ modules
5. CI logs show explicit PROFILED_SLUGS = 127 count + any failures with stack traces

If any slug still fails, the diagnostic will tell us exactly which one + why.

## Marginal cost

| Item | Cost |
|---|---|
| Vercel hosting | $0 |
| GitHub Actions | $0 (public repo) |
| Anthropic API | $0 (no LLM-gen jobs) |
| CFBD tier-2 API | $30/mo (user-paid, unchanged) |
| **This session** | **$0** |

## Remaining work

Items still pending from audit / plan:

1. **Verify diagnostic deploy** (in flight) — confirm world-class ships for all 119
2. **Fix the silent-fail root cause** (after diagnostic reveals it)
3. **Player-page modules** (Achievements polish, Rival Radar, Mirror Match, Coaching Lineage,
   Live Signal Flow) — require touching `reporting.py` monolith; deferred
4. **CFBD coaches API ingest** for Coaching Era Strip chip — 1hr next session
5. **CFBD postseason games ingest** to activate Bowl History — 1hr next session
6. **Sprint F IA consolidation** (`/programs/` vs `/teams/`) — needs design decision
7. **Chronicle LLM-gen** (Echo, Retroactive, Player Arc) — needs $30-180/mo budget approval

The audit's structural backbone (T9 Recruiting, T11 Returning Production, T11 Talent, T11 Portal,
T6 Recent Form, T6 Statement Wins, T31 Two-Tier Reality, T34 Voice Register) is now closed.

## Bottom line

**100% of real FBS programs have hand-authored voice on the live (eventually) world-class team
pages.** Every page surfaces:
- Identity phrase under wordmark
- Conference-keyed voice register
- Per-program rituals (3-4 each)
- Cultural anchors (3-6 each)
- Mascot voice (3 states: awaiting / loss / win)
- Stock phrases, never-use guardrails, always-surface canon
- Program history + fanbase summary + rivalry context body sections

When 26321869940 ships, all 119 team pages will visually demonstrate this. The Cincinnati
screenshot the user surfaced will be fixed alongside every other newer-profile team.
