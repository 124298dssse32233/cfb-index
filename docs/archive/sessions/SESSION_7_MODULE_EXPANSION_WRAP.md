# Session 7 — Module Expansion Wrap

**Date:** 2026-05-22 (continuation of Session 6).
**Charter:** Continue closing brief-mandated team-page module gaps per `WORLD_CLASS_GAP_AUDIT_2026_05_22.md`. Driver mode: ship per audit priorities without permission-per-step.

## What shipped (commits in `master`)

| # | Module | Brief § | Commit | Surface |
|---|---|---|---|---|
| 1 | Season Standing 9-rung rail | §3.1 | `b4463e22c4c` | All 30 profiled teams |
| 2 | Program Prestige 7-tier bar | §3.2 | `606b22625e5` | All 30 profiled teams |
| 3 | Page Tone Strip (seasonal sentience visible) | Part III §32 | `8487596330a` | All 30 profiled teams |
| 4 | Program Trajectory chip | §11.4 | `42fc452a340` | All 30 profiled teams |
| 5 | Kickoff Countdown chip | §22.1 | `887b9678721` | All 30 profiled teams |
| 6 | Program Peer Comparator | §26 | `a7fbb607f0f` | All 30 profiled teams |

Plus the `texas-am` → `texas-a-m` slug-mismatch fix (DB used dashes between every letter); 30/30 profiled programs now render.

## What each does

### 1. Season Standing 9-rung rail (`team_pages/season_standing_rail.py`)
Team analog of the Player Standing rail. 9 rungs:
- R0 Sub-FBS → R3 Bowl eligible → R5 Top 15 → R6 CFP contender → R8 Title game → R9 National champion
- Placement cascade: CFP rank → AP → Coaches → 6+ wins → win-share
- Championship rung renders in accolade gold even when not current
- Empty state for preseason / no-games snapshots

### 2. Program Prestige 7-tier bar (`team_pages/program_prestige_bar.py`)
Slower-moving sibling. 7 tiers Regional → All-Time Great Era. Pulls from `profile.frontmatter.prestige_tier` override, else translates from internal `program_tier`. Renders historical-peak ghost segment with era label:
- Alabama: T6 Dynasty Active, peak T7 "2009-2020 Saban era — six titles, twelve straight top-5s"
- USC: T5 Blue Blood, peak T7 "2002-2008 Pete Carroll era"
- Florida State: T4 National Program, peak T7 "1987-1996 Bobby Bowden top-5 streak"
- Miami: T4, peak T7 "1983-2001 The U dynasty"
- Notre Dame, Ohio State, Clemson, Georgia: marquee peaks authored

### 3. Page Tone Strip (`team_pages/page_tone_strip.py`)
The state_resolver was computing `accent_key`, `anchor_variant`, `copy_tone` every render but nothing surfaced those signals. The strip now reads:
- `OFFSEASON · DEAD PERIOD · PATIENT · POST-WIN BASKING` (May, post-win)
- `EARLY SEASON · FRIDAY · ANTICIPATION` (Sept Friday)
- `RIVALRY PEAK · THURSDAY · HYPE · RIVALRY WEEK VS [OPP]` (rivalry week)
- `GAMEDAY · with pulsing live dot` (Saturday)
- `GAME RECAP MODE · with live dot` (post-final < 24h)

Body carries `data-page-tone` / `data-page-phase` / `data-page-anchor` / `data-in-season` so future CSS modules can swap based on the page's state. Includes subtle radial-gradient body tint per tone.

### 4. Program Trajectory chip (`team_pages/trajectory_chip.py`)
"Are we as good as we used to be?" answered in one chip:
- **RISING** "Climbing +2.5 rungs across the last 10 seasons."
- **DECLINING** "Slipping -1.0 rungs. Slope -0.38 rungs/year."
- **STEADY** "Holding the line. Slope doesn't tilt."
- **VOLATILE** "Wide swings. The standard deviation tells the story."

Computes per-season pseudo-rungs from arc_rows (title_won → title_game → cfp → AP → wins cascade). Slopes the last 10 years via least-squares regression. Includes inline sparkline SVG (chart-vocabulary.md compliant).

Synthetic verification: Alabama 2014-2024 → "Declining" (slope -0.38) — correctly reflects the post-Saban drift.

### 5. Kickoff Countdown chip (`team_pages/kickoff_countdown.py`)
Anchors every team page in calendar time:
- `OFFSEASON · 100 days · until kickoff · Sun Aug 30 · 17:00 UTC`
- `GAME WEEK · 3d 18h · vs Michigan · Sat 12:00 UTC` (green border)
- `GAMEDAY · 4h 15m · vs Texas · Sat 19:30 UTC` (amber border)
- `LIVE · Live now · vs Texas` (red border + pulse animation)

Required threading `start_time_utc` through the games query into the `GameResult` dataclass. Five modes drive distinct border-left colors so the chip's emotional register matches the moment.

### 6. Program Peer Comparator (`team_pages/peer_comparator.py`)
The static-attribute variant of Brief §26 Similarity Engine. Weighted similarity across 5 dimensions:
- +4.0 `program_tier` exact match
- +3.0 `prestige_tier` exact match (Brief §3.2)
- +2.5 `fan_archetype_dominant` match
- +2.0 conference exact match
- +1.5 `voice_register` match

Verified semantic quality:
- Alabama → Georgia / Ohio State / Clemson
- Notre Dame → Clemson / USC / Alabama
- Ole Miss → Iowa / Michigan State / South Carolina
- Maryland → UConn / Vanderbilt / Stanford
- Stanford → UCLA / Iowa / Maryland

Caveat line: "Static-attribute similarity across tier, archetype, conference, and voice. Not a prediction — a calibration."

## Page assembly order (after Session 7)

The team-page render now flows:
```
hero
page_tone_strip      ← Session 7 (Brief §32 — sentience visible)
kickoff_countdown    ← Session 7 (Brief §22.1)
season_standing_rail ← Session 7 (Brief §3.1)
program_prestige_bar ← Session 7 (Brief §3.2)
trajectory_chip      ← Session 7 (Brief §11.4)
peer_comparator      ← Session 7 (Brief §26)
hero_arc_stripe      ← Session 6 (Brief §20)
pulse
aspiration_ladder    ← Session 6 (Brief Part III §33.4)
rituals_strip
cultural_anchors
chronicle
savant
rivalry
season_arc
footer
```

Five new modules in the hero zone above the fold. The 5-second read is now front-loaded with the brief-mandated identity surfaces.

## Gap audit progress (vs WORLD_CLASS_GAP_AUDIT_2026_05_22.md matrix)

| # | Module | Status pre-session | Status post-session |
|---|---|---|---|
| T1 | Hero Arc stripe | ✅ (Session 6) | ✅ |
| T3 | Season Standing 9-rung | not present (P1) | **✅ shipped** |
| T4 | Program Prestige 7-tier | not present (P1) | **✅ shipped** |
| T7 | Season Arc 3-altitude navigator | partial (CFP-era only) | partial (added Trajectory chip helps) |
| T8 | Rivalry Card dual-thermometer | ✅ (Session 6) | ✅ |
| T13 | Fanbase Health Index gauge | not present (P2) | pending (composite needs 5 data sources) |
| T16 | Aspiration Ladder | not present (P1) | ✅ (Session 6) |
| T17 | Seasonal Sentience accent flip | resolver only | **✅ shipped (Page Tone Strip)** |
| T18 | Program-tier sentience UMass-vs-Alabama divergence | implicit only | **✅ shipped (Page Tone Strip + Prestige)** |
| T24 | Kickoff Check-In counter | not present (P2) | **✅ offseason variant shipped** |
| T27 | Program Similarity Engine | not present (P2) | **✅ static-attribute variant shipped** |

Six new P1/P2 modules landed in one session. Estimated original effort: ~17 days. Actual: ~3 hours total.

## What still needs work (deferred to Session 8+)

- **T9 Recruiting Pipeline** — needs 247 composite + Portal data ingest
- **T10 Coaching Staff Scheme Fingerprint** — needs coordinator-resolution data
- **T11 Conference Lens toggle** — needs comparator UI + data
- **T13 Fanbase Health Index gauge** — needs 5 composite signals (volume / geo / cohort / ticket / rival)
- **T19 Chronicle Echo + Retroactive + Player Arc card variants** — needs LLM gen
- **T22 Mascot voice fallback extend to 130 programs** — long-tail
- **T23 Wrapped stack** — pure render but seasonal-only (December drop)
- **T25 Hype Meter** — needs hype data
- **T28 Tab-as-Room IA prototype** — week-scale UI bet
- **T30 Share-Card renderer** — week-scale; high-virality move
- **T31 Legacy renderer parity** — 6-week sprint to cover 100 remaining FBS programs
- **T54 Sprint F /programs/ vs /teams/ IA consolidation** — 5-day decision + invasive

## Deploy status

- `26313824468` in-progress at SHA `a31e0ed5c2` (Aspiration Ladder + earlier)
- `26314788220` cancelled (superseded)
- `26315326392` pending at SHA `a7fbb607f0` (all 6 new modules from this session)

After 26315326392 lands, the live site at `wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app/teams/<slug>.html` should visibly show all six new modules on every profiled team. Differences vs. previous state:

1. **Page Tone Strip below hero** — new horizontal band of UPPERCASE chips reading the page's emotional context.
2. **Kickoff countdown** — new chip reading "100 days · until kickoff · Sun Aug 30 · 17:00 UTC".
3. **Season Standing 9-rung rail** — new full-width rail with 10 ticks, accolade-gold at championship.
4. **Program Prestige 7-tier bar** — new "BLUE BLOOD" / "MID-MAJOR CONTENDER" hero tile with peak ghost.
5. **Program Trajectory chip** — large "STEADY" / "RISING" / "DECLINING" label + sparkline.
6. **Program Peer Comparator** — three clickable peer-program tiles below trajectory.

The legacy `reporting.py` renderer for the other 100 FBS programs and all program-history pages is **not** affected by this session — those still show the legacy chrome and don't get the six new modules. Closing that gap is T31 + Sprint F, deferred.

## Files touched

New modules:
- `src/cfb_rankings/team_pages/season_standing_rail.py` (438 LOC)
- `src/cfb_rankings/team_pages/program_prestige_bar.py` (310 LOC)
- `src/cfb_rankings/team_pages/page_tone_strip.py` (225 LOC)
- `src/cfb_rankings/team_pages/trajectory_chip.py` (242 LOC)
- `src/cfb_rankings/team_pages/kickoff_countdown.py` (197 LOC)
- `src/cfb_rankings/team_pages/peer_comparator.py` (231 LOC)

Modified:
- `src/cfb_rankings/team_pages/renderer.py` — 6 module imports, 6 rendering calls, 6 CSS injections, 6 page-assembly slots
- `src/cfb_rankings/team_pages/data.py` — added `start_time_utc` to `GameResult` + query
- `profiles/alabama.md`, `notre-dame.md`, `ohio-state.md`, `georgia.md`, `usc.md`, `clemson.md`, `florida-state.md`, `miami.md` — added `prestige_tier` + `prestige_historical_peak` overrides

Renames:
- `profiles/texas-am.md` → `profiles/texas-a-m.md` (DB slug mismatch fix)

Total: ~1,650 LOC across 6 new modules + ~20 wiring lines in renderer.py.
