# CFB Stats Mobile Playbook

**Date:** May 18, 2026  
**Purpose:** Mobile-first design patterns for CFB stats tables  
**Reference:** FotMob (gold-standard mobile stats UX)  

---

## Executive Summary

Mobile is the hardest sub-problem in stats display. Every CFB site does it poorly. This playbook synthesizes patterns from FotMob (the only site that gets it right) and documents what CFB Index should do differently.

**Core Principle:** **Reformat, don't shrink.** The mobile experience should be a native mobile design, not a shrunken desktop table.

**Key Findings:**
- Horizontal scroll with sticky first column is the baseline
- Never silently drop columns on mobile
- Tap targets must be 44×44px minimum
- Bottom sheets for definitions, not hover tooltips
- Tabular numerals non-negotiable for column alignment

---

## 1. Site-by-Site Mobile Audit

### 1.1 Sports-Reference.com/cfb

**Mobile Experience:**
- Tables overflow horizontally inside a wrapper
- No sticky first column on player career tables (notable defect — they DO have it on some league standings tables)
- Sortable headers, but tiny touch targets (~28px tall)
- Recently rolled out "in-page navigation" redesign — vertical sidebar, better parity
- Glossary lives off-page (navigation penalty)

**Verdict:** Competent but dated. The table itself is strong; navigation around it is weak.

---

### 1.2 ESPN.com/college-football

**Mobile Experience:**
- Stats leaderboards use 2-column layout (rank+player on left, single stat value on right)
- To see a second metric, navigate to a different leaderboard
- Player pages use top-tab pattern (Overview / News / Stats / Bio / Splits / Game Log)
- Tabs truncate on iPhone-width viewports
- **Mobile column-drop without disclosure** — the worst sin. Sacks, long-of-rush vanish with no indication.

**Verdict:** Broad but shallow. Optimized for casual fans skimming, not power users.

---

### 1.3 CBS Sports

**Mobile Experience:** (403 on fetch; based on prior on-device experience)
- Roster pages alphabetize by default
- Career tables don't sort
- Aggressive mobile column-drop without disclosure
- **Lowest-density display of the four big sites**

**Verdict:** Mobile-first to a fault — too much hidden, too little surfaced.

---

### 1.4 PFF (College)

**Mobile Experience:**
- Premium positioning; most stats gated
- Public-facing tables use horizontal scroll without sticky first column
- Color-only encoding for grades
- Hover tooltips that don't fire on touch

**Verdict:** The data is great; the mobile UX is hostile to non-subscribers.

---

### 1.5 FotMob (Gold Standard Reference)

**Mobile Experience:**
- Sticky-top + sticky-left simultaneously on league tables
- Crests not names in leftmost column when space is tight (24px team identity)
- Bottom-sheet competition/season picker
- In-table sparklines for form (last 5 games)
- Tap-to-expand row reveals match details without navigation
- Definition popovers on every advanced stat (tap-triggered, bottom-sheet style)
- Tabular numerals consistently across every stat block
- **No mobile column collapse** — every stat reachable via horizontal scroll
- Search-within-table for long lists
- Performance: 80% Google PageSpeed improvement via mobile-first rewrite

**Verdict:** The only CFB-adjacent product that gets mobile stats right. This is the reference.

---

## 2. Sticky First Column Patterns

### 2.1 The CSS-Only Pattern

```css
.stats-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.stats-table {
  border-collapse: separate;
  border-spacing: 0;
  font-variant-numeric: tabular-nums lining-nums;
}

.stats-table th:first-child,
.stats-table td:first-child {
  position: sticky;
  left: 0;
  z-index: 2;
  background: var(--surface);
  box-shadow: 4px 0 6px -2px rgba(0,0,0,0.15); /* Seam affordance */
}
```

### 2.2 The Gotchas

| Issue | Solution |
|-------|----------|
| Background color required | Without it, body bleeds through sticky column |
| Box-shadow on seam | Gives clear affordance that column is "above" rest |
| iOS Safari bug | Add `-webkit-overflow-scrolling: touch` + `transform: translateZ(0)` |
| Multi-row headers | Sticky-top must span both header rows or second row scrolls under first |
| "L" configuration | Top-left cell needs both `top: 0` and `left: 0` + higher z-index |

### 2.3 The FotMob Approach

- Sticky-left-column + sticky-top-header simultaneously
- Works for dense CFB tables
- Test specifically in iOS Safari (not desktop Safari)

---

## 3. Horizontal Scroll vs Reflow vs Accordion

| Pattern | When to Use | Mobile Experience |
|---------|-------------|-------------------|
| **Horizontal scroll** | Dense tables requiring cross-column comparison | Use for season-by-season, career tables |
| **Reflow to cards** | Each row independently meaningful | Use for "today's top performers" feeds |
| **Accordion** | Grouped data with sensible summaries | Use for player page stat categories |

**Rule:** Use horizontal scroll for genuinely tabular data. It preserves cross-row comparability, which is the ONLY reason to show a table.

**Wrong call:** Using cards for dense stat tables — destroys comparability.

---

## 4. "Show More Columns" Toggles

**Current State:** Almost nobody in CFB has this working. Sports Reference offers no column-customization toolbar. ESPN doesn't. CBS doesn't.

**Best non-CFB example:** FBref (soccer side of Sports-Reference)
- Basic / Advanced / Splits button group above table
- Gives finite curated views rather than infinite per-column toggles

**CFB Index Recommendation:**
- Offer 3 named views per stat block: **Standard / Advanced / Splits**
- Segmented control above the table
- Remember choice in `localStorage`
- Avoid per-column checkboxes (too granular for median fan)

---

## 5. Touch Target Sizing

**Standards:**
- WCAG 2.5.5 (AAA) = 44×44 CSS pixels minimum
- Apple HIG = 44×44pt
- Material Design = 48×48dp

**CFB Index Target:** **44px minimum**, preferring 48px on critical headers

**Implementation Pattern:**
Visible row height can stay at 36px (for density) if the touch target is expanded via padding on the inner `<button>` element. The `<th>` contains a `<button>` with `padding: 12px 8px` — effective click area 44px+. This decouples touch ergonomics from visual density.

---

## 6. Filter UX on Mobile

| Pattern | When to Use | Example |
|---------|-------------|---------|
| **Modal** | 5+ filters, user expects to set several | ESPN does this poorly |
| **Inline** | 2-3 filters, toggled often | FotMob segmented controls |
| **Accordion** | Sometimes needed, default view common | Avoids modal disorientation |

**CFB Index Recommendation:**
- **Inline pills** for top 2 filters (season, situation)
- **Accordion** for long tail (opponent rank, location, month, weather)

---

## 7. Search-Within-Table

**Current CFB State:** Most CFB sites lack this entirely.

**FotMob Pattern:**
- Magnifying-glass icon opens inline filter input
- Typing narrows visible rows in real time
- Client-side row hiding (no server roundtrip)
- Debounce 100ms
- Show "Showing X of Y" count

**CFB Index Recommendation:**
- For any leaderboard or roster table >25 rows, include "Filter players" input
- Client-side filtering only
- No server roundtrip

---

## 8. Splits Access on Mobile

| Pattern | Sites Using | Assessment |
|---------|-------------|------------|
| **Tab bar** | ESPN | Truncates on small screens |
| **Dropdown** | Sports Reference | Workable but uninspiring |
| **Bottom sheet** | FotMob | Right pattern for many options |
| **Segmented control** | — | Best for 2-4 options |

**CFB Index Recommendation:**
- **Segmented control** for primary splits (Home / Away / All)
- **Bottom sheet** for long tail (opponent, situation, situation × month)

---

## 9. Cross-Link Tap Targets

**Patterns:**

| Pattern | Pros | Cons |
|---------|------|------|
| **Full-row tap** | Huge touch target | Ambiguous when multiple links in row |
| **Chip tap only** | Unambiguous | Tiny touch targets, easy to mistap |

**Best Pattern:** **Chip-with-padded-touch-area**
- Visible link is a chip with 36px tall body
- Touch target extends 8px in each direction via `padding`
- Effective hit area: 52×44px
- Visual stays tight, touch is forgiving

**CFB Index Recommendation:**
- Chip-with-padded-touch for opponent, score, date columns
- Whole-row tap only for player-name rows (no ambiguity)

---

## 10. Definition Tooltip Behavior

**Right Pattern:** **Tap-to-reveal bottom sheet**

Tapping a column header opens a bottom sheet (mobile) / popover (desktop) with:
- Stat name (full, not abbreviated)
- One-sentence plain-English definition
- Formula (in monospace, with operator spacing)
- "Top 10% of QBs are above X" benchmark
- Link to methodology

**Avoid:**
- Hover-only tooltips (broken on touch)
- Full-page navigation to glossary (kills context)
- Small popovers clipped by viewport edge

---

## 11. Tabular Numeral Discipline

**Current CFB State:** Almost every CFB site gets this wrong. Sports Reference, ESPN, CBS all use default proportional figures.

**The Fix (shockingly cheap):**

```css
.stats-table {
  font-variant-numeric: tabular-nums lining-nums;
}
```

Or with explicit OpenType:

```css
.stats-table { 
  font-feature-settings: "tnum" 1, "lnum" 1; 
}
```

**Visual Impact:** Dramatic. Every digit takes same horizontal space, columns align cleanly, eye scans vertically without zigzag.

**Font Recommendations:** Inter is excellent; Source Sans, Roboto, IBM Plex also work. CFB Index already uses Inter and enforces `font-feature-settings: "tnum"` — keep this strict.

---

## 12. Performance Budget for Mobile

**Targets** (per Web Vitals "Good" thresholds, tightened for sports sites):

| Metric | Target | Rationale |
|--------|--------|-----------|
| **FCP** | < 1.5s on 4G | Web Vitals "Good" = 1.8s; we should beat it |
| **LCP** | < 2.0s on 4G | Web Vitals "Good" = 2.5s |
| **CLS** | < 0.05 | Web Vitals "Good" = 0.1; tables must reserve space |
| **INP** | < 200ms | Web Vitals "Good" = 200ms |
| **Total page weight** | < 350KB (player), < 500KB (team) | Static-site advantage |

**Static-Site Advantage:** No client-side hydration delay, no API roundtrip. Main risks: oversized images (use AVIF/WebP + lazy-load), web-font FOUT/FOIT, inline `<script>` blocks.

**CI Budget:** Any commit pushing a page over 400KB or LCP over 2.0s on synthetic 4G test fails the build.

---

## 13. Top 10 Mobile Stats-Display DOs and DON'Ts

1. **DO** make the first column sticky-left on every horizontally-scrolling table. **DON'T** ever let the identifying column disappear during scroll.

2. **DO** enforce `font-variant-numeric: tabular-nums lining-nums` on every stat-bearing element. **DON'T** ship a table with proportional figures.

3. **DO** size every interactive element to ≥44px touch target. **DON'T** rely on visible row height as the click area.

4. **DO** make column headers tappable to sort, with visible arrow affordance and `aria-sort`. **DON'T** rely on hover to surface sort.

5. **DO** open a bottom-sheet on tap for advanced-stat definitions. **DON'T** require navigation to a glossary page.

6. **DO** show every column at every breakpoint, with horizontal scroll if needed. **DON'T** silently `display: none` columns on mobile.

7. **DO** default sort to the most-meaningful column. **DON'T** default to alphabetical-by-name on a stats site.

8. **DO** preserve scroll position across navigation. **DON'T** lose the fan's place when they hit back.

9. **DO** pair color with shape, icon, or text for percentile/rank encoding. **DON'T** rely on color alone.

10. **DO** budget every page to LCP < 2.0s on 4G and < 400KB transferred. **DON'T** ship a stats page heavier than a video.

---

## 14. FotMob: What They Do That No CFB Site Does

1. **Sticky-top + sticky-left simultaneously** on league tables
2. **Crests not names** in leftmost column when space is tight (24px team identity)
3. **Bottom-sheet competition/season picker** — single primary selector button
4. **In-table sparklines** for form (last 5 games) — 50×16px SVG per row
5. **Tap-to-expand row** reveals match details without navigation
6. **Definition popovers** on every advanced stat — tap-triggered, bottom-sheet style
7. **Tabular numerals consistently** across every stat block
8. **No mobile column collapse** — every stat reachable via horizontal scroll
9. **Search-within-table** for long lists (squad pages)
10. **Performance** — 80% Google PageSpeed improvement via mobile-first rewrite

**The CFB Convention** (which almost every CFB site follows):
- Horizontal scroll without sticky first column
- Hover-only tooltips
- Alphabetical default sort
- Column collapse without disclosure
- No row drilldown
- Hover-only definitions

**Doing the FotMob playbook on CFB data would be a real differentiator.**

---

## 15. Reconciliation with the Locked Design System

The mobile playbook needs to plug cleanly into the design-system contracts locked on 2026-05-17 ([00-tokens.md](../design-system/00-tokens.md), [30-page-archetypes.md](../design-system/30-page-archetypes.md), [31-chart-vocabulary.md](../design-system/31-chart-vocabulary.md), [32-receipt-pattern.md](../design-system/32-receipt-pattern.md), [33-confidence-signaling.md](../design-system/33-confidence-signaling.md)). Tag every finding as one of three states.

### 15.1 EXTENDS the locked system (additive, no Window A/B coordination required)

| Mobile-playbook finding | How it extends the locked system |
|------------------------|----------------------------------|
| Tabular numerals on every stat cell | Already locked in `00-tokens.md` (line 142: `.stat, .number, .tabular, td.numeric...` enforces `font-variant-numeric: tabular-nums`). Playbook re-affirms; lints can enforce on any new stat-table component. |
| Sticky first column CSS | Additive: new `.stats-wrap` + `.stats-table` selectors that read from existing tokens (`--color-surface`, `--color-line`, `--stroke-hair`). |
| 44px touch targets | Already implicit in design system; playbook makes the rule explicit. The `.cite-link`-style classes in receipt-pattern already use the same affordance pattern. |
| Bottom-sheet definitions | Additive new component; CSS reads from existing tokens (`--radius-lg`, `--sp-3`, `--color-ink`, etc.). |
| Segmented control for Standard/Advanced/Splits | Additive new component; no conflict with existing components. |
| Search-within-table input | Additive new component; reads token `--font-ui`, `--fs-body-sm`. |
| Performance budget (LCP < 2.0s, < 400KB) | Already in `30-page-archetypes.md` performance budgets per archetype. The Profile archetype budgets FCP < 1.0s, LCP < 2.5s; the Mobile Playbook tightens to LCP < 2.0s for stats-table-heavy variants. Compatible — strictly tighter, never looser. |
| Color-with-shape encoding for percentile cells | Already locked in `33-confidence-signaling.md`'s three-color-plus-icon discipline. Playbook re-affirms. |

### 15.2 CHALLENGES the locked system (requires Window A/B coordination before implementing)

| Mobile-playbook finding | What it challenges | Resolution path |
|------------------------|---------------------|-----------------|
| In-table sparklines (last 5 games) | `31-chart-vocabulary.md` allows Trajectory Spark but specifies 160×40px default; FotMob's in-table variant is 50×16px. | Add an "in-table-spark" size variant to chart vocabulary, or document the 50×16 size as a special-case sub-variant of Trajectory Spark. |
| Tap-to-expand row reveals | Not currently covered by any archetype. Profile and Database archetypes describe full-page render only, not in-table expansion. | Update `30-page-archetypes.md` Database archetype to allow inline row expansion (the spec already mentions "Expandable row details" — make the in-page-no-navigation behavior explicit). |
| Bottom-sheet competition picker | Not in any archetype today. The Database archetype mentions full-screen modal for filter trigger; bottom sheet is a different pattern. | Add bottom-sheet as an allowed mobile filter pattern in the Database archetype. |
| Print stylesheet for stat tables | Design system mentions print only briefly in `31-chart-vocabulary.md`. Tables need their own `@media print` rules (drop sticky positioning, expand glossary, repeat thead, avoid row breaks). | Add a `00-tokens.md` or new `01-print.md` document covering print rules for tables. |

### 15.3 OUT-OF-SCOPE for the locked contracts

| Mobile-playbook finding | Why out of scope |
|------------------------|------------------|
| CSV export per table | Backend/data-pipeline concern; not a design-system contract |
| `localStorage` view-toggle persistence | Client-side state-management concern; doesn't affect any design-system contract |
| iOS Safari workarounds (`-webkit-overflow-scrolling`, `transform: translateZ(0)`) | Browser-compatibility implementation detail; goes in component CSS, not design tokens |
| Lighthouse CI thresholds | Already in `30-page-archetypes.md` as Lighthouse CI score ≥ 95 |
| Mobile testing on real iOS Safari devices | Testing/QA concern, not design |

### 15.4 Profile-archetype-specific table behavior

Most stats tables on CFB Index live inside Profile archetype pages (`/programs/<slug>.html`, `/players/<slug>.html`). The Profile archetype currently specifies "Sticky identity strip persists; rituals strip horizontal scroll with snap; modules stack vertically" but doesn't specify table behavior. The mobile playbook supplies the missing contract for stats tables inside Profile pages:

- **Horizontal scroll wrapper** with sticky first column (the player/season/team identity).
- **Tabular numerals enforced** on every `<td>` in the table.
- **Modules stack vertically** at mobile width (Profile-archetype rule); the table inside each module scrolls horizontally on its own.
- **Filter chips** that affect a specific table live inside that table's module — not in the page-level filter strip (which would imply the filter affects the whole page).
- **Drill-down expansion** (game log under season row) opens as bottom sheet on mobile (per the in-page expansion challenge above).

This is a clarification, not a challenge — the Profile archetype is silent on the question, and the mobile playbook provides the natural answer.

---

## 16. Implementation Checklist

### P0 — Mobile Baseline

- [ ] Sticky first column on all horizontal-scrolling tables
- [ ] Tabular numerals on all stat cells
- [ ] 44×44px minimum touch targets on all interactive elements
- [ ] Horizontal scroll wrapper (never page-level scroll)
- [ ] Sortable column headers with visible affordance

### P1 — Mobile Experience

- [ ] Bottom-sheet definitions for all advanced stats
- [ ] Segmented control for primary splits (Home/Away/All)
- [ ] Search-within-table for tables >25 rows
- [ ] Chip-with-padded-touch for all cross-link chips
- [ ] Performance budget: LCP < 2.0s, < 400KB transferred

### P2 — Mobile Excellence

- [ ] In-table sparklines for trajectory (last 5 games)
- [ ] Tap-to-expand row reveals game details
- [ ] Standard/Advanced/Splits view toggle
- [ ] Bottom sheet for advanced split selection
- [ ] Print stylesheet for all stat tables

---

## Sources

- Sports Reference Table Tips: https://www.sports-reference.com/blog/2017/04/video-sports-reference-table-tips-and-tricks/
- Nielsen Norman — Mobile Tables: https://www.nngroup.com/articles/mobile-tables/
- Datawrapper — Fonts for Data Visualization: https://blog.datawrapper.de/fonts-for-data-visualization/
- FotMob FAQ: https://www.fotmob.com/faq
- Seven Peaks Software — FotMob Case Study: https://sevenpeakssoftware.com/case-studies/app-for-football/
- Mobbin — FotMob Screen Library: https://mobbin.com/explore/screens/2d3e370c-7780-4b5f-9f3c-133a91b6c063
- WebOsmotic — Mobile UX Tables: https://webosmotic.com/blog/tables-best-practice-for-mobile-ux/
- Ninja Tables — Sticky Headers vs Fixed Columns: https://ninjatables.com/sticky-headers-vs-fixed-columns/

---

**Document Length:** ~2,800 words  
**Version:** 1.0  
**Last Updated:** May 18, 2026  
**Status:** Ready for implementation
