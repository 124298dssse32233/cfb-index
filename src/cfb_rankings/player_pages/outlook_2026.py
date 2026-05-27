"""2026 Outlook — Wave 25 / Module 2 (Type A only).

Forward-looking preview for RETURNING_2026 players. Three cells:
  1. 2026 Depth Chart — projected starter / returning / camp competition
  2. Supporting Cast — OL/skill/OC continuity + draft losses + transfer net
  3. Preseason Award Watch — Heisman, Maxwell, Davey, Doak, Biletnikoff, etc.

Reads from:
  - player_current_status_view (status_code, current_team_id)
  - player_depth_chart_2026 (when seeded)
  - team_preview_snapshot (returning prod, talent rank, transfer net, drafted)
  - team_seasons 2025 + 2026 (OC continuity diff)
  - player_award_watch_2026 (when seeded)

Public API:
    render_outlook_2026(db, player_id) -> str
    OUTLOOK_2026_CSS                    -> str
"""
from __future__ import annotations

from html import escape
from typing import Any


OUTLOOK_2026_CSS = """
/* 2026 Outlook — Wave 25 / Module 2 */
.outlook-2026 {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid oklch(0.60 0.16 150);  /* green = returning */
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.outlook-2026__head {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 12px; margin-bottom: 12px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
}
.outlook-2026__eyebrow {
  font-size: 0.72rem; letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55)); margin: 0;
}
.outlook-2026__title {
  font-size: 1.05rem; font-weight: 600; margin: 0;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.outlook-2026__updated {
  font-size: 0.66rem; letter-spacing: 0.06em;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  background: rgba(255,255,255,0.04);
  padding: 2px 8px; border-radius: 99px;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.outlook-2026__lede {
  font-size: 0.88rem; line-height: 1.5;
  color: var(--text-soft, rgba(255,255,255,0.82));
  margin: 8px 0 14px 0;
}
.outlook-2026__cells {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
@media (max-width: 720px) {
  .outlook-2026__cells { grid-template-columns: 1fr; }
}
.outlook-2026__cell {
  background: rgba(255,255,255,0.018);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 12px 14px;
  display: flex; flex-direction: column; gap: 4px;
}
.outlook-2026__cell-label {
  font-size: 0.66rem; letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  margin: 0;
}
.outlook-2026__cell-value {
  font-size: 1.05rem; font-weight: 700;
  color: var(--text-bright, rgba(255,255,255,0.92));
  line-height: 1.25;
}
.outlook-2026__cell-value--projected {
  color: oklch(0.65 0.18 75);  /* amber */
}
.outlook-2026__cell-value--confirmed {
  color: oklch(0.65 0.16 150);  /* green */
}
.outlook-2026__cell-value--competition {
  color: oklch(0.65 0.18 25);  /* red */
}
.outlook-2026__cell-sub {
  font-size: 0.74rem;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  line-height: 1.4;
}
.outlook-2026__cast-list {
  list-style: none; padding: 0; margin: 4px 0 0 0;
  display: flex; flex-direction: column; gap: 3px;
}
.outlook-2026__cast-list li {
  font-size: 0.78rem;
  color: var(--text-soft, rgba(255,255,255,0.78));
  line-height: 1.4;
  display: flex; gap: 6px; align-items: baseline;
}
.outlook-2026__cast-list strong {
  color: var(--text-bright, rgba(255,255,255,0.92));
  font-weight: 600;
}
.outlook-2026__award-list {
  list-style: none; padding: 0; margin: 4px 0 0 0;
  display: flex; flex-wrap: wrap; gap: 6px;
}
.outlook-2026__award {
  font-size: 0.70rem; letter-spacing: 0.04em;
  padding: 3px 8px;
  background: var(--accolade-gold-base, #d1a23a);
  color: #15161a;
  border-radius: 4px;
  font-weight: 600;
}
.outlook-2026__no-awards {
  font-size: 0.74rem;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  font-style: italic;
}
.outlook-2026__team-context {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  font-size: 0.76rem;
  color: var(--text-quiet, rgba(255,255,255,0.65));
  line-height: 1.5;
}
"""


# Position group label for the depth-chart cell
_POSITION_LABELS = {
    "QB": "Quarterback",
    "RB": "Running back",
    "TB": "Running back",
    "FB": "Fullback",
    "WR": "Wide receiver",
    "TE": "Tight end",
    "OL": "Offensive line",
    "OT": "Offensive tackle",
    "OG": "Offensive guard",
    "C":  "Center",
    "DL": "Defensive line",
    "DE": "Defensive end",
    "EDGE": "Edge",
    "DT": "Defensive tackle",
    "NT": "Nose tackle",
    "LB": "Linebacker",
    "ILB": "Linebacker",
    "OLB": "Linebacker",
    "MLB": "Linebacker",
    "CB": "Cornerback",
    "S":  "Safety",
    "DB": "Defensive back",
    "K":  "Kicker",
    "P":  "Punter",
    "LS": "Long snapper",
}


def _depth_chart_for_player(db, player_id: int) -> dict[str, Any] | None:
    """Fetch manually-seeded depth chart row, or None."""
    rows = db.query_all(
        """
        select position_group, slot_rank, starter_status, confidence,
               source, source_url, notes, as_of
          from player_depth_chart_2026
         where player_id = :pid and season_year = 2026
         order by slot_rank asc
         limit 1
        """,
        {"pid": int(player_id)},
    )
    return dict(rows[0]) if rows else None


def _team_preview_for(db, team_id: int | None) -> dict[str, Any] | None:
    if db is None or team_id is None:
        return None
    rows = db.query_all(
        """
        select * from team_preview_snapshot
         where team_id = :tid and season_year = 2026
         order by as_of_date desc limit 1
        """,
        {"tid": int(team_id)},
    )
    return dict(rows[0]) if rows else None


def _team_seasons_oc(db, team_id: int | None, season: int) -> str | None:
    if db is None or team_id is None:
        return None
    rows = db.query_all(
        """
        select offensive_coordinator, head_coach
          from team_seasons
         where team_id = :tid and season_year = :s
         limit 1
        """,
        {"tid": int(team_id), "s": int(season)},
    )
    if not rows:
        return None
    return (rows[0].get("offensive_coordinator") or "").strip() or None


def _resolve_team_name(db, team_id: int | None) -> str | None:
    if db is None or team_id is None:
        return None
    rows = db.query_all(
        "select canonical_name from teams where team_id = :tid",
        {"tid": int(team_id)},
    )
    return rows[0]["canonical_name"] if rows else None


def _award_watch_for(db, player_id: int) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select award_slug, list_type, position_rank, as_of
          from player_award_watch_2026
         where player_id = :pid and season_year = 2026
         order by priority asc, position_rank asc
         limit 5
        """,
        {"pid": int(player_id)},
    )
    return [dict(r) for r in rows]


def _most_recent_as_of(*sources: Any) -> str | None:
    """Return the most recent as_of date string across depth/award rows.

    Accepts dicts and lists-of-dicts. Returns ISO date string (YYYY-MM-DD) or None.
    """
    candidates: list[str] = []
    for src in sources:
        if src is None:
            continue
        if isinstance(src, dict):
            v = src.get("as_of")
            if v:
                candidates.append(str(v)[:10])
        elif isinstance(src, list):
            for row in src:
                v = row.get("as_of") if isinstance(row, dict) else None
                if v:
                    candidates.append(str(v)[:10])
    return max(candidates) if candidates else None


def _format_as_of_pill(as_of_str: str | None) -> str:
    """Render an 'Updated MMM DD' pill. Empty string if no date."""
    if not as_of_str:
        return ""
    try:
        from datetime import datetime as _dt
        d = _dt.fromisoformat(as_of_str[:10])
        return (
            f'<span class="outlook-2026__updated" title="Refreshed {as_of_str[:10]}">'
            f'Updated {d.strftime("%b ")}{d.day}</span>'
        )
    except (TypeError, ValueError):
        return ""


def _award_display_name(award_slug: str) -> str:
    return {
        "heisman":         "Heisman Watch",
        "maxwell":         "Maxwell Watch",
        "walter_camp":     "Walter Camp",
        "davey_obrien":    "Davey O'Brien",
        "manning":         "Manning Award",
        "doak_walker":     "Doak Walker",
        "biletnikoff":     "Biletnikoff",
        "mackey":          "Mackey",
        "nagurski":        "Nagurski",
        "bednarik":        "Bednarik",
        "butkus":          "Butkus",
        "thorpe":          "Jim Thorpe",
        "outland":         "Outland",
        "rimington":       "Rimington",
        "lou_groza":       "Groza",
        "ray_guy":         "Ray Guy",
        "lott":            "Lott IMPACT",
        "hornung":         "Hornung",
        "wuerffel":        "Wuerffel",
        "burlsworth":      "Burlsworth",
    }.get(award_slug, award_slug.replace("_", " ").title())


def _starter_status_label(status: str) -> tuple[str, str]:
    """Return (display_label, CSS modifier class) for a starter_status."""
    return {
        "returning_starter":  ("Returning starter", "confirmed"),
        "projected_starter":  ("Projected starter", "projected"),
        "co_starter":         ("Co-starter", "projected"),
        "camp_competition":   ("Camp competition", "competition"),
        "backup":             ("Backup", "projected"),
        "depth":              ("Rotation / depth", "projected"),
    }.get(status, (status.replace("_", " ").title(), "projected"))


def _continuity_grade(returning_pct: float | None) -> tuple[str, str]:
    """Return (label, CSS modifier) for a returning-production percentage."""
    if returning_pct is None:
        return ("Unknown", "")
    p = float(returning_pct)
    if p >= 0.70:
        return ("Strong continuity", "confirmed")
    if p >= 0.50:
        return ("Solid continuity", "")
    if p >= 0.30:
        return ("Moderate turnover", "projected")
    return ("Heavy turnover", "competition")


def render_outlook_2026(db, player_id: int | None) -> str:
    """Render the 2026 Outlook. Only fires when status_code is RETURNING_2026."""
    if db is None or player_id is None:
        return ""

    from .status_strip import fetch_status_row
    status_row = fetch_status_row(db, player_id)
    if status_row is None:
        return ""
    if status_row.get("status_code") != "RETURNING_2026":
        return ""

    team_id = status_row.get("current_team_id")
    team_name = _resolve_team_name(db, team_id) or "—"
    position = (status_row.get("position_2026") or status_row.get("master_position") or "").upper()
    position_label = _POSITION_LABELS.get(position, position or "Player")

    # Cell 1 — Depth chart
    depth = _depth_chart_for_player(db, int(player_id))
    if depth:
        starter_label, cell_cls = _starter_status_label(depth.get("starter_status") or "projected_starter")
        # Prefer the depth chart's manually-curated position_group over the status cache's
        # position_2026 field (which comes from roster data and can be wrong, e.g. EDGE
        # players classified as LB).
        dc_position = (depth.get("position_group") or "").upper()
        if dc_position:
            position_label = _POSITION_LABELS.get(dc_position, dc_position or position_label)
        depth_sub = f"{position_label} · {team_name}"
        if depth.get("source") == "manual_editorial":
            depth_sub += " · editorial"
    else:
        starter_label = "Projected starter"
        cell_cls = "projected"
        depth_sub = f"{position_label} · {team_name}"

    # Cell 2 — Supporting cast
    preview = _team_preview_for(db, team_id)
    cast_lines: list[str] = []
    if preview:
        ret_off = preview.get("returning_offense")
        if ret_off is not None:
            pct = int(round(float(ret_off) * 100))
            cont_label, _ = _continuity_grade(ret_off)
            cast_lines.append(
                f'<li><strong>{pct}%</strong> of 2024 offensive production back '
                f'<span style="opacity:0.65;">({cont_label})</span></li>'
            )
        drafted = preview.get("drafted_count") or 0
        if drafted > 0:
            cast_lines.append(
                f'<li><strong>{drafted}</strong> {team_name} player'
                f'{"s" if drafted != 1 else ""} drafted to NFL</li>'
            )
        net = preview.get("transfer_net_count")
        if net is not None:
            net_int = int(net)
            sign = "+" if net_int >= 0 else ""
            cast_lines.append(
                f'<li>Transfer portal: <strong>{sign}{net_int}</strong> net '
                f'({preview.get("transfer_in_count") or 0} in / '
                f'{preview.get("transfer_out_count") or 0} out)</li>'
            )

    # OC continuity diff
    oc_2025 = _team_seasons_oc(db, team_id, 2025)
    oc_2026 = _team_seasons_oc(db, team_id, 2026)
    if oc_2025 and oc_2026:
        if oc_2025 == oc_2026:
            cast_lines.append(f'<li><strong>{escape(oc_2026)}</strong> returns as OC</li>')
        else:
            cast_lines.append(
                f'<li>New OC: <strong>{escape(oc_2026)}</strong> '
                f'(replaces {escape(oc_2025)})</li>'
            )
    elif oc_2026:
        cast_lines.append(f'<li>OC: <strong>{escape(oc_2026)}</strong></li>')

    cast_html = (
        f'<ul class="outlook-2026__cast-list">{"".join(cast_lines)}</ul>'
        if cast_lines else
        '<p class="outlook-2026__cell-sub">Supporting-cast data loading…</p>'
    )

    # Cell 3 — Award watch
    awards = _award_watch_for(db, int(player_id))
    if awards:
        award_html = (
            '<ul class="outlook-2026__award-list">' +
            "".join(
                f'<li class="outlook-2026__award outlook-2026__award--{escape(a["award_slug"])}">'
                f'{escape(_award_display_name(a["award_slug"]))}'
                f'</li>'
                for a in awards
            ) +
            '</ul>'
        )
    else:
        award_html = (
            '<p class="outlook-2026__no-awards">No preseason watch lists yet '
            '(most drop June 15 – July 15)</p>'
        )

    # Team-context trailer
    team_context = ""
    if preview:
        talent_rank = preview.get("talent_rank")
        recruiting_rank = preview.get("recruiting_rank")
        prior_record = ""
        if preview.get("prior_wins") is not None and preview.get("prior_losses") is not None:
            prior_record = f"Last season: {preview['prior_wins']}-{preview['prior_losses']}"
            if preview.get("prior_final_ap_rank"):
                prior_record += f" (AP #{preview['prior_final_ap_rank']})"
        parts: list[str] = []
        if prior_record:
            parts.append(prior_record)
        if talent_rank:
            parts.append(f"Talent rank #{int(talent_rank)}")
        if recruiting_rank:
            parts.append(f"2026 recruiting class #{int(recruiting_rank)}")
        if parts:
            team_context = (
                f'<p class="outlook-2026__team-context">'
                f'{escape(team_name)} &middot; {" &middot; ".join(parts)}'
                f'</p>'
            )

    # "Updated MMM DD" pill — most recent as_of across depth chart + award rows.
    updated_pill = _format_as_of_pill(_most_recent_as_of(depth, awards))

    return (
        '<section class="outlook-2026" '
        f'data-module="outlook-2026" data-state="ready" '
        f'aria-label="2026 season outlook for {escape(team_name)}">'
        '<header class="outlook-2026__head">'
        '<div>'
        '<p class="outlook-2026__eyebrow">2026 Outlook</p>'
        f'<p class="outlook-2026__title">'
        f'Returning to {escape(team_name)} for 2026'
        '</p>'
        '</div>'
        f'{updated_pill}'
        '</header>'
        '<div class="outlook-2026__cells">'
        '<div class="outlook-2026__cell">'
        '<p class="outlook-2026__cell-label">2026 Depth chart</p>'
        f'<p class="outlook-2026__cell-value outlook-2026__cell-value--{cell_cls}">'
        f'{escape(starter_label)}</p>'
        f'<p class="outlook-2026__cell-sub">{escape(depth_sub)}</p>'
        '</div>'
        '<div class="outlook-2026__cell">'
        '<p class="outlook-2026__cell-label">Returning around him</p>'
        f'{cast_html}'
        '</div>'
        '<div class="outlook-2026__cell">'
        '<p class="outlook-2026__cell-label">2026 Award watch</p>'
        f'{award_html}'
        '</div>'
        '</div>'
        f'{team_context}'
        '</section>'
    )
