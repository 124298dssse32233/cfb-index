# Monday Brief — Prompt Template

**Cadence**: Monday 10:00 AM ET, 30 minutes (STRATEGY §7).
**Flow**: paste divergence + cohort data snapshot → Claude/GPT drafts → Kevin edits for voice → publishes to Fan Intel Hub.
**Output length target**: 600–900 words, three sections below.

This template is a **prompt you paste into Claude/GPT**, with three data fixtures to fill in first. It produces a draft, not a finished brief — Kevin edits to match the CFB Index voice (plain, confident, never breathless).

---

## Step 1 — Gather data fixtures

Run these three CLIs, paste outputs into the prompt:

```
python manage.py compute-cohort-week --week=YYYY-WW
python manage.py compute-divergence --week=YYYY-WW
python manage.py dump-brief-fixtures --week=YYYY-WW --top=5    # TODO (TASK 8.4 follow-up)
```

`dump-brief-fixtures` produces:

```yaml
divergence_leaderboard:     # 5 highest-divergence teams this week
  - team: Alabama           # with >= 2 qualifying cohorts
    divergence_score: 0.41
    top_cohorts:
      - cohort: die_hard,    sentiment: +0.62
      - cohort: casual_vibes, sentiment: -0.15

confidence_dispersion:      # where signal is weakening
  - team: Oregon
    qualifying_cohorts: 2   # down from 5 week-over-week
    reason: "seatgeek listings dropped to zero; Bluesky firehose outage Saturday"

source_health:              # any source in error state last 24h
  - source_id: bluesky_firehose
    last_error: "2026-04-22T18:02:00Z — websocket disconnect"
    status: recovering

storyline_callouts:         # manually flagged during Monday sweep
  - team_pair: [Alabama, LSU]
    note: "TideFans vs. Tigerdroppings posting wild divergence on QB transfer rumor"
```

---

## Step 2 — The prompt

```
You are drafting the Monday Fan Intelligence Brief for CFB Index, week <YYYY-WW>.

Voice rules (non-negotiable):
- Plain, confident, never breathless.
- Every quantitative claim must cite the source_id it came from. Every.
- When effective_n is below 100, flag the sample as "thin" before asserting.
- Never speculate on demographics we don't measure (race, class, politics, gender).
- Never manufacture drama. If divergence is boring this week, say so.

Write THREE sections, in this order, using only the data provided below.

== Section 1 — Headline Divergence (200-250 words) ==
Lead with the single most interesting team from `divergence_leaderboard`. Explain
WHAT the divergence is (which cohorts disagree, by how much) and WHY it might
matter (relate it to an on-field storyline if there's an obvious one; if not,
say "cause not evident from signal alone — watch next week"). Use the top_cohorts
data exactly; do not invent cohorts.

== Section 2 — Confidence Dispersion Watchlist (200-250 words) ==
List the `confidence_dispersion` teams. For each, state the cohort loss in the
specific terms of the reason field (e.g., "Bluesky firehose dropped for 14 hours
Saturday, which cost Oregon the analytics cohort this week"). This is an
operational note as much as a narrative one — readers should trust the brief
more after reading this, not less.

== Section 3 — Storyline Callouts (200-400 words) ==
For each entry in `storyline_callouts`, write one paragraph. Each paragraph
must include at least ONE pull-quote from the underlying `conversation_documents`
(the fixture will include `top_quote_per_callout`). Quote text as given; do not
summarize paraphrased. Format quotes as blockquote with the capture_url as citation.

Close with ONE sentence that is NOT hype: either "The data is clean this week"
or "This week's signal had [specific problem] — caveat applies."

== Data ==
<paste dump-brief-fixtures output here>
<paste compute-cohort-week output here>
<paste compute-divergence output here>
```

---

## Step 3 — Kevin edits

Common post-draft edits:

- Strip any sentence that opens with "In a world where…" or "As we head into…"
- Replace any hedging ("some observers might say") with a real source citation.
- If the model wrote a divergence score to 3 decimal places, round to 2.
- If the model asserts causality ("because the QB tweeted…"), demote to
  correlation ("alongside the QB's Friday tweet").
- Add one sentence crediting the source diversity count —
  "this brief draws on N sources across M cohorts" — at the top.

---

## Step 4 — Publish

```
# Publish to Fan Intel Hub (TASK 8.4 follow-up — generator TBD)
python manage.py publish-monday-brief --week=YYYY-WW --md=path/to/brief.md
```

The generator writes to `output/site/fan-intel/briefs/<YYYY-WW>.html` and bumps
the Hub's "Latest Brief" pointer. Methodology page already links to the brief
archive once this publisher lands.

---

## Quality bar

A brief is acceptable if:

- [ ] Every quantitative claim cites a source_id.
- [ ] No cohort named that isn't in `cohorts.aggregate.COHORTS`.
- [ ] No sentiment claim made below effective_n=30 (floor rule, STRATEGY §4).
- [ ] All pull-quotes have a live `capture_url` that resolves at publish time.
- [ ] Kevin's voice edits are in; no "As an AI" residue.
- [ ] Under 900 words total.

A brief is excellent if, six months later, we reread it and each claim is still
defensible from the data that was live that week. The archive is canon — we
do not quietly edit past briefs.
