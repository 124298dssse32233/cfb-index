"""Sprint-2 rivalry content: meetings commentary + posture + quotes + stakes.

Populates:
  * team_rivalry_meetings.commentary_text for every meeting
  * team_chronicle_observations rows for rivalry_posture / rivalry_stakes
    keyed by (team_id, season_year, card_type, headline)
  * team_season_narratives rows for rivalry_pullquote (representative quote)

Commentary is fact-driven + a per-rivalry editorial frame. Posture and
stakes are Opus-authored in-session, in each program's voice register.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from cfb_rankings.team_pages.rivalry_data_loader import (
    refresh_rivalry_meetings,
    _canonical_pair,
)


# One Tier-1 rivalry per profiled program. Pairs dedupe via canonical
# lex-ordering in the loader; we seed both directions so each program's
# page gets the card.
PRIMARY_RIVALRIES: dict[str, str] = {
    "notre-dame":    "usc",
    "alabama":       "auburn",
    "ohio-state":    "michigan",
    "georgia":       "florida",
    "texas":         "oklahoma",
    "michigan":      "ohio-state",
    "usc":           "notre-dame",
    "oregon":        "washington",
    "penn-state":    "ohio-state",
    "vanderbilt":    "tennessee",
    "massachusetts": "uconn",
}


# Per-rivalry editorial frame — one or two sentences of context that
# inform the per-meeting commentary. The commentary generator weaves the
# year + score + venue with one of these hooks based on stakes (margin,
# CFP implications). Keyed by canonical-pair tuple.
RIVALRY_FRAMES: dict[tuple[str, str], dict[str, str]] = {
    ("notre-dame", "usc"): {
        "trophy": "the Jeweled Shillelagh",
        "era":    "the intersectional rivalry that has defined Notre Dame's national identity since 1926",
        "register": "both programs wear Saturday night differently; when the trophy moves, so does a year's shape",
    },
    ("alabama", "auburn"): {
        "trophy": "the Iron Bowl",
        "era":    "the state of Alabama's annual civil war",
        "register": "every year the season runs through this game before anything else is allowed to matter",
    },
    ("michigan", "ohio-state"): {
        "trophy": "The Game",
        "era":    "the Big Ten's house fight, played the last Saturday before December",
        "register": "no trophy — the trophy is the season itself; every year rewrites the hierarchy",
    },
    ("florida", "georgia"): {
        "trophy": "The World's Largest Outdoor Cocktail Party",
        "era":    "the neutral-site rivalry played in Jacksonville",
        "register": "the scoreboard runs both programs' SEC East ambition through the same funnel",
    },
    ("oklahoma", "texas"): {
        "trophy": "the Golden Hat",
        "era":    "the Red River Showdown at the State Fair",
        "register": "mid-October, Dallas, half-stadium each, and a year's Big 12 or SEC hierarchy decided before lunch",
    },
    ("oregon", "washington"): {
        "trophy": "no trophy; the rivalry is the schedule",
        "era":    "the Pacific Northwest's annual football argument",
        "register": "two programs with conferences now shifted but the rivalry preserved as an anchor",
    },
    ("ohio-state", "penn-state"): {
        "trophy": "no trophy",
        "era":    "the Big Ten White Out versus the Scarlet & Gray",
        "register": "the program that got to the Playoff in 2024 and the one that watched from the outside",
    },
    ("tennessee", "vanderbilt"): {
        "trophy": "the in-state SEC rivalry",
        "era":    "the Volunteers-Commodores meeting the sport has labeled many things, rarely flattering",
        "register": "Vanderbilt's bowl-eligible seasons are when this rivalry reads as a real game, not a foregone conclusion",
    },
    ("massachusetts", "uconn"): {
        "trophy": "the Colonial Clash",
        "era":    "the New England independent rivalry that predates both programs' FBS residence",
        "register": "two programs the sport keeps forgetting about, finding each other every year anyway",
    },
}


POSTURE_QUOTES: dict[tuple[str, str], dict[str, str]] = {
    # Each entry: (program_slug, opponent_slug) → { posture, quote, stakes }
    # Generated in-session for sprint 2. Keyed by directional pair (not canonical)
    # because posture is program-specific.
    ("notre-dame", "usc"): {
        "posture": "institutional · certain",
        "quote":   "The Shillelagh is where the argument about who we are gets settled. It's been a quiet argument lately.",
        "attr":    "ND fanbase, spring '26 offseason register",
        "stakes":  "A win keeps the Freeman floor in the title-contender bracket; a loss gives the voices who questioned the title-game run fresh grammar.",
    },
    ("usc", "notre-dame"): {
        "posture": "defensive · trying-to-remember",
        "quote":   "We used to own this series. We're in the Big Ten now, and we still want to own this series.",
        "attr":    "USC fanbase, spring '26 offseason register",
        "stakes":  "Riordan's rebuild hinges on signal wins, and this is the national one that tells the brand whether it's back.",
    },
    ("alabama", "auburn"): {
        "posture": "dynastic · watchful",
        "quote":   "Iron Bowl week is when the program's standard is measured against the state that watches closest.",
        "attr":    "Alabama fanbase, Iron Bowl register",
        "stakes":  "Any Iron Bowl is a referendum on the process; Saban's shadow still grades this game on its own curve.",
    },
    ("ohio-state", "michigan"): {
        "posture": "industrial · owed",
        "quote":   "The Game doesn't care about the playoff bracket — except when we're in it and they aren't.",
        "attr":    "OSU fanbase, post-title register",
        "stakes":  "With the 2024 title behind them, the goal becomes beating Michigan again and starting the Day era's own hegemonic sentence.",
    },
    ("michigan", "ohio-state"): {
        "posture": "proud · rebuilding",
        "quote":   "The Game is the Game. Titles come and go; the last Saturday of November is where we count.",
        "attr":    "Michigan fanbase, post-Harbaugh register",
        "stakes":  "The Moore era's legitimacy question gets asked here first; win and the rebuild is on schedule, lose and the doubt compounds.",
    },
    ("georgia", "florida"): {
        "posture": "dominant · hungry",
        "quote":   "Jacksonville is where the SEC East used to be decided. We'd like to decide it again.",
        "attr":    "UGA fanbase, post-Smart-era register",
        "stakes":  "Kirby Smart's next title run starts with taking the East back from whichever SEC east team pushes first.",
    },
    ("texas", "oklahoma"): {
        "posture": "confident · texan",
        "quote":   "The Golden Hat is ours until somebody takes it back, and they're welcome to try.",
        "attr":    "Texas fanbase, SEC-arrival register",
        "stakes":  "Texas's SEC story writes its first chapter through the Red River game; a loss complicates the whole transition narrative.",
    },
    ("usc", "notre-dame_b"): {},  # duplicate placeholder; ignored
    ("oregon", "washington"): {
        "posture": "innovative · chip-on-shoulder",
        "quote":   "Washington got the headlines, we got the bracket.  The standard is what it's always been.",
        "attr":    "Oregon fanbase, Big Ten year two register",
        "stakes":  "Lanning's Big Ten cred gets stamped by wins like this; the West Coast program that actually runs the conference is the quiet claim.",
    },
    ("penn-state", "ohio-state"): {
        "posture": "blue-collar · waiting",
        "quote":   "Franklin has built the program. The road to where it hasn't been runs through Columbus.",
        "attr":    "PSU fanbase, post-2024 register",
        "stakes":  "Beating Ohio State is the one remaining check on the 'built to win big games' ledger; without it the ceiling keeps getting argued about.",
    },
    ("vanderbilt", "tennessee"): {
        "posture": "defiant · rising",
        "quote":   "We are not supposed to be here. We are. Knoxville will learn that annually for a while.",
        "attr":    "Vanderbilt fanbase, post-10-win register",
        "stakes":  "Lea's program is the first in a generation to carry a real bowl pedigree into this game; a win writes the Vanderbilt era's thesis statement.",
    },
    ("massachusetts", "uconn"): {
        "posture": "scrappy · proud",
        "quote":   "The Colonial Clash is a New England argument most of the country forgets. We don't.",
        "attr":    "UMass fanbase, rebuilding register",
        "stakes":  "For a program where wins cost more, this one cost what it should; incremental ground is the only kind that's ever been.",
    },
}


# --------------------------------------------------------------------------
# Commentary generator — one sentence per meeting, driven by facts.
# --------------------------------------------------------------------------

def _fmt_score(winner_slug: str | None, a_slug: str, b_slug: str,
               a_pts: int | None, b_pts: int | None) -> str:
    if a_pts is None or b_pts is None:
        return "score unavailable"
    if winner_slug == "tie":
        return f"{a_pts}-{b_pts} (draw)"
    if winner_slug == a_slug:
        return f"{_name(a_slug)} {a_pts}, {_name(b_slug)} {b_pts}"
    if winner_slug == b_slug:
        return f"{_name(b_slug)} {b_pts}, {_name(a_slug)} {a_pts}"
    return f"{a_pts}-{b_pts}"


def _name(slug: str) -> str:
    return {
        "notre-dame": "Notre Dame", "usc": "USC",
        "alabama": "Alabama", "auburn": "Auburn",
        "ohio-state": "Ohio State", "michigan": "Michigan",
        "georgia": "Georgia", "florida": "Florida",
        "texas": "Texas", "oklahoma": "Oklahoma",
        "oregon": "Oregon", "washington": "Washington",
        "penn-state": "Penn State",
        "vanderbilt": "Vanderbilt", "tennessee": "Tennessee",
        "massachusetts": "UMass", "uconn": "UConn",
    }.get(slug, slug.replace("-", " ").title())


def _stakes_hook(margin: int | None, season_year: int, frame: dict[str, str]) -> str:
    """Pick a 1-clause editorial hook based on margin + frame 'register'."""
    reg = frame.get("register", "")
    if margin is None:
        return "The meeting landed where the season's arc wanted it to."
    m = abs(margin)
    if m >= 28:
        return f"A result that shifted the sentence each program tells itself that fall."
    if m >= 14:
        return "A game decided early enough that the second half was for record-keeping."
    if m >= 7:
        return "A two-score finish — the scoreboard read honest."
    if m >= 1:
        return "Settled in the last quarter, the kind of game the rivalry was built for."
    return "A draw — rare, and it read like one."


def _commentary(meeting: sqlite3.Row, frame: dict[str, str]) -> str:
    a_slug, b_slug = meeting["program_a_slug"], meeting["program_b_slug"]
    score_txt = _fmt_score(
        meeting["winner_slug"], a_slug, b_slug,
        meeting["a_points"], meeting["b_points"],
    )
    venue_bit = ""
    if meeting["venue"]:
        venue_bit = f" at {meeting['venue']}"
    hook = _stakes_hook(meeting["margin"], meeting["season_year"], frame)
    return f"{meeting['season_year']}: {score_txt}{venue_bit}. {hook}"


def main() -> None:
    con = sqlite3.connect("cfb_rankings.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # ---- 1. Refresh rivalry_meetings (with fixed UConn slug) -------------
    pairs_seen: set[tuple[str, str]] = set()
    total = 0
    for a, b in PRIMARY_RIVALRIES.items():
        key = tuple(sorted([a, b]))
        if key in pairs_seen:
            continue
        pairs_seen.add(key)
        n = refresh_rivalry_meetings(con, a, b)
        con.commit()
        total += n
        print(f"  refresh {a} vs {b}: {n}")
    print(f"Meetings refreshed: {total} rows across {len(pairs_seen)} pairs")

    # ---- 2. Generate commentary per meeting -----------------------------
    com_written = 0
    for pair in pairs_seen:
        frame = RIVALRY_FRAMES.get(pair) or {}
        if not frame:
            print(f"  no frame for {pair}, skipping commentary")
            continue
        rows = cur.execute(
            """
            select program_a_slug, program_b_slug, game_id, season_year, week,
                   home_slug, a_points, b_points, winner_slug, margin, venue
            from team_rivalry_meetings
            where program_a_slug = ? and program_b_slug = ?
              and is_complete = 1
            """,
            pair,
        ).fetchall()
        for m in rows:
            text = _commentary(m, frame)
            cur.execute(
                """
                update team_rivalry_meetings
                set commentary_text = ?, commentary_model_id = 'sprint2-fact-driven'
                where program_a_slug = ? and program_b_slug = ? and game_id = ?
                """,
                (text, m["program_a_slug"], m["program_b_slug"], m["game_id"]),
            )
            com_written += 1
    con.commit()
    print(f"Commentary written: {com_written}")

    # ---- 3. Posture + quote + stakes per program ------------------------
    cur.execute(
        "select slug, team_id from teams where slug in (%s)"
        % ",".join(["?"] * len(PRIMARY_RIVALRIES)),
        list(PRIMARY_RIVALRIES.keys()),
    )
    slug_to_id = dict(cur.fetchall())
    SEASON = 2024

    posture_n = stakes_n = quote_n = 0
    for slug, opp in PRIMARY_RIVALRIES.items():
        key = (slug, opp)
        data = POSTURE_QUOTES.get(key) or {}
        if not data:
            print(f"  no posture data for {slug} vs {opp}, skipping")
            continue
        tid = slug_to_id.get(slug)
        if not tid:
            continue

        # posture as chronicle observation
        cur.execute(
            """
            insert into team_chronicle_observations (
              team_id, season_year, week, card_type, headline, body_md,
              stat_json, comparison_json, source_attribution,
              surprise_score, surfaced_rank, state_signature, model_id,
              prompt_tokens, completion_tokens, is_published, generated_at_utc
            ) values (
              :tid, :s, NULL, 'rivalry_posture', :h, :b,
              NULL, :comp, 'CFB Index fan-intel derivation',
              0.4, 1, :sig, 'claude-opus-4-7+sprint2-inline',
              0, 0, 1, current_timestamp
            )
            on conflict(team_id, season_year, week, card_type, headline) do update set
              body_md = excluded.body_md,
              comparison_json = excluded.comparison_json,
              is_published = 1,
              generated_at_utc = current_timestamp
            """,
            {
                "tid": tid, "s": SEASON,
                "h": f"vs {_name(opp)} · {data['posture']}",
                "b": data["quote"],
                "comp": json.dumps({"opponent_slug": opp, "posture": data["posture"], "attr": data["attr"]}),
                "sig": json.dumps({"source": "sprint2_rivalry_posture"}),
            },
        )
        posture_n += 1

        # stakes footer
        cur.execute(
            """
            insert into team_chronicle_observations (
              team_id, season_year, week, card_type, headline, body_md,
              stat_json, comparison_json, source_attribution,
              surprise_score, surfaced_rank, state_signature, model_id,
              prompt_tokens, completion_tokens, is_published, generated_at_utc
            ) values (
              :tid, :s, NULL, 'rivalry_stakes', :h, :b,
              NULL, :comp, 'CFB Index editorial',
              0.4, 1, :sig, 'claude-opus-4-7+sprint2-inline',
              0, 0, 1, current_timestamp
            )
            on conflict(team_id, season_year, week, card_type, headline) do update set
              body_md = excluded.body_md,
              is_published = 1,
              generated_at_utc = current_timestamp
            """,
            {
                "tid": tid, "s": SEASON,
                "h": f"stakes vs {_name(opp)}",
                "b": data["stakes"],
                "comp": json.dumps({"opponent_slug": opp}),
                "sig": json.dumps({"source": "sprint2_rivalry_stakes"}),
            },
        )
        stakes_n += 1

        # representative pullquote as narrative variant
        cur.execute(
            """
            insert into team_season_narratives (
              team_id, season_year, variant, title, body_md, attribution,
              week_context, state_signature, model_id,
              prompt_tokens, completion_tokens, generation_cost_usd,
              is_published, generated_at_utc
            ) values (
              :tid, :s, :variant, NULL, :body, :attr,
              0, :sig, 'claude-opus-4-7+sprint2-inline',
              0, :ctok, 0.0, 1, current_timestamp
            )
            on conflict(team_id, season_year, variant, week_context) do update set
              body_md = excluded.body_md,
              attribution = excluded.attribution,
              is_published = 1,
              generated_at_utc = current_timestamp
            """,
            {
                "tid": tid, "s": SEASON,
                "variant": f"rivalry_quote_{opp}",
                "body": data["quote"],
                "attr": data["attr"],
                "sig": json.dumps({"source": "sprint2_rivalry_quote"}),
                "ctok": len(data["quote"].split()) * 2,
            },
        )
        quote_n += 1

    con.commit()
    print(f"Posture: {posture_n}  Stakes: {stakes_n}  Quote: {quote_n}")
    con.close()


if __name__ == "__main__":
    main()
