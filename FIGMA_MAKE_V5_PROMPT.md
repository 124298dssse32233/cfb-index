# Figma Make Prompt — Fan Intelligence Hub, Version 5

> Paste the **block below the horizontal rule** into Figma Make as your next prompt on the "Fan Intelligence Hub Design" project. Do not edit it before pasting. Everything above the rule is context for you, the human, not for Figma Make.

## Notes for Kevin (skip if pasting)

- V4 is a legitimate A−. The editorial framing, Mood Index flagship, Hype vs Reality matrix, Index Cards, and the commiseration block are all at or near publication quality.
- V5's job is *finishing*, not redesigning. The prompt below is tightly scoped: ship the taxonomy upgrade, ship three missing flagship modules (Mood Ticker / Rivalry Obsession Matrix / Lexicon of the Week), fix the dozen visible chart and copy bugs, and close the editorial-voice gaps.
- The prompt ends with a "do not regress" list that is load-bearing. Without it Figma Make tends to silently swap typography, introduce new accent colors, or add decoration that breaks the system.

---

# PROMPT FOR FIGMA MAKE

You are iterating on the existing Fan Intelligence Hub Design (Version 4). This is a **targeted polish pass** — do not redesign, do not restructure the page, do not change the page-level color or typography system. Keep every section that currently exists. Add the three new sections specified. Apply every polish fix in this prompt.

## What this page is

The Fan Intelligence Hub is the signature weekly "issue" of **The CFB Index** — a data-driven college football publication. It is styled as a print editorial publication that happens to run on live data. Volume/Issue/Model Week numbering in the masthead. Weekly cadence ("Next issue Wednesday 9AM ET"). Byline attributes authorship to the model and editorship to the staff. The editorial voice sits between Bloomberg Businessweek and The Ringer.

## Keep every one of these (do not regress)

1. **The warm-ink/bone-paper neutral pair.** Warm ink `#0B0F14`, bone paper `#F3EEE4`. No pure black, no pure white on any body background.
2. **One accent color only: amber `#E0A300`.** Used exclusively for freshness/motion signals — live-dot, positive deltas, section eyebrow labels, footer links, section numbering emphasis. Amber does not appear on decoration, backgrounds, cards, buttons, chart fills, or chrome.
3. **Alert red `#B7281D`.** Used only for alarming semantic signals (sharp negative delta, critical state). Never as a decorative color.
4. **Team colors are data ink only.** They appear on chart lines/points, team chip helmet-circles, Index Card left stripes, and archetype card team chips. They never appear on chrome (nav, buttons, headers, footer, section backgrounds, body text).
5. **Three-voice typography.**
   - Condensed display (Druk / GT Flexa / Bebas): headlines, big stats, quadrant words. Bold weight only.
   - Editorial serif (Tiempos / Source Serif 4): body prose, italic captions, pull quotes, editor's notes, commiseration prose.
   - Tabular mono (IBM Plex Mono / JetBrains Mono): masthead lines, metadata rows, axis labels, signature phrases in archetype cards, delta chips, section numbering (`N° 01`, `N° 02`, etc.). Must use `font-variant-numeric: tabular-nums` wherever numbers align.
6. **Masthead strip (top dark bar).** Left: `THE CFB INDEX · FAN INTELLIGENCE · VOL V · N° 047 · MODEL WEEK 21`. Right: `22 APR 2026 · UPDATED 22M AGO ●` (amber dot).
7. **Primary nav** (light bone bg): Rankings · Matchups · Teams · Players · Hub · Archive · About. Hub is the current section — amber underline only, no amber fill, no amber text.
8. **N° numbering as wayfinding.** Every flagship section is labeled `N° 01 · THE SIGNATURE CHART`, `N° 02 · THE TICKER`, etc. V5 must renumber to be contiguous (no gaps).
9. **Asymmetric 60/40 cover layout** — condensed display headline on the left ~60%, chart on the right ~40%.
10. **`— the staff` signoff** style on Editor's Note and commiseration block.
11. **Footer data-scope line + changelog link + "Next issue Wednesday 9AM ET" cadence signal.**
12. **Index Cards format.** Team-color left stripe, mono-caps masthead line, condensed display headline, huge stat, editorial body, italic signature line, team chip bottom-right.
13. **Commiseration block ("For the Michigan fans who are still here")** — keep exactly as is. Dark bg (warm ink), serif letter body, three-word benediction close, `— the staff · 22 Apr 2026`.

---

## Section-by-section changes

### Masthead strip (top)

- Keep content. No changes.

### Primary nav

- Add a subtle `Issue N° 046 →` link on the far right of the nav (same row as About), with a `← N° 048 preview` on the opposite side when available. These are prev/next-issue chevrons. The Archive link remains in the footer.
- Add a `Subscribe` text link (not a button) in the far-right position. Hairline style, underline on hover only. Leads to a lightbox with a single email field and "Delivered Wednesdays, 9AM ET" microcopy.

### Cover hero ("Michigan's Belief Is At A Decade Low")

Keep the current layout. Apply these polish fixes:

1. **Color Michigan's chart line in Michigan blue (`#00274C`) with a maize endpoint dot (`#FFCB05`).** Currently the line renders near-ink navy — undifferentiated from generic line color.
2. **Add an endpoint label** at the rightmost data point: a small maize-filled circle, and to its right in mono: `MICH 58`.
3. **Add a vertical tick at Mar 14** (where Michigan's line crosses the 10-year average dashed line). Two-word annotation, mono, italic, editorial voice: `Moore presser`.
4. **Anchor the "10-year average" label** to the right endpoint of the dashed line, inside the chart frame. Do not let it float.
5. **Straighten x-axis date labels.** Feb 15 / Feb 22 / Mar 1 / … / Apr 22 should render horizontal at this chart width.
6. **Add a chart-level byline** under the italic serif caption, in mono micro: `Chart by The Index Desk · Model: power-resume-v1.3.2`.
7. **Add a "Also reading this week" rail** below the cover chart, inside the right column. Three items, mono-caps eyebrow (`ALSO READING`), then three one-line teasers separated by `·` bullets: `Oregon passes Alabama · The quiet Iowa floor · Nebraska "we're back" at 47,392`. Each is a link.

### Byline + pull quote

Keep. Apply:
- **Pull quote gets a left hairline rule** (0.5px, warm ink at 24% opacity) — tightens it into a proper editorial pull.

### Editor's Note

- **Narrow the measure to ~60–68 characters per line.** Currently the column is too wide for comfortable serif reading.
- **Add a 3-line serif drop cap** on the first letter (`T` of "This week we watch Michigan…"). Warm ink, condensed display face, aligned to the top baseline.
- **Append a date to the signoff** for consistency with the commiseration block: `— the staff · 22 Apr 2026`.

### N° 01 — The Fanbase Mood Index

Keep the chart. Apply these polish fixes:

1. **Fix the two-reds problem.** Georgia, Alabama, and Ohio State all render in red hues right now — Alabama and Ohio State are visually indistinguishable. Render Alabama in its houndstooth-gray secondary brand (`#828A8F`) on this chart only, so it reads distinct from Ohio State's scarlet. Alternatively, add a second encoding: SEC schools solid line, B1G schools with a 2px dash.
2. **Move the `playoff confidence` reference line label** to chart-left whitespace (just inside the y-axis), not the right edge where two team lines cross through it.
3. **Color the delta chips semantically.** Positive deltas (`+2`, `+3`, `+5`) in amber. Negative deltas (`-6`, `-15`) in alert red `#B7281D`. Currently all render amber regardless of sign.
4. **Downsize team chips in the right rail from ~28px to ~20px.** The list should read as an index, not as a second chart.
5. **Make axis labels mono** with `font-variant-numeric: tabular-nums`. Currently the axis numerals don't match the rest of the data voice.

### N° 02 — THE TICKER (new section)

Insert immediately below N° 01, above the Hype vs Reality section.

- Full-width horizontal strip. Warm ink on bone paper.
- Eyebrow: `N° 02 · THE TICKER`.
- Condensed display headline: `THIS WEEK'S BIGGEST MOOD MOVERS`.
- Serif dek (one line): `Ten fanbases whose belief shifted hardest in the last seven days.`
- **Ten-column horizontal grid** of team pill entries, sorted left-to-right from biggest gainer to biggest loser. Each pill:
  - Team chip (20px helmet circle).
  - Team abbreviation in mono caps (e.g., `ORE`).
  - Current Mood Index in condensed display (`87`).
  - Delta chip in mono, amber for positive, alert red for negative (`+5`, `-15`).
  - One-line cause attribution in serif italic micro (`· portal win`, `· Moore presser`, `· spring game`).
- Editorial caption below in italic serif: `The top five are gaining on coach news; the bottom five are losing on a single press conference each.`
- Methodology row in mono micro: `n = 340K conversations over 7d · bot-filtered · updated 22m ago`.

### N° 03 — Hype vs Reality

Keep the matrix. Apply these fixes:

1. **Fix the Nebraska annotation truncation.** Change text to `Nebraska — peak delusion.` Fits in the current box.
2. **Fix the Michigan annotation.** Change text to `Michigan — underrated by its own.`
3. **Keep `SLEEPING GIANT` inside the chart bounds.** Either scale the ghost display type down ~15%, or mask to chart bounds. Same for the other three quadrant words — ensure no overflow.
4. **Rotate the `Fan Hype Level` y-axis title** to true vertical (90° CCW) or move it to an above-left corner label `Y: Fan Hype · X: Model Reality`.
5. **Add exactly one more annotation**: a leader line to the position `(Michigan reality 83, Michigan hype 50)` currently labeled, and a parallel leader line to the position cluster near `(PSU, ND, A&M)` with label `Cautious middle: schools whose fanbases track their teams.`
6. **Keep the dark-mode treatment.** This section differentiates visually from the rest of the issue and that differentiation is load-bearing.

### N° 04 — The Taxonomy (major upgrade)

Rename the section header from `THE EIGHT FANBASES OF COLLEGE FOOTBALL` to either `THE EIGHTEEN FANBASES OF COLLEGE FOOTBALL` or (preferred) `A TAXONOMY OF FANDOM`.

Update the dek to:
> Every FBS fanbase sorts into one of eighteen primary archetypes. Primary archetype shows the team's current competitive-emotional state; modifiers add structural and cultural context. Classification is probabilistic.

Ship **18 primary archetype cards**. The 8 existing plus 10 more:

**Keep from V4:**
1. The Anxious Dynasty
2. The Perpetual Believer
3. The Wounded Giant
4. The Hopeful Uprising
5. The Quiet Professional
6. The Identity-Crisis Blueblood
7. The Content Mid-Major
8. The Generational Hope

**Add in V5:**
9. **The Newly Crowned** — programs that just broke through (historic first playoff berth, first major title). Fans oscillate between disbelief and entitlement. Signature phrase: *"We belong here now."* Example: Washington 2023-24, TCU 2022-23 (briefly).
10. **The Stockholm Syndrome** — fanbases of programs with no realistic ceiling who love their team anyway. The fandom is the point; the results are not. Signature phrase: *"At least we're still Mississippi State."* Example: Mississippi State, Vanderbilt, Kansas (football, historically).
11. **The Service Academy** — institutional fans whose identity is tied to the school's mission, not its win total. Signature phrase: *"Beat Navy."* Example: Army, Navy, Air Force.
12. **The Coach Cult** — fanbase's entire emotional state rises and falls with a single figure. Without the coach, the fandom is unstable. Signature phrase: *"In Coach we trust."* Example: Deion's Colorado, Belichick's UNC, historically Saban's Alabama.
13. **The HBCU Standard** — fans whose pride is cultural and historical, with competitive expectations calibrated against FBS peers rather than national titles. Signature phrase: *"The Classic is the season."* Example: Jackson State, Howard, Grambling.
14. **The Mercenary** — fans who adopted the program because of NIL/coaching-era arbitrage. Recent ascension, uncertain half-life. Signature phrase: *"We paid for this."* Example: Tennessee post-Heupel, Colorado post-Prime (this is distinct from Coach Cult — the mercenary fandom follows the money, not the man).
15. **The Celebrity Appointment** — programs whose fanbase is getting national attention for the first time because a famous person is running things. Signature phrase: *"You watching this?"* Example: Colorado 2023, UNC 2025-.
16. **The Petulant Blueblood** — historic blueblood whose fanbase is actively angry at its own program for not being good enough. Signature phrase: *"This is unacceptable."* Example: Texas (pre-2022), USC (2020-2023), Nebraska (structurally).
17. **The Regional Identity** — fans for whom the team is a proxy for a state, a city, or a region. Signature phrase: *"This is who we are."* Example: Iowa State, West Virginia, Boise State.
18. **The Sleeper** — programs with quiet, sustained excellence whose fanbase hasn't fully caught up to their ceiling. Signature phrase: *"Wait, we're this good?"* Example: BYU post-B12 entry, SMU 2024-.

**Add a "Modifiers" strip to every card.** Below the signature phrase, a thin mono-caps line: `MODIFIERS` followed by 0–3 applicable modifier chips from this set:

- `State Identity` — the team is the state's team.
- `Rivalry-Defined` — fandom is organized around a single opponent.
- `Faith-Based` — religious affiliation is part of the identity (BYU, Notre Dame, Baylor).
- `Academic Cousin` — the fandom polices academic identity as much as athletic (Stanford, Duke, Northwestern).
- `Sibling School` — paired with one other school in the state that they define themselves against (Michigan/MSU, UGA/GT, UF/FSU).
- `Scorned Ex` — fandom left a conference under bad terms (Texas, A&M, Nebraska, Oklahoma).
- `Pedigree-Entitled` — historic success creates a permanent floor of expectations.
- `Independent` — no conference affiliation to default their identity (Notre Dame, BYU historically).

Example card rendering:

> **THE IDENTITY-CRISIS BLUEBLOOD**
> Historic programs in the middle of a traumatic transition. The old identity is gone. The new identity has not yet formed. The fanbase is lost.
>
> [MICH 96%] [FSU 92%]
>
> SIGNATURE PHRASE
> *"What are we now?"*
>
> MODIFIERS
> [Sibling School] [Academic Cousin] [Pedigree-Entitled]
>
> ━ 5-season migration sparkline ━

**Add a migration sparkline** at the bottom of each card: a 5-dot sequence (2021 → 2022 → 2023 → 2024 → 2025) where each dot is colored by that year's primary archetype. On hover (or in the mockup, as the default state of one featured card), label each dot. This turns the taxonomy from static into dynamic.

Add a section-closer below the 18-card grid: one full-width editorial paragraph in serif, italic, centered, ~85ch measure:
> *Archetypes are probabilistic, not permanent. Half of the 2024 Hopeful Uprisings are now Wounded Giants. The Newly Crowned have a median half-life of 3.1 seasons. The Quiet Professionals have a half-life of forever.*

### N° 05 — THE RIVALRY OBSESSION MATRIX (new section)

Insert between the Taxonomy (N° 04) and the Index Cards section. Warm ink text on bone paper.

- Eyebrow: `N° 05 · THE RIVALRY`.
- Condensed display headline: `WHO'S MORE OBSESSED WITH WHOM`.
- Serif dek (two lines): `For every rivalry, one fanbase mentions the other more than they get mentioned back. The ratio is the tell. When it flips, something has changed.`
- **Small-multiples grid, 3 columns × 4 rows = 12 rivalries.** Each cell is a compact visualization:
  - Two team chips side-by-side, connected by a horizontal bar split into two proportional segments in the teams' colors.
  - Above the bar: rivalry name in condensed display (e.g., `THE GAME`, `RED RIVER`, `IRON BOWL`, `CIVIL WAR`).
  - Below the bar: the ratio in mono (`Michigan mentions OSU 2.6× as often as OSU mentions Michigan`) and a one-line editorial take in serif italic (`the little brother hasn't noticed they're little again`).
- Rivalries to include:
  1. Michigan / Ohio State → 2.6× (Mich leans in)
  2. Texas / Oklahoma → 1.1× (roughly even)
  3. Alabama / Auburn → 1.8× (Auburn leans in)
  4. Florida / Georgia → 1.4× (Florida leans in)
  5. USC / Notre Dame → 2.2× (USC leans in)
  6. Iowa / Iowa State → 3.1× (Iowa State leans in — hardest in the sport)
  7. Oregon / Washington → 1.3× (Oregon leans in)
  8. Stanford / Cal → 1.7× (Stanford leans in)
  9. Army / Navy → 1.0× (perfectly even, mythic)
  10. Clemson / South Carolina → 2.4× (Carolina leans in)
  11. Penn State / Pitt → 4.2× (Pitt leans in)
  12. FSU / Miami → 1.9× (FSU leans in)
- Editorial caption below the grid: *"The ratio is the relationship. An asymmetric ratio means the relationship itself is asymmetric — one side still treats it as a rivalry, the other has moved on."*

### N° 06 — LEXICON OF THE WEEK (new section)

Insert between the Rivalry Obsession Matrix (N° 05) and the Index Cards section. Full-width editorial feature, bone paper background.

- Eyebrow: `N° 06 · THE LEXICON`.
- Condensed display headline: `"5-STAR TRUST ME"`.
- Serif dek (one line): `The phrase that spiked in Ohio State fan conversations this week, and what it means.`
- **Asymmetric two-column layout** (60% editorial text, 40% chart):
  - **Left column (editorial):** A three-paragraph magazine-style explainer in serif. First paragraph: what the phrase is and who says it. Second paragraph: how it spiked (+340% week-over-week, originated in the OSU247 subreddit after five-star commit Julian Sayin's spring game press availability). Third paragraph: what it replaces (the dying phrase `in Day we trust`).
  - **Right column (chart):** A 4-week sparkline of phrase-frequency with the spike labeled. Below the sparkline: three "field recording" quote callouts in mono italic:
    > *"5-star trust me on the OL class next year"* — r/OhioStateFootball, Apr 18
    > *"5-star trust me we're fine at LB"* — Eleven Warriors comments, Apr 20
    > *"5-star trust me, 5-star trust me, 5-star trust me"* — @BuckeyeGrove, Apr 21
- Footer of this section in mono micro: `Source: 340K OSU fan conversations · r/CFB · Eleven Warriors · Twitter/X · Rivals forums · 7d`.

### N° 09 — This Week's Cards (renumber to N° 07)

Apply:
1. **Renumber** from `N° 09` to `N° 07`. V5 must have contiguous section numbering: 01, 02, 03, 04, 05, 06, 07, 08 (commiseration block).
2. **Fix the ASCII straight quotes** in the Nebraska card body — `"we're back"` should use typographer's curly quotes (`"we're back"`).
3. **Rename** `Download this week's set` → `Save this week's cards` to avoid the "data download" framing Kevin explicitly doesn't want.
4. **Vary the left-stripe colors across cards.** Currently two reds and one navy. Target a mixed palette across the three cards this week — e.g., Nebraska red, Michigan navy, Georgia red is fine this week because the editorial thesis names those three teams. Document the rule: left-stripe color matches the card's subject team; if two cards share a subject, allow the duplicate.
5. **Add an `Index Card · N° 047 · 1 of 3` line** just under each card's masthead row, for collectibility framing.

### N° 08 — Commiseration block ("For the Michigan Fans Who Are Still Here")

Keep exactly as is. This is the best-executed block on the page.

### Footer

1. **Fix the `73 conferences` error.** FBS has 10 conferences. Either change to `10 FBS conferences` or remove the conference count entirely.
2. **Add a `Subscribe · Wednesdays 9AM ET →` link** in the PUBLICATION column, above Archive.
3. Keep every other footer element unchanged.

---

## Global polish rules (apply everywhere)

1. **Methodology row consistency.** Every chart that has a metadata row must use the same format: `n = [count] conversations · [scope] · bot-filtered · updated [freshness] · methodology →`. Apply this to the cover chart (currently says only `n = 340K conversations · bot-filtered · updated 22m ago`) and add `methodology →` to the Mood Ticker if missing.
2. **Deep-link anchors on section numbers.** Every `N° 0X` section number should render as a hover-underlined anchor — click to copy that section's deep-link URL to clipboard. Micro tooltip on click: `Link copied ·`.
3. **Every number that aligns in a column must use `tabular-nums`.** This includes: the Mood Index right-rail scores, the archetype card confidence percentages, the rivalry obsession ratios, the Index Card big stat, the footer data-scope counts.
4. **Typographer quotes everywhere.** Straight ASCII `'` and `"` should not appear in any rendered body text. Apostrophes and quotes use `'` `'` `"` `"`.
5. **Card dividers.** The horizontal rule inside each archetype card (between the team-chip row and the signature-phrase row) should render at `rgba(11,15,20,0.08)`, not darker.

---

## What not to do

- Don't add a Toys section. Don't add a Podcast module. Don't add a Data Download / CSV export module.
- Don't change the masthead typography or the three-voice typography system.
- Don't introduce any new accent color beyond amber and alert red.
- Don't let team colors leak onto chrome (nav, footer, buttons, card chrome).
- Don't wrap any of the flagship charts in a visible card container. Charts sit directly on the bone paper.
- Don't rewrite any of the serif prose in the Editor's Note, the pull quote, or the commiseration block. Those have been iterated on; the voice is right.
- Don't replace the mono signature phrases with serif italic. The mono-in-quotes treatment is the intentional "field recording" style.
- Don't add decorative illustrations, hero imagery, hero gradients, or any ornamental SVG pattern backgrounds.
- Don't add icons to the nav or footer columns.

## Output expectations

Return a single file, `App.tsx`, using React + TypeScript + Tailwind utility classes (no custom Tailwind config extensions — only the standard base stylesheet). Use shadcn/ui primitives where applicable. Use Recharts for line charts and scatter. Use pure SVG + Tailwind for the small-multiples rivalry grid and the lexicon sparkline. Import team colors from a constant map at the top of the file. All text content lives inline in the component — no external data files.

When you finish, the scroll from top to bottom should read: masthead → nav → cover hero → byline & pull quote → Editor's Note (with drop cap) → N° 01 Mood Index → N° 02 Ticker → N° 03 Hype vs Reality (dark-mode feature) → N° 04 Taxonomy (18 cards + modifiers + migration sparklines) → N° 05 Rivalry Obsession Matrix (12-cell grid) → N° 06 Lexicon of the Week (phrase feature) → N° 07 Index Cards (was N° 09) → N° 08 Commiseration block → Footer.

Ship only what is specified. Do not add scope.
