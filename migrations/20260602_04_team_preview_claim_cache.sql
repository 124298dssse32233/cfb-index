-- Team Preview — Claim cache (evidence-backed preview prose)
-- Spec: docs/specs/team-preview-implementation-plan-2026-05-26.md §1.6
--
-- NOT a source of truth. This caches LLM-synthesised preview snippets that are
-- each tied to a deterministic evidence bundle (evidence_hash) and gated by
-- validator scores. It mirrors the Chronicle card-cache supersession/LKG model
-- (migration 20260524_03) but stays in its own table so preview claims never
-- mingle with generic Chronicle rows. Milestone A creates the table empty;
-- Milestone D (local-LLM synthesis) populates it. The column contract is
-- locked here so downstream renderers can query a stable shape.
--
-- Supersession: regenerating a claim sets superseded_at_utc on the old row and
-- inserts a new row with superseded_at_utc IS NULL.
-- LKG: the most recent is_lkg=1 row for (slug, surface, claim_type) is served
-- when a fresh generation fails its gates.

CREATE TABLE IF NOT EXISTS team_preview_claim_cache (
    claim_key                  TEXT    PRIMARY KEY,              -- sha256(...)[:32]
    team_id                    INTEGER REFERENCES teams(team_id),
    slug                       TEXT    NOT NULL,
    season_year                INTEGER,
    as_of_date                 TEXT    NOT NULL,
    surface                    TEXT    NOT NULL,                 -- 'preview_thesis' | 'reload_summary' | 'schedule_leverage' | ...
    claim_type                 TEXT    NOT NULL,
    claim_text                 TEXT    NOT NULL,
    evidence_json              TEXT    NOT NULL DEFAULT '[]',
    evidence_hash              TEXT    NOT NULL,
    prompt_template_id         TEXT,
    model_id                   TEXT,
    model_backend              TEXT,                             -- 'ollama' | 'llama_server' | 'anthropic' | 'null'
    voice_score                REAL,
    fact_score                 REAL,
    slop_score                 REAL,
    confidence_band            TEXT    NOT NULL DEFAULT 'unset'
        CHECK (confidence_band IN ('high', 'medium', 'low', 'unset')),
    approved                   INTEGER NOT NULL DEFAULT 0,
    is_lkg                     INTEGER NOT NULL DEFAULT 0,
    created_at_utc             TEXT    NOT NULL DEFAULT (datetime('now')),
    superseded_at_utc          TEXT                              -- null = current
);

CREATE INDEX IF NOT EXISTS idx_team_preview_claim_cache_active
    ON team_preview_claim_cache (slug, season_year, as_of_date, surface, superseded_at_utc);

CREATE INDEX IF NOT EXISTS idx_team_preview_claim_cache_lkg
    ON team_preview_claim_cache (slug, surface, claim_type, is_lkg);

CREATE INDEX IF NOT EXISTS idx_team_preview_claim_cache_evidence
    ON team_preview_claim_cache (evidence_hash);
