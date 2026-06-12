"""Missed-Gold Critic + Faithfulness Gate — doc 59 §14.7 / §10 eval contract.

A DEV/EVAL QUALITY tool, NOT in the hot build path. ZERO writes to output/site/,
ZERO writes to the DB, READ-ONLY on prod data. NEVER imported by build-site.

This implements two of the three §10 eval layers (the third, the deterministic
coverage ratchet, is ``scripts/coverage_ratchet_story_cards.py``):

  2. MISSED-GOLD CRITIC (§10.2) — an LLM judge sees the FINISHED card (the five
     rendered fields) PLUS the full :class:`~cfb_rankings.player_pages.packet.Packet`
     and answers ONE question: "what is the single highest-value fact or quote in
     this packet that the card left out?" RESPECTS SUPPRESSION (doc 59 §6): a fact
     whose ``suppress_when``/``suppressed`` is true is NOT missed gold — those
     facts are FILTERED OUT before the judge ever sees them, so silence on a
     phantom-backup clock (Beck/Chambliss) can never be scored as a coverage miss.
     The judge runs on the LOCAL Ollama ``mistral`` path by default (keeps it $0);
     a ``--judge sonnet`` flag routes to the Anthropic API for a sharper read.

  3. FAITHFULNESS GATE (§10.3) — a DETERMINISTIC (zero-LLM) check that every
     concrete claim in the card (proper names, numbers, honors) traces to a packet
     Fact ``source_id`` / ``value`` / ``display``. Any concrete claim with NO
     packet support is flagged as a potential hallucination. Returns a per-card
     pass/fail + the unsupported spans.

Public API:
    card_text_fields(card) -> dict[str, str]            # the five rendered fields
    faithfulness_gate(card, packet) -> FaithfulnessResult
    missed_gold_critic(card, packet, *, judge=...) -> MissedGoldResult
    evaluate_player(db, player_id, season, *, judge=...) -> CardEval
    run_card_eval(db, *, players=None, top_n=12, judge="mistral",
                  season=None) -> dict          # the aggregate quality report
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .packet import Fact, Packet, build_packet
from .story_card import build_card_payload, resolve_external_id


# ===========================================================================
# THE FIVE RENDERED FIELDS (doc 59 §9 step 7 / doc 49 §5). The card's
# DominantTake is a dataclass carrying ``text`` + ``minority_take``; flatten it
# so the critic + faithfulness gate see exactly the prose a fan reads.
# ===========================================================================
def card_text_fields(card: Any) -> dict[str, str]:
    """Extract the five rendered card fields as a flat ``{field: text}`` dict.

    Fields: ``logline`` / ``dominant_take`` / ``minority_take`` / ``body`` /
    ``kicker`` (+ ``why_now`` as a sixth carried-but-secondary string). Missing /
    None fields become "" so callers never key-error. ``dominant_take`` is the
    DominantTake's ``.text``; ``minority_take`` is its ``.minority_take``."""
    out: dict[str, str] = {
        "logline": "",
        "dominant_take": "",
        "minority_take": "",
        "body": "",
        "kicker": "",
        "why_now": "",
    }
    if card is None:
        return out
    out["logline"] = str(getattr(card, "logline", "") or "")
    out["body"] = str(getattr(card, "body", "") or "")
    out["kicker"] = str(getattr(card, "kicker", "") or "")
    out["why_now"] = str(getattr(card, "why_now", "") or "")
    dt = getattr(card, "dominant_take", None)
    if dt is not None:
        out["dominant_take"] = str(getattr(dt, "text", "") or "")
        out["minority_take"] = str(getattr(dt, "minority_take", "") or "")
    return out


def card_full_text(card: Any) -> str:
    """All five+1 fields joined into one prose blob for span scanning."""
    f = card_text_fields(card)
    return " ".join(v for v in f.values() if v).strip()


# ===========================================================================
# SUPPRESSION FILTER (doc 59 §3/§6). A fact is OUT OF SCOPE for "missed gold"
# when ``suppressed`` is True OR ``suppress_when`` is a non-None predicate that
# the builder pre-evaluated to drop it. The builder already sets ``suppressed``
# for the machine-evaluable cases (aura BAN big-gap-tiny-buzz; succession
# entrenched clock; thin ledger take; projected depth-chart). We honor that flag
# AND treat any fact carrying a non-None ``suppress_when`` it itself marked
# suppressed as out of scope — silence on these is CORRECT, not a miss.
# ===========================================================================
def assertable_facts(packet: Packet) -> list[Fact]:
    """The facts the writer was PERMITTED to assert — suppressed facts removed.

    These are the only facts a missed-gold judge may legitimately flag as left
    out. A suppressed fact (phantom clock, big-gap-tiny-buzz BAN, single-source
    take) is intentionally silent per the §6 catalog and must NOT count as gold."""
    out: list[Fact] = []
    for section in packet.sections.values():
        for f in section:
            if getattr(f, "suppressed", False):
                continue
            out.append(f)
    return out


def suppressed_facts(packet: Packet) -> list[Fact]:
    """The mirror set — facts the builder dropped (for the critic's context-only
    appendix and the gate's no-false-positive assertion)."""
    out: list[Fact] = []
    for section in packet.sections.values():
        for f in section:
            if getattr(f, "suppressed", False):
                out.append(f)
    return out


# ===========================================================================
# FAITHFULNESS GATE (doc 59 §10.3) — DETERMINISTIC, ZERO-LLM.
#
# Every concrete claim in the card must trace to a packet Fact. We extract three
# kinds of concrete claim from the card prose:
#   - PROPER NAMES (capitalized multi-word spans + known single tokens)
#   - NUMBERS (integers, decimals, money, ranks like "#3", years, stats "2,616")
#   - HONORS / award tokens (Heisman, All-American, All-<Conf>, etc.)
# A claim is SUPPORTED if its normalized form appears in ANY packet Fact's
# searchable text — the union of every Fact's ``display`` + the stringified
# ``value`` + the player's identity (name/team/position/hometown) + the season
# clock. An UNSUPPORTED concrete claim is a potential hallucination span.
#
# The card's own player name + team are ALWAYS grounded (identity is a §4.1 hard
# fact even though it isn't wrapped as a Fact row). Common English stop-words and
# editorial connective tissue are NOT claims and are never flagged.
# ===========================================================================

# Tokens that look capitalized/number-ish but are editorial, not claims.
_FAITH_STOPWORDS = frozenset(
    w.lower()
    for w in (
        "The", "A", "An", "This", "That", "These", "Those", "It", "Its", "He",
        "His", "Him", "She", "Her", "They", "Their", "Them", "We", "Our", "You",
        "And", "But", "Or", "So", "Yet", "For", "Nor", "If", "Then", "Now",
        "When", "While", "After", "Before", "Over", "Under", "Into", "Onto",
        "Fans", "Fan", "Fanbase", "Room", "Take", "Story", "Season", "Year",
        "Last", "Next", "First", "Best", "More", "Most", "Less", "Least",
        "One", "Two", "Three", "No", "Not", "Never", "Always", "Still",
        "Among", "Across", "Behind", "Beyond", "Between", "Through",
        "Heading", "Looking", "Returning", "Preview", "Spring", "Fall",
        "Saturday", "Sunday", "Monday", "Conference", "League", "Program",
        "Offense", "Defense", "Coach", "Coaching", "Staff", "Job", "Role",
        "Quarterback", "Running", "Wide", "Receiver", "Back", "End", "Line",
        "QB", "RB", "WR", "TE", "All", "American",  # 'All'/'American' handled by honor pass
        # Sentence-initial editorial verbs/connectives that get a stray capital
        # (these are prose, never a concrete claim to ground).
        "Entering", "Despite", "Although", "Though", "Because", "Since",
        "However", "Meanwhile", "Instead", "Indeed", "Perhaps", "Maybe",
        "Already", "Once", "Until", "Unless", "Whether",
        "Question", "Questions", "Critics", "Potential", "Fresh", "New",
        "Last", "Strong", "Several", "Some", "Many", "Few", "Each", "Both",
        "What", "Why", "How", "Where", "Which", "Who", "Whose", "There",
        "As", "At", "By", "In", "On", "Of", "To", "Up", "Out", "Off",
    )
)

# Number-ish spans: money, ranks, decimals, comma-grouped ints, plain ints, years.
_NUM_RE = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?\s?(?:k|m|million|thousand|b|billion)?"  # money
    r"|#\s?\d+"                                                        # rank
    r"|[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?"                              # 2,616
    r"|[+-]?\d+\.\d+"                                                  # decimals
    r"|\b\d+\b",                                                       # plain ints
    re.IGNORECASE,
)

# Proper-name spans: runs of Capitalized words (>=1), allowing internal
# apostrophes/hyphens (O'Brien, Iamaleava). We then drop stopword-only spans.
_NAME_RE = re.compile(r"\b([A-Z][a-zA-Z'’.-]+(?:\s+[A-Z][a-zA-Z'’.-]+)*)\b")

# Honor / award tokens that must trace to a packet honors/award fact.
_HONOR_RE = re.compile(
    r"\b("
    r"Heisman|All-American|All-America|consensus|unanimous|"
    r"All-[A-Z][a-z]+|All-Big\s+\w+|All-SEC|All-ACC|All-Pac\b|"
    r"Davey\s+O'?Brien|Maxwell|Manning|Biletnikoff|Butkus|Bednarik|"
    r"Doak\s+Walker|Lombardi|Lou\s+Groza|Mackey|Hornung|Outland|Thorpe|"
    r"Walter\s+Camp|first-team|second-team|third-team|freshman\s+All-American"
    r")\b",
    re.IGNORECASE,
)


@dataclass
class FaithfulnessResult:
    passed: bool
    unsupported_spans: list[str]
    checked_spans: int
    supported_spans: int
    notes: str = ""


def _normalize(s: str) -> str:
    """Lowercase + strip punctuation so '43-41' and '4341' / '#3' and '3' match
    (CLAUDE.md chronicle eval gotcha: punctuation strip is required for numeric
    substring checks)."""
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


# Trailing possessive: "Iamaleava's" / "Iamaleava’s" / "Vols'" -> the base name.
# Straight + curly apostrophes; the singular-'s and plural-s' forms.
_POSSESSIVE_RE = re.compile(r"['’`]s?$|s['’`]$", re.IGNORECASE)


def _strip_possessive(word: str) -> str:
    """Drop a trailing possessive from ONE word so the possessive form of a
    grounded name ('Iamaleava's') traces to the base name in the packet."""
    return _POSSESSIVE_RE.sub("", str(word))


def _packet_search_corpus(card: Any, packet: Packet) -> tuple[str, set[str]]:
    """Return (normalized_blob, normalized_token_set) of EVERY packet Fact's
    display + value + the identity/season-clock hard facts. The blob is for
    substring containment (numbers/multi-word names); the token set is a fast
    membership cache. Identity name/team/position/hometown are always grounded."""
    parts: list[str] = []
    # Identity hard facts (§4.1) — always grounded even though not Fact rows.
    ident = packet.identity or {}
    for k in ("name", "team", "position", "class_year", "jersey", "hometown"):
        v = ident.get(k)
        if v:
            parts.append(str(v))
    # The card's own resolved player name + team (belt-and-suspenders).
    for attr in ("player_name",):
        v = getattr(card, attr, None)
        if v:
            parts.append(str(v))
    im = getattr(card, "identity_meta", None)
    if isinstance(im, dict):
        for v in im.values():
            if v:
                parts.append(str(v))
    # Season clock numbers (the previewed + stats years are always grounded).
    sc = packet.season_clock or {}
    for v in sc.values():
        if v:
            parts.append(str(v))
    # Every Fact's display + stringified value.
    for section in packet.sections.values():
        for f in section:
            if f.display:
                parts.append(str(f.display))
            try:
                parts.append(json.dumps(f.value, ensure_ascii=False, default=str))
            except Exception:
                parts.append(str(f.value))
    blob = _normalize(" ".join(parts))
    # Token set: split the raw (non-normalized) corpus into word/number tokens,
    # normalize each — used for single-token name membership.
    raw = " ".join(parts)
    tokens = {_normalize(t) for t in re.split(r"\s+", raw) if t}
    tokens.discard("")
    return blob, tokens


def _candidate_claims(text: str) -> list[tuple[str, str]]:
    """Extract (kind, span) concrete claims from the card prose. kind in
    {'name','number','honor'}. De-dups while preserving order."""
    claims: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def _add(kind: str, span: str) -> None:
        span = span.strip()
        if not span:
            return
        key = (kind, span.lower())
        if key in seen:
            return
        seen.add(key)
        claims.append((kind, span))

    # Honors first (so "All-American" isn't shredded into name tokens).
    for m in _HONOR_RE.finditer(text):
        _add("honor", m.group(0))

    # Numbers.
    for m in _NUM_RE.finditer(text):
        _add("number", m.group(0))

    # Proper-name spans — drop spans that are ENTIRELY stopwords/sentence-initial
    # filler. A multi-word capitalized span (a real name) is kept; a lone
    # sentence-start capital that is a stopword is dropped.
    for m in _NAME_RE.finditer(text):
        span = m.group(1)
        words = span.split()
        # Keep only the sub-span of words that aren't stopwords; if nothing is
        # left, the whole span was filler (e.g. "The", "Now Tennessee" -> keep
        # "Tennessee"). We re-tokenize and add each surviving real token-group.
        content_words = [w for w in words if w.lower() not in _FAITH_STOPWORDS]
        if not content_words:
            continue
        # Re-join CONTIGUOUS content words as one name span (so "Nico Iamaleava"
        # stays one claim; a leading stopword like "The Vols" -> "Vols").
        contiguous: list[str] = []
        groups: list[str] = []
        for w in words:
            if w.lower() in _FAITH_STOPWORDS:
                if contiguous:
                    groups.append(" ".join(contiguous))
                    contiguous = []
            else:
                contiguous.append(w)
        if contiguous:
            groups.append(" ".join(contiguous))
        for g in groups:
            # A single short stopword-ish token that slipped through is skipped.
            if len(g) < 2:
                continue
            _add("name", g)
    return claims


def faithfulness_gate(card: Any, packet: Packet) -> FaithfulnessResult:
    """DETERMINISTIC per-card pass/fail (doc 59 §10.3). Every concrete claim in
    the rendered card must trace to a packet Fact source / display / value (or the
    identity hard facts). Unmapped concrete claims are flagged as potential
    hallucination spans. A card with ZERO concrete claims (pure templated filler)
    trivially passes (nothing to ground)."""
    text = card_full_text(card)
    if not text.strip():
        return FaithfulnessResult(
            passed=True, unsupported_spans=[], checked_spans=0,
            supported_spans=0, notes="empty card (no claims to ground)",
        )
    blob, tokens = _packet_search_corpus(card, packet)
    claims = _candidate_claims(text)
    unsupported: list[str] = []
    supported = 0
    for kind, span in claims:
        norm = _normalize(span)
        if not norm:
            continue
        ok = False
        if kind == "name":
            # Multi-token name: require the whole normalized span in the blob OR
            # every word-token present in the token set (handles re-ordered
            # "Iamaleava, Nico"). Single-token: token-set membership. A trailing
            # possessive ("Iamaleava's" / curly apostrophe) is stripped per-word
            # before matching so the possessive form of a grounded name passes.
            if norm in blob:
                ok = True
            else:
                words = [_strip_possessive(w) for w in span.split()]
                words = [_normalize(w) for w in words if _normalize(w)]
                ok = bool(words) and all(w in tokens or w in blob for w in words)
        else:
            # number / honor: normalized substring containment in the blob.
            ok = norm in blob
        if ok:
            supported += 1
        else:
            unsupported.append(span)

    passed = not unsupported
    notes = (
        f"all {supported} concrete claims grounded"
        if passed
        else f"{len(unsupported)} unsupported claim(s) of {len(claims)} checked"
    )
    return FaithfulnessResult(
        passed=passed,
        unsupported_spans=unsupported,
        checked_spans=len(claims),
        supported_spans=supported,
        notes=notes,
    )


# ===========================================================================
# MISSED-GOLD CRITIC (doc 59 §10.2). The judge sees the finished card + the
# ASSERTABLE (non-suppressed) packet facts and names the single best omitted
# fact/quote. Default judge = local Ollama mistral ($0); --judge sonnet routes
# to the Anthropic API. A NULL judge (no LLM available) falls back to a
# deterministic salience heuristic so the tool always produces a signal.
# ===========================================================================

# Per-fact salience prior for the deterministic fallback + to RANK what the judge
# is shown (the most newsworthy assertable facts first). Higher = more gold.
_SALIENCE: dict[str, float] = {
    "nil_narrative": 1.00,   # money/holdout — the headline angle
    "ledger_take": 0.95,     # the dominant fan take
    "honors": 0.90,          # consensus/unanimous AA etc.
    "succession": 0.85,      # the legend/bust/clock read
    "aura": 0.82,            # the BAN
    "award_watch": 0.78,     # forward Heisman/positional watch
    "transfer": 0.72,        # portal arc / drafted fate
    "before_after": 0.68,    # the production delta
    "depth_chart": 0.55,
    "recruiting": 0.50,
    "discourse": 0.45,       # raw firehose (the ledger_take is the distilled take)
}

# Honors/award facts get a bump for consensus/unanimous (the rarest gold).
def _fact_salience(section: str, f: Fact) -> float:
    base = _SALIENCE.get(section, 0.4)
    val = f.value if isinstance(f.value, dict) else {}
    if section == "honors" and (val.get("consensus_flag") or val.get("unanimous_flag")):
        base += 0.06
    if section == "nil_narrative" and val.get("reported_figure"):
        base += 0.05
    # A high-confidence fact is slightly better gold than a hedged one.
    base += 0.05 * float(getattr(f, "confidence", 0.0) or 0.0)
    return base


def _section_of_fact(packet: Packet, target: Fact) -> str:
    for name, facts in packet.sections.items():
        for f in facts:
            if f is target:
                return name
    return ""


def _rank_assertable(packet: Packet) -> list[tuple[float, str, Fact]]:
    """(salience, section, fact) for every assertable fact, most-gold first."""
    ranked: list[tuple[float, str, Fact]] = []
    for section, facts in packet.sections.items():
        for f in facts:
            if getattr(f, "suppressed", False):
                continue
            ranked.append((_fact_salience(section, f), section, f))
    ranked.sort(key=lambda t: t[0], reverse=True)
    return ranked


@dataclass
class MissedGoldResult:
    player_name: str
    omission: Optional[str]        # the judge's named omission (short string)
    omitted_source: Optional[str]  # the §4 section the omission came from
    omitted_source_id: Optional[str]
    judge: str                     # 'mistral' | 'sonnet' | 'heuristic' | 'none'
    rationale: str = ""
    suppressed_count: int = 0      # facts excluded from scope (silence is correct)


def _fact_brief(section: str, f: Fact) -> str:
    """A compact one-liner shown to the judge: section + display + source_id."""
    disp = (f.display or "").strip().replace("\n", " ")
    if len(disp) > 280:
        disp = disp[:277] + "..."
    val = ""
    if isinstance(f.value, dict) and f.value.get("reported_figure"):
        val = f" (reported figure: {f.value.get('reported_figure')})"
    return f"[{section}] {disp}{val}  <{f.source_id}>"


def _build_missed_gold_prompt(card: Any, packet: Packet, ranked: list[tuple[float, str, Fact]]) -> str:
    """The single-question judge prompt (doc 59 §10.2). System + user separated
    by a blank line so the Sonnet backend's _split_system_user finds them; the
    Ollama path takes the whole string."""
    fields = card_text_fields(card)
    name = (packet.identity or {}).get("name") or getattr(card, "player_name", "") or "this player"
    card_block = "\n".join(
        f"- {k}: {v}" for k, v in fields.items() if v
    ) or "- (the card shipped as a stats-strip with no prose)"
    # Show the top assertable facts (already suppression-filtered). Cap to keep
    # the prompt tight; the most-gold facts are first.
    fact_lines = [_fact_brief(sec, f) for _, sec, f in ranked[:40]]
    facts_block = "\n".join(fact_lines) or "(no assertable facts in the packet)"
    system = (
        "You are a ruthless CFB editorial critic. You are given a player's FINISHED "
        "story card (five fields) and the COMPLETE list of facts the writer was "
        "ALLOWED to use (already filtered to remove anything under a suppression "
        "rule). Your ONE job: name the single highest-value fact or quote in the "
        "packet that the card LEFT OUT. Pick the most newsworthy omission a CFB fan "
        "would most want surfaced. Reply with STRICT JSON only: "
        '{"omission": "<short phrase naming the missed fact>", '
        '"source_id": "<the <...> source_id of that fact, copied verbatim>", '
        '"rationale": "<one sentence: why it is the best omission>"}. '
        'If the card already used every high-value fact, reply '
        '{"omission": null, "source_id": null, "rationale": "card captured the gold"}.'
    )
    user = (
        f"PLAYER: {name}\n\n"
        f"THE FINISHED CARD:\n{card_block}\n\n"
        f"FACTS THE WRITER WAS ALLOWED TO USE (most newsworthy first; "
        f"suppressed facts already removed):\n{facts_block}\n\n"
        "What is the single highest-value fact or quote the card left out? "
        "Return STRICT JSON only."
    )
    return system + "\n\n" + user


def _ollama_judge(prompt: str) -> Optional[str]:
    """Run the missed-gold question on the local Ollama writer model ($0). Returns
    the raw response string or None on any failure. Reuses the narrator's URL +
    model so it tracks the same box config. NEVER raises."""
    try:
        import httpx
        from .story_card_narrator import OLLAMA_URL, WRITER_MODEL
    except Exception:
        return None
    body: dict[str, Any] = {
        "model": WRITER_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": {
            "type": "object",
            "properties": {
                "omission": {"type": ["string", "null"]},
                "source_id": {"type": ["string", "null"]},
                "rationale": {"type": "string"},
            },
            "required": ["omission", "rationale"],
        },
        "options": {"temperature": 0.2, "top_p": 0.9, "num_predict": 220},
        "keep_alive": "5m",
    }
    if "qwen3" in WRITER_MODEL.lower():
        body["think"] = False
    timeout = float(os.environ.get("CFB_INDEX_STORY_NARRATOR_TIMEOUT", "75"))
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{OLLAMA_URL.rstrip('/')}/api/generate",
                json=body,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
    except Exception:
        return None


def _sonnet_judge(prompt: str) -> Optional[str]:
    """Run the missed-gold question on Sonnet via the Anthropic API. Uses a raw
    Messages call (NOT AnthropicBackend.generate, whose output_config pins the
    five card fields — the judge needs a different JSON shape). NEVER raises.
    Returns the raw JSON text or None. Loads the key from config/env; NEVER echoes
    it."""
    try:
        from ..config import AppConfig
    except Exception:
        AppConfig = None  # type: ignore
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key and AppConfig is not None:
        try:
            key = getattr(AppConfig.from_env(), "anthropic_api_key", None)
        except Exception:
            key = None
    if not key:
        return None
    model = os.environ.get("CFB_INDEX_SONNET_MODEL") or "claude-sonnet-4-6"
    system, _, user = prompt.partition("\n\n")
    if not user:
        system, user = "", prompt
    schema = {
        "type": "object",
        "properties": {
            "omission": {"type": ["string", "null"]},
            "source_id": {"type": ["string", "null"]},
            "rationale": {"type": "string"},
        },
        "required": ["omission", "rationale"],
        "additionalProperties": False,
    }
    body: dict[str, Any] = {
        "model": model,
        "max_tokens": 300,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": user}],
        "output_config": {"format": {"type": "json_schema", "schema": schema}},
    }
    if system:
        body["system"] = system
    try:
        import httpx

        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                "https://api.anthropic.com/v1/messages", json=body, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
        for block in data.get("content") or []:
            if block.get("type") == "text" and block.get("text"):
                return block["text"]
    except Exception:
        return None
    return None


def _parse_judge_json(raw: Optional[str]) -> Optional[dict[str, Any]]:
    if not raw:
        return None
    text = str(raw).strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    try:
        obj = json.loads(text)
    except Exception:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            obj = json.loads(text[start : end + 1])
        except Exception:
            return None
    return obj if isinstance(obj, dict) else None


def _resolve_source(packet: Packet, source_id: Optional[str], omission: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Map the judge's named omission back to a (section, source_id) by matching
    the returned source_id verbatim, else by fuzzy display-overlap. Returns
    (section, source_id) — both None if unresolvable."""
    if source_id:
        sid = str(source_id).strip().strip("<>")
        for section, facts in packet.sections.items():
            for f in facts:
                if str(f.source_id) == sid:
                    return section, sid
    # Fuzzy: the omission phrase overlaps a fact's display the most.
    if omission:
        target = _normalize(omission)
        best: tuple[float, Optional[str], Optional[str]] = (0.0, None, None)
        for section, facts in packet.sections.items():
            for f in facts:
                if getattr(f, "suppressed", False):
                    continue
                disp = _normalize(f.display or "")
                if not disp or not target:
                    continue
                # crude containment / overlap score
                score = 0.0
                if target in disp or disp in target:
                    score = 1.0
                else:
                    a = set(re.findall(r"[a-z0-9]+", (omission or "").lower()))
                    b = set(re.findall(r"[a-z0-9]+", (f.display or "").lower()))
                    if a and b:
                        score = len(a & b) / len(a | b)
                if score > best[0]:
                    best = (score, section, str(f.source_id))
        if best[0] >= 0.3:
            return best[1], best[2]
    return None, None


def missed_gold_critic(
    card: Any,
    packet: Packet,
    *,
    judge: str = "mistral",
) -> MissedGoldResult:
    """Run the §10.2 missed-gold judge. ``judge`` in {'mistral','sonnet','heuristic'}.
    'mistral' tries the local Ollama path and falls back to the heuristic if the
    daemon is down; 'sonnet' tries the API and falls back likewise; 'heuristic'
    skips the LLM entirely (deterministic salience pick). RESPECTS SUPPRESSION:
    only assertable facts are shown to the judge / considered gold."""
    name = (packet.identity or {}).get("name") or getattr(card, "player_name", "") or "player"
    ranked = _rank_assertable(packet)
    n_suppressed = len(suppressed_facts(packet))

    if not ranked:
        return MissedGoldResult(
            player_name=name, omission=None, omitted_source=None,
            omitted_source_id=None, judge="none",
            rationale="no assertable facts in the packet (nothing to miss)",
            suppressed_count=n_suppressed,
        )

    prompt = _build_missed_gold_prompt(card, packet, ranked)

    used_judge = judge
    raw: Optional[str] = None
    if judge == "sonnet":
        raw = _sonnet_judge(prompt)
        if raw is None:
            used_judge = "heuristic"
    elif judge == "mistral":
        raw = _ollama_judge(prompt)
        if raw is None:
            used_judge = "heuristic"
    else:
        used_judge = "heuristic"

    if used_judge in ("sonnet", "mistral"):
        obj = _parse_judge_json(raw)
        if obj is not None:
            omission = obj.get("omission")
            omission = str(omission).strip() if omission not in (None, "", "null") else None
            rationale = str(obj.get("rationale") or "").strip()
            section, sid = _resolve_source(packet, obj.get("source_id"), omission)
            return MissedGoldResult(
                player_name=name, omission=omission, omitted_source=section,
                omitted_source_id=sid, judge=used_judge, rationale=rationale,
                suppressed_count=n_suppressed,
            )
        # parse failed -> fall back to heuristic so the tool still emits a signal.
        used_judge = "heuristic"

    # HEURISTIC fallback: the highest-salience assertable fact whose display text
    # is NOT already substantially present in the card prose is the missed gold.
    card_norm = _normalize(card_full_text(card))
    for sal, section, f in ranked:
        disp = (f.display or "").strip()
        if not disp:
            continue
        # Is this fact already captured? Use a few salient tokens from the display.
        toks = [_normalize(t) for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9'.-]{2,}", disp)]
        toks = [t for t in toks if t][:6]
        if toks and sum(1 for t in toks if t in card_norm) >= max(1, len(toks) // 2):
            continue  # already substantially in the card
        return MissedGoldResult(
            player_name=name,
            omission=disp if len(disp) <= 160 else disp[:157] + "...",
            omitted_source=section,
            omitted_source_id=str(f.source_id),
            judge="heuristic",
            rationale=f"highest-salience assertable {section} fact not present in the card",
            suppressed_count=n_suppressed,
        )
    return MissedGoldResult(
        player_name=name, omission=None, omitted_source=None,
        omitted_source_id=None, judge="heuristic",
        rationale="every assertable fact is already substantially in the card",
        suppressed_count=n_suppressed,
    )


# ===========================================================================
# PER-PLAYER + AGGREGATE ORCHESTRATION (doc 59 §10 — reference-free, scales to a
# rotating top-50). evaluate_player builds the packet + the live card and runs
# both gates. run_card_eval runs a sample and prints/returns the quality report
# with the aggregate 'most-missed source'.
# ===========================================================================
@dataclass
class CardEval:
    player_id: int
    external_id: Optional[str]
    player_name: str
    season: int
    faithfulness: Optional[FaithfulnessResult]
    missed_gold: Optional[MissedGoldResult]
    error: Optional[str] = None


def evaluate_player(
    db,
    player_id: int,
    season: int,
    *,
    judge: str = "mistral",
    upcoming_season: int = 2026,
) -> CardEval:
    """Build the live card + the packet for one player and run BOTH gates.
    NEVER raises (read-only). On any failure returns a CardEval with ``error``."""
    try:
        ext = resolve_external_id(db, player_id)
    except Exception:
        ext = None
    try:
        card = build_card_payload(db, player_id, season)
    except Exception as exc:
        return CardEval(
            player_id=player_id, external_id=ext, player_name=f"player:{player_id}",
            season=season, faithfulness=None, missed_gold=None,
            error=f"card build failed: {type(exc).__name__}",
        )
    if card is None or not ext:
        return CardEval(
            player_id=player_id, external_id=ext, player_name=f"player:{player_id}",
            season=season, faithfulness=None, missed_gold=None,
            error="no stable anchor / no card payload",
        )
    try:
        packet = build_packet(db, ext, season, upcoming_season=upcoming_season)
    except Exception as exc:
        return CardEval(
            player_id=player_id, external_id=ext,
            player_name=getattr(card, "player_name", f"player:{player_id}"),
            season=season, faithfulness=None, missed_gold=None,
            error=f"packet build failed: {type(exc).__name__}",
        )
    name = (
        (packet.identity or {}).get("name")
        or getattr(card, "player_name", None)
        or f"player:{player_id}"
    )
    faith = faithfulness_gate(card, packet)
    gold = missed_gold_critic(card, packet, judge=judge)
    return CardEval(
        player_id=player_id, external_id=ext, player_name=name, season=season,
        faithfulness=faith, missed_gold=gold, error=None,
    )


def _resolve_sample(db, players: Optional[list[int]], top_n: int, season: int) -> list[int]:
    """Resolve the player_id sample: explicit --players, else the top-N most
    talked-about (reuse the coverage ratchet's top-50 selector)."""
    if players:
        return [int(p) for p in players]
    # Reuse the coverage ratchet's exact top-50 selector for parity with §8.
    try:
        import sys
        from pathlib import Path

        scripts_dir = Path(__file__).resolve().parents[3] / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        import coverage_ratchet_story_cards as crsc  # type: ignore

        top = crsc.build_top50(db, season)
        return [int(p["player_id"]) for p in top[: max(1, top_n)]]
    except Exception:
        # Fallback: latest-week aura mention_count DESC.
        try:
            rows = db.query_all(
                """
                SELECT paw.player_id
                  FROM player_aura_weekly paw
                 INNER JOIN (
                       SELECT player_id, MAX(week) AS mw
                         FROM player_aura_weekly
                        WHERE season_year = :s AND COALESCE(is_low_signal,0)=0
                        GROUP BY player_id
                 ) l ON l.player_id = paw.player_id AND l.mw = paw.week
                 WHERE paw.season_year = :s AND COALESCE(paw.is_low_signal,0)=0
                 ORDER BY paw.mention_count DESC
                 LIMIT :n
                """,
                {"s": season, "n": max(1, top_n)},
            ) or []
            return [int(r["player_id"]) for r in rows if r.get("player_id") is not None]
        except Exception:
            return []


def run_card_eval(
    db,
    *,
    players: Optional[list[int]] = None,
    top_n: int = 12,
    judge: str = "mistral",
    season: Optional[int] = None,
    upcoming_season: int = 2026,
    print_report: bool = True,
) -> dict[str, Any]:
    """Run the missed-gold critic + faithfulness gate over a sample and return
    (and optionally print) the quality report (doc 59 §10). The aggregate carries
    the FAITHFULNESS pass-rate + the 'most-missed source' across the sample."""
    if season is None:
        try:
            from .. import reporting as R

            summary, _ = R.fetch_latest_rankings(db, limit=1)
            season = int(summary["season_year"])
        except Exception:
            from .season_labels import _last_completed_season
            import datetime as _dt

            season = _last_completed_season(_dt.date.today())

    sample = _resolve_sample(db, players, top_n, int(season))
    results: list[CardEval] = []
    for pid in sample:
        results.append(
            evaluate_player(db, pid, int(season), judge=judge, upcoming_season=upcoming_season)
        )

    # Aggregate.
    evaluated = [r for r in results if r.error is None and r.faithfulness is not None]
    n_eval = len(evaluated)
    faith_pass = sum(1 for r in evaluated if r.faithfulness and r.faithfulness.passed)
    missed_source_counts: dict[str, int] = {}
    n_with_omission = 0
    for r in evaluated:
        mg = r.missed_gold
        if mg and mg.omission and mg.omitted_source:
            n_with_omission += 1
            missed_source_counts[mg.omitted_source] = missed_source_counts.get(mg.omitted_source, 0) + 1
    most_missed = sorted(missed_source_counts.items(), key=lambda kv: kv[1], reverse=True)

    report: dict[str, Any] = {
        "season": int(season),
        "judge": judge,
        "sample_size": len(sample),
        "evaluated": n_eval,
        "errors": len(results) - n_eval,
        "faithfulness_pass": faith_pass,
        "faithfulness_pass_rate": round(faith_pass / n_eval, 4) if n_eval else 0.0,
        "players_with_missed_gold": n_with_omission,
        "most_missed_source": most_missed[0][0] if most_missed else None,
        "missed_source_counts": dict(most_missed),
        "per_player": [
            {
                "player_id": r.player_id,
                "external_id": r.external_id,
                "name": r.player_name,
                "error": r.error,
                "faithfulness_passed": (r.faithfulness.passed if r.faithfulness else None),
                "unsupported_spans": (r.faithfulness.unsupported_spans if r.faithfulness else []),
                "checked_spans": (r.faithfulness.checked_spans if r.faithfulness else 0),
                "missed_gold": (
                    {
                        "omission": r.missed_gold.omission,
                        "source": r.missed_gold.omitted_source,
                        "source_id": r.missed_gold.omitted_source_id,
                        "judge": r.missed_gold.judge,
                        "rationale": r.missed_gold.rationale,
                        "suppressed_count": r.missed_gold.suppressed_count,
                    }
                    if r.missed_gold else None
                ),
            }
            for r in results
        ],
    }

    if print_report:
        _print_report(report)
    return report


def _print_report(report: dict[str, Any]) -> None:
    print(f"Card Quality Report — Season {report['season']} (judge: {report['judge']})")
    print("=" * 68)
    print(
        f"Sample: {report['sample_size']}  Evaluated: {report['evaluated']}  "
        f"Errors: {report['errors']}"
    )
    print(
        f"Faithfulness: {report['faithfulness_pass']}/{report['evaluated']} pass "
        f"({report['faithfulness_pass_rate']:.0%})"
    )
    mm = report["most_missed_source"]
    print(
        f"Most-missed source across sample: {mm or '(none — cards captured the gold)'}"
    )
    if report["missed_source_counts"]:
        counts = ", ".join(f"{k}={v}" for k, v in report["missed_source_counts"].items())
        print(f"  Missed-source tally: {counts}")
    print("-" * 68)
    for p in report["per_player"]:
        if p["error"]:
            print(f"  {p['name']!r:<34} ERROR: {p['error']}")
            continue
        faith = "PASS" if p["faithfulness_passed"] else "FAIL"
        mg = p["missed_gold"] or {}
        omission = mg.get("omission")
        src = mg.get("source")
        line = f"  {p['name']!r:<34} faith={faith}"
        if not p["faithfulness_passed"]:
            line += f" unsupported={p['unsupported_spans']}"
        print(line)
        if omission:
            print(
                f"      missed-gold [{src}]: {omission}"
                f"  (judge={mg.get('judge')}, suppressed={mg.get('suppressed_count')})"
            )
        else:
            print(
                f"      missed-gold: (none — {mg.get('rationale','captured the gold')})"
            )


__all__ = [
    "FaithfulnessResult",
    "MissedGoldResult",
    "CardEval",
    "card_text_fields",
    "card_full_text",
    "assertable_facts",
    "suppressed_facts",
    "faithfulness_gate",
    "missed_gold_critic",
    "evaluate_player",
    "run_card_eval",
]
