# Player Page — Season-Phase Design (v2)

**Status:** Design brief, v2 · **Owner:** Kevin · **Date:** 2026-04-23
**Supersedes:** v1 (2026-04-23 morning) — same general approach, but grounded in deeper fan research, more accurate sub-phases, a Draft Day Live treatment, mock-draft aggregation, coaching-change awareness, and explicit mobile-first patterns.

A player page that reads right in November reads wrong in April. And a page that reads right in early April reads wrong during NFL draft week. The offseason isn't one mode — it's four distinct sub-phases with different content primacies, different fan questions, and different energy levels. This doc defines the full season-phase system.

## 1. Why offseason is a different product

CFB offseason is one of the most content-active periods in American sports because it spans the NFL draft, the transfer portal (two windows: December-January and April), spring practice, recruiting's late-cycle flips, coaching changes, and way-too-early content cycles that begin the day after the national championship. The fans who visit a player page in April are asking fundamentally different questions than fans who visit in November.

**November (in-season) fan question:** "How is he playing right now?"
**April (offseason) fan question:** "What's next for him, and what should I expect in 2026?"

A retrospective-only page forces April readers to do the mental work of projecting forward from last season's stats. A forward-looking page does it for them. Do both and you've built something 247Sports and On3 charge for.

## 2. The five phases, with real sub-phases

Phase is a property of the system's clock, not the player. Every page gets the same phase at the same time. The system infers the phase from today's date crossed with the CFB calendar.

| Phase | Dates (approx) | Primary fan question | Energy |
|---|---|---|---|
| **IN-SEASON** | late Aug → early Dec | "How is he playing right now?" | Weekly, high |
| **POSTSEASON** | mid Dec → mid Jan | "How does he close out?" | Bowl/CFP focused |
| **OFFSEASON · EARLY** | mid Jan → mid April | "Spring update? Portal status? Draft declaration?" | Medium, diffuse |
| **OFFSEASON · DRAFT** | NFL draft week (late April) | "Where does he get picked? Who takes him?" | Peak, narrow, 72-hour burst |
| **OFFSEASON · SUMMER** | May → early July | "Commitment news? Any news?" | Low, patient |
| **OFFSEASON · PRESEASON** | mid July → mid Aug | "What's the outlook? Is he the starter?" | Rising, anticipation |
| **PRESEASON · CAMP** | mid Aug → first game | "Depth chart? Position battle resolved?" | High, countdown |

Today (April 23, 2026) we are in **OFFSEASON · DRAFT — Round 1 tonight.**

## 3. Fan archetypes to design for

Any given page gets all of these. The design has to serve them concurrently, not pick one.

- **Own-team fan.** Visits the player page for their school's player. Wants to know everything: portal moves, draft projection, spring practice, depth chart fit, coaching context. Will spend 60-180 seconds.
- **Rival-team fan.** Visits the other school's star to measure threat. Wants Hero + 2026 Outlook + Supporting Cast. 20-40 seconds.
- **National fan.** Follows 10-20 headline players (Carr, Manning, Smith, Downs). Wants the 5-second summary and one standout stat. 10-15 seconds.
- **Draft junkie / fantasy player.** Tracks draft prospects. Wants mock draft range, measurables, red flags, team fit scenarios. 30-60 seconds.
- **Bettor.** Tracks Heisman futures, preseason win totals, player props. Wants the 2026 Outlook cells and nothing else. 5-10 seconds.
- **Recruit follower.** Tracks HS signees. For incoming freshmen, wants commitment story, depth chart context, early enrollee status. 30 seconds.

The Hero must serve all six in the first 5 seconds. Subsequent modules specialize.

## 4. What the research says about real offseason content

This is grounded in what ESPN, 247Sports, On3, and PFF actually surface during offseason, crossed with what fans discuss on r/CFB (290K+ members, peak engagement during portal + draft windows).

**Active categories right now (mid-April 2026):**

1. **NFL draft tracking.** Round 1 tonight (April 23). Fans want: projected pick range, team fit, red flags, combine measurables, mock-draft aggregate from Mel Kiper / Daniel Jeremiah / Peter Schrager / ESPN Miller-Fowler / Walter. Live pick updates during draft days.
2. **Spring transfer portal** (April window). Fans want: who entered, who committed, who's visiting where. Both for their team and for players' own pages.
3. **Spring practice storylines.** QB battles, freshman emergence, position changes, injury recoveries. Ends with spring game or "spring showcase" (the old spring-game format is dying due to competitive-advantage concerns).
4. **Way-too-early rankings.** Top 25, Heisman odds, All-American projections, preseason watch lists. Content format begins the day after the national title game and runs through July.
5. **Coaching change aftermath.** New OC / new DC / new head coach affects returning players' outlook. "Playing for a new play-caller" is a real fan conversation.
6. **Heisman futures market.** Kalshi, PolyMarket, and sportsbook odds are active year-round. CJ Carr is currently the 2026 Heisman favorite per CBS Sports / FanDuel. Arch Manning second. Dante Moore, Julian Sayin, Jeremiah Smith in the mix.
7. **Returning starter tracker.** "X of 22 Ohio State starters return" is a standard content unit.
8. **Portal class rankings.** Both team-level and player-level. "Top transfer portal landing spots."

**Dormant or quiet right now:**

- Game logs, box scores, in-season production rankings — fans aren't mentally in November.
- Advanced stats for the recent season — fans consume these in-season and don't re-open them until bowl/playoff windows.
- In-game splits — same pattern.

The implication: the current retrospective-heavy player page is competent but dormant. The page is optimized for an audience that isn't there right now.

## 5. The core design move: one system, phase-aware content

Don't build a separate offseason page. Keep the same ten locked modules and:

1. **Add a phase banner** above Hero that names the phase explicitly.
2. **Add three new modules** (2026 Outlook, Development Trajectory, Draft Day Live) that are primary in offseason sub-phases and hidden / deprioritized in-season.
3. **Reshuffle page order per sub-phase** so retrospective modules demote and forward-looking ones promote.
4. **Rewrite labels** so retrospective surfaces are unambiguously retrospective ("2025 Season · Final" not "Current Season Production").
5. **Shift Hero cells** per sub-phase — in-season cells become retrospective; offseason cells appear.
6. **Make the Subnav phase-aware** so the anchor list matches the visible module set.

The system stays one system. Each module becomes phase-aware. Phase = props threaded through `_assemble_player_page_data` to every module render function.

## 6. Phase banner copy library

The banner is a slug-line that sets the reading frame. Short, factual, gold-on-dark.

| Phase / sub-phase | Banner copy |
|---|---|
| IN-SEASON | `WK {N} · 2025 SEASON` |
| POSTSEASON · Bowl week | `POSTSEASON · 2025 · BOWL WEEK` |
| POSTSEASON · CFP week | `POSTSEASON · 2025 · CFP {QUARTERFINAL/SEMIFINAL/CHAMPIONSHIP}` |
| OFFSEASON · EARLY · Jan-Feb | `OFFSEASON · {MONTH} 2026 · PORTAL WINDOW OPEN` |
| OFFSEASON · EARLY · Mar | `OFFSEASON · SPRING 2026 · PRACTICE ACTIVE` |
| OFFSEASON · EARLY · Early Apr | `OFFSEASON · SPRING 2026 · PRE-DRAFT` |
| OFFSEASON · DRAFT · Draft day | `🔴 LIVE · 2026 NFL DRAFT · ROUND {N}` |
| OFFSEASON · DRAFT · Post-draft | `OFFSEASON · 2026 NFL DRAFT · COMPLETE` |
| OFFSEASON · SUMMER · May-Jun | `OFFSEASON · SUMMER 2026 · COMMITMENT SEASON` |
| OFFSEASON · PRESEASON · Jul | `PRESEASON · 2026 · OUTLOOK WINDOW` |
| PRESEASON · CAMP · Aug | `PRESEASON · 2026 · FALL CAMP OPEN` |
| PRESEASON · CAMP · Week before opener | `PRESEASON · 2026 · {N} DAYS UNTIL KICKOFF` |

Draft day is the only phase where I'd allow the live-red-dot emoji — justified by the real-time energy of the moment. Every other banner is calm and factual.

## 7. Hero cells, phase-aware

The Hero's five fingerprint cells are what most readers see. Cell identity flexes by phase:

**In-season cells** (today's design):
1. CFB Index QB Score (composite 0-100)
2. Heisman Heat (nowcast + trajectory)
3. The Room on Carr (belief dial)
4. Respect Gap (fan vs national)
5. Reality Gap (fan vs structural)

**Offseason · Early cells:**
1. **2025 Season Score** — retrospective composite, labeled as retrospective.
2. **2026 Heisman Futures** — current market odds, trajectory across recent weeks.
3. **Draft Stock** — for eligible-declared players: mock-draft aggregate rank + projected round. For non-declared: null / replaced with (6).
4. **Returning Value** — composite of (2025 percentile × returning-play availability projection). For freshmen, flipped to "Projected Freshman Impact."
5. **Coaching Continuity** — chip showing new OC/DC/HC if applicable, with their offensive identity ("Tempo spread · 78 plays/gm prior stop"). Small but high-signal for returning players.
6. **Preseason Watch List** — which of the major preseason lists (Heisman / Davey O'Brien / Manning / Maxwell / Walter Camp / AP preseason AA / Athlon / Phil Steele / Lindy's) the player appears on.

If more than 5 cells populate, show the top 5 by signal strength and tuck the rest behind a "Show all 8" disclosure. Don't cram.

**Offseason · Draft cells** (draft week specifically):
1. **DRAFT LIVE** — real-time pick tracker. See §10.
2. Mock Draft Consensus — aggregated rank.
3. Team Fit Scenarios — top 3 landing spots with matchup notes.
4. Red Flags / Green Flags — short list from public scouting reports.
5. Combine / Pro Day Highlights — key measurables (40, vertical, bench).

This cell set is conditional: only appears for players in the draft class. Returning players during draft week still use Offseason · Early cells.

**Offseason · Summer cells:**
1. 2025 Season Score (retrospective)
2. 2026 Heisman Futures (market patient/stable)
3. Returning Value
4. Development Trajectory summary (multi-season arc headline)
5. Coaching Continuity

**Offseason · Preseason cells:**
1. 2026 Preseason Rank (his team's AP preseason rank, since his own preseason identity is tied)
2. 2026 Heisman Futures
3. Projected Role (`Starter` / `Co-Starter` / `Rotation` / `Backup` with confidence chip)
4. Preseason Watch Lists (multi-list count: "On 7 of 9 major watch lists")
5. Team 2026 Outlook (SP+ preseason, win total futures)

**Preseason · Camp cells:**
1. Days Until Kickoff (countdown)
2. Projected Role (with latest depth-chart update timestamp)
3. 2026 Heisman Futures
4. Camp Storyline (1-line narrative: "In QB1 competition with {other player}")
5. Opening Opponent context (preview, matchup tag)

## 8. New modules, spec'd in detail

### 8.1 2026 Outlook (30s tier · primary in all offseason sub-phases except draft week)

Forward-looking cell bank. Five-to-seven cells depending on data availability. Grammar matches Hero Fingerprint — eyebrow label + tabular number + one-line interpretation.

**Cells:**

1. **Projected Role** — chip: `STARTER` / `CO-STARTER` / `ROTATIONAL` / `BACKUP` / `COMPETING`. Derived from returning-starter flag + depth chart + spring practice text extraction. Confidence chip: `HIGH` / `MEDIUM` / `EMERGING`.

2. **Heisman Futures** — current best odds (Kalshi + PolyMarket + FanDuel ML aggregate). Rank if top-30. Trajectory spark over past 4 weeks. Empty state if not priced: "Not yet listed on major futures markets."

3. **NFL Draft Grade** — for eligible-declared players ONLY. Mock-draft consensus from 5+ boards (Kiper, Jeremiah, Schrager, Miller, Walter). Shows projected round range (e.g., "R1-2, picks 22-45") + consensus rank. See §11 for aggregation spec.

4. **Preseason Watch Lists** — count + names of major preseason lists the player appears on. "On 7 of 9 lists: Heisman, Davey O'Brien, Manning, Maxwell, Walter Camp, AP preseason AA, Athlon." Full list on hover / drawer.

5. **Returning Value** — composite score 0-100. For veterans: (prior-season percentile × returning availability × coaching continuity). For freshmen: recruit rating + early enrollee + depth chart projection. Methodology link.

6. **Team 2026 Outlook** — the player's TEAM's 2026 projected win total + SP+ preseason + schedule strength. Establishes the stage he'll be playing on.

7. **Coaching Continuity** — if OC/DC/HC changed since last season, show new name + system identity ("Air raid, 82 plays/gm prior"). If no change, show "Same OC from 2025 (Year 2)." Real signal for returning players.

**States:** empty (no outlook signal — walk-on, injured, unresolved — renders with a 2-3 sentence honest note), loading (shape-accurate skeleton), partial (some cells live + some "awaiting signal"), error.

**Position adaptation:** For WR, replace Heisman Futures with Biletnikoff Futures if markets exist. For DB, Thorpe. For OL, Outland. For K, Groza. Fall back to "{Position} Futures" if no market. This is a data-availability sweep, not a new design.

### 8.2 Development Trajectory (5m tier · primary in all offseason sub-phases)

Multi-season career arc. The module that turns a page from "season snapshot" into "career portrait."

**Content:**

- **Line chart** — season on x, CFB Index score on y. 4-6 data points for veterans, 1-2 for freshmen. Trajectory line interpolated.
- **Milestone markers** — dots on the chart at each season inflection, with labels: `Recruit Signing`, `Redshirt`, `First Start`, `Bowl MVP`, `All-Conference`, `All-American`, `Injury`, `Position Change`, `Transfer`, `POTY Finalist`. Click opens a micro-drawer with date + 1-sentence context.
- **Narrative header** — 1-2 sentences synthesizing the arc. `"From 3-star recruit to R15 Heisman finalist in three seasons — the steepest QB development arc of any active P4 starter."`
- **Peer arc overlay (optional)** — toggle to overlay 1-3 peer players' arcs on the same chart for context. Uses Pill Comparator primitive.
- **Cohort position** — at each inflection, small indicator of where the player sat within their position cohort that season (e.g., "78th percentile among P4 QBs in 2024").

**States:** populated (veterans), single-point (freshmen with just recruit rating + projected freshman impact), empty (walk-ons pre-roster), error.

**Design cue:** line ends with a bounded dot in retrospective phases (career closed to date), an open arrow during preseason (projection forward).

### 8.3 Draft Day Live (new, conditional, primary only during draft week)

The highest-energy module on the page when it's live. Appears only for players in the declared draft class during the 72-hour draft window.

**Pre-draft state (before their projected round opens):**

- Large countdown: "Round 1 starts in {hours}:{minutes}:{seconds}"
- Consensus mock pick: "Projected: #14 · Tampa Bay" with confidence (consensus range).
- Team fit scenarios: top 3 landing spots with 1-line matchup notes.
- Red / green flags: 3 short bullets from scouting aggregates.
- Compared to: 1-2 recent NFL comparisons ("Style comp: C.J. Stroud, reduced mobility").
- Share button — prominent, mobile-thumb-friendly.

**Live-picking state (round is active but player not picked yet):**

- Live ticker: current pick (e.g., "On the clock: Miami Dolphins · Pick 11") with auto-refresh every 15s.
- His projected pick range: highlighted band on the ticker.
- "What happens if {team} takes him?" micro-analyses for top 3 likely scenarios.

**Just-picked state (within 30 min of selection):**

- Big celebratory card (accolade gold border, motion: Delight 800ms) — **"DRAFTED · ROUND {N} · PICK {P} · {TEAM}"**
- Draft class number (e.g., "4th QB taken").
- Projected fit analysis.
- Analyst reactions (3-5 short quotes, if available from campus/beat feeds).
- Share button remains prominent.

**Post-draft state (after draft closes, until off-week):**

- Historical card: where he went, draft class rank, contract projection if public.
- Transition to the NFL-moved handling (see §13).

**Not-drafted state (draft closes, player undrafted):**

- "UNDRAFTED — AVAILABLE FOR FREE AGENCY" chip.
- Tracker: UDFA signings window.
- Once signed: "SIGNED WITH {TEAM}."

**Data sources for Draft Day Live:**

- Live pick feed: ESPN NFL Draft Tracker API / NFL.com API (TBD — v1 can be manual updates or a scheduled scraper; real-time feed is a nice-to-have, not a blocker).
- Mock draft aggregate: Kiper (ESPN), Jeremiah (NFL.com), Schrager (ESPN), Miller & Fowler (ESPN), Walter (WalterFootball), CBS.
- Team fit / red flag text: aggregator of beat reports and scouting blurbs.

**Live-update mechanism:** a single small JS polling helper at `/assets/js/draft-live.js` that hits a read-only endpoint on our side (populated from our ingest pipeline) every 15-30s during active rounds. Static HTML outside the 72-hour window. Don't build a full push-socket infrastructure for a 72-hour event.

## 9. Offseason Status chip — expanded states

Appears in Hero identity strip during offseason. Single source of truth for "what's his status right now?"

| State | Sub-context | Example copy |
|---|---|---|
| RETURNING | Year | `RETURNING · JR 2026` |
| DECLARED FOR DRAFT | Draft year | `DECLARED · 2026 NFL DRAFT` |
| DRAFTED | Round, pick, team | `DRAFTED · R1 · #14 · TB BUCS` |
| UNDRAFTED FA | Signing status | `UNDRAFTED · SIGNED W/ CHI BEARS` |
| TRANSFERRED IN | Prior school | `TRANSFERRED IN · FROM USC` |
| TRANSFERRED OUT | Destination | `TRANSFERRED OUT · TO OHIO STATE` |
| ENTERED PORTAL | Entry date | `PORTAL · ENTERED APR 15` |
| COMMITTED OUT OF PORTAL | Destination | `PORTAL COMMIT · OREGON` |
| EARLY ENROLLEE | Spring arrival | `EARLY ENROLLEE · SPRING 2026` |
| SIGNED RECRUIT | Fall arrival | `2026 SIGNEE · ARRIVING JUL` |
| MEDICAL RETIREMENT | — | `MEDICAL RETIREMENT` |
| GRADUATED · CAREER CLOSED | — | `GRADUATED · COLLEGE CAREER CLOSED` |
| NFL · ACTIVE | Years pro | `NFL · {TEAM} · YEAR {N}` |
| NFL · RETIRED | Years pro | `NFL RETIRED · {N} SEASONS` |
| UNRESOLVED | — | `STATUS UNRESOLVED` |

Chip color: `--accolade-gold` for positive-framing statuses (returning, drafted, portal commit), `--muted` for neutral (unresolved, graduated), `--destructive-subtle` for abrupt statuses (medical retirement, transferred out in unusual circumstances).

## 10. Module reshuffling per sub-phase

Each sub-phase gets its own page order. The subnav anchor list reflects the visible set.

**IN-SEASON** (unchanged):
1. Hero · 2. Standing · 3. Room · 4. Signature · 5. Production · 6. Savant · 7. Splits · 8. Peers · 9. Cast · 10. Bio

**OFFSEASON · EARLY** (mid Jan → early April):
1. Hero (with Offseason Status chip) · 2. Phase banner · 3. 2026 Outlook · 4. Room · 5. Bio/Recruiting/Transfer/Roster · 6. Development Trajectory · 7. Standing (2025 final + 2026 ghost marker) · 8. Supporting Cast (2026 projected) · 9. 2025 Signature · 10. 2025 Season Production · 11. 2025 Savant · 12. 2025 Splits · 13. Peers

**OFFSEASON · DRAFT** (draft week, for eligible-declared players):
1. Hero · 2. Phase banner (live) · 3. **Draft Day Live** · 4. 2026 Outlook (muted — not relevant for players going pro) · 5. Development Trajectory (full career arc) · 6. Room (draft-week topics) · 7. 2025 Signature · 8. Bio/Recruiting/Transfer/Roster · 9. Standing · 10. Supporting Cast · 11-14. Retrospective season modules

**OFFSEASON · DRAFT** (draft week, for returning players):
Same as OFFSEASON · EARLY. Draft Day Live doesn't render.

**OFFSEASON · SUMMER** (May-July):
Same as OFFSEASON · EARLY but Development Trajectory moves up (quiet time = reflective content wins), and Room often empties naturally.

**OFFSEASON · PRESEASON** (late July - early August):
1. Hero (preseason cells) · 2. Phase banner · 3. 2026 Outlook (primary focus) · 4. Standing (with 2026 projected rung front-and-center) · 5. Supporting Cast (2026) · 6. Room (preseason storylines) · 7. Bio/Recruiting/Transfer/Roster · 8. Development Trajectory · 9. 2025 Signature (now historical reference) · 10-13. Retrospective season

**PRESEASON · CAMP** (mid August):
Same as OFFSEASON · PRESEASON but Hero's countdown cell goes prominent and the Room surfaces depth-chart chatter.

## 11. Mock draft aggregation (data strategy)

Draft Grade and Draft Day Live depend on a mock-draft aggregate. Here's the contract:

**Sources (free / public):**
- Mel Kiper (ESPN Big Board) — updated weekly through draft week.
- Daniel Jeremiah (NFL.com) — updated weekly.
- Peter Schrager (ESPN) — mock drafts, multiple editions.
- Matt Miller & Jordan Reid (ESPN) — mock drafts.
- Walter Cherepinsky (WalterFootball) — rolling mocks, very high volume.
- CBS Sports (Ryan Wilson / Josh Edwards) — mocks.
- PFF draft board (scouting-first).
- The Athletic (Dane Brugler's "The Beast") — deep report, once a year.

**Aggregation rules:**
- Pull rank per prospect from each source where available.
- Compute mean + median + IQR (25th to 75th percentile) for the consensus range.
- Weight Kiper, Jeremiah, Brugler more heavily (the authoritative voices).
- Refresh weekly during pre-draft; daily during draft week.
- Never surface a single-source rank as the number — always show the range with a confidence note.

**Presentation:**
- Draft Grade cell: "R1-2 · #14-22 · consensus #17" with a spark showing rank movement over past 6 weeks.
- Drawer opens to show per-source ranks, red flags, team fit notes.

**Build effort:** new adapter family `src/cfb_rankings/ingest/sources/draft_boards/` with one adapter per source. Landing table `player_draft_projection` keyed by (player_id, source_id, snapshot_date, rank). Aggregator computes the consensus view. This is Stage P.3 work — not needed for P.0 hotfix.

## 12. Transfer portal treatment

Portal status is a first-class offseason concept. Treat it with real UX, not just a chip.

**Portal Status module** (inside or adjacent to Bio/Recruiting/Transfer/Roster — becomes primary when relevant):

- Entry date + entry context ("Entered Apr 15 after spring game").
- Reason summary (1 sentence from public sources, or blank if unclear).
- Contact / visit log: which schools have reportedly made contact, which visits scheduled. Cited sources.
- Projected landing: if aggregators (On3 Industry Ranking, 247) have a prediction, show it with confidence.
- Commitment outcome: once committed, the chip flips to `PORTAL COMMIT · {SCHOOL}` with the date.

**Historical portal activity:** If the player has been through the portal before (e.g., Pavia's Vandy story), surface it in Development Trajectory as a milestone marker and in Bio under a new "Transfer History" sub-tab.

## 13. Career-done / NFL-moved handling

For players whose CFB career is complete, the page shifts permanently. No more forward-looking content — the full page becomes retrospective + legacy.

**Graduated · no pro projection:**
- Offseason Status chip: `GRADUATED · COLLEGE CAREER CLOSED`.
- 2026 Outlook and Draft Day Live hidden.
- Development Trajectory shown with line terminated in a bounded dot.
- Phase banner: `COLLEGE CAREER · COMPLETE`.
- Canonized ribbon (from the original brief §7) appears if the player was retired-number-level alumni.

**NFL · Active:**
- Offseason Status chip: `NFL · {TEAM} · YEAR {N}`.
- 2026 Outlook hidden entirely (not relevant).
- Hero cells swap to retrospective-only CFB performance.
- Add a small "NFL Performance" link card that points to an external / later-build NFL player page if we build one.
- Development Trajectory closes its CFB arc and shows an "NFL career — see {link}" footnote.

**NFL · Retired (CFB historical):**
- All present-tense content gone.
- Page reads as archival record.
- Canonized ribbon if retired-number-level.

## 14. Mobile-first offseason patterns

During draft week especially, fans check on mobile constantly. Mobile offseason UX specifically:

- **Hero + Offseason Status chip + Draft Day Live** must be visible above the fold on a 375px viewport. No banner taking 80% of the first-view.
- **Share button** prominent on mobile. Thumb-reachable. Single tap → native share sheet with pre-filled text including the player's current status.
- **Live-ticker scroll behavior:** during Draft Day Live, the live-pick-tracker sticks to the top of the viewport as user scrolls (second sticky layer below the Subnav, only during draft week). Releases when draft closes.
- **Skeleton load on slow connections:** the "shape" of the page should be visible before any data hydrates. Phase banner + Hero skeleton + first two modules' skeletons load first, everything else is lazy.
- **Push notifications (post-kickoff feature):** if a user favorites a player, send a push notification when they get drafted or pick is announced. Not in scope for v1, but design for it.

## 15. Staged rollout (v2)

**P.0 — Offseason hotfix (45 min, ship today).**
Hard-coded phase banner above Hero. Retrospective labeling on Production / Savant / Splits / Signature. Hero accolade chip prefixed "2025". Bio promoted to position 5. Already spec'd in `CLAUDE_CODE_PATCH_OFFSEASON_HOTFIX.md`.

**P.1 — Phase detection infrastructure (4 hours, Sonnet).**
`src/cfb_rankings/season_phase.py` returns the current phase + sub-phase from today's date crossed with the CFB calendar. Thread `phase: SeasonPhase` through `_assemble_player_page_data`. Unit tests at each phase boundary.

**P.2 — Offseason Status chip (1 day, Sonnet with one Opus micro-decision on color semantics).**
Status resolution from `roster_week` + `player_transfers` + new `player_draft_declarations` table (minimal — just a flag per player). Render as chip in Hero identity strip. All 15 states from §9.

**P.3 — Mock draft aggregation (2-3 days, Sonnet for adapters + one Opus pass for the aggregator weights).**
Build draft-board adapters (start with 3: Kiper, Jeremiah, Walter). Landing table `player_draft_projection`. Aggregator. `2026 Outlook · Draft Grade` cell populated.

**P.4 — 2026 Outlook module (1-2 days, Sonnet).**
Build the render + data contract for 7-cell outlook. Defaults + empty states per §8.1. Ship with whatever data we have; cells without data render honest empty states.

**P.5 — Development Trajectory module (2-3 days, Sonnet).**
Pre-compute `player_season_summary` aggregates. Build the line chart. Milestone markers. Peer arc overlay (optional in v1).

**P.6 — Draft Day Live module (2 days, Sonnet — but see timing note).**
Conditional module for draft-week + declared players. Pre-draft / live-picking / just-picked / post-draft states. Live-update polling helper.

  **Timing note:** Draft Day Live would have been ideal to ship THIS week for the 2026 draft (April 23-25). That's not realistic — we're hours from Round 1. Ship it after draft week completes and stage it for 2027. The retrospective version ("DRAFTED · R{N} · PICK {P} · {TEAM}") can ship immediately once P.2 is in.

**P.7 — Transfer portal UX (1-2 days, Sonnet).**
Portal Status sub-module within Bio/Recruiting/Transfer/Roster. Entry context + contact log + projected landing + commitment outcome.

**P.8 — Figma Stage 4 commission (parallel to P.4-P.7).**
Once P.1+P.2+P.4 are live, commission Figma to produce offseason variants of Hero + 2026 Outlook + Development Trajectory + Draft Day Live + Portal Status at 1440+375. Plus phase-banner variants for all 6 banner copy sub-phases. Same locked v5 system.

**P.9 — Phase-aware subnav + page-order reshuffling (1 day, Sonnet).**
Subnav anchor list adapts to phase. Module render order reshuffles per the §10 tables.

**P.10 — Career-done handling (1 day, Sonnet).**
Status chips for graduated / NFL-active / NFL-retired. Hide forward-looking modules for these. Canonized ribbon integration.

## 16. Review criteria (v2)

When the full offseason treatment ships, grade it against:

1. **The calendar test.** A fan landing on Carr's page on April 23 should never wonder "is the season over?" Phase banner + retrospective labeling answer before they can ask. **This is the P.0 bar. Non-negotiable.**
2. **The "what's next" test.** Within 5 seconds, a fan should know the player's 2026 status (returning? declared? portal?) and one forward-looking signal. **P.2 + P.4 bar.**
3. **The draft-week test.** During April 23-25, 2027 (next draft week), a fan visits a first-round prospect's page at 8:30pm Thursday. Can they tell whether he's been picked yet? If picked, by whom, and at what pick? If not yet, his projected range? **P.6 bar.**
4. **The career-arc test.** A fan who's forgotten that Carr was a 3-star recruit should see that context surfaced in Development Trajectory without digging. **P.5 bar.**
5. **The portal test.** A fan arrives at a portal-active player's page. Can they tell the entry date, reported contacts, and projected landing? **P.7 bar.**
6. **The mobile draft-day test.** On a 375px viewport at 9pm Thursday during Round 1, the live pick status is visible without scrolling. **P.6 + §14 bar.**
7. **The dignity test.** A walk-on's offseason page renders cleanly with appropriate empty states — no broken modules, no apologetic copy. **Every stage.**
8. **The completeness test.** A graduated player's page becomes archival cleanly — no forward-looking ghosts, no "awaiting signal" on modules that will never have signal. **P.10 bar.**

## 17. Things I'm less sure about — flag for decision

1. **Mock draft aggregation cost.** If Kiper / Jeremiah / Brugler gate their content behind ESPN+ / subscriptions, scraping them is an ethical + legal question. Free public alternatives (Walter, public Substacks, podcast transcripts) may have lower accuracy. Decision: start with 3-4 free sources; add paid sources later if Kevin gets subscription access.

2. **Live draft feed.** A true real-time feed (pick-by-pick within seconds) requires either (a) a paid data partner (SportsData.io, Sportradar) or (b) scraping ESPN's Gamecast. Both have costs / risks. Decision: v1 Draft Day Live uses 60s polling of our own ingested data, which is refreshed by our scrapers; accept the latency; upgrade later.

3. **Portal activity reporting.** 247Sports and On3 are the sources of truth. Both are paywalled. Public Reddit threads + beat writer Twitter are the fallback. Decision: build on public sources (Reddit + campus news RSS + beat Twitter) and flag projected-landing as "community consensus, not authoritative."

4. **What if data isn't ready for a cell?** 2026 Outlook has 7 potential cells but many players will have data for only 2-3. Decision: always show the cells that have data, empty-state the ones that don't (no fallback inventions). A 2-cell 2026 Outlook is better than a 5-cell one with 3 fake ones.

5. **Phase at midnight.** When does a phase actually flip? Midnight local? Midnight UTC? Midnight East Coast (where most CFB games run)? Decision: use East Coast midnight. It's where the sport lives.

6. **Sub-phase sub-phase.** Within OFFSEASON · EARLY, there's also a pre-draft-declaration window (Jan 1-15) vs post-declaration window (Jan 15-April 15). Do we need another nesting? Decision: not yet. Keep 7 phases total; revisit if fan confusion shows up.

## 18. The one sentence (v2)

Offseason pages foreground what's next in a way that's phase-appropriate to the exact week of the year, with the draft week experience deserving its own live module, and the page gracefully terminating when a player's college career closes — all built from the same locked v5 system, just with phase-aware content.
