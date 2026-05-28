"""WS-09 prediction ledger: record, resolve, and summarize model predictions.

This is the data layer of the calibration trust spine (spec 09-calibration-ledger).
The full in-season build wraps every prediction-rendering chip; for now the write
path is real and one live surface (archetype assignments) is instrumented so the
record -> resolve -> summarize loop runs end-to-end against real data.

Confidence bands mirror cfb_rankings.confidence.Band (high/medium/low/unset).
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from cfb_rankings.db import Database

# A resolver maps a due ledger row to (actual_value, accuracy_score, note).
# Returning actual_value=None means "outcome not knowable yet" -> leave unresolved.
Resolver = Callable[[Database, dict[str, Any]], tuple[Optional[str], Optional[float], str]]

_VALID_BANDS = frozenset({"high", "medium", "low", "unset"})


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def prediction_id_for(
    model_id: str,
    entity_type: str,
    entity_id: str,
    prediction_kind: str,
    period_key: str,
) -> str:
    """Deterministic id so re-recording the same window upserts (never appends)."""
    raw = "|".join((model_id, entity_type, entity_id, prediction_kind, period_key))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _band_for_confidence(confidence: Optional[float]) -> str:
    """Map a 0..1 model confidence to an editorial band. Thresholds align with the
    high/medium/low ramp; absent confidence -> unset (suppress, per design doc 33)."""
    if confidence is None:
        return "unset"
    if confidence >= 0.66:
        return "high"
    if confidence >= 0.40:
        return "medium"
    return "low"


def record_prediction(
    db: Database,
    *,
    model_id: str,
    entity_type: str,
    entity_id: str,
    prediction_kind: str,
    period_key: str,
    predicted_value: str,
    confidence_band: Optional[str] = None,
    confidence_value: Optional[float] = None,
    evidence_ref: Optional[str] = None,
    expires_at: Optional[str] = None,
    model_version: Optional[str] = None,
    observed_at: Optional[str] = None,
) -> str:
    """Log/refresh one standing prediction. Idempotent on the deterministic id.

    Re-recording the same (model, entity, kind, period) refreshes the standing
    prediction's value/confidence/expiry but preserves observed_at_utc (first-seen)
    and never clobbers a resolution already written by resolve_due_predictions.
    Returns the prediction_id.
    """
    if confidence_band is None:
        confidence_band = _band_for_confidence(confidence_value)
    if confidence_band not in _VALID_BANDS:
        raise ValueError(f"invalid confidence_band {confidence_band!r}; expected one of {sorted(_VALID_BANDS)}")

    pid = prediction_id_for(model_id, entity_type, entity_id, prediction_kind, period_key)
    now = _utcnow()
    db.upsert_many(
        "prediction_ledger",
        [{
            "prediction_id": pid,
            "model_id": model_id,
            "model_version": model_version,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "prediction_kind": prediction_kind,
            "period_key": period_key,
            "predicted_value": predicted_value,
            "confidence_band": confidence_band,
            "confidence_value": confidence_value,
            "evidence_ref": evidence_ref,
            "observed_at_utc": observed_at or now,
            "expires_at_utc": expires_at,
            "updated_at_utc": now,
        }],
        conflict_columns=["prediction_id"],
        # Deliberately exclude observed_at_utc and the resolution columns so a
        # re-record preserves first-seen and any prior resolution.
        update_columns=[
            "model_version", "predicted_value", "confidence_band",
            "confidence_value", "evidence_ref", "expires_at_utc", "updated_at_utc",
        ],
    )
    return pid


# --------------------------------------------------------------------------- #
# Outcome resolvers (one per prediction_kind).
# --------------------------------------------------------------------------- #
def _resolve_archetype_assignment(
    db: Database, row: dict[str, Any]
) -> tuple[Optional[str], Optional[float], str]:
    """Grade an archetype_assignment for season=period_key against the actual
    fanbase_classification computed for that season. 1.0 if the predicted archetype
    held, else 0.0. None actual -> that season not yet classified (stay unresolved)."""
    try:
        season = int(row["period_key"])
    except (TypeError, ValueError):
        return None, None, "non-numeric period_key"
    actual = db.query_one(
        """
        select fc.primary_archetype_slug as slug
        from fanbase_classification fc
        join teams t on t.team_id = fc.team_id
        where t.slug = :slug and fc.season_year = :season
        """,
        {"slug": row["entity_id"], "season": season},
    )
    if not actual or not actual.get("slug"):
        return None, None, "season not yet classified"
    actual_slug = str(actual["slug"])
    score = 1.0 if actual_slug == row["predicted_value"] else 0.0
    return actual_slug, score, "held" if score else "revised"


OUTCOME_RESOLVERS: dict[str, Resolver] = {
    "archetype_assignment": _resolve_archetype_assignment,
}


def resolve_due_predictions(
    db: Database,
    *,
    now: Optional[str] = None,
    kinds: Optional[list[str]] = None,
    resolvers: Optional[dict[str, Resolver]] = None,
) -> dict[str, Any]:
    """Weekly resolver: for every unresolved prediction whose expires_at_utc has
    passed, call the kind's resolver and write actual_value/accuracy_score/resolved_at.

    A prediction whose resolver yields actual_value=None (outcome not yet knowable)
    is left unresolved for a later pass. Returns counts {due, resolved, skipped, by_kind}.
    """
    now = now or _utcnow()
    resolvers = resolvers or OUTCOME_RESOLVERS
    params: dict[str, Any] = {"now": now}
    kind_clause = ""
    if kinds:
        placeholders = ", ".join(f":k{i}" for i in range(len(kinds)))
        kind_clause = f" and prediction_kind in ({placeholders})"
        for i, k in enumerate(kinds):
            params[f"k{i}"] = k
    due = db.query_all(
        f"""
        select * from prediction_ledger
        where resolved_at_utc is null
          and expires_at_utc is not null
          and expires_at_utc <= :now
          {kind_clause}
        """,
        params,
    )
    resolved = 0
    skipped = 0
    by_kind: dict[str, int] = {}
    for row in due:
        kind = str(row["prediction_kind"])
        resolver = resolvers.get(kind)
        if resolver is None:
            skipped += 1
            continue
        actual, score, note = resolver(db, row)
        if actual is None:
            skipped += 1
            continue
        db.execute(
            """
            update prediction_ledger
               set resolved_at_utc = :now,
                   actual_value = :actual,
                   accuracy_score = :score,
                   resolution_note = :note,
                   updated_at_utc = :now
             where prediction_id = :pid
            """,
            {"now": now, "actual": actual, "score": score, "note": note, "pid": row["prediction_id"]},
        )
        resolved += 1
        by_kind[kind] = by_kind.get(kind, 0) + 1
    return {"due": len(due), "resolved": resolved, "skipped": skipped, "by_kind": by_kind}


def calibration_summary(
    db: Database,
    *,
    model_id: Optional[str] = None,
    prediction_kind: Optional[str] = None,
    last_n: Optional[int] = None,
) -> dict[str, Any]:
    """Aggregate resolved predictions into a calibration report for the methodology
    page and the Sunday public summary (D-015 B). Returns total/resolved counts,
    mean accuracy, and per-band accuracy so the page can show 'high-confidence calls
    were right X% of the time'."""
    where = ["resolved_at_utc is not null", "accuracy_score is not null"]
    params: dict[str, Any] = {}
    if model_id:
        where.append("model_id = :model_id")
        params["model_id"] = model_id
    if prediction_kind:
        where.append("prediction_kind = :kind")
        params["kind"] = prediction_kind
    where_sql = " and ".join(where)
    order_limit = ""
    if last_n:
        order_limit = " order by resolved_at_utc desc limit :last_n"
        params["last_n"] = last_n
    rows = db.query_all(
        f"select accuracy_score, confidence_band from prediction_ledger where {where_sql}{order_limit}",
        params,
    )
    total_logged = db.query_one(
        "select count(*) as n from prediction_ledger"
        + (" where model_id = :model_id" if model_id else ""),
        {"model_id": model_id} if model_id else {},
    )
    n = len(rows)
    mean_acc = round(sum(float(r["accuracy_score"]) for r in rows) / n, 4) if n else None
    by_band: dict[str, dict[str, float]] = {}
    for r in rows:
        band = str(r["confidence_band"] or "unset")
        b = by_band.setdefault(band, {"n": 0, "sum": 0.0})
        b["n"] += 1
        b["sum"] += float(r["accuracy_score"])
    band_accuracy = {
        band: {"n": int(v["n"]), "accuracy": round(v["sum"] / v["n"], 4)}
        for band, v in by_band.items()
    }
    return {
        "model_id": model_id,
        "prediction_kind": prediction_kind,
        "total_logged": int(total_logged["n"]) if total_logged else 0,
        "resolved": n,
        "mean_accuracy": mean_acc,
        "band_accuracy": band_accuracy,
    }


# --------------------------------------------------------------------------- #
# Live instrumented surface #1: fanbase archetype assignments.
# --------------------------------------------------------------------------- #
def record_archetype_predictions(
    db: Database, season: int, *, fbs_slugs: Optional[frozenset[str]] = None
) -> dict[str, Any]:
    """Instrument the fanbase classifier as a prediction surface.

    Each team's archetype for `season` is a standing prediction (we expect the
    prior season's archetype to persist), logged with the classifier's confidence.
    It resolves once `season`'s own classification exists (see the resolver). Reads
    the season-(season-1) classification as the predicted value; real-FBS only.

    teams.level_code is unreliable (~55 NAIA/DII schools mislabeled 'FBS'), so the
    authoritative gate is the profiles/ allowlist — same gate as the arc populator.
    Pass an explicit empty frozenset to disable the gate (tests). Returns
    {recorded, season, source_season}.
    """
    if fbs_slugs is None:
        from cfb_rankings.chronicle.arc_populator import _real_fbs_slugs
        fbs_slugs = _real_fbs_slugs()
    source_season = season - 1
    rows = db.query_all(
        """
        select t.slug as slug, fc.primary_archetype_slug as archetype,
               fc.primary_confidence as conf, fc.classifier_version as ver
        from fanbase_classification fc
        join teams t on t.team_id = fc.team_id and t.level_code = 'FBS'
        where fc.season_year = :src
        """,
        {"src": source_season},
    )
    if fbs_slugs:
        rows = [r for r in rows if str(r["slug"]) in fbs_slugs]
    expires = f"{season + 1}-02-01 00:00:00"  # next signing day window; season is graded by then
    recorded = 0
    for r in rows:
        record_prediction(
            db,
            model_id="fanbase-classifier",
            model_version=str(r["ver"] or "v1.0"),
            entity_type="team",
            entity_id=str(r["slug"]),
            prediction_kind="archetype_assignment",
            period_key=str(season),
            predicted_value=str(r["archetype"]),
            confidence_value=float(r["conf"]) if r["conf"] is not None else None,
            evidence_ref=f"fanbase_classification:{source_season}",
            expires_at=expires,
        )
        recorded += 1
    return {"recorded": recorded, "season": season, "source_season": source_season}
