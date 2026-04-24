# Figma Commission — Stage 3: Full Page Flow

**Status going in:** Stages 1 and 2 shipped clean. Ten modules live, token-disciplined, container-query responsive, each with a 4-state matrix. The design system is frozen. Stage 3 assembles those ten modules into the actual player page and designs the connective tissue: page flow across three breakpoints, scroll interaction, sticky subnav, sub-route states.

**What we are NOT doing in this stage:** Re-opening any module design, adding new primitives, or revisiting token decisions. If a module needs a tweak to work at page scale, flag the tweak — don't silently redesign.

**Companion docs:**
- `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` — canonical strategy.
- `FIGMA_COMMISSION_BRIEF.md` + `FIGMA_COMMISSION_BRIEF_STAGE2.md` — Stage 1/2 briefs (constraints still apply).
- Latest locked delivery — reference implementation.

---

## 1. Scope

### 1.1 Three breakpoints

Stage 1 and 2 locked 1440 desktop + 375 mobile. Stage 3 adds **768 tablet** as the third breakpoint — one page layout, three container widths. Same system rendered at different sizes, not three designs.

### 1.2 The full page at 1440 / 768 / 375

All ten modules assembled in the locked page order (§6 of Stage 2 brief):

1. Hero Fingerprint
2. Player Standing
3. The Room on [Player]
4. Signature Story
5. Current Season Production
6. Advanced Savant Card
7. Splits
8. Peer Comparator
9. Supporting Cast
10. Bio / Recruiting / Transfer / Roster

Every module renders at every breakpoint. Container queries on each module handle their internal responsive behavior; the page frame handles the assembly.

### 1.3 Sticky subnav

A horizontal nav rail that sticks to the top of the viewport after the Hero scrolls off. Structure:

- Left: player identity strip (monogram + name + team + position), compact
- Center: section anchors — Standing / Room / Story / Production / Savant / Splits / Peers / Cast / Bio — each clickable, current-section indicator
- Right: a "jump to top" control

Behavior:
- Sticky only after Hero exits viewport. Not sticky from page load.
- Current-section indicator updates via IntersectionObserver as user scrolls through modules.
- Click on anchor scrolls to module with a Reveal-motion-token-timed smooth scroll (240ms cubic-bezier(0.22, 1, 0.36, 1)), respecting prefers-reduced-motion.
- Collapses on mobile (375) into a horizontal scroll-snap strip of chips — anchors reorder by scroll distance, current one always visible.
- Backed by the Tab Bar primitive where possible. If that doesn't fit, propose a subnav primitive and design it with the full states matrix.

### 1.4 Scroll interaction

No scroll theatrics (no parallax, no fade-in-on-enter, no cinematic reveals). This is a data product; scroll is transport, not entertainment. What Stage 3 DOES design for scroll:

- Section entry uses the Data Entry motion token (420ms, stagger 30ms) only for data-viz elements that have a settling animation (percentile bars filling, trajectory splines drawing). Prose and numbers appear static. Max one such animation per module.
- Subnav transitions between "not-sticky" and "sticky" states use the State motion token (180ms).
- Loading states stream in module-by-module if the page data is lazy-loaded (design the skeleton-to-loaded transition).

### 1.5 Sub-route states

Modules with internal interactivity (Splits tabs, Bio tabs, Player Standing tier pills + rung drawer, The Room cohort pills, Current Season opponent-adjusted toggle, Savant cohort filter, Peer Comparator search) need URL-state representations so a user can link to "Carr's down-distance splits" or "Carr's recruiting tab" directly.

Design the URL parameter shape for each interactive module:

- `?standing=R15` (current rung drawer open on R15)
- `?splits=down-distance` (Splits deep drawer, down-distance tab)
- `?bio=recruiting` (Bio tab = recruiting)
- `?room=rivals` (The Room, rivals cohort active)
- `?savant=g5` (Savant, G5 cohort)
- `?peers=search:mccarthy` (Peer Comparator with search query)

Deliver a sub-route states page showing 4-6 representative URL combos, each rendered to confirm the interactive state loads correctly from URL.

## 2. Breakpoint discipline

- **Container queries only.** Page frame defines `container-type: inline-size` on the content column; modules adapt to their slot width. If a module needs to reflow at 768 vs 1440, use its own internal `@container` rules. The page-level CSS should never contain `@media` for layout.
- **Zero token forks.** Same `--fs-*`, `--space-*`, `--motion-*`, and color semantics at every breakpoint.
- **Page-level padding:** `--space-12` at 1440, `--space-8` at 768, `--space-4` at 375 — via a single container-query rule on the page wrapper, not per-viewport overrides.

## 3. Mobile specifics

- Sticky subnav collapses to horizontal-scroll chips (44×44 touch targets held).
- Hero compresses to single-column stack (already done at 375 in Stage 1).
- Standing Rail tick density drops to every-other below 600px (already done).
- Every module should be inspectable in one vertical scroll per module — no horizontal scrolling except inside the subnav chip strip and the Savant metric row if needed.
- Bottom-sheet pattern for any drawer that opens on tap (already the discipline).

## 4. States at page scale

Three new page-level states to design:

- **Page loading:** shape-accurate skeleton of all 10 modules in the scroll position. Subnav renders as static text, not interactive.
- **Page partial:** some modules loaded, others skeleton. Each module handles its own loading internally; page frame coordinates.
- **Page error:** if the player ID is invalid, show a "player not found" page that matches the system visually (same surfaces, same typography). Not a generic 404.

## 5. Deliverables (append to existing Figma file)

- **Page 10 — Full page flow.** Three vertical columns: 1440 / 768 / 375, full page height, all 10 modules.
- **Page 11 — Sticky subnav.** States (not-sticky / sticky / mid-transition), desktop + mobile variants, anchor-selected vs unselected.
- **Page 12 — Sub-route states.** 4-6 representative URL combos rendered.
- **Page 13 — Page-level states.** Loading / partial / error.

## 6. Anti-brief reminders

- No parallax. No cinematic scroll reveals. No "big number grows on scroll" effects. No horizontal-scroll narrative sections.
- No new primitives unless the subnav forces one, in which case design its full states pass.
- No module-level redesign hidden inside "page-flow adjustments." If a module needs a change, flag it.
- No font scaling on scroll (type scale is fluid via clamp, not scroll-driven).

## 7. Review criteria (add to Stage 1/2 tests)

**The scroll-to-signal test.** From page load, how many seconds does a fan take to hit each reading tier? 5s on Hero, 30s on Standing + Room + Production + Splits-headline, 5m on Signature Story + Savant + Peer + Splits-deep, deep on Supporting Cast + Bio. If the page-order timing is off, reorder or compress before shipping.

**The thumb test on 375.** Can a user hit every interactive element with a single thumb on a 6" phone? Subnav chips, tab bars, pills, drawers — all thumb-zone or obviously reachable by repositioning.

**The link test.** Can you copy-paste the URL for any interactive state and have the page load exactly there? If no, sub-route state design failed.

**The subnav test.** At mid-page scroll, can the user tell (a) where they are in the 10-module flow, and (b) how to jump to any other section? If not, subnav state is wrong.

## 8. Timeline

One week. Days 1-2: full page flow at all three breakpoints. Days 3-4: sticky subnav with states. Day 5: sub-route states + page-level loading/error. Commit per deliverable so audit is incremental.

## 9. Questions to answer back

1. Does the Tab Bar primitive stretch to serve as the sticky subnav, or do we need a new Subnav primitive? Name it before building.
2. Any module that, at 768 or 375, needs a container-query rule it doesn't currently have? Flag now, add to the module's Stage 2 file — don't fork into a "mobile variant."
3. Any sub-route URL shape in §1.5 that's semantically wrong or redundant? Propose alternatives.

---

**The one sentence:** Assemble the ten locked modules into one page that reads top-to-bottom at three breakpoints, with a subnav that tells you where you are and sub-routes that let you share exactly what you're looking at.
