-- Migration 20260527_05: Bulk reconcile split player IDs (honors importer vs CFBD game stats)
--
-- The honors import pipeline generates its own player_ids which diverge from
-- the CFBD-sourced game-stats player_ids. This remap unifies them so trophy_case
-- and any other player_id-keyed query gets correct results for both.
--
-- All remapped honor_pids have 0 rows in player_season_stats — safe to update.
-- All stats_pids have 0 existing honor rows — no duplicates introduced.

-- Caleb Downs (Safety, Georgia → Ohio State 2024, Consensus All-America)
UPDATE player_honors SET player_id = 3744   WHERE player_id = 1382;

-- Nick Nash (OL, Arkansas 2024)
UPDATE player_honors SET player_id = 8917   WHERE player_id = 880;

-- Walter Nolen (DL, Ole Miss 2024)
UPDATE player_honors SET player_id = 13889  WHERE player_id = 1114;

-- Shaun Dolac (OL, Penn State 2024)
UPDATE player_honors SET player_id = 12385  WHERE player_id = 1544;

-- Kyle Kennard (EDGE, Georgia 2024)
UPDATE player_honors SET player_id = 8183   WHERE player_id = 1852;

-- Keelan Marion (WR, Iowa State 2024)
UPDATE player_honors SET player_id = 12504  WHERE player_id = 7394;

-- Dillon Gabriel (QB, Oregon 2024)
UPDATE player_honors SET player_id = 11737  WHERE player_id = 120;

-- Dominic Zvada (K, Michigan 2024)
UPDATE player_honors SET player_id = 9376   WHERE player_id = 3138;

-- Kyle McCord (QB, Syracuse 2024)
UPDATE player_honors SET player_id = 13661  WHERE player_id = 1864;

-- Aiden Fisher (LB, Auburn 2024)
UPDATE player_honors SET player_id = 10974  WHERE player_id = 2406;
