"""Prediction Markets — Heisman futures + prop signals (S2.8 / §4 Bet #9).

Reads from ``prediction_market_snapshots`` + ``heisman_market_odds_
weekly`` (both populated by the prediction-market adapters in
``ingest/sources``). Returns a render-ready dict per player.

Empty state is honest: if a player isn't listed on any major market we
return ``listed=False`` and the renderer shows
"Not yet listed on major futures markets." — never a fabricated number.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cfb_rankings.db import Database


@dataclass
class PlayerMarketSignal:
    listed: bool
    heisman_implied_pct: float | None
    heisman_provider: str | None
    heisman_market_title: str | None
    heisman_last_price: float | None
    heisman_source_url: str | None
    heisman_snapshot_time: str | None
    trailing_move_bps: float | None


def _null_signal() -> PlayerMarketSignal:
    return PlayerMarketSignal(
        listed=False,
        heisman_implied_pct=None,
        heisman_provider=None,
        heisman_market_title=None,
        heisman_last_price=None,
        heisman_source_url=None,
        heisman_snapshot_time=None,
        trailing_move_bps=None,
    )


def fetch_player_market_signals(
    db: Database, player_id: int, season: int
) -> PlayerMarketSignal:
    """Pull the most recent Heisman futures snapshot for a player.

    Fallback chain:
    1. prediction_market_snapshots (provider-agnostic, newer pipeline).
    2. heisman_market_odds_weekly (legacy helper table).
    3. Empty signal → `listed=False`.
    """
    # Pipeline 1 — newer snapshot table.
    row = db.query_one(
        "SELECT provider, market_title, implied_probability, last_price, "
        "       source_url, snapshot_time_utc "
        "FROM prediction_market_snapshots "
        "WHERE player_id = :pid AND season_year = :s "
        "  AND market_type = 'heisman' "
        "ORDER BY snapshot_time_utc DESC LIMIT 1",
        {"pid": player_id, "s": season},
    )
    trailing_move_bps = None
    if row and row.get("implied_probability") is not None:
        # Trailing move: delta vs the oldest snapshot this season for this player.
        prev = db.query_one(
            "SELECT implied_probability FROM prediction_market_snapshots "
            "WHERE player_id = :pid AND season_year = :s "
            "  AND market_type = 'heisman' "
            "ORDER BY snapshot_time_utc ASC LIMIT 1",
            {"pid": player_id, "s": season},
        )
        if prev and prev.get("implied_probability") is not None:
            delta = float(row["implied_probability"]) - float(prev["implied_probability"])
            trailing_move_bps = round(delta * 10000.0, 1)
        return PlayerMarketSignal(
            listed=True,
            heisman_implied_pct=round(
                float(row["implied_probability"]) * 100.0, 1
            ),
            heisman_provider=str(row.get("provider") or ""),
            heisman_market_title=str(row.get("market_title") or ""),
            heisman_last_price=(
                float(row["last_price"]) if row.get("last_price") is not None else None
            ),
            heisman_source_url=row.get("source_url"),
            heisman_snapshot_time=row.get("snapshot_time_utc"),
            trailing_move_bps=trailing_move_bps,
        )

    # Pipeline 2 — legacy helper.
    row2 = db.query_one(
        "SELECT provider, american_odds, decimal_odds, implied_probability, "
        "       notes "
        "FROM heisman_market_odds_weekly "
        "WHERE player_id = :pid AND season_year = :s "
        "ORDER BY week DESC LIMIT 1",
        {"pid": player_id, "s": season},
    )
    if row2 and row2.get("implied_probability") is not None:
        return PlayerMarketSignal(
            listed=True,
            heisman_implied_pct=round(
                float(row2["implied_probability"]) * 100.0, 1
            ),
            heisman_provider=str(row2.get("provider") or ""),
            heisman_market_title=str(row2.get("notes") or "Heisman Trophy Winner"),
            heisman_last_price=(
                float(row2["decimal_odds"])
                if row2.get("decimal_odds") is not None else None
            ),
            heisman_source_url=None,
            heisman_snapshot_time=None,
            trailing_move_bps=None,
        )

    return _null_signal()


def signal_to_render_dict(sig: PlayerMarketSignal) -> dict[str, Any]:
    return {
        "listed": sig.listed,
        "heisman_implied_pct": sig.heisman_implied_pct,
        "heisman_provider": sig.heisman_provider,
        "heisman_market_title": sig.heisman_market_title,
        "heisman_last_price": sig.heisman_last_price,
        "heisman_source_url": sig.heisman_source_url,
        "heisman_snapshot_time": sig.heisman_snapshot_time,
        "trailing_move_bps": sig.trailing_move_bps,
    }
