"""Sprint-2: persist 11 Savant narrative headers + 11 defensive echoes.

Narratives are Opus-authored in-session (the 'claude-opus-4-7+sprint2-inline'
model_id flags this). Echoes are python-native cosine similarity across
defensive feature vectors from 2014+ program history.
"""
from __future__ import annotations

import json
import math
import sqlite3


NARRATIVES: dict[str, str] = {
    "notre-dame": (
        "The 2024 card reads exactly like the season did — Rushing EPA at the 96th, "
        "Red-Zone Finish at the 95th, Passing EPA Allowed at the 99th, and a defense "
        "that finished drives harder than anyone's. The title-game answer lives in a "
        "mid-tier Explosive Play Rate that never quite cracked open."
    ),
    "alabama": (
        "The Process still grades in the 90s against FBS — 96th EPA Allowed, 92nd "
        "Success Rate Allowed — but against Alabama's own 2014+ baseline it reads "
        "mid-tier. The concern is not the headline; it is a Red-Zone Finish at the "
        "8th percentile of the program's own history, which is where the title "
        "margin used to live."
    ),
    "ohio-state": (
        "Top-percentile in seven of thirteen: 99th EPA Allowed, 99th Red-Zone "
        "Defense, 99th EPA/play, 99th Passing EPA Allowed. This is what the Midwest's "
        "standing answer looks like in December — no single seam, no soft middle, "
        "and a ceiling the rest of the sport had to step inside of."
    ),
    "georgia": (
        "A dog-in-the-dirt profile: 77th Red-Zone Finish, 83rd Passing EPA Allowed, "
        "defense holding the line where it mattered. The unusual gap is the Explosive "
        "Play Rate at the 20th percentile — low for a program that used to lead the "
        "SEC there. The hunt, as ever, stays on between the 30-yard lines."
    ),
    "texas": (
        "The defense finally caught up to the logo — 99th Red-Zone Defense, 98th "
        "Explosive Plays Allowed, 98th EPA Allowed. The offense reads good-not-elite "
        "and the Rushing EPA sits at the 32nd percentile, which is the sentence Sark "
        "will be rewriting across spring before the next run at the sentence Texas "
        "is chasing."
    ),
    "michigan": (
        "The card says what Michigan tried not to — 25th Success Rate, 16th Red-Zone "
        "Finish, 4th Explosive Play Rate on offense. The defense held at a respectable "
        "71st EPA Allowed, which in Ann Arbor is the floor of a championship roster, "
        "not the ceiling. The offense is the thing that has to be rebuilt before the "
        "standard can hold."
    ),
    "usc": (
        "The offense reads in the 91st-percentile Success Rate while the defense "
        "gives up a 25th-percentile Success Rate Allowed — an imbalance a Big Ten "
        "schedule will find every week. The 98th-percentile Passing EPA by the USC "
        "offense is the headline; the defensive middle is the fix, and Fight On "
        "answers next."
    ),
    "oregon": (
        "97th Success Rate and 95th EPA/play say the offense hummed; the 23rd "
        "Explosive Play Rate says it hummed methodically, not cinematically. An 87th "
        "Passing EPA Allowed is the quiet reason the record landed where it did. Fast "
        "looked fashionable again — in the margins this time, not the highlights."
    ),
    "penn-state": (
        "Top-ten-percentile everywhere except Explosive Plays (17th) — 95th Success "
        "Rate, 94th Red-Zone Finish, 90th EPA/play. Defense tracks 88-92 across the "
        "core metrics. The card reads like the program Franklin has built, right "
        "down to the place where it breaks: a lack of chunk plays when the clock "
        "asks for them."
    ),
    "vanderbilt": (
        "By the program's own 2014+ history, the 85th-percentile Success Rate and "
        "EPA/play are a ceiling — the best Commodore offense the charts remember. "
        "Against FBS they read 48th and 45th, which is where bowl-eligible Vandy "
        "lives. The 14th-percentile Success Rate Allowed is the rung the defense "
        "has to clear next."
    ),
    "massachusetts": (
        "Middle of the FBS pack on offense (43rd Explosive Plays, 52nd Rushing EPA) "
        "is, by UMass's own 2014+ baseline, the 85th-to-95th-percentile version of "
        "itself. The card shows a rebuilding defense at the 15th FBS percentile in "
        "EPA Allowed and a program walking up the ladder one game at a time."
    ),
}


DEF_COLS: list[tuple[str, str]] = [
    ("defense_ppa",          "EPA Allowed"),
    ("success_rate_def",     "Success Rate Allowed"),
    ("explosiveness_def",    "Explosive Plays Allowed"),
    ("passing_ppa_def",      "Passing EPA Allowed"),
    ("finishing_drives_def", "Red-Zone Defense"),
]


def _cosine(v1: tuple[float, ...], v2: tuple[float, ...]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def main() -> None:
    SEASON = 2024
    con = sqlite3.connect("cfb_rankings.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    placeholders = ",".join(["?"] * len(NARRATIVES))
    cur.execute(
        f"select slug, team_id from teams where slug in ({placeholders})",
        list(NARRATIVES.keys()),
    )
    slug_to_id = dict(cur.fetchall())

    # ---- 1. Savant narratives -------------------------------------------
    wrote_n = 0
    for slug, body in NARRATIVES.items():
        tid = slug_to_id[slug]
        wc = len(body.split())
        if wc < 30 or wc > 75:
            print(f"  WARN {slug}: {wc} words")
        cur.execute(
            """
            insert into team_season_narratives (
              team_id, season_year, variant, title, body_md, attribution,
              week_context, state_signature, model_id,
              prompt_tokens, completion_tokens, generation_cost_usd,
              is_published, generated_at_utc
            ) values (
              :tid, :s, 'savant_narrative', NULL, :body, NULL,
              0, :sig, 'claude-opus-4-7+sprint2-inline',
              0, :ctok, 0.0, 1, current_timestamp
            )
            on conflict(team_id, season_year, variant, week_context) do update set
              body_md = excluded.body_md,
              model_id = excluded.model_id,
              is_published = 1,
              generated_at_utc = current_timestamp
            """,
            {
                "tid": tid, "s": SEASON, "body": body,
                "sig": json.dumps({"source": "sprint2_inline"}),
                "ctok": wc * 2,
            },
        )
        wrote_n += 1
    con.commit()
    print(f"Savant narratives: wrote {wrote_n}/11")

    # ---- 2. Defensive echoes (cross-era cosine) -------------------------
    echo_count = 0
    for slug, tid in slug_to_id.items():
        cols_csv = ", ".join(f"avg(tgas.{c[0]}) as {c[0]}" for c in DEF_COLS)
        cur.execute(
            f"""
            select g.season_year, {cols_csv}, count(*) as n
            from team_game_advanced_stats tgas
            join games g on g.game_id = tgas.game_id
            where tgas.team_id = ?
              and g.season_year >= 2014
              and tgas.defense_ppa is not null
            group by g.season_year
            having count(*) >= 3
            """,
            (tid,),
        )
        by_year: dict[int, tuple[float, ...]] = {}
        for row in cur.fetchall():
            y = row[0]
            vec = tuple(row[i + 1] for i in range(len(DEF_COLS)))
            if any(v is None for v in vec):
                continue
            by_year[y] = vec

        if SEASON not in by_year:
            print(f"  {slug}: no {SEASON} vector; skipping echo")
            continue

        metric_vals = list(zip(*by_year.values()))
        means = [sum(m) / len(m) for m in metric_vals]
        stds = [
            math.sqrt(sum((x - mu) ** 2 for x in m) / len(m)) or 1e-6
            for m, mu in zip(metric_vals, means)
        ]
        # Invert: defense is better when raw is lower, so negate z-score.
        z_by_year = {
            y: tuple(-(v - mu) / sd for v, mu, sd in zip(vec, means, stds))
            for y, vec in by_year.items()
        }

        target = z_by_year[SEASON]
        best_y: int | None = None
        best_sim = -2.0
        for y, v in z_by_year.items():
            if y == SEASON:
                continue
            s = _cosine(target, v)
            if s > best_sim:
                best_sim = s
                best_y = y
        if best_y is None:
            continue

        cur.execute(
            """
            select
              sum(case when
                 (home_team_id = ? and home_points > away_points) or
                 (away_team_id = ? and away_points > home_points)
                 then 1 else 0 end) as w,
              sum(case when
                 (home_team_id = ? and home_points < away_points) or
                 (away_team_id = ? and away_points < home_points)
                 then 1 else 0 end) as l
            from games
            where season_year = ?
              and (home_team_id = ? or away_team_id = ?)
              and status = 'Final'
            """,
            (tid, tid, tid, tid, best_y, tid, tid),
        )
        wl = cur.fetchone()
        wl_txt = f"{int(wl[0] or 0)}-{int(wl[1] or 0)}" if wl else ""

        headline = f"{best_y} defensive profile"
        sim_pct = int(round(best_sim * 100))
        body = (
            f"This year's defensive fingerprint — EPA Allowed, Success Rate, "
            f"Explosive Plays, Passing EPA, Red-Zone — lines up closest with the "
            f"{best_y} season ({wl_txt}) at {sim_pct}% cosine similarity across "
            f"the five metrics."
        )

        cur.execute(
            """
            insert into team_chronicle_observations (
              team_id, season_year, week, card_type, headline, body_md,
              stat_json, comparison_json, source_attribution,
              surprise_score, surfaced_rank, state_signature, model_id,
              prompt_tokens, completion_tokens, is_published, generated_at_utc
            ) values (
              :tid, :s, NULL, 'savant_echo', :h, :b,
              :stat, :comp, 'CFB Index cross-era cosine similarity',
              0.5, 1, :sig, 'python-native-cosine',
              0, 0, 1, current_timestamp
            )
            on conflict(team_id, season_year, week, card_type, headline) do update set
              body_md = excluded.body_md,
              comparison_json = excluded.comparison_json,
              is_published = 1,
              generated_at_utc = current_timestamp
            """,
            {
                "tid": tid, "s": SEASON, "h": headline, "b": body,
                "stat": json.dumps({"similarity": best_sim}),
                "comp": json.dumps({"compare_year": best_y, "similarity": best_sim, "wl": wl_txt}),
                "sig": json.dumps({"source": "sprint2_savant_echo"}),
            },
        )
        echo_count += 1
        print(f"  {slug}: echo -> {best_y} ({wl_txt}) sim={sim_pct}%")

    con.commit()
    print(f"Defensive echoes: wrote {echo_count}/11")
    con.close()


if __name__ == "__main__":
    main()
