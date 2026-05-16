"""Lede generator for Pulse v2.

One lede per entity: a 2-3 sentence fan-voice editorial statement that
anchors the current moment for that team, conference, or player.

Model routing (v5.3 tier upgrade: ALL entities use Opus 4.7):
  - "opus" tier  → alabama, ohio-state, georgia  (claude-opus-4-7)
  - "sonnet" tier → all other 12 entities        (claude-opus-4-7 — upgraded
    from claude-sonnet-4-6 per v5.3 row #15; form is identical regardless of
    program prestige, so uniform Opus across all entities)

Storage: team_pulse_cache (teams/players). Conference ledes are stored as
         the delta_label field in conference_themes (first theme row).

Public API:
    generate_entity_lede(entity_slug, entity_type, themes, model_tier, db_conn)
        → dict  {"text": str|None, "voice_validator_passed": bool}

    load_lede(entity_slug, entity_type, db_conn)
        → str | None
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

# Sprint v5-5 — Pattern C dispatch surface key. When
# ``config.QUALITY_LOOP_FLAGS["tier1.pulse_lede"]`` is set to
# ``LoopPattern.C_CRITIC_REVISE`` (the v5-5 default), the lede body is
# routed through the 3-critic loop instead of the sync
# generate_with_voice_check path. See ``_pattern_c_lede`` below.
_SURFACE_KEY = "tier1.pulse_lede"

_OPUS_MODEL = "claude-opus-4-7"
# v5.3 tier upgrade: was claude-sonnet-4-6. Pulse lede is the most-read line on
# each team page (2-3 sentences, hero of Pulse module). Uniform Opus across all
# 15 entities — the form is identical regardless of program prestige. Keeping
# the _SONNET_MODEL name + _model_for_tier dispatch so future tier-split is a
# one-line change.
_SONNET_MODEL = "claude-opus-4-7"

_SYSTEM_PROMPT = """\
You are a college football editorial writer who speaks directly to die-hard fans.
Write a Lede — 2 to 3 sharp sentences — that captures the *current moment* for
this team, conference, or player. Rules:
- Fan voice only: honest, vivid, direct. No corporate speak.
- Present tense. No hedging phrases ('it remains to be seen', 'time will tell',
  'at the end of the day', 'going forward', 'in terms of').
- Reference the themes provided. Make it specific, not generic.
- Do NOT start with the entity name. Start mid-thought.
- No sign-off, no byline. Just the lede copy."""


def _model_for_tier(tier: str) -> str:
    return _OPUS_MODEL if tier == "opus" else _SONNET_MODEL


def _flag_is_pattern_c() -> bool:
    """True when the v5-5 ``tier1.pulse_lede`` flag is set to Pattern C.

    Defensive: any failure to import the flag (test isolation, partial
    module load on a stale build) falls back to False → sync path. The
    flag map is checked on every call rather than cached because the
    quality-loop-reenable CLI mutates it in-process when an auto-disable
    is reversed.
    """
    try:
        from cfb_rankings.config import QUALITY_LOOP_FLAGS
        from cfb_rankings.quality_loop import LoopPattern
    except Exception:  # pragma: no cover — defensive
        return False
    configured = QUALITY_LOOP_FLAGS.get(_SURFACE_KEY)
    if isinstance(configured, str):  # raw-string fallback path in config
        try:
            configured = LoopPattern(configured)
        except ValueError:
            return False
    return configured == LoopPattern.C_CRITIC_REVISE


def _pattern_c_lede(prompt: str, model: str) -> str | None:
    """Run the lede through ``loop_c_critic_revise`` and return the
    final text, or None on fall-back.

    The loop's wall-clock timeout, Rung-2 critic-failure handling, and
    Rung-3 weekly-ceiling check all return ``fell_back=True``. The
    caller treats None as "use the sync path" — voice never lands as
    None unless both paths fail.
    """
    try:
        from cfb_rankings.quality_loop import loop_c_critic_revise
    except Exception:  # pragma: no cover — defensive
        return None
    try:
        result = loop_c_critic_revise(
            prompt,
            system=_SYSTEM_PROMPT,
            model=model,
            max_tokens=200,
            surface=_SURFACE_KEY,
            subcommand="quality_loop.C.pulse_lede",
        )
    except Exception as exc:  # pragma: no cover — defensive
        log.warning("pulse_lede Pattern C raised %s; falling back to sync", exc)
        return None
    if result.fell_back or not result.text:
        return None
    return result.text


def _themes_summary(themes: list[dict]) -> str:
    if not themes:
        return "(no specific themes available — write from general context)"
    lines = []
    for t in themes[:3]:
        label = t.get("label", "")
        summary = t.get("summary", "")
        lines.append(f"- {label}: {summary}")
    return "\n".join(lines)


def generate_entity_ledes_batch(
    entities: list[tuple[str, str, list[dict], str, str | None]],
    db_conn: Any,
    *,
    _meter: Any = None,
) -> dict[tuple[str, str], dict[str, Any]]:
    """Batched lede generator for N entities.

    ``entities`` is a list of ``(entity_slug, entity_type, themes, model_tier,
    entity_name)`` tuples. Returns ``{(slug, type): {text, voice_validator_passed,
    model_used}}`` for every entity.

    ``_meter`` (Pattern B, optional): single meter spans the batch.

    Same shared-system-cached + per-entity-user-message pattern as
    pulse_themes.extract_entities_themes_batch. The lede system prompt
    (~250 tokens) caches once per batch; per-entity messages stay tiny
    (just the entity name + 3 themes).
    """
    from cfb_rankings.llm_runtime import CostMeter
    meter = _meter or CostMeter(ceiling_usd=0.5, label="pulse_lede.batch")
    from cfb_rankings.llm_runtime_batch import BatchJob, submit_batch_offline_safe

    jobs: list[BatchJob] = []
    by_id: dict[str, tuple[str, str, str]] = {}  # custom_id -> (slug, type, model)
    for (entity_slug, entity_type, themes, model_tier, entity_name) in entities:
        name = entity_name or entity_slug.replace("-", " ").title()
        model = _model_for_tier(model_tier)
        themes_block = _themes_summary(themes)
        user_prompt = (
            f"Entity: {name} ({entity_type})\n\n"
            f"Current fan conversation themes:\n{themes_block}\n\n"
            f"Write the Lede (2-3 sentences, fan voice, present tense)."
        )
        sanitized_slug = entity_slug.replace("/", "-").replace(":", "-")
        custom_id = f"pulse-lede-{entity_type}-{sanitized_slug}"
        by_id[custom_id] = (entity_slug, entity_type, model)
        jobs.append(BatchJob(
            custom_id=custom_id,
            system_blocks=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral", "ttl": "1h"},
                },
            ],
            messages=[{"role": "user", "content": user_prompt}],
            model=model,
            max_tokens=200,
            metadata={"slug": entity_slug, "entity_type": entity_type},
        ))

    results = submit_batch_offline_safe(jobs)
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for r in results:
        slug, etype, model = by_id[r.custom_id]
        text = r.text
        passed = bool(r.voice_validator_passed)
        # Record batch cost. CostCeilingExceeded propagates out.
        if r.succeeded and (r.input_tokens or r.output_tokens):
            meter.record(
                r.model_used or model,
                {
                    "input_tokens": int(r.input_tokens or 0),
                    "output_tokens": int(r.output_tokens or 0),
                    "cache_creation_input_tokens": int(r.cache_creation_input_tokens or 0),
                    "cache_read_input_tokens": int(r.cache_read_input_tokens or 0),
                },
                is_batch=True,
                cache_ttl="1h",
                note=f"pulse_lede.batch.{slug}",
            )
        if r.succeeded and text and r.mode == "batch":
            if etype == "conference":
                _store_conference_lede(slug, text, model, db_conn, passed)
            else:
                _store_team_lede(slug, etype, text, model, db_conn, passed)
        out[(slug, etype)] = {
            "text": text,
            "voice_validator_passed": passed,
            "model_used": r.model_used,
            "mode": r.mode,
        }
    return out


def generate_entity_lede(
    entity_slug: str,
    entity_type: str,
    themes: list[dict],
    model_tier: str,
    db_conn: Any,
    entity_name: str | None = None,
    *,
    _meter: Any = None,
) -> dict[str, Any]:
    """Generate and persist a lede for one entity.

    Returns llm_runtime result dict with 'text' and 'voice_validator_passed'.

    ``_meter`` (Pattern B, optional): if supplied, records cost against the
    meter after the call. CostCeilingExceeded propagates up.
    """
    from cfb_rankings.llm_runtime import CostMeter, generate_with_voice_check

    meter = _meter or CostMeter(
        ceiling_usd=0.5,
        label=f"pulse_lede.{entity_slug}",
    )

    name = entity_name or entity_slug.replace("-", " ").title()
    model = _model_for_tier(model_tier)
    themes_block = _themes_summary(themes)

    prompt = (
        f"Entity: {name} ({entity_type})\n\n"
        f"Current fan conversation themes:\n{themes_block}\n\n"
        f"Write the Lede (2-3 sentences, fan voice, present tense)."
    )

    # Sprint v5-5 — Pattern C dispatch. When the surface flag is set,
    # route the lede through the 3-critic loop (voice / headline / factuality).
    # On any loop fall-back (offline-stub, wall-clock timeout, Rung-2 critic
    # failure, Rung-3 weekly ceiling, auto-disable) the sync path below
    # picks up — voice never lands as None unless both paths fail.
    pattern_c_text = _pattern_c_lede(prompt, model) if _flag_is_pattern_c() else None
    if pattern_c_text is not None:
        result = {
            "text": pattern_c_text,
            "voice_validator_passed": True,  # Pattern C uses critic scores
            "model_used": model,
            "mode": "live",
            "tokens_used": {},  # CostMeter inside loop_c_critic_revise logs spend
        }
    else:
        result = generate_with_voice_check(
            prompt,
            system=_SYSTEM_PROMPT,
            model=model,
            max_tokens=200,
            max_retries=1,
            fallback_to_offline=True,
        )

    lede_text = result.get("text")
    passed = result.get("voice_validator_passed", False)

    # Pattern B cost recording. Skip offline-stub mode (zero-token).
    if result.get("mode") == "live":
        tokens = result.get("tokens_used") or {}
        in_toks = int(tokens.get("input") or 0)
        out_toks = int(tokens.get("output") or 0)
        if in_toks or out_toks:
            meter.record(
                result.get("model_used", model),
                {
                    "input_tokens": in_toks,
                    "output_tokens": out_toks,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
                note=f"pulse_lede.{entity_slug}",
            )

    if lede_text and result["mode"] == "live":
        if entity_type == "conference":
            _store_conference_lede(entity_slug, lede_text, model, db_conn, passed)
        else:
            _store_team_lede(entity_slug, entity_type, lede_text, model, db_conn, passed)

    return result


def _store_team_lede(
    entity_slug: str,
    entity_type: str,
    lede: str,
    model: str,
    db_conn: Any,
    passed: bool,
) -> None:
    db_conn.execute(
        """
        INSERT INTO team_pulse_cache
            (entity_slug, entity_type, lede, lede_model, voice_validator_passed, generated_at_utc)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(entity_slug, entity_type) DO UPDATE SET
            lede = excluded.lede,
            lede_model = excluded.lede_model,
            voice_validator_passed = excluded.voice_validator_passed,
            generated_at_utc = excluded.generated_at_utc
        """,
        (entity_slug, entity_type, lede, model, int(passed)),
    )
    db_conn.commit()


def _store_conference_lede(
    conference_slug: str,
    lede: str,
    model: str,
    db_conn: Any,
    passed: bool,
) -> None:
    # Store in the first conference_themes row as delta_label (repurposed as lede).
    # If no theme rows exist yet, insert a placeholder row.
    db_conn.execute(
        """
        UPDATE conference_themes SET delta_label = ?
        WHERE conference_slug = ? AND surfaced_rank = 1
        """,
        (lede, conference_slug),
    )
    if db_conn.execute(
        "SELECT changes()"
    ).fetchone()[0] == 0:
        # No theme row exists — insert one to hold the lede.
        db_conn.execute(
            """
            INSERT OR IGNORE INTO conference_themes
                (conference_slug, week_iso, label, summary, delta_label,
                 surfaced_rank, is_published, voice_validator_passed, generated_at_utc)
            VALUES (?, strftime('%Y-W%W','now'), 'Pulse Lede', '', ?, 1, 1, ?, datetime('now'))
            """,
            (conference_slug, lede, int(passed)),
        )
    db_conn.commit()


def load_lede(entity_slug: str, entity_type: str, db_conn: Any) -> str | None:
    """Load previously generated lede from DB. Returns None if not yet generated."""
    cur = db_conn.cursor()
    if entity_type == "conference":
        cur.execute(
            "SELECT delta_label FROM conference_themes WHERE conference_slug=? AND surfaced_rank=1",
            (entity_slug,),
        )
        row = cur.fetchone()
        return row[0] if row else None
    else:
        cur.execute(
            "SELECT lede FROM team_pulse_cache WHERE entity_slug=? AND entity_type=?",
            (entity_slug, entity_type),
        )
        row = cur.fetchone()
        return row[0] if row else None
