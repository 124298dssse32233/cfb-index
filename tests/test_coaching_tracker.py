"""Tests for src/cfb_rankings/ingest/sources/coaching_tracker.py.

Covers:
- Mocked feedparser w/ coaching headline -> persisted
- Mocked feedparser w/ non-coaching headline -> filtered (NOT persisted)
- Network error path -> graceful, errors counter incremented, no raise
- Dedup: same entry pulled twice -> single row
- Smoke import test

All tests use in-memory sqlite (no fixtures touch disk meaningfully) and
mock both ``feedparser.parse`` and ``requests.get``. NO real network.

Note: feedparser/requests/bs4 are runtime deps of the adapter (declared in
pyproject.toml under hotfix-2). To keep the test suite green on minimal
environments we register stub ``feedparser`` / ``bs4`` modules in
``sys.modules`` when the real packages aren't installed.
"""
from __future__ import annotations

import sqlite3
import sys
import time
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


def _ensure_stub_feedparser() -> Any:
    """Return a feedparser-compatible module, creating a stub if missing."""
    try:
        import feedparser  # noqa: F401
        return sys.modules["feedparser"]
    except ImportError:
        stub = types.ModuleType("feedparser")
        stub.parse = lambda *_a, **_kw: SimpleNamespace(entries=[], bozo=0)  # type: ignore[attr-defined]
        sys.modules["feedparser"] = stub
        return stub


def _ensure_stub_bs4() -> Any:
    """Return a bs4-compatible module, creating a stub if missing.

    The stub's BeautifulSoup returns an object whose ``find_all`` returns
    an empty list, which is the behaviour our 247sports parser tolerates.
    """
    try:
        import bs4  # noqa: F401
        return sys.modules["bs4"]
    except ImportError:
        stub = types.ModuleType("bs4")

        class _Stub:
            def __init__(self, *_a: Any, **_kw: Any) -> None:
                pass

            def find_all(self, *_a: Any, **_kw: Any) -> list[Any]:
                return []

        stub.BeautifulSoup = _Stub  # type: ignore[attr-defined]
        sys.modules["bs4"] = stub
        return stub


# Pre-register stubs so the adapter's lazy ``import feedparser`` / ``from bs4``
# resolve in environments where those packages aren't installed.
_ensure_stub_feedparser()
_ensure_stub_bs4()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _build_schema(conn: sqlite3.Connection) -> None:
    """Create the minimal subset of the production schema we exercise."""
    conn.executescript(
        """
        CREATE TABLE teams (
            team_id INTEGER PRIMARY KEY,
            slug TEXT NOT NULL,
            canonical_name TEXT NOT NULL,
            short_name TEXT,
            school_name TEXT,
            level_code TEXT
        );
        CREATE TABLE coaching_changes (
            coaching_change_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER,
            team_slug TEXT NOT NULL,
            coach_name TEXT NOT NULL,
            role TEXT NOT NULL,
            change_type TEXT NOT NULL,
            announced_date TEXT NOT NULL,
            summary TEXT NOT NULL,
            issue_number TEXT,
            sources_json TEXT NOT NULL DEFAULT '[]',
            ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_coaching_changes_lookup
            ON coaching_changes (team_slug, announced_date, coach_name);

        CREATE TABLE wire_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            occurred_at DATETIME NOT NULL,
            program_slug TEXT,
            program_display TEXT NOT NULL,
            actor_kind TEXT NOT NULL,
            action TEXT NOT NULL,
            why_it_matters TEXT NOT NULL,
            impact_label TEXT NOT NULL,
            impact_color TEXT NOT NULL,
            historical_comp TEXT,
            source_kind TEXT NOT NULL,
            source_url TEXT,
            source_name TEXT,
            related_thread_slug TEXT,
            fan_intel_velocity_spike INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX idx_wire_dedupe
            ON wire_entries(program_slug, action, date(occurred_at));
        """
    )
    conn.execute(
        "INSERT INTO teams (team_id, slug, canonical_name, short_name, level_code) "
        "VALUES (?, ?, ?, ?, ?)",
        (1, "michigan", "Michigan", "Michigan", "FBS"),
    )
    conn.commit()


@pytest.fixture()
def db(tmp_path: Path) -> Any:
    """Return a ``cfb_rankings.db.Database`` pointed at a fresh sqlite file."""
    from cfb_rankings.db import Database

    db_path = tmp_path / "coaching_tracker_test.db"
    conn = sqlite3.connect(db_path)
    _build_schema(conn)
    conn.close()
    return Database(f"sqlite:///{db_path.as_posix()}")


def _fake_struct_time(dt: datetime) -> time.struct_time:
    return time.struct_time(
        (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, 0, 0, 0)
    )


def _make_entry(title: str, link: str = "https://footballscoop.com/x", *,
                published: datetime | None = None) -> SimpleNamespace:
    published = published or datetime.now(tz=timezone.utc) - timedelta(hours=2)
    return SimpleNamespace(
        title=title,
        link=link,
        summary=title,
        description=title,
        published_parsed=_fake_struct_time(published),
        updated_parsed=None,
    )


def _make_feed(entries: list[SimpleNamespace]) -> SimpleNamespace:
    return SimpleNamespace(entries=entries, bozo=0)


def _empty_247_response() -> SimpleNamespace:
    return SimpleNamespace(
        status_code=200,
        text="<html><body></body></html>",
        raise_for_status=lambda: None,
    )


# ---------------------------------------------------------------------------
# Smoke import
# ---------------------------------------------------------------------------


def test_smoke_import() -> None:
    """Module imports cleanly and exposes the public entry point."""
    from cfb_rankings.ingest.sources import coaching_tracker

    assert callable(coaching_tracker.fetch_coaching_news)
    assert "hired" in coaching_tracker.COACH_KEYWORDS
    assert coaching_tracker.FOOTBALLSCOOP_RSS.startswith("https://")


# ---------------------------------------------------------------------------
# Keyword match + persistence
# ---------------------------------------------------------------------------


def test_coaching_headline_persists(monkeypatch: pytest.MonkeyPatch, db: Any) -> None:
    """A coaching headline pulled from Footballscoop RSS is persisted."""
    feedparser = sys.modules["feedparser"]
    import requests

    from cfb_rankings.ingest.sources import coaching_tracker

    feed = _make_feed([
        _make_entry("Michigan hired Kyle Whittingham as head coach"),
    ])
    monkeypatch.setattr(feedparser, "parse", lambda *_a, **_kw: feed)
    monkeypatch.setattr(requests, "get", lambda *_a, **_kw: _empty_247_response())

    counter = coaching_tracker.fetch_coaching_news(db, days=14)

    assert counter["fetched"] >= 1
    assert counter["matched_keyword"] >= 1
    assert counter["persisted"] == 1
    assert counter["errors"] == 0

    rows = db.query_all("select * from coaching_changes")
    assert len(rows) == 1
    row = rows[0]
    assert row["team_slug"] == "michigan"
    assert row["change_type"] == "hire"
    assert "Whittingham" in row["coach_name"] or row["coach_name"]
    assert row["team_id"] == 1

    # wire_entries got a paired row
    wire = db.query_all("select * from wire_entries")
    assert len(wire) == 1
    assert wire[0]["actor_kind"] == "coach"
    assert wire[0]["program_slug"] == "michigan"


def test_non_coaching_headline_filtered(
    monkeypatch: pytest.MonkeyPatch, db: Any
) -> None:
    """A non-coaching headline is fetched but filtered by the keyword guard."""
    feedparser = sys.modules["feedparser"]
    import requests

    from cfb_rankings.ingest.sources import coaching_tracker

    feed = _make_feed([
        _make_entry("Five takeaways from Saturday's Big Ten slate"),
    ])
    monkeypatch.setattr(feedparser, "parse", lambda *_a, **_kw: feed)
    monkeypatch.setattr(requests, "get", lambda *_a, **_kw: _empty_247_response())

    counter = coaching_tracker.fetch_coaching_news(db, days=14)

    assert counter["fetched"] >= 1
    assert counter["matched_keyword"] == 0
    assert counter["persisted"] == 0

    rows = db.query_all("select * from coaching_changes")
    assert rows == []


# ---------------------------------------------------------------------------
# Network-error path
# ---------------------------------------------------------------------------


def test_network_error_graceful(
    monkeypatch: pytest.MonkeyPatch, db: Any
) -> None:
    """Both sources raise -> errors counter advances, no exception bubbles."""
    feedparser = sys.modules["feedparser"]
    import requests

    from cfb_rankings.ingest.sources import coaching_tracker

    def _explode(*_a: Any, **_kw: Any) -> None:
        raise RuntimeError("simulated network failure")

    monkeypatch.setattr(feedparser, "parse", _explode)
    monkeypatch.setattr(requests, "get", _explode)

    counter = coaching_tracker.fetch_coaching_news(db, days=7)

    assert counter["persisted"] == 0
    # Both sources failed -> errors >= 2
    assert counter["errors"] >= 2
    assert counter["fetched"] == 0


def test_one_source_down_other_continues(
    monkeypatch: pytest.MonkeyPatch, db: Any
) -> None:
    """Footballscoop down -> 247Sports still runs (and vice versa)."""
    feedparser = sys.modules["feedparser"]
    import requests

    from cfb_rankings.ingest.sources import coaching_tracker

    monkeypatch.setattr(feedparser, "parse",
                        lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(requests, "get", lambda *_a, **_kw: _empty_247_response())

    counter = coaching_tracker.fetch_coaching_news(db, days=7)

    # feedparser failed -> 1 error; 247sports succeeded with 0 rows.
    assert counter["errors"] == 1
    assert counter["persisted"] == 0


# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------


def test_same_entry_dedups(monkeypatch: pytest.MonkeyPatch, db: Any) -> None:
    """Same coaching headline pulled twice -> exactly one row."""
    feedparser = sys.modules["feedparser"]
    import requests

    from cfb_rankings.ingest.sources import coaching_tracker

    feed = _make_feed([
        _make_entry("Michigan hired Kyle Whittingham as head coach",
                    link="https://footballscoop.com/whittingham-michigan"),
    ])
    monkeypatch.setattr(feedparser, "parse", lambda *_a, **_kw: feed)
    monkeypatch.setattr(requests, "get", lambda *_a, **_kw: _empty_247_response())

    coaching_tracker.fetch_coaching_news(db, days=14)
    counter2 = coaching_tracker.fetch_coaching_news(db, days=14)

    # Second run sees the same dedup_key already in sources_json -> 0 persists
    assert counter2["matched_keyword"] >= 1
    assert counter2["persisted"] == 0

    rows = db.query_all("select * from coaching_changes")
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# Missing-table tolerance
# ---------------------------------------------------------------------------


def test_missing_coaching_table_does_not_crash(tmp_path: Path) -> None:
    """If coaching_changes is missing entirely we log + bail gracefully."""
    from cfb_rankings.db import Database
    from cfb_rankings.ingest.sources import coaching_tracker

    db_path = tmp_path / "empty.db"
    # Create the file but no schema.
    sqlite3.connect(db_path).close()
    db = Database(f"sqlite:///{db_path.as_posix()}")

    counter = coaching_tracker.fetch_coaching_news(db, days=7)

    assert counter["persisted"] == 0
    assert counter["errors"] >= 1


# ---------------------------------------------------------------------------
# Helper coverage
# ---------------------------------------------------------------------------


def test_change_type_inference() -> None:
    from cfb_rankings.ingest.sources import coaching_tracker

    assert coaching_tracker._infer_change_type("Texas hired new coach") == "hire"
    assert coaching_tracker._infer_change_type("Coach fired after rough season") == "exit"
    assert coaching_tracker._infer_change_type("Auburn promoted assistant") == "promotion"
    assert coaching_tracker._infer_change_type("Sherrone Moore signs extension") == "extension"
    assert coaching_tracker._infer_change_type("Random unrelated headline") == "other"


def test_dedup_key_stable() -> None:
    from cfb_rankings.ingest.sources import coaching_tracker

    a = coaching_tracker._make_dedup_key("footballscoop", "Hello", "2026-05-15")
    b = coaching_tracker._make_dedup_key("footballscoop", "Hello", "2026-05-15")
    c = coaching_tracker._make_dedup_key("footballscoop", "World", "2026-05-15")
    assert a == b
    assert a != c
