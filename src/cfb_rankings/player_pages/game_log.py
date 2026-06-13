"""Player Game Log — Brief §4.4 (P0).

Week-by-week box-score table for the player's current/most-recent
season. The biggest legacy-parity gap with ESPN / Sports Reference —
fans land on a player page expecting per-game rows.

Position-aware column sets:
  - QB        : CMP/ATT, YDS, TD, INT, YPA, QBR
  - RB / FB   : CAR, YDS, AVG, TD, LONG
  - WR / TE   : REC, YDS, AVG, TD, LONG
  - DB / LB / DL : TKL, SACK, INT, PD
  - K / P     : FG, XP, PUNT, AVG  (best-effort)

Each row carries opponent + W/L chip + final score, derived from
the games table. When a row is missing for a week (bye, DNP), the
table simply skips it — no synthetic placeholder rows.

Public API:
    render_game_log(db, player_id, season_year, position, team_id) -> str
    GAME_LOG_CSS                                                   -> str
"""
from __future__ import annotations

from html import escape
from typing import Any


GAME_LOG_CSS = """
/* Player Game Log module */
.player-game-log {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.player-game-log__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 10px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
}
.player-game-log__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 0.72rem;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  margin: 0;
}
.player-game-log__title {
  font-size: 1.05rem;
  font-weight: 600;
  margin: 0;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.player-game-log__meta {
  font-size: 0.78rem;
  color: var(--text-quiet, rgba(255,255,255,0.55));
}
.player-game-log__scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.player-game-log__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.86rem;
  min-width: 540px;
}
.player-game-log__table th,
.player-game-log__table td {
  padding: 7px 9px;
  text-align: right;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  white-space: nowrap;
}
.player-game-log__table th {
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  font-weight: 600;
  border-bottom: 1px solid rgba(255,255,255,0.10);
}
.player-game-log__table th:first-child,
.player-game-log__table td:first-child {
  text-align: left;
  position: sticky;
  left: 0;
  background: linear-gradient(90deg, rgba(15,16,20,0.96) 70%, rgba(15,16,20,0));
  z-index: 1;
}
.player-game-log__table th:nth-child(2),
.player-game-log__table td:nth-child(2) { text-align: left; }
.player-game-log__table tr:hover td { background: rgba(255,255,255,0.025); }
.player-game-log__week {
  font-weight: 600;
  color: var(--text-bright, rgba(255,255,255,0.85));
}
.player-game-log__opp {
  color: var(--text-quiet, rgba(255,255,255,0.7));
}
.player-game-log__result {
  display: inline-block;
  min-width: 50px;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  margin-right: 6px;
}
.player-game-log__result--win {
  background: rgba(58, 168, 102, 0.18);
  color: #6fd198;
}
.player-game-log__result--loss {
  background: rgba(204, 64, 76, 0.18);
  color: #ee8a92;
}
.player-game-log__result--tie {
  background: rgba(160, 160, 160, 0.18);
  color: #bcbcbc;
}
.player-game-log__result--na {
  background: rgba(160, 160, 160, 0.10);
  color: #888;
}
.player-game-log__note {
  font-size: 0.74rem;
  color: var(--text-quiet, rgba(255,255,255,0.62));
  font-style: italic;
  text-align: left;
  min-width: 160px;
  max-width: 240px;
  white-space: normal;
}
.player-game-log__note-col {
  text-align: left;
}
.player-game-log__total-row td {
  border-top: 1px solid rgba(255,255,255,0.15);
  font-weight: 600;
  color: var(--text-bright, rgba(255,255,255,0.92));
  background: rgba(255,255,255,0.015);
}
.player-game-log__empty {
  padding: 14px;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  font-size: 0.88rem;
  font-style: italic;
}
@media (max-width: 720px) {
  .player-game-log__table { font-size: 0.78rem; min-width: 480px; }
  .player-game-log__table th,
  .player-game-log__table td { padding: 6px 7px; }
}
"""


# Per-position column spec. Each entry: (header, category, stat_type, fmt).
# fmt: "int" | "float1" | "pct" | "text"
_QB_COLS = [
    ("CMP/ATT", "passing", "C/ATT", "text"),
    ("YDS",     "passing", "YDS",   "int"),
    ("TD",      "passing", "TD",    "int"),
    ("INT",     "passing", "INT",   "int"),
    ("YPA",     "passing", "AVG",   "float1"),
    ("QBR",     "passing", "QBR",   "float1"),
]
# Column glossary — rendered as native `title` attr on <th>. No JS needed,
# native browser tooltip on hover/touch-and-hold.
_COL_TOOLTIPS: dict[str, str] = {
    "CMP/ATT": "Completions / attempts",
    "YDS":     "Yards gained in this category",
    "TD":      "Touchdowns (position-dependent: passing/rushing/receiving)",
    "INT":     "Interceptions thrown (QB) or picked (DB)",
    "YPA":     "Yards per pass attempt",
    "QBR":     "ESPN Quarterback Rating, 0-100",
    "CAR":     "Carries — designed running plays",
    "AVG":     "Yards per attempt for that category",
    "LONG":    "Longest play of the game",
    "REC":     "Receptions (catches)",
    "TKL":     "Total tackles (solo + assist)",
    "SOLO":    "Solo tackles",
    "TFL":     "Tackles for loss",
    "SACK":    "Sacks of the opposing QB",
    "PD":      "Passes defended (broken up or intercepted)",
    "FGM/FGA": "Field goals made / attempted",
    "XP":      "Extra points made / attempted",
    "PUNT":    "Number of punts",
    "IN20":    "Punts landed inside the 20-yard line",
    "PTS":     "Points scored by kicking",
}
_RB_COLS = [
    ("CAR",  "rushing", "CAR",  "int"),
    ("YDS",  "rushing", "YDS",  "int"),
    ("AVG",  "rushing", "AVG",  "float1"),
    ("TD",   "rushing", "TD",   "int"),
    ("LONG", "rushing", "LONG", "int"),
]
_WR_COLS = [
    ("REC",  "receiving", "REC",  "int"),
    ("YDS",  "receiving", "YDS",  "int"),
    ("AVG",  "receiving", "AVG",  "float1"),
    ("TD",   "receiving", "TD",   "int"),
    ("LONG", "receiving", "LONG", "int"),
]
_DEF_COLS = [
    ("TKL",  "defensive", "TOT",  "int"),
    ("SOLO", "defensive", "SOLO", "int"),
    ("TFL",  "defensive", "TFL",  "float1"),
    ("SACK", "defensive", "SACKS", "float1"),
    ("INT",  "interceptions", "INT", "int"),
    ("PD",   "defensive", "PD",   "int"),
]
_K_COLS = [
    ("FGM/FGA", "kicking", "FG",  "text"),
    ("LONG",    "kicking", "LONG", "int"),
    ("XP",      "kicking", "XP",  "text"),
    ("PTS",     "kicking", "PTS", "int"),
]
_P_COLS = [
    ("PUNT", "punting", "NO",   "int"),
    ("YDS",  "punting", "YDS",  "int"),
    ("AVG",  "punting", "AVG",  "float1"),
    ("LONG", "punting", "LONG", "int"),
    ("IN20", "punting", "IN 20", "int"),
]


def _columns_for_position(position: str) -> list[tuple[str, str, str, str]]:
    pos = (position or "").upper().strip()
    if pos in {"QB", "QUARTERBACK"}:
        return _QB_COLS
    if pos in {"RB", "TB", "FB", "HB", "RUNNINGBACK", "RUNNING BACK"}:
        return _RB_COLS
    if pos in {"WR", "TE", "WIDE RECEIVER", "TIGHT END"}:
        return _WR_COLS
    if pos in {"CB", "S", "DB", "LB", "ILB", "OLB", "MLB",
               "DL", "DE", "DT", "NT", "EDGE", "DEFENSIVE BACK",
               "LINEBACKER", "DEFENSIVE LINEMAN"}:
        return _DEF_COLS
    if pos in {"K", "PK", "KICKER"}:
        return _K_COLS
    if pos in {"P", "PUNTER"}:
        return _P_COLS
    # Unknown position — best guess from data: empty result triggers
    # the empty-state copy below.
    return _QB_COLS


def _fmt(value: Any, fmt: str) -> str:
    if value is None or value == "":
        return "—"
    if fmt == "text":
        return escape(str(value))
    try:
        v = float(value)
    except (TypeError, ValueError):
        return escape(str(value))
    if fmt == "int":
        return f"{int(round(v))}"
    if fmt == "float1":
        return f"{v:.1f}"
    if fmt == "pct":
        return f"{v:.1f}%"
    return escape(str(value))


def _fetch_game_log_rows(
    db, player_id: int, season_year: int, team_id: int | None,
) -> list[dict[str, Any]]:
    """One row per (game_id, week). Aggregates stat_type values per row."""
    rows = db.query_all(
        """
        select
          pgs.game_id, pgs.week, pgs.season_type, pgs.category, pgs.stat_type,
          pgs.stat_value_num, pgs.stat_value_text, pgs.team_id,
          g.home_team_id, g.away_team_id,
          g.home_points, g.away_points, g.start_time_utc, g.status,
          home_t.canonical_name as home_team_name,
          home_t.slug           as home_team_slug,
          away_t.canonical_name as away_team_name,
          away_t.slug           as away_team_slug
        from player_game_stats pgs
        left join games g on g.game_id = pgs.game_id
        left join teams home_t on home_t.team_id = g.home_team_id
        left join teams away_t on away_t.team_id = g.away_team_id
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
            "season_type": r.get("season_type"),
            "player_team_id": r.get("team_id"),
            "home_team_id": r.get("home_team_id"),
            "away_team_id": r.get("away_team_id"),
            "home_team_name": r.get("home_team_name"),
            "home_team_slug": r.get("home_team_slug"),
            "away_team_name": r.get("away_team_name"),
            "away_team_slug": r.get("away_team_slug"),
            "home_points": r.get("home_points"),
            "away_points": r.get("away_points"),
            "start_time_utc": r.get("start_time_utc"),
            "status": r.get("status"),
            "stats": {},
        })
        cat = (r.get("category") or "").lower()
        stype = (r.get("stat_type") or "").upper()
        # Prefer numeric, fall back to text (e.g. "41/49" CMP/ATT)
        if r.get("stat_value_num") is not None:
            bucket["stats"][(cat, stype)] = r["stat_value_num"]
        elif r.get("stat_value_text"):
            bucket["stats"][(cat, stype)] = r["stat_value_text"]
    # Stable sort: regular season (by week) first, then postseason. CFBD
    # numbers postseason games from week=1 too, so without the phase key a
    # postseason "week 1" sorts ahead of regular week 2 and renders a second
    # "Wk 1" row (the Arch Manning duplicate-Wk-1 bug, 2026-06-13).
    def _phase_order(season_type: Any) -> int:
        return 0 if str(season_type or "regular").lower() == "regular" else 1
    out = list(by_game.values())
    out.sort(key=lambda x: (
        _phase_order(x.get("season_type")),
        (x.get("week") or 99),
        (x.get("start_time_utc") or ""),
        x.get("game_id") or 0,
    ))
    return out


def _opp_label(row: dict[str, Any], team_id: int | None) -> tuple[str, str, str]:
    """Return (opponent_label, result_class, result_text).

    Result is from the player team's perspective when team_id is supplied.
    """
    pteam = row.get("player_team_id") or team_id
    home = row.get("home_team_id")
    away = row.get("away_team_id")
    home_name = row.get("home_team_name") or "Home"
    away_name = row.get("away_team_name") or "Away"
    home_pts = row.get("home_points")
    away_pts = row.get("away_points")

    is_home = pteam is not None and home is not None and int(pteam) == int(home)
    is_away = pteam is not None and away is not None and int(pteam) == int(away)

    if is_home:
        opp_label = f"vs {away_name}"
    elif is_away:
        opp_label = f"@ {home_name}"
    else:
        opp_label = f"{away_name} @ {home_name}"

    # Result chip
    if home_pts is None or away_pts is None:
        return opp_label, "na", "—"
    hp, ap = int(home_pts), int(away_pts)
    if is_home:
        if hp > ap:
            return opp_label, "win", f"W {hp}-{ap}"
        if hp < ap:
            return opp_label, "loss", f"L {hp}-{ap}"
        return opp_label, "tie", f"T {hp}-{ap}"
    if is_away:
        if ap > hp:
            return opp_label, "win", f"W {ap}-{hp}"
        if ap < hp:
            return opp_label, "loss", f"L {ap}-{hp}"
        return opp_label, "tie", f"T {ap}-{hp}"
    # Unknown side
    return opp_label, "na", f"{hp}-{ap}"


def _compute_game_notes(
    rows: list[dict[str, Any]],
    cols: list[tuple[str, str, str, str]],
    position: str,
) -> dict[int, str]:
    """Return {week: note_text} for noteworthy games.

    Identifies: season-highs in headline volume stat, multi-TD games,
    zero/multi-INT games for QBs, big games against ranked-ish opponents,
    bounceback games after a rough one.
    """
    if not rows:
        return {}
    pos = (position or "").upper().strip()

    # Helper: pull a value from a row's stats
    def gv(r, cat, st):
        return r.get("stats", {}).get((cat, st))

    notes: dict[int, str] = {}
    # Per-position primary volume stat (for season-high detection)
    primary: tuple[str, str] | None = None
    if pos == "QB":
        primary = ("passing", "YDS")
    elif pos in {"RB", "TB", "FB", "HB"}:
        primary = ("rushing", "YDS")
    elif pos in {"WR", "TE"}:
        primary = ("receiving", "YDS")
    elif pos in {"CB", "S", "DB", "LB", "ILB", "OLB", "MLB",
                 "DL", "DE", "DT", "NT", "EDGE"}:
        primary = ("defensive", "TOT")

    # Compute series of primary stat with week
    series: list[tuple[int, float]] = []
    if primary:
        for r in rows:
            wk = r.get("week")
            v = gv(r, *primary)
            try:
                if wk is not None and v is not None:
                    series.append((int(wk), float(v)))
            except (TypeError, ValueError):
                continue

    season_high_wk: int | None = None
    season_high_val: float = 0.0
    if series:
        season_high_wk, season_high_val = max(series, key=lambda t: t[1])

    for r in rows:
        wk = r.get("week")
        if wk is None:
            continue
        bits: list[str] = []

        # Season-high in primary stat
        if season_high_wk is not None and wk == season_high_wk and primary:
            unit = "yds" if primary[1] in {"YDS"} else (
                "tackles" if primary[1] == "TOT" else "")
            bits.append(f"Season-high {int(season_high_val)} {unit}".strip())

        # Position-specific event flags
        if pos == "QB":
            td = gv(r, "passing", "TD")
            it = gv(r, "passing", "INT")
            try:
                td = float(td) if td is not None else 0
                it = float(it) if it is not None else 0
            except (TypeError, ValueError):
                td = 0; it = 0
            if td >= 4 and "Season-high" not in " ".join(bits):
                bits.append(f"{int(td)} TD passes")
            if it >= 3:
                bits.append(f"{int(it)} INTs — rough day")
            # Clean game
            if td >= 2 and it == 0 and primary and gv(r, *primary) and float(gv(r, *primary)) >= 250:
                if not bits:
                    bits.append(f"Clean {int(td)}-TD game")
        elif pos in {"RB", "TB", "FB", "HB"}:
            yds = gv(r, "rushing", "YDS") or 0
            tds = gv(r, "rushing", "TD") or 0
            try:
                yds = float(yds); tds = float(tds)
            except (TypeError, ValueError):
                yds = 0; tds = 0
            if tds >= 3 and "Season-high" not in " ".join(bits):
                bits.append(f"{int(tds)} rushing TDs")
            if yds >= 150 and not bits:
                bits.append(f"{int(yds)}-yard day")
        elif pos in {"WR", "TE"}:
            yds = gv(r, "receiving", "YDS") or 0
            tds = gv(r, "receiving", "TD") or 0
            try:
                yds = float(yds); tds = float(tds)
            except (TypeError, ValueError):
                yds = 0; tds = 0
            if tds >= 2 and "Season-high" not in " ".join(bits):
                bits.append(f"{int(tds)} TD catches")
            if yds >= 130 and not bits:
                bits.append(f"{int(yds)}-yard receiving day")
        else:
            sk = gv(r, "defensive", "SACKS") or 0
            tfl = gv(r, "defensive", "TFL") or 0
            try:
                sk = float(sk); tfl = float(tfl)
            except (TypeError, ValueError):
                sk = 0; tfl = 0
            if sk >= 2 and "Season-high" not in " ".join(bits):
                bits.append(f"{int(sk) if sk == int(sk) else sk} sacks")
            elif tfl >= 2.5 and not bits:
                bits.append(f"{tfl:.1f} TFL")

        if bits:
            notes[wk] = " · ".join(bits)
    return notes


def _row_totals(
    rows: list[dict[str, Any]],
    cols: list[tuple[str, str, str, str]],
) -> dict[tuple[str, str], Any]:
    """Sum or average per-column across all games for the bottom 'TOTAL' row.

    Numeric stat_types are summed except AVG / QBR / YPA which are averaged
    weighted by their corresponding count when computable. For simplicity we
    average AVG / QBR; for C/ATT we sum the two halves.
    """
    totals: dict[tuple[str, str], float] = {}
    counts: dict[tuple[str, str], int] = {}
    catt_total = [0, 0]  # [cmp, att]

    for r in rows:
        stats = r.get("stats", {})
        for _hdr, cat, stype, fmt in cols:
            key = (cat, stype)
            val = stats.get(key)
            if val is None:
                continue
            if cat == "passing" and stype == "C/ATT" and isinstance(val, str) and "/" in val:
                try:
                    c, a = val.split("/")
                    catt_total[0] += int(c)
                    catt_total[1] += int(a)
                except (TypeError, ValueError):
                    pass
                continue
            if cat == "kicking" and stype == "FG" and isinstance(val, str) and "/" in val:
                try:
                    m, a = val.split("/")
                    totals.setdefault((cat, "FG_MADE"), 0.0)
                    totals.setdefault((cat, "FG_ATT"), 0.0)
                    totals[(cat, "FG_MADE")] += int(m)
                    totals[(cat, "FG_ATT")] += int(a)
                except (TypeError, ValueError):
                    pass
                continue
            try:
                fv = float(val)
            except (TypeError, ValueError):
                continue
            if fmt in {"float1", "pct"} and stype in {"AVG", "QBR", "YPA"}:
                totals[key] = totals.get(key, 0.0) + fv
                counts[key] = counts.get(key, 0) + 1
            elif stype == "LONG":
                totals[key] = max(totals.get(key, fv), fv)
            else:
                totals[key] = totals.get(key, 0.0) + fv

    # Average the rate metrics
    for key in list(totals.keys()):
        if key in counts and counts[key] > 0 and key[1] in {"AVG", "QBR", "YPA"}:
            totals[key] = totals[key] / counts[key]

    out: dict[tuple[str, str], Any] = dict(totals)
    if catt_total[1] > 0:
        out[("passing", "C/ATT")] = f"{catt_total[0]}/{catt_total[1]}"
    if ("kicking", "FG_MADE") in out and ("kicking", "FG_ATT") in out:
        out[("kicking", "FG")] = f"{int(out[('kicking', 'FG_MADE')])}/{int(out[('kicking', 'FG_ATT')])}"
    return out


def render_game_log(
    db, player_id: int | None, season_year: int | None,
    position: str | None = None, team_id: int | None = None,
) -> str:
    if db is None or player_id is None or season_year is None:
        return ""

    cols = _columns_for_position(position or "")
    rows = _fetch_game_log_rows(db, int(player_id), int(season_year), team_id)

    if not rows:
        return (
            '<article class="player-game-log player-game-log--empty" '
            'data-module="game-log" data-state="empty">'
            '<header class="player-game-log__head">'
            '<div><p class="player-game-log__eyebrow">Game Log</p>'
            '<p class="player-game-log__title">Week-by-week box</p></div>'
            '</header>'
            '<p class="player-game-log__empty">No per-game rows for this season yet — '
            'the table fills in as box scores arrive.</p>'
            '</article>'
        )

    # Header — every column gets a native browser tooltip via title attr.
    def _th(label: str) -> str:
        tip = _COL_TOOLTIPS.get(label, "")
        title_attr = f' title="{escape(tip)}"' if tip else ""
        cursor_style = ' style="cursor: help; text-decoration: underline dotted rgba(255,255,255,0.25);"' if tip else ""
        return f'<th scope="col"{title_attr}{cursor_style}>{escape(label)}</th>'
    head_cells = "".join(_th(h) for h, *_ in cols)
    head_cells += '<th scope="col" class="player-game-log__note-col">Note</th>'

    notes_by_week = _compute_game_notes(rows, cols, position or "")

    # Body rows
    body_rows: list[str] = []
    for r in rows:
        wk = r.get("week")
        _is_post = str(r.get("season_type") or "regular").lower() != "regular"
        wk_disp = "Bowl" if _is_post else (f"Wk {wk}" if wk is not None else "—")
        opp_label, rcls, rtext = _opp_label(r, team_id)
        cells: list[str] = [
            f'<td><span class="player-game-log__week">{escape(wk_disp)}</span></td>',
            (
                '<td>'
                f'<span class="player-game-log__result player-game-log__result--{rcls}">'
                f'{escape(rtext)}</span>'
                f'<span class="player-game-log__opp">{escape(opp_label)}</span>'
                '</td>'
            ),
        ]
        for _hdr, cat, stype, fmt in cols:
            v = r.get("stats", {}).get((cat, stype))
            cells.append(f"<td>{_fmt(v, fmt)}</td>")
        # Auto-generated note cell. notes_by_week is keyed by week number;
        # postseason shares week numbers with the regular season, so skip the
        # lookup on postseason rows to avoid inheriting a regular-week note.
        note_text = "" if _is_post else notes_by_week.get(wk, "")
        cells.append(
            f'<td class="player-game-log__note">{escape(note_text)}</td>'
        )
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    # Total row
    totals = _row_totals(rows, cols)
    total_cells: list[str] = ['<td><span class="player-game-log__week">TOTAL</span></td>',
                              '<td></td>']
    for _hdr, cat, stype, fmt in cols:
        v = totals.get((cat, stype))
        total_cells.append(f"<td>{_fmt(v, fmt) if v is not None else '—'}</td>")
    total_cells.append('<td></td>')  # note col
    total_row = (
        '<tr class="player-game-log__total-row">'
        + "".join(total_cells)
        + "</tr>"
    )

    n_games = len(rows)
    return (
        '<article class="player-game-log" '
        f'data-module="game-log" data-state="ready" data-games="{n_games}">'
        '<header class="player-game-log__head">'
        '<div>'
        '<p class="player-game-log__eyebrow">Game Log &middot; Week-by-week</p>'
        f'<p class="player-game-log__title">{escape(str(season_year))} season &middot; {n_games} games</p>'
        '</div>'
        f'<span class="player-game-log__meta">Box score &middot; CFBD</span>'
        '</header>'
        '<div class="player-game-log__scroll">'
        '<table class="player-game-log__table">'
        '<thead><tr>'
        '<th scope="col">Wk</th>'
        '<th scope="col">Opp</th>'
        f'{head_cells}'
        '</tr></thead>'
        '<tbody>'
        + "".join(body_rows)
        + total_row
        + '</tbody>'
        '</table>'
        '</div>'
        '</article>'
    )
