"""Prompt and evidence-packet builders for team-preview claim synthesis."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field


PROMPT_TEMPLATE_ID = "team_preview_claim_v1"


class SupportingClaim(BaseModel):
    kind: Literal[
        "record_projection",
        "roster_reload",
        "portal",
        "draft",
        "schedule",
        "bowl",
        "fan_intel",
        "recruiting",
    ]
    text: str = Field(min_length=1, max_length=240)
    evidence_key: str = Field(min_length=1, max_length=120)
    numeric_values: list[float] = Field(default_factory=list, max_length=8)


class PreviewClaimCandidate(BaseModel):
    headline: str = Field(min_length=1, max_length=96)
    body: str = Field(min_length=1, max_length=520)
    supporting_claims: list[SupportingClaim] = Field(min_length=1, max_length=6)
    confidence_band: Literal["high", "medium", "low", "unset"] = "unset"
    fallback_reason: str | None = Field(default=None, max_length=240)


def build_preview_evidence(
    db: Any,
    slug: str,
    season_year: int,
    as_of_date: str,
) -> dict[str, Any] | None:
    team = db.query_one(
        "select team_id, slug, canonical_name from teams where slug = :slug",
        {"slug": slug},
    )
    if not team:
        return None
    team_id = int(team["team_id"])
    snapshot = _latest_row(
        db,
        """
        select team_id, slug, season_year, as_of_date, prior_season_year,
               prior_wins, prior_losses, schedule_known,
               first_game_start_utc, first_game_opponent_name,
               recruiting_rank, recruiting_score,
               returning_total, transfer_in_count, transfer_out_count,
               drafted_count, confidence_band, missing_sources_json
        from team_preview_snapshot
        where team_id = :team_id and season_year = :season and as_of_date <= :as_of
        order by as_of_date desc
        limit 1
        """,
        {"team_id": team_id, "season": season_year, "as_of": as_of_date},
    )
    if not snapshot:
        return None

    path_rows = db.query_all(
        """
        select scenario, final_wins, final_losses, final_ties, path_label,
               bowl_or_cfp_path, confidence_band
        from team_season_path_projection
        where team_id = :team_id and season_year = :season
          and as_of_date = :as_of
        order by case scenario when 'floor' then 1 when 'base' then 2 when 'ceiling' then 3 else 4 end
        """,
        {"team_id": team_id, "season": season_year, "as_of": snapshot["as_of_date"]},
    )
    reload_row = _latest_row(
        db,
        """
        select team_id, slug, season_year, as_of_date, returning_profile_label,
               transfer_profile_label, draft_loss_label, recruiting_reload_label,
               primary_pressure_position, primary_repair_position,
               reload_score, continuity_score, volatility_score,
               portal_addition_score, portal_loss_score, draft_loss_score,
               freshman_injection_score, summary_json, confidence_band
        from team_roster_reload_snapshot
        where team_id = :team_id and season_year = :season and as_of_date = :as_of
        limit 1
        """,
        {"team_id": team_id, "season": season_year, "as_of": snapshot["as_of_date"]},
    )
    positions = db.query_all(
        """
        select position, incoming_count, outgoing_count, net_count,
               incoming_top_player_name, outgoing_top_player_name,
               starter_risk_flag, need_filled_flag
        from team_transfer_position_snapshot
        where team_id = :team_id and season_year = :season and as_of_date = :as_of
        order by (coalesce(incoming_count, 0) + coalesce(outgoing_count, 0)) desc,
                 abs(coalesce(net_count, 0)) desc,
                 position asc
        limit 6
        """,
        {"team_id": team_id, "season": season_year, "as_of": snapshot["as_of_date"]},
    )
    bowl = _latest_row(
        db,
        """
        select wins, losses, ties, appearances, last_bowl_year, last_bowl_name,
               verification_status
        from team_bowl_record_ledger
        where slug = :slug
        order by case verification_status
          when 'verified' then 1 when 'single_source' then 2
          when 'conflict' then 3 else 4 end
        limit 1
        """,
        {"slug": slug},
    )
    fan_intel = _fan_intel_readiness(db, team_id)
    missing_sources = []
    try:
        missing_sources = json.loads(snapshot.get("missing_sources_json") or "[]")
    except (TypeError, json.JSONDecodeError):
        missing_sources = []
    reload_summary = {}
    if reload_row and reload_row.get("summary_json"):
        try:
            reload_summary = json.loads(reload_row["summary_json"])
        except (TypeError, json.JSONDecodeError):
            reload_summary = {}

    roster_reload = dict(reload_row) if reload_row else None
    if roster_reload is not None:
        roster_reload.update({
            "transfer_in_count": reload_summary.get("transfer_in_total"),
            "transfer_out_count": reload_summary.get("transfer_out_total"),
            "transfer_in_total": reload_summary.get("transfer_in_total"),
            "transfer_out_total": reload_summary.get("transfer_out_total"),
            "drafted_count": reload_summary.get("drafted_count"),
            "returning_total_pct": _pct(reload_summary.get("returning_total")),
            "recruiting_rank": reload_summary.get("recruiting_rank"),
            "recruiting_score": reload_summary.get("recruiting_score"),
        })

    evidence = {
        "team": {
            "team_id": team_id,
            "slug": slug,
            "name": team["canonical_name"],
            "season_year": season_year,
            "as_of_date": snapshot["as_of_date"],
        },
        "snapshot": {
            "prior_season_year": snapshot.get("prior_season_year"),
            "prior_wins": snapshot.get("prior_wins"),
            "prior_losses": snapshot.get("prior_losses"),
            "schedule_known": bool(snapshot.get("schedule_known")),
            "first_game_start_utc": snapshot.get("first_game_start_utc"),
            "first_game_opponent_name": snapshot.get("first_game_opponent_name"),
            "recruiting_rank": snapshot.get("recruiting_rank"),
            "recruiting_score": snapshot.get("recruiting_score"),
            "returning_total_pct": _pct(snapshot.get("returning_total")),
            "transfer_in_count": snapshot.get("transfer_in_count"),
            "transfer_out_count": snapshot.get("transfer_out_count"),
            "drafted_count": snapshot.get("drafted_count"),
            "confidence_band": snapshot.get("confidence_band") or "unset",
            "missing_sources": missing_sources,
        },
        "season_path": {r["scenario"]: dict(r) for r in path_rows},
        "roster_reload": roster_reload,
        "roster_reload_summary": reload_summary,
        "transfer_positions": [dict(r) for r in positions],
        "bowl_ledger": dict(bowl) if bowl else None,
        "fan_intel": fan_intel,
    }
    evidence["evidence_hash"] = evidence_hash(evidence)
    return evidence


def build_preview_claim_prompt(evidence: dict[str, Any]) -> str:
    packet = json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2, default=str)
    return f"""You are drafting ONE candidate 2026 college-football team preview thesis.

Output JSON only, matching the supplied schema.

Hard rules:
- Use only facts present in <evidence>.
- Every numeric value in headline, body, and supporting_claims must appear in <evidence>.
- Every numeric value in headline, body, and supporting_claims.text must also appear in supporting_claims.numeric_values.
- Every supporting_claim.evidence_key must be one single dotted path inside <evidence>; do not comma-join paths.
- Do not make fan-intel, fanbase, boards, Reddit, mood, or belief claims unless evidence.fan_intel.ready is true.
- Do not claim all-time bowl scope unless evidence.bowl_ledger.verification_status supports it.
- If evidence is thin, write a narrower thesis instead of filling gaps.
- Keep body to 2 concise sentences.
- Use ASCII characters only.
- Headline must not end with a conjunction or preposition.
- Body must start with an uppercase letter and read as standalone prose.
- Use exact ranks like #3; do not write approximate phrases like top-10.

<evidence>
{packet}
</evidence>
"""


def evidence_hash(evidence: dict[str, Any]) -> str:
    clean = {k: v for k, v in evidence.items() if k != "evidence_hash"}
    blob = json.dumps(clean, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _latest_row(db: Any, sql: str, params: dict[str, Any]) -> dict[str, Any] | None:
    try:
        row = db.query_one(sql, params)
    except Exception:
        return None
    return dict(row) if row else None


def _fan_intel_readiness(db: Any, team_id: int) -> dict[str, Any]:
    try:
        row = db.query_one(
            """
            select sum(effective_n) as effective_n, max(week) as latest_week,
                   count(*) as cohort_rows
            from team_cohort_week
            where team_id = :team_id
              and week = (
                select max(week) from team_cohort_week where team_id = :team_id
              )
            """,
            {"team_id": team_id},
        )
    except Exception:
        row = None
    effective_n = float((row or {}).get("effective_n") or 0.0)
    return {
        "ready": effective_n >= 100.0,
        "effective_n": effective_n,
        "latest_week": (row or {}).get("latest_week"),
        "cohort_rows": int((row or {}).get("cohort_rows") or 0),
        "readiness_label": "ready" if effective_n >= 100.0 else (
            "sample_growing" if effective_n >= 20.0 else "awaiting_signal"
        ),
    }


def _pct(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(round(float(value) * 100))
    except (TypeError, ValueError):
        return None
