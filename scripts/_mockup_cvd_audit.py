"""Color Vision Deficiency (CVD) audit on chart palettes.

Simulates protanopia (red-blind), deuteranopia (green-blind), and tritanopia
(blue-blind) for each of the chart colors used in the mockups, then checks
that distinguishable pairs (the chart needs to distinguish the lines) remain
distinguishable after the simulation.

Uses the standard Brettel/Vienot/Mollon transform matrices.
"""

# Brettel et al. 1997 transform matrices for sRGB → simulated dichromat
PROTANOPIA = [
    [0.567, 0.433, 0.000],
    [0.558, 0.442, 0.000],
    [0.000, 0.242, 0.758],
]
DEUTERANOPIA = [
    [0.625, 0.375, 0.000],
    [0.700, 0.300, 0.000],
    [0.000, 0.300, 0.700],
]
TRITANOPIA = [
    [0.950, 0.050, 0.000],
    [0.000, 0.433, 0.567],
    [0.000, 0.475, 0.525],
]


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def simulate(rgb, m):
    r, g, b = (c / 255.0 for c in rgb)
    out = (
        m[0][0] * r + m[0][1] * g + m[0][2] * b,
        m[1][0] * r + m[1][1] * g + m[1][2] * b,
        m[2][0] * r + m[2][1] * g + m[2][2] * b,
    )
    return tuple(int(max(0, min(255, round(c * 255)))) for c in out)


def color_distance(c1, c2):
    """Euclidean distance in CIE-Lab — approximated via RGB for speed.
    Threshold of ~30 is generally a confidently distinguishable pair."""
    return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2) ** 0.5


def hex_str(rgb):
    return "#" + "".join(f"{c:02X}" for c in rgb)


# Chart colors used in mockups
HUB_DIVERGENCE_LINES = [
    ("Big 12 (coral-400)", "#D85A30"),
    ("ACC (navy-600)",     "#185FA5"),
    ("SEC (gray-400)",     "#888780"),
    ("Big Ten (gray-400)", "#888780"),
]

HEISMAN_LINES = [
    ("Allar (amber-400)",      "#BA7517"),
    ("Carr (navy-600)",        "#185FA5"),
    ("Sayin (green-600)",      "#0F6E56"),
    ("Love (gray-400)",        "#888780"),
    ("Underwood (coral-400)",  "#D85A30"),
]

DELTA = [
    ("Up (green-600)",   "#0F6E56"),
    ("Down (red-600)",   "#A32D2D"),
    ("Flat (text-muted)","#6C6C6E"),
]


def audit_chart(name, lines, threshold=30):
    print(f"\n=== {name} ===")
    rgbs = [(label, hex_to_rgb(h)) for label, h in lines]
    print(f"  {'PAIR':<50} {'NORMAL':>7} {'PROT':>7} {'DEUT':>7} {'TRIT':>7}")
    fails = []
    for i in range(len(rgbs)):
        for j in range(i + 1, len(rgbs)):
            (la, ra), (lb, rb) = rgbs[i], rgbs[j]
            normal = color_distance(ra, rb)
            prot = color_distance(simulate(ra, PROTANOPIA), simulate(rb, PROTANOPIA))
            deut = color_distance(simulate(ra, DEUTERANOPIA), simulate(rb, DEUTERANOPIA))
            trit = color_distance(simulate(ra, TRITANOPIA), simulate(rb, TRITANOPIA))
            pair = f"{la[:25]} vs {lb[:25]}"
            status = ""
            if min(prot, deut, trit) < threshold:
                fails.append((pair, prot, deut, trit))
                status = "  <- LOW"
            print(f"  {pair:<50} {normal:>7.0f} {prot:>7.0f} {deut:>7.0f} {trit:>7.0f}{status}")
    return fails


all_fails = []
all_fails += [("Hub", *f) for f in audit_chart("Hub divergence chart lines", HUB_DIVERGENCE_LINES)]
all_fails += [("Heisman", *f) for f in audit_chart("Heisman horse-race lines", HEISMAN_LINES)]
all_fails += [("Delta", *f) for f in audit_chart("Delta indicators (up/down/flat)", DELTA)]

print("\n" + "-" * 90)
print(f"Total: {len(all_fails)} low-distinguishability pair(s) (threshold {30})")
if all_fails:
    print("\nRecommendation: pairs below the threshold should NOT rely on color")
    print("alone — line patterns (dashed/dotted), labels at endpoints, or different")
    print("stroke weights can carry the distinction. Mockups already use direct")
    print("end-of-line labels on every chart, which is the proper accessibility")
    print("backstop.")
