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


def _themes_summary(themes: list[dict]) -> str:
    if not themes:
        return "(no specific themes available — write from general context)"
    lines = []
    for t in themes[:3]:
        label = t.get("label", "")
        summary = t.get("summary", "")
        lines.append(f"- {label}: {summary}")
    return "\n".join(lines)


def generate_entity_lede(
    entity_slug: str,
    entity_type: str,
    themes: list[dict],
    model_tier: str,
    db_conn: Any,
    entity_name: str | None = None,
) -> dict[str, Any]:
    """Generate and persist a lede for one entity.

    Returns llm_runtime result dict with 'text' and 'voice_validator_passed'.
    """
    from cfb_rankings.llm_runtime import generate_with_voice_check

    name = entity_name or entity_slug.replace("-", " ").title()
    model = _model_for_tier(model_tier)
    themes_block = _themes_summary(themes)

    prompt = (
        f"Entity: {name} ({entity_type})\n\n"
        f"Current fan conversation themes:\n{themes_block}\n\n"
        f"Write the Lede (2-3 sentences, fan voice, present tense)."
    )

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
