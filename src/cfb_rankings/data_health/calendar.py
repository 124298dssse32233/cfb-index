"""Verified CFB ground truth — per-year regimes + the real-FBS entity universe.

These are HISTORY, so they are hard-coded (verified read-only against the
production ``cfb_rankings.db`` and cross-checked against real CFB history across
7 rounds of spec verification — see ``wave0_data_health_spec.md`` Appendix B).

The single most important fact this file encodes: the entity universe is defined
by membership in one of the **11 real FBS conferences**, NOT by ``level_code='FBS'``
(which over-counts — 175 vs the real 134 in 2024 — because ~41 teams are parked
in a generic "FBS" conference bucket). Health contracts key off the per-season
REGIME so legitimately-weird seasons (2020 COVID) stay GREEN while real gaps
(2022 half-season, 2023 black hole) flag RED.
"""
from __future__ import annotations

import sqlite3

# --- The entity universe -------------------------------------------------

# The 11 real FBS conferences. A team_seasons row whose conference resolves to
# one of these IS FBS for that year. Verified to yield the exactly-correct
# per-year counts below.
FBS_CONFERENCES: frozenset[str] = frozenset({
    "SEC", "Big Ten", "Big 12", "ACC", "American", "Mountain West",
    "Sun Belt", "Conference USA", "Mid-American", "Pac-12", "FBS Independents",
})

# Verified exact per-year FBS member counts (real-FBS-conference members in
# team_seasons). 2023 = a real season currently MISSING from the DB. FBS grows
# year over year via realignment + FCS->FBS transitions.
EXPECTED_FBS: dict[int, int] = {
    2020: 127, 2021: 130, 2022: 131, 2023: 133, 2024: 134, 2025: 136,
}

# --- Season cadence reference --------------------------------------------

NORMAL_GAMES_PER_TEAM = 12          # regular season; +1 conference championship; +1 Hawaii rule
COVID_GAMES_PER_TEAM_FLOOR = 6      # 2020 verified median 9 (range 3-12) -> never expect 12

# CFP bracket format by season: 4-team (2014-2023) -> 12-team (2024+).
CFP_FORMAT: dict[int, str] = {
    **{y: "4team" for y in range(2014, 2024)},
    **{y: "12team" for y in range(2024, 2027)},
}

# --- Per-(dataset, season) regime ----------------------------------------
# Regime tags: 'normal' | 'covid' | 'in_progress' | 'known_missing' | 'pre_data'
# The game-spine family below is the canonical example; OFFSEASON datasets carry
# the INVERSE holes (2021-2022 missing) and declare their own seasons via
# contracts.py. Lookups fall back to a sensible default when a key is absent.

REGIME: dict[tuple[str, int], str] = {
    # game spine: 2020 COVID-reduced, 2021/2022 normal (2022 is a partial-data
    # gap caught by density, not regime), 2024 normal, 2025 current.
    ("game_spine", 2020): "covid",
    ("game_spine", 2021): "normal",
    ("game_spine", 2022): "normal",
    # 2023 is a REAL season that played and is ENTIRELY absent from the DB — the
    # "black hole" the spec ranks as the #1 RED backfill priority (Appendix B).
    # It is NOT a legitimately-acknowledged/out-of-scope gap, so it must NOT be
    # tagged 'known_missing' (which the gate exempts as not-a-fail). Tagging it
    # 'normal' makes the completeness pillar emit it as a CRITICAL FAIL (0 rows,
    # a normal season expects data present) — exactly like the 2022 half-season.
    # The 'known_missing' regime stays available for genuinely-acknowledged holes.
    ("game_spine", 2023): "normal",
    ("game_spine", 2024): "normal",
    ("game_spine", 2025): "in_progress",
}

# Seasons earlier than this are simply absent from the DB (the audit's expected
# range starts at 2014, but the DB floor is 2020).
DB_FLOOR_SEASON = 2020
CURRENT_SEASON = 2025


def regime_for(season_phase: str, season: int) -> str:
    """Regime tag for a (season_phase, season) pair, with sane fallbacks.

    Explicit REGIME entries win. Otherwise derive from the season relative to
    the DB floor / current season so a phase without a hand-coded row still gets
    a non-false-red answer:
      * < DB_FLOOR_SEASON           -> 'pre_data'
      * > CURRENT_SEASON            -> 'pre_data' (future / not yet)
      * == CURRENT_SEASON           -> 'in_progress'
      * 2020                        -> 'covid'
      * otherwise                   -> 'normal'
    """
    key = (season_phase, season)
    if key in REGIME:
        return REGIME[key]
    if season < DB_FLOOR_SEASON or season > CURRENT_SEASON:
        return "pre_data"
    if season == CURRENT_SEASON:
        return "in_progress"
    if season == 2020:
        return "covid"
    return "normal"


def cfp_format(season: int) -> str:
    """'4team' | '12team' | 'unknown' for the season's CFP bracket."""
    return CFP_FORMAT.get(season, "unknown")


def expected_fbs(season: int) -> int | None:
    """Verified FBS member count for the season, or None if unknown."""
    return EXPECTED_FBS.get(season)


def fbs_team_ids(conn: sqlite3.Connection, season: int) -> set[int]:
    """Real-FBS team_ids for a season: team_seasons rows whose conference name
    is one of FBS_CONFERENCES.

    This is the CANONICAL entity universe — do NOT substitute ``level_code='FBS'``
    (over-counts via the generic "FBS" bucket: 175 vs 134 in 2024). Returns an
    empty set if the season is absent or the join can't resolve (callers treat an
    empty universe for a season that should exist as UNKNOWN, never GREEN).

    Resilient to schema variation: the conference table / name column are
    discovered at runtime so this keeps working across migrations.
    """
    placeholders = ",".join("?" for _ in FBS_CONFERENCES)
    conf_names = tuple(FBS_CONFERENCES)

    # Discover the conferences table + its name column so we don't hard-bind to a
    # column that a migration might rename (the exact schema-drift class the
    # health spine exists to catch elsewhere).
    conf_table, name_col = _resolve_conference_name_column(conn)
    if conf_table is None or name_col is None:
        return set()

    sql = (
        f"SELECT DISTINCT ts.team_id "
        f"FROM team_seasons ts "
        f"JOIN {conf_table} c ON c.conference_id = ts.conference_id "
        f"WHERE ts.season_year = ? "
        f"AND c.{name_col} IN ({placeholders})"
    )
    try:
        rows = conn.execute(sql, (season, *conf_names)).fetchall()
    except sqlite3.Error:
        return set()
    return {int(r[0]) for r in rows if r and r[0] is not None}


def _resolve_conference_name_column(
    conn: sqlite3.Connection,
) -> tuple[str | None, str | None]:
    """Find (conference_table, name_column) at runtime.

    Looks for a table with a ``conference_id`` column plus a human-readable name
    column (one of the common spellings). Returns (None, None) if nothing fits.
    """
    try:
        tables = [
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
    except sqlite3.Error:
        return None, None

    name_candidates = ("name", "conference_name", "display_name", "short_name")
    # Prefer a table literally called 'conferences'; fall back to any table that
    # has both a conference_id and a name-ish column.
    ordered = sorted(tables, key=lambda t: (t != "conferences", t))
    for table in ordered:
        try:
            cols = {row[1] for row in conn.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()}
        except sqlite3.Error:
            continue
        if "conference_id" not in cols:
            continue
        for cand in name_candidates:
            if cand in cols:
                return table, cand
    return None, None
