# Editorial Rhythm — Day-of-Week + Season-Phase Spec

**Status:** Locked 2026-05-28 per [DECISIONS.md#D-019](../DECISIONS.md)
**Parent doc:** [VISION_2026_2027.md § 17](../VISION_2026_2027.md)
**Code anchors:** `src/cfb_rankings/team_pages/state_resolver.py` (`_DOW_LABEL`, `_MONTH_TO_PHASE`)

> **Read this when:** designing a new editorial surface; deciding what content drops on what day; configuring an auto-publish cron; designing voice prompts that change by phase.

---

## 1. Why the rhythm matters

The single thing that separates a CFB publication from "a sports data product that happens to cover CFB" is whether the content matches how fans actually experience the week + the year.

Fans don't think about CFB at constant intensity. Saturday is the game. Sunday is reckoning. Wednesday they're processing the next opponent. May they're patient and historical. November they're frantic. The product that matches that emotional cadence wins. The product that publishes the same "data dashboard" every day loses.

The codebase already encodes this rhythm in `state_resolver.py`. This doc locks the editorial intent.

---

## 2. The In-Season Day-of-Week Rhythm

### Monday — "licking-wounds-or-basking"

**The day:** Game autopsy. Fans wake up Sunday hung over from the result; by Monday they want to know what it means.

**Editorial archetype:** Beat-writer. Reflective, data-anchored, "here's what changed."

**Auto-publish:**
- **Wire (Monday autopsy edition)** — 4am ET. Synthesizes: scoreboard recaps with narrative angles, biggest mood-swing teams, biggest market-belief swings, archetype-transition events from the weekend (e.g., "Tennessee just moved into the `fragile-contender` modifier after the Alabama loss").
- **Per-team mood-swing chips** updated across team pages.
- **Calendar pressure chip** updated for the week.

**Manual review:**
- **Mailbag draft prep** — editor (or LLM-drafted with editor review) starts the Friday Mailbag from Monday's reader-question intake.

**Voice notes:**
- Allow editorial conviction. Monday is the day to be opinionated about what Saturday meant.
- Receipts mandatory — fans WILL fact-check Monday claims hardest.

### Tuesday — "depth-chart-injuries"

**The day:** The "what's the team going to look like Saturday" day. Injury reports drop. Depth charts get updated.

**Editorial archetype:** Local reporter. Granular, roster-focused, no opinions.

**Auto-publish:**
- **Wire (Tuesday depth edition)** — 4am ET. Depth chart deltas across the 119 FBS programs. Injury news aggregation. Coaching-press takeaways.
- **`player_depth_chart_2026` deltas** auto-detected and surfaced as `player_signal_events`.
- **NFL-pipeline chips refreshed** on player pages (mock-draft updates).

**Manual review:** None.

**Voice notes:**
- Tuesday is the day to be informative, not clever. Names + numbers + facts.

### Wednesday — "matchup-sharpens"

**The day:** Now we're talking Saturday. Matchups, gameplans, "the X-factor."

**Editorial archetype:** Analyst. Comparative, structural-data-anchored.

**Auto-publish:**
- **Wire (Wednesday matchup edition)** — 4am ET. Top-10 games-of-the-week with structural matchups (this team's OL vs that team's DL, this team's pass D vs that team's air raid).
- **Chronicle `matchup_echo` cards** for upcoming-game rivalries.
- **Reality Gap chip emphasis** on team pages (the metric is most interesting Wednesday-Friday when fans are pricing in the matchup).

**Manual review:** None.

**Voice notes:**
- Structural framing dominates. Wednesday is when the SP+/FEI/Resume content is most-read.

### Thursday — "hype-peaks"

**The day:** Thursday-night games kick off. Friday-game previews. Hype peaks.

**Editorial archetype:** Hype-curator (with discipline). Anticipatory but receipt-anchored.

**Auto-publish:**
- **Wire (Thursday hype edition)** — 4am ET. Thursday-night game preview, Friday-game preview, weekend storyline preview.
- **Chronicle pre-game cards** for Thursday games.
- **Mailbag final review** by editor (publishes Friday morning).

**Manual review:** Mailbag.

**Voice notes:**
- Allow energy. Thursday is the only day where "this is going to be a fun weekend" framing is appropriate.
- Still: no bare hot takes. Every claim cited.

### Friday — "anticipation"

**The day:** Saturday morning preview drops. Mailbag publishes.

**Editorial archetype:** Friday columnist. Conversational, fan-aware, generous.

**Auto-publish:**
- **Wire (Friday set edition)** — 4am ET. Saturday's full slate of games with one-line take per game. Weather report for outdoor games.
- **Mailbag publishes 9am ET.** Per existing cadence.
- **Daily countdown chip** updated.

**Manual review:** Mailbag final pass before 9am publish.

**Voice notes:**
- Friday is the most fan-voice day of the week. Use it.

### Saturday — "gameday"

**The day:** Game day. Live action.

**Editorial archetype:** None (the games are the editorial).

**Auto-publish:**
- **Live attention chips** updated minute-by-minute during games (computational only — no AI generation, just data refresh).
- **Win-probability spark updates** if a model is plugged in.
- **NO play-by-play.** ESPN owns this. We do not compete.
- **NO live takes during games.** Slop risk too high. Save for Sunday.

**Manual review:** None during games.

**Voice notes:**
- Saturday is the day to shut up. The games speak. Sunday is when we speak about them.

### Sunday — "autopsy"

**The day:** Post-game recap, week-wide synthesis, set up next week.

**Editorial archetype:** Sunday essayist. Thoughtful, week-wide-perspective, "what did this week tell us."

**Auto-publish:**
- **Daily (Sunday recap)** — 6am ET. Week-wide synthesis: biggest stories, biggest movers, calibration check ("we said X on Friday; here's how it played out").
- **Updated mood data** across team pages (fanbase reactions to Saturday).
- **Market-belief delta chips** updated (where did markets move?).
- **Storyline candidate queue** surfaces for editor review.

**Manual review:** Sunday editor review window. Editor reviews:
- Storyline candidate queue (3-5 candidates per week typically)
- Anything flagged by automated quality checks
- Calibration anomalies (>10pp accuracy drop?)
- Weekly calibration report ("This week's predictions: 18 of 22 correct. Per-model: Heisman 4/5, Reality Gap 7/8, archetype 7/9.")

**Voice notes:**
- Sunday is the most editorial day of the week. Allow the longest pieces, the strongest takes (still receipt-anchored), the most ambitious framing.

---

## 3. The Offseason Month Rhythm

### January — "bowl-and-carousel"

**The cycle:** CFP semis + finals + coaching changes. The transition from in-season to offseason.

**Editorial focus:** Bowl game coverage (active in early-mid Jan), then pivot to coaching carousel news as it lands.

**Cadence:**
- Wire: daily through Jan 13 (CFP final aftermath), then M/W/F starting Jan 20
- Mailbag: weekly Friday
- Storyline chapters: Coaching Carousel thread gets weekly updates through end of Jan

**Annual calibration report published end of Jan** ("Here's how the model did in [season]").

### February — "nsd-and-portal"

**The cycle:** National Signing Day (first Wed of Feb) + transfer portal final wave.

**Editorial focus:** Per-team recruiting class wraps + portal-class wraps + early "Here's what your roster looks like in 2026" pieces.

**Cadence:**
- Wire: M/W/F
- Mailbag: weekly Friday
- Storyline chapters: Portal Era Settling thread gets monthly update
- Bespoke moment: **NSD live coverage Feb 5, 2026** (or appropriate Wed)

### March–April — "spring-and-portal"

**The cycle:** Spring practice opens for all programs. Spring portal window. Spring game weekends.

**Editorial focus:** Spring practice reports + spring game takeaways + portal arrival narratives.

**Cadence:**
- Wire: M/W/F
- Mailbag: weekly Friday
- Storyline chapters: bi-weekly
- Bespoke moments: spring game weekend coverage per program (rolling March-April)

### May–June — "dead-period-heritage"

**The cycle:** True dead period. No major events. Editorial calendar shifts to historical, longitudinal, off-field.

**Editorial focus:**
- Era page launches and updates
- "On This Day" content (anniversary pieces)
- Coaching tree features
- Decade retrospectives
- Underrated programs / "where are they now" pieces

**Cadence:**
- Wire: M/W/F
- Mailbag: weekly Friday
- Storyline chapters: bi-weekly
- **Heaviest editorial bandwidth for era page work** — this is the window where Phase 2-3 era page publishes happen

### July — "media-days"

**The cycle:** Conference media days. SEC + B1G + ACC + Big-12 all hold them mid-late July.

**Editorial focus:** Day-by-day media days coverage. Coach quotes synthesis. Preseason power rankings drop.

**Cadence:**
- Wire: ramps to daily during conference-specific media days weeks
- Mailbag: weekly Friday
- Storyline chapters: weekly (the volume of news supports it)
- Bespoke moments: per-conference media days dedicated content

### August — "camp"

**The cycle:** Fall camp opens ~Aug 1. Week 0 launches Aug 23.

**Editorial focus:** Camp reports (per program), depth chart preview, Week 0 preview, the Year-13 launch piece.

**Cadence:**
- Wire: daily starting Aug 15
- Mailbag: weekly Friday
- Storyline chapters: weekly
- Bespoke moments: **Aug 23 Week 0 launch piece** — biggest editorial moment of the year. Calibration ledger reset. "Year 2 begins" framing.

---

## 4. Annual Bespoke Editorial Moments

Non-negotiable: every year, on these dates, the site has dedicated content. These are calendar fixtures.

| Date | Moment | Lead time | Content slot |
|---|---|---|---|
| Early Jan | CFP National Championship | 2 weeks | Title game preview + Day-of live attention chips + Day-after autopsy |
| Mid-Jan | Annual calibration report | 1 month | "Here's how the model did" — long-form |
| First Wed of Feb | National Signing Day | 1 month | Live coverage + per-team recruiting class wraps |
| Mid-March | Spring portal window opens | 2 weeks | Portal-class running update |
| Mid-April | Spring games | 1 month rolling | Spring game weekend takeaways per program |
| Late May | Memorial Day weekend | 2 weeks | Era page launches + military-academy heritage content |
| Mid-late July | Conference media days | 1 month | Day-by-day per-conference coverage |
| Aug 1 | Fall camp opens | 2 weeks | Camp-watch tracker per program |
| **Aug 23, 2026 (Week 0)** | **Season opens** | **2 months** | **"Year 2" launch + calibration ledger reset** |
| Last Wed of Nov | College Football Saturday rivalry week | 1 month | Rivalry Saturday content blitz |
| Early Dec | CFP committee selection | 2 weeks | 12-team bracket coverage + selection reaction |
| Mid-Dec to early Jan | Bowl season | 1 month rolling | Per-bowl coverage |

---

## 5. The Transition Windows

Two transitions matter most operationally.

### Offseason → In-Season Transition (Aug 9 – Aug 30, 2026)

**Triggers automatic changes across the system:**
- **Phase swap** in `_MONTH_TO_PHASE` from `camp` to `early-season`.
- **Chip relabel:** "Fanbase Awareness" → "Fan Belief" per [D-009](../DECISIONS.md).
- **Wire cadence** changes from M/W/F to daily.
- **Chronicle generation cadence** changes from weekly to daily during game weeks.
- **Calibration ledger** zeroed for new season; prior-season summary frozen.
- **Mailbag** retains weekly Friday cadence.

**Manual editorial:** "Year 2 begins" launch piece publishes Aug 23 morning.

### In-Season → Offseason Transition (mid-Jan)

**Triggers automatic changes:**
- **Phase swap** to `bowl-and-carousel`.
- **Chip relabel** reverses to "Fanbase Awareness."
- **Wire cadence** ramps down from daily to M/W/F by Jan 20.
- **Chronicle generation cadence** ramps down.
- **Annual calibration report** drafted automatically; editor reviews before publish.
- **Editorial bandwidth** shifts toward era page work and historical features.

**Manual editorial:** "How we did" annual calibration piece publishes Jan 25-30 typically.

---

## 6. The Auto-Publish vs Review Gates

Per [D-020](../DECISIONS.md), every editorial surface has a gate:

| Surface | Day | Auto-publish gate | Review queue gate |
|---|---|---|---|
| Wire | Daily/M-W-F | Auto if all Chronicle cards in it pass voice + fact + receipt at confidence ≥ medium | Auto unless any card fails — then editor reviews before publish |
| Mailbag | Friday 9am | Never auto — always editor reviewed | N/A |
| Daily | Sunday 6am | Auto if voice_validator passes | Editor reviews Sunday-morning queue |
| Storyline chapters | Bi-weekly / weekly | Never auto — always editor reviewed | Sunday editor review window |
| Chronicle cards | Continuous | Auto if confidence_band ≥ medium AND voice_validator passes AND fact_critic ≥ 0.75 AND receipt density ≥ 1/200 | Auto unless any gate fails |
| Era page lede regen | Quarterly | Auto if voice + receipt pass | Quarterly review |
| Profile additions/changes | On-demand | NEVER auto | Always reviewed |
| Archetype/refuse-list changes | On-demand | NEVER auto | Always reviewed + DECISIONS.md entry |

---

## 7. The Override Workflow

Per D-020:

- **Daily digest** (in-season) / **weekly digest** (offseason) shows everything that auto-published.
- **`/retract <url>`** — flags content, removes from live site, opens issue. One command.
- **`/amend <url> "fix description"`** — marks for human-revised reissue.
- **`/freeze <workstream>`** — pauses auto-publish for that workstream until unfrozen.

These commands exist as CLI subcommands (to be built in Phase 2). Until built, override is via direct git revert + redeploy.

---

## 8. The Trust Pre-Conditions

Per D-020 § 5, three conditions must hold before going fully autonomous:

1. **Calibration ledger has ≥3 months of resolved predictions** within stated confidence bands. Target: Nov 2026.
2. **Voice_validator + chronicle_banlist coverage** at every editorial surface (not just Chronicle). Target: end of Phase 1 (Jul 2026).
3. **Override workflow tested end-to-end** for each command. Target: Phase 2 (Aug-Sep 2026).

Until those three hold, auto-publish only covers chip-level renders. Editorial cards stay in review queue.

---

## 9. What this means for the editorial product over a year

A reader who returns to the site every Monday in season sees a Monday-shaped autopsy, every Sunday sees a Sunday-shaped synthesis, every Friday gets the Mailbag. The cadence becomes legible. Fans plan around it.

A reader who returns in mid-June sees patient, longitudinal content — era pages, anniversary features, coaching trees — not a frantic "here's what's trending today." The product matches the calendar.

A reader who returns Aug 23 sees the calibration ledger reset, the "Year 2 begins" launch piece, the chip labels swapped to in-season mode. The site signals "the season is on" without anyone editing copy.

This is what "bespoke to CFB" means at the operational layer.
