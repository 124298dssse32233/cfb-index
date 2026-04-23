# Offseason Homepage Execution

Research date: 2026-04-22

Companion files:

- `research/offseason-modules-calendar-2026-04-21.md`
- `research/offseason-modules-recommendation-2026-04-21.md`
- `research/fan-intelligence-flagship-roadmap-2026-04-21.md`
- `research/unique-concepts-market-honesty-2026-04-22.md`

## Purpose

This memo turns the offseason strategy into a concrete homepage and fan-intelligence rendering stance for the live site.

The key constraint is simple:

- today is `April 22, 2026`
- the next real product window is `April -> August kickoff`
- the homepage should feel aware of that window instead of talking like every day is a game week

## What changed in code

`src/cfb_rankings/reporting.py` now has an explicit offseason-aware editorial layer.

That layer adds:

- month-aware home hero copy for `April`, `May`, `June`, `July`, and `August`
- a `Road To Kickoff` section that maps the full `April -> August` runway
- an `Offseason Mood Board` framing so the homepage no longer defaults to generic weekly copy in offseason mode
- a visible `Fanbase Civil War Watch` homepage card, using the already-computed `polarized` board rows

## What the homepage should now communicate

## 1. The offseason is not one blob

The site should make clear that:

- `April` is a post-spring reset
- `May` is identity formation
- `June` is summer discourse drift
- `July` is media-days and conference-mood season
- `August` is certainty theater meeting real uncertainty

This is the most important framing correction.

## 2. The fan-intelligence layer should stay usable even before the sample is full

The homepage should not collapse into:

- empty generic placeholders

Instead, the empty-state version of the mood board should explain:

- what kinds of modules belong in the current month
- what the site is waiting on before publishing live leaderboards

That keeps the product honest without feeling dead.

## 3. Civil war is a first-class story

The code already computed `polarized` fanbases.

The homepage was not surfacing that.

That is now corrected because:

- internal disagreement is one of the best fan-facing stories
- it matters in both offseason and in-season modes
- it fits the site's `argument engine` identity

## What is intentionally still not shipped

## 1. `Shock Index`

This is still a recommended next build, not a finished live metric.

Reason:

- the strongest version needs better event-level surprise context
- the current offseason window is not the best place to fake a football-shock product

## 2. Strong `What Changed This Week` explanations on the homepage

This is also still not fully shipped.

Reason:

- the repo stores `conversation_storylines`
- but the current homepage does not yet have a strong aggregate explanation layer built from those rows
- current live storyline coverage is still thin, so a rushed implementation would risk noise

## Recommended next implementation order

1. Keep the offseason-aware homepage framing.
2. Improve conversation collection volume and storyline quality.
3. Add a homepage `What Changed This Week` / `What Changed Right Now` explanation rail once storyline coverage is stronger.
4. Add `Shock Index` once surprise inputs are grounded in football events rather than only belief deltas.

## Verification note

The new homepage helpers now pass both:

- isolated helper rendering checks
- a full `python manage.py build-site` run against the latest valid snapshot

Important nuance:

- earlier in the day, the latest visible snapshot briefly pointed at a `model_runs.week` value that did not line up with the latest available `power_ratings_weekly.week` rows for that model run
- that created a temporary `No model runs found for static site` symptom
- later verification with the current latest valid snapshot completed successfully, so the homepage work is no longer blocked by that earlier transient mismatch

## Strategic takeaway

The site should now treat the offseason as:

- a sequence of changing emotional seasons

not:

- a dead zone before kickoff

That is the right voice for the product from `April 22, 2026` through the start of games in `August 2026`.
