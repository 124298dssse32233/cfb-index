from __future__ import annotations

from collections import Counter
from functools import lru_cache
import math
import re
from typing import Iterable


_TOKEN_RE = re.compile(r"[a-z0-9']+")

_STOPWORDS = {
    "a",
    "about",
    "after",
    "all",
    "also",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "but",
    "by",
    "can",
    "com",
    "comment",
    "comments",
    "did",
    "do",
    "for",
    "from",
    "game",
    "games",
    "get",
    "got",
    "had",
    "has",
    "have",
    "he",
    "her",
    "here",
    "him",
    "his",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "http",
    "https",
    "just",
    "like",
    "more",
    "most",
    "my",
    "new",
    "no",
    "not",
    "now",
    "of",
    "on",
    "or",
    "our",
    "out",
    "over",
    "post",
    "posts",
    "reddit",
    "really",
    "said",
    "season",
    "so",
    "team",
    "teams",
    "that",
    "the",
    "their",
    "them",
    "they",
    "this",
    "thread",
    "threads",
    "to",
    "too",
    "up",
    "was",
    "we",
    "week",
    "were",
    "what",
    "when",
    "who",
    "why",
    "with",
    "would",
    "www",
    "you",
    "your",
}

_EMOTION_LEXICON = {
    "joy": {"excited", "elite", "great", "happy", "hype", "love", "rolling", "thrilled", "win"},
    "anger": {"awful", "embarrassing", "fire", "furious", "hate", "pathetic", "pissed", "trash"},
    "fear": {"afraid", "anxious", "concerned", "nervous", "panic", "scared", "worry", "worried"},
    "trust": {"believe", "calm", "confident", "legit", "real", "steady", "trust"},
    "sadness": {"broken", "crushed", "depressed", "heartbroken", "sad", "upset"},
    "surprise": {"stunned", "surprised", "unexpected", "wild", "wow"},
}


# -----------------------------------------------------------------------------
# CFB meme / sarcasm lexicon
#
# This is intentionally a hand-built rules layer. It is not a substitute for a
# real irony classifier, but it gives the pipeline a fighting chance against
# the most common public-web patterns where plain sentiment gets it wrong.
#
# Each entry stores a normalized phrase plus a tag indicating what kind of
# sarcasm/meme risk it signals. Downstream code uses these to bias confidence,
# not to override the underlying sentiment score.
# -----------------------------------------------------------------------------


CFB_MEME_PHRASES: tuple[tuple[str, str], ...] = (
    # Victory-lap / "we're back" copium — frequently sarcastic when the team
    # just lost, frequently sincere when they just won. Context determines
    # which. Downstream confidence gate decides how to react.
    ("we are so back", "victory_lap"),
    ("we're so back", "victory_lap"),
    ("so back", "victory_lap"),
    ("natty bound", "victory_lap"),
    ("national championship bound", "victory_lap"),
    ("heisman campaign starts now", "victory_lap"),
    ("heisman szn", "victory_lap"),
    ("book it", "victory_lap"),
    ("run the table", "victory_lap"),
    ("we want bama", "victory_lap"),
    ("we want alabama", "victory_lap"),
    ("we want georgia", "victory_lap"),

    # Doomposting patterns — commonly sarcastic during winning streaks, commonly
    # genuine during losing streaks.
    ("it is so over", "doompost"),
    ("it's so over", "doompost"),
    ("it's over", "doompost"),
    ("this program is cooked", "doompost"),
    ("we're cooked", "doompost"),
    ("fire everyone", "doompost"),
    ("blow it up", "doompost"),
    ("back to the drawing board", "doompost"),
    ("same as always", "doompost"),
    ("here we go again", "doompost"),
    ("not again", "doompost"),

    # Irony markers common on Reddit / X / Bluesky.
    ("/s", "explicit_irony"),
    ("yeah right", "explicit_irony"),
    ("sure jan", "explicit_irony"),
    ("as if", "explicit_irony"),
    ("totally normal", "explicit_irony"),
    ("lol sure", "explicit_irony"),
    ("what could go wrong", "explicit_irony"),
    ("this is fine", "explicit_irony"),
    ("never doubted", "explicit_irony"),
    ("never in doubt", "explicit_irony"),
    ("love this for us", "explicit_irony"),
    ("living my best life", "explicit_irony"),
    ("exactly what i expected", "explicit_irony"),

    # Rival-bait / taunt phrases. Dangerous because they frequently register as
    # positive sentiment about the target team while carrying the opposite
    # social payload.
    ("scoreboard", "rival_bait"),
    ("stay humble", "rival_bait"),
    ("how about them", "rival_bait"),
    ("cope harder", "rival_bait"),
    ("cry more", "rival_bait"),
    ("get fitted for", "rival_bait"),
    ("paper champions", "rival_bait"),
    ("paper tigers", "rival_bait"),
    ("bag fumbled", "rival_bait"),
    ("fraud", "rival_bait"),
    ("overrated", "rival_bait"),
    ("rent free", "rival_bait"),
    ("little brother", "rival_bait"),
    ("embrace the hate", "rival_bait"),
    ("t shirt fan", "rival_bait"),
    ("t-shirt fan", "rival_bait"),
    ("melt", "rival_bait"),
    ("meltdown", "rival_bait"),

    # Sarcastic-praise patterns that the plain sentiment model reliably
    # misreads as optimism.
    ("great job", "sarcastic_praise"),
    ("great coaching", "sarcastic_praise"),
    ("great play calling", "sarcastic_praise"),
    ("great play call", "sarcastic_praise"),
    ("truly elite", "sarcastic_praise"),
    ("elite", "sarcastic_praise"),
    ("big brain", "sarcastic_praise"),
    ("genius move", "sarcastic_praise"),
    ("amazing decision", "sarcastic_praise"),
    ("wonderful", "sarcastic_praise"),
    ("copium", "explicit_irony"),
    ("hopium", "explicit_irony"),
    ("battered aggie syndrome", "doompost"),
)


_SARCASM_RISK_WEIGHTS: dict[str, float] = {
    "explicit_irony": 1.0,
    "sarcastic_praise": 0.8,
    "rival_bait": 0.6,
    "doompost": 0.35,
    "victory_lap": 0.35,
}

_CFB_CONTEXT_PHRASES = {
    "college football",
    "spring game",
    "spring ball",
    "spring practice",
    "transfer portal",
    "depth chart",
    "fall camp",
    "post spring",
    "post-spring",
    "orange and white",
    "orange white game",
    "spring showcase",
    "maize vs blue",
    "g day",
    "g-day",
    "a day",
    "a-day",
}

_CFB_CONTEXT_TOKENS = {
    "football",
    "cfb",
    "qb",
    "qbs",
    "quarterback",
    "rb",
    "rbs",
    "wr",
    "wrs",
    "receiver",
    "receivers",
    "te",
    "tes",
    "ol",
    "oline",
    "dline",
    "dl",
    "dt",
    "de",
    "lb",
    "lbs",
    "db",
    "dbs",
    "linebacker",
    "linebackers",
    "cornerback",
    "cornerbacks",
    "safety",
    "safeties",
    "secondary",
    "edge",
    "edges",
    "cb",
    "cbs",
    "offense",
    "offensive",
    "defense",
    "defensive",
    "portal",
    "recruiting",
    "recruit",
    "commit",
    "commits",
    "decommit",
    "decommits",
    "practice",
    "scrimmage",
    "coordinator",
    "touchdown",
    "natty",
    "playoff",
    "cfp",
    "bowl",
    "season",
    "schedule",
    "camp",
    "sickos",
    "croots",
}

_NON_FOOTBALL_TOKENS = {
    "baseball",
    "softball",
    "basketball",
    "volleyball",
    "gymnastics",
    "hockey",
    "soccer",
    "lacrosse",
    "wrestling",
    "tennis",
    "golf",
}

_CFB_REDDIT_OFF_TOPIC_PHRASES = {
    "free talk thread",
    "off topic free talk thread",
    "off topic",
    "off-topic",
    "daily off topic",
    "daily off-topic",
}

_CFB_REDDIT_STRONG_PHRASES = {
    "college football",
    "spring game",
    "spring ball",
    "spring practice",
    "fall camp",
    "maize vs blue",
    "g day",
    "g-day",
    "a day",
    "a-day",
    "orange white game",
    "orange and white",
    "qb battle",
    "post spring",
    "post-spring",
}

_CFB_REDDIT_STRONG_TOKENS = {
    "football",
    "cfb",
    "qb",
    "qbs",
    "quarterback",
    "quarterbacks",
    "rb",
    "rbs",
    "wr",
    "wrs",
    "te",
    "tes",
    "oline",
    "dline",
    "linebacker",
    "linebackers",
    "secondary",
    "cornerback",
    "cornerbacks",
    "safety",
    "safeties",
    "edge",
    "edges",
    "cb",
    "cbs",
    "offense",
    "offensive",
    "defense",
    "defensive",
    "touchdown",
    "scrimmage",
    "croots",
}

_CFB_REDDIT_AMBIGUOUS_PHRASES = {
    "transfer portal",
    "depth chart",
    "post spring",
    "post-spring",
}

_CFB_REDDIT_AMBIGUOUS_TOKENS = {
    "portal",
    "recruit",
    "recruits",
    "recruiting",
    "commit",
    "commits",
    "decommit",
    "decommits",
    "practice",
    "camp",
}

_NON_CFB_REDDIT_PHRASES = {
    "womens basketball",
    "women s basketball",
    "mens basketball",
    "men s basketball",
    "lady vols",
    "final four",
    "sweet 16",
    "elite eight",
    "point guard",
    "shooting guard",
    "small forward",
    "power forward",
    "free throw",
    "three point",
    "three pointer",
    "home run",
    "college world series",
    "starting pitcher",
    "sec tournament",
    "ncaa tournament",
}

_NON_CFB_REDDIT_TOKENS = _NON_FOOTBALL_TOKENS | {
    "guard",
    "guards",
    "forward",
    "forwards",
    "rebound",
    "rebounds",
    "assist",
    "assists",
    "hoops",
    "dunk",
    "dunks",
    "pitcher",
    "pitchers",
    "inning",
    "innings",
    "homer",
    "homers",
    "batting",
    "bullpen",
}

_CFB_DEDICATED_SUBREDDIT_MARKERS = {
    "football",
    "cfb",
    "collegefootball",
}

_BASKETBALL_POSITION_TOKEN_RE = re.compile(r"\b(?:pg|sg|sf|pf)\b")
_BASKETBALL_LINEUP_RE = re.compile(r"(?<![a-z])(?:g|f|c)\s+[a-z]{2,}")


def normalize_lookup_text(value: str) -> str:
    lowered = value.lower().strip()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", lowered)).strip()


def football_context_score(text: str) -> float:
    normalized = normalize_lookup_text(text)
    if not normalized:
        return 0.0

    tokens = set(tokenize(normalized))
    score = 0.0
    for phrase in _CFB_CONTEXT_PHRASES:
        if phrase in normalized:
            score += 1.0
    score += 0.35 * sum(1 for token in tokens if token in _CFB_CONTEXT_TOKENS)

    if tokens & _NON_FOOTBALL_TOKENS and not (tokens & _CFB_CONTEXT_TOKENS):
        score -= 1.0
    return round(max(0.0, min(1.0, score / 2.5)), 4)


def is_probably_cfb_text(text: str) -> bool:
    return football_context_score(text) >= 0.35


def is_probably_cfb_reddit_post(
    title: str,
    body: str = "",
    subreddit: str | None = None,
    source_prior: bool = False,
) -> bool:
    text = " ".join(part for part in [title or "", body or ""] if part).strip()
    normalized = normalize_lookup_text(text)
    if not normalized:
        return False

    if any(phrase in normalized for phrase in _CFB_REDDIT_OFF_TOPIC_PHRASES):
        return False

    tokens = set(tokenize(normalized))
    strong_hits = _phrase_hits(normalized, _CFB_REDDIT_STRONG_PHRASES) + _token_hits(tokens, _CFB_REDDIT_STRONG_TOKENS)
    ambiguous_hits = _phrase_hits(normalized, _CFB_REDDIT_AMBIGUOUS_PHRASES) + _token_hits(tokens, _CFB_REDDIT_AMBIGUOUS_TOKENS)
    non_cfb_hits = _phrase_hits(normalized, _NON_CFB_REDDIT_PHRASES) + _token_hits(tokens, _NON_CFB_REDDIT_TOKENS)
    basketball_roster_hits = _basketball_roster_marker_hits(normalized)
    non_cfb_hits += basketball_roster_hits
    score = football_context_score(text)
    is_dedicated_subreddit = _is_cfb_dedicated_subreddit(subreddit)

    if basketball_roster_hits > 0 and strong_hits == 0:
        return False
    if non_cfb_hits >= 2 and strong_hits == 0:
        return False

    if source_prior:
        if non_cfb_hits > 0 and strong_hits == 0:
            return False
        if strong_hits > 0:
            return score >= 0.28
        return ambiguous_hits >= 1

    if not is_dedicated_subreddit:
        if strong_hits == 0:
            return False
        if non_cfb_hits > strong_hits:
            return False
        return score >= 0.35

    if strong_hits == 0 and ambiguous_hits < 2 and score < 0.45:
        return False
    if non_cfb_hits > strong_hits and score < 0.55:
        return False
    return score >= 0.2 or strong_hits > 0


def score_sentiment(text: str) -> dict[str, float | str | None]:
    analyzer = _sentiment_analyzer()
    compound = float(analyzer.polarity_scores(text or "").get("compound") or 0.0)
    if compound >= 0.15:
        label = "positive"
    elif compound <= -0.15:
        label = "negative"
    else:
        label = "neutral"

    meme_hits = detect_meme_phrases(text)
    primary, secondary, emotion_scores = detect_emotions(text)
    sarcasm_score = detect_sarcasm(text, meme_hits=meme_hits, compound=compound)
    toxicity_score = detect_toxicity(text)
    confidence_score = _confidence_score(
        text=text,
        compound=compound,
        sarcasm_score=sarcasm_score,
        meme_hits=meme_hits,
    )
    adjusted_label = _adjust_sentiment_label(label, compound, sarcasm_score, meme_hits)
    return {
        "sentiment_label": adjusted_label,
        "sentiment_score": compound,
        "emotion_primary": primary,
        "emotion_secondary": secondary,
        "sarcasm_score": sarcasm_score,
        "toxicity_score": toxicity_score,
        "confidence_score": confidence_score,
        "emotion_scores": emotion_scores,
        "meme_hits": meme_hits,
    }


@lru_cache(maxsize=1)
def _sentiment_analyzer():
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    except ImportError as exc:
        raise RuntimeError(
            "Missing optional dependency 'vaderSentiment'. Install project dependencies before building conversation features."
        ) from exc
    return SentimentIntensityAnalyzer()


def detect_emotions(text: str) -> tuple[str | None, str | None, dict[str, float]]:
    tokens = tokenize(text)
    counts: dict[str, float] = {}
    for emotion, lexicon in _EMOTION_LEXICON.items():
        counts[emotion] = float(sum(1 for token in tokens if token in lexicon))
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    primary = ranked[0][0] if ranked and ranked[0][1] > 0 else None
    secondary = ranked[1][0] if len(ranked) > 1 and ranked[1][1] > 0 else None
    return primary, secondary, counts


_MEME_NORMALIZER = re.compile(r"[^a-z0-9/]+")


def detect_meme_phrases(text: str) -> list[dict[str, str]]:
    """Scan text for known CFB internet-language patterns.

    Returns a list of ``{"phrase": ..., "tag": ...}`` hits so downstream
    confidence gates can react differently to doomposting than to rivalry
    bait than to victory-lap sarcasm. Punctuation is normalized away so
    ``we are so back!`` still matches the ``we are so back`` phrase.
    """

    if not text:
        return []
    normalized = _MEME_NORMALIZER.sub(" ", text.lower())
    haystack = f" {normalized} "
    hits: list[dict[str, str]] = []
    seen: set[str] = set()
    for phrase, tag in CFB_MEME_PHRASES:
        needle = f" {phrase} "
        if needle in haystack and phrase not in seen:
            hits.append({"phrase": phrase, "tag": tag})
            seen.add(phrase)
    return hits


def detect_sarcasm(
    text: str,
    meme_hits: list[dict[str, str]] | None = None,
    compound: float | None = None,
) -> float:
    """Return a 0..1 sarcasm-risk score.

    The previous version only looked for a handful of generic irony markers.
    This version also reacts to the CFB meme lexicon and to clashes between
    strongly positive base sentiment and rivalry / sarcastic-praise patterns.
    """

    if meme_hits is None:
        meme_hits = detect_meme_phrases(text)
    if not meme_hits and not text:
        return 0.0

    risk = 0.0
    for hit in meme_hits:
        tag = str(hit.get("tag") or "")
        risk += _SARCASM_RISK_WEIGHTS.get(tag, 0.25)

    # If we saw strong positive sentiment AND rivalry bait or sarcastic-praise
    # patterns, treat the positivity as highly suspect.
    if compound is not None and compound >= 0.45:
        tags = {h.get("tag") for h in meme_hits}
        if "rival_bait" in tags or "sarcastic_praise" in tags:
            risk += 0.4
        if "explicit_irony" in tags:
            risk += 0.5

    return min(1.0, risk)


def detect_toxicity(text: str) -> float:
    lowered = text.lower()
    tokens = tokenize(lowered)
    toxic_words = {"idiot", "moron", "pathetic", "trash", "fraud", "garbage", "stupid"}
    matches = sum(1 for token in tokens if token in toxic_words)
    if matches <= 0:
        return 0.0
    return min(1.0, matches / 3.0)


def tokenize(text: str) -> list[str]:
    return [token for token in _TOKEN_RE.findall((text or "").lower()) if token]


def _phrase_hits(normalized_text: str, phrases: set[str]) -> int:
    return sum(1 for phrase in phrases if phrase in normalized_text)


def _token_hits(tokens: set[str], lexicon: set[str]) -> int:
    return sum(1 for token in tokens if token in lexicon)


def _is_cfb_dedicated_subreddit(subreddit: str | None) -> bool:
    normalized = normalize_lookup_text(subreddit or "")
    if not normalized:
        return False
    collapsed = normalized.replace(" ", "")
    return any(marker in collapsed for marker in _CFB_DEDICATED_SUBREDDIT_MARKERS)


def _basketball_roster_marker_hits(normalized_text: str) -> int:
    hits = 3 * len(_BASKETBALL_POSITION_TOKEN_RE.findall(normalized_text))
    if len(_BASKETBALL_LINEUP_RE.findall(normalized_text)) >= 2:
        hits += 2
    return hits


def extract_keywords(texts: Iterable[str], top_n: int = 6) -> list[str]:
    counter: Counter[str] = Counter()
    for text in texts:
        for token in tokenize(text):
            if len(token) < 4 or token in _STOPWORDS or token.isdigit():
                continue
            counter[token] += 1
    return [token for token, _ in counter.most_common(top_n)]


def sample_quality_score(
    mention_count: int,
    unique_author_count: int,
    subchannel_count: int,
) -> float:
    if mention_count <= 0:
        return 0.0
    mention_factor = min(1.0, mention_count / 20.0)
    author_factor = min(1.0, unique_author_count / 5.0)
    source_factor = min(1.0, subchannel_count / 3.0)
    return round((mention_factor + author_factor + source_factor) / 3.0, 4)


def attention_score(mention_count: int, unique_author_count: int) -> float:
    if mention_count <= 0:
        return 0.0
    return round(math.log1p(mention_count) * (1.0 + min(1.0, unique_author_count / max(1, mention_count))), 4)


def _adjust_sentiment_label(
    label: str,
    compound: float,
    sarcasm_score: float,
    meme_hits: list[dict[str, str]],
) -> str:
    """Downgrade obviously sarcastic positives to a neutral label.

    We do not flip positive → negative (that is a different research problem),
    but it is much better to treat sarcastic-praise "great coaching" as
    neutral than to count it as a genuine positive.
    """

    if label == "positive" and sarcasm_score >= 0.65:
        tags = {hit.get("tag") for hit in meme_hits}
        if tags & {"sarcastic_praise", "rival_bait", "explicit_irony"}:
            return "neutral"
    if label == "negative" and sarcasm_score >= 0.75:
        tags = {hit.get("tag") for hit in meme_hits}
        if "explicit_irony" in tags and compound > -0.6:
            # "it is so over /s" — likely not a real doompost
            return "neutral"
    return label


def _confidence_score(
    text: str,
    compound: float,
    sarcasm_score: float,
    meme_hits: list[dict[str, str]] | None = None,
) -> float:
    token_count = len(tokenize(text))
    text_factor = min(1.0, token_count / 20.0)
    signal_factor = min(1.0, abs(compound) / 0.6) if compound else 0.35
    sarcasm_penalty = max(0.0, 1.0 - sarcasm_score * 0.5)
    meme_penalty = 1.0
    if meme_hits:
        meme_tags = {h.get("tag") for h in meme_hits}
        if "explicit_irony" in meme_tags:
            meme_penalty = 0.75
        elif "sarcastic_praise" in meme_tags or "rival_bait" in meme_tags:
            meme_penalty = 0.85
    return round(
        max(
            0.05,
            min(1.0, text_factor * 0.5 + signal_factor * 0.5) * sarcasm_penalty * meme_penalty,
        ),
        4,
    )
