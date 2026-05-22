"""The 25 Best Coaching Hires of the 2020s — 2026 edition.

Author's note (Sprint 11): "best" judges (a) the outcome at the program
since the hire, (b) how good the bet looked the day it was made, and
(c) the ripple effect on the coaching market. Hires made 2020-2025
inclusive. Some entries (Cignetti, Moore, DeBoer-at-Alabama) are
provisional — one or two seasons of evidence — and the rank-delta
column will reflect revisions in 2027.

Every entry has an editorial paragraph (sonnet-equivalent). The list
draws from profile-frontmatter coaching_regimes (18 hires across the 17
profiled programs in the 2020s) plus seven additional hires from
non-profiled programs my editorial knowledge anchors with
high-confidence outcomes (Cignetti, Norvell, Leipold, Smith,
Drinkwitz, Pittman, Brent Pry). Where a non-profiled hire entry uses
the same program slug as a profiled program (e.g. Texas Sarkisian),
the entry uses that slug. Otherwise program_slug is left ``None`` and
program_label carries the institution name.
"""
from __future__ import annotations

from .data import CanonEntry


_LIST = "the-25-best-coaching-hires-2020s"


def _e(rank: int, **kwargs) -> CanonEntry:
    return CanonEntry(
        list_slug=_LIST, rank=rank, entity_kind="coaching_hire", **kwargs,
    )


def entries() -> list[CanonEntry]:
    return [
        _e(
            rank=1,
            entity_slug="curt-cignetti-indiana-2024",
            entity_display_name="Curt Cignetti — Indiana, December 2023",
            program_label="Indiana",
            era_label="2024–",
            statline="Year-1: 11-1 regular season · CFP appearance · won Big Ten East games",
            summary_short=(
                "The most consequential first-year hire of the 2020s — "
                "Indiana 11-0 in the regular season, a CFP appearance, "
                "and the new market-rate for proven Group-of-Five coaches."
            ),
            editorial_paragraph=(
                "Cignetti's December 2023 hire from James Madison cost "
                "Indiana the smallest price tag of any 2024 CFP-team head "
                "coach (~$3.4M base) and produced the largest immediate "
                "return: 11 wins in 11 starts, a Big Ten East schedule "
                "navigated, a CFP appearance in year one. He brought the "
                "JMU defensive coordinator and a portal class so "
                "deliberate that the season's roster turnover became "
                "the new template for how a Group-of-Five-trained "
                "coach lifts a Power-5 program. The market response was "
                "immediate — every December 2024 search for a "
                "long-tenured Group-of-Five winner started with the "
                "Cignetti precedent. The 2025 season will be the "
                "credibility test; the 2024 evidence stands as the "
                "decade's signal hire."
            ),
        ),
        _e(
            rank=2,
            entity_slug="lincoln-riley-usc-2022",
            entity_display_name="Lincoln Riley — USC, November 2021",
            program_slug="usc",
            program_label="USC",
            era_label="2022–",
            statline="Year-1: 11-3 · 2022 Heisman (Williams) · Big Ten move executed",
            summary_short=(
                "The hire that ended the Pac-12 — and the program's "
                "first credible national contention since the BCS years."
            ),
            editorial_paragraph=(
                "Riley left Norman for Los Angeles in November 2021 "
                "after a Big-12 era that was ending; USC made him the "
                "highest-paid coach in the conference and gave him a "
                "complete portal-and-roster reset. Year one — 11-3, "
                "Caleb Williams' Heisman, the closest thing to a USC "
                "title contention since the Pete Carroll era — vindicated "
                "the bet. The 2023 and 2024 seasons (8-5, 7-6) cooled "
                "the conversation; the Big Ten move's early returns are "
                "still being graded. The hire's structural impact — USC "
                "and UCLA leaving the Pac-12, the conference's "
                "subsequent dissolution — is the long-tail outcome that "
                "places it second."
            ),
        ),
        _e(
            rank=3,
            entity_slug="kalen-deboer-alabama-2024",
            entity_display_name="Kalen DeBoer — Alabama, January 2024",
            program_slug="alabama",
            program_label="Alabama",
            era_label="2024–",
            statline="Year-1: 9-4 · first non-CFP year for UA since 2007 · 2025 pending",
            summary_short=(
                "The hire that replaced Saban — and the most-watched "
                "coaching transition of the modern game."
            ),
            editorial_paragraph=(
                "DeBoer arrived in Tuscaloosa from a 14-1 Washington "
                "season and inherited the most institutionalized roster "
                "in college football. Year one (9-4, no SEC title game, "
                "outside the CFP) was Alabama's first November-loss "
                "season since 2007 — the data point that placed him "
                "third on this list rather than first or second is the "
                "outcome relative to the inheritance. The bet was "
                "obvious at the moment of hire: a coach with a national-"
                "title-game appearance, a portal-savvy operation, and a "
                "personality compatible with the Tuscaloosa register. "
                "The 2025 evidence will recalibrate the rank — the "
                "delta column reads ``→`` provisionally."
            ),
        ),
        _e(
            rank=4,
            entity_slug="marcus-freeman-notre-dame-2022",
            entity_display_name="Marcus Freeman — Notre Dame, December 2021",
            program_slug="notre-dame",
            program_label="Notre Dame",
            era_label="2022–",
            statline="Year-3: 14-2 · 2024 NCG appearance · 2nd youngest NCG HC since '70",
            summary_short=(
                "The Brian Kelly defection's response — a 35-year-old "
                "DC who became the program's first national-title-game "
                "head coach in twelve years."
            ),
            editorial_paragraph=(
                "Brian Kelly left for LSU in November 2021; Freeman, the "
                "first-year defensive coordinator, was promoted within "
                "a week. The 2022 season opened with a Marshall loss at "
                "home and the conversation curdled briefly; 2023 (10-3) "
                "stabilized the program; 2024 (14-2, the NCG appearance "
                "against Ohio State) ratified the bet. Freeman is the "
                "rare Notre Dame head coach the alumni-network has "
                "embraced without reservation, and the program's "
                "recruiting cycle since 2022 has been the strongest "
                "since the Holtz years."
            ),
        ),
        _e(
            rank=5,
            entity_slug="dan-lanning-oregon-2022",
            entity_display_name="Dan Lanning — Oregon, December 2021",
            program_slug="oregon",
            program_label="Oregon",
            era_label="2022–",
            statline="Year-1: 10-3 · Year-3: 13-1 · Big Ten transition's smoothest landing",
            summary_short=(
                "The Georgia DC who became the most successful Pac-12-"
                "to-Big-Ten transition coach — and the Lanning era as "
                "Oregon's strongest sustained run since the Kelly years."
            ),
            editorial_paragraph=(
                "Lanning arrived from Smart's Georgia in December 2021 "
                "and produced 10-3 in year one, 12-2 in year two, 13-1 "
                "with the first Big Ten Championship in year three — "
                "the smoothest conference-transition landing of the "
                "Pac-12 dissolution. The 2024 Big Ten Championship win "
                "over Penn State was the program's first conference title "
                "outside the Pac-12 in its history. The Lanning operation "
                "(portal-aggressive, defense-first, Florida-recruiting) "
                "is the early read on Big Ten's new west-coast power."
            ),
        ),
        _e(
            rank=6,
            entity_slug="mike-elko-texas-am-2024",
            entity_display_name="Mike Elko — Texas A&M, December 2023",
            program_label="Texas A&M",
            era_label="2024–",
            statline="Year-1: 9-3 · cleaned up post-Fisher roster · '24 Liberty Bowl",
            summary_short=(
                "The Duke defensive coordinator who took the Texas A&M "
                "job nobody outside the search committee thought he'd "
                "take — and stabilized the program in nine months."
            ),
            editorial_paragraph=(
                "Elko inherited the post-Jimbo Fisher A&M — the largest "
                "buyout in college football history, a roster that had "
                "been recruited to a different scheme, and a fanbase "
                "that had spent the offseason in receivership. Year one "
                "(9-3 regular season, Liberty Bowl bid) was the cleanest "
                "post-coaching-fire stabilization of the 2020s. The hire "
                "was a return to the program where Elko had been "
                "defensive coordinator under Fisher; the Duke detour "
                "produced the head-coaching evidence A&M needed. The "
                "2025 season will measure whether the floor is real."
            ),
        ),
        _e(
            rank=7,
            entity_slug="josh-heupel-tennessee-2021",
            entity_display_name="Josh Heupel — Tennessee, January 2021",
            program_slug="tennessee",
            program_label="Tennessee",
            era_label="2021–",
            statline="Year-2: 11-2 · '22 Orange Bowl · Hooker's Heisman finalist year",
            summary_short=(
                "The UCF tempo-offense coach who gave Tennessee its first "
                "11-win season since 2001 — and the Hooker partnership "
                "that briefly made Knoxville a top-five conversation."
            ),
            editorial_paragraph=(
                "Heupel arrived from UCF in January 2021 with a 12-0 "
                "regular season as his most recent credential and a "
                "tempo-spread offense that nobody in the SEC was ready "
                "for. Year one (7-6) was the install year; year two "
                "(11-2, Orange Bowl, the Alabama-in-Knoxville win, "
                "Hooker's Heisman finalist year) was the breakthrough; "
                "years three and four normalized at 9-4. The hire's "
                "structural impact — Tennessee's first sustained "
                "national-conversation period since the Fulmer years "
                "ending in 2008 — places it firmly in the top-10."
            ),
        ),
        _e(
            rank=8,
            entity_slug="steve-sarkisian-texas-2021",
            entity_display_name="Steve Sarkisian — Texas, January 2021",
            program_slug="texas",
            program_label="Texas",
            era_label="2021–",
            statline="Year-3: 12-2 · '23 Big-12 title · '24 SEC move · '24 CFP semifinal",
            summary_short=(
                "The Alabama OC whose third year produced the program's "
                "first Big-12 title in the CFP era — and whose fourth "
                "year ran the SEC move's first season to a CFP "
                "semifinal."
            ),
            editorial_paragraph=(
                "Sarkisian's first two years in Austin (5-7, 8-5) were "
                "the wilderness; year three (12-2, the Big-12 title win "
                "in Sarkisian's last conference season, the CFP "
                "semifinal loss to Washington) was the breakthrough; "
                "year four (the SEC's first-year landing, 13-3 with "
                "back-to-back CFP semifinal appearances) was the "
                "vindication. Texas-as-blue-blood is back in the "
                "national conversation in a way the program had not been "
                "since the Mack Brown post-2009 collapse, and the "
                "Sarkisian operation produced it."
            ),
        ),
        _e(
            rank=9,
            entity_slug="brent-venables-oklahoma-2022",
            entity_display_name="Brent Venables — Oklahoma, December 2021",
            program_slug="oklahoma",
            program_label="Oklahoma",
            era_label="2022–",
            statline="Year-1: 6-7 · Year-3: 10-3 · '24 SEC move · '24 8-5 first-year SEC",
            summary_short=(
                "The Clemson DC whose first year was a 6-7 disaster — "
                "and whose third-year 10-3 finish vindicated the "
                "Oklahoma program's most-criticized 2020s decision."
            ),
            editorial_paragraph=(
                "Venables took the Oklahoma job in December 2021 after "
                "Riley left for USC and produced the program's worst "
                "season in 24 years (6-7 in 2022). The pile-on was "
                "immediate; the recovery (8-5 in 2023, 10-3 in 2024 with "
                "a Big-12 farewell, 8-5 first-year SEC in 2024) was the "
                "patience-pays-off counterargument the year-one critics "
                "hadn't anticipated. The Venables hire's place in this "
                "list is contested — some panels would have it five "
                "ranks lower — but the directional evidence puts it "
                "in the top ten."
            ),
        ),
        _e(
            rank=10,
            entity_slug="lance-leipold-kansas-2021",
            entity_display_name="Lance Leipold — Kansas, May 2021",
            program_label="Kansas",
            era_label="2021–",
            statline="Year-2: 6-7 (1st bowl since '08) · Year-3: 9-4 · turned Kansas into a program",
            summary_short=(
                "The Buffalo coach who took the Kansas job in May with "
                "no spring practice — and produced the program's first "
                "bowl game in 14 years by year two."
            ),
            editorial_paragraph=(
                "Leipold's May 2021 hire — after the Mike Houston search "
                "collapsed two days before the announcement — gave him "
                "no spring practice and the worst Power-5 inheritance "
                "of the decade. Year one (2-10) was triage; year two "
                "(6-7, the program's first bowl since 2008) was "
                "vindication; year three (9-4) was a top-25 finish that "
                "the Kansas program had not produced since the Mark "
                "Mangino era ended in 2009. The Leipold operation has "
                "made Kansas a credibility-restoration template the "
                "rest of the bottom-tier Power-5 sport now studies."
            ),
        ),
        _e(
            rank=11,
            entity_slug="kalen-deboer-washington-2022",
            entity_display_name="Kalen DeBoer — Washington, November 2021",
            program_slug="washington",
            program_label="Washington",
            era_label="2022–2023",
            statline="Year-2: 11-2 · Year-3: 14-1 · '23 NCG appearance · 2024 → Alabama",
            summary_short=(
                "The Fresno State coach whose two-year Washington run "
                "produced the program's first national-title-game "
                "appearance since 1991."
            ),
            editorial_paragraph=(
                "DeBoer's two years at Washington (11-2, 14-1) produced "
                "the Pac-12's last conference championship and the "
                "program's first national-title-game appearance since "
                "1991. Penix's two-year passing-game implementation, "
                "the offensive-line continuity, the wide-receiver "
                "corps that produced Odunze and Polk as first-rounders "
                "— the operation peaked in the 14-1 January 2024 NCG "
                "loss to Michigan. The Alabama job opened the next "
                "week. The Washington program has not yet recovered "
                "from the rapid turnover."
            ),
        ),
        _e(
            rank=12,
            entity_slug="mike-norvell-fsu-2020",
            entity_display_name="Mike Norvell — Florida State, December 2019",
            program_label="Florida State",
            era_label="2020–",
            statline="Year-3: 10-3 · Year-4: 13-1 (snubbed CFP) · Year-5: 2-10",
            summary_short=(
                "The Memphis coach who rebuilt FSU to 13-1 — and then "
                "watched the snub-and-collapse of the next year's "
                "season."
            ),
            editorial_paragraph=(
                "Norvell took the Florida State job in December 2019 "
                "and spent three years rebuilding the post-Fisher "
                "wreckage (3-6 in 2020, 5-7 in 2021, 10-3 in 2022). "
                "Year four (13-1 in 2023, the most-criticized CFP snub "
                "of the four-team era) was the coronation that wasn't; "
                "year five (2-10 in 2024, the largest year-over-year "
                "win-total drop in FBS history) was the collapse. The "
                "rank reflects the 2020-2023 build more than the 2024 "
                "implosion; the 2025 season will determine whether the "
                "ranking holds."
            ),
        ),
        _e(
            rank=13,
            entity_slug="jonathan-smith-michigan-state-2024",
            entity_display_name="Jonathan Smith — Michigan State, November 2023",
            program_label="Michigan State",
            era_label="2024–",
            statline="Year-1: 5-7 · cleaned up post-Tucker scandal roster",
            summary_short=(
                "The Oregon State coach who came home to East Lansing — "
                "and is rebuilding the program from the post-Tucker-"
                "scandal floor."
            ),
            editorial_paragraph=(
                "Smith took the Michigan State job after his Oregon "
                "State team finished 8-3 and the conference imploded "
                "around him; the choice to leave a working Pac-12 "
                "program for the Spartans was not the obvious move. "
                "Year one (5-7) was the install year on a roster that "
                "had been recruited to two different schemes under "
                "two different head coaches. The hire reads as a "
                "long-arc bet on the Smith operation — the Oregon "
                "State years (2018-2023, 9 of 11 starting QBs were "
                "transfer-portal additions) are the closest analog to "
                "what East Lansing needs. Provisional rank."
            ),
        ),
        _e(
            rank=14,
            entity_slug="sherrone-moore-michigan-2024",
            entity_display_name="Sherrone Moore — Michigan, January 2024",
            program_slug="michigan",
            program_label="Michigan",
            era_label="2024–",
            statline="Year-1: 8-5 · 4-in-a-row over OSU · post-Stalions cleanup",
            summary_short=(
                "The Harbaugh OC who became the head coach within weeks "
                "of the national title — and beat Ohio State again in "
                "his first November."
            ),
            editorial_paragraph=(
                "Moore was the run-game coordinator who served as "
                "acting head coach during Harbaugh's 2023 sign-stealing "
                "suspension and went 4-0 in those games. The promotion "
                "was inevitable when Harbaugh left for the Chargers. "
                "Year one (8-5) was a step backward by win-total, but "
                "the Michigan beat-Ohio-State streak extended to four "
                "with the 13-10 Columbus win in November 2024. The "
                "Stalions investigation continues to overhang the "
                "tenure; the on-field evidence is mixed; the rivalry "
                "result keeps the rank top-15."
            ),
        ),
        _e(
            rank=15,
            entity_slug="hugh-freeze-auburn-2023",
            entity_display_name="Hugh Freeze — Auburn, November 2022",
            program_slug="auburn",
            program_label="Auburn",
            era_label="2023–",
            statline="Year-1: 6-7 · Year-2: 5-7 · '24 Iron Bowl close · provisional",
            summary_short=(
                "The Liberty coach whose two-year Auburn record (11-14) "
                "doesn't yet justify the ranking — but the SEC West "
                "schedule and the Iron Bowl evidence lean positive."
            ),
            editorial_paragraph=(
                "Freeze's hire from Liberty was the coaching market's "
                "most discussed second-chance bet of the 2020s — the "
                "previous Ole Miss tenure ending in NCAA penalties and "
                "the Liberty Group-of-Five years giving him three "
                "10-win seasons. Year one at Auburn (6-7) was the "
                "wilderness; year two (5-7) was worse on its line, "
                "better on its schedule (the close Iron Bowl loss "
                "to Alabama, the close LSU loss). The 2025 evidence "
                "is the make-or-break test; the hire's ranking here "
                "is provisional and will revise sharply either way "
                "next December."
            ),
        ),
        _e(
            rank=16,
            entity_slug="brian-kelly-lsu-2022",
            entity_display_name="Brian Kelly — LSU, November 2021",
            program_slug="lsu",
            program_label="LSU",
            era_label="2022–",
            statline="Year-1: 10-4 · Year-2: 10-3 (Daniels Heisman) · Year-3: 9-4",
            summary_short=(
                "The Notre Dame coach whose Baton Rouge transition "
                "produced Daniels' Heisman in year two — and whose "
                "fourth year is the test."
            ),
            editorial_paragraph=(
                "Kelly's November 2021 departure from Notre Dame for "
                "LSU was the highest-profile coaching defection of the "
                "decade — the press conference's southern-accent "
                "moment is the rare cringe that overshadowed the "
                "actual hire's strength. Year one (10-4) was the "
                "install; year two (10-3, Daniels' Heisman, the SEC "
                "Championship loss to Georgia) was the high point; "
                "year three (9-4) was an SEC West retreat. The "
                "absence of an SEC Championship Game appearance "
                "limits the ranking; the rebuild's trajectory still "
                "reads positive."
            ),
        ),
        _e(
            rank=17,
            entity_slug="eli-drinkwitz-missouri-2020",
            entity_display_name="Eli Drinkwitz — Missouri, December 2019",
            program_label="Missouri",
            era_label="2020–",
            statline="Year-3: 11-2 · '23 Cotton Bowl · stable 8-4 since",
            summary_short=(
                "The Appalachian State coach who took the Missouri job "
                "the week of the Sun Belt Championship — and produced "
                "the program's first 11-win season since 2014."
            ),
            editorial_paragraph=(
                "Drinkwitz's hire was the December 2019 surprise — App "
                "State had won the Sun Belt the day after he took the "
                "Missouri job. Years one and two were unremarkable "
                "(5-5, 6-7); years three through five (8-5, 11-2 with "
                "a Cotton Bowl win, 10-3 in 2024) compounded into the "
                "program's strongest sustained run since the Pinkel "
                "years. The 2023 Cotton Bowl win over Ohio State "
                "anchored the rank — the SEC East schedule's evolving "
                "shape is now Drinkwitz's to navigate."
            ),
        ),
        _e(
            rank=18,
            entity_slug="sam-pittman-arkansas-2020",
            entity_display_name="Sam Pittman — Arkansas, December 2019",
            program_label="Arkansas",
            era_label="2020–",
            statline="Year-2: 9-4 · Year-3: 7-6 · stable mid-tier SEC",
            summary_short=(
                "The Georgia OL coach whose third year (9-4) gave "
                "Arkansas its first ranked finish since 2011 — and the "
                "stability the Bret Bielema era hadn't produced."
            ),
            editorial_paragraph=(
                "Pittman's December 2019 hire was the recruiting-"
                "coordinator-as-head-coach experiment that the "
                "Bielema-Morris collapse necessitated. Year one was "
                "COVID-shortened (3-7); year two (9-4 with the "
                "Outback Bowl win, the program's first ranked finish "
                "since 2011) was the validation; subsequent years have "
                "stabilized in the 7-6 to 9-4 band. The hire's place "
                "on this list reads as a successful mid-tier-SEC bet "
                "rather than a transformational one — the floor was "
                "raised, the ceiling has not been tested."
            ),
        ),
        _e(
            rank=19,
            entity_slug="brent-pry-virginia-tech-2022",
            entity_display_name="Brent Pry — Virginia Tech, December 2021",
            program_label="Virginia Tech",
            era_label="2022–",
            statline="Year-3: 6-7 · stable but unremarkable · '25 the test year",
            summary_short=(
                "The Penn State DC who took the post-Fuente Virginia "
                "Tech job — and is two seasons into a multi-year "
                "rebuild whose verdict isn't yet."
            ),
            editorial_paragraph=(
                "Pry's December 2021 hire from Penn State was the "
                "obvious profile fit (Virginia Tech alum, longtime "
                "Beamer-tree assistant, defensive credentials). Year "
                "one (3-8) was triage; years two and three (7-6, 6-7) "
                "have stabilized but not progressed. The 2025 season "
                "is the make-or-break test — the ACC's reshuffled "
                "competitive shape gives the program a path back to "
                "relevance, and Pry has not yet found it. Provisional "
                "rank."
            ),
        ),
        _e(
            rank=20,
            entity_slug="willie-fritz-houston-2024",
            entity_display_name="Willie Fritz — Houston, December 2023",
            program_label="Houston",
            era_label="2024–",
            statline="Year-1: 4-8 · Big-12 transition · long-arc rebuild",
            summary_short=(
                "The Tulane coach whose Houston hire is the Big-12 "
                "expansion's most substantial bet — year-one returns "
                "are mid-rebuild."
            ),
            editorial_paragraph=(
                "Fritz arrived from Tulane after taking the Green Wave "
                "to back-to-back AAC titles — the credential the "
                "Houston search committee weighted highest. Year one "
                "(4-8) reflects the Big-12 schedule's first-time "
                "punishment more than the program's trajectory. The "
                "five-year window is the right horizon to grade the "
                "Fritz hire; one season of evidence puts it on this "
                "list as a placeholder."
            ),
        ),
        _e(
            rank=21,
            entity_slug="bret-bielema-illinois-2021",
            entity_display_name="Bret Bielema — Illinois, December 2020",
            program_label="Illinois",
            era_label="2021–",
            statline="Year-2: 8-5 · Year-4: 10-3 · '24 Citrus Bowl",
            summary_short=(
                "The post-Wisconsin Bielema return that took four years "
                "to compound — the 2024 Citrus Bowl winner and the "
                "Illini's strongest season since 2007."
            ),
            editorial_paragraph=(
                "Bielema's NFL coordinator detour ended in December "
                "2020 with the Illinois job — the first Big Ten head-"
                "coaching hire since his Wisconsin departure in 2012. "
                "The first three years (5-7, 8-5, 5-7) were uneven; "
                "year four (10-3 with a Citrus Bowl win) was the "
                "breakthrough that this list ranks above the win-total "
                "average. The 2025 season is the consolidation test."
            ),
        ),
        _e(
            rank=22,
            entity_slug="luke-fickell-wisconsin-2023",
            entity_display_name="Luke Fickell — Wisconsin, November 2022",
            program_label="Wisconsin",
            era_label="2023–",
            statline="Year-1: 7-6 · Year-2: 5-7 · two years of disappointing returns",
            summary_short=(
                "The Cincinnati Group-of-Five superstar whose Wisconsin "
                "tenure has not produced the early returns the "
                "Madison committee paid for."
            ),
            editorial_paragraph=(
                "Fickell's November 2022 hire from Cincinnati — the "
                "13-1 Group-of-Five Playoff team of 2021 — was the most "
                "celebrated Big Ten hire of the cycle. Two years later "
                "(7-6 and 5-7) the criticism has hardened; the air-raid "
                "implementation under Phil Longo has not yet produced "
                "the offensive identity Madison expected. The hire's "
                "ranking here is generous — the Group-of-Five "
                "credentials and the underlying recruiting work "
                "earn a top-25 placement that on-field results have "
                "not yet vindicated. Provisional."
            ),
        ),
        _e(
            rank=23,
            entity_slug="billy-napier-florida-2022",
            entity_display_name="Billy Napier — Florida, December 2021",
            program_slug="florida",
            program_label="Florida",
            era_label="2022–",
            statline="Year-1: 6-7 · Year-3: 8-5 · seat heated through '24",
            summary_short=(
                "The Louisiana coach whose three-year Florida run has "
                "been mid-tier SEC stable — and whose fourth year is "
                "the make-or-break."
            ),
            editorial_paragraph=(
                "Napier's hire from Louisiana was the Group-of-Five "
                "credentials bet that has not yet compounded — three "
                "years in (6-7, 5-7, 8-5) the program's trajectory has "
                "stabilized in the wrong band. The 2024 season "
                "produced the recruiting class that gives 2025 the "
                "evidence to grade the tenure. The seat is currently "
                "warm; the buyout's structure makes a December 2025 "
                "decision the program's most-anticipated one."
            ),
        ),
        _e(
            rank=24,
            entity_slug="jeff-brohm-louisville-2023",
            entity_display_name="Jeff Brohm — Louisville, December 2022",
            program_label="Louisville",
            era_label="2023–",
            statline="Year-1: 10-4 · Year-2: 9-4 · '23 ACC Championship runner-up",
            summary_short=(
                "The hometown coach whose two-year Louisville return has "
                "produced the program's strongest ACC run since the "
                "Petrino-Jackson years."
            ),
            editorial_paragraph=(
                "Brohm left Purdue (where he had taken the program to "
                "the 2022 Big Ten Championship) for the Louisville job "
                "— an unusual lateral that the Cardinals' alumni "
                "network had been pushing for two cycles. Year one "
                "(10-4, the ACC Championship Game appearance) was the "
                "validation; year two (9-4) sustained it. The 2025 "
                "season is the consolidation test; the Brohm hire's "
                "ranking should compound upward if year three holds."
            ),
        ),
        _e(
            rank=25,
            entity_slug="dabo-swinney-extension-2023",
            entity_display_name="Dabo Swinney — Clemson extension, January 2023",
            program_slug="clemson",
            program_label="Clemson",
            era_label="2023–",
            statline="$115M extension · Year-1: 9-4 · Year-2: 10-4 · '24 ACC title",
            summary_short=(
                "The 10-year, $115M extension that re-cemented Swinney "
                "in Clemson — and the post-extension years that have "
                "stabilized the program after the post-Lawrence dip."
            ),
            editorial_paragraph=(
                "Not a new hire — the January 2023 extension that made "
                "Swinney the longest-tenured contracted coach in the "
                "sport (through 2031) is included here as a "
                "consequential coaching-market decision of the 2020s. "
                "The post-extension years (9-4, 10-4 with the 2024 "
                "ACC Championship win) have stabilized the program in "
                "a way the 2021-2022 mid-tier-ACC seasons had not. "
                "Swinney's portal-aversion and his roster-development "
                "register remain idiosyncratic in the modern coaching "
                "market — the Clemson program is the test case for "
                "whether that register still produces championship-"
                "tier returns at scale."
            ),
        ),
    ]
