# Chart Vocabulary

**Locked 2026-05-17 (v2-addendum Sprint v5-5.5). Expanded 6 → 9 per D-007: Sankey (live), Choropleth (live 2026-05-28), Network (live 2026-05-28 — portal-pipeline web on `/offseason/`). All 9 types now have a centralised renderer.**

CFB Index uses a locked set of chart types. Any new chart on the site MUST be one of these. The constraint produces a coherent visual vocabulary; drift produces visual chaos.

When an engineer asks "what chart should I use here?" the first answer is "which of the approved types?"

---

## The six approved chart types

### 1. Percentile Bar (Baseball Savant style)

**Use for:** Single-entity vs cohort comparison. "Where does this player/team rank against peers?"

**Visual:**
```
PASS YARDS/GAME             87th pct ●━━━━━━━━━━━━━━━━━━━●━━━ vs FBS QBs
RUSH YARDS/GAME             34th pct ━━━━━●━━━━━━━━━━━━━━━━━ vs FBS QBs
RED ZONE TD%                92nd pct ●━━━━━━━━━━━━━━━━━━━━●━ vs FBS QBs
```

**Color encoding:** Diverging red→grey→blue (Baseball Savant convention; blue = high). Inverted for inverted metrics (pressure-to-sack where low is good — invert so red = bad regardless of direction).

**Required elements:**
- Stat label (left)
- Percentile value (e.g., "87th pct")
- Horizontal bar with value dot positioned at percentile
- Peer label (right) — e.g., "vs FBS QBs" or "vs P4 teams"
- Sample-size chip (see confidence-signaling doc)

**When to use:** Player Fingerprint cards, Team Savant cards, peer-comparison surfaces.

**When NOT to use:** Time series (use trajectory spark). Multi-entity comparison (use small multiples). Categorical without percentile context (use bar OR text).

---

### 2. Trajectory Spark

**Use for:** Anything moving over time. "How has this metric changed in recent N periods?"

**Visual:**
```
HEISMAN ODDS  ━━━━━━━━╱╲━━╱╲━╱━━━━╲━╱━━ 8 weeks
              [tiny 160×40px sparkline, no axes, no labels in chart]
              Baseline: dotted line at season-start value
              Current: solid line + dot at right edge
```

**Required elements:**
- 160×40px default size (inline-compatible)
- Solid line for current trajectory
- Dotted line at baseline (season-start, or relevant comparator)
- Final-value dot prominent at right edge
- Above-chart label: metric name + current value

**Optional elements:**
- Annotation arrows for notable inflections (only if 1-2 max; otherwise it's a different chart)
- Color: per semantic ramp (belief=red→green, percentile=red→blue, accolade=gold)

**When to use:** Inline alongside any metric ("HEISMAN ODDS ↗"). Mood spark on team pages. Heisman race cards. Stat trends.

**When NOT to use:** Anything requiring axes or comparison labels (use annotated line). More than 50 data points (sparkline becomes a smear).

---

### 3. Bump Chart

**Use for:** Rankings movement over time. "Who's climbing, who's falling?"

**Visual:**
```
        Wk 0    Wk 4    Wk 8    Wk 12
#1     Ohio ━━━━ Ohio ━━━━ Ohio ╲   Texas ←
#2     Texas━━╳━━━━━━━━━━╳━━━━ Ohio
#3     Bama ━━━━ Bama ━━━━ Bama ━━━━ Bama
#4     Oregon━━╳━━━━━━━━━━━━━━━━ Georgia
#5     Georgia━━━━╲━━━━╱━━━━━━━━ Oregon
```

**Required elements:**
- Y-axis: rank position (1 at top)
- X-axis: time periods
- Each team a single line tracing through ranks
- Team name labels at left AND right edges
- Crossing lines visible (the whole point — who passed whom)

**Color encoding:** Team accent colors (each line in team color). For high-density charts (10+ teams), gray-out non-highlighted teams; highlight 3-5 movers.

**When to use:** Power Rankings weekly tracker. Heisman race over weeks. Recruiting class rank movement.

**When NOT to use:** When the underlying metric isn't a rank (use trajectory spark for raw value). When there are >15 entities (becomes spaghetti — filter to top movers).

---

### 4. Annotated Line (NYT-Upshot style)

**Use for:** A single trajectory that tells a story via in-chart annotations.

**Visual:**
```
ALABAMA POWER RATING — 2014 to 2025
       ╲
        ╲      ┌───────────────────────┐
         ╲     │ 2017 title run        │
          ╲   ←┘  peak rating: 95.4    │
           ╲   └───────────────────────┘
            ╲╱╲
             ╲ ╲    ┌──────────────┐
              ╲ ╲   │ Saban retires │
               ╲ ╲ ←┘ rating: 88.2  │
                ╲ ╲  └──────────────┘
                 ╲╲
                  ╲
2014                                          2025
```

**Required elements:**
- X-axis: time (years, weeks, dates)
- Y-axis: metric value with label
- Annotations DIRECTLY ON the chart pointing at specific inflections
- Annotation text: 2-3 lines max per annotation
- Reader can understand the chart from annotations alone (no need to read body prose)

**When to use:** Long-form editorial pieces explaining "what happened." Season arcs. Coach-era retrospectives.

**When NOT to use:** Short-form contexts (use trajectory spark). When you don't have specific events to annotate (you have just a line — use trajectory spark).

**Implemented by:** `cfb_rankings.charts.render_annotation_overlay` (the shared NYT-Upshot callout: marker dot + leader + label box, collision-aware, bounds-clamped, static SVG). Pass it pixel coordinates in your chart's own viewBox; it returns a `<g>` overlay fragment. New annotated charts must reuse it rather than re-rolling dot+label markup.

---

### 5. Small Multiples Grid (Tufte / Bloomberg style)

**Use for:** Comparing many entities on the same metric. "How does the 14-team SEC look on red-zone efficiency?"

**Visual:**
```
RED ZONE TD% — SEC programs, 2025 season

Alabama          Auburn           Florida          Georgia
[mini-chart]     [mini-chart]     [mini-chart]     [mini-chart]

Kentucky         LSU              Miss State       Missouri
[mini-chart]     [mini-chart]     [mini-chart]     [mini-chart]

Ole Miss         Oklahoma         South Car        Tennessee
[mini-chart]     [mini-chart]     [mini-chart]     [mini-chart]

Texas            Texas A&M        Vanderbilt       —
[mini-chart]     [mini-chart]     [mini-chart]
```

**Required elements:**
- Grid layout (3-4 columns desktop, 2 columns mobile)
- Each cell: entity name + identical mini-chart (sparkline, bar, or distribution)
- Identical Y-axis range across all cells (so comparisons are honest)
- Optional: subtle background tinting per entity (conference color, team color at low opacity)

**When to use:** Conference comparisons. Position-group breakdowns. League-wide trend views.

**When NOT to use:** When entities aren't truly comparable (apples-to-oranges defeats the point). When entity count <5 (just use a single chart with multiple series).

---

### 6. Heatmap

**Use for:** Two-dimensional categorical/spatial data. "Where on the field do plays happen?"

**Visual:**
```
PLAY LOCATION HEATMAP — Alabama 2025 passing

Yards from LOS
  0  +5  +10 +15 +20 +25 +30 +35 +40
L ░░░░ ▓▓▓▓ ████ ▓▓▓▓ ░░░░ ░░░░ ░░░░ ░░░░
  ░░░░ ▓▓▓▓ ████ ████ ▓▓▓▓ ▓▓▓▓ ░░░░ ░░░░
  ░░░░ ▓▓▓▓ ████ ████ ████ ▓▓▓▓ ▓▓▓▓ ░░░░
M ░░░░ ▓▓▓▓ ▓▓▓▓ ████ ████ ████ ▓▓▓▓ ▓▓▓▓
  ░░░░ ░░░░ ▓▓▓▓ ████ ████ ████ ▓▓▓▓ ░░░░
  ░░░░ ░░░░ ▓▓▓▓ ▓▓▓▓ ████ ▓▓▓▓ ▓▓▓▓ ░░░░
R ░░░░ ░░░░ ░░░░ ▓▓▓▓ ▓▓▓▓ ▓▓▓▓ ░░░░ ░░░░
```

**Required elements:**
- Two clearly-labeled dimensions (X and Y)
- Color scale legend ("░ low → ▓ medium → █ high")
- Optional: overlay annotations for notable cells

**Color encoding:** Sequential single-hue (e.g., light gray → dark navy). Diverging only when zero/center is meaningful.

**When to use:** Play locations, mood-by-week (team-week heatmap), schedule difficulty matrices.

**When NOT to use:** When there's no second dimension (use bar/spark). When data is too sparse (large empty regions). When color-blindness concerns dominate (add pattern + color, or use small multiples instead).

---

### 7. Choropleth (statebins tile grid)

**Use for:** Geography where the geography IS the point — recruiting footprint, fan-density, regional attention pull.

**Visual:**
```
WHERE THEY RECRUIT · 2023-2026
        (tile per state, gold intensity = signee count)
  WA ID MT ND MN WI MI       NY MA
  OR NV WY SD IA IL IN OH PA NJ CT
  CA UT CO NE MO KY WV VA MD DE RI
     AZ NM KS AR TN NC SC DC
        OK LA MS [AL] GA
  AK HI    TX              FL
  Fewer ▁▂▃▄▅ More (peak 24)
```

**Required elements:**
- One tile per state (50 + DC), each in its approximate geographic position
- Sequential single-hue ramp (faint → accent gold); zero-count states render faint, never absent
- Legend with the peak value labelled
- Per-tile `aria-label` ("AL: 24") — the chart is keyboard/SR legible without the visual

**Color encoding:** Sequential single-hue only (color-blind safe; no red/green). `sqrt` spread so a dominant home state doesn't wash out the mid-volume pull.

**Why a tile grid, not true boundaries:** real state shapes collapse below ~360px (RI, DE, DC become invisible), violating the mobile-legibility gate. Uniform tiles stay readable at 320px and keep the SVG small enough for the per-page weight budget. Implementation: `src/cfb_rankings/charts/choropleth.py`.

**When to use:** Recruiting footprint (live on team pages), fan-density maps, transfer origin geography.

**When NOT to use:** When geography is incidental (use a bar of state counts). For flows between places (use Sankey). When fewer than ~5 states have data (use the text-chip list).

---

### 8. Network (circular chord diagram)

**Use for:** Relationships *between* a bounded set of entities — portal pipelines between programs, coaching carousel, rivalry graphs. The point is who connects to whom and how heavily.

**Visual:**
```
        Oklahoma St
   Baylor  ●   ●  Penn St
  Miss St ●  ╲│╱  ● UConn
 Florida ●  ──┼──  ● Memphis      (nodes on a ring; arcs bow
S Florida ● ╱│╲ ● Iowa St          toward centre; arrow = source→dest;
  Mich St ●   ●  ● LSU             dot size = total traffic)
   Colorado ● ● ● Arkansas
        West Va  N Texas  Auburn
```

**Required elements:**
- Nodes evenly spaced on a ring (deterministic, overlap-free — no force simulation, which would need JS and a seed)
- Directed edges as quadratic-bezier chords bowing toward the centre, with an arrowhead marker (constant size, `markerUnits="userSpaceOnUse"`) encoding direction
- Node radius ∝ degree/weight; edge stroke-width ∝ weight; thin the edge set to real relationships (e.g. ≥2) so the ring is never a hairball
- Per-node `aria-label` ("Penn State (N connections)"); labels fan outward, quadrant-anchored

**Why circular, not force-directed:** a force layout is non-deterministic and needs client-side JS to settle — both disqualifying (WS-11 static-SVG bar; the build needs stable, diffable output). A ring is fully deterministic and legible at 320px for the small node counts this chart is meant for (≤ ~20). Cap the node count and edge floor rather than rendering everything.

**Implemented by:** `cfb_rankings.charts.render_network` (`charts/network.py`) — `NetworkNode(id, label, weight)` + `NetworkEdge(source, target, weight)` in, self-contained `<figure>`/SVG out; `label_color` makes it portable to light host pages. Live on `/offseason/` as the 2026 portal-pipeline web (top-16 programs by transfer volume).

**When NOT to use:** As decoration where everything connects to everything (a hairball carries no information). When the relationships are a flow between *stages/levels* rather than a peer graph (use Sankey). When < 2 connected nodes survive the edge floor (omit the chart).

---

## FORBIDDEN chart types

These are explicitly NOT allowed on CFB Index:

### Pie Charts — ALWAYS forbidden
- Humans can't compare angles accurately
- Always replaceable with bar or text
- Reduce data density to near-zero

### Vertical Bar Charts (without percentile encoding) — forbidden
- For sport comparisons, percentile bars communicate the same data with more context
- Use percentile bar OR small multiples instead

### Radar / Spider Charts — forbidden EXCEPT in Player Fingerprint
- Radar charts are bad at quantitative comparison (PFF uses them but they're widely critiqued)
- Allowed ONLY when the SHAPE itself is the identity (player fingerprint hero context)
- All other multi-dimensional comparisons use small multiples or percentile bar grids

### Donut Charts — ALWAYS forbidden
- Pie chart with extra steps; same problems

### 3D Charts — ALWAYS forbidden
- 3D distorts data; no excuse in 2026

### Word Clouds — ALWAYS forbidden
- Pretty but uninformative; never appropriate for analytics

### Live-Animated Charts (perpetually moving) — forbidden
- Distraction without information value
- Animation only on chart load (per microanimation budget)

---

## Implementation

All approved chart types live in `src/cfb_rankings/charts/__init__.py`:

```python
"""Approved chart types. No chart on the site uses anything else."""

from .percentile_bar import render_percentile_bar
from .trajectory_spark import render_trajectory_spark
from .bump_chart import render_bump_chart
from .annotated_line import render_annotated_line
from .small_multiples import render_small_multiples_grid
from .heatmap import render_heatmap

# FORBIDDEN — not exported:
# - pie_chart (always)
# - vertical_bar_chart (use percentile_bar)
# - radar_chart (except in player_fingerprint internal context)

__all__ = [
    'render_percentile_bar',
    'render_trajectory_spark',
    'render_bump_chart',
    'render_annotated_line',
    'render_small_multiples_grid',
    'render_heatmap',
]
```

PRs that import or define chart-rendering functions outside this module SHOULD fail CI lint. (Add to repo lint config in a follow-up.)

---

## Annotation discipline (in-chart vs caption)

For every chart, annotations should live ON the chart, not in a caption below. The reader should be able to understand the chart from chart elements alone.

**Bad:**
```
[chart with no annotations]
Caption: "The 2017 inflection at week 8 was Alabama's title-run peak,
followed by Saban's retirement-era decline through 2023."
```

**Good:**
```
[chart with arrow + label on 2017-Wk8 point: "title-run peak"]
[chart with arrow + label on 2023-end point: "post-Saban transition"]
[brief caption below: "Alabama power rating, 2014-2025"]
```

Caption is identity (what's the chart). Annotations are story (what's notable). They have different jobs.

---

## Chart-card shell (the single shared wrapper)

Every chart should render through **one** shared shell so the surrounding chrome stops drifting (today some charts carry a source-receipt footer, some don't; some bury the data source inside the SVG, some omit it entirely).

**Implemented by:** `cfb_rankings.charts.render_chart_card` (`charts/card.py`). Pure, deterministic string composition — no JS, unit-tested with zero live data. Slots: `eyebrow` → `headline` → `lede`, then the chart (with optional `x_label`/`y_label` axis labels and an optional stacked `annotation_svg` overlay layer), then a `source` **source-receipt footer** (`Source · …`). The card does not draw the chart — pass it a finished SVG string from any renderer in the package.

**Discipline:** new chart surfaces render through `render_chart_card`. Existing hand-rolled chart chrome migrates to it incrementally (same posture as the `PENDING_CENTRALIZATION` registry for renderers). First production consumer: the **Talent Migration** Sankey on `/offseason/` (gained a source-receipt footer it previously lacked; its title + source moved out of the SVG onto the card).

---

## Color discipline per chart

Per `docs/design-system/00-tokens.md`:

| Encoding type | Ramp | Used in |
|---|---|---|
| Percentile (player/team vs cohort) | red → grey → blue | Percentile bar, distribution charts |
| Belief / sentiment | red → grey → green | Trajectory spark for mood, fan-intel charts |
| Accolade / award status | gold (single color) | Heisman cards, all-American badges |
| Sequential single-hue | light → dark (navy or coral) | Heatmaps |
| Categorical (team series) | team accent colors | Bump charts, multi-team lines |
| Neutral data | gray ramp | Background series, "everyone else" in highlight contexts |

**Critical rule:** When red+green encode meaning (belief ramp), also add shape/icon redundancy for color-blind accessibility. Up-arrow + green for "rising"; down-arrow + red for "falling." Color alone is insufficient.

**Enforced by:** `scripts/check_color_blind.py --enforce` (wired into `publish_site.yml`) simulates deuteranopia/protanopia/tritanopia on the real tokens and fails the build if the percentile ramp loses distinguishability. The belief ramp is the allowlisted exception above — it depends on this shape/icon redundancy.

---

## Sample-size signaling on charts

Per `docs/design-system/33-confidence-signaling.md`:

Every chart that displays a metric subject to sample size must include a confidence chip in its caption or corner:

```
[Chart]
Sample: 247 mentions · last 7 days · medium confidence
```

If confidence is "insufficient," do NOT render the chart. Show a text fallback: "(insufficient data — minimum 30 mentions needed)."

---

## Mobile chart reformatting

"Reformat, don't shrink." Each chart type has documented mobile variants:

| Chart type | Desktop default | Mobile reformat |
|---|---|---|
| Percentile bar | 3-col inline grid | 1-col, full-width, label above bar |
| Trajectory spark | inline 160×40 | inline 120×32 (smaller but readable) |
| Bump chart | full-width, all entities | Top 5 movers only; "see all" link |
| Annotated line | full-width with side annotations | annotations inline above/below |
| Small multiples | 4-col grid | 2-col grid; if still too dense, vertical scroll |
| Heatmap | full grid with side labels | top labels only; bottom labels via tap-reveal |

---

## Print stylesheet

Every chart should render legibly in print (PDF export, screenshot for share):
- No interactivity dependencies
- All annotations baked in (not hover-only)
- Color works in grayscale (use redundant pattern/shape encoding)
- Caption + sample-size visible

---

## Adding a new chart type

Don't unless you have to. The constraint produces consistency.

If a genuinely new chart type is needed:
1. Write a proposal in COORDINATION.md including: what data needs visualizing, why the 6 existing types don't work, what visual reference you're using
2. Wait for human approval
3. Update THIS file before any rendering code
4. Add to `src/cfb_rankings/charts/__init__.py` exports

Chart proliferation is the #1 way data sites become visual chaos. Six is enough.
