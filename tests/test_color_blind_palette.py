"""Tests for the WS-11 color-blind palette guard (scripts/check_color_blind.py).

Pins three things: (1) the dichromacy simulation actually collapses a red/green
pair while preserving a red/blue pair, (2) the guard FAILS a synthetic
red->grey->green ramp when it isn't allowlisted (proving teeth), and (3) the
real tokens.css passes --enforce today (percentile ramp CB-safe; belief ramp
treated as the documented shape/icon-redundancy exception).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_color_blind.py"
_spec = importlib.util.spec_from_file_location("check_color_blind", _SCRIPT)
ccb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ccb)

_RED = ccb._hex2rgb("#c04a4a")
_GREEN = ccb._hex2rgb("#3ea073")
_BLUE = ccb._hex2rgb("#3570b5")
_GREY = ccb._hex2rgb("#8a90a1")


def test_simulation_collapses_red_green_but_not_red_blue() -> None:
    # Normal vision: red is far from both green and blue.
    assert ccb._de(_RED, _GREEN) > 50
    assert ccb._de(_RED, _BLUE) > 50
    # Protanopia: red/green collapse; red/blue stays distinguishable.
    rg = ccb._de(ccb._sim(_RED, "protanopia"), ccb._sim(_GREEN, "protanopia"))
    rb = ccb._de(ccb._sim(_RED, "protanopia"), ccb._sim(_BLUE, "protanopia"))
    assert rg < 25
    assert rb > 35


def test_guard_fails_unallowlisted_red_green_ramp() -> None:
    # A red->grey->green ramp masquerading as a guarded (non-exception) ramp
    # must be reported as failed.
    failed, lines = ccb._audit_ramp("synthetic", [_RED, _GREY, _GREEN], allow_rg=False)
    assert failed is True
    assert any("COLLAPSES" in ln for ln in lines)


def test_belief_exception_never_fails() -> None:
    # Same collapsing ramp, but allowlisted as the rule-331 exception: reported,
    # never failed.
    failed, lines = ccb._audit_ramp("belief", [_RED, _GREY, _GREEN], allow_rg=True)
    assert failed is False
    assert any("EXCEPTION" in ln for ln in lines)


def test_safe_ramp_passes() -> None:
    # The real red->grey->blue percentile ramp survives every simulation.
    ramp = [ccb._hex2rgb(h) for h in ("#c04a4a", "#d9845e", "#8a90a1", "#5a9dd1", "#3570b5")]
    failed, _ = ccb._audit_ramp("percentile", ramp, allow_rg=False)
    assert failed is False


def test_real_tokens_pass_enforce() -> None:
    # End-to-end: the checked-in tokens.css passes --enforce (exit 0).
    assert ccb.main(["--enforce"]) == 0
