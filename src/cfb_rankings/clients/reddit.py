from __future__ import annotations

from datetime import datetime
import html
import re
from typing import Any
from urllib.parse import urlparse, urlencode
from xml.etree import ElementTree as ET

import requests

from cfb_rankings.clients.base import JsonApiClient


class RedditPublicClient(JsonApiClient):
    def __init__(self, base_url: str = "https://www.reddit.com", timeout_seconds: float = 30.0) -> None:
        super().__init__(
            base_url=base_url,
            headers={
                # Reddit's public JSON endpoints are increasingly sensitive to
                # non-browser request profiles. A browser-like header set has
                # proven much more reliable from this environment.
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/135.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": f"{base_url.rstrip('/')}/r/CFB/",
            },
            timeout_seconds=timeout_seconds,
        )

    def search_posts(
        self,
        query: str,
        subreddit: str | None = None,
        sort: str = "new",
        limit: int = 25,
        after: int | None = None,
        before: int | None = None,
    ) -> list[dict[str, Any]]:
        path = f"/r/{subreddit}/search.json" if subreddit else "/search.json"
        params: dict[str, Any] = {
            "q": query,
            "sort": sort,
            "limit": limit,
            "restrict_sr": 1 if subreddit else 0,
            "type": "link",
            "raw_json": 1,
        }
        try:
            payload = self.get_json(path, params=params)
            return _listing_children(payload)
        except RuntimeError:
            return self._search_posts_rss(query=query, subreddit=subreddit, sort=sort, limit=limit)

    def list_subreddit(
        self,
        subreddit: str,
        listing: str = "new",
        limit: int = 25,
        after: int | None = None,
        before: int | None = None,
    ) -> list[dict[str, Any]]:
        try:
            payload = self.get_json(f"/r/{subreddit}/{listing}.json", params={"limit": limit, "raw_json": 1})
            return _listing_children(payload)
        except RuntimeError:
            return self._list_subreddit_rss(subreddit=subreddit, listing=listing, limit=limit)

    def _search_posts_rss(
        self,
        query: str,
        subreddit: str | None,
        sort: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        path = f"/r/{subreddit}/search.rss" if subreddit else "/search.rss"
        params: dict[str, Any] = {
            "q": query,
            "sort": sort,
        }
        if subreddit:
            params["restrict_sr"] = "on"
        feed_url = f"{self.base_url}{path}?{urlencode(params, doseq=True)}"
        return self._rss_entries(feed_url=feed_url, fallback_subreddit=subreddit, limit=limit)

    def _list_subreddit_rss(self, subreddit: str, listing: str, limit: int) -> list[dict[str, Any]]:
        if listing == "hot":
            path = f"/r/{subreddit}/.rss"
        else:
            path = f"/r/{subreddit}/{listing}/.rss"
        feed_url = f"{self.base_url}{path}"
        return self._rss_entries(feed_url=feed_url, fallback_subreddit=subreddit, limit=limit)

    def _rss_entries(self, feed_url: str, fallback_subreddit: str | None, limit: int) -> list[dict[str, Any]]:
        response = requests.get(
            feed_url,
            headers=self.headers,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        root = ET.fromstring(response.text)
        return _rss_listing_children(root=root, fallback_subreddit=fallback_subreddit, limit=limit)


def _listing_children(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    children = data.get("children")
    if not isinstance(children, list):
        return []
    results: list[dict[str, Any]] = []
    for child in children:
        if isinstance(child, dict) and isinstance(child.get("data"), dict):
            results.append(child["data"])
    return results


def _rss_listing_children(root: ET.Element, fallback_subreddit: str | None, limit: int) -> list[dict[str, Any]]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall("atom:entry", ns)
    results: list[dict[str, Any]] = []
    for entry in entries[:limit]:
        title = _rss_text(entry, "atom:title", ns)
        content_html = _rss_text(entry, "atom:content", ns)
        author_name = _rss_text(entry, "atom:author/atom:name", ns).replace("/u/", "").strip()
        entry_id = _rss_text(entry, "atom:id", ns)
        published = _rss_text(entry, "atom:published", ns) or _rss_text(entry, "atom:updated", ns)
        link_element = entry.find("atom:link", ns)
        link_href = link_element.attrib.get("href") if link_element is not None else ""
        permalink = _path_from_url(link_href)
        subreddit = _rss_entry_subreddit(entry, ns) or fallback_subreddit or ""
        created_utc = _iso_to_timestamp(published)
        body_text = _strip_html(content_html)
        results.append(
            {
                "name": entry_id,
                "id": entry_id.removeprefix("t3_") if entry_id.startswith("t3_") else entry_id,
                "title": title,
                "selftext": body_text,
                "author": author_name,
                "author_fullname": "",
                "subreddit": subreddit,
                "permalink": permalink,
                "created_utc": created_utc,
                "ups": 0,
                "num_comments": 0,
                "view_count": None,
                "removed_by_category": None,
            }
        )
    return results


def _rss_text(element: ET.Element, path: str, ns: dict[str, str]) -> str:
    child = element.find(path, ns)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _rss_entry_subreddit(entry: ET.Element, ns: dict[str, str]) -> str:
    category = entry.find("atom:category", ns)
    if category is None:
        return ""
    label = str(category.attrib.get("label") or "").strip()
    if label.startswith("r/"):
        return label[2:]
    term = str(category.attrib.get("term") or "").strip()
    return term


def _path_from_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    return parsed.path or url


def _iso_to_timestamp(value: str) -> float:
    text = value.strip()
    if not text:
        return 0.0
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _strip_html(value: str) -> str:
    if not value:
        return ""
    text = html.unescape(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
