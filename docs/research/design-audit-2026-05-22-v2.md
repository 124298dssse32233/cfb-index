# CFB Index — Exhaustive Design + Content + Operational Audit (v2)

**Generated 2026-05-22.** Supersedes [`design-audit-2026-05-22.md`](design-audit-2026-05-22.md). Adds 12 audit axes not previously covered. Every claim is anchored in either a live-URL HEAD/GET response or a file:line in the repo.

---

## How to read this doc

- **Axis A–C** = covered in v1 (archetype gap, offseason copy bugs, structural spec violations). Re-summarized below for completeness.
- **Axis D–O** = new in v2. These represent material risks the v1 audit missed.
- **Tier −1 / 0 / 1 / 2 / 3** = priority. Tier −1 is "broken, fix before sharing." Tier 3 is "polish backlog."
- Every line item ends with either a `[file:line]` pointer or a `[URL]` evidence link.

---

## Audit data captured 2026-05-22 (used throughout)

Live page size sweep:

| Page | Bytes | Notes |
|------|-------|-------|
| `/heisman/` | 14,868,564 | 15MB → perf liability |
| `/players/` (directory) | 31,478,989 | 31MB → larger perf liability |
| `/history/` | 5,595,709 | 5.6MB |
| `/rankings/` | 933,115 | OK |
| `/programs/` | 690,941 | OK |
| `/teams/` (directory) | 418,077 | OK |
| `/teams/alabama.html` | 130,060 | OK |
| `/teams/florida-international.html` | 101,110 | OK |
| `/players/fernando-mendoza-38276.html` | 90,875 | OK |
| `/wire/` | 72,724 | OK |
| `/conferences/` (directory) | 50,312 | But individual conf pages all 404 (see Axis D) |
| `/` | 35,146 | OK |
| `/storylines/` | 23,898 | OK |
| `/editions/` | 21,283 | OK |
| `/compare/` | 14,969 | OK |
| `/about-model/` | 12,431 | OK |
| `/portal-heat/` | 10,048 | OK |
| `/anniversary/today/` | 7,728 | OK |
| `/methodology/` | 4,331 | Suspiciously thin |
| `/hub/vibe-shifts/` | 213 | **Meta-refresh stub** (redirects to `/hub/vibe-shifts/2025/18/`) |

---

## Axis A — Archetype renderer gap (from v1, summarized)

Per [docs/design-system/30-page-archetypes.md:339-344](docs/design-system/30-page-archetypes.md), 5 of 6 archetype renderers are "TO BUILD." Only `team_pages/renderer.py` (17 profiled teams) conforms.

| Archetype | Spec status | Affected URLs |
|-----------|-------------|----------------|
| Article | TO BUILD | `/daily/`, `/mailbag/`, `/editions/<n>/<slug>` |
| Dashboard | TO BUILD | `/`, `/heisman/`, `/rankings/`, `/hub/vibe-shifts/`, `/compare/` |
| Profile | Partial | 17 profiled teams ✓ · ~662 unprofiled teams + 17,836 players + 665 programs + conferences all use legacy `reporting.py` |
| Database | TO BUILD | `/wire/`, `/editions/`, `/canon/`, `/players/` (dir), `/portal-heat/`, `/recruit-board/`, `/storylines/` |
| Tentpole | TO BUILD | 9 marquee editions per year (none shipped yet) |
| Anniversary | TO BUILD | `/anniversary/today/`, `/saturdays-past/<date>/` |

**Impact:** clicking from a profiled team page to an unprofiled one feels like a different site. This is the single most visible "feels broken" issue for any visitor.

---

## Axis B — Offseason copy bugs (from v1, expanded)

**~22 high-visibility instances** of present-tense / live-tracker copy that doesn't switch via `is_offseason()`. Full table:

### Cluster B1: `/rankings/`
- [reporting.py:13517](src/cfb_rankings/reporting.py) "No meaningful risers this week" — empty state
- [reporting.py:13518](src/cfb_rankings/reporting.py) "No meaningful faders this week" — empty state
- [reporting.py:13526](src/cfb_rankings/reporting.py) "Teams whose stock dropped most against the board this week" — section-note
- [reporting.py:14844](src/cfb_rankings/reporting.py) "how strong teams look right now, and what they have actually earned" — selection-room intro

### Cluster B2: `/players/<slug>.html` (×17,836 pages)
- [reporting.py:10350](src/cfb_rankings/reporting.py) `title = "What makes this player interesting right now"`
- [reporting.py:17731](src/cfb_rankings/reporting.py) same h2 in a different code path

### Cluster B3: `/hub/vibe-shifts/`
- [hub_page.py:214](src/cfb_rankings/hub_page.py) default kwarg `updated_label="Updated this week"`
- [hub_page.py:812](src/cfb_rankings/hub_page.py) "updated this week" — module data label
- [hub_page.py:1022](src/cfb_rankings/hub_page.py) same
- [hub_page.py:1157](src/cfb_rankings/hub_page.py) "this week, one of eight modifiers"
- [hub_page.py:1175](src/cfb_rankings/hub_page.py) "updated this week"
- [hub_page.py:1242](src/cfb_rankings/hub_page.py) "No featured phrase this week" — empty state
- [hub_page.py:1271](src/cfb_rankings/hub_page.py) "spiked in [team] fan conversations this week"
- [hub_page.py:1347](src/cfb_rankings/hub_page.py) "Save this week's cards" CTA

### Cluster B4: `/conferences/*`, `/compare/`, `/heisman/` remnants
- [reporting.py:12280](src/cfb_rankings/reporting.py) "[Conference] reads like a balanced league right now"
- [reporting.py:13259](src/cfb_rankings/reporting.py) "looks stronger right now on the predictive board"
- [reporting.py:16452](src/cfb_rankings/reporting.py) "CFBD currently exposes game betting lines, not award futures" — dev commentary

### Cluster B5: `/methodology/`, `/about-model/`
- [reporting.py:14765](src/cfb_rankings/reporting.py) "What is loaded locally right now"
- [reporting.py:18985](src/cfb_rankings/reporting.py) "how strong a team is right now"
- [reporting.py:19001](src/cfb_rankings/reporting.py) "best team right now"
- [provenance/methodology_page.py:308](src/cfb_rankings/provenance/methodology_page.py) `<h3>Top divergence this week</h3>`

### Cluster B6: shared footer text (affects team / player / program / conference page footers)
- [reporting.py:500](src/cfb_rankings/reporting.py) `_power_resume_gap_text` "Power and resume are essentially aligned right now"
- [reporting.py:504](src/cfb_rankings/reporting.py) "Power is running … ahead of resume right now"
- [reporting.py:508](src/cfb_rankings/reporting.py) "Resume is running … ahead of power right now"

### Cluster B7: homepage scenarios (already mostly OK via `is_offseason` flag, but fallback text leaks)
- [reporting.py:14141](src/cfb_rankings/reporting.py) "The cleanest high-end matchup on the board right now"
- [reporting.py:14152](src/cfb_rankings/reporting.py) "who looks strongest right now versus who has earned"
- [reporting.py:14484, :14637](src/cfb_rankings/reporting.py) fallback hero_title "How college football is actually feeling this week"
- [players_landing.py:196](src/cfb_rankings/players_landing.py) "right now. The Room tracks who fans are..."

---

## Axis C — Other structural design-spec violations (from v1)

### C1 — Filter-widget `<h2>` hierarchy bug (8 sites)
[reporting.py:14937, :15327, :15826, :15975, :16299, :16514, :16658, :22012](src/cfb_rankings/reporting.py) — all render `<h2>Board Controls</h2>` (or similar) at the same hierarchy as editorial sections. Filter widgets should be visually subordinate.

### C2 — No hero finding zone on Dashboard pages
Per [30-page-archetypes.md:67-98](docs/design-system/30-page-archetypes.md), Dashboard pages should have a top-of-page eyebrow + big number (clamp 36-64px) + sentence + caption + sample-size chip. None of `/`, `/heisman/`, `/rankings/`, `/hub/vibe-shifts/` has this.

### C3 — No methodology footer on Dashboard pages
Per same spec, Dashboard pages should end with "How we measure this →" + sample-size summary + "Updated" timestamp. Missing across all four.

### C4 — Dev commentary leaking into user-facing copy
- [reporting.py:14844](src/cfb_rankings/reporting.py) "The list is meant to read like a clean selection-room board"
- [reporting.py:14765](src/cfb_rankings/reporting.py) "What is loaded locally right now"
- [reporting.py:16452](src/cfb_rankings/reporting.py) "CFBD currently exposes game betting lines, not award futures"

### C5 — Profile archetype split-personality
17 profiled teams use `team_pages/renderer.py`. 662 unprofiled teams + 17,836 player pages + 665 program pages + every conference page use the legacy `reporting.py` renderer. **The two look visibly different.** This is the most visible "feels broken when clicking around" issue.

---

## Axis D — Live-site navigation / content gaps (NEW)

### D1 — `/conferences/<slug>` ALL 404 (BROKEN)
- `/conferences/sec.html` → 404
- `/conferences/big-ten.html` → 404
- `/conferences/acc.html` → 404
- `/conferences/sec_pulse.html` → 404
- `/conferences/sec/` → 404

[conferences_pulse/renderer.py:228](src/cfb_rankings/conferences_pulse/renderer.py) writes `<slug>_pulse.html`. Workflow does call `python -u manage.py render-conferences-pulse --all` ([compute_full_pass.yml:231](.github/workflows/compute_full_pass.yml)). **But the output isn't appearing on production.** Either: (a) the CLI isn't running, (b) the output dir is wrong, (c) the files aren't being uploaded to the artifact, or (d) the live deploy chain is dropping them. Needs investigation. **Marker: 0 individual conference pages exist on production today.**

### D2 — `/players/nfl-pipeline/` returns 404
Despite [nfl_pipeline.py:233](src/cfb_rankings/nfl_pipeline.py) existing with content. Same render-not-shipping pattern.

### D3 — `/hub/vibe-shifts/` is a 213-byte meta-refresh stub
Redirects to `/hub/vibe-shifts/2025/18/`. Works in browsers but is bad form (lighthouse penalty, slower TTFB, breaks no-JS clients). The real page is at the nested URL.

### D4 — Custom 404.html exists but Vercel returns empty 404 body
- `/404.html` directly: 200 OK, 6,287 bytes, h1 "Wrong snap." (the friendly custom page)
- `/this-does-not-exist/`: 404 status, **0 bytes body**

Vercel's default behavior is to serve `404.html` automatically on 404 errors. Something in our `vercel.json` or the `trailingSlash: true` interaction is breaking this. Needs config fix.

### D5 — Footer present on most pages but **MISSING from `/rankings/` and `/players/*` (17,836 pages)**
Tested via `<footer>` tag presence:
- Homepage: 1 footer ✓
- Wire: 1 footer ✓
- Alabama (profiled): 2 footers ✓ (probably nested article footer + page footer)
- FIU (unprofiled): 1 footer ✓
- Mendoza (player): **0 footers** ✗
- Rankings: **0 footers** ✗

The legacy renderer's `_full_page_html` (or whatever wraps them) seems to omit the footer on these two surfaces.

### D6 — Footer link absolute-URL bug
[`/conferences/`](https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app/conferences/) page has an external href pointing at `https://wonderful-margulis-8ec96b.vercel.app/conferences/` — the **old project URL without the team suffix**. Probably outdated render. Cosmetic but a "this product changed names mid-build" smell.

---

## Axis E — Performance (NEW)

### E1 — Heisman page = 14.8 MB
[reporting.py:render_heisman_page_html](src/cfb_rankings/reporting.py:16374) emits the full 15,599-row board inline. This is the "single largest performance liability" called out in `docs/octopus/discover.md` (2026-05-12). **Mobile users on 4G will not load this page within an acceptable budget.** Fix path: paginate to top-100 + AJAX "load more", OR move the full board to a `/heisman/full-board/` sub-page.

### E2 — Players directory = 31 MB
`/players/` lists all 17,836 player cards inline. Same fix path: paginate / virtualize / move to `/players/all/`.

### E3 — History page = 5.6 MB
`/history/` likely embeds dynasty heatmap + many small images. Less urgent than Heisman/players-dir but still over budget for mobile.

### E4 — Asset hashing already present
[output/site/assets/cfb-index.f3924a06eced.css](output/site/assets/) shows hashed CSS. Good for cache busting. No action needed.

### E5 — No `Content-Encoding: br` / no `Cache-Control` audit completed
Vercel handles these by default but worth verifying via curl `-I` against a sample of pages.

---

## Axis F — Accessibility (NEW, sampled)

### F1 — Skip-to-content link present on every sampled page ✓
[reporting.py — `_site_nav` or similar](src/cfb_rankings/reporting.py) emits `#main-content` anchor. Verified on homepage, alabama, fiu, mendoza, rankings, wire (all 1 instance each).

### F2 — `aria-live` regions present but sparse
Mendoza player page: 2. Rankings: 1. Others: 0. Filter result counts on Heisman / rankings boards should be `aria-live="polite"` for screen readers — they're not.

### F3 — Image alt audit
Sampled pages with images:
- Rankings: 531 imgs, 531 alts ✓ (team logos)
- Alabama: 1 img, 1 alt ✓
- FIU: 1 img, 1 alt ✓
- Mendoza: 0 imgs ✓ (uses SVG percentile bars inline)
- Wire/homepage: 0 imgs (no team logos in their layout)

Looks compliant; no full-site sweep done.

### F4 — Heading hierarchy on Heisman: 2 h2s, 4 h3s
- h2: "Fast Read", "Board Controls"
- h3: "Fernando Mendoza", "Jeremiyah Love", "Byrum Brown", "Caden Curry"

No h1→h3 skip, no h2→h4 skip. ✓ (but the "Board Controls" h2 is the hierarchy bug from Axis C1.)

### F5 — Keyboard navigation not tested
Would require browser-side testing. Sort buttons, filter dropdowns, Cmd-K overlay should all be reachable + operable via Tab+Enter+Esc. Not verified.

### F6 — Color contrast not audited
Lighthouse + axe would catch this. Not run.

---

## Axis G — SEO (NEW)

### G1 — Universal coverage of essential meta tags ✓
Per sampled pages, all of these are present:
- `<link rel="canonical">`
- `<meta property="og:image">`
- `<meta name="description">`

[common/head_chrome.py:122-200](src/cfb_rankings/common/head_chrome.py) emits these via `render_head_chrome()`.

### G2 — Missing: `hreflang` tags
Per [head_chrome.py](src/cfb_rankings/common/head_chrome.py), no `<link rel="alternate" hreflang>`. Not relevant unless we add internationalization.

### G3 — Sitemap.xml status: needs verification
Need to fetch `/sitemap.xml` and verify it's populated and references the right canonical URLs.

### G4 — `robots.txt` status: needs verification

### G5 — Twitter card tags ✓ per head_chrome.py

### G6 — Per-page description: needs verification that callers DON'T pass boilerplate
Sample 5 pages, compare description strings. Likely most are unique (the `_meta_tags()` callers in reporting.py do pass page-specific text); should still spot-check.

---

## Axis H — Onboarding / first-visit context (NEW)

### H1 — No "What is CFB Index?" explainer for brand-new visitors
The homepage hero leads with editorial copy ("Three Weeks Before Camp Whispers") and assumes the reader already knows the product. A brand-new visitor lands and has no idea what CFB Index DOES.

Compare to NYT Upshot, FiveThirtyEight, or The Athletic: each has a tagline near the brand mark. CFB Index has neither a tagline nor an explicit "About" entry near the brand.

**Fix:** Add a 1-sentence tagline under the brand mark in `_site_nav()`, plus a `/about/` page that explains the product (currently `/about-model/` is methodology, not product context).

### H2 — Brand mark is just "FI" with "THE CFB INDEX" wordmark
Verified from user screenshot. The "FI" mark + wordmark combination is fine but small + inconsistent across mobile / desktop. Worth a dedicated brand pass.

---

## Axis I — Editorial voice compliance (NEW)

### I1 — Voice validator catches new violations
[test_llm_runtime.py:79-102](tests/test_llm_runtime.py) tests block "analytics-cohort", "casual-cohort", "stat-cohort" → require "the stat crowd", "regular fans". The retry loop in [editions/cover_essay.py](src/cfb_rankings/editions/cover_essay.py) and [daily/cover_essay.py](src/cfb_rankings/daily/cover_essay.py) re-runs the LLM if these terms appear.

### I2 — Legacy seeds.py potential drift (needs sample audit)
[editions/seeds.py](src/cfb_rankings/editions/seeds.py) has hand-written cover essays from before the voice validator was wired. These haven't been re-checked. Sample 3 to verify no banned terms.

### I3 — Heavy "right now" / "this week" usage across editorial files (overlaps Axis B)
The voice constraint isn't just cohort jargon — it's also avoiding stale live-tracker tone. The B-axis grep found this throughout `editions/seeds.py`, `daily/synthesizer.py`, etc. Editorial owner decisions, but flagged.

---

## Axis J — Chart vocabulary (NEW)

Per [docs/design-system/31-chart-vocabulary.md](docs/design-system/31-chart-vocabulary.md): allowed = percentile bar, trajectory spark, bump chart, annotated line, small multiples, heatmap. Forbidden = pie, vertical bar, radar (except player fingerprint).

### J1 — No forbidden charts in renderers ✓
Grepped `src/cfb_rankings/` for: `type="pie"`, `chart-type-pie`, `class="pie`, `<polygon.*radar`, `radar-chart`, `barchart-vertical`. **Zero matches in renderers.** [`bets/rival_radar.py`](src/cfb_rankings/bets/rival_radar.py) is named "radar" but is a feature-extraction module, not a chart renderer.

### J2 — Percentile bars confirmed in use
[theme/percentile_bar.py](src/cfb_rankings/theme/percentile_bar.py) implements the allowed percentile-bar chart per spec.

---

## Axis K — Dark mode (NEW)

### K1 — `data-theme` attribute present on every sampled archetype ✓
Counts per page:
- Homepage: 5
- Alabama (profiled): 15
- FIU (unprofiled): 5
- Mendoza (player): 5
- Rankings: 5
- Wire: 5

PR #163 (legacy), PR #165 (team_pages), PR #166 (shared-nav surfaces). Toggle button rendered by `nav.render_global_nav_actions()` and `theme.render_theme_assets_head()`.

### K2 — FOUC prevention via inline `theme_init.js`
[theme/render.py:26-59](src/cfb_rankings/theme/render.py) inlines the theme detection script in `<head>` to prevent flash-of-unstyled-content. ✓

### K3 — Each renderer wires it independently
hub_page.py + team_pages/ + reporting.py each call `render_global_head_chrome()`. Custom renderers (wire, editions, daily, mailbag, portal-heat) need verification.

---

## Axis L — Cmd-K search (NEW)

### L1 — Search index present on production ✓
`/search-index.json` is 951,516 bytes. Loaded as JSON object. [cmdk/index_builder.py](src/cfb_rankings/cmdk/index_builder.py) confirmed building it.

### L2 — Index contents: teams (tier 1-4) + players (~14k cap)
Per [cmdk/index_builder.py:1-80](src/cfb_rankings/cmdk/index_builder.py).

### L3 — Cmd-K button rendered on every sampled archetype ✓
Per the page-sweep, "cmdk" appears in HTML on every sampled page.

### L4 — Actual search result quality: not tested
Would require browser-side testing. The index exists; whether typing "Mendoza" returns the right player isn't verified.

---

## Axis M — Receipt pattern citation density (NEW)

Per [docs/design-system/32-receipt-pattern.md](docs/design-system/32-receipt-pattern.md), editorial body content must have ≥1 citation marker per 200 words.

### M1 — Schema for citations exists
[migrations/20260601_01_editorial_citations.sql](migrations/20260601_01_editorial_citations.sql) — `editorial_citations` table.

### M2 — Density not measured on live editions
Sample needed: 5 most-recent editions, count words and citation markers in body content.

---

## Axis N — Mockup vs live drift (NEW)

[docs/mockups/index.html](docs/mockups/index.html) (signed off 2026-05-17, 33 polish rounds) shows mockups for 11 surfaces:

| Mockup | Live equivalent | Drift |
|--------|----------------|-------|
| 01 — Hub | `/hub/vibe-shifts/2025/18/` | needs visual comparison |
| 02 — Alabama | `/teams/alabama.html` | needs visual comparison |
| 03 — Vanderbilt | `/teams/vanderbilt.html` | needs visual comparison |
| 04 — Daily | `/daily/<slug>/` | needs visual comparison |
| 05 — Heisman | `/heisman/` | **known to diverge significantly** (Axis A) |
| 06 — Saturday Strip | (in-season only) | n/a in May |
| 07 — Monday Mood Map PNG | `/hub/monday-mood-map/` | needs verification of URL |
| 08 — Dark Share Cards | (share card endpoint) | needs verification |
| 09 — Tokens Specimen | (design-system internal) | not user-facing |
| 07b — Mood Map SVG | (share card endpoint) | needs verification |
| 07c — Mood Map Dark PNG | (share card endpoint) | needs verification |

**Action needed:** side-by-side mockup vs live screenshot comparison for surfaces 01-05 (the user-visible ones).

---

## Axis O — Edition essays: real vs stubbed (NEW)

### O1 — Latest edition (2026-w19) is real
[editions/seeds.py](src/cfb_rankings/editions/seeds.py) contains `_W17_COVER_ESSAY` and others, hand-written. ~100 lines of editorial prose, not Pattern C/D scaffolds.

### O2 — Archive editions vary
Per the agent's earlier grep, "archive editions lighter but complete per seeds.py:14-22." Needs explicit verification: visit each of `/editions/2026-w17/`, `/editions/2026-w16/`, `/editions/2026-w15/`, `/editions/2026-w14/` and count body word counts.

### O3 — Pattern D adversarial-critique editorial is NOT shipped
Per [docs/design-system/30-page-archetypes.md:226](docs/design-system/30-page-archetypes.md) Tentpole archetype lists "Pattern D adversarial-critique editorial" as allowed. Pattern D is not implemented yet.

---

## Priority matrix — what to fix and in what order

### Tier −1: BROKEN — fix before sharing further (≤ 1 day work)

**D1.** `/conferences/<slug>` all 404. Single biggest navigation gap. Investigate render-not-shipping cause, fix the workflow OR the renderer call site so per-conference pages emit + deploy.
**D2.** `/players/nfl-pipeline/` 404. Probably same root cause as D1.
**D4.** Vercel 404 returns empty body. Add `routes: [{ src: ".*", status: 404, dest: "/404.html" }]` to vercel.json OR rely on Vercel's default 404.html serving and figure out why it isn't firing.
**D5.** Footer missing on `/players/*` (17,836 pages) and `/rankings/`. Find the legacy page-wrap function and ensure it includes the footer.

### Tier 0: COPY BUGS — autonomous, no design judgment (≤ 4 hours)

**B1–B7 clusters.** All ~22 offseason-tense bugs cataloged above. Each is a single-line copy edit gated on `is_offseason(date.today())`.
**C4.** Three dev-commentary leak fixes ([reporting.py:14765](src/cfb_rankings/reporting.py), [:14844](src/cfb_rankings/reporting.py), [:16452](src/cfb_rankings/reporting.py)).

### Tier 1: VISUAL POLISH — needs judgment but contained (~1-2 days)

**C1.** De-emphasize 8 filter-widget `<h2>` blocks → `<h3>` or `<div class="filter-strip-label">`.
**C2.** Add hero finding zone to each Dashboard page (`/`, `/heisman/`, `/rankings/`, `/hub/vibe-shifts/`).
**C3.** Add methodology footer to each Dashboard page.
**D6.** Fix the absolute-URL `wonderful-margulis-8ec96b.vercel.app` reference on `/conferences/` (search-and-replace pass).
**H1.** Add a 1-sentence product tagline under the brand mark + a real `/about/` page.

### Tier 2: STRUCTURAL — archetype rewrites + perf (~weeks each)

**E1.** Heisman pagination — top-100 inline, full board lazy-loaded. ~3 days.
**E2.** Players directory pagination + virtualization. ~3 days.
**A — Dashboard archetype renderer.** Consolidates `/`, `/heisman/`, `/rankings/`, `/hub/vibe-shifts/`. ~1 week.
**A — Profile archetype consolidation.** Bring 17,836 player pages + 665 program pages + conference pages into the `team_pages/renderer.py` design language. ~2 weeks if done right.
**A — Database archetype.** Consolidates `/wire/`, `/editions/`, `/canon/`, `/players/` (dir), `/portal-heat/`, `/recruit-board/`, `/storylines/`. ~1 week.
**A — Article archetype.** Consolidates `/daily/`, `/mailbag/`, `/reactions/`, `/editions/<n>/<slug>`. ~3-5 days.
**A — Anniversary, Tentpole.** Lower priority — Anniversary is closest to spec; Tentpole pages haven't shipped.

### Tier 3: POLISH BACKLOG (when bandwidth)

**F2.** aria-live on filter result counts.
**F5–F6.** Keyboard nav + color contrast audit (use Lighthouse / axe).
**G3–G4.** Verify sitemap.xml + robots.txt populated correctly.
**I2.** Sample 3 legacy editions/seeds.py essays for voice violations.
**M2.** Receipt density sample on 5 recent editions.
**N.** Mockup-vs-live screenshot diff for surfaces 01-05.
**O2.** Walk each `/editions/<slug>/` and grade body content as real/light/empty.
**Untrack 1374 tracked `output/site/` files** (legacy from old deploy strategy).
**Resolve `/today-in-history/` vs `/anniversary/today/` URL drift.**

---

## Honest "I didn't audit this" list

Things I couldn't reach in this pass:

1. **Mobile-width visual rendering** — need a real phone or browser dev-tools simulation
2. **Real keyboard / screen-reader a11y testing** — need assistive tech
3. **Actual receipt-density count on shipping editions** — need to fetch + tokenize each body
4. **Mockup pixel-diff vs live** — need browser headless screenshots side-by-side
5. **Lighthouse + axe scores** — need a CI integration or local browser run
6. **Editorial corpus voice scan of all shipping content** — need to fetch every edition body and run validator
7. **The actual sub-44px touch target audit on live HTML** — need browser-side measurement

These are the gates between "audit doc" and "full quality bar." Items 1, 4, 5 are particularly hard without browser automation.

---

## Discovered as a side effect of this audit (new follow-ups)

These are NOT in the priority matrix above; they're observations to track separately:

- The Heisman page's "Caden Curry" top-defender card shows `DE | Rank #657` — that's a strangely low rank for "top defender on the board." Worth checking whether defender ranking is broken or just legitimately deep.
- `/heisman/` shows 15,599 players visible by default; the spec calls for a 100-row cutoff with "load more." Compliance gap.
- `/players/` directory at 31MB suggests no pagination at all. Same gap.
- Each conference workflow run probably produces local files at `output/site/conferences/<slug>_pulse.html` but they're not in the deployed artifact. Possible cause: the workflow runs but the artifact upload step (or the pre-publish-site overlay) drops them.

---

**Bottom line:** v1's audit was 22 copy bugs + 5 structural points. v2 finds **4 Tier-−1 blockers** (broken navigation), **22 Tier-0 copy bugs**, **4 Tier-1 polish items**, **6 Tier-2 structural rewrites**, **5 Tier-3 backlog items**. Plus a list of 7 things I genuinely can't audit without browser automation or assistive tech.
