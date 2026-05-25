# Offseason Forward-Orientation Punch-List (2026-05-25)

Two Octopus research probes: (A) site forward-orientation audit, (B) proprietary-DB
product ideas. This tracks what's done vs queued. See memory
[[project-offseason-preview-posture]] and [[reference-cfb-offseason-fan-interests-2026]].

## Done this session
- Chronicle Visuals posture split (preview trio leads, retro labeled "last season").
- Roster Replacement Grid → position-quality story (upgrade/hidden hole).
- Draft Pipeline Conveyor (new visual) on FRESH-ingested 2026 NFL draft (257 picks).
- Rankings page offseason note relabeled "last completed board / 2026 baseline".
- Heisman page eyebrow → "archived race".

## Site audit — queued forward-orientation fixes (by impact)
1. **Homepage/editions** (reporting.py homepage_renderer.py:371-381, 794-796): move
   The Wire + Active Threads ahead of cover-essay TOC; month-aware hero label
   (May/June preview) instead of fixed "After the Bracket / Offseason Issue".
   Note: legacy `render_home_html` already has `_render_offseason_radar_section`
   (reporting.py:15936-15990) framing May as "Identity Formation" — consider
   promoting it / importing into the edition homepage.
2. **Rankings** (reporting.py:16358-16374): move Historical Context BELOW the board.
3. **Heisman** (reporting.py:18067-18078): CTA jump to player cards as primary.
4. **Player pages** (reporting.py:19375-19435, 19440-19448): move Identity & Role +
   Recruiting Pedigree + Transfer Arc ABOVE Current Heisman Lens; relabel
   "Current Season Production" → "last completed season" in offseason.
5. **Chronicle landing** (output/site/chronicle/index.html:185-191, 223-299): rename
   "Chronicle Cards / LLM-generated narrative content" to a fan-facing storyline
   hub; fix stale "wk 12 2024" badges on cards citing May-2026 evidence.
6. **Legacy /teams/*.html** (non-profiled): still open on "2024 Season" record-first
   recap. Routing inconsistency — profiled pages are world-class/forward, legacy
   aren't. Biggest structural risk.

## Proprietary-DB product ideas (ranked impact/effort) — queued
1. **Portal Reality Check** (10/5): cross-team matrix, lost production (x) vs portal
   replacement points (y). transfer_entries + returning_production + team_rating_deltas.
   (Per-team version partly shipped as Roster Replacement Grid; the cross-team
   matrix is the novel league-wide product.)
2. **Delta DNA** (low-med): team volatility "swing signature" from per-game
   power_delta/resume_delta — genuinely proprietary, novel vs ESPN/On3. EKG sparkline.
3. **Heisman Launchpad 2026** (med-high): preseason breakout candidates from
   latent_score trajectory + 2026 support context. Frame as launchpad, not forecast.
4. **Continuity Stress Test** (LOW): returning_production stress bar weighting
   QB/OL/offense/defense — richer than ESPN's single returning-production number.
5. Coach Impact Blueprint, Committee Shadow Board, Recruit-to-Impact-to-Draft Conveyor.

**Best next builds (impact/effort):** Delta DNA + Continuity Stress Test (both low
effort, exploit proprietary model outputs, no new data feeds needed).

## Data freshness
- DONE: ingested fresh 2026 NFL draft (257 picks) via `ingest-nfl-draft --year 2026`.
- KNOWN BUG: `ingest-cfbd-preseason --season 2026 --classification fbs` fails with
  FOREIGN KEY constraint in _ingest_player_recruiting (cfbd.py:831 →
  _upsert_player_source_ids). Blocks 2026 roster/recruiting refresh. Needs a fix
  before fresh 2026 forward-table ingest.

## Ideation round 2 (2026-05-25) — "what else?" Octopus probe

**Core verdict:** biggest gap is HORIZONTAL DISCOVERY. Site wins the vertical
question ("everything about my team/player") but lacks the league-wide one
("who's #1 at X nationally, where does my team rank?"). Shift from "rich
dossier" to "debate engine." Winning loop: leaderboard → team/player page →
compare → share.

**Top 10 adds (impact/effort):**
1. National Offseason Leaderboards Hub (med) — sortable team+player boards:
   portal gain/loss, returning production, replacement burden, continuity,
   draft returner value, talent yield, mood swing. ← BUILD FIRST.
2. Portal Impact Index (med) — national incoming/outgoing/net/room-by-room.
3. Offseason Winners / Roster Change Index (med) — before vs after "who
   improved most."
4. Compare + What-If Studio (med-high) — 2-8 team/player compare + roster sandbox.
5. Breakout Board (med) — league-wide player discovery / "who's next".
6. Returner Value / Draft Decision Hub (low-med).
7. Conference Power Map (med).
8. Coach Reset Lab (med).
9. Chronicle Summer Franchise (low) — recurring boards: Portal Kings, Most
   Fragile Top 15, Fake Continuity, Draft Returners Who Matter.
10. Fan Ballot + Sharecard layer (low-med).

**Don't build (missing data):** season-win sims, schedule playoff odds, SOS,
NIL trackers. Roster-profile sandbox IS fair (only moves our own inputs).

## Model-history product ideas (2026-05-25 deep research)
MOAT = archived model belief over time (weekly Heisman latent scores, weekly
power vs resume, per-game team_rating_deltas) — competitors publish snapshots,
not the historical path. Best first bets: 1,2,3,5.
1. **Best Loss / Worst Win Board** (S) — per-game resume/power deltas: games
   that made a team look better in a loss / worse in a win. Viral, attacks a cliché.
2. **Heisman Truth Serum** (S) — weekly latent_score trajectories: "when did the
   model know first?" + best/worst Heisman calls ever (publish misses too).
3. **Fork Point Index** (M) — the one game that bent a season (pre/post model state).
4. **Volatility DNA** (M) — chaos merchants vs slow-burn vs fake hot starters
   (multi-year per-game swing signatures). [Delta DNA per-team visual is a seed.]
5. **Power vs Resume Divorce Court** (M) — who was actually good vs who stacked
   wins; preseason regression/"fraud or buy-low" engine. Power-resume gap + roster bridge.
6. Coach Shock Profiles (M). 7. Portal Translation Index (L). 8. Fan Panic Index (M, compliance-sensitive).

## Built 2026-05-25 (deployed)
- National + Conference Offseason Leaderboards Hub at /offseason/ — flagship
  Portal Kings board + 2x2 (Returning, Draft Factories, Talent, Reloads) +
  #1 leader spotlights + mini-bars; conference-grouped section w/ chip jump-rail
  (10 conferences, 2 mini-boards each). Built to the Octopus UI/UX design pass.
  TODO: wire into global _site_nav + homepage link (needs build-site rerun).
