-- Storyline Threads schema
--
-- Sprint 10 — Storyline Threads v1. Persistent narrative threads (the
-- Stratechery / Acquired pattern adapted to CFB), each composed of
-- chapters that compound canon over time. Strategy lives in
-- docs/COMMUNAL_ENGAGEMENT_STRATEGY.md §"Storyline Threads" + §v2.
--
-- Three tables:
--   storyline_threads      — one row per active or archived thread
--   storyline_chapters     — append-only chapters under a thread
--   storyline_followers_stub — placeholder until email infra ships in
--                              a later sprint; lets the UI render a
--                              Follow CTA + cookie-id capture without
--                              the mail-send wire being live yet.
--
-- Disjoint from team_pages, editions, wire, canon, receipts. The
-- homepage's Active Threads section reads from this sprint's data via
-- stub_data/threads.json (the contract Sprint 9 consumes).

-- 1. storyline_threads ----------------------------------------------------

create table if not exists storyline_threads (
    thread_slug              text primary key,
    title                    text not null,
    dek                      text not null,
    accent_hex               text,
    status                   text not null check (status in ('active','resolved','archived')),
    started_at               date not null,
    last_chapter_at          datetime,
    follower_count           integer default 0,
    chapter_count            integer default 0,
    word_count               integer default 0,
    primary_program_slugs    text,             -- JSON array
    primary_conference_slug  text,
    voice_register_source    text,             -- 'profile:<slug>' | 'conference:<slug>' | 'editor-desk'
    created_at               datetime default current_timestamp,
    updated_at               datetime default current_timestamp
);

create index if not exists idx_storyline_threads_status_updated
    on storyline_threads(status, last_chapter_at desc);

-- 2. storyline_chapters ---------------------------------------------------

create table if not exists storyline_chapters (
    id                       integer primary key autoincrement,
    thread_slug              text not null references storyline_threads(thread_slug) on delete cascade,
    chapter_number           integer not null,
    title                    text not null,
    dek                      text not null,
    body_markdown            text not null,
    byline                   text not null,
    published_at             datetime not null,
    read_time_minutes        integer not null,
    referenced_chapter_ids   text,             -- JSON array of int chapter ids in same thread
    referenced_sources_json  text,             -- JSON array of {kind, name, label, url, date}
    pull_quote               text,             -- optional verbatim quote rendered in serif italic
    word_count               integer,
    voice_validator_passed   integer default 1,
    voice_validator_notes    text,
    created_at               datetime default current_timestamp,
    unique (thread_slug, chapter_number)
);

create index if not exists idx_storyline_chapters_thread_number
    on storyline_chapters(thread_slug, chapter_number desc);
create index if not exists idx_storyline_chapters_published
    on storyline_chapters(published_at desc);

-- 3. storyline_followers_stub --------------------------------------------

create table if not exists storyline_followers_stub (
    thread_slug text not null references storyline_threads(thread_slug) on delete cascade,
    cookie_id   text not null,
    email       text,
    followed_at datetime default current_timestamp,
    primary key (thread_slug, cookie_id)
);

create index if not exists idx_storyline_followers_email
    on storyline_followers_stub(email);
