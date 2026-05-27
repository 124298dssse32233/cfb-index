-- Wave 25 / Phase 1 fix — Player Current Status View v2
--
-- CFBD has not yet published 2026 rosters as of 2026-05-27. v1 view at
-- 20260527_07 depended on roster_2026 to detect Type A returning vs
-- Type C transferred. Without that data, every Type A player resolved
-- to EXHAUSTED_ELIGIBILITY.
--
-- v2: infer Type A from existing tables:
--   • NFL drafted (any year)        → NFL_DRAFTED_*  (highest priority)
--   • 2026 transfer with destination → TRANSFERRED_COLLEGE
--   • 2026 transfer without dest     → PORTAL_OPEN
--   • Has 2026 roster row            → RETURNING_2026  (high confidence)
--   • Has 2025 roster row, no above  → RETURNING_2026  (inferred)
--   • Last stats season ≥ 2024 + nothing above → EXHAUSTED_ELIGIBILITY
--   • Otherwise                      → HISTORICAL_ALUM
--
-- Idempotent: DROPs and recreates the view.

DROP VIEW IF EXISTS player_current_status_view;

CREATE VIEW player_current_status_view AS
WITH
nfl AS (
    SELECT player_id,
           MAX(draft_year) AS latest_draft_year,
           MAX(CASE WHEN draft_year = 2026 THEN 1 ELSE 0 END) AS drafted_2026,
           (SELECT round FROM player_nfl_draft p2
              WHERE p2.player_id = p1.player_id
              ORDER BY draft_year DESC LIMIT 1) AS round,
           (SELECT pick FROM player_nfl_draft p2
              WHERE p2.player_id = p1.player_id
              ORDER BY draft_year DESC LIMIT 1) AS pick,
           (SELECT overall FROM player_nfl_draft p2
              WHERE p2.player_id = p1.player_id
              ORDER BY draft_year DESC LIMIT 1) AS overall,
           (SELECT nfl_team FROM player_nfl_draft p2
              WHERE p2.player_id = p1.player_id
              ORDER BY draft_year DESC LIMIT 1) AS nfl_team,
           (SELECT nfl_team_abbr FROM player_nfl_draft p2
              WHERE p2.player_id = p1.player_id
              ORDER BY draft_year DESC LIMIT 1) AS nfl_team_abbr
      FROM player_nfl_draft p1
      WHERE player_id IS NOT NULL
      GROUP BY player_id
),
roster_2026 AS (
    SELECT player_id, team_id, is_returning_player, position, class_year, jersey
      FROM roster_entries WHERE season_year = 2026
),
roster_2025 AS (
    SELECT player_id, team_id, position
      FROM roster_entries WHERE season_year = 2025
),
last_team AS (
    SELECT player_id, team_id, team_name, season_year AS last_year
    FROM (
        SELECT pss.player_id, pss.team_id, pss.team_name, pss.season_year,
               ROW_NUMBER() OVER (
                   PARTITION BY pss.player_id
                   ORDER BY pss.season_year DESC, pss.week DESC
               ) AS rn
        FROM player_season_stats pss
        WHERE pss.team_id IS NOT NULL
    ) ranked
    WHERE rn = 1
),
transfer_2026 AS (
    SELECT player_id, from_team_id, to_team_id, transfer_date,
           eligibility, from_team_name, to_team_name
      FROM transfer_entries WHERE season_year = 2026
)
SELECT
    p.player_id,
    p.full_name,
    p.position AS master_position,
    COALESCE(
        CASE
            WHEN o.expires_at IS NULL THEN o.status_code
            WHEN o.expires_at > strftime('%Y-%m-%dT%H:%M:%SZ', 'now') THEN o.status_code
        END,
        CASE
            -- 1. NFL trumps everything
            WHEN nfl.drafted_2026 = 1            THEN 'NFL_DRAFTED_2026'
            WHEN nfl.latest_draft_year IS NOT NULL THEN 'NFL_DRAFTED_PRIOR'
            -- 2. 2026 transfer with destination = confirmed Type C
            WHEN t26.to_team_id IS NOT NULL      THEN 'TRANSFERRED_COLLEGE'
            -- 3. 2026 transfer without destination = portal
            WHEN t26.player_id IS NOT NULL       THEN 'PORTAL_OPEN'
            -- 4. Hard 2026 roster signal (when CFBD lights up)
            WHEN r26.team_id IS NOT NULL         THEN 'RETURNING_2026'
            -- 5. 2025 roster + no NFL + no transfer → INFER returning
            WHEN r25.team_id IS NOT NULL         THEN 'RETURNING_2026'
            -- 6. Stats history fallback
            WHEN lt.last_year = 2025             THEN 'RETURNING_2026'
            WHEN lt.last_year = 2024             THEN 'EXHAUSTED_ELIGIBILITY'
            WHEN lt.last_year IS NOT NULL        THEN 'HISTORICAL_ALUM'
            ELSE 'HISTORICAL_ALUM'
        END
    ) AS status_code,
    o.status_label_text AS override_label,
    o.set_by AS override_set_by,
    o.set_at AS override_set_at,
    o.expires_at AS override_expires_at,
    o.source_url AS override_source_url,
    COALESCE(o.current_team_id, r26.team_id, t26.to_team_id, r25.team_id, lt.team_id) AS current_team_id,
    COALESCE(t26.from_team_id, r25.team_id) AS previous_team_id,
    t26.from_team_id AS portal_origin_team_id,
    nfl.latest_draft_year AS draft_year,
    nfl.round AS draft_round,
    nfl.pick AS draft_pick,
    nfl.overall AS draft_overall,
    nfl.nfl_team AS nfl_team,
    nfl.nfl_team_abbr AS nfl_team_abbr,
    COALESCE(r26.position, r25.position) AS position_2026,
    r26.class_year AS class_year_2026,
    r26.jersey AS jersey_2026,
    r26.is_returning_player AS is_returning_player,
    t26.transfer_date AS transfer_date,
    t26.eligibility AS transfer_eligibility,
    lt.team_id AS last_college_team_id,
    lt.team_name AS last_college_team_name,
    lt.last_year AS last_college_year,
    CASE
        WHEN o.player_id IS NOT NULL THEN 'override'
        WHEN nfl.player_id IS NOT NULL THEN 'computed_nfl'
        WHEN t26.player_id IS NOT NULL THEN 'computed_portal'
        WHEN r26.player_id IS NOT NULL THEN 'computed_2026_roster'
        WHEN r25.player_id IS NOT NULL THEN 'inferred_2025_roster'
        WHEN lt.player_id IS NOT NULL THEN 'inferred_stats_history'
        ELSE 'computed_default'
    END AS status_provenance
FROM players p
LEFT JOIN player_status_override o ON o.player_id = p.player_id
LEFT JOIN nfl ON nfl.player_id = p.player_id
LEFT JOIN roster_2026 r26 ON r26.player_id = p.player_id
LEFT JOIN roster_2025 r25 ON r25.player_id = p.player_id
LEFT JOIN transfer_2026 t26 ON t26.player_id = p.player_id
LEFT JOIN last_team lt ON lt.player_id = p.player_id;
