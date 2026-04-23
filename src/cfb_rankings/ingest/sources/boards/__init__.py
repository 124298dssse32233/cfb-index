"""Independent message-board adapters. Per STRATEGY §3, each board is its
own source_id (``board_{name}``). The Python half here handles whatever
automation is possible (RSS feeds where available, structured thread
indexes); the Cowork playbook (``docs/cowork_playbooks/monday_board_sweep.md``)
handles the rest. Most boards only expose RSS for new-threads-listing, not
post content — so these adapters deliberately fetch headline+timestamp only
and leave body_text NULL for Cowork to fill in."""
