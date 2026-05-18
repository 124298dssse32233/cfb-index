-- Receipt pattern foundation (Sprint v5-6a.5)
-- Locked spec: docs/design-system/32-receipt-pattern.md
--
-- Stores citation receipts for Pattern C/D generations. Each [N] marker
-- in body_markdown gets one row keyed by (generation_id, marker_id).
-- Read by `cfb_rankings.citations.render` when emitting the citation
-- footer + inline superscript markers.
-- (Module renamed from `receipts` to `citations` to avoid collision
-- with Sprint 13's predictive-claim `cfb_rankings.receipts` package.)

CREATE TABLE IF NOT EXISTS editorial_citations (
    citation_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    generation_id   INTEGER NOT NULL,
    marker_id       INTEGER NOT NULL,
    source_kind     TEXT NOT NULL CHECK (source_kind IN (
        'reddit', 'beat_writer', 'podcast', 'wikipedia',
        'official', 'cfbd', 'wire', 'edition'
    )),
    source_url      TEXT,
    source_label    TEXT NOT NULL,
    source_date     TEXT,
    confidence      TEXT NOT NULL CHECK (confidence IN (
        'primary', 'supporting', 'background'
    )),
    created_at_utc  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (generation_id, marker_id)
);

CREATE INDEX IF NOT EXISTS idx_editorial_citations_generation
    ON editorial_citations(generation_id);

CREATE INDEX IF NOT EXISTS idx_editorial_citations_source_kind
    ON editorial_citations(source_kind);

CREATE INDEX IF NOT EXISTS idx_editorial_citations_source_date
    ON editorial_citations(source_date);
