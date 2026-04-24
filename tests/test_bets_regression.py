"""Regression test for Signature Bets modules.

Scans the last-built Carr + Mendoza player pages for the required
module markers. Catches any future commit that drops a module from
the page template (e.g. autopilot refactors that accidentally delete
a render call).

Skipped when output/site doesn't exist (fresh checkout). In CI, runs
after the site build.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


SITE_ROOT = Path("output/site")
CARR_PATH = SITE_ROOT / "players" / "cj-carr-4788.html"
MENDOZA_PATH = SITE_ROOT / "players" / "fernando-mendoza-2431.html"


@pytest.fixture(scope="module")
def carr_html() -> str:
    if not CARR_PATH.exists():
        pytest.skip(f"{CARR_PATH} missing — run build-site first.")
    return CARR_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def mendoza_html() -> str:
    if not MENDOZA_PATH.exists():
        pytest.skip(f"{MENDOZA_PATH} missing — run build-site first.")
    return MENDOZA_PATH.read_text(encoding="utf-8")


# Required modules on the Carr page. Map of test-name → substring to
# assert present. A pure-HTML substring test is fragile in detail but
# robust enough to detect "module disappeared."
REQUIRED_ON_CARR = {
    # Phase S1
    "fi_glossary_icon":    'class="fi-glossary"',
    "fi_confidence_chip":  'class="fi-confidence',
    "page_state_json":     'id="page-state"',
    # Phase S2
    "hot_take_card":       'class="hot-take"',
    "anti_take_card":      'class="anti-take"',
    "rival_radar":         'class="rival-radar',
    "mirror_match":        'class="mirror-match',
    "achievements":        'class="achievements',
    "prediction_markets":  'class="prediction-markets',
    "coaching_lineage":    'class="coaching-lineage',
    # Phase S3
    "cohort_divergence":   'class="cohort-divergence',
    "signature_play":      'class="signature-play',
    "narrative_arc":       'class="narrative-arc',
    "scenario_explorer":   'class="scenario-explorer',
    # Phase S4
    "change_log":          'class="change-log',
    "kb_toast":            'data-kb-toast',
    "keyboard_shortcuts_js": "/assets/js/bets/keyboard-shortcuts.js",
    "context_menu_js":       "/assets/js/bets/context-menu.js",
    "scenario_explorer_js":  "/assets/js/bets/scenario-explorer.js",
    "signal_flow_js":        "/assets/js/bets/signal-flow.js",
    "what_changed_js":       "/assets/js/bets/what-changed.js",
    "glossary_js":           "/assets/js/bets/glossary.js",
    "gilded_section":      "player-anchor-section gilded",
    "data_metric_attr":    'data-metric=',
}


@pytest.mark.parametrize("name,needle", list(REQUIRED_ON_CARR.items()))
def test_carr_page_has_module(carr_html: str, name: str, needle: str) -> None:
    assert needle in carr_html, f"Carr page is missing required marker for {name!r}: {needle}"


def test_carr_page_has_one_gilded_section(carr_html: str) -> None:
    # Exactly one section should be gilded (the deterministic picker
    # returns one surface per page).
    matches = re.findall(r'class="section player-anchor-section gilded"', carr_html)
    assert 1 <= len(matches) <= 1, (
        f"Expected exactly one gilded section on Carr page; found {len(matches)}."
    )


def test_mendoza_has_live_room(mendoza_html: str) -> None:
    # Mendoza renders a populated Room (fernando-mendoza is the known
    # data-carrying fixture). The Room's data-state should be "ready".
    assert 'data-state="ready"' in mendoza_html and '"the-room"' in mendoza_html


def test_hot_take_is_paired_with_anti_take(carr_html: str) -> None:
    # Pairing rule is mandatory; if Hot-Take renders, Anti-Take must follow.
    if 'class="hot-take"' in carr_html:
        assert 'class="anti-take"' in carr_html, (
            "Hot-Take present but Anti-Take absent — pairing rule violated."
        )
