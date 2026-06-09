"""Last-Known-Good (LKG) cache layer for Chronicle cards.

Every successful card generation writes a copy to the LKG cache. If a fresh
generation fails or is missing at site-build time, the build script reads from
LKG and renders the card with a `data-stale="true"` attribute that drives a
subtle "Awaiting refresh" badge in CSS.

This module owns:
- promote_to_lkg(): mark a card as LKG (called after successful generation).
- get_lkg_card(): fetch the LKG card for (slug, week, card_type) when fresh
  generation is missing.
- list_stale_surfaces(): which pages currently render LKG cards (for monitoring).
- export_lkg_to_disk() / import_lkg_from_disk(): the git-committed LKG dump.

The git-committed LKG dump lives at:
    output/site/_cards_lkg/
        index.json                         — manifest of all LKG cards
        cards/{entity_kind}/{slug}/{season}_{week}_{card_type}.json

This dump is read by build-site when DB is unavailable or empty (e.g., a CI
runner without a DB artifact, or a fresh-clone disaster recovery).
"""
from __future__ import annotations

import hashlib
import json
import logging
import statistics
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Literal

if TYPE_CHECKING:
    from cfb_rankings.db import Database

log = logging.getLogger("cfb_rankings.chronicle.lkg")

LKG_DUMP_DIR = Path("output/site/_cards_lkg")
LKG_MANIFEST_NAME = "index.json"
LKG_STALE_DAYS = 14

EntityKind = Literal["player", "team", "conference", "rivalry"]


@dataclass(frozen=True)
class LKGCard:
    cache_key: str
    entity_kind: EntityKind
    slug: str
    season_year: int | None
    week_number: int | None
    card_type: str
    slot_index: int | None
    card_content_json: dict
    card_html: str | None
    confidence_band: str
    model_id: str
    model_version: str
    schema_version: str
    word_count: int | None
    lkg_promoted_at_utc: str

    @property
    def is_stale(self) -> bool:
        """True if LKG card is older than LKG_STALE_DAYS days."""
        try:
            promoted = datetime.fromisoformat(self.lkg_promoted_at_utc.replace("Z", "+00:00"))
            if promoted.tzinfo is None:
                promoted = promoted.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - promoted
            return age.days > LKG_STALE_DAYS
        except (ValueError, AttributeError):
            return True


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _age_days(ts_str: str) -> float:
    """Return fractional days since a UTC ISO-8601 timestamp."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        return delta.total_seconds() / 86400.0
    except (ValueError, AttributeError):
        return float("inf")


def _row_to_lkg_card(row: dict) -> LKGCard:
    """Convert a DB row dict to an LKGCard dataclass."""
    raw_json = row.get("card_content_json", "{}")
    if isinstance(raw_json, str):
        try:
            content_dict = json.loads(raw_json)
        except json.JSONDecodeError:
            content_dict = {}
    else:
        content_dict = raw_json or {}

    return LKGCard(
        cache_key=row["cache_key"],
        entity_kind=row["entity_kind"],
        slug=row["slug"],
        season_year=row.get("season_year"),
        week_number=row.get("week_number"),
        card_type=row["card_type"],
        slot_index=row.get("slot_index"),
        card_content_json=content_dict,
        card_html=row.get("card_html"),
        confidence_band=row.get("confidence_band", "unset"),
        model_id=row.get("model_id", ""),
        model_version=row.get("model_version", ""),
        schema_version=row.get("schema_version", ""),
        word_count=row.get("word_count"),
        lkg_promoted_at_utc=row.get("lkg_promoted_at_utc", ""),
    )


def promote_to_lkg(db: "Database", cache_key: str) -> bool:
    """Mark a card as LKG by setting is_lkg=1 and lkg_promoted_at_utc.

    Returns True if promotion succeeded, False if cache_key doesn't exist.
    """
    row = db.query_one(
        "SELECT cache_key FROM chronicle_card_cache WHERE cache_key = :key",
        {"key": cache_key},
    )
    if row is None:
        log.warning("promote_to_lkg: cache_key %r not found", cache_key)
        return False

    now = _now_utc_iso()
    db.execute(
        """
        UPDATE chronicle_card_cache
           SET is_lkg = 1,
               lkg_promoted_at_utc = :now
         WHERE cache_key = :key
        """,
        {"now": now, "key": cache_key},
    )
    log.info("Promoted %s to LKG at %s", cache_key, now)
    return True


def get_lkg_card(
    db: "Database",
    entity_kind: EntityKind,
    slug: str,
    season_year: int | None,
    week_number: int | None,
    card_type: str,
    slot_index: int | None = None,
) -> LKGCard | None:
    """Fetch the LKG card for these dimensions, or None if no LKG exists.

    Picks the most recently promoted LKG row that matches all supplied
    dimensions.  season_year / week_number / slot_index may be None — when
    they are, the query ignores those dimensions so that cards that span
    multiple weeks (e.g. offseason summary cards) are still retrievable.
    """
    clauses = [
        "entity_kind = :entity_kind",
        "slug        = :slug",
        "card_type   = :card_type",
        "is_lkg      = 1",
    ]
    params: dict = {
        "entity_kind": entity_kind,
        "slug": slug,
        "card_type": card_type,
    }

    if season_year is not None:
        clauses.append("season_year = :season_year")
        params["season_year"] = season_year
    if week_number is not None:
        clauses.append("week_number = :week_number")
        params["week_number"] = week_number
    if slot_index is not None:
        clauses.append("slot_index = :slot_index")
        params["slot_index"] = slot_index

    sql = (
        "SELECT * FROM chronicle_card_cache"
        " WHERE " + " AND ".join(clauses) +
        " ORDER BY lkg_promoted_at_utc DESC LIMIT 1"
    )
    row = db.query_one(sql, params)
    if row is None:
        return None
    return _row_to_lkg_card(row)


def get_active_or_lkg_card(
    db: "Database",
    entity_kind: EntityKind,
    slug: str,
    season_year: int | None,
    week_number: int | None,
    card_type: str,
    slot_index: int | None = None,
) -> tuple[dict | None, bool]:
    """Resolution path for site-build:

    1. Try to fetch the active (non-superseded) card from chronicle_card_cache.
       If found, return (card_dict, is_stale=False).
    2. Else try LKG fallback. If found, return (card_dict, is_stale=True).
    3. Else return (None, False) — surface should render Awaiting Signal.

    The is_stale flag is what triggers the data-stale="true" attribute in render.
    """
    # --- Step 1: active card ---
    active_clauses = [
        "slug                = :slug",
        "card_type           = :card_type",
        "superseded_at_utc   IS NULL",
    ]
    active_params: dict = {"slug": slug, "card_type": card_type}

    if season_year is not None:
        active_clauses.append("season_year = :season_year")
        active_params["season_year"] = season_year
    if week_number is not None:
        active_clauses.append("week_number = :week_number")
        active_params["week_number"] = week_number
    if slot_index is not None:
        active_clauses.append("slot_index = :slot_index")
        active_params["slot_index"] = slot_index

    active_sql = (
        "SELECT * FROM chronicle_card_cache WHERE "
        + " AND ".join(active_clauses)
        + " ORDER BY created_at_utc DESC LIMIT 1"
    )
    active_row = db.query_one(active_sql, active_params)
    if active_row is not None:
        card_dict = dict(active_row)
        raw = card_dict.get("card_content_json", "{}")
        if isinstance(raw, str):
            try:
                card_dict["card_content_json"] = json.loads(raw)
            except json.JSONDecodeError:
                card_dict["card_content_json"] = {}
        return card_dict, False

    # --- Step 2: LKG fallback ---
    lkg = get_lkg_card(db, entity_kind, slug, season_year, week_number, card_type, slot_index)
    if lkg is not None:
        card_dict = {
            "cache_key": lkg.cache_key,
            "entity_kind": lkg.entity_kind,
            "slug": lkg.slug,
            "season_year": lkg.season_year,
            "week_number": lkg.week_number,
            "card_type": lkg.card_type,
            "slot_index": lkg.slot_index,
            "card_content_json": lkg.card_content_json,
            "card_html": lkg.card_html,
            "confidence_band": lkg.confidence_band,
            "model_id": lkg.model_id,
            "model_version": lkg.model_version,
            "schema_version": lkg.schema_version,
            "word_count": lkg.word_count,
            "lkg_promoted_at_utc": lkg.lkg_promoted_at_utc,
        }
        return card_dict, True

    # --- Step 3: no card available ---
    return None, False


def list_stale_surfaces(db: "Database", max_age_days: int = 7) -> list[dict]:
    """For monitoring — which slug+card_type pairs are currently serving LKG
    cards older than max_age_days.

    Returns list of dicts with slug, card_type, lkg_promoted_at_utc, age_days.
    """
    rows = db.query_all(
        """
        SELECT slug, entity_kind, card_type, lkg_promoted_at_utc
          FROM chronicle_card_cache
         WHERE is_lkg = 1
           AND lkg_promoted_at_utc IS NOT NULL
         ORDER BY lkg_promoted_at_utc ASC
        """
    )
    stale = []
    for row in rows:
        age = _age_days(row["lkg_promoted_at_utc"])
        if age > max_age_days:
            stale.append({
                "slug": row["slug"],
                "entity_kind": row["entity_kind"],
                "card_type": row["card_type"],
                "lkg_promoted_at_utc": row["lkg_promoted_at_utc"],
                "age_days": round(age, 2),
            })
    return stale


def _disk_path_for_card(
    dump_dir: Path,
    entity_kind: str,
    slug: str,
    season_year: int | None,
    week_number: int | None,
    card_type: str,
    slot_index: int | None,
    cache_key: str,
) -> Path:
    """Build a deterministic path for a single LKG card JSON file."""
    season_str = str(season_year) if season_year is not None else "none"
    week_str = str(week_number) if week_number is not None else "none"
    slot_str = str(slot_index) if slot_index is not None else "none"
    filename = f"{season_str}_{week_str}_{card_type}_{slot_str}_{cache_key[:8]}.json"
    return dump_dir / "cards" / entity_kind / slug / filename


def export_lkg_to_disk(db: "Database", dump_dir: Path = LKG_DUMP_DIR) -> dict:
    """Walk the chronicle_card_cache table for all is_lkg=1 rows.

    Write each to a JSON file under
    dump_dir/cards/{entity_kind}/{slug}/{season}_{week}_{card_type}.json

    Write a manifest at dump_dir/index.json with summary stats.

    Returns summary dict: {cards_exported, manifest_path, total_bytes}.
    """
    dump_dir = Path(dump_dir)
    dump_dir.mkdir(parents=True, exist_ok=True)

    rows = db.query_all(
        """
        SELECT *
          FROM chronicle_card_cache
         WHERE is_lkg = 1
         ORDER BY entity_kind, slug, card_type, lkg_promoted_at_utc DESC
        """
    )

    manifest_entries: list[dict] = []
    total_bytes = 0
    cards_exported = 0

    for row in rows:
        row_dict = dict(row)
        entity_kind = row_dict["entity_kind"]
        slug = row_dict["slug"]
        season_year = row_dict.get("season_year")
        week_number = row_dict.get("week_number")
        card_type = row_dict["card_type"]
        slot_index = row_dict.get("slot_index")
        cache_key = row_dict["cache_key"]

        # Parse embedded JSON so the dump is human-readable
        raw_json = row_dict.get("card_content_json", "{}")
        if isinstance(raw_json, str):
            try:
                row_dict["card_content_json"] = json.loads(raw_json)
            except json.JSONDecodeError:
                row_dict["card_content_json"] = {}

        out_path = _disk_path_for_card(
            dump_dir, entity_kind, slug,
            season_year, week_number, card_type, slot_index, cache_key,
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)

        card_text = json.dumps(row_dict, indent=2, sort_keys=True, default=str)
        out_path.write_text(card_text, encoding="utf-8")

        file_bytes = len(card_text.encode("utf-8"))
        total_bytes += file_bytes
        cards_exported += 1

        manifest_entries.append({
            "cache_key": cache_key,
            "entity_kind": entity_kind,
            "slug": slug,
            "season_year": season_year,
            "week_number": week_number,
            "card_type": card_type,
            "slot_index": slot_index,
            "lkg_promoted_at_utc": row_dict.get("lkg_promoted_at_utc", ""),
            "relative_path": str(out_path.relative_to(dump_dir)).replace("\\", "/"),
        })

    manifest = {
        "generated_at_utc": _now_utc_iso(),
        "cards_exported": cards_exported,
        "total_bytes": total_bytes,
        "cards": manifest_entries,
    }
    manifest_path = dump_dir / LKG_MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )

    log.info(
        "export_lkg_to_disk: exported %d cards (%d bytes) to %s",
        cards_exported, total_bytes, dump_dir,
    )
    return {
        "cards_exported": cards_exported,
        "manifest_path": str(manifest_path),
        "total_bytes": total_bytes,
    }


def import_lkg_from_disk(db: "Database", dump_dir: Path = LKG_DUMP_DIR) -> dict:
    """Reverse of export_lkg_to_disk.

    Reads dump_dir/index.json + cards/, upserts into chronicle_card_cache
    with is_lkg=1.

    Use case: fresh DB on a CI runner — bootstrap LKG cards from git.

    Returns summary: {cards_imported, manifest_path}.
    """
    dump_dir = Path(dump_dir)
    manifest_path = dump_dir / LKG_MANIFEST_NAME

    if not manifest_path.exists():
        log.warning("import_lkg_from_disk: no manifest at %s — nothing to import", manifest_path)
        return {"cards_imported": 0, "manifest_path": str(manifest_path)}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("cards", [])
    cards_imported = 0

    for entry in entries:
        rel_path = entry.get("relative_path", "")
        card_path = dump_dir / rel_path
        if not card_path.exists():
            log.warning("import_lkg_from_disk: missing file %s — skipping", card_path)
            continue

        row_dict = json.loads(card_path.read_text(encoding="utf-8"))

        # Re-serialize card_content_json back to a string for DB storage
        ccj = row_dict.get("card_content_json", {})
        if isinstance(ccj, dict):
            row_dict["card_content_json"] = json.dumps(ccj)

        # Ensure is_lkg is set
        row_dict["is_lkg"] = 1

        # Build the upsert using query_all (which handles commit for mutating queries)
        columns = list(row_dict.keys())
        col_csv = ", ".join(columns)
        placeholder_csv = ", ".join(f":{c}" for c in columns)
        update_csv = ", ".join(
            f"{c} = excluded.{c}"
            for c in columns
            if c != "cache_key"
        )
        upsert_sql = (
            f"INSERT INTO chronicle_card_cache ({col_csv}) VALUES ({placeholder_csv})"
            f" ON CONFLICT(cache_key) DO UPDATE SET {update_csv}"
        )

        try:
            db.execute(upsert_sql, row_dict)
            cards_imported += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("import_lkg_from_disk: failed to import %s: %s", entry.get("cache_key"), exc)

    log.info("import_lkg_from_disk: imported %d/%d cards from %s", cards_imported, len(entries), dump_dir)
    return {"cards_imported": cards_imported, "manifest_path": str(manifest_path)}


def compute_lkg_health(db: "Database") -> dict:
    """Return monitoring summary:

    - total_lkg_cards
    - lkg_by_card_type
    - oldest_lkg_card_age_days
    - lkg_freshness_p50_days
    - lkg_freshness_p95_days
    - stale_count (> LKG_STALE_DAYS days old)
    """
    rows = db.query_all(
        """
        SELECT card_type, lkg_promoted_at_utc
          FROM chronicle_card_cache
         WHERE is_lkg = 1
           AND lkg_promoted_at_utc IS NOT NULL
        """
    )

    if not rows:
        return {
            "total_lkg_cards": 0,
            "lkg_by_card_type": {},
            "oldest_lkg_card_age_days": None,
            "lkg_freshness_p50_days": None,
            "lkg_freshness_p95_days": None,
            "stale_count": 0,
        }

    card_type_counts: dict[str, int] = {}
    ages: list[float] = []

    for row in rows:
        ct = row["card_type"]
        card_type_counts[ct] = card_type_counts.get(ct, 0) + 1
        ages.append(_age_days(row["lkg_promoted_at_utc"]))

    ages_sorted = sorted(ages)
    n = len(ages_sorted)

    def _percentile(sorted_list: list[float], pct: float) -> float:
        idx = int(pct / 100.0 * (len(sorted_list) - 1))
        return round(sorted_list[idx], 2)

    stale_count = sum(1 for a in ages if a > LKG_STALE_DAYS)

    return {
        "total_lkg_cards": n,
        "lkg_by_card_type": card_type_counts,
        "oldest_lkg_card_age_days": round(max(ages), 2) if ages else None,
        "lkg_freshness_p50_days": _percentile(ages_sorted, 50),
        "lkg_freshness_p95_days": _percentile(ages_sorted, 95),
        "stale_count": stale_count,
    }


# ---------------------------------------------------------------------------
# CLI entry point (used by emergency_publish.ps1 via python -m)
# ---------------------------------------------------------------------------

def _cli_main() -> None:
    """Minimal CLI for emergency_publish.ps1 integration.

    Usage:
        python -m cfb_rankings.chronicle.lkg --import-from-disk
        python -m cfb_rankings.chronicle.lkg --export-to-disk
        python -m cfb_rankings.chronicle.lkg --health
    """
    import argparse
    from cfb_rankings.db import Database

    parser = argparse.ArgumentParser(description="Chronicle LKG cache utility")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--import-from-disk", action="store_true", help="Bootstrap LKG from disk dump into DB")
    group.add_argument("--export-to-disk", action="store_true", help="Export LKG cards from DB to disk dump")
    group.add_argument("--health", action="store_true", help="Print LKG health summary")
    parser.add_argument("--db", default="cfb_rankings.db", help="Path to SQLite DB")
    parser.add_argument("--dump-dir", default=str(LKG_DUMP_DIR), help="Path to LKG dump directory")

    args = parser.parse_args()
    db = Database(args.db)
    dump_dir = Path(args.dump_dir)

    if args.import_from_disk:
        result = import_lkg_from_disk(db, dump_dir)
        print(f"Imported {result['cards_imported']} LKG cards from {result['manifest_path']}")

    elif args.export_to_disk:
        result = export_lkg_to_disk(db, dump_dir)
        print(
            f"Exported {result['cards_exported']} LKG cards "
            f"({result['total_bytes']} bytes) to {result['manifest_path']}"
        )

    elif args.health:
        health = compute_lkg_health(db)
        print(json.dumps(health, indent=2))


if __name__ == "__main__":
    _cli_main()
