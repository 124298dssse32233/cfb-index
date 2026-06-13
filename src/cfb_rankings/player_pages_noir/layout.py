"""Noir 7-section composer (plan doc 61 §2/§3).

REUSES the already-rendered legacy module HTML carried on ``player_data`` (the
``new_*_html`` keys) and arranges it into the seven Noir sections. The module code
is NOT reimplemented and NOTHING is deleted — "merge into a section" means
render-in-place (preservation rule, §2). A module with no HTML simply hides; a
whole section with no content is omitted (adaptive). A catch-all guarantees that
ANY ``new_*_html`` key not explicitly placed still renders (never silently lost).
NEVER raises — any failure returns "" and the caller falls back to legacy.
"""
from __future__ import annotations

from html import escape
from typing import Any

# (number, eyebrow, [ordered player_data keys]).  Plain (single-group) sections.
_SECTIONS: list[tuple[str, str, list[str]]] = [
    ("2", "The Dossier", ["new_story_card_html"]),
    ("4", "The Heartbeat", [
        "new_career_arc_html", "new_dev_traj_html",
        "new_heisman_trajectory_html", "new_season_context_html",
    ]),
    ("5", "The Record", [
        "new_game_log_html", "new_splits_html", "new_box_savant_html",
        "new_pass_profile_html", "new_peer_comparator_html", "new_mirror_match_html",
        "new_career_standing_html", "new_standing_rail_html", "new_selector_grid_html",
        "new_trophy_case_html", "new_nil_draft_html", "new_narrative_arc_html",
        "new_scenario_explorer_html", "new_supporting_cast_html",
    ]),
]
# Section 3 "Showcases" renders three NAMED sub-showcases (doc 60 §7), each with its
# own eyebrow; a sub-showcase with no content hides; if all hide, Section 3 is gone.
_SHOWCASES: list[tuple[str, list[str]]] = [
    ("The Throne", ["new_where_ended_up_html", "new_coaching_lineage_html"]),
    ("The Tribunal", ["new_aura_html"]),
    ("In Their Words", ["new_in_their_words_html"]),
]
_SHOWCASE_KEYS = {k for _n, ks in _SHOWCASES for k in ks}
# Keys placed in the hero/footer chrome, excluded from the catch-all.
_CHROME_KEYS = {"new_story_card_html", "new_status_strip_html", "new_live_signal_flow_html"}


def _s(v: Any) -> str:
    return v if isinstance(v, str) else ""


def _present(player_data: dict, keys: list[str]) -> list[str]:
    return [_s(player_data.get(k)).strip() for k in keys if _s(player_data.get(k)).strip()]


def _hero(player_data: dict) -> str:
    # Authoritative identity keys (reporting.py render): player + primary_team.
    # `player_identity` kept only as a fallback for unit tests.
    player = player_data.get("player") or player_data.get("player_identity") or {}
    pteam = player_data.get("primary_team") or {}
    name = _s(player.get("full_name") or player.get("name") or "Player")
    pos = _s(player.get("position") or pteam.get("position"))
    team = _s(pteam.get("team_name") or player.get("team_name") or player.get("team"))
    cls = _s(str(player.get("class_year") or pteam.get("class_year") or player.get("class") or ""))
    jersey = player.get("jersey") or player.get("jersey_number")
    tier = _s(player_data.get("tier_rail") or "t3").lower()
    monogram = "".join(w[0] for w in name.split()[:2]).upper() or "?"
    eyebrow = " · ".join(p for p in [pos, team, (f"Cl {cls}" if cls else ""), (f"#{jersey}" if jersey else "")] if p)
    # scorecard: up to 4 real stat chips already prepared by the engine, if present.
    chips = player_data.get("hero_scorecard") or []
    chip_html = "".join(
        f'<div class="nchip"><b>{escape(_s(c.get("value")))}</b><span>{escape(_s(c.get("label")))}</span></div>'
        for c in chips[:4] if isinstance(c, dict)
    )
    status = _s(player_data.get("new_status_strip_html"))
    return (
        f'<section class="nz nz--first nhero" data-tier="{escape(tier)}">'
        f'<div class="nhero__rail"></div>'
        f'<div class="nhero__mono">{escape(monogram)}</div>'
        f'<div style="flex:1">'
        f'<p class="nz__eyebrow">The Dossier · CFB Index</p>'
        f'<div class="nhero__name">{escape(name)}</div>'
        f'<div class="nhero__eye">{escape(eyebrow)}</div>'
        f'{f"<div class=\"nhero__score\">{chip_html}</div>" if chip_html else ""}'
        f'{f"<div class=\"nmod\">{status}</div>" if status else ""}'
        '</div></section>'
    )


def _verdict(player_data: dict) -> str:
    v = player_data.get("noir_verdict") or {}
    word, kick = _s(v.get("word")), _s(v.get("kicker"))
    if not (word or kick):
        return ""
    return (
        '<section class="nz"><p class="nz__eyebrow">6 · Verdict</p>'
        '<div class="nverdict">'
        f'{f"<div class=\"nverdict__w\">{escape(word)}</div>" if word else ""}'
        f'{f"<p class=\"nverdict__k\">{escape(kick)}</p>" if kick else ""}'
        '</div></section>'
    )


def _footer(player_data: dict) -> str:
    meta = _s(player_data.get("noir_footer") or
             "How CFB Index scores players · /methodology/")
    return f'<section class="nz nfoot">{meta}</section>'


def _season_tables_html(player_data: dict) -> str:
    """The traditional multi-season + career stat table (The Record leads with it,
    'traditional-first', doc 60 §7). Reuses reporting.render_all_player_season_stat_tables
    on the precomputed season_stat_tables list. Lazy + guarded; "" on any issue."""
    rows = player_data.get("season_stat_tables") or []
    if not rows:
        return ""
    try:
        from cfb_rankings.reporting import render_all_player_season_stat_tables
        player = player_data.get("player") or {}
        html = render_all_player_season_stat_tables(
            rows,
            player_name=str(player.get("full_name") or "Player"),
            player_slug=str(player.get("player_slug") or "") or None,
            use_legacy=True,   # the traditional numeric career table
        )
        return html or ""
    except Exception:
        return ""


def _showcases(player_data: dict, skip: set[str] | None = None) -> str:
    """Section 3 — the three named sub-showcases, each hiding independently.
    `skip` drops specific module keys (used to de-dupe the Aura module when the BAN
    already IS the perception gap — avoids showing −37 then +37 right below)."""
    skip = skip or set()
    blocks: list[str] = []
    for sub_name, keys in _SHOWCASES:
        present = _present(player_data, [k for k in keys if k not in skip])
        if not present:
            continue
        mods = "".join(f'<div class="nmod">{h}</div>' for h in present)
        blocks.append(f'<div class="nshow"><p class="nshow__name">{escape(sub_name)}</p>{mods}</div>')
    if not blocks:
        return ""
    return f'<section class="nz"><h2 class="nz__h">3 · Showcases</h2>{"".join(blocks)}</section>'


def compose(summary: dict, player_data: dict) -> str:
    """Build the 7-section Noir body. Returns "" on any failure."""
    try:
        placed: set[str] = set(_CHROME_KEYS) | _SHOWCASE_KEYS
        parts: list[str] = [_hero(player_data)]

        # De-dupe: if the BAN already IS the perception gap (accent="aura"), don't
        # also show the standalone Aura module — it repeats the same number.
        story = _s(player_data.get("new_story_card_html"))
        ban_is_aura = 'data-ban-accent="aura"' in story
        showcase_skip = {"new_aura_html"} if ban_is_aura else set()

        # Dossier (2) first, then the named Showcases (3), then 4/5.
        for num, eyebrow, keys in _SECTIONS:
            present = _present(player_data, keys)
            placed.update(keys)
            if num == "2":  # the Dossier IS the story card — no wrapper chrome
                if present:
                    parts.append(f'<section class="nz"><p class="nz__eyebrow">2 · The Dossier</p>{present[0]}</section>')
                    parts.append(_showcases(player_data, showcase_skip))   # 3 follows the Dossier
                continue
            if num == "5":  # The Record leads with the traditional career stat table
                tables = _season_tables_html(player_data)
                if tables:
                    present = [tables] + present
            if not present:
                continue
            mods = "".join(f'<div class="nmod">{h}</div>' for h in present)
            parts.append(f'<section class="nz"><h2 class="nz__h">{num} · {escape(eyebrow)}</h2>{mods}</section>')

        # CATCH-ALL: any new_*_html not explicitly placed still renders in The Record,
        # so no module is ever silently lost (preservation rule).
        leftover = [
            _s(player_data.get(k)).strip()
            for k in player_data
            if isinstance(k, str) and k.startswith("new_") and k.endswith("_html")
            and k not in placed and _s(player_data.get(k)).strip()
        ]
        if leftover:
            mods = "".join(f'<div class="nmod">{h}</div>' for h in leftover)
            parts.append(f'<section class="nz"><h2 class="nz__h">5 · The Record (more)</h2>{mods}</section>')

        parts.append(_verdict(player_data))
        parts.append(_footer(player_data))
        return "".join(p for p in parts if p)
    except Exception:
        return ""
