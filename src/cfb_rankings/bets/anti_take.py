"""Anti-Take Engine — the honest sibling of the Hot-Take (S2.3).

Spec: ``docs/specs/signature_bets/anti_take_spec.md``. Every Hot-Take
pairs with an Anti-Take or does not ship. The caveat library lives in
``seeds/anti_take_templates.yaml`` and is selected deterministically
from the Hot-Take's meta dict.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML required") from exc

from cfb_rankings.bets.hot_take import HotTake


_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3] / "seeds" / "anti_take_templates.yaml"
)

# Efficiency-shaped metrics (unit or id signal) so the
# "efficiency-volume-offset" caveat fires naturally.
_EFFICIENCY_METRIC_IDS: set[str] = {
    "ypa", "ypc", "ypr", "completion_pct", "td_int_ratio",
    "wepa_passing_per_dropback", "wepa_combined_per_play",
    "wepa_rushing_per_carry", "qbr_season_avg",
}
_EFFICIENCY_UNITS: set[str] = {"pct", "EPA", "QBR", "ratio", "rate"}

# Volume-shaped metrics.
_VOLUME_METRIC_IDS: set[str] = {
    "passing_yards_total", "rushing_yards_total", "receiving_yards_total",
    "wepa_passing_total",
}

# Sample band where the "thin-sample" caveat fires — above the HIGH
# floor (40, per S1.2) but not deep into the comfort zone (>=80).
_THIN_SAMPLE_BAND: range = range(40, 80)


@dataclass(frozen=True)
class AntiTake:
    template_id: str
    rendered_text: str
    caveat_tag: str


@lru_cache(maxsize=1)
def _load_templates() -> list[dict[str, Any]]:
    if not _TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Missing {_TEMPLATE_PATH}")
    data = yaml.safe_load(_TEMPLATE_PATH.read_text(encoding="utf-8")) or {}
    out: list[dict[str, Any]] = []
    for row in (data.get("templates") or []):
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "id": str(row.get("id") or ""),
                "condition": str(row.get("condition") or "always"),
                "priority": int(row.get("priority") or 9),
                "caveat_tag": str(row.get("caveat_tag") or "NOTE"),
                "text": " ".join(str(row.get("text") or "").split()),
            }
        )
    out.sort(key=lambda r: r["priority"])
    return out


def _matches_condition(cond: str, meta: dict[str, Any], metric_id: str) -> bool:
    if cond == "always":
        return True
    unit = str(meta.get("unit") or "")
    percentile = float(meta.get("percentile") or 0)
    rank = int(meta.get("rank") or 0)
    cohort_size = int(meta.get("cohort_size") or 0)
    sample = int(meta.get("sample") or 0)
    cohort = str(meta.get("cohort") or "")

    if cond == "efficiency_metric":
        return metric_id in _EFFICIENCY_METRIC_IDS or unit in _EFFICIENCY_UNITS
    if cond == "volume_metric":
        return metric_id in _VOLUME_METRIC_IDS or unit == "yds"
    if cond == "cohort_tiered":
        return "P4" in cohort or "Notre Dame" in cohort or "P5" in cohort
    if cond == "sample_thin_for_band":
        return sample in _THIN_SAMPLE_BAND
    if cond == "rank_band_compressed":
        return percentile < 95.0
    if cond == "near_tie":
        return cohort_size > (rank + 2) and percentile < 97.0
    return False


def _render_template(tmpl: dict[str, Any], take: HotTake) -> str:
    meta = take.meta or {}
    placeholders = {
        "rank":          int(meta.get("rank") or 0),
        "percentile":    int(round(float(meta.get("percentile") or 0))),
        "cohort":        str(meta.get("cohort") or ""),
        "cohort_size":   int(meta.get("cohort_size") or 0),
        "sample":        int(meta.get("sample") or 0),
        "metric_label":  str(take.metric_id or ""),
        "runner_up":     max(int(meta.get("rank") or 0) + 1, 2),
        "stripped_rank": max(int(meta.get("rank") or 0) + 2, 2),
        "era_label":     "modern",  # placeholder — upgrade when era_context
                                    # is threaded through meta.
    }
    try:
        return tmpl["text"].format(**placeholders)
    except (KeyError, IndexError):
        return ""


def generate_anti_take(take: HotTake | None) -> AntiTake | None:
    """Return the paired Anti-Take for a Hot-Take, or None when no
    defensible caveat can be produced.

    Callers MUST treat None as a signal to drop the Hot-Take entirely —
    the pairing is mandatory per spec.
    """
    if take is None:
        return None
    meta = take.meta or {}
    metric_id = str(take.metric_id or "")
    for tmpl in _load_templates():
        if not _matches_condition(tmpl["condition"], meta, metric_id):
            continue
        rendered = _render_template(tmpl, take)
        if not rendered:
            continue
        return AntiTake(
            template_id=tmpl["id"],
            rendered_text=rendered,
            caveat_tag=tmpl["caveat_tag"],
        )
    return None


def anti_take_to_render_dict(ant: AntiTake | None) -> dict[str, Any] | None:
    if ant is None:
        return None
    return {
        "template_id": ant.template_id,
        "rendered_text": ant.rendered_text,
        "caveat_tag": ant.caveat_tag,
    }
