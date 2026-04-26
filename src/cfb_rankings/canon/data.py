"""Read/write helpers for canon_lists, canon_entries, canon_revision_history.

Pure SQLite, no team_pages imports.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, asdict
from typing import Iterable


@dataclass(frozen=True)
class CanonListMeta:
    list_slug: str
    title: str
    edition_year: int
    list_kind: str
    description: str
    methodology_notes: str | None
    entry_count: int
    next_revision_year: int | None


@dataclass
class CanonEntry:
    list_slug: str
    rank: int
    entity_kind: str
    entity_slug: str
    entity_display_name: str
    summary_short: str
    program_slug: str | None = None
    program_label: str | None = None
    era_label: str | None = None
    editorial_paragraph: str | None = None
    statline: str | None = None
    cohort_split_stat_rank: int | None = None
    cohort_split_casual_rank: int | None = None
    cohort_split_label: str | None = None
    prior_year_rank: int | None = None
    rank_delta_label: str | None = None


# --------------------------------------------------------------------------
# Writes
# --------------------------------------------------------------------------

def upsert_list_meta(con: sqlite3.Connection, meta: CanonListMeta) -> None:
    con.execute(
        """
        INSERT INTO canon_lists (
            list_slug, title, edition_year, list_kind, description,
            methodology_notes, entry_count, published_at, next_revision_year
        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
        ON CONFLICT(list_slug) DO UPDATE SET
            title = excluded.title,
            edition_year = excluded.edition_year,
            list_kind = excluded.list_kind,
            description = excluded.description,
            methodology_notes = excluded.methodology_notes,
            entry_count = excluded.entry_count,
            published_at = excluded.published_at,
            next_revision_year = excluded.next_revision_year
        """,
        (
            meta.list_slug, meta.title, meta.edition_year, meta.list_kind,
            meta.description, meta.methodology_notes, meta.entry_count,
            meta.next_revision_year,
        ),
    )


def replace_entries(
    con: sqlite3.Connection,
    list_slug: str,
    entries: Iterable[CanonEntry],
) -> int:
    """Atomically replace all entries for ``list_slug``."""
    con.execute("DELETE FROM canon_entries WHERE list_slug = ?", (list_slug,))
    rows: list[tuple] = []
    for e in entries:
        if e.list_slug != list_slug:
            raise ValueError(
                f"entry list_slug {e.list_slug!r} != target {list_slug!r}"
            )
        rows.append((
            e.list_slug, e.rank, e.entity_kind, e.entity_slug,
            e.entity_display_name, e.program_slug, e.program_label,
            e.era_label, e.summary_short, e.editorial_paragraph,
            e.statline, e.cohort_split_stat_rank,
            e.cohort_split_casual_rank, e.cohort_split_label,
            e.prior_year_rank, e.rank_delta_label,
        ))
    con.executemany(
        """
        INSERT INTO canon_entries (
            list_slug, rank, entity_kind, entity_slug, entity_display_name,
            program_slug, program_label, era_label, summary_short,
            editorial_paragraph, statline,
            cohort_split_stat_rank, cohort_split_casual_rank, cohort_split_label,
            prior_year_rank, rank_delta_label
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def record_revision_history(
    con: sqlite3.Connection,
    list_slug: str,
    edition_year: int,
    entries: Iterable[CanonEntry],
) -> int:
    """Snapshot the current ranks into canon_revision_history.

    Idempotent on (list_slug, edition_year, entity_slug).
    """
    rows = [(list_slug, edition_year, e.entity_slug, e.rank) for e in entries]
    con.executemany(
        """
        INSERT INTO canon_revision_history
            (list_slug, edition_year, entity_slug, rank_in_year)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(list_slug, edition_year, entity_slug) DO UPDATE SET
            rank_in_year = excluded.rank_in_year
        """,
        rows,
    )
    return len(rows)


# --------------------------------------------------------------------------
# Reads
# --------------------------------------------------------------------------

def fetch_list_meta(
    con: sqlite3.Connection, list_slug: str,
) -> CanonListMeta | None:
    row = con.execute(
        """
        SELECT list_slug, title, edition_year, list_kind, description,
               methodology_notes, entry_count, next_revision_year
        FROM canon_lists WHERE list_slug = ?
        """,
        (list_slug,),
    ).fetchone()
    if not row:
        return None
    return CanonListMeta(*row)


def fetch_all_list_metas(con: sqlite3.Connection) -> list[CanonListMeta]:
    rows = con.execute(
        """
        SELECT list_slug, title, edition_year, list_kind, description,
               methodology_notes, entry_count, next_revision_year
        FROM canon_lists
        ORDER BY edition_year DESC, title
        """,
    ).fetchall()
    return [CanonListMeta(*r) for r in rows]


def fetch_entries(
    con: sqlite3.Connection, list_slug: str,
) -> list[CanonEntry]:
    rows = con.execute(
        """
        SELECT list_slug, rank, entity_kind, entity_slug, entity_display_name,
               summary_short, program_slug, program_label, era_label,
               editorial_paragraph, statline,
               cohort_split_stat_rank, cohort_split_casual_rank,
               cohort_split_label, prior_year_rank, rank_delta_label
        FROM canon_entries
        WHERE list_slug = ?
        ORDER BY rank
        """,
        (list_slug,),
    ).fetchall()
    out: list[CanonEntry] = []
    for r in rows:
        out.append(CanonEntry(
            list_slug=r[0], rank=r[1], entity_kind=r[2], entity_slug=r[3],
            entity_display_name=r[4], summary_short=r[5],
            program_slug=r[6], program_label=r[7], era_label=r[8],
            editorial_paragraph=r[9], statline=r[10],
            cohort_split_stat_rank=r[11], cohort_split_casual_rank=r[12],
            cohort_split_label=r[13], prior_year_rank=r[14],
            rank_delta_label=r[15],
        ))
    return out


def fetch_prior_year_rank(
    con: sqlite3.Connection,
    list_slug: str,
    entity_slug: str,
    current_year: int,
) -> int | None:
    """Most-recent prior-year rank for an entity in ``list_slug``."""
    row = con.execute(
        """
        SELECT rank_in_year FROM canon_revision_history
        WHERE list_slug = ? AND entity_slug = ? AND edition_year < ?
        ORDER BY edition_year DESC LIMIT 1
        """,
        (list_slug, entity_slug, current_year),
    ).fetchone()
    return int(row[0]) if row else None


# --------------------------------------------------------------------------
# Homepage helper
# --------------------------------------------------------------------------

def load_featured_entry(
    con: sqlite3.Connection,
    week_index: int,
    *,
    fallback_path: str | None = None,
) -> dict:
    """Return the entry-of-the-week for the homepage Canon block.

    Strategy:
      1. If any canon_entries exist, rotate through the union of every
         list's top-5 keyed by ``week_index``.
      2. If no entries exist (Sprint 11 not yet generated), fall back to
         ``stub_data/canon_featured.json``.

    Returned dict shape mirrors Sprint 9's hardcoded Caleb Williams entry.
    """
    n = con.execute("SELECT COUNT(*) FROM canon_entries").fetchone()[0]
    if n == 0:
        return _load_stub(fallback_path)

    rows = con.execute(
        """
        SELECT e.list_slug, e.rank, e.entity_slug, e.entity_display_name,
               e.program_slug, e.program_label, e.era_label,
               e.summary_short, e.editorial_paragraph, e.statline,
               l.title, l.edition_year
        FROM canon_entries e
        JOIN canon_lists l ON l.list_slug = e.list_slug
        WHERE e.rank <= 5
        ORDER BY l.edition_year DESC, e.list_slug, e.rank
        """,
    ).fetchall()
    if not rows:
        return _load_stub(fallback_path)

    chosen = rows[week_index % len(rows)]
    return {
        "list_slug": chosen[0],
        "list_title": chosen[10],
        "edition_year": chosen[11],
        "rank": chosen[1],
        "entity_slug": chosen[2],
        "entity_display_name": chosen[3],
        "program_slug": chosen[4],
        "program_label": chosen[5],
        "era_label": chosen[6],
        "summary_short": chosen[7],
        "editorial_paragraph": chosen[8],
        "statline": chosen[9],
        "source": "db",
    }


def _load_stub(fallback_path: str | None) -> dict:
    import json
    from pathlib import Path
    if fallback_path is None:
        # Default location relative to repo root.
        fallback_path = "stub_data/canon_featured.json"
    p = Path(fallback_path)
    if not p.exists():
        return {
            "list_slug": "the-100-best-players-cfp-era",
            "list_title": "The 100 Best Players of the CFP Era",
            "edition_year": 2026,
            "rank": 1,
            "entity_slug": "tua-tagovailoa",
            "entity_display_name": "Tua Tagovailoa",
            "program_slug": "alabama",
            "program_label": "Alabama",
            "era_label": "Saban Era · 2017–2019",
            "summary_short": "Author of the second-and-26 throw and "
                              "the modern blueprint for SEC-quarterback as "
                              "first-overall reality.",
            "editorial_paragraph": None,
            "statline": "186.6 RTGN as a starter · 87 TD · 11 INT",
            "source": "stub-default",
        }
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    data["source"] = "stub-file"
    return data
