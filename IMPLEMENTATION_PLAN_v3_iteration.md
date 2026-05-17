# IMPLEMENTATION_PLAN — v3 Iteration
# Refinements + acceptance criteria + execution coordination for v2 addendum
# Read alongside IMPLEMENTATION_PLAN_v2_addendum.md

**Status:** Authoritative refinements + tactical execution guidance for the v2 addendum.
**Owner:** Window B (per COORDINATION.md)
**Last updated:** 2026-05-16

---

## Part A — Tomorrow Morning's Actionable Checklist

### Hour 0–1: Audit baseline
Verify current state of the v5-0 procurement items (status unknown):
```bash
ls output/_assets/rivalry_trophies/*.svg 2>/dev/null | wc -l   # should be 25
ls prompts/*.md 2>/dev/null | wc -l                             # should be 11
grep -l "signature_metrics_ladder\|archetype_tags\|lexicon_anchors" profiles/*.md | wc -l  # should be 17
grep -l "DIGEST_ISSUE_NUMBER" .github/workflows/*.yml           # should find at least 1
```
If any return zero, those v5-0 items haven't shipped. Add to Window A backlog.

### Hour 1–3: Read v2 addendum + this iteration end-to-end
Annotate where you disagree. Decisions you make now save weeks downstream.

### Hour 3–5: Lock the 5 foundational decisions (Sprint v5-5.5 prep)
- Typography: Bebas Neue (display) + Source Serif Pro (body — already in tokens) + Inter (UI/data — already in tokens)
- Add display font + tabular-nums rule to `docs/design-system/00-tokens.md`
- Create stubs for `30-page-archetypes.md`, `31-chart-vocabulary.md`, `32-receipt-pattern.md`, `33-confidence-signaling.md`

### Hour 5–8: Editorial curation of one team's rituals (proof of concept)
Pick Alabama. Add new frontmatter fields to `profiles/alabama.md`. If you can finish in 3 hours for Alabama, you know the full 17 teams will take ~50 hours. If it takes 6 hours, project needs editorial assistance.

### Hour 8–10: Sketch the Saturday Strip
On paper or in Figma. Don't code yet. Sketch in-season state (live games scrolling), off-season state (countdown + portal news), mobile portrait at 390px, sticky behavior.

### Hour 10–24: Sleep + first-pass sanity critique

### Day 2: Production-ready mockup of ONE page (the new Hub)
Use the v2 design tokens. Use page archetype patterns. Produce a high-fidelity HTML mockup of just the Hub with hero finding + movers board + methodology footer. Mobile + desktop. This becomes the visual reference for every subsequent sprint.

---

## Part B — Foundational Decisions, RECOMMENDED LOCKS

### Decision 1: Typography stack
**Bebas Neue (display) + Source Serif Pro (body, already in tokens) + Inter (UI/data, already in tokens).**

Add to `docs/design-system/00-tokens.md`:
```css
:root {
  --font-display: 'Bebas Neue', 'Trade Gothic Bold Condensed', sans-serif;
  /* Existing tokens stay: --font-sans (Inter), --font-serif (Source Serif Pro), --font-mono */
  --font-tabular: 'Inter', 'SF Mono', 'Menlo', monospace;
}

.stat, .number, .tabular,
td.numeric, .data-table td,
.percentile-value, .rank-value, .delta {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1;
  font-family: var(--font-ui, var(--font-sans));
}
```

**Rationale:** Source Serif Pro is already in `00-tokens.md` and works perfectly at 16-18px body. Inter has the strongest tabular numerals in the free-font universe. Bebas Neue adds the display register needed for hero findings and stadium-scoreboard energy. All free; total payload ~80KB variable woff2.

**Premium upgrade path:** Druk Wide (~$300 per-domain) replaces Bebas Neue for genuine distinctiveness. Not blocking.

### Decision 2: Page IA Archetypes
Six archetypes with concrete file-system mapping:

| Archetype | Pages | Renderer module |
|---|---|---|
| **Article** | `/daily/`, `/mailbag/`, `/reactions/<slug>`, `/editions/<n>/<slug>` | shared `articles/renderer.py` |
| **Dashboard** | `/`, `/hub/`, `/heisman/`, `/rankings/` | shared `dashboards/renderer.py` |
| **Profile** | `/programs/<slug>.html`, `/players/<slug>.html`, `/coaches/<slug>.html`, `/conferences/<slug>.html` | shared base, per-program overrides per v5-9 |
| **Database** | `/wire/`, `/editions/`, `/canon/<list>`, `/players/` | shared `database/renderer.py` |
| **Tentpole** | 9 marquee editions per year | shared base, manual per-edition CSS |
| **Anniversary** | `/anniversary/today/`, `/saturdays-past/<date>/` | shared `anniversary/renderer.py` |

Each renderer module gets a documented "what's allowed / what's not" spec.

### Decision 3: 6-Chart Vocabulary
Single module at `src/cfb_rankings/charts/__init__.py` that exports only the 6 approved chart types:
- `render_percentile_bar` (Baseball Savant)
- `render_trajectory_spark` (160×40 sparkline)
- `render_bump_chart` (rankings movement)
- `render_annotated_line` (NYT-style)
- `render_small_multiples_grid` (Tufte/Bloomberg)
- `render_heatmap`

Forbidden: pie charts (always), vertical bar charts (use percentile_bar instead), radar charts (except player fingerprint).

### Decision 4: Receipt Pattern Wire Format
Pattern C/D output schema extension:
```python
class PatternCOutput(TypedDict):
    body_markdown: str                          # prose with [1] inline markers
    headline: str
    dek: str | None
    citations: list[Citation]                   # NEW required field
    confidence: Literal["high", "medium", "low"]  # NEW required field
    sample_size: dict[str, int] | None          # NEW: {"reddit_mentions": 247, "beat_articles": 3}

class Citation(TypedDict):
    id: int
    source_kind: Literal["reddit", "beat_writer", "podcast", "wikipedia", "official", "cfbd"]
    source_url: str | None
    source_label: str
    source_date: str | None
    confidence: Literal["primary", "supporting", "background"]
```

Migration: new table `editorial_citations`.

Critic addition: `citation_critic` (Haiku or Sonnet) validates every [N] marker has a matching citation, every citation has a real source_url or verifiable source_label, density ≥1 per 200 words.

### Decision 5: Sample-Size Confidence Vocabulary
Three levels, calibrated against actual data distribution (NOT arbitrary):

Run this calibration once (1-hour ad-hoc analysis):
```sql
WITH per_team_week AS (
  SELECT team_id, strftime('%Y-%W', created_at_utc) AS week, COUNT(*) AS doc_count
  FROM conversation_documents cd
  JOIN conversation_document_targets cdt ON cd.document_id=cdt.document_id
  WHERE cd.created_at_utc > datetime('now', '-90 days')
  GROUP BY team_id, week
)
SELECT percentile values (p25, p50, p75, p90) FROM per_team_week;
```

Then set thresholds:
- **High** = above p75
- **Medium** = p25 to p75
- **Low** = below p25
- **Insufficient** = below p10 (suppress metric)

Self-adjusts as data volumes change. Re-run quarterly.

---

## Part C — Tier Strategy for the 17 Profiled Teams

Three tiers, calibrated by traffic potential × cultural relevance:

### Tier S — "Hand-tailored editorial product" (5 teams)
**Teams:** Alabama, Ohio State, Michigan, Notre Dame, Texas

These 5 account for an estimated 60%+ of team-page traffic. Each gets:
- Full bespoke renderer module (per v5-9 plan)
- Custom IA per the world-class brief (state-resolver, era arc, rivalry module)
- 5+ rituals fully illustrated with custom SVGs
- Pattern D adversarial-critique editorial on tentpole weeks
- Custom hero typography treatment (slight display weight variation)
- Featured in tentpole edition rotation

**Effort per team:** ~3-5 sessions after foundations ship.

### Tier A — "Programmatic bespoke" (8 teams)
**Teams:** Auburn, Florida, Georgia, Oklahoma, Oregon, Penn State, Tennessee, USC

These get:
- Shared bespoke renderer with per-team voice palette
- 3-5 rituals with ligne claire SVGs
- Pattern C standard editorial (not Pattern D)
- Shared hero typography
- Standard tentpole treatment

**Effort per team:** ~1-2 sessions after Tier S template proven.

### Tier B — "Profile-driven distinct" (4 teams)
**Teams:** Massachusetts, UConn, Vanderbilt, Washington

These get:
- Shared renderer with profile-frontmatter customization
- 3 rituals each
- Pattern C standard editorial
- Honest framing of each team's actual product context

**Effort per team:** ~0.5-1 session each.

**Total effort reduction:** 5×3 + 8×1.5 + 4×0.75 = 30 sessions (vs naive 17×3 = 51). Saves ~21 sessions / ~5 weeks.

### Mid-season tier promotion
Tiers aren't fixed. Promotion criteria (3-of-4 must trigger):
- Traffic to team page > median Tier S team's traffic for 4 consecutive weeks
- Team makes CFP playoff field (auto-promote during postseason)
- Team has a 5★ commitment or NFL draft pick in last 30 days
- Team appears in 3+ tentpole edition cover essays

Demotion is one-way: once promoted, stay promoted at least 1 full season.

---

## Part D — Technical Debt Sequencing

### Debt item 1: Pattern C critic tuning for short-form/JSON surfaces
**State:** pulse_lede 100% fall-back, pulse_themes_writer 71% fall-back. Paying 2× cost for no benefit.

**When:** BEFORE Sprint v5-5.4 (mockup sprint). Receipt pattern (v5-6a.5) depends on Pattern C reliability.

**Effort:** 2-3 sessions of prompt engineering. Different critic prompts for short-form (relax convergence) vs JSON (validate schema, not prose).

**Owner:** Window A (existing tech debt).

### Debt item 2: llm_usage_log dedup via call_id
**State:** quality_loop._emit_telemetry and CostMeter.record both insert; doubles per-surface counts.

**When:** BEFORE Sprint v5-10e (viral content). Telemetry-driven cost decisions need accurate numbers.

**Effort:** 1 session.

**Owner:** Window A.

### Debt item 3: Canon generator LLM rewrite
**State:** canon_top10 and canon_tail flags declared inert because generator is seed-authored.

**When:** DURING Sprint v5-10b (rivalry pages). Rivalry editorial benefits from same treatment.

**Effort:** 1-2 sessions.

**Owner:** Window A.

### Debt item 4: dawidd6 race condition Option B fix
**State:** Tactical fix works; long-term fix is DB-backed canonical pointer.

**When:** Defer to post-v5-12 launch unless it bites again.

**Owner:** Either window.

### Debt item 5: today_in_cfb_history workflow startup_failure
**State:** Non-live surface; no impact.

**When:** Bundle into Sprint v5-7.6 (mobile + Saturday Strip) since Strip benefits from today-in-history data.

**Owner:** Window B.

---

## Part E — Editorial Content Calendar

### Weekly cadence (in-season, Sept-Jan)
- **Monday 6am ET:** Mood Map + Power rankings + weekly take
- **Tuesday 6am ET:** "What we got wrong" recap
- **Wednesday 6am ET:** Deep-dive feature
- **Thursday 6am ET:** Thursday night game previews
- **Friday 6am ET:** Mailbag
- **Friday 5pm ET:** Weekend preview pack per marquee game
- **Saturday all day:** Saturday Strip live updates
- **Saturday 11pm ET:** Quick reaction takes per major game
- **Sunday 8am ET:** Full reaction Daily edition
- **Sunday 6pm ET:** Heisman update

### Weekly cadence (off-season, Feb-Aug)
- **Monday 9am ET:** Mood Map
- **Monday 10am ET:** Daily edition
- **Tuesday-Friday 10am ET:** Daily editions
- **Wednesday:** + "Today in CFB History"
- **Thursday:** + Recruit Watch update
- **Friday:** Mailbag
- **Friday 5pm ET:** Weekly Edition publish
- **Saturday:** "Saturdays Past" anniversary content
- **Sunday:** Light cadence (deep-dive Hub work)

### Slow content week fallback cascade
When nothing's happening (deep summer drought):
1. Anniversary content from `archive_threads`
2. Player retrospective (underappreciated season from 12-season DB)
3. Cohort archeology ("this fanbase 5 years ago")
4. Methodology deep-dive
5. "What we're reading" curation (3 columns + 2 threads + 1 podcast)
6. Tentpole pre-rolls (countdown content building to next tentpole)

If all 6 fail: skip the day with a small note. Better than empty content.

---

## Part F — Per-Sprint Acceptance + Kill Criteria

| Sprint | Acceptance | Kill |
|---|---|---|
| v5-5.4 (mockups) | 7 mockups produced; mobile + desktop variants; uses real data | If mockups reveal fundamental IA flaw, stop and re-plan |
| v5-5.5 (decisions) | 5 design-system docs updated/created with specific values | If can't decide on typography in 1 sprint, escalate |
| v5-6a.5 (receipts) | 100% Pattern C/D has citations; citation_critic catches missing 95%+ | If citation quality <80% after 2 weeks, demote to Pattern B |
| v5-7.5 (hero+samples) | Hero finding daily for 5+ archetypes; varies; sample-size on every metric | If findings sound robotic for 3 consecutive days, reformulate |
| v5-7.6 (mobile + Saturday Strip) | Strip <500ms load; bottom nav; auto-summary on articles | If Strip >5% error rate on gamedays, defer live ticker; ship countdown-only |
| v5-8.5 (rituals + texture) | All 17 profiles have rituals; module renders | If conference tints read as stereotype, remove |
| v5-10e (viral) | Mood Map auto-posts; 5 artifact types; X engagement >100 likes/share in 4 weeks | If viral artifacts get dunked persistently, audit data accuracy |
| v5-11.5 (dark + Cmd-K) | Dark mode on all archetypes; Cmd-K indexed; both pass accessibility | If dark mode introduces 10+ regressions, feature-flag off |

---

## Part G — Measurement & Feedback System

### Quantitative signals (via Vercel Analytics + GitHub digests)
| Metric | Baseline | Target (full v5) |
|---|---|---|
| Monthly unique visitors | unknown | 5x baseline |
| Mobile traffic % | ~50% | 65%+ |
| Avg session duration | <2 min | >4 min |
| Pages per session | <2 | >3.5 |
| Bounce rate | unknown | <40% |
| Return visitor % | unknown | >40% |
| Saturday Strip engagement (in-season) | n/a | >50% mobile sessions |
| Monday Mood Map shares (X) | n/a | >50 quote-tweets/post within 6 months |
| Cost per published edition | ~$0.50 | <$0.75 with quality lift |
| Receipt-pattern citation accuracy | n/a | >95% auditable monthly |

### Killer-app metric: Monday Mood Map shares
If >50 quote-tweets per Monday within 6 months of launch, the data moat is publicly visible and strategy is working. If not, audit the artifact design or distribution.

### Feedback loops
- **End of every sprint:** SESSION_LOG retrospective (what landed, what surprised, what to change)
- **End of every month:** Acceptance criteria review (which sprints hit, which didn't, why)
- **End of every quarter:** Plan-level retrospective (are we on track, what's the new highest-leverage item)

---

## Part H — Mockup-Level Specifications (the 5 highest-impact surfaces)

### H.1 Saturday Strip — Mobile UI Primitive

**In-season visual:**
```
┌──────────────────────────────────────────────────────────────────┐
│ 🔴 LIVE  IND 17 — PSU 14  •2Q 4:32              swipe →           │
├──────────────────────────────────────────────────────────────────┤
│ FINAL    TEX 24 — OU 21    UPSET                                  │
│ 7:30 ET  ALA — LSU         CBS                                    │
│ 8:00 ET  ORE — UTAH        ESPN                                   │
└──────────────────────────────────────────────────────────────────┘
```

**Off-season visual:**
```
┌──────────────────────────────────────────────────────────────────┐
│ 147 DAYS to kickoff      5★ QB SMITH → TEX      Camp opens Aug 3 │
└──────────────────────────────────────────────────────────────────┘
```

**Specs:**
- Fixed-position top of viewport on mobile only (desktop has full nav)
- Height: 44px live state → 56px expanded
- Background: warm cream with subtle bottom border
- Live indicator: pulsing red dot + "LIVE" text (only if motion not reduced)
- Horizontally scrollable; current focus snaps leftmost
- Each game tap → team page
- Auto-refresh: 30 sec during games, 5 min upcoming, 1 hour off-season
- Performance: single CFBD call cached 30 sec, ~5KB max

### H.2 Hero Finding — Page Archetype Component

**Visual structure:**
```
┌──────────────────────────────────────────────────────────────────┐
│                                                                   │
│   [WHAT THIS IS · 11px uppercase eyebrow]                         │
│                                                                   │
│   47 of 130 teams                                                 │
│   diverged from model rank this week                              │
│   ━━━━━━━━━━━ (amber underline accent)                            │
│                                                                   │
│   [Sample: 202,341 mentions · 47 sources · last 7 days]           │
│   [Confidence chip: ✓ high]                                       │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

**Generator algorithm** (`hero_findings/generator.py`):
- Candidate 1: Cohort divergence anomaly (count of teams diverging >15 spots)
- Candidate 2: Heisman race shift (biggest weekly mover)
- Candidate 3: Anniversary anchor (today-in-history)
- Candidate 4: Always-available fallback (avg fan mood)
- Picker: highest confidence_rank, then highest sort_priority

### H.3 Monday Mood Map — Viral Artifact

**Visual:** 1200×675px image (Twitter card optimal)

Contents:
- Masthead + week label
- Stylized US map with 130 team dots colored on belief ramp
- Top 8 movers labeled (4 up, 4 down) with delta + brief reason
- Sample-size footer
- CFB Index logo + URL

**Engineering:**
- Generated via Pillow every Monday 6am ET
- Auto-posted to X via GitHub Action at 9am ET
- File: 1200×675 PNG, <500KB

### H.4 Receipt Pattern — Article Render

**Mid-article inline citation:**
```
Sark has quietly turned Texas into a credible alternative for the
exact blue-chip prospects who used to rubber-stamp Georgia.¹
```

**Footer citation list:**
```
─── Sources ─────────────────────────────────────────
[1] Stewart Mandel · The Athletic · "Texas A&M-Texas
    rivalry redraws SEC recruiting" · May 12, 2026
[2] r/CFB · "Sark vs Kirby" thread · 318 replies · May 14
...
─────────────────────────────────────────────────────
```

**CSS treatment:** Superscript citation marker, color-coded amber, hover tooltip on desktop, tap-reveal on mobile, full list at article footer.

### H.5 Per-Team Rituals Strip — Team Page Module

**Visual:**
```
┌─────────────────────────────────────────────────────────────────┐
│  RITUALS                                                          │
│  ─────                                                            │
│                                                                   │
│  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐               │
│  │  🐘   │ │   ♫   │ │  🏛   │ │   ⚡  │ │   🎺  │ ← horizontal │
│  │RAMMER │ │ YEA   │ │ ELE-  │ │ PRE-  │ │ MILLI │   scroll on │
│  │JAMMER │ │ALABAMA│ │ PHANT │ │ GAME  │ │ ON    │   mobile    │
│  │       │ │       │ │ WALK  │ │ FLY-  │ │ DOLLAR│             │
│  │ since │ │ since │ │ since │ │ OVER  │ │ BAND  │             │
│  │ 1970  │ │ 1926  │ │ 1981  │ │ 2003  │ │ 1929  │             │
│  └───────┘ └───────┘ └───────┘ └───────┘ └───────┘               │
└─────────────────────────────────────────────────────────────────┘
```

**Specs:**
- 4-5 cards per team
- Card: 140×180px desktop, 120×160px mobile
- Ligne claire illustration family
- Horizontal scroll on mobile; static grid on desktop
- Tap card → modal/drawer with full description

---

## Part I — How to Execute

### Two-window parallel model

**Window A (original) continues:**
- Existing IMPLEMENTATION_PLAN sprints
- Tech debt cleanup
- Coordinates via SESSION_LOG + COORDINATION.md

**Window B (new) executes:**
- v2 addendum sprints in order
- Reads COORDINATION.md before touching shared files
- Stops at each sprint's acceptance gate

### Coordination cadence
- **Daily:** ~5 min glance at both windows' SESSION_LOG for blockers
- **Weekly (Sunday evening):** 30 min review of both windows' work + COORDINATION.md conflicts
- **Monthly:** acceptance criteria review across both windows

### When to refresh a window
After ~3-4 weeks of sustained work, AI agents accumulate context debt. Plan for 3-4 fresh-window refresh cycles across the 17-week timeline.

---

## Part J — What I Cut From v1 (be explicit)

These were considered and dropped:
1. **Conference visual tints** — risk of stereotyping outweighs differentiation
2. **AI-voice video format** — too risky for solo dev
3. **Personalization** — premature
4. **Native mobile apps** — PWA only is correct
5. **Live gameday hub** — ESPN owns this; Saturday Strip is enough
6. **Bento grids** — trend has peaked
7. **Premium subscription** — Year 2 question at earliest

---

## Part K — Critical Path (the literal execution order)

```
Hour 0-48: Part A actionable checklist
   ↓
Sprint v5-5.4 (1 week): Mockup sprint — 7 high-fidelity HTML mockups
   ↓
Sprint v5-5.5 (1 week): Lock 5 foundational decisions
   ↓
[Existing v5-6a/6b ships per current plan — visual layer, OG cards]
   ↓
Sprint v5-6a.5 (1 week): Receipt pattern foundation
   ↓
Sprint v5-7.5 (1 week): Hero findings + sample-size system
   ↓
Sprint v5-7.6 (1 week): Mobile Saturday Strip + bottom nav
   ↓
[Existing v5-8 ships per current plan — Pattern D + admin UI]
   ↓
Sprint v5-8.5 (1 week + ~10hr curation): Rituals + cultural identity
   ↓
[Existing v5-9 ships per current plan — but now uses Tier strategy from Part C]
   ↓
[Existing v5-10a/b/c/d ships per current plan]
   ↓
Sprint v5-10e (2 weeks): Viral content engine
   ↓
[Existing v5-11 ships per current plan]
   ↓
Sprint v5-11.5 (2 weeks): Dark mode + Command-K
   ↓
Existing v5-12 (launch retrospective)
```

Total net-new effort beyond existing plan: ~10 weeks if serial. ~4-6 weeks if parallel with Window A. Plus ~25-40 hours of editorial curation (mostly rituals data for 17 teams).

---

## Part L — Single Biggest Improvement vs v1

**Sprint v5-5.4 (mockup sprint) as a HARD GATE before any addendum coding.** Most "best in the world" projects fail because they code from imagination; mockups force the design problem to be solved before engineering commits to it.

If you only do ONE thing from this iteration: insert Sprint v5-5.4 (7 HTML mockups using real data) before any new code sprint starts. Saves 2-3 sprints of "we built it but it doesn't fit" downstream.
