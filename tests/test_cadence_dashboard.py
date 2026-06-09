"""Tests for the WS-12 editorial cadence dashboard.

Coverage:
  - a surface published within its threshold reads ok; one past it reads overdue;
    a surface with no rows reads never.
  - per-active-thread staleness flags threads whose last chapter is >14 days old.
  - render_cadence_dashboard writes both the Markdown dashboard and JSON sidecar.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.migrations import apply_runtime_migrations
from cfb_rankings.storylines.cadence_dashboard import (
    compute_cadence,
    render_cadence_dashboard,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCHEMA = REPO_ROOT / "research" / "cfb-data-schema-sqlite.sql"

# Fixed "now" so age computations are deterministic.
NOW = datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(f"sqlite:///{tmp_path / 'cadence.db'}")
    database.apply_sql_file(BASE_SCHEMA)
    apply_runtime_migrations(database)
    return database


def _thread(db: Database, slug: str, title: str, last_chapter_at: str) -> None:
    db.execute(
        "insert into storyline_threads "
        "(thread_slug, title, dek, status, started_at, chapter_count, last_chapter_at) "
        "values (:s, :t, 'dek', 'active', '2026-01-01', 4, :l)",
        {"s": slug, "t": title, "l": last_chapter_at},
    )


def test_surface_status_ok_overdue_never(db: Database) -> None:
    # Mailbag fresh (4 days ago, threshold 8) -> ok.
    db.execute(
        "insert into mailbag_editions (edition_slug, publish_date, status, generated_at_utc) "
        "values ('mb-1', '2026-05-24', 'published', '2026-05-24 12:00:00')",
        {},
    )
    # Daily stale (15 days ago, threshold 4) -> overdue.
    db.execute(
        "insert into daily_editions (edition_date, generated_at_utc, status) "
        "values ('2026-05-13', '2026-05-13 12:00:00', 'published')",
        {},
    )
    # Wire: no rows -> never.

    summary = compute_cadence(db, now=NOW)
    by_surface = {s["surface"]: s for s in summary["surfaces"]}

    assert by_surface["mailbag"]["status"] == "ok"
    assert by_surface["daily"]["status"] == "overdue"
    assert by_surface["wire"]["status"] == "never"
    # overdue_count counts both overdue and never-published surfaces.
    assert summary["overdue_count"] >= 2


def test_stale_thread_flagging(db: Database) -> None:
    _thread(db, "fresh-thread", "Fresh Thread", "2026-05-20 09:00:00")  # 8d -> ok
    _thread(db, "stale-thread", "Stale Thread", "2026-04-21 09:00:00")  # 37d -> stale

    summary = compute_cadence(db, now=NOW)
    threads = {t["thread_slug"]: t for t in summary["stale_threads"]}

    assert threads["fresh-thread"]["stale"] is False
    assert threads["stale-thread"]["stale"] is True
    assert summary["stale_thread_count"] == 1
    # The storyline_chapters surface reflects the newest active thread.
    storyline = next(s for s in summary["surfaces"] if s["surface"] == "storyline_chapters")
    assert storyline["status"] == "ok"  # newest active chapter is 8d old, < 14d


def test_render_writes_md_and_json(db: Database, tmp_path: Path) -> None:
    _thread(db, "stale-thread", "Stale Thread", "2026-04-21 09:00:00")
    out = tmp_path / "editorial-cadence.md"

    result = render_cadence_dashboard(db, output_path=out, now=NOW)

    md = out.read_text(encoding="utf-8")
    assert "Editorial cadence dashboard" in md
    assert "Stale Thread" in md
    assert Path(result["json_path"]).exists()
    assert result["stale_thread_count"] == 1
