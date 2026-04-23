# Conference Ranking Research

Last updated: April 21, 2026

## Goal

Upgrade conference rankings from a simple average-of-team-ratings view to a model that better matches how serious fans actually talk about leagues:

- how hard is this conference to survive week to week?
- how dangerous is the top of this conference nationally?
- is this league deep, or just top-heavy?

## Research notes

### KenPom backbone

Most important references:

- https://kenpom.com/blog/ratings-methodology-update/
- https://kenpom.com/blog/determining-the-best-conference/

Key takeaways:

- Ken Pomeroy explicitly moved conference strength away from a plain average.
- His conference rating is the strength of a hypothetical team that would go `.500` against a round-robin schedule.
- He chose that specifically because it reduces the effect of outliers at the bottom of a conference.
- He also wrote that alternate baselines can answer different questions, especially when users care more about the top of a league than the whole thing.

### Supplemental "top-end quality" idea

Useful secondary inspiration:

- https://blog.evanmiya.com/p/an-improved-conference-ranking-system

Key takeaways:

- A pure average can still feel unsatisfying when the national conversation is really about the top of a conference.
- Weighting the best teams more heavily is a reasonable second lens, especially for tournament or title discussions.

## Current site direction

Use a two-layer conference view:

1. `RR50`

- Primary conference sort.
- Defined as the neutral-field rating a hypothetical team would need to go `.500` against a full round robin of league opponents.
- This is the KenPom-like backbone.

2. `Upper Strength`

- Secondary lens for top-end conference quality.
- Weighted toward the best teams in the league, with diminishing weight down the standings.
- This helps separate "deepest conference" from "best title-ceiling conference."

Additional support metrics:

- `Median Power`
- `Resume Pulse`
- `Top-to-Middle Gap`

Small-sample rule:

- very small affiliation groups should be regressed toward their subdivision baseline
- this is especially important for football independents, because a one-team or two-team "conference" should not be allowed to break the board

## Product interpretation

- `RR50` is the best single number for top-to-bottom conference strength.
- `Upper Strength` is better when the question is national ceiling.
- `Median Power` helps explain how sturdy the middle of the league is.
- `Top-to-Middle Gap` helps identify top-heavy conferences versus weekly gauntlets.

## Implementation note

For this football site, conference rank should not collapse everything into one blended mystery score.

Better product behavior:

- rank by `RR50`
- expose `Upper Strength` beside it
- explain the league using both
- keep `Resume` separate from `Power`
