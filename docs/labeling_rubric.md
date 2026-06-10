# CFB Fan-Sentiment Labeling Rubric

**The one question:** *Is this comment expressing something **GOOD** or **BAD** about the team shown?*
You're labeling the **team's vibe / the writer's expressed feeling toward the team** — **not** the writer's general mood, and **not** how bad/good the underlying event is.

**Decision flow:**
1. Is it about this team's **football** at all? **No → Off-topic** (flag it; don't pick a sentiment).
2. Is there a **feeling or opinion** expressed (a word/phrase with emotion or judgment)? **No → Neutral.**
3. If yes, is that feeling **favorable → Positive** or **unfavorable → Negative**?
4. **Sarcasm?** Judge the *intended* meaning, then also tap **Sarcastic**.
5. **Mixed?** Go with the overall lean; truly 50/50 → Neutral.

> Go with a 2–3 second gut read and be **consistent**. The score is an average — close calls wash out.

---

## 🟢 POSITIVE — favorable feeling about the team

**Optimism / confidence**
- "This is the year we finally break through."
- "Our schedule sets up perfectly for a playoff run."
- "Defense is going to be a problem for everybody this fall."
- "Honestly the most excited I've been about a recruiting class in years."

**Praise (player / coach / unit)**
- "Coach completely changed the culture here."
- "Most accurate QB we've had in a decade."
- "That O-line is going to be elite."
- "Our DC is a genius, those blitz packages are unfair."

**Hype / good news embraced**
- "WE GOT THE 5-STAR!! LFG 🔥"
- "Portal haul is insane this year, GMs of the offseason."
- "Spring game had me hyped — the freshmen look the part."
- "Huge get landing that grad-transfer tackle."

**Pride / celebration / ownership**
- "Still not over that comeback. Best game I've ever seen live."
- "Four straight over them now. We own them."
- "Banner season no matter what happens the rest of the way."

**Defending the team / pushback at critics**
- "Y'all sleep on us every year and we keep proving you wrong."
- "Overrated? We literally made the playoff."

**Positive CFB slang (these *look* neutral/negative but mean GOOD)**
- "QB1 is **HIM**." (elite)
- "New RB is **different**, man." (special)
- "Our secondary is **nasty / filthy / disgusting** this year." (impressive)
- "He's been **cooking** all spring." (dominating)
- "That freshman edge is a **problem**." (a good problem — he's great)

---

## 🔴 NEGATIVE — unfavorable feeling about the team

**Pessimism / doom**
- "Same old us. We'll find a way to blow it."
- "Season's already over and it's August."
- "We're getting run out of the building by Georgia."

**Criticism (player / coach / scheme / AD)**
- "The OC has no creativity — same three plays every week."
- "Can't tackle, can't catch, can't coach. Embarrassing."
- "AD needs to open the checkbook or we'll never compete."

**Frustration / anger / disappointment**
- "I'm so done with this program."
- "How do you lose to THEM at home?? Unacceptable."
- "Watching this offense is physically painful."

**Coach on the hot seat**
- "Fire him tonight, buyout be damned."
- "He's lost the locker room."

**Self-deprecation / mockery of own team**
- "Peak us. Snatching defeat from the jaws of victory since forever."
- "We're frauds. Always have been."

**Negative reactions to news/results**
- "Losing our best WR to the portal is brutal. There goes the season."
- "That loss set the program back five years."

**Negative CFB slang**
- "We're **cooked / washed / done**." (declining / finished)
- "Offense is **mid** at best." (mediocre)
- "Got **exposed as frauds** again."
- "We **fumbled the bag** on that hire." (botched it)
- "Total **rebuild** year, write it off." (no hope)

---

## ⚪ NEUTRAL — no clear good/bad lean (and the default when unsure)

**Factual news / reports with NO opinion — even if the news is bad**
- "QB ruled out for Saturday with a high ankle sprain."
- "Kickoff moved to 3:30 on ABC."
- "Spring game is April 13."
- "He announced he's transferring." (stated flatly)
- *(If the same news is editorialized — "Devastating, our season's over" — that's Negative.)*

**Logistics / questions**
- "Anyone have a spare ticket for the opener?"
- "What channel is the game on?"
- "Where's everyone tailgating this week?"

**Balanced / mixed that cancels out**
- "Happy we won, but the run defense is still a real concern."
- "Good and bad today — clean QB play, sloppy special teams."

**Neutral analysis / speculation (no clear lean)**
- "They run a lot of two-high looks under this DC."
- "Depth chart probably shakes out with the JUCO starting."
- "He's a 4-star from Texas who played both ways in HS."

---

## ⚠️ Tricky cases & rules

**Sarcasm — judge the true meaning, then tap Sarcastic**
- "Oh fantastic, another 3-and-out 🙄" → **Negative** + Sarcastic
- "Love watching us punt, truly elite football." → **Negative** + Sarcastic
- "Sure, THIS year will be different lol." → **Negative** + Sarcastic

**Factual good/bad news (no opinion) → Neutral** *(label the feeling, not the event)*
- "QB out 3 weeks with injury." → **Neutral**
- "Landed a grad-transfer OL." (flat) → **Neutral** &nbsp;|&nbsp; "HUGE get!!" → **Positive**

**Mixed → overall lean; truly 50/50 → Neutral**
- "Defense carried us, offense looked lost — but a W is a W." → lean **Positive** (ends positive)

**Sentiment about an OPPONENT → label toward the TEAM SHOWN**
- *Team shown = Michigan:* "Ohio State's secondary is trash, we'll torch them." → **Positive** (about Michigan)
- *Team shown = Ohio State:* same comment → **Negative** (about Ohio State)

**Loaded questions → by implication**
- "Why is our OC still employed?" → **Negative**
- "What time is kickoff?" → **Neutral**

**Off-topic (not about the team's football) → Off-topic flag, not a sentiment**
- "Anyone know a good plumber in town?" → **Off-topic**
- "RIP to the campus diner, end of an era." → **Off-topic**
- "Selling 2 tickets, DM me." → **Off-topic** (it's a transaction, not football opinion)

---

## 📖 CFB slang cheat-sheet (the stuff the old tool got wrong)

| Phrase | Means | Lean |
|---|---|---|
| "he's **him**" / "**different** / built different" | elite, special | 🟢 |
| "**nasty / filthy / disgusting / dirty / sick / insane**" (a play, a player) | impressive | 🟢 |
| "**cooking**" / "cooked them" | dominating | 🟢 |
| "he's a **problem** / **dawg**" | great player | 🟢 |
| "**bag secured**" | got paid / recruited well | 🟢 |
| "**natty**" | national championship | context (usually 🟢) |
| "**cooked / washed / done / finished**" (a team/player) | declining | 🔴 |
| "**mid**" | mediocre | 🔴 |
| "**fraud / frauds**" | overrated, fake | 🔴 |
| "**copium**" | delusional hope | 🔴 |
| "**fumbled the bag**" | botched it | 🔴 |
| "**choked / choke job**" | blew it | 🔴 |
| "**fire [name]**" | wants coach gone | 🔴 |
| "**rebuild / cooked season**" | no hope this year | 🔴 |

> Note: "nasty," "filthy," "sick," "insane," "dirty" are almost always **compliments** in football talk. The old VADER tool read them as negative — that's a big part of why we're upgrading it.
