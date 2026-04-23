# CFB Language Understanding

Research date: 2026-04-21

Companion files:

- `research/sentiment-implementation-spec.md`
- `research/fanbase-mood-system-design-2026-04-21.md`
- `research/conversation-intelligence-v1-data-plan-2026-04-21.md`
- `output/anthropic-cfb-language-sarcasm-review.md`

Relevant external sources:

- TweetNLP paper: https://aclanthology.org/2022.emnlp-demos.5/
- TweetEval benchmark repo: https://github.com/cardiffnlp/tweeteval
- Cardiff irony model card: https://huggingface.co/cardiffnlp/twitter-roberta-base-irony

## Purpose

This memo answers a practical concern:

- how do we make the conversation layer understand memes, sarcasm, doomposting, rivalry bait, and other real CFB fan-language patterns well enough that the site does not feel clueless?

The goal is not perfect sarcasm detection.

The goal is:

- fewer embarrassing misreads
- better confidence gating
- more realistic public outputs

## Bottom line

We should treat college-football internet language as a distinct dialect.

That means the pipeline should not rely on:

- plain sentiment alone

It should use a layered system:

1. social-text baseline models
2. CFB-specific rules and pattern detection
3. audience-bucket separation
4. confidence gating
5. human review for the most visible outputs

## What the external sources say

The external tool and benchmark landscape supports this direction.

### TweetNLP

The TweetNLP paper describes an integrated social-media NLP toolkit with reasonably sized Transformer models specialized on social-media text, intended to run without dedicated cloud infrastructure.

That matters because it fits our stack:

- Python batch jobs
- local inference
- moderate cost discipline

Source:

- https://aclanthology.org/2022.emnlp-demos.5/

### TweetEval

The official TweetEval benchmark explicitly includes:

- sentiment
- emotion
- irony
- offensive
- hate
- stance

That is exactly the kind of social-text task bundle we need.

Sources:

- https://github.com/cardiffnlp/tweeteval
- https://huggingface.co/cardiffnlp/twitter-roberta-base-irony

### Cardiff irony model

The current Hugging Face model card for `cardiffnlp/twitter-roberta-base-irony` says the model was trained on about `58M tweets` and then fine-tuned for irony detection with TweetEval.

That makes it a useful baseline, not a full solution.

The model card also shows:

- example inference
- TweetNLP integration

Source:

- https://huggingface.co/cardiffnlp/twitter-roberta-base-irony

## The right architecture

The right v1 is a **three-tier sarcasm defense**.

### Tier 1: Baseline social-text models

Use local models for:

- sentiment
- emotion
- irony
- offensive / toxic flags

Best practical v1 stack:

- `tweetnlp` for general social-text tasks
- Cardiff / TweetEval irony model
- existing target-resolution and team/player mapping

These models are not enough by themselves, but they give the first pass.

### Tier 2: CFB-specific language rules

This is where the real improvement comes from.

Build a small explicit rules layer for college-football internet language.

Examples of patterns we should flag:

- `we are so back`
- `it is so over`
- `natty bound`
- `we want bama`
- `heisman campaign starts now`
- `fire everyone`
- `this program is cooked`
- `never doubted him` after obvious prior criticism
- sarcastic `great` / `awesome` / `love this` near negative game context

The purpose is not perfect interpretation.

The purpose is:

- flag likely sarcasm
- downgrade confidence
- reroute questionable content out of headline outputs

### Tier 3: Audience-aware interpretation

This is critical.

The same sentence means different things depending on who is saying it.

Examples:

- a rival calling a team `elite` may be mockery
- a long-suffering fan saying `great season` may be sincere relative to expectations
- doomposting from a blueblood fanbase has different baseline meaning than optimism from a rebuilding program

So the model output should always be conditioned by:

- `fan`
- `rival`
- `national`
- `unknown`

Never collapse these together.

## Best product rule

The public site should show:

- interpreted outputs
- labels
- confidence bands

It should **not** expose raw classifier confidence or raw irony calls as if they were truth.

## How to reduce embarrassing misreads

### 1. Confidence gating

When signals conflict, confidence should fall.

Lower confidence when:

- sentiment is strongly positive but irony is also elevated
- rivalry language is present
- one thread dominates the sample
- meme phrases dominate the top examples
- the audience bucket is mostly `unknown`

### 2. Phrase-level warning rules

Keep a hand-built library of:

- meme phrases
- cope phrases
- victory-lap phrases
- obvious rivalry bait

These do not need to fully classify the content.

They only need to:

- mark text as sarcasm-risky
- lower confidence
- optionally change downstream bucket weighting

### 3. Sample diversity rules

Do not publish a strong read when:

- one post or one video dominates
- one angry thread controls the sample
- post volume is too low

### 4. Homepage review queue

Only the highest-visibility surfaces need manual review.

That means:

- homepage leaderboards
- social cards
- especially spicy labels

should have a human pass when confidence is weak or sarcasm risk is high.

Team pages can tolerate softer uncertainty language.

## What should be public vs internal

### Public

- `Fan Pulse`
- `Reality Check`
- `Swing Meter`
- `Rival Heat`
- `Most Panicked Fanbases`
- `Most Polarizing Fanbases`
- storyline summaries
- confidence labels like `Low`, `Medium`, `High`

### Internal only

- raw irony score
- raw toxicity score
- exact phrase-trigger flags
- source-specific diagnostic breakdowns
- low-confidence edge-case examples

The point is:

- keep the public product readable
- keep the messy classifier guts behind the scenes

## What is realistic in v1

### Realistic

- social-text baseline models
- explicit CFB meme phrase flags
- separate audience buckets
- confidence downgrades
- manual review for homepage outputs
- simple sarcasm-risk annotations in internal data

### Not realistic yet

- perfect sarcasm understanding
- full meme lifecycle analysis
- custom fine-tuned college-football sarcasm model
- robust player-level irony handling for the whole sport
- real-time live inference for every spike

## Best v1 product behaviors

### Good

- `Fan Pulse: Cautiously Hopeful (Medium Confidence)`
- `Rival Heat: High`
- `Top Storyline: QB panic is dominating discussion`
- `Belief Shift: Down sharply after the upset`

### Bad

- `Indiana sentiment score: 0.742`
- `Everyone loves this coach`
- `Fans are positive`
- `This player is hated`

The public outputs should reflect uncertainty and context.

## Best long-term improvement path

### Phase 1

- use current social-text models
- add CFB phrase library
- add sarcasm-risk flagging
- add human review for homepage

### Phase 2

- build a manually labeled evaluation set from real CFB posts
- review false positives by category
- calibrate thresholds with real site use

### Phase 3

- if the feature proves valuable, fine-tune or adapter-tune on manually labeled CFB sarcasm / rivalry samples

That is the correct order.

Do not start with custom model training.

## Immediate implementation recommendations

1. add an internal `sarcasm_risk` layer that combines model score plus hand-built CFB phrase triggers
2. create a `cfb meme lexicon` file for common irony and doomposting phrases
3. lower public confidence when irony risk and positive sentiment collide
4. keep fan / rival / national buckets visually and analytically separate
5. route low-confidence homepage candidates into a manual review queue

## Final rule

The system does not need to perfectly understand every joke.

It does need to avoid the most humiliating failure:

- confidently misunderstanding obvious fan sarcasm as literal belief

If we design for:

- confidence-aware interpretation
- bucket separation
- CFB-specific phrase handling

the product can feel like it understands real fan culture without pretending the NLP is magical.
