"""Savant-card data loader.

Pulls CFBD tier-2 advanced stats already ingested into ``team_game_advanced_stats``
and computes four-peer-set percentiles (FBS / Power-4 / Conference / All-time
for this program, 2014+) for each of 13 metrics. Writes to ``team_savant_weekly``.

Design decisions:

* **No CFBD API call.** The data is already in the DB (18k rows,
  2014+ coverage). Pulling live would duplicate what the ingest pipeline
  has already done.
* **Season-to-date mean** is the raw_value. CFBD's game-level rows are
  per-game stats that already reflect opponent adjustment upstream; the
  season mean is the simplest fair aggregate for a "Savant card".
* **Peer distribution = every team-season's mean** in the corresponding
  bucket (FBS / P4 / Conference / this-program's-history). Percentile is
  the rank of the team's value within that distribution, rescaled 0-100.
* **Defense metrics are inverted** before percentile computation so that
  100 always means "elite" — the renderer doesn't have to know which way
  is up.
* **Power-4 definition**: SEC + Big Ten + ACC + Big 12 + FBS Independents.
  Conferences are read from the ``conferences`` table via
  ``teams.current_conference_id``.

Run: ``python manage.py refresh-savant`` (CLI wrapper added separately).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable

# --------------------------------------------------------------------------
# Metric registry — the 13 bars rendered on the Savant card.
# Each entry maps the underlying ``team_game_advanced_stats`` column to a
# display label + group (offense / defense / special) + inversion flag.
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class SavantMetric:
    key: str
    label: str
    group: str              # 'offense' | 'defense' | 'special'
    column: str             # column in team_game_advanced_stats
    is_inverted: bool       # True if lower raw = better (defense)


SAVANT_METRICS: tuple[SavantMetric, ...] = (
    # Offense (5) --------------------------------------------------------
    SavantMetric("epa_play",        "EPA / play",            "offense", "offense_ppa",          False),
    SavantMetric("success_off",     "Success Rate",          "offense", "success_rate_off",     False),
    SavantMetric("explosive_off",   "Explosive Plays",       "offense", "explosiveness_off",    False),
    SavantMetric("rushing_epa_off", "Rushing EPA",           "offense", "rushing_ppa_off",      False),
    SavantMetric("finishing_off",   "Red-Zone Finish",       "offense", "finishing_drives_off", False),
    # Defense (5, inverted) ---------------------------------------------
    SavantMetric("epa_allowed",     "EPA Allowed",           "defense", "defense_ppa",          True),
    SavantMetric("success_def",     "Success Rate Allowed",  "defense", "success_rate_def",     True),
    SavantMetric("explosive_def",   "Explosive Plays Allowed","defense","explosiveness_def",    True),
    SavantMetric("passing_epa_def", "Passing EPA Allowed",   "defense", "passing_ppa_def",      True),
    SavantMetric("finishing_def",   "Red-Zone Defense",      "defense", "finishing_drives_def", True),
    # Special situations (3) --------------------------------------------
    SavantMetric("field_pos_off",   "Field Position (O)",    "special", "field_position_off",   False),
    SavantMetric("passing_epa_off", "Passing EPA",           "special", "passing_ppa_off",      False),
    SavantMetric("rushing_epa_def", "Rushing EPA Allowed",   "special", "rushing_ppa_def",      True),
)


# --------------------------------------------------------------------------
# Peer sets
# --------------------------------------------------------------------------

P4_CONFERENCE_NAMES: frozenset[str] = frozenset({
    "Southeastern Conference", "SEC",
    "Big Ten Conference", "Big Ten",
    "Atlantic Coast Conference", "ACC",
    "Big 12 Conference", "Big 12",
    "FBS Independents",
})


def _get_conference_name(conn: sqlite3.Connection, team_id: int) -> str | None:
    row = conn.execute(
        """
        select c.conference_name
        from teams t
        left join conferences c on c.conference_id = t.current_conference_id
        where t.team_id = :tid
        """,
        {"tid": team_id},
    ).fetchone()
    return row[0] if row and row[0] else None


def _team_season_means(
    conn: sqlite3.Connection,
    season_year: int,
    column: str,
    *,
    min_games: int = 3,
    level_code: str = "FBS",
) -> dict[int, tuple[float, int]]:
    """Return {team_id: (mean, n_games)} for all FBS teams in season_year."""
    rows = conn.execute(
        f"""
        select tgas.team_id,
               avg(tgas.{column}) as mean_val,
               count(*) as n_games
        from team_game_advanced_stats tgas
        join games g on g.game_id = tgas.game_id
        join teams t on t.team_id = tgas.team_id
        where g.season_year = :season
          and t.level_code = :lvl
          and tgas.{column} is not null
        group by tgas.team_id
        having count(*) >= :min_games
        """,
        {"season": season_year, "lvl": level_code, "min_games": min_games},
    ).fetchall()
    return {int(r[0]): (float(r[1]), int(r[2])) for r in rows}


def _program_alltime_means(
    conn: sqlite3.Connection,
    team_id: int,
    column: str,
    *,
    since_year: int = 2014,
    min_games: int = 3,
) -> list[float]:
    """Return this program's per-season means from since_year forward."""
    rows = conn.execute(
        f"""
        select g.season_year, avg(tgas.{column}) as mean_val, count(*) as n
        from team_game_advanced_stats tgas
        join games g on g.game_id = tgas.game_id
        where tgas.team_id = :tid
          and g.season_year >= :yr
          and tgas.{column} is not null
        group by g.season_year
        having count(*) >= :min_games
        """,
        {"tid": team_id, "yr": since_year, "min_games": min_games},
    ).fetchall()
    return [float(r[1]) for r in rows]


def _p4_team_ids(conn: sqlite3.Connection) -> set[int]:
    rows = conn.execute(
        """
        select t.team_id
        from teams t
        join conferences c on c.conference_id = t.current_conference_id
        where t.level_code = 'FBS'
          and c.conference_name in (
              'Southeastern Conference','SEC',
              'Big Ten Conference','Big Ten',
              'Atlantic Coast Conference','ACC',
              'Big 12 Conference','Big 12',
              'FBS Independents'
          )
        """
    ).fetchall()
    return {int(r[0]) for r in rows}


def _conference_team_ids(conn: sqlite3.Connection, conference_name: str | None) -> set[int]:
    if not conference_name:
        return set()
    rows = conn.execute(
        """
        select t.team_id
        from teams t
        join conferences c on c.conference_id = t.current_conference_id
        where c.conference_name = :cn and t.level_code = 'FBS'
        """,
        {"cn": conference_name},
    ).fetchall()
    return {int(r[0]) for r in rows}


def _percentile(value: float, distribution: Iterable[float], *, invert: bool) -> float | None:
    """Return percentile 0..100 of value within distribution.

    invert=True means "lower raw is better" — i.e. we rank ascendingly
    instead of descendingly, so defensive EPA allowed of -0.2 scores ~95
    while +0.2 scores ~5.
    """
    dist = [float(v) for v in distribution if v is not None]
    if not dist:
        return None
    # Rank position: count of peers strictly worse than or tied with.
    if invert:
        better = sum(1 for d in dist if d > value)  # higher = worse
        tied = sum(1 for d in dist if d == value)
    else:
        better = sum(1 for d in dist if d < value)  # lower = worse
        tied = sum(1 for d in dist if d == value)
    # Midrank convention
    rank = better + (tied / 2.0)
    pct = (rank / len(dist)) * 100.0
    return max(0.0, min(100.0, pct))


# --------------------------------------------------------------------------
# Top-level computation
# --------------------------------------------------------------------------

def compute_savant_row(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    metric: SavantMetric,
    *,
    p4_ids: set[int] | None = None,
    conf_ids: set[int] | None = None,
) -> dict[str, Any] | None:
    """Compute one row for team_savant_weekly — team × season × metric."""
    fbs_means = _team_season_means(conn, season_year, metric.column)
    if team_id not in fbs_means:
        return None

    raw, n_games = fbs_means[team_id]

    p4_dist = [v for tid, (v, _) in fbs_means.items() if tid in (p4_ids or set())]
    conf_dist = [v for tid, (v, _) in fbs_means.items() if tid in (conf_ids or set())]
    fbs_dist = [v for (v, _) in fbs_means.values()]
    alltime_dist = _program_alltime_means(conn, team_id, metric.column)

    return {
        "team_id": team_id,
        "season_year": season_year,
        "week": 0,
        "metric_key": metric.key,
        "metric_group": metric.group,
        "metric_label": metric.label,
        "is_inverted": 1 if metric.is_inverted else 0,
        "raw_value": raw,
        "pct_vs_fbs": _percentile(raw, fbs_dist, invert=metric.is_inverted),
        "pct_vs_p4": _percentile(raw, p4_dist, invert=metric.is_inverted),
        "pct_vs_conf": _percentile(raw, conf_dist, invert=metric.is_inverted),
        "pct_vs_alltime": _percentile(raw, alltime_dist, invert=metric.is_inverted),
        "sample_size": n_games,
        "peer_set_size_fbs": len(fbs_dist),
        "peer_set_size_p4": len(p4_dist),
        "peer_set_size_conf": len(conf_dist),
        "peer_set_size_alltime": len(alltime_dist),
    }


def refresh_team_savant(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
) -> int:
    """Recompute every metric row for (team, season, week=0). Returns count written."""
    p4_ids = _p4_team_ids(conn)
    conf_name = _get_conference_name(conn, team_id)
    conf_ids = _conference_team_ids(conn, conf_name)

    written = 0
    for metric in SAVANT_METRICS:
        row = compute_savant_row(
            conn, team_id, season_year, metric,
            p4_ids=p4_ids, conf_ids=conf_ids,
        )
        if row is None:
            continue
        conn.execute(
            """
            insert into team_savant_weekly (
                team_id, season_year, week, metric_key, metric_group, metric_label,
                is_inverted, raw_value,
                pct_vs_fbs, pct_vs_p4, pct_vs_conf, pct_vs_alltime,
                sample_size,
                peer_set_size_fbs, peer_set_size_p4,
                peer_set_size_conf, peer_set_size_alltime,
                generated_at_utc
            ) values (
                :team_id, :season_year, :week, :metric_key, :metric_group, :metric_label,
                :is_inverted, :raw_value,
                :pct_vs_fbs, :pct_vs_p4, :pct_vs_conf, :pct_vs_alltime,
                :sample_size,
                :peer_set_size_fbs, :peer_set_size_p4,
                :peer_set_size_conf, :peer_set_size_alltime,
                current_timestamp
            )
            on conflict(team_id, season_year, week, metric_key) do update set
                metric_group = excluded.metric_group,
                metric_label = excluded.metric_label,
                is_inverted = excluded.is_inverted,
                raw_value = excluded.raw_value,
                pct_vs_fbs = excluded.pct_vs_fbs,
                pct_vs_p4 = excluded.pct_vs_p4,
                pct_vs_conf = excluded.pct_vs_conf,
                pct_vs_alltime = excluded.pct_vs_alltime,
                sample_size = excluded.sample_size,
                peer_set_size_fbs = excluded.peer_set_size_fbs,
                peer_set_size_p4 = excluded.peer_set_size_p4,
                peer_set_size_conf = excluded.peer_set_size_conf,
                peer_set_size_alltime = excluded.peer_set_size_alltime,
                generated_at_utc = current_timestamp
            """,
            row,
        )
        written += 1
    return written


def fetch_savant_rows(
    conn: sqlite3.Connection,
    team_id: int,
    season_year: int,
    week: int = 0,
) -> list[dict[str, Any]]:
    """Read back all 13 metrics for rendering."""
    cur = conn.execute(
        """
        select metric_key, metric_group, metric_label, is_inverted, raw_value,
               pct_vs_fbs, pct_vs_p4, pct_vs_conf, pct_vs_alltime,
               sample_size,
               peer_set_size_fbs, peer_set_size_p4,
               peer_set_size_conf, peer_set_size_alltime
        from team_savant_weekly
        where team_id = :tid and season_year = :s and week = :w
        """,
        {"tid": team_id, "s": season_year, "w": week},
    )
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    # Preserve the registry's order so the renderer gets offense→defense→special
    order = {m.key: i for i, m in enumerate(SAVANT_METRICS)}
    rows.sort(key=lambda r: order.get(r["metric_key"], 999))
    return rows
