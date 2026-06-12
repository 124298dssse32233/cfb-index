-- Player Story Card ("Dossier Noir") — persistent narrative state + deterministic detectors.
-- Specs: docs/design-system/41..49. ALL tables key on player_external_id (TEXT) =
-- player_source_ids.source_player_id WHERE source_name='cfbd' (the stable CFBD athlete id;
-- the linkrot anchor per src/cfb_rankings/player_id_anchor.py). NOTE: roster_entries.external_id
-- referenced in doc 46 / the archetype migration comment DOES NOT EXIST — resolve via player_source_ids.
-- Idempotent + re-runnable (CREATE TABLE IF NOT EXISTS). Narrative archetypes reuse
-- player_archetype_tags (namespaced archetype_slug 'narr:*') — no new archetype table.
BEGIN TRANSACTION;

-- ---------------------------------------------------------------------------
-- narrative_beats — NEL output (doc 42 §3,§4,§12). One row per detected beat.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS narrative_beats (
    narrative_beat_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    player_external_id       TEXT    NOT NULL,                 -- cfbd id (stable anchor)
    player_id                INTEGER,                          -- convenience denorm (current-DB only)
    season_year              INTEGER NOT NULL,
    week                     INTEGER,                          -- NULL = season/career-grain beat
    beat_type                TEXT    NOT NULL,                 -- 'transfer_controversy','role_lost','collapse','award',...
    register                 TEXT    NOT NULL DEFAULT 'current' -- 'permanent' | 'current' (doc 42 §4 two registers)
        CHECK (register IN ('permanent','current')),
    summary                  TEXT    NOT NULL,                 -- deterministic templated one-liner
    framing                  TEXT    NOT NULL DEFAULT 'fact'   -- 'fact' | 'attributed' | 'inference' (doc 42 §1)
        CHECK (framing IN ('fact','attributed','inference')),
    source_plane             TEXT    NOT NULL DEFAULT 'structured' -- 'structured'|'discourse'|'canon'
        CHECK (source_plane IN ('structured','discourse','canon')),
    valence                  REAL,                             -- -1..1 (encoder sentiment), NULL if structural
    -- five orthogonal salience axes (doc 42 §4) — stored, never collapsed
    career_impact            REAL    NOT NULL DEFAULT 0.0,
    current_relevance        REAL    NOT NULL DEFAULT 0.0,
    narrative_distinctiveness REAL   NOT NULL DEFAULT 0.0,
    discourse_intensity      REAL    NOT NULL DEFAULT 0.0,
    confidence               REAL    NOT NULL DEFAULT 0.0,     -- meta-claim reliability
    is_inflection            INTEGER NOT NULL DEFAULT 0,       -- drives chapter/logline lock (doc 41 §7)
    ledger                   TEXT,                             -- hope|grievance|belonging|judgment|grudge|NULL
    evidence_json            TEXT,                             -- {rows:[],doc_ids:[],quotes:[],canon_urls:[]}
    superseded_by_beat_id    INTEGER,                          -- correction/supersession (doc 42 §7); NULL=live
    computed_at_utc          TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (player_external_id, season_year, week, beat_type)
);
CREATE INDEX IF NOT EXISTS idx_nb_player_season
    ON narrative_beats (player_external_id, season_year, register, career_impact DESC);
CREATE INDEX IF NOT EXISTS idx_nb_latest
    ON narrative_beats (season_year, week);

-- ---------------------------------------------------------------------------
-- player_bible — persistent per-player evolving canon (doc 42 §7). One row/player.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_bible (
    player_external_id       TEXT    PRIMARY KEY,              -- one bible per player (stable anchor)
    player_id                INTEGER,
    season_year              INTEGER NOT NULL,                 -- current season the bible reflects
    identity_json            TEXT,                             -- {name,team,pos,class,jersey,team_color}
    permanent_beats_json     TEXT,                             -- ordered permanent register (beat ids/payload)
    current_beats_json       TEXT,                             -- decaying current-arc register
    canon_events_json        TEXT,                             -- career inflections w/ supersession
    arc_state_json           TEXT,                             -- {chapter,chapter_label,tensions[],trajectory}
    archetype_slug           TEXT,                             -- 'narr:transfer-saga' etc (mirrors archetype_tags)
    logline                  TEXT,                             -- stable; changes only on new inflection
    logline_locked_event_id  INTEGER,                          -- the inflection that set the current logline
    why_now                  TEXT,                             -- the heartbeat (changes most; doc 43 §6)
    data_coverage_flag       TEXT    NOT NULL DEFAULT 'no_data' -- 'narrative'|'no_story'|'no_data' (doc 42 §10)
        CHECK (data_coverage_flag IN ('narrative','no_story','no_data')),
    content_hash             TEXT,                             -- regen short-circuit (signature_story pattern)
    updated_at_utc           TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- player_bible_snapshots — the changelog / emotional EKG (doc 42 §7, doc 43 §6).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_bible_snapshots (
    player_bible_snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_external_id       TEXT    NOT NULL,
    season_year              INTEGER NOT NULL,
    week                     INTEGER,
    as_of_date               TEXT    NOT NULL,
    logline                  TEXT,
    why_now                  TEXT,
    arc_state_json           TEXT,
    tension_text             TEXT,
    diff_summary             TEXT,                             -- "this story shifted: <event>+date" (doc 41 §4)
    snapshot_json            TEXT,                             -- full bible blob at this instant
    created_at_utc           TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (player_external_id, season_year, week, as_of_date)
);
CREATE INDEX IF NOT EXISTS idx_pbs_player
    ON player_bible_snapshots (player_external_id, season_year, week);

-- ---------------------------------------------------------------------------
-- player_ledger_scores — five fan-ledger scores per player-week (doc 47 §1 step 6).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_ledger_scores (
    player_ledger_score_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    player_external_id       TEXT    NOT NULL,
    player_id                INTEGER,
    season_year              INTEGER NOT NULL,
    week                     INTEGER,
    ledger                   TEXT    NOT NULL                  -- hope|grievance|belonging|judgment|grudge
        CHECK (ledger IN ('hope','grievance','belonging','judgment','grudge')),
    score                    REAL    NOT NULL DEFAULT 0.0,     -- rate vs cohort/baseline (empirical-Bayes)
    direction                TEXT,                             -- 'us'|'them'|'contested' (doc 47 §3)
    confidence               REAL    NOT NULL DEFAULT 0.0,     -- model agreement x source diversity x (1-sarcasm)
    doc_count                INTEGER NOT NULL DEFAULT 0,       -- representativeness (MIN_DOCS)
    source_count             INTEGER NOT NULL DEFAULT 0,       -- independent origins (MIN_SOURCES)
    fired                    INTEGER NOT NULL DEFAULT 0,       -- passed FIRE_THRESHOLD + representativeness
    structured_anchor_json   TEXT,                             -- the fact the ledger fuses with (doc 47 §5)
    evidence_doc_ids_json    TEXT,
    top_lexical_trace_json   TEXT,                             -- human-readable "why this fired" (doc 47 §1c)
    computed_at_utc          TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (player_external_id, season_year, week, ledger)
);
CREATE INDEX IF NOT EXISTS idx_pls_player_week
    ON player_ledger_scores (player_external_id, season_year, week, fired);

-- ---------------------------------------------------------------------------
-- player_succession — throne-line role-holder + Filling-the-Shoes + Clock (doc 44).
-- Keyed on the role-holder's player_external_id per (team, position, season).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_succession (
    player_succession_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    player_external_id       TEXT    NOT NULL,                 -- the INCUMBENT (role-holder) cfbd id
    player_id                INTEGER,
    team_id                  INTEGER NOT NULL,
    team_name                TEXT,
    season_year              INTEGER NOT NULL,
    position_group           TEXT    NOT NULL,                 -- 'QB','RB','WR',... (role detected)
    role_holder_usage        REAL,                             -- the defining stat (e.g. pass ATT)
    role_holder_stars        INTEGER,
    -- predecessor (the ghost)
    predecessor_external_id  TEXT,
    predecessor_name         TEXT,
    predecessor_stars        INTEGER,
    predecessor_usage        REAL,
    predecessor_fate         TEXT,                             -- 'drafted'|'transferred_out'|'benched'|'graduated'
    predecessor_dest_team    TEXT,                             -- portal chain destination
    -- heir-apparent (the clock)
    heir_external_id         TEXT,
    heir_name                TEXT,
    heir_stars               INTEGER,
    heir_origin              TEXT,                             -- 'internal'|'portal'|'true_freshman'
    heir_origin_team         TEXT,
    clock_score              REAL,                             -- pedigree x youth x latent_opportunity
    -- filling-the-shoes read
    shoes_read               TEXT,                             -- 'downgrade'|'upgrade'|'continuity'|'leap_of_faith'|'low_bar'
    shoes_tone               TEXT,                             -- 'mourning'|'dread'|'hope'|'reverence'|'relief'|'suspense'
    confidence               REAL    NOT NULL DEFAULT 0.0,     -- gated low for OL/DEF/partial depth
    detail_json              TEXT,                             -- full throne-line chain + portal flow
    computed_at_utc          TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (team_id, position_group, season_year)
);
CREATE INDEX IF NOT EXISTS idx_psucc_player
    ON player_succession (player_external_id, season_year);
CREATE INDEX IF NOT EXISTS idx_psucc_team
    ON player_succession (team_id, position_group, season_year);

-- ---------------------------------------------------------------------------
-- player_story_card_cache — the assembled StoryCard contract (doc 49 §5).
-- Rendered HTML + structured card payload, regen-gated by content_hash.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_story_card_cache (
    player_external_id       TEXT    NOT NULL,
    player_id                INTEGER,
    season_year              INTEGER NOT NULL,
    as_of_date               TEXT    NOT NULL,
    card_tier                TEXT    NOT NULL DEFAULT 'stats-strip' -- 'narrative'|'stats-strip' (doc 49 §5)
        CHECK (card_tier IN ('narrative','stats-strip')),
    fallback_rung            TEXT,                             -- 'full'|'reduced'|'low-data'|'omit' (doc 48 §3)
    card_json                TEXT,                             -- the full StoryCard dataclass as JSON
    card_html                TEXT,                             -- pre-rendered HTML (optional; can render at request)
    content_hash             TEXT,                             -- structured-inputs hash (regen short-circuit)
    model_id                 TEXT,                             -- 'deterministic-v1' or 'ollama:<model>'
    generated_at_utc         TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_external_id, season_year)
);

COMMIT;
