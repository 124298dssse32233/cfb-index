"""Discourse rivalry mirror engine — Language Layer Wave 2 (A3).

For each rivalry pair (T, R) from ``rivalry_pairs`` (or an explicit ``pairs``
override), this ports the validated ``rival_windows`` approach from
``scripts/discourse_keyness_prototype.py``: take team T's fan-voice docs that
mention rival R (alias hits = R's structural terms + R's school/slug words),
collect +/-12-token windows around each rival mention, strip every school-name
word (built from the teams table — the "Texas, Oklahoma, Michigan..." list-post
guard), both teams' structural terms, stopwords/junk, and the generic seed.
Then contrast side T-about-R against side R-about-T with the Wave-1 weighted
log-odds (informative Dirichlet prior over the COMBINED windows, min_count 5,
z >= 1.96, top 15 per side) and write ``team_discourse_mirror`` rows.

Per-1k normalization is inherent to the log-odds; ``side_token_count`` and
``rival_mention_doc_count`` are stored anyway so the team-page Mirror band can
disclose volume ("N fan posts mention them / M mention us") without recompute.

Idempotent per (pair, season): both directions are DELETEd before INSERT —
including sides that no longer produce surviving terms (the Wave-1 stale-row
contract). ``commit=False`` is a dry run.

Single streaming pass over the fan-voice corpus (same source filter +
city-sub exclusion as keyness, via ``_common.fan_voice_filter_sql``); season
bucketing via ``resolve_week(day).season_year`` (A5).

PYTHONUTF8 note: like keyness.py, this module never prints raw post text —
progress lines carry counts and bare [a-z'] terms only.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from cfb_rankings.common.week import resolve_week
from cfb_rankings.ingest.relevance import score_text

from ._common import fan_voice_filter_sql, load_generic_terms
from .keyness import (
    ALPHA0,
    STOPWORDS,
    Z_FLOOR,
    _WORD_RE,
    _WS_RE,
    _clean,
    _load_banlist,
    _load_structural_seed,
    _row_get,
    _structural_terms_for,
    _term_blocked,
)

MODEL_VERSION = "discourse-mirror-v1"

# +/- token window around each rival mention (prototype-validated).
_WINDOW = 12
# Per-term floor inside the windows (windows are sparse vs whole docs).
_MIN_COUNT = 5
# Distinctive terms kept per side.
_TOP_N = 15
# Receipt-quote pool cap per side (shortest low-toxicity docs win).
_QUOTE_CAP = 512


def _alias_words(team_row: Any, structural_seed: dict[str, set[str]]) -> set[str]:
    """Token-level rival-mention alias words for one team.

    R's structural terms (programmatic teams-row words + curated nicknames,
    via the Wave-1 builder) split into single words >= 3 chars. A token hit on
    any of these counts as "talking about R".
    """
    words: set[str] = set()
    for term in _structural_terms_for(team_row, structural_seed):
        for w in _WORD_RE.findall(str(term).lower()):
            if len(w) >= 3:
                words.add(w)
    return words


def compute_discourse_mirror(
    db: Any,
    *,
    seasons: list[int],
    pairs: list[tuple[str, str]] | None = None,
    commit: bool = False,
) -> dict:
    """Compute + (optionally) store rivalry-mirror keyness for each pair.

    ``pairs`` is an optional list of (slugA, slugB) tuples that overrides the
    ``rivalry_pairs`` table read. ``commit=False`` is a dry run: computes,
    prints term lists, writes nothing. Returns ``{"pairs", "sides_written",
    "terms_written", "docs_scanned", "docs_gated", "seasons"}``.
    """
    season_list = sorted({int(s) for s in seasons})
    season_set = set(season_list)
    if not season_set:
        raise ValueError("compute_discourse_mirror: at least one season required")

    # -- teams table: slug resolution + name/structural word sets ------------
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

    # -- resolve the pair list ------------------------------------------------
    pair_ids: list[tuple[int, int]] = []
    if pairs:
        for slug_a, slug_b in pairs:
            row_a = by_slug.get(str(slug_a))
            row_b = by_slug.get(str(slug_b))
            if row_a is None or row_b is None:
                print(
                    f"compute_discourse_mirror: unknown pair slug "
                    f"{slug_a!r}:{slug_b!r} — skipped",
                    flush=True,
                )
                continue
            pair_ids.append(
                (int(_row_get(row_a, "team_id")), int(_row_get(row_b, "team_id")))
            )
    else:
        try:
            rows = db.query_all(
                "SELECT team_a_id, team_b_id FROM rivalry_pairs "
                "WHERE COALESCE(is_active, 1) = 1"
            )
        except Exception:
            rows = []
        for row in rows:
            a = _row_get(row, "team_a_id")
            b = _row_get(row, "team_b_id")
            if a is not None and b is not None:
                pair_ids.append((int(a), int(b)))
    pair_ids = [
        (a, b)
        for a, b in dict.fromkeys(pair_ids)
        if a != b and a in by_id and b in by_id
    ]
    if not pair_ids:
        print("compute_discourse_mirror: no resolvable pairs — nothing to do",
              flush=True)
        return {
            "pairs": 0,
            "sides_written": 0,
            "terms_written": 0,
            "docs_scanned": 0,
            "docs_gated": 0,
            "seasons": season_list,
        }

    structural_seed = _load_structural_seed()
    banlist = _load_banlist(db)
    generic_terms = load_generic_terms()

    # ALL school-name words (school_name + slug words, per the prototype):
    # windows around rival mentions pick up list-posts ("Texas, Oklahoma,
    # Michigan...") — strip every school name so what survives is the actual
    # language about the rival, not co-mentioned teams.
    school_words: set[str] = set()
    for row in team_rows:
        for w in _WORD_RE.findall(str(_row_get(row, "school_name") or "").lower()):
            if len(w) >= 3:
                school_words.add(w)
        for w in str(_row_get(row, "slug") or "").lower().split("-"):
            if len(w) >= 3:
                school_words.add(w)

    # Per-side config: team T -> [(rival R, alias words, exclusion set)].
    # A team can sit in several pairs (e.g. michigan: ohio-state + msu).
    sides_by_team: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for a, b in pair_ids:
        for t, r in ((a, b), (b, a)):
            aliases = _alias_words(by_id[r], structural_seed)
            exclude = (
                school_words
                | _structural_terms_for(by_id[t], structural_seed)
                | _structural_terms_for(by_id[r], structural_seed)
                | aliases
            )
            sides_by_team[t].append(
                {"rival_id": r, "aliases": aliases, "exclude": exclude}
            )

    # -- doc -> [(team_id, toxicity)] prefetch (pair teams only) -------------
    pair_team_ids = set(sides_by_team)
    doc_teams: dict[int, list[tuple[int, float]]] = defaultdict(list)
    with db.connection() as conn:
        cursor = conn.execute(
            "SELECT conversation_document_id, team_id, toxicity_score "
            "FROM conversation_document_targets "
            "WHERE target_type = 'team' AND team_id IS NOT NULL"
        )
        for target in cursor:
            tid = int(_row_get(target, "team_id") or 0)
            if tid in pair_team_ids:
                doc_id = int(_row_get(target, "conversation_document_id") or 0)
                tox = _row_get(target, "toxicity_score")
                doc_teams[doc_id].append(
                    (tid, float(tox) if tox is not None else 1.0)
                )

    # -- single streaming pass over the fan-voice corpus ---------------------
    where, city_params = fan_voice_filter_sql("d")
    doc_sql = (
        "SELECT d.conversation_document_id AS doc_id, "
        "COALESCE(d.title_text,'') || ' ' || COALESCE(d.body_text,'') AS text, "
        "SUBSTR(COALESCE(d.external_created_at_utc,''),1,10) AS day, "
        "COALESCE(d.source_name,'') AS source_name, "
        "COALESCE(d.source_subchannel,'') AS source_subchannel "
        "FROM conversation_documents d "
        f"WHERE {where}"
    )

    # Accumulators keyed (team_id, rival_id, season).
    win_counts: dict[tuple[int, int, int], Counter] = defaultdict(Counter)
    win_tokens: dict[tuple[int, int, int], int] = defaultdict(int)
    doc_counts: dict[tuple[int, int, int], int] = defaultdict(int)
    # (toxicity_bad, length, display_text, source)
    quote_pool: dict[tuple[int, int, int], list[tuple[int, int, str, str]]] = (
        defaultdict(list)
    )

    docs_scanned = 0
    docs_gated = 0
    with db.connection() as conn:
        cursor = conn.execute(doc_sql, city_params)
        for doc in cursor:
            doc_id = int(_row_get(doc, "doc_id") or 0)
            tagged = doc_teams.get(doc_id)
            if not tagged:
                continue
            day = _row_get(doc, "day") or ""
            if len(day) != 10:
                continue
            try:
                season = resolve_week(day).season_year
            except (ValueError, TypeError):
                continue
            if season not in season_set:
                continue
            text = _clean(_row_get(doc, "text") or "")
            raw = _WORD_RE.findall(text.lower())
            if not raw:
                continue
            raw_set = set(raw)
            gate_checked = False
            is_football = False
            display: str | None = None
            for tid, toxicity in tagged:
                for side in sides_by_team.get(tid, ()):
                    aliases = side["aliases"]
                    if not (raw_set & aliases):
                        continue
                    if not gate_checked:
                        gate_checked = True
                        docs_scanned += 1
                        if docs_scanned % 40000 == 0:
                            print(
                                f"  ...{docs_scanned} rival-mention docs scanned "
                                f"({docs_gated} gated)",
                                flush=True,
                            )
                        is_football = score_text(text).is_football
                        if not is_football:
                            docs_gated += 1
                    if not is_football:
                        continue
                    key = (tid, side["rival_id"], season)
                    exclude = side["exclude"]
                    counts = win_counts[key]
                    added = 0
                    seen: set[int] = set()
                    for j, tok in enumerate(raw):
                        if tok not in aliases:
                            continue
                        for k in range(max(0, j - _WINDOW),
                                       min(len(raw), j + _WINDOW + 1)):
                            if k in seen:
                                continue
                            seen.add(k)
                            w = raw[k]
                            if (
                                w in STOPWORDS
                                or len(w) < 3
                                or w.startswith("'")
                                or w in exclude
                            ):
                                continue
                            counts[w] += 1
                            added += 1
                    win_tokens[key] += added
                    doc_counts[key] += 1
                    if display is None:
                        display = _WS_RE.sub(" ", text).strip()
                    if 40 <= len(display) <= 220:
                        source = "{}/{}".format(
                            _row_get(doc, "source_name") or "",
                            _row_get(doc, "source_subchannel") or "",
                        ).rstrip("/")
                        pool = quote_pool[key]
                        pool.append(
                            (int(toxicity >= 0.3), len(display), display, source)
                        )
                        if len(pool) > _QUOTE_CAP:
                            pool.sort(key=lambda c: (c[0], c[1]))
                            del pool[_QUOTE_CAP // 2:]
    print(
        f"compute_discourse_mirror: pass done — {docs_scanned} rival-mention "
        f"docs scanned, {docs_gated} relevance-gated, {len(pair_ids)} pairs, "
        f"seasons={season_list}",
        flush=True,
    )

    # -- per (pair, season): contrast side T-about-R vs side R-about-T -------
    computed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
    for a, b in pair_ids:
        for season in season_list:
            key_a = (a, b, season)
            key_b = (b, a, season)
            counts_a = win_counts.get(key_a, Counter())
            counts_b = win_counts.get(key_b, Counter())
            n_a = win_tokens.get(key_a, 0)
            n_b = win_tokens.get(key_b, 0)
            if n_a + n_b == 0:
                continue
            # Informative prior over the COMBINED rival-mention windows of the
            # pair — the shared vocabulary of the rivalry conversation.
            prior = counts_a + counts_b
            n_prior = n_a + n_b
            for key, counts, n_side, other_counts, n_other in (
                (key_a, counts_a, n_a, counts_b, n_b),
                (key_b, counts_b, n_b, counts_a, n_a),
            ):
                candidates: list[dict[str, Any]] = []
                for term, ca in counts.items():
                    if ca < _MIN_COUNT:
                        continue
                    cb = other_counts.get(term, 0)
                    aw = ALPHA0 * prior.get(term, ca) / max(n_prior, 1)
                    if aw <= 0:
                        aw = 0.01
                    denom_a = n_side + ALPHA0 - ca - aw
                    denom_b = n_other + ALPHA0 - cb - aw
                    if denom_a <= 0 or denom_b <= 0:
                        continue
                    delta = (
                        math.log((ca + aw) / denom_a)
                        - math.log((cb + aw) / denom_b)
                    )
                    variance = 1.0 / (ca + aw) + 1.0 / (cb + aw)
                    z = delta / math.sqrt(variance)
                    if z < Z_FLOOR:
                        continue
                    if (
                        _term_blocked(term, banlist)
                        or _term_blocked(term, generic_terms)
                    ):
                        continue
                    candidates.append(
                        {"term": term, "window_count": ca, "z_score": round(z, 4)}
                    )
                if not candidates:
                    continue
                candidates.sort(
                    key=lambda c: (-c["z_score"], -c["window_count"], c["term"])
                )
                candidates = candidates[:_TOP_N]

                # Toxicity-gated receipt: the shortest 40-220 char low-toxicity
                # doc among this side's windowed docs, stamped on rank 1 only.
                quote = None
                quote_source = None
                pool = sorted(quote_pool.get(key, []), key=lambda c: (c[0], c[1]))
                if pool and pool[0][0] == 0:
                    quote = pool[0][2]
                    quote_source = pool[0][3] or None

                side_tokens = n_side
                side_docs = doc_counts.get(key, 0)
                rows = [
                    {
                        "team_id": key[0],
                        "rival_team_id": key[1],
                        "season_year": season,
                        "term": cand["term"],
                        "term_rank": rank,
                        "window_count": cand["window_count"],
                        "z_score": cand["z_score"],
                        "side_token_count": side_tokens,
                        "rival_mention_doc_count": side_docs,
                        "sample_quote": quote if rank == 1 else None,
                        "sample_quote_source": quote_source if rank == 1 else None,
                        "model_version": MODEL_VERSION,
                        "computed_at_utc": computed_at,
                    }
                    for rank, cand in enumerate(candidates, start=1)
                ]
                results[key] = rows
                slug_t = _row_get(by_id.get(key[0], {}), "slug") or key[0]
                slug_r = _row_get(by_id.get(key[1], {}), "slug") or key[1]
                print(
                    f"  {slug_t} on {slug_r} {season}: {side_docs} docs, "
                    "top terms: " + ", ".join(r["term"] for r in rows[:8]),
                    flush=True,
                )

    # -- write (idempotent DELETE + INSERT, both directions per pair) --------
    # The DELETE covers every requested (pair, season) in BOTH directions,
    # including sides that no longer produce surviving terms — the Wave-1
    # stale-row contract ported to the mirror table.
    sides_written = 0
    terms_written = 0
    if commit:
        insert_sql = (
            "INSERT INTO team_discourse_mirror ("
            "team_id, rival_team_id, season_year, term, term_rank, "
            "window_count, z_score, side_token_count, rival_mention_doc_count, "
            "sample_quote, sample_quote_source, model_version, computed_at_utc"
            ") VALUES ("
            ":team_id, :rival_team_id, :season_year, :term, :term_rank, "
            ":window_count, :z_score, :side_token_count, :rival_mention_doc_count, "
            ":sample_quote, :sample_quote_source, :model_version, :computed_at_utc)"
        )
        with db.connection() as conn:
            for a, b in pair_ids:
                for season in season_list:
                    conn.execute(
                        "DELETE FROM team_discourse_mirror "
                        "WHERE season_year = :season AND ("
                        "(team_id = :a AND rival_team_id = :b) "
                        "OR (team_id = :b AND rival_team_id = :a))",
                        {"season": season, "a": a, "b": b},
                    )
            for _key, rows in sorted(results.items()):
                conn.executemany(insert_sql, rows)
                sides_written += 1
                terms_written += len(rows)
            conn.commit()
    else:
        print(
            "compute_discourse_mirror: dry run — "
            f"{sum(len(rows) for rows in results.values())} terms across "
            f"{len(results)} sides NOT written (use --commit)",
            flush=True,
        )

    return {
        "pairs": len(pair_ids),
        "sides_written": sides_written,
        "terms_written": terms_written,
        "docs_scanned": docs_scanned,
        "docs_gated": docs_gated,
        "seasons": season_list,
    }


__all__ = ["compute_discourse_mirror", "MODEL_VERSION"]
