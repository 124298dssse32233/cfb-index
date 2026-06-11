"""Smoke test for the CLI ``main()`` dispatch body.

This is the test that would have caught the 2026-06-11 outage. An unaliased
``from pathlib import Path`` inside ``cli.main()`` made ``Path`` a function-local,
raising ``UnboundLocalError`` at the shared prologue (``schema_path = Path(...)``)
for EVERY command -- the 5 AM collect and 9 AM build both died and nothing
deployed. All ~1778 other tests stayed green because they exercise
``build_parser()`` (argument parsing) or the underlying functions directly;
none execute ``main()``'s dispatch body, so the import-shadowing class of bug
was invisible to CI.

``init-db`` is the cheapest command that traverses the shared prologue
(``AppConfig.from_env`` -> ``Database`` -> ``schema_path = Path(...)`` -> dispatch),
needs no network, and runs against a throwaway DB. If a Path/os/datetime-style
import-shadowing or NameError regression ever returns to that prologue, this test
raises instead of building a DB.
"""
from __future__ import annotations

import sqlite3
import sys

from cfb_rankings.cli import main


def test_resolve_week_smoke(monkeypatch, capsys):
    # resolve-week returns BEFORE the DB prologue -- cheapest guard that the
    # parser builds and the earliest dispatch path runs. (Note: on its own this
    # would NOT have caught the 2026-06-11 bug, because resolve-week returns
    # before line ~2607; that is exactly why the init-db case below exists.)
    monkeypatch.setattr(sys, "argv", ["cfb-rankings", "resolve-week"])
    main()
    assert "season_year" in capsys.readouterr().out


def test_init_db_executes_main_prologue(tmp_path, monkeypatch):
    # init-db passes THROUGH main()'s shared prologue (config + Database +
    # `schema_path = Path(...)`) and then applies the schema. An import-shadowing
    # regression in that prologue raises here instead of exiting clean.
    db_file = tmp_path / "smoke.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    monkeypatch.setattr(sys, "argv", ["cfb-rankings", "init-db"])

    main()  # must not raise

    assert db_file.exists(), "init-db did not create the database file"
    con = sqlite3.connect(str(db_file))
    try:
        tables = {r[0] for r in con.execute(
            "select name from sqlite_master where type='table'"
        )}
    finally:
        con.close()
    # Schema actually applied (base schema + runtime migrations), proving the
    # full prologue + init-db branch executed -- not just an early return.
    assert "conversation_documents" in tables
    assert len(tables) > 10
