"""PulseState dataclass + sentiment distribution from team_conversation_daily.

Central data model for Sprint 8.5 Pulse v2. All pulse surface renderers
(team pages, conference pages, player Room v2) consume PulseState.

Sentiment for teams is read directly from team_conversation_daily, which
already has positive_doc_count / negative_doc_count / mean_sentiment_score
pre-aggregated by the conversation pipeline. No LLM classification needed
for teams — Sprint 8.5 deferred that to the player corpus only.

Floor rule: sample_size < 100 → sentiment_distribution = None.
Callers must handle None and fall through to stock-phrase fallback.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SENTIMENT_FLOOR = 100        # min sample to show a distribution bar
TOP_ENTITIES_FULL = {        # 4 programs + top conference: get 3 themes each
    "alabama", "ohio-state", "georgia", "notre-dame", "sec",
}
# Expanded 2026-05-17 — was 11 entries covering 6 teams + 5 conferences,
# which left 7 of the 17 profiled programs (per CLAUDE.md's PROFILED_SLUGS)
# without any pulse content. Their team pages rendered the "Awaiting
# Signal" fallback panel even when conversation data was available.
# Now includes every profiled-but-not-FULL team. Cost impact per
# world_class_enrich run after the P1 demote (Pattern B, ~$0.05/call
# × 2 surfaces × 7 new teams) ≈ $0.70 additional — well under the
# tier1.pulse_lede / tier1.pulse_themes_writer 24h ceilings ($5/$8).
TOP_ENTITIES_PARTIAL = {     # next N: get 1 theme + 1 lede each
    # Original 6 teams
    "michigan", "texas", "usc", "penn-state", "tennessee", "auburn",
    # Conferences (unchanged from v5-3)
    "fbs-big-ten", "acc", "big-12", "american-athletic", "mountain-west",
    # 2026-05-17 audit2 expansion — the remaining 7 profiled programs
    "florida", "massachusetts", "oklahoma", "oregon",
    "uconn", "vanderbilt", "washington",
}


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class PulseState:
    entity_slug: str
    entity_type: str        # "team" | "conference" | "player"
    week: str | None        # ISO week string or None for off-season

    # LLM-generated content (None until Phase 2 populated)
    lede: str | None = None
    themes: list[dict[str, Any]] = field(default_factory=list)

    # Sentiment from conversation pipeline
    sentiment_distribution: dict[str, int] | None = None  # positive/neutral/negative counts
    mean_sentiment: float | None = None
    sample_size: int = 0

    # Rendering flags
    is_live: bool = False    # True = LLM-generated themes/lede; False = stock-phrase
    lede_model: str | None = None  # which model wrote the lede ("opus", "sonnet", etc.)


# ---------------------------------------------------------------------------
# Sentiment helpers
# ---------------------------------------------------------------------------

def compute_sentiment_distribution(
    entity_slug: str,
    entity_type: str,
    db_conn: Any,
    days: int = 30,
) -> tuple[dict[str, int] | None, float | None, int]:
    """Return (distribution_dict, mean_sentiment, sample_size) for an entity.

    For teams: reads team_conversation_daily aggregated across all sources for
    the last *days* days.

    For players: reads conversation_document_targets where player_id matches.

    Returns (None, None, 0) when sample_size < SENTIMENT_FLOOR.
    """
    cur = db_conn.cursor()

    if entity_type == "team":
        cur.execute(
            """
            SELECT
                SUM(positive_doc_count),
                SUM(negative_doc_count),
                SUM(mention_count),
                AVG(mean_sentiment_score)
            FROM team_conversation_daily tcd
            JOIN teams t ON t.team_id = tcd.team_id
            WHERE t.slug = ?
              AND tcd.as_of_date >= date('now', ? || ' days')
            """,
            (entity_slug, f"-{days}"),
        )
        row = cur.fetchone()
        if not row or not row[2]:
            return None, None, 0
        pos, neg, total, mean = row
        pos = int(pos or 0)
        neg = int(neg or 0)
        total = int(total or 0)
        neutral = max(0, total - pos - neg)
        if total < SENTIMENT_FLOOR:
            return None, None, total
        return {"positive": pos, "neutral": neutral, "negative": neg}, mean, total

    elif entity_type == "player":
        cur.execute(
            """
            SELECT player_id FROM players
            WHERE player_id = ?
            """,
            (entity_slug,),
        )
        # entity_slug for players is the player_id (int)
        try:
            player_id = int(entity_slug)
        except (ValueError, TypeError):
            return None, None, 0
        cur.execute(
            """
            SELECT
                SUM(CASE WHEN sentiment_label='positive' THEN 1 ELSE 0 END),
                SUM(CASE WHEN sentiment_label='negative' THEN 1 ELSE 0 END),
                SUM(CASE WHEN sentiment_label='neutral' THEN 1 ELSE 0 END),
                COUNT(*)
            FROM conversation_document_targets cdt
            JOIN conversation_documents cd ON cd.conversation_document_id = cdt.conversation_document_id
            WHERE cdt.player_id = ?
              AND cd.collected_at_utc >= datetime('now', ? || ' days')
              AND cdt.sentiment_label IS NOT NULL
            """,
            (player_id, f"-{days}"),
        )
        row = cur.fetchone()
        if not row or not row[3]:
            return None, None, 0
        pos, neg, neutral, total = [int(x or 0) for x in row]
        if total < SENTIMENT_FLOOR:
            return None, None, total
        mean = (pos - neg) / max(1, total)
        return {"positive": pos, "neutral": neutral, "negative": neg}, mean, total

    return None, None, 0


# ---------------------------------------------------------------------------
# State builder (wires in themes + lede from Phase 2 modules)
# ---------------------------------------------------------------------------

def build_pulse_state(
    entity_slug: str,
    entity_type: str,
    db_conn: Any,
    week: str | None = None,
    force_stock_phrase: bool = False,
) -> PulseState:
    """Build a full PulseState for an entity.

    Orchestration order:
    1. Sentiment distribution from DB (no LLM needed).
    2. Themes via pulse_themes.extract_entity_themes() if entity is in top sets.
    3. Lede via pulse_lede.generate_entity_lede() if entity is in top sets.
    4. If entity is not in top sets, or force_stock_phrase=True, skip LLM
       and mark is_live=False — callers render stock-phrase fallback.
    """
    dist, mean_sent, sample = compute_sentiment_distribution(
        entity_slug, entity_type, db_conn
    )
    state = PulseState(
        entity_slug=entity_slug,
        entity_type=entity_type,
        week=week,
        sentiment_distribution=dist,
        mean_sentiment=mean_sent,
        sample_size=sample,
    )

    if force_stock_phrase or (
        entity_slug not in TOP_ENTITIES_FULL
        and entity_slug not in TOP_ENTITIES_PARTIAL
    ):
        return state  # is_live stays False

    # Determine tier: 'full' = 3 themes, 'partial' = 1 theme
    tier = "full" if entity_slug in TOP_ENTITIES_FULL else "partial"

    # Phase 2 modules — imported lazily so this file loads cleanly before
    # pulse_themes.py / pulse_lede.py exist on disk.
    try:
        from cfb_rankings.team_pages import pulse_themes, pulse_lede
    except ImportError:
        return state  # Phase 2 not yet installed; return with sentiment only

    themes = pulse_themes.extract_entity_themes(entity_slug, entity_type, tier, db_conn)
    lede_model = "opus" if entity_slug in {"alabama", "ohio-state", "georgia"} else "sonnet"
    lede_result = pulse_lede.generate_entity_lede(
        entity_slug, entity_type, themes, lede_model, db_conn
    )

    state.themes = themes
    state.lede = lede_result.get("text")
    state.lede_model = lede_model
    state.is_live = bool(state.lede or state.themes)

    return state
