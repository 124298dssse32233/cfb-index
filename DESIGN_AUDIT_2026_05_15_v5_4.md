# CFB Index — v5.4 Offseason Engine + Calendar Labeling

**Date:** 2026-05-15
**Author:** Claude (synthesis of 3 v5.4 investigators: offseason content strategy, calendar labeling audit, offseason data flows audit)
**Status:** Additive to v5.3. Defines (a) the 14-week May 15 → Aug 30 offseason engagement engine and (b) the surgical fix for "Week N" labels that read as garbage during offseason.

---

## TL;DR

**Owner directives addressed:**
1. *"Focus on how to make content super engaging from today through the beginning of the season."* → 14-week phase-by-phase content calendar with 12 new surfaces (S1-S12) anchored by day-of-week cadence, 9 marquee tentpole dates, and 3 must-have data adapters.
2. *"Make sure it doesn't say 'week 31' anywhere for the offseason."* → 41-hit codebase audit found 11 offseason-broken labels concentrated in 5 files. New `cfb_calendar.py` helper module + 8 PR batches replace them with hybrid convention: phase label + `(X days to kickoff)` parenthetical.

**Critical finding flagged separately:** `wire/offseason_fallback.py` ships 14 **hardcoded fake transactions** (real player names + invented destinations) labeled `source_kind='unverified'` to production when wire data is thin. This is a data-integrity bug, not a content bug. Sprint v5-1 must replace it.

**Net effect on the program:**

| | v5.3 | **v5.4 additions** |
|---|---|---|
| Offseason daily cadence | unspecified | **8-band homepage stack + 7-day cadence with anchors** |
| Offseason content surfaces | implicit ("offseason editions") | **12 named surfaces (S1-S12) with data manifests + cadences** |
| Tentpole editions | "weekly editions" | **9 named marquee dates (100/50/25/10 days, media days, fall camp, AP poll, Week 0)** |
| Calendar labels in user copy | inconsistent ("Week 21") | **Hybrid: phase label + parenthetical (X days to kickoff)** |
| Fake-news fallback | unflagged | **Critical fix in Sprint v5-1: real-data retro replaces hardcoded entries** |
| New workflows | as v5.3 | **+4 offseason-specific crons (portal heat, recruiting pulse, today-in-history, kickoff countdown)** |
| Data-adapter gaps | unflagged | **3 must-haves: coaching changes feed, portal_moves persistence, archive_threads daily retro** |

All v5.3 architecture (Agent SDK credit, 17-week roadmap, $0 incremental cost, quality_loop, proprietary data manifests) carries forward unchanged.

---

## Part 1 · The Critical Bug — `wire/offseason_fallback.py` Ships Fake News

Sprint v5-1 must address this before anything else in this document.

### What's in the file today

`src/cfb_rankings/wire/offseason_fallback.py` contains ~14 hardcoded transactions with real player names attached to invented destinations (e.g., "Quinn Ewers to Ohio State"). These ship as `wire_entries` rows with `source_kind='unverified'` when the live CFBD portal feed returns thin results during offseason. They surface on the homepage `/wire/` ticker.

The "unverified" label is invisible to readers — the wire panel renders the headline verbatim. Effectively, the site has been silently publishing fan-fiction transactions during the dead months.

### The fix (Sprint v5-1, Day 2 — alongside the model-version bump PR)

**Replace `offseason_fallback.py` with a real-data retro selector:**

```python
# src/cfb_rankings/wire/offseason_fallback.py (rewrite)
"""Offseason wire fallback. Surfaces REAL historical content when live
flow is thin. Never fabricates."""

from datetime import date, timedelta
from typing import Iterable

def select_retro_wire_rows(today: date, db, n: int = 6) -> Iterable[dict]:
    """Pull real wire rows from the same calendar window N years back.

    Priority order:
      1. Same-MM-DD ±2 days in years 2024, 2023, 2022, 2021, 2020 — pull
         real `wire_entries` from those windows tagged `_provider='retro'`.
      2. Top portal/recruiting commits from current year (player_recruiting_profiles)
         that haven't been wire-ed yet — promote with action='commit_anniversary'.
      3. Top archive_threads from same calendar week N years back — promote
         as 'on this date' editorial cards.

    Every returned row carries:
      - source_kind='retro' (NOT 'unverified')
      - retro_year (so the renderer can prefix "5 years ago today:")
      - real player names + real outcomes (no fabrication)
    """
    ...
```

Verification: grep `wire_entries` rendered on homepage for any `source_kind='unverified'`. After fix, zero hits.

### Why this lands as a Sprint v5-1 patch, not a v5-4 deliverable

Three reasons:
1. It's a data-integrity bug currently in production. Same-day fix.
2. It's a tiny PR (~80 lines replaced) — fits Sprint v5-1 Day 2 alongside the model-version bump.
3. Most of v5.4's "Today in CFB History" surface (S5) reuses the same retro selector — solving this seeds S5.

---

## Part 2 · Calendar Labeling Fix

### 2.1 The audit finding

41 user-facing "Week N" references in the codebase, classified:
- **11 OFFSEASON-broken hits** (must fix): `fan_intelligence.py:122,235,402,523,1325`; `vibe_shifts.py:329,352`; `hub_page.py:208`; `reporting.py:12006,14287,15889,15890,16049,23356`; `team_pages/renderer.py:761,942`
- **28 IN-SEASON hits** (KEEP — tied to stored game-week rows): chronicle streams, signature moments, impact cards, journey points
- **2 narrative-generator hits** (improve, not fix): `narrative_generator.py:508-528` — works in-season, reads awkwardly when last game was 6 months ago

### 2.2 The recommended convention

**Hybrid — phase label + parenthetical kickoff distance:**

| Context | Format | Example |
|---|---|---|
| Section header | `{phase_label}` | "Late Spring", "Fall Camp", "Bowl Season" |
| Eyebrow / dateline | `{phase_label} · {N} days to kickoff` | "Late Spring · 106 days to kickoff" |
| Article body | Human dates | "On May 15", "in late spring" (NOT "Week 21") |
| Permalinks / archive URLs | ISO `YYYY-WW` | data layer only, never user-facing |
| Bowl season | Named labels | "Bowl Season", "CFP Quarterfinal Week", "CFP Title Week" |
| In-season | `Week N` | "Week 1", "Rivalry Week" (unchanged) |
| Game-week approach | `Game Week ({N} days to kickoff)` | "Game Week (3 days to kickoff)" |

**Rejected alternative: "Offseason Week N" counting from CFP title.** "Welcome to Offseason Week 17" reads as defunct-podcast — and the existing 10-phase taxonomy in `state_resolver.py:39-52` does the same job better.

### 2.3 The helper module — `src/cfb_rankings/common/cfb_calendar.py`

New module. Single source of truth for all user-facing date/phase/kickoff labeling. Public API:

```python
def kickoff_date(season: int, db) -> date:
    """First FBS game of given season. Queries games table; falls
    back to KEY_EVENTS_<season> week_0_kickoff if DB empty."""

def days_to_kickoff(today: date, season: int | None = None, db=None) -> int:
    """Days until next FBS kickoff. Rolls forward if past current season's."""

def cfp_title_game_date(season: int, db) -> date:
    """CFP title game ending the given season."""

def is_offseason(today: date, db) -> bool: ...
def is_in_season(today: date, db) -> bool: ...

def human_phase_label(today: date, db) -> str:
    """Phase label with key-event promotion:
      - If today within (event.start - 7) ≤ today ≤ (event.end + 1):
        return f'{event.label} Week' (e.g. 'SEC Media Days Week')
      - Else: PHASE_HUMAN_LABEL[_MONTH_TO_PHASE[today.month]]
      - In-season override: canonical 'Week N' / 'Rivalry Week' / 'CFP Title Week'"""

def cfb_week_label(today: date, db) -> str:
    """Canonical 'where are we' label. human_phase_label + parenthetical
    '(N days to kickoff)' when offseason and >7 days out.
    Within 7-day game-week window: 'Game Week (N days to kickoff)'.

    Examples:
      2026-05-15 → 'Late Spring (106 days to kickoff)'
      2026-07-15 → 'SEC Media Days Week (45 days to kickoff)'
      2026-08-25 → 'Game Week (4 days to kickoff)'
      2026-08-29 → 'Week 1'
      2026-11-28 → 'Rivalry Week'
      2027-01-11 → 'CFP Title Week'
      2027-01-15 → 'Bowl Season Closed (217 days to kickoff)'
    """

def cfb_week_label_for_window(today: date, iso_week: int, db) -> str:
    """For 'updated_label' fields — fan_intelligence pattern.
    In-season → 'Week 9 window'. Offseason → '{phase_label} window'."""

def archive_week_key(today: date) -> str:
    """ISO YYYY-WW. NEVER surface to readers — data-layer key only."""
```

### 2.4 The `KEY_EVENTS_2026` table

Verified dates against 2025 actual events as anchors:

```python
KEY_EVENTS_2026: list[KeyEvent] = [
    KeyEvent("nfl_draft",               "NFL Draft",           date(2026, 4, 23), date(2026, 4, 25)),
    KeyEvent("transfer_window_spring",  "Spring Portal Close", date(2026, 4, 30)),
    KeyEvent("big_12_media_days",       "Big 12 Media Days",   date(2026, 7,  8), date(2026, 7, 10)),
    KeyEvent("sec_media_days",          "SEC Media Days",      date(2026, 7, 14), date(2026, 7, 17)),
    KeyEvent("acc_kickoff",             "ACC Kickoff",         date(2026, 7, 22), date(2026, 7, 24)),
    KeyEvent("big_ten_media_days",      "Big Ten Media Days",  date(2026, 7, 27), date(2026, 7, 28)),
    KeyEvent("fall_camp_open",          "Fall Camp Opens",     date(2026, 8,  3)),
    KeyEvent("preseason_ap_poll",       "Preseason AP Poll",   date(2026, 8, 17)),
    KeyEvent("week_0_kickoff",          "Week 0 Kickoff",      date(2026, 8, 22), is_kickoff=True),
    KeyEvent("week_1_kickoff",          "Week 1 Kickoff",      date(2026, 8, 29), is_kickoff=True),
    KeyEvent("rivalry_saturday",        "Rivalry Saturday",    date(2026, 11, 28)),
    KeyEvent("army_navy",               "Army-Navy",           date(2026, 12, 12)),
    KeyEvent("cfp_first_round",         "CFP First Round",     date(2026, 12, 18), date(2026, 12, 20)),
    KeyEvent("cfp_quarterfinals",       "CFP Quarterfinals",   date(2026, 12, 31), date(2027, 1,  1)),
    KeyEvent("cfp_semifinals",          "CFP Semifinals",      date(2027, 1,  8), date(2027, 1, 9)),
    KeyEvent("cfp_title_game",          "CFP Title Game",      date(2027, 1, 11), is_cfp_title=True),
    KeyEvent("nsd_early",               "Early Signing Day",   date(2026, 12,  3)),
]

PHASE_HUMAN_LABEL = {
    "bowl-and-carousel":     "Bowl Season",
    "nsd-and-portal":        "National Signing Day & Portal Window",
    "spring-and-portal":     "Spring Practice & Portal Window",
    "dead-period-heritage":  "Late Spring",
    "media-days":            "Media Days Season",
    "camp":                  "Fall Camp",
    "early-season":          "Early Season",
    "stakes-rising":         "Stakes Rising",
    "rivalry-peak":          "Rivalry Window",
    "cfp-selection-and-bowl":"Selection & Bowl Window",
}
```

Move to `config/cfb_calendar_events.yml` after first season; keep inline through Sprint v5-1.

### 2.5 PR batches (8 surgical fixes)

| # | Batch | Files | Hits | Effort |
|---|---|---|---|---|
| 1 | Helper module + tests | `common/cfb_calendar.py` (new) + `tests/test_cfb_calendar.py` (new) | 0 (new) | 1 day |
| 2 | Fan Intel updated_label | `fan_intelligence.py:122,235,402,523,1325` | 5 | 2 hrs |
| 3 | Vibe Shifts page | `vibe_shifts.py:329,352` | 2 | 1 hr |
| 4 | Fan Intel Hub masthead | `hub_page.py:208` | 1 | 1 hr |
| 5 | Reporting.py homepage/Heisman/Site Pulse | `reporting.py:12006,14287,15889,15890,16049,23356` | 6 | 3 hrs |
| 6 | Team Page Pulse renderer | `team_pages/renderer.py:761,942` | 2 | 2 hrs |
| 7 | Narrative generator offseason variant | `team_pages/narrative_generator.py:508-528` | 4 | 2 hrs |
| 8 | Signature story season-boundary guard | `signature_story.py:720` | 1 | 1 hr |

**Total: ~1.5 days of work for 21 fixes across 8 PRs.** All ship in Sprint v5-1 Week 1.

### 2.6 Test suite

`tests/test_cfb_calendar.py`:

```python
def test_late_spring(db):
    assert cfb_week_label(date(2026, 5, 15), db) == "Late Spring (106 days to kickoff)"

def test_sec_media_days_week(db):
    assert cfb_week_label(date(2026, 7, 15), db) == "SEC Media Days Week (45 days to kickoff)"

def test_game_week_before_kickoff(db):
    assert cfb_week_label(date(2026, 8, 26), db) == "Game Week (3 days to kickoff)"

def test_week_1(db):
    assert cfb_week_label(date(2026, 8, 29), db) == "Week 1"

def test_rivalry_week(db):
    assert cfb_week_label(date(2026, 11, 28), db) == "Rivalry Week"

def test_cfp_title_week(db):
    assert cfb_week_label(date(2027, 1, 11), db) == "CFP Title Week"

def test_post_title_returns_to_offseason(db):
    label = cfb_week_label(date(2027, 1, 15), db)
    assert "Bowl Season" in label or "Carousel" in label
    assert "days to kickoff" in label

def test_archive_week_key_format(db):
    assert archive_week_key(date(2026, 5, 15)) == "2026-20"

def test_is_offseason(db):
    assert is_offseason(date(2026, 5, 15), db) is True
    assert is_in_season(date(2026, 9, 1), db) is True
```

---

## Part 3 · The Offseason Content Engine

### 3.1 The daily homepage on an offseason Tuesday

Five-band stack replaces the in-season homepage:

| Band | Content | Source |
|---|---|---|
| 1. **Phase banner** (top strip) | `LATE SPRING · 106 DAYS TO KICKOFF` | `cfb_calendar.cfb_week_label()` |
| 2. **Hero card** (`/the-daily/`) | Today's lead: tentpole story / anniversary retro / vibe shift | `daily/selector.py` extended with offseason branch |
| 3. **Lead module** (rotating by day-of-week) | Tue = Portal Heat (S3), Wed = Recruit Watch (S4), Thu = Heisman Watch (S9), Fri = Mailbag, Sat = Saturdays Past (S7), Sun = Cohort Ledger (S2), Mon = Power Drift | New `daily/offseason_modules.py` |
| 4. **Below-fold grid** (3 cards) | Latest /wire/, latest /editions/, today's Days-to-Kickoff card | Existing + S1 |
| 5. **Section rail** (bottom) | `/heisman-watch/` `/portal-heat/` `/recruit-board/` `/preseason-rankings/` `/anniversary/today/` `/the-room/` `/canon/` | Replaces in-season scoreboard rail |

**Critical principle:** Every offseason day must produce one new, dated artifact above the fold. S5 (Today in CFB History) is the safety net — date-anchored against `team_chronicle_observations` + `archive_threads`, never empty.

### 3.2 The 7-day rhythm

| Day | Anchor surface | Data sources | Replaces in-season |
|---|---|---|---|
| **Mon** | Power Drift Monday | `power_ratings_weekly` (recompute) | `/rankings/` update |
| **Tue** | Portal Heat Tuesday | `transfer_portal_entries`, `team_aliases` | (new) |
| **Wed** | Recruit Watch Wednesday | `recruiting_rankings`, `recruiting_class` | (new) |
| **Thu** | Heisman Watch Thursday | `player_season_summary`, `player_conversation_features` | In-season Heisman board |
| **Fri** | Mailbag (unchanged) | `mailbag_*` tables | (same) |
| **Sat** | Saturdays Past | `team_chronicle_observations`, `editions_archive`, `archive_threads` | In-season slate |
| **Sun** | Offseason Cohort Ledger | `fanbase_mood_weekly`, `fanbase_cohort_weekly`, `lexicon_weekly` | In-season Vibe Shift Ledger |

Same day-of-week brand voice anchors as in-season. Different data shape, same return-habit reinforcement.

### 3.3 The 8 offseason content phases

| # | Phase | Window | Hero surfaces |
|---|---|---|---|
| 1 | **Late-Spring Settling** | May 15 – May 31 | S3 Portal Heat launch · Grad-transfer ticker · NFL Pipeline 2026 retro (S11) · "Where Are They Now: 2025 stars" · Spring-game retro storyline |
| 2 | **Summer Open** | Jun 1 – Jun 14 | S1 Days-to-Kickoff goes live · S4 Recruit Watch debut · "100 Days to Kickoff" tentpole (May 21 anchor) · S9 Preseason Heisman Board v1 |
| 3 | **Visit Window** | Jun 15 – Jun 30 | Recruit board live updates · Official-Visits tracker edition · Conference Pulse Map ("Where the 2026 class is going") · Anniversary retros for 1996/2006/2016 (decade anchors) |
| 4 | **Independence Quiet** | Jul 1 – Jul 13 | "50 Days to Kickoff" tentpole (Jul 10) · Lexicon-spike weekly · Canon refresh window · Late-release schedule reactions |
| 5 | **Media Days Cascade** | Jul 14 – Jul 27 | **S8 Conference Media Days Live** — daily SEC → Big 12 → ACC → Big Ten · Quote-of-the-day from `source_observations` · Preseason watchlist trackers · Coach-quote receipts for Receipts cycle |
| 6 | **Watch List Season** | Jul 28 – Aug 4 | Preseason AP Poll reactions · S9 Heisman Watch v2 (post-watchlist) · Storyline reseed ("where we are entering camp") · **S6 Schedule Deep Dive begins** (1 game/day starting Aug 1) |
| 7 | **Fall Camp Open** | Aug 5 – Aug 18 | **S10 Fall Camp Tracker per profiled program** (daily) · Depth-chart watch · Injury report wire · "25 Days / 14 Days" anchored editions · Preseason rankings reactions |
| 8 | **Game Week Approach** | Aug 19 – Aug 29 | S6 Schedule Deep Dive completes (Aug 28 = Week 1 Sat) · **Week 0 Preview special edition** (Aug 20) · Power Ratings final preseason · Season Doppelganger v1 · **"Kickoff Day" tentpole hero edition** (Aug 29) |

### 3.4 The 9 marquee tentpole dates

| Date | Tentpole | Why it matters |
|---|---|---|
| **May 21, 2026** | "100 Days to Kickoff" | First milestone; sets countdown cadence |
| **Jul 10, 2026** | "50 Days to Kickoff" | Mid-summer anchor + media-days lead-in |
| **Jul 14, 2026** | SEC Media Days kick | Live-coverage page debuts |
| **Jul 21, 2026** | Big Ten Media Days + Watchlists | Hero edition + watchlist tracker launch |
| **Jul 28, 2026** | Preseason AP Poll release | Reactions cascade — cohort-by-cohort mood shifts |
| **Aug 4, 2026** | "25 Days" + Fall Camp Open | First Camp Tracker update; depth-chart wire |
| **Aug 19, 2026** | "10 Days to Kickoff" | Final countdown beat; schedule deep dive at midpoint |
| **Aug 22, 2026** | Week 0 Kickoff Edition | First games — transition begins |
| **Aug 29, 2026** | Week 1 Hero Edition | Full transition; `season_phase` → IN_SEASON |

Each tentpole gets a Pattern D adversarial-critique Edition cover essay (v5.3 Part 3, Pattern D — single use case extends from "Edition cover essay" to "every marquee tentpole").

---

## Part 4 · The 12 New Surfaces (S1-S12)

Detailed manifests for each new offseason surface. Cadence + data tables + sample headline + sprint slot.

### S1 — Days to Kickoff Countdown

- **URL:** `/kickoff/` + sitewide phase strip
- **Cadence:** Daily (static page, regenerated by `kickoff_countdown.yml`)
- **Data:** `season_phase.py`, `games` (first FBS game lookup via `cfb_calendar.kickoff_date()`)
- **Renderer:** Reuses v5.3's R1 share-card SVG renderer
- **Sample headline:** "99 Days. Penn State at Nevada is the first kickoff."
- **Sprint:** v5-1 (lightest possible; ships day 1 with cfb_calendar.py)

### S2 — Offseason Cohort Ledger

- **URL:** `/hub/cohort-shifts/<week>/`
- **Cadence:** Weekly (Sun, after `compute-cohort-week`)
- **Data:** `fanbase_mood_weekly` (Δ vs trailing 4w), `fanbase_cohort_weekly` (cohort transitions), `lexicon_weekly` (phrase spikes)
- **Renderer:** Extends existing `vibe_shifts.py`
- **Sample headline:** "Auburn lifer-cohort belief is up 18 points since spring. Recruiting is the reason."
- **Sprint:** v5-3

### S3 — Transfer Portal Heat Index

- **URL:** `/portal-heat/`
- **Cadence:** Daily during open windows (Dec, April-May); weekly otherwise
- **Data:** `transfer_portal_entries`, `portal_moves` (after persistence adapter), `team_aliases`, `recruiting_rankings`, `fanbase_mood_weekly` (Δ for destination program)
- **Renderer:** New module `src/cfb_rankings/portal_heat/`
- **Sample headline:** "Net +3 four-stars to Michigan since May 1. Net -2 from FSU."
- **Sprint:** v5-2 (after `portal_moves` persistence adapter lands)

### S4 — Recruit Watch Board

- **URL:** `/recruit-board/<class_year>/`
- **Cadence:** Daily (rendered from `recruiting_pulse.yml`)
- **Data:** `recruiting_rankings`, `recruiting_class`, `wire_entries` (cfbd-recruit subset)
- **Renderer:** New module `src/cfb_rankings/recruiting/`
- **Sample headline:** "Texas's 2027 class jumped from #8 to #3 on this week's flips."
- **Sprint:** v5-3

### S5 — Today in CFB History

- **URL:** `/anniversary/today/` + daily card
- **Cadence:** Daily generation in `generate-daily`
- **Data:** `team_chronicle_observations` (same MM-DD across 2014-2025), `historical_seasons_summary`, `editions_archive`, `archive_threads`
- **Renderer:** Extends `daily/selector.py` to pick anniversary content; reuses share-card renderer
- **Sample headline:** "On this date in 2006, Boise beat Oklahoma in the Fiesta. Here's the Reddit thread the morning after."
- **Sprint:** v5-2 (alongside `offseason_fallback.py` rewrite — shares retro-selector logic)

### S6 — Schedule Deep Dive

- **URL:** `/schedule-preview/<a>-vs-<b>/`
- **Cadence:** One game/day, Aug 1 – Aug 28
- **Data:** `games`, `power_ratings_weekly`, `team_aliases`, profile YAMLs, `team_rivalry`
- **Renderer:** New module `src/cfb_rankings/schedule_preview/`
- **Sample headline:** "Ohio State at Texas: the model gives the Horns a 41% chance. Here's why the gap is closer than it looks."
- **Sprint:** v5-6a (must ship before Aug 1 daily cadence begins)

### S7 — Saturdays Past

- **URL:** `/saturdays-past/<date>/`
- **Cadence:** Weekly (Sat)
- **Data:** `editions_archive`, `team_chronicle_observations` (same Sat 5-10 years ago), `archive_threads`
- **Renderer:** Extends `editions/archive_renderer.py`
- **Sample headline:** "10 years ago today: 2016 Week 1. The Reddit thread that introduced Lamar Jackson."
- **Sprint:** v5-4

### S8 — Conference Media Days Live

- **URL:** `/media-days/<conference>/<year>/`
- **Cadence:** Daily during 4-week window (Jul 14 – Jul 27)
- **Data:** `wire_entries` (actor_kind='conference'), `source_observations`, `conversation_documents` (topic='media_days')
- **Renderer:** Extends `wire/` + `daily/`
- **Sample headline:** "Day 1 of SEC Media Days: Saban is gone, Kirby is the dean, and Kalen DeBoer faces the room."
- **Sprint:** v5-5 (scaffolding) + v5-9 (live operation during media days)

### S9 — Preseason Heisman Watch

- **URL:** `/heisman-watch/preseason/<year>/`
- **Cadence:** Weekly (May-Aug)
- **Data:** `heisman_market_odds_weekly` (live from Kalshi/Polymarket), `player_season_summary`, `player_conversation_features`, `player_advanced_metrics`, `wiki_awards`
- **Renderer:** Extends `src/cfb_rankings/models/heisman.py` with offseason scoring
- **Sample headline:** "Preseason Heisman board: Manning at 1, Klubnik at 2, Sellers rising."
- **Sprint:** v5-5

### S10 — Fall Camp Tracker

- **URL:** `/programs/<slug>/camp/` (per profiled program)
- **Cadence:** Daily (Aug 5 – Aug 28)
- **Data:** `wire_entries`, profile YAML (depth-chart hints), `team_chronicle_observations`, `spring_events`/`camp_events` table
- **Renderer:** Extends `team_pages/` (profiled) + `reporting.py` (legacy)
- **Sample headline:** "Alabama camp Day 7: Mauk took every first-team rep. The QB room has narrowed to one."
- **Sprint:** v5-10a (scaffolding) → goes live Aug 5

### S11 — Offseason Receipts Court

- **URL:** `/receipts/offseason/<year>/`
- **Cadence:** Weekly
- **Data:** `predictive_claims`, `daily_takes`, `wire_entries` (May-Aug only)
- **Renderer:** Extends `receipts/`
- **Sample headline:** "We said in April that Oregon's portal class was the best. Three commits later, here's the verdict."
- **Sprint:** v5-11 (post-launch retrospective harvest)

### S12 — Dead Zone Mailbag

- **URL:** `/mailbag/dead-zone/` (extends `/mailbag/`)
- **Cadence:** Weekly (Fri)
- **Data:** `mailbag_*` tables with offseason prompts
- **Renderer:** Adds offseason theme to `mailbag/synthesizer.py`
- **Sample headline:** "Five questions, no scoreboard. Mailbag is the offseason scoreboard."
- **Sprint:** v5-4

---

## Part 5 · The 3 Must-Have Data Adapters

Sprint v5-1 ships these alongside the labeling fix and offseason_fallback.py rewrite.

### Adapter 1 — `portal_moves` persistence

**Problem:** Table `portal_moves` exists in `migrations.py:1238` with correct schema. Live wire path queries CFBD `/player/portal` endpoint at `wire/ingestion.py:58` but the result rows never get UPSERTed into `portal_moves`. So S3 (Portal Heat Index), Tier-1 Reaction stories filtered by portal, and v5.3 prompt-context manifests pointing at `portal_moves` all hit empty table.

**Fix:** Add ~30-line adapter to `wire/ingestion.py` that upserts every CFBD portal API result into `portal_moves` with deduplication on `(player_external_id, entered_at_utc)`.

**Verification:** After Sprint v5-1 close, query `SELECT count(*) FROM portal_moves` returns >500 (May 2026 spring window count).

### Adapter 2 — Coaching changes feed

**Problem:** Table `coaching_changes` exists in `migrations.py:1423`. No automated writer. Currently populated only from manual editorial seed at `data/offseason/2026/coaching.json`. So coaching-hire stories, narrative pivots, and Connections Desk pieces all rely on Kevin manually adding rows.

**Fix:** Add Footballscoop RSS adapter (free) + 247Sports coaching tracker scrape. New file `src/cfb_rankings/ingest/sources/coaching_tracker.py`. Daily cron writes new coaching events to `coaching_changes` table + emits a `wire_entries` row.

**Verification:** Manually trigger a coaching change (test with last week's news); confirm row appears in `coaching_changes` + corresponding wire entry.

### Adapter 3 — `archive_threads` daily retro pull

**Problem:** `ArcticShiftClient` exists at `clients/reddit_arctic_shift.py`. No cron uses it daily. So S5 (Today in CFB History), S7 (Saturdays Past), and storyline-chapter prompt-context manifests pointing at `archive_threads` for "this week N years ago" all hit empty table.

**Fix:** New daily workflow `archive_retro_daily.yml`. Pulls same-MM-DD across 2014-2025 from Arctic Shift, writes to `conversation_documents` tagged `_provider='arctic_shift_retro'` and (when high-engagement) promotes to `archive_threads`.

**Verification:** After Sprint v5-1 close, S5 surface renders an actual historical Reddit thread, not "Awaiting Signal" fallback.

---

## Part 6 · Workflow Cadence Adjustments

Three existing workflows get offseason-aware modifications:

### `wire-daily-04am-et.yml` — Bump to 2x/day during fall camp

```diff
 on:
   schedule:
-    - cron: '0 9 * * *'   # 04:00 ET daily
+    - cron: '0 9 * * *'   # 04:00 ET daily
+    - cron: '0 22 * * 8-12 *'  # 18:00 ET daily during August (fall camp window)
```

Captures evening fall-camp news the next morning, not 24h later.

### `ingest_daily.yml` — Split into morning + afternoon runs Jun-Aug

```diff
 on:
   schedule:
-    - cron: '0 9 * * *'   # 09:00 UTC
+    - cron: '0 9 * * *'    # 09:00 UTC morning
+    - cron: '0 21 * * 6,7,8 *'  # 21:00 UTC afternoon during Jun-Aug
```

Catches Substack posts published in the afternoon same day instead of next morning.

### `compute_full_pass.yml` — Monthly auto-trigger during offseason

```diff
 on:
   workflow_dispatch:
+  schedule:
+    - cron: '0 8 1 5,6,7 *'   # 1st of May/Jun/Jul, 08:00 UTC — NFL pipeline refresh
```

Keeps the NFL Pipeline 2026 retros (S11) fresh as undrafted-FA signings happen.

### New workflows

| Workflow | Cron | Purpose |
|---|---|---|
| `transfer_portal_heat.yml` | 3x/day during portal windows (Dec, Apr-May); daily otherwise | S3 Portal Heat Index |
| `recruiting_pulse.yml` | Daily 06:00 UTC, May-Aug | S4 Recruit Watch Board |
| `today_in_cfb_history.yml` | Daily 05:00 ET | S5 Today in CFB History |
| `kickoff_countdown.yml` | Daily 01:00 ET (just JSON refresh) | S1 sitewide countdown strip |
| `archive_retro_daily.yml` | Daily 03:00 ET | Adapter 3 (archive_threads pull) |

5 new workflows. All lightweight (<5 min wall-clock each). Fits within GitHub Actions free-tier (public repo).

---

## Part 7 · Revised Sprint v5-1 Day 1-2 Brief

Updated from v5.3 Part 6. Adds offseason-specific work to the foundation sprint.

### Day 1 Morning — Five patches (was 4 in v5.3, +1 here)

1. **`llm_runtime.py` prompt caching** (90 min, from v5.2)
2. **`backfill_full_history.yml` route fix** (5 min, from v5.2)
3. **`publish_site.yml` failure propagation** (30 min, from v5.2)
4. **Model-version bump PR** (45 min, from v5.3)
5. **🆕 `wire/offseason_fallback.py` rewrite** (60 min) — replace 14 hardcoded fake transactions with real-data retro selector

### Day 1 Afternoon — Trigger world_class_enrich + verify offseason flow

After patches merge, trigger `world_class_enrich.yml`. Verify (post-enrich):
- Wire homepage panel shows real retro content (no `source_kind='unverified'`)
- Site rebuilt with new 2014-2025 backfill data live

### Day 2 — `cfb_calendar.py` helper module + 8 PR batches

- Morning: Land helper module + tests (Batch 1)
- Afternoon: Land Batches 2-5 (Fan Intel, Vibe Shifts, Hub masthead, Reporting.py)

### Day 3 — Remaining label fixes + 3 must-have data adapters

- Morning: Batches 6-8 (Team Page Pulse, narrative offseason variant, signature story guard)
- Afternoon: Adapter 1 (portal_moves persistence) — extends existing `wire/ingestion.py`

### Day 4 — Adapters 2 + 3

- Morning: Adapter 2 (coaching changes RSS) + new `coaching_tracker.py` module
- Afternoon: Adapter 3 (archive_threads daily retro) + new `archive_retro_daily.yml` workflow

### Day 5 — `quality_loop.py` module (from v5.3 Sprint v5-1 brief)

(unchanged from v5.3 Part 6)

### Sprint v5-1 close criteria — updated

- `quality_loop.py` exists, tested, flags empty (v5.3)
- `prompt_context/builders.py` exists, 12 builders (v5.3)
- Model version bumps in production (v5.3)
- `BASE_URL` env-var pattern landed (v5.2)
- `backfill→world_class_enrich` rewire (v5.2)
- Sanity gate freshness check (v5.2)
- All 15 migrations applied in CI (v5.1)
- **🆕 `cfb_calendar.py` module + 8 label-fix PR batches landed**
- **🆕 `offseason_fallback.py` rewrite — no `source_kind='unverified'` in production**
- **🆕 `portal_moves` persistence adapter writing real rows**
- **🆕 Coaching changes RSS adapter populating `coaching_changes`**
- **🆕 `archive_retro_daily.yml` workflow running daily**

---

## Part 8 · Updated Sprint Roadmap

Sprint roadmap unchanged in length (still 17 weeks). Offseason surfaces slot into existing sprints; nothing is delayed.

| Week | Sprint | v5.3 deliverable | **v5.4 additions** |
|---|---|---|---|
| 0 | v5-0 Procurement | (unchanged) | (unchanged) |
| 1 | v5-1 Foundation | Migrations, quality_loop, prompt_context, BASE_URL, workflow chaining | **+ cfb_calendar.py + 8 label-fix PRs + offseason_fallback rewrite + 3 data adapters + 5 new workflows + S1 (countdown)** |
| 2 | v5-2 Editorial gen | Edition cover, Wire Sonnet, Headline Doctor | **+ S3 Portal Heat + S5 Today in CFB History** (both use the retro selector from v5-1) |
| 3 | v5-3 Reactions + storylines | Daily/Heisman/Mailbag/Reactions → Pattern C | **+ S2 Cohort Ledger + S4 Recruit Watch** |
| 4 | v5-4 Mailbag + Chronicle | Storylines + Chronicle Pattern E | **+ S7 Saturdays Past + S12 Dead Zone Mailbag** |
| 5 | v5-5 Heisman + Canon | Canon Pattern C/D, Pulse themes Stage 2, Best Calls | **+ S9 Preseason Heisman Watch v1 + S8 Media Days Live scaffolding** |
| 6 | v5-6a R2 + Pillow OG | Share cards, OG wiring | **+ S6 Schedule Deep Dive generator (renderer ready, fires Aug 1)** |
| 7 | v5-6b Visual assets | visual_assets helper, typographic helmet stripes | (unchanged) |
| 8 | v5-7 Imagery + auto-throttle | Pillow composition, auto-throttle | **Tentpole writer for "100 Days" (May 21) — but we're past that. Reframe: tentpole writers ready for Jul 10 "50 Days"** |
| 9 | v5-8 Zero-Touch UI | Pattern D on Edition cover, GitHub digest workflows | **+ S8 Media Days Live goes operational (Jul 14 SEC kick)** |
| 10 | v5-9 Programs + Sources | 17 bespoke per-program modules | **+ Watchlist tracker (post-Big Ten Media Days Jul 21)** |
| 11 | v5-10a Players | Player position + archetype surfaces | **+ S10 Fall Camp Tracker scaffolding (goes live Aug 5)** |
| 12 | v5-10b Rivalries | Tier-1 rivalry detail pages | **+ S11 Offseason Receipts Court v1 + Preseason AP reactions (Jul 28)** |
| 13 | v5-10c Phases + conferences | Phase landings + conference landings | **+ Schedule Deep Dive daily output Aug 1 + Camp Tracker live Aug 5** |
| 14 | v5-10d Reddit archive | Arctic Shift archive surfaces | **+ S9 Heisman Watch v2 (post-watchlist update)** |
| 15-16 | v5-11 Polish + verify | Bug fixes, performance, voice-validator regression | **+ Week 0 Preview edition (Aug 20) + "10 Days" tentpole (Aug 19)** |
| 17 | v5-12 Launch | Methodology updates, observability, retro | **+ Week 1 Hero Edition (Aug 29) — full transition. Postmortem: which offseason surfaces had highest stickiness** |

**Calendar alignment:** The 17-sprint plan starting Sprint v5-0 next Monday (May 18) hits Sprint v5-9 in the second week of July — right when SEC Media Days starts. Sprint v5-10a ships fall camp tracker in early August. Sprint v5-12 ships during the actual Week 1 transition (Aug 29). This is the optimal calendar alignment for shipping value as it's needed.

**If Sprint v5-0 doesn't start until later (e.g., May 25):** Push every milestone +1 week. Still hits Media Days Live for Big Ten Media Days (Jul 27); still hits Camp Tracker before Aug 5; still hits Week 1 Edition Aug 29 — but with less prep buffer.

**If Sprint v5-0 starts immediately (May 18 Monday):** Best case. Sprint v5-1 work outlined in Part 7 begins next week. By "100 Days" milestone May 21 we'd have the countdown surface live (S1 lands Sprint v5-1).

---

## Part 9 · Decision Log

### Decisions locked in v5.4

1. **Hybrid labeling convention.** Phase label for headers, `(N days to kickoff)` parenthetical for eyebrows, human dates in body copy. ISO weeks stay data-layer-only.
2. **`cfb_calendar.py` is single source of truth.** All 11 user-facing "Week N" hits route through `cfb_week_label()` after Sprint v5-1.
3. **Reject "Offseason Week N" convention.** Phase labels read more naturally; existing `_MONTH_TO_PHASE` does the same job better.
4. **Day-of-week cadence anchors offseason rhythm.** Tue/Wed/Thu/Sat/Sun all have specific anchor surfaces. Reader can predict the day's content without thinking.
5. **One renderer, many outputs.** Share-card SVG renderer (R1 in v5.3) powers S1, S2, S5, S9, tentpoles. Build once, parameterize liberally.
6. **`offseason_fallback.py` ships real retro data, not fake transactions.** Day 1 of Sprint v5-1. Data-integrity issue, not aesthetic preference.
7. **3 must-have data adapters in Sprint v5-1.** Portal moves persistence, coaching changes RSS, archive_threads daily retro. All unblock multiple v5.3 prompt-context manifests.
8. **5 new workflows.** Lightweight, fit in GitHub Actions free-tier (public repo). All 5 ship Sprint v5-1.
9. **9 marquee tentpole dates get Pattern D treatment.** Edition cover essay's adversarial-critique loop extends to every named tentpole — same per-call cost, ~9× more occurrences = ~$30 → $270/yr (still inside Agent SDK credit).
10. **S5 (Today in CFB History) is the safety net.** Every offseason day has at least one new dated artifact above the fold. S5 is date-anchored against tables that never run out of material.

### Open items requiring user judgment (not blockers)

1. **NIL deal tracker (skipped).** v5.4 investigators identified On3 NIL data as a possible feed but paywalled; deferred to post-launch. Fan-engagement uncertain.
2. **Depth chart tracking (skipped).** Too brittle for offseason; revisit at fall camp via athletics-site scrapes.
3. **Coaching changes data source.** v5.4 specs Footballscoop RSS + 247Sports scrape. Alternative: manual editorial via `data/offseason/2026/coaching.json` only (less work, less complete). Recommend: ship the RSS adapter; manual stays as fallback.
4. **`spring_events` table activation.** Schema exists but unused. Could power "Spring Practice Recap" surface in March-May of future years. Defer to v5.5+.
5. **Media days transcripts source.** Conferences broadcast publicly; transcripts via FTP/scrape. Investigator 3 flagged as "high editorial value in July." Recommend: ship S8 with quote-of-the-day from `source_observations` (existing pipeline); add transcript scrape post-launch if engagement supports it.
6. **Preseason watch lists data structure.** Could piggyback on `player_honors` table with `award_phase='preseason_watch'`, or new `watchlists` table. Recommend: piggyback. Less migration surface.

### What v5.4 does NOT change from v5.3

- 37-surface quality matrix (v5.3 Part 1)
- 5 critique loop patterns + 5 critic roles (v5.3 Part 3)
- 12 proprietary data manifests (v5.3 Part 4)
- $0 incremental cash cost
- 17-week roadmap
- Workflow chaining + self-healing (v5.2 Part 4)
- No custom domain, no commissions, no Resend (v5.2)
- Repo public posture

### Updated canonical reading order

| Doc | Read for |
|---|---|
| v1–v3 | Problem inventory, architecture, visual identity |
| **v4** | Build spec (atoms, voice stylebook, mobile, motion, share cards, governance) |
| v5 | Bespokeness + automation (per-program, per-player, per-rivalry) |
| v5.1 Review | Verification corrections |
| **v5.2** | Architectural reset ($0 cost, no domain, no commissions, workflow chaining) |
| **v5.3** | Quality maximization (37-surface matrix, quality_loop, proprietary data manifests) |
| **v5.4 (this doc)** | **Offseason engine + calendar labeling fix** |

**Single-source-of-truth updates from v5.3:**

| Dimension | Canonical |
|---|---|
| Calendar / kickoff labeling | **v5.4 Part 2 (`cfb_calendar.py`, hybrid convention)** |
| Offseason content cadence | **v5.4 Part 3 (8-phase calendar + 7-day rhythm + 9 tentpoles)** |
| Offseason new surfaces | **v5.4 Part 4 (S1-S12 with data manifests)** |
| Must-have data adapters | **v5.4 Part 5 (portal_moves persistence, coaching RSS, archive_threads retro)** |
| Workflow cadence adjustments | **v5.4 Part 6** |
| Sprint v5-1 Day 1-2 brief | **v5.4 Part 7** |

---

## Closing summary

**v5.4 turns 14 weeks of dead offseason into 14 weeks of compounding content engagement at zero incremental cost.**

Three forces make this work:

1. **Day-of-week anchors train return-visits.** Tuesday Portal Heat / Wednesday Recruit Watch / Thursday Heisman Watch / Saturday's Past — readers can predict the day's content. Habit becomes engagement.
2. **Live-feel without games.** Countdown (S1), portal churn (S3), recruit velocity (S4), cohort transitions (S2) all visibly change daily. Site always has fresh content above the fold.
3. **Backward inventory is bottomless.** `team_chronicle_observations` + `archive_threads` (Arctic Shift 2014-2025) + `historical_seasons_summary` provide unlimited "Today in CFB History" + "Saturdays Past" + anniversary retros. Never empty.

**Three forces that distinguish v5.4 from "make more content":**

1. **It's data-integrity-first.** The `offseason_fallback.py` fake-news bug ships before any new surface. Trust the data before scaling on it.
2. **It's calendar-aware.** The hybrid labeling convention (phase + parenthetical days-to-kickoff) reads naturally in May AND November. No "Week 31" anywhere.
3. **It's renderer-shared.** Share-card SVG renderer powers S1, S2, S5, S9, and 9 tentpoles. Build once, ship many times.

**Immediate action (still):** Trigger `world_class_enrich.yml` from GitHub Actions tab. The post-backfill 2014-2025 player-context data is what powers S5/S6/S9/S11 manifests.

**First Sprint v5-1 action:** Day 1 morning — land 5 patches (v5.3's 4 + offseason_fallback rewrite). Day 1 afternoon — verify production has zero `source_kind='unverified'` rows. Day 2 — ship `cfb_calendar.py` + 8 label-fix batches. By end of week, the site looks calendar-aware and ships real offseason content. Three months later, we're at Week 1 of the season.
