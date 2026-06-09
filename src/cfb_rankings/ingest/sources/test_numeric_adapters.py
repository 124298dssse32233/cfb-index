"""Offline parse-only tests for Tier A numeric adapters.

We don't hit the network here — each adapter's ``fetch()`` is called with a
hand-rolled fixture matching real API response shapes, and we assert that
``parse()`` produces the right source_observations rows + that ``write_rows``
deduplicates correctly.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.gdelt_volume import GdeltVolumeAdapter
from cfb_rankings.ingest.sources.numeric_base import NumericSourceAdapter
from cfb_rankings.ingest.sources.prediction_markets import KalshiAdapter, PolymarketAdapter
from cfb_rankings.ingest.sources.seatgeek import SeatGeekAdapter
from cfb_rankings.ingest.sources.spotify_charts import SpotifyChartsAdapter
from cfb_rankings.ingest.sources.wikipedia import WikipediaPageviewsAdapter


def _fresh_db() -> Database:
    tmp = Path(tempfile.mkdtemp()) / "numeric_test.db"
    db = Database(f"sqlite:///{tmp.as_posix()}")
    db.execute("""
        create table source_observations (
            source_observation_id integer primary key autoincrement,
            source_id text not null, entity_type text not null,
            entity_id text, entity_label text,
            observed_at_utc text not null, metric text not null,
            value_numeric real, value_text text, sample_window text,
            source_tier text, ingestion_adapter_version text,
            capture_url text, canonical_url text, raw_payload_json text,
            dedup_key text unique, created_at_utc text default current_timestamp
        )
    """)
    db.execute("""
        create table priority_teams (
            team_id integer primary key,
            wiki_team_page text, wiki_coach_page text, wiki_qb_page text,
            seatgeek_team_slug text, google_news_query text,
            youtube_team_channel_id text, youtube_fan_channels text
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


def test_numeric_base_write_and_dedup() -> None:
    db = _fresh_db()

    class X(NumericSourceAdapter):
        source_id = "test_src"
        adapter_version = "0.9"

        def fetch(self) -> Any:
            return None

        def parse(self, raw: Any) -> list[dict[str, Any]]:
            return []

    a = X(db)
    rows = [{
        "entity_type": "team", "entity_id": "1", "entity_label": "Alabama",
        "observed_at_utc": "2026-04-20T00:00:00Z",
        "metric": "pageviews", "value_numeric": 1234,
    }]
    assert a.write_rows(rows) == 1
    assert a.write_rows(rows) == 0  # dedup
    observed = db.query_one("select * from source_observations")
    assert observed["source_tier"] == "A"
    assert observed["source_id"] == "test_src"
    assert observed["ingestion_adapter_version"] == "0.9"
    assert observed["dedup_key"] is not None


def test_wikipedia_pageviews_parse() -> None:
    db = _fresh_db()
    db.execute(
        "insert into priority_teams (team_id, wiki_team_page) values (231, 'Alabama_Crimson_Tide_football')"
    )
    fixture = {
        "items": [
            {"timestamp": "2026041900", "views": 4201, "article": "Alabama_Crimson_Tide_football"},
            {"timestamp": "2026042000", "views": 6050, "article": "Alabama_Crimson_Tide_football"},
        ]
    }
    page = {"team_id": 231, "article": "Alabama_Crimson_Tide_football", "page_kind": "team"}
    adapter = WikipediaPageviewsAdapter(db)
    rows = adapter.parse([(page, fixture)])
    assert len(rows) == 2
    assert rows[0]["metric"] == "pageviews"
    assert rows[0]["entity_type"] == "wiki_team"
    assert rows[0]["value_numeric"] == 4201.0
    assert rows[0]["observed_at_utc"] == "2026-04-19T00:00:00Z"


def test_gdelt_parse() -> None:
    db = _fresh_db()
    fixture = {"timeline": [{"data": [
        {"date": "20260420T000000Z", "value": 42},
        {"date": "20260421T000000Z", "value": 61},
    ]}]}
    team = {"team_id": 231, "google_news_query": "Alabama Crimson Tide football"}
    adapter = GdeltVolumeAdapter(db)
    rows = adapter.parse([(team, fixture)])
    assert len(rows) == 2
    assert rows[0]["metric"] == "article_count"
    assert rows[0]["value_numeric"] == 42.0
    assert rows[0]["observed_at_utc"] == "2026-04-20T00:00:00Z"


def test_seatgeek_parse() -> None:
    db = _fresh_db()
    fixture = {"events": [{
        "id": 777,
        "title": "Alabama @ Georgia",
        "url": "https://seatgeek.com/events/777",
        "datetime_local": "2026-09-26T19:30:00",
        "stats": {"lowest_price": 185, "listing_count": 412},
    }]}
    adapter = SeatGeekAdapter(db, client_id="fake")
    rows = adapter.parse([({"team_id": 231, "seatgeek_team_slug": "alabama-crimson-tide-football"}, fixture)])
    metrics = {r["metric"]: r["value_numeric"] for r in rows}
    assert metrics["get_in_cents"] == 18500.0
    assert metrics["listing_count"] == 412.0


def test_kalshi_parse() -> None:
    db = _fresh_db()
    # Bypass seed loader by directly feeding parse
    import cfb_rankings.ingest.sources.prediction_markets as pm
    pm._load_contracts = lambda platform: [  # type: ignore[assignment]
        {"platform": "kalshi", "ticker": "KXCFBCHAMP-26", "label": "CFB Champ 2026"}
    ]
    fixture = {"market": {
        "ticker": "KXCFBCHAMP-26",
        "last_price": 18,
        "volume_24h": 52000,
    }}
    adapter = KalshiAdapter(db)
    rows = adapter.parse([({"ticker": "KXCFBCHAMP-26"}, fixture)])
    metrics = {r["metric"]: r["value_numeric"] for r in rows}
    assert metrics["last_price_cents"] == 18.0
    assert metrics["volume_usd"] == 52000.0


def test_kalshi_fetch_expands_event_into_markets() -> None:
    """An event ticker fans out into one (contract, market) pair per active
    market; settled/closed markets are dropped. Offline — http_get stubbed."""
    db = _fresh_db()
    import json as _json

    import cfb_rankings.ingest.sources.prediction_markets as pm
    pm._load_contracts = lambda platform: [  # type: ignore[assignment]
        {"platform": "kalshi", "ticker": "KXNCAAF-27", "label": "CFP Champ 2026-27"}
    ] if platform == "kalshi" else []

    event_payload = {"event": {"event_ticker": "KXNCAAF-27"}, "markets": [
        {"ticker": "KXNCAAF-27-OSU", "status": "active",
         "yes_sub_title": "Ohio St.", "last_price": 17, "volume_24h": 9000},
        {"ticker": "KXNCAAF-27-TEX", "status": "active",
         "yes_sub_title": "Texas", "last_price": None, "volume_24h": None},
        {"ticker": "KXNCAAF-27-OLD", "status": "settled",
         "yes_sub_title": "Defunct", "last_price": 1, "volume_24h": 5},
    ]}

    adapter = KalshiAdapter(db)
    adapter.http_get = lambda url, **kw: _json.dumps(event_payload).encode("utf-8")  # type: ignore[assignment]

    pairs = adapter.fetch()
    assert len(pairs) == 2  # settled market dropped
    rows = adapter.parse(pairs)
    by_metric = {(r["entity_id"], r["metric"]): r["value_numeric"] for r in rows}
    # Liquid market emits both price + volume; illiquid one emits nothing.
    assert by_metric[("KXNCAAF-27-OSU", "last_price_cents")] == 17.0
    assert by_metric[("KXNCAAF-27-OSU", "volume_usd")] == 9000.0
    assert not any(eid == "KXNCAAF-27-TEX" for eid, _ in by_metric)
    # Label carries the per-outcome sub_title.
    osu = next(r for r in rows if r["entity_id"] == "KXNCAAF-27-OSU")
    assert osu["entity_label"] == "CFP Champ 2026-27: Ohio St."


def test_polymarket_parse() -> None:
    db = _fresh_db()
    fixture = [{
        "slug": "cfb-2026-heisman",
        "question": "Will a QB win the 2026 Heisman?",
        "outcomePrices": ["0.72", "0.28"],
        "volume": 18500,
    }]
    adapter = PolymarketAdapter(db)
    rows = adapter.parse([({"slug": "cfb-2026-heisman", "label": "2026 Heisman QB?"}, fixture)])
    metrics = {r["metric"]: r["value_numeric"] for r in rows}
    assert abs(metrics["prob_yes"] - 0.72) < 1e-9
    assert metrics["volume_usd"] == 18500.0


def test_spotify_parse_filters_cfb() -> None:
    db = _fresh_db()
    fixture = {"playlists": {"items": [
        {"id": "pl1", "name": "Locked On College Football",
         "external_urls": {"spotify": "https://open.spotify.com/pl1"}},
        {"id": "pl2", "name": "NFL Hot Takes",
         "external_urls": {"spotify": "https://open.spotify.com/pl2"}},
        {"id": "pl3", "name": "The Paul Finebaum Show",
         "external_urls": {"spotify": "https://open.spotify.com/pl3"}},
    ]}}
    adapter = SpotifyChartsAdapter(db, client_id="x", client_secret="y")
    rows = adapter.parse(fixture)
    assert len(rows) == 2  # NFL filtered out
    assert rows[0]["value_numeric"] == 1.0  # rank #1
    assert rows[1]["value_numeric"] == 2.0


def test_run_writes_scrape_health_row_for_numeric() -> None:
    db = _fresh_db()
    db.execute(
        "insert into priority_teams (team_id, google_news_query) values (231, 'Alabama football')"
    )

    class FixtureGdelt(GdeltVolumeAdapter):
        def fetch(self):
            team = {"team_id": 231, "google_news_query": "Alabama football"}
            return [(team, {"timeline": [{"data": [
                {"date": "20260420T000000Z", "value": 5},
            ]}]})]

    result = FixtureGdelt(db).run()
    assert result.status == "ok"
    assert result.rows_inserted == 1
    health = db.query_one("select * from scrape_health where source_id='gdelt_volume'")
    assert health["status"] == "ok"


def test_auth_gated_adapter_missing_secret_skips_not_errors() -> None:
    """An auth-gated adapter with no secret must surface status='skipped'
    (graceful no-op, exit 0) — NOT 'error' (exit 1). Otherwise a progressive
    secrets rollout floods CI with red Xs for keys that simply aren't set yet."""
    import os

    prior = os.environ.pop("SEATGEEK_CLIENT_ID", None)
    try:
        db = _fresh_db()
        result = SeatGeekAdapter(db).run()  # no client_id arg, env var absent
        assert result.status == "skipped"
        assert result.rows_inserted == 0
        assert "AdapterConfigError" in (result.error_message or "")
        health = db.query_one("select * from scrape_health where source_id='seatgeek'")
        assert health["status"] == "skipped"
    finally:
        if prior is not None:
            os.environ["SEATGEEK_CLIENT_ID"] = prior
