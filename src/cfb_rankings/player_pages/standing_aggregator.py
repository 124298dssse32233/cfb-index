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
    if hasattr(db, "query_all"):
        return _query_all(db,sql, params)
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
# Tier 1 floor, 2 established, 3 quality starter, 4 all-conf, 5 nat'l recog, 6 nat'l honors.
RUNG_TABLE: list[tuple[int, str, int, str]] = [
    (0,  "Walk-on",                    1, "Floor"),
    (1,  "Backup",                     1, "Floor"),
    (2,  "Rotation",                   1, "Floor"),
    (3,  "Starter",                    2, "Established"),
    (4,  "Regular contributor",        2, "Established"),
    (5,  "Solid starter",              3, "Quality starter"),
    (6,  "Quality starter",            3, "Quality starter"),
    (7,  "All-Conference 2nd team",    4, "All-Conference"),
    (8,  "All-Conference 1st team",    4, "All-Conference"),
    (9,  "All-American 3rd team",      5, "National recognition"),
    (10, "All-American 2nd team",      5, "National recognition"),
    (11, "All-American 1st team",      5, "National recognition"),
    (12, "Position-of-the-Year",       6, "National honors"),
    (13, "Watch-list honoree",         6, "National honors"),
    (14, "POTY finalist",              6, "National honors"),
    (15, "Heisman finalist",           6, "National honors"),
    (16, "Heisman winner",             6, "National honors"),
]


def _placement_signal(placement: str | None) -> str:
    """Normalize honor_team / placement strings to {'first','second','third','other'}."""
    s = (placement or "").lower()
    if "1st" in s or "first" in s or s == "1":
        return "first"
    if "2nd" in s or "second" in s or s == "2":
        return "second"
    if "3rd" in s or "third" in s or s == "3":
        return "third"
    return "other"


def classify_rung(
    db: Any,
    player_id: int,
    season_year: int,
) -> int | None:
    """Compute the 17-rung classification for a player+season.

    Cascade: Heisman finals > All-America 1st/2nd/3rd > POTY finalist >
    Watch-list > All-Conference 1st/2nd > stat-based rotation tiers >
    walk-on baseline. Returns None if not enough signal exists yet.
    """
    if db is None or player_id is None or season_year is None:
        return None

    # 1. Heisman tier (R15/R16) — final ballot finish
    try:
        r = _query_one(db,
            "SELECT MIN(rank_overall) AS r FROM heisman_rankings_weekly "
            "WHERE player_id = :pid AND season_year = :s AND rank_overall IS NOT NULL",
            {"pid": player_id, "s": season_year},
        )
        if r and r.get("r"):
            rank = int(r["r"])
            if rank == 1:
                return 16          # Heisman winner
            if rank <= 5:
                return 15          # Heisman finalist (top 5 in voting)
            if rank <= 25:
                return 13          # Watch-list rung
    except Exception:
        pass

    # 2. Honor-based rungs (R9-R14 + R7-R8)
    try:
        honors = _query_all(db,
            """
            SELECT honor_scope, honor_name, honor_team, placement, consensus_flag
            FROM player_honors
            WHERE player_id = :pid AND season_year = :s
            """,
            {"pid": player_id, "s": season_year},
        )
    except Exception:
        honors = []

    has_aa_first = False
    has_aa_second = False
    has_aa_third = False
    has_poty_finalist = False
    has_watchlist = False
    has_conf_first = False
    has_conf_second = False

    for h in honors or []:
        scope = (h.get("honor_scope") or "").lower()
        placement = _placement_signal(h.get("placement") or h.get("honor_team"))
        name = (h.get("honor_name") or "").lower()
        # Position-of-the-Year markers
        if "winner" in name and "finalist" not in name:
            return 12  # POTY winner sits at rung 12
        if "finalist" in name:
            has_poty_finalist = True
        if "watch" in name or "watchlist" in name:
            has_watchlist = True
        if scope == "all_america":
            if placement == "first":
                has_aa_first = True
            elif placement == "second":
                has_aa_second = True
            elif placement == "third":
                has_aa_third = True
        elif scope == "all_conference":
            if placement == "first":
                has_conf_first = True
            elif placement == "second":
                has_conf_second = True

    if has_aa_first:
        return 11
    if has_aa_second:
        return 10
    if has_aa_third:
        return 9
    if has_poty_finalist:
        return 14
    if has_watchlist:
        return 13
    if has_conf_first:
        return 8
    if has_conf_second:
        return 7

    # 3. Stat-based rotation tiers (R3-R6) — derive from games-played
    # heuristics. Conservative: enough snaps in season_stats = starter.
    try:
        row = _query_one(db,
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
        if gp >= 11 and usage >= 200:
            return 5      # Solid starter
        if gp >= 9 and usage >= 80:
            return 4      # Regular contributor
        if gp >= 6 and usage >= 30:
            return 3      # Starter
        if gp >= 4:
            return 2      # Rotation
        if gp >= 1:
            return 1      # Backup
    except Exception:
        pass

    return None  # Unknown — render UI in awaiting state


# ---------------------------------------------------------------------------
# Narratives — generated from the cascade above
# ---------------------------------------------------------------------------

_RUNG_NARRATIVES: dict[int, dict[str, str]] = {
    16: {
        "why_here": "Won the Heisman Trophy — the season's defining player at the position.",
        "moves_up": "Already at the ceiling. A second Heisman would be without modern precedent.",
        "moves_down": "Subsequent seasons reset to projection; this rung is forever for the trophy year.",
    },
    15: {
        "why_here": "Heisman finalist — top 5 in the closing-night ballot.",
        "moves_up": "Win the trophy on Saturday in December.",
        "moves_down": "A late-season slump or championship-game letdown drops the finish into top-10 watch territory.",
    },
    14: {
        "why_here": "Named POTY finalist — among three nationally for the position award.",
        "moves_up": "Win the position award or punch a Heisman-finalist invite.",
        "moves_down": "Miss the closing weekend window with a quiet November.",
    },
    13: {
        "why_here": "Multiple major-award watch lists — national writers are watching.",
        "moves_up": "Convert watch-list status into a finalist invite.",
        "moves_down": "Watch-lists get pruned as the season progresses.",
    },
    12: {
        "why_here": "Won a Position-of-the-Year award — best at the position nationally.",
        "moves_up": "Add a Heisman finalist invite to the trophy case.",
        "moves_down": "Subsequent seasons reset to projection.",
    },
    11: {
        "why_here": "All-American 1st team — elite-tier national recognition.",
        "moves_up": "Climb into POTY finalist or Heisman watch territory.",
        "moves_down": "Drop to 2nd team if peer-rank slips on the closing weekends.",
    },
    10: {
        "why_here": "All-American 2nd team — among the country's best at the position.",
        "moves_up": "Top-of-position production in November lifts to 1st team.",
        "moves_down": "Slip to 3rd team or just All-Conference if the resume thins.",
    },
    9: {
        "why_here": "All-American 3rd team — national recognition has arrived.",
        "moves_up": "Sustain elite per-game value into November to climb the AA tiers.",
        "moves_down": "Drop to All-Conference if signature wins or stats fade.",
    },
    8: {
        "why_here": "All-Conference 1st team — among the conference's best at the position.",
        "moves_up": "An All-American nod takes the next jump.",
        "moves_down": "Quiet stretch returns this to 2nd-team consideration.",
    },
    7: {
        "why_here": "All-Conference 2nd team — the recognition has started.",
        "moves_up": "Best-at-position run in November lifts to 1st team.",
        "moves_down": "A back-end conference finish drops out of the honor list.",
    },
    6: {
        "why_here": "Quality starter producing measurable value above replacement.",
        "moves_up": "Sustain per-game production into the All-Conference watch.",
        "moves_down": "Injuries or platoon situations cap the trajectory.",
    },
    5: {
        "why_here": "Solid starter — the kind of player every program builds around.",
        "moves_up": "A breakout statistical run lifts into Quality-Starter / All-Conference territory.",
        "moves_down": "Lose the starting nod to depth competition.",
    },
    4: {
        "why_here": "Regular contributor on a competitive roster. Quietly productive.",
        "moves_up": "Earn the full-time starting role.",
        "moves_down": "Snap share drifts back to rotation as depth strengthens.",
    },
    3: {
        "why_here": "Starting role secured. Year-over-year improvement is the next bet.",
        "moves_up": "A statistical leap turns starter snaps into Solid-Starter trajectory.",
        "moves_down": "Lose snaps to a transfer or freshman.",
    },
    2: {
        "why_here": "Earned snaps in the rotation. Pushing for the starting nod.",
        "moves_up": "Win the depth-chart battle through camp.",
        "moves_down": "Drop back to the backup tier if rotation snaps thin.",
    },
    1: {
        "why_here": "Snap-by-snap rotation player. Working on the next step.",
        "moves_up": "Earn rotation reps in fall camp.",
        "moves_down": "Roster moves can shift this back to the floor.",
    },
    0: {
        "why_here": "Roster reality. The starting block is honest.",
        "moves_up": "Snap counts and special-teams reps are the leading indicators.",
        "moves_down": "Roster cuts and walk-on policies set the floor.",
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
