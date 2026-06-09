-- Chronicle: Banlist
-- CFB-specific and generic-AI-slop phrases. Severity is a logit-bias multiplier:
-- 0.5 = use sparingly (soft nudge against), 1.0 = standard ban (default),
-- 5.0 = hard ban (effectively forbidden in generation).
--
-- Source kinds (added_by):
--   * voice_validator_seed     — initial seed below
--   * manual_curation_YYYYwNN  — weekly editor adds
--   * drift_detection          — auto-flagged by chronicle_slop_observations
--
-- Query: WHERE is_active=1 (most callers) — index optimises that path.

BEGIN;

CREATE TABLE IF NOT EXISTS chronicle_banlist (
    phrase_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase           TEXT    NOT NULL UNIQUE,
    kind             TEXT    NOT NULL CHECK (kind IN ('cliche', 'cfb_specific', 'ai_slop', 'coach_speak', 'engagement_bait')),
    severity         REAL    NOT NULL DEFAULT 1.0,
    is_active        INTEGER NOT NULL DEFAULT 1,
    added_by         TEXT,
    created_at_utc   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_chronicle_banlist_active_kind
    ON chronicle_banlist (is_active, kind);

-- ----------------------------------------------------------------------------
-- Seed inserts (voice_validator_seed). Use INSERT OR IGNORE to keep idempotent.
-- ----------------------------------------------------------------------------

-- CFB-specific slop (5)
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('showed out', 'cfb_specific', 2.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('balling out', 'cfb_specific', 2.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('cooking', 'cfb_specific', 1.5, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('cooked', 'cfb_specific', 1.5, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('different breed', 'cfb_specific', 2.0, 'voice_validator_seed');

-- Cliches (15)
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('took the league by storm', 'cliche', 3.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('exploded onto the scene', 'cliche', 3.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('burst onto the scene', 'cliche', 3.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('find a way', 'cliche', 2.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('find ways to win', 'cliche', 2.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('do what it takes', 'cliche', 2.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('statement win', 'cliche', 1.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('hostile environment', 'cliche', 2.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('quietly putting together', 'cliche', 3.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('quietly elite', 'cliche', 3.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('under the radar', 'cliche', 3.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('has all the tools', 'cliche', 3.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('all the tools in the toolbox', 'cliche', 4.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('bend but don''t break', 'cliche', 3.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('punch in the mouth', 'cliche', 2.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('control their own destiny', 'cliche', 2.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('one game at a time', 'cliche', 3.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('gut-check moment', 'cliche', 2.0, 'voice_validator_seed');

-- Coach-speak (6)
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('true student of the game', 'coach_speak', 3.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('high football IQ', 'coach_speak', 2.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('great kid', 'coach_speak', 3.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('high-character kid', 'coach_speak', 3.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('motor never stops', 'coach_speak', 2.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('does all the little things right', 'coach_speak', 3.0, 'voice_validator_seed');

-- AI slop (15)
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('delve', 'ai_slop', 5.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('tapestry', 'ai_slop', 5.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('navigate the landscape', 'ai_slop', 5.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('testament to', 'ai_slop', 4.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('amongst', 'ai_slop', 3.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('myriad', 'ai_slop', 4.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('in terms of', 'ai_slop', 3.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('at the end of the day', 'ai_slop', 4.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('in a season full of', 'ai_slop', 4.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('when you think of', 'ai_slop', 4.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('it''s no secret that', 'ai_slop', 4.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('make no mistake', 'ai_slop', 4.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('it goes without saying', 'ai_slop', 4.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('in the realm of', 'ai_slop', 5.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('a symphony of', 'ai_slop', 5.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('paints a picture', 'ai_slop', 4.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('speaks volumes', 'ai_slop', 4.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('the perfect storm', 'ai_slop', 3.0, 'voice_validator_seed');

-- Engagement bait (8)
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('🚨', 'engagement_bait', 5.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('🔥🔥🔥', 'engagement_bait', 5.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('RT if you agree', 'engagement_bait', 5.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('Who ya got?', 'engagement_bait', 5.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('Buckle up', 'engagement_bait', 4.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('You won''t believe', 'engagement_bait', 5.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('Let that sink in', 'engagement_bait', 5.0, 'voice_validator_seed');
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('Wait for it', 'engagement_bait', 4.0, 'voice_validator_seed');

-- Soft-flag (severity 0.5 — use sparingly, not banned)
INSERT OR IGNORE INTO chronicle_banlist (phrase, kind, severity, added_by) VALUES ('dual-threat', 'cliche', 0.5, 'voice_validator_seed');

COMMIT;

-- VERIFY: SELECT count(*) AS seeded_phrases FROM chronicle_banlist WHERE added_by='voice_validator_seed';
