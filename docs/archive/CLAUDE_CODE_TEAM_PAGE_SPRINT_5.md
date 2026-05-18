# Claude Code — Team Page Sprint 5

Paste this whole document into a fresh Claude Code session. Execute autonomously. Sonnet default; Opus for editorial uplift only where specified; Haiku for bulk verification. Target token budget: ~250k.

---

## Context

Sprint 4 shipped: Season Arc polish (6 items), 6 new rival profiles (Auburn, Tennessee, Florida, Oklahoma, Washington, UConn) with dual-panel rivalry cards, HistoricalSeasonDeepDive across 174 season pages (19 flagship Opus-authored + 155 template-fallback), gap-year variant for 2017–2018 Alabama/Georgia.

**The product has two remaining quality gaps:**

1. **Six new programs render the world-class shell without voice.** Auburn's team page shows 8 module-class hits vs Alabama's 27. The structural modules (Pulse, Chronicle, Savant, Rivalry) are rendering but the voice-generated content inside them is thin or missing. The 6 programs have profiles (voice, identity, mantra, rivalries) but haven't had `generate-narratives` or `generate-chronicle` fan out to them.

2. **155 historical seasons are template fallbacks.** Alabama 2020 reads as a chapter. Alabama 2014 reads as a stat dump. The quality gap between flagship and fallback is the single most visible heterogeneity in the product.

Sprint 5 closes both gaps. Stretch: backfill the 2017–2018 Alabama/Georgia game data to collapse the gap-year variants into full deep-dives.

---

## Context documents — read these first

1. `TEAM_PAGE_SPRINT_4_REPORT.md` — where you just landed
2. `profiles/` — 17 program profiles now; 6 newest = auburn, tennessee, florida, oklahoma, washington, uconn
3. `src/cfb_rankings/team_pages/narrative_generator.py` + `chronicle_generator.py` — existing fanout infrastructure
4. `src/cfb_rankings/team_pages/historical_season_generator.py` — the template-fallback path
5. `docs/design-system/13-modules-archive.md` — chapter spec
6. `CLAUDE.md` — don't touch `reporting.py`; `PROFILED_SLUGS` guard is load-bearing

---

## Phase 1 — Narrative + Chronicle fanout to the 6 new programs (highest user-visible value)

### 1.1 generate-narratives fanout

Run `manage.py generate-narratives --team <slug>` for each of the 6 new programs: `auburn`, `tennessee`, `florida`, `oklahoma`, `washington`, `uconn`.

- Default model: Sonnet.
- For `auburn`, `tennessee`, `oklahoma`, `washington`: escalate to Opus. These are Tier-1/-2 voice-heavy programs (Auburn's defiant-underdog, Tennessee's restoration-era, Oklahoma's Big-8-to-SEC reinvention, Washington's edge-case-contender). Tonal drift here would be felt immediately.
- For `florida` and `uconn`: Sonnet is sufficient. Florida is a strong profile but the voice register is established; UConn is lower-tier and expectation is on-voice-but-not-virtuosic.

Each team × week generates a state-of-team paragraph + headline. Write to `team_season_narratives` per existing schema.

### 1.2 generate-chronicle fanout

Run `manage.py generate-chronicle --team <slug>` for each of the same 6.

- Haiku preprocess: scan stats for anomalies. 6 programs × current season ≈ small Haiku load.
- Sonnet ranking + writing: 4–6 Chronicle cards per program per week.
- Card types v1.1 (matching the profiled programs): anomaly, flashpoint, echo.

### 1.3 Re-render the 6 programs

Run `manage.py render-team <slug>` for each. Verify on disk: each of the 6 auburn/tennessee/florida/oklahoma/washington/uconn HTML files should have ≥20 module-class hits (matching the ~27 hits Alabama currently has).

Spot-check voice:
- Auburn's state-of-team paragraph should sound defiant-underdog, not Alabama-redux.
- Tennessee's Chronicle flashpoint should reference Heupel and restoration-era language, not Saban.
- UConn's Chronicle should NOT try to be Auburn; it should read just-found-itself / basketball-school-with-football.

### Self-verification for Phase 1

- All 6 new programs render with full populated modules (grep for actual state-of-team text content, not just the class).
- Run a blind tonal diff: paste all 6 state-of-team paragraphs back-to-back. If any two sound interchangeable, the profile-voice prompt isn't biting — fix before moving on.

---

## Phase 2 — Prioritized Opus graduation for ~40 historical seasons

155 template fallbacks is too many to Opus-graduate blindly. Use a priority scoring function to pick the top ~40.

### 2.1 Priority scoring

For each template-fallback `(team_slug, year)`:

```
score = 0
+3  if season has a CFP appearance OR title (from CFP_HISTORY)
+2  if profile has an era_annotation tied to this year
+2  if year is current-season − 1 or current-season − 2 (recency relevance)
+1  if team rank in win% was in top 10% or bottom 10% of that team's era (extreme seasons)
+1  if season includes a verified upset of a top-5 team OR a loss to unranked opponent (defining moments)
+1  if program is Tier-1 or Tier-2 (from profile) — blue-blood seasons hit harder culturally
```

Rank by score. Take top 40. Break ties by recency.

Expected distribution — approximately:
- Most Alabama seasons graduate (Tier-1, many CFP bids, many era_annotations)
- ND 2016 (bottom), 2018 (CFP), 2020 (CFP), 2022 (transition) and the current seasons graduate
- OSU 2014/2024 already flagship; add 2019, 2022
- Georgia 2021/2022 (back-to-back titles) if they're not already flagship
- Lower-tier programs contribute 2–4 seasons each at most
- UMass and UConn likely contribute 0–1 each

### 2.2 Generation

For each of the ~40 prioritized seasons, `manage.py generate-historical-seasons --team <slug> --year <year> --opus` to generate:
- `season_title` (Opus, 1-time, evocative editorial phrase)
- `season_thesis` (Opus, 1–2 sentences)
- `defining_moments` (Sonnet, 3 cards)
- `pull_quote` (Opus, prefer real contemporaneous if recallable; if not, flag `_generated: true`)
- `legacy_paragraph` (Opus, connects forward + backward to other seasons in the program's arc)

Use the voice register + identity phrase + mantra from `profiles/<slug>.md`. Each season should feel distinct from its neighbors — consecutive years should share program voice but vary emotionally (triumph year reads different from rebuild year).

### 2.3 Re-render

`manage.py render-historical-seasons --team <slug>` for each team that got graduations.

### Self-verification for Phase 2

- Pick 3 random graduated seasons from different programs. Paste the season_thesis + legacy_paragraph back-to-back. Each should be unmistakably its program.
- Pick 3 seasons that did NOT graduate (still template fallback). Paste those back-to-back. They should read as clearly-lower-fidelity (acceptable) but not-broken.
- The Alabama 2020 flagship should still be the ceiling; none of the newly-graduated seasons should exceed its quality.
- Check that the priority function picked sensible seasons: no CFP-title year should be template-fallback after this phase.

---

## Phase 3 (stretch) — Alabama/Georgia 2017–2018 CFBD backfill

Only do this if Phases 1 + 2 land under 200k tokens combined.

- CFBD API has game-level data for 2017–2018. Current DB gap is likely an ingestion-side issue, not a source-side one.
- `src/cfb_rankings/ingest/` has existing CFBD loaders; extend the year-range.
- Migration not required if the tables already accept those years.
- After backfill, re-run `season_arc_loader.py` for Alabama and Georgia. Expected: brick state stays `title-era` (canonical), but `record` field fills in (`14-1`, `13-1`) instead of `—`. `data-gap` flag drops.
- Re-render the 2017 and 2018 historical-season deep-dives for both programs. Expected: gap-year variant becomes full 8-section chapter.

### Self-verification for Phase 3

- Alabama arc: '17 brick shows "14-1" (not "—"), still title-era gold with ★.
- Alabama 2017 deep-dive: full shape-of-season SVG populates (13 games), not the data-unavailable placeholder.
- Georgia 2017 deep-dive: same.

---

## Decision authority

Act autonomously on: priority function weights, which Tier-1 programs warrant Opus on narratives vs Sonnet, Chronicle card counts per new program, specific CFBD year-range extension code.

Stop and flag only if:
- Opus-generated voice for any of the 6 new programs reads off-profile (Auburn sounding generic, Washington sounding like Oregon, etc.). In that case, stop and flag the profile — the voice-register field may need Kevin's edit.
- Token usage approaches 400k (pause, report, check in).

---

## Report back with

1. Phase 1 — module-class hit counts for each of 6 new programs before/after. Paste 6 state-of-team paragraphs back-to-back for Kevin's tonal review.
2. Phase 2 — priority function output (top 40 seasons + their scores). Paste 3 graduated season_theses + 3 template-fallback theses side-by-side.
3. Phase 3 (if done) — before/after on Alabama '17 and '18 bricks and deep-dives.
4. Token usage by phase + model.
5. Quality concerns observed — any voice drift, any profile fields that need Kevin's edit, any flagship season that now feels under-written relative to its graduated peers.
6. Natural sprint 6 — likely: profile expansion to the next tier (Clemson, LSU, Wisconsin, Iowa, Oklahoma State, Kansas State, ...) to bring coverage to 25 programs.

Report at end, not between phases. Good luck.
