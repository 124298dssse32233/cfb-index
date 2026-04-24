"""Live Signal Flow — event store + fetch helpers (Signature Bets S1.6).

Per SIGNATURE_BETS §4 Bet #13: when a player has a real-world news
moment (portal entry, commit, injury, draft pick, Heisman odds swing,
…) the page lights up with a thin, gold-left-border bar under the
Hero. The bar decays over ``decay_hours`` (default 72h) then hides.

This module handles the event lifecycle — ``emit_signal_event`` writes
a row, ``fetch_active_signals`` returns every row not-yet-decayed for a
player, and ``prune_expired_signals`` is a convenience for a nightly
cron.

The renderer + Alpine layer live in reporting.py +
``static_assets/js/bets/signal-flow.js``. This file has no rendering.
"""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass
from typing import Any

from cfb_rankings.db import Database


# Canonical event-type vocabulary. Keep in sync with the migration
# comment; the renderer branches on these for decay-tier / icon choice.
EVENT_TYPES: tuple[str, ...] = (
    "portal_entry",
    "commit",
    "injury",
    "draft_declare",
    "draft_pick",
    "watch_list",
    "all_american",
    "program_record",
    "heisman_odds_swing",
    "major_news",
)

DEFAULT_DECAY_HOURS: float = 72.0


@dataclass(frozen=True)
class Signal:
    """In-memory view of a ``player_signal_events`` row."""
    player_signal_event_id: int
    player_id: int
    event_type: str
    headline: str
    sub_line: str | None
    event_ts: _dt.datetime
    decay_hours: float
    source_url: str | None
    source_name: str | None
    event_data: dict[str, Any]

    @property
    def expires_at(self) -> _dt.datetime:
        return self.event_ts + _dt.timedelta(hours=self.decay_hours)

    def remaining_fraction(self, *, now: _dt.datetime | None = None) -> float:
        """Return how much of the decay window is left, 0..1."""
        now = now or _dt.datetime.now(_dt.timezone.utc)
        total = self.decay_hours * 3600.0
        elapsed = (now - self.event_ts).total_seconds()
        if total <= 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - (elapsed / total)))

    def is_expired(self, *, now: _dt.datetime | None = None) -> bool:
        now = now or _dt.datetime.now(_dt.timezone.utc)
        return now >= self.expires_at

    def to_render_dict(self) -> dict[str, Any]:
        return {
            "id": self.player_signal_event_id,
            "event_type": self.event_type,
            "headline": self.headline,
            "sub_line": self.sub_line,
            "event_ts": self.event_ts.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "remaining_fraction": round(self.remaining_fraction(), 3),
            "source_url": self.source_url,
            "source_name": self.source_name,
            "event_data": self.event_data,
        }


def _parse_ts(value: Any) -> _dt.datetime:
    if isinstance(value, _dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=_dt.timezone.utc)
    if isinstance(value, str):
        # Accept both "...Z" and "+00:00" forms.
        v = value.rstrip("Z")
        try:
            dt = _dt.datetime.fromisoformat(v)
        except ValueError:
            return _dt.datetime.now(_dt.timezone.utc)
        return dt if dt.tzinfo else dt.replace(tzinfo=_dt.timezone.utc)
    return _dt.datetime.now(_dt.timezone.utc)


def _signal_from_row(row: dict[str, Any]) -> Signal:
    data_json = row.get("event_data_json")
    try:
        event_data = json.loads(data_json) if data_json else {}
    except (TypeError, ValueError):
        event_data = {}
    return Signal(
        player_signal_event_id=int(row["player_signal_event_id"]),
        player_id=int(row["player_id"]),
        event_type=str(row["event_type"]),
        headline=str(row["headline"]),
        sub_line=(str(row["sub_line"]) if row.get("sub_line") else None),
        event_ts=_parse_ts(row["event_ts"]),
        decay_hours=float(row.get("decay_hours") or DEFAULT_DECAY_HOURS),
        source_url=(str(row["source_url"]) if row.get("source_url") else None),
        source_name=(str(row["source_name"]) if row.get("source_name") else None),
        event_data=event_data,
    )


def emit_signal_event(
    db: Database,
    *,
    player_id: int,
    event_type: str,
    headline: str,
    sub_line: str | None = None,
    event_ts: _dt.datetime | None = None,
    decay_hours: float = DEFAULT_DECAY_HOURS,
    source_url: str | None = None,
    source_name: str | None = None,
    event_data: dict[str, Any] | None = None,
    dedup_key: str | None = None,
) -> int:
    """Insert (or ignore-on-duplicate) one signal event.

    Returns the row id of the inserted event, or the existing id when a
    dedup_key collision occurs. Callers can rely on idempotency when
    replaying a backfill.
    """
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown event_type {event_type!r}")
    ts = event_ts or _dt.datetime.now(_dt.timezone.utc)
    ts_iso = ts.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    key = dedup_key or f"{player_id}|{event_type}|{ts_iso}"

    existing = db.query_one(
        "SELECT player_signal_event_id FROM player_signal_events "
        "WHERE dedup_key = :k",
        {"k": key},
    )
    if existing:
        return int(existing["player_signal_event_id"])

    db.execute(
        "INSERT INTO player_signal_events "
        "(player_id, event_type, headline, sub_line, event_ts, decay_hours, "
        " source_url, source_name, event_data_json, dedup_key) "
        "VALUES (:player_id, :event_type, :headline, :sub_line, :event_ts, "
        " :decay_hours, :source_url, :source_name, :event_data_json, :dedup_key)",
        {
            "player_id": player_id,
            "event_type": event_type,
            "headline": headline,
            "sub_line": sub_line,
            "event_ts": ts_iso,
            "decay_hours": float(decay_hours),
            "source_url": source_url,
            "source_name": source_name,
            "event_data_json": json.dumps(event_data or {}, separators=(",", ":")),
            "dedup_key": key,
        },
    )
    row = db.query_one(
        "SELECT player_signal_event_id FROM player_signal_events "
        "WHERE dedup_key = :k",
        {"k": key},
    )
    return int(row["player_signal_event_id"]) if row else 0


def fetch_active_signals(
    db: Database,
    player_id: int,
    *,
    now: _dt.datetime | None = None,
    limit: int = 4,
) -> list[Signal]:
    """Return unexpired signals for a player, newest first."""
    rows = db.query_all(
        "SELECT * FROM player_signal_events "
        "WHERE player_id = :pid "
        "ORDER BY event_ts DESC "
        "LIMIT :lim",
        {"pid": player_id, "lim": int(limit) * 4},
    )
    out: list[Signal] = []
    now = now or _dt.datetime.now(_dt.timezone.utc)
    for row in rows:
        sig = _signal_from_row(row)
        if sig.is_expired(now=now):
            continue
        out.append(sig)
        if len(out) >= limit:
            break
    return out


def prune_expired_signals(
    db: Database, *, older_than_hours: float = 24.0
) -> int:
    """Delete rows whose decay window closed more than ``older_than_hours``
    ago. Returns rows affected (pre-delete count)."""
    cutoff = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=older_than_hours)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    before = db.query_one(
        "SELECT COUNT(*) AS n FROM player_signal_events "
        "WHERE datetime(event_ts, '+' || decay_hours || ' hours') < :cutoff",
        {"cutoff": cutoff_iso},
    )
    db.execute(
        "DELETE FROM player_signal_events "
        "WHERE datetime(event_ts, '+' || decay_hours || ' hours') < :cutoff",
        {"cutoff": cutoff_iso},
    )
    return int((before or {}).get("n") or 0)
