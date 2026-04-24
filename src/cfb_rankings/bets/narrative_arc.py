"""Narrative Arc — 3-act season synopsis loader (S3.4 / §4 Bet #14).

V1 reads hand-authored seeds from ``seeds/narrative_arcs.yaml``. The
module is designed so a future auto-generator writes to the same
return shape behind a confidence + flag-for-review gate.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML required") from exc


_SEED_PATH = Path(__file__).resolve().parents[3] / "seeds" / "narrative_arcs.yaml"


@lru_cache(maxsize=1)
def _load_seed() -> dict[str, dict[str, Any]]:
    if not _SEED_PATH.exists():
        return {}
    data = yaml.safe_load(_SEED_PATH.read_text(encoding="utf-8")) or {}
    out: dict[str, dict[str, Any]] = {}
    for key, row in (data.get("arcs") or {}).items():
        if not isinstance(row, dict):
            continue
        out[str(key).strip()] = row
    return out


def fetch_narrative_arc(player_id: int, season: int) -> dict[str, Any] | None:
    """Return the arc payload for (player_id, season), or None.

    Seed file is keyed on player_id. If the seed entry carries a
    different season, we still return it (seasons align 1:1 in v1).
    """
    arc = _load_seed().get(str(int(player_id)))
    if not arc:
        return None
    # Validate shape — every arc needs exactly 3 acts with required fields.
    acts = arc.get("acts") or []
    if len(acts) != 3:
        return None
    for act in acts:
        for key in ("title", "week_range", "inflection", "synthesis"):
            if not str(act.get(key) or "").strip():
                return None
    if int(arc.get("season") or 0) != int(season):
        # Out-of-season seed; skip quietly.
        return None
    return arc


# ---------------- Auto-generator (S4.10 / S3.4 V2) -------------------- #
#
# Draft an arc from Signature Story + achievements + Hot-Take. Guarded
# by a confidence gate so we never publish weak arcs. Output is
# flagged-for-review (never auto-published) until an editor promotes
# it into seeds/narrative_arcs.yaml.
#
# Current gate requirements:
#   - Signature Story: has_story = True
#   - Achievements: >= 2 unlocks (proves genuine on-field signature)
#   - Hot-Take: cached take available
# If any fails, auto-gen returns None (renderer shows empty-state).

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DraftArc:
    player_id: int
    player_name: str
    season: int
    acts: list[dict[str, str]] = field(default_factory=list)
    confidence_ok: bool = False
    flag_for_review: bool = True
    rationale: str = ""


def auto_draft_arc(
    *,
    player_id: int,
    player_name: str,
    season: int,
    signature_story: dict[str, Any] | None,
    achievements: list[dict[str, Any]] | None,
    hot_take: Any | None,
) -> DraftArc | None:
    """Produce a flag-for-review draft arc. Returns None when the gate fails."""
    story_ok = bool(signature_story and signature_story.get("has_story"))
    ach = achievements or []
    hot = hot_take
    if not story_ok:
        return None
    if len(ach) < 2:
        return None
    if hot is None:
        return None

    hs = (signature_story or {}).get("headline_stat") or {}
    metric_label = str(hs.get("label") or "the signature stat").lower()
    metric_value = hs.get("value")
    cohort_size = int(hs.get("cohort_size") or 0)
    percentile = int(round(float(hs.get("percentile") or 0)))
    rank = int(hs.get("rank") or 0)

    # Act I — Discovery. Template reads from the hot-take's one-liner
    # if available so the voice stays consistent across the page.
    hot_text = getattr(hot, "rendered_text", None) if not isinstance(hot, dict) else hot.get("rendered_text")
    act1_inflection = str(hot_text or (
        f"Early {metric_label} performances set the baseline — "
        f"the {percentile}th-percentile reading was visible by Week 4."
    ))
    act1_synthesis = (
        f"Discovery phase established a top-{max(rank or 5, 1)}-in-cohort "
        f"rank against {cohort_size} peers and anchored the rest of the season."
    )

    # Act II — Ascent. Reference the rarest achievement (first element of
    # list if sorted ASC by rarity in fetch_player_achievements).
    rarest = ach[0] if ach else {}
    rarest_name = str(rarest.get("display_name") or "an achievement")
    rarest_rarity = rarest.get("rarity_pct")
    rarity_phrase = (
        f"held by only {float(rarest_rarity):.1f}% of the pool"
        if rarest_rarity is not None else "a rare mark"
    )
    act2_inflection = (
        f"Mid-season run unlocked {rarest_name} — {rarity_phrase}."
    )
    act2_synthesis = (
        f"The efficiency curve continued up; volume stayed stable. "
        f"Cohort-percentile headroom thinned as {metric_label} cleared the "
        f"top-band threshold."
    )

    # Act III — Coronation / Closure. Uses the number of total unlocks
    # as a proxy for recognition weight.
    ach_count = len(ach)
    act3_inflection = (
        f"Season close carried {ach_count} distinct achievement tags, "
        f"with {rarest_name} the defining ticket."
    )
    act3_synthesis = (
        f"Year-end position at #{rank} of {cohort_size} in {metric_label} "
        f"({percentile}th pct) makes the multi-year narrative live. "
        f"The next chapter opens on whether this was a peak or a floor."
    )

    draft = DraftArc(
        player_id=player_id,
        player_name=player_name,
        season=season,
        acts=[
            {
                "title": "Discovery",
                "week_range": "Weeks 1-4",
                "inflection": act1_inflection,
                "synthesis": act1_synthesis,
            },
            {
                "title": "Ascent",
                "week_range": "Weeks 5-9",
                "inflection": act2_inflection,
                "synthesis": act2_synthesis,
            },
            {
                "title": "Coronation",
                "week_range": "Weeks 10+",
                "inflection": act3_inflection,
                "synthesis": act3_synthesis,
            },
        ],
        confidence_ok=True,
        flag_for_review=True,
        rationale=(
            f"Auto-drafted from Signature Story (rank {rank}/{cohort_size}, "
            f"pct {percentile}), {ach_count} achievements, and Hot-Take pairing."
        ),
    )
    return draft


def draft_arc_to_dict(draft: DraftArc) -> dict[str, Any]:
    return {
        "player_name": draft.player_name,
        "season": draft.season,
        "acts": list(draft.acts),
        "flag_for_review": draft.flag_for_review,
        "rationale": draft.rationale,
        "auto_generated": True,
    }
