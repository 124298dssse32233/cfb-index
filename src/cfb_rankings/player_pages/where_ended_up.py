"""Where They Ended Up — Wave 25 / Module 3.

For Type B (NFL departures) and Type C (CFB transfers), shows the
destination + role projection. Sits in the page slot where Module 2
(2026 Outlook) would render for Type A players.

Two render variants:
  5A. NFL destination — pick chip, team name, draft-year-aware subtitle
      (e.g. "2026 rookie season" vs "Entering 2nd NFL season")
  5B. CFB transfer destination — from→to flow, role projection

Public API:
    render_where_ended_up(db, player_id) -> str
    WHERE_ENDED_UP_CSS                   -> str
"""
from __future__ import annotations

from datetime import date
from html import escape
from typing import Any


WHERE_ENDED_UP_CSS = """
/* Where They Ended Up — Wave 25 / Module 3 */
.where-ended-up {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accolade-gold-base, #d1a23a);
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.where-ended-up--nfl       { border-left-color: oklch(0.50 0.18 260); }
.where-ended-up--transfer  { border-left-color: oklch(0.65 0.18 75); }

.where-ended-up__head {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 12px; margin-bottom: 10px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
}
.where-ended-up__eyebrow {
  font-size: 0.72rem; letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55)); margin: 0;
}
.where-ended-up__title {
  font-size: 1.15rem; font-weight: 700; margin: 0;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.where-ended-up__title small {
  display: block;
  font-size: 0.74rem;
  font-weight: 500;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  margin-top: 2px;
  letter-spacing: 0.02em;
}

/* Variant 5A — NFL destination */
.where-ended-up__pick {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 14px;
  align-items: center;
  margin: 12px 0;
}
.where-ended-up__pick-chip {
  display: inline-flex; flex-direction: column;
  background: oklch(0.18 0.10 260);
  color: #f4f4f5;
  padding: 10px 14px;
  border-radius: 8px;
  text-align: center;
  min-width: 84px;
}
.where-ended-up__pick-chip--first-overall {
  background: var(--accolade-gold-base, #d1a23a);
  color: #15161a;
  box-shadow: 0 0 14px rgba(209, 162, 58, 0.35);
}
.where-ended-up__pick-overall {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.7rem; line-height: 1;
  font-weight: 700;
}
.where-ended-up__pick-round {
  font-size: 0.68rem; letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-top: 2px;
  opacity: 0.85;
}
.where-ended-up__destination {
  display: flex; flex-direction: column; gap: 2px;
}
.where-ended-up__destination-name {
  font-size: 1.1rem; font-weight: 600;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.where-ended-up__destination-sub {
  font-size: 0.78rem;
  color: var(--text-quiet, rgba(255,255,255,0.62));
}

/* Variant 5B — transfer flow */
.where-ended-up__flow {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 14px;
  align-items: center;
  margin: 14px 0;
}
.where-ended-up__from,
.where-ended-up__to {
  display: flex; flex-direction: column; gap: 2px;
  padding: 8px 12px;
  background: rgba(255,255,255,0.020);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
}
.where-ended-up__from { text-align: right; }
.where-ended-up__team-label {
  font-size: 0.62rem; letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.45));
}
.where-ended-up__team-name {
  font-size: 1.0rem; font-weight: 600;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.where-ended-up__arrow {
  font-size: 1.4rem;
  color: var(--accolade-gold-base, #d1a23a);
  font-weight: 700;
}

/* Role projection block (both variants) */
.where-ended-up__projection {
  margin-top: 12px;
  padding: 10px 12px;
  background: rgba(255,255,255,0.015);
  border-radius: 8px;
}
.where-ended-up__projection-label {
  font-size: 0.66rem; letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55)); margin: 0 0 4px 0;
}
.where-ended-up__projection-text {
  font-size: 0.88rem; line-height: 1.45;
  color: var(--text-soft, rgba(255,255,255,0.82));
  margin: 0;
}

.where-ended-up__legacy {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  font-size: 0.78rem;
}
.where-ended-up__legacy-link {
  color: var(--accolade-gold-base, #d1a23a);
  text-decoration: none;
  font-weight: 500;
}
.where-ended-up__legacy-link:hover { text-decoration: underline; }

@media (max-width: 640px) {
  .where-ended-up__pick {
    grid-template-columns: 1fr;
    gap: 8px;
  }
  .where-ended-up__pick-chip { align-self: start; }
  .where-ended-up__flow {
    grid-template-columns: 1fr;
    gap: 8px;
  }
  .where-ended-up__from { text-align: left; }
  .where-ended-up__arrow { display: none; }
}
"""


def _ordinal(n: int) -> str:
    if 10 <= (n % 100) <= 20:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _resolve_team_name(db, team_id: int | None) -> str | None:
    if db is None or team_id is None:
        return None
    rows = db.query_all(
        "select canonical_name from teams where team_id = :tid",
        {"tid": int(team_id)},
    )
    return rows[0]["canonical_name"] if rows else None


def _years_since_draft(draft_year: int | None, today: date | None = None) -> int:
    """Compute how many seasons removed from draft. 0 = rookie 2026,
    1 = sophomore (drafted 2025), etc."""
    if draft_year is None:
        return 0
    today = today or date.today()
    # NFL season nominally maps to "year drafted = rookie season"
    return max(0, today.year - int(draft_year))


def _nfl_subtitle(draft_year: int | None, today: date | None = None) -> str:
    """Generate the right framing for NFL destination subtitle.

    draft_year=2026 → "2026 NFL rookie season"
    draft_year=2025 → "Entering 2nd NFL season"
    draft_year=2024 → "Entering 3rd NFL season"
    older → "{year} NFL Draft"
    """
    if draft_year is None:
        return "NFL career"
    yrs = _years_since_draft(draft_year, today)
    if yrs == 0:
        return f"{draft_year} NFL rookie season"
    if yrs == 1:
        return "Entering 2nd NFL season"
    return f"Entering {_ordinal(yrs + 1)} NFL season"


def _render_nfl_variant(status_row: dict[str, Any], db) -> str:
    """Variant 5A — NFL destination."""
    nfl_team = status_row.get("nfl_team") or "—"
    draft_year = status_row.get("draft_year")
    rd = status_row.get("draft_round")
    pick = status_row.get("draft_pick")
    overall = status_row.get("draft_overall")
    status_code = status_row.get("status_code")

    chip_cls = ""
    overall_label = "—"
    round_label = "—"
    if overall is not None:
        try:
            overall_int = int(overall)
            overall_label = f"#{overall_int}"
            if overall_int == 1:
                chip_cls = " where-ended-up__pick-chip--first-overall"
                overall_label = "#1"
        except (TypeError, ValueError):
            pass
    if rd is not None and pick is not None:
        round_label = f"Rd {rd} · Pick {pick}"
    elif rd is not None:
        round_label = f"Rd {rd}"

    subtitle = _nfl_subtitle(draft_year)

    if status_code == "NFL_UDFA":
        chip_html = (
            '<div class="where-ended-up__pick-chip">'
            '<span class="where-ended-up__pick-overall">UDFA</span>'
            '<span class="where-ended-up__pick-round">FREE AGENT</span>'
            '</div>'
        )
    else:
        chip_html = (
            f'<div class="where-ended-up__pick-chip{chip_cls}">'
            f'<span class="where-ended-up__pick-overall">{escape(overall_label)}</span>'
            f'<span class="where-ended-up__pick-round">{escape(round_label)}</span>'
            '</div>'
        )

    return (
        '<section class="where-ended-up where-ended-up--nfl" '
        f'data-module="where-ended-up" data-variant="nfl" '
        f'data-status-code="{escape(status_code or "")}">'
        '<header class="where-ended-up__head">'
        '<div>'
        '<p class="where-ended-up__eyebrow">Where He Ended Up &middot; NFL</p>'
        f'<p class="where-ended-up__title">{escape(nfl_team)}'
        f'<small>{escape(subtitle)}</small></p>'
        '</div>'
        '</header>'
        '<div class="where-ended-up__pick">'
        f'{chip_html}'
        '<div class="where-ended-up__destination">'
        f'<span class="where-ended-up__destination-name">{escape(nfl_team)}</span>'
        f'<span class="where-ended-up__destination-sub">{escape(subtitle)}</span>'
        '</div>'
        '</div>'
        '<div class="where-ended-up__legacy">'
        '<a href="#current-season-production" class="where-ended-up__legacy-link">'
        'View college career stats ↓'
        '</a>'
        '</div>'
        '</section>'
    )


def _render_transfer_variant(status_row: dict[str, Any], db) -> str:
    """Variant 5B — CFB transfer destination."""
    from_team = _resolve_team_name(db, status_row.get("previous_team_id"))
    to_team = _resolve_team_name(db, status_row.get("current_team_id"))
    status_code = status_row.get("status_code")

    is_portal_open = status_code == "PORTAL_OPEN"

    if is_portal_open:
        to_block = (
            '<div class="where-ended-up__to">'
            '<span class="where-ended-up__team-label">Destination</span>'
            '<span class="where-ended-up__team-name">TBD</span>'
            '</div>'
        )
        title_text = "In transfer portal"
        eyebrow_text = "In Portal · 2026"
    else:
        to_block = (
            '<div class="where-ended-up__to">'
            '<span class="where-ended-up__team-label">2026</span>'
            f'<span class="where-ended-up__team-name">{escape(to_team or "—")}</span>'
            '</div>'
        )
        title_text = f"Transferred to {to_team or 'new program'}"
        eyebrow_text = "Where He Ended Up · Transfer"

    return (
        '<section class="where-ended-up where-ended-up--transfer" '
        f'data-module="where-ended-up" data-variant="transfer" '
        f'data-status-code="{escape(status_code or "")}">'
        '<header class="where-ended-up__head">'
        '<div>'
        f'<p class="where-ended-up__eyebrow">{escape(eyebrow_text)}</p>'
        f'<p class="where-ended-up__title">{escape(title_text)}</p>'
        '</div>'
        '</header>'
        '<div class="where-ended-up__flow">'
        '<div class="where-ended-up__from">'
        '<span class="where-ended-up__team-label">2025</span>'
        f'<span class="where-ended-up__team-name">{escape(from_team or "—")}</span>'
        '</div>'
        '<span class="where-ended-up__arrow" aria-hidden="true">→</span>'
        f'{to_block}'
        '</div>'
        '<div class="where-ended-up__legacy">'
        f'<a href="#current-season-production" class="where-ended-up__legacy-link">'
        f'View {from_team or "previous"} career stats ↓'
        '</a>'
        '</div>'
        '</section>'
    )


def render_where_ended_up(db, player_id: int | None) -> str:
    """Render NFL or transfer variant based on status_code, or empty."""
    if db is None or player_id is None:
        return ""

    from .status_strip import fetch_status_row
    status_row = fetch_status_row(db, player_id)
    if status_row is None:
        return ""

    status_code = status_row.get("status_code") or ""
    nfl_codes = {"NFL_DRAFTED_2026", "NFL_DRAFTED_PRIOR", "NFL_UDFA"}
    transfer_codes = {"TRANSFERRED_COLLEGE", "PORTAL_OPEN"}

    if status_code in nfl_codes:
        return _render_nfl_variant(status_row, db)
    if status_code in transfer_codes:
        return _render_transfer_variant(status_row, db)

    return ""
