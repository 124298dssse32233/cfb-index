"""Quote Card — single shareable pull-quote share card.

v5-10e Sprint deliverable #5. Spec: docs/mockups/mockup_08_dark_share_cards.html
(the "Daily quote" variant). 1200×630 OG card.

Layout:
  +-----------------------------------------------------------+
  | CFB INDEX                          DAILY · 13 MAY 2026    |
  |                                                            |
  |  "The dead zone is the sport's most consequential work    |
  |  week."                                                    |
  |                                                            |
  |  — Lead take, The Daily                                   |
  |                                                            |
  |  3 sources cited                              /daily       |
  +-----------------------------------------------------------+
"""

from __future__ import annotations

import textwrap
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    Image = ImageDraw = None  # type: ignore

from .mood_map import DARK, LIGHT, _fnt, _fnt_display


W, H = 1200, 630


def render(
    out_path: str | Path,
    *,
    when_label: str,
    quote: str,
    attribution: str = "Lead take, The Daily",
    footer_meta: str = "3 sources cited",
    url_line: str = "cfb-index · /daily",
    dark: bool = False,
) -> Path:
    if Image is None:
        raise ImportError("Pillow is required for quote_card.render()")
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

    # Curly quotes around the body — Pitchfork-style
    quote_marks_color = tokens["amber_100" if dark else "amber_600"]
    d.text((40, 80), "“", fill=quote_marks_color, font=_fnt_display(120))

    # The quote body — wrapped at ~36 chars/line for visual rhythm
    lines = textwrap.wrap(quote, width=36)[:5]  # max 5 lines
    line_y = 160
    for line in lines:
        d.text((100, line_y), line, fill=tokens["ink"], font=_fnt_display(48))
        line_y += 60

    # Attribution
    attr_y = max(line_y + 20, 460)
    d.text((100, attr_y), f"— {attribution}", fill=tokens["muted"], font=_fnt(18))

    # Footer
    foot_y = H - 56
    d.rectangle([(0, foot_y), (W, H)], fill=tokens["footer_bg"])
    d.text((40, foot_y + 12), footer_meta, fill=tokens["muted"], font=_fnt(13))
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


__all__ = ["render"]
