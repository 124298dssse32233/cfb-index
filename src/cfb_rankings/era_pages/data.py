"""Data assembly for the CFP-era page (WS-07).

Pure DB reads + dataclass assembly — no HTML. The renderer consumes the
returned ``EraSummary``. Everything degrades gracefully: a section with no
data is simply omitted by the renderer, and ``build_era_summary`` returns
``None`` when the program lacks enough power-rating history to draw the
three-act trajectory (the local/offseason guard, matching the dynasty
detector's posture).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..db import Database
from ..dynasty_heatmap import compute_year_percentiles, fetch_final_powers

CFP_ERA_START = 2014
MIN_SEASONS = 8  # need a dense trajectory before the page is worth shipping


@dataclass(frozen=True)
class _ActDef:
    key: str
    label: str
    year_start: int
    year_end: int | None  # None = open-ended ("present")
    blurb: str


# The three acts of the CFP era (D-001 horizon; sub-eras per the data-horizon
# memory: Founding / Transition / Expansion).
ACTS: tuple[_ActDef, ...] = (
    _ActDef("founding", "Founding", 2014, 2020,
            "The four-team Playoff era. The bracket is small, the margin for error none."),
    _ActDef("transition", "Transition", 2021, 2023,
            "The last seasons before expansion — NIL arrives, the portal opens, the four-team format ends."),
    _ActDef("expansion", "Expansion", 2024, None,
            "The twelve-team Playoff. A wider field changes what a season has to prove."),
)


@dataclass
class EraSeason:
    year: int
    power_rating: float | None
    percentile: float | None  # 0..100 within that season's FBS cohort
    wins: int
    losses: int
    head_coach: str | None
    postseason_label: str | None  # short note for the deepest postseason result
    draftees: int  # NFL draftees from the *following* spring's draft


@dataclass
class EraAct:
    key: str
    label: str
    year_start: int
    year_end: int | None
    blurb: str
    seasons: list[EraSeason] = field(default_factory=list)

    @property
    def span_label(self) -> str:
        if self.year_end is None:
            return f"{self.year_start}–present"
        if self.year_start == self.year_end:
            return str(self.year_start)
        return f"{self.year_start}–{self.year_end}"

    @property
    def avg_percentile(self) -> float | None:
        vals = [s.percentile for s in self.seasons if s.percentile is not None]
        return sum(vals) / len(vals) if vals else None

    @property
    def record(self) -> tuple[int, int]:
        return (sum(s.wins for s in self.seasons), sum(s.losses for s in self.seasons))


@dataclass
class DefiningGame:
    year: int
    label: str          # bowl/round name (cleaned)
    opponent: str
    team_points: int
    opp_points: int
    won: bool
    is_title: bool


@dataclass
class CoachSpan:
    name: str
    year_start: int
    year_end: int


@dataclass
class EraSummary:
    slug: str
    program_name: str
    conference: str
    year_start: int
    year_end: int
    acts: list[EraAct]
    seasons: list[EraSeason]
    stat_sheet: dict[str, Any]
    defining_games: list[DefiningGame]
    coaches: list[CoachSpan]
    coaches_partial_from: int | None  # earliest season we actually have a coach for
    forward: dict[str, Any]


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def _act_for_year(year: int) -> _ActDef:
    for act in ACTS:
        if year >= act.year_start and (act.year_end is None or year <= act.year_end):
            return act
    return ACTS[-1]


def _clean_postseason_label(notes: str | None) -> str | None:
    if not notes:
        return None
    n = " ".join(notes.split())
    upper = n.upper()
    if "NATIONAL CHAMPIONSHIP" in upper:
        return "CFP National Championship"
    if "SEMIFINAL" in upper:
        return "CFP Semifinal"
    if "QUARTERFINAL" in upper:
        return "CFP Quarterfinal"
    if "FIRST ROUND" in upper:
        return "CFP First Round"
    if "PLAYOFF" in upper:
        return "CFP Playoff"
    # Title-case a bowl name, trimming sponsor cruft to the first " - ".
    base = n.split(" - ")[0].split(" PRES")[0].split(" Pres")[0]
    return base.title() if base else None


def _team_records(db: Database, team_id: int, ys: int, ye: int) -> dict[int, tuple[int, int]]:
    rows = db.query_all(
        """
        select season_year, home_team_id, away_team_id, home_points, away_points
          from games
         where (home_team_id = :t or away_team_id = :t)
           and season_year between :ys and :ye
           and status = 'Final'
           and home_points is not null and away_points is not null
        """,
        {"t": team_id, "ys": ys, "ye": ye},
    ) or []
    rec: dict[int, list[int]] = {}
    for r in rows:
        is_home = r["home_team_id"] == team_id
        tp = r["home_points"] if is_home else r["away_points"]
        op = r["away_points"] if is_home else r["home_points"]
        acc = rec.setdefault(int(r["season_year"]), [0, 0])
        if tp > op:
            acc[0] += 1
        elif tp < op:
            acc[1] += 1
    return {y: (w, l) for y, (w, l) in rec.items()}


def _deepest_postseason(db: Database, team_id: int, ys: int, ye: int) -> tuple[dict[int, str], list[DefiningGame]]:
    rows = db.query_all(
        """
        select season_year, notes, home_team_id, away_team_id, home_points, away_points
          from games
         where (home_team_id = :t or away_team_id = :t)
           and season_year between :ys and :ye
           and season_type = 'postseason'
           and status = 'Final'
           and home_points is not null and away_points is not null
         order by season_year
        """,
        {"t": team_id, "ys": ys, "ye": ye},
    ) or []
    # Rank labels so the per-season chip shows the *deepest* round reached.
    rank = {"CFP National Championship": 5, "CFP Semifinal": 4, "CFP Quarterfinal": 3,
            "CFP First Round": 2, "CFP Playoff": 4}
    per_season: dict[int, tuple[int, str]] = {}
    games: list[DefiningGame] = []
    opp_names = _opponent_names(db, [r for r in rows], team_id)
    for r in rows:
        label = _clean_postseason_label(r["notes"]) or "Bowl"
        yr = int(r["season_year"])
        is_home = r["home_team_id"] == team_id
        tp = int(r["home_points"] if is_home else r["away_points"])
        op = int(r["away_points"] if is_home else r["home_points"])
        opp_id = r["away_team_id"] if is_home else r["home_team_id"]
        won = tp > op
        is_title = label == "CFP National Championship"
        games.append(DefiningGame(
            year=yr, label=label, opponent=opp_names.get(opp_id, "—"),
            team_points=tp, opp_points=op, won=won, is_title=is_title,
        ))
        score = rank.get(label, 1)
        if yr not in per_season or score > per_season[yr][0]:
            chip = label
            if label == "CFP National Championship":
                chip = "Won National Title" if won else "Played for the Title"
            per_season[yr] = (score, chip)
    return ({y: chip for y, (_s, chip) in per_season.items()}, games)


def _opponent_names(db: Database, rows: list[dict[str, Any]], team_id: int) -> dict[int, str]:
    ids = set()
    for r in rows:
        ids.add(r["away_team_id"] if r["home_team_id"] == team_id else r["home_team_id"])
    ids.discard(None)
    if not ids:
        return {}
    placeholders = ",".join(str(int(i)) for i in ids)
    res = db.query_all(
        f"select team_id, canonical_name from teams where team_id in ({placeholders})"
    ) or []
    return {int(r["team_id"]): str(r["canonical_name"]) for r in res}


def _coach_spans(db: Database, team_id: int, ys: int, ye: int) -> tuple[list[CoachSpan], int | None]:
    rows = db.query_all(
        """
        select season_year, head_coach
          from team_seasons
         where team_id = :t and head_coach is not null and head_coach <> ''
           and season_year between :ys and :ye
         order by season_year
        """,
        {"t": team_id, "ys": ys, "ye": ye},
    ) or []
    if not rows:
        return [], None
    spans: list[CoachSpan] = []
    earliest = int(rows[0]["season_year"])
    for r in rows:
        yr = int(r["season_year"])
        name = str(r["head_coach"])
        if spans and spans[-1].name == name and yr == spans[-1].year_end + 1:
            spans[-1].year_end = yr
        else:
            spans.append(CoachSpan(name=name, year_start=yr, year_end=yr))
    return spans, earliest


def _draftees_by_class(db: Database, team_id: int, ys: int, ye: int) -> dict[int, int]:
    # NFL draft happens the spring *after* a season; map draft_year y to season y-1.
    rows = db.query_all(
        """
        select draft_year, count(*) n
          from player_nfl_draft
         where college_team_id = :t and draft_year between :ys and :ye
         group by draft_year
        """,
        {"t": team_id, "ys": ys + 1, "ye": ye + 1},
    ) or []
    return {int(r["draft_year"]) - 1: int(r["n"]) for r in rows}


def build_era_summary(db: Database, slug: str, *, end_season: int = 2025) -> EraSummary | None:
    team = db.query_one(
        """
        select t.team_id, t.canonical_name, coalesce(c.conference_name, '') as conf
          from teams t left join conferences c on c.conference_id = t.current_conference_id
         where t.slug = :s
        """,
        {"s": slug},
    )
    if not team:
        return None
    team_id = int(team["team_id"])

    pct_rows = compute_year_percentiles(
        fetch_final_powers(db, CFP_ERA_START, end_season)
    )
    by_year_pct: dict[int, dict[str, float]] = {}
    for r in pct_rows:
        if int(r["team_id"]) == team_id:
            by_year_pct[int(r["season_year"])] = {
                "power": float(r["power_rating"]),
                "pct": float(r["percentile"]),
            }
    if len(by_year_pct) < MIN_SEASONS:
        return None  # not enough trajectory to be worth a page

    records = _team_records(db, team_id, CFP_ERA_START, end_season)
    post_chips, defining = _deepest_postseason(db, team_id, CFP_ERA_START, end_season)
    coaches, coaches_from = _coach_spans(db, team_id, CFP_ERA_START, end_season)
    coach_by_year = {y: cs.name for cs in coaches for y in range(cs.year_start, cs.year_end + 1)}
    draft_by_season = _draftees_by_class(db, team_id, CFP_ERA_START, end_season)

    seasons: list[EraSeason] = []
    for yr in range(CFP_ERA_START, end_season + 1):
        pc = by_year_pct.get(yr)
        w, l = records.get(yr, (0, 0))
        seasons.append(EraSeason(
            year=yr,
            power_rating=pc["power"] if pc else None,
            percentile=pc["pct"] if pc else None,
            wins=w, losses=l,
            head_coach=coach_by_year.get(yr),
            postseason_label=post_chips.get(yr),
            draftees=draft_by_season.get(yr, 0),
        ))

    acts: list[EraAct] = []
    for ad in ACTS:
        act_seasons = [s for s in seasons
                       if s.year >= ad.year_start
                       and (ad.year_end is None or s.year <= ad.year_end)
                       and s.year <= end_season]
        if not act_seasons:
            continue
        acts.append(EraAct(ad.key, ad.label, ad.year_start, ad.year_end, ad.blurb, act_seasons))

    total_w = sum(s.wins for s in seasons)
    total_l = sum(s.losses for s in seasons)
    titles = sum(1 for g in defining if g.is_title and g.won)
    title_games = sum(1 for g in defining if g.is_title)
    best = max((s for s in seasons if s.percentile is not None),
               key=lambda s: s.percentile, default=None)
    pcts = [s.percentile for s in seasons if s.percentile is not None]
    total_draft = sum(draft_by_season.values())

    stat_sheet = {
        "seasons": len([s for s in seasons if s.percentile is not None]),
        "record": (total_w, total_l),
        "win_pct": (total_w / (total_w + total_l)) if (total_w + total_l) else None,
        "titles": titles,
        "title_games": title_games,
        "playoff_appearances": sum(1 for g in defining
                                   if g.label in {"CFP Semifinal", "CFP First Round",
                                                  "CFP Quarterfinal", "CFP Playoff"}),
        "best_season": best.year if best else None,
        "best_season_pct": best.percentile if best else None,
        "avg_percentile": (sum(pcts) / len(pcts)) if pcts else None,
        "nfl_draftees": total_draft,
    }

    forward = {
        "next_season": end_season + 1,
        "team_url": f"/teams/{slug}.html",
        "current_coach": coaches[-1].name if coaches else None,
    }

    return EraSummary(
        slug=slug,
        program_name=str(team["canonical_name"]),
        conference=str(team["conf"]),
        year_start=CFP_ERA_START,
        year_end=end_season,
        acts=acts,
        seasons=seasons,
        stat_sheet=stat_sheet,
        defining_games=defining,
        coaches=coaches,
        coaches_partial_from=coaches_from,
        forward=forward,
    )
