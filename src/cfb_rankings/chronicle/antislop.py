"""Antislop sampler + banlist enforcement (CFB Index Chronicle).

Three defense layers:
  1. PROMPT-LEVEL — banlist embedded in system prompt (handled by prompts.py)
  2. LOGIT BIAS — push down first-token probability for banned phrases at decode
  3. BACKTRACKING — post-gen scan; on hit, truncate + regenerate with stronger bias

Severity → bias mapping:
  5.0 → -100  (effectively impossible)
  2.0 → -40   (strongly disfavored)
  1.0 → -20   (mildly disfavored)
  0.5 → -10   (soft nudge)

Public API:
    load_banlist(db, kinds=None, active_only=True) → list[BanEntry]
    build_logit_bias(banlist, tokenizer=None) → dict[str, float]
    check_violations(text, banlist) → list[Violation]
    backtrack_and_regenerate(...) → tuple[str, int]
    apply_antislop_to_config(config, banlist) → GenerationConfig  (mutates + returns)
    score_slop_fingerprint(text, banlist) → float  (0..1, higher = more slop)
    compute_mtld(text) → float
    compute_ngram_novelty(text, prior_corpus, n=4) → float
    record_batch_observation(db, batch_id, card_texts, banlist) → dict
"""
from __future__ import annotations

import json
import logging
import re
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("cfb_rankings.chronicle.antislop")

# ---------------------------------------------------------------------------
# Compiled regex for em-dash counting and word tokenisation
# ---------------------------------------------------------------------------

_EM_DASH_RE = re.compile(r"—")
_WORD_RE = re.compile(r"[A-Za-z0-9]+")
_ALPHA_TOKEN_RE = re.compile(r"[a-z0-9]+")


# ---------------------------------------------------------------------------
# Core dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BanEntry:
    """A single banned phrase with severity metadata.

    Attributes:
        phrase:   The exact phrase string to ban (case-insensitive matching).
        kind:     Category from chronicle_banlist.kind column.
        severity: Float in [0.5, 5.0] — higher = more aggressively penalised.

    Property:
        bias: logit bias value (negative float). Derived as ``-20.0 * severity``
              so that severity 5.0 maps to -100 and severity 0.5 maps to -10.
    """

    phrase: str
    kind: str
    severity: float

    @property
    def bias(self) -> float:
        """Return the logit bias value for this entry.

        Mapping (per spec):
            5.0 → -100
            2.0 →  -40
            1.0 →  -20
            0.5 →  -10
        """
        return -20.0 * self.severity


@dataclass(frozen=True)
class Violation:
    """A detected occurrence of a banned phrase in generated text.

    Attributes:
        phrase:   The matching banned phrase.
        start:    Character offset of the match start (inclusive).
        end:      Character offset of the match end (exclusive).
        severity: Inherited from the BanEntry that matched.
        kind:     Category of the banned phrase.

    Property:
        span: ``(start, end)`` tuple for convenience.
    """

    phrase: str
    start: int
    end: int
    severity: float
    kind: str

    @property
    def span(self) -> tuple[int, int]:
        """Return ``(start, end)`` character offsets."""
        return (self.start, self.end)


# ---------------------------------------------------------------------------
# Banlist loading
# ---------------------------------------------------------------------------


def load_banlist(
    db: Any,
    kinds: list[str] | None = None,
    active_only: bool = True,
) -> list[BanEntry]:
    """Load banned phrases from the ``chronicle_banlist`` DB table.

    Args:
        db:          Database accessor with a ``query_all(sql, params)`` method.
        kinds:       Optional list of kind strings to include (e.g. ``["cliche",
                     "ai_slop"]``). If *None*, all kinds are returned.
        active_only: When *True* (default), only rows where ``is_active = 1``
                     are returned.

    Returns:
        List of :class:`BanEntry` instances sorted by severity descending (most
        severe phrase first, so callers iterating in order encounter worst
        offenders first).
    """
    conditions: list[str] = []
    params: dict[str, Any] = {}

    if active_only:
        conditions.append("is_active = 1")

    if kinds:
        placeholders = ", ".join(f":kind_{i}" for i in range(len(kinds)))
        conditions.append(f"kind IN ({placeholders})")
        for i, k in enumerate(kinds):
            params[f"kind_{i}"] = k

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT phrase, kind, severity FROM chronicle_banlist {where_clause}"

    rows = db.query_all(sql, params)

    entries: list[BanEntry] = []
    for row in rows:
        if isinstance(row, dict):
            entries.append(
                BanEntry(
                    phrase=row["phrase"],
                    kind=row["kind"],
                    severity=float(row["severity"]),
                )
            )
        else:
            # Support tuple rows
            entries.append(
                BanEntry(
                    phrase=row[0],
                    kind=row[1],
                    severity=float(row[2]),
                )
            )

    entries.sort(key=lambda e: e.severity, reverse=True)
    return entries


# ---------------------------------------------------------------------------
# Violation detection
# ---------------------------------------------------------------------------


def check_violations(text: str, banlist: list[BanEntry]) -> list[Violation]:
    """Scan *text* for occurrences of every phrase in *banlist*.

    Matching is case-insensitive substring search.  All occurrences of all
    phrases are reported; no overlap deduplication is performed.

    Args:
        text:     The generated text to scan.
        banlist:  List of :class:`BanEntry` instances to check.

    Returns:
        List of :class:`Violation` instances sorted by start offset ascending.
        Empty list when *text* is empty or no phrases match.
    """
    if not text:
        return []

    text_lower = text.lower()
    violations: list[Violation] = []

    for entry in banlist:
        phrase_lower = entry.phrase.lower()
        start = 0
        while True:
            idx = text_lower.find(phrase_lower, start)
            if idx == -1:
                break
            violations.append(
                Violation(
                    phrase=entry.phrase,
                    start=idx,
                    end=idx + len(entry.phrase),
                    severity=entry.severity,
                    kind=entry.kind,
                )
            )
            start = idx + len(phrase_lower)

    violations.sort(key=lambda v: v.start)
    return violations


# ---------------------------------------------------------------------------
# Logit bias construction
# ---------------------------------------------------------------------------


def build_logit_bias(
    banlist: list[BanEntry],
    tokenizer: Any | None = None,
) -> dict[str, float]:
    """Build a logit-bias dict suitable for llama-server's string-keyed API.

    Without a tokenizer, returns ``{phrase: bias_value}`` where each phrase maps
    to its :attr:`BanEntry.bias`.  This form is consumed directly by newer
    llama-server builds that accept string-keyed logit_bias payloads.

    When a *tokenizer* is supplied (optional, future use), the dict will be
    keyed by token-id integers instead.  Currently falls back to string mode.

    Args:
        banlist:    Loaded banlist entries.
        tokenizer:  Optional tokenizer (ignored in current implementation).

    Returns:
        Dict mapping phrase strings (or token ids) to negative float bias values.
    """
    return {entry.phrase: entry.bias for entry in banlist}


# ---------------------------------------------------------------------------
# Config mutation
# ---------------------------------------------------------------------------


def apply_antislop_to_config(
    config: Any,
    banlist: list[BanEntry],
    tokenizer: Any | None = None,
) -> Any:
    """Attach antislop fields to a :class:`GenerationConfig` object.

    Mutates and returns *config*.  Sets three fields:

    - ``logit_bias``          — phrase → bias float dict from :func:`build_logit_bias`
    - ``antislop_banlist``    — flat list of banned phrase strings
    - ``antislop_severity``   — phrase → severity float dict

    Args:
        config:     A :class:`~cfb_rankings.chronicle.runtime.GenerationConfig`
                    or any object with settable attributes.
        banlist:    Loaded banlist entries.
        tokenizer:  Passed through to :func:`build_logit_bias`.

    Returns:
        The mutated *config* object.
    """
    config.logit_bias = build_logit_bias(banlist, tokenizer)
    config.antislop_banlist = [b.phrase for b in banlist]
    config.antislop_severity = {b.phrase: b.severity for b in banlist}
    return config


# ---------------------------------------------------------------------------
# Slop fingerprint scoring
# ---------------------------------------------------------------------------


def score_slop_fingerprint(text: str, banlist: list[BanEntry]) -> float:
    """Return a composite slop score in [0.0, 1.0].

    Higher scores indicate lower editorial quality.  Clean prose should score
    below 0.2; obviously sloppy text above 0.5.

    Composition:
    - **Hit rate** (70% weight): ``sum(v.severity for v in violations) /
      max(1, word_count / 50)``, capped at 1.0.
    - **Em-dash density** (30% weight): em-dashes per 100 words.  Penalty kicks
      in above 2 per 100 words; capped at 1.0.

    Args:
        text:    Generated card text.
        banlist: Loaded banlist entries.

    Returns:
        Float in [0.0, 1.0].
    """
    if not text:
        return 0.0

    words = _WORD_RE.findall(text)
    word_count = len(words)

    violations = check_violations(text, banlist)
    severity_sum = sum(v.severity for v in violations)

    # Hit rate component
    denominator = max(1, word_count / 50)
    hit_rate = min(1.0, severity_sum / denominator)

    # Em-dash density component
    em_dash_count = len(_EM_DASH_RE.findall(text))
    em_dash_per_100 = (em_dash_count / max(1, word_count)) * 100.0
    # Penalty: if > 2 per 100 words, normalise over a max of ~10 per 100
    em_dash_penalty = min(1.0, max(0.0, (em_dash_per_100 - 2.0) / 8.0))

    score = 0.70 * hit_rate + 0.30 * em_dash_penalty
    return max(0.0, min(1.0, score))


# ---------------------------------------------------------------------------
# Lexical diversity: MTLD
# ---------------------------------------------------------------------------


def compute_mtld(text: str, threshold: float = 0.72) -> float:
    """Compute Measure of Textual Lexical Diversity (MTLD).

    Implements the forward-scan algorithm from McCarthy & Jarvis (2010).  The
    text is scanned word by word; when the running type-token ratio (TTR) drops
    below *threshold*, one factor is recorded and the window resets.

    Args:
        text:      Input text.
        threshold: TTR threshold for factor completion (default 0.72).

    Returns:
        MTLD float.  Higher = more lexically diverse.  Returns 0.0 for empty
        or single-token input.
    """
    tokens = _WORD_RE.findall(text.lower())
    total = len(tokens)
    if total == 0:
        return 0.0

    def _scan(token_list: list[str]) -> float:
        factor_count = 0.0
        types: set[str] = set()
        token_count = 0

        for token in token_list:
            types.add(token)
            token_count += 1
            ttr = len(types) / token_count
            if ttr <= threshold:
                factor_count += 1.0
                types = set()
                token_count = 0

        # Partial final factor
        if token_count > 0:
            ttr = len(types) / token_count
            # Proportion of the way from 1.0 to threshold
            if ttr < 1.0:
                partial = (1.0 - ttr) / (1.0 - threshold)
            else:
                partial = 0.0
            factor_count += partial

        if factor_count == 0:
            return float(total)
        return total / factor_count

    return _scan(tokens)


# ---------------------------------------------------------------------------
# N-gram novelty
# ---------------------------------------------------------------------------


def compute_ngram_novelty(
    text: str,
    prior_corpus: str | list[str],
    n: int = 4,
) -> float:
    """Fraction of n-grams in *text* NOT found in *prior_corpus*.

    Word-level n-grams using lowercased alphanumeric tokens.

    Args:
        text:          The newly generated text to evaluate.
        prior_corpus:  Either a single string or a list of strings forming the
                       reference corpus.
        n:             N-gram size (default 4).

    Returns:
        Float in [0.0, 1.0].  1.0 means fully novel; 0.0 means all n-grams
        already appeared in the corpus.  Returns 1.0 for empty text or empty
        prior corpus.
    """
    if not text:
        return 1.0

    if isinstance(prior_corpus, list):
        corpus_text = " ".join(prior_corpus)
    else:
        corpus_text = prior_corpus

    if not corpus_text.strip():
        return 1.0

    def _ngrams(tokens: list[str], size: int) -> set[tuple[str, ...]]:
        return {tuple(tokens[i : i + size]) for i in range(len(tokens) - size + 1)}

    text_tokens = _ALPHA_TOKEN_RE.findall(text.lower())
    corpus_tokens = _ALPHA_TOKEN_RE.findall(corpus_text.lower())

    if len(text_tokens) < n:
        return 1.0

    text_ngrams = _ngrams(text_tokens, n)
    if not text_ngrams:
        return 1.0

    corpus_ngrams = _ngrams(corpus_tokens, n)

    novel = text_ngrams - corpus_ngrams
    return len(novel) / len(text_ngrams)


# ---------------------------------------------------------------------------
# Backtracking regeneration
# ---------------------------------------------------------------------------


def backtrack_and_regenerate(
    text: str,
    violations: list[Violation],
    backend: Any,
    base_prompt: str,
    config: Any,
    max_retries: int = 3,
    bias_amplification: float = 1.5,
) -> tuple[str, int]:
    """Truncate at the first violation and regenerate with amplified bias.

    When no violations are present, returns *(text, 0)* immediately.

    On each retry:
    1. Truncates the text at the character offset of the first violation.
    2. Amplifies all logit bias values by *bias_amplification*.
    3. Calls ``backend.generate(base_prompt + truncated_text, amplified_config)``.
    4. Re-checks for violations in the result.

    Args:
        text:               Current generated text.
        violations:         Violations detected in *text* (sorted by start).
        backend:            Object with a ``generate(prompt, config)`` method
                            returning an object with a ``.text`` attribute.
        base_prompt:        System/user prompt prefix.
        config:             Generation config object with a ``logit_bias``
                            attribute (dict mapping phrase → bias).
        max_retries:        Maximum number of truncate-and-regenerate iterations.
        bias_amplification: Multiplier applied to bias values on each retry.

    Returns:
        ``(final_text, retries_used)`` tuple.
    """
    if not violations:
        return (text, 0)

    current_text = text
    current_violations = violations

    for attempt in range(max_retries):
        # Truncate at first violation
        truncation_point = current_violations[0].start
        truncated = current_text[:truncation_point]

        # Amplify logit bias
        if hasattr(config, "logit_bias") and config.logit_bias:
            amplified_bias = {
                phrase: bias * bias_amplification
                for phrase, bias in config.logit_bias.items()
            }
            config.logit_bias = amplified_bias

        # Regenerate
        prompt = base_prompt + truncated
        result = backend.generate(prompt, config)
        new_text = result.text if hasattr(result, "text") else str(result)

        # Re-check violations — use an empty banlist if config lacks one
        banlist_phrases: list[str] = (
            config.antislop_banlist if hasattr(config, "antislop_banlist") and config.antislop_banlist else []
        )
        severity_map: dict[str, float] = (
            config.antislop_severity if hasattr(config, "antislop_severity") and config.antislop_severity else {}
        )
        banlist_for_check = [
            BanEntry(phrase=p, kind="unknown", severity=severity_map.get(p, 1.0))
            for p in banlist_phrases
        ]
        new_violations = check_violations(new_text, banlist_for_check)

        current_text = new_text
        current_violations = new_violations

        if not current_violations:
            return (current_text, attempt + 1)

    return (current_text, max_retries)


# ---------------------------------------------------------------------------
# Batch observation recording
# ---------------------------------------------------------------------------


def record_batch_observation(
    db: Any,
    batch_id: str,
    card_texts: list[str],
    banlist: list[BanEntry],
    prior_corpus: str | list[str] | None = None,
) -> dict[str, Any]:
    """Compute and persist slop-quality metrics for a generation batch.

    Computes MTLD, 4-gram novelty, and slop fingerprint across all cards.
    Inserts a row into ``chronicle_slop_observations`` and returns the inserted
    dict.

    Schema columns written (see migration 20260524_03):
        batch_id, card_count, mtld_median, mtld_p25, mtld_p75,
        ngram_novelty_4gram, slop_fingerprint_score,
        banlist_top_offenders_json, em_dash_density_per_100w,
        flagged_for_review, created_at_utc

    Args:
        db:            Database accessor with ``query_all`` and optionally an
                       ``execute`` method for inserts.  If it only has
                       ``query_all``, the insert is skipped (test mode).
        batch_id:      Identifier string for the generation batch.
        card_texts:    List of generated card text strings.
        banlist:       Loaded banlist entries.
        prior_corpus:  Optional reference corpus for novelty computation.

    Returns:
        Dict with all computed fields (matches the DB row that was inserted).
    """
    if not card_texts:
        card_texts = []

    n = len(card_texts)

    # Per-card metrics
    mtld_values: list[float] = [compute_mtld(t) for t in card_texts]
    fp_values: list[float] = [score_slop_fingerprint(t, banlist) for t in card_texts]

    # Novelty — join all cards as corpus if no prior given
    corpus = prior_corpus if prior_corpus is not None else []
    novelty_values: list[float] = [
        compute_ngram_novelty(t, corpus, n=4) for t in card_texts
    ]

    # Aggregate
    mtld_median = statistics.median(mtld_values) if mtld_values else 0.0
    mtld_p25 = statistics.quantiles(mtld_values, n=4)[0] if len(mtld_values) >= 2 else (mtld_values[0] if mtld_values else 0.0)
    mtld_p75 = statistics.quantiles(mtld_values, n=4)[2] if len(mtld_values) >= 2 else (mtld_values[0] if mtld_values else 0.0)

    ngram_novelty = statistics.mean(novelty_values) if novelty_values else 1.0
    fp_score = statistics.mean(fp_values) if fp_values else 0.0

    # Em-dash density across all text
    all_text = " ".join(card_texts)
    all_words = _WORD_RE.findall(all_text)
    em_dash_count = len(_EM_DASH_RE.findall(all_text))
    em_dash_density = (em_dash_count / max(1, len(all_words))) * 100.0

    # Top offenders: phrases by total occurrence × severity across all cards
    offender_scores: dict[str, float] = {}
    for t in card_texts:
        for v in check_violations(t, banlist):
            offender_scores[v.phrase] = offender_scores.get(v.phrase, 0.0) + v.severity
    top_offenders = sorted(offender_scores, key=lambda p: offender_scores[p], reverse=True)[:10]

    flagged = fp_score > 0.5

    now_utc = datetime.now(timezone.utc).isoformat()

    row: dict[str, Any] = {
        "batch_id": batch_id,
        "card_count": n,
        "mtld_median": mtld_median,
        "mtld_p25": mtld_p25,
        "mtld_p75": mtld_p75,
        "ngram_novelty_4gram": ngram_novelty,
        "slop_fingerprint_score": fp_score,
        "banlist_top_offenders_json": json.dumps(top_offenders),
        "em_dash_density_per_100w": em_dash_density,
        "flagged_for_review": int(flagged),
        "created_at_utc": now_utc,
    }

    # Attempt insert — gracefully skip if the DB object doesn't support it
    # (e.g. test stubs that only implement query_all)
    _try_insert(db, "chronicle_slop_observations", row)

    return row


def _try_insert(db: Any, table: str, row: dict[str, Any]) -> None:
    """Best-effort INSERT into *table*.  Silent no-op if DB lacks execute support."""
    cols = ", ".join(row.keys())
    placeholders = ", ".join(f":{k}" for k in row.keys())
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    try:
        if hasattr(db, "execute"):
            db.execute(sql, row)
        elif hasattr(db, "query_all"):
            # Some DB wrappers route all SQL through query_all
            db.query_all(sql, row)
    except Exception as exc:  # noqa: BLE001
        log.debug("record_batch_observation: insert skipped (%s)", exc)
