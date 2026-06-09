"""Tests for the compare-page payload externalization (WS-11 page weight).

/compare/index.html embeds an all-teams JSON payload (~668 teams) that the
client uses to hydrate the A-vs-B comparison tool. Inlined, that blob was
~360KB+ gzipped on every page load. The fix routes it to a sidecar
compare/teams.json via a `payload_writer` callback; the JS fetches it on load.
These tests pin the inline-vs-external branching. The data-assembly helpers
(_compare_team_snapshot etc.) are stubbed — they're orthogonal to the page
weight change and are exercised end-to-end in the build path.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from cfb_rankings import reporting


def _ranking(slug: str) -> SimpleNamespace:
    return SimpleNamespace(slug=slug, team_name=slug.title(), level_code="FBS", rank=1)


_SNAPSHOT = {
    "team_name": "Alpha", "rank": 1, "level_code": "FBS", "conference": "SEC",
    "record": "10-0", "average_margin": 12.0, "team_url": "../teams/alpha.html",
    "best_result": "win", "worst_result": "loss", "efficiency_note": "note",
    "metrics": {"power": 5.0, "resume": 80.0},
}


@pytest.fixture
def patched(monkeypatch):
    pages = [{"ranking": _ranking("alpha")}, {"ranking": _ranking("bravo")}]
    monkeypatch.setattr(reporting, "_default_compare_pair", lambda tp: (tp[0], tp[1]))
    monkeypatch.setattr(reporting, "_compare_team_snapshot", lambda page, prefix="": dict(_SNAPSHOT))
    monkeypatch.setattr(reporting, "_compare_payload", lambda tp, prefix="": '{"teams":[],"defaultTeamA":"alpha","defaultTeamB":"bravo"}')
    monkeypatch.setattr(reporting, "_render_compare_scenario_cards", lambda tp: "")
    return pages


_SUMMARY = {"season_year": 2025}
_PULSE: dict = {}


def test_inline_mode_keeps_payload_script(patched) -> None:
    html = reporting.render_compare_page_html(_SUMMARY, patched, _PULSE)
    assert '<script id="comparePayload" type="application/json">' in html


def test_external_mode_writes_sidecar_and_fetches(patched) -> None:
    captured: dict[str, str] = {}
    html = reporting.render_compare_page_html(
        _SUMMARY, patched, _PULSE,
        payload_writer=lambda payload: captured.__setitem__("json", payload),
    )
    assert '<script id="comparePayload" type="application/json">' not in html
    assert "fetch('teams.json')" in html
    assert "json" in captured
    assert json.loads(captured["json"])["defaultTeamA"] == "alpha"


def test_external_smaller_than_inline(patched) -> None:
    inline = reporting.render_compare_page_html(_SUMMARY, patched, _PULSE)
    external = reporting.render_compare_page_html(
        _SUMMARY, patched, _PULSE, payload_writer=lambda payload: None
    )
    assert len(external) < len(inline)
