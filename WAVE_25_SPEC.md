# Wave 25 — Player Page 2026 Offseason Posture Spec

**Status:** Locked spec, ready for implementation.
**Generated:** 2026-05-27
**Research provenance:** Multi-AI probe (Claude-sonnet × 2, Codex × 2, Perplexity) +
codex live web fetches against ESPN, On3, NFL.com, team athletics pages.
**Source recency target:** as fresh as 2026-05-27 (met for codex-fetched URLs in §8).

---

## TL;DR

Player pages currently lead with 2024 retrospective stats. In mid-May 2026 — eight
weeks post-2026 NFL Draft, six weeks post-portal close, two weeks post-spring
practice depth charts — that framing is wrong. **Three new modules + one
re-labeling pass** fix it:

1. **Player Status Strip** (all archetypes) — top-of-page identity bar that answers
   "what's this player's deal right now?" in under 3 seconds.
2. **2026 Outlook** (returning players only) — depth chart status + OL/WR/OC
   continuity + preseason award watch.
3. **Where They Ended Up** (NFL departures + CFB transfers) — destination card +
   role projection + legacy link back to college stats.
4. **Re-labeling pass** — rename "Current Season Production" → archetype-appropriate
   label via a new `season_context_label()` function.

Implementation gates on building a **`player_current_status_view`** that resolves
every player to one of 11 status codes with provenance, manual override, and
verification flags.

---

## CRITICAL: The example player list in the original request is stale

The codex probe verified live 2026 sources and surfaced these corrections:

| Player | Original Spec | Actual (May 27, 2026) | Verified Source |
|---|---|---|---|
| Arch Manning | Type A returning | ✅ Type A returning, Texas QB1 2026 | texaslonghorns.com roster, ESPN player page |
| DJ Lagway | Type A returning | ✅ Likely Type A | floridagators.com roster |
| Drew Allar | Type A returning | ❌ **Type B drafted** — Steelers Rd 3, 2026 Draft | psu.edu 2026 draft recap |
| Jeremiah Smith | Type A returning | ✅ Type A, Ohio State WR 2026 | ohiostatebuckeyes.com roster |
| Carson Beck | Type C transferred (UGA→Miami) | ❌ **Type B drafted** — Arizona #65 overall, 2026 Draft | nfl.com/news |
| Fernando Mendoza | Type C transferred (Cal→Indiana) | ❌ **Type B** (NFL per ESPN Feb 9 2026 Heisman piece) | ESPN |
| Cam Ward | Type B 2026 #1 Tennessee | ⚠️ Type B but **2025 Draft** (#1 overall) — by May 2026 he's a 2nd-year NFL player | nfl.com, Titans bio |
| Shedeur Sanders | Type B drafted | ⚠️ **2025 Draft** Cleveland Browns #144 | clevelandbrowns.com |
| Dillon Gabriel | Type B drafted | ⚠️ **2025 Draft** Cleveland Browns #94 (2nd-yr NFL by May 2026) | clevelandbrowns.com |
| Ashton Jeanty | Type B drafted | ⚠️ **2025 Draft** Las Vegas Raiders #6 (2nd-yr NFL) | raiders.com |

**Implication:** The "two-stage Type B" — players drafted 2025 vs. drafted 2026 —
is a real edge case. Both need "Where They Ended Up" cards but with different
date framing ("Drafted by ... — entering 2nd NFL season" vs. "Drafted by ... —
2026 rookie season").

**Lesson for the data layer:** Never hard-code archetypes from editorial
assumptions. Derive every status from queryable DB state with a `status_as_of`
timestamp.

---

## §1. Executive Summary — What Fans Get

1. **A 3-second answer** — every player page opens with a Status Strip that says
   "Returning Starter at Texas," "Drafted #65 by Arizona," "Transferred to
   Indiana," or "1971–1974 Alabama Alumni" depending on archetype.
2. **A forward-looking outlook for Type A** — 2026 starter status, OL/WR/OC
   continuity grades, preseason Heisman/award watch — drawn from the
   already-shipping `team_preview_*` tables.
3. **A destination card for Type B/C** — NFL team logo + round + pick + role
   projection (for the drafted) or origin→destination + role projection (for the
   transferred), with a "View college career stats" link to demote the 2024
   retrospective surfaces.

---

## §2. Data Audit — Have / Need by Module

### §2.1 What we have RIGHT NOW (verified via local DB queries this session)

| Table | Rows | Useful For |
|---|---|---|
| `players` | many | Identity, name, position |
| `player_season_stats` | 426,725 | Career stats; max season = 2024 |
| `player_game_stats` | 1,304,322 | Game-by-game; max season = 2024 |
| `player_nfl_draft` | 2,316 (2018-2025) | NFL Draft outcomes — **missing 2026 draft** |
| `player_recruiting_profiles` | 20,392 | Stars, ratings, hometown |
| `player_draft_projection` | 0 | Schema exists, empty |
| `player_signature_story` | 500 (Wave 8) | LLM bios |
| `player_narrative_arc` | 91 (Wave 15) | LLM 3-act arcs |
| `player_pbp_metrics_season` | populated | EPA/CPOE/aDOT from PBP (Wave 10) |
| `team_preview_core` | populated | Team-level 2026 previews (parallel work stream) |
| `team_preview_roster_reload` | populated | OL/WR/skill continuity at team level |
| `team_preview_bowl_ledger` | populated | Bowl history per team |
| `team_preview_claim_cache` | populated | Validated 2026 claims (126/127 teams) |
| `team_seasons` | 2,272 | head_coach, oc, dc per (team, season) |
| `games` | many | W/L records |
| `conversation_documents` | 9,322 | Reddit/news offseason chatter, tagged season=2025 |
| `player_week_conversation_features` | 571 (Wave 7) | Player-FI mood data |

### §2.2 What we NEED to ingest (Wave 25 dependencies)

| Gap | Required For | Smallest Viable Source |
|---|---|---|
| 2026 NFL Draft picks (Allar, Beck, Mendoza, etc.) | Module 3 Type B | CFBD `/draft/picks?year=2026`, or manual scrape of nfl.com |
| 2026 transfer portal final outcomes | Module 3 Type C + status resolver | CFBD `/transfer-portal?year=2026`, manual fallback for top-100 |
| 2026 roster per FBS team | Status resolver (Type A vs B vs C vs D) | CFBD `/roster?year=2026` |
| 2026 depth chart / starter flag | Module 2 starter status | Team athletic site scrape or manual seed for top 50 programs |
| 2026 OC continuity flag per team | Module 2 supporting cast | Already in `team_seasons` if 2026 row is populated — verify |
| Preseason 2026 award watchlists | Module 2 award watch | Manual seed (Heisman, Maxwell, Davey, Doak, Biletnikoff, Butkus, etc.) |
| Player → 2026 status code | All three modules | Derived view + manual override table |

### §2.3 CFBD `/returning` endpoint feasibility

**Team-level only.** Returns `percentPPA`, `offensePPAPercentage`,
`defensePPAPercentage`, `quarterbackPPAPercentage`, `runningBackPPAPercentage`,
`receiverPPAPercentage`. Does NOT enumerate which specific players make up the
returning production.

**Player-level attribution requires joining**:
- 2025 box-score volume per player per team
- 2026 roster (who's still on roster)
- Filter: returning_player.season_2025_stats > threshold

This is doable but adds an ingest step. For Wave 25 v1, use team-level
returning-PPA as a context number in Module 2; defer player-level attribution
to Wave 26.

---

## §3. Module 1: Player Status Strip

### §3.1 Purpose

Top-of-page identity bar that immediately classifies the player into one of 11
status codes. Replaces the current QB Fingerprint hero as the first surface on
the page during offseason; QB Fingerprint shifts to below it (or stays primary
during in-season).

### §3.2 Status taxonomy (11 codes)

```
RETURNING_2026          — on a 2026 college roster, same school as 2025
TRANSFERRED_COLLEGE     — on a 2026 college roster, different school than 2025
NFL_DRAFTED_2026        — selected in 2026 NFL Draft (rookie season approaching)
NFL_DRAFTED_PRIOR       — drafted in 2024 or 2025 Draft (2nd+ NFL season)
NFL_UDFA                — signed as undrafted free agent
PORTAL_OPEN             — entered portal, no commitment yet
PORTAL_WITHDREW         — entered portal then exited without transferring
EXHAUSTED_ELIGIBILITY   — college career complete, did not pursue NFL
MEDICAL_RETIREMENT      — career ended via medical hardship
HISTORICAL_ALUM         — past alum, ≥2 years removed from college career
HS_RECRUIT_ONLY         — committed but never enrolled (rare; legal sensitivity)
```

### §3.3 Resolution order (first match wins)

1. NFL drafted ≤ current_year → `NFL_DRAFTED_2026` or `NFL_DRAFTED_PRIOR`
2. NFL UDFA signed (per UDFA tracker) → `NFL_UDFA`
3. Active 2026 college roster + same team as 2025 → `RETURNING_2026`
4. Active 2026 college roster + different team than 2025 → `TRANSFERRED_COLLEGE`
5. In portal with no destination → `PORTAL_OPEN`
6. Was in portal + returned to original school → `PORTAL_WITHDREW`
7. No 2026 roster + ≤1 year removed → `EXHAUSTED_ELIGIBILITY`
8. No 2026 roster + ≥2 years removed → `HISTORICAL_ALUM`
9. Medical override flag → `MEDICAL_RETIREMENT`
10. Recruiting profile only, no enrollment → `HS_RECRUIT_ONLY`

### §3.4 DB resolution (new view + override table)

```sql
-- New override table for editorial corrections
CREATE TABLE player_status_override (
    player_id INTEGER PRIMARY KEY,
    status_code TEXT NOT NULL,
    status_label_text TEXT,
    set_by TEXT NOT NULL,
    set_at TEXT NOT NULL,
    notes TEXT
);

-- New view that consolidates status resolution
CREATE VIEW player_current_status_view AS
WITH nfl_2026 AS (
    SELECT player_id, draft_year, round, pick, overall, nfl_team, nfl_team_abbr
    FROM player_nfl_draft
    WHERE draft_year = 2026
),
nfl_prior AS (
    SELECT player_id, draft_year, round, pick, overall, nfl_team, nfl_team_abbr
    FROM player_nfl_draft
    WHERE draft_year < 2026
    ORDER BY draft_year DESC
),
roster_2026 AS (
    -- TODO: ingest 2026 rosters; placeholder until then
    SELECT player_id, team_id, team_name
    FROM player_season_stats  -- fallback while 2026 roster not ingested
    WHERE season_year = 2026
    GROUP BY player_id
),
last_team AS (
    SELECT player_id, team_id, team_name, MAX(season_year) AS last_year
    FROM player_season_stats
    GROUP BY player_id
)
SELECT
    p.player_id,
    p.full_name,
    COALESCE(o.status_code,
        CASE
            WHEN nfl26.player_id IS NOT NULL THEN 'NFL_DRAFTED_2026'
            WHEN nfl_pr.player_id IS NOT NULL THEN 'NFL_DRAFTED_PRIOR'
            WHEN r26.team_id IS NOT NULL AND lt.team_id = r26.team_id THEN 'RETURNING_2026'
            WHEN r26.team_id IS NOT NULL AND lt.team_id <> r26.team_id THEN 'TRANSFERRED_COLLEGE'
            WHEN lt.last_year >= 2024 THEN 'EXHAUSTED_ELIGIBILITY'
            ELSE 'HISTORICAL_ALUM'
        END
    ) AS status_code,
    o.status_label_text AS override_label,
    lt.team_name AS previous_team,
    r26.team_name AS current_team,
    COALESCE(nfl26.nfl_team, nfl_pr.nfl_team) AS nfl_team,
    COALESCE(nfl26.round, nfl_pr.round) AS draft_round,
    COALESCE(nfl26.pick, nfl_pr.pick) AS draft_pick,
    COALESCE(nfl26.overall, nfl_pr.overall) AS draft_overall,
    COALESCE(nfl26.draft_year, nfl_pr.draft_year) AS draft_year,
    o.set_at AS status_as_of
FROM players p
LEFT JOIN player_status_override o ON o.player_id = p.player_id
LEFT JOIN nfl_2026 nfl26 ON nfl26.player_id = p.player_id
LEFT JOIN nfl_prior nfl_pr ON nfl_pr.player_id = p.player_id
LEFT JOIN roster_2026 r26 ON r26.player_id = p.player_id
LEFT JOIN last_team lt ON lt.player_id = p.player_id;
```

### §3.5 Render-per-archetype

| Status code | Strip label | Detail line | Accent |
|---|---|---|---|
| `RETURNING_2026` | "Returning for 2026" | "{team} {position} · {starter\|backup\|depth}" | `--belief-high` (green) |
| `TRANSFERRED_COLLEGE` | "Transferred for 2026" | "from {previous_team} → to {current_team}" | `--accolade-gold-base` |
| `NFL_DRAFTED_2026` | "2026 NFL Draft" | "Rd {round}, Pick {pick} · {nfl_team}" | navy `oklch(0.32 0.18 260)` |
| `NFL_DRAFTED_PRIOR` | "Now in the NFL" | "{nfl_team} · drafted {year}, Rd {round} #{overall}" | navy |
| `NFL_UDFA` | "Signed as UDFA" | "{nfl_team} · 2026 free agent" | navy-dim |
| `PORTAL_OPEN` | "In transfer portal" | "destination TBD · last at {previous_team}" | amber `oklch(0.65 0.18 75)` |
| `PORTAL_WITHDREW` | "Withdrew from portal" | "Returning to {previous_team} for 2026" | green |
| `EXHAUSTED_ELIGIBILITY` | "College career complete" | "{previous_team} · {final_year}" | `--text-quiet` |
| `MEDICAL_RETIREMENT` | "Career-ending injury" | "{previous_team} · {final_year}" | `--text-quiet` |
| `HISTORICAL_ALUM` | "{years} {team}" | "Career alumnus" | `--text-quiet` |
| `HS_RECRUIT_ONLY` | "Committed — never enrolled" | "Class of {recruit_year}" | `--text-quiet` |

### §3.6 HTML structure

```html
<section class="player-status-strip player-status-strip--{archetype_class}"
         data-status-code="{status_code}"
         aria-label="2026 player status">
  <div class="player-status-strip__badge-wrap">
    <span class="player-status-strip__badge">{strip_label}</span>
  </div>
  <div class="player-status-strip__detail-wrap">
    <span class="player-status-strip__detail">{detail_line}</span>
  </div>
  <div class="player-status-strip__as-of">
    <time datetime="{status_as_of}">As of {status_as_of_display}</time>
  </div>
</section>
```

### §3.7 Mobile

Stack: badge top, detail middle, "as of" bottom. At <375px collapse "as of" into
a tap-to-reveal tooltip on the badge.

### §3.8 Season-phase gate

Strip renders ALWAYS — both in-season and offseason. In-season the badge text
flips to current-game framing ("Active · QB" vs "Returning starter for 2026").
Use existing `is_offseason()` helper.

### §3.9 Edge branches

- Override row present → strip uses `override_label` and accent of the override's
  status_code.
- Status unknown / no rows match → render `HISTORICAL_ALUM` defensive fallback
  with "Status pending verification" amber pill.
- 2026 draft ingest not yet run → `NFL_DRAFTED_2026` won't match; falls through
  to `EXHAUSTED_ELIGIBILITY` until draft ingest backfills. NOT a render bug;
  document in ops runbook.
- Multiple drafts for same player (NFL re-entry) → take latest `draft_year`.
- 2026 roster ingest pending → `RETURNING_2026` / `TRANSFERRED_COLLEGE` may
  under-fire. Manual override is the escape hatch for top-100 marquee players.

---

## §4. Module 2: 2026 Outlook (Type A only)

### §4.1 Purpose

Forward-looking 3-card row that answers "what should I expect in 2026?" for any
player resolving to `RETURNING_2026`. Sits just below the Status Strip + Hero,
ABOVE the 2024 retrospective stat ribbon.

### §4.2 Three cells

**Cell 1 — 2026 Depth Chart**
- Primary: "Projected starter" / "Returning starter" / "Camp competition" /
  "Backup" / "Depth"
- Sub: position + team name
- Source: new `player_depth_chart_2026` table (manual-seeded for top 100,
  inferred for rest from `player_season_stats` snap volume continuity)

**Cell 2 — Supporting Cast Continuity**
- Line 1 OL: "{X}/5 OL starters return" pulled from `team_preview_roster_reload`
- Line 2 Skill: "{returning top WR name} returning" or "OL/WR continuity Strong/Mixed/Rebuild"
- Line 3 OC: "OC {name} ({returning|new})" from `team_seasons` 2025→2026 diff
- Fallback: team-level returning PPA from CFBD `/returning` if specific rows
  missing

**Cell 3 — Preseason Award Watch**
- 1–3 award badges from `player_award_watch_2026` (new seed table)
- Awards by position:
  - QB: Heisman, Maxwell, Davey O'Brien, Manning
  - RB: Heisman, Doak Walker, Maxwell
  - WR: Heisman (rare but valid for Jeremiah Smith archetype), Biletnikoff
  - TE: Mackey
  - DL/Edge: Nagurski, Bednarik, Outland
  - LB: Butkus, Bednarik
  - DB: Jim Thorpe, Nagurski
- Falls back to "No 2026 watch lists yet" if empty (don't suppress; explain)

### §4.3 DB queries

```sql
-- Depth chart
SELECT pdc.starter_status,    -- 'projected_starter'|'returning_starter'|'co_starter'|'backup'|'depth'
       pdc.position_group,
       pdc.confidence,        -- 'confirmed'|'projected'
       pdc.as_of
FROM player_depth_chart_2026 pdc
WHERE pdc.player_id = :player_id;

-- Supporting cast (joined to team_preview_roster_reload from parallel work stream)
SELECT trr.ol_returners_count,
       trr.ol_returners_total,
       trr.top_wr_returning_player_id,
       trr.top_wr_returning_name,
       trr.skill_continuity_grade,   -- 'Strong'|'Mixed'|'Rebuild'
       ts26.offensive_coordinator    AS oc_2026,
       ts25.offensive_coordinator    AS oc_2025,
       (ts26.offensive_coordinator = ts25.offensive_coordinator) AS oc_returning,
       tret.offense_ppa_percentage,
       tret.quarterback_ppa_percentage
FROM team_preview_roster_reload trr
LEFT JOIN team_seasons ts26 ON ts26.team_id = trr.team_id AND ts26.season_year = 2026
LEFT JOIN team_seasons ts25 ON ts25.team_id = trr.team_id AND ts25.season_year = 2025
LEFT JOIN team_returning_production tret ON tret.team_id = trr.team_id AND tret.season = 2026
WHERE trr.team_id = :current_team_id;

-- Award watch
SELECT paw.award_slug,        -- 'heisman','davey_obrien','butkus', etc.
       paw.list_type,         -- 'odds_top10'|'watchlist'|'media_predict'
       paw.position_rank,
       paw.source,
       paw.as_of
FROM player_award_watch_2026 paw
WHERE paw.player_id = :player_id
ORDER BY paw.priority ASC
LIMIT 3;
```

### §4.4 HTML structure

```html
<section class="outlook-2026" data-module="outlook-2026" aria-label="2026 season outlook">
  <header class="outlook-2026__head">
    <p class="outlook-2026__eyebrow">2026 Outlook</p>
    <p class="outlook-2026__lede">{starter_lede}</p>
  </header>
  <div class="outlook-2026__cells">
    <div class="outlook-2026__cell outlook-2026__cell--depth">
      <p class="outlook-2026__cell-label">Depth chart</p>
      <p class="outlook-2026__cell-value">{starter_status_label}</p>
      <p class="outlook-2026__cell-sub">{position} · {team}</p>
    </div>
    <div class="outlook-2026__cell outlook-2026__cell--cast">
      <p class="outlook-2026__cell-label">Returning around him</p>
      <ul class="outlook-2026__cast-list">
        <li>{ol_returners_count}/5 OL starters back</li>
        <li>Top WR: {top_wr_name} returning</li>
        <li>OC: {oc_name} ({"returning" if oc_returning else "new"})</li>
      </ul>
    </div>
    <div class="outlook-2026__cell outlook-2026__cell--awards">
      <p class="outlook-2026__cell-label">2026 watch</p>
      <ul class="outlook-2026__award-list">
        {for award in awards}
        <li class="outlook-2026__award outlook-2026__award--{award.slug}">
          {award.display_name}
        </li>
        {endfor}
      </ul>
    </div>
  </div>
  <p class="outlook-2026__team-context">
    {team} returns {offense_ppa_pct}% of 2025 offensive production
    (rank {return_rank} nationally).
  </p>
</section>
```

### §4.5 Edge branches

- Missing `team_preview_roster_reload` row → omit cast cell, show team-level
  CFBD `/returning` percentage in a single line.
- No award watch → "No preseason watch yet" in grey, NOT suppression.
- Starter status = 'co_starter' or 'projected' → amber accent (not green),
  copy reads "Position battle" or "Projected starter — camp competition."
- OL data = 5/5 returning → gold "Full unit returning" pill.
- OL data = 0/5 → red "Rebuilt line" warning pill.
- Spring depth chart not yet published → starter_status defaults to
  `projected_starter`, NOT `returning_starter`; copy uses "Expected to start."
- Jeremiah Smith Heisman watch as WR → award badges must support WR Heisman;
  do NOT suppress as edge case; this is feature, not bug.

### §4.6 Mobile

Cells stack vertically. Award cell collapses to 2 badges max. Team-context
trailer hidden at <375px (secondary).

---

## §5. Module 3: Where They Ended Up (Type B + C)

### §5.1 Two variants

**Variant 5A — NFL destination** (status: `NFL_DRAFTED_2026`, `NFL_DRAFTED_PRIOR`,
`NFL_UDFA`)

**Variant 5B — College transfer destination** (status: `TRANSFERRED_COLLEGE`,
`PORTAL_OPEN`)

### §5.2 Variant 5A render

```html
<section class="where-ended-up where-ended-up--nfl"
         data-module="where-ended-up"
         data-variant="nfl">
  <header class="where-ended-up__head">
    <p class="where-ended-up__eyebrow">Where He Ended Up</p>
    <h2 class="where-ended-up__heading">{nfl_team}</h2>
  </header>
  <div class="where-ended-up__pick">
    <span class="where-ended-up__pick-overall">#{overall} overall</span>
    <span class="where-ended-up__pick-round">Rd. {round}, Pick {pick}</span>
    <span class="where-ended-up__pick-year">{draft_year} NFL Draft</span>
  </div>
  <div class="where-ended-up__projection">
    <p class="where-ended-up__projection-label">Role projection</p>
    <p class="where-ended-up__projection-text">{role_projection_text}</p>
  </div>
  <a class="where-ended-up__legacy-link" href="#college-career">
    View college career stats ↓
  </a>
</section>
```

For `NFL_DRAFTED_PRIOR` (Gabriel/Sanders/Ward/Jeanty): subtitle "Entering 2nd
NFL season" instead of "2026 rookie season."

### §5.3 Variant 5B render

```html
<section class="where-ended-up where-ended-up--transfer"
         data-module="where-ended-up"
         data-variant="transfer">
  <header class="where-ended-up__head">
    <p class="where-ended-up__eyebrow">Transfer Destination</p>
  </header>
  <div class="where-ended-up__transfer-flow">
    <div class="where-ended-up__from">
      <span class="where-ended-up__team-name">{previous_team}</span>
      <span class="where-ended-up__from-tag">2025</span>
    </div>
    <div class="where-ended-up__arrow" aria-hidden="true">→</div>
    <div class="where-ended-up__to">
      <span class="where-ended-up__team-name">{current_team}</span>
      <span class="where-ended-up__to-tag">2026</span>
    </div>
  </div>
  <div class="where-ended-up__projection">
    <p class="where-ended-up__projection-label">Projected role</p>
    <p class="where-ended-up__projection-text">{transfer_role_projection}</p>
  </div>
  <a class="where-ended-up__legacy-link" href="#college-career">
    View career at {previous_team} ↓
  </a>
</section>
```

For `PORTAL_OPEN`: omit the "to" half, show "Destination TBD" with question-mark
glyph.

### §5.4 Edge branches

- Draft pick not yet ingested → use override label "Selected in 2026 Draft (pick
  TBD)" or fall through to UDFA template if confidence high.
- UDFA with unknown team → "Available · undrafted" amber pill.
- Player drafted AND was in portal same window → drafted wins (resolution rule
  §3.3.1). Portal record stays for historical context, not for status.
- Transfer with `eligibility_status = 'waiver_pending'` → amber pill
  "Eligibility waiver pending" below role projection.
- Type B "drafted 2025" (Gabriel/Sanders/Ward/Jeanty by May 2026) → subtitle
  reads "{nfl_team} · entering 2nd NFL season" not "2026 rookie season."
- Logo URL 404 → fallback to colored block with team initials.

### §5.5 Mobile

Variant 5A: NFL team name big, pick chip below, projection collapses to "Show
projection" tap target.
Variant 5B: "from → to" flow stays horizontal (small logos), projection below.

---

## §6. Re-labeling pass

### §6.1 New function

```python
def season_context_label(
    status_code: str,
    last_team_name: str | None,
    last_season_year: int | None,
    current_team_name: str | None,
    current_date: date | None = None,
) -> str:
    """Return the section-header prefix for the existing 'Current Season
    Production' surface, archetype-aware.

    Examples:
      RETURNING_2026     -> '2025 Season · last completed'
      TRANSFERRED_COLLEGE-> '2025 at {last_team} · final season there'
      NFL_DRAFTED_2026   -> '2025 · final college season'
      NFL_DRAFTED_PRIOR  -> '2024 · final college season'
      EXHAUSTED_ELIGIBILITY -> 'College career stats'
      HISTORICAL_ALUM    -> 'College career stats'
      PORTAL_OPEN        -> '2025 at {last_team} · last season before portal'
    """
```

### §6.2 Surfaces to relabel

- "Current Season Production" h2 → archetype-specific
- "Career Stats" tab → "{College Career}" (Type B) | "{Career}" (Type A) |
  "{Years} Career" (Type D)
- "Game Log" subtitle → "2024 game-by-game" or "Final season game log"
- Page `<title>` tag for SEO → archetype-aware suffix:
  - Type A: "{name} | {team} {position} · 2026 Outlook"
  - Type B: "{name} | {nfl_team} · NFL Draft {year}"
  - Type C: "{name} | {team} {position} · Transfer for 2026"
  - Type D: "{name} | {final_team} alum"

---

## §7. Vocabulary glossary (locked)

| Concept | Preferred | Avoid | Rationale |
|---|---|---|---|
| Same school 2026 | **Returning starter** / **Returning** | "Active", "Still here" | Industry standard (247/ESPN) |
| Same school, depth TBD | **Projected starter** / **Expected starter** | "Likely" | Signals analytical uncertainty |
| Same school, position battle | **Camp competition** | "Possible starter" | Honest about uncertainty |
| Same school, withdrew from draft | **Returning — withdrew from draft** | "Changed mind" | Neutral, respects player agency |
| NFL drafted current year | **Drafted — Rd {n}, Pick {p}, {team}** | "Gone pro" | Specific beats vague |
| NFL drafted prior year | **{Team} · NFL · {N}-year veteran** or **drafted {year}** | "Former" | Captures NFL tenure |
| UDFA | **Signed as UDFA — {team}** | "Went undrafted" | UDFA implies signing; undrafted alone implies failure |
| Portal, no destination | **In the transfer portal** | "Available", "Exploring options" | Matches official portal vocabulary |
| Portal, committed, not enrolled | **Committed — pending enrollment** | "Transferring to" | Enrollment vs commitment differ legally |
| Transfer, enrolled | **Transferred to {team}** | "Now at" | "Transferred to" is standard |
| Medical | **Medical redshirt — {year}** or **Career-ending injury** | "Injured" | Avoid medical detail; HIPAA-adjacent |
| Career complete | **College career complete** or **{years} {team}** | "Retired" | Neutral |
| Last college season label | **Final college season** (Type B/C) / **2025 season · last completed** (Type A in May 2026) | "2024 stats" | Date-aware, archetype-aware |

---

## §8. Sources verified (codex live web fetches, 2026-05-27)

- ESPN Arch Manning: https://www.espn.com/college-football/player/_/id/4870906/arch-manning
- ESPN Cam Ward (NFL): https://www.espn.com/nfl/player/_/id/4688380/cam-ward
- On3 Arch Manning: https://www.on3.com/rivals/arch-manning-7353/
- On3 Carson Beck: https://www.on3.com/rivals/carson-beck-18711/
- ESPN 2026 returning production (Mar 23, 2026):
  https://www.espn.com/college-football/story/_/id/48259759/college-football-returning-production-2026-notre-dame-texas
- ESPN way-too-early 2026 Heisman (Feb 9, 2026):
  https://africa.espn.com/college-football/story/_/id/47278107/way-too-early-look-2026-heisman-trophy-race
- On3 top returning QBs (Feb 27, 2026):
  https://www.on3.com/news/college-football-qb-rankings-danny-kanell-ranks-top-10-returners-in-2026/
- NFL.com Carson Beck draft result:
  https://www.nfl.com/news/carson-beck-cardinals-no-65-overall-pick-2026-nfl-draft
- Penn State 8-player 2026 Draft recap:
  https://www.psu.edu/news/intercollegiate-athletics/story/eight-nittany-lions-taken-2026-nfl-draft
- Browns on Shedeur Sanders (2025 Draft):
  https://www.clevelandbrowns.com/news/browns-select-qb-shedeur-sanders-with-the-no-144-pick-in-the-2025-nfl-draft
- Browns on Dillon Gabriel (2025 Draft):
  https://www.clevelandbrowns.com/news/browns-select-qb-dillon-gabriel-with-the-no-94-pick-in-the-2025-nfl-draft
- Raiders on Ashton Jeanty (2025 Draft):
  https://www.raiders.com/news/ashton-jeanty-no-6-overall-pick-raiders-select-2025-nfl-draft-boise-state-running-back
- NCAA 2026 portal numbers (Jan 16, 2026):
  https://www.ncaa.com/news/football/article/2026-01-16/10-numbers-breaking-down-2026-college-football-transfer-portal
- ESPN 2026 portal trends:
  https://www.espn.com/college-football/story/_/id/47624150/2026-college-football-transfer-portal-trends-prices-qbs

---

## §9. Implementation order (dependency-ordered)

### Phase 1 — Data layer (BLOCKER for all modules)

1. **Migration 20260527_04_player_status_override.sql** — create override table
2. **View `player_current_status_view`** — see §3.4
3. **Ingest 2026 NFL Draft picks** — CFBD `/draft/picks?year=2026`, or scrape
   nfl.com if CFBD lags. Affects 250+ players. ETA: 20 min if CFBD-ready, ~2hr
   if manual scrape.
4. **Ingest 2026 college rosters** — CFBD `/roster?year=2026` for all 134 FBS
   teams. Affects ~17k players. ETA: 1 hr.
5. **Manual override seed** for top-100 marquee players — verify Status Strip
   renders correctly for Manning, Smith, Allar, Beck, Lagway, etc. ETA: 1 hr.

### Phase 2 — Module 1 (Player Status Strip)

6. `src/cfb_rankings/player_pages/status_strip.py` — render function
7. CSS via design tokens
8. Wire into reporting.py via `new_status_strip_html` key
9. Inject ABOVE `<section class="qb-fingerprint">` in template
10. Smoke-test on Manning, Allar, Beck, Smith, Gabriel, retired-alum cases

### Phase 3 — Module 2 (2026 Outlook, Type A only)

11. **Migration 20260527_05_player_depth_chart_2026.sql** — depth chart table
12. **Migration 20260527_06_player_award_watch_2026.sql** — award watch table
13. **Seed depth chart** for top 100 returning players (manual)
14. **Seed award watch** for top 50 returning per-position (manual, from ESPN
    way-too-early Heisman + Phil Steele watch lists)
15. `src/cfb_rankings/player_pages/outlook_2026.py` — render function
16. Wire into reporting.py
17. Render ONLY when `status_code = 'RETURNING_2026'`

### Phase 4 — Module 3 (Where They Ended Up)

18. `src/cfb_rankings/player_pages/where_ended_up.py` — render function for
    both 5A and 5B variants
19. Wire into reporting.py
20. Render when `status_code` matches §5.1 list
21. NFL team logos asset pipeline (cached static SVGs in `output/site/assets/nfl/`)
22. **Optional**: seed `player_draft_projection.role_projection_text` for top
    50 draftees (manual editorial, ~1 hr)

### Phase 5 — Re-labeling pass

23. `season_context_label()` function in a new
    `src/cfb_rankings/player_pages/season_labels.py`
24. Audit all "Current Season Production", "Career Stats", section headers in
    reporting.py player template
25. Replace hardcoded "2024" / "Current Season" with `season_context_label()` calls
26. Update `<title>` tag template per §6.2

### Phase 6 — Verification

27. Build + verify against eight marquee players covering all 11 status codes:
    Manning (A), Smith (A), Lagway (A), Allar (B-2026), Beck (B-2026),
    Mendoza (B-2026), Gabriel (B-prior), Ward (B-prior), Jeanty (B-prior),
    Bear Bryant (D historical)
28. Mobile audit at 375px / 640px / 1024px
29. Update `scripts/verify_player_pages_wave_complete.py` to require Status
    Strip + (Outlook OR Where-Ended-Up) per archetype

---

## §10. Ready-now vs data-gated split

### §10.1 Ready-now (ship today against current DB)

- **Module 1 Status Strip** for Type B/D using existing `player_nfl_draft`
  (2025 draft data already in DB for Gabriel/Sanders/Ward/Jeanty)
- **Module 1 Status Strip** for Type D (historical alumni) — needs no new data
- **Module 3 Variant 5A** for `NFL_DRAFTED_PRIOR` (Gabriel/Sanders/Ward/Jeanty
  have full draft records)
- **Re-labeling pass** — function-only, no new data
- **Vocabulary glossary** — copy-only

### §10.2 Data-gated (needs new ingest)

| Capability | Block | Smallest unblock |
|---|---|---|
| Type A status resolution | No 2026 roster table | CFBD `/roster?year=2026` ingest, ~1hr |
| Type B for 2026 draftees (Allar/Beck/Mendoza) | No 2026 draft rows | CFBD `/draft/picks?year=2026` or manual scrape |
| Type C transfers | No transfer table | CFBD `/transfer-portal?year=2026` |
| Module 2 depth chart | No 2026 depth chart table | Manual seed top 100 |
| Module 2 award watch | No 2026 award watch table | Manual seed top 50 per position |
| Module 2 supporting cast (OL/WR/OC) | Depends on `team_preview_roster_reload` rows (already populated for FBS by parallel work stream) | Already ready |

---

## §11. Open questions for user decision

1. **Multi-year NFL veterans** — for Gabriel/Sanders/Ward/Jeanty in their 2nd NFL
   season, should "Where They Ended Up" show their NFL stats for 2025 season, or
   just the destination card? Recommend: destination card only for Wave 25;
   defer NFL stat integration to Wave 26.
2. **Type C "transferred" data** — none of the original example players are
   actually Type C anymore (Beck/Mendoza drafted). Do we want to find Type C
   examples in the data (LJ Martin Florida State, Maalik Murphy → Oregon State,
   etc.) and verify the variant 5B renders, or accept this archetype is rare
   for marquee names in May 2026?
3. **NIL valuation** — On3 prominently shows NIL. Include in Module 2? (Needs
   new data source — On3 API or scrape; not in our DB today.)
4. **Manual override scope** — Phase 1 step 5 says "top 100 marquee players."
   How is that list defined? Suggest: top 50 per position cohort + all 2026
   NFL Draft picks + all 2025 NFL Draft picks who are still active.
5. **Player photos** — Status Strip optionally accepts a player headshot. Do
   we have a license? Recommend defer to Wave 27; team logos only for now.
6. **Season-phase gate sharpness** — should Status Strip suppress entirely
   during in-season weeks, or just change copy? Recommend: change copy ("Active
   · {team} {position} · Week {N}") but never suppress.
7. **Override audit trail** — should `player_status_override.set_by` accept
   free text, or a controlled vocabulary of operator usernames?

---

## §12. What's often overlooked (pre-mortem)

- **"In portal + signed UDFA same week"** — player can enter portal AND sign
  UDFA within 48 hours post-draft. Both records exist. Status resolver MUST
  check `player_nfl_draft` first; NFL outcome always wins.
- **Logo URL rot** — never hardcode NFL franchise logo URLs at ingest time;
  resolve from a `nfl_franchises` table at render time.
- **WR Heisman** — Jeremiah Smith on Heisman watch is a real 2026 case. Display
  logic must NOT suppress this as edge case.
- **`Retry-After` missing on CFBD 429** — pipeline must default to 60s if header
  absent; otherwise KeyError at 3am.
- **Date-aware re-labeling** — `season_context_label()` must take `current_date`
  parameter, not hardcode 2026. Same bug will hit in 2027 otherwise.
- **Stale archetype assumptions** — Drew Allar was on every "returning" list
  through April 2026; drafted Rd 3. Anyone hard-coding archetypes from January
  predictions will be wrong by May. Override table is the safety net.
- **Identity drift** — Cameron Ward (game stats `player_id=9464`) vs Cam Ward
  (player_honors `player_id=1015`). Status resolver should join on a canonical
  alias table, not raw `player_id` only.

---

*Spec assembled from multi-AI probe outputs (Claude-sonnet ×2, Codex ×2,
Perplexity). Codex pulled live 2026 web sources verifying the corrections in §0.
Gemini failed (exit 55); Perplexity returned empty parse error — those branches
not represented. Knowledge of 2026 NFL Draft + portal outcomes verified from
official team/league sources listed in §8.*
