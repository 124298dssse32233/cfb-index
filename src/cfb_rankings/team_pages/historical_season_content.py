"""Content generator for HistoricalSeasonDeepDive rows.

Two paths:

* **Template fallback** (``build_template_season``) — deterministic, no LLM.
  Pulls from the profile + arc row + games, produces a defensible title,
  thesis, 3 defining moments, pull quote, and legacy paragraph. Voice is
  tuned-but-generic; not a substitute for editorial.

* **LLM path** — the ``generate-historical-seasons`` CLI subcommand calls
  Opus for (season_title, season_thesis, legacy_paragraph) and Sonnet for
  defining_moments. Pull quotes try a contemporaneous-search prompt first;
  fall back to a synthesized quote tagged ``is_generated=True``.

The flagship-authored rows (Alabama 2020, Notre Dame 2024, etc.) live in
``historical_season_authored.py`` and are loaded first; template fallback
only runs for rows not in that authored set.
"""
from __future__ import annotations

import json
from typing import Any

from .profile_loader import Profile


# ------------------------------------------------------------------------
# Deterministic template fallback
# ------------------------------------------------------------------------

def build_template_season(
    profile: Profile,
    arc_row: dict[str, Any],
    games: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a complete, insert-ready row for (profile.slug, arc_row.season_year).

    Uses only structured inputs — no LLM. Suitable as an initial pass to get
    every profiled (slug, year) to render; Opus-authored content should then
    overwrite specific high-load seasons via the CLI path.
    """
    year = arc_row["season_year"]
    w = arc_row.get("wins") or 0
    l = arc_row.get("losses") or 0
    cfp = bool(arc_row.get("cfp_flag"))
    title_game = bool(arc_row.get("title_game_flag"))
    title_won = bool(arc_row.get("title_won_flag"))
    brick_state = arc_row.get("brick_state") or "baseline"
    ap_final = arc_row.get("ap_rank_final")

    is_gap = (w + l + (arc_row.get("ties") or 0) == 0)

    # ---------------- season_title ----------------
    if title_won:
        season_title = "The Crown"
    elif title_game:
        season_title = "One Game From It"
    elif cfp:
        season_title = "Into the Room"
    elif brick_state == "crisis":
        season_title = "The Correction"
    elif brick_state == "current":
        season_title = "The Chapter Being Written"
    elif ap_final and ap_final <= 10:
        season_title = "The Top-10 Year"
    elif w >= 10:
        season_title = "The Ten-Win Year"
    elif w >= 8:
        season_title = "The Winning Chapter"
    elif is_gap:
        season_title = "The Preserved Chapter"
    else:
        season_title = f"The {year} Season"

    # ---------------- season_thesis ----------------
    identity = profile.identity_phrase or ""
    if title_won:
        season_thesis = (
            f"{profile.program_name} closed the {year} season with the sport's final answer. "
            f"The crown did not move; it returned to a program that has carried it before."
        )
    elif title_game:
        season_thesis = (
            f"{profile.program_name} reached the final Monday of the {year} season and left without the crown. "
            f"The distance between the semifinal and the trophy is the chapter's subject."
        )
    elif cfp:
        season_thesis = (
            f"The {year} season put {profile.program_name} in the room where the sport ends. "
            f"The room did not open further; the invitation is the chapter."
        )
    elif brick_state == "crisis":
        season_thesis = (
            f"{year} is a losing-side chapter for {profile.program_name}. "
            f"The program metabolises it; the voice does not apologize."
        )
    elif brick_state == "current":
        season_thesis = f"The {year} season is in progress. This chapter is still being written."
    elif ap_final and ap_final <= 10:
        season_thesis = (
            f"{profile.program_name} finished {year} inside the final AP top-10. "
            f"The top-10 is the tier the program calibrates annual expectation against."
        )
    elif is_gap:
        season_thesis = (
            f"The per-game record for {profile.program_name}'s {year} season is preserved from canonical history. "
            f"What is documented here is the outcome; what is not is the week-by-week shape."
        )
    else:
        season_thesis = (
            f"{profile.program_name}'s {year} season ({w}-{l}) is a middle chapter: "
            f"table-stakes progress, no crown in the ledger, the program still writing the book."
        )

    # ---------------- defining moments ----------------
    moments = _template_moments(profile, arc_row, games)

    # ---------------- pull quote ----------------
    pull_quote = _template_pull_quote(profile, arc_row)

    # ---------------- legacy paragraph ----------------
    if title_won:
        legacy = (
            f"{profile.program_name}'s {year} title is one of the program's dated lines on the era ledger. "
            f"Future seasons are measured against it; future coaches against the staff that won it; "
            f"future rosters against the one that stood on the final Monday."
        )
    elif title_game:
        legacy = (
            f"The {year} title-game trip is part of {profile.program_name}'s modern ledger. "
            f"The loss does not vacate the trip; the trip does not vacate the loss. The chapter sits in the peak tier "
            f"of the era's observable arc."
        )
    elif cfp:
        legacy = (
            f"The {year} CFP appearance is part of the record {profile.program_name} brings to every subsequent "
            f"season. The bid is structural; the exit is a data point; the chapter is honest about both."
        )
    elif brick_state == "crisis":
        legacy = (
            f"{year} sits in {profile.program_name}'s crisis ledger. The program does not moralise it. "
            f"The next season begins the day this one ended and the crisis chapter closes when the ledger does."
        )
    elif is_gap:
        legacy = (
            f"This chapter of {profile.program_name}'s {year} season is preserved from the program's canonical "
            f"record. The per-game shape is not available; the outcome and the era's place for it are."
        )
    else:
        legacy = (
            f"{year} is a middle chapter for {profile.program_name} — neither a crown year nor a crisis. "
            f"It is the kind of season that fills the ledger between the named ones and gives the arc its shape."
        )

    return {
        "team_slug": profile.slug,
        "season_year": year,
        "season_title": season_title,
        "season_thesis": season_thesis,
        "defining_moments_json": json.dumps(moments, ensure_ascii=False),
        "pull_quote_json": json.dumps(pull_quote, ensure_ascii=False) if pull_quote else None,
        "legacy_paragraph": legacy,
        "gap_year_flag": 1 if is_gap else 0,
        "model_id": "template-fallback",
    }


def _template_moments(
    profile: Profile,
    arc_row: dict[str, Any],
    games: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Three {type, register, body} moment cards drawn from the game log + arc row."""
    year = arc_row["season_year"]
    out: list[dict[str, str]] = []
    team_id = profile.team_id or 0

    if not games:
        # Gap-year minimum set
        if bool(arc_row.get("title_won_flag")):
            out.append({
                "type": "triumph",
                "register": "triumph",
                "body": f"{profile.program_name} won the {year} national championship. The title sits in the canonical record even where per-game ingest is incomplete.",
            })
        elif bool(arc_row.get("title_game_flag")):
            out.append({
                "type": "near-miss",
                "register": "turning-point",
                "body": f"{profile.program_name} reached the {year} national championship game and lost the decider. The trip is preserved; the outcome is documented.",
            })
        elif bool(arc_row.get("cfp_flag")):
            out.append({
                "type": "appearance",
                "register": "turning-point",
                "body": f"{profile.program_name} earned a {year} CFP bid. The selection is the chapter's load-bearing artifact.",
            })
        out.append({
            "type": "gap",
            "register": "shift",
            "body": "Per-game data is unavailable for this season in the current ingest. The chapter is preserved from canonical record.",
        })
        return out

    # Highest-margin win
    wins_by_margin: list[tuple[int, dict[str, Any]]] = []
    losses_by_margin: list[tuple[int, dict[str, Any]]] = []
    for g in games:
        is_home = int(g["home_team_id"]) == team_id
        tp = g["home_points"] if is_home else g["away_points"]
        op = g["home_points"] if not is_home else g["away_points"]
        if tp is None or op is None:
            continue
        margin = int(tp) - int(op)
        if margin > 0:
            wins_by_margin.append((margin, g))
        elif margin < 0:
            losses_by_margin.append((margin, g))

    wins_by_margin.sort(key=lambda x: x[0], reverse=True)
    losses_by_margin.sort(key=lambda x: x[0])

    def _opp(g: dict[str, Any]) -> str:
        is_home = int(g["home_team_id"]) == team_id
        return str((g["away_name"] if is_home else g["home_name"]) or "an opponent")

    if wins_by_margin:
        m, g = wins_by_margin[0]
        tp = g["home_points"] if int(g["home_team_id"]) == team_id else g["away_points"]
        op = g["home_points"] if int(g["home_team_id"]) != team_id else g["away_points"]
        out.append({
            "type": "statement",
            "register": "triumph",
            "body": f"The {year} season's largest margin: {profile.program_name} {tp}, {_opp(g)} {op}. A {abs(int(m))}-point win anchoring the year's ceiling.",
        })
    if losses_by_margin:
        m, g = losses_by_margin[0]
        tp = g["home_points"] if int(g["home_team_id"]) == team_id else g["away_points"]
        op = g["home_points"] if int(g["home_team_id"]) != team_id else g["away_points"]
        out.append({
            "type": "setback",
            "register": "crash",
            "body": f"The season's deepest loss: {profile.program_name} {tp}, {_opp(g)} {op}. A {abs(int(m))}-point margin the chapter carries forward.",
        })

    # Postseason result
    post = [g for g in games if g.get("season_type") == "postseason"]
    if post:
        last = post[-1]
        is_home = int(last["home_team_id"]) == team_id
        tp = last["home_points"] if is_home else last["away_points"]
        op = last["home_points"] if not is_home else last["away_points"]
        opp = _opp(last)
        won = tp is not None and op is not None and tp > op
        out.append({
            "type": "postseason",
            "register": "turning-point" if not won else "triumph",
            "body": (
                f"The season's last act: {profile.program_name} {'beat' if won else 'fell to'} {opp} {tp}-{op} in the postseason. "
                f"The bowl / CFP result closes the chapter's arc."
            ),
        })

    if not out:
        out.append({
            "type": "aggregate",
            "register": "shift",
            "body": f"{profile.program_name} finished {arc_row.get('wins',0)}-{arc_row.get('losses',0)} in {year}. The season's defining moment is aggregate.",
        })

    return out[:3]


def _template_pull_quote(profile: Profile, arc_row: dict[str, Any]) -> dict[str, Any] | None:
    """Deterministic pull-quote placeholder — marked ``is_generated=True``.

    Pulls from the profile's own voice so at least the register matches.
    Opus-backed generation replaces this with a contemporaneous or a
    carefully-synthesized quote.
    """
    stock = profile.stock_phrases
    if not stock:
        return None
    text = stock[0]
    return {
        "text": text,
        "source": f"{profile.program_name} fanbase voice",
        "date": f"{arc_row.get('season_year') or ''}",
        "is_generated": True,
    }
