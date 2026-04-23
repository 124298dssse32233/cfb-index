"""Unit tests for CampusNewsAdapter.

Uses fixture RSS + Atom payloads (no live network). Verifies parse, dedup,
write_rows, and scrape_health integration end-to-end against an ephemeral
SQLite DB that mimics the relevant bits of production schema.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.campus_news import (
    CampusNewsAdapter,
    _parse_date_any,
    _season_year_for,
    _season_week_for,
)

RSS_FIXTURE = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>The Crimson White</title>
    <link>https://cw.ua.edu/</link>
    <description>Alabama's student newspaper</description>
    <item>
      <title>Saban steps in as advisor</title>
      <link>https://cw.ua.edu/1001/saban-steps-in</link>
      <description>&lt;p&gt;Nick Saban returned today as an informal advisor...&lt;/p&gt;</description>
      <pubDate>Mon, 20 Apr 2026 14:05:00 +0000</pubDate>
      <author>reporter@cw.ua.edu (Jane Student)</author>
      <guid>https://cw.ua.edu/1001/saban-steps-in</guid>
    </item>
    <item>
      <title>Bryant-Denny renovation timeline</title>
      <link>https://cw.ua.edu/1002/bryant-denny</link>
      <description>Updated timeline for the Bryant-Denny renovation...</description>
      <pubDate>Sun, 19 Apr 2026 09:30:00 +0000</pubDate>
      <guid>https://cw.ua.edu/1002/bryant-denny</guid>
    </item>
    <item>
      <title>No date entry should be skipped</title>
      <link>https://cw.ua.edu/no-date</link>
      <description>body</description>
    </item>
  </channel>
</rss>"""

ATOM_FIXTURE = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Feed</title>
  <entry>
    <id>https://example.edu/articles/42</id>
    <title>Starting QB named for spring</title>
    <link href="https://example.edu/articles/42"/>
    <published>2026-04-21T12:00:00Z</published>
    <summary>Head coach announced the starting QB today.</summary>
  </entry>
</feed>"""


def _fresh_db() -> Database:
    tmp = Path(tempfile.mkdtemp()) / "campus_test.db"
    db = Database(f"sqlite:///{tmp.as_posix()}")
    # Minimal schemas just for this test
    db.execute("""
        create table conversation_documents (
            conversation_document_id integer primary key autoincrement,
            source_name text not null,
            source_document_id text not null,
            content_type text not null default 'article',
            title_text text,
            body_text text,
            external_created_at_utc text not null,
            collected_at_utc text not null default current_timestamp,
            source_author_name text,
            source_url text,
            language_code text,
            is_deleted integer not null default 0,
            is_removed integer not null default 0,
            source_id text, source_tier text, author_identity_class text,
            capture_url text, canonical_url text, retention_policy text,
            ingestion_adapter_version text, dedup_key text, demographic_slice text
        )
    """)
    db.execute("create index idx_dedup on conversation_documents(dedup_key)")
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
            adapter_version text,
            primary key (source_id, run_date)
        )
    """)
    return db


def test_parse_rss_produces_two_rows_one_skipped() -> None:
    db = _fresh_db()
    adapter = CampusNewsAdapter(db, team_id=231, team_slug="alabama",
                                feed_url="https://example/feed")
    rows = adapter.parse(RSS_FIXTURE)
    assert len(rows) == 2  # the no-date entry is skipped
    first = rows[0]
    assert first["source_id"] == "campus_alabama"
    assert first["source_tier"] == "B"
    assert first["title_text"] == "Saban steps in as advisor"
    assert "advisor" in first["body_text"]
    assert first["source_url"] == "https://cw.ua.edu/1001/saban-steps-in"
    assert first["external_created_at_utc"] == "2026-04-20T14:05:00Z"
    assert first["author_identity_class"] == "verified_media"
    assert first["demographic_slice"] == "campus_student"
    assert first["retention_policy"] == "raw_keep"
    # dedup key is deterministic
    assert len(first["dedup_key"]) == 40


def test_parse_atom_entry() -> None:
    db = _fresh_db()
    adapter = CampusNewsAdapter(db, team_id=1, team_slug="ex",
                                feed_url="https://example/feed")
    rows = adapter.parse(ATOM_FIXTURE)
    assert len(rows) == 1
    row = rows[0]
    assert row["title_text"] == "Starting QB named for spring"
    assert row["source_url"] == "https://example.edu/articles/42"
    assert row["external_created_at_utc"] == "2026-04-21T12:00:00Z"


def test_write_rows_inserts_docs_and_targets() -> None:
    db = _fresh_db()
    adapter = CampusNewsAdapter(db, team_id=231, team_slug="alabama",
                                feed_url="https://example/feed")
    rows = adapter.parse(RSS_FIXTURE)
    n = adapter.write_rows(rows)
    assert n == 2
    docs = db.query_all("select * from conversation_documents")
    assert len(docs) == 2
    for d in docs:
        assert d["source_id"] == "campus_alabama"
        assert d["capture_url"] is not None
        assert d["dedup_key"] is not None
    targets = db.query_all("select * from conversation_document_targets")
    assert len(targets) == 2
    for t in targets:
        assert t["team_id"] == 231
        assert t["target_type"] == "team"


def test_write_rows_is_idempotent_on_dedup_key() -> None:
    db = _fresh_db()
    adapter = CampusNewsAdapter(db, team_id=231, team_slug="alabama",
                                feed_url="https://example/feed")
    rows = adapter.parse(RSS_FIXTURE)
    adapter.write_rows(rows)
    # Simulate second run: re-parse same RSS, re-write, no duplicates
    rows2 = adapter.parse(RSS_FIXTURE)
    n2 = adapter.write_rows(rows2)
    assert n2 == 0
    doc_count = db.query_one("select count(*) as n from conversation_documents")["n"]
    assert doc_count == 2


def test_run_writes_scrape_health_row() -> None:
    db = _fresh_db()

    class FixtureAdapter(CampusNewsAdapter):
        def fetch(self):
            return RSS_FIXTURE

    adapter = FixtureAdapter(db, team_id=231, team_slug="alabama",
                             feed_url="https://example/feed")
    result = adapter.run()
    assert result.status == "ok"
    assert result.rows_inserted == 2
    health = db.query_one(
        "select * from scrape_health where source_id = 'campus_alabama'"
    )
    assert health["status"] == "ok"
    assert health["rows_inserted"] == 2
    assert health["adapter_version"] == "0.1.0"


def test_season_year_rollover() -> None:
    assert _season_year_for("2026-04-20T14:05:00Z") == 2025  # spring → prior season
    assert _season_year_for("2026-09-15T14:05:00Z") == 2026  # fall → current season


def test_season_week_clamps() -> None:
    # January is deep offseason — week clamped to 0
    assert _season_week_for("2026-01-15T00:00:00Z") == 0
    # Late November — CFB regular season week ~14 to conference-champ week ~17
    week = _season_week_for("2026-11-25T00:00:00Z")
    assert 12 <= week <= 20


def test_parse_date_rfc822_and_iso() -> None:
    assert _parse_date_any("Mon, 20 Apr 2026 14:05:00 +0000") is not None
    assert _parse_date_any("2026-04-20T14:05:00Z") is not None
    assert _parse_date_any("2026-04-20T14:05:00+00:00") is not None
    assert _parse_date_any(None) is None
    assert _parse_date_any("") is None
    assert _parse_date_any("not a date") is None
