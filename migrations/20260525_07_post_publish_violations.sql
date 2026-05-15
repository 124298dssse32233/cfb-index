-- Sprint v5-1 Day 3 — Post-publish HTML audit findings.
-- Spec: IMPLEMENTATION_PLAN.md Part 4 Day 3; DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Correction #8 (#7 of 15).
--
-- After site-deploy completes the v5-11 polish sprint runs a post-publish
-- HTML audit (broken-link sweep, missing assets, schema.org validation,
-- voice-validator regression). Each finding is one row. The /admin queue
-- page reads severity='blocker' rows and surfaces them. Findings can be
-- marked resolved=1 once fixed so a re-run de-dupes naturally.

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS post_publish_violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,                            -- audit invocation id (uuid / iso ts)
    page_path TEXT NOT NULL,                         -- e.g. '/teams/alabama.html'
    rule TEXT NOT NULL,                              -- e.g. 'broken_link', 'missing_og_image'
    severity TEXT NOT NULL DEFAULT 'warning'
        CHECK (severity IN ('info','warning','error','blocker')),
    detail TEXT,                                     -- human-readable explanation
    context_json TEXT,                               -- rule-specific payload (links, selectors)
    detected_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved INTEGER NOT NULL DEFAULT 0,
    resolved_at_utc TEXT,
    resolved_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_post_publish_violations_run
    ON post_publish_violations (run_id, severity);

CREATE INDEX IF NOT EXISTS idx_post_publish_violations_unresolved
    ON post_publish_violations (severity, detected_at_utc DESC)
    WHERE resolved = 0;

CREATE INDEX IF NOT EXISTS idx_post_publish_violations_page
    ON post_publish_violations (page_path, detected_at_utc DESC);

COMMIT;
