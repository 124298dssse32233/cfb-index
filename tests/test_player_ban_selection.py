"""BAN selection — the tier model + achievement candidate pool (doc 41 §6).

These pin the brand hierarchy that ``_select_ban`` must enforce STRUCTURALLY so
the BAN never monopolizes on one register:

    national distinction > proprietary production (WEPA) > national volume >
    pedigree (recruiting) > team-relative leader

Pure-unit + an in-memory SQLite driving the real ``_select_ban`` (no live DB).
"""
from __future__ import annotations

import sqlite3

import pytest

from cfb_rankings.player_pages import story_card as sc


# --------------------------------------------------------------------------- #
# Pure parsers
# --------------------------------------------------------------------------- #
def test_paren_number_pulls_last_group():
    assert sc._paren_number("Team leader in rushing yards (775).") == "775"
    assert sc._paren_number("Two (a) groups (1,928) here") == "1,928"
    assert sc._paren_number("no parens here") is None
    assert sc._paren_number(None) is None


def test_volume_bar_reads_the_detector_words():
    ctx = "3195 passing yards — clears the 2,500-QB volume bar."
    assert sc._volume_bar(ctx) == "2,500"
    assert sc._volume_bar("1649 rushing yards — clears the 1,200-RB volume bar.") == "1,200"
    assert sc._volume_bar("no marker") is None
    assert sc._volume_bar(None) is None


# --------------------------------------------------------------------------- #
# Tier ordering invariant — the whole hierarchy rides on this
# --------------------------------------------------------------------------- #
def test_tier_priority_ordering():
    assert (
        sc._BAN_T_NATIONAL
        < sc._BAN_T_PRODUCTION
        < sc._BAN_T_VOLUME
        < sc._BAN_T_PEDIGREE
        < sc._BAN_T_TEAM
    )


# --------------------------------------------------------------------------- #
# _achievement_ban mapping
# --------------------------------------------------------------------------- #
def test_money_efficiency_is_national_rank_ban():
    row = {
        "achievement_id": "achievement_money_efficiency",
        "season_year": 2025,
        "unlock_context": "#1 YPA at 10.00 among qualified QBs.",
        "rarity_pct": 0.11,
        "meta_json": '{"rank":1,"ypa":10.0}',
    }
    tier, score, ban = sc._achievement_ban(row, 2025)
    assert tier == sc._BAN_T_NATIONAL
    assert ban.number == "No.1"
    assert "Y/A" in ban.label and "QUALIFIED QBs" in ban.label
    assert ban.kind == "rank"
    assert ban.receipt.table == "player_achievements"
    # rank 5 scores below rank 1 (surprise decays with rank)
    row5 = {**row, "meta_json": '{"rank":5,"ypa":9.0}'}
    _, score5, _ = sc._achievement_ban(row5, 2025)
    assert score5 < score


def test_volume_king_is_volume_tier_with_club_label():
    row = {
        "achievement_id": "achievement_volume_king",
        "season_year": 2025,
        "unlock_context": "3195 passing yards — clears the 2,500-QB volume bar.",
        "rarity_pct": 1.56,
        "meta_json": '{"position":"QB","metric":"passing_yds","value":3195.0}',
    }
    tier, _score, ban = sc._achievement_ban(row, 2025)
    assert tier == sc._BAN_T_VOLUME
    assert ban.number == "3,195"
    assert ban.label == "PASS YDS · 2,500-YD CLUB"
    assert ban.kind == "magnitude"


def test_receiving_volume_king_label_is_rec_not_rece():
    row = {
        "achievement_id": "achievement_volume_king",
        "season_year": 2025,
        "unlock_context": "1033 receiving yards — clears the 900-WR volume bar.",
        "rarity_pct": 1.3,
        "meta_json": '{"position":"WR","metric":"receiving_yds","value":1033.0}',
    }
    _tier, _score, ban = sc._achievement_ban(row, 2025)
    assert ban.label == "REC YDS · 900-YD CLUB"


def test_program_benchmark_is_team_tier_last_resort():
    row = {
        "achievement_id": "achievement_program_benchmark",
        "season_year": 2025,
        "unlock_context": "Team leader in rushing yards (775).",
        "rarity_pct": 5.53,
        "meta_json": '{"team_id":13,"position":"QB","metric":"rushing yards"}',
    }
    tier, _score, ban = sc._achievement_ban(row, 2025)
    assert tier == sc._BAN_T_TEAM
    assert ban.number == "775"
    assert "LEADER" in ban.label


def test_honors_badge_is_not_a_ban():
    """Honors are categorical (no honest single number) -> selector grid, not BAN."""
    row = {
        "achievement_id": "achievement_honors_badge",
        "season_year": 2025,
        "unlock_context": "Recognized on: All-America (AFCA).",
        "rarity_pct": 0.7,
        "meta_json": '{"honor":"All-America (AFCA)"}',
    }
    assert sc._achievement_ban(row, 2025) is None


def test_recency_decays_prior_season():
    base = {
        "achievement_id": "achievement_money_efficiency",
        "unlock_context": "#1 YPA at 10.00 among qualified QBs.",
        "rarity_pct": 0.11,
        "meta_json": '{"rank":1,"ypa":10.0}',
    }
    _, cur, _ = sc._achievement_ban({**base, "season_year": 2025}, 2025)
    _, old, _ = sc._achievement_ban({**base, "season_year": 2024}, 2025)
    assert old < cur


# --------------------------------------------------------------------------- #
# _select_ban end-to-end via in-memory SQLite
# --------------------------------------------------------------------------- #
class _MemDB:
    """Minimal Database-like wrapper exposing query_one/query_all over sqlite."""

    def __init__(self):
        self.c = sqlite3.connect(":memory:")
        self.c.row_factory = sqlite3.Row
        self.c.executescript(
            """
            create table player_aura_weekly(
              player_id int, season_year int, week int,
              perception_pctl real, production_pctl real,
              cohort_size int, production_plays int);
            create table player_value_metrics(
              player_id int, season_year int, metric_name text,
              metric_value real, plays int);
            create table player_recruiting_profiles(
              player_id int, season_year int, stars int, rating real, national_rank int);
            create table player_achievements(
              player_id int, season_year int, achievement_id text,
              unlock_context text, rarity_pct real, meta_json text);
            create table player_game_stats(
              player_id int, season_year int, week int, season_type text,
              category text, stat_type text, stat_value_num real);
            """
        )

    def query_one(self, sql, params):
        r = self.c.execute(sql, params).fetchone()
        return dict(r) if r else None

    def query_all(self, sql, params):
        return [dict(r) for r in self.c.execute(sql, params).fetchall()]

    def add_aura(self, pid, gap, cohort=50, plays=200, season=2025):
        # gap = production - perception; centre on 50.
        self.c.execute(
            "insert into player_aura_weekly values(?,?,?,?,?,?,?)",
            (pid, season, 1, 50 - gap / 2, 50 + gap / 2, cohort, plays),
        )

    def add_wepa(self, pid, val, season=2025, plays=200):
        self.c.execute(
            "insert into player_value_metrics values(?,?,?,?,?)",
            (pid, season, "wepa_passing", val, plays),
        )

    def add_recruit(self, pid, nat, stars=5, season=2023):
        self.c.execute(
            "insert into player_recruiting_profiles values(?,?,?,?,?)",
            (pid, season, stars, 0.99, nat),
        )

    def add_ach(self, pid, aid, ctx, rarity, meta, season=2025):
        self.c.execute(
            "insert into player_achievements values(?,?,?,?,?,?)",
            (pid, season, aid, ctx, rarity, meta),
        )

    def add_games(self, pid, category, yards_by_week, season=2025):
        """yards_by_week: list of per-week yardage totals (week index from 1)."""
        for wk, yds in enumerate(yards_by_week, start=1):
            self.c.execute(
                "insert into player_game_stats values(?,?,?,?,?,?,?)",
                (pid, season, wk, "regular", category, "YDS", yds),
            )


def test_national_achievement_beats_moderate_aura_gap():
    db = _MemDB()
    db.add_aura(1, gap=16)  # moderate -> PRODUCTION tier
    db.add_ach(1, "achievement_money_efficiency",
               "#1 YPA at 10.00 among qualified QBs.", 0.11, '{"rank":1,"ypa":10.0}')
    ban = sc._select_ban(db, 1, 2025, "QB")
    assert ban.receipt.table == "player_achievements"
    assert ban.number == "No.1"


def test_extreme_aura_gap_stays_national_and_wins_over_wepa():
    db = _MemDB()
    db.add_aura(1, gap=40)          # extreme -> NATIONAL tier
    db.add_wepa(1, 0.55)            # strong WEPA but only PRODUCTION tier
    ban = sc._select_ban(db, 1, 2025, "QB")
    assert ban.receipt.table == "player_aura_weekly"


def test_wepa_moat_beats_vanilla_volume():
    db = _MemDB()
    db.add_wepa(1, 0.30)           # modest WEPA, PRODUCTION tier
    db.add_ach(1, "achievement_volume_king",
               "3195 passing yards — clears the 2,500-QB volume bar.",
               1.56, '{"position":"QB","metric":"passing_yds","value":3195.0}')
    ban = sc._select_ban(db, 1, 2025, "QB")
    # Even a modest proprietary metric outranks a vanilla counting total.
    assert ban.receipt.table == "player_value_metrics"


def test_pedigree_only_wins_for_unproven_player():
    db = _MemDB()
    db.add_recruit(1, nat=4, stars=5)   # blue-chip, but no production signal
    ban = sc._select_ban(db, 1, 2025, "WR")
    assert ban.receipt.table == "player_recruiting_profiles"
    assert ban.number == "No.4"


def test_production_overrides_stale_pedigree():
    db = _MemDB()
    db.add_recruit(1, nat=20, stars=5)   # was a 5-star
    db.add_wepa(1, 0.21)                 # but has actually played
    ban = sc._select_ban(db, 1, 2025, "QB")
    assert ban.receipt.table == "player_value_metrics"  # tape over pedigree


def test_no_candidate_returns_none():
    db = _MemDB()
    assert sc._select_ban(db, 999, 2025, "QB") is None


def test_tiny_cohort_aura_is_disqualified_not_downweighted():
    db = _MemDB()
    db.add_aura(1, gap=40, cohort=5)   # below _BAN_MIN_COHORT -> gated out
    assert sc._select_ban(db, 1, 2025, "QB") is None


# --------------------------------------------------------------------------- #
# The Streak (RB rushing / WR-TE receiving 100-yd game runs)
# --------------------------------------------------------------------------- #
def test_strong_streak_is_production_tier_ban():
    db = _MemDB()
    db.add_games(1, "rushing", [120, 105, 100, 140, 133])  # 5 straight 100+
    ban = sc._select_ban(db, 1, 2025, "RB")
    assert ban.receipt.table == "player_game_stats"
    assert ban.number == "5"
    assert ban.label == "STRAIGHT 100-YD RUSH GAMES"


def test_streak_breaks_on_sub_bar_game():
    db = _MemDB()
    db.add_games(1, "rushing", [120, 105, 50, 100, 110, 130])  # longest run = 3
    ban = sc._select_ban(db, 1, 2025, "RB")
    assert ban.number == "3"  # not 6


def test_short_streak_is_volume_tier_yields_to_production():
    db = _MemDB()
    db.add_games(1, "rushing", [120, 105, 100])  # 3-game streak = VOLUME tier
    db.add_wepa(1, 0.40)                          # PRODUCTION tier
    assert sc._select_ban(db, 1, 2025, "RB").receipt.table == "player_value_metrics"


def test_strong_streak_beats_modest_wepa():
    db = _MemDB()
    db.add_games(1, "rushing", [120, 105, 100, 140, 133])  # 5 straight -> production
    db.add_wepa(1, 0.29)                                    # modest WEPA
    assert sc._select_ban(db, 1, 2025, "RB").receipt.table == "player_game_stats"


def test_streak_below_min_is_not_a_ban():
    db = _MemDB()
    db.add_games(1, "rushing", [120, 105, 40, 90])  # longest run = 2
    assert sc._select_ban(db, 1, 2025, "RB") is None


def test_qb_passing_streak_excluded():
    db = _MemDB()
    db.add_games(1, "passing", [300, 320, 310, 290, 305])  # QB has no streak spec
    assert sc._select_ban(db, 1, 2025, "QB") is None


def test_receiving_streak_label():
    db = _MemDB()
    db.add_games(1, "receiving", [110, 120, 100, 130, 105])
    ban = sc._select_ban(db, 1, 2025, "WR")
    assert ban.label == "STRAIGHT 100-YD REC GAMES"


# --------------------------------------------------------------------------- #
# Accent tagging (color-by-register; doc 60 §2/§6)
# --------------------------------------------------------------------------- #
def test_accent_tags_match_register():
    db = _MemDB()
    db.add_aura(1, gap=40)
    assert sc._select_ban(db, 1, 2025, "QB").accent == "aura"
    db2 = _MemDB()
    db2.add_wepa(2, 0.40)
    assert sc._select_ban(db2, 2, 2025, "QB").accent == "production"
    db3 = _MemDB()
    db3.add_recruit(3, nat=5, stars=5)
    assert sc._select_ban(db3, 3, 2025, "QB").accent == "rank"
