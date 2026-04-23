# Fan Intelligence Hub — V4 Live Review & A+ Polish Document

**Source reviewed:** `https://www.figma.com/make/80i0wHIeaOR9dGyBO0usMx/Fan-Intelligence-Hub-Design` (Version 4, full-screen render, 22 Apr 2026)
**Reviewer framing:** what a nerdy, data-viz-obsessed CFB fan who loves the fan community would ship as A+.

---

## The one-line verdict

V4 is a legitimate A−. It is the first version where opening the page and scrolling feels like reading a publication, not like looking at a dashboard. The masthead, cover, Mood Index flagship, Hype vs Reality matrix, Index Cards, and the "For the Michigan fans who are still here" commiseration block are all at or near publication-quality. The distance from A− to A+ is not a redesign. It is about a dozen concrete polish fixes, one taxonomy upgrade, and three missing modules that the spec called for but Figma Make didn't render.

---

## What v4 got right (keep all of this)

**Editorial framing is locked in.** The masthead strip with `THE CFB INDEX · FAN INTELLIGENCE · VOL V · N° 047 · MODEL WEEK 21` on the left and `22 APR 2026 · UPDATED 22M AGO` + amber live-dot on the right is doing real work. It establishes that this is an *issue*, not a page. The "Next issue Wednesday 9AM ET" line in the footer closes the loop on cadence. A reader who sees Volume/Issue/Date at the top and a cadence promise at the bottom believes they're reading a publication, which is the entire positioning play.

**The cover is a cover.** The `MICHIGAN'S BELIEF IS AT A DECADE LOW.` headline in condensed display + small cover-label eyebrow + byline (`BY THE CFB INDEX MODEL · EDITED BY THE STAFF`) + italic serif pull quote + a right-rail chart with the 10-year average reference line and an in-canvas annotation is exactly the asymmetric 60/40 editorial layout I wanted. The byline in particular — attributing authorship to the model and editorship to the staff — is the clearest expression of the "quant + newsroom" positioning anywhere on the page.

**Mood Index flagship chart is real data journalism.** Six teams, team colors as data ink, three in-canvas annotations with leader lines (`Georgia hasn't dropped below 90 all offseason`, `Oregon overtook Alabama on Apr 2`, `Michigan's slide began with the Moore presser (Mar 14)`), a `playoff confidence` reference line at ~78, Y-axis truncated to 50–100, team chips on the right with rank/score/delta, and the italic serif caption *"The historically confident fanbases sit at their lowest mark of the decade while Oregon quietly ascends."* This is Bloomberg-does-CFB. The methodology row with `n = 2.4M conversations · 133 FBS fanbases · bot-filtered · updated 22m ago · methodology →` is the single highest-credibility thing on the page.

**Hype vs Reality is the best chart on the site.** 16 teams plotted as team chips against a `Fan Hype Level` × `Model Reality Score` grid, four ghosted condensed-display quadrant words (`DELUSIONAL / JUSTIFIED / REALISTIC / SLEEPING GIANT`) rendered as background type, two annotations with leader lines (Nebraska, Michigan), a diagonal reference line, and the editorial caption *"The diagonal runs from despair to destiny — everything north is wishfulness; everything south is quiet strength."* The dark-mode background treatment differentiates it visually from the rest of the issue — the reader registers it as a *feature*, not a module.

**Archetype cards have found the right voice.** The signature phrases — `"Are we still elite?"` / `"Don't do this to me"` / `"We know what we are"` / `"What are we now?"` / `"Punching above our weight"` — are specific, voice-y, and read like things actual fanbases say. Setting them in mono italic inside quote marks treats them like field recordings, which is correct.

**Index Cards are publication-grade collectibles.** The team-color left-edge stripe, mono-caps masthead line, condensed-display headline, huge tabular stat number, editorial explanation below, italic signature line at the bottom, and team chip bottom-right is a *format*. `NEBRASKA IS NOT BACK / 47,392 / they are not back` works on the page and works as a social image. `LITTLE BROTHER, CONFIRMED / 2.6× / the receipts are public` is the rivalry obsession ratio I speced, shipped as a card. `archive of all 47 issues →` implies 47 weeks of back catalogue, which is a massive credibility signal.

**The commiseration block is the emotional landing.** `FOR THE MICHIGAN FANS WHO ARE STILL HERE` as a quiet mono caps header, a three-paragraph serif letter that grants historical context without condescension, and a three-word benediction — `Hold the line.` — signed `— the staff · 22 Apr 2026`. Nothing else on any sports analytics site does this. It's the single move that differentiates CFB Index from "yet another ranking aggregator."

**The footer closes like a Bloomberg terminal.** `N° 047 · 22 APR 2026 · NEXT ISSUE WEDNESDAY 9AM ET` + amber dot, the data-scope line, and `Model: power-resume-v1.3.2 · last cut 2026-04-22 · changelog →` together tell the reader: this is engineered, versioned, and reliably periodic. That is the trust moat.

---

## The gap from A− to A+

### 1. Ship the taxonomy upgrade (highest leverage)
The archetype section still renders `THE EIGHT FANBASES OF COLLEGE FOOTBALL`. The research produced 18 primary archetypes + 8 modifiers with migration pathways and half-lives. The 8-card grid is shipping the 1.0 version of a taxonomy that now has a 3.0 version sitting on the shelf. Concrete deltas:

- **Rename section** to `THE 18 FANBASES OF COLLEGE FOOTBALL` (or `A TAXONOMY OF FANDOM`, if the number feels gimmicky) and update the dek to reference the primary + modifier structure.
- **Add the three new primary archetypes** that only emerged from the deeper research: `The HBCU Standard` (Jackson State/Howard), `The Mercenary` (Colorado under Prime, UNC under Belichick — distinct from Generational Hope because it's coach-as-celebrity not program-as-rising), and `The Celebrity Appointment` (if keeping Mercenary and Celebrity as separate archetypes).
- **Reframe the 8 existing cards** as Primary archetypes and add a "Modifiers" strip below each — showing which of the 8 structural modifiers (State Identity, Rivalry-Defined, Faith-Based, Academic Cousin, Sibling School, Scorned Ex, Pedigree-Entitled, Independent) apply. E.g., Michigan card shows "Primary: Identity-Crisis Blueblood 96% · Modifiers: Sibling School (OSU), Academic Cousin, Pedigree-Entitled."
- **Add a third row to each card**: a tiny sparkline showing that fanbase's archetype migration history over the last 5 seasons. This is the structural upgrade that makes the taxonomy feel *dynamic* instead of static.
- **Fix the signature phrases** — Perpetual Believer's "This is our year" is generic; the Nebraska-specific version ("we're back") is already elsewhere on the page in the Index Card and Editor's Note. The taxonomy card should cite the specific community phrase, not the universal one. Every card's signature phrase should be a *receipt*, not a paraphrase.

### 2. Ship the three missing flagship modules
The section numbering (N° 01 Mood Index → N° 03 Hype vs Reality → N° 04 Taxonomy → N° 09 Index Cards) tells the reader that N° 02, N° 05, N° 06, N° 07, N° 08 exist somewhere. Either ship them or renumber to be contiguous. The three that earn their slot:

- **N° 02 Mood Ticker** — a tight horizontal strip right after the Mood Index flagship, showing the 10 biggest week-over-week mood movers as team chips + delta numbers, left-to-right. Think of it as the "weekly box" of the issue. Already in the v2 component code; just needs to be wired in.
- **N° 05 Rivalry Obsession Matrix** — the 2.6× OSU/Michigan ratio is shipping as an Index Card, which is fine, but the full module is a different thing: a small multiples grid showing 10–12 rivalries and who's more obsessed with whom, ordered by asymmetry. This is the single most shareable fan-community concept on the whole site and it's currently a one-line card.
- **N° 06 Lexicon of the Week** — one editorial spread featuring a single piece of community jargon that spiked this week. E.g., `"5-star trust me" — Ohio State fans, +340% this week. What it means, where it started, what it replaces. Field recordings from r/CFB, Twitter, Rivals.` This is the module that most clearly says "we are of the community, not above it."

A 'Fan IQ' module showing the reader their own fanbase's archetype + this week's mood + the top three phrases their community is saying is also worth shipping — it turns a read into a personalized artifact. But it's lower leverage than 02/05/06, so save it for a v5.

### 3. Chart-level polish (the visible bugs)

**Cover chart (Michigan line):**
- Michigan's line is rendered in dark navy (close to ink), not Michigan blue. With only one line in the chart, the color is doing nothing. Either render in Michigan's maize/blue brand color (the maize endpoint dot would be the editorial flourish) or drop the color and stay monochrome.
- No endpoint label on the line. The reader has to infer that the line ends at 58. Add a small maize circle + `MICH 58` in mono at the Apr 22 endpoint.
- The `10 year average` label floats next to the dashed line with no explicit anchor. Anchor it to the right endpoint of the dashed line, inside the chart area.
- The `Mar 14` crossing moment (where Michigan's line crosses below the 10-year average — the whole thesis of the cover) has *no visual marker*. Add a thin vertical tick at Mar 14 with a 2-word annotation: `Moore presser`.
- X-axis date labels (Feb 15 → Apr 22) are slightly rotated. At this chart width, horizontal works. Straighten them.

**Mood Index flagship:**
- The `playoff confidence` reference line label lands at a vertical position where two team lines (Alabama crimson, Ohio State red) cross it, making it visually noisy. Move the label to chart-left whitespace or a position where no team line is sitting on it.
- **The two-reds problem.** Georgia is bright red, Alabama is crimson, Ohio State is deep red. Three reds on the same chart. Alabama and Ohio State's lines are genuinely hard to distinguish. Options: (a) render Alabama in its houndstooth gray secondary brand color on this chart, or (b) add a second visual encoding (dotted line for SEC schools, solid for B1G — uses the conference affiliation as a legible dimension).
- Delta chips on the right — Georgia's `+2`, Michigan's `-15`. They appear to render in the same amber accent regardless of sign. Deltas should be semantic: amber (attention) for positive change, alert-red for negative. The `-15` next to Michigan should read red.
- Team chip sizes are slightly oversized relative to the chart height. Downsize from ~28px to ~20px so the list reads as a quieter index, not a second chart.

**Hype vs Reality matrix:**
- The `Nebraska, the most delusional fanbase in the sport.` annotation gets **cut off** — `sport` is partially rendered. Extend the text box or shorten the annotation: `Nebraska: peak delusion.`
- The `Michigan, the most underrated team by its own fans.` annotation has the same risk. Shorten: `Michigan: underrated by its own.`
- The `SLEEPING GIANT` ghosted quadrant label extends past the chart's right edge. Either scale down the display type or mask it to the chart bounds.
- The `Fan Hype Level` Y-axis title is set horizontally and creeps into the chart area. Rotate to true vertical (90°) or move it to a top-left caption position: `Y: Fan Hype · X: Model Reality`.

### 4. Editorial-voice consistency

- **Drop-cap the Editor's Note.** A genuine magazine editor's note gets a large serif drop cap on the first letter. The voice is there — the typography isn't quite closing the loop. One three-line drop cap on `T` would push this to A+.
- **Tighten the Editor's Note measure.** It currently spans ~850px of body width. Serif body copy reads best at 60–70 characters per line (~540–620px). Narrow the column and let it breathe.
- **The Editor's Note "— the staff" should mirror the commiseration block's `— the staff · 22 Apr 2026`.** Right now the editor's note ends `— the staff` (italic, no date) and the commiseration ends `— the staff · 22 Apr 2026`. Either add the date to both or drop it from both. Consistency > either choice.
- **The methodology row is inconsistent**. Cover chart says `n = 340K conversations · bot-filtered · updated 22m ago` (no methodology link, no fanbase count). Mood Index row says `n = 2.4M conversations · 133 FBS fanbases · bot-filtered · updated 22m ago · methodology →`. Pick a canonical format (I'd pick the Mood Index version) and apply it everywhere.
- **Footer data-scope line error.** `73 conferences` is wrong for FBS — there are ~10 FBS conferences. Either say `10 FBS conferences` or drop the conference count. Right now it triggers a "wait, is this right?" from any reader who actually knows college football, which is exactly the wrong response.

### 5. Specific typographic fixes

- **Y-axis labels** on the Mood Index and Hype vs Reality are in regular sans; they should be in the mono tabular-nums stack used elsewhere in the data system. Right now numeric axis labels and metadata numbers don't look like they come from the same voice.
- **Index Card `2.6×`** — the `×` character is rendered slightly above baseline. If this is a superscript, intentional. If not, the multiplier sign should sit inline with the numeral.
- **`Nebraska fans have said "we're back" this offseason`** — the quote marks around "we're back" are straight ASCII ("..."). Across the rest of the page, typographer's curly quotes are used correctly ("…"). Fix the one card.
- **Horizontal rule below archetype cards** — cards have a dividing rule between the team-chip row and the signature-phrase row. The rule color is a little too dark. Half a step lighter (`rgba(11,15,20,0.08)` instead of `rgba(11,15,20,0.12)`) will restore the delicate divider feel.

### 6. Things that would move the needle if added

- **Give the cover chart a byline of its own.** Under the italic editorial caption, a tiny line: `Chart by The Index Desk`. Or `Model: power-resume-v1.3.2`. The cover chart is a piece of reporting and it should be credited as one.
- **"Also reading this week" sidebar on the cover.** A three-item column on the right rail below the cover chart: the three other stories that would have been the cover if Michigan hadn't cratered. `Also reading · Oregon passes Alabama · The quiet Iowa floor · Nebraska's "we're back" at 47,392`. This is the New York Times above-the-fold device.
- **Archetype migration arrows on the cards.** Each card carries a tiny subtext: `→ trending toward Newly Crowned` / `→ 63% chance to exit within 2 seasons`. This converts static taxonomy into live state.
- **"Issue N° 046 · last week" navigation rail** at the top of the issue, next to the masthead. Prev/next issue arrows. The Archive exists but is hidden in the footer. Surface it.
- **Weekly issue email.** A quiet inline sign-up block between the Archetypes section and the Index Cards: `Delivered Wednesdays, 9AM ET. Sample issue →`. The cadence is the product; give readers the receive-it form.
- **Bookmarkable anchors on each module.** `N° 01 · The Fanbase Mood Index` should render as an in-page link — click the `N° 01` to copy a deep link to that module. This is how serious editorial products turn their page into a library.

### 7. Keep these defaults, they're load-bearing

- Amber (`#E0A300`) as the sole accent used only for motion/freshness signals (live-dot, positive deltas, section eyebrows, footer links). Do **not** let amber creep into decoration anywhere else.
- Warm ink (`#0B0F14`) + bone paper (`#F3EEE4`) as the only neutral pair. Every dark-mode section should use warm ink, not pure black — it's why the whole site feels printed, not screen-ed.
- Team colors as *data ink only*. The archetype chips, the line colors, the card stripes — that's the entire team-color budget. The moment a team color appears on chrome (button, header, nav underline), the system breaks.
- Mono (IBM Plex / JetBrains) for: tabular numerals, masthead, metadata, signature phrases. Condensed display (Druk / GT Flexa / Bebas) for: headlines, big stats, quadrant words. Serif (Tiempos / Source Serif 4) for: body prose, italic captions, pull quotes. Three voices, three jobs. Don't let them overlap.
- Section-numbering discipline (`N° 01`, `N° 02`, `N° 03`, …) as the primary wayfinding. Readers learn this in the first scroll and it does all the navigation for the rest of the issue.

---

## The 10-item punch list (ship this)

Ordered by leverage per hour of engineering time. Do 1–3 this sprint.

1. **Fix the `73 conferences` footer error.** 2-minute fix, highest embarrassment-avoided ratio.
2. **Color Michigan's cover chart line in Michigan blue + add the `MICH 58` endpoint label + add the `Moore presser` vertical marker at Mar 14.** The cover chart is the first chart the reader sees; it should be the most editorially tight.
3. **Fix the two-reds problem on Mood Index.** Differentiate Alabama from Ohio State either by secondary brand color or by line style.
4. **Fix the Hype vs Reality annotation truncation + quadrant-word overflow.** Two text-box widths and one display-type scale.
5. **Color Mood Index deltas semantically** (amber for positive, alert-red for negative).
6. **Drop-cap the Editor's Note + narrow its measure to ~60ch.** Pushes the editorial voice from "intended" to "executed."
7. **Ship the taxonomy upgrade** — 18 primary + 8 modifiers, with a migration sparkline on each card.
8. **Ship the Mood Ticker module** (N° 02) between the flagship chart and Hype vs Reality. Horizontal strip, 10 biggest movers, team chips + delta.
9. **Ship the Rivalry Obsession Matrix** (N° 05) as a small-multiples spread. The `2.6×` card is a tease; the full module is the shareable feature.
10. **Ship the Lexicon of the Week** (N° 06). The module that most clearly says "we're of the community, not above it."

---

## What not to do

- Don't add a Toys section. Don't add a Podcast. Don't add CSV downloads. Stay away from these.
- Don't add more colors. The palette is doing real work precisely because it's disciplined.
- Don't redesign any of the flagship charts. They're the strongest thing on the page. Polish, don't rebuild.
- Don't let the archetype section balloon past one screen-height per primary archetype. 18 cards at current density is fine; 18 cards at 2× density is a slog.
- Don't let "methodology" become a page of text. Keep it as a modal/panel triggered by the `methodology →` link in the metadata row. A short, readable, versioned page. Anything longer and the trust signal becomes a slog signal.

---

## Closing read

V4 ships three things that very few sports-data products ship: an editorial voice that sounds like a person, charts that do reporting rather than merely display data, and an emotional register that takes fandom seriously. The Michigan commiseration block alone puts this in a different category than the rest of the category. The work from here is finishing — not reinventing.
