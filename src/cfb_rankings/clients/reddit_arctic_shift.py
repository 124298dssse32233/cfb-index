from __future__ import annotations

import logging
import time
from typing import Any

import requests


LOGGER = logging.getLogger(__name__)


class ArcticShiftClient:
    """Arctic Shift-backed Reddit submission client for historical backfills."""

    def __init__(
        self,
        base_url: str = "https://arctic-shift.photon-reddit.com/api",
        timeout_seconds: float = 30.0,
    ) -> None:
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
            "query": query,
            "subreddit": subreddit,
            "after": after,
            "before": before,
            "limit": min(max(int(limit), 1), 100),
            "sort": _sort_direction(sort),
        }
        return self._get_posts(params=params, subreddit=subreddit, after=after, before=before)

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
            "after": after,
            "before": before,
            "limit": min(max(int(limit), 1), 100),
            "sort": _sort_direction(listing),
        }
        return self._get_posts(params=params, subreddit=subreddit, after=after, before=before)

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
            "body": query,
            "subreddit": subreddit,
            "link_id": _post_link_id(link_id) if link_id else None,
            "after": after,
            "before": before,
            "limit": min(max(int(limit), 1), 100),
            "sort": _sort_direction(sort),
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
            "limit": min(max(int(limit), 1), 1000),
            "after": after,
            "before": before,
        }
        return self._get_comments(params=params, subreddit=None, after=after, before=before, tree=True)

    def _get_posts(
        self,
        *,
        params: dict[str, Any],
        subreddit: str | None,
        after: int | None,
        before: int | None,
    ) -> list[dict[str, Any]]:
        filtered = {key: value for key, value in params.items() if value is not None and value != ""}
        url = f"{self.base_url}/posts/search"
        for attempt in range(5):
            try:
                response = self.session.get(url, params=filtered, timeout=self.timeout_seconds)
            except requests.RequestException as exc:
                if attempt < 4:
                    sleep_for = 1.5 * (2**attempt)
                    LOGGER.warning(
                        "Arctic Shift request failed for subreddit=%s after=%s before=%s; retrying in %.1fs",
                        subreddit or "all",
                        after,
                        before,
                        sleep_for,
                    )
                    time.sleep(sleep_for)
                    continue
                raise RuntimeError(str(exc)) from exc
            if response.status_code == 429 and attempt < 4:
                sleep_for = _rate_limit_sleep_seconds(response, attempt)
                LOGGER.warning(
                    "Arctic Shift 429 for subreddit=%s after=%s before=%s; retrying in %.1fs",
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
                raise RuntimeError(str(exc)) from exc
            payload = response.json() if response.content else {}
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, list):
                return []
            return [_normalize_post(row) for row in data if isinstance(row, dict)]
        return []

    def _get_comments(
        self,
        *,
        params: dict[str, Any],
        subreddit: str | None,
        after: int | None,
        before: int | None,
        tree: bool = False,
    ) -> list[dict[str, Any]]:
        filtered = {key: value for key, value in params.items() if value is not None and value != ""}
        url = f"{self.base_url}/comments/tree" if tree else f"{self.base_url}/comments/search"
        for attempt in range(5):
            try:
                response = self.session.get(url, params=filtered, timeout=self.timeout_seconds)
            except requests.RequestException as exc:
                if attempt < 4:
                    sleep_for = 1.5 * (2**attempt)
                    LOGGER.warning(
                        "Arctic Shift comments request failed for subreddit=%s after=%s before=%s; retrying in %.1fs",
                        subreddit or "all",
                        after,
                        before,
                        sleep_for,
                    )
                    time.sleep(sleep_for)
                    continue
                raise RuntimeError(str(exc)) from exc
            if response.status_code == 429 and attempt < 4:
                sleep_for = _rate_limit_sleep_seconds(response, attempt)
                LOGGER.warning(
                    "Arctic Shift comments 429 for subreddit=%s after=%s before=%s; retrying in %.1fs",
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
                raise RuntimeError(str(exc)) from exc
            payload = response.json() if response.content else {}
            rows = _comment_rows(payload)
            return [_normalize_comment(row) for row in rows if isinstance(row, dict)]
        return []


def _sort_direction(value: str) -> str:
    normalized = (value or "new").strip().lower()
    if normalized in {"asc", "old", "oldest"}:
        return "asc"
    return "desc"


def _rate_limit_sleep_seconds(response: requests.Response, attempt: int) -> float:
    reset_header = response.headers.get("x-ratelimit-reset")
    if reset_header:
        try:
            return max(1.0, min(float(reset_header), 30.0))
        except ValueError:
            pass
    return 2.0 * (2**attempt)


def _post_link_id(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text if text.startswith("t3_") else f"t3_{text}"


def _comment_rows(payload: Any) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, dict) else payload
    rows: list[dict[str, Any]] = []
    _collect_comment_rows(data, rows)
    return rows


def _collect_comment_rows(value: Any, rows: list[dict[str, Any]]) -> None:
    if isinstance(value, list):
        for item in value:
            _collect_comment_rows(item, rows)
        return
    if not isinstance(value, dict):
        return
    if str(value.get("kind") or "").lower() == "more":
        return
    nested_data = value.get("data")
    if isinstance(nested_data, dict) and (nested_data.get("body") is not None or nested_data.get("id")):
        _collect_comment_rows(nested_data, rows)
        return
    body = value.get("body")
    if body is not None or value.get("id"):
        rows.append(value)
    for child_key in ("children", "replies"):
        child = value.get(child_key)
        if isinstance(child, dict) and "data" in child:
            _collect_comment_rows(child.get("data"), rows)
        else:
            _collect_comment_rows(child, rows)


def _normalize_post(row: dict[str, Any]) -> dict[str, Any]:
    post_id = str(row.get("id") or "").strip()
    subreddit = str(row.get("subreddit") or "").strip()
    permalink = str(row.get("permalink") or "").strip()
    if not permalink and subreddit and post_id:
        permalink = f"/r/{subreddit}/comments/{post_id}/"
    if permalink.startswith("https://www.reddit.com"):
        permalink = permalink.removeprefix("https://www.reddit.com")
    return {
        "name": row.get("name") or (f"t3_{post_id}" if post_id else ""),
        "id": post_id,
        "title": row.get("title") or "",
        "selftext": row.get("selftext") or "",
        "author": row.get("author") or "",
        "author_fullname": row.get("author_fullname") or "",
        "subreddit": subreddit,
        "permalink": permalink,
        "created_utc": float(row.get("created_utc") or 0),
        "ups": int(row.get("score") or row.get("ups") or 0),
        "num_comments": int(row.get("num_comments") or 0),
        "view_count": row.get("view_count"),
        "removed_by_category": row.get("removed_by_category"),
        "_provider": "arctic_shift",
        "_raw": row,
    }


def _normalize_comment(row: dict[str, Any]) -> dict[str, Any]:
    comment_id = str(row.get("id") or "").strip()
    subreddit = str(row.get("subreddit") or "").strip()
    link_id = _post_link_id(str(row.get("link_id") or ""))
    permalink = str(row.get("permalink") or "").strip()
    if permalink.startswith("https://www.reddit.com"):
        permalink = permalink.removeprefix("https://www.reddit.com")
    return {
        "name": row.get("name") or (f"t1_{comment_id}" if comment_id else ""),
        "id": comment_id,
        "body": row.get("body") or "",
        "author": row.get("author") or "",
        "author_fullname": row.get("author_fullname") or "",
        "subreddit": subreddit,
        "permalink": permalink,
        "created_utc": float(row.get("created_utc") or 0),
        "ups": int(row.get("score") or row.get("ups") or 0),
        "parent_id": row.get("parent_id") or link_id,
        "link_id": link_id,
        "author_flair_text": row.get("author_flair_text") or "",
        "author_flair_css_class": row.get("author_flair_css_class") or "",
        "removed_by_category": row.get("removed_by_category"),
        "_provider": "arctic_shift",
        "_raw": row,
    }
