"""Top-level team-page renderer.

Composes the hero + Pulse + Chronicle + state-of-team paragraph into a
single HTML document and writes it to ``output/site/teams/<slug>.html``.

Judgment call: rather than adding a Jinja2 dependency (not present in the
project's vendor tree), templates are Python functions that build HTML
via f-strings and helper functions — matching ``reporting.py``'s pattern.
The CSS lives in ``assets/`` and is inlined into the <head> at render
time, so each page is a single standalone HTML file requiring no external
assets (consistent with the static-site model).
"""
from __future__ import annotations

import html
import json
from datetime import date
from pathlib import Path
from typing import Any

from cfb_rankings.common.cfb_calendar import (
    cfb_week_label,
    human_phase_label,
    is_in_season,
    kickoff_date,
)
from cfb_rankings.common.head_chrome import render_head_chrome

from .profile_loader import Profile, load_profile, PROFILED_SLUGS
from .data import (
    FLOOR_AWAITING, FLOOR_GROWING,
    GameResult, TeamSnapshot, fetch_team_snapshot, fetch_mood_snapshot,
    fetch_divergence, fetch_state_of_team, fetch_chronicle_cards,
    fetch_last_sp_rating,
    fetch_savant_rows, fetch_savant_narrative, fetch_savant_echo,
    fetch_rivalry_posture, fetch_rivalry_stakes, fetch_rivalry_quote,
    fetch_season_arc, fetch_arc_narrative,
)
from .state_resolver import PageState, resolve_state
from .savant_card import render_savant_card
from .rivalry_card import render_rivalry_card
from .season_arc_card import render_season_arc_card
from .hero_arc_stripe import render_hero_arc_stripe, HERO_ARC_STRIPE_CSS
from .aspiration_ladder import render_aspiration_ladder, ASPIRATION_LADDER_CSS
from .season_standing_rail import (
    render_season_standing_rail,
    SEASON_STANDING_RAIL_CSS,
)
from .program_prestige_bar import (
    render_program_prestige_bar,
    PROGRAM_PRESTIGE_BAR_CSS,
)
from .page_tone_strip import render_page_tone_strip, PAGE_TONE_STRIP_CSS
from .trajectory_chip import render_trajectory_chip, TRAJECTORY_CHIP_CSS
from .kickoff_countdown import render_kickoff_countdown, KICKOFF_COUNTDOWN_CSS
from .peer_comparator import render_peer_comparator, PEER_COMPARATOR_CSS
from .on_this_day import render_on_this_day, ON_THIS_DAY_CSS
from .wrapped_stack import render_wrapped_stack, WRAPPED_STACK_CSS
from .fanbase_health import render_fanbase_health, FANBASE_HEALTH_CSS
from .conference_standing import render_conference_standing, CONFERENCE_STANDING_CSS
from .ceiling_floor import render_ceiling_floor, CEILING_FLOOR_CSS
from .home_field_advantage import render_home_field_advantage, HOME_FIELD_ADVANTAGE_CSS
from .moment_of_year import render_moment_of_year, MOMENT_OF_YEAR_CSS
from .schedule_strength import render_schedule_strength, SCHEDULE_STRENGTH_CSS
from .offseason_pulse import render_offseason_pulse, OFFSEASON_PULSE_CSS
from .recent_form import render_recent_form, RECENT_FORM_CSS
from .bowl_history import render_bowl_history, BOWL_HISTORY_CSS
from .statement_wins import render_statement_wins, STATEMENT_WINS_CSS
from .top_commits import render_top_commits, TOP_COMMITS_CSS
from .nfl_draft_pipeline import render_nfl_draft_pipeline, NFL_DRAFT_PIPELINE_CSS
from .rivalry_data_loader import (
    fetch_meetings, compute_all_time_record, fetch_next_meeting,
)


_ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def render_all_profiled_pages(
    db,
    output_dir: Path | str,
    *,
    today: date | None = None,
    season_year: int | None = None,
    include_unprofiled_fbs: bool = False,
) -> int:
    """Render the team page for every slug present in profiles/.

    Build-site hook. Swallows per-slug exceptions so one broken profile
    never fails the whole build; prints a one-line note per failure.
    Returns the count of pages successfully written.

    When ``include_unprofiled_fbs=True``, also renders every real FBS
    program that lacks a hand-authored YAML, using
    ``synthesize_profile()`` to build a usable Profile from DB signal.
    This closes the audit's T31 ("two-tier reality") gap — all 119 real
    FBS programs share the world-class chrome; only the 30 profiled ones
    carry hand-authored voice on top.
    """
    from .profile_loader import PROFILED_SLUGS, list_real_fbs_slugs, PROFILES_DIR
    from .historical_season_page import render_all_historical_seasons
    import sys

    # Diagnostic: surface PROFILED_SLUGS contents + count at runtime so CI logs
    # show what the discovery actually found. The silent-fail bug (2026-05-23)
    # where CI rendered only 50 of 55 hand-authored slugs needed this visibility.
    profiled_sorted = sorted(PROFILED_SLUGS)
    print(
        f"  team-pages v2: PROFILES_DIR={PROFILES_DIR} "
        f"PROFILED_SLUGS={len(profiled_sorted)} slugs",
        flush=True,
    )
    print(
        f"  team-pages v2: slugs = {profiled_sorted}",
        flush=True,
    )

    count = 0
    profiled_count = 0
    synthesized_count = 0
    errors: list[tuple[str, str]] = []
    for slug in profiled_sorted:
        try:
            render_team_page(
                db, slug, output_dir,
                today=today, season_year=season_year,
            )
            count += 1
            profiled_count += 1
        except Exception as exc:
            errors.append((slug, f"{type(exc).__name__}: {exc}"))
            # Eager print + flush so an OOM / SIGTERM mid-loop still leaves
            # a trail of which slugs we'd already tried.
            print(
                f"  team-pages v2: {slug} failed — {type(exc).__name__}: {exc}",
                flush=True,
            )
            sys.stdout.flush()

    if include_unprofiled_fbs:
        try:
            all_fbs = list_real_fbs_slugs(db)
        except Exception as exc:
            print(f"  team-pages v2: FBS slug list unavailable — {exc}")
            all_fbs = []
        unprofiled = [s for s in all_fbs if s not in PROFILED_SLUGS]
        for slug in unprofiled:
            try:
                render_team_page(
                    db, slug, output_dir,
                    today=today, season_year=season_year,
                )
                count += 1
                synthesized_count += 1
            except Exception as exc:
                errors.append((slug, f"{type(exc).__name__}: {exc}"))

    if errors:
        # Keep the noise short — show first 10 only.
        for slug, msg in errors[:10]:
            print(f"  team-pages v2: {slug} failed — {msg}")
        if len(errors) > 10:
            print(f"  team-pages v2: + {len(errors) - 10} more failures suppressed")

    if include_unprofiled_fbs:
        print(
            f"  team-pages v2: {profiled_count} hand-authored + "
            f"{synthesized_count} synthesized = {count} world-class team pages"
        )

    # Also render historical-season archive pages for every (slug, year)
    # pair present in team_season_arc. Errors per (slug, year) are logged
    # inside the helper so one bad row doesn't fail the whole build.
    try:
        hs_count = render_all_historical_seasons(db, output_dir)
        print(f"  team-pages v2: {hs_count} historical-season pages written")
    except Exception as exc:
        print(f"  team-pages v2: historical seasons render failed — {exc}")

    return count


def render_team_page(
    db,
    slug: str,
    output_dir: Path | str,
    *,
    today: date | None = None,
    season_year: int | None = None,
) -> Path:
    """Build the HTML and write it to output_dir/<slug>.html.

    Sprint H: when no hand-authored profile YAML exists for this slug,
    falls back to ``synthesize_profile()`` so every real FBS program can
    render with the world-class chrome.
    """
    from .profile_loader import load_or_synthesize
    profile = load_or_synthesize(slug, db)
    snapshot = fetch_team_snapshot(db, slug, season_year)
    # Sprint 6 — load any recent finalized live-game row for this team
    # within the 72h post-game window. resolve_state uses this to flip into
    # game-recap mode for the first 24h, then post-game-monday-tuesday
    # for hours 24–72.
    from cfb_rankings.ingest.sources.cfbd_live_game import fetch_recent_final_for_team
    try:
        live_game_meta = fetch_recent_final_for_team(db, slug, window_hours=72.0)
    except Exception:
        live_game_meta = None
    state = resolve_state(profile, snapshot, today=today, live_game_meta=live_game_meta)

    mood = fetch_mood_snapshot(db, snapshot.team_id, snapshot.season_year)
    divergence = fetch_divergence(db, snapshot.team_id, snapshot.season_year)
    sp_rating = fetch_last_sp_rating(db, snapshot.team_id, snapshot.season_year)
    state_of_team = fetch_state_of_team(db, snapshot.team_id, snapshot.season_year)
    chronicle_cards = fetch_chronicle_cards(db, snapshot.team_id, snapshot.season_year, limit=5)

    # Savant card data — falls back to the latest season that has rows so
    # the card renders even when the current-season ingest is incomplete.
    savant_season = _pick_savant_season(db, snapshot.team_id, snapshot.season_year)
    savant_rows = fetch_savant_rows(db, snapshot.team_id, savant_season) if savant_season else []
    savant_narrative = fetch_savant_narrative(db, snapshot.team_id, savant_season) if savant_season else None
    savant_echo = fetch_savant_echo(db, snapshot.team_id, savant_season) if savant_season else None

    # Rivalry card — pick tier-1 primary from profile.rivalries and pull meetings.
    rivalry_bundle = _load_rivalry_bundle(db, profile, savant_season or snapshot.season_year)

    # Season Arc — 2014+ CFPEraView
    arc_rows = fetch_season_arc(db, snapshot.team_id) if snapshot.team_id else []
    arc_thesis = fetch_arc_narrative(db, snapshot.team_id, "arc_thesis") if snapshot.team_id else None
    arc_closing = fetch_arc_narrative(db, snapshot.team_id, "arc_closing") if snapshot.team_id else None

    # Sprint 6 — game-recap mode: when state.game_recap_active is True,
    # generate / reuse the post-game narrative + diagnosis stats so the
    # GameRecapHero has its content. The standard hero is suppressed by
    # _render_page when state.hero_priority == 'game-recap'.
    game_recap_state_para = None
    game_recap_diagnosis = None
    if state.game_recap_active and live_game_meta is not None:
        from .narrative_generator import generate_state_of_team_post_game
        from .game_recap_hero import build_diagnosis_stats
        try:
            res = generate_state_of_team_post_game(
                profile, snapshot, state,
                final_meta=live_game_meta, mode="template",
            )
            game_recap_state_para = {"body_md": res.body_md, "model_id": res.model_id}
        except Exception as exc:
            print(f"  team-pages: game-recap narrative failed for {slug} — {exc}")
        # Diagnosis stats — fixture-supplied mock wins; otherwise derive from
        # team_savant_weekly's most-recent week. Returns [] (hides row) when
        # neither is available.
        try:
            mock = live_game_meta.get("diagnosis_stats")
            if isinstance(mock, str):
                mock = json.loads(mock)
            if mock:
                game_recap_diagnosis = build_diagnosis_stats(mock=mock)
            else:
                game_recap_diagnosis = build_diagnosis_stats(
                    db=db,
                    team_id=snapshot.team_id,
                    season_year=snapshot.season_year,
                )
        except Exception:
            game_recap_diagnosis = []

    html_out = _render_page(
        profile=profile,
        snapshot=snapshot,
        state=state,
        mood=mood,
        divergence=divergence,
        sp_rating=sp_rating,
        state_of_team=state_of_team,
        chronicle_cards=chronicle_cards,
        savant_rows=savant_rows,
        savant_narrative=savant_narrative,
        savant_echo=savant_echo,
        savant_season=savant_season,
        rivalry_bundle=rivalry_bundle,
        arc_rows=arc_rows,
        arc_thesis=arc_thesis,
        arc_closing=arc_closing,
        live_game_meta=live_game_meta,
        game_recap_state_para=game_recap_state_para,
        game_recap_diagnosis=game_recap_diagnosis,
        db=db,
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    out_path = out / f"{slug}.html"
    out_path.write_text(html_out, encoding="utf-8")
    return out_path


# ------------------------------------------------------------------------
# Page scaffold
# ------------------------------------------------------------------------

def _load_rivalry_bundle(db, profile: Profile, season_year: int) -> dict[str, Any] | None:
    """Pick the profile's first Tier-1 rivalry and load everything the card needs."""
    rivalries = profile.rivalries
    tier1 = next((r for r in rivalries if (r.get("tier") or 99) == 1), None)
    if not tier1:
        return None
    opp_slug = tier1.get("opponent_slug") or ""
    if not opp_slug:
        return None
    opp_team_row = db.query_one(
        "select team_id from teams where slug = :slug",
        {"slug": opp_slug},
    )
    opp_team_id = opp_team_row["team_id"] if opp_team_row else None

    meetings = fetch_meetings(db, profile.slug, opp_slug, limit=10, completed_only=True)
    if not meetings:
        return None
    all_time = compute_all_time_record(db, profile.slug, opp_slug)
    next_meeting = fetch_next_meeting(db, profile.slug, opp_slug)

    primary_posture = fetch_rivalry_posture(db, profile.team_id or 0, season_year, opp_slug)
    primary_stakes = fetch_rivalry_stakes(db, profile.team_id or 0, season_year, opp_slug)
    primary_quote = fetch_rivalry_quote(db, profile.team_id or 0, season_year, opp_slug)

    opponent_posture = opponent_stakes = opponent_quote = None
    if opp_slug in PROFILED_SLUGS and opp_team_id:
        opponent_posture = fetch_rivalry_posture(db, opp_team_id, season_year, profile.slug)
        opponent_stakes = fetch_rivalry_stakes(db, opp_team_id, season_year, profile.slug)
        opponent_quote = fetch_rivalry_quote(db, opp_team_id, season_year, profile.slug)

    return {
        "opponent_slug": opp_slug,
        "rivalry_meta": tier1,
        "meetings": meetings,
        "all_time": all_time,
        "next_meeting": next_meeting,
        "primary_posture": primary_posture,
        "primary_stakes": primary_stakes,
        "primary_quote": primary_quote,
        "opponent_posture": opponent_posture,
        "opponent_stakes": opponent_stakes,
        "opponent_quote": opponent_quote,
    }


def _pick_savant_season(db, team_id: int, preferred: int) -> int | None:
    """Return the preferred season if it has Savant rows, else latest available.

    The loader is driven by data-ingest completeness — when the current
    season is only partially ingested (as 2025 is during 2026 spring), we
    fall back to the most-recent season with rows so the card still reads.
    """
    row = db.query_one(
        """
        select season_year
        from team_savant_weekly
        where team_id = :tid and season_year = :s
        limit 1
        """,
        {"tid": team_id, "s": preferred},
    )
    if row:
        return preferred
    row = db.query_one(
        """
        select max(season_year) as y
        from team_savant_weekly
        where team_id = :tid
        """,
        {"tid": team_id},
    )
    return int(row["y"]) if row and row["y"] else None


def _render_page(
    *,
    profile: Profile,
    snapshot: TeamSnapshot,
    state: PageState,
    mood: dict[str, Any],
    divergence: float | None,
    sp_rating: dict[str, Any] | None,
    state_of_team: dict[str, Any] | None,
    chronicle_cards: list[dict[str, Any]],
    savant_rows: list[dict[str, Any]],
    savant_narrative: str | None,
    savant_echo: dict[str, Any] | None,
    savant_season: int | None,
    rivalry_bundle: dict[str, Any] | None,
    arc_rows: list[dict[str, Any]],
    arc_thesis: str | None,
    arc_closing: str | None,
    live_game_meta: dict[str, Any] | None = None,
    game_recap_state_para: dict[str, Any] | None = None,
    game_recap_diagnosis: list[dict[str, Any]] | None = None,
    db=None,  # Sprint I — On This Day needs DB to query past games
) -> str:
    tokens_css = (_ASSETS_DIR / "tokens.css").read_text(encoding="utf-8")
    styles_css = (_ASSETS_DIR / "styles.css").read_text(encoding="utf-8")
    savant_css = (_ASSETS_DIR / "savant_card.css").read_text(encoding="utf-8")
    rivalry_css = (_ASSETS_DIR / "rivalry_card.css").read_text(encoding="utf-8")
    arc_css = (_ASSETS_DIR / "season_arc_card.css").read_text(encoding="utf-8")
    rituals_css = (_ASSETS_DIR / "rituals_card.css").read_text(encoding="utf-8")

    # Sprint v5-11.5 Surface 2 wire-up — theme toggle + Cmd-K on profiled
    # team pages. The team_pages renderer inlines its CSS bundle and
    # doesn't go through _global_link_tags(), so we inject the assets
    # directly here. tokens-bridge.css is NOT loaded (team-page CSS uses
    # its own --bg-*/--fg-* tokens directly, with a [data-theme="light"]
    # override block appended to tokens.css for the toggle to flip).
    from cfb_rankings.theme.render import (
        THEME_INIT_SCRIPT,
        render_theme_toggle_button,
    )
    theme_toggle_css = (
        Path(__file__).parents[1] / "theme" / "assets" / "theme_toggle.css"
    ).read_text(encoding="utf-8")
    theme_toggle_js = (
        Path(__file__).parents[1] / "theme" / "assets" / "theme_toggle.js"
    ).read_text(encoding="utf-8")
    cmdk_css = (
        Path(__file__).parents[1] / "cmdk" / "assets" / "cmdk.css"
    ).read_text(encoding="utf-8")
    cmdk_js = (
        Path(__file__).parents[1] / "cmdk" / "assets" / "cmdk.js"
    ).read_text(encoding="utf-8")
    # Defensive </script> escape — same hardening as render_theme_assets_head
    theme_init_safe = THEME_INIT_SCRIPT.replace("</script>", "<\\/script>")

    accent_primary = profile.accent_hex
    accent_secondary = profile.accent_hex_secondary or _darken_color(accent_primary)

    page_title = f"{profile.program_name} — CFB Index"

    # Sprint 6 — when state.game_recap_active, the GameRecapHero replaces the
    # standard hero block. Falls back gracefully when the helper returns "".
    hero_html = ""
    if state.game_recap_active and live_game_meta is not None:
        from .game_recap_hero import render_game_recap_hero
        hero_html = render_game_recap_hero(
            profile=profile, snapshot=snapshot, state=state,
            live_meta=live_game_meta,
            state_of_team_para=game_recap_state_para,
            diagnosis=game_recap_diagnosis,
        )
    if not hero_html:
        hero_html = _render_hero(profile, snapshot, state, state_of_team, sp_rating)
    pulse_html = _render_pulse(profile, snapshot, state, mood, divergence)
    # Sprint v5-8.5 — rituals strip + cultural anchors sit between pulse
    # and chronicle per mockup_02_team_alabama_v2.html. Empty string when
    # the profile YAML carries no rituals (e.g. legacy slugs); module
    # never fabricates content.
    from .rituals_module import (
        render_cultural_anchors,
        render_rituals_strip,
    )
    rituals_html = render_rituals_strip(profile)
    cultural_anchors_html = render_cultural_anchors(profile)
    chronicle_html = _render_chronicle_section(chronicle_cards, profile, state)
    savant_html = render_savant_card(
        profile, savant_rows,
        narrative=savant_narrative,
        echo=savant_echo,
        season_year=savant_season or snapshot.season_year,
    ) if savant_rows else ""
    rivalry_html = ""
    if rivalry_bundle:
        rivalry_html = render_rivalry_card(
            profile,
            rivalry_bundle["opponent_slug"],
            rivalry_meta=rivalry_bundle["rivalry_meta"],
            meetings=rivalry_bundle["meetings"],
            all_time=rivalry_bundle["all_time"],
            next_meeting=rivalry_bundle["next_meeting"],
            primary_posture=rivalry_bundle["primary_posture"],
            primary_stakes=rivalry_bundle["primary_stakes"],
            primary_quote=rivalry_bundle["primary_quote"],
            opponent_posture=rivalry_bundle["opponent_posture"],
            opponent_stakes=rivalry_bundle["opponent_stakes"],
            opponent_quote=rivalry_bundle["opponent_quote"],
            season_year=savant_season or snapshot.season_year,
        )
    arc_html = ""
    if arc_rows:
        arc_html = render_season_arc_card(
            profile, arc_rows,
            thesis=arc_thesis, closing=arc_closing,
            accent_primary=accent_primary,
        )
    # Hero Arc 13-brick CFP-era stripe — Brief §20, screenshot-virality
    # identity strip above the fold. Reuses arc_rows so no new data fetch.
    hero_arc_stripe_html = ""
    if arc_rows:
        hero_arc_stripe_html = render_hero_arc_stripe(
            profile, arc_rows,
            current_season=snapshot.season_year if snapshot else None,
        )
    # Program Trajectory chip — Brief §11.4 "Are we as good as we used to be?"
    # 10-year rolling prestige rung with slope label + sparkline.
    trajectory_chip_html = ""
    if arc_rows:
        trajectory_chip_html = render_trajectory_chip(profile, arc_rows)
    # Program Peer Comparator — Brief §26 static-attribute variant. "What
    # does this team remind us of?" answered with 3 peer-program tiles.
    peer_comparator_html = render_peer_comparator(profile)
    # On This Day — Brief §25.3. Daily-rotated historical artifact. Pulls
    # past games on today's MM-DD, falls back to deterministic rotation.
    on_this_day_html = render_on_this_day(db, profile, today=state.today) if db is not None else ""
    # Wrapped stack — Brief §21.3. Spotify-Wrapped-styled retrospective.
    # Only renders in the Jan-Mar window; returns "" outside that.
    wrapped_html = render_wrapped_stack(profile, snapshot, arc_rows, today=state.today)
    # Fanbase Health Index gauge — Brief §11.1. 0-100 composite from record,
    # mood volume, and cohort divergence. Honest empty when all signals are
    # missing.
    fanbase_health_html = render_fanbase_health(profile, snapshot, mood, divergence, arc_rows)
    # Conference Standing — Brief §10.2-10.3. Where the focal team sits
    # within its conference cohort. Compact table + positioning summary.
    conference_standing_html = render_conference_standing(db, profile, snapshot) if db is not None else ""
    # Ceiling/Floor projection — Brief §11.2. Three-scenario next-season band.
    ceiling_floor_html = render_ceiling_floor(profile, snapshot, arc_rows)
    # Home-Field Advantage — Brief §11.3. Home vs away win-share + margin
    # differential from games table. Honest empty when sample < 6 games.
    home_field_html = render_home_field_advantage(db, profile, snapshot) if db is not None else ""
    # Moment of the Year — Brief §11.7 games-table approximation. Surfaces the
    # single highest-impact game of the season (ranked opponent + postseason +
    # margin scored). Honest empty when no impactful game scores ≥4.
    moment_of_year_html = render_moment_of_year(db, profile, snapshot) if db is not None else ""
    # Schedule Strength chip — opponent quality from games table.
    schedule_strength_html = render_schedule_strength(db, profile, snapshot) if db is not None else ""
    # Offseason Pulse — combines 4 CFBD tier-2 data feeds (recruiting class,
    # returning production, talent composite, transfer activity). Audit T9
    # resolution at team level. Above-the-fold in offseason.
    offseason_pulse_html = render_offseason_pulse(db, profile, snapshot) if db is not None else ""
    # Recent Form chip — last 10 finalized games as W/L glyph row.
    recent_form_html = render_recent_form(db, profile, snapshot) if db is not None else ""
    # Bowl History chip — postseason ledger from season_type='postseason' games.
    bowl_history_html = render_bowl_history(db, profile, snapshot) if db is not None else ""
    # Statement Wins counter — wins over AP top-25 ranked opponents.
    statement_wins_html = render_statement_wins(db, profile, snapshot) if db is not None else ""
    # Top Commits — 3 highest-rated incoming recruits (CFBD player_recruiting_profiles).
    top_commits_html = render_top_commits(db, profile, snapshot) if db is not None else ""
    # NFL Draft Pipeline — last 5 cycles of draft picks (CFBD player_nfl_draft).
    nfl_draft_html = render_nfl_draft_pipeline(db, profile, snapshot) if db is not None else ""
    # Aspiration Ladder — Brief Part III §33.4 mandates one per team page.
    aspiration_ladder_html = render_aspiration_ladder(profile, snapshot)
    # Season Standing 9-rung rail — Brief §3.1. Team analog of player
    # Standing Rail. Placed directly under the hero so the 5-second read
    # ("where is this team in the national picture") lands first.
    season_standing_html = render_season_standing_rail(profile, snapshot)
    # Program Prestige bar — Brief §3.2. Slower-moving sibling answering
    # "what kind of program is this, historically?" Sits next to Season
    # Standing so the fast + slow signals read together.
    program_prestige_html = render_program_prestige_bar(profile)
    # Page Tone Strip — Brief Part III §32. Makes seasonal sentience visible:
    # offseason vs gameday vs rivalry-peak read differently AND look
    # differently. The strip surfaces phase + tone + outcome + live state.
    page_tone_html = render_page_tone_strip(state)
    # Kickoff Countdown — Brief §22.1 offseason variant. Anchors every team
    # page in calendar time: "247 days · until kickoff · Aug 30" / "3d 18h ·
    # vs Michigan · Sat 12:00" / "Live now."
    kickoff_html = render_kickoff_countdown(snapshot, today=state.today)
    footer_html = _render_footer(profile, state)

    head_chrome_block = render_head_chrome(
        page_path=f"/teams/{profile.slug}.html",
        title=page_title,
        description=f"{profile.program_name} — state of the program, the Pulse, the Chronicle, the Savant card, and the Rivalry card.",
        og_image_path=f"/teams/{profile.slug}-og.svg",
        og_type="article",
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(page_title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="{html.escape(profile.program_name)} — state of the program, the Pulse, the Chronicle, the Savant card, and the Rivalry card.">
<meta name="theme-color" content="{accent_primary}">
{head_chrome_block}
<script>{theme_init_safe}</script>
<style>
{tokens_css}

body {{
  --accent-primary: {accent_primary};
  --accent-secondary: {accent_secondary};
  --accent-gradient: linear-gradient(135deg, {accent_primary}, {accent_secondary});
}}

{styles_css}
{savant_css}
{rivalry_css}
{arc_css}
{rituals_css}

/* Hero Arc 13-brick CFP-era stripe — Sprint E (Brief §20) */
{HERO_ARC_STRIPE_CSS}

/* Aspiration Ladder — Brief Part III §33.4 */
{ASPIRATION_LADDER_CSS}

/* Season Standing Rail — Brief §3.1 (team-page analog) */
{SEASON_STANDING_RAIL_CSS}

/* Program Prestige Bar — Brief §3.2 */
{PROGRAM_PRESTIGE_BAR_CSS}

/* Page Tone Strip — Brief Part III §32 (seasonal sentience visible) */
{PAGE_TONE_STRIP_CSS}

/* Program Trajectory chip — Brief §11.4 */
{TRAJECTORY_CHIP_CSS}

/* Kickoff Countdown — Brief §22.1 */
{KICKOFF_COUNTDOWN_CSS}

/* Program Peer Comparator — Brief §26 */
{PEER_COMPARATOR_CSS}

/* On This Day — Brief §25.3 */
{ON_THIS_DAY_CSS}

/* Wrapped stack — Brief §21.3 */
{WRAPPED_STACK_CSS}

/* Fanbase Health Index — Brief §11.1 */
{FANBASE_HEALTH_CSS}

/* Conference Standing — Brief §10.2-10.3 */
{CONFERENCE_STANDING_CSS}

/* Ceiling/Floor projection — Brief §11.2 */
{CEILING_FLOOR_CSS}

/* Home-Field Advantage — Brief §11.3 */
{HOME_FIELD_ADVANTAGE_CSS}

/* Moment of the Year — Brief §11.7 approximation */
{MOMENT_OF_YEAR_CSS}

/* Schedule Strength chip */
{SCHEDULE_STRENGTH_CSS}

/* Offseason Pulse — recruiting + returning + talent + portal (Audit T9) */
{OFFSEASON_PULSE_CSS}

/* Recent Form chip — last 10 games */
{RECENT_FORM_CSS}

/* Bowl History chip — postseason ledger */
{BOWL_HISTORY_CSS}

/* Statement Wins counter — top-25 wins this season */
{STATEMENT_WINS_CSS}

/* Top Commits — 3 highest-rated recruits per class */
{TOP_COMMITS_CSS}

/* NFL Draft Pipeline — last 5 cycles of draft picks */
{NFL_DRAFT_PIPELINE_CSS}

/* Sprint v5-11.5 Surface 2 — theme + cmdk on profiled team pages */
{theme_toggle_css}
{cmdk_css}

/* Floating button group — top-right corner. Cmd-K trigger + theme toggle. */
.profile-page-controls {{
  position: fixed;
  top: var(--sp-3, 12px);
  right: var(--sp-4, 16px);
  display: flex;
  gap: var(--sp-2, 8px);
  z-index: 50;
}}
.profile-page-controls .nav-action,
.profile-page-controls .theme-toggle,
.profile-page-controls .cmdk-trigger {{
  background: var(--bg-card, var(--bg-1));
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}}
@media (max-width: 640px) {{
  .profile-page-controls {{
    top: auto;
    bottom: var(--sp-3, 12px);
    right: var(--sp-3, 12px);
  }}
}}
</style>
<script defer>{theme_toggle_js}</script>
<script defer>{cmdk_js}</script>
</head>
<body data-page-tone="{state.accent_key}"
      data-page-phase="{state.season_phase}"
      data-page-anchor="{state.anchor_variant}"
      data-in-season="{'true' if state.is_in_season else 'false'}">
<a class="skip-link" href="#main-content">Skip to main content</a>
<div class="profile-page-controls" role="group" aria-label="Page controls">
  <button class="cmdk-trigger" data-cmdk-trigger type="button"
          aria-label="Search (Ctrl-K / Cmd-K)"
          title="Search (Ctrl-K / Cmd-K)">⌘K</button>
  {render_theme_toggle_button(css_class="theme-toggle")}
</div>
<main id="main-content" class="team-page">
  <div class="content">
    {hero_html}
    {page_tone_html}
    {kickoff_html}
    {offseason_pulse_html}
    {top_commits_html}
    {nfl_draft_html}
    {recent_form_html}
    {season_standing_html}
    {program_prestige_html}
    {trajectory_chip_html}
    {peer_comparator_html}
    {on_this_day_html}
    {wrapped_html}
    {fanbase_health_html}
    {conference_standing_html}
    {ceiling_floor_html}
    {home_field_html}
    {moment_of_year_html}
    {schedule_strength_html}
    {statement_wins_html}
    {bowl_history_html}
    {hero_arc_stripe_html}
    {pulse_html}
    {aspiration_ladder_html}
    {rituals_html}
    {cultural_anchors_html}
    {chronicle_html}
    {savant_html}
    {rivalry_html}
    {arc_html}
    {footer_html}
  </div>
</main>
</body>
</html>
"""


# ------------------------------------------------------------------------
# Hero
# ------------------------------------------------------------------------

def _render_hero(
    profile: Profile,
    snap: TeamSnapshot,
    state: PageState,
    state_of_team: dict[str, Any] | None,
    sp_rating: dict[str, Any] | None,
) -> str:
    record = f"{snap.wins}-{snap.losses}" + (f"-{snap.ties}" if snap.ties else "")

    chips: list[str] = []
    if snap.ap_rank:
        chips.append(_chip(f"AP #{snap.ap_rank}", cls=""))
    if snap.coaches_rank:
        chips.append(_chip(f"COACHES #{snap.coaches_rank}", cls=""))
    if snap.cfp_rank:
        chips.append(_chip(f"CFP #{snap.cfp_rank}", cls="hero__rank-chip--cfp"))
    chips_html = "".join(chips)

    eyebrow_text = _eyebrow_text(state, snap)

    # Team logo. Emit URL deterministically from slug (not via the
    # team_brand_assets DB lookup, which returned None for many slugs
    # even though /assets/team-art/<slug>/logo_primary.png exists for
    # all 664 teams). onerror gracefully hides the img for any
    # genuinely-missing PNG.
    logo_html = (
        f'<img class="hero__logo" '
        f'src="../assets/team-art/{html.escape(profile.slug)}/logo_primary.png" '
        f'alt="{html.escape(profile.display_name)} logo" '
        f'width="80" height="80" loading="eager" decoding="async" '
        f'onerror="this.style.display=\'none\'">'
        if profile.slug else ""
    )

    heritage_html = _render_heritage_strip(profile)
    state_paragraph_html = _render_state_paragraph(state_of_team, profile, state)
    metrics_html = _render_metric_tiles(profile, snap, sp_rating, state)

    # Identity phrase below the wordmark — gives every team a one-line
    # voice anchor (hand-authored profiles have bespoke phrases; synth
    # profiles get a register-templated phrase per Sprint H+).
    identity_html = (
        f'<p class="hero__identity-phrase">{html.escape(profile.identity_phrase)}</p>'
        if profile.identity_phrase else ""
    )

    return f"""<section class="hero" aria-labelledby="hero-wordmark">
  <div>
    <div class="hero__eyebrow">{html.escape(eyebrow_text)}</div>
    <div class="hero__identity-bar">
      {logo_html}
      <h1 id="hero-wordmark" class="hero__wordmark">{html.escape(profile.display_name)}</h1>
      <span class="hero__record" aria-label="Season record">{html.escape(record)}</span>
      {chips_html}
    </div>
    {identity_html}
  </div>
  {heritage_html}
  {state_paragraph_html}
  {metrics_html}
</section>
"""


def _eyebrow_text(state: PageState, snap: TeamSnapshot) -> str:
    today_str = state.today.strftime("%B %d, %Y").upper()
    phase_map = {
        "spring-and-portal": "SPRING & PORTAL",
        "nsd-and-portal": "NSD & PORTAL",
        "dead-period-heritage": "DEAD PERIOD · HERITAGE WINDOW",
        "media-days": "MEDIA DAYS",
        "camp": "FALL CAMP",
        "early-season": "EARLY SEASON",
        "stakes-rising": "STAKES RISING",
        "rivalry-peak": "RIVALRY PEAK",
        "cfp-selection-and-bowl": "CFP SELECTION · BOWL WINDOW",
        "bowl-and-carousel": "BOWLS · COACHING CAROUSEL",
    }
    phase = phase_map.get(state.season_phase, state.season_phase.upper())
    return f"{today_str} · {phase} · {snap.season_year} SEASON"


def _chip(text: str, cls: str = "") -> str:
    cls_attr = f"hero__rank-chip {cls}".strip()
    return f'<span class="{cls_attr}">{html.escape(text)}</span>'


def _render_heritage_strip(profile: Profile) -> str:
    """One-line compact program silhouette (Iteration Log §Refinements)."""
    heritage = profile.frontmatter.get("heritage") or {}
    items: list[str] = []
    if heritage.get("founded"):
        items.append(f"<span>Founded <strong>{heritage['founded']}</strong></span>")
    if heritage.get("national_titles"):
        items.append(f"<span>Titles <strong>{heritage['national_titles']}</strong></span>")
    if heritage.get("conference_titles"):
        items.append(f"<span>Conf titles <strong>{heritage['conference_titles']}</strong></span>")
    if heritage.get("heismans"):
        items.append(f"<span>Heismans <strong>{heritage['heismans']}</strong></span>")
    if heritage.get("cfp_appearances"):
        items.append(f"<span>CFP <strong>{heritage['cfp_appearances']}</strong></span>")
    if heritage.get("bowl_appearances"):
        items.append(f"<span>Bowls <strong>{heritage['bowl_appearances']}</strong></span>")
    if heritage.get("current_conference"):
        items.append(f"<span>Conference <strong>{html.escape(str(heritage['current_conference']))}</strong></span>")
    if heritage.get("stadium"):
        items.append(f"<span>Stadium <strong>{html.escape(str(heritage['stadium']))}</strong></span>")
    if heritage.get("legendary_coach"):
        items.append(f"<span>Legacy <strong>{html.escape(str(heritage['legendary_coach']))}</strong></span>")
    if not items:
        return ""
    return f'<div class="hero__heritage">{"".join(items)}</div>'


def _render_state_paragraph(
    state_of_team: dict[str, Any] | None,
    profile: Profile,
    state: PageState,
) -> str:
    if state_of_team and state_of_team.get("body_md"):
        body = state_of_team["body_md"]
    else:
        # Fallback copy — mascot voice 'empty_state' rather than generic
        # 'Awaiting Signal' (Iteration Log §24.4).
        mascot = profile.mascot_voice
        body = (
            mascot.get("empty_state")
            or mascot.get("awaiting_signal")
            or f"{profile.program_name} — state-of-team narrative pending."
        )
    # light inline bold emphasis for program name + mantra
    return f'<p class="hero__state">{html.escape(body)}</p>'


def _render_metric_tiles(
    profile: Profile,
    snap: TeamSnapshot,
    sp_rating: dict[str, Any] | None,
    state: PageState,
) -> str:
    tiles: list[tuple[str, str, str | None]] = []

    # Tile selection depends on tier (Iteration Log §Program-tier sentience).
    # Contenders (tier 1-2): AP / SP+ / CFP-hook / Record
    # Mid (tier 3-5): SP+ / Record / Bowl odds / Conf rank
    # Lower-tier: Record / SP+ / Bowl odds / Improvement-vs-last

    record = f"{snap.wins}-{snap.losses}" + (f"-{snap.ties}" if snap.ties else "")
    record_delta = _record_delta_label(snap)

    if profile.program_tier <= 2:
        tiles.append(("RECORD", record, record_delta))
        tiles.append(("AP", _rank_display(snap.ap_rank), _rank_delta_stub(snap.ap_rank)))
        tiles.append(("SP+", _sp_display(sp_rating), None))
        tiles.append(("CFP STANDING", _cfp_display(snap), None))
    elif profile.program_tier <= 5:
        tiles.append(("RECORD", record, record_delta))
        tiles.append(("SP+", _sp_display(sp_rating), None))
        tiles.append(("AP / COACHES", _rank_display(snap.ap_rank or snap.coaches_rank), None))
        tiles.append(("BOWL STATUS", _bowl_display(snap), None))
    else:
        tiles.append(("RECORD", record, record_delta))
        tiles.append(("SP+", _sp_display(sp_rating), None))
        tiles.append(("BOWL ODDS", _bowl_display(snap), None))
        tiles.append(("YEAR-OVER-YEAR", _improvement_display(snap), None))

    tiles_html = "".join(
        _render_metric_tile(label, value, delta, idx == 0)
        for idx, (label, value, delta) in enumerate(tiles)
    )

    return f'<div class="hero__metrics">{tiles_html}</div>'


def _render_metric_tile(label: str, value: str, delta: str | None, accent: bool) -> str:
    value_cls = "metric-tile__value metric-tile__value--accent" if accent else "metric-tile__value"
    delta_html = (
        f'<div class="metric-tile__delta">{html.escape(delta)}</div>' if delta else ""
    )
    return f"""<div class="metric-tile">
  <div class="metric-tile__label">{html.escape(label)}</div>
  <div class="{value_cls}">{html.escape(value)}</div>
  {delta_html}
</div>"""


def _rank_display(rank: int | None) -> str:
    if rank is None:
        return "—"
    return f"#{rank}"


def _rank_delta_stub(rank: int | None) -> str | None:
    if rank is None:
        return None
    return f"top-{max(25, ((rank // 5) + 1) * 5)}"


def _sp_display(sp: dict[str, Any] | None) -> str:
    if not sp:
        return "—"
    return f"{sp['power_rating']:+.1f}"


def _cfp_display(snap: TeamSnapshot) -> str:
    if snap.cfp_rank:
        return f"#{snap.cfp_rank}"
    if snap.season_complete:
        return "Season closed"
    if snap.wins >= 10:
        return "In the window"
    return "Outside the window"


def _bowl_display(snap: TeamSnapshot) -> str:
    if snap.wins >= 6:
        return "Eligible"
    needed = max(0, 6 - snap.wins)
    if snap.season_complete:
        return "Season closed"
    return f"Needs {needed}"


def _improvement_display(snap: TeamSnapshot) -> str:
    return f"{snap.wins} wins"


def _record_delta_label(snap: TeamSnapshot) -> str | None:
    total = snap.wins + snap.losses + snap.ties
    if total == 0:
        return None
    pct = snap.wins / total
    if pct >= 0.75:
        return f"win% .{int(pct * 1000):03d}"
    if pct >= 0.5:
        return f"win% .{int(pct * 1000):03d}"
    return f"win% .{int(pct * 1000):03d}"


# ------------------------------------------------------------------------
# Pulse
# ------------------------------------------------------------------------

# Floor thresholds (FLOOR_AWAITING, FLOOR_GROWING) live in data.py and
# are imported above — single source of truth. Keep the rendering rules
# documented here for grep-ability:
#   <FLOOR_AWAITING       → "Awaiting Signal" (no sparkline, no velocity
#                            number, takes fall back to profile stock
#                            phrases).
#   FLOOR_AWAITING-FLOOR_GROWING → "Sample Growing" badge with live data.
#   ≥FLOOR_GROWING        → Full render, no caveat badge.


def _render_pulse(
    profile: Profile,
    snap: TeamSnapshot,
    state: PageState,
    mood: dict[str, Any],
    divergence: float | None,
) -> str:
    has_data = bool(mood.get("has_data"))
    mood_value = mood.get("mood_value")
    effective_n = float(mood.get("effective_n") or 0.0)

    # Mode A only when we have aggregated cohort signal AT the floor AND
    # the team-week conversation pipeline produced a number we can show.
    show_live = has_data and mood_value is not None and effective_n >= FLOOR_AWAITING

    if show_live:
        mood_value_html = f'<div class="pulse__mood-number">{mood_value}</div>'
        delta = mood.get("mood_delta")
        if delta is not None:
            delta_sign = "+" if delta >= 0 else ""
            delta_txt = f'Δ {delta_sign}{delta * 50:.1f} vs last wk'
        else:
            delta_txt = "baseline · first week of signal"
        mood_meta = f'<div class="pulse__mood-delta">{html.escape(delta_txt)}</div>'
    else:
        fallback = profile.mascot_voice.get("awaiting_signal") \
            or f"{profile.program_name} — signal pending."
        mood_value_html = '<div class="pulse__mood-number">—</div>'
        mood_meta = f'<div class="pulse__mood-delta">{html.escape(fallback)}</div>'

    # Sparkline + velocity render only above the awaiting-signal floor.
    sparkline_points = mood.get("trajectory") or []
    trajectory_html = (
        _render_trajectory(sparkline_points) if show_live and sparkline_points else ""
    )
    velocity_html = (
        _render_velocity(int(mood.get("volume") or 0), state) if show_live else ""
    )

    live_dot_cls = "pulse__live-dot" if show_live else "pulse__live-dot pulse__live-dot--quiet"
    # The "LIVE" label is only honest when the latest_week is from the
    # current calendar year. If we're surfacing mentions from a prior
    # season (e.g. 2025-30 on a page rendered in May 2026), say
    # "ARCHIVE" so the label doesn't lie about being real-time.
    is_archive_week = False
    if show_live:
        wk_str = str(mood.get("latest_week") or "")
        if wk_str:
            try:
                wk_year = int(wk_str.split("-")[0])
                from datetime import datetime as _dt_pulse
                is_archive_week = wk_year < _dt_pulse.utcnow().year
            except (ValueError, IndexError):
                is_archive_week = False
    if not show_live:
        live_label = "QUIET"
    elif is_archive_week:
        live_label = "ARCHIVE"
    else:
        live_label = "LIVE"
    meta_text = _pulse_meta(mood, state, snap)

    event_log_html = _render_event_log(snap, state, profile)

    # Top take — if conversation data has a top storyline at-or-above the
    # floor, surface it; otherwise rotate a deterministic stock phrase from
    # the profile so the same fan doesn't see the same line every visit.
    storyline = mood.get("top_storyline") if show_live else None
    top_take_text, top_take_attr = _resolve_top_take(storyline, profile, state)

    badge_html = _render_pulse_badge(effective_n)

    # Sprint D (Brief §4.2 Panel 2): five-axis strip — Reality Gap /
    # Respect Gap / Cohort Divergence / Rival Heat / Volatility.
    # Wire from existing data where present; honest empty-state otherwise.
    five_axis_html = _render_five_axis_strip(mood, divergence, snap, state, show_live)

    return f"""<section class="pulse" aria-labelledby="pulse-title">
  <div class="pulse__header">
    <span class="{live_dot_cls}" aria-hidden="true"></span>
    <h2 id="pulse-title" class="pulse__title">The Pulse on {html.escape(profile.program_name)}</h2>
    <span class="pulse__meta">{html.escape(live_label)} · {html.escape(meta_text)}</span>
  </div>
  <div class="pulse__grid">
    <div class="pulse__mood-card">
      {mood_value_html}
      {mood_meta}
      {trajectory_html}
      {velocity_html}
    </div>
    <div>
      {event_log_html}
      <div class="pulse__top-take" style="margin-top: var(--sp-4);">
        <em>"{html.escape(top_take_text)}"</em>
        <span class="pulse__top-take-attr">{html.escape(top_take_attr)}</span>
      </div>
    </div>
  </div>
  {five_axis_html}
  {badge_html}
</section>"""


# ============================================================================
# Five-axis strip — Brief §4.2 Panel 2 (Sprint D)
# ============================================================================

def _render_five_axis_strip(
    mood: dict[str, Any],
    divergence: float | None,
    snap: TeamSnapshot,
    state: PageState,
    show_live: bool,
) -> str:
    """Five axes per the brief: Reality Gap / Respect Gap / Cohort Divergence
    / Rival Heat / Volatility. Each renders a mini-bar with a labeled chip.
    Axes where data isn't ingested yet render in honest empty-state mode."""
    # Best-effort signal extraction. The mood dict carries cohort signals
    # when the FI pipeline has populated them; everything else falls
    # through to honest awaiting copy per brief §8.8.
    def _abs_pct(v: Any) -> int | None:
        if v is None:
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        if abs(f) <= 1.0 + 1e-9:
            return max(0, min(100, int(round(abs(f) * 100))))
        return max(0, min(100, int(round(abs(f)))))

    reality_pct = _abs_pct(mood.get("reality_gap"))
    respect_pct = _abs_pct(mood.get("respect_gap"))
    divergence_pct = _abs_pct(divergence)
    rival_pct = _abs_pct(mood.get("rival_heat"))
    volatility_pct = _abs_pct(mood.get("volatility"))

    def _axis(label: str, pct: int | None, desc: str) -> str:
        if pct is None:
            return (
                '<div class="pulse-axis pulse-axis--awaiting">'
                f'<span class="pulse-axis__label">{html.escape(label)}</span>'
                '<div class="pulse-axis__bar"><span class="pulse-axis__fill" style="--pct: 8%;"></span></div>'
                f'<span class="pulse-axis__chip">awaiting</span>'
                f'<span class="pulse-axis__desc">{html.escape(desc)}</span>'
                '</div>'
            )
        # Band by absolute strength (this is intensity, not signed)
        band = "high" if pct >= 70 else "mid" if pct >= 40 else "low"
        return (
            f'<div class="pulse-axis" data-band="{band}">'
            f'<span class="pulse-axis__label">{html.escape(label)}</span>'
            f'<div class="pulse-axis__bar"><span class="pulse-axis__fill" style="--pct: {pct}%;"></span></div>'
            f'<span class="pulse-axis__chip">{pct} pct</span>'
            f'<span class="pulse-axis__desc">{html.escape(desc)}</span>'
            '</div>'
        )

    axes_html = "".join([
        _axis("Reality Gap", reality_pct,
              "How far fan belief diverges from the structural model."),
        _axis("Respect Gap", respect_pct,
              "Fan score minus national score for this team's brand."),
        _axis("Cohort Divergence", divergence_pct,
              "Spread between sub-fanbase cohorts in the Pulse window."),
        _axis("Rival Heat", rival_pct,
              "How much rival fanbases are mentioning this team."),
        _axis("Volatility", volatility_pct,
              "Week-over-week mood swing magnitude."),
    ])
    return f"""<div class="pulse-five-axis" aria-label="Five-axis Pulse strip" data-state="{('ready' if show_live else 'empty')}">
    <p class="pulse-five-axis__eyebrow">FIVE-AXIS · Brief §4.2 Panel 2</p>
    {axes_html}
  </div>"""


def _render_trajectory(trajectory: list[dict[str, Any]]) -> str:
    # Scale heights from [-1, 1] → [8%, 96%]. Caller ensures non-empty input.
    bars_html = []
    max_idx = len(trajectory) - 1
    for i, pt in enumerate(trajectory):
        raw = pt.get("net_sentiment", 0.0)
        pct = max(0.08, min(0.96, (float(raw) + 1.0) / 2.0))
        cls = "pulse__trajectory-bar"
        if i == max_idx:
            cls += " pulse__trajectory-bar--current"
        bars_html.append(
            f'<div class="{cls}" style="height: {pct*100:.0f}%" '
            f'title="Wk {pt.get("week")}"></div>'
        )
    return (
        f'<div class="pulse__trajectory" aria-label="7-week mood trajectory">'
        f'{"".join(bars_html)}</div>'
    )


def _pulse_meta(mood: dict[str, Any], state: PageState, snap: TeamSnapshot) -> str:
    if mood.get("has_data"):
        wk = mood.get("latest_week")
        vol = mood.get("volume", 0)
        conf = mood.get("confidence_tier") or "medium"
        # In-season: 'Wk 9 · 1,234 mentions · medium confidence'.
        # Offseason: drop the bare 'Wk N' (reads as garbage in May) and use
        # the human phase label instead. The mention count + confidence
        # tier stay informative regardless of phase.
        if is_in_season(date.today(), db=None):
            return f"Wk {wk} · {vol:,} mentions · {conf} confidence"
        return f"{human_phase_label(date.today(), db=None)} · {vol:,} mentions · {conf} confidence"
    return f"{state.season_phase.replace('-', ' ')} · signal ramps back in camp"


def _pulse_panel_label(state: PageState) -> str:
    """Header for the right-hand 'what moved it' panel.

    Keyed on the resolved anchor variant (more granular than season_phase
    so we can split post-win / post-loss / rivalry from the standard
    midweek render). Falls back to month-of-year season phase.
    """
    by_anchor = {
        "post-loss-sunday-monday": "LAST 72 HOURS",
        "post-win-sunday-monday": "LAST 72 HOURS",
        "rivalry-week-friday": "RIVALRY WEEK · BUILD-UP",
        "gameday-pre-kickoff": "GAMEDAY · LAST 24 HOURS",
        "dead-period-summer": "OFFSEASON · LAST 30 DAYS",
        "portal-window-active": "SPRING & PORTAL · LAST 30 DAYS",
        "bowl-and-carousel": "BOWLS & CAROUSEL · LAST 30 DAYS",
        "media-days": "MEDIA DAYS · LAST 14 DAYS",
        "camp-open": "FALL CAMP · LAST 14 DAYS",
    }
    label = by_anchor.get(state.anchor_variant)
    if label:
        return label
    by_phase = {
        "spring-and-portal": "SPRING & PORTAL · LAST 30 DAYS",
        "nsd-and-portal": "NSD & PORTAL · LAST 30 DAYS",
        "dead-period-heritage": "OFFSEASON · LAST 30 DAYS",
        "bowl-and-carousel": "BOWLS & CAROUSEL · LAST 30 DAYS",
        "media-days": "MEDIA DAYS · LAST 14 DAYS",
        "camp": "FALL CAMP · LAST 14 DAYS",
        "rivalry-peak": "RIVALRY WINDOW · LAST 14 DAYS",
        "cfp-selection-and-bowl": "SELECTION WINDOW",
    }
    return by_phase.get(state.season_phase, "LAST 14 DAYS")


def _render_event_log(snap: TeamSnapshot, state: PageState, profile: Profile) -> str:
    """State-aware event log.

    In-season: last 2-3 game results with margin deltas (the legacy view).
    Offseason: date-driven placeholders covering portal / spring practice /
    coaching activity windows. We never show a previous-season game result
    in an offseason window — that's the bug we're fixing here.
    """
    label = _pulse_panel_label(state)
    is_offseason = state.season_phase in (
        "spring-and-portal",
        "nsd-and-portal",
        "dead-period-heritage",
        "bowl-and-carousel",
        "media-days",
        "camp",
    )

    events: list[tuple[str, str, str, str]] = []  # (time, text, delta, delta_cls)
    if is_offseason:
        events.extend(_offseason_events(state, profile))
    else:
        finals = [g for g in snap.recent_games if g.outcome in ("W", "L", "T")]
        for g in reversed(finals[-3:]):
            loc = "vs" if g.is_home else "at"
            text = f"{g.outcome} {g.team_points}-{g.opp_points} {loc} {g.opponent_name}"
            delta = f"{g.margin:+d}" if g.margin is not None else ""
            delta_cls = "pulse__event-delta--up" if (g.margin or 0) > 0 else "pulse__event-delta--down"
            events.append((f"Wk {g.week}", text, delta, delta_cls))

    if not events:
        events.append(("—", "Awaiting next signal window", "", ""))

    events_html = []
    for t, text, delta, cls in events:
        delta_html = (
            f'<span class="pulse__event-delta {cls}">{html.escape(delta)}</span>'
            if delta else '<span class="pulse__event-delta"></span>'
        )
        events_html.append(f"""<div class="pulse__event">
      <span class="pulse__event-time">{html.escape(t)}</span>
      <span class="pulse__event-text">{html.escape(text)}</span>
      {delta_html}
    </div>""")
    return f"""<div class="pulse__event-log">
    <p class="pulse__event-log-title">What moved it — {html.escape(label.lower())}</p>
    {''.join(events_html)}
  </div>"""


def _offseason_events(
    state: PageState,
    profile: Profile,
) -> list[tuple[str, str, str, str]]:
    """Date-driven offseason event placeholders.

    Source tables (portal_moves, coaching_changes, spring_events) are
    seeded but currently empty for these programs. Until the offseason
    ingest pipeline lands, we render anchored, date-arithmetic items so
    the panel stays readable instead of showing stale game results.
    """
    today = state.today
    phase = state.season_phase
    items: list[tuple[str, str, str, str]] = []

    if phase in ("spring-and-portal", "nsd-and-portal"):
        # Spring practice window: late-March through late-April for most
        # programs; transfer portal spring window May 1 - 15.
        portal_open = date(today.year, 5, 1)
        portal_close = date(today.year, 5, 15)
        if today < portal_open:
            days_to_portal = (portal_open - today).days
            items.append((
                "Spring",
                f"Spring practice window — {profile.program_name} reps + position battles",
                "ongoing",
                "pulse__event-delta--up",
            ))
            items.append((
                "Portal",
                f"Spring transfer window opens in {days_to_portal} days",
                f"{portal_open.strftime('%b %d')}",
                "",
            ))
        elif portal_open <= today <= portal_close:
            items.append((
                "Portal",
                "Spring transfer portal window OPEN",
                "active",
                "pulse__event-delta--up",
            ))
            items.append((
                "Spring",
                "Spring game wrap — depth chart resets",
                "—",
                "",
            ))
        else:
            items.append((
                "Spring",
                "Spring window closed — staff in evaluation mode",
                "—",
                "",
            ))
        items.append((
            "Camp",
            f"Fall camp opens early August — {(date(today.year, 8, 1) - today).days} days out",
            "",
            "",
        ))
    elif phase == "dead-period-heritage":
        items.append((
            "June",
            "Dead-period quiet — official-visit + heritage window",
            "—",
            "",
        ))
        items.append((
            "Camp",
            f"Fall camp ~{max(0, (date(today.year, 8, 1) - today).days)} days out",
            "",
            "",
        ))
    elif phase == "media-days":
        items.append((
            "Media",
            "Conference media days — coach + player podium runs",
            "live",
            "pulse__event-delta--up",
        ))
        items.append((
            "Camp",
            f"Fall camp opens in ~{max(0, (date(today.year, 8, 1) - today).days)} days",
            "",
            "",
        ))
    elif phase == "camp":
        items.append((
            "Camp",
            "Fall camp open — install + scrimmage cycle",
            "ongoing",
            "pulse__event-delta--up",
        ))
        # Use real kickoff date from the games table (with KEY_EVENTS_2026
        # fallback when DB is empty) rather than the historical hardcoded
        # Aug 30 anchor. See common/cfb_calendar.
        kickoff = kickoff_date(today.year, db=None)
        if today < kickoff:
            items.append((
                "Kickoff",
                f"Season opener in {(kickoff - today).days} days",
                "kickoff",
                "",
            ))
    elif phase == "bowl-and-carousel":
        items.append((
            "Bowls",
            "Bowl/playoff window — postseason matchups firming up",
            "live",
            "pulse__event-delta--up",
        ))
        items.append((
            "Carousel",
            "Coaching carousel + early portal moves",
            "active",
            "",
        ))
    return items


def _resolve_top_take(storyline, profile: Profile, state: PageState) -> tuple[str, str]:
    if storyline and isinstance(storyline, dict):
        text = str(storyline.get("text") or storyline.get("headline") or "").strip()
        venue = str(storyline.get("venue") or storyline.get("source") or "beat-writer feed").strip()
        if text:
            return text, f"— {venue}"
    # Off-season / below-floor fallback: deterministic rotation through the
    # profile's stock_phrases. Hash on (slug + ISO week) stabilizes within a
    # week, varies week to week. Attribution reads as fanbase vernacular —
    # never references the pipeline or the module itself.
    stock = profile.stock_phrases
    if stock:
        week_no = state.today.isocalendar().week
        idx = abs(hash((profile.slug, week_no))) % len(stock)
        return stock[idx], f"— {profile.program_name} fanbase · recurring line"
    # Last-resort: an on-voice mascot quiet-state line.
    quiet = profile.mascot_voice.get("empty_state") or profile.mascot_voice.get("awaiting_signal")
    if quiet:
        return quiet, f"— {profile.program_name} · offseason register"
    return (
        f"{profile.program_name} through the quiet.",
        f"— {profile.program_name} · offseason register",
    )


def _render_velocity(volume: int, state: PageState) -> str:
    """Velocity readout. Caller hides this entirely below the floor."""
    return f"""<div class="pulse__velocity">
    <span class="pulse__velocity-number">{volume:,}</span>
    <span class="pulse__velocity-context">mentions this week · conversation velocity</span>
  </div>"""


def _render_pulse_badge(effective_n: float) -> str:
    """Footer badge surfacing the floor-rule state.

    <30 → "Awaiting Signal"; 30–100 → "Sample Growing"; ≥100 → no badge
    (full-fidelity render is the norm at that point).
    """
    # Audit-2 finding: "n=0 · awaiting signal" exposes the internal
    # effective_n field name to fans. Fan-readable rephrase keeps the
    # number (useful) but uses "mentions" instead of "n=" (jargon).
    n = max(0, int(round(effective_n)))
    label_word = "mention" if n == 1 else "mentions"
    if effective_n < FLOOR_AWAITING:
        return (
            f'<div class="pulse__badge-row">'
            f'<span class="pulse__badge pulse__badge--awaiting">'
            f'{n} {label_word} · awaiting signal</span></div>'
        )
    if effective_n < FLOOR_GROWING:
        return (
            f'<div class="pulse__badge-row">'
            f'<span class="pulse__badge pulse__badge--growing">'
            f'{n} {label_word} · sample growing</span></div>'
        )
    return ""


# ------------------------------------------------------------------------
# Chronicle
# ------------------------------------------------------------------------

def _render_chronicle_section(
    cards: list[dict[str, Any]],
    profile: Profile,
    state: PageState,
) -> str:
    if not cards:
        return ""
    cards_html = "".join(_render_chronicle_card(c) for c in cards)
    return f"""<section class="chronicle" aria-labelledby="chronicle-title">
  <div class="chronicle__header">
    <h2 id="chronicle-title" class="chronicle__title">The Chronicle</h2>
    <span class="pulse__meta">{state.season_year} season · editorial observations</span>
  </div>
  <div class="chronicle__grid">
    {cards_html}
  </div>
</section>"""


def _render_chronicle_card(card: dict[str, Any]) -> str:
    ct = card.get("card_type", "anomaly")
    type_label = ct.upper()
    return f"""<article class="chronicle-card chronicle-card--{html.escape(ct)}">
  <span class="chronicle-card__type">{html.escape(type_label)}</span>
  <h3 class="chronicle-card__headline">{html.escape(card.get('headline', ''))}</h3>
  <p class="chronicle-card__body">{html.escape(card.get('body_md', ''))}</p>
  <span class="chronicle-card__source">{html.escape(card.get('source', '') or '')}</span>
</article>"""


# ------------------------------------------------------------------------
# Footer
# ------------------------------------------------------------------------

def _render_footer(profile: Profile, state: PageState) -> str:
    mantra = profile.mantra or ""
    mantra_html = (
        f'<span class="page-footer__mantra">“{html.escape(mantra)}”</span>'
        if mantra else "<span></span>"
    )
    model = profile.frontmatter.get("model_version", "team-pages v1.0")
    # Sprint F: reverse-pointer to the /programs/<slug> historical view so
    # users on the current-season page can navigate to the multi-decade
    # history without going through the nav. Closes the audit's "two URL
    # families, no obvious crosslink" complaint from the team-page side.
    program_link = (
        f'<a class="page-footer__link" href="/programs/{html.escape(profile.slug)}.html" '
        'aria-label="View the multi-decade program history page">'
        'Historical view →</a>'
        if profile.slug else ""
    )
    return f"""<footer class="page-footer">
  <span>CFB Index · {html.escape(model)}</span>
  {mantra_html}
  {program_link}
</footer>"""


# ------------------------------------------------------------------------
# Color helpers
# ------------------------------------------------------------------------

def _darken_color(hex_color: str, factor: float = 0.7) -> str:
    """Simple hex-RGB darken for the gradient partner when profile omits one."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6:
        return hex_color
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    r = int(r * factor)
    g = int(g * factor)
    b = int(b * factor)
    return f"#{r:02x}{g:02x}{b:02x}"
