"""Receipt Card — share card celebrating a resolved prediction that aged well.

v5-10e Sprint deliverable #4. Posted when a predictive_claims row
flips to outcome_verdict='hit'. Same OG dimensions as the other share
cards (1200×630).

Layout:
  +-----------------------------------------------------------+
  | CFB INDEX                       RECEIPT · MAY 13          |
  |                                                            |
  |  Aged well ✓                                              |
  |                                                            |
  |  Original claim (Apr 22):                                  |
  |  "Drew Allar will lead the preseason Heisman market by    |
  |   the second week of May."                                |
  |                                                            |
  |  — Bill Connelly, ESPN                                    |
  |                                                            |
  |  Resolved: Allar leads at +325, 23.4% market-implied.     |
  |                                                            |
  |  92% aged-well score                          /receipts   |
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
    original_claim_date: str,
    original_claim_quote: str,
    original_attribution: str,
    resolved_summary: str,
    aged_well_pct: int,
    url_line: str = "cfb-index · /receipts",
    dark: bool = False,
) -> Path:
    if Image is None:
        raise ImportError("Pillow is required for receipt_card.render()")
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

    # "Aged well ✓" badge
    badge_color = tokens["green_200" if dark else "green_400"]
    d.rounded_rectangle([(40, 90), (260, 130)], radius=20, fill=badge_color)
    d.text((58, 99), "AGED WELL ✓", fill=tokens["surface"], font=_fnt(18, bold=True))

    # Original claim
    d.text((40, 160), f"Original claim ({original_claim_date}):",
           fill=tokens["muted"], font=_fnt(13, bold=True))
    quote_lines = textwrap.wrap(f'"{original_claim_quote}"', width=58)[:3]
    qy = 185
    for line in quote_lines:
        d.text((40, qy), line, fill=tokens["ink"], font=_fnt_display(32))
        qy += 38
    d.text((40, qy + 8), f"— {original_attribution}",
           fill=tokens["muted"], font=_fnt(15))

    # Resolved section
    resolved_y = max(qy + 50, 380)
    d.text((40, resolved_y), "Resolved:", fill=tokens["muted"], font=_fnt(13, bold=True))
    resolved_lines = textwrap.wrap(resolved_summary, width=66)[:2]
    ry = resolved_y + 24
    for line in resolved_lines:
        d.text((40, ry), line, fill=tokens["ink"], font=_fnt(18))
        ry += 26

    # Footer
    foot_y = H - 56
    d.rectangle([(0, foot_y), (W, H)], fill=tokens["footer_bg"])
    score_text = f"{aged_well_pct}% aged-well score"
    d.text((40, foot_y + 12), score_text, fill=tokens["muted"], font=_fnt(13))
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
