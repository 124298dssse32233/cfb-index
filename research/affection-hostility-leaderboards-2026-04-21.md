# Affection And Hostility Leaderboards

Research date: 2026-04-21

Companion files:

- `research/fanbase-mood-system-design-2026-04-21.md`
- `research/fan-intelligence-flagship-roadmap-2026-04-21.md`
- `research/conversation-intelligence-v1-data-plan-2026-04-21.md`
- `output/anthropic-love-hate-leaderboards-review.md`

## Purpose

This memo sharpens one of the most naturally viral parts of the product:

- `most loved`
- `most hated`
- `most criticized`
- `most obsessed-over`
- `most polarizing`

The core lesson is:

- these can be great fan-facing categories
- but only if we separate **love**, **criticism**, **rival hostility**, **national fascination**, and **internal fan conflict**

If we blur those together, the output becomes misleading and cheap.

## Core decision

The product should **not** treat `love/hate` as one generic sentiment ladder.

It should separate at least five different things:

### 1. Fan Love

Question:

- `How warmly does a team's own fanbase talk about this team, player, or coach?`

This is the cleanest version of `most loved`.

### 2. Fan Criticism

Question:

- `How much criticism, frustration, or blame is coming from the entity's own side?`

This is much safer and more useful than generic `most hated`.

### 3. Rival Hostility

Question:

- `How much mockery, fear, or obsession comes from rival audiences?`

This is the best replacement for many `most hated team` ideas.

### 4. National Fascination

Question:

- `How much attention is the broader sport paying to this entity, whether positive or negative?`

This captures:

- discussion volume
- centrality in the sport's conversation
- main-character energy

### 5. Polarization

Question:

- `Are people sharply split on this team, player, or coach?`

This is especially useful for:

- players
- coaches
- big-brand teams

## Best public framing by entity type

The right answer is different for teams, players, and coaches.

## Teams

Teams are the strongest place to be bold.

Why:

- team-level targets are easier to resolve
- the risk is lower than ranking individual humans
- college-football fandom is inherently tribal and rivalrous

### Best team leaderboards to ship

- `Most Loved By Their Own Fans`
- `Most Criticized By Their Own Fans`
- `Rival Heat Leaders`
- `National Darlings`
- `National Villains`
- `Most Polarizing Teams`
- `Living Rent-Free`

### Best interpretation of the original instinct

Instead of one `most hated teams` board, split it into:

- `Most Criticized By Their Own Fans`
- `Most Hated By Rivals`
- `Most Talked About Nationally`

That is far more informative.

## Players

Players are strong later, but should be narrower and more careful.

Why:

- player name disambiguation is harder
- player discussion is thinner for non-stars
- player-specific hostility can turn ugly fast

### Best player categories later

- `Most Loved Stars`
- `Most Discussed Players`
- `Most Polarizing Players`
- `Most Praised Breakout Players`
- `Most Criticized Featured Players`

### Best constraints

- only for award-watch players, quarterbacks, and major headline names
- require much larger samples than team-level boards
- never present thin-sample criticism as a broad truth

### Important wording rule

Avoid:

- `most hated player`

Prefer:

- `most criticized player`
- `most polarizing player`
- `main character player`

Those are stronger editorially and much safer.

## Coaches

Coaches are probably the weakest place to be cavalier.

Why:

- coach discussion is often highly negative
- coach blame is noisy and event-driven
- the current repo does not yet have a rich dedicated coach entity / alias system like it does for players

Current repo reality:

- `team_seasons` stores coach names like `head_coach`
- but there is not yet a full coach identity layer comparable to `players` plus `player_aliases`

That makes coaches a later-phase product even if the editorial idea is strong.

### Best coach categories later

- `Coach Confidence`
- `Hot Seat Heat`
- `Most Trusted Coaches`
- `Most Criticized Coaches`
- `Most Polarizing Coaches`

### Avoid

- `most hated coach`

That wording adds heat without adding insight.

## Best v1 public leaderboards

The strongest launch boards are still mostly team-level and behavior-focused.

### Immediate launch board candidates

- `Most Loved By Their Own Fans`
- `Most Criticized By Their Own Fans`
- `Rival Heat Leaders`
- `Most Polarizing Fanbases`
- `National Darlings`
- `National Villains`
- `Living Rent-Free`

### Boards that pair especially well with the mood system

- `Delusion Meter`
- `Panic Meter`
- `Reality Check Leaders`
- `Biggest Vibe Shifts`
- `Civil War Watch`

These are not exactly `love/hate` boards, but they scratch the same fan itch while being even more ownable.

## Best labeling system

The biggest product win is to keep the buckets separate and label them cleanly.

## For teams

### Good labels

- `Most Loved By Their Own Fans`
- `Most Criticized By Their Own Fans`
- `Rival Heat`
- `National Darlings`
- `National Villains`
- `Most Polarizing`

### Bad labels

- `most hated team`
- `least likable team`
- `internet sentiment rank`

`Most hated team` is tempting, but it collapses:

- rival hatred
- national annoyance
- fan frustration

into one muddy category.

## For players

### Good labels

- `Most Loved Stars`
- `Most Criticized Stars`
- `Most Polarizing Players`
- `Most Discussed Players`

### Bad labels

- `most hated player`
- `least liked player`

## For coaches

### Good labels

- `Coach Confidence`
- `Hot Seat Heat`
- `Most Criticized Coaches`
- `Most Trusted Coaches`

### Bad labels

- `most hated coach`

## Recommended metric mapping

Each leaderboard should map to a specific source bucket and interpretation.

### Most Loved By Their Own Fans

Use:

- fan audience bucket only
- positive share
- trust / joy weighting
- minimum volume threshold

### Most Criticized By Their Own Fans

Use:

- fan audience bucket only
- negative share
- anger / fear weighting
- minimum volume threshold

### Rival Heat

Use:

- rival bucket only
- attention plus negativity
- allow fear / respect to count, not only mockery

### National Darlings / Villains

Use:

- national bucket only
- separate positive and negative national sentiment rather than averaging everything together

### Polarization

Use:

- disagreement / polarity spread
- especially strong when positive and negative shares are both high

## Best archetypes

Leaderboards are even better when paired with archetypes.

### Teams

- `Beloved`
- `Besieged`
- `Rent-Free`
- `Polarizing`
- `Main Character`

### Players

- `Crowd Favorite`
- `Lightning Rod`
- `Breakout Darling`
- `Punching Bag`

### Coaches

- `Trusted`
- `Under Fire`
- `Polarizing`
- `Unshakeable`

## Biggest risks

### 1. Mixing buckets

This is the single biggest mistake.

If rival hostility is mixed into fan sentiment, the output becomes nonsense.

### 2. Thin individual samples

Team-level boards are much easier to support than player or coach boards.

For individuals, require:

- substantially larger mention counts
- better entity resolution
- stronger moderation review

### 3. Harassment-vector wording

Words like:

- `hated`
- `least likable`
- `worst person`

create a much uglier product than:

- `criticized`
- `under fire`
- `polarizing`

### 4. One-thread dominance

Especially for players and coaches, one viral clip or one ugly thread can swamp the sample.

### 5. Cheapening the brand

If the site sounds like a tabloid outrage machine, it will undermine the smarter fan-intelligence positioning.

The best tone is:

- sharp
- playful
- honest

not:

- cruel

## Launch sequence recommendation

### Phase 1

Ship only team-level boards:

- `Most Loved By Their Own Fans`
- `Most Criticized By Their Own Fans`
- `Rival Heat Leaders`
- `National Darlings`
- `Most Polarizing Teams`

### Phase 2

Add featured-player boards:

- `Most Loved Stars`
- `Most Polarizing Players`
- `Most Criticized Stars`

Only for:

- quarterbacks
- Heisman/watchlist players
- major headline names

### Phase 3

Add coach boards carefully:

- `Coach Confidence`
- `Hot Seat Heat`
- `Most Polarizing Coaches`

This phase should wait until coach entity mapping and better moderation rules exist.

## Final recommendation

The instinct is good.

Fans absolutely will care about:

- who is loved
- who is hated
- who everyone is obsessed with
- who gets blamed

But the best product version is not a blunt `love/hate` board.

It is a more precise set of boards:

- `fan love`
- `fan criticism`
- `rival hostility`
- `national fascination`
- `polarization`

That keeps the site fun and sharp while still feeling smarter and more original than generic outrage content.
