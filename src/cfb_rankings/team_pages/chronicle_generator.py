"""Chronicle card generator — six-stream pipeline (v2, editorial rebuild).

See docs/CHRONICLE_EDITORIAL_BRIEF.md for the voice manifesto this module
implements. The rebuild replaces the earlier template-only generator with a
four-stage pipeline:

    Stage 1 — Multi-stream candidate scan (chronicle_streams.py, pure Python)
    Stage 2 — Heuristic ranking with diversity enforcement
    Stage 3 — LLM writing (claude CLI subprocess; Sonnet standard, Opus
              for blue-bloods' top card)
    Stage 4 — Regex-based validation gate (kills scaffolded / generic copy)

Writing is the only stage with LLM cost. Ranking and validation are pure
Python so the LLM budget can be spent where it actually matters — on voice.

Public entry points:

    generate_chronicle_for_team(db, profile, snapshot, model='auto',
                                max_cards=5, season_year=None) -> list[ChronicleCard]

The returned cards have the same shape as the legacy generator's so the
CLI's persist path is unchanged.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from .chronicle_streams import CandidateObservation, scan_all_streams
from .data import TeamSnapshot
from .profile_loader import Profile


# --------------------------------------------------------------------------
# Card dataclass (persistence contract unchanged — matches legacy schema)
# --------------------------------------------------------------------------

@dataclass
class ChronicleCard:
    card_type: str
    headline: str
    body_md: str
    stat: dict[str, Any]
    comparison: dict[str, Any]
    source_attribution: str
    surprise_score: float
    week: int | None
    model_id: str = "claude-sonnet-4-6"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    validation_notes: list[str] = field(default_factory=list)

    def persist(self, db, team_id: int, season_year: int, surfaced_rank: int, state_sig: dict[str, Any]) -> None:
        db.execute(
            """
            insert into team_chronicle_observations (
                team_id, season_year, week, card_type, headline, body_md,
                stat_json, comparison_json, source_attribution,
                surprise_score, surfaced_rank, state_signature, model_id,
                prompt_tokens, completion_tokens,
                is_published, generated_at_utc
            ) values (
                :team_id, :season, :week, :ct, :hl, :body,
                :stat, :comp, :src,
                :surprise, :rank, :sig, :model,
                :ptok, :ctok,
                1, current_timestamp
            )
            on conflict(team_id, season_year, week, card_type, headline) do update set
                body_md = excluded.body_md,
                stat_json = excluded.stat_json,
                comparison_json = excluded.comparison_json,
                source_attribution = excluded.source_attribution,
                surprise_score = excluded.surprise_score,
                surfaced_rank = excluded.surfaced_rank,
                state_signature = excluded.state_signature,
                model_id = excluded.model_id,
                prompt_tokens = excluded.prompt_tokens,
                completion_tokens = excluded.completion_tokens,
                is_published = 1,
                generated_at_utc = current_timestamp
            """,
            {
                "team_id": team_id,
                "season": season_year,
                "week": self.week,
                "ct": self.card_type,
                "hl": self.headline,
                "body": self.body_md,
                "stat": json.dumps(self.stat, ensure_ascii=False),
                "comp": json.dumps(self.comparison, ensure_ascii=False),
                "src": self.source_attribution,
                "surprise": self.surprise_score,
                "rank": surfaced_rank,
                "sig": json.dumps(state_sig, ensure_ascii=False),
                "model": self.model_id,
                "ptok": int(self.prompt_tokens or 0),
                "ctok": int(self.completion_tokens or 0),
            },
        )


# --------------------------------------------------------------------------
# Blue-blood roster (brief §Stage 3 — Opus gets top-1 per week for these)
# --------------------------------------------------------------------------

BLUE_BLOODS: frozenset[str] = frozenset({
    "alabama", "ohio-state", "georgia", "michigan",
    "texas", "usc", "notre-dame",
})


# --------------------------------------------------------------------------
# Stage 2 — Ranking with diversity
# --------------------------------------------------------------------------

def rank_candidates(
    candidates: list[CandidateObservation],
    profile: Profile,
    max_cards: int = 5,
) -> list[CandidateObservation]:
    """Heuristic ranking with diversity caps (brief §Stage 2).

    Score = oddity_score × voice_fit × evidence_strength. Then apply:
      - max 2 of any single card_type
      - aim for ≥3 distinct types in the final list
      - tie-break on recency (later date_window wins)
    """
    scored: list[tuple[float, CandidateObservation]] = []
    for c in candidates:
        voice_fit = _voice_fit_score(c, profile)
        evidence_strength = _evidence_strength_score(c)
        score = c.oddity_score * voice_fit * evidence_strength
        scored.append((score, c))
    # Sort high-to-low, with recency tie-break.
    scored.sort(key=lambda t: (t[0], t[1].date_window[1]), reverse=True)

    picked: list[CandidateObservation] = []
    type_counts: dict[str, int] = {}
    for (score, cand) in scored:
        if len(picked) >= max_cards:
            break
        if type_counts.get(cand.suggested_type, 0) >= 2:
            continue
        picked.append(cand)
        type_counts[cand.suggested_type] = type_counts.get(cand.suggested_type, 0) + 1

    # Second pass: if we're short of max_cards and have leftover slots,
    # allow one more of the best types.
    if len(picked) < max_cards:
        for (score, cand) in scored:
            if cand in picked:
                continue
            if len(picked) >= max_cards:
                break
            if type_counts.get(cand.suggested_type, 0) >= 3:
                continue
            picked.append(cand)
            type_counts[cand.suggested_type] = type_counts.get(cand.suggested_type, 0) + 1
    return picked


def _voice_fit_score(c: CandidateObservation, profile: Profile) -> float:
    """Cheap voice-fit heuristic. 0.6–1.1 range."""
    score = 1.0
    # Reward streams that carry named entities by default.
    if c.stream in ("rivalry", "player_arc", "archive"):
        score += 0.10
    # Penalize signals that carry no concrete noun beyond the team name.
    if c.stream == "fanintel" and not c.evidence.get("week_key"):
        score -= 0.20
    # Reward candidates whose notes already contain a proper noun
    # (heuristic: any capitalized word beyond first token).
    tokens = c.notes.split()
    cap_count = sum(1 for t in tokens[1:] if t and t[0].isupper())
    if cap_count >= 2:
        score += 0.10
    # Tie into profile aspiration: if candidate evidence mentions a rival
    # that's in the profile's Tier-1 list, bump.
    opp = (c.evidence.get("opponent_slug") or "").lower()
    if opp:
        for r in profile.rivalries:
            if r.get("opponent_slug") == opp and int(r.get("tier", 9)) == 1:
                score += 0.08
                break
    return max(0.4, min(1.2, score))


def _evidence_strength_score(c: CandidateObservation) -> float:
    """Source-strength bonus. 0.7–1.1."""
    src = (c.source_citation or "").lower()
    score = 1.0
    # Archive + gamelog + savant cites are durable signals.
    if "archive" in src or "gamelog" in src or "savant" in src:
        score += 0.05
    # Rivalry trophy cites are great for flashpoint.
    if "archive · last met" in src:
        score += 0.10
    # Velocity-only cites are thin on their own.
    if "velocity" in src and "·" not in src.replace("velocity ·", ""):
        score -= 0.10
    return max(0.7, min(1.1, score))


# --------------------------------------------------------------------------
# Stage 3 — LLM writer
# --------------------------------------------------------------------------

CLAUDE_MODEL_SONNET = "claude-sonnet-4-6"
CLAUDE_MODEL_OPUS = "claude-opus-4-7"

_BANNED_PHRASES: tuple[str, ...] = (
    # brief §6 — banned editorial scaffolding
    " sample",       # leading space to avoid matching "sampling" in context
    "sample ",
    "stat engine",
    "pipeline",
    "our algorithm",
    "the algorithm",
    "methodology",
    "tier 1",
    "tier 2",
    "the pattern is",
    "summary stat",
    "compression of outcome",
    "flattening of",
    "every season produces",
    "this table",
    "this card",
    "this module",
    "the engine",
    "cfb index",
)

# Acceptable attribution patterns (brief §7, plus sensible variants).
_ATTRIBUTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"^gamelog\b",
    r"^savant card\b",
    r"^from the [a-z0-9 '\-–·]+ archive\b",
    r"^from the [a-z0-9 '\-–·]+ season archive\b",
    r"^from \d+ beat[- ]writer pieces\b",
    r"^from [a-z0-9 '\-–·]+ threads?\b",
    r"^onefootdown\b",
    r"^bluegraygold\b",
    r"^south bend tribune\b",
    r"^bluesky\b",
    r"^reddit\b",
    r"^conversation velocity\b",
    r"^cohort divergence\b",
    r"^via \d+",
    r"^player arc\b",
    r"^[a-z '\-]+ beat[- ]writers?\b",
    r"^roster archive\b",
    r"^[a-z' \-]+ · [0-9]{4}",    # Name · YEAR
    r"^beat writers? · ",
))

_COMPARATIVE_MARKERS_RE = re.compile(
    r"\b(since|like|only|longest|shortest|first time|last time|the last time|"
    r"hasn't [a-z]+ since|first (?:since|in)|second[- ]most|best in|worst in|"
    r"more than|fewer than|more of|fewer of|than any|biggest [a-z]+ since|"
    r"most consecutive|fewest|ever|never|always|[0-9]+ years?\b|decade|"
    # program-era markers: 'Era', 'Reconstruction', 'Restoration',
    # 'Dynasty', 'Wilderness', 'Return' (per profile.era_name_overrides)
    r"\b(?:era|reconstruction|restoration|dynasty|wilderness|"
    r"return|correction|chapter|years)|"
    # percentile/rank comparatives
    r"[0-9]+(?:st|nd|rd|th) percentile|top[- ][0-9]+|bottom[- ][0-9]+|"
    r"above|below|beyond|ahead of|behind|ranked|ranks|ranking|"
    # temporal
    r"this season|this year|last season|prior season|previous|earlier|"
    r"a decade ago|generations|ago|across [0-9]+|over [0-9]+|"
    r"back when|back to|not seen|rare|unprecedented|record|historic|"
    r"compares? to|comparison|against the|equal(?:s|led|ing)?|match(?:es|ed|ing)?)\b",
    re.IGNORECASE,
)

# A proper noun beyond the program name: any capitalized word that isn't a
# generic stopword. We check via a simple token scan.
_STOPWORD_CAPS: frozenset[str] = frozenset({
    "The", "A", "An", "In", "On", "At", "To", "Of", "For", "By", "From",
    "Is", "Are", "Was", "Were", "Be", "Been", "Will", "Would", "Could",
    "Should", "Has", "Have", "Had", "Their", "His", "Her", "Its", "This",
    "That", "These", "Those", "But", "And", "Or", "If", "Then", "So",
    "Not", "No", "Yes",
})


def build_write_prompt(
    candidate: CandidateObservation,
    profile: Profile,
    snapshot: TeamSnapshot,
) -> str:
    """Assemble the strict editorial writing prompt (brief §Stage 3)."""
    never = "\n".join(f"- {s}" for s in profile.never_use) or "- (none specified)"
    stock = "\n".join(f"- {s}" for s in profile.stock_phrases) or "- (none specified)"
    era_overrides = profile.era_name_overrides
    era_lines = "\n".join(f"- {k}: {v}" for k, v in era_overrides.items()) or "- (none)"
    mascot = profile.mascot_voice
    mascot_lines = "\n".join(f"- {k}: {v}" for k, v in mascot.items()) or "- (none)"

    banned_list = "\n".join(f"- {p.strip()}" for p in _BANNED_PHRASES) + (
        "\n- any phrase from this program's never-use list above"
    )

    evidence_blob = json.dumps(candidate.evidence, indent=2, ensure_ascii=False)

    return f"""You are writing ONE Chronicle card for {profile.program_name}'s team page.

The Chronicle is an editorial observation feed. Each card reads like what a
sharp independent beat writer for this program would post — a named writer
with taste and a ten-year memory of the program, not a research note, not a
stats engine, not a pipeline describing itself.

# Program voice (use literally, do not paraphrase)

voice_register: {profile.voice_register}
identity_phrase: "{profile.identity_phrase}"
mantra: "{profile.mantra}"

Stock phrases earned on this fanbase — may be echoed in a card when the
context carries them:
{stock}

Era name overrides — use these when referring to coaching periods:
{era_lines}

Mascot voice — for tonal register only, not for literal inclusion:
{mascot_lines}

# Never use (hard bans — rewrite if your draft contains any of these)

{banned_list}

# This week's candidate

Card type: {candidate.suggested_type}
Stream origin: {candidate.stream}
Source citation (use VERBATIM as the attribution field): {candidate.source_citation}

Summary the writer should anchor on:
{candidate.notes}

Raw evidence (JSON):
{evidence_blob}

# Structural constraints

- Headline: 6–14 words. MUST contain at least one specific noun beyond
  "{profile.program_name}" — a player name, a coach, an opponent, a date, a
  stadium, a play. Generic headlines are failures.
- Body: 2–3 sentences, 45–85 words total. Short sentences. Concrete nouns.
  Active voice. At least ONE comparative marker ("since", "like", "only",
  "longest", "first time in X years", "hasn't Y since", etc.) — threading
  the current observation to program memory.
- Attribution: use the source_citation above VERBATIM.
- Do not explain your card. Do not cite "this Chronicle" or "this card" or
  "the pipeline" or "our model" or anything meta. The fan does not want to
  know how the card was made.
- Do not invent facts not in the evidence blob. Do not invent quotes.

# Output format

Return ONLY a JSON object, no markdown fences, no preamble:

{{
  "headline": "<6-14 word headline with a specific noun>",
  "body": "<45-85 word body, 2-3 sentences>",
  "attribution": "<use the source citation verbatim>"
}}

Before returning, read your draft back as if you were a sharp independent
blogger for {profile.program_name}. Would you post this? If the answer is
"yeah, I'd post this," return. Otherwise rewrite once and return."""


def write_card(
    candidate: CandidateObservation,
    profile: Profile,
    snapshot: TeamSnapshot,
    *,
    model: str = CLAUDE_MODEL_SONNET,
    timeout_s: float = 180.0,
) -> tuple[dict[str, str] | None, dict[str, Any]]:
    """Invoke the claude CLI to write the card. Returns (payload, metadata).

    payload = {"headline": str, "body": str, "attribution": str} on success,
    None on failure. metadata includes duration, model, prompt length.
    """
    prompt = build_write_prompt(candidate, profile, snapshot)
    meta: dict[str, Any] = {
        "model": model,
        "prompt_chars": len(prompt),
        "duration_s": 0.0,
        "error": None,
    }
    claude_bin = shutil.which("claude")
    if not claude_bin:
        meta["error"] = "claude CLI not on PATH"
        return None, meta

    # Strip env variables that prevent nested `claude` subprocesses when
    # this CLI is itself run from within a Claude Code session.
    child_env = {k: v for k, v in os.environ.items()
                 if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    start = time.time()
    try:
        # No --permission-mode flag: keeps headless `claude -p` in pure-text
        # mode. plan-mode injects a planning preamble that breaks JSON
        # parsing on some prompts (observed for content-only requests).
        proc = subprocess.run(
            [claude_bin, "-p", prompt, "--model", model],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            encoding="utf-8",
            errors="replace",
            env=child_env,
        )
    except subprocess.TimeoutExpired:
        meta["error"] = f"timeout after {timeout_s}s"
        meta["duration_s"] = timeout_s
        return None, meta
    meta["duration_s"] = round(time.time() - start, 2)
    if proc.returncode != 0:
        meta["error"] = f"claude CLI exit={proc.returncode}: {(proc.stderr or '')[:300].strip()}"
        return None, meta
    raw = (proc.stdout or "").strip()
    payload = _parse_json_from_model_output(raw)
    if payload is None:
        meta["error"] = f"model output unparseable: {raw[:200]}"
        return None, meta
    return payload, meta


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


def _parse_json_from_model_output(raw: str) -> dict[str, str] | None:
    """Tolerant JSON parser — handles bare JSON, fenced blocks, or leading prose."""
    if not raw:
        return None
    # 1. Try direct parse
    for text in (raw, raw.strip()):
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return _normalize_payload(obj)
        except Exception:
            pass
    # 2. Try fenced block
    m = _JSON_FENCE_RE.search(raw)
    if m:
        try:
            obj = json.loads(m.group(1).strip())
            if isinstance(obj, dict):
                return _normalize_payload(obj)
        except Exception:
            pass
    # 3. Try any JSON-shaped substring
    m = _JSON_OBJECT_RE.search(raw)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return _normalize_payload(obj)
        except Exception:
            pass
    return None


def _normalize_payload(obj: dict[str, Any]) -> dict[str, str] | None:
    hl = str(obj.get("headline") or "").strip()
    body = str(obj.get("body") or "").strip()
    attr = str(obj.get("attribution") or "").strip()
    if not (hl and body and attr):
        return None
    return {"headline": hl, "body": body, "attribution": attr}


# --------------------------------------------------------------------------
# Stage 4 — Regex validator
# --------------------------------------------------------------------------

def validate_card(
    payload: dict[str, str],
    candidate: CandidateObservation,
    profile: Profile,
) -> tuple[bool, list[str]]:
    """Four checks from brief §Stage 4. Returns (ok, failure_reasons)."""
    reasons: list[str] = []
    hl = payload["headline"]
    body = payload["body"]
    attr = payload["attribution"]
    combined = f"{hl} {body}".lower()

    # 1) Proper noun beyond program name
    program_tokens = {t.lower() for t in profile.program_name.split()} | {"the"}
    has_specific_noun = False
    for text in (hl, body):
        for tok in text.split():
            clean = tok.strip(".,;:!?'\"()[]·—–-").strip()
            if not clean or not clean[0].isupper():
                continue
            if clean.lower() in program_tokens:
                continue
            if clean in _STOPWORD_CAPS:
                continue
            if len(clean) < 2:
                continue
            has_specific_noun = True
            break
        if has_specific_noun:
            break
    # Numbers (jersey, year, score) also qualify as specific nouns.
    if not has_specific_noun:
        if re.search(r"\b(19|20)\d{2}\b", hl + " " + body):
            has_specific_noun = True
        elif re.search(r"\b\d+[-–]\d+\b", hl + " " + body):
            has_specific_noun = True
    if not has_specific_noun:
        reasons.append("no specific proper-noun beyond program name")

    # 2) Banned phrase check (program-specific never_use + brief §6)
    never_use = [p.lower() for p in (profile.never_use or [])]
    for phrase in _BANNED_PHRASES:
        if phrase in combined:
            reasons.append(f"banned phrase: '{phrase.strip()}'")
            break
    for phrase in never_use:
        if not phrase:
            continue
        if phrase in combined:
            reasons.append(f"profile never_use: '{phrase}'")
            break

    # 3) Comparative marker check
    if not _COMPARATIVE_MARKERS_RE.search(hl + " " + body):
        reasons.append("no comparative marker (since/like/only/longest/…)")

    # 4) Attribution format
    attr_ok = any(pat.search(attr) for pat in _ATTRIBUTION_PATTERNS)
    # Fallback: an exact match of the candidate's source_citation is always acceptable.
    if not attr_ok and attr.strip().lower() == candidate.source_citation.strip().lower():
        attr_ok = True
    if not attr_ok:
        reasons.append(f"attribution format not recognized: '{attr[:80]}'")
    # Banned self-references in attribution — always fatal.
    low_attr = attr.lower()
    if "cfb index" in low_attr or "stat engine" in low_attr or "the pipeline" in low_attr:
        reasons.append("attribution carries scaffolding phrase")

    return (len(reasons) == 0), reasons


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------

def generate_chronicle_for_team(
    db,
    profile: Profile,
    snapshot: TeamSnapshot,
    *,
    model: str = "auto",
    max_cards: int = 5,
    season_year: int | None = None,
    week: int | None = None,
    parallel_workers: int = 3,
    log: Any = None,
) -> list[ChronicleCard]:
    """Full pipeline: scan → rank → write (LLM) → validate → keep survivors.

    model:
      - 'auto'    → Sonnet for standard cards; Opus for the top-1 card of
                    blue-blood programs (brief §Stage 3).
      - 'sonnet'  → all Sonnet
      - 'opus'    → all Opus (expensive; avoid unless testing)
      - 'template' → skip the LLM entirely; emit a deterministic card from
                     the candidate evidence (degraded mode for offline dev).
    """
    logf = _make_logger(log)
    season_year = season_year or snapshot.season_year
    conn = db.connection() if hasattr(db, "connection") else db
    # Stage 1 — Stream scan
    with conn as c:
        candidates = scan_all_streams(c, profile.slug, season_year, week)
    logf(f"  [{profile.slug}] streams: {len(candidates)} candidates")

    # Stage 2 — Rank + diversify
    ranked = rank_candidates(candidates, profile, max_cards=max_cards)
    if not ranked:
        logf(f"  [{profile.slug}] no candidates survived ranking")
        return []

    # Stage 3 — Write (LLM, parallel)
    if model == "template":
        return [_template_card(c, profile, rank=i+1) for i, c in enumerate(ranked)]

    is_blueblood = profile.slug in BLUE_BLOODS
    job_specs: list[tuple[int, CandidateObservation, str]] = []
    for i, cand in enumerate(ranked):
        if model == "sonnet":
            mdl = CLAUDE_MODEL_SONNET
        elif model == "opus":
            mdl = CLAUDE_MODEL_OPUS
        else:  # auto
            if is_blueblood and i == 0:
                mdl = CLAUDE_MODEL_OPUS
            else:
                mdl = CLAUDE_MODEL_SONNET
        job_specs.append((i, cand, mdl))

    def _one(spec: tuple[int, CandidateObservation, str]) -> tuple[int, CandidateObservation, str, dict[str, str] | None, dict[str, Any]]:
        i, cand, mdl = spec
        payload, meta = write_card(cand, profile, snapshot, model=mdl)
        return (i, cand, mdl, payload, meta)

    results: list[tuple[int, CandidateObservation, str, dict[str, str] | None, dict[str, Any]]] = []
    if parallel_workers > 1:
        with ThreadPoolExecutor(max_workers=parallel_workers) as ex:
            futs = [ex.submit(_one, s) for s in job_specs]
            for fut in as_completed(futs):
                results.append(fut.result())
    else:
        for s in job_specs:
            results.append(_one(s))
    results.sort(key=lambda t: t[0])

    # Stage 4 — Validate, drop failures after 1 retry
    surviving: list[ChronicleCard] = []
    dropped: list[dict[str, Any]] = []
    for (i, cand, mdl, payload, meta) in results:
        if payload is None:
            logf(f"  [{profile.slug}] rank-{i+1} {cand.stream}/{cand.suggested_type}: LLM call failed ({meta.get('error')!r})")
            dropped.append({"rank": i+1, "stream": cand.stream, "type": cand.suggested_type, "reason": meta.get("error"), "stage": "write"})
            continue
        ok, reasons = validate_card(payload, cand, profile)
        if ok:
            surviving.append(_payload_to_card(payload, cand, model_id=mdl, snapshot=snapshot, season_year=season_year, validation_notes=[]))
            continue
        # Retry once.
        logf(f"  [{profile.slug}] rank-{i+1} {cand.stream}/{cand.suggested_type}: validation failed ({reasons}); retrying once")
        payload2, meta2 = write_card(cand, profile, snapshot, model=mdl)
        if payload2 is None:
            logf(f"  [{profile.slug}]   retry also failed: {meta2.get('error')!r}")
            dropped.append({"rank": i+1, "stream": cand.stream, "type": cand.suggested_type, "reason": meta2.get("error"), "stage": "retry-write"})
            continue
        ok2, reasons2 = validate_card(payload2, cand, profile)
        if ok2:
            surviving.append(_payload_to_card(payload2, cand, model_id=mdl, snapshot=snapshot, season_year=season_year, validation_notes=[f"retry:{reasons}"]))
        else:
            logf(f"  [{profile.slug}]   retry validation also failed: {reasons2}")
            dropped.append({"rank": i+1, "stream": cand.stream, "type": cand.suggested_type, "reason": reasons2, "stage": "retry-validate"})

    logf(f"  [{profile.slug}] survived: {len(surviving)}/{len(ranked)} cards "
         f"(dropped: {len(dropped)})")
    return surviving


def _payload_to_card(
    payload: dict[str, str],
    cand: CandidateObservation,
    *,
    model_id: str,
    snapshot: TeamSnapshot,
    season_year: int,
    validation_notes: list[str],
) -> ChronicleCard:
    # Try to extract a week from the candidate evidence or date_window.
    wk = cand.evidence.get("week") or cand.evidence.get("last_mentioned_week") or cand.evidence.get("original_week")
    if wk is not None:
        try:
            wk = int(wk)
        except (TypeError, ValueError):
            wk = None
    return ChronicleCard(
        card_type=cand.suggested_type,
        headline=payload["headline"],
        body_md=payload["body"],
        stat={
            "stream": cand.stream,
            "oddity_score": round(cand.oddity_score, 3),
            "evidence": cand.evidence,
        },
        comparison={
            "source_citation": cand.source_citation,
            "date_window": list(cand.date_window),
        },
        source_attribution=payload["attribution"],
        surprise_score=round(cand.oddity_score, 3),
        week=wk,
        model_id=model_id,
        validation_notes=validation_notes,
    )


def _template_card(cand: CandidateObservation, profile: Profile, rank: int) -> ChronicleCard:
    """Degraded-mode card when LLM is unavailable. Uses stock phrases."""
    stock = profile.stock_phrases[0] if profile.stock_phrases else ""
    hl = cand.notes.split(".")[0][:80]
    body = f"{cand.notes} {stock}".strip()
    return ChronicleCard(
        card_type=cand.suggested_type,
        headline=hl,
        body_md=body,
        stat={"stream": cand.stream, "oddity_score": round(cand.oddity_score, 3)},
        comparison={"source_citation": cand.source_citation},
        source_attribution=cand.source_citation,
        surprise_score=round(cand.oddity_score, 3),
        week=cand.evidence.get("week"),
        model_id="template-v2",
    )


def _make_logger(log: Any) -> Any:
    if log is None:
        return lambda msg: print(msg, flush=True)
    if callable(log):
        return log
    if hasattr(log, "write"):
        return lambda msg: (log.write(msg + "\n"), log.flush())
    return lambda msg: print(msg, flush=True)
