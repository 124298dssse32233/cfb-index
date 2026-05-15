"""Adapter 3 — daily Arctic Shift retro pull (Sprint v5-1 Day 4).

Pulls same-MM-DD ± 2 days submissions from prior years (2014..current-1)
off Arctic Shift's public API. High-engagement posts (score ≥ 50) are
promoted into ``archive_threads``; lower-scoring posts land in
``conversation_documents`` tagged ``_provider='arctic_shift_retro'``.

Powers downstream surfaces:
  * S5 Today in CFB History (``/anniversary/today/``) — anchor of every
    offseason day.
  * S7 Saturdays Past — week-anchored anniversaries.
  * storyline-chapter / prompt-context "this week N years ago" manifests.

Design notes:
  * Subreddits scanned: ``r/CFB`` + ``r/cfb`` (we let Arctic Shift dedup
    submissions; if both surface, ON CONFLICT keeps the first).
  * Engagement threshold (``min_score``) is configurable for tests.
  * Date windows are inclusive ± 2 days around the same calendar day in
    each prior year — captures Saturday-night posts that bleed into
    Sunday and pre-game Friday hype.
  * Graceful on errors — single-year failures log and continue, total
    return reflects only successful pulls.
  * DB-tolerant: missing tables (archive_threads, conversation_documents)
    short-circuit to a zero-row result rather than crash.

Spec: IMPLEMENTATION_PLAN.md Part 5 Adapter 3 +
      DESIGN_AUDIT_2026_05_15_v5_4.md Part 5 (Adapter 3).
"""
from __future__ import annotations

import calendar
import datetime as _dt
import logging
import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

logger = logging.getLogger(__name__)

DEFAULT_SUBREDDITS: tuple[str, ...] = ("CFB", "cfb")
DEFAULT_MIN_SCORE = 50
DEFAULT_YEARS_BACK = 12
DEFAULT_DAY_WINDOW = 2  # ± N days around target MM-DD
DEFAULT_LIMIT_PER_QUERY = 100


def fetch_archive_retro(
    db: Any,
    *,
    today: date | None = None,
    years_back: int = DEFAULT_YEARS_BACK,
    subreddits: Iterable[str] = DEFAULT_SUBREDDITS,
    min_score: int = DEFAULT_MIN_SCORE,
    day_window: int = DEFAULT_DAY_WINDOW,
    client: Any = None,
    limit_per_query: int = DEFAULT_LIMIT_PER_QUERY,
) -> dict[str, int]:
    """Pull same-MM-DD ± N-days Reddit submissions from prior years.

    Args:
        db: ``cfb_rankings.db.Database`` instance.
        today: Date to anchor on. Defaults to current UTC date.
        years_back: How many prior years to scan (default 12).
        subreddits: Subreddits to query. Default ``('CFB', 'cfb')``.
        min_score: Engagement threshold for promotion to archive_threads.
            Posts at or above this score → archive_threads; lower → conversation_documents.
        day_window: Inclusive +/- day window around the target MM-DD.
        client: Optional pre-built ArcticShiftClient. Default constructs one.
        limit_per_query: Per-(year, subreddit) Arctic Shift page size.

    Returns:
        Stats dict ``{'years_scanned', 'posts_fetched', 'posts_promoted',
        'posts_archived_low_engagement', 'errors'}``.
    """
    today = today or _utc_today()
    if client is None:
        # Late import keeps the module test-importable even if requests is
        # missing at collection time.
        from cfb_rankings.clients.reddit_arctic_shift import ArcticShiftClient
        client = ArcticShiftClient()

    has_archive_threads = _table_exists(db, "archive_threads")
    has_conversation_documents = _table_exists(db, "conversation_documents")

    if not has_archive_threads and not has_conversation_documents:
        logger.warning(
            "fetch_archive_retro: neither archive_threads nor conversation_documents "
            "exist; nothing to write. Run apply-migrations first."
        )

    current_year = today.year
    start_year = current_year - years_back
    end_year_exclusive = current_year  # range stop — exclusive

    stats = {
        "years_scanned": 0,
        "posts_fetched": 0,
        "posts_promoted": 0,
        "posts_archived_low_engagement": 0,
        "errors": 0,
    }

    for year in range(start_year, end_year_exclusive):
        try:
            after_ts, before_ts = _year_day_window(year, today, day_window)
        except ValueError as exc:
            # Edge case: today is Feb 29 in a leap year; prior non-leap year
            # has no Feb 29. We snap to Feb 28 instead and re-derive.
            logger.debug(
                "fetch_archive_retro: year=%d date-window edge (%s); snapping",
                year, exc,
            )
            try:
                after_ts, before_ts = _year_day_window_safe(year, today, day_window)
            except Exception as inner_exc:  # noqa: BLE001
                logger.warning(
                    "fetch_archive_retro: year=%d date-window failed (%s); skipping",
                    year, inner_exc,
                )
                stats["errors"] += 1
                continue

        for subreddit in subreddits:
            try:
                rows = client.list_subreddit(
                    subreddit=subreddit,
                    limit=limit_per_query,
                    after=after_ts,
                    before=before_ts,
                )
            except Exception as exc:  # noqa: BLE001
                # Arctic Shift can return transient 5xx / network errors.
                # We log + continue rather than blow up the daily cron.
                logger.warning(
                    "fetch_archive_retro: list_subreddit(%s, %d) failed: %s",
                    subreddit, year, exc,
                )
                stats["errors"] += 1
                continue

            if not rows:
                continue

            stats["years_scanned"] = max(stats["years_scanned"], year - start_year + 1)
            stats["posts_fetched"] += len(rows)

            for row in rows:
                try:
                    score = int(row.get("ups") or row.get("score") or 0)
                except (TypeError, ValueError):
                    score = 0

                if score >= min_score and has_archive_threads:
                    if _insert_archive_thread(db, row, subreddit):
                        stats["posts_promoted"] += 1
                elif has_conversation_documents:
                    if _insert_conversation_document(db, row, subreddit):
                        stats["posts_archived_low_engagement"] += 1

    return stats


# ---------------------------------------------------------------------------
# Date / window helpers
# ---------------------------------------------------------------------------

def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _year_day_window(year: int, today: date, day_window: int) -> tuple[int, int]:
    """Return (after_ts, before_ts) Unix seconds for the same MM-DD ± window
    in the given year. Raises ValueError if the MM-DD doesn't exist for
    that year (Feb 29 in a non-leap year)."""
    target = date(year, today.month, today.day)
    return _bounds_around(target, day_window)


def _year_day_window_safe(year: int, today: date, day_window: int) -> tuple[int, int]:
    """Variant that snaps Feb 29 → Feb 28 for non-leap years."""
    month = today.month
    day = today.day
    if month == 2 and day == 29 and not calendar.isleap(year):
        day = 28
    target = date(year, month, day)
    return _bounds_around(target, day_window)


def _bounds_around(target: date, day_window: int) -> tuple[int, int]:
    after = datetime(target.year, target.month, target.day, tzinfo=timezone.utc) - timedelta(days=day_window)
    before = datetime(target.year, target.month, target.day, tzinfo=timezone.utc) + timedelta(days=day_window + 1)
    return int(after.timestamp()), int(before.timestamp())


# ---------------------------------------------------------------------------
# DB writers
# ---------------------------------------------------------------------------

def _table_exists(db: Any, table: str) -> bool:
    """Return True if a sqlite_master row for ``table`` exists. Tolerant of
    missing DB / API mismatch (returns False rather than raising)."""
    try:
        row = db.query_one(
            "select 1 as ok from sqlite_master where type='table' and name = :n",
            {"n": table},
        )
        return bool(row)
    except Exception as exc:  # noqa: BLE001 — graceful degradation
        logger.debug("fetch_archive_retro: table_exists(%s) failed: %s", table, exc)
        return False


def _insert_archive_thread(db: Any, post: dict[str, Any], subreddit: str) -> bool:
    """INSERT OR IGNORE one row into archive_threads. Returns True on insert."""
    external_id = (post.get("id") or "").strip()
    title = (post.get("title") or "").strip()
    if not external_id or not title:
        return False

    created_utc_float = float(post.get("created_utc") or 0)
    if created_utc_float <= 0:
        return False
    created_dt = datetime.fromtimestamp(created_utc_float, tz=timezone.utc)
    created_iso = created_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    iso_date = created_dt.strftime("%Y-%m-%d")
    iso_mm_dd = created_dt.strftime("%m-%d")
    season_year = _season_year_for_date(created_dt.date())

    permalink = post.get("permalink") or ""
    if permalink and not permalink.startswith("http"):
        permalink = f"https://www.reddit.com{permalink}"

    raw = post.get("_raw") if isinstance(post.get("_raw"), dict) else {}
    selftext = (post.get("selftext") or raw.get("selftext") or "").strip() or None
    link_url = raw.get("url") if isinstance(raw, dict) else None
    is_self = 1 if (raw.get("is_self") if isinstance(raw, dict) else False) else 0
    if not raw and selftext:
        # Best-effort: if there is selftext we'll mark it self.
        is_self = 1
    upvote_ratio = raw.get("upvote_ratio") if isinstance(raw, dict) else None
    flair = (raw.get("link_flair_text") if isinstance(raw, dict) else None) or None
    over_18 = 1 if (raw.get("over_18") if isinstance(raw, dict) else False) else 0
    locked = 1 if (raw.get("locked") if isinstance(raw, dict) else False) else 0

    params = {
        "subreddit": subreddit,
        "external_id": external_id,
        "title": title[:1024],
        "body_md": selftext,
        "permalink": permalink or None,
        "author": (post.get("author") or "").strip() or None,
        "created_utc": created_iso,
        "score": int(post.get("ups") or post.get("score") or 0),
        "num_comments": int(post.get("num_comments") or 0),
        "upvote_ratio": float(upvote_ratio) if upvote_ratio is not None else None,
        "flair": flair,
        "is_self": is_self,
        "link_url": link_url,
        "over_18": over_18,
        "locked": locked,
        "iso_date": iso_date,
        "iso_mm_dd": iso_mm_dd,
        "season_year": season_year,
    }

    try:
        db.execute(
            """
            insert into archive_threads (
                subreddit, external_id, title, body_md, permalink, author,
                created_utc, score, num_comments, upvote_ratio, flair,
                is_self, link_url, over_18, locked, iso_date, iso_mm_dd,
                season_year
            ) values (
                :subreddit, :external_id, :title, :body_md, :permalink, :author,
                :created_utc, :score, :num_comments, :upvote_ratio, :flair,
                :is_self, :link_url, :over_18, :locked, :iso_date, :iso_mm_dd,
                :season_year
            )
            on conflict (subreddit, external_id) do nothing
            """,
            params,
        )
        return True
    except sqlite3.IntegrityError:
        # ON CONFLICT in SQLite covers UNIQUE — but if a different constraint
        # tripped (FK), we silently skip rather than crash the cron.
        return False
    except Exception as exc:  # noqa: BLE001 — graceful per-row
        logger.warning(
            "fetch_archive_retro: archive_thread insert failed for %s/%s: %s",
            subreddit, external_id, exc,
        )
        return False


def _insert_conversation_document(db: Any, post: dict[str, Any], subreddit: str) -> bool:
    """Insert one low-engagement post into conversation_documents.

    Tagged with ``source_name='arctic_shift_retro'`` so callers can filter
    on the provenance flag.
    """
    external_id = (post.get("id") or "").strip()
    title = (post.get("title") or "").strip()
    if not external_id:
        return False

    created_utc_float = float(post.get("created_utc") or 0)
    if created_utc_float <= 0:
        return False
    created_iso = datetime.fromtimestamp(created_utc_float, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    permalink = post.get("permalink") or ""
    if permalink and not permalink.startswith("http"):
        permalink = f"https://www.reddit.com{permalink}"

    body_text = (post.get("selftext") or "").strip()
    if not body_text and not title:
        return False

    params = {
        "source_name": "arctic_shift_retro",
        "source_document_id": f"t3_{external_id}",
        "source_author_name": (post.get("author") or "").strip() or None,
        "source_channel": subreddit,
        "source_url": permalink or None,
        "content_type": "reddit_submission",
        "title_text": title[:1024] or None,
        "body_text": body_text[:8000] if body_text else None,
        "external_created_at_utc": created_iso,
    }

    try:
        db.execute(
            """
            insert into conversation_documents (
                source_name, source_document_id, source_author_name,
                source_channel, source_url, content_type, title_text,
                body_text, external_created_at_utc
            ) values (
                :source_name, :source_document_id, :source_author_name,
                :source_channel, :source_url, :content_type, :title_text,
                :body_text, :external_created_at_utc
            )
            on conflict (source_name, source_document_id) do nothing
            """,
            params,
        )
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as exc:  # noqa: BLE001 — graceful per-row
        logger.warning(
            "fetch_archive_retro: conversation_documents insert failed for %s/%s: %s",
            subreddit, external_id, exc,
        )
        return False


def _season_year_for_date(d: date) -> int | None:
    """Heuristic mapping of post date → CFB season year.

    CFB seasons run Aug → early January. We map:
      * Aug–Dec → that calendar year
      * Jan (CFP / bowl tail) → prior calendar year
      * Feb–Jul → null (offseason; no season anchor)
    """
    if d.month >= 8:
        return d.year
    if d.month == 1:
        return d.year - 1
    return None


__all__ = [
    "DEFAULT_SUBREDDITS",
    "DEFAULT_MIN_SCORE",
    "DEFAULT_YEARS_BACK",
    "DEFAULT_DAY_WINDOW",
    "DEFAULT_LIMIT_PER_QUERY",
    "fetch_archive_retro",
]
