from __future__ import annotations

import logging
import time
from typing import Any

import requests


LOGGER = logging.getLogger(__name__)


class PullpushClient:
    """Pullpush-backed Reddit submission client.

    Method signatures intentionally mirror ``RedditPublicClient`` with added
    ``after`` and ``before`` Unix-second filters for retro backfills.
    """

    def __init__(self, base_url: str = "https://api.pullpush.io/reddit", timeout_seconds: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "cfb-rankings-site/retro-backfill"})

    def search_posts(
        self,
        query: str,
        subreddit: str | None = None,
        sort: str = "new",
        limit: int = 25,
        after: int | None = None,
        before: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "q": query,
            "subreddit": subreddit,
            "sort": _sort_direction(sort),
            "sort_type": "created_utc",
            "size": min(max(int(limit), 1), 100),
            "after": after,
            "before": before,
            "metadata": "true",
        }
        return self._get_submissions(params=params, subreddit=subreddit, after=after, before=before)

    def list_subreddit(
        self,
        subreddit: str,
        listing: str = "new",
        limit: int = 25,
        after: int | None = None,
        before: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "subreddit": subreddit,
            "sort": _sort_direction(listing),
            "sort_type": "created_utc",
            "size": min(max(int(limit), 1), 100),
            "after": after,
            "before": before,
            "metadata": "true",
        }
        return self._get_submissions(params=params, subreddit=subreddit, after=after, before=before)

    def search_comments(
        self,
        query: str,
        subreddit: str | None = None,
        sort: str = "new",
        limit: int = 25,
        after: int | None = None,
        before: int | None = None,
        link_id: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "q": query,
            "subreddit": subreddit,
            "link_id": _post_link_id(link_id) if link_id else None,
            "sort": _sort_direction(sort),
            "sort_type": "created_utc",
            "size": min(max(int(limit), 1), 100),
            "after": after,
            "before": before,
            "metadata": "true",
        }
        return self._get_comments(params=params, subreddit=subreddit, after=after, before=before)

    def list_post_comments(
        self,
        post_id: str,
        limit: int = 100,
        after: int | None = None,
        before: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "link_id": _post_link_id(post_id),
            "sort": "asc",
            "sort_type": "created_utc",
            "size": min(max(int(limit), 1), 100),
            "after": after,
            "before": before,
            "metadata": "true",
        }
        return self._get_comments(params=params, subreddit=None, after=after, before=before)

    def _get_submissions(
        self,
        *,
        params: dict[str, Any],
        subreddit: str | None,
        after: int | None,
        before: int | None,
    ) -> list[dict[str, Any]]:
        filtered = {key: value for key, value in params.items() if value is not None and value != ""}
        url = f"{self.base_url}/search/submission/"
        for attempt in range(5):
            try:
                response = self.session.get(url, params=filtered, timeout=self.timeout_seconds)
            except requests.RequestException as exc:
                if attempt < 4:
                    sleep_for = 2.0 * (2**attempt)
                    LOGGER.warning(
                        "Pullpush request failed for subreddit=%s after=%s before=%s; retrying in %.1fs",
                        subreddit or "all",
                        after,
                        before,
                        sleep_for,
                    )
                    time.sleep(sleep_for)
                    continue
                raise RuntimeError(str(exc)) from exc
            if response.status_code == 429 and attempt < 4:
                sleep_for = 2.0 * (2**attempt)
                LOGGER.warning(
                    "Pullpush 429 for subreddit=%s after=%s before=%s; retrying in %.1fs",
                    subreddit or "all",
                    after,
                    before,
                    sleep_for,
                )
                time.sleep(sleep_for)
                continue
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                LOGGER.warning(
                    "Pullpush partial-window error for subreddit=%s after=%s before=%s status=%s",
                    subreddit or "all",
                    after,
                    before,
                    response.status_code,
                )
                raise RuntimeError(str(exc)) from exc
            payload = response.json() if response.content else {}
            metadata = payload.get("metadata") if isinstance(payload, dict) else None
            if isinstance(metadata, dict) and metadata.get("timed_out"):
                raise RuntimeError(f"Pullpush timed out for subreddit={subreddit or 'all'} after={after} before={before}")
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, list):
                return []
            return [_normalize_submission(row) for row in data if isinstance(row, dict)]
        return []

    def _get_comments(
        self,
        *,
        params: dict[str, Any],
        subreddit: str | None,
        after: int | None,
        before: int | None,
    ) -> list[dict[str, Any]]:
        filtered = {key: value for key, value in params.items() if value is not None and value != ""}
        url = f"{self.base_url}/search/comment/"
        for attempt in range(5):
            try:
                response = self.session.get(url, params=filtered, timeout=self.timeout_seconds)
            except requests.RequestException as exc:
                if attempt < 4:
                    sleep_for = 2.0 * (2**attempt)
                    LOGGER.warning(
                        "Pullpush comments request failed for subreddit=%s after=%s before=%s; retrying in %.1fs",
                        subreddit or "all",
                        after,
                        before,
                        sleep_for,
                    )
                    time.sleep(sleep_for)
                    continue
                raise RuntimeError(str(exc)) from exc
            if response.status_code == 429 and attempt < 4:
                sleep_for = 2.0 * (2**attempt)
                LOGGER.warning(
                    "Pullpush comments 429 for subreddit=%s after=%s before=%s; retrying in %.1fs",
                    subreddit or "all",
                    after,
                    before,
                    sleep_for,
                )
                time.sleep(sleep_for)
                continue
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                LOGGER.warning(
                    "Pullpush comments partial-window error for subreddit=%s after=%s before=%s status=%s",
                    subreddit or "all",
                    after,
                    before,
                    response.status_code,
                )
                raise RuntimeError(str(exc)) from exc
            payload = response.json() if response.content else {}
            metadata = payload.get("metadata") if isinstance(payload, dict) else None
            if isinstance(metadata, dict) and metadata.get("timed_out"):
                raise RuntimeError(f"Pullpush comments timed out for subreddit={subreddit or 'all'} after={after} before={before}")
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, list):
                return []
            return [_normalize_comment(row) for row in data if isinstance(row, dict)]
        return []


def _sort_direction(value: str) -> str:
    normalized = (value or "new").strip().lower()
    if normalized in {"asc", "old", "oldest"}:
        return "asc"
    return "desc"


def _post_link_id(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text if text.startswith("t3_") else f"t3_{text}"


def _normalize_submission(row: dict[str, Any]) -> dict[str, Any]:
    permalink = str(row.get("permalink") or "")
    if permalink.startswith("https://www.reddit.com"):
        permalink = permalink.removeprefix("https://www.reddit.com")
    return {
        "name": row.get("name") or f"t3_{row.get('id', '')}",
        "id": row.get("id") or "",
        "title": row.get("title") or "",
        "selftext": row.get("selftext") or "",
        "author": row.get("author") or "",
        "author_fullname": row.get("author_fullname") or "",
        "subreddit": row.get("subreddit") or "",
        "permalink": permalink,
        "created_utc": float(row.get("created_utc") or 0),
        "ups": int(row.get("score") or row.get("ups") or 0),
        "num_comments": int(row.get("num_comments") or 0),
        "view_count": row.get("view_count"),
        "removed_by_category": row.get("removed_by_category"),
        "_provider": "pullpush",
        "_raw": row,
    }


def _normalize_comment(row: dict[str, Any]) -> dict[str, Any]:
    permalink = str(row.get("permalink") or "")
    if permalink.startswith("https://www.reddit.com"):
        permalink = permalink.removeprefix("https://www.reddit.com")
    comment_id = str(row.get("id") or "").strip()
    link_id = _post_link_id(str(row.get("link_id") or ""))
    return {
        "name": row.get("name") or f"t1_{comment_id}",
        "id": comment_id,
        "body": row.get("body") or "",
        "author": row.get("author") or "",
        "author_fullname": row.get("author_fullname") or "",
        "subreddit": row.get("subreddit") or "",
        "permalink": permalink,
        "created_utc": float(row.get("created_utc") or 0),
        "ups": int(row.get("score") or row.get("ups") or 0),
        "parent_id": row.get("parent_id") or link_id,
        "link_id": link_id,
        "author_flair_text": row.get("author_flair_text") or "",
        "author_flair_css_class": row.get("author_flair_css_class") or "",
        "removed_by_category": row.get("removed_by_category"),
        "_provider": "pullpush",
        "_raw": row,
    }
