-- team_coverage: unified registry of every cohort membership that today
-- lives across 6 disjoint structures in the codebase. Per DECISIONS.md#D-016,
-- consolidating them into one queryable table is Phase 1 / WS-01.
--
-- The 6 source structures this table replaces (read-side consumers should
-- migrate to query this table; the source structures stay as the seed input
-- and can be removed once readers are migrated):
--
--   1. PROFILED_SLUGS                  → tier='authored'             (~127 rows)
--   2. seeds/priority_teams.yaml       → tier='priority_intelligence' (21 rows)
--   3. TOP_ENTITIES_FULL               → tier='pulse_full'             (5 rows)
--   4. TOP_ENTITIES_PARTIAL            → tier='pulse_partial'         (18 rows)
--   5. BLUEBLOOD_PROGRAMS              → tier='blueblood_pedigree'    (19 rows)
--   6. STRUCTURAL_PRIMARIES (dict)     → tier='structural_identity'   (11 canonical, 23 aliased)
--
-- A team appears once per tier it qualifies for — most teams qualify for 0
-- or 1, top programs (Alabama, Ohio State, Georgia) qualify for 4. The
-- (team_slug, tier) UNIQUE constraint makes the table set-semantic.
--
-- Why a table not a YAML: queries like "which teams are both authored and
-- blueblood?" require runtime intersection. Today every reader of these
-- sources hardcodes the import. With the table, callers query by tier.
--
-- Migration timing locked at Phase 1 / week 2 per D-016 reasoning: touches
-- ~6 reader files but publish_site behavior should be byte-identical before
-- and after. The backfill script (scripts/backfill_team_coverage.py) is the
-- one-time data move from each source structure into rows here.
--
-- Audit log: source_origin records WHICH source structure inserted the row.
-- This is intentional — even after readers migrate, we keep the trail so a
-- future quarterly audit can see "this row came from BLUEBLOOD_PROGRAMS
-- on 2026-05-28" without spelunking git history.

create table if not exists team_coverage (
    coverage_id     integer primary key autoincrement,
    team_slug       text not null,
    tier            text not null,           -- one of the 6 tier enums below
    source_origin   text not null,           -- which source structure inserted this row
    archetype_slug  text,                    -- only populated for tier='structural_identity'
    rank_priority   integer,                 -- only populated for tier='priority_intelligence' (from YAML rank_priority)
    notes           text,                    -- free-text per-row annotation
    added_utc       text not null default current_timestamp,
    -- The set semantic: a team belongs to a tier at most once. Multiple
    -- rows per team is the norm (Alabama: authored + priority + pulse_full +
    -- blueblood). Aliases (texas-a-m vs texas-am, southern-california vs usc)
    -- are stored as separate rows; alias resolution is a reader concern.
    unique (team_slug, tier)
);

-- Tier enum values (single source of truth lives here, not in Python):
--   authored                — hand-authored editorial profile in profiles/*.md
--   priority_intelligence   — top-N targets for Fan Intelligence pipelines
--   pulse_full              — gets 3 themes/week via world_class_enrich (Tier 1)
--   pulse_partial           — gets 1 theme + 1 lede/week (Tier 2)
--   blueblood_pedigree      — secondary archetype bias signal (Anxious Dynasty etc.)
--   structural_identity     — deterministic archetype lock (service academy / HBCU)
--
-- source_origin enum:
--   profiled_yaml           — from profiles/*.md filename glob
--   priority_teams_yaml     — from seeds/priority_teams.yaml
--   top_entities_full       — from src/cfb_rankings/team_pages/pulse_state.py
--   top_entities_partial    — from src/cfb_rankings/team_pages/pulse_state.py
--   blueblood_programs      — from src/cfb_rankings/ingest/archetypes.py
--   structural_primaries    — from src/cfb_rankings/ingest/archetypes.py

-- (tier, team_slug) covers the "members of tier X" query path. The
-- UNIQUE(team_slug, tier) constraint above already provides the
-- implicit (team_slug, tier) prefix index — sufficient for "tiers a
-- given team belongs to" lookups — so no separate by_slug index needed.
create index if not exists idx_team_coverage_by_tier
    on team_coverage (tier, team_slug);
