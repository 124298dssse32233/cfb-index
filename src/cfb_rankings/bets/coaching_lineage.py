"""Coaching Lineage + System Context — S2.9 / §4 Bet #11.

Loads ``seeds/coaching_lineage.yaml`` (hand-authored for the top
programs) and resolves per-team lineage payloads for the player-page
renderer. Future upgrade: when CFBD / ingestion pipelines populate
database-side coach tables, a loader here can prefer the DB and fall
back to YAML for programs not yet threaded through.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML required") from exc


_SEED_PATH = (
    Path(__file__).resolve().parents[3] / "seeds" / "coaching_lineage.yaml"
)


@lru_cache(maxsize=1)
def _load_seed() -> dict[str, dict[str, Any]]:
    if not _SEED_PATH.exists():
        return {}
    data = yaml.safe_load(_SEED_PATH.read_text(encoding="utf-8")) or {}
    out: dict[str, dict[str, Any]] = {}
    for slug, row in (data.get("programs") or {}).items():
        if not isinstance(row, dict):
            continue
        out[str(slug).strip().lower()] = row
    return out


def fetch_coaching_lineage(team_slug: str | None) -> dict[str, Any] | None:
    """Return the coaching lineage payload for a team, or None."""
    if not team_slug:
        return None
    key = str(team_slug).strip().lower()
    return _load_seed().get(key)
