"""team_cohort_week aggregator — STRATEGY §4 / TASK 5.7.

For a given week (YYYY-WW) and each (team_id, cohort) pair, compute:

    effective_n    = Σ  source.cohort_weights[cohort]  over contributing docs
    sentiment_score = Σ  sentiment * weight / effective_n    (NULL if below floor)
    volume          = raw doc count contributing (weight > 0)
    confidence_tier = worst tier (A..D) among contributing sources

Floor rule (STRATEGY §4):

    effective_n < 30  → sentiment_score = NULL (UI shows rank / "Awaiting Signal")
    30 ≤ n < 100      → publish with sample-size badge  (confidence_floor='sample')
    n ≥ 100           → publish at standard styling      (confidence_floor='ok')

Tier-C ratchet (STRATEGY §6): if any contributing source has tier=C,
``confidence_tier`` is clamped to C regardless of effective_n. Tier D doesn't
contribute to numeric aggregation — D sources are citation-only.

CLI: ``python manage.py compute-cohort-week --week=YYYY-WW``.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from cfb_rankings.db import Database

logger = logging.getLogger(__name__)

# The full cohort catalog per STRATEGY §4. New cohorts must be added here AND
# in the source_registry.cohort_weights JSON to flow through.
COHORTS: tuple[str, ...] = (
    "boomer_gen_x", "millennial", "gen_z", "college_age",
    "analytics", "recruiting", "gambling", "casual_vibes", "die_hard", "media_class",
    "local_market", "national_narrative", "alumni_diaspora", "hbcu_community",
)

FLOOR_MIN = 30.0
FLOOR_STANDARD = 100.0

TIER_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}


@dataclass
class CohortCell:
    effective_n: float = 0.0
    weighted_sentiment_sum: float = 0.0
    weight_sum_for_sentiment: float = 0.0
    volume: int = 0
    worst_tier: str = "A"
    top_source_ids: dict[str, float] | None = None

    def add(self, weight: float, sentiment: float | None, source_id: str, tier: str) -> None:
        if weight <= 0:
            return
        self.effective_n += weight
        self.volume += 1
        if sentiment is not None:
            self.weighted_sentiment_sum += sentiment * weight
            self.weight_sum_for_sentiment += weight
        if TIER_ORDER.get(tier, 99) > TIER_ORDER.get(self.worst_tier, -1):
            self.worst_tier = tier
        if self.top_source_ids is None:
            self.top_source_ids = {}
        self.top_source_ids[source_id] = self.top_source_ids.get(source_id, 0.0) + weight

    def sentiment(self) -> float | None:
        if self.effective_n < FLOOR_MIN:
            return None
        if self.weight_sum_for_sentiment <= 0:
            return None
        return self.weighted_sentiment_sum / self.weight_sum_for_sentiment

    def confidence_tier(self) -> str:
        # worst_tier already represents the worst contributing numeric source.
        # Tier D sources never enter here (filtered upstream), so this is A..C.
        return self.worst_tier


def parse_week_key(week_key: str) -> tuple[int, int]:
    """YYYY-WW → (season_year, week_int)."""
    if "-" not in week_key:
        raise ValueError(f"expected YYYY-WW, got {week_key!r}")
    y, w = week_key.split("-", 1)
    return int(y), int(w)


def normalize_week_key(week_key: str) -> str:
    """Canonical zero-padded form so 2022-1 and 2022-01 collapse to 2022-01."""
    # Historical bug: both 'YYYY-W' and 'YYYY-WW' got written for weeks 0-9.
    y, w = parse_week_key(week_key)
    return f"{y:04d}-{w:02d}"


def _fetch_source_weights(db: Database) -> dict[str, dict[str, Any]]:
    """Return mapping source_id → {tier, cohort_weights(dict), max_publication_form}.

    Only returns rows with source_id populated AND tier in {A,B,C} (tier D is
    citation-only and skipped). source_name column from legacy rows is also
    indexed so pre-fanintel conversation_documents (which only have
    ``source_name``) can be mapped to fanintel source_id by convention.
    """
    rows = db.query_all(
        """
        select source_id, source_name, tier, cohort_weights, max_publication_form,
               ingest_method
        from source_registry
        where source_id is not null
        """
    )
    by_id: dict[str, dict[str, Any]] = {}
    for r in rows:
        if r["tier"] == "D":
            continue
        try:
            weights = json.loads(r["cohort_weights"] or "{}")
        except json.JSONDecodeError:
            logger.warning("source_registry.cohort_weights is not JSON for %s", r["source_id"])
            continue
        by_id[r["source_id"]] = {
            "tier": r["tier"],
            "cohort_weights": weights,
            "source_name": r["source_name"],
        }
    return by_id


def _resolve_source_id(doc_source_name: str | None, doc_source_id: str | None,
                        registry: dict[str, dict[str, Any]],
                        name_to_id: dict[str, str]) -> str | None:
    if doc_source_id and doc_source_id in registry:
        return doc_source_id
    if doc_source_name:
        # 'reddit:CFB' → try exact-ish match via name_to_id, then convention
        if doc_source_name in name_to_id:
            return name_to_id[doc_source_name]
        lowered = doc_source_name.lower()
        if lowered.startswith("reddit:") and "reddit_cfb" in registry:
            return "reddit_cfb"
        if "reddit" in lowered and "reddit_cfb" in registry:
            return "reddit_cfb"
        if "bluesky" in lowered and "bluesky_firehose" in registry:
            return "bluesky_firehose"
        if "youtube" in lowered and "youtube_comments_nat" in registry:
            return "youtube_comments_nat"
    return None


def compute_cohort_week(db: Database, week_key: str,
                        teams: Iterable[int] | None = None) -> dict[str, int]:
    """Compute team_cohort_week rows for a single YYYY-WW week.

    Returns counts: {'cells_written': N, 'docs_considered': M, 'docs_skipped': K}.
    """
    season_year, week_int = parse_week_key(week_key)
    week_key = normalize_week_key(week_key)

    # Check the underlying table has SOMETHING with a source_id — the filter
    # to non-D tiers happens inside _fetch_source_weights, and an all-D registry
    # is a legitimate no-op (Tier D is citation-only).
    any_row = db.query_one(
        "select 1 as x from source_registry where source_id is not null limit 1"
    )
    if not any_row:
        raise RuntimeError(
            "source_registry has no fanintel rows (source_id + cohort_weights). "
            "Run `python manage.py seed-source-registry` first."
        )
    registry = _fetch_source_weights(db)
    if not registry:
        return {"cells_written": 0, "docs_considered": 0, "docs_skipped": 0}
    name_to_id = {
        info["source_name"]: sid
        for sid, info in registry.items()
        if info.get("source_name")
    }

    team_filter = ""
    params: dict[str, Any] = {"season_year": season_year, "week": week_int}
    if teams:
        team_list = list(teams)
        placeholders = ",".join(f":team_{i}" for i in range(len(team_list)))
        for i, t in enumerate(team_list):
            params[f"team_{i}"] = t
        team_filter = f" and t.team_id in ({placeholders}) "

    rows = db.query_all(
        f"""
        select
            t.team_id           as team_id,
            cd.source_name      as doc_source_name,
            cd.source_id        as doc_source_id,
            t.sentiment_score   as sentiment
        from conversation_document_targets t
        join conversation_documents cd on cd.conversation_document_id = t.conversation_document_id
        where t.season_year = :season_year
          and t.week = :week
          and t.team_id is not null
          {team_filter}
        """,
        params,
    )

    cells: dict[tuple[int, str], CohortCell] = defaultdict(CohortCell)
    considered = 0
    skipped = 0
    for row in rows:
        considered += 1
        source_id = _resolve_source_id(row["doc_source_name"], row["doc_source_id"],
                                       registry, name_to_id)
        if source_id is None:
            skipped += 1
            continue
        info = registry[source_id]
        weights = info["cohort_weights"]
        tier = info["tier"]
        team_id = row["team_id"]
        sentiment = row["sentiment"]
        for cohort in COHORTS:
            weight = float(weights.get(cohort) or 0)
            if weight <= 0:
                continue
            cells[(team_id, cohort)].add(
                weight=weight,
                sentiment=sentiment,
                source_id=source_id,
                tier=tier,
            )

    # Write cells
    cells_written = 0
    for (team_id, cohort), cell in cells.items():
        top_sources = sorted(
            (cell.top_source_ids or {}).items(), key=lambda kv: kv[1], reverse=True
        )[:5]
        db.execute(
            """
            insert into team_cohort_week (
                team_id, cohort, week, effective_n, sentiment_score, volume,
                top_source_ids, confidence_tier, created_at_utc, updated_at_utc
            ) values (
                :team_id, :cohort, :week, :effective_n, :sentiment_score, :volume,
                :top_source_ids, :confidence_tier, :now, :now
            )
            on conflict (team_id, cohort, week) do update set
                effective_n = excluded.effective_n,
                sentiment_score = excluded.sentiment_score,
                volume = excluded.volume,
                top_source_ids = excluded.top_source_ids,
                confidence_tier = excluded.confidence_tier,
                updated_at_utc = excluded.updated_at_utc
            """,
            {
                "team_id": team_id,
                "cohort": cohort,
                "week": week_key,
                "effective_n": cell.effective_n,
                "sentiment_score": cell.sentiment(),
                "volume": cell.volume,
                "top_source_ids": json.dumps([sid for sid, _ in top_sources]),
                "confidence_tier": cell.confidence_tier(),
                "now": _utcnow_iso(),
            },
        )
        cells_written += 1

    return {
        "cells_written": cells_written,
        "docs_considered": considered,
        "docs_skipped": skipped,
    }


def _utcnow_iso() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["compute_cohort_week", "COHORTS", "parse_week_key", "normalize_week_key", "FLOOR_MIN", "FLOOR_STANDARD"]
