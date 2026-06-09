-- Wave 25 / Phase 1 — Player Current Status View
--
-- Single source of truth for "what's this player's deal in May 2026?"
-- 11 status codes resolved deterministically. Override table beats
-- computed when present and not expired.
--
-- Resolution order (first match wins, applied via CASE):
--   1. NFL drafted in CURRENT_YEAR → NFL_DRAFTED_2026
--   2. NFL drafted in any earlier year → NFL_DRAFTED_PRIOR
--   3. On 2026 roster, same team as 2025 → RETURNING_2026
--   4. On 2026 roster, different team → TRANSFERRED_COLLEGE
--   5. In transfer portal 2026 without destination → PORTAL_OPEN
--   6. Was in portal then back at original school → PORTAL_WITHDREW
--   7. No 2026 roster, last season ≥ 2024 → EXHAUSTED_ELIGIBILITY
--   8. No 2026 roster, last season < 2024 → HISTORICAL_ALUM

DROP VIEW IF EXISTS player_current_status_view;

CREATE VIEW player_current_status_view AS
WITH
nfl AS (
    SELECT player_id,
           MAX(draft_year)                                          AS latest_draft_year,
           MAX(CASE WHEN draft_year = 2026 THEN 1 ELSE 0 END)       AS drafted_2026,
           (SELECT round       FROM player_nfl_draft p2
              WHERE p2.player_id = p1.player_id
              ORDER BY draft_year DESC LIMIT 1)                     AS round,
           (SELECT pick        FROM player_nfl_draft p2
              WHERE p2.player_id = p1.player_id
              ORDER BY draft_year DESC LIMIT 1)                     AS pick,
           (SELECT overall     FROM player_nfl_draft p2
              WHERE p2.player_id = p1.player_id
              ORDER BY draft_year DESC LIMIT 1)                     AS overall,
           (SELECT nfl_team    FROM player_nfl_draft p2
              WHERE p2.player_id = p1.player_id
              ORDER BY draft_year DESC LIMIT 1)                     AS nfl_team,
           (SELECT nfl_team_abbr FROM player_nfl_draft p2
              WHERE p2.player_id = p1.player_id
              ORDER BY draft_year DESC LIMIT 1)                     AS nfl_team_abbr
      FROM player_nfl_draft p1
      WHERE player_id IS NOT NULL
      GROUP BY player_id
),
roster_2026 AS (
    SELECT player_id, team_id, is_returning_player,
           position, class_year, jersey
      FROM roster_entries
      WHERE season_year = 2026
),
roster_2025 AS (
    SELECT player_id, team_id, position
      FROM roster_entries
      WHERE season_year = 2025
),
last_team AS (
    -- pick the most-recent team a player appeared on (roster or stats),
    -- with snap-count/games-played tiebreak to handle mid-season transfers
    SELECT player_id,
           team_id,
           team_name,
           season_year AS last_year
    FROM (
        SELECT pss.player_id,
               pss.team_id,
               pss.team_name,
               pss.season_year,
               ROW_NUMBER() OVER (
                   PARTITION BY pss.player_id
                   ORDER BY pss.season_year DESC,
                            pss.week DESC
               ) AS rn
        FROM player_season_stats pss
        WHERE pss.team_id IS NOT NULL
    ) ranked
    WHERE rn = 1
),
transfer_2026 AS (
    SELECT player_id, from_team_id, to_team_id, transfer_date,
           eligibility, from_team_name, to_team_name
      FROM transfer_entries
      WHERE season_year = 2026
)
SELECT
    p.player_id,
    p.full_name,
    p.position                                AS master_position,
    -- Resolution: override beats computed (when override present and not expired)
    COALESCE(
        CASE
            WHEN o.expires_at IS NULL THEN o.status_code
            WHEN o.expires_at > strftime('%Y-%m-%dT%H:%M:%SZ', 'now') THEN o.status_code
        END,
        -- Computed path:
        CASE
            WHEN nfl.drafted_2026 = 1                                THEN 'NFL_DRAFTED_2026'
            WHEN nfl.latest_draft_year IS NOT NULL                   THEN 'NFL_DRAFTED_PRIOR'
            WHEN r26.team_id IS NOT NULL AND r25.team_id IS NOT NULL
                 AND r26.team_id = r25.team_id                       THEN 'RETURNING_2026'
            WHEN r26.team_id IS NOT NULL AND r25.team_id IS NOT NULL
                 AND r26.team_id != r25.team_id                      THEN 'TRANSFERRED_COLLEGE'
            WHEN r26.team_id IS NOT NULL AND r25.team_id IS NULL     THEN 'TRANSFERRED_COLLEGE'
            WHEN t26.player_id IS NOT NULL AND t26.to_team_id IS NULL THEN 'PORTAL_OPEN'
            WHEN t26.player_id IS NOT NULL AND r26.team_id IS NULL   THEN 'PORTAL_OPEN'
            WHEN lt.last_year IS NULL                                THEN 'HISTORICAL_ALUM'
            WHEN lt.last_year >= 2024                                THEN 'EXHAUSTED_ELIGIBILITY'
            ELSE 'HISTORICAL_ALUM'
        END
    ) AS status_code,
    -- Override-only fields
    o.status_label_text AS override_label,
    o.set_by            AS override_set_by,
    o.set_at            AS override_set_at,
    o.expires_at        AS override_expires_at,
    o.source_url        AS override_source_url,
    -- Current team
    COALESCE(
        o.current_team_id,
        r26.team_id,
        t26.to_team_id,
        lt.team_id
    ) AS current_team_id,
    -- Previous team (for Type C transfer flow)
    r25.team_id AS previous_team_id,
    t26.from_team_id AS portal_origin_team_id,
    -- NFL draft fields (passed through for Type B render)
    nfl.latest_draft_year AS draft_year,
    nfl.round             AS draft_round,
    nfl.pick              AS draft_pick,
    nfl.overall           AS draft_overall,
    nfl.nfl_team          AS nfl_team,
    nfl.nfl_team_abbr     AS nfl_team_abbr,
    -- Roster context
    r26.position          AS position_2026,
    r26.class_year        AS class_year_2026,
    r26.jersey            AS jersey_2026,
    r26.is_returning_player AS is_returning_player,
    -- Transfer context
    t26.transfer_date     AS transfer_date,
    t26.eligibility       AS transfer_eligibility,
    -- Last-team alumni context
    lt.team_id            AS last_college_team_id,
    lt.team_name          AS last_college_team_name,
    lt.last_year          AS last_college_year,
    -- Provenance
    CASE WHEN o.player_id IS NOT NULL THEN 'override' ELSE 'computed' END AS status_provenance
FROM players p
LEFT JOIN player_status_override o
    ON o.player_id = p.player_id
LEFT JOIN nfl
    ON nfl.player_id = p.player_id
LEFT JOIN roster_2026 r26
    ON r26.player_id = p.player_id
LEFT JOIN roster_2025 r25
    ON r25.player_id = p.player_id
LEFT JOIN transfer_2026 t26
    ON t26.player_id = p.player_id
LEFT JOIN last_team lt
    ON lt.player_id = p.player_id;
