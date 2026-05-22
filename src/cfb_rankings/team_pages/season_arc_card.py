"""CFPEraView renderer — 2014+ zoomed-out multi-metric view.

Spec: ``docs/design-system/13-modules-archive.md`` §CFPEraView.

Six sub-components:

1. Header — era title + thesis (LLM-generated per program).
2. 5-column meta strip (record · CFP appearances · title games · top-10 finishes · titles).
3. Trajectory SVG (640×200) — quality-score polyline + AP-rank polyline
   (inverted so higher = better) + amber vertical markers for CFP years.
4. Era ribbon at chart bottom — coaching regimes derived from the profile's
   `era_name_overrides`.
5. 10-season brick index (2014+ actually present in DB; spec's 13-season was
   for the full CFP era including a forward look).
6. Closing paragraph (serif, editorial) + 3-stat peer footer.
"""
from __future__ import annotations

import html
import json
from typing import Any

from .profile_loader import Profile


def _is_partial_row(r: dict[str, Any]) -> bool:
    """Read the partial-data flag stashed in notes_json by the loader."""
    notes = r.get("notes_json")
    if not notes:
        return False
    try:
        data = json.loads(notes) if isinstance(notes, str) else dict(notes)
    except (TypeError, ValueError):
        return False
    return bool(data.get("is_partial"))


def render_season_arc_card(
    profile: Profile,
    rows: list[dict[str, Any]],
    *,
    thesis: str | None = None,
    closing: str | None = None,
    accent_primary: str,
) -> str:
    """Render the CFPEraView HTML fragment."""
    if not rows:
        return ""

    meta_html = _render_meta_strip(rows)
    chart_html = _render_chart(profile, rows, accent_primary)
    bricks_html = _render_brick_index(profile, rows)
    closing_html = _render_closing(profile, rows, thesis, closing)

    return f"""<section class="arc-card" aria-labelledby="arc-title">
  <header class="arc-card__header">
    <span class="arc-card__eyebrow">THE ERA · {rows[0]['season_year']} THROUGH {rows[-1]['season_year']}</span>
    <h2 id="arc-title" class="arc-card__title">The CFP Era</h2>
    {_render_thesis(thesis, profile, rows)}
  </header>
  {meta_html}
  {chart_html}
  {bricks_html}
  {closing_html}
</section>"""


# ------------------------------------------------------------------------
# Thesis
# ------------------------------------------------------------------------

def _render_thesis(thesis: str | None, profile: Profile, rows: list[dict[str, Any]]) -> str:
    if thesis:
        return f'<p class="arc-card__thesis">{html.escape(thesis)}</p>'
    # Deterministic fallback
    years = [r["season_year"] for r in rows]
    cfp_n = sum(1 for r in rows if r["cfp_flag"])
    tg_n = sum(1 for r in rows if r["title_game_flag"])
    titles = sum(1 for r in rows if r["title_won_flag"])
    if titles:
        txt = f"{titles} title{'s' if titles != 1 else ''}, {cfp_n} CFP appearances across {len(years)} seasons — the era the program defined."
    elif cfp_n:
        txt = f"{cfp_n} CFP appearance{'s' if cfp_n != 1 else ''}, {tg_n} title game{'s' if tg_n != 1 else ''} across {len(years)} seasons — the era the program argued for."
    else:
        txt = f"{len(years)} seasons inside the CFP era, no bids yet — the era the program is still trying to break into."
    return f'<p class="arc-card__thesis arc-card__thesis--fallback">{html.escape(txt)}</p>'


# ------------------------------------------------------------------------
# Meta strip
# ------------------------------------------------------------------------

def _render_meta_strip(rows: list[dict[str, Any]]) -> str:
    total_w = sum(r["wins"] or 0 for r in rows)
    total_l = sum(r["losses"] or 0 for r in rows)
    cfp_n = sum(1 for r in rows if r["cfp_flag"])
    tg_n = sum(1 for r in rows if r["title_game_flag"])
    titles = sum(1 for r in rows if r["title_won_flag"])
    top10 = sum(1 for r in rows if (r["ap_rank_final"] or 99) <= 10)

    tiles = [
        ("ERA RECORD", f"{total_w}-{total_l}", f"{len(rows)} seasons"),
        ("CFP BIDS", str(cfp_n), f"{cfp_n}/{len(rows)} seasons"),
        ("TITLE GAMES", str(tg_n), f"{tg_n} appearance{'s' if tg_n != 1 else ''}"),
        ("TOP-10 FINISHES", str(top10), "AP polled only"),
        ("TITLES", str(titles), "national champions"),
    ]
    tile_html = "".join(
        f"""<div class="arc-card__meta-tile">
          <span class="arc-card__meta-label">{html.escape(lbl)}</span>
          <span class="arc-card__meta-value">{html.escape(val)}</span>
          <span class="arc-card__meta-sub">{html.escape(sub)}</span>
        </div>"""
        for lbl, val, sub in tiles
    )
    return f'<div class="arc-card__meta-strip">{tile_html}</div>'


# ------------------------------------------------------------------------
# Chart — 640×210 SVG
# ------------------------------------------------------------------------

def _render_chart(profile: Profile, rows: list[dict[str, Any]], accent: str) -> str:
    if len(rows) < 2:
        return ""

    # X mapping
    years = [r["season_year"] for r in rows]
    n = len(rows)
    x_left, x_right = 40, 600
    y_top, y_bottom = 20, 150
    # viewBox extends to 210 to make room for the coach-regime ribbon at
    # y=186..200 and the year-label row at y=205 (v1.1 polish).
    ribbon_top, ribbon_bottom = 186.0, 200.0
    y_year_labels = 205.0
    width = x_right - x_left
    height = y_bottom - y_top

    def x_of(i: int) -> float:
        if n == 1:
            return x_left + width / 2
        return x_left + (i / (n - 1)) * width

    def x_of_year(year: int) -> float:
        """Linear pixel position for a year even if it's not in the rows array.
        Used by the ribbon + annotations which may reference years outside the
        brick range.
        """
        if n == 1:
            return x_left + width / 2
        y0, y1 = years[0], years[-1]
        if y1 == y0:
            return x_left + width / 2
        t = max(0.0, min(1.0, (year - y0) / (y1 - y0)))
        return x_left + t * width

    # Quality score polyline — breaks into segments where quality_score is NULL
    # (dataset-gap years), so the chart doesn't draw through zero.
    quality_segments: list[list[tuple[float, float, dict[str, Any]]]] = []
    current_seg: list[tuple[float, float, dict[str, Any]]] = []
    for i, r in enumerate(rows):
        q = r["quality_score"]
        if q is None:
            if current_seg:
                quality_segments.append(current_seg)
                current_seg = []
            continue
        y = y_bottom - (q / 100.0) * height
        current_seg.append((x_of(i), y, r))
    if current_seg:
        quality_segments.append(current_seg)
    quality_polylines = ""
    for seg in quality_segments:
        if len(seg) < 2:
            continue
        coords = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in seg)
        quality_polylines += f'\n      <polyline class="arc-chart__quality" points="{coords}" style="stroke: {accent};" />'

    # AP rank polyline (inverted: rank 1 → near top, rank 25+ → near bottom;
    # missing seasons drop the polyline with a gap).
    ap_segments: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    for i, r in enumerate(rows):
        ap = r["ap_rank_final"]
        if ap is None or ap > 25:
            if current:
                ap_segments.append(current)
                current = []
            continue
        # rank 1 → y=y_top+4, rank 25 → y=y_bottom-6
        y = y_top + 4 + ((ap - 1) / 24.0) * (height - 10)
        current.append((x_of(i), y))
    if current:
        ap_segments.append(current)

    # CFP vertical markers — full chart height (v1.1). A gold vertical line
    # from y_top..y_bottom with a small "CFP" label 18px above the top dot.
    cfp_markers: list[str] = []
    for i, r in enumerate(rows):
        if not r["cfp_flag"]:
            continue
        cx = x_of(i)
        marker_cls = "arc-chart__cfp arc-chart__cfp--title" if r["title_won_flag"] else "arc-chart__cfp"
        cfp_markers.append(
            f'<line class="{marker_cls}" x1="{cx:.1f}" y1="{y_top - 2}" x2="{cx:.1f}" y2="{y_bottom}" />'
        )
        # Top-of-line dot (y_top) + "CFP" eyebrow 18px above the dot
        cfp_markers.append(
            f'<circle class="arc-chart__cfp-dot" cx="{cx:.1f}" cy="{y_top - 2}" r="3.5" />'
        )
        cfp_markers.append(
            f'<text x="{cx:.1f}" y="{y_top - 8}" text-anchor="middle" class="arc-chart__cfp-eyebrow">CFP</text>'
        )
        if r["title_won_flag"]:
            cfp_markers.append(
                f'<text x="{cx:.1f}" y="{y_top + 10}" text-anchor="middle" class="arc-chart__cfp-label arc-chart__cfp-label--won">★ {r["season_year"]}</text>'
            )
        elif r["title_game_flag"]:
            cfp_markers.append(
                f'<text x="{cx:.1f}" y="{y_top + 10}" text-anchor="middle" class="arc-chart__cfp-label">☆ {r["season_year"]}</text>'
            )

    # Gridlines at 25 / 50 / 75 quality
    grid_lines = "\n".join(
        f'<line class="arc-chart__grid" x1="{x_left}" y1="{y_bottom - (pct / 100) * height:.1f}" x2="{x_right}" y2="{y_bottom - (pct / 100) * height:.1f}" />'
        for pct in (25, 50, 75)
    )

    # Era ribbon — coach-regime bands at y_186..y_200 pulled from the profile
    # field `coaching_regimes`. 28% opacity fill, uppercase 9px label at the
    # leftmost edge of each band.
    ribbon_svg = _render_era_ribbon(
        profile, years, x_of_year, ribbon_top, ribbon_bottom, accent,
    )

    # Key annotations — 2..4 per profile (profile field `era_annotations`).
    # Each annotation references a year + a metric lane + a label.
    annotation_svg = _render_era_annotations(
        profile, rows, x_of_year, y_top, y_bottom, height,
    )

    # Year labels at y=205 — '14 '16 ... '24 NOW. Every 2 years in subtle grey,
    # the rightmost label is "NOW" in accent colour with letter-spacing.
    x_labels: list[str] = []
    year_first = years[0]
    year_last = years[-1]
    for i, r in enumerate(rows):
        year = r["season_year"]
        is_last = (i == n - 1)
        if is_last:
            x_labels.append(
                f'<text x="{x_of(i):.1f}" y="{y_year_labels:.1f}" text-anchor="middle" '
                f'class="arc-chart__xlabel arc-chart__xlabel--now">NOW</text>'
            )
            continue
        # every even-year relative to start (keeps a clean '14 '16 '18 '20 '22 '24 progression)
        if (year - year_first) % 2 == 0 or i == 0:
            # Short-form year label — '14, '20, etc.
            short = f"'{str(year)[-2:]}"
            x_labels.append(
                f'<text x="{x_of(i):.1f}" y="{y_year_labels:.1f}" text-anchor="middle" '
                f'class="arc-chart__xlabel">{short}</text>'
            )

    # AP polyline segments
    ap_polylines = ""
    for seg in ap_segments:
        if len(seg) < 2:
            continue
        coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in seg)
        ap_polylines += f'\n      <polyline class="arc-chart__ap" points="{coords}" />'
    # AP dots for each actual rank point
    ap_dots = ""
    for seg in ap_segments:
        for (x, y) in seg:
            ap_dots += f'\n      <circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" class="arc-chart__ap-dot" />'

    # Quality dots colored by brick state
    state_colors = {
        "title-era": "#d97706",
        "peak": "#d97706",
        "winning": accent,
        "current": accent,
        "crisis": "#dc2626",
        "baseline": "#9ca3af",
        "data-gap": "#d1d5db",
        "partial-data": "#d1d5db",
    }
    quality_dots = ""
    for seg in quality_segments:
        for (x, y, r) in seg:
            color = state_colors.get(r["brick_state"], "#6b7280")
            quality_dots += f'\n      <circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}" stroke="#fff" stroke-width="1.5" />'

    return f"""<div class="arc-card__chart-frame">
    <div class="arc-card__chart-header">
      <span class="arc-card__section-eyebrow">TRAJECTORY · quality-score line · AP rank dotted · CFP bids marked · coach regimes ribboned</span>
      <div class="arc-card__legend">
        <span class="arc-card__legend-item arc-card__legend-item--quality" style="--legend-color: {accent};">Program Quality</span>
        <span class="arc-card__legend-item arc-card__legend-item--ap">AP Rank (inverted)</span>
        <span class="arc-card__legend-item arc-card__legend-item--cfp">CFP Appearance</span>
      </div>
    </div>
    <svg class="arc-card__chart" viewBox="0 0 640 210" role="img" aria-label="{html.escape(profile.program_name)} 2014+ trajectory">
      {grid_lines}
      {"".join(cfp_markers)}
      {quality_polylines}
      {ap_polylines}
      {ap_dots}
      {quality_dots}
      {annotation_svg}
      {ribbon_svg}
      {"".join(x_labels)}
    </svg>
  </div>"""


# ------------------------------------------------------------------------
# Brick index
# ------------------------------------------------------------------------

def _render_brick_index(profile: Profile, rows: list[dict[str, Any]]) -> str:
    bricks = []
    for r in rows:
        year = r["season_year"]
        state = r["brick_state"] or "baseline"
        total = (r["wins"] or 0) + (r["losses"] or 0) + (r["ties"] or 0)
        is_partial = _is_partial_row(r)
        if total == 0:
            record = "—"
        elif is_partial:
            # Ingest is incomplete for a past season — don't display a partial
            # mid-season record as if it were the final. Title-era / peak
            # bricks keep their colour; only the record text drops.
            record = "—"
        else:
            record = f"{r['wins']}-{r['losses']}" + (f"-{r['ties']}" if r["ties"] else "")
        # CSS classes — combine brick_state + partial-data modifier when both apply
        cls_list = [f"season-brick--{state}"]
        if is_partial and state != "partial-data":
            cls_list.append("season-brick--is-partial")
        badge = ""
        if r["title_won_flag"]:
            badge = "★"
        elif r["title_game_flag"]:
            badge = "☆"
        elif r["cfp_flag"]:
            badge = "◆"
        href = f"/teams/{profile.slug}/seasons/{year}.html"
        ap_txt = f"AP #{r['ap_rank_final']}" if r["ap_rank_final"] else ""
        if is_partial:
            displayed = f"{r['wins']}-{r['losses']}" + (f"-{r['ties']}" if r["ties"] else "")
            title_attr = f"{year} · partial record on file ({displayed}) · {ap_txt}".strip(" ·")
        else:
            title_attr = f"{year} · {record} · {ap_txt}".strip(" ·")
        cls_attr = " ".join(["season-brick", *cls_list])
        bricks.append(
            f"""<a href="{html.escape(href)}" class="{html.escape(cls_attr)}"
              title="{html.escape(title_attr)}">
            <span class="season-brick__year">'{str(year)[-2:]}</span>
            <span class="season-brick__record">{html.escape(record)}</span>
            <span class="season-brick__badge">{badge}</span>
          </a>"""
        )
    return f"""<section class="arc-card__chapters">
    <span class="arc-card__section-eyebrow">CHAPTERS · {len(rows)} seasons · tap to open the archive</span>
    <div class="arc-card__chapter-grid">
      {''.join(bricks)}
    </div>
  </section>"""


# ------------------------------------------------------------------------
# Closing paragraph + peer footer
# ------------------------------------------------------------------------

def _render_closing(
    profile: Profile,
    rows: list[dict[str, Any]],
    thesis: str | None,
    closing: str | None,
) -> str:
    body = closing
    if not body:
        body = _fallback_closing(profile, rows)
    # Era peer footer
    total_seasons = len(rows)
    total_w = sum(r["wins"] or 0 for r in rows)
    total_l = sum(r["losses"] or 0 for r in rows)
    denom = total_w + total_l
    era_pct = (total_w / denom) if denom else 0.0
    ranked_seasons = sum(1 for r in rows if (r["ap_rank_final"] or 99) <= 25)
    best_ap = min((r["ap_rank_final"] for r in rows if r["ap_rank_final"]), default=None)
    best_ap_str = f"#{best_ap}" if best_ap else "—"
    return f"""<div class="arc-card__closing">
    <p class="arc-card__closing-text">{html.escape(body)}</p>
    <dl class="arc-card__peer-footer">
      <div>
        <dt>ERA WIN %</dt>
        <dd>.{int(era_pct * 1000):03d}</dd>
      </div>
      <div>
        <dt>RANKED SEASONS (AP)</dt>
        <dd>{ranked_seasons}/{total_seasons}</dd>
      </div>
      <div>
        <dt>BEST AP FINISH</dt>
        <dd>{best_ap_str}</dd>
      </div>
    </dl>
  </div>"""


def _fallback_closing(profile: Profile, rows: list[dict[str, Any]]) -> str:
    total_w = sum(r["wins"] or 0 for r in rows)
    total_l = sum(r["losses"] or 0 for r in rows)
    cfp_n = sum(1 for r in rows if r["cfp_flag"])
    titles = sum(1 for r in rows if r["title_won_flag"])
    span = f"{rows[0]['season_year']}–{rows[-1]['season_year']}"
    if titles:
        return (
            f"{profile.program_name}'s {span} record is {total_w}-{total_l} with {cfp_n} CFP appearances "
            f"and {titles} national title{'s' if titles != 1 else ''}. The era closed the program's question of whether "
            f"this program could still reach the room where the sport ends — by being in that room."
        )
    if cfp_n:
        return (
            f"{profile.program_name}'s {span} record is {total_w}-{total_l} with {cfp_n} CFP appearance{'s' if cfp_n != 1 else ''}. "
            f"The era has written the program's modern identity into the CFP field — not always from the inside of a title game, "
            f"but into the room."
        )
    return (
        f"{profile.program_name}'s {span} record is {total_w}-{total_l}. The era is still being written; "
        f"the CFP line is the one the program is arguing for."
    )


# ------------------------------------------------------------------------
# Era ribbon + key annotations (v1.1 polish)
# ------------------------------------------------------------------------

def _render_era_ribbon(
    profile: Profile,
    years: list[int],
    x_of_year,
    y_top: float,
    y_bottom: float,
    accent: str,
) -> str:
    """Coach-regime ribbon at the bottom of the chart.

    Reads `coaching_regimes` from the profile frontmatter. Each entry:
        {coach: str, start_year: int, end_year: int|None (None = ongoing)}

    Each band is a rect with 28% opacity + coach-name label in 9px uppercase.
    The incoming (rightmost, open-ended) regime gets 40% opacity so the ribbon
    visually emphasizes where the era is heading.
    """
    regimes = profile.frontmatter.get("coaching_regimes") or []
    if not regimes:
        return ""
    y_first = years[0]
    y_last = years[-1]
    band_height = y_bottom - y_top
    parts: list[str] = []
    for idx, reg in enumerate(regimes):
        coach = str(reg.get("coach") or "").strip()
        start = int(reg.get("start_year") or y_first)
        end_raw = reg.get("end_year")
        end = int(end_raw) if end_raw is not None else y_last
        # Clamp to visible range
        start_c = max(start, y_first)
        end_c = min(end, y_last)
        if end_c < start_c:
            continue
        x1 = x_of_year(start_c)
        # Expand rightward by half a tick to sit cleanly against the next band
        x2 = x_of_year(end_c)
        if idx < len(regimes) - 1:
            next_start = int(regimes[idx + 1].get("start_year") or end_c)
            if next_start > end_c:
                x2 = x_of_year(next_start) - 0.5
        else:
            # last band (typically ongoing) — extend to the right edge
            x2 = x_of_year(y_last) + 6
        width = max(2.0, x2 - x1)
        is_current_regime = (end_raw is None or end >= y_last)
        opacity = 0.40 if is_current_regime else 0.28
        # Use the program accent for every band (brand anchor); incoming band is brighter
        parts.append(
            f'<rect class="arc-chart__ribbon-band" x="{x1:.1f}" y="{y_top:.1f}" '
            f'width="{width:.1f}" height="{band_height:.1f}" '
            f'fill="{accent}" opacity="{opacity}" />'
        )
        if coach:
            parts.append(
                f'<text x="{x1 + 4:.1f}" y="{y_top + 10:.1f}" '
                f'class="arc-chart__ribbon-label">{html.escape(coach.upper())}</text>'
            )
    return "\n      ".join(parts)


def _render_era_annotations(
    profile: Profile,
    rows: list[dict[str, Any]],
    x_of_year,
    y_top: float,
    y_bottom: float,
    height: float,
) -> str:
    """Editorial annotations tied to a year + quality/ap lane.

    Reads `era_annotations` from the profile frontmatter. Each entry:
        {x_year: int, y_source: "mood"|"ap", label: str, color: "red"|"amber"|"gold"|"navy"}

    Renders a small serif-italic text label near the relevant polyline point,
    with a short leader line from the data point to the label.
    """
    annotations = profile.frontmatter.get("era_annotations") or []
    if not annotations:
        return ""
    # Index rows by year for quick lookup
    by_year: dict[int, dict[str, Any]] = {r["season_year"]: r for r in rows}
    color_hex = {
        "red": "#b91c1c",
        "amber": "#b45309",
        "gold": "#a16207",
        "navy": "#1e3a8a",
    }
    parts: list[str] = []
    for a in annotations:
        try:
            year = int(a.get("x_year"))
        except (TypeError, ValueError):
            continue
        r = by_year.get(year)
        if not r:
            continue
        label = str(a.get("label") or "").strip()
        if not label:
            continue
        source = a.get("y_source") or "mood"
        color = color_hex.get(str(a.get("color") or "amber"), "#b45309")
        cx = x_of_year(year)
        # Anchor y to the metric the annotation points at
        if source == "ap" and r.get("ap_rank_final"):
            ap = int(r["ap_rank_final"])
            anchor_y = y_top + 4 + ((ap - 1) / 24.0) * (height - 10)
        else:
            q = r.get("quality_score")
            if q is None:
                anchor_y = (y_top + y_bottom) / 2
            else:
                anchor_y = y_bottom - (float(q) / 100.0) * height
        # Stagger label positions above/below the anchor based on anchor y
        above = anchor_y > (y_top + y_bottom) / 2
        label_y = (anchor_y - 14) if above else (anchor_y + 16)
        # Keep labels inside the chart gutters
        label_y = max(y_top + 8, min(y_bottom - 4, label_y))
        # Leader line
        parts.append(
            f'<line class="arc-chart__annot-leader" x1="{cx:.1f}" y1="{anchor_y:.1f}" '
            f'x2="{cx:.1f}" y2="{label_y + (2 if above else -4):.1f}" '
            f'stroke="{color}" />'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{label_y:.1f}" text-anchor="middle" '
            f'class="arc-chart__annotation" fill="{color}">'
            f'{html.escape(label)}</text>'
        )
    return "\n      ".join(parts)
