"""Dark-variant Mood Map render — for iMessage / Slack / Twitter dark clients.

Same data, same composition as scripts/_mockup_mood_map.py but on the
dark-mode token set from docs/design-system/00-tokens.md @media dark-mode block.

Output: docs/mockups/mockup_07c_monday_mood_map_dark.png
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

OUT = "docs/mockups/mockup_07c_monday_mood_map_dark.png"
W, H = 1200, 675

# Dark-mode tokens
SURFACE = (26, 26, 24)              # --color-surface dark = #1A1A18
SURFACE_CARD = (36, 34, 32)         # --color-surface-card dark = #242220
INK = (244, 242, 236)               # --color-text dark = #F4F2EC
MUTED = (180, 178, 169)             # --color-text-muted dark = #B4B2A9
SUBTLE = (138, 136, 132)
LINE = (40, 40, 38)
AMBER_100 = (250, 199, 117)         # warm display accent
AMBER_400 = (186, 117, 23)
AMBER_600 = (133, 79, 11)
AMBER_800 = (99, 56, 6)
GREEN_400 = (29, 158, 117)
GREEN_200 = (93, 202, 165)          # lighter for dark surface
RED_400 = (226, 75, 74)
RED_200 = (240, 149, 149)           # lighter for dark surface
GRAY_400 = (136, 135, 128)
GRAY_300 = (160, 158, 150)


def belief_color(score):
    if score is None:
        return GRAY_400
    if score < 35:
        return RED_200
    if score < 45:
        return (235, 145, 130)
    if score < 55:
        return GRAY_300
    if score < 65:
        return GRAY_400
    if score < 75:
        return (140, 215, 175)
    return GREEN_200


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
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


# Same clusters as the light version
CLUSTERS = [
    ("SEC",       70,  150, 8, 2, 16, lambda i: 62 + 18 * math.sin(i * 0.3) - 5 * math.cos(i * 1.1)),
    ("BIG TEN",   70,  280, 9, 2, 18, lambda i: 55 + 22 * math.cos(i * 0.5)),
    ("ACC",       70,  410, 9, 2, 17, lambda i: 55 + 14 * math.sin(i * 0.7)),
    ("BIG 12",    70,  540, 8, 2, 16, lambda i: 60 + 14 * math.cos(i * 0.6)),
    ("PAC",       580, 150, 2, 1, 2,  lambda i: 56 + 6 * (-1)**i),
    ("AAC",       680, 150, 7, 2, 14, lambda i: 52 + 10 * math.sin(i * 0.5)),
    ("MWC",       580, 280, 6, 2, 12, lambda i: 58 + 12 * math.cos(i * 0.4)),
    ("CUSA",      810, 280, 5, 2, 10, lambda i: 52 + 8 * math.sin(i * 0.7)),
    ("SUN BELT",  580, 410, 7, 2, 14, lambda i: 55 + 10 * math.cos(i * 0.5)),
    ("MAC",       780, 410, 6, 2, 12, lambda i: 50 + 9 * math.sin(i * 0.6)),
    ("FBS IND.",  580, 540, 3, 2, 6,  lambda i: 64 + 12 * math.cos(i * 0.7)),
]

OVERRIDES = {
    ("SEC", 0): 84,
    ("SEC", 1): 38,
    ("SEC", 5): 36,
    ("SEC", 2): 32,
    ("BIG TEN", 0): 32,
    ("BIG TEN", 1): 86,
    ("BIG TEN", 5): 82,
    ("BIG TEN", 7): 42,
    ("BIG 12", 0): 78,
    ("MWC", 0): 84,
}


def draw_cluster(d, label, x, y, cols, rows, count, mood_fn):
    d.text((x, y - 14), label, fill=AMBER_100, font=fnt(10, bold=True))
    step_x = 28
    step_y = 28
    for i in range(count):
        col = i % cols
        row = i // cols
        cx = x + col * step_x
        cy = y + row * step_y
        mood = OVERRIDES.get((label, i), int(max(20, min(95, mood_fn(i)))))
        color = belief_color(mood)
        r = 10
        d.ellipse([(cx - r - 1, cy - r - 1), (cx + r + 1, cy + r + 1)], fill=SURFACE_CARD)
        d.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=color)


# ---- Build canvas ----
img = Image.new("RGB", (W, H), SURFACE)
d = ImageDraw.Draw(img)

# Masthead — invert: light bar on dark surface so it reads as masthead
d.rectangle([(0, 0), (W, 56)], fill=SURFACE_CARD)
d.text((40, 16), "CFB INDEX", fill=AMBER_100, font=fnt_display(28))
when = "MONDAY MOOD MAP · WEEK OF 11 MAY 2026 · No. 048"
when_w = d.textlength(when, font=fnt(13, bold=True))
d.text((W - when_w - 40, 22), when, fill=MUTED, font=fnt(13, bold=True))

# Hero finding
hero_y = 80
d.text((40, hero_y), "WHAT THIS WEEK SHOWS", fill=MUTED, font=fnt(11, bold=True))
d.text((40, hero_y + 18), "47 of 130", fill=INK, font=fnt_display(72))
d.text((255, hero_y + 28), "fanbases diverged from the model by more than 15 spots.",
       fill=INK, font=fnt(18))
d.text((255, hero_y + 55), "Sample: 202,341 mentions · 47 sources · 7 days · High confidence",
       fill=MUTED, font=fnt(12))
d.rectangle([(40, hero_y + 95), (180, hero_y + 99)], fill=AMBER_100)

# Clusters
for (label, x, y, cols, rows, count, mood_fn) in CLUSTERS:
    draw_cluster(d, label, x, y, cols, rows, count, mood_fn)

# Section divider
d.line([(40, 130), (W - 40, 130)], fill=LINE, width=1)

# Movers
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

# Up column — green pill with dark text inside (since pill is bright on dark bg)
for i, (team, delta, reason) in enumerate(up_movers):
    y = mv_y + i * 22
    rounded_pill(d, [(mv_x, y), (mv_x + 70, y + 18)], radius=9, fill=GREEN_200)
    d.text((mv_x + 6, y + 3), f"{team} {delta}",
           fill=SURFACE, font=fnt(11, bold=True))
    d.text((mv_x + 78, y + 3), reason, fill=INK, font=fnt(11))

for i, (team, delta, reason) in enumerate(down_movers):
    y = mv_y + 100 + i * 22
    rounded_pill(d, [(mv_x, y), (mv_x + 80, y + 18)], radius=9, fill=RED_200)
    d.text((mv_x + 6, y + 3), f"{team} {delta}",
           fill=SURFACE, font=fnt(11, bold=True))
    d.text((mv_x + 88, y + 3), reason, fill=INK, font=fnt(11))

# Legend
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
        c = tuple(int(RED_200[j] + (GRAY_300[j] - RED_200[j]) * u) for j in range(3))
    else:
        u = (t - 0.5) / 0.5
        c = tuple(int(GRAY_300[j] + (GREEN_200[j] - GRAY_300[j]) * u) for j in range(3))
    d.rectangle([(stripe_x0 + k * seg, stripe_y0),
                 (stripe_x0 + (k + 1) * seg, stripe_y1)], fill=c)

# Footer
foot_y = H - 56
d.rectangle([(0, foot_y), (W, H)], fill=SURFACE_CARD)
d.text((40, foot_y + 8),
       "Methodology v1.0 · 47 sources · ET-anchored 7-day window · receipts honored",
       fill=MUTED, font=fnt(13))
d.text((40, foot_y + 28),
       "Auto-generated Monday 6am ET via GitHub Action · auto-posted 9am ET · DARK VARIANT",
       fill=SUBTLE, font=fnt(10))
url = "cfb-index · /hub"
url_w = d.textlength(url, font=fnt(13, bold=True))
d.text((W - url_w - 40, foot_y + 12), url, fill=AMBER_100, font=fnt(13, bold=True))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
img.save(OUT, "PNG", optimize=True)
size_kb = os.path.getsize(OUT) / 1024
print(f"Wrote {OUT}  ({size_kb:.1f} KB · {W}x{H} · DARK)")
