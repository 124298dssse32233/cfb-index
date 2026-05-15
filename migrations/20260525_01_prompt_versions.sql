-- Sprint v5-1 Day 3 — Prompt template versioning.
-- Spec: IMPLEMENTATION_PLAN.md Part 4 Day 3; DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Correction #8 (#1 of 15).
--
-- Stores the versioned-prompt registry that backs llm_runtime.py prompt
-- caching and the quality_loop critics. One row per (surface, version),
-- with the prompt body, model_id binding, and rollout state. The currently
-- active prompt for a surface is the most-recent row with status='active'.
--
-- Skipped on subsequent runs once recorded in schema_migrations (see
-- src/cfb_rankings/migrations.py:apply_sql_migrations).

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    surface TEXT NOT NULL,                          -- e.g. 'edition_cover_essay', 'daily_lead', 'chronicle'
    version TEXT NOT NULL,                          -- semver-ish, e.g. '1.0.0'
    template_md TEXT NOT NULL,                      -- the full prompt body (markdown)
    model_id TEXT NOT NULL,                         -- model the template was authored against
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'draft', 'deprecated', 'retired')),
    author TEXT,                                    -- 'human' | 'claude' | model_id
    notes TEXT,                                     -- changelog / rationale
    created_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activated_at_utc TEXT,                          -- when status flipped to 'active'
    deprecated_at_utc TEXT,
    UNIQUE (surface, version)
);

CREATE INDEX IF NOT EXISTS idx_prompt_versions_surface_status
    ON prompt_versions (surface, status);

CREATE INDEX IF NOT EXISTS idx_prompt_versions_active
    ON prompt_versions (surface, activated_at_utc DESC)
    WHERE status = 'active';

COMMIT;
