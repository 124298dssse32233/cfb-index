"""Regression tests for qb_fingerprint._pct() — locked in after the
"14.3%%" double-percent bug from Mendoza's screenshot (2026-05-23).

The previous implementation used a broken rstrip chain that ALWAYS
concatenated a second "%" because the inner endswith check ran
against the un-suffixed format string. Result: "14.3%" + "%" = "14.3%%"
across every Heisman-Heat narrative on every top player page.
"""
from cfb_rankings.profile.qb_fingerprint import _pct


def test_pct_probability_form() -> None:
    """0..1 inputs scale to percentage. No double %."""
    assert _pct(0.143) == "14.3%"
    assert _pct(0.75) == "75%"
    assert _pct(0.5) == "50%"


def test_pct_percentage_form() -> None:
    """0..100 inputs pass through as-is. No double %."""
    assert _pct(14.3) == "14.3%"
    assert _pct(75.0) == "75%"
    assert _pct(99.9) == "99.9%"


def test_pct_whole_numbers_drop_decimal() -> None:
    """Whole percentages render without trailing '.0%'."""
    assert _pct(1.0) == "100%"
    assert _pct(0.0) == "<1%"
    assert _pct(50.0) == "50%"


def test_pct_low_clamp() -> None:
    """Sub-half-percent rounds to '<1%' instead of '0.0%' or empty."""
    assert _pct(0.004) == "0.4%"
    assert _pct(0.0001) == "<1%"
    assert _pct(0) == "<1%"


def test_pct_invalid_returns_none() -> None:
    """Non-numeric input returns None, not a stringified error."""
    assert _pct(None) is None
    assert _pct("not a number") is None
    assert _pct([1, 2, 3]) is None


def test_pct_no_double_percent_anywhere() -> None:
    """Defensive sweep: no value should produce '%%' in output."""
    samples = [0.0, 0.001, 0.05, 0.1, 0.143, 0.5, 0.75, 0.999, 1.0,
               14.3, 50.0, 75.0, 99.5, 100.0]
    for s in samples:
        result = _pct(s)
        assert result is None or "%%" not in result, (
            f"_pct({s!r}) produced '%%' in output: {result!r}"
        )


def test_pct_accepts_string_numerics() -> None:
    """String input that parses as float works."""
    assert _pct("0.5") == "50%"
    assert _pct("75") == "75%"
