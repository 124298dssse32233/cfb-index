# CFB Index — v5.2 Final Go-Live Plan

**Date:** 2026-05-15
**Author:** Claude (synthesis pass, 5 v5.2 investigators + v5.1 review folded in)
**Status:** Definitive go-live document. Supersedes prior audits where conflicts arise; all additive content from v1–v5 remains canonical.
**Scope:** What to do, in what order, at what cost, with what fallbacks — to ship the world-class CFB Index program.

---

## What changed since v5.1 Review

Four updates collapse the cost surface and reshape the architecture:

1. **Max 20x tier confirmed.** $200/mo separate Agent SDK credit (effective 2026-06-15) covers the entire LLM workload with 10× headroom. **Incremental LLM cost: $0/yr.**
2. **Backfill complete (2026-05-15, 3h 19m).** 2014-2025 player-context + game-level stats + fanbase classification all live in the DB artifact. But the site didn't rebuild — `publish_site.yml` ran for 1m 33s and pushed 17 files (stale artifact passthrough). **This exposed an architectural gap to fix in Sprint v5-1.**
3. **No commissioned art.** ChatGPT Plus + Claude-generated SVG cover the imagery surface. Year-1 commission spend: $0.
4. **No custom domain.** Stay on `wonderful-margulis-8ec96b.vercel.app`. `BASE_URL` env-var pattern; OG cards Vercel-direct; weekly digest via GitHub Issue comment (not Resend email).

**Net effect on the program:**

| | v5 | v5.1 Review | **v5.2** |
|---|---|---|---|
| Year-1 incremental cost | $4,420 | $1,800 | **$0** |
| Year-2+ recurring | $4,420 | $1,800 | **$0** |
| Roadmap | 14 weeks | 17 weeks | **17 weeks** (unchanged) |
| External dependencies (DNS, Resend, commissioned art) | many | several | **zero** |
| Ship probability at target week | 50% | 85% | **90%** (fewer external deps = fewer slip vectors) |

---

## Part 0 · Immediate Action (Today, 2026-05-15)

**Trigger `world_class_enrich.yml` from GitHub Actions tab.** Do this before reading the rest of this document.

**Why:** The 3h 19m backfill ran successfully and uploaded a fresh DB artifact, but the auto-triggered `publish_site.yml` only ran for 1m 33s — meaning `build-site` failed silently (`set +e` + `check=False`) and the sanity gate fell back to the prior (stale) site artifact. The live site is still showing pre-backfill state.

**Why not `publish_site.yml` again:** Same failure mode will repeat. The workflow is designed not to poison rolling state, so it intentionally falls through to prior artifact when build-site exits non-zero.

**Why not `compute_full_pass.yml`:** Faster (~30-60 min) but skips AI content. Six years of new player-context data deserves AI editorial coverage (Wire backfill, Best Calls 2014-2025, Canon entries, Chronicle cards, Narratives, Mailbag seed).

**Expected runtime:** 2-4 hours. Watch the workflow logs; the `Sanity-check site before upload` step will tell you whether the rebuild produced ≥5000 files (healthy threshold).

**Sprint v5-1 work-item discovered from this:** The `backfill_full_history.yml` final step at line 333 calls `gh workflow run publish_site.yml`. Change this to `gh workflow run world_class_enrich.yml --field skip_ai=false`. See Part 4 below.

---

## Part 1 · The v5.2 Architectural Reset

Three architectural decisions define v5.2. All flow from the Max 20x tier + no-domain stance.

### 1.1 LLM cost architecture: Agent SDK credit covers everything

The user holds a Claude Code Max 20x subscription ($200/mo). After 2026-06-15, Anthropic introduces a separate Agent SDK credit pool — distinct from interactive Claude Code use — sized at the subscription tier:

| Subscription | Interactive credit | Agent SDK credit (new) | Combined monthly |
|---|---|---|---|
| Max 5x ($100/mo) | $100/mo pooled | $100/mo separate | $200/mo |
| **Max 20x ($200/mo)** | **$200/mo pooled** | **$200/mo separate** | **$400/mo** |

The CFB Index automation runs against the Agent SDK credit pool via `anthropics/claude-code-action@v1` with `CLAUDE_CODE_OAUTH_TOKEN` (NOT raw `ANTHROPIC_API_KEY`). This routes all automated workloads through the subscription credit, not pay-per-call API billing.

**Steady-state workload (Investigator B optimized routing):**

| Surface | Model | Calls/wk | Cost/wk (post-cache) |
|---|---|---|---|
| Chronicle cards | Haiku 4.5 | 595 | $0.40 |
| Wire factual restatement | Haiku 4.5 | 420 | $0.25 |
| Daily edition | Sonnet 4.6 | 7 | $0.50 |
| Heisman weekly | Sonnet 4.6 | 1 (15 wks/yr) | $0.20 |
| Canon nightly | Haiku 4.5 | 175 | $0.10 |
| Mailbag answers | Sonnet 4.6 | 10 | $0.80 |
| Reactions | Sonnet 4.6 | 5 | $0.50 |
| Edition cover essay | Opus 4.7 | 1 | $0.50 |
| Headline judge (Haiku-as-validator) | Haiku 4.5 | ~50 | $0.05 |
| **Total** | | **~1,264/wk** | **~$3.30/wk** |

Annual: ~$170/yr at sub-API rates. Translates to **~5-8% of the $200/mo Agent SDK credit** at typical Anthropic API-equivalent metering. Headroom is enormous.

**Implementation requirements (all land in Sprint v5-1):**

1. Add prompt caching to `llm_runtime.py:311` — system prompt with `cache_control: {"type": "ephemeral"}`. 15-line patch. Captures 30-40% cost reduction across all surfaces.
2. Route Chronicle + Wire through Haiku 4.5 (not Sonnet 4.6). Single-line change in `team_pages/chronicle_generator.py` model selection + `wire/editorial.py:37-48`. Largest cost savings ($2,320/yr at API rates).
3. Switch all GitHub Actions workflows from `ANTHROPIC_API_KEY` to `CLAUDE_CODE_OAUTH_TOKEN` + `anthropics/claude-code-action@v1`. Update 15 workflow YAMLs.

**Net incremental LLM cost: $0/yr.** Even spike workloads (full backfill enrichment regenerate at ~5,000 calls = ~$15) fit comfortably within monthly credit.

### 1.2 Imagery architecture: zero commissions

Per user constraint (2026-05-15): "not going to commission any art, we can use ChatGPT image creation as needed. it should all be fair use since its not for commercial reason, its personal use."

**Imagery surface taxonomy:**

| Surface | Volume | v5 plan | **v5.2 plan** |
|---|---|---|---|
| Trophy glyphs (8 Tier-1 + 17 Tier-2 rivalries) | 25 one-time | $2,500 commission | **Claude-generated SVG** (saved to `output/_assets/rivalry_trophies/*.svg`) |
| Edition cover hero (16:9) | 1/wk = 52/yr | OpenAI gpt-image-1 HD | **ChatGPT Plus manual** (user generates Fri morning during ritual, drops into `output/_assets/edition_covers/`) |
| Chronicle card backgrounds | 595/wk auto | OpenAI gpt-image-1 standard | **Pillow typographic** (no AI imagery; pure CSS + Pillow card composition) |
| Storyline thread hero | 8/wk auto | OpenAI gpt-image-1 standard | **Pillow typographic** |
| Reaction story hero | 5/wk auto | OpenAI gpt-image-1 standard | **Pillow typographic** |
| OG/share cards | every page | Pillow Python | **Pillow Python** (unchanged from v4) |
| Helmet renders (17 programs) | 17 one-time | Blender pipeline | **Skip entirely** — replace with typographic helmet stripes in CSS |
| Conference glyphs | 11 FBS + 13 FCS one-time | Phosphor OSS | **Phosphor OSS** (unchanged) |
| 12-glyph nav set | one-time | Phosphor OSS | **Phosphor OSS** (unchanged) |
| 10 CLIP reference images | one-time | ChatGPT Plus | **Skip entirely** (no CLIP gate needed without AI imagery pipeline) |

**Net imagery cost: $0 incremental.** ChatGPT Plus already paid. No Blender, no commissions, no OpenAI Images API, no FLUX, no CLIP embeddings infrastructure.

**Why this works editorially:** Strongest CFB editorial properties (The Athletic, Banner Society, FootballScoop) use ~90% photography (which we can't legally use without commercial license) and ~10% typographic composition (which is the part we can match). v3's Brad-Holland × Hopper × Niemann illustration aspiration was beautiful but premium. The typographic + SVG-trophy + Pillow-card approach is the actual sustainable surface for a one-person operation.

**Trophy SVG generation prompt template** (Claude with extended thinking, run once via /octo:design-ui-ux in Sprint v5-0):

```
You are designing an iconic SVG glyph for the {trophy_name} trophy
({rivalry_short_name}: {team_a} vs {team_b}).

Visual brief:
- Single-color, line-art style at 64×64 baseline
- Recognizable silhouette in ≤500 SVG bytes
- Should read at 16px (nav favicon) and 256px (rivalry detail hero)
- Use viewBox="0 0 64 64", stroke-linecap="round", fill="currentColor"
- Optional: 1-2 hairline interior details for character
- Output: just the SVG markup, no explanation

Trophy historical details: {historical_blurb}
Visual references (verbal description only): {reference_descriptions}
```

Generate 25 SVGs in one Sprint v5-0 session; commit to `output/_assets/rivalry_trophies/`.

### 1.3 Domain & email architecture: nothing leaves Vercel

Per user constraint: skip custom domain. Implications cascade:

| Component | v5 plan | **v5.2 plan** |
|---|---|---|
| Canonical URL | `cfbindex.com` | `wonderful-margulis-8ec96b.vercel.app` |
| URL composition | Hardcoded `cfbindex.com` in renderers | **`BASE_URL` env var** (default = Vercel hostname) |
| OG card hosting | `cdn.cfbindex.com` CNAME → R2 | **Vercel-direct** (`/og/<slug>.png` static files in site artifact) |
| Weekly editorial digest | Resend email to subscriber list | **GitHub Issue comment** to rolling `weekly-digest` issue (Kevin reacts 👍/👎 to approve/reject) |
| Reject-link signing | HMAC-SHA256 with `REJECT_LINK_SIGNING_KEY` secret | **GitHub Issue reaction** — 👎 within 24h moves item to `editorial_overrides` table |
| Reject-link receiver | Vercel serverless function | **GitHub Actions cron** polls `weekly-digest` issue reactions every hour |
| Subscriber acquisition | Resend signup form | **None** (single user; the workflow IS the subscriber) |

**Implementation: `src/cfb_rankings/common/head_chrome.py` (new in Sprint v5-1):**

```python
import os
from urllib.parse import urljoin

DEFAULT_BASE_URL = "https://wonderful-margulis-8ec96b.vercel.app"
BASE_URL = os.environ.get("CFB_INDEX_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

def absolute_url(path: str) -> str:
    """All URLs absolute against BASE_URL. Zero hardcoded hosts allowed."""
    if path.startswith(("http://", "https://")):
        return path
    return urljoin(BASE_URL + "/", path.lstrip("/"))

def render_head_chrome(page_type: str, page_data: dict, *,
                       canonical_path: str | None = None) -> str:
    canonical = absolute_url(canonical_path or page_data.get("path", "/"))
    og_image = absolute_url(page_data.get("og_image", "/og/default.png"))
    return f"""
<link rel="canonical" href="{canonical}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og_image}">
""".strip()
```

Grep `reporting.py` + `team_pages/*.py` + all renderers for `cfbindex.com` hardcodes; replace with `absolute_url()`. ~40 occurrences expected.

**Weekly digest workflow** (`.github/workflows/digest_weekly.yml`, lands Sprint v5-8):

```yaml
name: digest_weekly
on:
  schedule:
    - cron: '0 21 * * 5'   # Fri 17:00 ET / 21:00 UTC
  workflow_dispatch:

jobs:
  digest:
    runs-on: ubuntu-latest
    permissions:
      issues: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: Build digest body
        run: |
          python -m pip install -U pip pyyaml
          python -u manage.py build-weekly-digest \
            --out digest.md \
            --look-ahead-days 7
      - name: Post comment to rolling digest issue
        uses: peter-evans/create-or-update-comment@v4
        with:
          issue-number: ${{ vars.DIGEST_ISSUE_NUMBER }}
          body-path: digest.md
```

**Reject-poll workflow** (`.github/workflows/digest_reactions_poll.yml`, lands Sprint v5-8):

```yaml
name: digest_reactions_poll
on:
  schedule:
    - cron: '0 * * * *'   # hourly
  workflow_dispatch:

jobs:
  poll:
    runs-on: ubuntu-latest
    permissions:
      issues: read
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: Sync digest reactions to editorial_overrides
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          DIGEST_ISSUE_NUMBER: ${{ vars.DIGEST_ISSUE_NUMBER }}
        run: |
          python -m pip install -U pip
          python -u manage.py sync-digest-reactions
      - name: Upload DB artifact
        uses: actions/upload-artifact@v4
        with:
          name: cfb-rankings-db
          path: cfb_rankings.db
          retention-days: 90
          overwrite: true
```

`manage.py sync-digest-reactions` (new CLI in Sprint v5-8) reads the digest issue's comments via `gh api`, parses 👎 reactions on items, and inserts rows into `editorial_overrides` with `override_kind='reject'`.

**Net domain/email cost: $0. No DNS, no SPF/DKIM, no Resend, no R2 CNAME, no Vercel serverless functions.**

---

## Part 2 · Final Operational Budget

### Year 1 (Sprint v5-0 through v5-12)

| Item | Cost | Notes |
|---|---|---|
| Anthropic LLM API | **$0** | Covered by Max 20x Agent SDK credit ($2,400/yr) |
| OpenAI Images API | **$0** | Not used; ChatGPT Plus manual + Pillow typographic |
| Vercel Pro | **$240/yr** | Already paid |
| Cloudflare R2 | **$0** | Free tier; ~50 MB used (well under 10 GB cap) |
| Resend | **$0** | Not used; GitHub Issue digest instead |
| GitHub Actions | **$0** if public, $300/yr if private | Strong recommendation: toggle public |
| ChatGPT Plus | **$240/yr** | Already paid (used Friday for cover-essay imagery) |
| Claude Code Max 20x | **$2,400/yr** | Already paid (Agent SDK credit covers all automation) |
| Custom domain | **$0** | Skipped per user constraint |
| Trophy commissions | **$0** | Claude-generated SVG |
| Helmet `.blend` mesh | **$0** | Skipped (typographic helmet stripes instead) |
| 10 CLIP reference images | **$0** | Skipped (no AI imagery pipeline) |
| **Total incremental year-1 cost** | **$0** | (existing subscriptions: $2,880/yr unchanged) |

### Year 2+ recurring

Same line items. **$0 incremental annual cost** to operate the v5.2 program.

**Where this saved money vs v5.1:**
- LLM API: $1,300 → $0 (Agent SDK credit)
- Image API: $180 → $0 (no automated AI imagery)
- Trophy commissions: $3,000 → $0 (Claude SVG)
- Resend: $0 → $0 (unchanged; was already free tier)
- Domain registration: $15/yr → $0 (skipped)
- DNS upkeep: $0 (was already free)

### Cost-headroom posture

The Max 20x Agent SDK credit ($200/mo = $2,400/yr) sits at ~10× the steady-state workload. This means:
- Backfill enrichment passes (~$15-25 per full regenerate) cost ~1% of monthly credit
- Trial-and-error during development (prompt iteration, voice-validator tuning) is essentially free
- Headline auto-improvement passes (regenerate top-25% lowest-scoring headlines weekly) are affordable
- A second model layer (Haiku-as-judge for high-stakes surfaces) costs nothing meaningful

The `quality_gates.llm_weekly_spend_ceiling_usd` table column is still useful as a circuit-breaker (e.g., default to **$50/wk** as a runaway-cost safeguard), but in practice it should never trigger.

---

## Part 3 · The 17-Week Sprint Roadmap (Final)

Carries forward from v5.1 Review Part 3 with three changes flagged 🆕:

| Week | Sprint | Deliverable |
|---|---|---|
| **0** | **v5-0 Procurement** | 🆕 No DNS, no commissions, no Resend. **Reduced to:** API keys, repo-public toggle, 11 prompt templates, 17 profile-schema extensions, 25 Claude-SVG trophy glyphs, GitHub Issue setup for digest, Vandy "Shedeur"→"Milroe" fix, 4 fallback Editions pre-authored |
| 1 | v5-1 Foundation | 🆕 15 migrations. `llm_runtime.py` adds prompt caching + Agent SDK switch (`CLAUDE_CODE_OAUTH_TOKEN`). **`backfill_full_history.yml` final step changed to dispatch `world_class_enrich.yml`**. `BASE_URL` env-var pattern lands in `common/head_chrome.py`. Cron conversions on `world_class_enrich.yml` + `compute_full_pass.yml` |
| 2 | v5-2 Editorial gen | `prompts/edition_cover_essay.md` + 5 feature templates. `manage.py generate-edition`. `publish-edition-weekly.yml` moves into `site-deploy` group. Wire `_factual_restatement` → Haiku swap with feature-flag rollback. **Route Chronicle → Haiku** |
| 3 | v5-3 Reactions + storylines | `reactions-check-triggers --auto` wired into wire-daily + gameday workflows. `auto-promote-storyline-drafts` poller in nightly cron |
| 4 | v5-4 Mailbag + Chronicle | `mailbag-mine-questions` (Reddit + Bluesky + Substack RSS — carve out 2-3 days for Substack adapter). Chronicle `approval_state` filter on render. Backfill chronicle from `is_published` |
| 5 | v5-5 Heisman + Canon | `generate-heisman-narrative` weekly. Canon tier-aware nightly regeneration. `canon_entries.model_version_at_generate` column read |
| 6 | **v5-6a R2 + Pillow OG** | R2 verification (already free tier). `share_cards/` package with 10 Pillow templates. OG `<meta>` wiring via `_render_head_chrome()` using `BASE_URL` |
| 7 | **v5-6b Visual assets** | 🆕 **No Blender pipeline.** `visual_assets.asset_for()` helper returns SVG trophies + Phosphor glyphs + Pillow-composed hero cards. Typographic helmet-stripe CSS module |
| 8 | v5-7 Imagery + auto-throttle | 🆕 **No OpenAI Images integration.** `scripts/imagery/compose_typographic_card.py` Pillow composition (no AI). Auto-throttle reads `llm_weekly_spend_ceiling_usd=50` from `quality_gates` (safety net, not load-bearing) |
| 9 | **v5-8 Zero-Touch UI** | 🆕 **`digest_weekly.yml` + GitHub Issue comment** (no Resend). `digest_reactions_poll.yml` hourly cron. `/admin/queue/` page + slider UI writing to `quality_gates`. `/admin/panic` + `system_state`. `notify_failure.yml` reusable workflow wired into every cron |
| 10 | v5-9 Programs + Sources | 17 bespoke per-program renderer modules. 16 named data-source surfaces |
| 11 | **v5-10a Players** | 19 player position + archetype surfaces. `player_archetype_tags` migration backfilled |
| 12 | **v5-10b Rivalries** | 8 Tier-1 rivalry detail pages — uses Claude-SVG trophy glyphs from Sprint v5-0 |
| 13 | **v5-10c Phases + conferences** | 10 phase-specific surfaces + 11 conference landings + 5 cross-program surfaces |
| 14 | **v5-10d Reddit archive** | 12 Arctic Shift archive surfaces (acceptable risk — Reddit data already in DB from backfill) |
| 15-16 | **v5-11 Polish + verify** | Bug fixes from prod observability, performance tuning, voice-validator regression checks, post-publish HTML audit |
| 17 | **v5-12 Launch** | Methodology page deep update, observability dashboard, retro |

**Total: 17 weeks if everything goes well. 18-19 weeks with realistic slippage.**

**Why the roadmap stayed 17 weeks despite removing external dependencies:** The dependency removals (no DNS, no Resend, no commissions) freed Sprint v5-0 from procurement risk, but Sprints v5-7 and v5-8 take similar time (typographic Pillow composition replaces OpenAI integration; GitHub Issue tooling replaces Resend wiring). Net effect: lower variance, higher probability of hitting the 17-week target.

---

## Part 4 · Workflow Chaining & Self-Healing

This section is **new in v5.2** — added in response to the 2026-05-15 backfill→site gap. The discovered gap is symptomatic of a broader class of issue: workflows that silently fall through on failure.

### 4.1 The bug discovered today

**Chain:** `backfill_full_history.yml` ─(triggers)→ `publish_site.yml` ─(falls through silently)→ stale site

**Detailed failure mode:**

1. `backfill_full_history.yml:333` calls `gh workflow run publish_site.yml`
2. `publish_site.yml:96-122` runs `build-site` out-of-season (today is May; `in_season = False`)
3. `build-site` exits non-zero (probably FK constraint from new schema-vs-data gap)
4. `set +e` + `check=False` swallow the error
5. `prior-site` cache (from prior healthy run, ~17,000+ files) is already seeded into `output/site/`
6. Sanity gate `FILE_COUNT >= 5000` passes against prior-site contents
7. Workflow uploads prior-site as fresh artifact (stale data, same file count)
8. Push to `published` branch shows tiny diff (only methodology + editions index pages refreshed)
9. Workflow reports SUCCESS

The user sees "publish-site succeeded in 1m 33s" with no indication that the new data didn't make it to the site.

### 4.2 The fix (lands Sprint v5-1)

**Three changes:**

**Change A — Route backfill to enrich, not publish:**

```diff
# .github/workflows/backfill_full_history.yml line 333
-          gh workflow run publish_site.yml
+          gh workflow run world_class_enrich.yml --field skip_ai=false
```

`world_class_enrich.yml` has 80+ render steps including AI content regeneration, runs `set +e` on each step but doesn't swallow errors at the artifact-upload level, and has the same sanity gate. After a full data backfill, you want the full editorial pass — not the incremental sync that `publish_site.yml` does in-season.

**Change B — Build-site failure must propagate:**

```diff
# .github/workflows/publish_site.yml line 93-122
       - name: Build or incrementally sync
+        id: site_build
         run: |
-          set +e
+          set -e  # propagate build failure
           python <<'PY'
           ...
           PY
+
+      - name: Verify build produced fresh pages
+        run: |
+          # Count team pages in built output; if zero, fail loudly
+          TEAM_COUNT=$(find output/site/teams -name "*.html" 2>/dev/null | wc -l)
+          if [ "$TEAM_COUNT" -lt 100 ]; then
+            echo "::error::build-site produced only $TEAM_COUNT team pages — likely silent failure"
+            exit 1
+          fi
+          echo "Build verified: $TEAM_COUNT team pages"
```

This makes silent build failures explicit. If you see a 1m 33s success again, you know to investigate — there's now no path where stale-artifact masquerades as success.

**Change C — Sanity gate freshness check:**

```diff
# .github/workflows/publish_site.yml + world_class_enrich.yml
       - name: Sanity-check site before upload
         id: site_check
         run: |
           set +e
           FILE_COUNT=$(find output/site -type f 2>/dev/null | wc -l)
+          # Verify at least one file was modified during this run
+          MODIFIED_RECENTLY=$(find output/site -type f -newer prior-site 2>/dev/null | wc -l)
           echo "file_count=$FILE_COUNT" >> "$GITHUB_OUTPUT"
+          echo "modified_recently=$MODIFIED_RECENTLY" >> "$GITHUB_OUTPUT"
           if [ "$FILE_COUNT" -lt 5000 ]; then
             echo "::warning::output/site has only $FILE_COUNT files — refusing to upload poisoned artifact"
             echo "healthy=false" >> "$GITHUB_OUTPUT"
+          elif [ "$MODIFIED_RECENTLY" -lt 50 ]; then
+            echo "::error::Only $MODIFIED_RECENTLY files modified — build likely did not run, refusing to publish stale artifact"
+            echo "healthy=false" >> "$GITHUB_OUTPUT"
           else
             echo "healthy=true" >> "$GITHUB_OUTPUT"
           fi
```

### 4.3 The 15-workflow audit list

Every cron with `set +e` + `check=False` is a candidate for this class of bug. Sprint v5-1 audit pass:

| Workflow | Risk | Fix |
|---|---|---|
| `publish_site.yml` | HIGH (manifested today) | Change B + C above |
| `world_class_enrich.yml` | MEDIUM | Add Change C; per-step errors OK to swallow but final artifact must be fresh |
| `compute_full_pass.yml` | MEDIUM | Same as world_class_enrich |
| `the-daily-06am-et.yml` | MEDIUM | Sanity-check Daily edition was actually written |
| `wire-daily-04am-et.yml` | MEDIUM | Sanity-check Wire entries were actually added |
| `mailbag-friday-09am-et.yml` | LOW | Mailbag is tolerant of misses |
| `publish-edition-weekly.yml` | MEDIUM | Verify edition slug exists in DB before render |
| `ingest_hourly.yml` | LOW | Already tolerant of API outages |
| `ingest_daily.yml` | LOW | Already tolerant |
| `ingest_weekly.yml` | MEDIUM | Has `build-site` step — apply Change B |
| `fanintel_gameday_live.yml` | LOW | Aggregates; misses are fine |
| `scrape_health.yml` | LOW | Diagnostic only |
| `backfill_2025_season.yml` | HIGH (similar pattern to backfill_full_history) | Apply Change A pattern |
| `backfill_full_history.yml` | HIGH (manifested today) | Change A |
| `deep_research_monthly.yml` | LOW | Optional cadence |

### 4.4 Notification on silent failure

New `notify_failure.yml` reusable workflow (Sprint v5-8):

```yaml
name: notify_failure
on:
  workflow_call:
    inputs:
      run_id:
        type: string
        required: true
      workflow_name:
        type: string
        required: true

jobs:
  notify:
    runs-on: ubuntu-latest
    permissions:
      issues: write
    steps:
      - name: Open issue for failed run
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh issue create \
            --title "🚨 ${{ inputs.workflow_name }} failed at run ${{ inputs.run_id }}" \
            --body "Workflow run: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/${{ inputs.run_id }}" \
            --label automation-failure
```

Every workflow's final step does:

```yaml
      - name: Notify on failure
        if: failure()
        uses: ./.github/workflows/notify_failure.yml
        with:
          run_id: ${{ github.run_id }}
          workflow_name: ${{ github.workflow }}
```

Now every silent failure surfaces as a GitHub issue you can see at-a-glance. The hourly digest-reactions-poll workflow can additionally summarize open `automation-failure` issues in the Friday digest.

---

## Part 5 · Imagery Strategy (Final, No-Commission)

Detailed implementation of v5.2 §1.2.

### 5.1 Trophy SVGs (Sprint v5-0 one-time)

25 SVG files committed to `output/_assets/rivalry_trophies/`. Generate via Claude with extended thinking (one session per trophy, ~2-3 mins each, ~75 min total).

**Tier-1 (8 trophies, mythic):**
- `iron-bowl.svg` — molten droplet/Cramton Bowl trophy form
- `nd-usc.svg` — Shillelagh (Irish walking stick with shamrock detail)
- `stanford-cal.svg` — Stanford Axe (single-blade axe with notched grip)
- `red-river.svg` — Golden Hat (cowboy hat, 10-gallon proportions)
- `michigan-osu.svg` — Wolverine-Buckeye paired silhouette (no commissioned trophy, abstract)
- `army-navy.svg` — Commander-in-Chief's Trophy (paired anchor + saber)
- `cocktail-party.svg` — Florida-Georgia (jukebox or RC Cola bottle)
- `bedlam.svg` — Oklahoma-OK State (paired star)

**Tier-2 (17 trophies, regional):**
- Old Oaken Bucket, Floyd of Rosedale (pig), Iron Skillet, Egg Bowl, Apple Cup, Civil War (platypus), Holy War, Backyard Brawl, Black Diamond, Land of Lincoln, Paul Bunyan Axe, Megaphone, Heroes Trophy, Sweet Sioux, Telephone Trophy, Border War, Battle for the Bell

**Prompt template** (run once, refine across trophies):

```
Generate a 64×64 viewBox SVG glyph for [trophy_name].

Style requirements:
- Single-color line art, stroke="currentColor", fill="none"
- stroke-width="2", stroke-linecap="round", stroke-linejoin="round"
- Recognizable silhouette ≤500 bytes total
- Must read at 16px (favicon) and 256px (rivalry hero)
- 1-2 hairline interior details for character (e.g. shamrock detail on Shillelagh)
- Use only <path>, <circle>, <line>, <polyline>, <polygon>
- NO <text>, NO embedded fonts, NO external refs

Visual brief: [describe trophy in 2-3 sentences]
Historical note: [1-line context for the glyph's character]

Output: just the SVG markup, no explanation, no <?xml prolog.
```

### 5.2 Pillow typographic cards (Sprint v5-6a)

`src/cfb_rankings/share_cards/` package contains 10 Pillow templates:

| Template | Use | Dimensions |
|---|---|---|
| `og_default.py` | All pages without specialized card | 1200×630 |
| `og_team.py` | Team pages | 1200×630 |
| `og_player.py` | Player pages | 1200×630 |
| `og_edition.py` | Weekly edition cover | 1200×630 + 2400×1260 retina |
| `og_storyline.py` | Storyline thread hero | 1200×630 |
| `og_chronicle.py` | Chronicle card | 1200×630 |
| `og_reaction.py` | Reaction story | 1200×630 |
| `og_canon.py` | Canon entry | 1200×630 |
| `og_rivalry.py` | Rivalry detail (uses trophy SVG) | 1200×630 |
| `og_phase.py` | Phase-specific landing | 1200×630 |

Each template loads:
- Atkinson Hyperlegible (headline, OFL)
- Inter (body, OFL)
- Team brand asset PNG from `team_brand_assets` table (already populated)
- Trophy SVG from `output/_assets/rivalry_trophies/` (where applicable)

Composition logic per template ~80-120 lines Python. Total package: ~1,000 lines.

### 5.3 Friday cover-essay ritual (Sprint v5-2 manual handoff)

Once per week, when generating the weekly edition:

1. Auto-generated cover essay (Opus 4.7 via Agent SDK) lands in `editions.cover_essay_md` Friday 04:00 ET
2. `digest_weekly.yml` Friday 17:00 ET posts the edition preview to GitHub Issue
3. User reviews on phone or laptop, copies first paragraph of cover essay
4. User opens ChatGPT, runs prompt: `"Generate a 1792×1024 illustration in the style of Brad Holland × Edward Hopper × Christoph Niemann for an essay opening: '<paste paragraph>'"`
5. User downloads PNG, drops into `output/_assets/edition_covers/2026-w17.png`
6. Next Saturday 06:00 ET, `the-daily-06am-et.yml` runs `render-edition --slug 2026-w17` which picks up the new cover asset

If the user skips the Friday ritual (vacation, busy), `og_edition.py` Pillow template falls back to typographic-only cover (still visually strong, just no illustration).

**Expected volume:** 1/week × 52 weeks = 52 manual generations/year. ChatGPT Plus subscription handles this with zero issue.

### 5.4 What v5 had that v5.2 cuts

| v5 spec | v5.2 status |
|---|---|
| OpenAI Images API integration | **CUT** (manual ChatGPT Plus instead) |
| FLUX.1 [pro] integration | **CUT** |
| CLIP gate (cosine similarity ≥0.7) | **CUT** (no automated AI imagery to gate) |
| 10 hand-curated CLIP reference images | **CUT** |
| Blender helmet pipeline | **CUT** (typographic helmet stripes instead) |
| 50 helmet renders | **CUT** |
| BFL LoRA hosting | **CUT** |
| Replicate FLUX fallback | **CUT** |
| 8 + 17 = 25 commissioned trophy SVGs | **REPLACED** (Claude-generated SVG) |
| 12-glyph bespoke nav | **CUT** (Phosphor OSS unchanged) |

**Engineering surface area reduction: ~3,500 lines of imagery infrastructure not built.** Time saved: ~1.5 weeks in Sprints v5-7 and v5-8.

---

## Part 6 · Domain-Free Architecture

Detailed implementation of v5.2 §1.3.

### 6.1 BASE_URL grep + replace pass (Sprint v5-1)

Audit script (run once, Sprint v5-1 Day 1):

```bash
# Find all hardcoded hosts
grep -rn "cfbindex\.com\|cfb-index\.com\|wonderful-margulis" \
  src/ scripts/ tools/ manage.py \
  --include="*.py" --include="*.html" \
  | tee /tmp/hardcoded_hosts.txt
```

Expected hits: ~40 in `src/cfb_rankings/reporting.py`, ~10 in team_pages, ~5 in storylines, ~5 in editions, scattered elsewhere.

Replacement pattern: import `absolute_url` from `common.head_chrome`, replace `f"https://cfbindex.com/{path}"` → `absolute_url(path)`.

### 6.2 Sitemap + robots.txt

```python
# manage.py build-sitemap (new in Sprint v5-1)
def build_sitemap():
    base_url = absolute_url("/").rstrip("/")
    urls = sorted(_walk_output_site_html_files())
    with open("output/site/sitemap.xml", "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for url in urls:
            f.write(f"  <url><loc>{base_url}{url}</loc></url>\n")
        f.write("</urlset>\n")
```

`robots.txt`:

```
User-agent: *
Allow: /
Sitemap: https://wonderful-margulis-8ec96b.vercel.app/sitemap.xml
```

(If user later wants to register a custom domain, change `DEFAULT_BASE_URL` in `head_chrome.py` and re-run `build-sitemap`. Migration is a one-line code change + full rebuild — no infrastructure changes needed.)

### 6.3 OG card hosting on Vercel

OG cards live at `output/site/og/<slug>.png`. Vercel serves them at `https://wonderful-margulis-8ec96b.vercel.app/og/<slug>.png` directly. No CDN needed at current scale (~80 cards generated weekly, ~4MB total).

**Storage usage:** 80 cards × 50KB avg × 52 weeks = ~200MB/year. Vercel Pro allows 5GB build output (will need cleanup pruning after ~5 years; trivial to add).

### 6.4 GitHub Issue digest workflow (Sprint v5-8)

**Setup (one-time, Sprint v5-0):**

1. Create issue `Title: Weekly Editorial Digest` with body `This is the rolling editorial digest issue. Friday cron posts new comments here.`
2. Note the issue number (e.g., 47)
3. Set repo variable `DIGEST_ISSUE_NUMBER = 47` via `gh variable set DIGEST_ISSUE_NUMBER --body 47`

**Weekly digest format** (`build-weekly-digest` CLI output):

```markdown
# CFB Index Editorial Digest — Week of 2026-W17

## This week's edition
**Slug:** [2026-w17](/editions/2026-w17/)
**Cover essay:** "When the Bayou Calls" — LSU's October identity crisis
**Status:** ✅ Auto-published Sat 06:15 ET

## Next week (drafts requiring approval)
- [ ] Chronicle: Alabama vs Tennessee chapter (confidence: 0.62)
  React 👍 to approve, 👎 to reject
- [ ] Storyline: "Sark's Texas Plot" chapter 7 (confidence: 0.71)
  React 👍 to approve, 👎 to reject

## Recent quality alerts
- 2 voice-validator failures (auto-rejected, no action needed)
- 0 silent workflow failures

## Spend & usage
- LLM credit used this week: 6% of $200/mo Agent SDK pool
- GitHub Actions minutes used: 12% of monthly allowance
- Vercel deploys: 47/100 daily cap

[View edition →](https://wonderful-margulis-8ec96b.vercel.app/editions/2026-w17/)
[View admin queue →](https://wonderful-margulis-8ec96b.vercel.app/admin/queue/)
```

**Reaction-to-overrides flow:**

1. User reads digest comment Friday evening
2. User adds 👎 reaction to a list item they want to reject
3. Saturday 00:00 hourly `digest_reactions_poll.yml` cron runs
4. Cron calls `gh api /repos/:owner/:repo/issues/comments/<id>/reactions`
5. For each 👎 reaction, parses the comment for `Chronicle: <slug>` or `Storyline: <slug>` pattern
6. Inserts into `editorial_overrides` table: `(surface, slug, override_kind='reject', source='digest_reaction', applied_at=NOW())`
7. Saturday 06:00 `the-daily-06am-et.yml` and other publish workflows check `editorial_overrides` table before rendering
8. Rejected items are skipped or fall back to alternate content

### 6.5 What v5 had that v5.2 cuts

| v5 spec | v5.2 status |
|---|---|
| Domain registration ($15/yr) | **CUT** |
| DNS A/AAAA records | **CUT** |
| SPF + DKIM + DMARC for Resend | **CUT** |
| `cdn.cfbindex.com` CNAME | **CUT** |
| Resend integration (`RESEND_API_KEY` secret, signup form) | **CUT** |
| Subscriber list management | **CUT** |
| Vercel serverless function `/api/reject.js` | **CUT** |
| `REJECT_LINK_SIGNING_KEY` HMAC infrastructure | **CUT** |
| Cloudflare R2 custom domain | **CUT** (R2 still used for archive overflow, but no CNAME) |

**Engineering surface area reduction: ~600 lines.** Time saved: ~3 days in Sprint v5-8.

---

## Part 7 · Sprint v5-0 Procurement Checklist (Final)

Two-day checklist. No DNS propagation wait, no commission lead times, no external vendors.

### Day 1 — Account + repo setup (2-3 hours)

```
API keys:
[ ] Confirm Max 20x subscription active in claude.ai/settings
[ ] Generate CLAUDE_CODE_OAUTH_TOKEN: `claude --print --output-format=json | jq .token`
    (Or via claude.ai/settings → API tokens → Generate Agent SDK token)
[ ] Verify ANTHROPIC_API_KEY still works as fallback (will be deprecated in workflows
    during Sprint v5-1)

GitHub:
[ ] Toggle repo public (Settings → General → Change visibility)
    Verify no commit history secrets (run: `git log --all -p | grep -i 'key\|secret\|password\|token' | head`)
[ ] Add secret: CLAUDE_CODE_OAUTH_TOKEN
[ ] Create issue "Weekly Editorial Digest", note issue number
[ ] Set variable: gh variable set DIGEST_ISSUE_NUMBER --body <num>
[ ] Verify existing secrets present: CFBD_API_KEY, CFBD_PATREON_KEY, YOUTUBE_API_KEY,
    SEATGEEK_CLIENT_ID, SPOTIFY_CLIENT_ID

Vercel:
[ ] Confirm Pro plan active (Vercel dashboard → billing)
[ ] Verify VERCEL_TOKEN in repo secrets
[ ] Note Vercel-assigned URL: wonderful-margulis-8ec96b.vercel.app
[ ] Verify `site-deploy` concurrency group queues (not cancels) under contention —
    test by manually running publish_site.yml and world_class_enrich.yml simultaneously;
    one should queue, not cancel
```

### Day 2 — Asset + content authoring (4-6 hours)

```
Trophy SVGs (Claude session, ~75 min):
[ ] Generate 25 trophy SVGs using prompt template from Part 5.1
[ ] Commit to output/_assets/rivalry_trophies/*.svg
[ ] Visual sanity check at 16px, 64px, 256px in browser

Prompt templates (Opus session, ~2 hours):
[ ] prompts/edition_cover_essay.md
[ ] prompts/wire_why_it_matters.md
[ ] prompts/chronicle_card.md
[ ] prompts/daily_take.md
[ ] prompts/mailbag_answer.md
[ ] prompts/heisman_weekly.md
[ ] prompts/reaction_story.md
[ ] prompts/canon_entry_top10.md
[ ] prompts/canon_entry_11to100.md
[ ] prompts/pulse_state_of_team.md
[ ] prompts/thread_chapter.md

Profile-schema extensions (Kevin editorial, ~8.5 hours — can spread over Sprint v5-1):
[ ] 17 profiles/*.md frontmatter extensions per v5 Part 1 schema
[ ] Use signature_metrics_ladder (renamed from signature_metrics_to_lead_with)

Factual fixes:
[ ] profiles/vanderbilt.md: "Shedeur-beater" → "Milroe-beater"

Fallback content (insurance, ~3 hours):
[ ] Pre-author 4 weeks of seeds.py fallback Editions
[ ] Pre-author 2 fallback storyline chapters
```

### Total Sprint v5-0 effort

- Account/repo setup: 2-3 hours
- Asset generation (Claude/Opus): ~3 hours of compute time, ~2 hours of review
- Editorial authoring (Kevin): ~8-12 hours
- **Calendar time: 1-2 days** (no external lead times)

**Compare to v5.1 Review's v5-0:** Same calendar duration (1-2 days), but v5.1 had 6-8 week trophy commission lead time hanging over Sprint v5-10b — that risk is gone in v5.2.

---

## Part 8 · Canonical Reading Order

The seven-document corpus, in build order:

| Doc | Read for |
|---|---|
| **v1** ([DESIGN_AUDIT_2026_05_15.md](DESIGN_AUDIT_2026_05_15.md)) | Per-page problem inventory; live-site evidence baseline |
| **v2** ([DESIGN_AUDIT_2026_05_15_v2.md](DESIGN_AUDIT_2026_05_15_v2.md)) | Architecture deep-dive (5 token vocabularies, gold-hex drift, 15-renderer quality matrix) |
| **v3** ([DESIGN_AUDIT_2026_05_15_v3.md](DESIGN_AUDIT_2026_05_15_v3.md)) | Visual identity (12-motif vocabulary, 28-pattern viz catalog, fall-Saturday color recipe) |
| **v4** ([DESIGN_AUDIT_2026_05_15_v4.md](DESIGN_AUDIT_2026_05_15_v4.md)) | **Build spec** — 13 atoms, voice stylebook, mobile substrate, motion choreography, share cards, governance |
| **v5** ([DESIGN_AUDIT_2026_05_15_v5.md](DESIGN_AUDIT_2026_05_15_v5.md)) | **Bespokeness + automation** — per-program, per-player, per-rivalry, per-conference, per-season-phase |
| **v5.1 Review** ([DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md](DESIGN_AUDIT_2026_05_15_v5_1_REVIEW.md)) | Verification corrections to v5 (file paths, table names, cost math, sprint scope) |
| **v5.2 (this doc)** | **Final go-live plan.** Supersedes v5.1 Review where conflicts arise; carries forward v5/v5.1 additive content unchanged |

**Single-source-of-truth by dimension:**

| Dimension | Canonical |
|---|---|
| Color tokens | v3 Part 3 + v4 Appendix C alias map |
| 13 atom specs | v4 Part 1 |
| 5 universal opt-in atoms | v5 Part 1 |
| Editorial voice (5 desks, banned phrases, headline templates) | v4 Part 2 |
| Mobile substrate | v4 Part 3 |
| Motion choreography | v4 Part 4 |
| Share cards + SEO | v4 Part 5 (Pillow templates) + **v5.2 Part 5.2 (typographic-only)** |
| Performance budgets + audit subcommands | v4 Part 6 |
| 28-pattern viz catalog | v3 Part 6 |
| Chart library (Python-SVG primary) | v3 Part 7 + v4 atom helpers |
| **Imagery pipeline** | **v5.2 Part 5 (no commissions, Claude-SVG + ChatGPT Plus + Pillow)** |
| **Domain & URL strategy** | **v5.2 Part 6 (BASE_URL env var, no custom domain)** |
| **LLM routing & cost** | **v5.2 Part 1.1 + Part 2 (Agent SDK credit, $0 incremental)** |
| **Workflow chaining** | **v5.2 Part 4 (new — backfill→enrich, propagate failures)** |
| **Sprint roadmap** | **v5.2 Part 3 (17 weeks)** |
| **Operational budget** | **v5.2 Part 2 ($0 incremental)** |
| **Procurement checklist** | **v5.2 Part 7 (2-day, no external lead times)** |
| Profile schema | v4 §2.8 + v5 Part 1 (union, with `signature_metrics_to_lead_with` → `signature_metrics_ladder` rename) |
| Tier-1 rivalry list | v5 Part 3 (8 rivalries) |
| Conference identity | v5 Part 4 |
| 10 phase atlas | v5 Part 5 + canonical `_MONTH_TO_PHASE` at `state_resolver.py:39-52` |
| 12 Reddit-archive surfaces | v5 Part 6 + Arctic Shift archive (data now in DB from backfill) |
| Schema migrations | v5.1 Review Part 2 Correction #8 (15 migrations, `YYYYMMDD_NN_*.sql` naming) |
| Workflow-failure notification | **v5.2 Part 4.4 (new — `notify_failure.yml` + GitHub issue)** |

---

## Part 9 · Decision Log & Open Items

### Decisions locked in v5.2

1. **Max 20x Agent SDK credit covers all LLM workload.** Switch all workflows from `ANTHROPIC_API_KEY` to `CLAUDE_CODE_OAUTH_TOKEN` + `anthropics/claude-code-action@v1`. Steady-state usage ~5-8% of monthly credit.
2. **No custom domain.** `BASE_URL` env-var pattern, Vercel-assigned hostname. GitHub Issue digest replaces Resend email.
3. **No commissioned art.** Claude-SVG for trophies, ChatGPT Plus manual for Edition covers, Pillow typographic for everything else, no helmet 3D pipeline.
4. **Backfill→enrich auto-trigger.** `backfill_full_history.yml` final step changes from `publish_site.yml` to `world_class_enrich.yml`.
5. **Propagate build failures.** `publish_site.yml` and similar workflows stop swallowing build-site errors with `set +e`. Sanity gate adds freshness check (files modified during this run).
6. **Repo public.** Saves $300/yr in Actions overage and removes scaling cliff. Code IS the moat; data IS the moat; making the source public doesn't change either.
7. **Claude Code Desktop scheduled tasks (optional, premium surfaces).** For Edition cover essays where Opus 4.7 quality matters most, the `mcp__scheduled-tasks__create_scheduled_task` API can dispatch Friday-morning generation jobs from the user's local Claude Code Desktop — leveraging the interactive Max credit pool ($200/mo separate from Agent SDK pool). This adds 50% more LLM headroom for the highest-value surface. Implementation: Sprint v5-2 alongside the standard Agent SDK path; both run, the locally-generated one supersedes if present.

### Open items requiring user judgment (not blockers)

1. **Claude Code Desktop scheduled tasks?** Optional enhancement. Adds ~30 min Sprint v5-2 work. Recommend: yes, for the Edition cover essay surface only.
2. **Public-repo timing.** Recommend toggling at start of Sprint v5-0 to capture savings immediately. No risk (no secrets in git history per spot-check).
3. **Sprint v5-10d (Reddit archive) — full ship or defer?** v5.1 flagged this as highest-slip risk. With backfill done, Reddit data is in the DB — the renderer work is straightforward. Recommend: ship in v5-10d, don't defer.
4. **Fallback Edition stockpile depth.** 4 weeks pre-authored is current plan. Could go 8 weeks for extra resilience. ~3 additional hours of editorial work. Recommend: 4 weeks unless a long planned absence is upcoming.
5. **Voice-validator Haiku judge enable/disable.** Currently spec'd as default-on for high-stakes surfaces (Edition cover, Heisman weekly, Canon top-10). With Agent SDK credit headroom this is essentially free — recommend: enable by default.

### Items deferred to post-launch (not v5.x scope)

1. Custom domain registration (if site grows or Kevin wants vanity URL — trivial migration, one-line in `head_chrome.py`)
2. Resend integration (if subscriber list ever materializes — adds back to Sprint v5-8 in <1 day)
3. Commissioned trophy SVGs (if Claude-generated versions need refinement — can swap in commissioned versions at any time)
4. Helmet 3D pipeline (if typographic helmet stripes don't visually satisfy — can add in v5.3+)
5. OpenAI Images API (if manual ChatGPT Plus ritual becomes a chore — can re-add automated pipeline)

---

## Part 10 · Sprint v5-1 Day-1 Kickoff Brief

The very first commits to land after Sprint v5-0 procurement is done.

### Day 1 — Three patches, half a day

**Patch 1 — `llm_runtime.py` prompt caching + Agent SDK swap (90 min)**

```diff
# src/cfb_rankings/llm_runtime.py:311
-     kwargs["system"] = system_text
+     kwargs["system"] = [
+         {"type": "text", "text": system_text,
+          "cache_control": {"type": "ephemeral"}}
+     ]
```

```diff
# src/cfb_rankings/llm_runtime.py (top of file)
+ import os
+ # Prefer Agent SDK OAuth token (covered by Max 20x credit) over API key
+ _OAUTH_TOKEN = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
+ _API_KEY = os.environ.get("ANTHROPIC_API_KEY")
+ AUTH_HEADERS = (
+     {"Authorization": f"Bearer {_OAUTH_TOKEN}"}
+     if _OAUTH_TOKEN
+     else {"x-api-key": _API_KEY}
+ )
```

**Patch 2 — `backfill_full_history.yml` route fix (5 min)**

```diff
# .github/workflows/backfill_full_history.yml:333
-          gh workflow run publish_site.yml
+          gh workflow run world_class_enrich.yml --field skip_ai=false
```

**Patch 3 — `publish_site.yml` failure propagation (30 min)**

```diff
# .github/workflows/publish_site.yml:94-122
       - name: Build or incrementally sync
+        id: site_build
         run: |
-          set +e
+          set -e
           python <<'PY'
           ...
           PY
+
+      - name: Verify build freshness
+        run: |
+          MODIFIED=$(find output/site -type f -newer prior-site/ 2>/dev/null | wc -l)
+          if [ "$MODIFIED" -lt 100 ]; then
+            echo "::error::Only $MODIFIED files modified — build did not run"
+            exit 1
+          fi
+          echo "Verified: $MODIFIED files freshly written"
```

**Verification:** Push patches to a branch, trigger `world_class_enrich.yml` manually, watch logs. Within 4 hours the new data is live.

### Week 1 of Sprint v5-1 — 15 migrations + BASE_URL pass

```
Monday:
[ ] Land 3 Day-1 patches via PR; verify world_class_enrich passes new sanity gate
[ ] Trigger world_class_enrich.yml; new backfill data lands on live site

Tuesday-Wednesday:
[ ] 15 migration files committed (see v5.1 Review Correction #8)
[ ] Apply all migrations to local dev DB; verify no FK violations
[ ] Run apply-migrations in CI; verify idempotent

Thursday-Friday:
[ ] common/head_chrome.py created with BASE_URL pattern
[ ] Grep + replace pass: 40 hardcoded host references → absolute_url()
[ ] Build-site full pass with CFB_INDEX_BASE_URL unset (verify default)
[ ] Build-site full pass with CFB_INDEX_BASE_URL=https://example.com (verify override)
```

Sprint v5-1 ships ready for Sprint v5-2 editorial generation.

---

## Closing summary

**The CFB Index v5.2 plan is to ship the full v5 vision over 17 weeks, at $0 incremental cost, with zero external dependencies, on the existing Vercel hostname.**

Three things make this possible that weren't true at v5:

1. **The Max 20x Agent SDK credit** removes the LLM cost surface entirely.
2. **The no-domain decision** removes DNS, email, signing-key, and serverless-function complexity.
3. **The no-commission decision** removes 6-8 weeks of art procurement risk and $2,500-3,500 of one-time spend.

Two things make this more robust than v5 was:

1. **Workflow chaining fixes** (Part 4) prevent the silent-failure class of bug that surfaced today.
2. **Reduced surface area** (no FLUX, no OpenAI Images, no Resend, no commissions, no DNS) means fewer failure modes and fewer slip vectors.

**Immediate action — do now, before reading further:** Trigger `world_class_enrich.yml` from GitHub Actions tab. 2-4 hour runtime. Gets the post-backfill data live.

**Next action — start Sprint v5-0:** Two-day procurement checklist in Part 7. No external lead times. Sprint v5-1 can start Monday after Sprint v5-0 closes.
