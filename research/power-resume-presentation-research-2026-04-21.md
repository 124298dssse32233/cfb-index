# Power / Resume Presentation Research

Date: April 21, 2026

## Question

How should `Power` and `Resume` be displayed so normal users understand them immediately?

The specific product question was whether both metrics should move to a bounded scale such as `-100` to `100`, where:

- `-100` = theoretical weakest team possible
- `0` = average college football team
- `100` = theoretical greatest team imaginable

## Short answer

We should **not** force both metrics onto the same `-100` to `100` scale.

The best public predictive systems do not do that. They keep the predictive rating on a **linear game-like scale** and make it readable by clearly telling the user what the number means. The resume side is different: the best public "deserving" or "achievement" style products usually present that information as a **rank, percentile, probability, or bounded score**, not as a fake point spread.

## What the best public systems do

### 1. KenPom keeps the predictive number linear and scoreboard-like

Ken Pomeroy's methodology update says the main benefit of moving to `AdjEM` was that the number became "more easily understood by humans." He explicitly argues that a linear margin-like scale is better than a non-linear winning-percentage style scale, because the difference between `+31` and `+28` means the same thing as the difference between `+4` and `+1`. He also defines `AdjEM` as the number of points a team would be expected to outscore the average Division I team over 100 possessions.

Why this matters for us:

- predictive ratings work best when the unit is tied to game outcomes
- users can reason from the number to a matchup
- linear differences are much easier to understand than arbitrary bounded indexes

Source:

- [KenPom ratings methodology update](https://kenpom.com/blog/ratings-methodology-update/)
- [KenPom ratings glossary](https://kenpom.com/blog/ratings-glossary/)

### 2. ESPN FPI does the same thing for football

ESPN's current FPI page says FPI is meant to be the best predictor of future team performance and that it represents how many points above or below average a team is. ESPN's older explanatory page is even more explicit: FPI is on a scoring-margin scale, and if Team A has a `24` and Team B has a `17`, Team A would be about a 7-point favorite on a neutral field.

Why this matters for us:

- this is the cleanest football-native way to express predictive strength
- the number is meaningful by itself
- it converts directly into spreads, matchups, and simulations

Source:

- [ESPN FPI page](https://www.espn.com/college-football/fpi)
- [Understanding ESPN Team Rankings](https://www.espn.com/college-football/story/_/id/9807386/understanding-espn-team-rankings)

### 3. ESPN's "deserving" side uses a bounded public-facing score

That same ESPN explanation separates predictive strength from deservingness. The older writeup explains Championship Drive Ratings on a `0` to `100` scale and describes the underlying logic in probability terms: what is the chance that an average team would accomplish that record against that schedule, and what is the chance it would control games that much against that schedule?

Why this matters for us:

- the public-facing "resume" number can be bounded and digestible
- the explanation can be probabilistic even if the display is simplified
- predictive strength and season accomplishment do not need identical units

Source:

- [Understanding ESPN Team Rankings](https://www.espn.com/college-football/story/_/id/9807386/understanding-espn-team-rankings)

### 4. Massey explicitly separates "Rating" from "Power"

Massey says the overall rating is a merit-based assessment of performance to date, while `Power` is estimated team strength going forward and is better for predictions.

Why this matters for us:

- trying to make predictive and descriptive metrics behave like the same thing is a conceptual mistake
- users can handle two different scales if each one is honest about what it means

Source:

- [Massey Ratings description](https://masseyratings.com/theory/massey.htm)

### 5. TeamRankings uses plain language for predictive display

TeamRankings' public team pages label their predictive rating as `Points Above Avg.` That is very simple and very understandable.

Why this matters for us:

- the label is doing a lot of the UX work
- a good label can make a raw predictive number feel obvious

Source:

- [TeamRankings college football team page example](https://www.teamrankings.com/college-football/team/maryland-terrapins)

## What our current system is doing

### Power

Our internal model spec already says `Power` is "expected neutral-field scoring margin versus an average NCAA team on the shared site scale."

However, the current implementation has a semantic mismatch:

- the docs describe the public number as "points above average NCAA team"
- the code seeds level priors at `FBS = 0.0`, `FCS = -11.5`, `DII = -22.5`, `DIII = -32.5`
- the current published numbers therefore behave more like an anchored all-level strength scale than a truly re-centered average-is-zero NCAA scale

Latest local snapshot inspected:

- latest model run: `season 2025`, `week 21`, `model_run_id 38`
- highest power: `Indiana +12.51`
- lowest power: `Apprentice School -28.16`

That means the site is currently publishing a useful predictive number, but the explanation is not quite aligned with the actual centering.

### Resume

The current `resume_score` is not a public-friendly scale at all. It is built as:

- `0.50 * record-strength z-score`
- `0.30 * performance-over-expectation z-score`
- `0.20 * result-quality z-score`

This is good model math, but weak public UX. The top 2025 value in the latest snapshot is over `8`, which normal users cannot interpret intuitively.

Important hidden opportunity:

the pipeline already stores benchmark probabilities in `strength_of_record_benchmarks`, including the probability that an `Elite`, `Top25`, or `Top50` strength team would match or exceed that record against that schedule.

That is extremely useful for public resume explanations.

## Recommendation

### Recommendation 1: keep predictive power linear

Do **not** convert the predictive model's primary public number to `-100` to `100`.

Why:

- it destroys the natural relationship between the rating and point spread
- the ceiling and floor become arbitrary and unstable
- users lose the ability to translate the number into a game expectation
- the best public predictive systems already use linear margin-like units

Instead:

- keep the primary predictive metric as a **margin-like rating**
- make the label much clearer
- optionally add a companion percentile or tier for instant reading

### Recommendation 2: fix the public meaning of power

We should choose one of these and then enforce it everywhere:

Option A. `Power = neutral-field points vs average NCAA team`

- re-center each snapshot so the average eligible team is `0`
- keep team-to-team differences unchanged
- this matches the user's intuition that average all-level team should be `0`

Option B. `Power = neutral-field points vs average FBS team`

- keep the current general anchoring
- relabel it honestly

My recommendation is **Option A**, because it is cleaner for an all-level product and fits the cross-division thesis better.

### Recommendation 3: make resume a bounded public score

Resume should not stay as a raw z-score on the front end.

The best public-facing shape is:

- `Resume Score: 0-100`
- plus rank
- plus one probability sentence for explanation

The simplest honest version:

- `Resume Score = percentile of the underlying resume model among all eligible teams in the current snapshot`

The richer version:

- keep the current composite model underneath
- expose a public explanation sentence using the stored benchmark probabilities

Example:

- `Resume 94`
- `Only 6% of Top-25-caliber teams would be expected to match this record against this schedule.`

This is much easier to understand than `Resume 2.84`.

### Recommendation 4: do not force power and resume onto identical units

Users do **not** need both numbers to be the same type of thing.

The cleanest product language is:

- `Power` answers: how strong are you right now?
- `Resume` answers: how much have you earned so far?

Those are different questions. Different display scales are fine.

## Best-in-class public format

### Homepage board

Recommended board columns:

- `Rank`
- `Delta`
- `Team`
- `Record`
- `Power`
- `Resume`

Recommended board labels:

- `Power` header helper: `neutral pts vs avg`
- `Resume` header helper: `season percentile`

Example row:

- `Power: +18.4`
- `Resume: 96`

### Team page stat cards

Recommended primary stat cards:

- `Power +7.5`
- small copy: `Neutral-field strength vs average NCAA team`

- `Resume 94`
- small copy: `94th-percentile season body of work`

- `Projection`
- small copy: `Would be favored by X vs average team`

- `Resume rarity`
- small copy: `Only 6% of Top-25 teams would match this record`

### Scatter / compare views

The current percentile-space scatter approach is directionally correct.

The improvement is not changing that chart back to raw units. It is:

- clearer labels
- more direct tooltips
- better team annotation
- more obvious hover / click behavior

Suggested axes:

- `Power percentile`
- `Resume percentile`

Tooltip:

- `Notre Dame`
- `Power: +7.5 (91st percentile)`
- `Resume: 94`
- `Top-25 benchmark match rate: 6.2%`

## Recommended product language

### Power

Good:

- `Power`
- `Team Strength`
- `Neutral Power`

Bad:

- `Predictive Rating` as the only label
- `Index` if the number is really a margin

Recommended public copy:

- `Power measures how many points better or worse a team is than an average NCAA team on a neutral field.`

### Resume

Good:

- `Resume`
- `Resume Score`
- `Earned Score`

Recommended public copy:

- `Resume measures how impressive a team's season has been so far once opponent quality and game difficulty are accounted for.`

## Suggested implementation plan

### Phase 1: no model rewrite, just presentation cleanup

1. Keep raw predictive model output.
2. Add a public `power_display` field that is re-centered if we choose the all-team-average-zero spec.
3. Add a public `resume_display` field on a `0-100` percentile scale.
4. Replace raw `resume_score` displays across homepage, team pages, compare, and conference views.
5. Add helper copy under both metrics everywhere they appear.

### Phase 2: richer resume explanation

1. Surface `Top25` benchmark probability on team pages.
2. Add "rarity of record" language to best-resume cards.
3. Add why-ahead-of-you compare text between neighboring teams.

### Phase 3: visual polish

1. Add color-banded tiers for power.
2. Add percentile badges for resume.
3. Add hover explainer panels in the board and scatter views.

## Final recommendation

If the goal is "immediately understandable," the strongest product choice is:

- **Power**: keep it linear and game-like
- **Resume**: make it bounded and percentile-like
- **Do not** force both onto `-100` to `100`

The best public models already point in this direction:

- predictive strength should read like football
- resume should read like accomplishment

That is the cleanest, most premium, and most honest version of the product.
