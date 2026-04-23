# Player-Page Data Pipeline

How raw conversation documents become live player-page modules (The Room on
[Player], Signature Story). Reference doc for Kevin; keep it here, not in
CLAUDE.md, since CLAUDE.md is a context doc for every agent session.

Current state: **code-complete, awaiting ingestion**. Every module below is
built, tested, and shippable; the only missing piece is populating
`conversation_document_targets.player_id`, which the tagger does on demand
and is currently opted out of auto-run.

## Pipeline overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                             RAW INGESTION                              │
│                                                                        │
│  reddit / bluesky / boards / RSS                                       │
│        ↓                                                               │
│  conversation_documents (body_text + metadata + provenance)            │
│        ↓  classifier pass (existing; writes team-scope targets)        │
│  conversation_document_targets (target_type='team', sentiment etc.)    │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (NEW — this build)
┌────────────────────────────────────────────────────────────────────────┐
│                     PLAYER-SCOPE EXTRACTION (B.5)                      │
│                                                                        │
│  python manage.py tag-player-mentions --season=YYYY [--commit]         │
│        - Builds a name index bounded to in-season QBs/RBs/WRs          │
│          with real stats (561 QB/RB/WR in 2025 via player_value_metrics│
│          + extensions via player_season_stats).                        │
│        - Full-name substring match against body_text + title_text.     │
│        - Team-affiliation tiebreak for ambiguous full names.           │
│        - Inherits sentiment / emotion / sarcasm / confidence / week /  │
│          audience_bucket from the doc's existing team target row.      │
│        - Dry-run by default. --commit required to insert rows.         │
│                                                                        │
│  Writes: conversation_document_targets (target_type='player',          │
│          player_id, affiliation_team_id, audience_bucket, plus         │
│          inherited sentiment signals).                                 │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  PLAYER-SCOPE AGGREGATION (B.1 + B.4)                  │
│                                                                        │
│  python manage.py compute-player-week-mood --week=YYYY-WW              │
│        - Groups rows by (player_id, source_name, audience_bucket).     │
│        - Sentiment classification (POS_CUTOFF=+0.1, NEG=-0.1).         │
│        - Emotion share from emotion_primary.                           │
│        - Log-scaled attention (likes+replies+views).                   │
│        - Average confidence + sarcasm; sarcasm_risk label              │
│          (low < 0.25, moderate < 0.5, high otherwise).                 │
│        - Per-bucket top_quote selected by |sentiment| × confidence.    │
│        - Upserts via unique index ux_pwcf_keys. Idempotent.            │
│                                                                        │
│  Writes: player_week_conversation_features (B.1 migration).            │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         READER PATH (B.2 + B.3)                        │
│                                                                        │
│  fan_intelligence.fetch_player_mood_profile(db, player_id, season, wk) │
│        - Reads player_week_conversation_features via                   │
│          _fetch_weekly_bucket_scoped(scope='player', ...).             │
│        - Returns the same shape as fetch_team_mood_profile + top_quote.│
│        - Gates: MIN_MENTIONS_FOR_SIGNAL=12, MIN_AUTHORS_FOR_SIGNAL=4.  │
│                                                                        │
│  compute_player_mood_index(db, season, week)                           │
│        - Batch version for site-build hot path. Groups per-player on a │
│          single table scan.                                            │
│                                                                        │
│  reporting.py  →  _render_the_room_card(story, player_name)            │
│        - Minimal HTML shell injected at #the-room in every player      │
│          page, above the algorithmic Signature Story section.          │
│        - Empty state = "Awaiting Signal"; ready state renders belief,  │
│          4-bucket pill row, respect_gap/swing/cohesion, top quote.     │
└────────────────────────────────────────────────────────────────────────┘
```

## Inspection CLIs

For debugging one player at a time:

```bash
# The Room on [Player] (reads player_week_conversation_features)
python manage.py player-mood cj-carr-4788 --week=12

# Signature Story (reads player_value_metrics + player_season_stats)
python manage.py player-signature cj-carr-4788

# JSON mode for both
python manage.py player-mood cj-carr-4788 --json --week=12
python manage.py player-signature cj-carr-4788 --json
```

## Turning the pipeline on

Today the pipeline exists in code but is off in data. To light it up:

1. **Dry-run the tagger.** See what matches look like before writing any rows.

   ```bash
   python manage.py tag-player-mentions --season=2025 --limit=500
   ```

   Current live DB (offseason-only 4869 docs) returns ~95 matches for
   `season=2025` at `--limit=500`. Validate a sample manually before flipping.

2. **Commit the tagger.** Writes `conversation_document_targets` rows.

   ```bash
   python manage.py tag-player-mentions --season=2025 --commit
   ```

   Idempotent — re-running does not duplicate rows.

3. **Aggregate.** Roll the new row-level data into `player_week_conversation_features`.

   ```bash
   python manage.py compute-player-week-mood --week=2025-12
   ```

   No-op if no matching player-scope target rows exist for that week.

4. **Rebuild the site.** Player pages now render live `The Room` cards for
   anyone who cleared the gates. Pre-existing `#signature-story` content
   is unaffected.

   ```bash
   python manage.py build-site
   ```

5. **Verify.** Any page should be inspectable via the CLIs above, or by
   grepping the generated HTML:

   ```bash
   grep -c "the-room--empty" output/site/players/cj-carr-4788.html
   # 0 when ready-state renders; 1 when skeleton.
   ```

## Test coverage

- `tests/test_signature_story.py` — 8 tests covering QB/RB/WR fixture flows.
- `tests/test_fan_intelligence_player.py` — 6 tests for the adapter + skeleton.
- `tests/test_player_aggregate.py` — 9 tests for the aggregator (math, idempotency, round-trip).
- `tests/test_player_name_tagger.py` — 7 tests for the tagger (bounded index, disambiguation, dry-run safety).
- `tests/test_player_pipeline_integration.py` — 3 tests proving the full chain works end-to-end.

Run everything:

```bash
python -m pytest tests/test_signature_story.py tests/test_fan_intelligence_player.py \
                 tests/test_player_aggregate.py tests/test_player_name_tagger.py \
                 tests/test_player_pipeline_integration.py
```

Expect 33 player-page-data tests all passing.

## Follow-ups the build deliberately did not do

1. **Ingest CFBD `pbp_data`.** Unblocks situational Signature Story metrics
   (EPA-under-pressure, CPOE, pressure-to-sack, 3rd-down EPA, red-zone TD%)
   that the original kickoff called out but the current DB does not support.
   See `research/signature_story_data_inventory_2026-04-22.md` §10.

2. **Scheduled auto-runs.** `tag-player-mentions` and `compute-player-week-mood`
   aren't wired into any `.github/workflows/` cron — they're on-demand CLIs
   right now. Wiring them up is a one-file Actions stub plus a COMMIT
   decision (the tagger writes to a human-curated corpus).

3. **Figma Stage 2 polish.** `_render_algorithmic_signature_card` and
   `_render_the_room_card` in `reporting.py` emit minimal shells. The
   `<article class="panel …">` pattern is Figma-replaceable; data attributes
   (`data-module`, `data-state`, `data-metric-id`, `data-cohort-id`) are
   already in place for the Stage 2 handoff.

4. **Player-scope storylines.** `conversation_storylines` is team-keyed.
   Adding an `entity_type`/`entity_id` column (or a parallel
   `player_conversation_storylines` table) would give The Room a proper
   "storylines" block instead of the current empty list. Out of scope here;
   scoped for Feature B v2.

5. **Alias support.** `player_aliases` table has 0 rows. Once populated,
   extend `build_player_name_index` to index aliases alongside full names.
