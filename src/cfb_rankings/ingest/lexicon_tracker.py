"""Curated fan-slang lexicon tracker (Fan Intelligence suite).

The existing ``mine-lexicon`` step surfaces *emergent* phrase spikes
(``lexicon_weekly``) — it finds what's new. This module is its complement: a
fixed, editorially-governed watchlist (``seeds/lexicon_terms.yaml``) counted
**daily, forever**, so branded terms ("aura", "cooked", "rent free") build an
unbroken history per team. The aggregates land in ``lexicon_term_daily`` and
survive any future raw-text purge — which is exactly why this must run in the
collection window, before ``purge-reddit-raw-content`` is ever scheduled.

Matching mirrors ``team_name_tagger``: text and variants are normalized the
same way (non-alphanumerics collapse to spaces) and matched on word
boundaries. Variant spans within a term group are merged before counting, so
"we're so back" does not also count its inner "so back".

Row shapes written per (term_group, day):
- one row per attributed team   (team_id set,  source_name='all')
- one row per source            (team_id NULL, source_name=<source>)
- one corpus-wide row           (team_id NULL, source_name='all')

CLI:
    python manage.py track-lexicon [--days N] [--backfill]
        [--terms-file seeds/lexicon_terms.yaml]
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from cfb_rankings.common.week import resolve_week
from cfb_rankings.db import Database

logger = logging.getLogger(__name__)

DEFAULT_TERMS_FILE = Path("seeds") / "lexicon_terms.yaml"
_DOC_CHUNK = 5000
_TARGET_CHUNK = 500


def _normalize(text: str) -> str:
    """Lowercase, strip non-alphanumerics to spaces, collapse whitespace.

    Identical to ``team_name_tagger._normalize`` so seed variants like
    "he's him" compare against documents the same way ("he s him").
    """
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", (text or "").lower())).strip()


def _word_boundary_pattern(normalized: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(normalized)}(?![A-Za-z0-9])")


def load_term_groups(path: Path | str = DEFAULT_TERMS_FILE) -> list[dict[str, Any]]:
    """Load the watchlist: ``[{group, label, patterns: [compiled...]}, ...]``."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    groups: list[dict[str, Any]] = []
    for entry in raw.get("terms", []):
        group = str(entry.get("group") or "").strip()
        variants = [_normalize(str(v)) for v in entry.get("variants") or []]
        variants = [v for v in variants if v]
        if not group or not variants:
            continue
        groups.append(
            {
                "group": group,
                "label": str(entry.get("label") or group),
                "patterns": [_word_boundary_pattern(v) for v in variants],
            }
        )
    return groups


def _merged_span_count(patterns: list[re.Pattern[str]], haystack: str) -> int:
    """Count non-overlapping matched spans across all variants of one group."""
    spans = sorted(
        (m.start(), m.end())
        for pattern in patterns
        for m in pattern.finditer(haystack)
    )
    if not spans:
        return 0
    merged = 1
    _, cur_end = spans[0]
    for start, end in spans[1:]:
        if start >= cur_end:
            merged += 1
            cur_end = end
        else:
            cur_end = max(cur_end, end)
    return merged


def _doc_team_ids(db: Database, doc_ids: list[int]) -> dict[int, set[int]]:
    """Map conversation_document_id -> distinct targeted team_ids."""
    teams_by_doc: dict[int, set[int]] = defaultdict(set)
    for offset in range(0, len(doc_ids), _TARGET_CHUNK):
        chunk = doc_ids[offset : offset + _TARGET_CHUNK]
        placeholders = ",".join(f":d_{i}" for i in range(len(chunk)))
        params = {f"d_{i}": doc_id for i, doc_id in enumerate(chunk)}
        rows = db.query_all(
            f"""
            select conversation_document_id, team_id
            from conversation_document_targets
            where target_type = 'team'
              and team_id is not null
              and conversation_document_id in ({placeholders})
            """,
            params,
        )
        for row in rows:
            teams_by_doc[int(row["conversation_document_id"])].add(int(row["team_id"]))
    return teams_by_doc


def track_lexicon_terms(
    db: Database,
    *,
    days: int = 3,
    backfill: bool = False,
    terms_file: Path | str = DEFAULT_TERMS_FILE,
) -> dict[str, int]:
    """Count watchlist terms over the document window and rewrite the aggregates.

    Idempotent per day: every day touched by the scan is deleted and
    re-inserted, so re-runs (and the daily 3-day rolling window) converge.
    """
    groups = load_term_groups(terms_file)
    if not groups:
        return {"docs_scanned": 0, "docs_matched": 0, "rows_written": 0, "days_touched": 0}

    where = "(length(coalesce(cd.body_text, '')) > 0 or length(coalesce(cd.title_text, '')) > 0)"
    params: dict[str, Any] = {}
    if not backfill:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max(1, days))).strftime("%Y-%m-%d")
        where += " and substr(cd.external_created_at_utc, 1, 10) >= :cutoff"
        params["cutoff"] = cutoff

    # (group, day, team_id|None, source_name) -> [doc_count, mention_count]
    agg: dict[tuple[str, str, int | None, str], list[int]] = defaultdict(lambda: [0, 0])
    docs_scanned = 0
    docs_matched = 0
    last_id = 0
    while True:
        rows = db.query_all(
            f"""
            select cd.conversation_document_id as doc_id,
                   cd.source_name,
                   substr(cd.external_created_at_utc, 1, 10) as as_of_date,
                   cd.title_text,
                   cd.body_text
            from conversation_documents cd
            where cd.conversation_document_id > :last_id
              and {where}
            order by cd.conversation_document_id
            limit {_DOC_CHUNK}
            """,
            {**params, "last_id": last_id},
        )
        if not rows:
            break
        last_id = int(rows[-1]["doc_id"])

        matched_docs: list[tuple[int, str, str, dict[str, int]]] = []
        for row in rows:
            docs_scanned += 1
            haystack = _normalize(
                (row.get("title_text") or "") + " " + (row.get("body_text") or "")
            )
            if not haystack:
                continue
            hits: dict[str, int] = {}
            for spec in groups:
                count = _merged_span_count(spec["patterns"], haystack)
                if count:
                    hits[spec["group"]] = count
            if hits:
                day = str(row.get("as_of_date") or "")[:10]
                if len(day) == 10:
                    matched_docs.append(
                        (int(row["doc_id"]), day, str(row.get("source_name") or "unknown"), hits)
                    )

        if matched_docs:
            docs_matched += len(matched_docs)
            teams_by_doc = _doc_team_ids(db, [d[0] for d in matched_docs])
            for doc_id, day, source, hits in matched_docs:
                team_ids = teams_by_doc.get(doc_id, set())
                for group, count in hits.items():
                    for team_id in team_ids:
                        cell = agg[(group, day, team_id, "all")]
                        cell[0] += 1
                        cell[1] += count
                    per_source = agg[(group, day, None, source)]
                    per_source[0] += 1
                    per_source[1] += count
                    corpus = agg[(group, day, None, "all")]
                    corpus[0] += 1
                    corpus[1] += count

    days_touched = sorted({key[1] for key in agg})
    if days_touched:
        week_cache: dict[str, tuple[int | None, int | None]] = {}
        for day in days_touched:
            try:
                wk = resolve_week(day)
                week_cache[day] = (wk.season_year, wk.week)
            except Exception:  # noqa: BLE001 — malformed historic dates fall back to NULL keys
                week_cache[day] = (None, None)

        if backfill:
            db.execute("delete from lexicon_term_daily")
        else:
            db.execute(
                "delete from lexicon_term_daily where as_of_date >= :first_day",
                {"first_day": days_touched[0]},
            )
        insert_rows = [
            {
                "term_group": group,
                "as_of_date": day,
                "season_year": week_cache[day][0],
                "week": week_cache[day][1],
                "team_id": team_id,
                "source_name": source,
                "doc_count": counts[0],
                "mention_count": counts[1],
            }
            for (group, day, team_id, source), counts in agg.items()
        ]
        db.execute_many(
            """
            insert into lexicon_term_daily (
                term_group, as_of_date, season_year, week,
                team_id, source_name, doc_count, mention_count
            ) values (
                :term_group, :as_of_date, :season_year, :week,
                :team_id, :source_name, :doc_count, :mention_count
            )
            """,
            insert_rows,
        )
        rows_written = len(insert_rows)
    else:
        rows_written = 0

    logger.info(
        "track-lexicon: scanned=%d matched=%d rows=%d days=%d backfill=%s",
        docs_scanned, docs_matched, rows_written, len(days_touched), backfill,
    )
    return {
        "docs_scanned": docs_scanned,
        "docs_matched": docs_matched,
        "rows_written": rows_written,
        "days_touched": len(days_touched),
    }


__all__ = ["track_lexicon_terms", "load_term_groups", "DEFAULT_TERMS_FILE"]
