"""Viral content engine (Sprint v5-10e).

Five share-card artifact types, each its own module:

    cfb_rankings.viral.mood_map         — Monday Mood Map (1200×675)
    cfb_rankings.viral.daily_movers     — Today's biggest belief moves
    cfb_rankings.viral.pregame_pack     — Friday-night Saturday game pack
    cfb_rankings.viral.receipt_card     — Resolved-prediction aged-well card
    cfb_rankings.viral.quote_card       — Single pull-quote card

All five share the same token system (mood_map.LIGHT + .DARK), the same
1200×{630|675} OG dimensions, and the same Pillow renderer style. Each
returns a Path on success and creates parent directories as needed.

The mood_map module is the most-feature-rich today (production-ready
runtime). The other four are scaffolds — render functions complete
and tested, but the v5-10e Sprint adds DB-backed data builders that
turn (predictive_claims, daily_takes, etc.) into the render input.
"""

from . import daily_movers, mood_map, pregame_pack, quote_card, receipt_card

__all__ = [
    "mood_map",
    "daily_movers",
    "pregame_pack",
    "receipt_card",
    "quote_card",
]
