# CFB Index — Comprehensive Design / Copy Audit

**Generated 2026-05-22.** Triggered by user's screenshot of the Heisman page reading like it's still a live 2025 race in May 2026.

This audit covers two axes:
- **Axis A — Archetype gap:** how each live page maps to the design-system archetype spec, and where the gap is.
- **Axis B — Offseason copy bugs:** specific present-tense / "this week" / "live X" copy that doesn't switch via `is_offseason()` when it should.

Plus a third short section on **other design-spec violations** I spotted along the way.

---

## Axis A — Archetype renderer audit

Per `docs/design-system/30-page-archetypes.md:333-344` the renderer status is:

| Archetype | Module path (spec) | Status (per spec) |
|---|---|---|
| Article | `src/cfb_rankings/articles/renderer.py` | **TO BUILD** |
| Dashboard | `src/cfb_rankings/dashboards/renderer.py` | **TO BUILD** |
| Profile | `src/cfb_rankings/team_pages/renderer.py` + `players/renderer.py` | **PARTIALLY EXISTS** (teams) |
| Database | `src/cfb_rankings/database/renderer.py` | **TO BUILD** |
| Tentpole | `src/cfb_rankings/tentpole/renderer.py` | **TO BUILD** |
| Anniversary | `src/cfb_rankings/anniversary/renderer.py` | **TO BUILD** |

**Bottom line: 5 of 6 archetype renderers are unbuilt.** Every page that isn't a profiled team page (17 of ~700) is rendered by the legacy `reporting.py` monolith or per-feature ad-hoc renderers, none of which conform to the archetype spec.

### What each live URL pattern actually uses today

| URL | Spec archetype | Actual renderer | Gap |
|-----|----------------|----------------|------|
| `/` | Dashboard | `reporting.py` + `editions/homepage_renderer.py` | Legacy monolith; doesn't follow Dashboard structure |
| `/heisman/` | Dashboard | `reporting.py:16374` `render_heisman_page_html` | Legacy. No hero finding, no primary viz, "BOARD CONTROLS" h2 is hierarchically misplaced. Same offseason copy bug just shipped a fix for. |
| `/rankings/` | Dashboard | `reporting.py` | Legacy. Same hierarchy issues as Heisman; Risers/Faders section uses "this week" in offseason |
| `/hub/vibe-shifts/` | Dashboard | `hub_page.py` | Custom renderer, predates the spec. Heavy "Updated this week" use throughout. |
| `/teams/<profiled>.html` (17) | Profile | `team_pages/renderer.py` | **CONFORMS** to Profile archetype — the reference implementation |
| `/teams/<unprofiled>.html` (~662) | Profile | `reporting.py` | Legacy. Visibly different look from profiled — the "unprofiled team page" is the most obvious archetype-drift on the site |
| `/programs/<slug>.html` (665) | Profile | `reporting.py` | Legacy. Should consolidate with team-page renderer. |
| `/players/<slug>.html` (17,836) | Profile | `reporting.py` | Legacy. Players renderer is on the spec but not built. |
| `/conferences/<slug>.html` | Profile | `reporting.py` | Legacy. Conference page is a third "Profile" surface, also unbuilt. |
| `/wire/` | Database | `wire/renderer.py` | Custom renderer, predates Database archetype. |
| `/editions/` | Database | `editions/archive_renderer.py` | Custom renderer. |
| `/editions/<n>/<slug>` | Article | `editions/page_renderer.py` (etc.) | Custom; closer to spec but no consolidated Article module |
| `/daily/` | Article | `daily/renderer.py` | Custom. |
| `/mailbag/` | Article | `mailbag/renderer.py` | Custom. |
| `/canon/<list>` | Database | `canon/renderer.py` | Custom. |
| `/portal-heat/` | Database | `portal_heat/renderer.py` | Custom. Just refreshed last night. |
| `/recruit-board/<class>/` | Database | `recruit_board/renderer.py` | Custom. |
| `/storylines/` | Database | `storylines/renderer.py` | Custom. |
| `/compare/` | Dashboard | `tools/wcfb_enhancements/build_compare.py` | Tool-script renderer; not in src/. |
| `/methodology/` | Article | `provenance/methodology_index_page.py` | Custom. |
| `/anniversary/today/` | Anniversary | `today_in_history/renderer.py` | Custom; closest to archetype spec since it was built recently. |

**Pattern:** Every renderer that predates the design-system lock (2026-05-17) is a custom one-off. Only `team_pages/renderer.py` is on the consolidation track. The "looks designed" feel happens for the 17 profiled team pages; everywhere else feels like a different site.

---

## Axis B — Offseason copy bugs (present-tense that doesn't switch)

Pattern: code uses "right now", "this week", "live X" without checking `is_offseason()` from `cfb_calendar.py`. Result: in May (current month), pages read as if a live game cycle is happening. **The Heisman page bug already-fixed in this session is one instance of this class.**

### High-visibility instances (rendered into live pages today)

| File:line | Page that renders it | Current copy | Fix shape |
|-----------|----------------------|--------------|-----------|
| `reporting.py:13526` | `/rankings/` | "Biggest Faders ... this week" | "this week" → "since last refresh" or "this offseason"; gate on `is_offseason()` |
| `reporting.py:13517-13518` | `/rankings/` | "No meaningful risers this week" | same |
| `reporting.py:10350`, `:17731` | `/players/<slug>.html` (17,836 pages) | "What makes this player interesting right now" | switch h2 to "What makes this player interesting" or branch on offseason |
| `reporting.py:12280` | `/conferences/<slug>.html` | "[Conference] reads like a balanced league right now" | rewrite for offseason: "...balanced through the most recent season" |
| `reporting.py:13259` | `/compare/` (and inline compare cards) | "looks stronger right now on the predictive board" | "looks stronger heading into 2026" |
| `reporting.py:14141, :14152` | `/` (homepage scenarios) | "The cleanest high-end matchup on the board right now" | offseason: "early-2026 scenario" |
| `reporting.py:14765` | `/methodology/` | "What is loaded locally right now" | tense neutral: "currently loaded" |
| `reporting.py:14844` | `/rankings/` (selection-room intro) | "how strong teams look right now, and what they have actually earned" | offseason: "how strong teams looked through the most recent season" |
| `reporting.py:18985, :19001` | `/about-model/` | "how strong a team is right now" / "best team right now" | model-explainer copy; could stay as "how strong a team is at any given point" |
| `reporting.py:500, :504, :508` | team / program / player pages (footers via `_power_resume_gap_text`) | "Power and resume are essentially aligned right now" | gate on offseason |
| `reporting.py:16452` (still there) | `/heisman/` | "CFBD currently exposes game betting lines, not award futures" | dev commentary, hide in methodology |
| `hub_page.py:214` | `/hub/vibe-shifts/` masthead | default updated_label = "Updated this week" | should be "Updated this offseason" or absolute date |
| `hub_page.py:812, :1022, :1175` | `/hub/vibe-shifts/` modules | "updated this week" labels | same |
| `hub_page.py:1157` | `/hub/vibe-shifts/` | "this week, one of eight modifiers" | "currently, one of eight modifiers" |
| `hub_page.py:1242` | `/hub/vibe-shifts/` empty state | "No featured phrase this week" | "No featured phrase this offseason" |
| `hub_page.py:1271` | `/hub/vibe-shifts/` lexicon detail | "spiked in [team] fan conversations this week" | "spiked recently in [team] fan conversations" |
| `hub_page.py:1347` | `/hub/vibe-shifts/` footer | "Save this week's cards" CTA + "archive of all 47 issues" | "this week's" wrong outside in-season |
| `editions/seeds.py:101, :138, :897, :938, :950` | editions text seeds | various "right now" / "this week" | content owner decisions; lower priority |
| `players_landing.py:196` | `/players/` directory | "right now. The Room tracks who fans are..." | gate on offseason |

### Medium-visibility (dynamic narrative; only stale if data flows match it)

| File:line | Surface | Note |
|-----------|---------|------|
| `fan_intelligence.py:634` | mood card subtext | "{N} rival mentions this week." — fine when N>0 and live |
| `fan_intelligence.py:827, :936` | mood card fallback narratives | "We have not seen rival fanbases post about this team this week" — appropriate as fallback |
| `mailbag/synthesizer.py:83, :198` | mailbag answer LLM prompt | "No live signal in the corpus for this question's tags this week" — LLM input not user copy |
| `daily/synthesizer.py:104, :221, :488, :496` | daily LLM prompts | not user-visible |
| `daily/cover_essay.py:111, :201, :224` | daily essay LLM prompts | not user-visible |
| `editions/cover_essay.py:167, :171, :189, :205` | editions LLM prompts | not user-visible |
| `the_room_board.py:351` | The Room board scope label | dynamic; offseason scope is "season rollup" already per the code |
| `hero_findings/generator.py:57, :130, :418, :423` | hero finding narrative | template; can use `is_offseason` gate |
| `mobile/saturday_strip.py:71, :132` | Saturday strip docstrings + empty state | only renders in-season; safe |
| `nfl_pipeline.py:233` | `/players/nfl-pipeline/` page lede | "running on twelve-year reputation" — context-appropriate; not stale |
| `provenance/methodology_page.py:308` | methodology footer | "Top divergence this week" h3 — same offseason mismatch |
| `reporting.py:9993` | player career row | "stat seasons currently loaded" — careful tense, OK |
| `reporting.py:12509` | site pulse banner | "currently surfaced" — OK |
| `reporting.py:15129` | program page predictive note | "most powerful closing teams currently modeled" — neutral, OK |
| `reporting.py:18792, :18859, :18868` | program page metric tooltips | "currently attached to this program" — OK as "as of right now" data state |
| `reporting.py:22297` | compare tool chart placeholder | "The chart will load the currently selected team here" — UI hint, OK |
| `reporting.py:22975` | percentile language | "currently grades around the [percentile]" — OK |
| `reporting.py:23146` | chart-view JS | "currently match this chart view" — OK |
| `reporting.py:13865` | rankings empty state | "Awaiting model run" — fine |

**Count of high-visibility offseason copy bugs: ~22.** Cluster by page:
- `/rankings/` — 3 instances
- `/players/*` (17,836 pages) — 2 instances
- `/heisman/` — 1 still-there (line 16452) plus the already-fixed copy
- `/hub/vibe-shifts/` — 7 instances
- `/conferences/*` — 1 instance
- `/compare/` — 1 instance
- `/methodology/` — 2 instances (reporting.py + provenance)
- `/about-model/` — 2 instances
- `/` homepage — 2 instances (already mostly handled via `is_offseason` flag in editorial_context, but scenario text falls through)
- team/program/player footers — 1 instance (`_power_resume_gap_text`)

---

## Axis C — Other design-spec violations spotted

### C1. Dashboard archetype missing structural elements

The spec at `30-page-archetypes.md:67-98` calls for, top-to-bottom: top zone → Saturday/countdown strip → **hero finding (1 big number + sentence + caption)** → primary visualization → movers grid → drill-down modules → methodology footer → bottom thumb-zone filter strip.

`/heisman/`, `/rankings/`, `/hub/vibe-shifts/`, `/` — **none** of these have a hero finding zone. They jump from generic nav into mixed sections.

### C2. Profile archetype split-personality

`team_pages/renderer.py` (17 profiled teams) conforms to spec. `reporting.py` (other ~662 teams + all 17k player pages + all 665 program pages + conference pages) does not. The visible result: clicking from a profiled team to an unprofiled one feels like a different site. This is the single most "feels broken" issue for any visitor who clicks around.

### C3. "BOARD CONTROLS" h2 hierarchy bug

`reporting.py:16507` renders `<h2>Board Controls</h2>` for the Heisman filter widget. Same h2 size as the page's "Fast Read" editorial section. CSS treats both as major sections. Filter widgets should not be h2-level — should be visually subordinate (the spec puts filter strips at the bottom thumb-zone, mobile-only). Same pattern in `reporting.py:14937, :15327, :15826, :15975, :16299, :16514, :16658, :22012`. **8 sites where filter widgets are over-emphasized.**

### C4. Dev commentary in user-facing copy

Examples:
- `reporting.py:16452` (Heisman): "CFBD currently exposes game betting lines, not award futures." Reader doesn't care what CFBD exposes.
- `reporting.py:14765` (methodology section-note): "What is loaded locally right now, what powers the numbers, and why the site can keep growing." reads as developer talking to themselves.
- `reporting.py:14844` (rankings selection room intro): "The list is meant to read like a clean selection-room board" — meta-commentary about what the list is *meant* to read like.

### C5. Forbidden patterns from the spec

Per `30-page-archetypes.md`:
- **Article archetype forbids**: multi-column layouts, right-rail widgets, mid-article ads, comment threads. Not violated currently.
- **Dashboard archetype forbids**: long-form prose (>200 words consecutive), more than 3-col layouts, decorative imagery, auto-rotating carousels. The Heisman page's hero lede (`reporting.py:16484`) is borderline — it's currently ~50 words, but the explanation goes on. Acceptable.
- **Database archetype forbids**: pagination above-the-fold, comment counts, visual noise per row (one badge max). `/wire/`, `/editions/`, `/players/` directory — need a spot-check pass.
- **Profile archetype forbids**: identical layout across entities, Dashboard-density grids in hero, long-form essays in middle. Profiled team pages comply. Legacy `reporting.py` team pages technically violate "identical layout" because every unprofiled team is the same boilerplate — but they get a pass because there's a separate archetype track for them.
- **Anniversary archetype forbids**: live data signals, recommendation engines. `/anniversary/today/` looks compliant.
- **Tentpole archetype forbids**: tentpole treatment on non-tentpole editions, auto-generated cover imagery, standard Article hero. Not yet built so n/a.

### C6. Chart vocabulary check

Per `docs/design-system/31-chart-vocabulary.md`, allowed charts are: percentile bar, trajectory spark, bump chart, annotated line, small multiples, heatmap. **Forbidden:** no pie, no vertical bar (except small multiples), no radar (except player fingerprint).

I didn't do a full chart inventory; suggest dedicated pass. Worth grepping `reporting.py` for any `<svg>` blocks that draw pie/radar.

### C7. Receipt pattern density

Per `docs/design-system/32-receipt-pattern.md`, editorial body content must have ≥1 citation marker per 200 words. Daily, mailbag, editions content was the receipt-pattern target. Without re-checking every published piece, I'd suggest sampling 5 recent editions to verify the wire format is present and the density is hitting the floor.

### C8. Tabular numerals coverage

Already verified clean in session 1 — see `docs/design-system/00-tokens.md`. The selector at the bottom of tokens.md covers `.wcfb-stats-* td`, `.biotabs__panel-value`, `.rank-delta`, `.table-wrap td` (per the P0 fix). Should still spot-check that no new tables added since then are missing the class.

---

## Priority matrix — what to fix first for "looks perfect" goal

### Tier 0 — Ship within the next 24 hours (≤ 4 hours work)

1. **Fix `/rankings/` "this week" copy** (reporting.py:13517-13526, 14844) — same pattern as the Heisman fix just shipped. ~30 min.
2. **Fix `/players/*` "What makes this player interesting right now" h2** (reporting.py:10350, 17731) — affects 17,836 pages. ~15 min copy change.
3. **Fix `/hub/vibe-shifts/` "this week" labels** (hub_page.py, 7 instances) — affects the live hub. ~45 min.
4. **Fix `/conferences/*` balanced-league line** (reporting.py:12280) — affects all conference pages. ~15 min.
5. **Fix `/compare/` "looks stronger right now"** (reporting.py:13259) — ~10 min.
6. **Fix `/heisman/` lingering dev commentary** (reporting.py:16452 still there) — ~5 min.

Total: ~2-3 hours work + 1 publish-site cycle (~50 min) to ship.

### Tier 1 — Visual polish, before any wider sharing (~1-2 days)

7. **"BOARD CONTROLS" h2 hierarchy** — convert all 8 filter-widget `<h2>` to `<h3>` or visually de-emphasize. ~1 hour.
8. **Hero finding zone for Dashboard pages** — add a single big-number + sentence + caption block at the top of `/`, `/heisman/`, `/rankings/`, `/hub/vibe-shifts/`. ~half day per page. **This is the highest visual ROI improvement before a Dashboard rewrite.**
9. **Methodology footer for Dashboard pages** — small "How we measure this →" link + sample-size summary + "Updated" timestamp at the bottom of `/`, `/heisman/`, `/rankings/`, `/hub/vibe-shifts/`. ~2 hours.
10. **"Awaiting Signal" copy review** — ~6 places in `reporting.py`. Check each is fan-language not dev-language.

### Tier 2 — Structural archetype work (weeks)

11. **Dashboard archetype renderer** (consolidates `/`, `/heisman/`, `/rankings/`, `/hub/vibe-shifts/`). ~1 week.
12. **Database archetype renderer** (consolidates `/wire/`, `/editions/`, `/canon/<list>`, `/players/` directory). ~1 week.
13. **Article archetype renderer** (consolidates `/daily/`, `/mailbag/`, `/reactions/<slug>`, `/editions/<n>/<slug>`). ~3-5 days.
14. **Profile archetype consolidation** — extract `team_pages/renderer.py` patterns into `players/renderer.py` and `conferences/renderer.py` so all Profile surfaces look the same. **Highest visible-impact long-form work.** ~2 weeks if done right.
15. **Anniversary, Tentpole renderers** — lower priority since Tentpole pages haven't shipped yet and Anniversary is closest to spec already.

### Tier 3 — Polish backlog (when bandwidth)

16. Chart vocabulary inventory (spot pie / radar / vertical bar violations).
17. Receipt pattern density sample across 5 recent editions.
18. Tabular-numerals re-sweep on any new tables added since session 1.

---

## What I'd ship tonight if user says go

Tier 0 (items 1-6) is the highest-value autonomous run: ~22 individual copy/hierarchy fixes across 6 page surfaces, ~3 hours of work, one publish-site cycle to deploy. Won't make the site "Dashboard archetype" but will eliminate the immediate "this reads like a live-tracker on a completed season" embarrassment across the whole site. Tier 1 is next-day visual polish (hero finding zones, methodology footers, filter-widget de-emphasis) that gets the site to "I'd share this without an asterisk."

Real Dashboard / Profile / Database archetype work is Tier 2 — sized properly for a focused multi-day session per archetype, not autonomous time.
