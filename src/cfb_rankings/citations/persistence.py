"""Persistence layer for the editorial_citations table.

The DDL is also in migrations/20260601_01_editorial_citations.sql.
``CITATION_DDL`` is re-exported here so callers running against an
ephemeral in-memory DB can create the table without applying the full
migration history (used by tests).

Public functions:
  * persist_citations(db, generation_id, citations) — upsert by
      (generation_id, marker_id). Idempotent; re-running a generation
      replaces its citation rows rather than duplicating.
  * load_citations(db, generation_id) — returns sorted Citations.
"""

from __future__ import annotations

import logging as _log
import sqlite3
from typing import TYPE_CHECKING, Iterable

from .types import Citation, citation_from_row

if TYPE_CHECKING:
    from ..db import Database


log = _log.getLogger(__name__)


CITATION_DDL = """
CREATE TABLE IF NOT EXISTS editorial_citations (
    citation_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    generation_id   INTEGER NOT NULL,
    marker_id       INTEGER NOT NULL,
    source_kind     TEXT NOT NULL CHECK (source_kind IN (
        'reddit', 'beat_writer', 'podcast', 'wikipedia',
        'official', 'cfbd', 'wire', 'edition'
    )),
    source_url      TEXT,
    source_label    TEXT NOT NULL,
    source_date     TEXT,
    confidence      TEXT NOT NULL CHECK (confidence IN (
        'primary', 'supporting', 'background'
    )),
    created_at_utc  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (generation_id, marker_id)
)
"""


def persist_citations(
    db: "Database",
    generation_id: int,
    citations: Iterable[Citation],
) -> int:
    """Upsert the citation rows for one generation.

    Returns the number of rows written. Idempotent on
    (generation_id, marker_id) — re-running with the same generation_id
    replaces the prior citation set.

    OperationalError (e.g. missing table) is logged + returns 0 so a
    caller running before the migration applies degrades gracefully.
    """
    rows = list(citations)
    if not rows:
        return 0
    try:
        # Wipe existing rows for this generation_id before inserting the
        # new set, so re-runs don't double-write or leave stale markers.
        db.execute(
            "DELETE FROM editorial_citations WHERE generation_id = ?",
            (generation_id,),
        )
        for c in rows:
            db.execute(
                """
                INSERT INTO editorial_citations
                  (generation_id, marker_id, source_kind, source_url,
                   source_label, source_date, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generation_id,
                    c.marker_id,
                    c.source_kind,
                    c.source_url,
                    c.source_label,
                    c.source_date,
                    c.confidence,
                ),
            )
    except sqlite3.OperationalError as e:
        log.warning(
            "persist_citations(generation_id=%s) failed: %s",
            generation_id, e,
        )
        return 0
    return len(rows)


def load_citations(
    db: "Database",
    generation_id: int,
) -> list[Citation]:
    """Load all citations for a generation, sorted by marker_id.

    Returns an empty list when the table is missing or no rows match.
    """
    try:
        rows = db.query_all(
            """
            SELECT citation_id, generation_id, marker_id, source_kind,
                   source_url, source_label, source_date, confidence
            FROM editorial_citations
            WHERE generation_id = ?
            ORDER BY marker_id ASC
            """,
            (generation_id,),
        )
    except sqlite3.OperationalError:
        return []
    return [citation_from_row(r) for r in rows]


__all__ = ["CITATION_DDL", "persist_citations", "load_citations"]
