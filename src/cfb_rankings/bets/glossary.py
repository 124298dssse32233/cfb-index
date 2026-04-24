"""Fan Intelligence Glossary — loader + JSON payload builder (Bet #5, S1.1).

The glossary is authored in ``seeds/fi_glossary.yaml`` and surfaced on
every player / team / fan-intel page as a small ``?`` button next to any
FI eyebrow label. Clicking the button opens a native ``<dialog>`` popover
with the term's definition and a micro-example.

This module is deliberately tiny: load the YAML once, expose a dict by
slug, and serialize the trimmed payload used by the client-side script
at ``static_assets/js/bets/glossary.js``.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError as exc:  # pragma: no cover - yaml is a hard dep
    raise RuntimeError(
        "PyYAML is required to load seeds/fi_glossary.yaml — `pip install pyyaml`"
    ) from exc


_SEED_PATH = Path(__file__).resolve().parents[3] / "seeds" / "fi_glossary.yaml"


@lru_cache(maxsize=1)
def load_glossary() -> dict[str, dict[str, Any]]:
    """Return {slug: term_dict} loaded from seeds/fi_glossary.yaml.

    Raises if the file is missing or malformed — glossary is a hard
    dependency of the render pipeline.
    """
    if not _SEED_PATH.exists():
        raise FileNotFoundError(f"Missing glossary seed at {_SEED_PATH}")
    data = yaml.safe_load(_SEED_PATH.read_text(encoding="utf-8")) or {}
    terms = data.get("terms") or []
    out: dict[str, dict[str, Any]] = {}
    required = ("name", "slug", "one_line", "full", "micro_example")
    for row in terms:
        if not isinstance(row, dict):
            continue
        missing = [k for k in required if not row.get(k)]
        if missing:
            raise ValueError(
                f"fi_glossary.yaml entry {row.get('slug') or row.get('name')!r} "
                f"is missing required fields: {missing}"
            )
        slug = str(row["slug"]).strip().lower()
        out[slug] = {
            "name": str(row["name"]).strip(),
            "slug": slug,
            "one_line": str(row["one_line"]).strip(),
            "full": str(row["full"]).strip(),
            "micro_example": str(row["micro_example"]).strip(),
            "see_also": list(row.get("see_also") or []),
        }
    return out


def glossary_payload_js() -> str:
    """Return the content of ``/assets/js/bets/fi-glossary-data.js``.

    The file sets ``window.__FI_GLOSSARY__`` to the full term dict so
    the client-side popover can look up a slug without a round trip.
    """
    payload = json.dumps(load_glossary(), ensure_ascii=False, separators=(",", ":"))
    return (
        "/*! fi-glossary-data.js — generated from seeds/fi_glossary.yaml at build time. */\n"
        f"window.__FI_GLOSSARY__ = {payload};\n"
    )


def glossary_slugs() -> list[str]:
    """Convenience: sorted list of known slugs (used by tests + Haiku audits)."""
    return sorted(load_glossary().keys())
