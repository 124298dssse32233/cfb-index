# Rankings Redesign — Microcopy & Voice Guide

**Authored 2026-06-08.** The canonical string source for the redesign. Every label, button, empty-state,
error, tooltip, and chart alt-text the build emits should come from here — so nothing gets ad-libbed at
build time and the product speaks in one voice. Pairs with the
[component spec](rankings_redesign_component_spec.md) (which component shows which state) and the
[data-viz standards](rankings_redesign_dataviz_standards.md) (the "name the finding" rule §6 below makes
operational).

> How to use: when a component needs a string, grep this file for the component name. `{curly}` tokens are
> runtime values. Copy is **final** unless a value doesn't exist — then use the empty/loading variant, never
> a blank or a zero.

---

## 1. Voice — five principles

CFB Index sounds like **an analyst who respects you**: FiveThirtyEight's candor about uncertainty + The
Athletic's feel for what a fanbase is actually living through, minus the hype machine. It is never a hot-take
account and never a brochure.

1. **Lead with the finding, then the number.** The headline is the conclusion ("Texas passed Georgia this
   week"), the number is the receipt. Don't bury the lede behind a stat; don't state a stat without saying
   what it means.
2. **Name your confidence. Own your misses.** When the model is unsure, say so ("near coin-flip", "low
   confidence — thin sample"). The Report Card is *candid*: "We said 70%. It happened 68% of the time." A
   product that admits a miss is trusted on its hits.
3. **Plain words for hard math.** "Strength of schedule", not "SoS-adjusted opponent-quality index". Define
   the term once in a tooltip; never make the reader feel dumb. Bebas does the shouting — the prose stays calm.
4. **The fans are people, not sentiment.** Belief, mood, and vibe describe a fanbase that is *hoping* or
   *bracing*, not a "sentiment score of 0.62". Coral is empathy, not a gauge readout.
5. **Every claim is checkable.** Editorial sentences carry a receipt marker; charts name their finding inside
   the frame. If we can't source it, we don't say it — we say "Awaiting signal."

**Smell test before shipping a string:** Would an analyst say this out loud to a smart friend? If it sounds
like a press release, a horoscope, or a spreadsheet, rewrite it.

---

## 2. Mechanics — formatting rules (locked)

| Thing | Rule | Write | Don't |
|---|---|---|---|
| **Rank in prose/chips** | hash + numeral | `#3`, `#12`, `#102` | "3rd-ranked", "No. 3" |
| **Rank as Bebas numeral** | bare, the font is the styling | `3` (in `.rk`) | "#3" inside the big numeral |
| **Ordinal (percentile)** | spelled where it's the subject | `90th percentile` | "90%ile", "p90" |
| **Percent** | whole number unless precision matters | `68%`, `CFP 92%` | "68.0%", "68 percent" |
| **Probability (model)** | 0 decimals in UI, the word "chance" in prose | `92% chance` | "0.92 probability" |
| **Brier / calibration error** | 3 decimals, it's a small number | `0.193`, `±0.04` | "0.19", "19%" |
| **Delta / movement** | real minus sign, sign always shown, glyph + number | `▲ +6`, `▼ −3`, `— even` | "+6" alone (color-only), hyphen `-3` |
| **Record** | en-dash, no spaces | `10–2`, `7–1 SEC` | "10-2", "10 - 2" |
| **Win streak** | `W5` / `L2` | `W5` | "won 5 straight" in a chip |
| **Money / market volume** | `$` + 2 decimals | `$27.16` | "$27", "27.16 USD" |
| **Big counts** | comma thousands, `k` only ≥10k in chips | `1,284 mentions`, `12k` | "1284", "1.2K" |
| **Date — dateline** | `Week {n} · {Mon} {d}` | `Week 14 · Nov 30` | "11/30/26" |
| **Date — freshness** | relative under 24h, then absolute | `Updated 2h ago`, `Updated Nov 30` | "Updated 127 minutes ago" |
| **Season label** | full 4-digit | `2026 season` | "'26", "26 season" |
| **Team name** | the product's display name, not the slug | `Ohio State` | "ohio-state", "tOSU" |

**Numerals are tabular** everywhere (locked token rule) — ranks, stats, deltas align in a column. Apply
`.num`/`font-variant-numeric:tabular-nums`.

**Capitalization:**
- **Display headers (Bebas):** Bebas Neue is all-caps by design — write source text in normal **Title Case**;
  the font renders the caps. Never hand-type `THE BOARD` in source.
- **Eyebrows / kickers / column heads** (`.kick`, `.lbl`, `.colhead`): `text-transform:uppercase` in CSS —
  write source in **sentence case**, let CSS uppercase it.
- **Buttons, UI labels, tooltips, empty/error copy:** **sentence case** ("View as table", "Sorted by
  résumé", "Not enough data yet"). Only proper nouns capitalize.
- **Product proper nouns** (always capitalized — see §3): The Board, The Room, The Bridge, Report Card,
  Tri-Rank, Signal Stack.

**Punctuation:** the middot `·` separates inline metadata (`SEC · 10–2 · #4`). The em-dash `—` sets off an
appositive in prose. Curly quotes in editorial prose, straight in code/labels.

---

## 3. Lexicon — canonical product nouns & the glossary

These are the product's words. The build uses **exactly** these — never a synonym. Where a term needs
defining for a new reader, the **tooltip copy** is the one-liner that appears on `?`/hover/long-press.

| Term | What it is | Tooltip (the definition string) |
|---|---|---|
| **The Board** | the ranking itself | — (it's the page) |
| **Power** | the model's core team rating | "Our model's overall team rating — predicts the score of a neutral-site game." |
| **Résumé** | what a team has *earned* | "What a team has actually earned — wins weighted by who they beat." |
| **SoS** | strength of schedule | "Strength of schedule — how hard the games have been so far." |
| **Tri-Rank** | Model vs Room vs Nation | "Three views of one team: where our **Model** has them, where their **Room** (fans) believe, and where the **Nation** (polls) rank them." |
| **Model** | the navy view (our math) | "Where our model ranks this team." |
| **Room** | the coral view (the fanbase) | "Where this team's own fans believe they stand." |
| **Nation** | the amber view (consensus polls) | "Where the national polls rank this team." |
| **Belief** | a fanbase's conviction vs the model | "How a fanbase feels about their team relative to where the model has them." |
| **Signal** | measurable fan conversation | "Enough fan conversation to measure a mood. Below the floor, we say *Awaiting signal*." |
| **Vibe** | mood movement over the week | "Which way a fanbase's mood moved this week." |
| **Mood** | fanbase emotional state, 0–100 | "A fanbase's emotional state this week, doom (0) to euphoria (100)." |
| **The Room** | the fan-intelligence hub page | — (it's the page) |
| **The Bridge** | cross-division equivalence | "Where a non-FBS team would rank if you dropped them into the FBS list." |
| **Report Card** | the model's accountability page | "How well our predictions have actually held up." |
| **CFP %** | playoff-bid probability | "Chance of making the 12-team College Football Playoff, from simulating the season." |
| **Cutline** | the top-12 playoff line | "The top-12 College Football Playoff line — teams above it are projected in." |
| **Signal Stack** | the swipeable story cards (mobile primary viz) | — |
| **Movers** | biggest week-over-week rank changes | — |
| **Confidence** | how sure the model is | "How confident the model is in this call, based on how much agrees." |

**Casing of the triad in running text:** **Model / Room / Nation** capitalize when used as the named views
(they're proper views with fixed colors). "the model said", lowercase, is fine when speaking of the system
generally.

---

## 4. Don't-say list (extends the Chronicle banlist spirit)

The Chronicle pipeline already bans ~56 cliché phrases for generated prose. UI copy inherits the spirit. Ban:

- **Hype inflation:** "elite", "must-win", "statement win" (as a label — it's fine as the *Statement Wins*
  module name), "for the ages", "instant classic", "best in the nation" (say the rank).
- **Empty intensifiers:** "absolutely", "literally", "simply", "of course", "needless to say".
- **Hedge mush:** "arguably", "it could be said", "many believe" (we *measured* belief — cite it).
- **Spreadsheet-speak in the UI:** "sentiment score", "data point", "metric value", "N/A", "null", "0
  results" (use the empty-state copy instead).
- **Fake urgency:** "breaking", "you won't believe", "shocking", "stunning" (a 6-rank jump is "the week's
  biggest climb", not "shocking").

When a value is missing, the answer is never "N/A" — it's the **specific** empty string from §5.3.

---

## 5. String tables

### 5.1 Global UI strings

| Context | String |
|---|---|
| Search button (aria) | `Search teams and pages` |
| Command palette placeholder | `Search a team, conference, or page…` |
| "View as table" toggle | `View as table` / `View as chart` |
| Clear all filters | `Clear all` |
| Remove one filter (aria) | `Remove {filter} filter` |
| Dismiss finding (aria) | `Dismiss` |
| Expand row (aria) | `Show {team} detail` |
| Collapse row (aria) | `Hide {team} detail` |
| Result count (aria-live) | `{n} teams` · singular `1 team` |
| Sort announce (aria-live) | `Sorted by {lens}` (e.g. "Sorted by résumé") |
| Back to top | `Top of board` |
| "More" affordance | `{n} more →` (e.g. "8 more →") |

### 5.2 Loading states (shown only after >300ms; `aria-busy="true"` on the region)

| Region | Visible | Screen-reader (aria-label on busy region) |
|---|---|---|
| Board | skeleton rows (no text) | `Loading the board` |
| A chart | skeleton box (no text) | `Loading {chart name}` |
| The Room mood | skeleton gauge | `Loading fan mood` |
| A team drawer | skeleton lines | `Loading {team} detail` |

Skeletons carry **no placeholder copy** ("Loading…" text causes layout shift when it swaps). The SR label
lives on the container.

### 5.3 Empty / low-data states — the heart of graceful degradation

**Never a blank, a zero, or "N/A".** Each is a *specific* sentence that says why and what would change it.

| Where | Trigger | Copy | Sub-copy / tooltip |
|---|---|---|---|
| **Belief chip** | mentions < `MIN_MENTIONS_FOR_SIGNAL` | `Awaiting signal` | "Not enough fan conversation yet to read a mood." |
| **The Room (whole team)** | no measurable fan data | `Awaiting signal` | "We don't have enough conversation about this program to read its room yet." |
| **Board (preseason)** | season hasn't started | `The 2026 board opens Week 1.` | "Preseason ratings post when the first games are played." |
| **Movers** | week 1, no prior week | `Movement starts after Week 1.` | "We need two weeks to show week-over-week change." |
| **Tri-Rank** | no poll/room view | `Model only — no poll yet` | "Polls and fan belief appear once they exist for this team." |
| **CFP %** | not simulated | `Not simulated yet` | "Playoff odds post after Week 4." |
| **Quantile dotplot** | not simulated | `Not simulated yet` | — |
| **Any chart** | thin sample | `Not enough data yet` | "This chart needs at least {min} games." |
| **Season arc** | < 3 games | `Too early for a trend` | "A few more games and the season shape appears." |
| **Report Card** | preseason | `No calls to grade yet` | "Grades appear once the model has made predictions this season." |
| **Bridge spotlight** | division off-season | `No {division} data this week` | — |
| **Search no-results** | no match | `No team or page matches "{query}".` | "Try a team name, a conference, or 'report card'." |
| **Filtered board empty** | filters exclude all | `No teams match these filters.` | "Clear a filter to see more." (+ a "Clear all" button) |

**Awaiting Signal is a brand moment, not an error.** Gray chip, calm tone. It says *we'd rather show nothing
than fake a reading* — which is the whole accountability thesis in one chip.

### 5.4 Error states (`role="alert"`; always offer the way back)

| Where | Copy | Action |
|---|---|---|
| Board failed to load | `The board didn't load.` | `Retry` button |
| A chart failed | `This chart didn't load.` | `Retry` (+ the table-fallback stays available) |
| Drawer detail failed | `Couldn't load {team}'s detail.` | `Retry` |
| Stale data (deploy lag) | `Showing the last good board from {time}.` | — (informational, not alarming) |
| Generic | `Something didn't load. Try again in a moment.` | `Retry` |

Tone: factual, never "Oops!" or "Error 500" or an emoji. Say what broke and the one button that fixes it.

### 5.5 Confidence band language (data-driven thresholds; §33 of design system)

The model's confidence is shown as a word + a band, never color alone.

| Band | Word | Chip/label copy | When it's the subject of a sentence |
|---|---|---|---|
| high | **High confidence** | `High confidence` | "High confidence — the views agree." |
| medium | **Some uncertainty** | `Some uncertainty` | "Some uncertainty — the room and the model disagree." |
| low | **Low confidence** | `Low confidence` | "Low confidence — thin sample this early." |
| unset | (no claim) | `Confidence pending` | "Not enough yet to set a confidence." |

Near-50% probabilities get the phrase **"near coin-flip"** in prose and a value on the sim bar ("52% / 48% ·
near coin-flip").

### 5.6 Per-surface specific strings

**Masthead / dateline**
- Brand wordmark: `THE CFB INDEX` (Bebas; source `The CFB Index`).
- Live dateline: `Updated {Xh} ago · Week {n}` with a pulse dot (`aria-hidden`).
- Archive dateline: `Frozen · Week {n}, {season}` (no pulse — it's a snapshot).

**Board lens tabs** (the four views)
- `Power` · `Résumé` · `Bettor` · `Belief`
- Tooltips: Power/Résumé/Belief from §3; **Bettor** = "How the betting market would rank these teams."

**Board column heads** (uppercased by CSS; source sentence case)
- `Rank` · `Team` · `Power` · (desktop adds) `Off` · `Def` · `Résumé` · `SoS` · `Tri-Rank` · `CFP %`
- Each sortable header aria: `Sort by {column}` → after sort `aria-sort="descending"`.

**CFP cutline**
- `College Football Playoff cutline · top 12 in` (bracket glyph `aria-hidden`).

**Belief chips** (the live three)
- Hot: `▲ Fans +{n}` · Cold: `▼ Fans −{n}` · Aligned: `Aligned`
- The arrow is `aria-hidden`; the word "Fans" + signed number carries meaning.

**Team dossier**
- Section eyebrows: `Tri-Rank` · `The case` · `Fingerprint` · `Season arc` · `The Room` · `Playoff path` ·
  `Accountability` · `Rivalries`.
- Fingerprint peer toggle: `vs FBS` · `vs Power 4` · `vs {Conf}`.
- Fingerprint scale legend (one-time): `0 · worse — 50 = average — elite · 100`.
- Accountability line template: `We had {team} at #{rank} entering Week {n}. They finished {result}.`

**Conference**
- Title: `{Conference} · {season}`.
- Scoped column heads: `Record` · `ATS` · `vs Market` · `Form` · `Nat'l`.
- Title race eyebrow: `Title race`. Bid math eyebrow: `Playoff math`.
- Bid math line: `{n} bids likely · {team} controls its path.`

**The Bridge**
- Division selector: `FCS` · `DII` · `DIII` · `NAIA` · `JUCO`.
- Spotlight template: `{team} ({division}) plays like FBS #{computed}.` Sub: `Ahead of {n} FBS teams.`
- Honesty note (footer): `Equivalents are computed from the same power scale — not hand-set.`

**Compare**
- Header: `{teamA} vs {teamB}`.
- Sim bar: `{a}% / {b}% · {qualifier}` where qualifier ∈ {`near coin-flip`, `{team} favored`, `{team}
  heavily favored`}.
- Dumbbell row aria (see §6).
- Empty 2nd slot: `Pick a team to compare`.

**The Room**
- Mood gauge label: `National mood` · center tick word `Mixed`.
- Vibe shifts eyebrow: `Vibe shifts this week`.
- Respect gap eyebrow: `Respect gap` (tooltip: "Where fans rank their team vs where the model does.").
- Rival heat eyebrow: `Rivalry heat`. Civil war eyebrow: `Civil wars` (tooltip: "Fanbases split against
  themselves this week.").
- Provenance footer: `From {n} sources across {m} fanbases · updated {time}.`

**Report Card**
- Page title: `Report Card` · eyebrow `Did we call it?`
- Calibration chart title: `Predicted chance` (x) · `How often it happened` (y); annotation template:
  `Said {p}% → happened {q}%`; figure: `Calibration error: ±{e}`.
- Accuracy chart: y-title `Calls correct`; baseline label `If you'd just picked the favorite ({b}%)`.
- Poll dot plot: axis `Brier score · ← lower is better`; rows `CFB Index` · `AP poll` · `Coaches`.
- Honest framing line: `Where we were wrong, here's where and by how much.`

**Archive (retrospective)**
- Banner: `This is how Week {n}, {season} looked when it was live.`
- Report-card-in-retrospect: `We said. Here's what happened.`

---

## 6. Accessibility copy — the "name the finding" alt-text rule

Every chart is `role="img"` with an `aria-label` that **states the finding in words**, never describes the
geometry. This operationalizes data-viz standard §3 (every chart names its finding) for screen-reader users
and is required for AA. Templates:

| Chart | aria-label template | Example |
|---|---|---|
| **Tri-Rank** | `Model {m}, room {r}, nation {n} — a {gap}-rank {agreement\|disagreement}.` | "Model 3, room 2, nation 4 — a two-rank disagreement." |
| **Fingerprint bar** | `{metric}: {p}th percentile vs {peer}.` | "Pass efficiency: 90th percentile vs FBS." |
| **Quantile dotplot** | `{k} of {N} simulations make the field, {pct} percent.` | "18 of 20 simulations make the field, 90 percent." |
| **Calibration** | `When we said {p} percent, it happened {q} percent of the time. Calibration error {e}.` | "When we said 70 percent, it happened 68 percent of the time. Calibration error 0.04." |
| **Accuracy line** | `{c} percent of calls correct, versus {b} percent for always picking the favorite.` | "74 percent correct, versus 72 percent for the favorite." |
| **Poll dot plot** | `Brier score: CFB Index {a}, AP {b}, Coaches {c}. Lower is better.` | "Brier score: CFB Index 0.193, AP 0.205, Coaches 0.211." |
| **Bump chart** | `{team} passed {other} in Week {n} to take #{rank}.` | "Texas passed Georgia in Week 9 to take #3." |
| **Division spectrum** | `{team}, power {pw}, equals FBS #{eq}, ahead of {n} FBS teams.` | "Ferris State, power 54, equals FBS #102, ahead of 32 teams." |
| **Dumbbell (compare)** | `{metric}: {a} {va}, {b} {vb}, edge {leader} by {gap}.` | "Pass efficiency: Georgia 80, Texas 90, edge Texas by 10." |
| **Mood gauge** | `National mood: {word}, {v} of 100, {dir} {delta}.` | "National mood: anxious optimism, 62 of 100, up 6." |
| **Season arc** | `{team} climbed from #{start} to #{now} over {n} weeks.` | "Texas climbed from #8 to #3 over nine weeks." |
| **Sim bar** | `{a} {va} percent, {b} {vb} percent, {qualifier}.` | "Texas 52 percent, Georgia 48 percent, near coin-flip." |

**Table-fallback caption** (the visually-hidden `<table>` behind each chart): `{Chart name} — data table.`
e.g. `Fingerprint percentiles — data table.`

**Decorative-only** (always `aria-hidden`): the momentum tick, every glyph/football/bracket, the pulse dot,
sparkline strokes whose number is already in text, gradient fills, the 50th-pct tick.

**Icon-only controls always carry an aria-label** (§5.1): search, dismiss, expand. The bottom tab bar never
goes icon-only — visible text label always.

---

## 7. Tone by context

| Context | Tense | Stance | Example |
|---|---|---|---|
| **Live board** | present | confident, current | "Texas sits #3 — its highest of the year." |
| **Movers / vibe** | present-perfect | momentum | "Ole Miss has climbed six spots since Week 8." |
| **Report Card** | past + candid | accountable, owns misses | "We had them in. They lost out. Here's the miss." |
| **Archive** | past, frozen | retrospective, no live verbs | "This is how it looked. Here's what happened next." |
| **Awaiting Signal** | present | calm, honest | "Not enough fan conversation yet." |
| **Tooltips** | present | teacherly, one sentence | "Strength of schedule — how hard the games have been." |

The through-line: **say what's true, say how sure we are, and where we were wrong, say so plainly.** That is
the CFB Index voice in one line.
