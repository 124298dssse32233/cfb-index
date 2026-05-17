"""WCAG AA contrast audit on the locked design tokens.

For every fg/bg pair used in the mockups, compute the WCAG 2.1 relative
luminance ratio. Flag any combination below the AA threshold.

Thresholds (WCAG 2.1):
  - Normal text  : 4.5:1
  - Large text (>= 18pt regular / 14pt bold) : 3.0:1
  - UI components / graphical objects : 3.0:1
"""

import sys


def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def relative_luminance(rgb):
    """WCAG 2.1 relative luminance from sRGB tuple."""
    def channel(c):
        cs = c / 255.0
        return cs / 12.92 if cs <= 0.03928 else ((cs + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg_hex, bg_hex):
    l1 = relative_luminance(hex_to_rgb(fg_hex))
    l2 = relative_luminance(hex_to_rgb(bg_hex))
    lighter, darker = (l1, l2) if l1 > l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)


TOKENS = {
    # surfaces
    "ink":             "#141618",
    "text-muted":      "#6C6C6E",
    "text-subtle":     "#A0A0A2",
    "surface":         "#FAFAF9",
    "surface-card":    "#FFFFFF",
    "amber-50":        "#FAEEDA",
    "amber-100":       "#FAC775",
    "amber-200":       "#EF9F27",
    "amber-400":       "#BA7517",
    "amber-600":       "#854F0B",
    "amber-800":       "#633806",
    "navy-400":        "#378ADD",
    "navy-600":        "#185FA5",
    "navy-800":        "#0C447C",
    "green-50":        "#E1F5EE",
    "green-400":       "#1D9E75",
    "green-600":       "#0F6E56",
    "green-800":       "#085041",
    "red-50":          "#FCEBEB",
    "red-400":         "#E24B4A",
    "red-600":         "#A32D2D",
    "red-800":         "#791F1F",
    "gray-50":         "#F1EFE8",
    "gray-100":        "#D3D1C7",
    "gray-400":        "#888780",
    "gray-600":        "#5F5E5A",
    "gray-800":        "#444441",
    # Alabama accent
    "alabama-primary": "#9E1B32",
    # Vandy accent
    "vandy-primary":   "#000000",
    "vandy-secondary": "#CFAE70",
}

PAIRS = [
    # (fg, bg, label, threshold, kind)
    ("ink",          "surface",       "Body text on bone paper",            4.5, "text"),
    ("ink",          "surface-card",  "Body text on white card",            4.5, "text"),
    ("text-muted",   "surface",       "Muted caption on bone paper",        4.5, "text"),
    ("text-muted",   "surface-card",  "Muted caption on white",             4.5, "text"),
    # text-subtle text-color usages all patched to text-muted in the mockups.
    # The token itself remains at #A0A0A2 in 00-tokens.md (locked).
    # Flagged for v5-5.5 review: either narrow its documented use to truly
    # decorative purposes, or darken to #7E7E80 (3.6x large / fails normal).
    ("text-muted",   "surface",       "Patched: was text-subtle, now muted",  4.5, "text"),
    ("gray-400",     "surface",       "Patched: dot divider (graphic)",       3.0, "graphic"),
    ("amber-600",    "surface",       "Amber accent text on bone paper",    4.5, "text"),
    ("amber-600",    "surface-card",  "Amber accent text on white",         4.5, "text"),
    ("amber-800",    "amber-50",      "Confidence/chip — amber-800/50",     4.5, "text"),
    ("amber-800",    "amber-100",     "Card eyebrow on amber-100 bg",       4.5, "text"),
    ("amber-400",    "surface",       "Amber accent stroke (graphic)",      3.0, "graphic"),
    ("navy-600",     "surface",       "Navy accent text",                   4.5, "text"),
    ("navy-800",     "surface",       "Navy heading",                       4.5, "text"),
    ("navy-600",     "surface-card",  "Navy accent on white",               4.5, "text"),
    ("green-800",    "green-50",      "Confidence chip — high",             4.5, "text"),
    ("green-600",    "surface-card",  "Green delta-up",                     4.5, "text"),
    ("red-800",      "red-50",        "Confidence chip — low",              4.5, "text"),
    ("red-600",      "surface-card",  "Red delta-down",                     4.5, "text"),
    ("red-600",      "surface",       "Red FINAL/UPSET text",               4.5, "text"),
    ("gray-800",     "gray-50",       "Confidence chip — unset",            4.5, "text"),
    ("gray-600",     "surface-card",  "Tertiary caption",                   4.5, "text"),
    # Program accents
    ("surface-card", "alabama-primary","Alabama crest mark (white on red)", 4.5, "text"),
    ("alabama-primary","surface",     "Alabama accent text",                4.5, "text"),
    ("alabama-primary","amber-50",    "Alabama pulse accent",               4.5, "text"),
    ("vandy-secondary","vandy-primary","Vandy crest (gold on black)",       4.5, "text"),
    # Mood Map
    ("ink",          "amber-50",      "Mood-map sample caption",            4.5, "text"),
    ("text-muted",   "amber-50",      "Mood-map secondary on cream",        4.5, "text"),
]


def main():
    print(f"{'STATUS':<6}  {'RATIO':>6}  {'NEED':>5}  PAIR")
    print("-" * 88)
    fails = 0
    warns = 0
    for fg, bg, label, threshold, kind in PAIRS:
        r = contrast_ratio(TOKENS[fg], TOKENS[bg])
        status = "PASS" if r >= threshold else "FAIL"
        if status == "FAIL":
            fails += 1
        elif r < threshold * 1.15:
            warns += 1
        print(f"{status:<6}  {r:>5.2f}x  {threshold:>4.1f}x  {label}  [{fg} on {bg}, {kind}]")
    print("-" * 88)
    print(f"Total: {len(PAIRS)} pairs · {fails} fails · {warns} warn-zone (within 15% of threshold)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
