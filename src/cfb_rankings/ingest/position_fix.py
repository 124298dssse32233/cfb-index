"""Repair players.position from roster / season-stat evidence.

Corruption mechanism (root cause, see cfbd._resolve_or_create_game_stat_player):
a player whose first appearance is a game-stat line gets created with a
position guessed from the stat category — "rushing" -> "RB" — which is how
QBs who rush (Arch Manning, Drew Allar, Cade Klubnik) were minted as RBs.
The guess is never revisited, even after authoritative positions arrive via
roster_entries and player_season_stats.

This module backfills players.position from best available evidence:
1. the most recent non-blank roster_entries.position, else
2. the modal non-blank player_season_stats.position in the player's most
   recent season that has one.

Idempotent; only rows whose best-evidence position differs are touched.

CLI:
    python manage.py fix-player-positions [--commit]   # dry-run by default
"""

from __future__ import annotations

import logging
from typing import Any

from cfb_rankings.db import Database

logger = logging.getLogger(__name__)

_EVIDENCE_SQL = """
with roster_best as (
  select player_id, position,
         row_number() over (
           partition by player_id
           order by season_year desc, roster_entry_id desc
         ) as rn
  from roster_entries
  where coalesce(trim(position), '') != ''
),
stats_latest_season as (
  select player_id, max(season_year) as season_year
  from player_season_stats
  where coalesce(trim(position), '') != ''
  group by player_id
),
stats_mode as (
  select pss.player_id, pss.position,
         row_number() over (
           partition by pss.player_id
           order by count(*) desc, pss.position
         ) as rn
  from player_season_stats pss
  join stats_latest_season ls
    on ls.player_id = pss.player_id and ls.season_year = pss.season_year
  where coalesce(trim(pss.position), '') != ''
  group by pss.player_id, pss.position
)
select p.player_id,
       p.full_name,
       coalesce(p.position, '') as current_position,
       coalesce(rb.position, sm.position) as best_position
from players p
left join (select player_id, position from roster_best where rn = 1) rb
  on rb.player_id = p.player_id
left join (select player_id, position from stats_mode where rn = 1) sm
  on sm.player_id = p.player_id
where coalesce(trim(coalesce(rb.position, sm.position)), '') != ''
  and trim(coalesce(rb.position, sm.position)) != trim(coalesce(p.position, ''))
"""


# Positions the game-stat category map could mint wrongly. A player currently
# carrying one of these whose roster/stat evidence says QB is the Arch Manning
# corruption class — safe to rescue. Everything else stays hands-off because
# the evidence tables carry their own category-guess noise (a DE who returned
# a kick can show 'WR' in player_season_stats) and generic roster buckets
# ('OL', 'LB') would downgrade specific positions ('OC', 'OLB').
_CATEGORY_GUESS_POSITIONS = {"RB", "WR", "DB", "TE", "FB"}


def fix_player_positions(db: Database, *, commit: bool = False) -> dict[str, Any]:
    """Find (and with ``commit=True`` repair) players.position drift.

    Do-no-harm policy — only two classes are ever written:
    1. blank fills: players.position is empty, any non-blank evidence wins;
    2. QB rescues: current position is a category-guess value but evidence
       says QB (passers can't appear in the 'passing' category by accident).
    Remaining conflicts are reported for review, never auto-applied.
    """
    rows = db.query_all(_EVIDENCE_SQL)
    fills = [r for r in rows if not str(r["current_position"]).strip()]
    qb_rescues = [
        r for r in rows
        if str(r["current_position"]).strip().upper() in _CATEGORY_GUESS_POSITIONS
        and str(r["best_position"]).strip().upper() == "QB"
    ]
    review = [
        r for r in rows
        if str(r["current_position"]).strip()
        and r not in qb_rescues
    ]

    sample = [
        f"{r['full_name']}: '{r['current_position']}' -> '{r['best_position']}'"
        for r in qb_rescues[:10]
    ]

    updated = 0
    if commit:
        apply_rows = fills + qb_rescues
        if apply_rows:
            db.execute_many(
                "update players set position = :best_position where player_id = :player_id",
                [
                    {"player_id": int(r["player_id"]), "best_position": str(r["best_position"]).strip()}
                    for r in apply_rows
                ],
            )
            updated = len(apply_rows)

    logger.info(
        "fix-player-positions: fills=%d qb_rescues=%d review_only=%d updated=%d",
        len(fills), len(qb_rescues), len(review), updated,
    )
    return {
        "candidates": len(rows),
        "blank_fills": len(fills),
        "qb_rescues": len(qb_rescues),
        "review_only": len(review),
        "updated": updated,
        "sample": sample,
    }


__all__ = ["fix_player_positions"]
