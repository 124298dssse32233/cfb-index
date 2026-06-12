"""2026 Eligibility Gate — is a 2025-discourse player ACTIVE for the upcoming season?

Spec: ``docs/design-system/59-player-evidence-packet-contract.md`` §4.1.1 (LOCKED
2026-06-12). Build step 14.2. ZERO LLM / ZERO network — pure structured reads.

WHY THIS EXISTS
---------------
The live top-50 player Story Cards preview the UPCOMING season (2026), but the
cohort is ranked by LAST season's (2025) discourse (``player_aura_weekly``,
``mention_count``). That 2025-ranked set therefore still contains players who are
GONE for 2026 — drafted, transferred out, graduated, flunked, walked-on-cut — and
previewing a departed player as a returning starter is wrong. This gate filters
the cohort to players actually active for the upcoming season, and a departed
player is excluded from the forward top-50 (recast as a GHOST in their successor's
succession block, §4.1.1 / §5).

TIME-EVOLVING TWO-LAYER DESIGN
------------------------------
The ONLY signal that catches *every* reason a player is gone is a published
upcoming-season roster. CFBD has NOT published the 2026 roster yet (verified live
2026-06-12: ``get_roster(year=2026)`` returns 0 players across all teams;
``roster_entries`` max ``season_year`` = 2025). So the gate is two-layered:

  LAYER 1 — GROUND TRUTH (roster, once it publishes ~August):
    * If ``roster_entries`` has ANY row for this player in ``upcoming_season`` ->
      ``on_upcoming_roster=True`` -> ACTIVE. Roster presence OVERRIDES inference.
    * If a non-empty upcoming roster EXISTS in the DB but this player is absent ->
      ``on_upcoming_roster=False`` -> DEPARTED ("absent from <yr> roster"). This
      catches the quiet exits the departure signals miss.
    * If NO upcoming roster exists in the DB yet -> ``on_upcoming_roster=None`` and
      we fall through to inference (the current offseason state).

  LAYER 2 — INFERENCE (offseason, no roster — the state TODAY):
    * DEPARTED if a ``player_nfl_draft`` row with ``draft_year >= upcoming_season``
      (drafted) OR a ``transfer_entries`` row for ``upcoming_season`` whose
      ``from_team_id`` == the player's last (2025) team_id (transferred OUT).
      NOTE: a player who transferred but ALSO carries a positive upcoming-season
      signal (``player_depth_chart_2026`` / ``player_award_watch_2026``) is ACTIVE
      on the new team, NOT departed — the positive signal is checked first.
    * ACTIVE if a positive upcoming-season row exists
      (``player_depth_chart_2026`` / ``player_award_watch_2026``) OR the player is
      an underclassman (2025 ``class_year`` in '1','2','3') with no departure
      signal (presumed returning).
    * UNCERTAIN otherwise — a senior (``class_year`` '4'+) with no departure signal
      and no positive row. Keep in the cohort but do NOT assert "returning starter"
      with confidence; resolve at roster.

Once the 2026 roster lands, LAYER 1 self-corrects the cards on the next cadence
beat (absence-from-roster overrides the inferred ACTIVE/UNCERTAIN reads).

CONTRACT
--------
NEVER raises — this feeds the live selector and the render path. Every DB read is
wrapped so a missing table / bad column / locked DB degrades to a safe default
(UNCERTAIN), never an exception. Uses the project's ``db.query_one`` /
``db.query_all``.

Public API:
    classify_2026_status(db, player_id, upcoming_season=2026, last_completed=2025) -> dict
        -> {"status": "active"|"departed"|"uncertain",
            "reason": str,
            "on_upcoming_roster": bool|None}
    is_departed(db, player_id, upcoming_season=2026) -> bool
    filter_active(db, player_ids, upcoming_season=2026) -> list[int]
"""
from __future__ import annotations

from typing import Any, Iterable, Optional


# Status constants (avoid stringly-typed typos at call sites).
ACTIVE = "active"
DEPARTED = "departed"
UNCERTAIN = "uncertain"

# 2025 roster class-year codes that read as "underclassman, presumed returning"
# ('1'=FR, '2'=SO, '3'=JR). Seniors ('4'+) with no positive signal fall to
# UNCERTAIN per §4.1.1. roster_entries.class_year is a string code.
_UNDERCLASS_CODES = frozenset({"1", "2", "3"})


# ---------------------------------------------------------------------------
# Crash-proof DB helpers (mirror succession.py — never raise into the caller).
# ---------------------------------------------------------------------------
def _safe_one(db, sql: str, params: dict[str, Any]) -> Optional[dict[str, Any]]:
    try:
        return db.query_one(sql, params)
    except Exception:
        return None


def _safe_all(db, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return db.query_all(sql, params) or []
    except Exception:
        return []


def _to_int(v: Any) -> Optional[int]:
    try:
        if v is None or v == "":
            return None
        return int(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Sub-signals
# ---------------------------------------------------------------------------
def _upcoming_roster_status(db, player_id: int, upcoming_season: int) -> Optional[bool]:
    """Layer-1 ground truth.

    Returns:
        True  -> player HAS a roster row for upcoming_season (active, ground truth).
        False -> a non-empty upcoming roster exists in the DB but this player is
                 absent (departed, ground truth).
        None  -> NO upcoming roster exists in the DB yet (fall through to inference).
    """
    mine = _safe_one(
        db,
        "select 1 as ok from roster_entries "
        "where player_id = :pid and season_year = :s limit 1",
        {"pid": int(player_id), "s": int(upcoming_season)},
    )
    if mine:
        return True
    # No row for me — but is there an upcoming roster at all? Only then is my
    # absence meaningful. (Today: 0 rows for 2026, so this returns None.)
    any_roster = _safe_one(
        db,
        "select 1 as ok from roster_entries where season_year = :s limit 1",
        {"s": int(upcoming_season)},
    )
    if any_roster:
        return False
    return None


def _last_team_id(db, player_id: int, last_completed: int) -> Optional[int]:
    """The player's team_id in the last completed season (the departure anchor).

    A transfer-OUT for the upcoming cycle counts only if its ``from_team_id``
    matches the team the player actually played for last season — otherwise a
    stale prior-year transfer row (e.g. a 2024 portal move) would mis-fire.
    """
    row = _safe_one(
        db,
        "select team_id from roster_entries "
        "where player_id = :pid and season_year = :s and team_id is not null "
        "order by roster_entry_id desc limit 1",
        {"pid": int(player_id), "s": int(last_completed)},
    )
    return _to_int(row.get("team_id")) if row else None


def _draft_departure(db, player_id: int, upcoming_season: int) -> Optional[str]:
    """Reason string if drafted into the NFL for the upcoming season (or later)."""
    row = _safe_one(
        db,
        "select draft_year, round from player_nfl_draft "
        "where player_id = :pid and draft_year >= :s "
        "order by draft_year asc limit 1",
        {"pid": int(player_id), "s": int(upcoming_season)},
    )
    if not row:
        return None
    yr = _to_int(row.get("draft_year"))
    rnd = _to_int(row.get("round"))
    if yr is None:
        return None
    return f"drafted {yr} r{rnd}" if rnd is not None else f"drafted {yr}"


def _transfer_out_departure(
    db, player_id: int, upcoming_season: int, last_completed: int
) -> Optional[str]:
    """Reason string if the player transferred OUT of their last team for the
    upcoming cycle. Gated on ``from_team_id`` == last-completed-season team_id so
    a stale prior-year portal row can't mis-fire.
    """
    last_team = _last_team_id(db, player_id, last_completed)
    rows = _safe_all(
        db,
        "select from_team_id, to_team_name from transfer_entries "
        "where player_id = :pid and season_year = :s",
        {"pid": int(player_id), "s": int(upcoming_season)},
    )
    for row in rows:
        from_tid = _to_int(row.get("from_team_id"))
        # If we know the last team, require the move to originate there. If we
        # can't resolve the last team (sparse roster), accept any upcoming-cycle
        # transfer-out as a departure signal — the upcoming season_year already
        # scopes it to the forward cycle.
        if last_team is not None and from_tid is not None and from_tid != last_team:
            continue
        dest = row.get("to_team_name")
        return f"transferred to {dest}" if dest else "transferred out"
    return None


def _positive_signal(db, player_id: int) -> Optional[str]:
    """Reason string if a positive UPCOMING-season row exists.

    A depth-chart-2026 or award-watch-2026 row is an affirmative "active for 2026"
    signal — it overrides a transfer-OUT (the player is active on the NEW team).
    """
    dc = _safe_one(
        db,
        "select 1 as ok from player_depth_chart_2026 where player_id = :pid limit 1",
        {"pid": int(player_id)},
    )
    if dc:
        return "on 2026 depth chart"
    aw = _safe_one(
        db,
        "select 1 as ok from player_award_watch_2026 where player_id = :pid limit 1",
        {"pid": int(player_id)},
    )
    if aw:
        return "on 2026 award watch list"
    return None


def _class_year(db, player_id: int, last_completed: int) -> Optional[str]:
    """The player's last-completed-season roster class_year code ('1'..'6')."""
    row = _safe_one(
        db,
        "select class_year from roster_entries "
        "where player_id = :pid and season_year = :s "
        "and class_year is not null and class_year <> '' "
        "order by roster_entry_id desc limit 1",
        {"pid": int(player_id), "s": int(last_completed)},
    )
    if row and row.get("class_year") not in (None, ""):
        return str(row["class_year"])
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def classify_2026_status(
    db,
    player_id: int,
    upcoming_season: int = 2026,
    last_completed: int = 2025,
) -> dict:
    """Classify a 2025-discourse player as active / departed / uncertain for 2026.

    See module docstring for the layered logic. Returns a dict:
        {"status": "active"|"departed"|"uncertain",
         "reason": str,
         "on_upcoming_roster": bool|None}

    NEVER raises — any failure degrades to UNCERTAIN with a diagnostic reason.
    """
    pid = _to_int(player_id)
    if db is None or pid is None:
        return {
            "status": UNCERTAIN,
            "reason": "no player_id",
            "on_upcoming_roster": None,
        }

    # --- LAYER 1: roster ground truth (overrides inference once published) ----
    on_roster = _upcoming_roster_status(db, pid, upcoming_season)
    if on_roster is True:
        return {
            "status": ACTIVE,
            "reason": f"on {upcoming_season} roster",
            "on_upcoming_roster": True,
        }
    if on_roster is False:
        return {
            "status": DEPARTED,
            "reason": f"absent from {upcoming_season} roster",
            "on_upcoming_roster": False,
        }

    # --- LAYER 2: inference (offseason, no roster) ----------------------------
    # Positive upcoming-season signal wins over a transfer-OUT: a player who
    # transferred but is on the new team's 2026 depth chart / watch list is
    # ACTIVE on the new team, not departed (§4.1.1). Check it before transfer.
    positive = _positive_signal(db, pid)

    # Drafted into the NFL for the upcoming season (or later) = DEPARTED. A draft
    # row is terminal for college eligibility and is NOT rescued by a positive
    # row (which would be a stale carryover, not a real 2026 college signal).
    draft_reason = _draft_departure(db, pid, upcoming_season)
    if draft_reason is not None:
        return {
            "status": DEPARTED,
            "reason": draft_reason,
            "on_upcoming_roster": None,
        }

    if positive is not None:
        return {
            "status": ACTIVE,
            "reason": positive,
            "on_upcoming_roster": None,
        }

    # Transferred OUT of last team for the upcoming cycle, with NO positive 2026
    # signal on a new team = DEPARTED (from the forward cohort).
    transfer_reason = _transfer_out_departure(db, pid, upcoming_season, last_completed)
    if transfer_reason is not None:
        return {
            "status": DEPARTED,
            "reason": transfer_reason,
            "on_upcoming_roster": None,
        }

    # Underclassman (class 1-3) with no departure signal = presumed returning.
    cls = _class_year(db, pid, last_completed)
    if cls in _UNDERCLASS_CODES:
        return {
            "status": ACTIVE,
            "reason": f"underclassman (class {cls}), presumed returning",
            "on_upcoming_roster": None,
        }

    # Senior / unknown class, no departure signal, no positive row -> UNCERTAIN.
    cls_label = f"class {cls}" if cls else "class unknown"
    return {
        "status": UNCERTAIN,
        "reason": f"senior, unverified ({cls_label}); resolve at roster",
        "on_upcoming_roster": None,
    }


def is_departed(db, player_id: int, upcoming_season: int = 2026) -> bool:
    """Convenience: True iff the player is classified DEPARTED for the season."""
    try:
        return classify_2026_status(db, player_id, upcoming_season=upcoming_season)[
            "status"
        ] == DEPARTED
    except Exception:
        # Defensive: an unexpected failure must never report a player departed
        # (that would silently drop them from the cohort). Keep = not departed.
        return False


def filter_active(
    db, player_ids: Iterable[int], upcoming_season: int = 2026
) -> list[int]:
    """Drop DEPARTED players; keep ACTIVE + UNCERTAIN, preserving input order.

    Feeds the forward top-50 selector — a departed player is excluded and the
    next-most-talked-about active player takes the slot (§4.1.1 / §8).
    """
    out: list[int] = []
    for raw in player_ids or []:
        pid = _to_int(raw)
        if pid is None:
            continue
        if not is_departed(db, pid, upcoming_season=upcoming_season):
            out.append(pid)
    return out


__all__ = [
    "ACTIVE",
    "DEPARTED",
    "UNCERTAIN",
    "classify_2026_status",
    "is_departed",
    "filter_active",
]
