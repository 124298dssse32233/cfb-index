"""Local cohort-divergence helpers for the Canon.

Per the Sprint 11 brief:

> Don't extend cohorts/aggregate.py — it's dirty in Sprint 8's working
> tree. Build a small canon/cohorts.py that queries source_observations
> directly with signal-velocity weighting. Document the surface so it
> can be merged into the canonical cohorts module later.

This module computes a single thing: for a set of candidate entities
(players, games, programs), produce a "stat-folks rank" and a
"casual-fans rank", and label the divergence.

Definitions
-----------
* **stat cohorts**:        ``analytics``, ``gambling``, ``recruiting``
* **casual cohorts**:      ``casual_vibes``, ``boomer_gen_x``, ``national_narrative``

Score per (entity, cohort_bucket) =
    sum over all source_observations rows whose source has cohort_weights
    populated, of  ``value_numeric * cohort_weight``,
    decayed by recency (signal velocity proxy: weight = exp(-days_since/180)).

Where the underlying data is sparse (the common case for 10-year-old
games and most 100-best-players entries), we *do not* fabricate a
divergence; we return ``cohort_split_label='consensus'`` with the
stat-rank == casual-rank == the seed editorial rank. That's faithful to
the data and honest in the UI.

Surface
-------
* ``compute_cohort_split(db, entries) -> dict[entity_slug, CohortSplit]``
* ``label_divergence(stat_rank, casual_rank) -> str``

To merge later: this whole module is ~150 lines, no team_pages imports,
and the SQL is read-only against ``source_observations`` and
``source_registry``. Drop into ``cohorts/aggregate.py`` whenever Sprint 8
lands and the API can be unified.
"""
from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


_STAT_COHORTS: tuple[str, ...] = ("analytics", "gambling", "recruiting")
_CASUAL_COHORTS: tuple[str, ...] = (
    "casual_vibes", "boomer_gen_x", "national_narrative",
)

_RECENCY_HALF_LIFE_DAYS = 180.0


@dataclass(frozen=True)
class CohortSplit:
    entity_slug: str
    stat_rank: int
    casual_rank: int
    label: str            # 'consensus' | 'slight divergence' | 'wide divergence'


def label_divergence(stat_rank: int, casual_rank: int) -> str:
    """Map an (stat_rank, casual_rank) pair to a human label."""
    delta = abs(stat_rank - casual_rank)
    if delta <= 2:
        return "consensus"
    if delta <= 8:
        return "slight divergence"
    return "wide divergence"


# --------------------------------------------------------------------------
# Source-registry → cohort-weight cache
# --------------------------------------------------------------------------

def _load_cohort_weight_table(con: sqlite3.Connection) -> dict[str, dict[str, float]]:
    """source_id -> {cohort_name: weight} from source_registry.cohort_weights.

    Sources without populated cohort_weights are silently skipped — they
    contribute zero to the divergence calculation.
    """
    table: dict[str, dict[str, float]] = {}
    cur = con.execute(
        "SELECT source_id, cohort_weights FROM source_registry "
        "WHERE source_id IS NOT NULL AND cohort_weights IS NOT NULL"
    )
    for sid, weights_json in cur:
        if not weights_json:
            continue
        try:
            weights = json.loads(weights_json)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(weights, dict):
            table[sid] = {k: float(v) for k, v in weights.items()
                         if isinstance(v, (int, float))}
    return table


def _recency_weight(observed_at_iso: str, *, now: datetime | None = None) -> float:
    """exp(-Δdays / half_life_days). Newer observations weigh more."""
    if not observed_at_iso:
        return 0.0
    now = now or datetime.now(timezone.utc)
    try:
        # source_observations.observed_at_utc is ISO without timezone in
        # most rows; treat naive strings as UTC.
        dt = datetime.fromisoformat(observed_at_iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return 0.0
    days = max(0.0, (now - dt).total_seconds() / 86_400.0)
    return math.exp(-days / _RECENCY_HALF_LIFE_DAYS)


# --------------------------------------------------------------------------
# Per-entity score fetch
# --------------------------------------------------------------------------

def _bucket_score(
    con: sqlite3.Connection,
    entity_label: str,
    weight_table: dict[str, dict[str, float]],
    cohorts: Iterable[str],
    *,
    now: datetime | None = None,
) -> float:
    """Sum value_numeric * cohort_weight * recency_weight for one bucket.

    Matches source_observations on entity_label using a case-insensitive
    LIKE; that's the most reliable join for player/game canon entries
    where the source-row entity_label is "Tua Tagovailoa", "Alabama
    Crimson Tide", "2018 Iron Bowl", etc.
    """
    if not entity_label:
        return 0.0
    cohort_set = set(cohorts)
    cur = con.execute(
        """
        SELECT source_id, value_numeric, observed_at_utc
        FROM source_observations
        WHERE entity_label LIKE ?
          AND value_numeric IS NOT NULL
        """,
        (f"%{entity_label}%",),
    )
    score = 0.0
    for sid, value_numeric, observed_at in cur:
        weights = weight_table.get(sid)
        if not weights:
            continue
        bucket_weight = sum(weights.get(c, 0.0) for c in cohort_set)
        if bucket_weight <= 0:
            continue
        score += float(value_numeric) * bucket_weight * _recency_weight(
            observed_at, now=now,
        )
    return score


def compute_cohort_split(
    con: sqlite3.Connection,
    entries: list[dict],
    *,
    now: datetime | None = None,
) -> dict[str, CohortSplit]:
    """Compute a cohort split for each entry that has source-observation hits.

    Entries lacking any matching source_observations rows are returned
    with ``label='consensus'`` and stat_rank == casual_rank == their seed
    rank — see module docstring.

    Each entry must be a dict with at least ``entity_slug``,
    ``entity_display_name``, and ``rank``. Optional ``program_label``
    is used as a secondary signal source — most CFP-era player/game
    entries have no direct source_observations rows, but their program's
    wiki/team-query rows give a meaningful divergence signal.
    """
    weight_table = _load_cohort_weight_table(con)

    scored: list[tuple[dict, float, float]] = []
    for entry in entries:
        label = entry.get("entity_display_name") or entry.get("entity_slug") or ""
        stat_score = _bucket_score(con, label, weight_table, _STAT_COHORTS, now=now)
        casual_score = _bucket_score(con, label, weight_table, _CASUAL_COHORTS, now=now)

        # Fallback: when the entity itself has no observations, score
        # against its program label at 50% weight (program signal is real
        # signal for player/game/coaching entries even when the entity
        # name doesn't match any wiki article directly).
        program_label = entry.get("program_label")
        if (stat_score == 0.0 and casual_score == 0.0) and program_label:
            stat_score = 0.5 * _bucket_score(
                con, program_label, weight_table, _STAT_COHORTS, now=now,
            )
            casual_score = 0.5 * _bucket_score(
                con, program_label, weight_table, _CASUAL_COHORTS, now=now,
            )

        scored.append((entry, stat_score, casual_score))

    # Rank by score desc within each bucket (1 = highest signal). Entries
    # with zero score in a bucket inherit their seed rank — they don't
    # participate in the divergence game.
    nonzero_stat = [(e, s) for (e, s, _) in scored if s > 0]
    nonzero_casual = [(e, c) for (e, _, c) in scored if c > 0]
    nonzero_stat.sort(key=lambda x: x[1], reverse=True)
    nonzero_casual.sort(key=lambda x: x[1], reverse=True)
    stat_rank_map = {e["entity_slug"]: i + 1 for i, (e, _) in enumerate(nonzero_stat)}
    casual_rank_map = {e["entity_slug"]: i + 1 for i, (e, _) in enumerate(nonzero_casual)}

    out: dict[str, CohortSplit] = {}
    for entry in entries:
        seed_rank = int(entry["rank"])
        slug = entry["entity_slug"]
        stat_rank = stat_rank_map.get(slug, seed_rank)
        casual_rank = casual_rank_map.get(slug, seed_rank)
        out[slug] = CohortSplit(
            entity_slug=slug,
            stat_rank=stat_rank,
            casual_rank=casual_rank,
            label=label_divergence(stat_rank, casual_rank),
        )
    return out
