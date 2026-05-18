# Claude Code Kickoff — Player-Mention Extraction Pipeline

**Context**: "The Room on [Player]" ships a skeleton/"Awaiting Signal" shell across all 15,939 player pages today because `conversation_document_targets.player_id` is never populated. The schema is ready. The aggregator is ready. The adapter is ready. The template is ready. The missing piece is the NER step that extracts player names from corpus text and attaches a `player_id` to target rows.

**Once this lands**, `compute_player_week_mood` will populate `player_week_conversation_features`, which `compute_player_mood_index` reads, which renders live Room-on-[Player] cards with real belief dials, cohort breakdowns, and top quotes — everywhere in the player-page network.

**How to use**: open a fresh Claude Code session in the repo and paste the block below as your first message.

---

```
You are wiring the player-mention extraction pipeline for CFB Index. This is
the final unblock for the live "The Room on [Player]" surface. Work through
the tasks below one at a time, commit per task, log progress in SESSION_LOG.md.

## Read first, in this order
1. CLAUDE.md
2. FAN_INTEL_SOURCE_STRATEGY.md §§ on player-scope mentions (if any)
3. PLAYER_PAGE_WORLD_CLASS_BRIEF.md §§ The Room
4. src/cfb_rankings/fan_intelligence.py lines 1-80 (orientation only)
5. src/cfb_rankings/cohorts/player_aggregate.py (the downstream consumer)
6. migrations/20260423_01_player_conversation_features.sql
7. SESSION_LOG.md entries for tasks B.0, B.1, B.2, B.3, B.4

Do NOT read reporting.py whole. Use Grep and offset+limit. Same for
fan_intelligence.py beyond the orientation range above.

## Model routing
- Opus:   NER strategy decisions, disambiguation rule design, schema additions.
- Sonnet: default. Extractor implementation, adapter, tests, backfill CLI.
- Haiku (via Task subagent): verification, row-count checks, precision/recall
          spot-checks on extraction samples.

Every task ends with Haiku-subagent verification evidence.

## The feature

Goal: for every row in `conversation_documents`, extract player name mentions
from body_text, disambiguate to a single player_id (or drop ambiguous
mentions), and write one row per extracted mention into
`conversation_document_targets` with:
- target_type = 'player'
- player_id populated
- mention_role (subject / mentioned-in-passing)
- sentiment_score / sarcasm_score (inherit from document if not computable
  at the mention level in v1; per-mention classification is a follow-up)
- audience_bucket (inherit from the document's context)
- affiliation_team_id (the player's current team)

Target precision goal: ≥ 0.95 for the high-salience bucket (top-500 QBs by
roster_week visibility). Recall matters less than precision in v1 — a missed
mention is invisible; a false mention poisons belief.

## Task list (execute in order)

### TASK M.0 — Data probe + name-map build (Sonnet)
Query `roster_week` (or `players`) to build a canonical name map:
  player_id → {first_name, last_name, full_name, team_id, position, roster_years}
Count ambiguity classes: how many shared surnames ("Smith"), shared full
names across seasons, shared full names within a single team/week.
Output: `research/player_name_disambiguation_2026-04-23.md` with counts, the
hard cases surfaced, and a recommended disambiguation strategy.

Decision rule seed: team-context first (if document has affiliation_team_id,
prefer players on that team), position context second (use context words like
"QB"/"quarterback" near the name), surname uniqueness third, drop if still
ambiguous. Document the seed rules in the research file so Opus can refine
in M.1.

Verification: Haiku subagent confirms the counts are reproducible and the
disambiguation strategy handles 10 spot-check cases Haiku picks itself.

### TASK M.1 — Disambiguation rule set (Opus)
Promote the M.0 seed rules into a formal ruleset in
`src/cfb_rankings/ingest/player_disambiguation.py`. Input: a candidate name
string + document context (source_id, affiliation_team_id, surrounding
tokens). Output: (player_id | None, confidence ∈ [0, 1]).

Rules, in order of application:
1. Full name match → try team context first, then surname uniqueness.
2. Surname-only match → require team context OR position context; else drop.
3. Nickname match (seed file `seeds/player_nicknames.yaml` — stub for v1
   with the 40 top name-class players: Carr, Pavia, Beck, etc.).
4. Handle transfer cases: if a name resolves to two player_ids across
   seasons, prefer the CURRENT-season roster entry when the document is
   current-season.
5. Ambiguity escape hatch: if two rules tie at the same confidence level,
   drop the mention and log to `scrape_health` with
   reason='ambiguous_player_mention'.

Unit tests in `tests/test_player_disambiguation.py` covering:
- Unambiguous full name → player_id with confidence 1.0
- Surname with team context → player_id with confidence 0.8+
- Surname without context → None
- Collision case (two active Smiths on same team) → None unless first initial
- Transfer case (Pavia 2024 Vandy → 2025 Vandy) → correct season player_id
- Nickname match → player_id with confidence 0.7
- Junk name ("Coach", "He", "The QB") → None

Verification: Haiku runs the test suite + hand-picks 20 real document
passages and verifies the disambiguator's calls against ground truth.

### TASK M.2 — Extractor (Sonnet)
`src/cfb_rankings/ingest/player_mention_extractor.py` — the extraction
function:
  extract_player_mentions(document_row) -> list[Mention]
where Mention has (player_id, start_char, end_char, mention_role, confidence).

Implementation: regex + named-entity heuristics, NOT a full NER model in v1.
- Pass 1: scan for full-name matches against the M.0 name map.
- Pass 2: scan for title-case token sequences ≥ 2 words, try disambiguation.
- Pass 3: scan for standalone surnames near position indicators (QB/RB/WR).
- mention_role: 'subject' if the mention appears in the first 30% of body_text
  OR in the title/headline; else 'passing'.
- confidence: inherited from the disambiguator.

Drop mentions with confidence < 0.7. Log drops to scrape_health under
'low_confidence_mention' for sampling.

Unit tests with fixture documents covering: title mention, body mention,
repeated mention (should emit distinct Mention rows, not dedupe), adjacent
coach name that shouldn't match a player (e.g. "Freeman" the head coach vs
"Freeman" the player), quote attribution ("said Carr" pattern).

Verification: Haiku runs tests + precision spot-check on 30 real documents
sampled across Tier A / B sources.

### TASK M.3 — Write pipeline (Sonnet)
`src/cfb_rankings/ingest/player_mention_writer.py` — applies the extractor
across conversation_documents and writes rows into
conversation_document_targets.

Idempotency: use a deterministic `dedup_key` on
(document_id, player_id, start_char) so re-runs upsert cleanly.

Bulk path: add CLI `python manage.py extract-player-mentions
[--since YYYY-MM-DD] [--source-id X] [--limit N]`. Default runs incrementally
from the latest target row's document_id high-watermark. Writes one
scrape_health row per run (source_id='_player_mention_extractor').

Per-document rate: log a progress line every 1,000 documents. Expect
~10–50k mentions written on a full-corpus first run.

Verification: Haiku runs the CLI on a 100-document slice, counts mentions
written, confirms dedup on re-run, confirms scrape_health row present.

### TASK M.4 — End-to-end wire + live smoke (Sonnet)
Run the extractor across the current corpus (~4,869 documents per SESSION_LOG
B.0 entry). Then run:
  python manage.py compute-player-week-mood --week=2026-16
and confirm `player_week_conversation_features` gets populated.

Then run:
  python manage.py build-site
and confirm at least one player page (pick the player with the most
mentions) renders a LIVE Room-on-[Player] card instead of "Awaiting Signal."
Post the HTML snippet of that card to SESSION_LOG.md.

Verification: Haiku opens 5 player pages — high-mention, mid-mention,
low-mention, zero-mention, and a walk-on — and confirms each renders the
correct state (live / partial / empty).

### TASK M.5 — Methodology page update (Sonnet)
Regenerate `output/site/methodology/fan-intelligence.html` to document the
player-mention extractor: what it does, the confidence floor, the drop-rule
for ambiguous mentions, link to source code.

Verification: Haiku diffs the methodology page before/after.

## Stop conditions
- End of TASK M.3 if extractor performance is weird (precision <0.9 on the
  spot-check). Stop, summarize, hand back.
- Context above 60%.
- Any schema change not covered here (M.1 adds an NER heuristics file; M.3
  uses the existing targets table — no schema change expected).

## Per-task protocol
Same as prior kickoffs.
1. Announce: "Starting TASK M.N — {name}. Model: {Opus|Sonnet}."
2. Read only what's needed.
3. Implement.
4. Haiku subagent verification.
5. git commit -m "player-mention: TASK M.N — {summary}"
6. Append to SESSION_LOG.md.

## Begin
Start with TASK M.0 (data probe + name-map build — Sonnet). Produce the
research file, verify with a Haiku subagent, commit, log, move to M.1.
```

---

## Operator notes

**Why this matters most right now**: Every design investment in The Room on [Player] — the belief dial, the cohort pills, the trajectory spark, the top-quote pattern — is invisible to users until mentions get extracted. This is the single change that converts 15,939 Awaiting-Signal cards into live cards.

**Why v1 is regex + heuristics, not a neural NER**: The name map is bounded (~3,000 active P4+G5 players), the corpus is domain-specific (football context disambiguates most surnames), and regex + rules ships this week. A neural NER with confidence calibration is a month-long project for marginal precision gains. Promote to NER when the rule-based system hits a ceiling.

**Cost expectation**: 6 tasks, mostly Sonnet, one Opus (M.1 disambiguation design). Haiku for verification. Should land in 2-3 Claude Code sessions.

**Expected user-visible outcome after M.4**: CJ Carr's page shows a populated Room card. So do the 500-1,000 players with the most in-corpus chatter. Everyone else still shows Awaiting Signal (correctly — no signal to publish).
