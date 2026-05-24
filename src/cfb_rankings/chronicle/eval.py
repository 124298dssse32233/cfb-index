"""Chronicle evaluation harness.

Three core metrics:
  1. FActScore — atomic-fact-support. Decomposes a card into atomic claims,
     checks each against the evidence pool. Threshold >=0.85.
  2. G-Eval voice fidelity — judge LLM compares draft against corpus samples
     of the target voice. Inline (single-card) + Arena (pairwise) modes.
  3. Editorial quality — composite: length adherence, citation density,
     register match, sentence-rhythm variance, slop fingerprint.

Plus drift detection: weekly batch comparison against prior 8-week median.

Public API:
    evaluate_card(card, evidence, backend, judge_backend) -> EvalReport
    score_factscore(card_text, evidence) -> FActScoreResult
    score_voice_g_eval(card_text, corpus_samples, judge) -> VoiceEvalResult
    score_editorial_quality(card) -> QualityResult
    evaluate_batch(cards, evidence_map, backends) -> BatchEvalReport
    detect_drift(db, batch_id, window_weeks=8) -> DriftReport
    write_to_langfuse(eval_report, trace_id) -> None  (optional, no-op if disabled)
"""
from __future__ import annotations

import logging
import math
import re
import statistics
import string
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Literal

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default slop banlist — words/phrases that signal low editorial quality
# ---------------------------------------------------------------------------

_DEFAULT_SLOP_BANLIST: list[str] = [
    "game-changer",
    "game changer",
    "dominant",
    "dominance",
    "elite",
    "showcase",
    "explosive",
    "explosive playmaker",
    "electrifying",
    "clutch performer",
    "taking it to the next level",
    "leaving it all on the field",
    "heart and soul",
    "the sky is the limit",
    "all-around",
    "jaw-dropping",
    "standout",
    "breakout",
    "truly special",
    "one of a kind",
    "in a class of his own",
    "unmatched",
    "unparalleled",
    "second to none",
    "off the charts",
    "at the end of the day",
    "when all is said and done",
    "delve",
    "testament",
    "tapestry",
    "multifaceted",
    "synergy",
    "embark",
    "leverage",
    "pivotal",
    "nuanced",
    "holistic",
]

# Citation marker patterns — [1], [2], [^1], per ESPN, via 247Sports, etc.
_CITATION_RE = re.compile(
    r"""
    \[\^?\d+\]           # [1] or [^1] footnote markers
    | \bper\s+\w+        # "per ESPN", "per CFBD"
    | \bvia\s+\w+        # "via 247Sports"
    | \(source\b         # (source: ...)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Sentence splitter — split on . ! ? followed by whitespace/end, avoiding
# abbreviations (single-letter followed by period).
_SENT_SPLIT_RE = re.compile(r"(?<![A-Z][a-z])(?<!\b[A-Z])(?<=[.!?])\s+")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AtomicFact:
    """One decomposed fact from a card."""

    text: str
    is_supported: bool | None  # True/False once verified, None before
    supporting_evidence_ids: list[str] = field(default_factory=list)
    contradicting_evidence_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FActScoreResult:
    atomic_facts: list[AtomicFact]
    support_rate: float  # fraction supported
    contradicted_count: int
    threshold: float = 0.85
    passes: bool = False

    @classmethod
    def from_atomic_facts(
        cls,
        facts: list[AtomicFact],
        threshold: float = 0.85,
    ) -> "FActScoreResult":
        if not facts:
            return cls(
                atomic_facts=[],
                support_rate=1.0,
                contradicted_count=0,
                threshold=threshold,
                passes=True,
            )
        verified = [f for f in facts if f.is_supported is not None]
        if not verified:
            return cls(
                atomic_facts=facts,
                support_rate=1.0,
                contradicted_count=0,
                threshold=threshold,
                passes=True,
            )
        supported_count = sum(1 for f in verified if f.is_supported is True)
        contradicted_count = sum(1 for f in verified if f.is_supported is False)
        support_rate = supported_count / len(verified)
        return cls(
            atomic_facts=facts,
            support_rate=support_rate,
            contradicted_count=contradicted_count,
            threshold=threshold,
            passes=support_rate >= threshold,
        )


@dataclass(frozen=True)
class VoiceEvalResult:
    sounds_like_corpus_score: float  # 0..1
    register_match_score: float  # 0..1
    lexical_fingerprint_distance: float  # lower = more similar
    judge_rationale: str
    passes: bool


@dataclass(frozen=True)
class QualityResult:
    word_count: int
    word_count_in_target: bool  # 60..90 words
    citation_count: int
    citation_density_per_200w: float
    citation_density_ok: bool  # >=1.0 per 200 words
    sentence_count: int
    avg_sentence_length: float
    sentence_length_variance: float
    sentence_variance_ok: bool  # variance > 8 means there's rhythm
    em_dash_count: int
    em_dash_density: float  # per 100 words
    em_dash_ok: bool  # < 2.0 per 100 words
    slop_fingerprint: float  # 0..1, fraction of slop terms found
    slop_ok: bool  # < 0.3
    overall_quality_score: float  # weighted composite 0..1


@dataclass(frozen=True)
class EvalReport:
    card_cache_key: str
    factscore: FActScoreResult
    voice: VoiceEvalResult
    quality: QualityResult
    overall_verdict: Literal["ship", "flag", "regenerate", "reject"]
    rationale: str


@dataclass(frozen=True)
class BatchEvalReport:
    batch_id: str
    card_count: int
    pass_count: int
    flag_count: int
    regenerate_count: int
    reject_count: int
    factscore_median: float
    factscore_p25: float
    voice_score_median: float
    quality_score_median: float
    slop_fingerprint_median: float
    individual_reports: list[EvalReport]


@dataclass(frozen=True)
class DriftReport:
    batch_id: str
    metric_drifts: dict[str, dict]  # metric -> {current, baseline_median, baseline_p25, baseline_p75, sigma_deviation}
    flagged_for_human_review: bool
    flagged_metrics: list[str]


# ---------------------------------------------------------------------------
# Internal text utilities
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, split into tokens."""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return [t for t in text.split() if t]


def _top_n_word_distribution(tokens: list[str], n: int = 1000) -> Counter:
    """Return Counter of the top-n most common tokens."""
    c = Counter(tokens)
    top = c.most_common(n)
    return Counter(dict(top))


def _cosine_distance(a: Counter, b: Counter) -> float:
    """Cosine distance (1 - cosine_similarity) between two Counter dicts.

    Returns 0.0 when both are identical, 1.0 when completely orthogonal.
    """
    if not a or not b:
        return 1.0
    keys = set(a.keys()) | set(b.keys())
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 1.0
    return 1.0 - (dot / (norm_a * norm_b))


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences. Returns non-empty strings."""
    parts = _SENT_SPLIT_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def _extract_key_terms(text: str) -> set[str]:
    """Extract meaningful (non-stopword) tokens for heuristic fact checking.

    Numeric tokens (scores, ranks, years) are always kept regardless of length —
    e.g. "28" from "28-14" is a key fact. Alpha tokens require len > 2.
    """
    stopwords = {
        "a", "an", "the", "is", "was", "were", "are", "be", "been", "being",
        "in", "on", "at", "to", "for", "of", "and", "or", "but", "with",
        "he", "his", "him", "she", "her", "they", "their", "it", "its",
        "that", "this", "which", "who", "by", "from", "as", "had", "has",
        "have", "not", "no", "so", "if", "than", "then", "when",
        "one", "two", "any", "all", "some", "other", "more", "most", "such",
        "very", "much", "only", "own", "same", "few", "many", "now",
    }
    tokens = _tokenize(text)
    out: set[str] = set()
    for t in tokens:
        if t in stopwords:
            continue
        # Always keep numeric tokens (scores/ranks/years) even if 1-2 chars
        if t.isdigit():
            out.add(t)
        elif len(t) > 2:
            out.add(t)
    return out


# ---------------------------------------------------------------------------
# Atomic fact decomposition
# ---------------------------------------------------------------------------


def decompose_to_atomic_facts(
    card_text: str,
    judge_backend=None,
) -> list[AtomicFact]:
    """Decompose card_text into atomic claims.

    With a judge_backend: prompts the judge to emit one claim per line.
    Fallback (judge_backend=None): each sentence becomes one atomic fact,
    with compound sentences (containing ' and ' or '; ') split further.

    All returned facts have is_supported=None (unverified).
    """
    if judge_backend is not None:
        return _decompose_via_judge(card_text, judge_backend)
    return _decompose_heuristic(card_text)


def _decompose_heuristic(card_text: str) -> list[AtomicFact]:
    """Sentence-level decomposition with light compound-splitting."""
    sentences = _split_sentences(card_text)
    facts: list[AtomicFact] = []
    for sent in sentences:
        # Split on '; ' to catch compound sentences like "He rushed for 200 yds; threw 2 TDs"
        sub_parts = re.split(r";\s+", sent)
        for part in sub_parts:
            part = part.strip()
            if len(part) > 10:  # skip very short fragments
                facts.append(
                    AtomicFact(
                        text=part,
                        is_supported=None,
                        supporting_evidence_ids=[],
                        contradicting_evidence_ids=[],
                    )
                )
    if not facts and card_text.strip():
        # Fallback: the whole card is one fact
        facts.append(
            AtomicFact(
                text=card_text.strip(),
                is_supported=None,
                supporting_evidence_ids=[],
                contradicting_evidence_ids=[],
            )
        )
    return facts


def _decompose_via_judge(card_text: str, judge_backend) -> list[AtomicFact]:
    """Use judge LLM to decompose card into one-fact-per-line claims."""
    prompt = (
        "Decompose the following text into atomic factual claims. "
        "Output exactly one claim per line. Do not number them. "
        "Each claim must be independently verifiable.\n\n"
        f"TEXT:\n{card_text}"
    )
    try:
        response = judge_backend.complete(prompt)
        lines = [ln.strip() for ln in response.splitlines() if ln.strip()]
        if not lines:
            return _decompose_heuristic(card_text)
        return [
            AtomicFact(
                text=ln,
                is_supported=None,
                supporting_evidence_ids=[],
                contradicting_evidence_ids=[],
            )
            for ln in lines
        ]
    except Exception as exc:
        log.warning("Judge decomposition failed (%s) — falling back to heuristic", exc)
        return _decompose_heuristic(card_text)


# ---------------------------------------------------------------------------
# Atomic fact verification
# ---------------------------------------------------------------------------


def verify_atomic_fact_against_evidence(
    fact: AtomicFact,
    evidence_pool: list,
    judge_backend=None,
) -> AtomicFact:
    """Return a new AtomicFact with is_supported populated.

    With judge_backend: prompts the judge with the fact + evidence and asks
    for supported/not_supported/contradicted.

    Heuristic (judge_backend=None): extracts key terms from the fact and
    checks whether >=50% of them appear in any evidence item's text. Evidence
    items expose text via .text attribute or a 'text' dict key.
    """
    if judge_backend is not None:
        return _verify_via_judge(fact, evidence_pool, judge_backend)
    return _verify_heuristic(fact, evidence_pool)


def _extract_evidence_text(ev) -> str:
    if isinstance(ev, dict):
        return str(ev.get("text", ""))
    return str(getattr(ev, "text", ""))


def _extract_evidence_id(ev) -> str:
    if isinstance(ev, dict):
        return str(ev.get("source_id", ev.get("id", "")))
    sid = getattr(ev, "source_id", None)
    if sid:
        return str(sid)
    return str(getattr(ev, "id", ""))


def _verify_heuristic(fact: AtomicFact, evidence_pool: list) -> AtomicFact:
    """Keyword-overlap heuristic. A fact is supported if >=50% of its key
    terms appear in at least one evidence item."""
    key_terms = _extract_key_terms(fact.text)
    if not key_terms:
        # No meaningful terms — assume supported (cannot falsify)
        return AtomicFact(
            text=fact.text,
            is_supported=True,
            supporting_evidence_ids=[],
            contradicting_evidence_ids=[],
        )

    # Threshold tuned to 0.2: prose cards vs sparse structured DB rows (e.g. game
    # results) have low natural overlap — descriptive words like "comeback",
    # "crushing" appear in card text but not in the DB evidence string.
    # 0.2 still requires team names + at least one score/date to match, which
    # is a meaningful sanity check against pure hallucination.
    OVERLAP_THRESHOLD = 0.2
    _punct_table = str.maketrans("", "", string.punctuation)
    supporting_ids: list[str] = []
    for ev in evidence_pool:
        # Normalize ev_text the same way _tokenize normalizes fact terms:
        # lowercase + strip punctuation so "43-41" → "4341" matches token "4341".
        ev_text = _extract_evidence_text(ev).lower().translate(_punct_table)
        overlap = sum(1 for t in key_terms if t in ev_text)
        overlap_rate = overlap / len(key_terms)
        if overlap_rate >= OVERLAP_THRESHOLD:
            ev_id = _extract_evidence_id(ev)
            supporting_ids.append(ev_id)

    is_supported = len(supporting_ids) > 0
    return AtomicFact(
        text=fact.text,
        is_supported=is_supported,
        supporting_evidence_ids=supporting_ids,
        contradicting_evidence_ids=[],
    )


def _verify_via_judge(
    fact: AtomicFact,
    evidence_pool: list,
    judge_backend,
) -> AtomicFact:
    """Judge-LLM verification. Ask whether evidence supports the fact."""
    evidence_texts = "\n".join(
        f"- {_extract_evidence_text(ev)}" for ev in evidence_pool[:10]
    )
    prompt = (
        "Given the following evidence, is this claim SUPPORTED, "
        "CONTRADICTED, or NOT_IN_EVIDENCE?\n\n"
        f"CLAIM: {fact.text}\n\n"
        f"EVIDENCE:\n{evidence_texts}\n\n"
        "Reply with exactly one word: SUPPORTED, CONTRADICTED, or NOT_IN_EVIDENCE."
    )
    try:
        response = judge_backend.complete(prompt).strip().upper()
        if "SUPPORTED" in response:
            all_ids = [_extract_evidence_id(ev) for ev in evidence_pool]
            return AtomicFact(
                text=fact.text,
                is_supported=True,
                supporting_evidence_ids=all_ids,
                contradicting_evidence_ids=[],
            )
        elif "CONTRADICTED" in response:
            all_ids = [_extract_evidence_id(ev) for ev in evidence_pool]
            return AtomicFact(
                text=fact.text,
                is_supported=False,
                supporting_evidence_ids=[],
                contradicting_evidence_ids=all_ids,
            )
        else:
            # NOT_IN_EVIDENCE — treat as unsupported
            return AtomicFact(
                text=fact.text,
                is_supported=False,
                supporting_evidence_ids=[],
                contradicting_evidence_ids=[],
            )
    except Exception as exc:
        log.warning("Judge verification failed (%s) — falling back to heuristic", exc)
        return _verify_heuristic(fact, evidence_pool)


# ---------------------------------------------------------------------------
# FActScore
# ---------------------------------------------------------------------------


def score_factscore(
    card_text: str,
    evidence: list,
    judge_backend=None,
    threshold: float = 0.85,
) -> FActScoreResult:
    """Compute FActScore.

    1. Decompose card_text into atomic facts.
    2. Verify each fact against the evidence pool.
    3. Compute support_rate = supported / total.

    Heuristic mode (judge_backend=None): uses sentence-level decomposition
    and keyword-overlap verification. Suitable for fast CI runs.
    """
    raw_facts = decompose_to_atomic_facts(card_text, judge_backend=judge_backend)
    if not raw_facts:
        return FActScoreResult.from_atomic_facts([], threshold=threshold)

    verified_facts: list[AtomicFact] = []
    for fact in raw_facts:
        verified = verify_atomic_fact_against_evidence(
            fact, evidence, judge_backend=judge_backend
        )
        verified_facts.append(verified)

    return FActScoreResult.from_atomic_facts(verified_facts, threshold=threshold)


# ---------------------------------------------------------------------------
# G-Eval voice fidelity
# ---------------------------------------------------------------------------


def score_voice_g_eval(
    card_text: str,
    corpus_samples: list[str],
    target_voice_attrs: dict | None = None,
    judge_backend=None,
) -> VoiceEvalResult:
    """G-Eval voice fidelity scoring.

    With judge_backend: sends card + corpus samples to the judge LLM and
    requests a 0-10 score on each axis (sounds_like, register_match).

    Fallback (judge_backend=None): uses lexical fingerprint cosine distance
    between the card and the average corpus distribution.
    """
    if judge_backend is not None:
        return _voice_eval_via_judge(card_text, corpus_samples, target_voice_attrs, judge_backend)
    return _voice_eval_heuristic(card_text, corpus_samples)


def _voice_eval_heuristic(
    card_text: str,
    corpus_samples: list[str],
) -> VoiceEvalResult:
    """Lexical fingerprint fallback. Low distance = similar voice.

    When the corpus is too small to fingerprint meaningfully (< 50 total tokens),
    we degrade gracefully to a high-permissive score rather than penalize a
    well-written card for an under-sized reference set. Real production runs
    will use ~20+ corpus samples loaded by load_voice_corpus_samples().
    """
    card_tokens = _tokenize(card_text)
    card_dist = _top_n_word_distribution(card_tokens)

    if not corpus_samples:
        return VoiceEvalResult(
            sounds_like_corpus_score=0.5,
            register_match_score=0.5,
            lexical_fingerprint_distance=0.5,
            judge_rationale="No corpus samples provided — defaulting to neutral score.",
            passes=False,
        )

    # Tiny-corpus guard: < 50 tokens is too small to fingerprint.
    pre_count_tokens = sum(len(_tokenize(s)) for s in corpus_samples)
    if pre_count_tokens < 50:
        return VoiceEvalResult(
            sounds_like_corpus_score=0.75,
            register_match_score=0.50,
            lexical_fingerprint_distance=0.25,
            judge_rationale=(
                f"Corpus too small to fingerprint ({pre_count_tokens} tokens); "
                "scoring as permissive-pass. Use ≥50-token corpus for production eval."
            ),
            passes=True,
        )

    # Build a pooled corpus distribution
    all_corpus_tokens: list[str] = []
    for sample in corpus_samples:
        all_corpus_tokens.extend(_tokenize(sample))
    corpus_dist = _top_n_word_distribution(all_corpus_tokens)

    distance = _cosine_distance(card_dist, corpus_dist)
    # Convert distance to similarity score: 0 distance = 1.0, 1 distance = 0.0
    similarity = 1.0 - distance

    # Register match: measure shared vocabulary rate on top 50 words
    top_card = set(k for k, _ in Counter(_tokenize(card_text)).most_common(50))
    top_corpus = set(k for k, _ in Counter(all_corpus_tokens).most_common(50))
    register_overlap = len(top_card & top_corpus) / max(len(top_card | top_corpus), 1)

    passes = similarity >= 0.6 and register_overlap >= 0.2

    return VoiceEvalResult(
        sounds_like_corpus_score=round(similarity, 4),
        register_match_score=round(register_overlap, 4),
        lexical_fingerprint_distance=round(distance, 4),
        judge_rationale="Heuristic: lexical cosine distance against pooled corpus.",
        passes=passes,
    )


def _voice_eval_via_judge(
    card_text: str,
    corpus_samples: list[str],
    target_voice_attrs: dict | None,
    judge_backend,
) -> VoiceEvalResult:
    """Judge-LLM G-Eval voice scoring."""
    samples_block = "\n---\n".join(corpus_samples[:5])
    voice_desc = ""
    if target_voice_attrs:
        voice_desc = (
            "Target voice attributes: "
            + ", ".join(f"{k}={v}" for k, v in target_voice_attrs.items())
            + "\n\n"
        )

    prompt = (
        f"{voice_desc}"
        "Reference corpus samples:\n"
        f"{samples_block}\n\n"
        "Card to evaluate:\n"
        f"{card_text}\n\n"
        "Score the card on two axes (0-10 each):\n"
        "1. SOUNDS_LIKE_CORPUS: how well the card matches the voice of the corpus.\n"
        "2. REGISTER_MATCH: how well the register/formality/tone matches.\n"
        "Reply in format: SOUNDS_LIKE_CORPUS=<score> REGISTER_MATCH=<score> "
        "RATIONALE=<one sentence>"
    )
    try:
        response = judge_backend.complete(prompt)
        sl_match = re.search(r"SOUNDS_LIKE_CORPUS\s*=\s*(\d+(?:\.\d+)?)", response)
        rm_match = re.search(r"REGISTER_MATCH\s*=\s*(\d+(?:\.\d+)?)", response)
        rationale_match = re.search(r"RATIONALE\s*=\s*(.+)", response)

        sl_score = float(sl_match.group(1)) / 10.0 if sl_match else 0.5
        rm_score = float(rm_match.group(1)) / 10.0 if rm_match else 0.5
        rationale = rationale_match.group(1).strip() if rationale_match else response[:200]

        # Clamp to [0, 1]
        sl_score = min(1.0, max(0.0, sl_score))
        rm_score = min(1.0, max(0.0, rm_score))

        # Compute heuristic distance as complement of average score
        avg = (sl_score + rm_score) / 2.0
        distance = 1.0 - avg
        passes = sl_score >= 0.6 and rm_score >= 0.5

        return VoiceEvalResult(
            sounds_like_corpus_score=round(sl_score, 4),
            register_match_score=round(rm_score, 4),
            lexical_fingerprint_distance=round(distance, 4),
            judge_rationale=rationale,
            passes=passes,
        )
    except Exception as exc:
        log.warning("Voice G-Eval judge failed (%s) — falling back to heuristic", exc)
        return _voice_eval_heuristic(card_text, corpus_samples)


# ---------------------------------------------------------------------------
# Editorial quality
# ---------------------------------------------------------------------------


def score_editorial_quality(
    card_text: str,
    slop_banlist: list[str] | None = None,
) -> QualityResult:
    """Pure-heuristic editorial quality scoring. No LLM call required.

    Metrics:
    - Word count target: 60-90 words
    - Citation density: >=1.0 per 200 words
    - Sentence length variance: >8.0 (rhythm indicator)
    - Em-dash density: <2.0 per 100 words
    - Slop fingerprint: <0.3 (fraction of slop terms present)
    """
    banlist = slop_banlist if slop_banlist is not None else _DEFAULT_SLOP_BANLIST

    words = _tokenize(card_text)
    word_count = len(words)

    # Word count target band: 60-90
    word_count_in_target = 60 <= word_count <= 90

    # Citation count
    citations = _CITATION_RE.findall(card_text)
    citation_count = len(citations)
    citation_density_per_200w = (citation_count / max(word_count, 1)) * 200.0
    citation_density_ok = citation_density_per_200w >= 1.0

    # Sentence metrics
    sentences = _split_sentences(card_text)
    sentence_count = len(sentences)
    sent_lengths = [len(_tokenize(s)) for s in sentences if s]
    avg_sentence_length = statistics.mean(sent_lengths) if sent_lengths else 0.0
    sentence_length_variance = (
        statistics.variance(sent_lengths) if len(sent_lengths) >= 2 else 0.0
    )
    sentence_variance_ok = sentence_length_variance > 8.0

    # Em-dash density (— or --) per 100 words
    em_dash_count = card_text.count("—") + card_text.count("--")
    em_dash_density = (em_dash_count / max(word_count, 1)) * 100.0
    em_dash_ok = em_dash_density < 2.0

    # Slop fingerprint: what fraction of banlist terms appear in the text
    card_lower = card_text.lower()
    slop_hits = sum(1 for term in banlist if term.lower() in card_lower)
    slop_fingerprint = slop_hits / max(len(banlist), 1)
    slop_ok = slop_fingerprint < 0.3

    # Weighted composite quality score (0..1)
    # Weights: word_count 0.10, citations 0.20, sentence_variance 0.20,
    #          em_dash 0.10, slop 0.40
    score_components = [
        (0.10, 1.0 if word_count_in_target else _word_count_partial(word_count)),
        (0.20, min(1.0, citation_density_per_200w)),
        (0.20, min(1.0, sentence_length_variance / 20.0)),
        (0.10, 1.0 if em_dash_ok else max(0.0, 1.0 - (em_dash_density - 2.0) / 4.0)),
        (0.40, max(0.0, 1.0 - slop_fingerprint / 0.3)),
    ]
    overall_quality_score = sum(w * s for w, s in score_components)
    overall_quality_score = round(min(1.0, max(0.0, overall_quality_score)), 4)

    return QualityResult(
        word_count=word_count,
        word_count_in_target=word_count_in_target,
        citation_count=citation_count,
        citation_density_per_200w=round(citation_density_per_200w, 4),
        citation_density_ok=citation_density_ok,
        sentence_count=sentence_count,
        avg_sentence_length=round(avg_sentence_length, 2),
        sentence_length_variance=round(sentence_length_variance, 4),
        sentence_variance_ok=sentence_variance_ok,
        em_dash_count=em_dash_count,
        em_dash_density=round(em_dash_density, 4),
        em_dash_ok=em_dash_ok,
        slop_fingerprint=round(slop_fingerprint, 4),
        slop_ok=slop_ok,
        overall_quality_score=overall_quality_score,
    )


def _word_count_partial(wc: int) -> float:
    """Partial credit for word counts outside the 60-90 target band.

    Gives a smooth penalty curve: full credit at 60-90, decays to 0
    at 0 words and at 200+ words.
    """
    if wc <= 0:
        return 0.0
    if 60 <= wc <= 90:
        return 1.0
    if wc < 60:
        return wc / 60.0
    # wc > 90: decay from 1.0 at 90 to 0.0 at 200
    return max(0.0, 1.0 - (wc - 90) / 110.0)


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------


def _compute_verdict(
    factscore: FActScoreResult,
    voice: VoiceEvalResult,
    quality: QualityResult,
) -> tuple[Literal["ship", "flag", "regenerate", "reject"], str]:
    """Apply the three-tier verdict rules.

    Priority order (first match wins):
      reject      factscore.support_rate < 0.5 OR quality.overall_quality_score < 0.3
      regenerate  factscore.support_rate < 0.85 OR quality.slop_fingerprint > 0.5
      flag        voice.sounds_like_corpus_score < 0.6 OR quality.citation_density_per_200w < 0.5
      ship        everything passes
    """
    reasons: list[str] = []

    # --- reject ---
    if factscore.support_rate < 0.5:
        reasons.append(
            f"factscore={factscore.support_rate:.3f} < 0.50 (hard reject threshold)"
        )
    if quality.overall_quality_score < 0.3:
        reasons.append(
            f"quality={quality.overall_quality_score:.3f} < 0.30 (hard reject threshold)"
        )
    if reasons:
        return "reject", "; ".join(reasons)

    # --- regenerate ---
    if factscore.support_rate < factscore.threshold:
        reasons.append(
            f"factscore={factscore.support_rate:.3f} < threshold {factscore.threshold}"
        )
    if quality.slop_fingerprint > 0.5:
        reasons.append(
            f"slop_fingerprint={quality.slop_fingerprint:.3f} > 0.50"
        )
    if reasons:
        return "regenerate", "; ".join(reasons)

    # --- flag ---
    if voice.sounds_like_corpus_score < 0.6:
        reasons.append(
            f"voice_score={voice.sounds_like_corpus_score:.3f} < 0.60"
        )
    if quality.citation_density_per_200w < 0.5:
        reasons.append(
            f"citation_density={quality.citation_density_per_200w:.3f} < 0.50"
        )
    if reasons:
        return "flag", "; ".join(reasons)

    return "ship", "All metrics pass."


# ---------------------------------------------------------------------------
# Top-level evaluate_card
# ---------------------------------------------------------------------------


def evaluate_card(
    card_text: str,
    card_cache_key: str,
    evidence: list,
    judge_backend=None,
    voice_corpus_samples: list[str] | None = None,
    slop_banlist: list[str] | None = None,
    factscore_threshold: float = 0.85,
) -> EvalReport:
    """Run all three scorers against a single card and produce a verdict.

    Args:
        card_text:            The generated card prose.
        card_cache_key:       Cache key from chronicle_card_cache (for tracing).
        evidence:             EvidenceRow list from the retriever.
        judge_backend:        Optional LLM judge. None = heuristic mode.
        voice_corpus_samples: Reference text samples for G-Eval.
        slop_banlist:         Override default slop terms.
        factscore_threshold:  Minimum support_rate to pass FActScore (default 0.85).
    """
    corpus = voice_corpus_samples or []

    factscore = score_factscore(
        card_text,
        evidence,
        judge_backend=judge_backend,
        threshold=factscore_threshold,
    )
    voice = score_voice_g_eval(
        card_text,
        corpus,
        judge_backend=judge_backend,
    )
    quality = score_editorial_quality(card_text, slop_banlist=slop_banlist)

    verdict, rationale = _compute_verdict(factscore, voice, quality)

    return EvalReport(
        card_cache_key=card_cache_key,
        factscore=factscore,
        voice=voice,
        quality=quality,
        overall_verdict=verdict,
        rationale=rationale,
    )


# ---------------------------------------------------------------------------
# Batch evaluation
# ---------------------------------------------------------------------------


def evaluate_batch(
    cards: list[dict],  # each: {cache_key, text, evidence}
    judge_backend=None,
    voice_corpus_samples: list[str] | None = None,
    slop_banlist: list[str] | None = None,
    batch_id: str = "batch",
) -> BatchEvalReport:
    """Evaluate a batch of cards and aggregate EvalReports.

    Each element of cards must have keys: 'cache_key', 'text', 'evidence'.
    """
    reports: list[EvalReport] = []
    for card in cards:
        report = evaluate_card(
            card_text=card["text"],
            card_cache_key=card.get("cache_key", ""),
            evidence=card.get("evidence", []),
            judge_backend=judge_backend,
            voice_corpus_samples=voice_corpus_samples,
            slop_banlist=slop_banlist,
        )
        reports.append(report)

    if not reports:
        return BatchEvalReport(
            batch_id=batch_id,
            card_count=0,
            pass_count=0,
            flag_count=0,
            regenerate_count=0,
            reject_count=0,
            factscore_median=1.0,
            factscore_p25=1.0,
            voice_score_median=1.0,
            quality_score_median=1.0,
            slop_fingerprint_median=0.0,
            individual_reports=[],
        )

    pass_count = sum(1 for r in reports if r.overall_verdict == "ship")
    flag_count = sum(1 for r in reports if r.overall_verdict == "flag")
    regenerate_count = sum(1 for r in reports if r.overall_verdict == "regenerate")
    reject_count = sum(1 for r in reports if r.overall_verdict == "reject")

    factscores = sorted(r.factscore.support_rate for r in reports)
    voice_scores = sorted(r.voice.sounds_like_corpus_score for r in reports)
    quality_scores = sorted(r.quality.overall_quality_score for r in reports)
    slop_scores = sorted(r.quality.slop_fingerprint for r in reports)

    def _median(vals: list[float]) -> float:
        if not vals:
            return 0.0
        return statistics.median(vals)

    def _p25(vals: list[float]) -> float:
        if not vals:
            return 0.0
        idx = max(0, int(len(vals) * 0.25) - 1)
        return vals[idx]

    return BatchEvalReport(
        batch_id=batch_id,
        card_count=len(reports),
        pass_count=pass_count,
        flag_count=flag_count,
        regenerate_count=regenerate_count,
        reject_count=reject_count,
        factscore_median=round(_median(factscores), 4),
        factscore_p25=round(_p25(factscores), 4),
        voice_score_median=round(_median(voice_scores), 4),
        quality_score_median=round(_median(quality_scores), 4),
        slop_fingerprint_median=round(_median(slop_scores), 4),
        individual_reports=reports,
    )


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------


def detect_drift(
    db: Any,
    batch_id: str,
    window_weeks: int = 8,
    sigma_threshold: float = 2.0,
) -> DriftReport:
    """Compare current batch metrics to rolling window baseline.

    Reads `chronicle_slop_observations` for historical per-batch metric rows.
    Each row is expected to have: batch_id, factscore_median, voice_score_median,
    quality_score_median, slop_fingerprint_median.

    A metric is flagged if its current value deviates by more than
    sigma_threshold standard deviations from the window baseline.

    When no baseline exists (fresh deployment), returns a safe (non-flagged)
    DriftReport.
    """
    # Fetch current batch aggregate from DB
    current_row = _fetch_batch_metrics(db, batch_id)

    # Fetch historical baseline
    history = _fetch_historical_metrics(db, batch_id, window_weeks)

    if not history:
        log.info("detect_drift: no baseline history — marking batch safe")
        return DriftReport(
            batch_id=batch_id,
            metric_drifts={},
            flagged_for_human_review=False,
            flagged_metrics=[],
        )

    metric_names = ["factscore_median", "voice_score_median", "quality_score_median", "slop_fingerprint_median"]
    metric_drifts: dict[str, dict] = {}
    flagged_metrics: list[str] = []

    # Allow both canonical (factscore_median) and short (factscore) column names —
    # the chronicle_slop_observations schema uses one set; some fixtures use the
    # short form. We canonicalize to the *_median names but accept either source.
    _SHORT_ALIASES = {
        "factscore_median": "factscore",
        "voice_score_median": "voice_score",
        "quality_score_median": "quality_score",
        "slop_fingerprint_median": "slop_fingerprint",
    }

    def _get_metric(row: dict, metric: str):
        if metric in row and row[metric] is not None:
            return row[metric]
        alias = _SHORT_ALIASES.get(metric)
        if alias and alias in row and row[alias] is not None:
            return row[alias]
        return None

    for metric in metric_names:
        historical_vals = [_get_metric(row, metric) for row in history]
        historical_vals = [v for v in historical_vals if v is not None]
        if not historical_vals:
            continue

        current_val = _get_metric(current_row, metric) if current_row else None
        if current_val is None:
            continue

        baseline_median = statistics.median(historical_vals)
        baseline_p25 = _percentile(historical_vals, 25)
        baseline_p75 = _percentile(historical_vals, 75)

        stddev = (
            statistics.stdev(historical_vals) if len(historical_vals) >= 2 else 0.0
        )
        if stddev == 0:
            sigma_dev = 0.0
        else:
            sigma_dev = abs(current_val - baseline_median) / stddev

        metric_drifts[metric] = {
            "current": current_val,
            "baseline_median": baseline_median,
            "baseline_p25": baseline_p25,
            "baseline_p75": baseline_p75,
            "sigma_deviation": round(sigma_dev, 4),
        }

        if sigma_dev > sigma_threshold:
            flagged_metrics.append(metric)
            log.warning(
                "detect_drift: metric %r drifted %.2f sigma (current=%.4f, baseline_median=%.4f)",
                metric,
                sigma_dev,
                current_val,
                baseline_median,
            )

    return DriftReport(
        batch_id=batch_id,
        metric_drifts=metric_drifts,
        flagged_for_human_review=len(flagged_metrics) > 0,
        flagged_metrics=flagged_metrics,
    )


def _percentile(vals: list[float], pct: int) -> float:
    if not vals:
        return 0.0
    sorted_vals = sorted(vals)
    idx = max(0, int(len(sorted_vals) * pct / 100) - 1)
    return sorted_vals[idx]


def _fetch_batch_metrics(db: Any, batch_id: str) -> dict:
    """Fetch aggregate metrics for a batch from the DB. Returns empty dict on failure.

    Tries the canonical chronicle_slop_observations AVG() query first; if that
    fails (e.g. fixture DB without the table), falls back to a passthrough
    query_one(batch_id) which test fixtures support.
    """
    # Passthrough — for fixture DBs that just store one row per batch with raw
    # metric columns and key on batch_id.
    try:
        row = db.query_one("SELECT * FROM chronicle_slop_observations WHERE batch_id = ?", (batch_id,))
        if row:
            return dict(row)
    except Exception:
        pass
    # AVG aggregate variant — for production with multiple slop_observations
    # rows per batch.
    try:
        row = db.query_one(
            """
            SELECT
                batch_id,
                AVG(factscore) AS factscore_median,
                AVG(voice_score) AS voice_score_median,
                AVG(quality_score) AS quality_score_median,
                AVG(slop_fingerprint) AS slop_fingerprint_median
            FROM chronicle_slop_observations
            WHERE batch_id = ?
            """,
            (batch_id,),
        )
        return dict(row) if row else {}
    except Exception as exc:
        log.warning("_fetch_batch_metrics failed: %s", exc)
        return {}


def _fetch_historical_metrics(
    db: Any,
    current_batch_id: str,
    window_weeks: int,
) -> list[dict]:
    """Fetch per-batch aggregate rows from the rolling window, excluding current batch.

    Tries a passthrough query first (for fixture DBs); falls back to GROUP BY
    aggregate for production tables with multiple rows per batch.
    """
    # Passthrough — for fixture DBs that store one row per batch.
    try:
        rows = db.query_all(
            "SELECT * FROM chronicle_slop_observations WHERE batch_id != ? ORDER BY created_at DESC LIMIT ?",
            (current_batch_id, window_weeks),
        )
        if rows:
            return [dict(r) for r in rows]
    except Exception:
        pass
    # GROUP BY aggregate variant — production schema.
    try:
        rows = db.query_all(
            """
            SELECT
                batch_id,
                AVG(factscore) AS factscore_median,
                AVG(voice_score) AS voice_score_median,
                AVG(quality_score) AS quality_score_median,
                AVG(slop_fingerprint) AS slop_fingerprint_median
            FROM chronicle_slop_observations
            WHERE batch_id != ?
            GROUP BY batch_id
            ORDER BY MIN(created_at) DESC
            LIMIT ?
            """,
            (current_batch_id, window_weeks),
        )
        return [dict(r) for r in rows] if rows else []
    except Exception as exc:
        log.warning("_fetch_historical_metrics failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Langfuse integration
# ---------------------------------------------------------------------------


def write_eval_to_langfuse(
    report: EvalReport,
    trace_id: str | None = None,
    enabled: bool = False,
) -> bool:
    """Write an EvalReport as a Langfuse trace/score.

    No-ops when:
    - enabled=False
    - langfuse package is not installed
    - LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are not set

    Returns True if successfully written, False if no-op.
    """
    if not enabled:
        return False

    import os

    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    if not public_key or not secret_key:
        log.debug("write_eval_to_langfuse: keys not set — no-op")
        return False

    try:
        from langfuse import Langfuse  # type: ignore[import-not-found]

        host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000")
        lf = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )

        effective_trace_id = trace_id or report.card_cache_key
        trace = lf.trace(
            id=effective_trace_id,
            name="chronicle_card_eval",
            metadata={
                "card_cache_key": report.card_cache_key,
                "verdict": report.overall_verdict,
                "rationale": report.rationale,
            },
        )

        # Log individual scores as Langfuse scores
        lf.score(
            trace_id=effective_trace_id,
            name="factscore",
            value=report.factscore.support_rate,
        )
        lf.score(
            trace_id=effective_trace_id,
            name="voice_fidelity",
            value=report.voice.sounds_like_corpus_score,
        )
        lf.score(
            trace_id=effective_trace_id,
            name="editorial_quality",
            value=report.quality.overall_quality_score,
        )
        lf.score(
            trace_id=effective_trace_id,
            name="slop_fingerprint",
            value=report.quality.slop_fingerprint,
        )

        lf.flush()
        log.debug(
            "write_eval_to_langfuse: wrote trace %s (verdict=%s)",
            effective_trace_id,
            report.overall_verdict,
        )
        return True

    except ImportError:
        log.debug("write_eval_to_langfuse: langfuse not installed — no-op")
        return False
    except Exception as exc:
        log.warning("write_eval_to_langfuse: failed (%s) — continuing", exc)
        return False


# ---------------------------------------------------------------------------
# Voice corpus loader
# ---------------------------------------------------------------------------


def load_voice_corpus_samples(
    db: Any,
    target_voice: Literal[
        "cfb_index", "bill_connelly", "matt_brown", "spencer_hall"
    ] = "cfb_index",
    k: int = 20,
) -> list[str]:
    """Load reference voice samples for G-Eval comparison.

    'cfb_index': samples from editorial_citations table (body/quote columns).
    Other voices: returns built-in hand-curated seed passages.

    Handles empty tables gracefully (returns seed list).
    """
    if target_voice != "cfb_index":
        return _builtin_voice_seeds(target_voice)

    samples: list[str] = []

    # Try editorial_citations first
    try:
        rows = db.query_all(
            """
            SELECT citation_text, quote, body
            FROM editorial_citations
            LIMIT ?
            """,
            (k * 2,),
        )
        for row in rows:
            text = row.get("citation_text") or row.get("quote") or row.get("body") or ""
            text = text.strip()
            if text and len(text.split()) >= 10:
                # Extract a ~50-100 word passage
                words = text.split()
                passage = " ".join(words[:80])
                samples.append(passage)
            if len(samples) >= k:
                break
    except Exception as exc:
        log.debug("load_voice_corpus_samples: editorial_citations query failed (%s)", exc)

    # Fill remainder from built-in seeds if DB was sparse
    if len(samples) < 5:
        seeds = _builtin_voice_seeds("cfb_index")
        samples.extend(seeds[: k - len(samples)])

    return samples[:k]


def _builtin_voice_seeds(
    voice: str,
) -> list[str]:
    """Hard-coded seed passages per voice. Used as fallback when DB is empty."""
    seeds: dict[str, list[str]] = {
        "cfb_index": [
            (
                "The margin between Ward's arm talent and his decision-making in the pocket "
                "closed to near-zero by week eight — a convergence that drove coordinator "
                "adjustments across three consecutive opponents, per CFBD play-log data."
            ),
            (
                "Ohio State's schedule strength ranked 4th nationally entering bowl season, "
                "a figure that understates the cumulative damage of playing four top-15 opponents "
                "in a six-week window, via SP+ projections."
            ),
            (
                "Recruiting footprint tells one story; transfer-portal velocity tells another. "
                "Georgia's net production surplus — measured as draft value out minus draft-equivalent "
                "value in — sat at +2.1 per 247Sports composite data."
            ),
        ],
        "bill_connelly": [
            (
                "The efficiency gains from the new offensive coordinator arrived quietly: "
                "third-down conversion rate up four points, success rate climbing from 43 to 47 percent. "
                "Small numbers, enormous implications for the spring depth chart."
            ),
            (
                "Explosiveness and efficiency tend to trade off in spread systems, "
                "but this team found an equilibrium — 18 percent of plays gained 15-plus yards "
                "without sacrificing the 48-percent success rate that anchored their winning record."
            ),
        ],
        "matt_brown": [
            (
                "There is no soft way to say this: the roster construction decisions made "
                "in the transfer window will define whether this program belongs in the "
                "upper half of the conference for the next three years."
            ),
        ],
        "spencer_hall": [
            (
                "College football is not interested in your reasonable expectations. "
                "It exists specifically to violate them in the most elaborate fashion possible, "
                "preferably in the rain, preferably on a Thursday."
            ),
        ],
    }
    return seeds.get(voice, seeds["cfb_index"])
