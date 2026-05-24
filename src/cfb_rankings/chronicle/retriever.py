"""Chronicle evidence retriever — hybrid lexical + semantic + rerank pipeline.

PRECONDITION: source_trust.py must exist (Task #102) — import will fail otherwise.

Architecture
------------
Three ranked layers are fused via Reciprocal Rank Fusion (RRF):

  1. SQL/FTS5 (lexical) — always executes; falls back to LIKE queries when no
     FTS5 virtual table is present. Results in this layer are the only rows
     that reach the LLM *today*.

  2. Dense semantic (BGE-M3) — stubbed with ``NullDenseEncoder`` that returns
     zero vectors. Real encoder wired in P1 when ``sentence-transformers`` +
     ``torch`` are added as optional deps. The RRF fusion code is real and
     correct even against the stub.

  3. Cross-encoder rerank — stubbed with ``NullCrossEncoder`` that passes
     scores through unchanged. Real cross-encoder wired alongside dense in P1.

Public API
----------
``retrieve_evidence(db, query)``      — top-level call; returns ranked list
``compute_evidence_hash(rows)``       — deterministic cache key component
``EvidenceRow``                       — Pydantic v2 model for one evidence unit
``RetrievalQuery``                    — Pydantic v2 model for a retrieval request
``EvidenceRetrievalError``            — raised on unrecoverable retrieval failures

Deferred deps (not imported at module load time)
-------------------------------------------------
- ``sentence_transformers``  — dense encoder (P1)
- ``torch``                  — required by sentence_transformers (P1)
- ``numpy`` is already a project dep; imported at module level.
"""
from __future__ import annotations

import abc
import hashlib
import json
import logging
import warnings
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, Field

from cfb_rankings.chronicle.source_trust import SOURCE_TRUST, filter_evidence

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class EvidenceRetrievalError(RuntimeError):
    """Raised when the retriever cannot satisfy a query."""


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class EvidenceRow(BaseModel):
    """One unit of evidence retrieved for LLM context."""

    source: str
    """Source identifier: 'cfbd' | 'espn' | 'on3' | '247sports' | 'rivals' |
    'cfbi_db' | 'wikipedia' | 'reddit' | 'twitter' | 'polymarket' | 'conversation'"""

    source_id: str | None = None
    """Optional source-specific ID for citation."""

    trust: Literal["high", "low", "blocked"]
    """Trust tier assigned at retrieval time via source_trust.SOURCE_TRUST."""

    kind: str
    """Evidence category: 'stat' | 'moment' | 'honor' | 'quote' | 'market' |
    'biography' | 'schedule'"""

    payload: dict[str, Any]
    """The actual evidence content as a freeform dict."""

    text: str
    """Canonical text representation used for FTS / embedding."""

    relevance_score: float = 0.0
    """BM25 / dense / RRF-fused ranking score. Higher = more relevant."""

    season_year: int | None = None
    week_number: int | None = None
    entity_slug: str | None = None
    timestamp_utc: str | None = None

    def evidence_hash_input(self) -> str:
        """Canonical string used to compute evidence_hash for cache keys."""
        return f"{self.source}|{self.source_id or ''}|{self.kind}|{self.text}"


class RetrievalQuery(BaseModel):
    """Specifies what evidence to fetch for a card-generation call."""

    entity_slug: str
    """Player or team slug (e.g., 'cam-ward', 'ohio-state')."""

    entity_kind: Literal["player", "team"]
    season_year: int

    week_number: int | None = None
    """Week within the season. None = season-level query."""

    card_type: str
    """Card template that drives table routing. e.g., 'flashpoint' | 'player_arc'."""

    query_text: str | None = None
    """Natural-language query for dense semantic search (P1)."""

    k: int = 20
    """How many evidence rows to return."""

    mode: Literal["fact", "color", "all"] = "fact"
    """Trust-filter mode. 'fact' = high-trust only; 'color'/'all' = include low-trust."""


# ---------------------------------------------------------------------------
# Card-type → table routing
# ---------------------------------------------------------------------------

# Each entry lists the SQLite tables that are relevant for a given card_type.
# The retriever queries ALL listed tables and merges results before ranking.
# Add new card types by extending this dict — the query functions below handle
# each table generically.
CARD_TYPE_TO_TABLES: dict[str, list[str]] = {
    "flashpoint": [
        "player_signature_plays",
        "player_advanced_metrics",
        "player_achievements",
        "chronicle_moments_pending",
        "editorial_citations",
    ],
    "player_arc": [
        "player_season_summary",
        "player_achievements",
        "player_honors",
        "player_advanced_metrics",
        "editorial_citations",
    ],
    "standing": [
        "player_honors",
        "player_achievements",
        "player_season_summary",
    ],
    "mirror": [
        "player_mirror_matches",
        "player_advanced_metrics",
        "player_season_summary",
    ],
    "pulse": [
        "conversation_documents",
        "source_observations",
        "editorial_citations",
    ],
    "market": [
        "source_observations",
    ],
    "biography": [
        "player_season_summary",
        "player_achievements",
        "editorial_citations",
    ],
    # Catch-all: query everything for unknown card types
    "_default": [
        "player_signature_plays",
        "player_advanced_metrics",
        "player_achievements",
        "player_honors",
        "player_season_summary",
        "chronicle_moments_pending",
        "editorial_citations",
        "conversation_documents",
        "source_observations",
    ],
}

# Maps table names to the trust tier of evidence drawn from that table.
_TABLE_TRUST: dict[str, Literal["high", "low", "blocked"]] = {
    "player_signature_plays": "high",
    "player_advanced_metrics": "high",
    "player_achievements": "high",
    "player_honors": "high",
    "player_season_summary": "high",
    "player_mirror_matches": "high",
    "chronicle_moments_pending": "high",
    "editorial_citations": "high",
    "conversation_documents": "low",
    "source_observations": "low",
}

# Maps table names to the evidence kind label.
_TABLE_KIND: dict[str, str] = {
    "player_signature_plays": "moment",
    "player_advanced_metrics": "stat",
    "player_achievements": "moment",
    "player_honors": "honor",
    "player_season_summary": "stat",
    "player_mirror_matches": "biography",
    "chronicle_moments_pending": "moment",
    "editorial_citations": "quote",
    "conversation_documents": "quote",
    "source_observations": "market",
}


# ---------------------------------------------------------------------------
# Abstract encoder / reranker interfaces
# ---------------------------------------------------------------------------


class DenseEncoder(abc.ABC):
    """Abstract dense encoder.

    Concrete implementations wrap sentence-transformers models (e.g., BGE-M3).
    Import of torch / sentence_transformers MUST be deferred inside __init__
    or encode() — never at class definition time.
    """

    @abc.abstractmethod
    def encode(self, texts: list[str]) -> np.ndarray:
        """Return a (len(texts), dim) float32 array of L2-normalised vectors."""

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Row-wise cosine similarity between (1, dim) query and (N, dim) corpus."""
        # Both should already be L2-normalised; dot product == cosine similarity.
        return (a @ b.T).flatten()


class CrossEncoder(abc.ABC):
    """Abstract cross-encoder reranker.

    Concrete implementations wrap a cross-encoder model that scores
    (query, candidate) pairs. Import of torch / sentence_transformers MUST be
    deferred inside __init__ or rerank() — never at class definition time.
    """

    @abc.abstractmethod
    def rerank(
        self,
        query: str,
        candidates: list[str],
    ) -> list[tuple[int, float]]:
        """Return [(original_index, score), ...] sorted descending by score."""


class NullDenseEncoder(DenseEncoder):
    """Zero-vector stub. P1 will replace with a real BGE-M3 encoder."""

    def encode(self, texts: list[str]) -> np.ndarray:
        # Returns zeros — dense ranking will contribute 0 score in RRF fusion.
        return np.zeros((len(texts), 1), dtype=np.float32)


class NullCrossEncoder(CrossEncoder):
    """Pass-through stub. P1 will replace with a real cross-encoder."""

    def rerank(
        self,
        query: str,
        candidates: list[str],
    ) -> list[tuple[int, float]]:
        # Identity rerank: preserve original order with uniform score 0.0
        return [(i, 0.0) for i in range(len(candidates))]


# Module-level singleton stubs. Replace via dependency injection in P1.
_DEFAULT_DENSE_ENCODER: DenseEncoder = NullDenseEncoder()
_DEFAULT_CROSS_ENCODER: CrossEncoder = NullCrossEncoder()


# ---------------------------------------------------------------------------
# RRF fusion
# ---------------------------------------------------------------------------

_RRF_K = 60  # standard constant from the original RRF paper (Cormack 2009)


def _rrf_score(rank: int, k: int = _RRF_K) -> float:
    """Single-list RRF contribution: 1 / (k + rank).

    Rank is 1-based (rank=1 is the top result).
    """
    return 1.0 / (k + rank)


def _fuse_rrf(
    lexical_ranked: list[str],
    dense_ranked: list[str],
    all_ids: list[str],
) -> dict[str, float]:
    """Fuse two ranked lists into a combined RRF score per evidence ID.

    Args:
        lexical_ranked: Evidence IDs in lexical (BM25/SQL) rank order.
        dense_ranked:   Evidence IDs in dense-similarity rank order.
        all_ids:        All candidate IDs (superset of both lists).

    Returns:
        Dict mapping evidence_id -> fused RRF score.
    """
    scores: dict[str, float] = {eid: 0.0 for eid in all_ids}

    for rank_1based, eid in enumerate(lexical_ranked, start=1):
        if eid in scores:
            scores[eid] += _rrf_score(rank_1based)

    for rank_1based, eid in enumerate(dense_ranked, start=1):
        if eid in scores:
            scores[eid] += _rrf_score(rank_1based)

    return scores


# ---------------------------------------------------------------------------
# FTS5 detection + SQL helpers
# ---------------------------------------------------------------------------


def _has_fts5_table(db: Any, table_name: str) -> bool:
    """Return True if an FTS5 virtual table named *table_name* exists."""
    try:
        rows = db.query_all(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (f"{table_name}_fts",),
        )
        return len(rows) > 0
    except Exception:
        return False


def _slug_to_player_id(db: Any, entity_slug: str) -> int | None:
    """Resolve a player slug to an integer player_id."""
    row = db.query_one(
        "SELECT id FROM players WHERE slug = ?",
        (entity_slug,),
    )
    return row["id"] if row else None


def _slug_to_team_id(db: Any, entity_slug: str) -> int | None:
    """Resolve a team slug to an integer team_id."""
    row = db.query_one(
        "SELECT id FROM teams WHERE slug = ?",
        (entity_slug,),
    )
    return row["id"] if row else None


# ---------------------------------------------------------------------------
# Per-table SQL query builders
# ---------------------------------------------------------------------------

# Each builder returns a list of raw dicts drawn from its table.
# Builders are responsible only for fetching; trust tagging happens in the
# caller (_fetch_sql_evidence).


def _query_player_signature_plays(
    db: Any,
    player_id: int,
    season_year: int,
    week_number: int | None,
) -> list[dict[str, Any]]:
    sql = """
        SELECT
            id,
            player_id,
            season_year,
            week,
            play_description,
            game_id,
            created_at
        FROM player_signature_plays
        WHERE player_id = ?
          AND season_year = ?
    """
    params: list[Any] = [player_id, season_year]
    if week_number is not None:
        sql += " AND week = ?"
        params.append(week_number)
    sql += " ORDER BY week DESC LIMIT 20"
    try:
        return db.query_all(sql, tuple(params))
    except Exception as exc:
        log.warning("player_signature_plays query failed: %s", exc)
        return []


def _query_player_advanced_metrics(
    db: Any,
    player_id: int,
    season_year: int,
) -> list[dict[str, Any]]:
    sql = """
        SELECT *
        FROM player_advanced_metrics
        WHERE player_id = ?
          AND season_year = ?
        LIMIT 10
    """
    try:
        return db.query_all(sql, (player_id, season_year))
    except Exception as exc:
        log.warning("player_advanced_metrics query failed: %s", exc)
        return []


def _query_player_achievements(
    db: Any,
    player_id: int,
    season_year: int,
) -> list[dict[str, Any]]:
    sql = """
        SELECT *
        FROM player_achievements
        WHERE player_id = ?
          AND season_year = ?
        ORDER BY week DESC
        LIMIT 20
    """
    try:
        return db.query_all(sql, (player_id, season_year))
    except Exception as exc:
        log.warning("player_achievements query failed: %s", exc)
        return []


def _query_player_honors(
    db: Any,
    player_id: int,
    season_year: int,
) -> list[dict[str, Any]]:
    sql = """
        SELECT *
        FROM player_honors
        WHERE player_id = ?
          AND season_year = ?
        LIMIT 20
    """
    try:
        return db.query_all(sql, (player_id, season_year))
    except Exception as exc:
        log.warning("player_honors query failed: %s", exc)
        return []


def _query_player_season_summary(
    db: Any,
    player_id: int,
    season_year: int,
) -> list[dict[str, Any]]:
    sql = """
        SELECT *
        FROM player_season_summary
        WHERE player_id = ?
          AND season_year = ?
        LIMIT 5
    """
    try:
        return db.query_all(sql, (player_id, season_year))
    except Exception as exc:
        log.warning("player_season_summary query failed: %s", exc)
        return []


def _query_player_mirror_matches(
    db: Any,
    player_id: int,
    season_year: int,
) -> list[dict[str, Any]]:
    sql = """
        SELECT *
        FROM player_mirror_matches
        WHERE player_id = ?
          AND season_year = ?
        LIMIT 10
    """
    try:
        return db.query_all(sql, (player_id, season_year))
    except Exception as exc:
        log.warning("player_mirror_matches query failed: %s", exc)
        return []


def _query_chronicle_moments_pending(
    db: Any,
    entity_slug: str,
    season_year: int,
) -> list[dict[str, Any]]:
    sql = """
        SELECT *
        FROM chronicle_moments_pending
        WHERE entity_slug = ?
          AND season_year = ?
        LIMIT 20
    """
    try:
        return db.query_all(sql, (entity_slug, season_year))
    except Exception as exc:
        log.warning("chronicle_moments_pending query failed: %s", exc)
        return []


def _query_editorial_citations(
    db: Any,
    entity_slug: str,
    season_year: int,
) -> list[dict[str, Any]]:
    # Try FTS5 first, fall back to LIKE
    fts_table = "editorial_citations_fts"
    sql_fts = f"""
        SELECT ec.*
        FROM editorial_citations ec
        JOIN {fts_table} fts ON fts.rowid = ec.rowid
        WHERE {fts_table} MATCH ?
        LIMIT 20
    """
    sql_like = """
        SELECT *
        FROM editorial_citations
        WHERE entity_slug = ?
          AND season_year = ?
        LIMIT 20
    """
    try:
        rows = db.query_all(sql_fts, (entity_slug,))
        if rows:
            return rows
    except Exception:
        log.debug("editorial_citations FTS5 unavailable — using LIKE fallback")

    try:
        return db.query_all(sql_like, (entity_slug, season_year))
    except Exception as exc:
        log.warning("editorial_citations query failed: %s", exc)
        return []


def _query_conversation_documents(
    db: Any,
    entity_slug: str,
    season_year: int,
) -> list[dict[str, Any]]:
    sql = """
        SELECT *
        FROM conversation_documents
        WHERE entity_slug = ?
          AND season_year = ?
        ORDER BY created_at DESC
        LIMIT 10
    """
    # Fallback: some schemas may not have entity_slug on this table
    try:
        return db.query_all(sql, (entity_slug, season_year))
    except Exception:
        # Try without entity_slug filter
        sql_fallback = """
            SELECT *
            FROM conversation_documents
            WHERE season_year = ?
            ORDER BY created_at DESC
            LIMIT 10
        """
        try:
            return db.query_all(sql_fallback, (season_year,))
        except Exception as exc:
            log.warning("conversation_documents query failed: %s", exc)
            return []


def _query_source_observations(
    db: Any,
    entity_slug: str,
    season_year: int,
) -> list[dict[str, Any]]:
    sql = """
        SELECT *
        FROM source_observations
        WHERE entity_slug = ?
          AND season_year = ?
        ORDER BY observed_at DESC
        LIMIT 20
    """
    try:
        return db.query_all(sql, (entity_slug, season_year))
    except Exception as exc:
        log.warning("source_observations query failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Row → EvidenceRow coercion
# ---------------------------------------------------------------------------


def _row_to_text(table: str, row: dict[str, Any]) -> str:
    """Build a canonical text string from a raw DB row for FTS / embedding."""
    # Strategy: prefer known text columns, fall back to JSON dump of whole row.
    text_columns: dict[str, list[str]] = {
        "player_signature_plays": ["play_description"],
        "player_advanced_metrics": ["metric_name", "metric_value"],
        "player_achievements": ["achievement_id", "description", "label"],
        "player_honors": ["honor_name", "honor_scope", "position"],
        "player_season_summary": ["summary_text", "position"],
        "player_mirror_matches": ["comparable_player_name", "similarity_notes"],
        "chronicle_moments_pending": ["moment_text", "headline", "body"],
        "editorial_citations": ["citation_text", "quote", "body"],
        "conversation_documents": ["body", "title", "text"],
        "source_observations": ["observation_text", "body", "text"],
    }
    preferred = text_columns.get(table, [])
    parts: list[str] = []
    for col in preferred:
        val = row.get(col)
        if val and isinstance(val, str) and val.strip():
            parts.append(val.strip())
    if parts:
        return " | ".join(parts)
    # Fallback: JSON of the row, excluding None values
    compact = {k: v for k, v in row.items() if v is not None}
    return json.dumps(compact, ensure_ascii=False, default=str)[:400]


def _row_to_source(table: str, row: dict[str, Any]) -> str:
    """Determine source label for a raw DB row."""
    explicit = row.get("source_name") or row.get("source") or ""
    if explicit:
        return str(explicit)
    table_source: dict[str, str] = {
        "player_signature_plays": "cfbi_db",
        "player_advanced_metrics": "cfbd",
        "player_achievements": "cfbi_db",
        "player_honors": "cfbi_db",
        "player_season_summary": "cfbd",
        "player_mirror_matches": "cfbi_db",
        "chronicle_moments_pending": "cfbi_db",
        "editorial_citations": "cfbi_db",
        "conversation_documents": "reddit",
        "source_observations": "polymarket",
    }
    return table_source.get(table, "cfbi_db")


def _coerce_to_evidence(
    table: str,
    row: dict[str, Any],
    entity_slug: str,
    season_year: int,
) -> EvidenceRow:
    """Convert a raw dict from any supported table into an EvidenceRow."""
    source = _row_to_source(table, row)
    trust_from_registry = SOURCE_TRUST.get(source, SOURCE_TRUST.get("_unknown", "low"))
    trust: Literal["high", "low", "blocked"] = _TABLE_TRUST.get(
        table,
        trust_from_registry,  # type: ignore[arg-type]
    )
    kind = _TABLE_KIND.get(table, "stat")
    text = _row_to_text(table, row)

    # Best-effort extraction of IDs / timestamps
    source_id: str | None = None
    for id_col in ("id", "play_id", "citation_id", "document_id", "observation_id"):
        val = row.get(id_col)
        if val is not None:
            source_id = str(val)
            break

    week_number: int | None = None
    for wk_col in ("week", "week_number"):
        val = row.get(wk_col)
        if val is not None:
            try:
                week_number = int(val)
            except (TypeError, ValueError):
                pass
            break

    row_season = row.get("season_year") or row.get("season")
    try:
        row_season_int: int | None = int(row_season) if row_season is not None else season_year
    except (TypeError, ValueError):
        row_season_int = season_year

    ts: str | None = None
    for ts_col in ("created_at", "observed_at", "timestamp_utc", "published_at"):
        val = row.get(ts_col)
        if val:
            ts = str(val)
            break

    return EvidenceRow(
        source=source,
        source_id=source_id,
        trust=trust,
        kind=kind,
        payload=dict(row),
        text=text,
        season_year=row_season_int,
        week_number=week_number,
        entity_slug=entity_slug,
        timestamp_utc=ts,
    )


# ---------------------------------------------------------------------------
# Core SQL fetch
# ---------------------------------------------------------------------------


def _fetch_sql_evidence(
    db: Any,
    query: RetrievalQuery,
) -> list[EvidenceRow]:
    """Fetch raw evidence from all tables relevant to query.card_type.

    Returns un-ranked EvidenceRow objects. Ranking happens after fusion.
    """
    tables = CARD_TYPE_TO_TABLES.get(query.card_type, CARD_TYPE_TO_TABLES["_default"])

    # Resolve entity IDs once
    player_id: int | None = None
    team_id: int | None = None
    if query.entity_kind == "player":
        player_id = _slug_to_player_id(db, query.entity_slug)
        if player_id is None:
            log.warning(
                "retrieve_evidence: no player found for slug %r — "
                "continuing with entity-slug fallback queries",
                query.entity_slug,
            )
    else:
        team_id = _slug_to_team_id(db, query.entity_slug)

    rows: list[EvidenceRow] = []
    seen_hashes: set[str] = set()

    for table in tables:
        raw_rows: list[dict[str, Any]] = []

        # Dispatch to per-table query function
        if table == "player_signature_plays" and player_id is not None:
            raw_rows = _query_player_signature_plays(
                db, player_id, query.season_year, query.week_number
            )
        elif table == "player_advanced_metrics" and player_id is not None:
            raw_rows = _query_player_advanced_metrics(db, player_id, query.season_year)
        elif table == "player_achievements" and player_id is not None:
            raw_rows = _query_player_achievements(db, player_id, query.season_year)
        elif table == "player_honors" and player_id is not None:
            raw_rows = _query_player_honors(db, player_id, query.season_year)
        elif table == "player_season_summary" and player_id is not None:
            raw_rows = _query_player_season_summary(db, player_id, query.season_year)
        elif table == "player_mirror_matches" and player_id is not None:
            raw_rows = _query_player_mirror_matches(db, player_id, query.season_year)
        elif table == "chronicle_moments_pending":
            raw_rows = _query_chronicle_moments_pending(
                db, query.entity_slug, query.season_year
            )
        elif table == "editorial_citations":
            raw_rows = _query_editorial_citations(db, query.entity_slug, query.season_year)
        elif table == "conversation_documents":
            raw_rows = _query_conversation_documents(
                db, query.entity_slug, query.season_year
            )
        elif table == "source_observations":
            raw_rows = _query_source_observations(
                db, query.entity_slug, query.season_year
            )

        for raw in raw_rows:
            ev = _coerce_to_evidence(table, raw, query.entity_slug, query.season_year)
            # Deduplicate by hash input to avoid the same row from FTS + LIKE
            h = ev.evidence_hash_input()
            if h not in seen_hashes:
                seen_hashes.add(h)
                rows.append(ev)

    return rows


# ---------------------------------------------------------------------------
# Dense retrieval (stub today)
# ---------------------------------------------------------------------------


def _dense_rank(
    query_text: str | None,
    candidates: list[EvidenceRow],
    encoder: DenseEncoder,
) -> list[str]:
    """Return candidate evidence IDs ranked by dense similarity.

    With ``NullDenseEncoder`` all vectors are zero, so cosine similarity is
    undefined. The stub returns the original order unchanged, contributing zero
    to RRF scores (since it is the same order as lexical, the RRF score is
    still non-zero from the lexical list — this is intentional for P0 parity).
    """
    if not candidates or not query_text:
        return [ev.evidence_hash_input() for ev in candidates]

    try:
        corpus_texts = [ev.text for ev in candidates]
        corpus_vecs = encoder.encode(corpus_texts)
        query_vec = encoder.encode([query_text])

        # If encoder is the null stub, all values are zero; skip similarity
        if np.all(corpus_vecs == 0):
            return [ev.evidence_hash_input() for ev in candidates]

        sims = DenseEncoder.cosine_similarity(query_vec, corpus_vecs)
        ranked_indices = np.argsort(-sims)
        return [candidates[i].evidence_hash_input() for i in ranked_indices]
    except Exception as exc:
        log.warning("Dense ranking failed (%s) — using identity order", exc)
        return [ev.evidence_hash_input() for ev in candidates]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def retrieve_evidence(
    db: Any,
    query: RetrievalQuery,
    *,
    dense_encoder: DenseEncoder | None = None,
    cross_encoder: CrossEncoder | None = None,
) -> list[EvidenceRow]:
    """Hybrid retrieve. Returns top-k evidence rows ranked by RRF-fused score.

    Args:
        db:             Database instance with a ``query_all(sql, params)`` method.
        query:          Describes what evidence to fetch.
        dense_encoder:  Override the default dense encoder (P1 hook).
        cross_encoder:  Override the default cross-encoder reranker (P1 hook).

    Returns:
        Up to ``query.k`` EvidenceRow objects sorted descending by
        ``relevance_score`` (RRF-fused). Empty list if no evidence found.

    Raises:
        EvidenceRetrievalError: On unrecoverable DB errors (not logged
            warnings from individual table queries, which are swallowed
            gracefully).
    """
    enc = dense_encoder or _DEFAULT_DENSE_ENCODER
    reranker = cross_encoder or _DEFAULT_CROSS_ENCODER

    # --- 1. SQL / lexical fetch ---
    try:
        all_rows = _fetch_sql_evidence(db, query)
    except Exception as exc:
        raise EvidenceRetrievalError(
            f"SQL fetch failed for {query.entity_slug}/{query.card_type}: {exc}"
        ) from exc

    if not all_rows:
        return []

    # Lexical rank = insertion order from the SQL queries (most relevant tables
    # are listed first in CARD_TYPE_TO_TABLES, and each table returns rows
    # ordered by recency/relevance already).
    lexical_ranked = [ev.evidence_hash_input() for ev in all_rows]
    all_ids = list(lexical_ranked)  # same set for now; dense may add none

    # --- 2. Dense rank ---
    dense_ranked = _dense_rank(query.query_text, all_rows, enc)

    # --- 3. RRF fusion ---
    fused_scores = _fuse_rrf(lexical_ranked, dense_ranked, all_ids)

    # Attach fused scores to rows
    id_to_row: dict[str, EvidenceRow] = {
        ev.evidence_hash_input(): ev for ev in all_rows
    }
    for ev_id, score in fused_scores.items():
        if ev_id in id_to_row:
            id_to_row[ev_id] = id_to_row[ev_id].model_copy(
                update={"relevance_score": score}
            )

    ranked_rows = sorted(
        id_to_row.values(),
        key=lambda r: r.relevance_score,
        reverse=True,
    )

    # --- 4. Cross-encoder rerank (stub pass-through today) ---
    if query.query_text and len(ranked_rows) > 1:
        try:
            candidate_texts = [r.text for r in ranked_rows]
            rerank_result = reranker.rerank(query.query_text, candidate_texts)
            # rerank_result is [(original_index, score), ...] sorted desc by score
            ranked_rows = [ranked_rows[idx] for idx, _ in rerank_result]
        except Exception as exc:
            log.warning("Cross-encoder rerank failed (%s) — skipping", exc)

    # --- 5. Trust filtering ---
    ranked_rows = filter_evidence(ranked_rows, mode=query.mode)

    # --- 6. Top-k ---
    return ranked_rows[: query.k]


def compute_evidence_hash(rows: list[EvidenceRow]) -> str:
    """SHA-256 hex (32-char truncated) of the sorted evidence set.

    Used as a cache key component. Order-independent: the canonical set is
    sorted before hashing, so two calls with the same rows in different order
    produce the same hash.

    Args:
        rows: Evidence rows (may be unsorted).

    Returns:
        32-character lowercase hex string.
    """
    canonical = sorted(r.evidence_hash_input() for r in rows)
    return hashlib.sha256("\n".join(canonical).encode("utf-8")).hexdigest()[:32]
