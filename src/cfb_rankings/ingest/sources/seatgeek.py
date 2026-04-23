"""SeatGeek get-in price + listing count adapter — TASK 2.4.

Pulls each priority_team's upcoming events (future home games + up to 3 away)
and stores the cheapest-listing price and total listing count per event snapshot.

Requires ``SEATGEEK_CLIENT_ID`` environment variable (free-tier key).
"""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.numeric_base import NumericSourceAdapter

logger = logging.getLogger(__name__)

_EVENTS_URL = (
    "https://api.seatgeek.com/2/events?"
    "performers.slug={slug}&per_page=10&client_id={client_id}"
)


class SeatGeekAdapter(NumericSourceAdapter):
    source_id = "seatgeek"
    adapter_version = "0.1.0"
    min_seconds_between_requests = 1.0

    def __init__(self, db: Database, client_id: str | None = None) -> None:
        super().__init__(db)
        self.client_id = client_id or os.environ.get("SEATGEEK_CLIENT_ID")
        if not self.client_id:
            logger.warning("SEATGEEK_CLIENT_ID not set — adapter.run() will error")

    def fetch(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        if not self.client_id:
            raise RuntimeError("SEATGEEK_CLIENT_ID env var is required")
        teams = self.db.query_all(
            "select team_id, seatgeek_team_slug from priority_teams "
            "where seatgeek_team_slug is not null"
        )
        out: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for t in teams:
            url = _EVENTS_URL.format(
                slug=urllib.parse.quote(t["seatgeek_team_slug"], safe=""),
                client_id=self.client_id,
            )
            try:
                data = json.loads(self.http_get(url).decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                logger.warning("seatgeek fetch failed for team %s: %s", t["team_id"], exc)
                continue
            out.append((t, data))
        return out

    def parse(self, raw: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        now_iso = _utcnow_iso()
        for team, data in raw:
            for event in (data.get("events") or []):
                stats = event.get("stats") or {}
                event_id = str(event.get("id") or "")
                event_label = event.get("title") or event.get("short_title") or event_id
                base = {
                    "entity_type": "seatgeek_event",
                    "entity_id": event_id,
                    "entity_label": event_label,
                    "observed_at_utc": now_iso,
                    "sample_window": "instant",
                    "capture_url": event.get("url"),
                    "canonical_url": event.get("url"),
                    "raw_payload_json": {
                        "team_id": team["team_id"],
                        "datetime_local": event.get("datetime_local"),
                        "stats": stats,
                    },
                }
                lowest = stats.get("lowest_price")
                if lowest is not None:
                    rows.append({
                        **base, "metric": "get_in_cents",
                        "value_numeric": float(int(lowest) * 100),
                    })
                listing = stats.get("listing_count")
                if listing is not None:
                    rows.append({
                        **base, "metric": "listing_count",
                        "value_numeric": float(int(listing)),
                        "dedup_key": self.make_dedup_key(
                            self.source_id, event_id, "listing_count", now_iso,
                        ),
                    })
        return rows


def _utcnow_iso() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["SeatGeekAdapter"]
