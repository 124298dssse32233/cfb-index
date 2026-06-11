"""Discourse player descriptor engine — Language Layer Wave 3 (A7).

For each player tagged in conversation_document_targets (target_type='player'),
finds fan-voice docs containing that player and extracts ±8-token windows around
each occurrence of the player's last name. Contrasts per-player window token
frequencies against the GLOBAL window corpus (all player windows combined) via
weighted log-odds.

This surfaces how fans specifically describe each player: "mobile", "elite",
"precision", "clutch", "yards after contact", "burst", etc. — language the fan
corpus uses DISPROPORTIONATELY when talking about this specific player.

Same cleaning pipeline as keyness.py. ALPHA0=500, Z_FLOOR=1.96, MIN_COUNT=3.

Applies descriptor_blocklist.yaml as a hard block on appearance/identity terms.
The bias-audit script (scripts/audit_player_descriptors.py) must be run before
committing to production.

Idempotent: DELETE WHERE player_id=:pid AND season_year=:season BEFORE INSERT.
commit=False is a dry-run.

Public API:
    compute_player_descriptors(db, *, seasons, top_n=10, min_windows=30,
                                players=None, commit=False) -> dict
    Returns: {players_written, terms_written, windows_scanned, seasons}
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cfb_rankings.common.week import resolve_week
from cfb_rankings.ingest.relevance import score_text

from .keyness import (
    STOPWORDS,
    _URL_RE,
    _WS_RE,
    _WORD_RE,
    _clean,
    _grams,
    _load_banlist,
    _load_structural_seed,
    _magnitude_band,
    _row_get,
    _structural_terms_for,
    _term_blocked,
    _tokenize,
    load_city_subs,
    load_generic_terms,
)
from ._common import fan_voice_filter_sql

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_VERSION = "discourse-descriptors-v1"
ALPHA0 = 500.0
Z_FLOOR = 1.96
MIN_COUNT = 3
WINDOW_HALF = 8        # ±8 tokens around the name occurrence
_QUOTE_CAP = 512
_QUOTE_TRIM = 256

_ROOT = Path(__file__).resolve().parents[3]
_BLOCKLIST_SEED = _ROOT / "seeds" / "discourse_descriptor_blocklist.yaml"


# ---------------------------------------------------------------------------
# Descriptor blocklist
# ---------------------------------------------------------------------------


def _load_descriptor_blocklist() -> set[str]:
    """Load appearance/identity block terms from the yaml seed.

    Missing file or missing pyyaml degrades to empty set — never crashes.
    Returns a set of lowercase strings.
    """
    terms: set[str] = set()
    if not _BLOCKLIST_SEED.is_file():
        return terms
    try:
        import yaml
    except ImportError:
        return terms
    try:
        data = yaml.safe_load(_BLOCKLIST_SEED.read_text(encoding="utf-8"))
    except Exception:
        return terms
    if isinstance(data, dict):
        for value in data.get("descriptor_blocklist") or []:
            if value:
                terms.add(str(value).strip().lower())
    terms.discard("")
    return terms


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def compute_player_descriptors(
    db: Any,
    *,
    seasons: list[int],
    top_n: int = 10,
    min_windows: int = 30,
    players: list[int] | None = None,
    commit: bool = False,
) -> dict:
    """Compute + (optionally) store per-(player, season) distinctive descriptors.

    ``players`` is an optional list of integer player_ids. When given, only
    those players are computed regardless of the ``min_windows`` floor; when
    None, every player tagged in the corpus is a candidate and the floor gates
    which ones get written.

    ``commit=False`` is a dry run: computes, prints term lists, writes nothing.

    Idempotent per (player_id, season_year): DELETE then INSERT before writing.
    Returns ``{"players_written", "terms_written", "windows_scanned", "seasons"}``.
    """
    season_list = sorted({int(s) for s in seasons})
    season_set = set(season_list)
    if not season_set:
        raise ValueError("compute_player_descriptors: at least one season required")

    # -- player table: id -> {last_name, first_name} --------------------------
    player_rows = db.query_all(
        "SELECT player_id, first_name, last_name FROM players "
        "WHERE last_name IS NOT NULL AND last_name != ''"
    )
    by_player_id: dict[int, dict[str, str]] = {}
    for row in player_rows:
        pid = _row_get(row, "player_id")
        if pid is None:
            continue
        pid = int(pid)
        ln = _row_get(row, "last_name") or ""
        fn = _row_get(row, "first_name") or ""
        if ln:
            by_player_id[pid] = {"last_name": ln, "first_name": fn}

    if players is not None:
        selected_ids: set[int] = set(players)
        explicit = True
    else:
        selected_ids = set(by_player_id)
        explicit = False

    # -- doc -> [player_id] prefetch (selected players only) ------------------
    player_doc_map: dict[int, list[int]] = defaultdict(list)
    with db.connection() as conn:
        cursor = conn.execute(
            "SELECT conversation_document_id, player_id "
            "FROM conversation_document_targets "
            "WHERE target_type = 'player' AND player_id IS NOT NULL"
        )
        for target in cursor:
            pid = _row_get(target, "player_id")
            if pid is None:
                continue
            pid = int(pid)
            if pid in selected_ids:
                doc_id = int(_row_get(target, "conversation_document_id") or 0)
                player_doc_map[doc_id].append(pid)

    # -- player -> first team (for structural-term exclusion) -----------------
    player_team_map: dict[int, int] = {}
    with db.connection() as conn:
        cursor = conn.execute(
            "SELECT DISTINCT player_id, team_id "
            "FROM conversation_document_targets "
            "WHERE target_type = 'player' AND player_id IS NOT NULL "
            "AND team_id IS NOT NULL"
        )
        for row in cursor:
            pid = _row_get(row, "player_id")
            tid = _row_get(row, "team_id")
            if pid is not None and tid is not None:
                pid = int(pid)
                if pid not in player_team_map:
                    player_team_map[pid] = int(tid)

    # -- seed data + shared blocklists ----------------------------------------
    structural_seed = _load_structural_seed()
    banlist = _load_banlist(db)
    generic_terms = load_generic_terms()
    descriptor_blocklist = _load_descriptor_blocklist()

    # team rows for structural-term lookups
    team_rows = db.query_all("SELECT * FROM teams")
    team_by_id: dict[int, Any] = {}
    for row in team_rows:
        tid = _row_get(row, "team_id")
        if tid is not None:
            team_by_id[int(tid)] = row

    # -- streaming accumulators -----------------------------------------------
    # player_window_grams[(pid, season)] -> Counter of window tokens
    player_window_grams: dict[tuple[int, int], Counter] = defaultdict(Counter)
    # player_window_total[(pid, season)] -> total token count in windows
    player_window_total: dict[tuple[int, int], int] = defaultdict(int)
    # player_window_docs[(pid, season)] -> doc count
    player_window_docs: dict[tuple[int, int], int] = defaultdict(int)
    # global reference corpus: all player window tokens combined
    global_grams: dict[int, Counter] = defaultdict(Counter)
    global_tokens: dict[int, int] = defaultdict(int)
    # quote pool: (pid, season) -> list of (tox_flag, length, lowered, display, source)
    quote_pool: dict[tuple[int, int], list[tuple[int, int, str, str, str]]] = (
        defaultdict(list)
    )

    where_frag, city_params = fan_voice_filter_sql("d")
    doc_sql = (
        "SELECT d.conversation_document_id AS doc_id, "
        "COALESCE(d.title_text,'') || ' ' || COALESCE(d.body_text,'') AS text, "
        "SUBSTR(COALESCE(d.external_created_at_utc,''),1,10) AS day, "
        "COALESCE(d.source_name,'') AS source_name, "
        "COALESCE(d.source_subchannel,'') AS source_subchannel "
        "FROM conversation_documents d "
        f"WHERE {where_frag}"
    )

    docs_scanned = 0
    docs_gated = 0
    windows_scanned = 0

    with db.connection() as conn:
        cursor = conn.execute(doc_sql, city_params)
        for doc in cursor:
            day = _row_get(doc, "day") or ""
            if len(day) != 10:
                continue
            try:
                wk = resolve_week(day)
                season = wk.season_year
            except (ValueError, TypeError):
                continue
            if season not in season_set:
                continue
            doc_id = int(_row_get(doc, "doc_id") or 0)
            tagged_pids = player_doc_map.get(doc_id)
            if not tagged_pids:
                continue

            docs_scanned += 1
            if docs_scanned % 20000 == 0:
                print(
                    f"  ...{docs_scanned} docs scanned ({docs_gated} gated, "
                    f"{windows_scanned} windows)",
                    flush=True,
                )

            text = _clean(_row_get(doc, "text") or "")
            if not score_text(text).is_football:
                docs_gated += 1
                continue

            tokens = _tokenize(text)
            if not tokens:
                continue

            source = "{}/{}".format(
                _row_get(doc, "source_name") or "",
                _row_get(doc, "source_subchannel") or "",
            ).rstrip("/")
            display = _WS_RE.sub(" ", text).strip()

            for pid in tagged_pids:
                info = by_player_id.get(pid)
                if info is None:
                    continue
                last_lower = info["last_name"].lower()
                # Find all token positions matching the last name
                occurrences = [i for i, tok in enumerate(tokens) if tok == last_lower]
                if not occurrences:
                    continue

                for idx in occurrences:
                    start = max(0, idx - WINDOW_HALF)
                    end = idx + WINDOW_HALF + 1
                    # Exclude the name token itself from the window
                    window = tokens[start:idx] + tokens[idx + 1:end]
                    if not window:
                        continue
                    key = (pid, season)
                    player_window_grams[key].update(window)
                    player_window_total[key] += len(window)
                    global_grams[season].update(window)
                    global_tokens[season] += len(window)
                    windows_scanned += len(window)

                player_window_docs[(pid, season)] += 1

                # Quote candidacy: 40-220 chars, last name appears in display
                if 40 <= len(display) <= 220 and last_lower in display.lower():
                    key = (pid, season)
                    pool = quote_pool[key]
                    pool.append(
                        (0, len(display), display.lower(), display, source)
                    )
                    if len(pool) > _QUOTE_CAP:
                        pool.sort(key=lambda c: (c[0], c[1]))
                        del pool[_QUOTE_TRIM:]

    print(
        f"compute_player_descriptors: pass done — {docs_scanned} docs scanned, "
        f"{docs_gated} relevance-gated, {windows_scanned} window-tokens, "
        f"seasons={season_list}",
        flush=True,
    )

    # -- per-(player, season) weighted log-odds vs global window corpus --------
    computed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    to_write: dict[tuple[int, int], list[dict[str, Any]]] = {}

    for (pid, season), counts in sorted(player_window_grams.items()):
        total_windows = player_window_total[(pid, season)]
        if not explicit and total_windows < min_windows:
            continue

        n_global = global_tokens[season]
        n_rest = max(n_global - total_windows, 1)
        global_counts = global_grams[season]

        # Build blocked set for this player's team
        team_id = player_team_map.get(pid)
        team_row = team_by_id.get(team_id) if team_id is not None else {}
        structural = _structural_terms_for(team_row or {}, structural_seed)
        blocked = structural | banlist | generic_terms | descriptor_blocklist

        candidates: list[dict[str, Any]] = []
        # When rest corpus is too small for meaningful contrast (single-player
        # corpus or very thin global pool), fall back to a frequency floor:
        # any term with raw rate >= 5% and ca >= MIN_COUNT is kept as a descriptor.
        _sparse_rest = n_rest < 50
        _MIN_SPARSE_RATE = 0.05
        for term, ca in counts.items():
            if ca < MIN_COUNT:
                continue
            cg = global_counts.get(term, ca)
            cb = max(cg - ca, 0)
            if _sparse_rest:
                rate_player = ca / max(total_windows, 1)
                if rate_player < _MIN_SPARSE_RATE:
                    continue
                # Synthetic z and ratio for ranking purposes
                z = rate_player * math.sqrt(max(ca, 1))
                ratio = rate_player / _MIN_SPARSE_RATE
            else:
                aw = ALPHA0 * cg / max(n_global, 1)
                if aw <= 0:
                    aw = 0.01
                denom_a = total_windows + ALPHA0 - ca - aw
                denom_b = n_rest + ALPHA0 - cb - aw
                if denom_a <= 0 or denom_b <= 0:
                    continue
                delta = math.log((ca + aw) / denom_a) - math.log((cb + aw) / denom_b)
                variance = 1.0 / (ca + aw) + 1.0 / (cb + aw)
                z = delta / math.sqrt(variance)
                rate_player = ca / max(total_windows, 1)
                rate_rest = max(cb, 0.5) / n_rest
                ratio = rate_player / rate_rest
                if z < Z_FLOOR:
                    continue
            if _term_blocked(term, blocked):
                continue
            candidates.append(
                {
                    "term": term,
                    "window_count": ca,
                    "global_count": cb,
                    "z_score": round(z, 4),
                    "rate_ratio": round(ratio, 2),
                    "log2_ratio": round(math.log2(max(ratio, 1e-9)), 4),
                }
            )

        if not candidates:
            continue
        candidates.sort(key=lambda c: (-c["z_score"], -c["window_count"], c["term"]))
        candidates = candidates[:top_n]

        # Receipt quotes: shortest entry that contains the term
        pool = sorted(quote_pool.get((pid, season), []), key=lambda c: (c[0], c[1]))
        rows: list[dict[str, Any]] = []
        doc_count = player_window_docs[(pid, season)]
        for rank, cand in enumerate(candidates, start=1):
            quote = None
            quote_source = None
            for _tox, _length, lowered, disp, src in pool:
                if cand["term"] in lowered:
                    quote = disp
                    quote_source = src or None
                    break
            rows.append(
                {
                    "player_id": pid,
                    "season_year": season,
                    "term_rank": rank,
                    "total_windows": total_windows,
                    "sample_quote": quote,
                    "sample_quote_source": quote_source,
                    "model_version": MODEL_VERSION,
                    "computed_at_utc": computed_at,
                    **cand,
                }
            )
        to_write[(pid, season)] = rows
        info = by_player_id.get(pid, {})
        label = f"{info.get('first_name','')} {info.get('last_name', pid)}".strip()
        print(
            f"  {label} {season}: {doc_count} docs, top terms: "
            + ", ".join(r["term"] for r in rows[:8]),
            flush=True,
        )

    # -- write (idempotent DELETE + INSERT) ------------------------------------
    terms_written = 0
    players_written = 0
    if commit:
        insert_sql = (
            "INSERT INTO player_discourse_terms ("
            "player_id, season_year, term, term_rank, window_count, "
            "global_count, z_score, rate_ratio, log2_ratio, "
            "total_windows, sample_quote, "
            "sample_quote_source, model_version, computed_at_utc"
            ") VALUES ("
            ":player_id, :season_year, :term, :term_rank, :window_count, "
            ":global_count, :z_score, :rate_ratio, :log2_ratio, "
            ":total_windows, :sample_quote, "
            ":sample_quote_source, :model_version, :computed_at_utc)"
        )
        with db.connection() as conn:
            # DELETE scope: every selected (player, season) — including those that
            # no longer qualify so stale rows don't linger from prior runs.
            pids_to_clear = (
                set(players) if players is not None
                else {pid for pid, _s in to_write}
            )
            for pid in sorted(pids_to_clear):
                for season in season_list:
                    conn.execute(
                        "DELETE FROM player_discourse_terms "
                        "WHERE player_id = :pid AND season_year = :season",
                        {"pid": pid, "season": season},
                    )
            for (_pid, _season), rows in sorted(to_write.items()):
                conn.executemany(insert_sql, rows)
                terms_written += len(rows)
            conn.commit()
        players_written = len({pid for pid, _s in to_write})
    else:
        print(
            "compute_player_descriptors: dry run — "
            f"{sum(len(rows) for rows in to_write.values())} terms across "
            f"{len(to_write)} (player, season) cuts NOT written (use --commit)",
            flush=True,
        )

    return {
        "players_written": players_written,
        "terms_written": terms_written,
        "windows_scanned": windows_scanned,
        "seasons": season_list,
    }
