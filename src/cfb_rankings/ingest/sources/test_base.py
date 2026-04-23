"""Unit tests for SourceAdapter. Runs against an ephemeral SQLite DB.

Exercises the full lifecycle (fetch → parse → write_rows → health_check) and
confirms a single row lands in ``scrape_health`` per run, for both success and
error paths.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Sequence

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.base import BaseRssAdapter, SourceAdapter


def _fresh_db() -> Database:
    tmp = Path(tempfile.mkdtemp()) / "fanintel_test.db"
    db = Database(f"sqlite:///{tmp.as_posix()}")
    db.execute(
        """
        create table scrape_health (
            source_id text not null,
            run_date text not null,
            rows_inserted integer,
            status text not null,
            error_message text,
            run_started_at_utc text,
            run_finished_at_utc text,
            adapter_version text,
            primary key (source_id, run_date)
        )
        """
    )
    db.execute("create table _sink (payload text)")
    return db


class DummyAdapter(SourceAdapter):
    source_id = "dummy_ok"
    adapter_version = "0.1.0-test"

    def __init__(self, db: Database, payloads: list[str]) -> None:
        super().__init__(db)
        self._payloads = payloads

    def fetch(self) -> list[str]:
        return self._payloads

    def parse(self, raw: list[str]) -> list[dict[str, Any]]:
        return [{"payload": p} for p in raw]

    def write_rows(self, rows: Sequence[dict[str, Any]]) -> int:
        for row in rows:
            self.db.execute("insert into _sink (payload) values (:payload)", row)
        return len(rows)


class ExplodingAdapter(DummyAdapter):
    source_id = "dummy_error"

    def fetch(self) -> list[str]:
        raise RuntimeError("network boom")


def _one_health_row(db: Database, source_id: str) -> dict[str, Any]:
    return db.query_one(
        "select * from scrape_health where source_id = :source_id",
        {"source_id": source_id},
    )


def test_full_lifecycle_ok() -> None:
    db = _fresh_db()
    adapter = DummyAdapter(db, ["one", "two", "three"])
    result = adapter.run()
    assert result.status == "ok"
    assert result.rows_inserted == 3
    sunk = db.query_all("select payload from _sink order by payload")
    assert [r["payload"] for r in sunk] == ["one", "three", "two"]
    health = _one_health_row(db, "dummy_ok")
    assert health["status"] == "ok"
    assert health["rows_inserted"] == 3
    assert health["adapter_version"] == "0.1.0-test"
    assert health["run_started_at_utc"] is not None
    assert health["run_finished_at_utc"] is not None


def test_empty_payload_reports_empty() -> None:
    db = _fresh_db()
    adapter = DummyAdapter(db, [])
    result = adapter.run()
    assert result.status == "empty"
    assert result.rows_inserted == 0
    health = _one_health_row(db, "dummy_ok")
    assert health["status"] == "empty"


def test_fetch_error_still_writes_health_row() -> None:
    db = _fresh_db()
    adapter = ExplodingAdapter(db, [])
    result = adapter.run()
    assert result.status == "error"
    assert result.rows_inserted == 0
    assert result.error_message and "network boom" in result.error_message
    health = _one_health_row(db, "dummy_error")
    assert health["status"] == "error"
    assert "network boom" in health["error_message"]


def test_run_is_idempotent_on_same_day() -> None:
    db = _fresh_db()
    adapter = DummyAdapter(db, ["x"])
    adapter.run()
    adapter.run()
    rows = db.query_all("select count(*) as n from scrape_health")
    assert rows[0]["n"] == 1  # upsert, not duplicate insert


def test_source_id_is_required() -> None:
    class NoIdAdapter(DummyAdapter):
        source_id = ""

    try:
        NoIdAdapter(_fresh_db(), [])
    except ValueError as exc:
        assert "source_id" in str(exc)
        return
    raise AssertionError("expected ValueError for missing source_id")


def test_base_rss_parses_rss_and_atom() -> None:
    rss = b"""<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <item><title>A</title><link>http://a</link></item>
      <item><title>B</title><link>http://b</link></item>
    </channel></rss>"""
    atom = b"""<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>C</title></entry>
    </feed>"""

    class R(BaseRssAdapter):
        source_id = "rss_test"

        def row_from_entry(self, entry: Any) -> dict[str, Any] | None:
            title = entry.findtext("title") or entry.findtext(
                "{http://www.w3.org/2005/Atom}title"
            )
            return {"title": title} if title else None

        def write_rows(self, rows: Sequence[dict[str, Any]]) -> int:
            return len(rows)

    db = _fresh_db()
    adapter = R(db)
    assert [r["title"] for r in adapter.parse(rss)] == ["A", "B"]
    assert [r["title"] for r in adapter.parse(atom)] == ["C"]
