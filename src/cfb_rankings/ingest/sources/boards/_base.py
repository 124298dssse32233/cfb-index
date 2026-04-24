"""Shared BoardRssAdapter for boards that expose a forum-listing RSS feed."""
from __future__ import annotations

import logging
from typing import Any

from cfb_rankings.ingest.sources.base import BaseRssAdapter
from cfb_rankings.ingest.sources.campus_news import CampusNewsAdapter


log = logging.getLogger(__name__)


class BoardRssAdapter(CampusNewsAdapter):
    """Base for message-board adapters.

    Subclasses set:
      - ``source_id``   (e.g. ``board_tigerdroppings``)
      - ``feed_url``    (forum listing RSS)
      - ``team_id``     (priority_teams.team_id)
    """

    source_id: str = ""
    feed_url: str = ""
    # Some boards expose an offset param on the RSS feed (e.g. ?p=2).
    # Subclasses that support pagination set this to a format string
    # with ``{page}`` placeholder; leave None if not supported.
    paginated_url_format: str | None = None
    max_backfill_pages: int = 5

    def __init__(self, db, team_id: int) -> None:
        self.team_id = team_id
        if not self.source_id or not self.feed_url:
            raise ValueError(
                f"{type(self).__name__} must set source_id + feed_url"
            )
        BaseRssAdapter.__init__(self, db)

    def row_from_entry(self, entry: Any) -> dict[str, Any] | None:
        row = super().row_from_entry(entry)
        if row is None:
            return None
        row.update({
            "source_id": self.source_id,
            "source_tier": "B",
            "author_identity_class": "pseudonymous",
            "demographic_slice": "hardcore_board",
            "retention_policy": "aggregated_only",
            "content_type": "thread_summary",
            "body_text": None,   # listing-only; body filled in via Cowork sweep
        })
        return row

    # ------------------------------------------------------------------
    # TASK 2.5 — best-effort historical backfill.
    # ------------------------------------------------------------------
    def backfill(self, since_days: int = 90) -> dict[str, int]:
        """Best-effort historical backfill of the public thread listing.

        Honest scope: RSS feeds for these boards typically cap at 20-50
        recent items regardless of query string. Pagination (when
        ``paginated_url_format`` is set) extends coverage but is still
        bounded by the board's own retention rules. ``since_days`` is
        advisory — we'll pull as many pages as the board exposes, up to
        ``self.max_backfill_pages``, then rely on ``row_from_entry`` to
        drop anything older than ``since_days``.

        Full multi-month historical coverage requires HTML scraping of
        forum listing pages, which is board-specific and pending.

        Returns a summary dict {pages_pulled, rows_written, rows_skipped}.
        """
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
        pages_pulled = 0
        rows_written = 0
        rows_skipped_old = 0

        urls: list[str] = [self.feed_url]
        if self.paginated_url_format:
            for p in range(2, self.max_backfill_pages + 1):
                urls.append(self.paginated_url_format.format(page=p))

        for url in urls:
            try:
                body = self.http_get(url)
            except Exception as exc:  # adapter-level errors: log + continue
                log.warning("%s backfill page %s failed: %s", self.source_id, url, exc)
                continue
            pages_pulled += 1

            try:
                rows = self.parse(body)
            except Exception as exc:
                log.warning("%s backfill page %s parse failed: %s", self.source_id, url, exc)
                continue

            fresh_rows: list[dict[str, Any]] = []
            for row in rows:
                published = row.get("published_at_utc")
                if published:
                    try:
                        pub_dt = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
                        if pub_dt < cutoff:
                            rows_skipped_old += 1
                            continue
                    except Exception:
                        pass
                fresh_rows.append(row)

            if fresh_rows:
                try:
                    rows_written += self.write_rows(fresh_rows)
                except Exception as exc:
                    log.warning("%s backfill write failed: %s", self.source_id, exc)
        log.info(
            "%s backfill: pages=%d rows=%d skipped_old=%d since_days=%d",
            self.source_id, pages_pulled, rows_written, rows_skipped_old, since_days,
        )
        return {
            "pages_pulled": pages_pulled,
            "rows_written": rows_written,
            "rows_skipped_old": rows_skipped_old,
        }


__all__ = ["BoardRssAdapter"]
