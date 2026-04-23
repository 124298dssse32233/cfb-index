"""Parse-only tests for Bluesky adapters + Google News adapter."""
from __future__ import annotations

import tempfile
from pathlib import Path

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.bluesky import (
    BlueskyCuratedAdapter, BlueskyFeedsAdapter, BlueskyFirehoseAdapter,
    _row_from_bsky_post,
)
from cfb_rankings.ingest.sources.google_news import GoogleNewsAdapter

BSKY_FEED_FIXTURE = {
    "feed": [
        {
            "post": {
                "uri": "at://did:plc:abc/app.bsky.feed.post/xyz123",
                "author": {"handle": "beat.writer.bsky.social"},
                "record": {
                    "text": "Alabama named starting QB today",
                    "createdAt": "2026-04-20T14:05:00.000Z",
                    "langs": ["en"],
                },
            }
        }
    ]
}

GOOGLE_NEWS_RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>Alabama earns big transfer commit</title>
    <link>https://news.google.com/articles/xyz</link>
    <description>News body</description>
    <pubDate>Mon, 21 Apr 2026 09:00:00 +0000</pubDate>
    <guid>https://news.google.com/articles/xyz</guid>
  </item>
</channel></rss>"""


def _fresh_db() -> Database:
    tmp = Path(tempfile.mkdtemp()) / "bsky_gn_test.db"
    db = Database(f"sqlite:///{tmp.as_posix()}")
    db.execute("""
        create table conversation_documents (
            conversation_document_id integer primary key autoincrement,
            source_name text not null, source_document_id text not null,
            content_type text not null default 'post',
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
            target_type text, target_key text, target_label text, audience_bucket text
        )
    """)
    db.execute("""
        create table priority_teams (
            team_id integer primary key,
            bluesky_beat_handles text
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


def test_row_from_bsky_post_basic() -> None:
    post = BSKY_FEED_FIXTURE["feed"][0]["post"]
    row = _row_from_bsky_post(post, "bluesky_curated", "0.1.0")
    assert row is not None
    assert row["source_id"] == "bluesky_curated"
    assert row["source_tier"] == "B"
    assert row["body_text"] == "Alabama named starting QB today"
    assert row["external_created_at_utc"] == "2026-04-20T14:05:00Z"
    assert row["source_author_name"] == "beat.writer.bsky.social"
    assert "bsky.app/profile/beat.writer.bsky.social/post/xyz123" in row["capture_url"]
    assert row["author_identity_class"] == "pseudonymous"
    assert row["dedup_key"] is not None
    assert row["language_code"] == "en"


def test_row_from_bsky_skips_empty_text() -> None:
    empty_post = {
        "uri": "at://did/app.bsky.feed.post/abc",
        "record": {"text": "", "createdAt": "2026-01-01T00:00:00Z"},
        "author": {"handle": "x.bsky"},
    }
    assert _row_from_bsky_post(empty_post, "s", "0") is None


def test_bluesky_curated_parse_and_write() -> None:
    db = _fresh_db()
    adapter = BlueskyCuratedAdapter(db)
    rows = adapter.parse([("beat.writer.bsky.social", BSKY_FEED_FIXTURE)])
    assert len(rows) == 1
    assert rows[0]["source_id"] == "bluesky_curated"
    assert adapter.write_rows(rows) == 1
    assert adapter.write_rows(rows) == 0  # dedup


def test_bluesky_feeds_parse() -> None:
    db = _fresh_db()
    adapter = BlueskyFeedsAdapter(db, feed_uris=["at://did/app.bsky.feed.generator/x"])
    rows = adapter.parse([("at://did/x", BSKY_FEED_FIXTURE)])
    assert len(rows) == 1
    assert rows[0]["source_id"] == "bluesky_feeds"


def test_bluesky_firehose_event_filter() -> None:
    # Event → post shape conversion
    event = {
        "kind": "commit", "did": "did:plc:abc",
        "commit": {
            "collection": "app.bsky.feed.post",
            "operation": "create", "rkey": "xyz",
            "record": {"text": "just had lunch", "createdAt": "2026-04-20T14:05:00Z"},
        },
    }
    post = BlueskyFirehoseAdapter._event_to_post(event)
    assert post is not None
    assert "did:plc:abc" in post["uri"]
    # Keyword filter in consume() would reject "just had lunch" — we can't call
    # consume() without a live websocket, but we can verify the filter predicate.
    db = _fresh_db()
    adapter = BlueskyFirehoseAdapter(db, keywords=["heisman"])
    text = post["record"]["text"].lower()
    assert not any(kw in text for kw in adapter.keywords)
    # But a CFB-adjacent post should pass
    adapter2 = BlueskyFirehoseAdapter(db, keywords=["kickoff"])
    text2 = "alabama kickoff time announced"
    assert any(kw in text2.lower() for kw in adapter2.keywords)


def test_google_news_adapter_parses() -> None:
    db = _fresh_db()
    adapter = GoogleNewsAdapter(db, team_id=231, team_slug="alabama",
                                query="Alabama Crimson Tide football")
    rows = adapter.parse(GOOGLE_NEWS_RSS)
    assert len(rows) == 1
    assert rows[0]["source_id"] == "google_news_alabama"
    assert rows[0]["source_tier"] == "B"
    assert rows[0]["demographic_slice"] == "aggregated_press"
    assert rows[0]["author_identity_class"] == "verified_media"
