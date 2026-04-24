"""Sprint-3 Season Arc editorial content.

Per program: one era-thesis sentence (opens the CFPEraView) + one closing
paragraph (caps the module). Written in voice register; Opus inline.
Persisted as team_season_narratives variants 'arc_thesis' and 'arc_closing'
with season_year = 0 (era-scope, not season-scope).
"""
from __future__ import annotations

import json
import sqlite3


THESIS: dict[str, str] = {
    "notre-dame": (
        "The CFP era is the one in which Notre Dame finally answered — and did not "
        "answer — the question that trails the program like a shadow: can they still "
        "be the standard they once were. 2024 was the answer they came closest to giving."
    ),
    "alabama": (
        "The Process era defined the CFP era. Six title games, three national "
        "championships, a standard the rest of the sport had to answer or be "
        "answered by. The Saban half has closed; the DeBoer half is being written."
    ),
    "ohio-state": (
        "Book-ended by the Ohio State that won the first CFP and the Ohio State that "
        "won the last one. The in-between was not dormant — it was the era in which the "
        "Midwest's standing answer never left the conversation long enough to be forgotten."
    ),
    "georgia": (
        "Chased the sentence for forty years, caught it in 2021, held it in 2022, "
        "and is in the part of the era where the argument is whether it can be built "
        "again. Between the 30-yard lines, the hunt never stops."
    ),
    "texas": (
        "Spent the early CFP era explaining what it used to be, and the last two "
        "years remembering present tense. A 12-team bracket, an SEC arrival, and the "
        "first two CFP bids since the format existed — the era the logo caught up with itself."
    ),
    "michigan": (
        "The longest stretch of CFP exclusion for a blueblood ended in 2021. The "
        "Harbaugh years turned into a title in 2023 and then into a rebuild. The era "
        "reads as the program proving it could still be where it belonged, and then "
        "leaving to see what comes after."
    ),
    "usc": (
        "The CFP era is the one USC watched from the outside. Sanction recovery, "
        "coaching shuffle, a move to the Big Ten — eleven seasons without a CFP bid "
        "is the story the program came to the new conference to start rewriting."
    ),
    "oregon": (
        "Opened with a title-game appearance against Ohio State in the first CFP. "
        "Spent a decade fast, fashionable, and mostly outside the bracket. Returned to "
        "the field in 2024 in a new conference — Big Ten day one, CFP seed day one — "
        "the era the program proved fast could still be serious."
    ),
    "penn-state": (
        "The Franklin era inside the CFP era. 2016 Rose Bowl, steady CFP conversation, "
        "a 2024 semifinal. The program that talks about the ceiling without ever quite "
        "touching it — and now talks about it with one less season of distance."
    ),
    "vanderbilt": (
        "The era Vanderbilt was not supposed to be in. Bowl games are the watermark; "
        "the program's CFP-era record is a genuine-program record, not a comeback-tour "
        "record. The 2024 season rewrote what the ceiling looked like from the SEC's bottom seed."
    ),
    "massachusetts": (
        "A full CFP era spent in the basement of the FBS trying to climb out of it. "
        "The Colonial Clash, the independent years, the MAC return — every season a "
        "rung on a ladder the program is still walking up."
    ),
}


CLOSING: dict[str, str] = {
    "notre-dame": (
        "The era reads like what the program always feared its history would read like — "
        "close, credible, one game short. The Freeman era is the part of the story that "
        "has decided 2024 was not a peak but a doorstep. Whether the next decade carries "
        "the program through the door is the era's argued question."
    ),
    "alabama": (
        "Nobody else won three titles inside the era. Nobody else appeared in seven "
        "national championships. The data reads what history will say: the CFP era was "
        "Alabama's era, and every other program spent twelve years being measured against it."
    ),
    "ohio-state": (
        "The program won the era's first title and the era's last. Six CFP bids, four "
        "title-game appearances, two championships — a decade of never being asked to "
        "prove the argument from scratch, because the program had already proved it."
    ),
    "georgia": (
        "Kirby Smart's Georgia wrote the era's back half — back-to-back 2021 and 2022 "
        "titles, a CFP run in every year of his tenure. The question the 2024 quarterfinal "
        "left open is the program's: does the next title run require rebuilding the 2021 "
        "formula, or starting a second one."
    ),
    "texas": (
        "Most of the CFP era Texas watched from a window — it's the rest of the story "
        "that matters. 2023 and 2024 are not a cycle; they are the first two seasons "
        "the program has owned inside this format, and the next five are what everyone's "
        "really watching."
    ),
    "michigan": (
        "The 2023 title was the sentence Harbaugh's return was built to write. The "
        "aftermath — the Moore era, a 2024 crisis season that read like the rebuild "
        "showed up before the program was ready — is the cost of the standard. Every "
        "era in Ann Arbor has a version of it."
    ),
    "usc": (
        "No other profiled program has a zero in the CFP column. The Big Ten move in 2024 "
        "was the structural bet that the next decade could be different — the era is the "
        "one where the program asked itself whether it could still be USC inside the "
        "argument, or only next to it."
    ),
    "oregon": (
        "The first CFP title-game appearance and the most recent CFP bid both belong to "
        "this program. The decade between them — four Pac-12 titles, a lot of fast "
        "offense, a little coaching turbulence — is the mid-arc of a program still "
        "deciding what 'fashionable' means at the top of the sport."
    ),
    "penn-state": (
        "The era reads as progress without the headline the program wants. 2024 is the "
        "first real brick — semifinal, a 3-brick-title-era badge on the ledger — but the "
        "argument about whether Franklin can build a title roster in Happy Valley has "
        "one more season at least before it is settled."
    ),
    "vanderbilt": (
        "The 2024 season is the sentence the program wanted to write, the one it will "
        "refer to for the rest of the decade. A Tennessee rivalry win, a ten-win bowl "
        "campaign, and the SEC's bottom-seed pedigree rewritten inside one calendar year "
        "— that is what era-shifting looks like from this register."
    ),
    "massachusetts": (
        "The era is the one the program walked through at its own pace. Every rung on "
        "the ladder had a cost, and every season had a version of itself that was honest "
        "about the math. Next chapter: whether independence or a conference is the "
        "structure the program uses to keep climbing."
    ),
}


def main() -> None:
    con = sqlite3.connect("cfb_rankings.db")
    cur = con.cursor()
    cur.execute(
        "select slug, team_id from teams where slug in (%s)"
        % ",".join("?" * len(THESIS)),
        list(THESIS.keys()),
    )
    slug_to_id = dict(cur.fetchall())
    n = 0
    for slug in THESIS:
        tid = slug_to_id.get(slug)
        if not tid:
            continue
        for variant, body in (("arc_thesis", THESIS[slug]), ("arc_closing", CLOSING[slug])):
            wc = len(body.split())
            cur.execute(
                """
                insert into team_season_narratives (
                  team_id, season_year, variant, title, body_md, attribution,
                  week_context, state_signature, model_id,
                  prompt_tokens, completion_tokens, generation_cost_usd,
                  is_published, generated_at_utc
                ) values (
                  :tid, 0, :v, NULL, :body, NULL,
                  0, :sig, 'claude-opus-4-7+sprint3-inline',
                  0, :ctok, 0.0, 1, current_timestamp
                )
                on conflict(team_id, season_year, variant, week_context) do update set
                  body_md = excluded.body_md,
                  model_id = excluded.model_id,
                  is_published = 1,
                  generated_at_utc = current_timestamp
                """,
                {
                    "tid": tid, "v": variant, "body": body,
                    "sig": json.dumps({"source": "sprint3_arc_inline"}),
                    "ctok": wc * 2,
                },
            )
            n += 1
    con.commit()
    print(f"Season Arc editorial: wrote {n} rows ({n // 2} programs × 2 variants)")
    con.close()


if __name__ == "__main__":
    main()
