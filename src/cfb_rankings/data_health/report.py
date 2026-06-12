"""Render the gate + results to deterministic JSON and a console string.

Lead with deterministic JSON + console (the spec's chosen surface for an
infra-beginner owner — a clear report with the failing SQL beats a dashboard).
No persistence here; snapshots land in a later wave.
"""
from __future__ import annotations

from datetime import datetime, timezone


def _result_to_dict(r) -> dict:
    return {
        "check_id": r.check_id,
        "pillar": r.pillar,
        "dataset": r.dataset,
        "season": r.season,
        "status": r.status,
        "severity": r.severity,
        "detail": r.detail,
        "evidence_sql": r.evidence_sql,
    }


def to_json(gate, results) -> dict:
    """Serializable report dict: run header + gate + normalized result rows.

    Stable key order + an ISO-8601 UTC ``generated_utc`` so two runs over the
    same DB diff cleanly (minus the timestamp).
    """
    rows = [_result_to_dict(r) for r in results]
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "overall": gate.get("overall"),
        "summary": gate.get("summary"),
        "passrates": gate.get("passrates", {}),
        "counts": gate.get("counts", {}),
        "results": rows,
    }


def render_console(gate, results) -> str:
    """Human-readable console report (header gate + per-pillar + failing rows)."""
    results = list(results)
    overall = gate.get("overall", "UNKNOWN")
    summary = gate.get("summary", "")
    counts = gate.get("counts", {})
    passrates = gate.get("passrates", {})

    lines: list[str] = []
    lines.append("=" * 64)
    lines.append(f"  DATA HEALTH GATE: {overall}")
    lines.append("=" * 64)
    lines.append(summary)
    lines.append("")

    # Header counts.
    lines.append(
        "counts: "
        f"total={counts.get('total', 0)} "
        f"pass={counts.get('pass', 0)} "
        f"fail={counts.get('fail', 0)} "
        f"unknown={counts.get('unknown', 0)} "
        f"(critical_fail={counts.get('critical_fail', 0)}, "
        f"critical_unknown={counts.get('critical_unknown', 0)})"
    )
    lines.append("")

    # Per-pillar pass-rates.
    if passrates:
        lines.append("pillar pass-rates:")
        for pillar in sorted(passrates):
            pr = passrates[pillar]
            lines.append(f"  {pillar:<28} {pr * 100:5.1f}%")
    else:
        lines.append("pillar pass-rates: (no pillars registered)")
    lines.append("")

    # Failing / unknown rows surfaced with their evidence SQL.
    flagged = [r for r in results if r.status in ("fail", "unknown")]
    if flagged:
        lines.append(f"flagged assertions ({len(flagged)}):")
        for r in flagged:
            season = "" if r.season is None else f" s{r.season}"
            lines.append(
                f"  [{r.status.upper():<7}] [{r.severity:<8}] "
                f"{r.check_id}{season}"
            )
            lines.append(f"            {r.detail}")
            if r.evidence_sql:
                lines.append(f"            sql: {r.evidence_sql}")
    else:
        if results:
            lines.append("no flagged assertions — all evaluated checks passed.")
        else:
            lines.append("no assertions evaluated (scaffold / zero pillars).")

    lines.append("=" * 64)
    return "\n".join(lines)
