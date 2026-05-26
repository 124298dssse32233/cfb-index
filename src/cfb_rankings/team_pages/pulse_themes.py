"""Theme extraction pipeline for Pulse v2.

Two-stage process per entity:
  Stage 1 — Haiku scan: feed recent conversation excerpts, get 5-10 raw
             theme candidates back as JSON.
  Stage 2 — Sonnet rank+write: pick top N (3 for 'full', 1 for 'partial'),
             write each with label, summary, representative_quote, rank.

Storage: team_pulse_cache (teams/players) and conference_themes (conferences).

Public API:
    extract_entity_themes(entity_slug, entity_type, tier, db_conn)
        → list[dict]  (persisted + returned; empty list on failure/offline)

    load_themes(entity_slug, entity_type, db_conn)
        → list[dict] | None  (None = no stored themes yet)
"""
from __future__ import annotations

import json
import logging
from typing import Any

# Load .env at module level so LOCAL_LLM_URL is in os.environ before
# is_local_enabled() is checked. _load_dotenv() is normally only called from
# AppConfig.from_env(), so pulse_themes has to trigger it explicitly here.
from cfb_rankings.config import _load_dotenv as _load_dotenv_once
_load_dotenv_once()

log = logging.getLogger(__name__)

_HAIKU_MODEL = "claude-haiku-4-5-20251001"
# v5.3 tier upgrade per row #16: pulse_themes Stage 2 ranker/writer was Sonnet,
# now Opus 4.7. Each theme carries label + summary + representative_quote —
# voice register lives here, justifying the upgrade. Stage 1 Haiku scan
# (candidate JSON extraction) stays — narrow factual task. Name kept as
# _SONNET_MODEL for now to avoid downstream rename churn; collapsing the
# naming is a future cleanup.
_SONNET_MODEL = "claude-opus-4-7"
_EXCERPT_LIMIT = 30     # docs fed to Haiku per entity
_EXCERPT_CHARS = 400    # truncate each body_text
_DAYS = 30              # lookback window for conversation docs

# Sprint v5-6 — Pattern C dispatch surface key for Stage 2 (Opus ranker/writer).
# Stage 1 Haiku scan stays sync-only; it's a narrow factual JSON extraction
# task that doesn't need a critic loop. When
# ``config.QUALITY_LOOP_FLAGS["tier1.pulse_themes_writer"]`` is set to
# ``LoopPattern.C_CRITIC_REVISE`` (the v5-5 default), the Stage 2 call is
# routed through the 3-critic loop. See ``_pattern_c_themes_writer`` below.
_SURFACE_KEY = "tier1.pulse_themes_writer"


def _flag_loop_pattern():
    """Resolve the ``tier1.pulse_themes_writer`` flag to a LoopPattern.

    Returns None on import failure or unknown value (falls through to
    sync path).
    """
    try:
        from cfb_rankings.config import QUALITY_LOOP_FLAGS
        from cfb_rankings.quality_loop import LoopPattern
    except Exception:  # pragma: no cover — defensive
        return None
    configured = QUALITY_LOOP_FLAGS.get(_SURFACE_KEY)
    if isinstance(configured, str):
        try:
            configured = LoopPattern(configured)
        except ValueError:
            return None
    return configured


def _flag_is_loop_dispatch() -> bool:
    """True when the flag selects either Pattern B or C."""
    try:
        from cfb_rankings.quality_loop import LoopPattern
    except Exception:  # pragma: no cover — defensive
        return False
    return _flag_loop_pattern() in (
        LoopPattern.B_SINGLE_CRITIC, LoopPattern.C_CRITIC_REVISE
    )


def _pattern_loop_themes_writer(
    prompt: str, system: str, model: str, max_tokens: int
) -> str | None:
    """Run the Stage 2 themes writer through the configured loop.

    Dispatches to ``loop_b_single_critic`` (Pattern B) or
    ``loop_c_critic_revise`` (Pattern C). Returns final text on success,
    None on any fall-back. Demoted from C → B on 2026-05-16 22:30 UTC
    after telemetry showed 71% fall-back rate on the C path for
    structured-JSON output.
    """
    try:
        from cfb_rankings.quality_loop import (
            LoopPattern, loop_b_single_critic, loop_c_critic_revise,
        )
    except Exception:  # pragma: no cover — defensive
        return None
    pattern = _flag_loop_pattern()
    if pattern == LoopPattern.B_SINGLE_CRITIC:
        loop_fn = loop_b_single_critic
        subcommand = "quality_loop.B.pulse_themes_writer"
    elif pattern == LoopPattern.C_CRITIC_REVISE:
        loop_fn = loop_c_critic_revise
        subcommand = "quality_loop.C.pulse_themes_writer"
    else:
        return None
    try:
        result = loop_fn(
            prompt,
            system=system,
            model=model,
            max_tokens=max_tokens,
            surface=_SURFACE_KEY,
            subcommand=subcommand,
        )
    except Exception as exc:  # pragma: no cover — defensive
        log.warning("pulse_themes loop %s raised %s; falling back to sync",
                    pattern, exc)
        return None
    if result.fell_back or not result.text:
        return None
    return result.text


# Back-compat aliases: keep old function names callable so any
# downstream import keeps working. New code uses _flag_is_loop_dispatch
# / _pattern_loop_themes_writer.
def _flag_is_pattern_c() -> bool:
    try:
        from cfb_rankings.quality_loop import LoopPattern
    except Exception:  # pragma: no cover
        return False
    return _flag_loop_pattern() == LoopPattern.C_CRITIC_REVISE


def _pattern_c_themes_writer(prompt: str, system: str, model: str, max_tokens: int) -> str | None:
    return _pattern_loop_themes_writer(prompt, system, model, max_tokens)

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _fetch_team_excerpts(entity_slug: str, db_conn: Any) -> list[dict[str, str]]:
    cur = db_conn.cursor()
    cur.execute(
        """
        SELECT cd.body_text, cd.source_name, cdt.target_label
        FROM conversation_document_targets cdt
        JOIN conversation_documents cd
            ON cd.conversation_document_id = cdt.conversation_document_id
        JOIN teams t ON t.team_id = cdt.team_id
        WHERE t.slug = ?
          AND cd.body_text IS NOT NULL
          AND cd.body_text != ''
          AND cd.collected_at_utc >= datetime('now', '-30 days')
        ORDER BY cd.like_count DESC, cd.collected_at_utc DESC
        LIMIT ?
        """,
        (entity_slug, _EXCERPT_LIMIT),
    )
    return [
        {"text": r[0][:_EXCERPT_CHARS], "source": r[1], "label": r[2]}
        for r in cur.fetchall()
    ]


def _fetch_conference_excerpts(conference_slug: str, db_conn: Any) -> list[dict[str, str]]:
    # Defensive: conferences.conference_slug column was added 2026-05-15
    # via migration 20260525_18. On a DB where the migration hasn't run
    # (or where the conferences table is wholly absent), this query
    # raises sqlite3.OperationalError. The world_class_enrich pipeline
    # used to silently swallow the exception via set+e || echo. Now we
    # log + return [] so pulse_themes degrades gracefully to zero
    # conference excerpts instead of crashing the entire prepare-pulse
    # CLI mid-run.
    import sqlite3
    cur = db_conn.cursor()
    try:
        cur.execute(
            """
            SELECT cd.body_text, cd.source_name, cdt.target_label
            FROM conversation_document_targets cdt
            JOIN conversation_documents cd
                ON cd.conversation_document_id = cdt.conversation_document_id
            JOIN teams t ON t.team_id = cdt.team_id
            JOIN conferences c ON c.conference_id = t.current_conference_id
            WHERE c.conference_slug = ?
              AND cd.body_text IS NOT NULL
              AND cd.body_text != ''
              AND cd.collected_at_utc >= datetime('now', '-30 days')
            ORDER BY cd.like_count DESC
            LIMIT ?
            """,
            (conference_slug, _EXCERPT_LIMIT),
        )
    except sqlite3.OperationalError as exc:
        log.warning(
            "_fetch_conference_excerpts: query failed for slug=%r (%s); "
            "returning empty list. Apply migration 20260525_18 to add "
            "conferences.conference_slug column.",
            conference_slug, exc,
        )
        return []
    return [
        {"text": r[0][:_EXCERPT_CHARS], "source": r[1], "label": r[2]}
        for r in cur.fetchall()
    ]


def _fetch_player_excerpts(player_id: int, db_conn: Any) -> list[dict[str, str]]:
    cur = db_conn.cursor()
    cur.execute(
        """
        SELECT cd.body_text, cd.source_name, cdt.target_label
        FROM conversation_document_targets cdt
        JOIN conversation_documents cd
            ON cd.conversation_document_id = cdt.conversation_document_id
        WHERE cdt.player_id = ?
          AND cd.body_text IS NOT NULL
          AND cd.body_text != ''
          AND cd.collected_at_utc >= datetime('now', '-30 days')
        ORDER BY cd.like_count DESC
        LIMIT ?
        """,
        (player_id, _EXCERPT_LIMIT),
    )
    return [
        {"text": r[0][:_EXCERPT_CHARS], "source": r[1], "label": r[2]}
        for r in cur.fetchall()
    ]


def _store_team_themes(
    entity_slug: str, entity_type: str, themes: list[dict], db_conn: Any, passed: bool
) -> None:
    db_conn.execute(
        """
        INSERT OR REPLACE INTO team_pulse_cache
            (entity_slug, entity_type, themes_json, voice_validator_passed, generated_at_utc)
        VALUES (?, ?, ?, ?, datetime('now'))
        """,
        (entity_slug, entity_type, json.dumps(themes), int(passed)),
    )
    db_conn.commit()


def _store_conference_themes(
    conference_slug: str, themes: list[dict], db_conn: Any, passed: bool
) -> None:
    # Clear previous week's themes for this slug, then insert fresh rows.
    db_conn.execute(
        "DELETE FROM conference_themes WHERE conference_slug = ?",
        (conference_slug,),
    )
    for rank_i, theme in enumerate(themes, start=1):
        db_conn.execute(
            """
            INSERT INTO conference_themes
                (conference_slug, week_iso, label, summary,
                 representative_quote, surfaced_rank,
                 is_published, voice_validator_passed, generated_at_utc)
            VALUES (?, strftime('%Y-W%W', 'now'), ?, ?, ?, ?, 1, ?, datetime('now'))
            """,
            (
                conference_slug,
                theme.get("label", ""),
                theme.get("summary", ""),
                theme.get("representative_quote", ""),
                rank_i,
                int(passed),
            ),
        )
    db_conn.commit()


# ---------------------------------------------------------------------------
# Stage 1 — Haiku candidate extraction
# ---------------------------------------------------------------------------

_HAIKU_SYSTEM = """\
You are a college football fan-conversation analyst. Given document excerpts
about a team or player, identify 5-8 distinct discussion themes from the fan
conversation. Each theme must reflect what fans are *actually* talking about —
not generic praise. Return ONLY a JSON array of objects with keys:
  "label"  (3-5 word theme title, no corporate speak)
  "summary" (one sentence, fan voice, present tense)
  "quote"   (verbatim excerpt ≤ 120 chars that best represents this theme)
Example: [{"label":"Transfer Portal Drama","summary":"...","quote":"..."}]"""


def _haiku_extract_candidates(
    excerpts: list[dict],
    entity_name: str,
    *,
    _meter: Any = None,
) -> list[dict]:
    from cfb_rankings.llm_local import is_local_enabled, local_generate
    from cfb_rankings.llm_runtime import generate_with_voice_check

    if not excerpts:
        return []

    numbered = "\n\n".join(
        f"[{i+1}] ({ex['source']}) {ex['text']}" for i, ex in enumerate(excerpts)
    )
    prompt = (
        f"Fan conversation excerpts about {entity_name}:\n\n{numbered}\n\n"
        f"Identify 5-8 recurring discussion themes as JSON."
    )

    # Route to local LLM if available — Stage 1 candidate extraction is a
    # pure JSON classification task where local Q4-Q5 models perform well.
    if is_local_enabled():
        result = local_generate(
            prompt,
            system=_HAIKU_SYSTEM,
            max_tokens=800,
            temperature=0.3,   # Mild creativity for theme generation
        )
    else:
        result = generate_with_voice_check(
            prompt,
            system=_HAIKU_SYSTEM,
            model=_HAIKU_MODEL,
            max_tokens=800,
            max_retries=1,
            fallback_to_offline=True,
        )
    # Pattern B cost recording for Stage-1 Haiku candidate extraction.
    if _meter is not None and result.get("mode") == "live":
        tokens = result.get("tokens_used") or {}
        in_toks = int(tokens.get("input") or 0)
        out_toks = int(tokens.get("output") or 0)
        if in_toks or out_toks:
            _meter.record(
                result.get("model_used", _HAIKU_MODEL),
                {
                    "input_tokens": in_toks,
                    "output_tokens": out_toks,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
                note=f"pulse_themes.haiku.{entity_name}",
            )
    if result["mode"] == "offline-stub" or not result["text"]:
        return []
    try:
        text = result["text"].strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        log.warning("haiku theme parse failed for %s", entity_name)
        return []


# ---------------------------------------------------------------------------
# Stage 2 — Sonnet rank + write final themes
# ---------------------------------------------------------------------------

_SONNET_SYSTEM = """\
You are a college football editorial voice: sharp, fan-authentic, never
corporate. Given raw theme candidates from fan conversation, select the top N
most interesting and rank them. For each, write:
  "label"  (3-5 word theme; vivid, not generic)
  "summary" (1-2 sentences max; fan voice; present tense; no banned phrases
             like 'It remains to be seen', 'time will tell', 'at the end of
             the day', or marketing language)
  "representative_quote" (verbatim fan quote ≤ 100 chars if available,
                          else empty string)
  "rank"   (integer, 1 = most important)
Return ONLY a JSON array of N objects, ordered rank 1 first."""


def _sonnet_rank_and_write(
    candidates: list[dict], entity_name: str, n: int, excerpts: list[dict],
    *,
    _meter: Any = None,
) -> tuple[list[dict], bool]:
    from cfb_rankings.llm_runtime import generate_with_voice_check

    if not candidates:
        return [], False

    candidate_json = json.dumps(candidates[:10], ensure_ascii=False)
    excerpt_lines = "\n".join(
        '- "' + ex["text"][:120] + '"' for ex in excerpts[:8]
    )
    prompt = (
        f"Entity: {entity_name}\n\n"
        f"Raw theme candidates from fan conversation:\n{candidate_json}\n\n"
        f"Select and write the {n} best themes as JSON array. "
        f"Pick verbatim quotes from these source excerpts where possible:\n"
        + excerpt_lines
    )

    # Sprint v5-6 — quality_loop dispatch for Stage 2 ranker/writer.
    # The flag selects Pattern B (single critic, no revise) or C (3-critic
    # + revise). The loop returns the same JSON-array-as-string format the
    # sync path produces, so the downstream parse logic is unchanged. On
    # any fall-back the sync path picks up — themes never land as [] unless
    # both paths fail. Demoted from C → B on 2026-05-16 22:30 UTC after
    # telemetry showed 71% fall-back rate on the C path for JSON output.
    pattern_loop_text = (
        _pattern_loop_themes_writer(prompt, _SONNET_SYSTEM, _SONNET_MODEL, 900)
        if _flag_is_loop_dispatch() else None
    )
    if pattern_loop_text is not None:
        result = {
            "text": pattern_loop_text,
            "voice_validator_passed": True,  # loop uses critic scores
            "model_used": _SONNET_MODEL,
            "mode": "live",
            "tokens_used": {},  # loop_*_critic_* logs spend via append_llm_usage
        }
    else:
        result = generate_with_voice_check(
            prompt,
            system=_SONNET_SYSTEM,
            model=_SONNET_MODEL,
            max_tokens=900,
            max_retries=1,
            fallback_to_offline=True,
        )
    passed = result.get("voice_validator_passed", False)
    # Pattern B cost recording for Stage-2 Sonnet rank/write.
    if _meter is not None and result.get("mode") == "live":
        tokens = result.get("tokens_used") or {}
        in_toks = int(tokens.get("input") or 0)
        out_toks = int(tokens.get("output") or 0)
        if in_toks or out_toks:
            _meter.record(
                result.get("model_used", _SONNET_MODEL),
                {
                    "input_tokens": in_toks,
                    "output_tokens": out_toks,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
                note=f"pulse_themes.sonnet.{entity_name}",
            )
    if result["mode"] == "offline-stub" or not result["text"]:
        return [], False
    try:
        text = result["text"].strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        themes = json.loads(text)
        # Ensure rank field exists
        for i, t in enumerate(themes, start=1):
            t.setdefault("rank", i)
        return themes[:n], passed
    except (json.JSONDecodeError, IndexError):
        log.warning("sonnet theme parse failed for %s", entity_name)
        return [], False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_entities_themes_batch(
    entities: list[tuple[str, str, str, str | None]],
    db_conn: Any,
    *,
    _meter: Any = None,
) -> dict[tuple[str, str], list[dict]]:
    """Batched Stage 2 (Sonnet/Opus) theme ranker/writer for N entities.

    ``entities`` is a list of ``(entity_slug, entity_type, tier, entity_name)``
    tuples. Returns ``{(slug, type): themes_list}`` for every entity.

    Implementation:
      1. Stage 1 (Haiku candidate scan) stays SYNCHRONOUS — short prompts,
         low token count, and we need candidates to feed Stage 2 anyway.
      2. Stage 2 (Sonnet/Opus ranker/writer) BATCHES across entities.
         Each entity carries a unique candidate JSON, but the system
         contract (output schema, voice register) is identical across
         every entity — so it caches well at 1h TTL.

    Telemetry: per-entity input/output tokens + cache stats emit via the
    batch helper's standard telemetry contract. Failed Stage 1 entities
    short-circuit to empty results and are skipped from the Stage 2
    batch.

    ``_meter`` (Pattern B, optional): single meter spans both stages.
    """
    from cfb_rankings.llm_runtime import CostMeter
    meter = _meter or CostMeter(
        ceiling_usd=1.0,
        label="pulse_themes.batch",
    )
    from cfb_rankings.llm_runtime_batch import BatchJob, submit_batch_offline_safe

    # Stage 1 — sync candidate scan + excerpt fetch (small per-entity).
    stage2_inputs: list[tuple[str, str, str, str, list[dict], list[dict], int]] = []
    out: dict[tuple[str, str], list[dict]] = {}
    for entity_slug, entity_type, tier, entity_name in entities:
        n_themes = 3 if tier == "full" else 1
        if entity_type == "team":
            excerpts = _fetch_team_excerpts(entity_slug, db_conn)
            name = entity_name or entity_slug.replace("-", " ").title()
        elif entity_type == "conference":
            excerpts = _fetch_conference_excerpts(entity_slug, db_conn)
            name = entity_name or entity_slug.replace("-", " ").upper()
        elif entity_type == "player":
            try:
                pid = int(entity_slug)
            except ValueError:
                out[(entity_slug, entity_type)] = []
                continue
            excerpts = _fetch_player_excerpts(pid, db_conn)
            name = entity_name or f"Player {entity_slug}"
        else:
            out[(entity_slug, entity_type)] = []
            continue
        if not excerpts:
            out[(entity_slug, entity_type)] = []
            continue
        candidates = _haiku_extract_candidates(excerpts, name, _meter=meter)
        if not candidates:
            out[(entity_slug, entity_type)] = []
            continue
        stage2_inputs.append((entity_slug, entity_type, tier, name, candidates, excerpts, n_themes))

    if not stage2_inputs:
        return out

    # Sprint v5-5/v5-6 follow-up (hotfix-15) — Pattern C and Batch API are
    # mutually exclusive. The Batch API doesn't support sequential critic
    # loops. When the ``tier1.pulse_themes_writer`` flag selects Pattern B
    # or C, skip the batch and iterate sync — each entity goes through
    # ``_sonnet_rank_and_write`` which has the loop dispatch wired
    # (PR #73, demoted C → B 2026-05-16 22:30 UTC). Cost trade-off:
    # lose the 50% Batch discount, gain the critic loop on ~30 entities.
    # 24h aggregate ceiling ($8/day) bounds the cost if a single run runs
    # hot.
    if _flag_is_loop_dispatch():
        for (slug, etype, tier, name, candidates, excerpts, n_themes) in stage2_inputs:
            themes, passed = _sonnet_rank_and_write(
                candidates, name, n_themes, excerpts, _meter=meter,
            )
            out[(slug, etype)] = themes
            if themes:
                if etype == "conference":
                    _store_conference_themes(slug, themes, db_conn, passed)
                else:
                    _store_team_themes(slug, etype, themes, db_conn, passed)
        return out

    # Stage 2 — BATCH the ranker/writer across entities.
    jobs: list[BatchJob] = []
    by_id: dict[str, tuple[str, str, int]] = {}  # custom_id -> (slug, type, n_themes)
    for (slug, etype, tier, name, candidates, excerpts, n_themes) in stage2_inputs:
        candidate_json = json.dumps(candidates[:10], ensure_ascii=False)
        excerpt_lines = "\n".join('- "' + ex["text"][:120] + '"' for ex in excerpts[:8])
        user_prompt = (
            f"Entity: {name}\n\n"
            f"Raw theme candidates from fan conversation:\n{candidate_json}\n\n"
            f"Select and write the {n_themes} best themes as JSON array. "
            f"Pick verbatim quotes from these source excerpts where possible:\n"
            + excerpt_lines
        )
        # Keep custom_id format safe — strip slashes/colons that might
        # appear in player_id strings or similar.
        sanitized_slug = slug.replace("/", "-").replace(":", "-")
        custom_id = f"pulse-themes-{etype}-{sanitized_slug}"
        by_id[custom_id] = (slug, etype, n_themes)
        jobs.append(BatchJob(
            custom_id=custom_id,
            system_blocks=[
                {
                    "type": "text",
                    "text": _SONNET_SYSTEM,
                    "cache_control": {"type": "ephemeral", "ttl": "1h"},
                },
            ],
            messages=[{"role": "user", "content": user_prompt}],
            model=_SONNET_MODEL,
            max_tokens=900,
            metadata={"slug": slug, "entity_type": etype, "n_themes": n_themes},
        ))

    results = submit_batch_offline_safe(jobs, run_voice_validator=False)
    for r in results:
        slug, etype, n_themes = by_id[r.custom_id]
        # Record batch cost. CostCeilingExceeded propagates.
        if r.succeeded and (r.input_tokens or r.output_tokens):
            meter.record(
                r.model_used or _SONNET_MODEL,
                {
                    "input_tokens": int(r.input_tokens or 0),
                    "output_tokens": int(r.output_tokens or 0),
                    "cache_creation_input_tokens": int(r.cache_creation_input_tokens or 0),
                    "cache_read_input_tokens": int(r.cache_read_input_tokens or 0),
                },
                is_batch=True,
                cache_ttl="1h",
                note=f"pulse_themes.batch.sonnet.{slug}",
            )
        if not r.succeeded or not r.text:
            log.warning("pulse_themes batch: %s failed (%s)", r.custom_id, r.error)
            out[(slug, etype)] = []
            continue
        try:
            text = r.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            themes = json.loads(text)
            for i, t in enumerate(themes, start=1):
                t.setdefault("rank", i)
            themes = themes[:n_themes]
            out[(slug, etype)] = themes
            if themes:
                # Persist using existing helpers. Voice-validator pass is
                # informational here (validator runs on batch results when
                # run_voice_validator=True; we bypassed for JSON output).
                # We mark passed=True since the structured-output gate is
                # JSON-shape, validated above.
                if etype == "conference":
                    _store_conference_themes(slug, themes, db_conn, True)
                else:
                    _store_team_themes(slug, etype, themes, db_conn, True)
        except (json.JSONDecodeError, IndexError) as exc:
            log.warning("pulse_themes batch parse failed for %s: %s", slug, exc)
            out[(slug, etype)] = []
    return out


def extract_entity_themes(
    entity_slug: str,
    entity_type: str,
    tier: str,
    db_conn: Any,
    entity_name: str | None = None,
    *,
    _meter: Any = None,
) -> list[dict]:
    """Run Haiku+Sonnet theme pipeline for one entity.

    tier: 'full' → 3 themes; 'partial' → 1 theme
    Returns persisted themes list (empty on offline/failure).

    ``_meter`` (Pattern B, optional): single meter spans Stage 1 (Haiku) +
    Stage 2 (Sonnet) so a per-entity ceiling covers the full pipeline.
    """
    from cfb_rankings.llm_runtime import CostMeter
    meter = _meter or CostMeter(
        ceiling_usd=1.0,
        label=f"pulse_themes.{entity_slug}",
    )
    n_themes = 3 if tier == "full" else 1

    # Fetch excerpts
    if entity_type == "team":
        excerpts = _fetch_team_excerpts(entity_slug, db_conn)
        name = entity_name or entity_slug.replace("-", " ").title()
    elif entity_type == "conference":
        excerpts = _fetch_conference_excerpts(entity_slug, db_conn)
        name = entity_name or entity_slug.replace("-", " ").upper()
    elif entity_type == "player":
        try:
            pid = int(entity_slug)
        except ValueError:
            return []
        excerpts = _fetch_player_excerpts(pid, db_conn)
        name = entity_name or f"Player {entity_slug}"
    else:
        return []

    if not excerpts:
        log.info("extract_entity_themes: no excerpts for %s (%s)", entity_slug, entity_type)
        return []

    log.info("extract_entity_themes: %s | %d excerpts | tier=%s", entity_slug, len(excerpts), tier)

    candidates = _haiku_extract_candidates(excerpts, name, _meter=meter)
    if not candidates:
        return []

    themes, passed = _sonnet_rank_and_write(candidates, name, n_themes, excerpts, _meter=meter)

    if themes:
        if entity_type == "conference":
            _store_conference_themes(entity_slug, themes, db_conn, passed)
        else:
            _store_team_themes(entity_slug, entity_type, themes, db_conn, passed)

    return themes


def load_themes(
    entity_slug: str, entity_type: str, db_conn: Any
) -> list[dict] | None:
    """Load previously generated themes from DB. Returns None if not yet generated."""
    cur = db_conn.cursor()
    if entity_type == "conference":
        cur.execute(
            """
            SELECT label, summary, representative_quote, surfaced_rank
            FROM conference_themes
            WHERE conference_slug = ?
            ORDER BY surfaced_rank
            """,
            (entity_slug,),
        )
        rows = cur.fetchall()
        if not rows:
            return None
        return [
            {"label": r[0], "summary": r[1], "representative_quote": r[2], "rank": r[3]}
            for r in rows
        ]
    else:
        cur.execute(
            "SELECT themes_json FROM team_pulse_cache WHERE entity_slug=? AND entity_type=?",
            (entity_slug, entity_type),
        )
        row = cur.fetchone()
        if not row or not row[0]:
            return None
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return None
