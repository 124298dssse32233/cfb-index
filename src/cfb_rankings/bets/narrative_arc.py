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
