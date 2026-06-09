"""Color-blind palette guard (WS-11, spec item 4).

The design system locks a color-blind-safety requirement
(``docs/design-system/31-chart-vocabulary.md`` line ~331): chart ramps and
categorical series must stay distinguishable for deuteranopia / protanopia /
tritanopia viewers, and the one ramp that *can't* (the belief red->grey->green
ramp) must carry redundant shape/icon cues in markup ("up-arrow + green",
"down-arrow + red").

This script parses the real token hex values from
``src/cfb_rankings/team_pages/assets/tokens.css`` and simulates the three
dichromacies (Machado et al. 2009, severity 1.0) to verify:

  * The **percentile ramp** (red->grey->blue) keeps monotonic, distinguishable
    stops under every simulation. This is the workhorse ramp (percentile bars,
    heatmaps) and is supposed to be CB-safe by hue choice (red/blue, never
    red/green).
  * The **belief ramp** (red->grey->green) is the known exception: it collapses
    under deutan/protan by design, so it is *reported* (not failed) as requiring
    the markup shape/icon redundancy mandated by the design-system rule.

Categorical *series* colors are deliberately out of scope: they're team-accent
colors assigned at runtime per team, so there's no fixed shared palette to audit
statically.

Default mode is report-only (exit 0). Pass ``--enforce`` to exit 1 when a
guarded ramp drops below the distinguishability thresholds — wire that into CI
so a future token edit can't silently ship a CB-unsafe percentile ramp.

Usage:
    python scripts/check_color_blind.py
    python scripts/check_color_blind.py --enforce
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

_TOKENS = Path("src/cfb_rankings/team_pages/assets/tokens.css")

# Machado et al. (2009) dichromacy matrices, severity 1.0 (linear-RGB row-major).
_MATS = {
    "deuteranopia": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "protanopia": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "tritanopia": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147601), (0.004733, 0.691367, 0.303900)),
}

# Ramps/series to audit, expressed as token names (resolved from tokens.css).
# allow_rg=True marks the documented red/green exception (rule 331) — reported,
# never failed, because redundancy is provided by markup shape/icon cues.
_PERCENTILE = ("pct-low", "pct-mid-low", "pct-mid", "pct-mid-high", "pct-high")
_BELIEF = ("belief-doom", "belief-mixed", "belief-bullish")

# Distinguishability thresholds in CIE76 deltaE. <~10 = effectively identical;
# <~20 across a full ramp = direction lost. Percentile clears these comfortably
# under all three sims (min adjacent ~16, endpoints ~55), so the floor guards
# against regressions, not the current palette.
_ADJ_MIN = 10.0
_END_MIN = 20.0


def _lin(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _delin(c: float) -> float:
    c = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
    return max(0.0, min(255.0, round(c * 255)))


def _hex2rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _sim(rgb: tuple[float, float, float], mode: str) -> tuple[float, float, float]:
    r, g, b = (_lin(x) for x in rgb)
    return tuple(_delin(row[0] * r + row[1] * g + row[2] * b) for row in _MATS[mode])


def _lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = (_lin(x) for x in rgb)
    X = r * 0.4124 + g * 0.3576 + b * 0.1805
    Y = r * 0.2126 + g * 0.7152 + b * 0.0722
    Z = r * 0.0193 + g * 0.1192 + b * 0.9505

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(X / 0.95047), f(Y / 1.0), f(Z / 1.08883)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def _de(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    la, lb = _lab(a), _lab(b)
    return sum((x - y) ** 2 for x, y in zip(la, lb)) ** 0.5


def _parse_tokens(text: str) -> dict[str, tuple[int, int, int]]:
    out: dict[str, tuple[int, int, int]] = {}
    for name, hexval in re.findall(r"--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})\s*;", text):
        out[name] = _hex2rgb(hexval)
    return out


def _resolve(names: tuple[str, ...], tokens: dict) -> list[tuple[int, int, int]] | None:
    if any(n not in tokens for n in names):
        return None
    return [tokens[n] for n in names]


def _audit_ramp(label: str, rgbs: list, allow_rg: bool) -> tuple[bool, list[str]]:
    """Return (failed, report_lines)."""
    lines = [f"  {label}:"]
    failed = False
    for mode in ("normal", "deuteranopia", "protanopia", "tritanopia"):
        pts = rgbs if mode == "normal" else [_sim(c, mode) for c in rgbs]
        adj = [_de(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
        ep = _de(pts[0], pts[-1])
        bad = mode != "normal" and (min(adj) < _ADJ_MIN or ep < _END_MIN)
        flag = ""
        if bad:
            flag = "  EXCEPTION(rule 331: needs shape/icon)" if allow_rg else "  ⚠ COLLAPSES"
            if not allow_rg:
                failed = True
        lines.append(
            f"    {mode:13} adj_min={min(adj):5.1f}  endpoints={ep:5.1f}{flag}"
        )
    return failed, lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Audit/enforce color-blind palette safety.")
    ap.add_argument("--tokens", default=str(_TOKENS))
    ap.add_argument("--enforce", action="store_true", help="Exit 1 on a guarded collapse.")
    args = ap.parse_args(argv)

    path = Path(args.tokens)
    if not path.is_file():
        print(f"::warning::tokens file not found: {path} — skipping color-blind audit")
        return 0

    tokens = _parse_tokens(path.read_text(encoding="utf-8"))
    print(f"Color-blind palette audit — {path} ({len(tokens)} color tokens)")

    failed = False
    report: list[str] = []

    pct = _resolve(_PERCENTILE, tokens)
    if pct:
        f, lines = _audit_ramp("percentile ramp (guarded)", pct, allow_rg=False)
        failed = failed or f
        report += lines
    else:
        print("::warning::percentile ramp tokens missing — skipped")

    belief = _resolve(_BELIEF, tokens)
    if belief:
        _, lines = _audit_ramp("belief ramp (red/green exception)", belief, allow_rg=True)
        report += lines

    print("\n".join(report))
    print(f"  thresholds: adj>={_ADJ_MIN:.0f} endpoints>={_END_MIN:.0f} (CIE76 deltaE)")

    if args.enforce and failed:
        print("::error::color-blind: a guarded ramp/series is indistinguishable under simulation.")
        return 1
    if failed:
        print("color-blind: guarded palette FAILED (report-only; pass --enforce to gate).")
    else:
        print("color-blind: guarded palettes OK; belief red/green ramp relies on markup shape/icon redundancy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
