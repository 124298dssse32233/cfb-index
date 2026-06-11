"""Tests for the robust baseline logic in scripts/verify_collect_volume.py.

The volume gate must catch a genuine collector collapse WITHOUT crying wolf on a
backfill-heavy / sparse offseason history (the 2026-06-11 false alarm, where a
150k-doc one-time backfill inflated the median and a normal 5.4k-doc day looked
like a >75% drop).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "verify_collect_volume.py"
_spec = importlib.util.spec_from_file_location("verify_collect_volume", _SCRIPT)
vcv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vcv)


def test_real_2026_06_11_noisy_history_skips():
    # The actual numbers that caused the false alarm. Only 6800 + 31897 survive
    # outlier removal (40 too low, 150690 a backfill) -> < 3 normal days -> SKIP.
    verdict, _ = vcv.assess(5435, [40, 6800, 31897, 150690])
    assert verdict == "SKIP"


def test_too_few_active_days_skips():
    verdict, _ = vcv.assess(5000, [6000, 6200])
    assert verdict == "SKIP"


def test_stable_baseline_healthy_today_ok():
    verdict, _ = vcv.assess(6000, [6000, 6200, 5800, 6100, 5900])
    assert verdict == "OK"


def test_stable_baseline_collapse_today_fails():
    # 1000 is below 25% of the ~6000 typical -> genuine collapse.
    verdict, msg = vcv.assess(1000, [6000, 6200, 5800, 6100, 5900])
    assert verdict == "FAIL"
    assert "1,000" in msg


def test_backfill_spike_does_not_inflate_baseline():
    # 150000 is a one-time backfill; it must be dropped so typical stays ~6000
    # and a normal 5000-doc day passes.
    verdict, _ = vcv.assess(5000, [6000, 6000, 6000, 6000, 150000])
    assert verdict == "OK"


def test_dead_day_does_not_drag_baseline_down():
    # A 40-doc partial-failure day must be dropped, not pull the floor down.
    verdict, _ = vcv.assess(5000, [6000, 6000, 6000, 6000, 40])
    assert verdict == "OK"


def test_collapse_still_caught_with_backfill_present():
    # Even with a backfill in history, a real collapse today is still flagged.
    verdict, _ = vcv.assess(500, [6000, 6000, 6000, 6000, 150000])
    assert verdict == "FAIL"
