# Player Page — §4 IA Spec Conformance Audit (2026-05-24)

Audit of `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` §4 (13-section IA) against the
shipped render (`reporting.py::render_player_page_html`, example
`output/site/players/cam-ward-1015.html`). Produced via Codex multi-LLM probe.

**Headline:** 0/13 sections are a full MATCH. 7 PARTIAL · 4 STUB (empty
"awaiting data" shell) · 2 MISSING. Most gaps are **data-empty, not
template-missing** — the modules render shells but their `player_data[...]`
contracts aren't populated.

## Conformance matrix

| § | Spec section | Status | Gap |
|---|---|---|---|
| 4.1 | Hero "QB Fingerprint" | PARTIAL | shell only; no Belief Dial / spark; cells "Awaiting" |
| 4.2 | Fan Intel "The Room" | PARTIAL | empty shells; rival tone split out vs pills-in-card; no Belief Dial/archetype/storylines |
| 4.3 | Accolade Lens | PARTIAL | fragmented across `current-heisman-lens` + `achievements` + `player-standing-detail`; no single surface |
| 4.4 | Current Season Production | PARTIAL | ribbon/drawers render; no game log; tables empty |
| 4.5 | Advanced Savant | STUB | 12 awaiting percentile bars, no real metric values |
| 4.6 | Splits (4 tabs) | STUB | empty-state copy only; no 4-tab IA |
| 4.7 | Signature Story | PARTIAL | prose renders but crowded by extra modules |
| 4.8 | Accolade Trajectory | **FIXED 2026-05-24** | promoted Heisman weekly chart to own `#accolade-trajectory` anchor (conditional). Still Heisman-only; doesn't generalize to non-Heisman awards yet |
| 4.9 | Peer Comparator | STUB | disabled search only; no pinned pills/radar |
| 4.10 | Supporting Cast & Scheme | STUB | empty shell awaiting roster/coordinator data |
| 4.11 | Trophy Case + Honors Timeline | PARTIAL | honors render; timeline unanchored + mixes live/historical |
| 4.12 | NIL + Draft | MISSING | only NFL-draft beat in career-arc; no NIL value, no mock-draft range |
| 4.13 | Bio/Recruiting/Transfer/Roster | PARTIAL | tabs exist but mostly "No fields populated"; fragmented |

## UX primitives (§3)
- **Shipped:** Percentile Bar, Drawer, Tab Bar, Chip, Selector Grid.
- **Absent:** Belief Dial, Trajectory Spark (now present in accolade tabs + §4.8), Pill Comparator.
- **Partial:** Eyebrow→Number→Narrative grammar (hero only).

## Mobile (§5)
Table wrappers present (good prerequisite). Unverified/absent: snap-scroll,
overflow containment, pinned-column, mobile accolade row. Needs CSS+browser pass.

## Three remaining work tracks (independent)

1. **Data contracts** (converts 4 STUBs → real): populate `savant.metrics`,
   `splits`, `peers`, `supporting_cast`. Biggest visual payoff; upstream
   ingestion/aggregation work.
2. **Missing UI primitives + sections**: Belief Dial, Pill Comparator;
   build §4.12 NIL+Draft (draft data exists via `player_nfl_draft`; NIL has
   no licensed source). Pure frontend — but Belief Dial/The Room are also
   data-blocked, so empty primitives add little until data lands.
3. **IA consolidation**: merge fragmented Accolade Lens into one surface;
   clean Trophy Case live-vs-historical. Editorial + anchor/subnav risk.

## Already fixed this session
- Player Standing rung ladder aligned to canonical §7.2/§7.3 (was mislabeling
  every All-American as "National watch").
- Accolade streams: per-position award tabs with real Heisman + AA data.
- §4.8 Accolade Trajectory promoted to its own anchored section.
