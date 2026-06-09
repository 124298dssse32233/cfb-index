"""Roster Reload dashboard for the forward-looking team page.

Consumes Milestone C truth-layer rows:
  * team_roster_reload_snapshot
  * team_transfer_position_snapshot

The hard product rule is visible in the markup: portal additions and portal
losses render as separate measures, not a single net number.
"""
from __future__ import annotations

import json
from html import escape
from typing import Any

from .data import TeamSnapshot
from .profile_loader import Profile


ROSTER_RELOAD_CSS = """
/* Roster Reload dashboard */
.roster-reload {
  margin-bottom: clamp(20px, 3vw, 32px);
  padding: clamp(16px, 2.2vw, 24px) clamp(18px, 2.4vw, 28px);
  background: rgba(255, 255, 255, 0.026);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, #c9a24a);
  border-radius: 8px;
  font-variant-numeric: tabular-nums;
}
.roster-reload__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-bottom: clamp(12px, 1.6vw, 18px);
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 10px;
}
.roster-reload__title {
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(20px, 1.2vw + 10px, 26px);
  font-weight: 400;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--fg-primary);
  margin: 0;
}
.roster-reload__tag {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fg-muted);
  white-space: nowrap;
}
.roster-reload__grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: clamp(8px, 1.2vw, 12px);
}
.roster-reload__metric {
  min-height: 102px;
  padding: 10px 12px;
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.06));
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.02);
  overflow-wrap: anywhere;
}
.roster-reload__metric-label {
  display: block;
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin-bottom: 7px;
}
.roster-reload__metric-value {
  display: block;
  font-family: var(--font-display, 'Bebas Neue', system-ui, sans-serif);
  font-size: clamp(24px, 1.8vw + 8px, 36px);
  line-height: 1;
  color: var(--fg-primary);
}
.roster-reload__metric-value--add { color: #4f9d6b; }
.roster-reload__metric-value--loss { color: #c98c1a; }
.roster-reload__metric-note {
  display: block;
  margin-top: 6px;
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 12px;
  line-height: 1.35;
  color: var(--fg-secondary);
}
.roster-reload__positions {
  margin-top: clamp(12px, 1.8vw, 18px);
  display: grid;
  gap: 8px;
}
.roster-reload__position {
  display: grid;
  grid-template-columns: minmax(48px, 0.4fr) repeat(2, minmax(0, 1fr)) minmax(0, 1.1fr);
  gap: 10px;
  align-items: center;
  padding: 9px 10px;
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.06));
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.018);
}
.roster-reload__pos {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 12px;
  font-weight: 800;
  color: var(--fg-primary);
}
.roster-reload__flow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 12px;
  color: var(--fg-secondary);
}
.roster-reload__flow strong {
  color: var(--fg-primary);
  font-weight: 800;
}
.roster-reload__flag {
  justify-self: end;
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.11em;
  text-transform: uppercase;
  color: var(--accent-primary, #c9a24a);
}
.roster-reload__flag--up { color: #4f9d6b; }
.roster-reload__flag--down { color: #c98c1a; }
.roster-reload__flag--even { color: var(--fg-muted); }
.roster-reload__rating {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 10px;
  font-weight: 700;
  color: var(--fg-muted);
  margin-left: 2px;
}
@media (max-width: 900px) {
  .roster-reload__grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .roster-reload__position { grid-template-columns: minmax(42px, 0.35fr) minmax(0, 1fr); }
  .roster-reload__flag { justify-self: start; }
}
@media (max-width: 480px) {
  .roster-reload__head { flex-direction: column; align-items: flex-start; }
  .roster-reload__grid { grid-template-columns: 1fr; }
  .roster-reload__metric { min-height: 0; }
  .roster-reload__position {
    grid-template-columns: minmax(38px, auto) minmax(0, 1fr);
    gap: 8px;
  }
  .roster-reload__flow { font-size: 11px; }
}
"""


def render_roster_reload(
    profile: Profile,
    snapshot: TeamSnapshot | None,
    reload_row: dict[str, Any] | None,
    position_rows: list[dict[str, Any]] | None,
) -> str:
    if snapshot is None or not reload_row:
        return ""

    summary = _summary(reload_row)
    metrics = [
        _metric(
            "Returning Production",
            _pct(reload_row.get("continuity_score")),
            reload_row.get("returning_profile_label") or "Continuity signal unavailable",
            "",
        ),
        _metric(
            "Portal Additions",
            str(int(summary.get("transfer_in_total") or 0)),
            _portal_note(reload_row.get("primary_repair_position"), "repair"),
            "add",
        ),
        _metric(
            "Portal Losses",
            str(int(summary.get("transfer_out_total") or 0)),
            _portal_note(reload_row.get("primary_pressure_position"), "pressure"),
            "loss",
        ),
        _metric(
            "Draft Loss",
            str(int(summary.get("drafted_count") or 0)),
            reload_row.get("draft_loss_label") or "No NFL Draft departures recorded",
            "loss" if int(summary.get("drafted_count") or 0) else "",
        ),
        _metric(
            "Recruiting Reload",
            _recruiting_value(summary, reload_row),
            reload_row.get("recruiting_reload_label") or "Recruiting class signal unavailable",
            "",
        ),
    ]

    positions_html = "".join(_position_row(r) for r in (position_rows or [])[:6])
    if not positions_html:
        positions_html = (
            '<div class="roster-reload__position">'
            '<span class="roster-reload__pos">Portal</span>'
            '<span class="roster-reload__flow">No position split available.</span>'
            '<span class="roster-reload__flow">Run roster reload snapshots for position flow.</span>'
            '<span class="roster-reload__flag">Awaiting</span>'
            '</div>'
        )

    season = int(reload_row.get("season_year") or snapshot.season_year)
    as_of = reload_row.get("as_of_date") or ""
    program = escape(profile.program_name)
    return f"""
<section class="roster-reload" aria-labelledby="roster-reload-h"
         data-module="roster-reload" data-state="ready" data-season="{season}">
  <div class="roster-reload__head">
    <h2 class="roster-reload__title" id="roster-reload-h">Roster Reload - {program}</h2>
    <span class="roster-reload__tag">{season} snapshot{(' - ' + escape(str(as_of))) if as_of else ''}</span>
  </div>
  <div class="roster-reload__grid">
    {''.join(metrics)}
  </div>
  <div class="roster-reload__positions" aria-label="Portal position flow">
    {positions_html}
  </div>
</section>"""


def _summary(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("summary_json")
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _metric(label: str, value: str, note: str, tone: str) -> str:
    tone_cls = f" roster-reload__metric-value--{tone}" if tone else ""
    return (
        '<div class="roster-reload__metric">'
        f'<span class="roster-reload__metric-label">{escape(label)}</span>'
        f'<span class="roster-reload__metric-value{tone_cls}">{escape(value)}</span>'
        f'<span class="roster-reload__metric-note">{escape(note)}</span>'
        '</div>'
    )


def _pct(value: Any) -> str:
    if value is None:
        return "NA"
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return "NA"


def _portal_note(position: Any, fallback: str) -> str:
    if not position:
        return "No clear position " + fallback + " point"
    label = "repair" if fallback == "repair" else "pressure"
    return f"Primary {label}: {position}"


def _recruiting_value(summary: dict[str, Any], row: dict[str, Any]) -> str:
    rank = summary.get("recruiting_rank")
    if rank is not None:
        try:
            return f"#{int(rank)}"
        except (TypeError, ValueError):
            pass
    score = row.get("freshman_injection_score")
    if score is not None:
        return _pct(score)
    return "NA"


def _rating(value: Any) -> str:
    """Format a composite player rating (~0.80-1.00) as a compact ``.NN`` stamp."""
    try:
        r = float(value)
    except (TypeError, ValueError):
        return ""
    if r <= 0:
        return ""
    return f'<span class="roster-reload__rating">{r:.2f}</span>'


def _quality_verdict(row: dict[str, Any]) -> tuple[str, str]:
    """Return (label, tone) answering 'better or worse here?' by talent, not headcount.

    Upstream starter-risk / need-filled flags win when set (they fold in
    production weighting); otherwise fall back to the net rating-points swing.
    """
    if int(row.get("starter_risk_flag") or 0):
        return "Starter Risk", "down"
    if int(row.get("need_filled_flag") or 0):
        return "Need Filled", "up"
    try:
        net = float(row.get("net_points") or 0)
    except (TypeError, ValueError):
        net = 0.0
    if net >= 0.5:
        return "Upgrade", "up"
    if net <= -0.5:
        return "Downgrade", "down"
    if int(row.get("incoming_count") or 0) or int(row.get("outgoing_count") or 0):
        return "Even", "even"
    return "", ""


def _position_row(row: dict[str, Any]) -> str:
    pos = row.get("position") or "UNK"
    incoming = int(row.get("incoming_count") or 0)
    outgoing = int(row.get("outgoing_count") or 0)
    incoming_top = row.get("incoming_top_player_name")
    outgoing_top = row.get("outgoing_top_player_name")
    label, tone = _quality_verdict(row)
    tone_cls = f" roster-reload__flag--{tone}" if tone else ""
    incoming_note = f"in <strong>{incoming}</strong>"
    if incoming_top:
        incoming_note += f" - {escape(str(incoming_top))}{_rating(row.get('incoming_top_player_rating'))}"
    outgoing_note = f"out <strong>{outgoing}</strong>"
    if outgoing_top:
        outgoing_note += f" - {escape(str(outgoing_top))}{_rating(row.get('outgoing_top_player_rating'))}"
    return (
        '<div class="roster-reload__position">'
        f'<span class="roster-reload__pos">{escape(str(pos))}</span>'
        f'<span class="roster-reload__flow">{incoming_note}</span>'
        f'<span class="roster-reload__flow">{outgoing_note}</span>'
        f'<span class="roster-reload__flag{tone_cls}">{escape(label)}</span>'
        '</div>'
    )


__all__ = ["render_roster_reload", "ROSTER_RELOAD_CSS"]
