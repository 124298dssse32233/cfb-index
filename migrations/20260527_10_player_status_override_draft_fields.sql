-- Wave 25 — Carry draft fields in the override table
--
-- Some marquee NFL players have stats pid != draft pid AND different name
-- variants (Cam Ward pid=1015 draft, Cameron Ward pid=9464 stats). The
-- name-alias resolution in view v3 catches exact name matches but not
-- variants. Cleanest fix: let the override row itself carry the draft
-- payload, then the view uses it directly.

ALTER TABLE player_status_override ADD COLUMN nfl_team TEXT;
ALTER TABLE player_status_override ADD COLUMN nfl_team_abbr TEXT;
ALTER TABLE player_status_override ADD COLUMN draft_year INTEGER;
ALTER TABLE player_status_override ADD COLUMN draft_round INTEGER;
ALTER TABLE player_status_override ADD COLUMN draft_pick INTEGER;
ALTER TABLE player_status_override ADD COLUMN draft_overall INTEGER;
