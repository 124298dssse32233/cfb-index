"""DAO for the editions schema.

One dataclass per table; one fetch / upsert pair per dataclass. The active
edition is the most recent ``status='published'`` row, ordered by
publish_date descending.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from cfb_rankings.db import Database


@dataclass
class Edition:
    edition_slug: str
    edition_number: int
    volume: int
    publish_date: date
    theme_title: str
    theme_dek: str
    cover_viz_kind: str
    cover_viz_data: dict[str, Any]
    cover_essay_id: Optional[int]
    status: str
    published_at_utc: Optional[str]

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Edition":
        return cls(
            edition_slug=row["edition_slug"],
            edition_number=row["edition_number"],
            volume=row["volume"],
            publish_date=date.fromisoformat(row["publish_date"]),
            theme_title=row["theme_title"],
            theme_dek=row["theme_dek"],
            cover_viz_kind=row["cover_viz_kind"],
            cover_viz_data=json.loads(row["cover_viz_data_json"] or "{}"),
            cover_essay_id=row["cover_essay_id"],
            status=row["status"],
            published_at_utc=row["published_at_utc"],
        )


@dataclass
class EditionFeature:
    id: Optional[int]
    edition_slug: str
    feature_order: int
    feature_kind: str
    title: str
    dek: str
    body_markdown: str
    byline: str
    read_time_minutes: int
    storyline_thread_slug: Optional[str] = None
    canon_entry_slug: Optional[str] = None
    receipt_id: Optional[int] = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "EditionFeature":
        return cls(
            id=row["id"],
            edition_slug=row["edition_slug"],
            feature_order=row["feature_order"],
            feature_kind=row["feature_kind"],
            title=row["title"],
            dek=row["dek"],
            body_markdown=row["body_markdown"],
            byline=row["byline"],
            read_time_minutes=row["read_time_minutes"],
            storyline_thread_slug=row["storyline_thread_slug"],
            canon_entry_slug=row["canon_entry_slug"],
            receipt_id=row["receipt_id"],
        )


@dataclass
class EditionVoice:
    edition_slug: str
    source_slug: str
    role_label: str
    bio: str
    receipt_score_pct: Optional[int]
    receipt_score_label: Optional[str]
    takes_tracked: int
    voice_order: int = 0

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "EditionVoice":
        return cls(
            edition_slug=row["edition_slug"],
            source_slug=row["source_slug"],
            role_label=row["role_label"],
            bio=row["bio"],
            receipt_score_pct=row["receipt_score_pct"],
            receipt_score_label=row["receipt_score_label"],
            takes_tracked=row["takes_tracked"],
            voice_order=row["voice_order"],
        )


# ---------------- Fetch ----------------

def fetch_edition(db: Database, edition_slug: str) -> Optional[Edition]:
    row = db.query_one(
        "select * from editions where edition_slug = :slug",
        {"slug": edition_slug},
    )
    return Edition.from_row(row) if row else None


def fetch_active_edition(db: Database) -> Optional[Edition]:
    row = db.query_one(
        "select * from editions where status = 'published' "
        "order by publish_date desc, edition_number desc limit 1",
    )
    return Edition.from_row(row) if row else None


def list_editions(db: Database, status: Optional[str] = None) -> list[Edition]:
    if status:
        rows = db.query_all(
            "select * from editions where status = :status order by publish_date desc",
            {"status": status},
        )
    else:
        rows = db.query_all("select * from editions order by publish_date desc")
    return [Edition.from_row(r) for r in rows]


def fetch_edition_features(db: Database, edition_slug: str) -> list[EditionFeature]:
    rows = db.query_all(
        "select * from edition_features where edition_slug = :slug "
        "order by feature_order asc",
        {"slug": edition_slug},
    )
    return [EditionFeature.from_row(r) for r in rows]


def fetch_edition_voices(db: Database, edition_slug: str) -> list[EditionVoice]:
    rows = db.query_all(
        "select * from edition_voices where edition_slug = :slug "
        "order by voice_order asc, source_slug asc",
        {"slug": edition_slug},
    )
    return [EditionVoice.from_row(r) for r in rows]


# ---------------- Upsert ----------------

def upsert_edition(db: Database, edition: Edition) -> None:
    db.execute(
        """
        insert into editions (
            edition_slug, edition_number, volume, publish_date,
            theme_title, theme_dek, cover_viz_kind, cover_viz_data_json,
            cover_essay_id, status, published_at_utc, last_updated_utc
        ) values (
            :slug, :num, :vol, :date, :title, :dek, :viz_kind, :viz_data,
            :essay_id, :status, :published_at, current_timestamp
        )
        on conflict(edition_slug) do update set
            edition_number = excluded.edition_number,
            volume = excluded.volume,
            publish_date = excluded.publish_date,
            theme_title = excluded.theme_title,
            theme_dek = excluded.theme_dek,
            cover_viz_kind = excluded.cover_viz_kind,
            cover_viz_data_json = excluded.cover_viz_data_json,
            cover_essay_id = excluded.cover_essay_id,
            status = excluded.status,
            published_at_utc = excluded.published_at_utc,
            last_updated_utc = current_timestamp
        """,
        {
            "slug": edition.edition_slug,
            "num": edition.edition_number,
            "vol": edition.volume,
            "date": edition.publish_date.isoformat(),
            "title": edition.theme_title,
            "dek": edition.theme_dek,
            "viz_kind": edition.cover_viz_kind,
            "viz_data": json.dumps(edition.cover_viz_data),
            "essay_id": edition.cover_essay_id,
            "status": edition.status,
            "published_at": edition.published_at_utc,
        },
    )


def upsert_feature(db: Database, feature: EditionFeature) -> int:
    db.execute(
        """
        insert into edition_features (
            edition_slug, feature_order, feature_kind, title, dek,
            body_markdown, byline, read_time_minutes,
            storyline_thread_slug, canon_entry_slug, receipt_id
        ) values (
            :slug, :ord, :kind, :title, :dek, :body, :byline, :read_time,
            :thread, :canon, :receipt
        )
        on conflict(edition_slug, feature_order) do update set
            feature_kind = excluded.feature_kind,
            title = excluded.title,
            dek = excluded.dek,
            body_markdown = excluded.body_markdown,
            byline = excluded.byline,
            read_time_minutes = excluded.read_time_minutes,
            storyline_thread_slug = excluded.storyline_thread_slug,
            canon_entry_slug = excluded.canon_entry_slug,
            receipt_id = excluded.receipt_id
        """,
        {
            "slug": feature.edition_slug,
            "ord": feature.feature_order,
            "kind": feature.feature_kind,
            "title": feature.title,
            "dek": feature.dek,
            "body": feature.body_markdown,
            "byline": feature.byline,
            "read_time": feature.read_time_minutes,
            "thread": feature.storyline_thread_slug,
            "canon": feature.canon_entry_slug,
            "receipt": feature.receipt_id,
        },
    )
    row = db.query_one(
        "select id from edition_features where edition_slug = :slug "
        "and feature_order = :ord",
        {"slug": feature.edition_slug, "ord": feature.feature_order},
    )
    return int(row["id"]) if row else 0


def upsert_voice(db: Database, voice: EditionVoice) -> None:
    db.execute(
        """
        insert into edition_voices (
            edition_slug, source_slug, role_label, bio,
            receipt_score_pct, receipt_score_label, takes_tracked, voice_order
        ) values (
            :slug, :source, :role, :bio, :pct, :label, :tracked, :order
        )
        on conflict(edition_slug, source_slug) do update set
            role_label = excluded.role_label,
            bio = excluded.bio,
            receipt_score_pct = excluded.receipt_score_pct,
            receipt_score_label = excluded.receipt_score_label,
            takes_tracked = excluded.takes_tracked,
            voice_order = excluded.voice_order
        """,
        {
            "slug": voice.edition_slug,
            "source": voice.source_slug,
            "role": voice.role_label,
            "bio": voice.bio,
            "pct": voice.receipt_score_pct,
            "label": voice.receipt_score_label,
            "tracked": voice.takes_tracked,
            "order": voice.voice_order,
        },
    )
