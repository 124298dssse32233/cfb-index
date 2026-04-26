"""Seed loader for Storyline Threads.

Reads thread metadata from `seeds._metadata.THREADS` and per-slug chapter
content from `seeds.<slug>.CHAPTERS`, upserts both into SQLite. Idempotent:
calling twice produces the same row set (UPSERT on conflict).

Used by:
    cli.py `render-storylines` subcommand
    Sprint 10 build pipeline (Phase 1 + Phase 2)
"""
from __future__ import annotations

import json
from typing import Any, Iterable

from . import seeds


def _json_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, separators=(",", ":"))


def _word_count(text: str) -> int:
    return len([w for w in text.split() if w.strip()])


def _read_time_minutes(word_count: int) -> int:
    # ~225 wpm reading speed; minimum 1 minute.
    return max(1, round(word_count / 225))


def load_thread_metadata(db, threads: Iterable[dict] | None = None) -> int:
    """Upsert the 8 thread metadata rows. Returns count written."""
    rows: list[dict] = []
    source = list(threads) if threads is not None else list(seeds.iter_thread_metadata())
    for t in source:
        rows.append(
            {
                "thread_slug": t["thread_slug"],
                "title": t["title"],
                "dek": t["dek"],
                "accent_hex": t.get("accent_hex"),
                "status": t["status"],
                "started_at": t["started_at"],
                "primary_program_slugs": _json_or_none(t.get("primary_program_slugs") or []),
                "primary_conference_slug": t.get("primary_conference_slug"),
                "voice_register_source": t.get("voice_register_source", "editor-desk"),
            }
        )
    if not rows:
        return 0

    db.upsert_many(
        "storyline_threads",
        rows,
        conflict_columns=["thread_slug"],
        update_columns=[
            "title",
            "dek",
            "accent_hex",
            "status",
            "started_at",
            "primary_program_slugs",
            "primary_conference_slug",
            "voice_register_source",
        ],
    )
    return len(rows)


def load_chapters(db) -> dict[str, int]:
    """Upsert chapters from every registered per-slug module.

    Returns a {thread_slug: chapter_count} dict for reporting.
    """
    counts: dict[str, int] = {}
    for thread_slug, chapter_dicts in seeds.iter_chapter_modules():
        rows: list[dict] = []
        for ch in chapter_dicts:
            body = ch["body_markdown"]
            wc = _word_count(body)
            rows.append(
                {
                    "thread_slug": thread_slug,
                    "chapter_number": ch["chapter_number"],
                    "title": ch["title"],
                    "dek": ch["dek"],
                    "body_markdown": body,
                    "byline": ch["byline"],
                    "published_at": ch["published_at"],
                    "read_time_minutes": ch.get("read_time_minutes") or _read_time_minutes(wc),
                    "referenced_chapter_ids": _json_or_none(ch.get("referenced_chapter_ids") or []),
                    "referenced_sources_json": _json_or_none(ch.get("referenced_sources") or []),
                    "pull_quote": ch.get("pull_quote"),
                    "word_count": wc,
                    "voice_validator_passed": 1 if ch.get("voice_validator_passed", True) else 0,
                    "voice_validator_notes": ch.get("voice_validator_notes"),
                }
            )
        if rows:
            db.upsert_many(
                "storyline_chapters",
                rows,
                conflict_columns=["thread_slug", "chapter_number"],
                update_columns=[
                    "title", "dek", "body_markdown", "byline", "published_at",
                    "read_time_minutes", "referenced_chapter_ids",
                    "referenced_sources_json", "pull_quote", "word_count",
                    "voice_validator_passed", "voice_validator_notes",
                ],
            )
            counts[thread_slug] = len(rows)
        else:
            counts.setdefault(thread_slug, 0)
    return counts


def refresh_thread_aggregates(db) -> None:
    """Recompute chapter_count, word_count, last_chapter_at on every thread."""
    db.execute(
        """
        update storyline_threads
        set
            chapter_count = (
                select count(*) from storyline_chapters
                where storyline_chapters.thread_slug = storyline_threads.thread_slug
            ),
            word_count = coalesce((
                select sum(word_count) from storyline_chapters
                where storyline_chapters.thread_slug = storyline_threads.thread_slug
            ), 0),
            last_chapter_at = (
                select max(published_at) from storyline_chapters
                where storyline_chapters.thread_slug = storyline_threads.thread_slug
            ),
            updated_at = current_timestamp
        """
    )


def load_all_seeds(db) -> dict[str, Any]:
    """Phase 1 + Phase 2 + aggregate refresh in a single call."""
    threads_written = load_thread_metadata(db)
    chapter_counts = load_chapters(db)
    refresh_thread_aggregates(db)
    return {
        "threads_written": threads_written,
        "chapter_counts": chapter_counts,
        "total_chapters": sum(chapter_counts.values()),
    }
