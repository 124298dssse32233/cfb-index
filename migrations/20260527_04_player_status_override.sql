-- Wave 25 / Phase 1 — Player Status Override
--
-- Editorial override table. When a player's archetype needs manual correction
-- (e.g. Drew Allar was projected returning through April, drafted Rd 3 in
-- April 2026), an editor writes a row here. The view
-- player_current_status_view COALESCEs override.status_code over computed.

CREATE TABLE IF NOT EXISTS player_status_override (
    player_id          INTEGER PRIMARY KEY,
    status_code        TEXT    NOT NULL,
    status_label_text  TEXT,
    current_team_id    INTEGER,
    set_by             TEXT    NOT NULL,
    set_at             TEXT    NOT NULL,
    expires_at         TEXT,
    notes              TEXT,
    source_url         TEXT
);

CREATE INDEX IF NOT EXISTS idx_player_status_override_pid
    ON player_status_override(player_id);
CREATE INDEX IF NOT EXISTS idx_player_status_override_expires
    ON player_status_override(expires_at);
