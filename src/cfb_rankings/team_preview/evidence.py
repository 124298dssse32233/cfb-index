"""Deterministic evidence gathering for the team-preview truth layer.

Spec: docs/specs/team-preview-implementation-plan-2026-05-26.md §2 (Deterministic
Builders). Everything here is sourced from existing tables — no LLM, no invented
values. When a signal is absent we record it in ``missing_sources`` and let the
confidence band fall, rather than fabricating a number or a date.

Two important honesty mechanics, both driven by the live data state observed on
2026-05-26 (no 2026 schedule loaded; returning/talent/recruiting lag to 2025;
full game records lag to 2024):

  * ``prior_season_year`` is *detected* as the latest season with a full game
    record, and stored explicitly, so a lagging dataset is visible, not hidden.
  * Each strength signal carries the season it actually came from; when that
    lags the target season it is flagged in ``missing_sources``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from cfb_rankings.team_preview.season_path import SeasonPathInputs

# Minimum regular-season game count for a season to count as "complete enough"
# to be the prior-season record source. Set well above a mid-season partial but
# below the smallest real season on record (the COVID-shortened 2020 has ~560
# regular-game rows), so an in-progress season is never promoted to "prior
# completed season" while legitimate short seasons still qualify.
_MIN_REGULAR_GAMES_FOR_PRIOR = 300

_INDEPENDENT_CONFERENCE_NAMES = {"FBS Independents", "Independent", "Independents"}

# Weights for the composite strength scalar. Re-normalised over present signals.
_STRENGTH_WEIGHTS = {
    "talent": 0.25,
    "power": 0.25,
    "recruiting": 0.20,
    "returning": 0.15,
    "prior_record": 0.15,
}


@lru_cache(maxsize=1)
def canonical_fbs_slugs() -> frozenset[str]:
    """Authoritative real-FBS slug set, read from the hand-maintained profiles/.

    The spec (§0, §7.4) warns that ``teams.level_code='FBS'`` is polluted, so we
    use the profiles/ directory as the canonical set — the same source the
    Chronicle pipeline trusts. Standalone here so the preview layer does not
    import Chronicle internals.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        profiles_dir = parent / "profiles"
        if profiles_dir.is_dir():
            return frozenset(
                f.stem for f in profiles_dir.iterdir() if f.suffix == ".md"
            )
    return frozenset()


@dataclass
class SeasonNormContext:
    """Per-season distributions used to normalise rank/rating signals to 0..1."""

    season_year: int
    # Talent: the source only populates talent_score (higher = better); rank is
    # always NULL, so we derive both rank and a 0..1 norm from the score.
    talent_season: int | None = None
    talent_min_score: float | None = None
    talent_max_score: float | None = None
    talent_rank_by_team: dict[int, int] = field(default_factory=dict)
    recruiting_rank_by_team: dict[int, int] = field(default_factory=dict)
    recruiting_max_rank: int | None = None
    power_min: float | None = None
    power_max: float | None = None
    power_season: int | None = None

    def talent_norm(self, score: float | None) -> float | None:
        if score is None or self.talent_min_score is None or self.talent_max_score is None:
            return None
        if self.talent_max_score <= self.talent_min_score:
            return 0.5
        return max(0.0, min(1.0,
                   (score - self.talent_min_score) / (self.talent_max_score - self.talent_min_score)))

    def recruiting_norm(self, team_id: int) -> float | None:
        rank = self.recruiting_rank_by_team.get(team_id)
        if rank is None or not self.recruiting_max_rank or self.recruiting_max_rank <= 1:
            return None
        return max(0.0, min(1.0, 1.0 - (rank - 1) / (self.recruiting_max_rank - 1)))

    def power_norm(self, rating: float | None) -> float | None:
        if rating is None or self.power_min is None or self.power_max is None:
            return None
        if self.power_max <= self.power_min:
            return 0.5
        return max(0.0, min(1.0, (rating - self.power_min) / (self.power_max - self.power_min)))


@dataclass
class TeamEvidence:
    """Deterministic fact bundle for one team / season / as-of date."""

    slug: str
    team_id: int
    season_year: int
    as_of_date: str
    conference_id: int | None
    conference_name: str | None
    is_independent: bool

    prior_season_year: int | None = None
    prior_wins: int | None = None
    prior_losses: int | None = None
    prior_ties: int | None = None
    prior_final_ap_rank: int | None = None
    prior_final_coaches_rank: int | None = None
    prior_final_cfp_rank: int | None = None

    schedule_known: bool = False
    first_game_id: int | None = None
    first_game_start_utc: str | None = None
    first_game_opponent_id: int | None = None
    first_game_opponent_name: str | None = None

    power_prior_rating: float | None = None
    resume_prior_rating: float | None = None
    talent_rank: int | None = None
    talent_score: float | None = None
    recruiting_rank: int | None = None
    recruiting_score: float | None = None
    returning_total: float | None = None
    returning_offense: float | None = None
    returning_defense: float | None = None
    returning_qb: float | None = None
    returning_ol: float | None = None
    transfer_in_count: int = 0
    transfer_out_count: int = 0
    transfer_net_count: int = 0
    drafted_count: int = 0
    draft_capital_lost: float | None = None

    strength: float = 0.0
    uncertainty: float = 1.0
    confidence_band: str = "unset"
    missing_sources: list[str] = field(default_factory=list)
    source_fingerprint: str | None = None


def _scalar(db: Any, sql: str, params: dict[str, Any]) -> Any:
    row = db.query_one(sql, params)
    if not row:
        return None
    return next(iter(row.values()))


def latest_season_with_regular_games(db: Any, before: int | None = None) -> int | None:
    clause = "and season_year < :before" if before else ""
    row = db.query_one(
        f"""
        select season_year
        from games
        where season_type = 'regular' {clause}
        group by season_year
        having count(*) >= :minc
        order by season_year desc
        limit 1
        """,
        {"before": before, "minc": _MIN_REGULAR_GAMES_FOR_PRIOR},
    )
    return int(row["season_year"]) if row else None


def latest_season_for_table(db: Any, table: str, season_col: str = "season_year",
                            where: str = "") -> int | None:
    # INTERNAL ONLY: ``table``, ``season_col`` and ``where`` are always
    # hard-coded literals supplied by callers in this module (the only dynamic
    # value embedded in ``where`` is an int season_year). Never pass
    # externally-derived strings here — they would be interpolated into SQL.
    suffix = f"where {where}" if where else ""
    val = _scalar(db, f"select max({season_col}) from {table} {suffix}", {})
    return int(val) if val is not None else None


def build_norm_context(db: Any, season_year: int) -> SeasonNormContext:
    """Build per-season normalisation distributions (latest available <= target)."""
    ctx = SeasonNormContext(season_year=season_year)

    talent_season = latest_season_for_table(
        db, "team_talent_snapshots", where=f"season_year <= {season_year}"
    )
    if talent_season is not None:
        ctx.talent_season = talent_season
        trows = db.query_all(
            "select team_id, talent_score from team_talent_snapshots "
            "where season_year = :s and talent_score is not null "
            "order by talent_score desc",
            {"s": talent_season},
        )
        for rank, r in enumerate(trows, start=1):
            ctx.talent_rank_by_team[int(r["team_id"])] = rank
        if trows:
            scores = [r["talent_score"] for r in trows]
            ctx.talent_min_score = min(scores)
            ctx.talent_max_score = max(scores)

    rec_season = latest_season_for_table(
        db, "recruiting_entries",
        where=f"season_year <= {season_year} and class_key = 'team'",
    )
    if rec_season is not None:
        rows = db.query_all(
            """
            select team_id, rating
            from recruiting_entries
            where season_year = :s and class_key = 'team' and rating is not null
            order by rating desc
            """,
            {"s": rec_season},
        )
        for rank, r in enumerate(rows, start=1):
            ctx.recruiting_rank_by_team[int(r["team_id"])] = rank
        ctx.recruiting_max_rank = len(rows) or None

    power_season = latest_season_for_table(
        db, "power_ratings_weekly", where=f"season_year <= {season_year}"
    )
    if power_season is not None:
        max_week = _scalar(
            db,
            "select max(week) from power_ratings_weekly where season_year = :s",
            {"s": power_season},
        )
        bounds = db.query_one(
            """
            select min(power_rating) lo, max(power_rating) hi
            from power_ratings_weekly
            where season_year = :s and week = :w
            """,
            {"s": power_season, "w": max_week},
        )
        if bounds:
            ctx.power_min = bounds["lo"]
            ctx.power_max = bounds["hi"]
            ctx.power_season = power_season
    return ctx


def _prior_record(db: Any, team_id: int, prior_season: int) -> tuple[int, int, int]:
    row = db.query_one(
        """
        select
          sum(case when (home_team_id = :t and home_points > away_points)
                     or (away_team_id = :t and away_points > home_points) then 1 else 0 end) w,
          sum(case when (home_team_id = :t and home_points < away_points)
                     or (away_team_id = :t and away_points < home_points) then 1 else 0 end) l,
          sum(case when home_points = away_points then 1 else 0 end) t
        from games
        where season_year = :s and status = 'Final'
          and (home_team_id = :t or away_team_id = :t)
          and home_points is not null and away_points is not null
        """,
        {"t": team_id, "s": prior_season},
    )
    if not row:
        return (0, 0, 0)
    return (int(row["w"] or 0), int(row["l"] or 0), int(row["t"] or 0))


def _final_rank(db: Any, team_id: int, season: int, ranking_system: str) -> int | None:
    row = db.query_one(
        """
        select rank_value
        from official_rankings
        where team_id = :t and season_year = :s and ranking_system = :sys
        order by case when week is null then 1 else 0 end, week desc
        limit 1
        """,
        {"t": team_id, "s": season, "sys": ranking_system},
    )
    return int(row["rank_value"]) if row and row["rank_value"] is not None else None


def _first_future_game(db: Any, team_id: int, season_year: int) -> dict[str, Any] | None:
    return db.query_one(
        """
        select g.game_id, g.start_time_utc, g.home_team_id, g.away_team_id,
               ht.canonical_name home_name, at.canonical_name away_name
        from games g
        join teams ht on ht.team_id = g.home_team_id
        join teams at on at.team_id = g.away_team_id
        where g.season_year = :s and (g.home_team_id = :t or g.away_team_id = :t)
          and g.start_time_utc is not null
        order by g.start_time_utc asc
        limit 1
        """,
        {"t": team_id, "s": season_year},
    )


def build_team_evidence(
    db: Any, slug: str, season_year: int, as_of_date: str,
    norm: SeasonNormContext,
) -> TeamEvidence | None:
    team = db.query_one(
        """
        select t.team_id, t.slug, t.current_conference_id, c.conference_name
        from teams t
        left join conferences c on c.conference_id = t.current_conference_id
        where t.slug = :slug
        """,
        {"slug": slug},
    )
    if not team:
        return None

    team_id = int(team["team_id"])
    conf_name = team["conference_name"]
    is_indep = (conf_name or "") in _INDEPENDENT_CONFERENCE_NAMES

    ev = TeamEvidence(
        slug=slug,
        team_id=team_id,
        season_year=season_year,
        as_of_date=as_of_date,
        conference_id=team["current_conference_id"],
        conference_name=conf_name,
        is_independent=is_indep,
    )
    missing = ev.missing_sources

    # --- prior completed season + final record + polls ----------------------
    prior_season = latest_season_with_regular_games(db, before=season_year)
    if prior_season is not None:
        ev.prior_season_year = prior_season
        w, l, t = _prior_record(db, team_id, prior_season)
        ev.prior_wins, ev.prior_losses, ev.prior_ties = w, l, t
        if prior_season < season_year - 1:
            missing.append(f"prior_season_lag(latest_full_games={prior_season})")
        ev.prior_final_ap_rank = _final_rank(db, team_id, prior_season, "AP Top 25")
        ev.prior_final_coaches_rank = _final_rank(db, team_id, prior_season, "Coaches Poll")
        ev.prior_final_cfp_rank = _final_rank(
            db, team_id, prior_season, "Playoff Committee Rankings"
        )
    else:
        missing.append("prior_season_record")

    # --- schedule truth ------------------------------------------------------
    fg = _first_future_game(db, team_id, season_year)
    if fg:
        ev.schedule_known = True
        ev.first_game_id = int(fg["game_id"])
        ev.first_game_start_utc = fg["start_time_utc"]
        if int(fg["home_team_id"]) == team_id:
            ev.first_game_opponent_id = int(fg["away_team_id"])
            ev.first_game_opponent_name = fg["away_name"]
        else:
            ev.first_game_opponent_id = int(fg["home_team_id"])
            ev.first_game_opponent_name = fg["home_name"]
    else:
        missing.append(f"schedule_{season_year}")

    # --- talent --------------------------------------------------------------
    talent_season = latest_season_for_table(
        db, "team_talent_snapshots", where=f"season_year <= {season_year}"
    )
    if talent_season is not None:
        row = db.query_one(
            "select talent_score from team_talent_snapshots "
            "where team_id = :t and season_year = :s",
            {"t": team_id, "s": talent_season},
        )
        if row and row["talent_score"] is not None:
            ev.talent_score = row["talent_score"]
            # talent_rank is always NULL upstream; derive it from the score order.
            ev.talent_rank = norm.talent_rank_by_team.get(team_id)
            if talent_season < season_year:
                missing.append(f"talent_lag({talent_season})")
        else:
            missing.append("talent")
    else:
        missing.append("talent")

    # --- recruiting class ----------------------------------------------------
    rec_season = latest_season_for_table(
        db, "recruiting_entries",
        where=f"season_year <= {season_year} and class_key = 'team'",
    )
    if rec_season is not None:
        row = db.query_one(
            "select rating from recruiting_entries "
            "where team_id = :t and season_year = :s and class_key = 'team'",
            {"t": team_id, "s": rec_season},
        )
        if row:
            ev.recruiting_score = row["rating"]
            ev.recruiting_rank = norm.recruiting_rank_by_team.get(team_id)
            if rec_season < season_year:
                missing.append(f"recruiting_lag({rec_season})")
        else:
            missing.append("recruiting")
    else:
        missing.append("recruiting")

    # --- returning production ------------------------------------------------
    rp_season = latest_season_for_table(
        db, "returning_production", where=f"season_year <= {season_year}"
    )
    if rp_season is not None:
        row = db.query_one(
            "select returning_total, returning_offense, returning_defense, "
            "returning_qb, returning_ol from returning_production "
            "where team_id = :t and season_year = :s",
            {"t": team_id, "s": rp_season},
        )
        if row:
            ev.returning_total = row["returning_total"]
            ev.returning_offense = row["returning_offense"]
            ev.returning_defense = row["returning_defense"]
            ev.returning_qb = row["returning_qb"]
            ev.returning_ol = row["returning_ol"]
            if rp_season < season_year:
                missing.append(f"returning_production_lag({rp_season})")
        else:
            missing.append("returning_production")
    else:
        missing.append("returning_production")

    # --- transfer flow (target season) --------------------------------------
    trow = db.query_one(
        """
        select
          sum(case when to_team_id = :t then 1 else 0 end) tin,
          sum(case when from_team_id = :t then 1 else 0 end) tout
        from transfer_entries
        where season_year = :s and (to_team_id = :t or from_team_id = :t)
        """,
        {"t": team_id, "s": season_year},
    )
    ev.transfer_in_count = int((trow or {}).get("tin") or 0)
    ev.transfer_out_count = int((trow or {}).get("tout") or 0)
    ev.transfer_net_count = ev.transfer_in_count - ev.transfer_out_count
    if ev.transfer_in_count == 0 and ev.transfer_out_count == 0:
        missing.append(f"transfers_{season_year}")

    # --- NFL draft loss (draft held in the target preview year) -------------
    drow = db.query_one(
        "select count(*) c, sum(case when round is not null then (8 - round) else 0 end) cap "
        "from player_nfl_draft where college_team_id = :t and draft_year = :y",
        {"t": team_id, "y": season_year},
    )
    ev.drafted_count = int((drow or {}).get("c") or 0)
    ev.draft_capital_lost = float((drow or {}).get("cap") or 0) or None

    # --- power / resume prior (latest available) -----------------------------
    if norm.power_season is not None:
        max_week = _scalar(
            db, "select max(week) from power_ratings_weekly where season_year = :s",
            {"s": norm.power_season},
        )
        prow = db.query_one(
            "select power_rating from power_ratings_weekly "
            "where team_id = :t and season_year = :s and week = :w",
            {"t": team_id, "s": norm.power_season, "w": max_week},
        )
        if prow:
            ev.power_prior_rating = prow["power_rating"]
            if norm.power_season < season_year:
                missing.append(f"power_prior_lag({norm.power_season})")
        else:
            missing.append("power_prior")
    else:
        missing.append("power_prior")

    _compute_strength(ev, norm)
    ev.source_fingerprint = _fingerprint(ev)
    return ev


def _compute_strength(ev: TeamEvidence, norm: SeasonNormContext) -> None:
    """Composite 0..1 strength scalar from available normalised signals."""
    signals: dict[str, float] = {}

    tn = norm.talent_norm(ev.talent_score)
    if tn is not None:
        signals["talent"] = tn

    pn = norm.power_norm(ev.power_prior_rating)
    if pn is not None:
        signals["power"] = pn

    rn = norm.recruiting_norm(ev.team_id)
    if rn is not None:
        signals["recruiting"] = rn

    if ev.returning_total is not None:
        signals["returning"] = max(0.0, min(1.0, ev.returning_total))

    if ev.prior_wins is not None and ev.prior_losses is not None:
        games = ev.prior_wins + ev.prior_losses
        if games > 0:
            signals["prior_record"] = ev.prior_wins / games

    if signals:
        total_w = sum(_STRENGTH_WEIGHTS[k] for k in signals)
        ev.strength = sum(_STRENGTH_WEIGHTS[k] * v for k, v in signals.items()) / total_w
    else:
        ev.strength = 0.0

    # Uncertainty = share of the five strength signals that are missing, with a
    # small extra penalty when the future schedule is unknown.
    present = len(signals)
    base_uncertainty = 1.0 - present / len(_STRENGTH_WEIGHTS)
    if not ev.schedule_known:
        base_uncertainty = min(1.0, base_uncertainty + 0.10)
    ev.uncertainty = round(base_uncertainty, 3)
    ev.confidence_band = _confidence_band(ev.uncertainty, present)


def _confidence_band(uncertainty: float, present_signals: int) -> str:
    if present_signals == 0:
        return "unset"
    if uncertainty <= 0.25:
        return "high"
    if uncertainty <= 0.55:
        return "medium"
    return "low"


def _fingerprint(ev: TeamEvidence) -> str:
    import hashlib
    import json

    payload = {
        "slug": ev.slug,
        "season": ev.season_year,
        "as_of": ev.as_of_date,
        "prior_season": ev.prior_season_year,
        "prior": [ev.prior_wins, ev.prior_losses, ev.prior_ties],
        "talent_rank": ev.talent_rank,
        "recruiting_rank": ev.recruiting_rank,
        "returning_total": ev.returning_total,
        "power": ev.power_prior_rating,
        "transfers": [ev.transfer_in_count, ev.transfer_out_count],
        "drafted": ev.drafted_count,
        "schedule_known": ev.schedule_known,
        "strength": round(ev.strength, 4),
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def to_season_path_inputs(ev: TeamEvidence) -> SeasonPathInputs:
    return SeasonPathInputs(
        slug=ev.slug,
        season_year=ev.season_year,
        strength=ev.strength,
        is_independent=ev.is_independent,
        uncertainty=ev.uncertainty,
        confidence_band=ev.confidence_band,
        # Deep CFP / title projections require real talent + recruiting evidence,
        # not just a high composite built from a thin signal set.
        cfp_eligible=(ev.talent_score is not None and ev.recruiting_score is not None),
    )
