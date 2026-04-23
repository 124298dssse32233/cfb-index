# Unique Concepts Hardening

Research date: 2026-04-22

Companion files:

- `research/fan-intelligence-flagship-roadmap-2026-04-21.md`
- `research/fanbase-mood-system-design-2026-04-21.md`
- `research/affection-hostility-leaderboards-2026-04-21.md`
- `research/frontend-design-benchmark-2026-04-21.md`
- `research/cfb-language-understanding-2026-04-21.md`

## Purpose

This memo uses outside research to harden the most promising proprietary concepts rather than just inventing more feature ideas.

The goal is:

- keep the strongest concepts
- sharpen them with outside evidence
- kill weak or redundant directions
- identify a few new signature concepts worth adding

## Outside research that matters most

## 1. Surprise is a stronger organizing principle than generic sentiment

In `"This is why we play": Characterizing Online Fan Communities of the NBA Teams`, Zhang et al. found that **surprise** plays an important role in fan activity:

- fans of top teams are more active when their teams lose
- fans of bottom teams are more active in unexpected wins

Source:

- https://arxiv.org/abs/1809.01170

Implication for us:

- `surprise` should become a first-class concept
- not just a modeling control variable

This strengthens:

- `Biggest Vibe Shifts`
- `Belief Shift`
- postgame elasticity ideas

It also suggests a new signature module:

- `Shock Index`

Definition:

- how surprising the football event was times how much the conversation moved

This is better than a generic `sentiment moved a lot` story because it adds football context and makes the change legible.

## 2. Bandwagon behavior and loyalty are measurable in online fan communities

In `Jump on the Bandwagon? -- Characterizing Bandwagon Phenomenon in Online NBA Fan Communities`, Zhang et al. found:

- better teams attract more bandwagon fans
- bandwagon users write shorter comments
- bandwagon users show less attachment in their language

Source:

- https://arxiv.org/abs/2104.08632

Implication for us:

There is a real concept here beyond mood:

- `Loyalty Temperature`
- `Bandwagon Risk`
- `Attachment Strength`

This should not be a v1 homepage centerpiece, but it is a strong later-phase concept because it turns a hand-wavy fan argument into something observable.

Potential module:

- `Bandwagon Meter`

Best use:

- season-level or offseason identity cards
- not week-to-week overreaction boards

## 3. Fan language should be modeled as intergroup language, not generic discussion

In `Do they mean 'us'? Interpreting Referring Expression variation under Intergroup Bias`, Govindarajan et al. build a large NFL Reddit corpus grounded in:

- team-specific fan subreddits
- opposing perspectives on the same game
- live win probabilities

The paper explicitly models:

- in-group language
- out-group language
- language grounded in the state of the game

Sources:

- https://aclanthology.org/2024.findings-emnlp.571/
- https://aclanthology.org/2024.findings-emnlp.571.pdf

Implication for us:

This strongly validates several decisions we already leaned toward:

- separate `fan`, `rival`, and `national` buckets
- avoid one global sentiment score
- tie conversation interpretation to football context

But it also suggests a sharper concept:

- `In-Group / Out-Group Split`

Potential module:

- how fans describe themselves versus how rivals describe them

This is related to `Respect Gap`, but not identical.

`Respect Gap` is:

- fan optimism versus national mood

`In-Group / Out-Group Split` is:

- fan self-language versus rival language during the same football reality

That is a more psychologically rich rivalry module.

## 4. Rival contact and spillover make hostility itself a measurable product concept

In `Intergroup Contact in the Wild`, Zhang et al. find that NBA forum members with intergroup contact use more negative and abusive language in their affiliated group than those without such contact.

Source:

- https://arxiv.org/abs/1908.10870

And in `Catching Stray Balls`, Hill shows that football-related emotional shifts on Reddit can spill into other communities and that negative sentiment correlates with problematic language.

Source:

- https://aclanthology.org/2025.woah-1.17/

Implication for us:

This hardens the case for:

- `Rival Heat`
- `Civil War Watch`
- confidence-aware toxicity handling

It also suggests a new internal concept:

- `Spillover Risk`

Definition:

- how much a team's game or controversy is driving emotionally loaded discourse beyond its home fan context

This is probably too abstract for v1 as a homepage card.

But it is useful internally because it helps decide:

- when to boost coverage
- when to route outputs through human review
- when a storyline is becoming nationally contagious

## 5. Fans of weak teams talk about the future to sustain hope

The same NBA fan-community paper found that fans of bottom teams tend to discuss:

- young talents
- the future
- long-term hope

Source:

- https://arxiv.org/abs/1809.01170

Implication for us:

This strongly validates:

- `Hope Inventory`
- `Storyline Gravity`

and suggests those are not fluffy ideas.

They are behavioral coping patterns that help explain why fanbases remain emotionally invested through adversity.

This makes `Hope Inventory` more than just a nice card.

It becomes:

- a resilience / coping profile for a fanbase

## 6. Team colors are not cosmetic; they are identity infrastructure

In `Factors Influencing Fan Acceptance or Rejection of a Sport Team's Revolutionary Rebrand`, Simmons et al. found that:

- team color scheme was at least three times more important than any other brand association in the context they studied

Source:

- https://journals.sagepub.com/doi/10.32731/SMQ.322.062023.01

Implication for us:

The front-end direction should not treat team colors as:

- optional decoration

They are:

- identity anchors

This hardens the UI decision to let team and conference identity show up visually much more strongly.

## 7. Fan-facing visualizations need to embed data into fan context, not analyst context

In `The Quest for Omnioculars`, Lin et al. argue that while sports data is increasingly complex, relatively few tools target fans rather than analysts, and they present a user-centered framework for embedded visualizations that improve understanding and engagement.

Source:

- https://arxiv.org/abs/2209.00202

Implication for us:

This supports the core design principle:

- charts should answer a fan question immediately

not:

- merely display a metric

This strengthens:

- `Rating River`
- `Team Mood Card`
- embedded comparison callouts
- explanatory annotations

## 8. Human-in-the-loop sports text generation is a real model, not a hack

In `A Community-Driven Data-to-Text Platform for Football Match Summaries`, Fernandes et al. describe Prosebot, a system that generates draft match summaries and then relies on community refinement.

Source:

- https://aclanthology.org/2024.lrec-main.15.pdf

Implication for us:

We do not need to choose between:

- pure automation
- pure manual editorial

There is a strong middle path:

- structured story draft generation
- then human editing for the highest-value outputs

This is especially relevant for:

- `What Changed This Week`
- storyline summaries
- lower-volume teams
- archive / recap surfaces

## Concepts that just got stronger

These ideas are now more defensible, not less.

### 1. Belief Shift

Outside research reinforces that:

- surprise and performance shocks drive fan activity

So this should stay central.

### 2. Hope Inventory

This now has stronger behavioral grounding:

- weak-team fans often stay engaged through future-oriented discussion

### 3. Rival Heat

Intergroup language and spillover research both support this as a genuine behavioral object, not a gimmick.

### 4. Civil War Watch

Conflict within and across communities is real and measurable.

### 5. Team Mood Card

Still the best flagship because it bundles several validated dynamics into one readable surface.

## New concepts worth adding

These are the most promising additions after reviewing outside work.

## 1. Shock Index

Definition:

- the size of the football surprise multiplied by the size of the conversation shift

Why it matters:

- it ties mood movement to football reality
- it avoids generic sentiment-chasing
- it can power weekly and postgame editorial

Best uses:

- homepage
- game pages
- `What Changed This Week`

## 2. Loyalty Temperature

Definition:

- how attached, future-oriented, or bandwagon-prone the discussion around a team appears over time

Why it matters:

- differentiates stable identity from transient hype
- adds depth beyond bullish/bearish

Best uses:

- offseason team cards
- season-long team identity profiles

## 3. In-Group / Out-Group Split

Definition:

- the language gap between how fans describe their own team and how rivals describe that same team or game state

Why it matters:

- sharper than broad sentiment
- rivalry-native
- explainable

Best uses:

- rivalry pages
- matchup pages
- team cards as a secondary module

## 4. Spillover Risk

Definition:

- whether a team's discourse is escaping its home context and becoming a broader emotional event

Why it matters:

- editorially useful
- helps decide when to boost coverage or apply more review

Best uses:

- internal triage
- not necessarily a v1 public stat

## 5. Story Drafting Pipeline

Definition:

- structured automated draft generation for recurring summaries, followed by human review for flagship outputs

Why it matters:

- scales editorial voice without pretending full automation is trustworthy enough

Best uses:

- weekly roundups
- team update blurbs
- archive summaries

## Concepts that should still stay secondary

These are interesting but should not become the new center of gravity.

### Bandwagon Meter

Interesting, but more season-identity than daily hook.

### Spillover Risk

Useful internally, but probably too abstract for early public UI.

### Heavy player-level mood tracking

Still later-phase because entity resolution and sample quality are not strong enough yet.

## Updated prioritization

If we had to rank the strongest current concept family after hardening, it would be:

1. `Team Mood Card`
2. `Belief Shift` / `Shock Index`
3. `Respect Gap`
4. `Rival Heat`
5. `Hope Inventory`
6. `Civil War Watch`
7. `What Changed This Week`
8. `Loyalty Temperature`

## Strategic takeaway

The outside research is not pushing us toward:

- generic sentiment dashboards
- commodity sports pages
- broader but blurrier coverage

It is pushing us toward:

- event-grounded fan behavior
- intergroup language
- surprise-sensitive storytelling
- identity-aware presentation
- human-in-the-loop narrative packaging

That means the moat is getting clearer:

- not `more data than everyone else`
- but `better framing of fandom as a measurable, explainable, and visual product object`

## Sources checked

- `"This is why we play": Characterizing Online Fan Communities of the NBA Teams`
  - https://arxiv.org/abs/1809.01170
- `Jump on the Bandwagon? -- Characterizing Bandwagon Phenomenon in Online NBA Fan Communities`
  - https://arxiv.org/abs/2104.08632
- `Intergroup Contact in the Wild: Characterizing Language Differences between Intergroup and Single-group Members in NBA-related Discussion Forums`
  - https://arxiv.org/abs/1908.10870
- `Do they mean 'us'? Interpreting Referring Expression variation under Intergroup Bias`
  - https://aclanthology.org/2024.findings-emnlp.571/
  - https://aclanthology.org/2024.findings-emnlp.571.pdf
- `Catching Stray Balls: Football, fandom, and the impact on digital discourse`
  - https://aclanthology.org/2025.woah-1.17/
- `The Quest for Omnioculars: Embedded Visualization for Augmenting Basketball Game Viewing Experiences`
  - https://arxiv.org/abs/2209.00202
- `A Community-Driven Data-to-Text Platform for Football Match Summaries`
  - https://aclanthology.org/2024.lrec-main.15.pdf
- `Factors Influencing Fan Acceptance or Rejection of a Sport Team's Revolutionary Rebrand`
  - https://journals.sagepub.com/doi/10.32731/SMQ.322.062023.01
