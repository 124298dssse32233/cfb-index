-- Hotfix-5 (owner Interrupt 2): purge the legacy fake-news offseason
-- fallback rows that are still surfacing on /wire/.
--
-- Bug context: commit 1162d5b3 (hotfix-1, 2026-05-15) rewrote
-- src/cfb_rankings/wire/offseason_fallback.py from "14 hardcoded fake
-- transactions" to "real-data retro selector". But the rewrite only
-- changed FUTURE writes — the wire_entries table still had ~14 rows
-- of fake content (Quinn Ewers to Ohio State, Glenn Schumann leaving
-- Georgia, Matayo Uiagalelei entering portal, etc.) tagged with
-- source_kind='unverified' that the wire renderer kept reading and
-- showing on the live site at /wire/index.html — the exact bug the
-- hotfix was supposed to eliminate.
--
-- Companion render-time filter added in wire/renderer.py — both
-- defenses run, so this migration's effect is to clean the data at
-- source while the filter handles any future drift.
--
-- All non-'unverified' rows are preserved (real CFBD portal pulls,
-- real recruiting commits from player_recruiting_profiles, etc).

DELETE FROM wire_entries
WHERE coalesce(source_kind, '') = 'unverified';
