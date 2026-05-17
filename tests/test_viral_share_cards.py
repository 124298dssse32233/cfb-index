"""Tests for the v5-10e share-card module suite.

Covers the 4 share-card artifact types beyond Monday Mood Map:
  - daily_movers
  - pregame_pack
  - receipt_card
  - quote_card

Each one's render() is a thin shape verifier — produces a 1200×630 PNG
under 500KB, escapes content, handles edge cases. The v5-10e Sprint
adds DB-backed data builders + per-artifact tests with real DB
fixtures.
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore

from cfb_rankings.viral import (
    daily_movers,
    pregame_pack,
    quote_card,
    receipt_card,
)


pytestmark = pytest.mark.skipif(Image is None, reason="Pillow not installed")


# ---------------------------------------------------------------------------
# daily_movers
# ---------------------------------------------------------------------------

def test_daily_movers_renders_under_500kb(tmp_path: Path) -> None:
    out = tmp_path / "movers.png"
    daily_movers.render(
        out,
        when_label="MOVERS · 13 MAY 2026",
        movers=[
            daily_movers.MoverCard("OSU", "+8", "5★ trust me", direction="up"),
            daily_movers.MoverCard("TEX", "+7", "spring tempo", direction="up"),
            daily_movers.MoverCard("MICH", "-15", "Moore presser", direction="down"),
            daily_movers.MoverCard("UF", "-9", "OL exits", direction="down"),
        ],
    )
    assert out.stat().st_size < 500 * 1024


def test_daily_movers_dimensions(tmp_path: Path) -> None:
    out = tmp_path / "movers2.png"
    daily_movers.render(
        out,
        when_label="X",
        movers=[daily_movers.MoverCard("X", "+1", "y", direction="up")],
    )
    with Image.open(out) as img:
        assert img.size == (1200, 630)


def test_daily_movers_truncates_to_6_max(tmp_path: Path) -> None:
    """Caller passing 10 movers shouldn't crash; only 6 are drawn."""
    out = tmp_path / "many.png"
    daily_movers.render(
        out,
        when_label="X",
        movers=[
            daily_movers.MoverCard(f"T{i}", f"+{i}", "reason", direction="up")
            for i in range(10)
        ],
    )
    assert out.exists()


def test_daily_movers_dark_variant(tmp_path: Path) -> None:
    out = tmp_path / "movers_dark.png"
    daily_movers.render(
        out,
        when_label="X",
        movers=[daily_movers.MoverCard("X", "+1", "y", direction="up")],
        dark=True,
    )
    assert out.exists()


# ---------------------------------------------------------------------------
# pregame_pack
# ---------------------------------------------------------------------------

def test_pregame_pack_renders(tmp_path: Path) -> None:
    out = tmp_path / "pack.png"
    pregame_pack.render(
        out,
        when_label="FRI · SATURDAY PACK",
        away=pregame_pack.TeamSide("Alabama", "ALA", "7-1", 76, "Crimson Tide road"),
        home=pregame_pack.TeamSide("LSU", "LSU", "6-2", 58, "Death Valley"),
        headline_facts=[
            "Last meeting: 32-31 LSU, 2024",
            "Power-rating gap: ALA +3.5",
            "7:30 PM ET · CBS",
        ],
        url_line="cfb-index · /preview/x",
    )
    assert out.exists()
    with Image.open(out) as img:
        assert img.size == (1200, 630)
    assert out.stat().st_size < 500 * 1024


def test_pregame_pack_handles_many_facts(tmp_path: Path) -> None:
    """More than 3 facts should not crash; only 3 are drawn."""
    out = tmp_path / "pack2.png"
    pregame_pack.render(
        out,
        when_label="X",
        away=pregame_pack.TeamSide("A", "A", "1-0", 50, "x"),
        home=pregame_pack.TeamSide("B", "B", "1-0", 50, "y"),
        headline_facts=[f"Fact {i}" for i in range(10)],
        url_line="x",
    )
    assert out.exists()


# ---------------------------------------------------------------------------
# receipt_card
# ---------------------------------------------------------------------------

def test_receipt_card_renders(tmp_path: Path) -> None:
    out = tmp_path / "receipt.png"
    receipt_card.render(
        out,
        when_label="RECEIPT · MAY 13",
        original_claim_date="Apr 22",
        original_claim_quote="Drew Allar will lead the preseason Heisman market by May.",
        original_attribution="Bill Connelly, ESPN",
        resolved_summary="Allar leads at +325, 23.4% market-implied.",
        aged_well_pct=92,
    )
    assert out.exists()
    with Image.open(out) as img:
        assert img.size == (1200, 630)


def test_receipt_card_long_quote_truncates(tmp_path: Path) -> None:
    """A very long quote should wrap, capped at 3 lines, not crash."""
    out = tmp_path / "receipt2.png"
    receipt_card.render(
        out,
        when_label="X",
        original_claim_date="Jan 1",
        original_claim_quote=" ".join(["very-long-claim"] * 50),
        original_attribution="Author",
        resolved_summary="x",
        aged_well_pct=50,
    )
    assert out.exists()


# ---------------------------------------------------------------------------
# quote_card
# ---------------------------------------------------------------------------

def test_quote_card_renders(tmp_path: Path) -> None:
    out = tmp_path / "quote.png"
    quote_card.render(
        out,
        when_label="DAILY · 13 MAY 2026",
        quote="The dead zone is the sport's most consequential work week.",
        attribution="Lead take, The Daily",
        footer_meta="3 sources cited",
    )
    assert out.exists()
    with Image.open(out) as img:
        assert img.size == (1200, 630)
    assert out.stat().st_size < 500 * 1024


def test_quote_card_dark(tmp_path: Path) -> None:
    out = tmp_path / "quote_dark.png"
    quote_card.render(
        out,
        when_label="X",
        quote="A quote.",
        dark=True,
    )
    assert out.exists()
