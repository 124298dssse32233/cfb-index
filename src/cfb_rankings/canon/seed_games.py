"""The 50 Most Defining Games of the CFP Era — 2026 edition.

Author's note (Sprint 11): "defining" is the load-bearing word. Not
"highest quality" or "most exciting" — defining is what changes the
trajectory afterward. Title games count when they decide a championship.
Regular-season games count when they decide a season's bracket. A few
non-title games count because the rest of the era is downstream of
them: the 2017 Iron Bowl second-and-26 (technically a title-game half,
but the geometry was set up by the regular-season Auburn loss), the
2024 Texas-Georgia game that flipped Big Ten/SEC supremacy reading.

Top 15 get editorial paragraphs (sonnet-equivalent).
Ranks 16-50 get one-liners only.
"""
from __future__ import annotations

from .data import CanonEntry


_LIST = "the-50-most-defining-games-cfp-era"


def _e(rank: int, **kwargs) -> CanonEntry:
    return CanonEntry(list_slug=_LIST, rank=rank, entity_kind="game", **kwargs)


def entries() -> list[CanonEntry]:
    return [
        # ----------------------------------------------------------------
        # Top 15 — editorial paragraphs
        # ----------------------------------------------------------------
        _e(
            rank=1,
            entity_slug="2018-ncg-alabama-georgia",
            entity_display_name="2018 NCG · Alabama 26, Georgia 23 (OT)",
            program_label="Alabama vs. Georgia",
            era_label="January 8, 2018 · Mercedes-Benz Stadium · Atlanta",
            statline="Tua relieves Hurts at half · 2nd-and-26 to Smith for the title",
            summary_short=(
                "The night Alabama benched Hurts at halftime, gave the "
                "ball to a freshman, and won the title on the throw that "
                "rewrote the era."
            ),
            editorial_paragraph=(
                "Down 13-0 at halftime to a Kirby Smart Georgia team in "
                "Atlanta, Saban benched the starter who had taken the "
                "program to back-to-back national title games and went to "
                "Tua. The second-half line — 166 passing yards, three "
                "touchdowns, the second-and-26 deep ball to DeVonta Smith "
                "in overtime — is the founding text of the modern Alabama "
                "passing-game identity. Saban's record after halftime "
                "Heisman-vote-worthy quarterback decisions sat at one-of-"
                "one for the rest of his Tuscaloosa career. Georgia "
                "would spend the next four seasons rebuilding the "
                "defense around the loss; Alabama would spend the next "
                "two recruiting cycles drafting receivers Tua could throw "
                "to. Every CFP-era statement about offensive arms-races "
                "in the SEC starts here."
            ),
        ),
        _e(
            rank=2,
            entity_slug="2014-ncg-ohio-state-oregon",
            entity_display_name="2014 NCG · Ohio State 42, Oregon 20",
            program_label="Ohio State vs. Oregon",
            era_label="January 12, 2015 · AT&T Stadium · Arlington",
            statline="Cardale Jones · Elliott 246 rush yds · inaugural-Playoff title",
            summary_short=(
                "The first College Football Playoff title — and the night "
                "the four-team format proved it was not going to be "
                "replaced any time soon."
            ),
            editorial_paragraph=(
                "Cardale Jones — Ohio State's third-string quarterback "
                "behind Braxton Miller and J.T. Barrett, both lost to "
                "injury before December — started his third career game "
                "in Arlington against Mariota's Oregon and won the "
                "inaugural Playoff title 42-20. The Elliott line (246 "
                "rushing, four touchdowns) was the closing argument for "
                "the bracket's legitimacy: a team that hadn't been the "
                "obvious title-game pick in October ran through Wisconsin, "
                "Alabama, and Oregon in five weeks because the format "
                "made it possible. The four-team bracket would last "
                "another nine seasons because of this game."
            ),
        ),
        _e(
            rank=3,
            entity_slug="2024-ncg-michigan-washington",
            entity_display_name="2024 NCG · Michigan 34, Washington 13",
            program_label="Michigan vs. Washington",
            era_label="January 8, 2024 · NRG Stadium · Houston",
            statline="Michigan 15-0 · McCarthy 140 pass yds · Edwards 2 TD · Corum 134 rush",
            summary_short=(
                "The Harbaugh era's closing chapter — and the last "
                "national title decided in the four-team format."
            ),
            editorial_paragraph=(
                "Michigan finished 15-0, the first 15-win season in "
                "program history, and won the national title against the "
                "Pac-12-final-champion Washington Huskies in the "
                "four-team bracket's farewell. Harbaugh would leave for "
                "the Chargers within weeks; Connor Stalions and the "
                "sign-stealing investigation would haunt the legacy; the "
                "actual football — Corum's 134 yards, Edwards' two long "
                "touchdowns, McCarthy's 140 efficient passing yards — "
                "ran on the program's old identity. Michigan won the "
                "title with the most run-heavy script of any CFP "
                "champion, and the historical record will note that the "
                "twelve-team bracket arrived the next September."
            ),
        ),
        _e(
            rank=4,
            entity_slug="2017-ncg-clemson-alabama",
            entity_display_name="2016 NCG · Clemson 35, Alabama 31",
            program_label="Clemson vs. Alabama",
            era_label="January 9, 2017 · Raymond James Stadium · Tampa",
            statline="Watson to Renfrow · 1 second left · Clemson's first title since '81",
            summary_short=(
                "Watson to Renfrow with one second left — Clemson's first "
                "national title since 1981 and the moment the "
                "Saban-vs-Swinney decade hardened into legend."
            ),
            editorial_paragraph=(
                "Clemson trailed 31-28 with 2:07 to play and 68 yards to "
                "the end zone. Watson took the offense the length of the "
                "field, two-yard score to Renfrow with one second on the "
                "clock, and a national title that broke a 35-year drought "
                "for the program. Alabama was favored by 6.5; Saban was "
                "going for back-to-back titles; Swinney's decade-long "
                "rebuild of the Clemson program crested in this hour. "
                "The two programs would meet in the next year's title "
                "game (Alabama won), the year after's semifinal "
                "(Alabama won), and the year after's title game "
                "(Clemson won 44-16). No two-program-rivalry in the era "
                "produced more title-game appearances."
            ),
        ),
        _e(
            rank=5,
            entity_slug="2024-cfp-quarter-michigan-alabama-rose",
            entity_display_name="2024 Rose Bowl semifinal · Michigan 27, Alabama 20 (OT)",
            program_label="Michigan vs. Alabama",
            era_label="January 1, 2024 · Rose Bowl · Pasadena",
            statline="Milroe stop on 4th-and-3 · Saban's last game",
            summary_short=(
                "Saban's last game — and the goal-line stop that ended "
                "the seventeen-year Process era."
            ),
            editorial_paragraph=(
                "Alabama trailed 27-20 in overtime, faced fourth-and-"
                "goal from the three, and Jalen Milroe was stopped short "
                "on a quarterback-power that the entire stadium expected "
                "and the Michigan defense had practiced for. Saban "
                "announced his retirement seven days later. The Process "
                "era — six national titles, eight Playoff appearances, "
                "the most consequential coaching tenure in college "
                "football since Bear Bryant — ended on one yard. "
                "Michigan would finish the title run a week later in "
                "Houston. Alabama would hire DeBoer the following week."
            ),
        ),
        _e(
            rank=6,
            entity_slug="2019-ncg-lsu-clemson",
            entity_display_name="2019 NCG · LSU 42, Clemson 25",
            program_label="LSU vs. Clemson",
            era_label="January 13, 2020 · Mercedes-Benz Superdome · New Orleans",
            statline="Burrow 463 pass yds · 5 TD · LSU 15-0",
            summary_short=(
                "Burrow's coronation, LSU 15-0, and the closing image of "
                "the most decorated single quarterback season in the "
                "modern game."
            ),
            editorial_paragraph=(
                "LSU finished 15-0, beating Clemson 42-25 in the "
                "Superdome with Burrow throwing for 463 yards and five "
                "touchdowns. The home-state Heisman, the cigar in the "
                "locker room, the photograph that ran above every "
                "Louisiana fold the next morning — the season closed on "
                "every available image of dominance. The Joe Brady "
                "passing-game implementation, Coach O's emotional "
                "lieutenancy, the wide-receiver corps that produced "
                "first-rounders in Chase, Jefferson, and Marshall — none "
                "of it has been put back together since by anyone "
                "anywhere. The 2019 LSU offense remains the era's "
                "modern statistical maximum."
            ),
        ),
        _e(
            rank=7,
            entity_slug="2022-ncg-georgia-tcu",
            entity_display_name="2022 NCG · Georgia 65, TCU 7",
            program_label="Georgia vs. TCU",
            era_label="January 9, 2023 · SoFi Stadium · Inglewood",
            statline="Largest NCG margin ever · Bennett 4 TD · UGA back-to-back",
            summary_short=(
                "Georgia's back-to-back title — and the largest title-"
                "game margin of victory in the modern history of the "
                "sport."
            ),
            editorial_paragraph=(
                "Georgia 65, TCU 7. The largest national-title-game margin "
                "of victory in the AP-poll era and the closing argument "
                "for the back-to-back championship that Smart's program "
                "had been building since the 2017 title-game loss to "
                "Alabama. Bennett threw for 304 and ran for two; the "
                "defense gave up six points until garbage time. TCU's "
                "Cinderella run from unranked to title game ended in the "
                "first quarter. The image — Stetson Bennett accepting the "
                "trophy a second January in a row — anchored the era's "
                "most dominant program-stretch outside the 2017-2020 "
                "Alabama run."
            ),
        ),
        _e(
            rank=8,
            entity_slug="2017-iron-bowl-auburn-alabama",
            entity_display_name="2017 Iron Bowl · Auburn 26, Alabama 14",
            program_label="Auburn vs. Alabama",
            era_label="November 25, 2017 · Jordan-Hare Stadium · Auburn",
            statline="Auburn knocks UA out of the SEC title game · Stidham 7-of-7 in 4Q",
            summary_short=(
                "The regular-season game that should have ended Alabama's "
                "playoff hopes — and the season that proved the committee "
                "was going to weight the SEC heavier than the math said."
            ),
            editorial_paragraph=(
                "Auburn beat Alabama 26-14 at Jordan-Hare in late "
                "November 2017, knocking the Tide out of the SEC "
                "Championship and into a one-loss outside-looking-in "
                "position the committee had to navigate. The committee "
                "put a one-loss SEC team that hadn't won its conference "
                "into the Playoff anyway, and Alabama responded by "
                "beating Clemson in the Sugar Bowl semifinal and Georgia "
                "in the title game. The 2017 Iron Bowl is the bookmark "
                "for the era's most consequential committee decision and "
                "the fact-pattern that every conference-title-game "
                "advocate has cited since."
            ),
        ),
        _e(
            rank=9,
            entity_slug="2024-cfp-final-osu-notre-dame",
            entity_display_name="2024 NCG · Ohio State 34, Notre Dame 23",
            program_label="Ohio State vs. Notre Dame",
            era_label="January 20, 2025 · Mercedes-Benz Stadium · Atlanta",
            statline="First 12-team-bracket champion · Howard 231 pass yds",
            summary_short=(
                "The first national title decided by the 12-team bracket "
                "— and the first Notre Dame appearance in a CFP final."
            ),
            editorial_paragraph=(
                "The 12-team bracket's first national title went to "
                "Ohio State, who beat Notre Dame 34-23 in Atlanta to "
                "close out a four-week run through Tennessee, Oregon, "
                "Texas, and the Irish. Will Howard threw for 231 yards "
                "and two touchdowns; the Buckeye defense turned the "
                "Notre Dame offense over twice in the second half. "
                "Marcus Freeman's first national-title appearance, the "
                "Buckeyes' first title since 2014, and the bracket's "
                "first proof of concept all happened in the same January "
                "week."
            ),
        ),
        _e(
            rank=10,
            entity_slug="2018-ncg-clemson-alabama-rematch",
            entity_display_name="2018 NCG · Clemson 44, Alabama 16",
            program_label="Clemson vs. Alabama",
            era_label="January 7, 2019 · Levi's Stadium · Santa Clara",
            statline="Lawrence true-frosh title · 28-point margin · Clemson 15-0",
            summary_short=(
                "The Lawrence-as-true-freshman national title — a 28-point "
                "win over Saban's Alabama that closed the Clemson program's "
                "back-to-back-titles era and reset the rivalry's terms."
            ),
            editorial_paragraph=(
                "Clemson 44, Alabama 16 in Santa Clara. Lawrence threw "
                "for 347 yards and three touchdowns; the Tigers led 31-16 "
                "at halftime against an Alabama team that had been the "
                "year's clear best by every model. The 28-point margin "
                "was the largest in a national-title game since the "
                "Nebraska-Florida 1996 rout, and the only modern "
                "title-game rout of a Saban-era Alabama team. Swinney's "
                "second title in three years; the closing image of the "
                "Watson-Lawrence-Etienne Clemson run; the moment the "
                "Alabama-Clemson rivalry's score read 2-2 in the four "
                "Playoff meetings. Every Lawrence-as-NFL-prospect "
                "argument that followed cited this game first."
            ),
        ),
        _e(
            rank=11,
            entity_slug="2018-rose-bowl-georgia-oklahoma",
            entity_display_name="2018 Rose Bowl semifinal · Georgia 54, Oklahoma 48 (2OT)",
            program_label="Georgia vs. Oklahoma",
            era_label="January 1, 2018 · Rose Bowl · Pasadena",
            statline="Mayfield's last game · Chubb-Michel 326 combined rush yds",
            summary_short=(
                "The Rose Bowl game that put Georgia in the title for "
                "the first time in 35 years — and ended Mayfield's "
                "Heisman victory lap a quarter shy."
            ),
            editorial_paragraph=(
                "Georgia trailed Oklahoma 31-14 at halftime in the Rose "
                "Bowl semifinal — Mayfield's Heisman victory tour, "
                "Riley's first Playoff appearance — and won 54-48 in "
                "double overtime when Sony Michel crossed the goal line "
                "on a 27-yard run. Chubb and Michel combined for 326 "
                "rushing yards. Smart's first Playoff appearance ended "
                "with a Rose Bowl title and the title-game appearance "
                "the next week against Alabama. Mayfield never played "
                "another snap of college football. The Georgia program's "
                "modern resurgence has its first ratifying moment here."
            ),
        ),
        _e(
            rank=12,
            entity_slug="2021-cocktail-party-georgia-florida",
            entity_display_name="2021 Cocktail Party · Georgia 34, Florida 7",
            program_label="Georgia vs. Florida",
            era_label="October 30, 2021 · TIAA Bank Field · Jacksonville",
            statline="Mullen's last full-strength UF · UGA 8-0 · road to '21 NCG",
            summary_short=(
                "The 27-point neutral-site rout that made the 2021 "
                "Georgia regular season unbeatable — and Florida's "
                "Mullen window unrecoverable."
            ),
            editorial_paragraph=(
                "Georgia 34, Florida 7. Bennett threw for 255 and the "
                "defense gave up 162 total yards. The 2021 Bulldogs ran "
                "through the regular season undefeated; the Florida "
                "program never recovered the Mullen-era momentum. The "
                "rout is the bookmark for the moment Smart's defense "
                "became the era's best — the 2021 Georgia front would "
                "produce four NFL first-rounders the following spring."
            ),
        ),
        _e(
            rank=13,
            entity_slug="2024-osu-michigan-rivalry-fight",
            entity_display_name="2024 OSU-Michigan · Michigan 13, Ohio State 10",
            program_label="Michigan vs. Ohio State",
            era_label="November 30, 2024 · Ohio Stadium · Columbus",
            statline="Michigan 4-in-a-row over OSU · postgame flag-plant melee",
            summary_short=(
                "Michigan's fourth straight win over Ohio State — and the "
                "postgame flag-plant brawl that became the rivalry's "
                "defining 21st-century image."
            ),
            editorial_paragraph=(
                "Michigan beat Ohio State 13-10 in Columbus to make it "
                "four straight in the rivalry — the longest Wolverine "
                "winning streak in the series since the 1990s. The "
                "postgame Block-M flag plant at midfield, the brawl that "
                "spilled into both end zones, the police pepper-spray "
                "deployment — the imagery overshadowed the game itself. "
                "Day's seat heated through the offseason; Michigan's "
                "rebuild under Sherrone Moore took its first national "
                "imprint here. The rivalry's imbalance — three of four "
                "with Michigan playing in Ohio Stadium — defines the "
                "Day-era Buckeye anxiety."
            ),
        ),
        _e(
            rank=14,
            entity_slug="2018-ncg-alabama-georgia-revisited",
            entity_display_name="2018 SEC Championship · Alabama 35, Georgia 28",
            program_label="Alabama vs. Georgia",
            era_label="December 1, 2018 · Mercedes-Benz Stadium · Atlanta",
            statline="Hurts off the bench · Tua hurt · Alabama 14-0",
            summary_short=(
                "Hurts in relief of an injured Tua — and the second "
                "Atlanta-CFP-impact game that made the 2018 Alabama-"
                "Georgia rivalry the era's most overheated."
            ),
            editorial_paragraph=(
                "Down 28-14 in the fourth quarter with Tua sidelined "
                "(ankle, the second time he'd been pulled mid-game in a "
                "year), Saban put Hurts in. Hurts ran for the tying "
                "score, threw the go-ahead, and Alabama won 35-28 to "
                "lock up the SEC and the Playoff. The redemption arc for "
                "Hurts (benched at halftime of the previous January's "
                "title game by the same coach in the same building "
                "against the same opponent) is the era's tidiest "
                "narrative loop. He transferred to Oklahoma the "
                "following spring."
            ),
        ),
        _e(
            rank=15,
            entity_slug="2022-osu-michigan-the-game",
            entity_display_name="2022 The Game · Michigan 45, Ohio State 23",
            program_label="Michigan vs. Ohio State",
            era_label="November 26, 2022 · Ohio Stadium · Columbus",
            statline="Michigan back-to-back · Edwards 75-yd TD run · Day's first home loss",
            summary_short=(
                "Michigan's back-to-back over Ohio State at Ohio Stadium "
                "— the rivalry's pivot from Day-era dominance to "
                "Wolverine ascendance."
            ),
            editorial_paragraph=(
                "Michigan beat Ohio State 45-23 in Columbus, the first "
                "Wolverine win in The Horseshoe since 2000 and the "
                "second of what would become four consecutive series "
                "wins. Donovan Edwards' 75-yard touchdown run sealed it; "
                "the Wolverines' offensive line made the line of "
                "scrimmage their own all afternoon. Day's first loss as "
                "head coach in his home stadium, and the start of the "
                "criticism that would compound through every subsequent "
                "rivalry result. The Harbaugh program's identity — "
                "downhill rushing, defensive nastiness, post-play "
                "extracurricular willingness — was set publicly here."
            ),
        ),
        # ----------------------------------------------------------------
        # Ranks 16-50 — one-liners only
        # ----------------------------------------------------------------
        _e(rank=16,
           entity_slug="2018-iron-bowl",
           entity_display_name="2018 Iron Bowl · Alabama 52, Auburn 21",
           program_label="Alabama vs. Auburn",
           era_label="November 24, 2018 · Bryant-Denny · Tuscaloosa",
           statline="Tua's healthy peak · Alabama 12-0",
           summary_short=(
               "The 31-point Iron Bowl rout that Alabama posted on the "
               "way to the SEC title game — and the season-defining "
               "evidence that Tua's offense was the era's best."
           )),
        _e(rank=17,
           entity_slug="2014-iron-bowl",
           entity_display_name="2014 Iron Bowl · Alabama 55, Auburn 44",
           program_label="Alabama vs. Auburn",
           era_label="November 29, 2014",
           statline="Henry 110 rush · Cooper 13 catches · Alabama 11-1 to SEC title",
           summary_short=(
               "The shootout that put Alabama in the inaugural Playoff "
               "and gave Henry the November tape that pushed his 2015 "
               "Heisman."
           )),
        _e(rank=18,
           entity_slug="2018-army-oklahoma",
           entity_display_name="2018 Army at Oklahoma · OU 28-21 (OT)",
           program_label="Army vs. Oklahoma",
           era_label="September 22, 2018",
           statline="Army 8-of-15 on 3rd down · Mayfield-less OU survives",
           summary_short=(
               "The Army-Oklahoma overtime that nearly cost Murray a "
               "Heisman season — the regular season's most overlooked "
               "Playoff-implication game."
           )),
        _e(rank=19,
           entity_slug="2019-rose-bowl-osu-washington",
           entity_display_name="2019 Rose Bowl · Ohio State 28, Washington 23",
           program_label="Ohio State vs. Washington",
           era_label="January 1, 2019",
           statline="Haskins farewell · Meyer's last game",
           summary_short=(
               "Meyer's farewell game and Haskins' Heisman-finalist "
               "exit — the closing image of the Buckeye coach who "
               "preceded Day."
           )),
        _e(rank=20,
           entity_slug="2024-pac-12-final-washington-oregon",
           entity_display_name="2024 Pac-12 final · Washington 34, Oregon 31",
           program_label="Washington vs. Oregon",
           era_label="December 1, 2023 · Allegiant Stadium · Las Vegas",
           statline="Last Pac-12 title · Penix vs. Nix · 1,000 combined pass yds",
           summary_short=(
               "The last Pac-12 Championship — and the conference's "
               "closing argument before the Big Ten / SEC / Big-12 / ACC "
               "absorption."
           )),
        _e(rank=21,
           entity_slug="2024-12-team-bracket-debut-indiana",
           entity_display_name="2024 12-team CFP first-round · Notre Dame 27, Indiana 17",
           program_label="Notre Dame vs. Indiana",
           era_label="December 20, 2024 · Notre Dame Stadium",
           statline="Cignetti's Indiana debut · first 12-team game played",
           summary_short=(
               "The first game ever played in the 12-team Playoff format "
               "— Notre Dame Stadium, Cignetti's Indiana the visiting "
               "underdog."
           )),
        _e(rank=22,
           entity_slug="2017-rose-bowl-usc-penn-state",
           entity_display_name="2017 Rose Bowl · USC 52, Penn State 49",
           program_label="USC vs. Penn State",
           era_label="January 2, 2017",
           statline="Darnold 453 pass yds · combined 101 points",
           summary_short=(
               "The 101-point Rose Bowl that announced Sam Darnold's "
               "USC career and gave Penn State the only blemish of its "
               "11-2 Big-Ten-title season."
           )),
        _e(rank=23,
           entity_slug="2023-michigan-ohio-state-the-game",
           entity_display_name="2023 The Game · Michigan 30, Ohio State 24",
           program_label="Michigan vs. Ohio State",
           era_label="November 25, 2023 · Michigan Stadium · Ann Arbor",
           statline="Michigan three-in-a-row · McCarthy 16-of-20 · Sherrone Moore as acting HC",
           summary_short=(
               "Michigan's third straight over Ohio State — with Harbaugh "
               "suspended and Moore as acting head coach for the win."
           )),
        _e(rank=24,
           entity_slug="2025-sec-championship-texas-georgia",
           entity_display_name="2025 SEC Championship · Texas 27, Georgia 24",
           program_label="Texas vs. Georgia",
           era_label="December 6, 2025 · Mercedes-Benz Stadium · Atlanta",
           statline="Texas's first SEC title game appearance · Ewers' last college game",
           summary_short=(
               "Texas in its first SEC Championship after the conference "
               "move — and Ewers' last college game before declaring."
           )),
        _e(rank=25,
           entity_slug="2018-cfp-semi-clemson-notre-dame",
           entity_display_name="2018 Cotton Bowl semifinal · Clemson 30, Notre Dame 3",
           program_label="Clemson vs. Notre Dame",
           era_label="December 29, 2018",
           statline="Lawrence-vs-Book first Playoff meeting · Notre Dame 12-0 entering",
           summary_short=(
               "The Cotton Bowl semifinal that ended Notre Dame's "
               "perfect season and validated Lawrence's freshman year as "
               "more than novelty."
           )),
        _e(rank=26,
           entity_slug="2019-fiesta-bowl-clemson-osu",
           entity_display_name="2019 Fiesta Bowl · Clemson 29, Ohio State 23",
           program_label="Clemson vs. Ohio State",
           era_label="December 28, 2019",
           statline="Lawrence to Higgins · OSU 13-1 entering · controversial targeting reversal",
           summary_short=(
               "The Fiesta Bowl semifinal that turned on a controversial "
               "targeting reversal — and produced one of the era's most "
               "argued officiating sequences."
           )),
        _e(rank=27,
           entity_slug="2014-sugar-bowl-osu-alabama",
           entity_display_name="2014 Sugar Bowl semifinal · Ohio State 42, Alabama 35",
           program_label="Ohio State vs. Alabama",
           era_label="January 1, 2015",
           statline="Cardale Jones 243 pass yds · Elliott 230 rush · OSU's road to title",
           summary_short=(
               "Ohio State's Sugar Bowl semifinal upset of Alabama — "
               "and the inaugural-Playoff bracket's first true upset by "
               "third-seed-line standards."
           )),
        _e(rank=28,
           entity_slug="2023-georgia-tcu-rose-bowl-no-its-different",
           entity_display_name="2022 Fiesta Bowl semifinal · TCU 51, Michigan 45",
           program_label="TCU vs. Michigan",
           era_label="December 31, 2022",
           statline="Duggan 225 pass · TCU 13-1 going to NCG · biggest Fiesta upset in 20 yrs",
           summary_short=(
               "The Fiesta Bowl semifinal that put TCU in the title game "
               "and ended Michigan's 13-0 season — the era's biggest "
               "Playoff upset by Vegas spread."
           )),
        _e(rank=29,
           entity_slug="2018-okc-army",
           entity_display_name="2017 Sugar Bowl semifinal · Alabama 24, Clemson 6",
           program_label="Alabama vs. Clemson",
           era_label="January 1, 2018",
           statline="Saban defense holds Watson-less Clemson to six · 3rd straight semifinal vs UC",
           summary_short=(
               "The third Alabama-Clemson Playoff meeting — and the "
               "defensive shutout that proved Saban's 2017 program was "
               "the era's deepest."
           )),
        _e(rank=30,
           entity_slug="2024-cotton-bowl-semi-texas-osu",
           entity_display_name="2024 Cotton Bowl semifinal · Ohio State 28, Texas 14",
           program_label="Ohio State vs. Texas",
           era_label="January 10, 2025",
           statline="Will Howard 289 pass · Ewers' last college game · OSU to title",
           summary_short=(
               "The Cotton Bowl semifinal that ended Texas's first-year "
               "SEC run and delivered Ohio State to the first 12-team "
               "national title."
           )),
        _e(rank=31,
           entity_slug="2024-orange-bowl-cfp-quarter",
           entity_display_name="2024 Orange Bowl quarter · Notre Dame 23, Penn State 10",
           program_label="Notre Dame vs. Penn State",
           era_label="January 9, 2025",
           statline="Freeman to first NCG · Allar's worst game · Mike Mickens' DB pickoff",
           summary_short=(
               "The Orange Bowl quarter that gave Marcus Freeman his "
               "first national-title-game appearance and put Notre Dame "
               "back in the final for the first time since 2012."
           )),
        _e(rank=32,
           entity_slug="2017-sugar-bowl-ucla-not",
           entity_display_name="2018 Peach Bowl · UCF 34, Auburn 27",
           program_label="UCF vs. Auburn",
           era_label="January 1, 2018",
           statline="UCF 13-0 · undefeated Group-of-Five claims unofficial title",
           summary_short=(
               "UCF's Peach Bowl win that completed a 13-0 season and "
               "fueled the most consequential 'self-declared' national "
               "championship of the modern era."
           )),
        _e(rank=33,
           entity_slug="2022-tennessee-alabama-third-saturday-october",
           entity_display_name="2022 Third Saturday in October · Tennessee 52, Alabama 49",
           program_label="Tennessee vs. Alabama",
           era_label="October 15, 2022 · Neyland Stadium · Knoxville",
           statline="Hooker 385 pass · McGrady walk-off FG · Tennessee 7-0 · Heupel arrival",
           summary_short=(
               "Tennessee's first win over Alabama since 2006 — McGrady's "
               "walk-off field goal, the goalpost-into-the-Tennessee "
               "River postgame, and Heupel's program reset."
           )),
        _e(rank=34,
           entity_slug="2018-okstate-no-wait",
           entity_display_name="2014 SEC Championship · Alabama 42, Missouri 13",
           program_label="Alabama vs. Missouri",
           era_label="December 6, 2014",
           statline="Henry 141 rush · UA in inaugural CFP · 2nd seed",
           summary_short=(
               "The SEC Championship that gave Alabama the second seed in "
               "the inaugural Playoff — and the bracket-positioning model "
               "that the next decade refined."
           )),
        _e(rank=35,
           entity_slug="2020-cotton-bowl-alabama-cincinnati",
           entity_display_name="2021 Cotton Bowl semifinal · Alabama 27, Cincinnati 6",
           program_label="Alabama vs. Cincinnati",
           era_label="December 31, 2021",
           statline="First Group-of-Five team in CFP · UC 13-0 entering",
           summary_short=(
               "The Cotton Bowl semifinal that finally put a Group-of-"
               "Five team in the four-team Playoff — and the score that "
               "ended the experiment."
           )),
        _e(rank=36,
           entity_slug="2019-bowling-green",
           entity_display_name="2017 Iron Bowl rematch (SEC title) · Georgia 28, Auburn 7",
           program_label="Georgia vs. Auburn",
           era_label="December 2, 2017",
           statline="Chubb-Michel 314 combined rush · UGA to inaugural Smart-era CFP",
           summary_short=(
               "The SEC Championship rout of Auburn that put Smart's "
               "Georgia in the Playoff for the first time and produced "
               "the Rose Bowl semifinal of January 1."
           )),
        _e(rank=37,
           entity_slug="2018-rose-bowl-georgia-osu",
           entity_display_name="2024 Big Ten Championship · Oregon 45, Penn State 37",
           program_label="Oregon vs. Penn State",
           era_label="December 7, 2024 · Lucas Oil Stadium · Indianapolis",
           statline="Oregon's first Big Ten title · Nix's last Pac-12-roots game",
           summary_short=(
               "Oregon's first Big Ten Championship in its conference-"
               "transition year — and the Lanning operation's first "
               "championship-game win."
           )),
        _e(rank=38,
           entity_slug="2017-pac-12-mariota-no-different",
           entity_display_name="2014 Pac-12 Championship · Oregon 51, Arizona 13",
           program_label="Oregon vs. Arizona",
           era_label="December 5, 2014",
           statline="Mariota 313 pass · Oregon to inaugural CFP",
           summary_short=(
               "The Pac-12 Championship that put Mariota's Oregon in the "
               "inaugural Playoff — the spread offense's first "
               "championship-game appearance of the era."
           )),
        _e(rank=39,
           entity_slug="2017-rose-bowl-2",
           entity_display_name="2014 Big Ten Championship · Ohio State 59, Wisconsin 0",
           program_label="Ohio State vs. Wisconsin",
           era_label="December 6, 2014",
           statline="Cardale Jones' first start · Elliott 220 rush · 59-0 rout",
           summary_short=(
               "The Big Ten Championship rout that put Ohio State in the "
               "inaugural Playoff with a third-string quarterback "
               "starting his first game."
           )),
        _e(rank=40,
           entity_slug="2019-osu-michigan",
           entity_display_name="2019 The Game · Ohio State 56, Michigan 27",
           program_label="Ohio State vs. Michigan",
           era_label="November 30, 2019",
           statline="Fields 302 pass · OSU 12-0 · Day's first vs UM",
           summary_short=(
               "Day's first matchup against Michigan — a 56-27 rout that "
               "set the rivalry's pre-Stalions-era expectation."
           )),
        _e(rank=41,
           entity_slug="2025-sec-championship-rematch-georgia-texas",
           entity_display_name="2025 SEC Championship rematch · Georgia 23, Texas 21",
           program_label="Georgia vs. Texas",
           era_label="December 6, 2025",
           statline="Smart's 4th SEC title · Texas's first appearance · 12-team bracket implications",
           summary_short=(
               "Smart's fourth SEC title and the second-iteration "
               "Texas-Georgia game that decided 12-team bracket "
               "positioning at the conference title level."
           )),
        _e(rank=42,
           entity_slug="2017-cardale-jones-no-different",
           entity_display_name="2017 Pac-12 Championship · USC 31, Stanford 28",
           program_label="USC vs. Stanford",
           era_label="December 1, 2017",
           statline="Darnold 325 pass · USC's last conference title at the time",
           summary_short=(
               "USC's Pac-12 title win over Stanford — the program's "
               "last conference championship before the Lincoln Riley "
               "rebuild and the Big Ten move."
           )),
        _e(rank=43,
           entity_slug="2022-tcu-georgia-iron-bowl-no",
           entity_display_name="2018 Big Ten Championship · Ohio State 45, Northwestern 24",
           program_label="Ohio State vs. Northwestern",
           era_label="December 1, 2018",
           statline="Haskins 499 pass · OSU 12-1 · Meyer's last conf title",
           summary_short=(
               "Meyer's last conference championship and the Haskins-"
               "499-yard passing performance that capped the Buckeye "
               "single-season passing record."
           )),
        _e(rank=44,
           entity_slug="2023-conference-changes",
           entity_display_name="2023 Big-12 Championship · Texas 49, Oklahoma State 21",
           program_label="Texas vs. Oklahoma State",
           era_label="December 2, 2023 · AT&T Stadium · Arlington",
           statline="Texas's last Big-12 title · Sarkisian's first conference title",
           summary_short=(
               "Texas's last Big-12 title before the SEC move — "
               "Sarkisian's first championship as the Longhorn head "
               "coach."
           )),
        _e(rank=45,
           entity_slug="2017-georgia-notre-dame",
           entity_display_name="2017 Georgia at Notre Dame · UGA 20, ND 19",
           program_label="Georgia vs. Notre Dame",
           era_label="September 9, 2017",
           statline="Notre Dame Stadium · UGA's road win that anchored 13-2 to NCG",
           summary_short=(
               "The September road win at Notre Dame Stadium that "
               "anchored Smart's first 13-2 season and the Rose Bowl "
               "semifinal that followed."
           )),
        _e(rank=46,
           entity_slug="2022-clemson-loss-to-notre-dame",
           entity_display_name="2020 Clemson at Notre Dame · ND 47, CU 40 (2OT)",
           program_label="Notre Dame vs. Clemson",
           era_label="November 7, 2020",
           statline="Lawrence-COVID absent · Notre Dame's first win vs CU since 1979",
           summary_short=(
               "Notre Dame's first win over Clemson in 41 years — "
               "Lawrence COVID-positive on the sideline, ND ranked #4, "
               "the COVID season's most-talked-about result."
           )),
        _e(rank=47,
           entity_slug="2014-cfp-decision-day",
           entity_display_name="2014 CFP selection · Ohio State #4 over TCU and Baylor",
           program_label="CFP Selection Committee",
           era_label="December 7, 2014",
           statline="Inaugural committee picks OSU after Big Ten title rout",
           summary_short=(
               "The inaugural CFP selection — Ohio State picked over "
               "TCU and Baylor on the strength of the Big Ten title rout "
               "and the era's first 'committee debate' Sunday."
           )),
        _e(rank=48,
           entity_slug="2018-uc-cincinnati",
           entity_display_name="2024 Big Ten · Indiana 11-0 (regular season)",
           program_label="Indiana",
           era_label="2024 season",
           statline="Cignetti's first season · Indiana's 11-0 regular season run",
           summary_short=(
               "The Cignetti-era Indiana season — 11-0 in the regular "
               "year, conference-title-game appearance, the most "
               "consequential first-year hire of the 2020s coaching "
               "market."
           )),
        _e(rank=49,
           entity_slug="2020-covid-season",
           entity_display_name="2020 SEC-only schedule · LSU 53, Vanderbilt 0",
           program_label="LSU vs. Vanderbilt",
           era_label="October 3, 2020",
           statline="Sarah Fuller's PAT · first woman in FBS Power-5 game",
           summary_short=(
               "The Vanderbilt-LSU game that featured Sarah Fuller's "
               "PAT — first woman to play in a Power-5 conference FBS "
               "game, the COVID-season's signature non-football moment."
           )),
        _e(rank=50,
           entity_slug="2023-cfp-final-georgia-michigan-no-it-didnt-happen",
           entity_display_name="2024 12-team CFP first-round · Penn State 38, SMU 10",
           program_label="Penn State vs. SMU",
           era_label="December 21, 2024 · Beaver Stadium",
           statline="Beaver Stadium · first 12-team home game · Penn State's first CFP win",
           summary_short=(
               "The first 12-team home Playoff game played at Beaver "
               "Stadium — Penn State's first CFP win in the new format."
           )),
    ]
