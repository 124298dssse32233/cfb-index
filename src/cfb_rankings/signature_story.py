"""Signature Story engine — player-page headline-stat picker.

For any player-season-(optional week), surface ONE stat that defines the
player's story, with cohort rank + percentile + a narrative line. Picks are
scored deterministically from seeds/signature_story_metrics.yaml — every
result is auditable from the seed file + the raw cohort data.

Public entry points:

    fetch_player_signature_story(db, player_id, season_year, week=None)
        -> dict with the contract shape from CLAUDE_CODE_KICKOFF_PLAYER_DATA.md.

    build_candidate_scoreboard(db, player_id, season_year, week=None)
        -> dict[metric_id, candidate_eval]; used by the CLI to expose the
           full ranking trace (who won, who tied, why). Signature Story
           stays explainable by making the scoreboard printable.

Selection algorithm (kickoff §Feature A):

    1. Determine player position from `players.position`.
    2. For each seed metric with matching position:
       a. Run sql_query_template → (value, sample_size).
       b. Skip if value is None OR sample_size < min_volume.
       c. Run cohort_sql_template → cohort members and their values.
       d. Skip if cohort has < cohort.min_qualifying_members.
       e. Compute rank and percentile (inverting when higher_is_better=False).
       f. score = percentile_unit * log(max(sample_size, 2)) * narrative_weight
          where percentile_unit is 0..1 (not 0..100).
    3. Pick highest-scoring candidate.
    4. If no candidate qualifies, return shape-accurate skeleton.

The skeleton path is mandatory: every player page must get a dict with
the same keys so the template doesn't branch on has_data=True/False-with-
different-shapes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import math
from pathlib import Path
from typing import Any

import yaml

from cfb_rankings.db import Database


SEED_PATH = Path(__file__).resolve().parent.parent.parent / "seeds" / "signature_story_metrics.yaml"

# Placeholder keys in the SQL templates. All expand to the cohort's
# `sql_filter` text verbatim — the three names exist so the seed author
# can signal which alias the filter is meant to match (pvm vs. pss.team etc.),
# but the substitution is the same string for all.
FORMAT_PLACEHOLDERS = {"cohort_filter", "cohort_filter_pvm", "cohort_filter_pvm_or_team"}


# ---------------------------------------------------------------------------
# Seed loading
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Cohort:
    id: str
    label: str
    description: str
    sql_filter: str
    min_qualifying_members: int


@dataclass(frozen=True)
class Metric:
    id: str
    label: str
    unit: str
    higher_is_better: bool
    position: str
    cohort: str
    min_volume: float
    narrative_weight: float
    narrative_template: str
    sql_query_template: str
    cohort_sql_template: str


@dataclass
class _Seed:
    cohorts: dict[str, Cohort] = field(default_factory=dict)
    metrics: list[Metric] = field(default_factory=list)


@lru_cache(maxsize=1)
def _load_seed(path: str = str(SEED_PATH)) -> _Seed:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    seed = _Seed()
    for c in raw.get("cohorts") or []:
        seed.cohorts[c["id"]] = Cohort(
            id=c["id"],
            label=c["label"],
            description=c.get("description", ""),
            sql_filter=c["sql_filter"].strip(),
            min_qualifying_members=int(c["min_qualifying_members"]),
        )
    for m in raw.get("metrics") or []:
        seed.metrics.append(
            Metric(
                id=m["id"],
                label=m["label"],
                unit=m["unit"],
                higher_is_better=bool(m["higher_is_better"]),
                position=m["position"],
                cohort=m["cohort"],
                min_volume=float(m["min_volume"]),
                narrative_weight=float(m["narrative_weight"]),
                narrative_template=m["narrative_template"].strip(),
                sql_query_template=m["sql_query_template"],
                cohort_sql_template=m["cohort_sql_template"],
            )
        )
    return seed


def reload_seed() -> None:
    """Test hook: drop the cached seed so the next call re-reads the YAML."""
    _load_seed.cache_clear()


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


@dataclass
class CandidateEval:
    metric: Metric
    value: float
    sample_size: float
    rank: int
    cohort_size: int
    percentile: float  # 0..100, already inverted for higher_is_better=False
    score: float
    cohort_rows: list[dict[str, Any]]


def _apply_placeholders(sql: str, cohort: Cohort) -> str:
    filled = sql
    for key in FORMAT_PLACEHOLDERS:
        filled = filled.replace("{" + key + "}", cohort.sql_filter)
    return filled


def _rank_and_percentile(
    cohort_rows: list[dict[str, Any]],
    player_id: int,
    *,
    higher_is_better: bool,
) -> tuple[int, int, float] | None:
    """Return (rank, cohort_size, percentile_0_to_100) or None if player absent.

    Rank is 1-indexed. Ties share the best rank (standard competition ranking).
    Percentile is 0..100 where 100 = best performer in the cohort.
    """
    values = [
        (int(r["player_id"]), float(r["value"]))
        for r in cohort_rows
        if r.get("value") is not None
    ]
    if not values:
        return None
    # Sort so rank 1 is the best performer.
    values.sort(key=lambda pv: pv[1], reverse=higher_is_better)
    cohort_size = len(values)

    player_value: float | None = None
    for pid, v in values:
        if pid == player_id:
            player_value = v
            break
    if player_value is None:
        return None

    # Competition ranking: count strictly-better players, then +1.
    better = sum(
        1
        for _, v in values
        if (higher_is_better and v > player_value) or (not higher_is_better and v < player_value)
    )
    rank = better + 1

    # Percentile_0_to_100 where 100 = best. Use (cohort_size - rank) / (cohort_size - 1).
    if cohort_size == 1:
        percentile = 100.0
    else:
        percentile = ((cohort_size - rank) / (cohort_size - 1)) * 100.0
    return rank, cohort_size, percentile


def _score_candidate(
    metric: Metric,
    value: float,
    sample_size: float,
    percentile: float,
) -> float:
    """score = (percentile/100) * log(max(sample_size, 2)) * narrative_weight."""
    percentile_unit = max(0.0, min(1.0, percentile / 100.0))
    sample_factor = math.log(max(float(sample_size), 2.0))
    return percentile_unit * sample_factor * float(metric.narrative_weight)


def _fetch_player_position(db: Database, player_id: int) -> str | None:
    rows = db.query_all(
        "select position from players where player_id = %(player_id)s",
        {"player_id": player_id},
    )
    if not rows:
        return None
    return (rows[0].get("position") or "").strip() or None


def _evaluate_metric(
    db: Database,
    metric: Metric,
    cohort: Cohort,
    *,
    player_id: int,
    season_year: int,
    week: int | None,
) -> CandidateEval | None:
    """Run metric SQL for the player and cohort; return eval or None if ineligible."""
    params = {"player_id": player_id, "season_year": season_year, "week": week}

    # Player query first — cheaper. Skip cohort work if the player has no value.
    player_sql = _apply_placeholders(metric.sql_query_template, cohort)
    player_rows = db.query_all(player_sql, params)
    if not player_rows:
        return None
    value = player_rows[0].get("value")
    sample_size = player_rows[0].get("sample_size")
    if value is None or sample_size is None:
        return None
    if float(sample_size) < metric.min_volume:
        return None

    # Cohort query.
    cohort_sql = _apply_placeholders(metric.cohort_sql_template, cohort)
    cohort_params = {
        "season_year": season_year,
        "week": week,
        "min_volume": metric.min_volume,
    }
    cohort_rows = db.query_all(cohort_sql, cohort_params)
    if len(cohort_rows) < cohort.min_qualifying_members:
        return None

    ranked = _rank_and_percentile(
        cohort_rows,
        player_id,
        higher_is_better=metric.higher_is_better,
    )
    if ranked is None:
        return None
    rank, cohort_size, percentile = ranked

    score = _score_candidate(metric, float(value), float(sample_size), percentile)
    return CandidateEval(
        metric=metric,
        value=float(value),
        sample_size=float(sample_size),
        rank=rank,
        cohort_size=cohort_size,
        percentile=percentile,
        score=score,
        cohort_rows=cohort_rows,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_candidate_scoreboard(
    db: Database,
    player_id: int,
    season_year: int,
    week: int | None = None,
) -> list[CandidateEval]:
    """Evaluate every position-matching metric for the player.

    Returned list is sorted by score descending. Metrics the player failed to
    qualify for (below min_volume, thin cohort, missing from cohort rows) are
    dropped — they do not appear in the scoreboard.
    """
    seed = _load_seed()
    position = _fetch_player_position(db, player_id)
    if position is None:
        return []

    evals: list[CandidateEval] = []
    for metric in seed.metrics:
        if metric.position != position:
            continue
        cohort = seed.cohorts.get(metric.cohort)
        if cohort is None:
            continue
        result = _evaluate_metric(
            db,
            metric,
            cohort,
            player_id=player_id,
            season_year=season_year,
            week=week,
        )
        if result is not None:
            evals.append(result)

    evals.sort(key=lambda e: e.score, reverse=True)
    return evals


def compute_signature_story_index(
    db: Database,
    season_year: int,
    week: int | None = None,
) -> dict[int, dict[str, Any]]:
    """Batch-precompute Signature Stories for every qualifying player.

    Designed for the site-build hot path. Instead of N × M queries
    (N players × M metrics), we run one cohort SQL per metric (cached),
    then one cheap player SQL per candidate player. Non-candidates get
    no entry — callers should render the skeleton for them.

    Returned mapping is keyed on player_id. Only players who clear at
    least one metric's gates receive an entry; callers fall back to
    `_skeleton(...)` for anyone missing.
    """
    seed = _load_seed()

    # Candidate shortlist: any player with WEPA data OR any WR with enough
    # receptions for the WR stub metrics to have a chance.
    candidate_rows = db.query_all(
        """
        select distinct player_id from player_value_metrics
         where season_year = :season
        union
        select pss.player_id from player_season_stats pss
          join players p on p.player_id = pss.player_id
         where pss.season_year = :season
           and pss.category = 'receiving'
           and pss.stat_type = 'REC'
           and pss.stat_value_num >= 20
           and p.position = 'WR'
        """,
        {"season": season_year},
    )
    candidate_ids = {int(r["player_id"]) for r in candidate_rows}
    if not candidate_ids:
        return {}

    # Bulk-load player positions for quick filter.
    position_rows = db.query_all(
        "select player_id, position from players",
        {},
    )
    position_by_player = {
        int(r["player_id"]): (r.get("position") or "").strip()
        for r in position_rows
    }

    # Cache cohort rows keyed by metric.id.
    cohort_cache: dict[str, list[dict[str, Any]]] = {}
    cohort_size_cache: dict[str, int] = {}

    for metric in seed.metrics:
        cohort = seed.cohorts.get(metric.cohort)
        if cohort is None:
            continue
        sql = _apply_placeholders(metric.cohort_sql_template, cohort)
        rows = db.query_all(
            sql,
            {
                "season_year": season_year,
                "week": week,
                "min_volume": metric.min_volume,
            },
        )
        if len(rows) >= cohort.min_qualifying_members:
            cohort_cache[metric.id] = rows
            cohort_size_cache[metric.id] = len(rows)

    # Build a per-metric lookup: player_id -> (value, sample_size) from the
    # cached cohort rows. This avoids N × M single-row player queries during
    # the hot loop — every piece of data we need is already in cohort_cache.
    metric_player_lookup: dict[str, dict[int, tuple[float, float]]] = {}
    for metric_id, rows in cohort_cache.items():
        lookup: dict[int, tuple[float, float]] = {}
        for r in rows:
            pid = r.get("player_id")
            if pid is None or r.get("value") is None or r.get("sample_size") is None:
                continue
            lookup[int(pid)] = (float(r["value"]), float(r["sample_size"]))
        metric_player_lookup[metric_id] = lookup

    index: dict[int, dict[str, Any]] = {}
    updated_label = _format_week_label(season_year, week)

    # Cache ranking per (metric_id, player_id) to avoid recomputing if a player
    # appears in multiple metric evaluations. Ranking is O(cohort_size) though,
    # which is fine for cohorts ~60-100.
    for player_id in candidate_ids:
        position = position_by_player.get(player_id)
        if not position:
            continue
        evals: list[CandidateEval] = []
        for metric in seed.metrics:
            if metric.position != position:
                continue
            lookup = metric_player_lookup.get(metric.id)
            if not lookup:
                continue  # cohort didn't qualify globally — skip for everyone
            player_entry = lookup.get(player_id)
            if player_entry is None:
                continue  # player not in cohort (below volume gate for this metric)
            value, sample_size = player_entry
            if sample_size < metric.min_volume:
                continue
            cohort_rows = cohort_cache[metric.id]
            ranked = _rank_and_percentile(
                cohort_rows, player_id,
                higher_is_better=metric.higher_is_better,
            )
            if ranked is None:
                continue
            rank, cohort_size, percentile = ranked
            score = _score_candidate(metric, float(value), float(sample_size), percentile)
            evals.append(
                CandidateEval(
                    metric=metric,
                    value=float(value),
                    sample_size=float(sample_size),
                    rank=rank,
                    cohort_size=cohort_size,
                    percentile=percentile,
                    score=score,
                    cohort_rows=cohort_rows,
                )
            )
        if not evals:
            continue
        evals.sort(key=lambda e: e.score, reverse=True)
        winner = evals[0]
        index[player_id] = _story_from_winner(winner, evals, player_id, season_year, week, updated_label)

    return index


def _story_from_winner(
    winner: CandidateEval,
    scoreboard: list[CandidateEval],
    player_id: int,
    season_year: int,
    week: int | None,
    updated_label: str,
) -> dict[str, Any]:
    narrative = _render_narrative(winner)
    confidence = _confidence_for(winner)
    return {
        "has_story": True,
        "player_id": player_id,
        "season_year": season_year,
        "week": week,
        "headline_stat": {
            "metric_id": winner.metric.id,
            "label": winner.metric.label,
            "value": winner.value,
            "unit": winner.metric.unit,
            "rank": winner.rank,
            "rank_cohort": _rank_cohort_label(winner),
            "cohort_id": winner.metric.cohort,
            "cohort_size": winner.cohort_size,
            "percentile": round(winner.percentile, 1),
            "sample_size": winner.sample_size,
            "higher_is_better": winner.metric.higher_is_better,
        },
        "narrative": narrative,
        "supporting_chart": _supporting_chart(winner),
        "confidence": confidence,
        "updated_label": updated_label,
        "runners_up": [
            {
                "metric_id": e.metric.id,
                "label": e.metric.label,
                "rank": e.rank,
                "cohort_size": e.cohort_size,
                "percentile": round(e.percentile, 1),
                "score": round(e.score, 4),
            }
            for e in scoreboard[1:4]
        ],
    }


def fetch_player_signature_story(
    db: Database,
    player_id: int,
    season_year: int,
    week: int | None = None,
) -> dict[str, Any]:
    """Return the Signature Story payload for (player, season[, week]).

    Shape is stable whether or not a winning metric exists; an empty state
    returns the same keys with `has_story=False` and narrative-friendly copy.
    """
    scoreboard = build_candidate_scoreboard(db, player_id, season_year, week)
    updated_label = _format_week_label(season_year, week)

    if not scoreboard:
        return _skeleton(
            player_id=player_id,
            season_year=season_year,
            week=week,
            updated_label=updated_label,
        )

    winner = scoreboard[0]
    narrative = _render_narrative(winner)
    confidence = _confidence_for(winner)
    return {
        "has_story": True,
        "player_id": player_id,
        "season_year": season_year,
        "week": week,
        "headline_stat": {
            "metric_id": winner.metric.id,
            "label": winner.metric.label,
            "value": winner.value,
            "unit": winner.metric.unit,
            "rank": winner.rank,
            "rank_cohort": _rank_cohort_label(winner),
            "cohort_id": winner.metric.cohort,
            "cohort_size": winner.cohort_size,
            "percentile": round(winner.percentile, 1),
            "sample_size": winner.sample_size,
            "higher_is_better": winner.metric.higher_is_better,
        },
        "narrative": narrative,
        "supporting_chart": _supporting_chart(winner),
        "confidence": confidence,
        "updated_label": updated_label,
        "runners_up": [
            {
                "metric_id": e.metric.id,
                "label": e.metric.label,
                "rank": e.rank,
                "cohort_size": e.cohort_size,
                "percentile": round(e.percentile, 1),
                "score": round(e.score, 4),
            }
            for e in scoreboard[1:4]
        ],
    }


# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------


def _render_narrative(eval: CandidateEval) -> str:
    rank_ord = _ordinal(eval.rank)
    cumulative_value = eval.value * eval.sample_size
    tmpl = eval.metric.narrative_template
    try:
        text = tmpl.format(
            rank_ordinal=rank_ord,
            rank=eval.rank,
            cohort_size=eval.cohort_size,
            cohort_label=_load_seed().cohorts[eval.metric.cohort].label,
            value=eval.value,
            cumulative_value=cumulative_value,
            sample_size=int(eval.sample_size),
            min_volume=int(eval.metric.min_volume),
            unit=eval.metric.unit,
        )
    except (KeyError, ValueError):
        text = (
            f"{rank_ord} of {eval.cohort_size} {_load_seed().cohorts[eval.metric.cohort].label} "
            f"by {eval.metric.label.lower()}."
        )
    # Templates span lines in YAML for readability — fold to single line.
    return " ".join(text.split())


def _rank_cohort_label(eval: CandidateEval) -> str:
    cohort = _load_seed().cohorts[eval.metric.cohort]
    return f"{cohort.label}, min {int(eval.metric.min_volume)} {_volume_noun(eval.metric)}"


def _volume_noun(metric: Metric) -> str:
    mapping = {
        "wepa_passing_per_dropback": "dropbacks",
        "wepa_passing_total": "dropbacks",
        "wepa_combined_per_play": "touches",
        "qbr_season_avg": "games",
        "ypa": "attempts",
        "td_int_ratio": "attempts",
        "completion_pct": "attempts",
        "passing_yards_total": "attempts",
        "wepa_rushing_qb": "carries",
        "third_down_usage_share": "",
        "wepa_rushing_per_carry": "carries",
        "ypc": "carries",
        "rushing_yards_total": "carries",
        "receiving_yards_total": "receptions",
        "ypr": "receptions",
        "receiving_tds": "receptions",
    }
    return mapping.get(metric.id, "samples")


def _supporting_chart(eval: CandidateEval) -> dict[str, Any]:
    """A cohort strip: every qualifying cohort member's value, sorted best→worst."""
    data = [
        {
            "player_id": int(r["player_id"]),
            "player_name": r.get("player_name"),
            "team_name": r.get("team_name"),
            "value": float(r["value"]) if r.get("value") is not None else None,
            "sample_size": float(r["sample_size"]) if r.get("sample_size") is not None else None,
        }
        for r in eval.cohort_rows
        if r.get("value") is not None
    ]
    data.sort(key=lambda d: d["value"], reverse=eval.metric.higher_is_better)
    return {"type": "cohort_strip", "data": data}


def _confidence_for(eval: CandidateEval) -> dict[str, Any]:
    """Confidence label = function of sample_size and cohort_size."""
    sample_factor = min(1.0, eval.sample_size / max(eval.metric.min_volume * 2.0, 1.0))
    cohort_factor = min(1.0, eval.cohort_size / 50.0)
    score = round(0.6 * sample_factor + 0.4 * cohort_factor, 2)
    if score >= 0.85:
        label = "High"
    elif score >= 0.55:
        label = "Moderate"
    else:
        label = "Thin"
    return {
        "label": label,
        "score": score,
        "sample_size": int(eval.sample_size),
        "cohort_size": eval.cohort_size,
    }


def _skeleton(
    *,
    player_id: int,
    season_year: int,
    week: int | None,
    updated_label: str,
) -> dict[str, Any]:
    return {
        "has_story": False,
        "player_id": player_id,
        "season_year": season_year,
        "week": week,
        "headline_stat": None,
        "narrative": (
            "He hasn't written his page yet — we'll start filling it in "
            "when there are enough snaps to rank against his peers."
        ),
        "supporting_chart": {"type": "cohort_strip", "data": []},
        "confidence": {"label": "No signal", "score": 0.0, "sample_size": 0, "cohort_size": 0},
        "updated_label": updated_label,
        "runners_up": [],
    }


def _format_week_label(season_year: int, week: int | None) -> str:
    if week is None:
        return f"{season_year} season"
    return f"Through Week {week}, {season_year}"


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"#{n}"  # kickoff spec uses "#1" formatting not "1st"; keep both hooks.


# Alternative rendering available for narrative templates that want words.
def _ordinal_words(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
