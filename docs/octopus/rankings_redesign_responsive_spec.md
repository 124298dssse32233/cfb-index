# Rankings Redesign — Responsive & Breakpoint Spec

**Authored 2026-06-08.** How every surface reflows across screen sizes — the thing the fixed-width
mockups (390px phones, 1280px desktop) can't demonstrate. Pairs with the
[component spec](rankings_redesign_component_spec.md) and `cfb-tokens.css` breakpoints. Philosophy:
**mobile-first + progressive enhancement** — the 390px layout is authored first and *enhances up*; it is
not a desktop layout squeezed down.

---

## Breakpoints (from `cfb-tokens.css`)
| Token | Width | Role |
|---|---|---|
| `--bp-mobile` | 390px | phone (authoring baseline) |
| `--bp-tablet` | 768px | tablet / large phone landscape |
| `--bp-desktop` | 1024px | desktop nav appears |
| `--bp-wide` | 1280px | the "analyst" density |

**Author at 390 first**, add `min-width` enhancements at 768 / 1024 / 1280. Prefer **container queries**
(`container-type:inline-size` on module wrappers) over viewport queries so a module reflows by *its own*
width — the same card works full-bleed on mobile, 3-up on desktop, or embedded.

## Fluid foundations (between the breakpoints)
- **Type:** `clamp()` scales already baked into the tokens (`--fs-display`, `--fs-h1`, `--fs-h2`); body/UI sizes are fixed steps. Headlines use `text-wrap:balance`.
- **Spacing:** the 4px grid is fixed; gutters step at breakpoints (16px mobile → 24–26px desktop), not fluid.
- **Grid:** modules use `repeat(auto-fit, minmax(…))` or container queries, not hard-coded column counts.
- **Touch vs pointer:** hover effects gated behind `@media (hover:hover)`; targets stay ≥48px even on desktop; the command palette (⌘K) is pointer/keyboard, the bottom tab bar is touch.

---

## Main board `/rankings/` — the load-bearing reflow

| Zone | 390 (phone) | 768 (tablet) | 1280 (desktop "analyst") |
|---|---|---|---|
| **Nav** | bottom tab bar + sticky masthead | bottom tab bar | top `.nav` in masthead, no bottom bar |
| **Finding** | one-line banner | one-line banner | one line, inline with dateline |
| **Primary viz** | **Signal Stack** (swipeable story cards) | Signal Stack OR a compact bump | full-width **overtake-bump chart** |
| **The board** | **card-feed** (one team = one card; rank · team · one dominant number · belief chip; tap → drawer) | hybrid: card-feed widens, 2 stat columns appear | **dense KenPom table** — inline-rank columns (Power·rk, Off·rk, Def·rk, Résumé·rk, SoS, Tri-Rank, CFP%), sticky team-name spine, sortable headers |
| **Modules** (Room, Report Card, Movers) | stacked, lazy on scroll | 2-col grid | **right rail** beside the board |
| **Filters** | thumb-zone bottom strip → full-screen Popover sheet | chip row above board | inline chip row + lens tabs in the control bar |
| **Compare** | bottom-sheet tray (pick 2) | side-by-side sheet | side panel |

**The board is the hero at every size** — #1 sits directly under the masthead; the finding is one line, the
Signal Stack/bump sits *below* the top of the list, never in front of it. Card-feed ↔ table is the central
enhance-up: same data, re-authored, not a squeezed grid (never `display:block` a `<table>`; wrap the real
table in `role="region" tabindex="0"` for keyboard scroll). Deep board (rows 26–668) is `content-visibility`
lazy at all sizes.

## Team dossier `/teams/<slug>` (Profile)
- **390:** single column; sticky identity strip condenses on scroll; modules stack (Tri-Rank → key stats → fingerprint → season arc → The Room → playoff path → accountability → CTAs). Fingerprint peer-toggle is a segmented control.
- **768:** the hero goes 2-col (identity | key stats); fingerprint + season-arc can sit side-by-side.
- **1280:** 2–3 col grid; the hero is a full band; rivalry/accountability modules promote into the rail. Charts get more width (season arc + calibration breathe).

## Conference `/conferences/<slug>`
- **390:** board-first card-feed scoped to the conference; the title-race 2-up; stat strip 4-up (may wrap to 2×2 on the narrowest); The Room scoped to members below.
- **768/1280:** the scoped board becomes the dense table with the conference-native columns (Record · ATS · Wins-vs-Market · Recent Form); title race + bid math move to a rail.

## The Bridge `/bridge`
- **390:** division selector full-width (5 chips), spectrum SVG full-width (it's `viewBox`-scaled — already fluid), spotlight card, matchups stacked.
- **768/1280:** spectrum gets more height (taller lanes, clearer overlap band); spotlight + matchups can sit beside the spectrum; the rank-reference ticks on the FBS lane get more room for labels.

## Compare `/compare`
- **390:** vs-header split; sim bar; winner-per-row stat table; fingerprint dumbbells stacked; rooms 2-up.
- **768/1280:** wider dumbbells (the gap is more legible); stat table + fingerprint can sit in two columns; add a third "pick another team" column.

## The Room `/the-room`
- **390:** mood gauge hero; vibe shifts list; respect-gap 2-col; rival heat; civil wars; provenance footer.
- **768/1280:** modules become a masonry/3-col grid; the mood-by-week sparklines widen; vibe shifts can show more entries.

## Report Card `/the-model/report-card`
- **390:** hero stat trio; calibration; accuracy; ledger; poll dot plot — all stacked, each chart full-width (`viewBox`-scaled).
- **768/1280:** calibration + accuracy side-by-side; the poll dot plot widens (the small Brier gaps get more pixels); ledger in a 2-col grid.

## Archive snapshot `/archive/<season>-week-<n>` (retrospective)
- All sizes: **frozen** — no live strip/pulse/vibe. The overtake-bump scrollyteller + the Model Report Card ("said vs happened") are the focus. Same reflow as the board minus the live modules.

---

## Per-breakpoint quality gates
- **No CLS at any width:** every `content-visibility` chunk, chart, and image carries explicit
  `contain-intrinsic-size` / width-height. Charts are `viewBox`-scaled SVGs (intrinsically fluid).
- **Perf budget holds at all sizes:** FCP < 1.5s, INP < 200ms, JS < 50KB, critical CSS < 10KB, Lighthouse ≥ 95.
- **Render correctly at 390 / 768 / 1280** (the design-system mandate) — plus spot-check 320 (small phone) and
  430 (large phone) for the card-feed, and 1024 for the nav switchover.
- **Reduced-motion:** the card-feed↔table and Signal-Stack↔bump transitions are layout (CSS), not animation;
  the View-Transition re-sort and scroll reveals are enhancement-only and no-op under `prefers-reduced-motion`.
