"""Source profile aggregation + bio writing (Sprint 13).

For each source_slug with at least N tracked claims, recompute:
    * receipt_score_pct (weighted by surprise_index)
    * takes_tracked / resolved / hit / miss / partial
    * cohort_lean (stat-leaning vs casual-leaning, by program-focus distribution)
    * voice_summary (Sonnet — or stubbed offline)
    * longest_long_shot_id, most_aged_poorly_id

Bio writing is offline-stub by default; flips to Sonnet when ANTHROPIC_API_KEY
is set. Volume target: top-50 most-cited sources.
"""
from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter
from dataclasses import dataclass
from typing import Any, Sequence

from .runtime import db_conn, slugify


@dataclass
class SourceAggregate:
    source_slug: str
    display_name: str
    role_label: str | None
    takes_tracked: int
    takes_resolved: int
    takes_hit: int
    takes_miss: int
    takes_partial: int
    receipt_score_pct: float
    last_take_at: str | None
    cohort_lean: str
    program_focus_slugs: list[str]
    longest_long_shot_id: int | None
    most_aged_poorly_id: int | None


def _aggregate_source(conn: sqlite3.Connection, source_slug: str) -> SourceAggregate | None:
    rows = conn.execute("""
        SELECT id, source_kind, source_slug, source_url, source_published_at,
               claim_text, claim_summary_short, prediction_kind, surprise_index,
               outcome_resolved, outcome_verdict, aged_well_pct,
               entities_mentioned_json
          FROM predictive_claims
         WHERE source_slug = ?
         ORDER BY source_published_at DESC
    """, (source_slug,)).fetchall()
    if not rows:
        return None
    n = len(rows)
    resolved = [r for r in rows if r["outcome_resolved"]]
    hit = sum(1 for r in resolved if r["outcome_verdict"] == "hit")
    miss = sum(1 for r in resolved if r["outcome_verdict"] == "miss")
    partial = sum(1 for r in resolved if r["outcome_verdict"] == "partial")
    score = _receipt_score(resolved)
    long_shot_id = _highest(resolved, hit_only=True, key="surprise_index")
    aged_poorly_id = _highest(resolved, hit_only=False, key="surprise_index", verdict="miss")
    programs = _program_focus(rows)
    cohort_lean = _cohort_lean(rows)
    last_at = rows[0]["source_published_at"]
    return SourceAggregate(
        source_slug=source_slug,
        display_name=_display_name_from_slug(source_slug),
        role_label=_role_label_from_rows(rows),
        takes_tracked=n,
        takes_resolved=len(resolved),
        takes_hit=hit,
        takes_miss=miss,
        takes_partial=partial,
        receipt_score_pct=score,
        last_take_at=last_at,
        cohort_lean=cohort_lean,
        program_focus_slugs=programs,
        longest_long_shot_id=long_shot_id,
        most_aged_poorly_id=aged_poorly_id,
    )


def _receipt_score(resolved: Sequence[sqlite3.Row]) -> float:
    if not resolved:
        return 0.0
    weights = [max(1.0, (r["surprise_index"] or 1.0)) for r in resolved]
    aged = [(r["aged_well_pct"] or 0.0) for r in resolved]
    if not weights:
        return 0.0
    weighted_sum = sum(w * a for w, a in zip(weights, aged))
    return round(weighted_sum / sum(weights), 1)


def _highest(rows: Sequence[sqlite3.Row], *, hit_only: bool, key: str, verdict: str | None = None) -> int | None:
    best: sqlite3.Row | None = None
    for r in rows:
        if hit_only and r["outcome_verdict"] != "hit":
            continue
        if verdict and r["outcome_verdict"] != verdict:
            continue
        if r[key] is None:
            continue
        if best is None or r[key] > best[key]:
            best = r
    return int(best["id"]) if best else None


def _program_focus(rows: Sequence[sqlite3.Row]) -> list[str]:
    counter: Counter[str] = Counter()
    for r in rows:
        try:
            ents = json.loads(r["entities_mentioned_json"] or "{}")
        except json.JSONDecodeError:
            ents = {}
        for slug in ents.get("programs", []) or []:
            counter[slug] += 1
    return [slug for slug, _ in counter.most_common(8)]


def _cohort_lean(rows: Sequence[sqlite3.Row]) -> str:
    """Heuristic: stat-leaning if 'sp+' / 'rating' / 'efficiency' appear,
    casual-leaning if vibes-laden words dominate, else balanced."""
    stat = casual = 0
    for r in rows:
        text = (r["claim_text"] or "").lower()
        if any(w in text for w in ("sp+", "fei", "havoc", "advanced", "efficiency", "epa")):
            stat += 1
        if any(w in text for w in ("vibes", "energy", "swag", "feeling", "doomed", "cooked")):
            casual += 1
    if stat > casual * 2:
        return "stat-leaning"
    if casual > stat * 2:
        return "casual-leaning"
    return "balanced"


def _display_name_from_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-"))


def _role_label_from_rows(rows: Sequence[sqlite3.Row]) -> str | None:
    kinds = Counter(r["source_kind"] for r in rows)
    top, _ = kinds.most_common(1)[0]
    return {
        "beat_writer": "BEAT WRITER",
        "podcast": "PODCAST",
        "board_post": "MESSAGE BOARD",
        "reddit": "REDDIT",
        "bluesky": "BLUESKY",
        "official_release": "OFFICIAL RELEASE",
        "our_chronicle": "CFB INDEX · CHRONICLE",
        "our_canon": "CFB INDEX · CANON",
    }.get(top, top.upper().replace("_", " "))


# ---------------------------------------------------------------------------
# Voice summary: Sonnet (online) or heuristic stub (offline).
# ---------------------------------------------------------------------------

_VOICE_SYSTEM = """You are an editorial profile writer for CFB Index Receipts.

Given a source's predictive-claim history (titles, kinds, hit/miss verdicts,
surprise scores), produce a 2-sentence voice characterization that:
  * Names what kinds of predictions this source makes (e.g. "leans on advanced
    stats; recurring conviction about Big Ten title contenders").
  * Notes their batting average + their most-distinctive long shot if any.
  * Avoids gotcha tone — celebratory or measured even when describing misses.

Output plain text, 2 sentences, no markdown."""


def _voice_summary(
    agg: SourceAggregate, sample: Sequence[sqlite3.Row],
    *,
    _meter: Any = None,
) -> str:
    """Generate a short voice/style summary for a tracked Receipts source.

    ``_meter`` (Pattern A, optional): records this Sonnet call's cost.

    Routes to a local LLM (zero API cost) when LOCAL_LLM_URL is set;
    the 2-sentence plain-text task is a good local-model candidate.
    """
    from cfb_rankings.llm_local import is_local_enabled, local_generate
    from cfb_rankings.llm_runtime import CostMeter
    meter = _meter or CostMeter(
        ceiling_usd=0.3,
        label=f"receipts.source_voice.{agg.source_slug}",
    )

    bullets = "\n".join(
        f"- ({r['outcome_verdict'] or 'pending'}, surprise={r['surprise_index'] or 0:.0f}) "
        f"{r['claim_summary_short'][:140]}"
        for r in sample[:8]
    )
    user = (
        f"source_slug: {agg.source_slug}\n"
        f"display_name: {agg.display_name}\n"
        f"role_label: {agg.role_label}\n"
        f"takes_tracked: {agg.takes_tracked} / resolved: {agg.takes_resolved}\n"
        f"hit/miss/partial: {agg.takes_hit}/{agg.takes_miss}/{agg.takes_partial}\n"
        f"receipt_score_pct: {agg.receipt_score_pct}\n"
        f"cohort_lean: {agg.cohort_lean}\n"
        f"program_focus: {agg.program_focus_slugs}\n\n"
        f"Sample claims:\n{bullets}"
    )

    # Local path — 2-sentence editorial summary with no API cost
    if is_local_enabled():
        result = local_generate(
            user,
            system=_VOICE_SYSTEM,
            max_tokens=240,
            temperature=0.5,   # Mild creativity for editorial voice
        )
        if result["text"]:
            return result["text"].strip() or _stub_voice_summary(agg, sample)
        return _stub_voice_summary(agg, sample)

    # Anthropic SDK path
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _stub_voice_summary(agg, sample)
    try:
        import anthropic  # noqa: WPS433
    except ImportError:
        return _stub_voice_summary(agg, sample)
    client = anthropic.Anthropic()
    model_id = os.environ.get("RECEIPTS_SONNET_MODEL", "claude-sonnet-4-6")
    resp = client.messages.create(
        model=model_id,
        max_tokens=240,
        system=_VOICE_SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    if getattr(resp, "usage", None) is not None:
        meter.record(model_id, resp.usage, note="receipts.source_voice")
    text = "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
    return text or _stub_voice_summary(agg, sample)


def _stub_voice_summary(agg: SourceAggregate, sample: Sequence[sqlite3.Row]) -> str:
    if agg.cohort_lean == "stat-leaning":
        flavor = "leans on advanced metrics"
    elif agg.cohort_lean == "casual-leaning":
        flavor = "writes from feel and storyline"
    else:
        flavor = "splits between numbers and narrative"
    focus = ", ".join(agg.program_focus_slugs[:3]) if agg.program_focus_slugs else "varied programs"
    if agg.takes_resolved:
        bat = f"{agg.receipt_score_pct:.0f}% aged-well across {agg.takes_resolved} resolved takes"
    else:
        bat = f"{agg.takes_tracked} tracked, none yet resolved"
    return (
        f"{agg.display_name} {flavor}, with recurring focus on {focus}. "
        f"Receipts so far: {bat}."
    )


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def recompute_all(
    *, min_takes: int = 3, top_n: int = 50,
    _meter: Any = None,
) -> dict[str, int]:
    """Recompute source_profiles for every slug with >= min_takes claims.

    Bios are written for the top_n most-cited sources only (cost control).

    ``_meter`` (Pattern C, optional): single meter spans every voice_summary
    call. Defaults to a per-invocation meter sized for the full top_n run.
    """
    from cfb_rankings.llm_runtime import CostMeter
    meter = _meter or CostMeter(
        ceiling_usd=0.3,
        label="receipts.source_profiles.recompute_all",
    )
    n = 0
    bios = 0
    with db_conn() as conn:
        slugs = [r[0] for r in conn.execute("""
            SELECT source_slug FROM predictive_claims
             GROUP BY source_slug HAVING COUNT(*) >= ?
             ORDER BY COUNT(*) DESC
        """, (min_takes,)).fetchall()]
        for idx, slug in enumerate(slugs):
            agg = _aggregate_source(conn, slug)
            if not agg:
                continue
            sample = conn.execute("""
                SELECT * FROM predictive_claims
                 WHERE source_slug = ?
                 ORDER BY surprise_index DESC NULLS LAST
                 LIMIT 8
            """, (slug,)).fetchall()
            voice = _voice_summary(agg, sample, _meter=meter) if idx < top_n else None
            if voice:
                bios += 1
            conn.execute("""
                INSERT INTO source_profiles (
                    source_slug, display_name, role_label, bio,
                    receipt_score_pct, receipt_score_label,
                    takes_tracked, takes_resolved, takes_hit, takes_miss, takes_partial,
                    last_take_at, cohort_lean, program_focus_slugs_json,
                    voice_summary, longest_long_shot_id, most_aged_poorly_id,
                    profile_published, last_recomputed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(source_slug) DO UPDATE SET
                    display_name = excluded.display_name,
                    role_label = excluded.role_label,
                    receipt_score_pct = excluded.receipt_score_pct,
                    receipt_score_label = excluded.receipt_score_label,
                    takes_tracked = excluded.takes_tracked,
                    takes_resolved = excluded.takes_resolved,
                    takes_hit = excluded.takes_hit,
                    takes_miss = excluded.takes_miss,
                    takes_partial = excluded.takes_partial,
                    last_take_at = excluded.last_take_at,
                    cohort_lean = excluded.cohort_lean,
                    program_focus_slugs_json = excluded.program_focus_slugs_json,
                    voice_summary = COALESCE(excluded.voice_summary, source_profiles.voice_summary),
                    longest_long_shot_id = excluded.longest_long_shot_id,
                    most_aged_poorly_id = excluded.most_aged_poorly_id,
                    profile_published = 1,
                    last_recomputed_at = CURRENT_TIMESTAMP
            """, (
                agg.source_slug, agg.display_name, agg.role_label,
                voice,  # bio = voice for now (single short paragraph)
                agg.receipt_score_pct, _score_label(agg.receipt_score_pct),
                agg.takes_tracked, agg.takes_resolved, agg.takes_hit,
                agg.takes_miss, agg.takes_partial,
                agg.last_take_at, agg.cohort_lean,
                json.dumps(agg.program_focus_slugs),
                voice, agg.longest_long_shot_id, agg.most_aged_poorly_id, 1,
            ))
            n += 1
        conn.commit()
    return {"profiles_updated": n, "bios_written": bios}


def _score_label(pct: float) -> str:
    if pct >= 80:
        return "AGED WELL"
    if pct >= 60:
        return "MOSTLY HOLDS UP"
    if pct >= 40:
        return "SPLIT DECISIONS"
    if pct >= 20:
        return "MIXED RESULTS"
    return "EARLY RETURNS"
