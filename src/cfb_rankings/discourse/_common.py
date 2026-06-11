"""Shared discourse-engine helpers — Language Layer Wave 2.

Factored out so the Wave-2 engines (``mirror.py``, ``voice_profile.py``) reuse
the exact fan-voice corpus definition and the generic-term stoplist instead of
re-deriving them. Wave-1 ``keyness.py`` defines the canonical source-filter SQL
inline; this module mirrors that definition once (the SAME predicate, verbatim)
so every Wave-2 cut measures the same corpus.

PYTHONUTF8 note: like keyness.py, nothing here prints raw post text.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

# Reuse the Wave-1 seed loader + city-sub set so all engines share one corpus
# definition. (keyness.py owns these; import rather than copy.)
from .keyness import _load_yaml_seed, load_city_subs

_ROOT = Path(__file__).resolve().parents[3]
_GENERIC_SEED = _ROOT / "seeds" / "discourse_generic_terms.yaml"


def load_generic_terms() -> set[str]:
    """Editorial generic-term stoplist (``seeds/discourse_generic_terms.yaml``).

    Conversational / thread boilerplate that survived Wave-1 cleaning. Excluded
    from every Wave-2 output. Missing file / missing pyyaml -> empty set (the
    engine never crashes on a missing seed — degrades to no extra exclusions).
    """
    terms: set[str] = set()
    data = _load_yaml_seed(_GENERIC_SEED)
    if isinstance(data, dict):
        for value in data.get("generic_terms") or []:
            if value:
                terms.add(str(value).strip().lower())
    terms.discard("")
    return terms


# Fan-voice corpus predicate (verbatim shape from keyness.py's doc_sql WHERE
# clause). Reddit / Bluesky / YouTube / boards only, soft-deleted excluded,
# city/residential subchannels excluded. Callers bind the city placeholders.
def fan_voice_filter_sql(alias: str = "d") -> tuple[str, dict[str, str]]:
    """Return ``(where_fragment, city_params)`` for the fan-voice corpus.

    ``where_fragment`` is a boolean SQL expression (no leading ``WHERE``/``AND``)
    that callers AND into their own query against ``conversation_documents``
    aliased as ``alias``. ``city_params`` must be passed as bind parameters.

    Mirrors the keyness.py corpus definition exactly so every Wave-2 cut measures
    the same fan-voice corpus the Lexicon does.
    """
    city_subs = load_city_subs()
    city_params = {f"city_{i}": s for i, s in enumerate(sorted(city_subs))}
    city_placeholders = ", ".join(f":{k}" for k in city_params) or "''"
    where = (
        f"COALESCE({alias}.is_deleted,0) = 0 "
        f"AND COALESCE({alias}.is_removed,0) = 0 "
        f"AND ({alias}.body_text IS NOT NULL OR {alias}.title_text IS NOT NULL) "
        f"AND ({alias}.source_name LIKE 'reddit%' "
        f"OR {alias}.source_name LIKE 'bluesky%' "
        f"OR {alias}.source_name LIKE 'youtube%' "
        f"OR {alias}.source_name LIKE 'board%') "
        f"AND COALESCE({alias}.source_subchannel,'') NOT IN ({city_placeholders}) "
        f"AND (COALESCE({alias}.relevance_ml_score, 1.0) >= 0.5)"
    )
    return where, city_params


__all__ = ["load_generic_terms", "fan_voice_filter_sql"]
