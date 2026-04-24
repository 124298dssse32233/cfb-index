"""Sprint-4 addendum to sprint2_rivalry_content: write posture/quote/stakes
rows for the OPPOSITE side of each Tier-1 rivalry, now that 6 new profiles
(Auburn, Tennessee, Florida, Oklahoma, Washington, UConn) exist.

Before Sprint 4, the sprint2 script wrote content only from the 11 original
programs' direction. The rivalry card's dual-panel rendering pulls the
opponent panel from the opponent's own posture row, which didn't exist for
programs that weren't profiled. Now that they are, these 6 directional
entries are the final piece that makes the dual panel carry voice on both
sides.

Voice register notes:
* auburn→alabama — defiant-underdog-with-teeth. Iron Bowl is the year.
* tennessee→vanderbilt — restoration-era-orange. In-state annual.
* florida→georgia — fallen-dynasty-rebuilding. Jacksonville / Cocktail Party.
* oklahoma→texas — crown-program-in-transition. Golden Hat / Red River.
* washington→oregon — edge-case-contender. Pac-to-Big-Ten, old neighborhood.
* uconn→massachusetts — basketball-school-with-football. Colonial quiet.
"""
from __future__ import annotations

import json
import sqlite3


OPPOSITE_POSTURE: dict[tuple[str, str], dict[str, str]] = {
    ("auburn", "alabama"): {
        "posture": "defiant · state-claimant",
        "quote": "The ledger favors them. The state is still ours half the time, and the eagle still flies before the ball is kicked.",
        "attr": "Auburn fanbase, Iron Bowl register",
        "stakes": "The Iron Bowl's emotional economy doesn't move with the ledger; a win rewrites the whole season and a loss shortens Freeze's runway.",
    },
    ("florida", "georgia"): {
        "posture": "proud · rebuilding",
        "quote": "Jacksonville is still Jacksonville. The Okefenokee argument is older than either program's current regime and it will outlast them.",
        "attr": "Florida fanbase, Napier-era register",
        "stakes": "Napier's Florida story writes its chapter through this game; a win in Jacksonville signals the restoration has traction.",
    },
    ("oklahoma", "texas"): {
        "posture": "crown-bearing · relocated",
        "quote": "The Golden Hat belongs to whoever wins it on the second Saturday. It has rarely stayed quiet at the Cotton Bowl.",
        "attr": "Oklahoma fanbase, SEC-debut register",
        "stakes": "The Red River game is now an SEC title-path indicator; Venables' program validates or invalidates the 2024 move here.",
    },
    ("washington", "oregon"): {
        "posture": "steady · neighborly",
        "quote": "The Apple Cup got a new conference and so did this one. The lake doesn't move. Neither do we.",
        "attr": "Washington fanbase, Big Ten year-two register",
        "stakes": "Fisch's inherited program proves its Big Ten bona fides against Oregon annually; the rivalry's national visibility is the new baseline.",
    },
    ("tennessee", "vanderbilt"): {
        "posture": "dominant · annoyed",
        "quote": "In-state means we always show up. The ledger says so. We'd like the ledger to keep saying so, please.",
        "attr": "Tennessee fanbase, Heupel-restoration register",
        "stakes": "Vanderbilt's 2024 resurgence raised the stakes of an annual game that used to be a foregone conclusion; the Vols' response is the season's quiet plotline.",
    },
    ("uconn", "massachusetts"): {
        "posture": "quiet · dual-identity",
        "quote": "Both teams are Huskies. One of us is named for the other's cousin. The game doesn't need fireworks to count.",
        "attr": "UConn fanbase, independence-era register",
        "stakes": "For UConn, the Colonial Clash is the closest thing to a conference rivalry the schedule offers; the season's emotional weight lives here.",
    },
}


def _name(slug: str) -> str:
    return {
        "alabama": "Alabama", "auburn": "Auburn",
        "georgia": "Georgia", "florida": "Florida",
        "texas": "Texas", "oklahoma": "Oklahoma",
        "oregon": "Oregon", "washington": "Washington",
        "tennessee": "Tennessee", "vanderbilt": "Vanderbilt",
        "massachusetts": "Massachusetts", "uconn": "UConn",
    }.get(slug, slug.replace("-", " ").title())


SEASON = 2024


def main() -> None:
    con = sqlite3.connect("cfb_rankings.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Resolve slug -> team_id for the 6 new programs
    slugs = [s for (s, _) in OPPOSITE_POSTURE.keys()]
    placeholders = ",".join(["?"] * len(slugs))
    cur.execute(
        f"select slug, team_id from teams where slug in ({placeholders})",
        slugs,
    )
    slug_to_id = dict(cur.fetchall())

    posture_n = stakes_n = quote_n = 0
    for (slug, opp), data in OPPOSITE_POSTURE.items():
        tid = slug_to_id.get(slug)
        if not tid:
            print(f"  skip {slug}: team not found")
            continue

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
              0.4, 1, :sig, 'claude-opus-4-7+sprint4-inline',
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
                "sig": json.dumps({"source": "sprint4_rivalry_opposite_posture"}),
            },
        )
        posture_n += 1

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
              0.4, 1, :sig, 'claude-opus-4-7+sprint4-inline',
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
                "sig": json.dumps({"source": "sprint4_rivalry_opposite_stakes"}),
            },
        )
        stakes_n += 1

        cur.execute(
            """
            insert into team_season_narratives (
              team_id, season_year, variant, title, body_md, attribution,
              week_context, state_signature, model_id,
              prompt_tokens, completion_tokens, generation_cost_usd,
              is_published, generated_at_utc
            ) values (
              :tid, :s, :variant, NULL, :body, :attr,
              0, :sig, 'claude-opus-4-7+sprint4-inline',
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
                "sig": json.dumps({"source": "sprint4_rivalry_opposite_quote"}),
                "ctok": len(data["quote"].split()) * 2,
            },
        )
        quote_n += 1

    con.commit()
    print(f"Sprint 4 opposite rivalry: posture={posture_n} stakes={stakes_n} quote={quote_n}")
    con.close()


if __name__ == "__main__":
    main()
