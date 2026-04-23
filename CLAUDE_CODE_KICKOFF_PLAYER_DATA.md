# Claude Code Kickoff — Player Page Data Wiring (Signature Story + The Room on [Player])

**Context**: Figma is executing Stage 2 of the player-page redesign. Two modules need data wiring on our side before they can render with real content: **Signature Story** (5m tier) and **The Room on [Player]** (30s tier). Both require player-scoped data that doesn't exist yet — Signature Story needs a ranking engine over per-player advanced stats; The Room needs `fan_intelligence.py` extended from team-scope to player-scope.

**How to use**: open a fresh Claude Code session in the repo and paste the block below as the first message.

---

```
You are wiring two new player-page data modules for CFB Index: Signature
Story (algorithmic stat surfacing) and The Room on [Player] (player-scoped
fan sentiment). Work through the tasks below one at a time, commit per task,
log progress in SESSION_LOG.md so context can reset cleanly between tasks.

## Read first, in this order
1. CLAUDE.md
2. FAN_INTEL_SOURCE_STRATEGY.md
3. PLAYER_PAGE_WORLD_CLASS_BRIEF.md §§ The Room, Signature Story
4. src/cfb_rankings/fan_intelligence.py — lines 1-80 and 820-890 (don't read whole file)

Do NOT read reporting.py whole. Do NOT read fan_intelligence.py whole beyond
the orientation ranges above. Use offset+limit and Grep for everything else.

## Model routing
- Opus:   schema additions, Signature Story ranking algorithm, cohort-weight
          decisions on player-scoped fan buckets.
- Sonnet: everything implementation — adapters, queries, tests, CLI, template
          wiring into reporting.py.
- Haiku (via Task subagent): row-count verification, grep sweeps, diff review,
          scrape_health canaries.

Every task ends with Haiku-subagent verification evidence. No "I'm done"
without evidence.

## The two features

### Feature A — Signature Story ranking engine

Goal: for any player-season-week, surface ONE stat that defines the player's
season. Must be position-aware (QB/RB/WR/etc have different candidate metric
pools) and cohort-aware (percentile computed against the right peer group).

Output shape (returned from a function in src/cfb_rankings/signature_story.py):
  {
    "player_id": int,
    "headline_stat": {
      "metric_id": "epa_per_dropback_under_pressure",
      "label": "EPA/dropback when blitzed",
      "value": 0.38,
      "unit": "EPA",
      "rank": 1,
      "rank_cohort": "P4 QBs, min 80 dropbacks",
      "percentile": 92.0,
    },
    "narrative": "Best QB in football under pressure — ranks #1 of 72 P4 QBs
                  with at least 80 blitzed dropbacks.",
    "supporting_chart": {
      "type": "cohort_strip",  # or "trajectory", "bar"
      "data": [...],           # cohort members with values for context
    },
    "confidence": {"label": "High", "score": 0.91, "sample_size": 94},
    "updated_label": "Through Week 12",
  }

Selection algorithm (simple and explainable, not ML):
1. Pull all candidate metrics for the player's position from a seed file
   seeds/signature_story_metrics.yaml (you will create it).
2. For each metric, compute (rank, percentile, sample_size) against the
   position cohort (P4 QBs, min-volume gate per metric).
3. Score each candidate by: percentile * log(sample_size) * narrative_weight,
   where narrative_weight comes from the seed file (pressure/third-down
   metrics score higher than vanilla counting stats so the story is
   interesting, not just top).
4. Pick the highest scorer. Emit the shape above.
5. Shape-accurate skeleton when no candidate clears min-volume gate.

This is EXPLAINABLE on purpose. When we ship, every pick must be
auditable — "why did we call Carr the best under pressure" has a
deterministic answer from the seed file + percentile math.

### Feature B — The Room on [Player]

Goal: extend fan_intelligence.py from team-scope to player-scope. Same
grammar (belief dial, cohort buckets, quoted take, confidence, trajectory),
but scoped to mentions of a named player inside the feeding corpus.

Assumptions:
- Player mentions already flow through the same sources that feed
  team_week_conversation_features (confirm in FAN_INTEL_SOURCE_STRATEGY.md).
- If player mentions aren't extracted yet, that is Task B.1 — add
  player_week_conversation_features alongside the team table.
- Cohort buckets: own_fans / rival_fans / national / media — SAME four
  buckets as team scope, just filtered to mentions of this player_id.

Output shape (returned from fan_intelligence.fetch_player_mood_profile):
  mirror fetch_team_mood_profile's shape, but keyed on player_id and with
  a top_quote field surfacing one representative take.

Gates (reuse team-scope discipline):
- MIN_MENTIONS_FOR_SIGNAL = 12   (lower if player mentions are sparser —
                                  decide in Task B.0 with a data probe)
- MIN_AUTHORS_FOR_SIGNAL = 4
- Sarcasm-risk suppression logic: reuse from team scope.

Empty state: graceful "Awaiting Signal" card identical in shape to the
team-scope _empty_profile. The same grammar from fan_intelligence.py must
apply — fans, rivals, national, and media stay separate; rival mockery
never drifts into a player's own fan pulse.

## Task list (execute in order)

### TASK A.0 — Data probe: signature-story feasibility (Sonnet)
Grep the schema for advanced stat tables available per-player-per-game.
Confirm EPA/dropback, CPOE, pressure-to-sack, third-down EPA, red-zone
TD% exist or identify which are missing. Output: one-page
research/signature_story_data_inventory_2026-04-22.md.
Verification: Haiku subagent confirms every metric listed has a real
source table + example row count.

### TASK A.1 — Seed file + metric library (Opus)
Create seeds/signature_story_metrics.yaml. Columns per metric:
id, label, unit, position, candidate_cohort, min_volume, narrative_weight,
sql_query_template. Cover QB fully (10-15 metrics), stub RB/WR with 2-3
each (full coverage later).
Verification: Sonnet runs the YAML through a validator script and confirms
every SQL template parses.

### TASK A.2 — Signature Story engine (Sonnet)
Implement src/cfb_rankings/signature_story.py with
fetch_player_signature_story(db, player_id, season_year, week). Use the
seed file. Colocate test_signature_story.py with fixtures for CJ Carr
(R15 Heisman finalist), a backup (R03), and a walk-on (R00). All three
must return a stable shape — either a real story or a shape-accurate
skeleton.
Verification: pytest -k signature_story passes; Haiku subagent confirms
output shape matches the contract above.

### TASK A.3 — CLI + template wiring (Sonnet)
Add `python manage.py player-signature <player-slug> [--week N]` to cli.py
so Kevin can inspect any player's story from the terminal. Wire the
function into the player-page template in reporting.py at a known line
(Grep for "Player Card Blueprint" ~9821 as the anchor). Minimal HTML
shell — Figma will replace it in Stage 2.
Verification: python manage.py build-site runs clean. Haiku subagent
opens output/site/players/cj-carr-4788.html and confirms the signature
stat renders.

### TASK B.0 — Player-mention probe (Sonnet)
Query the conversation tables and count mentions per player for Week 12,
2025, P4 QBs. Report: median mentions per player, percentile-of-sparsity
where we'd need to relax MIN_MENTIONS_FOR_SIGNAL below 12.
Output: research/player_mention_sparsity_2026-04-22.md.
Verification: Haiku subagent confirms the counts are reproducible from
the query.

### TASK B.1 — Schema: player_week_conversation_features (Opus)
If player-mention extraction isn't already landing in the corpus, design
the migration to add player_week_conversation_features mirroring
team_week_conversation_features. Include cohort bucket fan/rival/
national/media, sarcasm_risk, top_quote_id.
If player mentions ARE already extracted, skip the migration and document
where they live in FAN_INTEL_SOURCE_STRATEGY.md.
Verification: Haiku subagent runs the migration on a throwaway copy of
cfb_rankings.db and confirms existing build still runs.

### TASK B.2 — Player mood adapter (Sonnet)
Implement fan_intelligence.fetch_player_mood_profile(db, player_id,
season_year, week, context). Same shape as fetch_team_mood_profile plus
top_quote. Reuse _fetch_weekly_bucket, _fetch_belief_history by adding a
player_id filter argument. Do NOT duplicate the functions — parameterize.
Colocate test_fan_intelligence_player.py with CJ Carr (high-mention),
backup QB (low-mention → empty state), freshman (no mentions →
_empty_profile).
Verification: pytest passes. Haiku subagent confirms buckets don't leak
(rival mentions never land in own-fan belief score).

### TASK B.3 — Template wiring (Sonnet)
Wire fetch_player_mood_profile into reporting.py at the player-page render
site. Minimal HTML shell. Awaiting-Signal fallback copy reuses the exact
string from team scope (~line 14830) but player-worded.
Verification: python manage.py build-site runs clean. Subagent spot-checks
three players (Carr, a backup, a freshman) and confirms each renders the
right state.

## Stop conditions
- End of Feature A (after TASK A.3): commit, summarize, hand back to Kevin.
- End of Feature B (after TASK B.3): commit, summarize, hand back.
- Context above 60% full: stop at the next task boundary, commit, summarize.
- Any schema change not covered by TASKS A.1 / B.1: AskUserQuestion, don't
  extrapolate.

## Per-task protocol (reuse from fan-intel kickoff)
1. Announce: "Starting TASK X.N — {name}. Model: {Opus|Sonnet}."
2. Read only what's needed.
3. Implement.
4. Spawn Haiku subagent for verification.
5. git commit -m "player-data: TASK X.N — {summary}".
6. Append to SESSION_LOG.md:
   YYYY-MM-DD | TASK X.N | {outcome} | {follow-ups}
7. Move to next task.

## Begin
Start with TASK A.0 (data probe — Sonnet). Produce the inventory file,
verify with a Haiku subagent, commit, log, move to A.1.

If SESSION_LOG.md doesn't exist, create it with header
"# Player Page Data — Session Log" and begin appending.
```

---

## Operator notes (not part of the paste-in)

**Why two features in one kickoff**: Signature Story and The Room on [Player] both unblock Stage 2 Figma work on their respective modules. Running them in parallel tasks keeps the Figma review loop fed with real data instead of placeholders.

**When to paste**: as soon as you want Claude Code rolling on player-scoped data. Ideally in parallel with Figma's Stage 2 execution.

**Feature A is fast, Feature B is slow**. Signature Story is self-contained — seed file + ranking algorithm + CLI + template wire. Player-scoped fan intel may require a schema migration and touches the corpus pipeline; it can stretch across a week if mention-extraction gaps surface.

**Expected landing point**: player-page HTML at `output/site/players/cj-carr-4788.html` renders a real Signature Story card and a real Room-on-Carr card (both in minimal HTML shells) after these 7 tasks ship. Figma will then consume the actual data shapes when Stage 2 modules are ready for integration.
