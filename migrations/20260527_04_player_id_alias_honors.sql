-- Migration 20260527_04: Reconcile split player IDs for Cam/Cameron aliases
--
-- The honors import used different player IDs than the CFBD game-stats pipeline.
-- "Cam Ward" (pid=1015) == "Cameron Ward" (pid=9464, Miami QB 2024)
-- "Cam Ward (2-6)" (pids 63488-63493) == same person, duplicate selector rows
-- "Cam Skattebo" (pid=63722) == "Cameron Skattebo" (pid=9254, Arizona State RB 2024)
--
-- We remap player_honors to the canonical CFBD-sourced player_id so that
-- trophy_case.py and other modules that query by player_id work correctly.
-- These orphan IDs have 0 rows in player_season_stats, so the remap is safe.

-- Cameron Ward: remap all Cam Ward honor rows to Cameron Ward CFBD id
UPDATE player_honors SET player_id = 9464
WHERE player_id IN (1015, 63488, 63489, 63490, 63492, 63493);

-- Cameron Skattebo: remap Cam Skattebo to Cameron Skattebo CFBD id
UPDATE player_honors SET player_id = 9254
WHERE player_id = 63722;
