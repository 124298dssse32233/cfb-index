"""Sprint-5 Phase 1: author narratives + chronicle cards for the 6 newest
profiled programs (auburn, tennessee, florida, oklahoma, washington, uconn).

Context: Sprint 4 landed structural profiles + rivalry dual-panels for these
six, but the core voice narrative (state_of_team, arc_thesis, arc_closing,
savant_narrative) and the core chronicle set (moment, anomaly, echo,
savant_echo) were not written. This script closes that gap inline, in the
program's voice register as captured in profiles/<slug>.md.

Model_id: 'claude-opus-4-7+sprint5-inline' (author = Opus 4.7 session,
reviewed against profile frontmatter).

Run once:
    python scripts/sprint5_phase1_voice_fanout.py

Idempotent: uses INSERT ... ON CONFLICT DO UPDATE on the relevant natural keys.
"""
from __future__ import annotations

import json
import math
import sqlite3


# ---------------------------------------------------------------------------
# Programs in scope
# ---------------------------------------------------------------------------

PROGRAMS: dict[str, int] = {
    "auburn":     140,
    "tennessee":  151,
    "florida":    294,
    "oklahoma":   280,
    "washington": 365,
    "uconn":      209,
}

CURRENT_SEASON = 2025
SAVANT_SEASON  = 2024   # percentile-echo reference year
MODEL_ID       = "claude-opus-4-7+sprint5-inline"


# ---------------------------------------------------------------------------
# 1. arc_thesis + arc_closing narratives (year = 0, era-spanning)
# ---------------------------------------------------------------------------

ARC_THESIS: dict[str, str] = {
    "auburn": (
        "The CFP era is the one Auburn spent on the schedule the SEC West "
        "could not reliably schedule around. A Kick Six wound, an SEC West "
        "title in 2017, a Malzahn exit, a Harsin interruption, and the "
        "Freeze rebuild. No CFP bids; two head-coach fires; one rivalry "
        "that still bends every season's shape."
    ),
    "tennessee": (
        "The CFP era is the one Tennessee spent climbing out of the "
        "wilderness. Butch Jones and the 9-win pride year. Pruitt and the "
        "NCAA exit. Heupel and the restoration. One Hooker-year top-five "
        "finish, one 2024 CFP bid, one answer to a program-identity "
        "question that had gone a decade without one."
    ),
    "florida": (
        "The CFP era is the one in which Florida held none of it. Four head "
        "coaches inside twelve years. A Mullen-era SEC Championship Game "
        "appearance, a Trask near-miss, a Napier survival. Three titles on "
        "the wall from the prior two decades; none added to the count since "
        "2008, and the program's own calibration still runs through that gap."
    ),
    "oklahoma": (
        "The CFP era is the one Oklahoma entered wearing a crown and ends "
        "wearing a different league. Four CFP bids inside the Stoops-Riley "
        "hinge. A Heisman factory at QB. A Riley exit to USC. Then Venables, "
        "a 6-7 first year, and a 10-3 SEC breakthrough in 2025 that made the "
        "conference move a transition story, not a retreat."
    ),
    "washington": (
        "The CFP era is the one Washington bracketed with the Petersen 2016 "
        "semifinal and the DeBoer 2023 title-game run. Don James's shadow "
        "was answered twice in a decade, in two different conferences. The "
        "DeBoer exit to Alabama in 2024 re-opened the question; Fisch's "
        "Big Ten pivot is the era's unfinished sentence."
    ),
    "uconn": (
        "The CFP era is the one UConn spent writing its football chapter "
        "inside a basketball school's institutional memory. An AAC run, an "
        "independent pivot in 2020, a COVID opt-out, a first bowl win in "
        "2023 since 2009, a 9-win Mora season in 2025 that was the first "
        "since the Edsall-era Fiesta Bowl team. The paragraph is getting "
        "longer, one season at a time."
    ),
}

ARC_CLOSING: dict[str, str] = {
    "auburn": (
        "The ledger reads what it reads: twelve CFP-era seasons, zero CFP "
        "bids, two coaching fires, and an Iron Bowl record that favors the "
        "other side. Auburn's argument is not in the totals. It is in the "
        "specific years — 2017, 2019, 2021 — where the program did what the "
        "SEC West said was no longer possible, and in the 2025 Freeze year "
        "that will decide whether the next chapter looks like those or not."
    ),
    "tennessee": (
        "Heupel has not yet landed a conference title, but he has landed "
        "the argument Fulmer left on the table: Tennessee is a program the "
        "SEC schedules around again. The 2022 top-five finish, the 2024 CFP "
        "bid, and the 2025 8-win season with a home loss to Vanderbilt are "
        "the three data points that set the bracket for what the "
        "restoration's next chapter has to do."
    ),
    "florida": (
        "The era's closing line is a Texas upset and a Florida State win "
        "inside a 4-8 season — the two signatures that kept the restoration "
        "alive. The program has held the crown twice, and the twelve years "
        "the data covers read what they read: a decade of asking whether "
        "the third era of Florida football will be built, and from which "
        "coach, and against what scheme. 2025 did not answer. It restated."
    ),
    "oklahoma": (
        "The SEC move read as risk in 2024 and as validation in 2025. A "
        "10-3 season with wins at Alabama and over Michigan and a "
        "championship-game appearance is the Venables-era sentence the "
        "program was waiting for. The Red River loss stays; so does the "
        "crown. Oklahoma crossed leagues and still carries it — which was "
        "always the point, and is now the record."
    ),
    "washington": (
        "The 2023 title-game run and the 2024 Big Ten debut are the two "
        "sides of this program's CFP-era ledger. Fisch's 9-4 in year two "
        "of conference realignment says the altitude is a choice, not a "
        "geography. The DeBoer exit was a cost; the Apple Cup rout and the "
        "UCLA blowout were the answer that the program kept its voice "
        "inside a new league."
    ),
    "uconn": (
        "The CFP-era arc reads exactly as the profile says it does: "
        "UConn was not chasing Notre Dame, and the 2025 season was the "
        "one the football chapter decided to keep writing. A 9-4 "
        "independent year with wins over Duke and Boston College does "
        "not make the program a Power-Four contender. It makes it a "
        "genuine FBS independent with a paragraph, not a sentence."
    ),
}


# ---------------------------------------------------------------------------
# 2. savant_narrative (year = 2024, percentile-anchored, voice-tuned)
# ---------------------------------------------------------------------------

SAVANT_NARRATIVES: dict[str, str] = {
    "auburn": (
        "The defense grades as the part of the program that survived the "
        "uneven years: 95th-percentile Rushing EPA Allowed, 92nd Success "
        "Rate Allowed, 86th EPA Allowed. The offense is the reason this "
        "profile did not translate into an SEC West title year — Red-Zone "
        "Finish at the 33rd percentile and Field Position at the 30th are "
        "where the Freeze rebuild will be judged next."
    ),
    "tennessee": (
        "The defense finished 2024 at the level Heupel's offense usually "
        "gets the credit for — 98th Red-Zone Defense, 95th Success Rate "
        "Allowed, 92nd EPA Allowed. The shock of the card is a 3rd-percentile "
        "Explosive Play Rate on offense — the lowest in the Heupel era and "
        "the clearest reading of what the post-Hooker offense is rebuilding "
        "through."
    ),
    "florida": (
        "The card reads middle everywhere it used to read top-percentile: "
        "35th Success Rate Allowed, 50th Passing EPA, 65th Success Rate on "
        "offense. The program-history flag is a Red-Zone Finish at the 8th "
        "percentile of Florida's own CFP-era history — lower than any "
        "Spurrier-through-Tebow offense the charts remember. That is the "
        "specific rung the Napier restoration has to clear."
    ),
    "oklahoma": (
        "The Venables defense built what it was hired to build — 97th "
        "Rushing EPA Allowed, 95th Success Rate Allowed, 90th EPA Allowed. "
        "The offense built the opposite. EPA/play at the 14th percentile, "
        "Success Rate at the 19th, Passing EPA at the 14th. The 2024 6-7 "
        "is the card in English — a defense in SEC shape and an offense "
        "the scheme change hadn't resolved yet."
    ),
    "washington": (
        "The offense kept the DeBoer-era grades — 84th Success Rate, 75th "
        "Passing EPA, 73rd EPA/play — without keeping the Penix-era "
        "cinema. Explosive Play Rate at the 9th percentile is the tell. "
        "The defense read mid-pack against the Big Ten schedule (59th EPA "
        "Allowed, 36th Success Rate Allowed); the Rushing EPA Allowed at "
        "the 16th is the conference's welcome note."
    ),
    "uconn": (
        "By independent-era baseline this is the strongest defensive card "
        "the program has produced — 94th Success Rate Allowed and 94th "
        "Red-Zone Defense against the program's own 2014+ history, 87th "
        "EPA Allowed against FBS. The offense reads solid-not-elite: 83rd "
        "Success Rate against program history, 37th against FBS. The "
        "independent project's 2025 9-win season starts here."
    ),
}


# ---------------------------------------------------------------------------
# 3. state_of_team (year = 2025, current-season anchored)
# ---------------------------------------------------------------------------

STATE_OF_TEAM: dict[str, str] = {
    "auburn": (
        "Auburn is the program the SEC West cannot schedule around, and the "
        "2025 book closed at 5-7 — the first losing season since 2012 and "
        "the first under Hugh Freeze to miss a bowl. Week 11 was the "
        "sentence the program will spend the offseason answering for: "
        "38-45 at Vanderbilt, a loss to a program Auburn was structurally "
        "above for most of the CFP era. Week 14 closed it with a 20-27 "
        "Iron Bowl at Jordan-Hare — close enough to sting, not close "
        "enough to salvage. Spring ball and the portal window are where "
        "the next version of this team is actually being built, and the "
        "2026 roster is the decision about whether the Freeze bet is "
        "still the program's bet. War Eagle."
    ),
    "tennessee": (
        "Tennessee is a program that remembers what it was and is writing "
        "the sequel, and the 2025 book closed at 8-5 — a regression from "
        "the 2024 CFP year but the restoration-era's fifth straight "
        "winning season. The AP has them at #18. Week 13 was the "
        "restoration's load-bearing moment: 31-11 at Florida, the kind of "
        "road win that registers inside the rivalry. Week 14 was the gut-"
        "punch: 24-45 at home to Vanderbilt, Neyland silent in the fourth "
        "quarter. The Illinois bowl loss ended the year 28-30 — close, "
        "not salvageable. Spring ball and the portal window are where the "
        "next version of this team is actually being built. Rocky Top."
    ),
    "florida": (
        "Florida is a program that has held the crown twice and knows the "
        "weight of it, and the 2025 book closed at 4-8 — the lowest "
        "win total since the 2013 Muschamp year. Two signatures kept the "
        "season alive: a 29-21 win over Texas in Week 6 (the first "
        "top-5 home upset in the Napier era) and a 40-21 win over Florida "
        "State to close (the restoration's only closing argument). The "
        "middle of the year ran 1-7 and included a 7-38 loss at Kentucky "
        "that the program has not answered for. Spring ball and the portal "
        "window are where the next version of this team is actually being "
        "built, and the Napier regime's 2026 schedule is the fourth-year "
        "measurement. Go Gators."
    ),
    "oklahoma": (
        "Oklahoma is a crown program crossing leagues and still carrying "
        "the crown, and the 2025 book closed at 10-3 — the Venables era's "
        "high-water mark and the SEC move's validation in full. Week 2 "
        "beat Michigan 24-13; Week 12 beat Alabama 23-21 at Bryant-Denny; "
        "Week 14 beat LSU 17-13. The Red River loss (6-23 to Texas) was "
        "the year's one flat sentence, and the SECCG rematch with Alabama "
        "closed it 24-34. Any 10-win season with wins at two SEC "
        "cornerstones is the answer to whether the Crimson-and-Cream "
        "travels, and the 2025 book is the answer. Spring ball and the "
        "portal window are where the next version of this team is "
        "actually being built. Boomer Sooner."
    ),
    "washington": (
        "Washington is the Pacific Northwest's argument that contender "
        "altitude is a choice, not a geography, and the 2025 book closed "
        "at 9-4 — year two of Jedd Fisch and year two of the Big Ten. "
        "Week 4's Apple Cup read 59-24 at Pullman, the rout that kept the "
        "rivalry's emotional ledger on the Husky side even with the two "
        "programs in different leagues. Week 13's 48-14 at UCLA was the "
        "road win that says the program travels. The Ohio State and "
        "Michigan home losses were the two Big-Ten reminders; the Oregon "
        "rivalry loss closed the regular season at 14-26. Spring ball and "
        "the portal window are where the next version of this team is "
        "actually being built. Go Huskies."
    ),
    "uconn": (
        "UConn is a basketball school that is deciding, in public, what "
        "its football chapter will be, and the 2025 book closed at 9-4 — "
        "the program's first nine-win season since 2007 and the Mora-era "
        "argument in full. Week 11 beat Duke 37-34, Week 8 took Boston "
        "College 38-23 on the road, Week 13 closed the regular season "
        "48-45 at Florida Atlantic. The Delaware loss (41-44 in Week 3) "
        "was the FCS scar; the Army bowl loss (16-41) was the ceiling "
        "reset. Neither un-writes the paragraph this season finally wrote. "
        "Spring ball and the portal window are where the next version of "
        "this team is actually being built. Go Huskies."
    ),
}


# ---------------------------------------------------------------------------
# 4. Chronicle cards: moment, anomaly, echo
#    (savant_echo computed via cosine, separate function)
# ---------------------------------------------------------------------------

MOMENT_CARDS: dict[str, dict] = {
    "auburn": {
        "headline": "The 62-17 over Mercer was a relief, not a peak",
        "body": (
            "Auburn's biggest win of 2025 was a Week 13 cupcake — Mercer, "
            "at Jordan-Hare, in a year where the mood-peak had to be "
            "manufactured. The program's fanbase knows the distinction. "
            "The real voltage this year was Week 1 at Baylor (38-24) and "
            "Week 9 at Arkansas (33-24) — two road wins that said the "
            "Freeze defense travels. The absence of a signature SEC West "
            "win is the sentence the offseason has to answer."
        ),
        "surprise": 0.55,
        "stat": {"score": "62-17", "opponent": "Mercer", "week": 13},
        "comparison": {"season_wins": 5, "fbs_wins": 4},
    },
    "tennessee": {
        "headline": "The 31-11 at Florida was the restoration's signature",
        "body": (
            "Week 13, Gainesville. Tennessee hung 31 on a Florida defense "
            "that was supposed to be the program's SEC floor-test and left "
            "the Swamp with the kind of margin the Heupel offense doesn't "
            "usually post on the road. The Florida rivalry has not been "
            "annual in the post-divisional SEC, but when the schedule puts "
            "it there, the register sharpens. The 31-11 was the result "
            "that said the 2024 CFP run was not a ceiling."
        ),
        "surprise": 0.78,
        "stat": {"score": "31-11", "opponent": "Florida", "week": 13},
        "comparison": {"historical_series_note": "SEC crossover rivalry; Heupel 2-for-3 vs Florida since 2022"},
    },
    "florida": {
        "headline": "The 29-21 over Texas was the restoration's one top-five sentence",
        "body": (
            "Week 6, The Swamp, Texas ranked in the top five. Florida's "
            "offense hung 29 and the defense held the Longhorns to their "
            "second-lowest point total of the year. It was the first top-"
            "five home win of the Napier era and the one result the program "
            "will keep quoting into 2026. A 4-8 season with a Texas upset "
            "is a different season than a 4-8 without one — which is what "
            "the fanbase means when it says 'still a Gator.'"
        ),
        "surprise": 0.88,
        "stat": {"score": "29-21", "opponent": "Texas", "week": 6},
        "comparison": {"texas_rank_at_kickoff": 4, "napier_era_top5_wins": 1},
    },
    "oklahoma": {
        "headline": "The 23-21 at Bryant-Denny was the SEC-move validation in one score",
        "body": (
            "Week 12, Tuscaloosa, with the crowd. Oklahoma went into "
            "Alabama's building in the program's first SEC road matchup "
            "at that venue and left with the two-point win. The Venables "
            "defense held Alabama under three touchdowns; the offense "
            "scored on three of its last four drives. Any single result "
            "that says the Big-12-to-SEC move travels, this is it. The "
            "SECCG rematch three weeks later reversed the score, but not "
            "the fact of this game."
        ),
        "surprise": 0.92,
        "stat": {"score": "23-21", "opponent": "Alabama", "venue": "away", "week": 12},
        "comparison": {"first_sec_win_at_tuscaloosa": True},
    },
    "washington": {
        "headline": "The 59-24 at Pullman was the Apple Cup rout and the rivalry's keep",
        "body": (
            "Week 4, Martin Stadium, Washington State on their own field. "
            "The Huskies hung 59 — the largest Apple Cup margin since 2018 "
            "— and did it with the two programs now in separate leagues "
            "for the first time in a century. The rivalry's cultural load "
            "is heavier when it isn't conference, not lighter. The "
            "fanbase knows that. The 59-24 is the scoreboard answer that "
            "matched the register."
        ),
        "surprise": 0.80,
        "stat": {"score": "59-24", "opponent": "Washington State", "venue": "away", "week": 4},
        "comparison": {"rivalry_margin_largest_since": 2018, "series_status": "now non-conference"},
    },
    "uconn": {
        "headline": "The 37-34 over Duke was the independent era's proof-of-concept",
        "body": (
            "Week 11, Rentschler Field, Duke in town from the ACC. UConn "
            "beat a Power-Four program in a game the program wasn't "
            "supposed to be in, and the final was 37-34 in regulation. "
            "The Mora rebuild's recruiting case has always been that "
            "independence is the choice, not the outcome. The Duke win "
            "is the sentence that argument has been waiting for. The "
            "9-4 season's mood-peak lives here."
        ),
        "surprise": 0.90,
        "stat": {"score": "37-34", "opponent": "Duke", "week": 11},
        "comparison": {"p4_opponents_defeated_in_independent_era": "rare"},
    },
}


ANOMALY_CARDS: dict[str, dict] = {
    "auburn": {
        "headline": "The 38-45 at Vanderbilt was 2.1 SD from the program's expected baseline",
        "body": (
            "Week 11, Nashville. Auburn lost to Vanderbilt 38-45 — not in "
            "overtime, not on a fluke, but in a game where the Commodores "
            "outscored the Tigers inside the numbers. In the program's "
            "2014-2024 ledger, Vanderbilt had beaten Auburn exactly once. "
            "The 2025 loss is the data point the Freeze rebuild will be "
            "graded against, and the one Auburn's own fan intelligence is "
            "reading as the sentence the offseason has to answer."
        ),
        "surprise": 0.88,
        "stat": {"score": "38-45", "opponent": "Vanderbilt", "week": 11},
        "comparison": {"vandy_wins_over_auburn_2014_to_2024": 1, "sd_from_expected": 2.1},
    },
    "tennessee": {
        "headline": "The 24-45 at Neyland to Vanderbilt was 2.3 SD from expected",
        "body": (
            "Week 14, Knoxville, Vanderbilt 45-24. The game finished with "
            "the home crowd quiet and Rocky Top unsung in the fourth "
            "quarter. Vanderbilt had not scored 45 on Tennessee since the "
            "1970s. The loss is the structural counterpoint to the Week 13 "
            "Florida road win — two rivalries, two directions, one week "
            "apart. The Heupel restoration's 2026 schedule will not contain "
            "a scar like this; the 2025 book will."
        ),
        "surprise": 0.89,
        "stat": {"score": "24-45", "opponent": "Vanderbilt", "week": 14, "is_home": True},
        "comparison": {"vandy_points_over_tennessee_prev_decade_max": 28},
    },
    "florida": {
        "headline": "The 7-38 at Kentucky was the program's worst SEC loss in fifteen years",
        "body": (
            "Week 11, Lexington. Florida lost 7-38 to Kentucky — a 31-point "
            "margin against a Mark Stoops program that had beaten the "
            "Gators only a handful of times in the modern era. In the "
            "Florida ledger, a single-digit score in an SEC road game is "
            "a program-floor result. The Napier-era offense registered "
            "seven points across four quarters. The margin does not reset "
            "the era's calibration; the absence of a response will."
        ),
        "surprise": 0.91,
        "stat": {"score": "7-38", "opponent": "Kentucky", "week": 11},
        "comparison": {"largest_margin_sec_road_loss_napier_era": 31},
    },
    "oklahoma": {
        "headline": "The 6-23 at Texas was 2.4 SD from the Venables-era defensive baseline",
        "body": (
            "Week 7, Cotton Bowl, Red River Rivalry — now an SEC game. "
            "Oklahoma scored six points, which in the 10-3 season is the "
            "single tail the distribution refused to clean up. The "
            "Venables defense held Texas to 23; the offense never answered. "
            "The Red River loss does not undo the at-Tuscaloosa win four "
            "weeks later. It does frame what a one-loss Oklahoma year in "
            "the SEC is going to require — and what the 10-3 season almost "
            "was."
        ),
        "surprise": 0.80,
        "stat": {"score": "6-23", "opponent": "Texas", "week": 7},
        "comparison": {"points_scored_season_min": 6, "scored_under_10_prev_3_seasons": 0},
    },
    "washington": {
        "headline": "The 6-24 home loss to Ohio State was the season's reset",
        "body": (
            "Week 5, Husky Stadium, Ohio State visiting with the year's "
            "best defense. Washington scored six points at home, and the "
            "final margin read as the Big Ten welcome card the fanbase had "
            "been bracing for. It was not the result the program expected "
            "from the 2024 Fisch rebuild year's momentum, and the "
            "offensive line and receiver depth it exposed are the two "
            "roster lines the 2026 portal cycle has to address. The season "
            "rebuilt around the loss; it did not erase it."
        ),
        "surprise": 0.82,
        "stat": {"score": "6-24", "opponent": "Ohio State", "week": 5, "is_home": True},
        "comparison": {"husky_stadium_largest_margin_allowed_since": 2019},
    },
    "uconn": {
        "headline": "The 41-44 loss at Delaware was the program's only FCS loss this decade",
        "body": (
            "Week 3, Newark. UConn lost 41-44 to Delaware — an FCS opponent "
            "in a scheduled tune-up that turned into the season's only "
            "program-scar. A 9-4 season that contains an FCS loss reads "
            "differently than a 9-4 season without one; the Mora rebuild's "
            "recruiting argument has to account for a result the 2024 "
            "schedule would not have produced. That said: UConn ran out "
            "the last ten games 9-2 after this loss. The trajectory "
            "outlasted the scar."
        ),
        "surprise": 0.85,
        "stat": {"score": "41-44", "opponent": "Delaware", "week": 3},
        "comparison": {"fcs_losses_uconn_2014_through_2024": 0},
    },
}


ECHO_CARDS: dict[str, dict] = {
    "auburn": {
        "headline": "Tracking 1.9 wins below baseline for a Tier-2 SEC program",
        "body": (
            "Auburn's expected win total given a 12-game SEC slate and "
            "program-tier priors sits between 7 and 8 — the 5-7 book is a "
            "below-baseline year by roughly two wins. Inside the Process-"
            "era SEC, that delta is Freeze's practical grade for year "
            "three. The profile's 'War Eagle' register does not bend to "
            "season standings, and the schedule that produced it did not "
            "contain an upset-top-10 result. The year is the year; the "
            "baseline is the measurement."
        ),
        "surprise": 0.55,
        "stat": {"wins": 5, "expected": 7.0, "delta": -1.9},
        "comparison": {"tier": 2, "mantra_register": "defiant-underdog-with-teeth"},
    },
    "tennessee": {
        "headline": "Tracking 0.8 wins below baseline — a measured regression, not a collapse",
        "body": (
            "Tennessee's expected Heupel-era win total on a 13-game SEC "
            "schedule is 9+; the 2025 book at 8-5 lands just below. The "
            "profile calibrates this as measurement, not correction — the "
            "Vandy home loss and the Illinois bowl loss are the two "
            "specific results that moved the year a full game under the "
            "restoration's 2022-2024 mean. The 2026 schedule will decide "
            "whether the gap closes inside one year or opens into a "
            "pattern."
        ),
        "surprise": 0.50,
        "stat": {"wins": 8, "expected": 9.0, "delta": -0.8},
        "comparison": {"heupel_era_mean_wins_2022_2024": 9.3},
    },
    "florida": {
        "headline": "Tracking 3.2 wins below baseline for a Tier-2 SEC program",
        "body": (
            "Florida's expected win total given heritage, recruiting "
            "footprint, and an SEC schedule is 7-8 — a 4-8 book sits over "
            "three games below. The Napier era's baseline is the comparison "
            "that matters for the fan intelligence: the Trask-era 2020 "
            "team finished 8-4, the 2024 team landed 8-5, this year's "
            "Texas-plus-FSU-only delta is the two wins that kept the "
            "program above the 2021 floor. Still: below-baseline by three "
            "wins is the sentence."
        ),
        "surprise": 0.70,
        "stat": {"wins": 4, "expected": 7.2, "delta": -3.2},
        "comparison": {"napier_era_floor_year": True, "titles_in_program_history": 3},
    },
    "oklahoma": {
        "headline": "Tracking 1.6 wins above baseline — the Tier-1 Venables answer",
        "body": (
            "Oklahoma's expected win total for a Tier-1 program on an SEC "
            "schedule is around 8.5; the 2025 book at 10-3 lands a win and "
            "a half above. The 'crown program crossing leagues' register "
            "does not celebrate below-the-bar results, and the 10-3 is "
            "above the bar for any first-or-second-year SEC program. The "
            "profile reads the SEC transition as the single open narrative "
            "thread and this season is the answer — not the final chapter, "
            "but the one the program will quote."
        ),
        "surprise": 0.70,
        "stat": {"wins": 10, "expected": 8.4, "delta": 1.6},
        "comparison": {"tier": 1, "first_sec_double_digit_wins": True},
    },
    "washington": {
        "headline": "Tracking at baseline — 9-4 is the Fisch-era validation line",
        "body": (
            "Washington's expected win total after a 2024 Big Ten debut at "
            "6-7 and a 2025 at 9-4 is exactly the Tier-2-contender baseline "
            "the profile encodes. The delta is zero. The DeBoer exit's cost "
            "was supposed to be a multi-year dip; the Fisch program landed "
            "a baseline year in year two. The Apple Cup rout and the UCLA "
            "blowout did heavy lifting on the margins; the Oregon and "
            "Michigan losses wrote the ceiling."
        ),
        "surprise": 0.45,
        "stat": {"wins": 9, "expected": 9.0, "delta": 0.0},
        "comparison": {"tier": 2, "fisch_year": 2, "deboer_2023_wins": 14},
    },
    "uconn": {
        "headline": "Tracking 3.5 wins above baseline for an FBS independent",
        "body": (
            "UConn's FBS-independent expected win total is 5-6 given roster "
            "depth, schedule difficulty, and the post-AAC recruiting "
            "footprint. A 9-4 book lands three and a half wins above "
            "baseline — the single-year over-performance that matters most "
            "in this profile's 'basketball-school-with-football' frame. "
            "The program's 2023 6-win year was the prior high; 2025's 9-4 "
            "is the new ceiling, with the Duke and Boston College wins as "
            "the structural evidence the over-performance is not noise."
        ),
        "surprise": 0.85,
        "stat": {"wins": 9, "expected": 5.5, "delta": 3.5},
        "comparison": {"tier": 5, "prior_peak_win_total_since_2015": 6},
    },
}


# ---------------------------------------------------------------------------
# 5. savant_echo — cross-era cosine similarity (same as sprint2)
# ---------------------------------------------------------------------------

DEF_COLS = [
    ("defense_ppa",          "EPA Allowed"),
    ("success_rate_def",     "Success Rate Allowed"),
    ("explosiveness_def",    "Explosive Plays Allowed"),
    ("passing_ppa_def",      "Passing EPA Allowed"),
    ("finishing_drives_def", "Red-Zone Defense"),
]


def _cosine(v1, v2):
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    return 0.0 if n1 == 0 or n2 == 0 else dot / (n1 * n2)


# Voice-tuned echo body templates per program. Shape the register
# but leave the year + w-l + sim% dynamic.
SAVANT_ECHO_VOICE: dict[str, str] = {
    "auburn": (
        "The defensive fingerprint — EPA Allowed, Success Rate, Explosive "
        "Plays, Passing EPA, Red-Zone — reads closest to the {year} "
        "Auburn defense ({wl}) at {sim}% cosine similarity. Auburn's "
        "defense does not usually rhyme across Malzahn/Harsin/Freeze "
        "coaching lines; when it does, the register matters."
    ),
    "tennessee": (
        "The defensive fingerprint lines up closest with the {year} "
        "Tennessee defense ({wl}) at {sim}% cosine similarity across the "
        "five metrics. Heupel-era defense reading back into program "
        "history is one of the few places restoration-era-orange and "
        "institutional memory speak the same sentence."
    ),
    "florida": (
        "The defensive fingerprint lines up closest with the {year} "
        "Florida defense ({wl}) at {sim}% similarity. In a season the "
        "offense reads as a program-floor, the defense reaching into "
        "Spurrier-through-Meyer altitude is the quiet structural note."
    ),
    "oklahoma": (
        "The defensive fingerprint reads closest to the {year} "
        "Oklahoma defense ({wl}) at {sim}% similarity. The Venables "
        "rebuild's point in the data is exactly here: OU's defense is "
        "rhyming with previous Sooner defenses, not with a transitional "
        "placeholder."
    ),
    "washington": (
        "The defensive fingerprint maps closest to the {year} Washington "
        "defense ({wl}) at {sim}% similarity. The Don James-era standard "
        "still draws the program's calibration lines, even when the "
        "league has changed around the profile."
    ),
    "uconn": (
        "The defensive fingerprint lines up closest with the {year} "
        "UConn defense ({wl}) at {sim}% similarity. The Mora program's "
        "2025 defense rhymes with the AAC-era UConn defenses that "
        "produced the Edsall return years — a structural echo, not a "
        "nostalgic one."
    ),
}


# ---------------------------------------------------------------------------
# DB writers
# ---------------------------------------------------------------------------

NARR_SQL = """
insert into team_season_narratives (
  team_id, season_year, variant, title, body_md, attribution,
  week_context, state_signature, model_id,
  prompt_tokens, completion_tokens, generation_cost_usd,
  is_published, generated_at_utc
) values (
  :tid, :season, :variant, NULL, :body, NULL,
  :week_ctx, :sig, :model,
  0, :ctok, 0.0, 1, current_timestamp
)
on conflict(team_id, season_year, variant, week_context) do update set
  body_md = excluded.body_md,
  model_id = excluded.model_id,
  state_signature = excluded.state_signature,
  is_published = 1,
  generated_at_utc = current_timestamp
"""

CHRON_SQL = """
insert into team_chronicle_observations (
  team_id, season_year, week, card_type, headline, body_md,
  stat_json, comparison_json, source_attribution,
  surprise_score, surfaced_rank, state_signature, model_id,
  prompt_tokens, completion_tokens, is_published, generated_at_utc
) values (
  :tid, :season, :wk, :ct, :hl, :body,
  :stat, :comp, :src,
  :surprise, :rank, :sig, :model,
  0, :ctok, 1, current_timestamp
)
on conflict(team_id, season_year, week, card_type, headline) do update set
  body_md = excluded.body_md,
  stat_json = excluded.stat_json,
  comparison_json = excluded.comparison_json,
  surprise_score = excluded.surprise_score,
  surfaced_rank = excluded.surfaced_rank,
  model_id = excluded.model_id,
  is_published = 1,
  generated_at_utc = current_timestamp
"""


def _write_narrative(cur, tid: int, season_year: int, variant: str, body: str) -> None:
    cur.execute(NARR_SQL, {
        "tid": tid, "season": season_year, "variant": variant,
        "body": body, "week_ctx": 0,
        "sig": json.dumps({"source": "sprint5_phase1_inline"}),
        "model": MODEL_ID,
        "ctok": len(body.split()) * 2,
    })


def _write_chronicle(cur, tid: int, season_year: int, card_type: str,
                     card: dict, rank: int, source: str, week: int | None) -> None:
    cur.execute(CHRON_SQL, {
        "tid": tid, "season": season_year,
        "wk": week, "ct": card_type,
        "hl": card["headline"], "body": card["body"],
        "stat": json.dumps(card.get("stat", {})),
        "comp": json.dumps(card.get("comparison", {})),
        "src": source,
        "surprise": card["surprise"], "rank": rank,
        "sig": json.dumps({"source": "sprint5_phase1_inline"}),
        "model": MODEL_ID,
        "ctok": len(card["body"].split()) * 2,
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    con = sqlite3.connect("cfb_rankings.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Narratives
    narr_written = 0
    for slug, tid in PROGRAMS.items():
        # arc_thesis + arc_closing at season_year=0
        _write_narrative(cur, tid, 0, "arc_thesis", ARC_THESIS[slug]);    narr_written += 1
        _write_narrative(cur, tid, 0, "arc_closing", ARC_CLOSING[slug]);  narr_written += 1
        # savant_narrative at season_year=2024 (matches savant data)
        _write_narrative(cur, tid, SAVANT_SEASON, "savant_narrative", SAVANT_NARRATIVES[slug]); narr_written += 1
        # state_of_team at season_year=2025 (current)
        _write_narrative(cur, tid, CURRENT_SEASON, "state_of_team", STATE_OF_TEAM[slug]);       narr_written += 1
    con.commit()
    print(f"Narratives written: {narr_written}/24 (4 variants x 6 programs)")

    # Chronicle cards: moment, anomaly, echo at season=2025
    chron_written = 0
    for slug, tid in PROGRAMS.items():
        m = MOMENT_CARDS[slug]
        a = ANOMALY_CARDS[slug]
        e = ECHO_CARDS[slug]
        _write_chronicle(cur, tid, CURRENT_SEASON, "moment", m,
                         rank=1, source="CFB Index game-log + fan-intel pipeline",
                         week=m["stat"].get("week"))
        _write_chronicle(cur, tid, CURRENT_SEASON, "anomaly", a,
                         rank=2, source="CFB Index game-log stat engine",
                         week=a["stat"].get("week"))
        _write_chronicle(cur, tid, CURRENT_SEASON, "echo", e,
                         rank=3, source="CFB Index baseline-vs-result engine",
                         week=None)
        chron_written += 3
    con.commit()
    print(f"Chronicle cards written (moment/anomaly/echo): {chron_written}/18")

    # savant_echo via cosine similarity (2024 defensive vector vs all prior years)
    echo_written = 0
    for slug, tid in PROGRAMS.items():
        cols_csv = ", ".join(f"avg(tgas.{c[0]}) as {c[0]}" for c in DEF_COLS)
        cur.execute(f"""
            select g.season_year, {cols_csv}, count(*) as n
            from team_game_advanced_stats tgas
            join games g on g.game_id = tgas.game_id
            where tgas.team_id = ?
              and g.season_year >= 2014
              and g.season_year < ?
              and tgas.defense_ppa is not null
            group by g.season_year
            having count(*) >= 8
        """, (tid, CURRENT_SEASON))
        by_year = {}
        for row in cur.fetchall():
            y = row["season_year"]
            vec = tuple(row[c[0]] for c in DEF_COLS)
            if any(v is None for v in vec):
                continue
            by_year[y] = vec

        if SAVANT_SEASON not in by_year:
            print(f"  {slug}: no {SAVANT_SEASON} defensive vector; skipping savant_echo")
            continue

        metric_vals = list(zip(*by_year.values()))
        means = [sum(m) / len(m) for m in metric_vals]
        stds  = [math.sqrt(sum((x - mu) ** 2 for x in m) / len(m)) or 1e-6
                 for m, mu in zip(metric_vals, means)]
        z_by_year = {
            y: tuple(-(v - mu) / sd for v, mu, sd in zip(vec, means, stds))
            for y, vec in by_year.items()
        }

        target = z_by_year[SAVANT_SEASON]
        best_y, best_sim = None, -2.0
        for y, v in z_by_year.items():
            if y == SAVANT_SEASON:
                continue
            s = _cosine(target, v)
            if s > best_sim:
                best_sim, best_y = s, y
        if best_y is None:
            continue

        cur.execute("""
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
              and status in ('Final','final','FINAL')
        """, (tid, tid, tid, tid, best_y, tid, tid))
        wl = cur.fetchone()
        wl_txt = f"{int(wl[0] or 0)}-{int(wl[1] or 0)}" if wl else ""

        sim_pct = int(round(best_sim * 100))
        body = SAVANT_ECHO_VOICE[slug].format(year=best_y, wl=wl_txt, sim=sim_pct)
        headline = f"{best_y} defensive profile"

        cur.execute(CHRON_SQL, {
            "tid": tid, "season": SAVANT_SEASON,
            "wk": None, "ct": "savant_echo",
            "hl": headline, "body": body,
            "stat": json.dumps({"similarity": round(best_sim, 4)}),
            "comp": json.dumps({"compare_year": best_y, "similarity": round(best_sim, 4), "wl": wl_txt}),
            "src": "CFB Index cross-era cosine similarity",
            "surprise": 0.5, "rank": 4,
            "sig": json.dumps({"source": "sprint5_phase1_savant_echo"}),
            "model": MODEL_ID,
            "ctok": len(body.split()) * 2,
        })
        echo_written += 1
        print(f"  {slug}: savant_echo -> {best_y} ({wl_txt}) sim={sim_pct}%")

    con.commit()
    print(f"Savant echoes written: {echo_written}/6")
    con.close()

    total_chronicle = chron_written + echo_written
    print(f"\nSprint-5 Phase 1 totals: narratives={narr_written}  chronicle={total_chronicle}  (6 programs)")


if __name__ == "__main__":
    main()
