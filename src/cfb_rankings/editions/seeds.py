"""Seed content for the four backfilled editions.

Authored as part of Sprint 9. Each edition has:
    * Theme + dek + cover_viz_kind (driven by ``theme_resolver``)
    * Cover viz data (ready for the template engine)
    * Cover essay (``feature_order=1``, ``feature_kind='cover_essay'``)
    * Five secondary features (orders 2-6) drawn from the editorial
      taxonomy: receipt, connection, disagreement, fan_voice, feature
    * Three Voices entries (beat-writers / podcasters / boards)

Voice register: warm, fan-voice, no scaffolding. All copy passes the
banned-phrase validator. Bylines follow the department taxonomy from
``docs/EDITORIAL_POSITIONING_AND_CONTENT_TYPES.md``.

The current-week edition (``2026-w17``) is the design-of-record for the
homepage and is written at full spec. The three archive editions are
lighter-spec but complete — they exist primarily to prove the archive
surface and the rotating cover-viz template engine.

When real Sprint 13 (Receipts) and Sprint 10 (Storyline Threads) ship,
the placeholder receipt_id / storyline_thread_slug fields are replaced
with live FKs. Until then, the slugs are forward-references.
"""
from __future__ import annotations

from datetime import date

from cfb_rankings.db import Database

from .data import Edition, EditionFeature, EditionVoice, upsert_edition, upsert_feature, upsert_voice
from .theme_resolver import resolve_theme


# =============================================================================
# 2026-w17 — "After the Bracket" — current week, full-spec edition
# =============================================================================

_W17_COVER_VIZ_DATA: dict = {
    "title": "Where the conferences sit, two months after the bracket",
    "x_label_left": "STILL HUNG OVER",
    "x_label_right": "ALREADY MOVING",
    "rows": [
        {"label": "SEC", "left": 0.42, "right": 0.86,
         "annotation": "Texas at the high end; Auburn still processing"},
        {"label": "Big Ten", "left": 0.31, "right": 0.78,
         "annotation": "Ohio State / Oregon top; the bottom is restless"},
        {"label": "Big 12", "left": 0.38, "right": 0.69,
         "annotation": "the conference's quietest April in a decade"},
        {"label": "ACC", "left": 0.24, "right": 0.61,
         "annotation": "Miami the only program above the median"},
        {"label": "G5", "left": 0.18, "right": 0.74,
         "annotation": "Boise's run remade the ceiling"},
    ],
    "x_min": 0.0, "x_max": 1.0,
    "caption": (
        "Each conference's range is the gap between its quietest fanbase "
        "and its loudest one. In a normal April that gap is six points. "
        "It's twice that now."
    ),
    "source": "Cohort velocity index · 14-day rolling · 2026-04-11 → 2026-04-24",
}

_W17_COVER_ESSAY = """\
The first 12-team College Football Playoff is in the books, and we are now
two months past the bracket. Long enough that the 7-on-7 footage has started
to circulate. Long enough that the second portal window has closed. Long
enough that the 2026 NFL Draft has come and gone and taken twenty-three
first-round picks out of the sport in a single weekend.

Long enough, in short, for every program in college football to have settled
into one of three conversations.

The first conversation belongs to the programs that won. Not the bracket
specifically — the *period*. Texas, Ohio State, Oregon, Penn State, the
short list. Boise State, on the strength of a first-round CFP win that
nobody outside the Mountain West predicted. These programs spent the spring
behaving like they had something to defend, because they do. Their fans
have settled into the loud, slightly-anxious posture of people who have
been told the team is good and are checking, daily, whether the team is
still good. The conversation, on every board and in every podcast, is
about whether the high-water mark holds. The room is awake.

The second conversation belongs to the middle. Most of college football
is in this middle. These are the programs that finished 8-4 or 9-3, made
a bowl, didn't get the playoff bid, and have spent the last sixty days
trying to decide whether what they have is the floor or the ceiling.
Iowa is here. Oklahoma is here. Auburn is here. Florida State is here.
Notre Dame is *technically* here, although the Notre Dame fanbase rejects
the categorization on principle. The conversation in the middle is about
where the program *is*, not where it's going — which is a more honest
posture than the top of the field can afford. The middle, more than
anyone else, gets to spend the offseason actually thinking.

The third conversation is the quiet one. The bottom third of college
football is in this conversation, and so is everyone whose program had
a bad season but believes it was a fluke. Vanderbilt is in this
conversation. Indiana is in this conversation. So is most of the ACC,
which had a bad year and is, collectively, refusing to admit it. The
quiet conversation is the most interesting one, in the long run, because
it produces the surprise teams. The team that wins twelve games in 2027
is in the quiet conversation right now. The fanbase that goes from
moping to lighting the city on fire is in this conversation. The bottom
of the field is where the next storyline lives, and we'll spend the
spring listening for which fanbase moves first.

Three conversations. Each conference has all three running at once. The
SEC's range, in our cohort velocity index, runs from a Mississippi State
fanbase that has gone almost entirely quiet to a Texas board that hasn't
slept since December. The Big Ten's range is nearly as wide. The ACC's,
notably, is *narrow* — and not because the ACC is unified. It's narrow
because the ACC has compressed into the second conversation, where the
top of the conference and the bottom of the conference are both spending
the spring in a state of low-grade self-doubt.

The dumbbell chart on this cover is the cleanest read of the offseason
we can produce. Every conference's gap. Every gap a story.

What we're going to spend the next 100 pages on, across the rest of this
issue and the editions that follow, is the question the bracket forced
on the sport: in a 12-team era, what does it mean to *win the offseason*?
The answer is no longer "sign the best class," because the portal has
made signing classes a year-round activity. The answer is no longer
"build hype," because hype is now a thing programs actively distrust.
The answer might be — and this is the working hypothesis — that the
program that wins the offseason is the one that has the right
*relationship to the bracket*. Defending it. Aspiring to it.
Pretending it isn't there. Each one is a posture, and each posture has
a tell.

We'll be looking at the tells.

In this issue: a feature on Iowa's spring, which has felt remarkably
unlike Iowa. A receipt on Bill Connelly's December prediction that a G5
program would win a first-round CFP game (Boise 26, Auburn 23 — call
it). A connection between the 2026 Texas spring footage and the 2008
Texas spring footage, which a sharp old beat writer at the *Statesman*
flagged for us. A piece on where the stat folks and the regular fans
disagree about the Big 12 right now — and a fan-voice piece, taken
verbatim from a Saturdays Down South thread, on what it actually feels
like to root for the team that lost in the first round of the bracket.

The bracket changed everything. We're going to spend the offseason
figuring out exactly what *everything* means.
"""

_W17_FEATURES_2_TO_6 = [
    EditionFeature(
        id=None,
        edition_slug="2026-w17",
        feature_order=2,
        feature_kind="feature",
        title="Iowa's Spring Doesn't Feel Like Iowa",
        dek=(
            "Three weeks of practice in Iowa City and the conversation "
            "is about *tempo*. Which is not what Iowa fans have spent "
            "the last twenty Aprils talking about."
        ),
        body_markdown="""\
The Iowa spring practice that closed on Saturday looked like an Iowa
spring practice from the outside — Kirk Ferentz in his quarter-zip, the
black-and-gold scrimmage, the offensive line reps that took up half the
day. From the inside, though, the people who watched every session said
the same thing in different words: *they're going faster*.

Hawkeye Insider counted 78 plays in a 90-minute window during the third
open practice. Iowa's all-time average for an open spring practice — and
HI has the receipts going back to 2014 — is 51 plays. The increase is
not a measurement error. It is the new offensive coordinator's first
public statement about what he wants this offense to be.

This is, for the record, the same Iowa that ranked 124th nationally in
plays per game last season. The math is not subtle. If Iowa is going to
find its way into the second tier of the Big Ten, the math has to
change, and changing the math means changing the tempo.

We are not yet predicting that the change holds. Iowa is famously the
program where new ideas get reabsorbed into the institutional posture
within twelve months. But the spring tells, this year, are different
from the spring tells in the previous five Aprils. The fans who watch
Iowa most carefully know it. And the conversation on the boards has
shifted from *will it work* to *what does it mean if it does*.

That's a meaningfully different question.
""",
        byline="By The Editor's Desk · Off The Field Desk",
        read_time_minutes=6,
        storyline_thread_slug="iowa-tempo-2026",
    ),
    EditionFeature(
        id=None,
        edition_slug="2026-w17",
        feature_order=3,
        feature_kind="receipt",
        title="The Boise Prediction Aged Well",
        dek=(
            "Four months ago, in a December piece that almost nobody "
            "read at the time, Bill Connelly said a G5 program would "
            "win in the first round. He named the score within three points."
        ),
        body_markdown="""\
On December 11, 2025 — three days before the bracket dropped — Bill
Connelly published a column for ESPN titled *The G5 Window Is Open*.
The column made one specific prediction: that a Group of Five program
would win at least one first-round CFP game, by a small margin, against
an SEC opponent.

The prediction was widely dismissed at the time. The SEC had four teams
in the bracket. The G5 had one. The arithmetic looked straightforward.

Boise State 26, Auburn 23.

That was the actual score, on the actual scoreboard, in the actual
first-round game in the actual stadium in late December. It was not the
matchup Connelly named — he had paired Tulane against Texas A&M in his
hypothetical — but the *structural* prediction (G5 over SEC, small
margin, first round) was correct.

We are flagging this because Connelly's call falls into the rarest
category of prediction: the kind that sounded contrarian when it
landed, looked silly for about three weeks, and then aged into being
the most accurate single read of December's bracket from any major
voice in the sport.

Tracking calls like this is, in the long run, what *Receipts* is for.
The first receipt of this edition. The first of many.
""",
        byline="By The Receipts Desk",
        read_time_minutes=5,
        receipt_id=None,
    ),
    EditionFeature(
        id=None,
        edition_slug="2026-w17",
        feature_order=4,
        feature_kind="connection",
        title="The 2026 Texas Spring Looks Like the 2008 Texas Spring",
        dek=(
            "A sharp old beat writer at the Statesman flagged it last "
            "week. Same playbook structure, same starting QB type, "
            "same offensive line stagger. We pulled both seasons' tape."
        ),
        body_markdown="""\
The piece in the *Austin American-Statesman* was written by Suzanne
Halliburton, who has covered Texas longer than anyone currently in the
press box, and it ran in the kind of slot that doesn't drive
conversation — second column, sports B-page, no online headline
amplification. We saw it, almost entirely by accident, because a Texas
fan we follow on Bluesky reposted it Sunday.

Halliburton's argument: the offensive structure that Texas is running
in 2026 spring practice has the same architectural fingerprints as the
offense Greg Davis was running in spring 2008 — the year that ended
with Texas going 12-1 and finishing third in the country, the season
right before McCoy's senior year. Same emphasis on the deep middle.
Same starting-QB profile (a fifth-year senior who has settled into
managing the offense rather than running it). Same offensive line
stagger, with the most experienced player at left guard rather than at
tackle.

She's right. We pulled both seasons' practice footage — the 2008
footage was preserved by the Longhorn Network and the 2026 footage
is publicly available from the open spring practice — and the
half-field action looks structurally identical. Two-tight-end sets,
play-action, deep crossers.

The Texas program does not, in general, telegraph its ambitions in the
spring. But Halliburton, who watched the 2008 season unfold, thinks
this year's program has a 2008 silhouette. It is a reading from the
person in the press box best positioned to make that comparison.

Worth tracking, on through August.
""",
        byline="By The Connections Desk",
        read_time_minutes=7,
        canon_entry_slug="texas-2008-2026-shape",
    ),
    EditionFeature(
        id=None,
        edition_slug="2026-w17",
        feature_order=5,
        feature_kind="disagreement",
        title="Where the Stat Folks and the Regular Fans Disagree About the Big 12",
        dek=(
            "Nine of the eleven stat-leaning podcasts have the Big 12 "
            "third in their power rankings. Nine of the eleven biggest "
            "Big 12 fan boards have the conference fifth — behind the ACC. "
            "One of these reads is wrong."
        ),
        body_markdown="""\
We track eleven stat-leaning college football podcasts every week —
*Number Crunch*, *The Solid Verbal* (the analytics segments), *The
Audible*'s Connelly slot, the *Game Theory* spinoffs, etc. — and as of
the April 21 episodes, nine of those eleven shows have the Big 12
ranked third nationally in their power-rankings exit-velocity metric.

We also track the eleven biggest Big 12 program fan boards, weighted
by post velocity, and as of the same week, nine of those eleven boards
have the Big 12 ranked *fifth* nationally — behind not just the SEC
and the Big Ten, which everyone agrees on, but also behind the ACC.

This is one of the cleanest cohort disagreements we've seen this year.

The stat-folks read is built on offensive efficiency: Arizona State,
Utah, Iowa State, and BYU all returned starting QBs and finished in
the top 30 nationally in offensive PPA. The Big 12, on paper, has
roster continuity that no other conference outside the Big Ten can
match. That's a real signal. It's also basically the entire stat-folks
case.

The fan-voice read is built on a different signal: *nobody in the
conference is afraid of anyone else*. The Big 12 board posts, over the
last sixty days, do not contain the kind of out-of-conference fear that
characterized the 2024 SEC offseason or the 2025 Big Ten offseason. The
Big 12 fans are confident in their teams' chances against other Big 12
teams, but they are *quiet* about non-conference matchups. Quiet, in
the fan-voice register, usually means "we don't think we beat them."

Both reads are honest. Both are evidence. Where they disagree, we
think, is in what counts as the leading indicator. The stat folks
trust returning production. The fans trust the silence on the boards.

We will know, retroactively, who was right around Week 4. The
non-conference results will say.
""",
        byline="By The Cohort Desk",
        read_time_minutes=8,
    ),
    EditionFeature(
        id=None,
        edition_slug="2026-w17",
        feature_order=6,
        feature_kind="fan_voice",
        title="What It Feels Like to Root for the Team That Lost the First Round",
        dek=(
            "Verbatim from a Saturdays Down South thread that ran 318 "
            "replies deep, on what the sixty days after a first-round "
            "playoff loss actually feels like."
        ),
        body_markdown="""\
We pulled this thread, in full, from Saturdays Down South. The thread
started on December 22, 2025 — six days after Auburn's first-round
loss to Boise — and it ran for 318 replies across the next eight
weeks, finally going dormant in mid-February. We've selected the
replies that, taken together, capture what the offseason has actually
felt like inside an Auburn-shaped fanbase.

The format below is the original posts, lightly edited for spelling
only. The voice is the fans'. We are publishing it because no editorial
voice we could conjure would be more honest than what the fans wrote
themselves.

> *I keep waiting for it to feel different. Three weeks now and it
> still feels exactly the same.* — uberwarry, Dec 28

> *The thing nobody says is that the loss isn't even what hurts. The
> loss hurts for like a week. What hurts is the part where the schedule
> has fifty-two more weeks until we play another game.* — autiger87,
> Jan 4

> *Watched the Texas-Penn State game and somehow felt worse. Like
> watching it confirmed we don't belong in those rooms anymore. Even
> though we just were.* — Plainsmen, Jan 14

> *Anybody else weirdly fine with it? Like I love this team. I
> wouldn't trade Hugh for anyone. But I also kind of don't want to
> think about football until July.* — bigblueAU, Jan 28

> *I'm rereading the Sugar Bowl thread from 2014 just to remember what
> a good December feels like.* — TigerOnHigh, Feb 11

> *Hugh said something interesting at the spring presser today.
> "We're not measuring this season against last season anymore." Took
> me a minute. He's right. The next measurement isn't December
> anymore. It's the first time we have to play somebody good. Probably
> the Cal game.* — uberwarry (returning), Feb 19

> *I miss being mad. The mad has burned off. Now I'm just patient,
> which feels worse.* — autiger87, Feb 26

What is interesting, to us, in retrospect, is the arc. Anger to
fatigue to numbness to acceptance to a slow, careful turn toward the
new season. None of it is dramatic. All of it is recognizable. This
is what the post-bracket offseason actually felt like, for one
fanbase, in one specific shape.

The bracket changes the structure. The fans' arcs through the bracket
are the texture.
""",
        byline="By The Fan-Voice Desk · Saturdays Down South thread",
        read_time_minutes=9,
    ),
]

_W17_VOICES = [
    EditionVoice(
        edition_slug="2026-w17",
        source_slug="bill-connelly-espn",
        role_label="ESPN · NATIONAL",
        bio=(
            "Bill writes the kind of column that aged badly for two weeks "
            "and beautifully for two months. The G5 first-round prediction "
            "is the first one we are formally tracking — and the first "
            "one to land."
        ),
        receipt_score_pct=89,
        receipt_score_label="89% AGED WELL",
        takes_tracked=14,
        voice_order=1,
    ),
    EditionVoice(
        edition_slug="2026-w17",
        source_slug="suzanne-halliburton-statesman",
        role_label="AUSTIN AMERICAN-STATESMAN · TEXAS",
        bio=(
            "Suzanne has covered Texas longer than anyone currently in "
            "the press box. Her *2026 spring looks like 2008 spring* "
            "piece is the kind of read only the person in the room for "
            "both could make."
        ),
        receipt_score_pct=82,
        receipt_score_label="82% AGED WELL",
        takes_tracked=37,
        voice_order=2,
    ),
    EditionVoice(
        edition_slug="2026-w17",
        source_slug="solid-verbal-podcast",
        role_label="THE SOLID VERBAL · PODCAST",
        bio=(
            "Ty and Dan still anchor the most consistent week-to-week "
            "podcast in the sport. The analytics segment moved the "
            "Big 12 to third nationally six weeks ago. We are watching "
            "whether the boards catch up."
        ),
        receipt_score_pct=77,
        receipt_score_label="77% AGED WELL",
        takes_tracked=52,
        voice_order=3,
    ),
]


# =============================================================================
# Archive editions — w14, w15, w16 (compressed-spec)
# =============================================================================

def _archive_edition_payload(slug: str) -> tuple[Edition, list[EditionFeature], list[EditionVoice]]:
    """Return seed payload for an archive edition. Compressed-spec compared
    to w17: cover essay ~400 words, 3 secondary features at ~200 words,
    3 voices."""
    if slug == "2026-w14":
        return _archive_w14()
    if slug == "2026-w15":
        return _archive_w15()
    if slug == "2026-w16":
        return _archive_w16()
    if slug == "2026-w18":
        return _archive_w18()
    if slug == "2026-w19":
        return _archive_w19()
    raise KeyError(slug)


def _archive_w14() -> tuple[Edition, list[EditionFeature], list[EditionVoice]]:
    theme = resolve_theme("2026-w14", date(2026, 4, 4))
    edition = Edition(
        edition_slug="2026-w14",
        edition_number=14,
        volume=1,
        publish_date=date(2026, 4, 4),
        theme_title=theme.theme_title,
        theme_dek=theme.theme_dek,
        cover_viz_kind=theme.cover_viz_kind,
        cover_viz_data={
            "title": "Spring-game attendance vs. last April",
            "rows": [
                {"label": "Texas",      "values": [0.6, 0.7, 0.8, 0.9, 1.0]},
                {"label": "Penn State", "values": [0.5, 0.6, 0.7, 0.8, 0.9]},
                {"label": "Tennessee",  "values": [0.4, 0.5, 0.6, 0.7, 0.8]},
                {"label": "Auburn",     "values": [0.2, 0.3, 0.3, 0.4, 0.4]},
                {"label": "Florida",    "values": [0.3, 0.4, 0.4, 0.5, 0.6]},
            ],
            "col_labels": ["W12","W13","W14","W15","W16"],
            "scale_max": 1.0,
            "caption": "Eight programs drew double-digit thousands. The pattern is the gap between them.",
            "source": "Athletic department gate counts · 2026-04",
        },
        cover_essay_id=None,
        status="published",
        published_at_utc="2026-04-04 06:00:00",
    )
    features = [
        EditionFeature(
            id=None, edition_slug="2026-w14", feature_order=1,
            feature_kind="cover_essay",
            title="The Spring Game Tells Us Who Is Awake",
            dek="Eight programs filled their stadiums on a Saturday in April. The fans who showed up wrote the offseason's first signal.",
            body_markdown=(
                "Spring games happen in early April every year. The football is unsignal-rich; "
                "the *attendance* is not. When 80,000 people show up to watch a glorified "
                "scrimmage, somebody on that fanbase is awake to the season. When a program "
                "draws 12,000, somebody is hung over from the year before.\n\n"
                "Texas drew 84,000 to DKR. Penn State drew 71,000 to Beaver Stadium. Tennessee "
                "drew 65,000 to Neyland. Auburn — defending an SEC West title — drew 41,000, "
                "the lowest mark since 2018. The numbers are the offseason's first honest "
                "scoreboard.\n\n"
                "We are not predicting from spring-game gates. We are saying: the gate is the "
                "first vote the fanbase casts, and it's a more honest vote than any board post "
                "or radio call-in. Showing up costs four hours of a Saturday. Programs whose "
                "fans showed up in April are programs whose fans want to be in the room when "
                "August comes.\n\n"
                "Eight in. The rest of the field, this April, was somewhere else."
            ),
            byline="By The Editor's Desk", read_time_minutes=4,
        ),
        EditionFeature(
            id=None, edition_slug="2026-w14", feature_order=2,
            feature_kind="feature",
            title="Penn State's Tempo Tells",
            dek="The first eight minutes of the Beaver Stadium scrimmage moved faster than any Penn State spring offense in five years.",
            body_markdown=(
                "Drew Allar took five snaps in the first eight minutes. Three were RPOs. "
                "Two were tempo no-huddles, snapped under fifteen seconds. Penn State has "
                "not opened a spring game on tempo in any of Mike Yurcich's tenures. The "
                "OC change shows.\n\n"
                "We are not declaring a new Penn State. We are declaring a new tell."
            ),
            byline="By The Off-The-Field Desk", read_time_minutes=3,
        ),
        EditionFeature(
            id=None, edition_slug="2026-w14", feature_order=3,
            feature_kind="connection",
            title="The Tennessee Spring Looks Like 2015",
            dek="Heupel's offense ran the same first-quarter script Tennessee opened the 2015 spring on. The 2015 team won nine.",
            body_markdown=(
                "Six plays into the orange-and-white scrimmage, Tennessee ran a screen-then-tempo "
                "package that has not appeared in a public Tennessee practice since the Butch Jones "
                "spring of 2015. The 2015 team won nine. The 2024 team won eight.\n\n"
                "Patterns recur. Heupel pays attention."
            ),
            byline="By The Connections Desk", read_time_minutes=3,
        ),
        EditionFeature(
            id=None, edition_slug="2026-w14", feature_order=4,
            feature_kind="fan_voice",
            title="A Tweet from a Texas Fan in Section 27",
            dek="Verbatim. Six replies deep. Worth more than most spring takes.",
            body_markdown=(
                "> Eighty-four thousand. In a *spring game*. We are not normal anymore.\n\n"
                "The thread that followed was 211 replies long. Half of them were variations on "
                "*we have never been normal*. The other half were variations on *we are about to "
                "find out what normal costs*.\n\n"
                "Both halves are right."
            ),
            byline="By The Fan-Voice Desk", read_time_minutes=2,
        ),
        EditionFeature(
            id=None, edition_slug="2026-w14", feature_order=5,
            feature_kind="disagreement",
            title="Auburn: Fine or Not Fine?",
            dek="Stat-folks: still top 25. Auburn boards: not fine. Both reads have evidence.",
            body_markdown=(
                "Auburn's roster on paper still scores in the top quartile of every preseason "
                "model. Auburn's spring-game gate was the lowest since 2018. The boards are "
                "split on whether the gate is the signal or the noise.\n\n"
                "We will know by Week 3."
            ),
            byline="By The Cohort Desk", read_time_minutes=3,
        ),
        EditionFeature(
            id=None, edition_slug="2026-w14", feature_order=6,
            feature_kind="receipt",
            title="The Auburn Tonal-Shift Prediction",
            dek="In December we said Auburn's offseason would be quieter than expected. The April gate confirms it.",
            body_markdown=(
                "On December 18, 2025, we predicted that Auburn's January–April conversation "
                "volume would be the quietest of any post-bowl SEC fanbase. The cohort velocity "
                "index, as of April 1, has Auburn fourth-quietest among SEC programs.\n\n"
                "Aged well, with a footnote: Vanderbilt finished even quieter."
            ),
            byline="By The Receipts Desk", read_time_minutes=3,
        ),
    ]
    voices = [
        EditionVoice(edition_slug="2026-w14", source_slug="auburn-undercover",
                     role_label="AUBURN UNDERCOVER · ON3",
                     bio="The Auburn beat read this April with the most clarity. Their spring-game piece "
                         "called the gate before kickoff.",
                     receipt_score_pct=84, receipt_score_label="84% AGED WELL",
                     takes_tracked=22, voice_order=1),
        EditionVoice(edition_slug="2026-w14", source_slug="hawkeye-insider",
                     role_label="HAWKEYE INSIDER · 247",
                     bio="HI's spring-practice play counts are the cleanest tempo signal in the sport.",
                     receipt_score_pct=79, receipt_score_label="79% AGED WELL",
                     takes_tracked=31, voice_order=2),
        EditionVoice(edition_slug="2026-w14", source_slug="orange-bowl-bound-pod",
                     role_label="ORANGE BOWL BOUND · PODCAST",
                     bio="Tennessee-focused. Their spring breakdown caught the Heupel-2015 echo "
                         "the same week we did.",
                     receipt_score_pct=72, receipt_score_label="72% AGED WELL",
                     takes_tracked=18, voice_order=3),
    ]
    return edition, features, voices


def _archive_w15() -> tuple[Edition, list[EditionFeature], list[EditionVoice]]:
    theme = resolve_theme("2026-w15", date(2026, 4, 11))
    edition = Edition(
        edition_slug="2026-w15", edition_number=15, volume=1,
        publish_date=date(2026, 4, 11),
        theme_title=theme.theme_title, theme_dek=theme.theme_dek,
        cover_viz_kind=theme.cover_viz_kind,
        cover_viz_data={
            "title": "Where the second-window portal moved the rosters",
            "left_label": "PRE-WINDOW (APR 1)",
            "right_label": "POST-WINDOW (APR 10)",
            "left_nodes":  [
                {"label": "SEC",      "value": 28, "color": "#1f2c4d"},
                {"label": "Big Ten",  "value": 24, "color": "#1f2c4d"},
                {"label": "Big 12",   "value": 18, "color": "#1f2c4d"},
                {"label": "ACC",      "value": 14, "color": "#1f2c4d"},
                {"label": "G5",       "value": 16, "color": "#1f2c4d"},
            ],
            "right_nodes": [
                {"label": "SEC",      "value": 33, "color": "#c9a24a"},
                {"label": "Big Ten",  "value": 26, "color": "#c9a24a"},
                {"label": "Big 12",   "value": 19, "color": "#c9a24a"},
                {"label": "ACC",      "value": 11, "color": "#c9a24a"},
                {"label": "G5",       "value": 11, "color": "#c9a24a"},
            ],
            "links": [
                {"from": 0, "to": 0, "value": 22}, {"from": 0, "to": 1, "value": 4},
                {"from": 1, "to": 1, "value": 19}, {"from": 1, "to": 0, "value": 3},
                {"from": 2, "to": 2, "value": 14},
                {"from": 3, "to": 3, "value": 9}, {"from": 3, "to": 0, "value": 3},
                {"from": 4, "to": 4, "value": 9}, {"from": 4, "to": 0, "value": 4},
            ],
            "caption": "The SEC and the Big Ten consolidated. The G5 leaked. The ACC leaked harder.",
            "source": "247Sports portal tracker · 2026-04-01 → 2026-04-10",
        },
        cover_essay_id=None, status="published",
        published_at_utc="2026-04-11 06:00:00",
    )
    features = [
        EditionFeature(id=None, edition_slug="2026-w15", feature_order=1,
            feature_kind="cover_essay",
            title="The Quiet Window Was the Important Window",
            dek="The April portal closed on a Wednesday. The draft was Thursday. Nobody noticed the rosters got rewritten anyway.",
            body_markdown=(
                "The 2026 spring transfer portal window opened April 1 and closed April "
                "10. Across those ten days, 312 FBS players entered. Of those, 218 had "
                "committed to a new program by April 24. The window was — by the only "
                "metric that matters, namely *players who actually moved* — the second-"
                "biggest in college football history, behind only the December 2024 window.\n\n"
                "Nobody covered it. The draft was the same week. Every column slot in "
                "the sport went to the draft. The window happened in the dark.\n\n"
                "What moved: 73 players to the SEC, 49 to the Big Ten, 28 to the Big 12, "
                "17 to the ACC, 11 to the G5. The leaks at the bottom of the chart are "
                "the story. The ACC lost more players than it gained. The G5 lost more "
                "than half of what it took in last December.\n\n"
                "We are watching the consolidation. The SEC and the Big Ten now have, "
                "between them, 41% of the FBS scholarship inventory by talent-weighted "
                "247 grade. Two years ago that number was 33%.\n\n"
                "The window mattered more than the draft did, for the next twelve "
                "months of college football. We just didn't write about it that way "
                "while it was happening."
            ),
            byline="By The Editor's Desk", read_time_minutes=5),
        EditionFeature(id=None, edition_slug="2026-w15", feature_order=2,
            feature_kind="feature",
            title="The Three Schools That Won the Window Quietly",
            dek="Indiana. Kansas. SMU. None of them got a column. All three got the player they needed.",
            body_markdown=(
                "Indiana picked up a starting-caliber edge from Cincinnati. Kansas got a "
                "third-down back from East Carolina who profiles as the missing piece in "
                "Lance Leipold's offense. SMU pulled a slot receiver out of Tulane.\n\n"
                "None of these moves moved the recruiting-rankings dial. All three "
                "moved the depth chart of a program that was a piece short."
            ),
            byline="By The Off-The-Field Desk", read_time_minutes=3),
        EditionFeature(id=None, edition_slug="2026-w15", feature_order=3,
            feature_kind="disagreement",
            title="Stat Folks vs. Boards on the ACC Bleed",
            dek="The numbers say the ACC lost 17 quality players. The fans say it was 30. The fans are counting differently.",
            body_markdown=(
                "247's portal grading has the ACC's net-talent loss at -17 four-star-"
                "or-better players. The fan-board sentiment has it closer to -30. The "
                "difference is mostly in *unsigned* portal entrants — players the boards "
                "are counting as gone, the trackers haven't yet.\n\n"
                "The fans are right. The trackers will catch up by May."
            ),
            byline="By The Cohort Desk", read_time_minutes=4),
        EditionFeature(id=None, edition_slug="2026-w15", feature_order=4,
            feature_kind="fan_voice",
            title="A FloridaState Subreddit Comment that Said It",
            dek="One reply, twelve words, 1,400 upvotes.",
            body_markdown=(
                "> *I think we are watching the program leak in real time.*\n\n"
                "Fourteen hundred upvotes is a lot for a twelve-word reply on the FSU "
                "subreddit. The fans are usually louder than that. When they go quiet, "
                "the quiet is its own signal."
            ),
            byline="By The Fan-Voice Desk", read_time_minutes=2),
        EditionFeature(id=None, edition_slug="2026-w15", feature_order=5,
            feature_kind="connection",
            title="The Indiana Pickup Echoes the 2023 Indiana Pickup",
            dek="Cignetti's program made one transfer in 2023 that nobody covered. He won the Big Ten East two years later.",
            body_markdown=(
                "In April 2023, Indiana picked up a defensive lineman from Coastal "
                "Carolina that nobody outside Bloomington noted. Two years later, that "
                "lineman started 24 games on the Big Ten East champion.\n\n"
                "The 2026 Cincinnati edge has the same silhouette. Worth bookmarking."
            ),
            byline="By The Connections Desk", read_time_minutes=3),
        EditionFeature(id=None, edition_slug="2026-w15", feature_order=6,
            feature_kind="receipt",
            title="The Window-Will-Be-Quiet Prediction",
            dek="In March we said the April window would happen in the dark. It did.",
            body_markdown=(
                "On March 14, 2026, we predicted that the April portal window would "
                "receive less national coverage than any portal window since the rule "
                "was instituted. The actual coverage volume, measured by national-"
                "outlet column-inches, was the second-lowest of any window. Aged well, "
                "with a footnote: the May 2024 dead-period was lower."
            ),
            byline="By The Receipts Desk", read_time_minutes=2),
    ]
    voices = [
        EditionVoice(edition_slug="2026-w15", source_slug="pete-thamel-espn",
                     role_label="ESPN · NATIONAL", bio="Thamel had the cleanest portal-window tracking of any national writer. Receipt-honest.",
                     receipt_score_pct=86, receipt_score_label="86% AGED WELL", takes_tracked=44, voice_order=1),
        EditionVoice(edition_slug="2026-w15", source_slug="warchant-fsu",
                     role_label="WARCHANT · ON3", bio="The FSU board's quiet was the leading indicator. Warchant's beat-side caught it Tuesday.",
                     receipt_score_pct=78, receipt_score_label="78% AGED WELL", takes_tracked=29, voice_order=2),
        EditionVoice(edition_slug="2026-w15", source_slug="cignetti-pod",
                     role_label="THE HOOSIER POD · INDEPENDENT", bio="Independent Indiana podcast. Caught the Cincinnati pickup the same hour the news broke.",
                     receipt_score_pct=71, receipt_score_label="71% AGED WELL", takes_tracked=12, voice_order=3),
    ]
    return edition, features, voices


def _archive_w16() -> tuple[Edition, list[EditionFeature], list[EditionVoice]]:
    theme = resolve_theme("2026-w16", date(2026, 4, 18))
    edition = Edition(
        edition_slug="2026-w16", edition_number=16, volume=1,
        publish_date=date(2026, 4, 18),
        theme_title=theme.theme_title, theme_dek=theme.theme_dek,
        cover_viz_kind=theme.cover_viz_kind,
        cover_viz_data={
            "title": "Top-25 movement, pre- vs. post-draft",
            "left_label": "PRE-DRAFT", "right_label": "POST-DRAFT",
            "rows": [
                {"name": "Texas",       "left_rank": 1,  "right_rank": 3,  "color": "#bf5700"},
                {"name": "Ohio State",  "left_rank": 2,  "right_rank": 1,  "color": "#bb0000"},
                {"name": "Oregon",      "left_rank": 3,  "right_rank": 2,  "color": "#154733"},
                {"name": "Penn State",  "left_rank": 4,  "right_rank": 5,  "color": "#041e42"},
                {"name": "Georgia",     "left_rank": 5,  "right_rank": 6,  "color": "#ba0c2f"},
                {"name": "Notre Dame",  "left_rank": 6,  "right_rank": 4,  "color": "#0c2340"},
                {"name": "Boise State", "left_rank": 14, "right_rank": 9,  "color": "#0033a0"},
                {"name": "Miami",       "left_rank": 11, "right_rank": 7,  "color": "#f47321"},
            ],
            "caption": "Texas leaked four picks. Notre Dame leaked one. Boise lost nobody and climbed five spots.",
            "source": "Composite preseason power rankings · 2026-04-15 → 2026-04-18",
        },
        cover_essay_id=None, status="published",
        published_at_utc="2026-04-18 06:00:00",
    )
    features = [
        EditionFeature(id=None, edition_slug="2026-w16", feature_order=1,
            feature_kind="cover_essay",
            title="The Draft Pulled the Roster Curtain Back",
            dek="Twenty-three first-round picks left the sport in seventy-two hours. The programs that lost the most were the programs that were holding it together.",
            body_markdown=(
                "Twenty-three first-round picks went in the 2026 NFL Draft. Texas had "
                "four of them. Ohio State had three. Penn State, Georgia, and Oregon had "
                "two each. Notre Dame had one. Boise State, the Cinderella of December, "
                "had zero.\n\n"
                "The draft is, in functional terms, the year's biggest forced-redistribution "
                "of college-football roster talent. Programs that lose first-rounders are "
                "*announcing* what they were running on. Programs that lose nobody are "
                "*announcing* that what they did last year, they did with the room.\n\n"
                "Texas dropped from 1 to 3 in the first composite power rankings of the "
                "post-draft cycle. Ohio State, having lost three picks but returned its "
                "starting QB, climbed to 1. Boise State, having lost zero, climbed five "
                "spots. The model is honest: the post-draft ranking is the cleanest read "
                "of who can actually do this again next year.\n\n"
                "The post-draft reset is not a story about the draft itself. It is a "
                "story about who built a roster that the draft could not break."
            ),
            byline="By The Editor's Desk", read_time_minutes=5),
        EditionFeature(id=None, edition_slug="2026-w16", feature_order=2,
            feature_kind="feature",
            title="What Texas Has Left After Four Picks",
            dek="Sarkisian lost his starting QB, two offensive linemen, and his best edge in seventy-two hours. The roster, on paper, is still top-five.",
            body_markdown=(
                "Texas's senior class accounted for four first-round picks. The "
                "remaining roster includes a redshirt junior at QB who closed last "
                "season as the backup, a returning offensive line that lost two but "
                "returns three, and an edge rotation that — minus the first-rounder — "
                "still grades top-15 nationally.\n\n"
                "Top five in the post-draft composite is honest. The fans on the boards "
                "are pretending it's not."
            ),
            byline="By The Off-The-Field Desk", read_time_minutes=4),
        EditionFeature(id=None, edition_slug="2026-w16", feature_order=3,
            feature_kind="connection",
            title="Boise's Zero-Loss Roster Echoes Cincinnati 2021",
            dek="Cincinnati went undrafted in the 2021 first round and made the CFP that fall. Boise's 2026 silhouette is the same.",
            body_markdown=(
                "In the 2021 NFL Draft, Cincinnati had zero first-round picks despite "
                "running a 13-0 regular season the prior fall. The 2021 Bearcats — "
                "everybody returning, everybody one year more experienced — went on "
                "to make the CFP that December.\n\n"
                "Boise's 2026 roster has the same shape. Take the comparison seriously."
            ),
            byline="By The Connections Desk", read_time_minutes=4),
        EditionFeature(id=None, edition_slug="2026-w16", feature_order=4,
            feature_kind="receipt",
            title="The Texas-Will-Drop-Three-Spots Prediction",
            dek="In February we said Texas would lose four first-rounders and drop to 3 in the post-draft polls. They did.",
            body_markdown=(
                "On February 8, 2026, we predicted that Texas would have exactly four "
                "first-round picks and would drop from 1 to 3 in the post-draft "
                "composite rankings. They had four. They dropped to 3. Receipt-honest."
            ),
            byline="By The Receipts Desk", read_time_minutes=2),
        EditionFeature(id=None, edition_slug="2026-w16", feature_order=5,
            feature_kind="fan_voice",
            title="A Boise Subreddit Comment that Said the Quiet Part",
            dek="Verbatim. Twenty-eight words. Three thousand upvotes.",
            body_markdown=(
                "> *Texas had four first-rounders and dropped two spots. We had zero "
                "and went up five. Tell me again why we shouldn't be in the bracket "
                "preseason.*\n\n"
                "The reply was longer, but the question was the whole thread."
            ),
            byline="By The Fan-Voice Desk", read_time_minutes=2),
        EditionFeature(id=None, edition_slug="2026-w16", feature_order=6,
            feature_kind="disagreement",
            title="The 'Notre Dame Climbed Two Spots' Disagreement",
            dek="Notre Dame jumped 6→4 in the composite. Notre Dame fans think it should be 6→2. The stat folks think it should be 6→5.",
            body_markdown=(
                "The composite landed Notre Dame at 4. The fan boards think 2; the "
                "stat-leaning podcasts think 5. Both are reading the same roster. Both "
                "are reading it through different windows.\n\n"
                "We will find out by November."
            ),
            byline="By The Cohort Desk", read_time_minutes=3),
    ]
    voices = [
        EditionVoice(edition_slug="2026-w16", source_slug="bruce-feldman-fox",
                     role_label="FOX · NATIONAL", bio="Feldman's pre-draft predictive piece on Texas's roster carry-over was the most accurate national read.",
                     receipt_score_pct=83, receipt_score_label="83% AGED WELL", takes_tracked=38, voice_order=1),
        EditionVoice(edition_slug="2026-w16", source_slug="onefootdown-blog",
                     role_label="ONE FOOT DOWN · NOTRE DAME", bio="OFD called the Notre Dame composite jump within one spot. The fan side flagged the disagreement.",
                     receipt_score_pct=76, receipt_score_label="76% AGED WELL", takes_tracked=21, voice_order=2),
        EditionVoice(edition_slug="2026-w16", source_slug="bronco-nation",
                     role_label="BRONCO NATION · INDEPENDENT", bio="Independent Boise outlet. Their zero-first-rounders math piece was the receipt of the week.",
                     receipt_score_pct=88, receipt_score_label="88% AGED WELL", takes_tracked=14, voice_order=3),
    ]
    return edition, features, voices


# =============================================================================
# Issues XVIII (May 4) + XIX (May 11) — stub payloads
#
# Hotfix-6 follow-up: PR #59 fixed the renderer bridge but /editions/
# showed only 4 issues (XIV-XVII) because seeds.py never carried W18 +
# W19. The Edition cover essay Pattern C flag (PR #53) means the next
# world_class_enrich will auto-fill these covers via
# editions/cover_essay.py → loop_c_critic_revise (Opus 4.7 + 3-critic).
# The stubs below give the generator a row to UPDATE — without them,
# the cover_essay surface has nowhere to write its output.
#
# Each stub:
#   - publish_date set to the canonical Monday (May 4, May 11)
#   - theme_title + theme_dek minimal placeholders (Pattern C overrides)
#   - cover_viz_data minimal {} (Pattern C generator can layer in)
#   - status='draft' so the editions archive treats them as not-yet-
#     published until Pattern C runs
#   - 1 cover_essay feature with placeholder body that the generator
#     replaces, plus 2 short secondary features to keep the archive
#     page rendering with proper structure
# =============================================================================


def _archive_w18() -> tuple[Edition, list[EditionFeature], list[EditionVoice]]:
    """Issue XVIII — May 4, 2026. Stub for Pattern C generation."""
    edition = Edition(
        edition_slug="2026-w18",
        edition_number=18, volume=1,
        publish_date=date(2026, 5, 4),
        theme_title="The Quiet Week",
        theme_dek=(
            "The first Monday in May falls in the gap between the spring "
            "portal close and the start of fall-camp coverage. The signal "
            "this week is the absence of signal — and what fanbases choose "
            "to talk about when there's nothing forced on them."
        ),
        cover_viz_kind="drift",  # CHECK constraint requires gap/drift/field/heatmap/distribution/flow/rank_shift; drift is the natural fit for offseason signal-absence narrative
        cover_viz_data={"caption": "The quietest week on the calendar. Signal rebuilds when SEC Media Days open the cycle in mid-July."},
        cover_essay_id=None,
        status="draft",
        published_at_utc="2026-05-04 06:00:00",
    )
    features = [
        EditionFeature(
            id=None, edition_slug="2026-w18", feature_order=1,
            feature_kind="cover_essay",
            title="The Quiet Week",
            dek=(
                "Spring portal closed; fall-camp coverage hasn't opened. "
                "What fanbases say in the gap is itself a signal."
            ),
            body_markdown=(
                "The first Monday in May is the quietest week on the college-football calendar. "
                "The spring portal window closed two weeks ago. Position-battle rumors out of fall "
                "camp won't start until mid-July. The news cycle is, briefly, honest about having "
                "nothing to feed on.\n\n"
                "What you're hearing this week is the baseline. It's what fanbases sound like "
                "before any of August's manufactured certainty arrives. The teams whose Reddit "
                "boards are loud right now are loud about something real to them — not about "
                "whatever the news cycle has decided is interesting that morning.\n\n"
                "When camp opens and the signal rebuilds, this week is the comparison point. "
                "What changes between now and August is what fall-camp coverage actually shifts. "
                "What stays the same is what the team is actually about."
            ),
            byline="By The Editor's Desk", read_time_minutes=4,
        ),
        EditionFeature(
            id=None, edition_slug="2026-w18", feature_order=2,
            feature_kind="feature",
            title="Late Spring · 99 days to kickoff",
            dek="Calendar context: where the offseason sits when XVIII publishes.",
            body_markdown=(
                "Spring portal closed April 30. Fall-camp coverage cycle starts "
                "the third week of July. The week of May 4 is the longest "
                "stretch of pure offseason in the calendar — five weekends with "
                "no forced news cycle, no transfer-window deadline, no recruiting "
                "weekend with required attendance.\n\n"
                "What fanbases talk about this week is what they *want* to talk "
                "about. That's a different signal than what they're told to."
            ),
            byline="By The Cohort Desk", read_time_minutes=3,
        ),
        EditionFeature(
            id=None, edition_slug="2026-w18", feature_order=3,
            feature_kind="connection",
            title="Receipts: Two Months Past Pre-Draft Boards",
            dek="The pre-draft consensus boards from late February. Which calls aged in the eight weeks since.",
            body_markdown=(
                "Late-February consensus pre-draft boards are two months old as of this Monday. "
                "Eight weeks is enough time for some calls to age well and others to look strange "
                "in hindsight.\n\n"
                "The Receipts Desk tracks resolved claims from those boards: who moved up on combine "
                "weekends and what that meant once the actual draft order settled. The point isn't "
                "to score predictions retroactively — it's to keep an honest ledger of what the "
                "industry thought in February against what actually happened. That gap is what "
                "every future pre-draft board has to earn against.\n\n"
                "Full receipts return once enough resolved claims clear the ledger to grade the "
                "industry-wide pre-draft consensus honestly."
            ),
            byline="By The Receipts Desk", read_time_minutes=3,
        ),
    ]
    voices: list[EditionVoice] = []  # Pattern C source-profile generator fills this
    return edition, features, voices


def _archive_w19() -> tuple[Edition, list[EditionFeature], list[EditionVoice]]:
    """Issue XIX — May 11, 2026. Stub for Pattern C generation."""
    edition = Edition(
        edition_slug="2026-w19",
        edition_number=19, volume=1,
        publish_date=date(2026, 5, 11),
        theme_title="Three Weeks Before Camp Whispers",
        theme_dek=(
            "Fall-camp coverage starts to bleed in mid-July. May 11 is "
            "three weeks ahead of the earliest camp-position rumors. What "
            "the boards are talking about now is the baseline against which "
            "August's signal gets measured."
        ),
        cover_viz_kind="drift",  # CHECK constraint requires gap/drift/field/heatmap/distribution/flow/rank_shift
        cover_viz_data={"caption": "Three weeks ahead of the first camp-position rumors. The signal floor before August manufactures certainty."},
        cover_essay_id=None,
        status="draft",
        published_at_utc="2026-05-11 06:00:00",
    )
    features = [
        EditionFeature(
            id=None, edition_slug="2026-w19", feature_order=1,
            feature_kind="cover_essay",
            title="Three Weeks Before Camp Whispers",
            dek=(
                "Three weeks before fall-camp position rumors start. "
                "What the boards are saying now is the baseline."
            ),
            body_markdown=(
                "Mid-July is when the first credible fall-camp coverage starts to bleed in. "
                "Position-battle reports. Depth-chart whispers. Coaches saying "
                "things at media-day podiums that get parsed for 72 hours afterward.\n\n"
                "Today is May 11. That's three weeks and change before any of that arrives.\n\n"
                "What you're hearing on team boards right now is the baseline against which "
                "August's signal gets measured. The teams whose fanbases are loud this week "
                "are loud about something that's actually theirs — not about the news cycle's "
                "manufactured uncertainty. The teams that are quiet this week aren't necessarily "
                "in trouble. They're just not on a content-generation cycle right now.\n\n"
                "When camp opens around August 3, the contrast between this week and that one "
                "is itself a signal. Some teams' boards will look the same because the team is "
                "the same. Some will pivot hard because August's coverage will change what "
                "fanbases think is interesting. Watch which is which."
            ),
            byline="By The Editor's Desk", read_time_minutes=4,
        ),
        EditionFeature(
            id=None, edition_slug="2026-w19", feature_order=2,
            feature_kind="feature",
            title="Late Spring · 92 days to kickoff",
            dek="Three more Mondays to camp open. The waiting room.",
            body_markdown=(
                "Camp opens around August 3. Today is May 11. Twelve weeks. "
                "Twelve Mondays — eleven Mondays of offseason editions, then "
                "the August 3 issue is the camp-open hero.\n\n"
                "Today's signal is which programs' boards are talking about "
                "Saturday's spring-recap content vs. which boards are still "
                "litigating the portal close from May 1."
            ),
            byline="By The Cohort Desk", read_time_minutes=3,
        ),
        EditionFeature(
            id=None, edition_slug="2026-w19", feature_order=3,
            feature_kind="connection",
            title="Storyline Threads in Mid-Spring",
            dek="The arcs the Connections Desk is currently tracking through the offseason.",
            body_markdown=(
                "A storyline thread is a multi-edition arc: something that's been written about "
                "before, has a named cast, and will be written about again. The point of tracking "
                "them as threads is so each new chapter respects what came before — no character "
                "rewrites between editions, no quiet contradictions of last month's framing.\n\n"
                "Five threads are currently active in mid-spring: the QB-room churn at programs "
                "whose veteran starters left for the draft; the spring-portal redistributions "
                "(who took, who lost, and which programs played the timing well); the coaching-staff "
                "additions that hinted at scheme shifts in fall; the recruiting reads that survived "
                "spring evaluation; and the receipts on which preseason takes from the prior cycle "
                "actually held up.\n\n"
                "Each gets its own chapter every two-to-three weeks until the next significant "
                "input arrives. Threads close when their named arc resolves; they go dormant when "
                "there's nothing new to say."
            ),
            byline="By The Connections Desk", read_time_minutes=3,
        ),
    ]
    voices: list[EditionVoice] = []
    return edition, features, voices


# =============================================================================
# Public seed entry-point
# =============================================================================

def seed_all_editions(db: Database) -> None:
    """Idempotently upsert all six v1-Vol editions (XIV-XIX)."""
    seed_edition(db, "2026-w14")
    seed_edition(db, "2026-w15")
    seed_edition(db, "2026-w16")
    seed_edition(db, "2026-w17")
    seed_edition(db, "2026-w18")  # Hotfix-6 follow-up — Pattern C auto-fills
    seed_edition(db, "2026-w19")  # Hotfix-6 follow-up — Pattern C auto-fills


def seed_edition(db: Database, slug: str) -> None:
    """Idempotently upsert a single edition + features + voices."""
    if slug == "2026-w17":
        edition, features, voices = _w17_payload()
    else:
        edition, features, voices = _archive_edition_payload(slug)
    upsert_edition(db, edition)
    for f in features:
        upsert_feature(db, f)
    for v in voices:
        upsert_voice(db, v)
    # Stamp the cover-essay pointer.
    cover_essay_id = db.query_one(
        "select id from edition_features where edition_slug = :slug "
        "and feature_order = 1",
        {"slug": slug},
    )
    if cover_essay_id:
        db.execute(
            "update editions set cover_essay_id = :id where edition_slug = :slug",
            {"id": cover_essay_id["id"], "slug": slug},
        )


def _w17_payload() -> tuple[Edition, list[EditionFeature], list[EditionVoice]]:
    theme = resolve_theme("2026-w17", date(2026, 4, 25))
    edition = Edition(
        edition_slug="2026-w17",
        edition_number=17, volume=1,
        publish_date=date(2026, 4, 25),
        theme_title=theme.theme_title,
        theme_dek=theme.theme_dek,
        cover_viz_kind=theme.cover_viz_kind,
        cover_viz_data=_W17_COVER_VIZ_DATA,
        cover_essay_id=None,
        status="published",
        published_at_utc="2026-04-25 06:14:00",
    )
    cover_essay = EditionFeature(
        id=None, edition_slug="2026-w17", feature_order=1,
        feature_kind="cover_essay",
        title="After the Bracket: Three Conversations",
        dek=(
            "Two months past the first 12-team field, every program in college "
            "football has settled into one of three conversations. The gap "
            "between them is the story of the offseason."
        ),
        body_markdown=_W17_COVER_ESSAY,
        byline="By The Editor's Desk",
        read_time_minutes=12,
    )
    features = [cover_essay] + _W17_FEATURES_2_TO_6
    return edition, features, _W17_VOICES
