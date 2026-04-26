"""Predictive-claim extraction pipeline (Sprint 13 Phase 1+3).

Stage 0 — deterministic prefilter (regex) over conversation_documents.
            Cheap, runs over all 180k corpus rows in a few seconds.
            Output: candidate sentence + parent doc id + extracted prediction
            phrase markers.

Stage 1 — Haiku batch classification.
            For each candidate, decide:
              - is this actually a prediction? (boolean)
              - prediction_kind (record/game/recruit/...)
              - entities mentioned (programs / players / coaches / conferences)
              - outcome_window (start, end)
              - confidence
            Batched 25 candidates per call.

Stage 2 — Sonnet review on Haiku's medium-confidence (0.55..0.85) outputs.
            Refines kind, entities, window; drops misclassifications.

Offline mode (no ANTHROPIC_API_KEY): Stage 1+2 are stubbed with heuristics so
the full pipeline still runs end-to-end during dev / CI verification.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Iterator, Sequence

from .runtime import db_conn, slugify, utc_now_iso


# ---------- Stage 0: deterministic prefilter --------------------------------

# Patterns the prefilter looks for. Order roughly matches strength.
_PREDICTIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("direct_will",       re.compile(r"\b(?:will|is going to|are going to)\b\s+\w+", re.IGNORECASE)),
    ("soft_predict",      re.compile(r"\bI (?:think|bet|believe|guarantee|predict)\s+\w+", re.IGNORECASE)),
    ("watch_for",         re.compile(r"\b(?:watch|look)\s+for\s+\w+\s+to\b", re.IGNORECASE)),
    ("bet_on",            re.compile(r"\bbet on\b\s+\w+\s+to\b", re.IGNORECASE)),
    ("mark_x",            re.compile(r"\bmark\s+(?:them|this|\w+)\s+(?:down\s+)?(?:for|as)\b", re.IGNORECASE)),
    ("starts_wins",       re.compile(r"\b\d+\s*-\s*\d+\b.*\b(?:season|start|finish|record)\b", re.IGNORECASE)),
    ("calling_it",        re.compile(r"\b(?:calling it now|book it|mark my words|write it down)\b", re.IGNORECASE)),
    ("make_playoff",      re.compile(r"\b(?:make|miss)\s+(?:the\s+)?(?:playoff|cfp|final\s*four)\b", re.IGNORECASE)),
    ("win_the",           re.compile(r"\bwin\s+(?:the\s+)?(?:title|natty|championship|sec|big\s*ten|acc|big\s*12)\b", re.IGNORECASE)),
    ("by_end_of",         re.compile(r"\bby (?:the )?end of (?:the )?(?:year|season|month)\b", re.IGNORECASE)),
)

# Sentence splitter — naive but good enough for fan-intel corpus quality.
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

# Tokens to skip outright — these are clearly not predictions.
_DEAD_PATTERNS = re.compile(
    r"\b(?:was|were|had|won|lost|finished|ended|beat|defeated)\b", re.IGNORECASE
)


@dataclass
class Candidate:
    conversation_document_id: int
    source_name: str
    source_subchannel: str | None
    source_author_name: str | None
    source_url: str | None
    external_created_at_utc: str
    sentence: str
    pattern_hits: list[str] = field(default_factory=list)


def iter_documents(
    conn: sqlite3.Connection,
    *,
    days: int | None = 365,
    source_names: Sequence[str] | None = None,
    limit: int | None = None,
) -> Iterator[sqlite3.Row]:
    """Yield candidate documents for prefilter scanning."""
    where = ["body_text IS NOT NULL", "LENGTH(body_text) > 30"]
    params: list[Any] = []
    if days is not None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        where.append("external_created_at_utc >= ?")
        params.append(cutoff)
    if source_names:
        placeholders = ",".join("?" for _ in source_names)
        where.append(f"source_name IN ({placeholders})")
        params.extend(source_names)
    sql = f"""
        SELECT conversation_document_id, source_name, source_subchannel,
               source_author_name, source_url, title_text, body_text,
               external_created_at_utc
          FROM conversation_documents
         WHERE {' AND '.join(where)}
         ORDER BY external_created_at_utc DESC
    """
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    yield from conn.execute(sql, params)


def split_sentences(text: str) -> list[str]:
    if not text:
        return []
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]


def detect_predictive_patterns(sentence: str) -> list[str]:
    """Return list of pattern names that fired. Empty = not predictive."""
    if _DEAD_PATTERNS.search(sentence) and not re.search(
        r"\b(?:will|going to|bet|mark|book it|predict)\b", sentence, re.IGNORECASE
    ):
        # Past-tense without prediction markers — drop.
        return []
    hits: list[str] = []
    for name, pat in _PREDICTIVE_PATTERNS:
        if pat.search(sentence):
            hits.append(name)
    return hits


def prefilter_corpus(
    *,
    days: int | None = 365,
    source_names: Sequence[str] | None = None,
    limit_docs: int | None = None,
    max_sentence_len: int = 400,
    min_sentence_len: int = 25,
) -> Iterator[Candidate]:
    """Stream Candidate records through the regex prefilter."""
    with db_conn(read_only=True) as conn:
        for doc in iter_documents(
            conn, days=days, source_names=source_names, limit=limit_docs
        ):
            title = doc["title_text"] or ""
            body = doc["body_text"] or ""
            for sentence in split_sentences(f"{title}. {body}"):
                if not (min_sentence_len <= len(sentence) <= max_sentence_len):
                    continue
                hits = detect_predictive_patterns(sentence)
                if not hits:
                    continue
                yield Candidate(
                    conversation_document_id=doc["conversation_document_id"],
                    source_name=doc["source_name"],
                    source_subchannel=doc["source_subchannel"],
                    source_author_name=doc["source_author_name"],
                    source_url=doc["source_url"],
                    external_created_at_utc=doc["external_created_at_utc"] or "",
                    sentence=sentence,
                    pattern_hits=hits,
                )


# ---------- Stage 1: Haiku batch classifier ---------------------------------

HAIKU_MODEL = os.environ.get("RECEIPTS_HAIKU_MODEL", "claude-haiku-4-5")
SONNET_MODEL = os.environ.get("RECEIPTS_SONNET_MODEL", "claude-sonnet-4-5")
OPUS_MODEL = os.environ.get("RECEIPTS_OPUS_MODEL", "claude-opus-4-5")

PREDICTION_KINDS = (
    "record", "game", "recruit", "coaching_change", "portal",
    "award", "rank", "title", "playoff_bid", "other",
)


def _have_anthropic() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _anthropic_client():
    """Lazy-import the SDK so offline mode never imports it."""
    import anthropic  # noqa: WPS433
    return anthropic.Anthropic()


@dataclass
class ExtractedClaim:
    candidate: Candidate
    is_prediction: bool
    prediction_kind: str
    entities_mentioned: dict[str, list[str]]
    outcome_window_start: str  # ISO date
    outcome_window_end: str
    confidence: float
    summary_short: str
    extractor_pass: str = "haiku_initial"
    extractor_model: str = HAIKU_MODEL
    review_notes: str | None = None


_HAIKU_SYSTEM = """You are a CFB editorial classifier.

For each numbered candidate sentence, decide whether the sentence makes a TESTABLE PREDICTION about a future college-football outcome (game result, season record, recruiting destination, coaching hire, award, ranking, playoff bid). Past-tense statements, opinions about identity ("Bama is built different"), and rhetorical questions are NOT predictions.

For each candidate, emit a single JSON line with EXACTLY these keys:
  i: candidate index (integer)
  is_prediction: true|false
  kind: one of [record, game, recruit, coaching_change, portal, award, rank, title, playoff_bid, other]
  programs: array of program slugs (lowercase-hyphen, e.g. "ohio-state")
  players: array of player names mentioned
  coaches: array of coach names mentioned
  conferences: array of conference slugs (sec, big-ten, acc, big-12, pac-12, american, mwc, sun-belt, mac, c-usa, ind)
  window_start: YYYY-MM-DD that the prediction becomes testable
  window_end: YYYY-MM-DD that the prediction must resolve by
  confidence: 0..1 — your certainty this is genuinely a prediction
  summary: 1-sentence editorial summary (under 25 words)

Output ONE JSON object per line, no preamble, no commentary."""


def _build_haiku_user_prompt(batch: Sequence[Candidate]) -> str:
    lines = []
    for i, c in enumerate(batch):
        lines.append(f"[{i}] {c.sentence}")
    return "Candidates:\n" + "\n".join(lines)


def classify_batch_haiku(
    batch: Sequence[Candidate],
    *,
    offline: bool | None = None,
) -> tuple[list[ExtractedClaim], dict[str, int]]:
    """Returns (claims, token_usage_dict)."""
    use_offline = offline if offline is not None else not _have_anthropic()
    if use_offline:
        return _stub_classify_haiku(batch), {"input_tokens": 0, "output_tokens": 0}

    client = _anthropic_client()
    user_prompt = _build_haiku_user_prompt(batch)
    resp = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=2000,
        system=_HAIKU_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(b.text for b in resp.content if hasattr(b, "text"))
    tokens = {
        "input_tokens": getattr(resp.usage, "input_tokens", 0),
        "output_tokens": getattr(resp.usage, "output_tokens", 0),
    }
    return _parse_haiku_response(text, batch), tokens


def _parse_haiku_response(text: str, batch: Sequence[Candidate]) -> list[ExtractedClaim]:
    out: list[ExtractedClaim] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        i = obj.get("i")
        if not isinstance(i, int) or i < 0 or i >= len(batch):
            continue
        if not obj.get("is_prediction"):
            continue
        kind = obj.get("kind", "other")
        if kind not in PREDICTION_KINDS:
            kind = "other"
        out.append(ExtractedClaim(
            candidate=batch[i],
            is_prediction=True,
            prediction_kind=kind,
            entities_mentioned={
                "programs": list(obj.get("programs") or []),
                "players": list(obj.get("players") or []),
                "coaches": list(obj.get("coaches") or []),
                "conferences": list(obj.get("conferences") or []),
            },
            outcome_window_start=obj.get("window_start") or _default_window_start(batch[i]),
            outcome_window_end=obj.get("window_end") or _default_window_end(batch[i]),
            confidence=float(obj.get("confidence") or 0.5),
            summary_short=(obj.get("summary") or batch[i].sentence)[:240],
        ))
    return out


def _default_window_start(c: Candidate) -> str:
    base = c.external_created_at_utc[:10] or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return base


def _default_window_end(c: Candidate) -> str:
    try:
        d = datetime.fromisoformat(c.external_created_at_utc.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        d = datetime.now(timezone.utc)
    return (d + timedelta(days=400)).strftime("%Y-%m-%d")


# ---------- Stage 1 offline stub -------------------------------------------

# Lightweight slug map so the offline path produces sensible entities.
_PROGRAM_HINTS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE), slug)
    for name, slug in [
        ("Alabama", "alabama"), ("Bama", "alabama"),
        ("Ohio State", "ohio-state"), ("Buckeyes", "ohio-state"),
        ("Michigan", "michigan"), ("Wolverines", "michigan"),
        ("Georgia", "georgia"), ("Bulldogs", "georgia"),
        ("Texas", "texas"), ("Longhorns", "texas"),
        ("Oklahoma", "oklahoma"), ("Sooners", "oklahoma"),
        ("Notre Dame", "notre-dame"),
        ("USC", "usc"), ("Trojans", "usc"),
        ("LSU", "lsu"), ("Tigers", "lsu"),
        ("Penn State", "penn-state"),
        ("Oregon", "oregon"), ("Ducks", "oregon"),
        ("Tennessee", "tennessee"), ("Vols", "tennessee"),
        ("Florida", "florida"), ("Gators", "florida"),
        ("Auburn", "auburn"),
        ("UMass", "umass"),
        ("Indiana", "indiana"), ("Hoosiers", "indiana"),
        ("Miami", "miami"), ("Hurricanes", "miami"),
        ("Clemson", "clemson"),
        ("Florida State", "florida-state"), ("FSU", "florida-state"),
    ]
)

_CONFERENCE_HINTS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE), slug)
    for name, slug in [
        ("SEC", "sec"), ("Big Ten", "big-ten"), ("ACC", "acc"),
        ("Big 12", "big-12"), ("Pac-12", "pac-12"),
    ]
)


def _stub_extract_entities(sentence: str) -> dict[str, list[str]]:
    progs = sorted({slug for pat, slug in _PROGRAM_HINTS if pat.search(sentence)})
    confs = sorted({slug for pat, slug in _CONFERENCE_HINTS if pat.search(sentence)})
    return {"programs": progs, "players": [], "coaches": [], "conferences": confs}


def _stub_classify_kind(sentence: str) -> str:
    s = sentence.lower()
    if re.search(r"\b\d+\s*[-–]\s*\d+\b|\b(?:undefeated|unbeaten|finish [\d]+)\b", s):
        return "record"
    if "playoff" in s or "cfp" in s:
        return "playoff_bid"
    if re.search(r"\b(?:title|natty|championship)\b", s):
        return "title"
    if re.search(r"\b(?:rank|ranked|top \d+|preseason)\b", s):
        return "rank"
    if re.search(r"\b(?:hire|fire|coach|coaching)\b", s):
        return "coaching_change"
    if re.search(r"\b(?:commit|recruit|prospect|signing)\b", s):
        return "recruit"
    if re.search(r"\b(?:transfer|portal)\b", s):
        return "portal"
    if re.search(r"\b(?:heisman|biletnikoff|outland|bednarik|maxwell|doak)\b", s):
        return "award"
    if re.search(r"\b(?:beat|loses to|covers|cover the spread|wins by)\b", s):
        return "game"
    return "other"


def _stub_classify_haiku(batch: Sequence[Candidate]) -> list[ExtractedClaim]:
    out: list[ExtractedClaim] = []
    for c in batch:
        ents = _stub_extract_entities(c.sentence)
        # heuristic: stronger pattern hits + entity present → higher confidence
        base = 0.55 + min(len(c.pattern_hits), 3) * 0.08
        if ents["programs"]:
            base += 0.10
        if ents["conferences"]:
            base += 0.05
        confidence = min(base, 0.92)
        out.append(ExtractedClaim(
            candidate=c,
            is_prediction=True,
            prediction_kind=_stub_classify_kind(c.sentence),
            entities_mentioned=ents,
            outcome_window_start=_default_window_start(c),
            outcome_window_end=_default_window_end(c),
            confidence=round(confidence, 3),
            summary_short=c.sentence[:240],
        ))
    return out


# ---------- Stage 2: Sonnet review pass -------------------------------------

_SONNET_SYSTEM = """You are a CFB editorial fact-checker reviewing tentative predictive-claim extractions.

For each claim, output a single JSON line with:
  i: index (integer)
  keep: true|false (drop misclassifications)
  kind: refined prediction_kind (or unchanged)
  programs: refined program slugs
  players: refined player names
  coaches: refined coach names
  conferences: refined conference slugs
  window_start: YYYY-MM-DD
  window_end: YYYY-MM-DD
  confidence: 0..1 (refined)
  summary: 1-sentence editorial summary (under 25 words)
  notes: short explanation of any change (optional)

Be especially strict about: (a) past-tense statements masquerading as predictions, (b) rhetorical hyperbole, (c) jokes."""


def review_batch_sonnet(
    drafts: Sequence[ExtractedClaim],
    *,
    offline: bool | None = None,
) -> tuple[list[ExtractedClaim], dict[str, int]]:
    """Review medium-confidence Haiku drafts and refine."""
    use_offline = offline if offline is not None else not _have_anthropic()
    if use_offline:
        return _stub_review_sonnet(drafts), {"input_tokens": 0, "output_tokens": 0}

    client = _anthropic_client()
    user_lines = [
        f"[{i}] kind={d.prediction_kind} | text={d.candidate.sentence} | "
        f"programs={d.entities_mentioned['programs']} | confidence={d.confidence}"
        for i, d in enumerate(drafts)
    ]
    user_prompt = "Drafts:\n" + "\n".join(user_lines)
    resp = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=2400,
        system=_SONNET_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(b.text for b in resp.content if hasattr(b, "text"))
    tokens = {
        "input_tokens": getattr(resp.usage, "input_tokens", 0),
        "output_tokens": getattr(resp.usage, "output_tokens", 0),
    }
    return _parse_sonnet_response(text, drafts), tokens


def _parse_sonnet_response(text: str, drafts: Sequence[ExtractedClaim]) -> list[ExtractedClaim]:
    out: list[ExtractedClaim] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        i = obj.get("i")
        if not isinstance(i, int) or i < 0 or i >= len(drafts):
            continue
        if not obj.get("keep", True):
            continue
        d = drafts[i]
        kind = obj.get("kind", d.prediction_kind)
        if kind not in PREDICTION_KINDS:
            kind = "other"
        out.append(ExtractedClaim(
            candidate=d.candidate,
            is_prediction=True,
            prediction_kind=kind,
            entities_mentioned={
                "programs": list(obj.get("programs") or d.entities_mentioned["programs"]),
                "players": list(obj.get("players") or d.entities_mentioned["players"]),
                "coaches": list(obj.get("coaches") or d.entities_mentioned["coaches"]),
                "conferences": list(obj.get("conferences") or d.entities_mentioned["conferences"]),
            },
            outcome_window_start=obj.get("window_start") or d.outcome_window_start,
            outcome_window_end=obj.get("window_end") or d.outcome_window_end,
            confidence=float(obj.get("confidence") or d.confidence),
            summary_short=(obj.get("summary") or d.summary_short)[:240],
            extractor_pass="sonnet_review",
            extractor_model=SONNET_MODEL,
            review_notes=obj.get("notes"),
        ))
    return out


def _stub_review_sonnet(drafts: Sequence[ExtractedClaim]) -> list[ExtractedClaim]:
    """Offline reviewer: drop low-confidence / no-entity drafts; bump the rest."""
    kept: list[ExtractedClaim] = []
    for d in drafts:
        has_entities = any(d.entities_mentioned[k] for k in ("programs", "players", "coaches", "conferences"))
        if d.confidence < 0.55 and not has_entities:
            continue
        kept.append(ExtractedClaim(
            candidate=d.candidate,
            is_prediction=True,
            prediction_kind=d.prediction_kind,
            entities_mentioned=d.entities_mentioned,
            outcome_window_start=d.outcome_window_start,
            outcome_window_end=d.outcome_window_end,
            confidence=min(0.95, d.confidence + 0.04),
            summary_short=d.summary_short,
            extractor_pass="sonnet_review",
            extractor_model=SONNET_MODEL,
            review_notes="offline-stub: kept based on confidence + entities",
        ))
    return kept


# ---------- Persistence ------------------------------------------------------

def _source_kind_from_name(source_name: str | None, subchannel: str | None) -> str:
    name = (source_name or "").lower()
    if name == "reddit":
        return "reddit"
    if name in {"bluesky", "bsky"}:
        return "bluesky"
    if name in {"podcast", "podcasts", "podcasts_meta"}:
        return "podcast"
    if name in {"campus_news", "google_news", "rss"}:
        return "beat_writer"
    if name in {"official_release", "official"}:
        return "official_release"
    if name == "our_chronicle":
        return "our_chronicle"
    if name == "our_canon":
        return "our_canon"
    return "board_post"  # default


def _source_slug(claim: ExtractedClaim) -> str:
    cand = claim.candidate
    if cand.source_author_name:
        return slugify(f"{cand.source_name}-{cand.source_author_name}")
    if cand.source_subchannel:
        return slugify(f"{cand.source_name}-{cand.source_subchannel}")
    return slugify(cand.source_name or "unknown")


def persist_claims(
    claims: Iterable[ExtractedClaim],
    *,
    run_id: int | None = None,
) -> int:
    """Insert claims into predictive_claims. Returns count inserted."""
    n = 0
    with db_conn() as conn:
        for claim in claims:
            cand = claim.candidate
            try:
                conn.execute("""
                    INSERT INTO predictive_claims (
                        source_kind, source_slug, source_url, source_published_at,
                        conversation_document_id, claim_text, claim_summary_short,
                        entities_mentioned_json, outcome_window_start, outcome_window_end,
                        prediction_kind, confidence_in_extraction,
                        extractor_model, extractor_pass, review_notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    _source_kind_from_name(cand.source_name, cand.source_subchannel),
                    _source_slug(claim),
                    cand.source_url,
                    cand.external_created_at_utc,
                    cand.conversation_document_id,
                    cand.sentence,
                    claim.summary_short,
                    json.dumps(claim.entities_mentioned, sort_keys=True),
                    claim.outcome_window_start,
                    claim.outcome_window_end,
                    claim.prediction_kind,
                    claim.confidence,
                    claim.extractor_model,
                    claim.extractor_pass,
                    claim.review_notes,
                ))
                n += 1
            except sqlite3.IntegrityError:
                continue
        conn.commit()
    return n


def open_run(pass_kind: str, *, days_window: int | None, sources_filter: str | None) -> int:
    with db_conn() as conn:
        cur = conn.execute("""
            INSERT INTO predictive_extraction_runs (pass_kind, days_window, sources_filter)
            VALUES (?, ?, ?)
        """, (pass_kind, days_window, sources_filter))
        conn.commit()
        return int(cur.lastrowid)


def close_run(
    run_id: int,
    *,
    documents_scanned: int,
    claims_extracted: int,
    claims_promoted: int,
    claims_dropped: int,
    haiku_in: int,
    haiku_out: int,
    sonnet_in: int,
    sonnet_out: int,
    notes: str = "",
) -> None:
    with db_conn() as conn:
        conn.execute("""
            UPDATE predictive_extraction_runs
               SET finished_at = CURRENT_TIMESTAMP,
                   documents_scanned = ?,
                   claims_extracted = ?,
                   claims_promoted = ?,
                   claims_dropped = ?,
                   haiku_input_tokens = ?,
                   haiku_output_tokens = ?,
                   sonnet_input_tokens = ?,
                   sonnet_output_tokens = ?,
                   notes = ?
             WHERE id = ?
        """, (documents_scanned, claims_extracted, claims_promoted, claims_dropped,
              haiku_in, haiku_out, sonnet_in, sonnet_out, notes, run_id))
        conn.commit()


# ---------- Orchestration ---------------------------------------------------

def chunked(seq: Iterable[Any], size: int) -> Iterator[list[Any]]:
    buf: list[Any] = []
    for item in seq:
        buf.append(item)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


def run_extraction(
    *,
    days: int = 365,
    source_names: Sequence[str] | None = None,
    limit_docs: int | None = None,
    haiku_batch: int = 25,
    sonnet_review_min: float = 0.55,
    sonnet_review_max: float = 0.85,
    offline: bool | None = None,
    progress_every: int = 50,
) -> dict[str, Any]:
    """Top-level entry. Streams docs through prefilter → Haiku → Sonnet → DB."""
    started = time.time()
    docs_seen = 0
    candidates_count = 0
    haiku_claims_count = 0
    promoted = 0
    dropped = 0
    haiku_in = haiku_out = sonnet_in = sonnet_out = 0

    run_id = open_run(
        "haiku_initial",
        days_window=days,
        sources_filter=",".join(source_names) if source_names else None,
    )

    candidates_iter = prefilter_corpus(
        days=days, source_names=source_names, limit_docs=limit_docs,
    )

    for batch in chunked(candidates_iter, haiku_batch):
        candidates_count += len(batch)
        # Approximate doc count: each candidate corresponds to one doc (some
        # docs produce multiple candidates so this overcounts slightly; ok).
        docs_seen += len({c.conversation_document_id for c in batch})

        haiku_claims, htok = classify_batch_haiku(batch, offline=offline)
        haiku_in += htok["input_tokens"]
        haiku_out += htok["output_tokens"]
        haiku_claims_count += len(haiku_claims)

        # Split: high-confidence → promote directly; medium → Sonnet review.
        high_conf = [c for c in haiku_claims if c.confidence > sonnet_review_max]
        medium = [c for c in haiku_claims
                  if sonnet_review_min <= c.confidence <= sonnet_review_max]
        low = [c for c in haiku_claims if c.confidence < sonnet_review_min]
        dropped += len(low)

        promoted_batch = list(high_conf)
        if medium:
            reviewed, stok = review_batch_sonnet(medium, offline=offline)
            sonnet_in += stok["input_tokens"]
            sonnet_out += stok["output_tokens"]
            promoted_batch.extend(reviewed)
            dropped += len(medium) - len(reviewed)

        promoted += persist_claims(promoted_batch, run_id=run_id)

        if progress_every and (candidates_count % progress_every == 0 or progress_every == 1):
            elapsed = time.time() - started
            print(f"  [extract] candidates={candidates_count} promoted={promoted} "
                  f"dropped={dropped} elapsed={elapsed:.1f}s", flush=True)

    close_run(
        run_id,
        documents_scanned=docs_seen,
        claims_extracted=haiku_claims_count,
        claims_promoted=promoted,
        claims_dropped=dropped,
        haiku_in=haiku_in, haiku_out=haiku_out,
        sonnet_in=sonnet_in, sonnet_out=sonnet_out,
        notes="offline" if (offline or not _have_anthropic()) else "online",
    )

    return {
        "run_id": run_id,
        "documents_scanned": docs_seen,
        "candidates_total": candidates_count,
        "claims_extracted": haiku_claims_count,
        "claims_promoted": promoted,
        "claims_dropped": dropped,
        "haiku_input_tokens": haiku_in,
        "haiku_output_tokens": haiku_out,
        "sonnet_input_tokens": sonnet_in,
        "sonnet_output_tokens": sonnet_out,
        "elapsed_sec": round(time.time() - started, 2),
        "mode": "offline" if (offline or not _have_anthropic()) else "online",
    }
