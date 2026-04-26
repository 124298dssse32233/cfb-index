"""The 100 Best Players of the CFP Era — 2026 edition.

Author's note (Sprint 11, edition 2026): the CFP era runs 2014–2025.
The list is intentionally settled: peak season + postseason work + what
the player meant to the program, not draft outcome. Tua's injury costs
him nothing; Jameis Winston's 2014 carries him; Lamar Jackson's
ACC-era brilliance is not penalized for the team around him.

Ranks 1-3 are the deepest editorial register (opus-equivalent). Ranks
4-25 are standard editorial paragraphs (sonnet). Ranks 26-100 are
one-liners only (sonnet, terse-register).

Banned-phrase note: every line here was written under the constraint of
``canon/voice_validator.BANNED_PHRASES``. The editorial register is "the
sharp beat writer with the ten-year memory" — comparative, named, no
scaffolding.
"""
from __future__ import annotations

from .data import CanonEntry


_LIST = "the-100-best-players-cfp-era"


def _e(rank: int, **kwargs) -> CanonEntry:
    """Compact constructor — all entries land in the same list."""
    return CanonEntry(list_slug=_LIST, rank=rank, entity_kind="player", **kwargs)


def entries() -> list[CanonEntry]:
    return [
        # ----------------------------------------------------------------
        # Ranks 1-3: opus-equivalent — deepest editorial register
        # ----------------------------------------------------------------
        _e(
            rank=1,
            entity_slug="joe-burrow",
            entity_display_name="Joe Burrow",
            program_slug="lsu",
            program_label="LSU",
            era_label="2018–2019",
            statline="60 TD · 6 INT in 2019 · 76.3% completion · 8.9 yards/attempt",
            summary_short=(
                "The platonic ideal of a one-year college quarterback — "
                "5,671 yards and a national title that landed harder than "
                "any single season of the era."
            ),
            editorial_paragraph=(
                "Burrow's 2019 is the season the rest of the era keeps "
                "trying to remember. He arrived at LSU as a transfer from "
                "Ohio State who had thrown 287 passes there across three "
                "years, took a year to settle, and then produced what is, "
                "by any honest reading, the best statistical quarterback "
                "season ever played: 5,671 passing yards, 60 touchdowns, "
                "six interceptions, and a national title in New Orleans "
                "against a Clemson team that had won the previous two "
                "Playoff games it played. The coronation was the Heisman "
                "speech, the cigar in the locker room, and the calm in "
                "every fourth quarter. The number that still does the work "
                "for him is the completion percentage on third down "
                "against pressure — better than every quarterback in "
                "Power-5 football that year by a margin no other season "
                "has touched. He left as the most decorated player of the "
                "era and the easiest first-overall pick in a decade."
            ),
        ),
        _e(
            rank=2,
            entity_slug="tua-tagovailoa",
            entity_display_name="Tua Tagovailoa",
            program_slug="alabama",
            program_label="Alabama",
            era_label="Saban Era · 2017–2019",
            statline="186.6 RTGN as a starter · 87 TD · 11 INT · 69% completion",
            summary_short=(
                "Author of the second-and-26 throw and the modern blueprint "
                "for SEC-quarterback as first-overall reality."
            ),
            editorial_paragraph=(
                "Tua's place is fixed by a single throw — second-and-26, "
                "DeVonta Smith down the seam, January 8 2018, the half "
                "Alabama needed to keep Saban's empire from ceding to a "
                "Hurts-led plateau — but the rank is for the three years "
                "around it. The 2018 season was a 199.4 passer rating "
                "before the SEC Championship hip injury, the kind of "
                "efficiency line that made every analytic departments' "
                "model think it was a printing error. The 2019 season was "
                "incomplete and luminous: he was the Heisman favorite "
                "until the Mississippi State hit, and the surgery that "
                "followed reset the trajectory of the Miami franchise but "
                "did not retroactively undo what the Alabama years were. "
                "Inside the Saban operation he is the quarterback who let "
                "the offense breathe — the pivot from ground-and-pound to "
                "the spread-passing identity that powered six straight "
                "Playoff appearances. Smith, Jeudy, Ruggs, Waddle: every "
                "one of them has a top-twenty NFL draft year because Tua's "
                "floor was that high."
            ),
        ),
        _e(
            rank=3,
            entity_slug="bryce-young",
            entity_display_name="Bryce Young",
            program_slug="alabama",
            program_label="Alabama",
            era_label="Saban Era · 2021",
            statline="2021 Heisman · 4,872 yards · 47 TD · 7 INT · 167.5 RTGN",
            summary_short=(
                "The smallest Heisman quarterback in the trophy's history "
                "and the most precise pocket operator the era has produced."
            ),
            editorial_paragraph=(
                "Bryce Young won the Heisman at 5'10\" and 194 pounds with "
                "a margin of 1,242 first-place votes — the largest margin "
                "in eight years — and he did it by locating throws no one "
                "else on Alabama's roster was capable of locating. The "
                "2021 SEC Championship against Georgia is the master "
                "tape: 421 yards, three touchdowns, the Saban-Smart "
                "rivalry's first proof that the chair could move under "
                "pressure. The only reason 2021 isn't a national title is "
                "the rematch in Indianapolis a month later, when the "
                "Georgia defense — finally healthy and with the run-game "
                "in starting form — flipped the geometry. The 2022 season "
                "added arrhythmia to the legend: a sprained shoulder he "
                "played through, a Tennessee game he lost on the road for "
                "the first time, and the lingering question of whether the "
                "frame could survive the NFL. The frame question belongs "
                "to Carolina now. The Alabama record stands."
            ),
        ),
        # ----------------------------------------------------------------
        # Ranks 4-10: blue-blood era-shapers, sonnet-equivalent
        # ----------------------------------------------------------------
        _e(
            rank=4,
            entity_slug="caleb-williams",
            entity_display_name="Caleb Williams",
            program_slug="usc",
            program_label="USC",
            era_label="Riley Era · 2022–2023",
            statline="2022 Heisman · 10,082 career passing yards · 93 TD · 14 INT",
            summary_short=(
                "Bridged the Oklahoma–USC Lincoln Riley transition and "
                "won the Heisman doing it in his first year as a starter "
                "at his second program."
            ),
            editorial_paragraph=(
                "Williams is the Riley-era avatar — the 2022 Heisman "
                "winner whose campaign was the cleanest single-year "
                "argument the trophy has seen since Mayfield. He moved "
                "from Norman to Los Angeles inside Riley's portal exit "
                "and immediately won 11 games for a USC program that had "
                "been irrelevant in its conference since the BCS years. "
                "The line that does the work: 4,537 yards and 42 "
                "touchdowns against ten interceptions in a Pac-12 schedule "
                "that asked him to throw 60 times some weeks. The 2023 "
                "season — Pac-12 in dissolution, the offensive-line "
                "unraveling, his receiver corps thin after Addison's "
                "departure — was where the criticism started, mostly "
                "unfair, and where the Bears decided he was their "
                "first-overall pick. He is the era's portrait of "
                "quarterback as roster-architect, the player a program "
                "is built around rather than the player a program "
                "produces."
            ),
        ),
        _e(
            rank=5,
            entity_slug="devonta-smith",
            entity_display_name="DeVonta Smith",
            program_slug="alabama",
            program_label="Alabama",
            era_label="Saban Era · 2018–2020",
            statline="2020 Heisman (1st WR since '91) · 3,965 career rec yds · 46 TD",
            summary_short=(
                "First wide receiver to win the Heisman since Desmond "
                "Howard — and the only one to win it after catching the "
                "throw that won a national title."
            ),
            editorial_paragraph=(
                "Smith's 2020 — 1,856 receiving yards, 23 touchdowns, the "
                "Heisman, the title, the Mac Jones partnership that made "
                "the season look easier than it was — was the natural "
                "endpoint of an arc that began on second-and-26. He was "
                "117 pounds when he committed to Alabama and 175 the "
                "week he won the trophy; the frame was always the "
                "argument against, the route-running was always the "
                "answer. The Slim Reaper nickname doesn't capture how "
                "much of the game was won at the line of scrimmage on "
                "releases against press, against bracket, against safeties "
                "who knew the ball was coming. He is the receiver every "
                "modern coordinator now tries to draft — the one who "
                "wins separation before the snap is fully arrived."
            ),
        ),
        _e(
            rank=6,
            entity_slug="lamar-jackson",
            entity_display_name="Lamar Jackson",
            program_slug="louisville",
            program_label="Louisville",
            era_label="Petrino Era · 2015–2017",
            statline="2016 Heisman · 9,043 career pass yds · 4,132 rush yds · 119 TD",
            summary_short=(
                "Reinvented the quarterback position so completely that "
                "the rest of the era is still arguing about how to grade it."
            ),
            editorial_paragraph=(
                "Jackson's 2016 — 51 total touchdowns, 4,929 total yards, "
                "the Heisman won by the largest margin since Ingram-over-"
                "Gerhart — was a season the sport's evaluators didn't have "
                "a vocabulary for. He played in the ACC at Louisville for "
                "Bobby Petrino, a program that would not contend, on a "
                "roster that did not deserve him, and he produced the "
                "kind of season that retroactively made the position "
                "broader than every coaching tree had assumed. The 2017 "
                "follow-up — 3,660 passing, 1,601 rushing, 45 total "
                "touchdowns — was statistically better in the ways that "
                "ought to matter, and a 9-4 finish meant zero national "
                "conversation. The draft slot was the punishment for "
                "playing in the wrong league at the wrong moment. The "
                "two NFL MVPs are the receipt the college vote owed."
            ),
        ),
        _e(
            rank=7,
            entity_slug="jayden-daniels",
            entity_display_name="Jayden Daniels",
            program_slug="lsu",
            program_label="LSU",
            era_label="Kelly Era · 2022–2023",
            statline="2023 Heisman · 3,812 pass + 1,134 rush · 50 total TD · 11.7 Y/A",
            summary_short=(
                "The 2023 Heisman season's efficiency was so extreme it "
                "broke the comparative shelf — only Burrow's 2019 sits "
                "near it."
            ),
            editorial_paragraph=(
                "Daniels' 2023 was the second-best dual-threat season ever "
                "produced — Cam Newton 2010 is the only one in front of "
                "it on most ledgers, and Newton played fewer games. The "
                "yards-per-attempt was 11.7, the highest of any FBS "
                "starter that season by margin, and the rushing line "
                "(1,134 yards, 10 touchdowns) was a starter's whole "
                "season for most quarterbacks of the era. He arrived at "
                "LSU as a transfer from Arizona State, gave Brian Kelly "
                "his first signature year in Baton Rouge, and made the "
                "Florida game (372 passing, 234 rushing, four touchdowns "
                "with two minutes left) the master tape of the year. The "
                "Commanders took him second overall and got the rookie "
                "season the Saints had hoped for from Caleb in 2024. He "
                "is the era's best argument that the modernized "
                "dual-threat — pocket-stable, then explosive — is the "
                "ceiling of the position, not the floor."
            ),
        ),
        _e(
            rank=8,
            entity_slug="derrick-henry",
            entity_display_name="Derrick Henry",
            program_slug="alabama",
            program_label="Alabama",
            era_label="Saban Era · 2014–2015",
            statline="2015 Heisman · 2,219 rush yds · 28 TD · 6.0 ypc · NCAA SEC record",
            summary_short=(
                "The last Heisman won by a back who carried it 395 times "
                "and the closing argument for the throwback bell-cow."
            ),
            editorial_paragraph=(
                "Henry's 2015 is the running-back season the era will not "
                "produce again — 395 carries, 2,219 rushing yards, 28 "
                "touchdowns, an SEC single-season record that broke "
                "Bo Jackson's, and a national title that was decided in "
                "Glendale on a 75-yard touchdown that ended the Clemson "
                "comeback. Saban put the offense in his hands the week "
                "after Tennessee in October, and from then to the title "
                "game Henry averaged 192 carries a month. The body type "
                "(6'3\", 247) was the argument against him as a Heisman "
                "candidate until November, and then the body type was the "
                "argument for him in every fourth quarter. The Titans "
                "took him 45th overall, which the rest of that draft "
                "class never lived down. He is the era's bookmark for "
                "the moment when a program could still win a national "
                "title with a running back as the offensive identity."
            ),
        ),
        _e(
            rank=9,
            entity_slug="trevor-lawrence",
            entity_display_name="Trevor Lawrence",
            program_slug="clemson",
            program_label="Clemson",
            era_label="Swinney Era · 2018–2020",
            statline="34-2 as a starter · 90 TD · 17 INT · '18 NCG win as a freshman",
            summary_short=(
                "True-freshman national title in the Santa Clara rout "
                "and three full seasons as the most-anticipated NFL "
                "first overall in a decade."
            ),
            editorial_paragraph=(
                "Lawrence is the era's pre-ordained quarterback — the "
                "blue-chip-of-blue-chips who arrived in Clemson in 2018, "
                "took the starting job from Kelly Bryant by week six, and "
                "won the national title against Alabama in Santa Clara "
                "44-16 as a true freshman. The 25-2 record across "
                "2018-2019 was the most dominant two-year run by a "
                "quarterback in the era. The 2020 season — 10-1 in the "
                "regular season, a positive COVID test that cost him the "
                "Notre Dame ACC Championship rematch, the Sugar Bowl loss "
                "to Ohio State that ended his college career on a sour "
                "down — undersold the body of work, and the two NFL "
                "championship-game appearances since don't change what "
                "the Clemson years were. He is the closest thing the era "
                "has to an Andrew Luck: the prospect every other team's "
                "war room treated as a season-long argument-ender."
            ),
        ),
        _e(
            rank=10,
            entity_slug="will-anderson-jr",
            entity_display_name="Will Anderson Jr.",
            program_slug="alabama",
            program_label="Alabama",
            era_label="Saban Era · 2020–2022",
            statline="34.5 career sacks · 58.5 TFL · 2x Bednarik · 2x Lombardi",
            summary_short=(
                "The most decorated defender of the era and the closest "
                "thing the modern game has produced to a Suh-level "
                "non-secondary disruptor."
            ),
            editorial_paragraph=(
                "Anderson's three years at Alabama — 2020, 2021, 2022 — "
                "produced 34.5 sacks, 58.5 tackles for loss, two Bednarik "
                "Awards, two Lombardi Awards, and a Heisman finish in "
                "2022 that was the first by an off-ball edge since Manti "
                "Te'o. He is the answer to the question of who replaces "
                "Quinnen Williams in the era's ledger: the defender every "
                "left tackle's tape-grinding week was built around. The "
                "Texans took him third overall in 2023, and the Tide's "
                "back-to-back Playoff appearances during his tenure are "
                "inseparable from his presence on third down."
            ),
        ),
        # ----------------------------------------------------------------
        # Ranks 11-25: era cornerstones, sonnet-equivalent paragraphs
        # ----------------------------------------------------------------
        _e(
            rank=11,
            entity_slug="kyler-murray",
            entity_display_name="Kyler Murray",
            program_slug="oklahoma",
            program_label="Oklahoma",
            era_label="Riley Era · 2018",
            statline="2018 Heisman · 4,361 pass + 1,001 rush · 54 total TD",
            summary_short=(
                "The Heisman-and-MLB-first-rounder year — the cleanest "
                "single-season case the position has produced in the "
                "spread era."
            ),
            editorial_paragraph=(
                "Murray's 2018 was the ninth-overall MLB pick spending a "
                "Saturday autumn winning the Heisman by a margin nobody "
                "expected against a runner-up (Tua) playing the best "
                "season of his life. The numbers — 4,361 yards through "
                "the air, 1,001 yards on the ground, a 199.2 passer "
                "rating that was the second-best in FBS history at the "
                "time, 54 total touchdowns, an Orange Bowl semifinal "
                "loss to Alabama where he passed for 308 in defeat — "
                "are the actual best CFP-era statistical year by a "
                "quarterback besides Burrow 2019. The first-overall NFL "
                "pick six months later was the receipt. Riley's "
                "Oklahoma identity — quarterback as throne, three "
                "Heismans in four years — runs through this season."
            ),
        ),
        _e(
            rank=12,
            entity_slug="baker-mayfield",
            entity_display_name="Baker Mayfield",
            program_slug="oklahoma",
            program_label="Oklahoma",
            era_label="Stoops/Riley Era · 2014–2017",
            statline="2017 Heisman · 12,292 career pass yds · 131 TD · 30 INT",
            summary_short=(
                "Walked on at Texas Tech, transferred to Oklahoma, "
                "won the 2017 Heisman, and gave the era its first "
                "Big-12-quarterback-as-portrait."
            ),
            editorial_paragraph=(
                "Mayfield's 2017 — 4,627 yards, 43 touchdowns, six "
                "interceptions, an Orange Bowl loss to Georgia in the "
                "Playoff semifinal that ended his career — is the "
                "Heisman season where the trophy belonged to the "
                "argument as much as the line. He arrived at Oklahoma as "
                "a walk-on who'd already started at Texas Tech, a "
                "circumstance that is now in the trivia book and was, at "
                "the time, in the why-this-shouldn't-work column. The "
                "Browns took him first overall in 2018; the Buccaneers "
                "have him on the back end of a career that has finally "
                "settled. The Oklahoma legacy is intact."
            ),
        ),
        _e(
            rank=13,
            entity_slug="jalen-hurts",
            entity_display_name="Jalen Hurts",
            program_slug="oklahoma",
            program_label="Oklahoma",
            era_label="Saban → Riley · 2016–2019",
            statline="38-4 starter record · 9,477 pass + 3,274 rush · 121 TD",
            summary_short=(
                "Two SEC titles at Alabama, a Heisman runner-up at "
                "Oklahoma after the transfer, and the era's portrait of "
                "the quarterback who outgrew his benching."
            ),
            editorial_paragraph=(
                "Hurts started 28 games at Alabama, won 26, lost the "
                "starting job at halftime of the 2018 national title to "
                "Tua, came back in the SEC Championship that next "
                "December to win the conference title in relief, and then "
                "transferred to Oklahoma to be a Heisman runner-up under "
                "Riley. The trajectory — undersized SEC starter who "
                "becomes the era's most accomplished quarterback "
                "transfer story — anchors a top-15 placement that the "
                "NFL trajectory has only made more legible. He is the "
                "era's closest thing to a player who made the second-act "
                "the master tape."
            ),
        ),
        _e(
            rank=14,
            entity_slug="quinnen-williams",
            entity_display_name="Quinnen Williams",
            program_slug="alabama",
            program_label="Alabama",
            era_label="Saban Era · 2018",
            statline="2018 Outland · 19.5 TFL · 8 sacks · 71 tackles as a 3-tech",
            summary_short=(
                "The era's purest interior-line season — 19.5 tackles "
                "for loss from the three-technique, no NFL career has "
                "yet eclipsed the college version."
            ),
            editorial_paragraph=(
                "Williams' 2018 was the kind of season offensive "
                "coordinators built protections around. He won the "
                "Outland Trophy as a redshirt sophomore at a position "
                "that doesn't usually get the trophy, and his 19.5 "
                "tackles for loss are still the gold standard for an "
                "interior-line season in the era. The Jets took him third "
                "overall and have largely failed to surround him with "
                "anything; the Alabama version, against the SEC West and "
                "the Playoff, remains the master tape. He is the "
                "argument for why the position-by-position list of the "
                "CFP era still has interior defensive line in the top 20."
            ),
        ),
        _e(
            rank=15,
            entity_slug="jameis-winston",
            entity_display_name="Jameis Winston",
            program_slug="florida-state",
            program_label="Florida State",
            era_label="Fisher Era · 2013–2014",
            statline="2013 Heisman · 26-1 starter · '13 NCG win",
            summary_short=(
                "The 2013 Heisman, the BCS title in Pasadena, and the "
                "starting point for everything Florida State spent the "
                "next decade trying to recover."
            ),
            editorial_paragraph=(
                "Winston's eligibility window technically began in the "
                "BCS era, but his 2014 — 13-1, an undefeated regular "
                "season that ended in the Rose Bowl semifinal loss to "
                "Oregon — is the bridge into the CFP era and earns the "
                "placement here. The 2013 Heisman is the foundational "
                "fact: 4,057 yards, 40 touchdowns, 10 interceptions, the "
                "BCS title win against Auburn, the first national title "
                "won by a freshman since the 1980s. The off-field "
                "complications and the NFL trajectory are not in this "
                "list's scope. The Florida State era he represents — "
                "the Fisher peak before the program's collapse — is."
            ),
        ),
        _e(
            rank=16,
            entity_slug="bo-nix",
            entity_display_name="Bo Nix",
            program_slug="oregon",
            program_label="Oregon",
            era_label="Lanning Era · 2022–2023",
            statline="34-7 starter · 3 schools · 92 TD · 11 INT (Oregon yrs)",
            summary_short=(
                "The portal-era's most successful arc — Auburn freshman "
                "to Heisman finalist at Oregon — and the proof of "
                "concept for the Lanning rebuild."
            ),
            editorial_paragraph=(
                "Nix's three years at Oregon (2022 transfer, 2023 "
                "Heisman finalist, 2024 Pac-12-killer with the Big Ten "
                "transition coming) were the Lanning operation's "
                "showcase. The 2023 season — 4,508 passing yards, 45 "
                "touchdowns, three interceptions across 14 games, a "
                "Pac-12 Championship loss to Washington that decided the "
                "last Pac-12 title — was the best year a Pac-12 "
                "quarterback produced in the era and the cleanest "
                "argument the conference made for its own continued "
                "relevance before the breakup. The Broncos took him "
                "12th overall in 2024."
            ),
        ),
        _e(
            rank=17,
            entity_slug="mac-jones",
            entity_display_name="Mac Jones",
            program_slug="alabama",
            program_label="Alabama",
            era_label="Saban Era · 2020",
            statline="2020 NCG win · 4,500 pass yds · 41 TD · 4 INT · 77.4% comp",
            summary_short=(
                "The 2020 Alabama-undefeated season — and the cleanest "
                "supporting-cast quarterback year of the era."
            ),
            editorial_paragraph=(
                "Jones inherited the Tua starting job in 2020 and ran "
                "the Alabama operation to 13-0, a national title against "
                "Ohio State, and a 77.4% completion rate that's the "
                "highest a Power-5 starter has ever posted. The "
                "supporting cast (Smith, Waddle, Najee Harris, four NFL "
                "first-rounders on offense) was the best ever assembled "
                "in the era; the question of how much the season was "
                "Jones and how much it was the cast was settled by "
                "the games where the cast was hurt. He delivered on "
                "those weeks too. The Patriots took him 15th overall."
            ),
        ),
        _e(
            rank=18,
            entity_slug="ed-oliver",
            entity_display_name="Ed Oliver",
            program_slug="houston",
            program_label="Houston",
            era_label="Herman/Applewhite · 2016–2018",
            statline="192 tackles · 53 TFL · 13.5 sacks · 1st DT to win Outland in '17",
            summary_short=(
                "The era's defining Group-of-Five player — and an "
                "argument for why the playoff bracket should never have "
                "been four teams."
            ),
            editorial_paragraph=(
                "Oliver was the kind of recruit who shouldn't have been "
                "at Houston — five-star defensive tackle, the first the "
                "program had ever signed — and his three-year career "
                "(2016–2018) was the era's most consequential defensive "
                "tape played outside the Power-5. He won the Outland "
                "in 2017 as a sophomore, the first defensive tackle to "
                "do it. The Bills took him ninth overall in 2019. The "
                "Houston bowl-eligible seasons during his tenure are "
                "the program's Group-of-Five high-water mark, and the "
                "rest of the era's interior-line evaluation is graded "
                "against his tape."
            ),
        ),
        _e(
            rank=19,
            entity_slug="ezekiel-elliott",
            entity_display_name="Ezekiel Elliott",
            program_slug="ohio-state",
            program_label="Ohio State",
            era_label="Meyer Era · 2014–2015",
            statline="2014 NCG MVP · 2x 1,800-yd seasons · 696 yds in '14 Playoff",
            summary_short=(
                "The 2014 inaugural-Playoff MVP and the back who turned "
                "the bracket from speculation to canon."
            ),
            editorial_paragraph=(
                "Elliott's 696 rushing yards across the three 2014 "
                "Playoff games — the Big Ten Championship rout of "
                "Wisconsin, the Sugar Bowl win over Alabama, the title "
                "game in Arlington against Oregon — is the line that "
                "made the inaugural Playoff bracket feel earned. The "
                "Cardale Jones third-string starter situation only "
                "worked because the offensive line was Big Ten's best "
                "and Elliott was the era's best one-cut zone-runner. "
                "The Cowboys took him fourth overall in 2016 and got the "
                "rookie season every projection had promised."
            ),
        ),
        _e(
            rank=20,
            entity_slug="cj-stroud",
            entity_display_name="C.J. Stroud",
            program_slug="ohio-state",
            program_label="Ohio State",
            era_label="Day Era · 2021–2022",
            statline="85 TD · 12 INT · 85.4% comp in '22 Peach Bowl semifinal vs UGA",
            summary_short=(
                "The Day-era Buckeye who ran the offense at the highest "
                "yards-per-attempt of any Power-5 starter in 2022."
            ),
            editorial_paragraph=(
                "Stroud's 2022 ended in the Peach Bowl semifinal against "
                "Georgia — 348 passing yards, four touchdowns, no "
                "interceptions, the only blemish a missed deep ball to "
                "Marvin Harrison Jr. that would have won the game. He "
                "was second in the Heisman vote two years running "
                "without ever winning it, and the Texans took him "
                "second overall in 2023 (where he was Offensive Rookie "
                "of the Year). The Day-era Buckeye trajectory — back-to-"
                "back Heisman runners-up in Stroud and Harrison — runs "
                "through this season."
            ),
        ),
        _e(
            rank=21,
            entity_slug="leonard-fournette",
            entity_display_name="Leonard Fournette",
            program_slug="lsu",
            program_label="LSU",
            era_label="Miles Era · 2014–2016",
            statline="3,830 career rush yds · 40 TD · 6.2 ypc · 2015 Doak Walker",
            summary_short=(
                "The 2015 SEC season that made the recruiting service "
                "industry believe its own pre-draft hype on a back."
            ),
            editorial_paragraph=(
                "Fournette's 2015 — 1,953 rushing yards, 22 touchdowns, "
                "the Doak Walker, the only Heisman finalist who carried "
                "an entire offense through the SEC West and finished "
                "second to Henry — was the recruiting industry's most "
                "completely realized projection of the era. He was the "
                "consensus number-one running-back recruit in 2014 and "
                "was an All-American by the next December. The Jaguars "
                "took him fourth overall in 2017 and the NFL trajectory "
                "was less straightforward than the LSU years; the "
                "Baton Rouge body of work (the Florida game, the "
                "Texas A&M Thanksgiving rout) is the placement."
            ),
        ),
        _e(
            rank=22,
            entity_slug="myles-garrett",
            entity_display_name="Myles Garrett",
            program_slug="texas-am",
            program_label="Texas A&M",
            era_label="Sumlin Era · 2014–2016",
            statline="32.5 career sacks · 47 TFL · '17 first-overall NFL pick",
            summary_short=(
                "The first-overall pick whose three-year College Station "
                "run produced the era's most consistent edge tape."
            ),
            editorial_paragraph=(
                "Garrett's three years at Texas A&M (2014–2016) were "
                "the era's textbook for an off-ball-edge career: 32.5 "
                "sacks, 47 tackles for loss, the kind of separation off "
                "the snap that made him the first-overall pick and the "
                "Browns' rebuild cornerstone. He is the era's bookmark "
                "for what the position can be when the body type is "
                "Combine-perfect and the tape is consistent across "
                "three years; the SEC schedules he played were the "
                "right test."
            ),
        ),
        _e(
            rank=23,
            entity_slug="travis-hunter",
            entity_display_name="Travis Hunter",
            program_slug="colorado",
            program_label="Colorado",
            era_label="Sanders Era · 2023–2024",
            statline="2024 Heisman · 96 catches · 1,258 rec yds · 4 INT · two-way",
            summary_short=(
                "The first two-way Heisman in 27 years and the closest "
                "thing the modern era has produced to a player playing "
                "the wrong sport."
            ),
            editorial_paragraph=(
                "Hunter's 2024 — 96 catches for 1,258 yards as a "
                "receiver, four interceptions and 11 PBUs as a corner, "
                "1,400 snaps total, the Heisman won as a two-way player "
                "for the first time since Charles Woodson in 1997 — was "
                "the season the rest of the sport spent trying to "
                "explain. He was a five-star recruit who flipped from "
                "Florida State to Jackson State because Deion Sanders "
                "was running it, then followed Sanders to Colorado "
                "for 2023, and ran the program's resurrection. The "
                "Jaguars took him second overall in 2025. The Colorado "
                "season that put Sanders' program on the national "
                "schedule is inseparable from his presence on both "
                "sides of the ball."
            ),
        ),
        _e(
            rank=24,
            entity_slug="marvin-harrison-jr",
            entity_display_name="Marvin Harrison Jr.",
            program_slug="ohio-state",
            program_label="Ohio State",
            era_label="Day Era · 2022–2023",
            statline="155 catches · 2,613 rec yds · 31 TD across two starting yrs",
            summary_short=(
                "The era's most credentialed receiver — Biletnikoff and "
                "fourth-overall pick — and the Day-era Buckeye visual "
                "identity."
            ),
            editorial_paragraph=(
                "Harrison's two years as the Buckeye number-one — "
                "2022 (1,263 yards, 14 TDs) and 2023 (1,211 yards, 14 "
                "TDs) — were the receiver tape every coordinator in "
                "the league spent the offseason studying. The Cardinals "
                "took him fourth overall in 2024. He is the receiver "
                "the era will remember as the cleanest ten-game film "
                "since Calvin Johnson, and the Stroud–Harrison "
                "partnership at Ohio State is the Day-era's most "
                "coherent two-year stretch."
            ),
        ),
        _e(
            rank=25,
            entity_slug="aidan-hutchinson",
            entity_display_name="Aidan Hutchinson",
            program_slug="michigan",
            program_label="Michigan",
            era_label="Harbaugh Era · 2021",
            statline="2021 Heisman runner-up · 14 sacks · '21 Big Ten title",
            summary_short=(
                "Heisman runner-up as an edge defender, the first "
                "Michigan-Ohio State win in eight years, and the "
                "captain of the program's CFP-era turning point."
            ),
            editorial_paragraph=(
                "Hutchinson's 2021 — 14 sacks, 16.5 tackles for loss, "
                "the Heisman runner-up vote behind Bryce Young, the "
                "Big Ten title that ended Ohio State's eight-year "
                "stranglehold on the rivalry — was the season that "
                "started the Michigan run that ended in Houston in "
                "January 2024 with a national title. He was a captain "
                "and the program's emotional center; the Lions took him "
                "second overall in 2022. The legacy is that the "
                "Michigan revival had a face."
            ),
        ),
        # ----------------------------------------------------------------
        # Ranks 26-100: one-liners only (sonnet-equivalent, terse)
        # ----------------------------------------------------------------
        _e(rank=26, entity_slug="dak-prescott", entity_display_name="Dak Prescott",
           program_slug="mississippi-state", program_label="Mississippi State",
           era_label="Mullen Era · 2014–2015", statline="70 career TD · 23-15 starter",
           summary_short=(
               "The 2014 Mississippi State season that briefly held the AP "
               "number-one ranking — and the SEC West's first portrait of "
               "the dual-threat era arriving."
           )),
        _e(rank=27, entity_slug="josh-allen-quarterback",
           entity_display_name="Josh Allen", program_slug="wyoming",
           program_label="Wyoming", era_label="2016–2017",
           statline="44 TD · 21 INT · 1,063 career rush yds",
           summary_short=(
               "The Mountain-West quarterback whose Wyoming tape made "
               "the Bills draft him seventh overall and gave the era "
               "its loudest small-school NFL outcome."
           )),
        _e(rank=28, entity_slug="josh-allen-edge",
           entity_display_name="Josh Allen (edge)",
           program_slug="kentucky", program_label="Kentucky", era_label="2017–2018",
           statline="2018 Bednarik · 17 sacks · 88 tackles as a senior",
           summary_short=(
               "The 2018 Kentucky senior who won the Bednarik and the "
               "Nagurski as the only player in history to win both in the "
               "same season."
           )),
        _e(rank=29, entity_slug="amari-cooper", entity_display_name="Amari Cooper",
           program_slug="alabama", program_label="Alabama", era_label="2014",
           statline="2014 Biletnikoff · 124 catches · 1,727 rec yds · 16 TD",
           summary_short=(
               "The Saban-era receiver template — the 2014 Biletnikoff "
               "season that retroactively explains every five-star "
               "wideout Tuscaloosa has signed since."
           )),
        _e(rank=30, entity_slug="josh-jacobs", entity_display_name="Josh Jacobs",
           program_slug="alabama", program_label="Alabama", era_label="2018",
           statline="640 career rush yds · 6.3 ypc · 1st-rd NFL pick",
           summary_short=(
               "The third-down back nobody outside the Alabama building "
               "knew was carrying the offense until the Raiders made "
               "him a first-rounder in 2019."
           )),
        _e(rank=31, entity_slug="cam-akers", entity_display_name="Cam Akers",
           program_slug="florida-state", program_label="Florida State",
           era_label="2017–2019", statline="2,875 career rush yds · 27 TD",
           summary_short=(
               "The Florida-State-in-decline back who carried the offense "
               "across three coaching staffs and made the Rams second-round "
               "investment look like a steal."
           )),
        _e(rank=32, entity_slug="dwayne-haskins", entity_display_name="Dwayne Haskins",
           program_slug="ohio-state", program_label="Ohio State", era_label="2018",
           statline="50 TD · 8 INT · 4,831 pass yds · '18 Big Ten title",
           summary_short=(
               "The 2018 single-season passing record at Ohio State — and "
               "the Heisman finalist whose post-college trajectory cannot "
               "be allowed to retroactively diminish what the year was."
           )),
        _e(rank=33, entity_slug="nick-bosa", entity_display_name="Nick Bosa",
           program_slug="ohio-state", program_label="Ohio State", era_label="2017–2018",
           statline="17.5 career sacks · '19 second-overall NFL pick",
           summary_short=(
               "The Bosa-line-of-Ohio-State edge tradition continued — and "
               "the 2018 injury that cost the Buckeyes a Playoff trip "
               "ended his college career too early."
           )),
        _e(rank=34, entity_slug="quinn-ewers", entity_display_name="Quinn Ewers",
           program_slug="texas", program_label="Texas",
           era_label="Sarkisian Era · 2022–2024",
           statline="58 TD · 23 INT · '23 Big-12 title · '23 CFP semifinal",
           summary_short=(
               "The portal-era five-star who ran the Sarkisian Texas "
               "rebuild, lost the Heisman race twice, and bridged the "
               "program's Big-12-to-SEC pivot."
           )),
        _e(rank=35, entity_slug="bijan-robinson", entity_display_name="Bijan Robinson",
           program_slug="texas", program_label="Texas", era_label="2020–2022",
           statline="3,410 career rush yds · 6.0 ypc · '23 8th-overall pick",
           summary_short=(
               "The Texas rebuild's bridge back — the running-back season "
               "that retroactively justified the recruiting apparatus the "
               "Sarkisian regime inherited."
           )),
        _e(rank=36, entity_slug="kenny-pickett", entity_display_name="Kenny Pickett",
           program_slug="pittsburgh", program_label="Pittsburgh",
           era_label="Narduzzi Era · 2021",
           statline="2021 ACC Player of the Year · 42 TD · 7 INT",
           summary_short=(
               "The 2021 Pittsburgh season where the program won an ACC "
               "title nobody had picked them for — and the era's "
               "purest fifth-year-senior breakout."
           )),
        _e(rank=37, entity_slug="kenneth-walker-iii",
           entity_display_name="Kenneth Walker III",
           program_slug="michigan-state", program_label="Michigan State",
           era_label="Tucker Era · 2021",
           statline="2021 Doak Walker · 1,636 rush yds · 18 TD",
           summary_short=(
               "The Wake Forest transfer who made Michigan State an "
               "unranked-to-ranked-eleven story in November 2021 and won "
               "the Doak doing it."
           )),
        _e(rank=38, entity_slug="jonathan-taylor",
           entity_display_name="Jonathan Taylor", program_slug="wisconsin",
           program_label="Wisconsin", era_label="2017–2019",
           statline="6,174 career rush yds · 50 TD · 2x Doak Walker",
           summary_short=(
               "The Wisconsin three-year run that put back-to-back Doak "
               "Walkers on the same back and made the early-2010s "
               "Big-Ten-power-back identity portable into the late decade."
           )),
        _e(rank=39, entity_slug="ja-marr-chase",
           entity_display_name="Ja'Marr Chase", program_slug="lsu",
           program_label="LSU", era_label="2019",
           statline="84 catches · 1,780 rec yds · 20 TD · '19 Biletnikoff",
           summary_short=(
               "The 2019 LSU number-one — Burrow's deepest target, "
               "Biletnikoff winner, and the receiver the rest of the "
               "decade's wideout tape gets compared against."
           )),
        _e(rank=40, entity_slug="justin-jefferson",
           entity_display_name="Justin Jefferson", program_slug="lsu",
           program_label="LSU", era_label="2018–2019",
           statline="111 catches · 1,540 rec yds · 18 TD in '19",
           summary_short=(
               "The 2019 LSU slot — the receiver Burrow trusted on every "
               "third down, the player who slipped to 22nd overall, and "
               "the NFL's current best route-runner."
           )),
        _e(rank=41, entity_slug="cam-taylor-britt",
           entity_display_name="Sam Hubbard", program_slug="ohio-state",
           program_label="Ohio State", era_label="2017",
           statline="13.5 career sacks · 7.0 in '17 alone",
           summary_short=(
               "The Ohio State edge whose four-year body of work produced "
               "the 2017 sack title — and the cleanest Big Ten "
               "edge-defender film of the late-2010s."
           )),
        _e(rank=42, entity_slug="tre-davious-white",
           entity_display_name="Tre'Davious White", program_slug="lsu",
           program_label="LSU", era_label="2014–2016",
           statline="6 INT · 38 PBU · 2x All-SEC corner",
           summary_short=(
               "The LSU corner who anchored the secondary across the "
               "Miles-to-Orgeron transition and went 27th overall to the "
               "Bills."
           )),
        _e(rank=43, entity_slug="brian-burns", entity_display_name="Brian Burns",
           program_slug="florida-state", program_label="Florida State",
           era_label="2016–2018", statline="23 career sacks · '19 16th-overall pick",
           summary_short=(
               "The Florida State edge whose three-year sack production "
               "continued through the Fisher-to-Taggart transition and "
               "got the Panthers a building-block defender."
           )),
        _e(rank=44, entity_slug="trey-hendrickson",
           entity_display_name="Reese's Senior Bowl invitee · Trey Hendrickson",
           program_slug="florida-atlantic", program_label="FAU",
           era_label="2014–2016", statline="29.5 career sacks · 9.5 in '16",
           summary_short=(
               "The Group-of-Five edge tape that went third-round but "
               "vindicated the projection — the Bengals are still the "
               "beneficiaries."
           )),
        _e(rank=45, entity_slug="andrew-thomas",
           entity_display_name="Andrew Thomas", program_slug="georgia",
           program_label="Georgia", era_label="Smart Era · 2017–2019",
           statline="3-year starter at LT · '20 4th-overall pick",
           summary_short=(
               "The Georgia tackle whose three-year run as the Smart "
               "regime's left-tackle anchor produced the cleanest "
               "first-round pass-protection résumé of the era."
           )),
        _e(rank=46, entity_slug="jalen-carter", entity_display_name="Jalen Carter",
           program_slug="georgia", program_label="Georgia",
           era_label="Smart Era · 2020–2022",
           statline="3-time CFP semifinalist · 2x national champ",
           summary_short=(
               "The interior defender who rotated through the back-to-back "
               "Georgia title teams and went ninth overall as the most "
               "obvious draft-day argument of the 2023 class."
           )),
        _e(rank=47, entity_slug="jamaree-salyer",
           entity_display_name="Stetson Bennett",
           program_slug="georgia", program_label="Georgia",
           era_label="Smart Era · 2020–2022",
           statline="29-3 career record · 2x national champ · '22 Heisman finalist",
           summary_short=(
               "The walk-on who started the back-to-back Georgia title "
               "runs, won SEC Player of the Year in '22, and made the "
               "Smart program's identity legible to a national audience."
           )),
        _e(rank=48, entity_slug="brock-bowers", entity_display_name="Brock Bowers",
           program_slug="georgia", program_label="Georgia",
           era_label="Smart Era · 2021–2023",
           statline="175 catches · 2,538 rec yds · 26 TD as a TE",
           summary_short=(
               "The 2023 Mackey winner who reset the era's tight-end "
               "evaluation — the Raiders took him 13th overall and "
               "regretted nothing."
           )),
        _e(rank=49, entity_slug="rashan-gary", entity_display_name="Rashan Gary",
           program_slug="michigan", program_label="Michigan",
           era_label="Harbaugh Era · 2016–2018",
           statline="9.5 career sacks · '19 12th-overall pick",
           summary_short=(
               "The Michigan five-star who never put up the headline sack "
               "totals but whose three-year tape was the most consistent "
               "edge film the early-Harbaugh era produced."
           )),
        _e(rank=50, entity_slug="reggie-white-namesake",
           entity_display_name="Roquan Smith",
           program_slug="georgia", program_label="Georgia",
           era_label="Smart Era · 2017",
           statline="2017 Butkus · 137 tackles · 6.5 sacks · 14 TFL",
           summary_short=(
               "The 2017 Butkus winner who anchored the 13-2 Georgia run "
               "to the national title game and went eighth overall to the "
               "Bears as the era's prototype off-ball linebacker."
           )),
        _e(rank=51, entity_slug="ryan-finley",
           entity_display_name="Sam Darnold",
           program_slug="usc", program_label="USC", era_label="2016–2017",
           statline="57 career TD · 22 INT · '17 Rose Bowl OT win vs Penn State",
           summary_short=(
               "The USC quarterback whose 2017 Rose Bowl overtime win was "
               "the program's CFP-era high-water mark before the Riley arrival."
           )),
        _e(rank=52, entity_slug="jalen-mills",
           entity_display_name="J.J. McCarthy",
           program_slug="michigan", program_label="Michigan",
           era_label="Harbaugh Era · 2022–2023",
           statline="27-1 starter · '23 NCG win · 72 career TD · 11 INT",
           summary_short=(
               "The Michigan starter who finished the back-to-back-to-"
               "back Big Ten title run with a national championship and "
               "got the Vikings to take him 10th overall."
           )),
        _e(rank=53, entity_slug="penei-sewell",
           entity_display_name="Penei Sewell", program_slug="oregon",
           program_label="Oregon", era_label="2018–2019",
           statline="2019 Outland · '20 Pac-12 OL of the year · '21 7th-overall pick",
           summary_short=(
               "The Oregon left tackle whose 2019 Outland season was "
               "the cleanest pass-protection film a college tackle has "
               "produced in the era."
           )),
        _e(rank=54, entity_slug="deebo-samuel",
           entity_display_name="Deebo Samuel", program_slug="south-carolina",
           program_label="South Carolina", era_label="2014–2018",
           statline="148 catches · 2,070 rec yds · 19 TD",
           summary_short=(
               "The South Carolina receiver whose injury-shortened "
               "senior year still produced the tape that made him a "
               "second-round pick and a Niners' All-Pro."
           )),
        _e(rank=55, entity_slug="rondale-moore",
           entity_display_name="Rondale Moore", program_slug="purdue",
           program_label="Purdue", era_label="2018",
           statline="114 catches · 1,258 rec yds · 12 TD as a true freshman",
           summary_short=(
               "The Purdue freshman whose 2018 season briefly made the "
               "program a top-15 conversation and produced the Ohio State "
               "upset that year."
           )),
        _e(rank=56, entity_slug="garrett-wilson",
           entity_display_name="Garrett Wilson", program_slug="ohio-state",
           program_label="Ohio State", era_label="2019–2021",
           statline="143 catches · 2,213 rec yds · 23 TD",
           summary_short=(
               "The Buckeye receiver whose three-year run produced the "
               "cleanest separation tape of the Day era and the Jets' "
               "rookie-of-the-year season."
           )),
        _e(rank=57, entity_slug="chris-olave",
           entity_display_name="Chris Olave", program_slug="ohio-state",
           program_label="Ohio State", era_label="2018–2021",
           statline="176 catches · 2,711 rec yds · 35 TD",
           summary_short=(
               "The Buckeye receiver whose four-year run made Ohio "
               "State's wideout room the era's best — Saints first-round "
               "pick in 2022."
           )),
        _e(rank=58, entity_slug="jaxson-dart",
           entity_display_name="Jaxson Dart", program_slug="ole-miss",
           program_label="Ole Miss", era_label="Kiffin Era · 2022–2024",
           statline="9,276 career pass yds · 70 TD · 19 INT",
           summary_short=(
               "The Kiffin Era's quarterback — the USC transfer who ran "
               "the Ole Miss offense for three years and gave the program "
               "its most coherent stretch since Eli."
           )),
        _e(rank=59, entity_slug="evan-engram",
           entity_display_name="Evan Engram", program_slug="ole-miss",
           program_label="Ole Miss", era_label="2014–2016",
           statline="2016 Mackey · 162 catches · 2,320 rec yds",
           summary_short=(
               "The Mackey-winning tight end who anchored the "
               "Freeze-era Ole Miss offense and made the Giants take him "
               "in the first round."
           )),
        _e(rank=60, entity_slug="tony-pollard",
           entity_display_name="A.J. Brown", program_slug="ole-miss",
           program_label="Ole Miss", era_label="2016–2018",
           statline="189 catches · 2,984 rec yds · 19 TD",
           summary_short=(
               "The Ole Miss receiver who outproduced D.K. Metcalf in the "
               "same room — Titans second-rounder, Eagles All-Pro."
           )),
        _e(rank=61, entity_slug="dk-metcalf",
           entity_display_name="D.K. Metcalf", program_slug="ole-miss",
           program_label="Ole Miss", era_label="2017–2018",
           statline="67 catches · 1,228 rec yds · 14 TD across 21 games",
           summary_short=(
               "The injury-shortened Ole Miss career that produced the "
               "Combine performance that made him a Seahawk and a "
               "Steelers' building block."
           )),
        _e(rank=62, entity_slug="micah-parsons",
           entity_display_name="Micah Parsons", program_slug="penn-state",
           program_label="Penn State", era_label="Franklin Era · 2018–2019",
           statline="191 tackles · 6.5 sacks · 14 TFL · '21 12th-overall pick",
           summary_short=(
               "The Penn State linebacker whose 2019 sophomore year was "
               "the era's best pre-NFL film at the position — opted out "
               "of 2020 and went 12th overall regardless."
           )),
        _e(rank=63, entity_slug="travon-walker",
           entity_display_name="Travon Walker", program_slug="georgia",
           program_label="Georgia", era_label="Smart Era · 2019–2021",
           statline="9.5 career sacks · '21 NCG win · '22 first-overall pick",
           summary_short=(
               "The Georgia edge whose three-year rotation through the "
               "championship roster produced the first-overall NFL pick "
               "the tape didn't quite predict."
           )),
        _e(rank=64, entity_slug="kelee-ringo",
           entity_display_name="Kelee Ringo", program_slug="georgia",
           program_label="Georgia", era_label="Smart Era · 2021–2022",
           statline="2x national champ · 79-yd pick-6 in '21 NCG · 4 INT",
           summary_short=(
               "The Georgia corner whose 79-yard pick-six iced the 2021 "
               "national title game — and made him the closing image of "
               "the back-to-back run."
           )),
        _e(rank=65, entity_slug="zach-charbonnet",
           entity_display_name="Donovan Edwards", program_slug="michigan",
           program_label="Michigan", era_label="Harbaugh Era · 2022–2023",
           statline="186 career rec · 1,927 rush yds · '23 NCG TD pair",
           summary_short=(
               "The Michigan back whose two-touchdown explosion in the "
               "2023 national title game closed the Harbaugh-era loop."
           )),
        _e(rank=66, entity_slug="blake-corum",
           entity_display_name="Blake Corum", program_slug="michigan",
           program_label="Michigan", era_label="Harbaugh Era · 2021–2023",
           statline="4,019 career rush yds · 58 TD · '23 Doak Walker",
           summary_short=(
               "The Michigan back whose three-year run produced the Doak "
               "Walker, the school's all-time TD record, and the bracket "
               "the Wolverines went 15-0 through."
           )),
        _e(rank=67, entity_slug="hendon-hooker",
           entity_display_name="Hendon Hooker", program_slug="tennessee",
           program_label="Tennessee", era_label="Heupel Era · 2021–2022",
           statline="58 TD · 5 INT · '22 Tennessee 11-2 season",
           summary_short=(
               "The Heupel-era Tennessee quarterback whose 2022 season "
               "ran the Vols to 11-2 and made the program a top-five "
               "conversation for the first time in fifteen years."
           )),
        _e(rank=68, entity_slug="aaron-donald-namesake",
           entity_display_name="Vita Vea", program_slug="washington",
           program_label="Washington", era_label="Petersen Era · 2015–2017",
           statline="100 career tackles · 9.5 sacks at 347 pounds",
           summary_short=(
               "The Washington nose tackle whose interior tape made him a "
               "top-12 pick and anchored the Petersen-era Pac-12 "
               "Championship runs."
           )),
        _e(rank=69, entity_slug="patrick-surtain-ii",
           entity_display_name="Patrick Surtain II", program_slug="alabama",
           program_label="Alabama", era_label="Saban Era · 2018–2020",
           statline="116 career tackles · 4 INT · '21 9th-overall pick",
           summary_short=(
               "The Alabama corner whose 2020 season was a Jim Thorpe "
               "winner — the cleanest single-season corner tape of the "
               "Saban era."
           )),
        _e(rank=70, entity_slug="minkah-fitzpatrick",
           entity_display_name="Minkah Fitzpatrick", program_slug="alabama",
           program_label="Alabama", era_label="Saban Era · 2015–2017",
           statline="2017 Bednarik + Thorpe · 9 INT · '18 11th-overall pick",
           summary_short=(
               "The Alabama secondary's hybrid — three-year starter, "
               "Bednarik and Thorpe winner in '17, and the closing image "
               "of the Saban-era safety blueprint."
           )),
        _e(rank=71, entity_slug="reuben-foster",
           entity_display_name="Reuben Foster", program_slug="alabama",
           program_label="Alabama", era_label="Saban Era · 2015–2016",
           statline="2016 Butkus · 115 tackles · 13 TFL · '16 NCG starter",
           summary_short=(
               "The Butkus-winning Alabama linebacker whose 2016 season "
               "anchored the SEC West run — pre-NFL the cleanest "
               "off-ball film of the Saban-era roster."
           )),
        _e(rank=72, entity_slug="da-ron-payne",
           entity_display_name="Da'Ron Payne", program_slug="alabama",
           program_label="Alabama", era_label="Saban Era · 2015–2017",
           statline="3 sacks · 12 TFL · '17 NCG MVP · '18 13th-overall pick",
           summary_short=(
               "The Alabama nose tackle whose 2018 national title MVP "
               "performance against Georgia was the closing argument for "
               "the program's interior-line dominance."
           )),
        _e(rank=73, entity_slug="rashawn-slater",
           entity_display_name="Rashawn Slater", program_slug="northwestern",
           program_label="Northwestern", era_label="2017–2019",
           statline="3-year starter at LT · '21 13th-overall pick",
           summary_short=(
               "The Northwestern tackle whose tape-vs-the-Big-Ten "
               "consistency made the Chargers reach for him at 13 — "
               "the right call."
           )),
        _e(rank=74, entity_slug="evan-neal", entity_display_name="Evan Neal",
           program_slug="alabama", program_label="Alabama",
           era_label="Saban Era · 2019–2021",
           statline="3-position starter · '22 7th-overall pick",
           summary_short=(
               "The Alabama tackle whose three-position starting record "
               "in three years was the era's most flexible offensive-line "
               "résumé."
           )),
        _e(rank=75, entity_slug="rashee-rice",
           entity_display_name="Christian Wilkins", program_slug="clemson",
           program_label="Clemson", era_label="Swinney Era · 2015–2018",
           statline="40.5 career TFL · '18 NCG win · '19 13th-overall pick",
           summary_short=(
               "The four-year Clemson interior defender who anchored the "
               "back-to-back Playoff title runs and went 13th overall to "
               "the Dolphins."
           )),
        _e(rank=76, entity_slug="dexter-lawrence-namesake",
           entity_display_name="Dexter Lawrence", program_slug="clemson",
           program_label="Clemson", era_label="Swinney Era · 2016–2018",
           statline="10 career sacks · 2x national champ · '19 17th-overall pick",
           summary_short=(
               "The Clemson nose tackle whose three-year run anchored "
               "the Playoff defenses that beat Alabama twice and went "
               "17th overall to the Giants."
           )),
        _e(rank=77, entity_slug="hunter-renfrow",
           entity_display_name="Hunter Renfrow", program_slug="clemson",
           program_label="Clemson", era_label="Swinney Era · 2014–2018",
           statline="186 catches · 2,133 rec yds · 17 TD · '16 NCG game-winner",
           summary_short=(
               "The walk-on receiver who caught the 2016 national title "
               "game-winner from Watson with one second left — Clemson's "
               "closing image."
           )),
        _e(rank=78, entity_slug="deshaun-watson",
           entity_display_name="Deshaun Watson", program_slug="clemson",
           program_label="Clemson", era_label="Swinney Era · 2014–2016",
           statline="90 TD · 32 INT · 2x ACC POY · '16 NCG MVP · 1,934 career rush",
           summary_short=(
               "The Clemson quarterback whose 2016 national title win "
               "over Alabama and back-to-back Heisman runner-up votes "
               "anchored the program's first BCS/CFP-era title."
           )),
        _e(rank=79, entity_slug="mike-williams",
           entity_display_name="Mike Williams", program_slug="clemson",
           program_label="Clemson", era_label="Swinney Era · 2014–2016",
           statline="177 catches · 2,727 rec yds · 21 TD",
           summary_short=(
               "The Clemson receiver whose two-year run with Watson — "
               "interrupted by a neck injury in '15 — produced the seventh-"
               "overall pick in '17."
           )),
        _e(rank=80, entity_slug="malik-willis",
           entity_display_name="Will Anderson predecessor · Reuben Foster — see #71",
           program_slug="liberty", program_label="Liberty",
           era_label="Freeze Era · 2020–2021",
           statline="6,287 career pass + 1,822 rush · 70 total TD",
           summary_short=(
               "The Liberty quarterback (Malik Willis) whose dual-threat "
               "tape made the program a national conversation under "
               "Freeze and got him drafted in the third round."
           )),
        _e(rank=81, entity_slug="malik-willis-real",
           entity_display_name="Malik Willis", program_slug="liberty",
           program_label="Liberty", era_label="Freeze Era · 2020–2021",
           statline="6,287 career pass + 1,822 rush · 70 total TD",
           summary_short=(
               "The Group-of-Five quarterback whose two-year Liberty run "
               "produced the dual-threat tape that made him a top-100 "
               "draft pick."
           )),
        _e(rank=82, entity_slug="ej-perry",
           entity_display_name="Joey Bosa namesake", program_slug="ohio-state",
           program_label="Ohio State", era_label="2014–2015",
           statline="13 career sacks · '15 Big Ten DPOY · '16 3rd-overall pick",
           summary_short=(
               "The Ohio State edge whose two-year tape anchored the "
               "2014 Playoff defense and went third overall to the "
               "Chargers."
           )),
        _e(rank=83, entity_slug="von-bell",
           entity_display_name="Vonn Bell", program_slug="ohio-state",
           program_label="Ohio State", era_label="2013–2015",
           statline="9 career INT · '15 Big Ten title · '16 2nd-rd pick",
           summary_short=(
               "The Ohio State safety whose 2014 Playoff interception "
               "against Alabama in the Sugar Bowl semifinal was the era's "
               "first signature defensive moment."
           )),
        _e(rank=84, entity_slug="cameron-heyward-namesake",
           entity_display_name="Tyler Boyd", program_slug="pittsburgh",
           program_label="Pittsburgh", era_label="2013–2015",
           statline="254 catches · 3,361 rec yds · 21 TD",
           summary_short=(
               "The Pitt receiver whose three-year run produced the "
               "school all-time receptions record and a Bengals "
               "second-round draft slot."
           )),
        _e(rank=85, entity_slug="laviska-shenault",
           entity_display_name="Laviska Shenault Jr.", program_slug="colorado",
           program_label="Colorado", era_label="2017–2019",
           statline="149 catches · 1,943 rec yds · 16 TD",
           summary_short=(
               "The Colorado utility receiver whose 2018 season — six "
               "different position groups in one game — was the era's "
               "most novel offensive-skill film."
           )),
        _e(rank=86, entity_slug="jordan-davis",
           entity_display_name="Jordan Davis", program_slug="georgia",
           program_label="Georgia", era_label="Smart Era · 2018–2021",
           statline="2021 Outland + Bednarik + Nagurski · '22 13th-overall pick",
           summary_short=(
               "The 341-pound Georgia nose tackle whose 2021 awards sweep "
               "and 4.78 Combine 40 made him the era's most physically "
               "improbable first-rounder."
           )),
        _e(rank=87, entity_slug="brian-thomas-jr",
           entity_display_name="Brian Thomas Jr.", program_slug="lsu",
           program_label="LSU", era_label="Kelly Era · 2021–2023",
           statline="115 catches · 1,886 rec yds · 23 TD",
           summary_short=(
               "The LSU receiver whose 2023 partnership with Daniels "
               "produced the era's best deep-target tape and got the "
               "Jaguars a Pro Bowl rookie."
           )),
        _e(rank=88, entity_slug="malik-nabers",
           entity_display_name="Malik Nabers", program_slug="lsu",
           program_label="LSU", era_label="Kelly Era · 2021–2023",
           statline="189 catches · 3,003 rec yds · 23 TD",
           summary_short=(
               "The LSU number-one for Daniels in 2023 — Biletnikoff "
               "finalist, sixth overall to the Giants, the era's "
               "second-best LSU receiver season after Chase."
           )),
        _e(rank=89, entity_slug="terrion-arnold",
           entity_display_name="Terrion Arnold", program_slug="alabama",
           program_label="Alabama", era_label="Saban Era · 2022–2023",
           statline="5 career INT · '24 24th-overall pick · 2x All-SEC",
           summary_short=(
               "The Alabama corner whose two-year starting run produced "
               "the cleanest cover tape of the Saban era's final two "
               "seasons."
           )),
        _e(rank=90, entity_slug="dallas-turner",
           entity_display_name="Dallas Turner", program_slug="alabama",
           program_label="Alabama", era_label="Saban Era · 2021–2023",
           statline="22.5 career sacks · '24 17th-overall pick",
           summary_short=(
               "The Alabama edge whose three-year sack production made "
               "him the SEC DPOY in '23 and the Vikings' first-round "
               "investment in '24."
           )),
        _e(rank=91, entity_slug="laiatu-latu",
           entity_display_name="Laiatu Latu", program_slug="ucla",
           program_label="UCLA", era_label="Foster Era · 2022–2023",
           statline="23.5 career sacks · '24 15th-overall pick",
           summary_short=(
               "The Washington medical-retiree turned UCLA edge — '23 "
               "Lombardi winner and the only player to come back from a "
               "career-ending diagnosis to be a top-15 pick in the era."
           )),
        _e(rank=92, entity_slug="will-levis",
           entity_display_name="Will Levis", program_slug="kentucky",
           program_label="Kentucky", era_label="Stoops Era · 2021–2022",
           statline="43 career TD · 23 INT · '23 second-round pick",
           summary_short=(
               "The Kentucky two-year starter whose dual-threat tape made "
               "him a draft-night fall and a Titans starter."
           )),
        _e(rank=93, entity_slug="bryce-parr",
           entity_display_name="Anthony Richardson", program_slug="florida",
           program_label="Florida", era_label="Napier Era · 2022",
           statline="21 TD · 9 INT · 4.4 forty at 244 pounds",
           summary_short=(
               "The Florida one-year starter whose Combine performance "
               "made him the fourth-overall pick on the rawest tape of "
               "any quarterback ever taken in the top-five."
           )),
        _e(rank=94, entity_slug="kyle-pitts",
           entity_display_name="Kyle Pitts", program_slug="florida",
           program_label="Florida", era_label="Mullen Era · 2018–2020",
           statline="100 catches · 1,492 rec yds · 18 TD as a TE",
           summary_short=(
               "The Florida tight end whose 2020 season — Mackey winner, "
               "Heisman finalist as a TE — made him the highest TE pick "
               "since 1973 (4th overall to Atlanta)."
           )),
        _e(rank=95, entity_slug="kadarius-toney",
           entity_display_name="Treylon Burks", program_slug="arkansas",
           program_label="Arkansas", era_label="Pittman Era · 2019–2021",
           statline="146 catches · 2,399 rec yds · 18 TD",
           summary_short=(
               "The Arkansas receiver whose three-year SEC tape made him "
               "the Titans' replacement plan for A.J. Brown and a "
               "first-round pick."
           )),
        _e(rank=96, entity_slug="jared-goff-namesake",
           entity_display_name="Jared Goff", program_slug="california",
           program_label="California", era_label="Dykes Era · 2014–2015",
           statline="71 career TD · 23 INT · '16 first-overall pick",
           summary_short=(
               "The Cal quarterback whose 2015 Pac-12 production made him "
               "the first-overall pick in 2016 and the closing image of "
               "the late-Dykes Cal program."
           )),
        _e(rank=97, entity_slug="dak-cousins-namesake",
           entity_display_name="Marcus Mariota", program_slug="oregon",
           program_label="Oregon", era_label="Helfrich Era · 2014",
           statline="2014 Heisman · 42 TD · 4 INT · '15 NCG appearance",
           summary_short=(
               "The Oregon quarterback whose 2014 Heisman season "
               "delivered the first inaugural-Playoff title-game "
               "appearance and made the spread-pass identity portable."
           )),
        _e(rank=98, entity_slug="t-harris",
           entity_display_name="Najee Harris", program_slug="alabama",
           program_label="Alabama", era_label="Saban Era · 2017–2020",
           statline="3,843 career rush yds · 46 TD · '21 24th-overall pick",
           summary_short=(
               "The four-year Alabama back whose senior season anchored "
               "the 2020 13-0 title run and went late-first to the "
               "Steelers."
           )),
        _e(rank=99, entity_slug="leighton-vander-esch-namesake",
           entity_display_name="Tank Bigsby", program_slug="auburn",
           program_label="Auburn", era_label="2020–2022",
           statline="2,903 career rush yds · 25 TD · 2x All-SEC",
           summary_short=(
               "The Auburn back whose three-year run carried a program "
               "across two coaching changes and made him a top-100 "
               "draft pick."
           )),
        _e(rank=100, entity_slug="dont-a-hightower-namesake",
           entity_display_name="Christian McCaffrey", program_slug="stanford",
           program_label="Stanford", era_label="Shaw Era · 2014–2016",
           statline="3,922 career rush + 1,206 rec yds · 31 TD · '15 Heisman runner-up",
           summary_short=(
               "The Stanford all-purpose back whose 2015 single-season "
               "all-purpose yards record (3,864) closed the BCS-to-CFP "
               "transition and made him a top-10 NFL pick."
           )),
    ]
