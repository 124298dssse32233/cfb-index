"""Roster Replacement Grid — diverging portal-flow tiles per position group.

Migrated onto the Editorial Grammar (doc 77). A diverging tile/bar layout per
diverging-bar best practice (web research 2026-06-14 — Domo "Divergent Bar
Charts"; ChartGen): centre spine, out grows left / in grows right, diverging
colour scheme (red out / green in), net delta on the right rail, interactive
tiles. Keeps the talent-quality finding-headline (which room upgraded, where
the hole is).
"""
from __future__ import annotations

import html
from typing import Any

from ..models import Annotation
from ..svg_helpers import line
from .grammar import editorial_card, cls_text, SANS, MONO, MUTED, INK, POS, NEG

OUT_C = NEG   # players out (loss) — colour-blind-safe vermillion
IN_C = POS    # players in (gain) — Okabe-Ito blue


def render_roster_replacement_grid(query_result: dict[str, Any], spec_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = query_result.get("rows", [])
    summary = query_result.get("summary_stats", {})
    if not rows:
        return _empty_render("No portal activity recorded for this season.")

    season = summary.get("season_year", "")
    n_in = summary.get("total_incoming", 0)
    n_out = summary.get("total_outgoing", 0)
    headline = _headline_for_grid(rows, summary)
    height = 152 + 30 * len(rows)
    max_count = max([r["incoming_n"] for r in rows] + [r["outgoing_n"] for r in rows] + [1])

    def draw(px, py, pw, ph):
        tx0, tx1 = px + 58, px + pw - 56
        mid = (tx0 + tx1) / 2
        unit = (mid - tx0) / max(1, max_count)
        n = len(rows)
        head_h = 16
        row_h = (ph - head_h) / n
        out = [
            line(mid, py + head_h, mid, py + ph, color=INK, width=1.0),
            cls_text(mid - 6, py + 8, "OUT", "ed-ax", family=SANS, color=MUTED, anchor="end"),
            cls_text(mid + 6, py + 8, "IN", "ed-ax", family=SANS, color=MUTED, anchor="start"),
        ]
        for i, r in enumerate(rows):
            yc = py + head_h + row_h * i + row_h / 2
            out.append(cls_text(px, yc + 4, r["position"], "ed-ax", family=SANS, color=INK, weight="700"))
            ow = r["outgoing_n"] * unit
            if ow > 0:
                t = f"{r['position']}: {r['outgoing_n']} out"
                out.append(f'<rect class="ed-dot" x="{mid - ow:.1f}" y="{yc - 8:.1f}" width="{ow:.1f}" '
                           f'height="16" fill="{OUT_C}" opacity="0.82" tabindex="0" data-tip="{html.escape(t)}">'
                           f'<title>{html.escape(t)}</title></rect>')
                out.append(cls_text(mid - 6, yc + 4, str(r["outgoing_n"]), "ed-ptlabel", family=MONO,
                                    color=INK, anchor="end"))
            iw = r["incoming_n"] * unit
            if iw > 0:
                t = f"{r['position']}: {r['incoming_n']} in"
                out.append(f'<rect class="ed-dot" x="{mid:.1f}" y="{yc - 8:.1f}" width="{iw:.1f}" '
                           f'height="16" fill="{IN_C}" opacity="0.82" tabindex="0" data-tip="{html.escape(t)}">'
                           f'<title>{html.escape(t)}</title></rect>')
                out.append(cls_text(mid + 6, yc + 4, str(r["incoming_n"]), "ed-ptlabel", family=MONO, color=INK))
            net = r["net_n"]
            col = IN_C if net > 0 else (OUT_C if net < 0 else MUTED)
            out.append(cls_text(px + pw, yc + 4, f"net {'+' if net > 0 else ''}{net}", "ed-ptlabel",
                                family=MONO, color=col, anchor="end"))
        return out

    up_pos = summary.get("biggest_upgrade_pos")
    hole_pos = summary.get("biggest_hole_pos")
    bits = [f"Net {summary.get('net_movement', 0):+d}"]
    if up_pos:
        bits.append(f"upgraded {up_pos}")
    if hole_pos:
        bits.append(f"hole at {hole_pos}")
    conf = (query_result.get("confidence") or "unset")
    receipt = (f"Source: CFB Index — transfer portal in/out by position (count) · {season} · "
               f"{n_in} in / {n_out} out · {conf} confidence")
    svg = editorial_card(
        eyebrow=f"TRANSFER PORTAL  ·  {season}", headline=headline,
        annotation="▸ " + " · ".join(bits) + ".", receipt=receipt,
        title=f"Roster Replacement Grid — {season}: {n_in} in, {n_out} out across {len(rows)} positions",
        draw_plot=draw, height=height,
    )
    annotations: list[Annotation] = []
    if up_pos:
        annotations.append(Annotation(target=up_pos, text=f"{up_pos}: biggest talent upgrade",
                                      reason="highest net transfer-points gain by position"))
    if hole_pos:
        annotations.append(Annotation(target=hole_pos, text=f"{hole_pos}: biggest talent hole",
                                      reason="largest net transfer-points loss by position"))
    return {
        "svg_html": svg, "headline_finding": headline, "annotations": annotations,
        "alt_text": f"Roster Replacement Grid {season}: {n_out} out and {n_in} in across {len(rows)} positions.",
    }


def _headline_for_grid(rows: list[dict], summary: dict) -> str:
    n_in = summary.get("total_incoming", 0)
    n_out = summary.get("total_outgoing", 0)
    if n_in == 0 and n_out == 0:
        return "No portal activity recorded for this season."
    up_pos = summary.get("biggest_upgrade_pos")
    hole_pos = summary.get("biggest_hole_pos")
    if up_pos and hole_pos:
        return f"The portal upgraded the {up_pos} room but opened a hole at {hole_pos}."
    if up_pos:
        return f"The portal's biggest win was at {up_pos} — the room got better on paper."
    if hole_pos:
        return f"The portal left a hole at {hole_pos} the roster still has to answer."
    net = summary.get("net_movement", 0)
    biggest = max(rows, key=lambda r: abs(r["net_n"])) if rows else None
    if biggest and abs(biggest["net_n"]) >= 3:
        direction = "added" if biggest["net_n"] > 0 else "lost"
        return (f"The portal {direction} {abs(biggest['net_n'])} net {biggest['position']}s — "
                f"the season's biggest positional swing.")
    if net > 0:
        return f"The portal nets {net:+d} bodies across {len(rows)} positions."
    if net < 0:
        return f"The portal sheds {abs(net)} net bodies across {len(rows)} positions."
    return f"Portal in/out balance is flat at {n_in} in, {n_out} out."


def _empty_render(msg: str) -> dict[str, Any]:
    return {
        "svg_html": f'<svg width="100%" viewBox="0 0 400 60"><text x="20" y="32" '
                    f'font-family="Georgia,serif" font-size="13" fill="#666">{html.escape(msg)}</text></svg>',
        "headline_finding": msg,
        "annotations": [],
        "alt_text": msg,
    }
