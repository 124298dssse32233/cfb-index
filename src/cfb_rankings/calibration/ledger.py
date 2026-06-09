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


def _resolve_season_wins(
    db: Database, row: dict[str, Any]
) -> tuple[Optional[str], Optional[float], str]:
    """Grade a season_wins prediction for season=period_key against actual completed
    regular-season wins from games. Graded score: 1 - |pred-actual|/4 (clamped 0..1),
    so a dead-on call scores 1.0 and a miss of 4+ wins scores 0.0. Returns None actual
    if no completed regular-season game exists for the team (season not played/ingested)."""
    try:
        season = int(row["period_key"])
        predicted = float(row["predicted_value"])
    except (TypeError, ValueError):
        return None, None, "non-numeric period_key or predicted_value"
    tid = db.query_one("select team_id from teams where slug = :slug", {"slug": row["entity_id"]})
    if not tid:
        return None, None, "team slug not found"
    team_id = tid["team_id"]
    played = db.query_one(
        """
        select count(*) as n from games
        where season_year = :season and season_type = 'regular' and home_points is not null
          and (home_team_id = :tid or away_team_id = :tid)
        """,
        {"season": season, "tid": team_id},
    )
    if not played or int(played["n"]) == 0:
        return None, None, "regular season not yet played"
    wins = db.query_one(
        """
        select count(*) as n from games
        where season_year = :season and season_type = 'regular' and home_points is not null
          and ((home_team_id = :tid and home_points > away_points)
               or (away_team_id = :tid and away_points > home_points))
        """,
        {"season": season, "tid": team_id},
    )
    actual = int(wins["n"]) if wins else 0
    score = max(0.0, 1.0 - abs(predicted - actual) / 4.0)
    return str(actual), round(score, 4), f"predicted {int(predicted)}, actual {actual}"


def _resolve_game_pick(
    db: Database, row: dict[str, Any]
) -> tuple[Optional[str], Optional[float], str]:
    """Grade a game_pick. ``entity_id`` is the game_id; ``predicted_value`` is the
    picked winner's team slug. Scores 1.0 for the right side, 0.0 for the wrong side,
    0.5 for a tie (equal final points). Returns None until the game is final, so an
    unplayed/unscored game stays unresolved for a later pass."""
    try:
        game_id = int(row["entity_id"])
    except (TypeError, ValueError):
        return None, None, "non-numeric game_id"
    game = db.query_one(
        """
        select home_team_id, away_team_id, home_points, away_points
          from games where game_id = :gid
        """,
        {"gid": game_id},
    )
    if not game:
        return None, None, "game not found"
    if game.get("home_points") is None or game.get("away_points") is None:
        return None, None, "game not yet final"
    hp, ap = int(game["home_points"]), int(game["away_points"])
    if hp == ap:
        return "tie", 0.5, "tie — no winner"
    winner_id = game["home_team_id"] if hp > ap else game["away_team_id"]
    win = db.query_one("select slug from teams where team_id = :tid", {"tid": winner_id})
    winner_slug = str(win["slug"]) if win and win.get("slug") else str(winner_id)
    score = 1.0 if str(row["predicted_value"]) == winner_slug else 0.0
    return winner_slug, score, "called it" if score else "wrong side"


def _resolve_award_winner(
    db: Database, row: dict[str, Any]
) -> tuple[Optional[str], Optional[float], str]:
    """Grade an award_winner. ``entity_id`` is the award key, ``predicted_value`` is
    the predicted winner's player_id, ``period_key`` is the season. ``heisman`` grades
    against ``heisman_vote_results.winner_flag``; any other award against
    ``player_honors`` (placement=1) matched on ``honor_name``. 1.0 if the pick won,
    else 0.0. Returns None until a winner is recorded for that season."""
    try:
        season = int(row["period_key"])
    except (TypeError, ValueError):
        return None, None, "non-numeric period_key"
    award = str(row["entity_id"] or "").strip().lower()
    if award == "heisman":
        win = db.query_one(
            """
            select player_id from heisman_vote_results
             where season_year = :s and winner_flag = 1 limit 1
            """,
            {"s": season},
        )
    else:
        win = db.query_one(
            """
            select player_id from player_honors
             where season_year = :s and lower(honor_name) = :a and placement = 1
             limit 1
            """,
            {"s": season, "a": award},
        )
    if not win or win.get("player_id") is None:
        return None, None, "winner not yet recorded"
    actual = str(win["player_id"])
    score = 1.0 if str(row["predicted_value"]) == actual else 0.0
    return actual, score, "called the winner" if score else "missed"


OUTCOME_RESOLVERS: dict[str, Resolver] = {
    "archetype_assignment": _resolve_archetype_assignment,
    "season_wins": _resolve_season_wins,
    "game_pick": _resolve_game_pick,
    "award_winner": _resolve_award_winner,
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


# --------------------------------------------------------------------------- #
# Live instrumented surface #2: preseason season-win projections.
# --------------------------------------------------------------------------- #
def record_season_win_predictions(
    db: Database, season: int, *, fbs_slugs: Optional[frozenset[str]] = None
) -> dict[str, Any]:
    """Lock the preseason regular-season-win projection (the 'base' scenario) into the
    ledger so it can be graded after the season. This MUST run preseason — a calibration
    ledger is only honest if the prediction is recorded before the outcome is known.

    Reads team_season_path_projection (scenario='base') for `season`; carries the
    projection's own confidence_band and model_version. Real-FBS allowlist-gated.
    Resolves after expiry (mid-January) against actual completed regular-season wins.
    Returns {recorded, season}.
    """
    if fbs_slugs is None:
        from cfb_rankings.chronicle.arc_populator import _real_fbs_slugs
        fbs_slugs = _real_fbs_slugs()
    # The projection table keeps multiple as_of snapshots per team; take only the
    # latest snapshot of the base scenario so the locked prediction is the current one.
    rows = db.query_all(
        """
        select p.slug, p.regular_season_wins as wins, p.confidence_band as band,
               p.model_version as ver, p.as_of_date
        from team_season_path_projection p
        where p.season_year = :season and p.scenario = 'base'
          and p.as_of_date = (
              select max(p2.as_of_date) from team_season_path_projection p2
              where p2.team_id = p.team_id and p2.season_year = :season and p2.scenario = 'base'
          )
        """,
        {"season": season},
    )
    if fbs_slugs:
        rows = [r for r in rows if str(r["slug"]) in fbs_slugs]
    expires = f"{season + 1}-01-15 00:00:00"  # after the regular season + conf-title weekend
    recorded = 0
    for r in rows:
        record_prediction(
            db,
            model_id="season-path",
            model_version=str(r["ver"] or "season_path_v1"),
            entity_type="team",
            entity_id=str(r["slug"]),
            prediction_kind="season_wins",
            period_key=str(season),
            predicted_value=str(int(r["wins"])),
            confidence_band=str(r["band"] or "unset"),
            evidence_ref=f"team_season_path_projection:base:{r['as_of_date']}",
            expires_at=expires,
        )
        recorded += 1
    return {"recorded": recorded, "season": season}
