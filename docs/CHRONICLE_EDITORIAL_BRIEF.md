# The Chronicle — Editorial Brief

## What's broken now

Current Chronicle output (observed on ND team page, April 2026):

> **ANOMALY — 8 straight wins closing the season's sample**
> Running the last eight games end-to-end produces a run of 8 consecutive wins — a compression of outcome that a season's summary stat flattens. The pattern is often a better read of where the program is than any single number this table will print.
> *CFB Index game-log stat engine*

This reads like a stats engine describing itself. It is not what a fan wants. Specifically:

- **"a compression of outcome that a season's summary stat flattens"** — writing about statistics instead of writing about football.
- **"the pattern is often a better read … than any single number this table will print"** — the card explaining its own methodology. The fan isn't looking at the card to learn how the card works.
- **"CFB Index game-log stat engine"** — pipeline leakage. A fan reading OneFootDown doesn't want an attribution that reminds them a machine wrote this.
- **Zero proper nouns beyond "Notre Dame."** No player names. No coach names. No game dates. No archive references. No quotes. Nothing that could not be said about any 8-1 FBS team.
- **"Every season produces one of these; it's the one the program will quote to itself through the winter."** — generic gesture. Applies to every program. Strip the name and the card is reusable for Oklahoma, Oregon, UMass. That is the definition of voice failure.

A sharp OneFootDown contributor would never write these cards. A sharp fan in an iMessage group chat would never send these observations. They read like they were generated to fill a slot, which is exactly what they are.

## What the Chronicle SHOULD feel like

The fantasy: a sharp beat writer who has watched every game, read every other beat writer, and knows the program's ten-year archive cold, posts four observations per week. The observations surprise readers who already read everything. They thread the week's action to specific moments in program memory. They name names. They quote real fans.

A Chronicle card lands when, after reading it, a fan thinks one of:

1. "Huh — I hadn't noticed that."
2. "Yeah, that's exactly what I was saying in the group chat."
3. "Wait, that's like 2018."
4. "Who do I forward this to first?"

If none of those four fire, the card failed, and the slot should have been left empty.

## The voice contract — ten rules

### 1. Write like a fan who knows, not a system that reports

Every sentence should pass a BEAT-WRITER TEST: would a sharp independent blogger for this program write this sentence? If it sounds like it came from a research note, rewrite. If it sounds like narration of the data, rewrite.

Bad: *"Running the last eight games end-to-end produces a run of 8 consecutive wins."*
Better: *"Freeman hasn't lost since September. Eight in a row."*

### 2. Name names, every time

Every card contains at least one proper noun beyond the program name. A player, a coach, a specific opponent, a specific stadium, a specific date, a specific play. Generic cards — ones that could equally describe Oklahoma and UMass — fail.

Bad: *"The 70-7 over Syracuse is the season's mood-peak."*
Better: *"Benjamin Morrison's first pick since the shoulder surgery came in a 70-7 romp. Three OneFootDown writers led with it Monday."*

### 3. Thread to memory

Great Chronicle cards thread current action to specific earlier moments in the program's arc. "Hartman's road discipline is the longest stretch without a pick since Book in '19." "The QB room has 2022's silhouette: starter, blue-chip freshman, late-summer transfer." "The last time ND hung 70 was the 2015 Fiesta."

The program's historical archive (2014–now) is a resource, not just an archive page. The Chronicle reads from it as a first-class signal.

### 4. Use the program's voice — literally inject it

Every prompt to the LLM must include, verbatim, the program profile's `voice_register`, `identity_phrase`, `mantra`, `stock_phrases`, `mascot_voice`, `era_name_overrides`, `never_use`. Cards that don't carry program voice are generic. The profile IS the editorial infrastructure; the Chronicle must read from it.

A Chronicle card for UMass should sound scrappy-proud. For Alabama, dynastic-quiet-authority. For Auburn, defiant-underdog. For Vanderbilt, self-aware-underdog. If you can swap the team name in a card and it still reads, the voice hasn't bitten.

### 5. One surprise per card

Every card must reveal something a casual fan didn't already know. A new stat, a new connection, a new quote, a new angle, a new name. If the card only restates what the scoreboard showed, it has no reason to exist.

The Chronicle test: a fan who watched the game and reads two beat writers every Monday should still learn something from every card.

### 6. Kill self-referential scaffolding

The card never explains itself, never cites the pipeline, never references the taxonomy. The following are permanently banned:

- *"sample"* (it's a statistics word)
- *"stat engine"* / *"pipeline"* / *"our algorithm"* (pipeline leakage)
- *"tier 1"* / *"tier 2"* (internal program-tier taxonomy)
- *"pattern"* as the subject of a sentence (*"The pattern is often a better read"*)
- *"summary stat"* / *"summary"* (the card is the summary)
- *"a compression of outcome"* / *"a flattening of"* (meta-commentary on numbers)
- *"Every season produces one of these"* (generic gesture; applies to anyone)
- *"this table"* / *"this card"* / *"this module"* (referring to itself)
- *"methodology"* / *"scoring"* / *"the engine"* (system exposure)

If Haiku detects any of these phrases in a generated card, the card fails validation and goes back to Sonnet for rewrite.

### 7. Attribution a fan can read

Never "CFB Index game-log stat engine." The attribution field tells the fan where the observation came from in terms they'd use at a bar:

- Real source with date: *"OneFootDown · Mon"* — *"South Bend Tribune · 2d"* — *"BlueGrayGold thread · 5d"*
- Archive citation with era: *"from the Kelly-era archive"* — *"via 2018 Cotton Bowl recap"*
- Cluster citation for aggregate signals: *"from 14 beat-writer pieces this week"* — *"from three BGG threads"*
- Historical pattern (acceptable for anomaly type only): *"gamelog · 2014–now"* — *"Savant card, CFBD data"*
- Fan-intel citation when signal is the evidence: *"conversation velocity · Bluesky firehose"* — *"cohort divergence · analytics vs casual"*

If a card has no real attribution, it probably shouldn't ship this week.

### 8. Editorial prose, not sports copy

Short sentences. Concrete nouns. Active voice. The best Chronicle card is two sentences that land. No more than three.

Bad: *"A 70-7 win at home that the program closed at a +63 margin, indicating statistically significant offensive performance."*
Better: *"Seventy. At home. The program's biggest margin since the 2015 Fiesta."*

### 9. Data shown, not explained

Quote a stat and let it carry weight. Don't surround it with caveats and context-setting. The card IS the context.

Bad: *"The offensive explosive play rate of 14.2% — above the 75th percentile nationally — suggests strong downfield potential."*
Better: *"One in every seven plays goes for fifteen yards or more. Only Ohio State moves faster downfield."*

### 10. The card type is a promise

An anomaly card must actually surprise. A moment card must actually capture a moment the fanbase felt. An echo must actually connect years. A flashpoint must actually build toward something. A retroactive must actually reframe something earlier.

If the generator cannot find evidence for a given card type this week, skip the slot. A Chronicle module with 3 strong cards is better than one with 4 cards where the fourth is filler.

## Card type evidence table

Every card type is anchored to a specific proprietary data stream. The Chronicle pipeline reads from all of them in parallel.

| Type | Primary data stream | Secondary enrichment | Voice guidance |
|---|---|---|---|
| **Anomaly** | Savant percentile outliers (≥95th or ≤5th); gamelog patterns (streaks, splits, situational) | Historical distribution from 2014–now archive; peer-set comparison | Observational, analyst-like. Can be slightly technical but still program-voiced. |
| **Moment** | Fan-intel velocity spike (conversation volume vs 4-week baseline); Bluesky top post of the week; board-thread title; beat-writer headline | Game result; player involved | Cultural. Quote the fanbase. Name the player the fanbase is quoting. |
| **Flashpoint** | Upcoming-game metadata; rivalry archive meetings list; opponent profile voice; CFP implications; beat-writer build-up pieces | Historical last-meeting detail; this-year trajectories of both sides | Build-up. Stakes. Name both programs' current posture. |
| **Echo** | Historical season archive (2014–now); cosine similarity on situation features; coaching-regime parallels | Current-season signature; profile's era_name_overrides | Thoughtful, slightly melancholic. Not a gotcha — a thread. |
| **Retroactive** | Past Chronicle cards for this team this season; current trajectory | Beat-writer re-evaluations; fan-intel mood shift since original | Reframes. Always explicit: "what felt like X at the time reads now as Y." |
| **Player-arc** | Player stat trajectory; fan-intel name-velocity (how much is this player being mentioned); historical player comparisons in the program archive | Roster data; recruiting class; position coach history | Specific. Specific. Specific. One player, one pattern, one historical echo. |

Any card that cannot cite an evidence source from its primary stream should not ship.

## Pipeline — four stages

### Stage 1 — Multi-stream candidate scan (Haiku, parallel)

Scan six streams simultaneously and emit a candidate pool. Target ~30 candidates per team per week before ranking.

1. **Savant candidates**: percentile outliers, week-over-week deltas, gamelog patterns (5-game W/L streaks, home/away splits, situational splits like 3rd-and-long).
2. **Fan-intel candidates**: velocity spikes (cohort conversation volume ≥ 2x baseline), top Bluesky posts, top board threads, beat-writer headlines from the week.
3. **Archive echo candidates**: cosine similarity between current-season week-by-week features and every prior CFP-era season for this program.
4. **Rivalry candidates**: if an upcoming game involves a profiled rival, surface the last meeting, both sides' trajectories, and any build-up signals.
5. **Retroactive candidates**: look at Chronicle cards this team shipped in prior weeks — any whose framing has been overturned by later events?
6. **Player-arc candidates**: player-level stat trajectories + name-velocity from fan-intel.

Each candidate carries: `(evidence, source_citation, suggested_card_type, oddity_score, date_window)`.

### Stage 2 — Ranking (Sonnet)

From ~30 candidates, pick top 4–6 for the week. Rank by:

- **Surprise score**: would a fan reading the existing page already know this? Weight heavily.
- **Voice-fit**: can this be told in the program's voice register? (Some candidates are interesting but mis-fit — skip them.)
- **Evidence strength**: does the cited source exist, can it be linked or dated?
- **Recency × durability**: fresh but not ephemeral (don't lead with a Tuesday morning tweet).
- **Diversity**: enforce max 2 of any one card type; aim for 3–4 different types per week.

Output: ranked top candidates with justification tags.

### Stage 3 — Writing (Sonnet for standard cards; Opus for top-3 blue-blood cards weekly)

Prompt template must include, verbatim:

1. Program profile voice fields: `voice_register`, `identity_phrase`, `mantra`, `stock_phrases`, `mascot_voice`, `era_name_overrides`.
2. Negative prompt: full anti-scaffolding phrase list from Rule 6 above.
3. The candidate's evidence, source citation, suggested card type.
4. Structural constraints: headline with a specific noun; body 2–3 sentences max; attribution field must cite the actual source from Stage 1.
5. The Beat-Writer Test: *"Read your output back. Could this be written by a sharp independent beat writer for this program? If no, rewrite."*

Blue-blood programs (Alabama, Ohio State, Georgia, Michigan, Texas, USC, Notre Dame) get Opus on their single top Chronicle card per week. The ceiling must stay high.

### Stage 4 — Validation (Haiku)

For each generated card, check:

- Does the card name a specific person, date, play, or opponent beyond the program name? (Rule 2 — must be yes)
- Does the body contain any banned phrase from Rule 6's list? (Must be no)
- Does the body make a comparison or connection, not just restate? (Must be yes — check for comparative markers: "since", "like", "the first", "only", "longest", etc.)
- Is the attribution field one of the acceptable formats from Rule 7? (Must be yes)

Failures route back to Stage 3 for one rewrite attempt. Second failure: card is dropped from the week's output. Dropped cards are logged; if dropout rate >20% across a program's week, flag the profile — voice_register may need sharpening.

## Before / after examples

### Anomaly

**Before:**
> **8 straight wins closing the season's sample**
> Running the last eight games end-to-end produces a run of 8 consecutive wins — a compression of outcome that a season's summary stat flattens. The pattern is often a better read of where the program is than any single number this table will print.
> *CFB Index game-log stat engine*

**After:**
> **Eight straight, and the only one that wasn't double digits was at Stanford**
> Notre Dame hasn't lost since September. The margin: 23, 63, 22, 41, 11, 31, 17, 29. One of those was played at night on the road the week after the coaches' wife cancer diagnosis went public. The staff has not given anyone an inch of grace since.
> *gamelog · 2025 season through wk 14*

### Moment

**Before:**
> **The 70-7 over Syracuse is the season's mood-peak**
> In the post-game window around Week 13, Notre Dame's shared-text footprint spiked into the tribal vocabulary — a 70-7 win at home that the program closed at a +63 margin. Every season produces one of these; it's the one the program will quote to itself through the winter.
> *CFB Index game-log + fan-intel pipeline*

**After:**
> **The Syracuse scoreboard said 70. The boards said Morrison.**
> Benjamin Morrison's first interception since the shoulder surgery came on the second series of the fourth quarter of a game that was already 49–0. Three OneFootDown writers led their Monday columns with the play. The program has not celebrated a cornerback like this since Love in 2018.
> *OneFootDown · Mon + BlueGrayGold threads*

### Echo

**Before (hypothetical current output):**
> **Another April, another QB room without a clear QB1**
> 2022 and 2026 share the same silhouette: spring talent, late-August decision. How it resolved last time is instructive.
> *CFB Index archive engine*

**After:**
> **The QB room is 2022's room, shuffled.**
> Four years ago, Freeman's staff opened camp with an incumbent, a five-star freshman, and a late-summer transfer. They were 6–3 when they benched the incumbent. The '26 room has the same three chairs — the only question the staff is actually asking is whether they learned anything from the last time they sat down.
> *from the 2022 season archive · Freeman-era year one*

### Player-arc

**Before (hypothetical):**
> **Jordan Faison's receptions have increased**
> Jordan Faison's reception total has climbed across the last four games.
> *CFB Index player stats*

**After:**
> **Faison has the drop-catch streak Avery Davis had in 2021.**
> Four straight games with a contested-catch completion. Davis put together six in a row the year before he became the heart of the 2022 team. Faison is a sophomore. The pattern is not that he catches — it's that the ball keeps finding him when the game is tight.
> *gamelog + roster archive*

## Non-Chronicle editorial work — spillover effects

The same voice rules apply to:

- **Pulse "takes" fallback copy** when conversation signal is below floor — drawn from `profile.stock_phrases`, not boilerplate
- **Rivalry card one-line meeting commentary** — each prior meeting's one-liner must be specific, not generic
- **Historical season deep-dive** `defining_moments` cards — same anti-scaffolding rules
- **Season Arc annotations** — Rule 8 (editorial prose, short) applies

Anywhere the site generates prose that a fan reads, the Beat-Writer Test applies.

## Operational rules

- Regenerate Chronicle cards weekly during in-season, monthly during offseason.
- Log every dropped card with reason (banned phrase, no proper noun, etc.). Weekly dropout rate is a quality telemetry signal.
- Never ship a Chronicle slot empty; if no card survives, display a condensed Chronicle module ("3 observations this week" instead of 4) rather than a placeholder.
- Source attribution must resolve to a real URL or archive reference — no faking sources.
- Pull-quote cards (quoting a fan) must be real quotes from real sources (OneFootDown, BGG, Reddit, Bluesky, beat-writer Substack). Do not invent quotes.

## What this unlocks

When the Chronicle reads like what a sharp fan would send to their group chat, it becomes the moat. No other CFB site is doing this. The combination of:

1. Every program's profile voice injected verbatim
2. Six proprietary data streams scanned in parallel
3. A historical archive acting as a first-class signal
4. A fan-intelligence pipeline feeding moment + flashpoint candidates
5. A validation gate that rejects generic copy

... produces cards that cannot be reproduced by a competitor with access only to public stats. The cards feel like they were written by someone who has been reading the program for ten years, because the system has been.

That is the Chronicle.
