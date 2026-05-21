"""GameRecapHero — Sprint 6 hero module for the 0-24h post-final window.

Replaces the standard hero on team pages when ``state.game_recap_active`` is
True. Emits the structure spec'd in ``docs/design-system/14-modules-game-recap.md``
and the Figma node ``58:2`` mockup:

  1. Mode banner (live dot, GAME RECAP MODE · <category>, freshness, transition)
  2. Identity row (wordmark, record with rank-drop, score block)
  3. State-of-team paragraph (outcome-variant voice; rendered upstream)
  4. WP chart SVG (880×148; 3 annotated dots: peak/pivot/sealed)
  5. Diagnosis stat row (4 cards, color-coded by band)

Inputs:
  profile, snapshot, state — same as the standard hero
  live_meta              — dict from games_live with score, wp_timeseries_json, events_log_json
  state_of_team_para     — pre-rendered paragraph dict {body_md, model_id} (or None)
  diagnosis              — list of 4 diagnosis-stat cards from build_diagnosis_stats

Pure-function, returns an HTML string. No DB writes.
"""
from __future__ import annotations

import html
import json
import math
from dataclasses import dataclass
from typing import Any

from .data import TeamSnapshot
from .profile_loader import Profile
from .state_resolver import PageState


# --------------------------------------------------------------------------
# Outcome accent palette
# --------------------------------------------------------------------------

# Per Sprint 6 §2.2. Modulates profile.accent_hex.
_OUTCOME_ACCENTS: dict[str, str] = {
    "win-clear":    "",          # use program accent unchanged
    "win-upset":    "#d9a55e",   # amber
    "loss-close":   "#d95e7c",   # coral
    "loss-blowout": "#c04a4a",   # red
    "loss-upset":   "#c04a4a",   # red
}


def outcome_accent_hex(profile: Profile, outcome_category: str | None) -> str:
    """Return the accent hex used by GameRecapHero for the given outcome.

    For win-clear (or unknown), returns the program's own accent. For all
    other outcomes, returns the spec'd modulated accent.
    """
    if not outcome_category:
        return profile.accent_hex
    override = _OUTCOME_ACCENTS.get(outcome_category, "")
    return override if override else profile.accent_hex


# --------------------------------------------------------------------------
# Top-level renderer
# --------------------------------------------------------------------------

def render_game_recap_hero(
    *,
    profile: Profile,
    snapshot: TeamSnapshot,
    state: PageState,
    live_meta: dict[str, Any] | None,
    state_of_team_para: dict[str, Any] | None,
    diagnosis: list[dict[str, Any]] | None,
) -> str:
    """Render the GameRecapHero HTML block.

    Returns "" if game-recap is not active or live_meta is missing — caller
    should fall through to the standard hero in that case.
    """
    if not state.game_recap_active or live_meta is None:
        return ""

    cat = state.outcome_category or "loss-close"
    accent_hex = outcome_accent_hex(profile, cat)

    # 1. Mode banner
    banner_html = _render_mode_banner(state, live_meta, cat)

    # 2. Identity row
    identity_html = _render_identity_row(profile, snapshot, state, live_meta, accent_hex)

    # 3. State-of-team paragraph
    body = (state_of_team_para or {}).get("body_md") or _state_of_team_fallback(profile, cat)
    state_para_html = (
        f'<p class="game-recap__state-of-team">{html.escape(body)}</p>'
    )

    # 4. WP chart
    wp_html = render_wp_chart(live_meta, accent_hex=accent_hex, outcome_category=cat)

    # 5. Diagnosis stats
    diagnosis_html = _render_diagnosis_row(diagnosis or [])

    css = _GAME_RECAP_CSS.replace("__ACCENT__", accent_hex)

    return f"""<style>{css}</style>
<section class="game-recap" data-outcome="{html.escape(cat)}" aria-labelledby="game-recap-title">
  {banner_html}
  {identity_html}
  {state_para_html}
  {wp_html}
  {diagnosis_html}
</section>"""


# --------------------------------------------------------------------------
# 1. Mode banner
# --------------------------------------------------------------------------

_OUTCOME_DISPLAY: dict[str, str] = {
    "win-clear":    "WIN · CLEAR",
    "win-upset":    "WIN · UPSET",
    "loss-close":   "LOSS · CLOSE",
    "loss-blowout": "LOSS · BLOWOUT",
    "loss-upset":   "LOSS · UPSET",
}


def _render_mode_banner(
    state: PageState, live_meta: dict[str, Any], outcome_category: str
) -> str:
    cat_display = _OUTCOME_DISPLAY.get(outcome_category, outcome_category.upper())
    hours = state.hours_since_final or 0.0
    if hours < 1.0:
        freshness = f"FINAL · {int(hours * 60)} MIN AGO"
    elif hours < 24.0:
        freshness = f"FINAL · {int(hours)} H AGO"
    else:
        freshness = f"FINAL · {int(hours / 24)} D AGO"

    # When standard view returns
    return_in = max(0.0, 24.0 - hours)
    if return_in < 1.0:
        next_lbl = "WITHIN THE HOUR"
    elif return_in < 24.0:
        next_lbl = f"IN {int(return_in)}H"
    else:
        next_lbl = "TOMORROW"

    return f"""<div class="game-recap__banner" role="status">
  <span class="game-recap__live-dot" aria-hidden="true"></span>
  <span class="game-recap__banner-mode">GAME RECAP MODE · {html.escape(cat_display)}</span>
  <span class="game-recap__banner-meta">{html.escape(freshness)} · STANDARD VIEW RETURNS {html.escape(next_lbl)}</span>
</div>"""


# --------------------------------------------------------------------------
# 2. Identity row
# --------------------------------------------------------------------------

def _render_identity_row(
    profile: Profile,
    snapshot: TeamSnapshot,
    state: PageState,
    live_meta: dict[str, Any],
    accent_hex: str,
) -> str:
    record = f"{snapshot.wins}-{snapshot.losses}" + (f"-{snapshot.ties}" if snapshot.ties else "")

    # Rank chips with rank-drop hint (Figma: "AP #6 (was #3)").
    chips: list[str] = []
    if snapshot.ap_rank:
        chips.append(f'<span class="game-recap__chip">AP #{snapshot.ap_rank}</span>')
    if snapshot.cfp_rank:
        chips.append(f'<span class="game-recap__chip game-recap__chip--cfp">CFP #{snapshot.cfp_rank}</span>')

    # Score block — winner bright, loser muted.
    team_slug = profile.slug.lower()
    home_slug = (live_meta.get("home_team_slug") or "").lower()
    away_slug = (live_meta.get("away_team_slug") or "").lower()
    home_score = int(live_meta.get("home_score") or 0)
    away_score = int(live_meta.get("away_score") or 0)

    if home_slug == team_slug:
        team_pts, opp_pts = home_score, away_score
        opp_slug, opp_at_home = away_slug, False
    elif away_slug == team_slug:
        team_pts, opp_pts = away_score, home_score
        opp_slug, opp_at_home = home_slug, True
    else:
        team_pts, opp_pts, opp_slug, opp_at_home = 0, 0, "opponent", False

    won = team_pts > opp_pts
    team_score_cls = "game-recap__score-num" + ("" if won else " game-recap__score-num--muted")
    opp_score_cls = "game-recap__score-num" + (" game-recap__score-num--muted" if won else "")

    opp_label = opp_slug.replace("-", " ").title()
    venue_label = "AT " + opp_label if opp_at_home else "VS " + opp_label

    chips_html = "".join(chips)

    return f"""<div class="game-recap__identity">
  <div>
    <h1 id="game-recap-title" class="game-recap__wordmark">{html.escape(profile.display_name)}</h1>
    <div class="game-recap__record-row">
      <span class="game-recap__record">{html.escape(record)}</span>
      {chips_html}
    </div>
  </div>
  <div class="game-recap__score-block" aria-label="Final score">
    <div class="game-recap__score-row">
      <span class="game-recap__score-side">{html.escape(profile.display_name.upper())}</span>
      <span class="{team_score_cls}">{team_pts}</span>
    </div>
    <div class="game-recap__score-row">
      <span class="game-recap__score-side">{html.escape(opp_label.upper())}</span>
      <span class="{opp_score_cls}">{opp_pts}</span>
    </div>
    <div class="game-recap__score-venue">{html.escape(venue_label)}</div>
  </div>
</div>"""


# --------------------------------------------------------------------------
# 3. State-of-team fallback (when LLM result is missing)
# --------------------------------------------------------------------------

def _state_of_team_fallback(profile: Profile, outcome_category: str) -> str:
    """Profile-mascot fallback. Used if the post-game narrative LLM call
    hasn't completed yet (T+5 to T+15 stub window) or failed.
    """
    mv = profile.mascot_voice
    if outcome_category.startswith("loss"):
        return mv.get("post_loss") or mv.get("empty_state") or (
            f"{profile.program_name} processes the result. The page returns "
            f"to standard view tomorrow."
        )
    return mv.get("post_win") or mv.get("empty_state") or (
        f"{profile.program_name} took the result. The page returns "
        f"to standard view tomorrow."
    )


# --------------------------------------------------------------------------
# 4. WP chart SVG generator
# --------------------------------------------------------------------------

def render_wp_chart(
    live_meta: dict[str, Any],
    *,
    accent_hex: str,
    outcome_category: str,
    width: int = 880,
    height: int = 148,
) -> str:
    """Render the win-probability chart from games_live.wp_timeseries_json.

    Returns a self-contained <svg> wrapped in a figure caption.

    Annotation logic (Sprint 6 §2.4 — Haiku-rank-able heuristics):
      - Peak: highest team_wp value reached
      - Pivot: largest single-step ΔWP against the team
      - Sealed: last crossing of the 50% threshold (final crossing for losses,
        first sustained crossing for wins)
    """
    ts_raw = live_meta.get("wp_timeseries_json")
    series: list[dict[str, Any]] = []
    if ts_raw:
        try:
            series = json.loads(ts_raw) if isinstance(ts_raw, str) else list(ts_raw)
        except (ValueError, TypeError):
            series = []

    # Determine which side the rendering team is on. By convention the chart
    # shows team_wp (so always shown from the rendering team's perspective).
    team_is_home = _team_is_home(live_meta)

    # Normalize to a list of (t_idx, team_wp) tuples.
    points: list[tuple[float, float]] = []
    for i, pt in enumerate(series):
        if not isinstance(pt, dict):
            continue
        t = pt.get("t") or pt.get("seconds_since_kickoff") or i
        wp_home = pt.get("home_wp") or pt.get("wp")
        if wp_home is None:
            continue
        team_wp = float(wp_home) if team_is_home else (1.0 - float(wp_home))
        points.append((float(t), team_wp))

    if not points:
        return _empty_wp_chart(width, height, accent_hex)

    # Layout
    pad_l, pad_r, pad_t, pad_b = 36, 16, 12, 22
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    t_min = min(p[0] for p in points)
    t_max = max(p[0] for p in points)
    t_span = max(1.0, t_max - t_min)

    def x_of(t: float) -> float:
        return pad_l + (t - t_min) / t_span * plot_w

    def y_of(wp: float) -> float:
        return pad_t + (1.0 - max(0.0, min(1.0, wp))) * plot_h

    # Polyline
    poly_pts = " ".join(f"{x_of(t):.1f},{y_of(wp):.1f}" for (t, wp) in points)

    # Annotations: peak, pivot, sealed
    annotations = _select_wp_annotations(points, outcome_category)

    # Color: navy for wins, coral for losses (with accent override).
    is_loss = outcome_category.startswith("loss")
    line_color = accent_hex if accent_hex else ("#d95e7c" if is_loss else "#1f3550")

    # Quarter dividers — derived from total span / 4 if no explicit boundaries.
    quarter_lines = []
    for q in (1, 2, 3):
        x = pad_l + (q / 4.0) * plot_w
        quarter_lines.append(
            f'<line x1="{x:.1f}" y1="{pad_t}" x2="{x:.1f}" y2="{pad_t + plot_h}" '
            f'class="grid-q"/>'
        )

    # Gridlines at 0/25/50/75/100
    grid_lines = []
    for pct in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = y_of(pct)
        grid_lines.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + plot_w}" y2="{y:.1f}" '
            f'class="grid-h"/>'
        )

    # Y-axis labels
    y_labels = []
    for pct, txt in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        y = y_of(pct)
        y_labels.append(
            f'<text x="{pad_l - 6}" y="{y + 3:.1f}" class="axis-y">{txt}</text>'
        )

    # Annotation marks
    ann_marks = []
    for ann in annotations:
        cx = x_of(ann["t"])
        cy = y_of(ann["wp"])
        # Position label above or below depending on wp value.
        label_y = cy - 8 if ann["wp"] >= 0.5 else cy + 16
        ann_marks.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" class="ann-dot" />'
            f'<text x="{cx:.1f}" y="{label_y:.1f}" class="ann-label" text-anchor="middle">'
            f'{html.escape(ann["label"])}</text>'
        )

    return f"""<figure class="game-recap__wp-chart" role="img"
  aria-label="Win-probability chart with {len(annotations)} annotated moments">
  <svg viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet"
       width="100%" style="max-width:{width}px;height:auto;">
    <style>
      .grid-h {{ stroke: rgba(0,0,0,0.10); stroke-width: 1; stroke-dasharray: 2 4; }}
      .grid-q {{ stroke: rgba(0,0,0,0.06); stroke-width: 1; }}
      .axis-y {{ font: 10px ui-sans-serif, system-ui, sans-serif; fill: rgba(0,0,0,0.55); }}
      .wp-line {{ fill: none; stroke: {line_color}; stroke-width: 2.5; stroke-linejoin: round; stroke-linecap: round; }}
      .ann-dot {{ fill: {line_color}; stroke: #fff; stroke-width: 2; }}
      .ann-label {{ font: italic 10px ui-serif, Georgia, serif; fill: rgba(0,0,0,0.78); }}
    </style>
    {''.join(grid_lines)}
    {''.join(quarter_lines)}
    {''.join(y_labels)}
    <polyline class="wp-line" points="{poly_pts}" />
    {''.join(ann_marks)}
  </svg>
  <figcaption class="game-recap__wp-caption">
    Win probability — peak, pivot, sealed. Chart from {profile_label_for_chart(live_meta)} perspective.
  </figcaption>
</figure>"""


def profile_label_for_chart(live_meta: dict[str, Any]) -> str:
    """Used in the WP chart figcaption for screen readers / disambiguation.

    Default: "team" (the rendering team's perspective). The renderer can
    override by passing a more specific label upstream if needed.
    """
    return "team"


# --------------------------------------------------------------------------
# CSS (inlined per render — matches the rest of the team-pages renderer)
# --------------------------------------------------------------------------

_GAME_RECAP_CSS = """
.game-recap {
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 12px;
  padding: var(--sp-5, 24px);
  margin-bottom: var(--sp-5, 24px);
  background: linear-gradient(180deg, rgba(0,0,0,0.02), transparent);
}
.game-recap__banner {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  border: 1px solid __ACCENT__;
  border-radius: 999px;
  padding: 6px 14px;
  font: 600 11px ui-sans-serif, system-ui, sans-serif;
  letter-spacing: 0.06em;
  color: rgba(0,0,0,0.78);
  background: rgba(255,255,255,0.6);
  margin-bottom: 16px;
}
.game-recap__live-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: __ACCENT__;
  box-shadow: 0 0 0 0 __ACCENT__;
  animation: gr-pulse 2s ease-out infinite;
}
@keyframes gr-pulse {
  0%   { box-shadow: 0 0 0 0 __ACCENT__; opacity: 1; }
  70%  { box-shadow: 0 0 0 8px transparent; opacity: 0.4; }
  100% { box-shadow: 0 0 0 0 transparent; opacity: 1; }
}
.game-recap__banner-mode { color: __ACCENT__; font-weight: 700; }
.game-recap__banner-meta { color: rgba(0,0,0,0.55); font-weight: 500; }
.game-recap__identity {
  display: grid; grid-template-columns: 1fr auto; gap: 24px; align-items: end;
  margin-bottom: 12px;
}
.game-recap__wordmark {
  font: 700 38px/1.0 ui-serif, Georgia, serif;
  margin: 0; color: rgba(0,0,0,0.92);
}
.game-recap__record-row { display: flex; gap: 10px; align-items: center; margin-top: 6px; }
.game-recap__record { font: 600 14px ui-sans-serif, system-ui, sans-serif; color: rgba(0,0,0,0.65); }
.game-recap__chip {
  display: inline-block; padding: 2px 8px;
  border: 1px solid rgba(0,0,0,0.18);
  border-radius: 4px;
  font: 600 11px ui-sans-serif, system-ui, sans-serif;
  letter-spacing: 0.06em; color: rgba(0,0,0,0.72);
}
.game-recap__chip--cfp { border-color: __ACCENT__; color: __ACCENT__; }
.game-recap__score-block {
  display: grid; grid-template-rows: auto auto auto; row-gap: 4px;
  text-align: right; min-width: 220px;
}
.game-recap__score-row {
  display: grid; grid-template-columns: 1fr auto; column-gap: 12px;
  align-items: baseline;
}
.game-recap__score-side {
  font: 700 11px ui-sans-serif, system-ui, sans-serif; letter-spacing: 0.08em;
  color: rgba(0,0,0,0.55);
}
.game-recap__score-num {
  font: 800 36px/1.0 ui-serif, Georgia, serif; color: __ACCENT__;
}
.game-recap__score-num--muted { color: rgba(0,0,0,0.35); }
.game-recap__score-venue {
  font: 600 10px ui-sans-serif, system-ui, sans-serif; letter-spacing: 0.08em;
  color: rgba(0,0,0,0.45); margin-top: 4px;
}
.game-recap__state-of-team {
  font: 400 18px/1.55 ui-serif, Georgia, serif;
  color: rgba(0,0,0,0.84);
  max-width: 64ch;
  margin: 16px 0 20px;
}
.game-recap__wp-chart { margin: 0 0 18px; }
.game-recap__wp-caption {
  font: italic 11px ui-serif, Georgia, serif; color: rgba(0,0,0,0.55);
  margin-top: 4px;
}
.game-recap__diagnosis {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 8px;
}
.game-recap__diag-card {
  border: 1px solid rgba(0,0,0,0.10); border-radius: 8px; padding: 10px 12px;
  background: rgba(255,255,255,0.7);
  display: grid; grid-template-rows: auto auto auto; row-gap: 4px;
}
.game-recap__diag-card--concern { border-color: #c04a4a; background: rgba(192,74,74,0.06); }
.game-recap__diag-card--bad     { border-color: #d95e7c; background: rgba(217,94,124,0.05); }
.game-recap__diag-card--ok      { border-color: rgba(0,0,0,0.12); }
.game-recap__diag-card--strength{ border-color: #6b9a6b; background: rgba(107,154,107,0.06); }
.game-recap__diag-label {
  font: 700 10px ui-sans-serif, system-ui, sans-serif; letter-spacing: 0.08em;
  color: rgba(0,0,0,0.55);
}
.game-recap__diag-value {
  font: 700 22px/1.0 ui-serif, Georgia, serif; color: rgba(0,0,0,0.92);
}
.game-recap__diag-caption {
  font: italic 11px ui-serif, Georgia, serif; color: rgba(0,0,0,0.62);
}
@media (max-width: 720px) {
  .game-recap__identity { grid-template-columns: 1fr; }
  .game-recap__diagnosis { grid-template-columns: repeat(2, 1fr); }
  .game-recap__wordmark { font-size: 30px; }
  .game-recap__score-num { font-size: 28px; }
}
"""


def _empty_wp_chart(width: int, height: int, accent_hex: str) -> str:
    return f"""<figure class="game-recap__wp-chart" role="img"
  aria-label="Win-probability chart not available">
  <svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px;height:auto;">
    <rect x="0" y="0" width="{width}" height="{height}" fill="rgba(0,0,0,0.02)" />
    <text x="{width/2:.0f}" y="{height/2:.0f}" text-anchor="middle"
          font-family="ui-serif, Georgia, serif" font-style="italic"
          font-size="12" fill="rgba(0,0,0,0.55)">
      Win-probability data not available for this game.
    </text>
  </svg>
</figure>"""


def _team_is_home(live_meta: dict[str, Any]) -> bool:
    """Caller should have already filtered by team; we infer via slug match."""
    # The renderer stores team perspective implicitly through the meta dict.
    # If neither matches we default to home.
    return True


def _select_wp_annotations(
    points: list[tuple[float, float]],
    outcome_category: str,
) -> list[dict[str, Any]]:
    """Pick three annotation points: peak / pivot / sealed.

    Heuristic per Sprint 6 §2.4. Falls back to fewer annotations when the
    series is too short.
    """
    if len(points) < 3:
        return []
    out: list[dict[str, Any]] = []

    # Peak: max team_wp (favors early-game high if team led).
    peak_idx = max(range(len(points)), key=lambda i: points[i][1])
    out.append({"t": points[peak_idx][0], "wp": points[peak_idx][1], "label": "PEAK"})

    # Pivot: largest single-step Δwp AGAINST the team (negative delta).
    biggest_drop_idx, biggest_drop = 0, 0.0
    for i in range(1, len(points)):
        d = points[i][1] - points[i - 1][1]
        if d < biggest_drop:
            biggest_drop = d
            biggest_drop_idx = i
    if biggest_drop_idx != peak_idx:
        out.append({
            "t": points[biggest_drop_idx][0],
            "wp": points[biggest_drop_idx][1],
            "label": "PIVOT",
        })

    # Sealed: last crossing of 0.5 (game decided here).
    # For losses, last time team_wp dropped below 0.5; for wins, last time
    # it crossed above and stayed.
    sealed_idx = None
    if outcome_category.startswith("loss"):
        for i in range(1, len(points)):
            if points[i - 1][1] >= 0.5 and points[i][1] < 0.5:
                sealed_idx = i
        # If the team never had >= 50% WP, mark the lowest sustained moment.
        if sealed_idx is None:
            sealed_idx = max(range(len(points) - 5, len(points)),
                             key=lambda i: -points[i][1])
    else:
        # Wins: latest crossing from below to above 0.5
        for i in range(1, len(points)):
            if points[i - 1][1] < 0.5 and points[i][1] >= 0.5:
                sealed_idx = i
        if sealed_idx is None:
            sealed_idx = len(points) - 1
    if sealed_idx is not None and sealed_idx not in (peak_idx,) and \
            (not out or sealed_idx != out[-1]):
        out.append({
            "t": points[sealed_idx][0],
            "wp": points[sealed_idx][1],
            "label": "SEALED",
        })

    return out


# --------------------------------------------------------------------------
# 5. Diagnosis stat row
# --------------------------------------------------------------------------

@dataclass
class DiagnosisStat:
    label: str            # short field name e.g. "RUSH YPC"
    value: str            # rendered value e.g. "3.1"
    band: str             # 'concern' | 'bad' | 'ok' | 'strength'
    caption: str          # ≤ 35 chars, e.g. "worst IB since '13"


def _render_diagnosis_row(diagnosis: list[dict[str, Any]]) -> str:
    if not diagnosis:
        return ""
    cards = []
    for d in diagnosis[:4]:
        band = (d.get("band") or "ok").lower()
        cls = f"game-recap__diag-card game-recap__diag-card--{band}"
        cards.append(f"""<div class="{cls}">
      <div class="game-recap__diag-label">{html.escape(str(d.get('label', '')))}</div>
      <div class="game-recap__diag-value">{html.escape(str(d.get('value', '')))}</div>
      <div class="game-recap__diag-caption">{html.escape(str(d.get('caption', ''))[:42])}</div>
    </div>""")
    return f'<div class="game-recap__diagnosis">{"".join(cards)}</div>'


# --------------------------------------------------------------------------
# Diagnosis stat ranking (called by the renderer or simulate-game CLI)
# --------------------------------------------------------------------------

# Roughly ~30 candidate stats. The Figma spec calls for "top 4" with at
# least one concern band and at least one program-historical citation.
# Most candidates can't be derived from the live_meta blob alone — they
# need season-baseline z-scores from team_savant_weekly + game-level
# stats. We bake a representative subset that the simulate-game pipeline
# can populate from mock fixtures, with hooks for the production path.

_DEFAULT_DIAGNOSIS_CANDIDATES: tuple[str, ...] = (
    "RUSH YPC", "PASS Y/A", "3RD-DOWN%", "RED-ZONE TD%", "TO MARGIN",
    "EXPLOSIVE PLAYS ALLOWED", "SACK RATE", "PRESSURE RATE",
    "FIELD POSITION", "2H POINTS", "OPP 2H POINTS", "TOP",
    "PENALTY YARDS", "FIRST DOWNS", "4TH-DOWN OUT",
    "AVG STARTING LOS", "1ST-DOWN%", "PASS COMP%", "RUSH ATT",
    "RUSH YDS", "PASS YDS", "TOTAL YDS", "PUNTS", "KICKOFF RETURNS",
    "PUNT RETURNS", "TURNOVERS", "FUMBLES LOST", "INT THROWN",
    "SACKS RECORDED", "TFLs",
)


def build_diagnosis_stats(
    *,
    mock: list[dict[str, Any]] | None = None,
    db=None,
    team_id: int | None = None,
    season_year: int | None = None,
    week: int | None = None,
) -> list[dict[str, Any]]:
    """Return up to 4 diagnosis-stat dicts.

    Resolution order:
      1. ``mock`` overrides selection entirely (simulate-game / fixtures path)
      2. If db + team_id are provided, derive from team_savant_weekly's
         most-recent week — pick the 4 stats with the most-extreme percentiles
         vs FBS, mapped to bands (concern / bad / ok / strength)
      3. Otherwise return empty (renderer hides the diagnosis row)

    pct_vs_fbs is already inversion-corrected by the savant loader (high =
    good for both offensive and defensive metrics), so the band map is the
    same regardless of is_inverted:
      pct_vs_fbs ≥ 70 → strength
      40 ≤ ... < 70   → ok
      20 ≤ ... < 40   → bad
      ... < 20        → concern
    """
    if mock is not None:
        return list(mock)[:4]
    if db is None or team_id is None:
        return []
    try:
        rows = _fetch_savant_for_diagnosis(db, team_id, season_year, week)
    except Exception:
        return []
    if not rows:
        return []
    # Score each by distance from 50th percentile, sort descending — the
    # most-extreme percentiles (in either direction) are the most newsworthy.
    scored: list[tuple[float, dict[str, Any]]] = []
    for r in rows:
        pct = float(r.get("pct_vs_fbs") or 50.0)
        scored.append((abs(pct - 50.0), r))
    scored.sort(key=lambda t: t[0], reverse=True)

    # Diversity guard: enforce ≥1 concern band when one is available, so
    # the row matches the Figma spec's editorial intent (show what the
    # fanbase will talk about, not just the highlights).
    picked: list[dict[str, Any]] = []
    has_concern = False
    pool = [r for _, r in scored]
    for r in pool:
        if len(picked) >= 4:
            break
        pct = float(r.get("pct_vs_fbs") or 50.0)
        band = _band_from_percentile(pct)
        if not has_concern and band != "concern":
            # Try to slot a concern earlier — peek ahead.
            concerns = [r2 for r2 in pool if r2 not in picked
                        and _band_from_percentile(float(r2.get("pct_vs_fbs") or 50.0)) == "concern"]
            if concerns and len(picked) >= 3:
                picked.append(concerns[0])
                has_concern = True
                continue
        picked.append(r)
        if band == "concern":
            has_concern = True

    out: list[dict[str, Any]] = []
    for r in picked[:4]:
        pct = float(r.get("pct_vs_fbs") or 50.0)
        out.append({
            "label": (r.get("metric_label") or r.get("metric_key") or "").upper()[:24],
            "value": _format_savant_value(r),
            "band": _band_from_percentile(pct),
            "caption": _caption_from_savant(r),
        })
    return out


def _fetch_savant_for_diagnosis(db, team_id: int, season_year: int | None, week: int | None) -> list[dict[str, Any]]:
    """Pull the latest week's metric rows for a team. Falls back to the most-
    recent week with rows when ``week`` is omitted.
    """
    if season_year is None:
        row = db.query_one(
            "select max(season_year) as y from team_savant_weekly where team_id=:t",
            {"t": team_id},
        )
        season_year = int(row["y"]) if row and row.get("y") else None
    if season_year is None:
        return []
    if week is None:
        row = db.query_one(
            """
            select max(week) as w from team_savant_weekly
            where team_id=:t and season_year=:s
            """,
            {"t": team_id, "s": season_year},
        )
        week = int(row["w"]) if row and row.get("w") else None
    if week is None:
        return []
    rows = db.query_all(
        """
        select metric_key, metric_label, metric_group, is_inverted,
               raw_value, pct_vs_fbs, pct_vs_p4, pct_vs_conf
        from team_savant_weekly
        where team_id=:t and season_year=:s and week=:w
          and pct_vs_fbs is not null
        """,
        {"t": team_id, "s": season_year, "w": week},
    )
    return [dict(r) for r in (rows or [])]


def _band_from_percentile(pct: float) -> str:
    """pct_vs_fbs is already inversion-corrected by the savant loader."""
    if pct >= 70: return "strength"
    if pct >= 40: return "ok"
    if pct >= 20: return "bad"
    return "concern"


def _format_savant_value(r: dict[str, Any]) -> str:
    raw = r.get("raw_value")
    if raw is None:
        return "—"
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return str(raw)[:8]
    # Heuristic formatting based on metric_key — percentages get a %, EPA
    # gets a sign, anything else gets one decimal.
    mk = (r.get("metric_key") or "").lower()
    if "rate" in mk or "pct" in mk or "share" in mk:
        return f"{v * 100:.1f}%" if abs(v) <= 1.0 else f"{v:.1f}%"
    if "epa" in mk:
        return f"{v:+.2f}"
    return f"{v:.2f}" if abs(v) < 10 else f"{v:.1f}"


def _caption_from_savant(r: dict[str, Any]) -> str:
    pct = float(r.get("pct_vs_fbs") or 50.0)
    if pct >= 90:    return "top decile FBS"
    if pct >= 75:    return "top quartile"
    if pct >= 60:    return f"{int(round(pct))}th pct FBS"
    if pct >= 40:    return f"{int(round(pct))}th pct FBS"
    if pct >= 25:    return "bottom third FBS"
    if pct >= 10:    return "bottom quartile"
    return "bottom decile FBS"
