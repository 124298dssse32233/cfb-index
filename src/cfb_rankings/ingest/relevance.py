"""Lexical football-relevance signal for conversation documents.

Task #6 (relevance filtering): ~72% of team-tagged docs are off-topic, mostly
concentrated in CITY / UNIVERSITY subchannels that get tagged to a team only via
a place/school name ("the Chipotle closed", campus life, ticket sales).

This module provides a CHEAP, dependency-free football-relevance signal built
from the labeling rubric's vocabulary (docs/labeling_rubric.md). It is used two
ways, both aligned with the existing zero-false-negative design
(`conversation.OFFTOPIC_SUBREDDITS`):

  1. MEASUREMENT — `scripts/relevance_audit.py` scores a sample to quantify the
     off-topic rate per source/subchannel and surface new blocklist candidates.
  2. (future) a stored per-doc score / SetFit feature.

It is intentionally NOT wired as a per-doc hard filter: lexical anchors have
false negatives (pure-hype posts like "WE'RE SO BACK" carry no football noun),
so `is_football` is a high-precision / lower-recall signal — a floor on
relevance, not a verdict. Treat a LOW score as "needs a better judge", never as
"definitely drop".
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Strong anchors: presence strongly implies the text is about football. Grouped
# into categories so a score can reward topical breadth, not just one keyword.
_CATEGORIES: dict[str, list[str]] = {
    "position": [
        "quarterback", "running back", "wide receiver", "tight end",
        "offensive line", "defensive line", "o-line", "d-line", "linebacker",
        "cornerback", "safety", "edge rusher", "kicker", "punter",
        "long snapper", "qb", "rb", "wr", "te", "qb1", "qb2",
    ],
    "gameplay": [
        "touchdown", "field goal", "interception", "fumble", "sack", "blitz",
        "red zone", "pick six", "play action", "rushing yards", "passing yards",
        "completion", "snap count", "third down", "two-point", "pick-six",
    ],
    "structure": [
        "offense", "defense", "special teams", "depth chart", "playbook",
        "scheme", "formation", "secondary", "front seven", "backfield",
        "spring game", "fall camp", "spring ball", "scrimmage", "two-deep",
    ],
    "recruiting": [
        "recruit", "recruiting", "commit", "commitment", "decommit", "de-commit",
        "five-star", "four-star", "three-star", "5-star", "4-star", "3-star",
        "transfer portal", "portal", "signee", "signing day", "nil", "nil deal",
        "official visit", "reclassify", "class of 20", "247", "on3",
    ],
    "coaching": [
        "head coach", "coordinator", "offensive coordinator",
        "defensive coordinator", "hot seat", "buyout", "coaching staff",
        "play caller", "play-caller", "fire the coach", "coaching change",
    ],
    "season": [
        "kickoff", "playoff", "college football playoff", "cfp", "bowl game",
        "national championship", "natty", "conference championship", "ap poll",
        "top 25", "gameday", "season opener", "rivalry", "week 1", "week one",
        "schedule release", "ranked", "preseason",
    ],
}


def _compile(words: list[str]) -> re.Pattern[str]:
    # Word-bounded, longest-first so multi-word phrases win; '#'-free.
    # The (?:...) group is load-bearing: without it the lookbehind binds only
    # to the FIRST alternative and the lookahead only to the LAST, so middle
    # words match as bare substrings — and since same-length ties in sorted()
    # keep set-iteration order (PYTHONHASHSEED-dependent), WHICH words got
    # boundaries varied per process (found 2026-06-10: gate rates differed
    # 36% vs 58% across identical runs).
    alt = "|".join(re.escape(w) for w in sorted(set(words), key=len, reverse=True))
    return re.compile(rf"(?<![a-z0-9])(?:{alt})(?![a-z0-9])", re.IGNORECASE)


_CATEGORY_RES: dict[str, re.Pattern[str]] = {k: _compile(v) for k, v in _CATEGORIES.items()}


@dataclass(frozen=True)
class RelevanceSignal:
    score: int          # number of distinct football categories matched (0..6)
    categories: tuple[str, ...]
    is_football: bool   # score >= 1 (any strong anchor present)


def score_text(text: str) -> RelevanceSignal:
    """Return the football-relevance signal for a document's text."""
    t = text or ""
    hits = tuple(cat for cat, rx in _CATEGORY_RES.items() if rx.search(t))
    return RelevanceSignal(score=len(hits), categories=hits, is_football=bool(hits))


__all__ = ["RelevanceSignal", "score_text"]
