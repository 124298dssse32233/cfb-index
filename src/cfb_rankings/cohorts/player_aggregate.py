"""player_week_conversation_features aggregator.

Turns row-level player-scoped target rows
(`conversation_document_targets` WHERE target_type='player'
 AND player_id IS NOT NULL) into the `player_week_conversation_features`
aggregate table consumed by `fetch_player_mood_profile` and the
`#the-room` template slot on player pages.

Grammar mirrors `cohorts/aggregate.py` but uses the 4-bucket
(fan | rival | national | media) audience model from
PLAYER_PAGE_WORLD_CLASS_BRIEF.md §4.2, not the STRATEGY §4 cohort axes.

Today this runs as a no-op against the live DB (zero player_id rows).
When upstream extraction populates `player_id`, calling this writes
the aggregate immediately — no schema churn needed.

CLI: ``python manage.py compute-player-week-mood --week=YYYY-WW``.

Gating rules (same as team scope, per
FAN_INTEL_SOURCE_STRATEGY.md §4):

    mention_count < 12             → row still written, consumers gate
    confidence_floor: 'sample' when 12 ≤ mention_count < 40
                      'ok' otherwise
    sarcasm_risk aggregated from avg sarcasm_score on the raw rows.

Upsert uses the `ux_pwcf_keys` unique index defined in
migrations/20260423_01_player_conversation_features.sql.
"""
from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

from cfb_rankings.db import Database

logger = logging.getLogger(__name__)

# Bucket vocabulary mirrors the team-scope adapter.
AUDIENCE_BUCKETS: tuple[str, ...] = ("fan", "rival", "national", "media")

# Sentiment classification cutoffs. Same as the team-scope implementation.
POS_CUTOFF = 0.1
NEG_CUTOFF = -0.1

SAMPLE_SIGNAL_FLOOR = 12        # below → row still written, UI shows Awaiting Signal
SAMPLE_STANDARD_FLOOR = 40      # at/above → standard confidence

SARCASM_HIGH = 0.50
SARCASM_MODERATE = 0.25


EMOTION_FIELDS = (
    "joy_share", "anger_share", "fear_share",
    "trust_share", "sadness_share", "surprise_share",
)
EMOTION_TO_FIELD = {
    "joy": "joy_share",
    "anger": "anger_share",
    "fear": "fear_share",
    "trust": "trust_share",
    "sadness": "sadness_share",
    "surprise": "surprise_share",
}


@dataclass
class _PlayerBucketAccumulator:
    mention_count: int = 0
    authors: set[str] = field(default_factory=set)
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    sentiment_sum: float = 0.0
    sentiment_n: int = 0
    emotion_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    attention_raw: float = 0.0
    confidence_sum: float = 0.0
    confidence_n: int = 0
    sarcasm_sum: float = 0.0
    sarcasm_n: int = 0
    best_quote: tuple[float, dict[str, Any]] | None = None  # (score, payload)


    def add_row(self, row: dict[str, Any]) -> None:
        self.mention_count += 1

        author = row.get("source_author_id") or row.get("source_author_name") or ""
        if author:
            self.authors.add(str(author))

        sentiment = row.get("sentiment_score")
        if sentiment is not None:
            try:
                s = float(sentiment)
            except (TypeError, ValueError):
                s = None
            else:
                self.sentiment_sum += s
                self.sentiment_n += 1
                if s > POS_CUTOFF:
                    self.positive += 1
                elif s < NEG_CUTOFF:
                    self.negative += 1
                else:
                    self.neutral += 1

        emotion = (row.get("emotion_primary") or "").strip().lower()
        if emotion in EMOTION_TO_FIELD:
            self.emotion_counts[emotion] += 1

        # Attention: log-scaled sum of social metrics. Guards against
        # runaway values from a single viral doc.
        likes = int(row.get("like_count") or 0)
        replies = int(row.get("reply_count") or 0)
        views = int(row.get("view_count") or 0)
        self.attention_raw += math.log1p(max(0, likes + replies + views))

        confidence = row.get("confidence_score")
        if confidence is not None:
            try:
                c = float(confidence)
            except (TypeError, ValueError):
                c = None
            else:
                self.confidence_sum += c
                self.confidence_n += 1

        sarcasm = row.get("sarcasm_score")
        if sarcasm is not None:
            try:
                sk = float(sarcasm)
            except (TypeError, ValueError):
                sk = None
            else:
                self.sarcasm_sum += sk
                self.sarcasm_n += 1

        # Top-quote selection: weight = (sentiment magnitude toward positive
        # for fan/national/media; toward negative for rival) * (confidence
        # score). We pick the representative per bucket OUT here; the caller
        # hands us only the rows for ONE bucket, so direction is uniform.
        body_text = row.get("body_text") or row.get("title_text") or ""
        if body_text:
            conf = float(row.get("confidence_score") or 0.5)
            sscore = float(row.get("sentiment_score") or 0.0)
            quote_score = abs(sscore) * max(conf, 0.1)
            payload = {
                "text": str(body_text)[:400],
                "author_pseudonym": str(
                    row.get("source_author_name") or row.get("source_author_id") or "fan"
                )[:64],
                "source_url": row.get("source_url") or row.get("capture_url"),
                "sentiment_score": sscore,
            }
            if self.best_quote is None or quote_score > self.best_quote[0]:
                self.best_quote = (quote_score, payload)


    def mean_sentiment(self) -> float | None:
        if self.sentiment_n == 0:
            return None
        return self.sentiment_sum / self.sentiment_n

    def net_sentiment(self) -> float | None:
        total = self.positive + self.neutral + self.negative
        if total == 0:
            return None
        return (self.positive - self.negative) / total

    def emotion_shares(self) -> dict[str, float]:
        total = sum(self.emotion_counts.values())
        if total == 0:
            return {f: 0.0 for f in EMOTION_FIELDS}
        shares = {f: 0.0 for f in EMOTION_FIELDS}
        for emo, n in self.emotion_counts.items():
            field_name = EMOTION_TO_FIELD.get(emo)
            if field_name:
                shares[field_name] = n / total
        return shares

    def attention_score(self) -> float:
        # Normalize by mention_count so virality doesn't fake volume.
        if self.mention_count == 0:
            return 0.0
        return self.attention_raw / self.mention_count

    def sample_quality_score(self) -> float | None:
        if self.confidence_n == 0:
            return None
        return self.confidence_sum / self.confidence_n

    def sarcasm_risk_label(self) -> str:
        if self.sarcasm_n == 0:
            return "low"
        avg = self.sarcasm_sum / self.sarcasm_n
        if avg >= SARCASM_HIGH:
            return "high"
        if avg >= SARCASM_MODERATE:
            return "moderate"
        return "low"

    def confidence_floor_label(self) -> str:
        if self.mention_count < SAMPLE_SIGNAL_FLOOR:
            return "thin"
        if self.mention_count < SAMPLE_STANDARD_FLOOR:
            return "sample"
        return "ok"

    def top_quote_json(self) -> str | None:
        if self.best_quote is None:
            return None
        return json.dumps(self.best_quote[1], default=str)


SEASON_ROLLUP_WEEK = 0
"""Sentinel value for week on season-rollup rows.

Weekly aggregate rows use week = 1..17+ (matching the target row's week).
Rows written by ``compute_player_season_mood`` use week = 0 so they share
the same unique index ``ux_pwcf_keys`` without colliding, and readers can
opt into the rollup by passing ``week=0`` to the reader helpers.
"""


def parse_week_key(week_key: str) -> tuple[int, int]:
    if "-" not in week_key:
        raise ValueError(f"expected YYYY-WW, got {week_key!r}")
    y, w = week_key.split("-", 1)
    return int(y), int(w)


def compute_player_week_mood(
    db: Database,
    week_key: str,
    *,
    players: Iterable[int] | None = None,
    model_version: str = "player-mood-v0.1.0",
) -> dict[str, int]:
    """Compute player_week_conversation_features rows for one YYYY-WW week.

    Returns: {'rows_read': N, 'players_touched': P, 'cells_written': C}.
    """
    season_year, week_int = parse_week_key(week_key)

    params: dict[str, Any] = {"season_year": season_year, "week": week_int}
    player_filter = ""
    if players:
        pid_list = list(players)
        placeholders = ",".join(f":pid_{i}" for i in range(len(pid_list)))
        for i, pid in enumerate(pid_list):
            params[f"pid_{i}"] = int(pid)
        player_filter = f" and t.player_id in ({placeholders}) "

    rows = db.query_all(
        f"""
        select
          t.player_id             as player_id,
          t.audience_bucket       as audience_bucket,
          t.affiliation_team_id   as team_id,
          t.sentiment_score       as sentiment_score,
          t.emotion_primary       as emotion_primary,
          t.sarcasm_score         as sarcasm_score,
          t.confidence_score      as confidence_score,
          cd.conversation_document_id as conversation_document_id,
          cd.source_name          as source_name,
          cd.source_author_id     as source_author_id,
          cd.source_author_name   as source_author_name,
          cd.source_url           as source_url,
          cd.capture_url          as capture_url,
          cd.body_text            as body_text,
          cd.title_text           as title_text,
          cd.like_count           as like_count,
          cd.reply_count          as reply_count,
          cd.view_count           as view_count
        from conversation_document_targets t
        join conversation_documents cd
          on cd.conversation_document_id = t.conversation_document_id
        where t.season_year = :season_year
          and t.week        = :week
          and t.target_type = 'player'
          and t.player_id is not null
          {player_filter}
        """,
        params,
    )

    # Group by (player_id, source_name, audience_bucket). Empty bucket values
    # are normalized to 'fan' so old rows don't fall on the floor.
    cells: dict[tuple[int, str, str, int | None], _PlayerBucketAccumulator] = defaultdict(_PlayerBucketAccumulator)
    for r in rows:
        pid = int(r["player_id"])
        bucket = (r.get("audience_bucket") or "fan").strip().lower()
        if bucket not in AUDIENCE_BUCKETS:
            bucket = "fan"
        source = r.get("source_name") or ""
        team_id = r.get("team_id")
        key = (pid, source, bucket, int(team_id) if team_id is not None else None)
        cells[key].add_row(r)

    cells_written = 0
    players_touched: set[int] = set()
    for (pid, source, bucket, team_id), acc in cells.items():
        players_touched.add(pid)
        shares = acc.emotion_shares()
        db.execute(
            """
            insert into player_week_conversation_features (
                season_year, week, player_id, team_id, source_name, audience_bucket,
                mention_count, unique_author_count,
                positive_doc_count, neutral_doc_count, negative_doc_count,
                mean_sentiment_score, net_sentiment_score,
                joy_share, anger_share, fear_share,
                trust_share, sadness_share, surprise_share,
                attention_score, sample_quality_score,
                sarcasm_risk, top_storyline_json, top_quote_json,
                sample_n, sample_window, confidence_floor, model_version
            ) values (
                :season_year, :week, :player_id, :team_id, :source_name, :audience_bucket,
                :mention_count, :unique_author_count,
                :positive, :neutral, :negative,
                :mean_sent, :net_sent,
                :joy, :anger, :fear,
                :trust, :sadness, :surprise,
                :attention, :sample_quality,
                :sarcasm_risk, null, :top_quote,
                :sample_n, :sample_window, :confidence_floor, :model_version
            )
            on conflict (player_id, season_year, week, coalesce(source_name, ''), audience_bucket)
            do update set
                team_id = excluded.team_id,
                mention_count = excluded.mention_count,
                unique_author_count = excluded.unique_author_count,
                positive_doc_count = excluded.positive_doc_count,
                neutral_doc_count = excluded.neutral_doc_count,
                negative_doc_count = excluded.negative_doc_count,
                mean_sentiment_score = excluded.mean_sentiment_score,
                net_sentiment_score = excluded.net_sentiment_score,
                joy_share = excluded.joy_share,
                anger_share = excluded.anger_share,
                fear_share = excluded.fear_share,
                trust_share = excluded.trust_share,
                sadness_share = excluded.sadness_share,
                surprise_share = excluded.surprise_share,
                attention_score = excluded.attention_score,
                sample_quality_score = excluded.sample_quality_score,
                sarcasm_risk = excluded.sarcasm_risk,
                top_quote_json = excluded.top_quote_json,
                sample_n = excluded.sample_n,
                sample_window = excluded.sample_window,
                confidence_floor = excluded.confidence_floor,
                model_version = excluded.model_version
            """,
            {
                "season_year": season_year,
                "week": week_int,
                "player_id": pid,
                "team_id": team_id,
                "source_name": source,
                "audience_bucket": bucket,
                "mention_count": acc.mention_count,
                "unique_author_count": len(acc.authors),
                "positive": acc.positive,
                "neutral": acc.neutral,
                "negative": acc.negative,
                "mean_sent": acc.mean_sentiment(),
                "net_sent": acc.net_sentiment(),
                "joy": shares.get("joy_share"),
                "anger": shares.get("anger_share"),
                "fear": shares.get("fear_share"),
                "trust": shares.get("trust_share"),
                "sadness": shares.get("sadness_share"),
                "surprise": shares.get("surprise_share"),
                "attention": acc.attention_score(),
                "sample_quality": acc.sample_quality_score(),
                "sarcasm_risk": acc.sarcasm_risk_label(),
                "top_quote": acc.top_quote_json(),
                "sample_n": acc.mention_count,
                "sample_window": f"{week_key}",
                "confidence_floor": acc.confidence_floor_label(),
                "model_version": model_version,
            },
        )
        cells_written += 1

    return {
        "rows_read": len(rows),
        "players_touched": len(players_touched),
        "cells_written": cells_written,
    }


def compute_player_season_mood(
    db: Database,
    season_year: int,
    *,
    players: Iterable[int] | None = None,
    model_version: str = "player-mood-season-v0.1.0",
) -> dict[str, int]:
    """Compute a season-rollup row per (player, source, bucket) — week=0.

    Reads every player-scope `conversation_document_targets` row for the
    season (all weeks collapsed) and produces one aggregate row per bucket
    written at week=SEASON_ROLLUP_WEEK (0). Same math as
    ``compute_player_week_mood``; only the grouping key differs.

    Lets offseason pages surface real Room cards for players whose
    mentions cross the floor *across* the season even when no single week
    clears it on its own. The floor itself is unchanged (same
    MIN_MENTIONS_FOR_SIGNAL at the reader); only the granularity shifts.

    Returns counts: {'rows_read': N, 'players_touched': P, 'cells_written': C}.
    """
    params: dict[str, Any] = {"season_year": season_year}
    player_filter = ""
    if players:
        pid_list = list(players)
        placeholders = ",".join(f":pid_{i}" for i in range(len(pid_list)))
        for i, pid in enumerate(pid_list):
            params[f"pid_{i}"] = int(pid)
        player_filter = f" and t.player_id in ({placeholders}) "

    rows = db.query_all(
        f"""
        select
          t.player_id             as player_id,
          t.audience_bucket       as audience_bucket,
          t.affiliation_team_id   as team_id,
          t.sentiment_score       as sentiment_score,
          t.emotion_primary       as emotion_primary,
          t.sarcasm_score         as sarcasm_score,
          t.confidence_score      as confidence_score,
          cd.conversation_document_id as conversation_document_id,
          cd.source_name          as source_name,
          cd.source_author_id     as source_author_id,
          cd.source_author_name   as source_author_name,
          cd.source_url           as source_url,
          cd.capture_url          as capture_url,
          cd.body_text            as body_text,
          cd.title_text           as title_text,
          cd.like_count           as like_count,
          cd.reply_count          as reply_count,
          cd.view_count           as view_count
        from conversation_document_targets t
        join conversation_documents cd
          on cd.conversation_document_id = t.conversation_document_id
        where t.season_year = :season_year
          and t.target_type = 'player'
          and t.player_id is not null
          {player_filter}
        """,
        params,
    )

    # Rollup collapses across source_name (each player-bucket gets ONE row
    # with source_name='all'). If we kept separate rows per subreddit/board,
    # a player mentioned once in 15 different sources would stay below the
    # floor forever even though the total signal is 15 mentions.
    cells: dict[tuple[int, str, int | None], _PlayerBucketAccumulator] = defaultdict(
        _PlayerBucketAccumulator
    )
    for r in rows:
        pid = int(r["player_id"])
        bucket = (r.get("audience_bucket") or "fan").strip().lower()
        if bucket not in AUDIENCE_BUCKETS:
            bucket = "fan"
        team_id = r.get("team_id")
        key = (pid, bucket, int(team_id) if team_id is not None else None)
        cells[key].add_row(r)

    cells_written = 0
    players_touched: set[int] = set()
    for (pid, bucket, team_id), acc in cells.items():
        players_touched.add(pid)
        shares = acc.emotion_shares()
        db.execute(
            """
            insert into player_week_conversation_features (
                season_year, week, player_id, team_id, source_name, audience_bucket,
                mention_count, unique_author_count,
                positive_doc_count, neutral_doc_count, negative_doc_count,
                mean_sentiment_score, net_sentiment_score,
                joy_share, anger_share, fear_share,
                trust_share, sadness_share, surprise_share,
                attention_score, sample_quality_score,
                sarcasm_risk, top_storyline_json, top_quote_json,
                sample_n, sample_window, confidence_floor, model_version
            ) values (
                :season_year, :week, :player_id, :team_id, :source_name, :audience_bucket,
                :mention_count, :unique_author_count,
                :positive, :neutral, :negative,
                :mean_sent, :net_sent,
                :joy, :anger, :fear,
                :trust, :sadness, :surprise,
                :attention, :sample_quality,
                :sarcasm_risk, null, :top_quote,
                :sample_n, :sample_window, :confidence_floor, :model_version
            )
            on conflict (player_id, season_year, week, coalesce(source_name, ''), audience_bucket)
            do update set
                team_id = excluded.team_id,
                mention_count = excluded.mention_count,
                unique_author_count = excluded.unique_author_count,
                positive_doc_count = excluded.positive_doc_count,
                neutral_doc_count = excluded.neutral_doc_count,
                negative_doc_count = excluded.negative_doc_count,
                mean_sentiment_score = excluded.mean_sentiment_score,
                net_sentiment_score = excluded.net_sentiment_score,
                joy_share = excluded.joy_share,
                anger_share = excluded.anger_share,
                fear_share = excluded.fear_share,
                trust_share = excluded.trust_share,
                sadness_share = excluded.sadness_share,
                surprise_share = excluded.surprise_share,
                attention_score = excluded.attention_score,
                sample_quality_score = excluded.sample_quality_score,
                sarcasm_risk = excluded.sarcasm_risk,
                top_quote_json = excluded.top_quote_json,
                sample_n = excluded.sample_n,
                sample_window = excluded.sample_window,
                confidence_floor = excluded.confidence_floor,
                model_version = excluded.model_version
            """,
            {
                "season_year": season_year,
                "week": SEASON_ROLLUP_WEEK,
                "player_id": pid,
                "team_id": team_id,
                "source_name": "all",
                "audience_bucket": bucket,
                "mention_count": acc.mention_count,
                "unique_author_count": len(acc.authors),
                "positive": acc.positive,
                "neutral": acc.neutral,
                "negative": acc.negative,
                "mean_sent": acc.mean_sentiment(),
                "net_sent": acc.net_sentiment(),
                "joy": shares.get("joy_share"),
                "anger": shares.get("anger_share"),
                "fear": shares.get("fear_share"),
                "trust": shares.get("trust_share"),
                "sadness": shares.get("sadness_share"),
                "surprise": shares.get("surprise_share"),
                "attention": acc.attention_score(),
                "sample_quality": acc.sample_quality_score(),
                "sarcasm_risk": acc.sarcasm_risk_label(),
                "top_quote": acc.top_quote_json(),
                "sample_n": acc.mention_count,
                "sample_window": f"season-{season_year}",
                "confidence_floor": acc.confidence_floor_label(),
                "model_version": model_version,
            },
        )
        cells_written += 1

    return {
        "rows_read": len(rows),
        "players_touched": len(players_touched),
        "cells_written": cells_written,
    }


__all__ = [
    "compute_player_week_mood",
    "compute_player_season_mood",
    "parse_week_key",
    "AUDIENCE_BUCKETS",
    "SAMPLE_SIGNAL_FLOOR",
    "SAMPLE_STANDARD_FLOOR",
    "SEASON_ROLLUP_WEEK",
]
