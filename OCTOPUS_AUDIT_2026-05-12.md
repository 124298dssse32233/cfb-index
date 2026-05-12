# Octopus Audit 2026-05-12 — Summary

_End-to-end CFB Index audit run as a four-phase Double Diamond. Surgical fixes shipped on branch `claude/upbeat-mirzakhani-d6c855`. Full per-phase docs in `docs/octopus/`._

## Why this document exists

`CFB_INDEX_AUDIT.md` (2026-04-22) was the prior canonical audit. 12 of its 14 named P0 bugs have shipped fixes since. This document sits next to it so future sessions see the current state, not the historical one.

**Read order for orientation:**
1. This document (2-minute overview)
2. `docs/octopus/discover.md` — current-state audit with file:line evidence (10-minute deep read)
3. `docs/octopus/define.md` — the fix charter (5 minutes)
4. `docs/octopus/develop.md` — implementation log
5. `docs/octopus/deliver.md` — adversarial review + scoring + deferred backlog

## TL;DR

**The site is in much better shape than the 2026-04-22 audit suggested.** The Fan Intelligence layer is live (`/hub/` is fully populated), the homepage is no longer 5MB, the Mendoza Heisman contradiction is fixed, "Player Card Blueprint" / "Offensive Reminiscence" / "72 NCAA-eligible team records" / "v0.1.0" are all gone. The two highest-priority remaining issues are:

1. **🔥 Fan-intel entity matching is broken at the player-page level.** Mendoza's "Own fans" top quote is from a Penn State podcast about Mississippi NIL law and Indiana recruiting under Cignetti — not about Mendoza. The pipeline is treating team-level Indiana sentiment as player-personal sentiment. **Single most credibility-damaging issue on the site.** Deferred from this pass; needs dedicated work in `src/cfb_rankings/fan_intelligence.py`.

2. **🟡 Heisman page is 14.99 MB with ~15,363 unvirtualized rows.** Phone-killer. Deferred from this pass; needs pagination/virtualization work.

This Octopus pass shipped 8 surgical fixes addressing the rest of the active backlog.

## Shipped this pass (branch `claude/upbeat-mirzakhani-d6c855`)

| Commit | Fixes | Effect |
|---|---|---|
| `25ccf6c` | S-2 (Stress point → Closest call, 9 sites), S-3 (W15 W18 W20 W21 → "3-1 over the last 4 (W15 ...)" readable summary), S-4 (Heisman placeholder → five-lens legend), S-5 (illinois-college 404 guard), S-8 (effective-N floor jargon → fan copy) | Five user-visible content/copy fixes flagged by the prior audit and Codex's Phase 1 adversarial pass |
| `aea0c43` | S-6 (CLAUDE.md drift fix — line counts, profiled count, dropped stale line refs), S-7 (CFB_INDEX_AUDIT.md marked superseded) | Documentation hygiene — every future agent reads CLAUDE.md, and it was meaningfully stale |
| `b56c624` | S-5 regression fix — `_VALID_TEAM_SLUGS` pre-population ordering | Self-caught: my initial S-5 guard was a no-op because the set wasn't populated until after its first consumer ran. Fixed before review-pass close. |

## Deferred — out of scope for this pass, named explicitly

**MODULE-scope (1-2 days each, recommend a dedicated session):**
- **M-1: Fan Intel entity matching at the player level** — the Mendoza wrong-quote bug above. Highest priority.
- **M-2: Heisman board pagination / virtualization** — 14.99 MB single page.
- **M-3: Provenance chip on team Mood Cards** ("based on N posts from M sources") — partially landed for Heisman page in S-4; team-card variant pending.
- **M-4: Offseason watermark on homepage + team pages.**

**ARCHITECTURAL-scope (1-2 sprints each, need a planning session):**
- **A-1: Converge or freeze the two team-page renderers.** 17 profiled use `team_pages/`; 662 legacy use `reporting.py`. Each has modules the other lacks. The half-state is the maintainability cliff.
- **A-2: `/teams/<slug>.html` vs `/programs/<slug>.html` consolidation.** Audit flagged in April; still unresolved.
- **A-3: `reporting.py` decomposition.** 25,834 LOC and growing. Obvious module boundaries (heisman, history, conferences, compare).
- **A-4: Repo root cleanup.** 79+ stale `CLAUDE_CODE_*.md` and `OVERNIGHT_*.md` orphan briefs, plus empty `heisman_*.log` files.

## Provider summary

| Provider | Role | Outcome |
|---|---|---|
| Claude | Primary auditor + implementer | Ran Phase 1-4. Self-caught one S-5 regression mid-review. |
| Codex CLI | Adversarial Phase 1 perspective | Surfaced 5 critical bugs the primary pass missed: visible "Stub data until Sprint 14" copy, Mendoza wrong-quote attribution, Heisman beta copy, "Stress point" on wins, W15 W18 codes. **Codex was decisive on this audit.** Was running a second adversarial-review pass on the changes at session close. |
| Gemini CLI | Visual / UX / a11y / SEO perspective | Failed — auto-loaded the 15MB Heisman page on bootstrap, blew its 1M-token context. Accessibility/SEO scoring deferred to a Lighthouse pass. |
| 2026-04-22 audit | Frozen prior perspective | High-quality structural audit; 12 of 14 P0s now fixed, so largely historical. Marked superseded. |

## What's next

The user's autonomy directive was "fire all phases and implementations autonomously, I trust your judgment." Under that directive:

1. **Merge this branch.** Three small commits, all self-contained, all reviewable independently. Pre-merge checklist in `docs/octopus/deliver.md` §6.
2. **Run `./publish_site.ps1`** to rebuild the local site and deploy. The "Stub data until Sprint 14" homepage copy disappears (already fixed in source by `4e6b4c6`; only present in the 2026-05-11 stale local build).
3. **Open a follow-up session for M-1** (Mendoza wrong-quote / fan-intel entity matching). This is the single most credibility-damaging deferred item.
4. **Open a planning session for A-1 + A-3** when ready to invest in maintainability. The reporting.py monolith is the silent compounding cost.

---

_Audit run 2026-05-12. Branch: `claude/upbeat-mirzakhani-d6c855`. Generator: Claude Opus 4.7 with Codex CLI as adversarial pass. Gemini CLI failed; manual a11y/SEO follow-up needed._
