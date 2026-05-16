"""Narrative generator: state-of-team paragraphs, per-program voice.

Two modes:

*   **LLM mode** (``mode='claude'`` or ``mode='claude-code'``) — builds a
    structured prompt from profile + state + facts, and calls either the
    Anthropic SDK (if ``anthropic`` is importable) or the ``claude`` CLI
    binary as a subprocess. Tokens logged to the ``team_season_narratives``
    row for cost accountability. If neither is available, raises
    ``RuntimeError`` with a clear message — we never silently fall back to
    templates under an LLM-mode request.

*   **Template mode** (``mode='template'``) — builds an on-voice paragraph
    deterministically from profile frontmatter fields + state context. This
    is the fallback used when the CLI is invoked without ``--llm`` or when
    API access is unavailable. Quality depends on profile richness (hence
    the insistence on ~45-50 fields per profile).

Design judgment: the template mode is NOT a placeholder. It produces
publishable-quality copy when the profile is well-authored, because the
profile carries the voice. LLM mode adds fluency + subtlety; template mode
guarantees correctness + shipping.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .data import TeamSnapshot
from .profile_loader import Profile
from .state_resolver import PageState


# --------------------------------------------------------------------------
# Result type
# --------------------------------------------------------------------------

@dataclass
class NarrativeResult:
    body_md: str
    title: str | None
    attribution: str | None
    model_id: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    variant: str

    def persist(self, db, team_id: int, season_year: int, state: PageState) -> None:
        db.execute(
            """
            insert into team_season_narratives (
                team_id, season_year, variant, title, body_md, attribution,
                week_context, state_signature, model_id,
                prompt_tokens, completion_tokens, generation_cost_usd,
                is_published, generated_at_utc
            ) values (
                :team_id, :season, :variant, :title, :body, :attr,
                :week_context, :sig, :model,
                :p_tok, :c_tok, :cost, 1, current_timestamp
            )
            on conflict(team_id, season_year, variant, week_context) do update set
                title = excluded.title,
                body_md = excluded.body_md,
                attribution = excluded.attribution,
                state_signature = excluded.state_signature,
                model_id = excluded.model_id,
                prompt_tokens = excluded.prompt_tokens,
                completion_tokens = excluded.completion_tokens,
                generation_cost_usd = excluded.generation_cost_usd,
                is_published = 1,
                generated_at_utc = current_timestamp
            """,
            {
                "team_id": team_id,
                "season": season_year,
                "variant": self.variant,
                "title": self.title,
                "body": self.body_md,
                "attr": self.attribution,
                "week_context": 0,
                "sig": json.dumps(state.as_dict(), ensure_ascii=False),
                "model": self.model_id,
                "p_tok": self.prompt_tokens,
                "c_tok": self.completion_tokens,
                "cost": self.cost_usd,
            },
        )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def generate_state_of_team(
    profile: Profile,
    snapshot: TeamSnapshot,
    state: PageState,
    *,
    mode: str = "template",
    claude_model: str = "claude-opus-4-7",
    _meter: Any = None,
) -> NarrativeResult:
    """Generate the state-of-team paragraph.

    mode:
      - 'template' → deterministic composition from profile frontmatter.
      - 'claude' → Anthropic SDK call.
      - 'claude-code' → subprocess out to `claude` binary (Max sub).

    ``_meter`` (Pattern A, optional): cost ceiling for the claude SDK path.
    """
    prompt = build_state_of_team_prompt(profile, snapshot, state)

    if mode == "template":
        body = _template_state_of_team(profile, snapshot, state)
        return NarrativeResult(
            body_md=body,
            title=None,
            attribution=None,
            model_id="template-v1",
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0.0,
            variant="state_of_team",
        )

    if mode == "claude":
        return _call_anthropic_sdk(prompt, claude_model, variant="state_of_team", _meter=_meter)

    if mode == "claude-code":
        return _call_claude_code_cli(prompt, claude_model, variant="state_of_team")

    raise ValueError(f"unknown narrative mode: {mode}")


# --------------------------------------------------------------------------
# Sprint 6 — post-game state-of-team paragraph (outcome-variant voice).
#
# Editorial load-bearing paragraph that anchors the team page for the 24h
# after a game. Always Opus when an LLM is available because this is the
# single most-read paragraph on the page during the gameday window.
# --------------------------------------------------------------------------

def generate_state_of_team_post_game(
    profile: Profile,
    snapshot: TeamSnapshot,
    state: PageState,
    *,
    final_meta: dict[str, Any],
    mode: str = "template",
    claude_model: str = "claude-opus-4-7",
    _meter: Any = None,
) -> NarrativeResult:
    """Generate the post-game state-of-team paragraph for the GameRecapHero.

    ``final_meta`` carries the just-finalized game's score and venue context
    (home_team_slug, away_team_slug, home_score, away_score, optional
    quarter-by-quarter breakdown). Voice register is selected by
    ``state.outcome_category``.

    mode='template' produces a deterministic on-voice paragraph that passes
    the Beat-Writer Test for offline rehearsal. 'claude' / 'claude-code'
    route through the LLM with the structured prompt.
    """
    prompt = build_state_of_team_post_game_prompt(profile, snapshot, state, final_meta)

    if mode == "template":
        body = _template_state_of_team_post_game(profile, snapshot, state, final_meta)
        return NarrativeResult(
            body_md=body,
            title=None,
            attribution=None,
            model_id="template-v2-post-game",
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0.0,
            variant="state_of_team_post_game",
        )

    if mode == "claude":
        return _call_anthropic_sdk(
            prompt, claude_model, variant="state_of_team_post_game", _meter=_meter,
        )

    if mode == "claude-code":
        return _call_claude_code_cli(prompt, claude_model, variant="state_of_team_post_game")

    raise ValueError(f"unknown narrative mode: {mode}")


_OUTCOME_REGISTER_BRIEF: dict[str, str] = {
    "win-clear": (
        "OUTCOME REGISTER: confident. The expected result, executed. Don't "
        "preen. Don't catalogue what went wrong on isolated drives. Speak as "
        "the program continuing its work."
    ),
    "win-upset": (
        "OUTCOME REGISTER: vindicated. The result the room wasn't sure was "
        "coming. Don't gloat. Don't pretend it was always coming. Speak as "
        "a program that just earned what it took."
    ),
    "loss-close": (
        "OUTCOME REGISTER: reckoning. Not catastrophizing. Not bargaining. "
        "The register of a program accepting what just happened without "
        "flinching or posturing."
    ),
    "loss-blowout": (
        "OUTCOME REGISTER: wound. The result that stings and stays. Speak "
        "as a program that knows what just happened. Do not soften it. Do "
        "not announce a rebuild. Honest, not performative."
    ),
    "loss-upset": (
        "OUTCOME REGISTER: crisis. The result the room wasn't supposed to "
        "have to write. The register of a program facing a question it "
        "must answer aloud. Not panic, not denial — the honest reckoning of "
        "a result the program should not have lost."
    ),
}


def build_state_of_team_post_game_prompt(
    profile: Profile,
    snapshot: TeamSnapshot,
    state: PageState,
    final_meta: dict[str, Any],
) -> str:
    """Assemble the LLM prompt for the post-game paragraph.

    Strict by design: voice register, identity phrase, mantra, banned
    phrases, and the outcome's editorial register are surfaced separately
    so the model has no room to invent a voice.
    """
    cat = state.outcome_category or "loss-close"
    register_brief = _OUTCOME_REGISTER_BRIEF.get(
        cat, _OUTCOME_REGISTER_BRIEF["loss-close"]
    )
    score_facts = _post_game_score_facts(profile, final_meta)

    stock = "\n".join(f"- {s}" for s in profile.stock_phrases)
    never = "\n".join(f"- {s}" for s in profile.never_use)

    banned = (
        "sample, pipeline, every season produces, this table, pattern is, "
        "compression of outcome, methodology, stat engine, our algorithm, "
        "the engine, cfb index, summary stat"
    )

    return f"""ROLE: Write the single paragraph that anchors {profile.program_name}'s
team page for the next 24 hours after their game.

# Program voice
- Voice register: {profile.voice_register}
- Identity phrase: "{profile.identity_phrase}"
- Mantra (may close paragraph if it lands): "{profile.mantra}"
- Tonal template: {profile.tonal_template}

# Stock phrases (use only if they fit naturally; do not force)
{stock}

# Never use
{never}

# Outcome
{score_facts}

# {register_brief}

# Structure
2-4 sentences. 60-100 words. First sentence must be a factual statement of
what happened (score, venue, quarter where applicable). Remaining sentences
carry the program's voice processing it. Must reference a specific element
of the game — the venue, the rivalry name (if a rival), a specific quarter,
a specific play phase. No generic gestures.

# Banned constructions (verbatim — do not produce these phrases anywhere)
{banned}

# Beat-Writer Test
Could a sharp columnist for {profile.program_name} have written this paragraph
the morning after this game? If no, rewrite. The paragraph should read as
the program's honest reader, not as a stat engine commenting on the program.

Return only the paragraph text — no headline, no attribution, no quotes
wrapping it.
"""


def _post_game_score_facts(profile: Profile, final_meta: dict[str, Any]) -> str:
    """Build a short facts block for the prompt."""
    team_slug = profile.slug.lower()
    home_slug = (final_meta.get("home_team_slug") or "").lower()
    away_slug = (final_meta.get("away_team_slug") or "").lower()
    home_score = final_meta.get("home_score")
    away_score = final_meta.get("away_score")
    if home_slug == team_slug:
        team_pts, opp_pts, opp_slug, was_home = home_score, away_score, away_slug, True
    elif away_slug == team_slug:
        team_pts, opp_pts, opp_slug, was_home = away_score, home_score, home_slug, False
    else:
        team_pts, opp_pts, opp_slug, was_home = 0, 0, "opponent", False

    venue = "at home" if was_home else f"on the road at {opp_slug.replace('-', ' ').title()}"
    rivalry_name = ""
    for r in profile.rivalries:
        if (r.get("opponent_slug") or "").lower() == opp_slug:
            rivalry_name = r.get("name") or r.get("trophy") or ""
            break

    lines = [
        f"- Final: {profile.program_name} {team_pts}, {opp_slug.replace('-', ' ').title()} {opp_pts} ({venue})",
    ]
    if rivalry_name:
        lines.append(f"- This game is the {rivalry_name}.")
    if final_meta.get("quarter_summary"):
        lines.append(f"- Quarter-by-quarter: {final_meta['quarter_summary']}")
    if final_meta.get("turning_point"):
        lines.append(f"- Turning point: {final_meta['turning_point']}")
    return "\n".join(lines)


def _template_state_of_team_post_game(
    profile: Profile,
    snapshot: TeamSnapshot,
    state: PageState,
    final_meta: dict[str, Any],
) -> str:
    """Deterministic on-voice fallback. Used when the LLM is unavailable
    or by simulate-game's offline rehearsal path.

    The scaffold pulls voice fields from the profile (identity_phrase,
    mantra, mascot_voice.post_loss / post_win) so the same template
    produces distinct voices per program.
    """
    cat = state.outcome_category or "loss-close"
    team_slug = profile.slug.lower()
    home_slug = (final_meta.get("home_team_slug") or "").lower()
    away_slug = (final_meta.get("away_team_slug") or "").lower()
    home_score = int(final_meta.get("home_score") or 0)
    away_score = int(final_meta.get("away_score") or 0)
    if home_slug == team_slug:
        team_pts, opp_pts, opp_slug, was_home = home_score, away_score, away_slug, True
    elif away_slug == team_slug:
        team_pts, opp_pts, opp_slug, was_home = away_score, home_score, home_slug, False
    else:
        team_pts, opp_pts, opp_slug, was_home = 0, 0, "opponent", False

    opp_pretty = opp_slug.replace("-", " ").title()

    rivalry_name = ""
    for r in profile.rivalries:
        if (r.get("opponent_slug") or "").lower() == opp_slug:
            rivalry_name = r.get("name") or r.get("trophy") or ""
            break

    venue = "at home" if was_home else f"at {opp_pretty}"
    # Avoid double article when rivalry name already starts with "The".
    rivalry_clause = ""
    if rivalry_name:
        rname = rivalry_name.strip()
        if rname.lower().startswith("the "):
            rivalry_clause = f" — {rname}"
        else:
            rivalry_clause = f" — the {rname}"

    factual = (
        f"{team_pts}-{opp_pts} {('over' if team_pts > opp_pts else 'to')} "
        f"{opp_pretty} {venue}{rivalry_clause}."
    )

    mascot = profile.mascot_voice
    if cat in ("loss-close", "loss-blowout", "loss-upset"):
        register_line = mascot.get("post_loss") or (
            f"The {profile.program_name} room is honest about it. The standard "
            f"this program holds itself to is the same one that built it."
        )
    else:
        register_line = mascot.get("post_win") or (
            f"The result counted for what it counted for. The work continues."
        )

    cat_modifier = {
        "win-clear":    "The game played out close to expectation, and the program took it.",
        "win-upset":    "The room wasn't sure this one was coming. It came anyway.",
        "loss-close":   "It was the kind of finish where every drive in the second half mattered.",
        "loss-blowout": "It was the kind of result that asks the program to look at itself.",
        "loss-upset":   "It was a result this program should not have lost. The room knows it.",
    }.get(cat, "")

    mantra_close = f" {profile.mantra}" if profile.mantra else ""

    body = f"{factual} {cat_modifier} {register_line}{mantra_close}".strip()
    # Collapse whitespace.
    return " ".join(body.split())


# --------------------------------------------------------------------------
# Prompt builder
# --------------------------------------------------------------------------

def build_state_of_team_prompt(
    profile: Profile,
    snapshot: TeamSnapshot,
    state: PageState,
) -> str:
    """Assemble the LLM prompt from profile + state + facts.

    The prompt is intentionally strict: voice register, identity phrase,
    guardrails, and context lines are all surfaced separately so the model
    has no room to invent a voice.
    """
    header_section = profile.sections.get("identity_and_heritage", {}).get("_body", "")
    voice_section = profile.sections.get("voice_and_ethos", {}).get("_body", "")
    context = "\n".join(f"- {line}" for line in state.narrative_context_lines)
    stock = "\n".join(f"- {s}" for s in profile.stock_phrases)
    never = "\n".join(f"- {s}" for s in profile.never_use)
    surface = "\n".join(f"- {s}" for s in profile.always_surface)

    return f"""You are writing the state-of-team paragraph for {profile.program_name}'s CFB Index team page.

# Program identity
Program tier: {profile.program_tier}
Voice register: {profile.voice_register}
Tonal template: {profile.tonal_template}
Identity phrase (may open the paragraph): "{profile.identity_phrase}"
Mantra (may close the paragraph): "{profile.mantra}"

# Voice and ethos
{voice_section}

# Identity and heritage
{header_section}

# Today's state
Anchor: {state.anchor_variant}
Copy tone: {state.copy_tone}
Accent key: {state.accent_key}
Season phase: {state.season_phase}
Day label: {state.day_of_week_label}

# Facts (bullet, use only these)
{context}

# Stock phrases (optional, used when they fit naturally)
{stock}

# Always surface
{surface}

# Never use
{never}

# Task
Write a 90-130 word state-of-team paragraph in {profile.program_name}'s voice.
Serif-magazine tone, not sports-radio. Speak as the program's honest reader.
Do not introduce facts not in the bullets above. Do not use a single
construction from the 'never use' list. You may open with the identity
phrase (or a close variant). You may close with the mantra if it lands.
Return only the paragraph text — no headline, no attribution, no quotes
wrapping it."""


# --------------------------------------------------------------------------
# Template composition (fallback / default)
# --------------------------------------------------------------------------

def _template_state_of_team(
    profile: Profile,
    snapshot: TeamSnapshot,
    state: PageState,
) -> str:
    """Deterministic on-voice paragraph from profile + state.

    Uses the tonal template to select a scaffold, then fills with facts.
    The scaffolds are written in-voice for each tonal template; the profile
    supplies identity phrase, mantra, and specific-fact hooks.
    """
    record = f"{snapshot.wins}-{snapshot.losses}" + (
        f"-{snapshot.ties}" if snapshot.ties else ""
    )
    program = profile.program_name
    identity = profile.identity_phrase
    mantra = profile.mantra

    tonal = (profile.tonal_template or "generic").lower()
    season_close = ""
    if snapshot.season_complete:
        season_close = f"The {snapshot.season_year} book has closed at {record}."
    else:
        season_close = f"Through the games played, {program} sits at {record}."

    rank_clause = ""
    if snapshot.ap_rank:
        rank_clause = f" The AP has them at #{snapshot.ap_rank}"
        if snapshot.cfp_rank:
            rank_clause += f"; the committee at #{snapshot.cfp_rank}"
        rank_clause += "."
    elif snapshot.coaches_rank:
        rank_clause = f" The coaches have them #{snapshot.coaches_rank}."

    last = snapshot.last_game
    last_clause = ""
    if last and last.outcome in ("W", "L"):
        loc = "at home" if last.is_home else "on the road"
        if last.outcome == "W":
            if (last.margin or 0) >= 21:
                last_clause = (
                    f" Week {last.week} was the kind of result that quiets "
                    f"the room — {last.team_points}-{last.opp_points} "
                    f"over {last.opponent_name} {loc}."
                )
            else:
                last_clause = (
                    f" Week {last.week} was closer than the box suggests — "
                    f"{last.team_points}-{last.opp_points} over "
                    f"{last.opponent_name} {loc}."
                )
        else:
            if (last.margin or 0) <= -21:
                last_clause = (
                    f" Week {last.week} was the loss they will spend the "
                    f"offseason answering for — "
                    f"{last.team_points}-{last.opp_points} to "
                    f"{last.opponent_name} {loc}."
                )
            else:
                last_clause = (
                    f" Week {last.week} was a loss that didn't have to be — "
                    f"{last.team_points}-{last.opp_points} to "
                    f"{last.opponent_name} {loc}."
                )

    offseason_clause = ""
    if state.season_phase in ("spring-and-portal", "nsd-and-portal"):
        offseason_clause = (
            " Spring ball and the portal window are where the next version "
            "of this team is actually being built."
        )
    elif state.season_phase == "dead-period-heritage":
        offseason_clause = (
            " June is quiet. What lives here is what the program has built "
            "to live through the quiet."
        )
    elif state.season_phase == "bowl-and-carousel":
        offseason_clause = (
            " The coaching carousel will spin and the bowl trip will mean "
            "what it means."
        )

    # Tonal scaffolds ----------------------------------------------------
    if tonal in ("dynastic", "dynastic-with-question-mark"):
        # ND register: dynastic legacy with "can we still" question hovering.
        body = _dynastic_scaffold(
            identity, program, season_close, rank_clause, last_clause,
            offseason_clause, mantra, tonal, state,
        )
    elif tonal in ("dynastic-process", "process"):
        # Alabama "Process Era" register.
        body = _process_scaffold(
            identity, program, season_close, rank_clause, last_clause,
            offseason_clause, mantra, state,
        )
    elif tonal in ("defiant-academic", "defiant"):
        # Vanderbilt register.
        body = _defiant_scaffold(
            identity, program, snapshot, season_close, rank_clause,
            last_clause, offseason_clause, mantra, state,
        )
    elif tonal in ("scrappy-proud", "scrappy", "rising-minnow"):
        # UMass register.
        body = _scrappy_scaffold(
            identity, program, snapshot, season_close, rank_clause,
            last_clause, offseason_clause, mantra, state,
        )
    else:
        body = _generic_scaffold(
            identity, program, season_close, rank_clause, last_clause,
            offseason_clause, mantra,
        )

    return _collapse_spaces(body)


def _dynastic_scaffold(identity, program, season_close, rank_clause, last_clause,
                       offseason_clause, mantra, tonal, state):
    question = ""
    if tonal == "dynastic-with-question-mark":
        question = (
            " The question that trails this program like a shadow — "
            "can they still be the standard they once were — didn't get "
            "answered this year. It rarely does in one."
        )
    opener = identity if identity else f"Here is what {program} is right now."
    return (
        f"{opener} {season_close}{rank_clause}{last_clause}{question}"
        f"{offseason_clause} {mantra}" if mantra
        else f"{opener} {season_close}{rank_clause}{last_clause}{question}"
             f"{offseason_clause}"
    )


def _process_scaffold(identity, program, season_close, rank_clause, last_clause,
                      offseason_clause, mantra, state):
    opener = identity if identity else (
        f"What the rest of the sport calls 'good' {program} calls maintenance."
    )
    middle = (
        " The process does not flinch at rankings or at results in isolation; "
        "it measures the program against its own standard first and everyone "
        "else's a distant second."
    )
    close = f" {mantra}" if mantra else ""
    return f"{opener} {season_close}{rank_clause}{last_clause}{middle}{offseason_clause}{close}"


def _defiant_scaffold(identity, program, snapshot, season_close, rank_clause,
                      last_clause, offseason_clause, mantra, state):
    opener = identity if identity else (
        f"{program} does not apologize for where it plays from."
    )
    context = ""
    if snapshot.wins >= 6:
        context = (
            " A bowl-eligible season is not a ceiling to be gracious about; "
            "it is a bar this program has cleared by doing the thing the "
            "league said couldn't be done in this division."
        )
    elif snapshot.wins >= 3:
        context = (
            " Three wins is a number somebody else writes off. Inside the "
            "program it is a number that gets banked and built on — "
            "incremental and exact."
        )
    else:
        context = (
            " The competitive math is honest: the schedule is hard, the "
            "budget is smaller, and the standard remains that you earn what "
            "you take. None of that is a complaint."
        )
    close = f" {mantra}" if mantra else ""
    return (
        f"{opener} {season_close}{rank_clause}{last_clause}{context}"
        f"{offseason_clause}{close}"
    )


def _scrappy_scaffold(identity, program, snapshot, season_close, rank_clause,
                      last_clause, offseason_clause, mantra, state):
    opener = identity if identity else (
        f"{program} is playing for the version of itself that gets invited "
        f"to the conversation."
    )
    context = ""
    if snapshot.wins >= 6:
        context = (
            " Bowl eligibility is the kind of threshold this program has "
            "talked about in the locker room more than it has rendered on "
            "the scoreboard — this is what rendering it looks like."
        )
    elif snapshot.wins >= 3:
        context = (
            " Three wins in a season is real proof of life, and the program "
            "knows the difference between a good week and a good trend."
        )
    else:
        context = (
            " The ladder is long and the program is not pretending "
            "otherwise. Each rung is the game to win."
        )
    close = f" {mantra}" if mantra else ""
    return (
        f"{opener} {season_close}{rank_clause}{last_clause}{context}"
        f"{offseason_clause}{close}"
    )


def _generic_scaffold(identity, program, season_close, rank_clause, last_clause,
                      offseason_clause, mantra):
    opener = identity if identity else f"{program}, at this point in the calendar."
    close = f" {mantra}" if mantra else ""
    return f"{opener} {season_close}{rank_clause}{last_clause}{offseason_clause}{close}"


def _collapse_spaces(text: str) -> str:
    return " ".join(text.split()).strip()


# --------------------------------------------------------------------------
# LLM adapters
# --------------------------------------------------------------------------

_COST_PER_MTOK = {
    # Rough prices for logging; update if pricing changes. USD per million.
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-opus-4-7": {"input": 15.0, "output": 75.0},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
    "template-v1": {"input": 0.0, "output": 0.0},
}


def _estimate_cost(model: str, prompt_tok: int, completion_tok: int) -> float:
    rates = _COST_PER_MTOK.get(model, {"input": 3.0, "output": 15.0})
    return (prompt_tok * rates["input"] + completion_tok * rates["output"]) / 1_000_000


def _log_invocation(subcommand: str, model: str, p_tok: int, c_tok: int, dur: float, *, call_id: str | None = None) -> None:
    try:
        from .llm_usage_log import append_llm_usage
        extra: dict[str, Any] = {}
        if call_id:
            extra["call_id"] = call_id
        append_llm_usage(
            subcommand=subcommand, model=model,
            prompt_tokens=p_tok, completion_tokens=c_tok, duration_s=dur,
            extra=extra,
        )
    except Exception:
        pass  # never let logging break generation


def _call_anthropic_sdk(
    prompt: str, model: str, variant: str,
    *,
    _meter: Any = None,
) -> NarrativeResult:
    """Direct anthropic SDK call. ``_meter`` (Pattern A, optional) records cost.

    Note: this module ships its own ``_estimate_cost`` + ``_log_invocation``
    telemetry. The CostMeter integration is consolidated on top — Best Calls
    + DB usage log + meter all coexist, but the meter is the only one that
    can HARD-FAIL the workflow if the ceiling is breached.
    """
    from cfb_rankings.llm_runtime import CostMeter
    meter = _meter or CostMeter(
        ceiling_usd=1.0,
        label=f"narrative.{variant}",
    )
    try:
        import anthropic  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "anthropic SDK not installed. Install it or use mode='template' "
            "or mode='claude-code'."
        ) from e

    client = anthropic.Anthropic()
    # Priority 2 (2026-05-16) — mint one call_id per LLM call and share
    # it with both telemetry writers (CostMeter.record + the legacy
    # _log_invocation → append_llm_usage call). The unique-call_id index
    # backed by INSERT OR IGNORE makes the second write a silent no-op,
    # collapsing the historical 2× rows-per-call to 1.
    import uuid as _uuid
    call_id = _uuid.uuid4().hex
    msg = client.messages.create(
        model=model,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    # Record cost against the meter. CostCeilingExceeded propagates.
    if getattr(msg, "usage", None) is not None:
        meter.record(model, msg.usage, note=f"narrative.{variant}", call_id=call_id)
    body = "".join(
        getattr(block, "text", "") for block in msg.content
        if getattr(block, "type", "") == "text"
    ).strip()
    usage = getattr(msg, "usage", None)
    p_tok = int(getattr(usage, "input_tokens", 0) or 0)
    c_tok = int(getattr(usage, "output_tokens", 0) or 0)
    _log_invocation(f"generate-narratives:{variant}", model, p_tok, c_tok, 0.0, call_id=call_id)
    return NarrativeResult(
        body_md=body,
        title=None,
        attribution=None,
        model_id=model,
        prompt_tokens=p_tok,
        completion_tokens=c_tok,
        cost_usd=_estimate_cost(model, p_tok, c_tok),
        variant=variant,
    )


def _call_claude_code_cli(prompt: str, model: str, variant: str) -> NarrativeResult:
    claude_bin = shutil.which("claude")
    if not claude_bin:
        raise RuntimeError(
            "claude CLI not on PATH. Install Claude Code or use mode='template'."
        )
    # Use headless `claude -p` to get a single response. Strip CLAUDECODE
    # from the subprocess env so the CLI doesn't refuse to nest when this
    # generator runs from inside a Claude Code parent session.
    sub_env = {k: v for k, v in os.environ.items()
               if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    start = time.time()
    try:
        proc = subprocess.run(
            [claude_bin, "-p", prompt, "--model", model, "--permission-mode", "plan"],
            capture_output=True,
            text=True,
            timeout=90,
            env=sub_env,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("claude CLI timed out after 90s")
    if proc.returncode != 0:
        raise RuntimeError(
            f"claude CLI failed (code={proc.returncode}): {proc.stderr.strip()[:400]}"
        )
    body = proc.stdout.strip()
    # No token metering from CLI; approximate by characters (rough).
    p_tok = max(1, len(prompt) // 4)
    c_tok = max(1, len(body) // 4)
    dur = time.time() - start
    _log_invocation(f"generate-narratives:{variant}", f"{model}+claude-code", p_tok, c_tok, dur)
    return NarrativeResult(
        body_md=body,
        title=None,
        attribution=None,
        model_id=f"{model}+claude-code",
        prompt_tokens=p_tok,
        completion_tokens=c_tok,
        cost_usd=0.0,  # Max subscription — not charged per-token
        variant=variant,
    )
