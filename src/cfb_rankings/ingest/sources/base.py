"""SourceAdapter base class for Fan Intelligence ingest (STRATEGY §2).

Every adapter — Tier A numeric pull, Tier B conversation collector, RSS mirror,
Cowork manual playbook import — subclasses :class:`SourceAdapter` and implements
``fetch`` / ``parse`` / ``write_rows``. The base class provides:

* a retry + backoff policy keyed on ``max_attempts`` / ``backoff_seconds``
* a health-beacon writer that records one row in ``scrape_health`` per run
* a ``run()`` convenience that chains fetch → parse → write_rows under
  exception capture so partial failures still produce a health row

``BaseRssAdapter`` is a concrete helper for the ~40 RSS sources (beat writers,
campus papers, Substacks, athletics sites, Google News, Locked On). It handles
feed fetching and gives subclasses a single ``row_from_entry`` hook.
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Iterable, Sequence
from urllib.request import Request, urlopen

from cfb_rankings.db import Database

logger = logging.getLogger(__name__)


_DEFAULT_USER_AGENT = "CFBIndex-FanIntel/0.1 (+https://cfb-index.com)"


@dataclasses.dataclass(frozen=True)
class AdapterRunResult:
    source_id: str
    status: str  # ok | empty | error | skipped
    rows_inserted: int = 0
    error_message: str | None = None
    adapter_version: str | None = None
    run_started_at_utc: str | None = None
    run_finished_at_utc: str | None = None


class SourceAdapter(ABC):
    """Abstract adapter. Subclasses declare ``source_id`` + ``adapter_version``.

    Lifecycle:

        raw  = adapter.fetch()
        rows = adapter.parse(raw)
        n    = adapter.write_rows(rows)
        adapter.health_check(result)

    :meth:`run` wraps all four with exception capture + a health-beacon write.
    """

    source_id: str = ""
    adapter_version: str = "0.1.0"
    max_attempts: int = 3
    backoff_seconds: float = 2.0
    # Soft rate-limit between fetch() retries. Adapters hitting APIs with hard
    # quotas (YouTube, CFBD) should override _inter_request_sleep instead.
    min_seconds_between_requests: float = 0.0
    user_agent: str = _DEFAULT_USER_AGENT

    def __init__(self, db: Database) -> None:
        if not self.source_id:
            raise ValueError(f"{type(self).__name__} must set source_id")
        self.db = db
        self._last_request_at: float | None = None

    # --- lifecycle hooks -------------------------------------------------
    @abstractmethod
    def fetch(self) -> Any:
        """Pull raw payload(s). Network I/O lives here."""

    @abstractmethod
    def parse(self, raw: Any) -> list[dict[str, Any]]:
        """Convert raw payload to list of row dicts ready for write_rows."""

    @abstractmethod
    def write_rows(self, rows: Sequence[dict[str, Any]]) -> int:
        """Persist rows; return count actually written. Must be idempotent."""

    # --- utilities -------------------------------------------------------
    def _inter_request_sleep(self) -> None:
        if self.min_seconds_between_requests <= 0:
            return
        if self._last_request_at is None:
            self._last_request_at = time.monotonic()
            return
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.min_seconds_between_requests - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_request_at = time.monotonic()

    def http_get(self, url: str, *, timeout: float = 30.0, headers: dict[str, str] | None = None) -> bytes:
        """Minimal dependency-free GET with our User-Agent + retry policy."""
        merged = {"User-Agent": self.user_agent, "Accept": "*/*"}
        if headers:
            merged.update(headers)
        last_exc: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            self._inter_request_sleep()
            try:
                req = Request(url, headers=merged)
                with urlopen(req, timeout=timeout) as resp:
                    return resp.read()
            except Exception as exc:  # noqa: BLE001 — retries cover all network failures
                last_exc = exc
                logger.warning(
                    "http_get failed (attempt %d/%d) for %s: %s",
                    attempt, self.max_attempts, url, exc,
                )
                if attempt < self.max_attempts:
                    time.sleep(self.backoff_seconds * attempt)
        assert last_exc is not None
        raise last_exc

    def health_check(self, result: AdapterRunResult) -> None:
        """Write one row into scrape_health. Idempotent per (source_id, run_date)."""
        run_date = (result.run_started_at_utc or _utcnow_iso())[:10]
        self.db.execute(
            """
            insert into scrape_health (
                source_id, run_date, rows_inserted, status, error_message,
                run_started_at_utc, run_finished_at_utc, adapter_version
            ) values (
                :source_id, :run_date, :rows_inserted, :status, :error_message,
                :run_started_at_utc, :run_finished_at_utc, :adapter_version
            )
            on conflict (source_id, run_date) do update set
                rows_inserted = excluded.rows_inserted,
                status = excluded.status,
                error_message = excluded.error_message,
                run_started_at_utc = excluded.run_started_at_utc,
                run_finished_at_utc = excluded.run_finished_at_utc,
                adapter_version = excluded.adapter_version
            """,
            {
                "source_id": result.source_id,
                "run_date": run_date,
                "rows_inserted": result.rows_inserted,
                "status": result.status,
                "error_message": result.error_message,
                "run_started_at_utc": result.run_started_at_utc,
                "run_finished_at_utc": result.run_finished_at_utc,
                "adapter_version": result.adapter_version,
            },
        )

    # --- orchestration ---------------------------------------------------
    def run(self) -> AdapterRunResult:
        started = _utcnow_iso()
        try:
            raw = self.fetch()
            rows = self.parse(raw)
            n = self.write_rows(rows)
            status = "ok" if n > 0 else "empty"
            result = AdapterRunResult(
                source_id=self.source_id,
                status=status,
                rows_inserted=n,
                adapter_version=self.adapter_version,
                run_started_at_utc=started,
                run_finished_at_utc=_utcnow_iso(),
            )
        except Exception as exc:  # noqa: BLE001 — we want every failure to produce a health row
            logger.exception("adapter %s failed", self.source_id)
            result = AdapterRunResult(
                source_id=self.source_id,
                status="error",
                rows_inserted=0,
                error_message=f"{type(exc).__name__}: {exc}",
                adapter_version=self.adapter_version,
                run_started_at_utc=started,
                run_finished_at_utc=_utcnow_iso(),
            )
        self.health_check(result)
        return result


class BaseRssAdapter(SourceAdapter):
    """Shared bones for the 40+ RSS adapters. Subclasses supply ``feed_url`` and
    ``row_from_entry``. We parse with stdlib only (``xml.etree``) to avoid a
    feedparser dep; RSS 2.0 and Atom are both supported.
    """

    feed_url: str = ""

    def fetch(self) -> bytes:
        if not self.feed_url:
            raise ValueError(f"{type(self).__name__} must set feed_url")
        return self.http_get(self.feed_url)

    def parse(self, raw: bytes) -> list[dict[str, Any]]:
        import xml.etree.ElementTree as ET

        root = ET.fromstring(raw)
        entries: list[dict[str, Any]] = []
        # RSS 2.0: channel/item ; Atom: feed/entry
        items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
        for item in items:
            row = self.row_from_entry(item)
            if row is not None:
                entries.append(row)
        return entries

    def row_from_entry(self, entry: Any) -> dict[str, Any] | None:
        """Override to translate one RSS/Atom entry into a row dict."""
        raise NotImplementedError


def _utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["SourceAdapter", "BaseRssAdapter", "AdapterRunResult"]
