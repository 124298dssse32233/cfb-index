"""Box-Score Savant Card — Brief §4.5 (P1, downgraded for current data).

The Player Brief specifies a Savant-style percentile card built from
CFBD play-by-play (EPA/dropback, CPOE, aDOT, deep-ball accuracy,
pressure-to-sack, etc.). Today, no PBP table is ingested locally and
`player_advanced_metrics` is empty. Rather than ship an empty module
forever, this renders a v1 percentile card from box-score stats that
*are* in `player_season_stats` (1.3M+ rows ingested).

The bars are still Savant-grammar (red→neutral→blue diverging gradient,
percentile-pinned value chip, peer-cohort label, ordered best →
interesting → concerns) — just driven by box-rate metrics instead of
play-by-play efficiency metrics. An honest note in the header says
"EPA / CPOE / aDOT arrive when CFBD play-by-play lands."

Cohort: same position, same season, min sample size threshold per
position (so a backup QB with 12 attempts isn't ranked against starters).

Public API:
    render_box_savant(db, player_id, season_year, position) -> str
    BOX_SAVANT_CSS                                          -> str
"""
from __future__ import annotations

from html import escape
from typing import Any


BOX_SAVANT_CSS = """
/* Box-Score Savant card */
.box-savant {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(16px, 2vw, 22px) clamp(18px, 2.2vw, 26px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.box-savant__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 6px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
}
.box-savant__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 0.72rem;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  margin: 0;
}
.box-savant__title {
  font-size: 1.05rem;
  font-weight: 600;
  margin: 0;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.box-savant__meta {
  font-size: 0.74rem;
  color: var(--text-quiet, rgba(255,255,255,0.5));
}
.box-savant__lede {
  font-size: 0.92rem;
  line-height: 1.45;
  color: var(--text-soft, rgba(255,255,255,0.78));
  margin: 8px 0 14px 0;
}
.box-savant__lede strong { color: var(--text-bright, rgba(255,255,255,0.92)); }
.box-savant__bars { display: flex; flex-direction: column; gap: 9px; }
.box-savant__bar-row {
  display: grid;
  grid-template-columns: 11.5rem 1fr 4rem;
  gap: 14px;
  align-items: center;
}
.box-savant__bar-label {
  font-size: 0.86rem;
  color: var(--text-soft, rgba(255,255,255,0.78));
}
.box-savant__bar-label small {
  display: block;
  font-size: 0.66rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.5));
  margin-top: 1px;
}
.box-savant__bar-track {
  position: relative;
  height: 12px;
  border-radius: 999px;
  background: var(--pct-gradient, linear-gradient(90deg,#d93a4a,#6b7280,#1e6fd9));
  overflow: visible;
}
.box-savant__bar-track::before,
.box-savant__bar-track::after {
  content: "";
  position: absolute;
  top: -3px;
  bottom: -3px;
  width: 1px;
  background: rgba(255,255,255,0.18);
}
.box-savant__bar-track::before { left: 25%; }
.box-savant__bar-track::after  { left: 75%; }
.box-savant__bar-track--inverted {
  background: var(--pct-gradient-inverted, linear-gradient(90deg,#1e6fd9,#6b7280,#d93a4a));
}
.box-savant__bar-pin {
  position: absolute;
  top: -2px;
  width: 16px;
  height: 16px;
  background: #f4f4f5;
  border: 2px solid #15161a;
  border-radius: 50%;
  transform: translateX(-50%);
  box-shadow: 0 1px 4px rgba(0,0,0,0.45);
}
.box-savant__bar-value {
  text-align: right;
  font-weight: 600;
  font-size: 0.88rem;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.box-savant__bar-value small {
  display: block;
  font-size: 0.64rem;
  letter-spacing: 0.06em;
  color: var(--text-quiet, rgba(255,255,255,0.5));
  font-weight: 500;
}
.box-savant__footnote {
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  font-size: 0.74rem;
  color: var(--text-quiet, rgba(255,255,255,0.5));
  line-height: 1.45;
}
.box-savant--empty {
  color: var(--text-quiet, rgba(255,255,255,0.55));
  font-style: italic;
  padding: 14px;
}
@media (max-width: 640px) {
  .box-savant__bar-row {
    grid-template-columns: 9rem 1fr 3.4rem;
    gap: 10px;
  }
  .box-savant__bar-label { font-size: 0.80rem; }
  .box-savant__bar-value { font-size: 0.80rem; }
}
"""


# Metric spec: (display_label, category, stat_type, min_attempts_metric, inverted, format)
# min_attempts_metric: a (category, stat_type) gate for cohort eligibility (e.g. min ATT for QBs).
# inverted: True means low value is good (INT, fumbles).
# format: "int" | "float1" | "pct" (0-1 → %) | "intpct" (raw 0-100)
_QB_METRICS = [
    ("Pass yards",   "passing", "YDS",  ("passing", "ATT", 80),  False, "int"),
    ("Pass TDs",     "passing", "TD",   ("passing", "ATT", 80),  False, "int"),
    ("Yards / att",  "passing", "YPA",  ("passing", "ATT", 80),  False, "float1"),
    ("Completion %", "passing", "PCT",  ("passing", "ATT", 80),  False, "pct"),
    ("Interceptions","passing", "INT",  ("passing", "ATT", 80),  True,  "int"),
    ("Rush yards",   "rushing", "YDS",  ("passing", "ATT", 80),  False, "int"),
    ("Rush TDs",     "rushing", "TD",   ("passing", "ATT", 80),  False, "int"),
    ("Fumbles lost", "fumbles", "LOST", ("passing", "ATT", 80),  True,  "int"),
]

_RB_METRICS = [
    ("Rush yards",    "rushing",   "YDS",  ("rushing", "CAR", 40), False, "int"),
    ("Yards / carry", "rushing",   "YPC",  ("rushing", "CAR", 40), False, "float1"),
    ("Rush TDs",      "rushing",   "TD",   ("rushing", "CAR", 40), False, "int"),
    ("Long run",      "rushing",   "LONG", ("rushing", "CAR", 40), False, "int"),
    ("Carries",       "rushing",   "CAR",  ("rushing", "CAR", 40), False, "int"),
    ("Rec yards",     "receiving", "YDS",  ("rushing", "CAR", 40), False, "int"),
    ("Receptions",    "receiving", "REC",  ("rushing", "CAR", 40), False, "int"),
    ("Fumbles lost",  "fumbles",   "LOST", ("rushing", "CAR", 40), True,  "int"),
]

_WR_METRICS = [
    ("Rec yards",     "receiving", "YDS",  ("receiving", "REC", 12), False, "int"),
    ("Receptions",    "receiving", "REC",  ("receiving", "REC", 12), False, "int"),
    ("Yards / catch", "receiving", "YPR",  ("receiving", "REC", 12), False, "float1"),
    ("Rec TDs",       "receiving", "TD",   ("receiving", "REC", 12), False, "int"),
    ("Long catch",    "receiving", "LONG", ("receiving", "REC", 12), False, "int"),
    ("Rush yards",    "rushing",   "YDS",  ("receiving", "REC", 12), False, "int"),
    ("Rush TDs",      "rushing",   "TD",   ("receiving", "REC", 12), False, "int"),
    ("Fumbles lost",  "fumbles",   "LOST", ("receiving", "REC", 12), True,  "int"),
]

_DEF_METRICS = [
    ("Tackles",          "defensive",     "TOT",   ("defensive", "TOT", 10), False, "int"),
    ("Solo tackles",     "defensive",     "SOLO",  ("defensive", "TOT", 10), False, "int"),
    ("Tackles for loss", "defensive",     "TFL",   ("defensive", "TOT", 10), False, "float1"),
    ("Sacks",            "defensive",     "SACKS", ("defensive", "TOT", 10), False, "float1"),
    ("Passes defended",  "defensive",     "PD",    ("defensive", "TOT", 10), False, "int"),
    ("QB hurries",       "defensive",     "QB HUR",("defensive", "TOT", 10), False, "int"),
    ("Interceptions",    "interceptions", "INT",   ("defensive", "TOT", 10), False, "int"),
    ("Forced fumbles",   "fumbles",       "FUM",   ("defensive", "TOT", 10), False, "int"),
]


def _metrics_for_position(position: str) -> list[tuple]:
    pos = (position or "").upper().strip()
    if pos in {"QB", "QUARTERBACK"}:
        return _QB_METRICS
    if pos in {"RB", "TB", "FB", "HB", "RUNNINGBACK", "RUNNING BACK"}:
        return _RB_METRICS
    if pos in {"WR", "TE", "WIDE RECEIVER", "TIGHT END"}:
        return _WR_METRICS
    if pos in {"CB", "S", "DB", "LB", "ILB", "OLB", "MLB",
               "DL", "DE", "DT", "NT", "EDGE",
               "DEFENSIVE BACK", "LINEBACKER", "DEFENSIVE LINEMAN"}:
        return _DEF_METRICS
    return []


# Per-process cache of cohort distributions. Keyed by (season_year, position bucket, category, stat_type).
_COHORT_CACHE: dict[tuple, list[float]] = {}


_POSITION_BUCKETS = {
    "QB": ("QB",),
    "RB": ("RB", "TB", "FB", "HB"),
    "WR": ("WR",),
    "TE": ("TE",),
    "DEF": ("CB", "S", "DB", "LB", "ILB", "OLB", "MLB",
            "DL", "DE", "DT", "NT", "EDGE"),
}


def _position_bucket(position: str) -> str:
    pos = (position or "").upper().strip()
    for key, members in _POSITION_BUCKETS.items():
        if pos in members:
            return key
    return "OTHER"


def _fetch_cohort_values(
    db, season_year: int, position_bucket: str,
    category: str, stat_type: str,
    gate_category: str, gate_stat: str, gate_min: float,
) -> list[float]:
    """Return latest-week cumulative values for the metric across the cohort."""
    cache_key = (season_year, position_bucket, category, stat_type, gate_min)
    if cache_key in _COHORT_CACHE:
        return _COHORT_CACHE[cache_key]

    members = _POSITION_BUCKETS.get(position_bucket, ())
    if not members:
        _COHORT_CACHE[cache_key] = []
        return []

    placeholders = ",".join(f"'{m}'" for m in members)
    # Use the latest week's cumulative snapshot per player as the season value.
    # The gate ensures only players above sample threshold (e.g. QBs with 80+ ATT) are in
    # the cohort. Position is read from player_season_stats.position (per-snapshot, far
    # more complete than the players-table master position which is blank for ~12k rows).
    rows = db.query_all(
        f"""
        with player_latest as (
            select player_id, max(week) as max_week
              from player_season_stats
             where season_year = :s
               and category = :gate_cat
               and stat_type = :gate_st
             group by player_id
        ),
        gate_pass as (
            select pss.player_id
              from player_season_stats pss
              join player_latest pl
                on pl.player_id = pss.player_id
               and pl.max_week  = pss.week
             where pss.season_year = :s
               and pss.category = :gate_cat
               and pss.stat_type = :gate_st
               and pss.stat_value_num >= :gate_min
               and pss.position in ({placeholders})
        ),
        target_latest as (
            select pss.player_id, pss.stat_value_num
              from player_season_stats pss
              join player_latest pl
                on pl.player_id = pss.player_id
               and pl.max_week  = pss.week
             where pss.season_year = :s
               and pss.category = :tgt_cat
               and pss.stat_type = :tgt_st
        )
        select tl.stat_value_num
          from target_latest tl
          join gate_pass gp on gp.player_id = tl.player_id
         where tl.stat_value_num is not null
        """,
        {
            "s": season_year,
            "gate_cat": gate_category,
            "gate_st": gate_stat,
            "gate_min": gate_min,
            "tgt_cat": category,
            "tgt_st": stat_type,
        },
    )
    vals = [float(r["stat_value_num"]) for r in rows if r["stat_value_num"] is not None]
    _COHORT_CACHE[cache_key] = vals
    return vals


def _fetch_player_value(
    db, player_id: int, season_year: int, category: str, stat_type: str,
) -> float | None:
    rows = db.query_all(
        """
        select stat_value_num
          from player_season_stats
         where player_id = :pid
           and season_year = :s
           and category = :cat
           and stat_type = :st
         order by week desc
         limit 1
        """,
        {"pid": player_id, "s": season_year, "cat": category, "st": stat_type},
    )
    if not rows:
        return None
    v = rows[0]["stat_value_num"]
    return float(v) if v is not None else None


def _percentile(value: float, cohort: list[float], inverted: bool) -> float:
    """Return 0-100 percentile. Inverted: lower value → higher percentile."""
    if not cohort:
        return 50.0
    if inverted:
        below = sum(1 for c in cohort if c > value)
    else:
        below = sum(1 for c in cohort if c < value)
    equal = sum(1 for c in cohort if c == value)
    total = len(cohort)
    # Mid-rank for ties
    pct = 100.0 * (below + 0.5 * equal) / total
    return max(0.0, min(100.0, pct))


def _fmt_value(value: float, fmt: str) -> str:
    if fmt == "int":
        return f"{int(round(value))}"
    if fmt == "float1":
        return f"{value:.1f}"
    if fmt == "pct":
        if value <= 1.0:
            return f"{value*100:.1f}%"
        return f"{value:.1f}%"
    return f"{value:.1f}"


def compute_savant_bars(
    db, player_id: int, season_year: int, position: str,
) -> list[dict[str, Any]]:
    """Return ordered list of bar dicts. Best → interesting → concerns."""
    metrics = _metrics_for_position(position)
    if not metrics:
        return []
    bucket = _position_bucket(position)
    bars: list[dict[str, Any]] = []
    for label, cat, stype, gate, inverted, fmt in metrics:
        gate_cat, gate_st, gate_min = gate
        value = _fetch_player_value(db, player_id, season_year, cat, stype)
        if value is None:
            continue
        cohort = _fetch_cohort_values(
            db, season_year, bucket, cat, stype,
            gate_cat, gate_st, gate_min,
        )
        if len(cohort) < 5:
            continue
        pct = _percentile(value, cohort, inverted)
        bars.append({
            "label": label,
            "category": cat,
            "stat_type": stype,
            "value": value,
            "value_fmt": _fmt_value(value, fmt),
            "percentile": pct,
            "rank": _rank_in_cohort(value, cohort, inverted),
            "cohort_size": len(cohort),
            "inverted": inverted,
            "fmt": fmt,
        })
    bars.sort(key=lambda b: b["percentile"], reverse=True)
    return bars


def _rank_in_cohort(value: float, cohort: list[float], inverted: bool) -> int:
    if not cohort:
        return 0
    if inverted:
        higher = sum(1 for c in cohort if c < value)
    else:
        higher = sum(1 for c in cohort if c > value)
    return higher + 1


def _build_lede(bars: list[dict[str, Any]]) -> str:
    if not bars:
        return ""
    top = [b for b in bars if b["percentile"] >= 80]
    bot = [b for b in bars if b["percentile"] <= 30]
    parts: list[str] = []
    if top:
        b = top[0]
        parts.append(
            f"<strong>Elite</strong>: {escape(b['label'].lower())} ({int(b['percentile'])}th)"
        )
    if len(top) > 1:
        b = top[1]
        parts.append(
            f"<strong>Strength</strong>: {escape(b['label'].lower())} ({int(b['percentile'])}th)"
        )
    if bot:
        b = bot[-1]
        parts.append(
            f"<strong>Concern</strong>: {escape(b['label'].lower())} ({int(b['percentile'])}th)"
        )
    if not parts:
        return "Production sits in the middle of the position cohort across the board."
    return ". ".join(parts) + "."


def render_box_savant(
    db, player_id: int | None, season_year: int | None,
    position: str | None = None,
) -> str:
    if db is None or player_id is None or season_year is None:
        return ""
    bars = compute_savant_bars(db, int(player_id), int(season_year), position or "")
    if not bars:
        return (
            '<section class="box-savant box-savant--empty" '
            'data-module="box-savant" data-state="empty">'
            'Box-score Savant card waits for a season-stat snapshot above the '
            'cohort floor. Returns once enough box-score volume lands.'
            '</section>'
        )

    bar_html_parts: list[str] = []
    for b in bars:
        track_cls = "box-savant__bar-track--inverted" if b["inverted"] else ""
        pct = b["percentile"]
        bar_html_parts.append(
            '<div class="box-savant__bar-row">'
            f'<div class="box-savant__bar-label">{escape(b["label"])}'
            f'<small>#{b["rank"]} / {b["cohort_size"]} &middot; {int(round(pct))}th pct</small></div>'
            f'<div class="box-savant__bar-track {track_cls}">'
            f'<span class="box-savant__bar-pin" style="left:{pct:.1f}%"></span>'
            '</div>'
            f'<div class="box-savant__bar-value">{escape(b["value_fmt"])}'
            f'<small>{escape(b["category"][:4])}</small></div>'
            '</div>'
        )
    bars_html = "".join(bar_html_parts)
    lede = _build_lede(bars)
    n_metrics = len(bars)

    return (
        '<section class="box-savant" '
        f'data-module="box-savant" data-state="ready" data-metrics="{n_metrics}">'
        '<header class="box-savant__head">'
        '<div>'
        '<p class="box-savant__eyebrow">Savant &middot; Box-rate percentiles</p>'
        f'<p class="box-savant__title">Where this profile ranks vs the {escape(position or "position")} cohort</p>'
        '</div>'
        f'<span class="box-savant__meta">{n_metrics} metrics &middot; season cumulative</span>'
        '</header>'
        f'<p class="box-savant__lede">{lede}</p>'
        f'<div class="box-savant__bars">{bars_html}</div>'
        '<p class="box-savant__footnote">Percentiles versus same-position peers above the snap floor '
        'for this season. EPA / CPOE / aDOT / pressure splits arrive when CFBD play-by-play '
        'is wired — these bars use box-score rates in the meantime.</p>'
        '</section>'
    )
