"""mockup_07: Monday Mood Map — 1200x675 viral artifact.

Round 5 (autonomous): regional / conference clustering replaces the
generic 13x10 grid. Each conference is a labeled cluster, dots colored
on the belief ramp. Real Mood Index seeds for the labeled movers.

Output: docs/mockups/mockup_07_monday_mood_map.png
Spec: §H.3 — 1200x675, <500KB, posts via GitHub Action Mon 9am ET.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

OUT = "docs/mockups/mockup_07_monday_mood_map.png"
W, H = 1200, 675

# Tokens (from docs/design-system/00-tokens.md)
SURFACE = (250, 250, 249)
INK = (20, 22, 24)
MUTED = (108, 108, 110)
SUBTLE = (160, 160, 162)
LINE = (224, 223, 219)
AMBER_100 = (250, 199, 117)
AMBER_400 = (186, 117, 23)
AMBER_600 = (133, 79, 11)
AMBER_800 = (99, 56, 6)
GREEN_400 = (29, 158, 117)
GREEN_600 = (15, 110, 86)
RED_400 = (226, 75, 74)
RED_600 = (163, 45, 45)
NAVY_400 = (55, 138, 221)
GRAY_400 = (136, 135, 128)
GRAY_200 = (180, 178, 169)


def belief_color(score):
    """Map mood score (0..100) to a continuous red→gray→green ramp."""
    if score is None:
        return GRAY_200
    if score < 35:
        return (220, 75, 75)
    if score < 45:
        return (220, 130, 110)
    if score < 55:
        return (170, 170, 165)
    if score < 65:
        return GRAY_400
    if score < 75:
        return (130, 195, 155)
    return GREEN_400


def fnt(size, bold=False):
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


def fnt_display(size):
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


def rounded_pill(draw, xy, radius, fill):
    """Draw filled rounded rectangle."""
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


# ---- Conference clusters (real composition, mood scores hand-seeded per cluster) ----
# Real conference rosters as of 2026:
#   SEC: 16 teams · Big Ten: 18 teams · ACC: 17 · Big 12: 16 ·
#   Pac: 2 (residual) · AAC: 14 · MWC: 12 · CUSA: 10 · Sun Belt: 14 · MAC: 12 ·
#   FBS Independents: ~6
# Total = 130

CLUSTERS = [
    # (label, x, y, cols, rows, count, mood_seed_func)
    ("SEC",            70,  150, 8, 2, 16, lambda i: 62 + 18 * math.sin(i * 0.3) - 5 * math.cos(i * 1.1)),
    ("BIG TEN",        70,  280, 9, 2, 18, lambda i: 55 + 22 * math.cos(i * 0.5)),
    ("ACC",            70,  410, 9, 2, 17, lambda i: 55 + 14 * math.sin(i * 0.7)),
    ("BIG 12",         70,  540, 8, 2, 16, lambda i: 60 + 14 * math.cos(i * 0.6)),
    ("PAC",            580, 150, 2, 1, 2,  lambda i: 56 + 6 * (-1)**i),
    ("AAC",            680, 150, 7, 2, 14, lambda i: 52 + 10 * math.sin(i * 0.5)),
    ("MWC",            580, 280, 6, 2, 12, lambda i: 58 + 12 * math.cos(i * 0.4)),
    ("CUSA",           810, 280, 5, 2, 10, lambda i: 52 + 8 * math.sin(i * 0.7)),
    ("SUN BELT",       580, 410, 7, 2, 14, lambda i: 55 + 10 * math.cos(i * 0.5)),
    ("MAC",            780, 410, 6, 2, 12, lambda i: 50 + 9 * math.sin(i * 0.6)),
    ("FBS IND.",       580, 540, 3, 2, 6,  lambda i: 64 + 12 * math.cos(i * 0.7)),
]

# Specific overrides — labeled movers we'll callout
# Each entry: cluster_label, dot_index_in_cluster, override_mood
OVERRIDES = {
    ("SEC", 0): 84,        # Texas — up
    ("SEC", 1): 38,        # Florida — down
    ("SEC", 5): 36,        # Auburn — down
    ("SEC", 2): 32,        # Alabama — down (the W17 "ordinary contender")
    ("BIG TEN", 0): 32,    # Michigan — the headliner
    ("BIG TEN", 1): 86,    # Ohio State — up
    ("BIG TEN", 5): 82,    # Iowa — up
    ("BIG TEN", 7): 42,    # Wisconsin — down
    ("BIG 12", 0): 78,     # Boise State (Mountain West actually but easier visual)
    ("MWC", 0): 84,        # Boise (real spot — up)
}


def draw_cluster(d, label, x, y, cols, rows, count, mood_fn, base_idx):
    """Draw labeled grid of dots with cluster header."""
    # Cluster header
    d.text((x, y - 14), label, fill=AMBER_800, font=fnt(10, bold=True))
    # Grid dimensions
    step_x = 28
    step_y = 28
    for i in range(count):
        col = i % cols
        row = i // cols
        cx = x + col * step_x
        cy = y + row * step_y
        # Lookup override or computed seed
        mood = OVERRIDES.get((label, i), int(max(20, min(95, mood_fn(i)))))
        color = belief_color(mood)
        r = 10
        # White ring then fill
        d.ellipse([(cx - r - 1, cy - r - 1), (cx + r + 1, cy + r + 1)], fill=SURFACE)
        d.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=color)
    return count


# ---- Build canvas ----
img = Image.new("RGB", (W, H), SURFACE)
d = ImageDraw.Draw(img)

# Masthead
d.rectangle([(0, 0), (W, 56)], fill=INK)
d.text((40, 16), "CFB INDEX", fill=SURFACE, font=fnt_display(28))
when = "MONDAY MOOD MAP · WEEK OF 11 MAY 2026 · No. 048"
when_w = d.textlength(when, font=fnt(13, bold=True))
d.text((W - when_w - 40, 22), when, fill=(220, 220, 215), font=fnt(13, bold=True))

# Hero finding (top, full-width band)
hero_y = 80
d.text((40, hero_y), "WHAT THIS WEEK SHOWS", fill=MUTED, font=fnt(11, bold=True))
d.text((40, hero_y + 18), "47 of 130", fill=INK, font=fnt_display(72))
d.text((255, hero_y + 28), "fanbases diverged from the model by more than 15 spots.",
       fill=INK, font=fnt(18))
d.text((255, hero_y + 55), "Sample: 202,341 mentions · 47 sources · 7 days · High confidence",
       fill=MUTED, font=fnt(12))
# Amber underline
d.rectangle([(40, hero_y + 95), (180, hero_y + 99)], fill=AMBER_400)

# Conference clusters
base = 0
for (label, x, y, cols, rows, count, mood_fn) in CLUSTERS:
    base += draw_cluster(d, label, x, y, cols, rows, count, mood_fn, base)

# Section divider
d.line([(40, 130), (W - 40, 130)], fill=LINE, width=1)

# ---- Movers callouts (top-right column) ----
mv_x = 940
mv_y = 200
d.text((mv_x, mv_y - 18), "TOP MOVERS · ±MOOD vs LAST WEEK",
       fill=MUTED, font=fnt(10, bold=True))

up_movers = [
    ("OSU",  "+8", "5★ trust me"),
    ("TEX",  "+7", "spring tempo"),
    ("BSU",  "+5", "no exits"),
    ("IOWA", "+4", "RPO footage"),
]
down_movers = [
    ("MICH", "−15", "Moore presser"),
    ("UF",   "−9",  "OL exits"),
    ("AUB",  "−7",  "quiet portal"),
    ("WIS",  "−6",  "DC departure"),
]

# Up column
for i, (team, delta, reason) in enumerate(up_movers):
    y = mv_y + i * 22
    rounded_pill(d, [(mv_x, y), (mv_x + 70, y + 18)], radius=9, fill=GREEN_400)
    d.text((mv_x + 6, y + 3), f"{team} {delta}",
           fill=SURFACE, font=fnt(11, bold=True))
    d.text((mv_x + 78, y + 3), reason, fill=INK, font=fnt(11))

# Down column
for i, (team, delta, reason) in enumerate(down_movers):
    y = mv_y + 100 + i * 22
    rounded_pill(d, [(mv_x, y), (mv_x + 80, y + 18)], radius=9, fill=RED_400)
    d.text((mv_x + 6, y + 3), f"{team} {delta}",
           fill=SURFACE, font=fnt(11, bold=True))
    d.text((mv_x + 88, y + 3), reason, fill=INK, font=fnt(11))

# Belief legend at the bottom
legend_y = H - 86
d.text((40, legend_y - 14), "BELIEF RAMP — LOW", fill=MUTED, font=fnt(10, bold=True))
d.text((W - 40 - d.textlength("HIGH", font=fnt(10, bold=True)), legend_y - 14),
       "HIGH", fill=MUTED, font=fnt(10, bold=True))

stripe_x0, stripe_x1 = 200, W - 100
stripe_y0, stripe_y1 = legend_y - 8, legend_y
stops = 80
seg = (stripe_x1 - stripe_x0) / stops
for k in range(stops):
    t = k / (stops - 1)
    if t < 0.5:
        u = t / 0.5
        c = tuple(int(RED_400[j] + (GRAY_400[j] - RED_400[j]) * u) for j in range(3))
    else:
        u = (t - 0.5) / 0.5
        c = tuple(int(GRAY_400[j] + (GREEN_400[j] - GRAY_400[j]) * u) for j in range(3))
    d.rectangle([(stripe_x0 + k * seg, stripe_y0),
                 (stripe_x0 + (k + 1) * seg, stripe_y1)], fill=c)

# Footer
foot_y = H - 56
d.rectangle([(0, foot_y), (W, H)], fill=(244, 242, 235))
d.text((40, foot_y + 8),
       "Methodology v1.0 · 47 sources · ET-anchored 7-day window · receipts honored",
       fill=MUTED, font=fnt(13))
d.text((40, foot_y + 28),
       "Auto-generated Monday 6am ET via GitHub Action · auto-posted 9am ET",
       fill=SUBTLE, font=fnt(10))
url = "cfb-index · /hub"
url_w = d.textlength(url, font=fnt(13, bold=True))
d.text((W - url_w - 40, foot_y + 12), url, fill=AMBER_600, font=fnt(13, bold=True))

# Save
os.makedirs(os.path.dirname(OUT), exist_ok=True)
img.save(OUT, "PNG", optimize=True)
size_kb = os.path.getsize(OUT) / 1024
print(f"Wrote {OUT}  ({size_kb:.1f} KB · {W}x{H})")
