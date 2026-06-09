# Anti-Patterns Catalog & Mobile Playbook — CFB Stats Display Sites

**Compiled:** 2026-05-18
**Scope:** Competitive research across sports-reference.com/cfb, ESPN.com/college-football, CBS Sports, PFF, TeamRankings, CFBStats, plus FotMob as a non-CFB gold-standard reference.
**Use:** Inform CFB Index design decisions for player pages, team pages, leaderboards, and methodology surfaces.

---

## PART A — ANTI-PATTERNS CATALOG

A consolidated list of patterns CFB stats sites get wrong, why each one hurts, and the cheap, high-leverage thing CFB Index should do instead. Each pattern names sites where it's observed; where the live URL could not be fetched (CBS Sports, TeamRankings — 403s), patterns are inferred from prior on-device experience and from public design critiques of the same codebases.

### 1. Mobile column collapse without controls

**The pattern.** On narrow viewports, ESPN's player stat blocks (`espn.com/college-football/player/stats/_/id/...`) and CBS Sports' player pages drop entire columns. Sacks vanish. Long-of-rush vanishes. Fumbles vanish. The user is given no toggle, no "show more columns" affordance, and no indication that columns were removed. The only signal is a faint horizontal scroll bar that, on touch devices, appears only mid-gesture.

**Why it's bad.** Silent data omission breaks the implicit contract of a "career statistics" table. A fan who scrolled to a player page on their phone genuinely believes the displayed columns are all the columns that exist. Worse, the *same site on desktop* shows the missing columns, so cross-device users get inconsistent mental models. This is also bad for accessibility: a screen reader announces only what's in the DOM, and the hidden columns are typically `display: none` (not in the DOM at all on small breakpoints).

**Conformance win.** Always render every column at every breakpoint. Use horizontal scroll **with** a sticky first column (player name / season label). If horizontal scroll is unacceptable, provide an explicit "Customize columns" sheet that lets the user pick a 4-column subset and remembers their choice in `localStorage`. The visual cue must be unmissable: a right-edge fade or a visible scroll-hint chevron, never just a hairline scrollbar.

### 2. Unsortable historical tables

**The pattern.** Sports-reference.com career tables — the canonical "Year, School, Conf, Class, Pos, G, ..." block on every player page — *are* sortable on desktop (click a header). On mobile, the click-target on the header is roughly 24px tall, the sort affordance is invisible (no chevron, no underline, no aria-sort), and a misfired tap registers as a row tap that scrolls instead. CBS Sports career tables don't sort at all on either device.

**Why it's bad.** "Best season" is the most common implicit query a fan brings to a player page ("when was Travis Hunter most productive?"). If you can't sort by yards or yards/game, you must read the table linearly and compute mentally. This is friction for the most common task.

**Conformance win.** Every column header is a tap target ≥44px tall on mobile. Sort affordance is a visible arrow (`↑` / `↓`) that flips on tap. `aria-sort="ascending"` is set. The current sort persists across page navigation via URL fragment (`#sort=yds-desc`) so a fan can deep-link to "the table sorted by yards."

### 3. Tooltip behavior failures (advanced stats with no inline definitions)

**The pattern.** ESPN displays QBR, NY/A, AY/A, ANY/A in passing tables with no inline tooltip and no glossary link adjacent to the table. Sports-reference does include a glossary, but it lives at `/cfb/about/glossary.html` — a full navigation hop away. PFF gates advanced metrics (grades, EPA, true completion %) behind PFF+ and provides only marketing copy explaining what they mean.

**Why it's bad.** Advanced stats fail their job if the fan cannot resolve "what is this number telling me" in less than 2 seconds. On mobile, the cost of a hop to a glossary page is page reload + scroll + lose-your-place — easily 30 seconds round-trip, often abandoned.

**Conformance win.** Every advanced-stat column header is tappable on mobile. A tap reveals an inline definition (popover on desktop, bottom-sheet on mobile) with: one-sentence definition, formula, "leaders typically range from X to Y" benchmark, and a link to the methodology page. The bottom sheet pattern is the right call — it leaves the table visible above so the fan can match the definition to the value.

### 4. Missing drilldown (season-total row that can't expand to per-game)

**The pattern.** Sports-reference shows season totals on the main player page; per-game splits live at a separate URL (`/cfb/players/.../gamelog/`). There is no inline expand. ESPN's pattern is similar — season totals on one tab, "Game Log" on another. To answer "did he do this in one big game or consistently?" the fan must navigate, lose context, and navigate back.

**Why it's bad.** Drilldown is the natural exploratory motion of a sports fan. "Tell me more about that season" is a primitive intent. Forcing a navigation hop fragments the mental model and breaks back-button scroll restoration (see #13).

**Conformance win.** Season-total rows are expandable inline (chevron at row end, tap to expand). Expansion reveals a compact game-log table — opponent, result, key stats — directly beneath the season row. On mobile, the expansion can be a bottom sheet to preserve vertical density on small screens. Use `<details>` or an aria-expanded button — never a custom div that breaks keyboard nav.

### 5. Default sort wrong (alphabetical when fans want best/worst)

**The pattern.** ESPN's stat leader pages (e.g. `/college-football/stats`) default to ranked order (good), but team-roster pages alphabetize. CBS Sports player directories alphabetize by default. CFBStats.com defaults to alphabetical on conference roster pages. For a fan asking "who's the best receiver on this team?", alphabetical order is precisely the wrong answer.

**Why it's bad.** Default sort is a strong opinion the page is taking about the user's intent. Alphabetical by name is the *least* useful default for a stats site — it's the default a database administrator would choose, not the default a fan would choose. It also penalizes players whose names start with letters in the second half of the alphabet (a real visibility bias).

**Conformance win.** Default sort by the most-meaningful column for the page type. Roster page: sort by primary stat for that position group (yards for skill, tackles for defense). Team page: sort by total contribution (touches + production). Make the default obvious — show the sort arrow on the header, and persist the user's chosen sort in URL state.

### 6. Splits hidden behind tabs that aren't discoverable

**The pattern.** ESPN player pages use a horizontal tab bar — Overview, News, Stats, Bio, Splits, Game Log. On mobile, this bar truncates and requires horizontal scroll. The "Splits" tab sits past the right edge on iPhone-width viewports. CFBStats.com nests splits inside an "Advanced Package" — they exist, but require knowing the IA. Sports-reference exposes splits but only via a small text link in a sub-nav.

**Why it's bad.** Splits (home/away, vs ranked, by month, by half) are the most differentiated content a stats site can offer. Hiding them defeats their value. Users who don't know to look for splits don't ever find them; users who do look bounce when they can't see the tab.

**Conformance win.** Surface splits as a primary CTA on the player page above the fold — a labeled card or a prominent pill ("Splits & Situations →"). On mobile, make the tab bar wrap or use a segmented control that fits the viewport without horizontal scroll.

### 7. Historical depth UX failures (only career totals, no year-by-year scroll)

**The pattern.** ESPN player pages show "2024, 2025, Career" as three rows, then stop. There's no easy access to seasons 2020-2023 from the same view — the user must change the season filter or navigate to a "career" subpage. CBS Sports shows only "current season" by default. This collapses a player's whole story into a three-row table.

**Why it's bad.** Historical depth is *the* differentiator for a stats site. The "Cam Ward at Washington State → at Miami" arc is a story the table can tell if it shows all years. Forcing a season-picker click for each year breaks the storytelling beat.

**Conformance win.** Always render every year the player played, in chronological order, with one row per year. Sticky "Career Total" row at the bottom. If the player has 5+ years (transfer + redshirt) make the table scroll vertically inside its container rather than truncating.

### 8. Inconsistent abbreviations across pages on the same site

**The pattern.** ESPN uses "REC" for receptions on one page and "RECP" on another. Sports-reference uses "Cmp%" in passing tables and "Pct" in fielding tables. CBS uses "ATT" for both pass attempts and rushing attempts depending on the section. Glossaries don't reconcile.

**Why it's bad.** Fans pattern-match column headers. Inconsistency forces them to re-decode every table. For a site with our level of historical depth, this would compound badly.

**Conformance win.** Canonicalize a single abbreviation dictionary at the project level. Lock it in `docs/design-system/00-tokens.md` style. Lint for stragglers — any table column not in the dictionary fails the build.

### 9. Bad responsive table behavior (horizontal scroll without sticky first col)

**The pattern.** Sports-reference.com/cfb tables on mobile scroll horizontally but the first column (Year) does NOT stick. Scroll right to see receiving stats, lose the year label. CFBStats has the same defect. ESPN's leaderboards scroll horizontally with rank pinned, which is correct — but their player-detail pages don't pin.

**Why it's bad.** Loss of the identifying column during horizontal scroll is the single most disorienting thing a stats table can do. The fan ends up with a column of numbers and no idea which season or player it belongs to. Many users abandon the table at this point.

**Conformance win.** Always make the first column `position: sticky; left: 0;` with a background color matching the table to prevent text bleed-through. Add a thin right-border on the sticky column to signal the seam. Test in iOS Safari specifically — it has a position:sticky bug in nested scroll containers that requires `transform: translateZ(0)` on the parent.

### 10. Tap targets too small for mobile

**The pattern.** Sports-reference sortable headers compute to roughly 28px tall on mobile — below the WCAG 2.5.5 AAA threshold (44×44) and below Apple HIG (44×44pt) / Material (48×48dp). Row links on CBS roster pages are similar. Cross-link chips (player name → player page) are sometimes only 32px high on ESPN.

**Why it's bad.** Below 44px, mistap rate climbs sharply. WCAG 2.1 Success Criterion 2.5.5 (Target Size, AAA) requires 44×44 CSS pixels minimum. Failing this also fails most accessibility audits.

**Conformance win.** Make every interactive element in a stats table ≥44px tall. If row height must be 36px for density, expand the hit area via padding on an inner `<a>` so the touch box exceeds the visible row. Use `:focus-visible` rings so keyboard users get the same affordance.

### 11. Hover-dependent tooltips that don't work on mobile

**The pattern.** PFF's column headers show tooltip definitions on hover on desktop. On mobile, no tooltip ever fires because there's no hover event — tapping triggers sort or row select instead. Sports-reference glossary popups behave similarly.

**Why it's bad.** Mobile-first design failure. A definition that exists but is unreachable on the majority of traffic (mobile is >60% of sports-site traffic per Comscore) is no definition at all.

**Conformance win.** Definitions must be tap-triggered, not hover-triggered. Use `onClick` not `onMouseEnter`. On desktop, a 200ms hover delay can co-exist with click for power-user efficiency, but click is the source of truth.

### 12. Color-only encoding for rank/percentile

**The pattern.** PFF grades use a green-to-red gradient. Some PFF readers cannot distinguish the middle tones (red-green colorblindness affects ~8% of men). ESPN's "hot/cold streak" indicators use color only. CFBStats uses bold text only — better, but loses the at-a-glance signal.

**Why it's bad.** WCAG 1.4.1 (Use of Color, A-level) prohibits color as the only means of conveying information. Beyond compliance: color-only encoding is unreadable in greyscale print, in bright sunlight, and for the ~4% of users with various color vision differences.

**Conformance win.** Pair color with shape or text. A percentile cell becomes: colored fill + numeric percentile + optional icon (▲ for top quartile, ▼ for bottom). The CFB Index design system already enforces this via `33-confidence-signaling.md` — keep the discipline strict.

### 13. Lazy loading that breaks back-button scroll position

**The pattern.** ESPN's stats leaderboards lazy-load rows as the user scrolls. When the user taps a player row, navigates to that player's page, then hits back — the leaderboard reloads from scratch and scroll position is lost. The lazy-loading state is not in the history entry.

**Why it's bad.** This is the single biggest source of mobile sports-site rage. The fan was 200 rows deep in a leaderboard, tapped a player, hit back, and is now at the top again. They abandon.

**Conformance win.** Either render the whole leaderboard server-side (the CFB Index static-site approach makes this easy — we already do this), or stash scroll position + loaded-row count in `history.state` and restore on `popstate`. Test with `scroll-restoration: manual` to take control.

### 14. Comparison views that require too many clicks

**The pattern.** ESPN's player comparison flow: navigate to player 1, find compare button (often missing), enter player 2 name, wait for autocomplete, select, navigate to compare page. 4-6 taps minimum. CBS doesn't have a comparison view at all. Sports-reference has Stathead behind a paywall.

**Why it's bad.** Comparison is the single most common analytical request from sports fans ("Travis Hunter vs Charles Woodson"). Burying it kills the most valuable interaction.

**Conformance win.** Make comparison a primary action on every player page — a "Compare to..." pill at the top, with a typeahead populated from same-position peers. One tap to set up, one second to see results. If our archive is rich enough, also surface "auto-compare" cards ("This season ranks 3rd among Heisman finalists for ANY/A").

### 15. Page-level horizontal scroll (the absolute worst)

**The pattern.** Caused by a wide table that overflows its container *and* breaks the body layout. Not commonly seen on the big four sites — they avoid it via `overflow-x: scroll` on the table wrapper — but CFBStats has occasional cases on legacy pages, and many small CFB blogs do it. The user pinches to zoom and finds the whole page scrolls sideways including the header.

**Why it's bad.** Catastrophic. There is no other UX failure as immediately disqualifying. It signals "this page wasn't built for me."

**Conformance win.** `overflow-x: hidden` on `<body>`. Every table that might exceed viewport width must be wrapped in `<div class="table-scroll">` with its own `overflow-x: auto`. Add a CI check that asserts no element has a computed scrollWidth > clientWidth on `<body>` at 360px viewport.

---

## PART B — MOBILE PLAYBOOK

Mobile is the hardest sub-problem in a stats display. Below: a site-by-site audit, the structural choices each site made, and the playbook CFB Index should adopt.

### 1. Site-by-site mobile audit

**Sports-reference.com/cfb.** The dominant CFB-stats incumbent. Mobile experience: tables overflow horizontally inside a wrapper. No sticky first column on player career tables (a notable defect — they DO have sticky first column on some league standings tables, so the capability exists). Sortable headers, but with tiny touch targets. Recently (2025-2026) rolled out an "in-page navigation" redesign that moves the section nav from a horizontal bar to a vertical sidebar — a real improvement, parity between desktop and mobile, click-not-hover for the inner nav. Glossary lives off-page. Verdict: **competent but dated**; the table itself is the strongest part, the navigation around it the weakest.

**ESPN.com/college-football.** Optimized for breadth, not depth. Stats leaderboards on mobile use a 2-column layout (rank+player on left, single stat value on right). To see a second metric, the user navigates to a different leaderboard. Player pages use a top-tab pattern (Overview / News / Stats / Bio / Splits / Game Log) that truncates on iPhone. Mobile column-drop without disclosure is the worst sin. Verdict: **broad but shallow**; the design optimizes for casual fans skimming, not power users who want all the numbers.

**CBS Sports.** Could not fetch directly (403). Based on prior on-device experience: roster pages alphabetize by default, career tables don't sort, mobile column-drop is aggressive. The lowest-density display of the four big sites. Verdict: **mobile-first to a fault** — too much hidden, too little surfaced.

**PFF.** Premium positioning. Most advanced stats are gated. Public-facing tables on mobile use horizontal scroll without sticky first column. Color-only encoding for grades. Hover tooltips that don't fire on touch. Verdict: **the data is great, the mobile UX is hostile to non-subscribers**.

**FotMob (non-CFB reference).** The gold standard. Used as benchmark below.

### 2. Sticky first column patterns — how it's actually built

The CSS-only pattern is `position: sticky; left: 0` on the first `<td>` and `<th>` of each row, combined with `overflow-x: auto` on a wrapper. The gotchas:

- Background color is mandatory. Without it, the body of the table bleeds through the sticky column.
- A right-edge box-shadow (`box-shadow: 4px 0 6px -2px rgba(0,0,0,0.15)`) gives the seam a clear affordance — the eye sees the column is "above" the rest of the table.
- iOS Safari: `position: sticky` inside `overflow-x: auto` is fragile. Add `-webkit-overflow-scrolling: touch` and consider `transform: translateZ(0)` on the wrapper. Test specifically in iOS Safari, not just desktop Safari.
- Sticky headers (top) compose with sticky columns (left) to form an "L" — the top-left cell needs both `top: 0` and `left: 0` and a higher z-index.
- For multi-row headers (e.g. "Passing | Cmp Att Yds | Rushing | Att Yds TD"), the sticky-top must span both header rows or the second row will scroll under the first.

The FotMob approach uses sticky-left-column + sticky-top-header simultaneously and is the right structural answer for dense CFB tables.

### 3. Horizontal scroll vs reflow vs accordion — when each is appropriate

- **Horizontal scroll** is right when the user genuinely needs to compare across many columns (e.g. a season-by-season career table). Density wins. Pair with sticky first column always.
- **Reflow to cards** is right when each row is independently meaningful and rarely compared to its neighbors (e.g. a "today's top performers" feed). Each card becomes a self-contained unit with the primary stat large and contextual stats small.
- **Accordion** is right when there's grouped data with sensible top-level summaries (e.g. a player page where "Passing" expands to show the full passing table, "Rushing" expands to show rushing). The top level reads like a sentence; the detail is one tap away.

The wrong call is using cards for genuinely tabular data — it destroys cross-row comparability, which is the *only* reason to show a table.

### 4. "Show more columns" toggles — who has them, do they work?

Almost nobody in CFB. Sports-reference offers no column-customization toolbar. ESPN doesn't. CBS doesn't. PFF has a partial implementation on some pages but it's behind the paywall and uses a modal that's awkward on mobile.

The closest working example outside CFB is FBref (soccer side of Sports-Reference) which lets users toggle between Basic / Advanced views via a button group above the table. The pattern works: it acknowledges that no single column set fits all users, and it gives a finite set of curated views rather than infinite per-column toggles.

**CFB Index recommendation:** Offer 3 named views per stat block (e.g. for QB passing: Standard / Advanced / Splits), as a segmented control above the table. Remember the choice in `localStorage`. Avoid per-column checkboxes — they're too granular for the median fan.

### 5. Touch target sizing on sortable headers

WCAG 2.5.5 (AAA) = 44×44 CSS pixels. Apple HIG = 44×44pt. Material Design = 48×48dp. CFB Index target: **44px minimum**, preferring 48px on critical headers.

Implementation pattern: the visible row height can stay at 36px (for density) if the touch target is expanded via padding on the inner `<button>` element. The `<th>` itself contains a `<button>` with `padding: 12px 8px` and an effective click area of 44px+. This decouples touch ergonomics from visual density.

### 6. Filter UX on mobile (modal vs inline vs accordion)

- **Modal** (full-screen sheet that overlays the page) is the right call when filters are numerous (5+) and the user expects to set several before re-querying. ESPN does this poorly — the modal is dense and uses dropdowns inside dropdowns.
- **Inline** (filter pills above the table) is right when there are 2-3 filters and they're toggled often. FotMob does this well — segmented controls for season, competition.
- **Accordion** (filters collapsed in a "Filters" disclosure above the table) is right when filters are sometimes needed but the default view is the common case. It avoids the modal's "where did the page go" disorientation.

**CFB Index recommendation:** Inline pills for the top 2 filters (season, situation). Accordion for the long tail (opponent rank, location, month, weather).

### 7. Search-within-table behavior

Most CFB sites lack this entirely. Sports-reference has a global site search but not table search. ESPN doesn't. CFBStats doesn't.

FotMob has table search via a magnifying-glass icon that opens an inline filter input — typing narrows the visible rows in real time. This is the right pattern for any table longer than ~30 rows.

**CFB Index recommendation:** For any leaderboard or roster table >25 rows, include a "Filter players" input above the table that does client-side row hiding (no server roundtrip). Debounce 100ms. Show a "Showing X of Y" count.

### 8. How splits are accessed on mobile

- **Tab bar**: ESPN uses this; it truncates on small screens (#6 above).
- **Dropdown**: Sports-reference uses a `<select>` for season splits — workable but uninspiring.
- **Bottom sheet**: FotMob uses bottom sheets for "select competition" — the right pattern when there are many options.
- **Segmented control**: The best for 2-4 options (e.g. Home / Away / All) where direct access matters.

**CFB Index recommendation:** Segmented control for primary splits (e.g. H/A/Neutral). Bottom sheet for the long tail (opponent, situation, situation × month).

### 9. Cross-link tap targets (row to game, row to opponent)

Two patterns observed:

- **Full-row tap** — the entire `<tr>` is clickable. Pro: huge touch target. Con: ambiguous when the row contains multiple plausible link targets (opponent name AND game date AND score).
- **Chip tap** — only the specific text is linked. Pro: unambiguous. Con: tiny touch targets, easy to mistap.

The best pattern is **chip-with-padded-touch-area**: the visible link is a chip with a 36px tall body, but the touch target extends 8px in each direction via `padding`, hitting 52px effective. The visual stays tight, the touch is forgiving.

**CFB Index recommendation:** Chip-with-padded-touch for opponent, score, and date columns. Whole-row tap reserved for player-name rows where there's no ambiguity.

### 10. Definition tooltip behavior on mobile

The right pattern is **tap-to-reveal bottom sheet**. Tapping a column header opens a bottom sheet (or popover on desktop) with:

- Stat name (full, not abbreviated)
- One-sentence plain-English definition
- Formula (in monospace, with operator spacing)
- "Top 10% of QBs are above X" benchmark
- Link to methodology

Avoid: hover-only tooltips (broken on touch — #11 above), full-page navigation to a glossary (kills context), small popovers that get clipped by the viewport edge.

### 11. Tabular numeral discipline

Almost every CFB site gets this wrong. Sports-reference uses default proportional figures in its tables — "1" is narrower than "9", so column alignment drifts. ESPN does the same. CBS does the same.

This is shockingly cheap to fix:

```css
.stats-table {
  font-variant-numeric: tabular-nums lining-nums;
}
```

Or with explicit OpenType:

```css
.stats-table { font-feature-settings: "tnum" 1, "lnum" 1; }
```

The visual difference is dramatic — every digit takes the same horizontal space, columns align cleanly, the eye can scan vertically without zigzag. Combined with a sans-serif font that has good tabular figures (Inter is excellent; Source Sans, Roboto, IBM Plex also work), this is the single highest-leverage typographic fix.

CFB Index already uses Inter and the design system locks `font-feature-settings: "tnum"` — keep this discipline strict and audit any new table renderer for the same setting.

### 12. Performance budget for mobile

Targets (per Web Vitals "Good" thresholds, with sports-site-specific tightening):

- **First Contentful Paint (FCP):** < 1.5s on 4G (Web Vitals "Good" = 1.8s; we should beat it because we're static)
- **Largest Contentful Paint (LCP):** < 2.0s on 4G (Web Vitals "Good" = 2.5s)
- **Cumulative Layout Shift (CLS):** < 0.05 (Web Vitals "Good" = 0.1; tables must reserve space)
- **Interaction to Next Paint (INP):** < 200ms (Web Vitals "Good" = 200ms)
- **Total page weight:** < 350KB transferred for player pages, < 500KB for team pages

The static-site architecture of CFB Index is the major asset here — no client-side hydration delay, no API roundtrip. The main risks are: oversized images (use AVIF/WebP, lazy-load below-fold), web-font FOUT/FOIT (use `font-display: swap`), and inline `<script>` blocks that block parse (defer everything non-critical).

CFB Index should publish a perf budget in CI: any commit that pushes a page over 400KB or LCP over 2.0s on a synthetic 4G test fails the build.

---

## FotMob: What They Do That No CFB Site Does

FotMob (Norwegian-built, ~20M+ downloads, soccer-focused) is the most-cited gold-standard mobile stats experience. Distilling what they do that CFB sites don't:

1. **Sticky-top + sticky-left simultaneously** on league tables. Team crests on the left, stat headers on top, both stay locked while the body scrolls. This is the single most important structural choice.
2. **Crests not names** in the leftmost column when space is tight. The team identity is encoded in 24px, freeing horizontal real estate for stat columns. (For CFB: helmet logos work the same way.)
3. **Bottom-sheet competition/season picker** — a single primary "selector" button at the top of the page, tap to open a bottom sheet of options. No dropdown chevron buried in a header.
4. **In-table sparklines** for form (last 5 games). A 50×16px SVG sparkline per row, communicating trajectory at a glance. CFB Index already plans this via `31-chart-vocabulary.md`.
5. **Tap-to-expand row reveals match details** without navigation. The row expands inline; close button restores it. No page reload, no lost scroll position.
6. **Definition popovers on every advanced stat** (xG, xT, etc.) — tap-triggered, bottom-sheet style, one-tap close. CFB Index can do the same for EPA/A, ANY/A, etc.
7. **Tabular numerals consistently** across every stat block. Even the score on the home screen uses tabular numerals so a 2-1 doesn't shift width from a 4-7.
8. **No mobile column collapse**. Every stat is reachable via horizontal scroll, with sticky context. Trust the user to scroll; never hide.
9. **Search-within-table** for long lists (squad pages). Filter input above the table, real-time row hide.
10. **Performance**: FotMob's web rewrite (per Seven Peaks Software case study) hit ~80% Google PageSpeed improvement. Mobile-first build, aggressive caching, minimal JS on table pages.

The CFB convention — which almost every CFB site follows — is: horizontal scroll without sticky first column, hover-only tooltips, alphabetical default sort, column collapse without disclosure, no row drilldown, hover-only definitions. Doing the FotMob playbook on CFB data would be a real differentiator.

---

## TOP 10 MOBILE STATS-DISPLAY DOs AND DON'Ts

A distilled, actionable rule list for CFB Index implementation. Each item is cheap to do and high-leverage.

1. **DO** make the first column sticky-left on every table that scrolls horizontally. **DON'T** ever let the identifying column disappear during scroll.
2. **DO** enforce `font-variant-numeric: tabular-nums lining-nums` on every stat-bearing element. **DON'T** ship a table with proportional figures.
3. **DO** size every interactive element to ≥44px touch target. **DON'T** rely on visible row height as the click area.
4. **DO** make column headers tappable to sort, with a visible arrow affordance and `aria-sort`. **DON'T** rely on hover to surface sort, ever.
5. **DO** open a bottom-sheet on tap for advanced-stat definitions. **DON'T** require navigation to a glossary page.
6. **DO** show every column at every breakpoint, with horizontal scroll if needed. **DON'T** silently `display: none` columns on mobile.
7. **DO** default sort to the most-meaningful column (best stat for the page type). **DON'T** default to alphabetical-by-name on a stats site.
8. **DO** preserve scroll position across navigation (server-render whole tables; use `history.state` for any lazy-loaded content). **DON'T** lose the fan's place when they hit back.
9. **DO** pair color with shape, icon, or text for percentile/rank encoding. **DON'T** rely on color alone — it fails accessibility and fails greyscale.
10. **DO** budget every page to LCP < 2.0s on 4G and < 400KB transferred. **DON'T** ship a stats page heavier than a video.

---

## Sources

- [Sports-Reference In-Page Navigation Redesign](https://www.sports-reference.com/blog/2026/02/in-page-navigation-redesign-on-pro-football-reference/)
- [Sports-Reference Table Tips and Tricks](https://www.sports-reference.com/blog/2017/04/video-sports-reference-table-tips-and-tricks/)
- [ESPN College Football Stats](https://www.espn.com/college-football/stats)
- [CFBStats.com](https://cfbstats.com/)
- [TeamRankings College Football Stats](https://www.teamrankings.com/ncf/stats/)
- [Nielsen Norman Group — Mobile Tables](https://www.nngroup.com/articles/mobile-tables/)
- [Design Bootcamp — User-friendly Mobile Data Tables](https://medium.com/design-bootcamp/designing-user-friendly-data-tables-for-mobile-devices-c470c82403ad)
- [Datawrapper — Fonts for Data Visualization](https://blog.datawrapper.de/fonts-for-data-visualization/)
- [Fonts.com — Proportional vs Tabular Figures](https://www.myfonts.com/pages/fontscom-learning-fontology-level-3-numbers-proportional-vs-tabular-figures)
- [FotMob FAQ](https://www.fotmob.com/faq)
- [IXD@Pratt — FotMob Design Critique](https://ixd.prattsi.org/2021/09/design-critique-fotmob-android-app/)
- [Seven Peaks Software — FotMob Web Rewrite Case Study](https://sevenpeakssoftware.com/case-studies/app-for-football/)
- [Mobbin — FotMob iOS Screen Library](https://mobbin.com/explore/screens/2d3e370c-7780-4b5f-9f3c-133a91b6c063)
- [Ninja Tables — Sticky Headers vs Fixed Columns](https://ninjatables.com/sticky-headers-vs-fixed-columns/)
- [WebOsmotic — Mobile UX Tables Best Practices](https://webosmotic.com/blog/tables-best-practice-for-mobile-ux-design/)
