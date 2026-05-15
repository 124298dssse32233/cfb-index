"""S5 — anniversary card data layer.

Pulls candidate anniversary content from three priority tiers:

  1. archive_threads — same iso_mm_dd as today, score-sorted.
  2. team_chronicle_observations — same MM-DD on the ``generated_at_utc``
     stamp (best-effort approximation of "this day in history" for
     editorial chronicle cards; the cards themselves are tied to a
     team-season-week, not a calendar date, so we use generated_at).
     For an actual season-day match we'd need a calendar-date column;
     this is a graceful approximation until that column lands.
  3. historical_seasons_summary — same calendar week N years ago,
     when the table exists. Optional fallthrough.

Each source returns ``AnniversaryCard`` dicts with a uniform shape.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Card dataclass
# ---------------------------------------------------------------------------

@dataclass
class AnniversaryCard:
    """One anniversary card shown on /anniversary/today/."""

    year: int                       # the historical year being remembered
    years_ago: int                  # today.year - year
    source: str                     # 'archive_threads' | 'team_chronicle' | 'historical_season'
    headline: str                   # short title
    body: str = ""                  # 1-3 sentence body
    url: str | None = None          # link to source artifact
    attribution: str = ""           # "r/CFB · 1,243 upvotes" / "CFB Index chronicle"
    score: int = 0                  # engagement / surprise — used for sort tiebreaks
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "years_ago": self.years_ago,
            "source": self.source,
            "headline": self.headline,
            "body": self.body,
            "url": self.url,
            "attribution": self.attribution,
            "score": self.score,
            "extra": dict(self.extra),
        }


# ---------------------------------------------------------------------------
# Public entry — orchestrator
# ---------------------------------------------------------------------------

def gather_today_in_history_cards(
    db: Any,
    *,
    today: date,
    max_cards: int = 5,
) -> list[AnniversaryCard]:
    """Return up to ``max_cards`` anniversary cards for ``today``.

    Pulls from three sources in priority order. Higher-priority entries
    are kept until cap; ties broken by year-descending (recent first).
    Empty-list return is the explicit signal for "quiet day" — caller
    renders the empty state.
    """
    cards: list[AnniversaryCard] = []

    # Tier 1: archive_threads (date-anchored, high-confidence)
    cards.extend(_fetch_archive_threads(db, today=today, limit=max_cards * 2))

    # Tier 2: team_chronicle_observations (editorial color)
    if len(cards) < max_cards:
        cards.extend(_fetch_team_chronicles(db, today=today, limit=max_cards))

    # Tier 3: historical_seasons_summary (week-anchored — only if Tier 1+2 still light)
    if len(cards) < max_cards:
        cards.extend(_fetch_historical_seasons(db, today=today, limit=max_cards))

    # Sort: year descending (recent first), then score descending for tiebreaks.
    cards.sort(key=lambda c: (-c.year, -c.score))

    # Dedupe by (source, headline) — keep first occurrence
    seen: set[tuple[str, str]] = set()
    deduped: list[AnniversaryCard] = []
    for card in cards:
        key = (card.source, card.headline.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(card)
        if len(deduped) >= max_cards:
            break

    return deduped


# ---------------------------------------------------------------------------
# Tier 1 — archive_threads
# ---------------------------------------------------------------------------

def _fetch_archive_threads(db: Any, *, today: date, limit: int) -> list[AnniversaryCard]:
    """Same iso_mm_dd across prior years, score-sorted."""
    if not _table_exists(db, "archive_threads"):
        return []

    mm_dd = today.strftime("%m-%d")
    try:
        rows = db.query_all(
            """
            select subreddit, external_id, title, body_md, permalink, author,
                   created_utc, score, num_comments, iso_date, iso_mm_dd
              from archive_threads
             where iso_mm_dd = :mm_dd
             order by score desc, created_utc desc
             limit :lim
            """,
            {"mm_dd": mm_dd, "lim": int(limit)},
        ) or []
    except Exception as exc:  # noqa: BLE001 — graceful
        logger.warning("today_in_history: archive_threads query failed: %s", exc)
        return []

    cards: list[AnniversaryCard] = []
    for row in rows:
        thread_year = _year_from_iso(row.get("iso_date") or row.get("created_utc"))
        if thread_year is None or thread_year >= today.year:
            continue
        years_ago = today.year - thread_year
        subreddit = (row.get("subreddit") or "CFB").strip() or "CFB"
        score = int(row.get("score") or 0)
        permalink = (row.get("permalink") or "").strip() or None
        attribution = f"r/{subreddit} · {score:,} upvotes"
        body = (row.get("body_md") or "")[:280].strip()
        cards.append(AnniversaryCard(
            year=thread_year,
            years_ago=years_ago,
            source="archive_threads",
            headline=(row.get("title") or "").strip(),
            body=body,
            url=permalink,
            attribution=attribution,
            score=score,
            extra={"subreddit": subreddit, "external_id": row.get("external_id")},
        ))
    return cards


# ---------------------------------------------------------------------------
# Tier 2 — team_chronicle_observations
# ---------------------------------------------------------------------------

def _fetch_team_chronicles(db: Any, *, today: date, limit: int) -> list[AnniversaryCard]:
    """Same MM-DD across profiled teams. Approximates 'this day in chronicle
    history' by matching ``generated_at_utc`` MM-DD, since the chronicle
    table has no first-class event-date column.
    """
    if not _table_exists(db, "team_chronicle_observations"):
        return []

    mm_dd = today.strftime("%m-%d")
    # Be tolerant of teams join — left join so a missing teams row doesn't
    # wipe the result set.
    try:
        rows = db.query_all(
            """
            select
                tco.headline,
                tco.body_md,
                tco.card_type,
                tco.season_year,
                tco.surprise_score,
                tco.generated_at_utc,
                tco.source_attribution,
                tco.team_id,
                tco.is_published
              from team_chronicle_observations tco
             where strftime('%m-%d', tco.generated_at_utc) = :mm_dd
               and coalesce(tco.is_published, 0) = 1
             order by tco.season_year desc, tco.surprise_score desc
             limit :lim
            """,
            {"mm_dd": mm_dd, "lim": int(limit)},
        ) or []
    except Exception as exc:  # noqa: BLE001 — graceful
        logger.warning("today_in_history: team_chronicle query failed: %s", exc)
        return []

    cards: list[AnniversaryCard] = []
    for row in rows:
        season_year = row.get("season_year")
        if not isinstance(season_year, int) or season_year >= today.year:
            continue
        years_ago = today.year - season_year
        attribution = (row.get("source_attribution") or "CFB Index chronicle").strip()
        cards.append(AnniversaryCard(
            year=season_year,
            years_ago=years_ago,
            source="team_chronicle",
            headline=(row.get("headline") or "").strip(),
            body=(row.get("body_md") or "")[:280].strip(),
            url=None,
            attribution=attribution,
            score=int(round((row.get("surprise_score") or 0) * 100)),
            extra={
                "card_type": row.get("card_type"),
                "team_id": row.get("team_id"),
            },
        ))
    return cards


# ---------------------------------------------------------------------------
# Tier 3 — historical_seasons_summary
# ---------------------------------------------------------------------------

def _fetch_historical_seasons(db: Any, *, today: date, limit: int) -> list[AnniversaryCard]:
    """Week-anchored fallthrough. Optional table — soft-fail if absent."""
    if not _table_exists(db, "historical_seasons_summary"):
        return []

    iso = today.isocalendar()
    iso_week = iso[1]
    try:
        rows = db.query_all(
            """
            select season_year, week, headline, summary_md
              from historical_seasons_summary
             where week = :wk
               and season_year < :yr
             order by season_year desc
             limit :lim
            """,
            {"wk": int(iso_week), "yr": today.year, "lim": int(limit)},
        ) or []
    except Exception as exc:  # noqa: BLE001 — graceful (table may have different cols)
        logger.warning("today_in_history: historical_seasons query failed: %s", exc)
        return []

    cards: list[AnniversaryCard] = []
    for row in rows:
        season_year = row.get("season_year")
        if not isinstance(season_year, int):
            continue
        years_ago = today.year - season_year
        cards.append(AnniversaryCard(
            year=season_year,
            years_ago=years_ago,
            source="historical_season",
            headline=(row.get("headline") or f"Week {row.get('week')} of the {season_year} season").strip(),
            body=(row.get("summary_md") or "")[:280].strip(),
            url=None,
            attribution=f"CFB Index · {season_year} season recap",
            score=0,
            extra={"season_year": season_year, "week": row.get("week")},
        ))
    return cards


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _table_exists(db: Any, table: str) -> bool:
    try:
        row = db.query_one(
            "select 1 as ok from sqlite_master where type='table' and name = :n",
            {"n": table},
        )
        return bool(row)
    except Exception as exc:  # noqa: BLE001 — graceful
        logger.debug("today_in_history: table_exists(%s) failed: %s", table, exc)
        return False


def _year_from_iso(value: Any) -> int | None:
    if isinstance(value, int):
        # Assume Unix seconds.
        try:
            return datetime.utcfromtimestamp(value).year
        except (ValueError, OverflowError, OSError):
            return None
    if not isinstance(value, str) or not value:
        return None
    # Accept YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ
    head = value[:4]
    if head.isdigit():
        try:
            return int(head)
        except ValueError:
            return None
    return None


__all__ = [
    "AnniversaryCard",
    "gather_today_in_history_cards",
]
