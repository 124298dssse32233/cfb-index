"""Monday Mood Map — 1200x675 viral PNG (light + dark variants).

Sprint v5-10e foundation slice. Specs:
  - IMPLEMENTATION_PLAN_v3_iteration.md §H.3
  - docs/mockups/mockup_07_monday_mood_map.png (light, 50KB)
  - docs/mockups/mockup_07c_monday_mood_map_dark.png (dark, 54KB)
  - docs/mockups/mockup_07b_mood_map_svg.html (accessible SVG counterpart)

The light/dark token sets come from docs/design-system/00-tokens.md.
Output: 1200x675 PNG, under the 500KB share-card budget.

Public API:
    render(
        out_path,
        *,
        when_label,        # "WEEK OF 11 MAY 2026 · No. 048"
        hero_number,       # "47 of 130"
        hero_sentence,     # "fanbases diverged from the model..."
        hero_caption,      # "Sample: 202,341 mentions · 47 sources · 7 days"
        clusters,          # list[Cluster]
        up_movers,         # list[Mover] — max 4
        down_movers,       # list[Mover] — max 4
        dark=False,
    ) -> Path

Each Cluster is (label, x, y, cols, rows, dot_count, mood_provider).
``mood_provider(i)`` returns a 0-100 mood score for dot index i.

This module is renderer-only. The data shapes come from the v5-10e
generator (Sprint deliverable), which queries fanbase_mood_weekly +
hub_issue_metadata + lexicon_weekly to build the inputs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover — pillow is an optional dep
    Image = ImageDraw = ImageFont = None  # type: ignore[assignment]


W, H = 1200, 675


# ---------------------------------------------------------------------------
# Token sets (light + dark) from docs/design-system/00-tokens.md
# ---------------------------------------------------------------------------

LIGHT = {
    "surface":      (250, 250, 249),   # bone-paper #FAFAF9
    "surface_card": (255, 255, 255),
    "ink":          (20,  22,  24),    # #141618
    "muted":        (108, 108, 110),
    "subtle":       (160, 160, 162),
    "line":         (224, 223, 219),
    "amber_100":    (250, 199, 117),
    "amber_400":    (186, 117, 23),
    "amber_600":    (133, 79,  11),
    "amber_800":    (99,  56,  6),
    "green_400":    (29,  158, 117),
    "green_200":    (93,  202, 165),
    "red_400":      (226, 75,  74),
    "red_200":      (240, 149, 149),
    "gray_400":     (136, 135, 128),
    "footer_bg":    (244, 242, 235),
    "masthead_bg":  (20,  22,  24),    # dark masthead on light surface
    "masthead_fg":  (250, 250, 249),
    "masthead_meta": (220, 220, 215),
}

DARK = {
    "surface":      (26,  26,  24),    # dark surface #1A1A18
    "surface_card": (36,  34,  32),    # #242220
    "ink":          (244, 242, 236),   # #F4F2EC
    "muted":        (180, 178, 169),   # #B4B2A9
    "subtle":       (138, 136, 132),
    "line":         (40,  40,  38),
    "amber_100":    (250, 199, 117),
    "amber_400":    (186, 117, 23),
    "amber_600":    (133, 79,  11),
    "amber_800":    (99,  56,  6),
    "green_400":    (29,  158, 117),
    "green_200":    (93,  202, 165),
    "red_400":      (226, 75,  74),
    "red_200":      (240, 149, 149),
    "gray_400":     (136, 135, 128),
    "gray_300":     (160, 158, 150),
    "footer_bg":    (36,  34,  32),
    "masthead_bg":  (36,  34,  32),    # subtle dark masthead on darker surface
    "masthead_fg":  (250, 199, 117),
    "masthead_meta": (180, 178, 169),
}


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------

MoodProvider = Callable[[int], int]


@dataclass(frozen=True)
class Cluster:
    """One conference cluster of dots."""
    label: str
    x: int
    y: int
    cols: int
    rows: int
    count: int
    mood_provider: MoodProvider
    overrides: dict[int, int] = field(default_factory=dict)
    """Per-dot mood overrides — keyed by dot index within the cluster."""


@dataclass(frozen=True)
class Mover:
    """One labeled mover (up or down)."""
    abbr: str         # "MICH", "OSU", etc.
    delta: str        # "+8", "-15"
    reason: str       # "Moore presser", "5★ trust me"


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def _belief_color(score: int, tokens: dict, dark: bool) -> tuple[int, int, int]:
    """Map a mood score 0-100 to a token-driven color."""
    if score < 35:
        return tokens["red_200" if dark else "red_400"]
    if score < 45:
        return (235, 145, 130) if dark else (220, 130, 110)
    if score < 55:
        return tokens.get("gray_300") if dark else tokens["gray_400"]  # type: ignore
    if score < 65:
        return tokens["gray_400"]
    if score < 75:
        return (140, 215, 175) if dark else (130, 195, 155)
    return tokens["green_200" if dark else "green_400"]


# ---------------------------------------------------------------------------
# Font loaders
# ---------------------------------------------------------------------------

def _fnt(size: int, bold: bool = False):
    """Load a regular/bold sans font, falling back through common system fonts."""
    if ImageFont is None:
        return None
    candidates = [
        ("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        ("C:/Windows/Fonts/seguibl.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _fnt_display(size: int):
    """Bebas-Neue-like display font (locked typography choice)."""
    if ImageFont is None:
        return None
    candidates = [
        "C:/Windows/Fonts/BebasNeue-Regular.ttf",
        "C:/Windows/Fonts/Impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            pass
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def _draw_cluster(d, cluster: Cluster, tokens: dict, dark: bool) -> None:
    """Draw one cluster of dots with its label."""
    d.text(
        (cluster.x, cluster.y - 14),
        cluster.label,
        fill=tokens["amber_100" if dark else "amber_800"],
        font=_fnt(10, bold=True),
    )
    step = 28
    for i in range(cluster.count):
        col = i % cluster.cols
        row = i // cluster.cols
        cx = cluster.x + col * step
        cy = cluster.y + row * step
        mood = cluster.overrides.get(
            i, int(max(20, min(95, cluster.mood_provider(i))))
        )
        color = _belief_color(mood, tokens, dark)
        r = 10
        # White ring
        d.ellipse(
            [(cx - r - 1, cy - r - 1), (cx + r + 1, cy + r + 1)],
            fill=tokens["surface_card"] if dark else tokens["surface"],
        )
        d.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=color)


def _draw_movers(d, movers_up, movers_down, tokens: dict, dark: bool) -> None:
    mv_x = 940
    mv_y = 200
    d.text(
        (mv_x, mv_y - 18),
        "TOP MOVERS · ±MOOD vs LAST WEEK",
        fill=tokens["muted"],
        font=_fnt(10, bold=True),
    )
    up_color = tokens["green_200" if dark else "green_400"]
    dn_color = tokens["red_200" if dark else "red_400"]
    pill_text_fill = tokens["surface"] if dark else tokens["surface"]
    for i, m in enumerate(movers_up[:4]):
        y = mv_y + i * 22
        d.rounded_rectangle(
            [(mv_x, y), (mv_x + 70, y + 18)], radius=9, fill=up_color
        )
        d.text(
            (mv_x + 6, y + 3),
            f"{m.abbr} {m.delta}",
            fill=pill_text_fill,
            font=_fnt(11, bold=True),
        )
        d.text(
            (mv_x + 78, y + 3),
            m.reason,
            fill=tokens["ink"],
            font=_fnt(11),
        )
    for i, m in enumerate(movers_down[:4]):
        y = mv_y + 100 + i * 22
        d.rounded_rectangle(
            [(mv_x, y), (mv_x + 80, y + 18)], radius=9, fill=dn_color
        )
        d.text(
            (mv_x + 6, y + 3),
            f"{m.abbr} {m.delta}",
            fill=pill_text_fill,
            font=_fnt(11, bold=True),
        )
        d.text(
            (mv_x + 88, y + 3),
            m.reason,
            fill=tokens["ink"],
            font=_fnt(11),
        )


def _draw_legend(d, tokens: dict, dark: bool) -> None:
    """The bottom belief-ramp stripe."""
    legend_y = H - 86
    d.text(
        (40, legend_y - 14),
        "BELIEF RAMP — LOW",
        fill=tokens["muted"],
        font=_fnt(10, bold=True),
    )
    high_txt = "HIGH"
    high_w = d.textlength(high_txt, font=_fnt(10, bold=True))
    d.text(
        (W - 40 - high_w, legend_y - 14),
        high_txt,
        fill=tokens["muted"],
        font=_fnt(10, bold=True),
    )
    stripe_x0, stripe_x1 = 200, W - 100
    stripe_y0, stripe_y1 = legend_y - 8, legend_y
    stops = 80
    seg = (stripe_x1 - stripe_x0) / stops
    red = tokens["red_200" if dark else "red_400"]
    gray = tokens.get("gray_300" if dark else "gray_400", (136, 135, 128))
    green = tokens["green_200" if dark else "green_400"]
    for k in range(stops):
        t = k / (stops - 1)
        if t < 0.5:
            u = t / 0.5
            c = tuple(int(red[j] + (gray[j] - red[j]) * u) for j in range(3))
        else:
            u = (t - 0.5) / 0.5
            c = tuple(int(gray[j] + (green[j] - gray[j]) * u) for j in range(3))
        d.rectangle(
            [(stripe_x0 + k * seg, stripe_y0),
             (stripe_x0 + (k + 1) * seg, stripe_y1)],
            fill=c,
        )


# ---------------------------------------------------------------------------
# Public render API
# ---------------------------------------------------------------------------

def render(
    out_path: str | Path,
    *,
    when_label: str,
    hero_number: str,
    hero_sentence: str,
    hero_caption: str,
    clusters: list[Cluster],
    up_movers: list[Mover],
    down_movers: list[Mover],
    dark: bool = False,
    methodology_line: str = "Methodology v1.0 · 47 sources · ET-anchored 7-day window · receipts honored",
    cadence_line: str = "Auto-generated Monday 6am ET via GitHub Action · auto-posted 9am ET",
    url_line: str = "cfb-index · /hub",
) -> Path:
    """Render the Monday Mood Map to ``out_path`` and return the path.

    Raises ImportError if Pillow isn't available. Otherwise returns the
    output Path (parent created if missing).
    """
    if Image is None:
        raise ImportError("Pillow is required for mood_map.render()")

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

    # Hero finding (top-left band)
    hero_y = 80
    d.text(
        (40, hero_y),
        "WHAT THIS WEEK SHOWS",
        fill=tokens["muted"],
        font=_fnt(11, bold=True),
    )
    d.text((40, hero_y + 18), hero_number, fill=tokens["ink"], font=_fnt_display(72))
    d.text((255, hero_y + 28), hero_sentence, fill=tokens["ink"], font=_fnt(18))
    d.text((255, hero_y + 55), hero_caption, fill=tokens["muted"], font=_fnt(12))
    d.rectangle([(40, hero_y + 95), (180, hero_y + 99)],
                fill=tokens["amber_100" if dark else "amber_400"])

    # Divider
    d.line([(40, 130), (W - 40, 130)], fill=tokens["line"], width=1)

    # Conference clusters
    for cluster in clusters:
        _draw_cluster(d, cluster, tokens, dark)

    # Movers
    _draw_movers(d, up_movers, down_movers, tokens, dark)

    # Legend
    _draw_legend(d, tokens, dark)

    # Footer
    foot_y = H - 56
    d.rectangle([(0, foot_y), (W, H)], fill=tokens["footer_bg"])
    d.text((40, foot_y + 8), methodology_line,
           fill=tokens["muted"], font=_fnt(13))
    d.text((40, foot_y + 28), cadence_line,
           fill=tokens["subtle"], font=_fnt(10))
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


__all__ = ["Cluster", "Mover", "render", "LIGHT", "DARK"]
