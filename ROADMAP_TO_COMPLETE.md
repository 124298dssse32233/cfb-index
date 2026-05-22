# Roadmap to "complete" — exhaustive plan from session 6 forward

**Audit source of truth:** [docs/research/design-audit-2026-05-22-v2.md](docs/research/design-audit-2026-05-22-v2.md)
**Session 6 wrap:** [SESSION_6_FINAL_WRAP.md](SESSION_6_FINAL_WRAP.md)
**Production base URL:** https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app

This doc enumerates every remaining piece of work the audit + session
6 validation passes have flagged. Each phase has concrete tasks, a
rough day-budget, dependencies, and verification gates.

The phases are sequenced by a mix of risk (low-risk first), unblocking
(scaffolds before adopters), and visibility (visible wins woven through).

---

## How "complete" is defined

"Complete enough to show people" means all of these hold:

1. **No wrong-season editorial** — every published edition's body matches
   the publish date's calendar context.
2. **No dev-vocab leaks** — no "Sprint N", "Pattern C/D", "ingest", DB
   table names, internal slugs visible to users.
3. **Receipt pattern shipped** — every cover essay has ≥1 citation per
   ~200 words of body, with a Sources footer.
4. **Design-system spec compliance** — every page conforms to its
   archetype (Profile / Dashboard / Database / Article) per the locked
   spec in `docs/design-system/`.
5. **WCAG 2.1 Level AA** — keyboard nav works, color contrast ≥4.5:1,
   touch targets ≥24px (2.5.8) where standalone, ≥44px (2.5.5) where
   the spec recommends.
6. **Lighthouse CWV thresholds met** — LCP < 2.5s, CLS < 0.1, INP < 200ms
   on the top 20 surfaces.
7. **Mobile-first works** — every page renders correctly at 375px width
   without horizontal scroll.
8. **Navigation has no 404s** — every link in the nav, footer, breadcrumbs,
   and sidebar resolves.
9. **First-visit onboarding is clear** — a new visitor understands what
   CFB Index is within 5 seconds of landing.
10. **Editorial corpus is real** — every shipped essay has ≥800 words of
    on-topic content, not placeholders or sparse stubs.

---

## Phase 1 — Verify session 6 deploy (~1 hour, wakeup-driven)

**Status:** publish-site at SHA `1f1ea21ae6d` queued at ~17:21 UTC.
Wakeup scheduled for ~11:07 (T+45min) to verify.

**Verification checklist:**

- [ ] /editions/2026-w18/the-quiet-week/ shows `<sup class="citation">`
      HTML markers (not plain `[1]` text), with `data-cite-kind`,
      `data-cite-label`, `data-cite-url` data attributes
- [ ] Same page shows `<footer class="article-citations">` with 4
      Sources list entries
- [ ] /editions/2026-w19/three-weeks-before-camp-whispers/ shows 5
      citation markers + Sources footer
- [ ] /editions/2026-w17/after-the-bracket-three-conversations/ shows
      Sources footer (body has no inline markers since Pattern C
      output pre-dates the embedded `[N]` markers)
- [ ] /editions/2026-w18/the-quiet-week/ has a site-wide `<footer>`
      with Departments / Reference / Subscribe / Masthead columns
- [ ] /storylines/, /portal-heat/, /recruit-board/, /wire/,
      /daily/archive each show `.database-archetype__meta-footer`
- [ ] Homepage has `.methodology-footer` block above the global footer
- [ ] /conferences/fbs-sec.html shows `.profile-identity-strip` (the
      first concrete Profile identity-strip adopter in a legacy
      renderer)
- [ ] Heading-order: footer column headings are now `<h3>` (not `<h4>`)
- [ ] CSS: `.nav-link`, `.nav-action`, `.button-primary` etc. all
      render at ≥44px tall (computed style check via Chrome MCP)

**Failure modes & fixes:**

- If citations still render as plain text → the backfill-edition-
  citations CLI is still failing → check workflow logs again, may need
  another `seed_loaders` or import path fix.
- If publish-site itself fails → check the `Refresh backfilled edition
  pages` step logs.
- If touch-targets still sub-44px → the CSS block wasn't included in
  the global stylesheet → check `_compose_global_css` wiring.

**Gate:** Phase 1 passes when ≥9 of 10 checklist items verify on live.

---

## Phase 2 — Browser-MCP Lighthouse + axe audit (1-2 days)

**Why now:** with the receipt pattern + a11y CSS shipping, this is the
right moment to measure baseline CWV + a11y, then iterate.

**Task 2.1:** Sample-URL list (20 representative URLs covering each
archetype):
- 1 homepage
- 1 /heisman/, 1 /rankings/, 1 /hub/vibe-shifts/
- 2 player pages (Mendoza + a tail-of-board low-traffic one)
- 2 team pages (Alabama profiled + FIU unprofiled)
- 2 program pages (Notre Dame + Massachusetts)
- 2 conference pages (SEC + ACC)
- 2 edition pages (w18 + w19)
- 1 /wire/, 1 /storylines/, 1 /portal-heat/, 1 /recruit-board/
- 1 /canon/ index
- 1 /editions/ archive

**Task 2.2:** Run Chrome MCP axe-equivalent on each URL. Use
`javascript_tool` to inject the axe-core CDN script + execute
`axe.run()`, return violations as JSON. Capture in
`docs/research/axe-results-2026-05-22.json`.

**Task 2.3:** Run Chrome MCP Lighthouse-equivalent on each URL.
Capture CWV (LCP, CLS, INP) + perf score + a11y score per URL.

**Task 2.4:** Triage findings by frequency × severity. Each cluster
becomes a follow-up commit.

**Task 2.5:** Capture mobile-viewport screenshots (Chrome MCP
`resize_window` to 375x812) for each URL. Visual-spot-check no
horizontal scroll, no broken CTAs, no misaligned chrome.

**Day budget:** 1 day for Tasks 2.1-2.3 + capture; 1 day for Task 2.4
fixes.

**Gate:** Phase 2 passes when every sampled URL has axe critical
violations = 0 and Lighthouse CWV scores meet the "good" thresholds.

---

## Phase 3 — Richer Profile identity-strip primitive + migration (3-5 days)

**Why this is the biggest remaining piece:** 17,836 player pages +
665 program pages + ~662 unprofiled team pages currently render
with `<section class="hero team-hero premium-team-hero">` + stat
ribbon tiles + team mark + action buttons. The thin Profile primitive
shipped in session 5 doesn't support stat tiles or action buttons,
so it can't adopt these surfaces. This is the architectural debt
the audit called out as "the single most 'feels broken when clicking
around' issue."

**Task 3.1:** Design the v2 primitive API:

```python
def render_profile_identity_strip_v2(
    *,
    eyebrow: str,
    name: str,
    sub_meta: str = "",
    team_mark_html: str = "",        # SVG / unicode mark
    stat_tiles: list[dict] = (),     # [{label, value, sub}, ...]
    action_buttons: list[dict] = (), # [{label, href, variant}, ...]
    chips: list[str] = (),
    accent_color: str = "",          # CSS custom prop
) -> str: ...
```

CSS support: `_PROFILE_IDENTITY_V2_CSS_BLOCK` contributing rules for
`.profile-identity-v2`, `.profile-identity-v2__stat-tile`,
`.profile-identity-v2__action-row` etc. Color-coded by accent.

**Task 3.2:** Migrate `render_program_page_html` (665 surfaces).
Lower-risk than player pages because no stat-ribbon equivalent;
just hero + 4 stat tiles + 3 action buttons.

**Task 3.3:** Migrate `render_team_page_html` for unprofiled teams
(~662 surfaces). Same pattern as program page.

**Task 3.4:** Migrate `render_player_page_html` (17,836 surfaces).
The big one. Player pages have:
- Player name + team + position + jersey number eyebrow
- Stat tiles (current rank, season stats)
- Heisman rank chip
- "Open team page" / "Open Heisman" action buttons
- Career history table below

The v2 primitive needs to handle the player-page identity context.

**Task 3.5:** Build-site verification after each migration. The
player-page migration is the riskiest — 17,836 pages × ~50KB each
= ~900MB of output. Bad render = 17,836 broken pages.

**Task 3.6:** Live-verify 5 representative pages of each surface
type post-deploy. Chrome MCP DOM probe to confirm
`.profile-identity-v2` rendered.

**Day budget:** 1 day for v2 primitive + CSS; 1 day for program +
unprofiled team migrations; 2 days for player-page migration; 1 day
for verification + spot-fixes.

**Risk mitigation:** Each migration is a separate commit. Roll back
per surface if anything breaks. Hide v2 behind a feature flag in
config until first migration verifies cleanly.

**Gate:** Phase 3 passes when 5 representative pages of each surface
type render the v2 identity strip and Chrome MCP DOM probe confirms
no regression on existing chrome (breadcrumbs, action buttons,
team-mark, stat tiles all still functional).

---

## Phase 4 — Article archetype migration completion (2 days)

**Why:** /daily/ + /mailbag/ each have their own bespoke footer
templates. The Article archetype primitives (Track 7 scaffold) are
designed for these surfaces. Adopting them brings visual consistency.

**Task 4.1:** Migrate /daily/<edition>/ to use:
- `render_article_chrome` for the header (eyebrow + headline + dek +
  byline-row)
- `render_article_footer` for the closer (methodology pointer +
  share link)

**Task 4.2:** Migrate /mailbag/<edition>/ similarly.

**Task 4.3:** Live-verify /daily/2026-05-21/ + /mailbag/2026-05-23/
post-deploy.

**Day budget:** 1 day per surface (daily + mailbag).

**Gate:** Phase 4 passes when DOM probe confirms
`.article-archetype__chrome` + `.article-archetype__footer` present
on both daily and mailbag pages.

---

## Phase 5 — Editorial quality (3-5 days)

### 5a. Pattern D adversarial-critique editorial (~3 days)

**Why:** spec calls for Pattern D as Pattern C's upgrade. Pattern C
runs critics that suggest revisions; Pattern D's critics revise the
draft adversarially (poke holes, then the essayist defends or
revises). Produces sharper editorial.

**Task 5a.1:** Implement `loop_d_adversarial` in
`cfb_rankings/quality_loop.py` (the loop_c_critic_revise pattern
already exists; D is a v2 with adversarial-critic personas).

**Task 5a.2:** Flag `tier1.edition_cover` to `LoopPattern.D_ADVERSARIAL`
in `config.QUALITY_LOOP_FLAGS`.

**Task 5a.3:** A/B for 2 weeks: alternate weeks between C and D, log
metrics (word count, citation count, critic-pass-rate, voice-validator-
pass-rate).

**Day budget:** 1 day for loop_d_adversarial, 1 day for prompt tuning
+ critic personas, 1 day for A/B framework.

### 5b. Editorial corpus voice scan (~1 day)

**Task 5b.1:** Walk every `_archive_w*` payload in seeds.py, run
voice_validator on the body. Catch any "Sprint", "Pattern C", "ingest",
"placeholder" leaks. Fix in seed.

**Task 5b.2:** Live-fetch every `/editions/<slug>/` body and run voice
validator. Flag any with banned phrases. Force-reseed those.

**Day budget:** 1 day for corpus walk + fixes.

### 5c. Walk each /editions/<slug>/ and grade body real/light/empty (~1 day)

**Task 5c.1:** Programmatically fetch every published edition body,
count words, classify as:
- REAL (≥800 words, on-topic, voice-validator passes)
- LIGHT (300-800 words, on-topic)
- EMPTY (<300 words or placeholder text)

**Task 5c.2:** Force-reseed any EMPTY or LIGHT editions where the
seed has a richer body.

**Day budget:** 1 day.

**Gate:** Phase 5 passes when (a) Pattern D ships behind a flag, (b)
zero voice-validator violations across all shipped edition bodies, (c)
zero EMPTY-classified editions on production.

---

## Phase 6 — Infrastructure / SEO (1 day)

### 6a. Sitemap.xml + robots.txt verification (~2 hours)

**Task 6a.1:** Fetch `/sitemap.xml` and verify it lists every shipped
URL (homepage, /editions/*, /teams/*, /players/*, /heisman/, /rankings/,
/conferences/*, /programs/*, /canon/*, /storylines/, /wire/, /daily/,
/mailbag/, /reactions/, /portal-heat/, /recruit-board/, /history/,
/nfl-pipeline/, /hub/vibe-shifts/, /editions/<slug>/<feature>/).

**Task 6a.2:** Fetch `/robots.txt` and verify it allows the
production crawl + denies any preview/staging URLs.

**Task 6a.3:** If either is missing or stale, fix the build pipeline.

### 6b. Untrack legacy output/site/ files (~30 min)

**Task 6b.1:** `git ls-files output/site/ | head` to confirm tracked
count. Per the audit, 1374 legacy files.

**Task 6b.2:** `git rm --cached output/site/<each>` + commit.

### 6c. /today-in-history/ vs /anniversary/today/ URL drift (~1 hour)

**Task 6c.1:** Determine canonical URL by checking which one the nav
points to.

**Task 6c.2:** Add a redirect from the non-canonical URL to the
canonical via vercel.json `redirects` array.

### 6d. Deploy chain healthcheck (~30 min)

**Task 6d.1:** Verify the 19 workflows that gate on the rolling
cfb-rankings-db artifact still pass the artifact-healthy check.

**Task 6d.2:** Verify the 7 workflows with `permissions: { issues:
write }` for notify_failure.yml still have the block.

**Task 6d.3:** Verify live_smoke_test.yml is hitting 28 URLs and
the failure-issue gate works.

**Day budget:** 1 day total.

**Gate:** Phase 6 passes when sitemap is complete, robots.txt allows
crawl, legacy tracked files are untracked, /today-in-history/
canonical is set, and all healthcheck workflows pass.

---

## Phase 7 — Onboarding / first-visit context (1-2 days)

### 7a. /about/ page (~4 hours)

**Why:** the audit's H1 says no real "What is CFB Index?" explainer
exists. The /about/ page exists but is sparse.

**Task 7a.1:** Read existing /about/ template, identify gaps.

**Task 7a.2:** Add a hero finding: "CFB Index — every team, every
ranking, every fan-voice signal" or similar.

**Task 7a.3:** Add a 3-section explainer:
- "What we measure" (power + resume ratings, fan-mood, NFL pipeline)
- "How the editorial works" (Mondays = Edition essay; daily = wire;
  weekly = Heisman board, etc.)
- "Why the rankings differ from AP" (model-driven, NLP-fed, neutral-
  field)

**Task 7a.4:** Add a "Browse the site" footer with 8-card grid linking
to top archetypes.

### 7b. Brand mark tagline (~30 min)

**Task 7b.1:** Add a 1-sentence product tagline under the "THE CFB
INDEX" brand mark across the top nav. E.g. "Where every team stands
· what every fanbase thinks" (already in footer; surface it in nav too).

### 7c. Onboarding tooltip (~3 hours, optional)

**Task 7c.1:** First-visit detection (localStorage flag).

**Task 7c.2:** Tooltip overlay pointing at the 3 highest-value surfaces
(Rankings, Editions, Heisman) with one-sentence each.

**Task 7c.3:** Dismiss state persists.

**Day budget:** 1 day for /about/ + tagline; optional 0.5 day for
onboarding tooltip.

**Gate:** Phase 7 passes when (a) /about/ has ≥500 words of real
explainer content, (b) brand tagline visible on every page, (c) a
new visitor can identify "what this product is" within 5 seconds.

---

## Phase 8 — Mobile UX validation (1 day)

**Task 8.1:** Chrome MCP resize to 375x812 (iPhone-ish). Sample 12
pages: homepage, /heisman/, /rankings/, 1 player page, 1 team page,
1 conference page, 1 edition page, 1 edition article, /daily/,
/wire/, /storylines/, /editions/ archive.

**Task 8.2:** Capture full-page screenshots of each. Visual-check:
- No horizontal scroll
- All CTAs visible
- Top nav collapses to hamburger
- Mobile filter strip (Dashboard archetype) renders at the bottom
- Touch targets ≥44px (overlapping with Phase 2's touch-target audit)

**Task 8.3:** Fix any mobile-specific layout breaks.

**Day budget:** 1 day.

**Gate:** Phase 8 passes when all 12 sampled URLs render correctly
at 375px width with no horizontal scroll.

---

## Phase 9 — Accessibility hardening (1-2 days)

### 9a. aria-live on dynamic filter result counts (~3 hours)

**Task 9a.1:** Find every filter widget that updates a result count
(/heisman/, /rankings/, /teams/, /players/). Add `aria-live="polite"`
to the count element.

### 9b. Keyboard nav audit (~4 hours)

**Task 9b.1:** Chrome MCP simulate tab-through every page in the
sample set. Verify:
- Tab order is logical (top to bottom, left to right)
- Focus indicators visible on every interactive element
- Skip-to-content link works
- No keyboard traps

### 9c. Color contrast audit (~4 hours)

**Task 9c.1:** Run axe-core on the sample set with the contrast
checker enabled. Capture any contrast failures.

**Task 9c.2:** Bump any low-contrast pairs to meet 4.5:1 (Level AA).

### 9d. Screen-reader announcement audit (~4 hours, manual)

**Task 9d.1:** Open NVDA/VoiceOver and navigate the homepage +
/heisman/ + /editions/<slug>/. Verify announcements are clear.

**Day budget:** 1-2 days.

**Gate:** Phase 9 passes when zero axe-core critical violations, zero
keyboard nav blockers, all contrast pairs ≥4.5:1.

---

## Phase 10 — Performance hardening (1-2 days)

### 10a. Core Web Vitals measurement (~2 hours)

**Task 10a.1:** Chrome MCP run a Lighthouse-equivalent measurement
on the sample URL list. Capture LCP, CLS, INP per page.

### 10b. LCP fixes (~4 hours)

**Task 10b.1:** For any page with LCP > 2.5s, identify the LCP
element and either preload it or move it earlier in the HTML.

**Task 10b.2:** Verify `<link rel="preload">` on critical assets
(fonts, hero images).

### 10c. CLS fixes (~3 hours)

**Task 10c.1:** Find any page with CLS > 0.1. Identify the
shifting element (probably late-loading ad/image/SVG without
dimensions).

**Task 10c.2:** Add explicit width/height to all images, set aspect-
ratio on inline SVGs.

### 10d. INP / responsiveness (~3 hours)

**Task 10d.1:** For any page with INP > 200ms, identify the long-
running JS. Move work off the main thread or debounce.

### 10e. Compression + caching headers (~2 hours)

**Task 10e.1:** Verify Brotli compression is on (it is per session 5
check — `content-encoding: br` headers seen).

**Task 10e.2:** Verify Cache-Control headers per asset type:
- HTML: must-revalidate, max-age=0
- CSS/JS with hash: immutable, max-age=31536000
- Images: max-age=86400

**Day budget:** 1-2 days.

**Gate:** Phase 10 passes when all sampled URLs hit Lighthouse "good"
on all CWV metrics.

---

## Phase 11 — Mockup pixel-diff vs live (1 day, optional)

**Task 11.1:** For each of the 11 mockup surfaces in
`docs/mockups/index.html`, capture a screenshot at the design-locked
viewport size (1440x900).

**Task 11.2:** Capture matching live screenshots via Chrome MCP at
1440x900.

**Task 11.3:** Visual-diff each pair. Catalog drift.

**Task 11.4:** Fix drift where it's a regression; document it where
it's an intentional post-mockup polish.

**Day budget:** 1 day.

**Gate:** Phase 11 passes when each surface either matches the mockup
or has a documented intentional-divergence note.

---

## Phase 12 — Final consolidation + smoke (1 day)

**Task 12.1:** Run a final Chrome MCP audit pass on 50 URLs (the
sample list × ~2.5 each archetype).

**Task 12.2:** Update SESSION_6_FINAL_WRAP.md → rename to
SESSION_FINAL_WRAP.md, consolidate all phase outcomes.

**Task 12.3:** Update docs/research/design-audit-2026-05-22-v2.md to
reflect closed state. Each Tier-1/2/3 item gets a check mark.

**Task 12.4:** Trigger one final publish-site at the latest SHA.

**Task 12.5:** Live-smoke-test 28 URLs return 200; spot-check 10
representative pages for visual + content quality.

**Day budget:** 1 day.

**Gate:** Phase 12 passes when all 50 sample URLs return 200, the
audit doc shows zero open items in Tier 1, and the final wrap
documents every phase outcome.

---

## Total budget

| Phase | Budget |
|---|---|
| 1: Verify session 6 deploy | 1 hour |
| 2: Browser Lighthouse + axe | 1-2 days |
| 3: Richer Profile identity-strip + migration | 3-5 days |
| 4: Article archetype completion | 2 days |
| 5: Editorial quality (Pattern D + corpus scan) | 3-5 days |
| 6: Infrastructure / SEO | 1 day |
| 7: Onboarding / /about/ | 1-2 days |
| 8: Mobile UX validation | 1 day |
| 9: Accessibility hardening | 1-2 days |
| 10: Performance hardening | 1-2 days |
| 11: Mockup pixel-diff (optional) | 1 day |
| 12: Final consolidation | 1 day |

**Total:** ~16-25 days of focused work.

**Parallelizable:**
- Phase 2 (audit) can run in parallel with Phase 3 (identity-strip)
- Phase 6 (infra) can run anytime
- Phase 8 (mobile) can run anytime after Phase 1
- Phase 11 (mockup diff) can run anytime

**Strictly sequenced:**
- Phase 1 → all others (deploy must verify before more changes deploy)
- Phase 3 → Phase 12 (architecture must land before final smoke)
- Phase 4 → Phase 12
- Phase 5 → Phase 12
- Phase 9 → Phase 12 (a11y fixes inform later browser audits)

---

## Recommended execution order

**Right now (next 45 min):** Wakeup-driven Phase 1 verification.

**This session, after Phase 1 verifies:** Start Phase 2 (browser
audit) because it's read-only and surfaces concrete issues for
Phases 9/10 to fix.

**Next session:** Phase 3 (richer identity-strip) — the architectural
keystone. 3-5 days standalone.

**Sessions after:** Phase 4 (article archetype completion), then
Phases 5 + 6 + 7 in parallel, then Phases 8 + 9 + 10 in parallel.

**Final session:** Phase 12 consolidation + smoke.

---

## Risk register

| Risk | Phase | Mitigation |
|---|---|---|
| Identity-strip v2 breaks 17,836 player pages | 3 | Feature-flag; roll out per surface; CI smoke test on representative sample |
| Pattern D regresses editorial quality | 5a | A/B for 2 weeks; revert to C if voice-validator pass-rate drops |
| Lighthouse fixes ship without verification | 10 | Each fix gets its own commit; Phase 12 re-runs Lighthouse to confirm |
| Mobile fixes break desktop | 8 | Visual-regression check at 1440x900 after every mobile commit |
| Vercel deploy chain regresses | all | Smoke test gate; if <95% URL pass rate, hold deploy + investigate |

---

## What this doc deliberately does NOT include

- **New editorial surfaces** (Pattern E continuity loops, anniversary
  surfaces, tentpole surfaces) — outside session-6 budget; future
  work.
- **Recruiting class explorers** — distinct product surface, not in
  scope.
- **Predictive-claim receipts** (Sprint 13) — `cfb_rankings.receipts`
  package is a separate system from the editorial-citation receipt
  pattern this roadmap completes.
- **Real-CDN performance work** (image optimization, font subsetting)
  — Tier-3 polish that's marginal vs the gains in Phase 10.
- **Multi-language support** — explicitly out of scope per the audit.

---

## Bottom line

**To reach "perfect to show people," ~16-25 days of focused work
remain.** The work breaks cleanly into 12 phases with clear
dependencies and verification gates. ~50% of the budget is
architectural (Phase 3 identity-strip migration); the other 50%
is split across editorial quality, a11y hardening, perf hardening,
and onboarding.

After Phase 12, the audit's Tier 1 list is empty, Tier 2 is
substantially closed, and Tier 3 is reduced to fewer than 3
backlog items.
