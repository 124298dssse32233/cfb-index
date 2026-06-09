# World-Class CFB Stats Display — Implementation Plan

**Status**: Ready for implementation
**Context**: Card-based percentile design complete in `src/cfb_rankings/theme/`
**Goal**: Integrate world-class stats display into player/team pages with live CFBD tier 2 data

---

## Phase 1: Wire New Components to Player Pages (Sprint A)

### A1. Player Page Integration
**File**: `src/cfb_rankings/reporting.py`

**Task**: Replace legacy `season_stat_tables` rendering with new world-class components

**Changes**:
1. Locate `_render_player_season_stat_table()` function (grep for exact symbol)
2. Add import at top:
   ```python
   from cfb_rankings.theme import (
       render_all_player_season_stat_tables,
       render_percentile_bars_grid,
       render_sample_badge,
   )
   ```
3. Update the rendering call to use `render_all_player_season_stat_tables()` with `use_legacy=False`
4. Add feature flag for gradual rollout:
   ```python
   # In config.py or cli.py
   USE_WORLD_CLASS_STATS = os.getenv("USE_WORLD_CLASS_STATS", "false").lower() == "true"
   ```

**Acceptance Criteria**:
- Player pages show card-based percentile layout
- Sample size badge appears once at section header level
- No per-row "401 ATT" chips visible
- Theme toggle works on player pages
- Sortable headers preserve URL state

---

### A2. Advanced Stats Section (CFBD Tier 2)
**File**: `src/cfb_rankings/reporting.py` (new function)

**Task**: Add "Advanced Metrics" section to player pages with EPA, Success Rate, CPOE, AY/A

**Data Source**: CFBD API tier 2 (already accessible)

**Metrics to Display**:
| Metric | Definition | Benchmark |
|--------|------------|-----------|
| EPA/Play | Expected Points Added per play | +0.15 = elite |
| Success Rate | % of plays with positive EPA | 50% = elite |
| CPOE | Completion Percentage Over Expected | +5% = elite |
| AY/A | Air Yards per Attempt | 8.5 = elite |

**Implementation**:
1. Create `_fetch_advanced_stats(player_slug, season)` function
2. Call CFBD tier 2 endpoint for player advanced stats
3. Calculate percentiles against FBS QB peer group
4. Render using `render_percentile_bars_grid(bars, use_cards=True)`

**HTML Structure**:
```html
<section class="wcfb-advanced-stats">
  <h2>Advanced Metrics</h2>
  <div class="wcfb-sample-badge">...</div>
  <div class="wcfb-percentile-grid">
    <!-- EPA, Success Rate, CPOE, AY/A cards -->
  </div>
</section>
```

**Acceptance Criteria**:
- 4 advanced stat cards display per player
- Percentiles calculated against FBS QB cohort
- Gradient bars use tier-based colors (elite/good/low)
- Sample size badge shows "401 attempts • High confidence"
- Cards are tappable for stat definitions

---

### A3. Tap-Triggered Stat Definitions
**File**: `src/cfb_rankings/theme/assets/stat_definitions.js`

**Task**: Add definitions for advanced metrics

**Add to STAT_DEFINITIONS**:
```javascript
EPA: {
  name: "Expected Points Added",
  definition: "Measures the expected points value added on each play relative to the down, distance, and field position.",
  formula: "EPA = Points after play - Expected points before play",
  benchmark: "+0.15 per play = elite FBS QB",
  methodology: "https://cfbmetrics.com/epa/"
},
SUCCESS_RATE: {
  name: "Success Rate",
  definition: "Percentage of plays resulting in positive EPA.",
  formula: "Success Rate = (Positive EPA plays / Total plays) × 100",
  benchmark: "50% = elite FBS QB",
  methodology: "https://cfbmetrics.com/success-rate/"
},
// ... CPOE, AY/A
```

**Acceptance Criteria**:
- Tapping stat label opens bottom sheet (mobile) or popover (desktop)
- Each definition shows: name, one-sentence definition, formula, benchmark, methodology link
- Bottom sheet is dismissible with close button or backdrop tap

---

## Phase 2: Team Page Integration (Sprint B)

### B1. Team Offense/Defense Percentiles
**File**: `src/cfb_rankings/team_pages/` (new module)

**Task**: Add percentile fingerprint cards to profiled team pages

**Metrics**: Yards/Game, Points/Game, Yards/Play, Success Rate, EPA/Play, Turnover Rate

**Implementation**:
1. Use existing `render_team_offense_table()` and `render_team_defense_table()` factories
2. Add `PercentileBar` objects for each metric
3. Render with `render_percentile_bars_grid(use_cards=True)`

**Placement**:
- Offense card: After "Season Results" section
- Defense card: After opponent stats section

**Acceptance Criteria**:
- Offense card shows 6 metrics with team percentiles vs FBS
- Defense card shows 6 metrics with team percentiles vs FBS
- Sample size badge shows "13 games • High confidence"
- Cards link to team trend pages (future work)

---

## Phase 3: Data Pipeline (Sprint C)

### C1. CFBD Tier 2 Client Module
**File**: `src/cfb_rankings/ingest/cfbd_advanced.py` (new)

**Task**: Create dedicated client for CFBD tier 2 advanced stats

**Endpoints**:
```
GET /player/advanced?year={season}&player={player_id}
GET /team/advanced?year={season}&team={team_id}
```

**Implementation**:
```python
import requests
from cfb_rankings.config import CFBD_API_KEY

CFBD_TIER2_BASE = "https://api.collegefootballdata.com/player/advanced"

def fetch_player_advanced_stats(player_id: str, season: int) -> dict:
    """Fetch advanced stats for a player from CFBD tier 2."""
    resp = requests.get(
        CFBD_TIER2_BASE,
        params={"year": season, "player": player_id},
        headers={"Authorization": f"Bearer {CFBD_API_KEY}"}
    )
    resp.raise_for_status()
    return resp.json()
```

**Caching**: Add 24-hour cache to avoid rate limits

**Acceptance Criteria**:
- Client successfully fetches EPA, Success Rate, CPOE for any player
- 404 responses are handled gracefully (return empty dict, log warning)
- Cached responses are used when available

---

### C2. Percentile Calculation Module
**File**: `src/cfb_rankings/analytics/percentiles.py` (new)

**Task**: Calculate player percentiles against FBS peer group

**Implementation**:
```python
def calculate_player_percentile(
    player_value: float,
    season: int,
    stat_type: str,  # "epa_per_play", "success_rate", etc.
    min_snaps: int = 100,
) -> int:
    """Calculate percentile rank (0-100) for a player's stat value.

    Queries all qualified FBS players for the season/ stat,
    then computes percentile using linear interpolation.
    """
    # 1. Fetch all qualified players from database
    # 2. Sort values
    # 3. Calculate percentile using scipy.stats.percentileofscore
    pass
```

**Acceptance Criteria**:
- Percentiles are accurate (verified against manual calculation)
- Players with <100 snaps are excluded from denominator
- Results are cached per season to avoid repeated queries

---

## Phase 4: Testing & Validation (Sprint D)

### D1. Visual Regression Tests
**Files**: Create visual snapshots in `tests/visual/stats/`

**Test Cases**:
- `player_page_caleb_williams.png` — Elite QB (most values blue)
- `player_page_mid_qb.png` — Average QB (mixed green/blue)
- `player_page_low_qb.png` — Below-average QB (some red values)
- `team_page_alabama_offense.png` — Elite offense
- `team_page_low_defense.png` — Below-average defense

**Tool**: Use Playwright or similar for screenshot diffing

### D2. Mobile Responsiveness Tests
**Viewports**:
- 375×667 (iPhone SE)
- 390×844 (iPhone 12)
- 768×1024 (iPad)

**Checks**:
- All cards are fully visible without horizontal scroll
- Tap targets are ≥44×44px
- Sticky column doesn't overlap content
- Bottom sheet slides up smoothly

### D3. Cross-Link Verification
**File**: `tests/integration/cross_links.py`

**Task**: Verify all player/team/opponent links resolve

**Test**:
```python
def test_player_cross_links():
    """Verify player pages link to valid team pages."""
    html = render_player_page("caleb-williams")
    links = parse_links(html, class="wcfb-cross-link")
    for link in links:
        assert file_exists(link.href), f"Broken link: {link.href}"
```

---

## Phase 5: Rollout Strategy

### Week 1: Internal Testing
- Enable `USE_WORLD_CLASS_STATS=true` locally
- Verify 10-20 representative player pages
- Check load times (target: <2s per page)

### Week 2: Soft Launch
- Deploy to production behind feature flag
- Enable for 5% of traffic
- Monitor error logs and load times

### Week 3: Full Rollout
- Enable for 100% of traffic
- Remove legacy code path after 30 days

---

## Rollback Plan

If issues arise:
1. Set `USE_WORLD_CLASS_STATS=false` in environment
2. Site immediately falls back to legacy rendering
3. Fix issue, then re-enable flag

---

## File Checklist

- [ ] `src/cfb_rankings/reporting.py` — Player page integration
- [ ] `src/cfb_rankings/team_pages/` — Team page integration
- [ ] `src/cfb_rankings/ingest/cfbd_advanced.py` — CFBD tier 2 client
- [ ] `src/cfb_rankings/analytics/percentiles.py` — Percentile calculations
- [ ] `src/cfb_rankings/theme/assets/stat_definitions.js` — Advanced stat definitions
- [ ] `src/cfb_rankings/config.py` — Feature flag
- [ ] `tests/visual/stats/` — Regression snapshots
- [ ] `tests/integration/cross_links.py` — Link verification

---

## Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Page load time | <2s | TBD |
| Mobile tap target compliance | 100% | TBD |
| Broken links | 0 | TBD |
| Advanced stat coverage | 100% of FBS QBs | TBD |
| User engagement | ↑10% time-on-page | TBD |

---

**Ready to copy into new Claude Code session. Start with Phase 1, Task A1.**
