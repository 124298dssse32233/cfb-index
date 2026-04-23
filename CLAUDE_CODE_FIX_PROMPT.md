# Claude Code — CFB Index Site Fix Brief

> Paste this entire file into Claude Code as the opening message. The audit report it references is `CFB_INDEX_AUDIT.md` in this same repo. Read both before touching code.

---

## 0) Mission

You're picking up a static-site analytics product for college football (`THE CFB INDEX`). The generator is Python that writes `output/site/*.html` from a SQLite database. A product+UX audit just finished; the full report is at `CFB_INDEX_AUDIT.md`. This brief is a surgical, prioritized fix list tied to exact file and line locations so you don't have to re-discover the codebase.

Your job: execute the **P0 → P3** list below, verify with the protocol in §Verification, and leave the site ready for weekly publish. Do NOT redesign. Do NOT rewrite the generator. Do NOT do a "while I'm in here" refactor. Ship fixes.

If a fix requires a data repair (not template change), add it as a one-shot idempotent migration or a CLI subcommand — do not hand-edit `cfb_rankings.db`.

---

## 0.5) Model & token economy — READ THIS FIRST

This work is cost-sensitive. Use the cheapest model that can do each subtask correctly. Default to **Sonnet**. Escalate to **Opus** only where judgment earns the cost. Push everything mechanical to **Haiku** (usually via subagents).

### Routing table

| Subtask | Model | Why |
|---|---|---|
| Initial orientation + reading `CFB_INDEX_AUDIT.md` + this brief | Sonnet | One-shot, needs comprehension not raw reasoning |
| **Creating/updating `CLAUDE.md`** (see §0.75) | Sonnet | Seeds every future turn; write once well |
| P0.1 (tracked-teams counter) — find all callsites, decide counter strategy | **Opus** | Data-semantic decision: what "tracked" means is a judgment call |
| P0.2 (Heisman winner separation) — designing canonical vs projection split | **Opus** | Data-model decision with ripple effects on honors schema |
| P0.3 (empty-slug links) — template guard | Sonnet | Mechanical once the callsite is found |
| P0.4 (archive week labels) — week normalization logic | Sonnet | Straightforward mapping function |
| P0.5 (archive copy boilerplate gating) | Sonnet | Simple conditional |
| P0.6 (Mendoza Heisman tile) — verifies P0.2 | Haiku | Pure verification after P0.2 |
| P1.1 (Teams nav + teams index page) | Sonnet | Reuse the programs index pattern — templating work |
| P1.2 (rename internal labels) | **Haiku** | Find-replace with exact strings given |
| P1.3 (model_version leak) | Haiku | Grep + template guard |
| P1.4 (Mood Card offseason mode) — designing the offseason treatment | **Opus** for the design, Sonnet to implement | UX judgment: what shows in offseason is a product call |
| P1.5 (conference-page depth) — section design | **Opus** for IA, Sonnet for implementation | Info architecture decision |
| P2.1 (audit-links CLI command) | Sonnet | Standard CLI + walker code |
| P2.2 (meta description + OG tags) — per-page copy | **invoke `design:ux-copy` skill** (Sonnet) | Copy quality matters; skill is tuned for it |
| P2.3 (archive depth) | Sonnet | Routing + template work |
| P3 (a11y/polish) | **invoke `design:accessibility-review` skill** (Sonnet) | Skill is the right lens |
| Every verification grep / `wc -l` / file-read for pattern count | **Haiku subagent** | These are high-volume, low-judgment; never burn Sonnet on them |
| Final design review of rebuilt SEC page | **invoke `design:design-critique` skill** | Skill is the right lens |
| Writing the final summary (§8 deliverable) | Sonnet | Short, structured — no need for Opus |

### How to actually route in Claude Code

- Switch model for a run: `/model opus` → do the judgment work → `/model sonnet` to return to default.
- For mechanical sweeps, spawn an **Explore subagent** (Haiku-class) rather than doing it in the main loop. Prompt it narrowly: "Find every callsite of `program_url` in `src/cfb_rankings/reporting.py` and report line numbers only." Don't let it read whole files back to you.
- For verification, use a **general-purpose subagent** with Haiku. Hand it the exact grep/wc commands from §7.3 and ask for a pass/fail table. That subagent's context dies with the call — you don't pay to keep it.
- When a skill is the right tool (UX copy, a11y, design critique), invoke the skill — don't re-implement its prompt inline.

### Token discipline (non-negotiable)

- **Do not read the entire `reporting.py`.** It is ~17,500 lines. Use `Read` with `offset` and `limit` anchored to the line numbers in §2. If you need broader context around a fix, read ±80 lines, not the whole section.
- **Do not read the generated `output/site/**/*.html`** to verify fixes — they're 5MB+ each. Use targeted grep. The homepage alone is 5.2MB; one accidental full-read wastes ~200K tokens.
- **Do not re-dump `CFB_INDEX_AUDIT.md` into every subagent.** Pass the relevant P-id section only.
- **Build cadence:** use `python -u manage.py build-site` (template-only, fast) between fixes. Only run the full `./publish_site.ps1` (includes data refresh) once, at the end, before the final verification pass.
- **Batch verification:** run §7.3's whole grep suite in one bash call, not ten.
- **Compact early, compact often:** run `/compact` after each P0 ships. Your CLAUDE.md is the persistent memory; the live context isn't.
- **Don't re-explore between sessions.** If you end a session and start another, CLAUDE.md (§0.75) should be enough to resume. If it isn't, fix CLAUDE.md, don't re-read the repo.
- **Planning discipline:** use plan mode for P0.1, P0.2, P1.4, P1.5 (the Opus items). Skip plan mode for everything else — the fix is already specified here.

### When to escalate to Opus (and when NOT)

Escalate only when one of these is true:
- A decision affects the data model or schema.
- A decision affects cross-cutting copy (what users read on many pages).
- A bug's root cause is unclear after a 10-minute Sonnet attempt.

Do NOT escalate for:
- Template edits where the line number is already known.
- Grep sweeps.
- Renames with exact strings given.
- Writing new CLI commands against an established pattern.
- Anything a skill already handles.

---

## 0.75) Before you touch code: seed CLAUDE.md

If `CLAUDE.md` does not exist at repo root, create it on your first turn. It persists across sessions and saves re-orientation cost every time this project is re-opened. Populate it with exactly this (don't elaborate — the file earns its keep by being skimmable):

```markdown
# CFB Index — Agent Orientation

## What this is
Static-site CFB rankings + fan-intel product. Python generator → SQLite → ~17k HTML pages in output/site/.

## Do / Don't
- DO edit src/cfb_rankings/reporting.py (the generator) and fan_intelligence.py.
- DO use `python manage.py build-site` for fast iteration; `./publish_site.ps1` for full publish.
- DON'T edit output/site/** directly. Generated.
- DON'T hand-edit cfb_rankings.db. Write a CLI subcommand in cli.py.
- DON'T read reporting.py whole — it's 17.5k lines. Use offset+limit reads.

## Key line numbers (reporting.py)
- fetch_site_pulse: ~4087; counter bug at 4123-4124.
- "72 NCAA-eligible team records" copy: 5784, 10769.
- Empty-slug program link: 1131 (+ downstream consumer of program_url).
- Heisman winner render: 3935-3957.
- Nav tuples: 11717-11723.
- Fan intel fallback "Awaiting Signal": ~14830.
- Internal card labels to rename: 13116 (Stress Point), 13465 (Offensive Reminiscence), 13483 (Defensive Reminiscence), 9821 (Player Card Blueprint).

## Key files
- src/cfb_rankings/reporting.py — HTML monolith.
- src/cfb_rankings/fan_intelligence.py:833-838 — Mood Card default dict.
- src/cfb_rankings/ingest/honors.py — Heisman winner_flag source.
- src/cfb_rankings/cli.py — manage.py subcommands.
- src/cfb_rankings/config.py:43 — model_version string.

## Model routing
Sonnet = default. Opus = schema/data decisions, cross-cutting copy. Haiku = verification, renames, grep sweeps (via subagents).

## Build targets
- Fast: python -u manage.py build-site
- Full: ./publish_site.ps1
- Data refresh: ./safe_refresh_site.ps1
```

If `CLAUDE.md` already exists, read it once and only update if a section below makes it stale.

---

## 1) Ground rules

- **Never edit files under `output/site/**` directly.** Those are generated. Change the generator (`src/cfb_rankings/reporting.py`), the fan-intel layer (`src/cfb_rankings/fan_intelligence.py`), or the ingest/honors logic, then rebuild.
- **Rebuild command** (Windows PowerShell at repo root): `./publish_site.ps1` — this calls `python manage.py build-published` which runs `build_static_site`. If data changes are needed: `./safe_refresh_site.ps1` first.
- **Don't delete content wholesale.** Several bugs look like stale copy but the audit wants them renamed or gated, not removed.
- **Avoid client-side template literals in anything that must render statically.** Keep JS `${…}` only inside `<script>` blocks. Everything in the visible body must be Python-rendered before write.
- **Keep the SQLite file untouched at rest.** If you need a repair, write a CLI subcommand (`manage.py <name>`) that uses `cfb_rankings.db` helpers and is idempotent.
- **Testing:** after every logical group of fixes, do a spot build (`python -u manage.py build-site`) and re-open at least the pages listed in §Verification. Don't batch all fixes and build once.
- **Commit granularity:** one focused commit per P0 item. Bundle P1s and P2s by theme. P3s can be grouped.
- **Tool discipline:** prefer `Grep` over `Read`. Prefer `Edit` over `Write`. Never `Read` a file whose line count you don't already know — check with `wc -l` via `Bash` first if unsure.

---

## 2) Codebase orientation

```
src/cfb_rankings/
  reporting.py         ← the monolith (~17.5k lines). All HTML templating lives here.
  fan_intelligence.py  ← Mood Card / Respect Gap / Rival Heat / Cohesion / Swing Meter.
  config.py            ← model_version string (leaks to user copy right now).
  ingest/honors.py     ← Heisman winner flag + honors normalization. Source of Mendoza bug.
  cli.py               ← manage.py subcommands.
  pipeline.py, operations.py, audit.py, integrity.py
manage.py              ← entrypoint (wraps cli.py parser).
publish_site.ps1       ← python manage.py build-published
refresh_site.ps1       ← python manage.py sync-site-incremental --open-report
output/site/           ← generated (do not edit).
  index.html           ← homepage (~5.2MB)
  rankings/            ← Power Rankings landing
  heisman/             ← Heisman Tracker (~14.7MB)
  teams/<slug>.html    ← 667 team pages (current season)
  programs/<slug>.html ← 686 program pages (historical arc)
  players/<slug>-<id>.html ← 15,916 player pages
  conferences/<level>-<slug>.html ← 73 conference pages (fbs-*, fcs-*, dii-*, diii-*)
  archive/<season>-week-<n>.html ← 15 snapshot pages
  matchups/, compare/, history/, about-model/
```

### Where the headline bugs live (confirmed line numbers)

| Concern | File | Line(s) |
|---|---|---|
| `tracked_teams` / `tracked_conferences` counter (returns 72 instead of 667) | `reporting.py` | ~4087 (`fetch_site_pulse`), 4123-4124 (counter init) |
| "72 NCAA-eligible team records …" user-facing copy | `reporting.py` | 5784, 10769 (and 1 other) |
| Empty-slug program link: `../programs/.html` emitted when slug missing | `reporting.py` | ~1131 (`"program_url": f"../programs/{slug}.html" if slug else None`) + downstream render that coerces `None` → "" |
| "Heisman Trophy winner" rendered for Fernando Mendoza (a 2025 projection) | `reporting.py` | 3935-3957 (`winner_years`, `winner_flag`); root cause upstream in `ingest/honors.py` (`_honor_to_heisman_vote_result`) |
| Nav links (where to add a Teams link) | `reporting.py` | 11717-11723 (nav tuples) |
| Fan intel fallback label "Awaiting Signal" | `reporting.py` | ~14830 |
| Fan intel default dict | `fan_intelligence.py` | 833-838 |
| `model_version` leaks to user copy | `config.py` | 43 |
| "Stress Point" card label | `reporting.py` | 13116 |
| "Offensive Reminiscence" / "Defensive Reminiscence" | `reporting.py` | 13465, 13483 |
| "Player Card Blueprint" (internal scaffolding left on page) | `reporting.py` | 9821 |

---

## 3) P0 — data correctness bugs (ship first)

### P0.1 — Tracked-teams count is wrong  **[Opus for the fix design; Sonnet to apply]**
**Symptom:** Homepage and Data Pulse say "72 NCAA-eligible team records and X active conferences". Reality: 667 team pages, 73 conferences.
**Fix:** In `reporting.py` `fetch_site_pulse` (~line 4087). The counter (`tracked_teams = 0`) is only being incremented in a subset of branches. Change it to reflect the actual number of team pages that `build_static_site` emits — ideally by counting the unique `team_id`s that produce a page, not by re-walking a filtered branch.
**Token note:** Read only lines 4050-4200 of `reporting.py` to understand `fetch_site_pulse`. Do not re-read the whole file.
**Acceptance:** All three copy locations (reporting.py:5784, reporting.py:10769, plus any Data Pulse widget) show ≥ 600 team records and the accurate conference count. Build once, grep the output: `grep -n "NCAA-eligible team records" output/site/index.html` should reflect the real number.

### P0.2 — Fernando Mendoza labeled "Heisman Trophy Winner"  **[Opus — schema decision]**
**Symptom:** `/players/fernando-mendoza-2431.html` shows "Heisman Trophy Winner" in the honors timeline. Mendoza was the 2025 **Nowcast/Forecast** leader, not the canonical winner. The 2025 award has not been awarded in the data model (season year 2025, today is 2026-04-22; if the winner truly is him this is incidental — the bug is the provenance).
**Diagnosis steps:**
1. In `ingest/honors.py`, locate `_honor_to_heisman_vote_result` and whatever code sets a `winner_flag`. Confirm whether the projection pipeline (`run-heisman-model`) is writing rows into the honors table with a result-type that the generator can't distinguish from a real ballot result.
2. Run `python manage.py audit-awards-archive` if it exists; otherwise query the honors table directly in a small script and inspect Mendoza's row.

**Fix:**
- Separate "canonical" honors (source = AP ballot / trophy committee / CFBD historical) from "projected" honors (source = local heisman model).
- The generator (`reporting.py` ~3935-3957 where `winner_years` is processed) should emit "Heisman Trophy Winner" **only** for canonical sources. Projections render as "2025 Projected Heisman Leader" or "Nowcast Leader" with distinct styling.
- Back-compat: leave the historical 11 legit winners (Mayfield, Young, Williams, Henry, Smith, Daniels, Burrow, Murray, Jackson, Mariota, Hunter) exactly as they render.

**Acceptance:** `grep -l "Heisman Trophy Winner" output/site/players/*.html | wc -l` returns exactly **11** (the historical set). Mendoza's page shows a projection-styled badge instead.

### P0.3 — Empty-slug program links (`../programs/.html`)  **[Sonnet]**
**Symptom:** When a team lacks a `program_slug`, `reporting.py:1131` branches `"program_url": f"../programs/{slug}.html" if slug else None`. A downstream template almost certainly coerces `None` to `""` and the final HTML emits `href="../programs/.html"` or a Program History button that points nowhere.
**Fix:**
1. Track down the consumer of `program_url` in `reporting.py` (grep `program_url`). Fix the template to branch on truthiness — hide the Program History CTA entirely when no program page exists.
2. Ensure the JSON serialization path also skips the null, not stringifies it.
3. Optional: add an audit helper that scans the generated site for any `href=".../\.html"` patterns and fails the build.

**Acceptance:** `grep -RE 'href="[^"]*/\.html"' output/site | wc -l` returns 0.

### P0.4 — Archive "Week 38" (and stale Week 20 labels on 2014/2015/2021/2022)  **[Sonnet]**
**Symptom:** `/archive/2020-week-38.html` — Week 38 is not a real CFB week. Also `/archive/2014-week-20.html`, `/archive/2015-week-20.html`, `/archive/2021-week-20.html`, `/archive/2022-week-20.html` all uniformly say "Week 20" which is suspicious — most seasons top out at Week 16-17 including bowls.
**Diagnosis:** Find the archive-page builder in `reporting.py` (grep `archive` + `week`). The week number is likely being set from the raw CFBD `week` column (which can be `15 + season_type_offset` for bowls/playoffs) without normalization.
**Fix:**
- Normalize week labels before rendering: Regular-season weeks render as `Week N`. Bowl / CFP Round weeks render as `Bowl Season` or `CFP Quarterfinals` / `CFP Semifinals` / `National Championship` using a season_type field.
- The "Week 38" case is especially embarrassing — fall back to `Final` or `Postseason` for any week > 17.

**Acceptance:**
- `grep -l "Week 3[0-9]\|Week 2[2-9]" output/site/archive/*.html` → 0 files.
- `/archive/2020-week-38.html` either renames to `2020-final.html` with title "2020 Season | Final Snapshot" or retains a slug but displays "2020 Season | Final" in the header.

### P0.5 — Archive copy boilerplate leaks across seasons  **[Sonnet]**
**Symptom:** `/archive/2020-week-38.html` body contains the line "This page freezes the board exactly at this model checkpoint, so postseason games in early 2026 still remain attached to the 2025 season when that is the football cycle they decided." On a 2020 snapshot. That's a current-season blurb bleeding onto every archive page.
**Fix:** In the archive builder, gate that sentence behind `if season == current_season`. For historical snapshots use a different blurb keyed off the season (e.g. "2020 ended with a pandemic-shortened field — this snapshot is the model's final read on the season.").

**Acceptance:** `grep -l "early 2026" output/site/archive/` returns only the current-season page (or 2025-week-21.html), not 2014/2015/2020 etc.

### P0.6 — Mendoza "dual winner" Heisman tile on Heisman board  **[Haiku — verification only]**
**Symptom (referenced in CFB_INDEX_AUDIT.md):** The Heisman board emits conflicting status text for Mendoza in the finalist/winner row. Same root cause as P0.2 — fix P0.2 first and re-verify this view.
**Acceptance:** `/heisman/index.html` shows Mendoza exactly once at the top of the board with a single, consistent status label (e.g. "Projection Leader" or "Forecast #1" — not "Winner").

---

## 4) P1 — UX / copy / navigation

### P1.1 — Add a "Teams" link to primary navigation  **[Sonnet]**
Nav tuples live at `reporting.py:11717-11723`. Current: Power Rankings / Programs / History / The Model / Analysis / Weekly Archive / Matchup Simulator / Compare Teams. **Missing: a direct way to browse all 667 teams.** Add a `("teams", "Teams", "teams/index.html", ...)` tuple and build a `teams/index.html` that is a filterable, divisioned team browser (FBS / FCS / D-II / D-III tabs, conference group, alphabetical within).

Reuse the same filter/search idiom already used on `/programs/index.html` (1,362 hrefs works today) so the two indexes feel like siblings.

**Acceptance:** Click "Teams" in the top nav → lands on a team browser with all 667 pages linked and a level filter.

### P1.2 — Rename internal-sounding card labels  **[Haiku — mechanical rename]**
- `reporting.py:13116` — `"Stress Point"` → `"Pressure Point"` or `"Loss Risk"`.
- `reporting.py:13465` — `"Offensive Reminiscence"` → `"Offensive Comp"`.
- `reporting.py:13483` — `"Defensive Reminiscence"` → `"Defensive Comp"`.
- Remove the `"Player Card Blueprint"` H2 and its block entirely at `reporting.py:9821` — that's internal scaffolding that shipped.

**Acceptance:** `grep -R "Reminiscence\|Player Card Blueprint\|Stress Point" output/site | wc -l` returns 0.

### P1.3 — `model_version` string leaks to user copy  **[Haiku — grep + guard]**
`config.py:43` defaults to `"power-resume-v0.1.0"`. This string currently reaches the user-facing Data Pulse / methodology blurb. Audit every location in `reporting.py` that formats `model_version` into user-visible text; replace with a friendly `"CFB Index v1"` label that is independent of the internal semver. Keep the raw version in the methodology page (`/about-model/`) or a build-info footer, not in the top-of-page pulse.

**Acceptance:** `grep -R "power-resume-v" output/site | wc -l` → 0 in body copy (script blocks/data payloads fine if hidden).

### P1.4 — Fan Intelligence "Awaiting Signal" fallback needs a real offseason treatment  **[Opus to design, Sonnet to implement]**
Today's behavior (`reporting.py:~14830`, `fan_intelligence.py:833-838`): when Mood Card data is missing, every metric label defaults to "Awaiting Signal" and the card reads like a broken widget. It's April — the offseason — so this fallback is showing on the majority of team pages right now.

**Fix:**
- In `fan_intelligence.py`, add an `is_offseason` flag (true from ~Feb 1 through ~Aug 15). When true, render a distinct "Offseason Mode" Mood Card: show recruiting-class momentum, coaching stability, portal net (ingest separately), and spring-game buzz — whatever data is actually available in `cfb_rankings.db` for the offseason.
- When not offseason AND no signal: show a compact "No conversation signal yet this week — check back after first kickoff." message, one line, no fake zero-filled metrics.
- Never render "Awaiting Signal" repeated six times on a single card.

**Acceptance:** `grep -c "Awaiting Signal" output/site/teams/*.html | awk -F: '$2>0{c++} END{print c}'` → 0 (or the label is hidden by an offseason-mode branch).

### P1.5 — Conference pages are too thin  **[Opus for IA, Sonnet to implement]**
FBS SEC page renders ~2,100 visible characters total. Only 3 H2s: Conference Snapshot, League Drivers, Team Board. No games-of-the-week, no rivalry heat, no conference-level Mood Card, no stat leaders, no standings-within-conference over time.

Find the conference-page template in `reporting.py` (grep `"Conference Snapshot"`). Add sections, in this order:

1. **Games of the Week** (for the current week, or "This Week" / "Next Week" logic) — top 3 in-conference matchups with spread + model pick.
2. **Stat Leaders** — offensive/defensive top 5 within the conference (pull from game_player_stats).
3. **Conference Mood Pulse** — aggregate Fan Pulse across member teams.
4. **Rivalry Heat** — which rivalries inside this conference have the biggest "Rival Heat" score.
5. **Season Arc** — small sparkline of median conference power week over week.

FBS and FCS get the full treatment. D-II/D-III conferences can keep the current short form (data is thinner) but should still get at least the Games of the Week block.

**Acceptance:** Each FBS conference page renders ≥ 6 distinct H2 sections and ≥ 8,000 visible characters of body text.

---

## 5) P2 — Features worth doing because they're cheap after the fixes above

### P2.1 — Sitewide link audit as a CI gate  **[Sonnet]**
Add `python manage.py audit-links` that:
- Walks `output/site/**/*.html`
- Extracts every `href` not inside `<script>`/`<style>`
- Resolves relatively against the file location
- Asserts no broken internal targets, no `href=""`, no `href="../programs/.html"` patterns
- Exits non-zero on failure

Wire it into `publish_site.ps1` (or `build-published`) so every build fails loud on any future regression.

### P2.2 — Meta description + OG tags for share previews  **[invoke `design:ux-copy` skill — Sonnet]**
Zero pages currently have `<meta name="description">` or `og:*` tags. When a team page gets shared in iMessage/Slack/Twitter it has no preview card. Add to the base template in `reporting.py`:

- `<meta name="description" content="{page-specific summary}">` — per page type:
  - Team page: "Alabama (11-4, SEC) — Power #32, Resume 96. Mood, matchups, and the model's read on the Tide's 2025 season."
  - Heisman: "Live Heisman tracker — nowcast, forecast, and ballot lens for every real contender."
  - Homepage: "THE CFB INDEX — Power + Resume rankings for every NCAA football team, with Mood and Model lenses."
- `<meta property="og:title">`, `<meta property="og:description">`, `<meta property="og:type" content="website">`, `<meta property="og:url" content="{canonical}">`, `<meta name="twitter:card" content="summary_large_image">`.
- Optional but worth it: pre-generate a 1200x630 OG image per team (SVG is fine, or a PNG snapshot of the hero card).

### P2.3 — Archive depth for historical seasons  **[Sonnet]**
Today every historical snapshot (2014-2024) renders ~4.9K chars of mostly-same content with "No prior snapshot loaded" in the risers/drops. Either (a) generate at least 4 snapshots per historical season (pre-season, mid-season, end-of-regular, final) OR (b) be honest and route `/archive/2020-final.html` (etc.) to a "Final Snapshot" page that hides the week-over-week diff widgets since they have no meaning when there's only one snapshot.

Recommendation: ship (b) first; do (a) when you have time to backfill weekly snapshots during CFBD history ingestion.

### P2.4 — Player page density for non-star players
Not part of the audit sample (didn't dive on third-string backups) but worth a quick check: confirm mid-roster / low-stat players don't render half-empty Mood Cards or "--" stat blocks that make pages feel broken.

---

## 6) P3 — Accessibility / polish

- `<html lang="en">` on every page — confirm the base template always emits it. (Current sample: present on index but double-check archive pages.)
- Focus ring visibility — run a quick pass on interactive elements (tabs, filters, the Power/Resume chart dots) to ensure `:focus-visible` styles aren't masked by the hover treatment.
- Color contrast — verify secondary labels (the pale-gray submetrics under stat cards) hit WCAG AA 4.5:1 on the site's cream/white backgrounds. If close, darken once globally in CSS.
- Skip-to-main-content link at the top of each page for keyboard users.
- `aria-label` on icon-only buttons (filter chips, divisions toggles, chart focus selector).
- Print styles: currently most pages are 5MB+ and will print ugly. Add a `@media print` block that hides nav, scripts, and the hero hero background.

Run the `design:accessibility-review` skill (available in this session) on a representative sample: `/`, `/rankings/`, `/heisman/`, `/teams/alabama.html`, `/conferences/fbs-sec.html`.

---

## 7) Verification protocol

**Run this entire verification inside a Haiku subagent** (spawn a general-purpose subagent with Haiku) — don't do it in the main loop. The subagent's whole job is to run the commands below and return a pass/fail table. You pay its cost once; its context dies after.

After each logical group of fixes:

1. **Build:** `python -u manage.py build-site` (fast; skip ingest). Only run `./publish_site.ps1` once, at the very end.
2. **Machine checks — one bash call:** hand the Haiku subagent this exact block:
   ```bash
   set -e
   cd "<repo root>"
   echo "== P0.1 tracked-teams ==" ; grep -c "NCAA-eligible team records" output/site/index.html ; grep -oE "[0-9,]+ NCAA-eligible team records" output/site/index.html | head -2
   echo "== P0.2 heisman winners (expect 11) ==" ; grep -l "Heisman Trophy Winner" output/site/players/*.html 2>/dev/null | wc -l
   echo "== P0.2 mendoza should not be winner (expect 0) ==" ; grep -c "Heisman Trophy Winner" output/site/players/fernando-mendoza-2431.html
   echo "== P0.2 mayfield must still be winner (expect >=1) ==" ; grep -c "Heisman Trophy Winner" output/site/players/baker-mayfield-46652.html
   echo "== P0.3 empty-slug links (expect 0) ==" ; grep -REo 'href="[^"]*/\.html"' output/site 2>/dev/null | wc -l
   echo "== P0.4 nonsense week labels (expect 0) ==" ; grep -lE "Week 3[0-9]|Week 2[2-9]" output/site/archive/*.html 2>/dev/null | wc -l
   echo "== P0.5 'early 2026' leak on historical (expect 0) ==" ; grep -l "early 2026" output/site/archive/20[12][0-4]-*.html 2>/dev/null | wc -l
   echo "== P1.2 internal labels removed (expect 0) ==" ; grep -R "Reminiscence\|Player Card Blueprint" output/site 2>/dev/null | wc -l
   echo "== P1.3 model_version leaks in body (expect 0) ==" ; grep -R "power-resume-v[0-9]" output/site --include='*.html' -l 2>/dev/null | xargs -r -I{} sh -c 'python -c "import re,sys;h=open(sys.argv[1],errors=\"replace\").read();b=re.sub(r\"<script[\\s\\S]*?</script>\",\"\",h,flags=re.I);print(sys.argv[1] if \"power-resume-v\" in b else \"\")" "{}"' | grep -v '^$' | wc -l
   echo "== P1.4 no stacked 'Awaiting Signal' (expect 0) ==" ; python -c "import re,pathlib;c=0
   for p in pathlib.Path('output/site/teams').glob('*.html'):
     b=re.sub(r'<script[\s\S]*?</script>','',p.read_text(errors='replace'),flags=re.I)
     if b.count('Awaiting Signal')>=3:c+=1
   print(c)"
   echo "== P1.5 FBS conferences depth (expect each >=6 H2) ==" ; for f in output/site/conferences/fbs-*.html ; do echo -n "$f " ; grep -oE "<h2[^>]*>" "$f" | wc -l ; done
   ```
   Have the subagent return a single table: check name → actual → expected → PASS/FAIL. Nothing else.
3. **Spot-check** (only if the batch above passes) — open these in a local server (`python -m http.server --directory output/site 8000`):
   - `/` — Data Pulse count, hero CTAs, team browser link present
   - `/heisman/` — Mendoza row does NOT say Winner
   - `/teams/alabama.html` — card labels renamed, no "Awaiting Signal" stacks, no Player Card Blueprint
   - `/conferences/fbs-sec.html` — ≥6 H2 sections rendered
   - `/archive/2020-week-38.html` (or renamed equivalent) — no "early 2026" leak, sensible week label
4. **Design review** (skills — invoke at the end, not after every P-fix):
   - `design:design-critique` on the rebuilt SEC conference page
   - `design:accessibility-review` on `/teams/alabama.html`
5. **Reference** `CFB_INDEX_AUDIT.md` — anything in there you didn't address, flag explicitly in your summary (don't silently skip).

---

## 8) Deliverable

When you're done, commit changes, then post a summary that contains, in order:

1. **What changed** — one line per fix referencing P-id.
2. **What's verified** — the grep/machine-check outputs from §7.3 above.
3. **What you deferred** — anything from the audit you consciously chose not to do, with reason.
4. **Diff stats** — `git diff --stat main..HEAD`.
5. **Build artifact location** — paths to the 3-4 pages above that reviewers should open first.

Do not write a retrospective. Do not write new documentation beyond what fixes require. If you introduce a new CLI subcommand or migration, add exactly one line to `README.md` to point at it.

---

## 9) Execution order (optimized for cost)

Do it in this order — it's the cheapest path through the work:

1. **Sonnet — orientation pass** (one turn): read `CFB_INDEX_AUDIT.md` and this brief. Create or update `CLAUDE.md` per §0.75. **Do not start fixing yet.** Produce a one-paragraph plan of attack. Stop.
2. **Haiku subagent — mechanical P1.2 + P1.3** (renames, model_version grep/guard). These are cheap and clear out noise.
3. **Sonnet — P0.3 + P0.4 + P0.5** (empty-slug links, archive week normalization, archive copy gating). These are well-specified template edits. Batch into one working session, build once, verify.
4. **Opus — P0.1 + P0.2 design** (in plan mode). Decide the tracked-teams counter strategy and the canonical-vs-projection honors split. **Output: a plan, not code.** Then drop to Sonnet to implement.
5. **Sonnet — implement P0.1 + P0.2** from the Opus plan. Build, run Haiku verification subagent.
6. **Sonnet — P0.6 verification** (Haiku subagent actually runs the grep).
7. **Sonnet — P1.1** (Teams nav + teams index) by cloning the programs index pattern.
8. **Opus — P1.4 design + P1.5 IA** (what does offseason Mood look like? what sections go on a conference page?). Then Sonnet to implement.
9. **Sonnet — P2.1 + P2.3** and invoke `design:ux-copy` skill for P2.2 copy.
10. **Invoke skills — P3 a11y pass** via `design:accessibility-review`.
11. **Haiku subagent — run full verification** from §7.2. Should pass.
12. **Sonnet — final deliverable summary** (§8). Then `./publish_site.ps1` and post the summary.

Budget guardrail: if you find yourself on Opus for more than ~20 minutes of wall time without producing a concrete plan, you've scoped wrong — drop to Sonnet and reframe the problem.

Go.
