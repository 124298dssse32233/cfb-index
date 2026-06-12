"""Fan-Ledger detector (DETERMINISTIC subset of doc 47).

Turns the five Fan Ledgers (Hope / Grievance / Belonging / Judgment / Grudge)
into buildable, *deterministic* detectors. ZERO new LLM / Ollama / GPU call:
the per-doc stance signal is the sentiment/sarcasm/emotion the daily CardiffNLP
encoder pass ALREADY wrote onto ``conversation_document_targets``. The grounded
lexicons (doc 47 §2, real corpus frequencies) are the interpretable hybrid
feature + the human-readable "why this fired" trace — never the sole signal.

Pipeline per (player_external_id, season, week):
  1. Pull the player's tagged docs from conversation_document_targets, joined to
     conversation_documents for body_text + relevance_ml_score; drop off-topic
     noise via the relevance gate FIRST (doc 47 step 1, doc 45 risk).
  2. Per ledger: feature = lexicon hit-rate (§2, word-boundary + lemma)
     + directionality from audience_bucket/person (§3)
     + the already-computed per-doc sentiment_score (encoder stance)
     + (1 - sarcasm_score) down-weight (§4 — down-weight, never strip).
  3. Aggregate to a RATE (hits / mentions) so loud players don't dominate,
     shrunk toward a cohort prior (empirical-Bayes, cold-start safe).
  4. fired = rate above FIRE_THRESHOLD (cohort 75th pct OR z>1.0) AND
     doc_count >= MIN_DOCS(5) AND source_count >= MIN_SOURCES(2).
  5. confidence = model_agreement x source_diversity x (1 - sarcasm_risk).
  6. Pair each ledger with its STRUCTURED ANCHOR (doc 47 §5) so it grounds the
     claim and can fire even when chatter is thin.

Editorial stance (doc 42 §1, doc 49): COMPILE, do not adjudicate. These scores
describe *observed fan conversation* attributed to the fanbase; they are never
the site's verdict. The C7 do-not-amplify floor (doc 49) is honored by dropping
high-toxicity docs from the discourse aggregate so volume can never auto-surface
pile-ons / unverified allegations.

Stable key: ALL writes key on player_external_id = the cfbd athlete id
(``player_source_ids.source_player_id`` WHERE source_name='cfbd'), the linkrot
anchor per src/cfb_rankings/player_id_anchor.py. player_id is a convenience
denorm only — never the cache key (roster_entries has NO external_id column).

Every path degrades to an empty list / None on thin or missing data and NEVER
raises into a caller; the enrich writer is a NON-critical step.

Public API:
    LEXICONS: dict                                   the grounded seed lexicons (doc 47 §2)
    score_ledgers(db, player_external_id, season_year, week=None) -> list[dict]
    write_ledger_scores(db, season_year, week=None) -> int
    fetch_ledger_lead(db, player_external_id, season_year, week=None) -> dict | None
"""
from __future__ import annotations

import json
import math
import re
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Thresholds (doc 47 §4). Start here; tune against the gold benchmark later.
# ---------------------------------------------------------------------------
MIN_DOCS = 5          # representativeness floor — distinct tagged docs in window
MIN_SOURCES = 2       # independent origins — one troll/bot != a narrative
FIRE_Z = 1.0          # rate z-score above which a ledger fires (above noise)
LEAD_Z = 2.0          # strong enough to LEAD the card
FIRE_PCT = 0.75       # OR: rate above cohort 75th percentile

# Relevance gate — drop off-topic noise BEFORE scoring (doc 47 step 1). Docs
# with NULL relevance pass (not-yet-scored), but anything scored must clear it.
RELEVANCE_GATE = 0.30

# C7 do-not-amplify floor (doc 49): exclude high-toxicity docs from the
# discourse aggregate so volume cannot auto-surface pile-ons / allegations.
# toxicity_score is sparse (often NULL) — NULL passes; only a high score drops.
TOXICITY_CEILING = 0.85

# Empirical-Bayes shrinkage strength (pseudo-count of cohort-prior "mentions").
# Larger = cold-start players pulled harder toward the prior rate.
EB_PRIOR_STRENGTH = 8.0

LEDGERS = ("hope", "grievance", "belonging", "judgment", "grudge")

# audience_bucket has FOUR values: fan / local / national / rival.
# 'fan' and 'local' are the home/us slice; 'rival' is them; 'national' neutral.
_US_BUCKETS = frozenset({"fan", "local"})
_THEM_BUCKETS = frozenset({"rival"})


# ---------------------------------------------------------------------------
# §2 — The grounded lexicons (corpus-frequency seeds, doc 47 §2). Word-boundary
# + lemma compiled at import. These are FEATURES + the audit trace, not a
# standalone classifier. Multi-word phrases match as phrases; single tokens use
# \b boundaries so "edge" doesn't match "edged".
# ---------------------------------------------------------------------------
LEXICONS: dict[str, list[str]] = {
    # Grievance — disrespect as fuel (direction: US)
    "grievance": [
        "doubt", "doubted", "joke", "underrated", "screwed", "snub", "snubbed",
        "disrespect", "disrespected", "biased", "robbed",
        "slept on", "no love", "count us out", "count me out",
        "prove them wrong", "bulletin board", "chip on", "written off",
        "no respect", "overlooked",
    ],
    # Hope — potential > production (the dominant register)
    "hope": [
        "future", "potential", "next year", "breakout", "ceiling", "dawg",
        "sleeper", "upside", "franchise", "special",
        "wait till", "just wait", "if he develops", "buy stock",
        "the guy of the future", "glue",
    ],
    # Belonging — love orthogonal to talent (direction: US)
    "belonging": [
        "loyal", "loyalty", "culture", "stayed", "hometown", "our guy",
        "one of us", "homegrown", "bleeds",
        "four-year", "never left", "turned down the bag", "local kid",
        "in-state", "program guy", "warrior", "glue guy",
    ],
    # Judgment — fans as jury (direction: contested)
    "judgment": [
        "deserve", "deserves", "legit", "resume", "strength of schedule",
        "eye test", "overrated",
        "system", "stat padder", "empty stats", "hasn't played anyone",
        "should be ranked", "not elite", "washed", "proven", "mid",
    ],
    # Grudge — rooting against > for (direction: THEM / rival audience)
    "grudge": [
        "rival", "hate", "owned", "cope", "beat them", "fraud", "overrated",
        "choke", "choked", "rent free",
        "seething", "clown", "bust", "washed", "gets exposed", "exposed",
        "cooked", "down bad",
    ],
}

# Villain-tag terms — who is doing the disrespecting (Grievance amplifier, §2.1).
_GRIEVANCE_VILLAINS = ("media", "espn", "committee", "pollster", "pollsters", "analyst", "analysts")


def _compile_lexicon(terms: Iterable[str]) -> list[tuple[str, re.Pattern[str]]]:
    out: list[tuple[str, re.Pattern[str]]] = []
    for term in terms:
        t = term.strip()
        if not t:
            continue
        # Phrase vs single token. Allow internal hyphen/space flex on phrases.
        if " " in t or "-" in t:
            esc = re.escape(t).replace(r"\ ", r"[\s-]+").replace(r"\-", r"[\s-]+")
            pat = re.compile(rf"(?<!\w){esc}(?!\w)", re.IGNORECASE)
        else:
            pat = re.compile(rf"\b{re.escape(t)}\w*", re.IGNORECASE)  # lemma-ish suffix flex
        out.append((t, pat))
    return out


_COMPILED: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    ledger: _compile_lexicon(terms) for ledger, terms in LEXICONS.items()
}
_COMPILED_VILLAINS = _compile_lexicon(_GRIEVANCE_VILLAINS)


# ---------------------------------------------------------------------------
# §3 — Directionality. The same term flips ledger by audience + person.
# 'overrated' = Grievance when local/us, Grudge when rival/them.
# ---------------------------------------------------------------------------
_FIRST_PERSON = re.compile(r"\b(we|us|our|ours|ourselves)\b", re.IGNORECASE)
_THIRD_PERSON = re.compile(r"\b(they|them|their|he|him|his)\b", re.IGNORECASE)


def _direction(audience_bucket: str | None, body_text: str) -> str:
    """Return 'us' | 'them' | 'contested' from audience + person (doc 47 §3)."""
    bucket = (audience_bucket or "").lower()
    if bucket in _THEM_BUCKETS:
        return "them"
    if bucket in _US_BUCKETS:
        return "us"
    # national / unknown -> lean on person; default contested (neutral Judgment).
    has_first = bool(_FIRST_PERSON.search(body_text or ""))
    has_third = bool(_THIRD_PERSON.search(body_text or ""))
    if has_first and not has_third:
        return "us"
    if has_third and not has_first:
        return "them"
    return "contested"


def _lexical_features(body_text: str, ledger: str, direction: str) -> float:
    """Interpretable lexicon hit-rate feature for one (doc, ledger) pair.

    Returns a 0..~1 saturating intensity: the fraction of the ledger's lexicon
    that appears, lightly boosted for Grievance villain-tags, and gated by
    directionality for the polysemous ledgers (doc 47 §3). This is a FEATURE
    combined with encoder sentiment downstream — never the sole signal.
    """
    text = body_text or ""
    if not text:
        return 0.0
    patterns = _COMPILED.get(ledger, [])
    if not patterns:
        return 0.0

    hit = 0
    for _term, pat in patterns:
        if pat.search(text):
            hit += 1
    if hit == 0:
        return 0.0

    # Direction gate for polysemous ledgers: a 'them'-pointed doc cannot count
    # toward an US ledger (Grievance/Belonging), and an 'us'-pointed doc cannot
    # count toward Grudge. Judgment/Hope are direction-agnostic.
    if ledger in ("grievance", "belonging") and direction == "them":
        return 0.0
    if ledger == "grudge" and direction == "us":
        return 0.0

    # Saturating hit-rate vs the lexicon size (so a doc that name-checks one
    # term scores meaningfully but stacking terms still climbs).
    base = 1.0 - math.exp(-1.2 * hit)

    if ledger == "grievance":
        for _term, pat in _COMPILED_VILLAINS:
            if pat.search(text):
                base = min(1.0, base + 0.10)
                break
    return max(0.0, min(1.0, base))


# ---------------------------------------------------------------------------
# Per-ledger expected sentiment polarity (encoder stance fusion, doc 47 §1.2).
# sentiment_score is signed: -1 negative .. +1 positive (neutral ~0).
#   Hope / Belonging   -> positive talk about the player corroborates the read.
#   Grievance          -> fans angry ON the player's behalf (negative valence,
#                         pointed outward) corroborates "disrespect as fuel".
#   Grudge             -> rival NEGATIVE sentiment corroborates rooting-against.
#   Judgment           -> contested; magnitude matters, sign does not.
# Returns a 0..1 corroboration weight for a doc's sentiment given the ledger.
# ---------------------------------------------------------------------------
def _sentiment_corroboration(ledger: str, sentiment_score: float | None) -> float:
    if sentiment_score is None:
        return 0.5  # no encoder read -> neutral corroboration, lexicon carries
    s = max(-1.0, min(1.0, float(sentiment_score)))
    if ledger in ("hope", "belonging"):
        return 0.5 + 0.5 * max(0.0, s)          # rewards positive
    if ledger in ("grievance", "grudge"):
        return 0.5 + 0.5 * max(0.0, -s)         # rewards negative
    # judgment — magnitude is the signal (strong opinion either way)
    return 0.5 + 0.5 * abs(s)


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    try:
        v = row[key]
    except (TypeError, KeyError, IndexError):
        return default
    return default if v is None else v


# ---------------------------------------------------------------------------
# External-id resolution (the stable anchor).
# ---------------------------------------------------------------------------
def _resolve_external_id(db, player_id: int) -> str | None:
    row = db.query_one(
        "SELECT source_player_id FROM player_source_ids "
        "WHERE player_id = :pid AND source_name = 'cfbd'",
        {"pid": int(player_id)},
    )
    if not row:
        return None
    val = row.get("source_player_id")
    return str(val) if val else None


def _resolve_player_id(db, player_external_id: str) -> int | None:
    row = db.query_one(
        "SELECT player_id FROM player_source_ids "
        "WHERE source_player_id = :ext AND source_name = 'cfbd' LIMIT 1",
        {"ext": str(player_external_id)},
    )
    if not row:
        return None
    val = row.get("player_id")
    return int(val) if val is not None else None


# ---------------------------------------------------------------------------
# Discourse pull — tagged docs joined to text + relevance, gated.
# ---------------------------------------------------------------------------
def _fetch_player_docs(db, player_id: int, season_year: int, week: int | None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"pid": int(player_id), "s": int(season_year)}
    week_clause = ""
    if week is not None:
        week_clause = "AND cdt.week = :w"
        params["w"] = int(week)
    rows = db.query_all(
        f"""
        SELECT cdt.conversation_document_id AS doc_id,
               cdt.audience_bucket          AS audience_bucket,
               cdt.sentiment_label          AS sentiment_label,
               cdt.sentiment_score          AS sentiment_score,
               cdt.sarcasm_score            AS sarcasm_score,
               cdt.toxicity_score           AS toxicity_score,
               cd.body_text                 AS body_text,
               cd.title_text                AS title_text,
               cd.relevance_ml_score        AS relevance_ml_score,
               cd.source_name               AS source_name,
               cd.source_author_id          AS author_id,
               cd.source_author_name        AS author_name,
               cd.source_url                AS source_url
          FROM conversation_document_targets cdt
          JOIN conversation_documents cd
            ON cd.conversation_document_id = cdt.conversation_document_id
         WHERE cdt.player_id = :pid
           AND cdt.season_year = :s
           {week_clause}
           AND COALESCE(cd.is_deleted, 0) = 0
           AND COALESCE(cd.is_removed, 0) = 0
        """,
        params,
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        rel = r.get("relevance_ml_score")
        if rel is not None and float(rel) < RELEVANCE_GATE:
            continue  # off-topic noise out (doc 47 step 1)
        tox = r.get("toxicity_score")
        if tox is not None and float(tox) > TOXICITY_CEILING:
            continue  # C7 do-not-amplify floor (doc 49)
        out.append(r)
    return out


def _source_key(r: dict[str, Any]) -> str:
    """Independent-origin key for MIN_SOURCES (author first, then source)."""
    return (
        str(r.get("author_id") or r.get("author_name") or "")
        or str(r.get("source_name") or "")
        or str(r.get("doc_id"))
    )


# ---------------------------------------------------------------------------
# Structured anchors (doc 47 §5) — fact the ledger fuses with; fires when chatter
# is thin and grounds the discourse claim. Each returns a small JSON-able dict or
# None. Keyed on player_id (resolved from the external id by the caller).
# ---------------------------------------------------------------------------
def _anchor_hope(db, player_id: int, season_year: int) -> dict[str, Any] | None:
    rec = db.query_one(
        "SELECT stars, rating, national_rank FROM player_recruiting_profiles "
        "WHERE player_id = :pid AND stars IS NOT NULL "
        "ORDER BY season_year DESC LIMIT 1",
        {"pid": player_id},
    )
    nil = db.query_one(
        "SELECT rank, valuation_usd FROM player_nil_valuations "
        "WHERE player_id = :pid ORDER BY as_of_date DESC LIMIT 1",
        {"pid": player_id},
    )
    watch = db.query_all(
        "SELECT award_slug, list_type, position_rank FROM player_award_watch_2026 "
        "WHERE player_id = :pid ORDER BY priority LIMIT 5",
        {"pid": player_id},
    )
    if not (rec or nil or watch):
        return None
    a: dict[str, Any] = {}
    if rec:
        a["recruiting"] = {k: rec.get(k) for k in ("stars", "rating", "national_rank") if rec.get(k) is not None}
    if nil:
        a["nil"] = {"rank": nil.get("rank"), "valuation_usd": nil.get("valuation_usd")}
    if watch:
        a["award_watch"] = [{"award": w.get("award_slug"), "rank": w.get("position_rank")} for w in watch]
    return a or None


def _anchor_grievance(db, player_id: int, season_year: int) -> dict[str, Any] | None:
    # Measurable respect gap: WEPA production vs (lack of) recognition.
    vm = db.query_all(
        "SELECT metric_name, metric_value, plays FROM player_value_metrics "
        "WHERE player_id = :pid AND season_year = :s",
        {"pid": player_id, "s": season_year},
    )
    aura = db.query_one(
        "SELECT perception_pctl, production_pctl, verdict FROM player_aura_weekly "
        "WHERE player_id = :pid AND season_year = :s "
        "ORDER BY week DESC LIMIT 1",
        {"pid": player_id, "s": season_year},
    )
    if not (vm or aura):
        return None
    a: dict[str, Any] = {}
    if vm:
        a["wepa"] = {m.get("metric_name"): {"value": m.get("metric_value"), "plays": m.get("plays")} for m in vm}
    if aura and aura.get("perception_pctl") is not None and aura.get("production_pctl") is not None:
        gap = float(aura["production_pctl"]) - float(aura["perception_pctl"])
        a["respect_gap_pctl"] = round(gap, 1)  # +ve = produces more than fans credit
        a["verdict"] = aura.get("verdict")
    return a or None


def _anchor_belonging(db, player_id: int, season_year: int) -> dict[str, Any] | None:
    tenure = db.query_one(
        "SELECT COUNT(DISTINCT season_year) AS years, "
        "MAX(team_id) AS team_id, MAX(home_state) AS home_state "
        "FROM roster_entries WHERE player_id = :pid",
        {"pid": player_id},
    )
    geo = db.query_one(
        "SELECT state_province, city FROM player_recruiting_profiles "
        "WHERE player_id = :pid AND state_province IS NOT NULL "
        "ORDER BY season_year DESC LIMIT 1",
        {"pid": player_id},
    )
    transfers = db.query_one(
        "SELECT COUNT(*) AS n FROM transfer_entries WHERE player_id = :pid",
        {"pid": player_id},
    )
    if not tenure or not tenure.get("years"):
        if not geo:
            return None
    a: dict[str, Any] = {}
    years = int(tenure.get("years") or 0) if tenure else 0
    if years:
        a["tenure_years"] = years
        a["lifer"] = bool(years >= 3)
    n_transfers = int(transfers.get("n") or 0) if transfers else 0
    a["transfers"] = n_transfers
    a["rental"] = bool(n_transfers > 0)
    # in-state read: recruiting home state vs current team's state.
    if geo and tenure and tenure.get("team_id") is not None:
        team = db.query_one(
            "SELECT state FROM teams WHERE team_id = :tid", {"tid": tenure["team_id"]}
        )
        rec_state = (geo.get("state_province") or "").strip().upper()
        team_state = ((team or {}).get("state") or "").strip().upper()
        if rec_state and team_state:
            a["in_state"] = bool(rec_state == team_state)
            a["home_state"] = rec_state
    return a or None


def _anchor_judgment(db, player_id: int, season_year: int) -> dict[str, Any] | None:
    aura = db.query_one(
        "SELECT perception_pctl, production_pctl, verdict, is_low_signal "
        "FROM player_aura_weekly WHERE player_id = :pid AND season_year = :s "
        "ORDER BY week DESC LIMIT 1",
        {"pid": player_id, "s": season_year},
    )
    vm = db.query_all(
        "SELECT metric_name, metric_value, plays FROM player_value_metrics "
        "WHERE player_id = :pid AND season_year = :s",
        {"pid": player_id, "s": season_year},
    )
    if not (aura or vm):
        return None
    a: dict[str, Any] = {}
    if aura:
        a["perception_pctl"] = aura.get("perception_pctl")
        a["production_pctl"] = aura.get("production_pctl")
        a["verdict"] = aura.get("verdict")
        a["is_low_signal"] = bool(aura.get("is_low_signal"))
    if vm:
        a["wepa"] = {m.get("metric_name"): m.get("metric_value") for m in vm}
    return a or None


def _anchor_grudge(db, player_id: int, season_year: int) -> dict[str, Any] | None:
    # Rival-audience sentiment toward this player + rivalry context.
    rival = db.query_one(
        "SELECT COUNT(*) AS n, AVG(sentiment_score) AS avg_sent "
        "FROM conversation_document_targets "
        "WHERE player_id = :pid AND season_year = :s AND audience_bucket = 'rival'",
        {"pid": player_id, "s": season_year},
    )
    team = db.query_one(
        "SELECT team_id FROM roster_entries WHERE player_id = :pid "
        "ORDER BY season_year DESC LIMIT 1",
        {"pid": player_id},
    )
    a: dict[str, Any] = {}
    if rival and int(rival.get("n") or 0) > 0:
        a["rival_mentions"] = int(rival["n"])
        if rival.get("avg_sent") is not None:
            a["rival_avg_sentiment"] = round(float(rival["avg_sent"]), 3)
    if team and team.get("team_id") is not None:
        rp = db.query_one(
            "SELECT COUNT(*) AS n FROM rivalry_pairs "
            "WHERE (team_a_id = :tid OR team_b_id = :tid) AND COALESCE(is_active, 1) = 1",
            {"tid": team["team_id"]},
        )
        if rp and int(rp.get("n") or 0) > 0:
            a["active_rivalries"] = int(rp["n"])
    return a or None


_ANCHORS = {
    "hope": _anchor_hope,
    "grievance": _anchor_grievance,
    "belonging": _anchor_belonging,
    "judgment": _anchor_judgment,
    "grudge": _anchor_grudge,
}


def _structured_anchor(db, ledger: str, player_id: int, season_year: int) -> dict[str, Any] | None:
    fn = _ANCHORS.get(ledger)
    if fn is None:
        return None
    try:
        return fn(db, int(player_id), int(season_year))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Cohort prior — the empirical-Bayes baseline rate per ledger (doc 47 step 3).
# Cached on the db object so a write-all pass computes it once. Cold-start safe:
# a player with few docs is shrunk toward this prior so a single hit can't fire.
# ---------------------------------------------------------------------------
_PRIOR_CACHE_ATTR = "_ledger_cohort_prior_cache"


def _cohort_prior(db, season_year: int, week: int | None) -> dict[str, dict[str, float]]:
    """Mean ledger hit-rate across all tagged players in the window.

    Returns {ledger: {"mean": m, "p75": p}} — the prior mean drives EB shrinkage,
    p75 is the cohort FIRE percentile gate. Computed by sampling the same scoring
    on the population once; cached per (season, week).
    """
    cache = getattr(db, _PRIOR_CACHE_ATTR, None)
    if cache is None:
        cache = {}
        try:
            setattr(db, _PRIOR_CACHE_ATTR, cache)
        except Exception:
            cache = {}
    key = (int(season_year), -1 if week is None else int(week))
    if key in cache:
        return cache[key]

    # Per-ledger rate samples across the population of tagged players.
    samples: dict[str, list[float]] = {lg: [] for lg in LEDGERS}
    try:
        pid_rows = _distinct_tagged_player_ids(db, season_year, week)
        for pid in pid_rows:
            docs = _fetch_player_docs(db, pid, season_year, week)
            if len(docs) < MIN_DOCS:
                continue
            rates = _raw_ledger_rates(docs)
            for lg in LEDGERS:
                samples[lg].append(rates[lg]["rate"])
    except Exception:
        samples = {lg: [] for lg in LEDGERS}

    prior: dict[str, dict[str, float]] = {}
    for lg in LEDGERS:
        vals = sorted(samples[lg])
        if vals:
            mean = sum(vals) / len(vals)
            std = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals)) if len(vals) > 1 else 0.0
            p75 = vals[min(len(vals) - 1, int(math.ceil(FIRE_PCT * len(vals))) - 1)] if vals else 0.0
        else:
            mean, std, p75 = 0.0, 0.0, 0.0
        prior[lg] = {"mean": mean, "std": std, "p75": p75, "n": float(len(vals))}
    cache[key] = prior
    return prior


def _distinct_tagged_player_ids(db, season_year: int, week: int | None) -> list[int]:
    params: dict[str, Any] = {"s": int(season_year)}
    wc = ""
    if week is not None:
        wc = "AND week = :w"
        params["w"] = int(week)
    rows = db.query_all(
        f"SELECT DISTINCT player_id FROM conversation_document_targets "
        f"WHERE player_id IS NOT NULL AND season_year = :s {wc}",
        params,
    )
    return [int(r["player_id"]) for r in rows if r.get("player_id") is not None]


# ---------------------------------------------------------------------------
# Raw per-ledger rates from a doc set (no prior/threshold applied yet). Shared by
# the cohort-prior sampler and the per-player scorer.
# ---------------------------------------------------------------------------
def _raw_ledger_rates(docs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    n = max(1, len(docs))
    # Precompute per-doc direction once.
    dirs = [_direction(d.get("audience_bucket"), d.get("body_text") or "") for d in docs]
    for lg in LEDGERS:
        weighted_sum = 0.0
        hit_docs = 0
        sarcasm_accum = 0.0
        traces: dict[str, int] = {}
        src_keys: set[str] = set()
        for d, direction in zip(docs, dirs):
            body = (d.get("title_text") or "") + " " + (d.get("body_text") or "")
            feat = _lexical_features(body, lg, direction)
            if feat <= 0.0:
                continue
            sent_w = _sentiment_corroboration(lg, d.get("sentiment_score"))
            sarc = float(d.get("sarcasm_score") or 0.0)
            sarc = max(0.0, min(1.0, sarc))
            # combine: lexicon feature x sentiment corroboration x (1 - sarcasm)
            contrib = feat * sent_w * (1.0 - 0.7 * sarc)  # down-weight, never strip (§4)
            weighted_sum += contrib
            hit_docs += 1
            sarcasm_accum += sarc
            src_keys.add(_source_key(d))
            # record the why-this-fired lexical trace
            for term, pat in _COMPILED.get(lg, []):
                if pat.search(body):
                    traces[term] = traces.get(term, 0) + 1
        rate = weighted_sum / n  # RATE: per-mention, so loud players don't dominate
        mean_sarc = (sarcasm_accum / hit_docs) if hit_docs else 0.0
        out[lg] = {
            "rate": rate,
            "hit_docs": hit_docs,
            "source_count": len(src_keys),
            "sarcasm_risk": mean_sarc,
            "trace": traces,
        }
    return out


# ---------------------------------------------------------------------------
# Public — score one player's five ledgers.
# ---------------------------------------------------------------------------
def score_ledgers(
    db, player_external_id: str, season_year: int, week: int | None = None,
) -> list[dict[str, Any]]:
    """Return five ledger rows for the player (one per ledger).

    Each row: {ledger, score, direction, confidence, doc_count, source_count,
    fired, structured_anchor_json, evidence_doc_ids_json, top_lexical_trace_json}.
    Degrades to [] on thin/missing data; never raises.
    """
    if db is None or not player_external_id:
        return []
    try:
        player_id = _resolve_player_id(db, str(player_external_id))
        if player_id is None:
            return []

        docs = _fetch_player_docs(db, player_id, int(season_year), week)
        doc_count = len(docs)
        rates = _raw_ledger_rates(docs) if docs else {
            lg: {"rate": 0.0, "hit_docs": 0, "source_count": 0, "sarcasm_risk": 0.0, "trace": {}}
            for lg in LEDGERS
        }
        prior = _cohort_prior(db, int(season_year), week)

        # Overall representativeness from the player's full doc set.
        all_sources = {_source_key(d) for d in docs}
        total_source_count = len(all_sources)
        evidence_doc_ids = [d.get("doc_id") for d in docs if d.get("doc_id") is not None][:50]

        results: list[dict[str, Any]] = []
        for lg in LEDGERS:
            r = rates[lg]
            raw_rate = float(r["rate"])
            pri = prior.get(lg, {"mean": 0.0, "std": 0.0, "p75": 0.0})
            prior_mean = float(pri.get("mean", 0.0))
            prior_std = float(pri.get("std", 0.0))
            p75 = float(pri.get("p75", 0.0))

            # Empirical-Bayes shrinkage toward the cohort prior mean. The more
            # hit docs, the more we trust the player's own rate (cold-start safe).
            k = float(r["hit_docs"])
            score = (k * raw_rate + EB_PRIOR_STRENGTH * prior_mean) / (k + EB_PRIOR_STRENGTH)

            # z vs cohort
            z = ((score - prior_mean) / prior_std) if prior_std > 1e-9 else (
                999.0 if score > prior_mean else 0.0
            )

            ledger_source_count = int(r["source_count"])
            representative = doc_count >= MIN_DOCS and total_source_count >= MIN_SOURCES
            above_noise = (z >= FIRE_Z) or (p75 > 0.0 and score > p75)
            fired = bool(representative and ledger_source_count >= 1 and above_noise and r["hit_docs"] > 0)

            direction = _ledger_direction(lg, docs)

            # confidence = model_agreement x source_diversity x (1 - sarcasm_risk)
            model_agreement = _model_agreement(docs, lg)
            source_diversity = min(1.0, ledger_source_count / 3.0)
            sarcasm_risk = float(r["sarcasm_risk"])
            confidence = round(
                max(0.0, min(1.0, model_agreement * source_diversity * (1.0 - sarcasm_risk))), 4
            )

            anchor = _structured_anchor(db, lg, player_id, int(season_year))

            results.append({
                "player_external_id": str(player_external_id),
                "player_id": player_id,
                "season_year": int(season_year),
                "week": week,
                "ledger": lg,
                "score": round(score, 6),
                "z": round(z, 3),
                "direction": direction,
                "confidence": confidence,
                "doc_count": doc_count,
                "source_count": ledger_source_count,
                "fired": 1 if fired else 0,
                "is_lead": 1 if (fired and z >= LEAD_Z) else 0,
                "structured_anchor_json": json.dumps(anchor, default=str) if anchor else None,
                "evidence_doc_ids_json": json.dumps(evidence_doc_ids, default=str) if evidence_doc_ids else None,
                "top_lexical_trace_json": json.dumps(
                    _top_trace(r["trace"]), default=str
                ) if r["trace"] else None,
            })
        return results
    except Exception:
        # Never raise into a caller — graceful empty.
        return []


def _top_trace(trace: dict[str, int], limit: int = 6) -> list[dict[str, Any]]:
    items = sorted(trace.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [{"term": t, "hits": c} for t, c in items]


def _ledger_direction(ledger: str, docs: list[dict[str, Any]]) -> str:
    """Aggregate the dominant direction for a ledger's firing docs.

    'us' | 'them' | 'contested' (doc 47 §3). Grudge is inherently 'them';
    Grievance/Belonging are 'us'; Judgment reflects the audience split.
    """
    if ledger == "grudge":
        return "them"
    if ledger in ("grievance", "belonging"):
        return "us"
    us = sum(1 for d in docs if (d.get("audience_bucket") or "").lower() in _US_BUCKETS)
    them = sum(1 for d in docs if (d.get("audience_bucket") or "").lower() in _THEM_BUCKETS)
    if us and them:
        return "contested"
    if them and not us:
        return "them"
    if us and not them:
        return "us"
    return "contested"


def _model_agreement(docs: list[dict[str, Any]], ledger: str) -> float:
    """Fraction of docs whose encoder sentiment agrees with the ledger polarity.

    A coherent fan read (the encoder mostly agreeing) yields higher confidence;
    a split room lowers it. Direction-agnostic ledgers (Judgment/Hope) measure
    opinion strength instead.
    """
    if not docs:
        return 0.0
    scored = [d for d in docs if d.get("sentiment_score") is not None]
    if not scored:
        return 0.5
    if ledger in ("hope", "belonging"):
        agree = sum(1 for d in scored if float(d["sentiment_score"]) >= 0.0)
    elif ledger in ("grievance", "grudge"):
        agree = sum(1 for d in scored if float(d["sentiment_score"]) <= 0.0)
    else:  # judgment — strong opinions (either pole) agree
        agree = sum(1 for d in scored if abs(float(d["sentiment_score"])) >= 0.5)
    frac = agree / len(scored)
    # Map a fraction to an agreement weight floored at 0.4 so a thin but real
    # signal isn't zeroed; 1.0 only on unanimous reads.
    return round(0.4 + 0.6 * frac, 4)


# ---------------------------------------------------------------------------
# Public — enrich writer (NON-critical step; never blocks the deploy).
# ---------------------------------------------------------------------------
def write_ledger_scores(db, season_year: int, week: int | None = None) -> int:
    """Compute + upsert player_ledger_scores for every tagged player in the window.

    Returns the number of ledger rows written. Idempotent (upsert on the
    UNIQUE key). Swallows per-player errors so one bad player never aborts the
    batch; returns whatever was written.
    """
    if db is None:
        return 0
    written = 0
    try:
        player_ids = _distinct_tagged_player_ids(db, int(season_year), week)
    except Exception:
        return 0
    # Warm the cohort prior once.
    try:
        _cohort_prior(db, int(season_year), week)
    except Exception:
        pass

    for pid in player_ids:
        try:
            ext = _resolve_external_id(db, pid)
            if not ext:
                continue  # cannot key on the stable anchor -> skip
            rows = score_ledgers(db, ext, int(season_year), week)
            for row in rows:
                _upsert_ledger_row(db, row)
                written += 1
        except Exception:
            continue
    return written


def _upsert_ledger_row(db, row: dict[str, Any]) -> None:
    payload = {
        "player_external_id": row["player_external_id"],
        "player_id": row.get("player_id"),
        "season_year": int(row["season_year"]),
        "week": row.get("week"),
        "ledger": row["ledger"],
        "score": float(row.get("score") or 0.0),
        "direction": row.get("direction"),
        "confidence": float(row.get("confidence") or 0.0),
        "doc_count": int(row.get("doc_count") or 0),
        "source_count": int(row.get("source_count") or 0),
        "fired": int(row.get("fired") or 0),
        "structured_anchor_json": row.get("structured_anchor_json"),
        "evidence_doc_ids_json": row.get("evidence_doc_ids_json"),
        "top_lexical_trace_json": row.get("top_lexical_trace_json"),
    }
    # week is part of the UNIQUE key; NULL weeks need an IS-aware conflict target.
    # SQLite treats NULLs as distinct in UNIQUE, so a NULL-week upsert may insert
    # duplicates across runs — guard by deleting the prior NULL-week row first.
    if payload["week"] is None:
        db.execute(
            "DELETE FROM player_ledger_scores "
            "WHERE player_external_id = :player_external_id "
            "AND season_year = :season_year AND week IS NULL AND ledger = :ledger",
            {
                "player_external_id": payload["player_external_id"],
                "season_year": payload["season_year"],
                "ledger": payload["ledger"],
            },
        )
        db.execute(
            """
            INSERT INTO player_ledger_scores
                (player_external_id, player_id, season_year, week, ledger, score,
                 direction, confidence, doc_count, source_count, fired,
                 structured_anchor_json, evidence_doc_ids_json, top_lexical_trace_json)
            VALUES
                (:player_external_id, :player_id, :season_year, :week, :ledger, :score,
                 :direction, :confidence, :doc_count, :source_count, :fired,
                 :structured_anchor_json, :evidence_doc_ids_json, :top_lexical_trace_json)
            """,
            payload,
        )
        return
    db.execute(
        """
        INSERT INTO player_ledger_scores
            (player_external_id, player_id, season_year, week, ledger, score,
             direction, confidence, doc_count, source_count, fired,
             structured_anchor_json, evidence_doc_ids_json, top_lexical_trace_json)
        VALUES
            (:player_external_id, :player_id, :season_year, :week, :ledger, :score,
             :direction, :confidence, :doc_count, :source_count, :fired,
             :structured_anchor_json, :evidence_doc_ids_json, :top_lexical_trace_json)
        ON CONFLICT (player_external_id, season_year, week, ledger) DO UPDATE SET
            player_id              = excluded.player_id,
            score                  = excluded.score,
            direction              = excluded.direction,
            confidence             = excluded.confidence,
            doc_count              = excluded.doc_count,
            source_count           = excluded.source_count,
            fired                  = excluded.fired,
            structured_anchor_json = excluded.structured_anchor_json,
            evidence_doc_ids_json  = excluded.evidence_doc_ids_json,
            top_lexical_trace_json = excluded.top_lexical_trace_json,
            computed_at_utc        = CURRENT_TIMESTAMP
        """,
        payload,
    )


# ---------------------------------------------------------------------------
# Public — the top fired ledger for composition lead (doc 47 step 6).
# ---------------------------------------------------------------------------
def fetch_ledger_lead(
    db, player_external_id: str, season_year: int, week: int | None = None,
) -> dict[str, Any] | None:
    """Return the strongest FIRED ledger for the player, or None.

    Reads the cache first; if empty (table young / not yet enriched) it computes
    on the fly so the render path never depends on the nightly write having run.
    """
    if db is None or not player_external_id:
        return None
    try:
        params: dict[str, Any] = {"ext": str(player_external_id), "s": int(season_year)}
        if week is not None:
            wc = "AND week = :w"
            params["w"] = int(week)
        else:
            wc = "AND week IS NULL"
        rows = db.query_all(
            f"""
            SELECT ledger, score, direction, confidence, doc_count, source_count,
                   fired, structured_anchor_json, evidence_doc_ids_json,
                   top_lexical_trace_json
              FROM player_ledger_scores
             WHERE player_external_id = :ext AND season_year = :s {wc}
               AND fired = 1
             ORDER BY score DESC LIMIT 1
            """,
            params,
        )
        if rows:
            return dict(rows[0])
    except Exception:
        pass
    # Fallback: compute live (cache miss / young table).
    try:
        scored = score_ledgers(db, str(player_external_id), int(season_year), week)
        fired = [r for r in scored if r.get("fired")]
        if not fired:
            return None
        return max(fired, key=lambda r: r.get("score", 0.0))
    except Exception:
        return None


__all__ = [
    "LEXICONS",
    "LEDGERS",
    "MIN_DOCS",
    "MIN_SOURCES",
    "score_ledgers",
    "write_ledger_scores",
    "fetch_ledger_lead",
]
