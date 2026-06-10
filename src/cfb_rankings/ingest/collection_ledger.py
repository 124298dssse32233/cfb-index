"""Stale-first rotation + checkpoint/defer ledger for slow per-entity sources.

The cadence keystone (docs/pipeline_cadence_architecture_2026-06.md). A source
that can't refresh all N entities every run (rate-limited APIs like GDELT) instead
refreshes the **stalest-due** slice each run, covering every entity over a rolling
window with bounded per-run work. `next_due_at <= now` is the pending set; a
single SQLite writer means no locking needed.

Usage in an adapter's fetch():
    from cfb_rankings.ingest.collection_ledger import select_batch, mark_ok, mark_fail, Budget
    batch = select_batch(db, "gdelt", candidate_entities, budget=46, now_iso=now)
    clock = Budget(seconds=480)              # hard wall-clock box -> never grinds
    for entity in batch:
        if clock.expired(): break            # defer the rest to next run
        try:
            ... fetch + write ...
            mark_ok(db, "gdelt", entity, now, interval_hours=72)
        except Exception:
            mark_fail(db, "gdelt", entity, now)
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Budget:
    """A monotonic wall-clock deadline. expired() True once `seconds` elapse."""

    def __init__(self, seconds: float) -> None:
        self._deadline = time.monotonic() + max(1.0, seconds)

    def expired(self) -> bool:
        return time.monotonic() >= self._deadline


def select_batch(db, source: str, candidates: list[str], budget: int,
                 now_iso: str | None = None) -> list[str]:
    """Return up to `budget` entities to collect this run, stalest-due first.

    Ordering: never-collected first, then oldest next_due_at; entities in an
    active cooldown are excluded this run. `candidates` is the full universe
    (e.g. all team_ids as strings) so newly-added entities are picked up.
    """
    now_iso = now_iso or _now_iso()
    rows = {
        r["entity"]: r
        for r in db.query_all(
            "select entity, next_due_at, cooldown_until from collection_ledger "
            "where source = :s",
            {"s": source},
        )
    }

    def cooling(e: str) -> bool:
        r = rows.get(e)
        return bool(r and r.get("cooldown_until") and str(r["cooldown_until"]) > now_iso)

    def sort_key(e: str):
        r = rows.get(e)
        if r is None:
            return (0, "")  # never collected -> highest priority
        return (1, str(r.get("next_due_at") or ""))  # then stalest due first

    eligible = [e for e in candidates if not cooling(e)]
    eligible.sort(key=sort_key)
    return eligible[: max(0, int(budget))]


def mark_ok(db, source: str, entity: str, now_iso: str | None = None,
            *, interval_hours: float = 72.0, cursor: str | None = None) -> None:
    now_iso = now_iso or _now_iso()
    due = (datetime.now(timezone.utc) + timedelta(hours=interval_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    db.execute(
        """
        insert into collection_ledger
          (source, entity, last_ok_at, last_attempt_at, next_due_at, cursor,
           consecutive_failures, cooldown_until)
        values (:s, :e, :now, :now, :due, :cur, 0, null)
        on conflict(source, entity) do update set
          last_ok_at = :now, last_attempt_at = :now, next_due_at = :due,
          cursor = coalesce(:cur, collection_ledger.cursor),
          consecutive_failures = 0, cooldown_until = null
        """,
        {"s": source, "e": str(entity), "now": now_iso, "due": due, "cur": cursor},
    )


def mark_fail(db, source: str, entity: str, now_iso: str | None = None,
              *, base_cooldown_seconds: float = 3600.0, max_cooldown_seconds: float = 86400.0) -> None:
    """Record a failed attempt; set an escalating per-entity cooldown so a
    persistently-failing entity backs off instead of being retried every run."""
    now_iso = now_iso or _now_iso()
    prior = db.query_one(
        "select consecutive_failures from collection_ledger where source=:s and entity=:e",
        {"s": source, "e": str(entity)},
    )
    fails = int((prior or {}).get("consecutive_failures") or 0) + 1
    backoff = min(max_cooldown_seconds, base_cooldown_seconds * (2 ** (fails - 1)))
    cooldown = (datetime.now(timezone.utc) + timedelta(seconds=backoff)).strftime("%Y-%m-%dT%H:%M:%SZ")
    db.execute(
        """
        insert into collection_ledger
          (source, entity, last_attempt_at, consecutive_failures, cooldown_until)
        values (:s, :e, :now, :fails, :cd)
        on conflict(source, entity) do update set
          last_attempt_at = :now, consecutive_failures = :fails, cooldown_until = :cd
        """,
        {"s": source, "e": str(entity), "now": now_iso, "fails": fails, "cd": cooldown},
    )


__all__ = ["Budget", "select_batch", "mark_ok", "mark_fail"]
