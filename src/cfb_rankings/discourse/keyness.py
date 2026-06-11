"""Discourse keyness engine — Language Layer Wave 1.

Computes each (team, season) fan-voice corpus's most distinctive unigrams and
bigrams ("The Lexicon") via weighted log-odds with an informative Dirichlet
prior (Monroe et al.), measured against the same-season rest-of-corpus, and
writes them to ``team_discourse_terms`` (week=0 season cuts).

The cleaning rules are ported from ``scripts/discourse_keyness_prototype.py``
(validated against the real corpus on 2026-06-10):

* fan-voice sources only (reddit/bluesky/youtube/board) — kills podcast
  ad-reads and news bylines;
* city/residential subchannels excluded (``seeds/discourse_city_subs.yaml``) —
  r/Columbus is residents, not Buckeye fans;
* ``html.unescape`` + URL strip, then the prototype's STOPWORDS+JUNK lists;
* Stage-1 lexical relevance gate (``ingest.relevance.score_text`` —
  ``is_football`` required);
* per-team structural-term exclusion, built programmatically from the teams
  table row (name fields + slug words + city words + possessives) UNION the
  hand-curated nicknames in ``seeds/discourse_structural_terms.yaml``;
* banlist filter against active ``chronicle_banlist`` phrases.

Single streaming pass: one SELECT over ``conversation_documents`` feeds the
per-season global counts, every requested team's per-(team, season) counts,
AND the short-doc receipt-quote candidates — no per-team corpus re-reads.

PYTHONUTF8 note: this module never prints raw post text (encoding hazard on
this box) — progress lines carry counts and bare [a-z'] terms only.
"""
from __future__ import annotations

import html
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cfb_rankings.common.week import resolve_week
from cfb_rankings.ingest.relevance import score_text

MODEL_VERSION = "discourse-keyness-v1"

# Weighted log-odds parameters (validated in the prototype run).
ALPHA0 = 500.0
Z_FLOOR = 1.96
MIN_COUNT = 10

# Receipt-quote candidate retention per (team, season). Candidates are the
# team's short docs (40-220 chars); we keep the best (low-toxicity, shortest)
# so quote lookup after ranking is in-memory and the pass stays single.
_QUOTE_CAP = 2048
_QUOTE_TRIM = 1024

_ROOT = Path(__file__).resolve().parents[3]
_CITY_SUBS_SEED = _ROOT / "seeds" / "discourse_city_subs.yaml"
_STRUCTURAL_SEED = _ROOT / "seeds" / "discourse_structural_terms.yaml"
# Wave-2 editorial generic-term stoplist (thread boilerplate). Loaded here so the
# season AND weekly cuts both exclude it. SEPARATE from the structural seed.
_GENERIC_SEED = _ROOT / "seeds" / "discourse_generic_terms.yaml"

# Wave-2 weekly-cut floors (A2). A team-week needs >= this many docs to get a
# weekly cut; we keep the top _WEEKLY_TOP_N distinctive terms for it. The
# per-term count floor is lower than the season MIN_COUNT because a single
# week's corpus is ~1/15th of a season's.
_WEEKLY_MIN_DOCS = 30
_WEEKLY_TOP_N = 12
_WEEKLY_MIN_COUNT = 5

# Hard floor of city-sub exclusions; the seed yaml extends this list.
_BASE_CITY_SUBS = ("Columbus", "Eugene", "AnnArbor")

_WORD_RE = re.compile(r"[a-z][a-z']+")
_URL_RE = re.compile(r"http\S+|www\.\S+")
_WS_RE = re.compile(r"\s+")

JUNK = set(
    """
https http www com org reddit wiki comments thread threads poll view amp gt lt
nbsp x200b deleted removed url link sub subreddit post posts mod mods upvote
downvote edit tldr imo imho btw faq megathread crosspost discord
""".split()
)

STOPWORDS = set(
    """
a about above after again against all am an and any are aren't as at be because
been before being below between both but by can't cannot could couldn't did
didn't do does doesn't doing don't down during each few for from further had
hadn't has hasn't have haven't having he he'd he'll he's her here here's hers
herself him himself his how how's i i'd i'll i'm i've if in into is isn't it
it's its itself let's me more most mustn't my myself no nor not of off on once
only or other ought our ours ourselves out over own same shan't she she'd
she'll she's should shouldn't so some such than that that's the their theirs
them themselves then there there's these they they'd they'll they're they've
this those through to too under until up very was wasn't we we'd we'll we're
we've were weren't what what's when when's where where's which while who who's
whom why why's with won't would wouldn't you you'd you'll you're you've your
yours yourself yourselves will just also got get like one even still really
much can say said says know think going go gonna way make made want see right
yeah lol yes well thing things actually never always people year years guy
guys time game games team teams play played playing player players season
fans fan football week today day's
""".split()
) | JUNK


# ---------------------------------------------------------------------------
# Row access + seed loading helpers
# ---------------------------------------------------------------------------


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    """Read a column from a dict / sqlite3.Row defensively (missing -> default)."""
    try:
        value = row[key]
    except (KeyError, IndexError, TypeError):
        return default
    return value


def _load_yaml_seed(path: Path) -> Any:
    """Load a seed yaml; missing file / missing pyyaml degrade to None."""
    if not path.is_file():
        return None
    try:
        import yaml
    except ImportError:
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_city_subs() -> set[str]:
    """City/residential subchannels to exclude (base trio + seed yaml extras)."""
    subs = set(_BASE_CITY_SUBS)
    data = _load_yaml_seed(_CITY_SUBS_SEED)
    if isinstance(data, dict):
        for value in data.get("city_subs") or []:
            if value:
                subs.add(str(value))
    return subs


def _load_structural_seed() -> dict[str, set[str]]:
    """Hand-curated nickname exclusions keyed by team slug (seed yaml)."""
    data = _load_yaml_seed(_STRUCTURAL_SEED)
    out: dict[str, set[str]] = {}
    if isinstance(data, dict):
        for slug, terms in (data.get("structural_terms") or {}).items():
            out[str(slug)] = {str(t).lower() for t in (terms or []) if t}
    return out


def load_generic_terms() -> set[str]:
    """Editorial generic-term stoplist (``seeds/discourse_generic_terms.yaml``).

    Conversational / thread boilerplate that survived Wave-1 cleaning. Excluded
    from ALL outputs (season + weekly cuts here; mirror + voice via _common).
    Missing file / missing pyyaml -> empty set (never crashes).
    """
    terms: set[str] = set()
    data = _load_yaml_seed(_GENERIC_SEED)
    if isinstance(data, dict):
        for value in data.get("generic_terms") or []:
            if value:
                terms.add(str(value).strip().lower())
    terms.discard("")
    return terms


def _structural_terms_for(team_row: Any, seed: dict[str, set[str]]) -> set[str]:
    """Programmatic structural words for one team + curated nicknames.

    Words come from school_name / short_name / canonical_name / slug / city,
    each also with its "'s" possessive. Unknown slugs degrade gracefully to
    programmatic-only. Cultural terms ("blue", "autzen", "harbaugh") stay IN.
    """
    words: set[str] = set()
    for key in ("school_name", "short_name", "canonical_name", "city"):
        value = _row_get(team_row, key)
        if value:
            words.update(_WORD_RE.findall(str(value).lower()))
    slug = str(_row_get(team_row, "slug") or "")
    words.update(w for w in slug.lower().split("-") if len(w) >= 2)
    words |= seed.get(slug, set())
    return words | {f"{w}'s" for w in words}


def _load_banlist(db: Any) -> set[str]:
    """Active chronicle_banlist phrases, lowercased. Missing table -> empty."""
    try:
        rows = db.query_all(
            "SELECT phrase FROM chronicle_banlist WHERE is_active = 1"
        )
    except Exception:
        return set()
    phrases: set[str] = set()
    for row in rows:
        phrase = _row_get(row, "phrase")
        if phrase is None and not isinstance(row, dict):
            try:
                phrase = row[0]
            except (IndexError, TypeError):
                phrase = None
        if phrase:
            phrases.add(str(phrase).strip().lower())
    phrases.discard("")
    return phrases


# ---------------------------------------------------------------------------
# Text pipeline (ported from the prototype)
# ---------------------------------------------------------------------------


def _clean(text: str) -> str:
    return _URL_RE.sub(" ", html.unescape(text or ""))


def _tokenize(text: str) -> list[str]:
    return [
        t
        for t in _WORD_RE.findall(text.lower())
        if t not in STOPWORDS and len(t) >= 3 and not t.startswith("'")
    ]


def _grams(tokens: list[str]) -> list[str]:
    out = list(tokens)
    out.extend(f"{a} {b}" for a, b in zip(tokens, tokens[1:]))
    return out


def _term_blocked(term: str, blocked: set[str]) -> bool:
    """True when the term or any of its component words is in ``blocked``."""
    if term in blocked:
        return True
    return any(w in blocked for w in term.split())


def _magnitude_band(ratio: float) -> str:
    if ratio >= 10.0:
        return "signature"
    if ratio >= 3.0:
        return "characteristic"
    return "mild"


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def compute_team_keyness(
    db: Any,
    *,
    seasons: list[int],
    top_n: int = 30,
    min_team_docs: int = 200,
    teams: list[str] | None = None,
    weekly: bool = False,
    commit: bool = False,
) -> dict:
    """Compute + (optionally) store per-(team, season) distinctive terms.

    ``teams`` is an optional list of team slugs. When given, those teams are
    computed regardless of the ``min_team_docs`` floor (you asked for them);
    when None, every team in the corpus is computed and the floor gates which
    ones get written. ``commit=False`` is a dry run: computes, prints term
    lists, writes nothing.

    When ``weekly=True`` (A2), in addition to each requested season's week=0
    cut, the engine computes the CURRENT week cut for any requested season that
    contains today (per ``resolve_week``): the team's that-week docs vs the
    SAME-SEASON rest-of-corpus, stored with ``week=<week number>`` (>0),
    ``team-week`` doc floor ``_WEEKLY_MIN_DOCS`` and ``top_n`` ``_WEEKLY_TOP_N``.
    Past seasons (no current week inside them) are skipped for the weekly cut.

    Idempotent per (team_id, season_year, week): DELETE then INSERT (season cuts
    delete week=0; weekly cuts delete their own week number). Returns
    ``{"teams_written", "terms_written", "docs_scanned", "docs_gated",
    "seasons"}``.
    """
    season_list = sorted({int(s) for s in seasons})
    season_set = set(season_list)
    if not season_set:
        raise ValueError("compute_team_keyness: at least one season required")

    # -- weekly target: the current week, only for the season that contains it --
    # (A2) e.g. on 2026-06-10 resolve_week -> season_year 2025, week ~41. We only
    # cut the weekly slice for a requested season whose current week is live.
    current = resolve_week()
    weekly_week: int | None = None
    weekly_season: int | None = None
    if weekly and current.season_year in season_set:
        weekly_week = int(current.week)
        weekly_season = int(current.season_year)

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
                print(f"compute_team_keyness: unknown team slug {slug!r} — skipped",
                      flush=True)
                continue
            selected_ids.add(int(_row_get(row, "team_id")))
        explicit = True
    else:
        selected_ids = set(by_id)
        explicit = False

    structural_seed = _load_structural_seed()
    banlist = _load_banlist(db)
    generic_terms = load_generic_terms()  # A1: editorial thread-boilerplate stoplist
    city_subs = load_city_subs()

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
    city_params = {f"city_{i}": s for i, s in enumerate(sorted(city_subs))}
    city_placeholders = ", ".join(f":{k}" for k in city_params)
    doc_sql = (
        "SELECT d.conversation_document_id AS doc_id, "
        "COALESCE(d.title_text,'') || ' ' || COALESCE(d.body_text,'') AS text, "
        "SUBSTR(COALESCE(d.external_created_at_utc,''),1,10) AS day, "
        "COALESCE(d.source_name,'') AS source_name, "
        "COALESCE(d.source_subchannel,'') AS source_subchannel "
        "FROM conversation_documents d "
        "WHERE COALESCE(d.is_deleted,0) = 0 AND COALESCE(d.is_removed,0) = 0 "
        "AND (d.body_text IS NOT NULL OR d.title_text IS NOT NULL) "
        "AND (d.source_name LIKE 'reddit%' OR d.source_name LIKE 'bluesky%' "
        "OR d.source_name LIKE 'youtube%' OR d.source_name LIKE 'board%') "
        f"AND COALESCE(d.source_subchannel,'') NOT IN ({city_placeholders}) "
        "AND (COALESCE(d.relevance_ml_score, 1.0) >= 0.5)"
    )

    season_grams: dict[int, Counter] = defaultdict(Counter)
    season_tokens: dict[int, int] = defaultdict(int)
    team_grams: dict[tuple[int, int], Counter] = defaultdict(Counter)
    team_tokens: dict[tuple[int, int], int] = defaultdict(int)
    team_docs: dict[tuple[int, int], int] = defaultdict(int)
    # (toxicity_bad, length, lowered_text, display_text, source)
    quote_pool: dict[tuple[int, int], list[tuple[int, int, str, str, str]]] = (
        defaultdict(list)
    )
    # A2: weekly accumulators (only populated for the live weekly_week, if any).
    # Key is team_id only — they are all (weekly_season, weekly_week) by construction.
    week_team_grams: dict[int, Counter] = defaultdict(Counter)
    week_team_tokens: dict[int, int] = defaultdict(int)
    week_team_docs: dict[int, int] = defaultdict(int)
    week_quote_pool: dict[int, list[tuple[int, int, str, str, str]]] = defaultdict(list)

    docs_scanned = 0
    docs_gated = 0
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
            in_weekly = (
                weekly_week is not None
                and season == weekly_season
                and int(wk.week) == weekly_week
            )
            docs_scanned += 1
            if docs_scanned % 40000 == 0:
                print(
                    f"  ...{docs_scanned} docs scanned ({docs_gated} gated)",
                    flush=True,
                )
            text = _clean(_row_get(doc, "text") or "")
            if not score_text(text).is_football:
                docs_gated += 1
                continue
            tokens = _tokenize(text)
            if not tokens:
                continue
            grams = _grams(tokens)
            season_grams[season].update(grams)
            season_tokens[season] += len(grams)
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
                team_grams[key].update(grams)
                team_tokens[key] += len(grams)
                team_docs[key] += 1
                if quotable:
                    pool = quote_pool[key]
                    pool.append(
                        (int(toxicity >= 0.3), len(display), lowered, display, source)
                    )
                    if len(pool) > _QUOTE_CAP:
                        pool.sort(key=lambda c: (c[0], c[1]))
                        del pool[_QUOTE_TRIM:]
                if in_weekly:
                    week_team_grams[tid].update(grams)
                    week_team_tokens[tid] += len(grams)
                    week_team_docs[tid] += 1
                    if quotable:
                        wpool = week_quote_pool[tid]
                        wpool.append(
                            (int(toxicity >= 0.3), len(display), lowered, display, source)
                        )
                        if len(wpool) > _QUOTE_CAP:
                            wpool.sort(key=lambda c: (c[0], c[1]))
                            del wpool[_QUOTE_TRIM:]
    print(
        f"compute_team_keyness: pass done — {docs_scanned} docs scanned, "
        f"{docs_gated} relevance-gated, seasons={season_list}",
        flush=True,
    )

    # -- per-(team, season) weighted log-odds vs same-season rest ------------
    computed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    to_write: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for (tid, season), counts in sorted(team_grams.items()):
        doc_n = team_docs[(tid, season)]
        if not explicit and doc_n < min_team_docs:
            continue
        n_team = team_tokens[(tid, season)]
        n_season = season_tokens[season]
        n_rest = max(n_season - n_team, 1)
        global_counts = season_grams[season]
        blocked = _structural_terms_for(by_id.get(tid, {}), structural_seed)

        candidates: list[dict[str, Any]] = []
        for term, ca in counts.items():
            if ca < MIN_COUNT:
                continue
            cg = global_counts.get(term, ca)
            cb = max(cg - ca, 0)
            aw = ALPHA0 * cg / max(n_season, 1)
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

        # receipt quotes: shortest low-toxicity short doc containing the term
        pool = sorted(quote_pool.get((tid, season), []), key=lambda c: (c[0], c[1]))
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
                    "week": 0,
                    "term_rank": rank,
                    "team_doc_count": doc_n,
                    "team_token_count": n_team,
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
            f"  {slug} {season}: {doc_n} docs, top terms: "
            + ", ".join(r["term"] for r in rows[:10]),
            flush=True,
        )

    # -- A2: weekly cuts — the team's current-week docs vs the SAME-SEASON ----
    # rest-of-corpus (season counts minus the team-week counts). Floors:
    # _WEEKLY_MIN_DOCS docs per team-week (no explicit-teams bypass — it is a
    # data-quality floor, not a selection filter), _WEEKLY_MIN_COUNT per term,
    # top _WEEKLY_TOP_N kept. Stored with week=<live week number> (>0).
    weekly_to_write: dict[int, list[dict[str, Any]]] = {}
    if weekly_week is not None:
        n_season_w = season_tokens.get(weekly_season, 0)
        global_counts_w = season_grams.get(weekly_season, Counter())
        for tid, counts in sorted(week_team_grams.items()):
            doc_n = week_team_docs[tid]
            if doc_n < _WEEKLY_MIN_DOCS:
                continue
            n_team = week_team_tokens[tid]
            n_rest = max(n_season_w - n_team, 1)
            blocked = _structural_terms_for(by_id.get(tid, {}), structural_seed)

            candidates = []
            for term, ca in counts.items():
                if ca < _WEEKLY_MIN_COUNT:
                    continue
                cg = global_counts_w.get(term, ca)
                cb = max(cg - ca, 0)
                aw = ALPHA0 * cg / max(n_season_w, 1)
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
            candidates.sort(
                key=lambda c: (-c["z_score"], -c["mention_count"], c["term"])
            )
            candidates = candidates[:_WEEKLY_TOP_N]

            pool = sorted(
                week_quote_pool.get(tid, []), key=lambda c: (c[0], c[1])
            )
            rows = []
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
                        "season_year": weekly_season,
                        "week": weekly_week,
                        "term_rank": rank,
                        "team_doc_count": doc_n,
                        "team_token_count": n_team,
                        "sample_quote": quote,
                        "sample_quote_source": quote_source,
                        "model_version": MODEL_VERSION,
                        "computed_at_utc": computed_at,
                        **cand,
                    }
                )
            weekly_to_write[tid] = rows
            slug = _row_get(by_id.get(tid, {}), "slug") or tid
            print(
                f"  {slug} {weekly_season} wk{weekly_week}: {doc_n} docs, "
                "top terms: " + ", ".join(r["term"] for r in rows[:6]),
                flush=True,
            )

    # -- write (idempotent DELETE + INSERT over the full recompute scope) -----
    # The DELETE covers every selected (team, requested season) cut, INCLUDING
    # cuts that no longer qualify (below the doc floor / no surviving terms).
    # Otherwise stale rows from a prior run linger and the lexicon module keeps
    # rendering them — e.g. penn-state 'campus' / tennessee 'knoxville' after
    # the 2026-06-10 city-sub seed expansion dropped both below the floor.
    terms_written = 0
    teams_written = 0
    if commit:
        insert_sql = (
            "INSERT INTO team_discourse_terms ("
            "team_id, season_year, week, term, term_rank, mention_count, "
            "rest_count, z_score, rate_ratio, log2_ratio, magnitude_band, "
            "team_doc_count, team_token_count, sample_quote, "
            "sample_quote_source, model_version, computed_at_utc"
            ") VALUES ("
            ":team_id, :season_year, :week, :term, :term_rank, :mention_count, "
            ":rest_count, :z_score, :rate_ratio, :log2_ratio, :magnitude_band, "
            ":team_doc_count, :team_token_count, :sample_quote, "
            ":sample_quote_source, :model_version, :computed_at_utc)"
        )
        with db.connection() as conn:
            for tid in sorted(selected_ids):
                for season in season_list:
                    conn.execute(
                        "DELETE FROM team_discourse_terms "
                        "WHERE team_id = :team_id AND season_year = :season_year "
                        "AND week = 0",
                        {"team_id": tid, "season_year": season},
                    )
                # A2: the weekly cut clears its own week number — including
                # team-weeks that no longer qualify (same stale-row contract
                # as the season DELETE above).
                if weekly_week is not None:
                    conn.execute(
                        "DELETE FROM team_discourse_terms "
                        "WHERE team_id = :team_id AND season_year = :season_year "
                        "AND week = :week",
                        {
                            "team_id": tid,
                            "season_year": weekly_season,
                            "week": weekly_week,
                        },
                    )
            for (_tid, _season), rows in sorted(to_write.items()):
                conn.executemany(insert_sql, rows)
                terms_written += len(rows)
            for _tid, rows in sorted(weekly_to_write.items()):
                conn.executemany(insert_sql, rows)
                terms_written += len(rows)
            conn.commit()
        teams_written = len(
            {tid for tid, _season in to_write} | set(weekly_to_write)
        )
    elif not commit:
        print(
            "compute_team_keyness: dry run — "
            f"{sum(len(rows) for rows in to_write.values())} season terms across "
            f"{len(to_write)} (team, season) cuts + "
            f"{sum(len(rows) for rows in weekly_to_write.values())} weekly terms "
            f"across {len(weekly_to_write)} team-weeks NOT written (use --commit)",
            flush=True,
        )

    return {
        "teams_written": teams_written,
        "terms_written": terms_written,
        "docs_scanned": docs_scanned,
        "docs_gated": docs_gated,
        "seasons": season_list,
    }
