"""Scenario Explorer / Season Pace — Brief §4 + Wave 16.

Per-game pace + projected full-season totals for a player's primary
metric. Position-aware: QB tracks pass yards, RB rush yards, WR rec
yards, DEF tackles. Shows three rows:

  • Current (N games)        — actual totals through last game
  • Per-game pace            — totals / games
  • Projected full-season    — pace × 13 (median FBS regular season)

Where the season is finished (no more games to project), the
"Projected" row matches "Current". Where the season is in progress,
the projection is the simple linear extrapolation.

Public API:
    render_scenario_explorer(db, player_id, season_year, position) -> str
    SCENARIO_EXPLORER_CSS                                          -> str
"""
from __future__ import annotations

from html import escape
from typing import Any


SCENARIO_EXPLORER_CSS = """
/* Scenario Explorer / Season Pace */
.scenario-explorer-v2 {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.scenario-explorer-v2__head {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 12px; margin-bottom: 12px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
}
.scenario-explorer-v2__eyebrow {
  font-size: 0.72rem; letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55)); margin: 0;
}
.scenario-explorer-v2__title {
  font-size: 1.05rem; font-weight: 600; margin: 0;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.scenario-explorer-v2__rows {
  display: grid; gap: 8px;
}
.scenario-explorer-v2__row {
  display: grid; grid-template-columns: 9rem 1fr;
  gap: 12px; align-items: baseline;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.scenario-explorer-v2__row:last-child { border-bottom: 0; }
.scenario-explorer-v2__row-label {
  font-size: 0.74rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55));
}
.scenario-explorer-v2__row-values {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(85px, 1fr));
  gap: 12px;
}
.scenario-explorer-v2__row-value {
  font-size: 1.0rem; font-weight: 600;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.scenario-explorer-v2__row-sub {
  display: block;
  font-size: 0.66rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.5));
  font-weight: 500;
  margin-top: 2px;
}
.scenario-explorer-v2__row--pace .scenario-explorer-v2__row-value {
  color: var(--accolade-gold-base, #d1a23a);
}
.scenario-explorer-v2__lede {
  font-size: 0.86rem; line-height: 1.45;
  color: var(--text-soft, rgba(255,255,255,0.80));
  margin: 0 0 10px 0;
}
.scenario-explorer-v2__milestones {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
}
.scenario-explorer-v2__milestone-line {
  font-size: 0.78rem;
  color: var(--text-soft, rgba(255,255,255,0.72));
  margin: 4px 0;
}
.scenario-explorer-v2__milestone-line strong {
  color: var(--accolade-gold-base, #d1a23a);
}
.scenario-explorer-v2--empty {
  color: var(--text-quiet, rgba(255,255,255,0.55));
  font-style: italic;
  padding: 14px;
}
"""


# Per-position primary metric specs.
# (label, columns: [(col_label, category, stat_type)], milestones for "to hit X")
_QB_SPEC = {
    "label": "passing",
    "cols": [
        ("Pass yards", "passing", "YDS"),
        ("Pass TDs",   "passing", "TD"),
        ("INT",        "passing", "INT"),
    ],
    "milestones": [
        ("3,000-yard season", "passing.YDS", 3000),
        ("4,000-yard season", "passing.YDS", 4000),
        ("25 passing TDs",    "passing.TD",  25),
        ("30 passing TDs",    "passing.TD",  30),
        ("35 passing TDs",    "passing.TD",  35),
    ],
}
_RB_SPEC = {
    "label": "rushing",
    "cols": [
        ("Rush yards", "rushing", "YDS"),
        ("Carries",    "rushing", "CAR"),
        ("Rush TDs",   "rushing", "TD"),
    ],
    "milestones": [
        ("750-yard season",   "rushing.YDS", 750),
        ("1,000-yard season", "rushing.YDS", 1000),
        ("1,500-yard season", "rushing.YDS", 1500),
        ("10 rushing TDs",    "rushing.TD",  10),
        ("15 rushing TDs",    "rushing.TD",  15),
        ("20 rushing TDs",    "rushing.TD",  20),
    ],
}
_WR_SPEC = {
    "label": "receiving",
    "cols": [
        ("Rec yards", "receiving", "YDS"),
        ("Receptions","receiving", "REC"),
        ("Rec TDs",   "receiving", "TD"),
    ],
    "milestones": [
        ("700-yard receiver",   "receiving.YDS", 700),
        ("1,000-yard receiver", "receiving.YDS", 1000),
        ("60-catch season",     "receiving.REC", 60),
        ("80-catch season",     "receiving.REC", 80),
        ("8 receiving TDs",     "receiving.TD",  8),
        ("10 receiving TDs",    "receiving.TD",  10),
    ],
}
_DEF_SPEC = {
    "label": "defensive",
    "cols": [
        ("Tackles",        "defensive", "TOT"),
        ("Tackles for loss","defensive","TFL"),
        ("Sacks",          "defensive", "SACKS"),
    ],
    "milestones": [
        ("80-tackle season",  "defensive.TOT",   80),
        ("100-tackle season", "defensive.TOT",   100),
        ("6-sack season",     "defensive.SACKS", 6),
        ("10-sack season",    "defensive.SACKS", 10),
    ],
}


def _spec_for_position(position: str) -> dict[str, Any] | None:
    pos = (position or "").upper().strip()
    if pos == "QB":
        return _QB_SPEC
    if pos in {"RB", "TB", "FB", "HB"}:
        return _RB_SPEC
    if pos in {"WR", "TE"}:
        return _WR_SPEC
    if pos in {"CB", "S", "DB", "LB", "ILB", "OLB", "MLB",
               "DL", "DE", "DT", "NT", "EDGE"}:
        return _DEF_SPEC
    return None


def _fetch_season_totals(
    db, player_id: int, season_year: int, cols: list[tuple],
) -> tuple[dict[str, float], int]:
    """Return ({col_key: total}, games_played)."""
    rows = db.query_all(
        """
        select pgs.game_id, pgs.category, pgs.stat_type, pgs.stat_value_num
          from player_game_stats pgs
         where pgs.player_id = :pid
           and pgs.season_year = :s
           and pgs.stat_value_num is not null
        """,
        {"pid": player_id, "s": season_year},
    )
    totals: dict[str, float] = {}
    games: set[int] = set()
    for r in rows:
        gid = int(r["game_id"]) if r.get("game_id") is not None else 0
        if gid:
            games.add(gid)
        for _, cat, stype in cols:
            if r["category"] == cat and r["stat_type"] == stype:
                key = f"{cat}.{stype}"
                totals[key] = totals.get(key, 0.0) + float(r["stat_value_num"] or 0)
    return (totals, len(games))


def _fmt_num(v: float, stype: str) -> str:
    if v >= 1000:
        return f"{int(round(v)):,}"
    if stype in {"TD", "INT", "CAR", "REC", "TOT", "PD"}:
        return f"{int(round(v))}"
    if abs(v - int(v)) < 0.05:
        return f"{int(round(v))}"
    return f"{v:.1f}"


def render_scenario_explorer(
    db, player_id: int | None, season_year: int | None,
    position: str | None = None,
) -> str:
    if db is None or player_id is None or season_year is None:
        return ""
    spec = _spec_for_position(position or "")
    if spec is None:
        return ""

    cols = spec["cols"]
    totals, games = _fetch_season_totals(
        db, int(player_id), int(season_year), cols,
    )
    if games < 2:
        return ""

    projected_to_games = 13  # median FBS reg season; ceiling for projection
    will_project = games < projected_to_games
    remaining = max(0, projected_to_games - games)

    # Per-game pace + projected
    pace: dict[str, float] = {}
    projected: dict[str, float] = {}
    for _, cat, stype in cols:
        key = f"{cat}.{stype}"
        total = totals.get(key, 0.0)
        p = total / games if games else 0.0
        pace[key] = p
        projected[key] = p * projected_to_games if will_project else total

    def _row(label: str, getter, mod_class: str = "") -> str:
        cells: list[str] = []
        for col_label, cat, stype in cols:
            key = f"{cat}.{stype}"
            v = getter(key)
            cells.append(
                '<div>'
                f'<span class="scenario-explorer-v2__row-value">{_fmt_num(v, stype)}</span>'
                f'<span class="scenario-explorer-v2__row-sub">{escape(col_label)}</span>'
                '</div>'
            )
        return (
            f'<div class="scenario-explorer-v2__row{mod_class}">'
            f'<span class="scenario-explorer-v2__row-label">{escape(label)}</span>'
            f'<div class="scenario-explorer-v2__row-values">{"".join(cells)}</div>'
            '</div>'
        )

    rows_html = (
        _row(f"Through {games}g", lambda k: totals.get(k, 0.0)) +
        _row("Per game", lambda k: pace.get(k, 0.0),
             mod_class=" scenario-explorer-v2__row--pace") +
        _row(f"Projected ({projected_to_games}g)" if will_project else "Final",
             lambda k: projected.get(k, 0.0))
    )

    # Milestone lines — "to hit X you need Y/game"
    milestone_lines: list[str] = []
    for label, metric_key, threshold in spec.get("milestones", []):
        achieved = totals.get(metric_key, 0.0)
        if achieved >= threshold:
            milestone_lines.append(
                f'<p class="scenario-explorer-v2__milestone-line">'
                f'<strong>✓ Hit {label}</strong> &middot; '
                f'finished with {_fmt_num(achieved, "")}.'
                f'</p>'
            )
        elif will_project and remaining > 0:
            needed = threshold - achieved
            needed_per_game = needed / remaining
            milestone_lines.append(
                f'<p class="scenario-explorer-v2__milestone-line">'
                f'To hit <strong>{escape(label)}</strong> '
                f'(currently {_fmt_num(achieved, "")}): '
                f'needs {_fmt_num(needed_per_game, "")}/game over remaining {remaining}.'
                f'</p>'
            )
    milestones_html = (
        f'<div class="scenario-explorer-v2__milestones">{"".join(milestone_lines)}</div>'
        if milestone_lines else ""
    )

    return (
        '<section class="scenario-explorer-v2" '
        f'data-module="scenario-explorer-v2" data-state="ready" '
        f'data-games="{games}">'
        '<header class="scenario-explorer-v2__head">'
        '<div>'
        '<p class="scenario-explorer-v2__eyebrow">Season Pace &middot; Projection</p>'
        f'<p class="scenario-explorer-v2__title">Where the {escape(spec["label"])} totals stand</p>'
        '</div>'
        '<span class="scenario-explorer-v2__meta">'
        + (f"projecting to {projected_to_games}-game" if will_project else "final")
        + '</span>'
        '</header>'
        f'<div class="scenario-explorer-v2__rows">{rows_html}</div>'
        f'{milestones_html}'
        '</section>'
    )
