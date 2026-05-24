"""Voice LoRA corpus builder.

Extracts editorial-voice training data from multiple project sources:
  - 127 profile YAMLs (gold standard — hand-authored)
  - Recent editions + daily takes (high-quality production prose)
  - Mailbag answers (Q&A register sample)
  - Editorial citations / design-system docs (style cues)

Output: a JSONL file ready for Unsloth's continued-pretraining loader.
Each line: {"text": "[CFB-INDEX-VOICE]\\n<passage>\\n"}

The [CFB-INDEX-VOICE] sentinel is the activation trigger — at inference time,
we prepend this sentinel to prompts to activate the voice LoRA.

Public API:
    build_corpus(out_path, sources=None, min_words=50, max_words=2000) -> CorpusStats
    extract_from_profiles(profiles_dir) -> list[VoicePassage]
    extract_from_editions(db, since_date) -> list[VoicePassage]
    extract_from_mailbag(db) -> list[VoicePassage]
    extract_from_citations(db) -> list[VoicePassage]
    extract_from_design_docs(docs_dir) -> list[VoicePassage]
    validate_corpus(jsonl_path) -> ValidationReport
"""
from __future__ import annotations

import json
import logging
import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

import yaml

log = logging.getLogger(__name__)

SENTINEL = "[CFB-INDEX-VOICE]"

# Heuristic: 1 word ~= 1.3 tokens for English narrative text.
WORD_TO_TOKEN_RATIO = 1.3

# Sections in profile YAML bodies that hold publishable prose.
# Anything that looks like a stat block / bullet list gets filtered separately.
PROSE_SECTION_NAMES = {
    "program_history",
    "fanbase_summary",
    "rivalry_context",
    "cultural_anchors",
    "identity",
    "voice_register_essay",
    "trajectory_essay",
    "era_essay",
    "stadium_essay",
    "narrative",
    "essay",
    "context",
    "summary",
}

# YAML frontmatter scalar keys whose values are prose-y voice cues worth
# concatenating into a synthetic "style snippet."
VOICE_CUE_KEYS = (
    "identity_phrase",
    "mantra",
)


@dataclass(frozen=True)
class VoicePassage:
    text: str
    source: Literal["profile", "edition", "mailbag", "citation", "design_doc"]
    source_id: str  # filename or DB key
    word_count: int
    quality_score: float = 1.0
    voice_tags: list[str] = field(default_factory=list)

    def to_training_text(self) -> str:
        """Returns the '[CFB-INDEX-VOICE]\\n<passage>\\n' form."""
        return f"{SENTINEL}\n{self.text}\n"


@dataclass(frozen=True)
class CorpusStats:
    total_passages: int
    total_words: int
    total_tokens_estimate: int
    by_source: dict[str, int]
    median_words: float
    p25_words: float
    p75_words: float
    quality_score_mean: float
    out_path: Path


@dataclass(frozen=True)
class ValidationReport:
    line_count: int
    valid_json_count: int
    invalid_json_lines: list[int]
    sentinel_present_count: int
    duplicate_count: int
    avg_words_per_passage: float
    warnings: list[str]


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _looks_like_stat_block(text: str) -> bool:
    """Heuristic: bullet lists, YAML-ish lines, or short data-formatted blocks
    are filtered out. We want narrative prose only."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return True
    bullet_count = sum(1 for ln in lines if ln.lstrip().startswith(("-", "*", "+")))
    if bullet_count / max(1, len(lines)) > 0.5:
        return True
    # Many lines look like "key: value" (YAML scalar) — treat as data
    kv_count = sum(1 for ln in lines if re.match(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*:\s*\S", ln))
    if kv_count / max(1, len(lines)) > 0.5:
        return True
    # Average tokens-per-sentence too low — likely a table
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s for s in sentences if s.strip()]
    if sentences:
        avg_words = sum(_count_words(s) for s in sentences) / len(sentences)
        if avg_words < 6:
            return True
    return False


def _clean_prose(text: str) -> str:
    # Strip leftover markdown formatting we don't want the model to mimic.
    text = re.sub(r"`[^`]*`", "", text)             # inline code
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # bold
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)  # italics
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)    # links → text
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_frontmatter(md_text: str) -> tuple[dict[str, Any], str]:
    """Split a profile-style file into (yaml_dict, body_markdown)."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)\Z", md_text, re.DOTALL)
    if not m:
        return ({}, md_text)
    try:
        meta = yaml.safe_load(m.group(1)) or {}
        if not isinstance(meta, dict):
            meta = {}
    except yaml.YAMLError as exc:
        log.warning("YAML parse failed: %s", exc)
        meta = {}
    return (meta, m.group(2))


def _split_body_sections(body: str) -> list[tuple[str, str]]:
    """Profile bodies use '## section_name' headers. Return list of
    (section_name, prose_block) pairs."""
    sections: list[tuple[str, str]] = []
    # Find every "## name" header position.
    pattern = re.compile(r"^##\s+([A-Za-z0-9_ \-]+?)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(body))
    if not matches:
        # No section headers — treat whole body as one untitled block
        if body.strip():
            sections.append(("body", body.strip()))
        return sections
    for i, m in enumerate(matches):
        name = m.group(1).strip().lower().replace(" ", "_").replace("-", "_")
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections.append((name, body[start:end].strip()))
    return sections


def _voice_tags_from_meta(meta: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    register = meta.get("voice_register") or meta.get("tonal_template")
    if isinstance(register, str) and register:
        tags.append(register)
    tier = meta.get("program_tier")
    if isinstance(tier, int):
        tags.append(f"tier_{tier}")
    return tags


# ----------------------------------------------------------------------------
# Extractors
# ----------------------------------------------------------------------------


def extract_from_profiles(profiles_dir: Path) -> list[VoicePassage]:
    """Walk profiles/*.md (YAML frontmatter + markdown body).

    Extract every prose section longer than `min_words` words (filter applied
    in build_corpus), tag with voice attrs derived from the YAML frontmatter.

    The hand-authored 127 profiles are the GOLD standard — quality 1.0."""
    passages: list[VoicePassage] = []
    if not profiles_dir.exists():
        log.warning("profiles_dir not found: %s", profiles_dir)
        return passages
    files = sorted(profiles_dir.glob("*.md"))
    log.info("extract_from_profiles: scanning %d files", len(files))
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            log.warning("read %s failed: %s", path, exc)
            continue
        meta, body = _split_frontmatter(text)
        tags = _voice_tags_from_meta(meta)

        # 1. Synthesize a "style snippet" from frontmatter voice cues. These
        #    are short but extremely high-signal — identity_phrase + mantra +
        #    stock_phrases together read like a writer's mood board.
        cue_parts: list[str] = []
        for k in VOICE_CUE_KEYS:
            v = meta.get(k)
            if isinstance(v, str) and v.strip():
                cue_parts.append(v.strip())
        stock = meta.get("stock_phrases")
        if isinstance(stock, list):
            for s in stock:
                if isinstance(s, str) and s.strip():
                    cue_parts.append(s.strip())
        cultural = meta.get("cultural_anchors")
        if isinstance(cultural, dict):
            one = cultural.get("one_sentence")
            if isinstance(one, str) and one.strip():
                cue_parts.append(one.strip())
        if cue_parts:
            snippet = " ".join(cue_parts)
            wc = _count_words(snippet)
            if wc >= 20:  # below-threshold snippets get folded later
                passages.append(
                    VoicePassage(
                        text=snippet,
                        source="profile",
                        source_id=f"{path.stem}#frontmatter_cues",
                        word_count=wc,
                        quality_score=1.0,
                        voice_tags=tags + ["style_snippet"],
                    )
                )

        # 2. Body prose sections.
        for name, block in _split_body_sections(body):
            cleaned = _clean_prose(block)
            if not cleaned:
                continue
            if _looks_like_stat_block(cleaned):
                continue
            wc = _count_words(cleaned)
            section_tags = list(tags)
            if name in PROSE_SECTION_NAMES:
                section_tags.append(name)
            passages.append(
                VoicePassage(
                    text=cleaned,
                    source="profile",
                    source_id=f"{path.stem}#{name}",
                    word_count=wc,
                    quality_score=1.0,
                    voice_tags=section_tags,
                )
            )
    log.info("extract_from_profiles: %d raw passages", len(passages))
    return passages


def extract_from_editions(db: Any, since_date: str = "2025-01-01") -> list[VoicePassage]:
    """Pull prose from editions (cover_essay_md) + daily_takes (body) since
    `since_date`. Falls back gracefully if a table is missing."""
    passages: list[VoicePassage] = []
    if db is None:
        log.info("extract_from_editions: no db, skipping")
        return passages

    # editions.cover_essay_md
    try:
        rows = db.query_all(
            "SELECT edition_slug, publish_date, cover_essay_md, status "
            "FROM editions "
            "WHERE publish_date >= :since "
            "  AND cover_essay_md IS NOT NULL "
            "  AND length(cover_essay_md) > 100",
            {"since": since_date},
        )
    except Exception as exc:
        log.warning("editions query failed: %s", exc)
        rows = []
    for r in rows:
        essay = _clean_prose(r.get("cover_essay_md") or "")
        if not essay or _looks_like_stat_block(essay):
            continue
        # Break essay into paragraphs (100-500 words each as a soft target).
        for idx, para in enumerate(_paragraphize(essay, target_min=100, target_max=500)):
            wc = _count_words(para)
            if wc < 40:
                continue
            quality = 0.9 if r.get("status") == "published" else 0.7
            passages.append(
                VoicePassage(
                    text=para,
                    source="edition",
                    source_id=f"{r['edition_slug']}#para{idx}",
                    word_count=wc,
                    quality_score=quality,
                    voice_tags=["edition_cover_essay"],
                )
            )

    # daily_takes.body
    try:
        rows = db.query_all(
            "SELECT edition_date, rank_position, headline, body, voice_validator_passed "
            "FROM daily_takes "
            "WHERE edition_date >= :since "
            "  AND body IS NOT NULL "
            "  AND length(body) > 80",
            {"since": since_date},
        )
    except Exception as exc:
        log.warning("daily_takes query failed: %s", exc)
        rows = []
    for r in rows:
        body = _clean_prose(r.get("body") or "")
        if not body or _looks_like_stat_block(body):
            continue
        wc = _count_words(body)
        if wc < 30:
            continue
        quality = 0.9 if r.get("voice_validator_passed") else 0.75
        passages.append(
            VoicePassage(
                text=body,
                source="edition",
                source_id=f"daily:{r['edition_date']}#{r['rank_position']}",
                word_count=wc,
                quality_score=quality,
                voice_tags=["daily_take"],
            )
        )

    log.info("extract_from_editions: %d passages", len(passages))
    return passages


def extract_from_mailbag(db: Any) -> list[VoicePassage]:
    """Mailbag answers carry a distinct conversational register.
    Tag with voice_tags=['conversational', 'mailbag']."""
    passages: list[VoicePassage] = []
    if db is None:
        return passages
    try:
        rows = db.query_all(
            "SELECT edition_slug, rank_position, answer_body, voice_validator_passed "
            "FROM mailbag_answers "
            "WHERE answer_body IS NOT NULL "
            "  AND length(answer_body) > 100",
        )
    except Exception as exc:
        log.warning("mailbag_answers query failed: %s", exc)
        return passages
    for r in rows:
        body = _clean_prose(r.get("answer_body") or "")
        if not body or _looks_like_stat_block(body):
            continue
        wc = _count_words(body)
        if wc < 40:
            continue
        quality = 0.9 if r.get("voice_validator_passed") else 0.75
        passages.append(
            VoicePassage(
                text=body,
                source="mailbag",
                source_id=f"{r['edition_slug']}#{r['rank_position']}",
                word_count=wc,
                quality_score=quality,
                voice_tags=["conversational", "mailbag"],
            )
        )
    log.info("extract_from_mailbag: %d passages", len(passages))
    return passages


def extract_from_citations(db: Any) -> list[VoicePassage]:
    """editorial_citations in this schema are POINTERS (label + url) — no
    body text. We surface the source_label as a light style cue only when
    it contains an em-dash byline (e.g., 'The Athletic — Stewart Mandel'),
    which is rare. Returns empty list when the table holds only pointers."""
    passages: list[VoicePassage] = []
    if db is None:
        return passages
    try:
        rows = db.query_all(
            "SELECT citation_id, source_label, source_kind, confidence "
            "FROM editorial_citations "
            "WHERE source_label IS NOT NULL AND length(source_label) > 40"
        )
    except Exception as exc:
        log.warning("editorial_citations query failed: %s", exc)
        return passages
    # No prose content here. Skip unless we ever store summary text.
    log.info("extract_from_citations: %d candidate rows (none used — pointers only)", len(rows))
    return passages


def extract_from_design_docs(docs_dir: Path) -> list[VoicePassage]:
    """Pull narrative prose from docs/design-system/*.md voice/tone docs.

    Only files whose stem includes 'tokens', 'modules-hero', 'archetypes',
    'receipt', 'confidence' (which contain voice/copy cues, not pure spec
    tables) are scanned. Each section becomes one passage."""
    passages: list[VoicePassage] = []
    if not docs_dir.exists():
        return passages
    voice_relevant = re.compile(r"(tokens|modules-hero|archetypes|receipt|confidence)", re.IGNORECASE)
    for path in sorted(docs_dir.glob("*.md")):
        if not voice_relevant.search(path.name):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        # Strip frontmatter if present
        meta, body = _split_frontmatter(text)
        for name, block in _split_body_sections(body):
            cleaned = _clean_prose(block)
            if not cleaned:
                continue
            if _looks_like_stat_block(cleaned):
                continue
            wc = _count_words(cleaned)
            if wc < 60:
                continue
            passages.append(
                VoicePassage(
                    text=cleaned,
                    source="design_doc",
                    source_id=f"{path.stem}#{name}",
                    word_count=wc,
                    quality_score=0.7,  # spec prose, not editorial — lower weight
                    voice_tags=["design_doc", name],
                )
            )
    log.info("extract_from_design_docs: %d passages", len(passages))
    return passages


# ----------------------------------------------------------------------------
# Paragraphizer + dedup + builder + validator
# ----------------------------------------------------------------------------


def _paragraphize(text: str, target_min: int = 100, target_max: int = 500) -> list[str]:
    """Split a long essay into paragraph-ish chunks in the [target_min,
    target_max] word range. Greedy combine across blank lines."""
    raw_paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out: list[str] = []
    buf: list[str] = []
    buf_words = 0
    for para in raw_paras:
        wc = _count_words(para)
        if buf_words + wc <= target_max:
            buf.append(para)
            buf_words += wc
            if buf_words >= target_min:
                out.append("\n\n".join(buf))
                buf, buf_words = [], 0
        else:
            if buf:
                out.append("\n\n".join(buf))
                buf, buf_words = [], 0
            if wc <= target_max:
                buf.append(para)
                buf_words = wc
            else:
                # Single para too long — emit as-is; trainer will truncate.
                out.append(para)
    if buf:
        out.append("\n\n".join(buf))
    return out


def _shingles(text: str, k: int = 5) -> set[str]:
    words = re.findall(r"\b\w+\b", text.lower())
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


def deduplicate(passages: list[VoicePassage], min_diff_ratio: float = 0.85) -> list[VoicePassage]:
    """Remove near-duplicate passages by Jaccard on 5-gram shingles.

    Two passages are duplicates if Jaccard similarity > min_diff_ratio. The
    higher-quality (and longer, as tiebreaker) survivor is kept."""
    # Sort by (quality desc, word_count desc) so survivor is the first hit.
    ordered = sorted(passages, key=lambda p: (-p.quality_score, -p.word_count))
    kept: list[VoicePassage] = []
    kept_shingles: list[set[str]] = []
    for p in ordered:
        sh = _shingles(p.text)
        is_dup = False
        for prev in kept_shingles:
            if not sh or not prev:
                continue
            inter = len(sh & prev)
            union = len(sh | prev)
            if union and inter / union > min_diff_ratio:
                is_dup = True
                break
        if not is_dup:
            kept.append(p)
            kept_shingles.append(sh)
    return kept


def build_corpus(
    out_path: Path,
    sources: list[str] | None = None,
    min_words: int = 50,
    max_words: int = 2000,
    quality_threshold: float = 0.6,
    db: Any = None,
    profiles_dir: Path | None = None,
    design_docs_dir: Path | None = None,
    editions_since: str = "2025-01-01",
) -> CorpusStats:
    """Top-level corpus builder.

    sources defaults to ['profile', 'edition', 'mailbag', 'citation', 'design_doc'].
    """
    sources = sources or ["profile", "edition", "mailbag", "citation", "design_doc"]
    profiles_dir = profiles_dir or Path("profiles")
    design_docs_dir = design_docs_dir or Path("docs/design-system")

    all_passages: list[VoicePassage] = []
    if "profile" in sources:
        all_passages.extend(extract_from_profiles(profiles_dir))
    if "edition" in sources:
        all_passages.extend(extract_from_editions(db, since_date=editions_since))
    if "mailbag" in sources:
        all_passages.extend(extract_from_mailbag(db))
    if "citation" in sources:
        all_passages.extend(extract_from_citations(db))
    if "design_doc" in sources:
        all_passages.extend(extract_from_design_docs(design_docs_dir))

    log.info("raw passages: %d", len(all_passages))

    # Filter by length + quality
    filtered = [
        p
        for p in all_passages
        if min_words <= p.word_count <= max_words and p.quality_score >= quality_threshold
    ]
    log.info("after length/quality filter: %d", len(filtered))

    # Deduplicate
    deduped = deduplicate(filtered)
    log.info("after dedup: %d", len(deduped))

    # Write JSONL
    out_path.parent.mkdir(parents=True, exist_ok=True)
    by_source: dict[str, int] = {}
    with out_path.open("w", encoding="utf-8") as fh:
        for p in deduped:
            fh.write(json.dumps({"text": p.to_training_text()}, ensure_ascii=False) + "\n")
            by_source[p.source] = by_source.get(p.source, 0) + 1

    if deduped:
        word_counts = [p.word_count for p in deduped]
        median = statistics.median(word_counts)
        try:
            qs = statistics.quantiles(word_counts, n=4)
            p25, p75 = qs[0], qs[2]
        except statistics.StatisticsError:
            p25 = p75 = float(median)
        quality_mean = statistics.mean(p.quality_score for p in deduped)
        total_words = sum(word_counts)
    else:
        median = p25 = p75 = 0.0
        quality_mean = 0.0
        total_words = 0

    return CorpusStats(
        total_passages=len(deduped),
        total_words=total_words,
        total_tokens_estimate=int(total_words * WORD_TO_TOKEN_RATIO),
        by_source=by_source,
        median_words=float(median),
        p25_words=float(p25),
        p75_words=float(p75),
        quality_score_mean=float(quality_mean),
        out_path=out_path,
    )


def validate_corpus(jsonl_path: Path) -> ValidationReport:
    """Lint a built corpus file. Catches malformed JSON, missing sentinel,
    duplicates, suspiciously short passages."""
    line_count = 0
    valid_json = 0
    invalid_lines: list[int] = []
    sentinel_count = 0
    seen_texts: set[str] = set()
    duplicate_count = 0
    word_total = 0
    warnings: list[str] = []

    with jsonl_path.open(encoding="utf-8") as fh:
        for idx, raw in enumerate(fh, start=1):
            line_count += 1
            raw = raw.rstrip("\n")
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                invalid_lines.append(idx)
                continue
            valid_json += 1
            text = obj.get("text", "") if isinstance(obj, dict) else ""
            if SENTINEL in text:
                sentinel_count += 1
            else:
                warnings.append(f"line {idx}: missing sentinel")
            if text in seen_texts:
                duplicate_count += 1
            else:
                seen_texts.add(text)
            wc = _count_words(text)
            word_total += wc
            if wc < 30:
                warnings.append(f"line {idx}: suspiciously short ({wc} words)")

    avg_words = (word_total / valid_json) if valid_json else 0.0
    return ValidationReport(
        line_count=line_count,
        valid_json_count=valid_json,
        invalid_json_lines=invalid_lines,
        sentinel_present_count=sentinel_count,
        duplicate_count=duplicate_count,
        avg_words_per_passage=avg_words,
        warnings=warnings[:50],  # cap noise
    )
