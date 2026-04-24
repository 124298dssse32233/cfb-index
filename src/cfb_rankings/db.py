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

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self._path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("pragma foreign_keys = on")
        connection.execute("pragma busy_timeout = 30000")
        try:
            yield connection
        finally:
            connection.close()

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
