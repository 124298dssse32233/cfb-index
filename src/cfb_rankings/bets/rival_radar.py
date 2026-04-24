"""Rival Radar — how much rival fanbases fixate on a player (S2.4 / §4 Bet #1).

Reads from ``player_week_conversation_features`` (audience_bucket='rival'
rows) and emits an aggregated profile per player. When the rival sample
is below the floor (< 4 mentions in the season) we return an empty-state
dict so the renderer shows "Awaiting Signal" instead of a fake number.

Today's data is sparse — only 7 players carry any rival-bucket mentions
at all — so the module is largely dormant until ingestion thickens up.
Same architecture as the rest of bets/: aggregate function + small
render-payload helper, renderer in reporting.py reads the dict.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cfb_rankings.db import Database


# Floor rule — don't render a rival-radar card with < MIN_MENTIONS rival
# mentions in the season. Everything below the floor reads "Awaiting
# Signal" instead of a noise-driven score.
MIN_MENTIONS = 4


@dataclass(frozen=True)
class RivalRadar:
    player_id: int
    mention_count_season: int
    weeks_with_rival_chatter: int
    peak_week: int | None
    peak_week_mentions: int
    positive_share: float
    negative_share: float
    neutral_share: float
    obsession_score: float  # 0..100, naive normalization against the league max
    league_max_mentions: int
    applicable: bool
    awaiting_reason: str

    def to_render_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "mention_count_season": self.mention_count_season,
            "weeks_with_rival_chatter": self.weeks_with_rival_chatter,
            "peak_week": self.peak_week,
            "peak_week_mentions": self.peak_week_mentions,
            "positive_share": round(self.positive_share, 3),
            "negative_share": round(self.negative_share, 3),
            "neutral_share": round(self.neutral_share, 3),
            "obsession_score": round(self.obsession_score, 1),
            "league_max_mentions": self.league_max_mentions,
            "applicable": self.applicable,
            "awaiting_reason": self.awaiting_reason,
        }


def _fetch_league_max_rival_mentions(db: Database, season: int) -> int:
    row = db.query_one(
        "SELECT COALESCE(MAX(tot), 0) AS m FROM ("
        "  SELECT SUM(mention_count) AS tot "
        "  FROM player_week_conversation_features "
        "  WHERE audience_bucket = 'rival' AND season_year = :s "
        "  GROUP BY player_id"
        ")",
        {"s": season},
    )
    return int((row or {}).get("m") or 0)


def compute_rival_radar(db: Database, player_id: int, season: int) -> RivalRadar:
    """Build the RivalRadar dataclass for (player, season)."""
    empty = RivalRadar(
        player_id=player_id,
        mention_count_season=0,
        weeks_with_rival_chatter=0,
        peak_week=None,
        peak_week_mentions=0,
        positive_share=0.0,
        negative_share=0.0,
        neutral_share=0.0,
        obsession_score=0.0,
        league_max_mentions=0,
        applicable=False,
        awaiting_reason="No rival-bucket mentions in the current season.",
    )

    rows = db.query_all(
        "SELECT week, mention_count, positive_doc_count, neutral_doc_count, "
        "       negative_doc_count "
        "FROM player_week_conversation_features "
        "WHERE audience_bucket = 'rival' "
        "  AND player_id = :pid AND season_year = :s",
        {"pid": player_id, "s": season},
    )
    if not rows:
        return empty

    total_mentions = 0
    weeks_with_chatter = 0
    peak_week: int | None = None
    peak_week_mentions = 0
    pos_total = neg_total = neu_total = 0
    for r in rows:
        m = int(r.get("mention_count") or 0)
        total_mentions += m
        if m > 0:
            weeks_with_chatter += 1
        if m > peak_week_mentions:
            peak_week_mentions = m
            peak_week = int(r.get("week") or 0)
        pos_total += int(r.get("positive_doc_count") or 0)
        neu_total += int(r.get("neutral_doc_count") or 0)
        neg_total += int(r.get("negative_doc_count") or 0)

    if total_mentions < MIN_MENTIONS:
        return RivalRadar(
            player_id=player_id,
            mention_count_season=total_mentions,
            weeks_with_rival_chatter=weeks_with_chatter,
            peak_week=peak_week,
            peak_week_mentions=peak_week_mentions,
            positive_share=0.0,
            negative_share=0.0,
            neutral_share=0.0,
            obsession_score=0.0,
            league_max_mentions=0,
            applicable=False,
            awaiting_reason=(
                f"Only {total_mentions} rival mention(s) — below the "
                f"{MIN_MENTIONS}-mention floor for a defensible read."
            ),
        )

    denom = max(pos_total + neu_total + neg_total, 1)
    positive_share = pos_total / denom
    negative_share = neg_total / denom
    neutral_share = neu_total / denom

    league_max = _fetch_league_max_rival_mentions(db, season)
    obsession = (total_mentions / league_max * 100.0) if league_max > 0 else 0.0

    return RivalRadar(
        player_id=player_id,
        mention_count_season=total_mentions,
        weeks_with_rival_chatter=weeks_with_chatter,
        peak_week=peak_week,
        peak_week_mentions=peak_week_mentions,
        positive_share=positive_share,
        negative_share=negative_share,
        neutral_share=neutral_share,
        obsession_score=obsession,
        league_max_mentions=league_max,
        applicable=True,
        awaiting_reason="",
    )
