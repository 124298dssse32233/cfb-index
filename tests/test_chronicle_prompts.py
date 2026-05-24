"""Tests for cfb_rankings.chronicle.prompts."""
from __future__ import annotations

import pytest

from cfb_rankings.chronicle.prompts import (
    SYSTEM_VOICE_CFB,
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
    render_evidence_block,
    render_narrative_state,
)
from cfb_rankings.chronicle.retriever import EvidenceRow
from cfb_rankings.chronicle.runtime import GenerationConfig


def _ev(source: str = "cfbd", text: str = "Cam Ward threw 4,313 yards.") -> EvidenceRow:
    return EvidenceRow(
        source=source,
        source_id="row-1",
        trust="high",
        kind="stat",
        payload={"yards": 4313},
        text=text,
        season_year=2024,
        entity_slug="cam-ward",
    )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


def test_system_voice_covers_critical_rules():
    s = SYSTEM_VOICE_CFB.lower()
    # Editorial standards present
    assert "90 words" in s or "ninety words" in s
    assert "evidence" in s
    assert "instruction" in s  # injection-defense mention
    # Banned-content reminders
    assert "emoji" in s
    assert "hashtag" in s
    # Citation requirement
    assert "cite" in s or "citation" in s


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


def test_card_brief_defaults():
    b = CardBrief(slot_index=0)
    assert b.slot_index == 0
    assert b.action == "card"
    assert b.target_word_count == 75
    assert b.forbidden_ledes == []


def test_card_brief_validates_enums():
    with pytest.raises(Exception):
        CardBrief(slot_index=0, opening_type="not-a-valid-opening")


def test_card_draft_round_trip():
    d = CardDraft(slot_index=2, card_type="flashpoint", body_text="x", word_count=1)
    j = d.model_dump_json()
    d2 = CardDraft.model_validate_json(j)
    assert d2.body_text == "x"


def test_planner_output_holds_briefs():
    p = PlannerOutput(briefs=[CardBrief(slot_index=0), CardBrief(slot_index=1)], page_thesis="t")
    assert len(p.briefs) == 2


def test_critic_score_verdicts():
    f = FactCriticScore(verdict="pass", factscore_atomic=0.9)
    assert f.verdict == "pass"
    v = VoiceCriticScore(verdict="flag")
    assert v.verdict == "flag"
    c = CollisionCriticScore(verdict="fail")
    assert c.verdict == "fail"


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def test_render_evidence_block_uses_wrap_evidence():
    block = render_evidence_block([_ev()])
    # Format from source_trust.wrap_evidence
    assert "<evidence" in block
    assert "source=\"cfbd\"" in block
    assert "trust=\"high\"" in block


def test_render_evidence_block_empty():
    block = render_evidence_block([])
    assert "empty" in block.lower()


def test_render_narrative_state_compresses():
    out = render_narrative_state(
        frame_stack=[{"frame_id": "f1", "label": "Heisman push", "depth": 1}],
        open_arcs=[{"arc_id": "a1", "summary": "Late-season surge after Iowa loss"}],
        calendar_pressure={"days_to_signing_day": 5},
        phrase_tokens=[{"token": "TIME_COLLAPSE_2008", "uses_remaining": 1}],
    )
    assert "frame_stack" in out
    assert "open_arcs" in out
    assert "calendar" in out
    assert "phrase_tokens" in out


def test_render_narrative_state_skips_empty_sections():
    out = render_narrative_state(
        frame_stack=[], open_arcs=[], calendar_pressure={}, phrase_tokens=[],
    )
    # Just the wrapper tags
    assert "frame_stack" not in out
    assert "calendar" not in out


# ---------------------------------------------------------------------------
# Prompt builders — every one returns (system, user, cfg)
# ---------------------------------------------------------------------------


def test_build_planner_prompt_shape():
    s, u, cfg = build_planner_prompt(
        entity_slug="cam-ward",
        entity_kind="player",
        season_year=2024,
        week_number=9,
        n_slots=6,
        evidence=[_ev()],
        frame_stack=[],
        open_arcs=[],
        calendar_pressure={},
        phrase_tokens=[],
        available_card_types=["flashpoint", "player_arc"],
    )
    assert isinstance(s, str) and "Planner" in s
    assert "cam-ward" in u
    assert "<evidence" in u
    assert isinstance(cfg, GenerationConfig)
    assert cfg.json_schema is not None  # schema attached


def test_build_writer_prompt_shape():
    brief = CardBrief(slot_index=0, card_type="flashpoint", opening_type="number",
                      template_pattern="number_hook", target_word_count=70)
    s, u, cfg = build_writer_prompt(
        brief=brief, evidence=[_ev()], frame_stack=[],
        team_voice=None, page_thesis="Cam Ward is the favorite.",
    )
    assert "Writer" in s
    assert "Cam Ward is the favorite" in u
    assert cfg.json_schema is not None
    assert cfg.max_tokens < cfg.wall_clock_budget_s * 100  # sanity


def test_build_writer_prompt_devil_card():
    brief = CardBrief(slot_index=3, is_devil_card=True)
    _, u, _ = build_writer_prompt(
        brief=brief, evidence=[_ev()], frame_stack=[], team_voice=None, page_thesis="t",
        is_devil_card=True,
    )
    assert "devil" in u.lower()


def test_build_fact_critic_prompt_shape():
    draft = CardDraft(slot_index=0, body_text="Cam Ward threw for 4,313 yards.", word_count=7)
    s, u, cfg = build_fact_critic_prompt(draft=draft, evidence=[_ev()])
    assert "FactCritic" in s
    assert "4,313" in u
    assert cfg.json_schema is not None


def test_build_voice_critic_prompt_shape():
    draft = CardDraft(slot_index=0, body_text="x", word_count=1)
    s, u, cfg = build_voice_critic_prompt(
        draft=draft, banlist=["dominant", "elite"],
        banlist_severity={"dominant": 0.9}, team_voice=None,
    )
    assert "VoiceCritic" in s
    assert "dominant" in u
    assert cfg.json_schema is not None


def test_build_collision_critic_prompt_shape():
    drafts = [
        CardDraft(slot_index=0, body_text="a", word_count=1),
        CardDraft(slot_index=1, body_text="b", word_count=1),
    ]
    s, u, cfg = build_collision_critic_prompt(sibling_drafts=drafts)
    assert "CollisionCritic" in s
    assert cfg.json_schema is not None


def test_build_refiner_prompt_shape():
    draft = CardDraft(slot_index=0, body_text="x", word_count=1)
    fc = FactCriticScore(verdict="fix", factscore_atomic=0.7,
                          unsupported_claims=["x"])
    brief = CardBrief(slot_index=0)
    s, u, cfg = build_refiner_prompt(
        draft=draft, fact_critic=fc, voice_critic=None,
        collision_critic=None, brief=brief, evidence=[_ev()],
    )
    assert "Refiner" in s
    assert "fact_critic" in u
    assert cfg.json_schema is not None
