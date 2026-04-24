"""Base class for mock draft board adapters — TASK 4.6.

Subclasses implement ``fetch_and_parse()`` and return rows in the
DraftProjectionRow shape. The base handles upsert + dedup against
player_draft_projection.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, asdict
from typing import Any

from cfb_rankings.db import Database

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DraftProjectionRow:
    player_name: str
    source_name: str
    snapshot_date: str                # YYYY-MM-DD
    projected_round: int | None = None
    projected_pick: int | None = None          # overall pick
    projected_team_name: str | None = None
    overall_rank: int | None = None
    position_rank: int | None = None
    confidence_note: str | None = None
    source_url: str | None = None
    raw: str | None = None                     # original fragment for debugging


class DraftBoardAdapter:
    source_name: str = ""                      # e.g. 'kiper', 'jeremiah'
    adapter_version: str = "0.1.0"

    def __init__(self, db: Database) -> None:
        self.db = db
        if not self.source_name:
            raise ValueError(f"{type(self).__name__} must set source_name")

    # Subclass override -----------------------------------------------------
    def fetch_and_parse(self) -> list[DraftProjectionRow]:
        raise NotImplementedError

    # Default write path ----------------------------------------------------
    def run(self) -> dict[str, int]:
        rows = self.fetch_and_parse()
        if not rows:
            log.info("%s: 0 rows produced", self.source_name)
            return {"fetched": 0, "upserted": 0, "resolved": 0}

        db_rows: list[dict[str, Any]] = []
        resolved = 0
        for r in rows:
            pid = self._resolve_player_id(r.player_name)
            team_id = self._resolve_team_id(r.projected_team_name)
            if pid is not None:
                resolved += 1
            db_rows.append({
                "player_id": pid or 0,
                "source_name": r.source_name,
                "snapshot_date": r.snapshot_date,
                "projected_round": r.projected_round,
                "projected_pick": r.projected_pick,
                "projected_team_id": team_id,
                "projected_team_name": r.projected_team_name,
                "overall_rank": r.overall_rank,
                "position_rank": r.position_rank,
                "confidence_note": r.confidence_note,
                "source_url": r.source_url,
                "raw_payload_json": r.raw,
            })

        # Drop the pid=0 rows — we only persist resolved players.
        keep = [row for row in db_rows if row["player_id"]]
        if keep:
            self.db.upsert_many(
                "player_draft_projection",
                keep,
                conflict_columns=["player_id", "source_name", "snapshot_date"],
            )
        log.info(
            "%s: fetched=%d resolved=%d upserted=%d",
            self.source_name, len(rows), resolved, len(keep),
        )
        return {"fetched": len(rows), "upserted": len(keep), "resolved": resolved}

    def _resolve_player_id(self, name: str | None) -> int | None:
        if not name:
            return None
        name = re.sub(r"\s+", " ", name).strip()
        row = self.db.query_one(
            "select player_id from players where lower(full_name) = lower(:n) limit 1",
            {"n": name},
        )
        return int(row["player_id"]) if row else None

    def _resolve_team_id(self, name: str | None) -> int | None:
        if not name:
            return None
        row = self.db.query_one(
            "select team_id from teams where lower(canonical_name) = lower(:n) or "
            "lower(school_name) = lower(:n) or lower(short_name) = lower(:n) limit 1",
            {"n": name},
        )
        return int(row["team_id"]) if row else None
