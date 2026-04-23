-- source_observations: generic landing table for Tier A numeric observations.
-- STRATEGY §1 principle #2 ("every row carries provenance") applied literally —
-- each row encodes the full lineage: source_id, what entity it describes,
-- when it was observed, what metric, and the raw payload for audit.
--
-- Tier A adapters (wiki_pv, seatgeek, youtube_meta, kalshi, polymarket,
-- gdelt_volume, spotify_charts) write here. Adapters that have a natural
-- home in an existing table (cfbd → game_lines, etc.) continue to use it.
--
-- Decision 2026-04-23: Kevin's "take care of all this" = build the table
-- now, recommendation (a) from the blocker note in SESSION_LOG. Additive,
-- reversible (drop table). Not retroactively in STRATEGY §5 — the strategy
-- doc should be updated to reference this table in a future edit.

create table if not exists source_observations (
    source_observation_id integer primary key autoincrement,
    source_id           text not null,
    entity_type         text not null,            -- team | player | game | market | article_query | channel | event | podcast
    entity_id           text,                      -- JSON or "{id}" string; interpretation is per entity_type
    entity_label        text,                      -- human-readable: "Alabama football", "CFP Winner 2026"
    observed_at_utc     text not null,
    metric              text not null,            -- "pageviews" | "get_in_cents" | "listings" | "video_views" | ...
    value_numeric       real,
    value_text          text,                      -- for ordinal/categorical observations (rank label, chart position string)
    sample_window       text,                      -- e.g. "7d", "24h", "instant"
    -- STRATEGY §5 provenance
    source_tier         text,
    ingestion_adapter_version text,
    capture_url         text,
    canonical_url       text,
    raw_payload_json    text,
    dedup_key           text,                      -- sha1(source_id|entity_id|metric|observed_at_utc[:13])
    created_at_utc      text not null default current_timestamp
);

create unique index if not exists idx_source_observations_dedup
    on source_observations (dedup_key)
    where dedup_key is not null;

create index if not exists idx_source_observations_entity
    on source_observations (entity_type, entity_id, metric, observed_at_utc);

create index if not exists idx_source_observations_source_metric
    on source_observations (source_id, metric, observed_at_utc);
