"""Discourse season eras engine — Language Layer Wave 3 (A6).

For each (team, season), computes weighted log-odds of that season's fan-voice
tokens vs the SAME TEAM's own tokens from OTHER requested seasons. This surfaces
what vocabulary was most distinctive to each era: Michigan 2023 = harbaugh/jim/rose/bama,
Michigan 2024 = orji/warren/mullings/portal. No LLM — pure corpus statistics.

Same cleaning pipeline as keyness.py (city-sub exclusion, relevance gate, structural +
generic + banlist filters). ALPHA0=200 (smaller per-team corpora than global field),
Z_FLOOR=1.96, MIN_COUNT=5.

Only teams with data in >= min_seasons distinct requested seasons receive era terms
(no meaningful within-team contrast without at least 2 seasons). Teams below
min_team_docs per season are silently skipped for that season.

Single streaming pass: accumulates per-(team, season) counters from fan-voice docs.
No second pass.

Idempotent: DELETE WHERE team_id=:tid AND season_year=:season BEFORE INSERT.
commit=False is a dry-run (compute + print, write nothing).

Public API:
    compute_team_eras(db, *, seasons, top_n=8, min_team_docs=150, min_seasons=2,
                      teams=None, commit=False) -> dict
    Returns: {teams_written, terms_written, docs_scanned, seasons}
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from cfb_rankings.ingest.relevance import score_text

from ._common import fan_voice_filter_sql
from .keyness import (
    STOPWORDS,
    _QUOTE_CAP,
    _QUOTE_TRIM,
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

MODEL_VERSION = "discourse-eras-v1"

# Weighted log-odds parameters — smaller per-team corpora than global field.
ALPHA0 = 200.0
Z_FLOOR = 1.96
MIN_COUNT = 5  # lower than keyness; per-season per-team corpus is smaller


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def compute_team_eras(
    db: Any,
    *,
    seasons: list[int],
    top_n: int = 8,
    min_team_docs: int = 50,
    min_seasons: int = 2,
    teams: list[str] | None = None,
    commit: bool = False,
) -> dict:
    """Compute + (optionally) store per-(team, season) era-distinctive terms.

    Within-team contrast: each season's fan-voice tokens are measured against
    the SAME TEAM's tokens from all other requested seasons (not vs the field).

    ``seasons`` must contain at least two values; teams with qualifying data in
    fewer than ``min_seasons`` distinct seasons are skipped entirely.

    ``teams`` is an optional list of slugs to restrict computation. When None,
    every team with data in the corpus is computed.

    ``commit=False`` is a dry run: computes and prints, writes nothing.

    Returns ``{"teams_written", "terms_written", "docs_scanned", "seasons"}``.
    """
    season_list = sorted({int(s) for s in seasons})
    season_set = set(season_list)
    if len(season_set) < 2:
        raise ValueError(
            "compute_team_eras: at least two distinct seasons required for"
            " within-team contrast"
        )

    # -- teams table: slug resolution + structural-term sets -----------------
    team_rows = db.query_all("SELECT * FROM teams")
    by_slug: dict[str, Any] = {}
    by_id: dict[int, Any] = {}
    for row in team_rows:
        team_id = _row_get(row, "team_id")
        if team_id is None:
            continue
        team_id = int(team_id)
        by_id[team_id] = row
        slug = _row_get(row, "slug")
        if slug:
            by_slug[str(slug)] = row

    if teams:
        selected_ids: set[int] = set()
        for slug in teams:
            row = by_slug.get(slug)
            if row is None:
                print(
                    f"compute_team_eras: unknown team slug {slug!r} — skipped",
                    flush=True,
                )
                continue
            selected_ids.add(int(_row_get(row, "team_id")))
    else:
        selected_ids = set(by_id)

    structural_seed = _load_structural_seed()
    banlist = _load_banlist(db)
    generic_terms = load_generic_terms()

    # -- doc -> [(team_id, toxicity)] prefetch (selected teams only) ---------
    doc_teams: dict[int, list[tuple[int, float]]] = defaultdict(list)
    with db.connection() as conn:
        cursor = conn.execute(
            "SELECT conversation_document_id, team_id, toxicity_score "
            "FROM conversation_document_targets "
            "WHERE target_type = 'team' AND team_id IS NOT NULL"
        )
        for target in cursor:
            tid = int(_row_get(target, "team_id") or 0)
            if tid in selected_ids:
                doc_id = int(_row_get(target, "conversation_document_id") or 0)
                tox = _row_get(target, "toxicity_score")
                doc_teams[doc_id].append(
                    (tid, float(tox) if tox is not None else 1.0)
                )

    # -- single streaming pass over the fan-voice corpus ---------------------
    where_fragment, city_params = fan_voice_filter_sql("d")
    doc_sql = (
        "SELECT d.conversation_document_id AS doc_id, "
        "COALESCE(d.title_text,'') || ' ' || COALESCE(d.body_text,'') AS text, "
        "SUBSTR(COALESCE(d.external_created_at_utc,''),1,10) AS day, "
        "COALESCE(d.source_name,'') AS source_name, "
        "COALESCE(d.source_subchannel,'') AS source_subchannel "
        "FROM conversation_documents d "
        f"WHERE {where_fragment}"
    )

    # Accumulators keyed by (team_id, season_year)
    team_season_grams: dict[tuple[int, int], Counter] = defaultdict(Counter)
    team_season_tokens: dict[tuple[int, int], int] = defaultdict(int)
    team_season_docs: dict[tuple[int, int], int] = defaultdict(int)
    # (toxicity_bad, length, lowered_text, display_text, source)
    quote_pool: dict[tuple[int, int], list[tuple[int, int, str, str, str]]] = (
        defaultdict(list)
    )

    docs_scanned = 0
    with db.connection() as conn:
        from cfb_rankings.common.week import resolve_week

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
            docs_scanned += 1
            if docs_scanned % 40000 == 0:
                print(
                    f"  ...{docs_scanned} docs scanned",
                    flush=True,
                )
            text = _clean(_row_get(doc, "text") or "")
            if not score_text(text).is_football:
                continue
            tokens = _tokenize(text)
            if not tokens:
                continue
            grams = _grams(tokens)
            doc_id = int(_row_get(doc, "doc_id") or 0)
            tagged = doc_teams.get(doc_id)
            if not tagged:
                continue
            display = _WS_RE.sub(" ", text).strip()
            quotable = 40 <= len(display) <= 220
            if quotable:
                source = "{}/{}".format(
                    _row_get(doc, "source_name") or "",
                    _row_get(doc, "source_subchannel") or "",
                ).rstrip("/")
                lowered = display.lower()
            for tid, toxicity in tagged:
                key = (tid, season)
                team_season_grams[key].update(grams)
                team_season_tokens[key] += len(grams)
                team_season_docs[key] += 1
                if quotable:
                    pool = quote_pool[key]
                    pool.append(
                        (int(toxicity >= 0.3), len(display), lowered, display, source)
                    )
                    if len(pool) > _QUOTE_CAP:
                        pool.sort(key=lambda c: (c[0], c[1]))
                        del pool[_QUOTE_TRIM:]

    print(
        f"compute_team_eras: pass done — {docs_scanned} docs scanned, "
        f"seasons={season_list}",
        flush=True,
    )

    # -- within-team era contrast --------------------------------------------
    # Group all (team_id, season) keys by team_id.
    from collections import defaultdict as _dd

    team_to_seasons: dict[int, set[int]] = _dd(set)
    for tid, season in team_season_grams:
        if team_season_docs[(tid, season)] >= min_team_docs:
            team_to_seasons[tid].add(season)

    computed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    to_write: dict[tuple[int, int], list[dict[str, Any]]] = {}

    for tid in sorted(team_to_seasons):
        qualifying_seasons = sorted(team_to_seasons[tid])
        if len(qualifying_seasons) < min_seasons:
            continue
        blocked = _structural_terms_for(by_id.get(tid, {}), structural_seed)

        for season in qualifying_seasons:
            n_team = team_season_tokens[(tid, season)]
            this_counts = team_season_grams[(tid, season)]

            # Combine rest-of-team seasons
            rest_counter: Counter = Counter()
            n_rest = 0
            for other_s in qualifying_seasons:
                if other_s == season:
                    continue
                rest_counter.update(team_season_grams[(tid, other_s)])
                n_rest += team_season_tokens[(tid, other_s)]
            n_rest = max(n_rest, 1)

            candidates: list[dict[str, Any]] = []
            for term, ca in this_counts.items():
                if ca < MIN_COUNT:
                    continue
                cb = rest_counter.get(term, 0)
                total = ca + cb
                aw = ALPHA0 * total / max(n_team + n_rest, 1)
                if aw <= 0:
                    aw = 0.01
                denom_a = n_team + ALPHA0 - ca - aw
                denom_b = n_rest + ALPHA0 - cb - aw
                if denom_a <= 0 or denom_b <= 0:
                    continue
                delta = math.log((ca + aw) / denom_a) - math.log((cb + aw) / denom_b)
                variance = 1.0 / (ca + aw) + 1.0 / (cb + aw)
                z = delta / math.sqrt(variance)
                if z < Z_FLOOR:
                    continue
                if (
                    _term_blocked(term, blocked)
                    or _term_blocked(term, banlist)
                    or _term_blocked(term, generic_terms)
                ):
                    continue
                rate_team = ca / max(n_team, 1)
                rate_rest = max(cb, 0.5) / n_rest
                ratio = rate_team / rate_rest
                candidates.append(
                    {
                        "term": term,
                        "mention_count": ca,
                        "rest_count": cb,
                        "z_score": round(z, 4),
                        "rate_ratio": round(ratio, 2),
                        "log2_ratio": round(math.log2(ratio), 4),
                        "magnitude_band": _magnitude_band(ratio),
                    }
                )
            if not candidates:
                continue
            candidates.sort(key=lambda c: (-c["z_score"], -c["mention_count"], c["term"]))
            candidates = candidates[:top_n]

            # receipt quotes
            pool = sorted(
                quote_pool.get((tid, season), []), key=lambda c: (c[0], c[1])
            )
            doc_n = team_season_docs[(tid, season)]
            rows: list[dict[str, Any]] = []
            for rank, cand in enumerate(candidates, start=1):
                quote = None
                quote_source = None
                for _tox, _length, lowered, display, source in pool:
                    if cand["term"] in lowered:
                        quote = display
                        quote_source = source or None
                        break
                rows.append(
                    {
                        "team_id": tid,
                        "season_year": season,
                        "term_rank": rank,
                        "team_season_doc_count": doc_n,
                        "team_season_token_count": n_team,
                        "sample_quote": quote,
                        "sample_quote_source": quote_source,
                        "model_version": MODEL_VERSION,
                        "computed_at_utc": computed_at,
                        **cand,
                    }
                )
            to_write[(tid, season)] = rows
            slug = _row_get(by_id.get(tid, {}), "slug") or tid
            print(
                f"  {slug} {season}: {doc_n} docs, top era terms: "
                + ", ".join(r["term"] for r in rows[:8]),
                flush=True,
            )

    # -- write (idempotent DELETE + INSERT) -----------------------------------
    terms_written = 0
    teams_written = 0
    if commit:
        insert_sql = (
            "INSERT INTO team_discourse_era_terms ("
            "team_id, season_year, term, term_rank, mention_count, rest_count, "
            "z_score, rate_ratio, log2_ratio, magnitude_band, "
            "team_season_doc_count, team_season_token_count, "
            "sample_quote, sample_quote_source, model_version, computed_at_utc"
            ") VALUES ("
            ":team_id, :season_year, :term, :term_rank, :mention_count, :rest_count, "
            ":z_score, :rate_ratio, :log2_ratio, :magnitude_band, "
            ":team_season_doc_count, :team_season_token_count, "
            ":sample_quote, :sample_quote_source, :model_version, :computed_at_utc)"
        )
        with db.connection() as conn:
            # Delete all (team, season) cuts in scope — including ones that no
            # longer qualify — so stale rows never linger between runs.
            for tid in sorted(selected_ids):
                for season in season_list:
                    conn.execute(
                        "DELETE FROM team_discourse_era_terms "
                        "WHERE team_id = :team_id AND season_year = :season_year",
                        {"team_id": tid, "season_year": season},
                    )
            for (_tid, _season), rows in sorted(to_write.items()):
                conn.executemany(insert_sql, rows)
                terms_written += len(rows)
            conn.commit()
        teams_written = len({tid for tid, _season in to_write})
    else:
        print(
            "compute_team_eras: dry run — "
            f"{sum(len(rows) for rows in to_write.values())} era terms across "
            f"{len(to_write)} (team, season) cuts NOT written (use --commit)",
            flush=True,
        )

    return {
        "teams_written": teams_written,
        "terms_written": terms_written,
        "docs_scanned": docs_scanned,
        "seasons": season_list,
    }
