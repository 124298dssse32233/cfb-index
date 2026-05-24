"""Chronicle Visual Cache — sidecar to chronicle_card_cache.

See migrations/20260526_01_chronicle_visual_cache.sql for the schema.

Cache key composition:
    sha256(slug | entity_kind | season_year | week_number |
           visual_id | data_query_id | renderer_version |
           data_fingerprint | schema_version)[:32]

Supersession: regenerating a visual sets superseded_at_utc on the old row and
inserts a new one with NULL — same model as chronicle_card_cache.

LKG: when generation fails QA gates, fetch the most-recent is_lkg=1 row.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from .models import VisualResult

log = logging.getLogger("cfb_rankings.chronicle.visuals.cache")


# ---------------------------------------------------------------------------
# Cache-key computation
# ---------------------------------------------------------------------------


def compute_visual_cache_key(
    *,
    slug: str,
    entity_kind: str,
    season_year: int | None,
    week_number: int | None,
    visual_id: str,
    data_query_id: str,
    renderer_version: str,
    data_fingerprint: str,
    schema_version: str,
) -> str:
    def _s(x: Any) -> str:
        return "" if x is None else str(x)

    canonical = "|".join([
        _s(slug),
        _s(entity_kind),
        _s(season_year),
        _s(week_number),
        _s(visual_id),
        _s(data_query_id),
        _s(renderer_version),
        _s(data_fingerprint),
        _s(schema_version),
    ])
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def compute_data_fingerprint(query_result: dict[str, Any]) -> str:
    """Hash of the deterministic query output (rows + summary_stats).

    Uses an isoformat-coercing default so datetime/decimal values produce a
    stable string regardless of locale or timezone-printout flavor (e.g.
    `+00:00` vs `Z`). Without this, two equivalent query runs can produce
    different fingerprints and the cache stops hitting.
    """
    payload = {
        "rows": query_result.get("rows", []),
        "summary_stats": query_result.get("summary_stats", {}),
    }
    canonical = json.dumps(payload, sort_keys=True, default=_stable_repr)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _stable_repr(obj: Any) -> str:
    """Locale-stable str() fallback for json.dumps default=."""
    from decimal import Decimal
    if isinstance(obj, datetime):
        # Always UTC isoformat with explicit Z suffix
        if obj.tzinfo is None:
            return obj.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return obj.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(obj, Decimal):
        return format(obj, "f")
    if isinstance(obj, (bytes, bytearray)):
        return obj.hex()
    return str(obj)


def compute_thesis_hash(visual_id: str, thesis_direction: str, primary_source: str) -> str:
    canonical = f"{visual_id}|{thesis_direction}|{primary_source}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# DB helpers — work with both project Database wrapper and raw sqlite3
# ---------------------------------------------------------------------------


def _query_all(db: Any, sql: str, params: tuple | dict = ()) -> list[dict]:
    if hasattr(db, "query_all"):
        return db.query_all(sql, params)
    cur = db.execute(sql, params)
    cols = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _query_one(db: Any, sql: str, params: tuple | dict = ()) -> dict | None:
    rows = _query_all(db, sql, params)
    return rows[0] if rows else None


def _execute(db: Any, sql: str, params: tuple | dict = ()) -> Any:
    if hasattr(db, "execute"):
        result = db.execute(sql, params)
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


def get_cached_visual(db: Any, visual_cache_key: str) -> dict | None:
    """Return the active (non-superseded) cached visual row by key, or None."""
    return _query_one(
        db,
        """
        SELECT * FROM chronicle_visual_cache
        WHERE visual_cache_key = :key AND superseded_at_utc IS NULL
        LIMIT 1
        """,
        {"key": visual_cache_key},
    )


def store_visual(db: Any, result: VisualResult) -> None:
    """Write a visual row, replacing any prior row with the same cache_key.

    The cache_key is deterministic over (slug, season, week, visual_id,
    data_query_id, renderer_version, data_fingerprint, schema_version) — so
    "same key" means the inputs and renderer are identical, and replacing is
    semantically equivalent to "no-op the cache; just refresh wall_clock_ms
    and created_at_utc."

    When data_fingerprint or renderer_version change, the key changes too, so
    the OLD row is preserved (different PK). A separate sweep can supersede
    the older rows for the same scope — see _supersede_other_scope_rows below.
    """
    spec = result.spec
    receipt = result.receipt
    score = result.score

    # Preserve LKG status across forced regenerates with identical cache key —
    # INSERT OR REPLACE drops the prior row entirely, so any is_lkg=1 flag
    # would be lost. Read it back first and re-apply on insert.
    prior_lkg = _query_one(
        db,
        "SELECT is_lkg, lkg_promoted_at_utc FROM chronicle_visual_cache WHERE visual_cache_key = :key",
        {"key": result.visual_cache_key},
    ) or {}
    preserved_is_lkg = int(prior_lkg.get("is_lkg") or 0)
    preserved_lkg_at = prior_lkg.get("lkg_promoted_at_utc")

    # Supersede prior active rows for the same scope but a DIFFERENT cache_key
    # (i.e. data fingerprint or renderer version changed — old row is now stale).
    _execute(
        db,
        """
        UPDATE chronicle_visual_cache
        SET superseded_at_utc = :now
        WHERE slug = :slug
          AND COALESCE(season_year, -1) = COALESCE(:season, -1)
          AND COALESCE(week_number, -1) = COALESCE(:week, -1)
          AND visual_id = :vid
          AND visual_cache_key != :key
          AND superseded_at_utc IS NULL
        """,
        {
            "now": _now_utc(),
            "slug": spec.entity_scope.slug,
            "season": spec.entity_scope.season_year,
            "week": spec.entity_scope.week_number,
            "vid": spec.visual_id.value,
            "key": result.visual_cache_key,
        },
    )

    _execute(
        db,
        """
        INSERT OR REPLACE INTO chronicle_visual_cache (
            visual_cache_key, slug, entity_kind, season_year, week_number,
            card_cache_key, visual_id, chart_family, data_query_id,
            visual_spec_json, visual_receipt_json, svg_html, share_asset_path,
            headline_finding, visual_thesis_hash, visual_data_fingerprint,
            renderer_version, schema_version, sample_n, confidence_band,
            visual_quality_score, clarity_score, fan_relevance_score,
            data_depth_score, novelty_score, mobile_legibility_score,
            screenshot_value_score, evidence_strength_score, voice_fit_score,
            suppressed, suppression_reason, is_lkg, lkg_promoted_at_utc,
            wall_clock_ms, created_at_utc
        ) VALUES (
            :visual_cache_key, :slug, :entity_kind, :season_year, :week_number,
            :card_cache_key, :visual_id, :chart_family, :data_query_id,
            :visual_spec_json, :visual_receipt_json, :svg_html, :share_asset_path,
            :headline_finding, :visual_thesis_hash, :visual_data_fingerprint,
            :renderer_version, :schema_version, :sample_n, :confidence_band,
            :visual_quality_score, :clarity_score, :fan_relevance_score,
            :data_depth_score, :novelty_score, :mobile_legibility_score,
            :screenshot_value_score, :evidence_strength_score, :voice_fit_score,
            :suppressed, :suppression_reason, :is_lkg, :lkg_promoted_at_utc,
            :wall_clock_ms, :now
        )
        """,
        {
            "visual_cache_key": result.visual_cache_key,
            "slug": spec.entity_scope.slug,
            "entity_kind": _entity_kind_for(spec),
            "season_year": spec.entity_scope.season_year,
            "week_number": spec.entity_scope.week_number,
            "card_cache_key": None,
            "visual_id": spec.visual_id.value,
            "chart_family": spec.chart_family.value,
            "data_query_id": spec.data_query_id,
            "visual_spec_json": spec.model_dump_json(),
            "visual_receipt_json": receipt.model_dump_json(),
            "svg_html": result.svg_html,
            "share_asset_path": result.share_asset_path,
            "headline_finding": spec.headline_finding,
            "visual_thesis_hash": result.visual_thesis_hash,
            "visual_data_fingerprint": result.visual_data_fingerprint,
            "renderer_version": _renderer_version(),
            "schema_version": _schema_version(),
            "sample_n": receipt.sample_n,
            "confidence_band": receipt.confidence.value,
            "visual_quality_score": score.total,
            "clarity_score": score.clarity,
            "fan_relevance_score": score.fan_relevance,
            "data_depth_score": score.data_depth,
            "novelty_score": score.novelty,
            "mobile_legibility_score": score.mobile_legibility,
            "screenshot_value_score": score.screenshot_value,
            "evidence_strength_score": score.evidence_strength,
            "voice_fit_score": score.voice_fit,
            "suppressed": 1 if result.suppressed else 0,
            "suppression_reason": result.suppression_reason,
            "is_lkg": preserved_is_lkg,
            "lkg_promoted_at_utc": preserved_lkg_at,
            "wall_clock_ms": result.wall_clock_ms,
            "now": _now_utc(),
        },
    )
    log.info("stored visual %s for %s (score=%.2f)", spec.visual_id.value, spec.entity_scope.slug, score.total)


def fetch_visual_cards(
    db: Any,
    slug: str,
    season_year: int | None = None,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Fetch the active visual cards for a slug. Consumer hook for team_pages."""
    where = ["slug = :slug", "superseded_at_utc IS NULL", "suppressed = 0", "svg_html IS NOT NULL"]
    params: dict[str, Any] = {"slug": slug, "limit": limit}
    if season_year is not None:
        where.append("(season_year = :season OR season_year IS NULL)")
        params["season"] = season_year

    sql = f"""
        SELECT visual_id, chart_family, headline_finding, svg_html,
               share_asset_path, sample_n, confidence_band, visual_quality_score,
               season_year, week_number, created_at_utc, is_lkg
        FROM chronicle_visual_cache
        WHERE {' AND '.join(where)}
          AND COALESCE(suppressed, 0) = 0
        ORDER BY is_lkg DESC, visual_quality_score DESC, season_year DESC, week_number DESC
        LIMIT :limit
    """
    rows = _query_all(db, sql, params)
    return rows


def promote_visual_lkg(db: Any, visual_cache_key: str) -> bool:
    cur = _execute(
        db,
        """
        UPDATE chronicle_visual_cache
        SET is_lkg = 1, lkg_promoted_at_utc = :now
        WHERE visual_cache_key = :key
        """,
        {"key": visual_cache_key, "now": _now_utc()},
    )
    try:
        return cur.rowcount > 0
    except Exception:
        return True


def visual_cache_health(db: Any) -> dict:
    summary = _query_one(
        db,
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN superseded_at_utc IS NULL THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN is_lkg = 1 THEN 1 ELSE 0 END) AS lkg,
            SUM(CASE WHEN suppressed = 1 THEN 1 ELSE 0 END) AS suppressed,
            AVG(visual_quality_score) AS avg_score
        FROM chronicle_visual_cache
        """,
    )
    return summary or {}


def _entity_kind_for(spec) -> str:
    if spec.entity_scope.player_id is not None:
        return "player"
    return "team"


def _renderer_version() -> str:
    from . import RENDERER_VERSION
    return RENDERER_VERSION


def _schema_version() -> str:
    from . import SCHEMA_VERSION
    return SCHEMA_VERSION
