"""Thin RSS subclasses for Week 4 bulk adapters — TASK 4.1, 4.3, 4.4, 4.5.

Every Week 4 bulk RSS adapter shares the ``CampusNewsAdapter`` lifecycle:
parse RSS/Atom, strip HTML, compute dedup_key, write to
``conversation_documents`` (plus a targets row). The only per-family
differences are:

- ``source_id`` naming convention
- ``demographic_slice``
- ``author_identity_class``
- ``retention_policy``

We inherit from ``CampusNewsAdapter`` and override those class-level
constants / the ``row_from_entry`` overlay. Per-team seed files
(``seeds/beat_writer_feeds.yaml`` etc.) drive construction.
"""
from __future__ import annotations

import json
from typing import Any, Sequence

from cfb_rankings.ingest.sources.campus_news import CampusNewsAdapter


class BeatWriterAdapter(CampusNewsAdapter):
    """Beat-writer RSS — TASK 4.1. One instance per beat per team."""

    def __init__(self, db, team_id: int, team_slug: str, writer_slug: str, feed_url: str) -> None:
        self.source_id = f"beat_{team_slug.lower()}_{writer_slug.lower()}"
        self.feed_url = feed_url
        self.team_id = team_id
        # call grandparent init to avoid CampusNewsAdapter's source_id build
        from cfb_rankings.ingest.sources.base import BaseRssAdapter
        BaseRssAdapter.__init__(self, db)

    def row_from_entry(self, entry: Any) -> dict[str, Any] | None:
        row = super().row_from_entry(entry)
        if row is None:
            return None
        row.update({
            "source_id": self.source_id,
            "author_identity_class": "verified_media",
            "demographic_slice": "media_adjacent",
            "retention_policy": "raw_keep",
        })
        return row


class SubstackAdapter(CampusNewsAdapter):
    """CFB Substack RSS — TASK 4.3."""

    def __init__(self, db, team_id: int | None, writer_slug: str, feed_url: str) -> None:
        self.source_id = f"substack_{writer_slug.lower()}"
        self.feed_url = feed_url
        self.team_id = team_id
        from cfb_rankings.ingest.sources.base import BaseRssAdapter
        BaseRssAdapter.__init__(self, db)

    def row_from_entry(self, entry: Any) -> dict[str, Any] | None:
        row = super().row_from_entry(entry)
        if row is None:
            return None
        row.update({
            "source_id": self.source_id,
            "author_identity_class": "verified_media",
            "demographic_slice": "media_adjacent",
            "retention_policy": "raw_keep",
        })
        return row


class AthleticsSiteAdapter(CampusNewsAdapter):
    """School athletic department press RSS — TASK 4.4."""

    def __init__(self, db, team_id: int, team_slug: str, feed_url: str) -> None:
        self.source_id = f"athletics_{team_slug.lower()}"
        self.feed_url = feed_url
        self.team_id = team_id
        from cfb_rankings.ingest.sources.base import BaseRssAdapter
        BaseRssAdapter.__init__(self, db)

    def row_from_entry(self, entry: Any) -> dict[str, Any] | None:
        row = super().row_from_entry(entry)
        if row is None:
            return None
        row.update({
            "source_id": self.source_id,
            "author_identity_class": "official",
            "demographic_slice": "institutional_press",
            "retention_policy": "raw_keep",
        })
        return row


class LockedOnAdapter(CampusNewsAdapter):
    """Locked On team-daily podcast RSS metadata — TASK 4.5.

    Metadata only — no audio download, no transcription by default. Selective
    Whisper ASR is triggered separately by :mod:`tools.transcribe_episode`.
    """

    def __init__(self, db, team_id: int, team_slug: str, feed_url: str) -> None:
        self.source_id = f"locked_on_{team_slug.lower()}"
        self.feed_url = feed_url
        self.team_id = team_id
        from cfb_rankings.ingest.sources.base import BaseRssAdapter
        BaseRssAdapter.__init__(self, db)

    def row_from_entry(self, entry: Any) -> dict[str, Any] | None:
        row = super().row_from_entry(entry)
        if row is None:
            return None
        # Capture the audio <enclosure url="..."> so the Whisper ASR step can
        # find something to transcribe. Without this, collect-podcast-transcripts
        # selects `where raw_payload_json like '%enclosure_url%'` and matches 0
        # rows — the cause of episodes=0 (2026-06-10). Stashed under a non-column
        # key that write_rows() pops and folds into raw_payload_json.
        enc = entry.find("enclosure")
        enclosure_url = enc.attrib.get("url") if enc is not None else None
        row.update({
            "source_id": self.source_id,
            "author_identity_class": "verified_media",
            "demographic_slice": "podcast_listener",
            "retention_policy": "aggregated_only",
            "content_type": "podcast_episode",
            "raw_payload_enclosure_url": enclosure_url,
        })
        return row

    def write_rows(self, rows: Sequence[dict[str, Any]]) -> int:
        """Persist via the parent (doc + per-team target + sentiment), then fold
        the enclosure URL into raw_payload_json. We (re)write the payload even
        for already-present dedup_keys so the back catalogue collected before
        this fix gets backfilled and becomes transcribable on the next run."""
        written = 0
        for row in rows:
            enclosure_url = row.pop("raw_payload_enclosure_url", None)
            written += super().write_rows([row])
            if enclosure_url:
                self.db.execute(
                    "update conversation_documents set raw_payload_json = :p "
                    "where dedup_key = :k",
                    {"p": json.dumps({"enclosure_url": enclosure_url}, sort_keys=True),
                     "k": row["dedup_key"]},
                )
        return written


__all__ = ["BeatWriterAdapter", "SubstackAdapter", "AthleticsSiteAdapter", "LockedOnAdapter"]
