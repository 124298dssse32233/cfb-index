"""KWIC (keyword-in-context) quote extraction — Language Layer Wave 4.

For each team's top discourse terms (from ``team_discourse_terms`` week=0 rows),
fetches real fan posts containing that term and extracts short readable passages.
Writes results to ``team_discourse_term_quotes``.

PYTHONUTF8 note: this module never prints raw post text — progress lines carry
only team_id integers and bare [a-z'] terms.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .keyness import _row_get, _clean, load_city_subs, _WS_RE
from ._common import fan_voice_filter_sql


def _fetchall(db: Any, sql: str, params: Any) -> list:
    """Fetch rows — works with both raw sqlite3.Connection and Database wrapper."""
    cur = db.execute(sql, params)
    if cur is None:
        return db.query_all(sql, params)
    return cur.fetchall()

# Maximum window (chars) each side of the matched term.
_WINDOW = 80
# Maximum passages kept per (team, season, term).
_MAX_PASSAGES = 10
# Dedup key length (first N chars of passage).
_DEDUP_PREFIX = 60
# Passage length bounds.
_MIN_LEN = 30
_MAX_LEN = 250


def _extract_passage(text: str, term: str) -> "str | None":
    """Extract a readable window around the first occurrence of *term* in *text*.

    The window is ``_WINDOW`` characters either side of the match, trimmed to
    the nearest word boundary.  Returns ``None`` when the resulting passage is
    shorter than ``_MIN_LEN`` or longer than ``_MAX_LEN`` characters.
    """
    lower_text = text.lower()
    lower_term = term.lower()
    pos = lower_text.find(lower_term)
    if pos == -1:
        return None

    start = max(0, pos - _WINDOW)
    end = min(len(text), pos + len(term) + _WINDOW)

    # Trim to nearest space boundary (don't cut mid-word).
    if start > 0:
        space = text.rfind(" ", start, pos)
        if space != -1:
            start = space + 1

    if end < len(text):
        space = text.find(" ", end)
        if space != -1:
            end = space

    passage = text[start:end].strip()
    # Normalise internal whitespace (newlines, tabs, repeated spaces).
    passage = _WS_RE.sub(" ", passage)

    if len(passage) < _MIN_LEN or len(passage) > _MAX_LEN:
        return None
    return passage


def compute_kwic_quotes(
    db,
    *,
    seasons: "int | list[int]",
    teams: "list[int] | None" = None,
    top_terms: int = 5,
    commit: bool = False,
) -> dict[str, Any]:
    """Extract keyword-in-context passages for each team's top discourse terms.

    Parameters
    ----------
    db:
        Open ``sqlite3.Connection`` (or compatible) object.
    seasons:
        Single season year or list of season years to process.
    teams:
        Optional list of ``team_id`` values to restrict processing. ``None``
        means all teams that have rows in ``team_discourse_terms``.
    top_terms:
        How many top-ranked terms per team to fetch passages for (uses
        ``term_rank <= top_terms`` from ``team_discourse_terms``).
    commit:
        When ``True``, DELETE existing rows for each (team_id, season_year,
        week=0, term) and INSERT the extracted passages.  When ``False`` the
        function is a dry-run — nothing is written to the DB.

    Returns
    -------
    dict
        ``{"teams_processed": int, "quotes_written": int, "seasons": list}``
    """
    if isinstance(seasons, int):
        seasons = [seasons]
    seasons = list(seasons)

    where_frag, city_params = fan_voice_filter_sql("d")

    teams_seen: set[int] = set()
    total_quotes = 0

    for season in seasons:
        # ------------------------------------------------------------------
        # 1. Fetch top-ranked terms for the season (week=0 = season cut).
        # ------------------------------------------------------------------
        term_sql = """
            SELECT tdt.team_id, tdt.term, tdt.term_rank
            FROM team_discourse_terms tdt
            WHERE tdt.season_year = :season
              AND tdt.week = 0
              AND tdt.term_rank <= :top_terms
            ORDER BY tdt.team_id, tdt.term_rank
        """
        term_rows = _fetchall(
            db, term_sql, {"season": season, "top_terms": top_terms}
        )

        # Group into {team_id: [term, ...]} respecting optional team filter.
        team_terms: dict[int, list[str]] = {}
        for row in term_rows:
            tid = _row_get(row, "team_id")
            term = _row_get(row, "term")
            if teams is not None and tid not in teams:
                continue
            team_terms.setdefault(tid, []).append(term)

        # ------------------------------------------------------------------
        # 2. For each (team, term) fetch matching docs and extract passages.
        # ------------------------------------------------------------------
        for tid, terms in team_terms.items():
            for term in terms:
                bind: dict[str, Any] = {
                    **city_params,
                    "season": season,
                    "tid": tid,
                    "term_like": "%" + term + "%",
                }
                doc_sql = f"""
                    SELECT COALESCE(d.body_text, d.title_text) AS text,
                           COALESCE(d.source_subchannel, d.source_name) AS src
                    FROM conversation_documents d
                    JOIN conversation_team_tags t
                         ON t.conversation_document_id = d.conversation_document_id
                    WHERE t.team_id = :tid
                      AND {where_frag}
                      AND LOWER(COALESCE(d.body_text, d.title_text)) LIKE :term_like
                    ORDER BY d.conversation_document_id DESC
                    LIMIT 200
                """
                doc_rows = _fetchall(db, doc_sql, bind)

                passages: list[str] = []
                seen_prefixes: set[str] = set()
                for doc_row in doc_rows:
                    raw = _row_get(doc_row, "text")
                    if not raw:
                        continue
                    passage = _extract_passage(str(raw), term)
                    if passage is None:
                        continue
                    prefix = passage[:_DEDUP_PREFIX]
                    if prefix in seen_prefixes:
                        continue
                    seen_prefixes.add(prefix)
                    passages.append(passage)
                    if len(passages) >= _MAX_PASSAGES:
                        break

                if not passages:
                    continue

                teams_seen.add(tid)

                # ----------------------------------------------------------
                # 3. Optionally persist to team_discourse_term_quotes.
                # ----------------------------------------------------------
                if commit:
                    db.execute(
                        """
                        DELETE FROM team_discourse_term_quotes
                        WHERE team_id = :tid
                          AND season_year = :season
                          AND week = 0
                          AND term = :term
                        """,
                        {"tid": tid, "season": season, "term": term},
                    )
                    computed_at = datetime.now(timezone.utc).isoformat()
                    for idx, passage in enumerate(passages):
                        db.execute(
                            """
                            INSERT INTO team_discourse_term_quotes
                                (team_id, season_year, week, term,
                                 position_index, passage, computed_at_utc)
                            VALUES
                                (:tid, :season, 0, :term,
                                 :idx, :passage, :computed_at)
                            """,
                            {
                                "tid": tid,
                                "season": season,
                                "term": term,
                                "idx": idx,
                                "passage": passage,
                                "computed_at": computed_at,
                            },
                        )
                    db.commit()

                total_quotes += len(passages)

    return {
        "teams_processed": len(teams_seen),
        "quotes_written": total_quotes,
        "seasons": seasons,
    }
