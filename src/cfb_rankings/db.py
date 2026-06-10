from __future__ import annotations

import logging
import os
import random
import time
from contextlib import contextmanager
from pathlib import Path
import re
import sqlite3
from typing import Any, Callable, Iterable, TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")

# Transient-error retry. On Windows under Dropbox/OneDrive/Defender contention
# we see SQLite occasionally raise OperationalError with "database is locked"
# or "attempt to write a readonly database" — the file is momentarily held by
# the sync/scan process. These are harmless if retried, and fatal if not. Env
# overrides exist so Kevin can tune without editing code.
_RETRY_MAX_ATTEMPTS = int(os.environ.get("CFB_DB_RETRY_ATTEMPTS", "6"))
_RETRY_BASE_SECONDS = float(os.environ.get("CFB_DB_RETRY_BASE", "0.25"))
_RETRY_CAP_SECONDS = float(os.environ.get("CFB_DB_RETRY_CAP", "5.0"))
_RETRYABLE_PHRASES = (
    "database is locked",
    "readonly database",
    "disk i/o error",
    "database schema has changed",
)


def _is_retryable(exc: sqlite3.OperationalError) -> bool:
    message = (str(exc) or "").lower()
    return any(phrase in message for phrase in _RETRYABLE_PHRASES)


def _with_retry(op_name: str, fn: Callable[[], T]) -> T:
    last: sqlite3.OperationalError | None = None
    for attempt in range(1, _RETRY_MAX_ATTEMPTS + 1):
        try:
            return fn()
        except sqlite3.OperationalError as exc:
            if not _is_retryable(exc) or attempt == _RETRY_MAX_ATTEMPTS:
                raise
            backoff = min(
                _RETRY_CAP_SECONDS,
                _RETRY_BASE_SECONDS * (2 ** (attempt - 1)),
            ) * (0.75 + random.random() * 0.5)  # jitter
            log.warning(
                "db.%s attempt %d/%d hit %s — sleeping %.2fs and retrying",
                op_name, attempt, _RETRY_MAX_ATTEMPTS, exc, backoff,
            )
            time.sleep(backoff)
            last = exc
    if last is not None:
        raise last
    raise RuntimeError("unreachable")


class Database:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._path = _sqlite_path_from_dsn(dsn)
        # When set (inside a session()), every query reuses this one connection
        # instead of opening a fresh one. See session() for why.
        self._session_conn: sqlite3.Connection | None = None

    def _configure(self, connection: sqlite3.Connection) -> None:
        connection.row_factory = sqlite3.Row
        connection.execute("pragma foreign_keys = on")
        connection.execute("pragma busy_timeout = 30000")
        # Read-side perf for the large (>1GB) local DB: memory-map the file so
        # the OS page cache stays shared, and keep GROUP BY / ORDER BY temp
        # b-trees in RAM. Pure read optimizations — no durability or behavior
        # change — each wrapped so an unsupported pragma can't break a connection.
        for _pragma in ("pragma mmap_size = 2147483648", "pragma temp_store = memory"):
            try:
                connection.execute(_pragma)
            except sqlite3.Error:
                pass

    @contextmanager
    def connection(self):
        # Inside a session(), reuse the one cached connection and DON'T close it
        # here (session() owns its lifetime). Otherwise behave as before: a fresh
        # connection per call. The per-call path pays ~3ms of connect + 4 PRAGMAs
        # + 2GB mmap setup; reuse drops that to ~0.007ms — a 400x cut that turns
        # a ~50-min connection-churn tax across a full build into seconds.
        if self._session_conn is not None:
            yield self._session_conn
            return
        connection = sqlite3.connect(self._path, timeout=30.0)
        self._configure(connection)
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def session(self):
        """Reuse ONE connection for every query inside this block.

        Read-heavy bulk paths (the site build fires ~1M small indexed queries)
        otherwise pay a fresh connect + 4 PRAGMAs + 2GB mmap setup PER query
        (~3ms each → tens of minutes of pure overhead). Reusing one connection
        drops per-query overhead ~400x. This is a pure connection-lifecycle
        change: identical queries, identical results, same per-mutation commit
        semantics. SINGLE-THREADED ONLY (sqlite connections are thread-bound);
        nests harmlessly (an inner session() is a no-op).
        """
        if self._session_conn is not None:
            yield  # already in a session — reuse the outer one
            return
        conn = sqlite3.connect(self._path, timeout=30.0)
        self._configure(conn)
        self._session_conn = conn
        try:
            yield
        finally:
            self._session_conn = None
            try:
                conn.close()
            except sqlite3.Error:
                pass

    def apply_sql_file(self, path: str | Path) -> None:
        sql_text = Path(path).read_text(encoding="utf-8")

        def _op() -> None:
            with self.connection() as conn:
                conn.executescript(sql_text)
                conn.commit()

        _with_retry("apply_sql_file", _op)

    def execute(self, query: str, params: dict[str, Any] | tuple[Any, ...] | None = None) -> None:
        normalized_query = _normalize_query(query)

        def _op() -> None:
            with self.connection() as conn:
                conn.execute(normalized_query, params or {})
                conn.commit()

        _with_retry("execute", _op)

    def execute_many(self, query: str, rows: Iterable[dict[str, Any] | tuple[Any, ...]]) -> None:
        batch = list(rows)
        if not batch:
            return
        normalized_query = _normalize_query(query)

        def _op() -> None:
            with self.connection() as conn:
                conn.executemany(normalized_query, batch)
                conn.commit()

        _with_retry("execute_many", _op)

    def query_all(
        self,
        query: str,
        params: dict[str, Any] | tuple[Any, ...] | None = None,
    ) -> list[dict[str, Any]]:
        normalized_query = _normalize_query(query)

        def _op() -> list[dict[str, Any]]:
            with self.connection() as conn:
                cursor = conn.execute(normalized_query, params or {})
                rows = [dict(row) for row in cursor.fetchall()]
                if _is_mutating_query(normalized_query):
                    conn.commit()
                return rows

        return _with_retry("query_all", _op)

    def query_one(
        self,
        query: str,
        params: dict[str, Any] | tuple[Any, ...] | None = None,
    ) -> dict[str, Any] | None:
        rows = self.query_all(query, params)
        return rows[0] if rows else None

    def upsert_many(
        self,
        table: str,
        rows: list[dict[str, Any]],
        conflict_columns: list[str],
        update_columns: list[str] | None = None,
    ) -> None:
        if not rows:
            return

        columns = list(rows[0].keys())
        update_columns = update_columns or [column for column in columns if column not in conflict_columns]
        column_csv = ", ".join(columns)
        placeholder_csv = ", ".join(f":{column}" for column in columns)
        conflict_csv = ", ".join(conflict_columns)
        if update_columns:
            updates = ", ".join(f"{column} = excluded.{column}" for column in update_columns)
            query = f"""
                insert into {table} ({column_csv})
                values ({placeholder_csv})
                on conflict ({conflict_csv})
                do update set {updates}
            """
        else:
            query = f"""
                insert into {table} ({column_csv})
                values ({placeholder_csv})
                on conflict ({conflict_csv})
                do nothing
            """

        def _op() -> None:
            with self.connection() as conn:
                conn.executemany(query, rows)
                conn.commit()

        _with_retry("upsert_many", _op)

    def column_exists(self, table: str, column: str) -> bool:
        with self.connection() as conn:
            rows = conn.execute(f"pragma table_info({table})").fetchall()
            return any(str(row["name"]) == column for row in rows)


def _sqlite_path_from_dsn(dsn: str) -> str:
    if dsn.startswith("sqlite:///"):
        relative = dsn[len("sqlite:///") :]
        return str(Path(relative).resolve())
    return str(Path(dsn).resolve())


def _normalize_query(query: str) -> str:
    query = re.sub(r"%\((\w+)\)s", r":\1", query)
    query = query.replace("now()", "CURRENT_TIMESTAMP")
    return query


def _is_mutating_query(query: str) -> bool:
    stripped = query.lstrip().lower()
    return stripped.startswith(("insert", "update", "delete", "replace"))
