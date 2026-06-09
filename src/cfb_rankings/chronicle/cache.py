"""Chronicle cache layer.

SHA-256 truncated cache keys keyed on:
  sha256(slug | season | week | card_type | slot | evidence_hash |
         prompt_template_id | model_id | model_version | schema_version)[:32]

Two-tier cache:
  - chronicle_card_cache table: SQLite-backed result cache (this module)
  - llama-server prompt cache: in-server prefix cache (handled by runtime.py
    via cache_prompt=true)

The chronicle_card_cache schema lives in migration 20260524_03 — column names
here MUST match that migration exactly.

Public API:
    compute_cache_key(...)        -> str (32-hex)
    get_cached_card(db, key)      -> dict | None
    store_card(db, ...)           -> None
    invalidate_by_prefix(db, ...) -> int  (count invalidated)
    promote_lkg(db, key)          -> bool
    cache_health(db)              -> dict (hit-rate metrics)
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("cfb_rankings.chronicle.cache")


# ---------------------------------------------------------------------------
# Cache-key computation
# ---------------------------------------------------------------------------


def compute_cache_key(
    *,
    slug: str,
    season_year: int | None,
    week_number: int | None,
    card_type: str,
    slot_index: int | None,
    evidence_hash: str,
    prompt_template_id: str,
    model_id: str,
    model_version: str,
    schema_version: str,
) -> str:
    """Compute the canonical 32-hex cache key.

    All components are joined with '|' as a separator and SHA-256 hashed.
    The result is truncated to the first 32 hex chars (128 bits — collision-safe
    at our volume).

    None values are normalized to empty string before hashing so that the key
    is stable across calls that pass None vs the literal string "None".
    """

    def _s(x: Any) -> str:
        return "" if x is None else str(x)

    canonical = "|".join([
        _s(slug),
        _s(season_year),
        _s(week_number),
        _s(card_type),
        _s(slot_index),
        _s(evidence_hash),
        _s(prompt_template_id),
        _s(model_id),
        _s(model_version),
        _s(schema_version),
    ])
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# DB helpers — work with both project Database wrapper and raw sqlite3
# ---------------------------------------------------------------------------


def _query_all(db: Any, sql: str, params: tuple = ()) -> list[dict]:
    """Run a query and return list[dict] regardless of which db wrapper we got."""
    if hasattr(db, "query_all"):
        return db.query_all(sql, params)
    cur = db.execute(sql, params)
    cols = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _query_one(db: Any, sql: str, params: tuple = ()) -> dict | None:
    if hasattr(db, "query_one"):
        return db.query_one(sql, params)
    rows = _query_all(db, sql, params)
    return rows[0] if rows else None


def _execute(db: Any, sql: str, params: tuple = ()) -> Any:
    if hasattr(db, "execute"):
        result = db.execute(sql, params)
        # Some wrappers auto-commit; raw sqlite3.Connection does not
        if hasattr(db, "commit"):
            try:
                db.commit()
            except Exception:
                pass
        return result
    raise RuntimeError("db object has no execute() method")


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_cached_card(db: Any, cache_key: str) -> dict | None:
    """Fetch a single cached card by key.

    Returns the row as a dict, or None if not found / superseded.
    Only returns ACTIVE (non-superseded) rows.
    """
    row = _query_one(
        db,
        """
        SELECT *
        FROM chronicle_card_cache
        WHERE cache_key = ?
          AND superseded_at_utc IS NULL
        """,
        (cache_key,),
    )
    if row is None:
        return None
    # Decode the JSON payload for caller convenience
    out = dict(row)
    content = out.get("card_content_json")
    if isinstance(content, str):
        try:
            out["card_content"] = json.loads(content)
        except json.JSONDecodeError:
            out["card_content"] = None
    return out


def store_card(
    db: Any,
    *,
    cache_key: str,
    slug: str,
    entity_kind: str,
    season_year: int | None,
    week_number: int | None,
    card_type: str,
    slot_index: int | None,
    card_content: dict,
    card_html: str | None,
    evidence_hash: str,
    prompt_template_id: str,
    model_id: str,
    model_version: str,
    schema_version: str,
    confidence_band: str = "unset",
    voice_critic_score: float | None = None,
    fact_critic_score: float | None = None,
    collision_critic_score: float | None = None,
    factscore_atomic: float | None = None,
    word_count: int | None = None,
    generation_attempt: int = 1,
    wall_clock_ms: int | None = None,
    supersede_previous: bool = True,
) -> None:
    """Insert a new card row.

    If `supersede_previous` is True (default), any existing ACTIVE row matching
    (slug, season_year, week_number, card_type, slot_index) is marked
    superseded before the new row is inserted. This implements the temporal
    versioning model described in migration 20260524_03.

    Idempotent on cache_key collisions: if a row already exists for the SAME
    cache_key, this is a no-op (the inputs were identical so the output must
    be too, modulo nondeterministic sampling).
    """
    # Idempotency check
    existing = _query_one(
        db,
        "SELECT cache_key FROM chronicle_card_cache WHERE cache_key = ?",
        (cache_key,),
    )
    if existing:
        log.debug("store_card: cache_key %s already exists; no-op", cache_key)
        return

    if supersede_previous:
        _execute(
            db,
            """
            UPDATE chronicle_card_cache
               SET superseded_at_utc = ?
             WHERE slug = ?
               AND COALESCE(season_year, -1) = COALESCE(?, -1)
               AND COALESCE(week_number, -1) = COALESCE(?, -1)
               AND card_type = ?
               AND COALESCE(slot_index, -1) = COALESCE(?, -1)
               AND superseded_at_utc IS NULL
            """,
            (_now_utc(), slug, season_year, week_number, card_type, slot_index),
        )

    _execute(
        db,
        """
        INSERT INTO chronicle_card_cache (
            cache_key, slug, entity_kind, season_year, week_number, card_type,
            slot_index, card_content_json, card_html, evidence_hash,
            prompt_template_id, model_id, model_version, schema_version,
            confidence_band, voice_critic_score, fact_critic_score,
            collision_critic_score, factscore_atomic, word_count,
            is_lkg, generation_attempt, wall_clock_ms, created_at_utc
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?
        )
        """,
        (
            cache_key, slug, entity_kind, season_year, week_number, card_type,
            slot_index, json.dumps(card_content, ensure_ascii=False, default=str),
            card_html, evidence_hash, prompt_template_id, model_id, model_version,
            schema_version, confidence_band, voice_critic_score, fact_critic_score,
            collision_critic_score, factscore_atomic, word_count,
            generation_attempt, wall_clock_ms, _now_utc(),
        ),
    )


def invalidate_by_prefix(
    db: Any,
    *,
    slug: str | None = None,
    card_type: str | None = None,
    season_year: int | None = None,
    model_id: str | None = None,
    prompt_template_id: str | None = None,
) -> int:
    """Mark ACTIVE rows matching the filter as superseded.

    All filter args are AND-ed. None values are ignored (do not constrain).
    Returns count of rows affected.

    NB: this never DELETEs — temporal history is preserved.
    """
    clauses = ["superseded_at_utc IS NULL"]
    params: list[Any] = []
    if slug is not None:
        clauses.append("slug = ?")
        params.append(slug)
    if card_type is not None:
        clauses.append("card_type = ?")
        params.append(card_type)
    if season_year is not None:
        clauses.append("season_year = ?")
        params.append(season_year)
    if model_id is not None:
        clauses.append("model_id = ?")
        params.append(model_id)
    if prompt_template_id is not None:
        clauses.append("prompt_template_id = ?")
        params.append(prompt_template_id)

    if len(clauses) == 1:
        # No actual filter — refuse to invalidate everything by accident
        log.warning("invalidate_by_prefix called with no filters — refusing")
        return 0

    # Count first
    count_sql = "SELECT COUNT(*) AS n FROM chronicle_card_cache WHERE " + " AND ".join(clauses)
    row = _query_one(db, count_sql, tuple(params))
    n = int(row["n"]) if row else 0
    if n == 0:
        return 0

    update_sql = (
        "UPDATE chronicle_card_cache SET superseded_at_utc = ? WHERE "
        + " AND ".join(clauses)
    )
    _execute(db, update_sql, (_now_utc(), *params))
    return n


def promote_lkg(db: Any, cache_key: str) -> bool:
    """Mark a card as Last-Known-Good.

    Sets is_lkg=1 and lkg_promoted_at_utc=now() on the row with the given key.
    Returns True if the row was updated, False if no such row exists.

    NB: there can be multiple LKG rows for the same (slug, card_type). The
    LKG-fallback query in lkg.py picks the most recent by lkg_promoted_at_utc.
    """
    existing = _query_one(
        db,
        "SELECT cache_key FROM chronicle_card_cache WHERE cache_key = ?",
        (cache_key,),
    )
    if not existing:
        return False
    _execute(
        db,
        """
        UPDATE chronicle_card_cache
           SET is_lkg = 1, lkg_promoted_at_utc = ?
         WHERE cache_key = ?
        """,
        (_now_utc(), cache_key),
    )
    return True


def cache_health(db: Any) -> dict:
    """Return aggregate cache stats for monitoring.

    Keys:
        total_rows: int — all-time inserts
        active_rows: int — non-superseded
        lkg_rows: int — is_lkg=1
        by_card_type: dict[str,int] — active row count per card_type
        by_model_id: dict[str,int] — active row count per model_id
        avg_wall_clock_ms: float | None
        avg_factscore_atomic: float | None
    """
    out: dict[str, Any] = {
        "total_rows": 0,
        "active_rows": 0,
        "lkg_rows": 0,
        "by_card_type": {},
        "by_model_id": {},
        "avg_wall_clock_ms": None,
        "avg_factscore_atomic": None,
    }

    row = _query_one(db, "SELECT COUNT(*) AS n FROM chronicle_card_cache")
    if row:
        out["total_rows"] = int(row["n"])
    row = _query_one(
        db,
        "SELECT COUNT(*) AS n FROM chronicle_card_cache WHERE superseded_at_utc IS NULL",
    )
    if row:
        out["active_rows"] = int(row["n"])
    row = _query_one(
        db, "SELECT COUNT(*) AS n FROM chronicle_card_cache WHERE is_lkg = 1",
    )
    if row:
        out["lkg_rows"] = int(row["n"])

    rows = _query_all(
        db,
        """
        SELECT card_type, COUNT(*) AS n
          FROM chronicle_card_cache
         WHERE superseded_at_utc IS NULL
         GROUP BY card_type
        """,
    )
    out["by_card_type"] = {r["card_type"]: int(r["n"]) for r in rows}

    rows = _query_all(
        db,
        """
        SELECT model_id, COUNT(*) AS n
          FROM chronicle_card_cache
         WHERE superseded_at_utc IS NULL
         GROUP BY model_id
        """,
    )
    out["by_model_id"] = {r["model_id"]: int(r["n"]) for r in rows}

    row = _query_one(
        db,
        """
        SELECT AVG(wall_clock_ms) AS w, AVG(factscore_atomic) AS f
          FROM chronicle_card_cache
         WHERE superseded_at_utc IS NULL
        """,
    )
    if row:
        out["avg_wall_clock_ms"] = float(row["w"]) if row.get("w") is not None else None
        out["avg_factscore_atomic"] = float(row["f"]) if row.get("f") is not None else None

    return out


__all__ = [
    "compute_cache_key",
    "get_cached_card",
    "store_card",
    "invalidate_by_prefix",
    "promote_lkg",
    "cache_health",
]
