from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable


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
        with self.connection() as conn:
            conn.executescript(sql_text)
            conn.commit()

    def execute(self, query: str, params: dict[str, Any] | tuple[Any, ...] | None = None) -> None:
        normalized_query = _normalize_query(query)
        with self.connection() as conn:
            conn.execute(normalized_query, params or {})
            conn.commit()

    def execute_many(self, query: str, rows: Iterable[dict[str, Any] | tuple[Any, ...]]) -> None:
        batch = list(rows)
        if not batch:
            return
        normalized_query = _normalize_query(query)
        with self.connection() as conn:
            conn.executemany(normalized_query, batch)
            conn.commit()

    def query_all(
        self,
        query: str,
        params: dict[str, Any] | tuple[Any, ...] | None = None,
    ) -> list[dict[str, Any]]:
        normalized_query = _normalize_query(query)
        with self.connection() as conn:
            cursor = conn.execute(normalized_query, params or {})
            rows = [dict(row) for row in cursor.fetchall()]
            if _is_mutating_query(normalized_query):
                conn.commit()
            return rows

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

        with self.connection() as conn:
            conn.executemany(query, rows)
            conn.commit()

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
