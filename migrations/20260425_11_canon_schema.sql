-- Sprint 11 — The Canon v1
-- Three canonical lists (players, games, coaching hires) with editorial entries,
-- cohort-divergence data, and year-over-year revision history.
--
-- Tables are disjoint from team_pages, editions, storylines, wire, receipts
-- (Wave 2 file-ownership boundary).

CREATE TABLE IF NOT EXISTS canon_lists (
    list_slug             TEXT PRIMARY KEY,
    title                 TEXT NOT NULL,
    edition_year          INTEGER NOT NULL,
    list_kind             TEXT NOT NULL CHECK(list_kind IN (
        'players','games','coaching_hires','programs','seasons','plays','traditions'
    )),
    description           TEXT NOT NULL,
    methodology_notes     TEXT,
    entry_count           INTEGER NOT NULL,
    published_at          DATETIME,
    next_revision_year    INTEGER
);

CREATE TABLE IF NOT EXISTS canon_entries (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    list_slug                   TEXT NOT NULL REFERENCES canon_lists(list_slug),
    rank                        INTEGER NOT NULL,
    entity_kind                 TEXT NOT NULL CHECK(entity_kind IN (
        'player','game','coaching_hire','program'
    )),
    entity_slug                 TEXT NOT NULL,
    entity_display_name         TEXT NOT NULL,
    program_slug                TEXT,
    program_label               TEXT,
    era_label                   TEXT,
    summary_short               TEXT NOT NULL,
    editorial_paragraph         TEXT,
    statline                    TEXT,
    cohort_split_stat_rank      INTEGER,
    cohort_split_casual_rank    INTEGER,
    cohort_split_label          TEXT,
    prior_year_rank             INTEGER,
    rank_delta_label            TEXT,
    UNIQUE(list_slug, rank)
);

CREATE INDEX IF NOT EXISTS idx_canon_entries_list_rank
    ON canon_entries(list_slug, rank);

CREATE INDEX IF NOT EXISTS idx_canon_entries_program
    ON canon_entries(program_slug)
    WHERE program_slug IS NOT NULL;

CREATE TABLE IF NOT EXISTS canon_revision_history (
    list_slug      TEXT NOT NULL,
    edition_year   INTEGER NOT NULL,
    entity_slug    TEXT NOT NULL,
    rank_in_year   INTEGER NOT NULL,
    PRIMARY KEY (list_slug, edition_year, entity_slug)
);
