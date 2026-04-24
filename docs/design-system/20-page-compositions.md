# Page Compositions

End-to-end compositions for desktop and mobile team pages. Defines module ordering, variant selection, responsive breakpoints, and state-resolver integration.

## Standard page composition (in-season, non-game-recap)

Desktop (1440px wide content column) top-to-bottom:

1. `TeamIdentityHeader` — full-width, persistent
2. `HeritageStrip` — thin, above fold
3. `StateOfTeamParagraph` — serif, ~72ch max
4. `MetricTileGrid` — 4 tiles horizontal
5. `ScheduleStrip` — horizontal game cards
6. `MoodSparkline` — thin, full-width under schedule
7. `ThisWeekCallout` — accent-bordered paragraph
8. `PulseModule` — full-width composite
9. `ChronicleModule` — mixed-width (hero + 3-col grid + full-width echo)
10. `RivalryCard` — full-width, featured rivalry (next week's if rivalry week; else next Tier-1 upcoming)
11. `SavantCard` — full-width, 13 percentile bars
12. `AspirationLadder` — compact vertical stack
13. `CFPEraView` — full-width trajectory chart + chapter index
14. `FeaturedHistoricalSeason` — link-out card (most recent defining season)
15. `ArchiveSeasonGrid` — 13 compact season bricks
16. `Footer` — methodology + sources + next update schedule

Mobile (390px viewport) stacks identically — all full-width. Most horizontal grids collapse to single column except where indicated.

## Component swaps per state

The state-resolver returns a state object:
```python
{
  "hero_module": "state_of_team",  # or "pulse" | "rivalry" | "heritage" | "cfp_projection" | "chronicle" | "schedule_next"
  "copy_tone": "coiled",
  "accent_color": "amber",
  "promoted_modules": ["rivalry_card", "this_week"],
  "demoted_modules": ["cfp_era_view"],
  "hidden_modules": [],
}
```

### `post-loss-sunday-monday` state

- Hero: `GameRecapHero` (game-recap mode for first 24 hours; standard state-of-team from 24-48h)
- `PulseModule` promoted to just below hero
- `ChronicleModule` keeps game-edition cards generated T+25-35
- `ThisWeekCallout` demoted below fold
- `AspirationLadder` demoted below fold (less salient post-loss)
- `RivalryCard` hidden if the game that was lost was a rivalry (that rivalry just happened)
- Accent color: red
- Copy tone: reckoning / wound

### `post-win-sunday-monday` state

- Hero: `StateOfTeamParagraph` (with post-win tone)
- `PulseModule` promoted (mood spike visible)
- `ChronicleModule` keeps game-edition cards; anomaly card prominent
- `AspirationLadder` promoted if the win unlocked a new rung
- Accent color: green (subtle) or amber (for upset wins)
- Copy tone: basking / euphoric (upset)

### `rivalry-week-friday` state

- Hero: `RivalryCard` (the upcoming rivalry) — promoted to top of scroll
- `ThisWeekCallout` expanded to fuller version with rivalry-specific stakes
- `PulseModule` shows rivalry heat comparison section prominently
- `ChronicleModule` flashpoint card takes hero position
- Accent color: amber
- Copy tone: coiled / anticipatory

### `dead-period-summer` state

- Hero: `HeritageStrip` (full expanded version, not compact)
- `OnThisDay` module promoted (if data exists for today's date)
- `PortalTracker` promoted to page-top
- `ScheduleStrip` hidden (no current schedule)
- `MoodSparkline` hidden
- `ThisWeekCallout` hidden
- `AspirationLadder` shown with preseason projection data
- Accent color: gray
- Copy tone: patient / reflective

### `selection-sunday` state

- Hero: `CFPProjection` card (full-featured with scenario math)
- Everything else demoted
- Accent color: navy
- Copy tone: held-breath

## Mobile adaptations

### Horizontal scroll (with snap)

- `ScheduleStrip` on mobile scrolls horizontally. Current week card uses `scroll-margin-inline: 50%` to center on load.
- `ChronicleModule` 3-col grid collapses to single column vertical stack.

### Grid-to-stack

- `MetricTileGrid` 1×4 → 2×2
- Pulse `__mid-grid` 2-col → 1-col
- Savant card percentile bars keep left label column but the bar gets more width.

### Typography scale

Tokens already specify `clamp()` for display sizes so they scale; specific step-downs:
- Hero `TeamIdentityHeader` name: 22 → 20px on mobile
- `StateOfTeamParagraph` headline: 22 → 18px
- Chronicle hero-card headline: 20 → 16px
- Everything else: held

### Touch targets

All interactive elements (schedule cards, season bricks, peer-toggle chips, aspiration rungs) minimum 44pt tap area. Metric tiles 48pt for frequently-tapped.

## Screenshot-native sizing

Every module should fit within a single portrait screenshot (390 × 844 iPhone Pro). Validated at build time:
- `TeamIdentityHeader` — fits
- `StateOfTeamParagraph` — fits (typically 400-500px tall)
- Pulse mood summary + trajectory — one screenshot
- Pulse event log — one screenshot
- Pulse takes — one screenshot
- Chronicle hero card — one screenshot
- Chronicle mid-grid cards — each one a screenshot
- Rivalry meta + trajectory — one screenshot
- Rivalry posture panels — one screenshot
- Savant card sections — each section one screenshot

Full page never intended to be a single screenshot.

## Program-tier swaps

`state_resolver` reads `profile.program_tier` and applies:

**Tier 1-2 (contenders):**
- CFP odds tile in metric grid
- CFP Projection module active
- `aspiration_ladder` uses contender rungs (CFP → semifinal → title game → champion)
- Chronicle observations framed as era-relative (vs. dynasty peaks)

**Tier 3-5 (mid P4):**
- Bowl odds tile replaces CFP odds
- Conference standings tile added
- Aspiration ladder uses conf-title + bowl rungs
- Chronicle framed as program-relative-progress

**Tier 6-10 (G5/non-contenders):**
- CFP odds tile hidden
- AP rank tile hidden if unranked
- YoY-wins-pace tile added
- Aspiration ladder starts at bowl eligibility and maxes at program-historic
- Chronicle framed as program-historic-progress
- Some rungs dimmed as "locked"

## Build-time rendering

Single entry: `python manage.py render-team <team_slug>`.

Pipeline:
1. Load `profiles/<slug>.md` (YAML + markdown)
2. Query current-season data from SQLite (team stats, schedule, opponent profiles)
3. Call state-resolver with date + outcome context → state object
4. Load generated narratives from `team_season_narratives` (regenerated nightly)
5. Load chronicle cards from `team_chronicle_observations` (regenerated weekly in-season, monthly offseason)
6. Render Jinja template passing all context
7. Write HTML to `output/site/teams/<slug>.html`
8. Generate share cards (PNG) via Pillow for each shareable module

## Static-site architecture

The entire page is static HTML + static CSS + static SVG + pre-rendered PNG share cards. No JavaScript required for rendering. Optional minimal JS (~200 lines total) for:
- Peer-toggle on Savant card (swaps pre-computed bar widths via data attributes)
- Schedule-strip horizontal scroll snap behavior on mobile
- Aspiration ladder tooltip on locked rungs

All JS is progressive enhancement. Core content renders with JS off.
