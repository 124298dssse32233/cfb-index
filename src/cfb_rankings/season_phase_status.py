"""Offseason Status resolver — Autopilot v1 TASK 7.2.

Looks at roster history, transfers, draft picks, and recruiting entries
to produce the player's Offseason Status chip for the hero identity
strip. Spec: PLAYER_PAGE_SEASON_PHASE_DESIGN.md §9.

15 states enumerated:
    RETURNING, DECLARED FOR DRAFT, DRAFTED, UNDRAFTED FA,
    TRANSFERRED IN, TRANSFERRED OUT, ENTERED PORTAL,
    COMMITTED OUT OF PORTAL, EARLY ENROLLEE, SIGNED RECRUIT,
    MEDICAL RETIREMENT, GRADUATED, NFL ACTIVE, NFL RETIRED, UNRESOLVED.

Public entry: `resolve_offseason_status(db, player_id, today) ->
OffseasonStatus`.

Conservative semantics: when multiple states could apply, favor the
most-recent evidence. When evidence is missing, returns UNRESOLVED
rather than guessing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from cfb_rankings.db import Database


class OffseasonStatusKind(str, Enum):
    RETURNING = "RETURNING"
    DECLARED_FOR_DRAFT = "DECLARED_FOR_DRAFT"
    DRAFTED = "DRAFTED"
    UNDRAFTED_FA = "UNDRAFTED_FA"
    TRANSFERRED_IN = "TRANSFERRED_IN"
    TRANSFERRED_OUT = "TRANSFERRED_OUT"
    ENTERED_PORTAL = "ENTERED_PORTAL"
    COMMITTED_OUT_OF_PORTAL = "COMMITTED_OUT_OF_PORTAL"
    EARLY_ENROLLEE = "EARLY_ENROLLEE"
    SIGNED_RECRUIT = "SIGNED_RECRUIT"
    MEDICAL_RETIREMENT = "MEDICAL_RETIREMENT"
    GRADUATED = "GRADUATED"
    NFL_ACTIVE = "NFL_ACTIVE"
    NFL_RETIRED = "NFL_RETIRED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class OffseasonStatus:
    kind: OffseasonStatusKind
    display_copy: str                  # Per §9 example copy
    sub_context: str | None = None     # Year/team/date/etc
    chip_color: str = "muted"          # accolade-gold | muted | destructive-subtle


_POSITIVE = {
    OffseasonStatusKind.RETURNING,
    OffseasonStatusKind.DRAFTED,
    OffseasonStatusKind.COMMITTED_OUT_OF_PORTAL,
    OffseasonStatusKind.EARLY_ENROLLEE,
    OffseasonStatusKind.SIGNED_RECRUIT,
    OffseasonStatusKind.NFL_ACTIVE,
}
_ABRUPT = {
    OffseasonStatusKind.MEDICAL_RETIREMENT,
    OffseasonStatusKind.TRANSFERRED_OUT,
}


def _color_for(kind: OffseasonStatusKind) -> str:
    if kind in _POSITIVE:
        return "accolade-gold"
    if kind in _ABRUPT:
        return "destructive-subtle"
    return "muted"


def resolve_offseason_status(
    db: Database,
    player_id: int,
    today: date | None = None,
    forward_season_year: int | None = None,
) -> OffseasonStatus:
    """Resolve a player's current offseason status.

    Order of resolution (most-definitive first):
      1. Was this player drafted into the NFL? -> DRAFTED / NFL_ACTIVE.
      2. Did they enter the portal? -> ENTERED_PORTAL / COMMITTED_OUT_OF_PORTAL.
      3. Did they transfer? -> TRANSFERRED_IN / TRANSFERRED_OUT.
      4. Are they on a roster for the forward season? -> RETURNING.
      5. Signed as a recruit for the forward class? -> EARLY_ENROLLEE / SIGNED_RECRUIT.
      6. Otherwise UNRESOLVED.
    """
    today = today or date.today()
    forward = forward_season_year or (today.year if today.month >= 8 else today.year)

    # 1. Drafted? (requires player_nfl_draft table existing — guarded.)
    try:
        drafted = db.query_one(
            "select draft_year, round, pick, nfl_team, nfl_team_abbr "
            "from player_nfl_draft where player_id = :pid order by draft_year desc limit 1",
            {"pid": player_id},
        )
    except Exception:
        drafted = None
    if drafted:
        yrs_ago = today.year - int(drafted["draft_year"])
        if yrs_ago == 0:
            tag = drafted.get("nfl_team_abbr") or drafted.get("nfl_team") or ""
            copy = f"DRAFTED · R{drafted['round']} · #{drafted['pick']} · {tag}".strip()
            return OffseasonStatus(
                kind=OffseasonStatusKind.DRAFTED,
                display_copy=copy,
                sub_context=str(drafted["draft_year"]),
                chip_color="accolade-gold",
            )
        # Prior-year draftees are NFL_ACTIVE.
        tag = drafted.get("nfl_team_abbr") or drafted.get("nfl_team") or ""
        copy = f"NFL · {tag} · YEAR {yrs_ago}"
        return OffseasonStatus(
            kind=OffseasonStatusKind.NFL_ACTIVE,
            display_copy=copy,
            sub_context=str(drafted["draft_year"]),
            chip_color="accolade-gold",
        )

    # 2. Portal entry — schema uses from_team_name / to_team_name / transfer_date.
    try:
        portal_rows = db.query_all(
            "select from_team_name, to_team_name, transfer_date, eligibility "
            "from transfer_entries where player_id = :pid "
            "and season_year >= :season order by transfer_date desc limit 1",
            {"pid": player_id, "season": forward - 1},
        )
    except Exception:
        portal_rows = []
    if portal_rows:
        row = portal_rows[0]
        dest = row.get("to_team_name")
        if dest:
            return OffseasonStatus(
                kind=OffseasonStatusKind.COMMITTED_OUT_OF_PORTAL,
                display_copy=f"PORTAL COMMIT · {dest.upper()}",
                sub_context=row.get("transfer_date"),
                chip_color="accolade-gold",
            )
        entry = row.get("transfer_date") or "recent"
        return OffseasonStatus(
            kind=OffseasonStatusKind.ENTERED_PORTAL,
            display_copy=f"PORTAL · ENTERED {str(entry)[:10]}",
            sub_context=row.get("from_team_name"),
            chip_color="muted",
        )

    # 4. Returning — roster_entries for the forward OR current season.
    #    Fall back to the latest roster year so an in-progress preseason ingest
    #    doesn't read as UNRESOLVED.
    try:
        returning = db.query_one(
            "select class_year, season_year from roster_entries "
            "where player_id = :pid order by season_year desc limit 1",
            {"pid": player_id},
        )
    except Exception:
        returning = None
    if returning and int(returning.get("season_year") or 0) >= forward - 1:
        class_year = str(returning.get("class_year") or "").strip()
        class_short = {
            "FR": "FR", "SO": "SO", "JR": "JR", "SR": "SR", "GR": "GR",
            "Freshman": "FR", "Sophomore": "SO", "Junior": "JR",
            "Senior": "SR", "Graduate": "GR",
            "1": "FR", "2": "SO", "3": "JR", "4": "SR", "5": "GR",
        }.get(class_year, class_year) if class_year else ""
        copy = f"RETURNING · {class_short} {forward}" if class_short else f"RETURNING · {forward}"
        return OffseasonStatus(
            kind=OffseasonStatusKind.RETURNING,
            display_copy=copy,
            sub_context=str(forward),
            chip_color="accolade-gold",
        )

    # 5. Recruit signee — recruiting_entries for the forward class year.
    try:
        recruit = db.query_one(
            "select team_id, season_year from recruiting_entries "
            "where player_id = :pid order by season_year desc limit 1",
            {"pid": player_id},
        )
    except Exception:
        recruit = None
    if recruit and int(recruit.get("season_year") or 0) >= forward:
        return OffseasonStatus(
            kind=OffseasonStatusKind.SIGNED_RECRUIT,
            display_copy=f"{recruit['season_year']} SIGNEE · ARRIVING FALL",
            sub_context=str(recruit["season_year"]),
            chip_color="accolade-gold",
        )

    # 6. UNRESOLVED fallback
    return OffseasonStatus(
        kind=OffseasonStatusKind.UNRESOLVED,
        display_copy="STATUS UNRESOLVED",
        chip_color="muted",
    )
