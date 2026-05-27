"""All-time bowl-record ledger: import + honest label resolution.

Spec: docs/specs/team-preview-implementation-plan-2026-05-26.md §1.5, §2.4, §10.

Two layers:
  1. ``import_bowl_ledger`` — load true all-time bowl records from a seed
     CSV/JSON into ``team_bowl_record_ledger``.
  2. ``resolve_bowl_record_display`` — the render-time decision that guarantees
     the site never calls CFBD-era postseason data an "all-time" record. This is
     pure and unit-tested.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# verification_status values that may carry the "all-time" label.
_ALL_TIME_TRUSTWORTHY = {"verified", "single_source"}


@dataclass(frozen=True)
class BowlRecordDisplay:
    """Render-ready bowl record decision."""

    scope: str          # 'all_time' | 'recent_era' | 'unavailable'
    label: str          # e.g. "All-time bowls: 47-26-3"
    record: str | None  # "47-26-3" or None
    source_name: str | None
    verification_status: str | None
    suppress: bool      # True when nothing honest can be shown

    @property
    def is_all_time(self) -> bool:
        return self.scope == "all_time"


def resolve_bowl_record_display(
    ledger_row: dict[str, Any] | None,
    *,
    recent_postseason_wins: int | None = None,
    recent_postseason_losses: int | None = None,
    recent_era_label: str = "CFBD-era",
) -> BowlRecordDisplay:
    """Decide how (and whether) to present a team's bowl record.

    The single most important rule (spec §1.5): only a ledger row with
    ``verification_status`` in {'verified','single_source'} may be labelled an
    all-time record. Otherwise fall back to a clearly-scoped recent-era record
    or suppress entirely.
    """
    status = (ledger_row or {}).get("verification_status")
    if ledger_row is not None and status in _ALL_TIME_TRUSTWORTHY:
        record = _format_record(
            ledger_row.get("wins"), ledger_row.get("losses"), ledger_row.get("ties")
        )
        if record is not None:
            return BowlRecordDisplay(
                scope="all_time",
                label=f"All-time bowls: {record}",
                record=record,
                source_name=ledger_row.get("source_name"),
                verification_status=status,
                suppress=False,
            )

    # No trustworthy all-time ledger. Offer recent-era data only if we have it,
    # and label its scope explicitly so it is never mistaken for all-time.
    if recent_postseason_wins is not None and recent_postseason_losses is not None:
        record = _format_record(recent_postseason_wins, recent_postseason_losses, 0)
        if record is not None:
            return BowlRecordDisplay(
                scope="recent_era",
                label=f"Recent postseason ({recent_era_label}): {record}",
                record=record,
                source_name=None,
                verification_status=status,
                suppress=False,
            )

    return BowlRecordDisplay(
        scope="unavailable",
        label="All-time bowl record unavailable",
        record=None,
        source_name=None,
        verification_status=status,
        suppress=True,
    )


def _format_record(wins: Any, losses: Any, ties: Any) -> str | None:
    try:
        w = int(wins)
        loss = int(losses)
    except (TypeError, ValueError):
        return None
    try:
        t = int(ties) if ties is not None else 0
    except (TypeError, ValueError):
        t = 0
    return f"{w}-{loss}-{t}" if t else f"{w}-{loss}"


# --- seed import ------------------------------------------------------------

def load_bowl_ledger_seed(path: str | Path) -> list[dict[str, Any]]:
    """Read a bowl-ledger seed from CSV or JSON. Returns normalised dict rows.

    Expected columns/keys: slug, wins, losses, ties, appearances, first_bowl_year,
    last_bowl_year, last_bowl_name, last_bowl_result, source_name, source_url,
    source_retrieved_at, verification_status, notes (free text -> notes_json).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"bowl ledger seed not found: {p}")
    if p.suffix.lower() == ".json":
        raw = json.loads(p.read_text(encoding="utf-8"))
        records = raw if isinstance(raw, list) else raw.get("teams", [])
    else:
        with p.open("r", encoding="utf-8", newline="") as fh:
            records = list(csv.DictReader(fh))
    return [_normalise_seed_row(r) for r in records if (r.get("slug") or "").strip()]


def _normalise_seed_row(row: dict[str, Any]) -> dict[str, Any]:
    def _int(key: str) -> int | None:
        val = row.get(key)
        if val in (None, ""):
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    notes = row.get("notes")
    if isinstance(notes, str) and notes.strip():
        notes_json = json.dumps({"notes": notes.strip()})
    elif isinstance(notes, (dict, list)):
        notes_json = json.dumps(notes)
    else:
        notes_json = "{}"

    status = (row.get("verification_status") or "single_source").strip()
    return {
        "slug": str(row["slug"]).strip(),
        "wins": _int("wins") or 0,
        "losses": _int("losses") or 0,
        "ties": _int("ties") or 0,
        "appearances": _int("appearances"),
        "first_bowl_year": _int("first_bowl_year"),
        "last_bowl_year": _int("last_bowl_year"),
        "last_bowl_name": (row.get("last_bowl_name") or None),
        "last_bowl_result": (row.get("last_bowl_result") or None),
        "source_name": (row.get("source_name") or "seed").strip(),
        "source_url": (row.get("source_url") or None),
        "source_retrieved_at": (row.get("source_retrieved_at") or None),
        "verification_status": status,
        "notes_json": notes_json,
    }


def import_bowl_ledger(db: Any, seed_path: str | Path, *, as_of: str | None = None) -> dict[str, int]:
    """Import a bowl-ledger seed into ``team_bowl_record_ledger`` (upsert by slug+source).

    Resolves team_id from the slug where possible; rows for unknown slugs are
    still stored (team_id NULL) so the data is not silently dropped.
    """
    from cfb_rankings.team_preview.persistence import upsert_bowl_ledger_rows

    rows = load_bowl_ledger_seed(seed_path)
    slug_to_id = {
        r["slug"]: r["team_id"]
        for r in db.query_all("select slug, team_id from teams")
    }
    for r in rows:
        r["team_id"] = slug_to_id.get(r["slug"])
        if as_of and not r.get("source_retrieved_at"):
            r["source_retrieved_at"] = as_of
    upsert_bowl_ledger_rows(db, rows)
    matched = sum(1 for r in rows if r.get("team_id") is not None)
    return {"rows": len(rows), "matched_team_id": matched, "unmatched": len(rows) - matched}
