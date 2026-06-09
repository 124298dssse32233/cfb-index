# Chronicle Quality Proposal v3

Current as of May 24, 2026. This v3 preserves the v1 editorial diagnosis and the v2 local-LLM plus paid-API workflow, then expands the visual strategy. The key adjustment from v2: CFB Index should not be artificially limited to the current six chart families when a different chart form produces a world-class, CFB-native fan insight. The six-chart vocabulary remains the baseline, but Chronicle needs an expanded admission process for visuals that are good enough to earn a permanent place in the site.

## 1. V3 Bottom Line

Chronicle should become a visual-first fan-intel product, not an LLM prose module with occasional charts.

The target reader in 2026 is not asking for generic summaries. They want:

- Why my team is on the CFP line.
- Whether the portal fixed the actual roster hole.
- Which freshman or transfer is about to matter.
- Whether the market, models, committee, and fanbase disagree.
- How this season rhymes with a season I remember.
- One image worth sending to a group chat.

The revised product architecture:

```text
trusted data query
  -> deterministic frame and metric computation
  -> Visual Director spec
  -> deterministic SVG/PNG renderer
  -> local LLM card copy
  -> local critics
  -> paid critic/refiner only for flagship S/T1 cards
  -> screenshot QA
  -> Chronicle page, team page module, and share-card asset
```

The LLM may choose an angle, write prose, select annotations, and critique whether the visual has a clear takeaway. The LLM must not invent chart values.

## 2. Product Bar

A Chronicle card is not good enough because it is accurate. It is good enough when it does at least four of these:

| Test | Passing behavior |
|---|---|
| Fan question | Answers something a real fan is already arguing about. |
| Specificity | Names the player, game, class, coach, opponent, market, or week that creates the edge. |
| Comparison | Places the team against peers, history, expectation, or the 12-team CFP field. |
| Motion | Shows change, not just status. |
| Consequence | Makes the reader understand what changes next. |
| Screenshot value | Produces a compact visual with one clear headline finding. |
| Voice fit | Sounds like CFB Index, not an AI dashboard. |

The design target is "NYT Upshot clarity plus CFB message-board stakes." It should feel more analytical than On3 rumor streams, more visual than ESPN recaps, more fan-aware than generic model pages, and less sterile than a betting terminal.

## 3. 2026 CFB Context That Should Drive Visuals

As of May 24, 2026:

- The CFP remains a 12-team format for the 2026 season, with campus first-round games and a bracket that does not reseed or avoid rematches. The CFP's own format page describes seeds 5-12 playing on campus and no reseeding/rematch adjustment. AP reported on January 23, 2026 that the CFP stayed at 12 for the next season while expansion remained unresolved, with Notre Dame and Power Four champion treatment among the notable changes.
- NCAA Division I transfer windows list Football FBS as January 2, 2026 through January 16, 2026. That makes portal visualization a concentrated, calendar-driven product surface rather than a vague offseason story.
- CollegeFootballData API tiers include games, teams, team/player stats, recruiting, betting lines, advanced metrics such as EPA/PPA/win probability, opponent-adjusted metrics, weather, live scoreboard, live play-by-play, and GraphQL at higher tiers. This is enough to support CFB-native visuals without pretending CFB Index owns secret data.
- The repo already has a deep local database: 1.3M player-game stat rows, 426k player-season stat rows, 99k Heisman weekly rows, 32k power-rating rows, 26k resume-rating rows, 10k transfer rows, and team talent/returning production/draft/coaching tables.

Reference links:

- CFP format: https://collegefootballplayoff.com/sports/2024/5/29/12-team-format.aspx
- AP CFP status report, January 23, 2026: https://apnews.com/article/cfp-college-football-playoff-expansion-bfb7c8a66f337c76591cbf68536593d6
- NCAA transfer windows PDF: https://s3.amazonaws.com/fs.ncaa.org/Docs/eligibility_center/Transfer/DIUG_Windows.pdf
- CollegeFootballData API tiers: https://collegefootballdata.com/api-tiers
- D3 official site: https://d3js.org/
- Observable Plot marks: https://observablehq.com/plot/features/marks
- Datawrapper visualization types: https://developer.datawrapper.de/docs/chart-types

## 4. Expanded Visual Grammar

The existing locked chart vocabulary is a strong starting point:

1. Percentile bar.
2. Trajectory spark.
3. Bump chart.
4. Annotated line.
5. Small multiples.
6. Heatmap.

V3 recommendation: keep these as Tier 0 chart families, but add a governed Tier 1 visual grammar for Chronicle. A new chart family is allowed if it passes all admission tests below.

### New Chart Admission Tests

| Test | Requirement |
|---|---|
| Fan-native | A CFB fan can understand why this form fits football, recruiting, portal, CFP, or rivalry context. |
| Mobile legible | Works at 360px width without microscopic labels. |
| Static fallback | Can render as SVG/PNG during build; interaction is enhancement only. |
| Data honest | Encodings are proportional and annotated; no decorative geometry. |
| Repeatable | At least three Chronicle card types can reuse the family. |
| Sourceable | Every displayed value comes from a query, not prose. |
| Shareable | Can be cropped to a 1200x675 or 1080x1350 share card. |
| Accessible | Has alt text and table fallback. |

### Tier 1 Chart Families To Add

| Family | Use it for | Chronicle fit | Guardrail |
|---|---|---|---|
| Annotated scatter / quadrant | Market vs model, talent vs production, resume vs power | Perfect for disagreement cards and committee arguments | Max 40 dots on mobile; label only highlighted teams. |
| Dot plot / strip plot | Ranking many teams on one metric | More honest than vertical bars; high fan scan value | Sort by value; include median/percentile line. |
| Range plot | Best/worst/median, ceiling/floor, uncertainty | Makes prediction uncertainty visible | Always label interval meaning. |
| Arrow plot | Week-to-week movement, portal before/after, odds shift | Strong for "what changed" cards | Use only two time points; use bump/line for longer histories. |
| Slopegraph | Rank or metric movement from prior state to now | Clearer than a bump chart for two checkpoints | Limit to 8-12 entities. |
| Waterfall / decomposition | Why power rating moved, why resume changed, why odds moved | Shows causal ingredients, not just final number | Components must sum to displayed delta. |
| Alluvial / Sankey | Transfer portal flow, recruiting pipeline, coach tree movement | Excellent for offseason roster stories | Only for real flows; cap nodes; no spaghetti. |
| Bracket / path lattice | CFP path, conference title path, bowl road | 2026 CFP product anchor | Must show current seed/rank and path assumptions. |
| Football field map | Play location, explosive-play origin, red-zone failure zones | CFB-native and visually distinct | Requires play-level data; no fake field art. |
| Hexbin / contour density | Where events cluster on field or across two metrics | Useful when scatter overplots | Include legend and sample size. |
| Ridgeline / distribution bands | Team/player distribution over seasons or peers | Shows "how unusual is this?" better than a single number | Use sparingly; no more than 8 ridges. |
| Beeswarm | Player/team distribution with highlighted entity | Great for "this guy is an outlier" | Needs collision-safe labels. |
| Tile mosaic / roster grid | Scholarship roster, starters, class composition, portal churn | Great for roster construction | Each tile must represent a real count. |
| Map / travel arc | conference travel, CFP bowl path, road fatigue | New national-conference geography matters in 2026 | Use maps only when geography is the finding. |
| Minimal network | coaching lineage, recruiter territory, transfer relationships | Strong for lineage and pipeline cards | No force-layout hairballs; small annotated networks only. |

### Still Mostly Forbidden

| Family | Policy |
|---|---|
| Pie/donut | Still almost never. Use only if a future editorial review approves a tiny composition badge; default remains no. |
| 3D charts | Still no. |
| Decorative force networks | No. Networks must have few nodes and a named relationship. |
| Radar/spider | Keep only for player fingerprint contexts where the shape itself is the point. |
| Chord diagrams | Avoid unless a true conference/portal flow needs it and a Sankey is worse. |
| Gauges | Avoid. Use range, bullet, or percentile bars. |

## 5. Chronicle Visual Modules

These are not generic chart names. They are CFB Index visual products that can be paired with Chronicle cards.

| Module | Chart family | Fan question | Core data | Best phase |
|---|---|---|---|---|
| CFP Bubble Wall | Annotated scatter/quadrant plus bracket chips | Are we in, out, or dangerous? | resume ratings, power ratings, official rankings, conference champ status | Oct-Dec |
| 12-Team Path Lattice | Bracket/path lattice | What path would this seed create? | CFP seed rules, rankings, win probabilities | Nov-Jan |
| Committee Resume Split | Quadrant scatter | Does the committee like this team more than the model? | official rankings, resume score, power rating | Nov-Dec |
| Market vs Model Board | Quadrant scatter | Is the market overreacting or sleeping? | betting/Polymarket odds, power ratings, title odds | Year-round |
| Portal Flow Ledger | Sankey/alluvial | Did the portal fix the actual hole? | transfer_entries, returning_production, player usage | Jan-Feb |
| Roster Replacement Grid | Tile mosaic | Which positions changed hands? | transfers, recruiting, returning production, depth/usage | Jan-Aug |
| Talent Yield Curve | Annotated scatter or beeswarm | Is this program developing stars? | recruiting profiles, player stats, NFL draft | Offseason |
| Recruit-to-Snap Ladder | Slopegraph/range plot | Which class actually became the team? | recruiting profiles, usage, player stats | Offseason |
| Draft Pipeline Conveyor | Alluvial or dot plot | Which programs turn recruits into picks? | recruiting, player stats, NFL draft | Apr-May |
| Heisman Race Braid | Bump chart plus spark strips | Who is really moving in the race? | heisman_rankings_weekly, player stats | Sep-Dec |
| QB Volatility Strip | Distribution/range plot | Is the QB stable or chaos-prone? | player game stats, usage, turnovers, explosives | In-season |
| Explosive Play Field Map | Football field map/hexbin | Where did the game break? | play-by-play, PPA/EPA, yardline | In-season |
| Red-Zone Truth Table | Heatmap plus percentile bars | Is this offense unlucky or flawed? | red-zone drives, points, success rate | In-season |
| Win Path Trellis | Small multiples plus path lattice | Which games decide the season? | schedule, win probability, ratings | Preseason/in-season |
| Schedule Stress Map | Calendar heatmap/map | Where does travel/rest/opponent load peak? | games, venues, rest, power rating | Preseason |
| Travel Tax Map | Map/travel arc | How weird is the new-conference travel burden? | venues, conference schedule, miles | Preseason |
| Rivalry Pressure Gauge | Range plot plus history spark | Is this rivalry result normal or era-changing? | games, rivalry history, ratings deltas | Rivalry week |
| Coach Era Spine | Annotated line | Where does this coach era really stand? | team seasons, coaches, power/resume ratings | Year-round |
| Fan Mood Braid | Multi-line annotated chart | Are fans, market, and model aligned? | fan_intel, odds, ratings | Year-round |
| Panic vs Proof Matrix | Quadrant scatter | Is the fanbase right to panic? | fan mood, resume, power delta, injuries/news if available | Sep-Nov |
| Returning Production X-Ray | Waterfall/decomposition | What actually came back? | returning_production, team stats | Feb-Aug |
| Class Cliff Detector | Ridgeline/tile mosaic | Is the roster about to get old or empty? | recruiting classes, eligibility, usage | Offseason |
| Statement Win Ladder | Dot/range plot | Which win changed the resume? | games, team_rating_deltas, resume deltas | In-season |
| Bad Loss Seismograph | Waterfall plus annotated line | Which loss still hurts? | resume deltas, opponent quality, game result | In-season |
| Player Breakout Radar, constrained | Fingerprint-only radial/percentile hybrid | What kind of player is he becoming? | player stats, usage, value metrics | In-season |

The first implementation wave should be the ten with the highest reuse and fan impact:

1. CFP Bubble Wall.
2. Market vs Model Board.
3. Portal Flow Ledger.
4. Roster Replacement Grid.
5. Talent Yield Curve.
6. Heisman Race Braid.
7. Explosive Play Field Map.
8. Schedule Stress Map.
9. Returning Production X-Ray.
10. Statement Win Ladder.

## 6. Pair Visuals With Card Types

Every Chronicle card type should have a preferred visual. The visual is not optional decoration; it is the evidence object.

| Card type | Default visual | Backup visual | Primary evidence |
|---|---|---|---|
| Market disagreement | Market vs Model Board | Arrow plot | odds, power ratings, resume ratings |
| CFP bubble case | CFP Bubble Wall | 12-Team Path Lattice | official rankings, conference status, resume/power |
| Portal repair audit | Portal Flow Ledger | Roster Replacement Grid | transfer_entries, returning production, usage |
| Recruit development | Talent Yield Curve | Recruit-to-Snap Ladder | recruiting profiles, player stats, draft |
| Heisman motion | Heisman Race Braid | Trajectory spark | heisman_rankings_weekly, player stats |
| Game hinge | Explosive Play Field Map | Statement Win Ladder | play-by-play, rating deltas |
| Schedule trap | Schedule Stress Map | Win Path Trellis | games, venues, ratings |
| Coach-era verdict | Coach Era Spine | Dot plot vs peers | team seasons, power/resume ratings |
| Fanbase divergence | Fan Mood Braid | Panic vs Proof Matrix | fan_intel, market, ratings |
| Roster identity | Roster Replacement Grid | Returning Production X-Ray | roster, portal, returning production |
| Draft afterglow | Draft Pipeline Conveyor | Talent Yield Curve | NFL draft, recruiting, player stats |
| Rivalry pressure | Rivalry Pressure Gauge | Annotated line | historical games, deltas, rivalry metadata |

## 7. Visual Director Contract

Add a Visual Director pass after frame planning and before writing. It emits a deterministic spec, not pixels.

```json
{
  "visual_id": "market_model_board",
  "chart_family": "annotated_scatter",
  "headline_finding": "Alabama is priced like a contender but modeled like a bubble bye threat.",
  "data_query_id": "market_vs_model_weekly_v1",
  "entity_scope": {
    "team_slug": "alabama",
    "season_year": 2026,
    "week": 6
  },
  "encodings": {
    "x": "market_title_probability",
    "y": "power_rating_percentile",
    "color": "conference",
    "label": "highlighted_teams"
  },
  "annotations": [
    {
      "target": "alabama",
      "text": "market premium",
      "reason": "team is top quartile in odds but not top quartile in model"
    }
  ],
  "required_sources": [
    "power_ratings_weekly",
    "resume_ratings_weekly",
    "market_odds_snapshot"
  ],
  "mobile_priority": "highlighted_team_plus_four_peers",
  "share_card": true,
  "alt_text": "Scatter plot comparing title-market probability and power rating percentile, with Alabama highlighted."
}
```

Rules:

- `headline_finding` must be a chart claim, not a prose headline.
- `data_query_id` must resolve to a known SQL/Python query function.
- `annotations` can select and phrase callouts, but values must be computed by the renderer.
- The spec fails if it cannot produce a table fallback.
- The renderer fails if label collision, contrast, or viewport checks fail.

## 8. Renderer Architecture

Chronicle should use a two-layer rendering model.

### Layer 1: Build-Time Static Renderers

Default for all generated pages:

- Python computes datasets from SQLite.
- Renderer emits inline SVG for HTML.
- Renderer also emits PNG/JPEG share-card assets for social/iMessage contexts.
- Every visual gets a compact data table fallback in HTML.

Why this matters:

- Static site stays fast.
- Vercel output is deterministic.
- No client-side dependency is required for 69k pages.
- Screenshots can be tested in CI.

### Layer 2: Interactive Enhancements

Only for high-value surfaces:

- `/chronicle/index.html`.
- team pages for profiled FBS programs.
- `/heisman/`.
- `/rankings/`.
- future CFP hub.

Use D3 or Observable Plot when interaction genuinely helps. D3 is appropriate for bespoke geometry and interactions; Observable Plot is appropriate for layered marks and faster composition. Datawrapper's taxonomy is useful as a reference for dot/range/arrow/scatter choices, but do not depend on Datawrapper embeds for the static product.

Interactions worth building:

- Hover/tap tooltips.
- Conference/team filters.
- "Show my team" highlight.
- Before/after toggle.
- Week scrubber.
- Bracket seed toggle.

Interactions not worth building:

- Decorative animation.
- Auto-rotating charts.
- Zoom/pan on tiny mobile charts.
- Tooltips that contain essential facts unavailable elsewhere.

## 9. Data Query Layer

Add a visual query registry:

```text
src/cfb_rankings/chronicle/visuals/
  __init__.py
  registry.py
  specs.py
  queries.py
  render_svg.py
  render_share.py
  qa.py
  families/
    scatter.py
    bracket.py
    sankey.py
    field_map.py
    waterfall.py
    dotplot.py
    rangeplot.py
    tile_mosaic.py
```

Each visual query returns:

```json
{
  "query_id": "portal_flow_ledger_v1",
  "source_tables": ["transfer_entries", "returning_production", "player_usage_season"],
  "as_of": "2026-05-24T00:00:00Z",
  "rows": [],
  "summary_stats": {},
  "sample_n": 0,
  "confidence": "medium",
  "limitations": []
}
```

The renderer never reaches into arbitrary tables. It consumes query outputs with typed schemas.

## 10. Data Source Map

Use the repo's existing tables first.

| Source/table | Visuals unlocked | Notes |
|---|---|---|
| `games` | Schedule Stress Map, Win Path Trellis, Rivalry Pressure | Already local. |
| `team_rating_deltas` | Statement Win Ladder, Bad Loss Seismograph, Waterfall | High value because it explains movement. |
| `power_ratings_weekly` | CFP Bubble Wall, Market vs Model, Coach Era Spine | Main model axis. |
| `resume_ratings_weekly` | Committee Resume Split, CFP Bubble Wall | Main committee-case axis. |
| `official_rankings` | CFP Bubble Wall, Committee Resume Split | Needed in November/December. |
| `heisman_rankings_weekly` | Heisman Race Braid | Already rich enough for a flagship hub. |
| `player_game_stats` | QB Volatility Strip, Explosive Play Field Map fallback, player cards | Very large; query carefully. |
| `player_season_stats` | Talent Yield Curve, Recruit-to-Snap Ladder | Good for career arcs. |
| `player_usage_season` | Roster Replacement Grid, breakout cards | Useful for "who became the team?" |
| `player_value_metrics` | Player breakout and fingerprint visuals | Smaller but high-signal. |
| `player_recruiting_profiles` | Talent Yield Curve, Recruit-to-Snap Ladder | Core recruit-development data. |
| `recruiting_entries` | Class Cliff Detector | Useful but currently small. |
| `transfer_entries` | Portal Flow Ledger, Roster Replacement Grid | Must become a Chronicle centerpiece. |
| `player_nfl_draft` | Draft Pipeline Conveyor | Strong spring/offseason hook. |
| `returning_production` | Returning Production X-Ray, roster identity cards | High-value preseason/offseason source. |
| `team_talent_snapshots` | Talent vs production visuals | Great for over/underachievement. |
| `team_seasons` | Coach Era Spine | Connects data to staff/era. |
| Fan-intel tables | Fan Mood Braid, Panic vs Proof Matrix | Should be visualized against model/market, not alone. |

New or expanded external data priorities:

| Data | Priority | Why |
|---|---:|---|
| CFBD Tier 2 or higher | P0 | Opponent-adjusted metrics, weather, live play-by-play, and richer lines unlock better visuals. |
| Venue geo coordinates | P0 | Needed for travel maps and new-conference stress. |
| Public injury/depth-chart signal | P1 | Useful but noisy; use as annotation, not core metric. |
| PFF grades | P2 paid | Valuable for trench/position cards; explicit cost decision. |
| FEI/SP+ style references | P2 | Good benchmark context, but avoid copying proprietary values unless licensed. |

## 11. Local LLM + Paid API Workflow For Visuals

The v2 model workflow still holds:

- Ollama first.
- Mistral Nemo 12B-class writer.
- Qwen 8B-class planner/critic.
- llama.cpp as control lane.
- Paid APIs only for gated S/T1 judgment.

For visuals, split responsibilities:

| Step | Owner | Reason |
|---|---|---|
| Data query | Python/SQLite | Must be deterministic. |
| Metric computation | Python | Values must be reproducible. |
| Chart-family eligibility | Python rules plus Visual Director | Prevents nonsense chart selection. |
| Annotation candidate selection | Python first, local LLM second | Values first, language second. |
| Visual headline | local LLM | Useful for phrasing the finding. |
| Alt text | local LLM, deterministic value injection | Accessibility plus consistent facts. |
| Premium critique | paid API, gated | For flagship cards where "is this actually interesting?" matters. |
| Pixel/render QA | Playwright/static scripts | LLMs cannot inspect layout reliably enough. |

Paid APIs should review visual packages, not raw chart ideas:

```text
Input to paid critic:
  - rendered chart screenshot
  - data table
  - headline finding
  - card body
  - source list

Paid critic output:
  - keep / revise / suppress
  - reason
  - one suggested sharper headline
  - one suggested annotation improvement
```

Do not pay an API to create charts. Pay only to judge whether a flagship visual-card package is worth publishing.

## 12. Visual QA Gates

A visual cannot ship unless it passes all gates.

### Data Gates

| Gate | Rule |
|---|---|
| Source completeness | All source tables listed in `visual_receipt`. |
| Sample size | `sample_n` displayed when small or confidence is not high. |
| Value reproducibility | Renderer can regenerate the same values from query output. |
| No LLM values | Any number in SVG must originate in query output. |
| Units | Every axis/legend has units or a clear label. |

### Design Gates

| Gate | Rule |
|---|---|
| Mobile width | 360px screenshot has no overlapping labels. |
| Desktop width | 1024px screenshot uses available space without huge dead zones. |
| Contrast | Text and key marks pass accessible contrast against surface. |
| Label collision | Renderer either resolves collisions or suppresses nonessential labels. |
| Color meaning | Semantic colors carry meaning; team colors identify entities. |
| Text length | Chart labels are short; details go in caption/table fallback. |
| Aspect ratio | Default inline visual: 16:9 or 4:3. Share visual: 1200x675 and 1080x1350 variants. |

### Editorial Gates

| Gate | Rule |
|---|---|
| One-sentence finding | Reader can say what the chart shows in one sentence. |
| Not generic | The visual must name the team/player and the contrast. |
| Anti-duplicate | Visual thesis hash cannot match a same-team same-season visual. |
| Chronicle slot | Visual occupies a distinct angle slot: CFP, roster, market, player, history, fan mood, schedule, game hinge. |
| Share value | The cropped asset still makes sense without surrounding article prose. |

## 13. Visual Scoring Rubric

Add `visual_quality_score` from 0 to 1:

| Component | Weight |
|---|---:|
| Clarity of finding | 0.20 |
| Fan relevance | 0.20 |
| Data depth | 0.15 |
| Novelty of framing | 0.15 |
| Mobile legibility | 0.10 |
| Screenshot value | 0.10 |
| Evidence/provenance strength | 0.05 |
| Voice/brand fit | 0.05 |

Suppress below `0.62`. Local-refine from `0.62` to `0.78`. Paid-review only from `0.78` upward for S/T1 cards, or for homepage candidates.

## 14. Example Visual-Card Packages

### A. CFP Bubble Wall

```text
Headline finding:
Alabama is safer in the model than in the committee case.

Visual:
Annotated scatter. X = resume percentile. Y = power-rating percentile.
Bubble outline = conference champion path. Highlight Alabama, top four seeds,
last four in, first four out.

Card body:
Alabama's argument splits in two. The model still treats the Tide like a top-end
team, but the resume axis is where the bracket gets tight: same tier as the
last bye candidates, closer to the cut line than the logo suggests. That is the
danger zone in the 12-team era, where one ugly November box score can matter
more than three months of brand gravity.
```

### B. Portal Flow Ledger

```text
Headline finding:
Auburn bought volume, but the replacement value clusters in two rooms.

Visual:
Sankey/alluvial. Left = outgoing production by position group. Middle = portal
entries. Right = returning/added projected role. Width = prior usage or transfer
points, not headcount.

Card body:
The portal headline says Auburn added bodies. The ledger says the bet is more
specific: two position rooms carry most of the replacement value. That matters
because a seven-win roster rarely needs a vibes overhaul; it needs the right
third downs to stop leaking. If the new value does not show up where last year's
usage left, the portal class will look bigger than it plays.
```

### C. Talent Yield Curve

```text
Headline finding:
Oregon is converting blue-chip volume into draftable production faster than its peer group.

Visual:
Scatter/beeswarm. X = recruit rating bucket. Y = college value/draft outcome.
Highlight Oregon classes against P4 peers.

Card body:
Recruiting rankings are a receipt, not a verdict. Oregon's stronger claim is
what happens two and three years later: more of the high-end class is turning
into usage, production, and draft signal. That is the difference between
signing stars and building a roster that still looks fast after attrition hits.
```

### D. Schedule Stress Map

```text
Headline finding:
USC's hard part is not just opponent strength; it is where the mileage lands.

Visual:
Calendar heatmap plus travel arcs. Cells = week. Fill = opponent power.
Border = travel distance/rest disadvantage. Annotate two squeeze weeks.

Card body:
The new Big Ten map makes schedule difficulty less abstract. USC's issue is not
one impossible opponent; it is the weeks where rating, rest, and travel stack on
top of each other. That is where a good team starts playing like a tired one,
and it is where playoff-margin programs lose the clean resume they thought they
had in August.
```

### E. Statement Win Ladder

```text
Headline finding:
One win moved the resume more than the next three combined.

Visual:
Waterfall or dot/range ladder using `team_rating_deltas`.

Card body:
Not every ranked win weighs the same. The ladder shows the one result that
actually changed the season's math, then the smaller wins that mostly protected
the new position. That is the Chronicle difference: it does not just count
quality wins; it shows which one rewrote the argument.
```

## 15. Visual Components To Build First

### P0 Renderer Components

| Component | Purpose |
|---|---|
| `VisualSpec` Pydantic model | Validates Visual Director output. |
| `VisualReceipt` model | Stores source tables, query ID, sample, confidence, limitations. |
| `visual_query_registry` | Maps `data_query_id` to deterministic query function. |
| SVG renderer base | Layout, scales, labels, theme tokens. |
| Share-card renderer | 1200x675 and 1080x1350 image exports. |
| Visual QA script | Screenshot and label/contrast tests. |

### P0 Chart Families

1. Annotated scatter/quadrant.
2. Dot/range/arrow plot.
3. Waterfall.
4. Bracket/path lattice.
5. Tile mosaic.
6. Sankey/alluvial, simplified.

### P1 Chart Families

1. Football field map.
2. Travel map/arcs.
3. Beeswarm.
4. Ridgeline/distribution.
5. Minimal network.

## 16. Implementation Plan

### Week 1: Visual Foundation

| Day | Work | Output |
|---:|---|---|
| 1 | Add visual spec, receipt, registry skeleton | Visuals become typed pipeline artifacts. |
| 2 | Build annotated scatter renderer | Market vs Model and CFP Bubble Wall can render. |
| 3 | Build dot/range/arrow renderer | Rankings, movement, ceiling/floor visuals can render. |
| 4 | Add visual QA screenshots at 360/768/1200 widths | Prevents broken share cards and mobile overlap. |
| 5 | Wire Visual Director into Chronicle planner output | Cards receive visual specs before writing. |

### Week 2: Fan-Impact Visuals

| Day | Work | Output |
|---:|---|---|
| 6 | Build CFP Bubble Wall query and visual | First flagship 2026 visual. |
| 7 | Build Market vs Model query and visual | Offseason and in-season reusable card. |
| 8 | Build Portal Flow Ledger query and simplified alluvial | Offseason roster centerpiece. |
| 9 | Build Roster Replacement Grid | Mobile-friendly portal/recruiting view. |
| 10 | Add share-card renderer and homepage card variants | Visuals become social objects. |

### Week 3: Data Richness

| Day | Work | Output |
|---:|---|---|
| 11 | Add Talent Yield Curve | Recruiting-to-development product surface. |
| 12 | Add Heisman Race Braid | Player/Heisman hub integration. |
| 13 | Add Schedule Stress Map | Preseason schedule stories improve. |
| 14 | Add Statement Win Ladder | Game/result cards become more specific. |
| 15 | Run 50-card visual benchmark | Lock defaults and suppress weak visuals. |

## 17. Code-Level Touchpoints

Likely files/modules:

| Area | File/path |
|---|---|
| Chronicle pipeline | `src/cfb_rankings/chronicle/pipeline.py` |
| Prompts and schemas | `src/cfb_rankings/chronicle/prompts.py` |
| Runtime/router | `src/cfb_rankings/chronicle/runtime.py` |
| Evidence sources | `src/cfb_rankings/chronicle/evidence_sources.py` |
| Retriever | `src/cfb_rankings/chronicle/retriever.py` |
| Cache | `src/cfb_rankings/chronicle/cache.py` |
| Team page data | `src/cfb_rankings/team_pages/data.py` |
| Design tokens | `src/cfb_rankings/team_pages/styles/tokens.css` |
| New visual package | `src/cfb_rankings/chronicle/visuals/` |
| Visual tests | `tests/visual/` |

Schema additions:

```sql
CREATE TABLE IF NOT EXISTS chronicle_visual_cache (
    visual_cache_key TEXT PRIMARY KEY,
    slug TEXT NOT NULL,
    entity_kind TEXT NOT NULL,
    season_year INTEGER NOT NULL,
    week_number INTEGER,
    card_cache_key TEXT,
    visual_id TEXT NOT NULL,
    chart_family TEXT NOT NULL,
    data_query_id TEXT NOT NULL,
    visual_spec_json TEXT NOT NULL,
    visual_receipt_json TEXT NOT NULL,
    svg_html TEXT,
    share_asset_path TEXT,
    visual_quality_score REAL,
    created_at_utc TEXT NOT NULL,
    superseded_at_utc TEXT
);
```

Add indexes on `(slug, season_year, week_number)`, `(visual_id)`, and `(card_cache_key)`.

## 18. How This Works With V1 Anti-Duplication

The v1 anti-duplication system should apply to visuals too.

Add:

- `visual_thesis_hash`.
- `visual_data_fingerprint`.
- `chart_family_slot`.
- `primary_visual_source`.
- `consumed_visual_frames`.

Same-team six-card target:

| Slot | Example visual |
|---|---|
| CFP/ceiling | CFP Bubble Wall |
| Roster/portal | Portal Flow Ledger |
| Player/development | Talent Yield Curve |
| Market/model | Market vs Model Board |
| History/coach | Coach Era Spine |
| Fan mood/schedule | Fan Mood Braid or Schedule Stress Map |

No team should publish two same-week visuals with the same primary source, same chart family, and same thesis direction unless one is explicitly a follow-up.

## 19. Design Rules For "Amazing"

World-class does not mean loud. It means the reader knows where to look in half a second.

Rules:

- One headline finding above every visual.
- One primary highlighted team/player.
- Four to eight peer labels max.
- No legend if direct labels can work.
- Team colors identify teams; semantic colors explain meaning.
- Use tabular numerals for every stat.
- Keep chart captions short and specific.
- Put methodology in a receipt drawer, not in the headline zone.
- Mobile visuals get a different layout, not a squeezed desktop chart.
- Every share card should include source, sample size, and date in tiny UI text.

Visual tone:

- Scoreboard density, not SaaS dashboard chrome.
- Newspaper clarity, not betting-app clutter.
- Team identity without turning every page into a one-color theme.
- Static SVG first; animation only when it clarifies a transition.

## 20. Final V3 Recommendation

Chronicle's next leap is not just better LLM output. It is a controlled visual system where data queries produce chart-ready evidence objects, local LLMs turn those objects into fan-aware narrative packages, and paid APIs critique only the flagship results.

Adopt the expanded chart grammar. Build the first six renderer families. Make the CFP Bubble Wall, Market vs Model Board, Portal Flow Ledger, Roster Replacement Grid, Talent Yield Curve, and Heisman Race Braid the first product-quality visuals. Require every visual to pass mobile, share-card, provenance, and anti-duplication gates.

If CFB Index does this, Chronicle stops reading like an AI recap feed and starts feeling like the place fans go to see the season differently.
