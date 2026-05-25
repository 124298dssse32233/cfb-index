-- Clean orphaned child rows left by the 20260526_02 schedule-fragment player
-- purge. Those player deletes left 213 rows in player_source_ids pointing at
-- player_ids that no longer exist. player_source_ids has a hard
-- `references players(player_id)` FK, so when the CFBD recruiting ingest
-- (_match_player_for_recruit -> _upsert_player_source_ids, cfbd.py:831)
-- matched one of those dangling source ids it tried to UPDATE player_id to a
-- non-existent player and hit FOREIGN KEY constraint failed — blocking the
-- 2026 preseason/recruiting ingest entirely.
--
-- Fix: delete player_source_ids (and any other orphaned children) whose
-- player_id has no matching players row. Idempotent.

BEGIN;

DELETE FROM player_source_ids
WHERE player_id NOT IN (SELECT player_id FROM players);

COMMIT;

-- VERIFY: SELECT COUNT(*) FROM player_source_ids s
--   LEFT JOIN players p ON p.player_id = s.player_id WHERE p.player_id IS NULL;  -- expect 0
