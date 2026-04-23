"""Smoke tests for the podcast + Finebaum adapters."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.podcasts_meta import PodcastsMetaAdapter, FinebaumAdapter


RSS = b"""<?xml version="1.0"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
<channel>
  <item>
    <title>Ep 100 - Spring Portal Recap</title>
    <link>https://example/ep100</link>
    <description>Recap of portal moves.</description>
    <pubDate>Mon, 21 Apr 2026 09:00:00 +0000</pubDate>
    <itunes:duration>45:12</itunes:duration>
    <enclosure url="https://cdn.example/ep100.mp3" type="audio/mpeg"/>
    <guid>ep100</guid>
  </item>
</channel></rss>"""


def _fresh_db() -> Database:
    tmp = Path(tempfile.mkdtemp()) / "p.db"
    db = Database(f"sqlite:///{tmp.as_posix()}")
    db.execute("""
        create table conversation_documents (
            conversation_document_id integer primary key autoincrement,
            source_name text not null, source_document_id text not null,
            content_type text not null default 'x',
            title_text text, body_text text,
            external_created_at_utc text not null,
            collected_at_utc text default current_timestamp,
            source_author_name text, source_url text, language_code text,
            is_deleted integer default 0, is_removed integer default 0,
            source_id text, source_tier text, author_identity_class text,
            capture_url text, canonical_url text, retention_policy text,
            ingestion_adapter_version text, dedup_key text, demographic_slice text,
            raw_payload_json text
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


def test_podcast_meta_parse_and_payload() -> None:
    db = _fresh_db()
    adapter = PodcastsMetaAdapter(db, show_slug="split_zone_duo",
                                  feed_url="https://example/feed")
    rows = adapter.parse(RSS)
    assert len(rows) == 1
    r = rows[0]
    assert r["source_id"] == "podcast_split_zone_duo"
    assert r["content_type"] == "podcast_episode"
    assert r["canonical_url"] == "https://cdn.example/ep100.mp3"
    assert r["demographic_slice"] == "podcast_listener"
    assert r["source_tier"] == "B"
    assert adapter.write_rows(rows) == 1
    doc = db.query_one("select raw_payload_json from conversation_documents")
    payload = json.loads(doc["raw_payload_json"])
    assert payload["duration"] == "45:12"
    assert payload["enclosure_url"] == "https://cdn.example/ep100.mp3"


def test_finebaum_is_tier_d_citation_only() -> None:
    db = _fresh_db()
    fb = FinebaumAdapter(db, feed_url="https://example/finebaum")
    rows = fb.parse(RSS)
    assert len(rows) == 1
    r = rows[0]
    assert r["source_id"] == "finebaum_rss"
    assert r["source_tier"] == "D"
    assert r["retention_policy"] == "citation_only"
    assert r["demographic_slice"] == "radio_listener"
