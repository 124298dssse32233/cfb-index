"""Hot-Take Engine — defensibly-true one-liners (Signature Bets S2.2).

Spec: ``docs/specs/signature_bets/hot_take_spec.md``. This module reads
from the Signature Story evaluation cache, applies defensibility gates,
ranks candidates by novelty × narrative-weight, and emits a deterministic
per-day pick with its (rank, cohort, sample, methodology) quadruple.

Paired with the Anti-Take Engine (S2.3) which consumes the same
candidate record and produces the honest counter-caveat.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML required — pip install pyyaml") from exc

from cfb_rankings.db import Database
from cfb_rankings.signature_story import (
    CandidateEval,
    build_candidate_scoreboard,
    _fetch_player_position,
    _load_seed,
    _volume_noun,
)


_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3] / "seeds" / "hot_take_templates.yaml"
)


# Defensibility gate constants (see spec §Defensibility gates).
MIN_SAMPLE = 40
MIN_PERCENTILE = 90.0
MAX_RANK = 5
MIN_COHORT_SIZE = 20

# Daily rotation window — pick deterministically among the top-N candidates.
ROTATION_WINDOW = 3

# Position weight in the novelty score (spec §Novelty scoring).
_POSITION_WEIGHTS: dict[str, float] = {
    "QB": 1.0,
    "RB": 0.95,
    "WR": 0.95,
    "TE": 0.9,
}


@dataclass(frozen=True)
class HotTake:
    """One defensibly-true one-liner + its quadruple + provenance."""
    template_id: str
    metric_id: str
    rendered_text: str
    score: float
    meta: dict[str, Any]  # {rank, cohort, sample, methodology}

    def as_json(self) -> str:
        return json.dumps(
            {
                "template_id": self.template_id,
                "metric_id": self.metric_id,
                "rendered_text": self.rendered_text,
                "score": self.score,
                "meta": self.meta,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )


@lru_cache(maxsize=1)
def _load_templates() -> list[dict[str, Any]]:
    if not _TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Missing {_TEMPLATE_PATH}")
    data = yaml.safe_load(_TEMPLATE_PATH.read_text(encoding="utf-8")) or {}
    out: list[dict[str, Any]] = []
    for row in (data.get("templates") or []):
        if not isinstance(row, dict):
            continue
        if not row.get("id") or not row.get("text"):
            continue
        applies = row.get("applies_to")
        if isinstance(applies, str):
            applies_list = [applies]
        elif isinstance(applies, list):
            applies_list = [str(a) for a in applies if a]
        else:
            applies_list = ["*"]
        out.append(
            {
                "id": str(row["id"]),
                "applies_to": applies_list,
                "text": str(row["text"]).strip(),
                "voice": str(row.get("voice") or "cohort_top"),
                "min_percentile": float(
                    row.get("min_percentile") or MIN_PERCENTILE
                ),
            }
        )
    return out


def _era_label(season: int) -> str:
    if season >= 2020:
        return "modern"
    if season >= 2010:
        return "analytics"
    if season >= 2006:
        return "BCS-era"
    return "pre-BCS"


def _format_value(value: float, unit: str) -> str:
    if unit == "pct":
        return f"{value:.1f}%"
    if unit == "EPA":
        return f"{value:+.3f}"
    if unit == "QBR":
        return f"{value:.1f}"
    if unit == "ratio":
        return f"{value:.1f}"
    if unit == "yds":
        return f"{value:,.0f}" if value >= 100 else f"{value:.1f}"
    if unit == "rate":
        return f"{value:.0%}"
    return f"{value:g}"


def _template_applicable(tmpl: dict[str, Any], metric_id: str) -> bool:
    applies = tmpl.get("applies_to") or ["*"]
    return "*" in applies or metric_id in applies


def _build_meta(
    eval: CandidateEval, season: int, player_id: int
) -> dict[str, Any]:
    seed = _load_seed()
    cohort = seed.cohorts[eval.metric.cohort]
    methodology = (
        f"{eval.metric.label} over min {int(eval.metric.min_volume)} "
        f"{_volume_noun(eval.metric)}, {cohort.label} cohort, "
        f"season {season}. Rank is standard competition ranking."
    )
    return {
        "rank": int(eval.rank),
        "cohort": f"{eval.metric.cohort} ({cohort.label})",
        "cohort_size": int(eval.cohort_size),
        "sample": int(eval.sample_size),
        "percentile": round(eval.percentile, 1),
        "methodology": methodology,
        "season": int(season),
        "player_id": int(player_id),
        "value": float(eval.value),
        "unit": str(eval.metric.unit),
    }


def _passes_gates(eval: CandidateEval) -> bool:
    if not eval.metric.higher_is_better:
        return False
    if eval.sample_size < MIN_SAMPLE:
        return False
    if eval.percentile < MIN_PERCENTILE:
        return False
    if eval.rank > MAX_RANK:
        return False
    if eval.cohort_size < MIN_COHORT_SIZE:
        return False
    return True


def _novelty_score(eval: CandidateEval, position: str) -> float:
    pos_weight = _POSITION_WEIGHTS.get(position, 0.9)
    return (
        eval.percentile
        * math.log(max(eval.sample_size, 2))
        * eval.metric.narrative_weight
        * pos_weight
    )


def _render_template(
    tmpl: dict[str, Any], eval: CandidateEval, season: int
) -> str | None:
    if eval.percentile < tmpl["min_percentile"]:
        return None
    seed = _load_seed()
    cohort = seed.cohorts[eval.metric.cohort]
    placeholders = {
        "value": _format_value(eval.value, eval.metric.unit),
        "metric_label": eval.metric.label.lower(),
        "rank": eval.rank,
        "cohort_size": eval.cohort_size,
        "cohort_label": cohort.label,
        "position": eval.metric.position,
        "percentile": int(round(eval.percentile)),
        "era_label": _era_label(season),
        "top_n": max(int(eval.rank) - 1, 1),
    }
    try:
        return tmpl["text"].format(**placeholders)
    except (KeyError, IndexError):
        return None


def _pick_template(
    eval: CandidateEval, held_ids: set[str]
) -> tuple[dict[str, Any], str] | None:
    """Return (template, rendered_text) or None when no template fits."""
    templates = _load_templates()
    # Ordered: record → record_near → pace → cohort_top. First match wins
    # per voice band so 99th-pct values get the strongest phrasing.
    voice_rank = {"record": 0, "record_near": 1, "pace": 2, "cohort_top": 3}
    sorted_templates = sorted(
        templates,
        key=lambda t: voice_rank.get(t["voice"], 9),
    )
    for tmpl in sorted_templates:
        if tmpl["id"] in held_ids:
            continue
        if not _template_applicable(tmpl, eval.metric.id):
            continue
        rendered = _render_template(tmpl, eval, season=0)  # season set later
        if rendered:
            return tmpl, rendered
    return None


def _fetch_held_template_ids(db: Database) -> set[str]:
    try:
        rows = db.query_all(
            "SELECT template_id FROM hot_take_template_holds", {}
        )
    except Exception:
        return set()
    return {str(r["template_id"]) for r in rows if r.get("template_id")}


def generate_hot_takes(
    db: Database,
    player_id: int,
    season: int,
    *,
    held_ids: set[str] | None = None,
) -> list[HotTake]:
    """Compute all candidate Hot-Takes for a player; pass-gated + scored.

    Returned list is sorted by novelty score descending. Empty list is
    an honest "no defensibly-true take today" signal.
    """
    held_ids = (
        held_ids if held_ids is not None else _fetch_held_template_ids(db)
    )
    position = _fetch_player_position(db, player_id)
    if not position:
        return []
    evals = build_candidate_scoreboard(db, player_id, season, None)
    if not evals:
        return []

    takes: list[HotTake] = []
    for eval in evals:
        if not _passes_gates(eval):
            continue
        match = _pick_template(eval, held_ids)
        if match is None:
            continue
        tmpl, _rendered_stub = match
        # Re-render with the actual season so era_label resolves.
        final_text = _render_template(tmpl, eval, season=season)
        if not final_text:
            continue
        score = _novelty_score(eval, position)
        meta = _build_meta(eval, season=season, player_id=player_id)
        takes.append(
            HotTake(
                template_id=tmpl["id"],
                metric_id=eval.metric.id,
                rendered_text=" ".join(final_text.split()),
                score=round(score, 4),
                meta=meta,
            )
        )

    takes.sort(key=lambda t: (-t.score, t.meta["rank"], -t.meta["sample"]))
    return takes


def _daily_pick_index(player_id: int, as_of: _dt.date, n: int) -> int:
    if n <= 0:
        return 0
    key = f"{player_id}|{as_of.isoformat()}".encode("utf-8")
    digest = hashlib.sha256(key).hexdigest()
    return int(digest[:8], 16) % n


def select_daily_take(
    candidates: list[HotTake],
    *,
    player_id: int,
    as_of: _dt.date | None = None,
) -> HotTake | None:
    """Deterministically pick one take for the date from top-N candidates."""
    if not candidates:
        return None
    as_of = as_of or _dt.date.today()
    window = candidates[:ROTATION_WINDOW]
    idx = _daily_pick_index(player_id, as_of, len(window))
    return window[idx]


def fetch_cached_take(
    db: Database, player_id: int, as_of: _dt.date
) -> HotTake | None:
    try:
        row = db.query_one(
            "SELECT template_id, metric_id, rendered_text, meta_json, score "
            "FROM player_daily_hot_take "
            "WHERE player_id = :pid AND as_of_date = :d",
            {"pid": player_id, "d": as_of.isoformat()},
        )
    except Exception:
        return None
    if not row:
        return None
    try:
        meta = json.loads(row["meta_json"])
    except (TypeError, ValueError):
        meta = {}
    return HotTake(
        template_id=str(row["template_id"]),
        metric_id=str(row["metric_id"]),
        rendered_text=str(row["rendered_text"]),
        score=float(row["score"]),
        meta=meta,
    )


def store_daily_take(
    db: Database, player_id: int, as_of: _dt.date, take: HotTake
) -> None:
    db.execute(
        "INSERT INTO player_daily_hot_take "
        "(player_id, as_of_date, template_id, metric_id, rendered_text, meta_json, score) "
        "VALUES (:pid, :d, :tid, :mid, :rt, :mj, :sc) "
        "ON CONFLICT(player_id, as_of_date) DO UPDATE SET "
        "  template_id = excluded.template_id, "
        "  metric_id = excluded.metric_id, "
        "  rendered_text = excluded.rendered_text, "
        "  meta_json = excluded.meta_json, "
        "  score = excluded.score, "
        "  generated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')",
        {
            "pid": player_id,
            "d": as_of.isoformat(),
            "tid": take.template_id,
            "mid": take.metric_id,
            "rt": take.rendered_text,
            "mj": json.dumps(take.meta, ensure_ascii=False, separators=(",", ":")),
            "sc": float(take.score),
        },
    )


def compute_daily_hot_takes(
    db: Database, season: int, *, as_of: _dt.date | None = None
) -> int:
    """Batch-compute + cache one Hot-Take per qualifying player.

    Returns the count of rows written. Intended as a nightly CLI hook.
    """
    as_of = as_of or _dt.date.today()
    held = _fetch_held_template_ids(db)
    rows = db.query_all(
        "SELECT DISTINCT player_id FROM player_value_metrics "
        "WHERE season_year = :s",
        {"s": season},
    )
    n = 0
    for r in rows:
        pid = int(r["player_id"])
        takes = generate_hot_takes(db, pid, season, held_ids=held)
        pick = select_daily_take(takes, player_id=pid, as_of=as_of)
        if pick is None:
            continue
        store_daily_take(db, pid, as_of, pick)
        n += 1
    return n


def fetch_or_generate_take(
    db: Database,
    player_id: int,
    season: int,
    *,
    as_of: _dt.date | None = None,
) -> HotTake | None:
    """Cache-first read used by the renderer."""
    as_of = as_of or _dt.date.today()
    cached = fetch_cached_take(db, player_id, as_of)
    if cached:
        return cached
    takes = generate_hot_takes(db, player_id, season)
    return select_daily_take(takes, player_id=player_id, as_of=as_of)


def take_to_render_dict(take: HotTake | None) -> dict[str, Any] | None:
    if take is None:
        return None
    return {
        "template_id": take.template_id,
        "metric_id": take.metric_id,
        "rendered_text": take.rendered_text,
        "score": take.score,
        "meta": take.meta,
    }
