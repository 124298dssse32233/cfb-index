"""Player Standing aggregator — populates `player_data['standing']`.

Builds the payload that `_render_v5_player_standing_card` (reporting.py:21040)
expects. Computes the 17-rung classification + per-award accolade streams from
existing tables — heisman_rankings_weekly, player_honors, player_season_stats.

Public API:
    build_standing_payload(db, player_id, season_year, position) -> dict | None

Returns None for unknown players. Always returns *some* shape for known
players, with empty/awaiting flags on streams that lack data so the UI can
degrade honestly.

See PLAYER_PAGE_WORLD_CLASS_BRIEF.md §7 (Player Standing) and §6 build order
items 1 (rail) and 6 (accolade tabs) for the design intent.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("cfb_rankings.player_pages.standing_aggregator")


def _query_all(db, sql, params):
    # Delegate to the project Database wrapper when present; otherwise drop
    # to raw sqlite3.Connection.execute. The hasattr check decides which path.
    if hasattr(db, "query_all"):
        return db.query_all(sql, params)  # noqa: this is the wrapper's own method
    cur = db.execute(sql, params)
    cols = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _query_one(db, sql, params):
    rows = _query_all(db, sql, params)
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Rung classification — derive 0..16 from honors + Heisman + roster
# ---------------------------------------------------------------------------

# Rung -> (label, tier_id, tier_label).
# CANONICAL ladder — matches PLAYER_PAGE_WORLD_CLASS_BRIEF.md §7.2 exactly,
# and the render-side _STANDING_RUNGS table in reporting.py. Do not diverge:
# the renderer indexes its label table by this rung number, so a mismatch
# here mislabels every player (the 2026-05-26 "All-Americans shown as
# National watch" bug came from an earlier non-canonical version of this
# table).
# Tier 0 Not-on-team, 1 2-deep, 2 Starter, 3 Recognized, 4 Elite, 5 Apex.
RUNG_TABLE: list[tuple[int, str, int, str]] = [
    (0,  "Walk-on",                       0, "Not on team"),
    (1,  "Scout team / redshirt",         0, "Not on team"),
    (2,  "Deep reserve",                  1, "2-deep"),
    (3,  "Backup",                        1, "2-deep"),
    (4,  "Rotational",                    1, "2-deep"),
    (5,  "Part-time starter",             2, "Starter"),
    (6,  "Starter",                       2, "Starter"),
    (7,  "Impact starter",                2, "Starter"),
    (8,  "Watch-list name",               3, "Recognized"),
    (9,  "All-Conference HM / 2nd team",  3, "Recognized"),
    (10, "All-Conference 1st team",       3, "Recognized"),
    (11, "National watch / fringe AA",    3, "Recognized"),
    (12, "All-American",                  4, "Elite"),
    (13, "Consensus All-American",        4, "Elite"),
    (14, "Unanimous All-American",        4, "Elite"),
    (15, "POTY finalist",                 5, "Apex"),
    (16, "POTY / Heisman winner",         5, "Apex"),
]


def _placement_signal(placement) -> str:
    """Normalize honor_team / placement values to {'first','second','third','other'}.

    Accepts None, int (1/2/3), or str ('first', '1st team', '2'). Coerces
    safely — player_honors.placement is sometimes integer in the DB.
    """
    if placement is None:
        return "other"
    if isinstance(placement, int):
        return {1: "first", 2: "second", 3: "third"}.get(placement, "other")
    s = str(placement).strip().lower()
    if "1st" in s or "first" in s or s == "1":
        return "first"
    if "2nd" in s or "second" in s or s == "2":
        return "second"
    if "3rd" in s or "third" in s or s == "3":
        return "third"
    return "other"


# NCAA-recognized All-America selectors (the canonical 5). Consensus = 3 of 5,
# Unanimous = all 5. Per brief §7.2 / §7.3 step 2.
_NCAA_AA_SELECTORS = {"AP", "AFCA", "FWAA", "WCFF", "WALTER CAMP", "SN", "SPORTING NEWS"}


def classify_rung(
    db: Any,
    player_id: int,
    season_year: int,
) -> int | None:
    """Compute the 17-rung classification — PLAYER_PAGE_WORLD_CLASS_BRIEF.md §7.3.

    Short-circuit cascade, first rule that applies wins:
      1. Official POTY: trophy winner -> R16, finalist -> R15
      2. All-America: unanimous -> R14, consensus -> R13, 1+ selector -> R12,
         fringe/midseason -> R11
      3. All-Conference: 1st -> R10, HM/2nd -> R09
      4. Watch-list -> R08
      5. Production gates (G5-safe fallback on games + usage when snap% absent):
         impact -> R07, starter -> R06, part-time -> R05, rotational -> R04,
         spot -> R03
      6. Roster-only: deep reserve -> R02, scout/redshirt -> R01, walk-on -> R00
    Returns None when no signal at all (UI renders awaiting state).
    """
    if db is None or player_id is None or season_year is None:
        return None

    # ---- Step 1: Official POTY outcomes -----------------------------------
    try:
        honors = _query_all(
            db,
            """
            SELECT honor_scope, honor_name, honor_team, placement, selector,
                   consensus_flag, unanimous_flag
            FROM player_honors
            WHERE player_id = :pid AND season_year = :s
            """,
            {"pid": player_id, "s": season_year},
        )
    except Exception:
        honors = []
    honors = honors or []

    for h in honors:
        name = (h.get("honor_name") or "").lower()
        plc = str(h.get("placement") or h.get("honor_team") or "").lower()
        # Trophy winner: a position/POTY award (not All-* team) marked winner.
        is_award = ("award" in name or "trophy" in name or "heisman" in name
                    or "player of the year" in name)
        if is_award and ("winner" in name or plc == "winner"):
            return 16
        if is_award and "finalist" in plc:
            return 15

    # Heisman model nowcast as a POTY-finalist proxy (model rank, not ballot):
    # top-5 model rank -> finalist tier R15; top-25 -> watch-list R08 (handled
    # later only if nothing higher fires). We DON'T promote model #1 to R16 —
    # that requires a confirmed trophy honor above.
    heisman_rank = None
    try:
        r = _query_one(
            db,
            "SELECT MIN(rank_overall) AS r FROM heisman_rankings_weekly "
            "WHERE player_id = :pid AND season_year = :s AND rank_overall IS NOT NULL",
            {"pid": player_id, "s": season_year},
        )
        if r and r.get("r"):
            heisman_rank = int(r["r"])
    except Exception:
        pass
    if heisman_rank is not None and heisman_rank <= 5:
        return 15

    # ---- Step 2: All-America outcomes -------------------------------------
    aa_first_selectors: set[str] = set()
    any_aa = False
    any_aa_nonfirst = False
    consensus_flag = False
    unanimous_flag = False
    has_conf_first = False
    has_conf_hm_second = False
    has_watchlist = False

    for h in honors:
        scope = (h.get("honor_scope") or "").lower()
        placement = _placement_signal(h.get("placement") or h.get("honor_team"))
        selector = str(h.get("selector") or "").strip().upper()
        name = (h.get("honor_name") or "").lower()
        if h.get("consensus_flag") or selector == "CONSENSUS":
            consensus_flag = True
        if h.get("unanimous_flag"):
            unanimous_flag = True
        if "watch" in name:
            has_watchlist = True
        if scope == "all_america":
            any_aa = True
            if placement == "first":
                if selector in _NCAA_AA_SELECTORS:
                    aa_first_selectors.add(selector)
            else:
                any_aa_nonfirst = True
        elif scope == "all_conference":
            if placement == "first":
                has_conf_first = True
            elif placement in ("second", "third", "other"):
                has_conf_hm_second = True

    n_first = len(aa_first_selectors)
    if unanimous_flag or n_first >= 5:
        return 14   # Unanimous All-American
    if consensus_flag or n_first >= 3:
        return 13   # Consensus All-American
    if n_first >= 1:
        return 12   # All-American (1+ NCAA-recognized selector)
    if any_aa or any_aa_nonfirst:
        return 11   # National watch / fringe All-America (non-NCAA or 2nd/3rd)

    # ---- Step 3: All-Conference outcomes ----------------------------------
    if has_conf_first:
        return 10
    if has_conf_hm_second:
        return 9

    # ---- Step 4: Watch-list / preseason -----------------------------------
    if has_watchlist or (heisman_rank is not None and heisman_rank <= 25):
        return 8

    # ---- Step 5: Production gates (G5-safe games+usage fallback) ----------
    # Snap% from PBP isn't reliably available, so we approximate with
    # games_played + total opportunities (the brief sanctions this fallback).
    try:
        row = _query_one(
            db,
            """
            SELECT MAX(games_played) AS gp, MAX(passing_attempts) AS pa,
                   MAX(rushing_attempts) AS ra, MAX(receiving_targets) AS rt
            FROM player_season_stats
            WHERE player_id = :pid AND season_year = :s
            """,
            {"pid": player_id, "s": season_year},
        ) or {}
        gp = int(row.get("gp") or 0)
        usage = (int(row.get("pa") or 0) + int(row.get("ra") or 0) + int(row.get("rt") or 0))
        if gp >= 11 and usage >= 250:
            return 7      # Impact starter
        if gp >= 10 and usage >= 120:
            return 6      # Starter
        if gp >= 7 and usage >= 50:
            return 5      # Part-time starter
        if gp >= 4 and usage >= 15:
            return 4      # Rotational
        if gp >= 1:
            return 3      # Spot / situational
    except Exception:
        pass

    return None  # No signal — UI renders awaiting state


# ---------------------------------------------------------------------------
# Narratives — generated from the cascade above
# ---------------------------------------------------------------------------

# Narratives keyed to the CANONICAL §7.2 ladder.
_RUNG_NARRATIVES: dict[int, dict[str, str]] = {
    16: {
        "why_here": "National Player-of-the-Year / Heisman winner — the season's defining player.",
        "moves_up": "Already at the ceiling; the trophy is in the case.",
        "moves_down": "Subsequent seasons reset to projection — this rung is forever for the trophy year.",
    },
    15: {
        "why_here": "National Player-of-the-Year finalist — invited to the closing-night ceremony.",
        "moves_up": "Win the award on Saturday in December.",
        "moves_down": "A late slump or title-game letdown drops the finish out of the finalist set.",
    },
    14: {
        "why_here": "Unanimous All-American — 1st team on all five NCAA-recognized selectors.",
        "moves_up": "The only step up is a Player-of-the-Year invite.",
        "moves_down": "Losing a selector drops this to Consensus.",
    },
    13: {
        "why_here": "Consensus All-American — 1st team on at least three of the five NCAA selectors.",
        "moves_up": "Sweep the remaining selectors for Unanimous status.",
        "moves_down": "Fall below three selectors and this returns to plain All-American.",
    },
    12: {
        "why_here": "All-American — named 1st team by at least one NCAA-recognized selector.",
        "moves_up": "Add selectors to reach Consensus (3 of 5).",
        "moves_down": "Lose the selector and this slips to national-watch territory.",
    },
    11: {
        "why_here": "National watch / fringe All-American — on the edge of a 1st-team nod.",
        "moves_up": "Convert a fringe mention into a 1st-team NCAA-selector All-American spot.",
        "moves_down": "A quiet close drops this back to the conference honors.",
    },
    10: {
        "why_here": "All-Conference 1st team — among the conference's best at the position.",
        "moves_up": "A national All-America nod is the next jump.",
        "moves_down": "A quiet stretch returns this to HM / 2nd-team consideration.",
    },
    9: {
        "why_here": "All-Conference honorable mention / 2nd team — the recognition has started.",
        "moves_up": "A best-at-position run lifts to 1st team.",
        "moves_down": "A back-end conference finish drops out of the honor list.",
    },
    8: {
        "why_here": "Watch-list name — on at least one major award watch list, no hardware yet.",
        "moves_up": "Convert watch-list status into an All-Conference or All-America nod.",
        "moves_down": "Watch lists get pruned as the season progresses.",
    },
    7: {
        "why_here": "Impact starter — above-average production for the conference.",
        "moves_up": "A signature stretch puts this player on award watch lists.",
        "moves_down": "Regression to the mean returns this to plain-starter territory.",
    },
    6: {
        "why_here": "Starter — over 60% of the snaps, holding the job.",
        "moves_up": "A production leap lifts into impact-starter territory.",
        "moves_down": "Lose snap share and this slips to a part-time role.",
    },
    5: {
        "why_here": "Part-time starter — splitting the role or filling in on injury.",
        "moves_up": "Win the job outright for a full starter rung.",
        "moves_down": "Return to a rotational package role.",
    },
    4: {
        "why_here": "Rotational — a 15-40% snap-share package player.",
        "moves_up": "Earn a larger role to climb to part-time starter.",
        "moves_down": "Drop back to spot duty as depth strengthens.",
    },
    3: {
        "why_here": "Spot / situational — on the gameday roster with limited snaps.",
        "moves_up": "Earn rotation reps to climb the 2-deep.",
        "moves_down": "Roster moves can shift this back to deep reserve.",
    },
    2: {
        "why_here": "Deep reserve — rostered, no meaningful snaps yet.",
        "moves_up": "Win a package role in fall camp.",
        "moves_down": "Roster churn sets the floor.",
    },
    1: {
        "why_here": "Scout team / redshirt development — building toward the 2-deep.",
        "moves_up": "Earn gameday-roster reps.",
        "moves_down": "Redshirt-year reality sets the floor.",
    },
    0: {
        "why_here": "Walk-on (preferred / recruited / invited). The starting block is honest.",
        "moves_up": "Snap counts and special-teams reps are the leading indicators.",
        "moves_down": "Walk-on policies set the floor.",
    },
}


def narratives_for_rung(rung: int | None) -> dict[str, str]:
    if rung is None:
        return {
            "why_here": "Standing classification populates when honors, Heisman, and roster signals all align.",
            "moves_up": "",
            "moves_down": "",
        }
    return _RUNG_NARRATIVES.get(int(rung), _RUNG_NARRATIVES[0])


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_standing_payload(
    db: Any,
    player_id: int | None,
    season_year: int | None,
    position: str | None,
) -> dict[str, Any] | None:
    """Build the standing payload for _render_v5_player_standing_card."""
    if db is None or player_id is None or season_year is None:
        return None

    # Lazy import to avoid module-load-time circular ref via player_pages.__init__.
    from .accolade_streams import build_accolade_streams_for_position

    current_rung = classify_rung(db, int(player_id), int(season_year))
    last_rung = classify_rung(db, int(player_id), int(season_year) - 1)

    streams = build_accolade_streams_for_position(
        db,
        player_id=int(player_id),
        season_year=int(season_year),
        position=position or "",
    )

    return {
        "current_rung_id": current_rung,
        "last_season_rung_id": last_rung,
        "narratives": narratives_for_rung(current_rung),
        "accolade_streams": streams,
        # Convenience for the legacy renderer which already references these
        "standing_rung": current_rung,
    }


__all__ = [
    "build_standing_payload",
    "classify_rung",
    "narratives_for_rung",
    "RUNG_TABLE",
]
