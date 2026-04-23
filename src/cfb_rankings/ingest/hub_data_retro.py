"""Retro offseason Hub seed data for Issues N° 038 through N° 047.

These rows are intentionally editorial/curated. Phase B can promote individual
rows to computed values under audit, but Phase A never presents these numbers as
live conversation measurements.
"""

from __future__ import annotations

import json
from typing import Any

from cfb_rankings.db import Database
from cfb_rankings.ingest.hub_data import (
    ISSUE_047,
    LEXICON_SECONDARY_047,
    LEXICON_SEED_047,
    MOOD_SEED_047,
    RIVALRY_SEED_047,
)


SEASON_YEAR = 2025
RETRO_BANNER = "RETROACTIVE — reconstructed from the public record. See methodology."

SOURCE_URLS = {
    "championship": "https://www.ncaa.com/live-updates/football/fbs/indiana-defeats-miami-win-college-football-playoff-national-championship-game",
    "cfp_recap": "https://collegefootballplayoff.com/news/2026/1/19/NCG-recap.aspx",
    "coaching": "https://www.cbssports.com/college-football/news/2026-college-football-coaching-carousel-grades-michigan-kyle-whittingham-lane-kiffin/",
    "portal": "https://www.pff.com/news/college-football-transfer-portal-tracker-2026",
    "portal_numbers": "https://www.ncaa.com/news/football/article/2026-01-16/10-numbers-breaking-down-2026-college-football-transfer-portal",
    "recruiting": "https://www.cbssports.com/college-football/news/college-football-recruiting-rankings-2026-early-national-signing-day/",
    "spring_schedule": "https://www.on3.com/news/tracking-2026-college-football-spring-practice-schedules/",
    "spring_games": "https://www.si.com/college-football/every-power-conference-spring-game-schedule-2026",
    "michigan_spring": "https://gbmwolverine.com/michigan-has-qb-problem-post-spring-game-kyle-whittingham-may-not-want-to-admit",
    "draft": "https://en.wikipedia.org/wiki/2026_NFL_draft",
}


def _methodology(label: str, sources: int = 3) -> dict[str, list[str]]:
    base = [
        f"curated — {sources} editorial sources",
        "sample withheld",
        "source: Jan-Apr public record",
        label,
    ]
    return {
        "cover": base,
        "mood_index": ["editorial seed", "Mood Index annotated from event ledger", "sample withheld", label],
        "mood_ticker": ["editorial seed", "affected teams only", "sample withheld", label],
        "hype_reality": ["editorial seed", "belief vs public-record team arc", "sample withheld", label],
        "rivalry": ["editorial seed", "rivalry ratios curated from issue ledger", "sample withheld", label],
        "lexicon": ["editorial seed", "phrase selected by editor", "sample withheld", label],
        "cards": base,
    }


def _card(team_abbr: str, color: str, headline: str, number: str, label: str, punchline: str) -> dict[str, Any]:
    return {
        "team_abbr": team_abbr,
        "team_color": color,
        "headline": headline,
        "stat_number": number,
        "stat_label": label,
        "punchline": punchline,
        "source": "editorial",
    }


def _make_issue(
    *,
    number: str,
    date: str,
    week_start: str,
    model_week: int,
    title: str,
    headline: str,
    dek: str,
    caption: str,
    note: str,
    quote: str,
    commiseration_slug: str,
    commiseration_eyebrow: str,
    commiseration_body: str,
    slug: str,
    sources: list[str],
    cards: list[dict[str, Any]],
) -> dict[str, Any]:
    issue_number = f"N° {number}"
    return {
        "issue_number": issue_number,
        "issue_date": date,
        "week_start_date": week_start,
        "model_week": model_week,
        "cover_headline": headline,
        "cover_dek": dek,
        "cover_chart_caption": caption,
        "editor_note_body": note,
        "cover_pull_quote": quote,
        "pull_quote": quote,
        "commiseration_team_slug": commiseration_slug,
        "commiseration_eyebrow": commiseration_eyebrow,
        "commiseration_body": commiseration_body,
        "cards": cards,
        "methodology": _methodology(f"Issue {issue_number}", sources=len(sources)),
        "methodology_row_json": json.dumps(_methodology(f"Issue {issue_number}", sources=len(sources))),
        "mood_index_dek": "Confidence scores curated from the official Jan-Apr event record.",
        "source": "editorial",
        "retro_title": title,
        "retro_slug": slug,
        "sources": sources,
    }


ISSUE_038 = _make_issue(
    number="038",
    date="19 Jan 2026",
    week_start="2026-01-19",
    model_week=22,
    title="Perfect Hoosiers",
    headline="Indiana did the impossible and made it look procedural.",
    dek="The Hoosiers finish 16-0, Miami gets the cruel ending, and the Big Ten belief economy resets overnight.",
    caption="Indiana's title-week belief spike is shown as a curated retro seed until the Jan. 19 backfill clears calibration.",
    note="This issue reconstructs championship week from the public event ledger. The mood numbers are editorial seeds, not live Reddit measurements.",
    quote="The sport spent four months asking when Indiana would blink. Indiana never blinked.",
    commiseration_slug="miami",
    commiseration_eyebrow="Miami",
    commiseration_body="Miami was close enough to picture the parade and far enough away to spend the winter relitigating one interception.",
    slug="perfect-hoosiers",
    sources=[SOURCE_URLS["championship"], SOURCE_URLS["cfp_recap"]],
    cards=[
        _card("IU", "#990000", "Perfect Hoosiers", "+30", "Indiana mood delta after 16-0", "The bandwagon became a census."),
        _card("MIA", "#F47321", "The Door Slams", "-20", "Miami title-week mood delta", "Cristobal discourse survived the confetti."),
        _card("IU", "#990000", "The Pick", ":44", "Sharpe interception timestamp", "The offseason began on a takeaway."),
    ],
)

ISSUE_039 = _make_issue(
    number="039",
    date="26 Jan 2026",
    week_start="2026-01-26",
    model_week=23,
    title="Portal Wave Peaks",
    headline="The portal closed, but the aftershocks kept moving.",
    dek="Raiola-to-Oregon changes two fanbases at once: Eugene gets a second future, Nebraska gets a fresh scar.",
    caption="Portal-week mood movement is curated from the Jan. 16 close and the week of reaction that followed.",
    note="The Jan. 26 issue is a seeded audit trail of portal aftershocks. Phase B will replace only rows that clear sample gates.",
    quote="The portal is not a transaction wire. It is a grief machine with depth charts attached.",
    commiseration_slug="nebraska",
    commiseration_eyebrow="Nebraska",
    commiseration_body="Nebraska fans spent all fall saying the future had a name. By late January, the name had an Oregon locker.",
    slug="portal-wave-peaks",
    sources=[SOURCE_URLS["portal"], SOURCE_URLS["portal_numbers"]],
    cards=[
        _card("ORE", "#007030", "Second Arm", "+11", "Oregon portal-week mood delta", "Depth chart anxiety became luxury anxiety."),
        _card("NEB", "#E41C38", "Exit Wound", "-12", "Nebraska portal-week shock", "The We're Back jar went back on the shelf."),
        _card("LSU", "#461D7C", "Kiffin Math", "+8", "LSU winter mood delta", "The Lane premium arrived before spring ball."),
    ],
)

ISSUE_040 = _make_issue(
    number="040",
    date="2 Feb 2026",
    week_start="2026-02-02",
    model_week=24,
    title="Who's The Coach Now",
    headline="Michigan found the only hire louder than the firing.",
    dek="Kyle Whittingham-to-Ann Arbor turns the carousel from transaction log into national weather.",
    caption="Carousel aftershock values are curated until coaching-event conversation windows are backfilled.",
    note="This issue is the coaching ledger issue. Every score here is editorial unless a future computed row is promoted under audit.",
    quote="The cycle was supposed to be over. Michigan made it start again.",
    commiseration_slug="utah",
    commiseration_eyebrow="Utah",
    commiseration_body="Utah did not merely lose a coach. It lost the person who made the job feel weatherproof.",
    slug="whos-the-coach-now",
    sources=[SOURCE_URLS["coaching"]],
    cards=[
        _card("MICH", "#00274C", "The Swing", "+3", "Michigan mood rebound after hire", "Relief is not the same thing as belief."),
        _card("LSU", "#461D7C", "The Lane Era", "+7", "LSU carousel-week mood delta", "Hope with a headset and a burner account."),
        _card("UTAH", "#CC0000", "The Vacancy", "-14", "Utah mood delta after Whittingham", "Continuity finally got expensive."),
    ],
)

ISSUE_041 = _make_issue(
    number="041",
    date="9 Feb 2026",
    week_start="2026-02-09",
    model_week=25,
    title="Signing Day Truths",
    headline="USC bought the offseason's loudest receipt.",
    dek="A first No. 1 class since 2006 turns Lincoln Riley's winter from referendum into referendum with evidence.",
    caption="Signing-day mood movement is curated from public recruiting rankings and program reaction.",
    note="Recruiting numbers are sourced from the public rankings ledger; fan-confidence scores remain editorial until Phase B.",
    quote="Signing Day is a story we tell ourselves. USC finally got to tell the expensive version.",
    commiseration_slug="alabama",
    commiseration_eyebrow="Alabama",
    commiseration_body="Alabama signed the kind of class most programs frame. It still had to watch someone else win the headline.",
    slug="signing-day-truths",
    sources=[SOURCE_URLS["recruiting"]],
    cards=[
        _card("USC", "#990000", "#1 Class", "+13", "USC signing-week mood delta", "The spreadsheet finally matched the logo."),
        _card("ND", "#0C2340", "Top Five", "+8", "Notre Dame recruiting-week mood delta", "Freeman got a February receipt."),
        _card("ALA", "#9E1B32", "Not First", "-4", "Alabama relative mood delta", "A top-two class can still feel like a slight."),
    ],
)

ISSUE_042 = _make_issue(
    number="042",
    date="23 Feb 2026",
    week_start="2026-02-23",
    model_week=26,
    title="Spring Opens, Narratives Lock",
    headline="Spring practice began and the quarterbacks became the story.",
    dek="Arch limited at Texas, post-portal QB rooms wobbling elsewhere, and every fanbase mistaking reps for destiny.",
    caption="Spring-open mood readings are curated from the practice ledger and held as editorial rows.",
    note="This is a spring-practice shell until live conversation rows clear the minimum author and mention gates.",
    quote="February is when every depth chart becomes a belief system.",
    commiseration_slug="texas",
    commiseration_eyebrow="Texas",
    commiseration_body="Texas entered spring with the most famous quarterback room in the sport and somehow added uncertainty.",
    slug="spring-opens-narratives-lock",
    sources=[SOURCE_URLS["spring_schedule"]],
    cards=[
        _card("TEX", "#BF5700", "Limited Arch", "-6", "Texas spring-open mood delta", "The backup discourse never clocks out."),
        _card("BAMA", "#9E1B32", "QB Fog", "-5", "Alabama spring-open mood delta", "Every incompletion became a referendum."),
        _card("OSU", "#BB0000", "Quiet Floor", "+4", "Ohio State spring-open mood delta", "Stability is boring until March."),
    ],
)

ISSUE_043 = _make_issue(
    number="043",
    date="2 Mar 2026",
    week_start="2026-03-02",
    model_week=27,
    title="Hype Train Check",
    headline="The offseason had already started lying to itself.",
    dek="Oregon and LSU run hot, Georgia and Ohio State run quiet, and Alabama discovers what polite burial sounds like.",
    caption="Reality-gap labels are editorial buckets until matched to the latest FBS-only model run.",
    note="The Reality Gap board is seeded directionally. Phase B will publish only when the power-rating population is large enough.",
    quote="March hype is just August confidence wearing a lighter jacket.",
    commiseration_slug="alabama",
    commiseration_eyebrow="Alabama",
    commiseration_body="Alabama was not bad. It was merely being discussed like an ordinary contender, which felt worse.",
    slug="hype-train-check",
    sources=[SOURCE_URLS["spring_schedule"], SOURCE_URLS["coaching"]],
    cards=[
        _card("ORE", "#007030", "Overcooked", "+9", "Oregon hype-vs-reality seed", "The ceiling got louder than the floor."),
        _card("UGA", "#BA0C2F", "Ignored", "+2", "Georgia quiet-strength seed", "The boring good team remains good."),
        _card("ALA", "#9E1B32", "Buried", "-7", "Alabama narrative delta", "The obituary draft was premature."),
    ],
)

ISSUE_044 = _make_issue(
    number="044",
    date="9 Mar 2026",
    week_start="2026-03-09",
    model_week=28,
    title="The Moore Presser",
    headline="Michigan's offseason went over the cliff in one room.",
    dek="The March 14 presser becomes the hinge event: not the moment doubt arrived, but the moment it became official.",
    caption="The Moore-presser shock reading is editorial until the ET-anchored daily sentiment window clears volume gates.",
    note="This issue intentionally tags the Moore-presser numbers as editorial. They are not published as computed sentiment.",
    quote="A press conference can be a transaction if everyone leaves it selling.",
    commiseration_slug="michigan",
    commiseration_eyebrow="Michigan",
    commiseration_body="Michigan fans did not agree on the answer. They agreed the question had become unavoidable.",
    slug="the-moore-presser",
    sources=[SOURCE_URLS["coaching"]],
    cards=[
        _card("MICH", "#00274C", "Cliff Week", "-15", "Michigan presser-week shock", "The floor did not collapse. It was removed."),
        _card("USC", "#990000", "Riley Fatigue", "-7", "USC March narrative delta", "The joke kept finding new rooms."),
        _card("ALA", "#9E1B32", "Doubt Tax", "-6", "Alabama March narrative delta", "Every dynasty pays interest eventually."),
    ],
)

ISSUE_045 = _make_issue(
    number="045",
    date="23 Mar 2026",
    week_start="2026-03-23",
    model_week=29,
    title="Michigan Moves On",
    headline="Michigan fired the story and hired a new one.",
    dek="Whittingham's arrival turns Ann Arbor from crisis site into impossible-coach thought experiment.",
    caption="Michigan's move-on week is seeded from the coaching ledger and will promote row-by-row only after calibration.",
    note="Late-March numbers are curated from the firing/hire ledger. The rivalry heat rows remain editorial in Phase A.",
    quote="The hire did not solve the offseason. It made the offseason worth reading.",
    commiseration_slug="ohio-state",
    commiseration_eyebrow="Ohio State",
    commiseration_body="Ohio State got the rare rivalry problem of having too much material to choose from.",
    slug="michigan-moves-on",
    sources=[SOURCE_URLS["coaching"], SOURCE_URLS["spring_games"]],
    cards=[
        _card("MICH", "#00274C", "New Regime", "+9", "Michigan post-hire mood delta", "Panic got upgraded to argument."),
        _card("OSU", "#BB0000", "Rent Free", "+6", "Ohio State rival-mention heat", "The group chat had content again."),
        _card("NEB", "#E41C38", "Spring Pop", "+5", "Nebraska spring-game seed", "Hope got a scrimmage jersey."),
    ],
)

ISSUE_046 = _make_issue(
    number="046",
    date="6 Apr 2026",
    week_start="2026-04-06",
    model_week=30,
    title="Spring Games And Stock",
    headline="Spring games turned private anxiety into public evidence.",
    dek="USC, Alabama, Ohio State, and Michigan all put something on tape. Some of it helped. Some of it became a headline.",
    caption="Spring-game stock values are curated from public spring-game recaps and kept editorial in Phase A.",
    note="The final retro issue before the live handoff is explicitly seeded. Computed Shock Index rows must pass ET volume gates before promotion.",
    quote="April tape is not truth. It is the first draft of August's argument.",
    commiseration_slug="michigan",
    commiseration_eyebrow="Michigan",
    commiseration_body="Whittingham's debut answered the coaching question and made the quarterback question louder.",
    slug="spring-games-and-stock",
    sources=[SOURCE_URLS["spring_games"], SOURCE_URLS["michigan_spring"]],
    cards=[
        _card("MICH", "#00274C", "QB Problem", "-9", "Michigan post-spring mood delta", "A new coach still needs a passer."),
        _card("USC", "#990000", "Stock Up", "+5", "USC spring-game mood delta", "For one afternoon, the class looked real."),
        _card("OSU", "#BB0000", "Stable", "+3", "Ohio State spring-game mood delta", "The co-pilot stayed boring."),
    ],
)

ISSUE_047_RETRO = {
    **ISSUE_047,
    "methodology": _methodology("Issue N° 047", sources=3),
    "methodology_row_json": json.dumps(_methodology("Issue N° 047", sources=3)),
    "mood_index_dek": "Confidence scores curated from the official Jan-Apr event record.",
    "source": "editorial",
    "retro_title": "Live Handoff",
    "retro_slug": "live-handoff",
    "sources": [SOURCE_URLS["draft"], SOURCE_URLS["michigan_spring"], SOURCE_URLS["spring_games"]],
}
ISSUE_047_RETRO["cards"] = [{**card, "source": "editorial"} for card in ISSUE_047["cards"]]

RETRO_ISSUES: dict[str, dict[str, Any]] = {
    "038": ISSUE_038,
    "039": ISSUE_039,
    "040": ISSUE_040,
    "041": ISSUE_041,
    "042": ISSUE_042,
    "043": ISSUE_043,
    "044": ISSUE_044,
    "045": ISSUE_045,
    "046": ISSUE_046,
    "047": ISSUE_047_RETRO,
}

BASELINE_WEEK_021 = {
    "offseason_week": 21,
    "week_start_date": "2026-01-12",
    "issue_number": "baseline-021",
    "retro_title": "Pre-title baseline",
    "retro_slug": "pre-title-baseline",
    "model_week": 21,
    "sources": [],
}


OFFSEASON_WEEKS = [
    BASELINE_WEEK_021,
    {"offseason_week": 22, **RETRO_ISSUES["038"]},
    {"offseason_week": 23, **RETRO_ISSUES["039"]},
    {"offseason_week": 24, **RETRO_ISSUES["040"]},
    {"offseason_week": 25, **RETRO_ISSUES["041"]},
    {"offseason_week": 26, **RETRO_ISSUES["042"]},
    {"offseason_week": 27, **RETRO_ISSUES["043"]},
    {"offseason_week": 28, **RETRO_ISSUES["044"]},
    {"offseason_week": 29, **RETRO_ISSUES["045"]},
    {"offseason_week": 30, **RETRO_ISSUES["046"]},
    {"offseason_week": 31, **RETRO_ISSUES["047"]},
]

MOOD_RETRO: dict[str, list[dict[str, Any]]] = {
    "038": [
        {"slug": "indiana", "current": 94, "delta": 30, "cause": "16-0 title"},
        {"slug": "miami", "current": 55, "delta": -20, "cause": "title-game ending"},
        {"slug": "ohio-state", "current": 71, "delta": -4, "cause": "Big Ten reset"},
        {"slug": "oregon", "current": 74, "delta": 2, "cause": "title-path respect"},
        {"slug": "notre-dame", "current": 68, "delta": 1, "cause": "winter floor"},
    ],
    "039": [
        {"slug": "oregon", "current": 85, "delta": 11, "cause": "portal quarterback"},
        {"slug": "nebraska", "current": 45, "delta": -12, "cause": "Raiola exit"},
        {"slug": "lsu", "current": 72, "delta": 8, "cause": "Kiffin premium"},
        {"slug": "miami", "current": 61, "delta": 6, "cause": "settlement relief"},
        {"slug": "notre-dame", "current": 74, "delta": 6, "cause": "portal haul"},
    ],
    "040": [
        {"slug": "michigan", "current": 62, "delta": 3, "cause": "Whittingham hire"},
        {"slug": "lsu", "current": 79, "delta": 7, "cause": "Kiffin staff"},
        {"slug": "utah", "current": 49, "delta": -14, "cause": "Whittingham exit"},
        {"slug": "ole-miss", "current": 58, "delta": -6, "cause": "Kiffin exit"},
        {"slug": "oklahoma-state", "current": 54, "delta": 4, "cause": "Morris hire"},
    ],
    "041": [
        {"slug": "usc", "current": 78, "delta": 13, "cause": "No. 1 class"},
        {"slug": "notre-dame", "current": 82, "delta": 8, "cause": "top-five class"},
        {"slug": "oregon", "current": 88, "delta": 3, "cause": "recruiting stack"},
        {"slug": "alabama", "current": 68, "delta": -4, "cause": "not first"},
        {"slug": "tennessee", "current": 70, "delta": 5, "cause": "top-ten class"},
    ],
    "042": [
        {"slug": "texas", "current": 64, "delta": -6, "cause": "Arch limited"},
        {"slug": "alabama", "current": 63, "delta": -5, "cause": "QB fog"},
        {"slug": "ohio-state", "current": 75, "delta": 4, "cause": "stable spring"},
        {"slug": "nebraska", "current": 48, "delta": 3, "cause": "spring opens"},
        {"slug": "florida-state", "current": 51, "delta": -4, "cause": "QB ambiguity"},
    ],
    "043": [
        {"slug": "oregon", "current": 91, "delta": 9, "cause": "hype train"},
        {"slug": "lsu", "current": 83, "delta": 6, "cause": "Kiffin glow"},
        {"slug": "georgia", "current": 73, "delta": 2, "cause": "quiet strength"},
        {"slug": "ohio-state", "current": 76, "delta": 1, "cause": "co-pilot status"},
        {"slug": "alabama", "current": 56, "delta": -7, "cause": "premature burial"},
    ],
    "044": [
        {"slug": "michigan", "current": 47, "delta": -15, "cause": "Moore presser"},
        {"slug": "usc", "current": 66, "delta": -7, "cause": "Riley fatigue"},
        {"slug": "alabama", "current": 50, "delta": -6, "cause": "DeBoer doubt"},
        {"slug": "ohio-state", "current": 78, "delta": 2, "cause": "rival chaos"},
        {"slug": "michigan-state", "current": 61, "delta": 4, "cause": "rival heat"},
    ],
    "045": [
        {"slug": "michigan", "current": 56, "delta": 9, "cause": "Whittingham reset"},
        {"slug": "ohio-state", "current": 84, "delta": 6, "cause": "Michigan discourse"},
        {"slug": "nebraska", "current": 53, "delta": 5, "cause": "spring pop"},
        {"slug": "utah", "current": 45, "delta": -4, "cause": "aftershock"},
        {"slug": "usc", "current": 64, "delta": -2, "cause": "spotlight drift"},
    ],
    "046": [
        {"slug": "michigan", "current": 47, "delta": -9, "cause": "QB problem"},
        {"slug": "usc", "current": 69, "delta": 5, "cause": "spring tape"},
        {"slug": "alabama", "current": 54, "delta": 4, "cause": "spring answer"},
        {"slug": "ohio-state", "current": 87, "delta": 3, "cause": "stable spring"},
        {"slug": "oregon", "current": 90, "delta": -1, "cause": "waiting week"},
    ],
    "047": [
        {
            "slug": row["slug"],
            "current": int(row["current"]),
            "delta": int(row["delta"]),
            "cause": row["cause"],
        }
        for row in MOOD_SEED_047
    ],
}

RIVALRY_RETRO: dict[str, list[dict[str, Any]]] = {
    number: [
        {
            "slug": "michigan-ohio-state",
            "name": "Michigan / Ohio State",
            "team_a": {"slug": "michigan"},
            "team_b": {"slug": "ohio-state"},
            "ratio": 2.4 if number in {"044", "045", "046", "047"} else 1.6,
            "leaning_team": 2 if number in {"044", "045", "046", "047"} else 1,
            "take": "The rivalry turns into an offseason content engine.",
        },
        {
            "slug": "oregon-nebraska",
            "name": "Oregon / Nebraska",
            "team_a": {"slug": "oregon"},
            "team_b": {"slug": "nebraska"},
            "ratio": 2.8 if number == "039" else 1.4,
            "leaning_team": 2 if number == "039" else 1,
            "take": "Raiola made a transfer portal story feel like a rivalry story.",
        },
        {
            "slug": "usc-notre-dame",
            "name": "USC / Notre Dame",
            "team_a": {"slug": "usc"},
            "team_b": {"slug": "notre-dame"},
            "ratio": 1.9 if number == "041" else 1.2,
            "leaning_team": 1,
            "take": "Recruiting receipts make old grudges feel new again.",
        },
    ]
    for number in RETRO_ISSUES
}
RIVALRY_RETRO["047"] = RIVALRY_SEED_047

LEXICON_RETRO: dict[str, dict[str, Any]] = {
    "038": {
        "phrase": "the pick on the 44",
        "mention_count": 440,
        "spike_pct_wow": 310.0,
        "origin_community": "r/CFB",
        "related_team_slug": "indiana",
        "narrative": "The phrase collapses the title game into one timestamp.|It is a curated championship-week marker until backfilled.",
    },
    "039": {
        "phrase": "second arm",
        "mention_count": 320,
        "spike_pct_wow": 180.0,
        "origin_community": "r/ducks",
        "related_team_slug": "oregon",
        "narrative": "Oregon's portal story became less about need than excess.|The phrase is seeded from the portal ledger.",
    },
    "040": {
        "phrase": "Whittingham weather",
        "mention_count": 280,
        "spike_pct_wow": 155.0,
        "origin_community": "r/MichiganWolverines",
        "related_team_slug": "michigan",
        "narrative": "The hire reframed Michigan from unstable to unknowable.|This is editorial copy pending coaching-window conversation backfill.",
    },
    "041": {
        "phrase": "recruiting-service cope",
        "mention_count": 350,
        "spike_pct_wow": 140.0,
        "origin_community": "r/CFB",
        "related_team_slug": "usc",
        "narrative": "USC's No. 1 class split the room between receipt and skepticism.|The phrase is an editorial seed.",
    },
    "042": {
        "phrase": "backup discourse",
        "mention_count": 260,
        "spike_pct_wow": 115.0,
        "origin_community": "r/LonghornNation",
        "related_team_slug": "texas",
        "narrative": "Arch Manning's limited spring reps made every backup mention sound larger.|The number is curated, not computed.",
    },
    "043": {
        "phrase": "hype train check",
        "mention_count": 300,
        "spike_pct_wow": 125.0,
        "origin_community": "r/CFB",
        "related_team_slug": "oregon",
        "narrative": "By early March, offseason optimism needed a brake pedal.|Phase B will require the three-week baseline before promotion.",
    },
    "044": {
        "phrase": "hold the line",
        "mention_count": 420,
        "spike_pct_wow": 205.0,
        "origin_community": "r/MichiganWolverines",
        "related_team_slug": "michigan",
        "narrative": "The Moore presser split Michigan into patience and panic.|This phrase is editorial until daily windows clear volume gates.",
    },
    "045": {
        "phrase": "Ann Arbor Whitt",
        "mention_count": 390,
        "spike_pct_wow": 190.0,
        "origin_community": "r/CFB",
        "related_team_slug": "michigan",
        "narrative": "The hire was unlikely enough to become shorthand.|The phrase remains curated in Phase A.",
    },
    "046": {
        "phrase": "QB problem",
        "mention_count": 520,
        "spike_pct_wow": 165.0,
        "origin_community": "Michigan blogs",
        "related_team_slug": "michigan",
        "narrative": "The spring game made the post-hire honeymoon share space with the quarterback question.|This is seeded from the spring-game ledger.",
    },
    "047": LEXICON_SEED_047,
}


def _normalize_issue(issue: str | int) -> str:
    text = str(issue).strip().replace("N°", "").replace("No.", "").replace("No", "").strip()
    return text.zfill(3)


def _team_id_by_slug(db: Database, slug: str | None) -> int | None:
    if not slug:
        return None
    row = db.query_one("select team_id from teams where lower(slug) = %(slug)s limit 1", {"slug": slug.lower()})
    return int(row["team_id"]) if row and row.get("team_id") is not None else None


def seed_retro_issue_metadata(db: Database, issue: str | int = "038") -> int:
    issue_key = _normalize_issue(issue)
    meta = RETRO_ISSUES[issue_key]
    db.upsert_many(
        "hub_issue_metadata",
        [
            {
                "issue_number": meta["issue_number"],
                "week_start_date": meta["week_start_date"],
                "issue_date": meta["issue_date"],
                "model_week": meta["model_week"],
                "cover_headline": meta["cover_headline"],
                "cover_dek": meta["cover_dek"],
                "cover_chart_caption": meta["cover_chart_caption"],
                "editor_note_body": meta["editor_note_body"],
                "pull_quote": meta["cover_pull_quote"],
                "commiseration_team_slug": meta["commiseration_team_slug"],
                "commiseration_eyebrow": meta["commiseration_eyebrow"],
                "commiseration_body": meta["commiseration_body"],
                "cards_json": json.dumps(meta["cards"]),
                "methodology_row_json": json.dumps(meta["methodology"]),
            }
        ],
        conflict_columns=["issue_number"],
        update_columns=[
            "week_start_date",
            "issue_date",
            "model_week",
            "cover_headline",
            "cover_dek",
            "cover_chart_caption",
            "editor_note_body",
            "pull_quote",
            "commiseration_team_slug",
            "commiseration_eyebrow",
            "commiseration_body",
            "cards_json",
            "methodology_row_json",
        ],
    )
    return 1


def seed_offseason_week_map(db: Database) -> int:
    rows = [
        {
            "season_year": SEASON_YEAR,
            "offseason_week": int(entry["offseason_week"]),
            "week_start_date": entry["week_start_date"],
            "issue_number": entry["issue_number"],
            "issue_title": entry["retro_title"],
            "slug": entry["retro_slug"],
            "model_week": entry["model_week"],
            "sources_json": json.dumps(entry.get("sources") or []),
        }
        for entry in OFFSEASON_WEEKS
    ]
    db.upsert_many(
        "offseason_week_map",
        rows,
        conflict_columns=["season_year", "offseason_week"],
        update_columns=[
            "week_start_date",
            "issue_number",
            "issue_title",
            "slug",
            "model_week",
            "sources_json",
            "ingested_at",
        ],
    )
    return len(rows)


def seed_retro_mood_week(db: Database, issue: str | int = "038") -> int:
    issue_key = _normalize_issue(issue)
    meta = RETRO_ISSUES[issue_key]
    rows: list[dict[str, Any]] = []
    for entry in MOOD_RETRO[issue_key]:
        team_id = _team_id_by_slug(db, entry["slug"])
        if team_id is None:
            continue
        rows.append(
            {
                "team_id": team_id,
                "week_start_date": meta["week_start_date"],
                "mood_score": int(entry["current"]),
                "delta_from_prev_week": int(entry["delta"]),
                "top_cause_token": str(entry["cause"]).replace(" ", "_"),
                "top_cause_label": entry["cause"],
                "sample_size": 0,
                "source": "editorial",
                "sample_authors": 0,
                "confidence": 1.0,
            }
        )
    db.upsert_many(
        "fanbase_mood_weekly",
        rows,
        conflict_columns=["team_id", "week_start_date"],
        update_columns=[
            "mood_score",
            "delta_from_prev_week",
            "top_cause_token",
            "top_cause_label",
            "sample_size",
            "source",
            "sample_authors",
            "confidence",
            "ingested_at",
        ],
    )
    return len(rows)


def seed_retro_rivalry_week(db: Database, issue: str | int = "038") -> int:
    issue_key = _normalize_issue(issue)
    meta = RETRO_ISSUES[issue_key]
    rows: list[dict[str, Any]] = []
    for rivalry in RIVALRY_RETRO[issue_key]:
        team_a_id = _team_id_by_slug(db, rivalry["team_a"]["slug"])
        team_b_id = _team_id_by_slug(db, rivalry["team_b"]["slug"])
        if team_a_id is None or team_b_id is None:
            continue
        leaning = int(rivalry["leaning_team"])
        if team_a_id > team_b_id:
            team_a_id, team_b_id = team_b_id, team_a_id
            leaning = {0: 0, 1: 2, 2: 1}.get(leaning, leaning)
        ratio = float(rivalry["ratio"])
        a_count = int(round(100 if leaning != 2 else 100 / max(ratio, 0.1)))
        b_count = int(round(100 if leaning != 1 else 100 / max(ratio, 0.1)))
        rows.append(
            {
                "rivalry_slug": rivalry["slug"],
                "rivalry_name": rivalry["name"],
                "team_a_id": team_a_id,
                "team_b_id": team_b_id,
                "week_start_date": meta["week_start_date"],
                "a_mentions_b_count": max(a_count, 8),
                "b_mentions_a_count": max(b_count, 8),
                "ratio_dominant": ratio,
                "leaning_team": leaning,
                "take": rivalry["take"],
                "source": "editorial",
                "sample_authors": 0,
                "confidence": 1.0,
            }
        )
    db.upsert_many(
        "rivalry_obsession_weekly",
        rows,
        conflict_columns=["rivalry_slug", "week_start_date"],
        update_columns=[
            "rivalry_name",
            "team_a_id",
            "team_b_id",
            "a_mentions_b_count",
            "b_mentions_a_count",
            "ratio_dominant",
            "leaning_team",
            "take",
            "source",
            "sample_authors",
            "confidence",
            "ingested_at",
        ],
    )
    return len(rows)


def _trend_for(mention_count: int) -> list[dict[str, Any]]:
    return [
        {"week": "W-3", "frequency": max(2, int(mention_count * 0.18))},
        {"week": "W-2", "frequency": max(3, int(mention_count * 0.24))},
        {"week": "W-1", "frequency": max(5, int(mention_count * 0.36))},
        {"week": "Now", "frequency": mention_count},
    ]


def seed_retro_lexicon_week(db: Database, issue: str | int = "038") -> int:
    issue_key = _normalize_issue(issue)
    meta = RETRO_ISSUES[issue_key]
    feature = LEXICON_RETRO[issue_key]
    secondary = LEXICON_SECONDARY_047 if issue_key == "047" else []
    rows = [
        {
            "phrase": feature["phrase"],
            "week_start_date": meta["week_start_date"],
            "mention_count": int(feature["mention_count"]),
            "spike_pct_wow": float(feature["spike_pct_wow"]),
            "origin_community": feature["origin_community"],
            "related_team_id": _team_id_by_slug(db, feature.get("related_team_slug")),
            "sample_quotes_json": json.dumps(feature.get("sample_quotes") or []),
            "trend_json": json.dumps(feature.get("trend") or _trend_for(int(feature["mention_count"]))),
            "narrative": feature["narrative"],
            "featured": 1,
            "source": "editorial",
            "sample_authors": 0,
            "confidence": 1.0,
        }
    ]
    for item in secondary:
        rows.append(
            {
                "phrase": item["phrase"],
                "week_start_date": meta["week_start_date"],
                "mention_count": int(item["mention_count"]),
                "spike_pct_wow": float(item["spike_pct_wow"]),
                "origin_community": item["origin_community"],
                "related_team_id": _team_id_by_slug(db, item.get("related_team_slug")),
                "sample_quotes_json": "[]",
                "trend_json": "[]",
                "narrative": item["narrative"],
                "featured": 0,
                "source": "editorial",
                "sample_authors": 0,
                "confidence": 1.0,
            }
        )
    db.upsert_many(
        "lexicon_weekly",
        rows,
        conflict_columns=["phrase", "week_start_date"],
        update_columns=[
            "mention_count",
            "spike_pct_wow",
            "origin_community",
            "related_team_id",
            "sample_quotes_json",
            "trend_json",
            "narrative",
            "featured",
            "source",
            "sample_authors",
            "confidence",
            "ingested_at",
        ],
    )
    return len(rows)


def seed_retro_issue(db: Database, issue: str | int = "038") -> dict[str, int]:
    issue_key = _normalize_issue(issue)
    if issue_key not in RETRO_ISSUES:
        raise ValueError(f"Unknown retro issue: {issue}")
    from cfb_rankings.ingest.hub_data_compute import revert_week_to_editorial

    seed_offseason_week_map(db)
    reverted = revert_week_to_editorial(db, RETRO_ISSUES[issue_key]["week_start_date"])
    return {
        "reverted": reverted,
        "metadata": seed_retro_issue_metadata(db, issue_key),
        "mood": seed_retro_mood_week(db, issue_key),
        "rivalry": seed_retro_rivalry_week(db, issue_key),
        "lexicon": seed_retro_lexicon_week(db, issue_key),
    }


def seed_retro_all(db: Database) -> dict[str, dict[str, int]]:
    seed_offseason_week_map(db)
    return {issue: seed_retro_issue(db, issue) for issue in sorted(RETRO_ISSUES)}
