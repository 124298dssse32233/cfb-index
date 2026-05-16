"""Story synthesizer for Reaction Stories (Sprint 15 Phase 4).

Calls the LLM (Sonnet default, Opus for surprise_index >= 90 + blue-blood) or
falls back to a deterministic offline stub when no API key is present.

Voice validator gate: retry-once on failure, keep stub on second failure.

Model routing:
  - Sonnet: default
  - Opus: surprise_index >= 90 AND entity is blue-blood / Heisman-tier player
  - Track Opus < 15% of total spend (aspiration, not halt condition)
"""
from __future__ import annotations

import json
import os
import re
import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from .cohort_divergence import CohortData, CohortDivergence
from .data import (
    CohortSplit,
    ReactionStory,
    db_path,
    upsert_cohort_split,
    upsert_story,
    utc_now_iso,
)
from .triggers import TriggerEvent, _TOP25_PROGRAMS

# Voice validator shim — mirrors the receipts pattern
try:
    from cfb_rankings.team_pages.voice_validator import validate as _canonical_validate
except ImportError:
    import importlib.util as _ilu
    import sys as _sys
    from pathlib import Path as _P
    _src = _P(__file__).resolve().parents[1] / "team_pages" / "voice_validator.py"
    _mod_name = "cfb_rankings._reactions_canonical_voice"
    _spec = _ilu.spec_from_file_location(_mod_name, str(_src))
    _mod = _ilu.module_from_spec(_spec)
    _sys.modules[_mod_name] = _mod
    _spec.loader.exec_module(_mod)
    _canonical_validate = _mod.validate


_BLUE_BLOOD_SLUGS: frozenset[str] = frozenset({
    "alabama", "ohio-state", "georgia", "michigan", "texas",
    "notre-dame", "usc", "oklahoma", "penn-state", "lsu",
})

_OFFLINE = not bool(os.environ.get("ANTHROPIC_API_KEY", ""))


# ── Surprise Index ──────────────────────────────────────────────────────────

def _compute_surprise_index(wire_row: dict, cohort_div: CohortDivergence) -> float:
    """0–100 heuristic surprise score.

    Components:
      - Impact label: MAJOR=30, WATCH=15, MINOR=5
      - Cohort sentiment divergence (stat vs casual gap): 0–25
      - Volume concentration (single cohort dominating): 0–20
      - Entity tier bonus: top-25 program = 10, others = 0
      - Random salt for variation: 0–15 (deterministic from wire_id)
    """
    impact_scores = {"MAJOR": 30, "WATCH": 15, "MINOR": 5}
    base = impact_scores.get(wire_row.get("impact_label", "MINOR"), 5)

    sf_sent = cohort_div.stat_folks.sentiment_score
    cf_sent = cohort_div.casual_fans.sentiment_score
    dh_sent = cohort_div.die_hards.sentiment_score
    divergence_score = min(25, abs(sf_sent - cf_sent) * 30 + abs(dh_sent - cf_sent) * 10)

    max_share = max(
        cohort_div.stat_folks.volume_share,
        cohort_div.casual_fans.volume_share,
        cohort_div.die_hards.volume_share,
    )
    concentration = (max_share - 0.33) * 60 if max_share > 0.33 else 0

    entity_slug = wire_row.get("program_slug", "")
    tier_bonus = 10 if entity_slug in _TOP25_PROGRAMS else 0

    salt = (wire_row.get("id", 0) * 7) % 15

    raw = base + divergence_score + concentration + tier_bonus + salt
    return round(min(100.0, max(0.0, raw)), 1)


# ── Offline stub story generator ────────────────────────────────────────────

def _stub_story_body(
    wire_row: dict,
    cohort_div: CohortDivergence,
    surprise_index: float,
) -> tuple[str, str, str]:
    """Return (headline, dek, body_markdown) using wire + cohort data."""
    action = wire_row.get("action", "")
    program_display = wire_row.get("program_display", "the program")
    why_it_matters = wire_row.get("why_it_matters", "")
    occurred_at = wire_row.get("occurred_at", "")[:10]

    pos_match = re.search(r"^(QB|RB|WR|TE|OT|IOL|DL|LB|CB|S|EDGE|K|P|LS)", action)
    position = pos_match.group(1) if pos_match else "player"
    # Capture full player name (handles CamelCase like "GianCarlo" and multi-word)
    actor_name_match = re.search(
        r"(?:QB|RB|WR|TE|OT|IOL|DL|LB|CB|S|EDGE|K|P|LS)\s+([A-Za-z][A-Za-z']+(?:\s+[A-Za-z][A-Za-z']+)*?)(?:\s+transfer|\s+commits|$)",
        action,
    )
    actor_name = actor_name_match.group(1).strip() if actor_name_match else "the transfer"
    from_match = re.search(r"from\s+(.+?)$", action, re.IGNORECASE)
    from_program = from_match.group(1).strip() if from_match else "another program"

    surprise_call = f" ← Surprise Index {surprise_index}" if surprise_index >= 75 else ""

    sf = cohort_div.stat_folks
    cf = cohort_div.casual_fans
    dh = cohort_div.die_hards

    def _quote_pill(q) -> str:
        return f'> "{q.text}" — *{q.attribution}*'

    sf_quotes = "\n\n".join(_quote_pill(q) for q in sf.quotes[:3])
    cf_quotes = "\n\n".join(_quote_pill(q) for q in cf.quotes[:3])
    dh_quotes = "\n\n".join(_quote_pill(q) for q in dh.quotes[:3])

    headline = (
        f"{program_display} Lands {position} {actor_name} from {from_program} — "
        f"And the Fanbase Didn't React the Way You'd Expect"
    )
    dek = (
        f"{why_it_matters} The split between stat folks, regular fans, "
        f"and the boards tells you everything about where {program_display} is right now."
    )

    sentiment_note = ""
    sf_sent_dir = "positive" if sf.sentiment_score > 0.2 else ("negative" if sf.sentiment_score < -0.1 else "cautious")
    cf_sent_dir = "enthusiastic" if cf.sentiment_score > 0.5 else ("muted" if cf.sentiment_score < 0.2 else "warm")
    dh_sent_dir = "measured" if abs(dh.sentiment_score - 0.4) < 0.15 else ("bullish" if dh.sentiment_score > 0.55 else "skeptical")

    body = textwrap.dedent(f"""
    On {occurred_at}, {program_display} announced that {action.lower().rstrip('.')}. {why_it_matters}

    That's the fact. Here's the reaction — and it's more divided than the portal announcement might suggest.

    ## Stat folks said…

    The analytics corner landed {sf_sent_dir}. Volume share was {sf.volume_share:.0%} of total mentions, and the conversation circled around one core question: does the {from_program} production translate?

    {sf_quotes}

    *Mean sentiment among stat-inclined accounts: {sf.sentiment_score:+.2f} ({sf_sent_dir}).*

    ## Regular fans said…

    The general fan base went {cf_sent_dir} — {cf.volume_share:.0%} of total volume, which is the dominant signal. When regular fans are loud, the story is real.

    {cf_quotes}

    *Mean sentiment: {cf.sentiment_score:+.2f} ({cf_sent_dir}).*

    ## Die-hards said…

    The boards — {dh.volume_share:.0%} of mentions — were {dh_sent_dir}. This is the cohort that reads the depth chart before reading the press release.

    {dh_quotes}

    *Mean sentiment: {dh.sentiment_score:+.2f} ({dh_sent_dir}).*

    ## What we're watching

    The next 72 hours will tell us whether this move has legs. Watch for: (1) coaching staff comment at the next presser; (2) competing offers being announced by {actor_name}'s position peers; (3) whether the boards quiet down or keep cooking. If the casual fan energy holds and the stat folks find a number they like, this becomes a consensus win. If the analytics picture stays murky, expect the sentiment divergence to widen by the time camp opens.
    """).strip()

    return headline, dek, body


# ── Cited sources builder ───────────────────────────────────────────────────

def _build_cited_sources(wire_row: dict, cohort_div: CohortDivergence) -> list[dict]:
    sources = []
    for cohort_data in (cohort_div.stat_folks, cohort_div.casual_fans, cohort_div.die_hards):
        for q in cohort_data.quotes[:2]:
            sources.append({
                "attribution": q.attribution,
                "cohort": cohort_data.cohort,
                "text_excerpt": q.text[:120],
            })
    # Also credit the wire source
    if wire_row.get("source_name"):
        sources.append({
            "attribution": wire_row["source_name"],
            "cohort": "wire",
            "text_excerpt": wire_row.get("action", "")[:120],
        })
    return sources[:10]


# ── LLM synthesis (live path) ───────────────────────────────────────────────

_VOICE_EXAMPLES = """\
Example 1: "Nobody panicked when Michigan lost Harbaugh. Or they did, briefly, and then remembered the roster."
Example 2: "The SEC doesn't care that it looks messy from the outside. The inside view is the only one that matters."
Example 3: "College football has always been about managed chaos. The portal just made the chaos visible."
"""


def _llm_synthesize(
    wire_row: dict,
    cohort_div: CohortDivergence,
    surprise_index: float,
    model: str,
    *,
    _meter: "Any" = None,
) -> tuple[str, str, str]:
    """Call Anthropic API to synthesize the story. Returns (headline, dek, body).

    ``_meter`` (Pattern B, optional): if supplied, records this call's cost
    against the meter after the SDK returns. ``CostCeilingExceeded`` from
    ``meter.record`` propagates up to the workflow entry point.
    """
    import anthropic

    entity_name = wire_row.get("program_display", wire_row.get("program_slug", "Unknown"))
    wire_summary = f"{wire_row.get('action', '')} — {wire_row.get('why_it_matters', '')}"

    cohort_struct = json.dumps({
        "stat_folks": {
            "stance": cohort_div.stat_folks.stance,
            "sentiment_score": cohort_div.stat_folks.sentiment_score,
            "volume_share": cohort_div.stat_folks.volume_share,
            "quotes": [{"text": q.text, "attribution": q.attribution}
                       for q in cohort_div.stat_folks.quotes],
        },
        "casual_fans": {
            "stance": cohort_div.casual_fans.stance,
            "sentiment_score": cohort_div.casual_fans.sentiment_score,
            "volume_share": cohort_div.casual_fans.volume_share,
            "quotes": [{"text": q.text, "attribution": q.attribution}
                       for q in cohort_div.casual_fans.quotes],
        },
        "die_hards": {
            "stance": cohort_div.die_hards.stance,
            "sentiment_score": cohort_div.die_hards.sentiment_score,
            "volume_share": cohort_div.die_hards.volume_share,
            "quotes": [{"text": q.text, "attribution": q.attribution}
                       for q in cohort_div.die_hards.quotes],
        },
    }, indent=2)

    surprise_note = (
        f"\nSurprise Index: {surprise_index} (≥75 — mark this as unlikely/surprising in the lede)\n"
        if surprise_index >= 75 else ""
    )

    prompt = textwrap.dedent(f"""
    You are writing a Reaction Story for {entity_name} after {wire_summary}.

    This is a Reaction Story — the editorial product is the COHORT DIVERGENCE, not the event recap.
    Open by acknowledging the event briefly, then pivot HARD to: stat folks said X, regular fans said Y, die-hards said Z. Show why the split matters.

    Audience: college football fans who follow closely. Voice: warm-fan-positioned, knowledgeable, acknowledges CFB's absurdity.

    Required:
    - 350–500 words
    - Headline + dek + body (markdown body)
    - Cite ≥3 named sources verbatim across the 3 cohort sections
    - Each cohort section = 1 paragraph with 2–3 verbatim quotes
    - End with: "What we're watching" — what the next 72h will tell us
    - No banned phrases (don't say: analytics cohort, die-hard cohort, casual cohort, n=, discourse velocity, cohort taxonomy)
    - Use cohort labels naturally ("stat folks", "regular fans", "the boards") — never the internal taxonomy
    {surprise_note}
    Cohort divergence data:
    {cohort_struct}

    Wire event:
    {json.dumps(dict(wire_row), default=str, indent=2)}

    Voice register references:
    {_VOICE_EXAMPLES}

    Output JSON with keys: headline, dek, body (markdown string).
    """).strip()

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=model,
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    # Pattern B: record cost on the meter if one was supplied. We pass
    # the raw SDK usage object — CostMeter understands its attrs.
    if _meter is not None and getattr(msg, "usage", None) is not None:
        _meter.record(model, msg.usage, note="reaction_story")
    raw = msg.content[0].text.strip()

    # Parse JSON response
    try:
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        parsed = json.loads(raw)
        return parsed["headline"], parsed["dek"], parsed["body"]
    except Exception:
        # Fallback: try to extract sections from raw text
        lines = raw.split("\n")
        headline = next((l.lstrip("# ") for l in lines if l.strip()), "Reaction Story")
        dek = next((l for l in lines[1:] if l.strip()), "")
        body = "\n".join(lines[2:]).strip()
        return headline, dek, body


# ── Batched LLM synthesis (cost-optimized path) ─────────────────────────────

_REACTIONS_SHARED_SYSTEM = """You are writing Reaction Stories for a college football editorial site.

The editorial product for a Reaction Story is the COHORT DIVERGENCE, not the event recap. \
Open by acknowledging the event briefly, then pivot HARD to: stat folks said X, regular fans \
said Y, die-hards said Z. Show why the split matters.

Audience: college football fans who follow closely. Voice: warm-fan-positioned, knowledgeable, \
acknowledges CFB's absurdity.

Required for every story:
- 350-500 words
- Headline + dek + body (markdown body)
- Cite at least 3 named sources verbatim across the 3 cohort sections
- Each cohort section = 1 paragraph with 2-3 verbatim quotes
- End with: "What we're watching" — what the next 72h will tell us
- No banned phrases (don't say: analytics cohort, die-hard cohort, casual cohort, n=, discourse velocity, cohort taxonomy)
- Use cohort labels naturally ("stat folks", "regular fans", "the boards") — never the internal taxonomy

Output: a JSON object with keys "headline", "dek", "body" (markdown string). Nothing else.
"""


def _reactions_user_message(
    wire_row: dict,
    cohort_div: CohortDivergence,
    surprise_index: float,
) -> str:
    """Per-story user-turn payload for the batch path."""
    entity_name = wire_row.get("program_display", wire_row.get("program_slug", "Unknown"))
    wire_summary = f"{wire_row.get('action', '')} — {wire_row.get('why_it_matters', '')}"
    cohort_struct = json.dumps({
        "stat_folks": {
            "stance": cohort_div.stat_folks.stance,
            "sentiment_score": cohort_div.stat_folks.sentiment_score,
            "volume_share": cohort_div.stat_folks.volume_share,
            "quotes": [{"text": q.text, "attribution": q.attribution} for q in cohort_div.stat_folks.quotes],
        },
        "casual_fans": {
            "stance": cohort_div.casual_fans.stance,
            "sentiment_score": cohort_div.casual_fans.sentiment_score,
            "volume_share": cohort_div.casual_fans.volume_share,
            "quotes": [{"text": q.text, "attribution": q.attribution} for q in cohort_div.casual_fans.quotes],
        },
        "die_hards": {
            "stance": cohort_div.die_hards.stance,
            "sentiment_score": cohort_div.die_hards.sentiment_score,
            "volume_share": cohort_div.die_hards.volume_share,
            "quotes": [{"text": q.text, "attribution": q.attribution} for q in cohort_div.die_hards.quotes],
        },
    }, indent=2)
    surprise_note = (
        f"Surprise Index: {surprise_index} (>=75 — mark this as unlikely/surprising in the lede)\n"
        if surprise_index >= 75 else ""
    )
    return (
        f"Entity: {entity_name}\n"
        f"Event: {wire_summary}\n"
        f"{surprise_note}\n"
        f"Cohort divergence data:\n{cohort_struct}\n\n"
        f"Wire event:\n{json.dumps(dict(wire_row), default=str, indent=2)}\n\n"
        f"Voice register references:\n{_VOICE_EXAMPLES}\n\n"
        f"Write the Reaction Story now. Output JSON with keys: headline, dek, body."
    )


def synthesize_reactions_batch(
    stories: list[tuple["TriggerEvent", dict, CohortDivergence, str]],
    *,
    _meter: Any = None,
) -> list["ReactionStory"]:
    """Batched generation of N reaction stories.

    Args:
        stories: list of (trigger, wire_row, cohort_div, story_slug) tuples.
        _meter: optional CostMeter (Pattern B). One meter applies across the
            entire batch — if you supply one at the workflow entry point it
            tracks total spend for the run.

    Returns the persisted ReactionStory list. Voice-validator output here
    is informational — the JSON-output contract triggers false positives
    on the fan-voice validator, so the existing per-attempt _canonical_validate
    check on body+headline+dek remains the authoritative gate (with stub
    fallback on validate fail).
    """
    from cfb_rankings.llm_runtime import CostMeter
    meter = _meter or CostMeter(
        ceiling_usd=1.0,
        label="reaction.batch",
    )
    try:
        from cfb_rankings.llm_runtime_batch import BatchJob, submit_batch_offline_safe
    except ImportError as exc:
        print(f"  [reactions.batch] llm_runtime_batch unavailable: {exc} — falling back to sync", flush=True)
        return [generate_reaction(trigger, wire_row, cohort_div, story_slug, _meter=meter)
                for trigger, wire_row, cohort_div, story_slug in stories]

    jobs = []
    by_slug: dict[str, tuple] = {}
    for (trigger, wire_row, cohort_div, story_slug) in stories:
        surprise_index = _compute_surprise_index(wire_row, cohort_div)
        is_blue_blood = trigger.primary_entity_slug in _BLUE_BLOOD_SLUGS
        use_opus = (surprise_index >= 90) and is_blue_blood
        model = "claude-opus-4-7" if use_opus else "claude-sonnet-4-6"
        custom_id = f"reaction-{story_slug}"
        by_slug[custom_id] = (trigger, wire_row, cohort_div, story_slug, surprise_index, model)
        jobs.append(BatchJob(
            custom_id=custom_id,
            system_blocks=[
                {
                    "type": "text",
                    "text": _REACTIONS_SHARED_SYSTEM,
                    "cache_control": {"type": "ephemeral", "ttl": "1h"},
                },
            ],
            messages=[{"role": "user", "content": _reactions_user_message(wire_row, cohort_div, surprise_index)}],
            model=model,
            max_tokens=1200,
            metadata={"story_slug": story_slug, "surprise_index": surprise_index},
        ))

    results = submit_batch_offline_safe(jobs, run_voice_validator=False)
    out: list[ReactionStory] = []
    for r in results:
        (trigger, wire_row, cohort_div, story_slug, surprise_index, model) = by_slug[r.custom_id]
        validator_passed = False
        generation_model = r.model_used or model
        # Record batch cost. Cache fields propagate so cache_read pricing
        # applies. CostCeilingExceeded propagates out of the loop.
        if r.succeeded and (r.input_tokens or r.output_tokens):
            meter.record(
                generation_model,
                {
                    "input_tokens": int(r.input_tokens or 0),
                    "output_tokens": int(r.output_tokens or 0),
                    "cache_creation_input_tokens": int(r.cache_creation_input_tokens or 0),
                    "cache_read_input_tokens": int(r.cache_read_input_tokens or 0),
                },
                is_batch=True,
                cache_ttl="1h",
                note=f"reaction.batch.{story_slug}",
            )
        if r.succeeded and r.text:
            # Parse JSON; on failure or validator fail, drop to stub.
            raw = r.text.strip()
            try:
                if "```json" in raw:
                    raw = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw:
                    raw = raw.split("```")[1].split("```")[0].strip()
                parsed = json.loads(raw)
                headline = parsed["headline"]
                dek = parsed["dek"]
                body = parsed["body"]
            except Exception:
                # Fall back to stub generation
                headline, dek, body = _stub_story_body(wire_row, cohort_div, surprise_index)
                generation_model = "offline-stub-fallback"

            result_v = _canonical_validate(body + " " + headline + " " + dek)
            validator_passed = result_v.passed
            if not validator_passed:
                # Voice validator failed — drop to stub (no batch retries).
                print(f"  [reactions.batch] voice validator failed for {story_slug}; using stub", flush=True)
                headline, dek, body = _stub_story_body(wire_row, cohort_div, surprise_index)
                generation_model = "offline-stub-fallback"
                validator_passed = True
        else:
            print(f"  [reactions.batch] {r.custom_id}: {r.error!r} — using stub", flush=True)
            headline, dek, body = _stub_story_body(wire_row, cohort_div, surprise_index)
            generation_model = "offline-stub-fallback"
            validator_passed = True

        cited_sources = _build_cited_sources(wire_row, cohort_div)
        story = ReactionStory(
            slug=story_slug,
            triggered_by_wire_id=trigger.wire_id,
            triggered_at_utc=utc_now_iso(),
            triggered_by_velocity=trigger.velocity,
            primary_entity_slug=trigger.primary_entity_slug,
            primary_entity_type=trigger.primary_entity_type,
            headline=headline,
            dek=dek,
            body=body,
            surprise_index=surprise_index,
            status="published",
            voice_validator_passed=1 if validator_passed else 0,
            generation_model=generation_model,
            cited_sources_json=json.dumps(cited_sources),
            notes=f"trigger_reason={trigger.trigger_reason}; mode=batch",
        )
        upsert_story(story)
        for cohort_data in (cohort_div.stat_folks, cohort_div.casual_fans, cohort_div.die_hards):
            split = CohortSplit(
                story_slug=story_slug,
                cohort=cohort_data.cohort,
                stance=cohort_data.stance,
                representative_quotes_json=json.dumps(
                    [{"text": q.text, "attribution": q.attribution} for q in cohort_data.quotes]
                ),
                sentiment_score=cohort_data.sentiment_score,
                volume_share=cohort_data.volume_share,
            )
            upsert_cohort_split(split)
        out.append(story)
    return out


# ── Main entry point ────────────────────────────────────────────────────────

def generate_reaction(
    trigger: TriggerEvent,
    wire_row: dict,
    cohort_div: CohortDivergence,
    story_slug: str,
    offline: Optional[bool] = None,
    *,
    _meter: "Any" = None,
) -> ReactionStory:
    """Synthesize + persist a Reaction Story.

    Returns the persisted ReactionStory. Voice validator gate: retry once,
    drop to stub on second failure.

    ``_meter`` (Pattern B, optional): cost meter; per-call default created
    if omitted so standalone calls still hard-fail on runaway spend.
    """
    use_offline = offline if offline is not None else _OFFLINE
    # Lazy import — keep this module importable in minimal environments.
    from cfb_rankings.llm_runtime import CostMeter, CostCeilingExceeded
    meter = _meter or CostMeter(
        ceiling_usd=1.0,
        label=f"reaction.{story_slug}",
    )

    surprise_index = _compute_surprise_index(wire_row, cohort_div)

    # Model routing: Opus only for surprise >= 90 + blue-blood entity
    is_blue_blood = trigger.primary_entity_slug in _BLUE_BLOOD_SLUGS
    use_opus = (not use_offline) and (surprise_index >= 90) and is_blue_blood
    model = "claude-opus-4-7" if use_opus else "claude-sonnet-4-6"

    def _generate(attempt: int) -> tuple[str, str, str]:
        if use_offline:
            return _stub_story_body(wire_row, cohort_div, surprise_index)
        try:
            return _llm_synthesize(
                wire_row, cohort_div, surprise_index, model, _meter=meter,
            )
        except CostCeilingExceeded:
            # Cost ceiling breaches MUST propagate — never swallow.
            raise
        except Exception as exc:
            print(f"  [synthesizer] LLM call failed (attempt {attempt}): {exc}", flush=True)
            return _stub_story_body(wire_row, cohort_div, surprise_index)

    # First attempt
    headline, dek, body = _generate(1)

    # Voice validator gate
    result = _canonical_validate(body + " " + headline + " " + dek)
    validator_passed = result.passed
    generation_model = "offline-stub" if use_offline else model

    if not validator_passed and not use_offline:
        print(f"  [voice-validator] First attempt failed: {result.violations[:2]}", flush=True)
        headline, dek, body = _generate(2)
        result2 = _canonical_validate(body + " " + headline + " " + dek)
        validator_passed = result2.passed
        if not validator_passed:
            print(f"  [voice-validator] Second attempt also failed — using stub", flush=True)
            headline, dek, body = _stub_story_body(wire_row, cohort_div, surprise_index)
            generation_model = "offline-stub-fallback"
            validator_passed = True

    cited_sources = _build_cited_sources(wire_row, cohort_div)

    story = ReactionStory(
        slug=story_slug,
        triggered_by_wire_id=trigger.wire_id,
        triggered_at_utc=utc_now_iso(),
        triggered_by_velocity=trigger.velocity,
        primary_entity_slug=trigger.primary_entity_slug,
        primary_entity_type=trigger.primary_entity_type,
        headline=headline,
        dek=dek,
        body=body,
        surprise_index=surprise_index,
        status="published",
        voice_validator_passed=1 if validator_passed else 0,
        generation_model=generation_model,
        cited_sources_json=json.dumps(cited_sources),
        notes=f"trigger_reason={trigger.trigger_reason}; offline={use_offline}",
    )
    upsert_story(story)

    # Persist cohort splits
    for cohort_data in (cohort_div.stat_folks, cohort_div.casual_fans, cohort_div.die_hards):
        split = CohortSplit(
            story_slug=story_slug,
            cohort=cohort_data.cohort,
            stance=cohort_data.stance,
            representative_quotes_json=json.dumps(
                [{"text": q.text, "attribution": q.attribution} for q in cohort_data.quotes]
            ),
            sentiment_score=cohort_data.sentiment_score,
            volume_share=cohort_data.volume_share,
        )
        upsert_cohort_split(split)

    print(
        f"  [generate-reaction] slug={story_slug} "
        f"model={generation_model} surprise={surprise_index} "
        f"voice_ok={validator_passed}",
        flush=True,
    )
    return story


# ---------------------------------------------------------------------------
# Sprint v5-3 Pattern C flag-flip dispatch — synthesize_reaction_story
#
# Routes the body-generation step of a Reaction Story through
# `quality_loop.loop_c_critic_revise` when
# `QUALITY_LOOP_FLAGS["tier1.reaction_story"] == LoopPattern.C_CRITIC_REVISE`.
# Otherwise short-circuits to the existing sync `_llm_synthesize` path
# (preserving the offline-stub fall-back rail in `generate_reaction`).
# See DESIGN_AUDIT_2026_05_15_v5_3.md Part 1 row #5 and
# IMPLEMENTATION_PLAN.md Part 5.
# ---------------------------------------------------------------------------

import sqlite3 as _rxn_sqlite3
from dataclasses import dataclass as _rxn_dataclass
from typing import TYPE_CHECKING as _RXN_TYPE_CHECKING, Callable as _RxnCallable, Optional as _RxnOptional

from cfb_rankings.quality_loop import (
    LoopPattern as _RxnLoopPattern,
    loop_c_critic_revise as _rxn_loop_c_critic_revise,
)

if _RXN_TYPE_CHECKING:  # pragma: no cover
    from cfb_rankings.db import Database as _RxnDatabase
    from cfb_rankings.quality_loop import LoopResult as _RxnLoopResult


REACTION_STORY_SURFACE_KEY = "tier1.reaction_story"
REACTION_STORY_SUBCOMMAND = "quality_loop.C.reaction_story"

#: Reaction Story target = ~800 words (range 350-800) = ~1200 tokens of
#: output. 2048 leaves headroom for revise-pass guidance.
REACTION_STORY_MAX_TOKENS = 2048


REACTION_STORY_SYSTEM_PROMPT = """You are writing a Reaction Story for \
CFB Index — a wire-triggered piece whose editorial product is the COHORT \
DIVERGENCE, not the event recap. Open by acknowledging the event briefly, \
then pivot HARD to the three-cohort split: stat folks said X, regular \
fans said Y, the boards said Z. Show why the split matters.

VOICE
- Warm-fan-positioned, knowledgeable, acknowledges CFB's absurdity. \
  Never aloof-magazine, never AI marketing copy.
- Use cohort labels naturally ("stat folks", "regular fans", "the \
  boards") — NEVER the internal taxonomy (analytics cohort, casual \
  cohort, die-hard cohort, cohort taxonomy).
- No banned phrases (analytics-cohort, casual-cohort, die-hard-cohort, \
  national-narrative-cohort, n=, effective_n, discourse velocity, signal \
  pipeline, engagement loop, leverage the, delve into, in the realm of, \
  paradigm shift, synergy).

STRUCTURAL CONSTRAINTS
- ~800 words (350-800 acceptable; tentpole reactions can stretch to 800).
- THREE clearly-labeled cohort sections in order:
    "## Stat folks said..."
    "## Regular fans said..."
    "## Die-hards said..." (or "## The boards said...")
- Each cohort section: 1-2 paragraphs of prose + 2-3 verbatim block \
  quotes pulled from the COHORT QUOTES block.
- Closing section labeled "## What we're watching" — what the next 72h \
  will tell us.

VERBATIM QUOTE DISCIPLINE
- Every block quote must trace VERBATIM to the COHORT QUOTES block. The \
  attribution after each quote must match the block's attribution field.
- If a cohort has fewer than 2 quotes, write that section without \
  block-quotes — paraphrase instead. Do not invent.

FACTUALITY
- Every numeric value (volume share, sentiment score), every quoted \
  phrase, every named source must trace to the SOURCE OBSERVATIONS block \
  in the user prompt. Paraphrase prose; never invent.
- If the SURPRISE INDEX >= 75, flag it in the lede ("This is the kind \
  of move nobody priced in").

Output is the story BODY ONLY (markdown with the section headers above) \
— no headline, no dek, no byline. The caller supplies the headline + \
dek separately via the existing renderer."""


def _rxn_format_section(label: str, value: Any) -> str:
    """Render one labeled section."""
    if value is None or value == [] or value == {}:
        return f"{label}:\n(empty — no signal yet for this section)"
    if isinstance(value, (list, dict)):
        try:
            body = json.dumps(value, indent=2, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            body = str(value)
    else:
        body = str(value)
    return f"{label}:\n{body}"


def compose_reaction_prompt_body(context: dict[str, Any]) -> str:
    """Compose the prompt body for a wire-triggered Reaction Story.

    Sections (in order):
        1. WIRE EVENT (program, action, why_it_matters, source_name)
        2. HISTORICAL COMP (the wire's pre-authored comparable, if any)
        3. SURPRISE INDEX (computed; flag >= 75 in lede)
        4. COHORT DIVERGENCE (stat / casual / die-hard 4w split)
        5. COHORT QUOTES (verbatim — for the 3 cohort sections)
        6. MOOD DELTA 7D (program-level Δ this week)
        7. ARCHIVE THREADS (in-flight storyline arcs)
    """
    wire_id = context.get("wire_id", "")
    wire = context.get("wire") or {}
    parts: list[str] = []
    parts.append(
        "SOURCE OBSERVATIONS — every block quote must trace VERBATIM to "
        "the COHORT QUOTES block. Paraphrase prose freely."
    )
    parts.append(f"WIRE ID: {wire_id}")
    parts.append(_rxn_format_section("WIRE EVENT", wire))
    parts.append(_rxn_format_section(
        "HISTORICAL COMP (pre-authored comparable, if any)",
        context.get("historical_comp"),
    ))
    parts.append(_rxn_format_section(
        "SURPRISE INDEX (flag >=75 in lede)",
        context.get("surprise_index"),
    ))
    parts.append(_rxn_format_section(
        "COHORT DIVERGENCE (stat / casual / die-hard 4w split)",
        context.get("cohort_divergence"),
    ))
    parts.append(_rxn_format_section(
        "COHORT QUOTES (verbatim — for the 3 cohort sections)",
        context.get("cohort_quotes"),
    ))
    parts.append(_rxn_format_section(
        "MOOD DELTA 7D",
        context.get("mood_delta_7d"),
    ))
    parts.append(_rxn_format_section(
        "ARCHIVE THREADS",
        context.get("archive_threads"),
    ))
    parts.append(
        "TASK: Write the Reaction Story body. ~800 words (350-800 "
        "acceptable). Three labeled cohort sections + a 'What we're "
        "watching' close. Each cohort section pulls 2-3 verbatim block "
        "quotes from the COHORT QUOTES block. No headline / dek / byline "
        "— the body markdown only."
    )
    return "\n\n".join(parts)


@_rxn_dataclass
class ReactionStoryResult:
    """Outcome of one :func:`synthesize_reaction_story` call.

    ``text`` is the generated body markdown when ``source == "llm"``;
    ``None`` when ``source in ("offline", "none")``. Caller renders the
    existing offline-stub story body when ``text is None``.
    """
    text: _RxnOptional[str]
    source: str  # "llm" | "offline" | "none"
    loop_result: _RxnOptional["_RxnLoopResult"] = None
    fallback_reason: _RxnOptional[str] = None


def _rxn_connection_for_builder(db: "_RxnDatabase") -> _RxnOptional[_rxn_sqlite3.Connection]:
    """Best-effort extraction of an underlying ``sqlite3.Connection``."""
    for attr in ("_raw_conn", "raw_conn", "conn", "_conn", "connection"):
        candidate = getattr(db, attr, None)
        if isinstance(candidate, _rxn_sqlite3.Connection):
            return candidate
    url = getattr(db, "url", None) or getattr(db, "database_url", None)
    if isinstance(url, str) and url.startswith("sqlite:///"):
        try:
            conn = _rxn_sqlite3.connect(url.replace("sqlite:///", "", 1))
            conn.row_factory = _rxn_sqlite3.Row
            return conn
        except _rxn_sqlite3.Error:
            return None
    return None


def synthesize_reaction_story(
    *,
    wire_id: int,
    db: "_RxnDatabase",
    sqlite_conn: _RxnOptional[_rxn_sqlite3.Connection] = None,
    context_builder: _RxnOptional[_RxnCallable[..., dict[str, Any]]] = None,
    fallback: _RxnOptional[_RxnCallable[[int], _RxnOptional[str]]] = None,
) -> "ReactionStoryResult":
    """Generate a Reaction Story body markdown for the wire row ``wire_id``.

    Dispatch rules:

    * Flag set → build context via
      :func:`prompt_context.builders.build_reaction_context`, compose
      prompt body, route through :func:`quality_loop.loop_c_critic_revise`.

    * Flag absent → call ``fallback(wire_id)``. Default fallback returns
      ``None`` so the caller renders the existing offline-stub body via
      :func:`_stub_story_body`.
    """
    try:
        from cfb_rankings.config import QUALITY_LOOP_FLAGS
    except Exception:  # pragma: no cover
        QUALITY_LOOP_FLAGS = {}

    configured = QUALITY_LOOP_FLAGS.get(REACTION_STORY_SURFACE_KEY)
    if isinstance(configured, str):
        try:
            configured = _RxnLoopPattern(configured)
        except ValueError:
            configured = None

    fallback_fn = fallback or (lambda _wid: None)

    # Path 1: flag absent → caller's offline-stub path.
    if configured != _RxnLoopPattern.C_CRITIC_REVISE:
        stub_text = fallback_fn(wire_id)
        return ReactionStoryResult(
            text=stub_text,
            source="offline" if stub_text else "none",
            loop_result=None,
            fallback_reason="flag_absent" if stub_text else "flag_absent_no_stub",
        )

    # Path 2: flag set → LLM path via Pattern C.
    builder = context_builder
    if builder is None:
        from cfb_rankings.prompt_context.builders import (
            build_reaction_context as _default_builder,
        )
        builder = _default_builder

    conn = sqlite_conn
    if conn is None:
        conn = _rxn_connection_for_builder(db)

    context: dict[str, Any] = {"wire_id": wire_id}
    if conn is not None:
        try:
            context = builder(wire_id, conn)
        except Exception as exc:  # pragma: no cover
            print(
                f"  [reactions.v5_3] context builder failed "
                f"({type(exc).__name__}: {exc}); routing through loop with "
                f"empty context",
                flush=True,
            )
            context = {"wire_id": wire_id}

    prompt_body = compose_reaction_prompt_body(context)

    loop_result = _rxn_loop_c_critic_revise(
        prompt_body,
        system=REACTION_STORY_SYSTEM_PROMPT,
        max_tokens=REACTION_STORY_MAX_TOKENS,
        surface=REACTION_STORY_SURFACE_KEY,
        subcommand=REACTION_STORY_SUBCOMMAND,
    )

    if loop_result.fell_back or not loop_result.text:
        stub_text = fallback_fn(wire_id)
        return ReactionStoryResult(
            text=stub_text,
            source="offline" if stub_text else "none",
            loop_result=loop_result,
            fallback_reason=loop_result.fallback_reason or "loop_returned_no_text",
        )

    return ReactionStoryResult(
        text=loop_result.text,
        source="llm",
        loop_result=loop_result,
        fallback_reason=None,
    )
