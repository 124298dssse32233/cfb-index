# Octopus Define — Fix Charter

_Phase 2 of the Double Diamond. Takes Phase 1's findings (`docs/octopus/discover.md`), ranks them by impact × ease, tags each as SURGICAL / MODULE / ARCHITECTURAL, and locks the scope for Phase 3._

**Charter rules.**
- SURGICAL = single file or ≤ ~20 LOC, edit-and-go.
- MODULE = bounded to one Python module (e.g. `team_pages/`, `fan_intelligence.py`).
- ARCHITECTURAL = needs migration plan + green light, not patchable in one session.

**Consensus.** Phase 1 had Claude (primary) + Codex (adversarial) + the frozen 2026-04-22 audit. I treat an item as **CONSENSUS** when ≥2 of the 3 named it. I treat **CONTESTED** items as ones where Codex and Claude actively diverged in framing.

---

## A. SURGICAL — in scope for Phase 3, ship now

| ID | Fix | File:Line | Effort | Impact | Consensus | Risk if shipped wrong |
|---|---|---|---|---|---|---|
| S-1 | Rebuild `output/site/` — local build is stale (2026-05-11), commit `4e6b4c6` already fixed "Stub data until Sprint 14" in source on 2026-05-12. Just need `python -u manage.py build-site` to land it. | n/a (build step) | 5 min | High (visible homepage credibility) | Codex + me | None — fix already merged upstream, this is just rendering it locally. |
| S-2 | Rename "Stress point" → "Closest call" in user-visible copy. 9 emission sites in `reporting.py`. The label "Stress point: beat Old Dominion 27-14" is nonsensical when applied to a win; "Closest call" reads correctly for wins AND losses. | `reporting.py:11676, 11689, 12233, 12248, 12442, 14670, 17405, 21102, 22550` | 15 min | High (user-visible on every team page) | Audit + Codex | Wording shift — could clash with editorial brief if "Stress point" is canonical product vocab. **Mitigation:** I'll grep `docs/editorial/` before shipping to confirm no contractual usage. If canonical, fallback is a context-aware label (Closest call for wins, Stress point for losses). |
| S-3 | Replace `<h3>W15 W18 W20 W21</h3>` heading with a human label, and translate the codes to readable form ("Win W15, Win W18, Win W20, Win W21" → "Last 4: W vs OSU, W vs Alabama, W vs Oregon, W vs Miami") OR add a one-line legend. The `recent_form` token output from `_compact_recent_form()` ships into the H3 unmodified. | `reporting.py:17410` (and `_compact_recent_form` at `21975`) | 20 min | Medium (visible on every team page in Performance Narrative) | Audit + Codex | Low — recent_form is internal; user-facing string is editorial. |
| S-4 | Delete or replace heisman "structure is ready for a world-class nowcast and forecast system" placeholder copy. | `reporting.py:15538` | 5 min | Medium (visible on Heisman page header) | Codex | None — pure copy edit. |
| S-5 | Apply `_valid_team_slug()` guard to `season_url` emission, so history page stops linking to `teams/illinois-college.html` (which doesn't exist). | `reporting.py:6039` | 10 min | Medium (fixes the one named broken link, plus probably more) | Audit + me | Low — `_valid_team_slug()` is already a defined helper used elsewhere in the file. Net effect: some links become unlinked spans rather than broken `<a>`s. |
| S-6 | Update `CLAUDE.md` to reflect current state: reporting.py is 25,834 lines (not 17.5k); 17 profiled programs (not 11); known surgical-sites line numbers are all stale and should be removed or replaced with `grep -n` instructions. | `CLAUDE.md` | 15 min | High (every future agent session reads this) | me | None — internal doc. |
| S-7 | Mark `CFB_INDEX_AUDIT.md` as superseded by `docs/octopus/discover.md` — add a 3-line header pointing forward. Move to `docs/audits/CFB_INDEX_AUDIT_2026-04-22.md` to make the supersession obvious. | top of file + `git mv` | 10 min | Medium (every future agent reads this) | me | None — doc hygiene. |
| S-8 | Replace "Awaiting Signal. No cohort cell for this team-week cleared the effective-N floor" with fan-facing wording ("Fan signal: still collecting — re-opens once the conversation pool publishes"). | Find in `fan_intelligence.py` or `team_pages/` | 15 min | Low–medium (visible on every team page Mood Card) | Audit + me | Low — pure copy. |

**Total estimated SURGICAL time: ~1.5 hours.** All 8 land independently on `octopus/fix-<slug>` branches and merge in any order.

---

## B. MODULE — out of scope for this Octopus pass, named explicitly so they don't slip

| ID | Fix | Scope | Effort | Impact | Why deferred |
|---|---|---|---|---|---|
| M-1 | 🔥 **Fix Fan Intel entity matching at the player-page level.** Mendoza's "Own fans" top quote (score 94.7, sample 47) is from a Locked On Penn State podcast about Mississippi NIL law / Indiana's recruiting under Cignetti — it has nothing to do with Mendoza personally. The pipeline is treating team-level Indiana sentiment as player-personal sentiment. | `src/cfb_rankings/fan_intelligence.py` + `src/cfb_rankings/ingest/sources/` | 1–2 days | **Critical** — this is the single most credibility-destroying issue on the site. A real fan who reads that quote on Mendoza's page will (correctly) conclude the fan-intel layer is unreliable. | Requires data-pipeline work, not a copy/render fix. Needs cohort-level entity filter on `the_room` data assembly. Out of scope for a one-session Octopus pass. **Recommend opening a dedicated branch in next session.** |
| M-2 | **Paginate / virtualize the Heisman board.** 14.99 MB single page, ~15,363 rows, no virtualization. Phone-killer. | `team_pages/`-style standalone Heisman renderer, OR a `reporting.py`-internal pagination pass | 1–2 days | High (mobile perf + crawler indexing) | The clean answer is "extract Heisman into its own renderer module under `team_pages/`-style architecture", which is too much for this pass. Surgical alternative (top-50 default + load-more) is feasible but requires a JS interaction model I don't want to write blind. |
| M-3 | **Heisman page Nowcast/Forecast/Win/Finalist/Ballot definition row.** | `reporting.py` (Heisman renderer surface) | 30 min | Medium | Could be SURGICAL if I scope it tightly — but I want it landed alongside M-2's pagination so the legend lives on a redesigned page, not bolted onto the broken one. Punted to next pass. |
| M-4 | **Provenance chip on team Mood Cards** ("based on N posts from M sources, methodology →"). | `fan_intelligence.py` + Mood Card render path | 1 day | Medium-high | The Mood Card UI lives across both legacy and team_pages/ renderers. Doing it in one place breaks parity. Defer until the two renderers converge or both get the chip in one PR. |
| M-5 | **Offseason watermark / freshness signal on homepage + team pages.** "Model state: end-of-2025-season, refreshes August." | `editions/homepage_renderer.py` + reporting.py team-page render | 1 day | Medium | Worth doing but requires deciding the canonical phrasing across surfaces. Better as a sprint task than a one-off fix. |

---

## C. ARCHITECTURAL — out of scope, but the charter names them so the next planning session has them ready

| ID | Decision needed | Rationale |
|---|---|---|
| A-1 | **Two team-page systems: converge or freeze.** Profiled (17 slugs, `team_pages/renderer.py`) vs legacy (~662 slugs, `reporting.py`). Each renderer has modules the other lacks. Either migrate all to `team_pages/` (1-2 sprints) or formally freeze the legacy renderer at current feature set and ship only profiled-page upgrades from here. The current half-state is the maintainability cliff. |
| A-2 | **`/teams/<slug>.html` vs `/programs/<slug>.html` consolidation.** Audit flagged this in April; still unresolved. Two pages per team, neither tells the user which they're on. Recommend collapsing into one page with a "Current Season / Program Arc" tab. |
| A-3 | **`reporting.py` decomposition.** 25,834 lines and growing. Some module boundaries are obvious (heisman renderer → its own module, conferences renderer → its own module, history page → its own module). A decomposition pass would unblock the `team_pages/` migration in A-1 and pay off compounding-rates style. |
| A-4 | **Repo root cleanup.** 79+ stale `CLAUDE_CODE_KICKOFF_*.md`, `OVERNIGHT_*.md`, `FIGMA_*.md`, multi-megabyte mockups (`notre_dame_mockup.html` 46KB, `team-page-mockup.html` 53KB, `fan_hub_original.html` 102KB), empty `heisman_debug.log` / `heisman_run.log`. Move completed kickoff briefs to `docs/archive/`, delete empty logs (already in `.gitignore` if not, add them). Could be SURGICAL but the volume of judgment calls makes it module-sized. |

---

## D. CONTESTED — single-paragraph disagreement preservation

There were no major Codex–Claude disagreements on what to fix. The disagreement was on **how serious data integrity is right now** (Codex: 4/10, me originally: 8/10, revised after Mendoza-quote evidence: 5/10). Codex is right that quote-level entity mismatch is a deeper credibility issue than the missing data-watermarks I weighted. **Recording for posterity:** the audit pipeline should flag mismatched player↔quote attribution as a tier-blocker before publish, not as a post-hoc fix. That's a process change, not a fix item.

---

## E. Verification protocol (carried into Phase 3)

Per CLAUDE.md, each fix must:

1. Land on its own branch `octopus/fix-<slug>`.
2. Include a one-paragraph rationale in the commit body.
3. Pass `python -u manage.py build-site` (fast iteration; full `./publish_site.ps1` only at end of phase).
4. Include a before/after for the user-visible change (rendered page line numbers or grep counts).
5. Respect the "no edits to `output/site/**`" and "no whole-file reporting.py reads" rules.

---

## F. Scope acceptance

**IN for Phase 3:** S-1 through S-8 (8 surgical fixes; ~1.5 hours estimated work).

**OUT for Phase 3:** M-1 through M-5, A-1 through A-4. Each gets a paragraph in `docs/octopus/deliver.md` naming it as deferred.

**Punted explicitly:** Phase 4 (Deliver) accessibility scoring requires axe-core or Lighthouse against a deployed page; I'll spawn a focused subagent for it rather than blocking Phase 3 on it.

Proceeding to Phase 3 under autonomous-execution directive.
