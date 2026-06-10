"""Player-ID anchor — keep player-page URLs stable across full DB rebuilds.

WHY THIS EXISTS
---------------
Player-page URLs embed ``players.player_id`` — an ``INTEGER PRIMARY KEY
AUTOINCREMENT`` surrogate key (e.g. ``/players/fernando-mendoza-12763.html``).
Within a single database that id is stable: ingestion calls
``_get_or_create_player`` which matches on ``player_source_ids`` and reuses the
existing id. But a *full rebuild from an empty DB* (fresh ``init-db`` +
re-ingest — e.g. the 2026-06 box migration) reassigns every id by insertion
order, so every previously-shared ``/players/<name>-<id>.html`` link 404s.
Mendoza went 38276 -> 12763, Love 48316 -> 12194, Brown 38981 -> 12655.

THE FIX
-------
Persist the canonical ``(cfbd source_player_id -> player_id)`` mapping to a
committed CSV, then re-seed it BEFORE ingestion on a rebuild. Because
``_get_or_create_player`` looks the player up by ``player_source_ids`` and
returns the existing ``player_id``, pre-seeding the canonical ids makes
ingestion *reuse* them — so the URLs never churn again. No URL reset, no
23k-entry redirect table, no SEO loss.

Two operations:

* :func:`export_anchor` — write the current canonical mapping to the CSV.
  Run it after large ingests so newly-created players become anchored too.
* :func:`seed_anchor` — on a fresh/empty DB, pre-create ``players`` +
  ``player_source_ids`` rows with their canonical ids. It SKIPS any player or
  source-id already present, so it is a safe no-op on a populated DB and only
  changes anything on a genuine from-scratch rebuild. It also advances
  ``sqlite_sequence`` so brand-new players get ids above the anchored range.

Only CFBD-sourced players (those with a stable external athlete id) are
anchored — that covers the players who have stat-backed pages. Players without
an external id keep the old name-match behaviour (a small, low-profile tail).
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

from cfb_rankings.db import Database

log = logging.getLogger(__name__)

DEFAULT_ANCHOR_PATH = "data/player_id_anchor.csv"

# (source_name, source_player_id) + player_id are the load-bearing keys; the
# players-table fields let us recreate a renderable row before ingestion
# repopulates stats. We anchor EVERY external source mapping (cfbd, cfbd-recruit,
# …) so whichever match path ingestion uses reuses the canonical id.
_FIELDS = [
    "source_name",
    "source_player_id",
    "player_id",
    "full_name",
    "first_name",
    "last_name",
    "position",
    "hometown",
    "home_state",
]


def export_anchor(db: Database, path: str | Path = DEFAULT_ANCHOR_PATH) -> int:
    """Write the current canonical (cfbd source_player_id -> player_id) mapping.

    Returns the number of rows written. Ordered by player_id for a stable,
    diff-friendly committed file.
    """
    rows = db.query_all(
        """
        select psi.source_name           as source_name,
               psi.source_player_id      as source_player_id,
               p.player_id               as player_id,
               p.full_name               as full_name,
               coalesce(p.first_name,'') as first_name,
               coalesce(p.last_name,'')  as last_name,
               coalesce(p.position,'')   as position,
               coalesce(p.hometown,'')   as hometown,
               coalesce(p.home_state,'') as home_state
          from player_source_ids psi
          join players p on p.player_id = psi.player_id
         where psi.source_name is not null and psi.source_name <> ''
           and psi.source_player_id is not null and psi.source_player_id <> ''
         order by p.player_id, psi.source_name, psi.source_player_id
        """,
    )
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in _FIELDS})
    log.info("player-id anchor: exported %d rows -> %s", len(rows), out)
    return len(rows)


def seed_anchor(db: Database, path: str | Path = DEFAULT_ANCHOR_PATH) -> dict[str, int]:
    """Pre-seed canonical player ids from the anchor CSV (idempotent).

    Safe on a populated DB: any player_id already present, and any
    (source_name, source_player_id) already mapped, is skipped — so this only
    materialises rows on a from-scratch rebuild. Returns counts:
    {"anchor_rows", "players_inserted", "source_ids_inserted"}.
    """
    src = Path(path)
    if not src.exists():
        log.warning("player-id anchor: %s not found — nothing to seed", src)
        return {"anchor_rows": 0, "players_inserted": 0, "source_ids_inserted": 0}

    with src.open("r", encoding="utf-8", newline="") as fh:
        anchor_rows = list(csv.DictReader(fh))

    with db.connection() as conn:
        # Snapshot the pre-seed state so the final insert counts are exact even
        # though INSERT OR IGNORE gives no reliable per-row delta.
        initial_pids = {int(r[0]) for r in conn.execute("select player_id from players")}
        initial_srcids = {
            (str(r[0]), str(r[1]))
            for r in conn.execute("select source_name, source_player_id from player_source_ids")
        }

        seen_pids: set[int] = set()
        for row in anchor_rows:
            try:
                pid = int(row["player_id"])
            except (KeyError, ValueError, TypeError):
                continue
            src_pid = str(row.get("source_player_id") or "").strip()
            src_name = str(row.get("source_name") or "cfbd").strip() or "cfbd"
            if not src_pid:
                continue

            # Recreate the players row (once per canonical id) unless present.
            if pid not in initial_pids and pid not in seen_pids:
                conn.execute(
                    """
                    insert or ignore into players
                        (player_id, full_name, first_name, last_name,
                         position, hometown, home_state)
                    values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pid,
                        row.get("full_name") or "",
                        row.get("first_name") or "",
                        row.get("last_name") or "",
                        row.get("position") or "",
                        row.get("hometown") or "",
                        row.get("home_state") or "",
                    ),
                )
                seen_pids.add(pid)

            # Map external source id -> canonical player id unless already mapped.
            if (src_name, src_pid) not in initial_srcids:
                conn.execute(
                    """
                    insert or ignore into player_source_ids
                        (player_id, source_name, source_player_id)
                    values (?, ?, ?)
                    """,
                    (pid, src_name, src_pid),
                )

        # Advance the AUTOINCREMENT high-water mark so new players never collide
        # with an anchored id. Explicit-rowid inserts already bump
        # sqlite_sequence, but set it defensively for the fresh-table case.
        maxid = conn.execute("select coalesce(max(player_id), 0) from players").fetchone()[0]
        seqrow = conn.execute("select seq from sqlite_sequence where name = 'players'").fetchone()
        if seqrow is None:
            conn.execute("insert into sqlite_sequence (name, seq) values ('players', ?)", (maxid,))
        elif int(seqrow[0]) < maxid:
            conn.execute("update sqlite_sequence set seq = ? where name = 'players'", (maxid,))

        conn.commit()

        now_pids = {int(r[0]) for r in conn.execute("select player_id from players")}
        now_srcids = {
            (str(r[0]), str(r[1]))
            for r in conn.execute("select source_name, source_player_id from player_source_ids")
        }
        players_inserted = len(now_pids - initial_pids)
        source_ids_inserted = len(now_srcids - initial_srcids)

    log.info(
        "player-id anchor: seeded players+%d source_ids+%d (anchor rows=%d)",
        players_inserted,
        source_ids_inserted,
        len(anchor_rows),
    )
    return {
        "anchor_rows": len(anchor_rows),
        "players_inserted": players_inserted,
        "source_ids_inserted": source_ids_inserted,
    }


__all__ = ["export_anchor", "seed_anchor", "DEFAULT_ANCHOR_PATH"]
