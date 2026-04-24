# Figma Commission — Stage 2: Remaining Player Page Modules

**Status going in:** First-crack scope (Hero Fingerprint + Player Standing + tokens + primitives + variants + states) landed clean at v5. The design system is locked. Stage 2 applies that system to the remaining modules.

**What we are NOT doing in this stage:** Re-opening token decisions, motion grammar, color semantics, type scale, or container-query architecture. Those are frozen. If you think something in the system needs to change, flag it — don't silently fork.

**Companion docs (read first):**
- `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` — full strategy, §7 Player Standing spec, §8 Design Craft
- `FIGMA_COMMISSION_BRIEF.md` — Stage 1 brief (constraints are the same)
- v5 delivery — the reference implementation for this stage

---

## 1. The locked foundation (do not re-litigate)

- **Typography:** Inter Display (headings/UI) + Inter (body). Fluid clamp() scale — `--fs-display`, `--fs-h1`, `--fs-h2`, `--fs-body`, `--fs-meta`. Rhythm rule: bright tabular number, quiet uppercase eyebrow label. Never mix tiers on a surface.
- **Color:** 3 OKLCH ramps (percentile red→grey→blue, belief red→grey→green, accolade gold) + 10-step neutral. No decorative color. All WCAG 2.1 AA.
- **Motion:** 4 roles only — Reveal 240ms / State 180ms / Data entry 420ms / Delight 800ms. Exact easings from v5's theme.css. `prefers-reduced-motion` honored globally.
- **Responsive:** Container queries, not media queries. 44×44 touch targets. Bottom sheets for drawers on mobile.
- **Dark-mode first.** Light mode is secondary.
- **States:** Every module ships empty / loading / partial / error.

## 2. The four reading tiers (assign one per module)

Every module must declare which tier it serves and never mix.

- **5s (Vibe):** Hero Fingerprint (done). No new 5s modules in Stage 2.
- **30s (Gist):** The Room on [Player], Current Season Production, Splits headline.
- **5m (Investigation):** Signature Story, Advanced Savant, Peer Comparator, Splits deep.
- **Deep (Reference):** Supporting Cast, Bio/Recruiting/Transfer/Roster.

## 3. Modules to design — scope and tier

### 3.1 The Room on [Player] — 30s

Fan sentiment module. Belief dial (reuse primitive), cohort breakdown (own fans / rival fans / national / media), top quoted take, confidence score, sample size, trajectory spark across last 6 weeks. Cohort pills filter the dial. No text wall — one headline take, everything else visual.

### 3.2 Signature Story — 5m

One statistical fingerprint that defines this player's season. Algorithmically-surfaced (we'll wire the logic later; you design the display shell). For CJ Carr: "Best QB in football under pressure — 0.38 EPA/dropback when blitzed, #1 nationally, 92nd pct." Large number, one-paragraph narrative, supporting chart (simple line or bar, Savant color semantics), "vs cohort" comparison strip. Shape-accurate skeleton when we don't have enough data.

### 3.3 Current Season Production — 30s

The traditional box score, cleaner than ESPN/Sports Reference. Passing / rushing / misc in three columns on desktop, stacked on mobile. Each stat row: value, rank, percentile pill. Rank + percentile context on every number — never a bare stat. Opponent-adjusted vs raw toggle (chip pattern from primitives).

### 3.4 Advanced Savant Card — 5m

Baseball Savant tribute. Six advanced metrics (EPA/dropback, CPOE, pressure-to-sack, off-target %, under-pressure EPA, third-down EPA). Each with a percentile bar (the locked primitive). Card header names the cohort (P4 QBs, Week 12 update). One-line interpretation below each bar for the casual reader.

### 3.5 Splits — 30s headline / 5m deep

Headline row (30s): Home vs Away / vs P4 vs vs G5 / 1st half vs 2nd half / red zone — 4 split pairs max, each as a pill-comparator (the primitive). Click-through to 5m deep splits (tab-bar primitive): situational, down/distance, personnel, opponent tier. Pattern re-uses existing primitives — no new components.

### 3.6 Peer Comparator — 5m

Four peer players at the same rung (pulled from the Standing module's R15 peer strip as the default seed). Side-by-side column of the 6 headline stats with percentile bars. User can swap any peer via a pill search. Pill comparator primitive + small search input.

### 3.7 Supporting Cast — deep

Team context that explains the numbers. OL pass-protection grade, top-3 receivers with their own mini-fingerprints, play-caller identity, defensive coordinator name + scheme. This is the "why" behind the stats. Reference cards (primitive: eyebrow → number → narrative) in a dense grid.

### 3.8 Bio / Recruiting / Transfer / Roster — deep

Tabbed reference block. Bio (hometown, HS, measurables), Recruiting (247 composite, star rating, offer sheet), Transfer (portal status, prior schools if applicable), Roster (depth chart position, year, eligibility remaining). Tab bar primitive. Every field has a "—" fallback for missing data — no empty cards.

## 4. Breakpoints

Same as Stage 1: **1440 desktop + 375 mobile** via container queries. No new breakpoints. If a module needs a mid-width treatment, use container queries at the module level (600/720/900/1200px are the current precedent).

## 5. States

For each of the 8 modules above: empty, loading, partial, error. Lean on existing state patterns from Hero + Standing. Copy should be factual and forward-looking — the walk-on dignity bar applies to every module ("Snap data unavailable for G5 games this week" not "No data").

## 6. Page order on the player page

Fans read top-down. Order is load-bearing:

1. Hero Fingerprint (5s)
2. Player Standing (5s → 30s → 5m)
3. The Room on [Player] (30s)
4. Signature Story (5m)
5. Current Season Production (30s)
6. Advanced Savant Card (5m)
7. Splits (30s → 5m)
8. Peer Comparator (5m)
9. Supporting Cast (deep)
10. Bio/Recruiting/Transfer/Roster (deep)

Heaviest-signal surfaces first. Reference material last. Sticky subnav (design in Stage 3) will let pros jump.

## 7. Anti-brief (still applies)

No carousels. No radar charts. No decorative gradients. No drop shadows for style. No second typeface. No new colors. No icons unless functional. No bare numbers without context. No hover-only affordances. No generic spinners.

## 8. Content

Real CJ Carr data for every module. Plausible placeholder numbers for fields we haven't wired, flagged with `[placeholder]`. Don't invent narratives — use the factual shape ("Best QB in football under pressure" is real; verify EPA figures are P4-realistic).

## 9. Figma file structure (append to existing file)

Don't create a new file. Add pages to the existing Stage 1 Figma file:

- **Page 7 — Stage 2 modules.** All 8 modules at 1440 + 375. One section per module, stacked in the page-order from §6.
- **Page 8 — Stage 2 states.** Empty / loading / partial / error for each module.
- **Page 9 — Stage 2 scratch.** Rejected directions, options considered.

## 10. Review criteria

Same 6 tests from Stage 1, plus:

7. **The tier test.** Can you point to any module and name which of the 4 reading tiers it serves? Any module that mixes tiers is a bug.
8. **The reuse test.** Can every module be built from the 10 locked primitives (+ the variants already in Stage 1), or did you silently invent new ones? Any new primitive needs a written justification and a states pass.
9. **The page-flow test.** Read the 10 modules top-to-bottom on a 1440. Does a fan land on the right feeling at §1, know the lay of the land at §3, and reach supporting detail by §7 without fatigue?

## 11. Timeline

Two weeks. Week 1: modules §3.1 – §3.4 (Room / Signature Story / Season / Savant). Week 2: §3.5 – §3.8 (Splits / Peer / Supporting Cast / Bio). States can ship with each module or batch at end of Week 2 — your call.

## 12. Questions to answer back before starting

1. Any module in §3 where the scope is unclear or the wrong size for the tier it serves?
2. Any primitive from Stage 1 that needs extending, or any new primitive you're planning to introduce? Name it now, not after you've built it.
3. Any concern that the page-order in §6 will make a single module feel crowded or starved?

---

**The one sentence:** Apply the locked v5 system to 8 more modules, honor the 4 tiers, reuse primitives before inventing, ship with states.