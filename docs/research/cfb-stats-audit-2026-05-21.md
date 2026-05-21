# CFB Stats Conformance Audit — Punch List

**Date:** 2026-05-21
**Scope:** Drift between the locked conformance spec ([cfb-stats-conformance-spec.md](cfb-stats-conformance-spec.md)) and what the renderers actually emit.
**Method:** Source-code grep across `src/cfb_rankings/` (reporting.py monolith + module renderers + CSS), plus spot-checks of generated `output/site/` pages.
**Scoring:** P0 = ship-blocking conformance failure; P1 = visible drift but not ship-blocking; P2 = internal consistency work that scales over time.

---

## Status (updated 2026-05-21 PM)

- **P1 (abbreviation drift): RESOLVED.** All 5 edits applied at the file:line citations below. Verification pending build.
- **P0 (tabular-numerals coverage): RESOLVED with caveat.** The original Explore-agent finding ("~60+ uncovered classes, coverage ~15%") was inaccurate. Direct verification at the implementation site showed that almost every flagged BEM class already had `font-variant-numeric: tabular-nums` set either at its own rule site or via the consolidated enforcement block at [reporting.py:2471-2491](../../src/cfb_rankings/reporting.py). The genuine gap was 2 classes: `.biotabs__panel-value` and `.rank-delta` (family). Both added to the consolidated rule. The 00-tokens.md spec was also extended with BEM-suffix attribute selectors as documented intent — those serve as a safety net for future stat classes following the same naming pattern.
- **P2 (internal identifier drift): UNCHANGED.** Out-of-scope for this iteration; flagged for future work.

---

## Headline

Two distinct kinds of drift. The abbreviation drift is small (5 occurrences across 3 files) and surgical. The tabular-numeral coverage gap is **systemic** — roughly 60+ modern BEM-style stat classes never land on the locked selector list in [00-tokens.md](../design-system/00-tokens.md), so column alignment silently breaks on every team page, every signature-story card, and every conference table. That's Cheap Win #2 from the anti-patterns deliverable failing in the wild right now.

---

## P0 — Tabular-numeral coverage (Cheap Win #2 from antipatterns)

The locked selector list in [00-tokens.md:142-149](../design-system/00-tokens.md) covers only legacy classes:

```css
.stat, .number, .tabular,
td.numeric, .data-table td,
.percentile-value, .rank-value, .delta,
.hero-finding-number, .saturday-strip-score
```

But the modern team-page and signature-story renderers use BEM naming (`.csp__*`, `.savant__*`, `.signature-story__*`, etc.) that the lock never reaches. Each of these classes displays numerical data that needs column alignment and currently renders with proportional figures — meaning `1` is narrower than `9` and rows zigzag.

**Uncovered stat classes (sample of the highest-impact):**

| Class | Defined / used in | What it shows |
|-------|-------------------|---------------|
| `.csp__stat-value` | reporting.py around line 13788+ (conference stats table) | Conference summary metric values |
| `.hero-strip__stat-value` | reporting.py (team page hero) | Power, resume, model rank numbers |
| `.savant__metric-value` | reporting.py around line 4631+ | Obsession score, rival mentions |
| `.signature-story__stat-value` | reporting.py around line 16903+ | Player stat cards (height, weight, performance) |
| `.scenario-explorer__metric-value` | reporting.py around line 3635+ | Scenario projections |
| `.rival-radar__metric-value` | reporting.py around line 4631+ | Rival radar mentions, scores, weeks |
| `.the-room__meta-value` | reporting.py (the_room module) | Score breakdown values |
| `.biotabs__panel-value` | reporting.py (biotabs module) | Tabbed stat panels |
| `.sc__rcv-value` | reporting.py (receiving corps) | Receiving stats |
| `.impact-stat` (and variants) | reporting.py around line 12443+ | Team comparison cards |
| `.metric-cell` | reporting.py around line 13558+, 13784+ | Conference table numeric cells |
| `.rank-delta` | reporting.py around line 13980+ | Movement / delta indicators |
| `.stat-card`, `.stat-grid` | reporting.py around line 12443+, 13619+ | Generic stat containers |

The agent that ran the audit estimated **coverage ~15%** of stat-displaying classes are protected by the lock. Roughly **60+ classes** in the compiled bundle render numbers without the tabular-nums rule.

### Fix options (pick one)

**Option A — extend the locked selector** (smallest blast radius). Add a universal sweep to [00-tokens.md](../design-system/00-tokens.md) tabular-nums rule. Something like:

```css
.stat, .number, .tabular,
td.numeric, .data-table td,
.percentile-value, .rank-value, .delta,
.hero-finding-number, .saturday-strip-score,

/* Sprint v5-9+ modern BEM stat classes — extend the lock */
[class$="__stat-value"], [class$="__metric-value"],
[class$="__panel-value"], [class$="__meta-value"],
[class$="__rcv-value"], [class$="-delta"],
.metric-cell, .impact-stat, .stat-card, .stat-grid {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1;
  font-family: var(--font-ui);
}
```

The attribute selectors (`[class$="__stat-value"]`) catch the BEM family without enumerating every module. Risk: false-positive matches on classes that happen to end with the same suffix. Verify by spot-checking three team pages after the change.

**Option B — enumerate and lint** (highest correctness, more work). Add every uncovered class explicitly to the lock, then add a build-time lint rule that fails CI if a new `.*__stat-value`-style class ships without a tabular-nums declaration.

**Recommendation:** Option A in Sprint 1 (immediate win). Add the lint rule from Option B as a follow-up so this doesn't regress.

### Verification after fix

1. `grep -rn "font-variant-numeric" src/cfb_rankings/` should show the rule reaches the new selectors.
2. Spot-check: Open `output/site/programs/alabama.html` in browser, scroll to any conference-stats table, confirm the digits `1`, `4`, `7`, `9` all occupy the same horizontal width.
3. Add a Cmd-F sanity check on the generated CSS bundle: every BEM class ending in `__stat-value` or `__metric-value` should be picked up by the rule.

---

## P1 — Abbreviation drift (5 fixes, 3 files)

Surgical and small. The renderer emits two non-canonical column headers (`YPA` and `RTG`) that the conformance spec §1.13 says should be `Y/A` and `RATE`. The drift confirmed in both source and at least one rendered page (`output/site/canon/the-100-best-players-cfp-era.html` shows `RTGN` text in player snippets).

### Fixes

| File:Line | Current | Change to | Notes |
|-----------|---------|-----------|-------|
| [src/cfb_rankings/reporting.py:9457](../../src/cfb_rankings/reporting.py) | `("Passing", "Yards / attempt", "YPA")` | `("Passing", "Yards / attempt", "Y/A")` | Stat tuple; third element is the UI header |
| [src/cfb_rankings/reporting.py:9458](../../src/cfb_rankings/reporting.py) | `("Passing", "Passer rating", "RTG")` | `("Passing", "Passer rating", "RATE")` | Same shape; matches §1.13 |
| [src/cfb_rankings/reporting.py:9688](../../src/cfb_rankings/reporting.py) | `"label": "YPA"` | `"label": "Y/A"` | Player table column dict |
| [src/cfb_rankings/reporting.py:9696](../../src/cfb_rankings/reporting.py) | `"label": "RTG"` | `"label": "RATE"` | Player table column dict |
| [src/cfb_rankings/team_pages/game_recap_hero.py:627](../../src/cfb_rankings/team_pages/game_recap_hero.py) | `"PASS YPA"` | `"PASS Y/A"` | Diagnosis stat candidate list |

These are header-label string changes only; no data pipeline impact.

### Verification after fix

1. Run `python -u manage.py build-site` (fast path per CLAUDE.md).
2. Open `output/site/canon/the-100-best-players-cfp-era.html` and confirm `RTGN` (passer rating normalized) text now reads `RATEN` — or, better, that the underlying label change propagates to wherever the snippet was generated.
3. Grep `output/site/` for residual `YPA` or `RTG` strings; any hits are either historical pages built before the change (re-run publish) or untouched code paths.

---

## P2 — Internal identifier consistency (not a UI bug, but flagged)

The grep also surfaced YPA/RTG inside dict keys and internal metric identifiers in the betting / era-context / mirror-match modules:

- [src/cfb_rankings/bets/era_context.py:41,48](../../src/cfb_rankings/bets/era_context.py) — `"passing_ypa": ("passing", "YPA", True)` and `"ypa": ("passing", "YPA", True)`
- [src/cfb_rankings/bets/achievements.py:119-120](../../src/cfb_rankings/bets/achievements.py) — `vs.get("YPA")` dict-key lookups
- [src/cfb_rankings/bets/mirror_match.py:34](../../src/cfb_rankings/bets/mirror_match.py) — `("passing_ypa", "passing", "YPA", False)`

The conformance spec is silent on internal identifiers (the spec governs UI labels, not Python variable names). These are **not** P0 or P1 drift. They're flagged here only because renaming the public label without renaming the internal key creates a developer-facing mismatch (the code calls it `YPA` but the user sees `Y/A`).

**Recommendation:** leave the internal keys alone unless/until a coordinated rename across the bets data pipeline is in scope. If you do rename, do it in one PR with a migration test that confirms the bets pipeline still loads from the database. Don't bundle it with the P1 fix above.

---

## Out of scope for this audit (worth flagging as follow-ups)

- **Output HTML page-by-page audit.** The ~69k generated pages in `output/site/` were not exhaustively scanned. The renderer-source audit catches drift at the origin; output drift is a downstream consequence that resolves when the renderers ship.
- **CSS class-name conformance** (not just tabular-nums coverage). The conformance spec doesn't currently mandate class-name conventions beyond the tabular-nums lock. If we want `.stat-y-per-attempt` vs `.stat-ypa` consistency, that's a separate spec.
- **Defensive position-group tables.** The conformance spec §1.4-1.6 specifies DL/LB/DB column orders, but no renderer currently emits defensive position-group tables on player pages. This is a *missing feature*, not drift — call it P2 / new-work.
- **Tooltip / bottom-sheet for advanced-stat headers.** Cheap Win #3 from the antipatterns deliverable. No renderer ships this today. Building it is the natural sprint-2 work after this audit's P0/P1 ships.
- **iOS Safari sticky-first-column verification.** The Mobile Playbook §2 calls out `transform: translateZ(0)` as the iOS Safari fix. Whether the existing `.data-table` wrappers actually include it was not audited; recommend a one-hour spot-check on a real iOS device after the P0 fix ships.

---

## Suggested sprint plan

**Sprint 1 (this week):**
1. P0 — Extend the tabular-nums lock in [00-tokens.md](../design-system/00-tokens.md) (Option A above).
2. P1 — Apply the 5 abbreviation-drift fixes.
3. Rebuild the site (`./safe_refresh_site.ps1` or `./publish_site.ps1`).
4. Verify on three pages: a programs page, a canon page, a hub page.

**Sprint 2 (next):**
1. Add the CI lint rule (Option B follow-up).
2. Spec-check iOS Safari sticky-first-column behavior on a real device.
3. Start the Cheap Win #3 work (bottom-sheet tooltip component).

**Deferred:**
1. Internal-identifier rename (`passing_ypa` → `passing_y_a` etc.) — only if a coordinated bets-pipeline change is already planned.
2. Defensive position-group renderer work — bigger sprint, separate from this audit.

---

**Files referenced:**
- [docs/research/cfb-stats-conformance-spec.md](cfb-stats-conformance-spec.md) (§1.13 abbreviation dictionary)
- [docs/research/cfb-stats-antipatterns.md](cfb-stats-antipatterns.md) (Cheap Win #2: tabular numerals)
- [docs/design-system/00-tokens.md](../design-system/00-tokens.md) (locked tabular-nums selector list, lines 142-149)
- [src/cfb_rankings/reporting.py](../../src/cfb_rankings/reporting.py) (HTML monolith; line numbers shift weekly — grep symbols, not lines)
- [src/cfb_rankings/team_pages/game_recap_hero.py](../../src/cfb_rankings/team_pages/game_recap_hero.py)
