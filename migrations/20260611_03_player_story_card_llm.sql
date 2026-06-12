-- Player Story Card — additive LLM-narrator columns (Phase 2).
-- Extends migration 20260611_02's player_story_card_cache with the metadata the
-- confident-compiler narrator + LKG logic need. ADDITIVE ONLY: no existing
-- column/data is altered. PK stays (player_external_id, season_year), so the
-- single row per player-season IS the Last-Known-Good (no multi-row promotion).
--
-- Recorded once in schema_migrations by the runner (src/cfb_rankings/migrations.py
-- apply_sql_migrations), so these one-shot ALTER TABLE ADD COLUMN statements run
-- exactly once and are skipped on every subsequent run (the v5-1+ rule that
-- column additions may live in .sql files). Columns:
--   is_lkg               1 = this row is the last-known-good narration to serve.
--   lkg_promoted_at_utc  when is_lkg was last set.
--   fallback_reason      which path produced this row ('llm prose' | 'lkg ...' | 'deterministic ...').
--   prose_source         'llm' | 'lkg' | 'deterministic' (the overlay gate in build_card_payload).
--   eval_factscore       heuristic FActScore support_rate of the shipped prose.
--   eval_slop            slop fingerprint of the shipped prose (NULL until scored).
ALTER TABLE player_story_card_cache ADD COLUMN is_lkg INTEGER NOT NULL DEFAULT 0;
ALTER TABLE player_story_card_cache ADD COLUMN lkg_promoted_at_utc TEXT;
ALTER TABLE player_story_card_cache ADD COLUMN fallback_reason TEXT;
ALTER TABLE player_story_card_cache ADD COLUMN prose_source TEXT;
ALTER TABLE player_story_card_cache ADD COLUMN eval_factscore REAL;
ALTER TABLE player_story_card_cache ADD COLUMN eval_slop REAL;
