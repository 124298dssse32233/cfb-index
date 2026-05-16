"""Sprint v5-1.5c batch-path activation — CLI handler routing.

The ``_batch`` variants of synthesizer functions exist (Sprint v5-1.5,
commit 1cd48ce9) but production CLI handlers did NOT call them. This
sprint flips four high-impact handlers so that the 50%-off + 1h-cache
batch path actually fires in production.

These tests verify the routing decision shape — for each flipped
handler, ``--batch off`` calls the sync variant, ``--batch on`` calls
the batch variant, and ``--batch auto`` chooses by N. The synthesizer
internals stay covered by their own per-module tests
(``test_chronicle_batch.py``, ``test_llm_runtime_batch.py``, etc.); here
we only assert the CLI flips correctly.
"""
from __future__ import annotations

import sys
import types
from contextlib import contextmanager
from unittest import mock

import pytest

from cfb_rankings.cli import build_parser, main


# ---------------------------------------------------------------------------
# Parser-level flag presence + defaults
# ---------------------------------------------------------------------------

def test_parser_mailbag_generate_answers_has_batch_flag():
    """mailbag-generate-answers must accept --batch {auto,on,off} (default auto)."""
    parser = build_parser()
    args = parser.parse_args(["mailbag-generate-answers"])
    assert args.batch == "auto"
    args_on = parser.parse_args(["mailbag-generate-answers", "--batch", "on"])
    assert args_on.batch == "on"
    args_off = parser.parse_args(["mailbag-generate-answers", "--batch", "off"])
    assert args_off.batch == "off"


def test_parser_reactions_check_triggers_has_batch_flag():
    """reactions-check-triggers must accept --batch (default auto)."""
    parser = build_parser()
    args = parser.parse_args(["reactions-check-triggers"])
    assert args.batch == "auto"
    args_on = parser.parse_args(["reactions-check-triggers", "--batch", "on", "--auto"])
    assert args_on.batch == "on"
    assert args_on.auto is True


def test_parser_prepare_pulse_has_batch_flag():
    """prepare-pulse must accept --batch (default auto)."""
    parser = build_parser()
    args = parser.parse_args(["prepare-pulse"])
    assert args.batch == "auto"
    args_off = parser.parse_args(["prepare-pulse", "--batch", "off"])
    assert args_off.batch == "off"


def test_parser_wire_generate_editorial_has_batch_flag():
    """wire-generate-editorial must accept --batch (default off — the LLM
    path is gated on Sprint v5-2 quality-loop, so default keeps the
    deterministic templated factual fallback)."""
    parser = build_parser()
    args = parser.parse_args(["wire-generate-editorial"])
    assert args.batch == "off"
    args_auto = parser.parse_args(["wire-generate-editorial", "--batch", "auto"])
    assert args_auto.batch == "auto"


def test_parser_generate_chronicle_has_batch_flag():
    """generate-chronicle batch wiring was added in v5-1.5 — verify the flag
    survives subsequent edits."""
    parser = build_parser()
    args = parser.parse_args(["generate-chronicle"])
    assert args.batch == "auto"


# ---------------------------------------------------------------------------
# Handler-level dispatch — mocked synthesizer functions
# ---------------------------------------------------------------------------
#
# We monkey-patch the synthesizer imports the handler uses so the real
# database/LLM code never runs. Each test drives ``main()`` with the
# corresponding subcommand and asserts which variant (sync vs batch) was
# called.

@contextmanager
def _patched_argv(*argv: str):
    """Temporarily swap sys.argv so argparse picks up our args."""
    old = sys.argv
    sys.argv = ["cfb-rankings", *argv]
    try:
        yield
    finally:
        sys.argv = old


def _stub_db(monkeypatch):
    """Patch out the apply_runtime_migrations + Database init that main()
    triggers before any subcommand dispatch."""
    fake_db = mock.MagicMock(name="Database")
    fake_db.connection.return_value.__enter__ = mock.Mock(return_value=mock.MagicMock())
    fake_db.connection.return_value.__exit__ = mock.Mock(return_value=False)
    fake_db.query_all.return_value = []
    fake_db.execute.return_value = None
    monkeypatch.setattr("cfb_rankings.cli.AppConfig.from_env",
                        classmethod(lambda cls: types.SimpleNamespace(
                            database_url=":memory:",
                            anthropic_api_key=None,
                        )))
    monkeypatch.setattr("cfb_rankings.db.Database", lambda url: fake_db)
    monkeypatch.setattr("cfb_rankings.cli.apply_runtime_migrations", lambda db: None)
    # Database is constructed in main(): we shadow what it returns.
    monkeypatch.setattr("cfb_rankings.cli.Path", __import__("pathlib").Path)
    return fake_db


# ---- mailbag -------------------------------------------------------------

@pytest.fixture
def mailbag_mocks(monkeypatch):
    sync = mock.MagicMock(return_value={
        "edition_slug": "2026-w17", "answers_generated": 0,
        "voice_passed": 0, "voice_failed": 0,
        "total_input_tokens": 0, "total_output_tokens": 0,
        "model_usage": {},
    })
    batched = mock.MagicMock(return_value={
        "edition_slug": "2026-w17", "answers_generated": 3,
        "voice_passed": 3, "voice_failed": 0,
        "total_input_tokens": 100, "total_output_tokens": 200,
        "model_usage": {"claude-sonnet-4-6": 300},
        "mode": "batch",
    })
    monkeypatch.setattr(
        "cfb_rankings.mailbag.synthesizer.generate_answers_for_edition", sync,
    )
    monkeypatch.setattr(
        "cfb_rankings.mailbag.synthesizer.generate_answers_for_edition_batch", batched,
    )
    monkeypatch.setattr(
        "cfb_rankings.mailbag.data.current_edition_slug", lambda: "2026-w17",
    )
    return sync, batched


def _patch_list_curated(monkeypatch, n: int):
    """Stub list_curated_for_edition to return N rows so the 'auto'
    branch can count them for routing."""
    monkeypatch.setattr(
        "cfb_rankings.mailbag.data.list_curated_for_edition",
        lambda conn, slug: [{"id": i} for i in range(n)],
    )


def test_mailbag_batch_off_calls_sync(monkeypatch, mailbag_mocks):
    sync, batched = mailbag_mocks
    _stub_db(monkeypatch)
    _patch_list_curated(monkeypatch, 5)  # plenty — should be irrelevant
    with _patched_argv("mailbag-generate-answers", "--batch", "off"):
        main()
    assert sync.called
    assert not batched.called


def test_mailbag_batch_on_calls_batch(monkeypatch, mailbag_mocks):
    sync, batched = mailbag_mocks
    _stub_db(monkeypatch)
    _patch_list_curated(monkeypatch, 1)  # even N=1 forced to batch
    with _patched_argv("mailbag-generate-answers", "--batch", "on"):
        main()
    assert batched.called
    assert not sync.called


def test_mailbag_batch_auto_picks_batch_when_multiple_questions(monkeypatch, mailbag_mocks):
    sync, batched = mailbag_mocks
    _stub_db(monkeypatch)
    _patch_list_curated(monkeypatch, 3)
    with _patched_argv("mailbag-generate-answers"):
        main()
    assert batched.called
    assert not sync.called


def test_mailbag_batch_auto_picks_sync_when_single_question(monkeypatch, mailbag_mocks):
    sync, batched = mailbag_mocks
    _stub_db(monkeypatch)
    _patch_list_curated(monkeypatch, 1)
    with _patched_argv("mailbag-generate-answers"):
        main()
    assert sync.called
    assert not batched.called


# ---- reactions -----------------------------------------------------------

@pytest.fixture
def reactions_mocks(monkeypatch):
    sync = mock.MagicMock(return_value=mock.MagicMock(slug="story-a"))
    batched = mock.MagicMock(return_value=[
        mock.MagicMock(slug="story-a"),
        mock.MagicMock(slug="story-b"),
    ])
    monkeypatch.setattr(
        "cfb_rankings.reactions.synthesizer.generate_reaction", sync,
    )
    monkeypatch.setattr(
        "cfb_rankings.reactions.synthesizer.synthesize_reactions_batch", batched,
    )
    monkeypatch.setattr(
        "cfb_rankings.reactions.renderer.render_story", lambda slug: None,
    )
    monkeypatch.setattr(
        "cfb_rankings.reactions.renderer.render_archive", lambda: None,
    )
    return sync, batched


def _patch_reactions_triggers(monkeypatch, n: int):
    """Stub check_triggers to return N events, plus fetch_wire_entry and
    cohort divergence so the handler can build the input tuples."""
    events = [
        types.SimpleNamespace(
            wire_id=i,
            primary_entity_slug="alabama",
            primary_entity_type="team",
            suggested_slug=f"story-{i}",
            velocity=85.0,
            trigger_reason="velocity-spike",
        )
        for i in range(n)
    ]
    monkeypatch.setattr(
        "cfb_rankings.reactions.triggers.check_triggers",
        lambda hours=24, force_wire_id=None: events,
    )
    monkeypatch.setattr(
        "cfb_rankings.reactions.data.fetch_wire_entry",
        lambda wid: {"id": wid, "program_slug": "alabama", "actor_kind": "program"},
    )
    monkeypatch.setattr(
        "cfb_rankings.reactions.cohort_divergence.extract_cohort_divergence",
        lambda row: types.SimpleNamespace(
            stat_folks=types.SimpleNamespace(
                cohort="stat_folks", stance="bullish",
                quotes=[], sentiment_score=0.5, volume_share=0.33,
            ),
            casual_fans=types.SimpleNamespace(
                cohort="casual_fans", stance="bullish",
                quotes=[], sentiment_score=0.5, volume_share=0.33,
            ),
            die_hards=types.SimpleNamespace(
                cohort="die_hards", stance="bullish",
                quotes=[], sentiment_score=0.5, volume_share=0.33,
            ),
        ),
    )


def test_reactions_batch_off_calls_sync(monkeypatch, reactions_mocks):
    sync, batched = reactions_mocks
    _stub_db(monkeypatch)
    _patch_reactions_triggers(monkeypatch, 3)
    with _patched_argv("reactions-check-triggers", "--auto", "--batch", "off"):
        main()
    assert sync.call_count == 3
    assert not batched.called


def test_reactions_batch_on_calls_batch(monkeypatch, reactions_mocks):
    sync, batched = reactions_mocks
    _stub_db(monkeypatch)
    _patch_reactions_triggers(monkeypatch, 2)
    with _patched_argv("reactions-check-triggers", "--auto", "--batch", "on"):
        main()
    assert batched.call_count == 1
    assert not sync.called


def test_reactions_batch_auto_picks_batch_when_many_events(monkeypatch, reactions_mocks):
    sync, batched = reactions_mocks
    _stub_db(monkeypatch)
    _patch_reactions_triggers(monkeypatch, 4)
    with _patched_argv("reactions-check-triggers", "--auto"):
        main()
    assert batched.called
    assert not sync.called


def test_reactions_batch_auto_picks_sync_when_one_event(monkeypatch, reactions_mocks):
    sync, batched = reactions_mocks
    _stub_db(monkeypatch)
    _patch_reactions_triggers(monkeypatch, 1)
    with _patched_argv("reactions-check-triggers", "--auto"):
        main()
    assert sync.called
    assert not batched.called


# ---- prepare-pulse -------------------------------------------------------

@pytest.fixture
def pulse_mocks(monkeypatch):
    sync_themes = mock.MagicMock(return_value=[{"label": "x", "summary": "y", "rank": 1}])
    batch_themes = mock.MagicMock(
        return_value={
            ("alabama", "team"): [{"label": "x", "summary": "y", "rank": 1}],
            ("ohio-state", "team"): [{"label": "x", "summary": "y", "rank": 1}],
        }
    )
    sync_lede = mock.MagicMock(return_value={
        "text": "L", "voice_validator_passed": True, "mode": "live", "model_used": "claude-sonnet-4-6",
    })
    batch_lede = mock.MagicMock(return_value={
        ("alabama", "team"): {
            "text": "L", "voice_validator_passed": True, "mode": "batch", "model_used": "claude-sonnet-4-6",
        },
        ("ohio-state", "team"): {
            "text": "L", "voice_validator_passed": True, "mode": "batch", "model_used": "claude-sonnet-4-6",
        },
    })
    monkeypatch.setattr(
        "cfb_rankings.team_pages.pulse_themes.extract_entity_themes", sync_themes,
    )
    monkeypatch.setattr(
        "cfb_rankings.team_pages.pulse_themes.extract_entities_themes_batch", batch_themes,
    )
    monkeypatch.setattr(
        "cfb_rankings.team_pages.pulse_lede.generate_entity_lede", sync_lede,
    )
    monkeypatch.setattr(
        "cfb_rankings.team_pages.pulse_lede.generate_entity_ledes_batch", batch_lede,
    )
    return sync_themes, batch_themes, sync_lede, batch_lede


def test_prepare_pulse_batch_off_calls_sync(monkeypatch, pulse_mocks):
    sync_themes, batch_themes, sync_lede, batch_lede = pulse_mocks
    _stub_db(monkeypatch)
    with _patched_argv("prepare-pulse", "--batch", "off"):
        main()
    # The default run_list has >=2 entities — assert sync path used.
    assert sync_themes.called
    assert sync_lede.called
    assert not batch_themes.called
    assert not batch_lede.called


def test_prepare_pulse_batch_on_calls_batch(monkeypatch, pulse_mocks):
    sync_themes, batch_themes, sync_lede, batch_lede = pulse_mocks
    _stub_db(monkeypatch)
    # Even with --entity (single), --batch on forces batch path.
    with _patched_argv("prepare-pulse", "--entity", "alabama", "--type", "team", "--batch", "on"):
        main()
    assert batch_themes.called
    assert batch_lede.called
    assert not sync_themes.called
    assert not sync_lede.called


def test_prepare_pulse_batch_auto_with_default_run_list_uses_batch(monkeypatch, pulse_mocks):
    sync_themes, batch_themes, sync_lede, batch_lede = pulse_mocks
    _stub_db(monkeypatch)
    with _patched_argv("prepare-pulse"):
        main()
    # Default run_list is 15+ entities → batch.
    assert batch_themes.called
    assert batch_lede.called
    assert not sync_themes.called


def test_prepare_pulse_batch_auto_with_single_entity_uses_sync(monkeypatch, pulse_mocks):
    sync_themes, batch_themes, sync_lede, batch_lede = pulse_mocks
    _stub_db(monkeypatch)
    with _patched_argv("prepare-pulse", "--entity", "alabama", "--type", "team"):
        main()
    # Single entity → run_list length 1 → sync.
    assert sync_themes.called
    assert sync_lede.called
    assert not batch_themes.called


# ---- wire-generate-editorial -------------------------------------------

@pytest.fixture
def wire_mocks(monkeypatch):
    sync = mock.MagicMock(return_value={
        "processed": 0, "authored_used": 0, "factual_fallback": 0,
        "validator_dropped": 0, "validator_passed": 0, "historical_comps": 0,
    })
    batched = mock.MagicMock(return_value={
        "uncovered": 2, "batched": 2, "updated": 0, "mode": "noop",
    })
    monkeypatch.setattr(
        "cfb_rankings.wire.editorial.generate_editorial_for_pending", sync,
    )
    monkeypatch.setattr(
        "cfb_rankings.wire.editorial.generate_uncovered_rows_batch", batched,
    )
    return sync, batched


def test_wire_batch_off_calls_sync(monkeypatch, wire_mocks):
    sync, batched = wire_mocks
    _stub_db(monkeypatch)
    with _patched_argv("wire-generate-editorial", "--batch", "off"):
        main()
    assert sync.called
    assert not batched.called


def test_wire_batch_on_calls_batch_then_sync_passthrough(monkeypatch, wire_mocks):
    """--batch on runs the LLM batch path for uncovered rows AND the
    deterministic pass — non-uncovered rows still get factual_restatement
    + impact_label fields written. Verifies both fire."""
    sync, batched = wire_mocks
    _stub_db(monkeypatch)
    with _patched_argv("wire-generate-editorial", "--batch", "on"):
        main()
    assert batched.called
    # Deterministic pass also runs to fill non-uncovered rows
    assert sync.called


def test_wire_batch_default_is_off(monkeypatch, wire_mocks):
    """Default --batch=off: the LLM path is gated on Sprint v5-2 quality-loop;
    keep deterministic fallback as default for now."""
    sync, batched = wire_mocks
    _stub_db(monkeypatch)
    with _patched_argv("wire-generate-editorial"):
        main()
    assert sync.called
    assert not batched.called
