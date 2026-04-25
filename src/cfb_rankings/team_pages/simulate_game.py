"""Offseason rehearsal harness — Sprint 6 §4.

Drives a full end-to-end gameday-mode simulation against a mock fixture.
Inserts a games_live row, flips state_resolver, generates the post-game
narrative + diagnosis stats + Chronicle game-edition cards, re-renders
both teams' pages, and prints a structured report.

Public entry point: :func:`run_simulation`. Called from
``manage.py simulate-game``. Designed to be runnable offline without the
LLM (template mode) so we can rehearse all 5 outcome categories before
Week 1 of the 2026 season.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from .chronicle_game_edition import generate_game_edition_cards
from .data import fetch_team_snapshot
from .game_recap_hero import build_diagnosis_stats
from .narrative_generator import generate_state_of_team_post_game
from .profile_loader import load_profile
from .renderer import render_team_page
from .state_resolver import resolve_state


# --------------------------------------------------------------------------
# Result type — printed by the rehearsal report formatter
# --------------------------------------------------------------------------

@dataclass
class SimulationReport:
    home_slug: str
    away_slug: str
    final_home: int
    final_away: int
    fixture_path: str | None
    home_state: dict[str, Any] = field(default_factory=dict)
    away_state: dict[str, Any] = field(default_factory=dict)
    home_narrative: dict[str, Any] = field(default_factory=dict)
    away_narrative: dict[str, Any] = field(default_factory=dict)
    home_diagnosis: list[dict[str, Any]] = field(default_factory=list)
    away_diagnosis: list[dict[str, Any]] = field(default_factory=list)
    home_chronicle: list[dict[str, Any]] = field(default_factory=list)
    away_chronicle: list[dict[str, Any]] = field(default_factory=list)
    home_html_path: str | None = None
    away_html_path: str | None = None
    duration_seconds: float = 0.0
    token_usage: dict[str, int] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Public entry — called by manage.py simulate-game
# --------------------------------------------------------------------------

def run_simulation(
    *,
    db,
    home_slug: str,
    away_slug: str,
    final_home: int,
    final_away: int,
    wp_curve_path: str | None = None,
    events_log_path: str | None = None,
    persist: bool = False,
    output_dir: str = "output/site/teams",
    pre_game_spread_home: float | None = None,
    fixture_path: str | None = None,
    chronicle_mode: str = "template",
    narrative_mode: str = "template",
    season_year: int | None = None,
    week: int | None = None,
) -> str:
    """Run a single simulated game end-to-end. Returns a printable report.

    The default modes use 'template' for both narrative and chronicle so
    the harness runs with zero LLM cost. Pass ``chronicle_mode='auto'``
    or ``narrative_mode='claude-code'`` to engage Opus/Sonnet for
    voice-quality validation.
    """
    started = datetime.now(timezone.utc)

    # Load fixture if provided.
    fixture: dict[str, Any] = {}
    if fixture_path:
        fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
        # Fixture overrides scalar args when set explicitly.
        final_home = int(fixture.get("final_home", final_home))
        final_away = int(fixture.get("final_away", final_away))
        if "pre_game_spread_home" in fixture:
            pre_game_spread_home = float(fixture["pre_game_spread_home"])
    wp_ts = fixture.get("wp_timeseries")
    if wp_ts is None and wp_curve_path:
        wp_ts = json.loads(Path(wp_curve_path).read_text(encoding="utf-8"))
    events_log = fixture.get("events_log")
    if events_log is None and events_log_path:
        events_log = json.loads(Path(events_log_path).read_text(encoding="utf-8"))
    diag_seeds = fixture.get("diagnosis_stats")  # both teams or split dict
    game_edition_seeds = fixture.get("game_edition_seeds") or {}

    # Insert / upsert mock games_live row. final_at = now − 2h so freshness
    # window is comfortably inside 24h.
    final_dt = (started - timedelta(hours=2)).isoformat()
    kickoff_dt = (started - timedelta(hours=5)).isoformat()
    season_year = season_year or _infer_season_year(db)
    week = week or fixture.get("week") or 14

    home_team_id = _team_id(db, home_slug)
    away_team_id = _team_id(db, away_slug)
    db.execute(
        """
        insert into games_live (
            season_year, week,
            home_team_id, away_team_id,
            home_team_slug, away_team_slug,
            kickoff_at_utc, status, home_score, away_score,
            final_at_utc, pre_game_spread_home,
            wp_timeseries_json, events_log_json,
            simulated, updated_at_utc
        ) values (
            :s, :w,
            :hid, :aid,
            :hslug, :aslug,
            :kick, 'final', :hs, :as_,
            :final, :spread,
            :wp, :evt,
            1, current_timestamp
        )
        on conflict(season_year, week, home_team_slug, away_team_slug) do update set
            home_score = excluded.home_score,
            away_score = excluded.away_score,
            status = 'final',
            final_at_utc = excluded.final_at_utc,
            pre_game_spread_home = excluded.pre_game_spread_home,
            wp_timeseries_json = excluded.wp_timeseries_json,
            events_log_json = excluded.events_log_json,
            simulated = 1,
            updated_at_utc = current_timestamp
        """,
        {
            "s": season_year, "w": week,
            "hid": home_team_id, "aid": away_team_id,
            "hslug": home_slug, "aslug": away_slug,
            "kick": kickoff_dt, "hs": final_home, "as_": final_away,
            "final": final_dt, "spread": pre_game_spread_home,
            "wp": json.dumps(wp_ts) if wp_ts else None,
            "evt": json.dumps(events_log) if events_log else None,
        },
    )

    # Build the live_meta dict for both teams.
    base_meta = {
        "game_id": None,
        "season_year": season_year,
        "week": week,
        "home_team_slug": home_slug,
        "away_team_slug": away_slug,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "kickoff_at_utc": kickoff_dt,
        "status": "final",
        "home_score": final_home,
        "away_score": final_away,
        "final_at_utc": final_dt,
        "pre_game_spread_home": pre_game_spread_home,
        "wp_timeseries_json": json.dumps(wp_ts) if wp_ts else None,
        "events_log_json": json.dumps(events_log) if events_log else None,
        "simulated": 1,
        "game_edition_seeds": game_edition_seeds,
    }
    home_meta = dict(base_meta)
    away_meta = dict(base_meta)

    if isinstance(diag_seeds, dict):
        home_meta["diagnosis_stats"] = diag_seeds.get("home")
        away_meta["diagnosis_stats"] = diag_seeds.get("away")
    elif isinstance(diag_seeds, list):
        # Same diagnosis for both — useful for rehearsal symmetry.
        home_meta["diagnosis_stats"] = diag_seeds
        away_meta["diagnosis_stats"] = diag_seeds

    # ---- Per-team pipeline ----
    report = SimulationReport(
        home_slug=home_slug, away_slug=away_slug,
        final_home=final_home, final_away=final_away,
        fixture_path=fixture_path,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for slug, meta, label in [
        (home_slug, home_meta, "home"),
        (away_slug, away_meta, "away"),
    ]:
        try:
            profile = load_profile(slug)
        except FileNotFoundError:
            print(f"  simulate-game: {slug} not in profiles/ — skipping {label} team")
            continue

        snapshot = fetch_team_snapshot(db, slug, season_year)
        state = resolve_state(profile, snapshot, live_game_meta=meta)

        # Narrative
        narr = generate_state_of_team_post_game(
            profile, snapshot, state,
            final_meta=meta, mode=narrative_mode,
        )

        # Diagnosis stats
        diag = build_diagnosis_stats(mock=meta.get("diagnosis_stats"))

        # Chronicle game-edition cards
        try:
            cards = generate_game_edition_cards(
                db, profile, snapshot,
                final_meta=meta, season_year=season_year, week=week,
                mode=chronicle_mode, include_divergence_card=True,
                log=lambda _msg: None,  # quiet during simulation
            )
        except Exception as exc:
            print(f"  simulate-game: chronicle failed for {slug} — {exc}")
            cards = []

        # Render the team page (via the standard renderer which now reads
        # games_live and resolves into game-recap mode).
        try:
            html_path = render_team_page(
                db, slug, output_dir,
                today=None, season_year=season_year,
            )
        except Exception as exc:
            print(f"  simulate-game: render failed for {slug} — {exc}")
            html_path = None

        # Stash on the report.
        state_dict = state.as_dict()
        narr_dict = {
            "body_md": narr.body_md,
            "model_id": narr.model_id,
            "word_count": len(narr.body_md.split()),
            "prompt_tokens": narr.prompt_tokens,
            "completion_tokens": narr.completion_tokens,
        }
        diag_list = list(diag)
        cards_list = [{
            "card_type": c.card_type,
            "headline": c.headline,
            "body_md": c.body_md,
            "source_attribution": c.source_attribution,
            "model_id": c.model_id,
            "validation_notes": c.validation_notes,
        } for c in cards]

        if label == "home":
            report.home_state = state_dict
            report.home_narrative = narr_dict
            report.home_diagnosis = diag_list
            report.home_chronicle = cards_list
            report.home_html_path = str(html_path) if html_path else None
        else:
            report.away_state = state_dict
            report.away_narrative = narr_dict
            report.away_diagnosis = diag_list
            report.away_chronicle = cards_list
            report.away_html_path = str(html_path) if html_path else None

        # Aggregate tokens
        report.token_usage["prompt_tokens"] = (
            report.token_usage.get("prompt_tokens", 0) + (narr.prompt_tokens or 0)
        )
        report.token_usage["completion_tokens"] = (
            report.token_usage.get("completion_tokens", 0) + (narr.completion_tokens or 0)
        )

    if not persist:
        # Default: leave the row but mark for cleanup.
        try:
            db.execute(
                """
                delete from games_live
                where season_year = :s and week = :w
                  and home_team_slug = :h and away_team_slug = :a
                  and simulated = 1
                """,
                {"s": season_year, "w": week, "h": home_slug, "a": away_slug},
            )
        except Exception:
            pass

    report.duration_seconds = (datetime.now(timezone.utc) - started).total_seconds()
    return format_report(report)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _team_id(db, slug: str) -> int | None:
    row = db.query_one("select team_id from teams where slug = :s", {"s": slug})
    return int(row["team_id"]) if row else None


def _infer_season_year(db) -> int:
    row = db.query_one("select max(season_year) as y from games where status in ('Final','final')")
    if row and row["y"]:
        return int(row["y"])
    return datetime.now(timezone.utc).year


# --------------------------------------------------------------------------
# Rehearsal report formatter (Sprint 6 §4.3)
# --------------------------------------------------------------------------

def format_report(r: SimulationReport) -> str:
    lines: list[str] = []
    lines.append(f"\n=== SIMULATION REHEARSAL REPORT ===")
    lines.append(f"  fixture           : {r.fixture_path or '(scalar args)'}")
    lines.append(f"  matchup           : {r.home_slug} (home) vs {r.away_slug} (away)")
    lines.append(f"  final score       : {r.final_home}-{r.final_away}")
    lines.append(f"  duration (sec)    : {r.duration_seconds:.2f}")
    lines.append(f"  tokens (prompt/c) : {r.token_usage.get('prompt_tokens', 0)} / {r.token_usage.get('completion_tokens', 0)}")
    lines.append("")
    for label, slug, state, narr, diag, chron, html_path in [
        ("HOME", r.home_slug, r.home_state, r.home_narrative, r.home_diagnosis, r.home_chronicle, r.home_html_path),
        ("AWAY", r.away_slug, r.away_state, r.away_narrative, r.away_diagnosis, r.away_chronicle, r.away_html_path),
    ]:
        if not state:
            continue
        lines.append(f"--- {label}: {slug} ---")
        lines.append(f"  state.outcome_category : {state.get('outcome_category')}")
        lines.append(f"  state.anchor_variant   : {state.get('anchor_variant')}")
        lines.append(f"  state.copy_tone        : {state.get('copy_tone')}")
        lines.append(f"  state.accent_key       : {state.get('accent_key')}")
        lines.append(f"  state.game_recap_active: {state.get('game_recap_active')}")
        lines.append(f"  state.pre_game_spread  : {state.get('pre_game_spread')}")
        lines.append(f"  narrative              : {narr.get('word_count')} words via {narr.get('model_id')}")
        lines.append(f"    body: {narr.get('body_md', '')[:200]}{'…' if len(narr.get('body_md','')) > 200 else ''}")
        if diag:
            lines.append(f"  diagnosis stats        : {len(diag)} stat(s)")
            for d in diag:
                lines.append(f"    - {d.get('label'):<24} {str(d.get('value')):<12} band={d.get('band'):<10} | {d.get('caption','')}")
        if chron:
            lines.append(f"  chronicle (game ed.)   : {len(chron)} card(s)")
            for c in chron:
                lines.append(f"    [{c.get('card_type'):<11}] {c.get('headline')}")
                body_preview = (c.get('body_md') or '')[:160]
                lines.append(f"      body: {body_preview}{'…' if len(c.get('body_md','')) > 160 else ''}")
                lines.append(f"      attr: {c.get('source_attribution')}  · model={c.get('model_id')}")
        if html_path:
            lines.append(f"  html written           : {html_path}")
        lines.append("")
    lines.append("=== END REPORT ===\n")
    return "\n".join(lines)
