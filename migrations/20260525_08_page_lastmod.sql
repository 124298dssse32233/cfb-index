-- Sprint v5-1 Day 3 — Per-page last-modified tracking.
-- Spec: IMPLEMENTATION_PLAN.md Part 4 Day 3; DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Correction #8 (#8 of 15).
--
-- Feeds the sitemap.xml <lastmod> field and the "Updated YYYY-MM-DD"
-- timestamp the renderer drops into each page. Renderer modules write
-- one row per emitted HTML path on every build. content_hash lets us tell
-- a "re-render that produced identical bytes" from a "real content
-- change"; sitemap only bumps lastmod_utc when the hash changes.

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS page_lastmod (
    page_path TEXT PRIMARY KEY,                      -- e.g. '/programs/alabama.html'
    content_hash TEXT NOT NULL,                      -- sha256 of rendered HTML
    lastmod_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_rendered_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    render_count INTEGER NOT NULL DEFAULT 1,
    surface TEXT,                                    -- 'team_page','edition','daily', etc
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_page_lastmod_modified
    ON page_lastmod (lastmod_utc DESC);

CREATE INDEX IF NOT EXISTS idx_page_lastmod_surface
    ON page_lastmod (surface, lastmod_utc DESC);

COMMIT;
