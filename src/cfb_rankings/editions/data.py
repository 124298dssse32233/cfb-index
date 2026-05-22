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
    # Hotfix-13 — preserve status promotions and cover_essay_id linkage.
    #
    # Same race as upsert_feature (see below). The world_class_enrich
    # workflow's generate-edition-covers step promotes W18/W19 to
    # status='published' and stamps cover_essay_id. The NEXT workflow's
    # seed-editions step would call upsert_edition with the seed's
    # status='draft' and cover_essay_id=None, and ON CONFLICT was
    # overwriting them — demoting W18/W19 back to draft and dropping
    # the cover_essay_id pointer. The homepage's fetch_active_edition
    # (which filters on status='published') then stopped seeing them
    # and fell back to W17.
    #
    # Fix: in the ON CONFLICT update, never demote status (draft is the
    # only seed value; published once-set stays). Never overwrite a
    # set cover_essay_id with NULL. Title and dek follow the same
    # "preserve external writes" pattern as upsert_feature.
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
            -- Preserve cover_essay_id once it's been pointed at a real
            -- feature row. Seed sends NULL; Pattern C / publish-edition
            -- writer stamps the real id.
            cover_essay_id = coalesce(editions.cover_essay_id, excluded.cover_essay_id),
            -- Never demote status. The status ladder is one-way:
            -- draft → published. Re-seeding with status='draft' (the
            -- placeholder default) must not undo a previous promotion.
            status = case
                when editions.status = 'published' then 'published'
                else excluded.status
            end,
            published_at_utc = coalesce(editions.published_at_utc, excluded.published_at_utc),
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
    # Hotfix-13 — preserve Pattern C–generated dek + body_markdown across
    # subsequent seed-editions calls.
    #
    # Before this fix, ON CONFLICT was overwriting `dek` and `body_markdown`
    # with the seed payload's placeholder values on every re-seed. The
    # workflow ordering is:
    #   1. dawidd6-download artifact (has Pattern C 5890-char body for W19)
    #   2. seed-editions  → upsert_feature → ON CONFLICT resets dek+body
    #      back to "Cover essay scaffold — auto-filled by the Pattern C
    #      generator on the next world_class_enrich run" placeholder.
    #   3. render-edition reads the now-reset placeholder → article page
    #      ships with the placeholder text instead of the real essay.
    #
    # Symptom on the live site: /editions/2026-w19/three-weeks-before-camp
    # -whispers/ rendered to ~3.7KB of placeholder text even though the DB
    # had ~5.9KB of real essay content right before seed-editions ran.
    #
    # Fix: in the ON CONFLICT update, use `coalesce(nullif(existing,
    # placeholder), excluded)` semantics for content fields — keep the
    # existing value if it's non-empty AND not equal to the incoming seed
    # value. For dek and body_markdown specifically, prefer the existing
    # value when it differs from the new seed (indicating an external
    # writer like Pattern C has touched it).
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
            -- Preserve any externally-written dek/body (Pattern C, manual
            -- override, etc.). Only adopt the incoming seed when the
            -- existing value is empty/null. Equality with excluded is
            -- a no-op so this is safe for idempotent first-time seed.
            -- Session 5 addendum (2026-05-22): also overwrite when the
            -- existing value is a known dev-commentary placeholder. The
            -- original Hotfix-13 logic protected against re-seeding
            -- demoting Pattern C output to placeholder; the symmetric
            -- protection (re-seeding upgrading a placeholder to a
            -- better seed) was missing. Detection is conservative: only
            -- the exact "[Auto-generated content placeholder" prefix
            -- and the "Cover essay scaffold — auto-filled" prefix
            -- count as placeholders. Real essays never start that way.
            dek = case
                when coalesce(edition_features.dek, '') = '' then excluded.dek
                when edition_features.dek like 'Cover essay scaffold — auto-filled%' then excluded.dek
                -- Also catch dek strings that expose internal sprint /
                -- pattern identifiers ("Pattern C", "Pattern E", "Sprint 13").
                -- These shipped as authored deks but read as dev-vocab.
                when edition_features.dek like '%Pattern C %' then excluded.dek
                when edition_features.dek like '%Pattern E %' then excluded.dek
                when edition_features.dek like '%Sprint 1%' then excluded.dek
                else edition_features.dek
            end,
            body_markdown = case
                when coalesce(edition_features.body_markdown, '') = ''
                    then excluded.body_markdown
                when edition_features.body_markdown like '[Auto-generated content placeholder%'
                    then excluded.body_markdown
                -- Same internal-jargon detection on body_markdown.
                when edition_features.body_markdown like '%Pattern C cover essay generator%' then excluded.body_markdown
                when edition_features.body_markdown like '%Pattern E continuity loop%' then excluded.body_markdown
                when edition_features.body_markdown like '%world_class_enrich%' then excluded.body_markdown
                else edition_features.body_markdown
            end,
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
