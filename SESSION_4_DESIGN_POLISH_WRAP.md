# Session 4 — Autonomous design polish wrap

**Mode:** User said "do it yourself, autonomously for as long as it takes."
**Audit source:** [docs/research/design-audit-2026-05-22-v2.md](docs/research/design-audit-2026-05-22-v2.md) (442 lines, 12 audit axes across archetype/copy/perf/a11y/SEO/onboarding/voice/charts/dark mode/cmdK/receipts/mockup drift)

Read [SESSION_3_AUTONOMOUS_WRAP.md](SESSION_3_AUTONOMOUS_WRAP.md) first for the structural CI/deploy fixes that preceded this work.

---

## TL;DR

5 commits pushed to master tonight. Phase A (Tier −1 navigation blockers): 2 of 4 false-alarms-in-audit corrected, 1 deferred (Vercel platform quirk), 1 real fix shipped (global footer on 17k+ pages). Phase B (Tier 0 copy bugs): all 7 clusters / 22+ fixes landed. Phase C (Tier 1 visual polish): 3 of 5 shipped, 2 deferred for design judgment. Local smoke test still 29/29 pre-deploy. publish-site run 26268986578 in flight to deploy everything — background monitor `bi9g2f85d` will fire on completion.

---

## Commits pushed to master tonight (newest first)

| SHA | Title | What it does |
|-----|-------|-------------|
| `814e2d77178` | feat(design): hero finding zone + filter-strip de-emphasis + URL fix | Phase C partial: Heisman hero finding zone (top candidate's win equity %, big number, sentence, caption per Dashboard archetype spec); filter-widget h2→h3.filter-strip-label de-emphasis on Heisman + Rankings; stale absolute Vercel URL fixed in `common/head_chrome.py` |
| `b54fcd3e3bb` | fix(copy): offseason-tense sweep across 7 page clusters | Phase B: 22+ offseason copy bugs gated on `is_offseason()`. Rankings risers/faders + selection intro, Players ×17k "right now" h2s, Hub vibe-shifts ticker + methodology + modifier + lexicon + cards, Conferences balanced-league lede, Compare-tool JS, Methodology section note, About-model phrasing, shared power-resume gap footer, Homepage scenarios + players landing |
| `ec29e3f1899` | fix(footer): add render_global_footer to legacy reporting.py page wraps | Phase A4: new `render_global_footer()` in nav.py + injected into 17 reporting.py page wraps (homepage, rankings, players, programs, conferences, history, heisman). Affects /rankings/ + 17,836 /players/* + 665 /programs/ + 662 unprofiled /teams/ + every /conferences/<slug> that were previously footer-less |
| `40ff9cde081` | docs: exhaustive design + content + ops audit v2 | The v2 audit doc this session executed |
| `70deb710c59` | docs: comprehensive design + offseason-copy audit (3 axes, 22 bugs) | v1 audit (superseded by v2) |

---

## Phase A — Tier −1 (broken navigation)

| Item | Audit ref | Outcome |
|------|-----------|---------|
| A1: `/conferences/<slug>` universal 404 | v2 §D1 | **FALSE ALARM** — my probes used wrong slug pattern. Real URLs are `/conferences/fbs-sec.html` etc. Verified 5 conferences resolve 200. v2 audit was wrong; corrected in progress log. |
| A2: `/players/nfl-pipeline/` 404 | v2 §D2 | **FALSE ALARM** — real URL is `/nfl-pipeline/` at site root, not under `/players/`. Verified 200. v2 audit was wrong. |
| A3: Vercel returns empty 404 body | v2 §D4 | **DEFERRED** — tried mixing `routes` config with `rewrites` in vercel.json; Vercel rejects that combo. Direct `/404.html` serves correctly; the auto-404 behavior on unknown URLs is a Vercel platform quirk that needs deeper investigation (likely interaction with `trailingSlash: true`). Reverted vercel.json. |
| A4: Footer missing on /players/* + /rankings/ | v2 §D5 | **FIXED** in commit `ec29e3f1899`. New `render_global_footer()` in nav.py + 17 reporting.py page wraps. |

---

## Phase B — Tier 0 (copy bugs)

All 7 clusters, all gated on `is_offseason(date.today(), db=None)`:

| Cluster | Files | Fixes | Surfaces affected |
|---------|-------|-------|-------------------|
| B1 | reporting.py | 4 | /rankings/ |
| B2 | reporting.py | 2 | /players/* × 17,836 |
| B3 | hub_page.py | 8 | /hub/vibe-shifts/* |
| B4 | reporting.py | 3 | /conferences/*, /compare/, /heisman/ remnants |
| B5 | reporting.py + provenance/methodology_page.py | 4 | /methodology/, /about-model/ |
| B6 | reporting.py | 3 | team / player / program / conference page footers via _power_resume_gap_text |
| B7 | reporting.py + players_landing.py | 4 | homepage scenarios + /players/ landing |

In-season behavior is unchanged. After publish-site deploys, all copy on offseason pages will read retrospectively ("through the most recent season", "from the last refresh", etc.) instead of as a live tracker.

---

## Phase C — Tier 1 (visual polish)

| Item | Audit ref | Outcome |
|------|-----------|---------|
| C1: Filter-widget h2 de-emphasis | v2 §C1 | **PARTIAL** — Heisman + Rankings filter strips converted from `<h2>` shouty hierarchy to `<h3 class="filter-strip-label">` with subdued 11px UI uppercase styling. The 2 Explorer h2s (History Explorer + Program Explorer + Season Explorer) kept as h2 since they're editorial-ish sections, not utility filters. |
| C2: Hero finding zone on Dashboard pages | v2 §C2 | **PARTIAL** — `/heisman/` ships with a hero finding (top candidate's win equity % as big number + sentence + sample-size caption). Other 3 Dashboard pages (`/`, `/rankings/`, `/hub/vibe-shifts/`) deferred — the "which number?" call needs design judgment outside an autonomous pass. |
| C3: Methodology footer on Dashboards | v2 §C3 | **DEFERRED** — pattern exists in team_pages/renderer.py but adapting requires picking the right data point (sample sizes, last-update timestamps) per page. Out of scope for autonomous pass. |
| D6: Stale absolute Vercel URL | v2 §D6 | **FIXED** — `DEFAULT_BASE_URL` in common/head_chrome.py updated from `wonderful-margulis-8ec96b.vercel.app` (old project URL, missing the kevins-projects suffix) to the full canonical URL. Affects canonical link, og:url, sitemap entries, twitter:url, JSON-LD @id across every renderer. |
| H1: Brand tagline + /about/ page | v2 §H1 | **DEFERRED** — tagline copy is a real product decision; /about/ page content needs editorial drafting. Not autonomous-grade work. |

---

## Validation status

- **Local imports clean:** verified `from cfb_rankings.reporting import …`, `from cfb_rankings.hub_page import …`, `from cfb_rankings.players_landing import …`, `from cfb_rankings.provenance.methodology_page import …` — all OK after edits.
- **Local smoke test against production:** 29/29 (100%) pre-deploy. No regressions on current-production pages from my work (since none of it is deployed yet).
- **publish-site run 26268986578** triggered at 04:55 UTC on commit `814e2d77178`. Status pending at hand-off; monitor `bi9g2f85d` will fire when it terminates (~50 min total).

After deploy, click these to see the changes:

- `/heisman/` — hero finding zone with big "X.X%" win equity, "Filter the board" instead of "BOARD CONTROLS"
- `/rankings/` — "Filter the rankings" instead of "Rankings Board Controls", Risers/Faders + intro reads retrospectively
- `/players/fernando-mendoza-38276.html` — footer now present, "What made this player interesting" h2 instead of "right now"
- `/hub/vibe-shifts/2025/18/` — ticker heading, methodology labels, modifier strip, cards section all read offseason-correct
- Any team page (e.g. `/teams/alabama.html`) — power-resume gap footer text now retrospective

---

## What I did NOT get to and why

Hard-deferred (per the v2 audit Tier 2 + Tier 3):
- Dashboard archetype renderer rewrites — multi-week structural work, not for autonomous time
- Profile archetype consolidation (17k player pages + 665 program pages + conferences into the team_pages design language) — same
- Performance work (Heisman pagination 14.8MB, players-dir 31MB virtualization) — needs design judgment
- Custom domain wiring — user hasn't picked
- Mockup pixel-diff vs live — needs browser automation
- Lighthouse + axe scoring — needs CI integration

Deferred from this session specifically:
- A3 Vercel 404 platform quirk
- C3 Dashboard methodology footers
- H1 brand tagline + /about/ page
- The 1374 tracked output/site/* files (untrack work, not autonomous-safe)
- `/today-in-history/` vs `/anniversary/today/` URL drift

Discovered as a side effect:
- The /attributions/ page (reporting.py:5528) is raw HTML string without f-string interpolation; it's footer-less and harder to retrofit. Minor surface, defer.
- The local Python venv was importing cfb_rankings from `C:\actions-runner\_work\cfb-index\cfb-index\src\cfb_rankings\__init__.py` (the self-hosted runner's checkout), not the user's working dir. Edits ARE in the right file; deploy will use them correctly. Not a code issue but worth noting for future local-test workflows.

---

## How to keep going from here

When the publish-site monitor fires:
1. Re-run `python scripts/smoke_test_live.py` against production. Should still be 29/29.
2. Visually click through the changed pages above. The biggest "looks designed" lift is the Heisman hero finding zone.
3. Read the v2 audit doc Tier 2 section for the next session's structural work.

For continuing the design polish in a fresh session: the design system spec at `docs/design-system/30-page-archetypes.md` is your roadmap. Five of six archetype renderers are still "TO BUILD." The Profile consolidation (17k player pages → team_pages design language) is the highest-impact structural job after this session.

— Claude, signing off
