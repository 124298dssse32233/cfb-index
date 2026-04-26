"""Trigger detection for Reaction Stories (Sprint 15 Phase 2).

check_triggers(hours=24) scans recent wire entries and returns a list of
TriggerEvent objects — one per Wire entry that qualifies. The caller then
decides whether to auto-generate or just print candidates.

Trigger rules (any one fires):
  1. velocity_score >= 90 (top-decile of 30-day distribution)
  2. Entity is top-25 program / Heisman-tier player / power-conference coach
     AND velocity >= 75
  3. Entity has 3+ Wire entries in last 6 hours (compounding signal)
  4. Manual override via force_wire_id argument

Compounding: if multiple triggers fire on the same primary_entity_slug within
12h, they collapse into one TriggerEvent (highest velocity wins).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from .data import db_conn


# ── Program / entity tier lists ────────────────────────────────────────────

_TOP25_PROGRAMS: frozenset[str] = frozenset({
    "alabama", "georgia", "ohio-state", "michigan", "texas", "notre-dame",
    "penn-state", "lsu", "clemson", "oregon", "usc", "florida-state",
    "oklahoma", "tennessee", "texas-am", "utah", "washington", "ole-miss",
    "auburn", "miami", "florida", "north-carolina", "baylor", "arkansas",
    "wisconsin",
})

_POWER_CONF_PROGRAMS: frozenset[str] = frozenset({
    # SEC
    "alabama", "auburn", "florida", "georgia", "kentucky", "lsu", "mississippi-state",
    "missouri", "ole-miss", "south-carolina", "tennessee", "texas-am", "vanderbilt",
    "texas", "oklahoma",
    # Big Ten
    "illinois", "indiana", "iowa", "maryland", "michigan", "michigan-state",
    "minnesota", "nebraska", "northwestern", "ohio-state", "penn-state", "purdue",
    "rutgers", "ucla", "usc", "washington", "wisconsin",
    # Big 12
    "arizona", "arizona-state", "baylor", "byu", "cincinnati", "colorado",
    "houston", "iowa-state", "kansas", "kansas-state", "oklahoma-state",
    "tcu", "texas-tech", "ucf", "utah", "west-virginia",
    # ACC
    "boston-college", "california", "clemson", "duke", "florida-state",
    "georgia-tech", "louisville", "miami", "north-carolina", "nc-state",
    "notre-dame", "pittsburgh", "smum", "stanford", "syracuse", "virginia",
    "virginia-tech", "wake-forest",
})

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    return _SLUG_RE.sub("-", ascii_only.lower()).strip("-")


def _suggest_slug(wire_row: dict) -> str:
    program = wire_row.get("program_slug") or _slugify(wire_row.get("program_display", "unknown"))
    action = wire_row.get("action", "")
    # extract key words: first 5 tokens, lowercase-hyphen
    tokens = _SLUG_RE.sub(" ", action.lower()).split()[:5]
    action_part = "-".join(tokens)
    return f"{program}-{action_part}"[:80]


def _entity_type_from_actor(actor_kind: str) -> str:
    mapping = {
        "program": "team",
        "player": "player",
        "coach": "coach",
        "conference": "conference",
        "committee": "event",
    }
    return mapping.get(actor_kind, "team")


@dataclass
class TriggerEvent:
    wire_id: int
    primary_entity_slug: str
    primary_entity_type: str
    suggested_slug: str
    velocity: float
    trigger_reason: str


def check_triggers(
    hours: int = 24,
    force_wire_id: Optional[int] = None,
) -> list[TriggerEvent]:
    """Return TriggerEvents for qualifying Wire entries in the last `hours` hours.

    If force_wire_id is set, that entry is returned regardless of thresholds.
    """
    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    six_h_start = (now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")

    with db_conn(read_only=True) as c:
        # All recent entries
        rows = c.execute(
            "SELECT * FROM wire_entries WHERE occurred_at >= ? ORDER BY occurred_at DESC",
            (window_start,),
        ).fetchall()
        rows = [dict(r) for r in rows]

        # Count entries per entity in last 6h (rule 3)
        freq_rows = c.execute(
            """
            SELECT program_slug, COUNT(*) as cnt
            FROM wire_entries
            WHERE occurred_at >= ?
              AND program_slug IS NOT NULL
            GROUP BY program_slug
            """,
            (six_h_start,),
        ).fetchall()
        entity_freq: dict[str, int] = {r["program_slug"]: r["cnt"] for r in freq_rows}

        # Force-trigger override
        force_row = None
        if force_wire_id is not None:
            row = c.execute(
                "SELECT * FROM wire_entries WHERE id = ?", (force_wire_id,)
            ).fetchone()
            if row:
                force_row = dict(row)

        # Already-generated story slugs (dedup: don't re-fire within 12h)
        twelve_h_start = (now - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")
        recent_entities = set()
        existing = c.execute(
            "SELECT primary_entity_slug FROM reaction_stories WHERE triggered_at_utc >= ?",
            (twelve_h_start,),
        ).fetchall()
        for r in existing:
            recent_entities.add(r["primary_entity_slug"])

    # --- Evaluate triggers ---
    candidates: dict[str, TriggerEvent] = {}  # keyed by entity_slug

    def _add_candidate(row: dict, reason: str) -> None:
        velocity = float(row.get("fan_intel_velocity_spike") or 0)
        entity_slug = row.get("program_slug") or _slugify(row.get("program_display", "unknown"))
        entity_type = _entity_type_from_actor(row.get("actor_kind", "program"))

        # Skip if we already fired for this entity in last 12h (unless forced)
        if entity_slug in recent_entities and reason != "force":
            return

        evt = TriggerEvent(
            wire_id=row["id"],
            primary_entity_slug=entity_slug,
            primary_entity_type=entity_type,
            suggested_slug=_suggest_slug(row),
            velocity=velocity,
            trigger_reason=reason,
        )
        # Keep highest-velocity if multiple entries for same entity
        existing_evt = candidates.get(entity_slug)
        if existing_evt is None or velocity > existing_evt.velocity:
            candidates[entity_slug] = evt

    # Force trigger
    if force_row is not None:
        _add_candidate(force_row, "force")

    for row in rows:
        velocity = float(row.get("fan_intel_velocity_spike") or 0)
        program_slug = row.get("program_slug") or ""
        actor_kind = row.get("actor_kind", "program")

        # Rule 1: top-decile velocity
        if velocity >= 90:
            _add_candidate(row, "velocity>=90")
            continue

        # Rule 2: power program + velocity >= 75
        is_power = (
            program_slug in _TOP25_PROGRAMS
            or program_slug in _POWER_CONF_PROGRAMS
            or actor_kind in ("coach", "conference")
        )
        if is_power and velocity >= 75:
            _add_candidate(row, f"power-entity+velocity>={velocity}")
            continue

        # Rule 3: compounding signal
        if entity_freq.get(program_slug, 0) >= 3:
            _add_candidate(row, "3+entries-in-6h")
            continue

    return list(candidates.values())
