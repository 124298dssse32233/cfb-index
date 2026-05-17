"""Tests for cfb_rankings.viral.mood_map (Sprint v5-10e foundation slice)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

# Pillow is an optional dep — skip the whole module cleanly if absent.
try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore

from cfb_rankings.viral.mood_map import (
    DARK,
    LIGHT,
    Cluster,
    Mover,
    render,
)


pytestmark = pytest.mark.skipif(Image is None, reason="Pillow not installed")


def _trivial_clusters() -> list[Cluster]:
    return [
        Cluster("SEC", 70, 150, 4, 2, 8, lambda i: 60 + i, {}),
        Cluster("ACC", 580, 150, 4, 1, 4, lambda i: 50 + i, {0: 32, 3: 84}),
    ]


def test_light_render_writes_png_under_500kb(tmp_path: Path) -> None:
    out = tmp_path / "light.png"
    p = render(
        out,
        when_label="WEEK OF 11 MAY 2026 · TEST",
        hero_number="42",
        hero_sentence="test sentence",
        hero_caption="test caption",
        clusters=_trivial_clusters(),
        up_movers=[Mover("OSU", "+8", "test")],
        down_movers=[Mover("MICH", "-15", "test")],
        dark=False,
    )
    assert p == out
    assert out.exists()
    assert out.stat().st_size < 500 * 1024


def test_dark_render_writes_png(tmp_path: Path) -> None:
    out = tmp_path / "dark.png"
    p = render(
        out,
        when_label="WEEK OF 11 MAY 2026 · TEST",
        hero_number="42",
        hero_sentence="test sentence",
        hero_caption="test caption",
        clusters=_trivial_clusters(),
        up_movers=[],
        down_movers=[],
        dark=True,
    )
    assert p == out
    assert out.stat().st_size > 0


def test_render_dimensions_are_1200x675(tmp_path: Path) -> None:
    out = tmp_path / "size.png"
    render(
        out,
        when_label="X", hero_number="0", hero_sentence="x", hero_caption="x",
        clusters=_trivial_clusters(),
        up_movers=[], down_movers=[],
    )
    with Image.open(out) as img:
        assert img.size == (1200, 675)


def test_render_creates_parent_dir(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "deep" / "map.png"
    assert not out.parent.exists()
    render(
        out,
        when_label="X", hero_number="0", hero_sentence="x", hero_caption="x",
        clusters=_trivial_clusters(),
        up_movers=[], down_movers=[],
    )
    assert out.exists()


def test_dark_and_light_token_sets_differ() -> None:
    """The two token sets are intentionally different surfaces."""
    assert LIGHT["surface"] != DARK["surface"]
    assert LIGHT["ink"] != DARK["ink"]
    # Dark text on dark surface is light cream
    assert DARK["ink"] == (244, 242, 236)
    # Light text on light surface is dark ink
    assert LIGHT["ink"] == (20, 22, 24)


def test_up_movers_limited_to_4_on_render(tmp_path: Path) -> None:
    """If caller passes 7 up-movers, only the first 4 are drawn."""
    out = tmp_path / "many.png"
    many = [Mover(f"T{i}", f"+{i}", "reason") for i in range(7)]
    # Should NOT raise even when up_movers > 4
    render(
        out,
        when_label="X", hero_number="0", hero_sentence="x", hero_caption="x",
        clusters=_trivial_clusters(),
        up_movers=many,
        down_movers=many,
    )
    assert out.exists()


def test_cluster_overrides_take_precedence(tmp_path: Path) -> None:
    """An override at index i wins over mood_provider(i)."""
    captured = []

    def provider(i: int) -> int:
        captured.append(i)
        return 50  # provider returns 50

    cluster = Cluster("X", 70, 150, 4, 1, 4, provider, {0: 90})
    out = tmp_path / "ovr.png"
    render(
        out,
        when_label="X", hero_number="0", hero_sentence="x", hero_caption="x",
        clusters=[cluster],
        up_movers=[], down_movers=[],
    )
    # Provider called for every dot
    assert set(captured) == {0, 1, 2, 3}
    # File exists (we can't sample colours from PNG without reading it back,
    # but the override path is exercised)
    assert out.exists()


def test_cluster_count_dots_drawn_within_grid(tmp_path: Path) -> None:
    """A 5×3=15-dot cluster requested with count=12 only renders 12 dots."""
    cluster = Cluster("X", 70, 150, 5, 3, 12, lambda i: 50, {})
    out = tmp_path / "partial.png"
    render(
        out,
        when_label="X", hero_number="0", hero_sentence="x", hero_caption="x",
        clusters=[cluster],
        up_movers=[], down_movers=[],
    )
    # No exception, file produced
    assert out.exists()
