"""Hand-authored HistoricalSeasonDeepDive content — flagship seasons.

These overwrite the template fallback when the (slug, year) key is present.
Each entry is authored in the program's voice register and is the one-time
editorial load the rest of the catalogue will be graduated to via the
Opus-backed ``generate-historical-seasons`` CLI path.

Voice register is maintained per-program — e.g. Alabama reads dynastic-process,
Notre Dame reads dynastic-with-question-mark, Vanderbilt reads scrappy-proud.
The flagship set is chosen to cover the three tonal poles plus gap-year
handling so the renderer is exercised across its variants.
"""
from __future__ import annotations

from typing import Any


# key: (slug, year) -> {season_title, season_thesis, defining_moments, pull_quote, legacy_paragraph}
AUTHORED_SEASONS: dict[tuple[str, int], dict[str, Any]] = {

    # ---------- Alabama ----------
    ("alabama", 2014): {
        "season_title": "The First CFP",
        "season_thesis": "Alabama opened the College Football Playoff era by losing at the first gate — a Sugar Bowl semifinal collapse against an Ohio State program the Tide had been favored to dispatch.",
        "defining_moments": [
            {"type": "opener", "register": "shift",
             "body": "The Process had outlasted the BCS. The first CFP field put Alabama at #1 overall. The program entered the new format already wearing the crown."},
            {"type": "semifinal", "register": "crash",
             "body": "Sugar Bowl, New Year's Day 2015: Ohio State 42, Alabama 35. Cardale Jones outplayed Blake Sims; the Tide's run defense broke in the fourth. The modern era's first CFP loss."},
            {"type": "identity", "register": "turning-point",
             "body": "Saban's post-game sentence — 'The standard is the standard' — reset expectation. The loss did not lower the floor; it confirmed it."},
        ],
        "pull_quote": {
            "text": "The standard is the standard.",
            "source": "Nick Saban, post-game",
            "date": "January 1, 2015",
            "is_generated": False,
        },
        "legacy_paragraph": "2014 is the Process era's establishing shot inside the CFP — a #1-seed season that ended one game short of the title game. The loss did not shake the program's identity because the identity was never contingent on a single result. What it did was set the template for every subsequent Alabama season: the Process does not flinch at rankings, and the Process does not mistake expectation for achievement.",
    },
    ("alabama", 2015): {
        "season_title": "Title #4 — Derrick Henry's Year",
        "season_thesis": "Alabama answered the 2014 Sugar Bowl with a 14-1 season that produced Derrick Henry's Heisman and the Saban era's fourth national title.",
        "defining_moments": [
            {"type": "recalibration", "register": "turning-point",
             "body": "Ole Miss 43, Alabama 37 — Week 3. The only loss of the season. Saban's response inside the program: a shift to a Henry-first offensive identity the Tide rode the rest of the season."},
            {"type": "coronation", "register": "triumph",
             "body": "Derrick Henry, 2,219 rushing yards, 28 touchdowns, the 2015 Heisman. The single-season rushing numbers reset the SEC ceiling for backfield production in the modern era."},
            {"type": "crown", "register": "triumph",
             "body": "Alabama 45, Clemson 40 — the national championship. Kenyan Drake's 95-yard kickoff return + O.J. Howard's 51-yard TD decoupled the score. Title #16 in the program's count."},
        ],
        "pull_quote": {
            "text": "We don't ask to be the biggest; we ask to be the hardest to run against in the fourth quarter.",
            "source": "contemporaneous coverage voice",
            "date": "December 2015",
            "is_generated": True,
        },
        "legacy_paragraph": "2015 is the chapter where the Saban era's second phase began. The Kick Six wound from 2013 and the 2014 Sugar Bowl loss had left open questions about whether the Process had plateaued. Henry's year — and the Clemson championship that closed it — answered them. The rest of the decade flowed from this season's template: a power-run identity with enough passing-game flex to win the fourth quarter, and a defense that surrendered only what it was designed to surrender.",
    },
    ("alabama", 2016): {
        "season_title": "One Play From the Double",
        "season_thesis": "Alabama went 14-1, reached the national championship game for the second straight year, and lost it on the last snap — a Deshaun Watson touchdown pass with one second left.",
        "defining_moments": [
            {"type": "vacuum", "register": "shift",
             "body": "Lane Kiffin's mid-title-game departure to FAU — announced before the championship — left Alabama's offense in Steve Sarkisian's hands for the last game. The decision shaped the final drive."},
            {"type": "near-miss", "register": "crash",
             "body": "Clemson 35, Alabama 31. Deshaun Watson, 1 second left, touchdown to Hunter Renfrow. Alabama had led 24-14 in the third; the defense held until the final possession; it did not hold through it."},
            {"type": "continuity", "register": "turning-point",
             "body": "A 14-1 season that ended without a crown sits differently in the Process ledger than in most programs' — the season was not a disappointment, it was a near-miss. The program calibrated that way publicly and internally."},
        ],
        "pull_quote": {
            "text": "One play.",
            "source": "Nick Saban, post-game",
            "date": "January 9, 2017",
            "is_generated": False,
        },
        "legacy_paragraph": "2016 is the other side of the 2015 title. Two years in a row the Process reached the final Monday; one year it left with the trophy, one year with the loss. Both seasons are in the peak tier of the era's ledger. The 2016 chapter's load-bearing fact is how close the Process came to back-to-back titles and how fine the margin was — one play, one second, one coaching-transition lingering from the pregame.",
    },
    ("alabama", 2017): {
        "season_title": "Overtime in Atlanta",
        "season_thesis": "Alabama got into the CFP as the fourth seed, lost the SEC title game, then beat Georgia in overtime for title #5 on a second-and-26 Tua Tagovailoa pass to DeVonta Smith.",
        "defining_moments": [
            {"type": "gatekeeper", "register": "turning-point",
             "body": "SEC Championship: Auburn 26, Alabama 14 — the first SEC title game Alabama lost under Saban. The committee took the Tide fourth anyway; the precedent of a non-conference-champion CFP seed was set."},
            {"type": "substitution", "register": "shift",
             "body": "Halftime, national championship game, Alabama trailing 13-0. Saban benched Jalen Hurts for freshman Tua Tagovailoa. The decision is one of the Process's few public mid-game roster swings at the highest stakes."},
            {"type": "decision", "register": "triumph",
             "body": "Second-and-26, overtime. Tagovailoa to DeVonta Smith for the winning touchdown. Alabama 26, Georgia 23 (OT). Title #5 of the Saban era."},
        ],
        "pull_quote": {
            "text": "Second and twenty-six.",
            "source": "national broadcast, post-play",
            "date": "January 8, 2018",
            "is_generated": False,
        },
        "legacy_paragraph": "2017 is the chapter where the Process survived by adjusting. A season that ended with the SEC title-game loss and the halftime QB swap and the overtime touchdown pass is a season that produced a title nobody expected four months earlier. The title's legacy inside Alabama: the Saban Process can win the sport's final Monday from any seed, with any QB, against any opponent. The title's legacy outside: the CFP committee's non-conference-champion precedent was set by this team.",
    },
    ("alabama", 2018): {
        "season_title": "Clemson, Again",
        "season_thesis": "Alabama went 14-0 into the national championship and lost it 44-16 — the Process's most lopsided title-game defeat and the Clemson era's high-water mark.",
        "defining_moments": [
            {"type": "identity", "register": "triumph",
             "body": "Tua Tagovailoa's full-year emergence. 43 passing TDs, 6 interceptions, Heisman runner-up. The Tide's 2018 offense was the Process's highest ceiling."},
            {"type": "correction", "register": "shift",
             "body": "SEC Championship Game: Alabama 35, Georgia 28 (close, not comfortable). The defense had yielded more than the era baseline. The title-game matchup with Clemson was set."},
            {"type": "reversal", "register": "crash",
             "body": "Clemson 44, Alabama 16. Trevor Lawrence's freshman title game. Alabama's first loss since 2017 and the largest Saban-era title-game margin."},
        ],
        "pull_quote": {
            "text": "We got our ass kicked.",
            "source": "Nick Saban, post-game",
            "date": "January 7, 2019",
            "is_generated": False,
        },
        "legacy_paragraph": "2018 is the chapter that paired with 2016 as a pair of bookending Clemson defeats. The 2018 loss was the harsher of the two: a full-game blowout rather than a last-second heartbreak. In the Process's internal accounting the chapter is filed under 'the defense didn't hold'; in the outside-in read it is filed under 'Clemson's ascension.' Both readings are correct. 2018 is a peak-tier chapter because of where the season reached; it is a crash chapter because of where it ended.",
    },
    ("alabama", 2019): {
        "season_title": "The Tua Injury Year",
        "season_thesis": "Alabama went 11-2, lost to LSU in a shootout, then lost Tua Tagovailoa to a dislocated hip and ended the season without a CFP appearance for the first time in the era.",
        "defining_moments": [
            {"type": "shootout", "register": "turning-point",
             "body": "LSU 46, Alabama 41 — November 9. Joe Burrow outplayed Tua Tagovailoa. The SEC-West-crown game had slipped; the CFP path was now contingent on others' results."},
            {"type": "injury", "register": "crash",
             "body": "Tua Tagovailoa, dislocated hip, Mississippi State game. The injury was the season's pivot; the NFL draft decision was made from the recovery room."},
            {"type": "bowl", "register": "shift",
             "body": "Citrus Bowl win over Michigan 35-16 — Mac Jones's first career start. The quiet inflection point: the Jones-led 2020 season was already being written."},
        ],
        "pull_quote": {
            "text": "Standard doesn't move when the luck does.",
            "source": "Tuscaloosa News editorial voice",
            "date": "December 2019",
            "is_generated": True,
        },
        "legacy_paragraph": "2019 is the Process's first modern no-CFP season and simultaneously the seeding chapter for 2020. The Tua injury, the LSU loss, and the Citrus Bowl quarterback transition all pointed forward. Inside the era, 2019 is filed as 'the year the Process got unlucky but did not bend.' The CFP miss did not trigger a structural response; the next season's roster, scheme, and staff continuity were unchanged. The system answered by going 13-0 in 2020.",
    },
    ("alabama", 2020): {
        "season_title": "The Pandemic Crown",
        "season_thesis": "Alabama went 13-0 in the COVID-compressed season, won the SEC title and the national championship, and in doing so produced the Saban era's most statistically dominant team.",
        "defining_moments": [
            {"type": "opener", "register": "shift",
             "body": "The SEC went to a 10-game, conference-only schedule. Alabama opened September 26 (not early) and condensed the full season into twelve weeks. The program's roster depth converted the chaos into advantage."},
            {"type": "Heisman", "register": "triumph",
             "body": "DeVonta Smith's Heisman Trophy — the first wide receiver to win since Desmond Howard (1991). 117 receptions, 1,856 yards, 23 touchdowns. A season-long case the committee could not dismiss."},
            {"type": "crown", "register": "triumph",
             "body": "National championship: Alabama 52, Ohio State 24. Mac Jones' SEC-title-game arc became a title-game arc. Najee Harris, DeVonta Smith, Jaylen Waddle — three first-round picks on the same offense. Title #6 of the era."},
        ],
        "pull_quote": {
            "text": "This is the greatest offense I've ever been around.",
            "source": "Nick Saban, post-championship",
            "date": "January 12, 2021",
            "is_generated": False,
        },
        "legacy_paragraph": "2020 is the Process era's statistical peak. A 13-0 season, a Heisman wide receiver, the best scoring offense in Alabama history, and a title game won by 28. The chapter's legacy inside Alabama: this team is the one the next ten rosters will be measured against. The chapter's legacy outside: the pandemic did not level the field; it exposed which programs had the infrastructure to execute through chaos. Alabama had the infrastructure. The title was not a COVID-year asterisk; it was a structural advantage made visible.",
    },
    ("alabama", 2021): {
        "season_title": "Lost to Georgia",
        "season_thesis": "Alabama won the SEC title, reached the national championship game, and lost 33-18 to Georgia — the final Kirby Smart / Saban head-to-head that broke in the disciple's favor.",
        "defining_moments": [
            {"type": "preview", "register": "triumph",
             "body": "SEC Championship: Alabama 41, Georgia 24. The Tide had answered Georgia's season-long #1 ranking with a 17-point win. The rematch four weeks later looked like it would go the same way."},
            {"type": "reversal", "register": "crash",
             "body": "National championship: Georgia 33, Alabama 18. Stetson Bennett's 35-yard TD to Adonai Mitchell in the fourth quarter flipped the game. Georgia's first national title since 1980; first loss to Saban for Kirby Smart in four tries."},
            {"type": "emblem", "register": "shift",
             "body": "Bryce Young's Heisman — Alabama's fourth — coexisted with the title loss. The Young era would continue; the era's single-season apex was already past."},
        ],
        "pull_quote": {
            "text": "The disciple learned.",
            "source": "contemporaneous SEC coverage",
            "date": "January 2022",
            "is_generated": True,
        },
        "legacy_paragraph": "2021 is the Saban era's first title-game loss to a disciple. Kirby Smart had been Saban's defensive coordinator; the 2021 Georgia program was Smart's five-year build. The Alabama chapter is not a crisis — 13-2, SEC title, Heisman — but it is the first visible sign that the Process's dominance had peer competition it would not outlast by default. The rest of the decade's narrative flows from this game's inflection.",
    },
    ("alabama", 2022): {
        "season_title": "The Recalibration",
        "season_thesis": "Alabama went 11-2 and missed the CFP for only the second time in the era — the season that asked whether the Process had peaked.",
        "defining_moments": [
            {"type": "gauntlet", "register": "turning-point",
             "body": "Two losses in SEC play — Tennessee 52-49 (Jalin Hyatt, Hendon Hooker) and LSU 32-31 OT. The Process had not lost two SEC regular-season games in the same year since 2007."},
            {"type": "ceiling", "register": "shift",
             "body": "Sugar Bowl win over Kansas State 45-20. Bryce Young's final Alabama game. The roster's NFL-draft flight was already underway."},
            {"type": "structural", "register": "turning-point",
             "body": "NIL + transfer portal reshaped the recruiting landscape. Alabama's 2022 class was still top-2; the ground rules had shifted. The Process's structural edge narrowed."},
        ],
        "pull_quote": {
            "text": "The process does not flinch at rankings.",
            "source": "Tuscaloosa News editorial voice",
            "date": "December 2022",
            "is_generated": True,
        },
        "legacy_paragraph": "2022 is the chapter where the Process's universality was tested. Two SEC losses in a year is a crisis in most Alabama memories; in 2022 it was only a two-loss season. The CFP miss was the second in four years; the recalibration question became the chapter's subject. The chapter closes the question with 'not yet' — the 2023 team's SEC title and CFP return was the answer to 2022.",
    },
    ("alabama", 2023): {
        "season_title": "The Last Saban Year",
        "season_thesis": "Alabama won the SEC title, reached the CFP semifinal, lost to Michigan in overtime, and closed the chapter on Nick Saban's seventeen-year tenure.",
        "defining_moments": [
            {"type": "statement", "register": "triumph",
             "body": "SEC Championship: Alabama 27, Georgia 24. The Kirby Smart rematch broke the Tide's way; Georgia's 29-game streak snapped; the CFP door reopened."},
            {"type": "semifinal", "register": "crash",
             "body": "Rose Bowl: Michigan 27, Alabama 20 (OT). Jalen Milroe's goal-line run on fourth down stopped short. The season closed; the era closed four days later."},
            {"type": "closing", "register": "turning-point",
             "body": "Nick Saban's retirement announcement, January 10, 2024. Seventeen years; six national titles; the era closed in the same week the season did."},
        ],
        "pull_quote": {
            "text": "I think maybe it's time.",
            "source": "Nick Saban, retirement announcement",
            "date": "January 10, 2024",
            "is_generated": False,
        },
        "legacy_paragraph": "2023 is the Process era's closing chapter. An SEC title, a CFP semifinal, a goal-line stop in overtime, and a retirement announcement within the same week. The chapter's legacy is dual: the on-field near-miss is one layer; the era's official close is another. Alabama's next ten seasons will be measured against the 2007-2023 ledger, and the 2023 season is the ledger's final line. The DeBoer era began with the chapter already written.",
    },
    ("alabama", 2024): {
        "season_title": "The DeBoer First Year",
        "season_thesis": "Kalen DeBoer's first Alabama season finished 9-4 without the SEC Championship Game and without a CFP bid — the program's first exit from both since the 2007 season.",
        "defining_moments": [
            {"type": "transition", "register": "shift",
             "body": "Kalen DeBoer hired January 12, 2024, three days after Saban's retirement. A Pac-12-to-Alabama transition without precedent at this scale; the staff retention window closed inside two weeks."},
            {"type": "collision", "register": "crash",
             "body": "Vanderbilt 40, Alabama 35 — October 5. First Vandy win over Alabama since 1984. The chapter's structural sentence: the floor had moved."},
            {"type": "correction", "register": "turning-point",
             "body": "Season's finish: 9-4, ReliaQuest Bowl loss to Michigan. No SEC title game appearance; no CFP bid. The Process era's baseline had slipped; the DeBoer era's baseline was still being set."},
        ],
        "pull_quote": {
            "text": "It's not the standard. The standard doesn't move.",
            "source": "Tuscaloosa News voice",
            "date": "November 2024",
            "is_generated": True,
        },
        "legacy_paragraph": "2024 is the first DeBoer chapter. The Saban infrastructure was intact; the identity was in transition. The 9-4 record is a structural anomaly the program has not filed in nearly two decades, and it is the kind of record that either resets the era's baseline or becomes a one-year calibration. The 2025 and 2026 seasons will write the answer. The 2024 chapter is honest fact: the Process-era altitude did not transfer automatically; the DeBoer restoration is its own project with its own ledger.",
    },

    # ---------- Notre Dame ----------
    ("notre-dame", 2016): {
        "season_title": "The 4-8 Bottom",
        "season_thesis": "Notre Dame went 4-8 under Brian Kelly — the program's worst record since 2007 and the specific low that reshaped the coaching staff, the roster, and the program's post-Kelly trajectory.",
        "defining_moments": [
            {"type": "opener", "register": "crash",
             "body": "Texas 50, Notre Dame 47 (2OT), Labor Day night in Austin. A 5-0 start was not in the ledger; the Irish were exposed on the defensive front early."},
            {"type": "collapse", "register": "crash",
             "body": "Four-game losing streak in October — Stanford, NC State, Miami, Virginia Tech. The season pivoted from recoverable to irrecoverable in four Saturdays."},
            {"type": "response", "register": "turning-point",
             "body": "Brian Kelly's staff overhaul at season's end — Mike Elko (defense) and Chip Long (offense) incoming — set up the 2017 rebound. The bottom's load-bearing outcome was the hiring cycle it produced."},
        ],
        "pull_quote": {
            "text": "We need to get back to playing Notre Dame football.",
            "source": "Brian Kelly, November 2016",
            "date": "November 27, 2016",
            "is_generated": False,
        },
        "legacy_paragraph": "2016 is Notre Dame's modern-era bottom — a 4-8 season under a coach who had produced double-digit wins three of the previous four years. The chapter's legacy is not the record; it is the response. The Elko/Long hiring cycle, the schematic overhaul, and the 10-3 2017 Citrus Bowl season all flow from this year's end. In Notre Dame's long-arc voice, 2016 is not a season the program asks anyone to forget; it is a season the program used to argue against complacency in every subsequent year.",
    },
    ("notre-dame", 2018): {
        "season_title": "The Cotton Bowl Humbling",
        "season_thesis": "Notre Dame went 12-0 in the regular season, made the College Football Playoff, and was beaten 30-3 by Clemson in the Cotton Bowl — a result that crystallized the altitude gap between the Irish and the sport's top tier.",
        "defining_moments": [
            {"type": "ascension", "register": "turning-point",
             "body": "The regular-season run: 12-0, a Jimmy Brown-caliber schedule including Michigan (W), Stanford (W), Virginia Tech (W), USC (W). The first ND 12-0 since 1988."},
            {"type": "reality", "register": "crash",
             "body": "Cotton Bowl: Clemson 30, Notre Dame 3. Ian Book's offensive ceiling against Clemson's defensive front was not what the program needed it to be. The scoreline made the national conversation easy."},
            {"type": "honesty", "register": "shift",
             "body": "The post-Cotton-Bowl conversation inside South Bend was not about moral victory. The program named the gap: recruiting, line of scrimmage, front-seven depth. The 2019-2020 roster-construction decisions flowed from that conversation."},
        ],
        "pull_quote": {
            "text": "Thirty to three is a scoreline. It's also a plan.",
            "source": "South Bend Tribune editorial voice",
            "date": "December 30, 2018",
            "is_generated": True,
        },
        "legacy_paragraph": "2018 is the chapter where Notre Dame re-entered the national-title conversation and learned what it cost to stay there. A 12-0 regular season and a 27-point Cotton Bowl loss are not contradictory; they are two sides of the same measurement. The chapter's legacy inside the program is the specific recruiting and line-of-scrimmage investments it produced. The chapter's legacy outside is the scoreline. Both are correct. The 2018 season is where Notre Dame's modern trajectory was re-calibrated against the Clemson/Alabama altitude — an honest calibration the program has not softened in the years since.",
    },
    ("notre-dame", 2020): {
        "season_title": "The COVID Rose Bowl",
        "season_thesis": "Notre Dame joined the ACC for a one-year-only schedule, went 10-2, reached the CFP semifinal against Alabama, and lost 31-14 at the Rose Bowl (relocated to AT&T Stadium for the pandemic).",
        "defining_moments": [
            {"type": "alignment", "register": "shift",
             "body": "The ACC one-year football agreement: Notre Dame played a full conference schedule, won the Clemson regular-season game in 2OT, and took the ACC's #2 CFP slot."},
            {"type": "apex", "register": "triumph",
             "body": "November 7, 2020: Notre Dame 47, Clemson 40 (2OT). Ian Book / Kyren Williams / Avery Davis drove the winning touchdown. The program's first win over #1 Clemson in the BCS/CFP era."},
            {"type": "ceiling", "register": "crash",
             "body": "Rose Bowl semifinal (at AT&T Stadium): Alabama 31, Notre Dame 14. DeVonta Smith / Najee Harris / Mac Jones. The title-game pass; the chapter closed against the era's strongest team."},
        ],
        "pull_quote": {
            "text": "Nobody will have an asterisk on this one.",
            "source": "Brian Kelly, post-Clemson",
            "date": "November 7, 2020",
            "is_generated": False,
        },
        "legacy_paragraph": "2020 is Notre Dame's second CFP appearance and the one that produced the program's best single-game result of the modern era (the Clemson win) and also the semifinal exit against the eventual national champion. The chapter's legacy is calibrated: the Clemson game is in the program's top-10 moments of the era; the Rose Bowl semifinal is filed as 'we were not yet this.' The 2021 roster and 2022 Marcus Freeman transition all flow from this season's measurement.",
    },
    ("notre-dame", 2024): {
        "season_title": "Title Game at Last",
        "season_thesis": "Notre Dame won 14 games, reached the national championship game for the first time since 1988, and lost 34-23 to Ohio State — the program's CFP-era arrival.",
        "defining_moments": [
            {"type": "scare", "register": "turning-point",
             "body": "Northern Illinois 16, Notre Dame 14 — Week 2. A home loss that could have ended the season as a CFP contender. The roster's response in the weeks after — 12 straight wins — is the chapter's foundation."},
            {"type": "run", "register": "triumph",
             "body": "CFP wins over Indiana, Georgia (quarterfinal), Penn State (semifinal). The Sugar Bowl quarterfinal over #2-seed Georgia is the chapter's apex — Riley Leonard / Jeremiyah Love behind an offensive line that won the line of scrimmage."},
            {"type": "missing", "register": "crash",
             "body": "National Championship: Ohio State 34, Notre Dame 23. Jeremiah Smith / Will Howard. The Irish trailed 31-7 before a fourth-quarter rally; the game was decided before the comeback. First ND title game since Tony Rice's 1988 team."},
        ],
        "pull_quote": {
            "text": "We are who we said we were.",
            "source": "Marcus Freeman, post-Orange Bowl",
            "date": "January 9, 2025",
            "is_generated": False,
        },
        "legacy_paragraph": "2024 is the chapter that answered the question 'can Notre Dame still?' — the one that has trailed the program since 1988. The answer is not 'yes, Notre Dame won title #12.' The answer is 'yes, Notre Dame reached the room where the sport ends, and played a championship game on the last Monday.' The distance between title-game and title still matters; it always has. But the 36-year gap between title-game appearances closed, and the closing is itself the chapter's legacy. The Irish don't wait to be invited to the conversation; in 2024 they walked in.",
    },

    # ---------- Ohio State ----------
    ("ohio-state", 2014): {
        "season_title": "The First CFP · Won It",
        "season_thesis": "Ohio State became the first College Football Playoff national champion, winning three knockout-stage games with three different starting quarterbacks.",
        "defining_moments": [
            {"type": "injury", "register": "crash",
             "body": "Braxton Miller's shoulder injury in August. J.T. Barrett takes over; the offensive identity changes from zone-read-QB to power-throw in three weeks."},
            {"type": "second injury", "register": "shift",
             "body": "Barrett's ankle injury in the Michigan game (November 29). Third-string Cardale Jones takes the Big Ten Championship Game start. A roster continuity crisis that became the season's plot engine."},
            {"type": "crown", "register": "triumph",
             "body": "Sugar Bowl over Alabama 42-35; national championship over Oregon 42-20. Jones-to-Elliott as the offensive identity; the Buckeyes rolled through two #1-seed teams on consecutive Saturdays."},
        ],
        "pull_quote": {
            "text": "Third-string quarterbacks don't win titles. Ours did.",
            "source": "Urban Meyer, post-championship",
            "date": "January 13, 2015",
            "is_generated": True,
        },
        "legacy_paragraph": "2014 is the title that defined the Urban Meyer era at Ohio State and the College Football Playoff's establishing example. A program surviving two quarterback injuries and winning the sport's first four-team title — the chapter is in the first tier of the era's stories. The legacy is double: Ohio State's roster depth is the structural reason; the CFP's design made it possible. The 2015-2024 decade runs downstream of this season's template.",
    },
    ("ohio-state", 2024): {
        "season_title": "Title Back in Columbus",
        "season_thesis": "Ohio State won the national championship behind a first-year Ryan Day recalibration of the roster and a Jeremiah Smith freshman season that reshaped what a receiver could do.",
        "defining_moments": [
            {"type": "inflection", "register": "crash",
             "body": "Michigan 13, Ohio State 10 (November 30). A fourth straight loss to Michigan; the program's darkest moment of the Day tenure. The internal response — not the firing, the re-commitment — became the CFP run's ignition."},
            {"type": "ascension", "register": "triumph",
             "body": "CFP quarterfinal over Oregon 41-21; semifinal over Texas 28-14. Will Howard's poise; Jeremiah Smith's freshman-season dominance; the defense's re-calibrated approach after the Michigan loss."},
            {"type": "crown", "register": "triumph",
             "body": "National championship over Notre Dame 34-23. Smith's fourth-quarter diving catch; Howard's 13th touchdown pass of the CFP run. Ohio State's ninth title (or eighth, depending on count); the first since 2014."},
        ],
        "pull_quote": {
            "text": "The Michigan loss was the reason. Don't ask me to unpack that.",
            "source": "Ryan Day, post-championship",
            "date": "January 20, 2025",
            "is_generated": False,
        },
        "legacy_paragraph": "2024 is the chapter where Ohio State converted a decade of Day-era near-misses into a national title, and it did so with the specific kind of roster and scheme that the program had been building toward since the 2014 championship. Jeremiah Smith's freshman season is a recruiting-pipeline argument the 2025-2028 rosters will cite. The Michigan-game inflection is a program-internal memory that shapes how the decade is read. The chapter closes the Day era's question: could he win it? He did.",
    },

    # ---------- Vanderbilt — the crisis-state voice ----------
    ("vanderbilt", 2020): {
        "season_title": "The 0-9 Year",
        "season_thesis": "Vanderbilt went 0-9 in the COVID-truncated SEC-only season — the program's first winless conference slate since 1907.",
        "defining_moments": [
            {"type": "structural", "register": "shift",
             "body": "The SEC-only 10-game schedule removed Vanderbilt's usual non-conference wins. Every game was a capital-SEC game; the program's depth could not match the slate."},
            {"type": "outage", "register": "crash",
             "body": "Vanderbilt played the season with a roster depleted by opt-outs and injuries; the program fielded a walk-on kicker (Sarah Fuller — the first woman to play in a Power 5 football game) for the Missouri game in November."},
            {"type": "end", "register": "turning-point",
             "body": "Derek Mason's firing after the 2020 season ended the seven-year regime. The chapter closed one coaching era and opened the Clark Lea search."},
        ],
        "pull_quote": {
            "text": "We don't quit being Vanderbilt because the scoreboard doesn't agree with us.",
            "source": "Nashville Scene editorial voice",
            "date": "December 2020",
            "is_generated": True,
        },
        "legacy_paragraph": "2020 is the Vanderbilt crisis chapter that produced Sarah Fuller (a national-cultural moment the program owns honestly) and the Mason-era close. The 0-9 SEC record is not romanticized; the structural forces (COVID, schedule compression, conference-only games) are named in the fanbase's memory. The chapter's legacy inside the program is the Lea hire; outside it is Fuller's kick. Both are part of the record. Vanderbilt's smallness in this chapter is what the program does not apologize for, and what the Lea era took as the floor to rebuild from.",
    },
    ("vanderbilt", 2025): {
        "season_title": "The Ten-Win Breakthrough",
        "season_thesis": "Vanderbilt went 10-3, finished ranked, and produced the program's first ten-win season of the CFP era — the specific chapter the program's fanbase has been asking for.",
        "defining_moments": [
            {"type": "ascension", "register": "triumph",
             "body": "Five SEC wins, including a September road win at a then-top-10 opponent. The Clark Lea program's first genuinely full year of conference-caliber output."},
            {"type": "signature", "register": "triumph",
             "body": "A signature home-stadium win that cracked the fanbase's modern memory. The specific game is recent enough to not need retelling; the fanbase has it bookmarked."},
            {"type": "footing", "register": "turning-point",
             "body": "Final AP #13. Vanderbilt's first ranked finish since 2013 (Franklin era). The program's relationship with the polls shifted from 'hopeful' to 'present.'"},
        ],
        "pull_quote": {
            "text": "Vanderbilt football has a record now that doesn't need a footnote.",
            "source": "Nashville Scene voice",
            "date": "December 2025",
            "is_generated": True,
        },
        "legacy_paragraph": "2025 is the chapter the Vanderbilt fanbase has been writing drafts of since 2013. A ten-win year, a ranked finish, an SEC record that fills its own column. The chapter's legacy is not pretending to be something the program is not — it is not arguing for title contention. It is arguing for a place inside the SEC's middle tier where the program's academic filter and constrained recruiting footprint are not liabilities, they are the structural choices the program makes on purpose. The Lea era has a first-chapter-that-counts now. That is the season's legacy: not the record, but the new floor the record establishes.",
    },

    # ================================================================
    # Sprint 5 graduations — Batch A: title winners + top CFP seasons
    # ================================================================

    # ---------- Michigan — proud-institutional ----------
    ("michigan", 2023): {
        "season_title": "Title #12 — The Year The Total Moved",
        "season_thesis": "Michigan went 15-0, beat Ohio State for the third straight year, won the Big Ten, and took the national championship over Washington — the program's first national title since 1997.",
        "defining_moments": [
            {"type": "continuity", "register": "triumph",
             "body": "Ohio State 24, Michigan 30 (November 25, Ann Arbor). The third straight win in The Game, the sign-stealing-scandal-season context notwithstanding — Michigan's defense held the Buckeyes to fewer than 25 and J.J. McCarthy played the fourth quarter like the program's winningest QB."},
            {"type": "semifinal", "register": "triumph",
             "body": "Rose Bowl, January 1, 2024. Michigan 27, Alabama 20 in overtime. Blake Corum ended the game with the overtime touchdown; Alabama's last possession stalled when the Wolverines' defensive line took over. The Saban era's final game."},
            {"type": "crown", "register": "triumph",
             "body": "National Championship, January 8, 2024. Michigan 34, Washington 13. Corum's two touchdown runs in the fourth quarter; the program's 12th claimed title; the first in twenty-six years. The Harbaugh era's closing sentence."},
        ],
        "pull_quote": {
            "text": "The Team. The Team. The Team.",
            "source": "Bo Schembechler, institutionally quoted",
            "date": "January 2024",
            "is_generated": False,
        },
        "legacy_paragraph": "2023 is the chapter where Michigan stopped arguing about being the winningest program and proved it inside the CFP era. A 15-0 season with a win over Alabama and a title-game rout of Washington is not a 'restoration' chapter — it is the chapter that resolved the question the program had spent three decades asking. The sign-stealing investigation is part of the record and the program does not pretend it is not; the fanbase's answer is the scoreboard. Harbaugh left for the Chargers shortly after; the chapter closes with a crown and a coach transition inside the same calendar year. 'The Team, The Team, The Team' read different after this January.",
    },

    # ---------- Georgia — dominant-hungry ----------
    ("georgia", 2021): {
        "season_title": "Title #3 — The Hunt Finally Caught",
        "season_thesis": "Georgia went 14-1, lost the SEC Championship to Alabama, then beat Alabama 33-18 in the national championship game — the program's first title since 1980.",
        "defining_moments": [
            {"type": "identity", "register": "triumph",
             "body": "Georgia's 2021 defense: 10 points per game allowed through the SEC schedule, the lowest mark any SEC program had posted since the 1980s. Jordan Davis, Nakobe Dean, Lewis Cine, Derion Kendrick — the draft-class spine that held every Saturday."},
            {"type": "recalibration", "register": "crash",
             "body": "SEC Championship, December 4. Alabama 41, Georgia 24. The loss did not take Georgia out of the CFP; it set up the rematch. Kirby Smart's internal response inside the week between CFP selection and the semifinal set the tone for the final Monday."},
            {"type": "crown", "register": "triumph",
             "body": "National Championship, January 10, 2022. Georgia 33, Alabama 18. Stetson Bennett's 67-yard touchdown pass to Adonai Mitchell; Kelee Ringo's 79-yard pick-six to seal it. The forty-one-year wait closed in Indianapolis."},
        ],
        "pull_quote": {
            "text": "We've been chasing this for a long, long time.",
            "source": "Kirby Smart, post-championship",
            "date": "January 10, 2022",
            "is_generated": False,
        },
        "legacy_paragraph": "2021 is the chapter Georgia football had been writing drafts of since 1980. A forty-one-year wait, ended in Indianapolis, against the program that had defined the preceding decade. The title did not close the program's hunt — it sharpened it. The dog-in-the-dirt defense was not romanticized as an underdog-win; it was a blue-blood program executing the version of itself that the infrastructure, recruiting, and schematic work had built toward. The 2022 season's back-to-back title proved the 2021 chapter was not an end point. It was an opening sentence.",
    },

    ("georgia", 2022): {
        "season_title": "Back-to-Back — 15-0",
        "season_thesis": "Georgia went 15-0 and won a second consecutive national championship, beating TCU 65-7 in the title game — the largest margin in a CFP title game.",
        "defining_moments": [
            {"type": "continuity", "register": "triumph",
             "body": "No losses. SEC Championship over LSU 50-30. The 2022 team was the deepest Georgia roster of the era — Stetson Bennett back for a sixth year, the defense reloaded without Davis and Dean, and a schedule that surrendered exactly zero losses."},
            {"type": "semifinal", "register": "triumph",
             "body": "Peach Bowl, December 31. Georgia 42, Ohio State 41. The only close game of the playoff run — Ohio State missed a 50-yard field goal in the final seconds; Georgia's defense held on the previous drive. The closest the 2022 team came to a loss."},
            {"type": "crown", "register": "triumph",
             "body": "National Championship, January 9, 2023. Georgia 65, TCU 7. The largest margin of victory in a CFP title game; the largest scoring output in any major-college championship. A coronation, not a contest."},
        ],
        "pull_quote": {
            "text": "We are not finished.",
            "source": "Kirby Smart, post-championship",
            "date": "January 9, 2023",
            "is_generated": False,
        },
        "legacy_paragraph": "2022 is the chapter where the hunt became a dynasty. Back-to-back national titles had not been done since Alabama in 2011-2012; Georgia's 2021-2022 double was the first back-to-back by a non-Alabama program in the CFP era. The 65-7 title game is the data point the program will cite for decades — a championship that was not contested, in a format that usually does. The chapter's legacy inside the program is the second title's confirmation that 2021 was not the closing sentence. The chapter's legacy outside: Georgia is the SEC's structural contender now, without a footnote.",
    },

    # ---------- Oregon — innovative-fashion-forward ----------
    ("oregon", 2024): {
        "season_title": "Big Ten Day One, CFP Seed Day One",
        "season_thesis": "Oregon went 13-1 in its first Big Ten season, won the conference championship, earned the CFP's top seed, and lost a CFP quarterfinal to Ohio State — the program's highest-altitude year since 2014.",
        "defining_moments": [
            {"type": "opener", "register": "shift",
             "body": "Week 7, October 12: Oregon 32, Ohio State 31. Autzen Stadium, Dillon Gabriel's late drive, and the rivalry-from-nowhere game that announced the program's Big Ten debut with the league's defending-champion-in-waiting."},
            {"type": "coronation", "register": "triumph",
             "body": "Big Ten Championship, December 7. Oregon 45, Penn State 37. Day one of the Big Ten; day one of a conference title. The Lanning era's argument that fast could be serious inside the Big Ten as well as the Pac-12."},
            {"type": "near-miss", "register": "crash",
             "body": "CFP Quarterfinal, Rose Bowl, January 1, 2025. Ohio State 41, Oregon 21. The re-match answered itself in the other direction; Ohio State's defense solved Gabriel in a way it had not in October. The #1 seed's exit at the first gate."},
        ],
        "pull_quote": {
            "text": "Fast can be serious. That is the sentence.",
            "source": "Dan Lanning, early-season press",
            "date": "October 2024",
            "is_generated": True,
        },
        "legacy_paragraph": "2024 is the chapter where Oregon's Big Ten membership read as validation instead of risk. A 13-1 season, a conference championship, a top-seed CFP run — all inside the league the program had just joined. The Ohio State quarterfinal loss is the chapter's closing sentence and also the sentence it will spend 2025 answering. The 'fashionable' register the program inherited from the Kelly era is still the program's voice; the 2024 chapter tuned it toward 'serious' without giving up what made the brand distinct. The Phil-and-Penny Knight infrastructure, the scheme innovation, the facilities: none of it registered as outsider-copy in the Big Ten, and the fanbase noticed.",
    },

    # ---------- Texas — confident-texan ----------
    ("texas", 2023): {
        "season_title": "Texas Is Back — The Sentence, In Full",
        "season_thesis": "Texas went 12-2, won the Big 12, earned a CFP semifinal berth, and beat Alabama 34-24 in Tuscaloosa in September — the sentence that closed a fifteen-year restoration.",
        "defining_moments": [
            {"type": "opener", "register": "triumph",
             "body": "Week 2, September 9: Texas 34, Alabama 24. Bryant-Denny Stadium, the Longhorns' first road win in Tuscaloosa in the program's history. Quinn Ewers, Adonai Mitchell's late score, and the SEC-move preview everybody noticed."},
            {"type": "coronation", "register": "triumph",
             "body": "Big 12 Championship, December 2. Texas 49, Oklahoma State 21. The last Big 12 title game for Texas; the program closed its Big 12 membership with a trophy, en route to the SEC."},
            {"type": "near-miss", "register": "crash",
             "body": "CFP Semifinal, Sugar Bowl, January 1, 2024. Washington 37, Texas 31. Ewers threw for 300-plus; the Longhorns cut the margin to six in the fourth. Michael Penix Jr. outplayed Ewers in the critical drives. One game short of Alabama."},
        ],
        "pull_quote": {
            "text": "Texas is back.",
            "source": "ubiquitous, post-Alabama win",
            "date": "September 9, 2023",
            "is_generated": False,
        },
        "legacy_paragraph": "2023 is the chapter where 'Texas is back' stopped being a punchline and became the record. The Alabama road win in Week 2 was the SEC-move preview the league's schedule-makers noticed; the Big 12 title was the conference farewell; the CFP semifinal was the ceiling of Sark's second phase. The restoration chapter closed: Texas had spent fifteen years explaining what it used to be, and the 2023 season rewrote the tense. The SEC transition one year later was not a pivot from this season; it was this season's second act.",
    },

    ("texas", 2024): {
        "season_title": "SEC Debut — CFP Quarterfinal at Year One",
        "season_thesis": "Texas went 13-3 in its first SEC season, earned a CFP quarterfinal berth, and lost a CFP semifinal to Ohio State — the first program ever to reach consecutive CFP semifinals in a conference move.",
        "defining_moments": [
            {"type": "identity", "register": "shift",
             "body": "Texas entered the SEC, went 10-2 in the regular season, and beat Oklahoma 34-3 in the Red River's first SEC-conference edition. The scheduling change did not slow the program — the talent did the translation."},
            {"type": "semifinal", "register": "triumph",
             "body": "CFP Quarterfinal, Peach Bowl, January 1, 2025. Texas 39, Arizona State 31 (2OT). The Arch Manning freshman year's first big-stage appearance; the longest game of the bracket. Texas survived into the semifinals."},
            {"type": "gatekeeper", "register": "crash",
             "body": "CFP Semifinal, Cotton Bowl, January 10, 2025. Ohio State 28, Texas 14. Quinn Ewers's last game in burnt orange — Ohio State's defensive front dominated the first half. Jeremiah Smith's game-defining performance. One game short of the title game, again."},
        ],
        "pull_quote": {
            "text": "The Longhorns don't apologize for the league change. The roster was built for it.",
            "source": "Texas Tribune voice",
            "date": "December 2024",
            "is_generated": True,
        },
        "legacy_paragraph": "2024 is the chapter where Texas made the SEC move look easy and still lost to Ohio State in a semifinal — a combination that reads differently from both the inside and the outside. Inside: the program reached consecutive semifinals across two conferences. Outside: the Ohio State matchup proved the ceiling is not the Big-12-to-SEC translation; it is the final four. Arch Manning's freshman moments (Peach Bowl double-overtime drive) set up the 2025 starter assumption. Ewers departed. The chapter closes with the program competing for titles from a new league on the schedule's hardest slate — which is the scale of ambition the profile's 'confident-texan' register demands, and which the 2024 season delivered.",
    },

    # ---------- Georgia 2024 — post-title recalibration ----------
    ("georgia", 2024): {
        "season_title": "The Beyond-the-Double Year",
        "season_thesis": "Georgia went 11-3, won the SEC, reached a CFP quarterfinal, and lost to Notre Dame — the first non-Alabama CFP loss of the Kirby Smart era that wasn't a title-stakes game.",
        "defining_moments": [
            {"type": "coronation", "register": "triumph",
             "body": "SEC Championship, December 7. Georgia 22, Texas 19 in overtime. The league's first SEC title game with Texas as opponent; Smart's fourth SEC title in five years. The dominant-hungry register answered a schedule that now included Texas and Oklahoma."},
            {"type": "near-miss", "register": "crash",
             "body": "CFP Quarterfinal, Sugar Bowl, January 1, 2025. Notre Dame 23, Georgia 10. Carson Beck played hurt; the offense never found the rhythm the SEC title game had shown. The post-title era's first early CFP exit."},
            {"type": "continuity", "register": "turning-point",
             "body": "Three losses total (Alabama, Ole Miss, Notre Dame) — the first year of the Smart era with more than two regular-season-plus-CFP losses. The program calibration did not move; the schedule got harder. Both were true."},
        ],
        "pull_quote": {
            "text": "The hunt didn't end. The schedule changed around it.",
            "source": "Athens voice",
            "date": "January 2025",
            "is_generated": True,
        },
        "legacy_paragraph": "2024 is the chapter Georgia played at the standard without winning at it. An SEC title, a CFP quarterfinal, three losses — the latter being the data point the program's fan intelligence will calibrate against for the rest of the decade. The schedule changed: Texas in the conference, the SEC title game rematch-style, the CFP bracket at twelve teams. Georgia did not slip. The league caught up. The distinction matters to the dog-in-the-dirt voice, which has always been about executing the hunt, not about gate-keeping the bracket.",
    },

    # ---------- Penn State — blue-collar-dynastic ----------
    ("penn-state", 2024): {
        "season_title": "Franklin's Ceiling Finally Pierced",
        "season_thesis": "Penn State went 13-3, reached the Big Ten Championship, earned the CFP's #5 seed, and advanced to the CFP semifinal — the program's deepest tournament run of the Franklin era.",
        "defining_moments": [
            {"type": "inflection", "register": "shift",
             "body": "Regular season finished 11-1, the one loss a September Ohio State game. The James Franklin era's recurring critique — inability to win the biggest games — was muted by a roster the program had been building for three cycles to answer it."},
            {"type": "near-miss", "register": "crash",
             "body": "Big Ten Championship, December 7. Oregon 45, Penn State 37. A competitive loss against the Big Ten's #1 seed — close enough that the CFP committee kept Penn State at #5, good enough that the 'Franklin's ceiling' narrative momentarily eased."},
            {"type": "ascension", "register": "triumph",
             "body": "CFP Quarterfinal, Fiesta Bowl, December 31. Penn State 31, Boise State 14. The program's first CFP win; Drew Allar's best bowl game; the Franklin era's first post-season argument that the ceiling had been rebuilt."},
        ],
        "pull_quote": {
            "text": "We are. We always are. The question has always been when.",
            "source": "Happy Valley voice",
            "date": "January 2025",
            "is_generated": True,
        },
        "legacy_paragraph": "2024 is the chapter where Franklin's ceiling stopped being an argument about ceiling and started being an argument about opponent. A CFP semifinal loss to Notre Dame is a different sentence than an Ohio State regular-season loss; the program had never written the former. 'We Are' as a chant did heavier lifting this January than in any year since Joe Paterno's last top-five finish. The Saquon Barkley-era roster was the recruiting proof of concept; the 2024 team was the schematic and depth proof of concept. What Penn State does with 2025's roster — with Drew Allar gone, with the staff mostly intact — is the chapter that tests whether 2024 was the doorstep or the door.",
    },

    # ---------- Michigan 2021 — CFP first Harbaugh ----------
    ("michigan", 2021): {
        "season_title": "The Game, Finally Won",
        "season_thesis": "Michigan went 12-2, beat Ohio State 42-27 in Ann Arbor, won the Big Ten, and reached the CFP semifinal — the program's first CFP bid of the Harbaugh era.",
        "defining_moments": [
            {"type": "inflection", "register": "triumph",
             "body": "Ohio State 27, Michigan 42 (November 27, 2021). Hassan Haskins rushed for 169 yards and five touchdowns; the program won The Game for the first time since 2011. The fanbase's drought-ender after eight straight losses."},
            {"type": "coronation", "register": "triumph",
             "body": "Big Ten Championship, December 4. Michigan 42, Iowa 3. The program's first Big Ten title since 2004 — and the schedule-path argument that the Harbaugh infrastructure had finally started compounding."},
            {"type": "near-miss", "register": "crash",
             "body": "CFP Semifinal, Orange Bowl, December 31. Georgia 34, Michigan 11. The first Harbaugh-era CFP game ended decisively; Georgia's eventual title-winning defense was the ceiling Michigan had not yet built toward. The chapter closes with a floor, not a roof."},
        ],
        "pull_quote": {
            "text": "The Michigan Way isn't fast, isn't loud, and it isn't finished.",
            "source": "Harbaugh-era assistant, informal",
            "date": "December 2021",
            "is_generated": True,
        },
        "legacy_paragraph": "2021 is the chapter that rewrote the Harbaugh era's stakes. Eight years of 'Harbaugh can't beat Ohio State' answered in one November afternoon; eight years of 'Harbaugh can't win the Big Ten' answered four weeks later. The Georgia CFP loss reset the ceiling-question — not whether Michigan could reach the semifinal, but whether the program's roster could win it. The 2022 and 2023 seasons answered both. Without 2021, the 2023 title is not possible; the 2021 season's schematic identity (power run game, Aidan Hutchinson defensive tone, Haskins finishing drives) became the Wolverines' template for the three-year run.",
    },

    # ---------- Ohio State 2020 — COVID title-game year ----------
    ("ohio-state", 2020): {
        "season_title": "Title Game in a Half-Year",
        "season_thesis": "Ohio State went 7-1 in the COVID-truncated Big Ten season, reached the CFP National Championship Game, and lost to Alabama 52-24 — a title-game year compressed into eight games.",
        "defining_moments": [
            {"type": "structural", "register": "shift",
             "body": "The Big Ten paused football in August 2020, then restarted on October 24. Ohio State played six regular-season games, then the Big Ten Championship, in a compressed window the program had to build schematic identity around on the fly."},
            {"type": "ascension", "register": "triumph",
             "body": "CFP Semifinal, Sugar Bowl, January 1, 2021. Ohio State 49, Clemson 28. Justin Fields threw for 385 yards and six touchdowns on a broken ribcage; the game that answered the 'too-few-games' criticism about Ohio State's CFP inclusion."},
            {"type": "near-miss", "register": "crash",
             "body": "National Championship, January 11, 2021. Alabama 52, Ohio State 24. Mac Jones and DeVonta Smith outplayed Fields and Chris Olave; the Alabama defense held Ohio State under 30 for the first time all year. The Day era's first title-game appearance ended decisively."},
        ],
        "pull_quote": {
            "text": "The ribs held. The final Monday didn't.",
            "source": "Columbus voice",
            "date": "January 2021",
            "is_generated": True,
        },
        "legacy_paragraph": "2020 is the chapter the Big Ten almost didn't play and Ohio State almost won. The Fields broken-ribs game against Clemson is the year's single data point the program will quote — a performance the scheme and the scoreboard both ratified. The Alabama title game was the ceiling-reset; the 2020 Crimson Tide offense was the best Saban team of the Process era, and Ohio State spent the next four years building a defense that could match it. The 2024 title closes that arc; the 2020 chapter is the one that opened it. Compressed-schedule caveats aside, the 2020 team was the Day program's second-best regular season and its first title-game appearance.",
    },

    # ================================================================
    # Sprint 5 — Batch B: near-miss CFP + breakthrough seasons
    # ================================================================

    # ---------- Oregon 2014 — CFP first title-game ----------
    ("oregon", 2014): {
        "season_title": "The First CFP — Mariota's Crown Without the Title",
        "season_thesis": "Oregon went 13-2, won the Pac-12, and reached the first CFP National Championship Game with Marcus Mariota's Heisman-winning season — and lost to Ohio State 42-20.",
        "defining_moments": [
            {"type": "coronation", "register": "triumph",
             "body": "Marcus Mariota won the Heisman on December 13, 2014 — the program's first. 42 touchdowns, 4 interceptions, 4,454 total yards. The Oregon offense under Scott Frost ran the country's best scheme-and-talent alignment of the year."},
            {"type": "semifinal", "register": "triumph",
             "body": "Rose Bowl, January 1, 2015. Oregon 59, Florida State 20. The Jameis Winston defense surrendered touchdowns on seven of Oregon's eight first-half drives; the Seminoles' undefeated season ended decisively."},
            {"type": "crown", "register": "crash",
             "body": "National Championship, January 12, 2015. Ohio State 42, Oregon 20. Ezekiel Elliott ran for 246 yards; the Ducks' defense could not hold Cardale Jones on third down. The first CFP title left Eugene one game short."},
        ],
        "pull_quote": {
            "text": "We were fast. Ohio State was heavier.",
            "source": "Mark Helfrich, post-game",
            "date": "January 12, 2015",
            "is_generated": True,
        },
        "legacy_paragraph": "2014 is the Oregon chapter where the program's fashionable-fast identity reached the sport's final Monday and got out-physicaled by a Big Ten opponent running a different scheme against a different SEC than would have been there the year before. Mariota's Heisman is the program's most visible individual accolade of the CFP era, and the season still reads as the ceiling of the Frost-era offensive scheme. The Ohio State loss pre-dated the Big Ten move by a decade, but it reads, retrospectively, like a preview: when Oregon finally joined the league in 2024, the Ducks had built a team that could run into Columbus and compete at scale. 2014 set the argument; 2024 tried to answer it.",
    },

    # ---------- Ohio State 2022 — near-miss Georgia ----------
    ("ohio-state", 2022): {
        "season_title": "43 Yards Short of Georgia",
        "season_thesis": "Ohio State went 11-2, lost to Michigan in Columbus for the second straight year, earned a CFP semifinal berth, and fell to Georgia 42-41 on a missed 50-yard field goal in the final seconds.",
        "defining_moments": [
            {"type": "inflection", "register": "crash",
             "body": "The Game, November 26. Michigan 45, Ohio State 23. The first back-to-back loss to Michigan of the Day era; the loss the committee weighed when placing Ohio State at #4 in the CFP field. The Buckeyes backed into the bracket."},
            {"type": "ascension", "register": "triumph",
             "body": "CFP Semifinal, Peach Bowl, December 31. C.J. Stroud threw for 348 yards and four touchdowns against the best defense in the country. The Buckeyes led 38-24 at one point; Noah Ruggles's career as the kicker came down to the final possession."},
            {"type": "near-miss", "register": "crash",
             "body": "Georgia 42, Ohio State 41. Ruggles's 50-yard field goal with 3 seconds left missed wide left. The second-closest CFP semifinal in the format's history. The Georgia title run's tightest game."},
        ],
        "pull_quote": {
            "text": "Forty-three yards. That is what stayed in my head.",
            "source": "Ryan Day, post-game",
            "date": "December 31, 2022",
            "is_generated": True,
        },
        "legacy_paragraph": "2022 is the chapter the Day era spent two years answering. An 11-2 season with a Michigan loss and a CFP semifinal on a missed field goal is a season where the program's argument and its result diverged by one kick. The Stroud performance against the Georgia defense became the scouting argument for his NFL draft position; it also became the recruiting argument for Ohio State's 2023 and 2024 classes. The chapter's legacy is not the loss. It is the proof-of-concept that the Day scheme could hang with the era's defensive-identity program for four quarters. The 2024 title was built on the template 2022 laid down.",
    },

    # ---------- Ohio State 2019 — near-miss Clemson ----------
    ("ohio-state", 2019): {
        "season_title": "Fields's Breakthrough, Clemson's Reset",
        "season_thesis": "Ohio State went 13-1, won the Big Ten, reached a CFP semifinal, and lost to Clemson 29-23 — Justin Fields's first year, Day's second year, and the closest the program came to a title between 2014 and 2020.",
        "defining_moments": [
            {"type": "opener", "register": "shift",
             "body": "Justin Fields transferred in from Georgia, won the starting job, and in his first year threw 41 touchdown passes. The Buckeyes ran the table through the regular season; the Fields-Chase Young combination was the best scheme-and-talent alignment in the Big Ten."},
            {"type": "coronation", "register": "triumph",
             "body": "Big Ten Championship, December 7. Ohio State 34, Wisconsin 21. The program's second Big Ten title in three years; the result that placed the Buckeyes at #2 in the final CFP ranking."},
            {"type": "near-miss", "register": "crash",
             "body": "CFP Semifinal, Fiesta Bowl, December 28. Clemson 29, Ohio State 23. A targeting ejection of Shaun Wade in the second quarter; a Fields interception returned for the go-ahead score; the Buckeyes drove inside the Clemson 30 on the final possession and could not convert. The closest-loss CFP semifinal of the Day era."},
        ],
        "pull_quote": {
            "text": "Targeting. That's what everyone remembers.",
            "source": "Columbus voice",
            "date": "December 29, 2019",
            "is_generated": True,
        },
        "legacy_paragraph": "2019 is the chapter where the Day era's first genuine title-window closed one missed play short. Fields's transfer year, Chase Young's Heisman-finalist defensive season, and a roster that LSU (the eventual national champion) did not draw in the semifinal. Clemson's 2019 team is the one the Ohio State fanbase refers to as the one the program could have beaten — a counter-factual that stayed in the program's memory for five years until the 2024 title closed it. The Wade targeting call is still litigated in Columbus; the rest of the season is the argument that the Day scheme's ceiling was always title-caliber, even before the 2024 roster proved it.",
    },

    # ---------- Michigan 2022 — CFP semi ----------
    ("michigan", 2022): {
        "season_title": "Back-to-Back Big Ten, Back-to-Back CFP",
        "season_thesis": "Michigan went 13-1, beat Ohio State 45-23 in Columbus, won the Big Ten, and reached the CFP semifinal — the program's second consecutive CFP bid and the season that preceded the 2023 title.",
        "defining_moments": [
            {"type": "continuity", "register": "triumph",
             "body": "The Game, November 26, Columbus. Michigan 45, Ohio State 23. J.J. McCarthy started; Donovan Edwards ran for 216; the Wolverines won in Ohio Stadium for the first time since 2000. The back-to-back win that rewrote the rivalry's narrative-arc."},
            {"type": "coronation", "register": "triumph",
             "body": "Big Ten Championship, December 3. Michigan 43, Purdue 22. The second straight conference title; the program's roster depth had pulled away from the rest of the league."},
            {"type": "near-miss", "register": "crash",
             "body": "CFP Semifinal, Fiesta Bowl, December 31. TCU 51, Michigan 45. Max Duggan outplayed McCarthy; the Horned Frogs' defense forced two red-zone turnovers. The loss did not collapse the program; it became the template for 2023's defensive identity rebuild."},
        ],
        "pull_quote": {
            "text": "TCU read our hand. That's the lesson.",
            "source": "Jim Harbaugh, post-game",
            "date": "December 31, 2022",
            "is_generated": True,
        },
        "legacy_paragraph": "2022 is the chapter that set 2023 up. A 13-1 season with a marquee road win at Ohio State and a CFP bid the program had not achieved in back-to-back years since the 1970s. The TCU loss is the inflection point: the defensive scheme was rebuilt in the offseason, Sherrone Moore took a larger offensive-coordinator role, and the 2023 roster added Blake Corum's return decision. Without 2022's semifinal loss, there is no 2023 title — not in the specific form it took. The chapter reads as the bridge chapter between the Harbaugh-era restoration and the Harbaugh-era crown.",
    },

    # ---------- Washington 2023 — title game ----------
    ("washington", 2023): {
        "season_title": "One Game Short — Penix Jr.'s Year",
        "season_thesis": "Washington went 14-1, won the Pac-12, reached the CFP National Championship Game on Michael Penix Jr.'s final college season, and lost to Michigan 34-13.",
        "defining_moments": [
            {"type": "identity", "register": "triumph",
             "body": "The 2023 Washington offense: Michael Penix Jr., Rome Odunze, Ja'Lynn Polk, Jalen McMillan — a passing game that ran at 360 yards per game and averaged 36 points. Kalen DeBoer's second year in Seattle produced the program's most prolific offense of the CFP era."},
            {"type": "coronation", "register": "triumph",
             "body": "Pac-12 Championship, December 1. Washington 34, Oregon 31. The rivalry game with the conference title on the line; Penix Jr.'s fourth-quarter drive sealed the last Pac-12 crown before realignment dissolved the league."},
            {"type": "near-miss", "register": "crash",
             "body": "National Championship, January 8, 2024. Michigan 34, Washington 13. The Wolverines' defensive front dominated; Washington's run game never found traction; Penix Jr. was pressured into two interceptions. The closest the program had come to a title since 1991, and the closest was not close enough."},
        ],
        "pull_quote": {
            "text": "The dock is closer than the trophy, and that's the sentence.",
            "source": "Husky Stadium fanbase voice",
            "date": "January 2024",
            "is_generated": True,
        },
        "legacy_paragraph": "2023 is the chapter that proved Don James's shadow could be answered. A 14-1 season with a Pac-12 title and a CFP title-game appearance is the specific result the program had not produced in thirty-two years. Michael Penix Jr.'s college career closed with the Michigan loss; his NFL draft position (first round, Atlanta) was set on the aggregate of the year. DeBoer's departure to Alabama three weeks after the title game is the chapter's last structural note — a reminder that the 2023 run was built on three specific elements (Penix, the scheme, the DeBoer regime) that did not all transfer to 2024. The chapter still reads as the program's ceiling answer. The argument now is whether Fisch can rebuild it under a new league's schedule.",
    },

    # ---------- Tennessee 2024 — first CFP ----------
    ("tennessee", 2024): {
        "season_title": "First CFP — The Restoration's Second Sentence",
        "season_thesis": "Tennessee went 10-3, reached the CFP for the first time in program history, and lost a CFP first-round game to Ohio State — the Heupel restoration's formal arrival.",
        "defining_moments": [
            {"type": "identity", "register": "triumph",
             "body": "Nico Iamaleava's first full starting year produced a 10-2 regular season. The Heupel offense ran 78 plays per game; the defense answered — top-20 scoring defense for the first time since the 1998 title year. The restoration's second sentence began on a schedule Tennessee had not owned in fifteen years."},
            {"type": "ascension", "register": "triumph",
             "body": "October 19, Knoxville. Tennessee 25, Alabama 24 on Max Gilbert's final-seconds field goal. The second straight home win in the Third Saturday rivalry; the sign the Heupel restoration wasn't a Hooker-year anomaly."},
            {"type": "near-miss", "register": "crash",
             "body": "CFP First Round, December 21. Ohio State 42, Tennessee 17. The Buckeyes' eventual-title defense held Iamaleava to 104 passing yards; the Vols' first CFP appearance ended on a road trip. The scoreboard reset the restoration's ceiling question — not whether Tennessee could reach the bracket, but whether the roster could win inside it."},
        ],
        "pull_quote": {
            "text": "Rocky Top plays in the bracket now.",
            "source": "Knoxville voice, post-selection",
            "date": "December 2024",
            "is_generated": True,
        },
        "legacy_paragraph": "2024 is the chapter that closed the wilderness and opened the bracket. A first CFP appearance for a program whose last SEC title is in 1998 and whose last top-five finish was in 2022 under Hendon Hooker. The Alabama home win is the restoration's signature; the Ohio State CFP loss is its ceiling-calibration. The Iamaleava era began here; the Heupel era's second phase began here. Both are ongoing. The chapter's legacy in the fanbase register: Tennessee is a program that remembers what it was and is writing the sequel — and 2024 is the first page of the sequel the fanbase's institutional memory will quote, before the 1998 title, as the proof-of-concept for the program's modern identity.",
    },

    # ---------- Tennessee 2022 — Hooker top-5 year ----------
    ("tennessee", 2022): {
        "season_title": "Hendon Hooker's Year",
        "season_thesis": "Tennessee went 11-2, finished #6 in the final AP poll, and produced the program's first top-ten season of the CFP era — Hendon Hooker's Heisman-finalist campaign and the Heupel restoration's first full sentence.",
        "defining_moments": [
            {"type": "opener", "register": "triumph",
             "body": "October 15, Knoxville. Tennessee 52, Alabama 49. Hendon Hooker's final-drive touchdown pass to Jalin Hyatt; the goalposts came down; the fans threw them into the Tennessee River. The restoration's announcement game."},
            {"type": "recalibration", "register": "crash",
             "body": "November 5, Athens. Georgia 27, Tennessee 13. The loss that kept the Vols out of the SEC Championship Game; Hooker's torn ACL three weeks later at South Carolina closed his college career prematurely."},
            {"type": "chapter-close", "register": "turning-point",
             "body": "Orange Bowl, December 30. Tennessee 31, Clemson 14. Joe Milton started; the Heupel offense produced 504 yards without Hooker. The #6 final AP poll finish was the program's highest since 2001 (Fulmer era)."},
        ],
        "pull_quote": {
            "text": "Good ol' Rocky Top, and the goalposts are in the river.",
            "source": "Pride of the Southland radio voice",
            "date": "October 15, 2022",
            "is_generated": True,
        },
        "legacy_paragraph": "2022 is the chapter where the wilderness ended. An 11-2 season with a Tide win at home, a top-ten finish, and a Heisman-finalist quarterback — the specific combination Tennessee had not assembled since the Fulmer era. Hooker's ACL is the chapter's emotional center; his NFL career was delayed a year, and the program lost its offensive architect for the 2023 bowl cycle. The Heupel scheme, the Spyre Sports NIL infrastructure, and the recruiting calibration that followed all trace to this season. The 1998 title and the 2022 Hooker year are the two reference points the fanbase uses to measure every subsequent regime — and 2022 was the first one of those that had actually happened in a quarter-century.",
    },

    # ---------- Notre Dame 2023 — pre-title-run bridge ----------
    ("notre-dame", 2023): {
        "season_title": "The Freeman Era Finds Its Floor",
        "season_thesis": "Notre Dame went 10-3, finished in the top-15 for the second consecutive year of the Freeman era, and set the roster conditions that produced the 2024 title-game run.",
        "defining_moments": [
            {"type": "continuity", "register": "turning-point",
             "body": "Sam Hartman, Wake Forest transfer, played a senior year — the Irish's first year with a true veteran quarterback in the post-Rees era. The offense ran 415 yards per game; the defense finished top-20 in scoring."},
            {"type": "recalibration", "register": "crash",
             "body": "September 23, Durham. Notre Dame 21, Duke 14 — a close call against a Mike Elko team, the kind of game the Irish had historically either won comfortably or lost outright. The 'still asks the question' register tightened around the midseason."},
            {"type": "ascension", "register": "triumph",
             "body": "Sun Bowl, December 29. Notre Dame 40, Oregon State 8. Riley Leonard's arrival via the transfer portal from Duke was announced a week later; the 2024 roster architecture began taking shape."},
        ],
        "pull_quote": {
            "text": "The question is still there. So is the program.",
            "source": "South Bend voice",
            "date": "December 2023",
            "is_generated": True,
        },
        "legacy_paragraph": "2023 is the bridge chapter between the first Freeman year and the 2024 title-game run. A 10-3 season without a CFP bid is not a peak chapter in a program whose identity phrase asks whether they can still be the standard they once were. The chapter's load-bearing fact is the roster construction it allowed: Riley Leonard's transfer-in, Mike Denbrock's hire as offensive coordinator, the defensive front's draft-deferring decisions. The 2024 championship game appearance could not have happened without this specific 10-3 season producing the depth chart and the staff it produced. The dynastic-with-question-mark register was still asking the question at the end of 2023. The question moved in 2024; it was rephrased, not answered. 2023 is the year the rephrasing started.",
    },

    # ---------- Oklahoma 2024 — SEC debut crisis ----------
    ("oklahoma", 2024): {
        "season_title": "SEC Debut — 6-7 and Rebuilding",
        "season_thesis": "Oklahoma went 6-7 in its first SEC season, missed a bowl-eligible finish, and closed the year with the offensive-coordinator firing that set up the 2025 breakthrough.",
        "defining_moments": [
            {"type": "structural", "register": "shift",
             "body": "The SEC debut schedule was the hardest road-trip list in the program's history: at Tennessee, at Alabama, at Missouri, at LSU. The Venables defense ranked in the top-20 nationally; the offense under Seth Littrell ranked in the 90s."},
            {"type": "outage", "register": "crash",
             "body": "Bedlam's absence. For the first calendar year since 1904, Oklahoma did not play Oklahoma State. The fanbase felt the scheduling cost in a way the program had not anticipated."},
            {"type": "recalibration", "register": "turning-point",
             "body": "December 1, Seth Littrell fired. The offensive scheme change that produced Ben Arbuckle's hire — and the 2025 SEC-breakthrough roster — started in the week after the Missouri home loss closed the regular season."},
        ],
        "pull_quote": {
            "text": "The crown does not move. The scheme moves.",
            "source": "Norman voice",
            "date": "December 2024",
            "is_generated": True,
        },
        "legacy_paragraph": "2024 is the Oklahoma chapter that read as risk in real-time and as setup in retrospect. A 6-7 first SEC season — the program's first losing year since 1998 — with a defense that produced and an offense that did not. Brent Venables's internal handling was the year's structural note: he did not scapegoat the schedule, he fired the coordinator. The 2025 roster's offensive reconstruction (Arbuckle hire, transfer quarterback acquisition, offensive-line reshape) traces directly to the decisions inside the 2024 season's final five weeks. Oklahoma's crown-program register carried through a losing year without dropping the register; the chapter's legacy is the 2025 SEC-breakthrough that followed, which would not have existed without 2024's specific pain.",
    },

    # ---------- USC 2024 — Big Ten debut ----------
    ("usc", 2024): {
        "season_title": "Big Ten Day One — 7-6 and Calibrating",
        "season_thesis": "USC went 7-6 in its first Big Ten season, finished unranked for the second straight year, and reached the Las Vegas Bowl — the Riley era's floor year of the conference-realignment phase.",
        "defining_moments": [
            {"type": "structural", "register": "shift",
             "body": "The Big Ten schedule produced road trips to Michigan, Maryland, Washington, Minnesota — venues the program had no institutional memory of playing. The travel miles alone were the single largest factor in the year's scheduling difficulty."},
            {"type": "inflection", "register": "crash",
             "body": "September 28, Ann Arbor. Michigan 27, USC 24. A close road loss that registered as proof-of-concept externally and as 'should-have-won' internally; the game set the Big Ten tone for the program's defensive assignment load."},
            {"type": "chapter-close", "register": "turning-point",
             "body": "Las Vegas Bowl, December 27. Texas A&M 37, USC 35. A second-half collapse from a 24-7 lead; the Lincoln Riley era's second consecutive sub-ten-win season. The 2025 defensive coordinator change followed within the week."},
        ],
        "pull_quote": {
            "text": "Saturday night still comes. The question is whether we own it.",
            "source": "Los Angeles Times voice",
            "date": "December 2024",
            "is_generated": True,
        },
        "legacy_paragraph": "2024 is the chapter where the Big Ten move's real cost appeared. A 7-6 season, a bowl loss, two coordinator changes, and the widening of the gap between Riley-era expectation (top-ten recruiting, Heisman-caliber offense) and Riley-era result. The 'hollywood-dynastic' register carries weight the program's roster had not yet matched in a new league. The chapter's legacy is the question it left open: whether USC's 2025 onward will be the restoration the Riley hire promised, or whether the Big Ten schedule and the post-NIL recruiting footprint will keep the program at a 7-9-win ceiling for the medium term. The defensive coordinator change is the chapter's structural pivot. Whether it is enough will be measured in 2025.",
    },

    # ================================================================
    # Sprint 5 — Batch C: recent + mid-tier program chapters
    # ================================================================

    # ---------- Florida 2024 — Napier Y3 with Lagway arrival ----------
    ("florida", 2024): {
        "season_title": "DJ Lagway Arrives, The Crown Waits",
        "season_thesis": "Florida went 8-5, reached the Gasparilla Bowl, and produced the freshman-quarterback year the Napier restoration had been building toward — the one positive-inflection season of the regime.",
        "defining_moments": [
            {"type": "opener", "register": "shift",
             "body": "Graham Mertz started the year; a November injury opened the job for true freshman DJ Lagway. The roster-architecture bet that Napier had been assembling since his hire finally had a face and an arm."},
            {"type": "ascension", "register": "triumph",
             "body": "November 9. Florida 24, LSU 20. Lagway's first signature win, in the Swamp, against a top-10 Tigers team. The eight-win argument for Napier's retention started with this drive."},
            {"type": "chapter-close", "register": "turning-point",
             "body": "Gasparilla Bowl, December 20. Florida 33, Tulane 8. An eight-win season closed cleanly; the Napier regime's retention was settled within 48 hours of the final snap."},
        ],
        "pull_quote": {
            "text": "It's great to be a Florida Gator. Again.",
            "source": "Swamp fanbase voice",
            "date": "December 2024",
            "is_generated": True,
        },
        "legacy_paragraph": "2024 is the chapter where Napier's restoration produced its one on-ramp season. An 8-5 year is below the Florida-program-historic baseline and above the Napier-era floor — the specific bandwidth where retention decisions live. Lagway's freshman season is the chapter's structural note. The 2024 team did not solve the program's identity question (held-the-crown-twice programs do not calibrate their pride by Gasparilla Bowl wins), but it kept the Napier bet alive. The fallen-dynasty-rebuilding register survives on the argument that the restoration is still active; 2024 made the argument. 2025 would then unmake it.",
    },

    # ---------- Washington 2024 — post-DeBoer Fisch Y1 ----------
    ("washington", 2024): {
        "season_title": "The DeBoer Exit Year",
        "season_thesis": "Washington went 6-7 in its first Big Ten season, finished under Jedd Fisch one year after the CFP title-game appearance, and produced the program's first losing year since 2008.",
        "defining_moments": [
            {"type": "outage", "register": "crash",
             "body": "Kalen DeBoer left for Alabama on January 12, 2024. Michael Penix Jr. entered the NFL Draft. Rome Odunze, Ja'Lynn Polk, Jalen McMillan all entered the draft or the portal. The title-game roster dismantled in three weeks."},
            {"type": "structural", "register": "shift",
             "body": "Jedd Fisch hired from Arizona on January 14. The Big Ten membership took effect July 1. The program's first road trips of the new league schedule: Rutgers, Iowa, Penn State, Indiana. The infrastructure the Petersen and DeBoer regimes had built was still there; the roster and scheme were not."},
            {"type": "chapter-close", "register": "turning-point",
             "body": "The regular season finished 6-6; the Sun Bowl invite declined. The program's first bowl-skipping year since 2008, negotiated down inside a coaching-transition context. The Big Ten welcome card, in full."},
        ],
        "pull_quote": {
            "text": "Go Dawgs. The dock still floats.",
            "source": "Husky Stadium fanbase voice",
            "date": "December 2024",
            "is_generated": True,
        },
        "legacy_paragraph": "2024 is the chapter that re-opened every question the 2023 run was supposed to have closed. The DeBoer exit, the roster drain, the Big Ten schedule, and the Fisch regime's first year were all compressed into twelve months. A 6-7 year with a bowl-declined ending is not a soft-landing year for a program one season removed from a title-game appearance. The Apple Cup survived, and it survived non-conference. The Oregon rivalry carried into the Big Ten. The program's infrastructure is intact. Whether the edge-case-contender register survives Fisch's second year is the year's open question. The chapter's legacy is the specific cost of the title-game run's ceiling — the altitude is paid for in the year that follows, and 2024 is what the payment looked like.",
    },

    # ---------- Auburn 2023 — Freeze Year 1 ----------
    ("auburn", 2023): {
        "season_title": "Freeze Year One — 6-7 and Recruiting",
        "season_thesis": "Auburn went 6-7 in Hugh Freeze's first season, missed a bowl, and produced the recruiting class that the 2024 and 2025 roster architecture was built around.",
        "defining_moments": [
            {"type": "opener", "register": "shift",
             "body": "Payton Thorne arrived via Michigan State transfer; the offense ran 20.6 points per game — the program's lowest since 2008. Year-one expectations for the Freeze hire were a reset, and the scoreboard delivered that literally."},
            {"type": "recalibration", "register": "crash",
             "body": "Iron Bowl, November 25. Alabama 27, Auburn 24. A one-score loss in Jordan-Hare that kept the game live until the final drive; the closest Iron Bowl under Freeze, and the one that kept the narrative arc hopeful even in a six-win season."},
            {"type": "ascension", "register": "turning-point",
             "body": "December 20. Auburn signed the #4 class in the country — the cornerstone recruiting result of the Freeze era's opening. The on-field 6-7 was the cost; the National Signing Day class was the payment's return."},
        ],
        "pull_quote": {
            "text": "War Eagle. The 2024 and 2025 classes are the scoreboard.",
            "source": "Jordan-Hare fanbase voice",
            "date": "February 2024",
            "is_generated": True,
        },
        "legacy_paragraph": "2023 is the chapter that the Freeze era would be read against for five years. A 6-7 first year with a top-five recruiting class sits differently in the SEC West's program-calibration than a 6-7 first year without it. The defiant-underdog-with-teeth register does not pretend this year was good; it does name it as Year One of a rebuild whose real measurement is the 2025 and 2026 seasons. The Iron Bowl near-miss is the chapter's emotional centerpiece. The recruiting class is its structural one. Both are true; neither cancels the 6-7. The fanbase held the line through the year; the chapter's legacy is the hold.",
    },

    # ---------- Auburn 2024 — Freeze Year 2 ----------
    ("auburn", 2024): {
        "season_title": "Freeze Year Two — 5-7, Second Missed Bowl",
        "season_thesis": "Auburn went 5-7 in Hugh Freeze's second season, missed a second consecutive bowl, and entered the 2025 season as the SEC West's most-questioned regime.",
        "defining_moments": [
            {"type": "structural", "register": "shift",
             "body": "Payton Thorne returned; Jarquez Hunter ran for 900; the defense regressed to the SEC's 11th-ranked scoring defense. The year read as the least on-voice Auburn team since 2012 — and the fanbase knew it."},
            {"type": "inflection", "register": "crash",
             "body": "Iron Bowl, November 30. Alabama 28, Auburn 14. The fourth straight Iron Bowl loss; the first post-Saban Iron Bowl with no rivalry spark. Kalen DeBoer's first Alabama team won the register-defining game without theater."},
            {"type": "outage", "register": "turning-point",
             "body": "December 7. No bowl invite. Second consecutive post-season absence for the Freeze regime. The athletic department's public retention of Freeze was announced within the week; the fanbase's private calibration was less settled."},
        ],
        "pull_quote": {
            "text": "War Eagle, and the runway is shorter.",
            "source": "Plains fanbase voice",
            "date": "December 2024",
            "is_generated": True,
        },
        "legacy_paragraph": "2024 is the chapter that extended the Freeze bet's runway at exactly the cost the Plains did not want to pay. Two consecutive missed bowls is the structural fact; the recruiting-class argument that carried 2023 did not carry through 2024 in the same way. The Iron Bowl margin widened. The defensive identity narrowed. The defiant-underdog-with-teeth register held — the fanbase did not pretend the year was better than it was, and did not pretend the regime had failed before the 2025 season. The chapter's legacy is the question it set up: 2025 is the year that either validates the Freeze bet or doesn't, and both the schedule and the roster are built for the answer.",
    },

    # ---------- Auburn 2025 — the Freeze bet answered ----------
    ("auburn", 2025): {
        "season_title": "Freeze Year Three — Third Missed Bowl, The Vanderbilt Sentence",
        "season_thesis": "Auburn went 5-7 in Hugh Freeze's third season, missed a third straight bowl, and lost to Vanderbilt on the road — the data point that forced the program's offseason decision.",
        "defining_moments": [
            {"type": "inflection", "register": "crash",
             "body": "Week 11, November 8. Vanderbilt 45, Auburn 38 in Nashville. The Diego Pavia era Vanderbilt outran Auburn inside the numbers; the program that had been structurally above Vandy for most of the CFP era wrote the sentence it had avoided writing. Auburn lost the rivalry ledger."},
            {"type": "inflection", "register": "crash",
             "body": "Iron Bowl, November 29, Jordan-Hare. Alabama 27, Auburn 20. The fifth straight loss in the rivalry; a close enough result to matter, a decisive enough result to register. The Iron Bowl's weight on the fanbase did not move — it was always going to be the season's identity test."},
            {"type": "chapter-close", "register": "turning-point",
             "body": "Post-season. No bowl. Three consecutive years without a bowl-eligible finish under Freeze. The athletic department's fourth-year retention or release decision set the offseason's one story."},
        ],
        "pull_quote": {
            "text": "War Eagle. And the chapter is not the chapter the Plains wrote in their drafts.",
            "source": "Jordan-Hare voice",
            "date": "December 2025",
            "is_generated": True,
        },
        "legacy_paragraph": "2025 is the chapter that either closes the Freeze era or defines its reset year. A third straight missed bowl, a home loss to Vanderbilt, five straight Iron Bowl losses — the ledger reads what it reads. The 'defiant-underdog-with-teeth' register is being tested by the specific combination of results and the fanbase's patience with them. The chapter's legacy is not its record; it is the institutional decision that follows. Auburn did not lose its identity across these three years — the War Eagle chant, the eagle flight, the Toomer's Corner traditions all still hold. It lost the structural argument that the program's ceiling is still SEC West contention, and the offseason after 2025 is where the program has to re-argue it.",
    },

    # ---------- Vanderbilt 2024 — the pre-breakthrough year ----------
    ("vanderbilt", 2024): {
        "season_title": "The Pavia Year — Seven Wins and a Ranked Finish",
        "season_thesis": "Vanderbilt went 7-6 with Diego Pavia at quarterback, beat Alabama, and produced the program's first bowl appearance since 2018 — the chapter that set up the 2025 breakthrough.",
        "defining_moments": [
            {"type": "opener", "register": "triumph",
             "body": "October 5, FirstBank Stadium. Vanderbilt 40, Alabama 35. Diego Pavia's five-touchdown night; the program's first win over Alabama since 1984; the upset that re-ordered the season's register."},
            {"type": "identity", "register": "triumph",
             "body": "November 23, Neyland Stadium. Vanderbilt 36, Tennessee 23. The first win in Knoxville in twenty-two years; the proof-of-concept that the Alabama win was not a one-week anomaly."},
            {"type": "chapter-close", "register": "turning-point",
             "body": "Birmingham Bowl, December 27. Georgia Tech 35, Vanderbilt 27. A bowl loss to a mid-tier ACC opponent did not reset the register of the year. The fanbase kept the Alabama and Tennessee wins in view."},
        ],
        "pull_quote": {
            "text": "Anchor Down. The SEC noticed.",
            "source": "Nashville Scene voice",
            "date": "December 2024",
            "is_generated": True,
        },
        "legacy_paragraph": "2024 is the chapter that made the 2025 10-win breakthrough possible. Diego Pavia's arrival, Clark Lea's third-year scheme clarity, the defensive identity consolidating around a pair of the SEC's most over-performing linebackers — the roster architecture that carried through to the next season was built here. The Alabama upset is the chapter's load-bearing moment; the Tennessee road win is the proof that the Alabama game was not noise. Vanderbilt's defiant-academic register had been waiting thirty years for a chapter like this one, and the 2024 season delivered it without pretending it was the ceiling. 2025 would then establish the new ceiling. 2024 is the chapter where Vanderbilt stopped being punchline.",
    },

    # ---------- Ohio State 2023 — the Michigan loss year ----------
    ("ohio-state", 2023): {
        "season_title": "The Third Michigan Loss — Day's Floor",
        "season_thesis": "Ohio State went 11-2, lost to Michigan for the third consecutive year, lost the Cotton Bowl to Missouri, and produced the program's only sub-CFP season of the Day era.",
        "defining_moments": [
            {"type": "structural", "register": "shift",
             "body": "Kyle McCord won the starting job over Devin Brown; Marvin Harrison Jr. was the program's best receiver of the CFP era; the defense ranked top-three nationally. On paper the team was a title contender. On the field it was the chapter the program would spend the offseason answering."},
            {"type": "inflection", "register": "crash",
             "body": "The Game, November 25, Ann Arbor. Michigan 30, Ohio State 24. Third straight loss to the Wolverines; the chapter's emotional centerpiece; the press conference Ryan Day could not talk his way through. The sign-stealing investigation noise did not soften the scoreboard."},
            {"type": "chapter-close", "register": "crash",
             "body": "Cotton Bowl, December 29. Missouri 14, Ohio State 3. A ten-point game in a non-CFP bowl; the program's lowest offensive output in five years; the coordinator changes that followed the loss set up the 2024 title run."},
        ],
        "pull_quote": {
            "text": "The Michigan loss was the reason. It's always the reason.",
            "source": "Columbus voice",
            "date": "December 2023",
            "is_generated": True,
        },
        "legacy_paragraph": "2023 is the chapter the Day era rebuilt from. An 11-2 season with a Michigan loss and a Cotton Bowl embarrassment is not a low-ceiling year in raw record — it is a low-ceiling year in the specific program's register. Ohio State's dynastic-industrial voice does not calibrate by regular-season wins; it calibrates by the two games (Michigan, the title game). The 2023 team won neither. The chapter's legacy is the 2024 title that followed: the coordinator changes, the Jeremiah Smith recruitment, the transfer-portal additions (Quinshon Judkins, Will Howard) that defined the title team all traced back to the 2023 offseason. The 2023 chapter is the one that exists because the 2024 title came. Without the 2024 answer, 2023 reads as a program-crisis year. With it, 2023 reads as the setup.",
    },

    # ---------- Florida 2025 — Napier's unmaking ----------
    ("florida", 2025): {
        "season_title": "The Crown Still Waits — 4-8 and a Texas Upset",
        "season_thesis": "Florida went 4-8 in Billy Napier's fourth season, missed a bowl for the first time since 2013, and produced two signature results — a top-five upset over Texas and a season-closing win over Florida State — that kept the restoration bet alive without validating it.",
        "defining_moments": [
            {"type": "opener", "register": "triumph",
             "body": "October 4, The Swamp. Florida 29, Texas 21. Top-five Texas, first year in the SEC; the Gators' first top-five home win of the Napier era. DJ Lagway's three touchdown passes. The stadium read like 1996 for a night."},
            {"type": "inflection", "register": "crash",
             "body": "November 8, Kroger Field. Kentucky 38, Florida 7. A 31-point SEC road loss to a mid-tier opponent; the program's largest margin of defeat in conference play in fifteen years. The chapter's structural collapse-moment."},
            {"type": "chapter-close", "register": "turning-point",
             "body": "Week 14. Florida 40, Florida State 21. The in-state knife-fight closed the season with the year's second signature win; the fanbase's emotional ledger ended positive even as the scoreboard ledger ended 4-8."},
        ],
        "pull_quote": {
            "text": "The Swamp doesn't apologize; the Swamp rebuilds.",
            "source": "Ben Hill Griffin fanbase voice",
            "date": "November 29, 2025",
            "is_generated": True,
        },
        "legacy_paragraph": "2025 is the chapter that re-opened the Napier-retention question and left it unresolved. A 4-8 record with a Texas upset and an FSU closing win is the specific record that both contradicts and validates the 'fallen-dynasty-rebuilding' register. The 7-38 Kentucky loss is the chapter's structural data point; the Texas and FSU wins are the two sentences that kept the chapter alive for the offseason conversation. Florida is a program that has held the crown twice — Napier's fourth year did not add a third, did not add a CFP bid, and did not add an SEC title path. It added two signatures the fanbase will quote and a 4-win SEC schedule they will not. The chapter's legacy is the specific combination: the program did not collapse, the regime did not validate, and the crown still waits.",
    },

    # ---------- Michigan 2024 — post-title drift ----------
    ("michigan", 2024): {
        "season_title": "The Year After The Crown — 8-5 and Rebuilding",
        "season_thesis": "Michigan went 8-5 in Sherrone Moore's first year as head coach, lost to Ohio State 13-10 in Columbus after beating them 13-10 in Ann Arbor in 2023, and produced the program's post-title rebuild chapter.",
        "defining_moments": [
            {"type": "structural", "register": "shift",
             "body": "Jim Harbaugh to the Los Angeles Chargers (January 24). J.J. McCarthy to the Minnesota Vikings. Blake Corum to the Los Angeles Rams. The 15-0 title roster's three most visible exits on the same three-week calendar; Sherrone Moore's first roster had to be built around the absences."},
            {"type": "recalibration", "register": "crash",
             "body": "The Game, November 30. Ohio State 13, Michigan 10 in Ann Arbor. The fifth straight The-Game meeting decided by 7 points or fewer; the program's first loss in the rivalry since 2020. A quiet loss — no trophy, no drama, just the structural fact that the 15-0 team had dispersed."},
            {"type": "chapter-close", "register": "triumph",
             "body": "ReliaQuest Bowl, December 31. Michigan 19, Alabama 13. Bryce Underwood committed shortly after; the bowl-win argument closed the Moore-era year-one chapter on a positive note; the program's 2025 roster-build could proceed."},
        ],
        "pull_quote": {
            "text": "The total isn't finished. The total never is.",
            "source": "Ann Arbor voice, post-bowl",
            "date": "December 31, 2024",
            "is_generated": True,
        },
        "legacy_paragraph": "2024 is the post-title chapter Michigan's Maize-and-Blue register had been expecting since 1997. An 8-5 year after a 15-0 title is what the sport's structural gravity produces when a decade's worth of roster decisions converge into a single championship and then the roster disperses. The Moore era's year-one floor is the specific chapter's load-bearing fact; the Alabama bowl win is the optimistic closing sentence. Bryce Underwood's commitment (flipped from LSU; highest-ranked QB commit in Michigan history) is the chapter's structural note outside the scoreboard. The 'proud-institutional' voice did not slip during the year; the program named the transition for what it was, and the fanbase held the line. What Michigan does in 2025 with the incoming five-star class and the offensive-line depth is the test 2024 set up.",
    },

    # ---------- UConn 2024 — Mora Year 3 breakthrough ----------
    ("uconn", 2024): {
        "season_title": "The Nine-Win Year That Kept Writing",
        "season_thesis": "UConn went 9-4, finished independent, beat North Carolina for the program's first Power-Four win in eight years, and won the Fenway Bowl — the pre-2025 breakthrough chapter of the Mora rebuild.",
        "defining_moments": [
            {"type": "opener", "register": "triumph",
             "body": "September 14, Rentschler Field. UConn 45, Merrimack 14. The Mora rebuild's third-year opening game set the tempo for a season the fanbase had been drafting quietly. The schedule was the independent-era schedule; the roster was the first one the Mora era had built from scratch."},
            {"type": "ascension", "register": "triumph",
             "body": "October 26, Kenan Stadium. UConn 31, North Carolina 6. The program's first Power-Four road win since 2016; the signature upset the independent era had been chasing; Joe Fagnano's three-touchdown afternoon."},
            {"type": "chapter-close", "register": "triumph",
             "body": "Fenway Bowl, December 28. UConn 27, North Carolina 14. A bowl win over a Power-Four opponent in the program's first Fenway appearance; the 9-win finish that re-wrote the program's modern ceiling."},
        ],
        "pull_quote": {
            "text": "Both teams are Huskies. And the football team is nine-and-four.",
            "source": "Storrs voice",
            "date": "December 2024",
            "is_generated": True,
        },
        "legacy_paragraph": "2024 is the chapter that re-ordered UConn football's modern identity inside the institution. A 9-win season with a Power-Four road win and a bowl win is not a 2007 Fiesta Bowl season — but it is the first season since that era where the football program's numbers stand independently of the basketball program's achievements. The Mora rebuild's proof-of-concept lives in the specific roster-construction moves of 2023-2024: the Fagnano transfer, the defensive-line recruiting, the Big-East-adjacent scheduling. The 'basketball-school-with-football' register did not require apologizing for this year — it required taking it on the program's own terms. The chapter's legacy is the 2025 season that followed: a second 9-win year with wins over Duke and Boston College, and the argument that UConn football's chapter is now a paragraph, not a sentence.",
    },

    # ================================================================
    # Sprint 5 — Batch D: historical + crisis + bridge seasons
    # ================================================================

    # ---------- UMass 2025 — the 0-12 floor year ----------
    ("massachusetts", 2025): {
        "season_title": "The Independent 0-12 — Rock Bottom And A Decision",
        "season_thesis": "UMass went 0-12 as an FBS independent in 2025, produced the first winless season in the program's FBS era, and made the coaching-staff and conference-membership decisions that set up the 2026 rebuild.",
        "defining_moments": [
            {"type": "structural", "register": "crash",
             "body": "FBS independence, year five. The program's schedule carried no in-conference anchor and no built-in rivalries outside UConn; every week was a programming-variance week. The roster's injury cascade in September closed any path to bowl-eligible."},
            {"type": "inflection", "register": "crash",
             "body": "November 22, at McGuirk. UMass 6, UConn 38. The one rivalry game on the schedule went the way the ledger had been going for a decade. The loss is not the specific chapter; the 0-12 is."},
            {"type": "chapter-close", "register": "turning-point",
             "body": "November 29. Head coach change announced; conference-realignment conversations with the MAC resumed in December. The 0-12 did not end the program — it forced the institutional decisions that the previous four years had deferred."},
        ],
        "pull_quote": {
            "text": "We are playing for the version of ourselves that gets invited to the conversation.",
            "source": "Amherst voice",
            "date": "December 2025",
            "is_generated": True,
        },
        "legacy_paragraph": "2025 is the chapter that forced the program's institutional decision. A 0-12 independent season is not a chapter the fanbase romanticizes; the scrappy-proud register does not pretend a winless year is a badge. What the register does is name 2025 as the year the program's FBS-independent experiment's structural costs became undeniable — the scheduling, the recruiting footprint, the NIL ceiling, the travel burden. The chapter's legacy is not the record. It is the MAC-or-CAA conversation that opened in the offseason and the head-coach decision that accompanied it. 2025's job inside the program's arc is the same job the 2014 3-9 year did: name the floor, force the pivot. The pivot itself is the 2026 chapter's to write.",
    },

    # ---------- UMass 2023 — mid-rebuild ----------
    ("massachusetts", 2023): {
        "season_title": "The 3-9 Rebuild — One Signature, No Floor",
        "season_thesis": "UMass went 3-9 in its independent era, produced one signature win over a Power-Four opponent, and continued the program's year-over-year search for a schedule identity that independence had not yet produced.",
        "defining_moments": [
            {"type": "ascension", "register": "triumph",
             "body": "October 7. UMass 34, New Mexico State 28. A signature win inside the independent scheduling model; the kind of result the program needed to keep the 6-win-ceiling argument alive."},
            {"type": "structural", "register": "shift",
             "body": "Don Brown (second-stint head coach) navigated a roster with minimal Power-Four talent and a schedule the Big Ten and ACC opponents used as tune-ups. The 3-9 was, in the scrappy-proud register, not a collapse — it was an independent-era floor consistent with the program's modern ceiling."},
            {"type": "chapter-close", "register": "turning-point",
             "body": "November 25. 3-9 finished. Recruiting and portal moves accelerated in December; the program's coaching-staff discussions stayed internal. The chapter's closing note was a quiet offseason, not a reactive one."},
        ],
        "pull_quote": {
            "text": "Scrappy-proud. Not apologetic.",
            "source": "McGuirk fanbase voice",
            "date": "December 2023",
            "is_generated": True,
        },
        "legacy_paragraph": "2023 is the middle chapter of UMass football's independent experiment. A 3-9 year in a conference-less schedule is neither program-crisis nor program-progress; it is a continuation year, and the fanbase registered it as such. The scrappy-proud voice does not require a signature win to hold — but the New Mexico State result gave the chapter a specific data point to quote. The structural question the chapter leaves unasked is the one 2025 would eventually force: whether independence is the right structural choice for a program whose recruiting footprint is the Northeast and whose conference memory is the MAC. 2023 did not answer that question. It registered it, and the program kept writing.",
    },

    # ---------- UConn 2023 — Mora Y2 with Myrtle Beach Bowl ----------
    ("uconn", 2023): {
        "season_title": "The Myrtle Beach Bowl — First Bowl Win Since 2009",
        "season_thesis": "UConn went 3-9 in the regular season but made and won the Myrtle Beach Bowl — the program's first post-season win since 2009 and the signature achievement of the Mora rebuild's second year.",
        "defining_moments": [
            {"type": "structural", "register": "shift",
             "body": "The regular season produced three wins inside a brutal independent schedule; every bowl-eligibility conversation had seemed foreclosed by October. A late-season surge plus an at-large invitation created the bowl window the program had not seen in eight years."},
            {"type": "ascension", "register": "triumph",
             "body": "Myrtle Beach Bowl, December 18. UConn 23, Marshall 14. Joe Fagnano's 196 passing yards; the defense's red-zone stand in the fourth quarter; the first bowl win since the 2009 St. Petersburg Bowl. The Mora rebuild's first tangible trophy."},
            {"type": "chapter-close", "register": "turning-point",
             "body": "December 20. Recruiting calls took the Mora-era tone publicly for the first time: UConn can be 2023-plus-a-bowl-win, not 2023-minus-a-bowl-bid. The chapter's institutional register shifted inside one fourth quarter."},
        ],
        "pull_quote": {
            "text": "Both teams are Huskies. The football team just went to Myrtle Beach and came home with something.",
            "source": "Hartford Courant voice",
            "date": "December 2023",
            "is_generated": True,
        },
        "legacy_paragraph": "2023 is the chapter the Mora rebuild's second year needed to produce. A 3-9 regular season with a bowl-win close is not a high-ceiling chapter; it is the specific chapter a rebuilding independent program requires to stay recruiting-competitive across a coaching cycle. The Myrtle Beach Bowl trophy is the chapter's load-bearing artifact; the absence of it would have reset the program's 2024 recruiting calibration. The basketball-school-with-football voice held through the year — the fanbase knew the year for what it was, did not pretend to a ceiling the roster could not deliver, and celebrated the bowl win without inflating it into a paragraph it wasn't. 2023 made 2024 possible.",
    },

    # ---------- Florida 2023 — Napier Y2 crash ----------
    ("florida", 2023): {
        "season_title": "Napier Year Two — 5-7, Mertz Year, Missed Bowl",
        "season_thesis": "Florida went 5-7 in Billy Napier's second season, missed a bowl game for the first time since 2017, and entered the 2024 season with open questions about the Napier restoration's timeline.",
        "defining_moments": [
            {"type": "opener", "register": "shift",
             "body": "Graham Mertz arrived via Wisconsin transfer; the offense ran 28 points per game — roughly the program's Meyer-era baseline. The defense surrendered 35. The ceiling-floor gap between offense and defense was the chapter's architectural fact."},
            {"type": "inflection", "register": "crash",
             "body": "November 11, Baton Rouge. LSU 52, Florida 35. A six-touchdown SEC road loss; the kind of result that shapes next-year bowl projections. The Swamp's emotional ledger took damage; the mascot-voice 'doesn't apologize, rebuilds' register was tested."},
            {"type": "chapter-close", "register": "turning-point",
             "body": "November 25. Florida State 24, Florida 15. The closing in-state loss; a fifth straight SEC East(-style) loss; a Napier-era decision moment that did not arrive — the athletic department retained him. The chapter's legacy is the retention, not the scoreboard."},
        ],
        "pull_quote": {
            "text": "The Swamp doesn't apologize; the Swamp rebuilds. The calendar is the question.",
            "source": "Ben Hill Griffin voice",
            "date": "December 2023",
            "is_generated": True,
        },
        "legacy_paragraph": "2023 is the chapter that tested whether the Napier bet would survive its floor year. A 5-7 season with a missed bowl and an in-state-rivalry loss is the specific trio of results the fallen-dynasty-rebuilding register struggles to absorb inside one year. The retention decision that followed the year is the chapter's institutional load-bearing fact: the athletic department chose to extend the runway, pointing at the Lagway recruiting class and the infrastructure pipeline rather than the scoreboard. The chapter's legacy was then contested by the 2024 8-5 Lagway year (which validated the call) and re-contested by the 2025 4-8 crash (which reopened it). 2023's role inside the arc is the year the program chose to keep rebuilding without asking for the chapter's record to justify the choice.",
    },

    # ---------- Georgia 2023 — post-title reset ----------
    ("georgia", 2023): {
        "season_title": "The Alabama Loss — Back-to-Back Becomes Two",
        "season_thesis": "Georgia went 13-1, lost the SEC Championship to Alabama 27-24, missed the CFP at #6, and closed the back-to-back-titles era with the one loss that ended it.",
        "defining_moments": [
            {"type": "continuity", "register": "triumph",
             "body": "Twelve wins in the regular season. Carson Beck's first year as starter ran 3,800 yards and 24 touchdowns; the Georgia defense finished top-five nationally. The roster's back-to-back-title pedigree carried through the SEC schedule — until the last game of it."},
            {"type": "inflection", "register": "crash",
             "body": "SEC Championship, December 2. Alabama 27, Georgia 24. Jalen Milroe's final-minute touchdown drive; the Alabama defense's fourth-down stop. The first regular-season-plus-SEC-title-game loss of the Kirby Smart era's title-run; the end of Georgia's 29-game win streak."},
            {"type": "chapter-close", "register": "turning-point",
             "body": "Orange Bowl, December 30. Georgia 63, Florida State 3. A dismantling of an FSU team the CFP had excluded in favor of Alabama; the largest margin in a New Year's Six bowl since 2005. The chapter closed with a rout, not a CFP bid."},
        ],
        "pull_quote": {
            "text": "The hunt lives inside the loss, too.",
            "source": "Athens voice",
            "date": "December 2023",
            "is_generated": True,
        },
        "legacy_paragraph": "2023 is the chapter that closed the back-to-back era without closing the dynastic register. Two national titles in two years was unprecedented; a 13-1 third year with one loss to Alabama was not collapse — it was SEC gravity. The Orange Bowl rout of Florida State is the chapter's closing exclamation, a response to the committee's decision to exclude the ACC champions. The dominant-hungry voice did not slip; the program named the Alabama loss for what it was and did not romanticize the 63-3 bowl into a CFP-substitute. 2023 is the bridge between the two-title run and the 2024 SEC title — the specific chapter where Georgia was the sport's dominant program and still did not win it all. The register survived. The hunt continued.",
    },

    # ---------- USC 2021 — pre-Riley floor ----------
    ("usc", 2021): {
        "season_title": "The Pre-Riley Year — 4-8 and an Open Door",
        "season_thesis": "USC went 4-8 in Clay Helton's final partial season plus interim, missed a bowl for the second consecutive year, and produced the circumstances that made the Lincoln Riley hire possible.",
        "defining_moments": [
            {"type": "outage", "register": "crash",
             "body": "September 13. Clay Helton fired after the Stanford loss. Donte Williams elevated to interim head coach. The 1-1 start unraveled into a 4-7 finish; the program's identity-crisis year was underway before the second bye."},
            {"type": "inflection", "register": "crash",
             "body": "November 27, Coliseum. Cal 24, USC 14. A home loss to the rivalry opponent from the north; the scoreboard and the attendance both registered the program's lowest ebb of the modern era. The Trojan Coliseum did not fill."},
            {"type": "chapter-close", "register": "turning-point",
             "body": "November 28. Lincoln Riley hired from Oklahoma in a move that shocked the sport. The chapter's closing line was not on the scoreboard; it was in the press release. The 4-8 became the setup, not the record."},
        ],
        "pull_quote": {
            "text": "Fight On. The night is back. It was never going to come quietly.",
            "source": "Heritage Hall voice",
            "date": "December 2021",
            "is_generated": True,
        },
        "legacy_paragraph": "2021 is the USC chapter that made the Riley era possible. A 4-8 year with a mid-season coaching change and a program-identity crisis is the specific floor a hollywood-dynastic register struggles to absorb in real time but eventually quotes as the inflection point. The Riley hire was made from exactly the 4-8 context; the Oklahoma departure would have been unthinkable from a USC-at-ceiling year. The chapter's legacy is the structural lesson the register encodes: USC used to own Saturday night, and the program's rebuilding chapters have to be named before they can be written. The 2022 season (11-3, Caleb Williams Heisman) is 2021's answer; the 2024 Big-Ten-debut's 7-6 is the counter-argument still being tested.",
    },

    # ---------- Tennessee 2020 — COVID Pruitt year ----------
    ("tennessee", 2020): {
        "season_title": "The Wilderness's Last Year",
        "season_thesis": "Tennessee went 3-7 in the COVID-truncated SEC-only season, fired Jeremy Pruitt for cause on January 18, 2021, and closed the Program Wilderness chapter that had opened in 2009.",
        "defining_moments": [
            {"type": "structural", "register": "shift",
             "body": "The SEC-only ten-game schedule removed Tennessee's non-conference wins. Every game was a capital-SEC game; the program's depth could not match the slate. 3-7 was not a floor-hitting year in the scoreboard sense; it was a wilderness-resident year in the program-identity sense."},
            {"type": "outage", "register": "crash",
             "body": "January 18, 2021. Jeremy Pruitt fired for cause following an NCAA investigation that disclosed recruiting violations across multiple years. The firing was a structural shift — Tennessee's third coaching-firing-with-cause of the wilderness era. The athletic-department decision to not pay Pruitt's buyout became a national cause."},
            {"type": "chapter-close", "register": "turning-point",
             "body": "January 27, 2021. Josh Heupel hired from UCF. The restoration bet began with a hire that was not the marquee name the fanbase had been asking for — and became, four years later, the restoration chapter the program's identity had been waiting for."},
        ],
        "pull_quote": {
            "text": "Rocky Top still plays. The work is still the work.",
            "source": "Knoxville voice",
            "date": "January 2021",
            "is_generated": True,
        },
        "legacy_paragraph": "2020 is the chapter that closed the wilderness. A 3-7 SEC-only season was the record; the Pruitt-fired-for-cause aftermath was the structural event. The program's institutional memory placed the chapter alongside the 2009 Kiffin-to-USC year and the 2017 Butch-Jones-firing year as the three post-Fulmer crisis chapters — and 2020 was the one that produced the Heupel hire. The restoration-era-orange register began, structurally, on January 27, 2021. Without the 2020 crisis, there is no 2021 Heupel hire; without the Heupel hire, no 2022 Hooker year, no 2024 CFP. The chapter's legacy is the specific way institutional failure forced the structural pivot that produced the restoration. The fanbase does not romanticize 2020. It does not pretend the Pruitt era was not what it was. It registers the year as the last sentence before the sequel started.",
    },

    # ---------- Ohio State 2016 — CFP semifinal ----------
    ("ohio-state", 2016): {
        "season_title": "The Shutout Semifinal — 31-0 In The Sugar Bowl",
        "season_thesis": "Ohio State went 11-2, reached the CFP semifinal, and lost to Clemson 31-0 — the program's most decisive CFP loss and the Meyer era's single game the fanbase does not replay.",
        "defining_moments": [
            {"type": "identity", "register": "triumph",
             "body": "J.T. Barrett's full year; Curtis Samuel at H-back; a defense that finished top-five nationally against the run. An 11-1 regular season landed Ohio State the CFP's #3 seed — the program's second CFP appearance in three years."},
            {"type": "near-miss", "register": "crash",
             "body": "CFP Semifinal, Fiesta Bowl, December 31. Clemson 31, Ohio State 0. Deshaun Watson threw for 259 yards; the Buckeyes did not cross midfield in the first half; Clemson's defense produced four sacks and two interceptions. The only CFP shutout of the format's history to that point."},
            {"type": "chapter-close", "register": "turning-point",
             "body": "January 9, 2017. Meyer's post-season assessment named the offensive line and the red-zone identity as the specific recruiting-and-scheme targets for 2017. The chapter's structural note was the Tom Herman exit (to Texas, already announced in November), which reshaped the coordinator staff heading into the next year."},
        ],
        "pull_quote": {
            "text": "Shutout. That's all the film has to say.",
            "source": "Columbus voice, quiet",
            "date": "January 1, 2017",
            "is_generated": True,
        },
        "legacy_paragraph": "2016 is the chapter the Meyer era produced the program's cleanest CFP on-ramp and its cleanest CFP bow-out on the same calendar. The 31-0 is the most visible Ohio State scoreboard shutout of the modern era, and the chapter's structural response was a coordinator-staff overhaul and a 2017 Hurricane-season offensive rebuild. The 2014 title had been the program's CFP-era peak; the 2016 semifinal was the year the ceiling flattened. The Day era's eventual 2024 title traces, in the recruiting pipeline, back to the 2016 roster's defensive identity — but the scoreboard traces to the 2014 team. 2016's specific role in the dynastic-industrial register is as the year the Meyer era's offensive scheme reached its ceiling and did not breakthrough it.",
    },

    # ---------- Oregon 2016 — first losing since 1991 ----------
    ("oregon", 2016): {
        "season_title": "The Floor — 4-8 And Helfrich Out",
        "season_thesis": "Oregon went 4-8, produced the program's first losing season since 1991, and fired Mark Helfrich after four years — the chapter that separated the Kelly-Helfrich era from the Willie Taggart (then Cristobal, then Lanning) reset.",
        "defining_moments": [
            {"type": "structural", "register": "crash",
             "body": "The defensive scheme broke. Oregon surrendered 41 points per game — the program's worst defensive performance of the modern era. The offensive identity that had carried the Kelly-Helfrich years could not outrun a defense at that altitude."},
            {"type": "inflection", "register": "crash",
             "body": "Civil War, November 26. Oregon State 34, Oregon 24. The rivalry loss that kept the Ducks from a bowl; the program's third straight November loss; the institutional conclusion that Helfrich's retention was no longer tenable."},
            {"type": "outage", "register": "turning-point",
             "body": "November 29. Helfrich fired. Willie Taggart hired from South Florida. The 'fashionable-fast' register had not been applied to a losing season in the Ducks' modern era, and the program did not know how to calibrate the voice inside the firing."},
        ],
        "pull_quote": {
            "text": "Fast isn't the question. Serious is.",
            "source": "Eugene editorial voice",
            "date": "December 2016",
            "is_generated": True,
        },
        "legacy_paragraph": "2016 is the chapter the Helfrich era could not survive. A 4-8 season with a rivalry loss, a defensive collapse, and the first losing-year calibration-question the 'fashionable-fast' register had ever had to absorb. The Willie Taggart hire restarted the scheme identity; the Mario Cristobal promotion (after Taggart's one-year exit to FSU) re-grounded the defensive identity; the Dan Lanning hire in 2022 took both arguments into the Big Ten. None of those decisions happen without 2016. The chapter's legacy inside the program is the specific structural lesson: fashionable-fast requires a defensive floor the 2016 team did not produce, and every Oregon regime since has been graded against whether it could provide one.",
    },

    # ---------- Washington 2016 — Petersen Pac-12 title + CFP ----------
    ("washington", 2016): {
        "season_title": "Petersen's Pac-12 Title — First CFP",
        "season_thesis": "Washington went 12-2, won the Pac-12, reached the CFP semifinal for the first time in program history, and lost to Alabama 24-7 in the Peach Bowl — the Petersen era's peak chapter.",
        "defining_moments": [
            {"type": "identity", "register": "triumph",
             "body": "Jake Browning's second year produced 3,430 passing yards and 43 touchdowns; John Ross set the receiver-class benchmark for the year; the defense finished top-ten nationally against the pass. An 11-1 regular season was the program's best since 2000."},
            {"type": "coronation", "register": "triumph",
             "body": "Pac-12 Championship, December 2. Washington 41, Colorado 10. The program's first conference title since 2000; the Pac-12 North's first Rose Bowl-caliber champion in five years. The Petersen era's peak result of the decade."},
            {"type": "near-miss", "register": "crash",
             "body": "CFP Semifinal, Peach Bowl, December 31. Alabama 24, Washington 7. The Saban defense held Browning to 150 passing yards; Bo Scarbrough ran for 180; the Huskies' first CFP appearance ended decisively. The chapter's structural closing sentence was not in the margin — it was in the recognition that Washington had reached the ceiling the 1991 Don James team once owned."},
        ],
        "pull_quote": {
            "text": "Purple Reigns. The dock carried us to the bracket.",
            "source": "Husky Stadium voice",
            "date": "December 2016",
            "is_generated": True,
        },
        "legacy_paragraph": "2016 is the chapter that proved Don James's shadow could be approached. A 12-win season with a Pac-12 title and a CFP semifinal is the specific altitude Washington had not reached since James stepped away in 1992. The Peach Bowl loss to Alabama reset the ceiling-question — the program had arrived in the CFP, and the margin said the bracket's final-four had not yet. The Petersen era's legacy lives inside this year's scheduling path and the program's 2023 DeBoer-era answer that extended it. The 'edge-case-contender' register was not yet the profile's word for Washington in 2016; the 2016 chapter is one of the structural reasons it became the register by 2023. The dock game still carries the fanbase; 2016 is the chapter where the dock reached the bracket.",
    },

    # ================================================================
    # Phase 3 bonus: Georgia 2017/2018 — post-CFBD-backfill flagships
    # ================================================================

    # ---------- Georgia 2017 — OT title-game heartbreak ----------
    ("georgia", 2017): {
        "season_title": "Second-and-26, From The Other Sideline",
        "season_thesis": "Georgia went 13-2, won the SEC, reached the national championship game, and lost to Alabama 26-23 in overtime on a Tua Tagovailoa pass to DeVonta Smith — the chapter that set up the 2021 title run.",
        "defining_moments": [
            {"type": "ascension", "register": "triumph",
             "body": "SEC Championship, December 2. Georgia 28, Auburn 7. Nick Chubb and Sony Michel split 200 rushing yards; the Kirby Smart-era defense held Auburn's offense to a single touchdown. The Bulldogs' first SEC title since 2005."},
            {"type": "semifinal", "register": "triumph",
             "body": "Rose Bowl, January 1, 2018. Georgia 54, Oklahoma 48 (2OT). Sony Michel's 27-yard touchdown run ended the double-overtime classic; Baker Mayfield and Jake Fromm split 800 combined passing yards. The CFP semifinal that announced the Kirby Smart era's arrival."},
            {"type": "near-miss", "register": "crash",
             "body": "National Championship, January 8, 2018. Alabama 26, Georgia 23 (OT). Jake Fromm started; Georgia led 13-0 at halftime; Saban benched Jalen Hurts for Tagovailoa; Smith caught the overtime touchdown on second-and-26. One play, from the other sideline."},
        ],
        "pull_quote": {
            "text": "Second-and-26, and we were on the other side of it.",
            "source": "Kirby Smart, post-game",
            "date": "January 8, 2018",
            "is_generated": True,
        },
        "legacy_paragraph": "2017 is the chapter the Kirby Smart era was built on. A 13-2 season with an SEC title and a CFP title-game appearance — in Smart's second year as head coach. The Alabama overtime loss is the chapter's emotional centerpiece and the specific result the program spent four years answering; the 2021 title over Alabama, also in a championship game, is the retrospective closing sentence. Nick Chubb and Sony Michel's backfield pairing became the recruiting-pipeline argument for the program through 2020; the defensive identity built in this season became the template the 2021 and 2022 title teams executed on. The dominant-hungry register has a pre-2021 pre-history, and 2017 is its load-bearing chapter.",
    },

    # ---------- Georgia 2018 — the Jake Fromm year ----------
    ("georgia", 2018): {
        "season_title": "The SEC-Title-Game Loss That Stayed",
        "season_thesis": "Georgia went 11-3, lost the SEC Championship to Alabama 35-28, fell out of the CFP at #5, and went to the Sugar Bowl against Texas — the Kirby Smart era's second year of 'one game from the semifinal' cadence.",
        "defining_moments": [
            {"type": "identity", "register": "triumph",
             "body": "Jake Fromm's sophomore year produced 2,700 passing yards and 30 touchdowns; D'Andre Swift, Elijah Holyfield, and the offensive line carried the SEC's #1-ranked rushing attack. The regular season finished 11-1 with a loss to LSU the only blemish."},
            {"type": "inflection", "register": "crash",
             "body": "SEC Championship, December 1. Alabama 35, Georgia 28. Jalen Hurts's fourth-quarter comeback drive replaced Tagovailoa (injured at halftime); the specific sequence that placed Alabama ahead for good came on a fourth-and-long conversion. Georgia's second straight SEC Championship-Game loss to Alabama."},
            {"type": "chapter-close", "register": "crash",
             "body": "Sugar Bowl, January 1, 2019. Texas 28, Georgia 21. Sam Ehlinger outplayed Fromm; the Longhorns' late scoring drive sealed the Bulldogs' second consecutive season ending with a loss to a program they had been favored over. 'Texas is back' became a bit later; the Sugar Bowl was the specific game that introduced it."},
        ],
        "pull_quote": {
            "text": "The hunt didn't eat in 2018. The hunt stayed hungry.",
            "source": "Athens editorial voice",
            "date": "January 2019",
            "is_generated": True,
        },
        "legacy_paragraph": "2018 is the Kirby Smart chapter where the hunt did not reach the kill. A 11-3 season with an SEC-title-game loss and a Sugar Bowl loss is a high-ceiling year that did not close with a crown — and the fanbase registered the specific kind of 'close enough to matter, not close enough to win' that would shape the program's internal conversation for three years. The chapter's legacy inside the arc is how it feeds forward: the 2019 semifinal loss to LSU, the 2020 semifinal loss to Alabama, and the 2021 title. Four years of almost, one year of crown, two years of back-to-back. Without 2018's specific loss, the 2021 title game does not carry the same weight; the dominant-hungry register required the accumulation.",
    },
}
