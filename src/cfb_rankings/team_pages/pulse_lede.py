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


def _flag_loop_pattern():
    """Resolve the ``tier1.pulse_lede`` flag to a LoopPattern, or None.

    Defensive: any import failure or unknown value returns None → sync
    path. Called on every entity rather than cached because the
    quality-loop-reenable CLI mutates the flag dict in-process.
    """
    try:
        from cfb_rankings.config import QUALITY_LOOP_FLAGS
        from cfb_rankings.quality_loop import LoopPattern
    except Exception:  # pragma: no cover — defensive
        return None
    configured = QUALITY_LOOP_FLAGS.get(_SURFACE_KEY)
    if isinstance(configured, str):  # raw-string fallback path in config
        try:
            configured = LoopPattern(configured)
        except ValueError:
            return None
    return configured


def _flag_is_loop_dispatch() -> bool:
    """True when the flag selects either Pattern B or C (i.e. a loop
    dispatch, not the sync path).

    Pattern A and absent values both fall through to the sync path —
    Pattern A is effectively what sync is now (single shot + regex
    voice validator), and there's no need to add a second layer.
    """
    try:
        from cfb_rankings.quality_loop import LoopPattern
    except Exception:  # pragma: no cover — defensive
        return False
    configured = _flag_loop_pattern()
    return configured in (LoopPattern.B_SINGLE_CRITIC, LoopPattern.C_CRITIC_REVISE)


def _pattern_loop_lede(prompt: str, model: str) -> str | None:
    """Run the lede through the configured loop and return final text.

    Dispatches to ``loop_b_single_critic`` (Pattern B) or
    ``loop_c_critic_revise`` (Pattern C) based on the surface flag. On
    any fall-back (offline-stub, wall-clock timeout, Rung-2 critic
    failure, Rung-3 weekly ceiling, 24h auto-disable) returns None and
    the caller picks up the sync path. The demote 2026-05-16 moved this
    surface from C to B because the 3-critic loop rejected 100% of
    short-form pulse output as `consecutive_critic_failures_after_escalation`.
    """
    try:
        from cfb_rankings.quality_loop import (
            LoopPattern,
            loop_b_single_critic,
            loop_c_critic_revise,
        )
    except Exception:  # pragma: no cover — defensive
        return None
    pattern = _flag_loop_pattern()
    if pattern == LoopPattern.B_SINGLE_CRITIC:
        loop_fn = loop_b_single_critic
        subcommand = "quality_loop.B.pulse_lede"
    elif pattern == LoopPattern.C_CRITIC_REVISE:
        loop_fn = loop_c_critic_revise
        subcommand = "quality_loop.C.pulse_lede"
    else:
        return None
    try:
        result = loop_fn(
            prompt,
            system=_SYSTEM_PROMPT,
            model=model,
            max_tokens=200,
            surface=_SURFACE_KEY,
            subcommand=subcommand,
        )
    except Exception as exc:  # pragma: no cover — defensive
        log.warning("pulse_lede loop %s raised %s; falling back to sync",
                    pattern, exc)
        return None
    if result.fell_back or not result.text:
        return None
    return result.text


# Back-compat alias retained briefly to avoid breaking import paths in
# any downstream module that imported the old _flag_is_pattern_c name.
# Returns True only when the flag is exactly Pattern C — which now means
# False for pulse_lede after the demote. New code uses the broader
# `_flag_is_loop_dispatch` to cover both B and C.
def _flag_is_pattern_c() -> bool:
    try:
        from cfb_rankings.quality_loop import LoopPattern
    except Exception:  # pragma: no cover
        return False
    return _flag_loop_pattern() == LoopPattern.C_CRITIC_REVISE


# Back-compat alias for the old function name. New code calls
# _pattern_loop_lede which dispatches on the actual flag value.
def _pattern_c_lede(prompt: str, model: str) -> str | None:
    return _pattern_loop_lede(prompt, model)


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

    # Sprint v5-5 follow-up (hotfix-15) — loop dispatch / Batch API are
    # mutually exclusive. When the ``tier1.pulse_lede`` flag selects
    # Pattern B or C, skip the batch and iterate sync — each entity goes
    # through ``generate_entity_lede`` which has the loop dispatch wired
    # (PR #72, demoted to B 2026-05-16 22:30 UTC). Lose 50% Batch
    # discount, gain the critic loop on each lede. 24h aggregate ceiling
    # ($5/day in DAILY_AGGREGATE_CEILINGS_USD) bounds the cost.
    if _flag_is_loop_dispatch():
        out: dict[tuple[str, str], dict[str, Any]] = {}
        for (entity_slug, entity_type, themes, model_tier, entity_name) in entities:
            result = generate_entity_lede(
                entity_slug, entity_type, themes, model_tier, db_conn,
                entity_name=entity_name, _meter=meter,
            )
            out[(entity_slug, entity_type)] = {
                "text": result.get("text"),
                "voice_validator_passed": result.get("voice_validator_passed", False),
                "model_used": result.get("model_used", _model_for_tier(model_tier)),
                "mode": result.get("mode", "live"),
            }
        return out

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

    # Sprint v5-5 — quality_loop dispatch. The flag selects Pattern B
    # (single critic, no revise loop) or Pattern C (3-critic + revise).
    # On any loop fall-back the sync path below picks up — voice never
    # lands as None unless both paths fail. Demoted from C → B on
    # 2026-05-16 22:30 UTC after telemetry showed 100% fall-back rate
    # on the C path for short-form pulse output.
    pattern_loop_text = (
        _pattern_loop_lede(prompt, model) if _flag_is_loop_dispatch() else None
    )
    if pattern_loop_text is not None:
        result = {
            "text": pattern_loop_text,
            "voice_validator_passed": True,  # loop uses critic scores
            "model_used": model,
            "mode": "live",
            "tokens_used": {},  # loop_*_critic_* logs spend via append_llm_usage
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
