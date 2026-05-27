-- Wave 25 — Player Current Status View v4
--
-- Adds override draft-field passthrough. When player_status_override has
-- nfl_team/draft_year/etc populated (from the alias script), the view
-- prefers those values over the player_id's own draft row (which may not
-- exist due to split-pid issues).
--
-- Precedence for draft fields:
--   1. override.nfl_team/draft_* (when override present and not expired)
--   2. nfl_direct (player_id's own draft row)
--   3. nfl_by_name (any draft row with matching full_name)

DROP VIEW IF EXISTS player_current_status_view;

CREATE VIEW player_current_status_view AS
WITH
nfl_direct AS (
    SELECT player_id,
           MAX(draft_year) AS latest_draft_year,
           MAX(CASE WHEN draft_year = 2026 THEN 1 ELSE 0 END) AS drafted_2026,
           (SELECT round FROM player_nfl_draft p2 WHERE p2.player_id = p1.player_id ORDER BY draft_year DESC LIMIT 1) AS round,
           (SELECT pick FROM player_nfl_draft p2 WHERE p2.player_id = p1.player_id ORDER BY draft_year DESC LIMIT 1) AS pick,
           (SELECT overall FROM player_nfl_draft p2 WHERE p2.player_id = p1.player_id ORDER BY draft_year DESC LIMIT 1) AS overall,
           (SELECT nfl_team FROM player_nfl_draft p2 WHERE p2.player_id = p1.player_id ORDER BY draft_year DESC LIMIT 1) AS nfl_team,
           (SELECT nfl_team_abbr FROM player_nfl_draft p2 WHERE p2.player_id = p1.player_id ORDER BY draft_year DESC LIMIT 1) AS nfl_team_abbr
      FROM player_nfl_draft p1
      WHERE player_id IS NOT NULL
      GROUP BY player_id
),
nfl_by_name AS (
    SELECT p.full_name,
           MAX(pnd.draft_year) AS latest_draft_year,
           MAX(CASE WHEN pnd.draft_year = 2026 THEN 1 ELSE 0 END) AS drafted_2026,
           (SELECT round FROM player_nfl_draft pnd2 JOIN players p2 ON p2.player_id = pnd2.player_id WHERE p2.full_name = p.full_name ORDER BY pnd2.draft_year DESC LIMIT 1) AS round,
           (SELECT pick FROM player_nfl_draft pnd2 JOIN players p2 ON p2.player_id = pnd2.player_id WHERE p2.full_name = p.full_name ORDER BY pnd2.draft_year DESC LIMIT 1) AS pick,
           (SELECT overall FROM player_nfl_draft pnd2 JOIN players p2 ON p2.player_id = pnd2.player_id WHERE p2.full_name = p.full_name ORDER BY pnd2.draft_year DESC LIMIT 1) AS overall,
           (SELECT nfl_team FROM player_nfl_draft pnd2 JOIN players p2 ON p2.player_id = pnd2.player_id WHERE p2.full_name = p.full_name ORDER BY pnd2.draft_year DESC LIMIT 1) AS nfl_team,
           (SELECT nfl_team_abbr FROM player_nfl_draft pnd2 JOIN players p2 ON p2.player_id = pnd2.player_id WHERE p2.full_name = p.full_name ORDER BY pnd2.draft_year DESC LIMIT 1) AS nfl_team_abbr
      FROM player_nfl_draft pnd
      JOIN players p ON p.player_id = pnd.player_id
      GROUP BY p.full_name
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
               ROW_NUMBER() OVER (PARTITION BY pss.player_id
                                  ORDER BY pss.season_year DESC, pss.week DESC) AS rn
        FROM player_season_stats pss
        WHERE pss.team_id IS NOT NULL
    ) ranked
    WHERE rn = 1
),
transfer_2026 AS (
    SELECT player_id, from_team_id, to_team_id, transfer_date,
           eligibility, from_team_name, to_team_name
      FROM transfer_entries WHERE season_year = 2026
),
override_active AS (
    SELECT *
      FROM player_status_override
     WHERE expires_at IS NULL
        OR expires_at > strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
)
SELECT
    p.player_id,
    p.full_name,
    p.position AS master_position,
    COALESCE(
        o.status_code,
        CASE
            WHEN nfl_d.drafted_2026 = 1            THEN 'NFL_DRAFTED_2026'
            WHEN nfl_d.latest_draft_year IS NOT NULL THEN 'NFL_DRAFTED_PRIOR'
            WHEN t26.to_team_id IS NOT NULL      THEN 'TRANSFERRED_COLLEGE'
            WHEN t26.player_id IS NOT NULL       THEN 'PORTAL_OPEN'
            WHEN r26.team_id IS NOT NULL         THEN 'RETURNING_2026'
            WHEN r25.team_id IS NOT NULL         THEN 'RETURNING_2026'
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
    -- Draft fields: override wins, then direct, then name-alias
    COALESCE(o.draft_year, nfl_d.latest_draft_year, nfl_n.latest_draft_year) AS draft_year,
    COALESCE(o.draft_round, nfl_d.round, nfl_n.round) AS draft_round,
    COALESCE(o.draft_pick, nfl_d.pick, nfl_n.pick) AS draft_pick,
    COALESCE(o.draft_overall, nfl_d.overall, nfl_n.overall) AS draft_overall,
    COALESCE(o.nfl_team, nfl_d.nfl_team, nfl_n.nfl_team) AS nfl_team,
    COALESCE(o.nfl_team_abbr, nfl_d.nfl_team_abbr, nfl_n.nfl_team_abbr) AS nfl_team_abbr,
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
        WHEN nfl_d.player_id IS NOT NULL THEN 'computed_nfl'
        WHEN t26.player_id IS NOT NULL THEN 'computed_portal'
        WHEN r26.player_id IS NOT NULL THEN 'computed_2026_roster'
        WHEN r25.player_id IS NOT NULL THEN 'inferred_2025_roster'
        WHEN lt.player_id IS NOT NULL THEN 'inferred_stats_history'
        ELSE 'computed_default'
    END AS status_provenance
FROM players p
LEFT JOIN override_active o         ON o.player_id = p.player_id
LEFT JOIN nfl_direct nfl_d          ON nfl_d.player_id = p.player_id
LEFT JOIN nfl_by_name nfl_n         ON nfl_n.full_name = p.full_name
LEFT JOIN roster_2026 r26           ON r26.player_id = p.player_id
LEFT JOIN roster_2025 r25           ON r25.player_id = p.player_id
LEFT JOIN transfer_2026 t26         ON t26.player_id = p.player_id
LEFT JOIN last_team lt              ON lt.player_id = p.player_id;
