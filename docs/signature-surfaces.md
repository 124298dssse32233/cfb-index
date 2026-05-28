# Signature Surfaces — The 12 Things Nobody Else Can Publish

**Purpose:** The editorial products that only this stack enables. Each one is concrete, shippable, and inseparable from one or more workstreams.

**Use this doc when:** prioritizing editorial bandwidth, deciding what to ship for a calendar moment, scoping a new feature against existing infrastructure.

**Not a workstream itself:** these are *output* of the workstreams. Listed here so we don't lose sight of *why* we're building the stack.

---

## 1. Fan Calibration Scoreboard

**The claim:** "Auburn fans have been right about their team 41% of the time over our 8-week window — bottom 5 nationally."

**Sources:** Calibration ledger (WS-09) + fanbase classification (WS-02) + Reality Gap deltas (Layer 5 of signal model).

**Publication moment:** Weekly. Each week's published Reality Gap chip closes; whether the team's actual result matched the fan-belief direction gets scored.

**Why nobody else has it:** They don't log their predictions; we do.

---

## 2. Belief-to-Reality Drift Map

**The claim:** A single US map color-coded by Reality Gap. Red = belief outran structure. Blue = structure outran belief. One image, the entire CFB emotional weather in a glance.

**Sources:** Reality Gap (Layer 4 vs Layer 2) + Choropleth chart type (WS-08).

**Publication moment:** Weekly in-season. Updates with every Sunday Daily.

**Why nobody else has it:** Requires both fan-bucket conversation data + structural model + geographic mapping. Single-purpose competitors do one of three.

---

## 3. Coaching Tree Latency

**The claim:** "Disciples of Saban have won a conference title an average of 4.2 years after taking a head job; disciples of Riley average 2.1."

**Sources:** Coaches table (WS-06) + tenure history + Network chart type (WS-08).

**Publication moment:** Annually in offseason. Updates with each new HC hire that fits the tree.

**Why nobody else has it:** Requires structured coaching-tree data with succession edges + tenure outcomes. Nobody else stores both.

---

## 4. Transfer Portal Flow Sankey

**The claim:** Visualization of QBs (and other position groups) moving between programs, by year, by direction (Power Conference ↔ G5 ↔ FCS). Patterns nobody has named yet light up.

**Sources:** `transfer_entries` (14,801 rows) + Sankey chart type (WS-08).

**Publication moment:** Twice a year — end of January portal close, mid-April spring portal close.

**Why nobody else has it:** They have the transfer data but never built the visualization with editorial framing.

---

## 5. Recruit-to-NFL Pipeline Efficiency by Program

**The claim:** "Per 4★ recruit signed, what's the NFL draft probability?" Reveals which programs *develop* and which just *collect*.

**Sources:** `player_recruiting_profiles` (20,392 rows) + `player_nfl_draft` (2,316 rows) + per-program aggregation.

**Publication moment:** Annually after each NFL Draft (end of April).

**Why nobody else has it:** Recruiting sites cover recruiting. NFL Draft sites cover the draft. Almost nobody joins both at the program level with rigor.

---

## 6. Rivalry Intensity Index

**The claim:** Scoring beyond W-L. Folds in fan mood swing on rivalry week, NFL transfer counts, recruiting head-to-head wins, coaching disrespect frequency. Iron Bowl scores X.X out of 10.0; Backyard Brawl scores Y.Y.

**Sources:** Rivalry pages (WS-06) + fan-mood data (Layer 2) + portal flows (WS-05) + recruit overlap data.

**Publication moment:** Annually before rivalry week. Updates each rivalry game.

**Why nobody else has it:** Rivalry coverage is anecdotal everywhere else. This is the first quantitative scoreboard.

---

## 7. Era-Adjusted Strength

**The claim:** Alabama 2010-2020 vs Nebraska 1993-1995 vs Miami 1985-1992 — same axis, normalized for era. Bar fight starter.

**Sources:** Historical backfill (WS-04) + structural ratings normalized cross-era + Annotated Line chart type (existing vocab).

**Publication moment:** Annually in dead-period (May-June) heritage content slot.

**Why nobody else has it:** Sports Reference has the raw history; nobody has built the era-adjustment editorial layer.

---

## 8. "Quiet Seasons" — Programs that Overperformed Structure by 2+ SD with Bottom-Quartile Attention

**The claim:** "The best CFB stories never told." Identifies programs that punched above expectation in a season without media buzz.

**Sources:** Layer 1 (Attention) + Layer 4 (Structural) + historical structural data.

**Publication moment:** End-of-season retrospective (mid-January) + featured monthly during May-June dead period.

**Why nobody else has it:** Requires both attention measurement and structural performance — the underrated-team conversation usually happens informally on Reddit.

---

## 9. Generational Fanbase Mood Patterns

**The claim:** "Texas fans are most optimistic in May, peak panic in October, recover in January." 8-year cycle visualization per program.

**Sources:** Multi-year fan-bucket data (Layer 2) + per-team archetype history (WS-02).

**Publication moment:** Annual end-of-year retrospective. Per-team featured during May-June dead period.

**Why nobody else has it:** Requires multi-year longitudinal fan-mood data, which we'll be the only ones to have once Phase 1 ingest scales.

---

## 10. Calendar Pressure Forecast

**The claim:** "Sept 7 will be a 0.94-pressure day in CFB; the three storylines that will own it are X, Y, Z." Look-ahead, not look-back.

**Sources:** `calendar_pressure` populator (WS-02 dependency) + schedule data + Chronicle pipeline.

**Publication moment:** Weekly during in-season. Featured as homepage chip per VISION § 18.1.

**Why nobody else has it:** Everyone covers what happened. Almost nobody systematically forecasts narrative pressure.

---

## 11. "Has This Ever Happened Before" Queryable Engine

**The claim:** Fan asks "has my team ever lost to an unranked team after starting the season ranked top-5?" Engine returns: 12 times since 1936, here they are.

**Sources:** Historical backfill (WS-04) + event_ledger SQL view (WS-02) + Nomic embedding + cmdk semantic search (WS-10).

**Publication moment:** Always-on; featured during dead period as a heritage product.

**Why nobody else has it:** Sports Reference has the data but no queryable natural-language interface.

---

## 12. Coordinator Carousel Impact

**The claim:** Average power-rating change in year 1 after an OC change, by tier of replacement. Quantifies what fans always argue about.

**Sources:** Coaches table (WS-06) + coordinator-level tenure data + structural ratings.

**Publication moment:** Annually after coaching carousel closes (early February).

**Why nobody else has it:** OC/DC tracking is informal everywhere. This is the first systematic measurement.

---

## Beyond the 12

Additional surfaces enabled by the stack but not yet in the headline catalog:

- **Per-team archetype transition timeline** — narrated story of how a program's identity has shifted over the CFP era
- **"On This Day" auto-republishing** — anniversary content for memorable games + decisions
- **Conference realignment timeline** — interactive Sankey of how the conferences have shuffled 2014–
- **NFL Draft pipeline projections** — multi-year forecast per program of expected draft output
- **Pac-12 archive** — dignified memorial site for the dissolved conference
- **Anniversary edition every January** — calibration ledger annual report
- **The "What Changed Today" engine** — auto-publishes the day's biggest event-ledger entries

---

## Editorial Bandwidth Allocation

Per editorial cadence (`docs/editorial-rhythm.md`):

- **In-season Wire (daily M-F):** Cycles through surfaces 1, 4, 6, 10, 12 based on calendar context
- **Weekly Sunday Daily:** Always touches surface 1 (calibration) + 2 (drift map)
- **Friday Mailbag:** Reader questions about any surface
- **Annual reports (Jan):** Touch all 12 in some capacity (the "Year in Review" canon piece)
- **Dead-period (May-June):** Surfaces 7, 8, 9, 11 get the most depth (heritage + queryable)

---

## How this list grows

When a 13th surface is proposed:
1. Confirm it's genuinely unique (not just a different framing of an existing surface).
2. Confirm the data sources exist or are scoped in a workstream.
3. Add an entry here with: claim, sources, publication moment, why nobody else has it.
4. Reference the entry in the relevant workstream spec.
5. If it requires a new data source, open a DECISIONS.md entry.

---

## What this list will not become

- A list of generic "data products" — every entry must be a sentence a fan would screenshot.
- A list of "features we plan to build" — features are workstreams; this is publication-target catalog.
- A list of partner integrations — we don't have partners.

The discipline: 12-15 signature surfaces, each genuinely unique, all enabled by the same stack.
