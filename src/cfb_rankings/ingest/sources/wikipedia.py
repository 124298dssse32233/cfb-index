"""Wikipedia pageviews + edits adapters — TASK 2.2, 2.3.

Writes to ``source_observations`` via :class:`NumericSourceAdapter`. Per-team
entities are read from ``priority_teams`` (columns ``wiki_team_page``,
``wiki_coach_page``, ``wiki_qb_page``). One row per (page, day).

API docs:
    https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/...
    https://en.wikipedia.org/w/api.php?action=query&list=usercontribs (edits)

These APIs are free, don't require auth, and return JSON.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import urllib.parse
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.numeric_base import NumericSourceAdapter

logger = logging.getLogger(__name__)

_PAGEVIEWS_BASE = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
    "en.wikipedia/all-access/all-agents/{article}/daily/{start}/{end}"
)

_EDITS_BASE = (
    "https://en.wikipedia.org/w/api.php"
    "?action=query&format=json&prop=revisions&titles={title}"
    "&rvlimit=max&rvprop=timestamp%7Csize&rvstart={rvstart}&rvend={rvend}"
)


def _yyyymmdd(d: _dt.date) -> str:
    return d.strftime("%Y%m%d")


def _iso_day(d: _dt.date) -> str:
    return d.strftime("%Y-%m-%dT00:00:00Z")


def _fetch_priority_pages(db: Database) -> list[dict[str, Any]]:
    """Return [{team_id, article, page_kind}] for every wiki_* page populated."""
    rows = db.query_all(
        """
        select team_id, wiki_team_page, wiki_coach_page, wiki_qb_page
        from priority_teams
        """
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        for kind_col, kind in (
            ("wiki_team_page", "team"),
            ("wiki_coach_page", "coach"),
            ("wiki_qb_page", "qb"),
        ):
            article = r.get(kind_col)
            if article:
                out.append({
                    "team_id": r["team_id"],
                    "article": article,
                    "page_kind": kind,
                })
    return out


class WikipediaPageviewsAdapter(NumericSourceAdapter):
    """Daily Wikipedia pageviews for every wiki_* page in priority_teams."""

    source_id = "wiki_pv"
    adapter_version = "0.1.0"
    min_seconds_between_requests = 0.5  # Wikimedia asks for <200/s; be polite

    def __init__(self, db: Database, lookback_days: int = 7) -> None:
        super().__init__(db)
        self.lookback_days = lookback_days

    def fetch(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        pages = _fetch_priority_pages(self.db)
        end = _dt.date.today()
        start = end - _dt.timedelta(days=self.lookback_days)
        payloads: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for page in pages:
            article = urllib.parse.quote(page["article"], safe="")
            url = _PAGEVIEWS_BASE.format(
                article=article, start=_yyyymmdd(start), end=_yyyymmdd(end),
            )
            try:
                data = json.loads(self.http_get(url).decode("utf-8"))
            except Exception as exc:  # noqa: BLE001 — single-page failure should not abort run
                logger.warning("wiki_pv fetch failed for %s: %s", page["article"], exc)
                continue
            payloads.append((page, data))
        return payloads

    def parse(self, raw: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for page, data in raw:
            for item in (data.get("items") or []):
                ts = item.get("timestamp")  # "YYYYMMDDHH"
                if not ts or len(ts) < 8:
                    continue
                obs_day = f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}T00:00:00Z"
                out.append({
                    "entity_type": f"wiki_{page['page_kind']}",
                    "entity_id": str(page["team_id"]),
                    "entity_label": page["article"],
                    "observed_at_utc": obs_day,
                    "metric": "pageviews",
                    "value_numeric": float(item.get("views", 0)),
                    "sample_window": "1d",
                    "capture_url": f"https://en.wikipedia.org/wiki/{page['article']}",
                    "canonical_url": f"https://en.wikipedia.org/wiki/{page['article']}",
                    "raw_payload_json": item,
                })
        return out


class WikipediaEditsAdapter(NumericSourceAdapter):
    """Daily edit count + byte-change sum per tracked page."""

    source_id = "wiki_edits"
    adapter_version = "0.1.0"
    min_seconds_between_requests = 0.5

    def __init__(self, db: Database, lookback_days: int = 7) -> None:
        super().__init__(db)
        self.lookback_days = lookback_days

    def fetch(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        pages = _fetch_priority_pages(self.db)
        end = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)
        start = end - _dt.timedelta(days=self.lookback_days)
        payloads: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for page in pages:
            title = urllib.parse.quote(page["article"], safe="")
            url = _EDITS_BASE.format(
                title=title,
                rvstart=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                rvend=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            try:
                data = json.loads(self.http_get(url).decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                logger.warning("wiki_edits fetch failed for %s: %s", page["article"], exc)
                continue
            payloads.append((page, data))
        return payloads

    def parse(self, raw: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for page, data in raw:
            pages_dict = (data.get("query") or {}).get("pages") or {}
            daily_counts: dict[str, int] = {}
            daily_size_delta: dict[str, int] = {}
            prev_size_per_day: dict[str, int] = {}
            for _, page_entry in pages_dict.items():
                revs = page_entry.get("revisions") or []
                # Revisions come newest-first; reverse to iterate in time order
                revs_sorted = sorted(revs, key=lambda r: r.get("timestamp", ""))
                for rev in revs_sorted:
                    ts = rev.get("timestamp") or ""
                    if len(ts) < 10:
                        continue
                    day = ts[:10]
                    daily_counts[day] = daily_counts.get(day, 0) + 1
                    size = int(rev.get("size", 0))
                    if day in prev_size_per_day:
                        daily_size_delta[day] = daily_size_delta.get(day, 0) + abs(size - prev_size_per_day[day])
                    prev_size_per_day[day] = size
            for day, n in daily_counts.items():
                obs = f"{day}T00:00:00Z"
                base = {
                    "entity_type": f"wiki_{page['page_kind']}",
                    "entity_id": str(page["team_id"]),
                    "entity_label": page["article"],
                    "observed_at_utc": obs,
                    "sample_window": "1d",
                    "capture_url": f"https://en.wikipedia.org/wiki/{page['article']}?action=history",
                    "canonical_url": f"https://en.wikipedia.org/wiki/{page['article']}",
                    "raw_payload_json": {"rev_count": n, "byte_delta": daily_size_delta.get(day, 0)},
                }
                out.append({**base, "metric": "edits", "value_numeric": float(n)})
                out.append({
                    **base, "metric": "byte_delta",
                    "value_numeric": float(daily_size_delta.get(day, 0)),
                    "dedup_key": self.make_dedup_key(
                        self.source_id, base["entity_id"], "byte_delta", obs, "day",
                    ),
                })
        return out


__all__ = ["WikipediaPageviewsAdapter", "WikipediaEditsAdapter"]
