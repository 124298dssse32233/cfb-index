"""Tests for the WS-11 page-weight reporter (scripts/check_page_weight.py).

Runs against a tiny synthetic site so it's fast and CI-safe — never touches
the real output/site. Covers archetype bucketing, report-only exit 0, and the
--enforce gate tripping (and not tripping) around the budget.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_page_weight.py"
_spec = importlib.util.spec_from_file_location("check_page_weight", _SCRIPT)
cpw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cpw)


def _make_site(tmp_path: Path) -> Path:
    site = tmp_path / "site"
    (site / "teams").mkdir(parents=True)
    (site / "players").mkdir()
    # A small page and a deliberately huge, hard-to-compress page.
    (site / "index.html").write_text("<html><body>home</body></html>")
    (site / "teams" / "alabama.html").write_text("<html>" + "x" * 200 + "</html>")
    import os
    big = os.urandom(200_000).hex()  # ~400KB of incompressible hex text
    (site / "players" / "huge.html").write_text(f"<html>{big}</html>")
    return site


def test_archetype_for_buckets_known_and_unknown() -> None:
    assert cpw._archetype_for(Path("index.html")) == "root"
    assert cpw._archetype_for(Path("teams/alabama.html")) == "teams"
    assert cpw._archetype_for(Path("players/x/y.html")) == "players"
    assert cpw._archetype_for(Path("weird/page.html")) == "other"


def test_report_only_exits_zero_even_with_huge_page(tmp_path, capsys) -> None:
    site = _make_site(tmp_path)
    rc = cpw.main(["--site-dir", str(site), "--budget-kb", "10"])
    assert rc == 0  # report-only never fails the build
    out = capsys.readouterr().out
    assert "Page-weight report" in out
    assert "huge.html" in out  # worst offender surfaced


def test_enforce_fails_when_over_budget(tmp_path) -> None:
    site = _make_site(tmp_path)
    # 400KB low-redundancy page gzips well over a 10KB budget.
    rc = cpw.main(["--site-dir", str(site), "--budget-kb", "10",
                   "--enforce", "--max-violations", "0"])
    assert rc == 1


def test_enforce_passes_when_under_budget(tmp_path) -> None:
    site = _make_site(tmp_path)
    rc = cpw.main(["--site-dir", str(site), "--budget-kb", "5000", "--enforce"])
    assert rc == 0


def test_enforce_tolerates_allowed_violations(tmp_path) -> None:
    site = _make_site(tmp_path)
    # One page is huge; allowing 1 violation should pass.
    rc = cpw.main(["--site-dir", str(site), "--budget-kb", "10",
                   "--enforce", "--max-violations", "1"])
    assert rc == 0


def test_missing_site_dir_is_non_fatal(tmp_path) -> None:
    rc = cpw.main(["--site-dir", str(tmp_path / "nope")])
    assert rc == 0
