"""Preview readiness audit.

Spec: docs/specs/team-preview-implementation-plan-2026-05-26.md §0, §2.

Counts, per team, what is missing vs. present-but-low-confidence. The cardinal
distinction (spec §0 acceptance): "missing data" is NOT the same as "data
present but low confidence", and the audit must not treat
``teams.level_code='FBS'`` as authoritative — it uses the canonical profiles/
slug set instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cfb_rankings.team_preview.bowl_ledger import resolve_bowl_record_display
from cfb_rankings.team_preview.evidence import (
    build_norm_context,
    build_team_evidence,
    canonical_fbs_slugs_for_db,
)
from cfb_rankings.team_preview.schedule import resolve_schedule_status

# Lower rank == more trustworthy. Used to pick the best ledger row per slug
# when a team has more than one source (mirrors the all-time-trust precedence
# in bowl_ledger.resolve_bowl_record_display).
_LEDGER_TRUST = {"verified": 0, "single_source": 1, "conflict": 2, "missing": 3}


def _ledger_trust_rank(status: str | None) -> int:
    return _LEDGER_TRUST.get(status or "", 9)


def best_ledger_rows(rows: Any) -> dict[str, dict[str, Any]]:
    """Collapse multi-source ledger rows to one best row per slug.

    A slug may carry several source rows (unique key is slug+source_name). Keep
    the most trustworthy one so a later 'conflict'/'missing' row never shadows a
    'verified' one for the same team.
    """
    best: dict[str, dict[str, Any]] = {}
    for r in rows:
        cur = best.get(r["slug"])
        if cur is None or _ledger_trust_rank(r["verification_status"]) < \
                _ledger_trust_rank(cur["verification_status"]):
            best[r["slug"]] = r
    return best


@dataclass
class TeamReadiness:
    slug: str
    team_id: int | None
    found: bool
    schedule_known: bool = False
    has_prior_record: bool = False
    has_all_time_bowl: bool = False
    has_transfer_snapshot: bool = False
    has_returning_production: bool = False
    confidence_band: str = "unset"
    low_confidence: bool = False
    missing_sources: list[str] = field(default_factory=list)


@dataclass
class ReadinessReport:
    season_year: int
    as_of_date: str
    teams: list[TeamReadiness] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        n = len(self.teams)
        present = [t for t in self.teams if t.found]
        return {
            "teams_audited": n,
            "teams_found": len(present),
            "teams_not_found": n - len(present),
            "missing_schedule": sum(1 for t in present if not t.schedule_known),
            "missing_prior_record": sum(1 for t in present if not t.has_prior_record),
            "missing_all_time_bowl": sum(1 for t in present if not t.has_all_time_bowl),
            "missing_transfer_snapshot": sum(1 for t in present if not t.has_transfer_snapshot),
            "missing_returning_production": sum(1 for t in present if not t.has_returning_production),
            "low_confidence": sum(1 for t in present if t.low_confidence),
        }


def audit_team_preview_readiness(
    db: Any, season_year: int, as_of_date: str, slugs: list[str] | None = None,
) -> ReadinessReport:
    if slugs is None:
        slugs = canonical_fbs_slugs_for_db(db)
    norm = build_norm_context(db, season_year)

    # Pre-load which slugs have an all-time bowl ledger row, keeping the most
    # trustworthy source per slug.
    ledger = best_ledger_rows(db.query_all(
        "select slug, wins, losses, ties, verification_status, source_name "
        "from team_bowl_record_ledger"
    ))

    report = ReadinessReport(season_year=season_year, as_of_date=as_of_date)
    for slug in slugs:
        ev = build_team_evidence(db, slug, season_year, as_of_date, norm)
        if ev is None:
            report.teams.append(TeamReadiness(slug=slug, team_id=None, found=False))
            continue
        sched = resolve_schedule_status(db, ev.team_id, season_year)
        bowl = resolve_bowl_record_display(ledger.get(slug))
        tr = TeamReadiness(
            slug=slug,
            team_id=ev.team_id,
            found=True,
            schedule_known=sched.schedule_known,
            has_prior_record=ev.prior_wins is not None,
            has_all_time_bowl=bowl.is_all_time,
            has_transfer_snapshot=(ev.transfer_in_count + ev.transfer_out_count) > 0,
            has_returning_production=ev.returning_total is not None,
            confidence_band=ev.confidence_band,
            low_confidence=ev.confidence_band in ("low", "unset"),
            missing_sources=list(ev.missing_sources),
        )
        report.teams.append(tr)
    return report
