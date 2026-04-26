"""Shared runtime helpers for the receipts pipeline.

Keeps DB-connection wiring, slug normalization, and path helpers in one
spot so the rest of the module stays testable.
"""
from __future__ import annotations

import os
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

# Where the live DB lives on the dev box. Production runs override via env.
DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "cfb_rankings.db"


def db_path() -> Path:
    return Path(os.environ.get("CFB_RANKINGS_DB", str(DEFAULT_DB_PATH)))


@contextmanager
def db_conn(read_only: bool = False) -> Iterator[sqlite3.Connection]:
    p = db_path()
    if read_only:
        uri = f"file:{p}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Stable lowercase-hyphen slug. Used for source_slug, entity_slug."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    s = _SLUG_RE.sub("-", ascii_only.lower()).strip("-")
    return s


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def site_output_root() -> Path:
    return Path(__file__).resolve().parents[3] / "output" / "site"


def receipts_output_root() -> Path:
    return site_output_root() / "receipts"


def receipts_assets_root() -> Path:
    return Path(__file__).resolve().parent / "assets"
