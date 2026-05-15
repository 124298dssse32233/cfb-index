-- Sprint v5-1 hotfix-3: create the missing conference_themes table.
--
-- Bug context: src/cfb_rankings/team_pages/pulse_themes.py:146-172
-- (_store_conference_themes) INSERTs into conference_themes but the
-- table was never created by a migration. world_class_enrich.yml
-- run 25943290962 (2026-05-15) surfaced this as:
--   sqlite3.OperationalError: no such table: conference_themes
-- inside the "Hub — prepare pulse themes + ledes" step.
--
-- Also referenced by src/cfb_rankings/conferences_pulse/renderer.py:54
-- (_load_conference_data). The schema below matches both call sites.
--
-- Each conference produces 1-3 themes per week (3 for "full" tier
-- entities like SEC, 1 for "partial" tier like fbs-mac). Surfaced_rank
-- is the display order (1 = headline theme on conference pulse page).

CREATE TABLE IF NOT EXISTS conference_themes (
    conference_themes_id      INTEGER PRIMARY KEY,
    conference_slug           TEXT    NOT NULL,
    week_iso                  TEXT    NOT NULL,  -- YYYY-Www format from strftime
    label                     TEXT    NOT NULL,  -- 3-5 word theme title
    summary                   TEXT    NOT NULL,  -- one-sentence fan-voice description
    representative_quote      TEXT    NOT NULL,  -- verbatim excerpt, may be empty
    delta_label               TEXT,              -- optional ledge label (Δ from prior week)
    surfaced_rank             INTEGER NOT NULL DEFAULT 1,
    is_published              INTEGER NOT NULL DEFAULT 1 CHECK(is_published IN (0,1)),
    voice_validator_passed    INTEGER NOT NULL DEFAULT 1 CHECK(voice_validator_passed IN (0,1)),
    generated_at_utc          TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(conference_slug, week_iso, surfaced_rank)
);

CREATE INDEX IF NOT EXISTS idx_conference_themes_slug
    ON conference_themes(conference_slug);
CREATE INDEX IF NOT EXISTS idx_conference_themes_week
    ON conference_themes(week_iso);
