-- Chronicle Quality Proposal v3 — Visual Cache
--
-- Sidecar to chronicle_card_cache. Stores deterministic visual (SVG/PNG)
-- artifacts produced by the visuals/ package. Cache key includes
-- renderer_version + data_query_id so that a renderer bugfix or query change
-- naturally invalidates affected visuals without touching prose cards.
--
-- Cache key:
--   sha256(slug | entity_kind | season_year | week_number | visual_id |
--          data_query_id | renderer_version | data_fingerprint)[:32]
--
-- Supersession model mirrors chronicle_card_cache: when a visual is
-- regenerated, the OLD row gets superseded_at_utc set; NEW row written with
-- superseded_at_utc IS NULL.
--
-- Anti-duplication: visual_thesis_hash + chart_family + slug + season + week
-- prevents shipping two same-thesis visuals on the same surface.
--
-- Quality scoring: visual_quality_score is the weighted blend defined in
-- src/cfb_rankings/chronicle/visuals/scorer.py. Cards below
-- VISUAL_SUPPRESS_THRESHOLD (0.62) are not rendered.

BEGIN;

CREATE TABLE IF NOT EXISTS chronicle_visual_cache (
    visual_cache_key             TEXT    PRIMARY KEY,                       -- sha256(...)[:32]
    slug                         TEXT    NOT NULL,                           -- team or player slug
    entity_kind                  TEXT    NOT NULL CHECK (entity_kind IN ('player', 'team', 'conference', 'rivalry', 'league')),
    season_year                  INTEGER,
    week_number                  INTEGER,
    card_cache_key               TEXT,                                       -- optional FK to chronicle_card_cache.cache_key (NULL = standalone)
    visual_id                    TEXT    NOT NULL,                           -- 'statement_win_ladder' | 'returning_production_xray' | ...
    chart_family                 TEXT    NOT NULL,                           -- 'waterfall' | 'dot_plot' | 'tile_mosaic' | 'braid' | 'scatter'
    data_query_id                TEXT    NOT NULL,                           -- 'team_rating_deltas_v1' | ...
    visual_spec_json             TEXT    NOT NULL,                           -- VisualSpec Pydantic JSON
    visual_receipt_json          TEXT    NOT NULL,                           -- VisualReceipt: sources, sample_n, confidence, as_of
    svg_html                     TEXT,                                       -- inline SVG (Layer 1 static render)
    share_asset_path             TEXT,                                       -- relative path under output/site/_visuals/ for PNG/JPEG (Layer 1 share card)
    headline_finding             TEXT,                                       -- one-sentence chart claim (max 140 chars)
    visual_thesis_hash           TEXT,                                       -- sha256(visual_id|thesis_direction|primary_source)[:16] for anti-dup
    visual_data_fingerprint      TEXT,                                       -- sha256(canonical-JSON of query rows)[:16]
    renderer_version             TEXT    NOT NULL,                           -- bump to invalidate
    schema_version               TEXT    NOT NULL,                           -- bump to invalidate
    sample_n                     INTEGER,
    confidence_band              TEXT    CHECK (confidence_band IN ('high', 'medium', 'low', 'unset')),
    visual_quality_score         REAL,                                       -- 0..1 blended score
    clarity_score                REAL,
    fan_relevance_score          REAL,
    data_depth_score             REAL,
    novelty_score                REAL,
    mobile_legibility_score      REAL,
    screenshot_value_score       REAL,
    evidence_strength_score      REAL,
    voice_fit_score              REAL,
    suppressed                   INTEGER NOT NULL DEFAULT 0,                 -- 1 = below threshold, do not render
    suppression_reason           TEXT,
    is_lkg                       INTEGER NOT NULL DEFAULT 0,                 -- 1 = Last-Known-Good fallback
    lkg_promoted_at_utc          TEXT,
    wall_clock_ms                INTEGER,
    created_at_utc               TEXT    NOT NULL DEFAULT (datetime('now')),
    superseded_at_utc            TEXT                                        -- NULL = current
);

CREATE INDEX IF NOT EXISTS idx_chronicle_visual_cache_active
    ON chronicle_visual_cache (slug, season_year, week_number, visual_id, superseded_at_utc);

CREATE INDEX IF NOT EXISTS idx_chronicle_visual_cache_lkg
    ON chronicle_visual_cache (entity_kind, is_lkg);

CREATE INDEX IF NOT EXISTS idx_chronicle_visual_cache_family
    ON chronicle_visual_cache (chart_family, created_at_utc);

CREATE INDEX IF NOT EXISTS idx_chronicle_visual_cache_card_link
    ON chronicle_visual_cache (card_cache_key);

CREATE INDEX IF NOT EXISTS idx_chronicle_visual_cache_thesis
    ON chronicle_visual_cache (slug, season_year, visual_thesis_hash);

COMMIT;

-- VERIFY: SELECT name FROM sqlite_master WHERE type='table' AND name='chronicle_visual_cache';
