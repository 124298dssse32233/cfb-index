"""The 25 Best Calls of <year> — annual canonical list (Sprint 13 Phase 7).

Selection logic:
    * From predictive_claims with outcome_resolved = 1 and verdict = 'hit',
      season-year matching, sort by surprise_index DESC; pick top 25.
    * Sonnet writes editorial paragraph + pull quote per entry.
    * Opus writes the top 3 entries (highest-surprise hits) for voice-tier
      copy. Bound by the 15% Opus budget guardrail.
    * Voice validator passes copy through banned-phrase + Surprise-Index-token
      check. Failures are flagged and tagged but not auto-rewritten.
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Sequence

from . import voice_validator
from .runtime import db_conn


@dataclass
class BestCallEntry:
    rank: int
    claim_id: int
    title: str
    paragraph: str
    pull_quote: str | None
    model: str
    voice_passed: bool
    voice_notes: str


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def _passes_precision_filter(row: sqlite3.Row) -> bool:
    """Drop entries the offline resolver mis-classified.

    The offline resolver has two known precision gaps (documented in the
    sprint report): (1) game-resolver counts winner-mention-anywhere as a
    hit (so "FSU will beat Virginia" + Virginia winning still resolves hit
    because Virginia appears in the claim text), and (2) playoff_bid +
    record resolvers can fire on the empty 2026 season, producing
    "finished 0-0 in 2026" outcome strings that aren't real outcomes.
    Until the resolver is hardened, this filter excludes obvious
    mis-resolutions from editorial selection so we don't celebrate
    non-hits.
    """
    text = (row["claim_text"] or "").lower()
    outcome = (row["outcome_text"] or "").lower()
    # 1. Empty-2026 artifacts.
    if "finished 0-0 in 2026" in outcome:
        return False
    if "unranked all season 2026" in outcome:
        return False
    # 2. Locked-On podcast feed *episode descriptions* aren't predictions —
    # they're show notes. Filter the worst pattern: a single sentence that
    # ends with "?" (rhetorical question) or contains "is joined by"
    # (host introduction) or "Skull Session:" (link aggregator).
    if " is joined by " in text:
        return False
    if "skull session:" in text:
        return False
    if text.strip().endswith("?") and "will " in text and "podcast" in text:
        return False
    # Bare title-case "Will X DO Y?" chyron-style is filter-worthy.
    if text.strip().endswith("?") and any(w in text for w in (
        "shakes ", "shock ", "exploit ", "revolt", "explode", "patch",
    )):
        return False
    # 3. Game-resolver false positive: predicted-loser mentioned in claim
    # but actual winner was the OTHER team. Detect by checking if the
    # predicted-winner phrase ("X will beat Y" / "X to win" / "X over Y")
    # has an explicit subject-verb pattern AND that subject lost.
    # Skipped here at SQL-filter level; we'll do this at hand-curation.
    return True


def select_best_calls(season_year: int, *, n: int = 25, min_surprise: float = 30.0) -> list[sqlite3.Row]:
    with db_conn(read_only=True) as conn:
        rows = conn.execute("""
            SELECT * FROM predictive_claims
             WHERE outcome_resolved = 1
               AND outcome_verdict = 'hit'
               AND surprise_index IS NOT NULL
               AND surprise_index >= ?
               AND CAST(strftime('%Y', source_published_at) AS INTEGER) BETWEEN ? AND ?
             ORDER BY surprise_index DESC, aged_well_pct DESC
             LIMIT ?
        """, (min_surprise, season_year - 1, season_year, n * 4)).fetchall()
    filtered = [r for r in rows if _passes_precision_filter(r)]
    return filtered[:n]


def select_aged_poorly(season_year: int, *, n: int = 10, min_surprise: float = 30.0) -> list[sqlite3.Row]:
    """Companion list — gentle framing, not gotcha."""
    with db_conn(read_only=True) as conn:
        rows = conn.execute("""
            SELECT * FROM predictive_claims
             WHERE outcome_resolved = 1
               AND outcome_verdict = 'miss'
               AND surprise_index IS NOT NULL
               AND surprise_index >= ?
               AND CAST(strftime('%Y', source_published_at) AS INTEGER) BETWEEN ? AND ?
             ORDER BY surprise_index DESC
             LIMIT ?
        """, (min_surprise, season_year - 1, season_year, n * 4)).fetchall()
        filtered = [r for r in rows if _passes_precision_filter(r)]
        return filtered[:n]


# ---------------------------------------------------------------------------
# Editorial generation (Sonnet / Opus / offline stub)
# ---------------------------------------------------------------------------

_SONNET_SYSTEM = """You are an editorial writer for CFB Index Receipts — the section
that surfaces predictive takes that landed and the sources who made them. The
voice is celebratory, quantified, and respectful: never gotcha, never anonymous.

For the take you're handed, write:
  TITLE: a 4-8 word headline. Concrete. Names the predictor or the predicted thing.
  PARAGRAPH: one paragraph (60-110 words) that:
    - opens by naming the predictor and where/when they made the call
    - quotes the original claim verbatim, in quotation marks
    - states the actual outcome with one specific number
    - names the Surprise Index score and what made the call unlikely at the time
    - closes with one editorial sentence honoring what they saw before others did
  PULL_QUOTE: 6-12 words extracted from the predictor's verbatim claim.

Output strict JSON: {"title": "...", "paragraph": "...", "pull_quote": "..."}"""

_OPUS_SYSTEM = _SONNET_SYSTEM + """

Voice tier: marquee. This is one of the top-3 surprises of the year. Lift the
prose without becoming purple. Anchor the magnitude in a comparable historical
moment if natural. Keep the structure identical to the Sonnet template."""


def _have_anthropic() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _client():
    import anthropic  # noqa: WPS433
    return anthropic.Anthropic()


def _claim_brief(claim: sqlite3.Row) -> str:
    try:
        ents = json.loads(claim["entities_mentioned_json"] or "{}")
    except json.JSONDecodeError:
        ents = {}
    return (
        f"source_slug: {claim['source_slug']}\n"
        f"source_kind: {claim['source_kind']}\n"
        f"published_at: {claim['source_published_at']}\n"
        f"verbatim_claim: {claim['claim_text']}\n"
        f"summary: {claim['claim_summary_short']}\n"
        f"prediction_kind: {claim['prediction_kind']}\n"
        f"surprise_index: {claim['surprise_index']}\n"
        f"verdict: {claim['outcome_verdict']}\n"
        f"outcome_text: {claim['outcome_text']}\n"
        f"aged_well_pct: {claim['aged_well_pct']}\n"
        f"entities: {ents}"
    )


def _llm_write(claim: sqlite3.Row, *, tier: str) -> tuple[dict[str, Any], str]:
    """tier in {'sonnet','opus'}. Falls back to stub when offline."""
    if not _have_anthropic():
        return _stub_write(claim, tier=tier), f"stub:{tier}"
    try:
        client = _client()
    except ImportError:
        return _stub_write(claim, tier=tier), f"stub:{tier}"
    model = (
        os.environ.get("RECEIPTS_OPUS_MODEL", "claude-opus-4-5")
        if tier == "opus" else
        os.environ.get("RECEIPTS_SONNET_MODEL", "claude-sonnet-4-5")
    )
    system = _OPUS_SYSTEM if tier == "opus" else _SONNET_SYSTEM
    resp = client.messages.create(
        model=model,
        max_tokens=900,
        system=system,
        messages=[{"role": "user", "content": _claim_brief(claim)}],
    )
    text = "".join(b.text for b in resp.content if hasattr(b, "text"))
    try:
        obj = json.loads(text[text.index("{"):text.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        return _stub_write(claim, tier=tier), f"parse_error:{tier}"
    return obj, model


def _stub_write(claim: sqlite3.Row, *, tier: str) -> dict[str, Any]:
    """Offline editorial — terse but conformant to the contract."""
    surp = claim["surprise_index"] or 0
    program = ""
    try:
        ents = json.loads(claim["entities_mentioned_json"] or "{}")
        program = (ents.get("programs") or [""])[0] or ""
    except json.JSONDecodeError:
        pass
    title_subject = program.replace("-", " ").title() if program else claim["prediction_kind"].replace("_", " ").title()
    title = f"The {title_subject} Call"
    pred_text = claim["claim_text"] or ""
    quote_words = pred_text.split()
    pull = " ".join(quote_words[:10])
    paragraph = (
        f"{claim['source_slug'].replace('-', ' ').title()} called this on "
        f"{claim['source_published_at'][:10]}: \"{pred_text}\". "
        f"What followed: {claim['outcome_text']} "
        f"Surprise Index of {surp:.0f} — well above what the consensus expected at the time of the take. "
        f"Credit where due: this one landed before the rest of the room saw it coming."
    )
    return {"title": title, "paragraph": paragraph, "pull_quote": pull}


def _validate(entry: dict[str, Any]) -> tuple[bool, str]:
    full = f"{entry.get('title','')} {entry.get('paragraph','')} {entry.get('pull_quote','')}"
    result = voice_validator.validate(
        full, require_tokens=voice_validator.REQUIRED_TOKENS_BEST_CALLS,
    )
    return result.passed, result.notes


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def generate(season_year: int, *, n: int = 25, opus_top: int = 3) -> dict[str, Any]:
    selections = select_best_calls(season_year, n=n)
    if not selections:
        return {"season_year": season_year, "entries": 0, "note": "no_resolved_hits"}

    entries: list[BestCallEntry] = []
    voice_pass = 0
    with db_conn() as conn:
        # Wipe prior list for this season+kind so reruns are idempotent.
        conn.execute(
            "DELETE FROM receipts_annual_lists WHERE season_year = ? AND list_kind = 'best_calls'",
            (season_year,),
        )
        conn.commit()

        for rank, claim in enumerate(selections, start=1):
            tier = "opus" if rank <= opus_top else "sonnet"
            payload, model = _llm_write(claim, tier=tier)
            passed, notes = _validate(payload)
            entry = BestCallEntry(
                rank=rank, claim_id=int(claim["id"]),
                title=payload.get("title", ""),
                paragraph=payload.get("paragraph", ""),
                pull_quote=payload.get("pull_quote"),
                model=model, voice_passed=passed, voice_notes=notes,
            )
            entries.append(entry)
            if passed:
                voice_pass += 1
            conn.execute("""
                INSERT INTO receipts_annual_lists (
                    season_year, list_kind, rank, claim_id,
                    editorial_title, editorial_paragraph, editorial_pull_quote,
                    editorial_model, voice_validator_passed, voice_validator_notes
                ) VALUES (?, 'best_calls', ?, ?, ?, ?, ?, ?, ?, ?)
            """, (season_year, rank, entry.claim_id, entry.title,
                  entry.paragraph, entry.pull_quote, entry.model,
                  1 if passed else 0, notes))
        conn.commit()

    # Companion list: aged-poorly (gentle).
    aged = select_aged_poorly(season_year)
    aged_entries = []
    with db_conn() as conn:
        conn.execute(
            "DELETE FROM receipts_annual_lists WHERE season_year = ? AND list_kind = 'aged_poorly'",
            (season_year,),
        )
        for rank, claim in enumerate(aged, start=1):
            payload, model = _llm_write(claim, tier="sonnet")
            passed, notes = _validate(payload)
            aged_entries.append(payload)
            conn.execute("""
                INSERT INTO receipts_annual_lists (
                    season_year, list_kind, rank, claim_id,
                    editorial_title, editorial_paragraph, editorial_pull_quote,
                    editorial_model, voice_validator_passed, voice_validator_notes
                ) VALUES (?, 'aged_poorly', ?, ?, ?, ?, ?, ?, ?, ?)
            """, (season_year, rank, int(claim["id"]),
                  payload.get("title", ""), payload.get("paragraph", ""),
                  payload.get("pull_quote"), model,
                  1 if passed else 0, notes))
        conn.commit()

    pass_rate = voice_pass / max(1, len(entries))
    return {
        "season_year": season_year,
        "entries": len(entries),
        "aged_poorly": len(aged_entries),
        "opus_top": opus_top,
        "voice_pass_rate": round(pass_rate, 4),
        "mode": "online" if _have_anthropic() else "offline_stub",
    }
