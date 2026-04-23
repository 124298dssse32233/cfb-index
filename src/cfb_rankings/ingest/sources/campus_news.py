"""Campus newspaper RSS adapter — TASK 4.2.

Uses :class:`BaseRssAdapter` to pull each priority_team's campus paper RSS and
materialize rows in ``conversation_documents`` with full STRATEGY §5 provenance.

For v1 we run one :class:`CampusNewsAdapter` instance per team; the per-team
RSS URL is read from ``priority_teams.campus_newspaper_feed``. Each instance
reports its own ``scrape_health`` row keyed on ``source_id = f"campus_{slug}"``.
The cohort aggregator will map these instances back to the ``campus_template``
row in ``source_registry`` for cohort weights (via the
TASK 6.1 source-instance loader that's still pending).
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Sequence

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.base import BaseRssAdapter

logger = logging.getLogger(__name__)

ADAPTER_VERSION = "0.1.0"


class CampusNewsAdapter(BaseRssAdapter):
    """One adapter instance per priority_teams row.

    Parameters
    ----------
    db: target database
    team_id: priority_teams.team_id the feed belongs to
    team_slug: short stable identifier used in source_id (e.g. "alabama")
    feed_url: RSS or Atom URL from priority_teams.campus_newspaper_feed
    """

    adapter_version = ADAPTER_VERSION
    min_seconds_between_requests = 1.0  # be polite to campus servers

    def __init__(self, db: Database, team_id: int, team_slug: str, feed_url: str) -> None:
        self.source_id = f"campus_{team_slug.lower()}"
        self.feed_url = feed_url
        self.team_id = team_id
        super().__init__(db)

    # ------------------------------------------------------------------
    # Parse — BaseRssAdapter already gives us xml.etree entries.
    # ------------------------------------------------------------------
    def row_from_entry(self, entry: Any) -> dict[str, Any] | None:
        atom = "{http://www.w3.org/2005/Atom}"

        title = entry.findtext("title") or entry.findtext(f"{atom}title")
        if not title:
            return None
        title = title.strip()

        # RSS <link> is text; Atom <link href="..."/>
        link = entry.findtext("link") or ""
        if not link:
            atom_link = entry.find(f"{atom}link")
            if atom_link is not None:
                link = atom_link.attrib.get("href", "")
        link = (link or "").strip()

        guid = (
            entry.findtext("guid")
            or entry.findtext(f"{atom}id")
            or link
            or title
        )

        # Published / updated date — RSS uses pubDate (RFC 822), Atom uses
        # published/updated (ISO 8601).
        pub_text = (
            entry.findtext("pubDate")
            or entry.findtext(f"{atom}published")
            or entry.findtext(f"{atom}updated")
        )
        created_at = _parse_date_any(pub_text)
        if created_at is None:
            # skip dateless entries — RSS required field, Atom too
            return None

        # Body: RSS description / content:encoded ; Atom summary / content
        body_raw = (
            entry.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
            or entry.findtext("description")
            or entry.findtext(f"{atom}summary")
            or entry.findtext(f"{atom}content")
            or ""
        )
        body_text = _strip_html(body_raw).strip()[:4000]  # cap per playbook

        author = (
            entry.findtext("author")
            or entry.findtext("{http://purl.org/dc/elements/1.1/}creator")
            or ""
        ).strip() or None

        source_document_id = f"campus:{self.source_id}:{guid}"
        dedup_basis = f"{self.source_id}|{guid}|{created_at.isoformat()}"
        dedup_key = hashlib.sha1(dedup_basis.encode("utf-8")).hexdigest()

        return {
            "source_id": self.source_id,
            "source_tier": "B",
            "source_name": self.source_id,
            "source_document_id": source_document_id,
            "content_type": "article",
            "title_text": title,
            "body_text": body_text or None,
            "external_created_at_utc": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_author_name": author,
            "author_identity_class": "verified_media",
            "source_url": link or None,
            "capture_url": link or self.feed_url,
            "canonical_url": link or None,
            "retention_policy": "raw_keep",
            "ingestion_adapter_version": self.adapter_version,
            "dedup_key": dedup_key,
            "demographic_slice": "campus_student",
            "language_code": "en",
            "is_deleted": 0,
            "is_removed": 0,
            "team_id": self.team_id,  # consumed by write_rows → doc_targets
        }

    # ------------------------------------------------------------------
    # Persist. Writes to conversation_documents + conversation_document_targets
    # using the pre-existing tables (no schema change needed).
    # ------------------------------------------------------------------
    def write_rows(self, rows: Sequence[dict[str, Any]]) -> int:
        written = 0
        for row in rows:
            team_id = row.pop("team_id", None)
            # Dedup: skip if this dedup_key already present
            existing = self.db.query_one(
                "select conversation_document_id from conversation_documents "
                "where dedup_key = :k",
                {"k": row["dedup_key"]},
            )
            if existing:
                continue
            self.db.execute(
                """
                insert into conversation_documents (
                    source_name, source_document_id, content_type, title_text, body_text,
                    external_created_at_utc, source_author_name, source_url, language_code,
                    is_deleted, is_removed,
                    source_id, source_tier, author_identity_class, capture_url,
                    canonical_url, retention_policy, ingestion_adapter_version,
                    dedup_key, demographic_slice
                ) values (
                    :source_name, :source_document_id, :content_type, :title_text, :body_text,
                    :external_created_at_utc, :source_author_name, :source_url, :language_code,
                    :is_deleted, :is_removed,
                    :source_id, :source_tier, :author_identity_class, :capture_url,
                    :canonical_url, :retention_policy, :ingestion_adapter_version,
                    :dedup_key, :demographic_slice
                )
                """,
                row,
            )
            if team_id is not None:
                doc_row = self.db.query_one(
                    "select conversation_document_id from conversation_documents "
                    "where dedup_key = :k", {"k": row["dedup_key"]},
                )
                if doc_row is not None:
                    self.db.execute(
                        """
                        insert into conversation_document_targets (
                            conversation_document_id, season_year, week,
                            team_id, target_type, target_key, target_label, audience_bucket
                        ) values (
                            :doc, :season, :week, :team, 'team', :tkey, :tlabel, 'local'
                        )
                        """,
                        {
                            "doc": doc_row["conversation_document_id"],
                            "season": _season_year_for(row["external_created_at_utc"]),
                            "week": _season_week_for(row["external_created_at_utc"]),
                            "team": team_id,
                            "tkey": f"team:{team_id}",
                            "tlabel": self.source_id,
                        },
                    )
            written += 1
        return written


# ---------------------- helpers ----------------------
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(raw: str) -> str:
    if not raw:
        return ""
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", raw))


def _parse_date_any(text: str | None) -> datetime | None:
    if not text:
        return None
    text = text.strip()
    # Try RFC 822 (RSS)
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        pass
    # Try ISO 8601 (Atom)
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    ):
        try:
            dt = datetime.strptime(text, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def _season_year_for(iso_ts: str) -> int:
    """College football season year: weeks before July 1 belong to the prior year's season."""
    dt = datetime.strptime(iso_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return dt.year if dt.month >= 7 else dt.year - 1


def _season_week_for(iso_ts: str) -> int:
    """Rough season week = (ISO week of year) - 31, clamped to [0, 40].

    This is a placeholder; the real `games` table has authoritative week numbers
    per (season, date) and the cohort aggregator can join through it later.
    """
    dt = datetime.strptime(iso_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    iso_week = int(dt.strftime("%V"))
    week = iso_week - 31
    return max(0, min(week, 40))


__all__ = ["CampusNewsAdapter"]
