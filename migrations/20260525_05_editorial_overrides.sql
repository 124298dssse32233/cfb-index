-- Sprint v5-1 Day 3 — Editorial overrides ledger.
-- Spec: IMPLEMENTATION_PLAN.md Part 4 Day 3; DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Correction #8 (#5 of 15).
--
-- Surface-agnostic record of editorial decisions applied on top of the
-- automated pipeline. Writers from:
--   * /admin/queue/ approvals + rejections (human)
--   * digest_reactions_poll.yml pulling GitHub Issue comment reactions
--     (auto, source='reaction_poll')
--   * auto-promote-storyline-drafts (auto, source='auto_promote')
--
-- Readers: renderer modules consult this table before publishing a surface.
-- An (surface, slug, override_kind) triple resolves to the most-recent row.

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS editorial_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    surface TEXT NOT NULL,                          -- e.g. 'edition', 'storyline', 'chronicle', 'wire'
    slug TEXT NOT NULL,                             -- entity slug within the surface
    override_kind TEXT NOT NULL                     -- 'approve','reject','promote','demote','hide','pin','swap','annotate'
        CHECK (override_kind IN (
            'approve','reject','promote','demote','hide','pin','swap','annotate'
        )),
    source TEXT NOT NULL                            -- 'human','reaction_poll','auto_promote','quality_loop'
        CHECK (source IN ('human','reaction_poll','auto_promote','quality_loop','migration_v5_1')),
    actor TEXT,                                     -- github_handle / 'system' / model_id
    payload_json TEXT,                              -- override-kind-specific details
    notes TEXT,
    applied_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_editorial_overrides_surface_slug
    ON editorial_overrides (surface, slug, applied_at_utc DESC);

CREATE INDEX IF NOT EXISTS idx_editorial_overrides_kind
    ON editorial_overrides (override_kind, applied_at_utc DESC);

CREATE INDEX IF NOT EXISTS idx_editorial_overrides_source
    ON editorial_overrides (source, applied_at_utc DESC);

COMMIT;
