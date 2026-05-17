"""Daily Belief Movers — share card for the day's biggest fanbase deltas.

v5-10e Sprint deliverable #2. Spec: docs/design-system/30-page-archetypes.md +
docs/mockups/mockup_08_dark_share_cards.html.

Layout (1200×630 OG-card-optimal):
  +-----------------------------------------------------------+
  | CFB INDEX                          MOVERS · 13 MAY 2026   |
  |                                                            |
  |  Today's biggest belief moves                              |
  |                                                            |
  |  [+8 OSU]   5★ trust me ─ recruiting confidence spiked     |
  |  [+7 TEX]   spring tempo footage drove the room            |
  |  [-15 MICH] Moore presser still resonating                 |
  |  [-9 UF]    OL transfer-portal exits                       |
  |                                                            |
  |  Sample: 47 sources · 7 days  ✓ high confidence            |
  |                                /daily                       |
  +-----------------------------------------------------------+

Scaffold today — full render function lives here, the DB-backed data
builder is the v5-10e Sprint deliverable.

Public API:
    render(out_path, *, when_label, movers, sample_caption, dark=False)
        movers: list[MoverCard] — up to 6 (3 up + 3 down typical)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    Image = ImageDraw = None  # type: ignore

from .mood_map import DARK, LIGHT, _fnt, _fnt_display


W, H = 1200, 630


@dataclass(frozen=True)
class MoverCard:
    abbr: str
    delta: str
    reason: str
    direction: Literal["up", "down"]


def render(
    out_path: str | Path,
    *,
    when_label: str,
    movers: list[MoverCard],
    sample_caption: str = "Sample: 47 sources · 7 days · High confidence",
    title: str = "Today's biggest belief moves",
    url_line: str = "cfb-index · /daily",
    dark: bool = False,
) -> Path:
    if Image is None:
        raise ImportError("Pillow is required for daily_movers.render()")
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

    # Title
    d.text((40, 100), title, fill=tokens["ink"], font=_fnt_display(56))

    # Movers list — up to 6
    y = 190
    for m in movers[:6]:
        is_up = m.direction == "up"
        pill_color = tokens["green_200" if dark else "green_400"] if is_up \
            else tokens["red_200" if dark else "red_400"]
        pill_text = f"{m.delta} {m.abbr}"
        d.rounded_rectangle([(40, y), (200, y + 44)], radius=22, fill=pill_color)
        d.text((54, y + 12), pill_text, fill=tokens["surface"], font=_fnt(20, bold=True))
        d.text((220, y + 14), m.reason, fill=tokens["ink"], font=_fnt(18))
        y += 60

    # Footer
    foot_y = H - 56
    d.rectangle([(0, foot_y), (W, H)], fill=tokens["footer_bg"])
    d.text((40, foot_y + 12), sample_caption, fill=tokens["muted"], font=_fnt(13))
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


__all__ = ["MoverCard", "render"]
