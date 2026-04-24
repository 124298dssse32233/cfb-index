# CFB Index — Team Page Engagement Brief

**Status:** Synthesis + product direction. Companion to `TEAM_PAGE_WORLD_CLASS_BRIEF.md` (architecture) and `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` (design system).
**Owner:** Kevin (product), Claude (research + drafting).
**Last updated:** 2026-04-23.
**Purpose:** Where the World-Class Brief answers *what to build*, this answers *how it feels* — the emotional experience, the engagement mechanics, the things that make someone screenshot a page and come back tomorrow.
**North star:** A 20-year-old who just started watching CFB and a 40-year-old who's watched since Bowden should both feel the page was built for them, in that order.

---

## Preface: What the Current Pages Get Right and Wrong

Before the brief, a diagnosis. The current Alabama and Georgia team pages (audited against the live build, April 2026) already do several things well: the Season Rating Journey line chart is genuinely good — hoverable game markers, directional coloring, highlight cards for biggest swings. The Fanbase Archetype module ("The Anxious Dynasty" for both Alabama and Georgia) is strong conceptually. The hero stat ribbon (Record / Power / Resume / Net Points) is cleaner than ESPN's equivalent.

What they get wrong, and why it matters for this brief:

The page opens with four stat tiles — Record, Power, Resume, Net Points — and then immediately hits a "Team Mood Card — Offseason Mode" empty state and an "Awaiting Signal" cohort panel before anything narrative happens. A casual fan who arrives from a tweet about Georgia's bowl loss gets: four numbers they don't understand, a closed door, another closed door, and then an archetype label. There is no sentence that explains what Georgia *is* right now. There is no emotional hook.

The page knows *a lot* about Alabama. It knows their rating journey, their biggest game swings, their archetype. It just hasn't decided what it believes. A great sports page has a *point of view*. That's the gap this brief closes.

---

## Research Foundations

*Before the twelve sections, the research that grounds them.*

### What ESPN Gets Wrong for Casual Fans

A 20-year-old who just started watching CFB arrives at ESPN's Alabama team page and encounters: a photo of the stadium, a record (11-4), a schedule table, a roster table, and a stats table. What's missing isn't data. It's a sentence. ESPN's page cannot answer the question every casual fan actually walks in with: *"What's the deal with this team right now?"*

The deeper failure is structural. ESPN's page is designed for someone who already cares — someone who wants to confirm information they already have, not someone who needs to be won over. The above-the-fold zone contains nothing that tells a story. The photo is decorative. The record requires context to interpret (is 11-4 good for Alabama?). The schedule is a lookup table, not a narrative. There is no editorial thesis.

The emotional experience for a casual fan is: *professional but cold*. They got the answer to a question they didn't have. They still don't know what the deal is.

**The design lesson:** The first thing above the fold should answer "what's the story here" before it answers "what are the numbers." Numbers serve the story. The story is not an appendage to the numbers.

### What The Athletic Does That No One Else Can Replicate

The Athletic retains subscribers on the back of one thing: *telling you what it means*. Not what happened — anyone can report what happened. Not the numbers — anyone can publish the numbers. But the sentence that takes the numbers and the events and tells you what they mean for this team's arc, this season's story, this program's place in history.

"Alabama lost to Florida State in Week 1 because Kalen DeBoer's offense is still learning to take risks" is a sentence that ESPN cannot write because ESPN doesn't have opinions. CFB Index can write it because the FI data shows what Alabama fans were saying the week it happened, the SP+ model shows how much the rating moved, and the design system has a place for that sentence.

The Athletic's model for CFB Index means: every factual module needs a sentence that says what it means. Not as a tooltip, not as a footnote — as the lead. The rating journey chart should have a one-sentence interpretation above it, not just a legend. The archetype label should have a one-sentence gut-punch before the description. The rival heat thermometer should have a one-sentence read before the numbers.

**The design lesson:** Data earns the right to exist by being interpreted. Uninterpreted data is a lookup table. Interpreted data is a story.

### How NBA Twitter Creates Team "Vibes" (and What CFB Index Can Learn)

"The Nuggets are built different." "The Celtics don't lose at home in the playoffs." "The Lakers are a soap opera that occasionally wins basketball games." These aren't statistical claims — they're identity claims, and they travel on social media because they're *argumentable*. You can agree or disagree. You can screenshot them and show your friend. You can stake your credibility on them.

The best CFB fanbase identities work the same way. "Alabama fans are never happy, even when they're winning." "Georgia fans have been waiting for this level of dominance their entire lives and they're still nervous." "Ohio State fans have convinced themselves every year is the year they finally beat Michigan — and then they don't." These are sentences that travel. They're recognizable, debatable, emotionally resonant.

What NBA Twitter does structurally that CFB Index should replicate:
- **One identity claim, stated simply.** Not "the Nuggets have high cohort alignment and positive sentiment" but "the Nuggets are built different."
- **The claim is specific to *right now*, not generic.** The Lakers are always a soap opera — but *this year* the soap opera is about the coach.
- **The claim is slightly over-stated so it's worth arguing with.** "Always" and "never" generate engagement. Qualified hedging does not.

**The design lesson:** The fanbase archetype label and the "Story Right Now" headline need to be slightly bold. Slightly more than the data strictly supports. The FI system generates precision; the design system needs to have the courage to make a claim with it.

### The 3–5 Hero Moments That Make Sports Pages Viral

The best sports data visualizations become cultural objects because they do one of three things: they *reveal a truth fans suspected but couldn't prove*, they *create an argument where none existed before*, or they *make the abstract visceral*. Examples:

- **Baseball Savant's sprint speed leaderboard** — revealed that some players no one talked about were the fastest in baseball. Created arguments. Made "speed" measurable.
- **FiveThirtyEight's Elo ratings** — made the historical quality of NBA franchises comparable across eras. Every time someone argued "best dynasty ever," they could point to this.
- **538's Game Predictions** — made "what are our real odds" quantifiable before the game started. Created pre-game ritual.
- **ESPN's QBR** — controversial specifically because it was opinionated. The controversy *was* the engagement.
- **PFF grades** — created a new language for evaluating individual players. "His PFF grade was 91" became something you could say in an argument.

CFB Index equivalents that have the same potential:

1. **The Rival Heat Thermometer pre-game** — "How scared is the other fanbase right now?" is the question every fan walks into rivalry week with. Showing it with data creates the screenshot moment.
2. **The Reality Gap callout** — "Alabama fans are 1.4 standard deviations more bullish than what the SP+ model says. They see something it doesn't — or they're in denial." That sentence is shareable.
3. **The Fanbase Archetype migration** — showing that a team's fanbase shifted from "The Believers" to "The Fractured Kingdom" after a coaching change is a story no one else tells.
4. **The Season Rating Journey with fan mood underlay** — showing that Alabama's mood was actually pessimistic even during a 6-game win streak creates an argument: "why were fans unhappy when they were winning?"
5. **The "Quiet Years" chip** — surfacing that a team is ranked #38 in national media mentions but #12 in SP+ is an argument-starter every fan of an underrated program wants to share.

### Designing for the 5-Second Fan Without Patronizing the 5-Minute Fan

This is the hardest single UX problem in sports media. The solutions that work:

**Spotify Wrapped** structures information as a *journey*, not a dashboard. You get one number, then the context for that number, then the comparison, then the "here's what that means" — each screen builds on the last. You never feel overwhelmed because you're always looking at one thing.

**Apple Fitness summaries** lead with the achievement ring (one visual, maximum signal density) and let you tap into the detail. The ring works as a 2-second read. The behind-the-ring detail works as a 2-minute read. The same visual serves both audiences.

**ESPN's "Quick Facts" bar** fails because it treats all facts as equal. Capacity, founded, record, AP rank, coaching staff — all get the same visual weight. A casual fan doesn't know which one to look at. The solution isn't fewer facts; it's a *hierarchy of facts*.

The CFB Index solution: the page has an invisible but felt "fast lane" — a path from top to bottom that gives a complete picture in 5 seconds without requiring the fan to understand what they're skipping. Every element in the fast lane is labeled with its emotional function, not its data function. "Here's the vibe." "Here's where they are." "Here's what's next." The deeper modules are obviously secondary — they don't compete for attention with the fast lane.

### CFB Fanbase Archetypes — The Full Taxonomy

The current system identifies "The Anxious Dynasty" for both Alabama and Georgia. But fanbases are more varied than this. Based on the FI framework and CFB landscape, here are the 18 distinct emotional states a fanbase can occupy:

**Identity archetypes** (what the fanbase believes it is):
1. **The Anxious Dynasty** — elite programs whose fans can never fully relax. Alabama, Georgia, Ohio State. Signature phrase: "Are we still elite?"
2. **The True Believers** — full conviction, low external validation needed. Often mid-majors or ascendant programs. Signature phrase: "We know what we are."
3. **The Siege Mentality** — high belief despite external criticism or disrespect. Programs that feel overlooked. TCU 2022, Boise State in their peak years. Signature phrase: "Nobody believes in us but us."
4. **The Blue Blood in Waiting** — a program with historic pedigree that's been underperforming but expects to return to greatness. Tennessee, Michigan State, USC in rebuild years. Signature phrase: "Our time is coming."

**Crisis archetypes** (what the fanbase believes is wrong):
5. **The Fractured Kingdom** — high internal divergence; the fanbase is fighting itself more than the rival. Texas 2019-2021 energy. Signature phrase: "We can't even agree on the problem."
6. **The Powder Keg** — moderate record but extraordinary volatility in sentiment. One bad game away from a coaching fire. Signature phrase: "One more and we're done."
7. **The Doomers** — negative sentiment despite winning. Usually highly analytical fanbases that know the schedule was soft. Signature phrase: "We're going to get exposed."
8. **The Cope Machine** — rationalizing every loss into context. Talent gap, injuries, rebuilding year — every failure has an explanation. Signature phrase: "But we would have won if..."

**Aspiration archetypes** (what the fanbase is reaching toward):
9. **The Breakthrough Waiters** — a program one big win away from national relevance. James Madison, Liberty, UTSA in a breakthrough season. Signature phrase: "This is finally our year."
10. **The Redemption Arc** — recovering from a low point (coaching scandal, NCAA sanctions, prolonged losing). Penn State post-sanctions, Houston post-2019. Signature phrase: "We're back."
11. **The Conference Chip** — a program laser-focused on their conference context, not the national picture. Works at any level. Signature phrase: "We don't care about the CFP, we care about the West."
12. **The Floor Raisers** — a fanbase that has recalibrated expectations downward and is finding joy in incremental progress. Kansas before Lance Leipold. Signature phrase: "We're just happy to be here, honestly."

**Contextual archetypes** (shaped by external situation):
13. **The Rivalry Obsessives** — a fanbase where the rival game is the entire season. Michigan pre-2021 vis-à-vis Ohio State. Auburn fans vis-à-vis Alabama. Signature phrase: "Beat [rival] and the season is a success."
14. **The Entitled Class** — a fanbase that expects to compete for championships every year and treats anything less as failure. Recent Georgia, Alabama. Signature phrase: "This is unacceptable."
15. **The Quiet Observers** — low volume, watching and waiting. Often G5 programs with small but loyal audiences. Signature phrase: "We don't make noise, we win games."
16. **The Romantic Fanbase** — deeply attached to history, tradition, and identity over winning. Notre Dame fans who cite Lou Holtz during a 7-win season. Signature phrase: "This means more than wins."
17. **The Analytics Insurgents** — a fanbase where the analytics cohort is loudest and most influential, often at odds with tradition. Michigan, Stanford at various points. Signature phrase: "The coach's fourth-down decisions are the problem."
18. **The Portal Paranoids** — a fanbase currently consumed by roster construction anxiety. Post-portal era has produced this archetype at programs mid-transition. Signature phrase: "Who's leaving? Who's coming? I can't keep up."

**What makes each identifiable from conversation data:**
- Volume spike patterns (do they spike after wins or only after losses?)
- Cross-platform agreement score (do they agree with each other?)
- External mention tone vs. self-generated tone (chip-on-shoulder score)
- Portal/recruiting mention frequency vs. on-field results frequency
- Historical reference frequency (do they cite past eras constantly?)
- Doom keyword density vs. belief keyword density

### The Narrative Spine — What Every Great Team Page Needs

Every team has exactly one story right now. Not five. Not a dashboard full of stories. One. And that one story should be stateable in two sentences. Examples of what great sports media does:

*"Georgia is the team that keeps proving the doubters wrong but somehow the doubters multiply. Their next test isn't a bad team — it's a narrative about January."*

*"Alabama is in a transition they won't fully admit. Kalen DeBoer has the talent. He hasn't yet found the identity."*

*"James Madison is what happens when a program outgrows its context. They're playing Sun Belt football but they're thinking Power-4 thoughts."*

*"Ohio State is the bridesmaid that finally won one. The question is whether they can stop being defined by what they almost did."*

The generation algorithm for these sentences is the core product challenge. It's addressed in detail in Section C.

---

## A. The Emotional Contract

*What does a fan feel when they land on this page? Not what they see — what they feel.*

The team page makes four distinct emotional promises, one for each fan type. Keeping these promises simultaneously, without compromise, is the design challenge.

### The Casual Fan (arrived from a tweet, first visit, unfamiliar with CFB Index)

**They feel:** *Oriented within 3 seconds without having to work for it.*

The casual fan's nightmare is arriving somewhere and feeling lost. They don't know what Power means. They don't know what Resume percentile means. They might not even know Georgia's record. Their emotional need is the most primal one in media: *make me feel like I'm in the right place and that there's something here worth 30 more seconds of my time.*

The contract we make with them: **The first thing you see tells you what this team's deal is, in plain English, without requiring any prior knowledge.** If they land on Georgia's page during the SEC Championship week, they see Georgia's name, their record, and a sentence: *"The standard. 12-1, SEC title in sight, and a fanbase that's still somehow nervous."* That's the deal. They know what they need to know. Everything else is optional.

What we do NOT do: hit them with a four-number stat ribbon as the headline. Record / Power / Resume / Net Points requires three pieces of prior knowledge (what's a good Power? what's a good Resume? what are Net Points?) before it has any meaning. We keep all four numbers — but they're not the headline. The headline is the story.

### The Die-Hard Fan (checks every Monday morning, knows the SP+ landscape, emotionally invested)

**They feel:** *Confirmed, challenged, or surprised — never ignored.*

The die-hard fan doesn't need orientation. They need *the reading for this week*. They want to know: what does the model think after last Saturday? What does the FI data say about where the fanbase's head is? Did anything shift? They're coming back to an instrument they trust, not discovering something new.

The contract we make with them: **The page has moved since last week, in ways that matter.** The "Story Right Now" headline has updated. The mood dial has a new reading. The Season Rating Journey has a new data point. The archetype might have shifted. They get a *delta* from their last visit, not just a snapshot. They feel like they're reading a weekly update, not a static profile.

What we do NOT do: make them scroll past three zones of basics before they get to the new information. For return visitors, there should be a "What changed" signal near the top — even just a chip: *"Updated Mon Apr 21 — Mood shifted: +0.4 SD this week."*

### The Data Nerd (analyst, uses advanced metrics, wants to geek out, will share something interesting)

**They feel:** *Respected. Rewarded for going deeper.*

The data nerd has a specific need: they want to find something on this page that they can *use in an argument*. A number, a chart, a comparison — something specific and defensible that they didn't already know. They will tolerate a high information density if the information is good. What they won't tolerate is vagueness dressed up as data ("Resume: 96 percentile" means nothing without knowing what it means to be 96th percentile vs. this opponent set).

The contract we make with them: **Every number has context. Every context has a comparison. Every comparison has an interpretation.** Alabama's SP+ isn't just shown — it's shown in relation to their conference, their historical average, and what it means for their ceiling. The Savant Card gives them 15 percentile bars to explore. The Cohort Divergence stack shows them which fan cohort is the outlier and why. They leave with three things they didn't know when they arrived.

What we do NOT do: hide the interesting stuff three scrolls down without any signal that it's there. The data nerd needs to know within 15 seconds that the depth exists. A "Savant Card below ↓" chip near the top or a sticky subnav that shows "Savant | Rivalries | Deep Dive" tells them where to go.

### The Rival Fan (came to hate-read, probably doesn't like this team, looking for confirmation of their priors)

**They feel:** *Surprised to find themselves interested. Maybe even a little respectful.*

The rival fan is the hardest person to design for because they arrive adversarially. Ohio State fan visiting Michigan's page during rivalry week. Auburn fan on Alabama's page after the Iron Bowl. They want to see the opposing fanbase's angst, the flaws in the record, the reasons their team is overrated. They're not coming to learn — they're coming to confirm.

The contract we make with them: **The Fan Intelligence data is honest enough that it tells a story the rival fan wasn't expecting.** If Alabama fans are genuinely anxious despite a 9-2 record, the rival fan finds that interesting. If Georgia fans are more fractured than the record suggests, the rival fan finds that useful. The Rival Heat module shows them *their own fanbase's heat reading* toward this team — which is often flattering to both parties in an uncomfortable way.

What we do NOT do: make the page feel like a press release for the team. The fanbase archetype "The Anxious Dynasty" is not flattering to Alabama fans. The Reality Gap callout is honest. The Cohort Divergence showing internal fractures is honest. Honest data is the thing that converts a hate-reader into a return visitor.

---

## B. The Hero Section — "The Story Right Now"

*The most important real estate on the page. Designed for 5 seconds on a 375px phone.*

### The Principle

The hero section does one job and one job only: **make the fan feel oriented and intrigued in 5 seconds.** Oriented means: I know who this team is and where they are. Intrigued means: I want to know more.

This is not the job of four stat tiles. It is the job of a sentence.

### The Five Elements

On mobile (375px wide), above the fold, exactly this — in this order, in this visual weight:

**1. Identity Anchor** (visual, instant)
Team logo (left-anchored, 56px), team name in display type, record in large tabular numerals, conference + season context chip. This is the "you're in the right place" signal. 2 seconds.

**2. The Story Right Now** (headline, always updated)
One sentence. 14-18 words. Dark card surface with team accent color at 8% opacity. The most editorial element on the page and the most important. Updated every Monday in-season, bi-weekly in off-season. Examples below. 1 second.

**3. Fanbase Archetype Label + Mood Ring** (emotional truth)
The archetype name ("The Anxious Dynasty") with a mood ring — a small animated circle, filled with the belief ramp color at the current week's sentiment reading. No numbers on first view. Just color and label. The ring has a slow pulse animation calibrated to conversation volume (faster = more conversation). 1 second.

**4. Season Standing Rung Pill** (position)
One pill: the team's current Season Standing Rung label. "CFP CONTENDER" or "BOWL ELIGIBLE" or "REBUILDING" or "CHAMPION." Not a number. The label. 0.5 seconds.

**5. Next Game Context** (temporal anchor)
If within 14 days of a game: opponent name, countdown, current line. "vs Ohio State · Sat 4:30pm · Pick'em." If off-season: most relevant forward-looking signal ("Recruiting class: Ranked #8 · 14 commits"). 0.5 seconds.

**Total: 5 seconds. Three taps to go deeper.**

### Specific Examples for Three Teams

---

**GEORGIA — Mid-Dynasty (2025 Season, Week 12, 11-1, SEC Championship next)**

*Identity:* Georgia · 11-1 · SEC Conference · Dynasty Active (Tier 6)
*The Story Right Now:* "The dynasty is running out of ways to lose. Georgia controls its own destiny — for the third straight year."
*Archetype label:* The Anxious Dynasty · Mood ring: 67/100, warm amber. Pulse: moderate. The wins aren't producing relief — they're producing expectation.
*Season Standing:* CFP CONTENDER
*Next Game:* vs Alabama · SEC Championship · Sat 4pm · Georgia -3.5

**What this communicates in 5 seconds:** Georgia is good, they're in the championship game, and their fans are somehow still nervous about it. All three pieces of information land without requiring any prior knowledge.

---

**MICHIGAN — Rebuilding (2025 Season, Week 8, 4-4, post-Harbaugh era, year 2 of Sherrone Moore)**

*Identity:* Michigan · 4-4 · Big Ten · Blue Blood (Tier 5) — Historical peak: Dynasty Active (2021-23)
*The Story Right Now:* "Michigan is still trying to find itself after the dynasty. Year 2 of Sherrone Moore is looking like Year 2 of a rebuild, not a return."
*Archetype label:* The Blue Blood in Waiting · Mood ring: 31/100, cool blue-grey. Pulse: elevated (lots of argument). The belief has dropped but the engagement hasn't — people are *fighting* about this team, not ignoring it.
*Season Standing:* BOWL ELIGIBLE (barely)
*Next Game:* vs Ohio State · The Game · Sat 12pm · Ohio State -14.5

**What this communicates in 5 seconds:** Michigan is struggling, they're still a brand name, and Ohio State is next. The line tells you exactly where they stand.

---

**JAMES MADISON — Mid-Major Breakout (2025 Season, Week 10, 8-1, Sun Belt leading)**

*Identity:* James Madison · 8-1 · Sun Belt Conference · Mid-Major Contender (Tier 2) — Rising
*The Story Right Now:* "James Madison is playing G5 games but thinking P4 thoughts. The Sun Belt title is a floor, not a ceiling."
*Archetype label:* The Breakthrough Waiters · Mood ring: 89/100, bright green. Pulse: fast (surging conversation). High belief, high volume — the fanbase knows something is happening.
*Season Standing:* CONFERENCE LEADER
*Next Game:* vs Coastal Carolina · Sat 3:30pm · JMU -10.5

**What this communicates in 5 seconds:** James Madison is very good for their level, their fans are excited, and they're eyeing something bigger. The "G5 games but P4 thoughts" framing is debatable enough to be interesting.

---

### Design Notes on The Story Right Now

- The headline sentence lives in its own card element, slightly elevated from the stat tiles. It is not a subheading. It is a *claim*.
- Font: Inter Display, 18px mobile / 22px desktop. Slightly lighter weight than the team name so the team name still anchors.
- The sentence should use active voice and present tense. "Georgia is" not "Georgia has been." "Michigan is trying to find itself" not "Michigan is in a transitional period."
- The sentence is not the archetype description repackaged. It is specific to *this season, this moment*. If it could apply to this team five years ago, it's too generic.
- When the narrative is stable (model didn't move, FI didn't spike, no major news), the sentence stays the same but gets a subtle "Updated [date]" chip so return visitors know it was checked.

---

## C. The Narrative Engine

*How CFB Index generates and maintains the 1-2 sentence "story right now" for 130+ FBS teams.*

### The Inputs (in priority order)

The narrative engine draws from six signal layers, each with a defined weight and update trigger:

**Layer 1 — Season Result Context (weight: 35%)**
Current record + schedule strength + trajectory direction. Is the record tracking above, at, or below preseason SP+ expectations? What's the recent form (last 3 games)? Has the team hit a turning point — a major win or loss that changed the story?

Trigger: updates every Monday after a game result.

**Layer 2 — FI Belief Direction (weight: 30%)**
The current week's mood reading + the direction of travel (rising/falling/flat) + whether FI is diverging from SP+ (Reality Gap). This is the emotional overlay on the factual foundation. A team can be 8-2 with declining FI sentiment — the model picks that up.

Trigger: updates with each weekly FI publish cycle.

**Layer 3 — Archetype + Archetype Modifiers (weight: 15%)**
The active archetype shapes the *tone* of the narrative, not the facts. "The Anxious Dynasty" generates different language than "The Believers" even if the records are similar. The modifier chips (Entrenched / Ascendant / Fading / Volatile) refine the narrative template.

Trigger: archetype shifts trigger a full narrative regeneration.

**Layer 4 — Program Historical Context (weight: 10%)**
How does this season compare to this program's baseline? Alabama at 11-4 is below historical baseline — that matters. James Madison at 8-1 is above their typical trajectory — that matters differently. The narrative uses the Prestige Rail context (Season Standing vs. Program Prestige mismatch = story).

Trigger: static context that anchors the narrative; updates seasonally.

**Layer 5 — High-Signal Recent Events (weight: 5%)**
Coaching news, major recruiting commits/decommits, portal activity, injury announcements. These are override signals — if a coordinator leaves, the narrative acknowledges it even if the record is fine.

Trigger: event-driven; requires a Tier 1/2 source signal above a threshold.

**Layer 6 — National Context (weight: 5%)**
CFP picture, national ranking movement, conference standing. Used to give the "why it matters nationally" frame to the narrative.

Trigger: updates with rankings publications (Sundays in-season).

### The Narrative Templates

The engine uses 12 base templates, selected by the dominant archetype + season situation:

```
TEMPLATE_DYNASTY_PLATEAU     — "[Team] isn't losing ground, but they're not gaining it. 
                                [Context]. The question isn't whether they're elite — 
                                it's whether elite is enough this year."

TEMPLATE_DYNASTY_ASCENDANT   — "The [Team] dynasty isn't finished — it's accelerating. 
                                [Result context]. [FI read: fans believe X]."

TEMPLATE_DYNASTY_STRESSED    — "[Team] is doing the thing dynasties do when they're 
                                stressed — [specific behavior from FI data]. [Historical 
                                context]. The machinery is still running."

TEMPLATE_REBUILD_EARLY       — "Year [N] of [Coach]'s [Team] still has more questions 
                                than answers. [Specific unresolved question]. [FI read]."

TEMPLATE_REBUILD_SIGNAL      — "[Team] is starting to look like what [Coach] promised. 
                                [Key evidence]. Fans are cautiously buying in."

TEMPLATE_BREAKOUT            — "[Team] is playing [level] games but thinking [higher level] 
                                thoughts. [Key marker]. The fanbase knows something the 
                                rankings haven't caught up with."

TEMPLATE_RIVALRY_OBSESSION   — "[Team]'s season comes down to one thing. It always does. 
                                [Rivalry game context]. Everything else is prologue."

TEMPLATE_CHAOS               — "[Team] is in the strange territory where wins feel fragile 
                                and losses feel inevitable. [Specific volatility marker]. 
                                The fanbase is fighting itself more than the opponent."

TEMPLATE_QUIET_EXCELLENCE    — "[Team] keeps winning without getting the credit they've 
                                earned. [SP+ vs. media mention gap]. The underrated tag 
                                is either a badge of honor or a self-fulfilling prophecy."

TEMPLATE_HISTORICAL_PEAK     — "[Team] is having the best [timeframe] in program history 
                                by [specific metric]. [Context]. The record books are 
                                paying attention."

TEMPLATE_FLOOR_RAISING       — "[Team] isn't trying to be what they were. They're trying 
                                to be better than last year. [Incremental marker]. 
                                That's not a small thing."

TEMPLATE_OFFSEASON_WATCH     — "[Team] finished [end of season read]. The off-season story 
                                is [portal/recruiting/coaching context]. [Forward signal]."
```

### The Rules for Stability vs. Change

**The narrative changes when:**
- An FI spike exceeds ±2 SD from the team's own seasonal baseline (emotion shifted)
- A game result lands more than 1.5 Power points above or below the pregame projection (surprise changed the story)
- The fanbase archetype classification changes (identity shifted)
- A Tier 1 or 2 high-signal event fires (coaching news, major recruit)
- The team enters or exits a meaningful season milestone (bowl eligibility, CFP contention, elimination)

**The narrative stays stable when:**
- Results are tracking the model within 0.5 Power points (expected)
- FI is in a normal range (within 1 SD of team baseline)
- No major off-field events
- The team hasn't crossed a milestone threshold

**The update cadence:**
- In-season: evaluated every Monday, published if any change trigger fires
- Off-season: evaluated bi-weekly, typically stable unless portal/coaching news fires a trigger
- Maximum stability: a narrative is always reviewed after 21 days even if no triggers fire

### Quality Gates

Before a narrative publishes, it passes three checks:
1. **Specificity check** — Does the narrative name something specific (a number, a game, a pattern) or is it generic enough to apply to any team in a similar situation?
2. **Recency check** — Does the narrative reflect information from the last 14 days, or is it describing a state that's already resolved?
3. **Tone match check** — Does the tone match the archetype? An "Anxious Dynasty" narrative should have a different emotional register than a "Breakthrough Waiters" narrative, even if the facts are similar.

---

## D. The Fanbase Pulse — Redesigned

*"The Room on [Team]" needs to feel alive, not like a dashboard.*

### The Problem with the Current Design

The current Mood Card shows seven labeled empty tiles in the offseason, and seven labeled data tiles in-season. The tile format treats fan intelligence like a scoreboard — here's the reading, here's the label, next. There's no *sense of what it feels like to be this fanbase right now*.

A better metaphor: the Mood Card should feel like you're listening to a room. Not reading a report about the room — *listening to it*. The design should communicate tone before it communicates data.

### The Visual Metaphor: The Pulse

The redesigned "Room on [Team]" leads with a single dominant visual — the **Fanbase Pulse** — before it shows any numbers.

**What it looks like:**
A full-width horizontal band, approximately 100px tall on mobile. No labels, no numbers — just color and motion.

The band is filled with the belief ramp color at the current week's sentiment reading. A slow, organic breathing animation (expand/contract at 3-second intervals) communicates that something is alive here. The animation speed is calibrated to conversation volume — a high-volume week means slightly faster pulse; a quiet week means slower. This is a *felt* experience, not an *explained* one.

Below the pulse band, three pieces of information emerge in sequence (300ms stagger):
- The archetype name in large type: **THE ANXIOUS DYNASTY**
- One generated sentence in the belief ramp color: *"Cautiously optimistic — the most they've allowed themselves to feel since the Week 5 Georgia win."*
- The confidence chip: *"High confidence · 847 mentions this week"*

Only then, on tap/scroll, do the data panels appear.

### The Five Panels (Redesigned)

**Panel 1 — The Belief Dial** (visible by default)
The existing `mood-meter-track` implementation, promoted to full-width instead of a sub-tile. Current week pinned with a filled circle. Last week as a ghost tick. Start-of-season as a dotted baseline. The dial is the most legible single signal — lean into it.

Below the dial: a small generated sentence about the *direction*. Not just the level — the direction and what's driving it. *"Up 0.4 points this week. The Oklahoma win moved the needle more than the model predicted."*

**Panel 2 — The Five-Axis Strip** (revealed on first tap)
Five compact meters, each 44px tall with a label and a one-sentence read:

- **Reality Gap** — fan belief vs. SP+ model. Color-coded: green = fans are more bullish than model, red = fans are more pessimistic. The sentence explains the direction: *"Fans are calling it before the model does — or they're in denial. Probably both."*
- **Respect Gap** — fan belief vs. national media perception. *"The country underrates this team. The fanbase notices."*
- **Cohort Divergence** — segmented bar. Green = aligned cohorts. Red = fractured cohorts. *"Die-hards and analytics fans are reading this team completely differently right now."*
- **Rival Heat** — three rival pills with color temperature (cool → warm → red). No numbers — just color and label. Auburn: warm. Tennessee: hot. Mississippi State: cool.
- **Volatility** — a tiny 8-week sparkline of the belief score, with standard deviation band. *"Second most volatile fanbase in the SEC this week."*

**Panel 3 — Home vs. Away Mood Split** (team-specific)
Two bars side-by-side: home crowd sentiment vs. diaspora sentiment. The delta chip. *"Stronger in Tuscaloosa than on the road — this fanbase travels but doesn't travel its emotions."*

**Panel 4 — Top 3 Storylines** (the text intelligence layer)
Three generated storylines, each with a Platform Blend chip. Maximum density of useful FI signal.

1. Storyline headline · Platform Blend chip (`board_heavy` / `reddit_dominant` / `cross-platform`)
   One sentence expanding the storyline, grounded in what people are actually saying.

**Panel 5 — The Confidence Badge** (always visible, bottom)
*"N mentions · high/moderate/low confidence · last updated [date]"*

### Off-Season State

The Pulse band doesn't disappear in the off-season. It shows the *last in-season reading* with a clearly labeled timestamp and a soft overlay chip: *"Off-season mode — last live reading: Week 21 (Dec 2025)."* Below the band, the card shifts to portal/recruiting activity and spring practice signals. The frame stays open. The data changes.

**What it feels like:** You're looking at a fanbase that's resting, not disappeared. The pulse is slower. The room is quieter. But it's still breathing.

### Colors and Animation

The Pulse band uses the Belief ramp (red → neutral → green), but at a lower saturation (60% of full ramp saturation) to avoid alarm at either extreme. High belief isn't electric green — it's a warm sage green. Low belief isn't panic red — it's a muted terracotta. This is emotional weather, not a traffic light.

The pulse animation: `animation: pulse 3s ease-in-out infinite`. Scale oscillates between 1.0 and 1.03 (very subtle). This is just enough to feel alive without being distracting. Respects `prefers-reduced-motion` — animation disabled, static band shown.

---

## E. Progressive Disclosure Done Right

*The exact interaction pattern from first visit to power user.*

### The Four Levels

**LEVEL 1 — Always Visible (the fast lane)**
These elements are never hidden, never require a tap:

- Identity Anchor (team name, record, conference)
- The Story Right Now (the narrative headline)
- Fanbase Pulse (the visual mood band)
- Archetype label
- Season Standing Rung pill
- Next Game Context chip

This zone is the full experience for a casual fan who stays 5-10 seconds. It should feel complete, not like a teaser.

**LEVEL 2 — One Tap / First Scroll (the engaged zone)**
These elements are visible after one scroll or one tap — no drawers, no menus, no friction:

- Season Rating Journey (the line chart — this is the second-most important visual on the page)
- Game Impact Board (compact table, most important games)
- Full Fanbase Pulse card (all five panels)
- Season Snapshot Tiles (Record + SP+ rank + AP rank + Conference Standing)
- CFP/Bowl Probability tile

A fan who spends 30 seconds sees everything in Level 1 and Level 2. They leave with a complete picture of where the team is and how the fanbase feels. This is the ceiling for most mobile social traffic.

**LEVEL 3 — One "Go Deeper" Tap (the engaged fan zone)**
These elements are behind a single expandable section with a clear affordance. The section label is the hook, not just a label:

- Team Savant Card ("How They Actually Win") — 15 percentile bars
- Rivalry Module ("Iron Bowl / The Game / [Rivalry Name]") — the emotional heat module
- Conference Lens (toggle: National ↔ Conference)
- Era Arc ("The [Coach] Era") — the time navigator

Each of these sections has a preview chip above the drawer — one sentence of what's inside. *"Savant Card: Elite defensive havoc (97th). Concern: 3rd-down offense (31st). → Open"* The preview does the job of "making the 5-minute fan feel the depth is worth their time" before they commit to tapping.

**LEVEL 4 — Deep Dive (the power user zone)**
Behind explicit "Deep Dive" navigation anchor — reached via the sticky subnav tab:

- Coaching Staff Scheme Fingerprint
- Recruiting Pipeline + Portal Activity
- Program Trajectory Arc (10-year prestige chart)
- Ceiling / Floor Season Projections (probability distribution)
- Fanbase Health Index (composite score)
- Full Schedule + Results Explorer (filterable table)
- Peer Comparator (3 comparable programs)

A power user can access this zone immediately via the sticky subnav "Deep Dive" tab — they don't have to scroll through everything else. The subnav is the "fast lane for the hardcore fan."

### The Subnav

Sticky bottom-of-screen on mobile, sticky below-hero on desktop. Five tabs:

`📡 Fan Intel | 📅 Season | 📊 Savant | ⚔️ Rivalries | 🔬 Deep Dive`

Icons communicate function without requiring text processing. Active tab is marked with team accent color. Tapping a tab anchors to that zone with a smooth scroll (no page reload — URL updates for shareability).

Keyboard shortcuts (desktop): `F` Fan Intel, `S` Season, `V` saVant, `R` Rivalries, `D` Deep Dive. `?` opens shortcut overlay.

---

## F. The Shareable Moments

*Five elements that will generate organic social sharing.*

### 1. The Rival Heat Thermometer (Pre-Game)

**What it is:** Two opposing thermometers showing the heat level of each fanbase in the week before a rivalry game. Georgia fan temperature on the left, Alabama fan temperature on the right. Color gradient: cool blue at the base → amber → red at the peak. Fill height = intensity level. Current reading in large type above each thermometer: *"82 · HIGH OBSESSION"* vs. *"61 · ELEVATED"*.

**Why someone shares it:** Because it answers the question every fan asks before a rivalry: "Are they scared of us, or are we scared of them?" The answer, visualized, is the screenshot. Works especially well when the thermometers are asymmetric — one side at 78, the other at 41. That gap tells a story.

**The share looks like:** A cropped screenshot of the two thermometers side-by-side. Someone posts it to r/CFB or tweets it with "lmaooo Georgia fans are at 91 and Ohio State fans are at 53 😂"

**The trigger:** Activates 72 hours before any Tier 1 rivalry game. Updates every 6 hours in that window.

### 2. The Reality Gap Callout Card

**What it is:** A standalone card that surfaces when the Reality Gap is ±1.5 SD or more — fan belief vs. the model's rating. Example: *"Alabama fans are 1.8 standard deviations more bullish than what SP+ says. That's either remarkable conviction — or it's cope. The model isn't budging."*

The card has a visual: the two readings (fan belief score vs. model-derived expected belief based on SP+) shown as two markers on a single horizontal scale. The gap is labeled and color-coded.

**Why someone shares it:** Because it's an argument-starter. Alabama fans share it to prove their point. Auburn fans share it to make fun of Alabama fans. The model's honesty is the engagement driver.

**The share looks like:** A cropped screenshot. Either "this is why I love CFB Index" (confirming) or "this is what delusion looks like" (mocking). Both are engagement.

**The trigger:** Reality Gap exceeds ±1.5 SD from FBS median. Post-game after a surprising result is the peak moment.

### 3. The Archetype Migration Moment

**What it is:** When a team shifts archetypes — when the classification algorithm crosses a threshold and the team moves from "The Fractured Kingdom" to "The Reload" or from "The Anxious Dynasty" to "The Entitled Class" — the card shows the migration explicitly. Old archetype → arrow → new archetype. With a one-sentence explanation: *"Texas just shifted from 'The Fractured Kingdom' to 'The Believers' — the biggest single-week archetype movement of the season."*

**Why someone shares it:** Because it names something that fans had been feeling but couldn't articulate. The Texas fanbase *was* a mess for years. Seeing "Fractured Kingdom → Believers" is the data version of "huh, we actually fixed it."

**The share looks like:** The migration arrow card with the team's colors. Big archetype names, small explanatory sentence.

**The trigger:** Archetype classification changes with confidence ≥ 80%. This is a relatively rare event (3-5 per team per season maximum) — which makes it feel significant when it happens.

### 4. The Season Rating Journey Export

**What it is:** The Season Rating Journey chart, formatted as a standalone exportable image. Same visual — the line chart of the team's Power rating through the season — but with the team's colors, the "THE CFB INDEX" wordmark in the corner, and the three biggest game annotations already labeled.

**Why someone shares it:** Because it's the best single visual answer to "how did this season go?" One image tells the whole story. Season recap content is high-engagement in December and January.

**The share looks like:** A clean chart image — mostly dark background, the rating line in team accent color, the three annotation markers. Clean enough to post standalone on Instagram. Analytical enough to post on Twitter.

**The trigger:** Available year-round via a "Share" button on the journey chart. Peak engagement: after bowl games and CFP games.

### 5. The "Biggest Swing" Game Card

**What it is:** A single-game impact card — automatically generated for the biggest positive or negative Power swing of the season. Example: *"The Alabama game that changed everything: @ Indiana, Jan 1. Power dropped 3.24 points in a single game — the 7th largest single-game swing in FBS this season."*

**Why someone shares it:** For Alabama fans, it's the game they want to process. For Indiana fans, it's the signature moment of the season. The national context ("7th largest single-game swing in FBS") makes it feel like it matters beyond just one game.

**The share looks like:** A card with the game result prominent, the swing number in a large display, and the FBS context chip.

**The trigger:** Available as a "share this game" option on the journey chart's game markers. Automatically surfaced in the journey highlight row at the bottom of the chart.

---

## G. Week-to-Week Freshness

*The state machine of a team page across a typical season week.*

A great team page should feel different on Monday morning after a loss, on Thursday before a rivalry game, and on Sunday after the rankings drop. Here is the state machine — every state and what changes:

### MONDAY AFTER A WIN

What changes automatically:
- The Story Right Now headline updates (if trigger threshold met)
- Season Rating Journey adds a new data point, new game marker
- Game Impact Board reranks with the new result
- Fanbase Pulse band updates to the new mood reading (if FI data cleared the publish gate)
- Season Standing Rung updates if the win changes their status (e.g., bowl eligibility achieved)

What stays stable:
- The archetype (archetype changes are slower-moving; one win doesn't shift it)
- The Savant Card (weekly incremental update, not a full regen)
- The Rival module historical data

Editorial layer (human-optional):
- The "Biggest Swing" card can be promoted if the win was particularly significant
- The "A Moment Signal" fires if FI spiked ±2 SD: *"A Moment happened: the Oregon win produced the biggest single-week FI swing since the 2023 Rose Bowl."*

### MONDAY AFTER A LOSS

What changes automatically:
- The Story Right Now headline updates (loss triggers almost always cross the threshold)
- Season Rating Journey shows the downward swing — the "biggest hit" card updates
- Fanbase Pulse updates — and if the loss produced a spike in negative sentiment, the Fracture Detector chip may appear
- CFP/Bowl Probability tile updates (could be a significant drop)
- Reality Gap recalculates — if fans are still optimistic despite the loss, the gap widens

What stays stable:
- The archetype (unless the loss triggers the archetype algorithm's threshold)
- The Savant Card efficiency metrics (one loss doesn't change the season SP+)

Tone shift: The mood ring color visually shifts. If the band was warm amber, it cools. The pulse animation slows if conversation volume drops post-loss, or speeds if a post-loss controversy is generating argument volume.

### THURSDAY BEFORE A RIVALRY GAME (72 HOURS OUT)

**Rivalry Mode activates.**

What changes:
- Rivalry module promoted to Level 1 visibility — rivals content rises to above-the-fold territory on mobile
- The Rival Heat Thermometer appears in the hero zone (between the Pulse and the Next Game chip)
- The "Who needs this more?" module appears in the hero section (model-generated based on CFP implications + streak + season momentum)
- The Next Game chip expands to a full rivalry card: series record, current streak, both fanbases' current heat reading
- The hero's team accent color subtly deepens in saturation — a visual escalation that feels like the stakes going up
- Any available betting market data shows in the rivalry card: line, handle %, model prediction

Editorial layer:
- The "Story Right Now" headline becomes rivalry-specific: *"Georgia's season doesn't end Saturday — but it could begin again."*

### DEAD WEEK / BYE WEEK

What happens:
- The Next Game chip counts down to the next game (further in the future)
- The Recruiting Pipeline module gets promoted — bye weeks are when recruiting news tends to move
- The Portal Activity module shows current off-season or in-season portal movement
- No new FI data (conversation volume drops during bye week); last week's reading stays up with a "bye week — data stable" chip
- The page feels calmer by design — appropriate for the team's rhythms

### OFF-SEASON (April through August)

What happens:
- Mood Card shows last in-season reading with clear timestamp overlay
- Spring Practice module appears if spring game data is available
- Recruiting Pipeline becomes the primary forward-looking module (class rank, commit momentum)
- Portal Activity shows portal comings and goings
- The narrative engine pivots to the TEMPLATE_OFFSEASON_WATCH template: *"Georgia finished the dynasty's next chapter with a bowl loss. The off-season story is Carson Beck's future and whether the offensive line can rebuild."*
- The Season Rating Journey shows the completed season's arc as a historical record, labeled "2025 Season — Final"

**The rule:** The page should never look abandoned. A fan who visits in April should see a page that's alive — just alive differently than in November.

---

## H. The Rivalry Activation

*Rivalry week is the highest-stakes moment for any team page.*

### The Philosophy

Every rivalry has two fanbases, two narratives, and two sets of stakes — and the best rivalry coverage tells both sides simultaneously. ESPN covers the rivalry as a game. CFB Index covers it as a *collision of two emotional realities*.

The rivalry activation isn't a content injection. It's a full modal shift of the page's emotional register.

### The 72-Hour Window: What Changes

**Hero zone transformation:**
The hero section gains a rivalry banner — a subtle horizontal stripe in *both* teams' colors (a thin gradient: team A's accent fading to team B's accent). The banner has the rivalry name in large type: **THE IRON BOWL** or **THE GAME** or **CLEAN OLD-FASHIONED HATE**. Not "Alabama vs. Auburn" — the proper noun.

The Next Game chip expands from a one-liner to a four-element rivalry card:
1. Series record: **Alabama leads 48-37-1** (large display type)
2. Current streak: **BAMA 3-GAME STREAK**
3. Both fanbases' heat readings: the Thermometer, side-by-side
4. "Who needs this more?" — one sentence, model-generated: *"Alabama needs this game more — a loss could cost them a CFP bid they currently control."*

**Rival Heat Thermometer in the hero:**
On rival week only, the thermometer moves to above the fold — between the Fanbase Pulse and the Next Game card. It's not buried in the rivalry module anymore. It's *the* emotional signal of the week.

**FI data priority shift:**
The FI pipeline shifts its feature weights during rivalry week. Rivalry-specific source filters (rivalry subreddit threads, board-specific rivalry threads, rivalry keyword-filtered bluesky posts) get elevated weight. The storylines in "The Room on [Team]" shift to rivalry-specific narratives.

**Page feel:**
The pulse animation on the Fanbase Pulse band speeds slightly. The ambient tension of the page goes up. This is achieved entirely through animation timing and color saturation — no copy changes, no new sections. The page *feels* more urgent without announcing it.

### The Rivalry Module at Peak State

For a Tier 1 rivalry, 72 hours before the game, the rivalry module shows:

**Zone 1 — Identity Header:** Rivalry name, all-time record, current streak, years played.

**Zone 2 — The Four-Axis Matrix:** Win Rate Trend (last 10 games), Performance Gap (average SP+ differential, last 5 meetings), Fan Heat Index (the two thermometers), Respect Gap (how each fanbase *actually talks about* the other — sourced from cross-team sentiment data).

**Zone 3 — The Timeline:** Margin of victory by year, tappable to expand individual game context.

**Zone 4 — Game Week Context (live):** Vegas line + model prediction + fan pick % + "Who needs this more?" + both fanbases' current mood dial, side-by-side.

### Post-Game: The Rivalry Settling

After the game, the rivalry module transitions to "Post-Game" state. The "Who needs this more?" disappears. The series record updates. The streak chip flips (or extends). The Fan Heat readings shift — both fanbases' post-game sentiment replaces the pre-game readings.

A new element appears: **"The Aftermath."** One generated sentence about what the result means for the series narrative: *"Georgia has now won 4 of the last 5. The Clean Old-Fashioned Hate is increasingly one-sided — which means it's increasingly personal for Auburn."*

---

## I. Mobile-First, Thumb-Friendly

*The majority of fans hit this on their phone. Design the phone first.*

### The Scroll Pattern

The canonical mobile scroll (375px wide) moves through four zones:

**Zone 1 — Above the Fold (no scroll required):**
- Team name + record (left-anchored)
- The Story Right Now (one sentence, full-width card)
- Fanbase Pulse band (100px, full-width)
- Archetype label + Season Standing Rung pill (inline)

Everything above fold fits in one "glance" — the fan looks at their phone and absorbs the whole picture without moving their thumb.

**Zone 2 — First Scroll (thumb swipe down):**
- Season Rating Journey (the line chart, full-width, 240px height on mobile, optimized for thumb navigation — tap any point to expand)
- Next Game Context (full-width card)
- Fanbase Pulse detailed panels (snap-scroll tabs within the card: Belief | Reality Gap | Cohort | Rivals)

**Zone 3 — Second Scroll:**
- Season Snapshot Tiles (2x2 grid: Record, SP+ Rank, Conference Standing, CFP/Bowl Probability)
- Game Impact Board (5 rows, tap any row to expand)
- Archetype detail card (expandable)

**Zone 4 — Third Scroll and Beyond:**
- Team Savant Card (full-width percentile bars)
- Rivalry Module (first rivalry card, full-width)
- Era Arc (collapsed by default, tap to expand)

**Deep Dive zone:** Accessible via sticky subnav "Deep Dive" tab without any scrolling.

### What Collapses

On mobile, these elements collapse to their headline/preview state and require a tap to expand:
- Game Impact Board individual game details (see the score, tap to see the swing + opponent context)
- Era Arc (the full coach-era table is behind a tap)
- Coaching Staff Scheme Fingerprint
- Recruiting Pipeline full detail
- Full schedule table (shows top 5 games by default, tap "All games" to expand)

**The rule:** A module collapses if its full form requires horizontal scrolling or a viewport width greater than 375px to be readable. Tables collapse to tap-expandable rows. Charts resize proportionally — no horizontal scrolling ever.

### The Sticky Subnav

Position: fixed to the bottom of the screen on mobile (thumb reach zone). 5 tabs with icons + short labels. 44px minimum height, 44px minimum tap target per tab. Team accent color for the active tab.

```
[📡 Fan Intel] [📅 Season] [📊 Savant] [⚔️ Rivals] [🔬 Dive]
```

The subnav fades in after the first scroll (not visible on above-fold content, where it would compete with the hero). It never overlaps with content that needs to be read — there's a 56px bottom padding on all page content.

### Data Visualization at 375px

**The Season Rating Journey:** Full-width SVG, aspect ratio maintained. Minimum 240px height. Tap targets on game markers are 32x32px minimum (slightly below the 44px ideal, justified because the chart frame provides spatial context). The tooltip appears *above* the marker on mobile (never below, where it would be obscured by the thumb).

**Percentile bars on the Savant Card:** Full-width, stacked vertically. Each bar is 52px tall on mobile (larger than desktop, which is 36px). The label is above the bar (not beside it) to accommodate narrow width. Value indicator is a filled circle, 8px diameter, with team accent color.

**The Rival Heat Thermometer:** Stacks vertically on mobile. Your fanbase on top, their fanbase below. The two thermometers are horizontal (not vertical) at mobile width — easier to display side-by-side at 375px as two adjacent 160px-wide bars.

**Cohort Divergence Stack:** Full-width horizontal stacked bar. Cohort labels appear on tap (not on first render, too crowded at 375px).

---

## J. The 10 Signature Interactions

*The things that turn a visitor into a returning user.*

These are the moments where the page does something unexpected — something that makes a fan think "wait, how did it know that?" or "I've never seen a sports page do that."

**1. The Mood Ring Expansion**
Tap the Fanbase Pulse band → it expands like opening a door. The band stretches to full-height card revealing all five FI panels with a staggered data-entry animation (each row slides in 40ms apart). The expansion feels like listening to a room get louder as you open the door.

*Why it's delightful:* The tap is expected. The animation makes it feel like you've entered a space, not opened a drawer.

**2. The Journey Chart Mood Underlay**
Long-press any game marker on the Season Rating Journey chart → the chart background subtly shifts to the belief ramp color of the fanbase's sentiment *for that specific week*. If the mood was pessimistic in Week 7 even though the team was 5-1, the chart background goes terracotta. The data annotation: *"Fan mood that week: 43/100. Pessimistic despite the win streak — the team wasn't convincing anyone."*

*Why it's delightful:* It reveals a narrative you couldn't see before — the mismatch between the line (performance) and the color (belief). This is original analysis presented through an interaction.

**3. The Rival Thermometer Swipe**
On the Rivalry module, swipe left on the Fan Heat Thermometer → the panel flips to show *the rival team's version of this page's rivalry data*. Alabama's rivalry card, from Auburn's perspective: Auburn's heat reading on the left, Alabama's on the right, the series record framed from Auburn's point of view. Swipe right to return.

*Why it's delightful:* It surfaces a truth that fans know exists but have no way to access: "what does the other side actually look like from over there?"

**4. The Archetype Tap-Through**
Tap the archetype label → a bottom sheet opens with the archetype's full profile: description, signature phrase, historical examples from CFB ("Teams that had this archetype: 2019 Texas, 2016 LSU, 2022 Oregon"). A timeline of migrations for this specific team. An "Other teams right now" chip showing which other teams currently share this archetype.

*Why it's delightful:* "Oh wait, *we're* in the same bucket as 2019 Texas?" is a thought that starts an argument.

**5. The Percentile Peer Reveal**
Tap any percentile bar on the Savant Card → a small popover appears showing the three teams at the top, middle, and bottom of that specific metric: *"Defensive Havoc: 97th pct. Teams at this level: Georgia, Penn State, Michigan. Teams at 50th: Florida, Kansas, Stanford. Teams at 10th: Vanderbilt, Kansas State, Cal."* The tap is a calibration device.

*Why it's delightful:* "Oh, we're as good at defensive havoc as Penn State" is an insight that makes the percentile bar suddenly meaningful. It gives context to a number that was previously floating.

**6. Pull-to-Refresh with Narrative Update**
Pull down on the page (standard mobile pull-to-refresh gesture) → a unique animation: the mood ring expands, briefly shows "checking..." text, then resolves. If there's new data, the Story Right Now headline briefly highlights: a yellow-green flash on the card with a chip: *"Updated just now — mood shifted +0.3 SD after the coaching news."*

*Why it's delightful:* Creates a refresh ritual. The fan doesn't pull to refresh because they need new data — they pull because the animation is satisfying and they're hoping to see that flash.

**7. The Story Expansion**
Tap the "Story Right Now" headline → it expands to a three-sentence version with sourcing chips. *"The dynasty is running out of ways to lose. [fan conversation: 847 mentions, 71% bullish] Georgia controls their destiny for the third consecutive season [model: Power #1 in SEC]. The January question isn't whether they'll be there — it's whether they can stop making it close. [FI: belief at 67/100, below their standard at this record]."*

*Why it's delightful:* The casual fan gets the headline. The curious fan gets the footnotes built into the prose. The chip annotation style makes the sourcing visible without cluttering the headline.

**8. The Cohort Quote Tap**
Tap any segment of the Cohort Divergence Stack → a panel appears with two representative (anonymized) quotes from that cohort. The die-hard board quote and the analytics community quote, side-by-side: *"Die-hards: 'This defense is elite, stop panicking.' Analytics fans: 'The havoc rate is great but they're bending a lot — wait until they face a professional offense.'"*

*Why it's delightful:* It makes the quantitative divergence *audible*. You can hear why the cohorts disagree, not just see that they do.

**9. The Season Standing Context Tap**
Tap the Season Standing Rung pill → a small popover shows all 9 rungs, your team's position highlighted, and 3 other teams currently at your rung: *"Bowl Eligible (Rung 3): James Madison, Tulane, Liberty."* Below: what would move this team to the next rung: *"To reach Rung 4: Enter AP Top 25 (currently 26th in SP+)."*

*Why it's delightful:* It answers "what would it take" — the question every fan is already asking — with specific, actionable data.

**10. Long-Press to Share Any Stat**
Long-press on any stat value, percentile bar, or chip → a share sheet appears with a pre-formatted card: the stat, its context, the team name, and the CFB Index wordmark. *"Georgia's defensive havoc rate: 97th percentile nationally. Better than Penn State's current defense. via THE CFB INDEX."* The card is formatted for Twitter/X/Instagram Story with team colors as background.

*Why it's delightful:* Every stat becomes shareable in 2 seconds. The attribution is built into the image, not added later. This is the organic distribution mechanism — every shared stat is a CFB Index ad.

---

## K. Fan Intelligence Integration — The Full Vision

*How every piece of FI data connects to the visual experience.*

### The FI Signal Map

The Fan Intelligence system produces a set of signals, each of which connects to a specific visual element. Here is the complete map:

| FI Signal | Visual Element | Interaction Layer | Refresh Cadence |
|---|---|---|---|
| **Mood Index** (weekly belief score) | Pulse band color + Belief Dial position | Level 1 (always visible) | Monday in-season |
| **Fanbase Archetype** | Archetype label in hero + Archetype card | Level 1 (always visible) | Weekly evaluation, slower change |
| **Archetype Modifiers** | Modifier chips below archetype name | Level 2 (tap) | Weekly |
| **Archetype Migration** | Migration spark + "A Moment" card when it shifts | Level 2 (first scroll) | Event-driven |
| **Reality Gap** | Five-Axis Strip meter + Reality Gap callout card | Level 2 (FI panel) | Monday in-season |
| **Respect Gap** | Five-Axis Strip meter + Respect Gap chip in hero zone | Level 2 (FI panel) | Monday in-season |
| **Cohort Divergence** | Cohort Divergence Stack + Fracture Alert chip | Level 2 (FI panel) | Monday in-season |
| **Rival Heat** | Rival Heat thermometer + rival pills in Five-Axis Strip | Level 2 (FI panel) + Level 3 (Rivalry module) | Weekly; hourly in rivalry 72hr window |
| **Volatility** | Pulse animation speed + Volatility sparkline | Level 1 (felt) + Level 2 (FI panel) | Monday in-season |
| **Storylines** | "The Room on [Team]" Panel 4 (top 3 storylines) | Level 2 (FI panel) | Monday in-season |
| **Volume trend** | Confidence badge N count + pulse animation speed | Level 2 (FI panel) | Monday in-season |
| **FI Spike (±2SD)** | "A Moment" banner on FI card | Level 2 (auto-surfaced) | Event-driven |
| **Fracture Detection** | Fracture Alert chip + Cohort stack | Level 2 (FI panel) | Event-driven (±1.5SD) |
| **Home vs Away Mood** | Home/Away Split panel | Level 2 (FI panel, Panel 3) | Weekly |
| **Geographic reach** | Fanbase Health Index component | Level 4 (Deep Dive) | Monthly |
| **Ticket demand index** | Fanbase Health Index component | Level 4 (Deep Dive) | Weekly |
| **Platform Blend** | Storyline source chips (board_heavy / reddit_dominant) | Level 2 (FI panel) | Per-storyline |
| **Cohort quote samples** | Cohort Divergence tap interaction | Level 2 (interaction) | Weekly |

### The Hierarchy of FI Signals

Not all FI signals are equal. The hierarchy of what matters, in order:

**Tier 1 — Narrative-defining signals:** These appear in the hero zone and the "Story Right Now" headline. Mood Index direction + Fanbase Archetype + Archetype Migration. A fan should never miss these.

**Tier 2 — Engagement-deepening signals:** These live in the Fanbase Pulse card, visible after one tap. Reality Gap, Respect Gap, Cohort Divergence, Top Storylines. A fan who spends 30 seconds should encounter all four.

**Tier 3 — Contextual intelligence signals:** These surface in the Rivalry module, the Savant Card annotations, and the Narrative Engine's text. Rival Heat, Platform Blend, Volatility pattern. These are the signals that make the 5-minute fan think "I've never seen this analysis anywhere else."

**Tier 4 — Power-user signals:** Fanbase Health Index, Geographic Reach, historical archetype comparison. Deep Dive zone only. The signals that make the data nerd bookmark the site.

### The FI System's "Never Be Empty" Principle

Every FI-driven visual element has an off-season state that is better than empty:

- **Mood ring:** Shows last-season reading at reduced saturation, labeled "Post-season reading: [date]"
- **Archetype label:** Shows last-season archetype with "Off-season" badge
- **Storylines:** Shows the three most significant post-season storylines (portal, recruiting, coaching) with explicit "off-season signal" sourcing
- **Rival Heat:** Shows last rivalry-week heat reading with seasonal timestamp
- **Cohort Divergence:** Shows post-season divergence snapshot

The principle: the FI system captured real signal all year. That signal doesn't disappear because the season ended. Show the most recent real data, clearly labeled, rather than a frame that communicates "this is broken."

---

## L. Competitive Moat

*The three things on this team page that no competitor can replicate.*

These aren't features. They're the intersection of the FI conversation pipeline, the SP+ modeling, and the design system — all three required simultaneously. Remove any one leg and the stool falls.

### Moat 1: The Fanbase as an Analytical Object

**What it is:** The ability to measure a fanbase's identity, internal fractures, trajectory, and emotional relationship with reality over time — not as a poll, but as a derived analytical object from conversation data.

**Why no competitor can replicate it:** ESPN doesn't have conversation data. 247Sports has board data but no analytical framework. The Athletic has the writing but not the pipeline. To replicate what CFB Index does would require: building a multi-source conversation pipeline across Reddit, Bluesky, message boards, and podcast RSS; building the cohort architecture that separates die-hards from analytics fans from casual observers; and building the archetype classification system. That's 18-24 months of engineering work before you've designed anything.

**How it shows up on the page:** The Fanbase Pulse band. The Archetype label. The Cohort Divergence Stack. The "A Moment" signal. The Archetype Migration visualization. The Reality Gap callout. These elements collectively make CFB Index the only place where a fan can understand *what it is like* to be a fan of this team right now, with data behind it.

**The specific thing that will be screenshot-shared:** The Rival Heat Thermometer pre-rivalry. The moment a fan sees "Auburn fans: 82 · HIGH OBSESSION / Alabama fans: 47 · ELEVATED" — with the data actually behind it — is the moment CFB Index becomes the place people check before every rivalry game.

### Moat 2: The Narrative Engine + Time Axis

**What it is:** The weekly-updating "Story Right Now" headline, generated by an algorithm that combines SP+ model movement + FI belief direction + archetype + historical program context. And the Era Arc — the ability to navigate from "this week" to "this coach's era" to "all time" using the same data model, with the fan mood data underlay tracking through time.

**Why no competitor can replicate it:** Generating a weekly editorial sentence that is *specific*, *defensible*, and *narratively true* requires: a calibrated predictive model (the SP+ layer), real measured fan sentiment (the FI pipeline), an archetype classification system (the cohort architecture), and a historical baseline to contextualize both (the program history database). The combination of these four data sources into a coherent sentence is unique.

The Era Arc with mood underlay goes further — no competitor has historical fan sentiment data at weekly resolution going back multiple seasons. CFB Index is building this as a byproduct of running the FI pipeline. It becomes more valuable every week.

**How it shows up on the page:** The "Story Right Now" headline in the hero. The mood underlay on the Season Rating Journey (fan belief color under the performance line). The Era Arc view showing "what were fans feeling in each year of this coach's tenure." The Archetype Migration timeline.

**The specific thing that will be screenshot-shared:** The Era Arc with mood underlay — specifically the revelation that a team's fans were pessimistic during a win streak, or euphoric despite a losing record. That visual story is the kind of unexpected truth that makes people say "wait, is that actually data?" and then share it.

### Moat 3: The Reality Gap as a Live Editorial Instrument

**What it is:** The measurement of the gap between what a fanbase believes about its team (FI-derived) and what the model says the team actually is (SP+-derived), updated weekly, with enough history to show whether the gap is closing or widening.

**Why no competitor can replicate it:** The Reality Gap requires both a real belief measurement (not a poll — a derived signal from conversation data) and a calibrated performance model. Having one without the other produces either a poll (superficial) or a model with no emotional context (analytical but not human). The combination — and specifically the gap between them — is what makes it useful. That gap is the story. A team with fans who are 1.8 SD more bullish than the model is a team where either the fans see something the model can't, or the fans are in denial. That is an argument. Arguments travel.

**How it shows up on the page:** The Reality Gap meter in the Five-Axis Strip. The Reality Gap callout card (shareable). The "Story Right Now" narrative template that flags when the gap is notably wide. The Respect Gap's companion analysis (fan belief vs. national belief vs. model) creating a three-way comparison.

**The specific thing that will be screenshot-shared:** The Reality Gap callout card when the gap is extreme. *"Ohio State fans are 2.1 standard deviations more bullish than the SP+ model. That's the largest Reality Gap in the Big Ten. They either know something — or they've convinced themselves."* That sentence, with the CFB Index wordmark, will be on Twitter before every Ohio State game.

---

## Appendix: Opinionated Calls

These are the convictions worth defending, where conventional wisdom would push in a different direction.

**The story comes before the stats.** Every design instinct from traditional sports media says lead with the record and the rankings. We're doing the opposite: lead with the sentence, then show the numbers. This will feel wrong to some people and right to the audience we're building.

**Honest data is more engaging than flattering data.** The Alabama fanbase archetype is "The Anxious Dynasty." That's not flattering. It's true, and Alabama fans will recognize it as true, which is why they'll share it. A product that tells a fanbase they're great is a press release. A product that tells a fanbase the truth about itself is journalism.

**Rivalry week is the peak moment, not game day.** Game day belongs to the broadcast. The 72 hours before the game — the buildup, the heat, the history, the argument — that's where CFB Index lives. Design the rivalry activation for Thursday night, not Saturday noon.

**Off-season content is a competitive advantage, not a gap to fill.** ESPN has the off-season covered with recruiting news and transfer portal content. CFB Index can't win on recruiting granularity. But CFB Index can win on *interpretation* — what does the portal activity mean for this team's SP+ trajectory? What does the spring practice signal say about the archetype? The off-season is when the FI pipeline's historical data becomes most valuable, because there's nothing happening to distract from the narrative.

**Five signature modules, world-class, beat fifteen adequate ones.** The Fanbase Pulse, the Season Rating Journey, the Savant Card, the Rivalry Module, and the Narrative Engine. These five, executed exceptionally, are the product. Everything else is context.

---

*Session log: 2026-04-23 — Produced by Claude after deep read of TEAM_PAGE_WORLD_CLASS_BRIEF.md, PLAYER_PAGE_WORLD_CLASS_BRIEF.md, CFB_INDEX_AUDIT.md, FAN_INTEL_SOURCE_STRATEGY.md, and direct inspection of Alabama and Georgia team page HTML. Research inputs: ESPN team page design failures, The Athletic narrative quality analysis, NBA Twitter fanbase identity mechanics, Baseball Savant / 538 viral sports data analysis, Spotify Wrapped / Apple Fitness progressive disclosure patterns, full CFB fanbase archetype taxonomy development. Designed for the north star: a 20-year-old who just started watching CFB and a 40-year-old who's watched since Bowden should both feel the page was built for them.*
