"""Player Status Strip — Wave 25 / Module 1.

Top-of-page identity bar that answers "what's this player's deal in May 2026?"
in 3 seconds. Renders for every player, every archetype.

Reads from `player_current_status_view` (migration 20260527_07) which
resolves 11 status codes deterministically:

  RETURNING_2026, TRANSFERRED_COLLEGE, NFL_DRAFTED_2026, NFL_DRAFTED_PRIOR,
  NFL_UDFA, PORTAL_OPEN, PORTAL_WITHDREW, EXHAUSTED_ELIGIBILITY,
  MEDICAL_RETIREMENT, HISTORICAL_ALUM, HS_RECRUIT_ONLY

For each archetype, the strip renders three slots:
  1. Status badge (left, colored per archetype)
  2. Detail line (middle, archetype-specific copy)
  3. As-of timestamp (right; overridden by 'override' provenance pill)

Per Brief §8.3 OKLCH tokens. Mobile-clean at 375px.

Public API:
    render_status_strip(db, player_id) -> str
    STATUS_STRIP_CSS                    -> str
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from html import escape
from typing import Any


STATUS_STRIP_CSS = """
/* Player Status Strip — Wave 25 / Module 1 */
.player-status-strip {
  margin: var(--space-3, 0.75rem) 0 var(--space-4, 1rem) 0;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.018);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 4px solid var(--pss-accent, var(--text-quiet, rgba(255,255,255,0.45)));
  border-radius: 10px;
  font-variant-numeric: tabular-nums;
  contain: layout;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 14px;
  align-items: center;
}
.player-status-strip__badge {
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--pss-badge-fg, #15161a);
  background: var(--pss-accent, rgba(255,255,255,0.10));
  padding: 4px 9px;
  border-radius: 4px;
  white-space: nowrap;
}
.player-status-strip__detail {
  font-size: 0.92rem;
  color: var(--text-bright, rgba(255,255,255,0.92));
  line-height: 1.35;
  font-weight: 500;
}
.player-status-strip__detail-sub {
  display: block;
  font-size: 0.72rem;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  font-weight: 400;
  margin-top: 1px;
}
.player-status-strip__as-of {
  font-size: 0.66rem;
  color: var(--text-quiet, rgba(255,255,255,0.45));
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.player-status-strip__as-of--override {
  background: rgba(209, 162, 58, 0.15);
  color: var(--accolade-gold-base, #d1a23a);
  padding: 2px 7px;
  border-radius: 4px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
/* Archetype accents */
.player-status-strip--returning_2026         { --pss-accent: oklch(0.60 0.16 150); --pss-badge-fg: #0a1a0a; }
.player-status-strip--transferred_college    { --pss-accent: oklch(0.65 0.18 75);  --pss-badge-fg: #1a0e00; }
.player-status-strip--nfl_drafted_2026       { --pss-accent: oklch(0.45 0.18 260); --pss-badge-fg: #f4f4f5; }
.player-status-strip--nfl_drafted_prior      { --pss-accent: oklch(0.40 0.10 260); --pss-badge-fg: #f4f4f5; }
.player-status-strip--nfl_udfa               { --pss-accent: oklch(0.50 0.05 260); --pss-badge-fg: #f4f4f5; }
.player-status-strip--portal_open            { --pss-accent: oklch(0.65 0.18 75);  --pss-badge-fg: #1a0e00; }
.player-status-strip--portal_withdrew        { --pss-accent: oklch(0.60 0.16 150); --pss-badge-fg: #0a1a0a; }
.player-status-strip--exhausted_eligibility  { --pss-accent: oklch(0.45 0.02 250); --pss-badge-fg: #f4f4f5; }
.player-status-strip--medical_retirement     { --pss-accent: oklch(0.45 0.02 250); --pss-badge-fg: #f4f4f5; }
.player-status-strip--historical_alum        { --pss-accent: oklch(0.40 0.02 250); --pss-badge-fg: #f4f4f5; }
.player-status-strip--hs_recruit_only        { --pss-accent: oklch(0.65 0.18 75);  --pss-badge-fg: #1a0e00; }
.player-status-strip--unknown                { --pss-accent: rgba(255,255,255,0.18); --pss-badge-fg: #f4f4f5; }
/* Mobile */
@media (max-width: 640px) {
  .player-status-strip {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
    gap: 6px;
    padding: 10px 14px;
  }
  .player-status-strip__badge { justify-self: start; }
  .player-status-strip__as-of { justify-self: start; font-size: 0.62rem; }
}
"""


# Archetype label and detail copy templates
_STATUS_COPY: dict[str, tuple[str, str]] = {
    # (badge_label, detail_template)
    "RETURNING_2026":        ("2026 RETURNING",   "Returning to {team} for 2026"),
    "TRANSFERRED_COLLEGE":   ("2026 TRANSFER",    "Transferred {from_team_arrow}{team} for 2026"),
    "NFL_DRAFTED_2026":      ("2026 NFL DRAFT",   "Drafted by {nfl_team} — {round_pick_overall}"),
    "NFL_DRAFTED_PRIOR":     ("NOW IN NFL",       "{nfl_team} — drafted {draft_year}, {round_pick_overall}"),
    "NFL_UDFA":              ("NFL FREE AGENT",   "Signed as UDFA with {nfl_team}"),
    "PORTAL_OPEN":           ("IN PORTAL",        "In transfer portal — destination TBD{from_team_suffix}"),
    "PORTAL_WITHDREW":       ("RETURNED",         "Returning to {team} for 2026 (withdrew from portal)"),
    "EXHAUSTED_ELIGIBILITY": ("CAREER COMPLETE",  "{team} {last_year} — college career complete"),
    "MEDICAL_RETIREMENT":    ("CAREER ENDED",     "{team} — career-ending injury"),
    "HISTORICAL_ALUM":       ("ALUMNUS",          "{team} {last_year} alumnus"),
    "HS_RECRUIT_ONLY":       ("RECRUIT",          "High-school recruit — never enrolled"),
}


def _archetype_class(status_code: str) -> str:
    """Map status code to CSS class suffix (lowercase)."""
    if not status_code:
        return "unknown"
    return status_code.lower()


def _ordinal(n: int) -> str:
    if 10 <= (n % 100) <= 20:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _round_pick_overall(row: dict[str, Any]) -> str:
    """Build 'Rd 3, Pick 65 (#65 overall)' style string from view row."""
    rd = row.get("draft_round")
    pick = row.get("draft_pick")
    overall = row.get("draft_overall")
    parts: list[str] = []
    if rd is not None:
        parts.append(f"Rd {rd}")
        if pick is not None:
            parts.append(f"Pick {pick}")
    if overall is not None:
        if overall == 1:
            parts = ["No. 1 overall"]
        elif parts:
            parts.append(f"#{overall} overall")
        else:
            parts.append(f"#{overall} overall")
    return ", ".join(parts) if parts else "pick TBD"


def _resolve_team_name(db, team_id: int | None) -> str | None:
    if db is None or team_id is None:
        return None
    rows = db.query_all(
        "select canonical_name from teams where team_id = :tid",
        {"tid": int(team_id)},
    )
    return rows[0]["canonical_name"] if rows else None


def _format_detail(row: dict[str, Any], db) -> str:
    status_code = row.get("status_code") or "HISTORICAL_ALUM"
    template = _STATUS_COPY.get(status_code, _STATUS_COPY["HISTORICAL_ALUM"])[1]

    # Resolve team names
    current_team_name = _resolve_team_name(db, row.get("current_team_id"))
    prev_team_name = _resolve_team_name(db, row.get("previous_team_id"))
    portal_origin_name = _resolve_team_name(db, row.get("portal_origin_team_id"))
    last_college = row.get("last_college_team_name")

    # Build template substitutions
    nfl_team = row.get("nfl_team") or "—"
    last_year = row.get("last_college_year")

    # Prefer current_team_name, fall back to last_college, then "—"
    team = current_team_name or last_college or "—"

    from_team_arrow = ""
    if status_code == "TRANSFERRED_COLLEGE" and prev_team_name and current_team_name and prev_team_name != current_team_name:
        from_team_arrow = f"{prev_team_name} → "

    from_team_suffix = ""
    if status_code == "PORTAL_OPEN" and portal_origin_name:
        from_team_suffix = f" (from {portal_origin_name})"

    rpo = _round_pick_overall(row)
    draft_year = row.get("draft_year") or ""

    try:
        return template.format(
            team=team,
            from_team_arrow=from_team_arrow,
            from_team_suffix=from_team_suffix,
            nfl_team=nfl_team,
            round_pick_overall=rpo,
            draft_year=draft_year,
            last_year=last_year or "",
        )
    except (KeyError, ValueError):
        return template  # safe fallback


def _as_of_display(row: dict[str, Any]) -> tuple[str, bool]:
    """Return (display_text, is_override). For overrides, use the set_at date.
    For computed, use today's date.
    """
    if row.get("status_provenance") == "override":
        set_at = row.get("override_set_at")
        if set_at:
            try:
                dt = datetime.fromisoformat(set_at.replace("Z", "+00:00"))
                return (f"Editorial · {dt.strftime('%b %d')}", True)
            except (TypeError, ValueError):
                pass
        return ("Editorial override", True)
    today = date.today()
    return (f"As of {today.strftime('%b ')}{today.day}, {today.year}", False)


def fetch_status_row(db, player_id: int | None) -> dict[str, Any] | None:
    if db is None or player_id is None:
        return None
    # Prefer the materialized cache table (built by scripts/wave25_build_status_cache.py
    # at build start). Falls back to the view if cache missing — view is correct
    # but ~minutes per query, so cache is essential for the 7k-player build loop.
    try:
        rows = db.query_all(
            "select * from player_current_status_cache where player_id = :pid",
            {"pid": int(player_id)},
        )
        if rows:
            return dict(rows[0])
    except Exception:
        pass
    rows = db.query_all(
        "select * from player_current_status_view where player_id = :pid",
        {"pid": int(player_id)},
    )
    return dict(rows[0]) if rows else None


def render_status_strip(db, player_id: int | None) -> str:
    if db is None or player_id is None:
        return ""

    row = fetch_status_row(db, player_id)
    if row is None:
        return ""  # No row in players table → can't render

    status_code = row.get("status_code") or "HISTORICAL_ALUM"
    override_label = (row.get("override_label") or "").strip()

    # Badge text
    default_badge, _detail_tpl = _STATUS_COPY.get(
        status_code, _STATUS_COPY["HISTORICAL_ALUM"]
    )
    badge = override_label or default_badge

    # Detail line (replace override_label-driven if present)
    detail = _format_detail(row, db)

    # As-of right-side text
    as_of_text, is_override = _as_of_display(row)
    as_of_cls = (
        "player-status-strip__as-of player-status-strip__as-of--override"
        if is_override else
        "player-status-strip__as-of"
    )

    archetype_cls = _archetype_class(status_code)

    return (
        f'<section class="player-status-strip player-status-strip--{archetype_cls}" '
        f'data-module="player-status-strip" data-status-code="{escape(status_code)}" '
        f'data-provenance="{escape(row.get("status_provenance") or "computed")}" '
        'aria-label="2026 player status">'
        f'<span class="player-status-strip__badge">{escape(badge)}</span>'
        f'<span class="player-status-strip__detail">{escape(detail)}</span>'
        f'<time class="{as_of_cls}" datetime="{escape(date.today().isoformat())}">'
        f'{escape(as_of_text)}'
        '</time>'
        '</section>'
    )
