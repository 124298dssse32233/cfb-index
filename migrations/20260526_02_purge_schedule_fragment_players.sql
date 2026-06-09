-- Purge schedule-fragment "players" created by the broken All-Conference
-- Wikipedia scraper (src/cfb_rankings/ingest/sources/wiki_awards.py:
-- scrape_all_conference).
--
-- Bug context (fixed 2026-05-26 in the same commit): the All-ACC / All-Big
-- Ten scraper used an unanchored, case-insensitive position regex
--   (QB|RB|...|C|S|K|P|...)
-- The single-letter codes C/S/K/P with re.IGNORECASE matched arbitrary words:
-- "Augu[s]t", "O[c]tober", "[p].m." — so the scraper parsed a TV-schedule
-- table (col 0 = kickoff time, col 1 = "Noon" / "7:00 p.m.") as if it were a
-- roster. Result: 30 fake player rows named after kickoff times + month
-- abbreviations written into players.position, plus 92 bogus player_honors
-- rows, plus broken player pages (slugs like 7:00-pm-63409).
--
-- The scraper now uses _canonical_conference_position() (exact-match against
-- a known position vocabulary) + _looks_like_player_name() (rejects times,
-- months, "vs.", "TBD"). This migration cleans the data those bugs already
-- wrote. All 30 target rows have ZERO player_game_stats rows (verified), so
-- no real production is lost.
--
-- Idempotent: re-running deletes nothing once clean (the GLOB/LIKE set is
-- empty after first run).

-- PRECISE garbage pattern. A schedule-fragment "player" is a kickoff time:
-- one or two digits, a colon, two digits — "7:00 p.m.", "12:30 p.m.", "3:30 PM".
-- The GLOB '*[0-9]:[0-9][0-9]*' requires that digit:digit-digit shape, so it
-- can never match a real name. (The earlier draft used LIKE '%PM'/'%AM' which
-- wrongly matched Cunningham, Ingram, Woodham, Liam, etc. — do NOT reintroduce
-- those broad patterns.) Plus an exact-match list of non-name placeholders.
BEGIN;

-- 1. Delete honors attached to the garbage players first (FK-safe ordering).
DELETE FROM player_honors
WHERE player_id IN (
    SELECT player_id FROM players
    WHERE full_name GLOB '*[0-9]:[0-9][0-9]*'
       OR full_name IN ('Noon', 'TBD', 'TBA', 'Canceled', 'Postponed', 'Bye')
);

-- 2. Delete the garbage player rows themselves. Restricted to rows with no
--    real game production so we never remove a legitimate player who happens
--    to share a name token.
DELETE FROM players
WHERE (
        full_name GLOB '*[0-9]:[0-9][0-9]*'
        OR full_name IN ('Noon', 'TBD', 'TBA', 'Canceled', 'Postponed', 'Bye')
      )
  AND player_id NOT IN (SELECT DISTINCT player_id FROM player_game_stats);

-- 3. Repair corrupted positions on surviving players. The bad scraper wrote
--    month abbreviations + opponent fragments into players.position. Null them
--    out so downstream position logic (accolade streams, etc.) falls back
--    cleanly rather than rendering "AUGU"/"SEPT"/"VS." as a position.
UPDATE players
SET position = NULL
WHERE position IN (
    'AUGU', 'SEPT', 'OCTO', 'NOVE', 'DECE', 'JANU', 'FEBR', 'MARC',
    'APRI', 'JUNE', 'JULY', 'VS.', 'VS', 'AT', 'WEEK', 'NOON', 'TBD',
    'NORT', 'SOUT', 'EAST', 'WEST', 'MICH', 'OHIO', 'PENN'
);

-- 4. Same repair on player_honors.position (the all_conference rows carry the
--    same corruption; all_america rows are clean and untouched).
UPDATE player_honors
SET position = NULL
WHERE position IN (
    'AUGU', 'SEPT', 'OCTO', 'NOVE', 'DECE', 'JANU', 'FEBR', 'MARC',
    'APRI', 'JUNE', 'JULY', 'VS.', 'VS', 'AT', 'WEEK', 'NOON', 'TBD',
    'NORT', 'SOUT', 'EAST', 'WEST', 'MICH', 'OHIO', 'PENN'
);

COMMIT;

-- VERIFY: SELECT COUNT(*) FROM players WHERE full_name LIKE '%p.m.%';  -- expect 0
