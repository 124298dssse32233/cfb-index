-- Sprint v5-1 Day 3 — Reddit archive tables (3 tables in one migration).
-- Spec: IMPLEMENTATION_PLAN.md Part 4 Day 3; DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md Correction #8 (#9 of 15).
--
-- Powers v5-10d Reddit-archive surfaces (S5 "Today in CFB History",
-- S7 "Saturdays Past") via the Arctic Shift adapter at
-- src/cfb_rankings/ingest/sources/archive_retro.py.
--
-- Three tables, deliberately denormalized to keep retro queries trivial:
--   * archive_threads      — high-engagement r/CFB submissions, deduped on (subreddit, external_id)
--   * archive_comments     — top comments per archive_thread for color
--   * archive_term_weekly  — week-rolled term frequency for "What fans were saying" charts

BEGIN TRANSACTION;

-- ------------------------------------------------------------------
-- archive_threads: per-thread snapshot from r/CFB and r/cfb.
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS archive_threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subreddit TEXT NOT NULL,
    external_id TEXT NOT NULL,                       -- Reddit submission id, e.g. 't3_xxxxxx'
    title TEXT NOT NULL,
    body_md TEXT,
    permalink TEXT,
    author TEXT,                                     -- redactable handle; may be '[deleted]'
    created_utc TEXT NOT NULL,                       -- thread creation time
    fetched_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    score INTEGER,
    num_comments INTEGER,
    upvote_ratio REAL,
    flair TEXT,
    is_self INTEGER,                                 -- 1 = self-post, 0 = link
    link_url TEXT,
    over_18 INTEGER NOT NULL DEFAULT 0,
    locked INTEGER NOT NULL DEFAULT 0,
    iso_date TEXT NOT NULL,                          -- YYYY-MM-DD of created_utc (for MM-DD lookup)
    iso_mm_dd TEXT NOT NULL,                         -- MM-DD slice for "Today in CFB History"
    season_year INTEGER,                             -- nullable; null in offseason
    UNIQUE (subreddit, external_id)
);

CREATE INDEX IF NOT EXISTS idx_archive_threads_mm_dd
    ON archive_threads (iso_mm_dd, score DESC);

CREATE INDEX IF NOT EXISTS idx_archive_threads_date
    ON archive_threads (iso_date DESC);

CREATE INDEX IF NOT EXISTS idx_archive_threads_score
    ON archive_threads (score DESC, num_comments DESC);

-- ------------------------------------------------------------------
-- archive_comments: top comments per archive thread for editorial color.
-- Only top-N (typically 10) per thread to keep DB compact.
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS archive_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    archive_thread_id INTEGER NOT NULL REFERENCES archive_threads(id),
    external_id TEXT NOT NULL,                       -- Reddit comment id
    parent_external_id TEXT,                         -- parent comment id (null = top-level)
    author TEXT,
    body_md TEXT NOT NULL,
    created_utc TEXT NOT NULL,
    fetched_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    score INTEGER,
    is_top_level INTEGER NOT NULL DEFAULT 0,
    rank_in_thread INTEGER,                          -- 1..N by score
    UNIQUE (archive_thread_id, external_id)
);

CREATE INDEX IF NOT EXISTS idx_archive_comments_thread
    ON archive_comments (archive_thread_id, rank_in_thread);

CREATE INDEX IF NOT EXISTS idx_archive_comments_top
    ON archive_comments (archive_thread_id, score DESC)
    WHERE is_top_level = 1;

-- ------------------------------------------------------------------
-- archive_term_weekly: week-rolled term frequency. Powers "what fans
-- were saying" minicharts on retro pages. window_start_utc is the
-- ISO date of the Monday of the rolled week.
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS archive_term_weekly (
    window_start_utc TEXT NOT NULL,                  -- YYYY-MM-DD, Monday-anchored
    season_year INTEGER,                             -- nullable; null = year-agnostic rollup
    term TEXT NOT NULL,
    cohort TEXT NOT NULL DEFAULT 'all',              -- 'all' | 'rcfb' | per-team cohort
    doc_count INTEGER NOT NULL DEFAULT 0,            -- number of threads/comments matched
    term_count INTEGER NOT NULL DEFAULT 0,           -- total occurrences in window
    sentiment_mean REAL,                             -- -1..+1 mean, optional
    notes TEXT,
    computed_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (window_start_utc, cohort, term)
);

CREATE INDEX IF NOT EXISTS idx_archive_term_weekly_term
    ON archive_term_weekly (term, window_start_utc DESC);

CREATE INDEX IF NOT EXISTS idx_archive_term_weekly_window
    ON archive_term_weekly (window_start_utc DESC, term_count DESC);

COMMIT;
