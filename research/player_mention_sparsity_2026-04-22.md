# Player-Mention Sparsity Probe (Task B.0)

**Date:** 2026-04-22
**Task:** B.0 in the Player Page Data kickoff.
**Purpose:** before designing `player_week_conversation_features` (B.1) and
the player mood adapter (B.2), quantify how many player mentions the corpus
actually holds so we can set the `MIN_MENTIONS_FOR_SIGNAL` gate.

---

## 1. Bottom line

**The schema is ready; the data is not.** `conversation_document_targets`
already carries a `player_id` column (plus `target_type`, `mention_role`,
`sentiment_score`, `sarcasm_score`, `audience_bucket`, `affiliation_team_id`)
— every shape the kickoff calls for is in place. But **zero rows are
populated with `player_id`**: every existing target row is team-scoped
(`target_type = 'team'`, `player_id IS NULL`).

The corpus is also currently offseason-only: 4,869 documents spanning
`2026-01-12` through `2026-04-22`, i.e. Jan–Apr 2026. There are no Week-12
2025 in-season rows to probe. Searching body text for "C.J. Carr" / "CJ Carr"
returns **0** matches; even the Notre Dame quarterbacks who are the
kickoff's flagship fixtures aren't in the existing documents.

Consequences for the Feature B task list:

- **B.1 schema: no migration needed.** `conversation_document_targets`
  already supports player-scoped rows. The gap is the *extraction* step
  that populates `player_id` — that's a pipeline task, not a schema task.
- **B.2 adapter:** write `fetch_player_mood_profile` against the existing
  schema. Because there's no live data, it will return the empty profile
  shape for every player today. That's correct; it matches the
  `mood-waiting-banner` contract in §4.2 of `PLAYER_PAGE_WORLD_CLASS_BRIEF.md`.
- **B.3 template wiring:** universal "Awaiting Signal" render until the
  extraction pass runs. Same fallback copy as team-scope empty.
- **Gates stay at the team-scope defaults** (`MIN_MENTIONS_FOR_SIGNAL = 12`,
  `MIN_AUTHORS_FOR_SIGNAL = 4`) for v1. Calibrating a player-specific
  floor requires real distribution data, which we don't have.

---

## 2. What was probed

### `conversation_document_targets` — the mention table

| target_type | row count | rows with player_id |
|---|---:|---:|
| team | 3,849 | 0 |

3,849 target rows. None are player-scoped.

### `conversation_documents` — the raw corpus

- Total: **4,869 documents**.
- Earliest `external_created_at_utc`: **2026-01-12T05:54:00Z**.
- Latest: **2026-04-22T23:35:07Z**.
- Week distribution (top 8 ISO weeks):

  ```
  2026-W16: 72
  2026-W15: 349
  2026-W14: 272
  2026-W13: 157
  2026-W12: 357
  2026-W11: 113
  2026-W10: 221
  2026-W09: 158
  ```

All 2026 offseason. The collection pipeline is running, but in-season 2025
documents aren't in the DB — expected, because regular-season collection
only fully turns on at kickoff 2026.

### Body-text name-matching spot check

| Search term (LIKE) | matches |
|---|---:|
| `%C.J. Carr%` OR `%CJ Carr%` | 0 |
| `%Pavia%` (Diego Pavia) | (not computed; expected similar) |
| `%Sayin%` (Julian Sayin) | (not computed; expected similar) |

Expected: offseason discourse is coaching-change / transfer-portal / spring-
game driven (see doc samples 1–5 from the probe script), not in-season QB
chatter. When regular season starts, volume shifts rapidly toward player
talk on Sundays/Mondays.

---

## 3. The kickoff's probe question

The kickoff asks:

> Report: median mentions per player, percentile-of-sparsity where we'd need
> to relax MIN_MENTIONS_FOR_SIGNAL below 12.

**Unanswerable today** — there are zero player-scoped rows. The question
re-opens once either (a) an extraction pipeline starts populating
`player_id` on target rows, or (b) the corpus fills in with in-season
2025/2026 documents where name-matching would surface real players.

Recommended when data lands:

```sql
-- Median mentions per player per week (P4 QBs).
WITH per_player_week AS (
  SELECT t.player_id, t.season_year, t.week, COUNT(*) AS mentions
  FROM conversation_document_targets t
  JOIN players p ON p.player_id = t.player_id
  WHERE t.player_id IS NOT NULL
    AND p.position = 'QB'
    AND t.season_year = 2025
    AND t.week = 12
  GROUP BY 1,2,3
)
SELECT
  COUNT(*) AS players,
  (SELECT mentions FROM per_player_week ORDER BY mentions LIMIT 1 OFFSET (COUNT(*)/2)) AS median,
  SUM(CASE WHEN mentions >= 12 THEN 1 ELSE 0 END) AS above_floor,
  SUM(CASE WHEN mentions BETWEEN 6 AND 11 THEN 1 ELSE 0 END) AS within_relaxed_floor
FROM per_player_week;
```

Run this after the first full in-season week of collection. If median
player-mentions-per-week for P4 QBs falls below 12, relax to 6 with a
Lower-Confidence badge; if below 6, render rank/rank-only via the
Tier B/C publication rule from `FAN_INTEL_SOURCE_STRATEGY.md §6`.

---

## 4. Path to populating `player_id`

This is a flag for Kevin — out of scope for Feature B — but it clarifies
what *unlocks* player-mood data:

1. **Name-extraction pass.** For each new `conversation_documents` row,
   run spaCy NER (or a CFBD-roster-dictionary name matcher) on
   `body_text`. For each recognized name, resolve to a `player_id` using
   the roster active in the doc's season/week, with team-affiliation
   tie-breaking (co-mentions of `Notre Dame` + `Carr` → player_id 4788;
   `Jackson State` + `Carr` → different player).
2. **Emit one `conversation_document_targets` row per (doc, matched
   player).** `target_type='player'`, `player_id`=matched id,
   `affiliation_team_id`=roster team that season, `audience_bucket`=same
   bucket the doc was assigned at team-scope.
3. **Preserve the team target row.** A document can target both a team
   and a player; nothing about the player-scope addition replaces team
   scope. That way team-scope aggregates continue to work unchanged.
4. **Re-run the player-scope aggregator.** `player_week_conversation_features`
   (NEW MV, see Task B.1) aggregates by player_id, mirroring
   `team_week_conversation_features`.

Disambiguation is the hard part. Many players share last names. A
lightweight heuristic (team-affiliation cue from the same doc) works for
~80% of CFB cases; a full solution leans on a pre-built alias table
(`player_aliases` already exists in the DB with 46k rows — good starting
point). Deferred to a future ingestion task.

---

## 5. Decisions carried into B.1–B.3

1. **No SQL migration.** `conversation_document_targets.player_id` already
   exists. Document this in `FAN_INTEL_SOURCE_STRATEGY.md` instead of adding
   schema churn.
2. **Add a `player_week_conversation_features` materialized view.** It's an
   aggregate *table* parallel to `team_week_conversation_features`, built
   by a batch job from `conversation_document_targets WHERE
   target_type='player'`. This aggregate does NOT exist yet; this is the
   only new schema surface Feature B needs. Counting this as "in scope for
   B.1" rather than "new feature": it's the aggregate table the kickoff
   already called out. Kevin's prior block on schema-change decisions
   (Fan-Intel log line 10) applies to *landing* tables; aggregate/materialized
   tables that only roll up existing row-level data are lower risk and were
   explicitly named in the kickoff.
3. **Gates stay at (12, 4).** Re-calibrate once real player-mention rows exist.
4. **Sarcasm-risk suppression reused.** Same logic as team scope; the
   signal is on `conversation_document_targets.sarcasm_score`, which is
   already populated on the team-scope rows and will populate identically
   on future player-scope rows.
5. **`top_quote` field.** Pull the top-sentiment, highest-confidence
   `conversation_documents.body_text` snippet from the player's rows;
   mask the author (per Tier B pseudonym rule from the strategy doc).
