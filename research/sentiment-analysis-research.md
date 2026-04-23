# College Football Sentiment Analysis Research

Research date: 2026-04-20

## Goal

Evaluate whether this site should add an advanced sentiment analysis feature that:

- stays under roughly `$20/month` in recurring external spend
- does not depend on direct Reddit API access
- does not depend on X/Twitter access
- can explain how `fans of a team`, `rivals`, and the broader `national/world` conversation are talking about teams and players
- produces useful outputs like storylines, positive/negative vibes, player approval, player hate, and rival hostility

This memo is written to fit the current repo direction:

- the site wants to feel authoritative but arguable
- team pages should be `living hubs`
- trends should be a primary layer, not a buried extra
- player coverage is uneven across all levels, so player features need a softer rollout than team features

## Executive take

This feature is worth building, but only if we treat it as `conversation intelligence`, not just naive sentiment analysis.

The best version for this site is:

`a multi-layer sentiment and storyline system that separates fan sentiment, rival hostility, and national narrative`

The bad version is:

- one generic positive/negative score per team
- one sentiment model run over raw posts
- no distinction between team fans, rivals, and neutral media/fans
- no topic extraction
- no emotion layer
- no confidence / data-quality indicators

Under your budget, the best practical stack is:

1. `Reddit` for fan and rival discourse
2. `YouTube comments` for live and postgame emotional reaction
3. `Bluesky` for open-public social chatter as the closest lightweight replacement for X
4. `Google Search / Google News discovery` for national narrative and headlines
5. mostly `local NLP models` for scoring
6. very small optional LLM usage only for final storyline labeling / summarization

The key product insight is that the site should not present this as:

- `Team sentiment: 72`

It should present it more like:

- `Fan Pulse: strongly positive`
- `National Mood: mixed but rising`
- `Rival Heat: high`
- `Main Storylines: QB surge, portal optimism, defense skepticism`
- `Most Loved Players`
- `Most Criticized Players`
- `Most Hated By Rivals`

## Why normal sentiment analysis is not enough

### 1. Team and player sentiment is aspect-level, not document-level

Recent ABSA reviews note that traditional sentiment analysis usually works at document or sentence level and assumes a single subject of opinion. That is a poor fit for sports discourse where one comment can praise a QB, criticize a coach, and mock a rival in the same breath.

Implication:

- use `aspect-based` or `target-based` sentiment
- score the sentiment toward `specific entities` like a team, player, coach, or unit
- do not let one post produce a single score for everything mentioned inside it

### 2. Sentiment and stance are different

Stance detection research explicitly warns that sentiment and stance are distinct. In sports, that matters a lot:

- a rival can talk positively about a player while still arguing that he is overrated
- a fan can be negative in tone about a coach while still supporting the team
- sarcasm and rivalry banter often invert literal polarity

Implication:

- if you want `most hated by rivals`, you need more than sentiment
- you need some notion of `stance / affiliation / rivalry context`

### 3. Emotion matters more than simple polarity in sports

Sports research on football fan reactions found that emotional analysis adds value beyond simple positive/negative labels. Emotions like `joy`, `trust`, `fear`, `anger`, `optimism`, and `surprise` are much closer to how fans actually experience teams and players.

Implication:

- include an `emotion layer` in addition to polarity
- use emotion to power product language like `panic`, `hope`, `rage`, `confidence`, `excitement`

### 4. Topic extraction is useful, but easy to misuse

Reviews of short-text topic modeling for social media warn that researchers often use topic models sub-optimally and that automated topic quality metrics alone do not guarantee meaningful insights.

Implication:

- do use topic clustering for storyline extraction
- but validate topic quality manually
- treat topics as `decision support`, not ground truth

### 5. Sarcasm and profanity are real failure modes

Sarcasm survey work emphasizes that sarcasm flips polarity and is a major challenge for sentiment systems. In sports communities, jokes, irony, memes, and profanity-heavy banter are routine.

Implication:

- expect false positives on emotionally charged game threads
- use a confidence flag
- down-weight posts where sarcasm signals are strong or where models disagree sharply

## Best low-cost data sources

## Source 1: Reddit

Best use:

- team fan sentiment
- rival sentiment
- postgame reaction
- player-specific praise and blame
- long-form fan complaints and optimism

Why it fits:

- college football discourse on Reddit is unusually rich and searchable
- team subreddits and `r/CFB` give natural segmentation between local and national discourse

Budget fit:

- Apify’s official pricing page currently shows a `Free` plan with `$5 to spend in Apify Store`
- low-cost community Reddit actors currently exist at `from $0.50 / 1,000 results`
- there are also actors that scrape Reddit without API keys using public `.json` endpoints

Important implementation note:

- use Reddit mainly for `fan` and `rival` layers
- do not mix `team subreddit`, `r/CFB`, and rival-community discussion into one pool

Good buckets:

- `team fan`: team-specific subreddit, team-specific search queries
- `national`: `r/CFB`, general searches, national discussion threads
- `rival`: rival subreddit searches and rivalry-keyword matches

## Source 2: YouTube comments

Best use:

- emotional reaction after games
- player sentiment around highlights, interviews, and press conferences
- national discussion around big brands, quarterbacks, playoff contenders, and controversial moments

Why it fits:

- YouTube comment threads capture immediate fan emotion well
- official highlights, national media clips, coach pressers, and player clips create natural surfaces

Budget fit:

- official YouTube Data API `commentThreads.list` has `quota cost of 1 unit`
- Google currently says projects get `10,000 units per day` by default
- if you prefer scraping over API integration, Apify community actors currently exist around `$0.25 / 1,000 comments`

Recommendation:

- prefer the official YouTube API first because it is official, cheap, and stable
- keep an Apify comment scraper as fallback if the API becomes inconvenient for a specific workflow

## Source 3: Bluesky

Best use:

- open-public social conversation without depending on X
- national chatter
- media personalities, analysts, and fan accounts

Why it fits:

- Bluesky officially describes itself as an `open social network`
- public endpoints can be queried against `https://public.api.bsky.app`
- Bluesky docs explicitly say the public endpoint is cached and intended for public web use cases

Reality check:

- Bluesky is not a full replacement for X in sports volume
- it is best treated as an `extra national conversation layer`, not the backbone

## Source 4: Search / news discovery

Best use:

- national storylines
- headline momentum
- media framing of teams and players

Why it fits:

- you want to know not just what fans say, but what the broader national conversation is about

Budget fit:

- Apify’s official Google Search Results Scraper currently starts at `from $1.80 / 1,000 scraped search result pages`
- Google News community actors currently appear in the store at low pay-per-result rates, but these are community-maintained and less trustworthy than official APIs

Recommendation:

- use search/news discovery mainly to find URLs, headlines, and query volume patterns
- do not try to build your whole national sentiment layer from scraped full-text articles
- keep this layer lightweight and headline/snippet-oriented unless you later add a real news pipeline

## What I would not rely on

- `X/Twitter`: too unstable and expensive for this budget
- `Perspective API`: officially sunsetting and ending after `December 31, 2026`
- expensive commercial social-listening suites for v1
- full article-body news APIs with commercial terms that exceed your budget

## Recommended product definition

The feature should have `four` different outputs, not one.

### 1. Team Fan Pulse

Questions answered:

- how do this team’s own fans feel right now?
- are they optimistic, furious, anxious, proud, resigned?
- what are the top storylines inside the fanbase?

Suggested fields:

- positive / neutral / negative share
- top emotions
- 7-day trend
- storyline clusters
- confidence score

### 2. National Mood

Questions answered:

- how is the broader college-football world talking about this team?
- are they respected, doubted, ignored, mocked, feared?

Suggested fields:

- national polarity
- national emotion mix
- media/headline storyline mix
- attention volume
- controversy score

### 3. Rival Heat

Questions answered:

- how much hostile attention is this team getting from rival fan communities?
- which rivals are driving it?

Suggested fields:

- rival hostility index
- top rival communities / rival teams
- top hostile storylines
- volume-adjusted hate score

### 4. Player Heat / Approval

Questions answered:

- who is most loved on this team?
- who is taking the most blame?
- who is most hated by rivals?

Suggested fields:

- approval score
- criticism score
- rival hostility score
- optimism / trust / anger / disgust mix
- top positive and negative storylines

## Best-practice NLP stack

## Layer 1: Entity resolution

This repo already has the right base objects:

- `teams`
- `players`
- `player_source_ids`
- `roster_entries`

That should become the canonical entity layer for sentiment too.

Best practice:

- build an alias table for team names, nicknames, abbreviations, mascots, hashtags, and player surface forms
- resolve mentions with team and roster context
- for players, require team context when names are ambiguous

Examples:

- `Bama`, `Alabama`, `Crimson Tide`
- `UGA`, `Georgia`, `Dawgs`
- player full name, surname, jersey references, common nicknames

This matters because player heat maps become unreliable fast if surname-only mentions are attached to the wrong athlete.

## Layer 2: Target-based sentiment

The strongest low-cost off-the-shelf option I found is Cardiff NLP’s `twitter-roberta-base-topic-sentiment-latest`.

Why it fits:

- it is `target based`
- it was trained on `154M tweets` and fine-tuned for topic sentiment
- labels are richer than basic polarity: `strongly negative`, `negative`, `negative or neutral`, `positive`, `strongly positive`

Why this matters:

- if a comment mentions both a team and a player, you can score them separately
- this is much closer to the product you want than generic sentence sentiment

## Layer 3: General sentiment baseline

Useful baseline options:

- `VADER` as a cheap lexicon baseline for social language
- Cardiff NLP `twitter-roberta-base-sentiment-latest` for stronger general sentiment

Why keep both:

- VADER is cheap, fast, and still good as a fallback or ensemble signal
- transformer models are usually better on real sports chatter
- disagreement between the two can become a `low-confidence` signal

## Layer 4: Emotion classification

Cardiff NLP’s `twitter-roberta-base-emotion-latest` is a good fit for a sports product because it produces multi-label emotions such as:

- `anger`
- `anticipation`
- `disgust`
- `fear`
- `joy`
- `love`
- `optimism`
- `pessimism`
- `sadness`
- `surprise`
- `trust`

This is exactly the kind of layer that turns sterile sentiment into sports-native language.

Examples:

- `panic index`
- `hope meter`
- `trust in QB`
- `anger at coach`

## Layer 5: Toxicity / hostility

If you want `most hated by rivals`, polarity alone is not enough.

Use a separate hostility layer such as Unitary/Detoxify-style models.

Caution:

- Unitary’s own model card warns that profanity and swearing can trigger toxicity scores regardless of tone or intent
- it explicitly warns about bias toward vulnerable groups

Implication:

- treat toxicity as a supporting signal, not a final truth
- use it for `rival hostility` and `incivility` indicators
- do not directly label a player as `hated` from toxicity alone

## Layer 6: Storyline extraction

For storyline discovery, BERTopic is a reasonable fit because it uses transformer embeddings, clustering, and class-based TF-IDF to produce interpretable topics and topic reduction.

But the short-text topic-modeling literature is clear:

- topic models are often used sub-optimally
- automated quality metrics are not enough
- preprocessing, topic count choice, and interpretation need discipline

Practical recommendation:

- cluster posts/comments into topics weekly or daily
- manually inspect sample outputs during development
- use LLMs only to `name` or `summarize` clusters after clustering, not to invent the clusters from scratch

## Layer 7: Stance / affiliation

For `fans of a team` vs `rivals` vs `national/world`, build an affiliation classifier.

This does not need to be perfect in v1.

Good practical signals:

- subreddit or channel source
- user flair or self-description when available
- repeated posting about a team
- pronoun language like `we`, `our`, `us`
- rivalry keywords
- linked team pages or channel identity

Then derive three audience buckets:

- `fan`
- `rival`
- `neutral/national`

That single split will improve product quality more than obsessing over one extra point of model F1.

## Recommended scoring framework

Do not output one raw model score.

Create separate derived metrics.

### Team fan sentiment score

Aggregate:

- target-based sentiment toward the team
- weighted by recency
- lightly weighted by engagement
- deduplicated by near-identical text

### National narrative score

Aggregate:

- target-based sentiment in national/general contexts
- storyline cluster volume
- headline momentum

### Rival hostility score

Aggregate:

- negative target sentiment from rival bucket
- toxicity / insult signals
- explicit rivalry language
- volume normalization so large fanbases do not dominate by sheer size

### Player approval score

Aggregate:

- positive target-based sentiment toward player
- positive emotion mix (`joy`, `trust`, `optimism`, `love`)
- positive mention share

### Player criticism score

Aggregate:

- negative target sentiment
- negative emotion mix (`anger`, `disgust`, `sadness`, `pessimism`)
- blame-storyline share

### Controversy score

Aggregate:

- high positive and high negative at the same time
- disagreement between fan and national layers
- disagreement between model families

This is important because many of the most interesting players are not universally loved or hated. They are polarizing.

## Suggested pipeline

### Step 1: Collect

Collect raw public text plus metadata:

- source
- timestamp
- author handle / channel / subreddit
- URL
- title / body / comment text
- engagement counts when available
- thread / parent relationships when available

### Step 2: Normalize

Normalize:

- URLs
- mentions
- hashtags
- obvious spam
- duplicate reposted headlines
- quote tweets / copied headlines / copied YouTube comments where possible

### Step 3: Resolve entities

Attach:

- `team_id`
- `player_id`
- mention span
- mention confidence

### Step 4: Classify audience bucket

Attach:

- `fan`
- `rival`
- `neutral/national`

### Step 5: Score content

For each entity mention:

- target sentiment
- general sentiment
- emotion
- toxicity / hostility
- sarcasm risk
- confidence

### Step 6: Cluster into storylines

Cluster by:

- team + date window
- player + date window

Then generate:

- representative keywords
- short storyline title
- volume / trend
- sentiment mix by storyline

### Step 7: Materialize product tables

Publish:

- team daily sentiment snapshots
- player daily sentiment snapshots
- weekly storyline summaries
- rival hostility leaderboards

This matches the rest of the repo’s philosophy of materializing model-ready tables instead of doing heavy work at request time.

## Product ideas that fit your existing site direction

Your own team-page research says trends should be first-class and the page should feel alive.

That means sentiment should be shown as a `trend and storyline` layer, not a generic sidebar widget.

### Team page modules

Best fits:

- `Fan Pulse`
- `National Mood`
- `Why People Are Talking`
- `Rival Heat`
- `Most Loved / Most Criticized Players`
- `Vibe Over Time`

### Great visual ideas

#### 1. Fan vs National split meter

Show:

- fan sentiment on one side
- national sentiment on the other
- gap between them

This is extremely shareable:

- `fans still believe, nation doesn't`
- `nation is buying in faster than the fanbase`

#### 2. Storyline river

A trend band showing which topics dominate discussion week by week:

- QB development
- offensive line panic
- portal excitement
- playoff skepticism

#### 3. Rival heat map

Matrix:

- rows = rival teams
- columns = hostility, mockery, respect, fear

#### 4. Player temperature board

For a team page:

- hottest riser
- most trusted
- most blamed
- most hated by rivals

#### 5. Sentiment-by-game timeline

Overlay sentiment shifts against:

- games
- upset losses
- rivalry wins
- coaching news
- injuries
- transfer portal events

This fits beautifully with your `rating movement` story on team pages.

## Comparable attempts and benchmarks

## 1. Nashville SC + Vanderbilt

This is the closest publicly documented sports example I found that feels directly useful.

Vanderbilt describes a project with Nashville SC where students used:

- `Aspect-Based Sentiment Analysis`
- `Generative AI`
- over `3,600 Reddit threads`

They focused on aspects like:

- team performance
- stadium atmosphere
- pricing

Why this matters:

- it validates Reddit as a sports-fandom source
- it validates ABSA rather than naive polarity
- it shows a club found the outputs actionable

## 2. 2025 sports fan engagement paper

A 2025 study comparing traditional and transformer-based models found value in a `multi-method framework` for real-time sports fan sentiment analysis.

Important takeaway:

- not every metric matters equally
- the paper highlights accuracy, precision, recall, F1, specificity, statistical validation, and model stability

That is a good reminder not to judge the pipeline on one aggregate number.

## 3. Football fandom emotion research on YouTube + Twitter

The 2025 Tifo paper is useful because it goes beyond valence and explicitly studies:

- general attitudes
- specific emotions

It found predominantly positive sentiment, but more importantly identified meaningful emotion categories.

Why this matters:

- sports products are better when they surface emotion, not just sentiment polarity

## 4. Commercial benchmark: Blinkfire

Blinkfire’s fan-insight products are not cheap v1 tools for this project, but they are very useful as `product benchmarks`.

Their official docs and blog show they care about:

- `Brand Affinity`
- `Top Engaging Fans`
- `Most / Least Popular Posts`
- audience growth over time

Product lesson:

- useful sports sentiment products are not just scoring text
- they connect sentiment to `who`, `what`, and `how much attention`

## Cost scenarios

## Option A: cheapest serious build

Sources:

- Reddit via public JSON or a cheap Apify actor
- YouTube official API
- Bluesky public API
- local open-source models

Estimated recurring external spend:

- `~$0 to $8/month`

Why:

- Bluesky public endpoints are free
- YouTube API quota is generous enough for modest use
- Reddit collection can be done very cheaply

Tradeoff:

- more engineering work
- less turnkey scheduling convenience

## Option B: most practical under $20

Sources:

- Apify Reddit actor
- YouTube API or cheap Apify YouTube comments actor
- occasional Apify Google Search discovery
- local NLP models

Illustrative monthly budget:

- Reddit: `6,000 results` at `$0.50 / 1,000` = `$3.00`
- YouTube: `20,000 comments` at `$0.25 / 1,000` = `$5.00`
- Search discovery: `300 SERP pages` at `$1.80 / 1,000` = `$0.54`
- Total external data spend: about `$8.54`

This is before any free credits.

Apify currently offers a `Free` plan with `$5` monthly spend in the store, so early-stage experimentation can be even cheaper.

Tradeoff:

- community actors can break
- some actor pricing can change
- reliability is lower than official paid APIs

## Option C: what breaks the budget

- Apify `Starter` plan at `$29/month`
- enterprise news APIs
- commercial sports social-listening suites

Conclusion:

- yes, this feature can stay below `$20/month`
- but only if we avoid the instinct to buy a polished enterprise data stack too early

## Recommended v1 / v2 rollout

## V1: team-level conversation intelligence

Ship first:

- Team Fan Pulse
- National Mood
- Key Storylines
- Rival Heat
- Vibe timeline

Why:

- team-level sentiment is much easier to get right
- it aligns tightly with your team-page research
- it does not require full player coverage everywhere

## V1.5: player heat for FBS/FCS first

Ship second:

- most loved players
- most criticized players
- most hated by rivals

But only where player identity coverage is reliable.

That likely means:

- FBS and FCS first
- all-level team sentiment earlier than all-level player sentiment

This matches your existing research that roster/player completeness is uneven.

## V2: rivalry network and national story engine

Ship later:

- rivalry graph
- conference-level conversation maps
- player-vs-player polarity
- sitewide `most polarizing players in America`

## Recommended schema additions

This repo already has the right core canonical objects. I would add a small conversation layer instead of mixing this into raw team/game tables.

Suggested tables:

- `conversation_sources`
- `conversation_documents`
- `conversation_document_entities`
- `conversation_story_clusters`
- `team_sentiment_daily`
- `player_sentiment_daily`
- `team_sentiment_storylines_daily`
- `player_sentiment_storylines_daily`

Suggested `conversation_documents` fields:

- `document_id`
- `source_name`
- `source_document_id`
- `source_parent_id`
- `source_author_id`
- `published_at`
- `url`
- `title`
- `body_text`
- `engagement_score`
- `audience_bucket`
- `language_code`
- `raw_payload_path`

Suggested `conversation_document_entities` fields:

- `document_entity_id`
- `document_id`
- `entity_type` (`team`, `player`, `coach`, `conference`)
- `team_id`
- `player_id`
- `mention_text`
- `mention_confidence`
- `target_sentiment_label`
- `target_sentiment_score`
- `general_sentiment_score`
- `emotion_json`
- `toxicity_json`
- `sarcasm_risk`
- `quality_weight`

Suggested daily materialized outputs:

- `team_id`
- `as_of_date`
- `fan_sentiment_score`
- `national_sentiment_score`
- `rival_hostility_score`
- `emotion_mix_json`
- `storyline_summary`
- `document_count`
- `confidence_score`

## Biggest risks

### 1. Audience segmentation drift

If you do not reliably separate fans, rivals, and national discussion, the outputs will be muddy.

### 2. Player entity ambiguity

Same surnames, nicknames, and generic references can pollute player leaderboards.

### 3. Sarcasm and profanity

Sports banter can look toxic or negative when it is playful or performative.

### 4. Topic quality

Bad clustering will create fake storylines.

### 5. Coverage differences by level

All-level team sentiment is realistic.
All-level player sentiment is much less realistic in v1.

## Final recommendation

Build this feature, but frame it as:

`Conversation Intelligence`

not:

`Sentiment Analysis`

The best low-cost v1 is:

1. Reddit + YouTube + Bluesky + lightweight search/news discovery
2. target-based sentiment for teams and players
3. emotion layer
4. rivalry / hostility layer
5. storyline clustering
6. team-first rollout, then selective player rollout

If we do that, this becomes a real differentiator for the site.

It fits your existing product direction because it makes team pages feel:

- alive
- arguable
- story-first
- trend-driven

That is much more aligned with the repo vision than another stats table.

## Sources

- Local repo docs:
  - [`README.md`](../README.md)
  - [`research/cfb-site-research.md`](./cfb-site-research.md)
  - [`research/team-page-research.md`](./team-page-research.md)
  - [`research/data-ingestion-map.md`](./data-ingestion-map.md)
  - [`research/cfb-data-schema.sql`](./cfb-data-schema.sql)
- Apify pricing: https://apify.com/pricing
- Apify Reddit scraper using public `.json` endpoints: https://apify.com/gentle_cloud/reddit-scraper
- Apify Reddit scraper pricing example: https://apify.com/labrat011/reddit-scraper
- Apify YouTube comments scraper pricing example: https://apify.com/agentflow/youtube-comments-scraper
- Apify official Google Search Results Scraper: https://apify.com/apify/google-search-scraper
- YouTube Data API `commentThreads.list`: https://developers.google.com/youtube/v3/docs/commentThreads/list
- YouTube Data API quota costs: https://developers.google.com/youtube/v3/determine_quota_cost
- Bluesky developer docs: https://docs.bsky.app/
- Bluesky public endpoint guidance and rate limits: https://docs.bsky.app/docs/advanced-guides/rate-limits
- Bluesky public search/posts endpoints:
  - https://docs.bsky.app/docs/api/app-bsky-feed-search-posts
  - https://docs.bsky.app/docs/api/app-bsky-feed-get-post-thread
- Perspective API sunset notice: https://perspectiveapi.com/
- Perspective GitHub docs: https://github.com/conversationai/perspectiveapi
- Nashville SC / Vanderbilt fan sentiment project: https://www.vanderbilt.edu/datascience/2024/08/13/nashville-sc-leveraging-ai-for-fan-sentiment-analysis/
- Sports fan engagement paper (2025): https://doi.org/10.1177/18724981251364377
- Tifo emotions paper (2025): https://doi.org/10.1007/s13278-025-01492-1
- ABSA systematic review (2025): https://doi.org/10.1007/s10462-024-10906-z
- Topic-modeling review for short social text (2023): https://doi.org/10.1007/s10462-023-10471-x
- Stance detection practical guide (2024): https://doi.org/10.1017/psrm.2024.35
- Sarcasm detection survey (2024): https://doi.org/10.1016/j.neucom.2024.127428
- TweetEval benchmark: https://aclanthology.org/2020.findings-emnlp.148/
- BERTweet model: https://huggingface.co/papers/2005.10200
- VADER paper summary / DOI: https://doi.org/10.1609/icwsm.v8i1.14550
- Cardiff NLP target-based sentiment model:
  - https://huggingface.co/cardiffnlp/twitter-roberta-base-topic-sentiment-latest
- Cardiff NLP general sentiment model:
  - https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest
- Cardiff NLP emotion model:
  - https://huggingface.co/cardiffnlp/twitter-roberta-base-emotion-latest
- Unitary toxicity model:
  - https://huggingface.co/unitary/unbiased-toxic-roberta
- Blinkfire fan insights:
  - https://blinkfire-analytics.helpscoutdocs.com/article/17-fan-insights
  - https://analyticsblog.blinkfire.com/blog/2021/11/01/brand-affinities-fan-insights/
