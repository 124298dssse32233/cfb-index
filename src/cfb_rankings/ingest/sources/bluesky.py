"""Bluesky adapters — TASK 3.1 (firehose / Jetstream), 3.2 (curated + feeds),
3.3 (starter-pack harvester), 3.4 (social graph sampler).

All four write posts to ``conversation_documents`` with ``source_id`` set per
adapter:
- ``bluesky_firehose`` — posts matching keyword/handle filters, streamed
- ``bluesky_curated`` — ``getAuthorFeed`` for each handle in the curated list
- ``bluesky_feeds`` — ``getFeed`` for each subscribed custom feed URI
- ``bluesky_starterpack`` — harvests handles from public starter-pack URIs (utility)

Bluesky AppView REST base: https://public.api.bsky.app/xrpc/
Firehose / Jetstream: wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post

Tier B. All posts tagged ``demographic_slice=bluesky_post`` and
``author_identity_class=pseudonymous``. ``capture_url`` is the bsky.app post URL.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.parse
from typing import Any, Sequence

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.base import SourceAdapter

logger = logging.getLogger(__name__)

_APPVIEW = "https://public.api.bsky.app/xrpc"
_JETSTREAM = (
    "wss://jetstream2.us-east.bsky.network/subscribe"
    "?wantedCollections=app.bsky.feed.post"
)


def _post_url(handle: str, rkey: str) -> str:
    return f"https://bsky.app/profile/{handle}/post/{rkey}"


def _dedup(source_id: str, uri: str) -> str:
    return hashlib.sha1(f"{source_id}|{uri}".encode("utf-8")).hexdigest()


def _row_from_bsky_post(post: dict[str, Any], source_id: str,
                        adapter_version: str) -> dict[str, Any] | None:
    """Translate a Bluesky feed post dict into a conversation_documents row."""
    record = post.get("record") or post.get("post", {}).get("record") or {}
    if not record:
        return None
    uri = post.get("uri") or post.get("post", {}).get("uri") or ""
    if not uri:
        return None
    # Extract handle + rkey from URI: at://did:plc:.../app.bsky.feed.post/<rkey>
    author = post.get("author") or post.get("post", {}).get("author") or {}
    handle = author.get("handle") or ""
    rkey = uri.rsplit("/", 1)[-1] if "/" in uri else uri
    url = _post_url(handle, rkey) if handle and rkey else uri
    created = record.get("createdAt") or ""
    text = (record.get("text") or "").strip()
    if not text:
        return None
    return {
        "source_id": source_id,
        "source_tier": "B",
        "source_name": source_id,
        "source_document_id": f"bsky:{uri}",
        "content_type": "post",
        "title_text": None,
        "body_text": text[:4000],
        "external_created_at_utc": _normalize_iso(created),
        "source_author_name": handle,
        "author_identity_class": "pseudonymous",
        "source_url": url,
        "capture_url": url,
        "canonical_url": url,
        "retention_policy": "aggregated_only",
        "ingestion_adapter_version": adapter_version,
        "dedup_key": _dedup(source_id, uri),
        "demographic_slice": "bluesky_post",
        "language_code": (record.get("langs") or ["en"])[0],
        "is_deleted": 0,
        "is_removed": 0,
    }


def _normalize_iso(ts: str) -> str:
    if not ts:
        return ""
    # Strip fractional seconds if present
    if "." in ts and ts.endswith("Z"):
        return ts.split(".")[0] + "Z"
    return ts


# ------------------ base writer shared by all four adapters ------------------
class _BlueskyWriter(SourceAdapter):
    """Shared write_rows logic. Subclasses set source_id + implement fetch/parse."""

    adapter_version = "0.1.0"
    min_seconds_between_requests = 0.1

    def write_rows(self, rows: Sequence[dict[str, Any]]) -> int:
        written = 0
        for row in rows:
            if not row.get("body_text") or not row.get("external_created_at_utc"):
                continue
            existing = self.db.query_one(
                "select conversation_document_id from conversation_documents "
                "where dedup_key = :k", {"k": row["dedup_key"]},
            )
            if existing:
                continue
            self.db.execute(
                """
                insert into conversation_documents (
                    source_name, source_document_id, content_type, title_text, body_text,
                    external_created_at_utc, source_author_name, source_url, language_code,
                    is_deleted, is_removed,
                    source_id, source_tier, author_identity_class, capture_url,
                    canonical_url, retention_policy, ingestion_adapter_version,
                    dedup_key, demographic_slice
                ) values (
                    :source_name, :source_document_id, :content_type, :title_text, :body_text,
                    :external_created_at_utc, :source_author_name, :source_url, :language_code,
                    :is_deleted, :is_removed,
                    :source_id, :source_tier, :author_identity_class, :capture_url,
                    :canonical_url, :retention_policy, :ingestion_adapter_version,
                    :dedup_key, :demographic_slice
                )
                """,
                row,
            )
            written += 1
        return written


# ------------------ TASK 3.2: curated handles + public feeds ------------------
class BlueskyCuratedAdapter(_BlueskyWriter):
    """``app.bsky.feed.getAuthorFeed`` for each handle in ``priority_teams.bluesky_beat_handles``."""

    source_id = "bluesky_curated"

    def __init__(self, db: Database) -> None:
        super().__init__(db)

    def _gather_handles(self) -> list[tuple[int, str]]:
        rows = self.db.query_all(
            "select team_id, bluesky_beat_handles from priority_teams "
            "where bluesky_beat_handles is not null"
        )
        out: list[tuple[int, str]] = []
        for r in rows:
            try:
                handles = json.loads(r["bluesky_beat_handles"])
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            for h in handles or []:
                out.append((r["team_id"], h))
        return out

    def fetch(self) -> list[tuple[str, dict[str, Any]]]:
        handles = self._gather_handles()
        out: list[tuple[str, dict[str, Any]]] = []
        for _team_id, handle in handles:
            url = (f"{_APPVIEW}/app.bsky.feed.getAuthorFeed"
                   f"?actor={urllib.parse.quote(handle)}&limit=30")
            try:
                data = json.loads(self.http_get(url).decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                logger.warning("bluesky_curated getAuthorFeed failed for %s: %s", handle, exc)
                continue
            out.append((handle, data))
        return out

    def parse(self, raw: list[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for _handle, data in raw:
            for item in (data.get("feed") or []):
                row = _row_from_bsky_post(item.get("post", item),
                                           self.source_id, self.adapter_version)
                if row:
                    rows.append(row)
        return rows


class BlueskyFeedsAdapter(_BlueskyWriter):
    """``app.bsky.feed.getFeed`` for each subscribed public feed URI.

    Feed URIs live in ``seeds/bluesky_feeds.yaml``.
    """

    source_id = "bluesky_feeds"

    def __init__(self, db: Database, feed_uris: list[str] | None = None) -> None:
        super().__init__(db)
        self.feed_uris = feed_uris or _default_feed_uris()

    def fetch(self) -> list[tuple[str, dict[str, Any]]]:
        out: list[tuple[str, dict[str, Any]]] = []
        for uri in self.feed_uris:
            url = (f"{_APPVIEW}/app.bsky.feed.getFeed"
                   f"?feed={urllib.parse.quote(uri)}&limit=50")
            try:
                data = json.loads(self.http_get(url).decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                logger.warning("bluesky_feeds getFeed failed for %s: %s", uri, exc)
                continue
            out.append((uri, data))
        return out

    def parse(self, raw: list[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for _uri, data in raw:
            for item in (data.get("feed") or []):
                row = _row_from_bsky_post(item.get("post", item),
                                           self.source_id, self.adapter_version)
                if row:
                    rows.append(row)
        return rows


def _default_feed_uris() -> list[str]:
    # Known-public CFB feeds. Kept small; expand via quarterly harvest (TASK 3.3).
    return [
        # Generic sports
        "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/sports",
    ]


# ------------------ TASK 3.1: Jetstream firehose (keyword filtered) ------------------
class BlueskyFirehoseAdapter(_BlueskyWriter):
    """Streaming consumer — continuous Jetstream WebSocket with keyword + handle filter.

    NOT invoked by :meth:`run` (which assumes a bounded fetch). Instead, callers
    use :meth:`consume` with a stop condition. Designed to run under a supervisor
    (systemd / pm2) for hours at a time.
    """

    source_id = "bluesky_firehose"

    def __init__(self, db: Database,
                 keywords: Sequence[str] | None = None,
                 max_runtime_seconds: int = 3600,
                 flush_every_n: int = 50) -> None:
        super().__init__(db)
        self.keywords = tuple(k.lower() for k in (keywords or _default_keywords()))
        self.max_runtime_seconds = max_runtime_seconds
        self.flush_every_n = flush_every_n

    def fetch(self) -> list[dict[str, Any]]:
        """One bounded consume window. Use :meth:`consume` for long-running."""
        return self.consume()

    def parse(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # consume() returns conversation_document rows directly
        return raw

    def consume(self) -> list[dict[str, Any]]:
        try:
            import websocket  # type: ignore[import-not-found]
        except ImportError:
            logger.error("websocket-client not installed; bluesky firehose unavailable")
            return []

        collected: list[dict[str, Any]] = []
        start = time.monotonic()
        ws = websocket.create_connection(_JETSTREAM, timeout=30)
        try:
            while time.monotonic() - start < self.max_runtime_seconds:
                try:
                    frame = ws.recv()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("jetstream recv failed: %s", exc)
                    break
                try:
                    event = json.loads(frame)
                except json.JSONDecodeError:
                    continue
                post = self._event_to_post(event)
                if post is None:
                    continue
                text = (post.get("record") or {}).get("text") or ""
                if not any(kw in text.lower() for kw in self.keywords):
                    continue
                row = _row_from_bsky_post(post, self.source_id, self.adapter_version)
                if row:
                    collected.append(row)
                if len(collected) >= self.flush_every_n:
                    self.write_rows(collected)
                    collected = []
        finally:
            try:
                ws.close()
            except Exception:  # noqa: BLE001
                pass
        return collected

    @staticmethod
    def _event_to_post(event: dict[str, Any]) -> dict[str, Any] | None:
        """Jetstream payload → a shape compatible with _row_from_bsky_post."""
        if event.get("kind") != "commit":
            return None
        commit = event.get("commit") or {}
        if commit.get("collection") != "app.bsky.feed.post":
            return None
        if commit.get("operation") != "create":
            return None
        did = event.get("did") or ""
        rkey = commit.get("rkey") or ""
        record = commit.get("record") or {}
        return {
            "uri": f"at://{did}/app.bsky.feed.post/{rkey}",
            "record": record,
            "author": {"handle": did, "did": did},
        }


def _default_keywords() -> list[str]:
    # Broad-but-not-too-broad CFB filter. Expand via curated list later.
    return [
        "college football", "cfb", "ncaa football", "kickoff",
        "heisman", "cfp", "bowl game", "recruiting", "transfer portal",
    ]


# ------------------ TASK 3.3: starter-pack harvester ------------------
class BlueskyStarterPackHarvester:
    """Utility (not a SourceAdapter) — reads a list of starter-pack URIs and
    appends the handles to ``priority_teams.bluesky_beat_handles`` (or returns
    them for audit).

    Starter pack shape:
    at://{creator_did}/app.bsky.graph.starterpack/{rkey}
    """

    def __init__(self, db: Database, user_agent: str = "CFBIndex-FanIntel/0.1") -> None:
        self.db = db
        self.user_agent = user_agent

    def harvest(self, pack_uris: Sequence[str]) -> list[str]:
        """Return flat list of distinct handles across all supplied packs."""
        from urllib.request import Request, urlopen
        handles: set[str] = set()
        for uri in pack_uris:
            url = (f"{_APPVIEW}/app.bsky.graph.getStarterPack"
                   f"?starterPack={urllib.parse.quote(uri)}")
            try:
                req = Request(url, headers={"User-Agent": self.user_agent})
                with urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                logger.warning("starter-pack fetch failed for %s: %s", uri, exc)
                continue
            for item in ((data.get("starterPack") or {}).get("listItemsSample") or []):
                subj = item.get("subject") or {}
                h = subj.get("handle")
                if h:
                    handles.add(h)
        return sorted(handles)


# ------------------ TASK 3.4: social graph sampler ------------------
class BlueskyGraphSampler:
    """For each team's beat-writer handles, sample follower intersection and
    emit candidate fan handles that follow ≥2 beat writers.

    Utility, not an SourceAdapter — called from a CLI command. Writes to a
    follow-up table ``bluesky_candidate_handles`` (to be created in a future
    migration). For this session we return the list for logging only.
    """

    def __init__(self, db: Database, user_agent: str = "CFBIndex-FanIntel/0.1",
                 max_followers_per_writer: int = 500) -> None:
        self.db = db
        self.user_agent = user_agent
        self.max_followers = max_followers_per_writer

    def _get_followers(self, handle: str) -> list[str]:
        from urllib.request import Request, urlopen
        url = (f"{_APPVIEW}/app.bsky.graph.getFollowers"
               f"?actor={urllib.parse.quote(handle)}&limit={self.max_followers}")
        try:
            req = Request(url, headers={"User-Agent": self.user_agent})
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("getFollowers failed for %s: %s", handle, exc)
            return []
        return [f.get("handle") for f in (data.get("followers") or []) if f.get("handle")]

    def sample_team(self, beat_handles: Sequence[str],
                    min_intersection: int = 2) -> list[str]:
        if len(beat_handles) < min_intersection:
            return []
        counts: dict[str, int] = {}
        for h in beat_handles:
            for follower in self._get_followers(h):
                counts[follower] = counts.get(follower, 0) + 1
        return sorted([h for h, c in counts.items() if c >= min_intersection])


__all__ = [
    "BlueskyCuratedAdapter", "BlueskyFeedsAdapter", "BlueskyFirehoseAdapter",
    "BlueskyStarterPackHarvester", "BlueskyGraphSampler",
]
