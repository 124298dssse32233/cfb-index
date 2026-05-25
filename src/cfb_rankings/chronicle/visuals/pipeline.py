"""Visual generation pipeline — orchestrates query → render → score → cache.

This is the v1 "Python rule engine" Visual Director: it picks visuals based on
data availability rather than asking an LLM to choose. The proposal allows an
LLM Visual Director later, but Discover phase recommended the rule engine for
v1 to isolate rendering risk from prompt-schema risk.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from .models import (
    VisualSpec,
    VisualReceipt,
    VisualResult,
    VisualId,
    EntityScope,
    Annotation,
    ConfidenceBand,
)
from .scorer import score_visual, VISUAL_SUPPRESS_THRESHOLD
from .registry import (
    list_registered_visuals,
    get_query_function,
    get_renderer_function,
    get_chart_family,
)
from .cache import (
    compute_visual_cache_key,
    compute_data_fingerprint,
    compute_thesis_hash,
    store_visual,
    get_cached_visual,
    retire_visual_scope,
)
from .share_renderer import write_share_png

log = logging.getLogger("cfb_rankings.chronicle.visuals.pipeline")


def generate_visuals_for_team(
    db: Any,
    *,
    slug: str,
    season_year: int,
    week_number: int | None = None,
    visual_ids: list[VisualId] | None = None,
    force_regenerate: bool = False,
) -> list[VisualResult]:
    """Generate (and cache) all registered visuals for a team."""
    if visual_ids is None:
        visual_ids = list_registered_visuals()

    seen_theses: set[str] = set()
    results: list[VisualResult] = []
    for vid in visual_ids:
        try:
            result = _generate_one(
                db,
                visual_id=vid,
                slug=slug,
                season_year=season_year,
                week_number=week_number,
                force_regenerate=force_regenerate,
            )
            if not result:
                continue
            # Cross-visual thesis dedup: if two visuals on the same team page
            # would carry the same thesis (visual_id + thesis_direction + primary
            # source) the second one is marked suppressed so only one ships.
            if result.visual_thesis_hash in seen_theses and not result.suppressed:
                result.suppressed = True
                result.suppression_reason = "duplicate thesis on same team-page run"
                log.info(
                    "visual %s for %s suppressed — duplicate thesis hash %s",
                    vid.value, slug, result.visual_thesis_hash,
                )
            else:
                seen_theses.add(result.visual_thesis_hash)
            results.append(result)
        except Exception as exc:
            log.exception("visual %s failed for %s: %s", vid, slug, exc)
    return results


def generate_all_visuals(
    db: Any,
    *,
    season_year: int,
    week_number: int | None = None,
    team_slugs: list[str] | None = None,
    force_regenerate: bool = False,
    limit_teams: int | None = None,
) -> dict[str, list[VisualResult]]:
    """Batch generate visuals across teams.

    If team_slugs is None, pulls all active FBS teams from the DB.
    """
    if team_slugs is None:
        team_slugs = _all_fbs_team_slugs(db)
    if limit_teams:
        team_slugs = team_slugs[:limit_teams]

    out: dict[str, list[VisualResult]] = {}
    for slug in team_slugs:
        out[slug] = generate_visuals_for_team(
            db,
            slug=slug,
            season_year=season_year,
            week_number=week_number,
            force_regenerate=force_regenerate,
        )
    return out


def _all_fbs_team_slugs(db: Any) -> list[str]:
    rows = []
    if hasattr(db, "query_all"):
        rows = db.query_all(
            "SELECT slug FROM teams WHERE level_code='FBS' AND is_active=1 ORDER BY canonical_name"
        )
    else:
        cur = db.execute(
            "SELECT slug FROM teams WHERE level_code='FBS' AND is_active=1 ORDER BY canonical_name"
        )
        rows = [{"slug": r[0]} for r in cur.fetchall()]
    return [r["slug"] for r in rows if r["slug"]]


def _generate_one(
    db: Any,
    *,
    visual_id: VisualId,
    slug: str,
    season_year: int,
    week_number: int | None,
    force_regenerate: bool,
) -> VisualResult | None:
    t0 = time.time()
    query_fn = get_query_function(visual_id)
    render_fn = get_renderer_function(visual_id)
    chart_family = get_chart_family(visual_id)

    # Posture-aware season: the caller passes the PREVIEW season (e.g. 2025).
    # Preview visuals query that season; retrospective visuals query the
    # latest completed-game season (preview - 1). See registry.VISUAL_POSTURE
    # and memory project-offseason-preview-posture.
    from .registry import get_posture, RETROSPECTIVE
    effective_season = season_year
    if get_posture(visual_id) == RETROSPECTIVE:
        effective_season = season_year - 1

    # Step 1: data query
    query_result = query_fn(db, slug=slug, season_year=effective_season, week_number=week_number)
    data_fingerprint = compute_data_fingerprint(query_result)

    # Step 2: compute cache key — entity_kind defaults to 'team' for this
    # call site but is derived from spec.entity_scope shape so player/league
    # visuals get a distinct key namespace and can't collide via shared slugs.
    entity_kind = "team"  # generate_visuals_for_team contract
    cache_key = compute_visual_cache_key(
        slug=slug,
        entity_kind=entity_kind,
        season_year=effective_season,
        week_number=week_number,
        visual_id=visual_id.value,
        data_query_id=query_result["query_id"],
        renderer_version=_renderer_version(),
        data_fingerprint=data_fingerprint,
        schema_version=_schema_version(),
    )

    # Step 3: cache lookup
    if not force_regenerate:
        cached = get_cached_visual(db, cache_key)
        if cached:
            return _hydrate_cached(cached, query_result)

    # Step 4: data-floor gate — skip empty results. Retire any previously
    # cached row for this scope first, so a visual that used to generate but
    # now gates to empty (e.g. a team-relevance gate fired) stops shipping the
    # stale card instead of leaving the old active row in place.
    if query_result["sample_n"] == 0:
        retired = retire_visual_scope(
            db,
            slug=slug,
            season_year=effective_season,
            week_number=week_number,
            visual_id=visual_id.value,
        )
        if retired:
            log.info(
                "visual %s: empty query for %s — retired %d stale cache row(s)",
                visual_id.value, slug, retired,
            )
        else:
            log.debug("visual %s: empty query, skipping for %s", visual_id.value, slug)
        return None

    # Step 5: render
    rendered = render_fn(query_result)

    # Step 6: build spec + receipt
    spec = VisualSpec(
        visual_id=visual_id,
        chart_family=chart_family,
        headline_finding=rendered["headline_finding"],
        data_query_id=query_result["query_id"],
        entity_scope=EntityScope(slug=slug, season_year=effective_season, week_number=week_number),
        annotations=rendered.get("annotations", []),
        required_sources=query_result.get("source_tables", []),
        alt_text=rendered.get("alt_text", ""),
    )
    receipt = VisualReceipt(
        query_id=query_result["query_id"],
        source_tables=query_result.get("source_tables", []),
        sample_n=query_result["sample_n"],
        confidence=ConfidenceBand(query_result["confidence"]),
        limitations=query_result.get("limitations", []),
        as_of_utc=query_result.get("as_of_utc", ""),
    )

    # Step 7: score
    score = score_visual(spec, receipt)
    suppressed = score.total < VISUAL_SUPPRESS_THRESHOLD
    suppression_reason = (
        f"score {score.total:.2f} below threshold {VISUAL_SUPPRESS_THRESHOLD}"
        if suppressed else ""
    )

    # Step 8: anti-dup thesis hash
    primary_source = (query_result.get("source_tables") or ["unknown"])[0]
    thesis_hash = compute_thesis_hash(
        visual_id.value,
        thesis_direction=_thesis_direction(query_result),
        primary_source=primary_source,
    )

    # Share-card PNG export (deferred-friendly: returns None if resvg-py absent
    # or any rendering failure happens; the visual still ships as inline SVG).
    share_asset_path = None
    if not suppressed:
        share_asset_path = write_share_png(
            slug=slug,
            visual_id=visual_id.value,
            inner_svg=rendered["svg_html"],
            headline=rendered["headline_finding"],
            sample_n=receipt.sample_n,
            confidence=receipt.confidence.value,
        )

    result = VisualResult(
        visual_cache_key=cache_key,
        spec=spec,
        receipt=receipt,
        score=score,
        svg_html=rendered["svg_html"],
        share_asset_path=share_asset_path,
        visual_thesis_hash=thesis_hash,
        visual_data_fingerprint=data_fingerprint,
        suppressed=suppressed,
        suppression_reason=suppression_reason,
        wall_clock_ms=int((time.time() - t0) * 1000),
        rows=query_result.get("rows", []),
    )

    # Step 9: store
    try:
        store_visual(db, result)
    except Exception as exc:
        log.exception("failed to store visual %s for %s: %s", visual_id.value, slug, exc)

    return result


def _thesis_direction(query_result: dict[str, Any]) -> str:
    summary = query_result.get("summary_stats", {}) or {}
    rows = query_result.get("rows", []) or []
    # crude direction marker for anti-dup
    if "net_movement" in summary:
        n = summary["net_movement"]
        return "gain" if n > 0 else ("loss" if n < 0 else "flat")
    if rows and "total_delta" in (rows[0] or {}):
        n = rows[0]["total_delta"]
        return "up" if n > 0 else ("down" if n < 0 else "flat")
    return "neutral"


def _hydrate_cached(cached: dict, query_result: dict[str, Any]) -> VisualResult:
    """Build a VisualResult from a cached DB row (skip re-render)."""
    import json as _json
    spec = VisualSpec.model_validate_json(cached["visual_spec_json"])
    receipt = VisualReceipt.model_validate_json(cached["visual_receipt_json"])
    score = _score_from_cached(cached)
    return VisualResult(
        visual_cache_key=cached["visual_cache_key"],
        spec=spec,
        receipt=receipt,
        score=score,
        svg_html=cached["svg_html"] or "",
        share_asset_path=cached.get("share_asset_path"),
        visual_thesis_hash=cached.get("visual_thesis_hash") or "",
        visual_data_fingerprint=cached.get("visual_data_fingerprint") or "",
        suppressed=bool(cached.get("suppressed", 0)),
        suppression_reason=cached.get("suppression_reason") or "",
        wall_clock_ms=int(cached.get("wall_clock_ms") or 0),
        rows=query_result.get("rows", []),
    )


def _score_from_cached(cached: dict):
    from .models import VisualQualityScore
    return VisualQualityScore(
        clarity=cached.get("clarity_score") or 0,
        fan_relevance=cached.get("fan_relevance_score") or 0,
        data_depth=cached.get("data_depth_score") or 0,
        novelty=cached.get("novelty_score") or 0,
        mobile_legibility=cached.get("mobile_legibility_score") or 0,
        screenshot_value=cached.get("screenshot_value_score") or 0,
        evidence_strength=cached.get("evidence_strength_score") or 0,
        voice_fit=cached.get("voice_fit_score") or 0,
        total=cached.get("visual_quality_score") or 0,
    )


def _renderer_version() -> str:
    from . import RENDERER_VERSION
    return RENDERER_VERSION


def _schema_version() -> str:
    from . import SCHEMA_VERSION
    return SCHEMA_VERSION
