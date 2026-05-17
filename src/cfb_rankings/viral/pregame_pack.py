"""Pre-game Pack — Friday-night share for Saturday games.

v5-10e Sprint deliverable #3. One per marquee Saturday matchup. Posted
Friday 6pm ET via cron when a Saturday game's pre-game pack has been
generated.

Two-team-on-one-card layout (1200×630):
  +-----------------------------------------------------------+
  | CFB INDEX                       FRI · SATURDAY PACK       |
  |                                                            |
  |  ALA  · 7-1, mood 76     |    LSU  · 6-2, mood 58         |
  |  Crimson Tide road       |    Tigers home in Death Valley |
  |                                                            |
  |  ★ Last meeting: 32-31 LSU, 2024 (last play)              |
  |  ★ Power-rating gap: ALA +3.5 · 7:30 PM ET · CBS          |
  |                                                            |
  |  cfb-index · /preview/2026-w11-alabama-lsu                |
  +-----------------------------------------------------------+
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    Image = ImageDraw = None  # type: ignore

from .mood_map import DARK, LIGHT, _fnt, _fnt_display


W, H = 1200, 630


@dataclass(frozen=True)
class TeamSide:
    name: str               # "Alabama"
    abbr: str               # "ALA"
    record: str             # "7-1"
    mood: int               # 76
    short_line: str         # "Crimson Tide road"


def render(
    out_path: str | Path,
    *,
    when_label: str,
    away: TeamSide,
    home: TeamSide,
    headline_facts: list[str],
    url_line: str,
    dark: bool = False,
) -> Path:
    if Image is None:
        raise ImportError("Pillow is required for pregame_pack.render()")
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    tokens = DARK if dark else LIGHT
    img = Image.new("RGB", (W, H), tokens["surface"])
    d = ImageDraw.Draw(img)

    # Masthead
    d.rectangle([(0, 0), (W, 56)], fill=tokens["masthead_bg"])
    d.text((40, 16), "CFB INDEX", fill=tokens["masthead_fg"], font=_fnt_display(28))
    label_font = _fnt(13, bold=True)
    label_w = d.textlength(when_label, font=label_font)
    d.text(
        (W - label_w - 40, 22),
        when_label,
        fill=tokens["masthead_meta"],
        font=label_font,
    )

    # Two team panels side-by-side
    mid_x = W // 2
    d.line([(mid_x, 100), (mid_x, 380)], fill=tokens["line"], width=1)

    for i, side in enumerate((away, home)):
        col_x = 80 if i == 0 else mid_x + 40
        d.text((col_x, 100), side.abbr, fill=tokens["ink"], font=_fnt_display(80))
        d.text((col_x, 200), side.name, fill=tokens["ink"], font=_fnt_display(40))
        d.text((col_x, 250), f"· {side.record}, mood {side.mood}",
               fill=tokens["muted"], font=_fnt(16))
        line_wrapped = textwrap.wrap(side.short_line, width=24)
        ly = 290
        for ln in line_wrapped[:2]:
            d.text((col_x, ly), ln, fill=tokens["ink"], font=_fnt(18))
            ly += 26

    # Headline facts (3 max)
    fy = 410
    for fact in headline_facts[:3]:
        d.text((40, fy), f"★ {fact}", fill=tokens["ink"], font=_fnt(18))
        fy += 30

    # Footer
    foot_y = H - 56
    d.rectangle([(0, foot_y), (W, H)], fill=tokens["footer_bg"])
    url_font = _fnt(13, bold=True)
    url_w = d.textlength(url_line, font=url_font)
    d.text(
        (W - url_w - 40, foot_y + 12),
        url_line,
        fill=tokens["amber_100" if dark else "amber_600"],
        font=url_font,
    )

    img.save(out, "PNG", optimize=True)
    return out


__all__ = ["TeamSide", "render"]
