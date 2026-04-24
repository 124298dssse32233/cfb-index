"""Tests for the retry-on-OperationalError wrapper in cfb_rankings.db."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from cfb_rankings import db as db_mod
from cfb_rankings.db import Database, _is_retryable, _with_retry


def test_is_retryable_matches_common_transient_phrases() -> None:
    for msg in (
        "database is locked",
        "attempt to write a readonly database",
        "DISK I/O ERROR",  # case-insensitive
        "database schema has changed",
    ):
        exc = sqlite3.OperationalError(msg)
        assert _is_retryable(exc), msg


def test_is_retryable_returns_false_for_syntax_error() -> None:
    exc = sqlite3.OperationalError("no such table: foo")
    assert not _is_retryable(exc)


def test_with_retry_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise sqlite3.OperationalError("database is locked")
        return "ok"

    # Speed up the test.
    monkeypatch.setattr(db_mod, "_RETRY_BASE_SECONDS", 0.001)
    monkeypatch.setattr(db_mod, "_RETRY_CAP_SECONDS", 0.01)
    assert _with_retry("test_op", fn) == "ok"
    assert calls["n"] == 3


def test_with_retry_raises_non_retryable_immediately() -> None:
    def fn() -> None:
        raise sqlite3.OperationalError("no such column: bar")

    with pytest.raises(sqlite3.OperationalError, match="no such column"):
        _with_retry("test_op", fn)


def test_with_retry_raises_after_max_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db_mod, "_RETRY_BASE_SECONDS", 0.001)
    monkeypatch.setattr(db_mod, "_RETRY_CAP_SECONDS", 0.01)
    monkeypatch.setattr(db_mod, "_RETRY_MAX_ATTEMPTS", 3)

    def fn() -> None:
        raise sqlite3.OperationalError("database is locked")

    with pytest.raises(sqlite3.OperationalError, match="locked"):
        _with_retry("test_op", fn)


def test_database_execute_still_raises_syntax_errors(tmp_path: Path) -> None:
    # Sanity: real DB writes still work; non-retryable errors still surface.
    db = Database(str(tmp_path / "x.db"))
    db.execute("create table t (k text)")
    with pytest.raises(sqlite3.OperationalError):
        db.execute("select * from no_such_table")


def test_database_execute_happy_path_round_trip(tmp_path: Path) -> None:
    db = Database(str(tmp_path / "y.db"))
    db.execute("create table t (k text, v integer)")
    db.execute("insert into t values (:k, :v)", {"k": "a", "v": 1})
    rows = db.query_all("select k, v from t")
    assert rows == [{"k": "a", "v": 1}]
