"""Hidden-gem proprietary evidence sources for Chronicle pipeline.

Each function in this module returns list[EvidenceRow] from a specific
underused data source in the CFB Index DB. The retriever.py orchestrator
calls these for the appropriate card_type and merges into the evidence pool.

Data sources surfaced here:
1. Polymarket / Kalshi prediction market observations (source_observations table,
   source_id IN ('polymarket','kalshi')) — 160 rows as of 2026-05-23.
2. Statistical mirror-match comparables (player_mirror_matches) — empty today,
   populates once compute_mirror_matches() has been run for a season.
3. Season narrative arcs (bets/narrative_arc.py YAML seeds + optional
   team_season_arc for team-level arcs).
4. Week-over-week deltas (page-state blob in what_changed.py) — no dedicated
   table yet; this adapter returns [] gracefully until P0.7 schema lands.
5. Anniversary "on this day" hits via player_game_stats / games join.
6. Era-relative comparisons via player_season_stats cohort queries.
7. Signature plays — curated in player_signature_plays (276 rows).
8. Team voice JSON — stored in team_voice table (keyed on team_id; currently
   empty in prod DB until profiles are ingested; 127 YAML profiles exist on
   disk so this will populate once `manage.py load-profiles` runs).
9. Conversation documents — Reddit / forum posts in conversation_documents
   (110 rows) with author demographic tags.
10. Editorial citations — pre-validated quote/citation pairs from
    editorial_citations (0 rows today; populates via editions pipeline).

Schema notes (as of 2026-05-23):
- source_observations has NO entity_slug / player_id column — entities are
  matched via entity_label (text) or entity_id (market slug). The adapter
  does a fuzzy LIKE match against slug.
- player_mirror_matches stores pre-computed cosine matches keyed on
  (player_id, season_year) — this adapter requires a player_id lookup.
- conversation_documents lacks a direct entity_slug column; we join against
  body_text / title_text LIKE patterns. The table has source_name,
  author_identity_class, demographic_slice.
- editorial_citations is keyed on generation_id, NOT entity_slug. The adapter
  queries without entity_slug when slug-based filtering is unsupported.
- team_voice is keyed on team_id; fetch_team_voice() requires a team_id lookup.
- narrative_arc data lives in YAML seeds (bets/narrative_arc.py) — no DB table
  yet. The adapter reads from YAML and returns [] for team entities.
- team_season_arc exists for team-level arc data (0 rows today but schema live).
"""
from __future__ import annotations

import datetime as _dt
import json
import logging

from cfb_rankings.chronicle.retriever import EvidenceRow

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _slug_to_player_id(db, slug: str) -> int | None:
    """Resolve player slug → integer player_id. Returns None on miss."""
    row = db.query_one(
        "SELECT player_id FROM players WHERE slug = ?",
        (slug,),
    )
    if row:
        return int(row["player_id"])
    # Some schemas use 'id' as the PK name
    row = db.query_one(
        "SELECT id FROM players WHERE slug = ?",
        (slug,),
    )
    return int(row["id"]) if row else None


def _slug_to_team_id(db, slug: str) -> int | None:
    """Resolve team slug → integer team_id. Returns None on miss."""
    row = db.query_one(
        "SELECT team_id FROM teams WHERE slug = ?",
        (slug,),
    )
    if row:
        return int(row["team_id"])
    row = db.query_one(
        "SELECT id FROM teams WHERE slug = ?",
        (slug,),
    )
    return int(row["id"]) if row else None


def _make_row(
    *,
    source: str,
    kind: str,
    trust: str,
    text: str,
    payload: dict,
    entity_slug: str,
    season_year: int | None = None,
    week_number: int | None = None,
    source_id: str | None = None,
    timestamp_utc: str | None = None,
    relevance_score: float = 0.0,
) -> EvidenceRow:
    """Construct an EvidenceRow with consistent defaults."""
    return EvidenceRow(
        source=source,
        source_id=source_id,
        trust=trust,  # type: ignore[arg-type]
        kind=kind,
        payload=payload,
        text=text,
        relevance_score=relevance_score,
        season_year=season_year,
        week_number=week_number,
        entity_slug=entity_slug,
        timestamp_utc=timestamp_utc,
    )


# ---------------------------------------------------------------------------
# 1. Prediction market observations
# ---------------------------------------------------------------------------

def fetch_prediction_market_evidence(
    db,
    slug: str,
    entity_kind: str,
    season_year: int,
    week_number: int | None = None,
) -> list[EvidenceRow]:
    """Polymarket / Kalshi observations for this entity. High-trust (structured numeric).

    Reads from source_observations where source_id IN ('polymarket','kalshi').
    Matches entity via LIKE on entity_label / entity_id using the slug.

    Use cases:
    - Heisman trajectory: weekly probability shifts.
    - Flashpoint cards: pre-game vs post-game implied probability deltas.
    - Player Arc: draft stock movements.
    - Team cards: CFP / bowl win probability.

    Returns up to 20 rows, newest first.
    """
    # source_observations has no entity_slug column; match on entity_label / entity_id
    slug_pattern = f"%{slug.replace('-', ' ')}%"
    slug_dash_pattern = f"%{slug}%"
    try:
        rows = db.query_all(
            "SELECT source_observation_id, source_id, entity_type, entity_id, "
            "       entity_label, observed_at_utc, metric, value_numeric, "
            "       value_text, sample_window, capture_url, raw_payload_json "
            "FROM source_observations "
            "WHERE source_id IN ('polymarket', 'kalshi') "
            "  AND (entity_label LIKE :lbl OR entity_id LIKE :eid) "
            "ORDER BY observed_at_utc DESC LIMIT 20",
            {"lbl": slug_pattern, "eid": slug_dash_pattern},
        )
    except Exception as exc:
        log.warning("fetch_prediction_market_evidence(%s): %s", slug, exc)
        return []

    out: list[EvidenceRow] = []
    for r in rows:
        metric = str(r.get("metric") or "")
        val_num = r.get("value_numeric")
        val_text = r.get("value_text") or ""
        val_display = f"{val_num:.4f}" if val_num is not None else val_text
        label = str(r.get("entity_label") or r.get("entity_id") or slug)
        text = (
            f"{r['source_id'].capitalize()} market: {label} — "
            f"{metric} = {val_display} "
            f"(observed {str(r.get('observed_at_utc',''))[:10]})"
        )
        out.append(
            _make_row(
                source=str(r.get("source_id") or "polymarket"),
                kind="market",
                trust="high",
                text=text,
                payload=dict(r),
                entity_slug=slug,
                season_year=season_year,
                week_number=week_number,
                source_id=str(r.get("source_observation_id") or ""),
                timestamp_utc=str(r.get("observed_at_utc") or ""),
            )
        )
    return out


# ---------------------------------------------------------------------------
# 2. Statistical mirror-match comparables
# ---------------------------------------------------------------------------

def fetch_mirror_match_evidence(
    db,
    slug: str,
    entity_kind: str,
    season_year: int,
) -> list[EvidenceRow]:
    """Statistical comparables from player_mirror_matches. High-trust.

    Only meaningful for entity_kind='player'. Returns [] for teams.
    Requires compute_mirror_matches() to have run for season_year.

    Use cases:
    - Player Arc: "Only previous QB to do X" framing.
    - Devil card: comparables to players who did not break through.
    """
    if entity_kind != "player":
        return []

    player_id = _slug_to_player_id(db, slug)
    if player_id is None:
        return []

    try:
        rows = db.query_all(
            "SELECT pmm.match_slot, pmm.match_player_id, pmm.match_season_year, "
            "       pmm.similarity_pct, pmm.feature_coverage_pct, pmm.drivers_json, "
            "       p.full_name AS match_player_name "
            "FROM player_mirror_matches pmm "
            "LEFT JOIN players p ON p.player_id = pmm.match_player_id "
            "WHERE pmm.player_id = ? AND pmm.season_year = ? "
            "ORDER BY pmm.match_slot ASC LIMIT 10",
            (player_id, season_year),
        )
    except Exception as exc:
        log.warning("fetch_mirror_match_evidence(%s): %s", slug, exc)
        return []

    out: list[EvidenceRow] = []
    for r in rows:
        name = str(r.get("match_player_name") or f"Player {r['match_player_id']}")
        sim = int(r.get("similarity_pct") or 0)
        cov = int(r.get("feature_coverage_pct") or 0)
        match_season = int(r.get("match_season_year") or 0)
        try:
            drivers = json.loads(r.get("drivers_json") or "[]")
        except (TypeError, ValueError):
            drivers = []
        driver_text = "; ".join(
            f"{d['feature']} self={d['self_pct']}/match={d['match_pct']}"
            for d in drivers[:3]
        ) if drivers else ""
        text = (
            f"Statistical mirror: {name} ({match_season}) — "
            f"{sim}% similarity, {cov}% feature coverage. "
            f"Key drivers: {driver_text}"
        ).strip(". ")
        out.append(
            _make_row(
                source="cfbi_db",
                kind="biography",
                trust="high",
                text=text,
                payload={
                    **dict(r),
                    "target_player_slug": slug,
                    "target_season": season_year,
                },
                entity_slug=slug,
                season_year=season_year,
                source_id=f"mirror:{player_id}:{r['match_player_id']}:{match_season}",
                relevance_score=float(sim) / 100.0,
            )
        )
    return out


# ---------------------------------------------------------------------------
# 3. Season narrative arc
# ---------------------------------------------------------------------------

def fetch_narrative_arc_evidence(
    db,
    slug: str,
    entity_kind: str,
    season_year: int,
) -> list[EvidenceRow]:
    """Detected season arcs (underdog redemption, fall from grace, etc.).
    High-trust (our own DB derivation or hand-seeded YAML).

    For player entities: reads from bets/narrative_arc.py YAML seeds.
    For team entities: reads from team_season_arc table (if populated).

    Use cases:
    - All long-form cards: provides the framing arc.
    - Moment of the Year: identifies the arc-defining moment.
    """
    out: list[EvidenceRow] = []

    if entity_kind == "player":
        player_id = _slug_to_player_id(db, slug)
        if player_id is None:
            return []
        try:
            from cfb_rankings.bets.narrative_arc import fetch_narrative_arc
            arc = fetch_narrative_arc(player_id, season_year)
        except Exception as exc:
            log.warning("fetch_narrative_arc_evidence (player %s): %s", slug, exc)
            return []
        if not arc:
            return []
        acts = arc.get("acts") or []
        for i, act in enumerate(acts):
            text = (
                f"Season arc Act {i+1} — {act.get('title','')}: "
                f"{act.get('inflection','')} {act.get('synthesis','')} "
                f"[Weeks: {act.get('week_range','')}]"
            )
            out.append(
                _make_row(
                    source="cfbi_db",
                    kind="biography",
                    trust="high",
                    text=text.strip(),
                    payload={
                        "act_index": i,
                        "act_title": act.get("title"),
                        "week_range": act.get("week_range"),
                        "inflection": act.get("inflection"),
                        "synthesis": act.get("synthesis"),
                        "player_id": player_id,
                        "season": season_year,
                    },
                    entity_slug=slug,
                    season_year=season_year,
                    source_id=f"arc:{player_id}:{season_year}:act{i+1}",
                    # Act I is usually most scene-setting; give higher score
                    relevance_score=1.0 - (i * 0.1),
                )
            )

    elif entity_kind == "team":
        # team_season_arc table (may be empty today)
        team_id = _slug_to_team_id(db, slug)
        if team_id is None:
            return []
        try:
            rows = db.query_all(
                "SELECT season_year, wins, losses, win_pct, ap_rank_final, "
                "       sp_plus_final, cfp_flag, title_game_flag, title_won_flag, "
                "       brick_state, quality_score "
                "FROM team_season_arc "
                "WHERE team_id = ? AND season_year = ?",
                (team_id, season_year),
            )
        except Exception as exc:
            log.warning("fetch_narrative_arc_evidence (team %s): %s", slug, exc)
            return []
        for r in rows:
            w = r.get("wins") or 0
            l = r.get("losses") or 0
            cfp = bool(r.get("cfp_flag"))
            title = bool(r.get("title_won_flag"))
            text = (
                f"{slug} {season_year}: {w}-{l} record"
                + (", CFP appearance" if cfp else "")
                + (", national title" if title else "")
                + f", quality score {r.get('quality_score') or 'N/A'}"
            )
            out.append(
                _make_row(
                    source="cfbi_db",
                    kind="stat",
                    trust="high",
                    text=text,
                    payload=dict(r),
                    entity_slug=slug,
                    season_year=season_year,
                    source_id=f"team_arc:{team_id}:{season_year}",
                )
            )

    return out


# ---------------------------------------------------------------------------
# 4. Week-over-week deltas
# ---------------------------------------------------------------------------

def fetch_what_changed_evidence(
    db,
    slug: str,
    entity_kind: str,
    season_year: int,
    week_number: int,
) -> list[EvidenceRow]:
    """Week-over-week deltas for player pages.

    The what_changed.py module builds a page-state blob embedded in HTML,
    not a persistent DB table. No dedicated table exists yet (follow-up:
    P0.7 schema should add a player_page_state_history table).

    This adapter falls back to player_season_stats deltas by comparing two
    adjacent weeks of per-game stats from player_game_stats for quantitative
    delta evidence. Returns [] gracefully if data is absent.

    Use cases:
    - Flashpoint cards: post-game "this changed" moments.
    - Recruiting Pulse: portal/commit deltas.
    """
    if entity_kind != "player":
        return []
    if week_number is None or week_number < 2:
        return []

    player_id = _slug_to_player_id(db, slug)
    if player_id is None:
        return []

    out: list[EvidenceRow] = []
    try:
        # Compare this week vs prior week game-level stats
        rows = db.query_all(
            "SELECT week, category, stat_type, stat_value_num "
            "FROM player_game_stats "
            "WHERE player_id = ? AND season_year = ? "
            "  AND week IN (?, ?) "
            "  AND stat_value_num IS NOT NULL",
            (player_id, season_year, week_number - 1, week_number),
        )
    except Exception as exc:
        log.warning("fetch_what_changed_evidence(%s): %s", slug, exc)
        return []

    # Accumulate per (category, stat_type) by week
    by_week: dict[int, dict[str, float]] = {}
    for r in rows:
        wk = int(r.get("week") or 0)
        key = f"{r['category']}|{r['stat_type']}"
        by_week.setdefault(wk, {})[key] = float(r.get("stat_value_num") or 0)

    prev_week_data = by_week.get(week_number - 1, {})
    curr_week_data = by_week.get(week_number, {})

    deltas: list[dict] = []
    all_keys = set(prev_week_data) | set(curr_week_data)
    for key in all_keys:
        prev_val = prev_week_data.get(key, 0.0)
        curr_val = curr_week_data.get(key, 0.0)
        if prev_val == 0 and curr_val == 0:
            continue
        delta = curr_val - prev_val
        if abs(delta) < 0.01:
            continue
        cat, stat = key.split("|", 1)
        deltas.append({"category": cat, "stat_type": stat,
                       "prev": prev_val, "curr": curr_val, "delta": delta})

    if not deltas:
        return []

    # Sort by absolute delta descending, emit top movers as evidence rows
    deltas.sort(key=lambda d: abs(d["delta"]), reverse=True)
    for d in deltas[:5]:
        direction = "up" if d["delta"] > 0 else "down"
        text = (
            f"Week {week_number} vs Week {week_number-1}: "
            f"{d['category']} {d['stat_type']} moved {direction} by "
            f"{abs(d['delta']):.1f} (from {d['prev']:.1f} to {d['curr']:.1f})"
        )
        out.append(
            _make_row(
                source="cfbi_db",
                kind="stat",
                trust="high",
                text=text,
                payload={
                    **d,
                    "season_year": season_year,
                    "week_number": week_number,
                    "player_slug": slug,
                },
                entity_slug=slug,
                season_year=season_year,
                week_number=week_number,
                source_id=f"delta:{player_id}:{season_year}:{week_number}:{d['category']}:{d['stat_type']}",
                relevance_score=min(abs(d["delta"]) / 100.0, 1.0),
            )
        )
    return out


# ---------------------------------------------------------------------------
# 5. Anniversary "on this day" hits
# ---------------------------------------------------------------------------

def fetch_anniversary_evidence(
    db,
    slug: str,
    entity_kind: str,
    target_date_iso: str | None = None,
) -> list[EvidenceRow]:
    """'On this day' historical hits — same calendar date, prior years.

    Decade-pivot anniversaries (10 / 20 / 25 years ago) get a boosted
    relevance_score to surface them higher in the evidence pool.

    target_date_iso defaults to today UTC (YYYY-MM-DD).
    Only meaningful for entity_kind='player'; teams use team_season_arc.

    Use cases:
    - Retroactive Chronicle: anniversary content.
    - Time-collapse template: two-date callbacks (today vs prior decade).
    """
    if entity_kind != "player":
        return []

    if target_date_iso:
        try:
            today = _dt.date.fromisoformat(target_date_iso[:10])
        except ValueError:
            today = _dt.date.today()
    else:
        today = _dt.date.today()

    player_id = _slug_to_player_id(db, slug)
    if player_id is None:
        return []

    try:
        from cfb_rankings.bets.this_day import fetch_this_day_moment
        moment = fetch_this_day_moment(db, player_id, today)
    except Exception as exc:
        log.warning("fetch_anniversary_evidence(%s): %s", slug, exc)
        return []

    if moment is None:
        return []

    years_ago = moment.years_ago
    # Boost score for decade-pivot anniversaries
    if years_ago in (10, 20, 25):
        score = 0.95
    elif years_ago in (5, 15):
        score = 0.80
    else:
        score = 0.60

    text = (
        f"On This Day: {moment.headline} "
        f"({years_ago} year{'s' if years_ago != 1 else ''} ago, "
        f"{moment.date_iso}, {moment.result_label})"
    )
    return [
        _make_row(
            source="cfbi_db",
            kind="moment",
            trust="high",
            text=text,
            payload={
                "game_id": moment.game_id,
                "season": moment.season,
                "week": moment.week,
                "date_iso": moment.date_iso,
                "years_ago": years_ago,
                "opponent_short": moment.opponent_short,
                "result_label": moment.result_label,
                "headline": moment.headline,
                "target_date": today.isoformat(),
            },
            entity_slug=slug,
            season_year=moment.season,
            week_number=moment.week,
            source_id=f"this_day:{player_id}:{moment.game_id}",
            relevance_score=score,
        )
    ]


# ---------------------------------------------------------------------------
# 6. Era-relative comparisons
# ---------------------------------------------------------------------------

def fetch_era_context_evidence(
    db,
    slug: str,
    entity_kind: str,
    season_year: int,
) -> list[EvidenceRow]:
    """Era-relative comparisons using compute_era_context() for each headline metric.

    Queries the player's signature-story headline metric if available,
    falls back to scanning the top 3 stats by value. Returns [] for team
    entities (era context is player-centric in the current implementation).

    High-trust (our own DB derivation).

    Use cases:
    - Player Arc: framing within era cohort ("Best since BCS era").
    - Statement Wins: era-relativized significance.
    """
    if entity_kind != "player":
        return []

    player_id = _slug_to_player_id(db, slug)
    if player_id is None:
        return []

    # Resolve position first
    try:
        pos_row = db.query_one(
            "SELECT position FROM players WHERE player_id = ?",
            (player_id,),
        )
    except Exception:
        pos_row = None
    position = str((pos_row or {}).get("position") or "").strip().upper()

    # Metric priority: signature story metric → top-N by value
    metrics_to_try: list[tuple[str, float | None]] = []
    try:
        from cfb_rankings.bets.signature_play import _fetch_signature_metric_id
        metric_id = _fetch_signature_metric_id(db, player_id, season_year)
        if metric_id:
            # Fetch the player's value for that metric
            from cfb_rankings.bets.era_context import _METRIC_STAT_MAP
            meta = _METRIC_STAT_MAP.get(metric_id)
            if meta:
                cat, stat_type, _ = meta
                stat_row = db.query_one(
                    "SELECT stat_value_num FROM player_season_stats "
                    "WHERE player_id = ? AND season_year = ? "
                    "  AND category = ? AND stat_type = ?",
                    (player_id, season_year, cat, stat_type),
                )
                val = float(stat_row["stat_value_num"]) if stat_row and stat_row.get("stat_value_num") is not None else None
                metrics_to_try.append((metric_id, val))
    except Exception:
        pass

    if not metrics_to_try:
        # Fallback: try top passing/rushing/receiving yard metrics
        for mid in ("passing_yards_total", "rushing_yards_total", "receiving_yards_total"):
            try:
                from cfb_rankings.bets.era_context import _METRIC_STAT_MAP
                meta = _METRIC_STAT_MAP.get(mid)
                if not meta:
                    continue
                cat, stat_type, _ = meta
                stat_row = db.query_one(
                    "SELECT stat_value_num FROM player_season_stats "
                    "WHERE player_id = ? AND season_year = ? "
                    "  AND category = ? AND stat_type = ?",
                    (player_id, season_year, cat, stat_type),
                )
                if stat_row and stat_row.get("stat_value_num") is not None:
                    metrics_to_try.append((mid, float(stat_row["stat_value_num"])))
                    break
            except Exception:
                continue

    out: list[EvidenceRow] = []
    try:
        from cfb_rankings.bets.era_context import compute_era_context
        for metric_id, value in metrics_to_try[:2]:
            if value is None:
                continue
            ctx = compute_era_context(
                db,
                player_id=player_id,
                metric_id=metric_id,
                season=season_year,
                value=value,
                position=position,
            )
            if not ctx.get("applicable"):
                continue
            text = str(ctx.get("text") or "")
            if not text:
                continue
            target_ref = ctx.get("target_ref") or {}
            out.append(
                _make_row(
                    source="cfbi_db",
                    kind="stat",
                    trust="high",
                    text=text,
                    payload={
                        "metric_id": metric_id,
                        "player_value": value,
                        "era_context": ctx,
                        "position": position,
                    },
                    entity_slug=slug,
                    season_year=season_year,
                    source_id=f"era:{player_id}:{season_year}:{metric_id}",
                    relevance_score=0.85 if target_ref.get("rank_in_cohort") == 1 else 0.65,
                )
            )
    except Exception as exc:
        log.warning("fetch_era_context_evidence(%s): %s", slug, exc)

    return out


# ---------------------------------------------------------------------------
# 7. Signature plays
# ---------------------------------------------------------------------------

def fetch_signature_play_evidence(
    db,
    slug: str,
    entity_kind: str,
    season_year: int,
) -> list[EvidenceRow]:
    """One-off heroic or catastrophic plays curated in player_signature_plays.
    High-trust (276 rows in DB as of 2026-05-23).

    Use cases:
    - Flashpoint: the play that defined the game.
    - Moment of the Year: top candidate moments.
    """
    if entity_kind != "player":
        return []

    player_id = _slug_to_player_id(db, slug)
    if player_id is None:
        return []

    try:
        rows = db.query_all(
            "SELECT player_id, season_year, game_id, week, metric_id, "
            "       stat_value, score, opponent_name, home_away, "
            "       result_label, gloss "
            "FROM player_signature_plays "
            "WHERE player_id = ? AND season_year = ?",
            (player_id, season_year),
        )
    except Exception as exc:
        log.warning("fetch_signature_play_evidence(%s): %s", slug, exc)
        return []

    out: list[EvidenceRow] = []
    for r in rows:
        gloss = str(r.get("gloss") or "")
        metric_id = str(r.get("metric_id") or "")
        stat_val = float(r.get("stat_value") or 0)
        opp = str(r.get("opponent_name") or "opponent")
        result = str(r.get("result_label") or "—")
        wk = int(r.get("week") or 0)
        ha = str(r.get("home_away") or "")
        text = (
            gloss
            or f"Week {wk} {ha} vs {opp} ({result}): "
               f"{metric_id} = {stat_val:.0f}"
        )
        out.append(
            _make_row(
                source="cfbi_db",
                kind="moment",
                trust="high",
                text=text,
                payload=dict(r),
                entity_slug=slug,
                season_year=season_year,
                week_number=wk or None,
                source_id=f"sigplay:{player_id}:{season_year}",
                relevance_score=min(float(r.get("score") or 0) / 500.0, 1.0),
            )
        )
    return out


# ---------------------------------------------------------------------------
# 8. Team voice — NOT an EvidenceRow returner
# ---------------------------------------------------------------------------

def fetch_team_voice(db, team_slug: str) -> dict | None:
    """Return the parsed voice JSON dict for a team, or None.

    NOT an EvidenceRow returner — intended for prompt-time style injection.

    Returns a dict with keys:
        mascot_voice_templates: list[str]   — phrases the mascot/fan voice uses
        never_use_phrases: list[str]         — globally banned phrases for this team
        always_surface_phrases: list[str]    — slogans / battle cries to include
        vocab: dict                          — vocab substitutions (e.g. "quad" → "The Quad")
        tonal_template: str | None           — short voice register description
        primary_color: str | None            — hex accent color
        secondary_color: str | None          — hex secondary color

    Returns None if the team has no voice config, or if the team_voice table
    is missing or empty (currently 0 rows in prod — profiles need to be
    ingested via `manage.py load-profiles`).
    """
    team_id = _slug_to_team_id(db, team_slug)
    if team_id is None:
        return None

    try:
        row = db.query_one(
            "SELECT accent_hex, accent_hex_secondary, "
            "       mascot_voice_templates_json, never_use_phrases_json, "
            "       always_surface_phrases_json, vocab_dict_json, tonal_template "
            "FROM team_voice WHERE team_id = ?",
            (team_id,),
        )
    except Exception as exc:
        log.warning("fetch_team_voice(%s): %s", team_slug, exc)
        return None

    if not row:
        return None

    def _parse_json_list(text: str | None, default: list) -> list:
        if not text:
            return default
        try:
            val = json.loads(text)
            return val if isinstance(val, list) else default
        except (TypeError, ValueError):
            return default

    def _parse_json_dict(text: str | None, default: dict) -> dict:
        if not text:
            return default
        try:
            val = json.loads(text)
            return val if isinstance(val, dict) else default
        except (TypeError, ValueError):
            return default

    return {
        "mascot_voice_templates": _parse_json_list(
            row.get("mascot_voice_templates_json"), []
        ),
        "never_use_phrases": _parse_json_list(
            row.get("never_use_phrases_json"), []
        ),
        "always_surface_phrases": _parse_json_list(
            row.get("always_surface_phrases_json"), []
        ),
        "vocab": _parse_json_dict(
            row.get("vocab_dict_json"), {}
        ),
        "tonal_template": row.get("tonal_template"),
        "primary_color": row.get("accent_hex"),
        "secondary_color": row.get("accent_hex_secondary"),
    }


# ---------------------------------------------------------------------------
# 9. Conversation documents (Reddit / forum)
# ---------------------------------------------------------------------------

def fetch_conversation_evidence(
    db,
    slug: str,
    entity_kind: str,
    season_year: int,
    week_number: int | None = None,
    k: int = 5,
) -> list[EvidenceRow]:
    """Reddit / forum quotes — LOW TRUST.

    Returns EvidenceRow with trust='low' so source_trust mode='color'
    includes them but mode='fact' excludes them.

    Matches conversation_documents against slug via LIKE on body_text /
    title_text (no entity_slug column in this table). Ordered by
    like_count DESC then collected_at_utc DESC as a relevance proxy.

    Use cases:
    - Moment of the Year: authentic fan quotes.
    - Echo Card: community sentiment color.
    - Devil Card: dissent from the fanbase.

    Each EvidenceRow payload includes author_identity_class and
    demographic_slice for demographic-aware framing.
    """
    slug_display = slug.replace("-", " ")
    pattern = f"%{slug_display}%"
    # Tight entity matching to prevent topical drift:
    #   1. Slug appears in title_text (strongest signal — article IS about team)
    #   2. OR body_text mentions slug 2+ times (consistent topical focus)
    # Plain body_text LIKE was too permissive (Cincinnati card returned generic
    # OSU/Big Ten substack content because it mentioned "Cincinnati" once).
    try:
        rows = db.query_all(
            "SELECT conversation_document_id, source_name, source_author_name, "
            "       source_channel, title_text, body_text, "
            "       external_created_at_utc, like_count, reply_count, "
            "       author_identity_class, demographic_slice, source_url "
            "FROM conversation_documents "
            "WHERE is_deleted = 0 AND is_removed = 0 "
            "  AND (title_text LIKE :p "
            "       OR (LENGTH(body_text) - LENGTH(REPLACE(LOWER(body_text), :raw_slug, ''))) "
            "          / LENGTH(:raw_slug) >= 2) "
            "ORDER BY (CASE WHEN title_text LIKE :p THEN 0 ELSE 1 END), "
            "         COALESCE(like_count, 0) DESC, "
            "         external_created_at_utc DESC "
            "LIMIT :k",
            {"p": pattern, "raw_slug": slug_display.lower(), "k": int(k)},
        )
    except Exception as exc:
        log.warning("fetch_conversation_evidence(%s): %s", slug, exc)
        return []

    out: list[EvidenceRow] = []
    for r in rows:
        title = str(r.get("title_text") or "")
        body = str(r.get("body_text") or "")
        # Truncate body for text representation
        body_short = body[:300] + "..." if len(body) > 300 else body
        author = str(r.get("source_author_name") or "anon")
        identity = str(r.get("author_identity_class") or "")
        demo = str(r.get("demographic_slice") or "")
        likes = int(r.get("like_count") or 0)
        channel = str(r.get("source_channel") or r.get("source_name") or "reddit")
        ts = str(r.get("external_created_at_utc") or "")
        text = f"[{channel}] {author} ({identity}/{demo}): {title or body_short}"
        out.append(
            _make_row(
                source=str(r.get("source_name") or "reddit"),
                kind="quote",
                trust="low",
                text=text,
                payload={
                    **dict(r),
                    "body_text": body_short,  # truncated for payload
                },
                entity_slug=slug,
                season_year=season_year,
                week_number=week_number,
                source_id=str(r.get("conversation_document_id") or ""),
                timestamp_utc=ts,
                # Scale by like_count as a rough engagement proxy (cap at 1.0)
                relevance_score=min(likes / 100.0, 1.0),
            )
        )
    return out


# ---------------------------------------------------------------------------
# 10. Editorial citations
# ---------------------------------------------------------------------------

def fetch_editorial_citations(
    db,
    slug: str,
    entity_kind: str,
    season_year: int,
    k: int = 10,
) -> list[EvidenceRow]:
    """Pre-validated quote/citation pairs from editorial_citations.
    High-trust (already vetted by citation_critic at ingest).

    The editorial_citations table is keyed on (generation_id, marker_id)
    and does NOT have an entity_slug column — citations are associated with
    LLM generation runs, not directly with players/teams.

    This adapter:
    1. Attempts FTS5 full-text search on a slug-derived query string.
    2. Falls back to a LIKE scan on source_label column.
    3. As a final fallback, returns the k most recent citations regardless
       of entity (useful when the table is sparsely populated).

    Use cases:
    - All cards: receipts for claims.
    - Voice anchor: known-good quotes shape the voice register.
    """
    slug_display = slug.replace("-", " ")

    # Try FTS5 first
    try:
        rows = db.query_all(
            "SELECT ec.citation_id, ec.generation_id, ec.marker_id, "
            "       ec.source_kind, ec.source_url, ec.source_label, "
            "       ec.source_date, ec.confidence, ec.created_at_utc "
            "FROM editorial_citations ec "
            "JOIN editorial_citations_fts fts ON fts.rowid = ec.rowid "
            "WHERE editorial_citations_fts MATCH ? "
            "LIMIT ?",
            (slug_display, k),
        )
        if rows:
            return _citations_to_evidence(rows, slug, season_year)
    except Exception:
        pass  # FTS5 not available or no results

    # LIKE fallback on source_label
    try:
        rows = db.query_all(
            "SELECT citation_id, generation_id, marker_id, source_kind, "
            "       source_url, source_label, source_date, confidence, "
            "       created_at_utc "
            "FROM editorial_citations "
            "WHERE source_label LIKE ? "
            "ORDER BY created_at_utc DESC LIMIT ?",
            (f"%{slug_display}%", k),
        )
        if rows:
            return _citations_to_evidence(rows, slug, season_year)
    except Exception as exc:
        log.debug("fetch_editorial_citations LIKE fallback (%s): %s", slug, exc)

    # Final fallback: newest k citations regardless of entity
    try:
        rows = db.query_all(
            "SELECT citation_id, generation_id, marker_id, source_kind, "
            "       source_url, source_label, source_date, confidence, "
            "       created_at_utc "
            "FROM editorial_citations "
            "ORDER BY created_at_utc DESC LIMIT ?",
            (k,),
        )
        return _citations_to_evidence(rows, slug, season_year)
    except Exception as exc:
        log.warning("fetch_editorial_citations(%s): %s", slug, exc)
        return []


def _citations_to_evidence(
    rows: list[dict],
    entity_slug: str,
    season_year: int,
) -> list[EvidenceRow]:
    """Convert raw editorial_citations rows to EvidenceRow objects."""
    out: list[EvidenceRow] = []
    confidence_score = {"primary": 1.0, "supporting": 0.75, "background": 0.5}
    for r in rows:
        label = str(r.get("source_label") or "")
        kind = str(r.get("source_kind") or "")
        conf = str(r.get("confidence") or "background")
        url = str(r.get("source_url") or "")
        date = str(r.get("source_date") or "")
        marker = r.get("marker_id")
        text = f"[{kind}] {label}{' (' + date + ')' if date else ''}{' — ' + url if url else ''}"
        out.append(
            _make_row(
                source="cfbi_db",
                kind="quote",
                trust="high",
                text=text,
                payload=dict(r),
                entity_slug=entity_slug,
                season_year=season_year,
                source_id=str(r.get("citation_id") or ""),
                timestamp_utc=str(r.get("created_at_utc") or ""),
                relevance_score=confidence_score.get(conf, 0.5),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Routing table: card_type → ordered list of source-function names
# ---------------------------------------------------------------------------

def fetch_team_game_evidence(
    db,
    slug: str,
    entity_kind: str,
    season_year: int,
) -> list[EvidenceRow]:
    """Game-result evidence from the ``games`` table.

    Constructs factual season-context rows (recent W/L, final record,
    notable wins/losses) for the target FBS team. Works for any team with
    games data — provides the minimum evidence floor for ``echo`` and
    ``retroactive`` cards when Polymarket / conversation data is absent.

    Trust: ``high`` (derived from our own schedule/scores DB).
    """
    if entity_kind != "team":
        return []

    team_id = _slug_to_team_id(db, slug)
    if team_id is None:
        return []

    out: list[EvidenceRow] = []
    try:
        rows = db.query_all(
            """
            SELECT g.game_id, g.season_year, g.week, g.status,
                   g.home_team_id, g.away_team_id,
                   g.home_points, g.away_points,
                   ht.canonical_name AS home_name,
                   at.canonical_name AS away_name
            FROM games g
            JOIN teams ht ON g.home_team_id = ht.team_id
            JOIN teams at ON g.away_team_id = at.team_id
            WHERE (g.home_team_id = :tid OR g.away_team_id = :tid)
              AND g.season_year = :yr
              AND LOWER(g.status) IN ('final', 'completed', 'post', 'final-ot')
            ORDER BY g.week DESC
            LIMIT 12
            """,
            {"tid": team_id, "yr": season_year},
        )
    except Exception as exc:
        log.warning("fetch_team_game_evidence (team %s %s): %s", slug, season_year, exc)
        return []

    wins = losses = 0
    def _get(row, key, default=None):
        """Safe getter for both sqlite3.Row and dict-like rows."""
        try:
            v = row[key]
            return v if v is not None else default
        except (KeyError, IndexError):
            return default

    for r in rows:
        is_home = (_get(r, "home_team_id") == team_id)
        team_pts = _get(r, "home_points") if is_home else _get(r, "away_points")
        opp_pts = _get(r, "away_points") if is_home else _get(r, "home_points")
        opp_name = _get(r, "away_name") if is_home else _get(r, "home_name")
        ha = "vs" if is_home else "at"
        week = _get(r, "week")
        game_id = _get(r, "game_id")

        if team_pts is not None and opp_pts is not None:
            outcome = "W" if team_pts > opp_pts else "L"
            if outcome == "W":
                wins += 1
            else:
                losses += 1
            text = (
                f"{slug} {outcome} {team_pts}-{opp_pts} {ha} {opp_name} "
                f"(Week {week} {season_year})"
            )
        else:
            text = f"{slug} played {ha} {opp_name} Week {week} {season_year}"
            outcome = "?"

        out.append(
            _make_row(
                source="cfbi_db",
                kind="stat",
                trust="high",
                text=text,
                payload={
                    "game_id": game_id,
                    "week": week,
                    "season_year": season_year,
                    "outcome": outcome,
                    "team_points": team_pts,
                    "opp_points": opp_pts,
                    "opponent": opp_name,
                    "is_home": is_home,
                },
                entity_slug=slug,
                season_year=season_year,
                source_id=f"game:{game_id}",
                relevance_score=0.75,
            )
        )

    # Summary row gives the LLM a quick season overview
    if wins + losses > 0:
        out.append(
            _make_row(
                source="cfbi_db",
                kind="stat",
                trust="high",
                text=f"{slug} {season_year} record: {wins}-{losses} through week 14",
                payload={"wins": wins, "losses": losses, "season_year": season_year},
                entity_slug=slug,
                season_year=season_year,
                source_id=f"record:{slug}:{season_year}",
                relevance_score=0.9,
            )
        )

    return out


EVIDENCE_SOURCE_ROUTING: dict[str, list[str]] = {
    "flashpoint": [
        "fetch_signature_play_evidence",
        "fetch_what_changed_evidence",
        "fetch_prediction_market_evidence",
        "fetch_editorial_citations",
        "fetch_team_game_evidence",     # game-result floor for all FBS teams
    ],
    "player_arc": [
        "fetch_mirror_match_evidence",
        "fetch_era_context_evidence",
        "fetch_narrative_arc_evidence",
        "fetch_prediction_market_evidence",
        "fetch_editorial_citations",
    ],
    "echo": [
        "fetch_conversation_evidence",
        "fetch_what_changed_evidence",
        "fetch_editorial_citations",
        "fetch_team_game_evidence",     # game-result floor for all FBS teams
    ],
    "retroactive": [
        "fetch_anniversary_evidence",
        "fetch_era_context_evidence",
        "fetch_signature_play_evidence",
        "fetch_team_game_evidence",     # game-result floor for all FBS teams
    ],
    "heisman_trajectory": [
        "fetch_prediction_market_evidence",
        "fetch_mirror_match_evidence",
        "fetch_narrative_arc_evidence",
    ],
    "moment_of_year": [
        "fetch_signature_play_evidence",
        "fetch_narrative_arc_evidence",
        "fetch_conversation_evidence",
        "fetch_editorial_citations",
    ],
    "devil_card": [
        "fetch_mirror_match_evidence",      # comparables who didn't break through
        "fetch_what_changed_evidence",       # what got worse
        "fetch_conversation_evidence",       # dissent
    ],
    "rivalry_lens": [
        "fetch_anniversary_evidence",
        "fetch_signature_play_evidence",
        "fetch_era_context_evidence",
        "fetch_editorial_citations",
    ],
    "matchup_echo": [
        "fetch_mirror_match_evidence",
        "fetch_era_context_evidence",
        "fetch_signature_play_evidence",
        "fetch_prediction_market_evidence",
    ],
    "consensus_vs_metric": [
        "fetch_prediction_market_evidence",  # market consensus
        "fetch_mirror_match_evidence",        # statistical comparable
        "fetch_what_changed_evidence",
    ],
}

# Map function-name strings to callables — built at module load time so
# fetch_evidence_for_card() can dispatch without getattr() overhead.
_FETCHERS: dict[str, object] = {
    "fetch_prediction_market_evidence": fetch_prediction_market_evidence,
    "fetch_mirror_match_evidence": fetch_mirror_match_evidence,
    "fetch_narrative_arc_evidence": fetch_narrative_arc_evidence,
    "fetch_what_changed_evidence": fetch_what_changed_evidence,
    "fetch_anniversary_evidence": fetch_anniversary_evidence,
    "fetch_era_context_evidence": fetch_era_context_evidence,
    "fetch_signature_play_evidence": fetch_signature_play_evidence,
    "fetch_conversation_evidence": fetch_conversation_evidence,
    "fetch_editorial_citations": fetch_editorial_citations,
    "fetch_team_game_evidence": fetch_team_game_evidence,
}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def fetch_evidence_for_card(
    db,
    card_type: str,
    slug: str,
    entity_kind: str,
    season_year: int,
    week_number: int | None = None,
) -> list[EvidenceRow]:
    """Orchestrator. Looks up card_type in EVIDENCE_SOURCE_ROUTING, calls
    each function in order, and concatenates results.

    Each fetcher is wrapped in try/except — a single source failure does NOT
    break the whole evidence pool. Failures are logged at WARNING level and
    swallowed, so the pipeline continues with the remaining sources.

    Note: this returns a combined un-trust-filtered list. Trust filtering and
    RRF fusion happen in retriever.py after this call.

    Returns [] for unknown card_type values.
    """
    source_names = EVIDENCE_SOURCE_ROUTING.get(card_type)
    if not source_names:
        if card_type:
            log.debug(
                "fetch_evidence_for_card: unknown card_type=%r — returning []", card_type
            )
        return []

    combined: list[EvidenceRow] = []
    for name in source_names:
        fetcher = _FETCHERS.get(name)
        if fetcher is None:
            log.warning("fetch_evidence_for_card: no fetcher registered for %r", name)
            continue
        try:
            if name == "fetch_what_changed_evidence":
                # fetch_what_changed requires week_number; skip if absent
                if week_number is None:
                    continue
                rows = fetcher(db, slug, entity_kind, season_year, week_number)  # type: ignore[call-arg]
            elif name == "fetch_anniversary_evidence":
                rows = fetcher(db, slug, entity_kind)  # type: ignore[call-arg]
            else:
                # All other fetchers accept (db, slug, entity_kind, season_year)
                # with optional week_number as keyword where applicable
                import inspect
                sig = inspect.signature(fetcher)  # type: ignore[arg-type]
                params = list(sig.parameters)
                if "week_number" in params:
                    rows = fetcher(db, slug, entity_kind, season_year, week_number)  # type: ignore[call-arg]
                else:
                    rows = fetcher(db, slug, entity_kind, season_year)  # type: ignore[call-arg]
            combined.extend(rows)
        except Exception as exc:
            log.warning(
                "fetch_evidence_for_card: fetcher %r raised for slug=%r card=%r: %s",
                name, slug, card_type, exc,
            )
            # Swallow — do not propagate; other sources may still succeed

    return combined
