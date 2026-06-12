"""Snapshot persistence + cross-run source-change detection (Wave 0 guard).

The checker reads the DATA tables strictly ``?mode=ro``. This module is the ONE
place that opens a SEPARATE read-WRITE connection — and it writes ONLY to the two
additive ``data_health_*`` tables (migration ``20260612_01_data_health_snapshots``).
It never touches a product/data table.

What it does:
  * ``persist(db_path, gate, results, now_utc=...)`` — append one snapshot header
    row (the run header + the computed gate, with a cheap stable DB fingerprint)
    plus the normalized result rows, and return the new ``snapshot_id``.
  * ``latest(conn)`` / ``previous(conn)`` — read back the most recent (or
    second-most-recent) snapshot's result rows for trend comparison.
  * ``diff_source_states(prev_results, curr_results)`` — derive
    ``{added, retired, newly_failing}`` for source feeds by diffing the freshness
    pillar rows of two snapshots. No separate event-log table: the add/retire/
    first-failing story is DERIVED from snapshot diffs (per the spec — "drop
    source_change_log initially; derive by diffing").

Stdlib + raw sqlite3 only. The DB fingerprint is path-size-mtime + a schema hash
of a few spine tables; it is the pipeline-identity signal that defends the
box-DB-vs-cloud-artifact divergence class.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# The freshness pillar (checks/freshness.py) emits one summary row per source
# class as ``freshness.source_class.<cls>``. Source add/retire/newly-failing are
# derived ENTIRELY from these rows, so the prefix is the contract between the
# freshness pillar and this diff.
_SOURCE_CLASS_PREFIX = "freshness.source_class."

# Spine tables whose column signature we hash into the fingerprint. Cheap, stable,
# and exactly the surface whose drift caused the divergence pain (schema-level
# identity, not row content — row-count drift is what trend comparison is for).
_FINGERPRINT_TABLES = (
    "games",
    "players",
    "player_game_stats",
    "roster_entries",
    "teams",
)


# === DB fingerprint =========================================================


def _schema_hash(conn: sqlite3.Connection) -> str:
    """A stable hash of a few spine tables' CREATE-statement signatures.

    Reads ``sqlite_master.sql`` for the fingerprint tables (sorted, so order is
    deterministic). A missing table contributes a sentinel so a dropped spine
    table changes the fingerprint rather than silently matching.
    """
    parts: list[str] = []
    for table in sorted(_FINGERPRINT_TABLES):
        try:
            row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
        except sqlite3.Error:
            row = None
        parts.append(f"{table}::{(row[0] if row and row[0] else '<absent>')}")
    blob = "\n".join(parts).encode("utf-8", "replace")
    return hashlib.sha256(blob).hexdigest()[:16]


def compute_fingerprint(db_path: str | Path) -> str:
    """Cheap, stable identity of the DATA db: size + mtime + spine schema hash.

    Two runs over the SAME file fingerprint identically; the box DB vs a stale
    cloud artifact (different size/mtime/schema) fingerprint differently. Opens
    its own read-only connection for the schema hash and closes it — never holds
    the DB open. Best-effort: any failure degrades to a size/mtime-only string
    rather than crashing the snapshot.
    """
    p = Path(db_path)
    try:
        st = p.stat()
        size, mtime = st.st_size, int(st.st_mtime)
    except OSError:
        size, mtime = -1, -1

    schema = "unavailable"
    try:
        conn = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True, timeout=10)
        try:
            schema = _schema_hash(conn)
        finally:
            conn.close()
    except sqlite3.Error:
        pass

    return f"size={size};mtime={mtime};schema={schema}"


# === persistence ============================================================


def _open_rw(db_path: str | Path) -> sqlite3.Connection:
    """Open a SEPARATE read-WRITE connection (NOT ?mode=ro).

    This is the only read-write connection in the whole checker, and it writes
    ONLY to the data_health_* tables.
    """
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA busy_timeout=8000")
    return conn


def persist(
    db_path: str | Path,
    gate: dict,
    results,
    now_utc: str | None = None,
) -> int:
    """Append one snapshot (+ its result rows); return the new ``snapshot_id``.

    Args:
      db_path  the DATA db — fingerprinted, and where the data_health_* tables live.
      gate     the gate dict ({overall, passrates, counts, summary}).
      results  iterable of CheckResult rows.
      now_utc  the run timestamp to stamp (ISO-8601). Passed in for testability;
               defaults to ``datetime.now(timezone.utc)`` when omitted so callers
               that don't care get a sensible value without wiring a clock.

    Writes via a SEPARATE read-write connection to ONLY data_health_snapshot +
    data_health_result. Raises sqlite3.Error if the tables are absent (the
    migration must have run first) — surfaced, never swallowed, so a mis-wired
    pipeline fails loud rather than silently not persisting.
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")

    fingerprint = compute_fingerprint(db_path)
    passrates_json = json.dumps(gate.get("passrates", {}), sort_keys=True, default=str)
    counts_json = json.dumps(gate.get("counts", {}), sort_keys=True, default=str)

    conn = _open_rw(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO data_health_snapshot "
            "(run_utc, overall, db_fingerprint, passrates_json, counts_json, summary) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                now_utc,
                gate.get("overall"),
                fingerprint,
                passrates_json,
                counts_json,
                gate.get("summary"),
            ),
        )
        snapshot_id = int(cur.lastrowid)

        rows = [
            (
                snapshot_id,
                r.check_id,
                r.pillar,
                r.dataset,
                r.season,
                r.status,
                r.severity,
                r.detail,
            )
            for r in results
        ]
        if rows:
            conn.executemany(
                "INSERT INTO data_health_result "
                "(snapshot_id, check_id, pillar, dataset, season, status, severity, detail) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
        conn.commit()
        return snapshot_id
    finally:
        conn.close()


# === read-back ==============================================================


def _snapshot_id_at_offset(conn: sqlite3.Connection, offset: int) -> int | None:
    """The snapshot_id at ``offset`` back from newest (0 = newest, 1 = previous)."""
    try:
        row = conn.execute(
            "SELECT snapshot_id FROM data_health_snapshot "
            "ORDER BY snapshot_id DESC LIMIT 1 OFFSET ?",
            (offset,),
        ).fetchone()
    except sqlite3.Error:
        return None
    return int(row[0]) if row else None


def _result_rows(conn: sqlite3.Connection, snapshot_id: int) -> list[dict]:
    """The normalized result rows for one snapshot, as plain dicts."""
    cur = conn.execute(
        "SELECT check_id, pillar, dataset, season, status, severity, detail "
        "FROM data_health_result WHERE snapshot_id=? ORDER BY check_id",
        (snapshot_id,),
    )
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def latest(conn: sqlite3.Connection) -> list[dict]:
    """Result rows of the most recent snapshot (``[]`` if none persisted yet)."""
    sid = _snapshot_id_at_offset(conn, 0)
    return _result_rows(conn, sid) if sid is not None else []


def previous(conn: sqlite3.Connection) -> list[dict]:
    """Result rows of the SECOND-most-recent snapshot (``[]`` if < 2 exist)."""
    sid = _snapshot_id_at_offset(conn, 1)
    return _result_rows(conn, sid) if sid is not None else []


# === source-change detection (derived, no event log) ========================


def _source_state(result) -> tuple[str, str]:
    """(source_class, status) for one freshness source-class row, else ('','').

    Accepts both CheckResult objects (``.check_id``/``.status``) and the plain
    dicts read back from a snapshot — so a live run can diff directly against a
    persisted previous snapshot.
    """
    check_id = _field(result, "check_id")
    if not check_id or not check_id.startswith(_SOURCE_CLASS_PREFIX):
        return "", ""
    cls = check_id[len(_SOURCE_CLASS_PREFIX):]
    return cls, (_field(result, "status") or "")


def _field(result, name: str):
    """Read ``name`` off either a dataclass-like object or a dict row."""
    if isinstance(result, dict):
        return result.get(name)
    return getattr(result, name, None)


def diff_source_states(prev_results, curr_results) -> dict:
    """Derive source feed changes between two snapshots' freshness rows.

    Returns ``{"added": [...], "retired": [...], "newly_failing": [...]}`` where
    each list holds source-class names (sorted, deduped):
      * added         — a source class present now that was absent last snapshot.
      * retired       — a source class present last snapshot, gone now.
      * newly_failing — a source class that did NOT have status 'fail' last
                        snapshot but has status 'fail' now (a fresh regression;
                        an already-failing feed is not re-reported as "newly").

    No event-log table: this is the whole add/retire/first-failing story, derived
    purely by diffing — exactly the spec's "derive by diffing snapshots" rule.
    """
    prev: dict[str, str] = {}
    for r in prev_results or []:
        cls, status = _source_state(r)
        if cls:
            prev[cls] = status
    curr: dict[str, str] = {}
    for r in curr_results or []:
        cls, status = _source_state(r)
        if cls:
            curr[cls] = status

    added = sorted(set(curr) - set(prev))
    retired = sorted(set(prev) - set(curr))
    newly_failing = sorted(
        cls
        for cls, status in curr.items()
        if status == "fail" and prev.get(cls) != "fail"
    )
    return {"added": added, "retired": retired, "newly_failing": newly_failing}
