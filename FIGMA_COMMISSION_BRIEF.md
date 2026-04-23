# Figma Commission — CFB Index Player Page (First Crack)

**Product:** CFB Index — a college football rankings + fan-intelligence product.
**Page:** The quarterback player page, using CJ Carr (Notre Dame, 2025 Heisman contender) as the exemplar.
**What we're asking for:** A *first crack*, not a full page. Two modules, two breakpoints, all states, a token pass. ~1 week of focused work. If this lands, we commission the rest.
**Companion docs (attach these to the brief):**
- `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` — full 14-section strategy doc. Read it first.
- `output/site/players/cj-carr-4788.html` — the current page. This is what we're replacing.
- `research/player-page-worldclass-brainstorm-2026-04-22.md` — iteration research trail.

---

## 1. The thesis (internalize in one paragraph)

The page is three experiences stacked in order: **(1)** a 5-second vibe read — fans, the model, and the country form a feeling about the player instantly; **(2)** a traditional box-score foundation cleaner and more contextual than ESPN or Sports Reference; **(3)** an analytical exhibit behind progressive disclosure so casuals don't drown. **Fan Intelligence is the spine. Traditional stats are the foundation. Advanced stats are the exhibit.** Every module declares which of four reading tiers it serves (5s / 30s / 5m / deep-dive) and never mixes tiers on the same surface.

## 2. Non-negotiable constraints (the hard rules)

**Typography.** Single family: Inter Display for headings + UI, Inter for body. No second serif. Fluid `clamp()` scale. The *rhythm rule*: numbers are bright, tabular-nums, slightly heavier than their labels; labels are uppercase eyebrow, 11-12px, letter-spacing 0.08em, de-emphasized. Bright number, quiet label. Violating this is the single worst thing you can do.

**Color.** Exactly three semantic ramps plus one neutral scale. **No decorative color.** OKLCH-interpolated for perceptual continuity.
- Percentile: red `#d93a4a` → neutral `#6b7280` → blue `#1e6fd9`
- Belief: red `#c0392b` → neutral → green `#2d8659`
- Accolade gold: `#c9a227` base, `#e4c76b` highlight — reserved exclusively for honors
- Neutrals: 10-step OKLCH grey, dark-mode-first surface `oklch(0.18 0.01 250)`

All must pass WCAG 2.1 AA at every step (3:1 graphical / 4.5:1 text).

**Motion.** Four roles, exact durations:
- Reveal (drawer open): 240ms, `cubic-bezier(0.22, 1, 0.36, 1)`
- State change (pill select): 180ms, `cubic-bezier(0.4, 0, 0.2, 1)`
- Data entry (marker settle): 420ms total, 30ms stagger, ease-out-cubic
- Delight (rung-up ring): 800ms, `cubic-bezier(0.34, 1.56, 0.64, 1)` — max 3× per page

Linear easing forbidden. `prefers-reduced-motion` honored everywhere.

**Dark mode is the default.** Light mode supported but secondary.

**Mobile-first via container queries**, not viewport breakpoints. 44×44 minimum touch targets. Bottom sheets for every drawer. Thumb-zone CTAs. No hover-only affordances.

**Every module designs four states: empty, loading, partial, error.** Honest copy, never generic spinners.

## 3. What to design for the first crack

### 3.1 Scope (do only this — resist scope creep)

**Two breakpoints:** 1440 desktop, 375 mobile.
**Two modules, one exemplar (CJ Carr):**

**A) Hero Fingerprint** — 5-second read.
- Name, team (Notre Dame), position (QB), headshot slot, class year, jersey number
- Current rung tag ("HEISMAN FINALIST")
- Composite CFB Index QB Score (0-100)
- Fan Belief dial (label: "THE ROOM ON CARR")
- Heisman Heat (rank + trajectory spark + probability %)
- Respect Gap (fan − national consensus)
- Reality Gap (fan vs. structural model)
- Accolade ribbon strip (3 live honors with trajectory sparks)
- Optional "Canonized" ribbon (design but don't show on CJ Carr — show on a second frame with a retired-number alumnus placeholder)

**B) Player Standing** — the new crown-jewel module.
- **Rail:** full-width horizontal bar with 17 tick marks across 6 tiers (On-team / 2-deep / Starter / Recognized / Elite / Apex). Gold marker at current rung (R15 — Heisman finalist). Ghost marker at last season's rung. Current rung name in large type above marker.
- **Tier pills:** six pills below the rail. Active pill solid, others outlined. Tapping a tier zooms the rail into that tier's rungs with names.
- **Rung drawer** (opens on tapping current marker): "Why he's here" / "What moves him up" / "What moves him down" / trajectory sparkline / peer strip (4 players at same rung).
- **Accolade tabs** (nested below the rail): Heisman / Davey O'Brien / Manning / Unitas. Design *Heisman* tab fully; stub the others with the same grammar.
- Inside Heisman tab: left ladder (Watch → Conf → AA → POTY sub-rungs), middle three probability tiles (Win · Finalist · Ballot), right "What needs to happen" narrative block, and the **Selector Grid** below (pill grid of AA selectors, gold/silver/HM/empty).

### 3.2 Variant board (required)

A separate frame showing Player Standing rendered at **five rung extremes** so we can see the module flex across the whole roster:
1. **R00 Walk-on** (deep empty state, honest copy)
2. **R03 Backup** (minimal data)
3. **R06 Starter** (mid-data — the majority case)
4. **R12 All-American** (loaded)
5. **R15 Heisman finalist** (the CJ Carr case)

This is how we know the module isn't just built for stars.

### 3.3 States board (required)

For both Hero Fingerprint and Player Standing, show:
- **Empty** — e.g., Signature Story placeholder on a freshman backup
- **Loading** — shape-accurate skeletons, not spinners
- **Partial** — some data, honest placeholders for the rest ("Snap data unavailable for G5 games this week")
- **Error** — plain English, retry, contact

### 3.4 Tokens pass (required)

A single token page with:
- Type scale (five steps via `clamp()`)
- Three color ramps with every step swatched and labeled with OKLCH + hex
- Neutral 10-step grey scale
- Motion token table (four roles, durations, easings)
- Elevation (we use 3 levels, not more)
- Radius (8/12/16, nothing else)

### 3.5 Primitives pass (required)

All ten reusable atoms, each with desktop + mobile + loading + empty + error:
1. Percentile Bar (Savant-style)
2. Belief Dial
3. Trajectory Spark (44px mobile, 32px desktop)
4. Eyebrow → Number → Narrative card block
5. Drawer
6. Tab Bar (≤4 tabs, scroll-snap on mobile)
7. Chip (three sizes × neutral/positive/negative)
8. Pill Comparator
9. Selector Grid
10. **Standing Rail** (17-tick, the new one)

## 4. What *not* to do (anti-brief)

Hard no on any of the following:
- Carousel hero. ESPN/247 do it. It looks dated.
- Radar chart anywhere. Radars lie about data.
- Decorative gradients as backgrounds. Our gradients encode data only.
- Drop shadows for style. Shadows only for elevation hierarchy.
- "Hero scroll reveal" theatrics à la Awwwards-winning sports pages. Gorgeous, but 15 seconds to reach a stat — wrong for a data product.
- Second typeface. One family.
- More than three colors. Three ramps, one neutral scale, period.
- Icon sets unless functional. No decorative glyphs.
- Any stat displayed as a bare number without context (rank / percentile / cohort required).
- Mobile-as-afterthought. If mobile isn't great, nothing is great.
- Hover-only tooltips or drawers.
- Generic spinners or "No data available" copy.

## 5. Reference palette (internalize, don't copy)

**Borrow from:**
- **Baseball Savant** — the red→grey→blue percentile pill. This pattern is fluent to every sports-literate fan. Don't redesign it; reuse the idiom.
- **Apple Sports + Fitness** — number-first hierarchy, one huge number instead of twelve small ones, achievement-ring motion.
- **Linear / Raycast** — restraint, density without clutter, every pixel earning its place.

**Don't borrow from:**
- ESPN (tile-wall overwhelm)
- 247Sports (ad-dense flex-dump)
- Awwwards sports-page winners (showy, slow, unhelpful)

## 6. Content (use real copy, not lorem)

Use real CJ Carr content from the current page (`cj-carr-4788.html`). If you need fields we don't have, invent plausible ones and flag them with a `[placeholder]` marker so we can wire data. Numbers should look realistic for a P4 starting QB having a Heisman-level season (65-70% completion, 0.25-0.32 EPA/dropback, etc.).

## 7. Figma file structure (deliver in this shape)

- **Page 1 — Principles.** One-screen summary of the 4-tier reading ladder, the rhythm rule, color semantics, motion grammar, state matrix.
- **Page 2 — Tokens & primitives.** §3.4 + §3.5.
- **Page 3 — Hero + Player Standing.** The crown jewels. Desktop 1440 and mobile 375 side-by-side. Clean, final-quality.
- **Page 4 — Standing variants.** The five rung extremes from §3.2.
- **Page 5 — States.** Empty / loading / partial / error for both modules.
- **Page 6 — Scratch.** Anything else you explored, rejected directions, options considered. We want to see the work.

## 8. Review criteria (how we'll judge the first crack)

We'll ask six questions when reviewing. Design to these.

1. **The 5-second test.** If a fan sees only the Hero Fingerprint and nothing else, do they leave with a clear feeling about CJ Carr? Can they name his tier of player and the vibe around him?
2. **The walk-on test.** Does the Standing module have dignity when it shows a scout-team player with no honors? Or does it feel punitive?
3. **The rhythm test.** On any module, are the numbers brighter than their labels? If not, you haven't internalized the rhythm rule.
4. **The mobile test.** Does the 375 version feel equivalent to the 1440 version in information and beauty? Or is it a compressed afterthought?
5. **The color-audit test.** Can you point to every colored pixel on the page and name which of the three ramps (or the neutral scale) it came from? Any pixel you can't trace to a ramp is a bug.
6. **The motion test.** Every animation named and matched to one of the four motion roles with its exact duration and easing?

## 9. Iteration plan after this crack lands

- **Stage 2 (week 2-3):** Apply the established system to remaining modules — The Room on [Player], Signature Story, Current Season Production, Advanced Savant card, Splits, Peer Comparator, Supporting Cast, Bio/Recruiting/Transfer/Roster.
- **Stage 3 (week 4):** Full page flow at 1440 / 768 / 375. Scroll interaction. Sticky subnav behavior. Sub-route states (filter combos, tab selections).
- **Stage 4 (week 5+):** Polymorphism — WR, DB, OL, K/P tab sets for Accolade tabs. Career-retrospective Standing variant for alumni.

## 10. Questions to answer back to us before starting

1. Confirm: dark-mode-first, OKLCH ramps, WCAG 2.1 AA at every step. Understood?
2. Confirm: two breakpoints (1440 + 375), container-queries driven not media-queries driven. Understood?
3. Any reference pages you want to propose we add to §5 (positive or anti-example)?
4. Any primitive in §3.5 you think is over/under-specified?
5. Timeline check: is one week realistic for §3.1-§3.5?

---

**The one sentence to hold onto:** Make a page where a casual fan gets a feeling in 5 seconds, a pro finds every stat they want behind progressive disclosure, and every pixel can be traced back to a rule.
