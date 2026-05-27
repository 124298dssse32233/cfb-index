"""Player Splits — Brief §4.6 (P1, scoped to box-score data).

Brief specifies 4 tabs: Situational · Defense quality · Home/Road ·
Pocket (clean vs. pressure). Pocket + Defense-quality both require
play-by-play; today we ship the two splits computable from box-score
data joined to the games table:

  1. **Home / Road** — `games.home_team_id` vs `games.away_team_id`.
  2. **Win / Loss**  — final score from the player's team perspective.
  3. **First half / Second half of season** — week ≤ 7 vs week ≥ 8.

Each split shows a two-column comparison: per-game volume + rate stats.
The same position-aware column logic as `game_log.py` powers the rate
selection.

Public API:
    render_splits(db, player_id, season_year, position, team_id) -> str
    SPLITS_CSS                                                   -> str
"""
from __future__ import annotations

from html import escape
from typing import Any


SPLITS_CSS = """
/* Player Splits module */
.player-splits {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.player-splits__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 10px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
}
.player-splits__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 0.72rem;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  margin: 0;
}
.player-splits__title {
  font-size: 1.05rem;
  font-weight: 600;
  margin: 0;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.player-splits__meta {
  font-size: 0.74rem;
  color: var(--text-quiet, rgba(255,255,255,0.5));
}
.player-splits__panels {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 14px;
  margin-top: 10px;
}
.player-splits__panel {
  background: rgba(255,255,255,0.018);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 12px 14px;
}
.player-splits__panel-title {
  font-size: 0.72rem;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  margin: 0 0 6px 0;
}
.player-splits__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}
.player-splits__table th,
.player-splits__table td {
  padding: 5px 6px;
  text-align: right;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.player-splits__table th:first-child,
.player-splits__table td:first-child {
  text-align: left;
  color: var(--text-soft, rgba(255,255,255,0.78));
  font-weight: 500;
}
.player-splits__table th {
  font-size: 0.66rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  font-weight: 600;
}
.player-splits__games-pill {
  display: inline-block;
  padding: 1px 6px;
  background: rgba(255,255,255,0.06);
  border-radius: 4px;
  font-size: 0.66rem;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  margin-left: 6px;
}
.player-splits__delta {
  display: inline-block;
  font-size: 0.68rem;
  color: var(--text-quiet, rgba(255,255,255,0.5));
  margin-top: 4px;
}
.player-splits__empty {
  padding: 12px;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  font-size: 0.86rem;
  font-style: italic;
}
"""


# Per-game rate columns to show per split, by position.
# (label, category, stat_type, mode)
#   mode: "per_game" | "rate" (rate uses (stat / denom) inside a single game)
_QB_SPLIT_COLS = [
    ("YDS/g",  "passing", "YDS", "per_game"),
    ("TD/g",   "passing", "TD",  "per_game"),
    ("YPA",    "passing", "AVG", "avg"),
    ("INT/g",  "passing", "INT", "per_game"),
]
_RB_SPLIT_COLS = [
    ("YDS/g", "rushing", "YDS", "per_game"),
    ("YPC",   "rushing", "AVG", "avg"),
    ("TD/g",  "rushing", "TD",  "per_game"),
]
_WR_SPLIT_COLS = [
    ("REC/g", "receiving", "REC", "per_game"),
    ("YDS/g", "receiving", "YDS", "per_game"),
    ("YPR",   "receiving", "AVG", "avg"),
    ("TD/g",  "receiving", "TD",  "per_game"),
]
_DEF_SPLIT_COLS = [
    ("TKL/g",  "defensive", "TOT",   "per_game"),
    ("TFL/g",  "defensive", "TFL",   "per_game"),
    ("SACK/g", "defensive", "SACKS", "per_game"),
    ("PD/g",   "defensive", "PD",    "per_game"),
]


def _split_cols_for_position(position: str) -> list[tuple[str, str, str, str]]:
    pos = (position or "").upper().strip()
    if pos in {"QB", "QUARTERBACK"}:
        return _QB_SPLIT_COLS
    if pos in {"RB", "TB", "FB", "HB"}:
        return _RB_SPLIT_COLS
    if pos in {"WR", "TE"}:
        return _WR_SPLIT_COLS
    if pos in {"CB", "S", "DB", "LB", "ILB", "OLB", "MLB",
               "DL", "DE", "DT", "NT", "EDGE"}:
        return _DEF_SPLIT_COLS
    return _QB_SPLIT_COLS


def _fetch_per_game_rows(
    db, player_id: int, season_year: int,
) -> list[dict[str, Any]]:
    """One row per (game_id) with home/away/win-loss context + stats dict."""
    rows = db.query_all(
        """
        select
          pgs.game_id, pgs.week, pgs.team_id,
          pgs.category, pgs.stat_type, pgs.stat_value_num,
          g.home_team_id, g.away_team_id,
          g.home_points, g.away_points
        from player_game_stats pgs
        left join games g on g.game_id = pgs.game_id
        where pgs.player_id = :pid
          and pgs.season_year = :s
        order by pgs.week asc, pgs.game_id asc
        """,
        {"pid": player_id, "s": season_year},
    )
    by_game: dict[int, dict[str, Any]] = {}
    for r in rows:
        gid = int(r["game_id"]) if r["game_id"] is not None else 0
        if gid == 0:
            continue
        bucket = by_game.setdefault(gid, {
            "game_id": gid,
            "week": r.get("week"),
            "player_team_id": r.get("team_id"),
            "home_team_id": r.get("home_team_id"),
            "away_team_id": r.get("away_team_id"),
            "home_points": r.get("home_points"),
            "away_points": r.get("away_points"),
            "stats": {},
        })
        v = r.get("stat_value_num")
        if v is None:
            continue
        bucket["stats"][((r.get("category") or "").lower(), (r.get("stat_type") or "").upper())] = v
    return list(by_game.values())


def _is_home(row: dict[str, Any]) -> bool | None:
    pteam = row.get("player_team_id")
    home = row.get("home_team_id")
    away = row.get("away_team_id")
    if pteam is None or home is None or away is None:
        return None
    if int(pteam) == int(home):
        return True
    if int(pteam) == int(away):
        return False
    return None


def _is_win(row: dict[str, Any]) -> bool | None:
    hp = row.get("home_points")
    ap = row.get("away_points")
    if hp is None or ap is None:
        return None
    home = _is_home(row)
    if home is None:
        return None
    if home:
        if hp > ap: return True
        if hp < ap: return False
        return None  # tie
    if ap > hp: return True
    if ap < hp: return False
    return None


def _aggregate(
    rows: list[dict[str, Any]],
    cols: list[tuple[str, str, str, str]],
) -> dict[str, Any] | None:
    """Return dict mapping label → display string. None if no games."""
    if not rows:
        return None
    n = len(rows)
    out: dict[str, Any] = {"games": n}
    for label, cat, stype, mode in cols:
        key = (cat, stype)
        vals = [float(r["stats"].get(key)) for r in rows if r["stats"].get(key) is not None]
        if not vals:
            out[label] = "—"
            continue
        if mode == "per_game":
            v = sum(vals) / n  # treats missing games as 0
            out[label] = f"{v:.1f}" if v < 100 else f"{int(round(v))}"
        elif mode == "avg":
            v = sum(vals) / len(vals)
            out[label] = f"{v:.1f}"
        else:
            v = sum(vals)
            out[label] = f"{int(round(v))}"
    return out


def _render_panel(
    title: str, left_label: str, right_label: str,
    left_agg: dict[str, Any] | None, right_agg: dict[str, Any] | None,
    cols: list[tuple[str, str, str, str]],
) -> str:
    if not left_agg and not right_agg:
        return ""
    headers = "".join(f'<th>{escape(c[0])}</th>' for c in cols)

    def _row(label: str, agg: dict[str, Any] | None) -> str:
        if not agg:
            return ""
        cells = "".join(f'<td>{escape(str(agg.get(c[0], "—")))}</td>' for c in cols)
        games_pill = f'<span class="player-splits__games-pill">{agg["games"]}g</span>'
        return (
            f'<tr><th scope="row">{escape(label)}{games_pill}</th>'
            f'{cells}</tr>'
        )

    return (
        '<div class="player-splits__panel">'
        f'<p class="player-splits__panel-title">{escape(title)}</p>'
        '<table class="player-splits__table">'
        f'<thead><tr><th></th>{headers}</tr></thead>'
        f'<tbody>{_row(left_label, left_agg)}{_row(right_label, right_agg)}</tbody>'
        '</table>'
        '</div>'
    )


def render_splits(
    db, player_id: int | None, season_year: int | None,
    position: str | None = None, team_id: int | None = None,
) -> str:
    if db is None or player_id is None or season_year is None:
        return ""

    rows = _fetch_per_game_rows(db, int(player_id), int(season_year))
    if not rows:
        return (
            '<section class="player-splits player-splits--empty" '
            'data-module="splits-v2" data-state="empty">'
            '<header class="player-splits__head">'
            '<div><p class="player-splits__eyebrow">Splits</p>'
            '<p class="player-splits__title">Per-game splits</p></div>'
            '</header>'
            '<p class="player-splits__empty">Splits fill in once box scores from at '
            'least three games land for this season.</p>'
            '</section>'
        )

    cols = _split_cols_for_position(position or "")

    # Home / Road
    home_rows = [r for r in rows if _is_home(r) is True]
    road_rows = [r for r in rows if _is_home(r) is False]
    home_panel = _render_panel(
        "Home vs Road", "Home", "Road",
        _aggregate(home_rows, cols), _aggregate(road_rows, cols), cols,
    )

    # Win / Loss
    win_rows  = [r for r in rows if _is_win(r) is True]
    loss_rows = [r for r in rows if _is_win(r) is False]
    wl_panel = _render_panel(
        "Win vs Loss", "Wins", "Losses",
        _aggregate(win_rows, cols), _aggregate(loss_rows, cols), cols,
    )

    # First half / Second half
    first_rows  = [r for r in rows if (r.get("week") or 99) <= 7]
    second_rows = [r for r in rows if (r.get("week") or 0) >= 8]
    half_panel = _render_panel(
        "First half vs Second half", "Weeks 1-7", "Weeks 8+",
        _aggregate(first_rows, cols), _aggregate(second_rows, cols), cols,
    )

    panels_html = home_panel + wl_panel + half_panel
    if not panels_html.strip():
        return (
            '<section class="player-splits player-splits--empty" '
            'data-module="splits-v2" data-state="empty">'
            '<p class="player-splits__empty">Not enough games to split this season yet.</p>'
            '</section>'
        )

    return (
        '<section class="player-splits" '
        f'data-module="splits-v2" data-state="ready" data-games="{len(rows)}">'
        '<header class="player-splits__head">'
        '<div>'
        '<p class="player-splits__eyebrow">Splits · Per-game</p>'
        f'<p class="player-splits__title">{escape(str(season_year))} season · {len(rows)} games</p>'
        '</div>'
        '<span class="player-splits__meta">Home/Road · Win/Loss · Season halves</span>'
        '</header>'
        f'<div class="player-splits__panels">{panels_html}</div>'
        '<p class="player-splits__delta">Defense-quality and pocket (clean vs. pressure) splits arrive when CFBD play-by-play lands.</p>'
        '</section>'
    )
