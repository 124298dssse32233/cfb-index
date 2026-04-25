-- Sprint 13: Receipts + The Long-Shot That Hit infrastructure.
-- New tables for predictive-claim tracking, historical consensus snapshots,
-- and per-source receipt profiles.
--
-- Design notes:
--   * Extends the existing fan-intel corpus rather than replacing it.
--     `conversation_documents` (~180k rows) is the upstream source the
--     extractor scans. We keep a foreign-key reference into that table when
--     the claim is harvested from a corpus document.
--   * Historical consensus snapshots cover last 12 years (CFP era, 2014-2025).
--     For Vegas lines we lean on the existing `game_lines` table when game-
--     scoped consensus is needed; this table is for season-level / market-level
--     consensus (win-totals, preseason ranks, CFP odds).
--   * `source_profiles` is a sidecar to `source_registry` — we don't duplicate
--     metadata, just receipts-relevant scoring + display fields.

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS predictive_claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_kind TEXT NOT NULL CHECK(source_kind IN (
        'beat_writer','podcast','board_post','reddit','bluesky',
        'official_release','our_chronicle','our_canon'
    )),
    source_slug TEXT NOT NULL,
    source_url TEXT,
    source_published_at DATETIME NOT NULL,
    -- Optional FK back to the corpus document the claim was extracted from.
    -- Null when the claim is hand-seeded or originates from our_chronicle/canon.
    conversation_document_id INTEGER,
    claim_text TEXT NOT NULL,
    claim_summary_short TEXT NOT NULL,
    entities_mentioned_json TEXT NOT NULL,  -- {"programs":[],"players":[],"coaches":[],"conferences":[]}
    outcome_window_start DATE NOT NULL,
    outcome_window_end DATE NOT NULL,
    prediction_kind TEXT NOT NULL CHECK(prediction_kind IN (
        'record','game','recruit','coaching_change','portal',
        'award','rank','title','playoff_bid','other'
    )),
    confidence_in_extraction REAL NOT NULL,
    surprise_index REAL,
    surprise_index_components_json TEXT,
    outcome_resolved BOOLEAN NOT NULL DEFAULT 0,
    outcome_text TEXT,
    outcome_verdict TEXT CHECK(outcome_verdict IN ('hit','miss','partial','unresolvable')),
    outcome_resolved_at DATETIME,
    aged_well_pct REAL,
    -- Provenance / model routing trace
    extractor_model TEXT,
    extractor_pass TEXT,           -- 'haiku_initial' | 'sonnet_review' | 'manual_seed'
    review_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_document_id) REFERENCES conversation_documents(conversation_document_id)
);

CREATE INDEX IF NOT EXISTS idx_pc_source
    ON predictive_claims(source_kind, source_slug, source_published_at DESC);
CREATE INDEX IF NOT EXISTS idx_pc_resolved
    ON predictive_claims(outcome_resolved, outcome_resolved_at DESC);
CREATE INDEX IF NOT EXISTS idx_pc_surprise
    ON predictive_claims(surprise_index DESC);
CREATE INDEX IF NOT EXISTS idx_pc_kind_window
    ON predictive_claims(prediction_kind, outcome_window_end);
CREATE INDEX IF NOT EXISTS idx_pc_doc
    ON predictive_claims(conversation_document_id);

CREATE TABLE IF NOT EXISTS historical_consensus_snapshots (
    snapshot_date DATE NOT NULL,
    consensus_kind TEXT NOT NULL CHECK(consensus_kind IN (
        'vegas_line','ap_poll','coaches_poll','sp_plus_projection',
        'kalshi_market','polymarket_market','corpus_aggregate'
    )),
    entity_kind TEXT NOT NULL,                -- 'team' | 'game' | 'conference'
    entity_slug TEXT NOT NULL,
    metric TEXT NOT NULL,                     -- 'season_win_total' | 'game_spread' | 'preseason_rank' | 'cfp_odds'
    metric_value REAL NOT NULL,
    metric_implied_probability REAL,
    sample_size INTEGER,
    season_year INTEGER,
    week INTEGER,
    source_provider TEXT,                      -- 'cfbd' | 'kalshi' | 'polymarket' | 'corpus'
    raw_payload_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (snapshot_date, consensus_kind, entity_kind, entity_slug, metric)
);

CREATE INDEX IF NOT EXISTS idx_hcs_lookup
    ON historical_consensus_snapshots(entity_slug, snapshot_date, metric);
CREATE INDEX IF NOT EXISTS idx_hcs_kind
    ON historical_consensus_snapshots(consensus_kind, season_year, week);

CREATE TABLE IF NOT EXISTS source_profiles (
    source_slug TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    role_label TEXT,                          -- e.g. "THE ATHLETIC · NATIONAL"
    bio TEXT,
    receipt_score_pct REAL,
    receipt_score_label TEXT,
    takes_tracked INTEGER NOT NULL DEFAULT 0,
    takes_resolved INTEGER NOT NULL DEFAULT 0,
    takes_hit INTEGER NOT NULL DEFAULT 0,
    takes_miss INTEGER NOT NULL DEFAULT 0,
    takes_partial INTEGER NOT NULL DEFAULT 0,
    last_take_at DATETIME,
    cohort_lean TEXT,                         -- 'stat-leaning' | 'casual-leaning' | 'balanced'
    program_focus_slugs_json TEXT,
    voice_summary TEXT,                        -- 1-paragraph editorial characterization
    longest_long_shot_id INTEGER,              -- highest surprise_index hit, FK to predictive_claims
    most_aged_poorly_id INTEGER,
    profile_published BOOLEAN NOT NULL DEFAULT 0,
    last_recomputed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (longest_long_shot_id) REFERENCES predictive_claims(id),
    FOREIGN KEY (most_aged_poorly_id) REFERENCES predictive_claims(id)
);

CREATE INDEX IF NOT EXISTS idx_sp_score
    ON source_profiles(receipt_score_pct DESC);

-- Annual canonical lists ("The 25 Best Calls of <year>")
CREATE TABLE IF NOT EXISTS receipts_annual_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_year INTEGER NOT NULL,
    list_kind TEXT NOT NULL CHECK(list_kind IN ('best_calls','aged_poorly','vindicated','dark_horses')),
    rank INTEGER NOT NULL,
    claim_id INTEGER NOT NULL,
    editorial_title TEXT NOT NULL,
    editorial_paragraph TEXT NOT NULL,
    editorial_pull_quote TEXT,
    editorial_model TEXT,                       -- 'sonnet' | 'opus'
    voice_validator_passed BOOLEAN NOT NULL DEFAULT 0,
    voice_validator_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (season_year, list_kind, rank),
    FOREIGN KEY (claim_id) REFERENCES predictive_claims(id)
);

CREATE INDEX IF NOT EXISTS idx_ral_season_kind
    ON receipts_annual_lists(season_year, list_kind, rank);

-- Bookkeeping for the extraction pipeline so we can resume / audit.
CREATE TABLE IF NOT EXISTS predictive_extraction_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME,
    pass_kind TEXT NOT NULL,                    -- 'haiku_initial' | 'sonnet_review'
    days_window INTEGER,
    sources_filter TEXT,
    documents_scanned INTEGER NOT NULL DEFAULT 0,
    claims_extracted INTEGER NOT NULL DEFAULT 0,
    claims_promoted INTEGER NOT NULL DEFAULT 0,
    claims_dropped INTEGER NOT NULL DEFAULT 0,
    haiku_input_tokens INTEGER NOT NULL DEFAULT 0,
    haiku_output_tokens INTEGER NOT NULL DEFAULT 0,
    sonnet_input_tokens INTEGER NOT NULL DEFAULT 0,
    sonnet_output_tokens INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);

INSERT INTO schema_migrations (migration_id, applied_at_utc, note)
VALUES ('20260425_13_receipts_schema.sql', CURRENT_TIMESTAMP, 'sprint 13 receipts')
ON CONFLICT(migration_id) DO NOTHING;

COMMIT;
