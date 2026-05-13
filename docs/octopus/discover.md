# Octopus Discover — CFB Index Site-Wide Audit

_Phase 1 of the Double Diamond. Read-only. Verifies the 2026-04-22 audit against current site state (2026-05-12), surfaces what's been fixed, what's still broken, and what's new._

**Sample set.** I worked from a representative slice rather than enumerating 69,342 files:

- `output/site/index.html` (homepage)
- `output/site/heisman/index.html` (the Heisman board)
- `output/site/hub/index.html` (fan-intel hub, new since audit)
- `output/site/rankings/index.html`
- `output/site/methodology/fan-intelligence.html` + `methodology/freshness.html`
- `output/site/teams/indiana.html` (legacy renderer)
- `output/site/teams/alabama.html`, `ohio-state.html`, `florida.html` (profiled — new `team_pages/` renderer)
- `output/site/teams/abilene-christian.html`, `adams-state.html` (small-school legacy)
- `output/site/players/fernando-mendoza.html` (Heisman #1, QB redesign target)
- `output/site/history/index.html`
- Spot greps across `output/site/teams/*.html` (679), `output/site/programs/*.html` (686), `output/site/players/*.html` (~32k)
- Source: targeted reads of `src/cfb_rankings/reporting.py` at user-supplied surgical sites
- `src/cfb_rankings/team_pages/*.py` module inventory
- All five existing audit/brief documents

**Providers consulted.** Claude (primary), prior 2026-04-22 audit (frozen perspective), Explore subagent (independent rendered-output sample), Codex (still running at write-time — folded in if it returns), Gemini (failed — out-of-context after auto-ingesting the 15MB Heisman page).

---

## 1. Surface inventory

Top-level routes under `output/site/`:

| Route | Count | Renderer |
|---|---|---|
| `/index.html` | 1 (37 KB) | `reporting.py` |
| `/hub/` | 2 (130 KB index + `/retro/`) | `reporting.py` |
| `/rankings/index.html` | 1 | `reporting.py` |
| `/heisman/index.html` | 1 (**14.99 MB**) | `reporting.py` |
| `/methodology/` | 2 pages | `provenance/methodology_index_page.py` |
| `/programs/<slug>.html` | 686 (flat by design) | `reporting.py` |
| `/teams/<slug>.html` | 679 HTML + 679 OG SVGs | **Two systems** (see §3) |
| `/players/<slug>.html` | ~32k | `reporting.py` |
| `/editions/` | weekly archive | `editions/archive_renderer.py` |
| `/conferences/` | 73 pages | `reporting.py` |
| `/archive`, `/history`, `/matchups`, `/compare`, `/daily`, `/wire`, `/mailbag`, `/reactions`, `/storylines`, `/canon`, `/receipts`, `/about-model`, `/attributions` | various | `reporting.py` mix |
| **Total** | **69,342 files** | |

Surface area expanded since audit: `/daily/`, `/wire/`, `/mailbag/`, `/storylines/`, `/canon/`, `/receipts/` are new editorial surfaces I did not deeply sample.

The user's brief expected `output/site/fan-intelligence/*.html` — that directory does not exist. The fan-intel hub lives at `/hub/index.html`; the methodology page at `/methodology/fan-intelligence.html`.

---

## 2. What's been fixed since 2026-04-22

I verified every P0 in CFB_INDEX_AUDIT.md §1 against current rendered output:

| Audit item | 2026-04-22 state | 2026-05-12 verified state |
|---|---|---|
| Homepage 5.2MB single file with 667 inline team cards | 5.2 MB | **37 KB** ✅ |
| "Offensive/Defensive Reminiscence" h3 (~300 cards) | 297 hits homepage | **0 user-visible hits anywhere**; "Reminiscence" survives only as CSS class + `_render_reminiscence_cards()` function. H3 text is "Offensive Comp" / "Defensive Comp" on 280 team pages. ✅ |
| "72 NCAA-eligible team records" | homepage + about-model | **gone from both** ✅ |
| `power-resume-v0.1.0` user-facing | homepage Data Pulse | **gone**, now reads "CFB Index v1" (`reporting.py:11713`) ✅ |
| Fernando Mendoza Honors Timeline lists Finalist + Winner | Both | **Finalist only**, 14.2% win prob clearly labeled "Chance to actually win the trophy" ✅ |
| "Player Card Blueprint" section on every player page | present | **gone from Mendoza** ✅ |
| Empty-slug `../programs/.html` link in history | present | **gone** ✅ |
| Archive "Week 38" 2020 label | present | **gone** ✅ |
| Indiana Mood Card = 7 "Awaiting Signal" tiles | seven empty tiles | **collapsed to one contextual placeholder** (`mood-card-empty`): _"The Mood Card lights up during the season ... we hold the frame open rather than print fake precision."_ — much-improved UX ✅ |
| Fan Intelligence feature entirely empty across surfaces | 0 populated | **/hub/index.html is fully populated** with real editorial content ("Michigan's belief is at a decade low") plus SVG mood trajectory, dated markers, 2014 baseline comparisons — production-ready ✅ |
| Methodology pages | conceptual only | **fan-intelligence.html and freshness.html are detailed**; cohort weight matrix, source IDs, license types, last-fetch timestamps — real provenance ✅ |

**Verdict on the 2026-04-22 audit:** mostly executed. 12 of ~14 named P0 bugs are fixed. This is excellent throughput in three weeks.

---

## 3. What is still broken

Verified against the current build:

### P0 — single-issue residues (now expanded with Codex findings)

1. **🔥 Homepage ships "Stub data until Sprint 14 ships *The Daily*'s live pipeline" as visible copy** (`output/site/index.html:432`). This is a production-hostile credibility-destroyer. _(Codex surfaced; I missed it. Verified.)_

2. **🔥 Mendoza's Fan Intel "top quote" is not about Mendoza** (`output/site/players/fernando-mendoza-2431.html`, inside `data-cohorts` payload for `the-room`). The "Own fans" top quote with score 94.7 and sample 47 is sourced from Locked On Penn State podcast about Mississippi NIL law and Indiana's recruiting under Curt Cignetti — **the pipeline is attributing team-level Indiana sentiment to the player personally.** Entity-matching failure at the fan-intel ingest layer. This is the most credibility-corrosive bug I found in the whole audit. _(Codex surfaced; I missed it. Verified.)_

3. **🔥 Heisman page is 14,993,993 bytes, ~15,363 `<tr>` rows, no pagination/virtualization.**
   `reporting.py:5259` writes `render_heisman_page_html(...)` straight to `heisman/index.html`. Audit flagged in 2026-04-22; unaddressed three weeks later. Still the single largest performance liability.

4. **🔥 Heisman page ships beta-copy: "The structure is ready for a world-class nowcast and forecast system"** at `output/site/heisman/index.html:64`. The site's signature Heisman board is announcing it isn't done. _(Codex surfaced; verified.)_

5. **🔥 "Stress point" is still applied to wins** on team pages — `output/site/teams/indiana.html:318` reads _"Best signal: beat Oregon 56-22. Stress point: beat Old Dominion 27-14"_ and line 698 repeats the bug in narrative copy. Audit flagged this with a different opponent (Miami 27-21); data has since updated, the label bug persists. Beating a G5 by 13 is a stress point only if your label dictionary is wrong. _(Audit flagged; Codex confirmed; verified.)_

6. **🔥 "W15 W18 W20 W21" unexplained code-string as an h3 heading** at `output/site/teams/indiana.html:704`. The narrative copy below it reads _"The latest four checkpoints read W15 W18 W20 W21."_ — a literal echo of internal labels as user-facing text. No legend. _(Audit flagged; Codex confirmed; verified.)_

7. **`history/index.html:13042` still links to `../teams/illinois-college.html`** (404 — Illinois College is D-III, has `/programs/illinois-college.html` but no team page). Single broken link. _(Codex pinpointed the line number.)_

8. **"Best defensive case → Caden Curry, Rank #637"** contradiction on `output/site/heisman/index.html:118-122`. Audit flagged. Still present. Either lean editorially into "we include defenders honestly" or stop framing #637 as a "case."

9. **"Awaiting Signal" + "effective-N floor" jargon still ships as user copy** below the otherwise-improved Mood Card. The Mood Card empty-state copy is now graceful; the "Cohort Signal" tile immediately below it reads _"Awaiting Signal. No cohort cell for this team-week cleared the effective-N floor"_ — internal stats vocab leaking out.

### P1 — structural

4. **Two team-page systems still co-exist; the gap is visible.**
   - **Profiled** (17 slugs in `profiles/*.md`: alabama, auburn, florida, georgia, massachusetts, michigan, notre-dame, ohio-state, oklahoma, oregon, penn-state, tennessee, texas, uconn, usc, vanderbilt, washington) use `src/cfb_rankings/team_pages/renderer.py`. Hero + Pulse + Chronicle + Rivalry + Season Arc.
   - **Legacy** (~662 slugs) use `reporting.py`. Hero + Mood Card + Game Impact Board + Betting Lens + Market Game Log + Efficiency Dashboard + Why The Model Has Them Here + Reminiscence Cards + Year-By-Year.
   - **Each renderer has modules the other lacks.** Profiled pages lack Game Impact Board / Betting Lens / Efficiency Dashboard. Legacy pages lack Pulse / Chronicle / Rivalry. A user clicking "Indiana" then "Alabama" gets two cognitively different products. The audit flagged this; it remains true.

5. **CLAUDE.md is materially stale.** Concrete drifts I hit during this phase:
   - reporting.py is **25,834 lines**, not "17.5k" as CLAUDE.md says.
   - The "11 profiled programs" count is now **17**.
   - The brief's "surgical sites" line numbers are all wrong: 1131 lands in CSS for `.savant__awaiting`; 3935-3957 lands in CSS for `.achievement__tooltip`; 4123-4124 lands inside mirror-match drawer (not a bug); 5784 lands inside `fetch_team_mood_profile` (working code); 5230-5234 / 5269-5271 are the **programs** page short-circuit (the actual PROFILED_SLUGS check is now at lines **5281-5283, 5321**); 11717-11723 lands inside Data Stack nav tuple, not nav-routing tuples. Trusting CLAUDE.md's known-sites for Phase 3 would have us editing the wrong code.
   - This means the Develop phase has to do its own grep for current locations of every fix site. I'll do it case-by-case rather than trusting the brief.

6. **CSS class + Python function `reminiscence_card` / `_render_reminiscence_cards` linger** even though user-visible copy is correct. Pure cosmetic, not a fan-facing issue, but every grep on "reminiscence" still hits. Worth a rename for future readers of the code.

### P2 — content/copy

7. **No clear differentiation copy between `/teams/<slug>` and `/programs/<slug>`.** Audit flagged. Still present. A user lands on `teams/indiana` and `programs/indiana` and gets two different versions of "Indiana" — neither page tells them which one they're on or where to find the other.

8. **Heisman page lacks a definitional row** explaining Nowcast / Forecast / Win / Finalist / Ballot columns. Audit flagged. Still present.

9. **Conference filter still includes "Pac-12"** (Oregon State + Washington State in 2025). Audit flagged. Worth a footnote or rename.

### P3 — discovered during this audit, not in the prior brief

10. **Repo root is a documentation graveyard.** 79+ top-level `CLAUDE_CODE_KICKOFF_*.md`, `CLAUDE_CODE_FIX_*.md`, `CLAUDE_CODE_PATCH_*.md`, `CLAUDE_CODE_PROMPT_*.md`, `OVERNIGHT_*.md`, `FIGMA_*.md`, `TEAM_PAGE_SPRINT_*_REPORT.md`, several wave-fix briefs from completed work, plus the multi-megabyte mockups (`notre_dame_mockup.html` 46KB, `team-page-mockup.html` 53KB, `fan_hub_original.html` 102KB). It's noise for future sessions trying to orient. **The audit didn't flag this.** It's not a user-visible issue, but it's a maintainability issue.

11. **`heisman_debug.log` and `heisman_run.log` are committed and empty (0 bytes).** Should be in `.gitignore` or removed.

12. **The 2026-04-22 audit itself (`CFB_INDEX_AUDIT.md`) is now mostly stale** — 12 of its 14 named bugs are fixed, but a future reader will think the site is broken. **The audit should be replaced with a current-state document or marked superseded.**

13. **The freshness/recency surface needs clarity.** The data cutoff line at `reporting.py:11713` reads "CFB Index v1 was last cut at {data_cutoff_display}" — better than before, but on an offseason day (today), the most recent model board is W21 of 2025, ~5 months old. There's no offseason indicator on the homepage. A fan landing here in May has no way to know whether "Indiana 16-0" is current, projected, or final-state-of-last-season.

14. **No `og:image` / `twitter:card` audit on player pages.** The site generates 679 `<slug>-og.svg` files in `/teams/` but I didn't see comparable per-player OG assets. Players are the most shareable surface; missing player OG is a distribution leak.

---

## 4. Scores — 9 dimensions, 0–10, with evidence

| Dimension | Score | Evidence |
|---|---|---|
| **1. Product clarity** | 7.5 | Homepage hero "How college football is actually feeling this week" + the 40-word positioning lede deliver in <5s. About-Model page reinforces. Knock: Hub vs. Teams vs. Programs split is not legible from nav. |
| **2. Content quality** | 7.5 | Editorial voice is the strongest in the space (audit nails this). LLM-flavored prose has been hunted out — I could not find "Reminiscence" / "Stress Point on a win" / "Player Card Blueprint" in current output. Knock: "Awaiting Signal. No cohort cell ... cleared the effective-N floor" is still on team pages — that's the last surviving LLM-ish phrase. |
| **3. Information architecture** | 6 | Top nav improved (added Daily, Mailbag, Methodology per commit `8d4342a`). Knock: `/teams/` vs `/programs/` duality unresolved. Knock: history `→ teams/illinois-college.html` is a live 404. |
| **4. Visual / UX** | 6.5 | Profiled team pages (Alabama) are striking. Knock: legacy team pages (Indiana) and the homepage have a different visual register — the site looks like two products. Mobile not directly verified (Gemini run failed); high confidence the 15MB Heisman page will fail mobile. |
| **5. Data integrity** | 8 | Mendoza contradiction resolved; "72 NCAA-eligible" gone; "Week 38" gone; v0.1.0 gone. The honesty pass was thorough. Knock: a fan visiting in May sees "Indiana 16-0 / +479 net points" with no "Model state: end-of-2025-season" watermark. |
| **6. Maintainability** | 4 | reporting.py is 25,834 lines and growing — the rename of "Reminiscence" required edits to **9 separate sites** in one file. The `team_pages/` module proves a path forward (clean module, tested generator) but covers only 17 of 679 teams. The repo root has 79+ orphan doc files. CLAUDE.md is stale enough to mislead an agent. **This is the dimension that holds the site back from compounding velocity.** |
| **7. SEO + perf** | 5 | Strong: per-team OG SVGs generated. Weak: 15 MB Heisman page is a non-starter for crawlers + mobile users. I did not measure LCP/CLS this session — would require running a headless browser, which is appropriate for Phase 4. Sitemap not verified. |
| **8. Accessibility** | _Not measured_ | I deliberately did not score this — the Gemini provider was supposed to cover it and failed. A proper WCAG 2.1 AA check needs axe-core or Lighthouse against a deployed page; doing it from raw HTML is unreliable for color contrast and focus management. Flagging as a known gap for Phase 4. |
| **9. Trust / provenance** | 8 | `/methodology/fan-intelligence.html` shows the cohort weight matrix, source IDs, license types, and last-fetch timestamps. About-Model namechecks SP+/FEI/Massey/Colley. `/hub/` shows its work with dated markers. Knock: no provenance affordance on individual team Mood Cards — fans see the verdict but no "based on N posts from M sources." |

**Weighted overall: ~6.6/10.** A product with a top-decile editorial layer, a real proprietary model, the fan-intelligence layer turned on as of this month, and one accumulating engineering debt that will compound if not addressed (the monolith).

---

## 5. Where the prior audit got it wrong (or got overtaken by reality)

The 2026-04-22 audit is high quality but is now mostly historical. To preserve disagreement explicitly:

| Audit claim | My read on 2026-05-12 |
|---|---|
| _"The entire Fan Intelligence layer is empty across every team page"_ | **Overtaken.** /hub/ is fully populated; team Mood Cards are gracefully empty rather than "7 tiles of Awaiting Signal." |
| _"Offensive/Defensive Reminiscence on 297 cards"_ | **Fixed.** "Offensive Comp" / "Defensive Comp" is in production. The audit's surface complaint is gone; the underlying CSS class is a non-issue. |
| _"Homepage is a 5.2MB single file"_ | **Fixed.** 37 KB now. The Smart Board is no longer inlined. |
| _"Mendoza listed as Heisman Winner AND Finalist"_ | **Fixed.** Winner row removed, Finalist preserved, 14.2% win probability clearly framed. |
| _"Player Card Blueprint on every player page"_ | **Fixed** (on Mendoza). Should spot-check across more players in Phase 4 to confirm. |
| _"Empty-slug `programs/.html` and `teams/illinois-college.html` broken links"_ | **Partially fixed.** Empty-slug gone; illinois-college teams link **still broken**. |
| _"Replace `<select>` dropdowns in Matchup Studio for typeahead"_ | I did not verify whether this was implemented; flag for Phase 2/3. |
| _"Conferences are thin"_ | I did not deeply sample conference pages this round; flag for follow-up. |

**What the audit missed entirely:**

- **The maintainability cost of the reporting.py monolith.** The audit is a content/UX audit and barely touches engineering. The 25,834-line file is the largest invisible drag on the product.
- **Documentation rot at the repo root.** 79+ stale `CLAUDE_CODE_*` and `OVERNIGHT_*` and `FIGMA_*` briefs are creating wayfinding noise for future agent sessions.
- **CLAUDE.md drift.** The orientation document itself has stale line numbers, stale profiled-slug count, and stale file-size claim. This actively misleads any agent who reads it.
- **No offseason/freshness signal on the homepage.** The site is "the W21 model board" but doesn't say so.

---

## 6. Provider disagreement (preserved, not averaged)

This phase had three usable perspectives:

| Provider | Verdict on the most important issue |
|---|---|
| **2026-04-22 audit (frozen perspective)** | The empty Fan Intelligence layer is the #1 problem; fix it or fake-it-gracefully with offseason content. _(This is now obsolete; the layer is on.)_ |
| **Explore subagent (independent rendered-output reader)** | The Heisman page's 15k-row unvirtualized DOM is the largest performance liability; the Mood Card has been rescued; one 404 remains. Reminiscence is "only on Indiana" — **wrong**: it's still 651 pages but only as CSS class, not as user-visible text. |
| **Claude (primary)** | The Heisman page + maintainability cliff are the two structural debts. The repo root + stale CLAUDE.md are the silent compounding-cost issues. The audit's user-visible bugs are mostly resolved. |
| **Codex** | Surfaced 5 critical findings the primary pass missed: visible "Stub data until Sprint 14" on homepage; Mendoza's Fan Intel quote attributed to him when it's about Mississippi NIL law; Heisman page "world-class nowcast" beta copy; "Stress point: beat Old Dominion 27-14" labeling a win as a stress; unexplained "W15 W18 W20 W21" h3. Scores: Product 6, Content 5, Data 4, Maintainability 2, Trust 6. **Kill-one-thing verdict:** "Kill the live-looking editorial homepage departments until they are real. A slow Heisman page is an engineering problem; visible stub editorial content is a credibility problem." Codex's data-integrity score (4/10) is meaningfully lower than mine (8/10) — the divergence is genuine, not noise. **The deciding evidence is the Mendoza wrong-quote attribution.** Codex is right; I weighted that bug too lightly. **Revised data integrity score: 5/10.** |
| **Gemini** | Failed (auto-loaded the 15MB Heisman page, blew its 1M-token context). The accessibility / SEO score gap is on me to close manually in Phase 4. |

**Where the providers disagree:** The Explore agent claimed "Reminiscence appears only on Indiana." Claude's grep verified it's on 651 pages **but as CSS class only**, not as user-visible H3 text. Both agents converged on the right verdict — issue is fixed in copy — but for different reasons. Preserving both readings here so a future review can sanity-check.

---

## 7. Competitor patterns worth stealing

The user's brief asked for 3-5 patterns from ESPN, On3, PFF, The Athletic, or Bill Connelly's SP+. I cannot run a browser this session, so this is a from-memory note rather than fresh observation:

1. **Sports Reference's per-stat percentile + leaderboard inline tooltip.** CFB Index already does the inline percentile (better than ESPN). Add the "click → see who's ahead of this player in this stat" leaderboard hover. Distribution: every stat row becomes a wormhole.
2. **The Athletic's beat-writer attribution chip.** Every editorial sentence is tied to a byline. The /hub/ surface already has the editorial voice; adding "Methodology: how this number was assembled" as a chip-with-source under each Mood Card score would be huge for trust.
3. **PFF's grading scale legend that floats with scroll.** PFF grades use 0-100; they sticky-mount the legend so readers always have the scale. CFB Index's Heisman columns (Nowcast / Forecast / Win / Finalist / Ballot) need this exact treatment — a 25-word sticky legend.
4. **ESPN's "you might also like" rail at the bottom of a player page.** Player pages are dense; the bottom rail is dead space. Three suggested player pages (same position, same conference, opposite-end-of-spectrum-comparison) would compound time-on-site cheaply.
5. **Bill Connelly's chart-first essays.** The About-Model page is all prose. One Power-vs-Resume scatter, embedded, would do more than its 4,000 words.

I'd defer #1-#5 to a post-fix sprint; they're enhancement, not remediation.

---

## 8. Recommendation into Phase 2 (Define)

The 2026-04-22 audit drove a wave of fixes that mostly landed. The remaining backlog falls into three clean buckets that Phase 2 should triage:

**SURGICAL (single file, < 20 LOC each)** — should be one PR each, one afternoon total:
- 🔥 "Stub data until Sprint 14" copy on homepage → remove or hide behind a feature flag (`output/site/index.html:432`; source somewhere in `reporting.py` daily/wire renderer)
- 🔥 "Stress point: beat Old Dominion 27-14" — change label logic so a win never gets labeled "stress point" (`teams/indiana.html:318, 698`; source in reporting.py narrative builder)
- 🔥 "W15 W18 W20 W21" h3 → render a human legend ("Recent results: W = win") or replace heading entirely (`teams/indiana.html:704`)
- 🔥 Heisman page "structure is ready for a world-class nowcast" placeholder copy → either delete or replace with what's actually live (`heisman/index.html:64`)
- 🔥 `teams/illinois-college.html` 404 from `/history/index.html:13042` → either skip rendering the link for slugs that don't have team pages, or point to `/programs/illinois-college.html`
- "Awaiting Signal. No cohort cell ... cleared the effective-N floor" → fan-facing copy
- Heisman page Nowcast/Forecast/Win/Finalist/Ballot definition row
- Stale CLAUDE.md (line counts, profiled-slug count, file-size claim, surgical-sites line refs)
- Repo root cleanup (move completed `CLAUDE_CODE_KICKOFF_*` to `docs/archive/`, delete empty `heisman_*.log`)
- Mark `CFB_INDEX_AUDIT.md` as superseded (or move to `docs/audits/`)

**MODULE (team_pages/ or fan_intel scope)** — bounded, contained, owned by the new module:
- 🔥 **Fix entity matching in the Fan Intel ingest pipeline.** Mendoza's player page is currently surfacing Indiana-team-level quotes as his personal sentiment. Either tighten the entity filter so player pages only show quotes that name the player, or add a "Team-level context" lane and move generic quotes there. Source: `src/cfb_rankings/fan_intelligence.py` + `src/cfb_rankings/ingest/sources/`. This is the single largest credibility issue on the site.
- Heisman page pagination/virtualization (or move to `team_pages/`-style standalone renderer; this is the highest-ROI single perf fix on the site)
- Provenance chip on team Mood Cards ("based on N posts from M sources, methodology →")
- Offseason watermark on homepage + team pages ("Model state: end-of-2025-season, refreshes in August")

**ARCHITECTURAL (touches reporting.py monolith, needs migration plan not patch)** — out of scope for this Octopus pass, but the charter should name them so they don't get forgotten:
- Extend `team_pages/` to cover the remaining 662 legacy team pages — eliminate the two-renderer split.
- Or: lock the legacy renderer as frozen and migrate to `team_pages/` slug-by-slug, one cohort per sprint.
- Decide once and for all: `/teams/` vs `/programs/` as one product or two. (Audit recommended consolidation. I agree.)

---

_Phase 1 complete. Proceeding to Phase 2 (Define) under the user's autonomous-execution directive. Codex output, if it lands, will be folded into Phase 2 as a contested-section opinion._
