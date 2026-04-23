"""Kalshi + Polymarket prediction-market adapters — TASK 2.6.

Both pull CFB-relevant contracts (CFP champion, Heisman, conference titles,
select game markets) and store last price + 24h volume as source_observations.
Kalshi exposes a free public REST API; Polymarket exposes GraphQL at
https://gamma-api.polymarket.com/markets.

Kalshi contracts are identified by ``ticker`` (e.g. ``KXCFBCHAMP-26``).
Polymarket markets by ``slug`` (e.g. ``cfb-2026-heisman``). Both systems require
a pre-curated list (maintained in ``seeds/prediction_market_contracts.yaml``)
because the APIs are huge and we only care about ~40 contracts at any time.

``predict_thin`` (Tier C) filtering happens downstream in the aggregator —
rows with volume_usd < $1000 are labeled tier=C at aggregation time. Raw
rows land at tier=A regardless.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.numeric_base import NumericSourceAdapter

logger = logging.getLogger(__name__)

_KALSHI_MARKET_URL = "https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}"
_POLYMARKET_URL = "https://gamma-api.polymarket.com/markets?slug={slug}"

_CONTRACTS_SEED = Path(__file__).resolve().parents[3].parent / "seeds" / "prediction_market_contracts.yaml"


def _load_contracts(platform: str) -> list[dict[str, Any]]:
    if not _CONTRACTS_SEED.exists():
        return []
    doc = yaml.safe_load(_CONTRACTS_SEED.read_text(encoding="utf-8")) or {}
    return [c for c in (doc.get("contracts") or []) if c.get("platform") == platform]


class KalshiAdapter(NumericSourceAdapter):
    source_id = "kalshi"
    adapter_version = "0.1.0"
    min_seconds_between_requests = 0.5

    def fetch(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        out: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for contract in _load_contracts("kalshi"):
            url = _KALSHI_MARKET_URL.format(ticker=contract["ticker"])
            try:
                data = json.loads(self.http_get(url).decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                logger.warning("kalshi fetch failed for %s: %s", contract["ticker"], exc)
                continue
            out.append((contract, data))
        return out

    def parse(self, raw: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        now = _utcnow_iso()
        for contract, data in raw:
            market = data.get("market") or data  # envelope varies
            ticker = market.get("ticker") or contract["ticker"]
            url = f"https://kalshi.com/markets/{ticker}"
            base = {
                "entity_type": "kalshi_contract",
                "entity_id": ticker,
                "entity_label": contract.get("label") or ticker,
                "observed_at_utc": now,
                "sample_window": "instant",
                "capture_url": url,
                "canonical_url": url,
                "raw_payload_json": market,
            }
            last = market.get("last_price")
            vol = market.get("volume_24h") or market.get("volume")
            if last is not None:
                rows.append({**base, "metric": "last_price_cents", "value_numeric": float(last)})
            if vol is not None:
                rows.append({
                    **base, "metric": "volume_usd",
                    "value_numeric": float(vol),
                    "dedup_key": self.make_dedup_key(self.source_id, ticker, "volume_usd", now),
                })
        return rows


class PolymarketAdapter(NumericSourceAdapter):
    source_id = "polymarket"
    adapter_version = "0.1.0"
    min_seconds_between_requests = 0.5

    def fetch(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        out: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for contract in _load_contracts("polymarket"):
            url = _POLYMARKET_URL.format(slug=contract["slug"])
            try:
                data = json.loads(self.http_get(url).decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                logger.warning("polymarket fetch failed for %s: %s", contract["slug"], exc)
                continue
            out.append((contract, data))
        return out

    def parse(self, raw: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        now = _utcnow_iso()
        for contract, data in raw:
            markets = data if isinstance(data, list) else [data]
            for m in markets:
                slug = m.get("slug") or contract["slug"]
                url = f"https://polymarket.com/event/{slug}"
                base = {
                    "entity_type": "polymarket_market",
                    "entity_id": slug,
                    "entity_label": contract.get("label") or m.get("question") or slug,
                    "observed_at_utc": now,
                    "sample_window": "instant",
                    "capture_url": url,
                    "canonical_url": url,
                    "raw_payload_json": m,
                }
                outcomes = m.get("outcomePrices") or m.get("outcomes") or []
                if outcomes:
                    try:
                        prob_yes = float(outcomes[0]) if isinstance(outcomes[0], (int, float, str)) else None
                    except (ValueError, TypeError):
                        prob_yes = None
                    if prob_yes is not None:
                        rows.append({**base, "metric": "prob_yes", "value_numeric": prob_yes})
                vol = m.get("volume") or m.get("volumeNum")
                if vol is not None:
                    rows.append({
                        **base, "metric": "volume_usd",
                        "value_numeric": float(vol),
                        "dedup_key": self.make_dedup_key(self.source_id, slug, "volume_usd", now),
                    })
        return rows


def _utcnow_iso() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["KalshiAdapter", "PolymarketAdapter"]
