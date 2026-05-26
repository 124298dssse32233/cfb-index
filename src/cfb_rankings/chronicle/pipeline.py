"""Chronicle five-agent pipeline orchestrator.

Wires Planner -> Writer -> FactCritic -> VoiceCritic -> CollisionCritic -> Refiner
into one cohesive flow. Each stage uses pre-built chronicle modules.

Tier-aware: Tier S gets Best-of-3 on Writer + 1 refine retry; T3 gets single-pass
with reduced thresholds. Cache-checked via chronicle.cache; LKG-promoted on pass.

Public API:
    generate_page_cards(db, target, router, config) -> PageResult
    generate_card(db, brief, evidence, evidence_hash, target, ...) -> CardResult
    run_tier_batch(db, tier, router, config, max_cards, ...) -> list[PageResult]
    PipelineConfig.for_tier(tier) -> PipelineConfig
"""
from __future__ import annotations

import concurrent.futures
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from cfb_rankings.chronicle.antislop import (
    BanEntry,
    apply_antislop_to_config,
    load_banlist,
    score_slop_fingerprint,
)
from cfb_rankings.chronicle.cache import (
    compute_cache_key,
    get_cached_card,
    store_card,
)
from cfb_rankings.chronicle.eval import EvalReport, evaluate_card
from cfb_rankings.chronicle.evidence_sources import fetch_evidence_for_card, fetch_team_voice
from cfb_rankings.chronicle.lkg import promote_to_lkg
from cfb_rankings.chronicle.prompts import (
    CardBrief,
    CardDraft,
    CollisionCriticScore,
    FactCriticScore,
    PlannerOutput,
    VoiceCriticScore,
    build_collision_critic_prompt,
    build_fact_critic_prompt,
    build_planner_prompt,
    build_refiner_prompt,
    build_voice_critic_prompt,
    build_writer_prompt,
)
from cfb_rankings.chronicle.retriever import EvidenceRow, RetrievalQuery, compute_evidence_hash, retrieve_evidence
from cfb_rankings.chronicle.runtime import CardTier, GenerationConfig, LLMBackend, Router

log = logging.getLogger(__name__)

# Prompt template version constant — bump when prompts.py templates change
_PROMPT_TEMPLATE_ID = "v4-2026-05-24-game-evidence"  # v4 adds game-result evidence source for all FBS teams
_SCHEMA_VERSION = "v1"

# Default card types offered at each tier
_TIER_DEFAULT_CARD_TYPES: dict[str, list[str]] = {
    "S":  ["flashpoint", "player_arc", "heisman_trajectory", "moment_of_year", "echo", "devil_card"],
    "T1": ["flashpoint", "player_arc", "echo", "retroactive"],
    "T2": ["flashpoint", "player_arc", "echo"],
    "T3": ["flashpoint", "player_arc"],
}

# Default n_slots per tier (players)
_TIER_PLAYER_SLOTS: dict[str, int] = {"S": 6, "T1": 6, "T2": 4, "T3": 2}
_TIER_TEAM_SLOTS:   dict[str, int] = {"S": 6, "T1": 6, "T2": 4, "T3": 2}


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PageTarget:
    """Describes a single page (player or team) to generate cards for."""

    entity_kind: Literal["player", "team"]
    slug: str
    season_year: int
    week_number: int | None = None
    n_slots: int = 6
    card_types: list[str] | None = None
    tier: CardTier = CardTier.T3
    page_thesis_hint: str | None = None


@dataclass
class PipelineConfig:
    """Controls pipeline behaviour per run."""

    factscore_threshold: float = 0.85
    voice_critic_blocking: bool = False
    max_refiner_retries: int = 1
    best_of_n_writer: int = 1
    use_cache: bool = True
    promote_to_lkg_on_pass: bool = True
    suppress_thin_cards: bool = True
    eval_judge_backend: Any | None = None

    @classmethod
    def for_tier(cls, tier: CardTier) -> "PipelineConfig":
        """Return tier-appropriate defaults.

        Tier S: Best-of-3 writer, 1 refine retry, strict 0.85 threshold.
        Tier T1: Single-pass writer, 1 retry, standard threshold.
        Tier T2: Single-pass, 1 retry, relaxed threshold.
        Tier T3: Single-pass, no retry, 0.75 threshold.
        """
        if tier == CardTier.S:
            return cls(
                factscore_threshold=0.85,
                voice_critic_blocking=False,
                max_refiner_retries=1,
                best_of_n_writer=3,
                use_cache=True,
                promote_to_lkg_on_pass=True,
                suppress_thin_cards=True,
            )
        elif tier == CardTier.T1:
            return cls(
                factscore_threshold=0.85,
                voice_critic_blocking=False,
                max_refiner_retries=1,
                best_of_n_writer=1,
                use_cache=True,
                promote_to_lkg_on_pass=True,
                suppress_thin_cards=True,
            )
        elif tier == CardTier.T2:
            return cls(
                factscore_threshold=0.80,
                voice_critic_blocking=False,
                max_refiner_retries=1,
                best_of_n_writer=1,
                use_cache=True,
                promote_to_lkg_on_pass=True,
                suppress_thin_cards=True,
            )
        else:  # T3
            return cls(
                factscore_threshold=0.75,
                voice_critic_blocking=False,
                max_refiner_retries=0,
                best_of_n_writer=1,
                use_cache=True,
                promote_to_lkg_on_pass=True,
                suppress_thin_cards=False,
            )


@dataclass
class CardResult:
    """Result of generating a single card."""

    slot_index: int
    card_type: str
    cache_key: str
    action: Literal[
        "shipped",
        "shipped_with_flag",
        "suppressed",
        "failed_after_retry",
        "lkg_fallback",
        "cache_hit",
    ]
    draft: CardDraft | None = None
    fact_critic: FactCriticScore | None = None
    voice_critic: VoiceCriticScore | None = None
    eval_report: EvalReport | None = None
    attempts_used: int = 0
    wall_clock_ms: int = 0
    failure_reason: str | None = None


@dataclass
class PageResult:
    """Result of generating all cards for a single page."""

    target: PageTarget
    cards: list[CardResult] = field(default_factory=list)
    planner_output: PlannerOutput | None = None
    collision_critic: CollisionCriticScore | None = None
    evidence_count: int = 0
    evidence_hash: str = ""
    wall_clock_ms: int = 0
    shipped_count: int = 0
    suppressed_count: int = 0
    failed_count: int = 0
    batch_id: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fetch_narrative_state(db: Any, target: PageTarget) -> dict:
    """Query narrative state tables for the target entity.

    Reads from narrative_frame_stack, season_narrative_state, and
    calendar_pressure. Returns a dict with keys: frame_stack (list of dicts),
    open_arcs (list), calendar_pressure (dict), phrase_tokens (list).

    All tables are optional — missing tables or rows degrade gracefully to
    empty defaults so the pipeline always continues.
    """
    result: dict = {
        "frame_stack": [],
        "open_arcs": [],
        "calendar_pressure": {},
        "phrase_tokens": [],
    }

    try:
        rows = db.query_all(
            """
            SELECT frame_id, label, depth, created_at
            FROM narrative_frame_stack
            WHERE entity_slug = ? AND entity_kind = ?
            ORDER BY depth ASC
            LIMIT 8
            """,
            (target.slug, target.entity_kind),
        )
        result["frame_stack"] = [dict(r) for r in rows]
    except Exception as exc:
        log.debug("_fetch_narrative_state: frame_stack unavailable for %s: %s", target.slug, exc)

    try:
        rows = db.query_all(
            """
            SELECT arc_id, summary, status, started_week
            FROM season_narrative_state
            WHERE entity_slug = ? AND season_year = ? AND status = 'open'
            LIMIT 6
            """,
            (target.slug, target.season_year),
        )
        result["open_arcs"] = [dict(r) for r in rows]
    except Exception as exc:
        log.debug("_fetch_narrative_state: season_narrative_state unavailable for %s: %s", target.slug, exc)

    try:
        row = db.query_one(
            """
            SELECT *
            FROM calendar_pressure
            WHERE season_year = ?
            AND (week_number = ? OR week_number IS NULL)
            ORDER BY week_number DESC
            LIMIT 1
            """,
            (target.season_year, target.week_number),
        )
        if row:
            result["calendar_pressure"] = dict(row)
    except Exception as exc:
        log.debug("_fetch_narrative_state: calendar_pressure unavailable for %s: %s", target.slug, exc)

    try:
        rows = db.query_all(
            """
            SELECT token, uses_remaining, introduced_week
            FROM narrative_phrase_tokens
            WHERE entity_slug = ? AND season_year = ? AND uses_remaining > 0
            ORDER BY introduced_week DESC
            LIMIT 12
            """,
            (target.slug, target.season_year),
        )
        result["phrase_tokens"] = [dict(r) for r in rows]
    except Exception as exc:
        log.debug("_fetch_narrative_state: phrase_tokens unavailable for %s: %s", target.slug, exc)

    return result


def _fetch_team_voice(db: Any, target: PageTarget) -> dict | None:
    """Return team voice dict or None.

    For entity_kind='team': looks up directly by slug.
    For entity_kind='player': resolves the player's current team first,
    then fetches that team's voice config.
    """
    if target.entity_kind == "team":
        try:
            return fetch_team_voice(db, target.slug)
        except Exception as exc:
            log.debug("_fetch_team_voice: team %s: %s", target.slug, exc)
            return None

    # Player — look up their current team slug
    try:
        row = db.query_one(
            """
            SELECT t.slug AS team_slug
            FROM players p
            JOIN teams t ON t.id = p.team_id OR t.team_id = p.team_id
            WHERE p.slug = ?
            LIMIT 1
            """,
            (target.slug,),
        )
        if not row:
            # Try alternate schema layout
            row = db.query_one(
                "SELECT current_team_slug AS team_slug FROM players WHERE slug = ?",
                (target.slug,),
            )
        if row and row.get("team_slug"):
            return fetch_team_voice(db, row["team_slug"])
    except Exception as exc:
        log.debug("_fetch_team_voice: player %s team lookup: %s", target.slug, exc)

    return None


def _entity_name_aliases(db: Any, target: PageTarget) -> set[str]:
    """Return lowercase set of aliases that, if present in card body, prove
    topical relevance. For teams: slug, slug-with-spaces, canonical_name,
    school_name, short_name, all from teams table. For players: last_name
    and full_name from players table.

    Defensive against missing rows — always includes the raw slug as a
    minimum fallback.
    """
    slug = target.slug.lower()
    slug_spaces = slug.replace("-", " ")
    aliases: set[str] = {slug, slug_spaces}
    if target.entity_kind == "team":
        try:
            row = db.query_one(
                "SELECT canonical_name, school_name, short_name FROM teams WHERE LOWER(slug) = :slug",
                {"slug": slug},
            )
            if row:
                for col in ("canonical_name", "school_name", "short_name"):
                    val = row.get(col) if isinstance(row, dict) else (row[col] if col in row.keys() else None)
                    if val and len(str(val)) >= 3:
                        aliases.add(str(val).lower().strip())
        except Exception:
            pass
        # Also try team_aliases table if it exists
        try:
            for r in db.query_all(
                "SELECT alias FROM team_aliases ta JOIN teams t ON t.team_id = ta.team_id "
                "WHERE LOWER(t.slug) = :slug AND alias IS NOT NULL",
                {"slug": slug},
            ):
                a = r.get("alias") if isinstance(r, dict) else r["alias"]
                if a and len(str(a)) >= 3:
                    aliases.add(str(a).lower().strip())
        except Exception:
            pass
    elif target.entity_kind == "player":
        try:
            row = db.query_one(
                "SELECT full_name, last_name FROM players WHERE LOWER(REPLACE(LOWER(full_name), ' ', '-')) = :slug "
                "OR LOWER(last_name) = :slug",
                {"slug": slug},
            )
            if row:
                fn = row.get("full_name") if isinstance(row, dict) else row["full_name"]
                ln = row.get("last_name") if isinstance(row, dict) else row["last_name"]
                if fn:
                    aliases.add(str(fn).lower().strip())
                if ln and len(str(ln)) >= 3:
                    aliases.add(str(ln).lower().strip())
        except Exception:
            pass
    # Strip trailing "-2", "-3" suffix from slug (artifacts of duplicate ingest)
    base = re.sub(r"-\d+$", "", slug)
    if base != slug:
        aliases.add(base)
        aliases.add(base.replace("-", " "))
    return aliases


def _collect_evidence(
    db: Any,
    target: PageTarget,
    card_types: list[str],
) -> list[EvidenceRow]:
    """Build a deduped evidence pool for all requested card types.

    Calls fetch_evidence_for_card (evidence_sources) for each card type and
    also calls retrieve_evidence (retriever) with a generic query. Dedupes by
    source_id + text hash, caps at 50 rows total.

    Gracefully returns [] if all sources fail.
    """
    combined: list[EvidenceRow] = []
    seen_hashes: set[str] = set()

    def _add_rows(rows: list[EvidenceRow]) -> None:
        for row in rows:
            h = row.evidence_hash_input()
            if h not in seen_hashes:
                seen_hashes.add(h)
                combined.append(row)

    # Per-card-type evidence from evidence_sources routing
    for ct in card_types:
        try:
            rows = fetch_evidence_for_card(
                db,
                card_type=ct,
                slug=target.slug,
                entity_kind=target.entity_kind,
                season_year=target.season_year,
                week_number=target.week_number,
            )
            _add_rows(rows)
        except Exception as exc:
            log.warning(
                "_collect_evidence: fetch_evidence_for_card failed for %s/%s: %s",
                target.slug, ct, exc,
            )

    # Hybrid retrieval for the first card type as a catch-all
    primary_ct = card_types[0] if card_types else "flashpoint"
    try:
        query = RetrievalQuery(
            entity_slug=target.slug,
            entity_kind=target.entity_kind,
            season_year=target.season_year,
            week_number=target.week_number,
            card_type=primary_ct,
            k=30,
            mode="all",
        )
        retrieved = retrieve_evidence(db, query)
        _add_rows(retrieved)
    except Exception as exc:
        log.debug("_collect_evidence: retrieve_evidence failed for %s: %s", target.slug, exc)

    return combined[:50]


def _run_planner(
    backend: LLMBackend,
    target: PageTarget,
    evidence: list[EvidenceRow],
    narrative_state: dict,
    available_card_types: list[str],
) -> PlannerOutput:
    """Call the Planner agent to produce a PlannerOutput covering all slots.

    On any parse error, returns a minimal PlannerOutput with one freeform brief
    per slot so downstream stages always have something to work with.
    """
    try:
        system, user, gen_cfg = build_planner_prompt(
            entity_slug=target.slug,
            entity_kind=target.entity_kind,
            season_year=target.season_year,
            week_number=target.week_number,
            n_slots=target.n_slots,
            evidence=evidence,
            frame_stack=narrative_state.get("frame_stack", []),
            open_arcs=narrative_state.get("open_arcs", []),
            calendar_pressure=narrative_state.get("calendar_pressure", {}),
            phrase_tokens=narrative_state.get("phrase_tokens", []),
            available_card_types=available_card_types,
            previously_published_cards=None,
        )
        full_prompt = system + "\n\n" + user
        parsed, _result = backend.generate_structured(full_prompt, PlannerOutput, gen_cfg)
        return parsed
    except Exception as exc:
        log.warning(
            "_run_planner: failed for %s (%s) — using fallback briefs", target.slug, exc
        )
        # Build a minimal fallback: one freeform brief per slot
        fallback_briefs: list[CardBrief] = []
        for i in range(target.n_slots):
            ct = available_card_types[i % len(available_card_types)] if available_card_types else "flashpoint"
            fallback_briefs.append(
                CardBrief(
                    slot_index=i,
                    action="card",
                    card_type=ct,
                    template_pattern="freeform",
                    target_word_count=75,
                )
            )
        return PlannerOutput(briefs=fallback_briefs, page_thesis="")


def _run_writer(
    backend: LLMBackend,
    brief: CardBrief,
    evidence: list[EvidenceRow],
    narrative_state: dict,
    team_voice: dict | None,
    banlist: list[BanEntry],
    n_samples: int,
    entity_label: str | None = None,
    entity_aliases: list[str] | None = None,
) -> CardDraft | None:
    """Call the Writer agent with optional Best-of-N sampling.

    With n_samples > 1: generates N candidates, picks the one with the lowest
    slop fingerprint score.

    Returns None if all attempts fail.
    """
    system, user, gen_cfg = build_writer_prompt(
        brief=brief,
        evidence=evidence,
        frame_stack=narrative_state.get("frame_stack", []),
        team_voice=team_voice,
        page_thesis="",
        is_devil_card=brief.is_devil_card,
        entity_label=entity_label,
        entity_aliases=entity_aliases,
    )
    full_prompt = system + "\n\n" + user

    # Apply antislop to the config
    cfg_with_slop = GenerationConfig(**{
        k: v for k, v in gen_cfg.__dict__.items()
    })
    apply_antislop_to_config(cfg_with_slop, banlist)
    cfg_with_slop.n_samples = 1  # we loop manually for slop-aware selection

    candidates: list[CardDraft] = []
    for _ in range(max(1, n_samples)):
        try:
            parsed, _gen_result = backend.generate_structured(
                full_prompt, CardDraft, cfg_with_slop
            )
            if parsed is not None:
                candidates.append(parsed)
        except Exception as exc:
            log.debug("_run_writer: candidate attempt failed: %s", exc)

    if not candidates:
        return None

    if len(candidates) == 1:
        return candidates[0]

    # Pick candidate with lowest slop score
    banlist_phrases = [b.phrase for b in banlist]
    # Fake ban entries for scoring — reuse BanEntry with severity 1.0
    score_banlist = [BanEntry(phrase=p, kind="unknown", severity=1.0) for p in banlist_phrases]

    def _slop(draft: CardDraft) -> float:
        return score_slop_fingerprint(draft.body_text or "", score_banlist)

    return min(candidates, key=_slop)


def _run_fact_critic(
    backend: LLMBackend,
    draft: CardDraft,
    evidence: list[EvidenceRow],
    entity_label: str | None = None,
) -> FactCriticScore:
    """Run the FactCritic agent against the draft.

    On parse failure returns a FactCriticScore with verdict='fail' so the
    pipeline treats an unparseable critic as a hard fail rather than silently
    passing a card that may be fabricated.

    When `entity_label` is provided, the prompt enforces entity-attribution
    verification (catches "Arizona's Ty Simpson" cross-team misattributions).
    """
    try:
        system, user, gen_cfg = build_fact_critic_prompt(
            draft=draft,
            evidence=evidence,
            citation_markers_required=1,
            entity_label=entity_label,
        )
        full_prompt = system + "\n\n" + user
        parsed, _result = backend.generate_structured(full_prompt, FactCriticScore, gen_cfg)
        return parsed
    except Exception as exc:
        log.warning("_run_fact_critic: failed (%s) — returning fail verdict", exc)
        return FactCriticScore(
            factscore_atomic=0.0,
            verdict="fail",
            rationale=f"Critic output unparseable: {exc}",
        )


def _run_voice_critic(
    backend: LLMBackend,
    draft: CardDraft,
    banlist: list[BanEntry],
    team_voice: dict | None,
) -> VoiceCriticScore:
    """Run the VoiceCritic agent.

    On parse failure returns a VoiceCriticScore with verdict='flag' — softer
    than fact_critic's fail, since voice issues don't constitute fabrication.
    """
    banlist_phrases = [b.phrase for b in banlist]
    banlist_severity = {b.phrase: b.severity for b in banlist}

    try:
        system, user, gen_cfg = build_voice_critic_prompt(
            draft=draft,
            banlist=banlist_phrases,
            banlist_severity=banlist_severity,
            team_voice=team_voice,
        )
        full_prompt = system + "\n\n" + user
        parsed, _result = backend.generate_structured(full_prompt, VoiceCriticScore, gen_cfg)
        return parsed
    except Exception as exc:
        log.warning("_run_voice_critic: failed (%s) — returning flag verdict", exc)
        return VoiceCriticScore(
            sounds_like_corpus_score=0.5,
            verdict="flag",
            rationale=f"Critic output unparseable: {exc}",
        )


def _run_collision_critic(
    backend: LLMBackend,
    drafts: list[CardDraft],
) -> CollisionCriticScore | None:
    """Run the CollisionCritic over all sibling drafts on a page.

    Requires at least 2 drafts — returns None for single-card pages. On parse
    failure returns a safe CollisionCriticScore with verdict='pass' (collision
    detection is a quality signal but should not block shipping).
    """
    if len(drafts) < 2:
        return None

    try:
        system, user, gen_cfg = build_collision_critic_prompt(sibling_drafts=drafts)
        full_prompt = system + "\n\n" + user
        parsed, _result = backend.generate_structured(full_prompt, CollisionCriticScore, gen_cfg)
        return parsed
    except Exception as exc:
        log.warning("_run_collision_critic: failed (%s) — treating as pass", exc)
        return CollisionCriticScore(
            opening_type_diversity=1.0,
            evidence_overlap_max=0.0,
            ngram_collision_count=0,
            verdict="pass",
            rationale=f"Critic output unparseable: {exc}",
        )


def _run_refiner(
    backend: LLMBackend,
    draft: CardDraft,
    fact_critic: FactCriticScore | None,
    voice_critic: VoiceCriticScore | None,
    collision_critic: CollisionCriticScore | None,
    brief: CardBrief,
    evidence: list[EvidenceRow],
) -> CardDraft | None:
    """Run the Refiner agent to produce a revised draft addressing critic feedback.

    Returns None if generation fails, in which case the caller falls back to
    the original draft.
    """
    try:
        system, user, gen_cfg = build_refiner_prompt(
            draft=draft,
            fact_critic=fact_critic,
            voice_critic=voice_critic,
            collision_critic=collision_critic,
            brief=brief,
            evidence=evidence,
        )
        full_prompt = system + "\n\n" + user
        parsed, _result = backend.generate_structured(full_prompt, CardDraft, gen_cfg)
        return parsed
    except Exception as exc:
        log.warning("_run_refiner: failed (%s) — returning None (caller uses original)", exc)
        return None


# ---------------------------------------------------------------------------
# Core card generation
# ---------------------------------------------------------------------------


def generate_card(
    db: Any,
    brief: CardBrief,
    evidence: list[EvidenceRow],
    evidence_hash: str,
    target: PageTarget,
    narrative_state: dict,
    team_voice: dict | None,
    banlist: list[BanEntry],
    router: Router,
    config: PipelineConfig,
) -> CardResult:
    """Generate a single card through the full agent pipeline.

    Flow:
      1. Cache check (if config.use_cache)
      2. Writer (Best-of-N)
      3. FactCritic
      4. Refiner (if fact_critic fails and retries > 0)
      5. VoiceCritic
      6. evaluate_card
      7. Decide action (shipped / shipped_with_flag / failed_after_retry)
      8. store_card (on ship)
      9. promote_to_lkg (if action==shipped and config.promote_to_lkg_on_pass)

    Returns a CardResult with all intermediate scores attached.
    """
    t0 = time.monotonic()
    slot_index = brief.slot_index
    card_type = brief.card_type or "flashpoint"

    # Determine backend roles
    try:
        writer_backend = router.select(target.tier, "writer")
    except Exception as exc:
        log.warning("generate_card: no writer backend for tier=%s: %s", target.tier, exc)
        from cfb_rankings.chronicle.runtime import NullBackend
        writer_backend = NullBackend()

    try:
        critic_backend = router.select(target.tier, "critic")
    except Exception as exc:
        log.debug("generate_card: no critic backend, falling back to writer backend: %s", exc)
        critic_backend = writer_backend

    # Compute cache key
    try:
        model_id = writer_backend.model_id
        model_version = writer_backend.model_version
    except Exception:
        model_id = "unknown"
        model_version = "0"

    cache_key = compute_cache_key(
        slug=target.slug,
        season_year=target.season_year,
        week_number=target.week_number,
        card_type=card_type,
        slot_index=slot_index,
        evidence_hash=evidence_hash,
        prompt_template_id=_PROMPT_TEMPLATE_ID,
        model_id=model_id,
        model_version=model_version,
        schema_version=_SCHEMA_VERSION,
    )

    # --- Cache check ---
    if config.use_cache:
        try:
            cached = get_cached_card(db, cache_key)
            if cached is not None:
                log.debug(
                    "generate_card: cache hit for %s slot=%d type=%s",
                    target.slug, slot_index, card_type,
                )
                return CardResult(
                    slot_index=slot_index,
                    card_type=card_type,
                    cache_key=cache_key,
                    action="cache_hit",
                    wall_clock_ms=int((time.monotonic() - t0) * 1000),
                )
        except Exception as exc:
            log.debug("generate_card: cache check failed (%s) — continuing", exc)

    # --- Resolve topical anchor (entity_label + aliases) ---
    aliases = sorted(_entity_name_aliases(db, target))
    # Pick a human-readable entity_label: prefer canonical_name if available,
    # else slug-with-spaces titlecased.
    entity_label = target.slug.replace("-", " ").title()
    if target.entity_kind == "team":
        try:
            row = db.query_one(
                "SELECT school_name, canonical_name FROM teams WHERE LOWER(slug) = :slug",
                {"slug": target.slug.lower()},
            )
            if row:
                cand = (row.get("school_name") if isinstance(row, dict) else row["school_name"]) or \
                       (row.get("canonical_name") if isinstance(row, dict) else row["canonical_name"])
                if cand:
                    entity_label = str(cand)
        except Exception:
            pass

    # --- Writer ---
    draft: CardDraft | None = None
    attempts_used = 0

    try:
        draft = _run_writer(
            writer_backend, brief, evidence, narrative_state,
            team_voice, banlist, config.best_of_n_writer,
            entity_label=entity_label,
            entity_aliases=aliases,
        )
        attempts_used = 1
    except Exception as exc:
        log.warning("generate_card: _run_writer raised for %s slot=%d: %s", target.slug, slot_index, exc)

    if draft is None:
        return CardResult(
            slot_index=slot_index,
            card_type=card_type,
            cache_key=cache_key,
            action="failed_after_retry",
            attempts_used=attempts_used,
            wall_clock_ms=int((time.monotonic() - t0) * 1000),
            failure_reason="Writer produced no output",
        )

    # --- TOPICAL DRIFT DETECTOR ---
    # Reject cards that don't mention the target entity by name. This catches
    # the common case where the Writer pulled from substack_* evidence that
    # mentioned the team only tangentially, and wrote a card about whatever
    # the substack article was actually about (e.g. Cincinnati card about RJ
    # Day's commitment to Ohio State). Cheap O(1) check, big quality win.
    #
    # We accept the slug, slug-with-spaces, OR a known short-name alias
    # (loaded once via _team_name_aliases). For player entities, we accept
    # last name or full name.
    if draft.body_text:
        aliases = _entity_name_aliases(db, target)
        body_lower = draft.body_text.lower()
        if not any(alias in body_lower for alias in aliases):
            log.info(
                "generate_card: TOPICAL_DRIFT rejected %s/%s slot=%d — body doesn't mention any of %s",
                target.slug, card_type, slot_index, sorted(aliases)[:3],
            )
            return CardResult(
                slot_index=slot_index,
                card_type=card_type,
                cache_key=cache_key,
                action="failed_after_retry",
                draft=draft,
                attempts_used=attempts_used,
                wall_clock_ms=int((time.monotonic() - t0) * 1000),
                failure_reason=f"topical_drift: body doesn't mention '{target.slug}' or aliases",
            )

    # --- FactCritic ---
    fact_critic: FactCriticScore = _run_fact_critic(critic_backend, draft, evidence, entity_label=entity_label)

    # --- Refiner (if fact_critic fails and retries configured) ---
    if fact_critic.verdict == "fail" and config.max_refiner_retries > 0:
        refined = _run_refiner(
            critic_backend, draft, fact_critic, None, None, brief, evidence
        )
        if refined is not None:
            draft = refined
            attempts_used += 1
            fact_critic = _run_fact_critic(critic_backend, draft, evidence)

    # --- VoiceCritic ---
    voice_critic: VoiceCriticScore = _run_voice_critic(
        critic_backend, draft, banlist, team_voice
    )

    # --- Eval ---
    eval_report: EvalReport | None = None
    try:
        eval_report = evaluate_card(
            card_text=draft.body_text or "",
            card_cache_key=cache_key,
            evidence=evidence,
            judge_backend=config.eval_judge_backend,
            slop_banlist=[b.phrase for b in banlist],
            factscore_threshold=config.factscore_threshold,
        )
    except Exception as exc:
        log.warning("generate_card: evaluate_card failed for %s: %s", target.slug, exc)

    # --- Decide action ---
    # Priority order:
    #   1. FactCritic (LLM) is authoritative for groundedness — when an LLM
    #      critic explicitly says "pass" with semantic understanding, trust
    #      that over the heuristic keyword-overlap eval.
    #   2. Heuristic eval is a secondary safety net for cases the LLM critic
    #      didn't run or failed to produce output.
    #   3. Voice / quality flags are non-blocking by default.
    fact_fail = fact_critic.verdict == "fail"
    fact_pass = fact_critic.verdict == "pass"
    eval_reject = eval_report is not None and eval_report.overall_verdict == "reject"
    eval_flag = eval_report is not None and eval_report.overall_verdict in ("flag", "regenerate")

    if fact_fail:
        # LLM critic explicitly rejected on groundedness — that's a real fail.
        action: Literal[
            "shipped", "shipped_with_flag", "suppressed",
            "failed_after_retry", "lkg_fallback", "cache_hit"
        ] = "failed_after_retry"
        failure_reason = f"fact_critic.verdict=fail: {fact_critic.rationale[:200] if fact_critic.rationale else ''}"
    elif eval_reject and not fact_pass:
        # Heuristic eval rejected AND no LLM-critic pass to override it.
        action = "failed_after_retry"
        failure_reason = (
            f"eval={eval_report.overall_verdict}"
            + (f"; rationale={eval_report.rationale[:160]}" if eval_report and eval_report.rationale else "")
        )
    elif fact_pass and (eval_flag or eval_reject):
        # FactCritic passed but heuristic eval is uncomfortable — ship with flag.
        # This is the common case for LLM cards that don't keyword-overlap evidence verbatim.
        action = "shipped_with_flag"
        failure_reason = None
    elif eval_flag:
        action = "shipped_with_flag"
        failure_reason = None
    else:
        action = "shipped"
        failure_reason = None

    wall_clock_ms = int((time.monotonic() - t0) * 1000)

    # --- Store card on ship ---
    if action in ("shipped", "shipped_with_flag"):
        try:
            store_card(
                db,
                cache_key=cache_key,
                slug=target.slug,
                entity_kind=target.entity_kind,
                season_year=target.season_year,
                week_number=target.week_number,
                card_type=card_type,
                slot_index=slot_index,
                card_content=draft.model_dump(),
                card_html=None,
                evidence_hash=evidence_hash,
                prompt_template_id=_PROMPT_TEMPLATE_ID,
                model_id=model_id,
                model_version=model_version,
                schema_version=_SCHEMA_VERSION,
                confidence_band="high" if action == "shipped" else "medium",
                voice_critic_score=(
                    voice_critic.sounds_like_corpus_score if voice_critic else None
                ),
                fact_critic_score=(
                    fact_critic.factscore_atomic if fact_critic else None
                ),
                factscore_atomic=(
                    fact_critic.factscore_atomic if fact_critic else None
                ),
                word_count=draft.word_count or None,
                generation_attempt=attempts_used,
                wall_clock_ms=wall_clock_ms,
                supersede_previous=True,
            )
        except Exception as exc:
            log.warning(
                "generate_card: store_card failed for %s/%s slot=%d: %s",
                target.slug, card_type, slot_index, exc,
            )

        # --- LKG promotion ---
        if config.promote_to_lkg_on_pass and action == "shipped":
            try:
                promote_to_lkg(db, cache_key)
            except Exception as exc:
                log.debug("generate_card: promote_to_lkg failed for %s: %s", cache_key, exc)

    return CardResult(
        slot_index=slot_index,
        card_type=card_type,
        cache_key=cache_key,
        action=action,
        draft=draft,
        fact_critic=fact_critic,
        voice_critic=voice_critic,
        eval_report=eval_report,
        attempts_used=attempts_used,
        wall_clock_ms=wall_clock_ms,
        failure_reason=failure_reason,
    )


# ---------------------------------------------------------------------------
# Page orchestrator
# ---------------------------------------------------------------------------


def generate_page_cards(
    db: Any,
    target: PageTarget,
    router: Router,
    config: PipelineConfig | None = None,
) -> PageResult:
    """Generate all cards for a single page target.

    Steps:
      1. Fetch narrative state
      2. Fetch team voice
      3. Build evidence pool (deduped, capped at 50 rows)
      4. Compute evidence_hash
      5. Load banlist
      6. Run Planner -> list[CardBrief]
      7. Per brief: suppress or call generate_card
      8. Run CollisionCritic over shipped drafts
      9. Return PageResult with aggregate stats

    Returns a PageResult even if all cards fail (graceful degradation).
    """
    t0 = time.monotonic()

    if config is None:
        config = PipelineConfig.for_tier(target.tier)

    available_card_types = target.card_types or (
        _TIER_DEFAULT_CARD_TYPES.get(target.tier.value, _TIER_DEFAULT_CARD_TYPES["T3"])
    )

    # 1. Narrative state
    narrative_state = _fetch_narrative_state(db, target)

    # 2. Team voice
    team_voice = _fetch_team_voice(db, target)

    # 3. Evidence pool
    evidence = _collect_evidence(db, target, available_card_types)

    # 3a. EVIDENCE-FLOOR GATE
    # If we have < EVIDENCE_FLOOR rows for this entity, suppress ALL slots
    # rather than letting the LLM hallucinate. Empirically observed: when
    # evidence is empty, Mistral Nemo invents content about famous players
    # ("Bryce Young threw for...") with fake source citations, polluting the
    # card cache. The pipeline's eval correctly rejects these, but we save
    # 30+ seconds per team by short-circuiting here.
    EVIDENCE_FLOOR = 3
    if len(evidence) < EVIDENCE_FLOOR:
        log.info(
            "generate_page_cards: SUPPRESS-ALL for %s — evidence=%d < floor=%d",
            target.slug, len(evidence), EVIDENCE_FLOOR,
        )
        suppressed_cards = []
        for slot_idx in range(target.n_slots):
            ct = (available_card_types[slot_idx % len(available_card_types)]
                  if available_card_types else "flashpoint")
            suppressed_cards.append(
                CardResult(
                    slot_index=slot_idx,
                    card_type=ct,
                    cache_key="",
                    action="suppressed",
                    failure_reason=f"insufficient_evidence (have {len(evidence)}, need {EVIDENCE_FLOOR})",
                )
            )
        return PageResult(
            target=target,
            cards=suppressed_cards,
            planner_output=None,
            collision_critic=None,
            evidence_count=len(evidence),
            evidence_hash="empty",
            wall_clock_ms=int((time.monotonic() - t0) * 1000),
            shipped_count=0,
            suppressed_count=len(suppressed_cards),
            failed_count=0,
        )

    # 4. Evidence hash
    evidence_hash = compute_evidence_hash(evidence) if evidence else "empty"

    # 5. Banlist
    banlist: list[BanEntry] = []
    try:
        banlist = load_banlist(db)
    except Exception as exc:
        log.warning(
            "generate_page_cards: load_banlist failed for %s (%s) — continuing without banlist",
            target.slug, exc,
        )

    # 6. Planner
    try:
        planner_backend = router.select(target.tier, "planner")
    except Exception as exc:
        log.warning(
            "generate_page_cards: no planner backend for %s tier=%s: %s",
            target.slug, target.tier, exc,
        )
        from cfb_rankings.chronicle.runtime import NullBackend
        planner_backend = NullBackend()

    planner_output = _run_planner(
        planner_backend, target, evidence, narrative_state, available_card_types
    )

    # Pad briefs to n_slots if planner returned fewer
    briefs = list(planner_output.briefs or [])
    while len(briefs) < target.n_slots:
        idx = len(briefs)
        ct = available_card_types[idx % len(available_card_types)]
        briefs.append(
            CardBrief(
                slot_index=idx,
                action="card",
                card_type=ct,
                template_pattern="freeform",
                target_word_count=75,
            )
        )

    # 7. Per-brief card generation
    card_results: list[CardResult] = []
    for brief in briefs:
        if brief.action == "suppress" and config.suppress_thin_cards:
            card_results.append(
                CardResult(
                    slot_index=brief.slot_index,
                    card_type=brief.card_type or "flashpoint",
                    cache_key="",
                    action="suppressed",
                    failure_reason=brief.suppress_reason,
                )
            )
            continue

        card_result = generate_card(
            db=db,
            brief=brief,
            evidence=evidence,
            evidence_hash=evidence_hash,
            target=target,
            narrative_state=narrative_state,
            team_voice=team_voice,
            banlist=banlist,
            router=router,
            config=config,
        )
        card_results.append(card_result)

    # 8. CollisionCritic over all shipped drafts
    shipped_drafts = [
        cr.draft for cr in card_results
        if cr.action in ("shipped", "shipped_with_flag") and cr.draft is not None
    ]

    collision_critic: CollisionCriticScore | None = None
    if len(shipped_drafts) >= 2:
        try:
            critic_backend = router.select(target.tier, "critic")
        except Exception:
            from cfb_rankings.chronicle.runtime import NullBackend
            critic_backend = NullBackend()

        collision_critic = _run_collision_critic(critic_backend, shipped_drafts)

    # Aggregate stats
    shipped = sum(1 for cr in card_results if cr.action in ("shipped", "shipped_with_flag", "cache_hit"))
    suppressed = sum(1 for cr in card_results if cr.action == "suppressed")
    failed = sum(1 for cr in card_results if cr.action == "failed_after_retry")

    return PageResult(
        target=target,
        cards=card_results,
        planner_output=planner_output,
        collision_critic=collision_critic,
        evidence_count=len(evidence),
        evidence_hash=evidence_hash,
        wall_clock_ms=int((time.monotonic() - t0) * 1000),
        shipped_count=shipped,
        suppressed_count=suppressed,
        failed_count=failed,
    )


# ---------------------------------------------------------------------------
# Entity selection for tier batches
# ---------------------------------------------------------------------------


def _select_entities_for_tier(
    db: Any,
    tier: CardTier,
    max_count: int = 0,
) -> list[PageTarget]:
    """Select entities appropriate for the given tier.

    Tier S:  top 25 players by Heisman odds + top 10 teams by savant score.
    Tier T1: top 100 players by season summary + top 50 teams.
    Tier T2: next 100 players (rank 51-150) + next 50 teams.
    Tier T3: all remaining FBS players + teams.

    Uses try/except on every table — returns [] on completely missing data
    rather than raising so the caller can degrade gracefully.
    """
    season_year = _infer_season_year(db)
    entities: list[PageTarget] = []
    fbs_slugs = _real_fbs_slugs()  # authoritative FBS team slug set from profiles/

    tier_val = tier.value
    card_types = _TIER_DEFAULT_CARD_TYPES.get(tier_val, _TIER_DEFAULT_CARD_TYPES["T3"])
    player_slots = _TIER_PLAYER_SLOTS.get(tier_val, 2)
    team_slots = _TIER_TEAM_SLOTS.get(tier_val, 2)

    if tier == CardTier.S:
        # Players: top 25 from Heisman market
        try:
            rows = db.query_all(
                """
                SELECT p.slug
                FROM heisman_market_odds_weekly h
                JOIN players p ON p.id = h.player_id OR p.player_id = h.player_id
                WHERE h.season_year = ?
                ORDER BY h.implied_probability DESC
                LIMIT 25
                """,
                (season_year,),
            )
            for r in rows:
                if r.get("slug"):
                    entities.append(PageTarget(
                        entity_kind="player",
                        slug=r["slug"],
                        season_year=season_year,
                        n_slots=player_slots,
                        card_types=card_types,
                        tier=tier,
                    ))
        except Exception as exc:
            log.debug("_select_entities_for_tier S players: %s", exc)
            # Fall back to prediction_market_snapshots
            try:
                rows = db.query_all(
                    """
                    SELECT p.slug
                    FROM prediction_market_snapshots pms
                    JOIN players p ON p.id = pms.player_id OR p.player_id = pms.player_id
                    WHERE pms.season_year = ?
                    ORDER BY pms.probability DESC
                    LIMIT 25
                    """,
                    (season_year,),
                )
                for r in rows:
                    if r.get("slug"):
                        entities.append(PageTarget(
                            entity_kind="player",
                            slug=r["slug"],
                            season_year=season_year,
                            n_slots=player_slots,
                            card_types=card_types,
                            tier=tier,
                        ))
            except Exception as exc2:
                log.debug("_select_entities_for_tier S players fallback: %s", exc2)

        # Teams: top 10 by savant score
        try:
            rows = db.query_all(
                """
                SELECT t.slug
                FROM team_savant_weekly tsw
                JOIN teams t ON t.id = tsw.team_id OR t.team_id = tsw.team_id
                WHERE tsw.season_year = ?
                ORDER BY tsw.savant_score DESC
                LIMIT 10
                """,
                (season_year,),
            )
            for r in rows:
                if r.get("slug"):
                    entities.append(PageTarget(
                        entity_kind="team",
                        slug=r["slug"],
                        season_year=season_year,
                        n_slots=team_slots,
                        card_types=card_types,
                        tier=tier,
                    ))
        except Exception as exc:
            log.debug("_select_entities_for_tier S teams: %s", exc)

    elif tier == CardTier.T1:
        # Players: top 100 by any season summary metric
        try:
            rows = db.query_all(
                """
                SELECT p.slug
                FROM player_season_summary pss
                JOIN players p ON p.id = pss.player_id OR p.player_id = pss.player_id
                WHERE pss.season_year = ?
                ORDER BY COALESCE(pss.overall_grade, 0) DESC
                LIMIT 100
                """,
                (season_year,),
            )
            for r in rows:
                if r.get("slug"):
                    entities.append(PageTarget(
                        entity_kind="player",
                        slug=r["slug"],
                        season_year=season_year,
                        n_slots=player_slots,
                        card_types=card_types,
                        tier=tier,
                    ))
        except Exception as exc:
            log.debug("_select_entities_for_tier T1 players: %s", exc)

        # Teams: top 50 from teams table, filtered against the authoritative
        # profiles/ slug set so mislabelled non-FBS programs are excluded.
        try:
            rows = db.query_all(
                "SELECT slug FROM teams WHERE level_code = 'FBS' AND is_active = 1"
            )
            added = 0
            for r in rows:
                slug = r.get("slug")
                if not slug:
                    continue
                if fbs_slugs and slug not in fbs_slugs:
                    continue  # not a real FBS program
                entities.append(PageTarget(
                    entity_kind="team",
                    slug=slug,
                    season_year=season_year,
                    n_slots=team_slots,
                    card_types=card_types,
                    tier=tier,
                ))
                added += 1
                if added >= 50:
                    break
        except Exception as exc:
            log.debug("_select_entities_for_tier T1 teams: %s", exc)

    elif tier == CardTier.T2:
        # Players: rank 51-150 from season summary
        try:
            rows = db.query_all(
                """
                SELECT p.slug
                FROM player_season_summary pss
                JOIN players p ON p.id = pss.player_id OR p.player_id = pss.player_id
                WHERE pss.season_year = ?
                ORDER BY COALESCE(pss.overall_grade, 0) DESC
                LIMIT 100 OFFSET 50
                """,
                (season_year,),
            )
            for r in rows:
                if r.get("slug"):
                    entities.append(PageTarget(
                        entity_kind="player",
                        slug=r["slug"],
                        season_year=season_year,
                        n_slots=player_slots,
                        card_types=card_types,
                        tier=tier,
                    ))
        except Exception as exc:
            log.debug("_select_entities_for_tier T2 players: %s", exc)

        # Teams: rank 51-100, filtered against the authoritative profiles/ slug set.
        try:
            rows = db.query_all(
                "SELECT slug FROM teams WHERE level_code = 'FBS' AND is_active = 1"
            )
            added = 0
            skipped = 0
            for r in rows:
                slug = r.get("slug")
                if not slug:
                    continue
                if fbs_slugs and slug not in fbs_slugs:
                    continue  # not a real FBS program
                if skipped < 50:
                    skipped += 1
                    continue  # skip T1 slice
                entities.append(PageTarget(
                    entity_kind="team",
                    slug=slug,
                    season_year=season_year,
                    n_slots=team_slots,
                    card_types=card_types,
                    tier=tier,
                ))
                added += 1
                if added >= 50:
                    break
        except Exception as exc:
            log.debug("_select_entities_for_tier T2 teams: %s", exc)

    else:  # T3 — all remaining FBS, filtered against profiles/ slug set
        try:
            rows = db.query_all(
                "SELECT slug FROM teams WHERE level_code = 'FBS' AND is_active = 1"
            )
            for r in rows:
                slug = r.get("slug")
                if not slug:
                    continue
                if fbs_slugs and slug not in fbs_slugs:
                    continue  # not a real FBS program
                entities.append(PageTarget(
                    entity_kind="team",
                    slug=slug,
                    season_year=season_year,
                    n_slots=team_slots,
                    card_types=card_types,
                    tier=tier,
                ))
        except Exception as exc:
            log.debug("_select_entities_for_tier T3 teams: %s", exc)

        try:
            rows = db.query_all(
                # Players table has no classification column — use slug presence as a proxy.
                # Limit to player slugs that have at least one row in player_season_stats
                # for the current season so we don't try to write cards for orphan slugs.
                """
                SELECT DISTINCT p.slug FROM players p
                JOIN player_season_stats pss ON pss.player_id = p.player_id
                WHERE pss.season_year = ? AND p.slug IS NOT NULL
                LIMIT 2000
                """,
                (season_year,),
            )
            for r in rows:
                if r.get("slug"):
                    entities.append(PageTarget(
                        entity_kind="player",
                        slug=r["slug"],
                        season_year=season_year,
                        n_slots=player_slots,
                        card_types=card_types,
                        tier=tier,
                    ))
        except Exception as exc:
            log.debug("_select_entities_for_tier T3 players: %s", exc)

    if max_count and max_count > 0:
        entities = entities[:max_count]

    log.info(
        "_select_entities_for_tier: tier=%s season=%s found %d entities",
        tier.value, season_year, len(entities),
    )
    return entities


def _real_fbs_slugs() -> frozenset[str]:
    """Return the authoritative set of real FBS team slugs.

    Reads from the profiles/ directory (one .md file per team), which is the
    canonical FBS coverage list maintained by hand. This is used to filter out
    teams that have level_code='FBS' in the DB due to ingest data quality issues
    (e.g. NAIA/DII schools incorrectly tagged as FBS).

    Falls back to an empty frozenset (no filtering) if the directory is missing.
    """
    import os
    import pathlib

    # Walk up from this file to find the repo root, then locate profiles/
    here = pathlib.Path(__file__).resolve()
    for parent in [here.parent, here.parent.parent, here.parent.parent.parent,
                   here.parent.parent.parent.parent]:
        profiles_dir = parent / "profiles"
        if profiles_dir.is_dir():
            slugs = frozenset(
                f.stem for f in profiles_dir.iterdir() if f.suffix == ".md"
            )
            if slugs:
                return slugs
            break

    log.warning("_real_fbs_slugs: profiles/ directory not found — FBS filter disabled")
    return frozenset()


def _infer_season_year(db: Any) -> int:
    """Best-effort inference of the current season year from the DB.

    Tries several tables that have a season_year column; falls back to the
    current calendar year minus 1 if the season hasn't started yet.
    """
    import datetime as _dt

    for table in ("player_season_summary", "team_savant_weekly", "heisman_market_odds_weekly"):
        try:
            row = db.query_one(
                f"SELECT MAX(season_year) AS yr FROM {table}"
            )
            if row and row.get("yr"):
                return int(row["yr"])
        except Exception:
            continue

    # Fallback to ratings tables — these are reliably populated even when the
    # higher-level summary tables haven't been backfilled yet.
    for table in ("power_ratings_weekly", "resume_ratings_weekly", "heisman_rankings_weekly"):
        try:
            row = db.query_one(
                f"SELECT MAX(season_year) AS yr FROM {table}"
            )
            if row and row.get("yr"):
                return int(row["yr"])
        except Exception:
            continue

    today = _dt.date.today()
    # CFB season: August onwards = current year; Jan–July = prior year
    return today.year if today.month >= 8 else today.year - 1


# ---------------------------------------------------------------------------
# Batch driver
# ---------------------------------------------------------------------------


def run_tier_batch(
    db: Any,
    tier: CardTier,
    router: Router,
    config: PipelineConfig | None = None,
    max_cards: int = 0,
    card_types_override: list[str] | None = None,
    batch_id: str | None = None,
) -> list[PageResult]:
    """Top-level batch driver — generates cards for all entities in a tier.

    Args:
        db:                   Database with query_all / query_one / execute.
        tier:                 CardTier enum value.
        router:               Pre-built Router from build_default_router().
        config:               PipelineConfig; defaults to PipelineConfig.for_tier(tier).
        max_cards:            Hard cap on page targets processed (0 = no cap).
        card_types_override:  Override the tier-default card types for all targets.
        batch_id:             Stable batch identifier for antislop observations.

    Returns:
        list[PageResult] in the order processed.
    """
    if config is None:
        config = PipelineConfig.for_tier(tier)

    if batch_id is None:
        batch_id = str(uuid.uuid4())[:8]

    targets = _select_entities_for_tier(db, tier, max_count=max_cards)

    if card_types_override:
        targets = [
            PageTarget(
                entity_kind=t.entity_kind,
                slug=t.slug,
                season_year=t.season_year,
                week_number=t.week_number,
                n_slots=t.n_slots,
                card_types=card_types_override,
                tier=t.tier,
                page_thesis_hint=t.page_thesis_hint,
            )
            for t in targets
        ]

    # CHRONICLE_PARALLEL_WORKERS: how many page targets to process concurrently.
    # Default 1 = fully serial (backward-compatible).
    # Set to 4 when running llama-server with --parallel 4 to saturate all GPU
    # slots. Do NOT combine with MTP (speculative decoding) — they conflict.
    # Database is thread-safe (new sqlite3 connection per call). Router and
    # config are read-only and safe to share across threads.
    n_workers = max(1, int(os.environ.get("CHRONICLE_PARALLEL_WORKERS", "1")))

    log.info(
        "run_tier_batch: tier=%s batch_id=%s targets=%d workers=%d",
        tier.value, batch_id, len(targets), n_workers,
    )

    def _process_one(target: PageTarget) -> PageResult:
        log.info(
            "run_tier_batch: processing %s/%s", target.entity_kind, target.slug
        )
        page_result = generate_page_cards(db, target, router, config)
        page_result.batch_id = batch_id
        log.info(
            "run_tier_batch: %s/%s done — shipped=%d suppressed=%d failed=%d ms=%d",
            target.entity_kind, target.slug,
            page_result.shipped_count, page_result.suppressed_count,
            page_result.failed_count, page_result.wall_clock_ms,
        )
        return page_result

    if n_workers == 1:
        # Serial path — identical to original behaviour, no overhead
        results: list[PageResult] = [_process_one(t) for t in targets]
    else:
        # Parallel path — ThreadPoolExecutor preserves submission order via map()
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as pool:
            results = list(pool.map(_process_one, targets))

    total_shipped = sum(r.shipped_count for r in results)
    total_suppressed = sum(r.suppressed_count for r in results)
    total_failed = sum(r.failed_count for r in results)
    log.info(
        "run_tier_batch: complete — pages=%d shipped=%d suppressed=%d failed=%d",
        len(results), total_shipped, total_suppressed, total_failed,
    )

    return results


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "PageTarget",
    "PipelineConfig",
    "CardResult",
    "PageResult",
    "generate_page_cards",
    "generate_card",
    "run_tier_batch",
]
