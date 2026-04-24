"""Signature Play — per-player signature-moment picker (S3.2 / §4 Bet #8).

Spec: ``docs/specs/signature_bets/signature_play_spec.md``. V1 is
game-level (the play ↔ player bridge doesn't exist yet); "Signature
Moment" = the game where the player's headline metric was highest,
context-weighted by opponent + home/away.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cfb_rankings.db import Database


_METRIC_TO_STAT: dict[str, tuple[str, str]] = {
    "passing_yards_total": ("passing", "YDS"),
    "passing_yards":       ("passing", "YDS"),
    "passing_tds":         ("passing", "TD"),
    "ypa":                 ("passing", "YDS"),  # use yards as magnitude for YPA signatures
    "completion_pct":      ("passing", "YDS"),
    "rushing_yards_total": ("rushing", "YDS"),
    "rushing_yards":       ("rushing", "YDS"),
    "rushing_tds":         ("rushing", "TD"),
    "ypc":                 ("rushing", "YDS"),
    "receiving_yards_total": ("receiving", "YDS"),
    "receiving_yards":       ("receiving", "YDS"),
    "receiving_tds":         ("receiving", "TD"),
    "ypr":                   ("receiving", "YDS"),
}


@dataclass(frozen=True)
class SignatureMoment:
    player_id: int
    season: int
    game_id: int
    week: int
    metric_id: str
    stat_value: float
    score: float
    opponent_name: str
    home_away: str            # "home" | "away" | "neutral"
    result_label: str         # "W 34-27" or "L 17-21"
    gloss: str


def _resolve_metric_stat(metric_id: str | None) -> tuple[str, str] | None:
    if not metric_id:
        return None
    return _METRIC_TO_STAT.get(metric_id)


def _fetch_signature_metric_id(db: Database, player_id: int, season: int) -> str | None:
    """Pull the player's headline signature-story metric for the season."""
    # The signature-story cache isn't a table today; recompute on the fly
    # against the scoreboard.
    try:
        from cfb_rankings.signature_story import build_candidate_scoreboard
        scoreboard = build_candidate_scoreboard(db, player_id, season, None)
    except Exception:
        return None
    return scoreboard[0].metric.id if scoreboard else None


def _build_gloss(stat_type: str, stat_value: float, opponent_short: str, home_away: str) -> str:
    verb_map = {
        "YDS": "put up",
        "TD":  "stacked",
    }
    verb = verb_map.get(stat_type, "posted")
    site = "at" if home_away == "away" else "vs"
    return (
        f"The week the volume broke through — {verb} {int(stat_value)} "
        f"{stat_type.lower()} {site} {opponent_short}."
    )


def compute_signature_moment(
    db: Database, player_id: int, season: int
) -> SignatureMoment | None:
    metric_id = _fetch_signature_metric_id(db, player_id, season)
    mstat = _resolve_metric_stat(metric_id)
    if mstat is None:
        return None
    category, stat_type = mstat

    rows = db.query_all(
        "SELECT pgs.game_id, pgs.week, pgs.stat_value_num, pgs.team_id, "
        "       g.home_team_id, g.away_team_id, g.home_points, g.away_points, "
        "       ht.short_name AS home_short, at.short_name AS away_short "
        "FROM player_game_stats pgs "
        "LEFT JOIN games g ON g.game_id = pgs.game_id "
        "LEFT JOIN teams ht ON ht.team_id = g.home_team_id "
        "LEFT JOIN teams at ON at.team_id = g.away_team_id "
        "WHERE pgs.player_id = :pid AND pgs.season_year = :s "
        "  AND pgs.category = :c AND pgs.stat_type = :st "
        "  AND pgs.stat_value_num IS NOT NULL",
        {"pid": player_id, "s": season, "c": category, "st": stat_type},
    )
    # Acceptance gate: need at least 2 games of coverage to pick a signature.
    if len(rows) < 2:
        return None

    best: dict[str, Any] | None = None
    best_score = float("-inf")
    for r in rows:
        value = float(r.get("stat_value_num") or 0)
        if value <= 0:
            continue
        home_away = "home" if r.get("team_id") == r.get("home_team_id") else "away"
        home_away_factor = 1.05 if home_away == "away" else 1.0
        score = value * home_away_factor
        if score > best_score:
            best_score = score
            best = {**r, "value": value, "home_away": home_away}
    if best is None:
        return None

    opp_short = (
        best.get("away_short") if best["home_away"] == "home"
        else best.get("home_short")
    ) or "opponent"
    hp = best.get("home_points")
    ap = best.get("away_points")
    if hp is None or ap is None:
        result_label = "—"
    else:
        team_is_home = best["home_away"] == "home"
        own = hp if team_is_home else ap
        opp = ap if team_is_home else hp
        symbol = "W" if own > opp else ("L" if own < opp else "T")
        result_label = f"{symbol} {int(own)}-{int(opp)}"

    return SignatureMoment(
        player_id=player_id,
        season=season,
        game_id=int(best["game_id"]),
        week=int(best.get("week") or 0),
        metric_id=str(metric_id),
        stat_value=float(best["value"]),
        score=round(best_score, 2),
        opponent_name=str(opp_short),
        home_away=best["home_away"],
        result_label=result_label,
        gloss=_build_gloss(stat_type, best["value"], str(opp_short), best["home_away"]),
    )


def store_signature_moment(db: Database, m: SignatureMoment) -> None:
    db.execute(
        "INSERT INTO player_signature_plays "
        "(player_id, season_year, game_id, week, metric_id, stat_value, "
        " score, opponent_name, home_away, result_label, gloss) "
        "VALUES (:pid, :s, :gid, :w, :mid, :sv, :sc, :opp, :ha, :rl, :gl) "
        "ON CONFLICT(player_id, season_year) DO UPDATE SET "
        "  game_id=excluded.game_id, week=excluded.week, metric_id=excluded.metric_id, "
        "  stat_value=excluded.stat_value, score=excluded.score, "
        "  opponent_name=excluded.opponent_name, home_away=excluded.home_away, "
        "  result_label=excluded.result_label, gloss=excluded.gloss, "
        "  generated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')",
        {
            "pid": m.player_id, "s": m.season, "gid": m.game_id, "w": m.week,
            "mid": m.metric_id, "sv": m.stat_value, "sc": m.score,
            "opp": m.opponent_name, "ha": m.home_away, "rl": m.result_label,
            "gl": m.gloss,
        },
    )


def compute_signature_plays_for_season(db: Database, season: int) -> int:
    """Batch-compute + cache one Signature Moment per qualifying player."""
    rows = db.query_all(
        "SELECT DISTINCT player_id FROM player_game_stats "
        "WHERE season_year = :s",
        {"s": season},
    )
    n = 0
    for r in rows:
        pid = int(r["player_id"])
        m = compute_signature_moment(db, pid, season)
        if m is not None:
            store_signature_moment(db, m)
            n += 1
    return n


def fetch_signature_moment(
    db: Database, player_id: int, season: int
) -> SignatureMoment | None:
    row = db.query_one(
        "SELECT game_id, week, metric_id, stat_value, score, opponent_name, "
        "       home_away, result_label, gloss "
        "FROM player_signature_plays "
        "WHERE player_id = :pid AND season_year = :s",
        {"pid": player_id, "s": season},
    )
    if not row:
        return None
    return SignatureMoment(
        player_id=player_id,
        season=season,
        game_id=int(row["game_id"]),
        week=int(row.get("week") or 0),
        metric_id=str(row.get("metric_id") or ""),
        stat_value=float(row.get("stat_value") or 0),
        score=float(row.get("score") or 0),
        opponent_name=str(row.get("opponent_name") or ""),
        home_away=str(row.get("home_away") or ""),
        result_label=str(row.get("result_label") or ""),
        gloss=str(row.get("gloss") or ""),
    )
