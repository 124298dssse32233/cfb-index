"""Shaggy Bevo (Texas) — TASK 5.3. No public RSS; this adapter is a
placeholder that raises NotImplementedError on fetch. Cowork playbook
handles all extraction until the board exposes a scraping-friendly index.
"""
from __future__ import annotations

from typing import Any

from cfb_rankings.ingest.sources.base import SourceAdapter


class ShaggyBevoAdapter(SourceAdapter):
    source_id = "board_shaggy_bevo"
    adapter_version = "0.1.0"

    def __init__(self, db, team_id: int) -> None:
        self.team_id = team_id
        super().__init__(db)

    def fetch(self) -> Any:
        raise NotImplementedError(
            "Shaggy Bevo does not expose a public RSS or scraping-friendly index. "
            "Use docs/cowork_playbooks/monday_board_sweep.md for extraction."
        )

    def parse(self, raw: Any) -> list[dict[str, Any]]:
        return []

    def write_rows(self, rows):
        return 0


__all__ = ["ShaggyBevoAdapter"]
