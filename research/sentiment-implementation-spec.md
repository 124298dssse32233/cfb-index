# College Football Conversation Intelligence Implementation Spec

Research date: 2026-04-20

## Purpose

This document turns [`research/sentiment-analysis-research.md`](./sentiment-analysis-research.md) into a concrete implementation plan for this repo.

The goal is to add a low-cost conversation layer that:

- stays under roughly `$20/month` in recurring third-party spend
- does not require direct Reddit API access
- does not rely on X/Twitter access
- plugs into the existing ingestion and materialization patterns in this backend
- uses strong off-the-shelf tools where they already exist
- only custom-builds the pieces that are specific to college-football entity resolution and product logic

This spec assumes the existing project direction still holds:

- heavy work happens in batch ingestion, not at request time
- the app reads from derived tables
- canonical `teams`, `players`, and `roster_entries` are the source of truth
- product value comes from storylines and trends, not just raw scores

## Core decision

Do not build a custom end-to-end sentiment platform.

Build a `conversation intelligence` pipeline by combining:

- `Apify` for the scraping/orchestration pieces we do not need to own
- official public APIs where they are cheap and stable
- open-source social-text NLP models for scoring
- repo-specific entity resolution and aggregation logic for the college-football layer

In short:

- `buy` collection and wrappers where possible
- `use` proven open-source NLP
- `build` entity mapping, audience bucketing, and product-specific aggregation

## What we should not reinvent

The following should be treated as solved enough by existing tools for v1:

- scraping public Reddit surfaces
- scraping Google search results pages
- calling scheduled scraper jobs
- baseline social-text sentiment classification
- baseline irony, hate, and offensive-language classification
- topic clustering
- keyword extraction

The following are the pieces that are worth custom-building because they are product-specific:

- team and player alias resolution for college football
- fan vs rival vs national audience bucketing
- player ambiguity handling with roster context
- derived metrics like `Fan Pulse`, `National Mood`, and `Rival Heat`
- gating rules that decide when data quality is good enough to publish

## Recommended buy/use/build matrix

| Layer | Recommendation | Why |
| --- | --- | --- |
| Reddit collection | `Apify` actor called from `apify-client` | Avoid building or maintaining a Reddit scraper. Works without direct Reddit API access. |
| YouTube comments | Official `YouTube Data API` first, `Apify` fallback | Official API is cheap and stable. Scraping only when needed. |
| Bluesky posts | Direct `requests` calls to public Bluesky endpoints | Public endpoints already exist. No need to insert Apify in the middle. |
| Search and news discovery | Apify `Google Search Results Scraper` | Do not build SERP parsing or proxy management ourselves. |
| General sentiment, irony, offensive, hate, NER | `tweetnlp` | Existing package built for social text. Faster path than composing multiple raw model wrappers ourselves. |
| Target-based sentiment | `transformers` + Cardiff NLP target sentiment model | This is the highest-leverage model for team/player scoring. |
| Emotion | `transformers` + Cardiff NLP emotion model | Sports discussion is better expressed through emotion than plain polarity. |
| Topic clustering | `BERTopic` | Off-the-shelf clustering and interpretable topic labels without custom modeling. |
| Keyword extraction | `KeyBERT` | Quick way to get candidate storyline phrases from clusters. |
| Vector storage | `pgvector` only if our Postgres supports it cleanly | Reuse Postgres instead of adding a separate vector database. Optional, not required for v1. |

## Recommended source stack

### Source 1: Reddit

Use Reddit as the main signal for:

- fan mood
- rival hostility
- postgame emotion
- player praise and blame

Implementation choice:

- use an existing `Apify` Reddit actor instead of building a scraper or relying on direct API access
- prefer actors that use public `.json` endpoints and return normalized thread/comment payloads

What we store:

- thread title
- self text
- comment text
- subreddit
- author name if public
- score / replies when available
- permalink
- published timestamp
- parent-child relationship

### Source 2: YouTube comments

Use YouTube for:

- postgame reaction
- highlight-video reaction
- press-conference reaction
- player-specific sentiment on clips and interviews

Implementation choice:

- use the official `YouTube Data API` first
- only fall back to `Apify` for edge cases the API does not cover well

Important budget detail:

- Google currently documents a default quota of `10,000` units per day
- `commentThreads.list` is documented at `1` quota unit per request as of `December 4, 2025`

Important implementation detail:

- avoid leaning on `search.list` for large-scale discovery because Google's quota table documents `search.list` at `100` units per request
- prefer discovering candidate videos through Google search, rankings/news logic, or curated channel lists, then use cheap comment reads on the known video ids

That makes YouTube the cheapest official source in this stack.

### Source 3: Bluesky

Use Bluesky for:

- open-public national conversation
- analyst and media chatter
- social reaction outside Reddit

Implementation choice:

- use public Bluesky endpoints directly with `requests`
- do not pay for a scraper unless Bluesky access changes materially

Reality check:

- Bluesky adds useful public chatter
- it is not a complete replacement for old sports-Twitter volume
- it should be an extra layer, not the core of the feature

### Source 4: Search and headline discovery

Use search discovery for:

- national headlines
- story detection
- finding relevant URLs and videos to pull comments from

Implementation choice:

- use Apify's official Google search actor
- keep this layer URL and snippet oriented
- do not build full-text news sentiment in v1

This layer is mainly there to improve storyline coverage, not to become a separate news platform.

## Budget strategy

The budget does not break because of models.

The budget breaks when we try to collect too much text for too many teams at too high a frequency.

That means the real optimization lever is `coverage strategy`, not model optimization.

### Recommended monthly budget target

- `Reddit collection`: `$3 to $7`
- `Search discovery`: `$1 to $3`
- `YouTube API`: effectively `$0` unless we choose a paid scraper fallback
- `Bluesky`: `$0`
- `Optional cluster naming with a small LLM`: `$0 to $3`

Target external spend:

- `normal month`: `$6 to $12`
- `busy month`: keep below `$18`

### Apify plan caveat

As of `2026-04-20`, Apify's public pricing page shows:

- `Free`: `$0` with `$5` prepaid usage
- `Starter`: `$29/month`

That means the under-`$20` path should not assume a permanent `Starter` subscription.

The practical budget-safe path is:

- use the `Free` plan and stay disciplined on run volume when possible
- use direct official APIs where they are cheaper than scraping
- only consider moving collection logic into a custom actor path if store-actor limits become the blocker

In other words:

- `Apify` is still a good fit
- but we should treat it as a carefully used collection layer, not an always-on paid subscription assumption

### Coverage rules to stay under budget

Do not run full daily collection for every team and every player in every division.

Instead:

- keep `FBS` team coverage always on
- keep `ranked FCS` and featured `FCS` teams always on
- make `DII` and `DIII` conversation coverage event-driven or page-demand-driven until volume proves worthwhile
- keep `player` coverage on a watchlist, not a full-roster crawl

Good watchlist inputs:

- current rankings
- weekly rating movement
- rivalry week schedules
- upset alerts
- transfer-portal buzz
- Heisman / awards / All-America candidate lists
- site traffic if that becomes available

This is how we stay under budget without making the product feel small.

## Recommended v1 product scope

Ship `team-level` conversation intelligence first.

### V1 outputs

- `Fan Pulse`
- `National/Public Mood`
- `Rival Heat`
- `Key Storylines`
- `Vibe Over Time`

### V1.5 outputs

- `Most Loved Players`
- `Most Criticized Players`
- `Most Hated By Rivals`

But only for:

- `FBS`
- `FCS`
- teams with strong roster identity coverage

### Not in v1

- all-player coverage across all divisions
- full article-body news sentiment
- real-time live dashboards
- custom finetuned college-football sentiment models
- a separate vector database

## Recommended pipeline shape

This repo already uses ingestion plus derived tables. The sentiment feature should follow the same model.

### Phase 1: Collect

Collect raw public text into normalized document rows.

Each row should include:

- source name
- source document id
- parent id when present
- published timestamp
- url
- title
- body text
- engagement counters when present
- source community metadata such as subreddit or channel
- raw payload path

### Phase 2: Normalize and dedupe

Normalize:

- whitespace
- urls
- obvious copied headlines
- trivial reposts
- cross-post duplicates where detected

At this stage, do not lose the original raw text.

### Phase 3: Resolve entities

Attach mentions to canonical objects in this repo:

- `team_id`
- `player_id`

This is where most of the custom value lives.

Key rule:

- a player mention should prefer `team + season` context before attaching to a person

Example:

- `Sanders` is not safe to resolve without context
- `Colorado QB Sanders` is much safer

### Phase 4: Audience bucketing

Classify each document into one or more audience buckets:

- `fan`
- `rival`
- `national`

Do not force a hard label when confidence is low.

Use a confidence score and allow `unknown` during enrichment.

Practical signals:

- subreddit or channel prior
- self-referential language like `we`, `our`, `us`
- explicit rivalry terms
- repeated posting about a team
- team flair or profile metadata when public

### Phase 5: Score each mention

For each team or player mention, calculate:

- target-based sentiment
- general sentiment
- emotion labels
- irony risk
- offensive or hate flags
- model-agreement confidence

Optional:

- add a toxicity classifier only if rivalry outputs need more separation than `negative + offensive + hate` already provide

### Phase 6: Build storylines

Cluster documents into storylines by:

- entity
- date window
- audience bucket

Recommended flow:

1. embed and cluster with `BERTopic`
2. extract candidate phrases with `KeyBERT`
3. use a tiny LLM step only to compress the cluster into a display title if necessary

The cluster naming step is the only place where LLM usage should be considered in v1.

### Phase 7: Materialize derived tables

Publish daily or weekly snapshots into app-facing tables.

This keeps the frontend fast and makes the sentiment layer behave like the rest of the backend.

## Recommended model stack

### Baseline social-text package

Use `tweetnlp` for the tasks it already packages well:

- general sentiment
- irony
- offensive language
- hate speech
- NER

Why:

- it is already built for social text
- it reduces wrapper code
- it avoids us wiring a different model package for every basic classifier

### Target-based sentiment

Use Cardiff NLP's target-sentiment model through `transformers`.

Reason:

- target-based sentiment is the most important classifier in this feature
- it is much closer to the actual product question than plain document sentiment

Without target-based scoring, we will misread posts that praise one entity and attack another in the same sentence.

### Emotion

Use Cardiff NLP's emotion model through `transformers`.

Reason:

- sports discourse is often better explained as `anger`, `fear`, `joy`, `trust`, `optimism`, or `pessimism`
- this produces much more compelling product language than a flat positive/negative score

### Topic clustering

Use `BERTopic`.

Reason:

- it already combines transformer embeddings with clustering and class-based TF-IDF
- it supports practical topic exploration and incremental workflows
- we do not need a custom topic model to get to useful storylines

### Keyword extraction

Use `KeyBERT`.

Reason:

- it is simple
- it is local
- it is good enough for cluster keywords and storyline candidates

### Optional embeddings

Use `pgvector` only if:

- the database environment supports the extension cleanly
- we want semantic similarity inside Postgres

If enabling `pgvector` creates deployment or hosting friction, skip it in v1.

`BERTopic` and `KeyBERT` can still be useful without adding vector search to the production database.

## Schema additions

Keep the conversation layer separate from sports metadata and model tables.

Recommended new tables:

- `conversation_sources`
- `conversation_documents`
- `conversation_document_entities`
- `conversation_story_clusters`
- `team_sentiment_daily`
- `player_sentiment_daily`
- `team_storylines_daily`
- `player_storylines_daily`

### `conversation_sources`

Suggested fields:

- `source_id`
- `source_name`
- `source_type`
- `description`
- `is_active`

### `conversation_documents`

Suggested fields:

- `document_id`
- `source_id`
- `source_document_id`
- `source_parent_document_id`
- `source_author_id`
- `source_author_name`
- `community_name`
- `published_at`
- `fetched_at`
- `language_code`
- `url`
- `title`
- `body_text`
- `engagement_score`
- `audience_bucket`
- `audience_confidence`
- `dedupe_hash`
- `raw_payload_path`

Key uniqueness rule:

- unique on `source_id + source_document_id`

### `conversation_document_entities`

Suggested fields:

- `document_entity_id`
- `document_id`
- `entity_type`
- `team_id`
- `player_id`
- `mention_text`
- `mention_start_char`
- `mention_end_char`
- `mention_confidence`
- `target_sentiment_label`
- `target_sentiment_score`
- `general_sentiment_label`
- `general_sentiment_score`
- `emotion_json`
- `irony_score`
- `offensive_score`
- `hate_score`
- `quality_weight`

### `conversation_story_clusters`

Suggested fields:

- `story_cluster_id`
- `entity_type`
- `team_id`
- `player_id`
- `audience_bucket`
- `window_start_date`
- `window_end_date`
- `cluster_label`
- `cluster_keywords_json`
- `document_count`
- `sentiment_summary_json`

### `team_sentiment_daily`

Suggested fields:

- `team_id`
- `as_of_date`
- `fan_sentiment_score`
- `national_sentiment_score`
- `rival_hostility_score`
- `emotion_mix_json`
- `document_count`
- `confidence_score`
- `top_storyline_summary`

### `player_sentiment_daily`

Suggested fields:

- `player_id`
- `team_id`
- `as_of_date`
- `approval_score`
- `criticism_score`
- `rival_hostility_score`
- `emotion_mix_json`
- `document_count`
- `confidence_score`
- `top_storyline_summary`

## Raw payload storage

Do not store only the normalized text.

Store raw source payloads for replay and debugging.

Recommended pattern:

- write raw payloads to `data/raw/conversation/<source>/<yyyy-mm-dd>/...json.gz`
- store the file path in `conversation_documents.raw_payload_path`

Why this matters:

- community actors can change payload shapes
- entity resolution logic will improve over time
- backfills are much easier when raw payloads are preserved

This follows the same practical spirit as the existing ingestion guidance in this repo.

## CLI and module layout

The existing CLI design suggests keeping this as explicit subcommands.

Recommended additions:

- `ingest-conversations`
- `enrich-conversations`
- `build-conversation-snapshots`
- `backfill-conversations`

### Example responsibilities

`ingest-conversations`

- call Reddit, YouTube, Bluesky, and search collectors
- normalize documents
- dedupe obvious duplicates
- write raw documents

`enrich-conversations`

- run entity resolution
- run audience bucketing
- run classifiers

`build-conversation-snapshots`

- build daily team and player aggregates
- cluster and label storylines
- materialize derived tables

`backfill-conversations`

- rerun collection and enrichment for a historical window
- used when actor behavior changes or alias logic improves

### Recommended module shape

- `src/cfb_rankings/clients/apify.py`
- `src/cfb_rankings/clients/youtube.py`
- `src/cfb_rankings/clients/bluesky.py`
- `src/cfb_rankings/ingest/conversation.py`
- `src/cfb_rankings/conversation/entities.py`
- `src/cfb_rankings/conversation/audience.py`
- `src/cfb_rankings/conversation/scoring.py`
- `src/cfb_rankings/conversation/storylines.py`

This keeps the feature aligned with the current repo structure instead of becoming a sidecar app.

## Environment and dependency additions

If we implement this spec, the likely new environment variables are:

- `APIFY_API_TOKEN`
- `YOUTUBE_API_KEY`
- `BLUESKY_BASE_URL=https://public.api.bsky.app`
- `CONVERSATION_RAW_DIR=./data/raw/conversation`
- `CONVERSATION_MODEL_VERSION=conversation-v0.1.0`

Likely dependency additions:

- `apify-client`
- `tweetnlp`
- `transformers`
- `torch`
- `bertopic`
- `keybert`
- `sentence-transformers`
- `pgvector` as optional

I would not add these dependencies to `pyproject.toml` until we actually start implementation, because they are meaningfully heavier than the current base backend stack.

## Alias and entity-resolution strategy

This is the highest-value custom logic in the feature.

We need explicit alias coverage for:

- school names
- abbreviations
- mascots
- hashtags
- common shorthand
- coach references
- player full names
- player last names
- player nicknames when stable

Recommended supporting table:

- `entity_aliases`

Suggested fields:

- `entity_alias_id`
- `entity_type`
- `team_id`
- `player_id`
- `alias_text`
- `alias_type`
- `season_year`
- `priority_weight`

### Resolution rules

Good rules:

- prefer exact team alias matches over fuzzy matches
- prefer player matches that also have matching team context
- suppress surname-only player resolution when multiple candidates exist
- allow a lower-confidence unresolved state instead of forcing a bad match

This is far more important than squeezing one more classifier into the stack.

## Audience-bucketing strategy

`Fan`, `rival`, and `national` should not be treated as just a sentiment problem.

It is a metadata and heuristics problem first.

Recommended order of operations:

1. use source priors first
2. use community identity second
3. use text heuristics third
4. use soft confidence, not forced certainty

Examples:

- a team subreddit is a strong `fan` prior
- `r/CFB` is a strong `national` prior
- a rival team subreddit mentioning the team is a strong `rival` prior
- `we looked awful` is a fan-leaning hint, but should not override stronger source metadata

## Derived metric definitions

Avoid publishing raw model outputs directly.

Translate model outputs into product metrics.

### `Fan Pulse`

Built from:

- target sentiment toward the team
- fan-bucket only
- recency weighting
- engagement weighting
- confidence weighting

### `National Mood`

Built from:

- target sentiment in national buckets
- storyline mix
- headline and video-discussion volume

### `Rival Heat`

Built from:

- rival-bucket target negativity
- offensive and hate signals
- rivalry-language boosts
- volume normalization so big fanbases do not dominate by sheer scale

### `Player Approval`

Built from:

- positive target-based sentiment toward player
- trust, joy, optimism, and love signals
- minimum-volume thresholds

### `Player Criticism`

Built from:

- negative target-based sentiment toward player
- anger, disgust, sadness, and pessimism signals
- blame-storyline share

### `Most Hated By Rivals`

Do not compute this from one negative score.

Use all of:

- rival bucket only
- strong target negativity
- hostility indicators
- minimum number of distinct threads or source communities

That protects us from one viral thread producing a fake leaderboard.

## Publishing thresholds

This feature will look smarter if it withholds weak outputs.

Recommended minimums before showing a public score:

- team daily score: at least `20 to 30` resolved mentions in the rolling window
- player leaderboard appearance: at least `12 to 15` resolved mentions plus multiple distinct threads
- storyline cluster publication: at least `5` documents after dedupe

If thresholds are not met:

- show `insufficient signal`
- or suppress the module entirely

This is better than pretending weak data is precise.

## Quality controls

This feature needs a small manual-eval loop from day one.

Recommended practices:

- maintain a hand-labeled evaluation set across fan, rival, and national examples
- include examples with sarcasm, profanity, rivalry jokes, and multi-entity posts
- review cluster quality every week during development
- log disagreement between general sentiment and target sentiment
- log unresolved player mentions rather than forcing them into bad matches

### Key confidence inputs

Good confidence features:

- model agreement
- entity-resolution confidence
- audience-bucket confidence
- source reliability
- duplicate density
- minimum document count

## Rollout plan

### Phase A: foundation

- add conversation schema
- add collection clients
- add raw payload storage
- add document normalization and dedupe

### Phase B: team sentiment MVP

- add team alias resolution
- add audience bucketing
- add team target sentiment, general sentiment, and emotion scoring
- materialize `team_sentiment_daily`
- materialize team storylines

### Phase C: player leaderboards

- add player alias resolution tied to rosters
- add player-level snapshots
- add guarded player leaderboards for FBS and FCS

### Phase D: refinement

- tighten rivalry classification
- add better hostility handling if needed
- add optional semantic retrieval with `pgvector`
- add selective LLM summarization only where it clearly improves UX

## Final recommendation

The best path is not to build a bespoke sentiment engine from scratch.

The best path is:

1. use `Apify` for Reddit and search collection
2. use the official `YouTube Data API`
3. use public `Bluesky` endpoints directly
4. use `tweetnlp`, Cardiff NLP models, `BERTopic`, and `KeyBERT`
5. custom-build only the college-football-specific intelligence layer

That gives us a feature that is:

- affordable
- maintainable
- aligned with the repo's current architecture
- differentiated enough to matter on team pages

If we follow this spec, the feature should feel like:

- a living conversation layer for teams and players

not:

- a generic sentiment badge

## Sources

- Local repo docs:
  - [`README.md`](../README.md)
  - [`research/sentiment-analysis-research.md`](./sentiment-analysis-research.md)
  - [`research/data-ingestion-map.md`](./data-ingestion-map.md)
  - [`research/cfb-data-schema.sql`](./cfb-data-schema.sql)
- Apify pricing, checked `2026-04-20`: https://apify.com/pricing
- Apify Python client docs: https://docs.apify.com/api/client/python/docs
- YouTube Data API quota usage: https://developers.google.com/youtube/v3/getting-started
- YouTube Data API quota costs, checked from Google's current docs page: https://developers.google.com/youtube/v3/determine_quota_cost
- Bluesky rate limits and public endpoint guidance: https://docs.bsky.app/docs/advanced-guides/rate-limits
- Bluesky docs home: https://docs.bsky.app/
- TweetNLP repository: https://github.com/cardiffnlp/tweetnlp
- Cardiff NLP general sentiment model: https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest
- Cardiff NLP target-based sentiment model: https://huggingface.co/cardiffnlp/twitter-roberta-base-topic-sentiment-latest
- Cardiff NLP emotion model: https://huggingface.co/cardiffnlp/twitter-roberta-base-emotion-latest
- BERTopic docs: https://maartengr.github.io/BERTopic/
- KeyBERT docs: https://maartengr.github.io/KeyBERT/
- pgvector Postgres extension: https://github.com/pgvector/pgvector
- pgvector Python support: https://github.com/pgvector/pgvector-python
