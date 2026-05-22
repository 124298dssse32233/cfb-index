"""Per-surface proprietary-data manifest builders.

One builder per Tier-1 surface in v5.3 Part 4. Each builder accepts a
``sqlite3.Connection`` (or anything that exposes ``.execute()`` returning
a cursor with ``.fetchall()`` rows-as-tuples *or* rows-as-dicts) plus the
surface-specific identifiers, and returns a single ``dict`` whose keys
map to the manifest rows in the design audit.

**Defensive contract** — every helper catches :class:`sqlite3.Error` and
logs it, then returns ``[]`` or ``None`` for the affected key. This is
the *graceful degradation* path the audit calls out: when a manifest
table has not yet shipped (Sprint v5-1 runs ahead of the schema
back-fills for some surfaces) the builder still returns a dict with the
expected shape, just with empty slots. The Tier-1 prompts treat empty
slots as "we don't have this signal yet, skip the corresponding
paragraph" rather than crashing.

Schema reality vs v5.3 spec
---------------------------
v5.3 names a few tables that don't yet exist in this repo's schema. The
builder either substitutes the closest extant equivalent or returns an
empty list. Specifically:

* ``receipts`` — actual table is :data:`predictive_claims` (with
  ``surprise_index`` and ``outcome_verdict`` columns). Used for
  resolved-receipts pulls.
* ``fanbase_cohort_weekly`` — closest extant is
  :data:`team_cohort_week` keyed on ``(team_id, cohort, week)``. The
  "transition" delta is computed in-builder by joining the current week
  to the trailing week's row for the same cohort.
* ``archive_threads`` — not yet shipped. Builder returns ``[]`` for
  every key that consumes it (and the prompt template handles the
  empty list gracefully).
* ``nfl_pipeline`` — actual table is :data:`player_nfl_draft`.
* ``recruiting_rankings`` — not yet shipped. Builder returns ``[]``.
* ``player_season_context`` — closest extant is
  :data:`player_season_summary` (composite ``cfb_index_score`` +
  milestones). Builder maps the manifest's
  ``usage_rate`` / ``value_score`` to that table's columns where it can.
* ``game_player_stats`` — actual table is :data:`player_game_stats`.
* ``season_phase`` — derivable from :data:`offseason_week_map` plus the
  current date. Builder uses ``offseason_week_map`` as the source.
* ``team_brand_assets`` exists; ``team_brand`` exists. Both used as-is.

If a future migration ships any of these tables under the v5.3 name, the
matching helper becomes a one-line swap.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Mapping, Sequence

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return tz-naive current UTC time.

    The SQLite columns we filter against (``occurred_at``,
    ``external_created_at_utc``, etc.) are stored as ISO strings without
    a timezone suffix. Filtering with a tz-naive ``isoformat`` matches
    them lexicographically — adding a ``+00:00`` suffix would break the
    string comparison. We compute via ``datetime.now(tz=UTC)`` (the
    non-deprecated path) and strip the tzinfo for the comparison.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

# ---------------------------------------------------------------------------
# Internal SQL helpers
# ---------------------------------------------------------------------------


def _rows(
    db: sqlite3.Connection,
    sql: str,
    params: Sequence[Any] | Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Execute *sql* and return rows as a list of ``dict[column → value]``.

    Catches :class:`sqlite3.Error` (missing-table, syntax, locked, etc.)
    and returns ``[]`` after logging at WARNING. The caller decides what
    "empty result" means for the surface — usually "skip this section of
    the prompt".
    """
    try:
        cur = db.execute(sql, params or [])
    except sqlite3.Error as exc:
        logger.warning("prompt_context: SQL failed (returning []): %s", exc)
        return []
    try:
        col_names = [d[0] for d in (cur.description or [])]
        out: list[dict[str, Any]] = []
        for row in cur.fetchall():
            if isinstance(row, sqlite3.Row) or hasattr(row, "keys"):
                out.append({k: row[k] for k in row.keys()})  # type: ignore[index]
            else:
                out.append(dict(zip(col_names, row)))
        return out
    except sqlite3.Error as exc:
        logger.warning("prompt_context: fetch failed (returning []): %s", exc)
        return []


def _row(
    db: sqlite3.Connection,
    sql: str,
    params: Sequence[Any] | Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Single-row variant of :func:`_rows`. Returns ``None`` on no row."""
    rows = _rows(db, sql, params)
    return rows[0] if rows else None


def _scalar(
    db: sqlite3.Connection,
    sql: str,
    params: Sequence[Any] | Mapping[str, Any] | None = None,
) -> Any:
    """Return the first column of the first row, or ``None``."""
    rows = _rows(db, sql, params)
    if not rows:
        return None
    first = rows[0]
    if isinstance(first, dict) and first:
        return next(iter(first.values()))
    return None


# ---------------------------------------------------------------------------
# Shared sub-queries used by multiple builders
# ---------------------------------------------------------------------------


def _q_prior_covers(
    db: sqlite3.Connection, season: int, week: int, limit: int = 4
) -> list[dict[str, Any]]:
    """Last *limit* edition cover essays prior to (season, week).

    Pulls from ``editions`` + ``edition_features`` where
    ``feature_kind = 'cover_essay'``. Includes title, dek, theme,
    body excerpt (first 400 chars), publish_date.
    """
    return _rows(
        db,
        """
        SELECT e.edition_slug, e.publish_date, e.theme_title, e.theme_dek,
               ef.title AS feature_title,
               substr(ef.body_markdown, 1, 400) AS body_excerpt
        FROM editions e
        LEFT JOIN edition_features ef
          ON ef.edition_slug = e.edition_slug
         AND ef.feature_kind = 'cover_essay'
        WHERE e.status = 'published'
        ORDER BY e.publish_date DESC
        LIMIT :lim
        """,
        {"lim": limit},
    )


def _q_cohort_mood_dumbbell(
    db: sqlite3.Connection, week_iso: str
) -> list[dict[str, Any]]:
    """Per-team current-vs-trailing-4-week cohort mood delta.

    Uses :data:`team_cohort_week` (the table that does exist) as the
    stand-in for the v5.3-spec ``fanbase_cohort_weekly``. Returns rows
    of ``{team_id, cohort, current_score, prior4_avg, delta}``.
    """
    return _rows(
        db,
        """
        SELECT cur.team_id, cur.cohort,
               cur.sentiment_score AS current_score,
               prior.avg_score AS prior4_avg,
               (cur.sentiment_score - prior.avg_score) AS delta
        FROM team_cohort_week cur
        LEFT JOIN (
            SELECT team_id, cohort, AVG(sentiment_score) AS avg_score
            FROM team_cohort_week
            WHERE week < :wk
            GROUP BY team_id, cohort
        ) prior ON prior.team_id = cur.team_id AND prior.cohort = cur.cohort
        WHERE cur.week = :wk
          AND cur.confidence_tier IN ('high','medium')
        ORDER BY ABS(cur.sentiment_score - COALESCE(prior.avg_score, 0)) DESC
        LIMIT 50
        """,
        {"wk": week_iso},
    )


def _q_rank_disagreements(
    db: sqlite3.Connection, season: int, week: int, limit: int = 10
) -> list[dict[str, Any]]:
    """Top-N teams where BT-derived rank diverges across model runs.

    Reads :data:`power_ratings_weekly` ordered by ``power_rating`` per
    ``model_run_id``, computes the rank-position spread.
    """
    return _rows(
        db,
        """
        WITH ranked AS (
            SELECT team_id, model_run_id, power_rating,
                   row_number() OVER (
                       PARTITION BY model_run_id
                       ORDER BY power_rating DESC
                   ) AS rk
            FROM power_ratings_weekly
            WHERE season_year = :season AND week = :week
        )
        SELECT team_id,
               MIN(rk) AS best_rank,
               MAX(rk) AS worst_rank,
               (MAX(rk) - MIN(rk)) AS spread
        FROM ranked
        GROUP BY team_id
        HAVING spread > 0
        ORDER BY spread DESC
        LIMIT :lim
        """,
        {"season": season, "week": week, "lim": limit},
    )


def _q_active_storylines(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """All ``status='active'`` storyline_threads with last_chapter_at."""
    return _rows(
        db,
        """
        SELECT thread_slug, title, dek, accent_hex, last_chapter_at,
               chapter_count, primary_program_slugs, primary_conference_slug
        FROM storyline_threads
        WHERE status = 'active'
        ORDER BY last_chapter_at DESC NULLS LAST
        """,
    )


def _q_recent_wire(
    db: sqlite3.Connection,
    days: int = 7,
    impact: str | None = None,
    program_slug: str | None = None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Last *days* of wire entries, optionally filtered."""
    cutoff = (_utcnow() - timedelta(days=days)).isoformat(timespec="seconds")
    clauses = ["occurred_at >= :cutoff"]
    params: dict[str, Any] = {"cutoff": cutoff, "lim": limit}
    if impact:
        clauses.append("impact_label = :impact")
        params["impact"] = impact
    if program_slug:
        clauses.append("program_slug = :slug")
        params["slug"] = program_slug
    sql = (
        "SELECT id, occurred_at, program_slug, program_display, actor_kind, "
        "action, why_it_matters, impact_label, impact_color, "
        "historical_comp, source_name, related_thread_slug, "
        "fan_intel_velocity_spike "
        "FROM wire_entries WHERE "
        + " AND ".join(clauses)
        + " ORDER BY occurred_at DESC LIMIT :lim"
    )
    return _rows(db, sql, params)


def _q_resolved_receipts(
    db: sqlite3.Connection, days: int = 30, min_surprise: float = 60.0,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Recently-resolved predictive claims with high surprise_index.

    v5.3 calls this table ``receipts``; in this repo the canonical name
    is :data:`predictive_claims`.
    """
    cutoff = (_utcnow() - timedelta(days=days)).isoformat(timespec="seconds")
    return _rows(
        db,
        """
        SELECT id, source_kind, source_slug, claim_summary_short,
               surprise_index, outcome_verdict, outcome_text,
               outcome_resolved_at, aged_well_pct
        FROM predictive_claims
        WHERE outcome_resolved = 1
          AND outcome_resolved_at >= :cutoff
          AND COALESCE(surprise_index, 0) >= :min_s
        ORDER BY surprise_index DESC
        LIMIT :lim
        """,
        {"cutoff": cutoff, "min_s": min_surprise, "lim": limit},
    )


def _q_top_chronicle(
    db: sqlite3.Connection,
    days: int = 14,
    program_slug: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Top chronicle observations by resonance × surprise.

    Joins to :data:`teams` only if a program_slug filter is requested.
    Returns headline + body + source attribution.
    """
    cutoff = (_utcnow() - timedelta(days=days)).isoformat(timespec="seconds")
    if program_slug:
        return _rows(
            db,
            """
            SELECT c.team_chronicle_observation_id, c.team_id, c.season_year,
                   c.week, c.card_type, c.headline, c.body_md,
                   c.source_attribution, c.surprise_score, c.generated_at_utc
            FROM team_chronicle_observations c
            JOIN teams t ON t.team_id = c.team_id
            WHERE c.is_published = 1
              AND c.generated_at_utc >= :cutoff
              AND t.school_slug = :slug
            ORDER BY COALESCE(c.surprise_score, 0) DESC,
                     c.generated_at_utc DESC
            LIMIT :lim
            """,
            {"cutoff": cutoff, "slug": program_slug, "lim": limit},
        )
    return _rows(
        db,
        """
        SELECT team_chronicle_observation_id, team_id, season_year, week,
               card_type, headline, body_md, source_attribution,
               surprise_score, generated_at_utc
        FROM team_chronicle_observations
        WHERE is_published = 1 AND generated_at_utc >= :cutoff
        ORDER BY COALESCE(surprise_score, 0) DESC, generated_at_utc DESC
        LIMIT :lim
        """,
        {"cutoff": cutoff, "lim": limit},
    )


def _q_season_phase(
    db: sqlite3.Connection, season: int, week: int
) -> dict[str, Any] | None:
    """Best-effort season-phase label.

    v5.3 references a ``season_phase`` table; this repo uses
    :data:`offseason_week_map`. We return the row for the given
    (season, week) if it exists, else ``None``.
    """
    return _row(
        db,
        """
        SELECT * FROM offseason_week_map
        WHERE season_year = :s AND week = :w
        LIMIT 1
        """,
        {"s": season, "w": week},
    )


def _q_team_id_for_slug(
    db: sqlite3.Connection, program_slug: str
) -> int | None:
    """Resolve a program_slug → team_id via the ``teams`` table."""
    row = _row(
        db,
        "SELECT team_id FROM teams WHERE school_slug = :s LIMIT 1",
        {"s": program_slug},
    )
    if row and row.get("team_id") is not None:
        try:
            return int(row["team_id"])
        except (TypeError, ValueError):
            return None
    return None


def _q_mood_arc(
    db: sqlite3.Connection, team_id: int, weeks: int = 12
) -> list[dict[str, Any]]:
    """Last *weeks* of weekly mood for a team."""
    return _rows(
        db,
        """
        SELECT week_start_date, mood_score, delta_from_prev_week,
               top_cause_token, top_cause_label, sample_size
        FROM fanbase_mood_weekly
        WHERE team_id = :tid
        ORDER BY week_start_date DESC
        LIMIT :lim
        """,
        {"tid": team_id, "lim": weeks},
    )


def _q_mood_delta_7d(
    db: sqlite3.Connection, team_id: int
) -> dict[str, Any] | None:
    """Latest mood row + delta_from_prev_week."""
    return _row(
        db,
        """
        SELECT week_start_date, mood_score, delta_from_prev_week,
               top_cause_label
        FROM fanbase_mood_weekly
        WHERE team_id = :tid
        ORDER BY week_start_date DESC
        LIMIT 1
        """,
        {"tid": team_id},
    )


def _q_mood_same_week_last_year(
    db: sqlite3.Connection, team_id: int, week_start_date: str
) -> dict[str, Any] | None:
    """Mood from ~365 days before *week_start_date* for the same team."""
    try:
        ref = datetime.strptime(week_start_date[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    one_year_ago = (ref - timedelta(days=365)).isoformat()
    return _row(
        db,
        """
        SELECT week_start_date, mood_score, top_cause_label
        FROM fanbase_mood_weekly
        WHERE team_id = :tid
          AND week_start_date BETWEEN date(:ago, '-14 days')
                                  AND date(:ago, '+14 days')
        ORDER BY ABS(julianday(week_start_date) - julianday(:ago)) ASC
        LIMIT 1
        """,
        {"tid": team_id, "ago": one_year_ago},
    )


def _q_conversation_quotes(
    db: sqlite3.Connection,
    *,
    days: int = 7,
    text_match: str | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Recent verbatim quotes from ``conversation_documents``.

    Used by every Tier-1 surface that requires ≥3 cited verbatim
    sources. Returns the body text + source attribution + timestamp.
    """
    cutoff = (_utcnow() - timedelta(days=days)).isoformat(timespec="seconds")
    clauses = ["external_created_at_utc >= :cutoff", "is_deleted = 0"]
    params: dict[str, Any] = {"cutoff": cutoff, "lim": limit}
    if text_match:
        clauses.append("(body_text LIKE :pat OR title_text LIKE :pat)")
        params["pat"] = f"%{text_match}%"
    sql = (
        "SELECT conversation_document_id, source_name, source_author_name, "
        "source_channel, source_url, title_text, "
        "substr(COALESCE(body_text, ''), 1, 400) AS body_excerpt, "
        "external_created_at_utc "
        "FROM conversation_documents WHERE "
        + " AND ".join(clauses)
        + " ORDER BY external_created_at_utc DESC LIMIT :lim"
    )
    return _rows(db, sql, params)


def _q_source_observations(
    db: sqlite3.Connection,
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
    days: int = 14,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Recent ``source_observations`` rows for an entity.

    Tier-1 surfaces use this for boards / podcasts / beat-writer
    timestamps when satisfying the ≥3-cited-sources gate.
    """
    cutoff = (_utcnow() - timedelta(days=days)).isoformat(timespec="seconds")
    clauses = ["observed_at_utc >= :cutoff"]
    params: dict[str, Any] = {"cutoff": cutoff, "lim": limit}
    if entity_type:
        clauses.append("entity_type = :et")
        params["et"] = entity_type
    if entity_id:
        clauses.append("entity_id = :eid")
        params["eid"] = entity_id
    sql = (
        "SELECT source_id, entity_type, entity_id, entity_label, "
        "observed_at_utc, metric, value_numeric, value_text, "
        "sample_window, capture_url "
        "FROM source_observations WHERE "
        + " AND ".join(clauses)
        + " ORDER BY observed_at_utc DESC LIMIT :lim"
    )
    return _rows(db, sql, params)


def _q_team_brand(
    db: sqlite3.Connection, team_id: int
) -> dict[str, Any] | None:
    """Brand row for accent-color + mantra + mascot."""
    return _row(
        db,
        """
        SELECT primary_color, secondary_color, mascot_name,
               abbreviation_short
        FROM team_brand
        WHERE team_id = :tid LIMIT 1
        """,
        {"tid": team_id},
    )


def _q_signature_metrics_ladder(
    db: sqlite3.Connection, team_id: int
) -> dict[str, Any] | None:
    """Pull the ``signature_metrics_ladder`` JSON blob from team_profiles.

    The profile JSON carries the ladder structure; we return the raw
    string for the prompt template to deserialize on its side.
    """
    return _row(
        db,
        """
        SELECT program_slug, voice_register, tonal_template, identity_phrase,
               mantra, profile_json
        FROM team_profiles
        WHERE team_id = :tid LIMIT 1
        """,
        {"tid": team_id},
    )


def _q_power_ratings_history(
    db: sqlite3.Connection, team_id: int, years: int = 6
) -> list[dict[str, Any]]:
    """End-of-season power_rating per year, last *years* seasons.

    Returns ``[{season_year, week, power_rating, offense_rating,
    defense_rating}, ...]`` newest-first.
    """
    return _rows(
        db,
        """
        WITH latest_week AS (
            SELECT season_year, MAX(week) AS mw
            FROM power_ratings_weekly
            WHERE team_id = :tid
            GROUP BY season_year
        )
        SELECT p.season_year, p.week, p.power_rating,
               p.offense_rating, p.defense_rating
        FROM power_ratings_weekly p
        JOIN latest_week lw
          ON lw.season_year = p.season_year AND lw.mw = p.week
        WHERE p.team_id = :tid
        ORDER BY p.season_year DESC
        LIMIT :lim
        """,
        {"tid": team_id, "lim": years},
    )


def _q_power_delta_7d(
    db: sqlite3.Connection, team_id: int
) -> dict[str, Any] | None:
    """Current week vs trailing-week power_rating for a team."""
    rows = _rows(
        db,
        """
        SELECT week, season_year, power_rating
        FROM power_ratings_weekly
        WHERE team_id = :tid
        ORDER BY season_year DESC, week DESC
        LIMIT 2
        """,
        {"tid": team_id},
    )
    if len(rows) < 2:
        return rows[0] if rows else None
    cur, prev = rows[0], rows[1]
    return {
        "current": cur,
        "prior": prev,
        "delta": (cur.get("power_rating") or 0) - (prev.get("power_rating") or 0),
    }


def _q_cohort_divergence(
    db: sqlite3.Connection, team_id: int, weeks: int = 4
) -> list[dict[str, Any]]:
    """Last *weeks* of cohort divergence for a team."""
    return _rows(
        db,
        """
        SELECT week, divergence_score, num_cohorts_qualifying
        FROM team_cohort_divergence_week
        WHERE team_id = :tid
        ORDER BY week DESC
        LIMIT :lim
        """,
        {"tid": team_id, "lim": weeks},
    )


def _q_lexicon_spikes(
    db: sqlite3.Connection, team_id: int, limit: int = 8
) -> list[dict[str, Any]]:
    """Top spiking phrases this week for the team."""
    return _rows(
        db,
        """
        SELECT phrase, week_start_date, mention_count, spike_pct_wow,
               origin_community, sample_quotes_json, narrative
        FROM lexicon_weekly
        WHERE related_team_id = :tid
        ORDER BY week_start_date DESC, spike_pct_wow DESC
        LIMIT :lim
        """,
        {"tid": team_id, "lim": limit},
    )


def _q_rivalry_obsession(
    db: sqlite3.Connection, team_id: int
) -> list[dict[str, Any]]:
    """Most-recent rivalry-obsession rows touching this team."""
    return _rows(
        db,
        """
        SELECT rivalry_slug, rivalry_name, team_a_id, team_b_id,
               week_start_date, a_mentions_b_count, b_mentions_a_count,
               ratio_dominant, leaning_team, take
        FROM rivalry_obsession_weekly
        WHERE team_a_id = :tid OR team_b_id = :tid
        ORDER BY week_start_date DESC
        LIMIT 6
        """,
        {"tid": team_id},
    )


def _q_recent_daily_headlines(
    db: sqlite3.Connection, days: int = 14
) -> list[dict[str, Any]]:
    """Last *days* of daily_takes headlines — used for non-repetition."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    return _rows(
        db,
        """
        SELECT dt.edition_date, dt.rank_position, dt.headline,
               dt.primary_entity_slug, dt.primary_entity_type
        FROM daily_takes dt
        JOIN daily_editions de ON de.edition_date = dt.edition_date
        WHERE de.status = 'published'
          AND dt.edition_date >= :cutoff
        ORDER BY dt.edition_date DESC, dt.rank_position ASC
        """,
        {"cutoff": cutoff},
    )


def _q_player_honors(
    db: sqlite3.Connection, player_id: int
) -> list[dict[str, Any]]:
    """All-time honors rows for a player."""
    return _rows(
        db,
        """
        SELECT season_year, week, honor_scope, honor_name, selector,
               honor_team, position, placement, consensus_flag,
               unanimous_flag
        FROM player_honors
        WHERE player_id = :pid
        ORDER BY season_year DESC, week DESC NULLS LAST
        """,
        {"pid": player_id},
    )


def _q_nfl_pipeline_for_program(
    db: sqlite3.Connection, college_team_id: int, years: int = 6
) -> list[dict[str, Any]]:
    """NFL draft picks out of *college_team_id* in the last *years* drafts.

    v5.3 spec name ``nfl_pipeline`` → actual table
    :data:`player_nfl_draft`.
    """
    return _rows(
        db,
        """
        SELECT draft_year, round, pick, overall, player_id, player_name,
               position, nfl_team, nfl_team_abbr
        FROM player_nfl_draft
        WHERE college_team_id = :tid
          AND draft_year >= :since
        ORDER BY draft_year DESC, overall ASC
        """,
        {"tid": college_team_id, "since": date.today().year - years},
    )


def _q_player_last_n_games(
    db: sqlite3.Connection, player_id: int, n: int = 4
) -> list[dict[str, Any]]:
    """Last *n* per-game stat rows for a player (aggregated by game_id).

    v5.3 spec name ``game_player_stats`` → actual table
    :data:`player_game_stats`.
    """
    return _rows(
        db,
        """
        SELECT game_id, season_year, week, season_type,
               category, stat_type, stat_value_num, stat_value_text
        FROM player_game_stats
        WHERE player_id = :pid
        ORDER BY season_year DESC, week DESC, game_id DESC
        LIMIT :lim
        """,
        {"pid": player_id, "lim": n * 30},  # ~30 stat rows per game
    )


# ---------------------------------------------------------------------------
# 12 priority-surface builders
# ---------------------------------------------------------------------------


def build_edition_cover_context(
    season: int, week: int, db: sqlite3.Connection
) -> dict[str, Any]:
    """Pull all proprietary data for the edition-cover essay prompt.

    See ``DESIGN_AUDIT_2026_05_15_v5_3.md`` Part 4 §"Edition cover
    essay" for the manifest spec.

    Session 6 addendum (2026-05-22): also surface calendar context
    (``publish_date``, ``is_offseason``, ``days_to_kickoff``). Prior
    behavior passed only ``(season, week)`` to the prompt, which let
    Pattern C interpret an offseason edition's calendar ISO week
    number ("week 18" = first Monday of May) as a football week ("week
    18" = mid-November championship week). The live W18 cover essay
    shipped a 1,100-word essay set in mid-November on a May 4
    publishing date. Surfacing the calendar context lets ``compose_
    prompt_body`` emit a CALENDAR CONTEXT block the LLM can ground in.
    """
    from datetime import date as _date
    from cfb_rankings.common.cfb_calendar import (
        is_offseason as _is_offseason,
        days_to_kickoff as _days_to_kickoff,
    )

    # Compute the week's ISO date string for cohort lookups.
    # week_iso is treated as a free-text key in team_cohort_week.
    week_iso = f"{season}-W{int(week):02d}"

    # Calendar context. Best-effort: derive publish_date from the
    # edition row when available; otherwise default to today (the
    # build-time date), which is the next best anchor for "where in
    # the calendar is this edition publishing."
    publish_date: _date | None = None
    try:
        row = db.execute(
            "select publish_date from editions where edition_slug = ?",
            (f"{season}-w{int(week):02d}",),
        ).fetchone()
        if row and row[0]:
            publish_date = _date.fromisoformat(str(row[0]))
    except Exception:
        publish_date = None
    if publish_date is None:
        publish_date = _date.today()

    try:
        offseason_flag = _is_offseason(publish_date, db)
    except Exception:
        offseason_flag = publish_date.month < 8 or publish_date.month >= 1
    try:
        kickoff_days = _days_to_kickoff(publish_date, db=db)
    except Exception:
        kickoff_days = None

    return {
        "season": season,
        "week": week,
        "publish_date": publish_date.isoformat(),
        "is_offseason": offseason_flag,
        "days_to_kickoff": kickoff_days,
        "prior_4_covers": _q_prior_covers(db, season, week, limit=4),
        "cohort_mood_dumbbell": _q_cohort_mood_dumbbell(db, week_iso),
        "rank_disagreements": _q_rank_disagreements(db, season, week, limit=10),
        "active_storylines": _q_active_storylines(db),
        "major_wire_7d": _q_recent_wire(db, days=7, impact="MAJOR", limit=20),
        "resolved_receipts": _q_resolved_receipts(
            db, days=14, min_surprise=80.0, limit=8
        ),
        "top_chronicle_moments": _q_top_chronicle(db, days=14, limit=10),
        "season_phase": _q_season_phase(db, season, week),
    }


def build_daily_lead_context(
    date_: date, db: sqlite3.Connection
) -> dict[str, Any]:
    """Pull all proprietary data for the daily-edition rank-1 lead essay.

    See v5.3 Part 4 §"Daily edition lead essay" for the manifest spec.
    The "existing bundle" referenced in the manifest is left for the
    caller to merge in — this builder only contributes the proprietary
    enrichments (mood Δ, same-week-1yr, cohort transitions, divergence,
    archive, yesterday's headlines, power Δ).
    """
    iso = date_.isoformat() if hasattr(date_, "isoformat") else str(date_)
    week_iso = date_.strftime("%Y-W%V") if hasattr(date_, "strftime") else iso

    # The "primary entity" for the lead is published into daily_takes;
    # we surface yesterday's #1 entity to anchor mood-delta lookup.
    yesterday = _row(
        db,
        """
        SELECT dt.primary_entity_slug, dt.primary_entity_type, dt.edition_date
        FROM daily_takes dt
        JOIN daily_editions de ON de.edition_date = dt.edition_date
        WHERE de.status = 'published' AND dt.rank_position = 1
        ORDER BY dt.edition_date DESC LIMIT 1
        """,
    )
    headline_entity_slug = (yesterday or {}).get("primary_entity_slug")
    team_id: int | None = None
    if headline_entity_slug:
        team_id = _q_team_id_for_slug(db, headline_entity_slug)

    mood_delta: dict[str, Any] | None = None
    mood_1yr: dict[str, Any] | None = None
    power_delta: dict[str, Any] | None = None
    if team_id is not None:
        mood_delta = _q_mood_delta_7d(db, team_id)
        if mood_delta and mood_delta.get("week_start_date"):
            mood_1yr = _q_mood_same_week_last_year(
                db, team_id, mood_delta["week_start_date"]
            )
        power_delta = _q_power_delta_7d(db, team_id)

    return {
        "date": iso,
        "week_iso": week_iso,
        "headline_entity_slug": headline_entity_slug,
        "headline_entity_team_id": team_id,
        "mood_delta_7d": mood_delta,
        "mood_same_week_1yr_ago": mood_1yr,
        "cohort_transitions": _q_cohort_mood_dumbbell(db, week_iso),
        "cohort_divergence": (
            _q_cohort_divergence(db, team_id, weeks=4) if team_id else []
        ),
        "archive_threads": [],  # v5.3 spec table not yet shipped
        "recent_daily_headlines": _q_recent_daily_headlines(db, days=14),
        "power_delta_7d": power_delta,
    }


def build_heisman_weekly_context(
    season: int, week: int, db: sqlite3.Connection
) -> dict[str, Any]:
    """Pull all proprietary data for the weekly Heisman narrative.

    See v5.3 Part 4 §"Heisman weekly narrative" for the manifest spec.
    Includes top-10 board, market odds, vote-history archetype comps,
    last-4-games for top 5, season context, honors, conversation
    volume Δ.
    """
    top10 = _rows(
        db,
        """
        SELECT player_id, team_id, rank_overall, nowcast_rank,
               forecast_rank, latent_score, win_probability,
               finalist_probability, any_ballot_probability,
               market_implied_probability, market_american_odds
        FROM heisman_rankings_weekly
        WHERE season_year = :s AND week = :w
        ORDER BY COALESCE(rank_overall, 999) ASC
        LIMIT 10
        """,
        {"s": season, "w": week},
    )

    market_odds = _rows(
        db,
        """
        SELECT player_id, player_name, team_name, provider,
               american_odds, decimal_odds, implied_probability
        FROM heisman_market_odds_weekly
        WHERE season_year = :s AND week = :w
        ORDER BY COALESCE(implied_probability, 0) DESC
        LIMIT 25
        """,
        {"s": season, "w": week},
    )

    vote_history = _rows(
        db,
        """
        SELECT season_year, player_id, place, winner_flag,
               finalist_flag, first_place_votes, total_points
        FROM heisman_vote_results
        WHERE place <= 5
        ORDER BY season_year DESC
        LIMIT 200
        """,
    )

    last4_top5: list[dict[str, Any]] = []
    for cand in top10[:5]:
        pid = cand.get("player_id")
        if pid is None:
            continue
        last4_top5.append(
            {
                "player_id": pid,
                "games": _q_player_last_n_games(db, int(pid), n=4),
                "honors": _q_player_honors(db, int(pid)),
            }
        )

    return {
        "season": season,
        "week": week,
        "top_10": top10,
        "market_odds": market_odds,
        "vote_history_archetype_comps": vote_history,
        "last_4_games_top_5": last4_top5,
        "conversation_volume_top_5": [
            {
                "player_id": cand.get("player_id"),
                "quotes": _q_conversation_quotes(db, days=7, limit=4),
            }
            for cand in top10[:5]
        ],
        "archive_threads": [],
    }


def build_storyline_chapter_context(
    thread_slug: str, db: sqlite3.Connection
) -> dict[str, Any]:
    """Pull all proprietary data for a storyline-thread chapter prompt.

    See v5.3 Part 4 §"Storyline thread chapter" for the manifest spec.
    """
    thread = _row(
        db,
        """
        SELECT thread_slug, title, dek, accent_hex, status,
               primary_program_slugs, primary_conference_slug,
               voice_register_source, chapter_count, last_chapter_at
        FROM storyline_threads
        WHERE thread_slug = :slug LIMIT 1
        """,
        {"slug": thread_slug},
    )

    last_3_chapters = _rows(
        db,
        """
        SELECT chapter_number, title, dek, body_markdown, byline,
               published_at, referenced_chapter_ids,
               referenced_sources_json, pull_quote
        FROM storyline_chapters
        WHERE thread_slug = :slug
        ORDER BY chapter_number DESC
        LIMIT 3
        """,
        {"slug": thread_slug},
    )

    # Pull recent wire for each primary program. primary_program_slugs is
    # a JSON-encoded array; we parse defensively.
    program_slugs: list[str] = []
    raw_slugs = (thread or {}).get("primary_program_slugs") if thread else None
    if raw_slugs:
        try:
            import json as _json
            parsed = _json.loads(raw_slugs)
            if isinstance(parsed, list):
                program_slugs = [str(s) for s in parsed if s]
        except (ValueError, TypeError):
            program_slugs = []

    wire_per_program: list[dict[str, Any]] = []
    for slug in program_slugs:
        wire_per_program.append(
            {
                "program_slug": slug,
                "wire_14d": _q_recent_wire(db, days=14, program_slug=slug, limit=15),
            }
        )

    return {
        "thread_slug": thread_slug,
        "thread": thread,
        "last_3_chapters": last_3_chapters,
        "wire_per_primary_program": wire_per_program,
        "conversation_quotes": _q_conversation_quotes(
            db, days=14, text_match=thread_slug, limit=10
        ),
        "source_observations": _q_source_observations(
            db, entity_type="team", days=14, limit=20
        ),
        "prior_referenced_sources": [
            c.get("referenced_sources_json") for c in last_3_chapters
        ],
        "archive_threads": [],
    }


def build_mailbag_context(
    question_id: int, db: sqlite3.Connection
) -> dict[str, Any]:
    """Pull all proprietary data for a mailbag-answer prompt.

    See v5.3 Part 4 §"Mailbag answer" for the manifest spec.
    """
    question = _row(
        db,
        """
        SELECT id, submitter_handle, question_text, topic_tags_json, status,
               submitted_at_utc
        FROM mailbag_submissions
        WHERE id = :qid LIMIT 1
        """,
        {"qid": question_id},
    )

    # Parse topic tags
    topic_tags: list[str] = []
    raw_tags = (question or {}).get("topic_tags_json") if question else None
    if raw_tags:
        try:
            import json as _json
            parsed = _json.loads(raw_tags)
            if isinstance(parsed, list):
                topic_tags = [str(t) for t in parsed if t]
        except (ValueError, TypeError):
            topic_tags = []

    # Find named program slugs by checking topic_tags against teams.
    program_classifications: list[dict[str, Any]] = []
    for tag in topic_tags:
        tid = _q_team_id_for_slug(db, tag)
        if tid is None:
            continue
        rows = _rows(
            db,
            """
            SELECT season_year, primary_archetype_slug, primary_confidence,
                   modifier_slugs_json
            FROM fanbase_classification_history
            WHERE team_id = :tid
            ORDER BY season_year DESC LIMIT 6
            """,
            {"tid": tid},
        )
        program_classifications.append({"program_slug": tag, "history": rows})

    # Past mailbag answers tagged to adjacent topics — non-repetition.
    past_answers: list[dict[str, Any]] = []
    if topic_tags:
        # Build a LIKE pattern OR-chain.
        ors = " OR ".join(
            f"primary_topic = :t{i}" for i in range(len(topic_tags))
        )
        params = {f"t{i}": t for i, t in enumerate(topic_tags)}
        past_answers = _rows(
            db,
            f"""
            SELECT edition_slug, rank_position, primary_topic,
                   substr(answer_body, 1, 400) AS body_excerpt,
                   generation_model
            FROM mailbag_answers
            WHERE {ors}
            ORDER BY edition_slug DESC
            LIMIT 10
            """,
            params,
        )

    # Active storylines matching tags
    active_threads_matching: list[dict[str, Any]] = []
    for tag in topic_tags:
        active_threads_matching.extend(
            _rows(
                db,
                """
                SELECT thread_slug, title, dek, status, last_chapter_at
                FROM storyline_threads
                WHERE status = 'active'
                  AND (primary_program_slugs LIKE :pat
                       OR primary_conference_slug = :tag)
                """,
                {"pat": f"%{tag}%", "tag": tag},
            )
        )

    return {
        "question_id": question_id,
        "question": question,
        "topic_tags": topic_tags,
        "conversation_quotes": _q_conversation_quotes(
            db,
            days=14,
            text_match=topic_tags[0] if topic_tags else None,
            limit=10,
        ),
        "fanbase_classification_history": program_classifications,
        "archive_threads": [],
        "past_mailbag_answers": past_answers,
        "active_storylines_matching": active_threads_matching,
    }


def build_reaction_context(
    wire_id: int, db: sqlite3.Connection
) -> dict[str, Any]:
    """Pull all proprietary data for a wire-triggered reaction story.

    See v5.3 Part 4 §"Reaction story" for the manifest spec.
    """
    wire = _row(
        db,
        """
        SELECT id, occurred_at, program_slug, program_display, actor_kind,
               action, why_it_matters, impact_label, historical_comp,
               source_name, related_thread_slug,
               fan_intel_velocity_spike
        FROM wire_entries WHERE id = :wid LIMIT 1
        """,
        {"wid": wire_id},
    )

    program_slug = (wire or {}).get("program_slug")
    team_id = _q_team_id_for_slug(db, program_slug) if program_slug else None

    cohort_divergence: list[dict[str, Any]] = []
    mood_delta: dict[str, Any] | None = None
    if team_id is not None:
        cohort_divergence = _q_cohort_divergence(db, team_id, weeks=4)
        mood_delta = _q_mood_delta_7d(db, team_id)

    # Recruiting & honors: v5.3 spec calls for recruiting_rankings (not
    # yet shipped). We at least scan player_recruiting_profiles if the
    # wire row names a player. The action text often carries the player
    # name in human form — defer the name-parse to the prompt caller and
    # return the empty list here.

    return {
        "wire_id": wire_id,
        "wire": wire,
        "historical_comp": (wire or {}).get("historical_comp"),
        "cohort_divergence": cohort_divergence,
        "archive_threads": [],
        "mood_delta_7d": mood_delta,
        "recruiting_rank": None,  # spec table not yet shipped
        "player_season_context": None,
        "player_honors": [],
    }


def build_chronicle_context(
    program_slug: str, week: int, db: sqlite3.Connection
) -> dict[str, Any]:
    """Pull all proprietary data for a chronicle-card prompt.

    See v5.3 Part 4 §"Chronicle card" for the manifest spec.
    """
    team_id = _q_team_id_for_slug(db, program_slug)

    recent_chronicle: list[dict[str, Any]] = []
    classification_history: list[dict[str, Any]] = []
    power_sparkline: list[dict[str, Any]] = []
    if team_id is not None:
        recent_chronicle = _rows(
            db,
            """
            SELECT card_type, headline, week, season_year,
                   source_attribution, surprise_score
            FROM team_chronicle_observations
            WHERE team_id = :tid AND is_published = 1
            ORDER BY season_year DESC, week DESC NULLS LAST
            LIMIT 40
            """,
            {"tid": team_id},
        )
        classification_history = _rows(
            db,
            """
            SELECT season_year, primary_archetype_slug, primary_confidence,
                   modifier_slugs_json
            FROM fanbase_classification_history
            WHERE team_id = :tid
            ORDER BY season_year DESC LIMIT 6
            """,
            {"tid": team_id},
        )
        power_sparkline = _q_power_ratings_history(db, team_id, years=6)

    return {
        "program_slug": program_slug,
        "week": week,
        "team_id": team_id,
        "candidate_observations_evidence": None,  # caller supplies blob
        "recent_chronicle_headlines": recent_chronicle,
        "fanbase_classification_history": classification_history,
        "power_ratings_sparkline_6y": power_sparkline,
        "player_archetype_peers": [],  # spec: cross-season PPA lookup
    }


def build_team_narrative_context(
    program_slug: str, db: sqlite3.Connection
) -> dict[str, Any]:
    """Pull all proprietary data for the state-of-team narrative.

    See v5.3 Part 4 §"Team narrative" for the manifest spec.
    """
    team_id = _q_team_id_for_slug(db, program_slug)

    signature_metrics: dict[str, Any] | None = None
    mood_arc: list[dict[str, Any]] = []
    nfl_alumni: list[dict[str, Any]] = []
    top_chronicle: list[dict[str, Any]] = []
    if team_id is not None:
        signature_metrics = _q_signature_metrics_ladder(db, team_id)
        mood_arc = _q_mood_arc(db, team_id, weeks=12)
        nfl_alumni = _q_nfl_pipeline_for_program(db, team_id, years=6)
        top_chronicle = _q_top_chronicle(
            db, days=90, program_slug=program_slug, limit=5
        )

    # Recent edition mentions referencing this program slug. Body text
    # might mention the slug or program display; we use a LIKE search.
    recent_edition_mentions = _rows(
        db,
        """
        SELECT ef.edition_slug, e.publish_date, ef.feature_kind, ef.title,
               substr(ef.body_markdown, 1, 300) AS body_excerpt
        FROM edition_features ef
        JOIN editions e ON e.edition_slug = ef.edition_slug
        WHERE ef.body_markdown LIKE :pat
        ORDER BY e.publish_date DESC LIMIT 6
        """,
        {"pat": f"%{program_slug}%"},
    )

    return {
        "program_slug": program_slug,
        "team_id": team_id,
        "signature_metrics_ladder": signature_metrics,
        "mood_arc_12w": mood_arc,
        "nfl_alumni_active": nfl_alumni,
        "recruiting_trajectory_5y": [],  # spec table not yet shipped
        "recent_edition_mentions": recent_edition_mentions,
        "top_chronicle_90d": top_chronicle,
    }


def build_pulse_state_context(
    program_slug: str, db: sqlite3.Connection
) -> dict[str, Any]:
    """Pull all proprietary data for the Pulse state-of-team lede.

    See v5.3 Part 4 §"Pulse state-of-team / lede" for the manifest spec.
    """
    team_id = _q_team_id_for_slug(db, program_slug)

    # Pull the latest 4 weeks of cohort-week rows; the "dominant cohort
    # transition" is computed in the prompt template from these.
    cohort_4w: list[dict[str, Any]] = []
    mood_4w: list[dict[str, Any]] = []
    cohort_div: list[dict[str, Any]] = []
    lexicon: list[dict[str, Any]] = []
    wire_7d: list[dict[str, Any]] = []
    rivalry: list[dict[str, Any]] = []
    power_delta: dict[str, Any] | None = None
    mood_1yr: dict[str, Any] | None = None

    if team_id is not None:
        cohort_4w = _rows(
            db,
            """
            SELECT cohort, week, sentiment_score, volume, confidence_tier
            FROM team_cohort_week
            WHERE team_id = :tid
            ORDER BY week DESC LIMIT 32
            """,
            {"tid": team_id},
        )
        mood_4w = _q_mood_arc(db, team_id, weeks=4)
        cohort_div = _q_cohort_divergence(db, team_id, weeks=4)
        lexicon = _q_lexicon_spikes(db, team_id, limit=8)
        wire_7d = _q_recent_wire(db, days=7, program_slug=program_slug, limit=10)
        rivalry = _q_rivalry_obsession(db, team_id)
        power_delta = _q_power_delta_7d(db, team_id)
        if mood_4w and mood_4w[0].get("week_start_date"):
            mood_1yr = _q_mood_same_week_last_year(
                db, team_id, mood_4w[0]["week_start_date"]
            )

    return {
        "program_slug": program_slug,
        "team_id": team_id,
        "cohort_transitions_4w": cohort_4w,
        "mood_arc_4w": mood_4w,
        "mood_same_week_1yr_ago": mood_1yr,
        "cohort_divergence_4w": cohort_div,
        "lexicon_spikes": lexicon,
        "wire_7d": wire_7d,
        "rivalry_obsession_weekly": rivalry,
        "power_delta_7d": power_delta,
    }


def build_wire_why_it_matters_context(
    wire_id: int, db: sqlite3.Connection
) -> dict[str, Any]:
    """Pull all proprietary data for a wire "why it matters" sidebar.

    See v5.3 Part 4 §"Wire 'why it matters' sidebar" for the manifest.
    """
    wire = _row(
        db,
        """
        SELECT id, occurred_at, program_slug, program_display, actor_kind,
               action, why_it_matters, impact_label, historical_comp,
               fan_intel_velocity_spike
        FROM wire_entries WHERE id = :wid LIMIT 1
        """,
        {"wid": wire_id},
    )

    program_slug = (wire or {}).get("program_slug")
    actor_kind = (wire or {}).get("actor_kind")
    action = (wire or {}).get("action")
    team_id = _q_team_id_for_slug(db, program_slug) if program_slug else None

    # 5yr archetype lookup over wire_entries — same (actor_kind, action
    # word) historically.
    archetype_history: list[dict[str, Any]] = []
    if actor_kind and action:
        archetype_history = _rows(
            db,
            """
            SELECT id, occurred_at, program_slug, action, why_it_matters,
                   impact_label
            FROM wire_entries
            WHERE actor_kind = :ak
              AND action LIKE :pat
              AND occurred_at >= date('now', '-5 years')
              AND id != :wid
            ORDER BY occurred_at DESC LIMIT 20
            """,
            {"ak": actor_kind, "pat": f"%{action[:30]}%", "wid": wire_id},
        )

    brand: dict[str, Any] | None = None
    mood_delta: dict[str, Any] | None = None
    nfl_alumni: list[dict[str, Any]] = []
    if team_id is not None:
        brand = _q_team_brand(db, team_id)
        mood_delta = _q_mood_delta_7d(db, team_id)
        nfl_alumni = _q_nfl_pipeline_for_program(db, team_id, years=4)

    # Market snapshots — recent prediction-market reaction to similar
    # moves. Scope by team_id when we can.
    market_snapshots = _rows(
        db,
        """
        SELECT provider, market_key, market_type, outcome_label,
               implied_probability, last_price, snapshot_time_utc
        FROM prediction_market_snapshots
        WHERE team_id = :tid
          AND snapshot_time_utc >= date('now', '-30 days')
        ORDER BY snapshot_time_utc DESC LIMIT 15
        """,
        {"tid": team_id},
    ) if team_id is not None else []

    return {
        "wire_id": wire_id,
        "wire": wire,
        "archetype_history_5yr": archetype_history,
        "recruiting_rank": None,  # spec table not yet shipped
        "nfl_pipeline": nfl_alumni,
        "team_brand": brand,
        "mood_delta_7d": mood_delta,
        "prediction_market_snapshots": market_snapshots,
    }


def build_canon_top10_context(
    list_slug: str, rank: int, db: sqlite3.Connection
) -> dict[str, Any]:
    """Pull all proprietary data for a canon top-10 entry prompt.

    See v5.3 Part 4 §"Canon entry top-10" for the manifest spec.
    """
    entry = _row(
        db,
        """
        SELECT id, list_slug, rank, entity_kind, entity_slug,
               entity_display_name, program_slug, program_label, era_label,
               summary_short, editorial_paragraph, statline,
               cohort_split_stat_rank, cohort_split_casual_rank,
               cohort_split_label, prior_year_rank, rank_delta_label
        FROM canon_entries
        WHERE list_slug = :slug AND rank = :rk LIMIT 1
        """,
        {"slug": list_slug, "rk": rank},
    )

    # Prior-year same-rank in same list for continuity.
    prior_year_entry: dict[str, Any] | None = None
    if entry and entry.get("entity_slug"):
        prior_year_entry = _row(
            db,
            """
            SELECT crh.list_slug, crh.edition_year, crh.entity_slug,
                   crh.rank_in_year
            FROM canon_revision_history crh
            WHERE crh.list_slug = :slug AND crh.entity_slug = :es
            ORDER BY crh.edition_year DESC LIMIT 1
            """,
            {"slug": list_slug, "es": entry["entity_slug"]},
        )

    # Power-ratings final rank if we can resolve entity_slug → team_id.
    final_power_rank: dict[str, Any] | None = None
    nfl_drafted: list[dict[str, Any]] = []
    top_chronicle: list[dict[str, Any]] = []
    if entry and (entry.get("program_slug") or entry.get("entity_slug")):
        slug = entry.get("program_slug") or entry["entity_slug"]
        team_id = _q_team_id_for_slug(db, slug)
        if team_id is not None:
            history = _q_power_ratings_history(db, team_id, years=6)
            final_power_rank = history[0] if history else None
            nfl_drafted = _q_nfl_pipeline_for_program(db, team_id, years=10)
            top_chronicle = _q_top_chronicle(
                db, days=3650, program_slug=slug, limit=3
            )

    # Prior editions mentioning the entry — continuity.
    prior_editions: list[dict[str, Any]] = []
    if entry and entry.get("entity_slug"):
        prior_editions = _rows(
            db,
            """
            SELECT ef.edition_slug, e.publish_date, ef.feature_kind,
                   ef.title
            FROM edition_features ef
            JOIN editions e ON e.edition_slug = ef.edition_slug
            WHERE ef.canon_entry_slug = :es
            ORDER BY e.publish_date DESC LIMIT 5
            """,
            {"es": entry["entity_slug"]},
        )

    return {
        "list_slug": list_slug,
        "rank": rank,
        "entry": entry,
        "prior_year_entry": prior_year_entry,
        "cohort_split": {
            "stat_rank": (entry or {}).get("cohort_split_stat_rank"),
            "casual_rank": (entry or {}).get("cohort_split_casual_rank"),
            "label": (entry or {}).get("cohort_split_label"),
        } if entry else None,
        "final_power_rank": final_power_rank,
        "nfl_drafted_from_season": nfl_drafted,
        "top_chronicle_3": top_chronicle,
        "archive_thread": None,  # spec table not yet shipped
        "prior_editions": prior_editions,
    }


def build_player_season_narrative_context(
    player_id: int, season: int, db: sqlite3.Connection
) -> dict[str, Any]:
    """Pull all proprietary data for the player-season narrative (Accolade
    Lens).

    See v5.3 Part 4 §"Player season narrative" for the manifest spec —
    this is the surface where the *archetype-peer engine* is the
    differentiator.
    """
    season_games = _rows(
        db,
        """
        SELECT game_id, week, season_type, category, stat_type,
               stat_value_num, stat_value_text
        FROM player_game_stats
        WHERE player_id = :pid AND season_year = :s
        ORDER BY week ASC
        """,
        {"pid": player_id, "s": season},
    )

    usage = _rows(
        db,
        """
        SELECT week, usage_overall, usage_pass, usage_rush,
               usage_first_down, usage_passing_downs, usage_standard_downs
        FROM player_usage_season
        WHERE player_id = :pid AND season_year = :s
        ORDER BY week DESC LIMIT 1
        """,
        {"pid": player_id, "s": season},
    )

    value_metrics = _rows(
        db,
        """
        SELECT week, metric_name, metric_value, plays
        FROM player_value_metrics
        WHERE player_id = :pid AND season_year = :s
        ORDER BY week DESC, metric_name ASC
        LIMIT 50
        """,
        {"pid": player_id, "s": season},
    )

    season_summary = _row(
        db,
        """
        SELECT player_id, season_year, team_id, position, class_year,
               cfb_index_score, games_played, snap_count_proxy,
               wepa_total, milestones_json, is_projected
        FROM player_season_summary
        WHERE player_id = :pid AND season_year = :s LIMIT 1
        """,
        {"pid": player_id, "s": season},
    )

    honors = _q_player_honors(db, player_id)

    heisman_position = _rows(
        db,
        """
        SELECT season_year, week, rank_overall, nowcast_rank,
               forecast_rank, latent_score, win_probability,
               market_implied_probability
        FROM heisman_rankings_weekly
        WHERE player_id = :pid AND season_year = :s
        ORDER BY week DESC LIMIT 1
        """,
        {"pid": player_id, "s": season},
    )

    # Archetype peers — the proprietary differentiator. Find prior
    # seasons where a player at the same position posted PPA totals
    # within ±5% of this player's PPA total at the same week share.
    # We approximate by aggregating stat_value_num for category='passing'
    # or 'rushing' WEPA / EPA stats. If the position is unknown we skip.
    archetype_peers: list[dict[str, Any]] = []
    pos = (season_summary or {}).get("position")
    target_total = (season_summary or {}).get("wepa_total")
    if pos and target_total is not None:
        try:
            target = float(target_total)
            band_lo = target * 0.95
            band_hi = target * 1.05
            archetype_peers = _rows(
                db,
                """
                SELECT player_id, season_year, team_id, position,
                       cfb_index_score, wepa_total
                FROM player_season_summary
                WHERE position = :pos
                  AND season_year != :s
                  AND wepa_total BETWEEN :lo AND :hi
                ORDER BY ABS(wepa_total - :target) ASC LIMIT 3
                """,
                {
                    "pos": pos,
                    "s": season,
                    "lo": band_lo,
                    "hi": band_hi,
                    "target": target,
                },
            )
        except (TypeError, ValueError):
            archetype_peers = []

    # NFL pipeline historical comps for the player's program.
    nfl_history: list[dict[str, Any]] = []
    team_id = (season_summary or {}).get("team_id")
    if team_id is not None:
        nfl_history = _q_nfl_pipeline_for_program(db, int(team_id), years=10)

    # Conversation volume / quotes for the player's name. We look up the
    # ``players`` table to get the display name first.
    player_row = _row(
        db,
        "SELECT player_id, full_name FROM players WHERE player_id = :pid",
        {"pid": player_id},
    )
    name = (player_row or {}).get("full_name")
    conversation_quotes: list[dict[str, Any]] = []
    if name:
        conversation_quotes = _q_conversation_quotes(
            db, days=14, text_match=name, limit=8
        )

    brand: dict[str, Any] | None = None
    chronicle_tie_ins: list[dict[str, Any]] = []
    if team_id is not None:
        brand = _q_team_brand(db, int(team_id))
    if name:
        chronicle_tie_ins = _rows(
            db,
            """
            SELECT card_type, headline, body_md, source_attribution,
                   week, season_year
            FROM team_chronicle_observations
            WHERE is_published = 1
              AND (headline LIKE :pat OR body_md LIKE :pat)
            ORDER BY season_year DESC, week DESC NULLS LAST LIMIT 6
            """,
            {"pat": f"%{name}%"},
        )

    return {
        "player_id": player_id,
        "season": season,
        "player": player_row,
        "season_games": season_games,
        "usage": usage[0] if usage else None,
        "value_metrics": value_metrics,
        "season_summary": season_summary,
        "honors": honors,
        "heisman_position": heisman_position[0] if heisman_position else None,
        "archetype_peers": archetype_peers,
        "nfl_pipeline_program_history": nfl_history,
        "conversation_quotes": conversation_quotes,
        "team_brand": brand,
        "chronicle_tie_ins": chronicle_tie_ins,
    }


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "build_edition_cover_context",
    "build_daily_lead_context",
    "build_heisman_weekly_context",
    "build_storyline_chapter_context",
    "build_mailbag_context",
    "build_reaction_context",
    "build_chronicle_context",
    "build_team_narrative_context",
    "build_pulse_state_context",
    "build_wire_why_it_matters_context",
    "build_canon_top10_context",
    "build_player_season_narrative_context",
]
