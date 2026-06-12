"""Declarative dataset contracts — one per spine + offseason dataset.

THE central refinement (round 6 of spec verification): **there is no one
"missing 2023" rule.** Each data domain has its OWN expected-season set. A naive
global expectation would be wrong for half the tables. So every contract carries
its own ``expected_seasons`` frozenset; the completeness gate diffs *actual vs
that dataset's expectation*, tagged by the per-season REGIME in ``calendar``.

All column / table / grain names below are VERIFIED real names from the live DB
(council guessed several wrong; see spec "Verified repo facts"). This module is
data-only — the checks that consume these contracts live in ``checks/``.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DatasetContract:
    """The checked-in spec for one dataset's health expectations.

    Fields:
      name              human / check label.
      table             real DB table name.
      grain             columns forming the unique key (verified unique on the spine).
      required_non_null required columns whose null density is watched.
      parents           FK edges as (fk_col, parent_table, parent_col) for orphan anti-joins.
      expected_seasons  THIS dataset's own season set (NOT a global range).
      season_phase      which REGIME family in calendar.REGIME (drives covid/missing tagging).
      density           optional {"per": col, "min_normal": float, "min_covid": float}.
      allowed_values    optional {col: frozenset(values)} for categorical validity.
      zero_row_policy   'required' | 'deferred' | 'out_of_scope' (round-7 open question).
      severity          default severity for failures against this contract.
    """
    name: str
    table: str
    grain: tuple[str, ...]
    required_non_null: tuple[str, ...]
    parents: tuple[tuple[str, str, str], ...]
    expected_seasons: frozenset[int]
    season_phase: str
    density: dict | None = None
    allowed_values: dict | None = None
    zero_row_policy: str = "required"
    severity: str = "critical"


# === GAME SPINE ===========================================================
# Years present 2020,2021,2022*,2024,2025 ; 2023 missing, 2022 partial.
# Expected 2020-2025. season_phase='game_spine' so 2020=covid / 2023=known_missing.
_SPINE_SEASONS = frozenset(range(2020, 2026))  # 2020..2025

GAMES = DatasetContract(
    name="games",
    table="games",
    grain=("game_id",),
    required_non_null=("game_id", "season_year", "home_team_id", "away_team_id"),
    parents=(
        ("home_team_id", "teams", "team_id"),
        ("away_team_id", "teams", "team_id"),
    ),
    expected_seasons=_SPINE_SEASONS,
    season_phase="game_spine",
    # home-games-per-team density catches 2022 (max 6/team -> half-empty though
    # all teams present). Covid floor 3.0 lets 2020 pass.
    density={"per": "home_team_id", "min_normal": 5.5, "min_covid": 3.0},
    severity="critical",
)

PLAYER_GAME_STATS = DatasetContract(
    name="player_game_stats",
    table="player_game_stats",
    grain=("player_game_stat_id",),
    required_non_null=("game_id", "player_id", "team_id", "category", "stat_type"),
    parents=(
        ("game_id", "games", "game_id"),
        ("player_id", "players", "player_id"),
        ("team_id", "teams", "team_id"),
    ),
    expected_seasons=_SPINE_SEASONS,
    season_phase="game_spine",
    severity="critical",
)

ROSTER_ENTRIES = DatasetContract(
    name="roster_entries",
    table="roster_entries",
    grain=("roster_entry_id",),
    required_non_null=("player_id", "team_id", "season_year"),
    parents=(
        ("player_id", "players", "player_id"),
        ("team_id", "teams", "team_id"),
    ),
    # VERIFIED: rosters effectively exist only for 2024-2025 (2020=14 teams,
    # 2021-2023 missing). The contract still EXPECTS the full spine range so the
    # gap flags; the regime tags 2023 known_missing.
    expected_seasons=_SPINE_SEASONS,
    season_phase="game_spine",
    severity="critical",
)

POWER_RATINGS_WEEKLY = DatasetContract(
    name="power_ratings_weekly",
    table="power_ratings_weekly",
    grain=("power_rating_weekly_id",),  # verified real PK (singular 'rating')
    required_non_null=("team_id", "season_year"),
    parents=(("team_id", "teams", "team_id"),),
    # VERIFIED present 2020,2021,2024,2025 -> missing 2022 + 2023. Expect the
    # full spine; gate diffs against this.
    expected_seasons=_SPINE_SEASONS,
    season_phase="game_spine",
    severity="critical",
)

OFFICIAL_RANKINGS = DatasetContract(
    name="official_rankings",
    table="official_rankings",
    grain=("official_ranking_id",),  # verified real PK (singular 'ranking')
    required_non_null=("team_id", "season_year", "week"),  # verified col is 'week'
    parents=(("team_id", "teams", "team_id"),),
    # VERIFIED 2020,2021,2024,2025 present (AP/Coaches/CFP per week); 2022+2023 missing.
    expected_seasons=_SPINE_SEASONS,
    season_phase="game_spine",
    severity="critical",
)

SPINE_CONTRACTS: tuple[DatasetContract, ...] = (
    GAMES, PLAYER_GAME_STATS, ROSTER_ENTRIES, POWER_RATINGS_WEEKLY, OFFICIAL_RANKINGS,
)


# === OFFSEASON SET ========================================================
# Each declares its OWN expected_seasons per the round-6 per-dataset table.
# season_phase='offseason' so these are judged outside the game-spine regime.

# recruiting / returning / talent: present 2020,2023,2024,2025 ; 2021-2022 missing.
_OFFSEASON_CORE_SEASONS = frozenset({2020, 2021, 2022, 2023, 2024, 2025})

RECRUITING_ENTRIES = DatasetContract(
    name="recruiting_entries",
    table="recruiting_entries",
    grain=("recruiting_entry_id",),
    required_non_null=("team_id", "season_year"),
    parents=(("team_id", "teams", "team_id"),),
    expected_seasons=_OFFSEASON_CORE_SEASONS,   # 2021,2022 are the known holes
    season_phase="offseason",
    severity="warning",
)

RETURNING_PRODUCTION = DatasetContract(
    name="returning_production",
    table="returning_production",
    grain=("returning_production_id",),
    required_non_null=("team_id", "season_year"),
    parents=(("team_id", "teams", "team_id"),),
    expected_seasons=_OFFSEASON_CORE_SEASONS,   # 2021,2022 missing
    season_phase="offseason",
    severity="warning",
)

TEAM_TALENT_SNAPSHOTS = DatasetContract(
    name="team_talent_snapshots",
    table="team_talent_snapshots",
    grain=("team_talent_snapshot_id",),
    required_non_null=("team_id", "season_year"),
    parents=(("team_id", "teams", "team_id"),),
    expected_seasons=_OFFSEASON_CORE_SEASONS,   # 2021,2022 missing
    season_phase="offseason",
    severity="warning",
)

# transfers: portal era ~2021+ ; DB present 2023-2026 -> pre-2023 missing.
TRANSFER_ENTRIES = DatasetContract(
    name="transfer_entries",
    table="transfer_entries",
    grain=("transfer_entry_id",),
    required_non_null=("player_id", "season_year"),
    parents=(("player_id", "players", "player_id"),),
    expected_seasons=frozenset({2021, 2022, 2023, 2024, 2025, 2026}),
    season_phase="offseason",
    severity="warning",
)

# NFL draft: CLAUDE.md claims 2018-2025 (STALE) ; DB has only 2024,2025,2026.
# Expectation encodes the doc claim so the doc-vs-reality drift flags.
PLAYER_NFL_DRAFT = DatasetContract(
    name="player_nfl_draft",
    table="player_nfl_draft",
    grain=("player_nfl_draft_id",),
    # season column is 'draft_year' on this table (NOT season_year) — verified.
    required_non_null=("player_id", "draft_year"),
    parents=(("player_id", "players", "player_id"),),
    expected_seasons=frozenset(range(2018, 2027)),  # 2018..2026; 2018-2023 missing
    season_phase="offseason",
    severity="warning",
)

# honors: present 2024,2025 only ; multi-year expected.
PLAYER_HONORS = DatasetContract(
    name="player_honors",
    table="player_honors",
    grain=("player_honor_id",),  # verified real PK (singular 'honor')
    required_non_null=("player_id", "season_year"),
    parents=(("player_id", "players", "player_id"),),
    expected_seasons=frozenset(range(2020, 2026)),  # 2020..2025; pre-2024 missing
    season_phase="offseason",
    severity="warning",
)

# heisman weekly: a single snapshot present ONLY 2020,2024 ; feeds /film-room/.
HEISMAN_RANKINGS_WEEKLY = DatasetContract(
    name="heisman_rankings_weekly",
    table="heisman_rankings_weekly",
    grain=("heisman_ranking_id",),  # verified real PK (singular 'ranking')
    required_non_null=("player_id", "season_year"),
    parents=(("player_id", "players", "player_id"),),
    expected_seasons=frozenset(range(2020, 2026)),  # 2021,2022,2023,2025 missing
    season_phase="offseason",
    severity="warning",
)

OFFSEASON_CONTRACTS: tuple[DatasetContract, ...] = (
    RECRUITING_ENTRIES, RETURNING_PRODUCTION, TEAM_TALENT_SNAPSHOTS,
    TRANSFER_ENTRIES, PLAYER_NFL_DRAFT, PLAYER_HONORS, HEISMAN_RANKINGS_WEEKLY,
)


# === Registry =============================================================
ALL_CONTRACTS: tuple[DatasetContract, ...] = SPINE_CONTRACTS + OFFSEASON_CONTRACTS

CONTRACTS_BY_NAME: dict[str, DatasetContract] = {c.name: c for c in ALL_CONTRACTS}


def get(name: str) -> DatasetContract:
    """Look up a contract by dataset name (raises KeyError if absent)."""
    return CONTRACTS_BY_NAME[name]
