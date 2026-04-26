"""DAO layer for reaction_stories + reaction_cohort_splits (Sprint 15).

Uses direct sqlite3 (same pattern as receipts.runtime) rather than the
Database ORM, keeping the module self-contained.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "cfb_rankings.db"


def db_path() -> Path:
    return Path(os.environ.get("CFB_RANKINGS_DB", str(DEFAULT_DB_PATH)))


@contextmanager
def db_conn(read_only: bool = False) -> Iterator[sqlite3.Connection]:
    p = db_path()
    if read_only:
        conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class ReactionStory:
    slug: str
    triggered_by_wire_id: int
    triggered_at_utc: str
    triggered_by_velocity: float
    primary_entity_slug: str
    primary_entity_type: str
    headline: str
    dek: str
    body: str
    surprise_index: Optional[float]
    status: str
    voice_validator_passed: int
    generation_model: Optional[str]
    cited_sources_json: str
    notes: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ReactionStory":
        d = dict(row)
        return cls(
            slug=d["slug"],
            triggered_by_wire_id=d["triggered_by_wire_id"],
            triggered_at_utc=d["triggered_at_utc"],
            triggered_by_velocity=d["triggered_by_velocity"],
            primary_entity_slug=d["primary_entity_slug"],
            primary_entity_type=d["primary_entity_type"],
            headline=d["headline"],
            dek=d["dek"],
            body=d["body"],
            surprise_index=d.get("surprise_index"),
            status=d["status"],
            voice_validator_passed=d["voice_validator_passed"],
            generation_model=d.get("generation_model"),
            cited_sources_json=d["cited_sources_json"],
            notes=d.get("notes"),
        )


@dataclass
class CohortSplit:
    story_slug: str
    cohort: str  # stat_folks | casual_fans | die_hards
    stance: str
    representative_quotes_json: str
    sentiment_score: Optional[float]
    volume_share: Optional[float]

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "CohortSplit":
        d = dict(row)
        return cls(
            story_slug=d["story_slug"],
            cohort=d["cohort"],
            stance=d["stance"],
            representative_quotes_json=d["representative_quotes_json"],
            sentiment_score=d.get("sentiment_score"),
            volume_share=d.get("volume_share"),
        )

    @property
    def quotes(self) -> list[dict]:
        return json.loads(self.representative_quotes_json or "[]")


# ── Fetch ──────────────────────────────────────────────────────────────────

def fetch_story(slug: str) -> Optional[ReactionStory]:
    with db_conn(read_only=True) as c:
        row = c.execute(
            "SELECT * FROM reaction_stories WHERE slug = ?", (slug,)
        ).fetchone()
        return ReactionStory.from_row(row) if row else None


def list_stories(status: Optional[str] = None, limit: int = 50) -> list[ReactionStory]:
    with db_conn(read_only=True) as c:
        if status:
            rows = c.execute(
                "SELECT * FROM reaction_stories WHERE status = ? "
                "ORDER BY triggered_at_utc DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM reaction_stories ORDER BY triggered_at_utc DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [ReactionStory.from_row(r) for r in rows]


def fetch_cohort_splits(story_slug: str) -> list[CohortSplit]:
    with db_conn(read_only=True) as c:
        rows = c.execute(
            "SELECT * FROM reaction_cohort_splits WHERE story_slug = ? ORDER BY cohort",
            (story_slug,),
        ).fetchall()
        return [CohortSplit.from_row(r) for r in rows]


def fetch_wire_entry(wire_id: int) -> Optional[dict]:
    with db_conn(read_only=True) as c:
        row = c.execute(
            "SELECT * FROM wire_entries WHERE id = ?", (wire_id,)
        ).fetchone()
        return dict(row) if row else None


# ── Upsert ─────────────────────────────────────────────────────────────────

def upsert_story(story: ReactionStory) -> None:
    with db_conn() as c:
        c.execute(
            """
            INSERT INTO reaction_stories (
                slug, triggered_by_wire_id, triggered_at_utc, triggered_by_velocity,
                primary_entity_slug, primary_entity_type,
                headline, dek, body, surprise_index,
                status, voice_validator_passed, generation_model,
                cited_sources_json, notes
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(slug) DO UPDATE SET
                headline = excluded.headline,
                dek = excluded.dek,
                body = excluded.body,
                surprise_index = excluded.surprise_index,
                status = excluded.status,
                voice_validator_passed = excluded.voice_validator_passed,
                generation_model = excluded.generation_model,
                cited_sources_json = excluded.cited_sources_json,
                notes = excluded.notes
            """,
            (
                story.slug,
                story.triggered_by_wire_id,
                story.triggered_at_utc,
                story.triggered_by_velocity,
                story.primary_entity_slug,
                story.primary_entity_type,
                story.headline,
                story.dek,
                story.body,
                story.surprise_index,
                story.status,
                story.voice_validator_passed,
                story.generation_model,
                story.cited_sources_json,
                story.notes,
            ),
        )
        c.commit()


def upsert_cohort_split(split: CohortSplit) -> None:
    with db_conn() as c:
        c.execute(
            """
            INSERT INTO reaction_cohort_splits (
                story_slug, cohort, stance, representative_quotes_json,
                sentiment_score, volume_share
            ) VALUES (?,?,?,?,?,?)
            ON CONFLICT(story_slug, cohort) DO UPDATE SET
                stance = excluded.stance,
                representative_quotes_json = excluded.representative_quotes_json,
                sentiment_score = excluded.sentiment_score,
                volume_share = excluded.volume_share
            """,
            (
                split.story_slug,
                split.cohort,
                split.stance,
                split.representative_quotes_json,
                split.sentiment_score,
                split.volume_share,
            ),
        )
        c.commit()
