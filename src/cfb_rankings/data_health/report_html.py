"""Render the gate + CheckResults to a single self-contained INTERNAL HTML page.

This is an *operator dashboard*, NOT a deployed site surface — it must NEVER be
written under ``output/site``. It complements ``report.py`` (JSON + console): the
JSON/console is the canonical, diffable, CI-facing surface; this page is a quick
human read for the infra-beginner owner (a colored gate banner, pillar bars, a
season x dataset coverage heatmap, the flagged-assertions table, and the
source-feed health counts).

Contract consumed (do not widen — keep this a pure renderer):
  * gate     dict {overall, passrates, counts, summary} from ``gate.compute_gate``.
  * results  list of ``CheckResult`` (attribute access: check_id, pillar, dataset,
             season, status, severity, detail, evidence_sql).

Stdlib only; no JS framework, no external assets — a single string of HTML with
inline CSS so it renders from ``file://`` with no network. Numbers use a
monospace stack + tabular figures so columns line up.
"""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone

# The coverage-heatmap column range. Lower bound is the audit's expected floor
# (2014); upper bound is one past CURRENT_SEASON so the in-progress + next season
# render as columns too. Kept local (not imported) so this renderer stays a pure
# presentation layer with no coupling to the calendar regime tables.
_HEATMAP_MIN_YEAR = 2014
_HEATMAP_MAX_YEAR = 2026

# status -> (cell background, readable foreground). 'grey' is the not-evaluated /
# out-of-range default (a season a dataset never declared).
_STATUS_COLORS: dict[str, tuple[str, str]] = {
    "pass": ("#1f7a3d", "#eafff0"),     # green
    "fail": ("#a32020", "#ffecec"),     # red
    "unknown": ("#9a7b1f", "#fff6da"),  # yellow/amber
    "grey": ("#2a2f37", "#6b7280"),     # not-applicable / out of range
}

# overall gate -> banner color.
_GATE_COLORS: dict[str, str] = {
    "GREEN": "#1f7a3d",
    "YELLOW": "#9a7b1f",
    "RED": "#a32020",
    "UNKNOWN": "#54606e",
}

_SEVERITY_COLORS: dict[str, str] = {
    "critical": "#ff6b6b",
    "warning": "#ffcf5c",
    "info": "#7fb2ff",
}


def _esc(value) -> str:
    """HTML-escape any value (None -> '')."""
    return html.escape("" if value is None else str(value))


def _pct(fraction: float) -> str:
    try:
        return f"{float(fraction) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _bar_color(fraction: float) -> str:
    """Pass-rate bar color: green >= 0.9, amber >= 0.6, else red."""
    try:
        f = float(fraction)
    except (TypeError, ValueError):
        return _GATE_COLORS["UNKNOWN"]
    if f >= 0.9:
        return _STATUS_COLORS["pass"][0]
    if f >= 0.6:
        return _STATUS_COLORS["unknown"][0]
    return _STATUS_COLORS["fail"][0]


# === sections ============================================================


def _render_banner(gate: dict) -> str:
    overall = str(gate.get("overall", "UNKNOWN")).upper()
    color = _GATE_COLORS.get(overall, _GATE_COLORS["UNKNOWN"])
    summary = _esc(gate.get("summary", ""))
    counts = gate.get("counts", {}) or {}
    sub = (
        f"total={counts.get('total', 0)} &middot; "
        f"pass={counts.get('pass', 0)} &middot; "
        f"fail={counts.get('fail', 0)} &middot; "
        f"unknown={counts.get('unknown', 0)} &middot; "
        f"critical_fail={counts.get('critical_fail', 0)} &middot; "
        f"critical_unknown={counts.get('critical_unknown', 0)}"
    )
    return (
        f'<div class="banner" style="background:{color}">'
        f'<div class="banner-state">DATA HEALTH GATE: {_esc(overall)}</div>'
        f'<div class="banner-summary">{summary}</div>'
        f'<div class="banner-counts num">{sub}</div>'
        f"</div>"
    )


def _render_pillars(gate: dict) -> str:
    passrates = gate.get("passrates", {}) or {}
    by_pillar = (gate.get("counts", {}) or {}).get("by_pillar", {}) or {}
    if not passrates:
        return (
            '<section class="card"><h2>Pillar pass-rates</h2>'
            '<p class="muted">(no pillars registered)</p></section>'
        )
    rows: list[str] = []
    for pillar in sorted(passrates):
        frac = passrates[pillar]
        width = max(0.0, min(1.0, float(frac) if frac is not None else 0.0)) * 100
        color = _bar_color(frac)
        b = by_pillar.get(pillar, {}) or {}
        tally = (
            f"{b.get('pass', 0)}/{b.get('total', 0)} pass"
            + (f", {b['fail']} fail" if b.get("fail") else "")
            + (f", {b['unknown']} unknown" if b.get("unknown") else "")
        )
        rows.append(
            '<div class="pillar-row">'
            f'<div class="pillar-name">{_esc(pillar)}</div>'
            '<div class="pillar-track">'
            f'<div class="pillar-fill" style="width:{width:.1f}%;background:{color}"></div>'
            "</div>"
            f'<div class="pillar-pct num">{_pct(frac)}</div>'
            f'<div class="pillar-tally num muted">{_esc(tally)}</div>'
            "</div>"
        )
    return (
        '<section class="card"><h2>Pillar pass-rates</h2>'
        f'<div class="pillars">{"".join(rows)}</div></section>'
    )


def _heatmap_status(results) -> dict[tuple[str, int], str]:
    """Build {(dataset, season): status} from the completeness pillar.

    A dataset can emit several rows for one (dataset, season) only in pathological
    cases; we collapse with a worst-wins precedence (fail > unknown > pass) so a
    cell never under-reports a gap.
    """
    precedence = {"pass": 0, "unknown": 1, "fail": 2}
    grid: dict[tuple[str, int], str] = {}
    for r in results:
        if getattr(r, "pillar", None) != "completeness":
            continue
        season = getattr(r, "season", None)
        if season is None:
            continue
        try:
            season = int(season)
        except (TypeError, ValueError):
            continue
        status = getattr(r, "status", "unknown")
        key = (getattr(r, "dataset", "-"), season)
        if key not in grid or precedence.get(status, 1) > precedence.get(grid[key], 1):
            grid[key] = status
    return grid


def _render_heatmap(results) -> str:
    grid = _heatmap_status(results)
    if not grid:
        return (
            '<section class="card"><h2>Season &times; dataset coverage</h2>'
            '<p class="muted">no completeness results to chart.</p></section>'
        )

    # Datasets in first-seen order (spine then offseason, matching contract order).
    datasets: list[str] = []
    seen: set[str] = set()
    for r in results:
        if getattr(r, "pillar", None) != "completeness":
            continue
        ds = getattr(r, "dataset", "-")
        if ds not in seen:
            seen.add(ds)
            datasets.append(ds)

    years = list(range(_HEATMAP_MIN_YEAR, _HEATMAP_MAX_YEAR + 1))

    head_cells = "".join(
        f'<th class="num year">{y}</th>' for y in years
    )
    body_rows: list[str] = []
    for ds in datasets:
        cells: list[str] = []
        for y in years:
            status = grid.get((ds, y))
            key = status if status in _STATUS_COLORS else "grey"
            bg, fg = _STATUS_COLORS[key]
            glyph = {"pass": "OK", "fail": "X", "unknown": "?"}.get(status or "", "")
            title = (
                f"{ds} {y}: {status}" if status else f"{ds} {y}: not in contract"
            )
            cells.append(
                f'<td class="cell num" style="background:{bg};color:{fg}" '
                f'title="{_esc(title)}">{glyph}</td>'
            )
        body_rows.append(
            f'<tr><th class="rowhead">{_esc(ds)}</th>{"".join(cells)}</tr>'
        )

    legend = (
        '<div class="legend">'
        f'<span class="chip" style="background:{_STATUS_COLORS["pass"][0]}">OK present / regime-ok</span>'
        f'<span class="chip" style="background:{_STATUS_COLORS["unknown"][0]}">? unknown / acknowledged</span>'
        f'<span class="chip" style="background:{_STATUS_COLORS["fail"][0]}">X missing / sparse</span>'
        f'<span class="chip" style="background:{_STATUS_COLORS["grey"][0]};color:#6b7280">&nbsp; not in contract</span>'
        "</div>"
    )
    return (
        '<section class="card"><h2>Season &times; dataset coverage</h2>'
        f"{legend}"
        '<div class="heatmap-wrap"><table class="heatmap">'
        f'<thead><tr><th class="rowhead">dataset</th>{head_cells}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        "</table></div></section>"
    )


def _render_flagged(results) -> str:
    flagged = [
        r for r in results if getattr(r, "status", None) in ("fail", "unknown")
    ]
    # Worst first: critical fails, then warning fails, then unknowns; stable by id.
    sev_order = {"critical": 0, "warning": 1, "info": 2}
    status_order = {"fail": 0, "unknown": 1}
    flagged.sort(
        key=lambda r: (
            status_order.get(getattr(r, "status", ""), 9),
            sev_order.get(getattr(r, "severity", ""), 9),
            getattr(r, "check_id", ""),
        )
    )
    if not flagged:
        return (
            '<section class="card"><h2>Flagged assertions</h2>'
            '<p class="muted">none — every evaluated check passed.</p></section>'
        )

    rows: list[str] = []
    for r in flagged:
        status = getattr(r, "status", "")
        severity = getattr(r, "severity", "")
        sev_color = _SEVERITY_COLORS.get(severity, "#9aa3ad")
        st_bg = _STATUS_COLORS.get(status, _STATUS_COLORS["grey"])[0]
        season = getattr(r, "season", None)
        rows.append(
            "<tr>"
            f'<td><span class="pill" style="background:{st_bg}">{_esc(status.upper())}</span></td>'
            f'<td><span class="pill" style="background:{sev_color};color:#1a1d22">{_esc(severity)}</span></td>'
            f'<td class="mono">{_esc(getattr(r, "dataset", "-"))}</td>'
            f'<td class="num">{_esc("" if season is None else season)}</td>'
            f'<td class="mono small">{_esc(getattr(r, "check_id", ""))}</td>'
            f'<td>{_esc(getattr(r, "detail", ""))}</td>'
            "</tr>"
        )
    return (
        f'<section class="card"><h2>Flagged assertions ({len(flagged)})</h2>'
        '<div class="table-wrap"><table class="flagged">'
        "<thead><tr>"
        "<th>status</th><th>severity</th><th>dataset</th><th>season</th>"
        "<th>check_id</th><th>detail</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table></div></section>"
    )


def _render_source_feeds(results) -> str:
    """Source-feed health counts from the freshness pillar.

    Reads the structured per-class CheckResults + the ``freshness.inventory.overall``
    summary. The overall counts (instances / unhealthy / error / empty / overdue /
    unclassified) are parsed from the summary detail string the freshness pillar
    emits (kept resilient: any token it cannot find is shown as '—').
    """
    overall = None
    classes = []
    for r in results:
        if getattr(r, "pillar", None) != "freshness":
            continue
        cid = getattr(r, "check_id", "")
        if cid == "freshness.inventory.overall":
            overall = r
        elif cid.startswith("freshness.source_class."):
            classes.append(r)

    if overall is None and not classes:
        return (
            '<section class="card"><h2>Source-feed health</h2>'
            '<p class="muted">freshness pillar produced no source inventory.</p></section>'
        )

    summary_html = ""
    if overall is not None:
        nums = _parse_overall_feed_counts(getattr(overall, "detail", ""))
        tiles = [
            ("instances", nums.get("instances")),
            ("healthy", nums.get("healthy")),
            ("unhealthy", nums.get("unhealthy")),
            ("error", nums.get("error")),
            ("empty", nums.get("empty")),
            ("overdue", nums.get("overdue")),
            ("unclassified", nums.get("unclassified")),
        ]
        tile_html = "".join(
            '<div class="tile">'
            f'<div class="tile-num num">{("—" if v is None else v)}</div>'
            f'<div class="tile-label">{_esc(label)}</div>'
            "</div>"
            for label, v in tiles
        )
        summary_html = (
            f'<div class="tiles">{tile_html}</div>'
            f'<p class="muted small">{_esc(getattr(overall, "detail", ""))}</p>'
        )

    # Per-class rows: only show the unhealthy / unknown classes (the actionable ones),
    # worst first, to keep the panel readable. A healthy fleet collapses to a note.
    flagged_classes = [
        c for c in classes if getattr(c, "status", "pass") in ("fail", "unknown")
    ]
    flagged_classes.sort(key=lambda c: getattr(c, "dataset", ""))
    class_html = ""
    if flagged_classes:
        rows = "".join(
            "<tr>"
            f'<td><span class="pill" style="background:'
            f'{_STATUS_COLORS.get(getattr(c, "status", "grey"), _STATUS_COLORS["grey"])[0]}">'
            f'{_esc(getattr(c, "status", "").upper())}</span></td>'
            f'<td class="mono">{_esc(getattr(c, "dataset", "-"))}</td>'
            f'<td>{_esc(getattr(c, "detail", ""))}</td>'
            "</tr>"
            for c in flagged_classes
        )
        class_html = (
            f'<h3 class="subhead">Unhealthy source classes ({len(flagged_classes)})</h3>'
            '<div class="table-wrap"><table class="flagged">'
            "<thead><tr><th>status</th><th>class</th><th>detail</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></div>"
        )
    elif classes:
        class_html = '<p class="muted">all classified source feeds healthy.</p>'

    return (
        '<section class="card"><h2>Source-feed health</h2>'
        f"{summary_html}{class_html}</section>"
    )


def _parse_overall_feed_counts(detail: str) -> dict[str, int]:
    """Pull the headline feed counts out of the freshness overall detail string.

    The freshness pillar emits e.g.:
      "443 source instances reconciled vs 79 registry classes: 193 unhealthy
       (176 error + 16 empty + 1 overdue), 250 healthy; 180 unclassified."
    We parse defensively with light regex; a missing token is simply omitted.
    """
    out: dict[str, int] = {}
    text = detail or ""
    patterns = {
        "instances": r"(\d+)\s+source instances",
        "unhealthy": r"(\d+)\s+unhealthy",
        "error": r"(\d+)\s+error",
        "empty": r"(\d+)\s+empty",
        "overdue": r"(\d+)\s+overdue",
        "healthy": r"(\d+)\s+healthy",
        "unclassified": r"(\d+)\s+unclassified",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text)
        if m:
            try:
                out[key] = int(m.group(1))
            except ValueError:
                pass
    return out


# === page ================================================================

_CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 24px;
  background: #14171c; color: #d6dce4;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 14px; line-height: 1.45;
}
.num, .mono { font-family: "SF Mono", "Cascadia Mono", Consolas, "Roboto Mono", monospace; font-variant-numeric: tabular-nums; }
.small { font-size: 12px; }
.muted { color: #8b95a3; }
h1 { font-size: 20px; margin: 0 0 4px; letter-spacing: .5px; }
h2 { font-size: 15px; margin: 0 0 12px; color: #aeb8c6; text-transform: uppercase; letter-spacing: 1px; }
h3.subhead { font-size: 13px; margin: 16px 0 8px; color: #aeb8c6; }
.meta { color: #6b7686; margin: 0 0 20px; font-size: 12px; }
.banner {
  border-radius: 10px; padding: 18px 22px; margin-bottom: 20px;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.08);
}
.banner-state { font-size: 26px; font-weight: 800; letter-spacing: 1px; color: #fff; }
.banner-summary { margin-top: 6px; color: rgba(255,255,255,.92); }
.banner-counts { margin-top: 8px; color: rgba(255,255,255,.82); font-size: 13px; }
.card {
  background: #1b1f26; border: 1px solid #262b34; border-radius: 10px;
  padding: 18px 20px; margin-bottom: 18px;
}
.pillars { display: flex; flex-direction: column; gap: 10px; }
.pillar-row { display: grid; grid-template-columns: 150px 1fr 64px 200px; align-items: center; gap: 12px; }
.pillar-name { font-weight: 600; }
.pillar-track { background: #11141a; border-radius: 6px; height: 16px; overflow: hidden; border: 1px solid #262b34; }
.pillar-fill { height: 100%; border-radius: 6px 0 0 6px; }
.pillar-pct { text-align: right; }
.pillar-tally { font-size: 12px; }
.legend { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.chip { font-size: 11px; padding: 3px 8px; border-radius: 5px; color: #fff; }
.heatmap-wrap, .table-wrap { overflow-x: auto; }
table.heatmap { border-collapse: collapse; font-size: 12px; }
table.heatmap th.year { padding: 4px 6px; color: #8b95a3; text-align: center; min-width: 34px; }
table.heatmap th.rowhead { text-align: left; padding: 4px 12px 4px 4px; color: #cdd5df; white-space: nowrap; position: sticky; left: 0; background: #1b1f26; }
table.heatmap td.cell { text-align: center; padding: 5px 6px; min-width: 34px; font-weight: 700; font-size: 11px; border: 1px solid #14171c; }
table.flagged { border-collapse: collapse; width: 100%; font-size: 12.5px; }
table.flagged th { text-align: left; padding: 6px 10px; color: #8b95a3; border-bottom: 1px solid #2c323c; font-weight: 600; }
table.flagged td { padding: 6px 10px; border-bottom: 1px solid #21262e; vertical-align: top; }
.pill { display: inline-block; padding: 1px 7px; border-radius: 5px; font-size: 11px; font-weight: 700; color: #fff; }
.tiles { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 8px; }
.tile { background: #11141a; border: 1px solid #262b34; border-radius: 8px; padding: 10px 16px; min-width: 92px; text-align: center; }
.tile-num { font-size: 22px; font-weight: 800; color: #eef2f7; }
.tile-label { font-size: 11px; color: #8b95a3; text-transform: uppercase; letter-spacing: .5px; margin-top: 2px; }
"""


def render_html(gate, results) -> str:
    """Return a complete, self-contained internal HTML dashboard string.

    Args:
      gate     the dict from ``gate.compute_gate`` ({overall, passrates, counts, summary}).
      results  the list of ``CheckResult`` rows (attribute access).

    Never writes anything; the caller owns the destination path (and must keep it
    OUT of ``output/site`` — this is an internal operator view, not a site page).
    """
    results = list(results)
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")

    body = (
        _render_banner(gate)
        + _render_pillars(gate)
        + _render_heatmap(results)
        + _render_source_feeds(results)
        + _render_flagged(results)
    )

    return (
        "<!DOCTYPE html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>CFB Index — Data Health Dashboard</title>"
        f"<style>{_CSS}</style></head><body>"
        "<h1>CFB Index &mdash; Data Health Dashboard</h1>"
        f'<p class="meta num">generated {_esc(generated)} &middot; '
        "internal operator view (not deployed)</p>"
        f"{body}"
        "</body></html>"
    )
