"""Podcast RSS metadata adapter — TASK 7.1.

One instance per tracked show. Metadata only (title, description, duration,
chapters, enclosure URL). No transcription happens here; Whisper ASR is a
separate, deliberate step via :mod:`tools.transcribe_episode` (TASK 7.2).

Shows are listed in ``seeds/podcast_feeds.yaml`` (file created here).
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Sequence

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.base import BaseRssAdapter

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


class PodcastsMetaAdapter(BaseRssAdapter):
    """Generic podcast metadata fetcher."""

    adapter_version = "0.1.0"
    min_seconds_between_requests = 1.0

    def __init__(self, db: Database, show_slug: str, feed_url: str,
                 tier: str = "B") -> None:
        self.source_id = f"podcast_{show_slug.lower()}"
        self.feed_url = feed_url
        self.tier = tier
        super().__init__(db)

    def row_from_entry(self, entry: Any) -> dict[str, Any] | None:
        atom = "{http://www.w3.org/2005/Atom}"
        itunes = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
        title = entry.findtext("title") or entry.findtext(f"{atom}title")
        if not title:
            return None
        link = entry.findtext("link") or ""
        pub = (
            entry.findtext("pubDate")
            or entry.findtext(f"{atom}published")
            or entry.findtext(f"{atom}updated")
        )
        created_at = _parse_date(pub)
        if created_at is None:
            return None
        summary = (
            entry.findtext(f"{itunes}summary")
            or entry.findtext("description")
            or entry.findtext(f"{atom}summary")
            or ""
        )
        duration = entry.findtext(f"{itunes}duration") or ""
        enclosure_url = None
        enc = entry.find("enclosure")
        if enc is not None:
            enclosure_url = enc.attrib.get("url")
        guid = entry.findtext("guid") or link or title
        dedup = hashlib.sha1(
            f"{self.source_id}|{guid}|{created_at.isoformat()}".encode()
        ).hexdigest()
        return {
            "source_id": self.source_id,
            "source_tier": self.tier,
            "source_name": self.source_id,
            "source_document_id": f"podcast:{self.source_id}:{guid}",
            "content_type": "podcast_episode",
            "title_text": title.strip(),
            "body_text": _WS_RE.sub(" ", _TAG_RE.sub(" ", summary)).strip()[:4000] or None,
            "external_created_at_utc": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_author_name": None,
            "author_identity_class": "verified_media",
            "source_url": link or self.feed_url,
            "capture_url": link or self.feed_url,
            "canonical_url": enclosure_url or link or self.feed_url,
            "retention_policy": "aggregated_only",
            "ingestion_adapter_version": self.adapter_version,
            "dedup_key": dedup,
            "demographic_slice": "podcast_listener",
            "language_code": "en",
            "is_deleted": 0,
            "is_removed": 0,
            "raw_payload_duration": duration,
            "raw_payload_enclosure_url": enclosure_url,
        }

    def write_rows(self, rows: Sequence[dict[str, Any]]) -> int:
        written = 0
        for row in rows:
            # Strip non-column keys
            duration = row.pop("raw_payload_duration", None)
            enclosure = row.pop("raw_payload_enclosure_url", None)
            existing = self.db.query_one(
                "select conversation_document_id from conversation_documents where dedup_key = :k",
                {"k": row["dedup_key"]},
            )
            if existing:
                continue
            self.db.execute(
                """
                insert into conversation_documents (
                    source_name, source_document_id, content_type, title_text, body_text,
                    external_created_at_utc, source_url, language_code,
                    is_deleted, is_removed,
                    source_id, source_tier, author_identity_class, capture_url,
                    canonical_url, retention_policy, ingestion_adapter_version,
                    dedup_key, demographic_slice
                ) values (
                    :source_name, :source_document_id, :content_type, :title_text, :body_text,
                    :external_created_at_utc, :source_url, :language_code,
                    :is_deleted, :is_removed,
                    :source_id, :source_tier, :author_identity_class, :capture_url,
                    :canonical_url, :retention_policy, :ingestion_adapter_version,
                    :dedup_key, :demographic_slice
                )
                """,
                {k: v for k, v in row.items() if not k.startswith("_")},
            )
            # Store duration/enclosure in raw_payload_json for retrieval
            self.db.execute(
                """
                update conversation_documents
                set raw_payload_json = :payload
                where dedup_key = :k
                """,
                {
                    "payload": _json_str({"duration": duration, "enclosure_url": enclosure}),
                    "k": row["dedup_key"],
                },
            )
            written += 1
        return written


class FinebaumAdapter(PodcastsMetaAdapter):
    """Paul Finebaum Show — ESPN/SiriusXM — Tier D citation-only (TASK 7.3)."""

    adapter_version = "0.1.0"

    def __init__(self, db: Database, feed_url: str) -> None:
        self.source_id = "finebaum_rss"
        self.feed_url = feed_url
        self.tier = "D"
        from cfb_rankings.ingest.sources.base import BaseRssAdapter
        BaseRssAdapter.__init__(self, db)

    def row_from_entry(self, entry: Any) -> dict[str, Any] | None:
        row = super().row_from_entry(entry)
        if row is None:
            return None
        row.update({
            "source_id": self.source_id,
            "source_tier": "D",
            "source_name": self.source_id,
            "demographic_slice": "radio_listener",
            "retention_policy": "citation_only",
        })
        return row


def _parse_date(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            dt = datetime.strptime(text, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def _json_str(obj: Any) -> str:
    import json
    return json.dumps(obj, sort_keys=True)


__all__ = ["PodcastsMetaAdapter", "FinebaumAdapter"]
