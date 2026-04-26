-- Sprint 9 — Edition framework schema.
-- Powers src/cfb_rankings/editions/. Disjoint from reporting.py and team_pages.
-- Idempotent. CREATE IF NOT EXISTS only.
--
-- Design rationale:
--   * editions is the per-week magazine cover record. theme + dek + viz_kind +
--     viz_data_json + cover_essay pointer is enough to render the homepage.
--     status enum lets us draft an edition before publishing.
--   * edition_features is the article corpus for an edition. feature_kind
--     covers the 7 categories from EDITORIAL_POSITIONING_AND_CONTENT_TYPES.
--     feature_order drives the Roman numeral display (I = cover essay, II..N
--     = secondary features). storyline_thread_slug / canon_entry_slug /
--     receipt_id are nullable join keys to Wave 2 sprints.
--   * edition_voices records the beat-writer / podcaster / board profiles
--     surfaced in the "Voices Behind This Edition" section. receipt_score_pct
--     denormalises Sprint 13's rolling accuracy score for fast read.

create table if not exists editions (
    edition_slug text primary key,
    edition_number integer not null,
    volume integer not null,
    publish_date text not null,
    theme_title text not null,
    theme_dek text not null,
    cover_viz_kind text not null
        check (cover_viz_kind in ('gap','drift','field','heatmap','distribution','flow','rank_shift')),
    cover_viz_data_json text not null,
    cover_essay_id integer,
    status text not null default 'draft'
        check (status in ('draft','published','archived')),
    published_at_utc text,
    created_at_utc text not null default current_timestamp,
    last_updated_utc text not null default current_timestamp
);

create index if not exists idx_editions_publish_date on editions (publish_date);
create index if not exists idx_editions_status on editions (status);

create table if not exists edition_features (
    id integer primary key autoincrement,
    edition_slug text not null references editions(edition_slug),
    feature_order integer not null,
    feature_kind text not null
        check (feature_kind in ('cover_essay','feature','reaction','receipt','connection','disagreement','fan_voice')),
    title text not null,
    dek text not null,
    body_markdown text not null,
    byline text not null,
    read_time_minutes integer not null,
    storyline_thread_slug text,
    canon_entry_slug text,
    receipt_id integer,
    created_at_utc text not null default current_timestamp,
    unique (edition_slug, feature_order)
);

create index if not exists idx_edition_features_slug on edition_features (edition_slug, feature_order);
create index if not exists idx_edition_features_kind on edition_features (feature_kind);

create table if not exists edition_voices (
    edition_slug text not null references editions(edition_slug),
    source_slug text not null,
    role_label text not null,
    bio text not null,
    receipt_score_pct integer,
    receipt_score_label text,
    takes_tracked integer not null default 0,
    voice_order integer not null default 0,
    primary key (edition_slug, source_slug)
);

create index if not exists idx_edition_voices_order on edition_voices (edition_slug, voice_order);
