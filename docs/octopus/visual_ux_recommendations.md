# Visual & UX Recommendations — Prioritized

_Synthesized 2026-05-18 from a comprehensive audit of `CFB_INDEX_VISUAL_SYSTEM_CONCEPT.md`, `CFB_INDEX_IDENTITY_PRODUCTION_PLAYBOOK.md`, `CHATGPT_VISUAL_SYSTEM_RUNBOOK.md`, all 15 `docs/design-system/*.md` files, `PLAYER_PAGE_WORLD_CLASS_BRIEF.md`, `TEAM_PAGE_WORLD_CLASS_BRIEF.md`, plus spot-check of the live site at `origin/published`. The agent extracted 250+ rules; this doc collapses them into actionable priorities._

## What's already built (no action needed)

✅ **Tier-1 art system shipped 2026-05-18** (PR #131) — 36 bespoke PNGs deployed + URL helpers + hub wiring:
- 18 archetype totems on N° 04 Taxonomy section archetype cards
- 8 modifier glyphs on the modifier chip strip
- 8 section rubrics on N° 01–N° 08 eyebrow headers
- Author portrait + totem master plate available via helpers

✅ **Team logos on team pages** (PR #133) — 664 teams, deterministic URL emit + onerror fallback. Applies to both legacy reporting.py and team_pages/ renderer.

✅ **Tabular numerals + reduced-motion guard** (PR #134) — site-wide via `_DESIGN_SYSTEM_BASELINE_CSS_BLOCK`.

✅ **Confidence chip prototype** (PR #137 player Heisman Lens + PR #140 Heisman Tracker hero) — locked spec from `docs/design-system/33-confidence-signaling.md` wired into the two highest-traffic stat surfaces.

✅ **Comprehensive OG/twitter meta sweep** — every public render surface now has og:image / og:title / og:description / twitter:card. PRs #99/#103-#107/#114/#116/#121 + #141 (6 missing pages) + #142 (editions article+TOC) + #146 (methodology+freshness) + #148 (editions homepage + 3 boards) + #149 (dynasty heatmap) + #150 (countdown+today+recruit) + #151 (vibe-shifts).

✅ **SEO foundations** (PR #145, #153) — robots.txt + sitemap.xml at site root. Sitemap includes 18 top-level landing pages plus every site-eligible team URL (FBS 0.7 priority weekly, non-FBS 0.5 monthly). Per-player + per-archive deferred to Phase 2.

✅ **A11y skip-link** on profiled team pages (PR #115)
✅ **Label honesty layer** — every season label tracks the snapshot's actual data season (PR #84/#88/#91/#92/#93)
✅ **Heisman 2025 data pipeline** unblocked (PR #102 + #123)
✅ **Chart vocabulary audit** (PR #139) — verified inventory vs `docs/design-system/31`. 8 APPROVED, 2 FORBIDDEN (legacy vertical bars in reporting.py), 2 AMBIGUOUS. See `docs/octopus/chart_vocabulary_audit.md`.
✅ **Visual-system implementation plan** (PR #136) — 8-phase roadmap. See `docs/octopus/implementation_plan_visual_system.md`.

## Top 5 — highest leverage, can ship autonomously

These are the items where the docs lock a clear answer + I can ship without editorial judgment + impact is visible.

### 1. **Team logos on team pages** (1-day work, huge visual win)

Today the 664 team logos at `/assets/team-art/<slug>/logo_primary.png` appear only in the rankings table. Team pages themselves have no logo — you land on `/teams/alabama.html` and there's no Alabama 'A' anywhere except in the OG share card.

**The fix:** add a 64px logo to the team-page hero (legacy renderer + team_pages module). Same `<img>` pattern already used in rankings. Conservative: don't change layout, just inject the logo before the H1.

**Why it ships safely:** assets exist, file paths are stable, fallback to `display:none` on error already exists in rankings markup.

### 2. **Tabular numerals enforcement on stat-class elements** (2-hour work)

The design tokens spec (`docs/design-system/00-tokens.md`) locks tabular numerals as the cardinal typography rule. The CSS exists in tokens but isn't enforced consistently — many stat cells render with proportional digits which makes tables jitter.

**The fix:** add `font-variant-numeric: tabular-nums` via a targeted CSS rule on `.metric-cell`, `.stat-card strong`, `.csp__stat-value`, and any `td.metric-cell` selector. One CSS rule, applied site-wide via `cfb-index.css`.

**Why it ships safely:** purely additive CSS, no markup changes, zero functional risk.

### 3. **Confidence chip pattern** on player + team pages (1-day work)

`docs/design-system/33-confidence-signaling.md` locks the three-band signaling: high (✓ green), medium (• amber), low (? grey italic), insufficient (suppress). The site has NO confidence signaling visible today — every number reads as equally trustworthy.

**The fix:** add `_render_confidence_chip(level)` helper + thread `confidence_band` field through 2-3 highest-traffic stat surfaces (player Heisman lens, team mood card, signature story). Don't try to retrofit every stat — pick the surfaces where data quality varies most.

**Why it ships safely:** chip is additive, doesn't replace existing content. Insufficient-data suppression already happens elsewhere (PR #84/#88/#91); this just makes confidence visible.

### 4. **Cmd-K wire-up on global header** (10-min work, awaiting Window B's push)

Window B's PR #122 ships the Cmd-K overlay (CSS + JS + 9,253-item search index) but doesn't wire it into any page. Per Window B's hand-off note, the global header `<link>` + `<script>` + visible trigger button is "Window A's lane."

**The fix:** when PR #122 lands, add three lines to the head of every page (via global head helper) and one button to the topbar. Cmd-K/Ctrl-K already works via keybind; the button makes it discoverable for non-keyboard users.

**Why it ships safely:** trivial mechanical change; degrades gracefully (if JS fails, button still navigates or does nothing).

### 5. **Reduced-motion guard on existing animations** (30-min work)

Spot-check of `origin/published` HTML shows several `@keyframes` / `transition:` declarations but no `@media (prefers-reduced-motion: reduce)` overrides. The design system locks reduced-motion as non-negotiable.

**The fix:** append a global reduced-motion media query to `cfb-index.css` that collapses all transitions to `0.01ms` and disables keyframe animations. One CSS block, site-wide.

**Why it ships safely:** prefers-reduced-motion only activates for users who opted in. Standard accessibility pattern.

---

## Tier 2 — substantial work but high value (need editorial sign-off)

These are bigger projects. They require user judgment on scope/copy but have clear specifications in the docs.

### A. **Player Hero Fingerprint redesign** (1-2 week project)
The `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` locks a 3-column "vibe cells" hero pattern. Current player pages have a basic hero. Substantial layout work + needs design pass to confirm proportions on mobile.

### B. **Player Standing 17-rung ladder** (1-week project)
The standing ladder (Walk-on → ... → Heisman Winner) is locked in the brief but doesn't exist in the renderer. Needs CSS for the rail visualization + Python logic to compute rung position from accolades.

### C. **Game-log table on player pages** (1-week project)
ESPN data-parity gap. Brief locks the format (game-by-game stat rows with opponent + result + key stats). Needs schema confirmation that we have the data and a renderer.

### D. **Per-team helmet silhouettes** (production sprint, 1-2 days art + 4 hrs wire-up)
Tier-2 of the visual concept doc — 133 FBS helmet silhouettes in team primary color. Use the same Art Director GPT pattern that produced Tier-1. The wire-up is easy (replace text team chips with helmet silhouettes); the bottleneck is the 133-image production.

### E. **Rivalry coin marks** (production sprint, half-day art + 1-hr wire-up)
12 coin/seal marks per the concept doc. Same Art Director pattern. Wire into rivalry section cards on team pages + hub N° 05.

### F. **Editorial Receipt Pattern** (1-2 week project)
`docs/design-system/32-receipt-pattern.md` locks the inline citation system. AI editorial currently doesn't carry citations. Substantial Pattern C prompt revision + citation_critic validation + footer renderer + DB migration for `editorial_citations` table.

### G. **Annotated chart vocabulary** (1-week project)
`docs/design-system/31-chart-vocabulary.md` locks 6 chart types + forbidden list. Current site uses some SVG charts but doesn't enforce the vocabulary. Audit existing charts → refactor to match (e.g. any vertical bar charts replaced with percentile-bar pattern).

### H. **Container queries for module responsiveness** (1-week project)
Design system locks container queries so the same FI card works at 100% phone width and 50% desktop. Current responsive layout is viewport-based. Refactoring touches every module's CSS.

---

## Tier 3 — aspirational (multi-month or strategic)

These are mentioned in the strategy docs but don't have ready specifications.

- **Per-player OG images** (need per-player generation pipeline; currently using site-default `og-image.svg`)
- **Weekly issue covers** (47/year; one risograph cover per edition per the playbook)
- **Weekly commiseration cartoons** (47/year; one halftone spot per edition)
- **Stadium silhouettes** (40-60 generic profiles per concept doc)
- **Editorial portrait library** (10-15 anonymous fan types: "The Dad at the Tailgate", "The Alumni Returner")
- **Field notes marginal illustrations** (X's & O's, blackboard diagrams)
- **Tradition illustrations** (30-40: Dotting the I, Enter Sandman, The Grove tailgate)
- **Historical moment illustrations** (Flutie Hail Mary, Bush Push, Kick Six rendered as engraving memory pieces)
- **Player Pass chart** (route/throw visualization; needs play-by-play data integration)
- **Custom display face licensing** (the playbook flags this as a moat-tier investment)
- **Full Player Page world-class spec implementation** (the brief outlines 8+ modules; touches every player page)

## Tier 4 — won't ship without explicit decision

These are aspirational but need brand voice / editorial judgment that I shouldn't make autonomously.

- **Color token migration** — `docs/design-system/00-tokens.md` defines a v5 OKLCH ramp; current site uses older hex tokens. Migration touches every page's CSS. Need confirmation that v5 ramps are the brand-current direction.
- **Nav structure consolidation** — 7+ page types have different top-nav link sets. Some divergence is intentional (editorial vs product surfaces). Needs brand voice decision on what to unify.
- **Editorial voice critic** for AI-generated copy — concept doc references this but no spec exists for what passes/fails.

---

## Recommended autonomous next-session ordering

If you tell me "keep going on visual/UX work":

1. **Team logos on team pages** (Top-5 #1) — highest visible impact for least effort
2. **Tabular numerals enforcement** (Top-5 #2) — fixes table jitter site-wide
3. **Reduced-motion guard** (Top-5 #5) — accessibility win, 30-min ship
4. **Cmd-K wire-up** (Top-5 #4) — when Window B's PR #122 lands
5. **Confidence chip prototype on player Heisman lens only** (Top-5 #3, narrow scope) — proof-of-concept; expand to other surfaces in a follow-up

That's a half-day to full-day of work for substantial visible site improvement.

## Recommended user-input items

If you can answer a couple questions, two more Tier-1 items unlock:

- **Production sprint for Tier-2 helmet silhouettes?** — Concept doc has the spec. 133 PNGs at ~2-4 hrs of ChatGPT Art Director work + curation per the runbook. After that, replacing text team chips with helmet silhouettes is mechanical.
- **Production sprint for Tier-2 rivalry coins?** — 12 coins at ~1-2 hrs. Wires into N° 05 Rivalry section and team-page rivalry cards.

Both follow the established Art Director GPT workflow you locked in `CHATGPT_VISUAL_SYSTEM_RUNBOOK.md`.

## Carry-forward to next session

- Tier-2 helmet silhouettes (waiting on production sprint)
- Tier-2 rivalry coins (waiting on production sprint)
- Tier-2 archetype migration diagrams (5 images, halftone engraving — waiting on production)
- Per-player OG image generation (Tier-3, deferred until weekly-cover cadence is established)
- Color token migration to OKLCH v5 ramps (Tier-4, needs brand voice confirmation)
