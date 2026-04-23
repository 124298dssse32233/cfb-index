# Fan Intelligence Hub — V5 Code Review

*Audit of the v5 Figma Make export against `FIGMA_MAKE_V5_PROMPT.md` and the A+ review. Goal: decide whether to kick off Claude Code now or send one more Figma pass first.*

## One-line verdict

**Conditional go.** V5 implements ~80% of the prompt beautifully. One section — the Taxonomy — is still shipping the old v4 8-archetype version, not the 18 + modifiers + migration sparklines we specified. Three options below; my recommendation is Option B.

## Architecture — clean and right

`main.tsx → App.tsx` is the live render path. App.tsx composes 12 publication components in the correct order (Masthead → Navigation → CoverHero → EditorNote → MoodIndexFlagship → MoodTicker → HypeVsRealityMatrix → FanbaseArchetypesTaxonomy → RivalryMatrix → LexiconWeek → IndexCards → CommiserationBlock → Footer) with a clean one-import-per-section pattern. Shared primitives live in `publication/TeamChip.tsx` and `publication/TeamColors.ts`. This is exactly what Claude Code wants as a reference.

**One piece of dead code to delete before kickoff:** `src/app/AppV5.tsx`. It's a monolith with half the sections stubbed as empty `<div />`. Not referenced by main.tsx, but leaving it in the zip will confuse Claude Code. `rm src/app/AppV5.tsx` before you hand the reference over.

## What v5 nailed

**Masthead** — Vol V · N° 047 · Model Week 21 · 22 Apr 2026 · Updated 22m ago, with a live pulse dot. Exactly the small-print editorial register the prompt asked for.

**Navigation** — `← N° 046` on the left, `N° 048 preview →` on the right, `Subscribe` in the primary nav, Hub as the active tab with an amber underline. All four v5 additions landed.

**Cover Hero** — **this is the strongest section**. Michigan line is rendered in Michigan blue `#00274C` with a Michigan maize `#FFCB05` endpoint dot, the `MICH 58` endpoint label is positioned at the line's terminal, and the `Moore presser` annotation sits at the Mar 14 inflection. 10-year average reference line at y=67 with a serif italic label. 60/40 two-column grid (editorial text left, chart + Also Reading rail right). A+.

**Editor's Note** — drop cap in Bebas Neue floating left of the paragraph, 60-68ch measure (the `max-w-[720px]` gets there), italic staff sign-off. Matches the prompt.

**Mood Index Flagship** — the two-reds problem is resolved (Alabama rendered in grey `#828A8F`, Michigan in navy `#00274C`). Inline endpoint labels to the right of the chart show team chip + name + current value + delta, with deltas colored semantically (amber for positive, red `#B7281D` for negative). Three in-canvas annotations with leader lines (Michigan slide, Oregon overtakes Alabama, Georgia dominance). `playoff confidence` reference line at y=75. All the chart polish we asked for.

**The Ticker (N° 02)** — new section, correctly implemented. 10-column grid of team chip + abbreviation + current value + delta + cause. Deltas colored semantically. Methodology row underneath: `n = 340K conversations over 7d · bot-filtered · updated 22m ago · methodology →`.

**Hype vs Reality Matrix** — four quadrant watermarks at 10% opacity (DELUSIONAL / JUSTIFIED / REALISTIC / SLEEPING GIANT). The `SLEEPING GIANT` overflow is solved by breaking it to two lines. Nebraska and Michigan annotations are correctly positioned with leader lines. Dark backdrop `#0B0F14` treatment gives it flagship weight.

**Rivalry Matrix (N° 05)** — new section. 12 rivalries as a 3-column grid of cards, each with team chips, a proportional ratio bar, `X.X× ratio` in tabular mono, and a serif-italic take. THE GAME 2.6×, Iowa Corn 3.1×, Keystone 4.2× all present. The card grid is a better design decision than the horizontal bar chart I originally specced — this reads cleaner at 12 items.

**Lexicon of the Week (N° 06)** — new section. "5-Star Trust Me" headline, 4-week spike sparkline, three verbatim "field recordings" in mono italic with source attribution, 6-week trajectory context. Matches the spec.

**Index Cards (N° 07)** — renumbered from 09 correctly. Three cards: NEBRASKA IS NOT BACK (47,392), LITTLE BROTHER CONFIRMED (2.6×), THE QUIETEST CONFIDENCE IN THE SPORT (94). Typographer's apostrophes used inside these component strings (`card.teamAbbr` etc use `&rsquo;` in surrounding JSX).

**Commiseration Block** — "For the Michigan fans who are still here" with the Harbaugh/2014 parallel and the "hold the line" ending. Dark backdrop, 60-68ch measure, italic staff signature. Kept intact.

**Footer** — **the `73 conferences` bug is fixed**: `133 FBS fanbases · 10 FBS conferences · 3,828 games since 2014`. Also includes the weekly cadence signal: `Next Issue Wednesday 9am ET`.

## What v5 missed — ordered by leverage

**P0 — Taxonomy section still ships 8 archetypes, not 18.** `FanbaseArchetypesTaxonomy.tsx` line 92 reads "The eight fanbases of college football" and line 96 says "sorts into one of eight archetypes." The component's local `archetypes` const has exactly 8: Anxious Dynasty, Perpetual Believer, Wounded Giant, Hopeful Uprising, Quiet Professional, Identity-Crisis Blueblood, Content Mid-Major, Generational Hope. **Missing the 10 new ones the v5 prompt explicitly specified** with per-archetype content: Newly Crowned, Stockholm Syndrome, Service Academy, Coach Cult, HBCU Standard, Mercenary, Celebrity Appointment, Petulant Blueblood, Regional Identity, Sleeper.

**P0 — No 8-modifier strip.** The v5 prompt specified a horizontal strip beneath/beside the archetype grid with the 8 modifiers (Emerging, Entrenched, Upstart, Fading, Rebuilding, Reloading, In Crisis, Ascendant). Not implemented.

**P0 — No migration sparklines.** The v5 prompt specified small sparklines showing how fanbases have moved between archetypes over time (e.g. "Washington: Hopeful Uprising → Newly Crowned"). Not implemented.

**P2 — Typographer quotes inconsistency in RivalryMatrix.** The `take` strings use escaped single quotes (`hasn\'t noticed they\'re little`) instead of `&rsquo;`. These will render as straight apostrophes in the DOM. Other sections (IndexCards, LexiconWeek, Commiseration) used `&rsquo;` correctly. Search-and-replace fix.

**P2 — Tailwind arbitrary values for font-size breakpoints.** Multiple components use `text-6xl sm:text-7xl lg:text-[80px]`. Fine in prod, but `80px` as arbitrary value breaks if we ever swap Tailwind for a stricter token system in Claude Code. Not a blocker — worth noting for Phase 5 polish.

**P3 — Mobile navigation is hidden below `md`.** `<nav className="hidden md:flex ...">` means the nav collapses to nothing on mobile. No hamburger, no drawer. The mobile screenshots in `/src/imports/` show the issue. Claude Code will likely add a disclosure; log as follow-up, not blocker.

**P3 — HypeVsRealityMatrix uses manual pixel positioning for team chips.** `getChipPosition(reality, hype)` overlays absolutely-positioned divs on top of a Recharts ScatterChart. Works, but will drift if viewport changes or Recharts margins shift. Recharts `<Scatter>` with a custom shape prop would be cleaner. Non-blocking.

## Three options

**Option A — Kick off Claude Code now, as-is.**
Claude Code has the full 18-archetype spec in `CLAUDE_CODE_V5_IMPLEMENTATION_PROMPT.md` Phase 1. The reference being wrong for the Taxonomy section doesn't kill the build — Phase 1 tells Claude to create 18 archetypes from scratch, and reporting.py will render them from the database, not from the Figma component. Pro: ship now. Con: Claude Code may look at the 8-archetype Figma reference and get confused about which source is canonical.

**Option B (recommended) — One targeted Figma pass to fix Taxonomy, then kick off.**
Send Figma a narrow prompt: "Expand `FanbaseArchetypesTaxonomy.tsx` to 18 archetypes (here are the 10 to add, with content), add an 8-modifier strip below the grid, add small 6-week migration sparklines inside each archetype card showing whether teams have moved in or out of that archetype recently." That's one focused loop, probably 30 minutes of Figma Make time, and leaves Claude Code with a complete, unambiguous reference. Pro: Claude Code's path is clean. Con: one more iteration before kickoff.

**Option C — Delete the Taxonomy component entirely from the Figma zip and kick off.**
Keeps the good sections as reference, removes the incomplete section so Claude Code implements from the CLAUDE.md spec only. Cheap to do (literally `rm src/app/components/publication/FanbaseArchetypesTaxonomy.tsx` and the App.tsx import). Pro: no ambiguity. Con: loses the visual reference for the section's composition and styling language.

## My call

**Go with Option B.** The Taxonomy is the center of gravity for the archetype classifier work in Phase 3 of the Claude Code prompt — if the visual reference is wrong there, Claude Code will either under-ship or get stuck reconciling the two sources. 30 minutes of Figma to close the gap is worth it.

Here's a paste-ready Figma Make follow-up prompt for Option B:

```
Expand FanbaseArchetypesTaxonomy.tsx to match the v5 spec exactly:

1. Change the header from "The eight fanbases" to "The eighteen fanbases"
   and the intro from "one of eight" to "one of eighteen primary
   archetypes (any of eight modifiers)."

2. Add these 10 archetypes to the existing 8 (same card format,
   description + 2-3 teams at match %, signature phrase):

   - Newly Crowned: fresh champions still in honeymoon, every conversation
     anchored to the title game. "We did it." Teams: WASH 96%, LSU 82%.
   - Stockholm Syndrome: fans so long-suffering they root for suffering
     itself. "It's not supposed to be fun." Teams: NW 94%, VAN 91%,
     KANS 78%.
   - Service Academy: tradition-first, outcome-agnostic. "The uniform
     still matters." Teams: ARMY 98%, NAVY 96%, AF 94%.
   - Coach Cult: identity fused to one coach; the team is almost
     incidental. "In Coach we trust." Teams: KYS 92%, UCLA 87%.
   - HBCU Standard: cultural institution first, football program second.
     "The Classic is the real season." Teams: JKST 97%, PVAM 93%.
   - Mercenary: roster built via portal, no pretense of development.
     "Who's new this week?" Teams: TTU 91%, COL 88%.
   - Celebrity Appointment: program's national profile outpaces results.
     "The lights are on us now." Teams: COL 94%, DEI 82%.
   - Petulant Blueblood: former power refusing to concede decline.
     "We're still us." Teams: TAMU 88%, TENN 80%, OU 76%.
   - Regional Identity: fanbase defined by place more than program.
     "For the state." Teams: WVU 94%, MISS 88%, ARK 83%.
   - Sleeper: quiet program outperforming expectations without attention.
     "Wait, they're 9-2?" Teams: MEM 89%, JMU 86%, LIB 82%.

3. Below the 18-card grid, add a horizontal strip of 8 modifier chips:
   Emerging, Entrenched, Upstart, Fading, Rebuilding, Reloading, In
   Crisis, Ascendant. Each chip: uppercase mono, 10px, small amber dot
   next to it. Caption below: "Every fanbase carries one primary
   archetype and, this week, one of eight modifiers."

4. Inside each archetype card, add a 6-week migration sparkline at the
   bottom showing the count of fanbases in that archetype by week. Below
   the sparkline in serif italic: "Washington joined; Miami left." (or
   similar 2-clause line when relevant; leave blank when stable).

5. Replace all escaped apostrophes (\') in the `take` strings across
   FanbaseArchetypesTaxonomy.tsx AND RivalryMatrix.tsx with HTML entity
   &rsquo; so the curly-apostrophe renders correctly.

Do not touch any other section. Keep existing 8 archetypes exactly as
they are — only add the 10 new ones and the modifier strip and sparklines.
```

## After that pass lands

Delete `src/app/AppV5.tsx` from the zip (dead code), re-export, and kick off Claude Code using `CLAUDE_CODE_V5_IMPLEMENTATION_PROMPT.md`. The reference will be complete and Claude Code's Phase 1-5 can proceed without ambiguity.

## Sidebar findings — worth logging but not gating

- `TEAM_COLORS` in `TeamColors.ts` and the inline `TEAM_COLORS` in `AppV5.tsx` have slightly different Alabama colors (`#828A8F` vs `#9E1B32`). Once AppV5.tsx is deleted this disappears.
- Footer `Subscribe · Wednesdays 9AM ET` is a great weekly-rhythm signal — carry this into reporting.py footer exactly.
- Masthead "Model Week 21" is a nice editorial touch. Include in the `HUB_ISSUE_047` dict for Claude Code to swap weekly.
- The three field recordings in LexiconWeek are excellent copy. When Phase 4 implements lexicon mining, the editorial voice target is exactly this.

---

**Bottom line:** v5 is A− work product, one section short of shippable reference. Run Option B, then kick off. Do not run Claude Code against the zip as it stands; it'll produce an 8-archetype hub we'll have to go back and fix.
