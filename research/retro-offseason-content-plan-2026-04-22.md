# Retroactive Offseason Content Plan — National Championship → Today

Research date: 2026-04-22
Author: deep-research pass for retroactive Jan 19 → Apr 22 coverage
Companion files:

- `research/offseason-modules-calendar-2026-04-21.md`
- `research/offseason-fan-delight-deep-research-2026-04-22.md`
- `research/offseason-publishing-queue-and-build-order-2026-04-22.md`
- `research/offseason-homepage-execution-2026-04-22.md`
- `research/conversation-intelligence-v1-data-plan-2026-04-21.md`
- `src/cfb_rankings/ingest/hub_data.py` (Issue N° 047 seed)
- `src/cfb_rankings/fan_intelligence.py` (mood / gap / swing / storyline math)
- `src/cfb_rankings/ingest/conversation.py` (Reddit collector)

## Purpose

The forward calendar (Apr 22 → kickoff) is already specified in `offseason-publishing-queue-and-build-order-2026-04-22.md`. What is missing is a **retroactive** series that covers everything that actually happened in the sport between the 2026 National Championship game (Jan 19) and today (Apr 22) — delivered in the same weekly-magazine cadence the site now uses live.

This memo answers four questions:

1. What happened, week by week, between Jan 19 and Apr 22.
2. Which of those events we can hydrate from our existing APIs / scrapers, and which need manual seeding.
3. How the retroactive weeks should be keyed, named, presented, and navigated.
4. What code actually has to change to ship it.

Implementation is intentionally scoped *behind* the forward calendar — the retro run should be a backfill job, not a live-data job.

## What actually happened (canonical event catalog, Jan 19 → Apr 22)

This is the thin read that every retroactive week gets built around. Names and dates are anchored to primary reporting (see Sources).

### Championship week — Jan 19

- **CFP National Championship (Hard Rock Stadium):** Indiana 27, Miami 21. Indiana finishes 16–0 — the first FBS perfect season at the 16-game mark, matched only by Yale 1894 on total wins.
- QB Fernando Mendoza: 16/27, 186 yards, rushing TD — Offensive MVP.
- Sealing play: Indiana DB Jamari Sharpe picks Carson Beck with :44 left.
- Storyline lattice: *"Indiana was never supposed to be here"* vs. *"Miami and Mario Cristobal couldn't finish."*

### Portal window — Jan 2 → Jan 16 (overlaps pre-title-game)

- **Dylan Raiola (Nebraska QB) → Oregon.** Defining headline of the window. Dante Moore holds the starting job in Eugene; Raiola competes.
- **Sam Leavitt (Arizona State QB) → LSU** — follows Lane Kiffin.
- **Josh Hoover (TCU QB) → Indiana** to replace the draft-bound Mendoza.
- **Darian Mensah (Duke QB) → Miami** after a court settlement over portal eligibility. Becomes the Hurricanes' presumptive 2026 starter.
- **Cam Coleman (Auburn WR) → Texas** — top portal WR, pairs with Ryan Wingo.
- **Jordan Seaton (Colorado OT) → LSU** — top portal OL.
- **Keon Keeley (Alabama DE) → Notre Dame.**
- **Mylan Graham, Quincy Porter (Ohio State WRs) → Notre Dame.**
- **Oklahoma State** adds 50 incoming transfers under new HC Eric Morris.

### NFL Draft declaration deadline — Jan 15

- **Arch Manning stays at Texas.** Confirmed late-December by his father Cooper; deadline closes it.
- Mendoza declares (and becomes the presumed #1 overall).
- Auburn WR Cam Coleman *declares for portal rather than draft* — still a story.

### Coaching carousel aftershock — late Jan → early Feb

- 33 FBS jobs changed hands across the full cycle; 17 are new P4 head coaches.
- **Michigan fires Sherrone Moore, hires Kyle Whittingham** (out of Utah). This is the emotional center of the offseason — Issue 047's Michigan mood collapse is already keyed to a *"March 14 Moore presser"*; the firing arc extends that into April.
- **LSU hires Lane Kiffin** from Ole Miss (announced Nov 30, finalized in January window).
- **Ole Miss promotes Pete Golding** — continuity-on-defense play.
- **Oklahoma State hires Eric Morris** from North Texas.
- **Tulane promotes Will Hall** (internal OC) — the contrarian "underwhelming" grade in the tracker.

### National Signing Day — early February

- **USC #1** — first non-SEC No. 1 class since Miami 2008; first USC #1 since 2006.
- **Alabama #2** (DeBoer class, seventh straight elite finish for the program).
- **Oregon #3** — third straight top-5 under Dan Lanning; slimmest class in the top 10 (22 signees).
- **Ohio State #4** — seventh straight top-5; no top-10 individual recruit for just the second time this decade.
- **Notre Dame #5** — first top-5 class in more than a decade under Marcus Freeman.
- Also top 10: **Tennessee, Georgia, Texas, Miami.**

### Spring practice opens — late Feb → mid-March

- Nebraska: Feb 21 open.
- USC: Mar 3 open.
- Alabama: Mar 8 open.
- Ohio State: Mar 10 open.
- Oregon: Mar 12 open.
- **Arch Manning limited** in Texas spring reps after an offseason procedure — true frosh Dia Bell and Trey Owens split first-/second-team reps.

### Spring games — late March → late April

- Nebraska: Mar 28.
- USC: Apr 4.
- Alabama: Apr 11.
- **Michigan: Apr 18** — Kyle Whittingham's debut. QB Tommy Carr post-spring, *"QB problem post-spring game"* is the dominant national read.
- Ohio State: Apr 18.
- Oregon: Apr 25 (one day after our window closes — treat as peek/preview in the final retro week).

### Looming at window close (Apr 22)

- **2026 NFL Draft: Apr 23–25 in Pittsburgh.** Mendoza presumed #1 to Las Vegas. This is the *next* event after our backfill window and should be the teaser the last retroactive week hands off to the live calendar.

## Data availability audit (what we can backfill vs. what we must seed)

Everything below is framed around what the existing code path can do without new tier-3 API access.

### We can hydrate these cleanly

- **Football structure.** CFBD Tier 2 gives us the final CFP bracket, the championship box score, final 2025 team records, recruiting class composites by program, and all spring roster / returning-production signals. `python manage.py ingest-cfbd-week --season 2025 --week 21 --season-type postseason` (or the equivalent already in `cli.py`) should capture the final game cleanly — verify by checking that Indiana's `end_power` and Miami's CFP path appear in the postseason ledger.
- **Recruiting class data (Feb NSD).** Tier 2 supports `recruiting_entries` and `team_talent_snapshots`. This is already the recommended prior input per `historical-context-and-preseason-priors-2026-04-21.md`. Recruiting rankings feed "Class Shape" and the Jan/Feb retro weeks directly.
- **Reddit conversation, retroactively.** The Reddit collector (`collect-reddit-watchlist`, `collect-reddit-subreddit-listing`) works off query + listing windows; reddit `search` and subreddit `new` listings both support date ranges. We can backfill storyline volume and sentiment for every week in the window by running the collector with `--season 2025 --week N` where N is our chosen offseason-week integer (see §"Week keying" below), pointed at date-bounded queries for each event (e.g. *"Kyle Whittingham Michigan"*, *"Raiola Oregon"*, *"Kiffin LSU"*).
- **Transfer portal movements.** We do **not** have Tier 3 CFBD transfer data, per `historical-context-and-preseason-priors-2026-04-21.md`. But we can:
  - seed a `portal_moves` table from a curated manual list (the names above) — this is a one-time cost.
  - then hydrate *fan reaction* to those moves via Reddit collection, which is the actual product.
  - the portal ledger itself becomes a static-for-the-offseason dataset; no live scraper is needed for retro coverage.

### We must seed (no good scraper path today)

- **Coaching carousel ledger.** No tier-2 hook. Curate a `coaching_changes_2026` dict (mirroring the Issue 047 seed pattern in `hub_data.py`) that lists each hire/fire with date, program, outgoing coach, incoming coach, grade (ours or sourced). Small, bounded, high leverage.
- **Spring game ledger.** Dates, location, headline takeaway, QB1 read per team. Same shape as carousel ledger — 25–30 rows.
- **Press-conference canon events.** The "Moore presser" already anchors Issue 047. We should catalog 5–8 equivalents across the window (e.g. Whittingham intro, Raiola portal press, Mensah settlement press, DeBoer post-spring). These become the spine of the Shock Index retroactively.
- **NFL Draft declarations.** Until the draft completes 4/25, we only have declared-for-draft lists (+ Arch's stay). Manual ledger; short.

### What we deliberately do *not* backfill

- Per-game conversation features for games that didn't happen (there were none — the championship is already inside the window).
- Rival-bucket Reddit collection for most teams. Rival audience routing isn't cleanly supported in the live collector and won't be until `fan` source coverage hardens (see `offseason-publishing-queue-and-build-order-2026-04-22.md` §"Stage 0"). Retro weeks should use `national` bucket as the default and `fan` only where a team subreddit listing pass has been run.

## Week keying — the one real design decision

The data model keys conversation features and hub features by two different conventions:

- `team_week_conversation_features`, `conversation_storylines`, etc. use **integer** `(season_year, week)`.
- Hub v5 (`fanbase_mood_weekly`, `rivalry_obsession_weekly`, `lexicon_weekly`, `hub_issue_metadata`) uses **date-strings** `week_start_date` (e.g. `"2026-04-22"`) plus `model_week` integer.

For a retroactive offseason series, I recommend **using the hub-style date-keyed schema** for the primary surface and wiring the integer-keyed conversation tables to a parallel offseason-week numbering. Concretely:

- Canonical label: `"Offseason Week N"` with a `week_start_date` Monday anchor.
- Conversation ingest keys: `season_year = 2025`, `week = 22..30` (picking up where the regular season / postseason left off). This keeps the existing `build-conversation-features` loop working without a schema change — the gate logic, storyline ranker, and feature aggregator all read `(season_year, week)` and don't care that 22+ is offseason.
- Hub-surface rendering keys: `week_start_date` strings — mirrors the live Issue 047 surface.
- A small lookup `offseason_week_map` (code-side constant) translates between them so every package resolves both keys at render time.

This is reversible. If we later decide the hub schema should be canonical across the board, we migrate integer-keyed rows by joining on `offseason_week_map`. No data is stranded.

## Retroactive week cadence

Ten weeks, anchored to actual football events. Each week gets a week slug, a week label, a week_start Monday, the seed event(s) that define the week, and the package list.

### Week 22 — "Perfect Hoosiers"
- Start: Mon Jan 19, 2026 (Championship Monday)
- Seed events: CFP Natty (Indiana 27, Miami 21); Mendoza MVP; Indiana 16–0
- Packages:
  - **Issue N° 038: "Perfect Hoosiers"** — cover: Indiana's 16–0, Sharpe's pick, Mendoza's resume, what this does to Big Ten belief.
  - **Mood Index snapshot** — Indiana +30 WoW (title), Miami −20 (collapse narrative), rest of field cooling from regular-season highs.
  - **Cover story visualization**: Mood River — Indiana's belief from Week 1 (preseason doubters) through 16–0.
  - **Commiseration slot**: Miami fans ("Cristobal can't finish").
  - **Lexicon**: *"the pick on the 44"*, *"Hoosier math"*, *"Cristobal cramps"*.

### Week 23 — "Portal Wave Peaks"
- Start: Mon Jan 26, 2026
- Seed events: Jan 16 portal-window close rippling through the week; Raiola → Oregon is the cover; settlements (Mensah) close out
- Packages:
  - **Issue N° 039: "Portal Wave Peaks"** — cover: Raiola's exit reframes Nebraska's "we're back" arc and gives Oregon a second five-star arm.
  - **Shock Index v1 (retroactive)**: Nebraska −12 (Raiola exit), LSU +8 (Kiffin + Leavitt), Miami +6 (Mensah settlement), Notre Dame +6 (Keeley + Graham + Porter).
  - **Respect Gap Census — Winter Edition**: who the national audience still underrates after the portal shuffle.
  - **Rivalry micro-check**: Oregon–Washington "The Border" ratio moves after Raiola stacks Eugene.
  - **Lexicon**: *"portal QB roulette"*, *"five-star trust me"* (early origin of the Ohio State phrase), *"bought a team"* (new LSU).

### Week 24 — "Carousel Aftershock"
- Start: Mon Feb 2, 2026
- Seed events: Post-championship carousel wraps; Whittingham at Michigan intro presser; Kiffin's first LSU staff moves
- Packages:
  - **Issue N° 040: "Who's The Coach Now"** — cover: Whittingham-to-Michigan is the cycle's most disruptive move; Michigan's mood recovers slightly (+3) off the hire.
  - **Coaching Carousel Ledger** — static data viz, 33 moves.
  - **Fanbase Civil War Watch** — Michigan fans: Whittingham savior vs. Whittingham mercenary; LSU fans: Kiffin savior vs. Kiffin distraction.
  - **Living Rent Free** (soft debut, national bucket only): which fanbases mentioned the rival coach more than their own coach.
  - **Lexicon**: *"Whitt happens"*, *"Lane Train"*, *"little brother speedrun"*.

### Week 25 — "Signing Day Truths"
- Start: Mon Feb 9, 2026
- Seed events: National Signing Day (USC #1, Alabama #2, Oregon #3, Ohio State #4, Notre Dame #5 historic)
- Packages:
  - **Issue N° 041: "Signing Day Is A Story We Tell Ourselves"** — cover: USC's first #1 class since 2006 is either the Riley turnaround or recruiting-service cope; we show both reads.
  - **Class Shape Board** — all 17 new P4 HCs' first classes; delta vs. predecessor's last class.
  - **Hope Inventory (retro)** — top 10 fanbases by "this class fixes us" token density in r/CFB and their own subreddit.
  - **Respect Gap on classes**: where recruiting composites and fan belief disagree most (Notre Dame high class + still-doubters; Tennessee high class + peak-believers).
  - **Lexicon**: *"5-star trust me"* formal debut (attributed to r/OhioStateFootball origin), *"class above"*, *"services don't watch tape"*.

### Week 26 — "Spring Opens, Narratives Lock"
- Start: Mon Feb 23, 2026
- Seed events: Most FBS programs open spring practice; Arch Manning limited at Texas; early Ohio State / Alabama storylines form
- Packages:
  - **Issue N° 042: "Spring Opens, Narratives Lock"** — cover: Arch limited at Texas; Dia Bell and Trey Owens split reps.
  - **QB Panic Meter v1 (retro)**: programs with ambiguous QB1 post-portal — Michigan, Alabama, Florida State, Nebraska (post-Raiola), Miami (post-Mensah).
  - **Returning Production Dashboard** — Tier 2 data, paired with program arcs.
  - **Offseason Mood Board refresh** — first of the recurring ones.
  - **Lexicon**: *"limited reps"*, *"QB room vibes"*, *"chasing 2023 alabama"*.

### Week 27 — "Hype Train Check"
- Start: Mon Mar 2, 2026
- Seed events: First mid-spring takes; pre-Moore-presser baseline; national media starts preseason takes
- Packages:
  - **Issue N° 043: "Hype Train Check"** — who is already overcooked (Oregon, LSU); who is being politely ignored (Georgia, Ohio State as co-pilot); who is being prematurely buried (Alabama, USC).
  - **Reality Gap Board v1 (retro)** — Hype Train / A Little Ahead / Grounded / A Little Too Low / Doomer Ball buckets, whole FBS.
  - **Storyline Gravity** — ranked list of the top 12 running offseason storylines by mention volume.
  - **Lexicon**: *"cope"*, *"doomposting"*, *"we're the pick"*.

### Week 28 — "The Moore Presser"
- Start: Mon Mar 9, 2026
- Seed events: Sherrone Moore's March 14 presser (the hinge event already canonized in Issue 047); Big Ten spring games begin
- Packages:
  - **Issue N° 044: "The Moore Presser"** — cover: Michigan mood goes over the cliff; this is the hinge week; this week's cover is the one Issue 047's pull-quote references.
  - **Shock Index v2**: Michigan −15 (Moore presser); Alabama −6 (DeBoer doubt accelerates); USC −7 (Riley fatigue).
  - **Fanbase Civil War Watch** spotlight: Michigan — "hold the line" vs. "pull the plug".
  - **Camp Panic Meter (retro)** debut — Michigan, Nebraska, FSU, USC.
  - **Lexicon**: *"hold the line"* (formal debut, r/MichiganWolverines origin), *"in Day we trust"* (Ohio State, declining), *"Moore we know"*.

### Week 29 — "Michigan Moves On"
- Start: Mon Mar 23, 2026
- Seed events: Michigan fires Moore, hires Kyle Whittingham; Nebraska spring game Mar 28
- Packages:
  - **Issue N° 045: "Michigan Moves On"** — cover: Whittingham-to-Ann Arbor, the hire's structural improbability, and what it means for the Big Ten's coaching ceiling.
  - **Coaching Carousel Ledger — Addendum** — the one late move.
  - **Living Rent Free** — Ohio State mentions of Michigan hit a fresh high post-Whittingham news.
  - **Swing Meter v1 (retro)** — Michigan goes "Full Roller Coaster" on mood variance (collapse → Whittingham bump).
  - **Spring Game Diaries** (soft debut): Nebraska's spring game recap, mood follow-through.
  - **Lexicon**: *"Whitt happens"* resurgence, *"the mercenary era"*, *"this isn't 2007"*.

### Week 30 — "Spring Games And Stock"
- Start: Mon Apr 6, 2026
- Seed events: USC spring game Apr 4 → Alabama Apr 11 → Ohio State and Michigan Apr 18 (Whittingham's debut)
- Packages:
  - **Issue N° 046: "Spring Games And Stock"** — cover: Whittingham's Michigan debut; Tommy Carr's debut; the "QB problem post-spring game" read.
  - **Spring Game Ledger** — date, headline, QB1, mood delta, per team.
  - **Shock Index v3** — compressed; the last week before the live Issue 047 takes over.
  - **Hope Inventory refresh** — post-spring edition.
  - **Preseason Truth Detector (retro v1)** — the first mock ranking alignment check: where does the model already disagree with the offseason consensus poll?
  - **Lexicon**: *"Whitt-ball"*, *"Bryce we trust"*, *"stock up stock down"*.

### Week 31 — handoff to live
- Start: Mon Apr 20, 2026 → Issue 047 (already seeded) publishes 4/22.
- The retro series is done. The live calendar picks up.
- The last retro card on the hub should be a teaser: **"Next: NFL Draft, Pittsburgh, Apr 23–25. Mendoza goes first."**

## Presentation model — how a retro week is structured on the site

Every retro week gets:

1. **An Issue entry in the Hub (`/hub/issue-N°-0XX`)** — mirrors the Issue 047 layout: cover headline, dek, chart caption, editor note, commiseration, 3 cards, Mood Index week, Rivalry week, Lexicon week.
2. **A week hub page (`/offseason/2026/week-22-perfect-hoosiers`, `/offseason/2026/week-23-portal-wave-peaks`, …)** — mirrors the regular-season week page layout the site already generates, but with offseason modules replacing game modules.
3. **Team-page inclusions** — the retro week's Mood Card for each affected team becomes a row in that team's Mood History Timeline on their team page. This is the integration that makes the retro series *permanent* rather than a ten-page microsite.
4. **Homepage archive rail** — once the retro series ships, the homepage's existing "Road To Kickoff" section gets a sibling rail: "The Road From The Title Game" with Issue covers 038 → 046 as cards.

Navigation: a thin top-of-hub pager ("◀ Issue 045 | Issue 046 | Issue 047 ▶") links the series end-to-end so a user can read the offseason as a serialized story.

## Data model implications

**No schema change is required to ship v1** — but four small additions make the work cleaner.

Already-present tables that absorb retro data:

- `conversation_documents`, `conversation_document_targets`, `team_week_conversation_features`, `team_conversation_daily`, `conversation_storylines` — keyed by `(season_year, week)`. Retro runs use `season_year=2025, week ∈ [22..30]`.
- `fanbase_mood_weekly`, `rivalry_obsession_weekly`, `lexicon_weekly`, `hub_issue_metadata` — keyed by `week_start_date`. Retro runs use the nine Mondays from Jan 19 → Apr 13.

New tables (small, bounded, retro-first but reusable):

1. **`offseason_week_map`** — `(season_year, offseason_week INT, week_start_date DATE, slug TEXT, label TEXT, model_week INT)`. The one place where the two keying worlds meet.
2. **`coaching_changes`** — `(season_year, change_date, program_team_id, outgoing_coach, incoming_coach, change_type, grade, notes)`. Replaces the curated seed dict with a queryable table.
3. **`portal_moves`** — `(season_year, move_date, player_name, position, from_team_id, to_team_id, composite_rank, notes)`. Likewise.
4. **`spring_events`** — `(season_year, event_date, team_id, event_type, headline, qb1_read, mood_delta)`. Covers spring openers, pressers, and spring games uniformly.

Each table is a CLI-seedable curation; none requires a live scraper.

## Implementation brief (what actually has to be written)

Scoped in the same P0 → P3 style as `CLAUDE_CODE_FIX_PROMPT.md`.

### P0 — data spine

1. **New migration** in `research/cfb-data-schema-sqlite.sql` adding the four tables above. Small, idempotent, no backfill from existing tables.
2. **New CLI subcommand** `seed-offseason-weeks --season 2025` in `cli.py` that writes the nine rows of `offseason_week_map` from a hardcoded dict. (Model precedent: `seed-hub-issue`.)
3. **New CLI subcommand** `seed-offseason-events --season 2025 --kind {carousel|portal|spring}` that loads curated JSON under `data/offseason/2026/{carousel,portal,spring}.json` into `coaching_changes` / `portal_moves` / `spring_events`. Source of truth for the JSON is this memo plus its citations; one human pass.

### P1 — retro conversation backfill

4. **New CLI subcommand** `backfill-offseason-conversation --season 2025 --week N` that:
   - reads `offseason_week_map` for the week's `week_start_date` and its event anchors.
   - runs `collect-reddit-watchlist` with date-bounded queries generated from the week's event list (e.g. for week 22: *"Indiana championship"*, *"Mendoza MVP"*, *"Cristobal"*; for week 28: *"Moore presser"*, *"Michigan QB"*).
   - runs `collect-reddit-subreddit-listing` for each involved team's subreddit with `--listing new` and a one-week window.
   - then runs `build-conversation-features --season 2025 --week N` to populate the existing aggregate tables.
   - Emits `MIN_MENTIONS_FOR_SIGNAL=12` / `MIN_AUTHORS_FOR_SIGNAL=4` gating the same way the live path does. Weeks that don't clear the gate publish the *shell* with seed copy — same fallback path as `_empty_profile`.
5. **Editorial seed fallback** under `src/cfb_rankings/ingest/hub_data_retro.py` — mirrors `hub_data.py`'s `ISSUE_047`, `MOOD_SEED_047`, `LEXICON_SEED_047` pattern but with nine dicts (`ISSUE_038` … `ISSUE_046`) drawn from §"Retroactive week cadence" above. Ensures every retro week ships with final-voice copy even if the Reddit backfill under-delivers.

### P2 — rendering

6. **New function** `render_offseason_week(db, season, offseason_week)` in `src/cfb_rankings/reporting.py`. Reuses the hub renderer in `hub_page.py` for the Issue body and slots in the three ledger modules (carousel / portal / spring) when present for the week. URL: `/offseason/2026/week-{N}-{slug}.html`. Add to nav tuples at `reporting.py:11717-11723`.
7. **Homepage archive rail** — extend the existing `Road To Kickoff` section in the homepage builder to add a parallel `The Road From The Title Game` strip when `offseason_week_map` has rows with `week_start_date < today`. Reuses the existing offseason card component.
8. **Team-page Mood History inclusion** — extend `fetch_team_mood_profile` (fan_intelligence.py, around line 833-868) to also pull the team's mood deltas from any `fanbase_mood_weekly` row within the offseason window, so the team-page mood history timeline shows the whole Jan 19 → Apr 22 arc, not just the most recent week.

### P3 — polish

9. **Pager** component at the top of each Issue page linking prev/next by `issue_number`.
10. **Sitemap + RSS** entries for `/offseason/2026/...` URLs so the retro series is crawlable.
11. **Verification greps** (CLAUDE_CODE_FIX_PROMPT.md-style):
    - `grep -r "Issue N° 038" output/site/ | wc -l` ≥ 2 (cover render + archive rail).
    - `grep -l "perfect-hoosiers" output/site/offseason/2026/` — 1 file.
    - `grep -c "offseason_week" src/cfb_rankings/reporting.py` — at least 1 to confirm the nav tuple wired up.
    - `sqlite3 cfb_rankings.db "select count(*) from offseason_week_map where season_year=2025;"` → 9.
    - `sqlite3 cfb_rankings.db "select count(distinct issue_number) from hub_issue_metadata where issue_number like 'N° 03%' or issue_number like 'N° 04%';"` → 10 (038–047).

## Risks and open questions

- **Reddit date-bounded search reliability.** Reddit's public search is time-range-finicky; the collector currently uses `t=all` and then post-filters by `created_utc`. For retro backfill this is acceptable — we have ~94 days of posts per week slice — but will under-count for low-subscribe team subreddits. Mitigated by the editorial-seed fallback.
- **Whittingham-hire date precision.** The national carousel tracker describes the Michigan hire sequence as post-Moore-firing but doesn't pin a calendar date in the public-reporting searches I ran. The plan keys the hire announcement to Week 29 (Mar 23 anchor) as the best read; if the actual date is earlier, shift it into Week 28 and re-label Week 29 as a Whittingham-transition issue. Either way the weekly scaffold holds.
- **Issue-numbering collision.** Issue 047 is already the live April 22 issue. The retro proposal claims 038 → 046. Confirm with editorial that 038–046 are actually unused before committing — if any of those numbers are reserved for earlier 2025 issues that just aren't seeded yet, renumber the retro block (e.g. 200-series: `N° 201 Perfect Hoosiers` ... `N° 209 Spring Games And Stock`).
- **Rival-bucket collection for Michigan arc.** The Moore-presser and Whittingham-hire arcs are most satisfying with rival-bucket (Ohio State talking about Michigan, MSU talking about Michigan) signal, which the live collector can't cleanly produce until Stage 0 audience-source hardening lands (see `offseason-publishing-queue-and-build-order-2026-04-22.md`). Retro plan uses national bucket + Ohio State's subreddit listing as a stand-in. Acceptable for v1; revisit after Stage 0.
- **Blocked DB inventory.** The local `cfb_rankings.db` appears locked/WAL-busy to this sandbox. No schema claims in this memo depend on live queries — all references are grounded in `research/cfb-data-schema-sqlite.sql`, `hub_data.py`, and `fan_intelligence.py`. When running the P0 migration, verify the four new tables land cleanly by running a sqlite3 CLI pass from the Windows host, not the sandbox.

## One-paragraph summary (for Kevin)

Ten retroactive weekly issues, keyed (022 → 030) integer weeks and nine Monday `week_start_date` anchors from Jan 19 to Apr 13, telling the offseason as a serialized magazine: *Perfect Hoosiers → Portal Wave → Carousel Aftershock → Signing Day Truths → Spring Opens → Hype Check → Moore Presser → Michigan Moves On → Spring Games And Stock → (handoff to live Issue 047)*. Every issue reuses the existing Hub v5 layout, a small Ledger module (carousel / portal / spring) where relevant, and the existing `team_week_conversation_features` + `fanbase_mood_weekly` pipes fed either by date-bounded Reddit backfill or by curated seed copy under a new `hub_data_retro.py`. Four small tables (`offseason_week_map`, `coaching_changes`, `portal_moves`, `spring_events`) absorb the bits the current schema doesn't cover. Zero new external APIs. Ships as a backfill CLI (`seed-offseason-weeks`, `seed-offseason-events`, `backfill-offseason-conversation`) plus a single new renderer (`render_offseason_week`) and a new homepage rail. The whole thing slots into the forward Apr 22 → kickoff calendar without disturbing it.

## Sources

- [Indiana defeats Miami to win the College Football Playoff National Championship Game | NCAA.com](https://www.ncaa.com/live-updates/football/fbs/indiana-defeats-miami-win-college-football-playoff-national-championship-game)
- [2026 College Football Playoff National Championship — Wikipedia](https://en.wikipedia.org/wiki/2026_College_Football_Playoff_National_Championship)
- [Indiana Completes Undefeated Season With First CFP National Championship — College Football Playoff](https://collegefootballplayoff.com/news/2026/1/19/NCG-recap.aspx)
- [2026 college football coaching carousel grades (CBS Sports)](https://www.cbssports.com/college-football/news/2026-college-football-coaching-carousel-grades-michigan-kyle-whittingham-lane-kiffin/)
- [College football coaching carousel tracker (CBS Sports)](https://www.cbssports.com/college-football/news/college-football-coaching-carousel-tracker-grades-analysis-on-coach-changes-2025-26-firings-and-hirings/)
- [Every new Power Four coordinator hired for 2026 (CBS Sports)](https://www.cbssports.com/college-football/news/college-football-coaching-carousel-2026-new-power-four-coordinators/)
- [2026 college football transfer portal tracker (PFF)](https://www.pff.com/news/college-football-transfer-portal-tracker-2026)
- [Transfer portal winners and losers (Yahoo Sports)](https://sports.yahoo.com/college-football/article/transfer-portal-winners-and-losers-college-football-january-window-155046297.html)
- [10 numbers breaking down the 2026 transfer portal (NCAA.com)](https://www.ncaa.com/news/football/article/2026-01-16/10-numbers-breaking-down-2026-college-football-transfer-portal)
- [Arch Manning returning to Texas (CBS Sports)](https://www.cbssports.com/college-football/news/arch-manning-returning-texas-2026-nfl-draft/)
- [Longhorns spring depth chart: Arch Manning limited](https://www.texasfootballdepthchart.com/articles/texas-longhorns-spring-update-arch-manning-combine-2026)
- [2026 college football spring game schedule (SI)](https://www.si.com/college-football/every-power-conference-spring-game-schedule-2026)
- [Tracking 2026 spring practice schedules (On3)](https://www.on3.com/news/tracking-2026-college-football-spring-practice-schedules/)
- [2026 Michigan Spring Game Recap (mgoblog)](https://mgoblog.com/content/2026-michigan-spring-game-recap)
- [Michigan has a QB problem post spring game (GBMWolverine)](https://gbmwolverine.com/michigan-has-qb-problem-post-spring-game-kyle-whittingham-may-not-want-to-admit)
- [USC inks No. 1 recruiting class in 2026 (CBS Sports)](https://www.cbssports.com/college-football/news/college-football-recruiting-rankings-2026-early-national-signing-day/)
- [2026 recruiting class rankings top 75 (ESPN)](https://www.espn.com/college-football/recruiting/story/_/id/44574905/2026-college-football-recruiting-class-rankings-top-teams-schools)
- [2026 NFL Draft — Wikipedia](https://en.wikipedia.org/wiki/2026_NFL_draft)
- [2026 NFL Mock Draft: Mendoza #1 (Yahoo / CBS Sports)](https://sports.yahoo.com/nfl/article/2026-nfl-mock-draft-90-chiefs-trade-into-top-3-in-final-edition-while-giants-find-great-dexter-lawrence-transition-plan-114919969.html)
