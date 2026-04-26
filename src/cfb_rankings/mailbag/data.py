"""Mailbag data-access helpers — thin wrappers over raw sqlite3.

Keeps all SQL in one file. All other modules import from here.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "cfb_rankings.db"


def db_path() -> Path:
    return Path(os.environ.get("CFB_RANKINGS_DB", str(DEFAULT_DB_PATH)))


@contextmanager
def db_conn(read_only: bool = False) -> Iterator[sqlite3.Connection]:
    p = db_path()
    if read_only:
        uri = f"file:{p}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(zip(row.keys(), tuple(row)))


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------

def insert_submission(
    conn: sqlite3.Connection,
    *,
    handle: str,
    email: str | None,
    question_text: str,
    topic_tags: list[str] | None = None,
    status: str = "queued",
) -> int:
    cur = conn.execute(
        """
        INSERT INTO mailbag_submissions
          (submitter_handle, submitter_email, question_text, topic_tags_json, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            handle,
            email,
            question_text,
            json.dumps(topic_tags or []),
            status,
        ),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def list_queued_submissions(
    conn: sqlite3.Connection,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, submitted_at_utc, submitter_handle, submitter_email,
               question_text, topic_tags_json, status, curator_notes
        FROM mailbag_submissions
        WHERE status = 'queued'
        ORDER BY submitted_at_utc ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def update_submission_status(
    conn: sqlite3.Connection,
    submission_id: int,
    status: str,
    *,
    curator_notes: str | None = None,
    rejection_reason: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE mailbag_submissions
           SET status = ?,
               curator_notes = COALESCE(?, curator_notes),
               rejection_reason = COALESCE(?, rejection_reason)
         WHERE id = ?
        """,
        (status, curator_notes, rejection_reason, submission_id),
    )
    conn.commit()


def get_submission(conn: sqlite3.Connection, submission_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM mailbag_submissions WHERE id = ?", (submission_id,)
    ).fetchone()
    return row_to_dict(row) if row else None


def list_curated_for_edition(
    conn: sqlite3.Connection,
    edition_slug: str,
) -> list[dict[str, Any]]:
    """Return submissions curated for an edition (matched by curator_notes edition tag)."""
    rows = conn.execute(
        """
        SELECT * FROM mailbag_submissions
        WHERE status = 'curated'
          AND curator_notes LIKE ?
        ORDER BY id ASC
        """,
        (f"%{edition_slug}%",),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Editions
# ---------------------------------------------------------------------------

def upsert_edition(
    conn: sqlite3.Connection,
    *,
    edition_slug: str,
    publish_date: str,
    status: str = "draft",
    notes: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO mailbag_editions (edition_slug, publish_date, status, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(edition_slug) DO UPDATE SET
          publish_date = excluded.publish_date,
          status = excluded.status,
          notes = COALESCE(excluded.notes, mailbag_editions.notes)
        """,
        (edition_slug, publish_date, status, notes),
    )
    conn.commit()


def get_edition(conn: sqlite3.Connection, edition_slug: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM mailbag_editions WHERE edition_slug = ?", (edition_slug,)
    ).fetchone()
    return row_to_dict(row) if row else None


def list_recent_editions(
    conn: sqlite3.Connection,
    *,
    limit: int = 30,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM mailbag_editions
        ORDER BY publish_date DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def publish_edition(conn: sqlite3.Connection, edition_slug: str) -> None:
    conn.execute(
        "UPDATE mailbag_editions SET status = 'published' WHERE edition_slug = ?",
        (edition_slug,),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Answers
# ---------------------------------------------------------------------------

def upsert_answer(
    conn: sqlite3.Connection,
    *,
    edition_slug: str,
    rank_position: int,
    submission_id: int,
    answer_body: str,
    cited_sources: list[str],
    source_count: int,
    primary_topic: str | None = None,
    voice_validator_passed: bool = False,
    generation_model: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO mailbag_answers
          (edition_slug, rank_position, submission_id, answer_body,
           cited_sources_json, source_count, primary_topic,
           voice_validator_passed, generation_model)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(edition_slug, rank_position) DO UPDATE SET
          submission_id = excluded.submission_id,
          answer_body = excluded.answer_body,
          cited_sources_json = excluded.cited_sources_json,
          source_count = excluded.source_count,
          primary_topic = excluded.primary_topic,
          voice_validator_passed = excluded.voice_validator_passed,
          generation_model = excluded.generation_model
        """,
        (
            edition_slug,
            rank_position,
            submission_id,
            answer_body,
            json.dumps(cited_sources),
            source_count,
            primary_topic,
            1 if voice_validator_passed else 0,
            generation_model,
        ),
    )
    conn.commit()


def list_answers_for_edition(
    conn: sqlite3.Connection,
    edition_slug: str,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT a.*, s.submitter_handle, s.question_text, s.topic_tags_json
        FROM mailbag_answers a
        JOIN mailbag_submissions s ON s.id = a.submission_id
        WHERE a.edition_slug = ?
        ORDER BY a.rank_position ASC
        """,
        (edition_slug,),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Corpus context helpers — pull Wire/Pulse/Receipts excerpts for synthesis
# ---------------------------------------------------------------------------

def fetch_wire_excerpts(
    conn: sqlite3.Connection,
    topic_tags: list[str],
    *,
    limit: int = 8,
) -> list[str]:
    """Pull recent Wire entries loosely related to a question's topic tags."""
    if not topic_tags:
        return []
    like_clauses = " OR ".join(
        "lower(action) LIKE ? OR lower(why_it_matters) LIKE ?" for _ in topic_tags
    )
    params = []
    for tag in topic_tags:
        t = f"%{tag.lower()}%"
        params += [t, t]
    params.append(limit)
    try:
        rows = conn.execute(
            f"""
            SELECT program_display, action, why_it_matters
            FROM wire_entries
            WHERE ({like_clauses})
              AND trim(why_it_matters) <> ''
            ORDER BY occurred_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [
            f"{r['program_display']}: {r['action']} — {r['why_it_matters']}"
            for r in rows
        ]
    except Exception:
        return []


def fetch_receipt_excerpts(
    conn: sqlite3.Connection,
    topic_tags: list[str],
    *,
    limit: int = 5,
) -> list[str]:
    """Pull aged-well receipts relevant to the question's topic tags."""
    if not topic_tags:
        return []
    like_clauses = " OR ".join(
        "lower(claim_text) LIKE ?" for _ in topic_tags
    )
    params = [f"%{t.lower()}%" for t in topic_tags]
    params.append(limit)
    try:
        rows = conn.execute(
            f"""
            SELECT source_name, claim_text, verdict_text
            FROM receipts
            WHERE ({like_clauses})
            ORDER BY aged_well_score DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [
            f"{r['source_name']}: \"{r['claim_text']}\" → {r['verdict_text']}"
            for r in rows
        ]
    except Exception:
        return []


def fetch_pulse_excerpts(
    conn: sqlite3.Connection,
    topic_tags: list[str],
    *,
    limit: int = 5,
) -> list[str]:
    """Pull Pulse theme summaries related to the question's topic tags."""
    if not topic_tags:
        return []
    like_clauses = " OR ".join(
        "lower(theme_label) LIKE ? OR lower(theme_body) LIKE ?" for _ in topic_tags
    )
    params = []
    for tag in topic_tags:
        t = f"%{tag.lower()}%"
        params += [t, t]
    params.append(limit)
    try:
        rows = conn.execute(
            f"""
            SELECT program_slug, theme_label, theme_body
            FROM team_pulse_cache
            WHERE ({like_clauses})
            ORDER BY generated_at_utc DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [
            f"{r['program_slug']} pulse: {r['theme_label']} — {r['theme_body']}"
            for r in rows
        ]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# ISO-week helpers (Friday-anchored edition slugs)
# ---------------------------------------------------------------------------

def current_edition_slug() -> str:
    """Return the ISO-week slug for the current Friday-anchored week."""
    today = date.today()
    iso = today.isocalendar()
    return f"{iso.year}-w{iso.week:02d}"


def edition_publish_date(edition_slug: str) -> str:
    """Return the Friday date for a given 'YYYY-wNN' slug."""
    year_str, week_str = edition_slug.split("-w")
    year, week = int(year_str), int(week_str)
    # ISO week Monday = day 1; Friday = day 5
    monday = date.fromisocalendar(year, week, 1)
    friday = monday + timedelta(days=4)
    return friday.isoformat()
