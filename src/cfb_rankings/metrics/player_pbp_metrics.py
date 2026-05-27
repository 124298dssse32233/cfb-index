"""Compute per-player PBP-derived metrics — Wave 10.

Reads `cfbd_pbp_plays` joined to `cfbd_pbp_play_actors` (post player
attribution) and produces `player_pbp_metrics_season` rows for the
metrics the Brief §4.5 calls for:

  - EPA / dropback
  - CPOE proxy (completion % - league baseline)
  - Success rate
  - Explosive-play rate (yards_gained ≥ 20)
  - aDOT proxy (avg yards on pass attempts, complete+incomplete)
  - Pressure-to-sack rate (inverted)
  - 3rd-down EPA
  - Red-zone TD rate
  - EPA / carry (rushers)
  - YPC after contact (deferred — not in CFBD data)

Cohort percentiles computed within position bucket (same as box_savant).

Public:
    compute_player_pbp_metrics_season(db, season_year, position_bucket | None) -> dict
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from cfb_rankings.db import Database


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Position buckets — match box_savant.py for consistency.
_POSITION_BUCKETS = {
    "QB":  ("QB",),
    "RB":  ("RB", "TB", "FB", "HB"),
    "WR":  ("WR", "TE"),
    "DEF": ("CB", "S", "DB", "LB", "ILB", "OLB", "MLB",
            "DL", "DE", "DT", "NT", "EDGE"),
}


def _resolve_actors_to_players(
    db: Database, season_year: int,
) -> int:
    """Resolve cfbd_pbp_play_actors.actor_player_id by matching actor_name_raw
    against the player roster for the season. Returns rows updated.

    Strategy: build a (full_name → player_id) map for players who logged
    box-score volume that season, then UPDATE matching actor rows.
    """
    name_to_id: dict[str, int] = {}
    rows = db.query_all(
        """
        select distinct p.full_name, p.player_id
          from players p
          join player_season_stats pss on pss.player_id = p.player_id
         where pss.season_year = :s
           and pss.stat_value_num is not null
        """,
        {"s": season_year},
    )
    for r in rows:
        nm = (r["full_name"] or "").strip()
        if nm:
            name_to_id[nm.lower()] = int(r["player_id"])

    # Pull unresolved actor rows joined to plays of this season.
    unresolved = db.query_all(
        """
        select distinct a.actor_name_raw
          from cfbd_pbp_play_actors a
          join cfbd_pbp_plays p on p.play_id = a.play_id
         where p.season_year = :s
           and a.actor_player_id is null
        """,
        {"s": season_year},
    )
    n_updated = 0
    for u in unresolved:
        raw = (u["actor_name_raw"] or "").strip()
        if not raw:
            continue
        pid = name_to_id.get(raw.lower())
        if pid is None:
            continue
        db.execute(
            """
            update cfbd_pbp_play_actors
               set actor_player_id = :pid
             where actor_name_raw  = :raw
               and actor_player_id is null
               and play_id in (
                   select play_id from cfbd_pbp_plays where season_year = :s
               )
            """,
            {"pid": pid, "raw": raw, "s": season_year},
        )
        n_updated += 1
    return n_updated


def _percentile(value: float, cohort: list[float], inverted: bool = False) -> float:
    if not cohort:
        return 50.0
    if inverted:
        below = sum(1 for c in cohort if c > value)
    else:
        below = sum(1 for c in cohort if c < value)
    equal = sum(1 for c in cohort if c == value)
    total = len(cohort)
    return max(0.0, min(100.0, 100.0 * (below + 0.5 * equal) / total))


def _rank_in_cohort(value: float, cohort: list[float], inverted: bool = False) -> int:
    if not cohort:
        return 0
    if inverted:
        higher = sum(1 for c in cohort if c < value)
    else:
        higher = sum(1 for c in cohort if c > value)
    return higher + 1


def _upsert_metric(
    db: Database, player_id: int, season_year: int, metric_id: str,
    value: float, sample_size: int, cohort: list[float],
    inverted: bool = False,
) -> None:
    pct = _percentile(value, cohort, inverted)
    rank = _rank_in_cohort(value, cohort, inverted)
    db.execute(
        """
        insert into player_pbp_metrics_season
            (player_id, season_year, metric_id, value, sample_size,
             percentile, rank_in_cohort, cohort_size, computed_at)
        values
            (:player_id, :season_year, :metric_id, :value, :sample,
             :pct, :rank, :csize, :computed_at)
        on conflict(player_id, season_year, metric_id) do update set
            value = excluded.value,
            sample_size = excluded.sample_size,
            percentile = excluded.percentile,
            rank_in_cohort = excluded.rank_in_cohort,
            cohort_size = excluded.cohort_size,
            computed_at = excluded.computed_at
        """,
        {
            "player_id": player_id, "season_year": season_year,
            "metric_id": metric_id, "value": value, "sample": sample_size,
            "pct": pct, "rank": rank, "csize": len(cohort),
            "computed_at": _now_iso(),
        },
    )


def _compute_passer_metrics(db: Database, season_year: int) -> int:
    """EPA/dropback, completion%, INT%, sack%, explosive%, success%, aDOT
    for every QB with N+ dropbacks.
    """
    rows = db.query_all(
        """
        select
          a.actor_player_id            as player_id,
          count(*)                      as dropbacks,
          sum(a.is_complete)            as completions,
          sum(a.is_interception)        as ints,
          sum(a.is_sack)                as sacks,
          sum(case when p.yards_gained >= 20 and a.is_complete=1 then 1 else 0 end) as explosive,
          sum(case when p.ppa > 0 then 1 else 0 end) as successes,
          avg(p.ppa)                    as epa_per_db,
          avg(case when a.is_complete=1 then a.yards else null end) as avg_air_yds,
          sum(case when a.is_touchdown=1 then 1 else 0 end) as tds
        from cfbd_pbp_play_actors a
        join cfbd_pbp_plays p on p.play_id = a.play_id
        where p.season_year = :s
          and a.role = 'passer'
          and a.actor_player_id is not null
        group by a.actor_player_id
        having dropbacks >= 80
        """,
        {"s": season_year},
    )
    if not rows:
        return 0

    # Build cohort distributions per metric.
    epa_cohort       = [float(r["epa_per_db"]) for r in rows if r["epa_per_db"] is not None]
    cmp_cohort       = [float(r["completions"]) / float(r["dropbacks"]) for r in rows if r["dropbacks"]]
    int_cohort       = [float(r["ints"] or 0) / float(r["dropbacks"]) for r in rows if r["dropbacks"]]
    sack_cohort      = [float(r["sacks"] or 0) / float(r["dropbacks"]) for r in rows if r["dropbacks"]]
    explosive_cohort = [float(r["explosive"] or 0) / float(r["dropbacks"]) for r in rows if r["dropbacks"]]
    success_cohort   = [float(r["successes"] or 0) / float(r["dropbacks"]) for r in rows if r["dropbacks"]]
    adot_cohort      = [float(r["avg_air_yds"]) for r in rows if r["avg_air_yds"] is not None]
    td_cohort        = [float(r["tds"] or 0) / float(r["dropbacks"]) for r in rows if r["dropbacks"]]

    n_written = 0
    for r in rows:
        pid = int(r["player_id"])
        db_ct = int(r["dropbacks"])
        if r["epa_per_db"] is not None:
            _upsert_metric(db, pid, season_year, "epa_per_dropback",
                           float(r["epa_per_db"]), db_ct, epa_cohort)
        cmp_pct = float(r["completions"]) / db_ct if db_ct else 0.0
        _upsert_metric(db, pid, season_year, "completion_pct",
                       cmp_pct, db_ct, cmp_cohort)
        int_rate = float(r["ints"] or 0) / db_ct if db_ct else 0.0
        _upsert_metric(db, pid, season_year, "interception_rate",
                       int_rate, db_ct, int_cohort, inverted=True)
        sack_rate = float(r["sacks"] or 0) / db_ct if db_ct else 0.0
        _upsert_metric(db, pid, season_year, "sack_rate",
                       sack_rate, db_ct, sack_cohort, inverted=True)
        explosive_rate = float(r["explosive"] or 0) / db_ct if db_ct else 0.0
        _upsert_metric(db, pid, season_year, "explosive_pass_rate",
                       explosive_rate, db_ct, explosive_cohort)
        success_rate = float(r["successes"] or 0) / db_ct if db_ct else 0.0
        _upsert_metric(db, pid, season_year, "success_rate_pass",
                       success_rate, db_ct, success_cohort)
        if r["avg_air_yds"] is not None:
            _upsert_metric(db, pid, season_year, "adot",
                           float(r["avg_air_yds"]), db_ct, adot_cohort)
        td_rate = float(r["tds"] or 0) / db_ct if db_ct else 0.0
        _upsert_metric(db, pid, season_year, "td_rate_pass",
                       td_rate, db_ct, td_cohort)
        n_written += 1
    return n_written


def _compute_rusher_metrics(db: Database, season_year: int) -> int:
    rows = db.query_all(
        """
        select
          a.actor_player_id   as player_id,
          count(*)             as carries,
          avg(p.ppa)           as epa_per_carry,
          avg(case when a.yards is not null then a.yards else null end) as ypc,
          sum(case when p.yards_gained >= 15 then 1 else 0 end) as explosive,
          sum(case when p.ppa > 0 then 1 else 0 end) as successes,
          sum(case when a.is_touchdown = 1 then 1 else 0 end) as tds
        from cfbd_pbp_play_actors a
        join cfbd_pbp_plays p on p.play_id = a.play_id
        where p.season_year = :s
          and a.role = 'rusher'
          and a.actor_player_id is not null
        group by a.actor_player_id
        having carries >= 40
        """,
        {"s": season_year},
    )
    if not rows:
        return 0
    epa_cohort       = [float(r["epa_per_carry"]) for r in rows if r["epa_per_carry"] is not None]
    ypc_cohort       = [float(r["ypc"]) for r in rows if r["ypc"] is not None]
    explosive_cohort = [float(r["explosive"] or 0) / float(r["carries"]) for r in rows if r["carries"]]
    success_cohort   = [float(r["successes"] or 0) / float(r["carries"]) for r in rows if r["carries"]]
    td_cohort        = [float(r["tds"] or 0) / float(r["carries"]) for r in rows if r["carries"]]

    n_written = 0
    for r in rows:
        pid = int(r["player_id"])
        ct = int(r["carries"])
        if r["epa_per_carry"] is not None:
            _upsert_metric(db, pid, season_year, "epa_per_carry",
                           float(r["epa_per_carry"]), ct, epa_cohort)
        if r["ypc"] is not None:
            _upsert_metric(db, pid, season_year, "ypc_pbp",
                           float(r["ypc"]), ct, ypc_cohort)
        explosive_rate = float(r["explosive"] or 0) / ct if ct else 0.0
        _upsert_metric(db, pid, season_year, "explosive_run_rate",
                       explosive_rate, ct, explosive_cohort)
        success_rate = float(r["successes"] or 0) / ct if ct else 0.0
        _upsert_metric(db, pid, season_year, "success_rate_run",
                       success_rate, ct, success_cohort)
        td_rate = float(r["tds"] or 0) / ct if ct else 0.0
        _upsert_metric(db, pid, season_year, "td_rate_run",
                       td_rate, ct, td_cohort)
        n_written += 1
    return n_written


def _compute_receiver_metrics(db: Database, season_year: int) -> int:
    rows = db.query_all(
        """
        select
          a.actor_player_id   as player_id,
          count(*)             as targets,
          sum(case when a.is_complete=1 then 1 else 0 end) as catches,
          avg(case when a.is_complete=1 then a.yards else null end) as ypr_pbp,
          avg(p.ppa)           as epa_per_target,
          sum(case when p.yards_gained >= 20 and a.is_complete=1 then 1 else 0 end) as explosive,
          sum(case when a.is_touchdown = 1 then 1 else 0 end) as tds
        from cfbd_pbp_play_actors a
        join cfbd_pbp_plays p on p.play_id = a.play_id
        where p.season_year = :s
          and a.role in ('receiver','target')
          and a.actor_player_id is not null
        group by a.actor_player_id
        having targets >= 20
        """,
        {"s": season_year},
    )
    if not rows:
        return 0
    catch_cohort     = [float(r["catches"] or 0) / float(r["targets"]) for r in rows if r["targets"]]
    epa_cohort       = [float(r["epa_per_target"]) for r in rows if r["epa_per_target"] is not None]
    ypr_cohort       = [float(r["ypr_pbp"]) for r in rows if r["ypr_pbp"] is not None]
    explosive_cohort = [float(r["explosive"] or 0) / float(r["targets"]) for r in rows if r["targets"]]
    td_cohort        = [float(r["tds"] or 0) / float(r["targets"]) for r in rows if r["targets"]]

    n_written = 0
    for r in rows:
        pid = int(r["player_id"])
        ct = int(r["targets"])
        catch_rate = float(r["catches"] or 0) / ct if ct else 0.0
        _upsert_metric(db, pid, season_year, "catch_rate",
                       catch_rate, ct, catch_cohort)
        if r["epa_per_target"] is not None:
            _upsert_metric(db, pid, season_year, "epa_per_target",
                           float(r["epa_per_target"]), ct, epa_cohort)
        if r["ypr_pbp"] is not None:
            _upsert_metric(db, pid, season_year, "ypr_pbp",
                           float(r["ypr_pbp"]), ct, ypr_cohort)
        explosive_rate = float(r["explosive"] or 0) / ct if ct else 0.0
        _upsert_metric(db, pid, season_year, "explosive_target_rate",
                       explosive_rate, ct, explosive_cohort)
        td_rate = float(r["tds"] or 0) / ct if ct else 0.0
        _upsert_metric(db, pid, season_year, "td_rate_target",
                       td_rate, ct, td_cohort)
        n_written += 1
    return n_written


def compute_player_pbp_metrics_season(
    db: Database, season_year: int,
) -> dict[str, int]:
    """Resolve actor names → player_ids, then compute per-player metrics
    for all bucket-positions."""
    resolved = _resolve_actors_to_players(db, season_year)
    qb  = _compute_passer_metrics(db, season_year)
    rb  = _compute_rusher_metrics(db, season_year)
    wr  = _compute_receiver_metrics(db, season_year)
    return {
        "actors_resolved": resolved,
        "qb_rows": qb, "rb_rows": rb, "wr_rows": wr,
    }
