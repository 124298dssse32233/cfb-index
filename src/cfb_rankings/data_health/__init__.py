"""Data Health Spine (Wave 0).

One authoritative "is my data filled, healthy, and processed when I want?"
capability. Read-only against the canonical ``cfb_rankings.db``; stdlib + raw
``sqlite3`` only (no new deps); reuses existing primitives where the build
blueprint says to.

Module map (see ``docs/octopus/wave0_data_health_build_blueprint.md``):
  * ``calendar``  — verified CFB per-year regimes + the real-FBS-conference
    entity universe (hard-coded history) + ``fbs_team_ids(conn, season)``.
  * ``contracts`` — declarative ``DatasetContract`` objects (one per dataset),
    each carrying its OWN ``expected_seasons`` set.
  * ``checks``    — the 5 observability pillars. Each pillar module exposes
    ``run(conn) -> list[CheckResult]``; ``checks.run_all`` fans across
    ``checks.PILLARS``.
  * ``gate``      — pillar ``CheckResult`` rows -> one RED/YELLOW/GREEN/UNKNOWN
    gate (a covid/in-progress/known-missing season at its OWN expectation is
    never a fail; UNKNOWN never collapses to GREEN).
  * ``report``    — ``to_json`` + ``render_console`` for the gate + results.

The shared interface lives in ``checks.base`` (``CheckResult`` + ``Pillar``);
every downstream pillar conforms to it exactly.
"""
from __future__ import annotations

__all__ = ["calendar", "contracts", "checks", "gate", "report", "snapshots", "alerting"]
