"""Tests for S5 Today in CFB History renderer (Sprint v5-1 Day 4).

Verifies:
  * Empty DB → valid empty-state page (always renders).
  * 1 archive_thread row → 1 card with 'N years ago today'.
  * Mix of archive + chronicle → unified card list.
  * Smoke import + CLI parse round-trip.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from cfb_rankings.db import Database
from cfb_rankings.migrations import apply_runtime_migrations
from cfb_rankings.today_in_history import (
    AnniversaryCard,
    gather_today_in_history_cards,
    render_today_in_history_html,
    render_today_in_history_page,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCHEMA = REPO_ROOT / "research" / "cfb-data-schema-sqlite.sql"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def migrated_db(tmp_path: Path) -> Database:
    """Fresh DB with base schema + all migrations applied."""
    db_path = tmp_path / "today_history.db"
    db = Database(f"sqlite:///{db_path}")
    db.apply_sql_file(BASE_SCHEMA)
    apply_runtime_migrations(db)
    return db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_archive_thread(
    db: Database,
    *,
    subreddit: str,
    external_id: str,
    title: str,
    iso_date: str,
    score: int = 200,
    body_md: str = "",
    author: str = "fan1",
    num_comments: int = 50,
    permalink: str | None = None,
) -> None:
    iso_mm_dd = iso_date[5:10]
    season_year = int(iso_date[:4]) if int(iso_date[5:7]) >= 8 else (int(iso_date[:4]) - 1 if int(iso_date[5:7]) == 1 else None)
    db.execute(
        """
        insert into archive_threads (
            subreddit, external_id, title, body_md, permalink, author,
            created_utc, score, num_comments, upvote_ratio, flair,
            is_self, link_url, over_18, locked, iso_date, iso_mm_dd, season_year
        ) values (
            :subreddit, :external_id, :title, :body_md, :permalink, :author,
            :created_utc, :score, :num_comments, :upvote_ratio, :flair,
            :is_self, :link_url, :over_18, :locked, :iso_date, :iso_mm_dd, :season_year
        )
        """,
        {
            "subreddit": subreddit, "external_id": external_id, "title": title,
            "body_md": body_md, "permalink": permalink, "author": author,
            "created_utc": f"{iso_date}T14:00:00Z",
            "score": score, "num_comments": num_comments,
            "upvote_ratio": 0.92, "flair": None,
            "is_self": 1, "link_url": None, "over_18": 0, "locked": 0,
            "iso_date": iso_date, "iso_mm_dd": iso_mm_dd, "season_year": season_year,
        },
    )


def _insert_team_chronicle(
    db: Database,
    *,
    team_id: int = 1,
    season_year: int = 2020,
    headline: str = "Anomaly card",
    body_md: str = "Sample editorial body.",
    card_type: str = "anomaly",
    surprise_score: float = 0.8,
    generated_at_utc: str | None = None,
    is_published: int = 1,
    week: int | None = 5,
    source_attribution: str = "CFB Index model",
) -> None:
    """Insert a row into team_chronicle_observations.

    Uses ``PRAGMA foreign_keys=OFF`` for this raw insert so the test
    doesn't need to manufacture every parent row across the broad FK
    fan-out (seasons + teams + classifications + ...). The S5 renderer
    code path queries by MM-DD only — FK integrity is irrelevant to
    that read.
    """
    sql = """
        insert into team_chronicle_observations (
            team_id, season_year, week, card_type, headline, body_md,
            stat_json, comparison_json, source_attribution, surprise_score,
            surfaced_rank, state_signature, model_id, prompt_tokens,
            completion_tokens, is_published, generated_at_utc
        ) values (
            :team_id, :season_year, :week, :card_type, :headline, :body_md,
            null, null, :source_attribution, :surprise_score,
            1, null, 'claude-sonnet-4-6', 0, 0, :is_published, :generated_at_utc
        )
    """
    params = {
        "team_id": team_id, "season_year": season_year, "week": week,
        "card_type": card_type, "headline": headline, "body_md": body_md,
        "source_attribution": source_attribution,
        "surprise_score": surprise_score, "is_published": is_published,
        "generated_at_utc": generated_at_utc or "2025-06-05T14:00:00",
    }
    with db.connection() as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute(sql, params)
        conn.commit()


# ---------------------------------------------------------------------------
# Smoke + import
# ---------------------------------------------------------------------------

def test_module_imports() -> None:
    from cfb_rankings.today_in_history import (
        AnniversaryCard as AC,
        gather_today_in_history_cards as g,
        render_today_in_history_page as r,
        render_today_in_history_html as rhtml,
    )
    assert AC is AnniversaryCard
    assert callable(g) and callable(r) and callable(rhtml)


def test_cli_parses_render_today_in_history() -> None:
    """Smoke: CLI subcommand wiring is in place."""
    from cfb_rankings.cli import build_parser
    parser = build_parser()
    args = parser.parse_args([
        "render-today-in-history",
        "--today", "2026-06-05",
        "--output-dir", "/tmp/test-out",
        "--max-cards", "3",
    ])
    assert args.command == "render-today-in-history"
    assert args.today == "2026-06-05"
    assert args.max_cards == 3


# ---------------------------------------------------------------------------
# Empty-state path
# ---------------------------------------------------------------------------

def test_empty_db_produces_valid_empty_state(migrated_db: Database, tmp_path: Path) -> None:
    out_dir = tmp_path / "anniversary"
    result = render_today_in_history_page(
        migrated_db,
        today=date(2026, 6, 5),
        output_dir=str(out_dir),
    )
    assert result["cards_rendered"] == 0
    files = result["output_files"]
    assert len(files) == 2  # index.html + data.json
    index_path = out_dir / "index.html"
    assert index_path.exists()
    html_text = index_path.read_text(encoding="utf-8")
    assert "Today in CFB History" in html_text
    assert "Quiet day in CFB history" in html_text
    # Should reference the date phrase.
    assert "June" in html_text and "2026" in html_text


def test_html_has_valid_structure_in_empty_state() -> None:
    html = render_today_in_history_html(
        cards=[],
        today=date(2026, 6, 5),
        week_label="Late Spring (85 days to kickoff)",
        phase_label="Late Spring",
        days_to_kickoff_value=85,
    )
    assert "<!doctype html>" in html
    assert "<html" in html and "</html>" in html
    assert "Quiet day" in html
    assert "Late Spring" in html


# ---------------------------------------------------------------------------
# 1 archive_threads row → 1 card with "N years ago today"
# ---------------------------------------------------------------------------

def test_single_archive_thread_renders_one_card(migrated_db: Database, tmp_path: Path) -> None:
    _insert_archive_thread(
        migrated_db,
        subreddit="CFB",
        external_id="abc123",
        title="On this day in 2014, the playoff bracket changed everything",
        iso_date="2014-06-05",
        score=1243,
        body_md="A real archive thread from the offseason.",
        permalink="/r/CFB/comments/abc123/",
    )
    out_dir = tmp_path / "anniversary"
    result = render_today_in_history_page(
        migrated_db,
        today=date(2026, 6, 5),
        output_dir=str(out_dir),
    )
    assert result["cards_rendered"] == 1
    html_text = (out_dir / "index.html").read_text(encoding="utf-8")
    assert "playoff bracket" in html_text
    assert "12 years ago today" in html_text
    assert "2014" in html_text
    assert "1,243 upvotes" in html_text


def test_single_card_data_returns_correct_shape(migrated_db: Database) -> None:
    _insert_archive_thread(
        migrated_db,
        subreddit="CFB",
        external_id="single1",
        title="The hire that changed Alabama",
        iso_date="2020-06-05",
        score=523,
    )
    cards = gather_today_in_history_cards(migrated_db, today=date(2026, 6, 5))
    assert len(cards) == 1
    card = cards[0]
    assert card.source == "archive_threads"
    assert card.year == 2020
    assert card.years_ago == 6
    assert card.headline == "The hire that changed Alabama"
    assert card.score == 523
    assert "r/CFB" in card.attribution


# ---------------------------------------------------------------------------
# Mix of sources → unified card list
# ---------------------------------------------------------------------------

def test_mix_of_archive_and_chronicle_returns_unified_list(migrated_db: Database, tmp_path: Path) -> None:
    # Insert 2 archive_threads + 1 team_chronicle, all on 06-05.
    _insert_archive_thread(
        migrated_db,
        subreddit="CFB",
        external_id="ar1",
        title="The 2018 Tua moment",
        iso_date="2018-06-05",
        score=900,
    )
    _insert_archive_thread(
        migrated_db,
        subreddit="cfb",
        external_id="ar2",
        title="2020 portal frenzy",
        iso_date="2020-06-05",
        score=400,
    )
    _insert_team_chronicle(
        migrated_db,
        team_id=42,
        season_year=2019,
        headline="2019 Alabama spring anomaly",
        generated_at_utc="2019-06-05T14:30:00",
    )

    cards = gather_today_in_history_cards(migrated_db, today=date(2026, 6, 5), max_cards=5)
    # All three should surface.
    sources = {c.source for c in cards}
    assert "archive_threads" in sources
    assert "team_chronicle" in sources
    # 3 unique cards, sorted year-desc.
    assert len(cards) == 3
    years = [c.year for c in cards]
    assert years == sorted(years, reverse=True)


def test_max_cards_caps_output(migrated_db: Database) -> None:
    for i in range(10):
        _insert_archive_thread(
            migrated_db,
            subreddit="CFB",
            external_id=f"many{i}",
            title=f"Headline {i}",
            iso_date=f"{2014 + i}-06-05",
            score=500 - i * 10,
        )
    cards = gather_today_in_history_cards(migrated_db, today=date(2026, 6, 5), max_cards=3)
    assert len(cards) == 3


def test_unpublished_chronicle_skipped(migrated_db: Database) -> None:
    _insert_team_chronicle(
        migrated_db,
        team_id=99,
        season_year=2018,
        headline="Draft card never published",
        generated_at_utc="2018-06-05T10:00:00",
        is_published=0,
    )
    cards = gather_today_in_history_cards(migrated_db, today=date(2026, 6, 5))
    assert len(cards) == 0


# ---------------------------------------------------------------------------
# Year-filtering: don't surface today's year
# ---------------------------------------------------------------------------

def test_current_year_not_surfaced(migrated_db: Database) -> None:
    """An archive_thread from the current year shouldn't appear (years_ago=0
    would render as nonsense)."""
    _insert_archive_thread(
        migrated_db,
        subreddit="CFB",
        external_id="thisyear",
        title="Today's news",
        iso_date="2026-06-05",
        score=200,
    )
    _insert_archive_thread(
        migrated_db,
        subreddit="CFB",
        external_id="lastyear",
        title="Last year's news",
        iso_date="2025-06-05",
        score=200,
    )
    cards = gather_today_in_history_cards(migrated_db, today=date(2026, 6, 5))
    assert len(cards) == 1
    assert cards[0].year == 2025
    assert cards[0].years_ago == 1


# ---------------------------------------------------------------------------
# HTML rendering shape
# ---------------------------------------------------------------------------

def test_html_escapes_user_content() -> None:
    """Cards with HTML-injection content should be escaped."""
    cards = [
        AnniversaryCard(
            year=2020, years_ago=6, source="archive_threads",
            headline="<script>alert('xss')</script>",
            body="<img src=x onerror=alert(1)>",
            url="https://reddit.com/r/CFB",
            attribution="r/CFB · 100 upvotes",
            score=100,
        )
    ]
    html_text = render_today_in_history_html(cards=cards, today=date(2026, 6, 5))
    assert "<script>" not in html_text
    assert "&lt;script&gt;" in html_text
    assert "&lt;img" in html_text


def test_singular_years_ago_phrasing() -> None:
    cards = [
        AnniversaryCard(year=2025, years_ago=1, source="archive_threads",
                        headline="One year back", attribution="r/CFB"),
    ]
    html_text = render_today_in_history_html(cards=cards, today=date(2026, 6, 5))
    assert "1 year ago today" in html_text
    assert "1 years ago today" not in html_text


def test_renderer_always_writes_files(migrated_db: Database, tmp_path: Path) -> None:
    """Renderer must always produce at least the index.html + data.json,
    even on an empty DB."""
    out_dir = tmp_path / "anniversary_safety"
    result = render_today_in_history_page(
        migrated_db,
        today=date(2026, 6, 5),
        output_dir=str(out_dir),
    )
    for path_str in result["output_files"]:
        assert Path(path_str).exists()
    assert (out_dir / "index.html").exists()
    assert (out_dir / "data.json").exists()
