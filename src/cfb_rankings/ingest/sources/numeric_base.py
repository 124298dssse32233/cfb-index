"""Shared helper for Tier A numeric source adapters.

Every Tier A adapter writes to ``source_observations`` via this helper so the
provenance columns (source_id, source_tier, capture_url, dedup_key,
ingestion_adapter_version, raw_payload_json) are set consistently.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Sequence

from cfb_rankings.db import Database
from cfb_rankings.ingest.sources.base import SourceAdapter


class NumericSourceAdapter(SourceAdapter):
    """Base for adapters that land observations in ``source_observations``.

    Subclasses implement :meth:`fetch` + :meth:`parse`; :meth:`parse` returns
    ``list[dict]`` where each dict contains the keys in ``_WRITABLE_COLUMNS``.
    ``source_id`` / ``source_tier`` / ``ingestion_adapter_version`` are filled
    in automatically if the row omits them.
    """

    source_tier: str = "A"  # Tier A by default; overridden for Tier C (google_trends_dma, etc.)

    _WRITABLE_COLUMNS = (
        "source_id", "entity_type", "entity_id", "entity_label",
        "observed_at_utc", "metric", "value_numeric", "value_text",
        "sample_window", "source_tier", "ingestion_adapter_version",
        "capture_url", "canonical_url", "raw_payload_json", "dedup_key",
    )

    @staticmethod
    def make_dedup_key(source_id: str, entity_id: str | int | None, metric: str,
                       observed_at_utc: str, granularity: str = "hour") -> str:
        """Deterministic dedup key.

        Default granularity='hour' → truncate observed_at_utc to YYYY-MM-DDTHH.
        Pass 'day' for daily sources to collapse intra-day runs onto one row.
        """
        trim = {"hour": 13, "day": 10, "minute": 16, "full": 32}.get(granularity, 13)
        ts = (observed_at_utc or "")[:trim]
        basis = f"{source_id}|{entity_id or ''}|{metric}|{ts}"
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()

    def write_rows(self, rows: Sequence[dict[str, Any]]) -> int:
        written = 0
        for row in rows:
            full = {k: None for k in self._WRITABLE_COLUMNS}
            full.update({k: row.get(k) for k in row if k in self._WRITABLE_COLUMNS})
            full["source_id"] = full["source_id"] or self.source_id
            full["source_tier"] = full["source_tier"] or self.source_tier
            full["ingestion_adapter_version"] = (
                full["ingestion_adapter_version"] or self.adapter_version
            )
            if not full.get("metric") or not full.get("observed_at_utc"):
                continue
            if not full.get("dedup_key"):
                full["dedup_key"] = self.make_dedup_key(
                    full["source_id"], full.get("entity_id"),
                    full["metric"], full["observed_at_utc"],
                )
            if isinstance(full.get("raw_payload_json"), (dict, list)):
                full["raw_payload_json"] = json.dumps(full["raw_payload_json"], sort_keys=True)
            existing = self.db.query_one(
                "select source_observation_id from source_observations where dedup_key = :k",
                {"k": full["dedup_key"]},
            )
            if existing:
                continue
            self.db.execute(
                """
                insert into source_observations (
                    source_id, entity_type, entity_id, entity_label,
                    observed_at_utc, metric, value_numeric, value_text,
                    sample_window, source_tier, ingestion_adapter_version,
                    capture_url, canonical_url, raw_payload_json, dedup_key
                ) values (
                    :source_id, :entity_type, :entity_id, :entity_label,
                    :observed_at_utc, :metric, :value_numeric, :value_text,
                    :sample_window, :source_tier, :ingestion_adapter_version,
                    :capture_url, :canonical_url, :raw_payload_json, :dedup_key
                )
                """,
                full,
            )
            written += 1
        return written


__all__ = ["NumericSourceAdapter"]
