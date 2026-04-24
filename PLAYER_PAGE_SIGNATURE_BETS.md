# Player Page — Signature Bets for the CFB Nerd (v2)

**Status:** Design brief, v2 · **Owner:** Kevin · **Date:** 2026-04-23
**Purpose:** make the player page specific, memorable, and earned-for-the-audience. This isn't "features to add" — it's the texture and voice that turn a competent stat page into something CFB-nerd Twitter posts screenshots of.
**Changes since v1:** dropped Page Confidence Score (internal scaffolding, not reader-facing); added Anti-Take Engine, Coaching Lineage, Scenario Explorer, Live Signal Flow, Narrative Arc; added a "voice in practice" section with real copy; added an anti-brief that names what we refuse to do.

## 1. Who we're writing for

The audience is the CFB fan who reads Bill Connelly's SP+ breakdowns on purpose, has opinions about EPA vs. success rate, knows what "havoc rate" means, and has thoughts on Kalshi's Heisman odds. They're not Football Outsiders subscribers necessarily — but they respect the work, enjoy the depth, and appreciate when a site refuses to insult their intelligence.

They are not casual; they're not degree-holding statisticians either. They're the r/CFB power-upvoter, the PFF subscriber-curious, the Paul Finebaum listener who also reads The Athletic, the MIT Sloan-adjacent fan who showed up for Bill Barnwell's podcast. They want:

- **Depth with a friendly expert guide.** Not gatekept, not dumbed down.
- **Context on every number.** "87 passer rating" means nothing. "87 passer rating (91st percentile, best by a ND QB since Quinn 2006)" is gold.
- **Honesty about uncertainty.** Confidence bands, sample sizes, "data below floor" — these are features, not bugs.
- **Stories.** Not stat dumps — arcs, narratives, turning points.
- **Something to share.** Every surface should produce a screenshot-worthy moment.
- **Hidden depth.** Easter eggs, rare-achievement markers, power-user shortcuts that reward lingering.
- **Our Fan Intelligence concepts exposed.** Respect Gap, Reality Gap, Belief Dial, Rival Heat, Cohort Divergence — these are the edge. Show them off.

What they already consume: Bill Connelly's SP+. Kalshi's CFB markets. CFBNumbers on Substack. Ryan Nanni's work. Stewart Mandel podcasts. PFF College Twitter. Inside texts from beat writers. Blog posts on Reddit.

Our page should feel like a permanent version of the stuff they already read.

## 2. The eight voice principles

These are non-negotiable. Every module, every cell, every pixel either honors them or doesn't ship.

1. **Numbers with provenance.** Every stat has a tiny `?` that opens a popover with: definition, cohort, sample size, how we computed it, where the data came from, when it updated. No unsourced numbers.
2. **Context over volume.** One stat with deep context beats ten stats without. If we can't rank-percentile-cohort it, we don't show it.
3. **Uncertainty honored, not hidden.** Low sample = muted color + "sample: 28" note. Missing data = "data below floor for G5 pressure stats" — not "N/A."
4. **Stories over snapshots.** Career arcs, season narratives, weekly trajectories. Timeline bars, milestone markers, "what changed" widgets.
5. **Community in, not just out.** Show what fans are saying, not just what analysts are saying. The Room, Rival Heat, Respect Gap — lean into them.
6. **Easter eggs for power users.** Rare badges, hidden tooltips, "drag to compare" interactions, keyboard shortcuts. Reward the fan who lingers.
7. **Every surface shareable.** If a stat doesn't screenshot well on a phone in 5 seconds, it's not finished. Baseball Savant's percentile cards are our north star — the screenshot IS the product.
8. **Own our own takes; don't hide behind aggregation.** When we have a view, state it. "Carr is the best pressure QB in the country" — say it. The data backs it. CFB Twitter respects confidence.

## 3. Voice in practice — what the page actually says

Voice principles are useless without examples. Here's the copy across key surfaces, concrete enough that Claude Code can pattern-match when implementing. Same grammar, same rhythm, every time.

### Hero identity strip
```
CJ CARR
Notre Dame · FBS Independents · Junior
6-3 · 210 lb · #13

[RETURNING · JR 2026]          [2025 HEISMAN FINALIST]
```

Two chips. First chip is present-tense status (offseason-aware). Second chip is the single best retrospective accolade, prefixed with the year. Three lines of identity; everything else is fingerprint cells.

### Phase banner
```
OFFSEASON · SPRING 2026 · DRAFT WEEK
```

Uppercase, `--fs-meta`, 0.08em tracking, accolade-gold. Calm. Factual. Never uses exclamation points. Only allowed emoji: `🔴` during the live-draft 72-hour window.

### Hero fingerprint cells (offseason · draft week)
Each cell: eyebrow label, bright tabular number, one-line interpretation. No fluff.

```
2025 CFB INDEX QB SCORE
87
Best by a Notre Dame QB since Brady Quinn 2006.
91st percentile, P4+ND starters, n=73.

2026 HEISMAN FUTURES
+450
Kalshi market favorite · up 160 bps since NC championship.
Implied probability 18.2%.

RETURNING VALUE
96
Top-decile returning starter nationally.
Coaching continuity + 90+ pct prior-season production.

COACHING CONTEXT
Year 2 OC
Mike Denbrock · 82 plays/gm prior stop · RPO-heavy spread.
Continuity bonus: top-10 offense among returning-OC teams.

PRESEASON WATCH LISTS
7 of 9
Heisman · Davey O'Brien · Manning · Maxwell · Walter Camp ·
AP preseason AA · Athlon · Phil Steele · Lindy's ← missing the last 2.
```

Note the rhythm: bright number, muted eyebrow, one-line interpretation, optional second line for cohort context.

### Signature Story (algorithmic, backend-driven)
```
SIGNATURE · 2025 FINAL
COMBINED WEPA PER PLAY
+0.402
#16 of 58 P4+ND QBs · 339 touches · Moderate confidence

The decision-making jumped from 47th percentile as a freshman to
83rd as a sophomore to 91st now. That trajectory is the story of
the year. Carr became a Heisman finalist by getting better at the
thing hardest to teach: knowing when not to throw it.

See how this was picked →
```

Narrative voice — one sentence says the stat, one sentence says what it means, one sentence earns the hyperlink.

### The Room on [Player]
```
THE ROOM ON CARR
Mood: Grounded Optimism
Belief Dial: 72 (high confidence · n=142 · sarcasm-risk low)

Own fans: "Grounded optimism. We've seen this before and we know
not to peak too early." [48 mentions]
Rivals: "Genuine fear. Michigan board is 63% fearful takes." [31]
National: "Third-highest discussion volume among returning QBs." [47]
Media: "Consensus preseason top-2 Heisman." [16]
```

Real fan voices (sarcasm-filtered, cited by cohort). Our aggregation wraps them but doesn't swallow them.

### Rival Radar
```
RIVAL RADAR
Michigan fans talk about Carr 4.2× more than any opposing QB
they've faced since 2018. It's a fixation.

Peak moment: 89 mentions in the 24 hours after Week 8's loss.
Rival sentiment: 48% fear · 31% grudging respect · 21% mockery.
Michigan Obsession Score: 83 (89th percentile in rival-heat
against ND QBs across the 15-year tracking era).

See what they're saying →
```

### Hot-Take card + its Anti-Take sibling
```
TODAY'S HOT TAKE
Carr's 3rd-down EPA (+0.51) is higher than every Heisman
winner's 3rd-down EPA since Joe Burrow 2019.

Defensibility: ✓ · sample n=91 · vs 2019–2024 Heisman cohort
See the math →

────────

BUT: Carr's number is inflated by 3 garbage-time conversions
against Ball State. Strip those and he drops to 4th-best
since 2019 — still elite, but not record-breaking. Sample
quality matters.
```

Always paired. Hot takes are confident; anti-takes are the honest counter. Sibling cards. Two-second read, loadbearing on trust.

### 2026 Outlook — short block example
```
2026 OUTLOOK
Projected Role: STARTER · HIGH CONFIDENCE
  Returning QB1 · zero QB transfer activity · spring reports
  describe him as "untouchable" on the depth chart.

Draft Grade: — (returning junior · not declared)

Team outlook: Notre Dame projected 10.5 wins · SP+ #7 · CFP
bubble team in most projection models.

Preseason Watch Lists: 7 of 9 majors (see list above).
```

Sentences. Not tables. Sentences.

### Achievement badge hover
```
🏆 MONEY DOWN
Top-3 nationally in 3rd-down EPA

Held by 12 active P4 QBs. 9% of all qualifying QBs since 2008.
Unlocked: Week 9 2025 vs Stanford (+4.1 single-game EPA).
Share this badge →
```

### Page-change log footer (ambient, for power users)
```
04/23 14:02 · The Room · cohort volumes refreshed (n=142 → n=156)
04/23 10:14 · 2026 Outlook · Davey O'Brien watch list added
04/22 18:30 · Rival Radar · Michigan obsession score updated
04/21 09:00 · Achievements · unlocked "Road Warrior"
```

Terminal-esque. Tail of last 5 updates. Shows the page is alive.

## 4. Signature bets — the 14 that matter most

Ranked by (impact on audience delight) × (novelty — nobody else does this). These are the features that make the page not merely good but *ours*.

### BET #1 — Rival Radar (new module, 5m tier)

**What:** a module surfacing how much the *rival fanbase* is fixating on this player. Unique to us — nobody else has it because nobody else has our cohort-segmented fan-intelligence pipeline.

**Content:**
- Rival-mention count, trailing 7d + 30d.
- Peak 24-hour moment with context: "89 mentions on Oct 8 after the Michigan State game."
- Relative fixation: "Rival fanbases mention Carr 4.2× more than any other opposing QB this season."
- Sentiment arc of rival mentions: fear vs mockery vs grudging respect (three-way stack chart across season).
- Rival "Obsession Score" 0-100, scaled against historical baseline. Canon players score 90+. Forgettable QBs score sub-10.
- Sub-tab: per-rival breakout for top-3 rivals (Michigan, USC, Stanford for ND).

**Why nerds love it:** it's *meta*. Not "how good is he" but "how much are his enemies thinking about him." A proxy for how much his existence shapes the sport's discourse. You cannot extract this from traditional stats.

### BET #2 — Hot-Take Engine (new widget, appears throughout the page)

**What:** auto-generated one-liner statistical hot-takes that are defensibly true and wild-sounding. Fuels screenshotting and r/CFB debate.

**Generation:** a rules engine scans the player's full metric profile and picks 3-5 candidate takes per day, ranked by novelty × defensibility. Each take is backed by a (rank, cohort, sample, methodology) quadruple. Never "technically true but misleading."

**Presentation:** one card per page, visible but not shouty. Click to see the math. Each take has a "share this" button that generates a screenshot-ready image with take + micro-chart + cfbindex.com watermark.

**Why this works:** CFB fans LIVE for these. Every take is a potential Twitter thread or Reddit post. Each one drives a new visitor to the page.

### BET #3 — Anti-Take Engine (sibling to Hot-Take)

**What:** the paired counter to every Hot-Take. Names the caveat — the garbage-time games, the weak cohort, the sample-size issue, the home/road asymmetry — that makes the hot take shakier than it looks.

**Presentation:** visually paired with the Hot-Take card, a quiet divider between them. Never more than 3 sentences.

**Why nerds love it:** it's the intellectual honesty move that 247 and ESPN can't pull off because their content economy punishes self-critique. We have no business model forcing us into hype, so we can be honest in public. That *is* the differentiator.

**Example:**
```
HOT TAKE: Carr's 3rd-down EPA is higher than every Heisman
winner since Burrow 2019.

ANTI-TAKE: 3 of his 12 big 3rd-down conversions came in the
4th quarter against Ball State (53% garbage-time context
per our in-play model). Strip those: he ranks 4th in the
cohort, not 1st. Still elite. Not record.
```

### BET #4 — Statistical Mirror Match (new module, 5m tier)

**What:** finds the historical player whose statistical fingerprint is most similar to this player's current fingerprint. Across the 15-year tracking era.

**Presentation:** a match card — headshot slot, name, team, year, brief context, similarity score (0-100). One line: `Closest historical match: Bo Nix, Oregon 2023 · 94% similar through Week 12 · Finished 3rd in Heisman · 1st-round NFL draft.`

**Method:** cosine similarity on a feature vector of percentile-normalized stats per position. Computed nightly.

**Extension:** "show me the top 10 matches" drawer with slider for similarity threshold. Click any match to open THAT player's historical page. Rabbit hole.

**Why nerds love it:** remember-when machine. Tells you what kind of player this is by analogy to one you already understand. Creates arguments.

### BET #5 — Fan Intelligence Glossary (ambient, page-wide)

**What:** every Fan Intelligence term — Respect Gap, Reality Gap, Belief Dial, Rival Heat, Cohesion, Sarcasm Risk, Swing, Main Character — has a tiny `?` icon next to the label. Tap opens a 60-word explainer with a micro-example.

**Design:** `?` is `--fs-meta` size, `--muted` color, inline next to the eyebrow. Hover/tap opens a native popover. On mobile, bottom sheet.

**Power-user bonus:** pressing `?` anywhere on the page opens a global FI glossary.

**Why nerds love it:** methodology transparency, on demand. Also: makes our proprietary concepts legible to first-time visitors without dumbing them down for returning power users.

### BET #6 — Weekly "What Changed" Diff

**What:** when a fan returns, show a compact "since your last visit" card.

**Content:**
- `+3 Heisman Heat` (or `−3`)
- `Up 2 rungs in Standing`
- `+14 mentions in The Room`
- `New in 2026 Outlook: Davey O'Brien preseason watch list`
- `1 new achievement unlocked: "Gunslinger"`

**Implementation:** client-side — localStorage record of "last-visited timestamp" + a page state hash that diffs against the snapshot.

**Why it works:** drives return visits. Fan checks Carr's page daily; the diff gives them a reason to keep doing it.

### BET #7 — Achievements (ambient, page-wide badges)

**What:** statistical achievements — rare-percentile, historical-milestone, novelty markers. Small gold badges on the page. Power users collect / compare.

**Sample achievements:**
- **Elite Pocket** — 95th+ pct pressure-adjusted EPA
- **Gunslinger** — 10+ TDs of 40+ yards in a season
- **Heisman Moment** — single-game EPA above threshold against top-15
- **Red Zone Surgeon** — 95th+ pct red-zone TD rate, min 30 att
- **Money Down** — top-3 nationally in 3rd-down EPA
- **Clutch Gene** — 95th+ pct 4th-quarter EPA in one-score games
- **Dual Threat** — top-25 in BOTH WEPA-passing AND WEPA-rushing
- **Rival-Slayer** — top EPA in rivalry games
- **Cold-Weather Stud** — 95th+ pct EPA when temp < 40°F
- **Road Warrior** — 95th+ pct EPA in true road games
- **The Record-Holder** — program-career or program-season record
- **Mirror-Match** — ≥95% similarity to a historical Heisman winner (unlocks via Mirror Match data)

**Presentation:** badges render as small gold medallions in a ribbon near Hero or inside 2026 Outlook. Hover shows criteria + unlock context. Click opens the unlock exhibit (the game/play/season). Each badge lists what percentile of all FBS QBs in the 15-year era hold it.

**Rarity discipline:** many achievements must be held by <10% of the cohort. Re-tune quarterly. Badge inflation is the failure mode.

**Why nerds love it:** video-game logic applied to CFB. Instantly shareable. Drives depth-of-engagement.

### BET #8 — The Signature Play (new small module)

**What:** for each game, surface THE play that best encodes the player's identity. Not the highlight-reel TD — the play that statistically most represents "what he does."

**Method:** signature score = EPA × novelty × situational weight × profile-fit. Per-game winner → that game's signature play. Season winner → THE signature play of the year.

**Presentation:** per-game card with quarter + down + distance + yard line + situation + play description + EPA + WPA. If we can get a broadcast still frame legally, include. Plain text is fine in v1.

**Why this works:** turns a career's worth of plays into a findable narrative. Users discover "oh, THIS is why he's great."

### BET #9 — Prediction Markets Woven Everywhere

**What:** Kalshi + PolyMarket + FanDuel ML/futures aren't their own module; embedded throughout wherever relevant.

- **Heisman Heat cell** — `Kalshi +450 · 18.2% implied · up 160 bps since NC championship`
- **Team Outlook cell** — `Team win total o/u 9.5 · Kalshi 58% over`
- **Individual prop markets** — `Passing yards o/u 285.5 vs. Miami · PolyMarket 52%`
- **Market-move widgets** — `Heisman odds down 15% since the spring practice reports. Why →`

**Framing:** markets are third-party signals, not gospel. Named sources, never weighted into our scores.

**Why nerds love it:** fans obsess over futures. Kalshi has a college-football-active community. Surfacing this inline makes the page feel like it knows the state of play.

### BET #10 — Cohort Divergence Map (embedded inside The Room)

**What:** instead of just showing four cohort dots (own / rival / national / media), expose sub-cohorts and visualize the full dispersion as a 2D scatter.

**Layout:** 2D plane — x-axis = belief (negative → positive), y-axis = intensity (calm → heated). Sub-cohorts plotted as dots, sized by mention volume.

**Sub-cohorts:**
- Own-team alumni / own-team students / own-team general
- Per rival team (Michigan, USC, Stanford as separate dots for ND)
- National fans (conf-aligned / neutral)
- National media vs local beat
- Gambling community (Reddit r/sportsbook + DraftKings chatter)
- Recruiting community (247/On3 boards)

**Engagement:** cohort dots pulse gently when their mention volume is rising. Hover reveals top quote from that cohort.

**Why nerds love it:** stratified data is catnip. The scatter instantly shows "own-team alumni love him, students are skeptical, Michigan fans are PANICKED, Stanford fans don't know he exists." These are stories.

### BET #11 — Coaching Lineage + System Context (new small module near Supporting Cast)

**What:** the coaching-context module. "Carr plays in Marcus Freeman's Year-3 offense, designed by OC Mike Denbrock, lineage Denbrock → Coleman → Meyer 2010 Ohio State." With system fingerprint: plays/gm, pass rate, explosive rate, tempo style.

**Content:**
- Head coach + years in seat + prior-school identity
- OC name + scheme family + lineage (3-deep where traceable) + system fingerprint stats
- DC name + scheme family (for two-way player context)
- What changed since last season (chip: `NEW OC · YEAR 1`, `SAME OC · YEAR 2`, etc.)
- Quiet comparison: "Denbrock's previous 3 QBs averaged +0.28 WEPA/play across 2 seasons; Carr posted +0.41 in Year 1 of the system."

**Why nerds love it:** scheme-family obsession is a real thing. The "RPO descended from Briles 2012" line is the kind of detail r/CFB power users know and expect. We surface it as a first-class citizen rather than a hidden footnote.

### BET #12 — Scenario Explorer (interactive)

**What:** a small interactive widget. "What does Carr need to do in the final 4 games to surpass Brady Quinn 2006?" With sliders.

**How it works:**
- Target selector: pick a historical benchmark (from Mirror Match suggestions or a search).
- Live sliders for Carr's remaining-game projections: pass yards, TD, INT, completion %.
- Real-time computation of the resulting career/season stat vs the benchmark.
- Visual: his projected trajectory line + the benchmark target line on the same chart.

**Use cases:** offseason "what if he comes back and posts Y"; in-season "what does he need the rest of the way to pass Z"; draft-window "what does his 2025 season look like against 2024's Heisman class."

**Why nerds love it:** gamifies their mental math. CFB nerds already run these scenarios in their head; we give them the calculator. Excellent offseason engagement.

**Build cost:** moderate — requires a front-end slider widget + backend scenario model. Punt to Phase S3 if needed.

### BET #13 — Live Signal Flow (top-of-page signal bar, event-driven)

**What:** when a player has a real-world news moment — portal entry, commit, injury, draft pick, All-American nod, program record broken, Heisman odds swing — the page lights up with a time-decaying signal bar at the top.

**Presentation:**
- Thin bar under the Hero. Accolade-gold left border. Tap-to-expand.
- Headline: "🔴 LIVE · CARR COMMITS TO RETURN FOR 2026 · 2h ago"
- Sub-line: "Heisman odds shifted +180 bps · rival fanbases heating up · 9 beat-writer articles in last hour"
- Decays over 72 hours: full energy → muted → hidden. No permanent badge.

**Triggers:**
- Portal entry / commit
- Injury report
- Draft declaration / pick / trade
- Preseason watch list inclusion
- All-America team selection
- Program record broken
- Heisman odds move > 100 bps in 24h
- Major news article publication (from beat feeds)

**Why nerds love it:** makes the page feel *alive*. A site they can refresh during a news moment and actually see something change. Otherwise-static player pages become real-time canvases during event windows. Builds the habit of checking us during news cycles.

### BET #14 — Narrative Arc Board (editorial, appears on retrospective seasons)

**What:** a 3-act synopsis of the player's season. Opinionated. Written (by an LLM from a template, or by Kevin manually for headline players).

**Example for Carr 2025:**
```
2025 SEASON IN 3 ACTS

Act I — Discovery (Weeks 1-4)
From preseason question mark to verified starter. The
Texas A&M game was the inflection: 3 TDs, 88th pct pressure
EPA, suddenly in the Heisman conversation.

Act II — Ascent (Weeks 5-9)
The stretch where he outperformed his profile. Peak
Heisman Heat of +12 after the Stanford game. The WEPA
curve broke toward historic.

Act III — Coronation (Weeks 10-13)
Heisman finalist at 22. NC championship run ended in
semifinals. The freshman-phenom narrative closed; the
multi-year-star narrative opened.
```

**Design:** three named acts with a week range, a one-line "inflection moment," and a 1-2 sentence synthesis each. Small, tight, highly readable.

**Why nerds love it:** opinionated editorial in a sea of stat dumps. Tells a STORY — what most CFB content (especially data-first content) doesn't do.

**Risk:** auto-generation quality. If the LLM writes generic filler, it ruins the feature. Start hand-written for the top-20 players; auto-generate for the long tail; flag-for-review workflow.

## 5. Smaller details that compound

Not signature bets, but each one makes the page feel DIFFERENT. Together they stack into texture.

1. **Tabular numerals everywhere.** Numbers are always tabular-nums, weight 600+. Label uppercase eyebrow at `--fs-meta`, 0.08em tracking.
2. **`~` prefix for small-sample data.** Tilde signals "we're showing this but don't trust it at 100%." e.g., `~72%` for a stat with sample 14.
3. **Inline confidence chips.** Every stat gets a confidence dot (green/yellow/grey) + tiny sample count. Not a separate "Page Confidence Score" module — just ambient, per-metric honesty.
4. **Era context everywhere.** "Best by a ND QB since 2012 (Everett Golson)" on every record-breaking stat. Auto-computed.
5. **Spark terminators.** Each trajectory spark ends in a shape that tells you the state: arrow (trending), dot (static), square (closed). Visual language.
6. **Opponent-strength stripe.** 1px gradient bar under game-level stats showing opponent strength. Green = top-25, orange = P5 mid, grey = G5, red = FCS. Instantly signals quality.
7. **Rival callout markers.** When a stat references a specific game, if it was against a rival, add a small rivalry icon with the two school colors crossed.
8. **"Since your last visit" timestamp.** Subtle topbar chip: "Last viewed 3 days ago — 2 updates since."
9. **Copy-the-badge.** Right-click any achievement badge → copy a shareable image card.
10. **Game-by-game navigator.** Left/right arrows per game-level module to scrub. Keyboard: `[` / `]`.
11. **"Only QB in history" detector.** When a player is the sole holder of a (stat, cohort, era) combination, call it out. "Only P4 QB with 10+ TDs of 40+ yards AND 90th+ pct pressure EPA in the 15-year era."
12. **Screenshot mode.** Keyboard `S` toggles a clean-view: hides nav/subnav, maximizes primary module, adds watermark. One tap → share-worthy image.
13. **Terminal-style page-change log in footer.** `04/23 14:02 — The Room · cohort volumes refreshed`. Tail of 5 recent updates. Power users love this.
14. **Cohort-match sparks.** Under every percentile bar, a tiny spark showing 10 closest-percentile peers. Hover reveals their names. Makes context tactile.
15. **The "Gilded Section."** One module per page gets a subtle gold top-border when it contains the page's most interesting data point (determined by novelty score). Signals "start reading here."
16. **Keyboard shortcuts for power users.** `?` = FI glossary. `G` + module initial = jump to module. `J`/`K` = next/prev module. `/` = focus peer search. `C` = copy page URL with current URL state. `S` = screenshot mode. `[` / `]` = prev/next game in game-scoped modules.
17. **Right-click context menu on any metric.** "Why this number?" · "Compare to another player..." · "Copy as tweet" · "Embed in my blog."
18. **The Draw-The-Line mini-game.** On trajectory cards, optional "draw your guess" before the real line reveals. Skip button always visible. Bottom-of-page anonymous leaderboard for session-accurate guesses. Cute, not core — ship in S4.
19. **Historical "this day" chip.** Subtle chip near Hero: "One year ago today: Carr's first career start (4 TDs vs. BC)." Nostalgic, memorable.
20. **Rivalry splits in Splits module.** A sub-row showing EPA-in-rivalry-games vs EPA-overall. "Against rivals: +0.52 EPA/play · Overall: +0.28. Top rivalry performer in ND history (15-year era)."

## 6. How this layers onto the 10-module canvas

Three net-new modules. The rest are ambient enhancements or sub-modules nested in existing ones.

| Signature Bet | Lives in |
|---|---|
| Rival Radar | NEW module, between The Room and 2026 Outlook |
| Hot-Take Engine + Anti-Take Engine | Ambient — paired card, one per page, rotated daily |
| Statistical Mirror Match | NEW small module, nested in Peer Comparator |
| FI Glossary | Ambient — `?` icons throughout |
| What Changed diff | Ambient — small card above Hero on return visits |
| Achievements | Ambient — badges ribbon near Hero or inside 2026 Outlook |
| Signature Play | NEW sub-module under Signature Story / 2025 Signature |
| Prediction Markets | Woven through Hero cells + 2026 Outlook + Team Outlook |
| Cohort Divergence Map | Enhancement to The Room (drawer or nested tab) |
| Coaching Lineage | NEW small module near Supporting Cast |
| Scenario Explorer | NEW interactive widget, appears in 2026 Outlook drawer |
| Live Signal Flow | Ambient — top-of-page event-driven bar |
| Narrative Arc Board | NEW small module, appears in retrospective season modules |

Net-new modules: Rival Radar, Statistical Mirror Match, Coaching Lineage, Narrative Arc Board, Signature Play sub-module. The base 10-module architecture stays intact.

## 7. The anti-brief — what we REFUSE to do to stay nerdy

If we're not disciplined, it's easy to drift into ESPN territory. Some explicit no-fly zones:

**No ad-supported content.** No ad slots, no sponsored takes, no affiliate links in prediction-market surfaces. The moment we get paid to hype a player, we lose the Anti-Take Engine's credibility.

**No star ratings.** "4 stars out of 5" flattens everything. Percentile against cohort is harder and better. Don't regress to stars.

**No "experts agree" framing.** We have our own takes. We don't hide behind composite-of-experts. If we cite analysts, we cite by name and show their track record.

**No generic CTA buttons.** "Learn more" is a sin. Every link earns its verb: "See the math" · "Open the peer comparator" · "Why we call it grounded optimism."

**No false precision.** Never write "Heisman odds: 18.237%." Round to what the signal supports. Usually integer percentile or two-digit decimal, never further.

**No stock photography.** If we don't have a player headshot, a monogram with team accent color is better than a generic placeholder. Monograms have identity; stock photos don't.

**No patronizing empty states.** "Oops, something went wrong!" is out. "Data below floor for G5 pressure stats — CFBD pbp not ingested. Next refresh 04/24." is in.

**No cookie walls, no newsletter pop-ups, no interstitials.** The reading experience is sacred. Email capture, if we ever do it, earns its place at the footer of an article they already loved.

**No hype adjectives.** "Generational," "all-time," "special" — only used when the data demonstrably supports them. "Best by a ND QB since Quinn" is better than "generational."

**No stat dumps.** If we can't give a stat (rank, percentile, cohort, era context), we don't ship it. A table of 40 raw stats isn't a feature, it's a failure of curation.

**No dark-mode-only.** The system is dark-mode-first, but light mode has to work. Some readers prefer it, some devices force it, some offices require it.

**No "download the app."** This is a website. Forever. Mobile web is good enough.

**No auto-playing anything.** Not audio, not video, not animations longer than 800ms. Delight motion is the 800ms `cubic-bezier(0.34, 1.56, 0.64, 1)` reserved for rare moments — max 3× per page.

**No clickbait hot-takes.** The Hot-Take Engine is a rules engine with defensibility gates. If a take fails the anti-take's own standards, it doesn't ship. Drama without substance is what we're replacing, not what we're doing.

## 8. Shipping strategy

Phased ordering. Ship the ambient enhancements first (they compound across modules), then net-new modules, then gamification, then polish.

**Phase S1 — Texture + voice (2 weeks after frontend migration completes)**
1. FI Glossary `?` icons throughout.
2. Inline confidence chips on every metric.
3. Era context ("best since …") on every record stat.
4. Tabular numerals + rhythm rule enforcement.
5. Weekly What-Changed diff.
6. Live Signal Flow bar (infrastructure).

Low-risk, high-impact. Makes the whole page feel legitimate.

**Phase S2 — The big bets (3-5 weeks)**
7. Hot-Take Engine + Anti-Take Engine (paired).
8. Rival Radar.
9. Statistical Mirror Match.
10. Achievements system.
11. Prediction Markets woven through Hero + Outlook cells.
12. Coaching Lineage module.

These are the differentiators. The ones fans screenshot.

**Phase S3 — Engagement layer (3-4 weeks)**
13. Cohort Divergence Map inside The Room.
14. Signature Play sub-module.
15. Scenario Explorer.
16. Narrative Arc Board (start hand-written for top-20 players).

Deepens engagement; doesn't make-or-break.

**Phase S4 — Polish + experiments (ongoing)**
17. Keyboard shortcuts + context menu.
18. Screenshot mode.
19. Draw-the-Line mini-game.
20. Historical "this day" chip.
21. Page-change log.
22. Gilded Section.
23. Everything else in §5 we haven't shipped yet.
24. Qualitative tests: are these features driving return visits? What's the top screenshotted module?

## 9. Voice tests the page must pass

Design criteria. Each testable.

1. **The Screenshot Test.** Take a screenshot of any 400×400 region of any module. Does it make sense standalone? Could it be shared on X without context and still communicate something real?
2. **The Nerd-Impress Test.** Show the page to a r/CFB power user. Do they say "oh, they show ___" at least 3 times (meaning we surfaced something they assumed sites don't track)?
3. **The Return-Daily Test.** Would this audience visit the page more than once per week during offseason? Which features specifically drive that?
4. **The Twitter-Argument Test.** Can a hot take from this page plausibly start a 100+ reply thread? How would we know?
5. **The Gateway Test.** Does a casual fan who lands on this page (via Twitter share) come away feeling smarter, not excluded?
6. **The Honest Test.** Can a reader, just from reading the page, identify a stat where we explicitly hedge with small sample size, cohort limits, or uncertainty? If no, we've hidden our honesty.
7. **The Canon Test.** If Carr becomes a Heisman winner + top-5 pick, is this page a permanent historical record worth linking to in 2040?
8. **The Anti-ESPN Test.** Pick a random module. Is it something ESPN would ship? If yes, we've drifted. Go back.

## 10. Open questions

1. **Hot-take generation QA.** The rules engine must never produce misleading takes. Who QAs them? Ship a "flag this take" button; Kevin reviews weekly. Set a ceiling — if the weekly flag rate > 3%, the generator holds and we audit.
2. **Anti-Take authenticity.** Can the Anti-Take engine actually find the honest caveat, or does it produce generic "but actually" boilerplate? Start with hand-authored anti-take templates for the top-20 players; let the engine learn from them; auto-generate for the long tail with a confidence threshold.
3. **Achievement inflation.** If every player has 7 achievements, none feel special. Rarity-gating matters — many achievements must be held by <10% of cohort. Re-tune quarterly.
4. **Mirror Match false positives.** Statistical similarity can land weird matches. Add guardrails: min-sample, exclude sub-50th-pct matches, show similarity score honestly.
5. **Prediction-market legal framing.** Showing Kalshi/PolyMarket odds is fine. Showing sportsbook ML odds in regulated states is more sensitive. Punt by stating market names + linking out. Don't embed bet slips.
6. **Cohort-slicing feasibility.** Sub-cohort breakdowns ("own-team alumni vs. students") require mention-author metadata we may not always have. Start with the four top-level cohorts; add sub-cohorts as data allows.
7. **Signature Play video rights.** Full broadcast highlight reuse is a licensing nightmare. Static still frames from public broadcasts + play-description text may be the ceiling in v1.
8. **Narrative Arc authoring.** Hand-written for top-20 is fine for v1. Auto-generation is where quality can drop; need strict gating (confidence threshold + template library + flag-for-review).
9. **Live Signal Flow event-firing.** Which events qualify? Editorial judgment needed. Start with a strict whitelist (portal, draft, Heisman odds swing > 100 bps in 24h, watch-list inclusion, program record). Expand cautiously.
10. **Scenario Explorer scope creep.** This can eat weeks if we're not careful. Ship v1 with two scenarios only: "what does he need to surpass historical benchmark X" and "what if he maintains his current pace." Add more if usage data warrants.

## 11. Reading-tier discipline — this is the guardrail

The signature bets are additive only if they honor the four reading tiers that the v5 system already locks in. A feature that makes power users happy but drowns a 5-second reader is a failure, not a feature.

Every bet must either (a) have a natural 5s headline + a 30s expansion + a 5m deep read, or (b) live entirely behind progressive disclosure (drawer, tab, hover, click) so a casual reader never sees it unless they want to. No bet may crowd the 5s or 30s view.

### Tier assignments — every bet mapped

| Bet | 5s (vibe) | 30s (gist) | 5m (investigation) | Deep (reference) |
|---|---|---|---|---|
| Rival Radar | — (not visible) | One-sentence lede: "Rivals fixate on Carr 4.2× normal" | Full module: per-rival scatter + sentiment arc | Sub-cohort quotes + historical obsession timelines |
| Hot-Take Engine | One line: the take itself | The take + its defensibility tag | Click-through to the math | Full cohort / sample / methodology |
| Anti-Take Engine | — (paired with Hot-Take) | Quiet paragraph under the hot-take | The full caveat with stripped-sample version | Alternate cohort framings |
| Mirror Match | — | One line: "Closest match: Bo Nix 2023 · 94%" | Full peer card with context | Top-10 matches drawer with similarity slider |
| FI Glossary | — (passive) | `?` icon visible but dormant | Opens on tap | Full methodology page |
| What Changed diff | Small card above Hero on return | Full diff with 3-5 bullets | Click-through to what changed and why | Changelog history |
| Achievements | Gold badges visible in Hero ribbon | Hover reveals names | Criteria + unlock context + rarity | Full badge index cross-player |
| Signature Play | — | — | Per-game card | Full play-by-play + signature-score math |
| Prediction Markets | Hero cell: "Kalshi +450" | Trajectory direction + implied % | Market-move context | Full market history |
| Cohort Divergence Map | — | — | Full 2D scatter in Room drawer | Per-sub-cohort quote mining |
| Coaching Lineage | Chip in Hero: "Yr 2 OC" | Summary line in Supporting Cast | Full lineage + system fingerprint | Scheme genealogy tree |
| Scenario Explorer | — | — | Drawer in 2026 Outlook | Full slider-based scenario model |
| Live Signal Flow | Top-of-page bar | Headline + sub-line | Click-through to article / context | Event timeline |
| Narrative Arc Board | Act titles visible as headers | Full 3-act read | Per-act inflection play | — |

Read left to right: if a bet doesn't have a 5s or 30s row, it's properly tucked behind disclosure and won't clutter the top-read. If a bet has ALL four rows, its 5s version had better be tight.

### The 5-second experience, enumerated

A casual fan hits Carr's page. Phone screen, 375px. Thumb distance. In five seconds they see, in order:

1. Phase banner: `OFFSEASON · SPRING 2026 · DRAFT WEEK` — they know what season it is.
2. `CJ CARR` in display type — they know who.
3. `Notre Dame · Junior · Returning · 2025 Heisman Finalist` — they know the frame.
4. `87` — the CFB Index QB Score, the single loudest number. Bright, tabular, unmistakable.
5. Gold accolade ribbon with 3-4 achievement badges — they see he has done rare things.
6. Today's Hot-Take card: "Carr's 3rd-down EPA is higher than every Heisman winner since Burrow 2019." One line. Memorable.

That's it. Six surfaces. No jargon required. No click required. They have a feeling — this is an elite, returning, decorated QB who does one specific thing better than almost anyone in a decade.

If a bet or module pushes any of those six surfaces off the first-fold, we cut that bet.

### The 30-second experience, enumerated

Same visitor gives it 30 seconds. They scroll once.

7. Hero fingerprint cells: `2025 CFB Index Score 87 · 2026 Heisman Futures +450 · Returning Value 96 · Coaching Context Year 2 OC · Preseason Watch Lists 7 of 9`. Five cells. Each with a one-line interpretation.
8. The Room on Carr: mood chip (`Grounded Optimism`), belief dial at 72. They see what fans think.
9. Rival Radar headline sentence: "Michigan fans talk about Carr 4.2× more than any opposing QB since 2018." They see he's a threat other fanbases respect (or fear).
10. 2026 Outlook: "Projected starter, no transfer risk, Heisman favorite per Kalshi." They see what's coming.

Thirty seconds in, they know: who he is, how he played, what fans think, what rivals think, what's next. That's a rich picture without a single chart to parse.

### The beginner gateway — what we do for the non-expert

The v5 system already has multiple beginner-safety patterns; the signature bets must not undo them. Reminders:

- **Every Fan Intelligence term has a `?` glossary icon.** A beginner who doesn't know what "Belief Dial" means taps once; they learn in 60 words. Then they keep reading, not bounced.
- **Every number has its cohort and era context.** `87` means nothing; `87 (91st pct, best by an ND QB since Quinn 2006)` means something to anyone.
- **Hot Takes are the gateway drug.** A well-written hot take educates as it entertains. "3rd-down EPA" is a scary term; "his performance on 3rd down is better than any Heisman winner in six years" is a sentence anyone reads.
- **No gate-kept acronyms.** First use of any acronym expands: `WEPA (Weighted Expected Points Added)`. After first use we can shorten. Every module is self-contained enough that a user landing from a deep link gets their first use too.
- **Graceful degradation for missing context.** A beginner doesn't know what "88th percentile" means without a reference. We always pair percentile with a natural-language translation: "88th percentile — better than 88% of P4 QBs."
- **Don't hide the 5s read behind scroll.** On mobile, the six 5s surfaces fit above the fold of a 6" phone. We do not take space above the fold to advertise the 5m/deep features.

### The expert gateway — what we do for the power user

Experts will find the deep content; the signature bets make sure they find it fast and reward them when they linger:

- **Keyboard shortcuts.** `?` glossary · `J`/`K` next/prev module · `G`+module for direct jump · `/` focus peer search. Experts learn this in one session.
- **Right-click context menu.** Any metric — "Why this number?" · "Compare to another player..." · "Copy as tweet" · "Embed in my blog." Power-user UI that respects their time.
- **Drill-ins everywhere.** Every number, badge, cohort, and chart opens a deeper exhibit on click. No dead ends.
- **Screenshot mode.** `S` key — clean-view. Experts share screenshots; we make it one tap.
- **Methodology page link from every module.** Never hidden in a footer.
- **Page-change log at footer.** Visible tail of recent updates. Power users appreciate knowing when data refreshed.

### The two failure modes we're avoiding

**Failure mode A — the stat dump.** A page packed with 12 modules × 8 stats each. Overwhelming. No hierarchy. This is what ESPN, 247, and Sports Reference all fail at. Our answer: progressive disclosure, reading tiers, and relentless focus on the 5s and 30s experiences.

**Failure mode B — the esoteric oasis.** A page so advanced that only stat-Twitter can read it. Feels like a gated community. This is what Football Outsiders and some PFF content drifts toward. Our answer: every Fan Intelligence term glossed on demand, every percentile paired with natural-language context, every jargon-first sentence followed by a plain-English sibling.

The target is between the two: a page that feels simple to a beginner and inexhaustible to an expert, because both are looking at the same surface — just at different depths.

## 12. The one sentence (v2)

A CFB nerd visits a player page on this site and comes away with three hot takes plus their honest counters, one screenshot-worthy moment, one rabbit hole to dig into, one methodology footnote they trust, a badge they've never seen before, and a reason to come back tomorrow — all wrapped in design restraint that treats them like the expert they are.
