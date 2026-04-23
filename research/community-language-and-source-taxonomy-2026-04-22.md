# Community Language And Source Taxonomy

Last updated: April 22, 2026

## Bottom line

The repo now has a credible v1 path for offseason fan-intelligence collection, but the source mix has to stay honest:

- `r/CFB` is the best cheap `national` pulse.
- team subreddits are the best cheap `fan` pulse for a first pass.
- rival signal should come from targeted search inside rival communities, not from dumping an entire rival board into one team bucket.
- message boards are where the richest identity language lives, but they should be phase two because collection complexity and moderation friction are higher.

The key product insight is that fans do **not** talk in generic positive/negative sentiment language.
They talk in:

- fatalism
- cope
- rivalry taunts
- expectation management
- recruiting and portal anxiety
- inside-joke identity labels

If we flatten all of that into plain sentiment, the product will feel fake.

## What live research says

### Reddit scale

As of April 22, 2026, public Reddit metadata from `about.json` showed:

- `r/CFB`: `4,465,796` subscribers
- `r/MichiganWolverines`: `105,002`
- `r/OhioStateFootball`: `81,685`
- `r/georgiabulldogs`: `72,292`
- `r/USC`: `69,019`
- `r/FloridaGators`: `61,193`
- `r/huskers`: `51,940`
- `r/LonghornNation`: `49,502`
- `r/LSUFootball`: `48,210`
- `r/rolltide`: `47,370`
- `r/ockytop`: `44,595`
- `r/wde`: `20,985`
- `r/NDFootball`: `346`

Important implication:

- Reddit is strong enough for `national` and many major-brand `fan` communities.
- It is not uniform across teams.
- Notre Dame is the clearest example of a school where Reddit alone is too weak and message boards need to carry more weight later.

### Message-board scale

Live On3 board listings reinforce that message boards are still core CFB fan infrastructure:

- On3 `The Main Board`: `306.8K` threads / `13.7M` messages and described as "College Football's Most Unhinged Message Board"
- Tennessee `The General's Quarters`: `218.1K` threads / `3.6M` messages
- Texas A&M `Northgate`: `93.8K` threads / `2.1M` messages
- Texas `IT Members Only`: `102.6K` threads / `5.7M` messages
- Alabama `BOL Round Table`: `80.7K` threads / `2.3M` messages

Important implication:

- if we want the most tribal, identity-rich language, boards matter a lot
- if we want the cheapest and easiest v1, Reddit still wins
- the best medium-term setup is Reddit first, then selectively add boards for schools whose Reddit communities are small or too general

## How people actually talk

### 1. National Reddit is newsy, ironic, and offseason-obsessed

Recent `r/CFB` and related RSS/search results show a mix of:

- transfer portal rules and tampering anxiety
- spring game weirdness
- recruiting announcements
- countdown and preseason speculation threads
- absurdist inside-joke language

Examples from live threads and feed titles:

- "people who really like football year round"
- "we're back"
- "sickos"
- "immortal"

What that means for us:

- `national` should be treated as broad conversation atmosphere, not fan identity
- it is good for `Respect Gap`, `National Darlings`, and `Main Character` style modules
- it is weaker for "what do this team's own fans believe?" unless paired with team communities

### 2. Team subreddits are expectation-management machines

Recent team-subreddit threads were full of:

- post-spring depth-chart talk
- portal patience vs portal panic
- coaching trust or distrust
- realistic win-range debates
- "I care more about QB development than record" logic

Live examples:

- Michigan fans debating a record range from `7-5 to 11-1`
- Michigan fans saying they are "cautiously optimistic"
- Tennessee threads centered on post-spring depth chart projections
- portal threads framed as "no need to panic"

What that means for us:

- team subreddits are ideal for `Fan Pulse`
- offseason `fan` content should emphasize belief, patience, skepticism, and developmental hope
- these communities are often more nuanced than national social media, which is exactly what we want

### 3. Message boards carry the best rivalry and identity language

The most revealing language in live message-board reads was not generic sentiment. It was identity language:

- `Battered Aggie Syndrome`
- `rent free`
- `little brother`
- `Weird melt`
- `Embrace the Hate`

These are not just funny phrases.
They are markers of:

- self-aware fatalism
- rivalry fixation
- taunting posture
- intra-fanbase scar tissue
- outsider mockery

What that means for us:

- rivalry modules should not be pure negative sentiment
- we need explicit meme and taunt detection
- "obsession", "rent free", and "little brother" are better product concepts than raw hostility scores alone

## Product consequences

### Bucket strategy

We should keep three public buckets as the core:

- `fan`
- `national`
- `rival`

And we should map them this way:

### `fan`

Use:

- direct team-subreddit listings
- football-context filtering
- later, team-specific message boards where Reddit is weak

Why:

- source prior is stronger than text heuristics alone

### `national`

Use:

- `r/CFB` search and listing collection
- later, media and YouTube additions

Why:

- this is where the broad sport mood and outsider perception lives

### `rival`

Use:

- targeted search for Team A inside Team B communities
- not full-rival-board dumps

Why:

- rival communities mostly talk about themselves, not the target
- targeted mention search is much cleaner for a cheap v1

## What we shipped today

The repo now has a new config-driven Reddit collection path:

- new CLI command: `collect-reddit-plan`
- new collector path for direct team-subreddit listings with football-context filtering
- new starter plan file: `research/reddit-community-plan-v1.json`
- richer meme / rivalry lexicon in `conversation_utils.py`
- fan-intelligence fallback fixed so it no longer requires `source_name='all'` to render signal

## Exact commands

Use this sequence:

```powershell
python manage.py seed-team-aliases --season 2025
python manage.py collect-reddit-plan --season 2025 --week 21 --plan research\reddit-community-plan-v1.json
python manage.py build-conversation-features --season 2025 --week 21
python manage.py build-site
```

## What the live verification showed

### Collection run

The plan run against `season=2025` and `week=21` produced:

- `69` total documents
- `70` total team targets

Breakout highlights:

- Michigan fan bucket from `r/MichiganWolverines`: `12` docs
- Ohio State fan bucket from `r/OhioStateFootball`: `8` docs
- Texas fan bucket from `r/LonghornNation`: `6` docs
- Michigan rival bucket via `r/OhioStateFootball` search: `10` docs

### Feature build

The follow-up feature build for `2025 week 21` produced:

- `45` daily rows
- `14` weekly rows
- `42` storyline rows

### Site build

After the fallback fix and the aligned `week=21` collection:

- the static site built successfully
- the fan-intelligence board no longer stayed empty forever
- Michigan's team page rendered a live mood state instead of only "Awaiting Signal"

## What to prioritize from April through August

These are the best modules for the current source mix:

- `Team Mood Card`
- `Fanbase Civil War Watch`
- `Respect Gap Census`
- `Rival Heat`
- `What Changed Right Now`

These can all be grounded in `fan`, `national`, and targeted `rival` buckets without pretending we have perfect truth.

## What to avoid asking too early

Avoid leading with:

- exact cross-platform "most hated" claims
- player-level mood for every team
- broad coach reputation rankings
- any claim that implies we fully understand every fanbase equally well

Why:

- some teams have weak Reddit communities
- message-board coverage is not wired in yet
- coach and player identity resolution is still less mature than team resolution

## Honest current gaps

- `r/aggies` was weak as a football-first `fan` source in this first pass
- some general school subreddits still need better thread-level filtering
- storyline extraction can still pick up mixed-sport noise in broad communities
- message boards are not yet ingested, even though they are culturally important

## Recommended next step

The next best move is not "add every source."

It is:

1. Keep the current Reddit plan and make it stable.
2. Add `5-10` more high-signal team communities carefully.
3. Add one message-board path for a school with distinctive language and weak Reddit signal.
4. Only then expand public rivalry and hostility products.

## Live source references

- Reddit `r/CFB`: https://www.reddit.com/r/CFB/
- Reddit `r/MichiganWolverines`: https://www.reddit.com/r/MichiganWolverines/
- Reddit `r/OhioStateFootball`: https://www.reddit.com/r/OhioStateFootball/
- Reddit `r/ockytop`: https://www.reddit.com/r/ockytop/
- Reddit `r/LonghornNation`: https://www.reddit.com/r/LonghornNation/
- On3 boards directory: https://www.on3.com/boards/
- TexAgs BAS thread: https://texags.com/forums/5/topics/3568695
- SEC Rant example thread: https://www.secrant.com/rant/sec-football/hey-ou/120023656/
- TigerDroppings rivalry thread: https://www.tigerdroppings.com/rant/lsu-sports/texas-aandms-sad-obsession-with-lsu/110964200/
