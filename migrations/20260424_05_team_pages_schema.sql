-- Team-Pages schema additions — TEAM_PAGE_WORLD_CLASS_BRIEF + ITERATION_LOG.
-- Powers the new src/cfb_rankings/team_pages/ module. Disjoint from reporting.py.
-- Idempotent. CREATE IF NOT EXISTS style only. Column additions are NOT allowed
-- here — put those in cfb_rankings.migrations.apply_runtime_migrations.
--
-- Design rationale:
--  * team_profiles stores the hand-curated ~45-50-field editorial profile as a
--    single JSON blob (profile_json) plus a small set of hoisted columns that
--    are queried often (voice_register, program_tier, identity_phrase). The
--    JSON blob is the source of truth; hoisted columns are denormalised for
--    fast joins and can be rebuilt from profile_json. This lets profiles grow
--    new sections without schema churn.
--  * team_season_narratives is the write-back target for the LLM paragraph
--    generator. One row per (team, season, variant) so we can regenerate
--    without deleting prior drafts. `variant` enum covers state-of-team,
--    defining-moment, pull-quote, legacy-paragraph, season-thesis — five of
--    the iteration-log's narrative surfaces.
--  * team_chronicle_observations stores the six card-type taxonomy from
--    iteration-log §"Card-type taxonomy for observations" — each card carries
--    its content, source attribution, and a week stamp. Ranking/surfaced flag
--    lets the generator write >K candidates and the renderer pick top-K per
--    week.
--  * team_voice is intentionally separate from team_profiles: voice surfaces
--    (accent hex, vocab, mascot voice templates, era-name overrides) are
--    pulled by every render path (titles, footers, fallbacks) and benefit
--    from being a single-row lookup. One row per team.

-- ------------------------------------------------------------------
-- team_profiles: editorial program profile, ~45-50 hand-curated fields,
-- stored primarily as structured JSON with hoisted columns for hot paths.
-- ------------------------------------------------------------------
create table if not exists team_profiles (
    team_id integer primary key references teams(team_id),
    program_slug text not null,
    program_tier integer not null,              -- 1-10 per iteration-log tier taxonomy
    voice_register text not null,               -- dynastic / defiant-academic / scrappy-proud / ...
    identity_phrase text,                       -- headline opens with this
    mantra text,                                -- sign-off phrase
    tonal_template text,                        -- enum: dynasty / rebuild / cult / rising / haunted / ...
    profile_json text not null,                 -- full ~45-50 field blob (markdown-frontmatter → dict)
    source_path text,                           -- profiles/<slug>.md path for provenance
    authored_by text,                           -- 'opus-editorial' / 'sonnet-editorial' / 'kevin'
    editorial_review_status text not null default 'draft',   -- draft / reviewed / published
    created_at_utc text not null default current_timestamp,
    updated_at_utc text not null default current_timestamp
);

create unique index if not exists idx_team_profiles_slug
    on team_profiles (program_slug);
create index if not exists idx_team_profiles_tier
    on team_profiles (program_tier);
create index if not exists idx_team_profiles_register
    on team_profiles (voice_register);

-- ------------------------------------------------------------------
-- team_season_narratives: per (team, season, variant) editorial paragraphs
-- written by the LLM generator. `variant` is the narrative surface.
-- ------------------------------------------------------------------
create table if not exists team_season_narratives (
    team_season_narrative_id integer primary key autoincrement,
    team_id integer not null references teams(team_id),
    season_year integer not null references seasons(season_year),
    variant text not null,                      -- 'state_of_team' | 'season_thesis' | 'defining_moment' | 'pull_quote' | 'legacy_paragraph'
    title text,                                 -- optional serif headline
    body_md text not null,                      -- the generated paragraph (markdown)
    attribution text,                           -- attribution for pull_quote; null otherwise
    week_context integer,                       -- week the narrative is calibrated to (0 = full-season / offseason)
    state_signature text,                       -- JSON blob of sentience params used at generation time
    model_id text not null,                     -- 'claude-sonnet-4-6' / 'claude-opus-4-7' / 'template-v1'
    prompt_tokens integer,
    completion_tokens integer,
    generation_cost_usd real,
    voice_score real,                           -- self-review score 0-1 (reserved)
    is_published integer not null default 0,
    generated_at_utc text not null default current_timestamp,
    superseded_at_utc text,
    unique (team_id, season_year, variant, week_context)
);

create index if not exists idx_team_season_narr_team
    on team_season_narratives (team_id, season_year);
create index if not exists idx_team_season_narr_variant
    on team_season_narratives (variant, is_published);

-- ------------------------------------------------------------------
-- team_chronicle_observations: the 6-type editorial observation corpus
-- (anomaly / moment / flashpoint / echo / retroactive / player_arc).
-- ------------------------------------------------------------------
create table if not exists team_chronicle_observations (
    team_chronicle_observation_id integer primary key autoincrement,
    team_id integer not null references teams(team_id),
    season_year integer not null references seasons(season_year),
    week integer,                               -- null = season-level / offseason
    card_type text not null,                    -- 'anomaly' | 'moment' | 'flashpoint' | 'echo' | 'retroactive' | 'player_arc'
    headline text not null,                     -- short title (serif)
    body_md text not null,                      -- editorial copy (markdown, 2-4 sentences)
    stat_json text,                             -- the raw stat surfaced (json blob)
    comparison_json text,                       -- the historical comparison (json blob)
    source_attribution text,                    -- 'CFB Index model' / 'play-by-play' / 'fan-intel pipeline' / etc
    surprise_score real,                        -- 0-1; higher = more surprising to reader. Used for ranking.
    surfaced_rank integer,                      -- 1 = top card of the week (null = candidate, not selected)
    state_signature text,                       -- sentience snapshot JSON
    model_id text not null,                     -- model that wrote the copy
    prompt_tokens integer,
    completion_tokens integer,
    is_published integer not null default 0,
    generated_at_utc text not null default current_timestamp,
    unique (team_id, season_year, week, card_type, headline)
);

create index if not exists idx_team_chron_team_week
    on team_chronicle_observations (team_id, season_year, week);
create index if not exists idx_team_chron_surfaced
    on team_chronicle_observations (is_published, surfaced_rank);
create index if not exists idx_team_chron_card_type
    on team_chronicle_observations (card_type);

-- ------------------------------------------------------------------
-- team_voice: compact, one-row-per-team voice config read at every render.
-- Stored separate from team_profiles because the renderer/template layer
-- touches these fields on *every* request, while the full profile JSON is
-- only read during narrative generation.
-- ------------------------------------------------------------------
create table if not exists team_voice (
    team_id integer primary key references teams(team_id),
    accent_hex text not null,                   -- primary program color (#RRGGBB)
    accent_hex_secondary text,                  -- paired secondary (gradient partner)
    gradient_hex_pair text,                     -- 'primary,secondary' for css --accent-gradient
    vocab_dict_json text not null default '{}', -- {'signoff':'Roll Tide','greeting':'RTR',...}
    mascot_voice_templates_json text not null default '{}',  -- {'awaiting_signal':'The Elephant is...','empty_state':'...'}
    era_name_overrides_json text not null default '{}',      -- {'2007-present':'The Process Era',...}
    tonal_template text not null,               -- mirror of team_profiles.tonal_template for fast lookup
    never_use_phrases_json text not null default '[]',       -- guardrails: phrases that will NEVER appear in rendered copy
    always_surface_phrases_json text not null default '[]',  -- priors for narrative generator
    updated_at_utc text not null default current_timestamp
);

create index if not exists idx_team_voice_tonal
    on team_voice (tonal_template);
