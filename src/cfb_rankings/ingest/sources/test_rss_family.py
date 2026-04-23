"""Smoke tests for the thin RSS subclasses."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.rss_family import (
    AthleticsSiteAdapter, BeatWriterAdapter, LockedOnAdapter, SubstackAdapter,
)

RSS_FIXTURE = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>Sample article</title>
    <link>https://example.com/1</link>
    <description>body text</description>
    <pubDate>Mon, 20 Apr 2026 12:00:00 +0000</pubDate>
    <guid>https://example.com/1</guid>
  </item>
</channel></rss>"""


def _fresh_db() -> Database:
    tmp = Path(tempfile.mkdtemp()) / "rss_family_test.db"
    db = Database(f"sqlite:///{tmp.as_posix()}")
    db.execute("""
        create table conversation_documents (
            conversation_document_id integer primary key autoincrement,
            source_name text not null, source_document_id text not null,
            content_type text not null default 'article',
            title_text text, body_text text,
            external_created_at_utc text not null,
            collected_at_utc text not null default current_timestamp,
            source_author_name text, source_url text, language_code text,
            is_deleted integer not null default 0, is_removed integer not null default 0,
            source_id text, source_tier text, author_identity_class text,
            capture_url text, canonical_url text, retention_policy text,
            ingestion_adapter_version text, dedup_key text, demographic_slice text
        )
    """)
    db.execute("""
        create table conversation_document_targets (
            id integer primary key autoincrement,
            conversation_document_id integer,
            season_year integer, week integer, team_id integer,
            target_type text, target_key text, target_label text, audience_bucket text,
            sentiment_label text, sentiment_score real,
            emotion_primary text, emotion_secondary text,
            sarcasm_score real, toxicity_score real, confidence_score real,
            model_provider text, model_name text, model_version text
        )
    """)
    db.execute("""
        create table scrape_health (
            source_id text, run_date text, rows_inserted integer, status text,
            error_message text, run_started_at_utc text, run_finished_at_utc text,
            adapter_version text, primary key (source_id, run_date)
        )
    """)
    return db


def _run_through_parse(Adapter, expected_source_id: str, expected_slice: str,
                       expected_identity: str, expected_retention: str, **kwargs: Any) -> None:
    db = _fresh_db()
    adapter = Adapter(db, **kwargs)
    rows = adapter.parse(RSS_FIXTURE)
    assert len(rows) == 1
    r = rows[0]
    assert r["source_id"] == expected_source_id
    assert r["source_tier"] == "B"
    assert r["demographic_slice"] == expected_slice
    assert r["author_identity_class"] == expected_identity
    assert r["retention_policy"] == expected_retention
    # write + dedup smoke
    assert adapter.write_rows(rows) == 1
    assert adapter.write_rows(rows) == 0


def test_beat_writer_adapter_shape() -> None:
    _run_through_parse(
        BeatWriterAdapter, "beat_alabama_al_com_alabama",
        "media_adjacent", "verified_media", "raw_keep",
        team_id=231, team_slug="alabama", writer_slug="al_com_alabama",
        feed_url="https://example",
    )


def test_substack_adapter_shape() -> None:
    _run_through_parse(
        SubstackAdapter, "substack_split_zone_duo",
        "media_adjacent", "verified_media", "raw_keep",
        team_id=None, writer_slug="split_zone_duo",
        feed_url="https://example",
    )


def test_athletics_adapter_shape() -> None:
    _run_through_parse(
        AthleticsSiteAdapter, "athletics_alabama",
        "institutional_press", "official", "raw_keep",
        team_id=231, team_slug="alabama", feed_url="https://example",
    )


def test_locked_on_adapter_shape() -> None:
    db = _fresh_db()
    adapter = LockedOnAdapter(db, team_id=231, team_slug="alabama",
                              feed_url="https://example")
    rows = adapter.parse(RSS_FIXTURE)
    assert len(rows) == 1
    r = rows[0]
    assert r["source_id"] == "locked_on_alabama"
    assert r["content_type"] == "podcast_episode"
    assert r["retention_policy"] == "aggregated_only"
