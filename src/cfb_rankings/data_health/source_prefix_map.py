"""Heuristic instance -> source-class map for the multi-class prefixes.

WHY THIS EXISTS
---------------
The freshness pillar (``checks/freshness.py``) reconciles ``scrape_health``
*instances* (every collector that ever ran) against ``source_registry``
*classes* (the contract catalog). For most instances the reconciliation is
exact: the instance id IS a registry class (``cfbd``, ``polymarket``, the
``*_template`` rows), or it carries one of the four authorised single-class
prefixes (athletics/campus/locked/google).

Five prefixes, though, fan out to MANY registry classes and so cannot be
auto-parented by string-prefix alone (the spec forbids guessing an instance
into a multi-class parent):

  * ``reddit``   -> reddit_alumni / reddit_cfb / reddit_city / reddit_team
  * ``substack`` -> 9 named newsletters (+ substack_template)
  * ``beat``     -> 13 named beat blogs (+ beat_template)
  * ``youtube``  -> youtube_comments_nat / youtube_comments_team / youtube_meta
  * ``board``    -> board_247_free / board_quotes (+ board_template)

Before this map those instances stayed ``unclassified`` (visible, never a wrong
guess). That is correct as a floor, but ~180 instances sitting unclassified
hides real, recoverable structure: ``reddit_rss_alabama`` is OBVIOUSLY the
Alabama team subreddit; ``substack_solid_verbal`` is OBVIOUSLY
``substack_the_solid_verbal``.

WHAT THIS DOES
--------------
``classify_instance(source_id, registry_classes, known_team_slugs=None)``
applies a HEURISTIC, name-based map for those instances, returning a registry
class when the name unambiguously implies exactly one class, and ``None``
otherwise. ``None`` means "leave it unclassified" — the conservative default
the freshness pillar already understands. We never return a class we are not
sure of: a mis-attributed feed (e.g. an independent fan board folded into
``board_247_free``) would silently corrupt the per-class health roll-up, which
is far worse than a visible ``unclassified`` row.

HEURISTIC, NOT CONFIG — REVIEW NOTE
-----------------------------------
This is a reviewable HEURISTIC pending a fully hand-reviewed instance->class
config. Every rule here is intentionally conservative and self-explaining via
the ``reason`` returned by :func:`classify_instance_explained`. The rules:

  reddit_rss_<team-slug>          -> reddit_team   (only when <team-slug> is a
                                                    known FBS/teams.slug value)
  reddit_backfill_<x>_team        -> reddit_team
  reddit_backfill_<x>_city        -> reddit_city
  substack_<tokens>               -> the ONE registry substack_* class whose
                                      token set is a unique superset of <tokens>
  youtube_comments_<nat|team>     -> youtube_comments_{nat,team}
  youtube_meta                    -> youtube_meta
  board_*                         -> None (independent fan boards have no
                                      per-board registry class; do NOT fold them
                                      into board_247_free / board_quotes)

Anything not matched returns ``None``. Stdlib only; no DB access (the caller
passes ``known_team_slugs`` derived read-only from ``teams.slug``).
"""
from __future__ import annotations

from typing import Iterable, Optional

# The multi-class prefixes this map is responsible for. Mirrors
# ``freshness.MULTI_CLASS_PREFIXES`` (kept as a local copy so this module is
# import-cycle-free; the two are asserted equal in the tests).
MULTI_CLASS_PREFIXES = frozenset({"reddit", "substack", "beat", "youtube", "board"})


def _registry_set(registry_classes: Iterable[str]) -> set[str]:
    return {str(c) for c in registry_classes if c is not None}


def _classify_reddit(
    source_id: str,
    registry: set[str],
    known_team_slugs: Optional[set[str]],
) -> tuple[Optional[str], str]:
    """reddit_* instances -> reddit_team / reddit_city (or None)."""
    # reddit_rss_<team-slug>: a per-team team subreddit feed. Only attribute it
    # to reddit_team when <slug> is a KNOWN team slug — otherwise we have no
    # business asserting it is a team (could be a future city/alumni feed).
    if source_id.startswith("reddit_rss_"):
        if "reddit_team" not in registry:
            return None, "reddit_team not in registry"
        slug = source_id[len("reddit_rss_") :]
        if known_team_slugs is None:
            # No slug universe supplied -> stay conservative, do not guess.
            return None, "reddit_rss but no known_team_slugs provided"
        if slug in known_team_slugs:
            return "reddit_team", f"reddit_rss_<slug>='{slug}' is a known team slug"
        return None, f"reddit_rss_<slug>='{slug}' not a known team slug"

    # reddit_backfill_<program>_<team|city>: the suffix token IS the class hint.
    if source_id.startswith("reddit_backfill_"):
        if source_id.endswith("_team"):
            if "reddit_team" in registry:
                return "reddit_team", "reddit_backfill_*_team suffix"
            return None, "reddit_team not in registry"
        if source_id.endswith("_city"):
            if "reddit_city" in registry:
                return "reddit_city", "reddit_backfill_*_city suffix"
            return None, "reddit_city not in registry"
        return None, "reddit_backfill_* with unrecognised suffix"

    # reddit_alumni / reddit_cfb / reddit_city / reddit_team handle themselves
    # via exact-match upstream; anything else under reddit_ stays unclassified.
    return None, "unrecognised reddit_* instance"


def _classify_substack(
    source_id: str,
    registry: set[str],
) -> tuple[Optional[str], str]:
    """substack_<tokens> -> the unique registry substack class it abbreviates.

    The instance names are lossy abbreviations of the registry class names
    (``substack_solid_verbal`` for ``substack_the_solid_verbal``). We match by
    token-set containment and require EXACTLY ONE registry candidate — if zero
    or several classes contain the instance's tokens, we stay unclassified
    rather than pick one.
    """
    tokens = set(source_id.split("_")[1:])  # drop the 'substack' prefix token
    if not tokens:
        return None, "substack_ with no discriminating tokens"

    candidates = []
    for cls in registry:
        if not cls.startswith("substack_"):
            continue
        if cls == "substack_template":
            continue  # never auto-map a real newsletter into the template row
        cls_tokens = set(cls.split("_")[1:])
        if tokens and tokens.issubset(cls_tokens):
            candidates.append(cls)

    if len(candidates) == 1:
        return candidates[0], f"tokens {sorted(tokens)} uniquely match {candidates[0]}"
    if not candidates:
        return None, f"tokens {sorted(tokens)} match no substack class"
    return None, f"tokens {sorted(tokens)} ambiguous across {sorted(candidates)}"


def _classify_youtube(
    source_id: str,
    registry: set[str],
) -> tuple[Optional[str], str]:
    """youtube_* -> youtube_comments_{nat,team} / youtube_meta by suffix.

    Today every live youtube instance exact-matches a registry class upstream,
    so this is mostly future-proofing: if a new ``youtube_comments_<x>`` shows
    up, route it by the nat/team suffix and leave anything else unclassified.
    """
    if source_id.startswith("youtube_comments_"):
        if source_id.endswith("_nat") and "youtube_comments_nat" in registry:
            return "youtube_comments_nat", "youtube_comments_*_nat suffix"
        if source_id.endswith("_team") and "youtube_comments_team" in registry:
            return "youtube_comments_team", "youtube_comments_*_team suffix"
        return None, "youtube_comments_* with unrecognised suffix"
    if source_id == "youtube_meta" and "youtube_meta" in registry:
        return "youtube_meta", "exact youtube_meta"
    return None, "unrecognised youtube_* instance"


def classify_instance_explained(
    source_id: str,
    registry_classes: Iterable[str],
    known_team_slugs: Optional[set[str]] = None,
) -> tuple[Optional[str], str]:
    """Heuristic class for a multi-class-prefix instance, with a reason string.

    Returns ``(class_or_None, reason)``. ``class_or_None`` is a member of
    ``registry_classes`` when the name unambiguously implies it, else ``None``
    (= leave unclassified). The ``reason`` is for review/audit output.

    Only the five multi-class prefixes are handled here; everything else returns
    ``(None, ...)`` because the freshness pillar already classifies it (exact
    match / single-class prefix) before consulting this map.
    """
    sid = str(source_id)
    registry = _registry_set(registry_classes)
    prefix = sid.split("_", 1)[0]

    if prefix not in MULTI_CLASS_PREFIXES:
        return None, "not a multi-class prefix (handled upstream)"

    if prefix == "reddit":
        return _classify_reddit(sid, registry, known_team_slugs)
    if prefix == "substack":
        return _classify_substack(sid, registry)
    if prefix == "youtube":
        return _classify_youtube(sid, registry)
    if prefix == "beat":
        # All live beat_* instances exact-match a registry class upstream. The
        # remainder are named beat blogs with no derivable class -> unclassified.
        return None, "beat_* not exact-matched; no safe heuristic"
    if prefix == "board":
        # board_247_free / board_quotes / board_template exact-match upstream.
        # The independent fan boards (allbuffs, volnation, ...) have NO per-board
        # registry class; folding them into board_247_free would mis-attribute
        # independent boards to a 247Sports class. Stay unclassified.
        return None, "independent fan board; no per-board registry class"

    return None, "unhandled multi-class prefix"


def classify_instance(
    source_id: str,
    registry_classes: Iterable[str],
    known_team_slugs: Optional[set[str]] = None,
) -> Optional[str]:
    """Heuristic class for a multi-class-prefix instance, or ``None``.

    Thin wrapper over :func:`classify_instance_explained` returning just the
    class (or ``None`` to leave the instance unclassified). See the module
    docstring for the (reviewable, conservative) rule set.
    """
    cls, _reason = classify_instance_explained(
        source_id, registry_classes, known_team_slugs
    )
    return cls
